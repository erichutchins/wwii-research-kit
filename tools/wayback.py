"""Wayback Machine helper: download a lost website's archived pages and images, as captured.

Commands:
  python3 tools/wayback.py list usshaynsworth.org          every captured URL (the CDX index) -> index.tsv
  python3 tools/wayback.py fetch usshaynsworth.org [--yes] [--only dd700-photos/] [--type image/]
  python3 tools/wayback.py crawl usshaynsworth.org [--yes] [--start URL ...]   follow links instead

Files go to sources/wayback/<domain>/<path>, each the original bytes of its capture (the `id_`
form of the snapshot, without the Wayback toolbar or rewritten links). manifest.tsv beside them
records, for every file, the URL, the capture's timestamp and the snapshot address to cite:
https://web.archive.org/web/<timestamp>/<url> (the `url` form in records/SOURCES.yml).

list asks the CDX index for one capture per URL (the newest with status 200; --oldest for the
first). When the index is offline, crawl starts from the home page (or --start) and follows the
links and images of every captured page inside the domain. fetch and crawl without --yes only say
what they would download. Files already downloaded are skipped, so a run can be repeated.
sources/ is not committed.
"""
import argparse
import html.parser
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from records import CACHE, rel  # noqa: E402

OUT = CACHE / "wayback"
CDX = "https://web.archive.org/cdx/search/cdx"
AGENT = "wwii-unit-records/1.0 (family history; one request at a time)"
LATEST = "29991231235959"  # a timestamp after every capture: the Archive answers with the newest
PAUSE = 1.5  # seconds between downloads: be polite to the Archive


def get(url, tries=4):
    """(final URL, bytes, content type), retrying the Archive's 'temporarily offline' and 5xx."""
    for n in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": AGENT})
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.geturl(), r.read(), r.headers.get("Content-Type", "")
        except urllib.error.HTTPError as e:
            if e.code == 404 or n == tries - 1:
                raise
        except (urllib.error.URLError, TimeoutError):
            if n == tries - 1:
                raise
        time.sleep(10 * (n + 1))


def bare(url):
    """http://www.usshaynsworth.org/a/B.html -> usshaynsworth.org/a/B.html (the dedup key)."""
    p = urllib.parse.urlsplit(url if "://" in url else "http://" + url)
    host = p.netloc.lower().split(":")[0].removeprefix("www.")
    return host + (p.path or "/") + ("?" + p.query if p.query else "")


def local(domain, url):
    """Where a URL's file goes: sources/wayback/<domain>/<path>, index.html for a folder."""
    key = bare(url)
    path = key.split("/", 1)[1] if "/" in key else ""
    path = urllib.parse.unquote(path.split("?")[0])
    if not path or path.endswith("/"):
        path += "index.html"
    return OUT / domain / re.sub(r"[^\w./ ()&,+-]", "_", path).lstrip("/")


def snapshot(ts, url, raw=True):
    return f"https://web.archive.org/web/{ts}{'id_' if raw else ''}/{url}"


def cdx_list(domain, oldest=False):
    params = {"url": domain, "matchType": "domain", "fl": "original,mimetype,timestamp",
              "filter": "statuscode:200", "output": "txt"}
    if not oldest:
        params["collapse"] = "urlkey"  # the first row per URL; newest is taken below
    _, body, ctype = get(f"{CDX}?{urllib.parse.urlencode(params)}")
    if "html" in ctype:
        sys.exit("The CDX index is offline (the Archive says 'Temporarily Offline'). "
                 "Try again later, or use `crawl`, which needs only the snapshots.")
    rows = {}
    for line in body.decode("utf-8", "replace").splitlines():
        parts = line.split(" ")
        if len(parts) != 3:
            continue
        url, mime, ts = parts
        k = bare(url)
        if k not in rows or (ts < rows[k][2] if oldest else ts > rows[k][2]):
            rows[k] = (url, mime, ts)
    return sorted(rows.values(), key=lambda r: bare(r[0]))


def read_tsv(path):
    if not path.exists():
        return []
    return [line.split("\t") for line in path.read_text().splitlines()[1:] if line]


def write_manifest(domain, done):
    m = OUT / domain / "manifest.tsv"
    m.parent.mkdir(parents=True, exist_ok=True)
    rows = {r[0]: r for r in read_tsv(m)}
    rows.update(done)
    m.write_text("url\ttimestamp\tmimetype\tfile\tcite\n" +
                 "".join("\t".join(rows[k]) + "\n" for k in sorted(rows)))


def save(domain, url, ts, done):
    """Download one capture; returns (bytes, type) or None. Records it in done."""
    f = local(domain, url)
    try:
        final, body, ctype = get(snapshot(ts, url))
    except urllib.error.HTTPError as e:
        print(f"  {e.code}  {url}")
        return None
    m = re.search(r"/web/(\d{14})", final)
    ts = m.group(1) if m else ts
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_bytes(body)
    mime = ctype.split(";")[0].strip()
    done[bare(url)] = (bare(url), ts, mime, str(f.relative_to(OUT / domain)), snapshot(ts, url, raw=False))
    print(f"  {ts}  {len(body):>9,}  {rel(f)}")
    time.sleep(PAUSE)
    return body, mime


class Links(html.parser.HTMLParser):
    ATTRS = {"href", "src", "background", "data", "lowsrc"}

    def __init__(self):
        super().__init__()
        self.found = []

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if name in self.ATTRS and value:
                self.found.append(value.strip())


def links(base, body, domain):
    p = Links()
    try:
        p.feed(body.decode("utf-8", "replace"))
    except Exception:  # broken 1990s HTML: keep what was parsed
        pass
    out = []
    for v in p.found:
        if v.startswith(("mailto:", "javascript:", "#")):
            continue
        u = urllib.parse.urljoin(base, v).split("#")[0]
        u = re.sub(r"^https?://web\.archive\.org/web/\d+[a-z_]*/", "", u)
        if bare(u).startswith(domain + "/") or bare(u) == domain:
            out.append(u)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["list", "fetch", "crawl"])
    ap.add_argument("domain")
    ap.add_argument("--yes", action="store_true", help="download (otherwise only report)")
    ap.add_argument("--only", default="", help="path prefix, e.g. dd700-photos/")
    ap.add_argument("--type", default="", help="MIME prefix, e.g. image/ or text/html")
    ap.add_argument("--oldest", action="store_true", help="list: the first capture of each URL")
    ap.add_argument("--start", nargs="*", help="crawl: pages to start from")
    ap.add_argument("--redo", action="store_true", help="download files that already exist")
    a = ap.parse_args()
    domain = bare(a.domain).rstrip("/")
    index = OUT / domain / "index.tsv"

    if a.command == "list":
        rows = cdx_list(domain, a.oldest)
        index.parent.mkdir(parents=True, exist_ok=True)
        index.write_text("url\tmimetype\ttimestamp\n" + "".join("\t".join(r) + "\n" for r in rows))
        kinds = {}
        for _, mime, _ in rows:
            kinds[mime] = kinds.get(mime, 0) + 1
        print(f"{len(rows)} URLs -> {rel(index)}")
        for mime, n in sorted(kinds.items(), key=lambda kv: -kv[1]):
            print(f"  {n:>5}  {mime}")
        return

    done = {}
    if a.command == "fetch":
        rows = read_tsv(index)
        if not rows:
            sys.exit(f"no {rel(index)}: run `list {domain}` first (or `crawl`)")
        rows = [r for r in rows if bare(r[0]).startswith(f"{domain}/{a.only}") and r[1].startswith(a.type)]
        todo = [r for r in rows if a.redo or not local(domain, r[0]).exists()]
        print(f"{len(rows)} URLs, {len(todo)} not yet downloaded")
        if not a.yes:
            for url, mime, ts in todo[:40]:
                print(f"  {ts}  {mime:<12} {url}")
            print("  ..." if len(todo) > 40 else "", "\nrun again with --yes to download")
            return
        try:
            for url, _, ts in todo:
                save(domain, url, ts, done)
        finally:
            write_manifest(domain, done)
        return

    # crawl: breadth-first over captured pages, the newest capture of each (LATEST redirects to it)
    queue = list(a.start or [f"http://{domain}/"])
    if not a.yes:
        print(f"would crawl from {', '.join(queue)} and save every page and image inside {domain}"
              f"{' under ' + a.only if a.only else ''}\nrun again with --yes to download")
        return
    seen, n = set(), 0
    try:
        while queue:
            url = queue.pop(0)
            k = bare(url)
            if k in seen or (n and not k.startswith(f"{domain}/{a.only}")):
                continue
            seen.add(k)
            n += 1
            f = local(domain, url)
            if f.exists() and not a.redo:
                body, mime = f.read_bytes(), "text/html" if f.suffix.lower() in (".html", ".htm") else ""
            else:
                got = save(domain, url, LATEST, done)
                if not got:
                    continue
                body, mime = got
            if "html" in mime:
                queue += [u for u in links(url, body, domain) if bare(u) not in seen]
    finally:
        write_manifest(domain, done)
    print(f"{n} URLs visited, {len(done)} downloaded")


if __name__ == "__main__":
    main()
