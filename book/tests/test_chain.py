"""The chain of command from the kit's relations: dates, levels, names and symbols read from the records' wording."""
from datetime import date

import pytest
from wwiibook import chain, paths


def test_a_relations_end_reads_exact_open_or_unknown():
    assert chain._day("1944-08-15", True) == (date(1944, 8, 15), False)
    assert chain._day("..1944-08-15", True) == (date(1944, 8, 15), True)
    assert chain._day("1945-05-06..", False) == (date(1945, 5, 6), True)
    assert chain._day("", True) == (None, True)


def test_a_formation_s_level_comes_from_its_printed_name():
    assert chain.level("v-corps", "V Corps, First US Army") == "corps"
    assert chain.level("seventh-army", "Seventh US Army") == "army"
    assert chain.level("12th-army-group", "12th Army Group") == "army group"
    assert chain.level("x", "62nd C.A.(AA) Regt.") == "regiment"
    assert chain.level("106aaa-d", "Battery D, 106th AAA AW Bn (SP)") == "company"
    assert chain.level("106aaa", "106th AAA AW Bn (SP)") == "battalion"


def test_a_narrow_bar_gets_a_shorter_name_never_a_different_one():
    forms = chain.short("V Corps, First US Army", "corps")
    assert forms[0] == "V Corps, First US Army" and "V Corps" in forms
    assert chain.short("45th Infantry Division", "division")[-1] == "45th Inf Div"


def test_a_unit_without_a_patch_is_drawn_with_its_fm_symbol_read_from_its_name():
    assert chain.fm("106aaa-d", "Battery D, 106th AAA AW Bn (SP)", "company") == {
        "arm": "antiaircraft", "echelon": "i", "label": "106", "letter": "D", "mobility": "sp"}
    assert chain.fm("313inf", "313th Inf Regt", "regiment")["arm"] == "infantry"


@pytest.mark.skipif(not (paths.records() / "army" / "relations.csv").exists(), reason="the kit's records")
def test_a_battalion_s_attachments_are_kept_apart_and_its_division_s_chain_drawn_only_inside_them():
    ss = chain.spans("106aaa-d", date(1944, 8, 1), date(1945, 5, 8))
    div = [s for s in ss if s.level == "division"]
    # the attachments table's first row has no end: it stops where the next row begins, and is drawn open
    assert div[0].start == date(1944, 8, 15) and div[0].end == date(1944, 8, 30) and div[0].open_end
    assert div[1].start == date(1944, 8, 31) and div[1].end == date(1944, 11, 10)
    # between 10 and 23 November the battalion was not attached: nothing above it is drawn
    assert not [s for s in ss if s.level == "corps" and s.start <= date(1944, 11, 15) <= s.end]
    # one formation a level at once, not one a path
    assert len([s for s in ss if s.level == "army group" and s.start <= date(1945, 1, 10) <= s.end]) == 1


@pytest.mark.skipif(not (paths.records() / "army" / "relations.csv").exists(), reason="the kit's records")
def test_leniently_the_same_army_is_carried_across_a_short_gap_but_a_detachment_is_not():
    ss = chain.spans("106aaa-d", date(1944, 8, 1), date(1945, 5, 8), bridge=45)
    assumed = [s for s in ss if s.basis == "assumed"]
    assert any(s.parent == "seventh-army" and s.start == date(1944, 11, 11) and s.end == date(1944, 11, 22)
               for s in assumed)
    assert not [s for s in assumed if s.level == "division"]


def test_an_open_end_fades_to_white_paper_in_solid_colours():
    svg = chain._fade("f1", 10, 24, 5, 24, "#e9e5d9", "2.5 1.8")
    assert "opacity" not in svg                                  # nothing for the press to flatten
    assert 'stop-color="#e9e5d9"' in svg and 'stop-color="#ffffff"' in svg
    assert svg.count("<line ") == 2 and 'stroke-dasharray="2.5 1.8"' in svg   # the outline fades as ink to white
    hatched = chain._fade("f2", 24, 10, 5, 24, "url(#attached)")
    assert f'stop-color="{chain.ATTACHED_GROUND}"' in hatched     # a hatched bar fades from its ground


@pytest.mark.skipif(not (paths.records() / "army" / "relations.csv").exists(), reason="the kit's records")
def test_a_timeline_with_open_ends_has_no_transparency_left():
    from wwiibook import solid
    svg, _ = chain.timeline("106aaa-d", "1944-08-01", "1945-05-08", width_in=6.0)
    assert "fade1-f" in svg and solid.remaining(solid.svg(svg)) == 0


@pytest.mark.skipif(not (paths.records() / "army" / "relations.csv").exists(), reason="the kit's records")
def test_the_key_runs_on_to_a_second_row_rather_than_past_the_figure_s_edge():
    import re
    svg, _ = chain.timeline("106aaa-d", "1944-08-01", "1945-05-08", width_in=5.55)
    assert "an end the record leaves open" in svg
    key_rows = {m.group(1) for m in re.finditer(r'<text x="[0-9.]+" y="([0-9.]+)"[^>]*>(?:assigned|attached|part of|'
                                                  r'inferred|an end)', svg)}
    assert len(key_rows) == 2
