"""Decode the German Army's reference-point code (Bezugspunkte) in Italy, 1944.

A.O.K. 10's reports give places as block + point: "71 35" is point 35 in block 71 of the
"Bezugspunktkarte 1:100000" (Verm.u.Kart.Abt. (mot) 573), here Sonnino. Each edition
renumbered the blocks; the 4th edition (Arabic block numbers, in use March-May 1944) is
filmed on NARA T-312 roll 90. Points read so far, with their positions, are in
reference/bezugspunkte/ausgabe4.csv; the evidence in anchors.csv (guide: guides/BEZUGSPUNKTE.md).

  python3 tools/bezugspunkt.py decode "71 35"            (also 71/35, 71-35)
  python3 tools/bezugspunkt.py decode "2 km SW 60 22"    offsets: N NO/NE O/E SO/SE S SW W NW,
  python3 tools/bezugspunkt.py decode "2 km südwestl. 60 22"   nördl. südostw. ..., "Nordrand 61 27"
  python3 tools/bezugspunkt.py block 59                  the points read in a block
  python3 tools/bezugspunkt.py check                     anchors.csv: decoded vs expected place
  --edition 4 (default; the only edition read so far)

Accuracy: Section 6 (f0002) is fitted to the map's own printed km grid (Gauss-Krueger, central
meridian 15E, Bessel, scale 1.0, false easting 3,500 km; lines fitted to about 0.1 km), but against
17 independent towns (OSM) a decoded point is off by rms 0.44 km (median 0.34 km): the old 1:100,000
base and the town positions, not the grid. Section 5 (f0003) still uses a fit to towns (rms 0.46 km).
Take a decoded point as good to about 0.4-0.5 km (guide: "Georeferencing").
"""
import csv
import math
import re
import sys

try:
    from records import REFERENCE
except ImportError:  # run from elsewhere
    from pathlib import Path
    REFERENCE = Path(__file__).resolve().parents[1] / "reference"

DATA = REFERENCE / "bezugspunkte"

# bearing in degrees for each direction word (German abbreviations as the reports write them)
DIRS = {
    "n": 0, "nördl": 0, "nordl": 0, "nördlich": 0,
    "no": 45, "ne": 45, "nordostw": 45, "nordöstl": 45, "nordostl": 45,
    "o": 90, "e": 90, "östl": 90, "ostw": 90, "ostl": 90,
    "so": 135, "se": 135, "südostw": 135, "südöstl": 135, "sudostw": 135,
    "s": 180, "südl": 180, "sudl": 180, "südlich": 180,
    "sw": 225, "südwestl": 225, "sudwestl": 225, "südw": 225,
    "w": 270, "westl": 270, "wl": 270,
    "nw": 315, "nordwestl": 315, "nordw": 315,
}
EDGES = {"nordrand": "north", "südrand": "south", "sudrand": "south", "ostrand": "east", "westrand": "west"}


def load(edition="4"):
    pts = {}
    with open(DATA / f"ausgabe{edition}.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            pts.setdefault((r["block"], r["point"]), []).append(r)
    return pts


def offset(lat, lon, km, bearing):
    b = math.radians(bearing)
    return (lat + km * math.cos(b) / 111.2,
            lon + km * math.sin(b) / (111.2 * math.cos(math.radians(lat))))


def parse(text):
    """-> (block, point, km, bearing, edge, words) from '71 35', '2 km SW 60 22', 'Nordrand 61 27'."""
    t = text.strip()
    m = re.search(r"([IVXL]+|\d{1,3})\s*[ /-]\s*(\d{1,3})\s*$", t)
    if not m:
        raise ValueError(f"no block and point in {text!r}")
    block, point, rest = m.group(1), m.group(2), t[:m.start()].strip().lower()
    km = bearing = edge = None
    if rest:
        d = re.match(r"(?:etwa\s+)?([\d.,]+)\s*(km|m)\s+(\S+)", rest)
        if d:
            km = float(d.group(1).replace(",", "."))
            if d.group(2) == "m":
                km /= 1000
            word = d.group(3).rstrip(".").replace("ü", "ü")
            if word not in DIRS:
                raise ValueError(f"direction {d.group(3)!r} not known")
            bearing = DIRS[word]
        else:
            for w, e in EDGES.items():
                if rest.startswith(w):
                    edge = e
            if edge is None:
                raise ValueError(f"can't read the offset {rest!r}")
    return block, point, km, bearing, edge, rest


def decode(text, edition="4"):
    block, point, km, bearing, edge, words = parse(text)
    if re.fullmatch(r"[IVXL]+", block):
        return None, (f"block {block} is in Roman numerals: an earlier edition (Feb 1944), "
                      f"not edition {edition}; no key for it yet")
    rows = load(edition).get((block, point))
    if not rows:
        return None, f"{block} {point}: not read yet in edition {edition}"
    r = rows[0]
    lat, lon = float(r["lat"]), float(r["lon"])
    notes = [f"{block} {point}" + (f" = {r['name_as_printed']}" if r["name_as_printed"] else ""),
             f"{r['section_frame']} px {r['px_x']},{r['px_y']}",
             "reading uncertain" if r["read"] != "read" else "read"]
    if len(rows) > 1:
        notes.append(f"{len(rows)} readings of this number in the block: one is wrong")
    if km is not None:
        lat, lon = offset(lat, lon, km, bearing)
        notes.append(f"plus {km:g} km at {bearing}° ({words})")
    if edge:
        notes.append(f"the {edge} edge of the place at the point (no distance given)")
    return (lat, lon), "; ".join(notes)


def main(argv):
    edition = "4"
    if "--edition" in argv:
        i = argv.index("--edition"); edition = argv[i + 1]; del argv[i:i + 2]
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__); return 0
    cmd = argv[0]
    if cmd == "decode":
        pos, note = decode(" ".join(argv[1:]), edition)
        print(f"{pos[0]:.5f} {pos[1]:.5f}  {note}" if pos else note)
        return 0 if pos else 1
    if cmd == "block":
        for (b, p), rows in sorted(load(edition).items(), key=lambda k: int(k[0][1])):
            if b == argv[1]:
                for r in rows:
                    print(f"{b} {p:>3} {r['lat']:>9} {r['lon']:>9} {r['read']:4} {r['name_as_printed']}")
        return 0
    if cmd == "check":
        with open(DATA / "anchors.csv", encoding="utf-8") as f:
            for a in csv.DictReader(f):
                if not a["expected_lat"]:
                    print(f"{a['code']:10} {a['source']:28} not testable: {a['note']}")
                    continue
                if a["edition"] != edition:
                    print(f"{a['code']:10} edition {a['edition']}: skipped"); continue
                pos, note = decode(a["code"], edition)
                if not pos:
                    print(f"{a['code']:10} {note}"); continue
                la, lo = float(a["expected_lat"]), float(a["expected_lon"])
                err = math.hypot((pos[0] - la) * 111.2, (pos[1] - lo) * 111.2 * math.cos(math.radians(la)))
                print(f"{a['code']:10} {a['place_as_written'][:28]:28} {err:5.2f} km  {a['source']}")
        return 0
    print(__doc__); return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
