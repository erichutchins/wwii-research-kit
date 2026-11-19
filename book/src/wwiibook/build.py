"""Build a book in two passes.

  1. Ask Typst for every request the book's pages make (`<wwii-request>` metadata, written by the Typst package's
     facsimile(), records() and qr-tag()). Each request carries a `kind`, the `key` Typst will look it up by, and its
     arguments. The book compiles at this stage too: an unprepared request draws a placeholder.
  2. Prepare each request not yet in `build/assets.json` (fetch and crop a scan, stage a records file as JSON, draw
     a QR code), make its colours solid (`solid.py`: the press takes no transparency) and compile again. Then give the
     PDF its page boxes and black ink (`press.finish`) and ask Typst for its warnings (`<wwii-warning>`: an image
     placed below 300 dpi).

Everything prepared lands in the book's own `build/` folder, which Typst can read (a Typst project can't read files
outside its root). The keys come from Typst, so the two sides never compute them twice.
"""
import csv
import hashlib
import json
import re
import shutil
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path

import typst
import yaml

from . import figures, images, nara, paths, press, qr, solid
from .cite import parse


@dataclass
class Result:
    pdf: Path
    prepared: list[str] = field(default_factory=list)
    reused: list[str] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)
    warnings: list[dict] = field(default_factory=list)


def _slug(key: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", key).strip("-")[:60] + "-" + hashlib.sha1(key.encode()).hexdigest()[:8]


def _facsimile(req: dict, build: Path) -> dict:
    cite = parse(req["cite"])
    src = nara.page_image(cite)
    name = f"{_slug(req['key'])}.png"
    w, h = images.facsimile(src, build / name, crop=req.get("crop"), rotate=req.get("rotate") or 0)
    return {"kind": "facsimile", "path": f"build/{name}", "px": [w, h], "credit": cite.credit, "link": cite.link,
            "cite": cite.text}


def _records(req: dict, build: Path) -> dict:
    src = paths.records() / req["path"]
    if src.suffix == ".csv":
        with src.open(newline="") as f:
            data = list(csv.DictReader(f))
    elif src.suffix in (".yml", ".yaml"):
        data = yaml.safe_load(src.read_text())
    else:
        data = json.loads(src.read_text())
    name = f"{_slug(req['key'])}.json"
    (build / name).write_text(json.dumps(data, ensure_ascii=False))
    return {"kind": "records", "path": f"build/{name}", "source": req["path"]}


def _qr(req: dict, build: Path) -> dict:
    name = f"{_slug(req['key'])}.svg"
    if req.get("style") == "punch":
        qr.punch(req["url"], build / name, tuple(req.get("fields") or ()), req.get("caption") or "Scan to see it move")
    else:
        qr.svg(req["url"], build / name)
    return {"kind": "qr", "path": f"build/{name}", "url": req["url"]}


def _picture(req: dict, build: Path) -> dict:
    """A picture already in the cache (a photograph, a crop, a clipping), by its path under the cache."""
    from PIL import Image
    src = paths.cache() / req["path"]
    name = f"{_slug(req['key'])}{src.suffix.lower()}"
    shutil.copyfile(src, build / name)
    with Image.open(src) as im:
        px = im.size
    return {"kind": "picture", "path": f"build/{name}", "px": list(px), "source": req["path"]}


def _plate(req: dict, build: Path) -> dict:
    """A slice of a day's 12th Army Group situation map, as scanned, with a unit ringed (sitmap.plate)."""
    from . import sitmap
    name = f"{_slug(req['key'])}.png"
    meta = sitmap.plate(req["day"], req["box"], req.get("unit"), build / name, width_in=req.get("width"))
    return {"kind": "plate", "path": f"build/{meta.get('svg') or name}", **meta}


def _atlas(req: dict, build: Path) -> dict:
    """One view of an atlas extent (book/atlas/<name>/extent.yml): the panorama or the oblique view. The extent's
    period network is reconstructed first if it hasn't been."""
    from .atlas import oblique, panorama, reconstruct
    from .atlas.extent import Extent
    ex = Extent.load(req["extent"])
    # the mission, the fight and the section draw no period network: an extent without one (no sheets) still has them
    if req["view"] not in ("mission", "fight", "sightline") and not (ex.infrastructure / "manifest.json").exists():
        reconstruct.build(ex)
    if req["view"] in ("mission", "fight"):
        from .atlas import mission
        svg, notes = mission.mission_map(ex, req.get("width"), part="map" if req["view"] == "mission" else "fight")
    elif req["view"] == "sightline":
        from .atlas import sightline
        svg, notes = sightline.sightline(ex, req.get("width"))
    elif req["view"] == "panorama":
        svg, notes = panorama.panorama(ex, req.get("width"), highlight=req.get("highlight"),
                                       highlight_words=req.get("highlight_words"))
    elif req["view"] == "inset":
        from .atlas import inset
        svg, notes = inset.inset(ex, req.get("width"))
    elif req["view"] == "air":
        from .atlas import air
        svg, notes = air.air_map(ex, req.get("width"))
    elif req["view"] == "sheet":
        from .atlas import sheetview
        svg, notes = sheetview.sheet_view(ex, req.get("width"))
    else:
        svg, notes = oblique.oblique(ex, req.get("width"), azimuth=req.get("azimuth"), tilt=req.get("tilt"),
                                     exaggeration=req.get("exaggeration"), highlight=req.get("highlight"))
    name = f"{_slug(req['key'])}.svg"
    (build / name).write_text(svg)
    return {"kind": "atlas", "path": f"build/{name}", "title": ex.title, **notes}


def _figure(req: dict, build: Path) -> dict:
    if req["figure"] == "oblique":
        from . import oblique
        route = json.loads((build.parent / req["data"]).read_text()) if req.get("data") else None
        svg, notes = oblique.view(req["box"], req.get("width") or 5.5, req.get("height"),
                                  azimuth=req.get("azimuth", 180), tilt=req.get("tilt", 30),
                                  exaggeration=req.get("exaggeration", 4), zoom=req.get("zoom", 12),
                                  fronts=tuple(req.get("fronts") or ()), units=req.get("units"),
                                  highlight=req.get("highlight"), route=route, window=req.get("window"),
                                  labels=tuple(req.get("labels") or ()), places=tuple(tuple(x) for x in req.get("places") or ()),
                                  rivers=req.get("rivers") or 0, legs=req.get("legs") or "full",
                                  waters=tuple(tuple(x) for x in req.get("waters") or ()),
                                  moves=tuple(req.get("moves") or ()), key=req.get("keyed", True))
        name = f"{_slug(req['key'])}.svg"
        (build / name).write_text(svg)
        return {"kind": "figure", "path": f"build/{name}", **notes}
    if req["figure"] == "route":
        data = json.loads((build.parent / req["data"]).read_text())
        svg, notes = figures.route_map(data, req.get("width") or 5.5, req["panels"], req.get("labels") or [],
                                       req.get("fronts") or [], req.get("window"), req.get("height"),
                                       req.get("legs") or "full")
        name = f"{_slug(req['key'])}.svg"
        (build / name).write_text(svg)
        return {"kind": "figure", "path": f"build/{name}", **notes}
    svg, s = figures.render(req["figure"], req["engagement"], req.get("width") or 5.5, req.get("box"), req.get("window"),
                            req.get("follow"))
    name = f"{_slug(req['key'])}.svg"
    (build / name).write_text(svg)
    marks = []
    for m in s.marks:
        t = figures._t(m.utc)
        marks.append({**asdict(m), "gmt": f"{t.day} {t:%b} {t:%H%M}Z"})
    return {"kind": "figure", "path": f"build/{name}", "marks": marks, "others": figures.grouped_cites(s),
            "zones": figures.zones_line(s)}


def _aircraft(req: dict, build: Path) -> dict:
    """An aircraft card: a photograph of the type, its silhouettes, and the recognition manual's figures."""
    from . import aircraft
    svg, notes = aircraft.card(req["type"], req.get("width") or 4.4, req.get("photo") or 0)
    name = f"{_slug(req['key'])}.svg"
    (build / name).write_text(svg)
    return {**notes, "kind": "aircraft", "path": f"build/{name}"}


def _chain(req: dict, build: Path) -> dict:
    """A unit's chain of command from the kit's relations.csv (chain.py): over months, or on one day."""
    from . import chain
    if req["view"] == "ladder":
        svg, notes = chain.ladder(req["unit"], req["on"], req.get("width") or 3.0)
    elif req["view"] == "strip":
        svg, notes = chain.strip(req["unit"], req["on"], req.get("width") or 6.0)
    else:
        svg, notes = chain.timeline(req["unit"], req["start"], req["end"], req.get("width") or 9.6,
                                    req.get("title") or "", req.get("marks") or [])
    name = f"{_slug(req['key'])}.svg"
    (build / name).write_text(svg)
    return {"kind": "chain", "path": f"build/{name}", **notes}


def _board(req: dict, build: Path) -> dict:
    """Attacks on a maneuvering board, solved by the kit's site/engage.js (maneuvering.py)."""
    from . import maneuvering
    svg, notes = maneuvering.board(req["engagement"], req["attacks"], req.get("width") or 5.5, req.get("boat"),
                                   sizes=req.get("sizes"))
    name = f"{_slug(req['key'])}.svg"
    (build / name).write_text(svg)
    return {"kind": "board", "path": f"build/{name}", **notes}


def _fire_control(req: dict, build: Path) -> dict:
    """How a torpedo was aimed: the triangle, the angle on the bow, the TDC (fire_control.py, on site/engage.js)."""
    from . import fire_control
    return fire_control.prepare(req, build)


def _convoy_route(req: dict, build: Path) -> dict:
    """A convoy's whole route on the lanes of the time, joined to the engagement's map (convoy_route.py)."""
    from . import convoy_route
    svg, notes = convoy_route.route_figure(req["engagement"], req.get("width") or 7.0, req.get("height"), req.get("box"),
                                           req.get("layout") or "auto")
    name = f"{_slug(req['key'])}.svg"
    (build / name).write_text(svg)
    return {"kind": "convoy-route", "path": f"build/{name}", **notes}


def _convoy_ships(req: dict, build: Path) -> dict:
    """A convoy that several boats attacked: its ships at one scale, and the tally (convoy_ships.py)."""
    from . import convoy_ships
    return convoy_ships.prepare(req, build)


PREPARERS: dict[str, Callable[[dict, Path], dict]] = {"facsimile": _facsimile, "records": _records, "qr": _qr,
                                                      "figure": _figure, "picture": _picture, "plate": _plate,
                                                      "atlas": _atlas, "chain": _chain,
                                                      "aircraft": _aircraft, "board": _board,
                                                      "firecontrol": _fire_control, "convoy-route": _convoy_route, "convoyships": _convoy_ships}


def _query(book: Path, selector: str, root: Path) -> list:
    out = typst.query(str(book), selector, field="value", root=str(root), package_path=str(paths.TYPST),
                      font_paths=[str(paths.FONTS)])
    return json.loads(out) if isinstance(out, (str, bytes)) else list(out)


def build(book: Path | str, output: Path | str | None = None, refresh: bool = False) -> Result:
    book = Path(book).resolve()
    root = book.parent
    build_dir = root / "build"
    build_dir.mkdir(exist_ok=True)
    assets_path = build_dir / "assets.json"
    assets = {} if refresh or not assets_path.exists() else json.loads(assets_path.read_text())
    assets = {k: v for k, v in assets.items() if (root / v["path"]).exists()}   # a file gone is prepared again
    assets_path.write_text(json.dumps(assets, indent=1))
    pdf = Path(output).resolve() if output else book.with_suffix(".pdf")
    result = Result(pdf)

    requests = {r["key"]: r for r in _query(book, "<wwii-request>", root)}    # pass 1 (also proves it compiles)
    for key, req in requests.items():
        have = assets.get(key)
        if have and (root / have["path"]).exists():
            result.reused.append(key)
            continue
        try:
            assets[key] = PREPARERS[req["kind"]](req, build_dir)
            result.prepared.append(key)
        except Exception as e:          # one bad request leaves its placeholder; the rest of the book still builds
            result.failed.append((key, f"{type(e).__name__}: {e}"))
    for a in assets.values():           # solid colours for the press: no figure carries live transparency
        if a.get("path"):
            solid.asset(root / a["path"])
    assets_path.write_text(json.dumps(assets, indent=1))

    # pass 2. PDF tagging (the structure tree for screen readers) is off: a print book has no use for it, and Typst
    # 0.15's tagger fails with an internal error on some pages (a breakable block split beside a float)
    typst.compile(str(book), output=str(pdf), root=str(root), package_path=str(paths.TYPST), font_paths=[str(paths.FONTS)],
                  pdf_tags=False)
    press.finish(pdf)                   # the trim and bleed boxes, and black as black ink alone (press.py)
    result.warnings = _query(book, "<wwii-warning>", root)
    return result


def proof(book: Path | str, ppi: int = 110) -> list[Path]:
    """The book's pages as PNGs in its proof/ folder (git-ignored), for review: what an agent's report points at and
    what the main session looks at before merging. Compiles with the assets already prepared (run build first)."""
    book = Path(book).resolve()
    root = book.parent
    out = root / "proof"
    out.mkdir(exist_ok=True)
    for old in out.glob("page-*.png"):
        old.unlink()
    typst.compile(str(book), output=str(out / "page-{0p}.png"), format="png", ppi=ppi, root=str(root),
                  package_path=str(paths.TYPST), font_paths=[str(paths.FONTS)])
    return sorted(out.glob("page-*.png"))

