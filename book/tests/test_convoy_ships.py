"""A convoy several boats attacked: its ships at one scale, their fates as the Japanese records give them, and the
tally of claims, JANAC's credit and the records, each row citing its pages.

The cases are convoys TAKA-206 (BANG, REDFISH, SHAD; 22-23 November 1944) and TE-04 (BANG, PARCHE, TINOSA; 3-4 May
1944), from the kit's engagement.json for each."""
import re

import pytest
from wwiibook import convoy_ships as c

ENGAGEMENTS = ("taka-206-1944-11-22", "te-04-1944-05-03")
PATH = re.compile(r'<path data-ship="([^"]+)" data-sil="([^"]+)" data-length="([\d.]+)" '
                  r'transform="translate\([\d.]+,[\d.]+\) scale\(([\d.]+)\)"')


@pytest.mark.parametrize("eid", ENGAGEMENTS)
def test_one_scale(eid):
    svg, notes = c.silhouettes(eid, 5.5)
    drawn = PATH.findall(svg)
    assert len(drawn) == len(notes["drawn"]) + 1          # every plated ship, and one boat for scale
    scales = {float(k) for *_, k in drawn}
    assert len(scales) == 1                               # feet to points the same for every plate
    k = scales.pop()
    assert k == pytest.approx(notes["pt_per_ft"], rel=1e-5)
    bar = re.search(r'data-bar="100" d="M([\d.]+),[\d.]+V[\d.]+H([\d.]+)', svg)
    assert float(bar.group(2)) - float(bar.group(1)) == pytest.approx(100 * k, abs=0.02)
    assert notes["scale_boat"] == "BANG"


def test_ships_without_a_plate_are_listed_not_drawn():
    svg, notes = c.silhouettes("taka-206-1944-11-22", 5.5)
    assert notes["drawn"] == ["Manazuru", "W-15"]         # the merchant ships' silhouette is only "cargo", a kind
    assert "Hozan Maru" in notes["not_drawn"] and "Hozan Maru" in svg
    assert 'data-ship="Hozan Maru"' not in svg


def test_fates_match_the_japanese_records():
    taka = c.fates("taka-206-1944-11-22")
    assert {n for n, f in taka.items() if f["mark"] == "sunk"} == {"Hozan Maru", "Amakusa Maru", "Sakae Maru"}
    assert "jacar:C16120660200 p08" in taka["Hozan Maru"]["refs"]          # the Imperial Navy's November summary
    assert taka["Sakae Maru"]["words"].startswith("sunk 24 Nov 1944")      # her movement sheet: the 24th
    assert taka["Manazuru"]["mark"] is None and taka["Taiken Maru"]["mark"] is None
    te = c.fates("te-04-1944-05-03")
    assert {n for n, f in te.items() if f["mark"] == "sunk"} == {"Kinrei Maru", "Shoryu Maru", "Taiyoku Maru",
                                                                 "Toyohi Maru", "Daibu Maru"}
    assert te["Daibu Maru"]["refs"] == ["jacar:C08030140700 p26"]           # the May loss list: no log of her own
    assert te["Kinrei Maru"]["words"] == "sunk 0109 I, 4 May 1944"
    # every red mark in the drawing is a ship the records have sunk, and nothing else is marked
    for eid, f in (("taka-206-1944-11-22", taka), ("te-04-1944-05-03", te)):
        svg, _ = c.silhouettes(eid, 5.5)
        assert svg.count('data-fate="sunk"') == sum(v["mark"] == "sunk" for v in f.values())
        assert 'data-fate="damaged"' not in svg


@pytest.mark.parametrize("eid", ENGAGEMENTS)
def test_every_row_cites_its_pages(eid):
    t = c.tally(eid)
    assert t["rows"]
    for r in t["rows"]:
        assert all(tm["cite"].startswith("rg38-") for tm in r["times"])
        assert re.match(r"^rg38-\d+/p\d+$", r["claim"]["cite"]), r
        for j in r["janac"]:
            assert re.match(r"^janac:4/p\d+$", j["ref"]) and j["page"].startswith("JANAC 4, p. ")
        for x in r["records"]:
            assert x["ref"] and x["page"] and x["relation"] in c.RELATION
            assert x["primary"] == x["ref"].startswith("jacar:")


def test_janac_as_printed():
    t = c.tally("te-04-1944-05-03")
    rows = {(r["name"], r["attack"]): r for r in t["rows"]}
    j = {x["ship"]: x for x in rows[("BANG", "Attack 5")]["janac"]}
    assert j["Kinrei Maru"] == {**j["Kinrei Maru"], "tons": "5,947", "agent": "BANG", "probable": True,
                                "ref": "janac:4/p59"}
    assert j["Taiyoku Maru"]["agent"] == "PARCHE" and j["Shoryu Maru"]["probable"] is False
    # JANAC's spelling stands beside the records' own: Taibu Maru there, Daibu Maru (大武丸) in the loss list
    assert "Taibu Maru" in {x["ship"] for x in rows[("TINOSA", "Attack 2")]["janac"]}
    boats = {b["name"]: b for b in t["boats"]}
    assert [x["ship"] for x in boats["PARCHE"]["janac"]] == ["Shoryu Maru", "Taiyoku Maru"]
    assert boats["BANG"]["japanese_paired"] == [{"ship": "Taiyoku Maru", "relations": ["probable"]}]
    taka = {b["name"]: b for b in c.tally("taka-206-1944-11-22")["boats"]}
    assert [(x["ship"], x["tons"]) for x in taka["REDFISH"]["janac"]] == [("Hozan Maru", "2,345")]
    assert taka["BANG"]["claimed_sunk"] == 4                  # attacks 1, 2, 6 and 7, each "One ..."


def test_claim_counts_as_typed():
    assert c.count_claim("None.") == 0
    assert c.count_claim("One medium AK. EU.") == 1
    assert c.count_claim("One 5000-9000 ton AK or AP. One DD.") == 2
    assert c.count_claim("(1) AK similar to RYUYO MARU. (2) AK similar to GENOA MARU.") == 2
    assert c.count_claim("1-AO 7,500 1-AK 5,500") == 2
    assert c.count_claim("(UN) One unidentified engine-aft MARU. This ship gave the largest radar pip.") == 1
    assert c.count_claim("Unknown") == 0


def test_tonnage_and_names_as_written():
    ships = {s["ship"]: s for s in c._engagement("taka-206-1944-11-22")["convoys"]["taka-206"]["ships"]}
    assert c.tonnage(ships["Hozan Maru"]) == "2,345 tons displacement, as written"     # 二三四五
    assert c.written(ships["Manazuru"]) == "真鶴"
    assert c.basis_words("no13-minesweeper", ships["W-15"]["sil_basis"]).startswith("her class, assumed: No. 13 class")
    assert c.basis_words("type-k-ore-carrier", "representative").startswith("a type standing for her, assumed")
