"""A convoy's route beside its engagement, from a small engagement.json and lanes file, offline (no coastline download)."""
import json
import re
import xml.etree.ElementTree as ET

import pytest
import yaml
from wwiibook import convoy_route, geo

NS = "{http://www.w3.org/2000/svg}"

LANES = {"nodes": {
    "keelung": {"name": "Keelung", "lon": 121.74, "lat": 25.15, "port": True, "source": "hand-placed"},
    "w-etw": {"name": "east of Formosa", "lon": 122.55, "lat": 24.6, "assumed": "up the east coast"},
    "naha": {"name": "Naha", "lon": 127.68, "lat": 26.21, "port": True, "source": "hand-placed"},
    "moji": {"name": "Moji", "lon": 130.96, "lat": 33.95, "port": True, "source": "hand-placed"},
}}

ENGAGEMENT = {
    "box": [121.9, 23.4, 123.9, 24.8],
    "participants": [{"id": "bang", "name": "BANG", "of": "us", "kind": "submarine"},
                     {"id": "taka-206", "name": "Convoy TAKA-206", "of": "jp", "kind": "convoy"}],
    "places": [],
    "tracks": {"bang": [{"utc": "1944-11-22T14:00Z", "lon": 122.5, "lat": 24.0, "on_track": True},
                        {"utc": "1944-11-22T15:00Z", "lon": 122.7, "lat": 24.1, "on_track": True}]},
    "events": [{"origin": "track", "of": "us", "actor": "bang", "kind": "attack", "title": "Attack 1",
                "utc": "1944-11-22T15:32Z", "local": "1944-11-23 0032 K", "lon": 122.7, "lat": 24.1,
                "cite": {"ref": "rg38-1/p12", "kind": "record"}}],
    "convoys": {"taka-206": {"convoy": "TAKA-206", "route": ["keelung", "w-etw", "naha"],
                             "voyage": [{"at": "1944-11-22 0800 I", "place": "keelung", "event": "sailed",
                                         "source": "jacar:C1 p33", "basis": "reported"}]}},
}


@pytest.fixture
def engagement(tmp_path, monkeypatch):
    folder = tmp_path / "engagements" / "test-1944"
    folder.mkdir(parents=True)
    (folder / "engagement.json").write_text(json.dumps(ENGAGEMENT))
    lanes = tmp_path / "lanes.yml"
    lanes.write_text(yaml.safe_dump(LANES))
    monkeypatch.setenv("WWII_RECORDS", str(tmp_path))
    monkeypatch.setattr(convoy_route, "lanes_file", lambda: lanes)
    monkeypatch.setattr(geo, "land_rings", lambda box, scale="10m": [])
    return "test-1944"


def test_the_route_is_the_lanes_in_order(engagement):
    svg, notes = convoy_route.route_figure(engagement, 5.5)
    assert [r["id"] for r in notes["route"]] == ["keelung", "w-etw", "naha"]
    assert [(r["lon"], r["lat"]) for r in notes["route"]] == [(121.74, 25.15), (122.55, 24.6), (127.68, 26.21)]
    legs = [(e.get("data-from"), e.get("data-to")) for e in ET.fromstring(svg).iter(f"{NS}line")
            if "leg" in (e.get("class") or "").split()]
    assert legs == [("keelung", "w-etw"), ("w-etw", "naha")]
    assert "assumed: up the east coast" in notes["route_line"]
    assert notes["voyage"][0]["source"] == "jacar:C1 p33"


def test_assumed_waypoints_are_dotted_and_ports_dashed(engagement, monkeypatch):
    changed = json.loads(json.dumps(ENGAGEMENT))
    changed["convoys"]["taka-206"]["route"] = ["keelung", "w-etw", "naha", "moji"]
    path = convoy_route.paths.records() / "engagements" / engagement / "engagement.json"
    path.write_text(json.dumps(changed))
    svg, _ = convoy_route.route_figure(engagement, 5.5)
    legs = {(e.get("data-from"), e.get("data-to")): e for e in ET.fromstring(svg).iter(f"{NS}line")
            if "leg" in (e.get("class") or "").split()}
    for k in [("keelung", "w-etw"), ("w-etw", "naha")]:
        assert "assumed" in legs[k].get("class") and legs[k].get("stroke-dasharray") == convoy_route.DOTTED
    assert "assumed" not in legs[("naha", "moji")].get("class")
    assert legs[("naha", "moji")].get("stroke-dasharray") == convoy_route.DASHED


def test_the_box_is_the_engagements_and_the_map_is_nested(engagement):
    svg, notes = convoy_route.route_figure(engagement, 5.5)
    root = ET.fromstring(svg)
    assert notes["box"] == ENGAGEMENT["box"]
    zoom = [e for e in root.iter(f"{NS}svg") if e.get("class") == "zoom"]
    assert len(zoom) == 1
    # the nested map is drawn to the box exactly, so the overview's box and the map's frame are the same ground
    f = geo.fit(tuple(ENGAGEMENT["box"]), float(zoom[0].get("width")), pad=0.0)
    assert abs(f.height - float(zoom[0].get("height"))) < 0.2
    assert len([e for e in root.iter(f"{NS}rect") if e.get("class") == "engagement-box"]) == 1
    assert len([e for e in root.iter(f"{NS}line") if e.get("class") == "connector"]) == 2
    ids = re.findall(r'id="([^"]+)"', svg)
    assert len(ids) == len(set(ids))
    assert notes["marks"][0]["n"] == 1 and notes["marks"][0]["gmt"] == "22 Nov 1532Z"


def test_a_box_given_replaces_the_engagements(engagement):
    _, notes = convoy_route.route_figure(engagement, 5.5, box=[122.0, 23.5, 123.0, 24.5])
    assert notes["box"] == [122.0, 23.5, 123.0, 24.5]


def test_a_long_route_puts_the_overview_above(engagement):
    changed = json.loads(json.dumps(ENGAGEMENT))
    changed["convoys"]["taka-206"]["route"] = ["keelung", "w-etw", "naha", "moji"]
    (convoy_route.paths.records() / "engagements" / engagement / "engagement.json").write_text(json.dumps(changed))
    _, notes = convoy_route.route_figure(engagement, 5.5)
    assert notes["layout"] == "above"
    _, notes = convoy_route.route_figure(engagement, 5.5, layout="left")
    assert notes["layout"] == "left"


def test_no_routed_convoy_is_an_error(engagement):
    changed = {**ENGAGEMENT, "convoys": {}}
    (convoy_route.paths.records() / "engagements" / engagement / "engagement.json").write_text(json.dumps(changed))
    with pytest.raises(ValueError):
        convoy_route.route_figure(engagement, 5.5)


def test_the_route_alone_fits_a_column_and_marks_the_attack(engagement):
    svg, notes = convoy_route.route_figure(engagement, 3.3, zoom=False)
    root = ET.fromstring(svg)
    w, h = float((root.get("width") or "")[:-2]), float((root.get("height") or "")[:-2])
    assert w <= 3.3 * 72 + 0.1 and h <= convoy_route.MAX_H + 0.1
    assert notes["layout"] == "alone" and abs(notes["width"] * 72 - w) < 0.5
    assert not [e for e in root.iter(f"{NS}svg") if e.get("class") == "zoom"]      # no engagement map, no numbers
    assert notes["marks"] == []
    attacks = [e for e in root.iter(f"{NS}path") if e.get("class") == "attack"]
    assert len(attacks) == 1 and attacks[0].get("fill") == "#2a6fc9"
    assert notes["attacks"][0]["cite"] == "rg38-1/p12" and notes["attacks"][0]["gmt"] == "22 Nov 1532Z"
    ends = [e.text for e in root.iter(f"{NS}text") if e.get("class") == "end"]
    assert list(dict.fromkeys(ends)) == ["Keelung, origin", "Naha, destination"]     # (the halo layer repeats them)
    assert notes["origin"] == "Keelung" and notes["destination"] == "Naha"
    assert "north" in svg.lower() or "N</text>" in svg                                # the north arrow
    assert "nautical mile" in svg                                                    # the scale at sea


def test_the_route_alone_never_runs_taller_than_asked(engagement):
    changed = json.loads(json.dumps(ENGAGEMENT))
    changed["convoys"]["taka-206"]["route"] = ["keelung", "w-etw", "naha", "moji"]
    (convoy_route.paths.records() / "engagements" / engagement / "engagement.json").write_text(json.dumps(changed))
    for width, height in ((7.0, 3.0), (3.3, None), (7.0, None)):
        svg, _ = convoy_route.route_figure(engagement, width, height, zoom=False)
        root = ET.fromstring(svg)
        h = float((root.get("height") or "")[:-2])
        assert h <= (height * 72 if height else convoy_route.MAX_H) + 0.1
        assert float((root.get("width") or "")[:-2]) <= width * 72 + 0.1


def test_the_map_and_overview_are_held_to_the_page(engagement):
    changed = json.loads(json.dumps(ENGAGEMENT))
    changed["convoys"]["taka-206"]["route"] = ["keelung", "w-etw", "naha", "moji"]
    (convoy_route.paths.records() / "engagements" / engagement / "engagement.json").write_text(json.dumps(changed))
    svg, _ = convoy_route.route_figure(engagement, 7.0, layout="above")
    assert float((ET.fromstring(svg).get("height") or "")[:-2]) <= convoy_route.MAX_H + 0.5
