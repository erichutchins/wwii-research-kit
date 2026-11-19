"""The operational panorama: the extent from above, in the atlas's CRS, as SVG for print.

The military information leads: the day's front (and an earlier one, fainter, for the ground gained), and the
divisions where the army group's map drew them. The ground and the network sit under it, quieter: the terrain
(Copernicus GLO-30, shaded, with 20 m contours and the low marsh ground tinted), rivers, and the period roads and
railways reconstructed from IGN's 1:50,000 (reconstruct.py), in warm greys. A locator places the extent in the
campaign. Every layer's source and date is returned with the drawing, for the caption.

The network is an illustration of the period roads, one quiet background: a road only the sheet shows is drawn on
the sheet's line like the rest, and loose ends are joined to the nearest road (reconstruct.py says how each was
made). How we know is drawn where it matters: a railway the sheet shows only in part is lighter; a division's box is
where the 1:500,000 sheet put its symbol, not the ground it held.
"""
import base64
import io
import json
import math
from html import escape

import numpy as np
import shapely
from PIL import Image
from skimage import measure

from .. import cartography as carto
from .. import figures, geo, halo, symbols
from . import record, terrain
from .extent import Extent, Page

INK, MUTED, PAPER, FRONT = "#000000", "#586257", "#fbfaf6", "#a3241b"
LAND, SEA, LOW = np.array([243, 241, 233]), np.array([214, 226, 230]), np.array([214, 226, 216])
ROAD, ROAD_MINOR, RAIL = "#7a6b55", "#8d8270", "#38352f"
WATER = "#7397a6"
OWN = "#a3241b"
WOOD = "#dbe5cf"
CATHEDRAL = "#4b2c6f"
RAID = "#4d5963"
CONTOUR = "#b9ab8f"
LOW_CSS = "rgb({},{},{})".format(*LOW.tolist())
DISPLAY, SERIF = figures.DISPLAY, figures.SERIF


def _load(ex: Extent, layer: str) -> list[dict]:
    return json.loads((ex.infrastructure / f"{layer}.geojson").read_text())["features"]


def _lines(geom: dict) -> list[list[tuple[float, float]]]:
    return [geom["coordinates"]] if geom["type"] == "LineString" else list(geom["coordinates"])


class _Draw:
    """Lon/lat lines and points onto the page, through the extent's CRS."""

    def __init__(self, ex: Extent, page: Page, ox: float = 0.0, oy: float = 0.0):
        self.ex, self.page, self.ox, self.oy = ex, page, ox, oy

    def pts(self, coords) -> list[tuple[float, float]]:
        a = np.asarray(coords, dtype=float)
        x, y = self.ex.to_crs.transform(a[:, 0], a[:, 1])
        px, py = self.page.pt(x, y)
        return list(zip((px + self.ox).tolist(), (py + self.oy).tolist()))

    def pt(self, lon: float, lat: float) -> tuple[float, float]:
        return self.pts([(lon, lat)])[0]

    def path(self, coords, tol: float = 0.25) -> str:
        p = carto.simplify(self.pts(coords), tol)
        return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in p) if len(p) > 1 else ""


def _ticks(pts: list[tuple[float, float]], every: float, half: float) -> str:
    """A cross-tick every `every` points along a line: the railway's old map sign."""
    acc, out = every / 2, []
    for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
        seg = math.hypot(xb - xa, yb - ya)
        while seg > 0 and acc <= seg:
            tx, ty = xa + (xb - xa) * acc / seg, ya + (yb - ya) * acc / seg
            nx, ny = -(yb - ya) / seg * half, (xb - xa) / seg * half
            out.append(f"M{tx - nx:.1f},{ty - ny:.1f} L{tx + nx:.1f},{ty + ny:.1f}")
            acc += every
        acc -= seg
    return " ".join(out)


def _ground(ex: Extent, page: Page, res: float = 15.0) -> tuple[str, str, dict]:
    """The terrain as an image (land tone, hillshade, the low ground and the sea) and its contours as paths."""
    g = terrain.dem(ex, res=res)
    shade = terrain.hillshade(g, exaggeration=3.0)
    flat = math.sin(math.radians(45))                       # level ground's shade: no change there
    k = np.clip((shade - flat) * 0.9, -0.45, 0.25)[..., None]
    rgb = LAND * (1 + k)
    low = terrain.low_ground(g)[..., None]
    rgb = np.where(low, LOW * (1 + k * 0.5), rgb)
    rgb = np.where(terrain.sea(g)[..., None], SEA, rgb)
    im = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=88, optimize=True)
    gx0, gy1 = g.x0, g.y1
    gx1, gy0 = gx0 + g.shape[1] * res, gy1 - g.shape[0] * res
    (px0, py0), (px1, py1) = (page.pt(gx0, gy1)), (page.pt(gx1, gy0))
    image = (f'<image x="{float(px0):.2f}" y="{float(py0):.2f}" width="{float(px1 - px0):.2f}" '
             f'height="{float(py1 - py0):.2f}" preserveAspectRatio="none" '
             f'href="data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}"/>')
    # contours every 20 m, from a smoothed model so they read as the land's shape, not the model's noise
    from scipy import ndimage
    z = ndimage.gaussian_filter(g.z, 2.0)
    paths = []
    for level in range(20, int(z.max()) + 1, 20):
        for c in measure.find_contours(z, level):
            if len(c) < 12:
                continue
            x, y = g.xy(c[:, 1], c[:, 0])
            px, py = page.pt(x, y)
            p = carto.simplify(list(zip(px.tolist(), py.tolist())), 0.3)
            if len(p) > 2:
                w = 0.35 if level % 100 == 0 else 0.22
                paths.append(f'<path d="M{" L".join(f"{a:.1f},{b:.1f}" for a, b in p)}" fill="none" '
                             f'stroke="{CONTOUR}" stroke-width="{w}" stroke-opacity="0.8"/>')
    note = {"has_low": bool(low.any()), "terrain": "Copernicus DEM GLO-30 (doi:10.5270/ESA-c5d3d65), shaded from the north-west, contours "
                       "every 20 m; low ground under 6 m tinted"}
    return image, "".join(paths), note


def _network(ex: Extent, d: _Draw) -> tuple[list[str], list[list[tuple[float, float]]]]:
    """Rivers, roads and railways, quietest first. Returns the SVG and the drawn lines (soft label obstacles). A road
    or railway lying mostly over the open sea (a pier, a ferry, a breakwater the matching took for a road) isn't
    drawn."""
    out, lines = [], []
    g = terrain.dem(ex, res=15.0)
    wet = terrain.sea(g)

    def at_sea(c) -> bool:
        a = np.asarray(c, dtype=float)
        x, y = ex.to_crs.transform(a[:, 0], a[:, 1])
        col, row = g.colrow(x, y)
        ci = np.clip(np.rint(col).astype(int), 0, wet.shape[1] - 1)
        ri = np.clip(np.rint(row).astype(int), 0, wet.shape[0] - 1)
        return bool(wet[ri, ci].mean() > 0.5)
    for f in _load(ex, "water"):
        p = f["properties"]
        for c in _lines(f["geometry"]):
            path = d.path(c, 0.3)
            if path:
                w = 0.65 if p["kind"] == "river" else 0.35
                out.append(f'<path d="{path}" fill="none" stroke="{WATER}" stroke-width="{w}" stroke-linejoin="round"/>')
    roads = _load(ex, "roads")
    for minor in (True, False):
        for f in roads:
            p = f["properties"]
            if (p["road_class"] == "lesser") != minor or p.get("isolated"):
                continue
            for c in _lines(f["geometry"]):
                path = d.path(c)
                if not path or at_sea(c):
                    continue
                w, col = (0.55, ROAD_MINOR) if minor else (1.0, ROAD)
                out.append(f'<path d="{path}" fill="none" stroke="{col}" stroke-width="{w}" '
                           f'stroke-linecap="round" stroke-linejoin="round"/>')
                lines.append(d.pts(c))
    for f in _load(ex, "rails"):
        p = f["properties"]
        if p["on_sheet"] == "not seen":           # today's railway the sheet doesn't show: not drawn as 1944's
            continue
        op = "1" if p["on_sheet"] == "shown" else "0.5"
        for c in _lines(f["geometry"]):
            pts = carto.simplify(d.pts(c), 0.25)
            if len(pts) < 2 or at_sea(c):
                continue
            out.append(f'<path d="M{" L".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" fill="none" stroke="{RAIL}" '
                       f'stroke-width="0.7" stroke-opacity="{op}" stroke-linejoin="round"/>')
            t = _ticks(pts, 4.5, 1.4)
            if t:
                out.append(f'<path d="{t}" stroke="{RAIL}" stroke-width="0.5" stroke-opacity="{op}"/>')
            lines.append(pts)
    return out, lines


def _poly(d: "_Draw", geom: dict) -> str:
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    return " ".join(f"{d.path(ring, 0.4)} Z" for poly in polys for ring in poly if len(ring) > 3)


def _cathedral(x: float, y: float, colour: str = CATHEDRAL, k: float = 1.0) -> str:
    """A cathedral: a church's west front with its cross, standing on the point."""
    return (f'<path d="M{x - 3.2 * k:.1f},{y:.1f} V{y - 4 * k:.1f} L{x:.1f},{y - 6.4 * k:.1f} L{x + 3.2 * k:.1f},'
            f'{y - 4 * k:.1f} V{y:.1f} Z" fill="#ffffff" stroke="{colour}" stroke-width="0.8" stroke-linejoin="round"/>'
            f'<path d="M{x:.1f},{y - 6.4 * k:.1f} V{y - 10 * k:.1f} M{x - 1.3 * k:.1f},{y - 8.8 * k:.1f} '
            f'H{x + 1.3 * k:.1f}" stroke="{colour}" stroke-width="0.8"/>')


def reach_ring(cx: float, cy: float, r: float, colour: str, reach: dict, words: bool = True) -> str:
    """A unit's guns' reach as a ring of radius r (points): pale fill, a dashed edge where the gun is inferred, and
    its weapon and range written along the top of the ring."""
    dash = ' stroke-dasharray="3 2"' if reach.get("basis") != "reported" else ""
    out = (f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{colour}" fill-opacity="0.07" stroke="{colour}" '
           f'stroke-width="0.9" stroke-opacity="0.85"{dash}/>')
    if words and r > 30:
        yd = int(reach["range_yd"])
        miles = yd / 1760
        text = (f"{reach['weapon']}: reach {yd:,} yd, about {miles:.0f} miles"
                + (" (gun inferred)" if reach.get("basis") != "reported" else ""))
        pid = f"reach{int(cx)}{int(cy)}"
        out += (f'<defs><path id="{pid}" d="M{cx - r * 0.97:.1f},{cy:.1f} A{r * 0.97:.1f},{r * 0.97:.1f} 0 0 1 '
                f'{cx + r * 0.97:.1f},{cy:.1f}"/></defs>'
                f'<text font-family="{DISPLAY}" font-size="6.2" font-weight="bold" fill="{colour}" '
                f'stroke="#ffffff" stroke-width="2" stroke-linejoin="round" paint-order="stroke">'
                f'<textPath href="#{pid}" startOffset="50%" text-anchor="middle">{escape(text)}</textPath></text>')
    return out


def _burst(x: float, y: float, colour: str = OWN) -> str:
    """An aircraft engaged: a burst, eight short rays round a small open ring."""
    rays = " ".join(f"M{x + 2.2 * math.cos(a):.1f},{y + 2.2 * math.sin(a):.1f} "
                    f"L{x + 4.6 * math.cos(a):.1f},{y + 4.6 * math.sin(a):.1f}"
                    for a in (k * math.pi / 4 for k in range(8)))
    return (f'<path d="{rays}" stroke="{colour}" stroke-width="0.7" stroke-linecap="round"/>'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="1.3" fill="#ffffff" stroke="{colour}" stroke-width="0.7"/>')


def _network_words(manifest: dict) -> str:
    pm = manifest["sources"]["period_map"]
    eds = ", ".join(sorted({str(x["edition"]) for x in pm["sheets"]}))
    what = ("IGN's 1:50,000 (SCAN 50, 1950 series)" if pm["kind"] == "scan50" else
            f"the wartime {pm['kind'].upper().replace('GSGS', 'GSGS ')} sheets")
    return (f"roads and railways as {what} prints them, on OpenStreetMap's alignment where it follows the sheet; "
            f"editions {eds}")


def _north(ex: Extent, page: Page, x: float, y: float) -> str:
    """True north at the map's centre: Lambert-93's grid north is a few degrees off it here."""
    w, s, e, n = ex.bbox_lonlat
    lon, lat = (w + e) / 2, (s + n) / 2
    (x0, x1), (y0, y1) = ex.to_crs.transform([lon, lon], [lat, lat + 0.05])
    a = math.atan2(x1 - x0, y1 - y0)                      # clockwise from grid north
    dx, dy = math.sin(a), -math.cos(a)
    L = 14
    tip = (x + dx * L, y + dy * L)
    left = (x - dy * 3, y + dx * 3)
    right = (x + dy * 3, y - dx * 3)
    return (f'<path d="M{left[0]:.1f},{left[1]:.1f} L{tip[0]:.1f},{tip[1]:.1f} L{right[0]:.1f},{right[1]:.1f} Z" '
            f'fill="{INK}"/><text x="{tip[0] + dx * 5:.1f}" y="{tip[1] + dy * 5 + 2:.1f}" font-family="{DISPLAY}" '
            f'font-size="7" font-weight="bold" fill="{INK}" text-anchor="middle">N</text>')


def _scale(page: Page, x: float, y: float) -> str:
    km = 5
    L = km * 1000 / page.metres_per_pt()
    out = [f'<rect x="{x - 4:.1f}" y="{y - 12:.1f}" width="{L + 8:.1f}" height="17" fill="{PAPER}" fill-opacity="0.8"/>']
    for i in range(km):
        fill = INK if i % 2 == 0 else PAPER
        out.append(f'<rect x="{x + i * L / km:.1f}" y="{y - 2:.1f}" width="{L / km:.1f}" height="2.2" fill="{fill}" '
                   f'stroke="{INK}" stroke-width="0.4"/>')
    for i in (0, km):
        out.append(f'<text x="{x + i * L / km:.1f}" y="{y - 4:.1f}" font-family="{DISPLAY}" font-size="6" fill="{INK}" '
                   f'text-anchor="middle">{i}{" km" if i == km else ""}</text>')
    return "".join(out)


def _locator(ex: Extent, x: float, y: float, width: float) -> tuple[str, float]:
    """The extent in the campaign: land, the day's whole front, the box, a few towns."""
    box = tuple(ex.locator["bbox_lonlat"])
    lex = Extent(folder=ex.folder, name="locator", title="", crs=ex.crs, bbox_lonlat=box, date=ex.date,
                 fronts=[], units="", situation_map="")
    page = Page(lex.bounds, width)
    d = _Draw(lex, page, x, y)
    H = page.height
    out = [f'<defs><clipPath id="loc"><rect x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" height="{H:.1f}"/></clipPath></defs>',
           f'<rect x="{x - 0.5:.1f}" y="{y - 0.5:.1f}" width="{width + 1:.1f}" height="{H + 1:.1f}" fill="#ffffff"/>',
           f'<g clip-path="url(#loc)"><rect x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" height="{H:.1f}" fill="#dde7ea"/>']
    w, s, e, n = box
    clip = shapely.box(w - 0.3, s - 0.3, e + 0.3, n + 0.3)
    for ring in geo.land_rings((w - 1, s - 1, e + 1, n + 1)):
        part = shapely.make_valid(shapely.Polygon(ring)).intersection(clip)
        for poly in getattr(part, "geoms", [part]):
            if poly.is_empty or poly.geom_type != "Polygon":
                continue
            rings = [d.path(list(r.coords), 0.3) for r in (poly.exterior, *poly.interiors)]   # holes too: the sea
            path = " ".join(f"{r} Z" for r in rings if r)
            if path:
                out.append(f'<path d="{path}" fill="#f1f2ec" fill-rule="evenodd" stroke="#93aab3" stroke-width="0.4"/>')
    for line in figures._fronts(ex.fronts[-1]) if ex.fronts else []:
        path = d.path(line, 0.3)
        if path:
            out.append(f'<path d="{path}" fill="none" stroke="{FRONT}" stroke-width="0.9" stroke-linejoin="round"/>')
    (ax, ay), (bx, by) = d.pt(ex.bbox_lonlat[0], ex.bbox_lonlat[3]), d.pt(ex.bbox_lonlat[2], ex.bbox_lonlat[1])
    out.append(f'<rect x="{ax:.1f}" y="{ay:.1f}" width="{bx - ax:.1f}" height="{by - ay:.1f}" fill="none" '
               f'stroke="{INK}" stroke-width="1"/>')
    for name, lon, lat in ex.locator.get("places", []):
        px, py = d.pt(lon, lat)
        out.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="1.1" fill="{INK}"/>')
        out.append(f'<text x="{px + 2.2:.1f}" y="{py + 2:.1f}" font-family="{DISPLAY}" font-size="5.4" fill="{INK}" '
                   f'stroke="#f1f2ec" stroke-width="1.6" paint-order="stroke">{escape(name)}</text>')
    out.append("</g>")
    out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" height="{H:.1f}" fill="none" stroke="{INK}" '
               f'stroke-width="0.6"/>')
    return "".join(out), H


def _day(s: str) -> str:
    months = ["", "Jan", "Feb", "Mar", "Apr", "May", "June", "July", "Aug", "Sept", "Oct", "Nov", "Dec"]
    return f"{int(s[8:])} {months[int(s[5:7])]}"


def _legend(x: float, y: float, width: float, shown: list[dict], fronts: list[str], highlight: str | None,
            own: list[dict] | None = None, woods: bool = False, low: bool = True,
            raids: list[dict] | None = None, churches: list[dict] | None = None,
            highlight_arm: str = "") -> tuple[str, float]:
    """The network's signs and the fronts on one row; the divisions' symbols below it (symbols.legend)."""
    out, cx, cy = [], x, y

    def item(sign: str, words: str, w: float = 18):
        nonlocal cx, cy
        step = w + 8 + carto.Labels.width(words, 6.2)
        if cx + step > x + width and cx > x:          # a new row
            cx, cy = x, cy + 12
        out.append(sign.format(x=cx, y=cy, w=w))
        out.append(f'<text x="{cx + w + 3:.1f}" y="{cy + 2.2:.1f}" font-family="{DISPLAY}" font-size="6.2" '
                   f'fill="{INK}">{escape(words)}</text>')
        cx += step
    if fronts:
        item(f'<path d="M{{x}},{{y}} h{{w}}" stroke="{FRONT}" stroke-width="1.8"/>', f"front, {_day(fronts[-1])}")
    if len(fronts) > 1:
        item(f'<path d="M{{x}},{{y}} h{{w}}" stroke="{FRONT}" stroke-width="0.8" stroke-dasharray="3 1.6" '
             f'stroke-opacity="0.7"/>', f"front, {_day(fronts[0])}")
    item(f'<path d="M{{x}},{{y}} h{{w}}" stroke="{ROAD}" stroke-width="0.9"/>', "main road")
    item(f'<path d="M{{x}},{{y}} h{{w}}" stroke="{ROAD_MINOR}" stroke-width="0.45"/>', "lesser road")
    item(f'<path d="M{{x}},{{y}} h{{w}} M{{x}},{{y}} m2.2,-1.4 v2.8 m4.5,-2.8 v2.8 m4.5,-2.8 v2.8 m4.5,-2.8 v2.8" '
         f'stroke="{RAIL}" stroke-width="0.6"/>', "railway")
    item(f'<circle cx="{{x}}" cy="{{y}}" transform="translate(9,0)" r="1.7" fill="#ffffff" stroke="{WATER}" '
         f'stroke-width="0.7"/>', "river crossing", 18)
    if low:
        item(f'<rect x="{{x}}" y="{{y}}" transform="translate(0,-3.5)" width="{{w}}" height="7" fill="{LOW_CSS}" '
             f'stroke="{CONTOUR}" stroke-width="0.3"/>', "low ground, under 6 m")
    if woods:
        item(f'<rect x="{{x}}" y="{{y}}" transform="translate(0,-3.5)" width="{{w}}" height="7" fill="{WOOD}"/>',
             "woods, as the sheet prints them")
    seen: set[str] = set()
    for m in own or []:
        if m["kind"] != "station" or m["short"] in seen:
            continue
        seen.add(m["short"])
        short, c = m["short"], m["colour"]
        if m["symbol"]:
            item('<g transform="translate({x},{y})">' + symbols.symbol(9, 0, m["symbol"], colour=c, scale=0.8) +
                 "</g>", f"{short} on the map's date (else its longest stay here); dots, its other positions, dated",
                 26)
        else:
            item(f'<circle cx="{{x}}" cy="{{y}}" transform="translate(9,0)" r="2" fill="{c}" stroke="#ffffff" '
                 f'stroke-width="0.6"/>', f"{short}: its positions, dated")
        if any(x["kind"] == "action" and x["short"] == short for x in own or []):
            item('<g transform="translate({x},{y})">' + _burst(9, 0, c) + "</g>", "aircraft it engaged, dated")
    if raids:
        item('<g transform="translate({x},{y})">' + _burst(9, 0, RAID) + "</g>",
             "aircraft engaged by other units in the records, dated")
    if churches:
        item('<g transform="translate({x},{y})">' + _cathedral(9, 3) + "</g>", "Catholic cathedral")
    h = cy - y + 12
    if shown:
        strip, sh = symbols.legend(x, cy + 15, {u.get("of", "") for u in shown}, {u.get("arm", "") for u in shown},
                                   any(symbols.parse_label(u.get("label") or "")[1] for u in shown), highlight,
                                   max_width=width, highlight_arm=highlight_arm or "infantry")
        out.append(strip)
        h = cy - y + 15 + sh
    return "".join(out), h


def panorama(ex: Extent, width_in: float | None = None, highlight: str | None = None,
             highlight_words: str | None = None) -> tuple[str, dict]:
    """The panorama as SVG, and its notes: the sources and dates of each layer, and the divisions shown."""
    W = (width_in or float(ex.panorama.get("width_in", 9.6))) * 72
    highlight = highlight or ex.highlight or None
    highlight_words = highlight_words or ex.highlight_words or None
    page = Page(ex.bounds, W)
    H = page.height
    d = _Draw(ex, page)
    labels = carto.Labels((0, 0, W, H))
    image, contours, notes = _ground(ex, page)
    woods = "".join(f'<path d="{_poly(d, f["geometry"])}" fill="{WOOD}" fill-opacity="0.8" fill-rule="evenodd"/>'
                    for f in _load(ex, "woods")) if (ex.infrastructure / "woods.geojson").exists() else ""
    network, lines = _network(ex, d)

    crossings = "".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="1.7" fill="#ffffff" stroke="{WATER}" stroke-width="0.7"/>'
        for x, y in (d.pt(*f["geometry"]["coordinates"]) for f in _load(ex, "crossings")
                     if f["properties"].get("carries") == "rail" or f["properties"].get("road_class") == "main")
        if 0 < x < W and 0 < y < H)

    # the military layer: fronts (soft obstacles for labels) and divisions (hard)
    fronts = []
    for k, day in enumerate(ex.fronts):
        last = k == len(ex.fronts) - 1
        for line in figures._fronts(day):
            pts = d.pts(line)
            if not any(-20 < x < W + 20 and -20 < y < H + 20 for x, y in pts):
                continue
            labels.line(pts, pad=2)
            path = d.path(line, 0.3)
            style = ('stroke-width="1.8"' if last else
                     'stroke-width="0.8" stroke-dasharray="3 1.6" stroke-opacity="0.7"')
            fronts.append(f'<path d="{path}" fill="none" stroke="{FRONT}" {style} stroke-linejoin="round" '
                          f'stroke-linecap="round"/>')
    shown = ex.divisions(figures._units(ex.units))
    units = []
    for u in shown:
        ux, uy = d.pt(u["lon"], u["lat"])
        hl = bool(highlight) and u.get("unit") == highlight
        units.append(symbols.symbol(ux, uy, u, highlight=hl, scale=1.25))
        tw = carto.Labels.width(symbols.parse_label(u.get("label") or "")[0], 6.8 * 1.25)
        labels.occupy(ux - 9, uy - 12, 18 + 3 + tw, 18)
    # the unit's own record: its positions (with how precisely each is placed) and the aircraft it engaged
    # the Catholic cathedral, named, for an extent that asks for its churches (the rest are the inset's)
    cathedral_svg: list[str] = []
    cathedral_labels: list[str] = []
    churches = [f for f in _load(ex, "churches") if f["properties"].get("catholic")
                and f["properties"]["kind"] == "cathedral"] if ex.churches else []
    for f in churches:
        cx, cy = d.pt(*f["geometry"]["coordinates"])
        if not (0 < cx < W and 0 < cy < H):
            continue
        cathedral_svg.append(_cathedral(cx, cy))
        labels.occupy(cx - 4, cy - 11, 8, 11)
        cathedral_labels.append(labels.place(cx, cy - 4, [(f["properties"]["name"], 6.4, CATHEDRAL, "bold", DISPLAY)],
                                       force=True, gap=4))
    own, own_labels, own_marks = [], [], record.marks(ex)
    places = [f for f in _load(ex, "places") if f["properties"]["name"] not in ex.not_places]
    towns_of = {id(m): record.at_town(ex, m, places) for m in own_marks}
    forced = {t for t in towns_of.values() if t}     # towns a unit's position names: always labelled, once
    raids = record.raids(ex)
    for m in own_marks + raids:
        mx, my = d.pt(m["lon"], m["lat"])
        if m.get("current") and m.get("symbol") and m.get("placed") != "town":
            labels.occupy(mx - 12, my - 10, 34, 18)
        else:
            labels.occupy(mx - 4, my - 4, 8, 8)
    for m in own_marks:
        if m["kind"] == "station" and m.get("current") and m.get("reach"):
            mx, my = d.pt(m["lon"], m["lat"])
            r_reach = float(m["reach"]["range_yd"]) * 0.9144 / page.metres_per_pt()
            own.append(reach_ring(mx, my, r_reach, m["colour"], m["reach"]))
    for m in own_marks:
        mx, my = d.pt(m["lon"], m["lat"])
        c = m["colour"]
        if m["kind"] == "station":
            r = 1000 / page.metres_per_pt()
            if m["placed"] == "town":          # the town named: about a kilometre either way
                own.append(f'<circle cx="{mx:.1f}" cy="{my:.1f}" r="{r:.1f}" fill="none" stroke="{c}" '
                           f'stroke-width="0.45" stroke-dasharray="1 1.4" stroke-opacity="0.8"/>')
            elif m["placed"].startswith("grid"):   # a 1 km grid square
                own.append(f'<rect x="{mx - r / 2:.1f}" y="{my - r / 2:.1f}" width="{r:.1f}" height="{r:.1f}" '
                           f'fill="none" stroke="{c}" stroke-width="0.45" stroke-dasharray="1 1.4"/>')
            if m["current"] and m["symbol"] and m["placed"] == "town":
                # placed only by a town: the symbol stands clear of the town's landmarks, on a leader to its point
                for dx, dy in ((0, -24), (30, -16), (30, 16), (0, 26), (-30, 16), (-30, -16)):
                    if labels.free((mx + dx - 16, my + dy - 10, mx + dx + 22, my + dy + 8)):
                        break
                labels.occupy(mx + dx - 16, my + dy - 10, 38, 18)
                own.append(f'<line x1="{mx:.1f}" y1="{my:.1f}" x2="{mx + dx:.1f}" y2="{my + dy:.1f}" stroke="{c}" '
                           f'stroke-width="0.6"/>')
                own.append(symbols.symbol(mx + dx, my + dy, m["symbol"], colour=c, scale=1.1))
                own.append(f'<circle cx="{mx:.1f}" cy="{my:.1f}" r="2" fill="{c}" stroke="#ffffff" stroke-width="0.6"/>')
            elif m["current"] and m["symbol"]:   # where it was on the map's date: its own symbol, as the divisions'
                own.append(symbols.symbol(mx, my, m["symbol"], colour=c, scale=1.1))
            else:
                own.append(f'<circle cx="{mx:.1f}" cy="{my:.1f}" r="2" fill="{c}" stroke="#ffffff" stroke-width="0.6"/>')
            words = ([(record.span(m), 6.2, c, "bold", DISPLAY)] if towns_of[id(m)] else
                     [(record.name(m), 6.6, c, "bold", DISPLAY), (record.span(m), 6, c, "normal", DISPLAY)])
            own_labels.append(labels.place(mx, my, words, force=True,
                                           gap=9 if m["current"] and m["symbol"] and m["placed"] != "town" else 3.5))
        else:
            own.append(_burst(mx, my, c))
            own_labels.append(labels.place(mx, my, [(record.day(m["date"]), 6, c, "normal", DISPLAY)], gap=4))
    for m in raids:                            # the other side, as other units in the records saw it
        mx, my = d.pt(m["lon"], m["lat"])
        own.append(_burst(mx, my, RAID))
        own_labels.append(labels.place(mx, my, [(f"{record.day(m['date'])}, {m['time']}", 6, RAID, "bold", DISPLAY),
                                                (m["short"], 5.6, RAID, "normal", DISPLAY)], gap=4))
    # the corner pieces claim their room before the towns are named
    loc_w = 128
    loc_svg, loc_h = _locator(ex, 8, 8, loc_w)
    labels.occupy(0, 0, loc_w + 14, loc_h + 14)
    labels.occupy(0, H - 50, 96, 50)
    for pts in lines:
        labels.line(pts, pad=0.6)

    # towns: those at the network's main junctions first, then by population
    junction_names = {f["properties"]["name"]: f["properties"]["importance"] for f in _load(ex, "junctions")
                      if f["properties"]["name"]}
    def rank(f):
        p = f["properties"]
        pop = int(p.get("population") or 0) if str(p.get("population") or "0").isdigit() else 0
        return (p["name"] not in forced, p["name"] not in ex.towns and ex.label(p["name"])[0] not in ex.towns,
                -junction_names.get(p["name"], 0), -pop)
    town_svg = []
    for f in sorted(places, key=rank):
        p = f["properties"]
        if p["name"] in ex.not_places:
            continue
        px, py = d.pt(*f["geometry"]["coordinates"])
        if not (4 < px < W - 4 and 4 < py < H - 4):
            continue
        major = p["name"] in ex.towns or ex.label(p["name"])[0] in ex.towns
        size = 7.6 if major else 6.2
        name, today = ex.label(p["name"])
        lines = [(name, size, INK if major else MUTED, "bold" if major else "normal", DISPLAY)]
        if today:
            lines.append((f"today {today}", 5.4, MUTED, "normal", DISPLAY))
        svg = labels.place(px, py, lines, gap=2.5, force=p["name"] in forced)
        if svg:
            r = 1.8 if major else 1.1
            town_svg.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{r}" fill="{INK if major else MUTED}"/>' + svg)
            labels.occupy(px - r, py - r, 2 * r, 2 * r)
        if len(town_svg) >= 34:
            break

    # front dates at the line's west end
    front_labels = []
    for day in ex.fronts:
        for line in figures._fronts(day):
            pts = [(x, y) for x, y in d.pts(line) if 0 < x < W and 0 < y < H]
            if len(pts) < 2:
                continue
            x, y = min(pts)
            svg = labels.place(x, y, [(_day(day), 6.6, FRONT, "bold", DISPLAY)], gap=3)
            front_labels.append(svg)
            break

    body = [f'<defs><clipPath id="pano"><rect width="{W:.1f}" height="{H:.1f}"/></clipPath></defs>',
            '<g clip-path="url(#pano)">', image, woods, contours, *network, crossings, *fronts, *units, *own, *cathedral_svg, *town_svg,
            *front_labels, *own_labels, *cathedral_labels, "</g>",
            f'<rect width="{W:.1f}" height="{H:.1f}" fill="none" stroke="{INK}" stroke-width="0.7"/>',
            loc_svg, _north(ex, page, 18, H - 30), _scale(page, 34, H - 10)]
    legend, lh = _legend(4, H + 12, W - 8, shown, ex.fronts, highlight_words, own_marks, bool(woods),
                         notes.pop("has_low"), raids, churches,
                         next((u.get("arm", "") for u in shown if u.get("unit") == highlight), ""))
    body.append(legend)
    manifest = json.loads((ex.infrastructure / "manifest.json").read_text())
    notes |= {
        "network": _network_words(manifest),
        "water": "rivers: OpenStreetMap, today's courses",
        "fronts": [f"12ag-{day}" for day in ex.fronts],
        "units": [{"label": u.get("label"), "name": symbols.full_name(u), "cite": u.get("cite", "")} for u in shown],
        "record": [{k: m[k] for k in ("kind", "unit", "short", "place", "from", "to", "assumed_from", "date", "time",
                                      "result", "placed", "pages") if k in m} for m in own_marks + raids],
        "scale": f"1:{round(page.metres_per_pt() / 0.000352778 / 1000) * 1000:,}",
    }
    total = H + 12 + lh
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.1f}pt" height="{total:.1f}pt" '
           f'viewBox="0 0 {W:.1f} {total:.1f}">{"".join(body)}</svg>')
    return halo.split(svg), notes
