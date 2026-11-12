# /// script
# requires-python = ">=3.10"
# dependencies = ["playwright==1.64.1"]
# ///
"""Open every page of the site in a headless browser and fail on anything that breaks it.

Every page in site/, and every view a page opens from the address (the four theatres, each engagement's page and its
questions, each subject's page (a boat's at every patrol), the five walked-through subjects at their placement too,
BANG's dives by patrol, each explainer opened at a notation as the glossary's cards link it), in light and dark mode, at
desktop and phone width.
A view fails on:
  - an error in the console, or an uncaught exception;
  - a request to this site that fails or answers 4xx/5xx (a missing data file, a renamed script);
  - an empty figure: a visible SVG larger than an icon with nothing drawn in it.
A failed request to another site (the D3 and atlas CDNs) is a warning: the network, not the page. Each address on another
site is fetched once per run and answered from memory after that (every view opens in a new context, with an empty
cache), so a view waits on the network only for this site's files.

The builds check the data; this checks the pages against it. It would have caught the front page's "Also in Europe"
error (a unit with no stations) the day it broke.

Usage: uv run tools/smoke.py [--quick] [--only SUBSTRING] [--shard I/N] [-j N] [--list] [--install]
       --quick     every view at desktop width in light mode, and the pages themselves in all four combinations
       --shard I/N every N-th view from the I-th (1-based), so N runs together check every view once (the CI's matrix)
       --install   install the Chromium this script's pinned Playwright drives, and stop (`--install --with-deps` in the
                   CI, which adds the system libraries); run it once before the first run, and after the pin moves
The family repository runs its own pages through `views()` and `run()` here (its tests/smoke.py).
"""
import argparse
import asyncio
import functools
import http.server
import json
import sys
import threading
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
SIZES = {"desktop": (1400, 900), "phone": (390, 844)}
SCHEMES = ("light", "dark")

# A figure is empty when nothing is drawn in it: every mark the pages draw is one of these
MARKS = "path, circle, rect, line, polyline, polygon, ellipse, text, image, use, foreignObject"
EMPTY_FIGURES = f"""() => [...document.querySelectorAll("svg")].filter(s => {{
  const r = s.getBoundingClientRect(), st = getComputedStyle(s);
  if (r.width * r.height < 20000 || st.display === "none" || st.visibility === "hidden") return false;
  if (s.closest("[hidden], details:not([open])")) return false;
  return !s.querySelector("{MARKS}");
}}).map(s => s.id ? "#" + s.id : (s.className.baseVal ? "svg." + s.className.baseVal.split(" ")[0] : "svg"))"""


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def kit_views(root=KIT):
    """Every page in site/ and every view the address opens, as paths from the server's root."""
    rec, site = root / "records", root / "site"
    out = [f"site/{p.name}" for p in sorted(site.glob("*.html"))]
    out += theatre_views("site/theatre.html")
    out += engagement_views(rec / "engagements", "site/engagement.html")
    out += subject_views(rec / "subjects.json", "site/subject.html")
    out += [f"site/dives.html?patrol={p['patrol']}" for p in load(rec / "boats/ss-385-bang/dives.json")["patrols"]]
    out += EXPLAINER_VIEWS
    return out


def theatre_views(page):
    """The four theatre pages (theatre.html?t=<id>; the ids are site/chapter.js's THEATRES), and a deep link to a stage,
    which must land once the page is drawn."""
    return [f"{page}?t={t}" for t in ("pacific", "atlantic", "mediterranean", "europe")] + [f"{page}?t=mediterranean#stage-italy"]


# the explainers opened at a value, as the glossary's cards link them (reference/glossary.yml `patterns`, `see`)
EXPLAINER_VIEWS = ["site/zones.html?zone=K", "site/grids.html?ref=V-044572", "site/jgrid.html?code=メキ三ツ",
                   "site/german.html?ref=XXIII 97", "site/german.html?ref=CJ 9472", "site/torpedo.html?track=123S&gyro=013"]


def engagement_views(folder, page):
    """Each engagement at its two depths (engagement.html?e=<id>[&view=questions]): the page (the outcome, the map with
    the clock and the log or the chronology, the story and the figures) for every one, and the questions where the frame
    has something to show there (a pairing of an attack with the other side's record or a question the records leave
    open, for the claims board and the Sources view), from its engagement.json. The old addresses (view=account, records,
    working) must still arrive: one of each is opened."""
    out = []
    for x in load(folder / "index.json"):
        d = load(folder / x["id"] / "engagement.json")
        out.append(f"{page}?e={x['id']}")
        if d.get("pairs") or d.get("claims"):
            out.append(f"{page}?e={x['id']}&view=questions")
    out += [f"{page}?e=tama-17-1944-04-29&view=records", f"{page}?e=tama-17-1944-04-29&view=working", f"{page}?e=remagen-1945-03-07&view=account"]
    return out


# the subjects whose pages the guide walks through (guides/OPERATIONS-VIEWER.md 7.2 and the phase-6 check): their
# placement is opened too
WORKED = ("67ca-med", "ss-385-bang", "20ncb", "tama-17", "dd-700-haynsworth")


def subject_views(path, page):
    """Each subject's page (subject.html?s=<id>: its journey, and its record under it), a boat's at each patrol too, from
    subjects.json; every subject with an engagement at its Engagements view (view=engagements), the walked-through
    subjects at their placement (view=placement) as well, and one at each old address
    (view=account, records, working), which must still arrive."""
    out = []
    for s in load(path):
        out.append(f"{page}?s={s['id']}")
        if s["kind"] == "boat":
            out += [f"{page}?s={s['id']}&period={p['n']}" for p in s["periods"]]
        if s["id"] in WORKED:
            out.append(f"{page}?s={s['id']}&view=placement")
        if s.get("engagements"):
            out.append(f"{page}?s={s['id']}&view=engagements")
    out += [f"{page}?s=67ca-med&view=records", f"{page}?s=67ca-med&view=working", f"{page}?s=ss-385-bang&period=2&view=account"]
    return out


def army_views(path, page="site/subject.html"):
    """A family's pages still ask for these by name: each Army unit with stations, on its subject page."""
    return [f"{page}?s={u['unit']}" for u in load(path)["units"] if u["stations"]]


def seabee_views(path, page="site/subject.html"):
    return [f"{page}?s={u}" for u in load(path)["units"]]


def shard(views, spec):
    """Every N-th view from the I-th, for --shard I/N (1-based)."""
    i, n = (int(x) for x in spec.split("/"))
    if not 1 <= i <= n:
        raise SystemExit(f"--shard {spec}: want I/N with 1 <= I <= N")
    return views[i - 1::n]


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):   # the base class's signature: quiet
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def serve(root):
    class Server(http.server.ThreadingHTTPServer):
        request_queue_size = 128
        daemon_threads = True

        def handle_error(self, request, client_address):   # a view closed before its file was sent: not a fault
            pass

    srv = Server(("127.0.0.1", 0), functools.partial(Quiet, directory=str(root)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}/"


class Remote:
    """Another site's files, fetched once per run and answered from memory after that. A failed fetch isn't kept, and
    the request fails as it would have (a warning)."""

    def __init__(self, base):
        self.base, self.got = base, {}

    def elsewhere(self, url):
        return not url.startswith(self.base)

    async def fetch(self, route):
        r = await route.fetch()
        if not r.ok:
            raise RuntimeError(f"{r.status}")
        # the body comes back decoded, so the encoding and length headers no longer describe it
        headers = {k: v for k, v in r.headers.items() if k.lower() not in ("content-encoding", "content-length")}
        return r.status, headers, await r.body()

    async def answer(self, route):
        if route.request.method != "GET":
            return await route.continue_()
        url = route.request.url
        if url not in self.got:   # the first view to ask fetches it; the others asking meanwhile wait on the same fetch
            self.got[url] = asyncio.ensure_future(self.fetch(route))
        try:
            status, headers, body = await asyncio.shield(self.got[url])
        except Exception:
            self.got.pop(url, None)
            return await route.abort()
        await route.fulfill(status=status, headers=headers, body=body)


async def check(browser, base, view, size, scheme, remote):
    """Load one view; return (problems, warnings)."""
    w, h = SIZES[size]
    ctx = await browser.new_context(viewport={"width": w, "height": h}, color_scheme=scheme)
    await ctx.route(remote.elsewhere, remote.answer)
    page = await ctx.new_page()
    bad, warn = [], []
    page.on("console", lambda m: m.type == "error" and bad.append(f"console: {m.text[:300]}"))
    page.on("pageerror", lambda e: bad.append(f"exception: {str(e)[:300]}"))

    def failed(req, why):
        (bad if req.url.startswith(base) else warn).append(f"request {why}: {req.url}")

    page.on("requestfailed", lambda r: failed(r, r.failure or "failed"))
    page.on("response", lambda r: r.status >= 400 and failed(r.request, r.status))
    try:
        await page.goto(base + view, wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(400)   # the ResizeObservers redraw a frame after load
        # under load (several views at once, a slow machine) a figure can draw later than that: look again for up to
        # 3 s before calling it empty, so a slow frame isn't a failure and a figure that never draws still is
        empty = await page.evaluate(EMPTY_FIGURES)
        for _ in range(10):
            if not empty:
                break
            await page.wait_for_timeout(300)
            empty = await page.evaluate(EMPTY_FIGURES)
        bad += [f"empty figure: {s}" for s in empty]
    except Exception as e:
        bad.append(f"load: {str(e).splitlines()[0][:300]}")
    await ctx.close()
    # a "Failed to load resource" console line repeats a failed request, already reported (or warned of) above
    return [b for b in bad if not b.startswith("console: Failed to load resource")], warn


async def run_async(root, views, combos, jobs):
    from playwright.async_api import async_playwright

    srv, base = serve(root)
    sem = asyncio.Semaphore(jobs)
    remote = Remote(base)
    async with async_playwright() as p:
        browser = await p.chromium.launch()

        async def one(view, size, scheme):
            async with sem:
                return view, size, scheme, *await check(browser, base, view, size, scheme, remote)

        results = await asyncio.gather(*(one(v, sz, sc) for v in views for sz, sc in combos(v)))
        await browser.close()
    srv.shutdown()
    return results


def run(root, views, quick=False, jobs=6, pages=None):
    """Check `views` (paths from `root`); print the failures; return the number of failing views.
    `pages` are the plain pages, checked in all four combinations even with `quick`."""
    pages = set(pages or [v for v in views if "?" not in v and "#" not in v])
    every = [(sz, sc) for sz in SIZES for sc in SCHEMES]
    combos = (lambda v: every if v in pages else [("desktop", "light")]) if quick else (lambda v: every)
    results = asyncio.run(run_async(Path(root), views, combos, jobs))
    failing = 0
    for view, size, scheme, bad, warn in results:
        for x in warn:
            print(f"warning  {view} [{size} {scheme}]  {x}")
        if bad:
            failing += 1
            for x in dict.fromkeys(bad):
                print(f"FAIL     {view} [{size} {scheme}]  {x}")
    print(f"{len(results)} views checked ({len(views)} addresses), {failing} failing")
    return failing


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--only", help="check only the views whose address contains this")
    ap.add_argument("--shard", help="I/N: check every N-th view from the I-th")
    ap.add_argument("--install", action="store_true", help="install the pinned Playwright's Chromium and stop")
    ap.add_argument("--with-deps", action="store_true", help="with --install: the system libraries too (the CI)")
    ap.add_argument("-j", "--jobs", type=int, default=6)
    ap.add_argument("--list", action="store_true", help="list the views and stop")
    a = ap.parse_args()
    if a.install:
        import subprocess
        return subprocess.call([sys.executable, "-m", "playwright", "install", *(["--with-deps"] if a.with_deps else []),
                                "chromium"])
    views = [v for v in kit_views() if not a.only or a.only in v]
    if a.shard:
        views = shard(views, a.shard)
    if a.list:
        print("\n".join(views))
        return 0
    return 1 if run(KIT, views, a.quick, a.jobs) else 0


if __name__ == "__main__":
    sys.exit(main())
