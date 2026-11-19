"""A part's notes on pages of their own (`--input notes=part`, `wwiibook.partnotes`): the running-text example, with a
second chapter that carries its numbers on and a third that begins them again, sets no note and no sources in the
text but keeps its calls; every note is written out once with its number, its chapter's title and its source line
resolved (a source line inside a note's words too); the notes file `write` makes compiles, sets the notes section by
section with every number as the text called it, then the sources, in one list. Compiled with nothing prepared."""
import re
import shutil
from pathlib import Path

import pymupdf
import pytest
import typst
from wwiibook import partnotes, paths

BOOK = Path(__file__).resolve().parents[1] / "examples" / "running-text" / "book.typ"

MORE = """
#running-text(title: [A second chapter], recto: false, restart-notes: false)[
Carried on.#note(cite: "hist313/p90") A note with "quotes", _emphasis_, a \\# and a source line
(#source-line("rg64-480601116/p0031")).#note[It says "so" at #source-line("hist313/p91")]
]
#running-text(title: [A third chapter], recto: false)[
Begun again.#note(cite: "rg64-480601116/p0032")[Its words]
]
"""


def _kw(root: Path, mode: str) -> dict:
    return dict(root=str(root), package_path=str(paths.TYPST), font_paths=[str(paths.FONTS)], sys_inputs={"notes": mode})


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    copy = tmp_path_factory.mktemp("part") / "running-text"
    shutil.copytree(BOOK.parent, copy, ignore=shutil.ignore_patterns("build", "proof", "*.pdf"))
    (copy / "build").mkdir(exist_ok=True)
    (copy / "build" / "assets.json").write_text("{}")
    src = (copy / "book.typ").read_text()
    i = src.index("#section-sources(")
    (copy / "book.typ").write_text(src[:i] + MORE + "\n" + src[i:])
    typst.compile(str(copy / "book.typ"), output=str(copy / "book.pdf"), **_kw(copy, "part"))
    got = partnotes.collect(copy / "book.typ")
    return copy, got


def test_the_text_keeps_its_calls_and_sets_no_notes_or_sources(built):
    copy, got = built
    text = "\n".join(p.get_text() for p in pymupdf.open(str(copy / "book.pdf")))
    assert "NOTES" not in text and "Sources" not in text
    assert "NAID 480601116, p. 32" not in text      # a note's source line is set nowhere in the text
    assert len(got["notes"]) > 10 and got["sources"]


def test_every_note_is_written_out_with_its_number_chapter_and_source_line(built):
    _, got = built
    notes = got["notes"]
    ns = [v["n"] for v in notes]
    assert ns[-1] == 1 and ns[:-1] == list(range(1, len(ns)))        # carried on into chapter two, begun again in three
    assert [partnotes.plain(v["chapter"]) for v in notes[-3:]] == ["A second chapter"] * 2 + ["A third chapter"]
    assert "National Archives, RG 64, NAID 480601116, p. 32" in partnotes.plain(notes[-1]["text"])
    inner = partnotes.plain(notes[-2]["text"])
    assert inner.startswith('It says "so" at History of the 313th Infantry') and "p. 91" in inner


def test_sections_follow_the_numbering(built):
    _, got = built
    secs = partnotes.sections([got["notes"], got["notes"][:2]])
    assert len(secs) == 3                       # chapters 1-2 (one run), chapter 3, then the second file
    assert [partnotes.plain(c["title"]) for c in secs[0]["chapters"]][-1] == "A second chapter"
    assert [n for c in secs[0]["chapters"] for n, _ in c["notes"]] == list(range(1, len(got["notes"])))


def test_markup_sets_the_content_again():
    tree = {"func": "sequence", "children": [
        {"func": "text", "text": 'A "#hash" and \\ back'}, {"func": "space"}, {"func": "smartquote", "double": True},
        {"func": "emph", "body": {"func": "text", "text": "Italic"}}, {"func": "smartquote", "double": True},
        {"func": "link", "dest": "https://example.org/?a=1", "body": {"func": "text", "text": "p. 3"}},
        {"func": "raw", "text": "x/p1"}, {"func": "context"}]}
    m = partnotes.markup(tree)
    assert all(piece.startswith("#") for piece in re.split(r"(?<=[\])\"])(?=#)", m))
    assert partnotes.plain(tree) == 'A "#hash" and \\ back "Italic"p. 3x/p1'


def test_the_notes_file_sets_every_note_by_section_then_the_sources(built, tmp_path):
    _, got = built
    secs = partnotes.sections([got["notes"]])
    typ = partnotes.write(tmp_path / "notes" / "notes.typ", secs, partnotes.merge_sources([got["sources"]] * 2),
                          name="A test part", part="A test part · notes")
    (typ.parent / "build").mkdir()
    (typ.parent / "build" / "assets.json").write_text("{}")
    typst.compile(str(typ), output=str(typ.with_suffix(".pdf")), **_kw(typ.parent, "part"))
    doc = pymupdf.open(str(typ.with_suffix(".pdf")))
    text = re.sub(r"\s+", " ", " ".join(p.get_text() for p in doc))
    assert "NOTES" in text and "A TEST PART" in text
    assert text.index("A THIRD CHAPTER") < text.index("SOURCES")
    nums = [sp["text"].strip() for p in doc for b in p.get_text("dict")["blocks"] for ln in b.get("lines", [])
            for sp in ln["spans"] if re.fullmatch(r"\d+", sp["text"].strip()) and abs(sp["size"] - 7.2) < 0.3]
    assert [int(x) for x in nums] == [v["n"] for v in got["notes"]]
    assert 'It says “so” at History of the 313th Infantry' in text
    # one list of the whole book's sources, every run's: a source cited in both copies listed once, its pages joined
    listed = text[text.index("SOURCES"):]
    assert listed.count("Morning Reports for July 1944") == 1 and listed.count("History of the 313th Infantry in World") == 1
    assert re.search(r"Morning Reports for July 1944: Roll 523 \(5 of 5\), pp\. 9, 10, .*\b32, 58\.", listed)
