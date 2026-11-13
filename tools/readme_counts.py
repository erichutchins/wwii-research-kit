# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""The tallies in the two READMEs, counted from the records.

A count a README prints is wrapped in a marker a reader never sees:

    <!--n:boats-->25<!--/n--> submarines

  python3 tools/readme_counts.py [FILE ...]         rewrite every marked number (both READMEs, or the files named)
  python3 tools/readme_counts.py check [FILE ...]   exit 1 if a marked number disagrees with the records
  python3 tools/readme_counts.py list               the counts, by name

Each repository's commit hook runs it on its own README (the kit's on README.md, the records' on its README.md as
../tools/readme_counts.py README.md), so a commit that changes a count rewrites the number: prek then stops the commit
for the rewritten file to be staged. check_builds.sh runs `check` on both before a push and in the CI.

The counts:
  boats, ships, battalions, convoys   subjects.json, by kind (ships: US ships)
  other_ships                         subjects.json: the other side's ships, each followed through a record she kept
  patrols                             boats/*/patrol-N folders
  other_boats                         boats less one (the boat followed for every patrol)
  army_units                          units with at least one row in army/stations.csv
  engagements                         engagements/index.json
  engagements_pacific|mediterranean|europe|atlantic   the same, by theater
  engagements_other_side              those with at least one entry from the other side's own records
  front_days, symbol_days             fronts/12ag-<day>.yml, and those with a <day>-units.csv
"""
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

from records import RECORDS

KIT = Path(__file__).resolve().parent.parent
FILES = [KIT / "README.md", RECORDS / "README.md"]
MARK = re.compile(r"<!--n:([a-z_]+)-->([^<]*)<!--/n-->")


def counts():
    subjects = json.loads((RECORDS / "subjects.json").read_text(encoding="utf-8"))
    kinds = Counter(s["kind"] for s in subjects)
    other_ships = sum(1 for s in subjects if s["kind"] == "ship" and s.get("of", "us") != "us")
    index = json.loads((RECORDS / "engagements" / "index.json").read_text(encoding="utf-8"))
    with open(RECORDS / "army" / "stations.csv", encoding="utf-8", newline="") as f:
        stationed = {r["unit"] for r in csv.DictReader(f)}
    days = list((RECORDS / "fronts").glob("12ag-*.yml"))
    out = {
        "boats": kinds["boat"], "ships": kinds["ship"] - other_ships, "other_ships": other_ships, "battalions": kinds["battalion"], "convoys": kinds["convoy"],
        "patrols": len(list((RECORDS / "boats").glob("*/patrol-*/"))),
        "other_boats": kinds["boat"] - 1,
        "army_units": len(stationed),
        "engagements": len(index),
        "engagements_other_side": sum(1 for e in index if e.get("other_side")),
        "front_days": len(days),
        "symbol_days": sum(1 for d in days if d.with_name(d.stem + "-units.csv").exists()),
    }
    by = Counter(e["theater"] for e in index)
    for t in ("pacific", "mediterranean", "europe", "atlantic"):
        out[f"engagements_{t}"] = by[t]
    return out


def main():
    args = sys.argv[1:]
    cmd = args.pop(0) if args and args[0] in ("check", "list") else ""
    files = [Path(a).resolve() for a in args] or FILES
    have = counts()
    if cmd == "list":
        for k, v in have.items():
            print(f"{k:28}{v}")
        return
    bad = []
    for path in files:
        text = path.read_text(encoding="utf-8")

        def fill(m, path=path):
            if m[1] not in have:
                bad.append(f"{path.name}: no count named {m[1]!r}")
                return m[0]
            if m[2] != str(have[m[1]]):
                bad.append(f"{path.name}: {m[1]} is {have[m[1]]}, the README says {m[2]}")
            return f"<!--n:{m[1]}-->{have[m[1]]}<!--/n-->"

        new = MARK.sub(fill, text)
        if cmd != "check" and new != text:
            path.write_text(new, encoding="utf-8")
    unknown = [b for b in bad if "no count named" in b]
    if cmd == "check" and bad or unknown:
        print("\n".join(bad))
        sys.exit("the READMEs' counts are out of date: python3 tools/readme_counts.py" if not unknown else 1)
    print(f"{sum(len(MARK.findall(p.read_text(encoding='utf-8'))) for p in files)} counts"
          + ("" if cmd == "check" else f", {len(bad)} rewritten"))


if __name__ == "__main__":
    main()
