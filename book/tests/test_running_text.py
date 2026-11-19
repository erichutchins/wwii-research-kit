"""The running-text example on the magazine grid: its notes number in order from 1, each in the outer column of its
own page (right on a recto, left on a verso), the text frame alternates with them, every archive citation resolves to
a link at its page, and every page is Blurb's size. Compiled with nothing prepared, as test_examples does."""
import json
import re
import shutil
from pathlib import Path

import pytest
import typst
from wwiibook import paths
from wwiibook.preflight import check

BOOK = Path(__file__).resolve().parents[1] / "examples" / "running-text" / "book.typ"
TRIM_W, BLEED = 612.0, 9.0


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    copy = tmp_path_factory.mktemp("rt") / "running-text"
    shutil.copytree(BOOK.parent, copy, ignore=shutil.ignore_patterns("build", "proof", "*.pdf"))
    (copy / "build").mkdir(exist_ok=True)
    (copy / "build" / "assets.json").write_text("{}")
    kw = dict(root=str(copy), package_path=str(paths.TYPST), font_paths=[str(paths.FONTS)])
    typst.compile(str(copy / "book.typ"), output=str(copy / "book.pdf"), **kw)
    out = typst.query(str(copy / "book.typ"), "<wwii-note>", field="value", **kw)
    notes = json.loads(out) if isinstance(out, (str, bytes)) else list(out)
    return copy / "book.pdf", notes


def test_the_notes_number_in_order_from_one(built):
    _, notes = built
    assert len(notes) >= 20
    assert [n["n"] for n in notes] == list(range(1, len(notes) + 1))   # one chapter: no reset, no gap, no repeat


def test_every_note_cites_a_source(built):
    _, notes = built
    assert all(n["cite"] for n in notes)


def test_the_notes_and_the_text_alternate_sides(built):
    import pymupdf
    pdf, _ = built
    doc = pymupdf.open(str(pdf))
    assert len(doc) >= 4
    for i, page in enumerate(doc, start=1):
        recto = i % 2 == 1
        trim_left = 0.0 if recto else BLEED
        words = page.get_text("words")
        # the note numbers: words of digits at the note column's left edge (36 pt in from the outer trim, then 110 pt)
        outer, inner = TRIM_W - 36 - 110, 36.0
        here, there = (outer, inner) if recto else (inner, outer)
        # (a note's number is set in the display face at the notes' size: a figure in the text, a table or a list
        # of sources is not one)
        numbers = [(sp["bbox"][0], sp["bbox"][1], 0, 0, sp["text"].strip())
                   for b in page.get_text("dict")["blocks"] for ln in b.get("lines", []) for sp in ln["spans"]
                   if re.fullmatch(r"\d+", sp["text"].strip()) and "IBMPlex" in sp["font"]
                   and abs(sp["size"] - 7.2) < 0.3 and 60 < sp["bbox"][1] < 760]
        assert any(abs(w[0] - trim_left - here) < 1.5 for w in numbers), f"page {i}: no notes in the outer column"
        assert not any(abs(w[0] - trim_left - there) < 1.5 for w in numbers), f"page {i}: a note on the inside"
        # the text frame: the leftmost body word sits at the inside margin on a recto and after the notes on a verso
        body = [w[0] - trim_left for w in words if 80 < w[1] < 740 and len(w[4]) > 3 and not re.fullmatch(r"\d+", w[4])]
        left = min(x for x in body if x > (40 if recto else 36 + 110 + 6))
        assert abs(left - (54 if recto else 36 + 110 + 12)) < 3, f"page {i}: text frame starts at {left:.1f}"
        # the folio, outside
        folio = [w for w in words if w[4] == str(i) and w[1] > 750]
        assert folio and ((folio[0][0] - trim_left > TRIM_W / 2) == recto)


def test_every_archive_citation_links_to_its_page(built):
    import pymupdf
    pdf, notes = built
    links = {lk.get("uri", "") for page in pymupdf.open(str(pdf)) for lk in page.get_links()}
    for n in notes:
        m = re.fullmatch(r"rg(\d+)-(\d+)/p(\d+)", n["cite"])
        if m:
            assert f"https://catalog.archives.gov/id/{m[2]}?objectPage={int(m[3])}" in links


def test_every_page_is_the_magazine_page(built):
    pdf, _ = built
    rep = check(pdf, "blurb-magazine")
    assert not [p for p in rep.problems if "pt, not" in p or "not embedded" in p]
