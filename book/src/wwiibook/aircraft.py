"""An aircraft card: a representative photograph of the type, its silhouettes, and what the Allies' recognition
manuals told gunners and pilots about it at the time (records/air/aircraft.yml), each figure as printed and cited.

The photograph is from book/aircraft/photos.yml: a public-domain or freely licensed print of the type, captioned
for what it shows (the type, not the aircraft in our story unless the caption says so). A photograph with a face is
used only once it is approved; until then the card says so in its place. The silhouettes are the kit's
(records/silhouettes/silhouettes.yml, traced from the same manuals).
"""
import base64
import io
from functools import cache
from html import escape

import yaml

from . import halo, paths

INK, MUTED, RULE, PAPER = "#000000", "#586257", "#c4cbbf", "#fbfaf6"
DISPLAY = "IBM Plex Sans, IBM Plex Sans Condensed, Arial Narrow, sans-serif"
SERIF = "Libertinus Serif, Georgia, serif"
PHOTOS = paths.PACKAGE.parents[1] / "aircraft" / "photos.yml"


@cache
def _data() -> dict:
    return yaml.safe_load((paths.records() / "air" / "aircraft.yml").read_text())


@cache
def _silhouettes() -> dict:
    return yaml.safe_load((paths.records() / "silhouettes" / "silhouettes.yml").read_text())["aircraft"]


@cache
def _photos() -> dict:
    return yaml.safe_load(PHOTOS.read_text()) if PHOTOS.exists() else {}


def _t(x, y, s, size=7.0, fill=INK, anchor="start", weight="normal", family=DISPLAY, italic=False):
    it = ' font-style="italic"' if italic else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{family}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}" font-weight="{weight}"{it}>{escape(s)}</text>')


def _wrap(s: str, chars: int) -> list[str]:
    out, line = [], ""
    for w in s.split():
        if len(line) + len(w) + 1 > chars:
            out.append(line)
            line = w
        else:
            line = (line + " " + w).strip()
    return out + ([line] if line else [])


def _shape(view: dict, x: float, y: float, w: float, level6: str | None = None) -> str:
    """A view of the type at width w: its level-6 drawing where the records hold one (records/silhouettes/level6/
    <kind>-<view>.svg, drawn in the same frame as the solid outline), its body in ink and its panel lines and glass
    knocked out in the paper colour, as the strip size wants; else the solid outline."""
    k = w / float(view["w"])
    g = f'transform="translate({x:.1f},{y:.1f}) scale({k:.4f})"'
    f = paths.records() / "silhouettes" / "level6" / f"{level6}.svg" if level6 else None
    if f is not None and f.exists():
        s = f.read_text()
        inner = s[s.index("</desc>") + 7: s.rindex("</svg>")] if "</desc>" in s else s[s.index(">") + 1: s.rindex("</svg>")]
        inner = inner.replace('fill="#1b1b1b"', f'fill="{INK}"').replace('stroke="#1b1b1b"', f'stroke="{INK}"')
        inner = inner.replace('fill="#9a9a9a"', f'fill="{PAPER}"').replace('fill="#ffffff"', f'fill="{PAPER}"')
        return f"<g {g}>{inner}</g>"
    return f'<path {g} d="{view["d"]}" fill="{INK}" fill-rule="evenodd"/>'



def _photo(p: dict, w: float) -> tuple[str, float]:
    f = paths.cache() / "air-photos" / p["file"]
    if not f.exists():
        return "", 0.0
    from PIL import Image
    im = Image.open(f).convert("L")
    h = w * im.height / im.width
    im.thumbnail((int(w * 300 / 72), int(h * 300 / 72)))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=86, optimize=True)
    return (f'<image width="{w:.1f}" height="{h:.1f}" preserveAspectRatio="none" '
            f'href="data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}"/>'), h


def card(kind: str, width_in: float = 4.4, photo: int = 0, faces_ok: bool = False) -> tuple[str, dict]:
    """The card for an aircraft type (its key in records/air/aircraft.yml), `photo` the index of its photograph in
    book/aircraft/photos.yml. A photograph with a face is drawn only if approved there (or `faces_ok`)."""
    d, sil = _data()[kind], _silhouettes().get(kind, {})
    W = width_in * 72
    body, y = [], 0.0
    photos = _photos().get(kind, [])
    p = photos[photo] if photo < len(photos) else None
    shown = None
    if p and (p.get("approved") or faces_ok or p.get("faces") is False):
        img, h = _photo(p, W)
        if img:
            body.append(img)
            y = h + 3
            shown = p
            for ln in _wrap(p["caption"] + " " + p["credit"] + ".", int(W / (5.6 * 0.47))):
                y += 7.2
                body.append(_t(0, y, ln, 5.6, MUTED, family=SERIF, italic=True))
            y += 6
    if p and not shown:
        why = ("not yet downloaded" if not (paths.cache() / "air-photos" / p["file"]).exists() else
               "awaiting approval: a face is visible" if p.get("faces") is True else
               "awaiting a look: people may be visible")
        body.append(f'<rect width="{W:.1f}" height="40" fill="{PAPER}" stroke="{RULE}" stroke-width="0.6"/>')
        body.append(_t(W / 2, 18, f"Photograph chosen, {why}", 6.6, MUTED, anchor="middle"))
        body.append(_t(W / 2, 28, p["commons"], 5.6, MUTED, anchor="middle", italic=True))
        y = 48
    # the name, and what the manual called it
    y += 11
    body.append(_t(0, y, d["name"].upper(), 10, INK, weight="bold"))
    y += 9
    body.append(_t(0, y, d["as_printed"], 6.2, MUTED))
    # silhouettes: plan and profile at one scale (the plan as wide as a third of the card)
    y += 6
    sw = W * 0.32
    if sil.get("plan"):
        body.append(_shape(sil["plan"], 0, y, sw, f"{kind}-plan"))
    if sil.get("profile"):
        pw = sw * float(sil.get("length", 1)) / float(sil.get("span", 1)) if sil.get("span") else sw
        body.append(_shape(sil["profile"], sw + 10, y + 4, min(pw, W * 0.28), f"{kind}-profile"))
    sh = sw * float(sil["plan"]["h"]) / float(sil["plan"]["w"]) if sil.get("plan") else 0
    # the figures, as printed, in a box beside the silhouettes: the top speed large
    fx = W * 0.66
    box_y = y - 2
    fy = box_y + 13
    figs = []
    speeds = d.get("max_speed", [])
    if speeds:
        figs.append(_t(fx + 7, fy, "TOP SPEED", 5.6, MUTED, weight="bold"))
        top = speeds[0].split(" at ")
        figs.append(_t(fx + 7, fy + 13, top[0].replace(" (turbo-jet units)", ""), 12, INK, weight="bold"))
        rest = "; ".join(([("at " + top[1])] if len(top) > 1 else []) + speeds[1:])
        if "(turbo-jet units)" in speeds[0]:
            rest = "turbo-jet units" + ("; " + rest if rest else "")
        line = 0
        for k, ln in enumerate(_wrap(rest, int((W - fx - 12) / (5.8 * 0.45)))):
            figs.append(_t(fx + 7, fy + 21 + 7 * k, ln, 5.8, INK))
            line = k + 1
        fy += 21 + 7 * line + 6
    for label, val in (("Span", d.get("span")), ("Length", d.get("length")),
                       ("Ceiling", "; ".join(d.get("ceiling", []))), ("Armament", d.get("armament")),
                       ("Role", d.get("role"))):
        if not val:
            continue
        figs.append(_t(fx + 7, fy, label.upper(), 5.6, MUTED, weight="bold"))
        last = 0
        for k, ln in enumerate(_wrap(val, int((W - fx - 12) / (6.2 * 0.45)))):
            figs.append(_t(fx + 7, fy + 8 * (k + 1), ln, 6.2, INK))
            last = k
        fy += 8 * (last + 1) + 8
    body.append(f'<rect x="{fx:.1f}" y="{box_y:.1f}" width="{W - fx:.1f}" height="{fy - box_y:.1f}" rx="2" '
                f'fill="#f1efe6" stroke="{RULE}" stroke-width="0.6"/>')
    body += figs
    y = max(y + sh + 8, fy)
    # the manual's own words, and where they are
    for ln in _wrap(d["words"].strip(), int(W / (6.6 * 0.47))):
        y += 8.4
        body.append(_t(0, y, ln, 6.6, INK, family=SERIF, italic=True))
    y += 10
    body.append(_t(0, y, f"{d['source']} ({d['ref']})", 5.6, MUTED))
    body.append(f'<line x1="0" y1="{y + 5:.1f}" x2="{W:.1f}" y2="{y + 5:.1f}" stroke="{RULE}" stroke-width="0.6"/>')
    H = y + 8
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.1f}pt" height="{H:.1f}pt" viewBox="0 0 {W:.1f} '
           f'{H:.1f}">{"".join(body)}</svg>')
    notes = {"kind": kind, "ref": d["ref"], "photo": shown and {k: shown[k] for k in ("commons", "credit", "licence")}}
    return halo.split(svg), notes

