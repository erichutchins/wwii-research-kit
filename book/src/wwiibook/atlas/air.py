"""The air war over an extent, at the scale of the sea between the airfields: for an extent's `air:` (a box, a target, a
window), the raids on the target as the raiding side's record gives them (records/air/raids.csv), the airfields the
raiders and the defending fighters flew from (records/air/airfields.csv), and thick curved arrows from each field
toward the target.

The arrows show direction only. No record read gives a raid's route, so an arrow is drawn on a curve, wide and
pale, to read as "from there, toward here" and never as a track (the rule for a unit's positions: no lines between
them). A raid whose airfield no source names is listed beside the map, not drawn. A defending squadron's arrow ends
short of the target, over the approaches, where the night fighters patrolled.
"""
import csv
import math
from datetime import date
from html import escape

from .. import cartography as carto
from .. import geo, halo, mapmarks, paths, symbols
from . import record
from .extent import Extent
from .panorama import reach_fill, reach_ring

DISPLAY, INK, MUTED = carto.DISPLAY, "#000000", "#586257"
AXIS, ALLIED, TARGET = "#8a3324", "#5f84ad", "#a3241b"   # the Allied air arrows a lighter blue than our units'
SIDE = {"de": AXIS, "it": AXIS, "uk": ALLIED, "us": ALLIED}
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "June", "July", "Aug", "Sept", "Oct", "Nov", "Dec"]


def _csv(name: str) -> list[dict]:
    f = paths.records() / "air" / name
    if not f.exists():
        return []
    with open(f, newline="") as fh:
        return list(csv.DictReader(fh))


def _night(s: str, night: str = "yes") -> str:
    """'24/25 June' for the night of 24 June; '22 Aug' where the record doesn't say night."""
    d = date.fromisoformat(s)
    return f"{d.day}/{d.day + 1} {MONTHS[d.month - 1]}" if night else f"{d.day} {MONTHS[d.month - 1]}"


def arrow(p0, p1, w0: float, w1: float, colour: str, bend: float = 0.22, opacity: float = 0.82) -> str:
    """A thick, tapered, curved arrow from p0 to p1 (points), bowed to the left of its direction by `bend` of its
    length: a quadratic curve, its sides offset by a width growing from w0 to w1, and a head at p1."""
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy) or 1
    nx, ny = -dy / L, dx / L
    cx, cy = (x0 + x1) / 2 + nx * bend * L, (y0 + y1) / 2 + ny * bend * L
    head = min(3.2 * w1, 0.3 * L)

    def at(t):
        x = (1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t * t * x1
        y = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t * t * y1
        tx = 2 * (1 - t) * (cx - x0) + 2 * t * (x1 - cx)
        ty = 2 * (1 - t) * (cy - y0) + 2 * t * (y1 - cy)
        n = math.hypot(tx, ty) or 1
        return x, y, -ty / n, tx / n, tx / n, ty / n
    # the shaft stops where the head begins
    t_end, acc, px, py = 1.0, 0.0, x0, y0
    for i in range(1, 201):
        x, y, *_ = at(i / 200)
        acc += math.hypot(x - px, y - py)
        px, py = x, y
    total = acc
    acc, px, py = 0.0, x0, y0
    for i in range(1, 201):
        x, y, *_ = at(i / 200)
        acc += math.hypot(x - px, y - py)
        px, py = x, y
        if acc >= total - head:
            t_end = i / 200
            break
    left, right = [], []
    for i in range(41):
        t = t_end * i / 40
        x, y, ux, uy, _, _ = at(t)
        w = (w0 + (w1 - w0) * t / t_end) / 2
        left.append((x + ux * w, y + uy * w))
        right.append((x - ux * w, y - uy * w))
    x, y, ux, uy, _, _ = at(t_end)
    hw = w1 * 1.15
    pts = left + [(x + ux * hw, y + uy * hw), (x1, y1), (x - ux * hw, y - uy * hw)] + right[::-1]
    d = "M" + " L".join(f"{a:.1f},{b:.1f}" for a, b in pts) + " Z"
    return (f'<path d="{d}" fill="#ffffff" fill-opacity="0.55" stroke="#ffffff" stroke-width="2.4" '
            f'stroke-linejoin="round"/><path d="{d}" fill="{colour}" fill-opacity="{opacity}" stroke="{colour}" '
            f'stroke-width="0.5" stroke-linejoin="round"/>')


def _occupy(labels, p0, p1, bend: float, w: float):
    """Keep labels off an arrow: small boxes along its curve."""
    (x0, y0), (x1, y1) = p0, p1
    L = math.hypot(x1 - x0, y1 - y0) or 1
    nx, ny = -(y1 - y0) / L, (x1 - x0) / L
    cx, cy = (x0 + x1) / 2 + nx * bend * L, (y0 + y1) / 2 + ny * bend * L
    for i in range(1, 30):
        t = i / 30
        x = (1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t * t * x1
        y = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t * t * y1
        labels.occupy(x - w, y - w, 2 * w, 2 * w)


def _text(x, y, s, size=7.0, fill=INK, anchor="start", weight="normal", italic=False):
    it = ' font-style="italic"' if italic else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{DISPLAY}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}" font-weight="{weight}"{it} stroke="#ffffff" stroke-width="2.2" '
            f'stroke-linejoin="round" paint-order="stroke">{escape(s)}</text>')


def air_map(ex: Extent, width_in: float | None = None) -> tuple[str, dict]:
    cfg = ex.air
    w, s, e, n = (float(v) for v in cfg["bbox_lonlat"])
    total = (width_in or float(cfg.get("width_in", 9.6))) * 72
    side = float(cfg.get("side_in", 2.4)) * 72           # the column beside the map: the key and the raids
    W = total - side - 12
    f = geo.fit((w, s, e, n), W, pad=0.0)
    H = f.height
    t_name, t_lon, t_lat = cfg["target"]
    lo, hi = date.fromisoformat(str(cfg["from"])), date.fromisoformat(str(cfg["to"]))
    raids = [r for r in _csv("raids.csv") if r["target"] == cfg.get("target_id", ex.name)
             and lo <= date.fromisoformat(r["date"]) <= hi]
    fields = [r for r in _csv("airfields.csv") if date.fromisoformat(r["from"]) <= hi
              and date.fromisoformat(r["to"]) >= lo]
    labels = carto.Labels((0, 0, W, H))
    under, over = carto.base(f, 0, H, rivers=0, places=tuple(cfg.get("places", ())), labels=labels)
    body = [f'<defs><clipPath id="airmap"><rect width="{W:.1f}" height="{H:.1f}"/></clipPath></defs>'
            f'<g clip-path="url(#airmap)">'] + list(under)
    tx, ty = f.xy(t_lon, t_lat)
    # raiders: one arrow a field, its units and nights beside it
    by_field: dict[str, list[dict]] = {}
    for r in raids:
        if r["from_field"]:
            by_field.setdefault(r["from_field"], []).append(r)
    marks, words = [], []
    for fid, rs in by_field.items():
        rows = [a for a in fields if a["field"] == fid]
        if not rows:
            continue
        fx, fy = f.xy(float(rows[0]["lon"]), float(rows[0]["lat"]))
        L = math.hypot(tx - fx, ty - fy)
        end = (tx - (tx - fx) / L * 11, ty - (ty - fy) / L * 11)
        body.append(arrow((fx, fy), end, 3.0, 11.0, AXIS, bend=-0.18))
        _occupy(labels, (fx, fy), end, -0.18, 7)
        marks.append((fx, fy, rows[0], AXIS))
        lines = [(rows[0]["name"], 7.6, AXIS, "bold")]
        for r in rs:
            lines.append((f"{r['units']} · {'night of ' if r['night'] else ''}{_night(r['date'], r['night'])} 1943", 6.4,
                          INK, "normal"))
        words.append((fx, fy, lines))
    # defenders: an arrow from each field to where they would meet the raiders, back along the raiders' line from the
    # target (or north of the target where no raider's field is drawn)
    if marks:
        mx, my = marks[0][0], marks[0][1]
        L = math.hypot(mx - tx, my - ty) or 1
        reach = min(70.0, 0.25 * L)
        meet = (tx + (mx - tx) / L * reach, ty + (my - ty) / L * reach)
    else:
        meet = f.xy(t_lon + 0.2, t_lat + 0.4)
    seen = set()
    for a in fields:
        if a["side"] not in ("uk", "us") or a["field"] in seen and a["role"] == "day fighters":
            continue
        fx, fy = f.xy(float(a["lon"]), float(a["lat"]))
        ax_, ay_ = meet
        if math.hypot(ax_ - fx, ay_ - fy) < 24:
            continue
        body.append(arrow((fx, fy), (ax_, ay_), 2.0, 7.0, ALLIED, bend=0.3, opacity=0.75))
        _occupy(labels, (fx, fy), (ax_, ay_), 0.3, 5)
        if a["field"] not in seen:
            marks.append((fx, fy, a, ALLIED))
        seen.add(a["field"])
    # the target
    body.append(f'<circle cx="{tx:.1f}" cy="{ty:.1f}" r="7.5" fill="none" stroke="#ffffff" stroke-width="3.4"/>'
                f'<circle cx="{tx:.1f}" cy="{ty:.1f}" r="7.5" fill="none" stroke="{TARGET}" stroke-width="1.6"/>'
                f'<circle cx="{tx:.1f}" cy="{ty:.1f}" r="2" fill="{TARGET}"/>')
    labels.occupy(tx - 9, ty - 9, 18, 18)
    # the extent's own units (records/army), each at its position in the air view's window: a dot where it was, and
    # its FM 21-30 symbol set off on a leader (at this scale Lake Bizerte is a few points across), with its dates
    lo_s, hi_s = lo.isoformat(), hi.isoformat()
    ours = [m for m in record.marks(ex) if m["kind"] == "station" and m.get("symbol")
            and m["from"] <= hi_s and m["until"] >= lo_s]
    slot = 0
    for m in ours:                                       # the guns' reach, under everything of ours
        if m.get("reach"):
            mx, my = f.xy(m["lon"], m["lat"])
            r = float(m["reach"]["range_yd"]) * 0.9144 * f.k / (6371000 * math.cos(math.radians(m["lat"])))
            body.append(reach_ring(mx, my, r, m["colour"], m["reach"], words=False))
    for m in sorted(ours, key=lambda m: m["from"]):
        mx, my = f.xy(m["lon"], m["lat"])
        sx_, sy_ = max(26.0, tx - 175), ty + 34 + 34 * slot   # inland, west of the harbour, one under the other
        slot += 1
        body.append(f'<path d="M{mx:.1f},{my:.1f} L{sx_ + 9:.1f},{sy_:.1f}" stroke="{m["colour"]}" '
                    f'stroke-width="0.7" fill="none"/>')
        body.append(f'<circle cx="{mx:.1f}" cy="{my:.1f}" r="2.2" fill="{m["colour"]}" stroke="#ffffff" '
                    f'stroke-width="0.8"/>')
        body.append(f'<rect x="{sx_ - 12:.1f}" y="{sy_ - 9:.1f}" width="24" height="16" fill="#ffffff" '
                    f'fill-opacity="0.85"/>')
        body.append(symbols.symbol(sx_, sy_, m["symbol"], colour=m["colour"], scale=1.15))
        labels.occupy(sx_ - 14, sy_ - 11, 40, 22)
        d0, d1 = date.fromisoformat(m["from"]), date.fromisoformat(m["until"])
        span = f"{m['place']}, {d0.day} {MONTHS[d0.month - 1]} – {d1.day} {MONTHS[d1.month - 1]} 1943"
        if m.get("placed") == "town":
            span += " (the town; position not given)"
        body.append(_text(sx_ + 20, sy_ - 1, m["short"], 6.8, m["colour"], weight="bold"))
        body.append(_text(sx_ + 20, sy_ + 7, span, 5.8, INK))
        labels.occupy(sx_ + 18, sy_ - 9, 5.8 * 0.45 * max(len(span), len(m["short"]) * 1.2) + 4, 18)
    body.append(labels.place(tx, ty, [(t_name, 8.4, TARGET, "bold", DISPLAY),
                                      (cfg.get("target_words", "the harbour, the raids' target"), 6.2, TARGET,
                                       "normal", DISPLAY)], force=True, gap=10))
    # the airfields, then their names and units
    for fx, fy, _a, col in marks:
        if col == AXIS:
            body.append(f'<rect x="{fx - 4.2:.1f}" y="{fy - 4.2:.1f}" width="8.4" height="8.4" fill="#ffffff" '
                        f'stroke="{col}" stroke-width="1.4"/><path d="M{fx - 2.6:.1f},{fy:.1f} h5.2 M{fx:.1f},'
                        f'{fy - 2.6:.1f} v5.2" stroke="{col}" stroke-width="1.6"/>')
        else:
            body.append(f'<circle cx="{fx:.1f}" cy="{fy:.1f}" r="4.4" fill="#ffffff" stroke="{col}" '
                        f'stroke-width="1.4"/><circle cx="{fx:.1f}" cy="{fy:.1f}" r="1.8" fill="{col}"/>')
        labels.occupy(fx - 6, fy - 6, 12, 12)
    for fx, fy, lines in words:
        body.append(labels.place(fx, fy, [(t, sz, c, wt, DISPLAY) for t, sz, c, wt in lines], force=True, gap=8))
    allied: dict[str, list[dict]] = {}
    for a in fields:
        if a["side"] in ("uk", "us"):
            allied.setdefault(a["field"], []).append(a)
    for rows in allied.values():
        fx, fy = f.xy(float(rows[0]["lon"]), float(rows[0]["lat"]))
        lines = [(rows[0]["name"], 7.4, ALLIED, "bold", DISPLAY)]
        for a in rows:
            d0, d1 = date.fromisoformat(a["from"]), date.fromisoformat(a["to"])
            lines.append((f"{a['units']}, {d0.day} {MONTHS[d0.month - 1]} – {d1.day} {MONTHS[d1.month - 1]}",
                          6.2, INK, "normal", DISPLAY))
        body.append(labels.place(fx, fy, lines, force=True, gap=8))
    body += over
    body.append("</g>")
    # the map's marks: nautical miles (the sea between the airfields, and the airmen's own unit), north up (Mercator)
    bar, _ = mapmarks.scale(10, H - 14, 1 / (f.nm_per_pt() * 1.852), "sea", max_len=W / 5)
    body.append(bar + mapmarks.north(W - 14, H - 14, 0))
    # the column beside the map: what an arrow is, then the raids as the record gives them
    sx = W + 12
    body.append(_text(sx, 9, "ARROWS SHOW DIRECTION, NOT ROUTES", 6.2, INK, weight="bold"))
    body.append(arrow((sx + 2, 26), (sx + 36, 23), 2, 6.5, AXIS, bend=-0.2))
    body.append(_text(sx + 42, 27, "raiders, from their airfield", 6.2, INK))
    body.append(arrow((sx + 2, 44), (sx + 36, 41), 1.6, 5, ALLIED, bend=0.25, opacity=0.75))
    body.append(_text(sx + 42, 45, "night fighters, to meet them", 6.2, INK))
    rings = [m for m in ours if m.get("reach")]
    if rings:
        m = rings[0]
        defs, fill = reach_fill(m["colour"])
        body.append(f'{defs}<circle cx="{sx + 19:.1f}" cy="57" r="6" fill="{fill}" '
                    f'stroke="{m["colour"]}" stroke-width="0.9" stroke-dasharray="3 2"/>')
        body.append(_text(sx + 42, 56.5, f"{m['short']}'s guns' reach:", 6.2, INK))
        body.append(_text(sx + 42, 64.5, f"{m['reach']['weapon']} (inferred), {int(m['reach']['range_yd']):,} yd",
                          6.2, INK))
    rows = sorted(raids, key=lambda r: r["date"])
    ground = [g for g in record.raids(ex) if lo_s <= g["date"] <= hi_s]
    y = 84.0
    body.append(_text(sx, y, f"RAIDS ON {t_name.upper()}", 7.0, INK, weight="bold"))
    body.append(_text(sx, y + 9, "as the German Naval Staff's war diary records them", 5.8, MUTED, italic=True))
    y += 24
    cols = int((side - 4) / (6.0 * 0.45))
    for r in rows:
        body.append(_text(sx, y, _night(r["date"], r["night"]), 6.6, AXIS, weight="bold"))
        body.append(_text(sx + 40, y, r["force"], 6.4, INK, weight="bold"))
        res = r["result"] + (f"; {r['losses']}" if r["losses"] else "")
        if r["units"]:
            res += f". {r['units']}"
        for g in ground:       # the defenders' own record of the same night, where one exists
            gd = date.fromisoformat(g["date"])
            if 0 <= (gd - date.fromisoformat(r["date"])).days <= 1:
                said = g["text"].split(", ", 1)[-1] if g["text"].lower().startswith("alerted") else g["text"]
                res += f". {g['short']}, {gd.day} {MONTHS[gd.month - 1]} {g['time']}: \u201c{said}\u201d"
        words, line, out = res.split(), "", []
        for wd in words:
            if len(line) + len(wd) + 1 > cols - 8:
                out.append(line)
                line = wd
            else:
                line = (line + " " + wd).strip()
        out.append(line)
        for k, ln in enumerate(out[:5]):
            body.append(_text(sx + 40, y + 8.5 * (k + 1), ln, 6.0, MUTED))
        y += 8.5 * (min(len(out), 5) + 1) + 6
    body.append(_text(sx, y + 4, "Units and airfields only where a source names", 5.8, MUTED, italic=True))
    body.append(_text(sx, y + 12, "them (the arrows); the others' are not recorded.", 5.8, MUTED, italic=True))
    body.append(f'<rect width="{W:.1f}" height="{H:.1f}" fill="none" stroke="{INK}" stroke-width="0.6"/>')
    notes = {"raids": [{k: r[k] for k in ("date", "night", "force", "result", "units", "from_field", "page")} for r in rows],
             "airfields": [{k: a[k] for k in ("field", "name", "side", "units", "from", "to", "basis", "page")}
                           for a in fields]}
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{total:.1f}pt" height="{H:.1f}pt" viewBox="0 0 '
           f'{total:.1f} {H:.1f}">{"".join(body)}</svg>')
    return halo.split(svg), notes
