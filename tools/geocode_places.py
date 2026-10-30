"""Fill in coordinates for a places.csv (records/army/ by default) from OpenStreetMap.

Rows with an empty lat/lon are looked up by their `query` column (town,
region, country) with the Nominatim API, one request a second as its usage
policy asks; answers are cached in sources/geocode/. Rows that already have
coordinates are left alone, so a hand-placed point (a harbour, a camp) is
never overwritten. Every looked-up row gets source "OSM Nominatim" and the
OSM name it matched, so a wrong match is easy to spot.

Nominatim often ranks a commune's administrative boundary first, and a boundary's point is
the middle of the commune, not the town: Venafro's is 2.7 km from the town. So the lookup
asks for five answers and takes the first settlement (a city, town, village or hamlet
node) over a boundary; it falls back to the first answer, and the note says what kind it
matched. `--audit` re-checks rows already looked up this way and lists those whose
point was a boundary's, with the settlement's point and the distance between them; rows whose
note says "Kept (audit ...)" were reviewed and are skipped.

  python3 tools/geocode_places.py                              # records/army/places.csv
  python3 tools/geocode_places.py records/seabees/places.csv   # any other (path from here)
  python3 tools/geocode_places.py --audit [places.csv]         # rows placed on a boundary
"""
import csv
import json
import math
from pathlib import Path
import sys
import time
import urllib.parse
import urllib.request

from records import CACHE, RECORDS  # noqa: E402
PLACES = RECORDS / "army" / "places.csv"
CACHE = CACHE / "geocode"
UA = "wwii-submarine-history/1.0 (family history research; github.com/erichutchins)"


SETTLEMENT = {"city", "town", "village", "hamlet", "suburb", "locality", "isolated_dwelling", "neighbourhood", "quarter"}


def lookup(query):
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / (urllib.parse.quote(query, safe="") + ".5.json")
    if path.exists():
        return json.loads(path.read_text())
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
        {"q": query, "format": "jsonv2", "limit": 5, "accept-language": "en"})
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        hits = json.load(r)
    time.sleep(1.1)
    path.write_text(json.dumps(hits))
    return hits


def best(hits, query=""):
    """The first settlement whose name is the query's first part (so "Bad Brückenau" is the town, not
    Staatsbad Brückenau), else the first settlement, else the first answer."""
    name = query.split(",")[0].strip().lower()
    towns = [h for h in hits if h.get("category") == "place" and h.get("type") in SETTLEMENT]
    for h in towns:
        if h["display_name"].split(",")[0].strip().lower() == name:
            return h
    return towns[0] if towns else hits[0]


def km(a, b):
    dy = (a[0] - b[0]) * 111.2
    dx = (a[1] - b[1]) * 111.2 * math.cos(math.radians(a[0]))
    return math.hypot(dx, dy)


def audit(places):
    with places.open(newline="") as f:
        rows = list(csv.DictReader(f))
    n = 0
    for r in rows:
        if r["source"] != "OSM Nominatim" or not r["query"] or not r["lat"]:
            continue
        if "Kept (audit" in r["note"] or "(not Staatsbad" in r["note"]:   # reviewed: the note says why
            continue
        hits = lookup(r["query"])
        if not hits:
            continue
        b = best(hits, r["query"])
        d = km((float(r["lat"]), float(r["lon"])), (float(b["lat"]), float(b["lon"])))
        if d > 0.3:
            n += 1
            print(f"{r['place']:28} {d:5.1f} km  now {r['lat']},{r['lon']}  {b['type']} {float(b['lat']):.4f},{float(b['lon']):.4f}  {b['display_name'][:50]}")
    print(f"{n} rows more than 0.3 km from the settlement's point")


def main():
    if sys.argv[1:2] == ["--audit"]:
        audit(Path(sys.argv[2]) if len(sys.argv) > 2 else PLACES)
        return
    places = Path(sys.argv[1]) if len(sys.argv) > 1 else PLACES
    with places.open(newline="") as f:
        reader = csv.DictReader(f)
        fields, rows = reader.fieldnames, list(reader)
    for r in rows:
        if r["lat"] and r["lon"]:
            continue
        hits = lookup(r["query"])
        if not hits:
            print(f"NOT FOUND {r['place']!r} ({r['query']})")
            continue
        h = best(hits, r["query"])
        r["lat"], r["lon"] = f"{float(h['lat']):.4f}", f"{float(h['lon']):.4f}"
        r["source"] = "OSM Nominatim"
        r["note"] = r["note"] or f"matched ({h.get('type')}): {h['display_name'][:90]}"
        print(f"{r['place']:28} {r['lat']:>9} {r['lon']:>9}  {h['display_name'][:70]}")
    with places.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
