# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
"""Sample seafloor depth along each patrol track from NOAA ETOPO1 (1 arc-minute).

Walks each track in records/boats/<boat>/patrol-N/positions.csv, interpolating a point every
STEP_NM nautical miles (great circle, time interpolated between fixes), and
looks up the seafloor under each point. ETOPO1 is fetched from NOAA's ERDDAP
server one 1°x1° tile at a time and cached in sources/etopo1/, so only tiles
the tracks actually cross are downloaded, and only once.

Writes records/boats/<boat>/patrol-N/seafloor.csv: utc, lat, lon, seafloor_m (negative = below
sea level; positive would mean the interpolated line crosses land).

Usage: uv run tools/fetch_seafloor.py [bang/1 | bang ...]   (default: every patrol with a depths.csv)
"""
import csv
import gzip
import math
import sys
import time
import urllib.request
from datetime import timedelta

import records
from check_track import load, nm

CACHE = records.CACHE / "etopo1"
STEP_NM = 2.0
CELLS = 60  # 1 arc-minute cells per degree
URL = ("https://coastwatch.pfeg.noaa.gov/erddap/griddap/etopo180.csv"
       "?altitude%5B({lat0}):1:({lat1})%5D%5B({lon0}):1:({lon1})%5D")

_tiles = {}


def tile(lat_i, lon_i):
    """61x61 grid of altitude (m) for the 1° tile with SW corner (lat_i, lon_i)."""
    key = (lat_i, lon_i)
    if key in _tiles:
        return _tiles[key]
    path = CACHE / f"{lat_i:+03d}{lon_i:+04d}.csv.gz"
    if not path.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        url = URL.format(lat0=lat_i, lat1=lat_i + 1, lon0=lon_i, lon1=lon_i + 1)
        for attempt in range(3):
            try:
                with urllib.request.urlopen(url, timeout=120) as r:
                    raw = r.read()
                break
            except Exception as e:  # ERDDAP occasionally times out; retry
                print(f"  retry {key}: {e}")
                time.sleep(5 * (attempt + 1))
        else:
            raise RuntimeError(f"could not fetch tile {key}")
        path.write_bytes(gzip.compress(raw))
        time.sleep(0.3)  # be polite to the public server
    grid = [[0] * (CELLS + 1) for _ in range(CELLS + 1)]
    lines = gzip.decompress(path.read_bytes()).decode().splitlines()[2:]
    for row in csv.reader(lines):
        la, lo, alt = float(row[0]), float(row[1]), int(float(row[2]))
        grid[round((la - lat_i) * CELLS)][round((lo - lon_i) * CELLS)] = alt
    _tiles[key] = grid
    return grid


def seafloor(lat, lon):
    """Bilinear-interpolated ETOPO1 altitude at (lat, lon), lon in -180..180."""
    lat_i, lon_i = math.floor(lat), math.floor(lon)
    g = tile(lat_i, lon_i)
    y, x = (lat - lat_i) * CELLS, (lon - lon_i) * CELLS
    y0, x0 = min(int(y), CELLS - 1), min(int(x), CELLS - 1)
    fy, fx = y - y0, x - x0
    return ((g[y0][x0] * (1 - fx) + g[y0][x0 + 1] * fx) * (1 - fy)
            + (g[y0 + 1][x0] * (1 - fx) + g[y0 + 1][x0 + 1] * fx) * fy)


def interpolate(a, b, f):
    """Great-circle point a fraction f of the way from a to b; (lat, lon) in degrees."""
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    d = math.acos(min(1, math.sin(la1) * math.sin(la2) + math.cos(la1) * math.cos(la2) * math.cos(lo2 - lo1)))
    if d == 0:
        return a
    A, B = math.sin((1 - f) * d) / math.sin(d), math.sin(f * d) / math.sin(d)
    x = A * math.cos(la1) * math.cos(lo1) + B * math.cos(la2) * math.cos(lo2)
    y = A * math.cos(la1) * math.sin(lo1) + B * math.cos(la2) * math.sin(lo2)
    z = A * math.sin(la1) + B * math.sin(la2)
    lon = math.degrees(math.atan2(y, x))
    return math.degrees(math.atan2(z, math.hypot(x, y))), (lon + 180) % 360 - 180


def run(patrol):
    fixes = [r for r in load(patrol) if r["on_track"] == "yes"]
    out = records.unit_dir(patrol) / "seafloor.csv"
    n = 0
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["utc", "lat", "lon", "seafloor_m"])
        for a, b in zip(fixes, fixes[1:]):
            pa, pb = (a["lat"], a["lon"]), (b["lat"], b["lon"])
            steps = max(1, math.ceil(nm(pa, pb) / STEP_NM))
            for k in range(steps):
                frac = k / steps
                lat, lon = interpolate(pa, pb, frac)
                t = a["utc"] + timedelta(seconds=(b["utc"] - a["utc"]).total_seconds() * frac)
                w.writerow([f"{t:%Y-%m-%dT%H:%MZ}", f"{lat:.4f}", f"{lon:.4f}", round(seafloor(lat, lon))])
                n += 1
        last = fixes[-1]
        w.writerow([f"{last['utc']:%Y-%m-%dT%H:%MZ}", f"{last['lat']:.4f}", f"{last['lon']:.4f}",
                    round(seafloor(last["lat"], last["lon"]))])
    print(f"{patrol}: {n + 1} samples -> {records.rel(out)} ({len(_tiles)} tiles cached so far)")


def targets(args):
    """Patrols named on the command line ('bang/1', or 'bang' for all its patrols), or by
    default every patrol with a depth log (depths.csv), the ones site/dives.html shows."""
    if args:
        return [u for a in args for u in ([a] if "/" in a else records.units(a))]
    return [u for u in records.units() if (records.unit_dir(u) / "depths.csv").exists()]


if __name__ == "__main__":
    import sys
    for p in targets(sys.argv[1:]):
        run(p)
