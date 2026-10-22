# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
"""Sanity-check a track transcribed from a war patrol report or a war diary.

Reads a patrol's positions.csv (records/boats/<boat>/patrol-N/) or a ship's
(records/ships/<ship>/), converts every fix to UTC, sorts them, and flags legs whose
implied speed exceeds what the vessel could make (max_kts in its ship.yml).

Corrections for typos in the original report go in the lat_fix / lon_fix /
date_fix / time_fix columns (raw values are kept as typed). Rows with on_track=no are
kept as map points but left off the track line: ship contacts (which report
the target's position) and fixes that contradict their neighbours. Rows
missing a time or a coordinate are kept in the CSV but skipped here.

In a ship's single war-diary record, a row with no coordinates at all (blank
lat_raw/lon_raw/lat_fix/lon_fix) is a logged event with a time but no position
of its own. It is placed on the track
by interpolating between the on-track fixes either side, marked `assumed`,
and kept off the track line.

Usage: uv run tools/check_track.py bang/1 [--geojson] [-q]     one patrol
       uv run tools/check_track.py bang --geojson               every patrol of a boat
       uv run tools/check_track.py haynsworth --geojson         a ship's war diary
       uv run tools/check_track.py all --geojson                every boat and ship

--geojson writes each track.geojson, each boat's tracks.geojson (all its patrols, for the
map page) and records/ships.json (every ship.yml, for the pages).
"""
import csv
import json
import math
import sys
from datetime import datetime, timedelta
import records
from records import RECORDS, rel, unit_dir

# Zone letter -> hours ahead of GMT (K = -10 in the reports' "zone" notation).
# KL and IK are the half-hour zones between K and L, and I and K (GROWLER's Patrol 9 report).
# L, LM, V, UV, WX and XY are the Haynsworth war diary's zones (Ulithi to Hawaii, half-hour zones included).
# A and N to R are the Atlantic's (SOLAR's war diaries type no zone; her rows carry the zone of their longitude).
ZONES = {"A": 1, "Z": 0, "N": -1, "O": -2, "P": -3, "Q": -4, "R": -5, "M": 12, "LM": 11.5, "L": 11, "KL": 10.5, "K": 10, "IK": 9.5, "I": 9, "H": 8, "UV": -8.5, "V": -9, "VW": -9.5,
         "W": -10, "WX": -10.5, "X": -11, "XY": -11.5, "Y": -12}
DR_TOL = 30     # nm of dead-reckoning disagreement allowed between fixes


def parse_coord(s):
    """'26-42.5N' -> 26.708, '157-58W' -> -157.967"""
    if not s or "?" in s:  # blank, or illegible in the scan
        return None
    hemi = s[-1]
    deg, minutes = s[:-1].split("-")
    v = int(deg) + float(minutes) / 60
    return -v if hemi in "SW" else v


def to_utc(date, time, zone):
    local = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H%M")
    return local - timedelta(hours=ZONES[zone])


def nm(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    d = math.acos(min(1, math.sin(lat1) * math.sin(lat2)
                      + math.cos(lat1) * math.cos(lat2) * math.cos(lon2 - lon1)))
    return math.degrees(d) * 60


def single(unit):
    """A ship's single war-diary record ('haynsworth'), not a boat's patrol ('bang/1')."""
    return "/" not in str(unit)


def period(unit):
    """number the map page files this track under: the patrol, or 1 for a ship's single record"""
    return 1 if single(unit) else int(str(unit).split("/")[-1])


folder = patrol_dir = unit_dir  # the names check_crossrefs.py and build_battle.py import


def fmt_coord(v, hemis):
    """26.95 -> '26-57N'"""
    minutes = round(abs(v) * 60)
    return f"{minutes // 60:02d}-{minutes % 60:02d}{hemis[v < 0]}"


def interpolate(a, b, f):
    """Point a fraction f of the way along the great circle from a to b (lat, lon in degrees)."""
    p1, l1, p2, l2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    d = math.acos(min(1, math.sin(p1) * math.sin(p2) + math.cos(p1) * math.cos(p2) * math.cos(l2 - l1)))
    if d < 1e-9:
        return a
    k1, k2 = math.sin((1 - f) * d) / math.sin(d), math.sin(f * d) / math.sin(d)
    x = k1 * math.cos(p1) * math.cos(l1) + k2 * math.cos(p2) * math.cos(l2)
    y = k1 * math.cos(p1) * math.sin(l1) + k2 * math.cos(p2) * math.sin(l2)
    z = k1 * math.sin(p1) + k2 * math.sin(p2)
    return math.degrees(math.atan2(z, math.hypot(x, y))), math.degrees(math.atan2(y, x))


def place_events(events, rows):
    """Give each coordinate-less event a position interpolated along the on-track fixes."""
    fixes = [r for r in rows if r["on_track"] == "yes"]
    for r in events:
        i = max(0, min(sum(f["utc"] <= r["utc"] for f in fixes), len(fixes) - 1))
        a, b = fixes[max(0, i - 1)], fixes[i]
        span = (b["utc"] - a["utc"]).total_seconds()
        f = min(1, max(0, (r["utc"] - a["utc"]).total_seconds() / span)) if span else 0
        r["lat"], r["lon"] = interpolate((a["lat"], a["lon"]), (b["lat"], b["lon"]), f)
        r["lat_raw"], r["lon_raw"] = "~" + fmt_coord(r["lat"], "NS"), "~" + fmt_coord(r["lon"], "EW")
        r["assumed"] = True
        note = f"position assumed: interpolated between the {a['utc']:%d %b %H%M}Z and {b['utc']:%d %b %H%M}Z fixes"
        r["fix_note"] = f"{r['fix_note']}; {note}" if r["fix_note"] else note
        rows.append(r)


def load(unit):
    """Usable fixes (time and both coordinates present), sorted by UTC."""
    rows, events = [], []
    for r in csv.DictReader(open(folder(unit) / "positions.csv")):
        if not r["time"]:
            continue
        r["utc"] = to_utc(r["date_fix"] or r["date"], r["time_fix"] or r["time"], r["zone"])
        r["lat"] = parse_coord(r["lat_fix"] or r["lat_raw"])
        r["lon"] = parse_coord(r.get("lon_fix") or r["lon_raw"])
        if r["lat"] is not None and r["lon"] is not None:
            rows.append(r)
        elif single(unit) and not (r["lat_raw"] or r["lon_raw"] or r["lat_fix"] or r["lon_fix"]):
            events.append(r)   # (BANG's own coordinate-less rows, e.g. "enter area", stay unplaced)
    rows.sort(key=lambda r: r["utc"])
    place_events(events, rows)
    return sorted(rows, key=lambda r: r["utc"])


def write_geojson(unit, rows):
    """Track as a LineString of own-ship fixes, plus every fix as a Point."""
    track = [r for r in rows if r["on_track"] == "yes"]
    features = [{
        "type": "Feature",
        "properties": {"kind": "track", "patrol": period(unit),
                       "start": f"{track[0]['utc']:%Y-%m-%dT%H:%MZ}", "end": f"{track[-1]['utc']:%Y-%m-%dT%H:%MZ}"},
        "geometry": {"type": "LineString",
                     "coordinates": [[round(r["lon"], 4), round(r["lat"], 4)] for r in track]},
    }]
    for r in rows:
        features.append({
            "type": "Feature",
            "properties": {"kind": r["source"], "ref": r["ref"], "patrol": period(unit),
                           "on_track": r["on_track"] == "yes", "utc": f"{r['utc']:%Y-%m-%dT%H:%MZ}",
                           "lat_raw": r["lat_fix"] or r["lat_raw"], "lon_raw": r.get("lon_fix") or r["lon_raw"],
                           # the position as the page typed it, where lat_fix/lon_fix corrected it
                           **({"typed": f"{r['lat_raw']} {r['lon_raw']}"} if r["lat_fix"] or r.get("lon_fix") else {}),
                           "local": f"{r['date_fix'] or r['date']} {r['time_fix'] or r['time']}({r['zone']})",
                           "page": r["page"], "note": r["note"], "fix": r["fix_note"],
                           **({"assumed": True} if r.get("assumed") else {})},
            "geometry": {"type": "Point", "coordinates": [round(r["lon"], 4), round(r["lat"], 4)]},
        })
    out = folder(unit) / "track.geojson"
    json.dump({"type": "FeatureCollection", "features": features}, open(out, "w"), indent=1)
    print(f"wrote {rel(out)} ({len(track)} track points, {len(rows)} fixes)")


def check(unit, verbose=True):
    """Print each track leg; return the number of legs too long to sail in the time."""
    max_kts = records.ship(str(unit).split("/")[0])["max_kts"]
    rows = [r for r in load(unit) if r["on_track"] == "yes"]
    bad, prev = 0, None
    for r in rows:
        flag, leg = "", ""
        if prev:
            hours = (r["utc"] - prev["utc"]).total_seconds() / 3600
            dist = nm((prev["lat"], prev["lon"]), (r["lat"], r["lon"]))
            kts = dist / hours if hours else float("inf")
            leg = f"{dist:6.0f} nm {kts:5.1f} kt"
            if dist > max_kts * hours + DR_TOL:
                flag, bad = "  <-- TOO FAST", bad + 1
        if verbose or flag:
            print(f"{r['utc']:%m-%d %H%MZ} {r['ref']:<14} {r['lat_raw']:>9} {r['lon_raw']:>10}  {leg:>20}{flag}  {r['note'][:40]}")
        prev = r
    return bad


def write_boat_tracks(key):
    """A boat's tracks.geojson: every patrol's track.geojson in one file, for the map page."""
    d = records.vessel_dir(key)
    features = []
    for n in records.patrols(key):
        features += json.load(open(d / f"patrol-{n}" / "track.geojson"))["features"]
    records.write_json(d / "tracks.geojson", {"type": "FeatureCollection", "features": features})
    print(f"wrote {rel(d / 'tracks.geojson')} ({len(features)} features)")


def write_ships_json():
    """records/ships.json: every ship.yml, with the track file the map page loads (none for a ship
    with no positions yet, which the map pages leave out)."""
    out = []
    for d in records.vessels():
        y = records.load_yaml(d / "ship.yml")
        geojson = d / ("tracks.geojson" if records.patrols(d.name) else "track.geojson")
        out.append({"key": d.name, "alias": y["name"].lower(), **{k: v for k, v in y.items() if k != "map"},
                    "geojson": str(geojson.relative_to(RECORDS)) if geojson.exists() else None, **y.get("map", {})})
    records.write_json(RECORDS / "ships.json", out, indent=1, ensure_ascii=False)
    print(f"wrote {rel(RECORDS / 'ships.json')} ({len(out)} ships)")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    arg = args[0] if args else "all"
    units = records.units(None if arg == "all" else arg) if "/" not in arg else [arg]
    for unit in units:
        if "--geojson" in sys.argv:
            write_geojson(unit, load(unit))
        bad = check(unit, verbose="-q" not in sys.argv and len(units) == 1)
        print(f"{unit}: {bad} too-fast legs")
    if "--geojson" in sys.argv:
        for key in dict.fromkeys(u.split("/")[0] for u in units if not single(u)):
            write_boat_tracks(key)
        write_ships_json()


if __name__ == "__main__":
    main()
