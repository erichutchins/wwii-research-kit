"""A National Archives page image, by citation, through the kit's shared scan cache.

The cache is the one the kit's tools fill (`<cache>/nara/rg<group>-<naid>/`), so a page already downloaded by
tools/nara.py or tools/morning_reports.py is used as it is. Both tools' folder layouts are read:

  tools/nara.py              record.json = the catalog's own record (with `digitalObjects`); pNN.jpg; urls.txt "NN url"
  tools/morning_reports.py   record.json = {naId, title, pages: [[objectId, url], ...]}; p0712.jpg; urls.txt "0712 url"

A page not in the cache is downloaded in its original format (a morning-report roll's pages are TIFFs) beside the
others, and its URL added to urls.txt, so the tools see it too.
"""
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

from . import paths
from .cite import Cite

API = "https://catalog.archives.gov/proxy/v3/records/search"   # the catalog front end's own, unauthenticated
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".tif", ".tiff", ".png"}


def _get(url: str, tries: int = 4, timeout: int = 90) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "wwii-book (research kit)"})
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception:
            if attempt == tries - 1:
                raise
            time.sleep(5 * (attempt + 1))
    raise AssertionError("unreachable")


def catalog_record(naid: str) -> dict | None:
    body = json.loads(_get(f"{API}?{urllib.parse.urlencode({'naId': naid, 'allowLegacyOrgNames': 'true'})}"))
    hits = body["body"]["hits"]["hits"]
    return hits[0]["_source"]["record"] if hits else None


def folder(cite: Cite) -> Path:
    """The item's cache folder: the one already there (whatever group it was filed under), or rg<group>-<naid>."""
    base = paths.cache() / "nara"
    found = sorted(f for f in base.glob(f"rg*-{cite.item}") if f.is_dir()) if base.exists() else []
    return found[0] if found else base / f"rg{cite.group}-{cite.item}"


def _page_no(path: Path) -> int | None:
    stem = path.stem
    return int(stem[1:]) if stem[:1] == "p" and stem[1:].isdigit() else None


def cached_image(cite: Cite) -> Path | None:
    d = folder(cite)
    if not d.exists():
        return None
    for f in d.iterdir():
        if f.suffix.lower() in IMAGE_SUFFIXES and _page_no(f) == cite.page and f.stat().st_size > 0:
            return f
    return None


def page_url(cite: Cite) -> str:
    """The page's public image URL: from urls.txt, then record.json (either layout), then the catalog."""
    d = folder(cite)
    urls = d / "urls.txt"
    if urls.exists():
        for line in urls.read_text().splitlines():
            n, _, url = line.strip().partition(" ")
            if n.isdigit() and int(n) == cite.page and url:
                return url.strip()
    rec_path = d / "record.json"
    rec = json.loads(rec_path.read_text()) if rec_path.exists() else None
    if rec is None:
        rec = catalog_record(cite.item)
        if rec is None:
            raise LookupError(f"{cite.text}: no catalog record {cite.item}")
        d.mkdir(parents=True, exist_ok=True)
        rec_path.write_text(json.dumps(rec, indent=1))
    if "pages" in rec:                       # tools/morning_reports.py's layout
        pages = [p[1] for p in rec["pages"]]
    else:                                    # the catalog's own record
        pages = [o["objectUrl"] for o in rec.get("digitalObjects", [])]
    if not 1 <= cite.page <= len(pages):
        raise LookupError(f"{cite.text}: the item has {len(pages)} pages")
    return pages[cite.page - 1]


def page_image(cite: Cite) -> Path:
    """The page's scan, from the cache or downloaded into it."""
    hit = cached_image(cite)
    if hit:
        return hit
    url = page_url(cite)
    d = folder(cite)
    d.mkdir(parents=True, exist_ok=True)
    width = 4 if cite.group == 64 else 2     # each tool's own numbering: p0712 for a roll, p16 for a report
    suffix = Path(urllib.parse.urlparse(url).path).suffix.lower() or ".jpg"
    dest = d / f"p{cite.page:0{width}d}{suffix}"
    dest.write_bytes(_get(url))
    with (d / "urls.txt").open("a") as f:
        f.write(f"{cite.page:0{width}d} {url}\n")
    return dest
