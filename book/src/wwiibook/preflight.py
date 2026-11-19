"""Preflight a book's PDF against its printer's specifications before it is uploaded: every page at the preset's size
(trim plus bleed) with its TrimBox and BleedBox, the page count even and within the printer's range, every font
embedded, every image at 300 ppi or more at the size it is placed, no live transparency, text and rules in black ink
alone, no spot colours, and the PDF/X-3 markers and output intent the printer's preset asks for. The presets mirror
core.typ's."""
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Spec:
    page: tuple[float, float]      # points, trim plus bleed
    pages: tuple[int, int]         # the page counts the printer takes
    even: bool
    pdfx: str | None = None        # the PDF/X standard the printer's preset writes


PRESETS = {
    # Blurb's PDF-to-Book specifications for the Premium Magazine, read 17 Nov 2026
    "blurb-magazine": Spec(page=(621.0, 810.0), pages=(24, 240), even=True, pdfx="PDF/X-3:2002"),
    "draft": Spec(page=(504.0, 720.0), pages=(1, 10_000), even=False),
}


@dataclass
class Report:
    pdf: Path
    pages: int = 0
    problems: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checks: list[tuple[str, str]] = field(default_factory=list)   # (check, what was found), passed or not

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
    _press(rep, spec)
    return rep


def _press(rep: Report, spec: Spec) -> None:
    """The checks a press makes of the file itself: boxes, transparency, ink, spot colours, PDF/X."""
    from . import press
    r = press.inspect(rep.pdf)

    def report(name: str, found: str, problems: list[str]) -> None:
        more = " ..." if len(problems) > 3 else ""
        rep.checks.append((name, f"ok: {found}" if not problems else "problem: " + "; ".join(problems[:3]) + more))
        rep.problems.extend(problems)

    report("page boxes", "TrimBox inset 9 pt at the top, bottom and outside edge; BleedBox = MediaBox", r.trim)
    report("transparency", "none", [f"{n} {what}" for n, what in ((r.soft_masks, "images with soft masks"),
            (r.alpha_states, "translucent graphics states (CA or ca below 1)"), (r.blend_states, "blend modes"))
            if n])
    rich = {k: n for k, n in r.colour.items() if k.endswith(("rgb-black", "rich-black"))}
    text_k = sum(n for k, n in r.colour.items() if k.startswith("text ") and k.endswith(("k-black", "gray0")))
    report("black ink", f"{text_k} text runs in black ink alone (CMYK 0/0/0/100 or gray 0); no RGB or rich black",
           [f"{n} {k.replace('rgb-black', 'in RGB black').replace('rich-black', 'in rich black')}"
            for k, n in sorted(rich.items())])
    report("spot colours", "none", [f"{r.spot} Separation or DeviceN colour spaces"] if r.spot else [])
    if spec.pdfx:
        want = [("/GTS_PDFXVersion", spec.pdfx), ("/Trapped", "/False")]
        found = [f"{k[1:]} {r.pdfx.get(k, 'missing')}, not {v}" for k, v in want if r.pdfx.get(k) != v]
        if "intent" not in r.pdfx:
            found.append("no PDF/X output intent")
        else:
            if r.pdfx["intent"] != press.CONDITION or r.pdfx["registry"] != press.REGISTRY:
                found.append(f"output intent {r.pdfx['intent']!r} ({r.pdfx['registry']}), not {press.CONDITION!r} "
                             f"({press.REGISTRY})")
            if r.pdfx.get("profile") != "4 channels":
                found.append("the output intent carries no CMYK profile")
        if r.version > "1.3":
            found.append(f"PDF {r.version}, not 1.3")
        if r.groups:
            found.append(f"{r.groups} transparency groups")
        if not found and (r.links or r.outline):
            rep.warnings.append("links or an outline left in the file (the press ignores them)")
        if found and "/GTS_PDFXVersion" not in r.pdfx:
            found = [f"not {spec.pdfx}: run wwii-book press"]
        report(spec.pdfx, f"PDF {r.version}, output intent {r.pdfx.get('intent')} ({r.pdfx.get('registry')}), "
               "Trapped False", found)
