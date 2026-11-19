"""A day's air mission and the fighters sent up against it, at the scale of the airfields, with the fight inset: the
complement of the air view (air.py), where the raiders were the enemy's and the fighters ours.

The records give the two ends of each side's flight and the minutes of the fight, never the route between: the
bombers' field ("out of Dijon", a Missing Air Crew Report), their briefed target, their courses at the moment each was
lost, a squadron's sketch of the formation's way in and home; the jets' field and the time they took off. So each side
gets a **notional** leg out and home, drawn as air.py draws a raid (a wide, pale, curved arrow: "from there, toward
here", never a track), from its recorded field to the first point of its recorded path and from the last point back.
The record's own lines are drawn over them, solid where a course is typed, dashed where a sketch draws it.

In the inset, the jets' attack is drawn the way the published accounts and the gunners' statements describe it (they
met the formation nearly head-on, passed over, and wheeled round to attack from behind): a notional path, computed from
the formation's sketched course, never stored, and labelled as notional on the page.

Reads, never copies: the engagement's routes, positions and rings (records/engagements/<id>/engagement.json), the
airfields (records/air/airfields.csv), the day's front (records/fronts/12ag-<day>.geojson).
"""
import csv
import json
import math
from html import escape

from .. import cartography as carto
from .. import figures, geo, halo, paths
from .air import arrow
from .extent import Extent
from .panorama import reach_ring

DISPLAY, INK, MUTED = carto.DISPLAY, "#000000", "#586257"
AXIS, ALLIED, LOSS = "#8a3324", "#5f84ad", "#a3241b"
OURS = "#2f5f8a"                      # the record's own lines: the bombers' colour, darker than the notional arrows
FRONT = "#000000"


def _engagement(eid: str) -> dict:
    return json.loads((paths.records() / "engagements" / eid / "engagement.json").read_text())


def _fields() -> dict[str, dict]:
    f = paths.records() / "air" / "airfields.csv"
    with open(f, newline="") as fh:
        rows = list(csv.DictReader(fh))
    out: dict[str, dict] = {}
    for r in rows:
        out.setdefault(r["field"], r)
    return out


def _text(x, y, s, size=7.0, fill=INK, anchor="start", weight="normal", italic=False):
    it = ' font-style="italic"' if italic else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{DISPLAY}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}" font-weight="{weight}"{it} stroke="#ffffff" stroke-width="2.2" '
            f'stroke-linejoin="round" paint-order="stroke">{escape(s)}</text>')


def _wrap(s: str, cols: int) -> list[str]:
    out, line = [], ""
    for w in s.split():
        if line and len(line) + len(w) + 1 > cols:
            out.append(line)
            line = w
        else:
            line = (line + " " + w).strip()
    return out + ([line] if line else [])


def _in_window(t: str, window) -> bool:
    """A route's or position's time ("1150", "1130-1145" or blank) against the window ("1130", "1200")."""
    if not t or not window:
        return True
    a = t.split("-")[0].strip()[:4]
    return a.isdigit() and str(window[0]) <= a <= str(window[1])


def _line(pts, colour, width=1.3, dash="", head=True, opacity=1.0) -> str:
    """A record's line through points (already on the page), with a small arrowhead at its end."""
    d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    da = f' stroke-dasharray="{dash}"' if dash else ""
    out = (f'<path d="{d}" fill="none" stroke="#ffffff" stroke-width="{width + 2:.1f}" stroke-opacity="0.8" '
           f'stroke-linecap="round" stroke-linejoin="round"/>'
           f'<path d="{d}" fill="none" stroke="{colour}" stroke-width="{width}"{da} stroke-linecap="round" '
           f'stroke-linejoin="round" stroke-opacity="{opacity}"/>')
    if head and len(pts) > 1:
        (x0, y0), (x1, y1) = pts[-2], pts[-1]
        L = math.hypot(x1 - x0, y1 - y0) or 1
        ux, uy = (x1 - x0) / L, (y1 - y0) / L
        s = 3.2 + width
        out += (f'<path d="M{x1 - ux * s - uy * s * 0.6:.1f},{y1 - uy * s + ux * s * 0.6:.1f} L{x1:.1f},{y1:.1f} '
                f'L{x1 - ux * s + uy * s * 0.6:.1f},{y1 - uy * s - ux * s * 0.6:.1f}" fill="none" stroke="{colour}" '
                f'stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"/>')
    return out


def _cross(x, y, colour=LOSS, s=3.6) -> str:
    return (f'<path d="M{x - s:.1f},{y - s:.1f} L{x + s:.1f},{y + s:.1f} M{x - s:.1f},{y + s:.1f} L{x + s:.1f},'
            f'{y - s:.1f}" stroke="#ffffff" stroke-width="3.4" stroke-linecap="round"/>'
            f'<path d="M{x - s:.1f},{y - s:.1f} L{x + s:.1f},{y + s:.1f} M{x - s:.1f},{y + s:.1f} L{x + s:.1f},'
            f'{y - s:.1f}" stroke="{colour}" stroke-width="1.6" stroke-linecap="round"/>')


def _field_mark(x, y, colour, axis: bool) -> str:
    if axis:
        return (f'<rect x="{x - 4.2:.1f}" y="{y - 4.2:.1f}" width="8.4" height="8.4" fill="#ffffff" stroke="{colour}" '
                f'stroke-width="1.4"/><path d="M{x - 2.6:.1f},{y:.1f} h5.2 M{x:.1f},{y - 2.6:.1f} v5.2" '
                f'stroke="{colour}" stroke-width="1.6"/>')
    return (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.4" fill="#ffffff" stroke="{colour}" stroke-width="1.4"/>'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="1.8" fill="{colour}"/>')


def _burst(x, y, colour=LOSS, r=6.0) -> str:
    pts = []
    for i in range(16):
        a = math.pi * i / 8
        rr = r if i % 2 == 0 else r * 0.45
        pts.append(f"{x + rr * math.sin(a):.1f},{y - rr * math.cos(a):.1f}")
    return (f'<polygon points="{" ".join(pts)}" fill="#ffffff" stroke="#ffffff" stroke-width="2.4"/>'
            f'<polygon points="{" ".join(pts)}" fill="{colour}" fill-opacity="0.9"/>')


def _fronts(f: geo.Frame, days, ox=0.0, oy=0.0) -> list[str]:
    out = []
    for day in days:
        for line in figures._fronts(day):
            pts = [f.xy(lon, lat) for lon, lat in line]
            if not any(0 <= x <= f.width and 0 <= y <= f.height for x, y in pts):
                continue
            d = "M" + " L".join(f"{x + ox:.1f},{y + oy:.1f}" for x, y in pts)
            out.append(f'<path d="{d}" fill="none" stroke="#ffffff" stroke-width="3.2" stroke-opacity="0.7"/>'
                       f'<path d="{d}" fill="none" stroke="{FRONT}" stroke-width="1.3" stroke-dasharray="5 1.6 1.2 1.6" '
                       f'stroke-linejoin="round"/>')
    return out


def _attack_path(sketch, end, past_km: float = 5.0, turn_km: float = 1.3):
    """The jets' attack as the accounts describe it, computed from the formation's sketched course in (lon, lat points,
    in flight order) and the place of the loss it ends at: up the formation's course the other way, a little to its
    right (nearly head-on), `past_km` beyond the loss, round in a half turn of `turn_km` radius, and down the course
    from behind to the loss. Notional: only its shape is the accounts'."""
    (lon0, lat0), (lon1, lat1) = sketch[0], sketch[-1]
    kx = 111.32 * math.cos(math.radians((lat0 + lat1) / 2))
    ky = 110.57
    dx, dy = (lon1 - lon0) * kx, (lat1 - lat0) * ky
    L = math.hypot(dx, dy)
    ux, uy = dx / L, dy / L                              # the formation's direction (km east, km north)
    nx, ny = -uy, ux                                     # to its left
    ex_, ey_ = (end[0] - lon0) * kx, (end[1] - lat0) * ky
    s_end, o_end = ex_ * ux + ey_ * uy, ex_ * nx + ey_ * ny     # the loss, along and across the course
    def at(s, o):
        return lon0 + (ux * s + nx * o) / kx, lat0 + (uy * s + ny * o) / ky
    o_up = o_end - 2 * turn_km
    c = s_end - past_km
    up = [at(s_end + 7, o_up), at(s_end, o_up), at(c, o_up)]
    turn = [at(c - turn_km * math.sin(t), o_up + turn_km - turn_km * math.cos(t))
            for t in [math.pi * k / 12 for k in range(1, 12)]]
    return up + turn + [at(c, o_end), end]


def mission_map(ex: Extent, width_in: float | None = None, part: str = "map") -> tuple[str, dict]:
    """`part`: "map", the airfields' map with the key beside it; "fight", the inset with the minutes beside it."""
    cfg = ex.mission
    eng = _engagement(cfg["engagement"])
    pos = {p["id"]: p for p in eng["positions"]}
    routes = {r["id"]: r for r in eng["routes"]}
    fields = _fields()
    total = (width_in or float(cfg.get("width_in", 9.4))) * 72
    side = float(cfg.get("side_in", 2.5)) * 72
    W = total - side - 12
    window = cfg.get("window")

    # ---------------------------------------------------------------- the airfields' map
    w_, s_, e_, n_ = (float(v) for v in cfg["bbox_lonlat"])
    f = geo.fit((w_, s_, e_, n_), W, pad=0.0)
    H = f.height
    labels = carto.Labels((0, 0, W, H))
    under, over = carto.base(f, 0, H, rivers=4, places=tuple(cfg.get("places", ())), labels=labels)
    body = [f'<defs><clipPath id="mission"><rect width="{W:.1f}" height="{H:.1f}"/></clipPath>'
            f'</defs>'
            f'<g clip-path="url(#mission)">'] + list(under)
    body += _fronts(f, ex.fronts)
    bom, jet = cfg["bombers"], cfg["interceptors"]
    bf, jf = fields[bom["field"]], fields[jet["field"]]
    bxy = f.xy(float(bf["lon"]), float(bf["lat"]))
    jxy = f.xy(float(jf["lon"]), float(jf["lat"]))
    way_in = [tuple(p) for p in routes[cfg["way_in"]]["points"]]
    way_home = [tuple(p) for p in routes[cfg["way_home"]]["points"]]
    fight = pos[cfg["fight"]]
    fxy = f.xy(fight["lon"], fight["lat"])
    in0 = f.xy(*way_in[0])
    home1 = f.xy(*way_home[-1])
    # the notional legs: the bombers out and home, the jets up to meet them and back
    body.append(arrow(bxy, in0, 3.0, 10.0, ALLIED, bend=0.12, opacity=0.62))
    body.append(arrow(home1, bxy, 2.2, 7.0, ALLIED, bend=0.12, opacity=0.38))
    meet = (fxy[0] + (jxy[0] - fxy[0]) * 0.06, fxy[1] + (jxy[1] - fxy[1]) * 0.06)
    body.append(arrow(jxy, meet, 2.6, 8.5, AXIS, bend=-0.25, opacity=0.72))
    body.append(arrow(fxy, (jxy[0] + 6, jxy[1] - 7), 1.4, 4.6, AXIS, bend=-0.3, opacity=0.4))
    from .air import _occupy
    _occupy(labels, bxy, in0, 0.12, 8)
    _occupy(labels, home1, bxy, 0.12, 6)
    _occupy(labels, jxy, meet, -0.25, 7)
    # the record's own lines, at this scale a few points long
    body.append(_line([f.xy(*p) for p in way_in], OURS, 1.1, dash="2.4 1.4", head=False))
    body.append(_line([f.xy(*p) for p in way_home], OURS, 1.1, dash="2.4 1.4", head=False))
    # the briefed target
    tgt = pos[cfg["target"]]
    tx, ty = f.xy(tgt["lon"], tgt["lat"])
    body.append(f'<circle cx="{tx:.1f}" cy="{ty:.1f}" r="5.5" fill="none" stroke="#ffffff" stroke-width="3"/>'
                f'<circle cx="{tx:.1f}" cy="{ty:.1f}" r="5.5" fill="none" stroke="{INK}" stroke-width="1.1" '
                f'stroke-dasharray="2 1.4"/><circle cx="{tx:.1f}" cy="{ty:.1f}" r="1.5" fill="{INK}"/>')
    labels.occupy(tx - 7, ty - 7, 14, 14)
    # the fight, and the inset's frame
    ib = [float(v) for v in cfg["inset"]["bbox_lonlat"]]
    (ax, ay), (bx2, by2) = f.xy(ib[0], ib[3]), f.xy(ib[2], ib[1])
    body.append(f'<rect x="{ax:.1f}" y="{ay:.1f}" width="{bx2 - ax:.1f}" height="{by2 - ay:.1f}" fill="none" '
                f'stroke="{INK}" stroke-width="0.7"/>')
    body.append(_burst(*fxy, r=5.5))
    labels.occupy(ax - 2, ay - 2, bx2 - ax + 4, by2 - ay + 4)
    for (x, y), axis in ((bxy, False), (jxy, True)):
        body.append(_field_mark(x, y, AXIS if axis else ALLIED, axis))
        labels.occupy(x - 6, y - 6, 12, 12)
    body.append(labels.place(*bxy, [(bf["name"], 7.6, ALLIED, "bold", DISPLAY),
                                    (bom["name"] + ": the field the forms name", 6.2, INK, "normal", DISPLAY)],
                             force=True, gap=8))
    # the two labels by the jets' field and the target are set by hand, below and to the left of their marks,
    # where the Swabian plain is empty: the placer would take the first free place, too far off on this map
    jx, jy = jxy
    body.append(f'<path d="M{jx:.1f},{jy + 5:.1f} V{jy + 34:.1f}" stroke="{AXIS}" stroke-width="0.6"/>')
    body.append(_text(jx + 4, jy + 42, jf["name"], 7.6, AXIS, "end", "bold"))
    body.append(_text(jx + 4, jy + 50, jet["name"] + ", took off 1130 (secondary)", 6.2, INK, "end"))
    body.append(_text(tx - 9, ty + 12, tgt["label"].split(":")[0], 7.0, INK, "end", "bold"))
    body.append(_text(tx - 9, ty + 20, "the bombers' briefed target, on all three forms;", 6.0, INK, "end"))
    body.append(_text(tx - 9, ty + 27.5, "whether they bombed it is not in the records read", 6.0, MUTED, "end"))
    body.append(labels.place(bx2, (ay + by2) / 2, [("The fight, 1145-1152", 7.0, LOSS, "bold", DISPLAY),
                                                   ("over Neuburg an der Donau: the box", 6.0, INK, "normal", DISPLAY)],
                             force=True, gap=6))
    if ex.fronts:
        # name the front once, at its most southerly point inside the map
        best = None
        for line in figures._fronts(ex.fronts[-1]):
            for lon, lat in line:
                x, y = f.xy(lon, lat)
                if 30 < x < W - 120 and 20 < y < H - 20 and (best is None or y > best[1]):
                    best = (x, y)
        if best:
            body.append(labels.place(*best, [("front, noon 26 April", 6.2, INK, "bold", DISPLAY),
                                             ("12th Army Group's situation map", 5.6, MUTED, "normal", DISPLAY)],
                                     gap=6))
    body += over
    body.append("</g>")
    body.append(f'<rect width="{W:.1f}" height="{H:.1f}" fill="none" stroke="{INK}" stroke-width="0.6"/>')

    # ---------------------------------------------------------------- the inset: the fight from the records
    map_body, body = body, []
    IW = W
    fi = geo.fit((ib[0], ib[1], ib[2], ib[3]), IW, pad=0.0)
    IH = fi.height
    oy = 0.0
    ilabels = carto.Labels((0, 0, IW, IH))
    iu, io = carto.base(fi, 0, IH, relief_zoom=int(cfg["inset"].get("relief_zoom", 11)), rivers=10,
                        places=tuple(cfg["inset"].get("places", ())), labels=ilabels)
    ib_body = [f'<clipPath id="mission-in"><rect width="{IW:.1f}" height="{IH:.1f}"/></clipPath>'
               f'<g clip-path="url(#mission-in)">'] + list(iu)
    ib_body += _fronts(fi, ex.fronts)
    # the guns' reach, round their assumed position
    for ring in eng.get("rings", []):
        cx, cy = fi.xy(ring["lon"], ring["lat"])
        r = float(ring["km"]) * 1000 * fi.k / (6371000 * math.cos(math.radians(ring["lat"])))
        ib_body.append(reach_ring(cx, cy, r, OURS, {"weapon": ring["weapon"], "basis": ring["basis"]}, words=False))
    # a grid square, hatched
    for p in eng["positions"]:
        if p["kind"] == "square" and p.get("lat2") and _in_window(p["time"], window) and p["of"] == "us":
            (sx0, sy0), (sx1, sy1) = fi.xy(p["lon"], p["lat2"]), fi.xy(p["lon2"], p["lat"])
            ib_body.append(f'<pattern id="hatch-sq" width="3" height="3" patternUnits="userSpaceOnUse" '
                           f'patternTransform="rotate(45)"><path d="M0,0 v3" stroke="{LOSS}" stroke-width="0.8"/>'
                           f'</pattern><rect x="{sx0:.1f}" y="{sy0:.1f}" width="{sx1 - sx0:.1f}" '
                           f'height="{sy1 - sy0:.1f}" fill="url(#hatch-sq)" stroke="{LOSS}" stroke-width="0.7"/>')
            ilabels.occupy(sx0 - 2, sy0 - 2, sx1 - sx0 + 4, sy1 - sy0 + 4)
    # the jets' attack, notional
    end = pos.get(cfg.get("attack_end", "bigred"))
    att = _attack_path([list(p) for p in way_in], (end["lon"], end["lat"]) if end else way_in[-1])
    apts = [fi.xy(lon, lat) for lon, lat in att]
    ib_body.append(_line(apts, AXIS, 2.2, dash="", head=True, opacity=0.45))
    for x, y in apts:
        ilabels.occupy(x - 3, y - 3, 6, 6)
    # the formation's sketched lines and the typed courses
    for r in routes.values():
        if r.get("of") != "us" or not _in_window(r.get("time", ""), window):
            continue
        pts = [fi.xy(lon, lat) for lon, lat in r["points"]]
        if r["basis"] == "sketched":
            ib_body.append(_line(pts, OURS, 1.4, dash="4 2"))
        else:
            ib_body.append(_line(pts, OURS, 1.6))
        for x, y in pts:
            ilabels.occupy(x - 2, y - 2, 4, 4)
    # Bergen: the battery's assumed place
    ring0 = (eng.get("rings") or [None])[0]
    if ring0:
        bx_, by_ = fi.xy(ring0["lon"], ring0["lat"])
        ib_body.append(f'<rect x="{bx_ - 3:.1f}" y="{by_ - 3:.1f}" width="6" height="6" fill="#ffffff" '
                       f'stroke="{OURS}" stroke-width="1.3"/>')
        ilabels.occupy(bx_ - 4, by_ - 4, 8, 8)
    # the losses
    losses = [p for p in eng["positions"] if p["kind"] == "loss" and _in_window(p["time"], window)]
    for p in losses:
        x, y = fi.xy(p["lon"], p["lat"])
        ib_body.append(_cross(x, y))
        ilabels.occupy(x - 5, y - 5, 10, 10)
    for p in losses:
        x, y = fi.xy(p["lon"], p["lat"])
        name = p["label"].split("'s last")[0].split(" down")[0]
        ib_body.append(ilabels.place(x, y, [(name, 6.6, LOSS, "bold", DISPLAY),
                                            (f"{p['time']} · {'as typed' if p['basis'] == 'reported' else 'the place named'}",
                                             5.6, INK, "normal", DISPLAY)], force=True, gap=5))
    if ring0:
        ib_body.append(ilabels.place(bx_, by_, [("Battery D's guns' reach", 6.4, OURS, "bold", DISPLAY),
                                                ("round Bergen (assumed): 37 mm, .50 cal", 5.6, INK, "normal",
                                                 DISPLAY)], force=True, gap=6))
    ax0, ay0 = apts[0]
    ib_body.append(ilabels.place(ax0, ay0, [("the jets, notional:", 6.4, AXIS, "bold", DISPLAY),
                                            ("head-on, over, and round", 5.8, INK, "normal", DISPLAY),
                                            ("to attack from behind", 5.8, INK, "normal", DISPLAY)], force=True, gap=4))
    sa = fi.xy(*way_in[0])
    ib_body.append(ilabels.place(*sa, [("the formation's course in", 6.4, OURS, "bold", DISPLAY),
                                       ("the 432nd Squadron's sketch", 5.6, INK, "normal", DISPLAY)], force=True, gap=4))
    hb = fi.xy(*way_home[-1])
    ib_body.append(ilabels.place(*hb, [("its turn and the way home", 6.4, OURS, "bold", DISPLAY),
                                       ("the same sketch (our reading)", 5.6, INK, "normal", DISPLAY)], force=True, gap=4))
    ib_body += io
    ib_body.append("</g>")
    # a scale bar: 5 km
    km5 = 5000 * fi.k / (6371000 * math.cos(math.radians((ib[1] + ib[3]) / 2)))
    ib_body.append(f'<path d="M10,{IH - 12:.1f} h{km5:.1f}" stroke="{INK}" stroke-width="1.6"/>'
                   + _text(10, IH - 16, "5 km", 6.0, INK))
    ib_body.append(f'<rect width="{IW:.1f}" height="{IH:.1f}" fill="none" stroke="{INK}" stroke-width="0.7"/>')
    body.append(f'<g transform="translate(0,{oy:.1f})">{"".join(ib_body)}</g>')

    # ---------------------------------------------------------------- the column beside: the key, then the minutes
    fight_body, body = body, map_body
    sx = W + 12
    cols = int((side - 4) / (6.0 * 0.45))
    y = 9.0
    body.append(_text(sx, y, "NOTIONAL LEGS: THE ENDS ARE RECORDED,", 6.2, INK, weight="bold"))
    body.append(_text(sx, y + 8, "THE ROUTE BETWEEN IS NOT", 6.2, INK, weight="bold"))
    y += 26
    body.append(arrow((sx + 2, y), (sx + 36, y - 3), 2, 6.5, ALLIED, bend=0.2, opacity=0.62))
    body.append(_text(sx + 42, y + 1, "the bombers, out (and home, paler)", 6.2, INK))
    y += 16
    body.append(arrow((sx + 2, y), (sx + 36, y - 3), 1.8, 6, AXIS, bend=-0.2, opacity=0.72))
    body.append(_text(sx + 42, y + 1, "the jets, up to meet them (and back)", 6.2, INK))
    y += 16
    body.append(_line([(sx + 2, y), (sx + 36, y - 2)], OURS, 1.4, dash="4 2"))
    body.append(_text(sx + 42, y + 1, "a squadron's sketch, traced", 6.2, INK))
    y += 12
    body.append(_line([(sx + 2, y), (sx + 36, y - 2)], OURS, 1.6))
    body.append(_text(sx + 42, y + 1, "a course as typed on the form", 6.2, INK))
    y += 12
    body.append(_cross(sx + 19, y - 2))
    body.append(_text(sx + 42, y + 1, "a B-26 lost: its last known position", 6.2, INK))
    y += 12
    body.append(f'<path d="M{sx + 2:.1f},{y - 2:.1f} h34" stroke="{FRONT}" stroke-width="1.3" '
                f'stroke-dasharray="5 1.6 1.2 1.6"/>')
    body.append(_text(sx + 42, y + 1, "the front, noon 26 April", 6.2, INK))
    y += 12
    body.append(f'<circle cx="{sx + 19:.1f}" cy="{y - 2:.1f}" r="5" fill="{OURS}" fill-opacity="0.07" '
                f'stroke="{OURS}" stroke-width="0.9" stroke-dasharray="3 2"/>')
    body.append(_text(sx + 42, y + 1, "guns' reach (FM 4-155), place assumed", 6.2, INK))
    y += 18
    notes_lines = [
        "Escort: P-47s of the 50th Fighter Group flew top cover (published accounts); their field is not in the "
        "records read, so they are not drawn.",
    ]
    for s in notes_lines:
        for ln in _wrap(s, cols - 4):
            body.append(_text(sx, y, ln, 5.8, MUTED, italic=True))
            y += 7.5
    # the minutes, from the engagement's own entries
    map_body, body = body, fight_body
    key_end = y
    y = 9.0
    body.append(_text(sx, y, "THE FIGHT, FROM THE RECORDS", 6.8, INK, weight="bold"))
    y += 14
    body.append(_line([(sx + 2, y), (sx + 36, y - 2)], AXIS, 2.2, opacity=0.45))
    body.append(_text(sx + 42, y + 1, "the jets' attack, notional: head-on, over", 6.0, INK))
    body.append(_text(sx + 42, y + 8.5, "and round (Ethell and Price; the gunners)", 6.0, INK))
    y += 18
    for sample, words in ((_line([(sx + 2, y), (sx + 36, y - 2)], OURS, 1.4, dash="4 2"),
                           "the 432nd Squadron's sketch, traced"),
                          (_line([(sx + 2, y + 11), (sx + 36, y + 9)], OURS, 1.6), "a course as typed, at the loss"),
                          (_cross(sx + 19, y + 20), "a B-26 lost: its last known position"),
                          (f'<rect x="{sx + 14:.1f}" y="{y + 27:.1f}" width="10" height="7" fill="none" '
                           f'stroke="{LOSS}" stroke-width="0.7"/>', "a 1 km grid square a report gives")):
        body.append(sample)
        body.append(_text(sx + 42, y + 1, words, 6.0, INK))
        y += 11
    y += 12
    body.append(_text(sx, y, "THE MINUTES, AS THE RECORDS TYPE THEM", 6.8, INK, weight="bold"))
    body.append(_text(sx, y + 8, "Army B time and the forms' times, both GMT+2", 5.8, MUTED, italic=True))
    y += 22
    for ev in eng["events"]:
        t = (ev.get("local") or ev.get("at") or "")[-4:]
        if not _in_window(t, window):
            continue
        who = ev.get("actor") or ev.get("of", "")
        words = (ev.get("words") or "").replace("\n", " ")
        colour = AXIS if ev.get("of") == "de" else OURS
        body.append(_text(sx, y, t, 6.4, colour, weight="bold"))
        body.append(_text(sx + 26, y, who, 6.2, INK, weight="bold"))
        out = _wrap(words, cols - 10)
        for k, ln in enumerate(out[:3]):
            body.append(_text(sx + 26, y + 7.6 * (k + 1), ln + (" ..." if k == 2 and len(out) > 3 else ""),
                              5.7, MUTED))
        y += 7.6 * (min(len(out), 3) + 1) + 5
    if part == "fight":
        out, Htot = body, max(IH, y)
    else:
        out, Htot = map_body, max(H, key_end)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{total:.1f}pt" height="{Htot:.1f}pt" viewBox="0 0 '
           f'{total:.1f} {Htot:.1f}">{"".join(out)}</svg>')
    notes = {
        "engagement": cfg["engagement"],
        "fields": [{k: a[k] for k in ("field", "name", "side", "units", "basis", "page")} for a in (bf, jf)],
        "routes": [{k: r.get(k) for k in ("id", "basis", "source")} for r in eng["routes"]
                   if _in_window(r.get("time", ""), window)],
        "losses": [{k: p[k] for k in ("id", "time", "basis", "source")} for p in losses],
        "notional": ["the bombers' legs out and home", "the jets' legs up and back", "the jets' attack (inset)"],
        "fronts": [f"12ag-{d}" for d in ex.fronts],
    }
    return halo.split(svg), notes
