"""The Allies' own wartime 1:50,000 sheets as an atlas's period map, where IGN's 1950 series doesn't reach.

The British War Office's GSGS series, many reprinted by the US Army Map Service, cover North Africa, Sicily, Italy,
France and Germany. The units' reports give positions on their grids ("J 775914 Sheet 6, 1:50,000 Br N.W.A. Grid"),
so the sheet is the map the unit itself worked from. Scans come from the libraries that hold them (the University of
Texas's PCL Map Collection for Tunisia), cached under <cache>/maps/<library>/<series>/ and never edited.

A sheet is placed by its own military grid, drawn on it in one colour (purple for the North-West Africa grid): the
grid's lines are found on the scan, numbered from the sheet's margin labels (one easting and one northing a sheet,
read by eye and kept in atlas/sheets/<series>.yml), and every crossing becomes a control point, its grid
coordinates turned into latitude and longitude through the grid's own projection (as the kit's tools/grid_ref.py
defines it). A second-order polynomial each way, fitted to some hundreds of crossings, maps a pixel to a position.
"""
import json
import math
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

import numpy as np
import yaml
from PIL import Image
from pyproj import Transformer
from scipy import ndimage, signal

from .. import paths

Image.MAX_IMAGE_PIXELS = None
SHEETS = paths.PACKAGE.parents[1] / "atlas" / "sheets"

# the grids, as the kit's tools/grid_ref.py defines them (no datum shift: the kit places references the same way)
GRIDS = {
    "nwa": "+proj=lcc +lat_1=34 +lat_0=34 +lon_0=0 +k_0=0.9994 +x_0=1000000 +y_0=500000 "
           "+a=6378249.2 +rf=293.4660213 +units=m +no_defs",
    # South Italy Zone, as printed on GSGS 4229 (Lambert, Bessel, origin 39 30 N 14 E of Greenwich, 700 km E, 600 km N)
    "italy-s": "+proj=lcc +lat_1=39.5 +lat_0=39.5 +lon_0=14 +k_0=0.99906 +x_0=700000 +y_0=600000 "
               "+ellps=bessel +units=m +no_defs",
}
INKS = {
    # the grid's own colour on the scan
    # purple to lavender, as the printings and scans vary: blue over green, red over green, blue a little over red
    "purple": lambda r, g, b: (b - g > 25) & (r - g > 8) & (b - r > 0) & (b - r < 70),
    # blue: the grid's thin lines, bluish and darker than what is round them, so a line over the sea's lighter blue
    # fill counts and the fill doesn't
    "blue": lambda r, g, b: (b - r > 15) & (b >= g) & (_darker((r + g + b) / 3, 11) > 12),
}


@dataclass
class SheetDef:
    series: str
    number: str
    name: str
    file: Path
    url: str
    grid: str
    ink: str
    east0_km: float           # the first labelled easting line (the sheet's west margin label)
    north0_km: float          # the first labelled northing line (the north margin label)
    edition: str
    frame: tuple | None = None    # the sheet's printed frame, west, south, east, north (degrees), where known
    body: tuple = (0.05, 0.09, 0.86, 0.86)   # where on the scan to look for the grid: left, top, right, bottom


def series(name: str) -> dict:
    return yaml.safe_load((SHEETS / f"{name}.yml").read_text())


def sheet(series_name: str, number: str) -> SheetDef:
    d = series(series_name)
    s = d["sheets"][str(number)]
    return SheetDef(series=series_name, number=str(number), name=s["name"],
                    file=paths.cache() / d["cache"] / s["file"], url=d["url"].format(file=s["file"]),
                    grid=d["grid"], ink=d["ink"], east0_km=float(s["east0_km"]), north0_km=float(s["north0_km"]),
                    edition=str(s.get("edition") or d.get("edition", "")),
                    frame=tuple(float(v) for v in s["frame"]) if s.get("frame") else None,
                    body=tuple(float(v) for v in d.get("body", (0.05, 0.09, 0.86, 0.86))))


def fetch(sd: SheetDef) -> Path:
    if not sd.file.exists():
        from .sources import _get, _note
        sd.file.parent.mkdir(parents=True, exist_ok=True)
        sd.file.write_bytes(_get(sd.url, 600))
        _note(sd.file, sd.url, f"{sd.series} sheet {sd.number}, {sd.name}")
    return sd.file


def _lines(mask: np.ndarray, axis: int, spacing: float, bands: int = 10) -> list[tuple[float, float]]:
    """Straight lines of the grid's ink running across `axis` (0: vertical lines, found column by column), as
    (offset, slope): x = offset + slope * y for vertical lines, y = offset + slope * x for horizontal ones. Found as
    peaks of the ink's profile in bands across the sheet, the bands' peaks chained into lines and fitted."""
    m = mask if axis == 0 else mask.T
    H = m.shape[0]
    edges = np.linspace(0, H, bands + 1).astype(int)
    pts: list[tuple[float, float]] = []
    for a, b in zip(edges, edges[1:]):
        prof = ndimage.gaussian_filter1d(m[a:b].sum(0).astype(float), 2)
        pk, _ = signal.find_peaks(prof, distance=int(spacing * 0.6), height=(b - a) * 0.06)
        pts += [(float(x), (a + b) / 2) for x in pk]
    # chain the bands' peaks into lines band by band, each line followed by its own drift (a scan is often turned
    # a degree or two, which over a sheet's width moves a line by most of a kilometre)
    by_band: dict[float, list[float]] = {}
    for x, y in pts:
        by_band.setdefault(y, []).append(x)
    lines: list[list[tuple[float, float]]] = []
    for y in sorted(by_band):
        free = list(range(len(lines)))
        for x in sorted(by_band[y]):
            def predict(ln):
                if len(ln) < 2:
                    return ln[-1][0]
                (x1, y1), (x2, y2) = ln[-2], ln[-1]
                return x2 + (x2 - x1) / (y2 - y1) * (y - y2)
            best = min(free, key=lambda i: abs(predict(lines[i]) - x), default=None)
            if best is not None and abs(predict(lines[best]) - x) < spacing * 0.3:
                lines[best].append((x, y))
                free.remove(best)
            else:
                lines.append([(x, y)])
    out = []
    for ln in lines:
        if len(ln) < bands * 0.5:          # a line must run most of the way across: lettering doesn't
            continue
        xs, ys = np.array(ln).T
        slope, off = np.polyfit(ys, xs, 1)
        res = np.abs(xs - (off + slope * ys))
        keep = res < 4
        if keep.sum() >= 3:
            slope, off = np.polyfit(ys[keep], xs[keep], 1)
        out.append((float(off), float(slope)))
    return out


def _darker(lum: np.ndarray, size: int = 7) -> np.ndarray:
    """How much darker each pixel is than its neighbourhood's lightest (a black top-hat): thin dark strokes stand out
    whatever the tint behind them."""
    soft = ndimage.gaussian_filter(lum.astype(np.float32), 1.6)       # a fine ruled tint (the sea) blurs away
    return ndimage.grey_closing(soft, size=(size, size)) - soft


def _spacing(ink: np.ndarray) -> float:
    """The grid's spacing in pixels: the first strong peak of the ink's column profile's autocorrelation, between
    60 and 400 pixels (a stray peak between two lines would halve a spacing read from neighbouring peaks)."""
    prof = ndimage.gaussian_filter1d(ink.sum(0).astype(float), 1.5)
    prof -= prof.mean()
    ac = np.fft.irfft(np.abs(np.fft.rfft(prof, 2 * len(prof))) ** 2)[:400]
    pk, _ = signal.find_peaks(ac[60:400], height=ac[60:400].max() * 0.5)
    lag = 60 + (pk[0] if len(pk) else int(np.argmax(ac[60:400])))
    # refine to sub-pixel by the peak's parabola
    a, b, c = ac[lag - 1], ac[lag], ac[lag + 1]
    shift = 0.5 * (a - c) / (a - 2 * b + c) if (a - 2 * b + c) < 0 else 0.0
    return float(lag + max(-0.5, min(0.5, shift)))


def _lattice(lines: list[tuple[float, float]], across: int, spacing: float) -> tuple[list, np.ndarray]:
    """The lines that sit on a regular lattice, and each one's number from the first. The lattice's phase is the one
    most lines agree on (a stray line, the frame or a stretch of lettering in the grid's ink, doesn't set it); lines
    more than a sixth of a kilometre off it are dropped; then positions are fitted as first + k * spacing, and the
    fit repeated."""
    pos = np.array([o + s * across / 2 for o, s in lines])
    phase = (pos % spacing) / spacing
    bins = np.histogram(phase, bins=24, range=(0, 1))[0]
    k0 = int(np.argmax(bins + np.roll(bins, 1) + np.roll(bins, -1)))
    centre = (k0 + 0.5) / 24
    near = np.abs(((phase - centre) + 0.5) % 1 - 0.5) < 1 / 6
    centre = float(np.angle(np.exp(2j * np.pi * phase[near]).mean()) / (2 * np.pi)) % 1 if near.any() else centre
    keep = np.abs(((phase - centre) + 0.5) % 1 - 0.5) < 1 / 6
    step = spacing
    for tol in (1 / 6, 1 / 6, 1 / 10):        # the last pass tighter: a stray near the lattice goes too
        first = pos[keep].min()
        k = np.rint((pos - first) / step)
        if keep.sum() >= 3:
            step, first = np.polyfit(k[keep], pos[keep], 1)
        keep &= np.abs((pos - first) / step - k) < tol
    first = pos[keep].min()
    k = np.rint((pos - first) / step).astype(int)
    # two lines given one number: keep the nearer
    best: dict[int, int] = {}
    for i in np.flatnonzero(keep):
        if k[i] not in best or abs(pos[i] - first - k[i] * step) < abs(pos[best[k[i]]] - first - k[i] * step):
            best[int(k[i])] = int(i)
    idx = sorted(best.values())
    return [lines[i] for i in idx], k[idx]


class Placed:
    """A scanned sheet placed by its grid: pixel <-> lon/lat, and how well the crossings fit."""

    def __init__(self, sd: SheetDef):
        self.sd = sd
        with Image.open(fetch(sd)) as im:
            self.rgb = np.asarray(im.convert("RGB"))
        a = self.rgb.astype(np.int16)
        ink = INKS[sd.ink](a[..., 0], a[..., 1], a[..., 2])
        ink &= ~ndimage.binary_opening(ink, structure=np.ones((9, 9)))   # solid fills out: only lines are a grid
        H, W = ink.shape
        self._lum = ndimage.gaussian_filter(a.mean(-1).astype(np.float32), 0.8)
        # the grid's lines are ~1 km apart; estimate the spacing from the whole sheet's profile first
        spacing = _spacing(ink[int(H * .15):int(H * .85), int(W * .05):int(W * .86)])
        body = np.zeros_like(ink)
        # the series' window on the scan (atlas/sheets/<series>.yml `body`): inside its margins and clear of the legend
        bl, bt, br, bb = sd.body
        body[int(H * bt):int(H * bb), int(W * bl):int(W * br)] = True
        ink &= body
        v = _lines(ink, 0, spacing)
        h = _lines(ink, 1, spacing)
        # number the lines: the first labelled line of each axis is the leftmost (topmost) one inside the frame;
        # a line off the 1 km lattice (a stretch of purple lettering, a road in the same ink) is dropped
        v, km_v = _lattice(v, H, spacing)
        h, km_h = _lattice(h, W, spacing)
        self.spacing = spacing
        self.lines = {"vertical": len(v), "horizontal": len(h)}
        px, py, ge, gn = [], [], [], []
        for (ov, sv), kv in zip(v, km_v):
            for (oh, sh_), kh in zip(h, km_h):
                # intersection of x = ov + sv*y and y = oh + sh*x
                x = (ov + sv * oh) / (1 - sv * sh_)
                y = oh + sh_ * x
                px.append(x)
                py.append(y)
                ge.append((sd.east0_km + kv) * 1000)
                gn.append((sd.north0_km - kh) * 1000)
        self.px, self.py = np.array(px), np.array(py)
        to_ll = Transformer.from_crs(GRIDS[sd.grid], "EPSG:4326", always_xy=True)
        ge, gn = np.array(ge), np.array(gn)
        self.shift_km = (0, 0)
        if sd.frame:
            # a first line lost against the frame numbers every line one too late: try shifts, and keep the one that
            # puts every crossing inside the printed frame and within a kilometre of it on every side
            best = None
            for de in range(-2, 3):
                for dn in range(-2, 3):
                    self._fit(*to_ll.transform(ge + de * 1000, gn + dn * 1000))
                    score = self._frame_misfit(sd.frame, spacing)
                    if best is None or score < best[0]:
                        best = (score, de, dn)
            assert best is not None
            self.shift_km = (best[1], best[2])
            ge, gn = ge + best[1] * 1000, gn + best[2] * 1000
        self.lon, self.lat = to_ll.transform(ge, gn)
        self._fit(self.lon, self.lat)
        self.mpp = 1000 / spacing

    def _fit(self, lon, lat) -> None:
        A = self._terms(self.px, self.py)
        self.c_lon = np.linalg.lstsq(A, lon, rcond=None)[0]
        self.c_lat = np.linalg.lstsq(A, lat, rcond=None)[0]
        B = self._terms(lon, lat)
        self.c_x = np.linalg.lstsq(B, self.px, rcond=None)[0]
        self.c_y = np.linalg.lstsq(B, self.py, rcond=None)[0]
        res = np.hypot(B @ self.c_x - self.px, B @ self.c_y - self.py)
        self.rms_px = float(np.sqrt(np.mean(res ** 2)))

    def _frame_misfit(self, frame, spacing: float) -> float:
        """How far the predicted frame lies from the sheet's own printed frame line: the mean, along the four sides,
        of how light the scan is at its darkest within 4 pixels across the predicted side. The printed neat-line is
        the darkest line there, so the right numbering scores lowest."""
        w, s, e, n = frame
        t = np.linspace(0.03, 0.97, 160)
        lon = np.r_[w + (e - w) * t, np.full(160, e), w + (e - w) * t, np.full(160, w)]
        lat = np.r_[np.full(160, n), s + (n - s) * t, np.full(160, s), s + (n - s) * t]
        x, y = self.pixel(lon, lat)
        lum = self._lum
        H, W = lum.shape
        score = []
        for k in range(len(x)):
            horizontal = k < 160 or 320 <= k < 480
            xi, yi = int(round(x[k])), int(round(y[k]))
            if not (5 <= xi < W - 5 and 5 <= yi < H - 5):
                score.append(255.0)
                continue
            seg = lum[yi - 4:yi + 5, xi] if horizontal else lum[yi, xi - 4:xi + 5]
            score.append(float(seg.min()))
        return float(np.mean(score))

    @staticmethod
    def _terms(a, b):
        a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
        return np.stack([np.ones_like(a), a, b, a * a, a * b, b * b], axis=-1)

    def lonlat(self, x, y):
        A = self._terms(x, y)
        return A @ self.c_lon, A @ self.c_lat

    def pixel(self, lon, lat):
        B = self._terms(lon, lat)
        return B @ self.c_x, B @ self.c_y

    @cached_property
    def bounds(self) -> tuple[float, float, float, float]:
        lon, lat = self.lon, self.lat
        return float(lon.min()), float(lat.min()), float(lon.max()), float(lat.max())

    def report(self) -> dict:
        return {"sheet": self.sd.number, "name": self.sd.name, "crossings": int(len(self.px)), "lines": self.lines,
                "shift_km": list(self.shift_km),
                "px_per_km": round(self.spacing, 1), "fit_rms_m": round(self.rms_px * self.mpp, 1),
                "bounds": [round(v, 4) for v in self.bounds]}


def mosaic(series_name: str, numbers: list[str], bbox_lonlat, mpp: float = 6.0):
    """The sheets resampled onto one lon/lat grid over the box (rows north to south, `mpp` metres a pixel): RGB, the
    grid (west, south, east, north, width, height), each sheet's placing report, and each sheet's footprint
    (lon/lat polygon, number, name, edition year). A sheet's footprint is the hull of its grid crossings: the sheets
    of a series share their edge lines, so the footprints tile. Earlier sheets win where two overlap."""
    import shapely
    w, s, e, n = bbox_lonlat
    kx = 111320 * math.cos(math.radians((s + n) / 2))
    W, H = int((e - w) * kx / mpp), int((n - s) * 110570 / mpp)
    lon = w + (np.arange(W) + 0.5) / W * (e - w)
    lat = n - (np.arange(H) + 0.5) / H * (n - s)
    LON, LAT = np.meshgrid(lon, lat)
    out = np.full((H, W, 3), 255, dtype=np.uint8)
    have = np.zeros((H, W), dtype=bool)
    reports, hulls = [], []
    # first each sheet's core (the hull of its crossings), then the strip to its frame: a sheet's edge line, on
    # its frame, is seldom found, so the cores stop up to a kilometre short of the next sheet's
    for grow in (0.0, 1.0):
        for num in numbers:
            sd = sheet(series_name, num)
            pl = Placed(sd)
            # the sheet's printed frame where the series gives it; else the hull of its crossings, grown to the frame
            hull = shapely.box(*sd.frame) if sd.frame else shapely.MultiPoint(np.c_[pl.lon, pl.lat]).convex_hull
            if not grow:
                reports.append(pl.report())
                hulls.append((hull, sd.number, sd.name, int(sd.edition)))
            if grow and sd.frame:
                continue
            area = hull.buffer(grow * 1000 / 110570) if grow else hull
            inside = shapely.contains_xy(area, LON, LAT) & ~have
            if inside.any():
                x, y = pl.pixel(LON[inside], LAT[inside])
                for k in range(3):
                    out[..., k][inside] = ndimage.map_coordinates(pl.rgb[..., k], [y, x], order=1,
                                                                  mode="nearest").astype(np.uint8)
                have |= inside
            del pl
    return out, (w, s, e, n, W, H), reports, hulls


def report_json(reports: list[dict]) -> str:
    return json.dumps(reports, indent=1)
