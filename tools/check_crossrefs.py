# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
"""Compare a boat's torpedo attacks with the Japanese-side record of the same moments.

Inputs per patrol (records/boats/<boat>/patrol-N/):
  positions.csv  the boat's attack sheets (source=attack)
  japanese.csv   Japanese-side events, transcribed as written (hand-edited)
  crossrefs.csv  which attack goes with which Japanese event (hand-edited)
  frupac.csv     notes read off the FRUPAC war maps, each tied to an attack (hand-edited)

For each pair it prints both times in GMT, the difference in minutes, and the
distance between the two positions where both records give one, then writes
patrol-N/crossrefs.json for the pages.

Japanese records are assumed to be in Tokyo time (zone I, -9), the time the
Imperial Navy and its convoys kept. Nittatsu Maru's 0419 I torpedoing against
BANG's Attack 4 at 0518 K (one minute apart) supports that. FRUPAC notes carry
no zone letter; they are assumed to repeat the Japanese time (zone I) too.
FRUPAC rows are printed for checking only; positions on them are estimates read
off the map, so the distance is rough (a few tenths of a degree).

Usage: uv run tools/check_crossrefs.py [bang/1 | bang | all]   (default all: every patrol with a japanese.csv)
"""
import csv
import json
import sys

import records
from check_track import load, nm, parse_coord, patrol_dir, to_utc

JACAR = "https://www.jacar.archives.go.jp/das/image/"
COMBINEDFLEET = "https://www.combinedfleet.com/"


def source_url(source):
    kind, ref = source.split(":", 1)
    return JACAR + ref if kind == "jacar" else COMBINEDFLEET + ref + ".htm"


def load_japanese(patrol):
    rows = {}
    for r in csv.DictReader(open(patrol_dir(patrol) / "japanese.csv", encoding="utf-8")):
        r["utc"] = to_utc(r["date"], r["time"], r["zone"]) if r["time"] else None
        r["lat"], r["lon"] = parse_coord(r["lat_raw"]), parse_coord(r["lon_raw"])
        r["url"] = source_url(r["source"])
        rows[r["id"]] = r
    return rows


def build(patrol):
    path = patrol_dir(patrol) / "crossrefs.csv"
    if not path.exists():
        return None
    fixes = {}  # patrol id -> {ref: fix}; an attack may be another boat's, as "ss-384-parche/1:Attack 2"
    ja = load_japanese(patrol)
    out = []
    for x in csv.DictReader(open(path, encoding="utf-8")):
        other, _, ref = x["attack"].rpartition(":")
        key = other or patrol
        if key not in fixes:
            fixes[key] = {r["ref"]: r for r in load(key)}
        a, j = fixes[key][ref], ja[x["ja_id"]]
        minutes = round((j["utc"] - a["utc"]).total_seconds() / 60) if j["utc"] else None
        dist = round(nm((a["lat"], a["lon"]), (j["lat"], j["lon"])), 1) if j["lat"] is not None else None
        out.append({
            "attack": x["attack"], "boat": other or patrol_dir(patrol).parent.name, "relation": x["relation"], "note": x["note"],
            "submarine": {"utc": f"{a['utc']:%Y-%m-%dT%H:%MZ}", "local": f"{a['date']} {a['time']}({a['zone']})",
                     "lat_raw": a["lat_raw"], "lon_raw": a["lon_raw"], "page": a["page"]},
            "japanese": {"id": j["id"], "ship": j["ship"], "convoy": j["convoy"], "event": j["event"],
                         "utc": f"{j['utc']:%Y-%m-%dT%H:%MZ}" if j["utc"] else None,
                         "local": f"{j['date']} {j['time']}({j['zone']})" if j["time"] else j["date"],
                         "lat_raw": j["lat_raw"], "lon_raw": j["lon_raw"],
                         "original": j["original"], "translation": j["translation"],
                         "source": j["source"], "page": j["page"], "url": j["url"]},
            "minutes_apart": minutes, "nm_apart": dist,
        })
    return out


def frupac(patrol):
    path = patrol_dir(patrol) / "frupac.csv"
    if not path.exists():
        return
    attacks = {r["ref"]: r for r in load(patrol) if r["source"] == "attack"}
    for f in csv.DictReader(open(path, encoding="utf-8")):
        a = attacks.get(f["attack"])
        if not a or not f["time"]:
            continue
        mins = round((to_utc(f["date"], f["time"], "I") - a["utc"]).total_seconds() / 60)
        if abs(mins) > 24 * 60:   # later claims and arrivals, not the attack itself
            continue
        dist = (f"{nm((a['lat'], a['lon']), (float(f['lat_est']), float(f['lon_est']))):5.0f} nm"
                if f["lat_est"] else "     -")
        print(f"{patrol} {f['attack']:<9} {a['utc']:%Y-%m-%dT%H:%MZ}  {f['id']} {f['event']:<15} "
              f"{f['date']} {f['time']}(I?) {mins:+6d} min {dist}  {f['relation']:<9} {f['map']}")


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else "all"
    patrols = [arg] if "/" in arg else [u for u in records.units(None if arg == "all" else arg)
                                         if (patrol_dir(u) / "japanese.csv").exists()]
    for patrol in patrols:
        frupac(patrol)
        rows = build(patrol)
        if rows is None:
            continue
        for r in rows:
            b, j = r["submarine"], r["japanese"]
            mins = f"{r['minutes_apart']:+5d} min" if r["minutes_apart"] is not None else "        -"
            dist = f"{r['nm_apart']:5.1f} nm" if r["nm_apart"] is not None else "       -"
            print(f"{patrol} {r['attack']:<9} {b['utc']}  {j['id']} {j['ship']:<14} {j['event']:<19} "
                  f"{j['utc'] or '':<17} {mins} {dist}  [{j['source']}]")
        out = patrol_dir(patrol) / "crossrefs.json"
        json.dump(rows, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        print(f"wrote {records.rel(out)} ({len(rows)} links)")


if __name__ == "__main__":
    main()
