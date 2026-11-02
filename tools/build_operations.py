# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
"""The campaigns and operations, from hand-edited Markdown to records/operations/operations.json.

Each operation is one Markdown file, records/operations/<theater>/<id>.md (the theater itself is index.md): the facts
in the front matter between the --- lines (name, dates, area, the pages the dates come from), and below it what the
operation was for and what it meant, under `##` headings, a paragraph per statement. A paragraph starting with `>` is
an aside (a qualification). Every paragraph ends with its citation, [[cite:howe-nwa/35/p676]].

Links are written by name, not address, so they work on any page and can be checked:
  [[cite:howe-nwa/35/p676]]           a page of a source in SOURCES.yml
  [[op:husky|the invasion of Sicily]] an operation's chapter (by its file name)
  [[ship:bang]]                       a boat's or ship's track (the name in ships.json)
  [[unit:106aaa-d@1944-08-15|...]]    a unit on the Army map, on a day (army/units.csv)
  [[page:algiers|...]]                one of the kit's pages (site/algiers.html)
  [[convoy:te-04]]                    a convoy's record (records/convoys/<id>/convoy.md; site/convoys.html)
  [[engagement:te-04-1944-05-03]]     an engagement (records/engagements/<id>/; site/engagement.html)
  [[who:<person>@1942-11-11|...]]     a person on a family's Army map: only in a family's own files (--family)
The text after | is what the reader sees; without it, the thing's own name.

  uv run tools/build_operations.py                  check every operation and write operations.json
  uv run tools/build_operations.py check FILE...    check other Markdown files' links (a family's overlay), e.g.
        uv run kit/tools/build_operations.py check data/theaters/mediterranean.md --family .
        (--family DIR: the family repository's root, for its people and its own pages)

Exits 1 on any problem: an unknown citation, link or field, a paragraph without a citation, a date out of order.
"""
import csv
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import records

OPS = records.RECORDS / "operations"
OUT = OPS / "operations.json"
FIELDS = {"name", "short", "kind", "parent", "from", "to", "area", "area_precision", "ref", "note"}
KINDS = {"theater", "operation", "campaign", "phase"}
LINK = re.compile(r"\[\[(\w+):([^\]|]+)(?:\|([^\]]+))?\]\]")


def sources():
    """SOURCES.yml entries with a citation pattern: id -> (compiled pattern, entry)."""
    return {sid: (re.compile(s["match"]), s) for sid, s in records.load_yaml(records.RECORDS / "SOURCES.yml").items()
            if isinstance(s, dict) and s.get("match")}


def resolve_cite(cite, srcs):
    """'howe-nwa/35/p676' -> {href, short, title, page}, or None if no source matches."""
    for sid, (pat, s) in srcs.items():
        m = pat.match(cite)
        if m:
            href = re.sub(r"\{(\d)\}", lambda g: m.group(int(g.group(1))), s.get("link", s.get("url", "")))
            page = re.search(r"p(\d+)$", cite)
            return {"href": href, "short": s.get("short", sid), "title": s.get("title", ""),
                    "page": page.group(1) if page else ""}
    return None


def split(path):
    """A Markdown file -> (front matter dict, body text)."""
    text = path.read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n(.*)", text, re.S)
    if not m:
        return {}, text
    return records.load_yaml_text(m.group(1), path) or {}, m.group(2)


def sections(body):
    """The body -> [{heading, paras: [{text, aside}]}]; paragraphs are separated by a blank line."""
    out = [{"heading": "", "paras": []}]
    for block in re.split(r"\n\s*\n", body.strip()):
        block = block.strip()
        if not block:
            continue
        if block.startswith("## "):
            out.append({"heading": block[3:].strip(), "paras": []})
            continue
        aside = block.startswith(">")
        lines = [re.sub(r"^>\s?", "", ln) if aside else ln for ln in block.splitlines()]
        out[-1]["paras"].append({"text": " ".join(ln.strip() for ln in lines), "aside": aside})
    return [s for s in out if s["heading"] or s["paras"]]


class Checker:
    """Resolves and checks [[kind:name|label]] links; collects problems."""

    def __init__(self, family=None):
        self.srcs = sources()
        self.ops = {p.stem if p.stem != "index" else p.parent.name for p in OPS.glob("*/*.md")}
        self.ships = {s["alias"] for s in json.load(open(records.RECORDS / "ships.json"))}
        self.units = {r["unit"] for r in csv.DictReader(open(records.RECORDS / "army" / "units.csv", encoding="utf-8"))}
        self.pages = {p.stem for p in (records.KIT / "site").glob("*.html")}
        self.convoys = {p.parent.name for p in (records.RECORDS / "convoys").glob("*/convoy.md")}
        self.engagements = {p.parent.name for p in (records.RECORDS / "engagements").glob("*/engagement.md")}
        self.family = Path(family) if family else None
        self.people = set()
        if self.family:
            self.pages |= {p.stem for p in self.family.glob("*.html")}
            fu = self.family / "data" / "army" / "units.csv"
            if fu.exists():
                self.units |= {r["unit"] for r in csv.DictReader(open(fu, encoding="utf-8"))}
            fp = self.family / "data" / "army" / "people.csv"
            if fp.exists():
                self.people = {r["person"] for r in csv.DictReader(open(fp, encoding="utf-8"))}
        self.cites = {}
        self.problems = []

    def links(self, text, where):
        text = re.sub(r"`[^`]*`", "", text)        # an example in `backticks` isn't a link
        for kind, name, _ in LINK.findall(text):
            name = name.strip()
            target, _, day = name.partition("@")
            if day and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
                self.problems.append(f"{where}: [[{kind}:{name}]]: the day after @ must be YYYY-MM-DD")
            ok = {"cite": lambda: self.cite(target),
                  "op": lambda: target in self.ops,
                  "ship": lambda: target in self.ships,
                  "unit": lambda: target in self.units,
                  "page": lambda: target in self.pages,
                  "convoy": lambda: target in self.convoys,
                  "engagement": lambda: target in self.engagements,
                  "who": lambda: bool(self.family) and target in self.people}.get(kind)
            if ok is None:
                self.problems.append(f"{where}: [[{kind}:{name}]]: unknown kind (cite, op, ship, unit, page, convoy, engagement, who)")
            elif kind == "who" and not self.family:
                self.problems.append(f"{where}: [[who:{name}]]: a person's link belongs in the family's files, not the kit")
            elif not ok():
                self.problems.append(f"{where}: [[{kind}:{name}]]: no such {kind}")

    def cite(self, c):
        r = resolve_cite(c, self.srcs)
        if r:
            self.cites[c] = r
        return bool(r)


def build():
    chk = Checker()
    ops = []
    for path in sorted(OPS.glob("*/*.md")):
        where = path.relative_to(records.KIT)
        fm, body = split(path)
        op = {"id": path.parent.name if path.stem == "index" else path.stem, "theater": path.parent.name}
        unknown = set(fm) - FIELDS
        if unknown:
            chk.problems.append(f"{where}: unknown field(s) {', '.join(sorted(unknown))} (known: {', '.join(sorted(FIELDS))})")
        for k in ("name", "kind", "from", "ref"):
            if not fm.get(k):
                chk.problems.append(f"{where}: `{k}` is missing")
        if fm.get("kind") and fm["kind"] not in KINDS:
            chk.problems.append(f"{where}: kind {fm['kind']!r} is not one of {', '.join(sorted(KINDS))}")
        for k in ("from", "to"):
            if fm.get(k) is not None and not isinstance(fm[k], date):
                chk.problems.append(f"{where}: `{k}` must be a date, YYYY-MM-DD")
        if isinstance(fm.get("from"), date) and isinstance(fm.get("to"), date) and fm["to"] < fm["from"]:
            chk.problems.append(f"{where}: `to` is before `from`")
        area = fm.get("area")
        if area is not None and not (isinstance(area, list) and len(area) == 4 and area[0] < area[2] and area[1] < area[3]):
            chk.problems.append(f"{where}: `area` must be [west, south, east, north]")
        refs = fm.get("ref") or []
        for c in refs if isinstance(refs, list) else [refs]:
            if not chk.cite(str(c)):
                chk.problems.append(f"{where}: ref {c!r} matches no source in SOURCES.yml")
        secs = sections(body)
        for s in secs:
            for i, p in enumerate(s["paras"], 1):
                spot = f"{where} ({s['heading'] or 'top'}, paragraph {i})"
                chk.links(p["text"], spot)
                if "[[cite:" not in p["text"]:
                    chk.problems.append(f"{spot}: no citation; end it with [[cite:...]]")
        op.update({k: (v.isoformat() if isinstance(v, date) else v) for k, v in fm.items()})
        op["ref"] = [str(c) for c in (refs if isinstance(refs, list) else [refs])]
        op["sections"] = secs
        ops.append(op)
    ids = {o["id"] for o in ops}
    for o in ops:
        if o.get("parent") and o["parent"] not in ids:
            chk.problems.append(f"operations/{o['theater']}/{o['id']}.md: parent {o['parent']!r} is not an operation")
    ops.sort(key=lambda o: (o["theater"], o["kind"] != "theater", o.get("from", "")))
    return ops, chk


def main():
    args = sys.argv[1:]
    if args[:1] == ["check"]:
        fam = args[args.index("--family") + 1] if "--family" in args else None
        files = [a for a in args[1:] if a.endswith(".md")]
        chk = Checker(fam)
        for f in files:
            _fm, body = split(Path(f))
            chk.links(body, f)
        report(chk, f"{len(files)} file(s) checked")
        return
    ops, chk = build()
    if not chk.problems:
        records.write_json(OUT, {"operations": ops, "cites": chk.cites}, indent=1, ensure_ascii=False)
    report(chk, f"{len(ops)} operations; wrote {OUT.relative_to(records.KIT)}" if not chk.problems else "")


def report(chk, ok):
    for p in chk.problems:
        print(f"PROBLEM: {p}")
    if chk.problems:
        print(f"{len(chk.problems)} problem(s); nothing written" if ok == "" else f"{len(chk.problems)} problem(s)")
        sys.exit(1)
    print(ok)


if __name__ == "__main__":
    main()
