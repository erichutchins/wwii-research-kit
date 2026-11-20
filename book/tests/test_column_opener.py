"""A chapter opened in a column (`running-text(opener: "column")`): no new page, a smaller head set within one text
column (the eyebrow, the title, the standfirst), space above it, the text after it still on the baseline grid in both
columns, its notes begun again at 1, the page's running head kept, and the chapter named over its notes at the end."""
import json
import re

import pymupdf
import pytest
import typst
from wwiibook import paths

PAGE = r"""
#import "@local/wwii-book:0.1.0": *
#show: book.with(preset: "blurb-magazine")
#show: on-grid
#running-text(title: [The first chapter], eyebrow: [June 1944 · New York], standfirst: [A full opener.])[
#for i in range(24) [#lorem(60)#note[A note] ]
]
#running-text(title: [A chapter in a column], eyebrow: [July 1944 · Bermuda, Montauk], opener: "column",
  standfirst: [A short standfirst, set in the column.])[
#for i in range(3) [#lorem(50)#note[Another] ]
]
#running-text(title: [Third], eyebrow: [August 1944], opener: "column", recto: true)[
#for i in range(3) [#lorem(50) ]
]
"""
TOP = 9 + 54          # the live area's top, from the bleed box
BASELINE = 13.0


def _compile(tmp_path, notes="side"):
    src = tmp_path / "page.typ"
    src.write_text(PAGE)
    pdf = tmp_path / f"page-{notes}.pdf"
    kw = dict(root=str(tmp_path), package_path=str(paths.TYPST), font_paths=[str(paths.FONTS)],
              sys_inputs={"notes": notes})
    typst.compile(str(src), output=str(pdf), **kw)
    out = typst.query(str(src), "<wwii-note>", field="value", **kw)
    return pymupdf.open(str(pdf)), json.loads(out) if isinstance(out, (str, bytes)) else list(out)


def _spans(page):
    return [sp for b in page.get_text("dict")["blocks"] for ln in b.get("lines", []) for sp in ln["spans"]]


@pytest.fixture(scope="module")
def side(tmp_path_factory):
    return _compile(tmp_path_factory.mktemp("col"))


def _title_page(doc, words):
    hits = [(i, sp) for i, page in enumerate(doc) for sp in _spans(page) if sp["text"].startswith(words)]
    assert hits, f"{words!r} not set"
    return hits[0]


def test_a_column_chapter_opens_on_the_page_the_one_before_ends(side):
    doc, _ = side
    i, title = _title_page(doc, "A CHAPTER IN A")
    first_text = [sp for sp in _spans(doc[i]) if "Libertinus" in sp["font"] and abs(sp["size"] - 10) < 0.1
                  and sp["bbox"][3] < title["bbox"][1]]
    assert first_text, "the column chapter began a new page"
    j, _ = _title_page(doc, "THIRD")
    assert j == i or j == i + 1                               # no page break, and `recto` is ignored


def test_the_head_is_smaller_and_within_one_column(side):
    doc, _ = side
    i, title = _title_page(doc, "A CHAPTER IN A")
    full = _title_page(doc, "THE FIRST CHAPTER")[1]
    assert title["font"] == full["font"] == "IBMPlexSansCond-Bold"
    assert 14 < title["size"] < full["size"]
    eyebrow = next(sp for sp in _spans(doc[i]) if sp["text"].startswith("JULY 1944"))
    assert eyebrow["font"] == "IBMPlexSansCond-SemiBold" and abs(eyebrow["size"] - 8) < 0.1
    stand = next(sp for sp in _spans(doc[i]) if sp["text"].startswith("A short standfirst"))
    assert "Italic" in stand["font"] and stand["size"] < 12
    width = max(sp["bbox"][2] for sp in _spans(doc[i]) if sp["text"].startswith(("A CHAPTER", "COLUMN", "IN A")))
    assert width - title["bbox"][0] <= 194 + 1               # one text column of the side-notes grid


def test_space_above_and_the_text_after_on_the_grid(side):
    doc, _ = side
    j, _ = _title_page(doc, "THIRD")
    page = doc[j]
    eyebrow = next(sp for sp in _spans(page) if sp["text"].startswith("AUGUST 1944"))
    body = [sp for sp in _spans(page) if "Libertinus" in sp["font"] and abs(sp["size"] - 10) < 0.1]
    col = [sp for sp in body if abs(sp["bbox"][0] - eyebrow["bbox"][0]) < 3]
    above = [sp for sp in col if sp["bbox"][3] < eyebrow["bbox"][1]]
    assert above, "the third chapter should open partway down a column"
    assert eyebrow["bbox"][1] - max(sp["bbox"][3] for sp in above) > 2 * BASELINE
    offsets = {round((sp["origin"][1] - TOP) % BASELINE, 1) for sp in body}
    assert len(offsets) == 1, f"baselines off the grid: {offsets}"


def test_its_notes_begin_again_at_one(side):
    _, notes = side
    ns = [n["n"] for n in notes]
    assert ns == list(range(1, 25)) + [1, 2, 3]


def test_the_page_keeps_its_running_head(side):
    doc, _ = side
    i, _title = _title_page(doc, "A CHAPTER IN A")
    head = [sp for sp in _spans(doc[i]) if sp["bbox"][3] < TOP and abs(sp["size"] - 7.5) < 0.1]
    if i % 2 == 0:                                           # a recto: the chapter running at the page's top
        assert any("THE FIRST CHAPTER" in sp["text"] for sp in head)
    full = _title_page(doc, "THE FIRST CHAPTER")[0]
    assert not [sp for sp in _spans(doc[full]) if sp["bbox"][3] < TOP and abs(sp["size"] - 7.5) < 0.1]
    assert doc[i].get_drawings(), "no running head's rule"


def test_notes_at_the_end_name_the_column_chapter(tmp_path):
    doc, _ = _compile(tmp_path, notes="end")
    text = " ".join(page.get_text() for page in doc)
    tail = text[text.rindex("NOTES") if "NOTES" in text else text.rindex("Notes"):]
    assert re.search(r"The first chapter\s+1\s", tail) and re.search(r"A chapter in a column\s+1\s", tail)
