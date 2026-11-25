"""A period sheet fitted by its neatline corners and resampled onto a plain longitude-latitude grid, for a view's
ground where IGN's 1950 series doesn't reach (the block view's `sheet:`).

The Karte des Deutschen Reiches 1:100,000 is drawn in degrees: each sheet is 30 minutes of longitude by 15 of latitude
(east of Greenwich), its neatline the inner edge of the minute band. The four corners of the neatline are read on the
scan by eye, in pixels, and kept in the extent's file (`block: sheet: sheets:`); a point inside is placed by bilinear
interpolation between them, which holds to a few tens of metres on these sheets (the Dachau sheets, checked on
churches and stations, agree to 50 m or so). A sheet drawn on a projection with a graticule neatline (the Army Map
Service's GSGS 4416, on the Nord de Guerre Lambert) gives its `projection`: the corners are projected and the scan
fitted to them, which keeps the parallels' curve. Scans are never edited: the mosaic is written beside them in the
cache.

    cd kit/book && uv run python -m wwiibook.atlas.sheetfit neuburg      # writes the extent's block sheet image
"""
import sys

import numpy as np
import yaml
from PIL import Image
from pyproj import Transformer
from scipy import ndimage

from .. import paths

Image.MAX_IMAGE_PIXELS = None


def fit(sheets: list[dict], box: tuple[float, float, float, float], px_per_deg: float) -> Image.Image:
    """Each sheet: `file` (relative to the cache), `extent` [west, south, east, north] in degrees and `corners`
    [[x, y] north-west, north-east, south-east, south-west] in the scan's pixels. A later sheet covers an earlier one
    where they overlap (they meet at the neatline)."""
    bw, bs, be, bn = box
    W, H = int(round((be - bw) * px_per_deg)), int(round((bn - bs) * px_per_deg / 1.0))
    lon = bw + (np.arange(W) + 0.5) / W * (be - bw)
    lat = bn - (np.arange(H) + 0.5) / H * (bn - bs)
    LON, LAT = np.meshgrid(lon, lat)
    out = np.full((H, W, 3), 255, np.uint8)
    for sh in sheets:
        w, s, e, n = (float(v) for v in sh["extent"])
        inside = (LON >= w) & (LON < e) & (LAT > s) & (LAT <= n)
        if not inside.any():
            continue
        corners = np.array(sh["corners"], float)
        if sh.get("projection"):
            # a sheet drawn on a projection (GSGS 4416: Lambert, Nord de Guerre): the corners' degrees are projected
            # and the scan fitted to them by least squares (an affine map), so the curved parallels come out right
            tr = Transformer.from_crs("EPSG:4326", sh["projection"], always_xy=True)
            ce, cn = tr.transform([w, e, e, w], [n, n, s, s])
            A = np.column_stack([ce, cn, np.ones(4)])
            cx, *_ = np.linalg.lstsq(A, corners[:, 0], rcond=None)
            cy, *_ = np.linalg.lstsq(A, corners[:, 1], rcond=None)
            pe, pn = tr.transform(LON[inside], LAT[inside])
            P = np.column_stack([pe, pn, np.ones(len(pe))])
            x, y = P @ cx, P @ cy
        else:
            u = (LON[inside] - w) / (e - w)                      # 0 west, 1 east
            v = (n - LAT[inside]) / (n - s)                      # 0 north, 1 south
            (x0, y0), (x1, y1), (x2, y2), (x3, y3) = corners
            x = (1 - u) * (1 - v) * x0 + u * (1 - v) * x1 + u * v * x2 + (1 - u) * v * x3
            y = (1 - u) * (1 - v) * y0 + u * (1 - v) * y1 + u * v * y2 + (1 - u) * v * y3
        im = np.asarray(Image.open(paths.cache() / sh["file"]).convert("RGB"))
        for k in range(3):
            out[..., k][inside] = ndimage.map_coordinates(im[..., k], [y, x], order=1, mode="nearest")
    return Image.fromarray(out)


def main(name: str) -> None:
    folder = paths.PACKAGE.parents[1] / "atlas" / name
    cfg = yaml.safe_load((folder / "extent.yml").read_text())["block"]["sheet"]
    img = fit(cfg["sheets"], tuple(cfg["box"]), float(cfg.get("px_per_deg", 24000)))
    out = paths.cache() / cfg["image"]
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    print(out, img.size)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "neuburg")
