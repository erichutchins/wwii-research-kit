"""An engagement's map and timeline from a small engagement.json, offline (no coastline download)."""
import json
import xml.etree.ElementTree as ET
from datetime import date

import pytest
from wwiibook import figures, geo


def cite(ref, kind="record"):
    return {"ref": ref, "kind": kind}


ENGAGEMENT = {
    "box": [118.0, 18.0, 120.0, 20.0],
    "window": {"from": "1944-04-29T06:00Z", "to": "1944-04-30T08:00Z"},
    "participants": [
        {"id": "bang", "name": "BANG", "of": "us", "kind": "submarine", "followed": True},
        {"id": "parche", "name": "PARCHE", "of": "us", "kind": "submarine", "followed": True},
        {"id": "tama-17", "name": "Convoy TAMA-17", "of": "jp", "kind": "convoy"},
    ],
    "places": [{"name": "Luzon", "lon": 119.9, "lat": 18.2}],
    "tracks": {
        "bang": [{"utc": "1944-04-29T06:00Z", "lon": 118.8, "lat": 19.9, "on_track": True},
                 {"utc": "1944-04-29T12:56Z", "lon": 118.75, "lat": 19.43, "on_track": True}],
        "parche": [{"utc": "1944-04-29T07:00Z", "lon": 118.3, "lat": 19.4, "on_track": True},
                   {"utc": "1944-04-29T14:00Z", "lon": 118.4, "lat": 19.0, "on_track": True, "assumed": True}],
    },
    "events": [
        {"origin": "track", "of": "us", "actor": "bang", "kind": "sighting", "utc": "1944-04-29T07:20Z",
         "local": "1944-04-29 1720 K", "lon": 118.78, "lat": 19.73, "cite": cite("rg38-1/p13")},
        {"origin": "track", "of": "us", "actor": "bang", "kind": "attack", "title": "Attack 1", "utc": "1944-04-29T12:56Z",
         "local": "1944-04-29 2256 K", "lon": 118.75, "lat": 19.43, "cite": cite("rg38-1/p16")},
        {"origin": "japanese", "of": "jp", "actor": "Takegawa Maru", "ship": "Takegawa Maru", "kind": "torpedoed",
         "utc": "1944-04-29T13:01Z", "local": "1944-04-29 2201 I", "lon": 118.83, "lat": 19.33,
         "note": "the master's log", "cite": cite("jacar:C1 p23")},
        {"origin": "frupac", "of": "us", "actor": "FRUPAC", "kind": "hit", "utc": "1944-04-29T13:15Z",
         "local": "1944-04-29 2215 I", "words": "292215 / att. by torp", "lon": 118.7, "lat": 19.4,
         "cite": cite("metapth1", "intelligence")},
        {"origin": "japanese", "of": "jp", "actor": "30th Air Base", "kind": "weather", "utc": "1944-04-29T15:00Z",
         "local": "1944-04-30 0000 I", "cite": cite("jacar:C2 p26")},
    ],
    "pairs": [{"attack": "Attack 1", "boat": "bang", "utc": "1944-04-29T12:56Z", "relation": "hit",
               "record": {"utc": "1944-04-29T13:01Z", "lon": 118.83, "lat": 19.33}}],
}


@pytest.fixture
def engagement(tmp_path, monkeypatch):
    folder = tmp_path / "engagements" / "test-1944"
    folder.mkdir(parents=True)
    (folder / "engagement.json").write_text(json.dumps(ENGAGEMENT))
    monkeypatch.setenv("WWII_RECORDS", str(tmp_path))
    monkeypatch.setattr(geo, "land_rings", lambda box, scale="10m": [])
    return "test-1944"


def test_numbering_is_shared_and_in_time_order(engagement):
    _, m = figures.engagement_map(engagement)
    _, t = figures.engagement_timeline(engagement)
    assert [(k.n, k.kind) for k in m.marks] == [(k.n, k.kind) for k in t.marks] == [(1, "attack"), (2, "torpedoed"), (3, "hit")]
    assert m.marks[1].note == "the master's log"
    assert all(k.lane != "tama-17" or k.origin == "japanese" for k in m.marks)


def test_weather_and_contacts_are_not_numbered_but_cited(engagement):
    _, s = figures.engagement_timeline(engagement)
    assert "BANG, contacts: rg38-1/p13" in figures.grouped_cites(s)
    assert not any(k.kind == "weather" for k in s.marks)


def test_zones_named_from_the_records(engagement):
    _, s = figures.engagement_timeline(engagement)
    line = figures.zones_line(s)
    assert "BANG zone K (GMT+10)" in line and "zone I (GMT+9)" in line


def test_svg_is_well_formed_and_marks_the_followed_boat(engagement):
    svg, _ = figures.engagement_map(engagement, follow="parche")
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg")
    legs = [e for e in root.iter() if e.tag.endswith("line") and e.get("stroke") in figures.BOATS]
    # each boat in its own colour (BANG first, PARCHE second), never in the hits' red
    assert {e.get("stroke") for e in legs} == {figures.BOATS[0], figures.BOATS[1]}
    assert not any(e.get("stroke") == figures.OWN for e in root.iter() if e.tag.endswith("line"))
    heavy = [e for e in legs if e.get("stroke-width") == "1.4"]
    assert len(heavy) == 1 and heavy[0].get("stroke") == figures.BOATS[1]   # the followed boat, PARCHE, drawn heavier
    assert heavy[0].get("stroke-dasharray") == "3 2"   # and its one leg dashed: an end is assumed


def test_timeline_gives_the_minutes_between_clocks(engagement):
    svg, _ = figures.engagement_timeline(engagement)
    assert ">5 min<" in svg


def test_sun():
    rise, set_ = figures.sun(date(1944, 4, 29), 19.5, 119.2)
    assert (rise.hour, set_.hour) == (21, 10)    # 0536 and 1826 local (GMT+8): the night the attacks were made in


def test_a_closed_ring_survives_simplification():
    from wwiibook.cartography import simplify
    ring = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0), (0.0, 0.0)]
    assert len(simplify(ring, 0.5)) == 5


def test_labels_never_overlap():
    from wwiibook.cartography import Labels
    lab = Labels((0, 0, 200, 120))
    lab.line([(0, 60), (200, 60)])                      # a front across the middle
    for i in range(30):                                 # thirty places crowded into a small map
        x, y = 20 + (i * 37) % 160, 15 + (i * 23) % 90
        lab.occupy(x - 2, y - 2, 4, 4)
        lab.place(x, y, [(f"Place {i}", 7, "#000", "bold", "Barlow")], force=False)
    r = lab.placed
    assert len(r) > 10
    for i in range(len(r)):
        for j in range(i + 1, len(r)):
            a, b = r[i], r[j]
            assert a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1], (a, b)


def test_a_sheet_fit_reproduces_its_points(tmp_path, monkeypatch):
    from wwiibook import sitmap
    fronts = tmp_path / "fronts"
    fronts.mkdir()
    rows = ["town,x,y,read,lat,lon,source,query"]
    for lon in (-2.0, -1.5, -1.0, -0.5):
        for lat in (49.0, 49.5, 50.0):
            x, y = 1000 + (lon + 2) * 1700, 3000 - (lat - 49) * 2600      # a sheet drawn at a known scale
            rows.append(f"g,{x},{y},by eye,{lat},{lon},test,")
    (fronts / "12ag-1944-07-11-gcps.csv").write_text("\n".join(rows) + "\n")
    monkeypatch.setenv("WWII_RECORDS", str(tmp_path))
    fit = sitmap.Fit("1944-07-11")
    x, y = fit.px([-1.25], [49.25])
    assert abs(x[0] - (1000 + 0.75 * 1700)) < 0.01 and abs(y[0] - (3000 - 0.25 * 2600)) < 0.01
    assert fit.rms < 1e-6


def test_resampling_keeps_a_line_on_its_course():
    from wwiibook.atlas.reconstruct import _resample
    lon, lat, t = _resample([(-1.5, 49.3), (-1.5, 49.31)], 50)      # about 1,106 m due north
    assert abs(t[-1] - 1100) < 60 and len(lon) == len(t) and set(lon.round(6)) == {-1.5}
    assert (lat[1:] > lat[:-1]).all()


def test_a_halo_is_drawn_whole_under_its_lettering():
    from wwiibook.halo import split
    out = split('<svg><text x="1" y="2" fill="#000" stroke="#fff" stroke-width="2" paint-order="stroke">Lessay</text>'
                '<text x="3" y="4" fill="#000">plain</text></svg>')
    halo, letters, plain = out.split("</text>")[:3]
    assert 'fill="#fff"' in halo and 'stroke="#fff"' in halo and "paint-order" not in halo
    assert 'fill="#000"' in letters and "stroke" not in letters and letters.endswith("Lessay")
    assert plain.endswith('<text x="3" y="4" fill="#000">plain')
