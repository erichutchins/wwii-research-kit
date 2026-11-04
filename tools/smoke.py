# /// script
# requires-python = ">=3.10"
# dependencies = ["playwright"]
# ///
"""Open every page of the site in a headless browser and fail on anything that breaks it.

Every page in site/, and every view a page opens from the address (the four theatres, each engagement at its depths,
each subject at its account and at its records for every period, the five walked-through subjects at their working too,
BANG's dives by patrol), in light and dark mode, at desktop and phone width.
A view fails on:
  - an error in the console, or an uncaught exception;
  - a request to this site that fails or answers 4xx/5xx (a missing data file, a renamed script);
  - an empty figure: a visible SVG larger than an icon with nothing drawn in it.
A failed request to another site (the D3 and atlas CDNs) is a warning: the network, not the page.

The builds check the data; this checks the pages against it. It would have caught the front page's "Also in Europe"
error (a unit with no stations) the day it broke.

Usage: uv run tools/smoke.py [--quick] [--only SUBSTRING] [-j N] [--list]
       --quick   every view at desktop width in light mode, and the pages themselves in all four combinations
First run: `uv run --with playwright playwright install chromium` if no Chromium is installed.
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
    return out


def theatre_views(page):
    """The four theatre pages (theatre.html?t=<id>; the ids are site/chapter.js's THEATRES), and a deep link to a stage,
    which must land once the page is drawn."""
    return [f"{page}?t={t}" for t in ("pacific", "atlantic", "mediterranean", "europe")] + [f"{page}?t=mediterranean#stage-italy"]


def engagement_views(folder, page):
    """Each engagement at its depths (engagement.html?e=<id>&view=account|records|working): the account (the default)
    and the records (the map with the clock and the log, or the chronology) for every one, and the working where the
    frame has something to show there (an attack sheet's periscope, a convoy to close on, a pairing of an attack with the
    other side's record or a question the records leave open, for the Sources view), from its engagement.json."""
    out = []
    for x in load(folder / "index.json"):
        d = load(folder / x["id"] / "engagement.json")
        out += [f"{page}?e={x['id']}", f"{page}?e={x['id']}&view=records"]
        if d.get("sheets") or d.get("convoys") or d.get("pairs") or d.get("claims"):
            out.append(f"{page}?e={x['id']}&view=working")
    return out


# the subjects whose pages the guide walks through (guides/OPERATIONS-VIEWER.md 7.2 and the phase-6 check): their
# working depth is opened too
WORKED = ("67ca-med", "ss-385-bang", "20ncb", "tama-17", "dd-700-haynsworth")


def subject_views(path, page):
    """Each subject at its account (subject.html?s=<id>), and at its records for each period (a boat's every patrol
    and all of them together; a unit, battalion, ship or convoy once), from subjects.json; the walked-through subjects
    at their working too. A subject with no record of its own yet (a unit entered for its relations) has an account only."""
    out = []
    for s in load(path):
        out.append(f"{page}?s={s['id']}")
        if s["kind"] == "boat":
            out += [f"{page}?s={s['id']}&period={p['n']}&view=records" for p in s["periods"]]
            if len(s["periods"]) > 1:
                out.append(f"{page}?s={s['id']}&view=records")
        elif s["kind"] in ("ship", "battalion", "convoy") or (s["kind"] == "unit" and s["records"].get("stations")):
            out.append(f"{page}?s={s['id']}&view=records")
        if s["id"] in WORKED:
            out.append(f"{page}?s={s['id']}&view=working")
    return out


def army_views(path, page="site/subject.html"):
    """A family's pages still ask for these by name: each Army unit with stations, on its subject page."""
    return [f"{page}?s={u['unit']}&view=records" for u in load(path)["units"] if u["stations"]]


def seabee_views(path, page="site/subject.html"):
    return [f"{page}?s={u}&view=records" for u in load(path)["units"]]


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

    srv = Server(("127.0.0.1", 0), functools.partial(Quiet, directory=str(root)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}/"


async def check(browser, base, view, size, scheme):
    """Load one view; return (problems, warnings)."""
    w, h = SIZES[size]
    ctx = await browser.new_context(viewport={"width": w, "height": h}, color_scheme=scheme)
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
        bad += [f"empty figure: {s}" for s in await page.evaluate(EMPTY_FIGURES)]
    except Exception as e:
        bad.append(f"load: {str(e).splitlines()[0][:300]}")
    await ctx.close()
    # a "Failed to load resource" console line repeats a failed request, already reported (or warned of) above
    return [b for b in bad if not b.startswith("console: Failed to load resource")], warn


async def run_async(root, views, combos, jobs):
    from playwright.async_api import async_playwright

    srv, base = serve(root)
    sem = asyncio.Semaphore(jobs)
    async with async_playwright() as p:
        browser = await p.chromium.launch()

        async def one(view, size, scheme):
            async with sem:
                return view, size, scheme, *await check(browser, base, view, size, scheme)

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
    ap.add_argument("-j", "--jobs", type=int, default=6)
    ap.add_argument("--list", action="store_true", help="list the views and stop")
    a = ap.parse_args()
    views = [v for v in kit_views() if not a.only or a.only in v]
    if a.list:
        print("\n".join(views))
        return 0
    return 1 if run(KIT, views, a.quick, a.jobs) else 0


if __name__ == "__main__":
    sys.exit(main())
