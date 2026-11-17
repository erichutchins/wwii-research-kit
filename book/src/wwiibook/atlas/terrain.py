"""The extent's terrain, shared by both views: Copernicus DEM GLO-30 resampled onto a grid in the atlas's CRS.

GLO-30 is a surface model (it includes woods and buildings, smoothed at 30 m), dated 2011-2015: hills, valleys and
the low marsh ground are as they were in 1944 to within what a 30 m model shows; hedgerows aren't in it. The grid is
written as a GeoTIFF in the extent's build folder, for QGIS as well as for the views.
"""
import math

import numpy as np
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject
from scipy import ndimage

from . import sources
from .extent import Extent


class Grid:
    """Elevations (metres) on a regular grid in the extent's CRS: row 0 at the north edge."""

    def __init__(self, z: np.ndarray, x0: float, y1: float, res: float):
        self.z, self.x0, self.y1, self.res = z, x0, y1, res

    @property
    def shape(self):
        return self.z.shape

    def xy(self, col, row):
        return self.x0 + (np.asarray(col) + 0.5) * self.res, self.y1 - (np.asarray(row) + 0.5) * self.res

    def colrow(self, x, y):
        return (np.asarray(x) - self.x0) / self.res - 0.5, (self.y1 - np.asarray(y)) / self.res - 0.5

    def at(self, x, y):
        """Bilinear elevation at projected points."""
        c, r = self.colrow(x, y)
        return ndimage.map_coordinates(self.z, [np.atleast_1d(r), np.atleast_1d(c)], order=1, mode="nearest")


def dem(ex: Extent, res: float = 20.0, pad: float = 0.0) -> Grid:
    """GLO-30 over the extent (grown by `pad` metres each way) at `res` metres, cached as build/dem-<res>m[-pad].tif."""
    x0, y0, x1, y1 = ex.bounds
    x0, y0, x1, y1 = x0 - pad, y0 - pad, x1 + pad, y1 + pad
    W, H = math.ceil((x1 - x0) / res), math.ceil((y1 - y0) / res)
    dest = ex.build / f"dem-{res:g}m{f'-{pad:g}' if pad else ''}.tif"
    transform = from_origin(x0, y1, res, res)
    if dest.exists():
        with rasterio.open(dest) as src:
            return Grid(src.read(1), x0, y1, res)
    lon, lat = ex.to_lonlat.transform([x0, x1, x0, x1], [y0, y0, y1, y1])
    out = np.full((H, W), np.nan, dtype=np.float32)
    for tile in sources.copernicus((min(lon) - 0.02, min(lat) - 0.02, max(lon) + 0.02, max(lat) + 0.02)):
        part = np.full((H, W), np.nan, dtype=np.float32)
        with rasterio.open(tile) as src:
            reproject(rasterio.band(src, 1), part, dst_transform=transform, dst_crs=ex.crs,
                      resampling=Resampling.bilinear, dst_nodata=np.nan)
        out = np.where(np.isnan(out), part, out)
    out = np.nan_to_num(out, nan=0.0)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(dest, "w", driver="GTiff", width=W, height=H, count=1, dtype="float32", crs=ex.crs,
                       transform=transform, compress="deflate") as dst:
        dst.write(out, 1)
        dst.update_tags(source="Copernicus DEM GLO-30, doi:10.5270/ESA-c5d3d65", resampling="bilinear")
    return Grid(out, x0, y1, res)


def hillshade(g: Grid, azimuth: float = 315, altitude: float = 45, exaggeration: float = 1.0) -> np.ndarray:
    """Lambertian shade, 0 to 1, the sun from `azimuth` degrees (clockwise from grid north) and `altitude` up."""
    z = ndimage.gaussian_filter(g.z.astype(np.float32), 0.8) * exaggeration
    dzdx = ndimage.sobel(z, axis=1) / (8 * g.res)
    dzdy = -ndimage.sobel(z, axis=0) / (8 * g.res)          # rows run south
    az, alt = math.radians(azimuth), math.radians(altitude)
    lx, ly, lz = math.sin(az) * math.cos(alt), math.cos(az) * math.cos(alt), math.sin(alt)
    n = np.sqrt(dzdx ** 2 + dzdy ** 2 + 1)
    return np.clip((-dzdx * lx - dzdy * ly + lz) / n, 0, 1)


def sea(g: Grid) -> np.ndarray:
    """The sea: ground at or below half a metre that reaches the grid's edge (GLO-30 sets the sea to 0)."""
    low = g.z <= 0.5
    lab, _ = ndimage.label(low)
    edge = np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]])
    return np.isin(lab, edge[edge > 0])


def low_ground(g: Grid, below: float = 6.0) -> np.ndarray:
    """Inland ground under `below` metres: the valley floors and marshes (the prairies marécageuses), as the model
    shows them today; drained or flooded, their extent in 1944 is the record's to say."""
    return (g.z < below) & ~sea(g)
