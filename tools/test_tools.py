# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
# Python 3.11, not the 3.9 most tools claim: lint.py reads lint.toml with tomllib (3.11+) and its Lint dataclass
# writes `set | None` at run time (3.10+), and the lint tests below import it.
"""The tools' shared computation against cases worked by hand or read off the records: positions as typed, zone
letters to GMT, the three grids' decoders against their anchors, the land test; the lint's rules and its allow list
against small files made here; the engagement builder's times, bearings and vocabularies. site/engage.test.js does the
same for the engagement pages' computation.

The fixtures are written to a temporary folder, never read from records/ (which changes): a lint test gets a fresh
git repository with the files it names, an engagement test a folder with an engagement.md and its events.yml.

Usage: uv run tools/test_tools.py   (unittest; -v for each test's name)
"""
import contextlib
import io
import subprocess
import sys
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bezugspunkt
import build_engagement
import build_seabees
import check_sources
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


# ── the lint, on files made here ─────────────────────────────────────────────

class LintCase(unittest.TestCase):
    """A fresh git repository (Lint.files lists a repository's files with git) holding the files a test names, and
    the findings one rule yields on it as (path relative to the root, line, message, target)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name).resolve()
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)

    def tearDown(self):
        self._tmp.cleanup()

    def kit(self, files, **kw):
        """files: {relative path: text or bytes}; kw: more Lint fields (extra_ids, config)"""
        for name, body in files.items():
            p = self.root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(body if isinstance(body, bytes) else body.encode("utf-8"))
        return lint.Lint(self.root, [self.root], config_path=self.root / "lint.toml", **kw)

    def findings(self, L, code):
        return [(L.rel(p), line, msg, target) for p, line, msg, target in lint.RULES[code][2](L)]

    def flagged(self, L, code):
        """(path, line) of each finding"""
        return [(p, line) for p, line, _, _ in self.findings(L, code)]


class LintFiles(LintCase):
    def test_fmt001_a_byte_order_mark_or_bytes_that_are_not_utf8(self):
        L = self.kit({"bom.csv": b"\xef\xbb\xbfa,b\n1,2\n", "latin.yml": b"name: Noum\xe9a\n", "ok.csv": "a,b\n1,2\n"})
        found = self.findings(L, "FMT001")
        self.assertEqual([(p, n, m) for p, n, m, _ in found],
                         [("bom.csv", 1, "starts with a byte-order mark"), ("latin.yml", 1, "is not UTF-8")])

    def test_fmt001_names_the_line_of_the_bad_byte(self):
        L = self.kit({"latin.txt": b"fine\nfine\nNoum\xe9a\n"})
        self.assertEqual(self.flagged(L, "FMT001"), [("latin.txt", 3)])

    def test_fmt002_crlf_at_its_first_line(self):
        L = self.kit({"crlf.csv": b"a,b\n1,2\r\n3,4\r\n", "lf.csv": b"a,b\n1,2\n"})
        self.assertEqual(self.flagged(L, "FMT002"), [("crlf.csv", 2)])

    def test_fmt003_no_newline_at_the_end(self):
        # generated JSON is exempt (json.dump writes none); an empty file passes
        L = self.kit({"cut.csv": "a,b\n1,2", "ok.csv": "a,b\n1,2\n", "empty.md": "", "x.json": "{}", "y.geojson": "{}"})
        self.assertEqual(self.flagged(L, "FMT003"), [("cut.csv", 2)])

    def test_fmt004_a_tab_in_yaml_indentation(self):
        L = self.kit({"tab.yml": "a:\n\tb: 1\n  \tc: 2\n", "spaces.yml": "a:\n  b: 1\n", "data.csv": "a\n\tx\n"})
        self.assertEqual(self.flagged(L, "FMT004"), [("tab.yml", 2), ("tab.yml", 3)])


class LintCsv(LintCase):
    def test_csv001_a_repeated_empty_or_padded_column_name(self):
        L = self.kit({"twice.csv": "date,ref,date\n1944-05-03,a,1944-05-04\n", "blank.csv": "a,,b\n1,2,3\n",
                      "padded.csv": "a, b\n1,2\n", "ok.csv": "a,b\n1,2\n"})
        found = self.findings(L, "CSV001")
        self.assertEqual(found, [("blank.csv", 1, "has an empty or padded column name", ""),
                                 ("padded.csv", 1, "has an empty or padded column name", ""),
                                 ("twice.csv", 1, "column 'date' appears 2 times", "")])

    def test_csv002_a_row_not_as_wide_as_the_header(self):
        # an unquoted comma makes a cell too many (line 3); a lost cell one too few (line 4); a blank line is skipped
        L = self.kit({"w.csv": "a,b,c\n1,2,3\n1,2,x,y\n1,2\n\n4,5,6\n"})
        self.assertEqual(self.findings(L, "CSV002"),
                         [("w.csv", 3, "has 4 cells, the header 3", ""), ("w.csv", 4, "has 2 cells, the header 3", "")])

    def test_csv003_a_cell_padded_with_spaces(self):
        L = self.kit({"p.csv": "unit,place\n62ca-c,Nouméa \n62ca-c, Nouméa\n62ca-c,Nouméa\n"})
        self.assertEqual(self.findings(L, "CSV003"),
                         [("p.csv", 2, "place 'Nouméa ' has spaces at its ends", ""),
                          ("p.csv", 3, "place ' Nouméa' has spaces at its ends", "")])

    def test_csv004_a_date_column_holds_iso_dates(self):
        # a day, a month, a year, and `..` for an end left open (relations.csv) pass; typed dates don't. A column is
        # checked when most of its values are dates (is_date_column), so the fixture's are: 3 of 5 and 2 of 3
        L = self.kit({"d.csv": "date,from,to,ref\n1944-05-03,1944-05,1944,a\n3 May 1944,..1944-05-03,1944-05-03..,b\n"
                               "1944-5-3,05/03/1944,,c\n1944-05-04,,,d\n1944-05-05,,,e\n"})
        self.assertEqual(self.findings(L, "CSV004"),
                         [("d.csv", 3, "date '3 May 1944' isn't an ISO date", ""),
                          ("d.csv", 4, "date '1944-5-3' isn't an ISO date", ""),
                          ("d.csv", 4, "from '05/03/1944' isn't an ISO date", "")])

    def test_csv004_a_column_of_mostly_typed_dates_is_not_a_date_column(self):
        # by design: a `date` column whose values are mostly something else (a position id, a season) isn't checked
        L = self.kit({"d.csv": "date,ref\n1944-05-03,a\n3 May 1944,b\nspring 1944,c\n"})
        self.assertEqual(self.findings(L, "CSV004"), [])

    def test_csv004_leaves_a_from_column_of_ids_alone(self):
        # an engagement's positions.csv `from` is the position a bearing is taken from, not a date
        L = self.kit({"positions.csv": "id,from,brg,nm\nalgiers,,,\nbattery-c,algiers,270,3.48\nharbour,algiers,80,1\n"})
        self.assertEqual(self.findings(L, "CSV004"), [])
        self.assertTrue(lint.is_date_column(["1944-05-03", "", "1944-05"]))
        self.assertFalse(lint.is_date_column(["algiers", "1944-05-03", "harbour"]))


class LintYaml(LintCase):
    def test_yml001_a_key_given_twice(self):
        # PyYAML keeps the second `name` silently; the pages' js-yaml rejects the file: records.load_yaml refuses it
        L = self.kit({"twice.yml": "- id: a\n  name: one\n  name: two\n", "ok.yml": "- id: a\n  name: one\n"})
        found = self.findings(L, "YML001")
        self.assertEqual(self.flagged(L, "YML001"), [("twice.yml", 3)])
        self.assertIn("duplicate key 'name'", found[0][2])

    def test_yml001_yaml_that_does_not_parse(self):
        L = self.kit({"bad.yml": "a: [1, 2\n"})
        self.assertEqual(len(self.flagged(L, "YML001")), 1)
        self.assertTrue(self.findings(L, "YML001")[0][2].startswith("doesn't load:"))

    def test_yml001_reads_a_markdown_files_front_matter(self):
        L = self.kit({"e.md": "---\ntitle: One\ntitle: Two\n---\n\nThe story.\n", "plain.md": "# No front matter\n",
                      "ok.md": "---\ntitle: One\n---\n\nThe story.\n"})
        found = self.findings(L, "YML001")
        self.assertEqual([(p, n) for p, n, _, _ in found], [("e.md", 3)])
        self.assertTrue(found[0][2].startswith("front matter doesn't load:"))

    def test_yml002_an_unquoted_comma_that_split_a_value(self):
        # `{ name: AA action forms, 6 April 1945 }` reads as a key "6 April 1945" with no value
        L = self.kit({"split.yml": "- { n: 1, name: AA action forms, 6 April 1945, area: Okinawa }\n",
                      "ok.yml": "- { n: 1, name: 'AA action forms, 6 April 1945', area: Okinawa }\n  \nplain:\n"})
        self.assertEqual(self.findings(L, "YML002"),
                         [("split.yml", 1, "key '6 April 1945' has no value: quote the value it was split from", "")])


class LintReferences(LintCase):
    def test_ref002_a_deep_link_to_an_id_that_does_not_exist(self):
        # the ids are supplied through extra_ids, as the family repository does; the kit's own indexes aren't read
        L = self.kit({"guide.md": "See [the raid](site/engagement.html?e=algiers-1943) and "
                                  "[another](site/engagement.html?e=oran-1942).\n",
                      "site/page.js": "location.href = 'engagement.html?e=algiers%201943';\n"},
                     extra_ids={r"engagement\.html\?e=": ({"algiers-1943", "algiers 1943"}, "engagement")})
        with mock.patch.object(records, "RECORDS", self.root):   # no generated indexes here: only extra_ids apply
            found = self.findings(L, "REF002")
        self.assertEqual(found, [("guide.md", 1, "links to the engagement 'oran-1942', which doesn't exist", "oran-1942")])

    def test_ref002_decodes_an_encoded_id_and_drops_a_sentences_full_stop(self):
        L = self.kit({"n.md": "convoys.html?c=take-1.\nconvoys.html?c=a%20b convoys.html?c=a+b convoys.html?c=nope.\n"},
                     extra_ids={r"convoys\.html\?c=": ({"take-1", "a b"}, "convoy")})
        with mock.patch.object(records, "RECORDS", self.root):
            found = self.findings(L, "REF002")
        self.assertEqual([(p, n, t) for p, n, _, t in found], [("n.md", 2, "nope")])


class LintOrphans(LintCase):
    def test_orf003_a_place_no_row_uses(self):
        # the gazetteer is read from records.RECORDS/army: pointed at the fixture for the test
        L = self.kit({"army/places.csv": "place,lat,lon\nAlgiers,36.77,3.06\nOran,35.70,-0.64\nSavelborn,49.76,6.26\n",
                      "army/stations.csv": "unit,date,place,page\n62ca-c,1943-04-30,Algiers,p1\n",
                      "army/60aib/report.md": "---\nunit: 60aib\nstation: Savelborn\n---\n"})
        with mock.patch.object(records, "RECORDS", self.root):
            found = self.findings(L, "ORF003")
        self.assertEqual(found, [("army/places.csv", 3, "place 'Oran' is used by no row", "Oran")])


class LintRunner(LintCase):
    """run(): the allow list matches a finding by its target, by `file:target` or by its file; an allow that matches
    nothing is itself reported (LNT001); --select and --ignore pick rules by code or prefix."""

    FILES = {"p.csv": "unit,place\n62ca-c,Nouméa \n", "army/places.csv": "place\nOran\n"}

    def test_an_allow_by_file_and_target_hides_the_finding(self):
        L = self.kit(self.FILES, config={"allow": [{"code": "CSV003", "target": "p.csv:", "why": "a test"}]})
        self.assertEqual([f.code for f in quietly(lint.run, L, ["CSV"], [])], [])   # CSV003's target is "" here
        L = self.kit(self.FILES, config={"allow": [{"code": "CSV003", "target": "p.csv", "why": "by file"}]})
        self.assertEqual([f.code for f in quietly(lint.run, L, ["CSV"], [])], [])

    def test_an_allow_that_matches_nothing_is_reported(self):
        L = self.kit(self.FILES, config={"allow": [{"code": "CSV001", "target": "nowhere.csv", "why": "stale"}]})
        found = quietly(lint.run, L, ["CSV"], [])
        self.assertEqual([(f.code, f.path) for f in found], [("LNT001", "lint.toml"), ("CSV003", "p.csv")])   # sorted by path
        self.assertIn("allow CSV001 'nowhere.csv' matches nothing", found[0].message)

    def test_an_allow_for_a_rule_not_selected_is_not_reported(self):
        L = self.kit(self.FILES, config={"allow": [{"code": "CSV001", "target": "nowhere.csv", "why": "stale"}]})
        self.assertEqual([f.code for f in quietly(lint.run, L, ["FMT"], [])], [])

    def test_select_and_ignore_pick_by_code_or_prefix(self):
        self.assertTrue(lint.selected("CSV003", ["CSV"], []))
        self.assertTrue(lint.selected("CSV003", ["CSV003"], []))
        self.assertFalse(lint.selected("CSV003", ["FMT", "YML"], []))
        self.assertFalse(lint.selected("CSV003", ["CSV"], ["CSV003"]))
        self.assertFalse(lint.selected("CSV003", ["CSV"], ["CSV"]))

    def test_main_takes_select_and_the_paths_a_commit_hook_passes(self):
        files = {**self.FILES, "q.csv": "unit,place\n62ca-c, Oran\n", "lint.toml": 'select = ["CSV"]\n'}
        L = self.kit(files)
        self.assertEqual(quietly(lint.main, L, [str(self.root / "q.csv")]), 1)
        self.assertEqual(L.only, {"q.csv"})
        self.assertEqual([L.rel(p) for p in L.per_file(".csv")], ["q.csv"])   # the per-file rules see only that one
        self.assertEqual(quietly(lint.main, L, ["--select", "FMT", str(self.root / "q.csv")]), 0)
        self.assertEqual(quietly(lint.main, L, ["--select", "CSV", "--ignore", "CSV003", str(self.root / "q.csv")]), 0)


# ── the engagement builder ───────────────────────────────────────────────────

class EngagementTimes(unittest.TestCase):
    """Build.when: an entry's `at` as typed -> (the local time as written, GMT or None, a sort key)."""

    def setUp(self):
        self.b = build_engagement.Build()

    def test_a_date_alone(self):
        self.assertEqual(self.b.when("1944-05-03", "H", "w"), ("1944-05-03", None, "1944-05-03"))
        self.assertEqual(self.b.when("1944-05", "H", "w"), ("1944-05", None, "1944-05"))   # a monthly table
        self.assertEqual(self.b.when(date(1944, 5, 3), "H", "w"), ("1944-05-03", None, "1944-05-03"))   # YAML's own date
        self.assertEqual(self.b.problems, [])

    def test_a_time_with_its_zone_letter(self):
        # 0603 H (GMT+8) on 3 May is 2203 GMT the day before; the key is the GMT time, so sides on different clocks sort together
        self.assertEqual(self.b.when("1944-05-03 0603 H", "", "w"),
                         ("1944-05-03 0603 H", datetime(1944, 5, 2, 22, 3), "1944-05-02T22:03Z"))
        self.assertEqual(self.b.when("1945-04-06 1245 Z", "I", "w")[1], datetime(1945, 4, 6, 12, 45))
        self.assertEqual(self.b.problems, [])

    def test_a_time_without_a_zone_takes_the_engagements_clock(self):
        # the engagement's `clock` is I (GMT+9): 0419 I on 15 Nov is 1919 GMT on the 14th; the local time stays as typed
        self.assertEqual(self.b.when("1944-11-15 0419", "I", "w"),
                         ("1944-11-15 0419", datetime(1944, 11, 14, 19, 19), "1944-11-14T19:19Z"))
        self.assertEqual(self.b.problems, [])

    def test_a_time_with_no_zone_and_no_clock_stays_off_gmt(self):
        self.assertEqual(self.b.when("1944-11-15 0419", "", "w"), ("1944-11-15 0419", None, "1944-11-15T04:19"))
        self.assertEqual(self.b.problems, [])

    def test_an_unknown_zone_is_reported(self):
        # J is left out of the zone letters; the entry keeps its local time and sorts by it
        self.assertEqual(self.b.when("1944-05-03 0603 J", "", "w"), ("1944-05-03 0603 J", None, "1944-05-03T06:03"))
        self.assertEqual(self.b.problems, ["w: zone 'J' is not a zone letter (check_track.ZONES)"])
        self.b.when("1944-05-03 0603", "J", "w2")   # as the engagement's clock too
        self.assertEqual(self.b.problems[1], "w2: zone 'J' is not a zone letter (check_track.ZONES)")

    def test_a_time_not_in_the_form_is_reported(self):
        for bad in ("3 May 1944", "1944-05-03T06:03", "1944-05-03 603 H", ""):
            self.assertEqual(self.b.when(bad, "H", "w")[1], None)
        self.assertEqual(len(self.b.problems), 4)
        self.assertIn("`at` '3 May 1944' is not 'YYYY-MM-DD HHMM Z'", self.b.problems[0])


class EngagementPlaces(unittest.TestCase):
    """Build.place: a positions.csv row with no lat/lon but `from`, `brg` and `nm` is put at that bearing and
    distance from the row it names (a nautical mile is a minute of latitude; of longitude, a minute over cos(lat))."""

    def setUp(self):
        self.b = build_engagement.Build()

    def rows(self, *rs):
        return {r["id"]: {**{"lat": None, "lon": None}, **r} for r in rs}

    def test_bearing_and_distance_worked_by_hand(self):
        ps = self.rows({"id": "o", "label": "the city", "lat": 0.0, "lon": 0.0},
                       {"id": "n", "from": "o", "brg": "0", "nm": "30"},       # 30 nm north: half a degree of latitude
                       {"id": "e", "from": "o", "brg": "90", "nm": "60"},      # 60 nm east on the equator: one degree
                       {"id": "ne", "from": "o", "brg": "45", "nm": "60"})     # 60 cos 45° = 42.43 nm each way
        for r in ps.values():
            self.b.place(r, ps, r["id"])
        self.assertEqual((ps["n"]["lat"], ps["n"]["lon"]), (0.5, 0.0))
        self.assertEqual((ps["e"]["lat"], ps["e"]["lon"]), (0.0, 1.0))
        self.assertEqual((ps["ne"]["lat"], ps["ne"]["lon"]), (0.70711, 0.70711))
        self.assertEqual(ps["e"]["resolved"], "90° 60 nm from the city")
        self.assertEqual(self.b.problems, [])

    def test_a_degree_of_longitude_shrinks_with_latitude(self):
        # at 60° N a minute of longitude is half a nautical mile: 30 nm east is a whole degree
        ps = self.rows({"id": "o", "lat": 60.0, "lon": 10.0}, {"id": "e", "from": "o", "brg": "90", "nm": "30"})
        self.b.place(ps["e"], ps, "e")
        self.assertEqual((ps["e"]["lat"], ps["e"]["lon"]), (60.0, 11.0))

    def test_the_batterys_case(self):
        # Battery C, 62nd CA (AA): "4 mi West of Algiers" = 3.48 nm on 270° from the city's centre (36.7729, 3.0588);
        # by hand: 3.48 / (60 cos 36.77°) = 3.48 / 48.07 = 0.0724° of longitude west, the latitude unchanged
        ps = self.rows({"id": "algiers", "lat": 36.7729, "lon": 3.0588}, {"id": "battery-c", "from": "algiers", "brg": "270", "nm": "3.48"})
        self.b.place(ps["battery-c"], ps, "battery-c")
        self.assertAlmostEqual(ps["battery-c"]["lat"], 36.7729, places=4)
        self.assertAlmostEqual(ps["battery-c"]["lon"], 3.0588 - 0.0724, places=4)
        self.assertEqual(ps["battery-c"]["resolved"], "270° 3.48 nm from algiers")   # no label: the id

    def test_a_bearing_from_a_row_that_is_itself_placed_by_bearing(self):
        ps = self.rows({"id": "o", "lat": 0.0, "lon": 0.0}, {"id": "a", "from": "o", "brg": "0", "nm": "30"},
                       {"id": "b", "from": "a", "brg": "90", "nm": "60"})
        self.b.place(ps["b"], ps, "b")   # resolves `a` on the way
        self.assertEqual((ps["a"]["lat"], ps["a"]["lon"]), (0.5, 0.0))
        self.assertAlmostEqual(ps["b"]["lat"], 0.5)
        self.assertAlmostEqual(ps["b"]["lon"], 1 / 0.9999619, places=5)   # cos 0.5° = 0.9999619

    def test_a_from_that_names_no_position_is_reported(self):
        ps = self.rows({"id": "b", "from": "nowhere", "brg": "90", "nm": "1"})
        self.b.place(ps["b"], ps, "positions.csv b")
        self.assertIsNone(ps["b"]["lat"])
        self.assertEqual(self.b.problems, ["positions.csv b: `from` 'nowhere' is not a position here"])

    def test_a_row_with_its_own_position_is_left_alone(self):
        ps = self.rows({"id": "o", "lat": 1.0, "lon": 2.0, "from": "x", "brg": "90", "nm": "1"})
        self.b.place(ps["o"], ps, "o")
        self.assertEqual((ps["o"]["lat"], ps["o"]["lon"]), (1.0, 2.0))
        self.assertEqual(self.b.problems, [])


class EngagementVocabulary(unittest.TestCase):
    """Build.engagement on a folder made here: a `kind` or `basis` outside the vocabularies (KINDS, BASIS) is reported,
    an `of` that isn't a two-letter nationality, an entry with neither `words` nor `original`, and a [[link]] in the
    story that resolves to nothing. Only those problems are asserted: the fixture's citations aren't in SOURCES.yml and
    are reported too."""

    ENGAGEMENT = ("---\ntitle: A test\nshort: test\nclock: H\n"
                  "participants:\n"
                  "  - {id: boat, name: A boat, of: us, kind: submarine, basis: reported}\n"
                  "  - {id: ghost, name: A ghost, of: martian, kind: ship, basis: guessed}\n"
                  "---\n\n"
                  "The story links [[page:index]], [[page:nowhere]] and [[frob:x]]; an example in `[[page:nowhere2]]`.\n")
    EVENTS = ("- {at: 1944-05-03 0603, actor: boat, kind: attack, words: fired, source: s, ref: r}\n"
              "- {at: 1944-05-03 0604, of: martian, actor: ghost, kind: teleport, basis: guessed, words: gone, source: s, ref: r}\n")

    def build(self, engagement=ENGAGEMENT, events=EVENTS):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "test-1944"
            d.mkdir()
            (d / "engagement.md").write_text(engagement, encoding="utf-8")
            (d / "events.yml").write_text(events, encoding="utf-8")
            b = build_engagement.Build()
            out = b.engagement(d, {})
        return b.problems, out

    def test_an_unknown_kind_nationality_or_basis_is_reported(self):
        problems, out = self.build()
        said = "\n".join(problems)
        self.assertIn("participant ghost: of 'martian' is not a two-letter code (us, jp, de, it, uk, fr, ...)", said)
        self.assertIn("participant ghost: basis 'guessed' is not one of assumed, derived, inferred, reported, secondary", said)
        self.assertIn("#2 (1944-05-03 0604): kind 'teleport' is not in the vocabulary (KINDS)", said)
        self.assertIn("#2 (1944-05-03 0604): of 'martian' is not a two-letter code", said)
        self.assertIn("#2 (1944-05-03 0604): basis 'guessed' is not one of", said)
        # the entry in the vocabulary draws no such problem, takes its actor's nationality and the engagement's clock (H, GMT+8)
        self.assertNotIn("#1 (1944-05-03 0603): kind", said)
        self.assertNotIn("#1 (1944-05-03 0603): of", said)
        self.assertEqual(out["events"][0]["of"], "us")
        self.assertEqual(out["events"][0]["utc"], "1944-05-02T22:03Z")
        self.assertEqual(out["events"][0]["local"], "1944-05-03 0603")

    def test_a_participant_needs_a_nationality_and_an_entry_takes_its_actors(self):
        eng = ("---\ntitle: A test\nshort: test\nclock: H\nparticipants:\n"
               "  - {id: boat, name: A boat, kind: submarine}\n---\n\nWords.\n")
        problems, _ = self.build(engagement=eng, events="- {at: 1944-05-03 0603, actor: Someone, kind: log, words: w, source: s, ref: r}\n")
        said = "\n".join(problems)
        self.assertIn("participant boat: no `of` (a nationality as the record gives it: us, jp, de, it, uk, fr, ...)", said)
        self.assertIn("#1 (1944-05-03 0603): no `of` (the actor's nationality), and actor 'Someone' is not a participant to take it from", said)

    def test_the_other_side_is_derived_from_the_followed_subjects(self):
        # Venafro's shape: a followed US battery (a unit), a German report by its actor's nationality; nothing stores a side
        eng = ("---\ntitle: A test\nshort: test\nparticipants:\n"
               "  - {id: btry, name: Battery E, of: us, kind: army, unit: 67ca-e}\n"
               "  - {id: convoy, name: A convoy, of: jp, kind: convoy}\n---\n\nWords.\n")
        events = ("- {at: 1944-02-14, of: de, actor: 5. Geb.Div., kind: report, words: w, source: s, ref: r}\n"
                  "- {at: 1944-02-14, actor: btry, kind: station, words: w, source: s, ref: r}\n"
                  "- {at: 1944-02-15, of: uk, actor: 153 Sqn, kind: patrol, words: w, source: s, ref: r}\n")
        _, out = self.build(engagement=eng, events=events)
        self.assertEqual(out["own"], ["us"])
        self.assertIsNone(out["against"])
        btry, convoy = out["participants"]
        self.assertEqual((btry["followed"], btry["opposed"]), (True, False))
        self.assertEqual((convoy["followed"], convoy["opposed"]), (False, True))   # a convoy is the other side's record, not followed
        self.assertEqual([(e["of"], e["opposed"]) for e in out["events"]], [("de", True), ("us", False), ("uk", True)])
        # `against` names whom the subjects faced when more than two nationalities meet: the RAF is then on the battery's side
        _, out = self.build(engagement=eng.replace("participants:", "against: [de]\nparticipants:"), events=events)
        self.assertEqual(out["against"], ["de"])
        self.assertEqual([(e["of"], e["opposed"]) for e in out["events"]], [("de", True), ("us", False), ("uk", False)])
        problems, _ = self.build(engagement=eng.replace("participants:", "against: axis\nparticipants:"), events=events)
        self.assertIn("`against` is a list of nationalities, as the records name the other side ([de, it])", "\n".join(problems))

    def test_a_record_in_its_own_language(self):
        # the record's words in `original` with `lang` and our `translation` instead of `words`; one or the other, never neither
        good = "- {at: 1944-02-14, of: de, actor: 5. Geb.Div., kind: report, original: Eigene Artl., lang: de, translation: Own artillery, source: s, ref: r}\n"
        problems, out = self.build(events=good)
        self.assertNotIn("#1 (1944-02-14): `original`", "\n".join(problems))
        self.assertNotIn("#1 (1944-02-14): no `", "\n".join(problems))
        self.assertEqual((out["events"][0]["original"], out["events"][0]["lang"], out["events"][0]["translation"]), ("Eigene Artl.", "de", "Own artillery"))
        self.assertNotIn("words", out["events"][0])
        bad = ("- {at: 1944-02-14, of: de, actor: x, kind: report, original: Eigene Artl., source: s, ref: r}\n"
               "- {at: 1944-02-15, of: de, actor: x, kind: report, original: Eigene Artl., translation: t, lang: german, source: s, ref: r}\n"
               "- {at: 1944-02-16, of: de, actor: x, kind: report, words: w, translation: t, source: s, ref: r}\n"
               "- {at: 1944-02-17, of: de, actor: x, kind: report, source: s, ref: r}\n")
        said = "\n".join(self.build(events=bad)[0])
        self.assertIn("#1 (1944-02-14): `original` (the record's own words) needs our `translation` beside it", said)
        self.assertIn("#1 (1944-02-14): no `lang`", said)
        self.assertIn("#2 (1944-02-15): lang 'german' is not a two-letter code", said)
        self.assertIn("#3 (1944-02-16): `translation` and `lang` go with `original`", said)
        self.assertIn("#4 (1944-02-17): no `words` and no `original`", said)

    def test_a_citation_carries_its_sources_kind_and_nationality(self):
        # a morning report's page resolves to the National Archives' catalog, a record of the US; a Gallica issue to the French press
        events = ("- {at: 1943-05-13, of: us, actor: Battery C, kind: fire, words: w, source: s, ref: rg64-427182819/p0519}\n"
                  "- {at: 1943-05-13, of: fr, actor: L'Écho d'Alger, kind: report, words: w, source: s, ref: 'gallica:bpt6k75870445'}\n")
        _, out = self.build(events=events)
        self.assertEqual([(e["source_kind"], e["source_of"]) for e in out["events"]], [("record", "us"), ("press", "fr")])

    def test_a_link_in_the_story_must_resolve(self):
        problems, _ = self.build()
        said = "\n".join(problems)
        self.assertIn("[[page:nowhere]]: no such page", said)
        self.assertIn("[[frob:x]]: unknown kind (cite, op, ship, unit, page, convoy, engagement, who)", said)
        self.assertNotIn("nowhere2", said)         # an example in backticks isn't a link
        self.assertNotIn("[[page:index]]", said)   # site/index.html is there

    def test_an_unknown_field_and_a_missing_title(self):
        problems, _ = self.build(engagement="---\nshort: x\ncolour: red\nparticipants: []\n---\n\nWords.\n", events="")
        said = "\n".join(problems)
        self.assertIn("`title` is missing", said)
        self.assertIn("unknown field 'colour' (known: against, clock, eyebrow, participants, places, short, theater, title, window)", said)

    def test_the_vocabularies_hold_the_words_the_guides_name(self):
        self.assertFalse(hasattr(build_engagement, "SIDES"))   # retired: a nationality as the record gives it, never a bloc
        self.assertEqual(build_engagement.BASIS, {"reported", "derived", "inferred", "assumed", "secondary"})
        self.assertTrue({"position", "sighting", "attack", "hit", "sank", "station"} <= build_engagement.KINDS)


class SourceKinds(unittest.TestCase):
    """check_sources.check_kinds: every SOURCES.yml entry says what kind of source it is, from the one vocabulary
    (records.SOURCE_KINDS); `of`, when given, is a two-letter nationality. Against entries made here, and the real file
    only for "every entry has a kind in the vocabulary"."""

    def test_the_vocabulary(self):
        self.assertEqual(records.SOURCE_KINDS, {"record", "intelligence", "press", "assessment", "recollection", "secondary", "reference", "derived"})

    def test_a_source_without_a_kind_fails(self):
        said = check_sources.check_kinds({"gallica": {"title": "Gallica", "of": "fr"}})
        self.assertEqual(said, ["SOURCES.yml: gallica has no `kind` (one of assessment, derived, intelligence, press, recollection, record, reference, secondary)"])

    def test_a_kind_outside_the_vocabulary_fails(self):
        said = check_sources.check_kinds({"skl-ktb": {"title": "War Diary", "kind": "axis", "of": "de"}})
        self.assertEqual(said, ["SOURCES.yml: skl-ktb has kind 'axis', not one of assessment, derived, intelligence, press, recollection, record, reference, secondary"])

    def test_of_is_optional_but_a_two_letter_code(self):
        self.assertEqual(check_sources.check_kinds({"etopo1": {"title": "ETOPO1", "kind": "reference"}}), [])
        self.assertEqual(check_sources.check_kinds({"jacar": {"title": "JACAR", "kind": "record", "of": "jp"}}), [])
        self.assertEqual(check_sources.check_kinds({"x": {"title": "x", "kind": "record", "of": "Japan"}}),
                         ["SOURCES.yml: x has of 'Japan'; a nationality is a two-letter code (us, jp, de, it, uk, fr, ...)"])

    def test_every_real_entry_has_a_kind_in_the_vocabulary(self):
        self.assertEqual(check_sources.check_kinds(records.load_yaml(records.RECORDS / "SOURCES.yml")), [])


class EngagementPairs(unittest.TestCase):
    """Build.pair: a pairing from a patrol's claims.yml (as Build.patrol reads it, with the Japanese record beside it) ->
    the engagement's `pairs` entry for the Sources view: the attack, the boat, the record as written, and how they
    go together. The page computes the minutes and miles between the two; the build stores none."""

    def pairing(self, **ja):
        record = {"id": "J03", "source": "jacar:C08050103200", "page": "p23", "ship": "Takegawa Maru", "convoy": "TAMA-17",
                  "event": "torpedoed", "date": "1944-04-29", "time": "2201", "zone": "I", "lat_raw": "19-20N", "lon_raw": "118-50E",
                  "original": "二九日二二時〇一分…竹川丸敵潜水艦ノ魚雷攻撃ヲ受ケ", "translation": "At 2201 on the 29th … torpedoed",
                  "note": "Nittatsu Maru's own movement log", "local": "1944-04-29 2201 I", "utc": datetime(1944, 4, 29, 13, 1),
                  "lat": 19 + 20 / 60, "lon": 118 + 50 / 60, "cite": {"ref": "jacar:C08050103200 p23", "href": "h", "label": "p. 23"}}
        record.update(ja)
        return {"attack": "Attack 1", "record": "J03", "relation": "hit", "note": "Takegawa Maru (1,930 GRT), TAMA-17",
                "unit": "ss-385-bang/1", "attack_ref": "Attack 1", "attack_utc": datetime(1944, 4, 29, 12, 56), "ja": record}

    def test_bangs_attack_1_and_takegawa_marus_torpedoing(self):
        out = build_engagement.Build.pair(self.pairing(), {"ss-385-bang/1": "bang"})
        self.assertEqual({k: v for k, v in out.items() if k != "record"},
                         {"attack": "Attack 1", "boat": "bang", "utc": "1944-04-29T12:56Z", "relation": "hit", "note": "Takegawa Maru (1,930 GRT), TAMA-17"})
        r = out["record"]
        self.assertEqual((r["id"], r["event"], r["ship"], r["date"], r["time"], r["zone"]), ("J03", "torpedoed", "Takegawa Maru", "1944-04-29", "2201", "I"))
        self.assertEqual((r["local"], r["utc"]), ("1944-04-29 2201 I", "1944-04-29T13:01Z"))   # 2201 I is 1301 GMT, five minutes after the attack
        self.assertEqual((r["lat"], r["lon"], r["lat_raw"], r["lon_raw"]), (19.3333, 118.8333, "19-20N", "118-50E"))
        self.assertEqual((r["lang"], r["original"][:5], r["translation"][:7]), ("ja", "二九日二二", "At 2201"))
        self.assertEqual(r["cite"]["ref"], "jacar:C08050103200 p23")
        self.assertNotIn("minutes", out)   # the arithmetic is the page's (Engage.apart), never stored

    def test_a_loss_list_has_no_time_and_no_position(self):
        # J10, the April loss table: dated to a month, no time, no position; the record keeps its month and nothing is invented
        out = build_engagement.Build.pair(self.pairing(id="J10", event="loss_list", ship="", date="1944-04", time=None, zone=None, lat_raw="", lon_raw="",
                                                       local="1944-04", utc=None, lat=None, lon=None), {"ss-385-bang/1": "bang"})
        r = out["record"]
        self.assertEqual((r["id"], r["date"], r["time"], r["zone"], r["local"], r["utc"], r["lat"], r["lon"]), ("J10", "1944-04", "", "", "1944-04", None, None, None))

    def test_another_boats_attack_takes_that_boats_id(self):
        x = self.pairing()
        x.update({"attack": "ss-384-parche/1:Attack 2", "unit": "ss-384-parche/1", "attack_ref": "Attack 2", "relation": "possible"})
        out = build_engagement.Build.pair(x, {"ss-385-bang/1": "bang", "ss-384-parche/1": "parche"})
        self.assertEqual((out["attack"], out["boat"], out["relation"]), ("Attack 2", "parche", "possible"))


class EngagementIntelligence(unittest.TestCase):
    """Build.frupac and Build.frupac_events: a patrol's frupac.yml (US radio intelligence) read into an engagement like
    her japanese.yml. A fixture file made here, with BANG's F01 (Attack 1's candidate: 2215/29 at about 19.4N 118.7E),
    a note with no time tied to the attack, and a note of the next day outside the window; the attack rows are given.
    Checked: the zone assumed (2215 I is 1315 GMT, 19 minutes after the sheet's 2256 K), the estimated position with its
    basis, the words as written, the kind from the note's event, the note's own fields kept, and the window."""

    NOTES = ("- id: F01\n  map: metapth1733008\n  map_date: 1944-04-29\n  view: resolution=1&lat=6300&lon=4150\n"
             "  text: 292215 / Yoshima Maru / att. by torp / 2215/29\n  dtg: '292215'\n  date: 1944-04-29\n  time: '2215'\n"
             "  lat_est: '19.4'\n  lon_est: '118.7'\n  ship: Yashima Maru\n  event: torpedoed\n  attack: Attack 1\n  relation: candidate\n"
             "  note: Place and time fit Takegawa Maru\n"
             "- id: F02\n  map: metapth1733008\n  map_date: 1944-04-29\n  text: YASHIMA IN DANGER OF SINKING\n  date: 1944-04-29\n"
             "  ship: Yashima Maru\n  event: sinking\n  attack: Attack 1\n  relation: candidate\n"
             "- id: F05\n  map: metapth1733009\n  map_date: 1944-04-30\n  text: 301730\n  dtg: '301730'\n  date: 1944-04-30\n  time: '1730'\n"
             "  lat_est: '18.5'\n  lon_est: '119.3'\n  ship: Wales Maru\n  event: sub_contact\n  relation: candidate\n")
    ROWS = [{"ref": "Attack 1", "utc": datetime(1944, 4, 29, 12, 56), "lat": 19 + 26 / 60, "lon": 118 + 45 / 60}]
    WINDOW = (datetime(1944, 4, 29, 6, 0), datetime(1944, 4, 30, 8, 0))

    def notes(self, text=NOTES):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "frupac.yml"
            path.write_text(text, encoding="utf-8")
            b = build_engagement.Build()
            out = b.frupac("ss-385-bang/1", self.ROWS, path)
        return b, out

    def test_a_note_is_read_with_its_zone_assumed_and_its_position_estimated(self):
        b, notes = self.notes()
        self.assertEqual(b.problems, [])
        f = notes[0]
        self.assertEqual((f["id"], f["unit"], f["date"], f["time"], f["local"]), ("F01", "ss-385-bang/1", "1944-04-29", "2215", "1944-04-29 2215 I"))
        self.assertEqual(f["utc"], datetime(1944, 4, 29, 13, 15))   # 2215 with zone I assumed: 1315 GMT, 19 minutes after the sheet
        self.assertEqual((f["lat"], f["lon"]), (19.4, 118.7))
        self.assertEqual((f["attack_ref"], f["attack_unit"], f["attack_utc"]), ("Attack 1", "ss-385-bang/1", datetime(1944, 4, 29, 12, 56)))
        self.assertEqual(f["cite"]["kind"], "intelligence")   # the map's citation, through SOURCES.yml
        self.assertEqual(f["cite"]["of"], "us")
        self.assertEqual(f["cite"]["href"], "https://texashistory.unt.edu/ark:/67531/metapth1733008/m1/1/zoom/?resolution=1&lat=6300&lon=4150")
        self.assertEqual(f["cite"]["label"], "map")
        self.assertEqual(notes[1]["utc"], None)   # no time written
        self.assertEqual(notes[1]["local"], "1944-04-29")
        self.assertIsNone(notes[2]["attack_utc"])

    def test_the_entries_inside_the_window(self):
        b, notes = self.notes()
        evs = b.frupac_events(notes, *self.WINDOW)
        self.assertEqual([e["frupac"]["id"] for e in evs], ["F01", "F02"])   # F05, 1730 I on the 30th (0830 GMT), is after the window
        e = evs[0]
        self.assertEqual((e["origin"], e["actor"], e["of"], e["about"], e["kind"], e["title"]), ("frupac", "FRUPAC", "us", "Yashima Maru", "hit", "Yashima Maru"))
        self.assertEqual(e["words"], "292215 / Yoshima Maru / att. by torp / 2215/29")   # as written, the line breaks kept
        self.assertEqual((e["local"], e["utc"], e["key"]), ("1944-04-29 2215 I", "1944-04-29T13:15Z", "1944-04-29T13:15Z"))
        self.assertEqual(e["source"], "FRUPAC war map, 1944-04-29")
        self.assertEqual((e["lat"], e["lon"], e["pos_basis"]), (19.4, 118.7, "approx"))
        self.assertEqual(e["basis"], "assumed")
        self.assertIn("Zone I (Tokyo time) assumed", e["note"])   # the zone assumption, said on the entry
        self.assertIn("read off the map", e["note"])
        self.assertIn("Place and time fit Takegawa Maru", e["note"])   # our note from the file, after it
        self.assertEqual(e["frupac"], {"id": "F01", "ship": "Yashima Maru", "event": "torpedoed", "attack": "Attack 1", "relation": "candidate",
                                       "map": "metapth1733008", "map_date": "1944-04-29", "view": "resolution=1&lat=6300&lon=4150",
                                       "zoom": "https://texashistory.unt.edu/ark:/67531/metapth1733008/m1/1/zoom/?resolution=1&lat=6300&lon=4150", "dtg": "292215"})
        # the untimed note is drawn at the attack's time and says so; it has no mark of its own, so no position
        u = evs[1]
        self.assertEqual((u["utc"], u["kind"]), ("1944-04-29T12:56Z", "damage"))
        self.assertIn("drawn at the time of the attack it is tied to (Attack 1)", u["note"])
        self.assertNotIn("lat", u)
        self.assertNotIn("Zone I", u["note"])   # nothing assumed about a zone the note doesn't have a time for
        # the same notes a little later: nothing inside a window that ends before them
        self.assertEqual(b.frupac_events(notes, datetime(1944, 4, 29, 6, 0), datetime(1944, 4, 29, 12, 0)), [])

    def test_a_note_beside_its_attack_for_the_sources_view(self):
        _, notes = self.notes()
        i = build_engagement.Build.intel(notes[0])
        self.assertEqual((i["id"], i["relation"], i["utc"], i["lat"], i["lon"], i["time"], i["dtg"]), ("F01", "candidate", "1944-04-29T13:15Z", 19.4, 118.7, "2215", "292215"))
        self.assertEqual(i["text"], "292215 / Yoshima Maru / att. by torp / 2215/29")
        self.assertEqual(i["zoom"], i["cite"]["href"])
        self.assertIsNone(build_engagement.Build.intel(notes[1])["utc"])   # its own time, none: the view computes nothing from a placed one
        self.assertNotIn("minutes", i)   # the arithmetic is the page's (Engage.apart)

    def test_what_fails(self):
        bad = ("- id: F01\n  map: metapth1733008\n  map_date: 1944-04-29\n  text: x\n  date: 1944-04-29\n  time: '2215'\n  lat_est: '19.4'\n"
               "  event: teleport\n  attack: Attack 9\n  relation: maybe\n  colour: red\n")
        b, _ = self.notes(bad)
        said = "\n".join(b.problems)
        self.assertIn("F01: unknown field 'colour'", said)
        self.assertIn("F01: event 'teleport' has no kind in FRUPAC_KIND", said)
        self.assertIn("F01: relation 'maybe' is not one of candidate, context, match", said)
        self.assertIn("F01: no attack 'Attack 9' in ss-385-bang/1's positions.csv", said)
        self.assertIn("F01: `lat_est` and `lon_est` go together", said)

    def test_every_frupac_event_in_the_records_has_a_kind(self):
        for path in sorted(records.RECORDS.rglob("frupac.yml")):
            for f in records.load_yaml(path) or []:
                self.assertIn(f.get("event"), build_engagement.FRUPAC_KIND, f"{path}: {f.get('id')}")
        self.assertTrue(set(build_engagement.FRUPAC_KIND.values()) <= build_engagement.KINDS)


class EngagementCheck(unittest.TestCase):
    def test_what_check_compares(self):
        # `check` compares each JSON file's text to text(obj): compact JSON, UTF-8 as is, dates as strings, one newline
        self.assertEqual(build_engagement.text({"at": date(1944, 5, 3), "s": "Nouméa", "n": [1, 2]}),
                         '{"at":"1944-05-03","s":"Nouméa","n":[1,2]}\n')
        self.assertEqual(build_engagement.iso(datetime(1944, 5, 2, 22, 3)), "1944-05-02T22:03Z")
        self.assertIsNone(build_engagement.iso(None))
        self.assertEqual(build_engagement.parse_iso("1944-05-02T22:03Z"), datetime(1944, 5, 2, 22, 3))


if __name__ == "__main__":
    unittest.main()
