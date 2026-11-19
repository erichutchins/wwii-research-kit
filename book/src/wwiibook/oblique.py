"""An oblique view: the ground seen in perspective, for a chapter where the terrain is the story (the ridge the enemy
held, the marsh, the estuary). A picture to read beside the plan map, not a map to measure on: distances shrink with
depth, so it has no scale bar, and heights are exaggerated (the figure says by how much, and so should the caption).

The terrain is the AWS Terrain Tiles' elevation (as cartography's relief), shaded and tinted into a texture at the
tiles' full resolution, then rendered column by column: each column of the picture is a ray over the ground, stepped
from near to far, and a point on the ground shows where nothing nearer has already covered that row (the "voxel space"
method). Distant ground fades toward the sky. The record's marks go on top as vectors through the same camera: the
traced fronts, the stations, the division symbols raised on stalks over their positions.
"""
import base64
import io
import math
from datetime import date

import numpy as np
from PIL import Image

from . import cartography as carto
from . import halo, symbols

SKY = np.array([247, 246, 240], dtype=np.float32)
SEA = np.array([196, 212, 219], dtype=np.float32)
LOW = np.array([234, 236, 223], dtype=np.float32)
HIGH = np.array([200, 190, 156], dtype=np.float32)
OWN, INK, FRONT = "#a3241b", "#000000", "#2f3b31"
WATER = "#5f8fa6"     # a river draped on the ground: a shade deeper than the plan maps' so it reads over the relief
SERIF = "Libertinus Serif, Georgia, serif"


def _merc(lat):
    return np.log(np.tan(np.pi / 4 + np.radians(lat) / 2))


def terrain(box: tuple[float, float, float, float], z: int) -> tuple[np.ndarray, tuple[float, float, float, float]]:
    """Metres above sea level on the tiles' grid for the box (rows north to south, columns west to east, the rows
    evenly spaced in Mercator), and the exact box covered."""
    w, s, e, n = box
    x0, y0 = carto._txy(w, n, z)
    x1, y1 = carto._txy(e, s, z)
    tx0, ty0, tx1, ty1 = int(x0), int(y0), int(x1), int(y1)
    mosaic = Image.new("RGB", ((tx1 - tx0 + 1) * 256, (ty1 - ty0 + 1) * 256))
    for tx in range(tx0, tx1 + 1):
        for ty in range(ty0, ty1 + 1):
            mosaic.paste(carto._tile(z, tx, ty), ((tx - tx0) * 256, (ty - ty0) * 256))
    cx0, cy0, cx1, cy1 = int((x0 - tx0) * 256), int((y0 - ty0) * 256), int((x1 - tx0) * 256), int((y1 - ty0) * 256)
    a = np.asarray(mosaic.crop((cx0, cy0, cx1, cy1)), dtype=np.float32)
    elev = a[..., 0] * 256 + a[..., 1] + a[..., 2] / 256 - 32768
    exact = (*carto._lonlat(tx0 + cx0 / 256, ty0 + cy1 / 256, z), *carto._lonlat(tx0 + cx1 / 256, ty0 + cy0 / 256, z))
    return elev, exact


def texture(elev: np.ndarray, mpp: float, exaggeration: float) -> np.ndarray:
    """The ground's colour: a tint by height, lit from the north-west, sea where the ground is at or below sea level."""
    gy, gx = np.gradient(elev * exaggeration / 2, mpp)          # half the view's exaggeration reads true in light
    gy = -gy                                                     # rows run north to south
    lx, ly, lz = -0.6, 0.6, 0.55
    nl = math.sqrt(lx * lx + ly * ly + lz * lz)
    shade = (-gx * lx / nl - gy * ly / nl + lz / nl) / np.sqrt(gx * gx + gy * gy + 1)
    t = np.clip(elev / 140, 0, 1)[..., None]
    base = LOW * (1 - t) + HIGH * t
    lit = (0.6 + 0.58 * shade)[..., None]
    col = np.clip(base * lit, 0, 255)
    sea = (elev <= 0.5)[..., None]
    return np.where(sea, SEA, col).astype(np.float32)


def _bilinear(img: np.ndarray, r: np.ndarray, c: np.ndarray) -> np.ndarray:
    H, W = img.shape[:2]
    r = np.clip(r, 0, H - 1.001)
    c = np.clip(c, 0, W - 1.001)
    r0, c0 = r.astype(np.int32), c.astype(np.int32)
    tr, tc = r - r0, c - c0
    if img.ndim == 3:
        tr, tc = tr[..., None], tc[..., None]
    a, b = img[r0, c0], img[r0, c0 + 1]
    d, e = img[r0 + 1, c0], img[r0 + 1, c0 + 1]
    return (a * (1 - tc) + b * tc) * (1 - tr) + (d * (1 - tc) + e * tc) * tr


class Camera:
    """A camera over a box, looking along `azimuth` (degrees from north) and down at `tilt` degrees to the box's
    centre, `back` box-depths behind its near edge. Kilometres from the box's centre; heights times `exaggeration`.
    The picture plane is vertical, and the horizon is shifted to look down (the voxel-space camera), so verticals stay
    vertical: the division stalks stand straight."""

    def __init__(self, box, azimuth: float, tilt: float, exaggeration: float, width_px: float, back: float = 0.9):
        w, s, e, n = box
        self.lon_c, self.lat_c = (w + e) / 2, (s + n) / 2
        self.kx, self.ky = 111.32 * math.cos(math.radians(self.lat_c)), 110.57
        self.ex = exaggeration
        a = math.radians(azimuth)
        self.fwd = (math.sin(a), math.cos(a))
        self.right = (math.cos(a), -math.sin(a))
        corners = [((x - self.lon_c) * self.kx, (y - self.lat_c) * self.ky) for x in (w, e) for y in (s, n)]
        along = [cx * self.fwd[0] + cy * self.fwd[1] for cx, cy in corners]
        across = [cx * self.right[0] + cy * self.right[1] for cx, cy in corners]
        depth = max(along) - min(along)
        half = (max(across) - min(across)) / 2
        dist = -min(along) + back * depth                      # from the camera to the box's centre, along the view
        self.c = (-self.fwd[0] * dist, -self.fwd[1] * dist)
        self.h = dist * math.tan(math.radians(tilt))
        self.z_near = dist + min(along)
        self.z_far = dist + max(along)
        self.f = (width_px / 2) * dist / half                  # the box's middle depth fills the width
        self.width_px = width_px

    def world(self, lon, lat):
        return (lon - self.lon_c) * self.kx, (lat - self.lat_c) * self.ky

    def screen(self, lon, lat, metres, y_h):
        """Picture coordinates (pixels) of a point on the ground, and its depth."""
        x, y = self.world(lon, lat)
        dx, dy = x - self.c[0], y - self.c[1]
        z = dx * self.fwd[0] + dy * self.fwd[1]
        lat_ = dx * self.right[0] + dy * self.right[1]
        u = self.width_px / 2 + self.f * lat_ / z
        v = y_h + self.f * (self.h - max(metres, 0) / 1000 * self.ex) / z
        return u, v, z


def view(box: list[float], width_in: float, height_in: float | None, *, azimuth: float = 180, tilt: float = 30,
         exaggeration: float = 4, zoom: int = 12, fronts: tuple = (), units: str | None = None,
         highlight: str | None = None, route: dict | None = None, window: list[str] | None = None,
         labels: tuple = (), places: tuple = (), rivers: int = 0, legs: str = "full") -> tuple[str, dict]:
    from .figures import _fronts, _units
    elev, (ew, es, ee, en) = terrain((box[0], box[1], box[2], box[3]), zoom)
    rows, cols = elev.shape
    mpp = 40075016.686 * math.cos(math.radians((es + en) / 2)) / (256 * 2 ** zoom)
    tex = texture(elev, mpp, exaggeration)
    m_n, m_s = float(_merc(en)), float(_merc(es))
    S = 2 * 300 / 72                                          # pixels per point: drawn at 600 dpi, printed at 300
    W = width_in * 72
    Wpx = int(W * S)
    cam = Camera((ew, es, ee, en), azimuth, tilt, exaggeration, Wpx)
    top = 34 * S                                              # room above the far edge for the division stalks
    y_h = top - cam.f * cam.h / cam.z_far                     # the far edge's ground at `top`
    Hpx = int(height_in * 72 * S) if height_in else int(y_h + cam.f * cam.h / cam.z_near + 4 * S)
    H = Hpx / S

    # rays: geometric depth steps, fine enough that the near ground never jumps more than a pixel
    steps = int(math.log(cam.z_far / cam.z_near * 1.07) * (cam.f * cam.h / cam.z_near)) + 50
    zs = (cam.z_near * 0.97 * (cam.z_far * 1.03 / (cam.z_near * 0.97)) ** (np.arange(steps) / (steps - 1))).astype(np.float32)
    img = np.empty((Hpx, Wpx, 3), dtype=np.float32)
    img[:] = SKY
    rows_px = np.arange(Hpx, dtype=np.float32)
    haze = (np.clip((zs - cam.z_near) / (cam.z_far - cam.z_near), 0, 1) * 0.42)[:, None, None]
    chunk = 160
    for c0 in range(0, Wpx, chunk):
        cu = np.arange(c0, min(c0 + chunk, Wpx), dtype=np.float32)
        t = (cu - Wpx / 2) / cam.f                            # lateral per unit depth
        X = cam.c[0] + zs[:, None] * (cam.fwd[0] + t[None, :] * cam.right[0])
        Y = cam.c[1] + zs[:, None] * (cam.fwd[1] + t[None, :] * cam.right[1])
        lon = cam.lon_c + X / cam.kx
        lat = cam.lat_c + Y / cam.ky
        ml, mt = 2 * (ee - ew) / cols, 2 * (en - es) / rows      # two texels in from the grid's edge: no edge smear
        inside = (lon >= ew + ml) & (lon <= ee - ml) & (lat >= es + mt) & (lat <= en - mt)
        cc = (lon - ew) / (ee - ew) * (cols - 1)
        rr = (m_n - _merc(np.clip(lat, es, en))) / (m_n - m_s) * (rows - 1)
        h = np.maximum(_bilinear(elev, rr, cc), 0)
        col = _bilinear(tex, rr, cc) * (1 - haze) + SKY * haze
        yv = y_h + cam.f * (cam.h - h / 1000 * cam.ex) / zs[:, None]
        yv = np.where(inside, yv, np.inf)
        mins = np.minimum.accumulate(yv, axis=0)            # the y-buffer, near to far
        lowest = np.where(np.isfinite(yv), yv, -np.inf).max(axis=0)     # the near edge's ground, per column
        for k in range(len(cu)):
            owner = np.searchsorted(-mins[:, k], -rows_px, side="left")   # the nearest step covering each row
            seen = (owner < steps) & (rows_px <= lowest[k] + 1)            # nothing below the near edge
            img[seen, int(cu[k])] = col[owner[seen], k]
    pic = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).resize((int(W * 300 / 72), int(H * 300 / 72)),
                                                                          Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    pic.save(buf, "PNG", optimize=True)
    body = [f'<image x="0" y="0" width="{W:.1f}" height="{H:.1f}" preserveAspectRatio="none" '
            f'href="data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"/>']

    def height(lon: float, lat: float) -> float:
        cc = (lon - ew) / (ee - ew) * (cols - 1)
        rr = (m_n - float(_merc(lat))) / (m_n - m_s) * (rows - 1)
        return float(_bilinear(elev, np.array([rr]), np.array([cc]))[0])

    def at(lon: float, lat: float, lift: float = 20) -> tuple[float, float]:
        u, v, _ = cam.screen(lon, lat, height(lon, lat) + lift, y_h)
        return u / S, v / S

    def inside(lon, lat):
        return ew <= lon <= ee and es <= lat <= en

    placer = carto.Labels((0, 0, W, H))
    # rivers (Natural Earth 1:10m, as the plan maps draw them; `rivers` the largest scalerank drawn, 0 for none),
    # draped on the ground: each line densified so it follows the terrain rather than cutting through it
    if rivers:
        for name in ("ne_10m_rivers_lake_centerlines", "ne_10m_rivers_europe", "ne_10m_rivers_north_america"):
            try:
                gj = carto.natural(name)
            except Exception:  # noqa: BLE001 - a missing layer is a missing layer, not a broken figure
                continue
            for feat in gj["features"]:
                rank = feat["properties"].get("scalerank", 99)
                if rank > rivers or not feat["geometry"]:
                    continue
                for line in carto._lines(feat["geometry"]):
                    pts = []
                    for (lo1, la1), (lo2, la2) in zip(line, line[1:]):
                        n = max(1, int(math.hypot(lo2 - lo1, la2 - la1) / 0.002))
                        pts += [(lo1 + (lo2 - lo1) * k / n, la1 + (la2 - la1) * k / n) for k in range(n)]
                    if line:
                        pts.append(tuple(line[-1]))
                    run: list[tuple[float, float]] = []
                    for lo, la in pts + [(None, None)]:
                        if lo is not None and inside(lo, la):
                            run.append(at(lo, la, 2))
                            continue
                        if len(run) > 1:
                            d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in run)
                            body.append(f'<path d="{d}" fill="none" stroke="{WATER}" stroke-width="1.6" '
                                        f'stroke-linejoin="round" stroke-linecap="round"/>')
                        run = []
    for kf, day in enumerate(fronts):
        last = kf == len(fronts) - 1
        for line in _fronts(day):
            seg = [at(lo, la) for lo, la in line if inside(lo, la)]
            if len(seg) > 1:
                placer.line(seg)
                d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in seg)
                body.append(f'<path d="{d}" fill="none" stroke="#ffffff" stroke-width="{3.2 if last else 1.6}" '
                            f'stroke-opacity="0.7" stroke-linejoin="round"/>')
                body.append(f'<path d="{d}" fill="none" stroke="{FRONT}" stroke-width="{1.7 if last else 0.8}" '
                            f'stroke-opacity="{1 if last else 0.6}" stroke-linejoin="round" stroke-linecap="round"/>')
    # marks first, then labels where they fit: stations (always), then towns (if room)
    stops = []
    if route:
        stops = [s for s in route["stops"] if inside(s["lon"], s["lat"]) and
                 (not window or ((s["from"] or "") <= window[1] and (s["to"] or "9") >= window[0]))]
    sp = [at(s["lon"], s["lat"]) for s in stops]
    for x, y in sp:
        placer.occupy(x - 3, y - 3, 6, 6)
    shown = []
    unit_svg = []
    if units:
        for un in _units(units):
            if not inside(un["lon"], un["lat"]) or not (un.get("echelon") == "xx" or (not un.get("echelon") and un.get("arm"))):
                continue
            gx, gy = at(un["lon"], un["lat"], 0)
            hl = bool(highlight) and un.get("unit") == highlight
            number = symbols.parse_label(str(un.get("label") or ""))[0]
            nw = carto.Labels.width(number, 6.8)
            # the stalk grows until the box and its number are clear of every box and mark placed before
            for stalk in (16, 24, 32, 40, 50, 16):
                cy = gy - stalk - 5
                rect = (gx - 7.5, cy - 10, 15 + 2 + nw, 16)
                if placer.free((rect[0], rect[1], rect[0] + rect[2], rect[1] + rect[3])):
                    break
            placer.occupy(*rect)
            placer.line([(gx, gy), (gx, gy - stalk)])
            unit_svg.append(f'<line x1="{gx:.1f}" y1="{gy:.1f}" x2="{gx:.1f}" y2="{gy - stalk:.1f}" stroke="{OWN if hl else INK}" '
                            f'stroke-width="0.6"/><circle cx="{gx:.1f}" cy="{gy:.1f}" r="1" fill="{OWN if hl else INK}"/>')
            unit_svg.append(symbols.symbol(gx, cy, un, highlight=hl))
            shown.append({**un, "highlight": hl})
    # legs: "none" draws the stations alone (no line joins a unit's dated positions where the way isn't recorded)
    for (a, pa), (b, pb) in ([] if legs == "none" else zip(zip(stops, sp), list(zip(stops, sp))[1:])):
        placer.line([pa, pb])
        gap = a.get("to") and b.get("from") and (date.fromisoformat(b["from"]) - date.fromisoformat(a["to"])).days > 1
        dash = ' stroke-dasharray="3 2.2"' if gap or a["assumed"] or b["assumed"] else ""
        body.append(f'<line x1="{pa[0]:.1f}" y1="{pa[1]:.1f}" x2="{pb[0]:.1f}" y2="{pb[1]:.1f}" stroke="{OWN}" '
                    f'stroke-width="1.3" stroke-linecap="round"{dash}/>')
    for x, y in sp:
        body.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.1" fill="{OWN}" stroke="#ffffff" stroke-width="0.6"/>')
    labels_svg = []
    for s, (x, y) in zip(stops, sp):
        if any(s["name"].startswith(lb) for lb in labels):
            labels_svg.append(placer.place(x, y, [(s["name"].split(" (")[0], 7.2, INK, "bold", carto.DISPLAY)], force=True))
    for name, lon, lat in places:
        if inside(lon, lat):
            x, y = at(lon, lat)
            lab = placer.place(x, y, [(name, 6.6, INK, "normal", SERIF)])
            if lab:
                labels_svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="1.3" fill="#ffffff" stroke="{INK}" stroke-width="0.6"/>' + lab)
    body += unit_svg + labels_svg
    compass = {0: "north", 45: "north-east", 90: "east", 135: "south-east", 180: "south", 225: "south-west",
               270: "west", 315: "north-west"}.get(int(azimuth) % 360, f"{azimuth:.0f}°")
    body.append(f'<text x="6" y="{H - 6:.1f}" font-family="{carto.DISPLAY}" font-size="7" letter-spacing="1.2" '
                f'fill="#4a5249" stroke="#ffffff" stroke-width="2" paint-order="stroke">LOOKING {compass.upper()} · '
                f'HEIGHTS × {exaggeration:g} · NOT TO SCALE</text>')
    notes = {"units": [{"number": symbols.parse_label(str(u.get("label") or ""))[0], "name": symbols.full_name(u),
                        "side": symbols.SIDE_WORDS.get(u.get("of", ""), ""), "highlight": u["highlight"]}
                       for u in sorted(shown, key=lambda u: (u.get("of") == "de", not u["highlight"], u.get("label") or ""))],
             "exaggeration": exaggeration, "azimuth": azimuth}
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.1f}pt" height="{H:.1f}pt" viewBox="0 0 {W:.1f} {H:.1f}">'
           + "".join(body) + "</svg>")
    return halo.split(svg), notes
