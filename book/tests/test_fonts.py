"""Every face a book page uses is one the package ships, or Libertinus Serif, the body face, which Typst itself
carries: a family Typst can't find falls back silently to a system font, which varies from machine to machine and
can't be relied on in print."""
import pymupdf
import pytest
import typst
from wwiibook import paths

BUNDLED = ("LibertinusSerif", "IBMPlexSansCond", "CourierPrime", "TT2020StyleE", "ShipporiMincho", "NotoSerifJPSymbols")

PAGE = r"""
#import "@local/wwii-book:0.1.0": *
#show: book.with(preset: "blurb-magazine")
#show: on-grid
#running-text(title: [Fonts], eyebrow: [Every face], standfirst: [_Italic_ standfirst.])[
Body text, *bold*, _italic_, #text(weight: "semibold")[semibold], old-style 1944.#note[A note]
#text(font: tokens.typed)[0915-55 typed, rg38-74802831/p17] #text(font: tokens.typed-effect)[typed for effect]
#text(font: tokens.ja, lang: "ja")[第二東勢丸雷撃ヲ受ク] and in a note, quoted: 一九 0925 ✓第二東勢丸 ｜ ─ ∠ ﾄ
`a raw key`
== A section head
]
"""


def test_a_page_uses_only_bundled_faces(tmp_path):
    src = tmp_path / "page.typ"
    src.write_text(PAGE)
    pdf = tmp_path / "page.pdf"
    typst.compile(str(src), output=str(pdf), root=str(tmp_path), package_path=str(paths.TYPST),
                  font_paths=[str(paths.FONTS)])
    used = {f[3].split("+")[-1] for page in pymupdf.open(str(pdf)) for f in page.get_fonts()}
    stray = {u for u in used if not u.startswith(BUNDLED)}
    assert not stray, f"faces not shipped with the package: {sorted(stray)}"
    for face in ("LibertinusSerif-Regular", "LibertinusSerif-Italic", "LibertinusSerif-Bold"):
        assert any(u.startswith(face) for u in used), f"{face} not used"
    assert "IBMPlexSansCond-Bold" in used                 # the heads


@pytest.mark.parametrize("name", ["IBMPlexSansCond-SemiBold", "CourierPrime-Regular", "ShipporiMincho-Regular",
                                  "TT2020StyleE-Regular", "NotoSerifJPSymbols-Regular"])
def test_each_role_resolves(tmp_path, name):
    src = tmp_path / "page.typ"
    src.write_text(PAGE)
    pdf = tmp_path / "page.pdf"
    typst.compile(str(src), output=str(pdf), root=str(tmp_path), package_path=str(paths.TYPST),
                  font_paths=[str(paths.FONTS)])
    used = {f[3].split("+")[-1] for page in pymupdf.open(str(pdf)) for f in page.get_fonts()}
    assert name in used
