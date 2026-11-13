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
import json
import os
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
import build_glossary
import build_operations
import build_seabees
import build_subjects
import check_sources
import check_track
import jgrid
import lint
import loc_sitmaps
import morning_reports
import nara
import naval_grid
import neighbours
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
        # under a hook GIT_DIR names the kit's own repository, and `git init` would re-initialise that one (as bare,
        # with its worktree still set, which breaks every git command in it) instead of making a new one here
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True, env=env)

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

    def test_fmt005_a_single_angle_quote_in_a_page(self):
        # the character, its HTML entity or its CSS escape, in a page, script or stylesheet; « », → and the records pass
        L = self.kit({"a.css": '.door b::after { content: " ›"; }\n.x::after { content: "\\203A"; }\n',
                      "b.html": "<a>the records &rsaquo;</a>\n<a>« quoted » →</a>\n",
                      "c.js": "const back = '‹ before';\n", "notes.md": "a › in prose\n"})
        self.assertEqual(self.flagged(L, "FMT005"), [("a.css", 1), ("a.css", 2), ("b.html", 1), ("c.js", 1)])


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

class EngagementRoutes(unittest.TestCase):
    """Build.route: a routes.yml entry -> its points (records/README.md, "An engagement's routes")."""

    def setUp(self):
        self.b = build_engagement.Build()
        self.pos = {"x": {"id": "x", "label": "X", "lat": 48.0, "lon": 11.0}, "y": {"id": "y", "label": "Y", "lat": 48.5, "lon": 11.5}}

    def test_a_course_is_drawn_back_from_where_it_was_typed(self):
        # due south at 180°, 11.057 km: the line starts 0.1° of latitude north of the position and ends on it
        r = self.b.route({"id": "c", "of": "us", "by": "air", "basis": "reported", "to": "x", "course": 180, "drawn_km": 11.057, "ref": ""}, self.pos, "w")
        self.assertEqual(r["points"], [[11.0, 48.1], [11.0, 48.0]])
        self.assertIn("is drawn, not recorded", r["resolved"])

    def test_two_positions_or_a_run_of_points(self):
        r = self.b.route({"id": "s", "of": "de", "by": "air", "basis": "inferred", "from": "x", "to": "y", "ref": ""}, self.pos, "w")
        self.assertEqual(r["points"], [[11.0, 48.0], [11.5, 48.5]])
        r = self.b.route({"id": "k", "of": "us", "by": "ground", "actor": "u1", "basis": "sketched", "arrow": False, "points": [{"lat": 48.2, "lon": 11.1}, "y"], "ref": ""}, self.pos, "w")
        self.assertEqual((r["points"], r["arrow"], r["by"], r["actor"]), ([[11.1, 48.2], [11.5, 48.5]], False, "ground", "u1"))
        self.assertEqual([m for m in map(str, self.b.problems) if "no citation" not in m], [])   # (the cases cite nothing)

    def test_a_route_needs_a_basis_a_side_and_a_way_to_its_points(self):
        self.assertIsNone(self.b.route({"id": "bad", "basis": "guessed"}, self.pos, "w"))
        msgs = " ".join(m for _, m in self.b.problems) if self.b.problems and isinstance(self.b.problems[0], tuple) else " ".join(map(str, self.b.problems))
        self.assertIn("basis", msgs)
        self.assertIn("needs `points`", msgs)
        self.assertIn("by None", msgs)   # what moved is required: air, ground or sea


class EngagementReach(unittest.TestCase):
    """Build.ring: a reach.yml entry -> its ring (records/README.md, "An engagement's reach")."""

    def setUp(self):
        self.b = build_engagement.Build()
        self.pos = {"x": {"id": "x", "label": "X", "lat": 48.0, "lon": 11.0}, "n": {"id": "n", "label": "N", "lat": None, "lon": None}}

    def test_the_range_in_yards_becomes_km_round_the_place(self):
        # 3,500 yd (FM 4-155's 37 mm) x 0.9144 m = 3.2004 km
        r = self.b.ring({"id": "d", "of": "us", "at": "x", "weapon": "37 mm", "range_yd": 3500, "basis": "assumed", "ref": ""}, self.pos, "w")
        self.assertEqual((r["lon"], r["lat"], r["km"], r["basis"]), (11.0, 48.0, 3.2, "assumed"))

    def test_a_ring_needs_a_placed_position_and_a_range(self):
        self.assertIsNone(self.b.ring({"id": "a", "of": "us", "at": "n", "range_yd": 100, "basis": "assumed"}, self.pos, "w"))
        self.assertIsNone(self.b.ring({"id": "b", "of": "us", "at": "x", "range_yd": 0, "basis": "guessed"}, self.pos, "w"))
        msgs = " ".join(map(str, self.b.problems))
        for want in ("not a placed position", "range in yards", "basis"):
            self.assertIn(want, msgs)


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
        self.assertIn("[[frob:x]]: unknown kind (cite, op, ship, unit, page, convoy, engagement, step, who)", said)
        self.assertNotIn("nowhere2", said)         # an example in backticks isn't a link
        self.assertNotIn("[[page:index]]", said)   # site/index.html is there

    def test_an_unknown_field_and_a_missing_title(self):
        problems, _ = self.build(engagement="---\nshort: x\ncolour: red\nparticipants: []\n---\n\nWords.\n", events="")
        said = "\n".join(problems)
        self.assertIn("`title` is missing", said)
        self.assertIn("unknown field 'colour' (known: against, clock, eyebrow, fronts, participants, places, relief, roads, short, steps, theater, title, views, window)", said)

    def test_a_step_link_names_a_step_some_entry_carries(self):
        # the story's [[step:]] links set the clock and the map to a step; a step is defined by the entries that carry it
        eng = ("---\ntitle: A test\nshort: test\nclock: H\n"
               "views:\n  close: {name: The station, box: [[120.0, 18.0], [121.0, 19.0]]}\n"
               "steps:\n  s1: {view: close, when: 'the morning'}\n  s2: {view: [[119.0, 17.0], [122.0, 20.0]]}\n  s9: {view: close}\n"
               "participants:\n  - {id: boat, name: A boat, of: us, kind: submarine}\n---\n\n"
               "Words [[step:s1|at dawn]] and [[step:s2]] and [[step:s3|later]]; `[[step:s4]]` is an example.\n")
        events = ("- {at: 1944-05-03 0900, actor: boat, kind: log, words: w, source: s, ref: r, step: s2}\n"
                  "- {at: 1944-05-03 0603, actor: boat, kind: log, words: w, source: s, ref: r, step: s1}\n"
                  "- {at: 1944-05-03, actor: boat, kind: log, words: w, source: s, ref: r, step: s1}\n")
        problems, out = self.build(engagement=eng, events=events)
        said = "\n".join(problems)
        self.assertIn("[[step:s3]]: no entry in events.yml carries step 's3'", said)
        self.assertIn("step s9: no entry in events.yml carries step 's9'", said)
        self.assertNotIn("s4", said)                                   # an example in backticks isn't a link
        self.assertNotIn("[[step:s1", said)
        self.assertNotIn("[[step:s2", said)
        # the steps the entries carry, in time order, each timed by its earliest clocked entry and framed as the front matter says
        self.assertEqual([(x["id"], x["utc"], x["entries"], x["when"]) for x in out["steps"]],
                         [("s1", "1944-05-02T22:03Z", 2, "the morning"), ("s2", "1944-05-03T01:00Z", 1, "")])
        self.assertEqual(out["steps"][0]["view"], {"id": "close", "name": "The station", "box": [[120.0, 18.0], [121.0, 19.0]], "basis": "given"})
        self.assertEqual(out["steps"][1]["view"]["box"], [[119.0, 17.0], [122.0, 20.0]])
        # a step link outside an engagement's story (an operation's chapter) is refused
        chk = build_operations.Checker()
        chk.links("See [[step:s1]].", "ops.md")
        self.assertIn("ops.md: [[step:s1]]: a step link belongs in an engagement's story (engagement.md)", chk.problems)

    def test_a_relief_or_road_map_the_records_do_not_have_is_reported(self):
        eng = ("---\ntitle: A test\nshort: test\nrelief: nowhere\nroads: none\nparticipants: []\n---\n\nWords.\n")
        problems, out = self.build(engagement=eng, events="")
        said = "\n".join(problems)
        self.assertIn("relief 'nowhere' has no records/relief/nowhere/relief.json", said)
        self.assertIn("roads 'none' has no records/roads/none-primary.geojson", said)
        self.assertEqual((out["relief"], out["roads"]), ([], ""))

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


class GlossaryPatterns(unittest.TestCase):
    """build_glossary.check_pattern: a `patterns` entry (the records' notations) compiles, its example matches all of it,
    none of its `not` forms match anywhere, its `see` page exists and its $n are groups the pattern has. Then the
    committed patterns against values as the records write them, and against what each must leave alone."""

    GOOD = {"id": "t", "name": "a test", "pattern": "([0-9]{4}) ([A-Z])", "example": "2201 I", "not": ["VT 0893"],
            "says": "x", "source": "opnav-29-p1000/X", "see": "zones.html?zone=$2"}

    def test_a_good_entry_passes(self):
        self.assertEqual(build_glossary.check_pattern(self.GOOD, "p"), [])

    def test_an_example_that_does_not_match_the_whole_pattern_fails(self):
        said = build_glossary.check_pattern({**self.GOOD, "example": "2201 I sighted"}, "p")
        self.assertEqual(said, ["p: example '2201 I sighted' does not match the whole pattern"])

    def test_a_not_form_that_matches_fails(self):
        said = build_glossary.check_pattern({**self.GOOD, "not": ["at 2201 I sighted"]}, "p")
        self.assertEqual(said, ["p: 'at 2201 I sighted' matches, and must not"])

    def test_an_unknown_see_page_or_group_fails(self):
        self.assertEqual(build_glossary.check_pattern({**self.GOOD, "see": "clocks.html?zone=$2"}, "p"),
                         ["p: see 'clocks.html?zone=$2' is not a page in site/"])
        self.assertEqual(build_glossary.check_pattern({**self.GOOD, "see": "zones.html?zone=$3"}, "p"),
                         ["p: see refers to $3, but the pattern has 2 groups"])

    def test_a_pattern_that_does_not_compile_or_differs_between_engines_fails(self):
        self.assertTrue(build_glossary.check_pattern({**self.GOOD, "pattern": "([0-9]{4"}, "p")[0].startswith("p: pattern does not compile: "))
        self.assertEqual(build_glossary.check_pattern({**self.GOOD, "pattern": "(?P<t>[0-9]{4}) ([A-Z])"}, "p"),
                         ["p: pattern uses \\p, \\b, \\w, a flag or a named group, which JavaScript and Python read differently"])

    def committed(self):
        g = records.load_yaml(build_glossary.YML)
        return {p["id"]: __import__("re").compile(p["pattern"]) for p in g["patterns"]}

    def test_the_committed_patterns_against_the_records_forms(self):
        P = self.committed()
        # as the records write them: TAMA-17's events (2201 I, 1604 H), BANG's positions (1600 VW), Algiers (1500A, 2100 A)
        for v in ["2201 I", "0603 H", "2256 K", "0330 Z", "1250 I", "1600 VW", "1500A", "2100 A", "2400A"]:
            self.assertTrue(P["zone-time"].fullmatch(v), v)
        # the Army's stations: Btry D 106th AAA (F-2684), the 894th (VZ-6457, J 043628), S. Italy (RA 25, rN 25), Normandy (vV044572)
        for v in ["V-044572", "VT 0893", "F-2684", "J 043628", "RA 25", "rN 25", "vV044572", "wF6317", "Q9999", "N123456", "Y 99", "O-34"]:
            self.assertTrue(P["army-grid"].fullmatch(v), v)
        for v in ["XXIII 97", "XXIII 117", "XXIII 9"]:
            self.assertTrue(P["german-point"].fullmatch(v), v)
        for v in ["CJ 9472", "CO 3381", "CQ 11", "CJ9472"]:
            self.assertTrue(P["naval-square"].fullmatch(v), v)
        for v in ["メキ三ツ", "メツ四セ", "スフ二イ", "ホク三テへ"]:
            self.assertTrue(P["kana-code"].fullmatch(v), v)
        for v in ["123S", "91S", "149P", "9S", "99.9P"]:
            self.assertTrue(P["track-angle"].fullmatch(v), v)
        for v in ["Gyro 013", "gyro 009", "gyros 351", "gyro (356"]:
            self.assertTrue(P["gyro-angle"].fullmatch(v), v)

    def test_what_the_committed_patterns_leave_alone(self):
        P = self.committed()
        # a zone pattern is not a grid reference, and a grid pattern is not a time with its zone
        self.assertIsNone(P["zone-time"].search("VT 0893"))
        self.assertIsNone(P["army-grid"].search("2201 I"))
        for v in ["1944-04-29", "p03", "SS-385", "At 1604 I sighted the convoy", "0603 Hrs", "rg38-74802746/p16"]:
            self.assertIsNone(P["zone-time"].search(v), v)
        for v in ["TF 58", "TG 58.3", "JV 44", "Mk 14", "p03", "SS-385", "CJ 9472", "1944-04-29", "XXIII 97", "123S", "Me 262",
                  "KG 54", "leads L39, L40 and L45", "A 1600 hrs", "A 90 mm gun"]:   # a Luftwaffe wing, the family's leads, prose
            self.assertIsNone(P["army-grid"].search(v), v)
        for v in ["V-044572", "VT 0893", "II Corps", "World War II 1945"]:
            self.assertIsNone(P["german-point"].search(v), v)
        for v in ["VT 0893", "CV 16", "CA 1944", "V-044572", "CO 14 Tk Bn"]:   # a commanding officer, not a square
            self.assertIsNone(P["naval-square"].search(v), v)
        for v in ["タマ一七", "タカ九〇九", "ニテ四次ニ亘リ", "二十一日"]:   # a convoy's name, prose
            self.assertIsNone(P["kana-code"].search(v), v)
        for v in ["27-28S", "SS-385", "153-02E", "0893 VT", "2201 I"]:
            self.assertIsNone(P["track-angle"].search(v), v)
        for v in ["gyro + 180", "gyro angles by hand", "Gyro 13"]:
            self.assertIsNone(P["gyro-angle"].search(v), v)

    def test_the_committed_file_builds_with_no_problem(self):
        data, problems, _ = quietly(build_glossary.build)
        self.assertEqual(problems, [])
        self.assertEqual([p["id"] for p in data["patterns"]],
                         ["zone-time", "army-grid", "german-point", "naval-square", "kana-code", "track-angle", "gyro-angle"])


class Reckoning(unittest.TestCase):
    """A Japanese log's courses, as converted (北六五度東 -> N 65° E), to degrees true; and W-15's night of 22-23 November
    1944 reckoned from her log between her two fixes (ships/jp-w-15): the route is the build's, and says how far off it was."""

    def test_courses_as_written(self):
        c = build_engagement.Build.course_deg
        self.assertEqual([c("N 65° E"), c("S 80° E"), c("S 45° W"), c("N 20° W"), c("W"), c("E"), c("N 0° E")], [65, 100, 225, 340, 270, 90, 0])
        self.assertIsNone(c("north-east"))

    def test_w15_reckoned_from_her_log(self):
        b = build_engagement.Build()
        p = {"id": "w-15", "name": "W-15", "of": "jp", "track": "jp-w-15", "opposed": True}
        rows, _, _ = b.patrol("jp-w-15")
        r, logged = b.reckon(p, rows, datetime(1944, 11, 22, 10, 0), datetime(1944, 11, 23, 0, 0))
        charges = [e for e in logged if e["kind"] == "depth_charge"]
        self.assertEqual([(e["local"], e["placed"]) for e in charges], [("1944-11-22 2346 I", "reckoned"), ("1944-11-23 0005 I", "reckoned")])
        self.assertIn("Then, untimed: Sonar", charges[0]["words"])   # the untimed sonar line goes with the 2346 attack
        self.assertEqual([m for m in map(str, b.problems)], [])
        self.assertEqual((r["basis"], r["by"], r["actor"], r["points"][0]), ("reckoned", "sea", "w-15", [122.5167, 24.3667]))   # from her 2240 fix
        self.assertIn("off her 0730 I fix", r["note"])
        self.assertIn("(assumed)", r["note"])


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
                         {"attack": "Attack 1", "boat": "bang", "utc": "1944-04-29T12:56Z", "relation": "hit", "note": "Takegawa Maru (1,930 GRT), TAMA-17", "janac": []})
        r = out["record"]
        self.assertEqual((r["id"], r["event"], r["ship"], r["date"], r["time"], r["zone"]), ("J03", "torpedoed", "Takegawa Maru", "1944-04-29", "2201", "I"))
        self.assertEqual((r["local"], r["utc"]), ("1944-04-29 2201 I", "1944-04-29T13:01Z"))   # 2201 I is 1301 GMT, five minutes after the attack
        self.assertEqual((r["lat"], r["lon"], r["lat_raw"], r["lon_raw"]), (19.3333, 118.8333, "19-20N", "118-50E"))
        self.assertEqual((r["lang"], r["original"][:5], r["translation"][:7]), ("ja", "二九日二二", "At 2201"))
        self.assertEqual(r["cite"]["ref"], "jacar:C08050103200 p23")
        self.assertNotIn("minutes", out)   # the arithmetic is the page's (Engage.apart), never stored

    def test_janacs_entry_as_printed_and_checked(self):
        # Takegawa Maru in JANAC's merchant list (p58) and BANG's page of the appendix (p3): both pages resolve, the
        # position is placed from the printed minutes, and an entry with no `probable`, a wrong page or an unknown field is a problem
        b = build_engagement.Build()
        j = b.janac({"ship": "Takegawa Maru", "date": date(1944, 4, 29), "type": "Cargo", "tons": "1,930", "lat_raw": "19-26N",
                     "lon_raw": "118-45E", "agent": "BANG", "probable": False, "ref": "janac:4/p58", "appendix": "janac:6/p3"}, "test")
        self.assertEqual(b.problems, [])
        self.assertEqual((j["date"], j["agent"], j["probable"], round(j["lat"], 4), round(j["lon"], 4)), ("1944-04-29", "BANG", False, 19.4333, 118.75))
        self.assertEqual((j["cite"]["ref"], j["appendix"]["ref"]), ("janac:4/p58", "janac:6/p3"))
        b.janac({"ship": "Takegawa Maru", "date": "1944-04-29", "agent": "BANG", "ref": "janac:6/p3", "credit": "BANG"}, "test")
        msgs = " ".join(map(str, b.problems))
        self.assertIn("`probable`", msgs); self.assertIn("a page of the lists", msgs); self.assertIn("unknown field 'credit'", msgs)

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


class Subjects(unittest.TestCase):
    """build_subjects.py against a records folder made here: one subject of each kind, the relations merged from every
    dataset into one shape, and a subject without a plain line failing."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.rec = Path(self._tmp.name).resolve()
        w = lambda name, text: (self.rec / name).parent.mkdir(parents=True, exist_ok=True) or (self.rec / name).write_text(text, encoding="utf-8")
        w("SOURCES.yml", "nara-catalog:\n  title: NARA\n  short: National Archives\n  kind: record\n  match: '^rg(\\d+)-(\\d+)/p(\\d+)$'\n"
          "  link: https://catalog.archives.gov/id/{2}?objectPage={3}\n"
          "etoob:\n  title: Order of battle\n  short: ETO OB\n  kind: assessment\n  match: '^etoob-(\\w+)/p(\\d+)$'\n  link: https://example.org/{1}/{2}\n"
          "jacar:\n  title: JACAR\n  short: JACAR\n  kind: record\n  match: '^jacar:(C\\d{11})( p\\d+)?$'\n  link: https://www.jacar.archives.go.jp/das/image/{1}\n")
        w("inventory.yml", "boats:\n  SS-385:\n    folder: boats/ss-385-bang\n    patrols:\n      1: { status: mapped, nara: [74802746], first_fix: 1944-03-30, last_fix: 1944-05-15, files: [positions] }\n"
          "units:\n  67ca-med:\n    record: { status: mapped }\nseabees:\n  20ncb:\n    record: { status: mapped }\ncommands:\n  comsubpac:\n    records:\n      1944-10: { status: transcribed, nara: [139761402] }\n")
        w("boats/ss-385-bang/ship.yml", "name: BANG\nhull: SS-385\nclass: Balao\nkind: submarine\nplain: a fleet submarine of the Balao class\nmax_kts: 20.5\nmap:\n  periods:\n    - { n: 1, name: First War Patrol, dates: 29 Mar – 14 May 1944 }\n")
        w("boats/ss-385-bang/patrol-1/positions.csv", "source,ref,date,time,zone,lat_raw,lon_raw,page,on_track,note\nnoon,noon,1944-04-29,1200,K,19-26N,118-45E,rg38-74802746/p16,yes,\n")
        w("boats/ss-385-bang/tracks.geojson", '{"type":"FeatureCollection","features":[{"type":"Feature","properties":{"kind":"noon","ref":"noon","patrol":1,"on_track":true,"utc":"1944-04-29T02:00Z"},"geometry":{"type":"Point","coordinates":[118.75,19.43]}}]}')
        w("army/units.csv", "unit,name,short,note\n67ca-med,Medical Detachment,Med. Det.,aid men\n9ad,9th Armored Division,9th AD,a division\n")
        w("army/units.yml", "67ca-med:\n  plain: the aid men of a regiment\n9ad:\n  plain: an armored division\n")
        w("army/relations.csv", "unit,relation,other,other_name,from,to,basis,page,note\n67ca-med,part_of,9ad,9th Armored Division,..1944-01-01,,reported,etoob-9AD/p499,a row\n")
        w("army/leads.yml", "- statement: where it stood on 8 May\n  units: [9ad]\n  said_by: the booklet\n  ref: [etoob-9AD/p501]\n  searched: the order of battle\n  still: the division's report\n")
        w("army/army.json", '{"units":[{"unit":"67ca-med","name":"Medical Detachment","stations":[{"date":"1943-03-28","lat":35.7,"lon":-0.6,"place":"Oran","source":"regt","placed":"town","station":"x"},{"date":"1943-05-05","lat":37.0,"lon":9.6,"place":"Mateur","source":"mr","placed":"town","station":"y"}],"actions":[]},{"unit":"9ad","name":"9th Armored Division","stations":[],"actions":[]}],"routes":[]}')
        w("seabees/units.csv", "unit,name,note\n20ncb,20th Naval Construction Battalion,Seabees\n")
        w("seabees/units.yml", "20ncb:\n  plain: a naval construction battalion\n")
        w("seabees/parts.csv", "unit,part,parent,from,to,note\n20ncb,Forward Echelon,battalion,1943-05-13,1944-06-06,About 500 men (rg24-190273312/p0041)\n")
        w("seabees/seabees.json", '{"rows":[{"id":0,"unit":"20ncb","part":"battalion","date":"1942-08-20","station":"x","place":"Norfolk","lat":36.8,"lon":-76.3,"source":"muster","assumed":"","links":[]}],"parts":[],"voyages":[],"projects":[],"weather":{}}')
        w("convoys/tama-17/convoy.md", "---\nconvoy: TAMA-17\nname_ja: タマ一七\nplain: a Takao–Manila convoy\nfrom: Takao\nto: Manila\nsailed: 1944-04-28\nroute: []\nvoyage: []\nships:\n  - ship: Takegawa Maru\n    role: merchant\n    to: 1944-04-29\n    source: jacar:C08050103200\n    page: p23\n    basis: reported\n---\n\nTakao to Manila.\n")
        w("convoys/convoys.json", '{"lanes":{},"convoys":[{"id":"tama-17","sightings":[],"hits":[],"attacks":[]}]}')
        w("commands/comsubpac/command.yml", "name: Commander Submarine Force\nshort: ComSubPac\nkind: command\nof: us\nplain: the submarine force's headquarters\n")
        w("commands/comsubpac/task_organization.csv", "unit,title,page\nG 17.1,Empire Patrol Group.,rg38-139761402/p03\nG 17.11 through G 17.24 inclusive,Coordinated Attack Groups.,rg38-139761402/p03\n")
        w("commands/comsubpac/disposition.csv", "date,page,section,boat,name,unit,note\n1944-10-31,rg38-139761402/p18,Enroute patrol stations,BANG,BANG,17.18.2,\n")
        w("engagements/index.json", "[]")
        self.patch = mock.patch.object(build_subjects, "RECORDS", self.rec)
        self.patch.start()
        self.patch_r = mock.patch.object(records, "RECORDS", self.rec)
        self.patch_r.start()
        self.patch_o = mock.patch.object(build_operations.records, "RECORDS", self.rec)
        self.patch_o.start()

    def tearDown(self):
        self.patch.stop()
        self.patch_r.stop()
        self.patch_o.stop()
        self._tmp.cleanup()

    def test_one_subject_of_each_kind_with_its_plain_line(self):
        b, subjects = build_subjects.build()
        self.assertEqual(b.problems, [])
        self.assertEqual({s["kind"] for s in subjects}, {"boat", "unit", "battalion", "convoy", "command"})
        by = {s["id"]: s for s in subjects}
        self.assertEqual(by["ss-385-bang"]["alias"], "bang")
        self.assertEqual(by["ss-385-bang"]["plain"], "a fleet submarine of the Balao class")
        self.assertEqual(by["ss-385-bang"]["periods"][0]["status"], "mapped")
        self.assertEqual(by["67ca-med"]["periods"][0], {"month": "1943-03", "stations": 1, "source": "regt", "assumed": True, "sources": ["regt"], "places": ["Oran"]})
        self.assertEqual(by["67ca-med"]["theatre"], "mediterranean")
        self.assertEqual(by["9ad"]["leads"][0]["statement"], "where it stood on 8 May")
        self.assertEqual(by["tama-17"]["name"], "Convoy TAMA-17")

    def test_relations_from_every_dataset_in_one_shape(self):
        _, subjects = build_subjects.build()
        by = {s["id"]: s for s in subjects}
        keys = {"relation", "dir", "other", "other_name", "from", "to", "basis", "ref", "cite", "note"}
        for s in subjects:
            for r in s["relations"]:
                self.assertEqual(set(r), keys, s["id"])
        # relations.csv, both ways
        self.assertEqual([(r["relation"], r["dir"], r["other"]) for r in by["67ca-med"]["relations"]], [("part_of", "of", "9ad")])
        self.assertEqual([(r["relation"], r["dir"], r["other"]) for r in by["9ad"]["relations"]], [("part_of", "to", "67ca-med")])
        # a part of the battalion, its page read out of the note; a ship in the convoy; a boat in a task unit; the force's groups
        self.assertEqual(by["20ncb"]["relations"][0]["other_name"], "Forward Echelon")
        self.assertEqual(by["20ncb"]["relations"][0]["cite"][0]["ref"], "rg24-190273312/p0041")
        self.assertEqual((by["tama-17"]["relations"][0]["other_name"], by["tama-17"]["relations"][0]["to"]), ("Takegawa Maru", "1944-04-29"))
        self.assertEqual(by["ss-385-bang"]["relations"][0]["other_name"], "Task Unit 17.18.2, Coordinated Attack Groups")
        self.assertEqual(by["comsubpac"]["relations"][0]["other"], "G 17.1")

    def test_a_subject_without_a_plain_line_fails(self):
        (self.rec / "army/units.yml").write_text("67ca-med:\n  plain: the aid men\n", encoding="utf-8")
        b, _ = build_subjects.build()
        self.assertEqual(b.problems, ["army/units.csv 9ad: no `plain` line in army/units.yml (what it was, in a line, ours)"])


class EngagementCheck(unittest.TestCase):
    def test_what_check_compares(self):
        # `check` compares each JSON file's text to text(obj): compact JSON, UTF-8 as is, dates as strings, one newline
        self.assertEqual(build_engagement.text({"at": date(1944, 5, 3), "s": "Nouméa", "n": [1, 2]}),
                         '{"at":"1944-05-03","s":"Nouméa","n":[1,2]}\n')
        self.assertEqual(build_engagement.iso(datetime(1944, 5, 2, 22, 3)), "1944-05-02T22:03Z")
        self.assertIsNone(build_engagement.iso(None))
        self.assertEqual(build_engagement.parse_iso("1944-05-02T22:03Z"), datetime(1944, 5, 2, 22, 3))



class SituationMaps(unittest.TestCase):
    """loc_sitmaps.py: the Library's listing read into the catalogue, and a day or a run of days picked from it."""

    PAGE = {"pagination": {"current": 1, "total": 1, "next": None}, "results": [
        {"title": "The Battle of the Bulge", "original_format": ["web page"], "url": "https://www.loc.gov/collections/x/articles/", "date": "1944"},
        {"title": "[March 7, 1945], HQ Twelfth Army Group situation map", "original_format": ["map"], "date": "1945-03-07",
         "url": "https://www.loc.gov/item/2004631895/", "image_url": ["https://tile.loc.gov/storage-services/service/gmd/gmd5/g5701/g5701s/ict21276.gif"], "aka": []},
        {"title": "[June 6, 1944], HQ Twelfth Army Group situation map", "original_format": ["map"], "date": "1944-06-06",
         "url": "https://www.loc.gov/item/2004629028/", "image_url": [], "aka": ["http://www.loc.gov/resource/g5701s.ict21001/"]},
        {"title": "HQ Twelfth Army Group situation map : [Battle of the Bulge]", "original_format": ["map"], "date": "1944-06-06",
         "url": "https://www.loc.gov/item/2001628569/", "image_url": ["https://www.loc.gov/static/x.jpg"], "aka": []},
    ]}

    def test_listing_keeps_the_daily_sheets_and_leaves_the_rest_out(self):
        import json
        with mock.patch.object(loc_sitmaps, "get", return_value=(json.dumps(self.PAGE).encode(), {})), contextlib.redirect_stdout(io.StringIO()):
            rows = loc_sitmaps.listing()
        self.assertEqual([(r["item"], r["date"], r["lccn"]) for r in rows],
                         [("ict21276", "1945-03-07", "2004631895"), ("ict21001", "1944-06-06", "2004629028")])

    def test_catalogue_round_trip_sorts_by_date_and_keeps_sizes(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(loc_sitmaps, "CATALOGUE", Path(d) / "sitmaps.csv"), \
                mock.patch.object(loc_sitmaps, "FRONTS", Path(d)):
            loc_sitmaps.write_catalogue([{"item": "ict21276", "date": "1945-03-07", "lccn": "1", "width": "6670", "height": "5975"},
                                         {"item": "ict21001", "date": "1944-06-06", "lccn": "2"}])
            rows = loc_sitmaps.read_catalogue()
        self.assertEqual([r["item"] for r in rows], ["ict21001", "ict21276"])
        self.assertEqual((rows[1]["width"], rows[1]["height"], rows[0]["width"]), ("6670", "5975", ""))

    def test_select_a_day_a_run_or_an_item(self):
        rows = [{"item": f"ict{21276 + i}", "date": f"1945-03-{7 + i:02d}"} for i in range(5)]
        self.assertEqual([r["date"] for r in loc_sitmaps.select(rows, "1945-03-08")], ["1945-03-08"])
        self.assertEqual([r["date"] for r in loc_sitmaps.select(rows, "1945-03-08", "1945-03-10")], ["1945-03-08", "1945-03-09", "1945-03-10"])
        self.assertEqual([r["item"] for r in loc_sitmaps.select(rows, "ict21280")], ["ict21280"])
        for r in rows:
            r["base"] = "B11" if r["date"] < "1945-03-10" else "B12"
        self.assertEqual([r["date"] for r in loc_sitmaps.select(rows, "B12")], ["1945-03-10", "1945-03-11"])
        self.assertEqual(loc_sitmaps.select(rows, "1945-04-01"), [])

class CatalogCache(unittest.TestCase):
    """tools/morning_reports.py names a file unit's cache folder and its citations by the record group the catalog gives
    (rg38- for a war diary, rg24- for a muster roll, rg64- for a morning-report roll), not by the Army's."""

    def hit(self, naid, group):
        return {"body": {"hits": {"hits": [{"_source": {"record": {
            "naId": naid, "title": "T", "digitalObjects": [{"objectId": "9", "objectUrl": "u"}],
            "ancestors": [{"levelOfDescription": "recordGroup", "recordGroupNumber": group}]}}}]}}}

    def run_in(self, tmp, setup, roll, group):
        nara = Path(tmp)
        setup(nara)
        with mock.patch.object(morning_reports, "NARA", nara), mock.patch.object(morning_reports, "_RECORDS", {}), \
                mock.patch.object(morning_reports, "get_json", return_value=self.hit(int(roll), group)) as g:
            return morning_reports.cite(roll, 22), morning_reports.folder(roll).name, g.call_count, sorted(
                f.name for f in nara.iterdir())

    def test_new_roll_takes_the_catalogs_group(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = self.run_in(tmp, lambda n: None, "135938645", 38)
        self.assertEqual(out[:2], ("rg38-135938645/p0022", "rg38-135938645"))
        self.assertEqual(out[3], ["rg38-135938645"])

    def test_cache_filed_under_the_armys_group_is_renamed(self):
        def legacy(n):
            (n / "rg64-135938645").mkdir()
            (n / "rg64-135938645" / "record.json").write_text('{"naId": 1, "title": "T", "pages": [["9", "u"]]}')
            (n / "rg64-135938645" / "p0022.txt").write_text("ocr")
        with tempfile.TemporaryDirectory() as tmp:
            out = self.run_in(tmp, legacy, "135938645", 38)
            kept = (Path(tmp) / "rg38-135938645" / "p0022.txt").exists()
        self.assertEqual(out[3], ["rg38-135938645"])
        self.assertTrue(kept)

    def test_a_folder_nara_py_made_needs_no_request(self):
        def made(n):
            (n / "rg38-135938645").mkdir()
            (n / "rg38-135938645" / "record.json").write_text(json.dumps(self.hit(135938645, 38)["body"]["hits"]["hits"][0]["_source"]["record"]))
        with tempfile.TemporaryDirectory() as tmp:
            out = self.run_in(tmp, made, "135938645", 38)
        self.assertEqual((out[0], out[2]), ("rg38-135938645/p0022", 0))


class CatalogSearch(unittest.TestCase):
    """tools/nara.py search: the catalog's matches for words, in a named series, by title alone or by the scanned text."""

    HITS = {"total": {"value": 18, "relation": "eq"}, "hits": [{"_source": {"record": {
        "naId": 78591807, "title": "COM NAV BASES, SOUTH SOLOMONS - War Diary, 7/1-31/44",
        "digitalObjects": [{}] * 9, "ancestors": [{"levelOfDescription": "series", "title": "War Diaries"}]}}}]}

    def test_title_search_in_a_named_series(self):
        with mock.patch.object(nara, "get", return_value=self.HITS) as g:
            total, lower, rows = nara.search('"COM NAV BASES"', title=True, series="war-diaries", limit=3)
        self.assertEqual(g.call_args.args[0], {"title": '"COM NAV BASES"', "limit": 3, "page": 1,
                                                "ancestorNaId": nara.SERIES_WAR_DIARIES})
        self.assertEqual((total, lower), (18, False))
        self.assertEqual(rows, [(78591807, 9, "COM NAV BASES, SOUTH SOLOMONS - War Diary, 7/1-31/44", "War Diaries")])

    def test_text_search_is_q_and_a_capped_total_is_a_lower_bound(self):
        capped = {"total": {"value": 10000, "relation": "gte"}, "hits": []}
        with mock.patch.object(nara, "get", return_value=capped) as g:
            total, lower, rows = nara.search("Wickham")
        self.assertEqual(g.call_args.args[0], {"q": "Wickham", "limit": 20, "page": 1})
        self.assertEqual((total, lower, rows), (10000, True, []))


class Neighbours(unittest.TestCase):
    """Who was beside and facing a unit, from the situation maps: computed leads."""

    def test_crossing_and_grouping(self):
        self.assertTrue(neighbours.crosses((0, 0), (2, 0), (1, -1), (1, 1)))
        self.assertFalse(neighbours.crosses((0, 0), (0.5, 0), (1, -1), (1, 1)))
        self.assertEqual(neighbours.front_crossings((0, 0), (3, 0), [[(1, -1), (1, 1)], [(2, -1), (2, 1)]]), 2)
        base = {"unit": "", "of": "de", "echelon": "xx", "friendly": False}
        self.assertEqual(neighbours.group_key(dict(base, label="11 ?")), neighbours.group_key(dict(base, label="11")))
        self.assertEqual(neighbours.group_key(dict(base, unit="9ad", label="9(-)")), "9ad")

    def test_chenogne(self):
        """Task Force Collins at Chenogne, 30 Dec 1944: measured from the battalion's own station, the 11th Armored beside
        it, the enemy's "3" (Cole: the 3d Panzer Grenadier Division) across the line, its own division drawn far west."""
        out = neighbours.run("60aib", date(1944, 12, 30), date(1944, 12, 30), 20)
        d = out["days"][0]
        self.assertIn("60aib's station, Chenogne", d["anchor"])
        self.assertTrue(any(n["unit"] == "11th-armd-div" and n["friendly"] for n in d["near"]))
        three = [n for n in d["near"] if n["label"] == "3" and not n["friendly"]]
        self.assertTrue(three and three[0]["across"] and three[0]["km"] < 10)
        self.assertTrue(d["own"] and d["own"][0]["unit"] == "9ad" and d["own"][0]["km"] > 25)
        # on the record that day: the battalion under CC A, and CC A attached to the 4th Armored (etoob-9AD/p501)
        self.assertTrue(any(r["unit"] == "9ad-cca" and r["other"] == "4ad" for r in d["record"]))


if __name__ == "__main__":
    unittest.main()
