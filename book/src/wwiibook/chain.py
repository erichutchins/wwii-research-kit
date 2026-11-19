"""A unit's chain of command, from the kit's records/army/relations.csv: every link a dated, cited row (`part_of`,
`attached_to`, `under_command`), so the chain is a picture of intervals, not a fixed tree. Two drawings:

  timeline   a row a level (army group, army, corps, division, regiment, battalion, company), months across; each
             bar a parent formation, its shoulder patch and its name as the record prints it. Solid where assigned or
             under command, hatched where attached; dashed where the record infers the link; faded at an end the
             record leaves open. Two links at one level at once (assigned to one army, attached to another) are two
             lanes.
  ladder     the chain on one day, top to bottom, each step its patch, its name, how it was linked and since when,
             and the citation.

Patches are the formations' shoulder sleeve insignia (Wikimedia Commons, public domain US Army designs), listed in
book/insignia/insignia.yml with the file, its licence and the period it was worn; a formation without one is drawn
with its FM 21-30 symbol's box. Unit names only: the people are the family layer's.
"""
import base64
import csv
import io
import math
import re
from dataclasses import dataclass
from datetime import date
from functools import cache
from html import escape

import yaml

from . import halo, paths

INK, MUTED, RULE, PAPER = "#000000", "#586257", "#c4cbbf", "#fbfaf6"
DISPLAY = "IBM Plex Sans, IBM Plex Sans Condensed, Arial Narrow, sans-serif"
SERIF = "Libertinus Serif, Georgia, serif"
INSIGNIA = paths.PACKAGE.parents[1] / "insignia" / "insignia.yml"

# the levels, top to bottom, and how a name says which it is
# the Army's levels, and the Navy's: the operational chain (fleet, task force, task group, task unit) above the
# administrative one (squadron, division); a Seabee battalion's brigade and regiment are the Army's rows
LEVELS = ["theater", "fleet", "army group", "army", "task force", "corps", "task group", "task unit", "squadron",
          "division", "combat command", "brigade", "group", "regiment", "battalion", "company"]
WORDS = {"theater": "Theater", "army group": "Army group", "army": "Army", "corps": "Corps", "division": "Division",
         "combat command": "Combat command", "brigade": "Brigade", "group": "Group", "regiment": "Regiment",
         "battalion": "Battalion", "company": "Company, battery", "fleet": "Fleet", "task force": "Task force",
         "task group": "Task group, pack", "task unit": "Task unit", "squadron": "Squadron"}
RELATION = {"part_of": "part of", "attached_to": "attached to", "under_command": "under",
            "reported_through": "reported through"}


# formations an order-of-battle table puts in a level's column whose names don't say it: SHAEF's reserve and a Com Z
# section (for supply) stand in the ARMY columns
COLUMN = {"shaef-reserve": "army", "oise-section-comz": "army"}


def level(unit: str, name: str) -> str:
    if unit in COLUMN:
        return COLUMN[unit]
    n = f" {name} ".lower()
    if "task force" in n:
        return "task force"
    if " fleet" in n:
        return "fleet"
    if "task unit" in n:
        return "task unit"
    if any(w in n for w in ("task group", "wolfpack", "wolf pack", "attack group", "coordinated patrol", "pack:")):
        return "task group"
    if any(w in n for w in ("submarine squadron", "destroyer squadron")):
        return "squadron"
    if any(w in n for w in ("submarine division", "destroyer division")):
        return "division"
    if "construction regiment" in n:
        return "regiment"
    if "construction brigade" in n:
        return "brigade"
    if any(w in n for w in ("comsopac", "cincpoa", "pacific ocean areas", "south pacific")):
        return "theater"
    u = unit.lower()
    if any(w in n for w in ("etousa", "natousa", "afhq", " sos ", "theater", "allied force")) or u in ("afhq", "etousa"):
        return "theater"
    if "army group" in n or "army-group" in u:
        return "army group"
    if " corps" in n and "coast artillery" not in n:
        return "corps"
    if " army" in n and "army group" not in n:
        return "army"
    if "combat command" in n or u.endswith(("-cca", "-ccb", "-ccr")):
        return "combat command"
    if re.match(r"\s*(company|co\.?|battery|btry|hq battery|medical detachment)\b", n):
        return "company"
    if "div" in n:
        return "division"
    if "brigade" in n:
        return "brigade"
    if " group" in n:
        return "group"
    if any(w in n for w in (" bn", "battalion", "1st bn", "2nd bn")):
        return "battalion"
    if any(w in n for w in ("battery", "btry", " co ", "company", "co.", "med. det", "medical det")):
        return "company"
    if any(w in n for w in ("regt", "regiment", "infantry", "c.a.", "coast artillery")):
        return "regiment"
    return "battalion"


def short(name: str, lv: str) -> list[str]:
    """The name as printed, then shorter forms for a narrow bar, longest first: the corps without its army
    ("V Corps, First US Army"), without "US", without a parenthesis, with the usual abbreviations (the Army's, and the
    Navy's: TF, TG, TU, SubDiv, SubRon, DesDiv, DesRon, NCR)."""
    out = [name]
    n = name.split(",")[0] if lv == "corps" else name
    out.append(n)
    n = n.replace(" US ", " ")
    out.append(n)
    n = re.sub(r"\s*\(.*?\)", "", n)
    out.append(n)
    for a, b in (("Infantry Division", "Inf Div"), ("Armored Division", "Armd Div"), ("Army Group", "AG"),
                 ("Task Force ", "TF "), ("Task Group ", "TG "), ("Task Unit ", "TU "),
                 ("Submarine Division ", "SubDiv "), ("Submarine Squadron ", "SubRon "),
                 ("Destroyer Division ", "DesDiv "), ("Destroyer Squadron ", "DesRon "),
                 ("Naval Construction Regiment", "NCR"), ("Naval Construction Brigade", "Brigade"),
                 ("coordinated attack group: ", "pack: "), ("coordinated patrol: ", "with "),
                 ("Division", "Div"), ("Battalion", "Bn"), ("Regiment", "Regt")):
        n = n.replace(a, b)
    out.append(n)
    if n.startswith(("pack: ", "with ")):              # a pack named by its boats: the others, then fewer
        boats = [b for b in n.split(": ", 1)[-1].replace("with ", "").split(", ") if b != "BANG"]
        out += [", ".join(boats), boats[0] + (" +" if len(boats) > 1 else "")]
    if lv == "army":
        out.append(n.replace(" Army", ""))
    return list(dict.fromkeys(out))


@dataclass
class Span:
    """A dated link: `child` was `relation` `parent` from `start` to `end` (open where the record leaves it)."""
    child: str
    parent: str
    parent_name: str
    relation: str
    start: date
    end: date
    open_start: bool
    open_end: bool
    basis: str
    page: str
    level: str
    own_start: date | None = None          # the record's own start for the link, before the chain clips it


def _day(s: str, lo: bool) -> tuple[date | None, bool]:
    """A relations.csv end: '1944-08-15' exact; '..1944-08-15' on or before (open); '1944-08-15..' on or after;
    '' unknown. Returns the date (or None) and whether the end is open."""
    s = (s or "").strip()
    if not s:
        return None, True
    open_ = s.startswith("..") or s.endswith("..")
    core = s.strip(".")
    if ".." in core:                                    # '..A..B': take the side that bounds this end
        a, b = core.split("..")[0], core.split("..")[-1]
        core = a if lo else b
    try:
        y, m, d = (int(x) for x in core.split("-")[:3])
        return date(y, m, d), open_
    except ValueError:
        return None, True


@cache
def _rows() -> list[dict]:
    out = []
    for part in ("army", "navy"):
        f = paths.records() / part / "relations.csv"
        if f.exists():
            with open(f, newline="") as fh:
                out += list(csv.DictReader(fh))
    return out


@cache
def _names() -> dict[str, str]:
    """Units' names: the Army's and the Seabees' units files, and a ship's name and hull from her ship.yml."""
    out = {}
    for part in ("army", "seabees"):
        f = paths.records() / part / "units.csv"
        if f.exists():
            with open(f, newline="") as fh:
                out.update({r["unit"]: r["name"] for r in csv.DictReader(fh)})
    for folder in ("boats", "ships"):
        for y in (paths.records() / folder).glob("*/ship.yml"):
            d = yaml.safe_load(y.read_text())
            out[y.parent.name] = f"USS {d['name'].title() if d['name'].isupper() else d['name']} ({d.get('hull', '')})"
    return out


@cache
def insignia() -> dict:
    return yaml.safe_load(INSIGNIA.read_text()) if INSIGNIA.exists() else {}


KIND = {"attached_to": "attached", "part_of": "assigned", "under_command": "assigned", "reported_through": "assigned"}


@cache
def links(unit: str) -> tuple[tuple, ...]:
    """A unit's own links as the record dates them: (row, start, end, open_start, open_end), None for an unknown
    end. An end the record leaves blank stops the day before the unit's next link of the same kind at the same level
    begins (a battalion is not attached to two divisions at once, nor assigned to two corps); it is still drawn
    as an open end."""
    rows = [r for r in _rows() if r["unit"] == unit and r["relation"] in RELATION]
    out = []
    for r in rows:
        a, oa = _day(r["from"], True)
        b, ob = _day(r["to"], False)
        lv = level(r["other"], r["other_name"])
        # open: the record's own '..', or a blank end bounded only by the next link. A blank end with no next link
        # (an undated composition, a link that runs past the window) is simply cut by the window or the child's link
        oa, ob = oa and a is not None, ob and b is not None
        if b is None and a is not None:
            nxt = [_day(o["from"], True)[0] for o in rows if o is not r and KIND[o["relation"]] == KIND[r["relation"]]
                   and level(o["other"], o["other_name"]) == lv]
            nxt = [d for d in nxt if d and d > a]
            if nxt:
                b, ob = date.fromordinal(min(nxt).toordinal() - 1), True
        out.append((r, a, b, oa, ob))
    return tuple(out)


def spans(base: str, start: date, end: date, bridge: int = 0) -> list[Span]:
    """Every link in the chain above `base` that holds at some time in [start, end]: the base's own links, then each
    parent's within the time the child was linked to it. A formation reached twice at once (the regiment's own
    division's corps, and the corps of a division it was attached to) is drawn once."""
    out: list[Span] = []

    def walk(unit: str, lo: date, hi: date, depth: int):
        if depth > 8:
            return
        for r, a, b, oa, ob in links(unit):
            a2, b2 = max(a or lo, lo), min(b or hi, hi)
            if a2 > b2:
                continue
            # open is the record's own: an end clipped by the child's link or by the window is a plain end
            out.append(Span(unit, r["other"], r["other_name"], r["relation"], a2, b2, oa and a2 == a,
                            ob and b2 == b, r["basis"], r["page"], level(r["other"], r["other_name"]), a))
            walk(r["other"], a2, b2, depth + 1)
    walk(base, start, end, 0)
    # merge the pieces of one link (one parent reached in several of the child's intervals) that touch or overlap
    out.sort(key=lambda s: (s.child, s.parent, s.relation, s.start))
    merged: list[Span] = []
    for s in out:
        m = merged[-1] if merged else None
        if m and (m.child, m.parent, m.relation) == (s.child, s.parent, s.relation) and not m.open_end \
                and s.start.toordinal() <= m.end.toordinal() + 1:
            if s.end >= m.end:
                m.end, m.open_end = s.end, s.open_end
            continue
        merged.append(s)
    # a formation already drawn over the same days by another path is not drawn again
    keep = [s for s in merged if not any(o is not s and o.parent == s.parent and o.level == s.level
                                         and o.start <= s.start and o.end >= s.end
                                         and (o.start, -o.end.toordinal()) < (s.start, -s.end.toordinal())
                                         for o in merged)]
    if bridge:
        keep += bridges(keep, bridge)
    return sorted(keep, key=lambda s: (LEVELS.index(s.level), s.start))


def bridges(ss: list[Span], days: int) -> list[Span]:
    """Lenient: where the same formation holds a level on both sides of a gap of at most `days`, carry it across, as
    assumed. Not across attachments (an attachments table lists them interval by interval: a gap is a detachment),
    and not where a different formation holds the level on either side."""
    out = []
    for lv in {s.level for s in ss}:
        row = sorted((s for s in ss if s.level == lv), key=lambda s: s.start)
        for a in row:
            if a.relation == "attached_to":
                continue
            nxt = [b for b in row if b.start > a.end]
            if not nxt:
                continue
            b = min(nxt, key=lambda b: b.start)
            gap = (b.start - a.end).days - 1
            if b.parent != a.parent or KIND[b.relation] != KIND[a.relation] or not 0 < gap <= days:
                continue
            if any(o.start <= a.end + (b.start - a.end) / 2 <= o.end for o in row if o not in (a, b)):
                continue                                  # something else holds the level in the gap
            out.append(Span(a.child, a.parent, a.parent_name, a.relation,
                            date.fromordinal(a.end.toordinal() + 1), date.fromordinal(b.start.toordinal() - 1),
                            False, False, "assumed", "", lv, a.own_start))
    return out


@cache
def _patch_png(file: str) -> bytes | None:
    """The patch as a PNG with any white ground round it made clear (some renderings sit on a white square)."""
    f = paths.cache() / "insignia" / "commons" / file
    if not f.exists():
        return None
    from PIL import Image, ImageDraw
    im = Image.open(f).convert("RGBA")
    for xy in ((0, 0), (im.width - 1, 0), (0, im.height - 1), (im.width - 1, im.height - 1)):
        px = im.getpixel(xy)
        if isinstance(px, tuple) and px[3] > 0 and min(px[:3]) > 235:
            ImageDraw.floodfill(im, xy, (255, 255, 255, 0), thresh=40)
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def _patch(unit: str, x: float, y: float, h: float) -> str:
    """The formation's patch as an image (h points tall), or nothing."""
    ins = insignia().get(unit)
    png = _patch_png(ins["file"]) if ins else None
    if not ins or not png:
        return ""
    w = h * float(ins.get("aspect", 0.8))
    return (f'<image x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" preserveAspectRatio="xMidYMid meet" '
            f'href="data:image/png;base64,{base64.b64encode(png).decode()}"/>')


ECHELON = {"company": "i", "battalion": "ii", "regiment": "iii", "group": "iii", "brigade": "x", "combat command": "x",
           "division": "xx", "corps": "xxx", "army": "xxxx"}


def fm(unit: str, name: str, lv: str) -> dict:
    """The unit's FM 21-30 symbol (symbols.symbol), read from its name as the record prints it: the arm from its
    words, the echelon from its level, a company's or battery's letter, the number."""
    n = f" {name} "
    arm = ("antiaircraft" if re.search(r"AAA|A\.?A\.?\)|\(AA\)|Antiaircraft|C\.A\.", n) else
           "artillery" if re.search(r"Field Artillery|\bFA\b", n) else
           "medical" if re.search(r"Med", n) else
           "armored" if re.search(r"Armd|Armored|Tank", n) else
           "infantry" if re.search(r"\bInf|Infantry", n) else "")
    num = re.search(r"(\d+)(?:st|nd|rd|th|d)\b", n)
    letter = re.match(r"\s*(?:Company|Co\.?|Battery|Btry)\s+([A-Z]|Hq|HQ)\b", name)
    return {"arm": arm, "echelon": ECHELON.get(lv, ""), "label": num[1] if num else "",
            "letter": letter[1] if letter else "", "mobility": "sp" if "(SP)" in name else ""}


def _mark(unit: str, name: str, lv: str, cx: float, cy: float, h: float, colour: str | None = None,
          max_w: float | None = None, bare: bool = False) -> str:
    """The patch, centred on (cx, cy), h tall (and no wider than max_w), or the FM symbol where the unit wore none
    of its own; `bare` leaves the symbol's number and letter to the name beside it."""
    ins = insignia().get(unit)
    if ins:
        asp = float(ins.get("aspect", 0.8))
        if max_w and h * asp > max_w:
            h = max_w / asp
        p = _patch(unit, cx - h * asp / 2, cy - h / 2, h)
        if p:
            return p
    from . import symbols
    sym = fm(unit, name, lv)
    if not sym["arm"]:                       # no arm read (a headquarters, a naval command): the name alone
        return ""
    if bare:
        sym = {**sym, "label": "", "letter": ""}
    k = (max_w or h * 1.3) / 13 * (0.8 if bare else 0.55)
    return symbols.symbol(cx, cy + 2 * k, sym, scale=k, colour=colour)


def patches_used(units) -> list[dict]:
    """The patches a figure drew, with their source, licence and what is checked of their period: for its notes."""
    return [{"unit": u, **{k: insignia()[u].get(k, "") for k in ("name", "source", "licence", "credit", "period")}}
            for u in dict.fromkeys(units) if u in insignia()]


def _text(x, y, s, size=7.0, fill=INK, anchor="start", weight="normal", family=DISPLAY, italic=False):
    st = ' font-style="italic"' if italic else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{family}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}" font-weight="{weight}"{st}>{escape(s)}</text>')


def _defs() -> str:
    return ('<defs><pattern id="attached" width="4" height="4" patternUnits="userSpaceOnUse" '
            'patternTransform="rotate(45)"><rect width="4" height="4" fill="#f3efe4"/>'
            '<line x1="0" y1="0" x2="0" y2="4" stroke="#b9ad92" stroke-width="1.4"/></pattern>'
            '<linearGradient id="fadeL" x1="0" x2="1"><stop offset="0" stop-color="#ffffff" stop-opacity="1"/>'
            '<stop offset="1" stop-color="#ffffff" stop-opacity="0"/></linearGradient>'
            '<linearGradient id="fadeR" x1="0" x2="1"><stop offset="0" stop-color="#ffffff" stop-opacity="0"/>'
            '<stop offset="1" stop-color="#ffffff" stop-opacity="1"/></linearGradient></defs>')


def timeline(base: str, start: str, end: str, width_in: float = 9.6, title: str = "",
             marks: list[dict] | None = None, bridge: int = 45) -> tuple[str, dict]:
    """The chain over [start, end] as SVG, and its notes (each bar's citation). `marks`: vertical lines for dated
    events ({"date", "words"}), e.g. a station or an engagement."""
    d0, d1 = date.fromisoformat(start), date.fromisoformat(end)
    ss = spans(base, d0, d1, bridge)
    W = width_in * 72
    left, right = 92.0, 8.0
    span_days = (d1 - d0).days or 1

    def X(d: date) -> float:
        return left + (d - d0).days / span_days * (W - left - right)
    # rows: the levels present, top to bottom; within each, lanes for overlapping links
    levels = sorted({s.level for s in ss}, key=LEVELS.index)
    # assigned links (part of, under command) in the upper lanes, attachments below them; a further lane only where
    # two links of one kind overlap
    lanes: dict[str, list[list[Span]]] = {lv: [] for lv in levels}
    for lv in levels:
        for k in ("assigned", "attached"):
            mine: list[list[Span]] = []
            for s in sorted((s for s in ss if s.level == lv and KIND[s.relation] == k), key=lambda s: s.start):
                for lane in mine:
                    if all(s.start >= o.end or s.end <= o.start for o in lane):
                        lane.append(s)
                        break
                else:
                    mine.append([s])
            lanes[lv] += mine
    bar_h, gap, top = 24.0, 7.0, 34.0 if title else 22.0
    body = [_defs()]
    if title:
        body.append(_text(0, 12, title.upper(), 8, INK, weight="bold"))
    y = top
    row_y = {}
    for lv in levels:
        row_y[lv] = y
        n = len(lanes[lv])
        h = n * bar_h + (n - 1) * 3
        body.append(f'<rect x="0" y="{y - 3:.1f}" width="{W:.1f}" height="{h + 6:.1f}" fill="#f6f5ef"/>')
        body.append(_text(4, y + h / 2 + 2.5, WORDS[lv], 7, MUTED, weight="bold"))
        for k, lane in enumerate(lanes[lv]):
            by = y + k * (bar_h + 3)
            taken: list[tuple[float, float]] = []          # x ranges a name beside a bar has used in this lane
            for s in lane:
                x0, x1 = X(s.start), X(s.end) + (W - left - right) / span_days
                fill = "url(#attached)" if s.relation == "attached_to" else ("#ffffff" if s.relation == "part_of"
                                                                              else "#e9e5d9")
                dash = ' stroke-dasharray="2.5 1.8"' if s.basis != "reported" else ""
                if s.basis == "assumed":                      # carried across a gap: paler, so it reads as ours
                    fill = "#f3f1ea" if s.relation != "attached_to" else "url(#attached)"
                body.append(f'<rect x="{x0:.1f}" y="{by:.1f}" width="{max(x1 - x0, 1):.1f}" height="{bar_h:.1f}" '
                            f'rx="2" fill="{fill}" stroke="{INK}" stroke-width="0.6"{dash}/>')
                if s.open_start:
                    body.append(f'<rect x="{x0:.1f}" y="{by:.1f}" width="{min(14, x1 - x0):.1f}" height="{bar_h:.1f}" '
                                f'fill="url(#fadeL)"/>')
                if s.open_end:
                    body.append(f'<rect x="{max(x0, x1 - 14):.1f}" y="{by:.1f}" width="{min(14, x1 - x0):.1f}" '
                                f'height="{bar_h:.1f}" fill="url(#fadeR)"/>')
                if s.basis == "assumed":                      # a bridge: the formation is named on either side
                    continue
                # the patch, then the name as printed, as far as the bar allows
                px = x0 + 3
                p = _patch(s.parent, px, by + 2, bar_h - 4)
                tx = x0 + 4
                if p and x1 - x0 > bar_h * 0.9:
                    body.append(p)
                    tx = px + (bar_h - 4) * float(insignia()[s.parent].get("aspect", 0.8)) + 3
                elif not p and x1 - x0 > 60:            # no patch of its own: its FM 21-30 symbol, if it has one
                    m = _mark(s.parent, s.parent_name, s.level, x0 + 13, by + bar_h / 2, 15, max_w=18, bare=True)
                    if m:
                        body.append(m)
                        tx = x0 + 30
                room = x1 - tx - 3
                shown = next((n for n in short(s.parent_name, s.level) if len(n) * 6.6 * 0.42 <= room), "")
                if shown:
                    w_txt = len(shown) * 6.6 * 0.42
                    if s.relation == "attached_to":            # a paper ground under the name on the hatching
                        body.append(f'<rect x="{tx - 1.5:.1f}" y="{by + bar_h / 2 - 5.5:.1f}" width="{w_txt + 3:.1f}" '
                                    f'height="9" rx="1" fill="{PAPER}" fill-opacity="0.92"/>')
                    body.append(_text(tx, by + bar_h / 2 + 2.4, shown, 6.6, INK, weight="bold"))
                else:                                          # too narrow: the name beside it, where the lane is free
                    bx, beside = x1 + 3, ""
                    for _ in range(4):                         # past any name already set beside a bar
                        stop = [X(o.start) for o in lane if o is not s and X(o.start) >= bx] + \
                               [a for a, b in taken if a >= bx]
                        free = (min(stop) if stop else W - right) - bx - 4
                        beside = next((n for n in short(s.parent_name, s.level) if len(n) * 6.2 * 0.42 <= free), "")
                        hit = [b for a, b in taken if a < bx + len(beside) * 2.6 and b > bx]
                        if not hit:
                            break
                        bx, beside = max(hit), ""
                    if beside:
                        body.append(_text(bx, by + bar_h / 2 + 2.3, beside, 6.2, MUTED, weight="bold"))
                        taken.append((bx, bx + len(beside) * 6.2 * 0.42 + 4))
        y += h + gap + 6
    # the time axis: months, and the year where it turns
    axis = y
    body.append(f'<line x1="{left:.1f}" y1="{axis:.1f}" x2="{W - right:.1f}" y2="{axis:.1f}" stroke="{INK}" '
                f'stroke-width="0.6"/>')
    m = date(d0.year, d0.month, 1)
    months = ["Jan", "Feb", "Mar", "Apr", "May", "June", "July", "Aug", "Sept", "Oct", "Nov", "Dec"]
    step = max(1, math.ceil(((d1.year - d0.year) * 12 + d1.month - d0.month + 1) / 14))
    k = 0
    while m <= d1:
        if m >= d0 and k % step == 0:
            x = X(m)
            body.append(f'<line x1="{x:.1f}" y1="{top - 4:.1f}" x2="{x:.1f}" y2="{axis + 3:.1f}" stroke="{RULE}" '
                        f'stroke-width="0.4"/>')
            body.append(_text(x + 2, axis + 10, months[m.month - 1] + (f" {m.year}" if m.month == 1 or k == 0 else ""),
                              6.4, MUTED))
        k += 1
        m = date(m.year + (m.month == 12), m.month % 12 + 1, 1)
    for mk in marks or []:
        md = date.fromisoformat(mk["date"])
        if d0 <= md <= d1:
            x = X(md)
            body.append(f'<line x1="{x:.1f}" y1="{top - 8:.1f}" x2="{x:.1f}" y2="{axis:.1f}" stroke="#a3241b" '
                        f'stroke-width="0.9"/>')
            body.append(_text(x, top - 10, mk["words"], 6.4, "#a3241b", anchor="middle", weight="bold"))
    # the key
    ky = axis + 22
    key = [("#e9e5d9", "", "assigned, or under command"), ("url(#attached)", "", "attached"),
           ("#ffffff", "", "part of"), ("#f3f1ea", "2.5 1.8", "inferred, or carried across a gap (assumed)"),
           ("#e9e5d9", "fade", "an end the record leaves open")]
    kx = left
    for fill, dash, words in key:
        dash_attr = f' stroke-dasharray="{dash}"' if dash and dash != "fade" else ""
        body.append(f'<rect x="{kx:.1f}" y="{ky - 6:.1f}" width="18" height="8" rx="1.5" fill="{fill}" stroke="{INK}" '
                    f'stroke-width="0.5"{dash_attr}/>')
        if dash == "fade":
            body.append(f'<rect x="{kx + 9:.1f}" y="{ky - 6:.1f}" width="9" height="8" fill="url(#fadeR)"/>')
        body.append(_text(kx + 22, ky + 0.5, words, 6.2, INK))
        kx += 30 + len(words) * 6.2 * 0.47
    H = ky + 8
    notes = {"base": base, "window": [start, end],
             "links": [{"unit": s.child, "relation": RELATION[s.relation], "parent": s.parent_name,
                        "from": s.start.isoformat(), "to": s.end.isoformat(), "basis": s.basis, "page": s.page}
                       for s in ss],
             "patches": patches_used(s.parent for s in ss)}
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.1f}pt" height="{H:.1f}pt" viewBox="0 0 {W:.1f} '
           f'{H:.1f}">{"".join(body)}</svg>')
    return halo.split(svg), notes


def ladder(base: str, on: str, width_in: float = 3.0) -> tuple[str, dict]:
    """The chain on one day, top to bottom: each step its patch, its name as printed, the link and its date."""
    d = date.fromisoformat(on)
    ss = [s for s in spans(base, date(1939, 9, 1), date(1946, 12, 31)) if s.start <= d <= s.end]
    steps = sorted(ss, key=lambda s: (LEVELS.index(s.level), s.relation != "under_command"))
    W = width_in * 72
    row = 44.0
    body = [_defs()]
    y = 6.0
    base_name = _names().get(base, base)
    for s in steps:
        body.append(_mark(s.parent, s.parent_name, s.level, 19, y + 17, 34, max_w=34, bare=True))
        tx = 44
        body.append(_text(tx, y + 11, s.parent_name, 8, INK, weight="bold"))
        if s.own_start is None:
            since = "undated (the formation's own composition)"
        else:
            since = ("by" if s.open_start else "since") + f" {s.start.day} {s.start:%b %Y}"
        body.append(_text(tx, y + 21, f"{WORDS[s.level]} · {RELATION[s.relation]} · {since}", 6.4, MUTED))
        body.append(_text(tx, y + 30, s.page, 5.8, MUTED, family=SERIF, italic=True))
        y += row
    body.append(f'<line x1="2" y1="{y - 4:.1f}" x2="{W - 2:.1f}" y2="{y - 4:.1f}" stroke="{RULE}" stroke-width="0.6"/>')
    body.append(_mark(base, base_name, level(base, base_name), 19, y + 15, 30, colour="#a3241b", max_w=34, bare=True))
    body.append(_text(44, y + 12, base_name, 8.4, "#a3241b", weight="bold"))
    body.append(_text(44, y + 22, f"its chain on {d.day} {d:%B %Y}", 6.4, MUTED))
    H = y + 34
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.1f}pt" height="{H:.1f}pt" viewBox="0 0 {W:.1f} '
           f'{H:.1f}">{"".join(body)}</svg>')
    return halo.split(svg), {"on": on, "steps": [s.parent_name for s in steps],
                             "patches": patches_used(s.parent for s in steps)}


def strip(base: str, on: str, width_in: float = 6.0) -> tuple[str, dict]:
    """The chain on one day as a row of patches, army group first, for a chapter's opening: each its patch (or its
    FM 21-30 symbol where it wore none of its own), its name and its level, and the unit itself at the end in red."""
    d = date.fromisoformat(on)
    ss = [s for s in spans(base, date(1939, 9, 1), date(1946, 12, 31)) if s.start <= d <= s.end]
    seen, steps = set(), []
    for st in sorted(ss, key=lambda s: (LEVELS.index(s.level), s.relation != "under_command")):
        if st.level not in seen:                     # one formation a level: the assigned one first
            seen.add(st.level)
            steps.append(st)
    W = width_in * 72
    n = len(steps) + 1
    cell = W / max(n, 6)
    x_left = (W - cell * n) / 2
    ph = min(46.0, cell * 0.62)
    body = []
    base_name = re.sub(r"\s*\(.*\)$", "", _names().get(base, base))
    items = [(st.parent, st.parent_name, st.level, st.relation) for st in steps]
    items.append((base, base_name, level(base, base_name), "self"))
    for i, (unit, name, lv, rel) in enumerate(items):
        cx = x_left + i * cell + cell / 2
        red = "#a3241b" if rel == "self" else None
        body.append(_mark(unit, name, lv, cx, 2 + ph / 2, ph, colour=red, max_w=cell * 0.8))
        shown = next((x for x in short(name, lv) if len(x) * 7 * 0.45 <= cell - 8), short(name, lv)[-1])
        body.append(_text(cx, ph + 14, shown, 7, red or INK, anchor="middle", weight="bold"))
        sub = f"{d.day} {d:%B %Y}" if rel == "self" else WORDS[lv] + (" · attached" if rel == "attached_to" else "")
        body.append(_text(cx, ph + 23, sub, 5.8, MUTED, anchor="middle"))
        if i:
            x = cx - cell / 2
            body.append(f'<path d="M{x - 2:.1f},{ph / 2 - 1:.1f} l3,3 l-3,3" fill="none" stroke="{MUTED}" '
                        f'stroke-width="0.7"/>')
    H = ph + 28
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.1f}pt" height="{H:.1f}pt" viewBox="0 0 {W:.1f} '
           f'{H:.1f}">{"".join(body)}</svg>')
    return halo.split(svg), {"on": on, "steps": [s.parent_name for s in steps],
                             "patches": patches_used(s.parent for s in steps)}
