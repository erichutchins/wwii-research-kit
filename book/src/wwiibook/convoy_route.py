"""A convoy's whole voyage beside the engagement, for print: the overview of the site's engagement page
(`site/engage-overview.js`) set beside the zoomed engagement map (`figures.engagement_map`), joined by two lines from
the overview's box to the map's frame.

The overview draws what the site's does, by the same rules (guides/ENGAGEMENTS.md, the encodings table):

  - the convoy's lane through `reference/lanes/lanes.yml`, in the order its `route` lists the waypoints: a leg that
    touches an assumed waypoint dotted, a leg straight between two ports dashed (no waypoint is traced from a chart);
  - the ports as open rings, the voyage's dated stops (`voyage`, the record's) as solid dots, each labelled with its
    place and date;
  - a box in ink where the zoomed map is: the engagement's `box`, or the one asked for, exactly (the zoomed map is
    drawn to it with no margin, so the box and the map's frame are the same ground).

  route_figure(engagement, width_in, height_in=None, box=None, layout="auto") -> (svg, notes)

The overview sits left of the map, or above it when the route is long (more than LONG degrees either way) or both
it and the map are wide. North is up on
both; each has a scale bar. The notes carry the route's ports and waypoints with their basis, the voyage's stops with
their citations, and the engagement map's own numbered marks (with GMT), grouped citations and clocks, shaped as
`components/mark-key.typ` reads them.
"""
import math
import re
from dataclasses import asdict
from datetime import date
from pathlib import Path

import yaml

from . import figures, geo, halo, mapmarks, paths

INK, MUTED, RULE, PAPER, LAND, SEA = figures.INK, figures.MUTED, figures.RULE, figures.PAPER, figures.LAND, figures.SEA
DISPLAY, SERIF = figures.DISPLAY, figures.SERIF
DASHED = "4 2.5"         # straight between two ports
DOTTED = "0.1 2.4"       # through an assumed waypoint (round caps make the dots)
GAP = 20.0               # points between the overview and the map, where the connectors run
ASSUMPTION = "the lanes of the time, not traced from a chart"


def lanes_file() -> Path:
    return paths.KIT / "reference" / "lanes" / "lanes.yml"


def nodes() -> dict:
    return yaml.safe_load(lanes_file().read_text())["nodes"]


def routed(d: dict, n: dict) -> list[dict]:
    """The engagement's convoys whose route runs through known waypoints, as the site's overview takes them."""
    return [c for c in (d.get("convoys") or {}).values()
            if len(c.get("route") or []) > 1 and all(k in n for k in c["route"])]


def legs(c: dict, n: dict) -> list[tuple[str, str, bool]]:
    """(from, to, assumed) for each leg of the convoy's route, in the order sailed."""
    r = c["route"]
    return [(a, b, bool(n[a].get("assumed") or n[b].get("assumed"))) for a, b in zip(r, r[1:])]


def _day(at: str) -> str:
    try:
        t = date.fromisoformat(at[:10])
    except ValueError:
        return at
    return f"{t.day} {t:%b} {t.year}"


def _text(x, y, s, size=7.0, fill=INK, anchor="start", italic=False, family=SERIF):
    return figures._text(x, y, s, size, fill, family=family, anchor=anchor, italic=italic, halo=True)


def _merc_lat(m: float) -> float:
    return math.degrees(math.atan(math.sinh(m)))


def _fill(lon0: float, lat0: float, lon1: float, lat1: float, w: float, h: float) -> geo.Frame:
    """A Mercator frame w by h points holding the box, centred on it, widened the way it falls short."""
    m0, m1 = geo._merc(lat0), geo._merc(lat1)
    k = min(w / math.radians(lon1 - lon0), h / (m1 - m0))
    clon, cm = (lon0 + lon1) / 2, (m0 + m1) / 2
    half_lon, half_m = math.degrees(w / k) / 2, h / k / 2
    return geo.Frame(clon - half_lon, _merc_lat(cm - half_m), clon + half_lon, _merc_lat(cm + half_m), w)


def _aspect(lon0, lat0, lon1, lat1) -> float:
    return 100.0 / geo.Frame(lon0, lat0, lon1, lat1, 100.0).height


def _land(f: geo.Frame, ox: float, oy: float) -> list[str]:
    out = []
    for ring in geo.land_rings((f.lon0 - 2, f.lat0 - 2, f.lon1 + 2, f.lat1 + 2), scale="50m"):
        pts, last = [], None
        for lo, la in ring:
            x, y = f.xy(lo, la)
            if last is None or abs(x - last[0]) + abs(y - last[1]) > 0.6:
                pts.append(f"{ox + x:.1f},{oy + y:.1f}")
                last = (x, y)
        if len(pts) > 2:
            out.append(f'<polygon points="{" ".join(pts)}" fill="{LAND}" stroke="#b6bfad" stroke-width="0.4"/>')
    return out


def _nested(svg: str, x: float, y: float) -> tuple[str, float, float]:
    """The engagement map as a nested <svg> at (x, y), its ids renamed so they can't meet the overview's."""
    m = re.match(r'<svg [^>]*width="([\d.]+)pt" height="([\d.]+)pt" viewBox="([^"]+)">(.*)</svg>$', svg, re.S)
    if not m:
        raise ValueError("the engagement map is not the SVG expected")
    w, h, vb, inner = float(m.group(1)), float(m.group(2)), m.group(3), m.group(4)
    inner = inner.replace('id="frame"', 'id="zoom-frame"').replace("url(#frame)", "url(#zoom-frame)")
    return (f'<svg class="zoom" x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" viewBox="{vb}" '
            f'overflow="hidden">{inner}</svg>'), w, h


LONG = 10.0              # degrees: a route spanning more than this, either way, is long, and its overview goes above


def _layout(W: float, H: float | None, ra: float, za: float, layout: str, span: float = 0.0):
    """(where, the overview's (x, y, w, h), the map's width, the map's origin, the figure's height), in points."""
    if layout == "auto":
        layout = "above" if span > LONG or (ra >= 1.6 and za >= 1.6) else "left"
    if layout == "above":
        ho = W / max(ra, 2.2)
        wz = W
        if H is not None and H - GAP - ho < wz / za:
            wz = max(72.0, (H - GAP - ho) * za)
        hz = wz / za
        return "above", (0.0, 0.0, W, ho), wz, ((W - wz) / 2, ho + GAP), ho + GAP + hz
    lo, hi = 0.28 * W, 0.42 * W
    if H is None:
        wo = min(hi, max(lo, (W - GAP) * ra / (ra + za)))
        wz = W - GAP - wo
        H = max(wz / za, wo / ra)
    else:
        wz = min(W - GAP - lo, H * za)
        wo = W - GAP - wz
    return "left", (0.0, 0.0, wo, H), wz, (wo + GAP, (H - wz / za) / 2), H


def route_figure(engagement: str, width_in: float, height_in: float | None = None, box: list[float] | None = None,
                 layout: str = "auto") -> tuple[str, dict]:
    d = figures.load(engagement)
    n = nodes()
    convoys = routed(d, n)
    if not convoys:
        raise ValueError(f"{engagement} names no convoy with a route through reference/lanes/lanes.yml")
    b = list(box or d["box"])
    W = width_in * 72
    H = height_in * 72 if height_in else None

    pts = [(n[k]["lon"], n[k]["lat"]) for c in convoys for k in c["route"]] + [(b[0], b[1]), (b[2], b[3])]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    pad = max(0.6, 0.06 * max(max(xs) - min(xs), max(ys) - min(ys)))     # a margin round the voyage and the box
    ext = (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)
    where, (ox, oy, wo, ho), wz, (zx, zy), total = _layout(W, H, _aspect(*ext), _aspect(*b), layout,
                                                          max(ext[2] - ext[0], ext[3] - ext[1]))

    zoom_svg, s = figures.engagement_map(engagement, wz / 72, box=b)
    nested, zw, zh = _nested(zoom_svg, zx, zy)

    f = _fill(*ext, wo, ho)

    def P(lon: float, lat: float) -> tuple[float, float]:
        x, y = f.xy(lon, lat)
        return ox + x, oy + y

    body = [f'<defs><clipPath id="overview-frame"><rect x="{ox:.1f}" y="{oy:.1f}" width="{wo:.1f}" '
            f'height="{ho:.1f}"/></clipPath></defs>',
            '<g class="overview" clip-path="url(#overview-frame)">',
            f'<rect x="{ox:.1f}" y="{oy:.1f}" width="{wo:.1f}" height="{ho:.1f}" fill="{SEA}"/>']
    body += _land(f, ox, oy)
    # graticule, every 5 degrees (2 on a small overview)
    step = 5 if f.lon1 - f.lon0 > 10 else 2
    for lon in range(math.ceil(f.lon0 / step) * step, math.floor(f.lon1) + 1, step):
        x, _ = P(lon, f.lat0)
        body.append(f'<line x1="{x:.1f}" y1="{oy:.1f}" x2="{x:.1f}" y2="{oy + ho:.1f}" stroke="{RULE}" stroke-width="0.4"/>')
        if x < ox + wo - 18:
            body.append(_text(x + 2, oy + ho - 3, f"{lon}°E", 5.5, MUTED, family=DISPLAY))
    for lat in range(math.ceil(f.lat0 / step) * step, math.floor(f.lat1) + 1, step):
        _, y = P(f.lon0, lat)
        body.append(f'<line x1="{ox:.1f}" y1="{y:.1f}" x2="{ox + wo:.1f}" y2="{y:.1f}" stroke="{RULE}" stroke-width="0.4"/>')
        body.append(_text(ox + 3, y - 2, f"{lat}°N", 5.5, MUTED, family=DISPLAY))
    # the box where the map is
    (bx0, by0), (bx1, by1) = P(b[0], b[3]), P(b[2], b[1])
    body.append(f'<rect class="engagement-box" x="{bx0:.1f}" y="{by0:.1f}" width="{bx1 - bx0:.1f}" '
                f'height="{by1 - by0:.1f}" fill="{INK}" fill-opacity="0.08" stroke="{INK}" stroke-width="0.9"/>')
    # the lane, leg by leg
    route_notes, voyage_notes = [], []
    for c in convoys:
        for a, z, assumed in legs(c, n):
            (x1, y1), (x2, y2) = P(n[a]["lon"], n[a]["lat"]), P(n[z]["lon"], n[z]["lat"])
            body.append(f'<line class="leg{" assumed" if assumed else ""}" data-from="{a}" data-to="{z}" '
                        f'x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{MUTED}" stroke-width="1.2" '
                        f'stroke-linecap="round" stroke-dasharray="{DOTTED if assumed else DASHED}"/>')
        for k in c["route"]:
            w = n[k]
            route_notes.append({"convoy": c["convoy"], "id": k, "name": w["name"], "lon": w["lon"], "lat": w["lat"],
                                "port": bool(w.get("port")),
                                "basis": f"assumed: {w['assumed']}" if w.get("assumed") else w.get("source", "")})
        for v in c.get("voyage") or []:
            voyage_notes.append({"convoy": c["convoy"], "place": n[v["place"]]["name"] if v.get("place") in n else v.get("place"),
                                 "event": v.get("event", ""), "at": v.get("at", ""), "basis": v.get("basis", ""),
                                 "source": v.get("source", ""), "placed": v.get("place") in n})
    # ports, open rings; the voyage's dated stops, solid dots; one label a place, its stops' dates under it
    stops: dict[str, list[str]] = {}
    for c in convoys:
        for v in c.get("voyage") or []:
            if v.get("place") in n:
                stops.setdefault(v["place"], []).append(f"{v.get('event', '')} {_day(v.get('at', ''))}".strip())
    ports = list(dict.fromkeys(k for c in convoys for k in c["route"] if n[k].get("port")))
    for k in ports:
        x, y = P(n[k]["lon"], n[k]["lat"])
        body.append(f'<circle class="port" cx="{x:.1f}" cy="{y:.1f}" r="2.4" fill="{PAPER}" stroke="{INK}" stroke-width="0.9"/>')
    for k in stops:
        x, y = P(n[k]["lon"], n[k]["lat"])
        body.append(f'<circle class="stop" cx="{x:.1f}" cy="{y:.1f}" r="1.5" fill="{INK}"/>')
    for k in dict.fromkeys([*ports, *stops]):
        x, y = P(n[k]["lon"], n[k]["lat"])
        right = x - ox < wo * 0.6
        dx, anchor = (5, "start") if right else (-5, "end")
        body.append(_text(x + dx, y + 2.5, n[k]["name"], 7, INK, anchor, italic=True))
        lines = stops.get(k, [])
        down = y + 2.5 + 7 * len(lines) < oy + ho - 22      # the dates under the name, or over it near the foot
        for i, words in enumerate(lines):
            dy = 7 * (i + 1) if down else -7.5 * (len(lines) - i)
            body.append(_text(x + dx, y + 2.5 + dy, words, 6, MUTED, anchor, italic=True))
    # what the lane is
    name = ", ".join(c["convoy"] for c in convoys)
    body.append(_text(ox + 4, oy + 9, f"{name}: the lanes of the time,", 6, MUTED, italic=True))
    body.append(_text(ox + 4, oy + 16, "not traced from a chart; dotted where assumed", 6, MUTED, italic=True))
    body.append("</g>")
    # scale bar (nautical miles: the sea) and north (a Mercator frame: up)
    bar, _ = mapmarks.scale(ox + wo - 8, oy + ho - 12, 1 / (f.nm_per_pt() * 1.852), "sea", max_len=wo * 0.3,
                            anchor="end")
    body.append(bar)
    body.append(mapmarks.north(ox + wo - 12, oy + ho - 50, 0))
    body.append(f'<rect x="{ox:.1f}" y="{oy:.1f}" width="{wo:.1f}" height="{ho:.1f}" fill="none" stroke="{INK}" '
                'stroke-width="0.6"/>')
    # the zoomed map, and the two lines from the box to its frame
    body.append(nested)
    if where == "left":
        ends = [((bx1, by0), (zx, zy)), ((bx1, by1), (zx, zy + zh))]
    else:
        ends = [((bx0, by1), (zx, zy)), ((bx1, by1), (zx + zw, zy))]
    for (x1, y1), (x2, y2) in ends:
        body.append(f'<line class="connector" x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                    f'stroke="{INK}" stroke-width="0.5"/>')
    svg = halo.split(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.1f}pt" height="{total:.1f}pt" '
                     f'viewBox="0 0 {W:.1f} {total:.1f}">{"".join(body)}</svg>')

    marks = []
    for m in s.marks:
        t = figures._t(m.utc)
        marks.append({**asdict(m), "gmt": f"{t.day} {t:%b} {t:%H%M}Z"})
    assumed = [r for r in route_notes if r["basis"].startswith("assumed")]
    route_line = "; ".join(f"{r['name']} ({'port, ' + r['basis'] if r['port'] else r['basis']})" for r in route_notes)
    voyage_line = "; ".join(f"{v['event']} {v['place']} {v['at']} ({v['source']})".strip() for v in voyage_notes)
    notes = {
        "layout": where, "box": b, "convoys": [c["convoy"] for c in convoys],
        "route": route_notes, "voyage": voyage_notes,
        "route_line": f"{name}'s lane, {ASSUMPTION} (reference/lanes/lanes.yml): {route_line}",
        "assumptions": ("each waypoint between ports is assumed, for the reason given, and every leg that touches one "
                        "is dotted" if len(assumed) == sum(not r["port"] for r in route_notes) and assumed
                        else "a leg that touches an assumed waypoint is dotted, a leg straight between two ports dashed"
                        if assumed else "every point is a port, and every leg is dashed straight between two"),
        "voyage_line": f"Dated stops: {voyage_line}" if voyage_notes else "No dated stop is recorded",
        "marks": marks, "others": figures.grouped_cites(s), "zones": figures.zones_line(s),
    }
    return svg, notes
