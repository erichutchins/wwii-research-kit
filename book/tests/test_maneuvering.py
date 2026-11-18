"""The maneuvering board: typed values read as typed, disagreements said, and the solution the kit's engage.js gives.

The cases are BANG's attacks 3 and 4 on 19 September 1944 (rg38-74802831/p17-p20)."""
import shutil
import xml.etree.ElementTree as ET

import pytest
from wwiibook import maneuvering as m


def test_typed_values():
    assert m._seconds("0915") == 9 * 3600 + 15 * 60
    assert m._seconds("0915-55") == 9 * 3600 + 15 * 60 + 55
    assert m._signed_track("61S") == 61
    assert m._signed_track("76P") == -76
    assert m._signed_track("-") is None


def test_derived_track():
    # own course 340 + gyro 351 = torpedo course 331; against a target on 090 that is a 61 starboard track (as typed)
    assert m.derived_track(331, 90) == pytest.approx(61)
    # own course 340 + gyro 205 = 185; against 090, 85 port (typed 76P: the sheet's own note)
    assert m.derived_track(185, 90) == pytest.approx(-85)


needs_node = pytest.mark.skipif(not shutil.which("node"), reason="the board runs the kit's site/engage.js under Node")


@needs_node
def test_board_taka_909():
    svg, notes = m.board("taka-909-1944-09-19", ["Attack 3", "Attack 4"], 5.0)
    ET.fromstring(svg)
    a, b = notes["targets"]
    # the bow salvo's target fine on the port bow, the stern salvo's astern: from engage.js's attackSheet
    assert a["bearing"] == pytest.approx(328.1, abs=0.2) and a["range"] == 1400
    assert b["bearing"] == pytest.approx(189.1, abs=0.2) and b["range"] == 1200
    assert a["typed_track"] == "61S–70S" and b["typed_track"] == "76P–85P"
    # attack 4's typed tracks are said not to fit, attack 3's are not
    assert len(notes["disagree"]) == 1 and notes["disagree"][0].startswith("Attack 4")
    assert "rg38-74802831/p17" in notes["cites"] and "rg38-74802831/p20" in notes["cites"]
    assert notes["t0"] == [0, 55]
    assert any("400 ft by 55" in s for s in notes["assumed"])
