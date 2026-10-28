# /// script
# requires-python = ">=3.10,<3.14"
# dependencies = ["numpy", "scipy", "pillow", "scikit-image"]
# ///
"""Trace the primary roads of OSS Map No. 967 (1942) and route Army road moves along them.

OSS Map No. 967, "Algeria and Tunisia: Principal Highways and Landing Places", 22 August 1942
(Stanford University Libraries, https://purl.stanford.edu/vs189tm5539; SOURCES.yml `oss-967`).

    # the full-size scan, once (11249 x 6589, cached, git-ignored)
    curl -o sources/maps/stanford/oss967_full.jpg \
      "https://stacks.stanford.edu/image/iiif/vs189tm5539%2Fvs189tm5539_00_0001/full/max/0/default.jpg"
    uv run tools/trace_roads.py                    # records/roads/oss967-primary.geojson + the legs, printed
    uv run tools/trace_roads.py --write-routes     # also add the legs to records/army/routes.csv
    uv run tools/trace_roads.py --overlay /tmp/o.jpg [--crop X Y W H]   # check the network on the map

How it works:
1. The fit. The map's printed graticule does not agree with its own drawing (fitted to the
   tick marks, the towns land 11-36 km off), so the map is fitted to its towns instead: the
   ring symbols of 33 towns (`records/roads/oss967-gcps.csv`; pixel position on the full scan,
   modern position from `records/army/places.csv` or OSM Nominatim) and a 2nd-order polynomial
   each way (lon/lat <-> pixel). The residuals are printed; they are the map's drafting error
   as much as the fit's.
2. The roads. Dark ink (grey < 150) is opened with a disk: primary roads are about twice the
   width of secondary roads, coastline and lettering, so the opening keeps only them. Both
   the opened mask and all line work are thinned to one-pixel skeletons.
3. The routes. Every skeleton pixel of the line work (pieces under 1500 px, mostly lettering,
   dropped) is a graph node; steps along a primary road cost their length, along a secondary
   road 3x, and gaps under 45 px (where the line breaks at a town ring) are bridged at 3x.
   A leg is the cheapest path between its stations' towns (through any `via` towns), turned
   into lon/lat and thinned to a point about every 7 km.
"""
import argparse
import csv
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree
from skimage.morphology import disk, skeletonize

Image.MAX_IMAGE_PIXELS = None
KIT = Path(__file__).resolve().parent.parent
REC = KIT / "records"
SCAN = KIT / "sources" / "maps" / "stanford" / "oss967_full.jpg"
FRAME = (1145, 642, 10632, 5975)  # inside the map's neat line: x0, y0, x1, y1

# Road moves: (unit, from_date, to_date, [via towns], reported miles, how the report gives it)
LEGS = [
    ("62ca-c", "1943-02-01", "1943-02-24", [], 154, "Traveled 154 miles"),
    ("62ca-c", "1943-02-24", "1943-02-25", [], 139, "Travelled 139 miles"),
    ("62ca-c", "1943-02-25", "1943-02-26", [], 195, "Travelled 195 miles"),
    ("62ca-c", "1943-02-26", "1943-02-27", [], 41, "Travelled 41 miles"),
    ("62ca-c", "1943-03-01", "1943-04-30", [], 270, "168 and 102 miles, total 270"),
    ("62ca-c", "1943-05-01", "1943-06-16", [], 21, "travelled 21 miles"),
    ("62ca-c", "1943-06-16", "1943-06-17", [], None, "travelled ?0 mi (a digit illegible)"),
    ("62ca-c", "1943-06-17", "1943-06-18", [], 175, "travelled 175 mi"),
    ("62ca-c", "1943-06-18", "1943-06-19", [], 209, "travelled 209 mi"),
    ("62ca-c", "1943-06-19", "1943-06-20", [], 115, "travelled 115 mi"),
    ("67ca-med", "1943-03-28", "1943-03-29", [], 137.5, "Distance Travelled 137.5 Miles"),
    ("67ca-med", "1943-03-29", "1943-03-30", [], 141, "Distance Travelled 141 Miles"),
    ("67ca-med", "1943-03-30", "1943-03-31", [], 109, "Distance Travelled 109 Miles"),
    ("67ca-med", "1943-03-31", "1943-04-01", [], 200, "Distance Travelled 200 Miles"),
    ("67ca-med", "1943-04-01", "1943-04-02", [], 105, "Distance Travelled 105 Miles"),
    # Not drawn: Tebessa -> Thelepte (35 mi), Thelepte -> Souk Ahras -> Beja (200 + 80 mi) and
    # Beja -> Mateur. Map 967 draws no road from Tebessa to Feriana and Thelepte, nor from Beja
    # to Mateur: the cheapest paths on it run 151 km for a 35-mile move and 111 km for one of
    # about 30 miles. They need the 1943 Tunisia road map (purl.stanford.edu/fs323px5000).
    ("67ca-med", "1943-05-05", "1943-05-31", [], 83, "distance travelled 83 miles"),
]
VIA = {}  # towns a leg passes through that places.csv lacks: name -> (lat, lon), with its source


def design(a, b, order=2):
    t = [np.ones_like(a), a, b]
    if order >= 2:
        t += [a * a, a * b, b * b]
    return np.stack(t, 1)


class Fit:
    """lon/lat <-> pixel, 2nd-order polynomials fitted to the towns."""

    def __init__(self, gcps):
        self.px = np.array([[float(r["x"]), float(r["y"])] for r in gcps])
        self.ll = np.array([[float(r["lon"]), float(r["lat"])] for r in gcps])
        self.names = [r["town"] for r in gcps]
        self.f = np.linalg.lstsq(self._d(self.ll, 0), self.px, rcond=None)[0]
        self.i = np.linalg.lstsq(self._d(self.px, 1), self.ll, rcond=None)[0]

    @staticmethod
    def _d(v, inv):
        if inv:
            return design((v[:, 0] - 6000) / 5000, (v[:, 1] - 3300) / 3000)
        return design((v[:, 0] - 5) / 5, v[:, 1] - 35)

    def to_px(self, lonlat):
        return self._d(np.atleast_2d(lonlat), 0) @ self.f

    def to_ll(self, px):
        return self._d(np.atleast_2d(px).astype(float), 1) @ self.i

    def residuals_km(self):
        ll = self.to_ll(self.px)
        loo = []
        for k in range(len(self.px)):
            m = np.arange(len(self.px)) != k
            c = np.linalg.lstsq(self._d(self.px[m], 1), self.ll[m], rcond=None)[0]
            loo.append(km(self._d(self.px[k:k + 1], 1) @ c, self.ll[k:k + 1])[0])
        return km(ll, self.ll), np.array(loo)


def km(a, b):
    a, b = np.radians(np.atleast_2d(a)), np.radians(np.atleast_2d(b))
    h = np.sin((b[:, 1] - a[:, 1]) / 2) ** 2 + np.cos(a[:, 1]) * np.cos(b[:, 1]) * np.sin((b[:, 0] - a[:, 0]) / 2) ** 2
    return 6371 * 2 * np.arcsin(np.sqrt(h))


def masks(radius):
    g = np.asarray(Image.open(SCAN).convert("L"))
    ink = g < 150
    x0, y0, x1, y1 = FRAME
    ink[:y0] = ink[y1:] = 0
    ink[:, :x0] = ink[:, x1:] = 0
    primary = ndi.binary_opening(ink, structure=disk(radius))
    lab, n = ndi.label(primary)
    size = ndi.sum(primary, lab, range(n + 1))
    primary = (size > 3000)[lab]  # drop blobs (arrow heads, heavy letters)
    lines = skeletonize(ink)
    lab, n = ndi.label(lines, structure=np.ones((3, 3)))
    size = ndi.sum(lines, lab, range(n + 1))
    lines &= (size >= 1500)[lab]
    return g, primary, lines


def graph(primary, lines, gap=45, secondary_cost=3.0):
    ys, xs = np.nonzero(lines)
    idx = -np.ones(lines.shape, np.int64)
    idx[ys, xs] = np.arange(len(ys))
    onp = ndi.binary_dilation(primary, iterations=2)[ys, xs]
    w = np.where(onp, 1.0, secondary_cost)
    r, c, d = [], [], []
    for dy, dx in ((0, 1), (1, 0), (1, 1), (1, -1)):
        yy, xx = ys + dy, xs + dx
        ok = (yy < lines.shape[0]) & (xx >= 0) & (xx < lines.shape[1])
        j = np.full(len(ys), -1)
        j[ok] = idx[yy[ok], xx[ok]]
        k = j >= 0
        a, b = np.nonzero(k)[0], j[k]
        r += [a]; c += [b]; d += [math.hypot(dy, dx) * (w[a] + w[b]) / 2]
    # bridge gaps from line ends (a road broken by a town ring or by lettering)
    nb = ndi.convolve(lines.astype(np.uint8), np.ones((3, 3), np.uint8), mode="constant")[ys, xs] - 1
    ends = np.nonzero(nb <= 1)[0]
    lab, _ = ndi.label(lines, structure=np.ones((3, 3)))
    comp = lab[ys, xs]
    tree = cKDTree(np.c_[xs, ys])
    for e in ends:
        for j in tree.query_ball_point((xs[e], ys[e]), gap):
            if comp[j] != comp[e] or abs(int(j) - int(e)) > 400:  # another piece, or far along this one
                dist = math.hypot(xs[j] - xs[e], ys[j] - ys[e])
                if dist > 3:
                    r.append(np.array([e])); c.append(np.array([j])); d.append(np.array([dist * secondary_cost]))
    r, c, d = np.concatenate(r), np.concatenate(c), np.concatenate(d)
    n = len(ys)
    G = coo_matrix((np.r_[d, d], (np.r_[r, c], np.r_[c, r])), shape=(n, n)).tocsr()
    return G, xs, ys, onp, tree


def thin(ll, step_km=7.0):
    out, acc = [ll[0]], 0.0
    for p, q in zip(ll[:-1], ll[1:]):
        acc += km(p, q)[0]
        if acc >= step_km:
            out.append(q); acc = 0.0
    if km(out[-1], ll[-1])[0] > 0.5:
        out.append(ll[-1])
    return np.array(out)


# The map's own furniture, which the line filter picks up as "roads": the title lettering (top left, over the sea),
# the two scale bars and the legend's sample line. Lines lying wholly inside one of these boxes ([w, s, e, n],
# degrees through the fit) are dropped. Found by plotting the network (28 Oct 2026).
FURNITURE = [(-2.5, 36.55, 1.15, 38.3), (-0.2, 32.2, 3.0, 32.75), (6.9, 32.4, 7.8, 32.8)]


def furniture(ll):
    return any(all(w <= lo <= e and s <= la <= n for lo, la in ll) for w, s, e, n in FURNITURE)


def network_geojson(primary, fit, fit_km):
    sk = skeletonize(primary)
    lab, n = ndi.label(sk, structure=np.ones((3, 3)))
    feats = []
    ys, xs = np.nonzero(sk)
    nb = ndi.convolve(sk.astype(np.uint8), np.ones((3, 3), np.uint8), mode="constant")
    # cut at junctions, then walk each run
    run = sk & (nb <= 3)
    lab, n = ndi.label(run, structure=np.ones((3, 3)))
    for k, sl in enumerate(ndi.find_objects(lab), 1):
        m = lab[sl] == k
        if m.sum() < 30:
            continue
        py, px = np.nonzero(m)
        py, px = py + sl[0].start, px + sl[1].start
        pts = order_run(px, py)
        ll = fit.to_ll(pts)
        ll = thin(ll, 2.0)
        if len(ll) < 2 or furniture(ll):
            continue
        feats.append({"type": "Feature", "properties": {"source": "oss-967", "class": "primary", "fit_km": fit_km},
                      "geometry": {"type": "LineString", "coordinates": [[round(a, 4), round(b, 4)] for a, b in ll]}})
    return {"type": "FeatureCollection", "features": feats}


def order_run(px, py):
    """Order the pixels of a one-pixel-wide run from one end to the other."""
    pts = np.c_[px, py]
    tree = cKDTree(pts)
    deg = np.array([len(tree.query_ball_point(p, 1.5)) - 1 for p in pts])
    start = int(np.argmin(deg))
    seen = np.zeros(len(pts), bool); seen[start] = True
    order = [start]
    cur = start
    while True:
        cand = [j for j in tree.query_ball_point(pts[cur], 1.5) if not seen[j]]
        if not cand:
            break
        cur = min(cand, key=lambda j: np.hypot(*(pts[j] - pts[cur])))
        seen[cur] = True; order.append(cur)
    return pts[order]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--radius", type=int, default=4, help="opening disk radius in pixels (primary roads)")
    ap.add_argument("--write-routes", action="store_true")
    ap.add_argument("--overlay")
    ap.add_argument("--crop", type=int, nargs=4)
    a = ap.parse_args()

    fit = Fit(list(csv.DictReader(open(REC / "roads" / "oss967-gcps.csv"))))
    res, loo = fit.residuals_km()
    fit_km = round(float(np.sqrt((loo ** 2).mean())), 1)
    print(f"fit: {len(res)} towns, rms {np.sqrt((res**2).mean()):.1f} km, leave-one-out rms {fit_km} km, "
          f"max {loo.max():.1f} km ({fit.names[int(loo.argmax())]})")

    g, primary, lines = masks(a.radius)
    gj = network_geojson(primary, fit, fit_km)
    (REC / "roads" / "oss967-primary.geojson").write_text(json.dumps(gj, separators=(",", ":")) + "\n")
    print(f"network: {len(gj['features'])} primary-road lines -> records/roads/oss967-primary.geojson")

    G, xs, ys, onp, tree = graph(primary, lines)
    places = {r["place"]: (float(r["lon"]), float(r["lat"])) for r in csv.DictReader(open(REC / "army" / "places.csv")) if r["lat"]}
    places.update({k: (lon, lat) for k, (lat, lon) in VIA.items()})
    st = {(r["unit"], r["date"]): r["place"] for r in csv.DictReader(open(REC / "army" / "stations.csv"))}
    existing = {(r["unit"], r["from_date"], r["to_date"]) for r in csv.DictReader(open(REC / "army" / "routes.csv"))}
    rows, paths = [], []
    for unit, f, t, via, miles, said in LEGS:
        towns = [st[(unit, f)], *via, st[(unit, t)]]
        nodes = [int(tree.query(fit.to_px(places[p])[0])[1]) for p in towns]
        path = []
        for s, e in zip(nodes[:-1], nodes[1:]):
            _, pred = dijkstra(G, indices=s, return_predecessors=True)
            seg = [e]
            while seg[-1] != s:
                seg.append(pred[seg[-1]])
                if seg[-1] < 0:
                    sys.exit(f"no road from {towns[0]} to {towns[-1]}")
            path += seg[::-1]
        pts = np.c_[xs[path], ys[path]]
        paths.append(pts)
        ll = fit.to_ll(pts)
        length = float(km(ll[:-1], ll[1:]).sum())
        share = float(onp[path].mean())
        way = "the primary road" if share > 0.9 else f"the roads ({share:.0%} on primary roads, the rest secondary)"
        cmp = (f"traced {length / 1.609:.0f} mi ({length:.0f} km) against the report's {miles:g} mi" if miles
               else f"traced {length / 1.609:.0f} mi ({length:.0f} km); the report gives no usable distance")
        note = (f"Along {way} on OSS Map 967 (1942), traced: the reports give only the towns and distances, so the "
                f"route is assumed; ±{fit_km:.0f} km (map fit). {' – '.join(towns)}: {cmp} (\"{said}\").")
        print(f"{unit} {f} -> {t}: {note}")
        wp = thin(ll, 7.0)[1:-1] if len(thin(ll, 7.0)) > 2 else thin(ll, 2.0)[1:-1]
        if (unit, f, t) in existing:
            print("   already in routes.csv: left as it is")
            continue
        for k, (lon, lat) in enumerate(wp, 1):
            rows.append([unit, f, t, k, f"{lat:.4f}", f"{lon:.4f}", note if k == 1 else ""])
    if a.write_routes and rows:
        with open(REC / "army" / "routes.csv", "a", newline="") as fh:
            csv.writer(fh).writerows(rows)
        print(f"routes.csv: {len(rows)} rows added")

    if a.overlay:
        rgb = np.stack([g] * 3, -1).copy()
        rgb[primary] = (np.array([240, 120, 0]) * 0.7 + rgb[primary] * 0.3).astype(np.uint8)
        for pts in paths:
            for dx in range(-3, 4):
                for dy in range(-3, 4):
                    rgb[np.clip(pts[:, 1] + dy, 0, g.shape[0] - 1), np.clip(pts[:, 0] + dx, 0, g.shape[1] - 1)] = (0, 90, 255)
        for (lon, lat) in fit.ll:
            x, y = fit.to_px((lon, lat))[0].astype(int)
            rgb[y - 12:y + 13, x - 2:x + 3] = rgb[y - 2:y + 3, x - 12:x + 13] = (220, 0, 0)
        im = Image.fromarray(rgb)
        if a.crop:
            x, y, w, h = a.crop
            im = im.crop((x, y, x + w, y + h))
        im.thumbnail((2400, 2400))
        im.save(a.overlay, quality=85)


if __name__ == "__main__":
    main()
