"""The atlas's sources, fetched once into the cache and never edited. Each fetch records where and when it came from
(a `.source.json` beside it), so a reconstruction can say which download it rests on.

  IGN SCAN 50 Historique, 1950 series   GEOGRAPHICALGRIDSYSTEMS.MAPS.SCAN50.1950 (Géoplateforme WMTS, Web Mercator
                                       tiles); its sheet index with each sheet's edition year,
                                       GEOGRAPHICALGRIDSYSTEMS.MAPS.SCAN50.1950.GRAPHE:ta_france_cartes_50k_1950_date_wm
                                       (WFS). The series mixes editions: in the Cotentin 1947 to 1959.
  Copernicus DEM GLO-30                 the 1° tiles on AWS (copernicus-dem-30m), doi:10.5270/ESA-c5d3d65.
  OpenStreetMap                         Geofabrik's regional extract (.osm.pbf), parsed with pyosmium.
"""
import datetime as dt
import io
import json
import math
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image

from .. import paths

UA = {"User-Agent": "wwii-book (research kit)"}
WMTS = ("https://data.geopf.fr/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER={layer}&STYLE=normal"
        "&TILEMATRIXSET=PM_3_15&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&FORMAT=image/jpeg")
SCAN50 = "GEOGRAPHICALGRIDSYSTEMS.MAPS.SCAN50.1950"
SHEETS = "GEOGRAPHICALGRIDSYSTEMS.MAPS.SCAN50.1950.GRAPHE:ta_france_cartes_50k_1950_date_wm"
WFS = "https://data.geopf.fr/wfs/ows"
COPERNICUS = "https://copernicus-dem-30m.s3.amazonaws.com/{n}/{n}.tif"
GEOFABRIK = "https://download.geofabrik.de/{region}-latest.osm.pbf"


def _get(url: str, timeout: int = 120, tries: int = 4) -> bytes:
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                return r.read()
        except Exception:
            if attempt == tries - 1:
                raise
            time.sleep(3 * (attempt + 1))
    raise AssertionError("unreachable")


def _note(path: Path, url: str, what: str) -> None:
    path.with_name(path.name + ".source.json").write_text(json.dumps(
        {"url": url, "what": what, "retrieved": dt.date.today().isoformat()}, indent=1))


# ---------------------------------------------------------------- IGN SCAN 50, 1950 series

def txy(lon, lat, z):
    n = 2 ** z
    lat_r = np.radians(lat)
    return (np.asarray(lon) + 180) / 360 * n, (1 - np.log(np.tan(lat_r) + 1 / np.cos(lat_r)) / np.pi) / 2 * n


def tile_lonlat(x, y, z):
    n = 2 ** z
    return np.asarray(x) / n * 360 - 180, np.degrees(np.arctan(np.sinh(np.pi * (1 - 2 * np.asarray(y) / n))))


def scan50(bbox_lonlat, z: int = 14) -> tuple[np.ndarray, tuple[float, float, int]]:
    """The SCAN 50 1950 mosaic over the box, as RGB, and its origin (tile x, tile y, zoom) for placing pixels."""
    w, s, e, n = bbox_lonlat
    x0, y0 = txy(w, n, z)
    x1, y1 = txy(e, s, z)
    tx0, ty0, tx1, ty1 = int(x0), int(y0), int(x1), int(y1)
    folder = paths.cache() / "ign" / "scan50-1950"
    folder.mkdir(parents=True, exist_ok=True)
    mos = np.full(((ty1 - ty0 + 1) * 256, (tx1 - tx0 + 1) * 256, 3), 255, dtype=np.uint8)
    todo = [(x, y) for x in range(tx0, tx1 + 1) for y in range(ty0, ty1 + 1)
            if not (folder / f"{z}-{x}-{y}.jpg").exists()]

    def fetch(xy):
        x, y = xy
        (folder / f"{z}-{x}-{y}.jpg").write_bytes(_get(WMTS.format(layer=SCAN50, z=z, x=x, y=y), 60))
    with ThreadPoolExecutor(8) as pool:
        list(pool.map(fetch, todo))
    for x in range(tx0, tx1 + 1):
        for y in range(ty0, ty1 + 1):
            f = folder / f"{z}-{x}-{y}.jpg"
            mos[(y - ty0) * 256:(y - ty0 + 1) * 256, (x - tx0) * 256:(x - tx0 + 1) * 256] = \
                np.asarray(Image.open(io.BytesIO(f.read_bytes())).convert("RGB"))
    note = folder / "README.source.json"
    if not note.exists():
        note.write_text(json.dumps({"layer": SCAN50, "service": WMTS.split("?")[0], "tiles": "PM_3_15 (Web Mercator)",
                                    "retrieved": dt.date.today().isoformat()}, indent=1))
    return mos, (tx0, ty0, z)


def sheets(bbox_lonlat) -> dict:
    """The 1950 series' sheets over the box (GeoJSON, lon/lat): each with its name and edition year (`annee`)."""
    w, s, e, n = bbox_lonlat
    f = paths.cache() / "ign" / f"scan50-1950-sheets-{w:.2f}_{s:.2f}_{e:.2f}_{n:.2f}.json"
    if not f.exists():
        def m(lon, lat):
            return lon * 20037508.34 / 180, math.log(math.tan((90 + lat) * math.pi / 360)) * 6378137
        bx = (*m(w, s), *m(e, n))
        q = {"SERVICE": "WFS", "VERSION": "2.0.0", "REQUEST": "GetFeature", "TYPENAMES": SHEETS,
             "OUTPUTFORMAT": "application/json", "SRSNAME": "EPSG:4326", "BBOX": ",".join(f"{v:.0f}" for v in bx) + ",EPSG:3857"}
        url = WFS + "?" + urllib.parse.urlencode(q)
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(_get(url))
        _note(f, url, "IGN SCAN 50 1950 sheet index, with each sheet's edition year")
    return json.loads(f.read_text())


# ---------------------------------------------------------------- Copernicus GLO-30

def copernicus(bbox_lonlat) -> list[Path]:
    """The GLO-30 tiles (Cloud-Optimised GeoTIFF, EPSG:4326) covering the box."""
    w, s, e, n = bbox_lonlat
    out = []
    for lat in range(math.floor(s), math.floor(n) + 1):
        for lon in range(math.floor(w), math.floor(e) + 1):
            name = (f"Copernicus_DSM_COG_10_{'N' if lat >= 0 else 'S'}{abs(lat):02d}_00_"
                    f"{'E' if lon >= 0 else 'W'}{abs(lon):03d}_00_DEM")
            f = paths.cache() / "copernicus" / f"{name}.tif"
            if not f.exists():
                url = COPERNICUS.format(n=name)
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_bytes(_get(url, 600))
                _note(f, url, "Copernicus DEM GLO-30 (doi:10.5270/ESA-c5d3d65)")
            out.append(f)
    return out


# ---------------------------------------------------------------- OpenStreetMap

def geofabrik(region: str) -> Path:
    f = paths.cache() / "osm" / f"{region.replace('/', '_')}-latest.osm.pbf"
    if not f.exists():
        url = GEOFABRIK.format(region=region)
        f.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=900) as r, open(f, "wb") as out:
            while chunk := r.read(1 << 20):
                out.write(chunk)
        _note(f, url, "Geofabrik OpenStreetMap extract, (c) OpenStreetMap contributors, ODbL")
    return f


ROADS = {"motorway", "trunk", "primary", "secondary", "tertiary", "unclassified", "residential", "trunk_link",
         "primary_link", "secondary_link", "tertiary_link", "road"}
RAIL = {"rail", "abandoned", "disused", "razed", "dismantled", "narrow_gauge", "preserved", "light_rail"}
WATER = {"river", "canal", "stream"}
PLACES = {"town", "village", "hamlet", "city"}


def osm(region: str, bbox_lonlat) -> dict:
    """Roads, railways (in use or not), waterways, places, named hills and churches inside the box, from the regional extract:
    {"roads": [...], "rails": [...], "water": [...], "places": [...], "peaks": [...]}, each way with its id, tags and lon/lat line.
    Cached beside the extract as JSON, by box."""
    import osmium
    pbf = geofabrik(region)
    w, s, e, n = bbox_lonlat
    cache = pbf.with_name(f"{pbf.stem}.{w:.2f}_{s:.2f}_{e:.2f}_{n:.2f}.json")
    if cache.exists() and cache.stat().st_mtime > pbf.stat().st_mtime:
        got = json.loads(cache.read_text())
        if got.get("v") == 6:                  # an older cache (no churches, ...) is read again
            return got
    out: dict = {"v": 6, "roads": [], "rails": [], "water": [], "places": [], "peaks": [], "churches": []}

    def inside(lon, lat):
        return w <= lon <= e and s <= lat <= n

    def is_church(t) -> bool:
        return t.get("amenity") == "place_of_worship" and t.get("religion", "christian") == "christian"

    def church(kind, oid, t, lon, lat):
        out["churches"].append({"id": f"{kind}/{oid}", "name": t.get("name", ""), "name_fr": t.get("name:fr", ""),
                                "religion": t.get("religion", ""), "denomination": t.get("denomination", ""),
                                "building": t.get("building", ""), "place_of_worship": t.get("place_of_worship", ""),
                                "start_date": t.get("start_date", ""), "wikidata": t.get("wikidata", ""),
                                "lon": lon, "lat": lat})

    class H(osmium.SimpleHandler):
        def node(self, nd):
            t = nd.tags
            if is_church(t) and nd.location.valid() and inside(nd.location.lon, nd.location.lat):
                church("node", nd.id, {k.k: k.v for k in t}, nd.location.lon, nd.location.lat)
            if t.get("place") in PLACES and nd.location.valid() and inside(nd.location.lon, nd.location.lat):
                out["places"].append({"id": nd.id, "name": t.get("name", ""), "place": t.get("place"),
                                      "name_fr": t.get("name:fr", ""), "name_en": t.get("name:en", ""),
                                      "population": t.get("population", ""), "lon": nd.location.lon,
                                      "lat": nd.location.lat})
            elif t.get("natural") in ("peak", "hill") and (t.get("name") or t.get("name:fr")) and nd.location.valid() \
                    and inside(nd.location.lon, nd.location.lat):
                out["peaks"].append({"id": nd.id, "name": t.get("name", ""), "ele": t.get("ele", ""),
                                     "name_fr": t.get("name:fr", ""), "name_en": t.get("name:en", ""),
                                     "lon": nd.location.lon, "lat": nd.location.lat})

        def way(self, wy):
            t = wy.tags
            kind = ("rails" if t.get("railway") in RAIL else "roads" if t.get("highway") in ROADS
                    else "water" if t.get("waterway") in WATER else None)
            if not kind:
                return
            try:
                coords = [(nd.location.lon, nd.location.lat) for nd in wy.nodes]
            except osmium.InvalidLocationError:
                return
            if len(coords) < 2 or not any(inside(x, y) for x, y in coords):
                return
            out[kind].append({"id": wy.id, "tags": {k.k: k.v for k in t}, "coords": coords})

        def area(self, a):
            t = a.tags
            if not is_church(t):
                return
            try:
                pts = [(n.lon, n.lat) for ring in a.outer_rings() for n in ring]
            except osmium.InvalidLocationError:
                return
            if pts:
                lon, lat = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
                if inside(lon, lat):
                    church("way" if a.from_way() else "relation", a.orig_id(), {k.k: k.v for k in t}, lon, lat)

    H().apply_file(str(pbf), locations=True)
    cache.write_text(json.dumps(out))
    return out
