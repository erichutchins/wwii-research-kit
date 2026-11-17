"""An atlas extent: the shared geography of a coordinated pair of views, and the projected frame both are drawn in."""
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path

import numpy as np
import yaml
from pyproj import Transformer

from .. import paths

ATLAS = paths.PACKAGE.parents[1] / "atlas"          # <kit>/book/atlas: the extents and their reconstructions


@dataclass
class Extent:
    folder: Path
    name: str
    title: str
    crs: str
    bbox_lonlat: tuple[float, float, float, float]
    date: str
    fronts: list[str]
    units: str
    situation_map: str
    locator: dict = field(default_factory=dict)
    towns: list[str] = field(default_factory=list)
    not_places: list[str] = field(default_factory=list)
    churches: bool = False            # an extent that asks: its Catholic churches (the cathedral on the views)
    inset: dict = field(default_factory=dict)   # a detail at a larger scale (the inset view)
    air: dict = field(default_factory=dict)     # the air war round the extent: raids, airfields (the air view)
    stations: list[dict] = field(default_factory=list)
    names: dict = field(default_factory=dict)
    highlight: str = ""
    language: str = ""
    highlight_words: str = ""
    sources: dict = field(default_factory=dict)
    panorama: dict = field(default_factory=dict)
    oblique: dict = field(default_factory=dict)

    @classmethod
    def load(cls, where: str | Path) -> "Extent":
        p = Path(where)
        if not p.exists():
            p = ATLAS / str(where)
        if p.is_dir():
            p = p / "extent.yml"
        d = yaml.safe_load(p.read_text())
        d["bbox_lonlat"] = tuple(float(v) for v in d["bbox_lonlat"])
        d["fronts"] = [str(x) for x in d.get("fronts") or []]
        d.setdefault("units", "")
        d.setdefault("situation_map", "")
        d["units"], d["situation_map"], d["date"] = str(d["units"]), str(d["situation_map"]), str(d["date"])
        d["stations"] = [{k: (v if isinstance(v, dict) else str(v)) for k, v in s.items()}
                         for s in d.get("stations") or []]
        return cls(folder=p.parent, **d)

    @cached_property
    def to_crs(self) -> Transformer:
        return Transformer.from_crs("EPSG:4326", self.crs, always_xy=True)

    @cached_property
    def to_lonlat(self) -> Transformer:
        return Transformer.from_crs(self.crs, "EPSG:4326", always_xy=True)

    @cached_property
    def bounds(self) -> tuple[float, float, float, float]:
        """The extent in the projected system: the envelope of the lon/lat box's edges."""
        w, s, e, n = self.bbox_lonlat
        lon = np.r_[np.linspace(w, e, 50), np.full(50, e), np.linspace(e, w, 50), np.full(50, w)]
        lat = np.r_[np.full(50, s), np.linspace(s, n, 50), np.full(50, n), np.linspace(n, s, 50)]
        x, y = self.to_crs.transform(lon, lat)
        return float(np.min(x)), float(np.min(y)), float(np.max(x)), float(np.max(y))

    def divisions(self, units: list[dict]) -> list[dict]:
        """The divisions inside the extent (and units whose echelon the map doesn't mark): corps and armies are left
        off a map at this scale, as the route maps leave them."""
        w, s, e, n = self.bbox_lonlat
        return [u for u in units if w < u["lon"] < e and s < u["lat"] < n
                and (u.get("echelon") == "xx" or (not u.get("echelon") and u.get("arm")))]

    def label(self, name: str) -> tuple[str, str]:
        """A place's name as the period knew it, and today's where they differ (extent.yml `names`)."""
        old = self.names.get(name)
        return (old, name) if old else (name, "")

    @property
    def infrastructure(self) -> Path:
        return self.folder / "infrastructure"

    @property
    def build(self) -> Path:
        return self.folder / "build"


class Page:
    """A projected extent on the page: (x, y) in the CRS to points from the top left, one scale both ways."""

    def __init__(self, bounds, width_pt: float):
        self.x0, self.y0, self.x1, self.y1 = bounds
        self.k = width_pt / (self.x1 - self.x0)
        self.width = width_pt
        self.height = (self.y1 - self.y0) * self.k

    def pt(self, x, y):
        return (np.asarray(x) - self.x0) * self.k, (self.y1 - np.asarray(y)) * self.k

    def metres_per_pt(self) -> float:
        return 1 / self.k
