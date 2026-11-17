"""The oblique view: the panorama's extent seen from a low camera, the ground's shape made legible.

A cartographic picture, not a photograph: the ground is tinted by height and lit, with 20 m contours, the low marsh
ground in its own tint, and the period network (reconstruct.py) drawn onto it, so roads and railways climb and drop
with the land and a ridge hides what lies behind it. The extent is the panorama's, in the same CRS; a margin of
context round it is drawn paler, so the extent's edge doesn't read as a cliff. The front and the divisions go on top
as vectors through the same camera, hidden where the ground covers them (a depth buffer from the render); divisions
stand on stalks over their positions, as the army group's map placed them.

The render is the voxel-space method: each column of the picture a ray over the ground, stepped from near to far,
each step showing where nothing nearer covers it. Heights are exaggerated (the figure says by how much), and depth
shortens distances, so it carries no scale bar.
"""
import base64
import io
import json
import math

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
from skimage import measure

from .. import cartography as carto
from .. import figures, halo, symbols
from . import record, terrain
from .extent import Extent
from .panorama import CATHEDRAL, RAID, _burst, _cathedral

SKY_TOP, SKY = np.array([226, 232, 233], np.float32), np.array([246, 245, 239], np.float32)
SEA = np.array([203, 216, 222], np.float32)
LOWLAND, UPLAND = np.array([238, 237, 226], np.float32), np.array([212, 199, 163], np.float32)
MARSH = np.array([214, 226, 212], np.float32)
WOOD = np.array([176, 196, 158], np.float32)
CONTOUR = np.array([168, 150, 116], np.float32)
WATER = np.array([110, 148, 165], np.float32)
ROAD, ROAD_MINOR = np.array([96, 80, 62], np.float32), np.array([132, 116, 94], np.float32)
RAIL = np.array([52, 48, 42], np.float32)
INK, FRONT, OWN = "#1c221d", "#a3241b", "#a3241b"
DISPLAY, SERIF = carto.DISPLAY, carto.SERIF


class Camera:
    """A camera over the projected extent looking along `azimuth` (degrees clockwise from grid north), down at `tilt`
    degrees to the extent's centre, set back `back` extent-depths behind the near edge. Kilometres from the centre;
    heights times `exaggeration`. A vertical picture plane with its horizon shifted (the voxel-space camera), so the
    division stalks stand straight."""

    def __init__(self, bounds, azimuth: float, tilt: float, exaggeration: float, width_px: float, back: float = 0.9):
        x0, y0, x1, y1 = bounds
        self.xc, self.yc = (x0 + x1) / 2, (y0 + y1) / 2
        self.ex = exaggeration
        a = math.radians(azimuth)
        self.fwd = (math.sin(a), math.cos(a))
        self.right = (math.cos(a), -math.sin(a))
        corners = [((x - self.xc) / 1000, (y - self.yc) / 1000) for x in (x0, x1) for y in (y0, y1)]
        along = [cx * self.fwd[0] + cy * self.fwd[1] for cx, cy in corners]
        across = [cx * self.right[0] + cy * self.right[1] for cx, cy in corners]
        depth = max(along) - min(along)
        half = (max(across) - min(across)) / 2
        dist = -min(along) + back * depth
        self.c = (-self.fwd[0] * dist, -self.fwd[1] * dist)
        self.h = dist * math.tan(math.radians(tilt))
        self.z_near, self.z_far = dist + min(along), dist + max(along)
        self.f = (width_px / 2) * dist / half
        self.width_px = width_px

    def screen(self, x, y, metres, y_h):
        """Picture coordinates (pixels) of projected points at a height, and their depth (km)."""
        dx = (np.asarray(x) - self.xc) / 1000 - self.c[0]
        dy = (np.asarray(y) - self.yc) / 1000 - self.c[1]
        z = dx * self.fwd[0] + dy * self.fwd[1]
        lat = dx * self.right[0] + dy * self.right[1]
        return (self.width_px / 2 + self.f * lat / z,
                y_h + self.f * (self.h - np.maximum(metres, 0) / 1000 * self.ex) / z, z)


def _load(ex: Extent, layer: str) -> list[dict]:
    return json.loads((ex.infrastructure / f"{layer}.geojson").read_text())["features"]


def _lines(geom: dict):
    return [geom["coordinates"]] if geom["type"] == "LineString" else list(geom["coordinates"])


def _texture(ex: Extent, g: terrain.Grid, exaggeration: float, inside: np.ndarray) -> np.ndarray:
    """The ground's colour on the grid: tint by height, light, contours, marsh, sea, water, then the network."""
    shade = terrain.hillshade(g, azimuth=315, altitude=40, exaggeration=exaggeration / 2)
    flat = math.sin(math.radians(40))
    t = np.clip(g.z / 130, 0, 1)[..., None] ** 0.8
    col = LOWLAND * (1 - t) + UPLAND * t
    col = col * (1 + np.clip((shade - flat) * 1.1, -0.5, 0.22))[..., None]
    col = np.where(terrain.low_ground(g)[..., None], MARSH * (1 + np.clip((shade - flat) * 0.5, -0.2, 0.1))[..., None], col)
    col = np.where(terrain.sea(g)[..., None], SEA, col)
    H, W = g.shape
    to = ex.to_crs

    def draw(features, width, kind_filter=None, dotted=False):
        mask = Image.new("L", (W, H), 0)
        dr = ImageDraw.Draw(mask)
        for f in features:
            if kind_filter and not kind_filter(f["properties"]):
                continue
            for c in _lines(f["geometry"]):
                a = np.asarray(c, dtype=float)
                x, y = to.transform(a[:, 0], a[:, 1])
                cc, rr = g.colrow(x, y)
                pts = list(zip((cc + 0.5).tolist(), (rr + 0.5).tolist()))
                if len(pts) > 1:
                    dr.line(pts, fill=255, width=width, joint="curve")
        m = np.asarray(mask, dtype=np.float32) / 255
        return ndimage.gaussian_filter(m, 0.5)

    def paint(m, colour, alpha=1.0):
        nonlocal col
        a = (m * alpha)[..., None]
        col = col * (1 - a) + colour * a

    # the woods, as the sheet prints them
    if (ex.infrastructure / "woods.geojson").exists():
        wm = Image.new("L", (W, H), 0)
        wd = ImageDraw.Draw(wm)
        for f in _load(ex, "woods"):
            polys = f["geometry"]["coordinates"] if f["geometry"]["type"] == "MultiPolygon" else [f["geometry"]["coordinates"]]
            for poly in polys:
                for k, ring in enumerate(poly):
                    a = np.asarray(ring, dtype=float)
                    x, y = to.transform(a[:, 0], a[:, 1])
                    cc, rr = g.colrow(x, y)
                    wd.polygon(list(zip((cc + 0.5).tolist(), (rr + 0.5).tolist())), fill=0 if k else 255)
        paint(ndimage.gaussian_filter(np.asarray(wm, dtype=np.float32) / 255, 0.8), WOOD, 0.55)
    # contours every 20 m, from a smoothed model
    z = ndimage.gaussian_filter(g.z, 1.5)
    cm = Image.new("L", (W, H), 0)
    dr = ImageDraw.Draw(cm)
    for level in range(20, int(z.max()) + 1, 20):
        for c in measure.find_contours(z, level):
            if len(c) > 10:
                dr.line(list(zip((c[:, 1] + 0.5).tolist(), (c[:, 0] + 0.5).tolist())), fill=255, width=1)
    paint(np.asarray(cm, dtype=np.float32) / 255, CONTOUR, 0.45)
    water = _load(ex, "water")
    paint(draw(water, 1, lambda p: p["kind"] == "stream"), WATER, 0.7)
    paint(draw(water, 2, lambda p: p["kind"] == "river"), WATER, 0.95)
    roads = [f for f in _load(ex, "roads") if not f["properties"].get("isolated")]
    paint(draw(roads, 2, lambda p: p["road_class"] == "lesser"), ROAD_MINOR, 0.85)
    paint(draw(roads, 3, lambda p: p["road_class"] == "main"), ROAD, 0.95)
    rails = [f for f in _load(ex, "rails") if f["properties"]["on_sheet"] != "not seen"]
    paint(draw(rails, 2), RAIL, 0.95)
    col = np.where(terrain.sea(g)[..., None], SEA, col)       # nothing drawn over the open sea (a pier, a ferry)
    # the context margin outside the extent: paler, so the extent stands out without a hard edge
    fade = ndimage.gaussian_filter((~inside).astype(np.float32), 6)[..., None] * 0.55
    return (col * (1 - fade) + SKY * fade).astype(np.float32)


def _hills(ex: Extent, most: int = 7, apart: float = 6000) -> list[dict]:
    """The named hills worth a label: the highest first, none within `apart` metres of one already chosen."""
    w, s, e, n = ex.bbox_lonlat
    def ele(f):
        try:
            return float(str(f["properties"].get("ele") or "").replace(",", "."))
        except ValueError:
            return -1.0
    out, at = [], []
    for f in sorted(_load(ex, "hills"), key=ele, reverse=True):
        lon, lat = f["geometry"]["coordinates"]
        if not (w <= lon <= e and s <= lat <= n):
            continue
        x, y = ex.to_crs.transform(lon, lat)
        if any(math.hypot(x - a, y - b) < apart for a, b in at):
            continue
        out.append(f)
        at.append((x, y))
        if len(out) >= most:
            break
    return out


def _rose(ex: Extent, g, cam: "Camera", y_h: float, S: float, W: float, H: float, at, placer) -> tuple[str, tuple | None]:
    """A compass rose lying on the ground, drawn through the view's own camera: its ring an ellipse, its needle
    foreshortened toward true north, so the picture shows which way it looks without a word. Set on visible ground
    near a lower corner, clear of what is already placed, about 50 points across."""
    w, s, e, n = ex.bbox_lonlat
    lon, lat = np.meshgrid(np.linspace(w, e, 40)[1:-1], np.linspace(s, n, 40)[1:-1])
    u, v, seen = at(lon.ravel(), lat.ravel())
    for tx, ty in ((0.09, 0.80), (0.91, 0.80), (0.09, 0.62), (0.91, 0.62)):
        d = np.hypot(u - tx * W, v - ty * H) + np.where(seen, 0, 1e9)
        k = int(np.argmin(d))
        if d[k] > 0.12 * W:
            continue
        cu, cv = float(u[k]), float(v[k])
        if placer.free((cu - 30, cv - 40, cu + 30, cv + 22)):
            break
    else:
        return "", None
    x0, y0 = ex.to_crs.transform(float(lon.ravel()[k]), float(lat.ravel()[k]))
    (xn, yn) = ex.to_crs.transform(float(lon.ravel()[k]), float(lat.ravel()[k]) + 0.01)
    nx, ny = (xn - x0), (yn - y0)
    norm = math.hypot(nx, ny)
    nx, ny = nx / norm, ny / norm                      # true north, in the extent's grid
    ex_, ey_ = ny, -nx                                 # east
    h = float(g.at(x0, y0)[0]) + 30

    def page(px, py):
        a, b, _ = cam.screen(np.asarray(px, dtype=float), np.asarray(py, dtype=float), np.full(np.shape(px), h), y_h)
        return a / S, b / S
    # the radius that makes the rose about 50 points across where it stands
    a, _ = page([x0 - 500 * ex_, x0 + 500 * ex_], [y0 - 500 * ey_, y0 + 500 * ey_])
    a2, b2 = page([x0 - 500 * nx, x0 + 500 * nx], [y0 - 500 * ny, y0 + 500 * ny])
    span = max(abs(a[1] - a[0]), math.hypot(a2[1] - a2[0], b2[1] - b2[0]), 1e-6)
    R = 500 * 50 / span
    t = np.linspace(0, 2 * math.pi, 73)
    ru, rv = page(x0 + R * np.cos(t), y0 + R * np.sin(t))
    ring = "M" + " L".join(f"{p:.1f},{q:.1f}" for p, q in zip(ru, rv)) + " Z"

    def pt(f_n, f_e):                                  # a point R * (f_n north, f_e east) from the centre
        pu, pv = page([x0 + R * (f_n * nx + f_e * ex_)], [y0 + R * (f_n * ny + f_e * ey_)])
        return float(pu[0]), float(pv[0])
    tip, left, right, tail = pt(1.15, 0), pt(0, -0.2), pt(0, 0.2), pt(-0.7, 0)
    cu, cv = pt(0, 0)
    out = [f'<path d="{ring}" fill="#ffffff" fill-opacity="0.55" stroke="{INK}" stroke-width="0.6"/>',
           f'<path d="M{tip[0]:.1f},{tip[1]:.1f} L{left[0]:.1f},{left[1]:.1f} L{cu:.1f},{cv:.1f} Z" fill="{INK}"/>',
           f'<path d="M{tip[0]:.1f},{tip[1]:.1f} L{right[0]:.1f},{right[1]:.1f} L{cu:.1f},{cv:.1f} Z" fill="#59605a"/>',
           f'<path d="M{tail[0]:.1f},{tail[1]:.1f} L{left[0]:.1f},{left[1]:.1f} L{right[0]:.1f},{right[1]:.1f} Z" '
           f'fill="#ffffff" stroke="{INK}" stroke-width="0.5"/>']
    for word, (f_n, f_e), size, weight in (("N", (1.45, 0), 9, "bold"), ("E", (0, 1.3), 6, "normal"),
                                           ("S", (-1.3, 0), 6, "normal"), ("W", (0, -1.3), 6, "normal")):
        lu, lv = pt(f_n, f_e)
        out.append(f'<text x="{lu:.1f}" y="{lv + size * 0.35:.1f}" font-family="{DISPLAY}" font-size="{size}" '
                   f'font-weight="{weight}" fill="{INK}" text-anchor="middle" stroke="#ffffff" stroke-width="2" '
                   f'paint-order="stroke">{word}</text>')
    xs = list(ru) + [pt(1.45, 0)[0]]
    ys = list(rv) + [pt(1.45, 0)[1] - 8]
    return "".join(out), (min(xs) - 4, min(ys) - 4, max(xs) - min(xs) + 8, max(ys) - min(ys) + 8)


def oblique(ex: Extent, width_in: float | None = None, *, azimuth: float | None = None, tilt: float | None = None,
            exaggeration: float | None = None, highlight: str | None = None, res: float = 10.0,
            context: float = 3000.0) -> tuple[str, dict]:
    """The oblique view as SVG (an image of the ground, the record's marks over it as vectors), and its notes."""
    o = ex.oblique
    azimuth = float(azimuth if azimuth is not None else o.get("azimuth", 90))
    tilt = float(tilt if tilt is not None else o.get("tilt", 15))
    exaggeration = float(exaggeration if exaggeration is not None else o.get("exaggeration", 5))
    W = (width_in or float(o.get("width_in", 9.6))) * 72
    highlight = highlight or ex.highlight or None
    g = terrain.dem(ex, res=res, pad=context)
    bx0, by0, bx1, by1 = ex.bounds
    gx, gy = g.xy(np.arange(g.shape[1]), np.arange(g.shape[0]))
    inside = (gx[None, :] >= bx0) & (gx[None, :] <= bx1) & (gy[:, None] >= by0) & (gy[:, None] <= by1)
    tex = _texture(ex, g, exaggeration, inside)
    elev = g.z.astype(np.float32)
    wet = terrain.sea(g).astype(np.float32)

    S = 2 * 300 / 72                                        # drawn at 600 dpi, printed at 300
    Wpx = int(W * S)
    cam = Camera(ex.bounds, azimuth, tilt, exaggeration, Wpx)
    # the context margin's far edge: the farthest depth worth stepping to
    gb = (g.x0, g.y1 - g.shape[0] * res, g.x0 + g.shape[1] * res, g.y1)
    corners = [cam.screen(x, y, 0, 0)[2] for x in (gb[0], gb[2]) for y in (gb[1], gb[3])]
    z_far = float(max(corners))
    top = 40 * S
    y_h = top - cam.f * cam.h / z_far
    Hpx = int(y_h + cam.f * cam.h / cam.z_near + 4 * S)
    H = Hpx / S

    steps = int(math.log(z_far / cam.z_near * 1.07) * (cam.f * cam.h / cam.z_near)) + 50
    zs = (cam.z_near * 0.97 * (z_far * 1.03 / (cam.z_near * 0.97)) ** (np.arange(steps) / (steps - 1))).astype(np.float32)
    sky_t = np.clip(np.arange(Hpx, dtype=np.float32) / max(y_h + 20 * S, 1), 0, 1)[:, None]
    img = np.empty((Hpx, Wpx, 3), dtype=np.float32)
    img[:] = (SKY_TOP * (1 - sky_t) + SKY * sky_t)[:, None, :]
    depth = np.full((Hpx, Wpx), np.inf, dtype=np.float32)
    land = np.zeros((Hpx, Wpx), dtype=bool)
    rows_px = np.arange(Hpx, dtype=np.float32)
    haze = (np.clip((zs - cam.z_near) / (z_far - cam.z_near), 0, 1) ** 1.3 * 0.38)[:, None, None]
    rows, cols = elev.shape
    for c0 in range(0, Wpx, 160):
        cu = np.arange(c0, min(c0 + 160, Wpx), dtype=np.float32)
        t = (cu - Wpx / 2) / cam.f
        X = (cam.c[0] + zs[:, None] * (cam.fwd[0] + t[None, :] * cam.right[0])) * 1000 + cam.xc
        Y = (cam.c[1] + zs[:, None] * (cam.fwd[1] + t[None, :] * cam.right[1])) * 1000 + cam.yc
        cc, rr = g.colrow(X, Y)
        ok = (cc >= 2) & (cc <= cols - 3) & (rr >= 2) & (rr <= rows - 3)
        h = np.maximum(ndimage.map_coordinates(elev, [rr.ravel(), cc.ravel()], order=1, mode="nearest")
                       .reshape(rr.shape), 0)
        col = np.stack([ndimage.map_coordinates(tex[..., k], [rr.ravel(), cc.ravel()], order=1, mode="nearest")
                        .reshape(rr.shape) for k in range(3)], -1)
        col = col * (1 - haze) + SKY * haze
        dry = ndimage.map_coordinates(wet, [rr.ravel(), cc.ravel()], order=0, mode="nearest").reshape(rr.shape) < 0.5
        yv = y_h + cam.f * (cam.h - h / 1000 * cam.ex) / zs[:, None]
        yv = np.where(ok, yv, np.inf)
        mins = np.minimum.accumulate(yv, axis=0)
        lowest = np.where(np.isfinite(yv), yv, -np.inf).max(axis=0)
        for k in range(len(cu)):
            owner = np.searchsorted(-mins[:, k], -rows_px, side="left")
            seen = (owner < steps) & (rows_px <= lowest[k] + 1)
            img[seen, int(cu[k])] = col[owner[seen], k]
            depth[seen, int(cu[k])] = zs[owner[seen]]
            land[seen, int(cu[k])] = dry[owner[seen], k]
    # a foreground of open sea says nothing: the picture ends a little below the nearest land
    share = land.mean(axis=1)
    rows_land = np.flatnonzero(share > 0.04)
    cut = int(rows_land[-1] + 18 * S) if len(rows_land) else Hpx
    # nor does the context margin in front of the extent: the picture ends a little below the extent's near edge
    t = np.linspace(0, 1, 400)
    ex_x = np.r_[bx0 + (bx1 - bx0) * t, np.full(400, bx1), bx1 - (bx1 - bx0) * t, np.full(400, bx0)]
    ex_y = np.r_[np.full(400, by0), by0 + (by1 - by0) * t, np.full(400, by1), by1 - (by1 - by0) * t]
    eu, ev, _ = cam.screen(ex_x, ex_y, g.at(ex_x, ex_y), y_h)
    framed = (eu >= 0) & (eu < Wpx)
    if framed.any():
        cut = min(cut, int(ev[framed].max() + 10 * S))
    Hpx = max(min(Hpx, cut), int(Hpx * 0.3))
    img, depth = img[:Hpx], depth[:Hpx]
    H = Hpx / S
    pic = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).resize((int(W * 300 / 72), int(H * 300 / 72)),
                                                                          Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    pic.save(buf, "JPEG", quality=90, optimize=True)
    body = [f'<image x="0" y="0" width="{W:.1f}" height="{H:.1f}" preserveAspectRatio="none" '
            f'href="data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}"/>']

    to = ex.to_crs

    def at(lon, lat, lift=0.0):
        """Page points of lon/lat points on the ground (plus `lift` metres), and whether the ground shows them."""
        lon, lat = np.atleast_1d(lon), np.atleast_1d(lat)
        x, y = to.transform(lon, lat)
        hgt = g.at(x, y) + lift
        u, v, z = cam.screen(x, y, hgt, y_h)
        ui, vi = np.clip(u.astype(int), 0, Wpx - 1), np.clip(v.astype(int) + int(2 * S), 0, Hpx - 1)
        seen = (z <= depth[vi, ui] * 1.01 + 0.15) & (u >= 0) & (u < Wpx) & (v >= 0) & (v < Hpx)
        return u / S, v / S, seen

    def in_extent(lon, lat):
        w, s, e, n = ex.bbox_lonlat
        return w <= lon <= e and s <= lat <= n

    placer = carto.Labels((0, 0, W, H))
    placer.occupy(0, H - 16, 200, 16)
    rose_svg, rose_box = _rose(ex, g, cam, y_h, S, W, H, at, placer)
    if rose_box:
        placer.occupy(*rose_box)
    runs: list[tuple[str, list]] = []
    # fronts: draped, visible stretches only, with a pale casing
    for k, day in enumerate(ex.fronts):
        last = k == len(ex.fronts) - 1
        for line in figures._fronts(day):
            a = np.asarray([p for p in line if in_extent(*p)], dtype=float)
            if len(a) < 2:
                continue
            # densify so hidden stretches break where the ground covers them
            seg = np.cumsum(np.r_[0, np.hypot(*np.diff(a, axis=0).T)])
            tt = np.linspace(0, seg[-1], max(2, int(seg[-1] / 0.0015)))
            lon, lat = np.interp(tt, seg, a[:, 0]), np.interp(tt, seg, a[:, 1])
            u, v, seen = at(lon, lat, 8)
            lab, n = ndimage.label(seen)
            for i in range(1, n + 1):
                idx = np.flatnonzero(lab == i)
                if len(idx) < 2:
                    continue
                pts = carto.simplify(list(zip(u[idx].tolist(), v[idx].tolist())), 0.3)
                placer.line(pts)
                d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
                body.append(f'<path d="{d}" fill="none" stroke="#ffffff" stroke-width="{3.4 if last else 1.8}" '
                            f'stroke-opacity="0.75" stroke-linejoin="round" stroke-linecap="round"/>')
                style = 'stroke-width="1.8"' if last else 'stroke-width="0.8" stroke-dasharray="3 1.6" stroke-opacity="0.75"'
                body.append(f'<path d="{d}" fill="none" stroke="{FRONT}" {style} stroke-linejoin="round" '
                            f'stroke-linecap="round"/>')
                runs.append((day, pts))
    # divisions on stalks
    shown, unit_svg = [], []
    for un in ex.divisions(figures._units(ex.units)):
        u, v, seen = at(un["lon"], un["lat"])
        gx_, gy_ = float(u[0]), float(v[0])
        hl = bool(highlight) and un.get("unit") == highlight
        nw = carto.Labels.width(symbols.parse_label(str(un.get("label") or ""))[0], 6.8)
        for stalk in (18, 26, 34, 44, 54, 18):
            cy = gy_ - stalk - 5
            rect = (gx_ - 7.5, cy - 10, gx_ + 9.5 + nw, cy + 6)
            if placer.free(rect):
                break
        placer.occupy(rect[0], rect[1], rect[2] - rect[0], rect[3] - rect[1])
        placer.line([(gx_, gy_), (gx_, gy_ - stalk)])
        stroke = OWN if hl else INK
        dash = "" if seen[0] else ' stroke-dasharray="1.2 1.2"'     # behind a rise: the stalk's foot is hidden
        unit_svg.append(f'<line x1="{gx_:.1f}" y1="{gy_:.1f}" x2="{gx_:.1f}" y2="{gy_ - stalk:.1f}" stroke="{stroke}" '
                        f'stroke-width="0.6"{dash}/><circle cx="{gx_:.1f}" cy="{gy_:.1f}" r="1.1" fill="{stroke}"/>')
        unit_svg.append(symbols.symbol(gx_, cy, un, highlight=hl))
        shown.append({**un, "highlight": hl})
    # the units' own records: their positions, the one held on the map's date on a stalk with its own symbol, as the
    # divisions; the aircraft engaged, theirs and others'. No lines between positions: they aren't the way taken
    own_marks = record.marks(ex)
    raids = record.raids(ex)
    places = [f for f in _load(ex, "places") if f["properties"]["name"] not in ex.not_places]
    towns_of = {id(m): record.at_town(ex, m, places) for m in own_marks}
    forced = {t for t in towns_of.values() if t}     # towns a unit's position names: always labelled, once
    labels_svg: list[str] = []
    for m in own_marks + raids:
        u, v, seen = at(m["lon"], m["lat"])
        if not seen[0]:
            continue
        x, y = float(u[0]), float(v[0])
        c = m.get("colour", RAID)
        placer.occupy(x - 4, y - 4, 8, 8)
        if m["kind"] == "station":
            if m["current"] and m["symbol"]:
                for stalk in (18, 26, 34, 44, 18):
                    cy = y - stalk - 5
                    rect = (x - 12, cy - 10, x + 30, cy + 6)
                    if placer.free(rect):
                        break
                placer.occupy(rect[0], rect[1], rect[2] - rect[0], rect[3] - rect[1])
                unit_svg.append(f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x:.1f}" y2="{y - stalk:.1f}" stroke="{c}" '
                                f'stroke-width="0.7"/>')
                unit_svg.append(symbols.symbol(x, cy, m["symbol"], colour=c))
            unit_svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2" fill="{c}" stroke="#ffffff" stroke-width="0.6"/>')
            words = ([(record.span(m), 6.2, c, "bold", DISPLAY)] if towns_of[id(m)] else
                     [(record.name(m), 6.6, c, "bold", DISPLAY), (record.span(m), 6, c, "normal", DISPLAY)])
            labels_svg.append(placer.place(x, y, words, force=True))
        elif m["kind"] == "raid":
            unit_svg.append(_burst(x, y, RAID))
            labels_svg.append(placer.place(x, y, [(f"{record.day(m['date'])}, {m['time']}", 6, RAID, "bold", DISPLAY),
                                                  (m["short"], 5.6, RAID, "normal", DISPLAY)], gap=4))
        else:
            unit_svg.append(_burst(x, y, c))
            labels_svg.append(placer.place(x, y, [(record.day(m["date"]), 6, c, "normal", DISPLAY)], gap=4))
    # the Catholic cathedral, named, where the ground shows it, for an extent that asks for its churches
    if ex.churches:
        for f in _load(ex, "churches"):
            if not f["properties"].get("catholic") or f["properties"]["kind"] != "cathedral":
                continue
            u, v, seen = at(*f["geometry"]["coordinates"])
            if not seen[0]:
                continue
            x, y = float(u[0]), float(v[0])
            unit_svg.append(_cathedral(x, y, k=1.15))
            placer.occupy(x - 4, y - 12, 8, 12)
            labels_svg.append(placer.place(x, y - 5, [(f["properties"]["name"], 6.4, CATHEDRAL, "bold", DISPLAY)],
                                           force=True, gap=4))
    # towns, then hills: labelled only where the ground shows them
    places.sort(key=lambda f: (f["properties"]["name"] not in forced, f["properties"]["name"] not in ex.towns and ex.label(f["properties"]["name"])[0] not in ex.towns,
                               -int(f["properties"].get("population") or 0)
                               if str(f["properties"].get("population") or "0").isdigit() else 0))
    for f in places[:40]:
        lon, lat = f["geometry"]["coordinates"]
        if not in_extent(lon, lat):
            continue
        u, v, seen = at(lon, lat)
        if not seen[0]:
            continue
        major = f["properties"]["name"] in ex.towns or ex.label(f["properties"]["name"])[0] in ex.towns
        name, today = ex.label(f["properties"]["name"])
        lines = [(name, 7.4 if major else 6.2, INK if major else "#4a5249", "bold" if major else "normal", DISPLAY)]
        if today:
            lines.append((f"today {today}", 5.4, "#4a5249", "normal", DISPLAY))
        lab = placer.place(float(u[0]), float(v[0]), lines, gap=2.5, force=f["properties"]["name"] in forced)
        if lab:
            labels_svg.append(f'<circle cx="{float(u[0]):.1f}" cy="{float(v[0]):.1f}" r="{1.6 if major else 1.1}" '
                              f'fill="{INK}"/>' + lab)
    for f in _hills(ex):
        lon, lat = f["geometry"]["coordinates"]
        u, v, seen = at(lon, lat)
        if not seen[0]:
            continue
        ele = f["properties"].get("ele")
        lines = [(f["properties"]["name"], 6.8, "#5a4a2c", "normal", SERIF)]
        if ele:
            lines.append((f"{ele} m", 5.6, "#5a4a2c", "normal", SERIF))
        lab = placer.place(float(u[0]), float(v[0]), lines, gap=3)
        if lab:
            labels_svg.append(f'<path d="M{float(u[0]) - 2.2:.1f},{float(v[0]) + 1.4:.1f} l2.2,-3.4 l2.2,3.4 Z" '
                              f'fill="#5a4a2c"/>' + lab)
    # each front's date, at the nearest visible stretch's middle
    for day in ex.fronts:
        mine = [pts for d_, pts in runs if d_ == day]
        if mine:
            pts = max(mine, key=lambda p: max(y for _, y in p))
            x, y = pts[len(pts) // 2]
            months = ["", "Jan", "Feb", "Mar", "Apr", "May", "June", "July", "Aug", "Sept", "Oct", "Nov", "Dec"]
            labels_svg.append(placer.place(x, y, [(f"{int(day[8:])} {months[int(day[5:7])]}", 7, FRONT, "bold",
                                                   DISPLAY)], gap=3))
    body += unit_svg + labels_svg + [rose_svg]
    body.append(f'<text x="6" y="{H - 6:.1f}" font-family="{DISPLAY}" font-size="7" letter-spacing="1.2" '
                f'fill="#4a5249" stroke="#ffffff" stroke-width="2" paint-order="stroke">HEIGHTS × {exaggeration:g} · '
                f'NOT TO SCALE</text>')
    notes = {"azimuth": azimuth, "tilt": tilt, "exaggeration": exaggeration, "dem_metres": res,
             "terrain": f"Copernicus DEM GLO-30 (doi:10.5270/ESA-c5d3d65), resampled to {ex.crs}",
             "units": [{"label": u.get("label"), "name": symbols.full_name(u), "cite": u.get("cite", "")} for u in shown]}
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.1f}pt" height="{H:.1f}pt" viewBox="0 0 {W:.1f} {H:.1f}">'
           + "".join(body) + "</svg>")
    return halo.split(svg), notes
