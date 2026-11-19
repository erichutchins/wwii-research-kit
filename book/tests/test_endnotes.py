"""The notes at the end (`on-grid.with(notes: "end")`, here through `--input notes=end`): the running-text example's
text runs across the whole live area in two columns, no note stands in an outer column, the calls stay in the text,
and every note is set once, in order, under "Notes" before the sources; a figure that reaches into the note column
the grid's way is set at the full measure. Compiled with nothing prepared, as test_examples does."""
import json
import re
import shutil
from pathlib import Path

import pytest
import typst
from wwiibook import paths
from wwiibook.preflight import check

BOOK = Path(__file__).resolve().parents[1] / "examples" / "running-text" / "book.typ"
TRIM_W, BLEED, INSIDE, OUTSIDE = 612.0, 9.0, 54.0, 36.0

# the sections' helper for a figure run on into the note column: moved out by it on a verso, widened by it
REACH = """
#let outer(body) = context {
  let shift = if recto-at(here().page()) { 0pt } else { -122pt }
  align(left, move(dx: shift, box(width: 100% + 122pt, body)))
}
#pagebreak()
#across(at: top, outer(rect(width: 100%, height: 30pt, fill: rgb("#2a6fc9"))))
#lorem(40)
#pagebreak()
#across(at: top, outer(rect(width: 100%, height: 30pt, fill: rgb("#2a6fc9"))))
#lorem(40)
"""


def _compile(tmp: Path, mode: str, extra: str = "") -> tuple[Path, list]:
    copy = tmp / f"running-text-{mode}"
    shutil.copytree(BOOK.parent, copy, ignore=shutil.ignore_patterns("build", "proof", "*.pdf"))
    (copy / "build").mkdir(exist_ok=True)
    (copy / "build" / "assets.json").write_text("{}")
    if extra:
        src = (copy / "book.typ").read_text()
        i = src.index("#section-sources(")
        (copy / "book.typ").write_text(src[:i] + extra + "\n" + src[i:])
    kw = dict(root=str(copy), package_path=str(paths.TYPST), font_paths=[str(paths.FONTS)], sys_inputs={"notes": mode})
    typst.compile(str(copy / "book.typ"), output=str(copy / "book.pdf"), **kw)
    out = typst.query(str(copy / "book.typ"), "<wwii-note>", field="value", **kw)
    return copy / "book.pdf", json.loads(out) if isinstance(out, (str, bytes)) else list(out)


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    return _compile(tmp_path_factory.mktemp("end"), "end", REACH)


def _numbers(page):
    """Note numbers as the side notes and end notes set them: digits in the display face at the notes' size."""
    return [(sp["bbox"][0], sp["bbox"][1], sp["text"].strip())
            for b in page.get_text("dict")["blocks"] for ln in b.get("lines", []) for sp in ln["spans"]
            if re.fullmatch(r"\d+", sp["text"].strip()) and "IBMPlex" in sp["font"]
            and abs(sp["size"] - 7.2) < 0.3 and 60 < sp["bbox"][1] < 760]


def test_every_note_is_set_once_in_order_under_notes_before_the_sources(built):
    import pymupdf
    pdf, notes = built
    doc = pymupdf.open(str(pdf))
    text = "\n".join(p.get_text() for p in doc)
    assert "NOTES" in text and text.index("NOTES") < text.rindex("Sources")
    start = next(i for i, p in enumerate(doc) if "NOTES" in p.get_text())
    listed = [int(n[2]) for p in doc[start:] for n in sorted(_numbers(p), key=lambda n: (n[0] > 300, n[1]))]
    assert listed == [n["n"] for n in notes] == list(range(1, len(notes) + 1))
    assert not [n for p in doc[:start] for n in _numbers(p)], "a note set beside the text"


def test_the_text_runs_across_the_whole_live_area(built):
    import pymupdf
    pdf, _ = built
    full = []
    for i, page in enumerate(pymupdf.open(str(pdf)), start=1):
        trim_left = 0.0 if i % 2 == 1 else BLEED
        inside, outside = (INSIDE, OUTSIDE) if i % 2 == 1 else (OUTSIDE, INSIDE)
        body = [w for w in page.get_text("words") if 80 < w[1] < 740 and len(w[4]) > 3]
        if not body:
            continue
        assert min(w[0] for w in body) - trim_left >= inside - 2.5, f"page {i}: text inside the margin"
        assert max(w[2] for w in body) - trim_left <= TRIM_W - outside + 2.5, f"page {i}: text past the margin"   # punctuation hangs a little
        right = [w for w in body if w[0] - trim_left > TRIM_W / 2 + 40]     # the second column, where it has text
        # (a page of running text: a table or the ragged notes may stop short of it)
        if right and max(w[2] for w in right) - trim_left > TRIM_W - outside - 4:
            full.append(i)
    assert {i % 2 for i in full} == {0, 1}, "the second column runs to the outer margin on a recto and a verso"


def test_a_figure_that_reached_into_the_note_column_spans_the_full_measure(built):
    import pymupdf
    pdf, _ = built
    spans = []
    for i, page in enumerate(pymupdf.open(str(pdf)), start=1):
        trim_left = 0.0 if i % 2 == 1 else BLEED
        for d in page.get_drawings():
            if d.get("fill") and abs(d["rect"].height - 30) < 0.5 and abs(d["fill"][0] - 0x2a / 255) < 0.02:
                spans.append((i % 2 == 1, round(d["rect"].x0 - trim_left), round(d["rect"].x1 - trim_left)))
    assert {s[0] for s in spans} == {True, False}, "one on a recto and one on a verso"
    for recto, x0, x1 in spans:
        assert (x0, x1) == ((INSIDE, TRIM_W - OUTSIDE) if recto else (OUTSIDE, TRIM_W - INSIDE))


def test_the_side_notes_are_the_default_and_unchanged(tmp_path):
    import pymupdf
    pdf, _ = _compile(tmp_path, "side")
    text = "\n".join(p.get_text() for p in pymupdf.open(str(pdf)))
    assert "NOTES" not in text


def test_every_page_is_the_magazine_page(built):
    pdf, _ = built
    rep = check(pdf, "blurb-magazine")
    assert not [p for p in rep.problems if "pt, not" in p or "not embedded" in p]
