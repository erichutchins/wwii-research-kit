"""Japan Center for Asian Historical Records (JACAR) helper: search the
catalog and download a record's scanned pages.

JACAR (https://www.jacar.archives.go.jp) is the free online portal to the
National Archives of Japan, the Diplomatic Archives and the Ministry of
Defense's National Institute for Defense Studies (NIDS), which holds the
Imperial Navy's war diaries (戦時日誌), action reports (戦闘詳報) and the
designated-ship movement tables (指定船舶行動表). Each record has a reference
code like C08030140600. Search reaches OCR text that the record page only
shows the first ~300 characters of, and matches loosely (タマ17 also finds
モタ一七), so read every hit.

Commands:
  python3 tools/jacar.py search "第一海上護衛隊" [1944-04 1944-05]   reference codes and titles
  python3 tools/jacar.py meta C08030140600                          title, pages, OCR snippet
  python3 tools/jacar.py fetch C08030140600 [...]                   PDF + pages to sources/jacar/<code>/

fetch saves <code>.pdf and meta.json, and renders pNN.jpg pages at 110 dpi
(grayscale) with poppler's pdftoppm if it is installed. The PDFs are scans
with no text layer: read the page images. sources/ is not committed.
"""
import html
import json
import re
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request

from records import CACHE, rel  # noqa: E402
OUT = CACHE / "jacar"
SITE = "https://www.jacar.archives.go.jp"


def get(url):
    with urllib.request.urlopen(url, timeout=90) as r:
        return r.read().decode("utf-8", "replace")


def text_lines(page):
    page = re.sub(r"<script.*?</script>|<style.*?</style>", "", page, flags=re.S)
    return [x.strip() for x in html.unescape(re.sub(r"<[^>]+>", "\n", page)).split("\n") if x.strip()]


def search(keywords, start=None, end=None):
    """(code, title) for each hit. start/end are 'YYYY-MM' (the record's dates)."""
    params = {"kw": keywords, "rows": "100"}
    for prefix, ym in (("from", start), ("to", end)):
        if ym:
            y, m = ym.split("-")
            params[f"date_y_{prefix}"], params[f"date_m_{prefix}"] = y, str(int(m))
    page = get(f"{SITE}/aj/search?{urllib.parse.urlencode(params)}")
    hits = {}
    for m in re.finditer(r'href="[^"]*?(C\d{11})[^"]*"[^>]*>(.*?)</a>', page, flags=re.S):
        title = html.unescape(re.sub(r"<[^>]+>", "", m.group(2))).strip()
        if title and title != "閲覧":
            hits.setdefault(m.group(1), title)
    return list(hits.items())


def meta(code):
    lines = text_lines(get(f"{SITE}/das/meta/{code}"))
    field = lambda k: lines[lines.index(k) + 1] if k in lines else ""
    return {"code": code, "title": field("件名"), "pages": field("規模"), "holder": field("階層"),
            "call_number": field("所蔵館における請求番号"), "snippet": field("内容"),
            "url": f"{SITE}/das/image/{code}"}


def fetch(code):
    folder = OUT / code
    folder.mkdir(parents=True, exist_ok=True)
    info = meta(code)
    (folder / "meta.json").write_text(json.dumps(info, indent=1, ensure_ascii=False))
    viewer = get(f"{SITE}/das/image/{code}")
    m = re.search(r'\\/content\\/item\\/[^"]*?raw\\/[^"]*?\.pdf', viewer)
    if not m:
        sys.exit(f"{code}: no PDF link on the image page")
    pdf = folder / f"{code}.pdf"
    if not pdf.exists():
        urllib.request.urlretrieve(SITE + m.group(0).replace("\\/", "/"), pdf)
    if shutil.which("pdftoppm"):
        subprocess.run(["pdftoppm", "-r", "110", "-gray", "-jpeg", str(pdf), str(folder / "p")], check=True)
        for f in folder.glob("p-*.jpg"):  # pdftoppm writes p-1.jpg or p-01.jpg; match data's pNN refs
            f.rename(folder / f"p{int(f.stem[2:]):02d}.jpg")
    print(f"{code}: {info['title']} — {info['pages']} pages -> {rel(folder)}")


if __name__ == "__main__":
    cmd, args = (sys.argv[1], sys.argv[2:]) if len(sys.argv) > 1 else ("", [])
    if cmd == "search" and args:
        for code, title in search(*args[:3]):
            print(f"{code}\t{title}")
    elif cmd == "meta" and args:
        print(json.dumps(meta(args[0]), indent=1, ensure_ascii=False))
    elif cmd == "fetch" and args:
        for a in args:
            fetch(a)
    else:
        sys.exit(__doc__)
