# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""A run of traced days checked against one another (records/fronts/<map>.geojson): what a day's own checks can't
see, because the side test only asks whether a town is on the side the trace says, not whether the trace is whole.

A day is set beside the days either side of it (the front moves a few kilometres a day at most) and three things are
flagged, each a lead for the reviewer to look at on the overlay, not an error:

  side    a town on a different side from both neighbours: a stretch turned the wrong way, unless the line moved
          past the town that day and back (it rarely does)
  stray   a town nearer the front by more than STRAY km than on both neighbours: heavy ink traced as front that isn't
          (a boundary's stretch whose middle fell outside its box; the side test misses these when the stray ink is
          far behind the line), and the stretch nearest the town is named
  short   a front shorter by more than SHORT per cent than both neighbours: a stretch lost (a box over the front, or
          ink too heavy to trace)

The sides are the page's own test (site/engage.js frontSide, through node), as trace_front.py --sides runs it.

    uv run tools/check_fronts.py 1944-12-16 1945-01-31
"""
import argparse
import csv
import json
import math
import subprocess
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
REC = KIT / "records" / "fronts"
STRAY, SHORT = 15.0, 12.0


def front(day):
    """The day's front runs as [[lon, lat], ...] lists, with their run numbers."""
    g = json.load(open(REC / f"12ag-{day}.geojson", encoding="utf-8"))
    return [(f["properties"].get("run"), f["geometry"]["coordinates"]) for f in g["features"]
            if f["properties"].get("kind") == "front"]


def towns(day):
    return {r["town"]: (float(r["lon"]), float(r["lat"]))
            for r in csv.DictReader(open(REC / f"12ag-{day}-gcps.csv", encoding="utf-8"))}


def nearest(p, runs):
    """The distance in km from p to the front, and the run it is nearest."""
    lon0, lat0 = p
    k = math.cos(math.radians(lat0))
    best = (1e9, None)
    for n, c in runs:
        for a, b in zip(c, c[1:]):
            ax, ay = (a[0] - lon0) * k * 111.3, (a[1] - lat0) * 111.3
            dx, dy = (b[0] - a[0]) * k * 111.3, (b[1] - a[1]) * 111.3
            L = dx * dx + dy * dy
            u = 0.0 if not L else max(0.0, min(1.0, -(ax * dx + ay * dy) / L))
            best = min(best, (math.hypot(ax + u * dx, ay + u * dy), n), key=lambda t: t[0])
    return best


def length_km(runs):
    return sum(math.hypot((b[0] - a[0]) * math.cos(math.radians(a[1])) * 111.3, (b[1] - a[1]) * 111.3)
               for _, c in runs for a, b in zip(c, c[1:]))


def sides(days, pts):
    """{day: {town: -1 own, 1 enemy, 0 nothing tells}} by the page's frontSide, one node call for the run."""
    js = ("const E=require(process.argv[1]);const fs=require('fs');const q=JSON.parse(fs.readFileSync(0,'utf8'));"
          "const out={};for(const [d,runs,towns] of q){out[d]={};for(const [t,p] of Object.entries(towns))"
          "out[d][t]=E.frontSide(runs,p);}console.log(JSON.stringify(out));")
    q = [[d, [c for _, c in front(d)], pts[d]] for d in days]
    r = subprocess.run(["node", "-e", js, str(KIT / "site" / "engage.js")], input=json.dumps(q), capture_output=True,
                       text=True, check=True)
    return json.loads(r.stdout)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("first", help="the run's first day, YYYY-MM-DD")
    ap.add_argument("last", help="its last day")
    a = ap.parse_args()
    days = sorted(p.name[5:15] for p in REC.glob("12ag-*.geojson") if a.first <= p.name[5:15] <= a.last)
    if len(days) < 3:
        sys.exit("fewer than three traced days in that run: nothing to set a day beside")
    pts = {d: towns(d) for d in days}
    side = sides(days, pts)
    runs = {d: front(d) for d in days}
    dist = {d: {t: nearest(p, runs[d]) for t, p in pts[d].items()} for d in days}
    size = {d: length_km(runs[d]) for d in days}
    found = 0
    for i, d in enumerate(days):
        nb = [days[j] for j in (i - 1, i + 1) if 0 <= j < len(days)]
        out = []
        for t in pts[d]:
            if all(t in side[n] and side[n][t] == side[nb[0]][t] != side[d][t] for n in nb) and side[d][t]:
                out.append(f"side   {t}: {'enemy' if side[d][t] > 0 else 'own'} (both neighbours "
                           f"{'enemy' if side[nb[0]][t] > 0 else 'own'})")
            km, run = dist[d][t]
            if all(t in dist[n] and km < dist[n][t][0] - STRAY for n in nb):
                out.append(f"stray  {t}: {km:.0f} km from the front by run {run} "
                           f"(neighbours {', '.join(f'{dist[n][t][0]:.0f}' for n in nb)})")
        if all(size[d] < size[n] * (1 - SHORT / 100) for n in nb):
            out.append(f"short  {size[d]:.0f} km of front (neighbours {', '.join(f'{size[n]:.0f}' for n in nb)})")
        for o in out:
            print(f"12ag-{d}  {o}")
        found += len(out)
    print(f"{len(days)} days, {found} to look at")


if __name__ == "__main__":
    main()
