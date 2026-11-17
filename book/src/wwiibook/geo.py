"""Coastlines and a projection, for maps drawn as SVG.

The land is Natural Earth through world-atlas (the same outlines the kit's site draws), cached in <cache>/geo/ and
decoded here from TopoJSON, so a build needs no geographic library. A map's frame is a Mercator box: right for the
few degrees of sea an engagement covers.
"""
import json
import math
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from . import paths

LAND = "https://cdn.jsdelivr.net/npm/world-atlas@2.0.2/land-{scale}.json"


def land_file(scale: str = "10m") -> Path:
    dest = paths.cache() / "geo" / f"land-{scale}.json"
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(LAND.format(scale=scale), headers={"User-Agent": "wwii-book (research kit)"})
        with urllib.request.urlopen(req, timeout=120) as r:
            dest.write_bytes(r.read())
    return dest


def _arcs(topo: dict) -> list[list[tuple[float, float]]]:
    """Every arc as absolute (lon, lat) points: quantized arcs are delta-encoded integers."""
    t = topo.get("transform")
    out = []
    for arc in topo["arcs"]:
        x = y = 0
        pts = []
        for p in arc:
            if t:
                x, y = x + p[0], y + p[1]
                pts.append((x * t["scale"][0] + t["translate"][0], y * t["scale"][1] + t["translate"][1]))
            else:
                pts.append((p[0], p[1]))
        out.append(pts)
    return out


def land_rings(box: tuple[float, float, float, float], scale: str = "10m") -> list[list[tuple[float, float]]]:
    """The land's polygon rings that touch the box (lon0, lat0, lon1, lat1), as (lon, lat) lists."""
    topo = json.loads(land_file(scale).read_text())
    arcs = _arcs(topo)

    def ring(indexes):
        pts: list[tuple[float, float]] = []
        for i in indexes:
            a = arcs[i] if i >= 0 else arcs[~i][::-1]
            pts.extend(a if not pts else a[1:])
        return pts

    lon0, lat0, lon1, lat1 = box
    out = []
    for geom in topo["objects"]["land"]["geometries"]:
        polys = geom["arcs"] if geom["type"] == "MultiPolygon" else [geom["arcs"]]
        for poly in polys:
            for r in poly:
                pts = ring(r)
                xs, ys = [p[0] for p in pts], [p[1] for p in pts]
                if max(xs) >= lon0 and min(xs) <= lon1 and max(ys) >= lat0 and min(ys) <= lat1:
                    out.append(pts)
    return out


def _merc(lat: float) -> float:
    return math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))


@dataclass
class Frame:
    """A Mercator box fitted to a width in points; (x, y) in points from the top left."""
    lon0: float
    lat0: float
    lon1: float
    lat1: float
    width: float

    @property
    def k(self) -> float:
        return self.width / math.radians(self.lon1 - self.lon0)

    @property
    def height(self) -> float:
        return self.k * (_merc(self.lat1) - _merc(self.lat0))

    def xy(self, lon: float, lat: float) -> tuple[float, float]:
        return (self.k * math.radians(lon - self.lon0), self.k * (_merc(self.lat1) - _merc(lat)))

    def lonlat(self, x, y):
        """The inverse of xy, for arrays of points: (lon, lat) in degrees."""
        import numpy as np
        lon = self.lon0 + np.degrees(np.asarray(x, dtype=float) / self.k)
        lat = np.degrees(np.arctan(np.sinh(_merc(self.lat1) - np.asarray(y, dtype=float) / self.k)))
        return lon, lat

    def nm_per_pt(self) -> float:
        """Nautical miles per point at the frame's middle latitude (a minute of latitude is a nautical mile)."""
        mid = (self.lat0 + self.lat1) / 2
        return 1 / (self.k * math.radians(1 / 60) / math.cos(math.radians(mid)))


def fit(box: tuple[float, float, float, float], width: float, pad: float = 0.08) -> Frame:
    lon0, lat0, lon1, lat1 = box
    dx, dy = (lon1 - lon0) * pad, (lat1 - lat0) * pad
    return Frame(lon0 - dx, lat0 - dy, lon1 + dx, lat1 + dy, width)
