"""National Archives catalog helper: find a submarine's war patrol report
folders and download their page scans.

The catalog's own web front end calls an unauthenticated JSON endpoint,
  https://catalog.archives.gov/proxy/v3/records/search?naId=<id>
which returns a record's metadata, ancestors and `digitalObjects` (one public
JPG URL per scanned page). No API key is needed for this endpoint.

Commands:
  python3 tools/nara.py find "Bang"            list the boat's folders in the
                                                 War Patrol Reports series (RG 38 copies too)
  python3 tools/nara.py fetch 74802746 [...]   download folder(s) to sources/nara/rg367-<id>/
  python3 tools/nara.py index                  rebuild records/scans.json (page -> public URL)

Downloads land in sources/nara/rg367-<naId>/pNN.jpg with record.json and
urls.txt beside them. sources/ is not committed to git; the scans are always
re-downloadable, and the pages fall back to NARA's own URLs (records/scans.json)
when a local copy is missing.
"""
import json
import sys
import time
import urllib.parse
import urllib.request

from records import CACHE, RECORDS, rel  # noqa: E402
NARA = CACHE / "nara"
API = "https://catalog.archives.gov/proxy/v3/records/search"   # the older /proxy/records/search stopped answering q= in 2026
SERIES_PATROL_REPORTS = 305243        # RG 38/367 "U.S. Submarine War Patrol Reports" (microfilm M1752)
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


def fetch(na_id):
    rec = record(na_id)
    if not rec:
        sys.exit(f"no record {na_id}")
    folder = NARA / f"rg367-{na_id}"
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
    """records/scans.json: {"rg367-<id>/pNN": public URL} for every downloaded folder,
    merged into the existing index so folders not downloaded on this machine are kept."""
    path = RECORDS / "scans.json"
    out = json.loads(path.read_text()) if path.exists() else {}
    for urls in sorted(NARA.glob("rg367-*/urls.txt")):
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
    else:
        sys.exit(__doc__)
