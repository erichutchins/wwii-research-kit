"""A scan made ready for a page: turned, cropped, greyscale. Pillow only, so it runs anywhere (no macOS sips)."""
from pathlib import Path

from PIL import Image

PRINT_DPI = 300


def facsimile(src: Path, dest: Path, crop: list[float] | None = None, rotate: int = 0) -> tuple[int, int]:
    """Turn the scan by `rotate` degrees counter-clockwise (a sideways panel: 90 or -90), then crop to the fractions
    (x, y, width, height) of the turned page, and save it greyscale. Returns the result's size in pixels."""
    with Image.open(src) as im:
        im.load()
        out = im.convert("L")
    if rotate:
        out = out.rotate(rotate, expand=True)
    if crop:
        x, y, w, h = crop
        W, H = out.size
        out = out.crop((round(x * W), round(y * H), round((x + w) * W), round((y + h) * H)))
    dest.parent.mkdir(parents=True, exist_ok=True)
    out.save(dest)
    return out.size


def natural_width_in(px: int, dpi: int = PRINT_DPI) -> float:
    """The widest the image can print, in inches, at `dpi`."""
    return px / dpi
