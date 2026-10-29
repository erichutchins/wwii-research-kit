"""Check the Army transcriptions and build records/army/army.json for site/army.html.

Inputs (hand-edited, the source of truth; columns in records/army/README.md):
  units.csv      batteries, companies, detachments, a division, and their lineage
  stations.csv   each unit's station whenever it changed, as typed, with its page
  places.csv     coordinates for the places stations name
  routes.csv     waypoints for legs the reports don't trace (sea crossings, train rides),
                 drawn as assumed routes between two stations of a unit
  actions.csv    engagements and casualties in the battalion's histories that name the battery
  ships.csv      the ships of the sea crossings: what the reports typed, which ship it was
                 (or why it isn't known), and its history, with sources

Stations like "10 Mi SE Battipaglia" are placed by applying the distance and bearing in the
`offset` column to the named place. A station that also gives a grid reference (`grid`, on the
grid named in `grid_on`) is placed at the grid point instead when that is the more exact of the
two: a reference to 1 km or better that falls within AGREE_KM of the town. A two-digit reference
(10 km) is coarser than the town; one that misses is a typing slip.

Checks: every station has a known source and a page that fits it; every station's place has
coordinates; dates run forward within a unit; no move faster than MAX_KM_PER_DAY unless the
row's note says it went by sea or air; every route joins two mapped stations; every ship matches
a station; every action is placed (grid, place, or the unit's station that day) and has a known
kind.

`place()` does the work for any set of rows, so a project that adds its own units or sources to
these (a family's replacement depots, say) places them the same way.

  python3 tools/build_army.py      # must report 0 problems
"""
import csv
import json
import math
import re
import sys
from datetime import date

from grid_ref import GRIDS, decode as grid_decode
from records import RECORDS

ARMY = RECORDS / "army"
MAX_KM_PER_DAY = 350        # a motorized AA battery on the move; ships and planes are exempt
KM_PER_MILE = 1.609344
# A grid point replaces the town when they agree this closely. Every reference that names its
# town falls within 6 km of it (towns are taken at their centres, offsets as typed), and every
# known slip misses by 9.6 km or more.
AGREE_KM = 8
# stations.csv `source` (README.md), and the page citation each takes (SOURCES.yml):
# mr = the unit's morning report; btry = the battery's own position from the battalion's records
# (45th Infantry Division Museum); bn = the battalion command post from those records, the
# battery assumed nearby; regt = the regimental headquarters battery's morning report, for a
# detachment whose own reports are missing; hist = the 894th's printed history; aar = the
# battalion's symbol on Third Army's antiaircraft situation maps, or its move in the report's
# text; div = a division's position (or one combat command's); cp = a headquarters' command post, from the ETO
# order of battle: its own position; uaar = the unit's own after action report, as transcribed: its own position
AAR = r"aar3/p\d{3}"
PAGE = {"mr": r"rg64-\d+/p\d{4}", "btry": r"ok45th-\d+/p\d{2}", "bn": r"ok45th-\d+/p\d{2}",
        "regt": r"rg64-\d+/p\d{4}", "hist": r"hist894/p\d{2}", "aar": AAR,
        "div": AAR + r"|gi9ad|wiki9ad|etoob-\w+/p\d+(?:-\d+)?|rg64-\d+/p\d{4}",
        "cp": r"etoob-\w+/p\d+(?:-\d+)?", "uaar": r"eucmh60aib/\d{4}-\d{2}"}
# stations.csv `precision` (optional): how a position was given, when its source doesn't say (README.md)
PRECISIONS = ("grid-100m", "grid-1km", "town", "area", "division")
# actions.csv `kind` and `placed`
KINDS = ("air", "ground", "casualty", "event")
PLACED = ("grid", "place", "station")
# ships.csv `status`: confirmed (the ship is identified), candidate (a possible identification),
# unknown (the typed name or number doesn't identify a ship), none (the crossing isn't recorded)
SHIP_STATUS = ("confirmed", "candidate", "unknown", "none")
BEARINGS = {"N": 0, "NNE": 22.5, "NE": 45, "ENE": 67.5, "E": 90, "ESE": 112.5, "SE": 135, "SSE": 157.5,
            "S": 180, "SSW": 202.5, "SW": 225, "WSW": 247.5, "W": 270, "WNW": 292.5, "NW": 315, "NNW": 337.5}


def read(path):
    with path.open(newline="") as f:
        return [{k: (v or "").strip() for k, v in r.items()} for r in csv.DictReader(f)]


def day(s):
    return date.fromisoformat(s)


def offset(lat, lon, spec):
    """'10 mi SE' / '3 km N' / '500 yd S' -> a point that far along that bearing."""
    m = re.fullmatch(r"([\d.]+)\s*(mi|km|yd)\s+([NSEW]{1,3})", spec)
    if not m:
        sys.exit(f"bad offset {spec!r} (want e.g. '10 mi SE')")
    km = float(m[1]) * {"mi": KM_PER_MILE, "km": 1, "yd": 0.0009144}[m[2]]
    b, d = math.radians(BEARINGS[m[3]]), km / 6371.0
    la, lo = math.radians(lat), math.radians(lon)
    la2 = math.asin(math.sin(la) * math.cos(d) + math.cos(la) * math.sin(d) * math.cos(b))
    lo2 = lo + math.atan2(math.sin(b) * math.sin(d) * math.cos(la), math.cos(d) - math.sin(la) * math.sin(la2))
    return round(math.degrees(la2), 4), round(math.degrees(lo2), 4)


def km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def place(rows, page=PAGE):
    """Place and check every unit's stations, routes, ships and actions.

    rows(name) returns a file's rows ("stations.csv" ...); page maps each station source to the
    citation it takes. Returns places, units, stations and actions (each by unit), routes, and
    the problems found."""
    problems = []
    places = {r["place"]: r for r in rows("places.csv")}
    units = {r["unit"]: r for r in rows("units.csv")}

    stations = {}
    for r in rows("stations.csv"):
        if r["unit"] not in units:
            problems.append(f"stations: unknown unit {r['unit']}")
            continue
        if r["source"] not in page:
            problems.append(f"stations: {r['unit']} {r['date']} source {r['source']!r} (want one of {', '.join(page)})")
        if not re.fullmatch(page.get(r["source"], r".+"), r["page"]):
            problems.append(f"stations: {r['unit']} {r['date']} page {r['page']!r} doesn't fit source {r['source']!r}")
        if r.get("precision") and r["precision"] not in PRECISIONS:
            problems.append(f"stations: {r['unit']} {r['date']} precision {r['precision']!r} (want one of {', '.join(PRECISIONS)})")
        if not r["place"]:
            # "At sea", "en route": in the log, not on the map
            stations.setdefault(r["unit"], []).append(dict(r, lat=None, lon=None))
            continue
        p = places.get(r["place"])
        if not p or not (p["lat"] and p["lon"]):
            problems.append(f"stations: {r['unit']} {r['date']} place {r['place']!r} has no coordinates in places.csv")
            continue
        lat, lon = float(p["lat"]), float(p["lon"])
        if r["offset"]:
            lat, lon = offset(lat, lon, r["offset"])
        town = (lat, lon)
        placed, grid = "town", None
        if r["grid"] and r["grid_on"] not in GRIDS:
            problems.append(f"stations: {r['unit']} {r['date']} grid {r['grid']!r} needs grid_on (one of {', '.join(GRIDS)})")
        elif r["grid"] and "?" not in r["grid"]:
            try:
                g = grid_decode(r["grid_on"], r["grid"], near=town)
            except ValueError as e:
                problems.append(f"stations: {r['unit']} {r['date']} {e}")
            else:
                d = km(town, (g["lat"], g["lon"]))
                grid = {"on": GRIDS[r["grid_on"]][0], "cell_m": g["cell"], "km_from_town": round(d, 1),
                        "square_from_town": g["inferred"]}
                if p.get("source") == "grid":
                    placed = "grid-place"   # the place itself was made from the grid (its note says how)
                elif g["cell"] <= 1000 and d <= AGREE_KM:
                    placed, lat, lon = "grid", round(g["lat"], 4), round(g["lon"], 4)
        stations.setdefault(r["unit"], []).append({
            "date": r["date"], "lat": lat, "lon": lon, "place": r["place"], "offset": r["offset"],
            "station": r["station"], "page": r["page"], "source": r["source"], "note": r["note"],
            "place_note": p.get("note", ""), "place_source": p.get("source", ""),
            "grid": r["grid"], "placed": placed, "grid_check": grid,
            **{k: r[k] for k in ("when", "precision") if r.get(k)},
        })
    for u, st in stations.items():
        fixed = [x for x in st if x["lat"] is not None]
        for x, y in zip(st, st[1:]):
            if y["date"] < x["date"]:
                problems.append(f"stations: {u} goes back in time {x['date']} -> {y['date']}")
        for a, b in zip(fixed, fixed[1:]):
            days = max((day(b["date"]) - day(a["date"])).days, 1)
            d = km((a["lat"], a["lon"]), (b["lat"], b["lon"]))
            if d / days > MAX_KM_PER_DAY and not re.search(r"\b(sea|ship|convoy|air|flew|LST|LCT)\b", b["note"], re.I):
                problems.append(f"stations: {u} {a['date']} -> {b['date']} {d:.0f} km in {days} d (say 'by sea' in the note if it was)")

    # Ships: on the station row they're typed on (or, for a crossing the reports don't
    # record, the arrival row), and on the station where the crossing ended (`landed`)
    for r in rows("ships.csv"):
        where = f"ships: {r['unit']} {r['date']}"
        if r["status"] not in SHIP_STATUS:
            problems.append(f"{where} status {r['status']!r} (want one of {', '.join(SHIP_STATUS)})")
        st = stations.get(r["unit"], [])
        at = [i for i, x in enumerate(st) if x["date"] == r["date"]]
        if not at:
            problems.append(f"{where} matches no station of that unit")
            continue
        info = {k: r[k] for k in ("as_typed", "ship", "status", "voyage", "about")}
        info["links"] = r["links"].split()
        st[at[0]].setdefault("ships", []).append(info)
        landing = [x for x in st if x["date"] == r["landed"] and x["lat"] is not None]
        if not landing:
            problems.append(f"{where} landed {r['landed']!r} matches no mapped station of that unit")
        elif landing[0] is not st[at[0]]:
            landing[0].setdefault("arrived_by", []).append(info)

    routes = {}
    for r in rows("routes.csv"):
        key = (r["unit"], r["from_date"], r["to_date"])
        rt = routes.setdefault(key, {"unit": r["unit"], "from": r["from_date"], "to": r["to_date"], "points": [], "note": ""})
        rt["points"].append((int(r["seq"]), [float(r["lon"]), float(r["lat"])]))
        rt["note"] = rt["note"] or r["note"]
        rt["by"] = rt.get("by") or r.get("by", "")
    for (u, f, t), rt in routes.items():
        rt["points"] = [pt for _, pt in sorted(rt["points"])]
        dates = {x["date"] for x in stations.get(u, []) if x["lat"] is not None}
        if f not in dates or t not in dates:
            problems.append(f"routes: {u} {f} -> {t} doesn't join two mapped stations of that unit")

    # Actions: placed at a grid reference, a named place, or (when the
    # report gives no usable position) wherever the unit's station was that day
    actions = {}
    for r in rows("actions.csv"):
        where = f"actions: {r['unit']} {r['date']} {r['time']}"
        if r["unit"] not in units:
            problems.append(f"{where} unknown unit")
            continue
        if r["kind"] not in KINDS or r["placed"] not in PLACED:
            problems.append(f"{where} kind {r['kind']!r} / placed {r['placed']!r} (want {KINDS} / {PLACED})")
            continue
        if not re.fullmatch(r"ok45th-\d+/p\d{2}|rg64-\d+/p\d{4}", r["page"]):
            problems.append(f"{where} page {r['page']!r}")
        lat = lon = None
        if r["placed"] == "grid":
            try:
                if r["grid_on"] not in GRIDS:
                    raise ValueError(f"grid_on {r['grid_on']!r} (want one of {', '.join(GRIDS)})")
                g = grid_decode(r["grid_on"], r["grid"])
                lat, lon = g["lat"], g["lon"]
            except ValueError as e:
                problems.append(f"{where} {e}")
        elif r["placed"] == "place":
            p = places.get(r["place"])
            if not p or not p["lat"]:
                problems.append(f"{where} place {r['place']!r} has no coordinates in places.csv")
            else:
                lat, lon = float(p["lat"]), float(p["lon"])
        else:
            st = [x for x in stations.get(r["unit"], []) if x["lat"] is not None and x["date"] <= r["date"]]
            if not st:
                problems.append(f"{where} no station on or before this date to place it at")
            else:
                lat, lon = st[-1]["lat"], st[-1]["lon"]
        if lat is None:
            continue
        actions.setdefault(r["unit"], []).append(dict(r, lat=round(lat, 4), lon=round(lon, 4)))

    return {"places": places, "units": units, "stations": stations, "actions": actions,
            "routes": list(routes.values()), "problems": problems}


def main():
    built = place(lambda name: read(ARMY / name) if (ARMY / name).exists() else [])
    out = {"units": [dict(u, stations=built["stations"].get(k, []),
                          actions=sorted(built["actions"].get(k, []), key=lambda a: (a["date"], a["time"])))
                     for k, u in built["units"].items()],
           "routes": built["routes"]}
    for msg in built["problems"]:
        print("PROBLEM", msg)
    path = ARMY / "army.json"
    path.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    n = sum(len(u["stations"]) for u in out["units"])
    na = sum(len(u["actions"]) for u in out["units"])
    print(f"wrote {path.relative_to(RECORDS.parent)}: {len(out['units'])} units, {n} stations, "
          f"{na} actions, {len(built['problems'])} problems")
    sys.exit(1 if built["problems"] else 0)


if __name__ == "__main__":
    main()
