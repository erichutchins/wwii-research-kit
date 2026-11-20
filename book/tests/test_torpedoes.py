"""Each torpedo as a silhouette, grouped by attack into forward and after tubes, hits in red (torpedoes.py)."""
import xml.etree.ElementTree as ET

import pytest
from wwiibook import torpedoes

NS = "{http://www.w3.org/2000/svg}"


def row(attack, tube, hit, time="2256", zone="K", page="rg38-1/p16"):
    return {"attack": attack, "date": "1944-04-29", "time": time, "zone": zone, "tube": tube, "hit": hit,
            "torpedo": "23", "page": page}


ROWS = [row("Attack 1", "1", "Miss"), row("Attack 1", "2", "Hit"), row("Attack 1", "3", "Hit"),
        row("Attack 2", "9", "Miss", "0356", page="rg38-1/p21"), row("Attack 2", "7", "", "0356", page="rg38-1/p21"),
        row("Attack 2", "1", "Hit", "0357", page="rg38-1/p21"), row("Attack 3", "", "Hit", "0400")]


def test_tubes_one_to_six_are_forward_and_seven_to_ten_aft():
    a = {s["attack"]: s for s in torpedoes.salvos(ROWS)}
    assert [t["tube"] for t in a["Attack 1"]["forward"]] == ["1", "2", "3"] and a["Attack 1"]["after"] == []
    assert [t["tube"] for t in a["Attack 2"]["after"]] == ["9", "7"]          # in the order the sheet types them
    assert [t["tube"] for t in a["Attack 2"]["forward"]] == ["1"]
    assert [t["tube"] for t in a["Attack 3"]["unplaced"]] == [""]             # no tube typed: set apart
    assert a["Attack 2"]["times"] == ["0356", "0357"] and a["Attack 2"]["pages"] == ["rg38-1/p21"]


def test_only_a_typed_hit_is_a_hit():
    assert [torpedoes.state(h) for h in ("Hit", "hit?", "Miss", "", "-", "Erratic")] == \
        ["hit", "hit", "miss", "none", "none", "none"]


def test_attacks_named_are_kept_in_the_order_named():
    assert [s["attack"] for s in torpedoes.salvos(ROWS, ["Attack 2", "Attack 1"])] == ["Attack 2", "Attack 1"]
    with pytest.raises(ValueError):
        torpedoes.salvos(ROWS, ["Attack 9"])


def test_hits_are_red_and_the_rest_outlined():
    svg = torpedoes.salvo_svg(torpedoes.salvos(ROWS, ["Attack 1", "Attack 2"]))
    root = ET.fromstring(svg)
    groups = [g for g in root.iter(f"{NS}g") if "torpedo" in (g.get("class") or "").split()]
    drawn = [(g.get("class") or "").split()[1] for g in groups]
    # each attack's after group, then its forward group, each in the order fired
    assert drawn == ["miss", "hit", "hit", "miss", "none", "hit", "hit", "miss"]   # and the key's two
    for g in groups:
        body = next(g.iter(f"{NS}path"))
        if "hit" in (g.get("class") or ""):
            assert body.get("fill") == torpedoes.HIT
        else:
            assert body.get("fill") == torpedoes.PAPER and body.get("stroke") == torpedoes.INK
    assert "a hit, as the attack sheet records it" in svg and "forward tubes" in svg and "after tubes" in svg
    assert "tube not recorded" not in svg


def test_it_fits_a_column():
    svg = torpedoes.salvo_svg(torpedoes.salvos(ROWS, ["Attack 1", "Attack 2"]))
    assert float((ET.fromstring(svg).get("width") or "")[:-2]) <= 194                 # a text column of the grid


def test_a_salvos_count_of_hits_colours_no_torpedo():
    rows = [row("Attack 1", "1", ""), row("Attack 1", "2", ""), row("Attack 1", "3", ""), row("Attack 2", "7", "Hit")]
    sheets = [{"attack": "Attack 1", "hits": "2 Hits"}, {"attack": "Attack 2", "hits": "1 Hit"}]
    a = {s["attack"]: s for s in torpedoes.salvos(rows, sheets=sheets)}
    assert a["Attack 1"]["salvo_hits"] == 2
    assert a["Attack 2"]["salvo_hits"] == 0               # a torpedo's own hit is typed: the count isn't needed
    svg = torpedoes.salvo_svg(list(a.values()))
    root = ET.fromstring(svg)
    groups = [g for g in root.iter(f"{NS}g") if "torpedo" in (g.get("class") or "").split()]
    assert [(g.get("class") or "").split()[1] for g in groups][:4] == ["none", "none", "none", "hit"]
    assert len([c for c in root.iter(f"{NS}circle") if c.get("class") == "salvo-hit"]) == 2
    assert "2 hits, not by tube" in svg
