"""WWII Army morning reports (NARA RG 64, series 85713825): find a unit's or
a soldier's pages, read the catalog's OCR, and download page scans.

A morning report is one form per company/battery per day: date, STATION,
ORGANIZATION, the soldiers whose status changed (serial number, name,
grade, what happened), and a RECORD OF EVENTS. The catalog holds them as
microfilm rolls of 1,000-4,000 pages, filmed month by month in unit-number
order. Online: Jan 1940 - Dec 1944. 1945-46 are microfilm only (St. Louis).

The catalog front end uses these unauthenticated endpoints:
  /proxy/v3/records/search?q=...&ancestorNaId=85713825   full-text search -> rolls
  /proxy/metadata/naid-availability/naid/<roll>?q=...     -> objectIds of matching pages
  /proxy/extractedText/<roll>?objectId=<id>               -> one page's OCR

A roll is a "file unit" with its own NAID. Pages are numbered 1..N in the
order the catalog viewer shows them (its objectPage), which is how they're
cited: rg64-<rollNaId>/p0960 is https://catalog.archives.gov/id/<roll>?objectPage=960.

Commands:
  search "<text>" [YYYY-MM]          rolls whose OCR contains the phrase
  pages <roll> "<text>"              pages in a roll containing the phrase, with date/unit/station
  serial <serial> [...]              every page that mentions a soldier's serial number
  scan <roll> [step]                 sample every Nth page (default 100): which units, in order
  unit <roll> "<regex>" [step]       find a unit's run of pages, cache their OCR, list them
  locate "<phr>|<phr>" "<regex>" YYYY-MM YYYY-MM
                                     a unit's pages month by month -> sources/drafts/*.csv
  text <roll> <pages>                print cached/fetched OCR, e.g. 918-966,970
  changes <draft.csv> [skip-roll...] pages where the OCR'd station changes (read these on the scan)
  fetch <roll> <pages>               download scans -> sources/nara/rg64-<roll>/pNNNN.jpg
  classify <roll> <pages> ["<regex>"] each page's kind from its OCR (spacer, form, panel,
                                     entries, specialists, ration, noocr), with its date and unit as
                                     far as OCR goes, and * where the regex matches: the
                                     triage for 1940 - mid-1943 book-type rolls
  checkdraft <draft.csv> [...]       check a reader's draft (guides/MORNING-REPORTS.md,
                                     "Reading at scale") before its rows go to records/army/

OCR text and scans are cached in sources/nara/rg64-<roll>/ (git-ignored).
Search hits are OCR matches: always confirm on the scan. A soldier only
appears on a report when his status changes, so a missing name proves nothing.
"""
import concurrent.futures as cf
import json
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request

from records import CACHE, rel  # noqa: E402
NARA = CACHE / "nara"
PROXY = "https://catalog.archives.gov/proxy"
SERIES = 85713825
MONTHS = "January February March April May June July August September October November December".split()


def get_json(url, tries=7):
    # The catalog answers bursts with an HTML error page; back off and retry.
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                return json.load(r)
        except Exception as e:
            if attempt == tries - 1:
                raise
            print(f"  retry ({e})", file=sys.stderr)
            time.sleep(5 * 2 ** min(attempt, 4))


def folder(roll):
    return NARA / f"rg64-{roll}"


def record(roll):
    """Roll metadata, cached: title plus the page list (objectId, URL)."""
    path = folder(roll) / "record.json"
    if path.exists():
        return json.loads(path.read_text())
    hits = get_json(f"{PROXY}/v3/records/search?naId_is={roll}&allowLegacyOrgNames=true")["body"]["hits"]["hits"]
    if not hits:
        sys.exit(f"no record {roll}")
    r = hits[0]["_source"]["record"]
    rec = {"naId": r["naId"], "title": r["title"],
           "pages": [[o["objectId"], o["objectUrl"]] for o in r.get("digitalObjects", [])]}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rec))
    return rec


def ocr(roll, n):
    """OCR text of page n (1-based), cached as pNNNN.txt."""
    path = folder(roll) / f"p{n:04d}.txt"
    if path.exists():
        return path.read_text()
    oid = record(roll)["pages"][n - 1][0]
    j = get_json(f"{PROXY}/extractedText/{roll}?objectId={oid}")
    objs = j.get("digitalObjects") or [{}]
    text = objs[0].get("extractedText") or ""
    path.write_text(text)
    return text


def ocr_many(roll, pages, workers=4):
    record(roll)
    with cf.ThreadPoolExecutor(workers) as ex:
        return dict(zip(pages, ex.map(lambda n: ocr(roll, n), pages)))


def header(text):
    """(date, organization, station) as typed on the form, as far as OCR allows."""
    line = lambda label: (re.search(label + r"[ \t]*([^\n]*)", text) or [None, ""])[1].strip()
    org = line(r"ORGANIZATION")
    if not org:
        # Continuation sheets and rosters have no form header; the unit is
        # often typed on the first lines instead. Shown in [brackets].
        for ln in text.split("\n")[:6]:
            if re.search(r"\b(Btry|Battery|Co|Company|Bn|Det|Repl|CA|AAA|Hq)\b", ln):
                org = f"[{ln.strip()[:56]}]"
                break
    station = line(r"STATION") or line(r"OR LOCATION")
    station = re.sub(r"^OR LOCAT\.? ?ION\s*", "", station)
    m = re.search(r"(\d{1,2})\s*[,.]?\s*(" + "|".join(m[:3] for m in MONTHS) + r")[a-z]*[ ,./]*(19\s*4\s*\d|4\d)", text)
    date = ""
    if m:
        year = re.sub(r"\D", "", m.group(3))[-1]
        date = f"194{year}-{[x[:3] for x in MONTHS].index(m.group(2)) + 1:02d}-{int(m.group(1)):02d}"
    return date, org[:60], station[:50]


def parse_pages(spec):
    out = []
    for part in spec.split(","):
        a, _, b = part.partition("-")
        out += range(int(a), int(b or a) + 1)
    return out


def search(text, month=""):
    """Rolls whose OCR contains the phrase -> [(naId, title, pages)], best first."""
    out, page = [], 1
    while True:
        q = urllib.parse.urlencode({"q": f'"{text}"', "ancestorNaId": SERIES, "limit": 100,
                                    "page": page, "allowLegacyOrgNames": "true"})
        hits = get_json(f"{PROXY}/v3/records/search?{q}")["body"]["hits"]
        for h in hits["hits"]:
            r = h["_source"]["record"]
            out.append((r["naId"], r["title"].replace("Morning Reports for ", ""), len(r.get("digitalObjects", []))))
        if len(hits["hits"]) < 100 or page >= 5:
            break
        page += 1
    if month:
        y, m = month.split("-")
        out = [o for o in out if f"{MONTHS[int(m) - 1]} {y}" in o[1]]
    return out


def matching_pages(roll, text):
    """Page numbers in a roll whose OCR contains the phrase."""
    q = urllib.parse.urlencode({"q": f'"{text}"'})
    ids = get_json(f"{PROXY}/metadata/naid-availability/naid/{roll}?{q}"
                   "&commentContribution=&extractedTextContribution=&tagContribution=&transcriptionContribution=").get("ids", [])
    index = {oid: i for i, (oid, _) in enumerate(record(roll)["pages"], 1)}
    return sorted(index[i] for i in ids if i in index)


def show(roll, pages, needle=None):
    texts = ocr_many(roll, pages)
    for n in pages:
        date, org, station = header(texts[n])
        print(f"  rg64-{roll}/p{n:04d}  {date or '?':10}  {org or '-':45}  {station}")
        if needle:
            lines = [ln.strip() for ln in texts[n].split("\n")]
            for i, ln in enumerate(lines):
                if needle in ln.replace(" ", ""):
                    print("      | " + " | ".join(x for x in lines[i:i + 4] if x))


def month_key(title):
    """'January 1940 - July 1943: Roll 964 (2 of 4)' sorts first; then by month."""
    m = re.match(r"(\w+) (\d{4})", title)
    if not m or " - " in title.split(":")[0]:
        return (0, 0, title)
    return (int(m.group(2)), MONTHS.index(m.group(1)) + 1, title)


def cmd_serial(serials):
    for s in serials:
        rolls = search(s)
        print(f"{s}: {len(rolls)} roll parts")
        for roll, title, _ in sorted(rolls, key=lambda r: month_key(r[1])):
            pages = matching_pages(roll, s)
            print(f" {title}  [{roll}]" + ("" if pages else "  (no page-level match)"))
            show(roll, pages, needle=s)


def scan(roll, step):
    rec = record(roll)
    pages = list(range(1, len(rec["pages"]) + 1, step))
    print(f"{rec['title']}: {len(rec['pages'])} pages")
    show(roll, pages)


def form_org(text):
    """The ORGANIZATION line of a form; '' for continuation sheets and orders."""
    org = header(text)[1]
    return "" if org.startswith("[") else org


def run_of(roll, rx, seeds):
    """Pages of one unit's run in a roll part, grown outward from seed pages
    until a few pages in a row carry some other unit's heading. Pages without
    a heading (continuation sheets, orders) don't stop the walk."""
    total = len(record(roll)["pages"])
    found = set()

    def walk(start, d):
        n, misses = start, 0
        while 1 <= n <= total and misses < 4:
            batch = [p for p in range(n, n + 8 * d, d) if 1 <= p <= total]
            texts = ocr_many(roll, batch)
            for p in batch:
                org = form_org(texts[p])
                if rx.search(org):
                    found.add(p); misses = 0
                elif org:
                    misses += 1
                    if misses >= 4:
                        break
            n = batch[-1] + d
    for h in seeds:
        if h not in found:
            walk(h, -1)
            walk(h, +1)
    # Headed pages more than 40 apart are separate runs (e.g. the same
    # heading on another unit); return the longest.
    runs, cur = [], []
    for p in sorted(found):
        if cur and p - cur[-1] > 40:
            runs.append(cur); cur = []
        cur.append(p)
    if cur:
        runs.append(cur)
    best = max(runs, key=len) if runs else []
    return list(range(best[0], best[-1] + 1)) if best else []


def unit(roll, pattern, step):
    """Sample the roll for a unit's heading, then take its whole run."""
    rx = re.compile(pattern, re.I)
    total = len(record(roll)["pages"])
    hits = []
    for n, t in ocr_many(roll, list(range(1, total + 1, step))).items():
        # A sample that lands on a continuation sheet looks ahead to the
        # next page with a heading.
        for p in range(n, min(n + 6, total + 1)):
            org = form_org(t if p == n else ocr(roll, p))
            if org:
                if rx.search(org):
                    hits.append(p)
                break
    if not hits:
        sys.exit(f"no sampled page matches /{pattern}/; try a smaller step")
    pages = run_of(roll, rx, hits)
    print(f"{record(roll)['title']}: /{pattern}/ on pages {pages[0]}-{pages[-1]}")
    show(roll, pages)


def months(start, end):
    y, m = map(int, start.split("-"))
    while f"{y}-{m:02d}" <= end:
        yield f"{y}-{m:02d}"
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def locate(phrases, pattern, start, end):
    """For each month: rolls whose OCR has any of the phrases, ranked by how
    many pages match (the unit's own reports mention it on most pages;
    hospitals and depots only now and then). The best few are checked for a
    heading matching the pattern, and the unit's run is taken from there,
    including the other parts of the same microfilm roll. Writes a draft of
    every page's header (OCR, unchecked) to sources/drafts/<slug>.csv for
    transcription against the scans."""
    rx = re.compile(pattern, re.I)
    rows = []
    for month in months(start, end):
        cands = {roll: title for phrase in phrases for roll, title, _ in search(phrase, month)}

        def count(roll):
            return roll, sorted({p for phrase in phrases for p in matching_pages(roll, phrase)})
        with cf.ThreadPoolExecutor(4) as ex:
            matched = dict(ex.map(count, cands))
        ranked = sorted(matched, key=lambda r: -len(matched[r]))
        runs, rolls_found = [], set()
        for roll in ranked[:6]:
            texts = ocr_many(roll, matched[roll][:200])
            seeds = [p for p in matched[roll][:200] if rx.search(form_org(texts[p]))]
            if seeds:
                runs.append((roll, run_of(roll, rx, seeds)))
                rolls_found.add(re.search(r"Roll \d+", cands[roll])[0])
        # The same roll's other parts, when the run crosses a part boundary.
        for roll in ranked[6:]:
            if re.search(r"Roll \d+", cands[roll])[0] in rolls_found and matched[roll]:
                texts = ocr_many(roll, matched[roll][:200])
                seeds = [p for p in matched[roll][:200] if rx.search(form_org(texts[p]))]
                if seeds:
                    runs.append((roll, run_of(roll, rx, seeds)))
        # The unit's own pages often don't contain the search phrase (the OCR
        # mangles their heading), but its roll is still the best-matching one:
        # sample every 3rd heading across that roll's matched span.
        for roll in ranked[:2] if not runs else []:
            span = matched[roll]
            if not span:
                continue
            sample = list(range(span[0], span[-1] + 1, 3))[:600]
            texts = ocr_many(roll, sample)
            seeds = [p for p in sample if rx.search(form_org(texts[p]))]
            if seeds:
                runs.append((roll, run_of(roll, rx, seeds)))
        if not runs:
            print(f"{month}: not found (top: " + ", ".join(f"{cands[r]} {len(matched[r])}" for r in ranked[:3]) + ")")
        for roll, pages in sorted(runs, key=lambda r: cands[r[0]]):
            print(f"{month}: rg64-{roll} pages {pages[0]}-{pages[-1]}  ({cands[roll]})")
            texts = ocr_many(roll, pages)
            for p in pages:
                date, org, station = header(texts[p])
                rows.append([month, f"rg64-{roll}/p{p:04d}", date, org, station])
    out = CACHE / "drafts" / (re.sub(r"\W+", "-", pattern).strip("-").lower() + ".csv")
    out.parent.mkdir(parents=True, exist_ok=True)
    import csv
    with out.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["month", "page", "date_ocr", "org_ocr", "station_ocr"])
        w.writerows(rows)
    print(f"draft -> {rel(out)} ({len(rows)} pages)")


def changes(draft, skip=()):
    """Pages in a locate draft where the OCR'd station differs from the last
    one kept (fuzzy, so OCR misspellings don't count), plus each month's
    first page: the pages to read on the scan. -> {roll: [pages]}"""
    import csv
    import difflib
    norm = lambda st: re.sub(r"[^a-z0-9]", "", st.lower())
    out, prev, month = {}, "", ""
    for r in csv.DictReader(open(draft)):
        roll, page = r["page"].split("/")
        roll, page = roll.removeprefix("rg64-"), int(page[1:])
        st = norm(r["station_ocr"])
        if roll in skip or r["org_ocr"].startswith("[") or len(st) < 4:
            continue
        if r["month"] != month or difflib.SequenceMatcher(None, st, prev).ratio() < 0.75:
            out.setdefault(roll, []).append(page)
            prev, month = st, r["month"]
    return out


def fetch(roll, pages):
    """Download TIFF scans and convert to JPEG (macOS sips) so the pages and
    crop tools can read them. Keeps the TIFF if sips isn't available."""
    rec = record(roll)
    d = folder(roll)
    sips = shutil.which("sips")
    urls = {}
    path = d / "urls.txt"
    if path.exists():
        for ln in path.read_text().split("\n"):
            if ln.strip():
                n, u = ln.split(" ", 1)
                urls[n] = u
    for n in pages:
        url = rec["pages"][n - 1][1]
        urls[f"{n:04d}"] = url
        jpg, tif = d / f"p{n:04d}.jpg", d / f"p{n:04d}.tif"
        if jpg.exists() and jpg.stat().st_size:
            continue
        for attempt in range(4):
            try:
                urllib.request.urlretrieve(url, tif)
                break
            except Exception as e:
                print(f"  retry p{n:04d} ({e})", file=sys.stderr)
                time.sleep(5 * (attempt + 1))
        if sips:
            subprocess.run([sips, "-s", "format", "jpeg", "-s", "formatOptions", "85", str(tif), "--out", str(jpg)],
                           check=True, capture_output=True)
            tif.unlink()
    path.write_text("".join(f"{n} {u}\n" for n, u in sorted(urls.items())))
    print(f"{rec['title']}: {len(pages)} pages -> {rel(d)}")


# -- Book-type rolls (1940 - mid-1943) ---------------------------------------
# These reports were bound books: a wartime month may be one sideways "Station and
# record of events" panel, the unit's name on the month's first page, and between
# them name entries, rosters, and specialist and ration tables. The OCR finds some
# of it; `classify` says what each page is, so a reader fetches only the pages that
# matter. Kinds, from the OCR text: a guide, not a reading (a panel whose heading the OCR
# missed shows as `entries`, and OCR dates are often wrong), so confirm on the thumbnails:
KINDS = [
    ("spacer", r"SPACER|AG\s+RAC\s*M"),  # the filmer's target between units: a run's edge
    ("panel", r"STATION\s+AND\s+RECORD"),
    ("form", r"MORNING\s+REPORT"),
    ("specialists", r"Specialists\s+Present"),
    ("ration", r"RATION\s+(ACCOUNT|RETURN)|Messing\s+with"),
]


def kind(text):
    if len(text.strip()) < 25:
        return "noocr"
    for k, rx in KINDS:
        if re.search(rx, text, re.I):
            return k
    return "entries"


def classify(roll, pages, pattern=None):
    rx = re.compile(pattern, re.I) if pattern else None
    print(f"{record(roll)['title']}")
    print("page   kind         date        match  unit (OCR) | first words")
    for n, t in ocr_many(roll, pages).items():
        date, org, _ = header(t)
        first = " ".join(t.split())[:60]
        hit = "*" if rx and rx.search(t) else ""
        print(f"p{n:04d}  {kind(t):12} {date or '-':11} {hit:6} {org or '-'} | {first}")


DRAFT_COLS = ["unit", "roll", "page", "kind", "month", "days", "station", "org", "read", "note"]


def checkdraft(paths):
    """A reader's draft: one row per station read, its page, as typed. Problems
    are printed; the exit status is the count, so a script can gate on it."""
    import csv
    bad = 0
    for path in paths:
        rows = list(csv.DictReader(open(path, encoding="utf-8")))
        cols = list(rows[0].keys()) if rows else []
        if None in cols:
            print(f"{path}: a row has more fields than the header: quote any field with a comma in it"); bad += 1
            continue
        if cols != DRAFT_COLS:
            print(f"{path}: columns {cols} != {DRAFT_COLS}"); bad += 1
            continue
        for i, r in enumerate(rows, 2):
            where = f"{path}:{i}"
            def err(msg):
                nonlocal bad
                print(f"{where}: {msg}"); bad += 1
            if not re.fullmatch(r"\d{6,12}", r["roll"]): err(f"roll {r['roll']!r}")
            if not re.fullmatch(r"\d{1,4}", r["page"]): err(f"page {r['page']!r}")
            elif not (NARA / f"rg64-{r['roll']}" / f"p{int(r['page']):04d}.jpg").exists():
                err(f"page not fetched (read it on the scan): rg64-{r['roll']}/p{int(r['page']):04d}")
            if r["kind"] not in ("form", "panel", "entries"): err(f"kind {r['kind']!r}")
            if not re.fullmatch(r"194\d-(0[1-9]|1[0-2])", r["month"]): err(f"month {r['month']!r} (YYYY-MM)")
            if r["days"] and not re.fullmatch(r"\d{1,2}(-\d{1,2})?", r["days"]): err(f"days {r['days']!r}")
            if None in r or None in r.values():
                err("wrong number of fields: quote any field with a comma in it"); continue
            if r["read"] not in ("scan", "scan; org ocr"):
                err("read must be 'scan' (or 'scan; org ocr' when only the unit's name is from the OCR)")
            if not r["station"].strip(): err("no station: leave out a page that gives none")
        print(f"{path}: {len(rows)} rows")
    return bad


if __name__ == "__main__":
    cmd, args = (sys.argv[1], sys.argv[2:]) if len(sys.argv) > 1 else ("", [])
    if cmd == "search" and args:
        for roll, title, n in search(*args[:2]):
            print(f"{roll}\t{n:5d} pp\t{title}")
    elif cmd == "pages" and len(args) == 2:
        show(args[0], matching_pages(*args), needle=args[1])
    elif cmd == "serial" and args:
        cmd_serial(args)
    elif cmd == "scan" and args:
        scan(args[0], int(args[1]) if len(args) > 1 else 100)
    elif cmd == "locate" and len(args) == 4:
        locate(args[0].split("|"), args[1], args[2], args[3])
    elif cmd == "unit" and len(args) >= 2:
        unit(args[0], args[1], int(args[2]) if len(args) > 2 else 25)
    elif cmd == "text" and len(args) == 2:
        for n, t in ocr_many(args[0], parse_pages(args[1])).items():
            print(f"===== rg64-{args[0]}/p{n:04d}\n{t}\n")
    elif cmd == "changes" and args:
        for roll, pages in changes(args[0], skip=args[1:]).items():
            print(roll, ",".join(map(str, pages)))
    elif cmd == "fetch" and len(args) == 2:
        fetch(args[0], parse_pages(args[1]))
    elif cmd == "classify" and len(args) >= 2:
        classify(args[0], parse_pages(args[1]), args[2] if len(args) > 2 else None)
    elif cmd == "checkdraft" and args:
        n = checkdraft(args)
        print(f"{n} problem(s)")
        sys.exit(min(n, 99))
    else:
        sys.exit(__doc__)
