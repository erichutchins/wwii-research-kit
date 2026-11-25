"""The block view: the extent's ground as one solid block in a parallel (axonometric) projection, looking along the
way a record says the unit faced or moved, with the day's front, the divisions on pins and the unit's own stations.

Unlike the perspective oblique view, nothing shrinks with distance: across the view the scale is the same everywhere,
depth along the view is shortened by sin(tilt), and heights are exaggerated (the figure says by how much), so its
scale bar holds along every line across the picture. The ground is IGN's SCAN 50 of the 1950s draped on Copernicus
GLO-30, muted and shaded, the marks on it strong. An arrow is drawn only where extent.yml gives a record's words and
page for a direction, and it says it is a direction, not a route. The compass lies flat on the ground, so each arm
points where that direction runs on the ground; the inset is the extent's locator, north up, with the way the view
looks. Colours: friendly blue and enemy red (the period's convention for coloured maps), the front in black as the
army group's sheets draw it.
"""
import base64
import dataclasses
import io
import math
from html import escape

import numpy as np
from PIL import Image
from scipy import ndimage

from .. import figures, halo, mapmarks, paths, symbols
from . import record, sources, terrain
from .extent import Extent
from .panorama import _locator

PAPER = np.array([251, 250, 246], np.float32)
INK = "#141414"
BLUE, BLUE_OWN = "#184eaa", "#0a348c"
RED = "#c8201a"
GREY = "#5a5a5a"
DISPLAY = figures.DISPLAY
PX_PER_IN = 300.0


def _txt(x, y, s, size, fill=INK, anchor="start", weight="normal", italic=False, halo_w=None):
    hw = size * 0.32 if halo_w is None else halo_w
    style = ' font-style="italic"' if italic else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{DISPLAY}" font-size="{size:.1f}" fill="{fill}" '
            f'font-weight="{weight}"{style} text-anchor="{anchor}" '
            f'stroke="#ffffff" stroke-width="{hw:.1f}" stroke-linejoin="round" paint-order="stroke">{escape(s)}</text>')


class _Camera:
    """The parallel camera: u across the view (to the right), v along it (away), z up, all in metres in the
    extent's CRS about its centre; screen pixels from the block's near-left ground corner at z = 0."""

    def __init__(self, ex: Extent, azimuth: float, tilt: float, exaggeration: float, width_px: float):
        x0, y0, x1, y1 = ex.bounds
        self.xc, self.yc = (x0 + x1) / 2, (y0 + y1) / 2
        a = math.radians(azimuth)
        self.f = (math.sin(a), math.cos(a))
        self.r = (math.cos(a), -math.sin(a))
        us, vs = zip(*(self.uv(x, y) for x in (x0, x1) for y in (y0, y1)))
        self.u0, self.u1, self.v0, self.v1 = min(us), max(us), min(vs), max(vs)
        self.st, self.ct = math.sin(math.radians(tilt)), math.cos(math.radians(tilt))
        self.ex = exaggeration
        self.s = width_px / (self.u1 - self.u0)
        self.base = -30.0

    def uv(self, x, y):
        dx, dy = np.asarray(x) - self.xc, np.asarray(y) - self.yc
        return dx * self.r[0] + dy * self.r[1], dx * self.f[0] + dy * self.f[1]

    def xy(self, u, v):
        u, v = np.asarray(u), np.asarray(v)
        return self.xc + u * self.r[0] + v * self.f[0], self.yc + u * self.r[1] + v * self.f[1]

    def screen(self, u, v, z):
        return (np.asarray(u) - self.u0) * self.s, (np.asarray(v) - self.v0) * self.s * self.st + \
            np.asarray(z) * self.ex * self.s * self.ct


def _sampler(ex: Extent):
    """The period sheet under the block, as a function from longitude and latitude to RGB. By default IGN's SCAN 50
    (France); where it doesn't reach, `block: sheet:` names a mosaic already fitted to a plain longitude-latitude grid
    in the cache (`image`, relative to the cache; `box`, its west, south, east and north edges), such as the Karte des
    Deutschen Reiches sheets fitted by their neatline corners."""
    sheet = ex.block.get("sheet")
    if sheet:
        im = Image.open(paths.cache() / sheet["image"]).convert("RGB")
        mos = np.asarray(im, np.float32)
        bw, bs, be, bn = (float(v) for v in sheet["box"])
        h, w_ = mos.shape[:2]

        def scan(lon, lat):
            c = (lon - bw) / (be - bw) * w_ - 0.5
            r = (bn - lat) / (bn - bs) * h - 0.5
            return np.stack([ndimage.map_coordinates(mos[..., k], [r, c], order=1, mode="nearest", cval=255)
                             for k in range(3)], -1)
        return scan
    w, s, e, n = ex.bbox_lonlat
    mos, (tx0, ty0, zoom) = sources.scan50((w - 0.02, s - 0.02, e + 0.02, n + 0.02),
                                            int(ex.sources.get("scan50_zoom", 14)))
    mos = mos.astype(np.float32)
    n2 = 2 ** zoom

    def scan50(lon, lat):
        c = ((lon + 180) / 360 * n2 - tx0) * 256 - 0.5
        r = ((1 - np.arcsinh(np.tan(np.radians(lat))) / np.pi) / 2 * n2 - ty0) * 256 - 0.5
        return np.stack([ndimage.map_coordinates(mos[..., k], [r, c], order=1, mode="nearest") for k in range(3)], -1)
    return scan50


def _ground(ex: Extent, cam: _Camera, g: terrain.Grid) -> tuple[Image.Image, float]:
    """The block as an RGB image on the paper's tone, and the image row of the screen's y = 0."""
    scan = _sampler(ex)
    mute = float(ex.block.get("mute", 0.55))                     # how far the sheet is held back toward the paper
    low = float(ex.block.get("wash_below", 6))                   # metres: the marsh wash (none inland)

    W = int(round((cam.u1 - cam.u0) * cam.s))
    us = cam.u0 + (np.arange(W) + 0.5) / cam.s
    zmax = float(g.z.max())
    _, ytop = cam.screen(0, cam.v1, zmax)
    _, ybot = cam.screen(0, cam.v0, cam.base)
    H = int(ytop - ybot) + 20
    oy = int(ytop) + 10
    img = np.zeros((H, W, 3), np.float32) + PAPER
    top = np.full(W, H, int)
    dv = 0.45 / (cam.s * cam.st)
    wall = np.array([232, 224, 204], np.float32)
    for i, v in enumerate(np.arange(cam.v0, cam.v1, dv)):
        x, y = cam.xy(us, np.full(W, v))
        z = g.at(x, y)
        _, sy = cam.screen(us, v, z)
        row = (oy - sy).astype(int)
        if i == 0:                                           # the near face: the ground's edge, cut to the base
            _, yb = cam.screen(us, v, cam.base)
            rb = (oy - yb).astype(int)
            for k in range(int((rb - row).max()) + 1):
                rr = row + k
                ok = (rr <= rb) & (rr >= 0) & (rr < H)
                img[rr[ok], np.arange(W)[ok]] = wall
            top = row.copy()
            continue
        need = row < top
        if not need.any():
            continue
        lon, lat = ex.to_lonlat.transform(x, y)
        c = scan(np.asarray(lon), np.asarray(lat))
        gr = c.mean(-1, keepdims=True)
        c = 255 - (255 - (c * 0.55 + gr * 0.45)) * mute          # the sheet, part desaturated and held back
        c = c * np.array([1.0, 0.985, 0.94])
        # light from the upper left of the picture
        xa, ya = cam.xy(us + 30, np.full(W, v))
        xb, yb2 = cam.xy(us, np.full(W, v + 30))
        zx = (g.at(xa, ya) - z) / 30 * cam.ex
        zy = (g.at(xb, yb2) - z) / 30 * cam.ex
        sh = (zx * 0.55 - zy * 0.55 + 0.63) / np.sqrt(zx * zx + zy * zy + 1)
        c = c * np.clip(0.52 + 0.70 * sh, 0.47, 1.10)[:, None]
        marsh = ((z < low) & (z > 0.6))[:, None]
        c = np.where(marsh, c * 0.72 + np.array([150, 190, 196]) * 0.28, c)
        c = np.where((z <= 0.6)[:, None], c * 0.35 + np.array([196, 214, 222]) * 0.65, c)
        span = int((top - row)[need].max())
        for k in range(span):
            rr = top - 1 - k
            ok = need & (rr >= row) & (rr >= 0)
            img[rr[ok], np.arange(W)[ok]] = c[ok]
        top = np.minimum(top, row)
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)), oy


def block(ex: Extent, width_in: float | None = None, highlight: str | None = None,
          highlight_words: str | None = None) -> tuple[str, dict]:
    cfg = ex.block
    if cfg.get("bbox_lonlat"):                                   # the block's own ground, inside the extent's frame
        ex = dataclasses.replace(ex, bbox_lonlat=tuple(float(v) for v in cfg["bbox_lonlat"]))
    W_in = float(width_in or cfg.get("width_in", 5.55))
    k = 72.0 / PX_PER_IN                                          # points per pixel
    cam = _Camera(ex, float(cfg.get("azimuth", 180)), float(cfg.get("tilt", 30)), float(cfg.get("exaggeration", 6)),
                  W_in * PX_PER_IN)
    g = terrain.dem(ex, res=12.5)                                  # its own cache: not the panorama's 15 m grid
    img, oy = _ground(ex, cam, g)
    lift_top = 170 * cam.ex * cam.s * cam.ct * k + 30              # room above the block for the pins
    TOP = 18 + lift_top
    W = W_in * 72
    blockH = img.height * k
    highlight = highlight or ex.highlight or None

    def P(lon, lat, z=None, lift=0.0):
        x, y = ex.to_crs.transform(lon, lat)
        u, v = cam.uv(x, y)
        zz = float(g.at(x, y)[0]) if z is None else z
        sx, sy = cam.screen(u, v, zz + lift)
        return float(sx) * k, TOP + (oy - float(sy)) * k

    def inside(lon, lat):
        x, y = ex.to_crs.transform(lon, lat)
        u, v = cam.uv(x, y)
        return cam.u0 < u < cam.u1 and cam.v0 < v < cam.v1

    def dense(line, step=80.0):
        out = []
        for (a, b), (c, d) in zip(line[:-1], line[1:]):
            n = max(2, int(math.hypot((c - a) * 72600, (d - b) * 110574) / step))
            out += [(a + (c - a) * t, b + (d - b) * t) for t in np.linspace(0, 1, n, endpoint=False)]
        return out + [tuple(line[-1])]

    def runs(line):
        out, cur = [], []
        for p in dense(line):
            if inside(*p):
                cur.append(p)
            elif cur:
                out.append(cur)
                cur = []
        return out + ([cur] if cur else [])

    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=90, optimize=True)
    body = [f'<image x="0" y="{TOP:.2f}" width="{W:.2f}" height="{blockH:.2f}" preserveAspectRatio="none" '
            f'href="data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}"/>']

    # rivers the extent names, traced on the elevation model: along a guide line drawn by hand, the lowest ground
    # within `band` degrees north and south of it at each step east, smoothed (the valley floor, not a surveyed bank)
    for rv in cfg.get("rivers", []):
        guide = np.array(rv["guide"], float)
        band = float(rv.get("band", 0.006))
        lons = np.arange(guide[0, 0], guide[-1, 0], 0.0012)
        glat = np.interp(lons, guide[:, 0], guide[:, 1])
        offs = np.linspace(-band, band, 61)
        LA = glat[:, None] + offs[None, :]
        LO = np.repeat(lons[:, None], len(offs), 1)
        X, Y = ex.to_crs.transform(LO.ravel(), LA.ravel())
        Z = g.at(np.asarray(X), np.asarray(Y)).reshape(LA.shape)
        lat_r = ndimage.median_filter(LA[np.arange(len(lons)), Z.argmin(1)], size=9, mode="nearest")
        lat_r = ndimage.gaussian_filter1d(lat_r, 2.0, mode="nearest")
        for r in runs(list(zip(lons, lat_r))):
            pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in (P(*q) for q in r))
            body.append(f'<polyline points="{pts}" fill="none" stroke="#ffffff" stroke-width="4.4" stroke-linejoin="round" '
                        f'stroke-linecap="round"/><polyline points="{pts}" fill="none" stroke="#2f6fd0" stroke-width="2.4" '
                        f'stroke-linejoin="round" stroke-linecap="round"/>')
        if rv.get("label_at"):
            lx, ly = P(*rv["label_at"])
            body.append(_txt(lx, ly, rv["name"], 9.0, "#1f58b0", "middle", italic=True))

    # fronts: the earlier dashed grey, the day's heavy black with a white casing, ticked on the side its sheet ticks
    tick_side = cfg.get("front_ticks", "")
    for j, day in enumerate(ex.fronts):
        last = j == len(ex.fronts) - 1
        for line in figures._fronts(day):
            for r in runs(line):
                pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in (P(*p) for p in r))
                if not last:
                    body.append(f'<polyline points="{pts}" fill="none" stroke="{GREY}" stroke-width="1.1" '
                                f'stroke-dasharray="4 2.4"/>')
                    continue
                body.append(f'<polyline points="{pts}" fill="none" stroke="#ffffff" stroke-width="4.2" '
                            f'stroke-linejoin="round"/>')
                body.append(f'<polyline points="{pts}" fill="none" stroke="{INK}" stroke-width="2.4" '
                            f'stroke-linejoin="round"/>')
                if tick_side in ("north", "south"):
                    for i in range(2, len(r) - 2, 6):
                        (a, b), (c, d) = r[i - 1], r[i + 1]
                        nx, ny = -(d - b) * 110574, (c - a) * 72600
                        L = math.hypot(nx, ny) or 1
                        if (ny > 0) != (tick_side == "north"):
                            nx, ny = -nx, -ny
                        q = (r[i][0] + nx / L * 260 / 72600, r[i][1] + ny / L * 260 / 110574)
                        (x1, y1), (x2, y2) = P(*r[i]), P(*q)
                        body.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{INK}" '
                                    f'stroke-width="1.2"/>')

    # towns named in the extent's block list
    pg = ex.infrastructure / "places.geojson"
    places = ({f["properties"]["name"]: f["geometry"]["coordinates"]
               for f in __import__("json").loads(pg.read_text())["features"]} if pg.exists() else {})
    places.update({p[0]: (float(p[1]), float(p[2])) for p in cfg.get("places", [])})   # name, lon, lat by hand
    for name in cfg.get("towns", ex.towns):
        if name not in places or not inside(*places[name][:2]):
            continue
        x, y = P(*places[name][:2])
        body.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="1.9" fill="#ffffff" stroke="{INK}" stroke-width="0.8"/>')
        body.append(_txt(x + 3.5, y + 2.6, ex.label(name)[0], 7.4, INK, weight="600"))

    # the divisions on pins, where the day's sheet draws each box (its area, not a headquarters)
    for u in ex.divisions(figures._units(ex.units)):
        if not inside(u["lon"], u["lat"]):
            continue
        ours = u.get("of") != "de"
        hl = bool(highlight) and u.get("unit") == highlight
        col = (BLUE_OWN if hl else BLUE) if ours else RED
        (x, y), (xt, yt) = P(u["lon"], u["lat"]), P(u["lon"], u["lat"], lift=170)
        body.append(f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{xt:.1f}" y2="{yt + 8:.1f}" stroke="#ffffff" stroke-width="2.2"/>'
                    f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{xt:.1f}" y2="{yt + 8:.1f}" stroke="{col}" stroke-width="1"/>'
                    f'<circle cx="{x:.1f}" cy="{y:.1f}" r="1.3" fill="{col}"/>')
        body.append(symbols.symbol(xt, yt, u, scale=1.45 if hl else 1.3, halo=2.0,
                                   colour=col if ours else None, enemy=RED, text_colour=col))

    # the unit's own stations, from its reports
    if cfg.get("stations"):
        sub = dataclasses.replace(ex, stations=[{k2: (v if isinstance(v, dict) else str(v)) for k2, v in s.items()}
                                                for s in cfg["stations"]])
        for m in record.marks(sub):
            if m["kind"] != "station" or not inside(m["lon"], m["lat"]):
                continue
            (x, y), (xt, yt) = P(m["lon"], m["lat"]), P(m["lon"], m["lat"], lift=60)
            r = 4.2 if m.get("current") else 3.2
            body.append(f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{xt:.1f}" y2="{yt:.1f}" stroke="#ffffff" stroke-width="2.2"/>'
                        f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{xt:.1f}" y2="{yt:.1f}" stroke="{BLUE_OWN}" stroke-width="1"/>'
                        f'<circle cx="{xt:.1f}" cy="{yt:.1f}" r="{r}" fill="{BLUE_OWN}" stroke="#ffffff" stroke-width="1.1"/>')
            body.append(_txt(xt + r + 2.5, yt - 1.2, m["place"], 8.6, BLUE_OWN, weight="bold"))
            body.append(_txt(xt + r + 2.5, yt + 7.5, record.span(m), 7.0, BLUE_OWN))

    # points the extent gives by hand: a position the book assumes (open ring) or one a record gives (solid)
    for pt in cfg.get("points", []):
        lon, lat = (float(v) for v in pt["at"])
        if not inside(lon, lat):
            continue
        (x, y), (xt, yt) = P(lon, lat), P(lon, lat, lift=60)
        fill = "#ffffff" if pt.get("assumed") else BLUE_OWN
        dash = ' stroke-dasharray="2 1.4"' if pt.get("assumed") else ""
        body.append(f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{xt:.1f}" y2="{yt:.1f}" stroke="#ffffff" stroke-width="2.2"/>'
                    f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{xt:.1f}" y2="{yt:.1f}" stroke="{BLUE_OWN}" stroke-width="1"'
                    f'{dash}/>'
                    f'<circle cx="{xt:.1f}" cy="{yt:.1f}" r="3.6" fill="{fill}" stroke="{BLUE_OWN}" stroke-width="1.6"/>')
        anchor = pt.get("anchor", "start")
        dx = 7 if anchor == "start" else -7
        body.append(_txt(xt + dx, yt - 1.2, pt["words"], 8.6, BLUE_OWN, anchor, weight="bold"))
        if pt.get("sub"):
            body.append(_txt(xt + dx, yt + 7.5, pt["sub"], 7.0, BLUE_OWN, anchor))

    # arrows: a record's direction, flat and thick at one height so it runs straight over the ground
    notes_arrows = []
    for a in cfg.get("arrows", []):
        (lon0, lat0), (lon1, lat1) = a["from"], a["to"]
        zf = float(a.get("height", 150))
        half, head = float(a.get("half_width", 360)), float(a.get("head", 1000))
        x0_, y0_ = ex.to_crs.transform(lon0, lat0)
        x1_, y1_ = ex.to_crs.transform(lon1, lat1)
        L = math.hypot(x1_ - x0_, y1_ - y0_)
        ux, uy = (x1_ - x0_) / L, (y1_ - y0_) / L
        px, py = -uy, ux
        nx_, ny_ = x1_ - ux * head, y1_ - uy * head
        shape = [(x0_ + px * half, y0_ + py * half), (nx_ + px * half, ny_ + py * half),
                 (nx_ + px * half * 2.2, ny_ + py * half * 2.2), (x1_, y1_),
                 (nx_ - px * half * 2.2, ny_ - py * half * 2.2), (nx_ - px * half, ny_ - py * half),
                 (x0_ - px * half, y0_ - py * half)]

        def scr(pts, dz=0.0):
            out = []
            for X, Y in pts:
                u_, v_ = cam.uv(X, Y)
                sx, sy = cam.screen(u_, v_, zf)
                out.append((float(sx) * k, TOP + (oy - float(sy)) * k + dz))
            return " ".join(f"{x:.1f},{y:.1f}" for x, y in out)
        body.append(f'<polygon points="{scr(shape, 3.2)}" fill="#06205a"/>')
        body.append(f'<polygon points="{scr(shape)}" fill="{BLUE_OWN}" stroke="#ffffff" stroke-width="1.4" '
                    f'stroke-linejoin="round"/>')
        u_, v_ = cam.uv((x0_ + x1_) / 2 + px * half * 3, (y0_ + y1_) / 2 + py * half * 3)
        sx, sy = cam.screen(u_, v_, zf)
        tx, ty = float(sx) * k, TOP + (oy - float(sy)) * k
        anchor = "start" if px * cam.r[0] + py * cam.r[1] > 0 else "end"
        tx += 4 if anchor == "start" else -4
        if a.get("label", True) is False:  # the words go in the caption instead
            notes_arrows.append({"words": a["words"], "quote": a["quote"], "cite": a["cite"]})
            continue
        if a.get("label_at"):  # words set in open ground, with a leader to the arrow's tail
            lx, ly = P(*a["label_at"])
            anchor = a.get("label_anchor", "start")
            ax, ay = P(lon0, lat0, lift=zf)
            body.append(f'<line x1="{ax:.1f}" y1="{ay + 3:.1f}" x2="{lx:.1f}" y2="{ly - 18:.1f}" '
                        f'stroke="#ffffff" stroke-width="2.4"/><line x1="{ax:.1f}" y1="{ay + 3:.1f}" '
                        f'x2="{lx:.1f}" y2="{ly - 18:.1f}" stroke="{BLUE_OWN}" stroke-width="0.9"/>')
            tx, ty = lx, ly
        body.append(_txt(tx, ty - 8, a["words"], 10.5, BLUE_OWN, anchor, "bold"))
        body.append(_txt(tx, ty + 5, f"“{a['quote']}”", 10.0, BLUE_OWN, anchor, italic=True))
        body.append(_txt(tx, ty + 16, f"{a['source']}: a direction, not a route", 8.4, GREY, anchor, italic=True))
        notes_arrows.append({"words": a["words"], "quote": a["quote"], "cite": a["cite"]})

    # the sides, in the corners of each
    for words, at, col in ((cfg.get("near_words"), cam.v0 + float(cfg.get("near_v", 0.22)) * (cam.v1 - cam.v0), BLUE),
                           (cfg.get("far_words"), cam.v0 + 0.85 * (cam.v1 - cam.v0), RED)):
        if words:
            _, sy = cam.screen(cam.u1, at, 0)
            left = col == BLUE and cfg.get("near_left")
            body.append(_txt(6 if left else W - 6, TOP + (oy - float(sy)) * k, words, 9.6, col,
                             "start" if left else "end", italic=True))

    # the compass, flat on the ground (on the water by default: z = 0)
    if cfg.get("compass"):
        clon, clat = cfg["compass"]
        arm = float(cfg.get("compass_arm", 1500))
        cx0, cy0 = ex.to_crs.transform(clon, clat)

        def gp(dx, dy):
            u_, v_ = cam.uv(cx0 + dx, cy0 + dy)
            sx, sy = cam.screen(u_, v_, 0.0)
            return float(sx) * k, TOP + (oy - float(sy)) * k
        c0 = gp(0, 0)
        for nm, dx, dy in (("N", 0, 1), ("S", 0, -1), ("E", 1, 0), ("W", -1, 0)):
            tip, s1, s2 = gp(dx * arm, dy * arm), gp(dy * arm * 0.18, -dx * arm * 0.18), gp(-dy * arm * 0.18, dx * arm * 0.18)
            dark, light = (INK, "#ffffff") if nm == "N" else ("#ffffff", INK)
            body.append(f'<polygon points="{tip[0]:.1f},{tip[1]:.1f} {s1[0]:.1f},{s1[1]:.1f} {c0[0]:.1f},{c0[1]:.1f}" '
                        f'fill="{dark}" stroke="{INK}" stroke-width="0.7"/>'
                        f'<polygon points="{tip[0]:.1f},{tip[1]:.1f} {s2[0]:.1f},{s2[1]:.1f} {c0[0]:.1f},{c0[1]:.1f}" '
                        f'fill="{light}" stroke="{INK}" stroke-width="0.7"/>')
            lx, ly = gp(dx * arm * 1.32, dy * arm * 1.5)
            body.append(_txt(lx, ly + 3.5, nm, 11 if nm == "N" else 8.5, INK, "middle", "bold"))

    # under the block: the scale (true across the view), the key, and the locator with the way the view looks
    yb = TOP + blockH + 16
    depth = {180: "North–south", 0: "North–south", 90: "East–west", 270: "East–west"}.get(
        int(cfg.get("azimuth", 180)) % 360, "Depth along the view")
    across = "east–west" if depth == "North–south" else "north–south" if depth == "East–west" else "across"
    bar, bw = mapmarks.scale(6, yb + 6, cam.s * 1000 * k, max_len=70)
    body.append(bar)
    body.append(_txt(bw + 16, yb + 2, f"A parallel view: the scale holds along every {across} line, front to back.",
                     7.4, GREY, italic=True, halo_w=0))
    body.append(_txt(bw + 16, yb + 10.5, f"{depth} depth is shortened to {cam.st:.2g} of it; heights are drawn "
                     f"{cam.ex:g} times.", 7.4, GREY, italic=True, halo_w=0))
    ky = yb + 40 + (11 if cfg.get("points_words") else 0)
    key = [f'<line x1="6" y1="{ky:.1f}" x2="28" y2="{ky:.1f}" stroke="{INK}" stroke-width="2.4"/>'
           + "".join(f'<line x1="{x}" y1="{ky:.1f}" x2="{x}" y2="{ky + (3.5 if (tick_side == "north") == (abs(float(cfg.get("azimuth", 180)) % 360 - 180) < 90) else -3.5):.1f}" '
                     f'stroke="{INK}" stroke-width="1.2"/>' for x in (10, 17, 24))
           + _txt(32, ky + 2.4, f"front, {_day(ex.fronts[-1])}, ticked on the American side", 7.8, halo_w=0)]
    if len(ex.fronts) > 1:
        key.append(f'<line x1="176" y1="{ky:.1f}" x2="198" y2="{ky:.1f}" stroke="{GREY}" stroke-width="1.1" '
                   f'stroke-dasharray="4 2.4"/>' + _txt(202, ky + 2.4, f"front, {_day(ex.fronts[0])}", 7.8, halo_w=0))
    if cfg.get("stations"):
        key.append(f'<circle cx="9" cy="{ky - 11:.1f}" r="3" fill="{BLUE_OWN}"/>'
                   + _txt(15, ky - 8.6, cfg.get("stations_words", "the unit's stations, from its reports"), 7.8, halo_w=0))
    if cfg.get("points_words"):
        key.append(f'<circle cx="9" cy="{ky - 22:.1f}" r="3" fill="#ffffff" stroke="{BLUE_OWN}" stroke-width="1.4"/>'
                   + _txt(15, ky - 19.6, cfg["points_words"], 7.8, halo_w=0))
    body += key
    body.append(_txt(6, ky + 13, "Divisions on pins, where the day's sheet draws each box (its area, not a headquarters):",
                     7.4, GREY, italic=True, halo_w=0))
    body.append(_txt(6, ky + 23, "blue, American; red, German (pale, elements of a division)"
                     + (f"; {highlight_words}, heavier" if highlight_words else "") + ".", 7.4, GREY, italic=True, halo_w=0))
    body.append(_txt(6, ky + 33, cfg.get("ground_words", "Ground: IGN's 1:50,000 (1950 series) on Copernicus GLO-30; "
                                         "blue wash, ground under 6 m."), 7.4, GREY, italic=True, halo_w=0))
    loc_w = float(cfg.get("locator_width", 96))
    lx0 = W - loc_w - 2
    loc_svg, loc_h = _locator(ex, lx0, yb - 4, loc_w)
    body.append(loc_svg)
    # the way the view looks, an arrow onto the box from behind the camera
    a = math.radians(float(cfg.get("azimuth", 180)))
    lb = tuple(ex.locator["bbox_lonlat"])
    w, s, e, n = ex.bbox_lonlat
    cxl = lx0 + ((w + e) / 2 - lb[0]) / (lb[2] - lb[0]) * loc_w
    cyl = yb - 4 + (lb[3] - (s + n) / 2) / (lb[3] - lb[1]) * loc_h
    hx = (e - w) / (lb[2] - lb[0]) * loc_w / 2
    hy = (n - s) / (lb[3] - lb[1]) * loc_h / 2
    dx, dy = math.sin(a), -math.cos(a)
    tail = (cxl - dx * (hx + 22), cyl - dy * (hy + 22))
    tip = (cxl - dx * (hx + 3), cyl - dy * (hy + 3))
    body.append(f'<line x1="{tail[0]:.1f}" y1="{tail[1]:.1f}" x2="{tip[0]:.1f}" y2="{tip[1]:.1f}" stroke="{INK}" '
                f'stroke-width="1.2"/><path d="M{tip[0] - dy * 3:.1f},{tip[1] + dx * 3:.1f} L{tip[0] + dx * 5:.1f},'
                f'{tip[1] + dy * 5:.1f} L{tip[0] + dy * 3:.1f},{tip[1] - dx * 3:.1f} Z" fill="{INK}"/>')
    body.append(_txt(tail[0] + 4, tail[1] + 2, "looking south" if int(cfg.get("azimuth", 180)) == 180 else "the view", 6.2, INK, italic=True))
    total = max(ky + 36, yb - 4 + loc_h + 4)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.1f}pt" height="{total:.1f}pt" '
           f'viewBox="0 0 {W:.1f} {total:.1f}">{"".join(body)}</svg>')
    notes = {"terrain": "Copernicus DEM GLO-30 (doi:10.5270/ESA-c5d3d65)",
             "ground": (cfg.get("sheet") or {}).get("source", "IGN SCAN 50, 1950 series"),
             "fronts": [f"12ag-{d}" for d in ex.fronts], "arrows": notes_arrows,
             "camera": {"azimuth": cfg.get("azimuth", 180), "tilt": cfg.get("tilt", 30),
                        "exaggeration": cfg.get("exaggeration", 6)}}
    return halo.split(svg), notes


def _day(s: str) -> str:
    return record.day(s)
