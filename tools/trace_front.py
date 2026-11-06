# /// script
# requires-python = ">=3.10,<3.14"
# dependencies = ["numpy", "scipy", "pillow", "scikit-image"]
# ///
"""Trace the front line, and place the unit symbols, of a dated situation map (records/fronts/).

The maps (SOURCES.yml `loc-12ag`): HQ Twelfth Army Group's daily situation maps, 1:1,000,000, in the Library of
Congress (G5701.S7 svar .A4). The scan, once (cached, git-ignored):

    curl -o sources/maps/loc/g5701s-ict21276.jp2 \\
      https://tile.loc.gov/storage-services/service/gmd/gmd5/g5701/g5701s/ict21276.jp2
    uv run tools/trace_front.py 12ag-1945-03-07                      # records/fronts/12ag-1945-03-07.geojson
    uv run tools/trace_front.py 12ag-1945-03-07 --overlay /tmp/o.jpg [--crop X Y W H]   # check it on the scan
    uv run tools/trace_front.py 12ag-1945-03-09 --gcps-from 12ag-1945-03-07   # another day's towns, matched to that map's

How it works:
1. The fit. Town rings on the scan (records/fronts/<map>-gcps.csv: the ring's centre on the full scan, by eye or
   detected and checked by eye; the town today from OSM Nominatim) and a 2nd-order polynomial each way. The daily sheets
   are printings of one base map, so another day's towns are found by matching (--gcps-from): the sheets' offset from
   each other, then a patch of the first sheet round each ring, matched in the other (normalised cross-correlation),
   which needs no reading by eye; the residuals and the overlay check it. The sheet is a
   conformal conic ("Europe (Air) Conical Orthomorphic"), close to the polynomial over a few degrees; the residuals,
   printed, are the drafting's error as much as the fit's. Only the part of the sheet the towns surround is traced.
2. The front. The front line is the heaviest and blackest ink on the sheet (grey < 70, the roads' grey is about 85-150,
   the paper 190): opened with a disk, it keeps the front and drops the thin black of the unit symbols and lettering.
   Army group and army boundaries are as heavy in places, so the front is the cheapest path along that ink through
   waypoints read by eye (MAPS below, in pixels), never the whole mask: a person decides which line is the front.
3. The units. The symbols in records/fronts/<map>-units.csv (read by eye: the symbol's centre, the side, the echelon,
   the arm, the designation as drawn, the kit's
   unit where the symbol is certainly one of records/army's, and the map it was read on) are placed through the fit. A symbol stands in its unit's area; it is not a
   position, and the page says so.

The front's LineStrings run so that the side the map hatches (the enemy's) lies to the left as the line runs; a page
draws its ticks on that side.
"""
import argparse
import csv
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image
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

@dataclass(frozen=True)
class SitMap:
    """A map: its scan, citation, date and the hour of its situation, and the front's runs as waypoints on the scan
    (x, y), each run in order with the enemy's (hatched) side on its left."""
    scan: str
    cite: str
    date: str
    as_of: str
    title: str
    runs: list[list[tuple[int, int]]]
    exclude: tuple[tuple[int, int, int, int], ...] = ()   # boxes on the scan whose heavy ink isn't the front (boundaries)
    flip: tuple[tuple[int, int], ...] = ()                # points on stretches whose ticks don't tell their side, to turn
    checked: tuple[tuple[int, int], ...] = ()             # and on those found the right way, checked by eye


# The later days' fronts, as waypoints on each day's own scan (read on its overlay, 6 Nov 2026); the sheets are ict21269 + the
# day, G-3 report no. 268 + the day (read on each sheet's title, 6 Nov 2026).
RUNS: dict[int, list[list[tuple[int, int]]]] = {}
# their front is the ticked stretches (stretches()), less the heavy lines that aren't the front: the 21st/12th Army Group
# boundary from Aachen north-east (the same line on every sheet; the sheets' offsets are under 70 px)
BOUNDARY = ((3700, 1420, 4280, 2000),)
EXCLUDE: dict[int, tuple[tuple[int, int, int, int], ...]] = {}
FLIP: dict[int, tuple[tuple[int, int], ...]] = {}
# stretches with too few ticks of their own to tell and nothing to continue, found the right way (the US side on their
# right), checked on the scan (6 Nov 2026): the Rhine at Bonn (15th), its ticks crowded by the town's lettering
CHECKED: dict[int, tuple[tuple[int, int], ...]] = {15: ((4585, 1997),)}

# Waypoints read on the overlay (5 Nov 2026).
MAPS = {
    "12ag-1945-03-07": SitMap(
        scan="g5701s-ict21276.jp2",
        cite="loc-12ag/ict21276",
        date="1945-03-07",
        as_of="071200 MAR 1945",
        title="HQ Twelfth Army Group situation map, to accompany G-3 report no. 275: situation as of 071200 Mar 1945",
        # one run, north to south (the enemy to the east, on its left): down the Rhine from about Grevenbroich's latitude
        # past Cologne and Bad Godesberg, out to the point at Remagen and back, south through the Eifel, round Third
        # Army's salient toward Kaisersesch (its north side out, its south side back), and on south to about 50.05 N.
        # The towns the fit uses lie from 50.15 to 51.09 N; the ends are just outside that, and say so in the README.
        runs=[[(4395, 1540), (4510, 1700), (4510, 2070), (4700, 2215), (4530, 2200), (4200, 2345), (4185, 2420),
                  (4300, 2610), (4255, 2895), (4450, 2725), (4655, 2655), (4450, 2790), (4320, 2950)]],
    ),
    **{f"12ag-1945-03-{d:02d}": SitMap(
        scan=f"g5701s-ict{21269 + d}.jp2", cite=f"loc-12ag/ict{21269 + d}", date=f"1945-03-{d:02d}", as_of=f"{d:02d}1200 MAR 1945",
        title=f"HQ Twelfth Army Group situation map, to accompany G-3 report no. {268 + d}: situation as of {d:02d}1200 Mar 1945",
        runs=RUNS.get(d, []), exclude=EXCLUDE.get(d, BOUNDARY), flip=FLIP.get(d, ()),
        checked=CHECKED.get(d, ())) for d in (9, 11, 13, 15, 17)},
}


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


def heavy_ink(g, radius, dark=70):
    ink = g < dark
    heavy = ndi.binary_opening(ink, structure=disk(radius))
    lab, n = ndi.label(heavy)
    size = ndi.sum(heavy, lab, range(n + 1))
    return (size > 2000)[lab]


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


def tick_ink(rgb, heavy, dark=85):
    """The black ink that isn't the heavy line: black in all three channels, so not the rivers' blue (dark in grey,
    and printed beside the front along the Rhine) nor the roads' grey."""
    return (rgb.max(axis=2) < dark) & ~ndi.binary_dilation(heavy, iterations=2)


def tick_sides(ink, pts, step=4, near=(6, 18)):
    """How much tick ink lies a few pixels out on each side along a run: (left, right), as shares of the places sampled.
    The map ticks its front on its own side."""
    hits, n = {1: 0, -1: 0}, 0
    for i in range(step, len(pts) - step, step):
        t = pts[i + step] - pts[i - step]
        nrm = np.array([t[1], -t[0]]) / (np.hypot(*t) or 1)   # the left of the run's way, on the scan (y down)
        n += 1
        for side in (1, -1):
            for d in range(*near):
                x, y = (pts[i] + side * d * nrm).astype(int)
                if 0 <= y < ink.shape[0] and 0 <= x < ink.shape[1] and ink[y, x]:
                    hits[side] += 1
                    break
    return (hits[1] / n, hits[-1] / n) if n else (0.0, 0.0)


@dataclass
class Stretch:
    """A stretch of the front between junctions: its points in order, how its way was found, and whether it is turned by hand."""
    pts: np.ndarray
    how: str
    flip: bool


def stretches(rgb, heavy, fit, M, min_len=25):
    """The front as the heavy ink's stretches between junctions, inside the towns' spread and outside the map's
    `exclude` boxes (its boundaries), each turned so its ticks (the map's own side) are on its right and the enemy's on
    its left; a stretch whose ticks don't tell (too few, or as many each side) keeps the way it was found and is listed,
    and `flip` (a point on the scan near a stretch) turns one by hand. Returns [(points, how)]."""
    sk = skeletonize(heavy)
    nb = ndi.convolve(sk.astype(np.uint8), np.ones((3, 3), np.uint8), mode="constant")
    lab, _ = ndi.label(sk & (nb <= 3), structure=np.ones((3, 3)))
    ink = tick_ink(rgb, heavy)
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
        L, R = tick_sides(ink, pts)
        flip = any(np.min(np.hypot(*(pts - np.array(f)).T)) < 8 for f in M.flip)
        if max(L, R) >= 0.06 and max(L, R) >= 1.5 * min(L, R):
            how = "ticks"
            if L > R:
                pts = pts[::-1]
        else:
            how = "unsure"
        out.append(Stretch(pts, how, flip))
    # a stretch whose ticks don't tell takes the way of a stretch it continues (an end within a few pixels of the other's
    # start, or of its end, turned): one line, one way
    def near(u, v):
        return np.hypot(*(u - v)) < 12
    for _ in range(3):
        for st in out:
            if st.how != "unsure":
                continue
            for o in out:
                if o is st or o.how == "unsure":
                    continue
                a, b, c, d = st.pts[0], st.pts[-1], o.pts[0], o.pts[-1]
                if near(c, b) or near(d, a):
                    st.how = "continues"
                elif near(c, a) or near(d, b):
                    st.pts, st.how = st.pts[::-1], "continues"
                if st.how != "unsure":
                    break
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


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("map", choices=sorted(MAPS))
    ap.add_argument("--radius", type=int, default=4, help="opening disk radius in pixels (the front's weight)")
    ap.add_argument("--overlay")
    ap.add_argument("--crop", type=int, nargs=4)
    ap.add_argument("--gcps-from", choices=sorted(MAPS), help="write this map's towns, matched to another map's")
    a = ap.parse_args()
    M = MAPS[a.map]
    scan = CACHE / M.scan
    if not scan.exists():
        sys.exit(f"no scan at {scan}: fetch it (this tool's docstring says how)")

    if a.gcps_from:
        # the matches are checked against one another: the two printings differ by an affine transform (the scans'
        # placing and the paper), fitted to the matches that agree with it (within 4 px, refitted); a town whose match
        # doesn't agree (the day's overprint over its ring) is placed through the transform instead, and says so
        src = MAPS[a.gcps_from]
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
    heavy = heavy_ink(g, a.radius)
    sk = skeletonize(heavy)
    G, xs, ys, tree = graph(sk)
    feats, runs_px = [], []
    # the front: through the waypoints where the map has them (7 March, read by hand), else the ticked stretches
    if M.runs:
        found = [(trace(G, xs, ys, tree, via), "waypoints") for via in M.runs]
    else:
        found = stretches(np.asarray(Image.open(scan).convert("RGB")), heavy, fit, M)
        unsure = [tuple(int(v) for v in p[len(p) // 2]) for p, how in found if how == "unsure"]
        print(f"{len(found)} stretches: " + ", ".join(f"{sum(1 for _, h in found if h == k)} {k}" for k in ("ticks", "continues", "by hand", "checked by eye", "unsure")))
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

    if a.overlay:
        rgb = np.stack([g] * 3, -1).copy()
        rgb[heavy] = (rgb[heavy] * 0.4 + np.array([255, 140, 0]) * 0.6).astype(np.uint8)
        for pts in runs_px:
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    rgb[np.clip(pts[:, 1] + dy, 0, g.shape[0] - 1), np.clip(pts[:, 0] + dx, 0, g.shape[1] - 1)] = (0, 90, 255)
        for via in M.runs:
            for x, y in via:
                rgb[y - 9:y + 10, x - 2:x + 3] = rgb[y - 2:y + 3, x - 9:x + 10] = (0, 170, 0)
        for x, y in fit.px.astype(int):
            rgb[y - 12:y + 13, x - 2:x + 3] = rgb[y - 2:y + 3, x - 12:x + 13] = (220, 0, 0)
        for u in units:
            x, y = int(u["x"]), int(u["y"])
            rgb[y - 6:y + 7, x - 6:x + 7] = (200, 0, 200)
        im = Image.fromarray(rgb)
        if a.crop:
            x, y, w, h = a.crop
            im = im.crop((x, y, x + w, y + h))
        im.thumbnail((2400, 2400))
        im.save(a.overlay, quality=85)


if __name__ == "__main__":
    main()
