"""The extent as a QGIS project's data: every layer in one GeoPackage in the atlas's CRS, beside the terrain GeoTIFF.

  build/<extent>.gpkg   roads, rails, water, places, hills, junctions, crossings (the reconstruction, every attribute
                        kept), fronts and units (read from the kit's records/fronts/ for the extent's days, with their
                        own properties), and the extent's outline
  build/dem-20m.tif     Copernicus GLO-30 on the same grid (terrain.dem)

Open both in QGIS, set the project CRS to the extent's, and the 3D map view (View > 3D Map Views) drapes the layers
on the DEM. That is the comparison for the oblique renderer: see book/atlas/README.md.
"""
import json

import numpy as np
import shapely
from shapely.geometry import mapping, shape

from .. import paths
from . import terrain
from .extent import Extent


def _write(path, layer: str, feats: list[dict], ex: Extent) -> int:
    from pyogrio.raw import write
    if not feats:
        return 0
    to = ex.to_crs
    geoms = [shapely.transform(shape(f["geometry"]), lambda a: np.column_stack(to.transform(a[:, 0], a[:, 1])))
             for f in feats]
    keys = sorted({k for f in feats for k in f["properties"]})
    fields = {k: np.array([str(f["properties"].get(k, "") if f["properties"].get(k) is not None else "") for f in feats],
                          dtype=object) for k in keys}
    kinds = {g.geom_type for g in geoms}
    gtype = kinds.pop() if len(kinds) == 1 else "Unknown"
    write(str(path), shapely.to_wkb(geoms), list(fields.values()), list(fields), layer=layer, driver="GPKG",
                  geometry_type=gtype, crs=ex.crs)
    return len(feats)


def export(ex: Extent) -> dict:
    ex.build.mkdir(parents=True, exist_ok=True)
    gpkg = ex.build / f"{ex.name}.gpkg"
    gpkg.unlink(missing_ok=True)
    counts = {}
    for layer in ("roads", "rails", "water", "places", "hills", "junctions", "crossings"):
        f = ex.infrastructure / f"{layer}.geojson"
        if f.exists():
            counts[layer] = _write(gpkg, layer, json.loads(f.read_text())["features"], ex)
    for day in sorted({*ex.fronts, ex.units}):
        src = paths.records() / "fronts" / f"12ag-{day}.geojson"
        if not src.exists():
            continue
        feats = json.loads(src.read_text())["features"]
        for kind in ("front", "unit"):
            mine = [f for f in feats if f["properties"].get("kind") == kind]
            counts[f"{kind}s-{day}"] = _write(gpkg, f"{kind}s_{day.replace('-', '')}", mine, ex)
    w, s, e, n = ex.bbox_lonlat
    counts["extent"] = _write(gpkg, "extent", [{"geometry": mapping(shapely.box(w, s, e, n).segmentize(0.01)),
                                                "properties": {"name": ex.name, "title": ex.title}}], ex)
    terrain.dem(ex, res=20.0)
    return {"gpkg": str(gpkg), "dem": str(ex.build / "dem-20m.tif"), "layers": counts}
