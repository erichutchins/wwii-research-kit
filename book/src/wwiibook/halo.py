"""White halos behind map lettering, drawn so no halo covers a letter.

A label is written with a stroke painted under its fill (`paint-order="stroke"`). Renderers differ on whether that
order holds for the whole line or glyph by glyph: Typst's paints each glyph's stroke and then its fill before the
next glyph, so a letter's halo covers the right edge of the letter before it; and a label's halo, drawn after its
neighbour, covers the neighbour's lettering where the two come close.

`layer` rewrites a drawing so that every haloed label is two texts: the halo alone (the stroke, and a fill of the
stroke's colour) and the lettering alone. The labels that share a parent element are moved to the place of the last
of them: first all their halos, in one group (`<g class="halo">`), then all their lettering, in the order drawn. So
no halo covers any label's letters, and every halo still covers whatever the drawing put down before the labels
(the lines and bands a label is written across). The rewrite is idempotent, and it also gathers halos split one by
one before (an `aria-hidden` halo text and the lettering after it), so a figure prepared by an older engine comes
out the same. `solid.svg` runs it, so every figure the build prepares, and every section figure
made solid for print, is layered; `split` is the old name.
"""
import re

TOKEN = re.compile(r"<!--.*?-->|<!\[CDATA\[.*?\]\]>|<\?.*?\?>|<![^>]*>"
                   r"|<(/?)([A-Za-z][\w:.-]*)((?:[^>\"']|\"[^\"]*\"|'[^']*')*?)(/?)>", re.S)
ATTR = re.compile(r"""([\w:.-]+)\s*=\s*(?:"([^"]*)"|'([^']*)')""")
STROKE = {"stroke", "stroke-width", "stroke-opacity", "stroke-linejoin", "stroke-linecap", "stroke-miterlimit",
          "paint-order"}
GROUP = '<g class="halo" aria-hidden="true">'


def _attrs(s: str) -> list[tuple[str, str]]:
    return [(k, a if a or not b else b) for k, a, b in ATTR.findall(s)]


def _tag(attrs: list[tuple[str, str]]) -> str:
    return "<text " + " ".join(f'{k}="{v}"' for k, v in attrs) + ">"


def _halo(attrs: list[tuple[str, str]]) -> str | None:
    """What a text start tag is: 'label' (a fill with a halo under it), 'halo' (a halo split out before), or None."""
    d = dict(attrs)
    if not d.get("stroke") or d["stroke"] == "none":
        return None
    if d.get("paint-order", "").split()[:1] == ["stroke"]:
        return "label"
    if d.get("aria-hidden") == "true" and d.get("fill") == d["stroke"]:
        return "halo"
    return None


def _split(attrs: list[tuple[str, str]], body: str) -> tuple[str, str]:
    """A haloed label as (its halo, its lettering)."""
    d = dict(attrs)
    halo = [(k, v) for k, v in attrs if k not in ("fill", "fill-opacity", "paint-order", "aria-hidden")]
    halo.append(("fill", d["stroke"]))
    if "stroke-opacity" in d:
        halo.append(("fill-opacity", d["stroke-opacity"]))
    halo.append(("aria-hidden", "true"))
    text = [(k, v) for k, v in attrs if k not in STROKE]
    return _tag(halo) + body + "</text>", _tag(text) + body + "</text>"


class _Frame:
    def __init__(self, name: str, start: str):
        self.name, self.start = name, start
        self.out: list[str] = []
        self.halos: list[str] = []
        self.fills: list[str] = []
        self.at: int | None = None          # where in `out` the labels go: the place of the last haloed label

    def add(self, halo: str, fill: str) -> None:
        self.at = len(self.out)
        self.out.append("")
        self.halos.append(halo)
        self.fills.append(fill)

    def body(self) -> str:
        if self.at is not None:
            inside = self.start.startswith('<g class="halo"')          # already the halos' group: no group in a group
            group = "".join(self.halos) if inside else GROUP + "".join(self.halos) + "</g>"
            self.out[self.at] = group + "".join(self.fills)
        return "".join(self.out)


def layer(svg: str) -> str:
    """The drawing with every halo under every label's lettering (see the module's note)."""
    if "<text" not in svg:
        return svg
    stack = [_Frame("", "")]
    pos = 0
    while (m := TOKEN.search(svg, pos)) is not None:
        stack[-1].out.append(svg[pos:m.start()])
        pos = m.end()
        close, name, rest, empty = m.group(1), m.group(2), m.group(3), m.group(4)
        if name is None or empty:                     # a comment, a declaration, an empty element
            stack[-1].out.append(m.group(0))
        elif close:
            if not any(f.name == name for f in stack[1:]):
                stack[-1].out.append(m.group(0))
                continue
            while True:
                f = stack.pop()
                stack[-1].out.append(f.start + f.body() + (f"</{name}>" if f.name == name else ""))
                if f.name == name:
                    break
        elif name == "text" and (kind := _halo(attrs := _attrs(rest))) and (end := svg.find("</text>", pos)) >= 0:
            inner = svg[pos:end]
            pos = end + len("</text>")
            if kind == "label":
                stack[-1].add(*_split(attrs, inner))
                continue
            # a halo split out before: its lettering is the plain text that follows it
            nxt = TOKEN.search(svg, pos)
            fill = ""
            if (nxt and not svg[pos:nxt.start()].strip() and nxt.group(2) == "text" and not nxt.group(1)
                    and _halo(_attrs(nxt.group(3))) is None and (fend := svg.find("</text>", nxt.end())) >= 0):
                fill = svg[nxt.start():fend + len("</text>")]
                pos = fend + len("</text>")
            stack[-1].add(m.group(0) + inner + "</text>", fill)
        else:
            stack.append(_Frame(name, m.group(0)))
    stack[-1].out.append(svg[pos:])
    while len(stack) > 1:                             # unclosed elements, written back as they were
        f = stack.pop()
        stack[-1].out.append(f.start + f.body())
    return stack[0].body()


split = layer
