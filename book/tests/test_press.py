"""The print pass: solid colours in place of transparency, the page boxes, black ink, PDF/X-3."""
import pikepdf
import pytest
import typst
from wwiibook import preflight, press, solid

TRANSLUCENT = ('<svg xmlns="http://www.w3.org/2000/svg" width="100" height="60" viewBox="0 0 100 60">'
               '<rect width="100" height="60" fill="#ffffff"/>'
               '<g opacity="0.5"><rect x="5" y="5" width="40" height="20" fill="#2a6fc9"/></g>'
               '<circle cx="70" cy="30" r="20" fill="#c8323c" fill-opacity="0.4" stroke="#000" stroke-opacity="0.8"/>'
               '<text x="5" y="50" fill="#000000">ink</text></svg>')


def _book(tmp_path, svg: str):
    (tmp_path / "fig.svg").write_text(svg)
    (tmp_path / "book.typ").write_text(
        '#set page(width: 621pt, height: 810pt)\n#set text(fill: rgb("#000000"))\n'
        'One #image("fig.svg", width: 3in)\n#pagebreak()\nTwo #rect(fill: rgb("#c8323c").transparentize(50%))\n'
        '#pagebreak()\nThree\n')
    pdf = tmp_path / "book.pdf"
    typst.compile(str(tmp_path / "book.typ"), output=str(pdf), root=str(tmp_path), pdf_tags=False)
    return pdf


def test_mix_is_the_colour_on_white():
    assert solid.mix("#000000", 0.5) == "#808080"
    assert solid.mix("#2a6fc9", 1.0) == "#2a6fc9"
    assert solid.mix("#c8323c", 0.0) == "#ffffff"
    assert solid.mix("#c9b78c", 0.55, "#1d1a16") == "#7c7057"


def test_svg_made_solid():
    out = solid.svg(TRANSLUCENT)
    assert solid.remaining(out) == 0
    assert 'fill="#94b7e4"' in out            # the blue at half opacity, through its group
    assert 'fill="#e9adb1"' in out            # the red at 40 per cent
    assert solid.remaining(TRANSLUCENT) == 3


def test_boxes_and_transparency(tmp_path):
    pdf = _book(tmp_path, TRANSLUCENT)
    before = press.inspect(pdf)
    assert before.alpha_states >= 2 and before.trim
    pdf2 = _book(tmp_path, solid.svg(TRANSLUCENT))
    press.finish(pdf2)
    after = press.inspect(pdf2)
    assert after.alpha_states == 1            # the Typst rect, transparentized in the page itself, is still there
    with pikepdf.open(pdf2) as p:
        boxes = [([float(v) for v in pg.obj.TrimBox], [float(v) for v in pg.obj.BleedBox]) for pg in p.pages]
    assert boxes[0] == ([0, 9, 612, 801], [0, 0, 621, 810])      # a recto: the bleed on the right
    assert boxes[1] == ([9, 9, 621, 801], [0, 0, 621, 810])      # a verso: on the left
    assert boxes[2][0] == [0, 9, 612, 801]
    assert not after.trim


def test_black_reaches_the_pdf_as_black_ink(tmp_path):
    pdf = _book(tmp_path, solid.svg(TRANSLUCENT))
    assert press.inspect(pdf).colour["text rgb-black"] > 0
    assert press.finish(pdf) > 0
    c = press.inspect(pdf).colour
    assert not any(k.endswith("rgb-black") for k in c)
    assert c["text k-black"] > 0


def test_pdfx(tmp_path):
    try:
        press.find_profile()
    except FileNotFoundError:
        pytest.skip("no CMYK output profile on this machine")
    pdf = _book(tmp_path, solid.svg(TRANSLUCENT))
    with pytest.raises(ValueError, match="translucent"):
        press.pdfx(pdf, tmp_path / "x.pdf")                       # the Typst rect's alpha is refused
    (tmp_path / "book.typ").write_text('#set page(width: 621pt, height: 810pt)\nOne\n#pagebreak()\nTwo\n')
    typst.compile(str(tmp_path / "book.typ"), output=str(pdf), root=str(tmp_path), pdf_tags=False)
    press.pdfx(pdf, tmp_path / "x.pdf", title="Test")
    rep = preflight.check(tmp_path / "x.pdf")
    assert dict(rep.checks)["PDF/X-3:2002"].startswith("ok")
    assert all(found.startswith("ok") for _, found in rep.checks)
    assert (tmp_path / "x.pdf").read_bytes()[:8] == b"%PDF-1.3"
