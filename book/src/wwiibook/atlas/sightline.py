"""A section under an aircraft's course, seen from a battery: the ground along the course (Copernicus GLO-30), the
lowest height at which an aircraft over each point could be seen from the guns, the guns' reach where it cuts the
section, and the heights the records type for the aircraft.

The section follows an engagement's route (`along`), carried on to a position (`extend_to`). The battery stands at a
ring's `at` (its position, often assumed: the page says so). Everything is computed here, never stored:

- **the hidden ground**: from the guns (2 m above the ground), a straight ray to an aircraft over a point of the course
  must clear the ground between; the lowest height that does, with the earth's curve and the usual refraction (k = 4/3),
  is the line under which the aircraft were out of sight. GLO-30 includes woods and buildings as they are today, so the
  line is today's, to within what a 30 m model shows.
- **the reach**: a gun's range (the ring's `km`, horizontal and vertical alike in FM 4-155's table) is a sphere round
  the guns; the section, a vertical plane off the guns by some distance, cuts it in a circle, drawn as such.
- **the heights**: as typed, in feet. No record says above what; they are drawn above the guns' ground, assumed.
"""
import json
import math
from html import escape

import numpy as np

from .. import cartography as carto
from .. import paths
from ..solid import mix
from . import terrain
from .extent import Extent

DISPLAY, INK, MUTED = carto.DISPLAY, "#000000", "#586257"
GROUND, HIDDEN, OURS, AXIS, LOSS = "#c9c2ad", "#8a8f86", "#2f5f8a", "#8a3324", "#a3241b"
PLOT = "#fbfaf6"                   # the plot's ground (core.typ tokens.paper)
FT = 0.3048
R_EFF = 6371000 * 4 / 3


def _text(x, y, s, size=6.4, fill=INK, anchor="start", weight="normal", italic=False):
    it = ' font-style="italic"' if italic else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{DISPLAY}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}" font-weight="{weight}"{it} stroke="#ffffff" stroke-width="2.2" '
            f'stroke-linejoin="round" paint-order="stroke">{escape(s)}</text>')


def section(ex: Extent, step: float = 50.0) -> dict:
    """The numbers the figure draws: distance along the course (m), the ground, the lowest height in sight, and the
    battery's place on the section."""
    cfg = ex.sightline
    eng = json.loads((paths.records() / "engagements" / cfg["engagement"] / "engagement.json").read_text())
    pos = {p["id"]: p for p in eng["positions"]}
    route = next(r for r in eng["routes"] if r["id"] == cfg["along"])
    if cfg.get("back_km") is not None:
        # the route's typed course, carried back and on through its last point (the record's position), on the
        # ellipsoid: back_km before it and on_km after it
        from pyproj import Geod
        lon, lat = route["points"][-1]
        crs = float(cfg.get("course", route.get("course") or 0))
        g = Geod(ellps="WGS84")
        b_lon, b_lat, _ = g.fwd(lon, lat, crs + 180, float(cfg["back_km"]) * 1000)
        o_lon, o_lat, _ = g.fwd(lon, lat, crs, float(cfg["on_km"]) * 1000)
        pts = [(b_lon, b_lat), (lon, lat), (o_lon, o_lat)]
    else:
        pts = [tuple(p) for p in route["points"]]
        if cfg.get("extend_to"):
            e = pos[cfg["extend_to"]]
            pts.append((e["lon"], e["lat"]))
    X, Y = ex.to_crs.transform([p[0] for p in pts], [p[1] for p in pts])
    xs, ys, ds, d0 = [], [], [], 0.0
    for i in range(len(X) - 1):
        seg = math.hypot(X[i + 1] - X[i], Y[i + 1] - Y[i])
        n = max(1, int(seg // step))
        for k in range(n):
            t = k / n
            xs.append(X[i] + (X[i + 1] - X[i]) * t)
            ys.append(Y[i] + (Y[i + 1] - Y[i]) * t)
            ds.append(d0 + seg * t)
        d0 += seg
    xs.append(X[-1])
    ys.append(Y[-1])
    ds.append(d0)
    xs, ys, ds = np.array(xs), np.array(ys), np.array(ds)
    grid = terrain.dem(ex, res=30.0)
    ground = grid.at(xs, ys)
    rings = {r["id"]: r for r in eng.get("rings", [])}
    gun = pos[cfg["from"]] if cfg["from"] in pos else rings[cfg["rings"][0]]
    bx, by = ex.to_crs.transform(gun["lon"], gun["lat"])
    bz = float(grid.at(bx, by)[0])
    eye = bz + 2.0
    # the battery's place on the section: the nearest point of the course, and how far off it the guns stood
    off = np.hypot(xs - bx, ys - by)
    i_b = int(np.argmin(off))
    # the lowest height in sight over each point
    t = np.linspace(0.01, 1.0, 160)
    lowest = np.empty_like(ground)
    for i, (px, py) in enumerate(zip(xs, ys)):
        D = math.hypot(px - bx, py - by)
        qx, qy = bx + (px - bx) * t, by + (py - by) * t
        z = grid.at(qx, qy) - (D * t) ** 2 / (2 * R_EFF)       # the ground, lowered by the curve as seen from the guns
        drop = D ** 2 / (2 * R_EFF)
        need = eye + (z - eye) / t                             # the height at the aircraft for the ray to clear z(t)
        lowest[i] = max(float(np.max(need)) + drop, float(ground[i]))
    marks = []
    for mid in cfg.get("marks", []):
        p = pos[mid]
        mx, my = ex.to_crs.transform(p["lon"], p["lat"])
        dd = np.hypot(xs - mx, ys - my)
        j = int(np.argmin(dd))
        marks.append({"id": mid, "label": p["label"], "time": p.get("time", ""), "d": float(ds[j]),
                      "off": float(dd[j]), "kind": p["kind"]})
    return {"d": ds, "ground": ground, "lowest": lowest, "gun": gun, "gun_z": bz, "gun_d": float(ds[i_b]),
            "gun_off": float(off[i_b]), "rings": [rings[r] for r in cfg.get("rings", [])], "marks": marks,
            "route": route}


def sightline(ex: Extent, width_in: float | None = None) -> tuple[str, dict]:
    cfg = ex.sightline
    s = section(ex)
    d, ground, lowest = s["d"], s["ground"], s["lowest"]
    total = (width_in or float(cfg.get("width_in", 9.4))) * 72
    left, right, top, plot_h = 46.0, 14.0, 18.0, float(cfg.get("height_pt", 250))
    W = total - left - right
    zmax = float(cfg.get("top_ft", 11000)) * FT + s["gun_z"]
    zmin = math.floor((float(np.min(ground)) - 40) / 50) * 50
    kx = W / float(d[-1])
    ky = plot_h / (zmax - zmin)

    def X(v):
        return left + v * kx

    def Y(z):
        return top + (zmax - z) * ky

    body = [f'<rect x="{left:.1f}" y="{top:.1f}" width="{W:.1f}" height="{plot_h:.1f}" fill="{PLOT}"/>']
    # Every tint is drawn solid, as the translucent tints looked one over another on the plot's ground (the press
    # takes no transparency): the heights' bands cut into strips, each strip the colour of the bands over it, and the
    # guns' reach drawn in each strip at the colour of its rings over that strip, then the ground over both.
    bands = []
    for k, h in enumerate(cfg.get("heights", [])):
        y0, y1 = Y(s["gun_z"] + h["high_ft"] * FT), Y(s["gun_z"] + h["low_ft"] * FT)
        bands.append((y0, y1, 0.16 if k == 0 else 0.07))
    edges = sorted({top, top + plot_h, *(min(max(v, top), top + plot_h) for b in bands for v in b[:2])})
    strips = []
    for a, b in zip(edges, edges[1:]):
        colour = PLOT
        for y0, y1, op in bands:
            if y0 <= a and b <= y1:
                colour = mix(AXIS, op, colour)
        strips.append((a, b, colour))
        if colour != PLOT:
            body.append(f'<rect x="{left:.1f}" y="{a:.1f}" width="{W:.1f}" height="{b - a:.1f}" fill="{colour}"/>')
    gx, gy = X(s["gun_d"]), Y(s["gun_z"])
    arcs = []
    for ring in s["rings"]:
        R = float(ring["km"]) * 1000
        if R <= s["gun_off"]:
            continue
        r = math.sqrt(R ** 2 - s["gun_off"] ** 2)
        arcs.append((r, ring, f'M{gx - r * kx:.1f},{gy:.1f} A{r * kx:.1f},{r * ky:.1f} 0 0 1 {gx + r * kx:.1f},{gy:.1f}'))
    arcs.sort(key=lambda t: -t[0])                 # widest first, so each narrower reach lies over the wider
    for n, (a, b, colour) in enumerate(strips):
        if not arcs or a >= gy:
            continue
        body.append(f'<clipPath id="sl-strip-{n}"><rect x="{left:.1f}" y="{a:.1f}" width="{W:.1f}" '
                    f'height="{b - a:.1f}"/></clipPath>')
        c = colour
        for _, _, d_arc in arcs:
            c = mix(OURS, 0.08, c)
            body.append(f'<path d="{d_arc}" fill="{c}" clip-path="url(#sl-strip-{n})"/>')
    for y0, _, _ in bands:
        body.append(f'<path d="M{left:.1f},{y0:.1f} h{W:.1f}" stroke="{AXIS}" stroke-width="0.6" '
                    f'stroke-dasharray="3 2"/>')
    for k, h in enumerate(cfg.get("heights", [])):
        x0 = left + 6 + k * 120
        body.append(_text(x0 + 1, bands[k][0] + 9, h["label"], 6.2, AXIS, weight="bold"))
        body.append(_text(x0 + 1, bands[k][0] + 16.5, h["source"], 5.6, MUTED))
    # the ground, and the hidden band above it
    gpts = " ".join(f"{X(a):.1f},{Y(b):.1f}" for a, b in zip(d, ground))
    lpts = " ".join(f"{X(a):.1f},{Y(b):.1f}" for a, b in zip(d, lowest))
    rev = " ".join(f"{X(a):.1f},{Y(b):.1f}" for a, b in zip(d[::-1], ground[::-1]))
    body.append('<pattern id="sl-hide" width="4" height="4" patternUnits="userSpaceOnUse" '
                f'patternTransform="rotate(45)"><path d="M0,0 v4" stroke="{HIDDEN}" stroke-width="0.9"/></pattern>')
    body.append(f'<polygon points="{lpts} {rev}" fill="url(#sl-hide)" stroke="none"/>')
    body.append(f'<polyline points="{lpts}" fill="none" stroke="{HIDDEN}" stroke-width="1.1"/>')
    base = f"{X(d[-1]):.1f},{top + plot_h:.1f} {X(0):.1f},{top + plot_h:.1f}"
    body.append(f'<polygon points="{gpts} {base}" fill="{GROUND}" stroke="{INK}" stroke-width="0.7"/>')
    # the guns' reach where it cuts the section
    for r, ring, d_arc in arcs:
        body.append(f'<path d="{d_arc}" fill="none" stroke="{OURS}" stroke-width="0.9" stroke-dasharray="3 2"/>')
        body.append(_text(gx + r * kx * 0.72, gy - r * ky * 0.72 - 2, ring["weapon"], 6.0, OURS, weight="bold"))
    short = [r["weapon"] for r in s["rings"] if float(r["km"]) * 1000 <= s["gun_off"]]
    if short:
        body.append(_text(gx, gy - 6, f"{', '.join(short)}: reach ends short of this line", 5.8, OURS, "middle"))
    body.append(f'<path d="M{gx:.1f},{gy:.1f} l-4,6 h8 z" fill="{OURS}" stroke="#ffffff" stroke-width="0.8"/>')
    body.append(_text(gx, top + plot_h + 22, f"Battery D, round {s['gun']['label'].split(':')[0].split(' (')[0]}"
                      f" (assumed), {s['gun_off'] / 1000:.1f} km off this line", 6.2, OURS, "middle", "bold"))
    # the marks: losses and the town, where they come nearest the course
    for k, m in enumerate(s["marks"]):
        x = X(m["d"])
        row = 18.0 * k
        col = LOSS if m["kind"] == "loss" else INK
        body.append(f'<path d="M{x:.1f},{top:.1f} V{top + plot_h:.1f}" stroke="{col}" stroke-width="0.6" '
                    f'stroke-dasharray="1.5 1.5"/>')
        name = m["label"].split("'s last")[0].split(" down")[0].split(":")[0]
        words = f"{m['time']} " if m["time"] else ""
        body.append(_text(x + 2, top + 8 + row, name, 6.2, col, weight="bold"))
        where = ("on this line: its last known position" if m["off"] < 50
                 else f"{m['off'] / 1000:.1f} km off this line")
        body.append(_text(x + 2, top + 15 + row, f"{words}{where}", 5.6, MUTED))
    # axes: heights in feet above the sea, on the left; distance along the course below
    ft = 0
    while ft * FT <= zmax:
        if ft * FT >= zmin:
            y = Y(ft * FT)
            body.append(f'<path d="M{left - 3:.1f},{y:.1f} h3" stroke="{INK}" stroke-width="0.5"/>')
            body.append(_text(left - 5, y + 2, f"{ft:,}", 5.6, MUTED, "end"))
        ft += 1000
    body.append(_text(4, top - 6, "feet above the sea", 5.8, MUTED, italic=True))
    for km in range(0, int(d[-1] // 1000) + 1, 5):
        x = X(km * 1000)
        body.append(f'<path d="M{x:.1f},{top + plot_h:.1f} v3" stroke="{INK}" stroke-width="0.5"/>')
        body.append(_text(x, top + plot_h + 11, f"{km} km", 5.6, MUTED, "middle"))
    body.append(_text(left, top + plot_h + 22, "\u2190 " + cfg.get("from_words", "back along the course"), 6.0, INK))
    body.append(_text(left + W, top + plot_h + 22, cfg.get("to_words", "on along the course") + " \u2192", 6.0, INK,
                      "end"))
    body.append(f'<rect x="{left:.1f}" y="{top:.1f}" width="{W:.1f}" height="{plot_h:.1f}" fill="none" '
                f'stroke="{INK}" stroke-width="0.6"/>')
    exag = ky / kx
    note_y = top + plot_h + 36
    along = (f"Big Red's course as typed on its form, {cfg.get('course')}°, drawn through its last known position "
             f"and carried {cfg.get('back_km')} km back and {cfg.get('on_km')} km on (ours)"
             if cfg.get("back_km") is not None else s["route"]["label"])
    lines = [
        f"The section: {along} ({s['route']['source']}). The ground: Copernicus DEM GLO-30. Heights {exag:.0f} times distances, so the guns' reach is drawn as "
        f"flattened circles: the cut of each sphere of reach by this section.",
        "Hatched: too low to be seen from the guns, 2 m above Bergen's ground, past the hills between, with the "
        "earth's curve and refraction. The model includes today's woods. The jets' heights are as typed; no record "
        "says above what, so they are drawn above the guns' ground (assumed).",
    ]
    cols = int(total / (6.0 * 0.45))
    for ln in lines:
        words, cur = ln.split(), ""
        for w in words:
            if len(cur) + len(w) + 1 > cols:
                body.append(_text(left, note_y, cur, 6.0, MUTED))
                note_y += 8
                cur = w
            else:
                cur = (cur + " " + w).strip()
        body.append(_text(left, note_y, cur, 6.0, MUTED))
        note_y += 11
    Htot = note_y
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{total:.1f}pt" height="{Htot:.1f}pt" '
           f'viewBox="0 0 {total:.1f} {Htot:.1f}">{"".join(body)}</svg>')
    notes = {"exaggeration": round(exag, 1), "gun_off_km": round(s["gun_off"] / 1000, 2),
             "dem": "Copernicus DEM GLO-30, doi:10.5270/ESA-c5d3d65",
             "marks": [{k: m[k] for k in ("id", "time")} | {"off_km": round(m["off"] / 1000, 2)} for m in s["marks"]],
             "heights": cfg.get("heights", [])}
    return svg, notes
