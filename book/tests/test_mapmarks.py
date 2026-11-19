"""The marks every map carries: north, and a scale in km and miles on land, nautical miles at sea."""
import re

from wwiibook import mapmarks


def test_land_bar_gives_km_and_miles_each_its_own_length():
    svg, width = mapmarks.scale(10, 50, 4.0, "land", max_len=60)        # 4 pt a km: 10 km is 40 pt, 5 mi 32 pt
    assert ">10 km<" in svg and ">5 mi<" in svg and width == 40


def test_sea_bar_is_nautical_miles():
    svg, _ = mapmarks.scale(10, 50, 1.0, "sea", max_len=60)            # 1 pt a km: 25 nm is 46 pt
    assert ">25 nautical miles<" in svg and " km<" not in svg


def test_bar_anchored_at_its_end():
    svg, width = mapmarks.scale(100, 50, 4.0, "land", max_len=60, anchor="end")
    assert f'x1="{100 - width:.1f}"' in svg


def test_north_points_where_north_is():
    up = mapmarks.north(50, 50, 0)
    tip = re.search(r'x2="([\d.]+)" y2="([\d.]+)"', up).groups()
    assert float(tip[0]) == 50 and float(tip[1]) < 50 and ">N<" in up
    # a view looking south: north on the ground runs down the page
    assert abs(mapmarks.north_angle(lambda lo, la: (lo * 100, la * 100), 0, 0) - 180) < 1e-6
