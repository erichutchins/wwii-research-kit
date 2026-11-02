# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""The tools' shared computation against cases worked by hand or read off the records: positions as typed, zone
letters to GMT, the three grids' decoders against their anchors, the land test. site/engage.test.js does the same for
the engagement pages' computation.

Usage: uv run tools/test_tools.py   (unittest; -v for each test's name)
"""
import contextlib
import io
import sys
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bezugspunkt
import build_seabees
import check_track
import jgrid
import lint
import naval_grid
import records


def quietly(fn, *a):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a)


class Positions(unittest.TestCase):
    def test_a_typed_position(self):
        # as the war patrol reports and diaries type them; worked by hand
        self.assertAlmostEqual(check_track.parse_coord("27-28S"), -(27 + 28 / 60))
        self.assertAlmostEqual(check_track.parse_coord("153-02E"), 153 + 2 / 60)
        self.assertAlmostEqual(check_track.parse_coord("123-10W"), -(123 + 10 / 60))
        self.assertAlmostEqual(check_track.parse_coord("26-56-15N"), 26 + 56 / 60 + 15 / 3600)
        self.assertAlmostEqual(check_track.parse_coord("26-42.5N"), 26 + 42.5 / 60)

    def test_an_illegible_or_blank_position_is_none(self):
        self.assertIsNone(check_track.parse_coord("26-4?N"))
        self.assertIsNone(check_track.parse_coord(""))

    def test_a_seabee_voyage_position(self):
        # voyage_positions.csv types degrees and minutes with their signs: 20ncb's LST log, 8 Jun 1943
        self.assertAlmostEqual(build_seabees.parse_coord("25° 57' S"), -(25 + 57 / 60))
        self.assertAlmostEqual(build_seabees.parse_coord("163° 37' E"), 163 + 37 / 60)


class Zones(unittest.TestCase):
    def test_zone_letters_to_gmt(self):
        # K is GMT+10 (SEAHORSE leaving Brisbane, 1400 K); T is GMT-7 (HAYNSWORTH off San Francisco, 0800 T);
        # I is GMT+9, the Imperial Navy's clock; Z is GMT
        self.assertEqual(check_track.to_utc("1944-06-03", "1400", "K"), datetime(1944, 6, 3, 4, 0))
        self.assertEqual(check_track.to_utc("1945-08-08", "0800", "T"), datetime(1945, 8, 8, 15, 0))
        self.assertEqual(check_track.to_utc("1944-11-15", "0419", "I"), datetime(1944, 11, 14, 19, 19))
        self.assertEqual(check_track.to_utc("1944-11-15", "0419", "Z"), datetime(1944, 11, 15, 4, 19))

    def test_the_half_hour_zones(self):
        self.assertEqual(check_track.to_utc("1944-07-01", "1200", "KL"), datetime(1944, 7, 1, 1, 30))


class Grids(unittest.TestCase):
    """Each grid's anchors (reference/*/anchors.csv) are positions a record states two ways: by the grid and by a
    named place, a bearing or a plot. The decoders must keep agreeing with them."""

    def test_the_kana_grid_puts_every_anchor_in_its_square(self):
        self.assertEqual(quietly(jgrid.check, jgrid.load_keys()), 0, "an anchor is more than 10 nm outside its square")

    def test_the_naval_grid_decodes_every_anchor_as_recorded(self):
        self.assertEqual(quietly(naval_grid.check, naval_grid.load_blocks()), 0,
                         "an anchor no longer decodes, or decodes off its recorded error")

    def test_the_reference_points_decode_as_recorded(self):
        import csv
        eds = {"4": "4", "Feb 1944": "feb1944", "Jan 1944": "jan1944"}
        with open(bezugspunkt.DATA / "anchors.csv", encoding="utf-8") as f:
            rows = [a for a in csv.DictReader(f) if a["expected_lat"] and a["error_km"] and a["edition"] in eds]
        self.assertTrue(rows)
        for a in rows:
            pos, note = bezugspunkt.decode(a["code"], eds[a["edition"]], True)
            self.assertIsNotNone(pos, f"{a['code']}: {note}")
            assert pos is not None
            self.assertAlmostEqual(pos[0], float(a["decoded_lat"]), places=3, msg=a["code"])
            self.assertAlmostEqual(pos[1], float(a["decoded_lon"]), places=3, msg=a["code"])


@unittest.skipUnless((records.CACHE / "lint/land-10m.json").exists(), "the land map isn't cached (tools/lint.py --select ACC)")
class Land(unittest.TestCase):
    def test_land_and_sea(self):
        rings = lint.land_rings()
        self.assertTrue(lint.on_land(rings, 2.35, 48.86))        # Paris
        self.assertTrue(lint.on_land(rings, -123.17, 38.67))     # HAYNSWORTH's typed noon position, 8 Aug 1945
        self.assertFalse(lint.on_land(rings, -123.5, 37.68))     # her 0800 position, off San Francisco
        self.assertFalse(lint.on_land(rings, 135.0, 30.0))       # south of Japan
        self.assertFalse(lint.on_land(rings, 18.0, 35.0))        # the Ionian Sea


if __name__ == "__main__":
    unittest.main()
