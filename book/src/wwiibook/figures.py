"""An engagement's figures for print, drawn as SVG from the kit's engagements/<id>/engagement.json: the same merged,
GMT-clocked records the site's engagement page draws, so the book and the page can't disagree.

  map        the boats' tracks, the convoy where each boat saw it, the attacks, the Japanese records' positions,
             FRUPAC's estimates, and a dotted line from each attack to the Japanese record of it
  timeline   a lane per boat, the convoy and FRUPAC on one GMT axis, night shaded, each attack joined to its
             Japanese record with the minutes between them

Both number the same marks the same way (attacks, the Japanese records of attacks and losses, FRUPAC's notes, in
time order), and return them as a key: number, GMT, the time as typed, who, what, and the citation. Marks left
unnumbered (contacts, log entries, depth charges) are cited in groups. Units are points, so a stroke or a type size
here is its printed size.
"""
import json
import math
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from html import escape
from typing import Any

from . import geo, halo, paths, symbols

INK, MUTED, RULE, PAPER = "#1c221d", "#586257", "#c4cbbf", "#fbfaf6"
OWN, JP, INTEL, LAND, SEA, NIGHT = "#a3241b", "#4d5963", "#8a6d1f", "#d4dbcc", "#f3f5f1", "#e6e9e3"
DISPLAY = "IBM Plex Sans, IBM Plex Sans Condensed, Arial Narrow, sans-serif"   # Typst files IBM Plex Sans Condensed as family IBM Plex Sans
TYPED = "Courier Prime, Courier New, Courier, monospace"
SERIF = "Newsreader, Georgia, serif"

NUMBERED = {("track", "attack"), ("japanese", "torpedoed"), ("japanese", "sank"), ("japanese", "attacked_no_damage"),
            ("frupac", "attacked"), ("frupac", "hit"), ("frupac", "damage"), ("frupac", "sighting")}
JP_WORDS = {"torpedoed": "torpedoed", "sank": "sank", "attacked_no_damage": "torpedoes, no damage", "rescue": "rescue"}
# Navy time zone letters: Z is GMT; A-I are 1-9 hours ahead, K-M 10-12 (no J); N-Y 1-12 hours behind.
ZONES = {"Z": 0, **{c: i for i, c in enumerate("ABCDEFGHI", 1)}, "K": 10, "L": 11, "M": 12,
         **{c: -i for i, c in enumerate("NOPQRSTUVWXY", 1)}}


def load(engagement: str) -> dict:
    return json.loads((paths.records() / "engagements" / engagement / "engagement.json").read_text())


def _t(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@dataclass
class Mark:
    n: int
    utc: str
    local: str
    lane: str
    what: str
    cite: str
    source_kind: str
    origin: str
    kind: str
    lon: float | None = None
    lat: float | None = None
    note: str = ""         # the kit's note on the record: what the position is, a doubt, a disagreement


@dataclass
class Sorted:
    lanes: list[tuple[str, str]]                  # (id, name), top to bottom
    events: list[dict]                            # every timed event, with its lane
    marks: list[Mark]                             # the numbered ones
    pairs: list[tuple[dict, dict]] = field(default_factory=list)   # (attack event, Japanese record) both timed


def sort(d: dict) -> Sorted:
    us = [p for p in d["participants"] if p["of"] == "us" and p["kind"] == "submarine"]
    jp = [p for p in d["participants"] if p["of"] == "jp"]
    lanes = [(p["id"], p["name"]) for p in us] + [(p["id"], p["name"]) for p in jp] + [("frupac", "FRUPAC")]
    jp_lane = jp[0]["id"] if jp else "jp"
    events: list[dict[str, Any]] = []
    for e in d["events"]:
        if not e.get("utc") or e["kind"] == "weather":
            continue
        lane = jp_lane if e["origin"] == "japanese" else "frupac" if e["origin"] == "frupac" else e["actor"]
        events.append({**e, "lane": lane})
    events.sort(key=lambda e: e["utc"])
    relation = {(p["boat"], p["utc"]): p["relation"] for p in d.get("pairs", [])}
    marks = []
    for e in events:
        if (e["origin"], e["kind"]) not in NUMBERED:
            continue
        if e["origin"] == "track":
            rel = relation.get((e["actor"], e["utc"]))
            what = f"{e['actor'].upper()}: {e.get('title') or 'attack'}" + (f" ({rel.replace('_', ' ')})" if rel else "")
        elif e["origin"] == "japanese":
            what = f"{e.get('ship') or e['actor']}: {JP_WORDS.get(e['kind'], e['kind'])}"
        else:
            what = f"FRUPAC map note: {e.get('words', '')}"
        c: dict[str, Any] = e.get("cite") or {}
        marks.append(Mark(len(marks) + 1, e["utc"], e.get("local", ""), e["lane"], what, c.get("ref", ""),
                          c.get("kind", ""), e["origin"], e["kind"], e.get("lon"), e.get("lat"), e.get("note") or ""))
    pairs = []
    attacks = {(e["actor"], e["utc"]): e for e in events if e["origin"] == "track" and e["kind"] == "attack"}
    for p in d.get("pairs", []):
        rec = p.get("record") or {}
        a = attacks.get((p["boat"], p["utc"]))
        if a and rec.get("utc"):
            pairs.append((a, rec))
    return Sorted(lanes, events, marks, pairs)


def grouped_cites(s: Sorted) -> list[str]:
    """The unnumbered marks' citations, grouped by lane and kind: 'BANG, contacts: rg38-74802746/p13, p14'."""
    names = dict(s.lanes)
    words = {"sighting": "contacts", "received": "reports received", "log": "log entries", "depth_charge": "depth charges",
             "status": "depth and status", "rescue": "rescue"}
    groups: dict[tuple[str, str], list[str]] = {}
    for e in s.events:
        if (e["origin"], e["kind"]) in NUMBERED:
            continue
        ref = (e.get("cite") or {}).get("ref", "")
        refs = groups.setdefault((names.get(e["lane"], e["lane"]), words.get(e["kind"], e["kind"])), [])
        if ref and ref not in refs:
            refs.append(ref)
    return [f"{lane}, {kind}: {', '.join(refs)}" for (lane, kind), refs in groups.items()]


def zones_line(s: Sorted) -> str:
    names = dict(s.lanes)
    seen: dict[str, list[str]] = {}
    for e in s.events:
        z = (e.get("local") or "").split(" ")[-1]
        if z in ZONES:
            who = names.get(e["lane"], e["lane"])
            if who not in seen.setdefault(z, []):
                seen[z].append(who)
    parts = [f"{' and '.join(w)} zone {z} (GMT{ZONES[z]:+d})" if ZONES[z] else f"{' and '.join(w)} GMT"
             for z, w in sorted(seen.items(), key=lambda kv: -ZONES[kv[0]])]
    return "Times as typed: " + "; ".join(parts)


# ---------------------------------------------------------------- SVG pieces

def _text(x, y, s, size=7.0, fill=INK, family=DISPLAY, anchor="start", weight="normal", italic=False, halo=False):
    style = ' font-style="italic"' if italic else ""
    h = f' stroke="{PAPER}" stroke-width="2.2" stroke-linejoin="round" paint-order="stroke"' if halo else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{family}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}" font-weight="{weight}"{style}{h}>{escape(s)}</text>')


def _svg(w, h, body):
    return halo.split(f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.1f}pt" height="{h:.1f}pt" '
            f'viewBox="0 0 {w:.1f} {h:.1f}">{"".join(body)}</svg>')


def _symbol(kind, origin, x, y, colour, size=4.0):
    s = size
    if origin == "frupac":
        return (f'<path d="M{x:.1f},{y - s:.1f} L{x + s:.1f},{y:.1f} L{x:.1f},{y + s:.1f} L{x - s:.1f},{y:.1f} Z" '
                f'fill="{PAPER}" stroke="{INTEL}" stroke-width="1"/>')
    if kind == "attack":
        return (f'<path d="M{x:.1f},{y - s:.1f} L{x + s * 0.9:.1f},{y + s * 0.6:.1f} L{x - s * 0.9:.1f},{y + s * 0.6:.1f} Z" '
                f'fill="{colour}" stroke="{PAPER}" stroke-width="0.6"/>')
    if kind in ("torpedoed", "attacked_no_damage"):
        fill = JP if kind == "torpedoed" else "none"
        return (f'<path d="M{x - s * .8:.1f},{y - s * .8:.1f} L{x + s * .8:.1f},{y + s * .8:.1f} M{x + s * .8:.1f},{y - s * .8:.1f} '
                f'L{x - s * .8:.1f},{y + s * .8:.1f}" stroke="{JP}" stroke-width="1.4"/>'
                + (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{s:.1f}" fill="none" stroke="{JP}" stroke-width="0.7"/>'
                   if fill == "none" else ""))
    if kind == "sank":
        return f'<rect x="{x - s * .7:.1f}" y="{y - s * .7:.1f}" width="{s * 1.4:.1f}" height="{s * 1.4:.1f}" fill="{JP}"/>'
    if kind == "sighting":
        return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{s * 0.45:.1f}" fill="{PAPER}" stroke="{colour}" stroke-width="0.8"/>'
    if kind == "depth_charge":
        return (f'<path d="M{x - s * .6:.1f},{y - s * .4:.1f} L{x + s * .6:.1f},{y - s * .4:.1f} L{x:.1f},{y + s * .6:.1f} Z" '
                f'fill="{colour}"/>')
    if kind == "rescue":
        return (f'<path d="M{x - s * .6:.1f},{y:.1f} H{x + s * .6:.1f} M{x:.1f},{y - s * .6:.1f} V{y + s * .6:.1f}" '
                f'stroke="{JP}" stroke-width="1"/>')
    return f'<line x1="{x:.1f}" y1="{y - s * .6:.1f}" x2="{x:.1f}" y2="{y + s * .6:.1f}" stroke="{colour}" stroke-width="0.8"/>'


# The boats' colours, in participant order (guides/ENGAGEMENTS.md, "Colour": checked for colour blindness with the hit
# red, every pair). Red is reserved for hits and is never a boat's colour.
BOATS = ("#2a6fc9", "#008f78", "#6a3a9e")


def _boat_colour(d: dict, lane: str) -> str:
    us = [p for p in d["participants"] if p["of"] == "us"]
    p = next((p for p in us if p["id"] == lane), None)
    i = (p.get("colour") or us.index(p) + 1) - 1 if p else 0
    return BOATS[i % len(BOATS)]


def _lane_colour(lane: str, d: dict, follow: str) -> str:
    """Each US boat in its own colour; the other side in its cool grey; FRUPAC in ochre. The boat the book follows is
    drawn heavier (in the tracks), not in another hue."""
    p = next((p for p in d["participants"] if p["id"] == lane), None)
    if p is None:
        return INTEL
    if p["of"] != "us":
        return JP
    return _boat_colour(d, lane)


def _follow(d: dict, follow: str | None) -> str:
    return follow or next(p["id"] for p in d["participants"] if p["of"] == "us")


def _merged(items: list[tuple[float, int]], gap: float) -> list[tuple[float, str]]:
    """Numbers whose marks sit within `gap` points of each other along a lane share one label: '3–5', '13, 15'."""
    out: list[list] = []
    for x, n in sorted(items):
        if out and x - out[-1][1] < gap:
            out[-1][1] = x
            out[-1][2].append(n)
        else:
            out.append([x, x, [n]])
    def words(ns):
        ns = sorted(ns)
        return f"{ns[0]}–{ns[-1]}" if len(ns) > 2 and ns[-1] - ns[0] == len(ns) - 1 else ", ".join(map(str, ns))
    return [((a + b) / 2, words(ns)) for a, b, ns in out]


def _labels_for(points: list[tuple[float, float, int]], gap: float = 3.0):
    """Marks that fall on one spot share a label: [(x, y, '2, 3'), ...]."""
    out: list[list] = []
    for x, y, n in points:
        for o in out:
            if abs(o[0] - x) < gap and abs(o[1] - y) < gap:
                o[2].append(n)
                break
        else:
            out.append([x, y, [n]])
    return [(x, y, ", ".join(map(str, ns))) for x, y, ns in out]


# ---------------------------------------------------------------- the map

def engagement_map(engagement: str, width_in: float = 5.5, box: list[float] | None = None,
                   follow: str | None = None) -> tuple[str, Sorted]:
    d = load(engagement)
    s = sort(d)
    follow = _follow(d, follow)
    b = box or d["box"]
    f = geo.fit((b[0], b[1], b[2], b[3]), width_in * 72, pad=0.0 if box else 0.06)
    W, H = f.width, f.height
    body = [f'<defs><clipPath id="frame"><rect width="{W:.1f}" height="{H:.1f}"/></clipPath></defs>',
            f'<rect width="{W:.1f}" height="{H:.1f}" fill="{SEA}"/>', '<g clip-path="url(#frame)">']
    for ring in geo.land_rings((f.lon0 - 1, f.lat0 - 1, f.lon1 + 1, f.lat1 + 1)):
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in (f.xy(lo, la) for lo, la in ring))
        body.append(f'<polygon points="{pts}" fill="{LAND}" stroke="#b6bfad" stroke-width="0.4"/>')
    # graticule every degree
    for lon in range(math.ceil(f.lon0), math.floor(f.lon1) + 1):
        x, _ = f.xy(lon, f.lat0)
        body.append(f'<line x1="{x:.1f}" y1="0" x2="{x:.1f}" y2="{H:.1f}" stroke="{RULE}" stroke-width="0.4"/>')
        body.append(_text(x + 2, H - 3, f"{lon}°E", 6, MUTED))
    for lat in range(math.ceil(f.lat0), math.floor(f.lat1) + 1):
        _, y = f.xy(f.lon0, lat)
        body.append(f'<line x1="0" y1="{y:.1f}" x2="{W:.1f}" y2="{y:.1f}" stroke="{RULE}" stroke-width="0.4"/>')
        body.append(_text(3, y - 2, f"{lat}°N", 6, MUTED))
    for p in d.get("places", []):
        x, y = f.xy(p["lon"], p["lat"])
        if 0 < x < W and 0 < y < H:
            anchor = "end" if x > W - 50 else "start" if x < 50 else "middle"
            body.append(_text(x, y, p["name"], 8, MUTED, italic=True, anchor=anchor, halo=True))
    # tracks: each boat's own fixes in time order; a leg dashed where an end is assumed
    for who, fixes in d["tracks"].items():
        own = sorted((x for x in fixes if x.get("on_track")), key=lambda x: x["utc"])
        colour, sw = _boat_colour(d, who), (1.4 if who == follow else 0.9)
        for a, c in zip(own, own[1:]):
            (x1, y1), (x2, y2) = f.xy(a["lon"], a["lat"]), f.xy(c["lon"], c["lat"])
            dash = ' stroke-dasharray="3 2"' if a.get("assumed") or c.get("assumed") else ""
            body.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{colour}" '
                        f'stroke-width="{sw}" stroke-linecap="round"{dash}/>')
        if own:
            x, y = f.xy(own[-1]["lon"], own[-1]["lat"])
            body.append(_text(x + 4, y + 3, who.upper(), 7.5, colour, weight="bold", halo=True))
    # pair lines: an attack's position to the Japanese record's position of the same event
    for a, rec in s.pairs:
        if a.get("lat") is not None and rec.get("lat") is not None:
            (x1, y1), (x2, y2) = f.xy(a["lon"], a["lat"]), f.xy(rec["lon"], rec["lat"])
            body.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{JP}" '
                        f'stroke-width="0.7" stroke-dasharray="0.8 1.6" stroke-linecap="round"/>')
    # contacts (unnumbered), then the numbered marks
    for e in s.events:
        if e["kind"] == "sighting" and e["origin"] == "track" and e.get("lat") is not None:
            x, y = f.xy(e["lon"], e["lat"])
            body.append(_symbol("sighting", "track", x, y, _lane_colour(e["lane"], d, follow)))
    pts = []
    for m in s.marks:
        if m.lat is None or m.lon is None:
            continue
        x, y = f.xy(m.lon, m.lat)
        body.append(_symbol(m.kind, m.origin, x, y, _lane_colour(m.lane, d, follow)))
        pts.append((x, y, m.n))
    for x, y, label in _labels_for(pts):
        body.append(_text(x + 5, y - 4, label, 7, INK, weight="bold", halo=True))
    body.append("</g>")
    # scale bar, 20 nautical miles
    nm = 20
    L = nm / f.nm_per_pt()
    x0, y0 = W - L - 12, H - 12
    body.append(f'<path d="M{x0:.1f},{y0:.1f} h{L:.1f} M{x0:.1f},{y0 - 3:.1f} v3 M{x0 + L:.1f},{y0 - 3:.1f} v3" '
                f'stroke="{INK}" stroke-width="0.8" fill="none"/>')
    body.append(_text(x0 + L / 2, y0 - 4, f"{nm} nautical miles", 6.5, INK, anchor="middle", halo=True))
    body.append(f'<rect width="{W:.1f}" height="{H:.1f}" fill="none" stroke="{INK}" stroke-width="0.6"/>')
    return _svg(W, H, body), s


# ---------------------------------------------------------------- the timeline

def sun(day: date, lat: float, lon: float) -> tuple[datetime, datetime]:
    """Sunrise and sunset (GMT) on a day at a place: the sunrise equation (Meeus, simplified), good to a minute or two."""
    jd = datetime(day.year, day.month, day.day, 12, tzinfo=UTC).timestamp() / 86400 + 2440587.5
    n = jd - 2451545.0 + 0.0008
    js = n - lon / 360
    M = math.radians((357.5291 + 0.98560028 * js) % 360)
    C = 1.9148 * math.sin(M) + 0.02 * math.sin(2 * M) + 0.0003 * math.sin(3 * M)
    lam = math.radians((math.degrees(M) + C + 180 + 102.9372) % 360)
    transit = 2451545.0 + js + 0.0053 * math.sin(M) - 0.0069 * math.sin(2 * lam)
    dec = math.asin(math.sin(lam) * math.sin(math.radians(23.4397)))
    phi = math.radians(lat)
    w0 = math.degrees(math.acos((math.sin(math.radians(-0.833)) - math.sin(phi) * math.sin(dec))
                                / (math.cos(phi) * math.cos(dec))))

    def dt(j):
        return datetime.fromtimestamp((j - 2440587.5) * 86400, tz=UTC)

    return dt(transit - w0 / 360), dt(transit + w0 / 360)


def engagement_timeline(engagement: str, width_in: float = 5.5, window: list[str] | None = None,
                        follow: str | None = None) -> tuple[str, Sorted]:
    d = load(engagement)
    s = sort(d)
    follow = _follow(d, follow)
    t0, t1 = (_t(window[0]), _t(window[1])) if window else (_t(d["window"]["from"]), _t(d["window"]["to"]))
    W = width_in * 72
    lanes = [ln for ln in s.lanes if any(e["lane"] == ln[0] for e in s.events)]
    left = 10 + 7.5 * 0.56 * max(len(name) for _, name in lanes)     # the longest lane name, at 7.5 pt condensed
    right, top, lane_h = 8.0, 20.0, 26.0
    H = top + lane_h * len(lanes) + 26
    span = (t1 - t0).total_seconds()

    def X(t: datetime) -> float:
        return left + (W - left - right) * (t - t0).total_seconds() / span

    row = {lane: top + lane_h * (i + 0.5) for i, (lane, _) in enumerate(lanes)}
    body = [f'<rect width="{W:.1f}" height="{H:.1f}" fill="{PAPER}"/>']
    # night, at the middle of the engagement's box
    b = d["box"]
    lat, lon = (b[1] + b[3]) / 2, (b[0] + b[2]) / 2
    day = (t0 - timedelta(days=1)).date()
    while day <= t1.date():
        _, sunset = sun(day, lat, lon)
        sunrise, _ = sun(day + timedelta(days=1), lat, lon)
        a, z = max(sunset, t0), min(sunrise, t1)
        if a < z:
            body.append(f'<rect x="{X(a):.1f}" y="{top - 6:.1f}" width="{X(z) - X(a):.1f}" '
                        f'height="{lane_h * len(lanes) + 6:.1f}" fill="{NIGHT}"/>')
            body.append(_text(X(a) + 2, top - 1, "night", 6, MUTED, italic=True))
        day += timedelta(days=1)
    # hours, every two, GMT; the date at midnight
    t = t0.replace(minute=0, second=0) + timedelta(hours=(t0.hour % 2 != 0) + (t0.minute > 0))
    while t <= t1:
        x = X(t)
        body.append(f'<line x1="{x:.1f}" y1="{top - 6:.1f}" x2="{x:.1f}" y2="{top + lane_h * len(lanes):.1f}" '
                    f'stroke="{RULE}" stroke-width="{0.8 if t.hour == 0 else 0.3}"/>')
        label = t.strftime("%H%M") + ("Z" if t == t0 or t.hour == 0 else "")
        body.append(_text(x, top + lane_h * len(lanes) + 9, label, 6.5, MUTED, anchor="middle"))
        if t.hour == 0:
            body.append(_text(x, top + lane_h * len(lanes) + 18, f"{t.day} {t:%B}", 6.5, INK, anchor="middle",
                              weight="bold"))
        t += timedelta(hours=2)
    for lane, name in lanes:
        y = row[lane]
        body.append(f'<line x1="{left:.1f}" y1="{y:.1f}" x2="{W - right:.1f}" y2="{y:.1f}" stroke="{RULE}" stroke-width="0.6"/>')
        body.append(_text(left - 6, y + 2.5, name, 7.5, _lane_colour(lane, d, follow), anchor="end", weight="bold"))
    # pairs: an attack joined to its Japanese record, with the minutes between the two clocks
    rec_lane = next((e["lane"] for e in s.events if e.get("origin") == "japanese"), None)
    by_record: dict[str, list[tuple[float, float, float, int]]] = {}
    for a, rec in s.pairs:
        if a["lane"] not in row or rec_lane not in row:
            continue
        ta, tr = _t(a["utc"]), _t(rec["utc"])
        x1, y1, x2, y2 = X(ta), row[a["lane"]], X(tr), row[rec_lane]
        body.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{JP}" stroke-width="0.6" '
                    f'stroke-dasharray="0.8 1.4"/>')
        by_record.setdefault(rec["utc"], []).append((x2, y1, y2, round((ta - tr).total_seconds() / 60)))
    for i, (_, joins) in enumerate(sorted(by_record.items())):
        x2, y1, y2 = joins[0][0], joins[0][1], joins[0][2]
        mins = " and ".join(f"{abs(m)}" for m in sorted({j[3] for j in joins}, key=abs))
        y = y1 + (y2 - y1) * (0.3 + 0.3 * (i % 2))
        body.append(_text(x2 + 3, y + 2, f"{mins} min", 5.8, JP, halo=True))
    numbers = {(m.utc, m.lane, m.kind): m.n for m in s.marks}
    per_lane: dict[str, list[tuple[float, int]]] = {}
    for e in s.events:
        if e["lane"] not in row:
            continue
        x, y = X(_t(e["utc"])), row[e["lane"]]
        body.append(_symbol(e["kind"], e["origin"], x, y, _lane_colour(e["lane"], d, follow), size=3.6))
        n = numbers.get((e["utc"], e["lane"], e["kind"]))
        if n:
            per_lane.setdefault(e["lane"], []).append((x, n))
    order = [lane for lane, _ in lanes]
    for lane, items in per_lane.items():
        below = order.index(lane) >= len(order) / 2
        for x, label in _merged(items, gap=10):
            y = row[lane] + (11 if below else -6)
            body.append(_text(x, y, label, 6.5, INK, anchor="middle", weight="bold", halo=True))
    return _svg(W, H, body), s


def render(kind: str, engagement: str, width_in: float, box=None, window=None, follow=None) -> tuple[str, Sorted]:
    if kind == "map":
        return engagement_map(engagement, width_in, box, follow)
    if kind == "timeline":
        return engagement_timeline(engagement, width_in, window, follow)
    raise ValueError(f"no figure called {kind!r}")


# ---------------------------------------------------------------- a person's route (Army stations)

FRONT = "#3b4a3e"


def _month(d: str | None) -> str:
    if not d:
        return "…"
    t = date.fromisoformat(d)
    return f"{t:%b} {t.year}"


def _day(d: str | None) -> str:
    if not d:
        return "…"
    t = date.fromisoformat(d)
    return f"{t.day} {t:%b}"


def _span_words(first: dict, last: dict, short: bool) -> str:
    a, b = first.get("from"), last.get("to")
    f = _day if short else _month
    return f(a) if (f(a) == f(b) or not b) else f"{f(a)} – {f(b)}"


def _fronts(day: str) -> list[list[tuple[float, float]]]:
    path = paths.records() / "fronts" / f"12ag-{day}.geojson"
    if not path.exists():
        return []
    d = json.loads(path.read_text())
    return [[(c[0], c[1]) for c in f["geometry"]["coordinates"]] for f in d["features"]
            if f["properties"].get("kind") == "front" and f["geometry"]["type"] == "LineString"]


def _units(day: str) -> list[dict]:
    path = paths.records() / "fronts" / f"12ag-{day}.geojson"
    if not path.exists():
        return []
    return [{**x["properties"], "lon": x["geometry"]["coordinates"][0], "lat": x["geometry"]["coordinates"][1]}
            for x in json.loads(path.read_text())["features"] if x["properties"].get("kind") == "unit"]


def route_map(data: dict, width_in: float, panels: list[dict], labels: list[str], fronts: list[str],
              window: list[str] | None = None, height_in: float | None = None, legs: str = "full") -> tuple[str, dict]:
    """A person's stations (his units' positions, as a JSON file a family layer supplies beside its book) on one or more
    panels side by side at one height: say the United States and Europe, with the crossing between them.

    How we know: a station is a filled dot where his unit's report places it and he is recorded with the unit; hollow
    where his being with the unit is assumed. A leg is solid between consecutive stations, dashed where the move
    between them isn't recorded (a gap of days, or an assumed end). How precisely: a ring the size of the record's
    working tolerance (a 1 km grid square; a town, about 6 km).

    Each panel is a dict: box (west, south, east, north); title; and the base's options: relief (a terrain-tile zoom),
    admin (state and province lines), countries (whose region names to print), rivers (the largest Natural Earth
    rank drawn), towns (how many to try to label), units (a date: the 12th Army Group's division boxes that day).
    Fronts are the 12th Army Group's traced lines for the days given, the last one strongest."""
    from . import cartography as carto
    stops = [s for s in data["stops"] if not window or (s["from"] or "") <= window[1] and (s["to"] or "9") >= window[0]]
    W = width_in * 72
    gap = 16.0
    boxes = [p["box"] for p in panels]
    ratio = [(geo.fit(tuple(b), 100, pad=0).height / 100) for b in boxes]     # height per point of width
    H = height_in * 72 if height_in else (W - gap * (len(boxes) - 1)) / sum(1 / r for r in ratio)
    frames, x0s, x = [], [], 0.0
    for b, r in zip(boxes, ratio):
        w = H / r
        frames.append(geo.fit(tuple(b), w, pad=0))
        x0s.append(x)
        x += w + gap
    W = x - gap
    under, marks, over = [], [], []
    shown: list[dict] = []
    placers = [carto.Labels((x0, 0, x0 + f.width, H)) for f, x0 in zip(frames, x0s)]

    def where(lon, lat):
        for i, f in enumerate(frames):
            if f.lon0 <= lon <= f.lon1 and f.lat0 <= lat <= f.lat1:
                px, py = f.xy(lon, lat)
                return i, x0s[i] + px, py
        return None

    placed = [(s, where(s["lon"], s["lat"])) for s in stops]
    # the record's marks claim their ground first, so nothing is printed over a station or a division's box
    for _s, at in placed:
        if at:
            placers[at[0]].occupy(at[1] - 2.5, at[2] - 2.5, 5, 5)
    for i, (f, x0, p) in enumerate(zip(frames, x0s, panels)):
        for un in _shown_units(p, f):
            ux, uy = f.xy(un["lon"], un["lat"])
            w = 13 + 2 + carto.Labels.width(symbols.parse_label(un.get("label") or "")[0], 6.8)
            placers[i].occupy(x0 + ux - 7, uy - 9.5, w, 14)
        # lines are soft obstacles: the fronts, and the route's legs
        for day in fronts:
            for line in _fronts(day):
                placers[i].line([(x0 + px, py) for px, py in (f.xy(lo, la) for lo, la in line)])
    for (_a, pa), (_b, pb) in zip(placed, placed[1:]):
        if pa and pb and pa[0] == pb[0]:
            placers[pa[0]].line([(pa[1], pa[2]), (pb[1], pb[2])])
    # route labels next, before the towns: each named place once, with the span of its stations
    route_labels: list[str] = []
    for name in labels:
        group = [(s, at) for s, at in placed if at and s["name"].startswith(name)]
        if not group:
            continue
        (s0, at0), (s1, _) = group[0], group[-1]
        pi, px, py = at0
        short = any(d in (s0.get("from") or "")[:7] for d in ("1944-06", "1944-07"))
        svg = placers[pi].place(px, py, [(name, 7.2, INK, "bold", carto.DISPLAY),
                                         (_span_words(s0, s1, short), 6.2, MUTED, "normal", carto.DISPLAY)], force=True)
        route_labels.append(svg)
    for i, (f, x0, p) in enumerate(zip(frames, x0s, panels)):
        cid = f"p{i}"
        u, o = carto.base(f, x0, H, relief_zoom=p.get("relief"), admin=p.get("admin", False),
                          countries=tuple(p.get("countries", ())), rivers=p.get("rivers", 7), towns=p.get("towns", 0),
                          town_rank=p.get("town_rank", 8), places=tuple(tuple(x) for x in p.get("places", ())),
                          labels=placers[i])
        under.append(f'<defs><clipPath id="{cid}"><rect x="{x0:.1f}" width="{f.width:.1f}" height="{H:.1f}"/></clipPath></defs>')
        under.append(f'<g clip-path="url(#{cid})">' + "".join(u))
        for k, day in enumerate(fronts):
            for line in _fronts(day):
                pts = " ".join(f"{x0 + px:.1f},{py:.1f}" for px, py in (f.xy(lo, la) for lo, la in line))
                last = k == len(fronts) - 1
                under.append(f'<polyline points="{pts}" fill="none" stroke="{FRONT}" stroke-width="{1.5 if last else 0.7}" '
                             f'stroke-opacity="{1 if last else 0.5}" stroke-linejoin="round" stroke-linecap="round"/>')
        for un in _shown_units(p, f):
            ux, uy = f.xy(un["lon"], un["lat"])
            under.append(symbols.symbol(x0 + ux, uy, un, highlight=bool(p.get("highlight")) and un.get("unit") == p["highlight"]))
            shown.append({**un, "highlight": bool(p.get("highlight")) and un.get("unit") == p["highlight"],
                          "words": p.get("highlight_words")})
        under.append("</g>")
        over.append("".join(o))
        under.append(f'<rect x="{x0:.1f}" width="{f.width:.1f}" height="{H:.1f}" fill="none" stroke="{INK}" stroke-width="0.6"/>')
        if p.get("title"):
            over.append(_text(x0 + 6, 11, p["title"].upper(), 7, INK, weight="bold", halo=True))
        km_per_pt = f.nm_per_pt() * 1.852
        target = f.width / 5 * km_per_pt
        km = next(v for v in (1, 2, 5, 10, 20, 50, 100, 200, 500, 1000) if v >= target / 1.6)
        L = km / km_per_pt
        bx, by = x0 + f.width - L - 8, H - 9
        over.append(f'<path d="M{bx:.1f},{by:.1f} h{L:.1f} M{bx:.1f},{by - 3:.1f} v3 M{bx + L:.1f},{by - 3:.1f} v3" '
                    f'stroke="{INK}" stroke-width="0.7" fill="none"/>')
        over.append(_text(bx + L / 2, by - 4, f"{km} km", 6, INK, anchor="middle", halo=True))
    # precision rings, legs, stations
    for s, at in placed:
        if not at:
            continue
        i, px, py = at
        r = s["radius_km"] / (frames[i].nm_per_pt() * 1.852)
        if r > 2.5:
            marks.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{r:.1f}" fill="none" '
                         f'stroke="{OWN}" stroke-opacity="0.4" stroke-width="0.4" stroke-dasharray="1 1.8"/>')
    crossings = []
    leg_w, leg_o = (0.8, 0.55) if legs == "light" else (1.2, 1.0)
    for (a, pa), (b, pb) in zip(placed, placed[1:]):
        if not pa or not pb:
            continue
        unrecorded = a.get("to") and b.get("from") and (date.fromisoformat(b["from"]) - date.fromisoformat(a["to"])).days > 1
        dash = ' stroke-dasharray="3 2.2"' if unrecorded or a["assumed"] or b["assumed"] else ""
        if pa[0] == pb[0]:
            marks.append(f'<line x1="{pa[1]:.1f}" y1="{pa[2]:.1f}" x2="{pb[1]:.1f}" y2="{pb[2]:.1f}" stroke="{OWN}" '
                         f'stroke-width="{leg_w}" stroke-opacity="{leg_o}" stroke-linecap="round"{dash}/>')
        else:
            ea, eb = x0s[pa[0]] + frames[pa[0]].width, x0s[pb[0]]
            marks.append(f'<path d="M{pa[1]:.1f},{pa[2]:.1f} L{ea:.1f},{pa[2]:.1f} M{eb:.1f},{pb[2]:.1f} L{pb[1]:.1f},{pb[2]:.1f}" '
                         f'stroke="{OWN}" stroke-width="1.2" stroke-dasharray="3 2.2" fill="none"/>')
            crossings.append((ea, eb, a, b))
    for s, at in placed:
        if at:
            fill = PAPER if s["assumed"] else OWN
            marks.append(f'<circle cx="{at[1]:.1f}" cy="{at[2]:.1f}" r="2" fill="{fill}" stroke="{OWN}" stroke-width="0.8"/>')
    for ea, eb, a, b in crossings:
        gaps = [g for g in data.get("gaps", []) if (g["from"] or "") >= (a.get("to") or "") and (g["to"] or "9") <= (b.get("from") or "9")]
        words = f"{gaps[0]['what'].title()}, {_day(gaps[0]['from'])} – {_day(gaps[0]['to'])} 1944" if gaps else "crossing"
        over.append(_text((ea + eb) / 2, H - 22, words, 6.5, OWN, anchor="middle", italic=True, halo=True))
    notes = {"stops": len(stops), "fronts": [f"12ag-{d}" for d in fronts],
             "cites": sorted({s["cite"] for s in stops if s["cite"]}), "units": []}
    total_h = H
    if shown:
        hl = next((u["words"] for u in shown if u["highlight"] and u.get("words")), None)
        strip, strip_h = symbols.legend(4, H + 13, {u.get("of", "") for u in shown}, {u.get("arm", "") for u in shown},
                                        any(symbols.parse_label(u.get("label") or "")[1] for u in shown), hl,
                                        max_width=W - 8)
        over.append(strip)
        total_h = H + 8 + strip_h
        seen = set()
        for u in sorted(shown, key=lambda u: (u.get("of") == "de", not u["highlight"], u.get("label") or "")):
            number = symbols.parse_label(u.get("label") or "")[0]
            if (u.get("of"), number) in seen:
                continue
            seen.add((u.get("of"), number))
            notes["units"].append({"number": number, "name": symbols.full_name(u), "side": symbols.SIDE_WORDS.get(u.get("of", ""), ""),
                                   "highlight": u["highlight"], "cite": u.get("cite", "")})
    return _svg(W, total_h, under + marks + over + route_labels), notes


def _shown_units(p: dict, f) -> list[dict]:
    """The divisions (and units whose echelon the map doesn't mark) inside a panel on its `units` day; corps and armies
    are left off a map at this scale."""
    if not p.get("units"):
        return []
    return [u for u in _units(p["units"]) if f.lon0 < u["lon"] < f.lon1 and f.lat0 < u["lat"] < f.lat1
            and (u.get("echelon") == "xx" or (not u.get("echelon") and u.get("arm")))]
