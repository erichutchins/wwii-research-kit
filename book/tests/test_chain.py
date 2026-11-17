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
