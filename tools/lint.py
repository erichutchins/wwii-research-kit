# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""Lint the kit and its records, in the manner of ruff: rules with codes, one line per finding, settings in a file.

The builds check each dataset on its own terms (build_army, build_seabees, build_engagement, check_sources). This
checks what falls between them: references that point at nothing, things nothing points at, files that differ in
form from their neighbours, records that disagree with each other, and anything private.

Rules (`--explain CODE` for one, `--rules` for all):
  FMT  files: UTF-8 without a BOM, LF line endings, a final newline, no tabs in YAML
  CSV  a CSV's shape: a header with no blanks or repeats, every row as wide as it, no padded cells, ISO dates
  YML  YAML: parses, no key given twice, no value split by an unquoted comma
  REF  references that point at nothing: a page's links and scripts, a deep link's id, a value a page must know
  ORF  orphans: a script or page nothing loads or links, a place, silhouette, source, lane or tool nothing uses
  CON  records that disagree: one unit at two places on one day
  PRV  a term from the private list (names, serial numbers) anywhere in the kit or the records
  ACC  accuracy: a ship's position well inland (needs the land map, fetched once into the cache)

A finding is fixed in the data, or allowed in lint.toml with its reason (an `[[allow]]` entry: code, target, why).
Nothing is fixed automatically: every finding is for a person to look at.

Usage: uv run tools/lint.py [--select FMT,REF] [--ignore ACC] [--statistics] [--explain CODE] [--rules] [PATH...]
       PATHs limit the per-file rules (FMT, CSV, YML, PRV) to those files, as a commit hook passes them.
The family repository adds its own rules through `Lint` and `RULES` here (its scripts/lint.py).
"""
import argparse
import csv
import io
import json
import os
import re
import subprocess
import sys
import tomllib
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import records

KIT = records.KIT
TEXT = {".csv", ".yml", ".yaml", ".md", ".html", ".js", ".css", ".py", ".json", ".toml", ".txt", ".geojson"}
RULES = {}   # code -> (summary, explanation, function(lint) yielding (path, line, message, target))


def rule(code, summary):
    """Register a rule; its docstring is what --explain prints."""
    def deco(fn):
        RULES[code] = (summary, (fn.__doc__ or "").strip(), fn)
        return fn
    return deco


@dataclass
class Finding:
    path: str
    line: int
    code: str
    message: str
    target: str = ""

    def __str__(self):
        return f"{self.path}:{self.line}: {self.code} {self.message}"


@dataclass
class Lint:
    """One repository's files and settings. `root` is where paths are shown from; `repos` are the git work trees
    whose files are linted (the kit and its records, or the family repository)."""
    root: Path
    repos: list
    config: dict = field(default_factory=dict)
    only: set | None = None   # limit the per-file rules to these paths (relative to root)
    config_path: Path | None = None   # its lint.toml
    extra_ids: dict = field(default_factory=dict)   # more deep-link ids for REF002: {pattern: (ids, what)}
    _files: list | None = None

    def files(self, *suffixes):
        if self._files is None:
            out = []
            for repo in self.repos:
                # a hook runs with GIT_DIR and GIT_INDEX_FILE set for its own repository: drop them, or every repository
                # lists that one's files
                env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
                listed = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                                        cwd=repo, capture_output=True, text=True, check=True, env=env).stdout.split("\0")
                out += [repo / f for f in listed if f and (repo / f).is_file()]
            self._files = sorted(set(out))
        fs = [f for f in self._files if not suffixes or f.suffix in suffixes]
        return fs

    def per_file(self, *suffixes):
        """files() limited to the paths given on the command line, for the rules that look at one file at a time"""
        fs = self.files(*suffixes)
        return [f for f in fs if self.only is None or self.rel(f) in self.only]

    def rel(self, p):
        return os.path.relpath(p, self.root)

    def text(self, p):
        try:
            return Path(p).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            return ""

    def csv(self, p):
        """(header, rows as dicts with their line numbers under "__line__")"""
        r = csv.reader(io.StringIO(self.text(p)))
        header = next(r, [])
        rows = []
        for cells in r:
            d: dict = dict(zip(header, cells))
            d["__line__"] = r.line_num
            rows.append(d)
        return header, rows

    def yaml(self, p):
        try:
            return records.load_yaml(p)
        except Exception:
            return None


def line_of(text, needle, start=0):
    i = text.find(needle, start)
    return text.count("\n", 0, i) + 1 if i >= 0 else 1


# ── FMT: files ───────────────────────────────────────────────────────────────

@rule("FMT001", "a text file that isn't UTF-8, or starts with a byte-order mark")
def fmt_encoding(L):
    """Every tool reads UTF-8, and a BOM becomes part of the first column's name in a CSV."""
    for p in L.per_file(*TEXT):
        b = p.read_bytes()
        if b.startswith(b"\xef\xbb\xbf"):
            yield p, 1, "starts with a byte-order mark", ""
        try:
            b.decode("utf-8")
        except UnicodeDecodeError as e:
            yield p, b.count(b"\n", 0, e.start) + 1, "is not UTF-8", ""


@rule("FMT002", "CRLF line endings")
def fmt_crlf(L):
    """Windows line endings make every line of a diff change, and a CSV cell end in a stray \\r."""
    for p in L.per_file(*TEXT):
        b = p.read_bytes()
        if b"\r\n" in b:
            yield p, b.count(b"\n", 0, b.index(b"\r\n")) + 1, "has CRLF line endings", ""


@rule("FMT003", "no newline at the end of the file")
def fmt_eof(L):
    """A file that doesn't end in a newline joins its last line to the next file's first in `cat`, and a CSV appended
    to without one runs two rows together."""
    for p in L.per_file(*TEXT - {".json", ".geojson"}):
        b = p.read_bytes()
        if b and not b.endswith(b"\n"):
            yield p, b.count(b"\n") + 1, "has no newline at the end", ""


@rule("FMT004", "a tab in a YAML file's indentation")
def fmt_yaml_tab(L):
    """YAML forbids tabs in indentation; PyYAML and the pages' js-yaml disagree about some of the places they appear."""
    for p in L.per_file(".yml", ".yaml"):
        for i, ln in enumerate(L.text(p).splitlines(), 1):
            if re.match(r"^ *\t", ln):
                yield p, i, "indents with a tab", ""


ANGLE_QUOTE = re.compile(r"[‹›]|&[lr]saquo;|\\0*203[aA9]\b")


@rule("FMT005", "a single angle quote (‹ ›) in a page, a script or a stylesheet")
def fmt_angle_quote(L):
    """ET Book, the pages' serif, draws its single angle quotes as ligatures: › as "ffl" and ‹ as "ffi" (the roman and
    italic glyphs are the ligatures' outlines; the bold is nearly so). Write → for "on to" (ET Book has none, so the next
    font in the stack draws it), or « » where a quotation needs guillemets."""
    for p in L.per_file(".html", ".js", ".css"):
        for i, ln in enumerate(L.text(p).splitlines(), 1):
            if ANGLE_QUOTE.search(ln):
                yield p, i, "has a single angle quote, which ET Book draws as a ligature (ffl, ffi)", ""


# ── CSV: shape ───────────────────────────────────────────────────────────────

DATE_COLUMNS = re.compile(r"^(date|from|to|from_date|to_date|sailed|arrived|landed|date_fix)$")
DATE = re.compile(r"^(\.\.)?\d{4}(-\d\d(-\d\d)?)?(\.\.)?$")


def is_date_column(values):
    """A column named like a date holds dates when most of its values are (an engagement's positions.csv `from` is a
    position id)."""
    vs = [v for v in values if v]
    return bool(vs) and sum(bool(DATE.match(v)) for v in vs) * 2 > len(vs)


def csvs(L):
    return [p for p in L.per_file(".csv")]


@rule("CSV001", "a header with an empty or repeated column name")
def csv_header(L):
    """A repeated column is silently dropped by every reader that builds a dict of the row."""
    for p in csvs(L):
        header, _ = L.csv(p)
        for name, n in Counter(header).items():
            if n > 1:
                yield p, 1, f"column {name!r} appears {n} times", ""
        if "" in header or any(h != h.strip() for h in header):
            yield p, 1, "has an empty or padded column name", ""


@rule("CSV002", "a row not as wide as the header")
def csv_width(L):
    """A row with too many cells has an unquoted comma in it; one with too few has lost a cell. Either way every column
    after it is read from the wrong place."""
    for p in csvs(L):
        r = csv.reader(io.StringIO(L.text(p)))
        header = next(r, [])
        for cells in r:
            if cells and len(cells) != len(header):
                yield p, r.line_num, f"has {len(cells)} cells, the header {len(header)}", ""


@rule("CSV003", "a cell with leading or trailing spaces")
def csv_padding(L):
    """`Nouméa ` and `Nouméa` are different keys to every join."""
    for p in csvs(L):
        header, rows = L.csv(p)
        for r in rows:
            for k in header:
                v = r.get(k, "")
                if v != v.strip() and "\n" not in v:
                    yield p, r["__line__"], f"{k} {v!r} has spaces at its ends", ""


@rule("CSV004", "a date column whose value isn't an ISO date")
def csv_dates(L):
    """Columns named date, from, to, from_date, to_date, sailed, arrived, landed or date_fix hold an ISO date
    (YYYY-MM-DD, or YYYY-MM or YYYY where the record gives no more), optionally open at one end with `..` as in
    relations.csv. Anything else sorts wrongly and won't parse on the pages."""
    for p in csvs(L):
        header, rows = L.csv(p)
        cols = [h for h in header if DATE_COLUMNS.match(h) and is_date_column([r.get(h, "") for r in rows])]
        for r in rows:
            for k in cols:
                v = r.get(k, "")
                if v and not DATE.match(v):
                    yield p, r["__line__"], f"{k} {v!r} isn't an ISO date", ""


# ── YML: YAML ────────────────────────────────────────────────────────────────

def yamls(L):
    return L.per_file(".yml", ".yaml")


def front_matter(L, p):
    """A Markdown file's front matter, parsed, with the line it starts on; (None, 0) if it has none."""
    t = L.text(p)
    if not t.startswith("---\n"):
        return None, 0
    end = t.find("\n---", 4)
    return (t[4:end], 2) if end > 0 else (None, 0)


@rule("YML001", "YAML that doesn't parse, or gives a key twice")
def yml_parse(L):
    """PyYAML keeps the last of two equal keys silently; the pages' js-yaml rejects the whole file. records.load_yaml
    refuses both, and so does this, for every YAML file and every Markdown file's front matter."""
    for p in yamls(L):
        try:
            records.load_yaml(p)
        except Exception as e:
            mark = getattr(e, "problem_mark", None) or getattr(e, "context_mark", None)
            yield p, (mark.line + 1) if mark else 1, f"doesn't load: {str(e).splitlines()[0]}", ""
    for p in L.per_file(".md"):
        fm, start = front_matter(L, p)
        if fm is None:
            continue
        try:
            records.load_yaml_text(fm, p)
        except Exception as e:
            mark = getattr(e, "problem_mark", None)
            yield p, (mark.line + start) if mark else start, f"front matter doesn't load: {str(e).splitlines()[0]}", ""


def walk(v, path=()):
    if isinstance(v, dict):
        for k, x in v.items():
            yield path, k, x
            yield from walk(x, (*path, k))
    elif isinstance(v, list):
        for i, x in enumerate(v):
            yield from walk(x, (*path, i))


@rule("YML002", "a key with no value that reads like the end of a sentence: an unquoted comma split a value")
def yml_split(L):
    """In a flow mapping, `{ n: 1, name: AA action forms, 6 April 1945, area: ... }` is read as a name of "AA action
    forms" and a key "6 April 1945" with no value: the page shows the name cut short, and nothing fails. A key with a
    space in it and no value is almost always this. Quote the value."""
    for p in yamls(L):
        data, text = L.yaml(p), None
        for _path, k, x in walk(data):
            if x is None and isinstance(k, str) and " " in k.strip():
                text = text or L.text(p)
                yield p, line_of(text, k), f"key {k!r} has no value: quote the value it was split from", ""


# ── REF: references that point at nothing ───────────────────────────────────

LINK = re.compile(r"""(?<![\w-])(?:href|src)\s*=\s*["']([^"'#?]+?)(?:[?#][^"']*)?["']""")
SKIP_LINK = re.compile(r"^([a-z]+:|//|\$\{|#|data:)", re.I)


def pages(L):
    return [p for p in L.files(".html") if ".playwright-mcp" not in p.parts]


@rule("REF001", "a page's link, script, stylesheet or image that isn't there")
def ref_links(L):
    """Every `href` and `src` in a page that points at a file of this repository (not another site) must find it.
    Links into the cache (`sources/`, never committed) are skipped: the pages fall back to the archive's copy."""
    for p in pages(L):
        t = L.text(p)
        for m in LINK.finditer(t):
            u = m.group(1)
            if SKIP_LINK.match(u) or "${" in u or "sources/" in u:
                continue
            if not (p.parent / u).resolve().exists():
                yield p, line_of(t, m.group(0)), f"links to {u}, which isn't there", u


def deep_ids(L):
    """The ids each page opens from its address, from the generated indexes: {pattern: (ids, what)}"""
    rec = records.RECORDS
    load = lambda p: json.loads((rec / p).read_text(encoding="utf-8"))
    out = {}
    try:
        out[r"engagement\.html\?e="] = ({x["id"] for x in load("engagements/index.json")}, "engagement")
        # the four theatre pages (theatre.html?t=<id>): the ids site/chapter.js's THEATRES names, and nothing else
        out[r"theatre\.html\?t="] = ({"pacific", "atlantic", "mediterranean", "europe"}, "theatre")
        # the subject pages (subject.html?s=<id or alias>, from the registry); the four old addresses still arrive, by
        # redirect, and are checked the same way while the redirect pages stand
        subjects = load("subjects.json")
        out[r"subject\.html\?s="] = ({s["id"] for s in subjects} | {s["alias"] for s in subjects}, "subject")
        out[r"convoys\.html\?c="] = ({c["id"] for c in load("convoys/convoys.json")["convoys"]}, "convoy")
        ships = load("ships.json")
        out[r"patrols\.html\?ship="] = ({s["key"] for s in ships} | {s["alias"] for s in ships}, "ship")
        out[r"army\.html\?unit="] = ({u["unit"] for u in load("army/army.json")["units"]}, "Army unit")
        out[r"seabees\.html\?unit="] = (set(load("seabees/seabees.json")["units"]), "Seabee battalion")
        out[r"seabees\.html#proj-|(?<![\w.])#proj-"] = ({p["id"] for p in load("seabees/seabees.json")["projects"]},
                                                         "Seabee project")
    except (OSError, KeyError, ValueError):
        pass
    return out


def deep_links(L, ids, files):
    for p in files:
        t = L.text(p)
        for pat, (known, what) in ids.items():
            for m in re.finditer(f"(?:{pat})([A-Za-z0-9%+_.-]+)", t):
                v = m.group(1).replace("%20", " ").replace("+", " ").rstrip(".")
                if v not in known:
                    yield p, line_of(t, m.group(0)), f"links to the {what} {v!r}, which doesn't exist", v


@rule("REF002", "a deep link to a theatre, engagement, subject, convoy, ship, unit or project that doesn't exist")
def ref_deep(L):
    """`theatre.html?t=…` (one of the four theatres), `engagement.html?e=…`, `subject.html?s=…` (a boat, ship, unit,
    battalion, convoy or command, by id or alias) and,
    while their redirect pages stand, `convoys.html?c=…`, `patrols.html?ship=…`, `army.html?unit=…`, `seabees.html?unit=…`
    and `#proj-…` in a page, a script or a record must name one that exists: the pages fall back to a default without a
    word, so a broken link shows the wrong thing rather than an error. Ids come from the generated indexes
    (engagements/index.json, subjects.json, convoys.json, ships.json, army.json, seabees.json): rebuild them first."""
    files = [p for p in L.files(".html", ".js", ".md", ".yml") if ".playwright-mcp" not in p.parts]
    yield from deep_links(L, deep_ids(L) | L.extra_ids, files)


@rule("REF003", "a position whose source the patrols panel has no class for")
def ref_position_kind(L):
    """The patrols panel (site/panels/patrols.js, the subject page's records depth for a boat or a ship) draws each
    position by its `source` (CLASS: bt, noon, diary, attack...). A source it doesn't know breaks the whole panel
    (`SHAPE[undefined].type`): ESSEX's and CABOT's `action` rows did, unseen, until the smoke test. Add the kind to CLASS
    and BASE_LABEL in site/panels/patrols.js, or use one it knows."""
    js = KIT / "site/panels/patrols.js"
    m = re.search(r"const CLASS = \{(.*?)\};", js.read_text(encoding="utf-8"), re.S) if js.exists() else None
    if not m:
        return
    known = set(re.findall(r"(\w+):", m.group(1)))
    for v in records.vessels():
        for p in sorted(v.glob("**/positions.csv")):
            _, rows = L.csv(p)
            for r in rows:
                if r.get("source") and r["source"] not in known:
                    yield p, r["__line__"], f"source {r['source']!r} isn't one patrols.js draws ({', '.join(sorted(known))})", r["source"]


# ── ORF: orphans ─────────────────────────────────────────────────────────────

def words_outside(L, exclude, suffixes=(".html", ".js", ".css", ".md", ".yml", ".csv", ".py", ".toml")):
    """The text of every file but `exclude`, joined, for 'does anything mention it' checks."""
    ex = {Path(e).resolve() for e in exclude}
    return "\n".join(L.text(p) for p in L.files(*suffixes) if p.resolve() not in ex and "json" not in p.suffix)


def mentioned(word, text, pattern=None, after=r"[\w-]"):
    """Whether `word` (or the regex `pattern`) appears in `text` as a whole word. The boundary before it is checked
    after the match: a pattern that starts with a lookbehind can't use re's fast scan for its literal start."""
    pat = re.compile((pattern or re.escape(word)) + f"(?!{after})")
    return any(m.start() == 0 or not re.match(r"[\w-]", text[m.start() - 1]) for m in pat.finditer(text))


@rule("ORF001", "a script or stylesheet in site/ that no page loads")
def orf_assets(L):
    """A file no page loads is dead code, or a page lost its <script> tag. Tests (`*.test.js`) are exempt."""
    site = KIT / "site"
    loaded = set()
    for p in pages(L):
        for m in LINK.finditer(L.text(p)):
            loaded.add((p.parent / m.group(1)).resolve())
    js = "\n".join(L.text(p) for p in [*site.glob("*.js"), *site.glob("panels/*.js")])
    for p in sorted([*site.glob("*.js"), *site.glob("panels/*.js"), *site.glob("*.css"), *site.glob("fonts/*.css")]):
        if p.name.endswith(".test.js") or p.resolve() in loaded:
            continue
        if re.search(rf"""["'/]{re.escape(p.name)}["'?]""", js) or re.search(rf"@import[^;]*{re.escape(p.name)}",
                                                                           "\n".join(L.text(c) for c in site.glob("**/*.css"))):
            continue   # loaded by a script or imported by a stylesheet
        yield p, 1, f"{p.name} is loaded by no page", p.name


REDIRECT = re.compile(r"""<meta\s+http-equiv=["']refresh["']""", re.I)
# a redirect that must map its parameters (patrols.html?ship=X&patrol=N -> subject.html?s=X&period=N): one script, which
# only rewrites location
REDIRECT_SCRIPT = re.compile(r"<script>(?:(?!</script>).)*location\.replace\((?:(?!</script>).)*</script>", re.S)


def is_redirect(text):
    """A page kept at an old address whose whole job is to send the reader on: a meta refresh with no script, or a page
    whose only script rewrites location (and loads nothing else)."""
    if REDIRECT.search(text) and "<script" not in text:
        return True
    return text.count("<script") == 1 and bool(REDIRECT_SCRIPT.search(text)) and "<link" not in text and "<svg" not in text


@rule("ORF002", "a page in site/ that no other page links to")
def orf_pages(L):
    """A page nothing links to can only be found by its address. index.html is exempt, and so is a redirect (a page
    that is only a `<meta http-equiv="refresh">` to another, or whose only script rewrites location to carry the old
    address's parameters across, kept at an old address so links from outside still arrive): being found by its address
    is its whole job."""
    site = KIT / "site"
    for p in sorted(site.glob("*.html")):
        if p.name == "index.html":
            continue
        t = L.text(p)
        if is_redirect(t):
            continue
        others = "\n".join(L.text(q) for q in [*site.glob("*.html"), *site.glob("*.js")] if q != p)
        if not re.search(rf"""["'/]{re.escape(p.name)}["'?#]""", others):
            yield p, 1, f"{p.name} is linked from no other page", p.name


@rule("ORF003", "a place in places.csv that no row uses")
def orf_places(L):
    """Each places.csv (army, seabees) is the gazetteer of its folder's rows. A place no station, action, project or
    route names is left over from a renamed or removed row, or the row that should use it misspells it."""
    for folder in ("army", "seabees"):
        d = records.RECORDS / folder
        gaz = d / "places.csv"
        if not gaz.exists():
            continue
        used = set()
        for p in d.glob("*.csv"):
            if p.name != "places.csv":
                _, rows = L.csv(p)
                used |= {v for r in rows for k, v in r.items() if k != "__line__"}
        for p in d.glob("**/*.md"):
            used |= {m.strip() for m in re.findall(r"(?:station|place):\s*([^\n#]+)", L.text(p))}
        _, rows = L.csv(gaz)
        for r in rows:
            if r["place"] not in used:
                yield gaz, r["__line__"], f"place {r['place']!r} is used by no row", r["place"]


@rule("ORF004", "a silhouette that nothing draws")
def orf_silhouettes(L):
    """A shape in silhouettes.yml that no ship, convoy, engagement, Army crossing or page names. It may be waiting for
    its first use (allow it in lint.toml and say so) or its user was renamed."""
    path = records.RECORDS / "silhouettes/silhouettes.yml"
    data = L.yaml(path) or {}
    shapes = data.get("silhouettes", data) if isinstance(data, dict) else {}
    text = words_outside(L, [path, records.RECORDS / "silhouettes/silhouettes.json"])
    src = L.text(path)
    for k in shapes:
        if isinstance(k, str) and not mentioned(k, text):
            yield path, line_of(src, f"\n  {k}:"), f"silhouette {k!r} is drawn by nothing", k


@rule("ORF005", "a source in SOURCES.yml that nothing cites")
def orf_sources(L):
    """An entry nothing cites: no citation anywhere (a row, a note, a page, a guide, a reference file) matches its
    `match` pattern or names its key, and no page links to its `url`. A series entry (`series_of`) is described by its
    parent and exempt. check_sources.py lists the ones no row cites; this looks everywhere."""
    path = records.RECORDS / "SOURCES.yml"
    data = L.yaml(path) or {}
    text = words_outside(L, [path, records.RECORDS / "citations.json"])
    src = L.text(path)
    for k, e in data.items():
        if not isinstance(k, str) or not isinstance(e, dict) or e.get("series_of"):
            continue
        names = [k]
        if e.get("short"):
            names.append(str(e["short"]))
        if str(e.get("cite", "")).startswith("in notes, "):
            names.append(e["cite"][len("in notes, "):].split(",")[0])
        if e.get("title"):
            names.append(re.sub(r"^The ", "", str(e["title"]).split(":")[0].split(" (")[0]))
        if any(n in text and mentioned(n, text) for n in names if len(n) > 3):
            continue
        if e.get("match") and mentioned("", text, e["match"].lstrip("^").rstrip("$"), after=r"\w"):
            continue
        if e.get("url") and e["url"].rstrip("/") in text:
            continue
        yield path, line_of(src, f"\n{k}:") + 1, f"source {k!r} is cited by nothing", k


@rule("ORF006", "a lane node that no convoy's route uses")
def orf_lanes(L):
    """lanes.yml's ports and waypoints exist for the convoys' `route:` lists. A node none uses is left over or
    misspelled in a route (build_engagement fails on an unknown id in a route, not on an unused node)."""
    path = KIT / "reference/lanes/lanes.yml"
    data = L.yaml(path) or {}
    routes = ",".join(re.findall(r"^route:\s*\[([^\]]*)\]", "\n".join(L.text(p) for p in (records.RECORDS / "convoys").glob("*/convoy.md")), re.M))
    used = {x.strip() for x in routes.split(",")}
    src = L.text(path)
    for k in (data.get("nodes") or {}):
        if k not in used:
            yield path, line_of(src, f"  {k}:"), f"node {k!r} is on no convoy's route", k


@rule("ORF007", "a tool that nothing mentions")
def orf_tools(L):
    """Every tool is documented (CLAUDE.md, a guide, a README, a skill) or used by another tool or the CI. One that
    nothing mentions is forgotten, or its documentation is missing."""
    tools = KIT / "tools"
    text = "\n".join(L.text(p) for p in L.files(".md", ".py", ".yml", ".toml", ".js", ".html"))
    for p in sorted(tools.glob("*.py")):
        others = text.replace(L.text(p), "")
        if not mentioned(p.stem, others):
            yield p, 1, f"{p.name} is mentioned nowhere else", p.name


# ── CON: records that disagree ───────────────────────────────────────────────

def two_places(L, path, keys, cite, place="place", skip=lambda r: False):
    _, rows = L.csv(path)
    seen = defaultdict(list)
    for r in rows:
        if r.get(place) and r.get("date") and not skip(r):
            seen[tuple(r.get(k, "") for k in keys)].append(r)
    for key, rs in seen.items():
        by = defaultdict(set)   # place -> the records (items, without the page) that put it there
        for r in rs:
            by[r[place]] |= {re.sub(r"/p[\w-]*$", "", c.strip()) for c in r.get(cite, "").split(";") if c.strip()}
        cites = [c for cs in by.values() for c in cs]
        if len(by) > 1 and len(set(cites)) == len(cites):   # no record gives two of the places: they disagree
            said = "; ".join(f"{p} ({', '.join(sorted(c))})" for p, c in sorted(by.items()))
            yield path, rs[-1]["__line__"], f"{' '.join(key)}: {len(by)} records give {len(by)} places ({said}): check which", " ".join(key)


@rule("CON001", "two records put one unit at two places on the same day")
def con_stations(L):
    """Station rows for one unit (and part) on one date at different places, each from a different record. One
    record giving two places in a day is a move made that day, and passes (the 189th FA's history, 28 April 1945:
    Thierham, then Doderhof); two records disagreeing is for a person to settle: a slip, a stale report, or a part of
    the unit that needs its own `part`. A Seabee row marked `last_day: yes` and an Army row with a `when` are skipped.
    Never fixed automatically."""
    army = records.RECORDS / "army/stations.csv"
    if army.exists():
        yield from two_places(L, army, ("unit", "date"), "page", skip=lambda r: bool(r.get("when")))
    sb = records.RECORDS / "seabees/stations.csv"
    if sb.exists():
        yield from two_places(L, sb, ("unit", "part", "date"), "ref", skip=lambda r: r.get("last_day") == "yes")


# ── PRV: privacy ─────────────────────────────────────────────────────────────

def private_terms():
    """The private list: one term a line (a relative's name in the forms it's written, a serial number), `#` comments.
    It lives in the cache (never committed): `$WWII_PRIVATE`, else sources/private-terms.txt. The family repository
    writes it from its people (scripts/lint.py --write-private). Without it PRV001 checks nothing, and says so."""
    p = Path(os.environ.get("WWII_PRIVATE") or records.CACHE / "private-terms.txt")
    if not p.exists():
        return None, p
    terms = [t.strip() for t in p.read_text(encoding="utf-8").splitlines() if t.strip() and not t.startswith("#")]
    return terms, p


@rule("PRV001", "a term from the private list (a relative's name, a serial number)")
def prv_terms(L):
    """No relative's name, serial number or personal path in a public repository (the kit and the records). The terms
    come from the private list (see private_terms); matching ignores case and runs of spaces, and a term matches only
    as a whole word. A finding is fixed by rewording the file with the unit's name instead; never allowed in lint.toml."""
    terms, path = private_terms()
    if terms is None:
        print(f"PRV001: no private list at {path}; nothing checked", file=sys.stderr)
        return
    alts = sorted((r"\s+".join(re.escape(w) for w in t.split()) for t in terms), key=len, reverse=True)
    pat = re.compile(r"(?<![\w])(?:" + "|".join(alts) + r")(?![\w])", re.I)   # one pass over each file
    for p in L.per_file():
        if p.suffix not in TEXT:
            continue
        t = L.text(p)
        for n in sorted({t.count("\n", 0, m.start()) + 1 for m in pat.finditer(t)}):
            yield p, n, "names a term on the private list", ""   # never print the term


# ── ACC: accuracy ────────────────────────────────────────────────────────────

LAND_URL = "https://cdn.jsdelivr.net/npm/world-atlas@2/land-10m.json"   # Natural Earth 1:10m land, as the pages draw


def land_rings():
    """Natural Earth's 1:10m land as rings of (lon, lat), from the cache (fetched once from the CDN the pages use)."""
    cache = records.CACHE / "lint/land-10m.json"
    if not cache.exists():
        cache.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(LAND_URL, timeout=60) as r:
            cache.write_bytes(r.read())
    topo = json.loads(cache.read_text())
    sx, sy = topo["transform"]["scale"]
    tx, ty = topo["transform"]["translate"]
    arcs = []
    for arc in topo["arcs"]:
        x = y = 0
        pts = []
        for dx, dy in arc:
            x += dx
            y += dy
            pts.append((x * sx + tx, y * sy + ty))
        arcs.append(pts)

    def ring(ix):
        pts = []
        for i in ix:
            a = arcs[i] if i >= 0 else arcs[~i][::-1]
            pts += a[1:] if pts else a
        return pts

    rings = []
    for g in topo["objects"]["land"]["geometries"]:
        polys = g["arcs"] if g["type"] == "MultiPolygon" else [g["arcs"]]
        for poly in polys:
            for k, r in enumerate(poly):
                pts = ring(r)
                xs, ys = [p[0] for p in pts], [p[1] for p in pts]
                rings.append((min(xs), min(ys), max(xs), max(ys), pts, k > 0))
    return rings


def on_land(rings, lon, lat):
    inside = False
    for x0, y0, x1, y1, pts, _hole in rings:
        if not (x0 <= lon <= x1 and y0 <= lat <= y1):
            continue
        c = False
        for (ax, ay), (bx, by) in zip(pts, pts[1:] + pts[:1]):
            if (ay > lat) != (by > lat) and lon < (bx - ax) * (lat - ay) / (by - ay) + ax:
                c = not c
        if c:
            inside = not inside   # a hole inside its polygon cancels it
    return inside


@rule("ACC001", "a ship's track position more than 3 nautical miles inland")
def acc_land(L):
    """Every position on a boat's or ship's track (positions.csv rows on the track, after any fix) and every logged
    position of a Seabee voyage, against Natural Earth's 1:10m land. A position is flagged only when it and every point
    3 nautical miles around it are on land, so a harbour, a narrow strait or the coarse coastline doesn't count; one
    that is flagged is usually a typing slip (a degree, N for S) to fix with lat_fix/lon_fix and a fix_note, or to leave
    off the track (`on_track: no`) when the right figure can't be told. A river port is a true position the coastline
    is too coarse for: allow it in lint.toml by its coordinates ("40.70, -73.97"), once for every row there."""
    import check_track

    rings = land_rings()
    d = 3 / 60
    ring8 = [(d * a, d * b) for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1), (.7, .7), (-.7, .7), (.7, -.7), (-.7, -.7))]

    def inland(lat, lon):
        return on_land(rings, lon, lat) and all(on_land(rings, lon + dx, lat + dy) for dx, dy in ring8)

    for v in records.vessels():
        for p in sorted(v.glob("**/positions.csv")):
            _, raw = L.csv(p)
            for r in raw:
                if r.get("on_track") == "no":
                    continue
                lat = check_track.parse_coord(r.get("lat_fix") or r.get("lat_raw", ""))
                lon = check_track.parse_coord(r.get("lon_fix") or r.get("lon_raw", ""))
                if lat is not None and lon is not None and inland(lat, lon):
                    yield p, r["__line__"], f"{r.get('date', '')} {r.get('time', '')} at {lat:.2f}, {lon:.2f} is inland", f"{lat:.2f}, {lon:.2f}"
    vp = records.RECORDS / "seabees/voyage_positions.csv"
    if vp.exists():
        import build_seabees

        _, raw = L.csv(vp)
        for r in raw:
            if r.get("on_track") == "no":
                continue
            lat = build_seabees.parse_coord(r.get("lat_fix") or r.get("lat", ""))
            lon = build_seabees.parse_coord(r.get("lon_fix") or r.get("lon", ""))
            if lat is not None and lon is not None and inland(lat, lon):
                yield vp, r["__line__"], f"{r.get('date', '')} {r.get('time', '')} at {lat:.2f}, {lon:.2f} is inland", f"{lat:.2f}, {lon:.2f}"


# ── the runner ───────────────────────────────────────────────────────────────

def selected(code, select, ignore):
    pick = lambda xs: any(code.startswith(x) for x in xs)
    return pick(select) and not pick(ignore)


def run(L, select, ignore, statistics=False):
    allows = L.config.get("allow", [])
    found, used = [], set()
    for code in sorted(RULES):
        if not selected(code, select, ignore):
            continue
        for path, line, msg, target in RULES[code][2](L):
            rel = L.rel(path)
            hit = next((i for i, a in enumerate(allows) if a["code"] == code and a["target"] in (target, f"{rel}:{target}", rel)
                        and code != "PRV001"), None)
            if hit is not None:
                used.add(hit)
                continue
            found.append(Finding(rel, line, code, msg, target))
    if L.only is None:   # an allow that matches nothing is itself an orphan (as ruff's RUF100, an unused noqa)
        for i, a in enumerate(allows):
            if i not in used and selected(a["code"], select, ignore):
                found.append(Finding(L.rel(L.config_path or L.root), 1, "LNT001", f"allow {a['code']} {a['target']!r} matches nothing: remove it"))
    found.sort(key=lambda f: (f.path, f.line, f.code))
    if statistics:
        for code, n in Counter(f.code for f in found).most_common():
            summary = RULES[code][0] if code in RULES else "an allow that matches nothing"
            print(f"{n:5d}  {code}  {summary}")
    else:
        for f in found:
            print(f)
    print(f"Found {len(found)} problem{'s' * (len(found) != 1)}." if found else "All checks passed.")
    return found


def main(L=None, argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--select", help="comma-separated codes or prefixes (default: lint.toml's select)")
    ap.add_argument("--ignore", help="comma-separated codes or prefixes to skip")
    ap.add_argument("--statistics", action="store_true", help="count the findings by rule")
    ap.add_argument("--explain", metavar="CODE")
    ap.add_argument("--rules", action="store_true", help="list every rule")
    a = ap.parse_args(argv)
    if a.explain:
        s, doc, _ = RULES[a.explain]
        print(f"{a.explain}: {s}\n\n{doc}")
        return 0
    if a.rules:
        for code in sorted(RULES):
            print(f"{code}  {RULES[code][0]}")
        return 0
    if L is None:
        L = Lint(KIT, [KIT, records.RECORDS], config_path=KIT / "lint.toml")
    cfg = L.config_path
    L.config = tomllib.loads(cfg.read_text(encoding="utf-8")) if cfg and cfg.exists() else {}
    select = (a.select or ",".join(L.config.get("select", sorted({c[:3] for c in RULES})))).split(",")
    ignore = (a.ignore or ",".join(L.config.get("ignore", []))).split(",") if (a.ignore or L.config.get("ignore")) else []
    if a.paths:
        L.only = {os.path.relpath(Path(p).resolve(), L.root) for p in a.paths}
    return 1 if run(L, select, ignore, a.statistics) else 0


if __name__ == "__main__":
    sys.exit(main())
