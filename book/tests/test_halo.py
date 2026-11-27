"""Halos under lettering: every label's halo is drawn before every label's fill (halo.layer)."""
import re

from wwiibook import halo, solid

LABEL = ('<text x="{x}" y="10" font-size="7" fill="#000000" stroke="#ffffff" stroke-width="2.2" '
         'stroke-linejoin="round" paint-order="stroke">{s}</text>')


def _texts(svg: str) -> list[tuple[str, str]]:
    """(halo|fill, words) for each text, in drawing order."""
    out = []
    for attrs, body in re.findall(r"<text([^>]*)>(.*?)</text>", svg, re.S):
        out.append(("halo" if 'aria-hidden="true"' in attrs else "fill", body))
    return out


def _svg(*body: str) -> str:
    return '<svg xmlns="http://www.w3.org/2000/svg" width="100pt" height="20pt">' + "".join(body) + "</svg>"


def test_every_halo_before_every_fill():
    svg = _svg('<rect width="100" height="20" fill="#eee"/>',
               LABEL.format(x=5, s="Roth"), LABEL.format(x=30, s="Monheim"), LABEL.format(x=60, s="Wellheim"))
    order = _texts(halo.layer(svg))
    assert order == [("halo", "Roth"), ("halo", "Monheim"), ("halo", "Wellheim"),
                     ("fill", "Roth"), ("fill", "Monheim"), ("fill", "Wellheim")]


def test_halo_carries_no_fill_paint_order_and_lettering_no_stroke():
    out = halo.layer(_svg(LABEL.format(x=5, s="Roth")))
    h, f = re.findall(r"<text([^>]*)>", out)
    assert 'fill="#ffffff"' in h and "paint-order" not in h and 'stroke="#ffffff"' in h
    assert 'fill="#000000"' in f and "stroke" not in f and "paint-order" not in f


def test_halos_cover_the_marks_drawn_among_the_labels():
    """The labels move to the place of the last of them, so a line drawn between two labels is under both halos."""
    svg = _svg('<path d="M0 0L100 20" stroke="#000"/>', LABEL.format(x=5, s="A"), '<circle r="2"/>',
               LABEL.format(x=30, s="B"), '<rect width="5" height="5"/>')
    out = halo.layer(svg)
    assert out.index("<path") < out.index("<circle") < out.index('<g class="halo"') < out.index(">A</text>") \
        < out.index("<rect")
    assert _texts(out) == [("halo", "A"), ("halo", "B"), ("fill", "A"), ("fill", "B")]


def test_groups_keep_their_own_labels():
    svg = _svg('<g transform="translate(10 0)">', LABEL.format(x=0, s="In"), "</g>", LABEL.format(x=50, s="Out"))
    out = halo.layer(svg)
    inner = out[out.index("<g transform"):out.rindex(">In</text></g>") + 14]
    assert _texts(inner) == [("halo", "In"), ("fill", "In")]          # the transform still applies to both
    assert _texts(out)[-2:] == [("halo", "Out"), ("fill", "Out")]


def test_old_split_pairs_are_gathered_and_layer_is_idempotent():
    pair = ('<text x="{x}" y="9" stroke="#ffffff" stroke-width="2" fill="#ffffff" aria-hidden="true">{s}</text>'
            '<text x="{x}" y="9" fill="#000">{s}</text>')
    old = _svg(pair.format(x=1, s="A"), pair.format(x=20, s="B"))
    once = halo.layer(old)
    assert [k for k, _ in _texts(once)] == ["halo", "halo", "fill", "fill"]
    assert halo.layer(once) == once
    assert once.count('<g class="halo"') == 1


def test_unhaloed_text_and_tspans_untouched():
    plain = _svg('<text x="1" y="9" fill="#000">plain <tspan font-weight="bold">bold</tspan></text>')
    assert halo.layer(plain) == plain
    nested = _svg(LABEL.format(x=1, s='A <tspan font-style="italic">b</tspan>'))
    assert _texts(halo.layer(nested)) == [("halo", 'A <tspan font-style="italic">b</tspan>'),
                                          ("fill", 'A <tspan font-style="italic">b</tspan>')]


def test_solid_runs_the_layering():
    svg = _svg(LABEL.format(x=5, s="Roth"), LABEL.format(x=30, s="Monheim"))
    out = solid.svg(svg)
    assert [k for k, _ in _texts(out)] == ["halo", "halo", "fill", "fill"]


def test_build_lays_the_halos_of_a_sections_own_drawings(tmp_path):
    """A section's own SVG (one its script wrote, or one committed beside its book) is layered in place by the build,
    which Typst would otherwise paint glyph by glyph; a second pass changes nothing."""
    from wwiibook.build import layer_halos
    (tmp_path / "figures").mkdir()
    own = tmp_path / "figures" / "map.svg"
    own.write_text(_svg(LABEL.format(x=5, s="Roth"), LABEL.format(x=30, s="Monheim")))
    plain = tmp_path / "plain.svg"
    plain.write_text(_svg('<rect width="5" height="5"/>'))
    assert layer_halos(tmp_path) == ["figures/map.svg"]
    assert _texts(own.read_text()) == [("halo", "Roth"), ("halo", "Monheim"), ("fill", "Roth"), ("fill", "Monheim")]
    assert layer_halos(tmp_path) == []
