import math

import numpy as np
from wwiibook.atlas import terrain
from wwiibook.atlas.extent import ATLAS, Extent, Page
from wwiibook.atlas.oblique import Camera
from wwiibook.atlas.reconstruct import _gaps


def test_the_extent_loads_in_its_projected_frame():
    ex = Extent.load("la-haye-du-puits")
    x0, y0, x1, y1 = ex.bounds
    assert ex.crs == "EPSG:2154" and 30_000 < x1 - x0 < 50_000 and 15_000 < y1 - y0 < 30_000
    x, y = ex.to_crs.transform(-1.5451, 49.2911)            # La Haye-du-Puits
    assert x0 < x < x1 and y0 < y < y1
    assert (ATLAS / "la-haye-du-puits" / "extent.yml").exists()


def test_a_page_keeps_one_scale_both_ways_and_puts_north_up():
    p = Page((0, 0, 40_000, 20_000), 720)
    assert p.height == 360
    x, y = p.pt([0, 40_000], [20_000, 0])
    assert list(x) == [0, 720] and list(y) == [0, 360]


def test_a_dashed_line_reads_broken_and_a_solid_one_not():
    solid = np.full(60, 12.0)                               # a way 12 m off a continuous line
    dashed = solid.copy()
    dashed[np.arange(60) % 15 >= 11] = 45.0                 # the gaps between dashes: the ink much farther off
    assert _gaps(solid) == 0.0 and _gaps(dashed) > 0.15


def test_the_camera_sees_the_far_edge_higher_and_smaller():
    cam = Camera((0, 0, 40_000, 20_000), azimuth=90, tilt=15, exaggeration=5, width_px=1000)
    u_near, v_near, z_near = cam.screen(0, 10_000, 0, 0)
    u_far, v_far, z_far = cam.screen(40_000, 10_000, 0, 0)
    assert z_far > z_near and v_far < v_near                 # farther up the picture
    assert abs(u_near - 500) < 1e-6 and abs(u_far - 500) < 1e-6
    _, v_hill, _ = cam.screen(20_000, 10_000, 100, 0)
    _, v_flat, _ = cam.screen(20_000, 10_000, 0, 0)
    assert v_hill < v_flat                                   # a hill stands up


def test_flat_ground_is_shaded_as_the_sun_is_high_and_the_sea_found_from_the_edge():
    z = np.zeros((40, 40), dtype=np.float32)
    z[10:30, 10:30] = 20                                     # an island
    g = terrain.Grid(z, 0, 800, 20)
    shade = terrain.hillshade(g, altitude=45)
    assert abs(shade[0, 0] - math.sin(math.radians(45))) < 1e-3
    sea = terrain.sea(g)
    assert sea[0, 0] and not sea[20, 20]


def test_an_edition_is_described_by_its_distance_from_the_battle():
    from wwiibook.atlas.reconstruct import _validity
    assert "5 years before the battle" in _validity("road", 1939)
    assert "1 year after" in _validity("road", 1945) and "taken to have existed" in _validity("rail", 1947)
    assert "post-war work may show" in _validity("road", 1956)


def test_grid_lines_are_numbered_on_a_lattice_and_a_stray_line_is_dropped():
    from wwiibook.atlas.gsgs import _lattice
    lines = [(100.0 + 141 * k, 0.0) for k in range(8) if k != 3]     # the fourth line not found
    lines.insert(2, (100.0 + 141 * 1.5, 0.0))                       # a stretch of lettering in the grid's ink
    kept, km = _lattice(lines, 1000, 141.0)
    assert list(km) == [0, 1, 2, 4, 5, 6, 7] and len(kept) == 7


def test_the_north_west_africa_grid_places_a_reference_as_the_kits_tools_do():
    from pyproj import Transformer
    from wwiibook.atlas.gsgs import GRIDS
    lon, lat = Transformer.from_crs(GRIDS["nwa"], "EPSG:4326", always_xy=True).transform(1877500, 891400)
    assert abs(lon - 9.8837) < 0.002 and abs(lat - 37.1468) < 0.002     # J 775914, as tools/grid_ref.py places it


def test_a_grid_placed_position_wears_its_reference_not_the_town_alone():
    from wwiibook.atlas.record import name
    m = {"placed": "grid", "grid": "J 775914", "place": "Ferryville", "offset": "3 mi E"}
    assert name(m) == "J 775914 (Ferryville, 3 mi E)"
    assert name({**m, "placed": "town", "grid": ""}) == "Ferryville, 3 mi E"
    assert name({"placed": "grid", "grid": "Q-8628", "place": "Zutzendorf", "offset": ""}) == "Zutzendorf"


def test_a_position_at_a_named_town_leaves_the_name_to_the_town():
    from wwiibook.atlas.record import at_town
    ex = Extent.load("bizerte")
    places = [{"properties": {"name": "Mateur"}, "geometry": {"coordinates": [9.6646, 37.0400]}},
              {"properties": {"name": "Menzel Bourguiba"}, "geometry": {"coordinates": [9.7853, 37.1536]}}]
    st = {"kind": "station", "place": "Mateur", "offset": "", "lon": 9.6677, "lat": 37.0386, "placed": "town"}
    assert at_town(ex, st, places) == "Mateur"
    assert at_town(ex, {**st, "place": "Ferryville", "lon": 9.7853, "lat": 37.1536}, places) == "Menzel Bourguiba"
    assert at_town(ex, {**st, "offset": "3 mi E"}, places) is None          # an offset keeps its own words


def test_a_loose_offset_folds_into_the_next_grid_reference_for_the_same_place():
    from wwiibook.atlas.record import stations
    unit = {"stations": [
        {"date": "1943-06-19", "place": "La Calle", "offset": "", "placed": "town", "lon": 8.44, "lat": 36.89},
        {"date": "1943-06-20", "place": "Ferryville", "offset": "3 mi E", "placed": "town", "lon": 9.85, "lat": 37.155},
        {"date": "1943-07-04", "place": "Ferryville", "offset": "3 mi E", "placed": "grid", "lon": 9.884, "lat": 37.147},
    ]}
    rows = stations(unit)
    assert [r["date"] for r in rows] == ["1943-06-19", "1943-07-04"] and rows[1]["assumed_from"] == "1943-06-20"


def test_the_antiaircraft_and_medical_symbols_are_the_manuals():
    from wwiibook.symbols import symbol
    aa = symbol(0, 0, {"of": "us", "arm": "antiaircraft", "echelon": "i", "letter": "D", "label": "106",
                       "mobility": "sp"}, colour="#a3241b")
    assert ">I<" in aa and ">D<" in aa and ">106<" in aa and aa.count("<path") >= 2     # tail, triangle
    med = symbol(0, 0, {"of": "us", "arm": "medical", "label": "67"})
    assert "V" in med.split("<path")[1] and ">67<" in med                                # the cross: one stroke each way


def test_the_grid_lattice_is_set_by_most_lines_not_a_stray_first_one():
    from wwiibook.atlas.gsgs import _lattice
    lines = [(37.0, 0.0)] + [(100.0 + 157 * k, 0.0) for k in range(10)]    # the frame, then the grid
    kept, km = _lattice(lines, 1000, 157.0)
    assert len(kept) == 10 and list(km) == list(range(10)) and kept[0][0] == 100.0


def test_a_ruled_tint_is_not_a_line_but_a_stroke_on_it_is():
    from wwiibook.atlas.gsgs import _darker
    lum = np.full((60, 60), 150.0)
    lum[::2, :] = 140                       # a fine ruled tint, as the sheets print the sea
    lum[:, 30:33] = 100                     # a grid line across it
    d = _darker(lum, 11)
    assert d[30, 31] > 12 and d[30, 10] < 6


def test_the_jets_notional_attack_runs_up_the_course_turns_and_ends_on_the_loss_from_behind():
    from wwiibook.atlas.mission import _attack_path
    sketch = [[11.0, 48.9], [11.1, 48.8]]                # a course south-east
    end = (11.12, 48.78)
    path = _attack_path(sketch, end)
    assert path[-1] == end
    # the first leg runs north-west (against the course): latitude rises, longitude falls
    assert path[1][1] > path[0][1] and path[1][0] < path[0][0]
    # the last leg runs south-east (with the course), from behind the loss
    (a, b), (c, d) = path[-2], path[-1]
    assert d < b and c > a


def test_a_route_time_is_inside_or_outside_the_fights_minutes():
    from wwiibook.atlas.mission import _in_window
    w = ["1130", "1200"]
    assert _in_window("1150", w) and _in_window("1130-1145", w) and _in_window("", w)
    assert not _in_window("1725", w)


def test_the_reach_cut_by_a_section_off_the_guns_is_the_smaller_circle():
    import math
    R, off = 3200.0, 1840.0                              # a 3.2 km reach, the section 1.84 km off the guns
    r = math.sqrt(R ** 2 - off ** 2)
    assert 2600 < r < 2630
