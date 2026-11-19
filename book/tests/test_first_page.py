"""A part set to start on a volume's later page (`sys.inputs` first-page, as a volume of separately built sections
uses): its folios continue from that page, and a part that starts on a verso mirrors its grid, so the notes stay in
the outer column and the trim against the binding for the side each page ends up on."""
import shutil
from pathlib import Path

import pikepdf
import pymupdf
import pytest
import typst
from wwiibook import paths, press

BOOK = Path(__file__).resolve().parents[1] / "examples" / "running-text" / "book.typ"
TRIM_W, BLEED = 612.0, 9.0


def _compile(tmp: Path, first: int) -> Path:
    copy = tmp / f"rt-{first}"
    shutil.copytree(BOOK.parent, copy, ignore=shutil.ignore_patterns("build", "proof", "*.pdf"))
    (copy / "build").mkdir(exist_ok=True)
    (copy / "build" / "assets.json").write_text("{}")
    out = copy / "book.pdf"
    typst.compile(str(copy / "book.typ"), output=str(out), root=str(copy), package_path=str(paths.TYPST),
                  font_paths=[str(paths.FONTS)], sys_inputs={"first-page": str(first)})
    press.finish(out, first)
    return out


@pytest.fixture(scope="module")
def parts(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("first-page")
    return {n: _compile(tmp, n) for n in (1, 2, 17)}


def _folio(page) -> str:
    """The folio: the last line of digits at the foot of the page."""
    words = [w for w in page.get_text("words") if w[1] > 750 and w[4].isdigit()]
    return words[-1][4] if words else ""


@pytest.mark.parametrize("first", [1, 2, 17])
def test_the_folios_continue_from_the_first_page(parts, first):
    doc = pymupdf.open(str(parts[first]))
    folios = [_folio(p) for p in doc]
    numbered = [(i, f) for i, f in enumerate(folios) if f]
    assert numbered, "no folios"
    assert all(int(f) == first + i for i, f in numbered)


@pytest.mark.parametrize("first", [1, 2])
def test_the_folio_and_the_text_sit_outside_for_the_final_side(parts, first):
    doc = pymupdf.open(str(parts[first]))
    for i, page in enumerate(doc):
        recto = (first + i) % 2 == 1
        foot = [w for w in page.get_text("words") if w[1] > 750 and w[4].isdigit()]
        if foot:   # the folio is at the outer edge: the right of a recto, the left of a verso
            assert (foot[-1][0] > TRIM_W / 2) == recto, f"page {first + i}: folio on the wrong side"
        body = [w for w in page.get_text("words") if 100 < w[1] < 700]
        if body:   # the text frame is at the binding: the left of a recto's sheet, the right of a verso's
            mid = sum(w[0] for w in body) / len(body)
            sheet_mid = (TRIM_W + BLEED) / 2
            assert (mid < sheet_mid + 60) if recto else (mid > sheet_mid - 60), f"page {first + i}: frame not mirrored"


def test_the_trim_box_follows_the_final_side(parts):
    with pikepdf.open(parts[2]) as pdf:
        first = [float(v) for v in pdf.pages[0].TrimBox]
        second = [float(v) for v in pdf.pages[1].TrimBox]
    assert first[0] == BLEED      # page 2, a verso: the bleed on the left
    assert second[0] == 0.0       # page 3, a recto: the trim from the binding on the left
