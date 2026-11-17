"""A QR code as SVG, square modules, high error correction (so a silhouette can later sit in its centre)."""
from pathlib import Path

import segno


def svg(url: str, dest: Path, dark: str = "#1c221d") -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    segno.make(url, error="h").save(str(dest), kind="svg", dark=dark, light=None, border=0, scale=10, xmldecl=False,
                                     svgns=True, nl=False)
    return dest
