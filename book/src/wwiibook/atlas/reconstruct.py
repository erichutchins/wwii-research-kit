"""The period transportation network of an atlas extent, as attributed vectors.

IGN's 1:50,000 (the SCAN 50 1950 series) establishes what existed: its roads are printed in red (solid for the main
roads, red dashes for the lesser ones) on the old *type 1922* sheets, its railways as a heavy dark line. OpenStreetMap
supplies the alignment, which is precise today and, where it follows the sheet, the course the sheet drew. A modern
way is reference material, never proof: it is kept only where the sheet shows the road or railway beside it.

Every feature carries:
  kind                road, rail, river, stream, place, hill, wood, church, cathedral, junction, crossing
  source              the sheet that shows it, with its edition year (or OSM for reference layers)
  source_date         that edition year
  geometry_source     "osm:way/<id>" (today's alignment) or "traced:<sheet>" (the sheet's own line)
  validity            what the source shows, and what that does and doesn't establish for 1944
  confidence          high, medium, low or reference
  note                how it was matched or traced, and anything to check
Roads also carry `period_class` (red-solid, red-dashed or black, as the sheet prints them) and `road_class` (main,
lesser); railways `osm_status` (in use,
disused, abandoned, razed...) and `on_sheet` (shown, partly, not seen).

Written to atlas/<extent>/infrastructure/<layer>.geojson (lon/lat, as GeoJSON requires), with manifest.json: the
sources and their retrieval, the tolerances, and the counts.
"""
import json
import math
from datetime import date

import numpy as np
from scipy import ndimage
from shapely import LineString, MultiLineString, Point
from shapely.geometry import shape
from shapely.ops import nearest_points
from skimage.morphology import skeletonize

from . import sources
from .extent import Extent

ROAD_TOL, ROAD_ANGLE, RAIL_TOL, STEP = 30.0, 25.0, 25.0, 15.0
LINK_TOL, LINK_GAP, LINK_LEN, LINK_SNAP = 60.0, 600.0, 400.0, 30.0   # joining the network: see roads()
JOIN, ISOLATED = 300.0, 600.0   # a loose end joins the nearest road this near; a short road meeting none is left out
TRACE_SNAP = 80.0     # a traced road's end this close to a kept road is carried to it
DASHED = 0.08          # a red line broken along more than this share of it is the sheet's dashed road
ROAD_RANK = {"trunk": 0, "primary": 1, "secondary": 2, "tertiary": 3, "trunk_link": 4, "primary_link": 4,
             "secondary_link": 4, "tertiary_link": 4, "unclassified": 5, "residential": 6, "road": 6, "motorway": 7}


class Sheet:
    """The period map's mosaic over the extent, its inks, and the placing of its pixels: IGN's SCAN 50 1950 series
    (France; `period_map: scan50`, the default) or the Allies' wartime GSGS sheets (`period_map: gsgs4225`, with
    `sheets:`), placed by their own grid (gsgs.py)."""

    def __init__(self, ex: Extent):
        w, s, e, n = ex.bbox_lonlat
        self.box = (w - 0.03, s - 0.03, e + 0.03, n + 0.03)
        self.battle = int(ex.date[:4])
        self.kind = str(ex.sources.get("period_map", "scan50"))
        if self.kind == "scan50":
            self.z = int(ex.sources.get("scan50_zoom", 14))
            rgb, (self.tx0, self.ty0, _) = sources.scan50(self.box, self.z)
            lat_mid = (self.box[1] + self.box[3]) / 2
            self.mpp = 156543.03392 * math.cos(math.radians(lat_mid)) / 2 ** self.z
            self.sheets = [(shape(f["geometry"]), f["properties"]["nom"], int(f["properties"]["annee"]))
                           for f in sources.sheets(self.box)["features"]]
            self.placing: list[dict] = []
        else:
            from . import gsgs
            self.mpp = 6.0
            rgb, (gw, gs_, ge, gn, GW, GH), self.placing, hulls = gsgs.mosaic(
                self.kind, [str(x) for x in ex.sources["sheets"]], self.box, self.mpp)
            self.grid = (gw, gs_, ge, gn, GW, GH)
            meta = gsgs.series(self.kind)
            self.sheets = [(hull, f"{meta['series']} sheet {num} ({name})", int(year))
                           for hull, num, name, year in hulls]
        self.rgb = rgb
        a = rgb.astype(np.int16)
        r, g, b = a[..., 0], a[..., 1], a[..., 2]
        lum = a.mean(-1)
        self.red = (r > 140) & (r - g > 60) & (r - b > 60)
        # the sheets print roads one of two ways: red (the old type 1922 sheets: solid main roads, dashed lesser
        # ones) or black, cased with a white fill (the later editions, and some pre-war ones); the extent says which
        self.style = str(ex.sources.get("scan50_roads", "red"))
        self.ink = self.style
        self.road = self.red if self.style == "red" else (lum < 130) & (a.max(-1) - a.min(-1) < 50)
        self.dark = (lum < 95) & (a.max(-1) - a.min(-1) < 45)
        dist, near = ndimage.distance_transform_edt(~self.road, return_indices=True)
        self.road_dist = (dist * self.mpp).astype(np.float32)
        # how near a modern way must run to the sheet's line: the sheet's survey and our placing of it
        self.road_tol = float(ex.sources.get("road_tol_m", ROAD_TOL))
        self.rail_tol = float(ex.sources.get("rail_tol_m", RAIL_TOL))
        self.dark_dist = ndimage.distance_transform_edt(~self.dark) * self.mpp
        smooth = ndimage.gaussian_filter(self.road.astype(np.float32), 1.5)
        gx, gy = ndimage.sobel(smooth, axis=1), ndimage.sobel(smooth, axis=0)
        jxx, jyy, jxy = (ndimage.gaussian_filter(v, 3) for v in (gx * gx, gy * gy, gx * gy))
        # the ink's direction, read at the nearest ink: a way running beside the line, not on it, is tested too
        self.road_dir = (0.5 * np.arctan2(2 * jxy, jxx - jyy) + np.pi / 2)[near[0], near[1]].astype(np.float32)
        del near

    def px(self, lon, lat):
        if self.kind == "scan50":
            x, y = sources.txy(lon, lat, self.z)
            return (np.asarray(x) - self.tx0) * 256, (np.asarray(y) - self.ty0) * 256
        w, s, e, n, W, H = self.grid
        return (np.asarray(lon) - w) / (e - w) * W - 0.5, (n - np.asarray(lat)) / (n - s) * H - 0.5

    def lonlat(self, col, row):
        if self.kind == "scan50":
            return sources.tile_lonlat(self.tx0 + np.asarray(col) / 256, self.ty0 + np.asarray(row) / 256, self.z)
        w, s, e, n, W, H = self.grid
        return w + (np.asarray(col) + 0.5) / W * (e - w), n - (np.asarray(row) + 0.5) / H * (n - s)

    def words(self, name, year) -> str:
        """The source, in words, for a feature on the named sheet."""
        if not name:
            return "no period sheet here"
        if self.kind == "scan50":
            return f"IGN SCAN 50, 1950 series, sheet {name.split('_')[0]} (edition {year})"
        return f"{name}, {year} edition"

    def ref(self, name) -> str:
        return (name or "").split("_")[0] if self.kind == "scan50" else (name or "").split(" (")[0]

    def sample(self, field: np.ndarray, lon, lat, fill=np.inf):
        c, r = self.px(lon, lat)
        ci, ri = np.round(c).astype(int), np.round(r).astype(int)
        ok = (ci >= 0) & (ri >= 0) & (ci < field.shape[1]) & (ri < field.shape[0])
        out = np.full(ci.shape, fill, dtype=float)
        out[ok] = field[ri[ok], ci[ok]]
        return out

    def sheet_at(self, lon: float, lat: float) -> tuple[str, int] | tuple[None, None]:
        p = Point(lon, lat)
        for poly, name, year in self.sheets:
            if poly.contains(p):
                return name, year
        return None, None


def _resample(coords, step: float):
    lon = np.array([c[0] for c in coords], dtype=float)
    lat = np.array([c[1] for c in coords], dtype=float)
    kx = 111320 * math.cos(math.radians(float(lat.mean())))
    d = np.hypot(np.diff(lon) * kx, np.diff(lat) * 110570)
    cum = np.concatenate([[0], np.cumsum(d)])
    if cum[-1] < step:
        return lon, lat, cum
    t = np.arange(0, cum[-1] + 1e-9, step)
    return np.interp(t, cum, lon), np.interp(t, cum, lat), t


def _gaps(dist: np.ndarray) -> float:
    """How broken the sheet's red line is along a matched way, from the distance to the ink at each sample (every
    STEP metres): on a solid line the distance holds steady (the way's offset from the ink); along a dashed one it
    jumps by half a gap (35 m or more) between dashes. The share of samples more than 15 m farther than their
    neighbourhood's usual distance: near 0 for a solid line, a fifth or more for a dashed one."""
    if len(dist) < 9:
        return 0.0
    base = ndimage.median_filter(dist, size=9, mode="nearest")
    return float((dist > base + 15).mean())


def _feature(geom, props) -> dict:
    return {"type": "Feature", "properties": props, "geometry": geom.__geo_interface__}


def _validity(kind: str, year, battle: int = 1944) -> str:
    """What the sheet's edition establishes for the battle's year."""
    if year is None:
        return "outside the period sheets"
    lag = year - battle
    shown = "on the sheet as a road" if kind == "road" else "drawn as a railway"
    if lag < 0:
        return (f"{shown}, {year} edition, {-lag} year{'s' if lag < -1 else ''} before the battle: there in {year}; "
                "one built since wouldn't show")
    if lag == 0:
        return f"{shown}, {year} edition: taken to have existed in {battle}"
    if lag <= 3:
        return (f"{shown}, {year} edition, {lag} year{'s' if lag > 1 else ''} after the battle: taken to have "
                f"existed in {battle}")
    return f"{shown}, {year} edition, {lag} years after the battle: likely in {battle}, but post-war work may show"


def _chains(ways: list[dict]) -> list[dict]:
    """OSM's roads joined end to end where nothing else meets them. OSM splits a road at every bridge, change of class
    or survey edit; tested piece by piece against the sheet, a short piece fails where the road plainly runs on. A
    chain stops at a junction (three or more ends meeting), so a branch is tested as itself. Its tags are its most
    important piece's; its ids are all of them."""
    def key(p):
        return round(p[0], 7), round(p[1], 7)
    ends: dict[tuple, list[int]] = {}
    for i, w in enumerate(ways):
        for p in (w["coords"][0], w["coords"][-1]):
            ends.setdefault(key(p), []).append(i)
    used: set[int] = set()
    out = []
    for i, w in enumerate(ways):
        if i in used:
            continue
        used.add(i)
        coords, members = list(w["coords"]), [w]
        for forward in (True, False):
            while True:
                node = key(coords[-1] if forward else coords[0])
                if len(ends[node]) != 2:
                    break
                nxt = [j for j in ends[node] if j not in used]
                if len(nxt) != 1:
                    break
                c = ways[nxt[0]]["coords"]
                c = c if key(c[0]) == node else c[::-1]
                coords = coords + c[1:] if forward else c[::-1][:-1] + coords
                used.add(nxt[0])
                members.append(ways[nxt[0]])
        best = min(members, key=lambda m: ROAD_RANK.get(m["tags"].get("highway", ""), 9))
        out.append({"ids": [m["id"] for m in members], "tags": best["tags"], "coords": coords})
    return out


def _osm_ref(ids: list[int]) -> str:
    return "osm:way/" + ",".join(str(i) for i in ids)


def _classes(sh: Sheet, gap: float, highway: str) -> dict:
    """How the sheet prints the road (`period_class`), and main or lesser for the views (`road_class`): read off a red
    sheet (solid or dashed); on a black one, OSM's class (trunk, primary, secondary are main)."""
    if sh.style == "red" and sh.kind == "scan50":
        dashed = gap > DASHED
        return {"period_class": "red-dashed" if dashed else "red-solid", "road_class": "lesser" if dashed else "main"}
    return {"period_class": sh.style, "road_class": "main" if ROAD_RANK.get(highway, 9) <= 2 else "lesser"}


def roads(sh: Sheet, ways: list[dict]) -> list[dict]:
    """OSM roads that the sheet's red ink shows beside them, on their modern alignment; short stretches between them
    that the sheet still shows nearby, so the network doesn't break where a modern road strays from the old line; then
    the red ink no modern road explains, traced from the sheet."""
    kept, taken = [], set()
    cell = 20.0
    kx = 111320 * math.cos(math.radians((sh.box[1] + sh.box[3]) / 2))

    def cells(lon, lat):
        return {(int(x * kx // cell), int(y * 110570 // cell)) for x, y in zip(lon, lat)}

    def props(chain, idx, dist, near, geom, bridged=0.0, connector=False):
        gap = _gaps(dist[idx])
        mid = geom.interpolate(0.5, normalized=True)
        name, year = sh.sheet_at(mid.x, mid.y)
        share = float(near[idx].mean())
        conf = "high" if (year or 9999) <= 1950 and share >= 0.8 and not connector else "medium"
        if connector:
            how = (f"A connecting stretch of {float(len(idx) - 1) * STEP:.0f} m between roads the sheet shows: the "
                   f"modern road strays from the sheet's line here, but {sh.ink} ink lies within {LINK_TOL:.0f} m along "
                   f"{float((dist[idx] <= LINK_TOL).mean()):.0%} of it.")
        else:
            how = (f"OSM alignment within {sh.road_tol:.0f} m and {ROAD_ANGLE:.0f} degrees of the sheet's {sh.ink} ink "
                   f"along {share:.0%} of its length" + (f"; the sheet's line there is broken along {gap:.0%} of it."
                                                         if sh.kind == "scan50" and sh.style == "red" else
                                                         "; main or lesser is OSM's class, not read off the sheet."))
            if bridged:
                how += f" Gaps of up to {LINK_GAP:.0f} m where both sides match are bridged: {bridged:.0f} m here."
        return {
            "kind": "road", **_classes(sh, gap, chain["tags"].get("highway", "")),
            "source": sh.words(name, year), "source_date": str(year) if year else "",
            "geometry_source": _osm_ref(chain["ids"]), "osm_highway": chain["tags"].get("highway", ""),
            "name": chain["tags"].get("name", ""), "ref": chain["tags"].get("ref", ""),
            "validity": _validity("road", year, sh.battle), "confidence": conf, "connector": connector,
            "bridged_m": round(bridged), "note": how + " The alignment is today's: a widened road or an eased bend "
                                                       "shows on it."}

    # pass 1: each chain against the sheet
    tested = []
    for chain in sorted(_chains(ways), key=lambda w: ROAD_RANK.get(w["tags"].get("highway", ""), 9)):
        lon, lat, t = _resample(chain["coords"], STEP)
        if len(lon) < 2:
            continue
        dist = sh.sample(sh.road_dist, lon, lat)
        c, r = sh.px(lon, lat)
        way_dir = np.arctan2(np.gradient(r), np.gradient(c))
        ink_dir = sh.sample(sh.road_dir, lon, lat, fill=0.0)
        diff = np.abs(((way_dir - ink_dir) + np.pi / 2) % np.pi - np.pi / 2)
        # the direction is tested only where the sample sits on ink: between a dashed road's dashes it says nothing
        near = (dist <= sh.road_tol) & (diff <= math.radians(ROAD_ANGLE))
        near = ndimage.binary_closing(near, structure=np.ones(21)) | near     # bridge a miss of up to 300 m
        if near.mean() >= 0.6 and t[-1] >= 100:
            on = np.ones(len(lon), dtype=bool)
        else:
            lab, n = ndimage.label(near)
            on = np.zeros(len(lon), dtype=bool)
            for k in range(1, n + 1):
                i = np.flatnonzero(lab == k)
                if len(i) > 1 and t[i[-1]] - t[i[0]] >= 300:
                    on[i] = True
        # a gap between two matched stretches of one road, short and still near the sheet's ink, is the same road
        bridged = 0.0
        lab, n = ndimage.label(~on)
        for k in range(1, n + 1):
            i = np.flatnonzero(lab == k)
            inner = i[0] > 0 and i[-1] < len(on) - 1
            if inner and len(i) * STEP <= LINK_GAP and (dist[i] <= LINK_TOL).mean() >= 0.5:
                on[i] = True
                bridged += len(i) * STEP
        tested.append((chain, lon, lat, t, dist, near, on, bridged))

    # pass 2: keep the matched stretches, a lower-ranked road that only shadows one already kept dropped
    for chain, lon, lat, _t, dist, near, on, bridged in tested:
        lab, n = ndimage.label(on)
        for k in range(1, n + 1):
            idx = np.flatnonzero(lab == k)
            if len(idx) < 2:
                continue
            cs = cells(lon[idx], lat[idx])
            if len(cs & taken) > 0.6 * len(cs):
                on[idx] = False
                continue
            taken |= {(a + da, b + db) for a, b in cs for da in (-1, 0, 1) for db in (-1, 0, 1)}
            geom = (LineString(chain["coords"]) if len(idx) == len(lon)
                    else LineString(list(zip(lon[idx], lat[idx]))))
            kept.append(_feature(geom, props(chain, idx, dist, near, geom, bridged=bridged)))

    # pass 3: the stretches left over that join the kept network at both ends, short, with the sheet's ink near
    ends = [(f["geometry"]["coordinates"][0], f["geometry"]["coordinates"][-1]) for f in kept]
    pts = np.array([p for pair in ends for p in pair] +
                   [q for f in kept for q in f["geometry"]["coordinates"][::4]], dtype=float)
    from scipy.spatial import KDTree
    tree = KDTree(np.c_[pts[:, 0] * kx, pts[:, 1] * 110570])

    def touches(lo, la):
        return tree.query([lo * kx, la * 110570], distance_upper_bound=LINK_SNAP)[0] < LINK_SNAP

    for chain, lon, lat, _t, dist, near, on, _ in tested:
        lab, n = ndimage.label(~on)
        for k in range(1, n + 1):
            i = np.flatnonzero(lab == k)
            a, b = max(i[0] - 1, 0), min(i[-1] + 1, len(on) - 1)      # one sample into the kept ground each side
            idx = np.arange(a, b + 1)
            if len(idx) < 2 or len(idx) * STEP > LINK_LEN or (dist[i] <= LINK_TOL).mean() < 0.5:
                continue
            if not (touches(lon[a], lat[a]) and touches(lon[b], lat[b])):
                continue
            cs = cells(lon[i], lat[i])
            if len(cs & taken) > 0.6 * len(cs):
                continue
            taken |= cs
            geom = LineString(list(zip(lon[idx], lat[idx])))
            kept.append(_feature(geom, props(chain, idx, dist, near, geom, connector=True)))
    if sh.style != "red":          # black ink is also lettering, buildings and railways: nothing traced from it
        return _join(kept, kx)
    # the red ink nothing explains: traced from the sheet itself
    covered = np.zeros(sh.red.shape, dtype=bool)
    for f in kept:
        g = shape(f["geometry"])
        lon, lat, _ = _resample(list(g.coords), 5.0)
        c, r = sh.px(lon, lat)
        ci, ri = np.round(c).astype(int), np.round(r).astype(int)
        ok = (ci >= 0) & (ri >= 0) & (ci < covered.shape[1]) & (ri < covered.shape[0])
        covered[ri[ok], ci[ok]] = True
    covered = ndimage.binary_dilation(covered, iterations=int(sh.road_tol / sh.mpp))
    rest = _close_dashes(sh.red) & ~covered
    # a traced line running within 60 m of an aligned road for most of its length is that road's ink, beside it
    shadow = ndimage.binary_dilation(covered, iterations=int(30 / sh.mpp))
    network = MultiLineString([f["geometry"]["coordinates"] for f in kept])
    pieces = []
    for whole in _trace(skeletonize(rest), min_px=int(250 / sh.mpp)):
        # only the stretches away from every kept road: the rest is that road's own ink, beside its modern line
        lab, n = ndimage.label(~shadow[whole[:, 0], whole[:, 1]])
        pieces += [whole[lab == k] for k in range(1, n + 1) if (lab == k).sum() * sh.mpp >= 250]
    for line in pieces:
        lon, lat = sh.lonlat(line[:, 1], line[:, 0])
        coords = list(zip(lon.tolist(), lat.tolist()))
        # an end that stops just short of a kept road (the ink broken by a village's buildings) is carried to it
        for at in (0, -1):
            e = Point(coords[at])
            q = nearest_points(e, network)[1]
            if 0 < math.hypot((q.x - e.x) * kx, (q.y - e.y) * 110570) <= TRACE_SNAP:
                coords.insert(len(coords) if at == -1 else 0, (q.x, q.y))
        geom = LineString(coords).simplify(0.00006)
        mid = geom.interpolate(0.5, normalized=True)
        name, year = sh.sheet_at(mid.x, mid.y)
        gap = _gaps(sh.road_dist[line[::max(1, int(STEP / sh.mpp)), 0], line[::max(1, int(STEP / sh.mpp)), 1]])
        kept.append(_feature(geom, {
            "kind": "road", **_classes(sh, gap, ""),
            "source": sh.words(name, year),
            "source_date": str(year) if year else "", "geometry_source": f"traced:{sh.ref(name)}",
            "osm_highway": "", "name": "", "ref": "", "validity": _validity("road", year, sh.battle), "confidence": "medium",
            "connector": False, "bridged_m": 0,
            "note": ("Traced from the sheet's red ink where no OSM road runs beside it: a road since realigned or "
                     "gone, or a misreading. Its line is the sheet's, good to about 25 m; check on the sheet. An end "
                     f"within {TRACE_SNAP:.0f} m of a kept road is carried to it.")}))
    return _join(kept, kx)


def _join(kept: list[dict], kx: float) -> list[dict]:
    """Best effort at one network, for an illustration: a road's end that meets no other road is carried straight to
    the nearest road within JOIN metres (the sheet's ink broken by a village, a label or a bridge; the modern line
    a few metres off the old). A short road still meeting nothing at either end is marked `isolated`, for the views
    to leave out. Both are recorded on the feature (`joined_m`, `isolated`)."""
    from shapely.strtree import STRtree

    def m(c):
        return (c[0] * kx, c[1] * 110570)
    lines = [LineString([m(c) for c in f["geometry"]["coordinates"]]) for f in kept]
    tree = STRtree(lines)
    for i, (f, g) in enumerate(zip(kept, lines)):
        coords = f["geometry"]["coordinates"]
        joined, loose = 0.0, 0
        for at in (0, -1):
            e = Point(g.coords[at])
            others = [j for j in tree.query(e.buffer(JOIN)) if j != i]
            if any(lines[j].distance(e) <= 40 for j in others):
                continue
            best = min(others, key=lambda j: lines[j].distance(e), default=None)
            if best is None or lines[best].distance(e) > JOIN:
                loose += 1
                continue
            q = nearest_points(e, lines[best])[1]
            joined += e.distance(q)
            p = (q.x / kx, q.y / 110570)
            coords = [p, *coords] if at == 0 else [*coords, p]
        f["geometry"]["coordinates"] = coords
        f["properties"]["joined_m"] = round(joined)
        f["properties"]["isolated"] = loose == 2 and g.length < ISOLATED
        if joined:
            f["properties"]["note"] += f" Carried {joined:.0f} m in a straight line to meet the next road."
    return kept


def _close_dashes(mask: np.ndarray, length: int = 33, turns: int = 8) -> np.ndarray:
    """A dashed road's dashes joined into one line: closed along a short straight stroke in each of `turns`
    directions, so a gap of up to `length` pixels (about 200 m here; the sheet's gaps run 12 to 20 pixels) is bridged
    along the road and nothing is joined across it, as a square would join two roads side by side."""
    out = mask.copy()
    half = length // 2
    for k in range(turns):
        a = math.pi * k / turns
        foot = np.zeros((length, length), dtype=bool)
        for t in np.linspace(-half, half, 4 * length):
            foot[int(round(half + t * math.sin(a))), int(round(half + t * math.cos(a)))] = True
        out |= ndimage.binary_closing(mask, structure=foot)
    return out


def _trace(skel: np.ndarray, min_px: int) -> list[np.ndarray]:
    """A skeleton's paths between its ends and branch points, as (row, col) arrays, the short ones dropped."""
    nb = ndimage.convolve(skel.astype(np.uint8), np.ones((3, 3), dtype=np.uint8), mode="constant") - 1
    node = skel & (nb != 2)
    seen = np.zeros(skel.shape, dtype=bool)
    rows, cols = np.nonzero(skel)
    pix = set(zip(rows.tolist(), cols.tolist()))
    out = []

    def nbrs(p):
        r, c = p
        return [(r + dr, c + dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1) if (dr or dc) and (r + dr, c + dc) in pix]

    starts = list(zip(*np.nonzero(node))) + [p for p in pix]       # nodes first, then any loop's pixels
    for s in starts:
        s = (int(s[0]), int(s[1]))
        for first in nbrs(s):
            if seen[first]:
                continue
            path, prev, cur = [s], s, first
            while True:
                path.append(cur)
                seen[cur] = True
                if node[cur]:
                    break
                nxt = [q for q in nbrs(cur) if q != prev and not seen[q]]
                if not nxt:
                    break
                prev, cur = cur, nxt[0]
            if len(path) >= min_px:
                out.append(np.array(path))
    return out


def rails(sh: Sheet, ways: list[dict]) -> list[dict]:
    out = []
    for way in ways:
        lon, lat, t = _resample(way["coords"], STEP)
        if len(lon) < 2 or t[-1] < 100:
            continue
        share = float((sh.sample(sh.dark_dist, lon, lat) <= sh.rail_tol).mean())
        on = "shown" if share >= 0.6 else "partly" if share >= 0.3 else "not seen"
        geom = LineString(way["coords"])
        mid = geom.interpolate(0.5, normalized=True)
        name, year = sh.sheet_at(mid.x, mid.y)
        status = way["tags"].get("railway", "")
        conf = {"shown": "high" if (year or 9999) <= 1950 else "medium", "partly": "medium", "not seen": "low"}[on]
        out.append(_feature(geom, {
            "kind": "rail", "osm_status": status, "on_sheet": on, "name": way["tags"].get("name", ""),
            "source": sh.words(name, year), "source_date": str(year) if year else "",
            "geometry_source": f"osm:way/{way['id']}",
            "validity": (_validity("rail", year, sh.battle) if on != "not seen" else
                         f"OSM records a railway here ({status}); the sheet's railway line isn't seen beside it"),
            "confidence": conf,
            "note": (f"OSM alignment ({status}); the sheet's dark line work lies within {sh.rail_tol:.0f} m along "
                     f"{share:.0%} of it. Dark ink also takes lettering and hachures: a crowded stretch may read as "
                     "shown when it isn't.")}))
    return out


def water(ways: list[dict]) -> list[dict]:
    out = []
    for way in ways:
        t = way["tags"]
        if t.get("waterway") == "stream" and not t.get("name"):
            continue
        out.append(_feature(LineString(way["coords"]), {
            "kind": "river" if t.get("waterway") in ("river", "canal") else "stream", "name": t.get("name", ""),
            "source": "OpenStreetMap", "source_date": "", "geometry_source": f"osm:way/{way['id']}",
            "validity": "today's course; a reference, not a 1944 survey", "confidence": "reference",
            "note": "Rivers here have moved little since 1944; drainage works may have straightened streams."}))
    return out


def woods(sh: Sheet) -> list[dict]:
    """The woods as the sheet prints them (green), as polygons: the period's woodland, not today's. The sheet's tree
    signs and lettering break the green, so it is closed and opened before tracing, and a patch under 2 ha dropped."""
    import rasterio.features
    from shapely.geometry import Polygon
    a = sh.rgb.astype(np.int16)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    green = (g > r + 25) & (g > b + 5) & (g > 110)
    green = ndimage.binary_opening(ndimage.binary_closing(green, np.ones((9, 9))), np.ones((5, 5)))
    green = ndimage.binary_fill_holes(green)
    lab, n = ndimage.label(green)
    sizes = ndimage.sum(green, lab, range(1, n + 1)) * sh.mpp ** 2
    keep = np.isin(lab, np.flatnonzero(sizes >= 20_000) + 1)
    out = []
    for geom, _ in rasterio.features.shapes(keep.astype(np.uint8), mask=keep):
        rings = []
        for ring in geom["coordinates"]:
            ring = np.asarray(ring, dtype=float)
            lon, lat = sh.lonlat(ring[:, 0], ring[:, 1])
            rings.append(list(zip(lon.tolist(), lat.tolist())))
        poly = Polygon(rings[0], rings[1:]).simplify(0.00012)
        if poly.is_empty or not poly.is_valid:
            poly = poly.buffer(0)
        if poly.is_empty:
            continue
        c = poly.representative_point()
        name, year = sh.sheet_at(c.x, c.y)
        out.append(_feature(poly, {
            "kind": "wood", "source": sh.words(name, year), "source_date": str(year) if year else "",
            "geometry_source": f"traced:{sh.ref(name)}", "validity": (
                f"printed as woodland on the {year} edition" if year else "outside the 1950 series' sheets"),
            "confidence": "medium", "note": "Traced from the sheet's green, closed over its tree signs; edges good "
                                            "to about 30 m. Clearings and felling since 1944 aren't known here."}))
    return out


LANGUAGE = ""      # set by build() from the extent: "fr" names Tunisia's places in French, as its 1942 sheets do


def _name(p: dict) -> str:
    """A place's name in the period maps' language (the extent's `language`, else the local name)."""
    if LANGUAGE:
        return p.get(f"name_{LANGUAGE}") or p.get("name") or p.get("name_en") or ""
    return p.get("name") or p.get("name_en") or ""


def places(nodes: list[dict]) -> list[dict]:
    out = []
    for p in nodes:
        if p["place"] not in ("town", "village", "city") or not _name(p):
            continue
        out.append(_feature(Point(p["lon"], p["lat"]), {
            "kind": "place", "name": _name(p), "place": p["place"], "population": p.get("population", ""),
            "source": "OpenStreetMap", "source_date": "",
            "geometry_source": f"osm:node/{p['id']}", "validity": "today's place; the town or village is on the sheet",
            "confidence": "reference", "note": "The name and point are today's; check the sheet for its 1940s form."}))
    return out


def peaks(nodes: list[dict]) -> list[dict]:
    return [_feature(Point(p["lon"], p["lat"]), {
        "kind": "hill", "name": _name(p), "ele": p.get("ele", ""), "source": "OpenStreetMap", "source_date": "",
        "geometry_source": f"osm:node/{p['id']}", "validity": "today's name and summit; a reference",
        "confidence": "reference", "note": "Check the name against the sheet and the after-action reports, which may "
                                           "call the hill by its height."}) for p in nodes]


CATHEDRAL_WORDS = ("cathédrale", "cathedral", "cattedrale", "kathedrale")


def churches(found: list[dict]) -> list[dict]:
    """Churches, from OSM's Christian places of worship: one a building, the node and the building of one church
    taken once. A cathedral by OSM's tags or its name. Catholic means in communion with Rome (Roman and Eastern
    Catholic alike; an Old Catholic church isn't); untagged, taken as Catholic. Today's buildings: one OSM dates after
    1945 (`start_date`) is dropped; whether the rest stood in 1945 is checked by hand."""
    out: list[dict] = []
    for c in sorted(found, key=lambda c: not c["id"].startswith(("way", "relation"))):   # the building first
        if any(math.hypot((c["lon"] - o["geometry"]["coordinates"][0]) * 73000,
                          (c["lat"] - o["geometry"]["coordinates"][1]) * 111000) < 60 for o in out):
            continue
        year = (c.get("start_date") or "")[:4]
        if year.isdigit() and int(year) > 1945:
            continue
        name = _name(c)
        den = c.get("denomination", "")
        catholic = ("catholic" in den and den != "old_catholic") or (not den and c.get("religion", "christian") == "christian")
        cathedral = c.get("building") == "cathedral" or c.get("place_of_worship") == "cathedral" or \
            any(w in name.lower() for w in CATHEDRAL_WORDS)
        out.append(_feature(Point(c["lon"], c["lat"]), {
            "kind": "cathedral" if cathedral else "church", "name": name, "denomination": den, "catholic": catholic,
            "start_date": c.get("start_date", ""), "wikidata": c.get("wikidata", ""), "source": "OpenStreetMap",
            "source_date": "", "geometry_source": f"osm:{c['id']}", "validity": "today's building and name",
            "confidence": "reference",
            "note": ("Catholic by OSM's denomination tag." if den else "No denomination tagged; taken as Catholic: "
                     "check.") if catholic else f"Denomination {den}."}))
    return out


def junctions(ex: Extent, sh: Sheet, place_feats: list[dict]) -> list[dict]:
    """Where three or more period roads meet, read off the sheet's own red network: branch points of its skeleton,
    with the branches counted where they leave a 150 m ring round the point, each branch solid or dashed by how much
    red lies along it. Named from the nearest town or village."""
    if sh.style != "red" or sh.kind != "scan50":    # read off IGN's red network only
        return []
    net = ndimage.binary_closing(sh.red, structure=np.ones((11, 11)))
    skel = skeletonize(net)
    nb = ndimage.convolve(skel.astype(np.uint8), np.ones((3, 3), dtype=np.uint8), mode="constant") - 1
    branch = skel & (nb >= 3)
    lab, _ = ndimage.label(ndimage.binary_dilation(branch, iterations=int(60 / sh.mpp)))
    ring_r = 150 / sh.mpp
    to = ex.to_crs
    pts = [(to.transform(*f["geometry"]["coordinates"]), f["properties"]["name"], f["properties"]["place"])
           for f in place_feats]
    out = []
    R = int(ring_r)
    for k, sl in enumerate(ndimage.find_objects(lab), 1):
        if sl is None:
            continue
        rr, cc = np.nonzero(lab[sl] == k)
        r0, c0 = int(rr.mean()) + sl[0].start, int(cc.mean()) + sl[1].start
        if r0 < R + 2 or c0 < R + 2 or r0 + R + 2 >= skel.shape[0] or c0 + R + 2 >= skel.shape[1]:
            continue
        win = skel[r0 - R - 2:r0 + R + 3, c0 - R - 2:c0 + R + 3]
        yy, xx = np.mgrid[-R - 2:R + 3, -R - 2:R + 3]
        d = np.hypot(yy, xx)
        annulus = win & (d >= R - 2) & (d <= R + 2)
        alab, branches = ndimage.label(annulus, structure=np.ones((3, 3)))
        if branches < 3:
            continue
        solid = 0
        for b in range(1, branches + 1):
            br, bc = np.nonzero(alab == b)
            # a solid red road: red ink under most of the branch near the ring
            rr2, cc2 = br + r0 - R - 2, bc + c0 - R - 2
            solid += int(sh.red[np.clip(rr2, 0, sh.red.shape[0] - 1), np.clip(cc2, 0, sh.red.shape[1] - 1)].mean() > 0.7)
        lon, lat = sh.lonlat(c0, r0)
        x, y = to.transform(lon, lat)
        near = sorted((math.hypot(px - x, py - y), name, kind) for (px, py), name, kind in pts)
        dist, name, kind = near[0] if near else (1e9, "", "")
        out.append(_feature(Point(float(lon), float(lat)), {
            "kind": "junction", "branches": int(branches), "solid_branches": int(solid),
            "name": name if dist < 700 else "", "place": kind if dist < 700 else "",
            "importance": int(branches + solid + (2 if kind == "town" and dist < 700 else 0)),
            "source": "derived from the sheet's red network", "source_date": "",
            "geometry_source": "derived", "validity": "where the period roads meet, as the sheet draws them",
            "confidence": "medium",
            "note": (f"{branches} branches leave a 150 m ring, {solid} of them solid red; "
                     + (f"named from the nearest town or village, {dist:.0f} m" if dist < 700 else
                        "no town or village within 700 m"))}))
    out.sort(key=lambda f: -f["properties"]["importance"])
    # one junction a place: a town's several branch points within 400 m are one crossroads on a page
    kept: list[dict] = []
    for f in out:
        x, y = to.transform(*f["geometry"]["coordinates"])
        if all(math.hypot(x - kx, y - ky) > 400 for kx, ky in (to.transform(*k["geometry"]["coordinates"]) for k in kept)):
            kept.append(f)
    return kept


def crossings(ex: Extent, road_feats: list[dict], rail_feats: list[dict], water_feats: list[dict]) -> list[dict]:
    to = ex.to_crs

    def proj(f):
        xs, ys = to.transform(*np.array(f["geometry"]["coordinates"]).T)
        return LineString(list(zip(xs, ys)))
    rivers = [(proj(f), f["properties"]["name"]) for f in water_feats if f["properties"]["kind"] == "river"]
    out, seen = [], []
    back = ex.to_lonlat
    for feats, what in ((road_feats, "road"), ([f for f in rail_feats if f["properties"]["on_sheet"] != "not seen"], "rail")):
        for f in feats:
            g = proj(f)
            for rv, rname in rivers:
                if not g.intersects(rv):
                    continue
                inter = g.intersection(rv)
                for p in getattr(inter, "geoms", [inter]):
                    if p.geom_type != "Point" or any(math.hypot(p.x - q[0], p.y - q[1]) < 60 for q in seen):
                        continue
                    seen.append((p.x, p.y))
                    lon, lat = back.transform(p.x, p.y)
                    out.append(_feature(Point(lon, lat), {
                        "kind": "crossing", "carries": what, "river": rname,
                        "road_class": f["properties"].get("road_class", "") if what == "road" else "",
                        "source": "derived", "source_date": "",
                        "geometry_source": f"derived: {f['properties']['geometry_source']} × river",
                        "validity": "where a period road or railway crosses a river", "confidence": "medium",
                        "note": "A crossing of today's river course; the 1944 bridge, ford or causeway isn't recorded here."}))
    return out


def build(ex: Extent) -> dict:
    """Reconstruct the extent's period network and write it to atlas/<extent>/infrastructure/."""
    global LANGUAGE
    LANGUAGE = ex.language
    sh = Sheet(ex)
    o = sources.osm(ex.sources["geofabrik"], sh.box)
    r = roads(sh, o["roads"])
    rl = rails(sh, o["rails"])
    wt = water(o["water"])
    pl = places(o["places"])
    pk = peaks(o.get("peaks", []))
    wd = woods(sh)
    ch = churches(o.get("churches", [])) if ex.churches else []
    jn = junctions(ex, sh, pl)
    cr = crossings(ex, r, rl, wt)
    folder = ex.infrastructure
    folder.mkdir(parents=True, exist_ok=True)
    layers = {"roads": r, "rails": rl, "water": wt, "places": pl, "hills": pk, "woods": wd, "churches": ch, "junctions": jn,
              "crossings": cr}
    for name, feats in layers.items():
        (folder / f"{name}.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": feats},
                                                           ensure_ascii=False, separators=(",", ":")))
    manifest = {
        "extent": ex.name, "built": date.today().isoformat(),
        "sources": {
            "period_map": {"kind": sh.kind, "metres_per_pixel": round(sh.mpp, 2),
                           "sheets": [{"sheet": sh.ref(n), "edition": y} for _, n, y in sh.sheets],
                           "placing": sh.placing,
                           **({"layer": sources.SCAN50, "zoom": sh.z} if sh.kind == "scan50" else {})},
            "osm": {"extract": ex.sources["geofabrik"], "licence": "ODbL, (c) OpenStreetMap contributors"},
        },
        "tolerances": {"road_m": sh.road_tol, "road_degrees": ROAD_ANGLE, "rail_m": sh.rail_tol, "step_m": STEP,
                       "link_ink_m": LINK_TOL, "link_gap_m": LINK_GAP, "connector_m": LINK_LEN,
                       "connector_snap_m": LINK_SNAP, "trace_snap_m": TRACE_SNAP,
                       "join_m": JOIN, "isolated_under_m": ISOLATED},
        "counts": {k: len(v) for k, v in layers.items()},
        "roads": {"osm_aligned": sum(1 for f in r if f["properties"]["geometry_source"].startswith("osm")),
                  "traced": sum(1 for f in r if f["properties"]["geometry_source"].startswith("traced")),
                  "connectors": sum(1 for f in r if f["properties"].get("connector")),
                  "bridged_km": round(sum(f["properties"].get("bridged_m", 0) for f in r) / 1000, 1),
                  "joined_km": round(sum(f["properties"].get("joined_m", 0) for f in r) / 1000, 1),
                  "isolated": sum(1 for f in r if f["properties"].get("isolated"))},
        "rails_on_sheet": {k: sum(1 for f in rl if f["properties"]["on_sheet"] == k) for k in ("shown", "partly", "not seen")},
    }
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=1))
    return manifest
