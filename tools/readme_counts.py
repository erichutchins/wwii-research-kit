# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""The tallies in the two READMEs, counted from the records.

A count a README prints is wrapped in a marker a reader never sees:

    <!--n:boats-->25<!--/n--> submarines

  python3 tools/readme_counts.py          rewrite every marked number in README.md and records/README.md
  python3 tools/readme_counts.py check    exit 1 if a marked number disagrees with the records (check_builds.sh)
  python3 tools/readme_counts.py list     the counts, by name

The counts:
  boats, ships, battalions, convoys   subjects.json, by kind
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
    kinds = Counter(s["kind"] for s in json.loads((RECORDS / "subjects.json").read_text(encoding="utf-8")))
    index = json.loads((RECORDS / "engagements" / "index.json").read_text(encoding="utf-8"))
    with open(RECORDS / "army" / "stations.csv", encoding="utf-8", newline="") as f:
        stationed = {r["unit"] for r in csv.DictReader(f)}
    days = list((RECORDS / "fronts").glob("12ag-*.yml"))
    out = {
        "boats": kinds["boat"], "ships": kinds["ship"], "battalions": kinds["battalion"], "convoys": kinds["convoy"],
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
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    have = counts()
    if cmd == "list":
        for k, v in have.items():
            print(f"{k:28}{v}")
        return
    bad = []
    for path in FILES:
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
    print(f"{sum(len(MARK.findall(p.read_text(encoding='utf-8'))) for p in FILES)} counts in the READMEs"
          + ("" if cmd == "check" else f", {len(bad)} rewritten"))


if __name__ == "__main__":
    main()
