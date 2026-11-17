"""White halos behind map lettering, drawn so no halo covers a letter.

A label is written with a stroke painted under its fill (`paint-order="stroke"`). Renderers differ on whether that
order holds for the whole line or glyph by glyph: Typst's paints each glyph's stroke and then its fill before the
next glyph, so a letter's halo covers the right edge of the letter before it. `split` rewrites every such label as two:
the halo alone (the stroke, and a fill of the stroke's colour), then the lettering alone on top.
"""
import re

TEXT = re.compile(r"<text(\s[^>]*)>(.*?)</text>", re.S)
ATTR = re.compile(r'([\w:-]+)="([^"]*)"')
STROKE = {"stroke", "stroke-width", "stroke-opacity", "stroke-linejoin", "stroke-linecap", "paint-order"}


def _tag(attrs: list[tuple[str, str]]) -> str:
    return "<text " + " ".join(f'{k}="{v}"' for k, v in attrs) + ">"


def _one(m: re.Match) -> str:
    attrs = ATTR.findall(m.group(1))
    d = dict(attrs)
    if d.get("paint-order") != "stroke" or not d.get("stroke"):
        return m.group(0)
    body = m.group(2)
    halo = [(k, v) for k, v in attrs if k not in ("fill", "fill-opacity", "paint-order")]
    halo.append(("fill", d["stroke"]))
    if "stroke-opacity" in d:
        halo.append(("fill-opacity", d["stroke-opacity"]))
    halo.append(("aria-hidden", "true"))
    text = [(k, v) for k, v in attrs if k not in STROKE]
    return _tag(halo) + body + "</text>" + _tag(text) + body + "</text>"


def split(svg: str) -> str:
    return TEXT.sub(_one, svg)
