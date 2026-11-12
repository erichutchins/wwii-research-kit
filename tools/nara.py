# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""National Archives catalog helper: find a submarine's war patrol report
folders and download their page scans.

The catalog's own web front end calls an unauthenticated JSON endpoint,
  https://catalog.archives.gov/proxy/v3/records/search?naId=<id>
which returns a record's metadata, ancestors and `digitalObjects` (one public
JPG URL per scanned page). No API key is needed for this endpoint.

Commands:
  python3 tools/nara.py find "Bang"            list the boat's folders in the
                                                 War Patrol Reports series (RG 38 copies too)
  python3 tools/nara.py fetch 74802746 [...]   download folder(s) to sources/nara/rg<group>-<id>/
  python3 tools/nara.py index                  rebuild records/scans.json (page -> public URL)
  python3 tools/nara.py rename                 move cache folders still under the old "rg367-" name

Downloads land in sources/nara/rg<record group>-<naId>/pNN.jpg (rg38-74802746 for a war
patrol report: the group is read from the catalog record) with record.json and
urls.txt beside them. sources/ is not committed to git; the scans are always
re-downloadable, and the pages fall back to NARA's own URLs (records/scans.json)
when a local copy is missing.
"""
import json
import sys
import time
import urllib.parse
import urllib.request

from records import CACHE, RECORDS, rel

NARA = CACHE / "nara"
API = "https://catalog.archives.gov/proxy/v3/records/search"   # the older /proxy/records/search stopped answering q= in 2026
SERIES_PATROL_REPORTS = 305243        # RG 38 "U.S. Submarine War Patrol Reports" (microfiche M1752)
SERIES_WAR_DIARIES = 4697018          # RG 38 "World War II War Diaries, Other Operational Records and Histories"


def get(params, tries=4):
    url = f"{API}?{urllib.parse.urlencode({**params, 'allowLegacyOrgNames': 'true'})}"
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=90) as r:
                return json.load(r)["body"]["hits"]
        except Exception as e:
            if attempt == tries - 1:
                raise
            print(f"  retry ({e})", file=sys.stderr)
            time.sleep(5 * (attempt + 1))


def record(na_id):
    hits = get({"naId": na_id})["hits"]
    return hits[0]["_source"]["record"] if hits else None


def find(name):
    """War patrol report folders for a boat, oldest first."""
    seen, out = set(), []
    for page in range(1, 4):
        hits = get({"q": f'"USS {name}"', "limit": 100, "page": page})["hits"]
        if not hits:
            break
        for h in hits:
            r = h["_source"]["record"]
            series = [a for a in r.get("ancestors", []) if a.get("levelOfDescription") == "series"]
            s = series[0] if series else {}
            title = r.get("title", "")
            if r["naId"] in seen or name.lower() not in title.lower():
                continue
            if s.get("naId") == SERIES_PATROL_REPORTS or "war patrol" in title.lower():
                seen.add(r["naId"])
                out.append((r["naId"], title, s.get("title", ""), len(r.get("digitalObjects", []))))
    return out


def record_group(rec):
    """The record group number of a catalog record (38 for a war patrol report or a war diary), from its ancestors.
    Not the catalog ID of the record group's own description (367 for RG 38), which the folders once carried."""
    for a in rec.get("ancestors", []):
        if a.get("levelOfDescription") == "recordGroup" and a.get("recordGroupNumber"):
            return int(a["recordGroupNumber"])
    sys.exit(f"no record group in the catalog record {rec.get('naId')}")


def folder_for(na_id, rec=None):
    """The cache folder of a catalog item, rg<record group>-<id>: the one already there, or named from the record."""
    for f in sorted(NARA.glob(f"rg*-{na_id}")):
        if f.name != f"rg367-{na_id}":
            return f
    rec = rec or record(na_id)
    if not rec:
        sys.exit(f"no record {na_id}")
    return NARA / f"rg{record_group(rec)}-{na_id}"


def rename():
    """Cache folders downloaded under the old name, rg367-<id>, moved to rg<record group>-<id> (from each record.json)."""
    n = 0
    for old in sorted(NARA.glob("rg367-*")):
        rec = json.loads((old / "record.json").read_text()) if (old / "record.json").exists() else record(old.name[6:])
        new = NARA / f"rg{record_group(rec)}-{old.name[6:]}"
        if new.exists():
            print(f"  {old.name}: {new.name} is already there, left alone", file=sys.stderr)
            continue
        old.rename(new)
        n += 1
    print(f"renamed {n} folders")


def fetch(na_id):
    rec = record(na_id)
    if not rec:
        sys.exit(f"no record {na_id}")
    folder = folder_for(na_id, rec)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "record.json").write_text(json.dumps(rec, indent=1))
    objs = rec.get("digitalObjects", [])
    lines = []
    for i, o in enumerate(objs, 1):
        lines.append(f"{i:02d} {o['objectUrl']}")
        dest = folder / f"p{i:02d}.jpg"
        if dest.exists() and dest.stat().st_size > 0:
            continue
        for attempt in range(4):
            try:
                urllib.request.urlretrieve(o["objectUrl"], dest)
                break
            except Exception as e:
                print(f"  retry p{i:02d} ({e})", file=sys.stderr)
                time.sleep(5 * (attempt + 1))
    (folder / "urls.txt").write_text("\n".join(lines) + "\n")
    print(f"{na_id}: {rec['title']} — {len(objs)} pages -> {rel(folder)}")


def index():
    """records/scans.json: {"rg38-<id>/pNN": public URL} for every downloaded folder,
    merged into the existing index so folders not downloaded on this machine are kept."""
    path = RECORDS / "scans.json"
    out = json.loads(path.read_text()) if path.exists() else {}
    for urls in sorted(NARA.glob("rg*-*/urls.txt")):
        if urls.parent.name.startswith("rg64-"):   # morning-report rolls (tools/morning_reports.py): TIFFs, not indexed here
            continue
        for line in urls.read_text().split("\n"):
            if line.strip():
                n, url = line.split(" ", 1)
                out[f"{urls.parent.name}/p{n}"] = url.strip()
    path.write_text(json.dumps(out, indent=0, sort_keys=True))
    print(f"wrote {rel(path)} ({len(out)} pages)")


if __name__ == "__main__":
    cmd, args = (sys.argv[1], sys.argv[2:]) if len(sys.argv) > 1 else ("", [])
    if cmd == "find" and args:
        for na_id, title, series, pages in find(" ".join(args)):
            print(f"{na_id}\t{pages:3d} pp\t{title}\t[{series}]")
    elif cmd == "fetch" and args:
        for a in args:
            fetch(int(a))
        index()
    elif cmd == "index":
        index()
    elif cmd == "rename":
        rename()
        index()
    else:
        sys.exit(__doc__)
