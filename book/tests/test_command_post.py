"""The command post flag (FM 21-30): the unit's box on a staff whose foot is at the post."""
import re

from wwiibook import symbols

AAA = {"of": "us", "echelon": "ii", "arm": "antiaircraft", "mobility": "sp", "label": "106"}


def test_staff_foot_at_post_and_box_above():
    svg = symbols.command_post(100, 200, AAA, staff=11)
    x1, y1, x2, y2 = map(float, re.search(r'x1="([\d.]+)" y1="([\d.]+)" x2="([\d.]+)" y2="([\d.]+)"', svg).groups())
    assert (x1, y1) == (100, 200) and x2 == 100 and y2 < 200 - 11
    rect = re.search(r'<rect x="([\d.]+)" y="([\d.]+)"', svg)
    assert rect and float(rect.group(1)) == 100 and float(rect.group(2)) == y2   # flown from the staff's top
    assert ">106<" in svg and ">II<" in svg


def test_dashed_staff_when_assumed():
    assert "stroke-dasharray" not in symbols.command_post(0, 50, {**AAA, "mobility": ""})
    assert "stroke-dasharray" in symbols.command_post(0, 50, AAA, dashed=True)


def test_box_covers_the_flag():
    x, y, w, h = symbols.command_post_box(100, 200, staff=11)
    assert x <= 100 and w > 13 and y + h >= 200 and y <= 200 - 11 - 8.5
