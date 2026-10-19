# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
"""Hourly ERA5 weather along each patrol track, via the Open-Meteo archive API.

ERA5 is ECMWF's climate reanalysis (0.25°, hourly), which now reaches back to
1940. For each UTC day of a patrol this asks for that day's 24 hours at the
boat's position at 00, 06, 12 and 18 GCT (interpolated along the track), and
each hour takes the values from the nearest of those four positions.

Responses are cached in sources/era5/ so re-runs don't re-download.
Writes records/boats/<boat>/patrol-N/weather.csv.

Usage: uv run tools/fetch_weather.py [bang/1 | bang ...]   (default: every patrol with a depths.csv)
"""
import csv
import json
import time
import urllib.request
from datetime import datetime, timedelta

import records
from check_track import load
from fetch_seafloor import interpolate

CACHE = records.CACHE / "era5"
VARS = ["temperature_2m", "pressure_msl", "wind_speed_10m", "wind_direction_10m",
        "wind_gusts_10m", "cloud_cover", "precipitation"]
URL = ("https://archive-api.open-meteo.com/v1/archive?latitude={lats}&longitude={lons}"
       "&start_date={day}&end_date={day}&hourly=" + ",".join(VARS) + "&wind_speed_unit=kn&timezone=GMT")


def position(fixes, t):
    """Boat position (lat, lon) at time t, great-circle between bracketing fixes."""
    if t <= fixes[0]["utc"]:
        return fixes[0]["lat"], fixes[0]["lon"]
    for a, b in zip(fixes, fixes[1:]):
        if a["utc"] <= t <= b["utc"]:
            span = (b["utc"] - a["utc"]).total_seconds() or 1
            return interpolate((a["lat"], a["lon"]), (b["lat"], b["lon"]), (t - a["utc"]).total_seconds() / span)
    return fixes[-1]["lat"], fixes[-1]["lon"]


def fetch_day(day, points):
    """ERA5 hourly for one UTC day at up to four (lat, lon) points; cached."""
    key = day.strftime("%Y-%m-%d") + "_" + "_".join(f"{la:.2f},{lo:.2f}" for la, lo in points)
    path = CACHE / f"{key}.json"
    if not path.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        url = URL.format(lats=",".join(f"{la:.2f}" for la, _ in points),
                         lons=",".join(f"{lo:.2f}" for _, lo in points), day=day.strftime("%Y-%m-%d"))
        for attempt in range(4):
            try:
                with urllib.request.urlopen(url, timeout=60) as r:
                    path.write_bytes(r.read())
                break
            except Exception as e:  # rate limits / timeouts: back off and retry
                print(f"  retry {key}: {e}")
                time.sleep(10 * (attempt + 1))
        else:
            raise RuntimeError(f"could not fetch {key}")
        time.sleep(0.25)
    data = json.loads(path.read_text())
    return data if isinstance(data, list) else [data]


def run(patrol):
    fixes = [r for r in load(patrol) if r["on_track"] == "yes"]
    start, end = fixes[0]["utc"], fixes[-1]["utc"]
    day = datetime(start.year, start.month, start.day)
    out = records.unit_dir(patrol) / "weather.csv"
    rows = 0
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["utc", "lat", "lon", "temp_c", "pressure_hpa", "wind_kn", "wind_dir", "gust_kn", "cloud_pct", "precip_mm"])
        while day <= end:
            points = [position(fixes, day + timedelta(hours=h)) for h in (0, 6, 12, 18)]
            points = [(round(la * 4) / 4, round(lo * 4) / 4) for la, lo in points]  # ERA5 grid is 0.25°
            series = fetch_day(day, points)
            for hour in range(24):
                t = day + timedelta(hours=hour)
                if t < start - timedelta(hours=1) or t > end + timedelta(hours=1):
                    continue
                k = min(3, (hour + 3) // 6)  # nearest of the 00/06/12/18 positions
                h = series[k]["hourly"]
                la, lo = points[k]
                w.writerow([f"{t:%Y-%m-%dT%H:%MZ}", la, lo] + [h[v][hour] for v in VARS])
                rows += 1
            day += timedelta(days=1)
    print(f"{patrol}: {rows} hours -> {records.rel(out)}")


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
