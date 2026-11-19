"""Units as the situation maps drew them, simplified for print: the US Army's own symbols (FM 21-30, as the kit's
fronts read them, records/fronts/README.md), a box with the arm's mark inside and the echelon above it.

  infantry           the box crossed corner to corner
  armored            an oval inside the box
  armored-infantry   both: the cross and the oval
  airborne           the cross, and an arc at the foot of the box
  antiaircraft       a triangle in the box (FM 21-30, 1943, chart 13); self-propelled: the box drawn with a tail
  artillery          a dot in the box (artillery other than antiaircraft)
  medical            the box quartered by a cross
  elements           "(ELMS)" on the map: only parts of the division; drawn with a dashed box

Our side is drawn open (white, ink lines); the enemy's filled (grey, white lines). The number stands beside the box,
without the map's qualifiers, which the box's style and the key carry instead.
"""
import re
from html import escape

INK, ENEMY, PAPER, OWN = "#000000", "#4d5963", "#ffffff", "#a3241b"
DISPLAY = "IBM Plex Sans, IBM Plex Sans Condensed, Arial Narrow, sans-serif"

ARM_WORDS = {"infantry": "Infantry", "armored": "Armored", "armored-infantry": "Armored Infantry", "airborne": "Airborne"}
ARM_WORDS_DE = {"infantry": "Infantry", "armored": "Panzer", "armored-infantry": "Panzergrenadier", "airborne": "Parachute"}
SIDE_WORDS = {"us": "American", "uk": "British", "ca": "Canadian", "de": "German"}


def parse_label(label: str) -> tuple[str, bool, str]:
    """'91 (ELMS)' -> ('91', True, ''); '9(-)' -> ('9', False, '(-)'): the number, whether only elements, a qualifier."""
    elements = bool(re.search(r"\(?\s*ELMS?\s*\)?", label, re.I))
    rest = re.sub(r"\(?\s*ELMS?\s*\)?", "", label, flags=re.I).strip()
    m = re.match(r"^(.*?)\s*(\([+-]\))?$", rest)
    return (m.group(1).strip() if m else rest), elements, (m.group(2) or "") if m else ""


def _ordinal(n: str) -> str:
    m = re.match(r"^(\d+)(.*)$", n)
    if not m:
        return n
    k = int(m.group(1))
    suffix = "th" if 10 <= k % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(k % 10, "th")
    return f"{k}{suffix}{m.group(2)}"


def full_name(unit: dict) -> str:
    """Words for a box, from what the symbol shows: '2 SS' drawn armored on the German side -> '2nd SS Panzer Division'.
    Worked out from the symbol, so no more than the map says."""
    number, elements, _ = parse_label(unit.get("label") or "")
    arm, side, echelon = unit.get("arm") or "", unit.get("of") or "", unit.get("echelon") or ""
    words = ARM_WORDS_DE if side == "de" else ARM_WORDS
    kind = {"xx": "Division", "xxx": "Corps", "xxxx": "Army"}.get(echelon, "unit, echelon not marked")
    ss = " SS" if re.search(r"\bSS\b", number) else ""
    num = _ordinal(re.sub(r"\s*SS\b", "", number).strip())
    name = f"{num}{ss} {words.get(arm, '')} {kind}".replace("  ", " ")
    return ("elements of the " if elements else "") + name


def symbol(x: float, y: float, unit: dict, highlight: bool = False, scale: float = 1.0,
           colour: str | None = None) -> str:
    """The box at (x, y) with its mark, echelon, and number (a battery's letter, `letter`, on the left). `colour`
    draws one of our units in its own colour (an atlas's units' own records)."""
    number, elements, _ = parse_label(unit.get("label") or "")
    ours = unit.get("of") != "de"
    w, h = 13 * scale, 8.5 * scale
    x0, y0 = x - w / 2, y - h / 2
    fill, line = (PAPER, INK) if ours else (ENEMY, PAPER)
    stroke = OWN if highlight else (INK if ours else ENEMY)
    if colour:
        stroke = line = colour
    sw = 1.3 if highlight or colour else 0.7
    dash = ' stroke-dasharray="1.6 1.1"' if elements else ""
    opacity = ' fill-opacity="0.45"' if elements and not ours else ""   # a part of the division: the box half-filled
    out = []
    if unit.get("mobility") == "sp":   # self-propelled: the box with a tail (chart 26)
        out.append(f'<path d="M{x0 + w:.1f},{y0 + h * 0.15:.1f} L{x0 + w * 1.28:.1f},{y0 + h * 0.38:.1f} '
                   f'L{x0 + w * 1.28:.1f},{y0 + h * 0.62:.1f} L{x0 + w:.1f},{y0 + h * 0.85:.1f}" fill="{fill}" '
                   f'stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="round"/>')
    out.append(f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{fill}"{opacity} stroke="{stroke}" '
               f'stroke-width="{sw * 1.3 if elements else sw}"{dash}/>')
    arm = unit.get("arm") or ""
    if arm == "antiaircraft":
        out.append(f'<path d="M{x0:.1f},{y0 + h:.1f} L{x:.1f},{y0:.1f} L{x0 + w:.1f},{y0 + h:.1f} '
                   f'M{x0 + w * 0.25:.1f},{y0 + h * 0.5:.1f} L{x0 + w * 0.75:.1f},{y0 + h * 0.5:.1f}" fill="none" '
                   f'stroke="{line}" stroke-width="0.6" stroke-linejoin="round"/>')
    if arm == "artillery":
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{h * 0.16:.1f}" fill="{line}"/>')
    if arm == "medical":
        out.append(f'<path d="M{x:.1f},{y0:.1f} V{y0 + h:.1f} M{x0:.1f},{y:.1f} H{x0 + w:.1f}" stroke="{line}" '
                   f'stroke-width="0.6"/>')
    if arm in ("infantry", "armored-infantry", "airborne"):
        out.append(f'<path d="M{x0:.1f},{y0:.1f} L{x0 + w:.1f},{y0 + h:.1f} M{x0 + w:.1f},{y0:.1f} L{x0:.1f},{y0 + h:.1f}" '
                   f'stroke="{line}" stroke-width="0.6"/>')
    if arm in ("armored", "armored-infantry"):
        out.append(f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="{w * 0.33:.1f}" ry="{h * 0.27:.1f}" fill="none" '
                   f'stroke="{line}" stroke-width="0.7"/>')
    if arm == "airborne":
        out.append(f'<path d="M{x - w * 0.22:.1f},{y0 + h:.1f} Q{x:.1f},{y0 + h * 0.55:.1f} {x + w * 0.22:.1f},{y0 + h:.1f}" '
                   f'fill="none" stroke="{line}" stroke-width="0.7"/>')
    ech = {"i": "I", "ii": "II", "iii": "III", "x": "X", "xx": "XX", "xxx": "XXX",
           "xxxx": "XXXX"}.get(unit.get("echelon") or "", "")
    if ech:
        out.append(f'<text x="{x:.1f}" y="{y0 - 1.2:.1f}" font-family="{DISPLAY}" font-size="{4.2 * scale:.1f}" '
                   f'fill="{stroke}" text-anchor="middle" font-weight="bold">{ech}</text>')
    right = x0 + w * (1.28 if unit.get("mobility") == "sp" else 1) + 1.8
    text = colour or (OWN if highlight else INK)
    out.append(f'<text x="{right:.1f}" y="{y + 2.4 * scale:.1f}" font-family="{DISPLAY}" font-size="{6.8 * scale:.1f}" '
               f'fill="{text}" font-weight="bold" stroke="#ffffff" stroke-width="1.8" '
               f'stroke-linejoin="round" paint-order="stroke">{escape(number)}</text>')
    if unit.get("letter"):
        out.append(f'<text x="{x0 - 1.6:.1f}" y="{y + 2.4 * scale:.1f}" font-family="{DISPLAY}" '
                   f'font-size="{6.8 * scale:.1f}" fill="{text}" font-weight="bold" text-anchor="end" stroke="#ffffff" '
                   f'stroke-width="1.8" stroke-linejoin="round" paint-order="stroke">{escape(unit["letter"])}</text>')
    return "".join(out)


def legend(x: float, y: float, sides: set[str], arms: set[str], elements: bool, highlight: str | None,
           max_width: float = 400, highlight_arm: str = "infantry") -> tuple[str, float]:
    """The symbols on the map, explained, starting at (x, y) and wrapping onto a new row before `max_width`.
    Returns (svg, the height it takes)."""
    items: list[tuple[dict, str, bool]] = []
    for arm in ("infantry", "armored", "armored-infantry", "airborne"):
        if arm in arms:
            items.append(({"of": "us", "arm": arm, "echelon": "xx", "label": ""}, ARM_WORDS[arm].lower(), False))
    if "de" in sides:
        items.append(({"of": "de", "arm": "infantry", "echelon": "xx", "label": ""}, "German (filled)", False))
    if elements:
        items.append(({"of": "de", "arm": "", "echelon": "", "label": "ELMS"}, "elements of a division", False))
    if highlight:
        items.append(({"of": "us", "arm": highlight_arm, "echelon": "", "label": ""}, highlight, True))
    out = [f'<text x="{x:.1f}" y="{y + 3:.1f}" font-family="{DISPLAY}" font-size="6.2" fill="{INK}" '
           f'font-weight="bold" letter-spacing="0.5">DIVISIONS, XX:</text>']
    start, row_h = x + 54, 15.0
    cx, cy = start, y
    for unit, words, hl in items:
        w = 20 + len(words) * 3.0 + 10
        if cx + w > x + max_width and cx > start:
            cx, cy = start, cy + row_h
        out.append(symbol(cx + 6, cy, unit, highlight=hl))
        out.append(f'<text x="{cx + 15:.1f}" y="{cy + 2.3:.1f}" font-family="{DISPLAY}" font-size="6.2" '
                   f'fill="{OWN if hl else INK}">{escape(words)}</text>')
        cx += w
    return "".join(out), cy - y + row_h
