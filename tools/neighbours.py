# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Who was beside a unit, and who faced it, day by day, from the 12th Army Group's situation maps.

For a unit and a run of days, each day whose sheet has its symbols read (records/fronts/<map>-units.csv, placed in
<map>.geojson):

  1. the anchor: the unit's own station that day (records/army/army.json, the last station on or before the day), or,
     where it has none, the nearest formation above it (relations.csv `part_of`) with a station or a symbol tied to it
     on the sheet;
  2. every symbol placed within the radius of the anchor, friendly or enemy, with its distance and bearing, and for an
     enemy symbol whether it is across the traced front from the nearest friendly division (an odd number of
     crossings; measured from a friendly symbol, not the anchor, as a unit's own village may lie on the line itself);
  3. the rows of relations.csv in force that day for the unit and the formations above it, and the attachments of a
     command it was under that day (an army group's command left out): what the records say, set apart from what the
     maps suggest.

It ends with each neighbour over the run (the days it was drawn, its nearest and middle distance) and a reading list:
the neighbours with a key in the kit, and where to look for the rest.

Every neighbour is computed, never stored, and a lead: the sheets draw divisions and above (a battalion or a combat
command has no box of its own), each symbol in its unit's area and not at a position, the enemy's as the army group's
intelligence picture, and they can run days behind a move (records/fronts/README.md). Being drawn beside a unit is not
working with it until a record says so.

Usage: uv run tools/neighbours.py 60aib 1944-12-27 1945-01-03 [--radius 20] [--json]
"""
import argparse
import csv
import json
import math
import statistics
import sys
from datetime import date, timedelta

from records import RECORDS

FRONTS = RECORDS / "fronts"
ARMY = RECORDS / "army"
FRIENDLY = {"us", "uk", "ca", "fr", "pl"}
# where a unit with no records in the kit keeps them: the US Army's operations reports, the German records filmed
# at Alexandria (NARA microfilm, by echelon)
LOOK_US = "its after action reports and journals for these days (NARA RG 407, World War II Operations Reports)"
LOOK_DE = {"xx": "its war diary (Kriegstagebuch), NARA microfilm T-315 (German divisions)",
           "x": "its war diary, NARA microfilm T-315 (divisions and brigades) or its parent's",
           "xxx": "its war diary, NARA microfilm T-314 (German corps)",
           "xxxx": "its war diary, NARA microfilm T-312 (armies) or T-313 (panzer armies)"}


def km(a, b):
    """Distance in km between (lon, lat) points: a local equirectangular, good to well under a percent at 30 km."""
    k = math.cos(math.radians((a[1] + b[1]) / 2))
    return math.hypot((a[0] - b[0]) * 111.32 * k, (a[1] - b[1]) * 110.57)


def bearing(a, b):
    k = math.cos(math.radians((a[1] + b[1]) / 2))
    deg = math.degrees(math.atan2((b[0] - a[0]) * k, b[1] - a[1])) % 360
    return "N NE E SE S SW W NW".split()[int((deg + 22.5) // 45) % 8]


def crosses(p, q, a, b):
    """Whether segment pq crosses segment ab (in the lon/lat plane; fine at these distances)."""
    def side(o, s, t):
        return (s[0] - o[0]) * (t[1] - o[1]) - (s[1] - o[1]) * (t[0] - o[0])
    d1, d2, d3, d4 = side(a, b, p), side(a, b, q), side(p, q, a), side(p, q, b)
    return d1 * d2 < 0 and d3 * d4 < 0


def front_crossings(p, q, lines):
    return sum(crosses(p, q, a, b) for ln in lines for a, b in zip(ln, ln[1:]))


def group_key(n):
    """One neighbour across days: its key, or its side, echelon and label without the day's qualifiers (the arm is left
    out, as a reader may give the same box as armored one day and unread the next)."""
    if n["unit"]:
        return n["unit"]
    label = n["label"].replace("?", "").replace("(-)", "").replace("(+)", "").replace("(±)", "").strip()
    return f"{'friendly' if n['friendly'] else n['of']}:{n['echelon']}:{label}"


def load():
    army = json.loads((ARMY / "army.json").read_text(encoding="utf-8"))
    stations = {u["unit"]: sorted((s for s in u.get("stations", []) if s.get("lat") not in (None, "")), key=lambda s: s["date"])
                for u in army["units"]}
    with open(ARMY / "relations.csv", encoding="utf-8", newline="") as f:
        relations = list(csv.DictReader(f))
    with open(ARMY / "units.csv", encoding="utf-8", newline="") as f:
        names = {r["unit"]: r["name"] for r in csv.DictReader(f)}
    names.update({r["other"]: r["other_name"] for r in relations if r["other"] not in names})
    return stations, relations, names


def parents(unit, relations):
    """The formations above a unit, nearest first, by `part_of`."""
    out, seen = [], {unit}
    while True:
        up = [r["other"] for r in relations if r["unit"] == unit and r["relation"] == "part_of" and r["other"] not in seen]
        if not up:
            return out
        unit = up[0]; seen.add(unit); out.append(unit)


def station_on(stations, unit, day):
    rows = [s for s in stations.get(unit, []) if s["date"] <= day]
    return rows[-1] if rows else None


def in_force(r, day):
    return (not r["from"] or r["from"][:10] <= day) and (not r["to"] or day <= r["to"][:10])


def sheet(day):
    """The day's map: its symbols placed (not listed), its front lines, its as_of; None if its symbols aren't read."""
    name = f"12ag-{day}"
    if not (FRONTS / f"{name}-units.csv").exists() or not (FRONTS / f"{name}.geojson").exists():
        return None
    g = json.loads((FRONTS / f"{name}.geojson").read_text(encoding="utf-8"))
    units = [dict(f["properties"], lonlat=tuple(f["geometry"]["coordinates"])) for f in g["features"]
             if f["properties"].get("kind") == "unit" and not f["properties"].get("list")]
    fronts = [[tuple(c) for c in f["geometry"]["coordinates"]] for f in g["features"] if f["properties"].get("kind") == "front"]
    as_of = next((f["properties"].get("as_of") for f in g["features"] if f["properties"].get("as_of")), "")
    return {"name": name, "units": units, "fronts": fronts, "as_of": as_of}


def anchor(unit, day, sh, stations, relations):
    """Where to measure from: the unit's own station, else the nearest formation above it with one, else a symbol tied
    to it or a formation above it on the sheet. Returns (lonlat, words) or (None, why)."""
    for who in [unit] + parents(unit, relations):
        s = station_on(stations, who, day)
        if s:
            return (float(s["lon"]), float(s["lat"])), f"{who}'s station, {s['place'] or s['station']} (from {s['date']}; {s['page']})"
        tied = [u for u in sh["units"] if u.get("unit") == who]
        if tied:
            return tied[0]["lonlat"], f"{who}'s symbol \"{tied[0]['label']}\" on {sh['name']}"
    return None, f"no station for {unit} or a formation above it, and no symbol tied to them on {sh['name']}"


def commands(chain, day, relations):
    """The rows in force on the day for the unit and the formations above it, and one step further: a battalion under a
    combat command (`under_command`) brings the command's own attachments (CC A attached to the 4th Armored)."""
    rows = [r for r in relations if r["unit"] in chain and r["relation"] != "part_of" and in_force(r, day)]
    above = [r["other"] for r in rows if r["relation"] == "under_command"]
    rows += [r for r in relations if r["unit"] in above and r["relation"] != "part_of" and in_force(r, day) and r not in rows]
    return [r for r in rows if not r["other"].endswith("army-group")]


def run(unit, start, end, radius):
    stations, relations, names = load()
    chain = [unit] + parents(unit, relations)
    days, seen = [], {}
    d = start
    while d <= end:
        day = d.isoformat(); d += timedelta(days=1)
        sh = sheet(day)
        if not sh:
            days.append({"day": day, "read": False}); continue
        at, how = anchor(unit, day, sh, stations, relations)
        rec = {"day": day, "read": True, "map": sh["name"], "as_of": sh["as_of"], "anchor": how, "near": [],
               "own": [], "record": commands(chain, day, relations)}
        if at is None:
            days.append(rec); continue
        for u in sh["units"]:
            dist = km(at, u["lonlat"])
            if u.get("unit") in chain:
                rec["own"].append({"label": u["label"], "unit": u["unit"], "km": round(dist, 1), "bearing": bearing(at, u["lonlat"])})
                continue
            if dist > radius:
                continue
            friendly = u["of"] in FRIENDLY
            ref = min((v["lonlat"] for v in sh["units"] if v["of"] in FRIENDLY and v.get("echelon") == "xx"),
                      key=lambda c: km(at, c), default=at)
            n = {"label": u["label"], "unit": u.get("unit") or "", "of": u["of"], "echelon": u.get("echelon", ""),
                 "arm": u.get("arm", ""), "doubt": u.get("doubt", ""), "km": round(dist, 1), "bearing": bearing(at, u["lonlat"]),
                 "across": front_crossings(ref, u["lonlat"], sh["fronts"]) % 2 == 1, "friendly": friendly}
            rec["near"].append(n)
            key = group_key(n)
            s = seen.setdefault(key, {"n": n, "days": [], "km": []})
            s["days"].append(day); s["km"].append(dist)
        rec["near"].sort(key=lambda n: n["km"])
        days.append(rec)
    summary = sorted(({"key": k, "label": v["n"]["label"], "unit": v["n"]["unit"], "of": v["n"]["of"], "echelon": v["n"]["echelon"],
                       "arm": v["n"]["arm"], "friendly": v["n"]["friendly"], "doubt": v["n"]["doubt"], "days": len(v["days"]),
                       "first": v["days"][0], "last": v["days"][-1], "nearest": round(min(v["km"]), 1),
                       "middle": round(statistics.median(v["km"]), 1)} for k, v in seen.items()),
                     key=lambda s: (not s["friendly"], -s["days"], s["middle"]))
    for s in summary:
        s["name"] = names.get(s["unit"], "")
        s["read"] = ("in the kit: " + s["name"]) if s["unit"] in names else ("not in the kit yet: " + (
            LOOK_US if s["friendly"] else LOOK_DE.get(s["echelon"], LOOK_DE["xx"])))
    return {"unit": unit, "name": names.get(unit, unit), "chain": chain, "from": start.isoformat(), "to": end.isoformat(),
            "radius_km": radius, "days": days, "neighbours": summary}


def words(out):
    L = [f"# Beside and facing {out['name']} ({out['unit']}), {out['from']} to {out['to']}, within {out['radius_km']:g} km", "",
         "Computed from the 12th Army Group's situation maps: leads, not records. The sheets draw divisions and above, each "
         "symbol in its unit's area; the enemy's are the army group's intelligence picture; the maps can run days behind a "
         "move. Being drawn beside a unit is not working with it until a record says so.", ""]
    last = None
    for d in out["days"]:
        if not d["read"]:
            L.append(f"## {d['day']}: symbols not read"); L.append(""); continue
        L.append(f"## {d['day']} ({d['map']}, as of {d['as_of']})")
        L.append(f"Measured from {d['anchor']}.")
        for o in d["own"]:
            L.append(f"- its own formation drawn: \"{o['label']}\" ({o['unit']}) {o['km']} km {o['bearing']}")
        rec = [f"{r['unit']} {r['relation'].replace('_', ' ')} {r['other_name']} ({r['from']} - {r['to'] or 'open'}; {r['page']})" for r in d["record"]]
        if rec != last:
            L.append("- on the record (relations.csv): " + ("; ".join(rec) or "no attachment or command in force"))
            last = rec
        fr = [n for n in d["near"] if n["friendly"]]; en = [n for n in d["near"] if not n["friendly"]]
        fmt = lambda n: (f"\"{n['label']}\" {n['arm']} {n['echelon']}{' (' + n['unit'] + ')' if n['unit'] else ''} {n['km']} km {n['bearing']}"
                         + ("" if n["friendly"] else (" across the line" if n["across"] else " not across the traced line"))
                         + (f" [doubt: {n['doubt']}]" if n["doubt"] else ""))
        L.append("- beside it: " + ("; ".join(fmt(n) for n in fr) or "none drawn within the radius"))
        L.append("- facing it: " + ("; ".join(fmt(n) for n in en) or "none drawn within the radius"))
        L.append("")
    L += ["## Over the run", "", "| side | symbol | key | days drawn | nearest km | middle km | to read |", "|---|---|---|---|---|---|---|"]
    for s in out["neighbours"]:
        L.append(f"| {'beside' if s['friendly'] else 'facing'} | \"{s['label']}\" {s['arm']} {s['echelon']} | {s['unit'] or '-'} | "
                 f"{s['days']} ({s['first']} to {s['last']}) | {s['nearest']} | {s['middle']} | {s['read']} |")
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("unit"); ap.add_argument("start"); ap.add_argument("end")
    ap.add_argument("--radius", type=float, default=20.0, help="km round the anchor (default 20)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    out = run(a.unit, date.fromisoformat(a.start), date.fromisoformat(a.end), a.radius)
    if not any(d["read"] for d in out["days"]):
        sys.exit(f"no day from {a.start} to {a.end} has its symbols read (records/fronts/README.md, Known gaps)")
    print(json.dumps(out, ensure_ascii=False, indent=1) if a.json else words(out))


if __name__ == "__main__":
    main()
