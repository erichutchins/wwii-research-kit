# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
"""The glossary: reference/glossary.yml (hand-edited) -> reference/glossary.json, which site/glossary.js reads.

Every entry says where its explanation comes from: `source:` holds one or more citations, separated by `; `, each
in a form SOURCES.yml knows (tm-20-205/n186, opnav-29-p1000/C, usf-25a/4107, a page of a record, or a web page's
address). The build resolves each one to its link and short name, so the card on the page can show and link it.
It fails on an entry with no source, a citation SOURCES.yml doesn't know, a `see` page that doesn't exist, or a term
listed twice. The `patterns` (the records' notations: a time with its zone letter, a grid reference, a kana code, an
attack sheet's angles) are checked too: the regular expression compiles, the `example` matches all of it, no `not` form
matches anywhere, the `see` page exists and its $n refer to groups the pattern has, the ids are unique.

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
PATTERN_FIELDS = {"id", "name", "pattern", "example", "not", "says", "source", "see"}


def see_page(see):
    """'zones.html?zone=$2' -> True if the page is in site/"""
    return (SITE / see.split("?")[0].split("#")[0]).exists()


def cite_all(t, where, srcs, problems, cited):
    """An entry's `source` resolved to [{cite, href, short, title}], each problem noted"""
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
    return out


def check_pattern(p, where):
    """The problems with one `patterns` entry (its fields, its regular expression against its example and `not`
    forms, its `see` page and $n), as strings."""
    problems = [f"{where}: unknown field {k!r}" for k in sorted(set(p) - PATTERN_FIELDS)]
    for k in ("id", "name", "pattern", "example", "says"):
        if not p.get(k):
            problems.append(f"{where}: needs `{k}`")
    if not isinstance(p.get("pattern"), str):
        return problems
    try:
        re_ = re.compile(p["pattern"])
    except re.error as e:
        return problems + [f"{where}: pattern does not compile: {e}"]
    if re.search(r"\\[pPbBw]|\(\?[a-zA-Z]+[:)]|\(\?P<|\(\?<[A-Za-z]", p["pattern"]):
        problems.append(f"{where}: pattern uses \\p, \\b, \\w, a flag or a named group, which JavaScript and Python read differently")
    ex = str(p.get("example") or "")
    if ex and not re_.fullmatch(ex):
        problems.append(f"{where}: example {ex!r} does not match the whole pattern")
    for form in p.get("not") or []:
        if re_.search(str(form)):
            problems.append(f"{where}: {form!r} matches, and must not")
    see = p.get("see")
    if see:
        if not see_page(see):
            problems.append(f"{where}: see {see!r} is not a page in site/")
        for n in re.findall(r"\$(\d)", see):
            if int(n) > re_.groups:
                problems.append(f"{where}: see refers to ${n}, but the pattern has {re_.groups} groups")
    return problems


def build():
    """-> (the JSON's data, problems, every citation used)"""
    g = records.load_yaml(YML) or {}
    srcs = sources()
    problems, cited, seen, terms = [], [], set(), []
    patterns, ids = [], set()
    for n, p in enumerate(g.get("patterns") or [], 1):
        where = f"{records.rel(YML)} pattern #{n} ({p.get('id', '?')})"
        problems += check_pattern(p, where)
        if p.get("id") in ids:
            problems.append(f"{where}: id listed twice")
        ids.add(p.get("id"))
        out = cite_all(p, where, srcs, problems, cited)
        patterns.append({k: v for k, v in {"id": p.get("id"), "name": p.get("name"), "pattern": p.get("pattern"),
                                            "example": p.get("example"), "says": " ".join(str(p.get("says") or "").split()),
                                            "see": p.get("see"), "sources": out}.items() if v})
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
        out = cite_all(t, where, srcs, problems, cited)
        terms.append({k: v for k, v in {"term": t["term"], "match": t.get("match"), "unless": t.get("unless"),
                                         "says": " ".join(t["says"].split()),
                                         "see": t.get("see"), "sources": out}.items() if v})
    return {"ships": g.get("ships") or {}, "terms": terms, "patterns": patterns}, problems, cited


def main():
    data, problems, cited = build()
    for p in problems:
        print(f"PROBLEM: {p}")
    text = json.dumps(data, indent=1, ensure_ascii=False) + "\n"
    if sys.argv[1:2] == ["check"]:
        stale = not OUT.exists() or OUT.read_text(encoding="utf-8") != text
        if stale:
            print(f"{records.rel(OUT)} is out of date: run uv run tools/build_glossary.py")
        print(f"{len(data['terms'])} terms, {len(data['patterns'])} patterns, {len(cited)} citations, {len(problems)} problems")
        sys.exit(1 if problems or stale else 0)
    if problems:
        print(f"{len(problems)} problems; nothing written")
        sys.exit(1)
    OUT.write_text(text, encoding="utf-8")
    print(f"{len(data['terms'])} terms, {len(data['patterns'])} patterns, {len(cited)} citations; wrote {records.rel(OUT)}")


if __name__ == "__main__":
    main()
