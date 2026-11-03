# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
"""Compare a boat's torpedo attacks with the Japanese-side record of the same moments, for checking by eye.

Inputs per patrol (records/boats/<boat>/patrol-N/):
  positions.csv  the boat's attack sheets (source=attack)
  japanese.yml   Japanese-side events, transcribed as written (hand-edited)
  claims.yml     which attack goes with which Japanese record, and how (hand-edited)
  frupac.yml     notes read off the FRUPAC war maps, each tied to an attack (hand-edited)

For each pairing it prints both times in GMT, the difference in minutes, and the distance between the two positions
where both records give one. tools/build_engagement.py reads the same pairings for the engagement pages (`pairs` in
engagement.json) and fails on one that names an attack or a record that doesn't exist; the page's Sources view does this
same arithmetic in the browser (site/engage.js, Engage.apart), tested against Attack 1 and J03 below (5 min, 7.6 nm).

Japanese records are assumed to be in Tokyo time (zone I, -9), the time the Imperial Navy and its convoys kept.
Nittatsu Maru's 0419 I torpedoing against BANG's Attack 4 at 0518 K (one minute apart) supports that. FRUPAC notes
carry no zone letter; they are assumed to repeat the Japanese time (zone I) too. Positions on them are estimates read
off the map, so the distance is rough (a few tenths of a degree).

Usage: uv run tools/check_crossrefs.py [bang/1 | bang | all]   (default all: every patrol with a japanese.yml)
"""
import sys
from datetime import date

import records
from check_track import load, nm, parse_coord, patrol_dir, to_utc


def text(v):
    return v.isoformat() if isinstance(v, date) else str(v or "")


def load_japanese(patrol):
    rows = {}
    for r in records.load_yaml(patrol_dir(patrol) / "japanese.yml") or []:
        r = {k: text(v) for k, v in r.items()}
        r["utc"] = to_utc(r["date"], r["time"], r.get("zone") or "I") if r.get("time") else None
        r["lat"], r["lon"] = parse_coord(r.get("lat_raw", "")), parse_coord(r.get("lon_raw", ""))
        rows[r["id"]] = r
    return rows


def pairs(patrol):
    path = patrol_dir(patrol) / "claims.yml"
    if not path.exists():
        return
    fixes = {}  # patrol -> {ref: fix}; an attack may be another boat's, as "ss-384-parche/1:Attack 2"
    ja = load_japanese(patrol)
    for x in records.load_yaml(path) or []:
        other, _, ref = x["attack"].rpartition(":")
        key = other or patrol
        if key not in fixes:
            fixes[key] = {r["ref"]: r for r in load(key)}
        a, j = fixes[key][ref], ja[x["record"]]
        mins = f"{round((j['utc'] - a['utc']).total_seconds() / 60):+5d} min" if j["utc"] else "        -"
        dist = f"{nm((a['lat'], a['lon']), (j['lat'], j['lon'])):5.1f} nm" if j["lat"] is not None else "       -"
        print(f"{patrol} {x['attack']:<9} {a['utc']:%Y-%m-%dT%H:%MZ}  {j['id']} {j.get('ship', ''):<14} "
              f"{j.get('event', ''):<19} {(format(j['utc'], '%Y-%m-%dT%H:%MZ') if j['utc'] else ''):<17} {mins} {dist}  "
              f"{x['relation']:<9} [{j['source']}]")


def frupac(patrol):
    path = patrol_dir(patrol) / "frupac.yml"
    if not path.exists():
        return
    attacks = {r["ref"]: r for r in load(patrol) if r["source"] == "attack"}
    for f in records.load_yaml(path) or []:
        f = {k: text(v) for k, v in f.items()}
        a = attacks.get(f.get("attack", ""))
        if not a or not f.get("time"):
            continue
        mins = round((to_utc(f["date"], f["time"], "I") - a["utc"]).total_seconds() / 60)
        if abs(mins) > 24 * 60:   # later claims and arrivals, not the attack itself
            continue
        dist = (f"{nm((a['lat'], a['lon']), (float(f['lat_est']), float(f['lon_est']))):5.0f} nm"
                if f.get("lat_est") else "     -")
        print(f"{patrol} {f['attack']:<9} {a['utc']:%Y-%m-%dT%H:%MZ}  {f['id']} {f.get('event', ''):<15} "
              f"{f['date']} {f['time']}(I?) {mins:+6d} min {dist}  {f.get('relation', ''):<9} {f['map']}")


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else "all"
    patrols = [arg] if "/" in arg else [u for u in records.units(None if arg == "all" else arg)
                                         if (patrol_dir(u) / "japanese.yml").exists()]
    for patrol in patrols:
        frupac(patrol)
        pairs(patrol)


if __name__ == "__main__":
    main()
