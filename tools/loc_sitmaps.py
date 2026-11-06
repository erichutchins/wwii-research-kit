# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""The Library of Congress's World War II military situation maps (SOURCES.yml `loc-12ag`): the catalogue, the scans
and crops of them, for tracing (tools/trace_front.py, the skill trace-situation-map, guides/SITUATION-MAPS.md).

The collection (https://www.loc.gov/collections/world-war-ii-maps-military-situation-maps-from-1944-to-1945/) holds
HQ Twelfth Army Group's daily situation map for every day from 6 June 1944 to 26 July 1945 but one (12 November 1944):
415 sheets, each a Library item (an LCCN) with one scan (a resource id, ict21001 to ict21417, which rises with the
date). The Library's JSON API lists them; its tile server holds each scan as a JPEG 2000 of about 6 MB, 6,600 by 6,000
pixels, and serves any part of it at any size through IIIF, so a title or a symbol can be read without the scan.

    uv run tools/loc_sitmaps.py list                       # the listing -> records/fronts/sitmaps.csv (item, date, lccn)
    uv run tools/loc_sitmaps.py sizes                      # each scan's pixel size from IIIF, into the same file (resumes)
    uv run tools/loc_sitmaps.py status                     # by month: catalogued, fetched, traced, read
    uv run tools/loc_sitmaps.py fetch 1945-03-08 [1945-03-17]   # the scans of a day or a run of days -> sources/maps/loc/
    uv run tools/loc_sitmaps.py fetch ict21277             # or by resource id
    uv run tools/loc_sitmaps.py crop ict21277 4400 1900 400 300 [--width 1200] [-o out.jpg]   # a region, full resolution
    uv run tools/loc_sitmaps.py overview ict21277 [--pct 12.5] [-o out.jpg]                   # the whole sheet, small

Every request waits a second after the last (the Library's servers are shared) and names this kit in its User-Agent;
a scan already here is not fetched again, and a fetch cut short is finished on the next run (the file's size is checked
against the server's). Nothing here reads a map: the dates are the Library's catalogue, and a sheet's own title is read
on the scan (trace_front.py --title) before anything is traced from it.
"""
import argparse
import csv
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
FRONTS = KIT / "records" / "fronts"
CATALOGUE = FRONTS / "sitmaps.csv"
CACHE = KIT / "sources" / "maps" / "loc"   # the scans (git-ignored), as trace_front.py names them
COLLECTION = "https://www.loc.gov/collections/world-war-ii-maps-military-situation-maps-from-1944-to-1945/"
TILE = "https://tile.loc.gov/storage-services/service/gmd/gmd5/g5701/g5701s/{item}.jp2"
IIIF = "https://tile.loc.gov/image-services/iiif/service:gmd:gmd5:g5701:g5701s:{item}"
AGENT = "wwii-research-kit (research; github.com/erichutchins/wwii-research-kit)"
PAUSE = 1.0
COLUMNS = ["item", "date", "lccn", "width", "height"]
_last = [0.0]


def get(url, timeout=120, tries=3):
    """One polite request: a second after the last, this kit named, three tries on a server error."""
    for k in range(tries):
        wait = PAUSE - (time.monotonic() - _last[0])
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.monotonic()
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": AGENT}), timeout=timeout) as r:
                return r.read(), dict(r.headers)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            code = getattr(e, "code", None)
            if code in (403, 404) or k == tries - 1:
                raise
            time.sleep(5 * (k + 1))
    raise RuntimeError("unreachable")


def read_catalogue():
    if not CATALOGUE.exists():
        return []
    with open(CATALOGUE, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_catalogue(rows):
    rows = sorted(rows, key=lambda r: (r["date"], r["item"]))
    FRONTS.mkdir(parents=True, exist_ok=True)
    with open(CATALOGUE, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows({k: r.get(k, "") for k in COLUMNS} for r in rows)


def listing():
    """Every map in the collection's JSON listing: (item, date, lccn). The collection's own record, its essays and
    the one composite sheet (the Battle of the Bulge, catalogued without a resource id of this shape) are left out."""
    out, url = [], f"{COLLECTION}?fo=json&c=100&sp=1"
    while url:
        body, _ = get(url)
        page = json.loads(body)
        for r in page["results"]:
            if "map" not in (r.get("original_format") or []):
                continue
            m = re.search(r"g5701s[:/.](ict\d+)", " ".join((r.get("image_url") or []) + (r.get("aka") or [])))
            lccn = re.search(r"/item/(\d+)/", r.get("url") or "")
            date = r.get("date") or ""
            if not (m and lccn and re.fullmatch(r"\d{4}-\d{2}-\d{2}", date)):
                print(f"   left out: {r.get('title', '')[:70]} ({r.get('url', '')})")
                continue
            out.append({"item": m.group(1), "date": date, "lccn": lccn.group(1)})
        url = (page.get("pagination") or {}).get("next")
        print(f"   page {page['pagination']['current']} of {page['pagination']['total']}: {len(out)} maps so far")
    return out


def cmd_list(a):
    old = {r["item"]: r for r in read_catalogue()}
    rows = listing()
    for r in rows:   # the sizes already fetched stay
        r.update({k: old.get(r["item"], {}).get(k, "") for k in ("width", "height")})
    write_catalogue(rows)
    dates = sorted(r["date"] for r in rows)
    print(f"wrote {rel(CATALOGUE)}: {len(rows)} maps, {dates[0]} to {dates[-1]}"
          + (f"; {len(old)} were catalogued before" if old else ""))


def cmd_sizes(a):
    rows = read_catalogue()
    todo = [r for r in rows if not r.get("width")]
    print(f"{len(todo)} of {len(rows)} scans without a size")
    for i, r in enumerate(todo, 1):
        info = json.loads(get(f"{IIIF.format(item=r['item'])}/info.json")[0])
        r["width"], r["height"] = str(info["width"]), str(info["height"])
        if i % 25 == 0 or i == len(todo):
            write_catalogue(rows)
            print(f"   {i}/{len(todo)} ({r['date']}: {r['width']} x {r['height']})")
    write_catalogue(rows)


def scan_path(item):
    return CACHE / f"g5701s-{item}.jp2"


def fetch_item(item, quiet=False):
    """One scan into the cache; a file already there and whole is left alone, a short one is fetched again."""
    dest = scan_path(item)
    CACHE.mkdir(parents=True, exist_ok=True)
    url = TILE.format(item=item)
    req = urllib.request.Request(url, headers={"User-Agent": AGENT}, method="HEAD")
    with urllib.request.urlopen(req, timeout=60) as r:
        size = int(r.headers.get("Content-Length") or 0)
    if dest.exists() and dest.stat().st_size == size:
        if not quiet:
            print(f"   {rel(dest)}: here ({size} bytes)")
        return dest
    body, _ = get(url, timeout=600)
    if size and len(body) != size:
        sys.exit(f"{item}: got {len(body)} bytes of {size}; try again")
    dest.write_bytes(body)
    if not quiet:
        print(f"   {rel(dest)}: fetched ({len(body)} bytes)")
    return dest


def select(rows, first, last=None):
    """The catalogue's rows for a day, a run of days (inclusive) or a resource id."""
    if first.startswith("ict"):
        return [r for r in rows if r["item"] == first]
    last = last or first
    return [r for r in rows if first <= r["date"] <= last]


def cmd_fetch(a):
    rows = read_catalogue()
    if not rows:
        sys.exit(f"no catalogue at {rel(CATALOGUE)}: run `list` first")
    picked = select(rows, a.first, a.last)
    if not picked:
        sys.exit(f"nothing catalogued for {a.first}{' to ' + a.last if a.last else ''}")
    print(f"{len(picked)} scans, about {6 * len(picked)} MB:")
    for r in picked:
        fetch_item(r["item"])


def cmd_crop(a):
    item = a.item
    size = f"{a.width}," if a.width else "full"
    body, _ = get(f"{IIIF.format(item=item)}/{a.x},{a.y},{a.w},{a.h}/{size}/0/default.jpg")
    out = Path(a.out) if a.out else KIT / "sources" / "fronts-work" / item / f"crop-{a.x}-{a.y}-{a.w}x{a.h}.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(body)
    print(f"wrote {out} ({len(body)} bytes)")


def cmd_overview(a):
    body, _ = get(f"{IIIF.format(item=a.item)}/full/pct:{a.pct}/0/default.jpg")
    out = Path(a.out) if a.out else KIT / "sources" / "fronts-work" / a.item / f"overview-{a.pct}.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(body)
    print(f"wrote {out} ({len(body)} bytes)")


def cmd_status(a):
    rows = read_catalogue()
    if not rows:
        sys.exit(f"no catalogue at {rel(CATALOGUE)}: run `list` first")
    months = {}
    for r in rows:
        name = f"12ag-{r['date']}"
        m = months.setdefault(r["date"][:7], {"maps": 0, "fetched": 0, "traced": 0, "read": 0})
        m["maps"] += 1
        m["fetched"] += scan_path(r["item"]).exists()
        m["traced"] += (FRONTS / f"{name}.geojson").exists()
        m["read"] += (FRONTS / f"{name}-units.csv").exists()
    print("month     maps  fetched  traced  read")
    for k, m in sorted(months.items()):
        print(f"{k}   {m['maps']:4d}  {m['fetched']:7d}  {m['traced']:6d}  {m['read']:4d}")
    t = {k: sum(m[k] for m in months.values()) for k in ("maps", "fetched", "traced", "read")}
    print(f"all       {t['maps']:4d}  {t['fetched']:7d}  {t['traced']:6d}  {t['read']:4d}")


def rel(p):
    try:
        return str(Path(p).relative_to(KIT))
    except ValueError:
        return str(p)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="the collection's listing into records/fronts/sitmaps.csv").set_defaults(f=cmd_list)
    sub.add_parser("sizes", help="each scan's pixel size, from IIIF").set_defaults(f=cmd_sizes)
    sub.add_parser("status", help="by month: catalogued, fetched, traced, read").set_defaults(f=cmd_status)
    p = sub.add_parser("fetch", help="the scans of a day, a run of days, or a resource id")
    p.add_argument("first", help="a date (YYYY-MM-DD) or a resource id (ict21277)")
    p.add_argument("last", nargs="?", help="the last date of a run")
    p.set_defaults(f=cmd_fetch)
    p = sub.add_parser("crop", help="a region of a scan at full resolution, through IIIF")
    p.add_argument("item")
    p.add_argument("x", type=int); p.add_argument("y", type=int); p.add_argument("w", type=int); p.add_argument("h", type=int)
    p.add_argument("--width", type=int, help="scale the crop to this width (pixels)")
    p.add_argument("-o", "--out")
    p.set_defaults(f=cmd_crop)
    p = sub.add_parser("overview", help="the whole sheet, small, through IIIF")
    p.add_argument("item")
    p.add_argument("--pct", type=float, default=12.5)
    p.add_argument("-o", "--out")
    p.set_defaults(f=cmd_overview)
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
