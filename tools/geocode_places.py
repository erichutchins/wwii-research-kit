"""Fill in coordinates for records/army/places.csv from OpenStreetMap.

Rows with an empty lat/lon are looked up by their `query` column (town,
region, country) with the Nominatim API, one request a second as its usage
policy asks; answers are cached in sources/geocode/. Rows that already have
coordinates are left alone, so a hand-placed point (a harbour, a camp) is
never overwritten. Every looked-up row gets source "OSM Nominatim" and the
OSM name it matched, so a wrong match is easy to spot.

  python3 tools/geocode_places.py
"""
import csv
import json
import time
import urllib.parse
import urllib.request

from records import CACHE, RECORDS  # noqa: E402
PLACES = RECORDS / "army" / "places.csv"
CACHE = CACHE / "geocode"
UA = "wwii-submarine-history/1.0 (family history research; github.com/erichutchins)"


def lookup(query):
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / (urllib.parse.quote(query, safe="") + ".json")
    if path.exists():
        return json.loads(path.read_text())
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
        {"q": query, "format": "jsonv2", "limit": 1, "accept-language": "en"})
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        hits = json.load(r)
    time.sleep(1.1)
    path.write_text(json.dumps(hits))
    return hits


def main():
    with PLACES.open(newline="") as f:
        reader = csv.DictReader(f)
        fields, rows = reader.fieldnames, list(reader)
    for r in rows:
        if r["lat"] and r["lon"]:
            continue
        hits = lookup(r["query"])
        if not hits:
            print(f"NOT FOUND {r['place']!r} ({r['query']})")
            continue
        h = hits[0]
        r["lat"], r["lon"] = f"{float(h['lat']):.4f}", f"{float(h['lon']):.4f}"
        r["source"] = "OSM Nominatim"
        r["note"] = r["note"] or f"matched: {h['display_name'][:90]}"
        print(f"{r['place']:28} {r['lat']:>9} {r['lon']:>9}  {h['display_name'][:70]}")
    with PLACES.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
