"""The grid section: how a unit's typed grid reference finds its place, from the grid's lettered 100 km squares down to
the hundred metres a six-figure reference names.

Two figures, both drawn from the kit's own definition of each grid (tools/grid_ref.py: the projection, its false
origin, the lettering of its 100 km squares) and the worked cases in book/grids/cases.yml:

- **zones**: the larger grid. Western Europe and North Africa with each grid's 100 km squares, lettered as the kit
  letters them, drawn over the ground the records' references fall on (not the zones' official limits), and every
  grid-referenced station in the Army records as a dot of its grid's colour.
- **ladder**: one reference read down in four steps, each drawn in the grid's own metres, so its squares are square:
  the 500 km block and its lettered squares; the 100 km square and its 10 km lines; the 10 km square on the period
  sheet the unit worked from (resampled into the grid, its printed grid lines under ours); and the 1 km square, where
  a six-figure reference's tenths are estimated. A reference typed with the wrong letter is drawn twice: as typed,
  hatched, and as read.

Nothing here is stored: every square, letter and point is computed each time from tools/grid_ref.py.
"""
import base64
import csv
import importlib.util
import io
import json
import math
from functools import cache
from html import escape

import numpy as np
import yaml
from PIL import Image
from pyproj import Transformer
from scipy import ndimage

from . import cartography as carto
from . import geo, halo, paths

DISPLAY = carto.DISPLAY
TYPED = "Courier Prime"
INK, MUTED, RULE, ACCENT, PAPER = "#000000", "#5d675b", "#c4cbbf", "#a3241b", "#fbfaf6"
CASES = paths.KIT / "book" / "grids" / "cases.yml"


@cache
def _gr():
    """The kit's tools/grid_ref.py, imported from where the kit keeps it (it is a script, not a package)."""
    spec = importlib.util.spec_from_file_location("grid_ref", paths.KIT / "tools" / "grid_ref.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@cache
def config() -> dict:
    return yaml.safe_load(CASES.read_text())


@cache
def _to_grid(system: str) -> Transformer:
    """lon/lat to the grid's metres, as tools/grid_ref.py defines the grid (one standard parallel, no datum shift)."""
    gr = _gr()
    _name, ell, lat0, lon0, k0, fe, fn, *_ = gr.GRIDS[system]
    a, f = gr.ELLIPSOIDS[ell]
    crs = (f"+proj=lcc +lat_1={lat0} +lat_0={lat0} +lon_0={lon0} +k_0={k0} +x_0={fe} +y_0={fn} "
           f"+a={a} +rf={1 / f} +units=m +no_defs")
    return Transformer.from_crs("EPSG:4326", crs, always_xy=True)


@cache
def _to_lonlat(system: str) -> Transformer:
    return Transformer.from_crs(_to_grid(system).target_crs, "EPSG:4326", always_xy=True)


def _letter(system: str, x: float, y: float) -> str | None:
    """The 100 km square's letter(s) at grid metres (x, y), as tools/grid_ref.py letters them; None outside the
    lettered block."""
    gr = _gr()
    spec = config()["grids"][system]["letters"]
    if spec == "repeat":
        col, row = int(x // 1e5) % 5, int(y // 1e5) % 5
        return gr.MINOR[(4 - row) * 5 + col]
    x0, y0 = spec["block"]
    col, row = int((x - x0) // 1e5), int((y - y0) // 1e5)
    if not (0 <= col < 5 and 0 <= row < 5):
        return None
    return spec.get("prefix", "") + gr.MINOR[(4 - row) * 5 + col]


def _block(system: str, x: float, y: float) -> tuple[float, float]:
    """The south-west corner of the 500 km block holding (x, y)."""
    spec = config()["grids"][system]["letters"]
    if spec == "repeat":
        return math.floor(x / 5e5) * 5e5, math.floor(y / 5e5) * 5e5
    return tuple(spec["block"])


def _point(case: dict, ref: str | None = None) -> dict:
    """A case's reference (or another spelling of it) on its grid: lon/lat, grid metres, the cell it names."""
    near = tuple(case["near"]) if case.get("near") else None
    d = _gr().decode(case["grid"], ref or case["ref"], near=near)
    x, y = _to_grid(case["grid"]).transform(d["lon"], d["lat"])
    return {**d, "x": float(x), "y": float(y)}


def _text(x, y, s, size=6.4, fill=INK, anchor="start", weight="normal", family=DISPLAY, italic=False, halo_=True):
    it = ' font-style="italic"' if italic else ""
    h = (' stroke="#ffffff" stroke-width="2.2" stroke-linejoin="round" paint-order="stroke"' if halo_ else "")
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{family}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}" font-weight="{weight}"{it}{h}>{escape(s)}</text>')


def _stations() -> list[dict]:
    """Every station row in the Army records that gives a grid reference on a grid the section draws, at the kit's
    placing of it (army.json): the dots on the large map."""
    grids = config()["grids"]
    rows = []
    with open(paths.records() / "army" / "stations.csv", newline="") as fh:
        for r in csv.DictReader(fh):
            if r.get("grid_on") in grids and r.get("grid"):
                rows.append(r)
    placed = {}
    for u in json.loads((paths.records() / "army" / "army.json").read_text())["units"]:
        for s in u.get("stations", []):
            placed[(u["unit"], s["date"], s.get("page", ""))] = (s.get("lon"), s.get("lat"))
    out = []
    for r in rows:
        lon, lat = placed.get((r["unit"], r["date"], r["page"]), (None, None))
        if lon is None:
            continue
        out.append({"unit": r["unit"], "date": r["date"], "grid": r["grid"], "on": r["grid_on"], "lon": lon,
                    "lat": lat, "page": r["page"]})
    return out


# ---------------------------------------------------------------- the larger grid

def zones(width_in: float = 7.2) -> tuple[str, dict]:
    cfg = config()
    W = width_in * 72
    w, s, e, n = (float(v) for v in cfg["map"]["box"])
    f = geo.fit((w, s, e, n), W, pad=0.0)
    H = f.height
    labels = carto.Labels((0, 0, W, H))
    under, over = carto.base(f, 0, H, rivers=3, places=tuple(cfg["map"].get("places", ())), labels=labels)
    body = [f'<defs><clipPath id="gz"><rect width="{W:.1f}" height="{H:.1f}"/></clipPath></defs>'
            f'<g clip-path="url(#gz)">'] + list(under)
    letters_svg = []
    for system, g in cfg["grids"].items():
        col = g["colour"]
        gw, gs, ge, gn = (float(v) for v in g["box"])
        tg = _to_grid(system)
        tl = _to_lonlat(system)
        lon = np.r_[np.linspace(gw, ge, 60), np.full(60, ge), np.linspace(ge, gw, 60), np.full(60, gw)]
        lat = np.r_[np.full(60, gs), np.linspace(gs, gn, 60), np.full(60, gn), np.linspace(gn, gs, 60)]
        X, Y = tg.transform(lon, lat)
        x0, x1 = math.floor(min(X) / 1e5) * 1e5, math.ceil(max(X) / 1e5) * 1e5
        y0, y1 = math.floor(min(Y) / 1e5) * 1e5, math.ceil(max(Y) / 1e5) * 1e5
        spec = g["letters"]

        def inside_block(x, y):
            if spec == "repeat":
                return np.ones_like(np.asarray(x), dtype=bool)
            bx, by = spec["block"]
            return (np.asarray(x) >= bx - 1) & (np.asarray(x) <= bx + 5e5 + 1) & \
                   (np.asarray(y) >= by - 1) & (np.asarray(y) <= by + 5e5 + 1)

        def line(xs, ys, heavy):
            lo, la = tl.transform(xs, ys)
            lo, la = np.asarray(lo), np.asarray(la)
            ok = (lo >= gw) & (lo <= ge) & (la >= gs) & (la <= gn) & inside_block(xs, ys)
            segs, cur = [], []
            for k in range(len(lo)):
                if ok[k]:
                    cur.append(f.xy(float(lo[k]), float(la[k])))
                elif cur:
                    segs.append(cur)
                    cur = []
            if cur:
                segs.append(cur)
            for sg in segs:
                if len(sg) < 2:
                    continue
                d = "M" + " L".join(f"{a:.1f},{b:.1f}" for a, b in sg)
                body.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{1.3 if heavy else 0.5}" '
                            f'stroke-opacity="{0.95 if heavy else 0.7}"/>')

        def heavy_at(v, axis):
            if spec == "repeat":
                return abs(v / 5e5 - round(v / 5e5)) < 1e-9
            b = spec["block"][0 if axis == "x" else 1]
            return abs(v - b) < 1 or abs(v - b - 5e5) < 1
        for xv in np.arange(x0, x1 + 1, 1e5):
            ys = np.linspace(y0, y1, 200)
            line(np.full_like(ys, xv), ys, heavy_at(xv, "x"))
        for yv in np.arange(y0, y1 + 1, 1e5):
            xs = np.linspace(x0, x1, 200)
            line(xs, np.full_like(xs, yv), heavy_at(yv, "y"))
        # the letters, at each square's centre inside the box
        for xv in np.arange(x0, x1, 1e5):
            for yv in np.arange(y0, y1, 1e5):
                cx, cy = xv + 5e4, yv + 5e4
                lt = _letter(system, cx, cy)
                if not lt:
                    continue
                lo, la = tl.transform(cx, cy)
                if not (gw <= lo <= ge and gs <= la <= gn):
                    continue
                px, py = f.xy(lo, la)
                letters_svg.append(f'<text x="{px:.1f}" y="{py + 3:.1f}" font-family="{DISPLAY}" font-size="8.4" '
                                   f'font-weight="bold" fill="{col}" fill-opacity="0.8" text-anchor="middle" '
                                   f'stroke="#ffffff" stroke-width="2" stroke-opacity="0.8" paint-order="stroke">'
                                   f'{lt}</text>')
                labels.occupy(px - 6, py - 6, 12, 12)
    body += letters_svg
    # every grid-referenced station in the Army records
    for st in _stations():
        x, y = f.xy(st["lon"], st["lat"])
        body.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="1.7" fill="{cfg["grids"][st["on"]]["colour"]}" '
                    f'stroke="#ffffff" stroke-width="0.6"/>')
    # the worked cases, ringed
    for case in cfg["cases"].values():
        p = _point(case)
        x, y = f.xy(p["lon"], p["lat"])
        col = cfg["grids"][case["grid"]]["colour"]
        body.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="none" stroke="#ffffff" stroke-width="3"/>'
                    f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="none" stroke="{INK}" stroke-width="1.3"/>')
        labels.occupy(x - 8, y - 8, 16, 16)
        body.append(labels.place(x, y, [(case["ref"], 8, INK, "bold", DISPLAY),
                                        (case["title"], 6.4, INK, "normal", DISPLAY)], force=True, gap=8))
        if case.get("slip"):
            q = _point(case, case["slip"]["typed"])
            qx, qy = f.xy(q["lon"], q["lat"])
            body.append(f'<circle cx="{qx:.1f}" cy="{qy:.1f}" r="4" fill="none" stroke="{ACCENT}" stroke-width="1.2" '
                        f'stroke-dasharray="2 1.4"/>')
            body.append(f'<path d="M{qx:.1f},{qy + 4:.1f} L{x:.1f},{y - 6:.1f}" stroke="{ACCENT}" stroke-width="0.8" '
                        f'stroke-dasharray="2 1.4"/>')
            body.append(_text(qx + 7, qy + 2, f"{case['slip']['typed']} as typed", 6.4, ACCENT, weight="bold"))
    body += over
    body.append("</g>")
    # the key, in the Atlantic
    kx, ky = f.xy(-9.2, 46.6)
    body.append(f'<rect x="{kx - 4:.1f}" y="{ky - 10:.1f}" width="150" height="{22 + 30 * len(cfg["grids"]):.1f}" '
                f'fill="#ffffff" fill-opacity="0.88" stroke="{RULE}" stroke-width="0.5"/>')
    body.append(_text(kx, ky, "THE GRIDS THE RECORDS USE", 6.8, INK, weight="bold", halo_=False))
    yy = ky + 13
    for g in cfg["grids"].values():
        body.append(f'<rect x="{kx:.1f}" y="{yy - 6:.1f}" width="14" height="9" fill="none" stroke="{g["colour"]}" '
                    f'stroke-width="1.2"/><text x="{kx + 7:.1f}" y="{yy + 1:.1f}" font-family="{DISPLAY}" '
                    f'font-size="6.5" font-weight="bold" fill="{g["colour"]}" text-anchor="middle">A</text>')
        body.append(_text(kx + 20, yy, g["name"], 6.6, g["colour"], weight="bold", halo_=False))
        words = g["note"]
        cut = words.rfind(";", 0, 70)
        body.append(_text(kx + 20, yy + 8, words[:cut] if cut > 0 else words[:68], 5.5, MUTED, halo_=False))
        if cut > 0:
            body.append(_text(kx + 20, yy + 15, words[cut + 2:], 5.5, MUTED, halo_=False))
        yy += 30
    body.append(_text(kx, yy, "Lettered 100 km squares; heavy lines bound 500 km blocks.", 5.6, MUTED,
                      italic=True, halo_=False))
    body.append(_text(kx, yy + 7.5, "Dots: every station the Army records give by grid.", 5.6, MUTED,
                      italic=True, halo_=False))
    body.append(f'<rect width="{W:.1f}" height="{H:.1f}" fill="none" stroke="{INK}" stroke-width="0.6"/>')
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.1f}pt" height="{H:.1f}pt" viewBox="0 0 {W:.1f} '
           f'{H:.1f}">{"".join(body)}</svg>')
    notes = {"grids": {k: g["name"] for k, g in cfg["grids"].items()}, "stations": len(_stations()),
             "definition": "tools/grid_ref.py"}
    return halo.split(svg), notes


# ---------------------------------------------------------------- one reference, read down

def _sampler(case: dict):
    """A function from lon/lat arrays to RGB (H, W, 3) arrays, sampling the period map the case names."""
    m = case["map"]
    if m["kind"] == "gsgs":
        from .atlas import gsgs
        pl = gsgs.Placed(gsgs.sheet(m["series"], str(m["sheet"])))
        src = pl.rgb

        def to_px(lon, lat):
            return pl.pixel(lon, lat)
        credit = f"{gsgs.series(m['series'])['series']} sheet {m['sheet']} ({pl.sd.name}), as scanned"
    else:
        from .atlas import sources
        z = int(m.get("z", 14))
        state: dict = {}

        def to_px(lon, lat):
            tx, ty = sources.txy(lon, lat, z)
            return (np.asarray(tx) - state["tx0"]) * 256, (np.asarray(ty) - state["ty0"]) * 256
        credit = "IGN SCAN 50, 1950 series (the nearest edition to the war online)"

        def prime(box):
            rgb, (tx0, ty0, _) = sources.scan50(box, z)
            state.update(rgb=rgb, tx0=tx0, ty0=ty0)
        state["prime"] = prime
        src = None

    def sample(lon, lat, box=None):
        nonlocal src
        if src is None or m["kind"] != "gsgs":
            state["prime"](box)
            src = state["rgb"]
        x, y = to_px(lon.ravel(), lat.ravel())
        out = np.stack([ndimage.map_coordinates(src[..., k], [np.asarray(y), np.asarray(x)], order=1,
                                                mode="constant", cval=255) for k in range(3)], -1)
        return out.reshape(lon.shape + (3,)).astype(np.uint8)
    return sample, credit


def _raster(case, sample, x0, y0, L, P, dpi=300) -> str:
    """The period map over the grid window (x0, y0, side L metres), resampled into the grid at `dpi`, as an <image>."""
    n = int(P / 72 * dpi)
    xs = x0 + (np.arange(n) + 0.5) / n * L
    ys = y0 + L - (np.arange(n) + 0.5) / n * L
    X, Y = np.meshgrid(xs, ys)
    lon, lat = _to_lonlat(case["grid"]).transform(X, Y)
    lon, lat = np.asarray(lon), np.asarray(lat)
    box = (float(lon.min()) - 0.01, float(lat.min()) - 0.01, float(lon.max()) + 0.01, float(lat.max()) + 0.01)
    rgb = sample(lon, lat, box)
    im = Image.fromarray(rgb)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=88)
    return (f'<image width="{P:.1f}" height="{P:.1f}" preserveAspectRatio="none" '
            f'href="data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}"/>')


def _coast(system, x0, y0, L, P) -> str:
    tg = _to_grid(system)
    tl = _to_lonlat(system)
    lo, la = tl.transform([x0, x0 + L, x0, x0 + L], [y0, y0, y0 + L, y0 + L])
    box = (min(lo) - 1, min(la) - 1, max(lo) + 1, max(la) + 1)
    out = []
    for ring in geo.land_rings(box):
        xs, ys = tg.transform([p[0] for p in ring], [p[1] for p in ring])
        pts = [((x - x0) / L * P, (y0 + L - y) / L * P) for x, y in zip(xs, ys)]
        if not any(-P < a < 2 * P and -P < b < 2 * P for a, b in pts):
            continue
        d = "M" + " L".join(f"{a:.1f},{b:.1f}" for a, b in pts) + " Z"
        out.append(f'<path d="{d}" fill="#eeece4" stroke="#8d9a8f" stroke-width="0.5"/>')
    return f'<rect width="{P:.1f}" height="{P:.1f}" fill="#dfe8ec"/>' + "".join(out)


def ladder(case_id: str, width_in: float = 7.2, columns: int = 2) -> tuple[str, dict]:
    """`columns`: 4, the steps in a row; 2, two rows of two, each panel twice the size."""
    cfg = config()
    case = cfg["cases"][case_id]
    system = case["grid"]
    g = cfg["grids"][system]
    col = g["colour"]
    p = _point(case)
    slip = _point(case, case["slip"]["typed"]) if case.get("slip") else None
    gr = _gr()
    letters, digits = gr.parse(case["ref"])
    k = len(digits) // 2
    unit = 10 ** (5 - k)                                   # metres per last figure
    W = width_in * 72
    gap = 22.0 if columns == 2 else 12.0
    P = (W - (columns - 1) * gap) / columns
    top = 26.0
    row_h = P + 46.0
    sample, credit = _sampler(case)
    # the windows: the 500 km block, the 100 km square, the 10 km square, the 1 km square (or the 2 km round the
    # kilometre a four-figure reference names)
    bx, by = _block(system, p["x"], p["y"])
    sx, sy = math.floor(p["x"] / 1e5) * 1e5, math.floor(p["y"] / 1e5) * 1e5
    tx, ty = math.floor(p["x"] / 1e4) * 1e4, math.floor(p["y"] / 1e4) * 1e4
    kx, ky = math.floor(p["x"] / 1e3) * 1e3, math.floor(p["y"] / 1e3) * 1e3
    last = (kx, ky, 1000.0) if unit < 1000 else (kx - 500, ky - 500, 2000.0)
    wins = [(bx, by, 5e5), (sx, sy, 1e5), (tx, ty, 1e4), last]
    e_km, n_km = int(digits[:k][:2]), int(digits[k:][:2])
    letter = letters[-1]
    heads = [
        (f"1  The 100 km square: {letters}", "one of 25 in its 500 km block"),
        (f"2  The 10 km square: {digits[0]}, {digits[k]}", "the first figure of each half"),
        (f"3  The 1 km square: {e_km:02d}, {n_km:02d}", "the sheet's own grid figures"),
        ((f"4  The tenths: {digits[2]}, {digits[k + 2]}" if unit < 1000 else "4  The kilometre square"),
         ("estimated, east then north" if unit < 1000 else "a four-figure reference names the whole square")),
    ]
    body = []
    for i, (x0, y0, L) in enumerate(wins):
        ox = (i % columns) * (P + gap)
        oy = top + (i // columns) * row_h
        sc = P / L

        def at(x, y, x0=x0, y0=y0, L=L):
            return (x - x0) / L * P, (y0 + L - y) / L * P
        panel = [f'<clipPath id="lad{case_id}{i}"><rect width="{P:.1f}" height="{P:.1f}"/></clipPath>',
                 f'<g clip-path="url(#lad{case_id}{i})">']
        if i < 2:
            panel.append(_coast(system, x0, y0, L, P))
        else:
            panel.append(_raster(case, sample, x0, y0, L, P))
        step = L / (5 if i == 0 else 10)
        # the square the next panel draws, filled
        nx0, ny0, nL = wins[i + 1] if i < 3 else (kx, ky, 1000.0)
        if i < 3 or unit >= 1000:
            ax, ay = at(nx0, ny0 + nL)
            panel.append(f'<rect x="{ax:.1f}" y="{ay:.1f}" width="{nL * sc:.1f}" height="{nL * sc:.1f}" '
                         f'fill="{col}" fill-opacity="{0.22 if i < 2 else 0.0}" stroke="{col}" stroke-width="2"/>')
        # the slip: the square as typed, hatched, in the block's panel
        if slip and i == 0:
            qx, qy = math.floor(slip["x"] / 1e5) * 1e5, math.floor(slip["y"] / 1e5) * 1e5
            ax, ay = at(qx, qy + 1e5)
            panel.append(f'<pattern id="slip{case_id}" width="4" height="4" patternUnits="userSpaceOnUse" '
                         f'patternTransform="rotate(45)"><path d="M0,0 v4" stroke="{ACCENT}" stroke-width="1"/>'
                         f'</pattern><rect x="{ax:.1f}" y="{ay:.1f}" width="{1e5 * sc:.1f}" height="{1e5 * sc:.1f}" '
                         f'fill="url(#slip{case_id})" stroke="{ACCENT}" stroke-width="1.4" stroke-dasharray="3 1.6"/>')
        # the grid lines: on the period map, thin and see-through, so the sheet's own printed lines show under them
        on_map = i >= 2
        sw, so = (0.6, 0.55) if on_map else (0.7, 1.0)
        if i == 3 and unit < 1000:
            sw, so = 0.4, 0.35                             # the tenths: an estimating lattice, not printed lines
        for j in range(int(round(L / step)) + 1):
            v = x0 + j * step
            a, _ = at(v, y0)
            heavy = i == 0 and j in (0, 5)
            w_ = 1.3 if heavy else sw
            panel.append(f'<path d="M{a:.1f},0 V{P:.1f}" stroke="{col}" stroke-width="{w_}" stroke-opacity="{so}"/>')
            v2 = y0 + j * step
            _, b = at(x0, v2)
            panel.append(f'<path d="M0,{b:.1f} H{P:.1f}" stroke="{col}" stroke-width="{w_}" stroke-opacity="{so}"/>')
        if i == 0:
            for cxi in range(5):
                for cyi in range(5):
                    cx, cy = x0 + (cxi + 0.5) * 1e5, y0 + (cyi + 0.5) * 1e5
                    lt = _letter(system, cx, cy) or ""
                    a, b = at(cx, cy)
                    hit = lt.endswith(letter) and math.floor(cx / 1e5) * 1e5 == sx and math.floor(cy / 1e5) * 1e5 == sy
                    panel.append(f'<text x="{a:.1f}" y="{b + 4:.1f}" font-family="{DISPLAY}" font-size="11" '
                                 f'font-weight="bold" fill="{INK if hit else col}" text-anchor="middle" '
                                 f'stroke="#ffffff" stroke-width="2.2" paint-order="stroke">{lt}</text>')
        if i == 3 and unit < 1000:
            # the tenths along the square's south and west edges, and the point's lines from them
            for j in range(1, 10):
                a, _ = at(x0 + j * 100, y0)
                panel.append(f'<path d="M{a:.1f},{P - 7:.1f} V{P:.1f}" stroke="{col}" stroke-width="0.8"/>')
                _, b = at(x0, y0 + j * 100)
                panel.append(f'<path d="M0,{b:.1f} H7" stroke="{col}" stroke-width="0.8"/>')
            ex, ey = at(x0 + int(digits[2]) * 100, y0 + int(digits[k + 2]) * 100)
            panel.append(f'<path d="M{ex:.1f},{P:.1f} V{ey:.1f} H0" fill="none" stroke="{INK}" stroke-width="1" '
                         f'stroke-dasharray="3 2"/>')
        # the point: the corner of the cell the reference names, and the cell itself
        cx0, cy0 = math.floor(p["x"] / unit) * unit, math.floor(p["y"] / unit) * unit
        a, b = at(cx0, cy0 + unit)
        if unit * sc >= 3:
            panel.append(f'<rect x="{a:.1f}" y="{b:.1f}" width="{unit * sc:.1f}" height="{unit * sc:.1f}" '
                         f'fill="{ACCENT}" fill-opacity="0.35" stroke="{ACCENT}" stroke-width="1.2"/>')
        else:
            a, b = at(p["x"], p["y"])
            panel.append(f'<circle cx="{a:.1f}" cy="{b:.1f}" r="2.6" fill="{ACCENT}" stroke="#ffffff" '
                         f'stroke-width="0.9"/>')
        panel.append("</g>")
        # edge figures: the lines' numbers as the sheet prints them (two figures of kilometres), or the 10 km digit
        if i in (1, 2, 3):
            for j in range(int(round(L / step)) + 1):
                v = x0 + j * step
                if i == 1:
                    lab = str(int((v % 1e5) // 1e4)) if j < 10 else ""
                elif i == 2:
                    lab = f"{int((v % 1e5) // 1e3):02d}"
                else:
                    lab = "" if unit < 1000 else f"{int((v % 1e5) // 1e3):02d}" if abs(v % 1e3) < 1 else ""
                if i == 3 and unit < 1000:
                    lab = f"{int((x0 % 1e5) // 1e3):02d}" if j == 0 else ""
                a, _ = at(v, y0)
                if lab:
                    panel.append(_text(a + (2 if i != 1 else (step * sc) / 2), P + 8, lab, 6.0, col, "middle"
                                       if i == 1 else "start", "bold", TYPED, halo_=False))
                v2 = y0 + j * step
                _, b = at(x0, v2)
                if i == 1:
                    lab2 = str(int((v2 % 1e5) // 1e4)) if j < 10 else ""
                elif i == 2:
                    lab2 = f"{int((v2 % 1e5) // 1e3):02d}"
                else:
                    lab2 = "" if unit < 1000 else f"{int((v2 % 1e5) // 1e3):02d}" if abs(v2 % 1e3) < 1 else ""
                if i == 3 and unit < 1000:
                    lab2 = f"{int((y0 % 1e5) // 1e3):02d}" if j == 0 else ""
                if lab2:
                    if i == 3:                             # inside the panel: the gap beyond is the last panel's
                        panel.append(_text(3, b - 3, lab2, 6.0, col, "start", "bold", TYPED))
                    else:
                        panel.append(_text(-2, b - (2 if i != 1 else (step * sc) / 2) + 2, lab2, 6.0, col, "end",
                                           "bold", TYPED, halo_=False))
        panel.append(f'<rect width="{P:.1f}" height="{P:.1f}" fill="none" stroke="{INK}" stroke-width="0.6"/>')
        h1, h2 = heads[i]
        body.append(f'<g transform="translate({ox:.1f},{oy:.1f})">{"".join(panel)}</g>')
        body.append(_text(ox, oy - 17, h1, 8.4 if columns == 2 else 7.4, INK, weight="bold", halo_=False))
        body.append(_text(ox, oy - 7, h2, 6.6 if columns == 2 else 6.0, MUTED, halo_=False))
    # the reading, under the panels: the reference broken into its parts
    y = top + ((3 // columns) * row_h) + P + 30
    parts = ([(letters[0], "the 500 km square"), (letters[1], "the 100 km square")] if len(letters) == 2
             else [(letters, "the 100 km square")]) + [(digits[:k], "east: read right"), (digits[k:], "north: then up")]
    x = 0.0
    for txt, words in parts:
        body.append(_text(x, y, txt, 20, col if txt.isalpha() else INK, weight="bold", family=TYPED, halo_=False))
        w_ = len(txt) * 12.2
        body.append(_text(x, y + 11, words, 6.4, MUTED, halo_=False))
        x += max(w_, 62) + 12
    prec = "to the nearest 100 metres" if unit == 100 else "to the nearest kilometre" if unit == 1000 else f"{unit} m"
    y2 = y + 30                                            # the reading's words, under the reference's parts
    body.append(_text(0, y2, f"{g['name']}: {prec}.", 7.0, INK, weight="bold", halo_=False))
    body.append(_text(0, y2 + 10, f"As typed: \u201c{case['typed']}\u201d", 6.6, INK, family=TYPED, halo_=False))
    if slip:
        body.append(_text(0, y2 + 20, case["slip"]["words"] + " (hatched, panel 1).", 6.4, ACCENT, halo_=False))
    y = y2 + (6 if slip else -4)
    Htot = y + 30
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W + 14:.1f}pt" height="{Htot:.1f}pt" viewBox="-14 0 '
           f'{W + 14:.1f} {Htot:.1f}">{"".join(body)}</svg>')
    notes = {"case": case_id, "ref": case["ref"], "grid": g["name"], "lon": round(p["lon"], 5),
             "lat": round(p["lat"], 5), "cell_m": unit, "page": case["page"], "map": credit,
             "slip": case.get("slip")}
    return halo.split(svg), notes
