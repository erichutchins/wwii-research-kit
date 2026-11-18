"""How a torpedo was aimed: the figures' numbers are the kit's engage.js for BANG's Attack 3, 19 September 1944
(rg38-74802831/p17-p18): own course 340 at 2 knots, the target on 090 at 7 knots, 1,400 yards, gyros 351-0, tracks
61S-70S as typed. The figure's triangle has to close, and its angles to add up as the doctrine's definitions say."""
import math
import shutil
import subprocess
import xml.etree.ElementTree as ET

import pytest
from wwiibook import fire_control as fc
from wwiibook import paths

needs_node = pytest.mark.skipif(not shutil.which("node"), reason="the figures run the kit's site/engage.js under Node")
E, A = "taka-909-1944-09-19", "Attack 3"


def _engage(expr: str) -> float:
    """One number straight from engage.js, for the figure's to be checked against."""
    js = f"const E = require(process.argv[1]); process.stdout.write(String({expr}));"
    r = subprocess.run([shutil.which("node") or "node", "-e", js, str(paths.KIT / "site" / "engage.js")],
                       capture_output=True, text=True, check=True)
    return float(r.stdout)


@needs_node
def test_triangle_attack_3():
    svg, n = fc.triangle(E, A, 3.2, "bang")
    ET.fromstring(svg)
    assert n["own_course"] == 340 and n["own_speed"] == 2
    assert n["target"] == {"course": 90, "speed": 7, "range": 1400}
    # the solution engage.js's attackSheet gives, the point of aim in the middle of the spread
    assert n["bearing"] == pytest.approx(328.1, abs=0.05)
    assert n["aob"] == pytest.approx(58.1, abs=0.05)
    assert n["lead"] == pytest.approx(7.4, abs=0.05)
    assert n["gyro"] == pytest.approx(355.5, abs=0.05) and n["side"] == "S"
    # the doctrine's sum: track angle = angle on the bow + lead
    assert n["track"] == pytest.approx(n["aob"] + n["lead"], abs=0.1)
    # the law of sines: sin L = k sin AOB, k = 7/46 (46 knots assumed: the sheet types no speed)
    assert n["torpedo_knots"] == 46 and any("46 knots" in s for s in n["assumed"])
    assert math.sin(math.radians(n["lead"])) == pytest.approx(7 / 46 * math.sin(math.radians(n["aob"])), abs=1e-3)
    # the typed tracks follow from own course + the typed gyros, so nothing is flagged
    assert [t["track"] for t in n["torpedoes"]] == ["61S", "64S", "67S", "70S"]
    assert [t["derived_track"] for t in n["torpedoes"]] == ["61S", "64S", "67S", "70S"]
    assert n["disagree"] == []
    assert n["cites"] == ["rg38-74802831/p17", "rg38-74802831/p18"]


@needs_node
def test_triangle_against_engage():
    """The figure's numbers against engage.js called directly, not through the figure's own Node script."""
    _, n = fc.triangle(E, A, 3.2, "bang")
    fire = "E.fireControl({ownCourse: 340, gyro: 355.5, targetCourse: 90, targetSpeed: 7, torpedoSpeed: 46})"
    assert n["lead"] == pytest.approx(_engage(fire + ".lead"), abs=0.05)
    assert n["aob"] == pytest.approx(_engage(fire + ".aob"), abs=0.05)
    assert n["track"] == pytest.approx(_engage(fire + ".track"), abs=0.05)
    # the triangle closes: the torpedo's run along its course ends on the target's track, where she is when it arrives
    sh = fc.sheet(E, A, "bang")
    s = fc.solve(sh["torpedoes"])["aim"]
    ix, iy = fc._along((0, 0), s["torpedoCourse"], s["run"])
    tx, ty = s["p0"]
    assert iy == pytest.approx(ty, abs=0.5)            # the target's course is 090: her track is a line of latitude
    target_run = math.hypot(ix - tx, iy - ty)
    assert target_run / s["run"] == pytest.approx(7 / 46, rel=1e-3)
    assert n["distance_to_track"] == pytest.approx(1400 * math.sin(math.radians(n["aob"])), abs=1)


@needs_node
def test_aob_strip():
    svg, n = fc.aob_strip(E, A, 5.5, "bang", (20, 45, 90, 135, 160))
    ET.fromstring(svg)
    p = n["panels"]
    assert [round(x["aob"]) for x in p] == [20, 45, 58, 90, 135, 160]
    assert [x["as_fired"] for x in p] == [False, False, True, False, False, False]
    # the lead is greatest square on the beam, and never more than asin(k)
    assert max(p, key=lambda x: x["lead"])["aob"] == pytest.approx(90, abs=0.1)
    assert all(x["lead"] <= math.degrees(math.asin(7 / 46)) + 0.05 for x in p)
    assert all(x["track"] == pytest.approx(x["aob"] + x["lead"], abs=0.1) for x in p)


def test_tdc_dials_named_as_the_site_names_them():
    svg, n = fc.tdc_diagram(5.5)
    ET.fromstring(svg)
    assert n["position_keeper"] == fc.PK_DIALS and n["angle_solver"] == fc.AS_DIALS
    assert "op1056/p107" in n["cites"] and "op1056/p111" in n["cites"]


def test_red_only_for_hits():
    """Torpedoes and own ship in BANG's blue; the figures carry no hit, so no red."""
    for svg in (fc.tdc_diagram(5.5)[0],) + ((fc.triangle(E, A, 3.2, "bang")[0],) if shutil.which("node") else ()):
        assert "#a3241b" not in svg.lower() and fc.BLUE in svg
