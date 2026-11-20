"""A printed map's base: water, boundaries, terrain, towns and labels, drawn as SVG for a geo.Frame.

Layers, all cached under <cache>/ and always re-downloadable:
  Natural Earth 1:10m (nvkelso/natural-earth-vector's GeoJSON, as the kit's tools/build_relief.py uses): rivers (the
  world's set and the European and North American supplements), lakes, state and province lines, country borders,
  populated places, and the states' label points. Cached in <cache>/geo/ne/.
  Relief: the AWS Terrain Tiles (Terrarium), shaded as the kit's relief is (sun from the north-west, 45 degrees up,
  1.5x vertical exaggeration). The tiles share <cache>/terrain-tiles/ with the kit; a shaded box is cached in
  <cache>/geo/relief/.

Readability first: every line is simplified to a fraction of a point at the printed scale; a town is labelled only
where its label clears every label placed before it; boundaries and water stay pale under the record's own marks.
"""
import base64
import hashlib
import io
import json
import math
import urllib.request
from functools import cache
from html import escape

from PIL import Image

from . import geo, paths

NE = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/{}.geojson"
TILES = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"

SEA, LAND, COAST = "#dde7ea", "#f1f2ec", "#93aab3"
WATER, WATER_INK = "#7d9dab", "#4f7484"
ADMIN, BORDER, TOWN, REGION = "#9ba49a", "#727b70", "#4a5249", "#8a9388"
DISPLAY = "IBM Plex Sans, IBM Plex Sans Condensed, Arial Narrow, sans-serif"
SERIF = "Libertinus Serif, Georgia, serif"


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "wwii-book (research kit)"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read()


@cache
def natural(name: str) -> dict:
    f = paths.cache() / "geo" / "ne" / f"{name}.geojson"
    if not f.exists():
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(_get(NE.format(name)))
    return json.loads(f.read_text(encoding="utf-8"))


def _lines(geom: dict) -> list[list[list[float]]]:
    t = geom["type"]
    if t == "LineString":
        return [geom["coordinates"]]
    if t == "MultiLineString":
        return geom["coordinates"]
    if t == "Polygon":
        return geom["coordinates"]
    if t == "MultiPolygon":
        return [r for poly in geom["coordinates"] for r in poly]
    return []


def _touches(pts, box) -> bool:
    w, s, e, n = box
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return max(xs) >= w and min(xs) <= e and max(ys) >= s and min(ys) <= n


def simplify(pts: list[tuple[float, float]], tol: float) -> list[tuple[float, float]]:
    """Douglas-Peucker on page points: drops what can't be seen at the printed size. A closed ring (first point = last)
    is split at its farthest point and each half simplified, since the line from a point to itself measures nothing."""
    if len(pts) < 3:
        return pts
    if math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) < 1e-6:
        k = max(range(len(pts)), key=lambda i: math.hypot(pts[i][0] - pts[0][0], pts[i][1] - pts[0][1]))
        if 0 < k < len(pts) - 1:
            return simplify(pts[:k + 1], tol) + simplify(pts[k:], tol)[1:]
        return pts
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        a, b = stack.pop()
        (x1, y1), (x2, y2) = pts[a], pts[b]
        dx, dy = x2 - x1, y2 - y1
        norm = math.hypot(dx, dy) or 1e-9
        far, at = 0.0, -1
        for i in range(a + 1, b):
            d = abs(dy * (pts[i][0] - x1) - dx * (pts[i][1] - y1)) / norm
            if d > far:
                far, at = d, i
        if far > tol:
            keep[at] = True
            stack += [(a, at), (at, b)]
    return [p for p, k in zip(pts, keep) if k]


def _path(f: geo.Frame, x0: float, coords, tol: float = 0.35, close: bool = False) -> str:
    pts = simplify([(x0 + x, y) for x, y in (f.xy(c[0], c[1]) for c in coords)], tol)
    if len(pts) < 2:
        return ""
    d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    return d + (" Z" if close else "")


# ---------------------------------------------------------------- relief

def _tile(z: int, x: int, y: int) -> Image.Image:
    f = paths.cache() / "terrain-tiles" / f"{z}-{x}-{y}.png"
    if not f.exists():
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(_get(TILES.format(z=z, x=x, y=y)))
    return Image.open(io.BytesIO(f.read_bytes())).convert("RGB")


def _txy(lon: float, lat: float, z: int) -> tuple[float, float]:
    n = 2 ** z
    y = (1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n
    return (lon + 180) / 360 * n, y


def _lonlat(x: float, y: float, z: int) -> tuple[float, float]:
    n = 2 ** z
    return x / n * 360 - 180, math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))


def _on_land(png: bytes, strength: float) -> bytes:
    """The hillshade (grey light and shadow, alpha by strength) laid on the land tint at `strength`: an opaque RGB
    image of what the translucent overlay looked like on the land."""
    with Image.open(io.BytesIO(png)) as im:
        shade = im.convert("LA")
    mask = shade.getchannel("A").point(lambda v: round(v * strength))
    land = Image.new("RGB", shade.size, LAND)
    out = Image.composite(shade.getchannel("L").convert("RGB"), land, mask)
    buf = io.BytesIO()
    out.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def relief(box: tuple[float, float, float, float], z: int) -> tuple[bytes, tuple[float, float, float, float]]:
    """A hillshade of the box as a PNG (black shadow, white light, alpha by strength; sea and flat ground clear), and
    the exact box its pixels cover."""
    w, s, e, n = box
    key = hashlib.sha1(json.dumps([round(v, 4) for v in box] + [z]).encode()).hexdigest()[:16]
    out = paths.cache() / "geo" / "relief" / f"{key}.png"
    meta = out.with_suffix(".json")
    if out.exists() and meta.exists():
        return out.read_bytes(), tuple(json.loads(meta.read_text()))
    x0, y0 = _txy(w, n, z)
    x1, y1 = _txy(e, s, z)
    tx0, ty0, tx1, ty1 = int(x0), int(y0), int(x1), int(y1)
    mosaic = Image.new("RGB", ((tx1 - tx0 + 1) * 256, (ty1 - ty0 + 1) * 256))
    for tx in range(tx0, tx1 + 1):
        for ty in range(ty0, ty1 + 1):
            mosaic.paste(_tile(z, tx, ty), ((tx - tx0) * 256, (ty - ty0) * 256))
    cx0, cy0, cx1, cy1 = int((x0 - tx0) * 256), int((y0 - ty0) * 256), int((x1 - tx0) * 256), int((y1 - ty0) * 256)
    mosaic = mosaic.crop((cx0, cy0, cx1, cy1))
    W, H = mosaic.size
    rgb = mosaic.tobytes()
    elev = [[rgb[k] * 256 + rgb[k + 1] + rgb[k + 2] / 256 - 32768 for k in range(3 * W * j, 3 * W * (j + 1), 3)]
            for j in range(H)]
    mpp = 40075016.686 * math.cos(math.radians((s + n) / 2)) / (256 * 2 ** z)
    shade = Image.new("LA", (W, H))
    sp = shade.load()
    assert sp is not None
    az, alt = math.radians(315), math.radians(45)
    flat = math.sin(alt)
    for j in range(H):
        row, up, down = elev[j], elev[max(j - 1, 0)], elev[min(j + 1, H - 1)]
        for i in range(W):
            if row[i] <= 0:
                sp[i, j] = (0, 0)
                continue
            dzdx = (row[min(i + 1, W - 1)] - row[max(i - 1, 0)]) / (2 * mpp)
            dzdy = (down[i] - up[i]) / (2 * mpp)
            slope = math.atan(1.5 * math.hypot(dzdx, dzdy))
            aspect = math.atan2(dzdy, -dzdx)
            hs = math.sin(alt) * math.cos(slope) + math.cos(alt) * math.sin(slope) * math.cos(az - aspect)
            v = hs - flat
            sp[i, j] = (255, min(150, int(v * 420))) if v > 0 else (0, min(190, int(-v * 520)))
    buf = io.BytesIO()
    shade.save(buf, "PNG", optimize=True)
    exact = (*_lonlat(tx0 + cx0 / 256, ty0 + cy1 / 256, z), *_lonlat(tx0 + cx1 / 256, ty0 + cy0 / 256, z))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(buf.getvalue())
    meta.write_text(json.dumps(exact))
    return buf.getvalue(), exact


# ---------------------------------------------------------------- labels

class Labels:
    """Places labels so that none overlaps another label or a mark, and, where there is room, none lies on a line.

    Hard obstacles (`occupy`): marks and labels already placed; a label never covers one. Soft obstacles (`line`): the
    route's legs, the fronts; a label avoids them when it can, and may cross one, on its white halo, when it can't.
    Positions are tried in order: beside the point in eight directions, then farther out in the same eight with a
    short leader line back to the point. Widths are estimated from the type size (IBM Plex Sans Condensed is narrow)."""

    def __init__(self, bounds: tuple[float, float, float, float]):
        self.bounds = bounds
        self.taken: list[tuple[float, float, float, float]] = []
        self.soft: list[tuple[float, float, float, float]] = []
        self.placed: list[tuple[float, float, float, float]] = []      # the labels themselves, for checking

    @staticmethod
    def width(text: str, size: float, family: str = DISPLAY) -> float:
        return len(text) * size * (0.49 if family == DISPLAY else 0.52)

    def occupy(self, x: float, y: float, w: float, h: float) -> None:
        self.taken.append((x, y, x + w, y + h))

    def line(self, pts: list[tuple[float, float]], pad: float = 1.2) -> None:
        """A drawn line as a soft obstacle: a chain of small boxes along it."""
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            n = max(1, int(math.hypot(x2 - x1, y2 - y1) / 4))
            for i in range(n):
                ax, ay = x1 + (x2 - x1) * i / n, y1 + (y2 - y1) * i / n
                bx, by = x1 + (x2 - x1) * (i + 1) / n, y1 + (y2 - y1) * (i + 1) / n
                self.soft.append((min(ax, bx) - pad, min(ay, by) - pad, max(ax, bx) + pad, max(ay, by) + pad))

    @staticmethod
    def _clear(r, boxes) -> bool:
        return all(r[2] < t[0] or r[0] > t[2] or r[3] < t[1] or r[1] > t[3] for t in boxes)

    def free(self, r: tuple[float, float, float, float], soft: bool = False) -> bool:
        bx0, by0, bx1, by1 = self.bounds
        if r[0] < bx0 + 2 or r[2] > bx1 - 2 or r[1] < by0 + 2 or r[3] > by1 - 2:
            return False
        return self._clear(r, self.taken) and (not soft or self._clear(r, self.soft))

    def _options(self, x: float, y: float, w: float, h: float, gap: float):
        for d, lead in ((gap, False), (gap * 3.2, True), (gap * 6, True)):
            yield x + d, y - h / 2, lead                      # right
            yield x - d - w, y - h / 2, lead                  # left
            yield x - w / 2, y - d - h, lead                  # above
            yield x - w / 2, y + d, lead                      # below
            yield x + d * 0.7, y - d * 0.7 - h, lead          # above right
            yield x - d * 0.7 - w, y - d * 0.7 - h, lead      # above left
            yield x + d * 0.7, y + d * 0.7, lead              # below right
            yield x - d * 0.7 - w, y + d * 0.7, lead          # below left

    def place(self, x: float, y: float, lines: list[tuple[str, float, str, str, str]], force: bool = False,
              gap: float = 3.5) -> str:
        """Lines of (text, size, colour, weight, family) near the point (x, y), at the first position clear of marks,
        labels and lines; failing that, clear of marks and labels; failing that, nowhere (or, with `force`, beside
        the point on the right, whatever it covers: a station's name is never dropped)."""
        w = max(self.width(t, s, fam) for t, s, _, _, fam in lines)
        h = sum(s * 1.15 for _, s, _, _, _ in lines)
        choice = None
        for soft in (True, False):
            for lx, ly, lead in self._options(x, y, w, h, gap):
                if self.free((lx, ly, lx + w, ly + h), soft=soft):
                    choice = (lx, ly, lead)
                    break
            if choice:
                break
        if choice is None:
            if not force:
                return ""
            # nowhere is clear: the position that covers least of the marks and labels already there
            def covered(o):
                lx, ly, _ = o
                return sum(max(0.0, min(lx + w, t[2]) - max(lx, t[0])) * max(0.0, min(ly + h, t[3]) - max(ly, t[1]))
                           for t in self.taken) + (1e6 if not self.free((lx, ly, lx + w, ly + h)) and
                                                   (lx < self.bounds[0] or lx + w > self.bounds[2]) else 0)
            choice = min(self._options(x, y, w, h, gap), key=covered)
        lx, ly, lead = choice
        r = (lx, ly, lx + w, ly + h)
        self.taken.append(r)
        self.placed.append(r)
        out = []
        if lead:   # a leader from the point to the label's nearest edge
            ex = min(max(x, lx), lx + w)
            ey = min(max(y, ly), ly + h)
            out.append(f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{ex:.1f}" y2="{ey:.1f}" stroke="#5d675b" stroke-width="0.4"/>')
        cy = ly
        for text, size, colour, weight, fam in lines:
            cy += size * 1.0
            italic = ' font-style="italic"' if fam == SERIF else ""
            out.append(f'<text x="{lx:.1f}" y="{cy:.1f}" font-family="{fam}" font-size="{size}" fill="{colour}" '
                       f'font-weight="{weight}"{italic} stroke="#ffffff" stroke-opacity="0.9" stroke-width="2.2" '
                       f'stroke-linejoin="round" paint-order="stroke">{escape(text)}</text>')
            cy += size * 0.15
        return "".join(out)


# ---------------------------------------------------------------- rivers by the map's scale

RIVER_LAYERS = ("ne_10m_rivers_lake_centerlines", "ne_10m_rivers_europe", "ne_10m_rivers_north_america")

# A river is drawn by the map's span (its longer side, km): (at least this span, the largest scalerank, at most so many
# rivers, each at least this share of the span inside the frame). A continent or an ocean shows only its great rivers
# (the Mississippi, the Missouri, the Columbia, not their tributaries), a theater its major ones (the Rhine, the
# Danube, the Seine are scalerank 2 to 4), a region the detail the old fixed rank of 7 gave.
RIVER_SCALE = (
    (2500.0, 5, 8, 0.10),     # the United States, an ocean
    (1000.0, 5, 12, 0.04),    # a theater: northern Europe, North Africa
    (400.0, 6, None, 0.0),    # a country's coast: the eastern seaboard
    (0.0, 7, None, 0.0),      # a region: a battery's week, a town
)


def span_km(f: geo.Frame) -> float:
    """A frame's longer side in kilometres (east-west at its middle latitude, or north-south)."""
    mid = math.radians((f.lat0 + f.lat1) / 2)
    return max((f.lon1 - f.lon0) * 111.32 * math.cos(mid), (f.lat1 - f.lat0) * 110.57)


def river_scale(f: geo.Frame) -> tuple[int, int | None, float]:
    """(largest scalerank, at most so many rivers, the least share of the span) for a frame, from RIVER_SCALE."""
    km = span_km(f)
    _, rank, most, share = next(t for t in RIVER_SCALE if km >= t[0])
    return rank, most, share


def _km_inside(geom: dict, box: tuple[float, float, float, float]) -> float:
    """A line's length inside the box, km (each segment whose midpoint falls inside)."""
    w, s, e, n = box
    total = 0.0
    for line in _lines(geom):
        for (a, b), (c, d) in zip(line, line[1:]):
            mx, my = (a + c) / 2, (b + d) / 2
            if w <= mx <= e and s <= my <= n:
                total += math.hypot((c - a) * math.cos(math.radians(my)), d - b) * 111.2
    return total


def select_rivers(features: list[dict], f: geo.Frame, rivers: int | str | None = "auto") -> list[tuple[dict, float]]:
    """The river features a frame draws, with each one's rank. A number is the largest scalerank, every river up to it
    (the figure's override); "auto" or None takes the rank from the map's span and, on a wide map, keeps only the
    longest few: a river is its features of one name (or Natural Earth's river number), measured inside the frame."""
    if rivers is not None and rivers != "auto":
        top, most, share = int(rivers), None, 0.0
    else:
        top, most, share = river_scale(f)
    if top <= 0:
        return []
    kept = []
    for feat in features:
        rank = feat["properties"].get("scalerank")
        rank = 10 if rank is None else rank
        if rank <= top and feat["geometry"]:
            kept.append((feat, rank))
    if most is None and not share:
        return kept
    box = (f.lon0, f.lat0, f.lon1, f.lat1)
    groups: dict[str, list] = {}
    for feat, rank in kept:
        p = feat["properties"]
        key = p.get("name") or f"#{p.get('rivernum')}"
        g = groups.setdefault(key, [rank, 0.0, []])
        g[0] = min(g[0], rank)
        g[1] += _km_inside(feat["geometry"], box)
        g[2].append((feat, rank))
    least = share * span_km(f)
    ranked = sorted((g for g in groups.values() if g[1] > 0 and g[1] >= least), key=lambda g: -g[1])
    return [fr for g in ranked[:most] for fr in g[2]]


LAKE_LAYERS = ("ne_10m_lakes", "ne_10m_lakes_europe", "ne_10m_lakes_north_america")
WIDE_LAKES = (1000.0, 6)      # on a map this wide (km) or wider, only the world layer's lakes up to this scalerank


def select_lakes(features: list[dict], f: geo.Frame) -> list[dict]:
    """On a wide map, the larger lakes alone (the supplements' ponds print as specks); on a close one, every lake."""
    if span_km(f) < WIDE_LAKES[0]:
        return features
    return [ft for ft in features if _rank(ft) <= WIDE_LAKES[1]]


def lakes_drawn(f: geo.Frame) -> list[dict]:
    """select_lakes over Natural Earth's lake layers: the supplements only on a map narrower than WIDE_LAKES."""
    names = LAKE_LAYERS if span_km(f) < WIDE_LAKES[0] else LAKE_LAYERS[:1]
    return select_lakes([ft for name in names for ft in natural(name)["features"]], f)


def rivers_drawn(f: geo.Frame, rivers: int | str | None = "auto") -> list[tuple[dict, float]]:
    """select_rivers over Natural Earth's three river layers."""
    return select_rivers([ft for name in RIVER_LAYERS for ft in natural(name)["features"]], f, rivers)


# ---------------------------------------------------------------- the base

def _rank(ft: dict) -> float:
    r = ft["properties"].get("scalerank")
    return 10 if r is None else r          # 0 is Natural Earth's most important rank, not a missing one


def base(f: geo.Frame, x0: float, H: float, *, relief_zoom: int | None = None, admin: bool = False,
         countries: tuple[str, ...] = (), rivers: int | str | None = "auto", towns: int = 0, town_rank: int = 8,
         places: tuple = (), labels: Labels | None = None) -> tuple[list[str], list[str]]:
    """The base map for a frame placed at x0: (layers under the record's marks, labels over them).

    rivers: "auto" (or None) draws them by the map's scale (river_scale); a number overrides it, every river up to that
    Natural Earth scalerank (lower is more important; 0 none, 10 to 12 the supplements' detail); towns: how many towns to try to label
    (most important first), down to town_rank; admin: state and province lines, and region names for `countries`
    (Natural Earth's admin names, e.g. "United States of America")."""
    box = (f.lon0, f.lat0, f.lon1, f.lat1)
    wide = (f.lon0 - 0.5, f.lat0 - 0.5, f.lon1 + 0.5, f.lat1 + 0.5)
    under, over = [], []
    under.append(f'<rect x="{x0:.1f}" width="{f.width:.1f}" height="{H:.1f}" fill="{SEA}"/>')
    land = [d for d in (_path(f, x0, ring, tol=0.3, close=True) for ring in geo.land_rings(wide)) if d]
    for d in land:
        under.append(f'<path d="{d}" fill="{LAND}" stroke="{COAST}" stroke-width="0.5" stroke-linejoin="round"/>')
    if relief_zoom and land:
        # the hillshade is composited onto the land tint here, at its 55 per cent, and clipped to the land, so the
        # page carries an opaque image and no transparency; the coast is drawn again over its edge
        png, (rw, rs, re_, rn) = relief(box, relief_zoom)
        (ax, ay), (bx, by) = f.xy(rw, rn), f.xy(re_, rs)
        href = "data:image/png;base64," + base64.b64encode(_on_land(png, 0.55)).decode()
        clip = "land-" + hashlib.sha1(json.dumps([round(v, 4) for v in box]).encode()).hexdigest()[:8]
        under.append(f'<clipPath id="{clip}"><path d="{" ".join(land)}"/></clipPath>')
        under.append(f'<image x="{x0 + ax:.1f}" y="{ay:.1f}" width="{bx - ax:.1f}" height="{by - ay:.1f}" '
                     f'preserveAspectRatio="none" clip-path="url(#{clip})" href="{href}"/>')
        under += [f'<path d="{d}" fill="none" stroke="{COAST}" stroke-width="0.5" stroke-linejoin="round"/>'
                  for d in land]
    for feat in lakes_drawn(f):
        for ring in _lines(feat["geometry"] or {"type": ""}):
            if _touches(ring, wide):
                d = _path(f, x0, ring, tol=0.3, close=True)
                if d:
                    under.append(f'<path d="{d}" fill="{SEA}" stroke="{COAST}" stroke-width="0.35"/>')
    for feat, rank in rivers_drawn(f, rivers):
        width = max(0.3, 1.05 - 0.065 * rank)
        for line in _lines(feat["geometry"]):
            if _touches(line, wide):
                d = _path(f, x0, line)
                if d:
                    under.append(f'<path d="{d}" fill="none" stroke="{WATER}" stroke-width="{width:.2f}" '
                                 f'stroke-linecap="round" stroke-linejoin="round"/>')
    if admin:
        for feat in natural("ne_10m_admin_1_states_provinces_lines")["features"]:
            if countries and feat["properties"].get("ADM0_NAME", feat["properties"].get("adm0_name")) not in countries:
                continue
            for line in _lines(feat["geometry"] or {"type": ""}):
                if _touches(line, wide):
                    d = _path(f, x0, line)
                    if d:
                        under.append(f'<path d="{d}" fill="none" stroke="{ADMIN}" stroke-width="0.45" '
                                     f'stroke-dasharray="2.2 1.4"/>')
    for feat in natural("ne_10m_admin_0_boundary_lines_land")["features"]:
        for line in _lines(feat["geometry"] or {"type": ""}):
            if _touches(line, wide):
                d = _path(f, x0, line)
                if d:
                    under.append(f'<path d="{d}" fill="none" stroke="{BORDER}" stroke-width="0.8" '
                                 f'stroke-dasharray="4 1.4 1 1.4"/>')
    # edge ticks, not a grid: every degree, or every half or quarter on a close map
    step = next(s for s in (0.25, 0.5, 1, 2, 5, 10) if (f.lon1 - f.lon0) / s <= 8)
    k = math.ceil(f.lon0 / step)
    while k * step <= f.lon1:
        lon = k * step
        x, _ = f.xy(lon, f.lat0)
        under.append(f'<line x1="{x0 + x:.1f}" y1="{H - 4:.1f}" x2="{x0 + x:.1f}" y2="{H:.1f}" stroke="{BORDER}" stroke-width="0.5"/>')
        deg = abs(lon)
        txt = f"{int(deg)}°{int(round((deg % 1) * 60)):02d}′" if deg % 1 else f"{int(deg)}°"
        over.append(f'<text x="{x0 + x + 1.5:.1f}" y="{H - 5:.1f}" font-family="{DISPLAY}" font-size="5.5" fill="{BORDER}">'
                    f'{txt}{"W" if lon < 0 else "E"}</text>')
        k += 1
    k = math.ceil(f.lat0 / step)
    while k * step <= f.lat1:
        lat = k * step
        _, y = f.xy(f.lon0, lat)
        under.append(f'<line x1="{x0:.1f}" y1="{y:.1f}" x2="{x0 + 4:.1f}" y2="{y:.1f}" stroke="{BORDER}" stroke-width="0.5"/>')
        txt = f"{int(lat)}°{int(round((lat % 1) * 60)):02d}′" if lat % 1 else f"{int(lat)}°"
        over.append(f'<text x="{x0 + 5:.1f}" y="{y + 2:.1f}" font-family="{DISPLAY}" font-size="5.5" fill="{BORDER}">{txt}N</text>')
        k += 1
    # region names: spaced capitals at Natural Earth's label points
    if admin and countries:
        named: set[str] = set()
        for feat in natural("ne_10m_admin_1_label_points")["features"]:
            p = feat["properties"]
            if p.get("admin") not in countries or p.get("name") in named:
                continue
            lon, lat = feat["geometry"]["coordinates"][:2]
            if f.lon0 < lon < f.lon1 and f.lat0 < lat < f.lat1:
                x, y = f.xy(lon, lat)
                name = (p.get("name") or "").upper()
                size, spaced = 6.2, " ".join(name)
                w = Labels.width(spaced, size)
                if labels is None or labels.free((x0 + x - w / 2, y - 4, x0 + x + w / 2, y + 3)):
                    named.add(p.get("name"))
                    if labels is not None:
                        labels.occupy(x0 + x - w / 2, y - 4, w, 7)
                    over.append(f'<text x="{x0 + x:.1f}" y="{y:.1f}" font-family="{DISPLAY}" font-size="{size}" '
                                f'fill="{REGION}" text-anchor="middle" letter-spacing="0.6">{escape(name)}</text>')
    # reference places the book names (a town for orientation, not a place a record puts him): open dots
    if places and labels is not None:
        for name, lon, lat in places:
            if f.lon0 < lon < f.lon1 and f.lat0 < lat < f.lat1:
                x, y = f.xy(lon, lat)
                svg = labels.place(x0 + x, y, [(name, 6.8, TOWN, "normal", SERIF)])
                if svg:
                    over.append(f'<circle cx="{x0 + x:.1f}" cy="{y:.1f}" r="1.4" fill="#ffffff" stroke="{TOWN}" '
                                f'stroke-width="0.6"/>' + svg)
    # towns, most important first, where their labels fit
    if towns and labels is not None:
        candidates = [ft for ft in natural("ne_10m_populated_places_simple")["features"]
                  if f.lon0 < ft["geometry"]["coordinates"][0] < f.lon1 and f.lat0 < ft["geometry"]["coordinates"][1] < f.lat1
                  and _rank(ft) <= town_rank]
        candidates.sort(key=lambda ft: (_rank(ft), -(ft["properties"].get("pop_max") or 0)))
        placed = 0
        for ft in candidates:
            if placed >= towns:
                break
            lon, lat = ft["geometry"]["coordinates"][:2]
            x, y = f.xy(lon, lat)
            svg = labels.place(x0 + x, y, [(ft["properties"]["name"], 6.6, TOWN, "normal", SERIF)])
            if svg:
                over.append(f'<circle cx="{x0 + x:.1f}" cy="{y:.1f}" r="1.2" fill="{TOWN}"/>' + svg)
                placed += 1
    return under, over
