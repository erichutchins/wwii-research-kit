# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
"""Sample seafloor depth along each Army unit's LST crossings, from NOAA ETOPO1 (1 arc-minute).

A crossing is a leg between two mapped stations (records/army/army.json, from build_army.py) with a
tank landing ship on it in ships.csv (on a station row from the leg's start up to its end, or the
end station being where the LST landed the unit): the short assault crossings, Bizerte to Sicily and
the like. The ocean crossings are left out. The line is the one the map draws: the route's waypoints
if routes.csv has them, otherwise straight. The ships' real courses aren't in the records, so the
depths are those under the drawn line, not the ship's.

Writes records/army/seafloor.csv: unit, from, to (the leg's station dates), nm (along the line),
lat, lon, seafloor_m (negative = below sea level; positive = the line crosses land there).
Tiles are fetched and cached by fetch_seafloor.py (sources/etopo1/).

Usage: uv run tools/army_seafloor.py        (after build_army.py)
"""
import csv
import json
import math
import re

import records
from fetch_seafloor import interpolate, seafloor

ARMY = records.RECORDS / "army"
STEP_NM = 2.0
LST = re.compile(r"\bLST\b", re.I)   # ships.csv `ship` (or `as_typed`) of a tank landing ship


def nm(a, b):
    """Great-circle distance in nautical miles between (lat, lon) points."""
    la1, lo1, la2, lo2 = map(math.radians, (*a, *b))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * math.asin(math.sqrt(h)) * 3440.065


def crossings(data):
    """(unit, from, to, [(lat, lon), ...]) for every LST leg the map draws."""
    routes = {(r["unit"], r["from"], r["to"]): r for r in data["routes"]}
    for u in data["units"]:
        st = u["stations"]
        pts = [i for i, s in enumerate(st) if s["lat"] is not None]
        for i, j in zip(pts, pts[1:]):
            a, b = st[i], st[j]
            rt = routes.get((u["unit"], a["date"], b["date"]))
            ships = [sh for s in st[i:j] for sh in s.get("ships", [])] + b.get("arrived_by", [])
            if not any(LST.search(sh["ship"] or sh["as_typed"]) for sh in ships):
                continue
            line = [(a["lat"], a["lon"])] + [(p[1], p[0]) for p in (rt["points"] if rt else [])] + [(b["lat"], b["lon"])]
            yield u["unit"], a["date"], b["date"], line


def main():
    data = json.loads((ARMY / "army.json").read_text())
    out = []
    for unit, d0, d1, line in crossings(data):
        run = 0.0
        for k, (p, q) in enumerate(zip(line, line[1:])):
            leg = nm(p, q)
            n = max(1, math.ceil(leg / STEP_NM))
            for s in range(0 if k == 0 else 1, n + 1):
                lat, lon = interpolate(p, q, s / n)
                out.append([unit, d0, d1, round(run + leg * s / n, 1), round(lat, 4), round(lon, 4), round(seafloor(lat, lon))])
            run += leg
        mine = [r[6] for r in out if r[:3] == [unit, d0, d1]]
        wet = [k for k, m in enumerate(mine) if m <= 0]
        inner = mine[wet[0]:wet[-1] + 1] if wet else mine
        land = sum(1 for m in inner if m > 0) / len(inner)
        print(f"{unit} {d0} -> {d1}: {run:,.0f} nm, deepest {-min(mine):,} m, over land between the coasts {land:.0%}")
    with open(ARMY / "seafloor.csv", "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["unit", "from", "to", "nm", "lat", "lon", "seafloor_m"])
        w.writerows(out)
    print(f"wrote {records.rel(ARMY / 'seafloor.csv')}: {len(out)} points")


if __name__ == "__main__":
    main()
