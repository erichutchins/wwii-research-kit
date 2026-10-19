"""Google Books helper: find digitized manuals and reports, read a volume's
access info, and download the PDF when the volume is full view.

Needs GOOGLE_BOOKS_API_KEY (environment or the git-ignored .env in the repo
root); the keyless quota is zero. The key is never printed.

Commands:
  python3 tools/gbooks.py search "intitle:\\"after action report\\" inauthor:\\"Third Army\\"" [--full]
  python3 tools/gbooks.py meta ee9mAAAAMAAJ        title, date, pages, viewability, PDF available?
  python3 tools/gbooks.py fetch ee9mAAAAMAAJ --yes  PDF + pNN.jpg pages -> sources/googlebooks/<id>/

search takes Google Books query syntax (intitle:, inauthor:, inpublisher:,
isbn:); --full limits it to full-view volumes. fetch without --yes only says
what it would download. If Google refuses the signed PDF link, open
https://books.google.com/books?id=<id> and download it by hand into the same
folder. The search-inside text (OCR) of a PDF is a lead: confirm on the scan.
sources/ is not committed.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from records import CACHE, KIT, rel  # noqa: E402
OUT = CACHE / "googlebooks"
API = "https://www.googleapis.com/books/v1/volumes"


def api_key():
    key = os.environ.get("GOOGLE_BOOKS_API_KEY")
    env = next((p for p in (Path.cwd() / ".env", KIT / ".env", KIT.parent / ".env") if p.exists()), KIT / ".env")
    if not key and env.exists():
        for line in env.read_text().splitlines():
            name, _, value = line.partition("=")
            if name.strip() == "GOOGLE_BOOKS_API_KEY":
                key = value.strip().strip("\"'")
    if not key:
        sys.exit("GOOGLE_BOOKS_API_KEY not set (environment or .env)")
    return key


def call(path="", **params):
    params["key"] = api_key()
    url = f"{API}{path}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:  # don't echo the URL: it carries the key
        sys.exit(f"Google Books API: HTTP {e.code} {e.reason}")


def summary(v):
    i, a = v.get("volumeInfo", {}), v.get("accessInfo", {})
    return {"id": v["id"], "title": i.get("title", ""), "authors": i.get("authors", []),
            "publisher": i.get("publisher", ""), "date": i.get("publishedDate", ""),
            "pages": i.get("pageCount"), "viewability": a.get("viewability"),
            "public_domain": a.get("publicDomain"),
            "pdf": a.get("pdf", {}).get("isAvailable", False),
            "snippet": re.sub(r"<[^>]+>|&#39;|&quot;", "", v.get("searchInfo", {}).get("textSnippet", "")),
            "link": f"https://books.google.com/books?id={v['id']}"}


def search(query, full=False):
    params = {"q": query, "maxResults": "40", "printType": "books"}
    if full:
        params["filter"] = "full"
    return [summary(v) for v in call(**params).get("items", [])]


def meta(vid):
    return summary(call("/" + vid))


def fetch(vid, yes=False):
    v = call("/" + vid)
    s = summary(v)
    link = v.get("accessInfo", {}).get("pdf", {}).get("downloadLink")
    if not link:
        sys.exit(f"{vid}: no PDF download link ({s['viewability']}); download by hand from {s['link']}")
    folder = OUT / vid
    pdf = folder / f"{vid}.pdf"
    if not yes and not pdf.exists():
        sys.exit(f"{vid}: {s['title']} ({s['date']}, {s['pages']} pages) would download to "
                 f"{rel(pdf)}; rerun with --yes")
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "meta.json").write_text(json.dumps(s, indent=1, ensure_ascii=False))
    if not pdf.exists():
        req = urllib.request.Request(link, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(req, timeout=300) as r, open(pdf, "wb") as f:
                shutil.copyfileobj(r, f)
        except urllib.error.HTTPError as e:
            pdf.unlink(missing_ok=True)
            sys.exit(f"{vid}: PDF refused (HTTP {e.code}); download by hand from {s['link']}")
    if shutil.which("pdftoppm") and not list(folder.glob("p[0-9]*.jpg")):
        subprocess.run(["pdftoppm", "-r", "110", "-gray", "-jpeg", str(pdf), str(folder / "p")], check=True)
        for f in folder.glob("p-*.jpg"):  # match data's pNN refs
            f.rename(folder / f"p{int(f.stem[2:]):02d}.jpg")
    print(f"{vid}: {s['title']} -> {rel(folder)}")


if __name__ == "__main__":
    cmd, args = (sys.argv[1], sys.argv[2:]) if len(sys.argv) > 1 else ("", [])
    flags = {a for a in args if a.startswith("--")}
    args = [a for a in args if not a.startswith("--")]
    if cmd == "search" and args:
        for r in search(args[0], "--full" in flags):
            print(f"{r['id']}\t{r['date']}\t{r['viewability']}\t{r['pages']}p\t{r['title']} — {r['publisher']}")
            if r["snippet"]:
                print(f"\t\t\t\t… {r['snippet']}")
    elif cmd == "meta" and args:
        print(json.dumps(meta(args[0]), indent=1, ensure_ascii=False))
    elif cmd == "fetch" and args:
        for a in args:
            fetch(a, "--yes" in flags)
    else:
        sys.exit(__doc__)
