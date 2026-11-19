"""The grid section's computation (gridref.py) against the worked examples the period sheets and records give."""
import math

from wwiibook import gridref


def test_the_alger_sheets_worked_example_is_square_h():
    # AMS Alger and vicinity (1942), sheet 3 of 7: "POINT MON ROUGE LETTERS H ... REFERENCE H743072"
    case = {"grid": "nwa", "ref": "H743072", "near": [36.75, 3.06]}
    p = gridref._point(case)
    assert gridref._letter("nwa", p["x"], p["y"]) == "H"
    assert p["cell"] == 100


def test_a_wrong_square_letter_moves_a_reference_a_hundred_kilometres():
    case = gridref.config()["cases"]["la-haye"]
    read, typed = gridref._point(case), gridref._point(case, case["slip"]["typed"])
    assert math.isclose(typed["y"] - read["y"], 100000, abs_tol=1)
    assert math.isclose(typed["x"], read["x"], abs_tol=1)
    assert gridref._letter("lambert1", read["x"], read["y"]) == "VT"
    assert gridref._letter("lambert1", typed["x"], typed["y"]) == "VO"


def test_letters_repeat_every_500_km_on_the_north_west_africa_grid():
    assert gridref._letter("nwa", 1_250_000, 750_000) == gridref._letter("nwa", 1_750_000, 750_000)
    assert gridref._letter("ndg", 0, 0) is None              # outside the one lettered block
