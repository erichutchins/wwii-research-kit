"""Soft-proofing: how the book's colours, and its pages, will look printed on a press described by an ICC profile.

Each colour goes from sRGB into the printer's colour space and back (relative colorimetric, with black point
compensation, as a press proof does), and the shift is measured as CIEDE2000 colour difference against the screen
colour. The signal colours that must stay apart (the hit red and the three boats) are measured pair by pair after
proofing, since a press can pull two colours together that differ well on screen.

  palette(profile)               -> rows for each named colour: the screen hex, the proofed hex, the shift (ΔE00)
  pairs(profile)                 -> the signal pairs' differences on screen and in print
  page(png, profile, out)        -> a page proof rendered as it would print

A rough guide to ΔE00: under 2 hard to see, 2-5 visible side by side, over 10 a different colour.
"""
import math
from pathlib import Path

from PIL import Image, ImageCms

# the palette by name (core.typ's tokens and the figures' colours), with what to watch for in print
PALETTE = {
    "ink": "#000000", "muted": "#5d675b", "rule": "#c4cbbf", "paper": "#fbfaf6",
    "hit": "#c8323c", "accent": "#a3241b",
    "boat 1": "#2a6fc9", "boat 2": "#008f78", "boat 3": "#6a3a9e",
    "other-ink": "#4d5963", "other": "#e4e7e9", "intel": "#8a6d1f",
    "land": "#d4dbcc", "sea": "#f3f5f1", "coast": "#93aab3", "board": "#6f8a78",
    "card": "#eadcb4",
}
# pairs that must stay distinguishable in print: the hit red against every boat, and the boats against each other
SIGNALS = ("hit", "boat 1", "boat 2", "boat 3")


def _hex(rgb) -> str:
    r, g, b = rgb
    return f"#{r:02x}{g:02x}{b:02x}"


def _rgb(hexs: str) -> tuple[int, int, int]:
    h = hexs.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def lab(hexs: str) -> tuple[float, float, float]:
    """CIE L*a*b* (D65) of an sRGB colour."""
    def lin(c):
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(c) for c in _rgb(hexs))
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883

    def f(t):
        return t ** (1 / 3) if t > 216 / 24389 else (24389 / 27 * t + 16) / 116
    fx, fy, fz = f(x), f(y), f(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def de2000(l1, l2) -> float:
    """CIEDE2000 colour difference between two L*a*b* colours (Sharma, Wu and Dalal, 2005)."""
    L1, a1, b1 = l1
    L2, a2, b2 = l2
    C1, C2 = math.hypot(a1, b1), math.hypot(a2, b2)
    Cm = (C1 + C2) / 2
    G = 0.5 * (1 - math.sqrt(Cm ** 7 / (Cm ** 7 + 25 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1p = math.degrees(math.atan2(b1, a1p)) % 360
    h2p = math.degrees(math.atan2(b2, a2p)) % 360
    dLp, dCp = L2 - L1, C2p - C1p
    dhp = 0.0 if C1p * C2p == 0 else (h2p - h1p if abs(h2p - h1p) <= 180 else
                                       h2p - h1p - 360 if h2p > h1p else h2p - h1p + 360)
    dHp = 2 * math.sqrt(C1p * C2p) * math.sin(math.radians(dhp / 2))
    Lm, Cmp = (L1 + L2) / 2, (C1p + C2p) / 2
    if C1p * C2p == 0:
        hm = h1p + h2p
    elif abs(h1p - h2p) <= 180:
        hm = (h1p + h2p) / 2
    else:
        hm = (h1p + h2p + 360) / 2 if h1p + h2p < 360 else (h1p + h2p - 360) / 2
    T = (1 - 0.17 * math.cos(math.radians(hm - 30)) + 0.24 * math.cos(math.radians(2 * hm))
         + 0.32 * math.cos(math.radians(3 * hm + 6)) - 0.20 * math.cos(math.radians(4 * hm - 63)))
    dth = 30 * math.exp(-(((hm - 275) / 25) ** 2))
    Rc = 2 * math.sqrt(Cmp ** 7 / (Cmp ** 7 + 25 ** 7))
    Sl = 1 + 0.015 * (Lm - 50) ** 2 / math.sqrt(20 + (Lm - 50) ** 2)
    Sc, Sh = 1 + 0.045 * Cmp, 1 + 0.015 * Cmp * T
    Rt = -math.sin(math.radians(2 * dth)) * Rc
    return math.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2 + Rt * (dCp / Sc) * (dHp / Sh))


def _transform(profile: Path | str):
    srgb = ImageCms.createProfile("sRGB")
    press = ImageCms.getOpenProfile(str(profile))
    flags = ImageCms.Flags.SOFTPROOFING | ImageCms.Flags.BLACKPOINTCOMPENSATION
    return ImageCms.buildProofTransform(srgb, srgb, press, "RGB", "RGB",
                                        renderingIntent=ImageCms.Intent.RELATIVE_COLORIMETRIC,
                                        proofRenderingIntent=ImageCms.Intent.RELATIVE_COLORIMETRIC, flags=flags)


def proofed(hexs: list[str], profile: Path | str) -> list[str]:
    """Each sRGB colour as it would print, back in sRGB for the screen."""
    im = Image.new("RGB", (len(hexs), 1))
    im.putdata([_rgb(h) for h in hexs])
    out = ImageCms.applyTransform(im, _transform(profile))
    return [_hex(out.getpixel((i, 0))) for i in range(len(hexs))]


def palette(profile: Path | str, colours: dict[str, str] = PALETTE) -> list[dict]:
    names = list(colours)
    printed = proofed([colours[n] for n in names], profile)
    return [{"name": n, "screen": colours[n], "print": p, "shift": de2000(lab(colours[n]), lab(p)),
             "lightness": (lab(colours[n])[0], lab(p)[0])} for n, p in zip(names, printed)]


def pairs(profile: Path | str, colours: dict[str, str] = PALETTE, names=SIGNALS) -> list[dict]:
    printed = dict(zip(names, proofed([colours[n] for n in names], profile)))
    out = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            out.append({"pair": (a, b), "screen": de2000(lab(colours[a]), lab(colours[b])),
                        "print": de2000(lab(printed[a]), lab(printed[b]))})
    return out


def page(png: Path | str, profile: Path | str, out: Path | str) -> Path:
    im = Image.open(png).convert("RGB")
    ImageCms.applyTransform(im, _transform(profile)).save(out)
    return Path(out)


def report(profile: Path | str, pages: list[Path] = ()) -> str:
    lines = [f"Soft proof against {Path(profile).name} (relative colorimetric, black point compensation)", "",
             f"{'colour':10} {'screen':8} {'print':8} {'shift ΔE00':>10}  L* screen > print"]
    for r in palette(profile):
        flag = "  visible" if r["shift"] >= 5 else ""
        lines.append(f"{r['name']:10} {r['screen']} {r['print']} {r['shift']:10.1f}  "
                     f"{r['lightness'][0]:5.1f} > {r['lightness'][1]:5.1f}{flag}")
    lines += ["", "Signals that must stay apart (ΔE00 between them; under 15 is worth a look in print):"]
    for p in pairs(profile):
        flag = "  CLOSE" if p["print"] < 15 else ""
        lines.append(f"  {p['pair'][0]:7} / {p['pair'][1]:7}  screen {p['screen']:5.1f}  print {p['print']:5.1f}{flag}")
    for png in pages:
        out = Path(png).with_name(Path(png).stem + "-softproof.png")
        page(png, profile, out)
        lines.append(f"page proof: {out}")
    return "\n".join(lines)
