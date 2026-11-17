"""The period map itself over the extent, as the third of an atlas's pages: the sheet the reconstruction reads (IGN's
1:50,000, or the Allies' wartime GSGS sheets), with each unit's own positions ringed in its colour. The rings are
ours; the sheet is as scanned. Where a front's own map exists (the 12th Army Group's), that is the plate instead.
"""
import base64
import io

import numpy as np
from PIL import Image

from .. import cartography as carto
from .. import halo
from . import record
from .extent import Extent
from .reconstruct import Sheet

DISPLAY = carto.DISPLAY


def sheet_view(ex: Extent, width_in: float | None = None) -> tuple[str, dict]:
    sh = Sheet(ex)
    w, s, e, n = ex.bbox_lonlat
    xs, ys = sh.px(np.array([w, e]), np.array([n, s]))
    x0, x1, y0, y1 = float(xs[0]), float(xs[1]), float(ys[0]), float(ys[1])
    crop = Image.fromarray(sh.rgb[int(y0):int(y1), int(x0):int(x1)])
    W = (width_in or float(ex.panorama.get("width_in", 9.6))) * 72
    H = W * crop.height / crop.width
    crop = crop.resize((int(W * 300 / 72), int(H * 300 / 72)), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    crop.save(buf, "JPEG", quality=88, optimize=True)
    body = [f'<image width="{W:.1f}" height="{H:.1f}" preserveAspectRatio="none" '
            f'href="data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}"/>']
    labels = carto.Labels((0, 0, W, H))
    marks = record.marks(ex)

    def at(lon, lat):
        x, y = sh.px(lon, lat)
        return (float(x) - x0) / (x1 - x0) * W, (float(y) - y0) / (y1 - y0) * H
    for m in marks:
        x, y = at(m["lon"], m["lat"])
        labels.occupy(x - 7, y - 7, 14, 14)
    for m in marks:
        if m["kind"] != "station":
            continue
        x, y = at(m["lon"], m["lat"])
        body.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6.5" fill="none" stroke="#ffffff" stroke-width="3.2" '
                    f'stroke-opacity="0.8"/><circle cx="{x:.1f}" cy="{y:.1f}" r="6.5" fill="none" '
                    f'stroke="{m["colour"]}" stroke-width="1.6"/>')
        body.append(labels.place(x, y, [(record.name(m), 7, m["colour"], "bold", DISPLAY),
                                        (record.span(m), 6.2, m["colour"], "normal", DISPLAY)], force=True, gap=8))
    body.append(f'<rect width="{W:.1f}" height="{H:.1f}" fill="none" stroke="#1c221d" stroke-width="0.6"/>')
    notes = {"sheets": [{"sheet": sh.ref(nm), "edition": yr} for _, nm, yr in sh.sheets],
             "placing": sh.placing, "kind": sh.kind,
             "units": list(dict.fromkeys(m["short"] for m in marks))}
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.1f}pt" height="{H:.1f}pt" viewBox="0 0 {W:.1f} '
           f'{H:.1f}">{"".join(body)}</svg>')
    return halo.split(svg), notes
