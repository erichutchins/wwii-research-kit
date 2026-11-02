# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
"""The glossary: reference/glossary.yml (hand-edited) -> reference/glossary.json, which site/glossary.js reads.

Every entry says where its explanation comes from: `source:` holds one or more citations, separated by `; `, each
in a form SOURCES.yml knows (tm-20-205/n186, opnav-29-p1000/C, usf-25a/4107, a page of a record, or a web page's
address). The build resolves each one to its link and short name, so the card on the page can show and link it.
It fails on an entry with no source, a citation SOURCES.yml doesn't know, a `see` page that doesn't exist, or a term
listed twice.

  uv run tools/build_glossary.py          check and write reference/glossary.json
  uv run tools/build_glossary.py check    check, and fail if glossary.json is out of date (CI)
"""
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).parent))
import records
from build_operations import resolve_cite, sources

YML = records.REFERENCE / "glossary.yml"
OUT = records.REFERENCE / "glossary.json"
SITE = records.KIT / "site"
FIELDS = {"term", "match", "says", "see", "source", "unless"}


def build():
    """-> (the JSON's data, problems, every citation used)"""
    g = records.load_yaml(YML) or {}
    srcs = sources()
    problems, cited, seen, terms = [], [], set(), []
    for n, t in enumerate(g.get("terms") or [], 1):
        where = f"{records.rel(YML)} #{n} ({t.get('term', '?')})"
        for k in set(t) - FIELDS:
            problems.append(f"{where}: unknown field {k!r}")
        if not t.get("term") or not t.get("says"):
            problems.append(f"{where}: needs `term` and `says`")
            continue
        for form in [t["term"], *(t.get("match") or [])]:
            key = form if re.search(r"[A-Z]{2}", form) else form.lower()   # as glossary.js matches it
            if key in seen:
                problems.append(f"{where}: {form!r} is listed twice")
            seen.add(key)
        if t.get("see") and not (SITE / t["see"].split("?")[0].split("#")[0]).exists():
            problems.append(f"{where}: see {t['see']!r} is not a page in site/")
        cites = [c.strip() for c in str(t.get("source") or "").split(";") if c.strip()]
        if not cites:
            problems.append(f"{where}: no source")
        out = []
        for c in cites:
            r = resolve_cite(c, srcs)
            if r is None:
                problems.append(f"{where}: source {c!r} is not in a form SOURCES.yml knows")
                continue
            if not r["href"] or r["short"] == "url":     # a web page cited by its address
                r = {**r, "href": c, "short": urlparse(c).netloc.removeprefix("www."), "title": ""}
            cited.append(c)
            out.append({"cite": c, "href": r["href"], "short": r["short"], "title": r["title"]})
        terms.append({k: v for k, v in {"term": t["term"], "match": t.get("match"), "unless": t.get("unless"),
                                         "says": " ".join(t["says"].split()),
                                         "see": t.get("see"), "sources": out}.items() if v})
    return {"ships": g.get("ships") or {}, "terms": terms}, problems, cited


def main():
    data, problems, cited = build()
    for p in problems:
        print(f"PROBLEM: {p}")
    text = json.dumps(data, indent=1, ensure_ascii=False) + "\n"
    if sys.argv[1:2] == ["check"]:
        stale = not OUT.exists() or OUT.read_text(encoding="utf-8") != text
        if stale:
            print(f"{records.rel(OUT)} is out of date: run uv run tools/build_glossary.py")
        print(f"{len(data['terms'])} terms, {len(cited)} citations, {len(problems)} problems")
        sys.exit(1 if problems or stale else 0)
    if problems:
        print(f"{len(problems)} problems; nothing written")
        sys.exit(1)
    OUT.write_text(text, encoding="utf-8")
    print(f"{len(data['terms'])} terms, {len(cited)} citations; wrote {records.rel(OUT)}")


if __name__ == "__main__":
    main()
