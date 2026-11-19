"""The HQ Twelfth Army Group situation maps (Library of Congress, g5701s-ict*; the kit's records/fronts/): a slice of a
day's sheet as a plate, with a unit ringed. The sheets' faint base-map roads are not lifted for our maps: at 1:500,000
they are too generalised; the period network comes from IGN's 1:50,000 instead (atlas/reconstruct.py).

Each day's sheet is fitted to the kit's points for it (records/fronts/12ag-<day>-gcps.csv: towns or graticule
crossings, pixel and position) with a second-order polynomial each way, as tools/trace_front.py does. The scans are
the Library's JPEG 2000 originals, cached where the kit's tools cache them (<cache>/maps/loc/).
"""
import base64
import csv
import math
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from . import mapmarks, paths

Image.MAX_IMAGE_PIXELS = None
TILE = "https://tile.loc.gov/storage-services/service/gmd/gmd5/g5701/g5701s/{item}.jp2"


def item(day: str) -> str:
    for row in csv.DictReader(open(paths.records() / "fronts" / "sitmaps.csv")):
        if row["date"] == day:
            return row["item"]
    raise LookupError(f"no situation map for {day} in records/fronts/sitmaps.csv")


def scan(day: str) -> Path:
    it = item(day)
    f = paths.cache() / "maps" / "loc" / f"g5701s-{it}.jp2"
    if not f.exists():
        f.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(TILE.format(item=it), headers={"User-Agent": "wwii-book (research kit)"})
        with urllib.request.urlopen(req, timeout=300) as r:
            f.write_bytes(r.read())
    return f


class Fit:
    """lon/lat -> scan pixel for one day's sheet: a second-order polynomial fitted to the kit's points."""

    def __init__(self, day: str):
        rows = list(csv.DictReader(open(paths.records() / "fronts" / f"12ag-{day}-gcps.csv")))
        lon = np.array([float(r["lon"]) for r in rows])
        lat = np.array([float(r["lat"]) for r in rows])
        x = np.array([float(r["x"]) for r in rows])
        y = np.array([float(r["y"]) for r in rows])
        A = self._terms(lon, lat)
        self.cx = np.linalg.lstsq(A, x, rcond=None)[0]
        self.cy = np.linalg.lstsq(A, y, rcond=None)[0]
        self.rms = float(np.sqrt(np.mean((A @ self.cx - x) ** 2 + (A @ self.cy - y) ** 2)))

    @staticmethod
    def _terms(lon, lat):
        lon, lat = np.asarray(lon, dtype=float), np.asarray(lat, dtype=float)
        return np.stack([np.ones_like(lon), lon, lat, lon * lon, lon * lat, lat * lat], axis=-1)

    def px(self, lon, lat):
        A = self._terms(lon, lat)
        return A @ self.cx, A @ self.cy


def window(day: str, box, pad: int = 40) -> tuple[np.ndarray, int, int, Fit]:
    """The scan's pixels over the box (west, south, east, north), as RGB, with the window's origin and the fit."""
    fit = Fit(day)
    w, s, e, n = box
    xs, ys = fit.px([w, w, e, e], [s, n, s, n])
    x0, y0 = int(max(0, xs.min() - pad)), int(max(0, ys.min() - pad))
    x1, y1 = int(xs.max() + pad), int(ys.max() + pad)
    with Image.open(scan(day)) as im:
        a = np.asarray(im.crop((x0, y0, x1, y1)).convert("RGB"), dtype=np.float32)
    return a, x0, y0, fit


def plate(day: str, box, unit: str | None, dest: Path, ring: str = "#c0261b", width_in: float | None = None) -> dict:
    """A slice of the day's sheet over the box, as scanned, with the unit (its id in the day's units file) ringed.
    With `width_in`, also an SVG beside the PNG (`svg` in the result): the slice at that width with the marks every
    map carries, north where the sheet's fit puts it and km and miles at its middle (mapmarks)."""
    a, x0, y0, fit = window(day, box, pad=0)
    im = Image.fromarray(a.astype(np.uint8))
    found = None
    if unit:
        for row in csv.DictReader(open(paths.records() / "fronts" / f"12ag-{day}-units.csv")):
            if row.get("unit") == unit:
                found = (float(row["x"]) - x0, float(row["y"]) - y0)
                break
        if found:
            draw = ImageDraw.Draw(im)
            cx, cy = found
            for k in range(4):                             # a ring drawn by us, a few pixels thick
                draw.rounded_rectangle((cx - 58 - k, cy - 46 - k, cx + 70 + k, cy + 34 + k), radius=16, outline=ring)
    dest.parent.mkdir(parents=True, exist_ok=True)
    im.filter(ImageFilter.UnsharpMask(radius=1.2, percent=60, threshold=2)).save(dest)
    out = {"px": list(im.size), "item": item(day), "ringed": bool(found), "fit_px": round(fit.rms, 1),
           "scale_m_per_px": round(_metres_per_px(fit, box), 1)}
    if width_in:
        W = width_in * 72
        k = W / im.size[0]                                   # points a scan pixel
        H = im.size[1] * k

        def at(lon, lat):
            xs, ys = fit.px([lon], [lat])
            return (float(xs[0]) - x0) * k, (float(ys[0]) - y0) * k
        w, s_, e, n = box
        bar, _ = mapmarks.scale(W - 10, H - 18, k * 1000 / _metres_per_px(fit, box), "land", max_len=W / 6,
                                anchor="end")
        marks = bar + mapmarks.north(16, H - 16, mapmarks.north_angle(at, (w + e) / 2, (s_ + n) / 2))
        svg = dest.with_suffix(".svg")
        svg.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.1f}pt" height="{H:.1f}pt" '
                       f'viewBox="0 0 {W:.1f} {H:.1f}"><image width="{W:.1f}" height="{H:.1f}" '
                       f'preserveAspectRatio="none" href="data:image/png;base64,'
                       f'{base64.b64encode(dest.read_bytes()).decode()}"/>{marks}</svg>')
        out["svg"] = svg.name
    return out


def _metres_per_px(fit: Fit, box) -> float:
    w, s, e, n = box
    mid = (s + n) / 2
    xs, _ = fit.px([w, e], [mid, mid])
    return (e - w) * 111320 * math.cos(math.radians(mid)) / abs(xs[1] - xs[0])
