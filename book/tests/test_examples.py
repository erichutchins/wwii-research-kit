"""Every example book compiles, before any of its requests are prepared: the package's templates and each example's
calls to them are sound Typst (a request draws its placeholder until the build prepares it)."""
import shutil
from pathlib import Path

import pytest
import typst
from wwiibook import paths

EXAMPLES = sorted((Path(__file__).resolve().parents[1] / "examples").glob("*/book.typ"))


@pytest.mark.parametrize("book", EXAMPLES, ids=[b.parent.name for b in EXAMPLES])
def test_an_example_compiles_with_nothing_prepared(book, tmp_path):
    copy = tmp_path / book.parent.name
    shutil.copytree(book.parent, copy, ignore=shutil.ignore_patterns("build", "proof", "*.pdf"))
    (copy / "build").mkdir()
    (copy / "build" / "assets.json").write_text("{}")
    typst.compile(str(copy / "book.typ"), output=str(copy / "out.pdf"), root=str(copy),
                  package_path=str(paths.TYPST), font_paths=[str(paths.FONTS)])
    assert (copy / "out.pdf").stat().st_size > 1000


def test_the_blurb_magazine_page_is_trim_plus_bleed_on_three_edges(tmp_path):
    (tmp_path / "build").mkdir()
    (tmp_path / "build" / "assets.json").write_text("{}")
    (tmp_path / "b.typ").write_text('#import "@local/wwii-book:0.1.0": *\n#show: book.with(preset: "blurb-magazine")\n'
                                     + "= One\nText.\n#pagebreak()\nMore.\n")
    typst.compile(str(tmp_path / "b.typ"), output=str(tmp_path / "b.pdf"), root=str(tmp_path),
                  package_path=str(paths.TYPST), font_paths=[str(paths.FONTS)])
    from wwiibook.preflight import check
    rep = check(tmp_path / "b.pdf", "blurb-magazine")
    assert not [p for p in rep.problems if "pt, not" in p]          # 621 x 810, every page
    assert any("printer takes" in p for p in rep.problems)          # two pages: under the 24 minimum
