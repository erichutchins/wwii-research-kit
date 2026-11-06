# /// script
# requires-python = ">=3.10,<3.14"
# dependencies = ["numpy", "scipy", "pillow", "scikit-image", "pyyaml"]
# ///
"""Trace the front line, and place the unit symbols, of a dated situation map (records/fronts/).

The maps (SOURCES.yml `loc-12ag`): HQ Twelfth Army Group's daily situation maps in the Library of Congress (G5701.S7
svar .A4), one a day from 6 June 1944 to 26 July 1945, catalogued in records/fronts/sitmaps.csv (tools/loc_sitmaps.py).
A map is named 12ag-<date>. What is read and decided for it by hand is records/fronts/<map>.yml: its title as read (the
hour of its situation, the G-3 report), which day's towns its own are matched to, and the boxes, flips and checks its
trace needed, each with its reason; the tool refuses to trace a day whose title hasn't been read. The skill
`trace-situation-map` (.claude/skills/) gives the order of work; records/fronts/README.md the files and what was learnt;
guides/SITUATION-MAPS.md the whole collection and how to work through it.

    uv run tools/trace_front.py 12ag-1945-03-08 --title                       # its title block, from the Library (no scan needed):
                                                                              #   read it, write records/fronts/<map>.yml
    uv run tools/trace_front.py 12ag-1945-03-08 --fetch                       # the scan (cached, git-ignored)
    uv run tools/trace_front.py 12ag-1945-03-08 --gcps-from 12ag-1945-03-07   # its towns, matched to that day's (the YAML's default)
    uv run tools/trace_front.py 12ag-1945-03-08 --overlay                     # trace, and draw it over the scan to check
    uv run tools/trace_front.py 12ag-1945-03-08 --boxes                       # the symbols' boxes, numbered, to read
    uv run tools/trace_front.py 12ag-1945-03-08 --look 4590,2020 4630,1797    # magnified, to read a hard one
    uv run tools/trace_front.py 12ag-1945-03-08 --units reading.txt           # the units CSV from what was read
    uv run tools/trace_front.py 12ag-1945-03-08 --sides                       # the page's side test on every town
    uv run tools/trace_front.py 12ag-1945-03-08                               # records/fronts/<map>.geojson

The working images go to sources/fronts-work/<map>/ (git-ignored); --overlay and --boxes say where.

How it works:
1. The fit. Town rings on the scan (records/fronts/<map>-gcps.csv) and a 2nd-order polynomial each way; the sheet is a
   conformal conic ("Europe (Air) Conical Orthomorphic"), close to the polynomial over a few degrees, and the residuals,
   printed, are the drafting's error as much as the fit's. 7 March's rings were read by eye. The daily sheets are
   printings of one base map, so another day's towns are found by matching (--gcps-from): the sheets' offset by phase
   correlation, then a wide patch of the first sheet round each ring matched in the other, the matches checked against
   one affine transform between the sheets (a town whose match doesn't agree is placed through the transform, and says
   so). Only the part of the sheet the towns surround is traced.
2. The front is the heaviest and blackest ink (grey < 70; the roads' grey is about 85-150, the paper 190), opened with a
   disk so the thin black of symbols and lettering drops out, and thinned to a centre line. Either it is followed
   through waypoints read by eye (a map's `runs`: 7 March), or (every later day) the centre line is cut at its junctions
   into stretches, the heavy lines that aren't the front are left out by boxes (`exclude`; the army group boundary from
   Aachen on every sheet), and each stretch is turned by its ticks. The 12th Army Group ticks its front on its OWN side
   (the legend's sample; the US divisions on the ticked side of every stretch), so a stretch is turned to have its ticks
   on its right and the enemy on its left. Ticks are counted as black in all three colours: the Rhine is printed in blue
   beside the front, dark enough in grey to pass for ticks, and counting it turns the Rhine's stretches the wrong way. A
   stretch with too few ticks takes the way of the stretch it continues; one that still can't be told is listed as
   `unsure` and is turned by hand (`flip`) or confirmed (`checked`) after a look on the overlay.
3. The units. The symbols in records/fronts/<map>-units.csv, read by eye (--boxes finds most boxes by their edges and
   numbers them; the rest are read on its overview), placed through the fit. A symbol stands in its unit's area; it is
   not a position, and the page says so. A symbol in the map's list of the divisions facing the bridgehead (`list`) is a
   list, not a place.
"""
import argparse
import csv
import json
import math
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import KDTree
from skimage.feature import match_template
from skimage.morphology import disk, skeletonize

Image.MAX_IMAGE_PIXELS = None
KIT = Path(__file__).resolve().parent.parent
REC = KIT / "records" / "fronts"
CACHE = KIT / "sources" / "maps" / "loc"
WORK = KIT / "sources" / "fronts-work"   # the working images and lists, a folder a map (git-ignored)
# the kit's units a map's US symbol certainly is: (arm, label) as drawn -> records/army's unit or relation (a German
# "XIII" or "FIFTEENTH" is the German corps or army, never the US one of that number)
UNIT_IDS = {("armored", "9"): "9ad", ("", "III"): "iii-corps", ("", "VII"): "vii-corps", ("infantry", "1"): "1st-division",
            ("", "V"): "v-corps", ("", "VIII"): "viii-corps", ("", "XIX"): "xix-corps", ("", "FIRST"): "first-army",
            ("", "NINTH"): "ninth-army", ("", "THIRD"): "third-army"}

sys.path.insert(0, str(Path(__file__).resolve().parent))
import loc_sitmaps
import records


@dataclass(frozen=True)
class SitMap:
    """A map: its scan and citation (the catalogue, records/fronts/sitmaps.csv), and what was read and decided for it by
    hand (records/fronts/<map>.yml): the date and hour of its situation and its title as read on the sheet, which day's
    towns its own are matched to, the front's runs as waypoints where it is traced that way (7 March), and the boxes,
    flips and checks its trace needed, each with its reason."""
    name: str
    item: str
    scan: str
    cite: str
    date: str
    width: int
    height: int
    read: bool                                             # the sheet's title has been read: the YAML exists
    as_of: str = ""
    title: str = ""
    report: str = ""
    gcps_from: str = ""
    runs: tuple = ()                                       # [[(x, y), ...], ...] on the scan, the enemy's side on the left
    exclude: tuple = ()                                    # boxes on the scan whose heavy ink isn't the front (boundaries)
    flip: tuple = ()                                       # points on stretches whose ticks don't tell their side, to turn
    checked: tuple = ()                                    # and on those found the right way, checked by eye


def catalogue():
    """The Library's listing (loc_sitmaps.py list), by the map's name: 12ag-<date> -> its row."""
    rows = {f"12ag-{r['date']}": r for r in loc_sitmaps.read_catalogue()}
    if not rows:
        sys.exit("no catalogue at records/fronts/sitmaps.csv: uv run tools/loc_sitmaps.py list")
    return rows


def sitmap(name):
    row = catalogue().get(name)
    if not row:
        sys.exit(f"{name} is not a day in records/fronts/sitmaps.csv (12ag-YYYY-MM-DD, 1944-06-06 to 1945-07-26)")
    path = REC / f"{name}.yml"
    y = records.load_yaml(path) if path.exists() else None
    if y and y.get("item") != row["item"]:
        sys.exit(f"{path.name} says item {y.get('item')}, the catalogue {row['item']}: one of them is wrong")
    y = y or {}
    pts = lambda key: tuple((int(d["at"][0]), int(d["at"][1])) for d in y.get(key) or [])
    return SitMap(name=name, item=row["item"], scan=f"g5701s-{row['item']}.jp2", cite=f"loc-12ag/{row['item']}", date=row["date"],
                  width=int(row.get("width") or 6700), height=int(row.get("height") or 6000), read=bool(y),
                  as_of=str(y.get("as_of") or ""), title=str(y.get("title") or ""), report=str(y.get("report") or ""),
                  gcps_from=str(y.get("gcps_from") or ""),
                  runs=tuple([tuple(p) for p in run] for run in y.get("runs") or []),
                  exclude=tuple(tuple(int(v) for v in d["box"]) for d in y.get("exclude") or []),
                  flip=pts("flip"), checked=pts("checked"))


def region(M, scan, x, y, w, h, width=None):
    """A part of the sheet, from the scan when it is here, else from the Library's IIIF service (no scan needed)."""
    if scan.exists():
        im = Image.open(scan).convert("RGB").crop((x, y, x + w, y + h))
        return im.resize((width, int(h * width / w))) if width else im
    import io
    body, _ = loc_sitmaps.get(f"{loc_sitmaps.IIIF.format(item=M.item)}/{x},{y},{w},{h}/{f'{width},' if width else 'full'}/0/default.jpg")
    return Image.open(io.BytesIO(body)).convert("RGB")


def skeleton(M):
    """The YAML a reader writes once the title is read (records/fronts/<map>.yml), to fill in."""
    return "\n".join([
        f"# {M.name}: the sheet as read on its title, and the hand decisions its trace needed (tools/trace_front.py;",
        "# fronts/README.md). The towns are <map>-gcps.csv, the symbols <map>-units.csv; the GeoJSON is generated.",
        f"item: {M.item}", f"date: {M.date}",
        "as_of: DD1200 MON 1945          # the situation's day and hour, as the title gives it (or 2400 HRS D MONTH 1944)",
        "report:                          # the G-3 report's number, where the title gives one",
        f'title: "HQ Twelfth Army Group situation map, to accompany G-3 report no. NNN: situation as of {M.date}"   # as read',
        "read: the title on the sheet, <date>",
        "gcps_from: 12ag-1945-03-07       # the day whose towns this sheet's are matched to (the same base sheet), or gcps_read: by eye",
        "exclude:   # boxes on the scan (x0, y0, x1, y1) whose heavy ink isn't the front, each with why",
        "  - {box: [3700, 1420, 4280, 2000], why: \"the 21st/12th Army Group boundary from Aachen north-east (the 1:1,000,000 sheet)\"}",
        "flip: []   # stretches turned by hand after a look: {at: [x, y], why: ...}",
        "checked: []   # stretches whose ticks didn't tell, found the right way by eye: {at: [x, y], why: ...}",
    ])


def design(a, b):
    return np.stack([np.ones_like(a), a, b, a * a, a * b, b * b], 1)


class Fit:
    """lon/lat <-> pixel, 2nd-order polynomials fitted to the towns (each side centred and scaled)."""

    def __init__(self, gcps):
        self.px = np.array([[float(r["x"]), float(r["y"])] for r in gcps])
        self.ll = np.array([[float(r["lon"]), float(r["lat"])] for r in gcps])
        self.names = [r["town"] for r in gcps]
        self.pm, self.ps = self.px.mean(0), self.px.std(0)
        self.lm, self.ls = self.ll.mean(0), self.ll.std(0)
        self.f = np.linalg.lstsq(self._d(self.ll, 0), self.px, rcond=None)[0]
        self.i = np.linalg.lstsq(self._d(self.px, 1), self.ll, rcond=None)[0]

    def _d(self, v, inv):
        v = (np.atleast_2d(v).astype(float) - (self.pm if inv else self.lm)) / (self.ps if inv else self.ls)
        return design(v[:, 0], v[:, 1])

    def to_px(self, lonlat):
        return self._d(lonlat, 0) @ self.f

    def to_ll(self, px):
        return self._d(px, 1) @ self.i

    def residuals_km(self):
        res = km(self.to_ll(self.px), self.ll)
        loo = []
        for k in range(len(self.px)):
            m = np.arange(len(self.px)) != k
            c = np.linalg.lstsq(self._d(self.px[m], 1), self.ll[m], rcond=None)[0]
            loo.append(km(self._d(self.px[k:k + 1], 1) @ c, self.ll[k:k + 1])[0])
        return res, np.array(loo)


def km(a, b):
    a, b = np.radians(np.atleast_2d(a)), np.radians(np.atleast_2d(b))
    h = np.sin((b[:, 1] - a[:, 1]) / 2) ** 2 + np.cos(a[:, 1]) * np.cos(b[:, 1]) * np.sin((b[:, 0] - a[:, 0]) / 2) ** 2
    return 6371 * 2 * np.arcsin(np.sqrt(h))


def gcps_from(base, other, rows, patch=140, search=60):
    """The towns of `rows` (on the scan `base`) found on `other`: the sheets' offset by phase correlation at 1/8 size,
    then each ring's patch matched near its offset place (a wide patch, so the base map outweighs the day's overprint).
    Returns the rows with x, y on `other` and the match's score."""
    k = 8
    a, b = base[::k, ::k].astype(float), other[::k, ::k].astype(float)
    h, w = min(a.shape[0], b.shape[0]), min(a.shape[1], b.shape[1])
    a, b = a[:h, :w] - a[:h, :w].mean(), b[:h, :w] - b[:h, :w].mean()
    r = np.fft.ifft2(np.fft.fft2(b) * np.conj(np.fft.fft2(a)))
    dy, dx = np.unravel_index(np.argmax(np.abs(r)), r.shape)
    dy, dx = (dy - h if dy > h // 2 else dy) * k, (dx - w if dx > w // 2 else dx) * k
    out = []
    for row in rows:
        x, y = int(row["x"]), int(row["y"])
        t = base[y - patch:y + patch, x - patch:x + patch].astype(float)
        X, Y = x + dx, y + dy
        win = other[Y - patch - search:Y + patch + search, X - patch - search:X + patch + search].astype(float)
        m = match_template(win, t)
        j, i = np.unravel_index(np.argmax(m), m.shape)
        out.append({**row, "x": X - search + int(i), "y": Y - search + int(j), "score": float(m.max())})
    return out, (int(dx), int(dy))


def heavy_ink(g, radius, dark=70, min_area=2000):
    """The heaviest, blackest ink: the front (and any boundary as heavy). Pieces under `min_area` px are dropped (heavy
    lettering); the stretch method keeps smaller ones (min_area 500), since a corridor's head is a short heavy arc set
    apart from its sides by the division's own symbol (8 March: the 4th and 11th Armored's heads, about 1000 px)."""
    ink = g < dark
    heavy = ndi.binary_opening(ink, structure=disk(radius))
    lab, n = ndi.label(heavy)
    size = ndi.sum(heavy, lab, range(n + 1))
    return (size > min_area)[lab]


def graph(sk, gap=40, gap_cost=4.0):
    """The skeleton's pixels as a graph; gaps under `gap` px between line ends bridged at a higher cost."""
    ys, xs = np.nonzero(sk)
    idx = -np.ones(sk.shape, np.int64)
    idx[ys, xs] = np.arange(len(ys))
    r, c, d = [], [], []
    for dy, dx in ((0, 1), (1, 0), (1, 1), (1, -1)):
        yy, xx = ys + dy, xs + dx
        ok = (yy < sk.shape[0]) & (xx >= 0) & (xx < sk.shape[1])
        j = np.full(len(ys), -1)
        j[ok] = idx[yy[ok], xx[ok]]
        k = j >= 0
        r.append(np.nonzero(k)[0]); c.append(j[k]); d.append(np.full(int(k.sum()), math.hypot(dy, dx)))
    nb = ndi.convolve(sk.astype(np.uint8), np.ones((3, 3), np.uint8), mode="constant")[ys, xs] - 1
    lab, _ = ndi.label(sk, structure=np.ones((3, 3)))
    comp = lab[ys, xs]
    tree = KDTree(np.c_[xs, ys])
    for e in np.nonzero(nb <= 1)[0]:
        for j in tree.query_ball_point((xs[e], ys[e]), gap):
            if comp[j] != comp[e]:
                r.append(np.array([e])); c.append(np.array([j]))
                d.append(np.array([math.hypot(xs[j] - xs[e], ys[j] - ys[e]) * gap_cost]))
    r, c, d = np.concatenate(r), np.concatenate(c), np.concatenate(d)
    n = len(ys)
    return coo_matrix((np.r_[d, d], (np.r_[r, c], np.r_[c, r])), shape=(n, n)).tocsr(), xs, ys, tree


def order_run(px, py):
    """A one-pixel-wide run's pixels in order from one end to the other."""
    pts = np.c_[px, py]
    tree = KDTree(pts)
    deg = np.array([len(tree.query_ball_point(p, 1.5)) - 1 for p in pts])
    cur = int(np.argmin(deg))
    seen = np.zeros(len(pts), bool)
    seen[cur] = True
    order = [cur]
    while True:
        cand = [j for j in tree.query_ball_point(pts[cur], 1.5) if not seen[j]]
        if not cand:
            break
        cur = min(cand, key=lambda j: np.hypot(*(pts[j] - pts[cur])))
        seen[cur] = True
        order.append(cur)
    return pts[order]


def tick_ink(rgb, dark=80, blue=15):
    """Ink a tick can be: as dark as the line (the line and its ticks are about 35 in every channel; the grey roads that
    run beside the front along the Rhine, 95-100, are not), and not bluish (the rivers' blue is dark at its edge; its blue
    channel runs some 30 above its red, the black's are level)."""
    r, b = rgb[..., 0].astype(int), rgb[..., 2].astype(int)
    return (rgb.max(axis=2) < dark) & (b - r < blue)


def tick_sides(ink, heavy, pts, step=4, reach=24, lo=3, hi=14):
    """How often a tick stands on each side along a run: (left, right), as shares of the places sampled. A tick is a
    short stroke attached to the line: walking out from the run's centre along the normal, past the heavy line's edge,
    ink starts within 2 px of the edge and runs `lo`-`hi` px before paper. A road or a river beside the line isn't
    attached (or doesn't end), and a road crossing it counts on both sides alike. The map ticks its front on its own side."""
    H, W = ink.shape
    hits, n = {1: 0, -1: 0}, 0
    for i in range(step, len(pts) - step, step):
        t = pts[i + step] - pts[i - step]
        nrm = np.array([t[1], -t[0]]) / (np.hypot(*t) or 1)   # the left of the run's way, on the scan (y down)
        n += 1
        for side in (1, -1):
            d, edge = 1, None
            while d < reach:
                x, y = (pts[i] + side * d * nrm).astype(int)
                if not (0 <= y < H and 0 <= x < W):
                    break
                if not heavy[y, x]:
                    edge = d
                    break
                d += 1
            if edge is None:
                continue
            run, gap = 0, 0
            for d in range(edge, edge + hi + 3):
                x, y = (pts[i] + side * d * nrm).astype(int)
                if not (0 <= y < H and 0 <= x < W):
                    break
                if ink[y, x]:
                    if run == 0 and d - edge > 2:
                        break                      # not attached to the line
                    run += 1
                elif run:
                    gap += 1
                    if gap >= 2:
                        break
            if lo <= run <= hi and gap >= 2:
                hits[side] += 1
    return (hits[1] / n, hits[-1] / n) if n else (0.0, 0.0)


@dataclass
class Stretch:
    """A stretch of the front between junctions: its points in order, how its way was found, whether it is turned by
    hand, and its ticks' evidence for its way as found (the places sampled with ticks on its right, less those on its
    left: positive, it runs the right way)."""
    pts: np.ndarray
    how: str
    flip: bool
    vote: float = 0.0


def stretches(rgb, heavy, fit, M, min_len=25):
    """The front as the heavy ink's stretches between junctions, inside the towns' spread and outside the map's
    `exclude` boxes (its boundaries), each turned so its ticks (the map's own side) are on its right and the enemy's on
    its left; a stretch whose ticks don't tell (too few, or as many each side) keeps the way it was found and is listed,
    and `flip` (a point on the scan near a stretch) turns one by hand. Returns [(points, how)]."""
    sk = skeletonize(heavy)
    nb = ndi.convolve(sk.astype(np.uint8), np.ones((3, 3), np.uint8), mode="constant")
    lab, _ = ndi.label(sk & (nb <= 3), structure=np.ones((3, 3)))
    ink = tick_ink(rgb)
    (w, s_), (e, n_) = fit.ll.min(0) - (0.15, 0.1), fit.ll.max(0) + (0.15, 0.1)
    out = []
    for k, sl in enumerate(ndi.find_objects(lab), 1):
        m = lab[sl] == k
        if m.sum() < min_len:
            continue
        py, px = np.nonzero(m)
        pts = order_run(px + sl[1].start, py + sl[0].start).astype(float)
        mx, my = pts[len(pts) // 2]
        lon, lat = fit.to_ll((mx, my))[0]
        if not (w <= lon <= e and s_ <= lat <= n_) or any(x0 <= mx <= x1 and y0 <= my <= y1 for x0, y0, x1, y1 in M.exclude):
            continue
        L, R = tick_sides(ink, heavy, pts)
        flip = any(np.min(np.hypot(*(pts - np.array(f)).T)) < 8 for f in M.flip)
        n = max(1, (len(pts) - 8) // 4)   # places sampled
        out.append(Stretch(pts, "ticks" if max(L, R) >= 0.06 and max(L, R) >= 1.5 * min(L, R) else "unsure", flip, (R - L) * n))
    # One line runs one way. Stretches whose ends meet two at a time (not at a fork, where three or more meet) are links
    # of one line: chained, with each link's way relative to the chain's, the ticks' evidence is summed over the chain and
    # the whole chain turned by the sum, so a stretch misread (the Rhine beside it, lettering over it) is carried by its
    # line, and one with no ticks of its own takes its line's way.
    ends = [(i, k, st.pts[0 if k == 0 else -1]) for i, st in enumerate(out) for k in (0, 1)]
    meet: dict[int, list[tuple[int, int]]] = {}
    for a_i, (i, k, p) in enumerate(ends):
        meet[a_i] = [(j, m) for (j, m, q) in ends if (j, m) != (i, k) and np.hypot(*(p - q)) < 12]
    parent = list(range(len(out)))
    parity = [0] * len(out)   # 1: runs against its chain's way

    def find(x):
        if parent[x] == x:
            return x, 0
        r, p_ = find(parent[x])
        parent[x], parity[x] = r, parity[x] ^ p_
        return r, parity[x]

    for a_i, (i, k, _) in enumerate(ends):
        if len(meet[a_i]) != 1:
            continue                         # a free end, or a fork
        j, m = meet[a_i][0]
        if len(meet[2 * j + m]) != 1:
            continue
        same = k != m                        # an end meeting a start: the same way; two ends or two starts: opposite
        (ri, pi), (rj, pj) = find(i), find(j)
        if ri != rj:
            parent[ri], parity[ri] = rj, pi ^ pj ^ (0 if same else 1)
    total: dict[int, float] = {}
    for i, st in enumerate(out):
        r, p_ = find(i)
        total[r] = total.get(r, 0.0) + (st.vote if p_ == 0 else -st.vote)
    for i, st in enumerate(out):
        r, p_ = find(i)
        chain_way = 1 if total[r] >= 0 else -1          # the chain as found runs the right way, or not
        own = 1 if p_ == 0 else -1
        turn = chain_way * own < 0
        if turn:
            st.pts = st.pts[::-1]
        size = sum(1 for x in range(len(out)) if find(x)[0] == r)
        if total[r] == 0:
            st.how = "unsure"
        elif size > 1 and (st.how == "unsure" or (st.vote > 0) == turn):
            st.how = "line"                              # turned with the line it is a link of, not by its own ticks
        else:
            st.how = "ticks"
    for st in out:
        if st.flip:
            st.pts, st.how = st.pts[::-1], "by hand"
        elif st.how == "unsure" and any(np.min(np.hypot(*(st.pts - np.array(c)).T)) < 8 for c in M.checked):
            st.how = "checked by eye"
    return [(st.pts, st.how) for st in out]


def thin(ll, step_km):
    out, acc = [ll[0]], 0.0
    for p, q in zip(ll[:-1], ll[1:]):
        acc += km(p, q)[0]
        if acc >= step_km:
            out.append(q); acc = 0.0
    if km(out[-1], ll[-1])[0] > 0.2:
        out.append(ll[-1])
    return np.array(out)


def trace(G, xs, ys, tree, via):
    nodes = [int(tree.query(p)[1]) for p in via]
    path = [nodes[0]]
    for s, e in zip(nodes[:-1], nodes[1:]):
        _, pred = dijkstra(G, indices=s, return_predecessors=True)
        seg = [e]
        while seg[-1] != s:
            seg.append(int(pred[seg[-1]]))
            if seg[-1] < 0:
                sys.exit(f"no ink between {via}")
        path += seg[::-1][1:]
    return np.c_[xs[path], ys[path]]


def find_boxes(g, heavy, area):
    """The unit symbols' boxes inside `area` (x0, y0, x1, y1 on the scan): a top and a bottom edge of one length (black
    strokes at least 26 px long, the heavy line left out), 16-50 px apart, joined by short sides; a box inside another
    (a headquarters' inner frame or oval) gives way to the outer. Finds about four in five; a box touching its number or a
    line is often missed, and is read on the overview. Returns [(x, y, w, h)] by rows."""
    x0, y0, x1, y1 = area
    sub = ((g < 80) & ~ndi.binary_dilation(heavy, iterations=1))[y0:y1, x0:x1]
    lab, _ = ndi.label(ndi.binary_opening(sub, structure=np.ones((1, 26))))
    segs = sorted(((sl[1].start, sl[1].stop, (sl[0].start + sl[0].stop) // 2) for sl in ndi.find_objects(lab)), key=lambda t: t[2])
    found, used = [], set()
    for i, (ax0, ax1, ay) in enumerate(segs):
        for j in range(i + 1, len(segs)):
            bx0, bx1, by = segs[j]
            if by - ay > 50:
                break
            if by - ay < 16 or abs(ax0 - bx0) > 7 or abs(ax1 - bx1) > 7 or i in used or j in used:
                continue
            bx, ex = (ax0 + bx0) // 2, (ax1 + bx1) // 2
            if not 30 <= ex - bx <= 160:
                continue
            if min(sub[ay:by, max(c - 3, 0):c + 4].any(1).mean() for c in (bx, ex - 1)) < 0.7:
                continue
            used |= {i, j}
            found.append((x0 + (bx + ex) // 2, y0 + (ay + by) // 2, ex - bx, by - ay))
            break
    keep: list[tuple[int, int, int, int]] = []
    for b in sorted(found, key=lambda b: -b[2]):
        if not any(abs(b[0] - k[0]) < k[2] / 2 and abs(b[1] - k[1]) < k[3] / 2 for k in keep):
            keep.append(b)
    return sorted(keep, key=lambda b: (b[1] // 60, b[0]))


def contact_sheet(rgb, points, out, half=(75, 40), scale=2.2, cols=6, labels=None):
    """Crops of the scan round each point, magnified and numbered, in a grid: for reading symbols by eye."""
    tiles = []
    for i, (x, y) in enumerate(points):
        hx, hy = half
        c = Image.fromarray(rgb[max(y - hy, 0):y + hy, max(x - hx, 0):x + hx]).resize((int(2 * hx * scale), int(2 * hy * scale)))
        d = ImageDraw.Draw(c)
        tag = labels[i] if labels else str(i + 1)
        d.rectangle([0, 0, 8 + 7 * len(tag), 14], fill=(255, 255, 255))
        d.text((2, 1), tag, fill=(220, 0, 0))
        tiles.append(c)
    if not tiles:
        return
    w, h = tiles[0].size
    sheet = Image.new("RGB", (cols * (w + 4), ((len(tiles) + cols - 1) // cols) * (h + 4)), "white")
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % cols) * (w + 4), (i // cols) * (h + 4)))
    sheet.save(out, quality=85)


def grid_ticks(d, x0, y0, x1, y1):
    """Scan coordinates every 100 px along the top and left of an image cropped at (x0, y0)."""
    for X in range((x0 // 100 + 1) * 100, x1, 100):
        d.line([(X - x0, 0), (X - x0, 8)], fill=(200, 0, 0)); d.text((X - x0 + 2, 2), str(X), fill=(200, 0, 0))
    for Y in range((y0 // 100 + 1) * 100, y1, 100):
        d.line([(0, Y - y0), (8, Y - y0)], fill=(200, 0, 0)); d.text((2, Y - y0 + 2), str(Y), fill=(200, 0, 0))


def area_of(fit, margin=150):
    """The towns' spread on the scan, with a margin: the part of the sheet that is traced and read."""
    x0, y0 = fit.px.min(0).astype(int) - margin
    x1, y1 = fit.px.max(0).astype(int) + margin
    return int(x0), int(y0), int(x1), int(y1)


def write_units(map_name, M, spec, boxes_csv):
    """The units CSV from a reading: lines `n of echelon arm label [list:bridgehead]` (n a box --boxes numbered) or
    `@x,y of echelon arm label [...]` (read by eye on the overview), `-` for an empty arm; `#` starts a comment."""
    det = {r["n"]: (int(r["x"]), int(r["y"])) for r in csv.DictReader(open(boxes_csv))} if boxes_csv.exists() else {}
    rows = []
    for ln in open(spec, encoding="utf-8"):
        ln = ln.split("#")[0].strip()
        if not ln:
            continue
        key, of, ech, arm, *label = ln.split()
        lst = label.pop()[5:] if label and label[-1].startswith("list:") else ""
        arm = "" if arm == "-" else arm
        text = " ".join(label)
        if key.startswith("@"):
            x, y = (int(v) for v in key[1:].split(","))
        elif key in det:
            x, y = det[key]
        else:
            sys.exit(f"no box {key} in {boxes_csv}: run --boxes first, or give @x,y")
        # tied on the designation alone: "9(-)" (less some of its units), "1(+)" (with others attached) and "(ELMS)" are
        # still that division
        bare = re.sub(r"\s*\((?:-|\+|±|ELMS?)\)\s*$", "", text)
        unit = UNIT_IDS.get((arm, bare), "") if of == "us" else ""
        rows.append([x, y, of, ech, arm, text, unit, lst, M.cite])
    rows.sort(key=lambda r: (r[1], r[0]))
    out = REC / f"{map_name}-units.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["x", "y", "of", "echelon", "arm", "label", "unit", "list", "map"])
        w.writerows(rows)
    print(f"wrote {out.relative_to(KIT)}: {len(rows)} symbols, {sum(1 for r in rows if r[7])} listed, "
          f"tied to the kit's units: {', '.join(f'{r[5]}={r[6]}' for r in rows if r[6]) or 'none'}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("map", help="a day's map, 12ag-YYYY-MM-DD (records/fronts/sitmaps.csv)")
    ap.add_argument("--radius", type=int, default=4, help="opening disk radius in pixels (the front's weight)")
    ap.add_argument("--fetch", action="store_true", help="download the map's scan from the Library's tile server")
    ap.add_argument("--overlay", nargs="?", const="", help="draw the trace over the scan (to the work folder, or a path)")
    ap.add_argument("--crop", type=int, nargs=4, help="the overlay's part of the scan: X Y W H")
    ap.add_argument("--gcps-from", nargs="?", const="", metavar="MAP", help="write this map's towns, matched to another map's (the YAML's gcps_from)")
    ap.add_argument("--boxes", action="store_true", help="find and number the symbols' boxes, with a sheet to read them")
    ap.add_argument("--title", nargs="*", type=int, metavar="N", help="the sheet's title block (or the region X Y W H), to read its date and report")
    ap.add_argument("--look", nargs="+", metavar="X,Y", help="magnified crops of the scan round these points")
    ap.add_argument("--units", metavar="SPEC", help="write the units CSV from a reading (see write_units)")
    ap.add_argument("--sides", action="store_true", help="the page's side test (Engage.frontSide) on every town")
    ap.add_argument("--check-units", action="store_true", help="every symbol in the units CSV, magnified with its reading, to check")
    a = ap.parse_args()
    M = sitmap(a.map)
    scan = CACHE / M.scan
    work = WORK / a.map
    work.mkdir(parents=True, exist_ok=True)
    if a.fetch:
        loc_sitmaps.fetch_item(M.item)
        print(f"next: --title to read the sheet's date and report, then write records/fronts/{a.map}.yml")
        return
    if a.title is not None:
        # the title block: the sheet's top left, where the 1:1,000,000 sheets carry it, scaled to read (another sheet's
        # title stands elsewhere: give the region); from the Library's IIIF service when the scan isn't here
        x, y, w, h = a.title if len(a.title) == 4 else (0, 0, int(M.width * 0.6), int(M.height * 0.2))
        out = work / "title.jpg"
        region(M, scan, x, y, w, h, width=1600).save(out, quality=85)
        print(f"wrote {out}: read the situation's date and hour and the report number on it; the catalogue says {M.date}.")
        if M.read:
            print(f"records/fronts/{a.map}.yml says: as of {M.as_of}, report {M.report or '?'}. It must agree.")
        else:
            print(f"no records/fronts/{a.map}.yml yet. Write it from what the title says, starting from:\n")
            print(skeleton(M))
        return
    if a.look:
        pts = [tuple(int(v) for v in p.split(",")) for p in a.look]
        out = work / "look.jpg"
        if scan.exists():
            contact_sheet(np.asarray(Image.open(scan).convert("RGB")), pts, out, half=(90, 60), scale=2.5, cols=3, labels=a.look)
        else:   # each look from the Library's IIIF service
            tiles = [region(M, scan, x - 90, y - 60, 180, 120, width=450) for x, y in pts]
            sheet = Image.new("RGB", (3 * 454, ((len(tiles) + 2) // 3) * 304), "white")
            for i, t in enumerate(tiles):
                ImageDraw.Draw(t).text((2, 1), a.look[i], fill=(220, 0, 0))
                sheet.paste(t, ((i % 3) * 454, (i // 3) * 304))
            sheet.save(out, quality=85)
        print(f"wrote {out}")
        return
    if not scan.exists():
        sys.exit(f"no scan at {scan}: --fetch it")
    if not M.read:
        sys.exit(f"records/fronts/{a.map}.yml is missing: read the sheet's title (--title) and write it first, so the trace carries the date and hour the sheet gives")
    if a.units:
        write_units(a.map, M, Path(a.units), work / "boxes.csv")
        return
    if a.check_units:
        rows = list(csv.DictReader(open(REC / f"{a.map}-units.csv")))
        tags = [f"{i} {r['of']} {r['echelon']} {r['arm'] or '-'} {r['label']}{' L' if r.get('list') else ''}" for i, r in enumerate(rows, 1)]
        out = work / "units.jpg"
        contact_sheet(np.asarray(Image.open(scan).convert("RGB")), [(int(r["x"]) + 10, int(r["y"]) - 5) for r in rows], out,
                      half=(80, 45), scale=2.2, cols=5, labels=tags)
        print(f"wrote {out}: {len(rows)} symbols, each tagged with its row, side, echelon, arm and label as recorded (L: listed)")
        return

    if a.gcps_from is not None:
        # the matches are checked against one another: the two printings differ by an affine transform (the scans'
        # placing and the paper), fitted to the matches that agree with it (within 4 px, refitted); a town whose match
        # doesn't agree (the day's overprint over its ring) is placed through the transform instead, and says so
        a.gcps_from = a.gcps_from or M.gcps_from
        if not a.gcps_from:
            sys.exit(f"which day's towns to match to? --gcps-from MAP, or gcps_from in records/fronts/{a.map}.yml")
        src = sitmap(a.gcps_from)
        if not (REC / f"{a.gcps_from}-gcps.csv").exists():
            sys.exit(f"{a.gcps_from} has no towns yet (records/fronts/{a.gcps_from}-gcps.csv): a new base sheet's are read by eye")
        if not (CACHE / src.scan).exists():
            sys.exit(f"no scan of {a.gcps_from} at {CACHE / src.scan}: fetch it too (the matching needs both sheets)")
        rows = list(csv.DictReader(open(REC / f"{a.gcps_from}-gcps.csv")))
        base = np.asarray(Image.open(CACHE / src.scan).convert("L"))
        found, (dx, dy) = gcps_from(base, np.asarray(Image.open(scan).convert("L")), rows)
        A = np.array([[float(r["x"]), float(r["y"]), 1.0] for r in rows])
        B = np.array([[r["x"], r["y"]] for r in found], float)
        ok = np.ones(len(rows), bool)
        for _ in range(4):
            T = np.linalg.lstsq(A[ok], B[ok], rcond=None)[0]
            res = np.hypot(*(A @ T - B).T)
            ok = res <= 4
        if ok.sum() < 12 or np.median(res[ok]) > 2:
            sys.exit(f"the matches don't agree on one transform ({ok.sum()} within 4 px): check the overlay")
        print(f"{a.gcps_from} -> {a.map}: sheets offset {dx:+d}, {dy:+d} px; {ok.sum()} of {len(rows)} towns agree "
              f"(median {np.median(res[ok]):.1f} px)")
        pred = A @ T
        with open(REC / f"{a.map}-gcps.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["town", "x", "y", "read", "lat", "lon", "source", "query"])
            for r, good, q, e in zip(found, ok, pred, res):
                x, y = (r["x"], r["y"]) if good else (int(round(q[0])), int(round(q[1])))
                read = (f"matched to {a.gcps_from}'s ring" if good
                        else f"placed through the sheets' transform (its match was {e:.0f} px off: the day's overprint)")
                w.writerow([r["town"], x, y, read, r["lat"], r["lon"], r["source"], r["query"]])
                if not good:
                    print(f"   {r['town']}: match {e:.0f} px off the transform; placed through it")
        print(f"wrote records/fronts/{a.map}-gcps.csv")
        return

    fit = Fit(list(csv.DictReader(open(REC / f"{a.map}-gcps.csv"))))
    res, loo = fit.residuals_km()
    fit_km = round(float(np.sqrt((loo ** 2).mean())), 1)
    print(f"fit: {len(res)} towns, rms {np.sqrt((res ** 2).mean()):.1f} km, leave-one-out rms {fit_km} km, "
          f"worst {loo.max():.1f} km ({fit.names[int(loo.argmax())]})")
    for n, r, lo in sorted(zip(fit.names, res, loo), key=lambda t: -t[2])[:5]:
        print(f"   {n:14s} {r:4.1f} km (left out: {lo:4.1f} km)")

    g = np.asarray(Image.open(scan).convert("L"))
    heavy = heavy_ink(g, a.radius, min_area=2000 if M.runs else 500)
    if a.boxes:
        area = area_of(fit)
        bx = find_boxes(g, heavy, area)
        with open(work / "boxes.csv", "w", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["n", "x", "y", "w", "h"])
            w.writerows([i, *b] for i, b in enumerate(bx, 1))
        rgb = np.asarray(Image.open(scan).convert("RGB"))
        contact_sheet(rgb, [(x + 10, y - 5) for x, y, _, _ in bx], work / "boxes.jpg")
        x0, y0, x1, y1 = area
        ov = Image.fromarray(rgb[y0:y1, x0:x1].copy())
        d = ImageDraw.Draw(ov)
        for i, (x, y, w_, h_) in enumerate(bx, 1):
            d.rectangle([x - x0 - w_ // 2 - 3, y - y0 - h_ // 2 - 3, x - x0 + w_ // 2 + 3, y - y0 + h_ // 2 + 3], outline=(0, 160, 255), width=3)
            d.text((x - x0 - w_ // 2, y - y0 + h_ // 2 + 3), str(i), fill=(0, 100, 255))
        grid_ticks(d, x0, y0, x1, y1)
        ov.save(work / "boxes-overview.jpg", quality=80)
        print(f"{len(bx)} boxes -> {work / 'boxes.csv'}; read them on {work / 'boxes.jpg'} (numbered) and find the ones "
              f"missed on {work / 'boxes-overview.jpg'} (unmarked symbols; scan coordinates on its edges)")
        return
    sk = skeletonize(heavy)
    G, xs, ys, tree = graph(sk)
    feats, runs_px = [], []
    # the front: through the waypoints where the map has them (7 March, read by hand), else the ticked stretches
    if M.runs:
        found = [(trace(G, xs, ys, tree, via), "waypoints") for via in M.runs]
    else:
        found = stretches(np.asarray(Image.open(scan).convert("RGB")), heavy, fit, M)
        unsure = [tuple(int(v) for v in p[len(p) // 2]) for p, how in found if how == "unsure"]
        print(f"{len(found)} stretches: " + ", ".join(f"{sum(1 for _, h in found if h == k)} {k}" for k in ("ticks", "line", "by hand", "checked by eye", "unsure")))
        if unsure:
            print(f"   unsure (no ticks, nothing to continue; kept as found, check them): {unsure}")
    for k, (pts, how) in enumerate(found, 1):
        runs_px.append(pts)
        ll = thin(fit.to_ll(pts), 1.0)
        feats.append({"type": "Feature", "properties": {"kind": "front", "run": k, "how": how, "cite": M.cite,
                                                        "date": M.date, "as_of": M.as_of, "fit_km": fit_km},
                      "geometry": {"type": "LineString", "coordinates": [[round(x, 4), round(y, 4)] for x, y in ll]}})
    units_csv = REC / f"{a.map}-units.csv"
    units = list(csv.DictReader(open(units_csv))) if units_csv.exists() else []
    for u in units:
        lon, lat = fit.to_ll((float(u["x"]), float(u["y"])))[0]
        feats.append({"type": "Feature", "properties": {"kind": "unit", "of": u["of"], "echelon": u["echelon"], "arm": u["arm"],
                                                        "label": u["label"], "unit": u.get("unit", ""), "list": u.get("list", ""), "cite": u["map"], "fit_km": fit_km},
                      "geometry": {"type": "Point", "coordinates": [round(float(lon), 4), round(float(lat), 4)]}})
    hull = fit.ll
    gj = {"type": "FeatureCollection",
          "properties": {"map": a.map, "cite": M.cite, "date": M.date, "as_of": M.as_of,
                         "title": M.title, "fit_km": fit_km,
                         "box": [round(float(hull[:, 0].min()), 3), round(float(hull[:, 1].min()), 3),
                                 round(float(hull[:, 0].max()), 3), round(float(hull[:, 1].max()), 3)]},
          "features": feats}
    out = REC / f"{a.map}.geojson"
    out.write_text(json.dumps(gj, separators=(",", ":"), ensure_ascii=False) + "\n")
    print(f"{len(runs_px)} front runs, {len(units)} unit symbols -> {out.relative_to(KIT)}")

    if a.sides:
        # the page's own test (site/engage.js), on every town: -1 the map's own side, 1 the enemy's, 0 nothing tells
        js = ("const E=require(process.argv[1]);const fs=require('fs');const gj=JSON.parse(fs.readFileSync(process.argv[2]));"
              "const runs=gj.features.filter(f=>f.properties.kind==='front').map(f=>f.geometry.coordinates);"
              "for(const t of JSON.parse(process.argv[3]))console.log(t[0].padEnd(16),{'-1':'own (US)','1':'enemy','0':'?'}[E.frontSide(runs,[t[2],t[1]])]);")
        towns = json.dumps([[n, float(la), float(lo)] for n, (lo, la) in zip(fit.names, fit.ll)])
        subprocess.run(["node", "-e", js, str(KIT / "site" / "engage.js"), str(out), towns], check=True)

    if a.overlay is not None:
        # the trace in blue with short red ticks on each run's right (the map's own side: they should fall on the map's
        # ticks), an unsure stretch in magenta, each run numbered at its middle; the towns red crosses, the symbols with
        # their labels
        rgb = np.asarray(Image.open(scan).convert("RGB")).copy()
        im = Image.fromarray(rgb)
        d = ImageDraw.Draw(im)
        for k, (pts, how) in enumerate(found, 1):
            q = [tuple(p) for p in pts.astype(int)]
            d.line(q, fill=(255, 0, 255) if how == "unsure" else (0, 90, 255), width=4)
            for i in range(6, len(q) - 6, 22):
                t = np.subtract(q[i + 4], q[i - 4]); nrm = -np.array([t[1], -t[0]]) / (np.hypot(*t) or 1)
                d.line([q[i], tuple(np.add(q[i], 12 * nrm).astype(int))], fill=(230, 0, 0), width=3)
            mx, my = q[len(q) // 2]
            d.text((mx + 6, my - 6), f"{k}{'?' if how == 'unsure' else ''}", fill=(160, 0, 160))
        for via in M.runs:
            for x, y in via:
                d.rectangle([x - 5, y - 5, x + 5, y + 5], outline=(0, 170, 0), width=2)
        for x, y in fit.px.astype(int):
            d.line([(x - 12, y), (x + 12, y)], fill=(220, 0, 0), width=3); d.line([(x, y - 12), (x, y + 12)], fill=(220, 0, 0), width=3)
        for u in units:
            x, y = int(u["x"]), int(u["y"])
            d.rectangle([x - 5, y - 5, x + 5, y + 5], fill=(200, 0, 200))
            d.text((x + 8, y + 6), f"{u['label']}{' (list)' if u.get('list') else ''}", fill=(200, 0, 200))
        x, y, w, h = a.crop or (lambda b: (b[0], b[1], b[2] - b[0], b[3] - b[1]))(area_of(fit))
        im = im.crop((x, y, x + w, y + h))
        grid_ticks(ImageDraw.Draw(im), x, y, x + w, y + h)
        dest = Path(a.overlay) if a.overlay else work / "overlay.jpg"
        im.save(dest, quality=85)
        print(f"wrote {dest}")


if __name__ == "__main__":
    main()
