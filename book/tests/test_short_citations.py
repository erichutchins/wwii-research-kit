"""Repeated citations on a part's notes pages, and a section's sources across chapters that begin their numbers again.

A small book of two chapters, the second beginning its numbers at 1 again: a newspaper with a parenthesised aside in
its title, a book that declares its own short title, a family paper cited by its title alone, and an archive item.
Built in the "part" mode, `partnotes.abbreviate` sets the first citation of each in full and every later bare one in
its short form, and never shortens a note with words of its own. Built with the notes beside the text, the sources
set once at the section's end list every chapter's citations, not only the last chapter's. Compiled with nothing
prepared."""
import re

import pymupdf
import pytest
import typst
from wwiibook import partnotes, paths

BOOK = """#import "@local/wwii-book:0.1.0": *
#show: book.with(preset: "blurb-magazine")
#show: on-grid.with(sources: (
  news: [_The Star_, 1 May 1942 (a library's copy)],
  hist: (title: [Smith, _A History of the Regiment_ (1947)], short: [Smith, history]),
  fam: (title: [A family's war history (family papers)], short: [Family war history]),
))
#let fam = [A family's war history (family papers)]
#running-text(title: [One])[
A.#note(cite: "news/p1") B.#note(cite: "news/p2") C.#note[#fam] D.#note[#fam]
E.#note(cite: "rg64-480601116/p0031") F.#note(cite: "rg64-480601116/p0032") G.#note(cite: "news/p3")[Its words]
H.#note(cite: "hist/p5") I.#note(cite: "hist/p6")
]
#running-text(title: [Two], recto: false)[
J.#note(cite: "news/p4") K.#note(cite: "rg64-480601116/p0033") L.#note[#fam: and words of its own]
]
#section-sources(titles: ("480601116": "Morning Reports for July 1944"))
"""


def _kw(root, mode):
    return dict(root=str(root), package_path=str(paths.TYPST), font_paths=[str(paths.FONTS)], sys_inputs={"notes": mode})


@pytest.fixture(scope="module")
def book(tmp_path_factory):
    d = tmp_path_factory.mktemp("short")
    (d / "book.typ").write_text(BOOK)
    return d / "book.typ"


@pytest.fixture(scope="module")
def notes(book):
    got = partnotes.collect(book)
    [lst] = partnotes.abbreviate([got["notes"]], [got["titles"]])
    return [re.sub(r"\s+", " ", partnotes.plain(v["text"])).strip() for v in lst]


def test_the_first_citation_is_full_and_a_repeat_is_short(notes):
    assert notes[0] == "The Star, 1 May 1942 (a library's copy), p. 1."
    assert notes[1] == "The Star, 1 May 1942, p. 2."                   # derived: the aside left out
    assert notes[4] == "National Archives, RG 64, NAID 480601116, p. 31."
    assert notes[5] == "NAID 480601116, p. 32."
    assert notes[7] == "Smith, A History of the Regiment (1947), p. 5."
    assert notes[8] == "Smith, history, p. 6."                          # its own short title


def test_a_note_that_is_a_title_alone_is_a_citation(notes):
    assert notes[2] == "A family's war history (family papers)."
    assert notes[3] == "Family war history."


def test_a_note_with_words_is_never_shortened(notes):
    assert notes[6] == "Its words. The Star, 1 May 1942 (a library's copy), p. 3."
    assert notes[11] == "A family's war history (family papers): and words of its own."


def test_the_short_forms_run_across_the_numbering(notes):
    # chapter Two begins its numbers again; the part has cited both sources already
    assert notes[9] == "The Star, 1 May 1942, p. 4."
    assert notes[10] == "NAID 480601116, p. 33."


def test_the_notes_file_sets_the_short_forms_and_no_sources(book, tmp_path):
    got = partnotes.collect(book)
    secs = partnotes.sections(partnotes.abbreviate([got["notes"]], [got["titles"]]))
    typ = partnotes.write(tmp_path / "notes" / "notes.typ", secs, name="A part")
    typst.compile(str(typ), output=str(typ.with_suffix(".pdf")), **_kw(typ.parent, "part"))
    text = re.sub(r"\s+", " ", " ".join(p.get_text() for p in pymupdf.open(str(typ.with_suffix(".pdf")))))
    assert "Smith, history, p. 6." in text and "NAID 480601116, p. 32." in text
    assert "SOURCES" not in text


def test_the_sources_set_once_list_every_chapter(book):
    pdf = book.with_suffix(".pdf")
    typst.compile(str(book), output=str(pdf), **_kw(book.parent, "side"))
    text = re.sub(r"\s+", " ", " ".join(p.get_text() for p in pymupdf.open(str(pdf))))
    listed = text[text.rindex("Sources"):]
    assert "pp. 1, 2, 3, 4." in listed                                  # both chapters' pages of the newspaper
    assert re.search(r"Morning Reports for July 1944, pp\. 31, 32, 33\.", listed)
    assert "Smith, A History of the Regiment (1947), pp. 5, 6." in listed
