# /// script
# requires-python = ">=3.10,<3.14"
# dependencies = ["numpy", "scipy", "pillow", "scikit-image", "pyyaml"]
# ///
"""The towns of a whole base sheet (records/fronts/towns-<base>.csv): the step before any day of a base is traced
across the sheet rather than in the corner the first towns surround (guides/SITUATION-MAPS.md, section 5, B).

    uv run tools/sheet_towns.py crops B11 candidates.csv [--with readings.txt]   # a numbered, gridded crop of the sheet round each candidate, to read
    uv run tools/sheet_towns.py crops B13 --graticule [--step 1] --with seeds.txt   # the same round each whole-degree graticule crossing
    uv run tools/sheet_towns.py accept B11 readings.txt      # the rings or crossings read on them -> records/fronts/towns-B11.csv

`crops`: the base's record in records/fronts/bases.yml names the day whose scan the towns are read on (`towns_on`) and
whose towns, read by eye, seed the fit. The sheet is a conformal conic, and a conic fitted to twenty towns in one
corner (trace_front.Conic) puts a town at the far edge within about 40 px of its ring. So for every candidate
(`town,query`; the query geocoded with OSM Nominatim as records/army/places.csv is, one request a second, cached), the
fit predicts its place (`--with`: readings already made, in `accept`'s form, join the seeds, so the predictions
tighten from about 40 px to about 10 as towns across the sheet are read), and the tool crops the sheet round it (160 px square at 3x, a grid every 20 px with the scan's
coordinates on the edges, a blue cross at the prediction), 16 crops a sheet, into sources/fronts-work/bases/
(<base>-crops-N.jpg, and <base>-candidates.csv with each candidate's number, prediction and coordinates). A reader finds
the town's ring (a ring for a town, a ring with a dot for a city; its name printed beside it) and reads the ring's
centre off the grid, to a few pixels, which is how the first twenty were read. Finding the ring by machine was tried
first (a ring template, matched near the prediction) and lost to the letters' bowls and the road junctions round a
city; a reader does it at a glance. `accept`: the readings, one a line (`12 2037,3966`; `12 none` for a town the sheet
draws as an area, or not at all; a later line for the same number replaces an earlier one, so a second look (`crops
--with readings.txt --only 12,27`, whose predictions are then good to about 10 px) is appended to the file), with the seeds, into records/fronts/towns-<base>.csv (`read` says which), and the
conic fit's residuals, the towns that disagree most first, for a second look.

Better than towns: **the sheet's graticule**. The 1:1,000,000 sheets print a meridian and a parallel every degree, and
a crossing is an exact control point with no geocoder's centroid and no name to match. `crops --graticule` makes the
candidates itself, every crossing (at `--step` degrees) the fit puts on the sheet, named `7E 50N`, and labels each crop
with the name rather than a number (the numbering changes as the fit moves crossings on and off the sheet; a name
doesn't); the reader reads the crossing of the two thin lines and writes `7E 50N x,y`. A new base has no fit to start from: its seeds are three or four crossings read by eye
on the sheet's margins, where the degrees are printed, given in the readings file as `7E 50N 693,5750` (the crossing
named, then its x,y), and `--with seeds.txt` builds the first fit from them (the cone constant the Europe sheets'
usual, which the whole sheet's crossings then refine). The 1:1,000,000 plate's towns-B11.csv was read from towns
before this was seen; the sheet's crossings agreed with that fit within 10 px.
"""
import argparse
import csv
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
import geocode_places
import records
import trace_front as tf

OUT = tf.KIT / "sources" / "fronts-work" / "bases"
HALF = 80      # the crop's half-size on the scan, px
SCALE = 3
GRID = 20      # the grid's spacing on the scan, px
PER, COLS = 16, 4


def base_record(base):
    for b in records.load_yaml(tf.REC / "bases.yml"):
        if b["base"] == base:
            return b
    sys.exit(f"no {base} in records/fronts/bases.yml")


def geocode(cands):
    for c in cands:
        if c.get("lat") and c.get("lon"):
            continue
        hit = geocode_places.best(geocode_places.lookup(c["query"]), c["query"])
        c["lat"], c["lon"] = f"{float(hit['lat']):.4f}", f"{float(hit['lon']):.4f}"
        c["osm"] = hit["display_name"].split(",")[0].strip()
        c["source"] = "OSM Nominatim"
    return cands


def crop(rgb, X, Y, label):
    """The sheet round (X, Y) at SCALE, gridded every GRID px with the scan's coordinates on its edges."""
    x0, y0 = X - HALF, Y - HALF
    tile = Image.fromarray(rgb[y0:y0 + 2 * HALF, x0:x0 + 2 * HALF]).resize((2 * HALF * SCALE, 2 * HALF * SCALE), Image.Resampling.LANCZOS)
    d = ImageDraw.Draw(tile)
    for v in range((x0 // GRID + 1) * GRID, x0 + 2 * HALF, GRID):
        d.line([((v - x0) * SCALE, 0), ((v - x0) * SCALE, 2 * HALF * SCALE)], fill=(255, 60, 60), width=1)
        d.text(((v - x0) * SCALE + 2, 12), str(v), fill=(200, 0, 0))
    for v in range((y0 // GRID + 1) * GRID, y0 + 2 * HALF, GRID):
        d.line([(0, (v - y0) * SCALE), (2 * HALF * SCALE, (v - y0) * SCALE)], fill=(255, 60, 60), width=1)
        d.text((2, (v - y0) * SCALE + 2), str(v), fill=(200, 0, 0))
    c = HALF * SCALE
    d.line([(c - 12, c), (c + 12, c)], fill=(0, 90, 255), width=2); d.line([(c, c - 12), (c, c + 12)], fill=(0, 90, 255), width=2)
    d.rectangle([0, 0, 2 * HALF * SCALE, 11], fill=(255, 255, 255))
    d.text((3, 0), label, fill=(0, 0, 0))
    return tile


def cmd_crops(a):
    b = base_record(a.base)
    on = b.get("towns_on") or b["towns"]
    M = tf.sitmap(on)
    scan = tf.CACHE / M.scan
    if not scan.exists():
        sys.exit(f"no scan of {on} at {scan}: loc_sitmaps.py fetch {M.date}")
    seeds = list(csv.DictReader(open(tf.REC / f"{on}-gcps.csv"))) if (tf.REC / f"{on}-gcps.csv").exists() else []
    cands = [] if a.graticule else geocode(list(csv.DictReader(open(a.candidates))))
    prev = {r["n"]: r for r in csv.DictReader(open(OUT / f"{a.base}-candidates.csv"))} if (OUT / f"{a.base}-candidates.csv").exists() else {}
    for path in a.with_ or []:
        for v in readings(path):
            if v[1] == "none":
                continue
            x, y = v[1].split(",")
            if CROSSING.fullmatch(v[0]):
                lon, lat = crossing_ll(v[0])
                seeds.append({"town": v[0], "x": x, "y": y, "lat": f"{lat}", "lon": f"{lon}"})
            else:   # a number: of the last run's candidates (sheet_towns.py crops numbers them anew each run)
                c = prev[v[0]] if v[0] in prev else cands[int(v[0]) - 1]
                seeds.append({"town": c["town"], "x": x, "y": y, "lat": c["lat"], "lon": c["lon"]})
    if len(seeds) < 3:
        sys.exit(f"{on} has no towns yet: read three or four graticule crossings by eye on the sheet's margins and give "
                 f"them with --with (`7E 50N 693,5750` a line)")
    rgb = np.asarray(Image.open(scan).convert("RGB"))
    H, W = rgb.shape[:2]
    fit = tf.Conic(seeds)
    if a.graticule:
        # every crossing the fit puts on the sheet, by rows from the north-west
        ll = fit.to_ll([[0, 0], [W, 0], [0, H], [W, H]])
        lons = np.arange(np.floor(ll[:, 0].min() / a.step) * a.step, ll[:, 0].max() + a.step, a.step)
        lats = np.arange(np.ceil(ll[:, 1].max() / a.step) * a.step, ll[:, 1].min() - a.step, -a.step)
        for lat in lats:
            for lon in lons:
                X, Y = fit.to_px([[lon, lat]])[0]
                if 0 <= X < W and 0 <= Y < H:
                    name = f"{abs(lon):g}{'W' if lon < 0 else 'E'} {abs(lat):g}{'S' if lat < 0 else 'N'}"
                    cands.append({"town": name, "lat": f"{lat:g}", "lon": f"{lon:g}", "source": f"loc-12ag/{M.item}", "query": "", "osm": ""})
    corners = fit.to_ll([[0, 0], [W, 0], [0, H], [W, H]])
    print(f"{on}: {len(seeds)} towns seed the conic (rms {fit.rms_px:.1f} px); the sheet's corners by it: "
          + ", ".join(f"{lon:.1f}E {lat:.1f}N" for lon, lat in corners))
    OUT.mkdir(parents=True, exist_ok=True)
    tiles, rows = [], []
    for i, c in enumerate(cands, 1):
        X, Y = (int(round(v)) for v in fit.to_px([[float(c["lon"]), float(c["lat"])]])[0])
        on_sheet = HALF <= X < W - HALF and HALF <= Y < H - HALF
        rows.append([i, c["town"], X if on_sheet else "", Y if on_sheet else "", c["lat"], c["lon"], c.get("source", ""), c["query"], c.get("osm", "")])
        if on_sheet and (not a.only or i in a.only):
            tiles.append(crop(rgb, X, Y, c["town"] if a.graticule else f"{i} {c['town']}"))
    with open(OUT / f"{a.base}-candidates.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["n", "town", "pred_x", "pred_y", "lat", "lon", "source", "query", "osm"])
        w.writerows(rows)
    T = 2 * HALF * SCALE
    for s in range(0, len(tiles), PER):
        page = tiles[s:s + PER]
        sheet = Image.new("RGB", (T * COLS, T * ((len(page) + COLS - 1) // COLS)), "white")
        for k, tile in enumerate(page):
            sheet.paste(tile, ((k % COLS) * T, (k // COLS) * T))
        sheet.save(OUT / f"{a.base}-crops-{s // PER + 1}.jpg", quality=85)
    print(f"{len(tiles)} of {len(cands)} candidates on the sheet; wrote {OUT / (a.base + '-candidates.csv')} and "
          f"{(len(tiles) + PER - 1) // PER} sheets {a.base}-crops-N.jpg ({PER} crops each, numbered as the CSV)")


def readings(path):
    """The readings file: `n x,y` or `n none` a line, or a graticule crossing named by its degrees, `7E 50N x,y`
    (a seed on a new sheet); after a `#` a comment; a later line for the same n (a second look) replaces the earlier."""
    out = {}
    for ln in Path(path).read_text().splitlines():
        v = ln.split("#")[0].split()
        if len(v) >= 3 and CROSSING.fullmatch(f"{v[0]} {v[1]}"):
            v = [f"{v[0]} {v[1]}", *v[2:]]
        if len(v) >= 2:
            out[v[0]] = v
    return list(out.values())


CROSSING = re.compile(r"(\d+(?:\.\d+)?)([EW]) (\d+(?:\.\d+)?)([NS])")


def crossing_ll(name):
    """`7E 50N` -> (7.0, 50.0); `0.5W 48.5N` -> (-0.5, 48.5)."""
    m = CROSSING.fullmatch(name)
    if m is None:
        raise ValueError(f"not a crossing's name: {name!r} (7E 50N)")
    lon, lat = float(m.group(1)), float(m.group(3))
    return (-lon if m.group(2) == "W" else lon), (-lat if m.group(4) == "S" else lat)


def cmd_accept(a):
    b = base_record(a.base)
    on = b.get("towns_on") or b["towns"]
    seeds = list(csv.DictReader(open(tf.REC / f"{on}-gcps.csv"))) if (tf.REC / f"{on}-gcps.csv").exists() else []
    cands = {r["n"]: r for r in csv.DictReader(open(OUT / f"{a.base}-candidates.csv"))}
    item = tf.sitmap(on).item
    out = [{**r, "on": on} for r in seeds]
    for v in readings(a.readings):
        if v[1] == "none":
            continue
        x, y = v[1].split(",")
        if CROSSING.fullmatch(v[0]):   # a crossing read by eye on the sheet's margin, named
            lon, lat = crossing_ll(v[0])
            out.append({"town": v[0], "x": x, "y": y, "read": "graticule crossing read by eye on the sheet's margin", "lat": f"{lat:g}", "lon": f"{lon:g}",
                        "source": f"loc-12ag/{item}", "query": "", "on": on})
            continue
        c = cands[v[0]]
        what = "graticule crossing" if CROSSING.fullmatch(c["town"]) else "ring"
        out.append({"town": c["town"], "x": x, "y": y, "read": f"{what} read by eye on a crop round the conic's prediction", "lat": c["lat"], "lon": c["lon"],
                    "source": c["source"], "query": c["query"], "on": on})
    path = tf.REC / f"towns-{a.base}.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, ["town", "x", "y", "read", "lat", "lon", "source", "query", "on"], lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        w.writerows(out)
    if len(out) < 4:
        sys.exit(f"wrote {path}: {len(out)} points, too few to fit")
    fit = tf.make_fit(out)
    res, loo = fit.residuals_km()
    print(f"wrote {path}: {len(out)} towns ({len(seeds)} seeds, {len(out) - len(seeds)} read); conic n {getattr(fit, 'n', 0):.3f}, "
          f"rms {np.sqrt((res ** 2).mean()):.2f} km, leave-one-out rms {np.sqrt((loo ** 2).mean()):.2f} km, worst {loo.max():.1f} km ({fit.names[int(loo.argmax())]})")
    print("the towns that disagree most (look again at any over 1.5 km):")
    for n, r, lo in sorted(zip(fit.names, res, loo), key=lambda t: -t[2])[:10]:
        print(f"   {n:22s} {r:4.1f} km (left out: {lo:4.1f} km)")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("crops"); p.add_argument("base"); p.add_argument("candidates", nargs="?", help="town,query a line (not with --graticule)")
    p.add_argument("--graticule", action="store_true", help="the candidates are the sheet's graticule crossings")
    p.add_argument("--step", type=float, default=1.0, help="the graticule's spacing, degrees")
    p.add_argument("--with", dest="with_", action="append", help="readings already made (accept's form): they join the seeds for the predictions; may repeat")
    p.add_argument("--only", type=lambda v: {int(x) for x in v.split(",")}, help="crop only these candidates (numbers), for a second look")
    p.set_defaults(fn=cmd_crops)
    p = sub.add_parser("accept"); p.add_argument("base"); p.add_argument("readings"); p.set_defaults(fn=cmd_accept)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
