"""Solid colours in place of transparency, before Typst sees a figure.

A press that takes PDF/X-3 (PDF 1.3) has no live transparency: a fill at 40 per cent, a translucent arrow or a PNG's
alpha channel would be flattened by the printer's software, which rasterises what it touches, lettering included. The
figures here are drawn for white paper, so each translucent colour is replaced by the solid colour it looks like there:
the colour mixed with the ground at its opacity (`mix`). `svg` does that to a whole drawing, through its groups'
opacity and inherited paint, and flattens any embedded PNG onto the ground; `png` flattens an image file. Where a
preparer knows its colour lies on something other than the ground (a hole's lip on the card's backing, the relief on
the land tint), it mixes onto that itself and draws solid.

What cannot be made solid this way is left as it was, so preflight still finds it: a gradient that fades from one
opacity to another, a translucent paint server (`url(#...)`), an image linked rather than embedded.
"""
import base64
import io
import re
import xml.etree.ElementTree as ET
from pathlib import Path

GROUND = "#ffffff"   # the paper the book prints on: white stock (the `paper` token is a figure's tint on it)
SVG_NS, XLINK_NS = "http://www.w3.org/2000/svg", "http://www.w3.org/1999/xlink"
ET.register_namespace("", SVG_NS)
ET.register_namespace("xlink", XLINK_NS)

NAMED = {"black": (0, 0, 0), "white": (255, 255, 255), "red": (255, 0, 0), "gray": (128, 128, 128),
         "grey": (128, 128, 128)}
PAINTED = {"path", "rect", "circle", "ellipse", "line", "polyline", "polygon", "text", "tspan", "textPath", "use"}
CONTAINERS = {"g", "a", "switch", "svg", "symbol", "marker", "pattern", "defs"}
SKIP = {"clipPath", "mask", "metadata", "title", "desc", "style", "script"}   # their paint is never seen


def rgb(c: str) -> tuple[int, int, int] | None:
    """A colour as an (r, g, b) triple, or None for anything not a plain colour (none, url(...), currentColor)."""
    c = c.strip().lower()
    if c in NAMED:
        return NAMED[c]
    if m := re.fullmatch(r"#([0-9a-f]{3})", c):
        return tuple(int(ch * 2, 16) for ch in m.group(1))  # type: ignore[return-value]
    if m := re.fullmatch(r"#([0-9a-f]{6})", c):
        h = m.group(1)
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    if m := re.fullmatch(r"rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", c):
        return int(m.group(1)), int(m.group(2)), int(m.group(3))
    return None


def mix(colour: str, alpha: float, ground: str = GROUND) -> str:
    """The solid colour `colour` at `alpha` looks like over `ground`: how a PDF composites one over the other."""
    c, g = rgb(colour), rgb(ground)
    if c is None or g is None:
        raise ValueError(f"not a plain colour: {colour!r} over {ground!r}")
    a = min(max(alpha, 0.0), 1.0)
    return "#" + "".join(f"{round(ci * a + gi * (1 - a)):02x}" for ci, gi in zip(c, g))


def _num(v: str | None, default: float = 1.0) -> float:
    if v is None:
        return default
    v = v.strip()
    try:
        return float(v[:-1]) / 100 if v.endswith("%") else float(v)
    except ValueError:
        return default


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _props(el: ET.Element) -> dict[str, str]:
    """An element's presentation attributes, with its style="..." properties over them (style wins, as in CSS)."""
    p = {k: v for k, v in el.attrib.items() if not k.startswith("{")}
    for part in (el.get("style") or "").split(";"):
        if ":" in part:
            k, v = part.split(":", 1)
            p[k.strip()] = v.strip()
    return p


def _set(el: ET.Element, key: str, value: str | None) -> None:
    """Set (or, with None, remove) a property, in the attribute and out of the style."""
    style = el.get("style")
    if style:
        kept = [s for s in style.split(";") if s.strip() and s.split(":", 1)[0].strip() != key]
        if kept:
            el.set("style", ";".join(kept))
        else:
            del el.attrib["style"]
    if value is None:
        el.attrib.pop(key, None)
    else:
        el.set(key, value)


def _flat_png(data: bytes, alpha: float, ground: str) -> bytes | None:
    """A PNG composited onto the ground at `alpha`, opaque; None when it is opaque already and alpha is 1."""
    from PIL import Image
    with Image.open(io.BytesIO(data)) as im:
        im.load()
        has_alpha = im.mode in ("RGBA", "LA", "PA") or (im.mode == "P" and "transparency" in im.info)
        if not has_alpha and alpha >= 1:
            return None
        grey = im.mode in ("L", "LA", "1", "I", "I;16")
        src = im.convert("RGBA")
    if alpha < 1:
        src.putalpha(src.getchannel("A").point(lambda v: round(v * alpha)))
    g = rgb(ground) or (255, 255, 255)
    out = Image.new("RGBA", src.size, (*g, 255))
    out.alpha_composite(src)
    out = out.convert("L" if grey and len(set(g)) == 1 else "RGB")
    buf = io.BytesIO()
    out.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def png(path: Path | str, ground: str = GROUND) -> bool:
    """Flatten an image file's alpha onto the ground, in place. True if it changed."""
    path = Path(path)
    if path.suffix.lower() != ".png":
        return False
    flat = _flat_png(path.read_bytes(), 1.0, ground)
    if flat is None:
        return False
    path.write_bytes(flat)
    return True


def _walk(el: ET.Element, inh: dict, ground: str) -> None:
    tag = _local(el.tag)
    if tag in SKIP:
        return
    p = _props(el)
    fill = p.get("fill", inh["fill"])
    stroke = p.get("stroke", inh["stroke"])
    fo = _num(p["fill-opacity"]) if "fill-opacity" in p else inh["fo"]
    so = _num(p["stroke-opacity"]) if "stroke-opacity" in p else inh["so"]
    group = inh["group"] * _num(p.get("opacity"))
    if "opacity" in p:
        _set(el, "opacity", None)

    if tag == "stop":
        pass                                      # gradients: `_stops`, a gradient at a time
    elif tag == "image":
        href_key = f"{{{XLINK_NS}}}href" if f"{{{XLINK_NS}}}href" in el.attrib else "href"
        href = el.get(href_key) or ""
        if href.startswith("data:image/png;base64,"):
            flat = _flat_png(base64.b64decode(href.split(",", 1)[1]), group, ground)
            if flat is not None:
                el.set(href_key, "data:image/png;base64," + base64.b64encode(flat).decode())
        elif group < 1:
            el.set("opacity", f"{group:g}")       # linked, not embedded: left for preflight to find
    elif tag in CONTAINERS:
        for key in ("fill-opacity", "stroke-opacity"):
            if key in p:
                _set(el, key, None)               # each shape inside takes its own solid colour
    elif tag in PAINTED:
        for key, paint, own in (("fill", fill, fo), ("stroke", stroke, so)):
            a = own * group
            if a >= 1:
                if f"{key}-opacity" in p:
                    _set(el, f"{key}-opacity", None)
                continue
            if rgb(paint) is not None:
                _set(el, key, mix(paint, a, ground))
                _set(el, f"{key}-opacity", None)
            elif paint.strip().lower() != "none":
                _set(el, f"{key}-opacity", f"{a:g}")   # a gradient or currentColor: left as it was
    # children inherit the paint as specified and the opacity so far, and each works out its own solid colour
    sub = {"fill": fill, "stroke": stroke, "fo": fo, "so": so, "group": group}
    for child in el:
        _walk(child, sub, ground)


def _stops(root: ET.Element, ground: str) -> None:
    """A gradient whose stops share one opacity is made solid; one that fades between opacities is left."""
    for grad in root.iter():
        if _local(grad.tag) not in ("linearGradient", "radialGradient"):
            continue
        stops = [s for s in grad if _local(s.tag) == "stop"]
        alphas = {_num(_props(s).get("stop-opacity")) for s in stops}
        if len(alphas) != 1 or alphas == {1.0}:
            continue
        a = alphas.pop()
        for s in stops:
            c = _props(s).get("stop-color", "black")
            if rgb(c) is not None:
                _set(s, "stop-color", mix(c, a, ground))
                _set(s, "stop-opacity", None)


def svg(text: str, ground: str = GROUND) -> str:
    """The drawing with every translucent colour made solid over the ground."""
    if not re.search(r"opacity|data:image/png", text):
        return text
    root = ET.fromstring(text)
    _stops(root, ground)
    _walk(root, {"fill": "black", "stroke": "none", "fo": 1.0, "so": 1.0, "group": 1.0}, ground)
    return ET.tostring(root, encoding="unicode")


def asset(path: Path | str, ground: str = GROUND) -> bool:
    """Make a prepared asset solid in place (an SVG or a PNG). True if it changed."""
    path = Path(path)
    if path.suffix.lower() == ".svg":
        old = path.read_text()
        new = svg(old, ground)
        if new != old:
            path.write_text(new)
            return True
        return False
    return png(path, ground)


def remaining(text: str) -> int:
    """How many translucent marks a drawing still has (what `svg` could not make solid)."""
    n = 0
    for m in re.finditer(r'(?:fill-opacity|stroke-opacity|stop-opacity|opacity)\s*[=:]\s*"?([0-9.]+%?)', text):
        if _num(m.group(1)) < 1:
            n += 1
    return n
