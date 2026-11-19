"""wwii-book: build a book; fetch one archive page by its citation.

  wwii-book build examples/morning-report/book.typ [-o out.pdf] [--refresh]
  wwii-book proof examples/morning-report/book.typ [--ppi 110]     its pages as PNGs in proof/, for review
  wwii-book preflight book.pdf [--preset blurb-magazine]          page size, page count, fonts, image resolution
  wwii-book fetch rg64-469722323/p0712
  wwii-book atlas la-haye-du-puits [--reconstruct] [--qgis]
  wwii-book softproof blurb.icc [proof/page-01.png ...]           the palette (and pages) as the press will print them
"""
import argparse
import sys

from . import nara
from .build import build, proof
from .cite import parse


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="wwii-book", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="prepare a book's requests and compile it")
    b.add_argument("book")
    b.add_argument("-o", "--output")
    b.add_argument("--refresh", action="store_true", help="prepare every request again")
    pr = sub.add_parser("proof", help="build, then render every page to proof/page-NN.png for review")
    pr.add_argument("book")
    pr.add_argument("--ppi", type=int, default=110)
    pf = sub.add_parser("preflight", help="check a finished PDF against its printer's specifications")
    pf.add_argument("pdf")
    pf.add_argument("--preset", default="blurb-magazine")
    f = sub.add_parser("fetch", help="download a page into the scan cache and print its path")
    f.add_argument("cite", nargs="+")
    at = sub.add_parser("atlas", help="reconstruct an atlas extent's period network and draw its pair of views")
    at.add_argument("extent", help="a name under book/atlas/, or a path to an extent.yml")
    at.add_argument("--reconstruct", action="store_true", help="rebuild the network even if it exists")
    at.add_argument("--qgis", action="store_true", help="also write the GeoPackage and DEM for QGIS")
    sp = sub.add_parser("softproof", help="the palette, and any page PNGs, as a press's ICC profile will print them")
    sp.add_argument("profile", help="the printer's ICC profile")
    sp.add_argument("pages", nargs="*", help="page PNGs (from proof/) to render as they would print")
    a = ap.parse_args(argv)

    if a.cmd == "softproof":
        from pathlib import Path

        from .softproof import report
        print(report(a.profile, [Path(p) for p in a.pages]))
        return 0

    if a.cmd == "atlas":
        return _atlas(a)

    if a.cmd == "preflight":
        from .preflight import check
        rep = check(a.pdf, a.preset)
        print(f"{rep.pdf}: {rep.pages} pages, {len(rep.problems)} problems, {len(rep.warnings)} warnings")
        for p in rep.problems:
            print("  problem:", p)
        for w in rep.warnings:
            print("  warning:", w)
        return 0 if rep.ok else 1

    if a.cmd == "fetch":
        for c in a.cite:
            print(nara.page_image(parse(c)))
        return 0

    r = build(a.book, getattr(a, "output", None), refresh=getattr(a, "refresh", False))
    print(f"{r.pdf}: {len(r.prepared)} prepared, {len(r.reused)} reused, {len(r.failed)} failed")
    for key, err in r.failed:
        print(f"  failed {key}: {err}", file=sys.stderr)
    for w in r.warnings:
        print(f"  warning: {w.get('message', w)}", file=sys.stderr)
    if a.cmd == "proof":
        for p in proof(a.book, a.ppi):
            print(p)
    return 1 if r.failed else 0


def _atlas(a) -> int:
    import json

    from .atlas import oblique, panorama, qgis, reconstruct
    from .atlas.extent import Extent
    ex = Extent.load(a.extent)
    networked = bool(ex.sources)          # an extent with a period map; the mission and the section need none
    if networked and (a.reconstruct or not (ex.infrastructure / "manifest.json").exists()):
        m = reconstruct.build(ex)
        print(f"{ex.infrastructure}: {json.dumps(m['counts'])}")
    ex.build.mkdir(parents=True, exist_ok=True)
    from .atlas import sheetview
    views = ((("panorama", lambda: panorama.panorama(ex)), ("oblique", lambda: oblique.oblique(ex)),
              ("sheet", lambda: sheetview.sheet_view(ex))) if networked else ())
    if ex.inset:
        from .atlas import inset
        views += (("inset", lambda: inset.inset(ex)),)
    if ex.air:
        from .atlas import air
        views += (("air", lambda: air.air_map(ex)),)
    if ex.mission:
        from .atlas import mission
        views += (("mission", lambda: mission.mission_map(ex, part="map")),
                  ("fight", lambda: mission.mission_map(ex, part="fight")))
    if ex.sightline:
        from .atlas import sightline
        views += (("sightline", lambda: sightline.sightline(ex)),)
    for name, draw in views:
        svg, notes = draw()
        (ex.build / f"{name}.svg").write_text(svg)
        (ex.build / f"{name}.json").write_text(json.dumps(notes, indent=1, ensure_ascii=False))
        print(ex.build / f"{name}.svg")
    if a.qgis:
        print(json.dumps(qgis.export(ex), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
