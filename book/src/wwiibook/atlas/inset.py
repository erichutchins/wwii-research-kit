"""A detail at a larger scale than the panorama, beside it on the page: for an extent's `inset:` (a box and a title),
the period map itself over the box at its own full detail (IGN's 1:50,000, read at twice the panorama's tiles), with
the extent's Catholic churches numbered on it and named in a key below. The churches are today's buildings that OSM
dates to before 1945 or doesn't date; the sheet shows the town as its edition drew it.
"""
import base64
import io
from html import escape

import numpy as np
from PIL import Image

from .. import cartography as carto
from .. import halo
from . import sources
from .extent import Extent
from .panorama import CATHEDRAL, _cathedral, _load

DISPLAY, INK, MUTED = carto.DISPLAY, "#000000", "#586257"
CHURCH_WORDS = ("église", "eglise", "basilique", "cathédrale", "chiesa", "basilica", "cattedrale", "duomo", "kirche",
                "church", "cathedral")


def inset(ex: Extent, width_in: float | None = None) -> tuple[str, dict]:
    cfg = ex.inset
    w, s, e, n = (float(v) for v in cfg["bbox_lonlat"])
    z = int(cfg.get("zoom", 15))
    mos, (tx0, ty0, _) = sources.scan50((w, s, e, n), z)

    def px(lon, lat):
        x, y = sources.txy(lon, lat, z)
        return (np.asarray(x) - tx0) * 256, (np.asarray(y) - ty0) * 256
    (x0, x1), (y0, y1) = px(np.array([w, e]), np.array([n, s]))
    crop = Image.fromarray(mos[int(y0):int(y1), int(x0):int(x1)])
    W = (width_in or float(cfg.get("width_in", 3.0))) * 72
    H = W * crop.height / crop.width
    crop = crop.resize((int(W * 300 / 72), int(H * 300 / 72)), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    crop.save(buf, "JPEG", quality=90, optimize=True)

    def at(lon, lat):
        x, y = px(lon, lat)
        return (float(x) - x0) / (x1 - x0) * W, (float(y) - y0) / (y1 - y0) * H

    # churches a Sunday Mass would be in: named as a church, basilica or cathedral (not a convent's or a hospital's
    # chapel, nor an unnamed building)
    found = [f for f in _load(ex, "churches") if f["properties"].get("catholic")
             and f["properties"]["name"].lower().startswith(CHURCH_WORDS)
             and w <= f["geometry"]["coordinates"][0] <= e and s <= f["geometry"]["coordinates"][1] <= n]
    found.sort(key=lambda f: (f["properties"]["kind"] != "cathedral", -f["geometry"]["coordinates"][1]))
    # a church whose number can't sit wholly inside the map, below its title band, is left to a wider view
    found = [f for f in found if 8 < at(*f["geometry"]["coordinates"])[0] < W - 8
             and 22 < at(*f["geometry"]["coordinates"])[1] < H - 8]
    body = [f'<image width="{W:.1f}" height="{H:.1f}" preserveAspectRatio="none" '
            f'href="data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}"/>']
    key = []
    for k, f in enumerate(found, 1):
        x, y = at(*f["geometry"]["coordinates"])
        if f["properties"]["kind"] == "cathedral":
            body.append(_cathedral(x, y + 3, k=1.3))
        body.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5.2" fill="#ffffff" stroke="{CATHEDRAL}" stroke-width="1"/>'
                    f'<text x="{x:.1f}" y="{y + 2.4:.1f}" font-family="{DISPLAY}" font-size="6.6" font-weight="bold" '
                    f'fill="{CATHEDRAL}" text-anchor="middle">{k}</text>')
        key.append((k, f["properties"]["name"] or "(unnamed church)", f["properties"]["kind"]))
    # the title on a pale band, a 500 m bar
    title = cfg.get("title", "")
    body.append(f'<rect width="{W:.1f}" height="14" fill="#ffffff" fill-opacity="0.85"/>'
                f'<text x="5" y="10" font-family="{DISPLAY}" font-size="7.4" font-weight="bold" fill="{INK}">'
                f'{escape(title.upper())}</text>')
    mpp = (e - w) * 111320 * np.cos(np.radians((s + n) / 2)) / W          # metres a point
    L = 500 / mpp
    bx, by = W - L - 8, H - 7
    body.append(f'<rect x="{bx - 3:.1f}" y="{by - 9:.1f}" width="{L + 6:.1f}" height="13" fill="#ffffff" '
                f'fill-opacity="0.85"/><path d="M{bx:.1f},{by:.1f} h{L:.1f} M{bx:.1f},{by - 3:.1f} v3 '
                f'M{bx + L:.1f},{by - 3:.1f} v3" stroke="{INK}" stroke-width="0.7" fill="none"/>'
                f'<text x="{bx + L / 2:.1f}" y="{by - 3.5:.1f}" font-family="{DISPLAY}" font-size="5.8" fill="{INK}" '
                f'text-anchor="middle">500 m</text>')
    body.append(f'<rect width="{W:.1f}" height="{H:.1f}" fill="none" stroke="{INK}" stroke-width="0.7"/>')
    # the key, in two columns under the map
    rows = (len(key) + 1) // 2
    for i, (k, name, _kind) in enumerate(key):
        cx = 2 + (i // rows) * W / 2
        cy = H + 12 + (i % rows) * 10
        body.append(f'<text x="{cx:.1f}" y="{cy:.1f}" font-family="{DISPLAY}" font-size="6.4" fill="{CATHEDRAL}" '
                    f'font-weight="bold">{k}</text><text x="{cx + 9:.1f}" y="{cy:.1f}" font-family="{DISPLAY}" '
                    f'font-size="6.4" fill="{INK}">{escape(name)}</text>')
    total = H + 12 + rows * 10 + 4
    notes = {"churches": [{"number": k, "name": name, "kind": kind} for k, name, kind in key],
             "zoom": z, "bbox_lonlat": [w, s, e, n]}
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.1f}pt" height="{total:.1f}pt" viewBox="0 0 {W:.1f} '
           f'{total:.1f}">{"".join(body)}</svg>')
    return halo.split(svg), notes
