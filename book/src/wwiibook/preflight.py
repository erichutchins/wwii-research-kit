"""Preflight a book's PDF against its printer's specifications before it is uploaded: every page at the preset's size
(trim plus bleed), the page count even and within the printer's range, every font embedded, and every image at
300 ppi or more at the size it is placed. The presets mirror core.typ's."""
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Spec:
    page: tuple[float, float]      # points, trim plus bleed
    pages: tuple[int, int]         # the page counts the printer takes
    even: bool


PRESETS = {
    # Blurb's PDF-to-Book specifications for the Premium Magazine, read 17 Nov 2026
    "blurb-magazine": Spec(page=(621.0, 810.0), pages=(24, 240), even=True),
    "draft": Spec(page=(504.0, 720.0), pages=(1, 10_000), even=False),
}


@dataclass
class Report:
    pdf: Path
    pages: int = 0
    problems: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems


def check(pdf: Path | str, preset: str = "blurb-magazine", min_ppi: float = 300) -> Report:
    import pymupdf  # the package's dev dependency (uv sync --extra dev, or uv run --with pymupdf)
    spec = PRESETS[preset]
    rep = Report(Path(pdf))
    doc = pymupdf.open(str(pdf))
    rep.pages = len(doc)
    lo, hi = spec.pages
    if not lo <= rep.pages <= hi:
        rep.problems.append(f"{rep.pages} pages: the printer takes {lo} to {hi}")
    if spec.even and rep.pages % 2:
        rep.problems.append(f"{rep.pages} pages: the count must be even")
    w, h = spec.page
    fonts: dict[str, bool] = {}
    for i in range(1, rep.pages + 1):
        page = doc[i - 1]
        r = page.rect
        if abs(r.width - w) > 0.5 or abs(r.height - h) > 0.5:
            rep.problems.append(f"page {i}: {r.width:.1f} x {r.height:.1f} pt, not {w:g} x {h:g}")
        for f in page.get_fonts(full=True):
            name, ext = f[3], f[1]
            fonts[name] = fonts.get(name, False) or bool(ext and ext != "n/a")
        for info in page.get_image_info():
            bw, bh = info["bbox"][2] - info["bbox"][0], info["bbox"][3] - info["bbox"][1]
            if bw <= 1 or bh <= 1:
                continue
            ppi = min(info["width"] / (bw / 72), info["height"] / (bh / 72))
            if ppi < min_ppi:
                rep.warnings.append(f"page {i}: an image at {ppi:.0f} ppi ({info['width']} px across {bw / 72:.2f} in)")
    for name, embedded in sorted(fonts.items()):
        if not embedded:
            rep.problems.append(f"font not embedded: {name}")
    return rep
