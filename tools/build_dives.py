# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
"""Bundle depth logs, seafloor samples and track fixes into <boat>/dives.json
for site/dives.html.

Inputs per patrol (records/boats/<boat>/patrol-N/):
  depths.csv     transcribed depth/dive/surface/depth-charge log (times as typed)
  seafloor.csv   ETOPO1 seafloor along the track (tools/fetch_seafloor.py)
  positions.csv  fixes, used to place the boat in time for day/night
  layers.csv     the report's density-layer (bathythermograph) table
  weather.csv    ERA5 hourly weather along the track (tools/fetch_weather.py)
and per boat, dives.yml (hand-edited): background for particular log entries, and the
captain's own sky observations.

Usage: uv run tools/build_dives.py [boat]     (default bang)
"""
import csv
import json
import re
import sys
from datetime import datetime, timedelta

import records
from check_track import ZONES, load
from records import rel

UNTIL = re.compile(r"routine applies until (\d{4}-\d{2}-\d{2})")


def num(v):
    return float(v) if v not in ("", None) else None


def utc(date, time, zone):
    return datetime.strptime(f"{date} {time}", "%Y-%m-%d %H%M") - timedelta(hours=ZONES[zone])


def iso(t):
    return f"{t:%Y-%m-%dT%H:%MZ}"


def build(boat, patrol, notes):
    folder = records.unit_dir(f"{boat}/{patrol}")
    context = {(c["patrol"], str(c["date"]), c["event"]): c["text"] for c in notes.get("context", [])}
    events, routine = [], []
    for r in csv.DictReader(open(folder / "depths.csv")):
        t = utc(r["date"], r["time"], r["zone"])
        if r["event"] == "routine":
            until = UNTIL.search(r["quote"])
            end = utc(until.group(1), "2359", r["zone"]) if until else t + timedelta(hours=12)
            routine.append({"from": iso(t), "to": iso(end), "quote": r["quote"], "page": r["page"]})
            continue
        events.append({
            "utc": iso(t), "local": f"{r['date']} {r['time']}({r['zone']})", "event": r["event"],
            "depth_ft": int(r["depth_ft"]) if r["depth_ft"] else None,
            "charges": int(r["charges"]) if r["charges"] else None,
            "proximity": r["proximity"], "quote": r["quote"], "page": r["page"],
            "context": context.get((patrol, r["date"], r["event"])),
        })
    events.sort(key=lambda e: e["utc"])
    seafloor = [[row["utc"], int(row["seafloor_m"])] for row in csv.DictReader(open(folder / "seafloor.csv"))]
    fixes = [[iso(r["utc"]), round(r["lon"], 3), round(r["lat"], 3)] for r in load(f"{boat}/{patrol}") if r["on_track"] == "yes"]
    layers = []
    for r in csv.DictReader(open(folder / "layers.csv")):
        if not r["time_gct"]:  # summary notes without a time: attach to the day at noon GCT
            r["time_gct"] = "1200"
        t = utc(r["date_fix"] or r["date"], r["time_gct"], "Z")
        layers.append({"utc": iso(t), "iso_ft": num(r["iso_ft"]), "iso_deg": num(r["iso_deg"]),
                       "grad_ft": num(r["grad_ft"]), "grad_deg": num(r["grad_deg"]),
                       "note": r["note"], "page": r["page"]})
    layers.sort(key=lambda l: l["utc"])
    weather = [[w["utc"], num(w["wind_kn"]), num(w["wind_dir"]), num(w["gust_kn"]), num(w["cloud_pct"]),
                num(w["precip_mm"]), num(w["temp_c"]), num(w["pressure_hpa"])]
               for w in csv.DictReader(open(folder / "weather.csv"))]
    sky = [{**n, "utc": iso(utc(n["local"][:10], n["local"][11:15], n["local"][16:-1]))}
           for n in notes.get("sky", []) if n["patrol"] == patrol]
    return {"patrol": patrol, "start": fixes[0][0], "end": fixes[-1][0], "events": events, "routine": routine,
            "seafloor": seafloor, "fixes": fixes, "layers": layers, "weather": weather, "sky": sky}


def main():
    boat = sys.argv[1] if len(sys.argv) > 1 else "bang"
    d = records.vessel_dir(boat)
    notes = records.load_yaml(d / "dives.yml") if (d / "dives.yml").exists() else {}
    patrols = [n for n in records.patrols(boat) if (d / f"patrol-{n}" / "depths.csv").exists()]
    out = {"patrols": [build(boat, p, notes) for p in patrols]}
    path = d / "dives.json"
    json.dump(out, open(path, "w"), separators=(",", ":"))
    for p in out["patrols"]:
        print(f"patrol {p['patrol']}: {len(p['events'])} events, {len(p['layers'])} layer readings, "
              f"{len(p['weather'])} weather hours, {len(p['seafloor'])} seafloor samples")
    print(f"wrote {rel(path)} ({path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
