# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
"""Cite every source: check that every citation in the records resolves to records/SOURCES.yml.

Each transcribed row names where it came from in a citation column (CITES below): a National
Archives page (rg367-74802746/p05), a JACAR reference code (jacar:C08030140600), a museum item
(ok45th-17552/p06), a URL... Every citation must match one entry's `match` pattern in SOURCES.yml,
and every row of a cited file must carry at least one. Files whose rows need no citation of their
own say why in UNCITED. The `sources:` lists in dives.yml and silhouettes.yml must name SOURCES.yml entries. And
records/inventory.yml must agree with the folders: every patrol folder listed as transcribed,
verified or mapped, and every patrol so listed present. And every ship.yml `silhouette:` must name a
ship profile in silhouettes.yml.

  uv run tools/check_sources.py            check; exits 1 on an unresolved citation or an uncited row
  uv run tools/check_sources.py --fetch    also look up every cited National Archives item's title
                                           and series in the catalog -> records/citations.json

citations.json (generated) is what a page shows for a cited archive page: the item's own title,
its series, and the link to the page.
"""
import csv
import json
import re
import sys
from collections import Counter, defaultdict

import records
from records import RECORDS, REFERENCE, rel

# file name (or folder/name) -> the columns that cite the row's source
CITES = {
    "positions.csv": ["page"],
    "depths.csv": ["page"],
    "layers.csv": ["page"],
    "japanese.csv": ["source"],
    "frupac.csv": ["map"],
    "convoys/ships.csv": ["source"],
    "notes.csv": ["page"],
    "army/stations.csv": ["page"],
    "army/actions.csv": ["page"],
    "army/places.csv": ["source"],
    "army/ships.csv": ["links"],
    "army/relations.csv": ["page"],
    "comsubpac/disposition.csv": ["page"],
    "comsubpac/task_organization.csv": ["page"],
    "comsubpac/changes.csv": ["page"],
    "comsubpac/log.csv": ["page"],
    "seabees/stations.csv": ["ref"],
    "seabees/places.csv": ["source"],
    "seabees/weather.csv": ["source"],
    "seabees/voyages.csv": ["ref"],
    "seabees/voyage_positions.csv": ["ref"],
    "jgrid/anchors.csv": ["source"],
    "engagements/timeline.csv": ["ref"],
    "engagements/claims.csv": ["ref"],
    "engagements/positions.csv": ["ref"],
}
# files whose rows don't carry a citation of their own, and why
UNCITED = {
    "crossrefs.csv": "pairs an attack with a japanese.csv row; both are cited",
    "pack_timeline.csv": "generated from cited rows (tools/pack_timeline.py), each with its source",
    "seafloor.csv": "dataset file: SOURCES.yml etopo1",
    "weather.csv": "dataset file: SOURCES.yml era5",
    "army/units.csv": "unit names and lineage; the stations give the pages",
    "seabees/parts.csv": "the battalions' parts and when they existed; each note cites its source",
    "seabees/units.csv": "battalion names and outlines, citing the stations' sources in the note",
    "army/routes.csv": "sea legs the reports don't trace, drawn approximately; each note says so",
    "jgrid/keys.csv": "letters worked out from the anchors (anchors.csv), named in the evidence column",
}


def key(path):
    """'records/army/stations.csv' -> 'army/stations.csv'; 'records/engagements/<id>/timeline.csv' ->
    'engagements/timeline.csv'; 'records/boats/x/patrol-1/depths.csv' -> 'depths.csv'"""
    for k in (f"{path.parent.name}/{path.name}", f"{path.parent.parent.name}/{path.name}"):
        if k in CITES or k in UNCITED:
            return k
    return path.name


def resolver(sources):
    pats = [(sid, re.compile(s["match"])) for sid, s in sources.items() if "match" in s]

    def resolve(cite):
        for sid, pat in pats:
            if pat.match(cite):
                return sid
        return None
    return resolve


def main():
    sources = records.load_yaml(RECORDS / "SOURCES.yml")
    resolve = resolver(sources)
    used, bad, uncited, unknown_files = Counter(), [], defaultdict(int), []
    nara = defaultdict(set)   # catalog ID -> cited pages
    files = sorted(RECORDS.rglob("*.csv")) + sorted(REFERENCE.rglob("*.csv"))
    for path in files:
        k = key(path)
        if k in UNCITED:
            continue
        if k not in CITES:
            unknown_files.append(rel(path))
            continue
        with open(path, encoding="utf-8", newline="") as f:
            for n, row in enumerate(csv.DictReader(f), 2):
                cites = [c.strip() for col in CITES[k] for c in re.split(r"[;\s]+(?=https?://)|\s*;\s*", row.get(col) or "") if c.strip()]
                if not cites:
                    uncited[rel(path)] += 1
                for c in cites:
                    sid = resolve(c)
                    if sid is None:
                        bad.append(f"{rel(path)}:{n}: {c!r}")
                        continue
                    used[sid] += 1
                    m = re.match(r"^rg\d+-(\d+)/p(\d+)$", c)
                    if m:
                        nara[m[1]].add(int(m[2]))
    # YAML files whose entries cite SOURCES.yml ids in a `sources:` list
    cited = [(p, c) for p in RECORDS.rglob("dives.yml") for c in records.load_yaml(p).get("context", [])]
    sil = RECORDS / "silhouettes" / "silhouettes.yml"
    if sil.exists():
        y = records.load_yaml(sil)
        cited += [(sil, c) for group in ("aircraft", "ships") for c in y.get(group, {}).values()]
    for path, c in cited:
        if not c.get("sources"):
            bad.append(f"{rel(path)}: {c.get('name', c.get('event', '?'))} cites no source")
        for sid in c.get("sources", []):
            (used.update([sid]) if sid in sources else bad.append(f"{rel(path)}: source {sid!r} not in SOURCES.yml"))

    print(f"{sum(used.values())} citations in {len(files)} files, {len(nara)} National Archives items")
    for sid, n in used.most_common():
        print(f"  {n:6}  {sid}")
    unused = [s for s in sources if s not in used and "match" in sources[s]]
    if unused:
        print("SOURCES.yml entries no row cites (fine if a page or a dataset file uses them):", ", ".join(unused))
    for f in unknown_files:
        print(f"not checked: {f} (add it to CITES or UNCITED in tools/check_sources.py)")
    for f, n in uncited.items():
        print(f"UNCITED: {f}: {n} rows with no citation")
    for b in bad:
        print(f"UNRESOLVED: {b}")

    bad_inventory = check_inventory() + check_silhouette_links()
    for b in bad_inventory:
        print(f"MISMATCH: {b}")
    if "--fetch" in sys.argv:
        fetch_titles(nara)
    sys.exit(1 if bad or uncited or unknown_files or bad_inventory else 0)


def check_silhouette_links():
    """Every ship.yml `silhouette:` names a ship profile in silhouettes/silhouettes.yml."""
    path = RECORDS / "silhouettes" / "silhouettes.yml"
    have = set(records.load_yaml(path).get("ships", {})) if path.exists() else set()
    return [f"{rel(d / 'ship.yml')}: silhouette {s!r} is not in silhouettes.yml"
            for d in records.vessels() for s in [records.load_yaml(d / "ship.yml").get("silhouette")] if s and s not in have]


def check_inventory():
    """inventory.yml's boats and patrols against records/boats/<hull>-<name>/patrol-N/."""
    inv = records.load_yaml(RECORDS / "inventory.yml")
    done = {"transcribed", "verified", "mapped"}
    listed = {(hull.lower(), n) for hull, b in inv.get("boats", {}).items()
              for n, p in (b.get("patrols") or {}).items() if p.get("status") in done}
    on_disk = {("-".join(d.name.split("-")[:2]), n) for d in records.vessels() if d.parent.name == "boats"
               for n in records.patrols(d.name)}
    return ([f"{h.upper()} patrol {n} is on disk but not listed as transcribed" for h, n in sorted(on_disk - listed)] +
            [f"{h.upper()} patrol {n} is listed as transcribed but has no folder" for h, n in sorted(listed - on_disk)])


def fetch_titles(nara):
    """records/citations.json: each cited catalog item's title, series and pages, from the catalog."""
    from nara import record
    path = RECORDS / "citations.json"
    old = json.load(open(path)) if path.exists() else {}
    out = {}
    for na_id in sorted(nara, key=int):
        item = old.get(na_id)
        if not item:
            r = record(na_id) or {}
            series = next((a for a in r.get("ancestors", []) if a.get("levelOfDescription") == "series"), {})
            group = next((a for a in r.get("ancestors", []) if a.get("levelOfDescription") == "recordGroup"), {})
            item = {"title": r.get("title", ""), "series": series.get("title", ""), "series_id": series.get("naId"),
                    "record_group": group.get("recordGroupNumber"), "url": f"https://catalog.archives.gov/id/{na_id}"}
            print(f"  {na_id}: {item['title'][:70]} [{item['series'][:50]}]")
        out[na_id] = {**item, "pages": sorted(nara[na_id])}
    records.write_json(path, out, indent=1, ensure_ascii=False)
    print(f"wrote {rel(path)} ({len(out)} items)")


if __name__ == "__main__":
    main()
