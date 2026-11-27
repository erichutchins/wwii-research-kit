# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = ["numpy", "pillow", "pymupdf", "pyyaml", "scikit-image", "scipy"]
# ///
"""The detailed version of each silhouette: the plate's own key lines and small white areas, inside the solid outline.

Every silhouette in records/silhouettes/silhouettes.yml is a solid shape (level 1). Its `detail` adds what the plate
draws inside that shape (level 2), traced from the same scan, at the same scale and place, by the entry's `crop`:

- lines: an SVG path (polylines, no fill), drawn as a stroke in the paper colour, 0.4 pt at print size;
- fills: an SVG path (even-odd), filled with the paper colour: glazing, windows, openings between struts.

Both are in the solid path's own frame (ships and vehicles in feet, y up negative; aircraft views in their 100-unit
frame). Nothing is drawn by hand: every mark is a threshold, opening or skeleton of the plate's pixels inside the
outline, and the thresholds are stored per entry in records/silhouettes/detail-params.yml, so a rerun reproduces the
result. The outline itself is never changed.

Two methods, by the kind of plate:

- `lines` (line drawings, stippled or shaded: the ONI warship and merchant plates, ONI 226, TM 9-2800): the plate's
  dark ink inside the outline (darker than `dark` after a 1 px blur, at least `inset` px inside), kept where it runs
  `min_len` px or more. With `orient: h` only runs along the hull count (deck, sheer, deckhouse tiers; window frames,
  the stipple and lettering drop out), with `orient: any` curves count too (fenders, wheels).
- `marks` (solid silhouettes with white marks: FM 30-30, the TAIC silhouettes, the Journal of Recognition): the white
  inside the outline (lighter than `white`): thin marks (no wider than `thin` px) become lines along their skeleton,
  other white areas become fills (windows, glazing, an opening between struts).

Further keys, where a plate needs them: `hug` (drop lines lying within that many px of the outline: a keel or edge
line that only doubles it), `within_ink` (take white marks only where the plate's ink encloses them: ports in a black
hull), `max_fill` (largest white area kept), `offset` (a fixed `[dx, dy]` where the alignment search drifts), `drop`.

`lines+marks` does both (ONI 208's black hulls with white ports and line-drawn upper works). `none` (with `note`)
writes `detail: none` and `detail_note`: the plate adds nothing inside the outline. `skip` (with `note`) writes
nothing: not done, and why.

    uv run tools/silhouette_detail.py run <id> [<id> ...]   trace, write the check images, don't touch the YAML
    uv run tools/silhouette_detail.py run <id> --write      ... and write `detail` into silhouettes.yml
    uv run tools/silhouette_detail.py all [--write]         every entry with a crop (or a `method` in the params)
    uv run tools/silhouette_detail.py status                which entries have detail, none, or nothing yet

Check images (the plate, the outline in red, lines in blue, fills in green) go to
sources/silhouettes/detail-check/<id>[-<view>].png. Scans are fetched once into sources/silhouettes/scans/.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

import records
from records import CACHE, RECORDS, rel

SIL = RECORDS / "silhouettes"
YML = SIL / "silhouettes.yml"
PARAMS = SIL / "detail-params.yml"
SCANS = CACHE / "silhouettes" / "scans"
CHECK = CACHE / "silhouettes" / "detail-check"
VIEWS = ("plan", "front", "profile")

# What a plate's kind usually needs, by the scan's prefix; detail-params.yml overrides any of it per entry or view.
DEFAULTS = {
    "ia:Fm30-30": {"method": "marks", "thin": 4, "edge": 10},
    "ia:oni-208-j": {"dark": 120},
    "ia:USANJOR": {"method": "marks"},
    "ibiblio:hyperwar/USN/ref/KYE/CINCPAC": {"method": "marks"},
    "ia:MerchShipRecogManual": {"method": "lines+marks", "white": 170},
    "ia:TM9-2800": {"method": "lines", "orient": "any", "min_len": 40, "inset": 8, "rules": True},
    "ia:FM_30_50": {"rules": True},
    "gbooks:Epii9ppEzeYC": {"rules": True},
}
BASE = {"method": "lines", "orient": "h", "dark": 95, "min_len": 20, "inset": 4, "white": 128, "thin": 2.0,
        "min_fill": 8, "edge": 6, "tol": 0.6, "search": 60, "rules": False, "hug": 0, "within_ink": 0,
        "max_fill": 0, "drop": []}


# ------------------------------------------------------------------ paths (no numpy: imported by the tests)
def subpaths(d: str) -> list[list[tuple[float, float]]]:
    """An M/L/Z path's subpaths as point lists."""
    out: list[list[tuple[float, float]]] = []
    for cmd, body in re.findall(r"([MLZ])([^MLZ]*)", d):
        nums = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", body)]
        if cmd == "M":
            out.append([])
        if nums:
            out[-1].extend(zip(nums[0::2], nums[1::2]))
    return out


def bbox(d: str) -> tuple[float, float, float, float]:
    pts = [p for s in subpaths(d) for p in s]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def num(v: float) -> str:
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def polyline_d(pts: list[tuple[float, float]], closed: bool = False) -> str:
    return "M" + "L".join(f"{num(x)},{num(y)}" for x, y in pts) + ("Z" if closed else "")


def solid_path(group: str, entry: dict, view: str | None) -> str:
    if group == "aircraft":
        return entry[view]["d"]
    import build_silhouettes
    return build_silhouettes.ship_path(entry["parts"])


def params_for(prm: dict, key: str, view: str | None, scan: str) -> dict:
    p = dict(BASE)
    for prefix, d in DEFAULTS.items():
        if scan.startswith(prefix):
            p.update(d)
    e = prm.get(key) or {}
    p.update({k: v for k, v in e.items() if k != "views"})
    if view:
        p.update((e.get("views") or {}).get(view) or {})
    return p


# ------------------------------------------------------------------ YAML (text edits, so the file keeps its comments)
DETAIL_IN_VIEW = re.compile(r', detail: (?:none, detail_note: "(?:[^"\\]|\\.)*"|\{ lines: "[^"]*", fills: "[^"]*" \})')


def detail_flow(detail: dict | None, note: str = "") -> str:
    """`detail` as a YAML flow value: { lines: "...", fills: "..." }, or none plus its note."""
    if detail is None:
        return f"detail: none, detail_note: {json.dumps(note)}"
    return f'detail: {{ lines: "{detail["lines"]}", fills: "{detail["fills"]}" }}'


def set_view_detail(line: str, detail: dict | None, note: str = "") -> str:
    """A view's one-line mapping (`    plan: { w: 100, ..., d: "..." }`) with its detail replaced."""
    line = DETAIL_IN_VIEW.sub("", line.rstrip("\n"))
    if not line.endswith(" }"):
        raise ValueError(f"not a one-line view mapping: {line[:60]}")
    return line[:-2] + ", " + detail_flow(detail, note) + " }\n"


def entry_span(text: str, group: str, key: str) -> tuple[int, int]:
    g = ("\n" + text).index(f"\n{group}:\n")
    m = re.compile(rf"^  {re.escape(key)}:\n", re.M).search(text, g)
    if not m:
        raise KeyError(f"{group}.{key}")
    nxt = re.compile(r"^(?:  \S|\S)", re.M).search(text, m.end())
    end = nxt.start() if nxt else len(text)
    # a comment line above the next entry belongs to it
    while True:
        prev = text.rfind("\n", 0, end - 1) + 1
        if text[prev:end].startswith("  #"):
            end = prev
        else:
            break
    return m.start(), end


def write_detail(text: str, group: str, key: str, view: str | None, detail: dict | None, note: str = "") -> str:
    a, b = entry_span(text, group, key)
    block = text[a:b]
    if view:
        m = re.compile(rf"^    {view}: \{{.*\}}\n", re.M).search(block)
        if not m:
            raise KeyError(f"{group}.{key}.{view}")
        block = block[:m.start()] + "    " + set_view_detail(m.group(0)[4:], detail, note) + block[m.end():]
    else:
        block = re.sub(r"^    detail(?:_note)?: .*\n", "", block, flags=re.M)
        new = (f"    detail: none\n    detail_note: {json.dumps(note)}\n" if detail is None
               else f'    detail: {{ lines: "{detail["lines"]}", fills: "{detail["fills"]}" }}\n')
        i = block.find("\n    crop:")
        i = i + 1 if i >= 0 else len(block.rstrip("\n")) + 1
        block = block[:i] + new + block[i:]
    return text[:a] + block + text[b:]


# ------------------------------------------------------------------ scans
def scan_image(scan: str, crop: dict):
    """The plate's scan as a grey array, as the crop's box was measured on it (served width, turned if `turn`)."""
    import numpy as np
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    kind, rest = scan.split(":", 1)
    if kind == "ia":
        ident, leaf = rest.split("/", 1)
        leaf = leaf if leaf.startswith("n") else f"n{int(leaf)}"
        path = SCANS / "ia" / ident / f"{leaf}.jpg"
        url = f"https://archive.org/download/{ident}/page/{leaf}.jpg"
    elif kind == "ibiblio":
        path = SCANS / "ibiblio" / rest
        url = f"https://www.ibiblio.org/{rest}"
    elif kind == "gbooks":
        ident, page = rest.split("/", 1)
        path = SCANS / "gbooks" / ident / f"{page}-400dpi.png"
        url = ""
        if not path.exists():
            import pymupdf
            pdfs = sorted((CACHE / "googlebooks" / ident).glob("*.pdf"))
            if not pdfs:
                raise RuntimeError(f"{scan}: no PDF in {rel(CACHE / 'googlebooks' / ident)}")
            path.parent.mkdir(parents=True, exist_ok=True)
            doc = pymupdf.open(pdfs[0])
            doc[int(page.lstrip("p")) - 1].get_pixmap(dpi=400, colorspace=pymupdf.csGRAY).save(path)
    else:
        raise RuntimeError(f"unknown scan {scan}")
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": "wwii-research-kit"})
        try:
            path.write_bytes(urllib.request.urlopen(req, timeout=120).read())
        except urllib.error.URLError:  # some hosts' certificates fail Python's store; curl uses the system's
            subprocess.run(["curl", "-sfL", "-A", "wwii-research-kit", "-o", str(path), url], check=True, timeout=180)
    im = Image.open(path).convert("L")
    if crop.get("width") and im.width != crop["width"]:
        im = im.resize((crop["width"], round(im.height * crop["width"] / im.width)), Image.Resampling.LANCZOS)
    if crop.get("turn") and abs(float(crop["turn"])) < 45:  # a scan levelled: the box is on the turned page
        centre = tuple(crop["turn_centre"]) if crop.get("turn_centre") else None
        im = im.rotate(-float(crop["turn"]), resample=Image.Resampling.BICUBIC, fillcolor=255, center=centre)
    a = np.asarray(im, dtype=float)
    if a.max() < 200:  # a bitonal scan stored with paper at 128
        a = a * (255 / max(a.max(), 1))
    return a


# ------------------------------------------------------------------ geometry
class Frame:
    """Path units to crop-local pixels: px = (x - x0) * s + dx, py = (y - y0) * s + dy."""

    def __init__(self, s: float, x0: float, y0: float, dx: float = 0, dy: float = 0):
        self.s, self.x0, self.y0, self.dx, self.dy = s, x0, y0, dx, dy

    def to_px(self, x, y):
        return (x - self.x0) * self.s + self.dx, (y - self.y0) * self.s + self.dy

    def to_unit(self, px, py):
        return (px - self.dx) / self.s + self.x0, (py - self.dy) / self.s + self.y0


def raster(d: str, frame: Frame, shape, ss: int = 3, union: bool = False):
    import numpy as np
    from PIL import Image, ImageDraw
    acc = np.zeros((shape[0] * ss, shape[1] * ss), dtype=bool)
    for sub in subpaths(d):
        if len(sub) < 3:
            continue
        m = Image.new("1", (shape[1] * ss, shape[0] * ss), 0)
        ImageDraw.Draw(m).polygon([tuple(v * ss for v in frame.to_px(x, y)) for x, y in sub], fill=1)
        if union:
            acc |= np.asarray(m, dtype=bool)
        else:
            acc ^= np.asarray(m, dtype=bool)
    im = Image.fromarray(acc.astype(np.uint8) * 255).resize((shape[1], shape[0]), Image.Resampling.BOX)
    return np.asarray(im) > 127


def locate(d: str, s: float, crop: dict, img, p: dict):
    """Cut the crop's box (padded) from the scan, mirrored as the path is, and find where the outline sits on it: the
    box places it, a correlation of the outline with the plate's ink within `search` px corrects it."""
    import numpy as np
    from scipy import signal
    bx, by, bw, bh = crop["box"]
    pad = int(p["search"]) + 12
    H, W = img.shape
    sx0, sy0 = max(0, int(bx) - pad), max(0, int(by) - pad)
    sx1, sy1 = min(W, int(bx + bw) + pad), min(H, int(by + bh) + pad)
    c = img[sy0:sy1, sx0:sx1]
    lx, ly = bx - sx0, by - sy0
    turn = float(crop.get("turn") or 0)
    if abs(turn) >= 45:  # a drawing printed sideways: the box is on the page as printed; turn the cut section
        k = -round(turn / 90) % 4  # np.rot90 turns anticlockwise
        h0, w0 = c.shape
        c = np.rot90(c, k)
        for _ in range(k):  # the box's top-left corner, carried through each anticlockwise quarter turn
            lx, ly, h0, w0 = ly, w0 - lx - bw, w0, h0
            bw, bh = bh, bw
    if crop.get("mirrored"):
        c = c[:, ::-1]
        lx = c.shape[1] - (lx + bw)
    ink = c < (128 if p["method"] == "marks" else 205)
    union = not p.get("_aircraft")  # a ship's parts overlap (masts on the hull) and are drawn as one shape
    cy, cx = np.array(c.shape) // 2
    r = int(p["search"])
    # The box is the traced outline's extent: on most ships the whole outline, on some only the hull polygon traced
    # before the masts were added back. Try both tops, keep the one the ink agrees with best; then correlate the
    # outline with the plate's ink within `search` px.
    full = bbox(d)
    tops = [full[1]] if p.get("_aircraft") else sorted({full[1], bbox(d.split("Z")[0] + "Z")[1]})
    best = None
    for y0 in tops:
        m = raster(d, Frame(s, full[0], y0, lx, ly), c.shape, ss=1, union=union).astype(float)
        corr = signal.fftconvolve((ink - ink.mean()), (m - m.mean())[::-1, ::-1], mode="same")
        win = corr[max(0, cy - r):cy + r + 1, max(0, cx - r):cx + r + 1]
        iy, ix = np.unravel_index(np.argmax(win), win.shape)
        if best is None or win[iy, ix] > best[0]:
            best = (win[iy, ix], y0, iy - min(r, cy), ix - min(r, cx))
    assert best is not None
    _, y0, dy, dx = best
    if p.get("offset"):  # an offset fixed by hand where the correlation drifts (an outline cut at a waterline)
        dx, dy = (int(v) for v in p["offset"])
        r = max(r, abs(dx) + 1, abs(dy) + 1)
    x0 = full[0]
    frame = Frame(s, x0, y0, lx + dx, ly + dy)
    sil = raster(d, frame, c.shape, union=union)
    iou = (sil & ink).sum() / max((sil | ink).sum(), 1)
    at_limit = abs(dx) >= r or abs(dy) >= r
    return c, sil, frame, (int(dx), int(dy)), float(iou), at_limit


# ------------------------------------------------------------------ vectorising
def trace_skeleton(mask):
    """Skeleton pixels into polylines of (row, col), walked from ends and junctions."""
    import numpy as np
    from skimage.morphology import skeletonize
    sk = skeletonize(mask)
    pts = set(zip(*(v.tolist() for v in np.nonzero(sk))))
    nb = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]

    def neigh(q):
        return [(q[0] + a, q[1] + b) for a, b in nb if (q[0] + a, q[1] + b) in pts]

    deg = {q: len(neigh(q)) for q in pts}
    seen: set = set()
    lines = []
    for s0 in [q for q in pts if deg[q] != 2] + sorted(pts):
        for n in neigh(s0):
            e = frozenset((s0, n))
            if e in seen:
                continue
            seen.add(e)
            line, prev, cur = [s0, n], s0, n
            while deg[cur] == 2:
                nxt = [q for q in neigh(cur) if q != prev]
                if not nxt or frozenset((cur, nxt[0])) in seen:
                    break
                seen.add(frozenset((cur, nxt[0])))
                prev, cur = cur, nxt[0]
                line.append(cur)
            lines.append(line)
    return lines


def join_ends(lines, gap: float = 2.5):
    """Join polylines whose ends meet (the skeleton breaks a line at every junction): greedily, nearest ends first."""
    import numpy as np
    from scipy.spatial import KDTree
    lines = [list(ln) for ln in lines if len(ln) > 1]
    while len(lines) > 1:
        ends = np.array([q for ln in lines for q in (ln[0], ln[-1])], float)
        pairs = sorted(KDTree(ends).query_pairs(gap, output_type="ndarray").tolist(),
                       key=lambda ij: float(np.hypot(*(ends[ij[0]] - ends[ij[1]]))))
        pairs = [(i, j) for i, j in pairs if i // 2 != j // 2]
        if not pairs:
            break
        used: set = set()
        merged = []
        for i, j in pairs:
            li, lj = i // 2, j // 2
            if li in used or lj in used:
                continue
            a = lines[li] if i % 2 else lines[li][::-1]  # a ends at end i
            b = lines[lj][::-1] if j % 2 else lines[lj]  # b starts at end j
            merged.append(a + b[1:])
            used |= {li, lj}
        lines = [ln for k, ln in enumerate(lines) if k not in used] + merged
    return lines


def merge_runs(lines, row_tol: float = 2.5, gap: int = 16):
    """The broken pieces of one drawn line along the hull (window frames and stipple cross it): pieces at the same
    height, end to end within `gap` px, become one line."""
    import numpy as np
    pieces = sorted((sorted(ln, key=lambda q: q[1]) for ln in lines if len(ln) > 1), key=lambda ln: ln[0][1])
    out: list = []
    for ln in pieces:
        r = float(np.mean([q[0] for q in ln]))
        for o in out:
            if abs(float(np.mean([q[0] for q in o[-6:]])) - r) <= row_tol and -2 <= ln[0][1] - o[-1][1] <= gap:
                o.extend(q for q in ln if q[1] > o[-1][1])
                break
        else:
            out.append(list(ln))
    return out


def length_px(ln) -> float:
    import numpy as np
    a = np.asarray(ln, float)
    return float(np.hypot(*np.diff(a, axis=0).T).sum()) if len(a) > 1 else 0.0


def drop_small(mask, min_px: int):
    import numpy as np
    from scipy import ndimage as ndi
    lab, n = ndi.label(mask)
    if n == 0:
        return mask
    sizes = ndi.sum(mask, lab, range(1, n + 1))
    return np.isin(lab, 1 + np.nonzero(np.asarray(sizes) >= min_px)[0])


def ink_lines(c, sil, p):
    import numpy as np
    from scipy import ndimage as ndi
    fine = ndi.gaussian_filter(c, 1.0)
    dark = (fine < p["dark"]) & ndi.binary_erosion(sil, iterations=int(p["inset"]))
    n = int(p["min_len"])
    if p.get("rules"):  # the plate's height rules or dimension lines: thin dark runs that carry on outside the outline
        allink = fine < p["dark"]
        runs = ndi.binary_opening(allink, structure=np.ones((1, n))) | ndi.binary_opening(allink, structure=np.ones((n, 1)))
        lab, _k = ndi.label(runs)
        outside = ~ndi.binary_dilation(sil, iterations=3)
        hit = np.unique(lab[runs & outside])
        rules = np.isin(lab, hit[hit > 0])
        dark &= ~ndi.binary_dilation(rules, iterations=1)
    if p["orient"] == "h":
        run = ndi.binary_opening(dark, structure=np.ones((1, n)))
        run = ndi.binary_dilation(run, structure=np.ones((1, 5))) & dark
        lines = [ln for ln in merge_runs(trace_skeleton(run)) if length_px(ln) >= 1.5 * n]
    else:
        dark = drop_small(dark, n)
        lines = [ln for ln in join_ends(trace_skeleton(dark)) if length_px(ln) >= n]
    return [ln for ln in lines if not hugs(ln, sil, p)]


def hugs(ln, sil, p) -> bool:
    """A line that only doubles the outline (a keel or edge line drawn just inside it): most of it lies within `hug` px
    of the outline's edge."""
    import numpy as np
    from scipy import ndimage as ndi
    if not p.get("hug"):
        return False
    key = id(sil)
    if p.get("_dist_key") != key:
        p["_dist"], p["_dist_key"] = ndi.distance_transform_edt(sil), key
    dist = p["_dist"]
    a = np.asarray(ln, int)
    return float(np.median(dist[a[:, 0], a[:, 1]])) <= float(p["hug"])


def white_marks(c, sil, p):
    import numpy as np
    from scipy import ndimage as ndi
    white = (c > p["white"]) & ndi.binary_erosion(sil, iterations=max(1, int(p["inset"]) - 1))
    if p.get("within_ink"):  # only white enclosed by the plate's ink (ports in a black hull), not the paper of line-drawn works
        ink = ndi.binary_closing(c < 128, structure=np.ones((3, 3)), iterations=int(p["within_ink"]))
        white &= ink
    white = drop_small(white, 5)
    lab, n = ndi.label(white)
    dt = ndi.distance_transform_edt(white)
    thin = np.zeros_like(white)
    areas = np.zeros_like(white)
    # a white sliver along the edge is where the outline (closed, or mirrored for a symmetric view) runs a little
    # outside the plate's ink, not a mark: drop marks lying mostly within `edge` px of the outline
    band = sil & ~ndi.binary_erosion(sil, iterations=int(p["edge"]))
    for i in range(1, n + 1):
        comp = lab == i
        if (comp & band).sum() > 0.5 * comp.sum():
            continue
        if p.get("max_fill") and comp.sum() > int(p["max_fill"]):
            continue
        if dt[comp].max() <= float(p["thin"]):
            if comp.sum() >= 10:
                if (np.ptp(np.nonzero(comp)[0]) + np.ptp(np.nonzero(comp)[1])) >= max(8, int(p["min_len"]) // 2):
                    thin |= comp
                elif comp.sum() >= int(p["min_fill"]):  # a small pane: too short to be a line, kept as a fill
                    areas |= comp
        elif comp.sum() >= int(p["min_fill"]):
            areas |= ndi.binary_closing(comp, iterations=1) if comp.sum() >= 300 else comp
    lines = [ln for ln in join_ends(trace_skeleton(thin)) if length_px(ln) >= max(8, int(p["min_len"]) // 2)]
    return lines, areas


def to_path_lines(lines, frame: Frame, tol: float) -> list[list[tuple[float, float]]]:
    import numpy as np
    from skimage.measure import approximate_polygon
    out = []
    for ln in lines:
        a = np.asarray(ln, float)
        if len(a) > 4:  # a light running mean drops the scan's one-pixel stair steps
            k = 2
            a = np.vstack([a[:1], np.array([a[max(0, i - k):i + k + 1].mean(0) for i in range(1, len(a) - 1)]),
                           a[-1:]])
        a = approximate_polygon(a, tolerance=tol)
        out.append([frame.to_unit(col + 0.5, row + 0.5) for row, col in a])
    return out


def to_path_fills(mask, frame: Frame, tol: float) -> list[list[tuple[float, float]]]:
    import numpy as np
    from skimage.measure import approximate_polygon, find_contours
    out = []
    for c in find_contours(np.pad(mask, 1).astype(float), 0.5):
        if len(c) < 4:
            continue
        c = approximate_polygon(c, tolerance=tol)
        out.append([frame.to_unit(col - 1 + 0.5, row - 1 + 0.5) for row, col in c])
    return out


def in_drop(pts, drops) -> bool:
    """Most of a line's points lie in one of the rectangles."""
    if not drops:
        return False
    return any(sum(x0 <= x <= x1 and y0 <= y <= y1 for x, y in pts) > len(pts) / 2 for x0, y0, x1, y1 in drops)


def cut_drops(mask, frame: Frame, drops):
    """Clear the rectangles from a mask (so a ring and its hole go together)."""
    for x0, y0, x1, y1 in drops or []:
        (c0, r0), (c1, r1) = frame.to_px(x0, y0), frame.to_px(x1, y1)
        r0, r1 = sorted((int(r0), int(r1) + 1))
        c0, c1 = sorted((int(c0), int(c1) + 1))
        mask[max(0, r0):max(0, r1), max(0, c0):max(0, c1)] = False
    return mask


# ------------------------------------------------------------------ one silhouette
def targets(y: dict, prm: dict, only: set | None = None):
    for group in ("ships", "aircraft", "vehicles"):
        for key, e in (y.get(group) or {}).items():
            if only and key not in only:
                continue
            views = [v for v in VIEWS if v in e] if group == "aircraft" else [None]
            for view in views:
                crop = e.get("crop") or {}
                if view:
                    crop = crop.get(view) or {}
                yield group, key, view, e, crop


def run_one(group, key, view, e, crop, prm, write_check=True):
    """Returns ("detail", {lines, fills}, report) | ("none", note, report) | ("skip", note, report)."""
    scan = crop.get("scan", "")
    p = params_for(prm, key, view, scan)
    if p["method"] in ("none", "skip"):
        return p["method"], p.get("note", ""), ""
    if not crop:
        return "skip", p.get("note") or "no crop: the outline was not traced from a scan, so the plate's marks cannot be placed", ""
    import numpy as np
    from PIL import Image
    d = solid_path(group, e, view)
    x0, _y0, x1, _y1 = bbox(d)
    s = crop["box"][2] / (x1 - x0) if group == "aircraft" else float(p.get("px_per_unit") or crop["px_per_ft"])
    p["_aircraft"] = group == "aircraft"
    img = scan_image(scan, crop)
    c, sil, frame, off, iou, at_limit = locate(d, s, crop, img, p)
    if at_limit:  # the true place lies outside the search: anything traced here would be off the drawing
        return "limit", None, f"offset {off} at the search limit ({p['search']} px): widen `search` or fix the box"
    lines, fills = [], np.zeros_like(sil)
    if "lines" in p["method"]:
        lines += ink_lines(c, sil, p)
    if "marks" in p["method"]:
        ml, fills = white_marks(c, sil, p)
        lines += ml
    tol = float(p["tol"])
    pl = [q for q in to_path_lines(lines, frame, tol) if not in_drop(q, p["drop"])]
    pf = to_path_fills(cut_drops(fills, frame, p["drop"]), frame, tol)
    detail = {"lines": "".join(polyline_d(q) for q in pl), "fills": "".join(polyline_d(q, True) for q in pf)}
    report = f"offset {off}, overlap {iou:.2f}, {len(pl)} lines, {len(pf)} fills"
    if write_check:
        from scipy import ndimage as ndi
        CHECK.mkdir(parents=True, exist_ok=True)
        rgb = np.stack([np.clip(c, 0, 255)] * 3, -1).astype(np.uint8)
        rgb[sil & ~ndi.binary_erosion(sil)] = (230, 0, 0)
        if fills.any():
            rgb[fills] = (rgb[fills] * 0.4 + np.array([0, 200, 80]) * 0.6).astype(np.uint8)
        from PIL import ImageDraw
        im = Image.fromarray(rgb)
        dr = ImageDraw.Draw(im)
        for q in pl:
            dr.line([frame.to_px(x, yv) for x, yv in q], fill=(0, 90, 255), width=1)
        k = 2 if max(c.shape) < 1400 else 1
        name = f"{key}{'-' + view if view else ''}"
        im.resize((im.width * k, im.height * k), Image.Resampling.NEAREST).save(CHECK / f"{name}.png")
        # and as the detailed silhouette will look: solid ink, the lines and fills in paper
        r = Image.fromarray(np.where(sil, 27, 255).astype(np.uint8)).convert("RGB")
        dr = ImageDraw.Draw(r)
        lw = max(1, round(min(c.shape) / 220))
        hole = np.zeros(sil.shape, dtype=bool)  # the fills even-odd, as the path is drawn
        for q in pf:
            m = Image.new("1", (sil.shape[1], sil.shape[0]), 0)
            ImageDraw.Draw(m).polygon([frame.to_px(x, yv) for x, yv in q], fill=1)
            hole ^= np.asarray(m, dtype=bool)
        arr = np.asarray(r).copy()
        arr[hole] = 255
        r = Image.fromarray(arr)
        dr = ImageDraw.Draw(r)
        for q in pl:
            dr.line([frame.to_px(x, yv) for x, yv in q], fill=(255, 255, 255), width=lw)
        r.save(CHECK / f"{name}-detailed.png")
    if not pl and not pf:
        return "empty", detail, report
    return "detail", detail, report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=("run", "all", "status"))
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--write", action="store_true", help="write the result into silhouettes.yml")
    ap.add_argument("--params", action="append", default=[], help="another params file, laid over detail-params.yml")
    a = ap.parse_args(argv)
    y = records.load_yaml(YML)
    prm = (records.load_yaml(PARAMS) if PARAMS.exists() else None) or {}
    for extra in a.params:
        for k, v in ((records.load_yaml(Path(extra)) or {}).items()):
            prm[k] = v
    if a.cmd == "status":
        done = none = todo = 0
        for group, key, view, e, _crop in targets(y, prm):
            v = (e[view] if view else e).get("detail")
            label = f"{group}.{key}{'.' + view if view else ''}"
            if v is None:
                todo += 1
                print(f"  not done  {label}")
            elif v == "none":
                none += 1
            else:
                done += 1
        print(f"{done} with detail, {none} none, {todo} not done")
        return
    only = set(a.ids) if a.cmd == "run" else None
    if a.cmd == "run" and not only:
        raise SystemExit("run: name the entries")
    text = YML.read_text()
    for group, key, view, e, crop in targets(y, prm, only):
        label = f"{group}.{key}{'.' + view if view else ''}"
        try:
            kind, val, report = run_one(group, key, view, e, crop, prm)
        except Exception as ex:  # one bad scan shouldn't stop a batch
            print(f"  ERROR {label}: {ex}")
            continue
        print(f"  {kind:6} {label}: {report or val}")
        if not a.write:
            continue
        if kind == "detail":
            text = write_detail(text, group, key, view, val)
        elif kind == "none":
            text = write_detail(text, group, key, view, None, val)
        elif kind == "empty":
            p = params_for(prm, key, view, crop.get("scan", ""))
            text = write_detail(text, group, key, view, None, p.get("note") or "the plate draws nothing inside the outline")
    if a.write:
        YML.write_text(text)
        print(f"wrote {rel(YML)}")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()
