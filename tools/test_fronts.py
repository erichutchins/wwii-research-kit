# /// script
# requires-python = ">=3.10,<3.14"
# dependencies = ["numpy", "scipy", "pillow", "scikit-image", "pyyaml"]
# ///
"""The situation maps' fit (tools/trace_front.py) against worked cases: the conic recovers a sheet drawn on a known
conformal conic, exactly and both ways; the choice of fit follows the number of towns. Apart from test_tools.py because
trace_front needs numpy, scipy and scikit-image, which the rest of the tools' tests don't.

    uv run tools/test_fronts.py
"""
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import trace_front as tf


def sheet(n_towns, seed=1, p1=45.0, p2=55.0, lon0=5.0):
    """Towns spread over a sheet, placed on it by a Lambert conic with the given parallels and an affine (a scale of
    1,200 px a unit, a 1.5 degree turn, an offset): what a scan of such a sheet gives, without the drafting's error."""
    rng = np.random.default_rng(seed)
    lon = rng.uniform(1.5, 9.5, n_towns)
    lat = rng.uniform(47.8, 52.2, n_towns)
    n = tf.Conic.cone(p1, p2)
    p1r = np.radians(p1)
    F = np.cos(p1r) * np.tan(np.pi / 4 + p1r / 2) ** n / n
    rho = F / np.tan(np.pi / 4 + np.radians(lat) / 2) ** n
    rho0 = F / np.tan(np.pi / 4 + np.radians(50.0) / 2) ** n
    th = n * np.radians(lon - lon0)
    x, y = rho * np.sin(th), rho0 - rho * np.cos(th)
    a = np.radians(1.5)
    px = 1200 * 6371 / 1000 * (x * np.cos(a) - y * np.sin(a)) + 3300
    py = 1200 * 6371 / 1000 * (x * np.sin(a) + y * np.cos(a)) + 3000
    return [{"town": f"t{i}", "x": f"{px[i]:.3f}", "y": f"{py[i]:.3f}", "lon": f"{lon[i]:.6f}", "lat": f"{lat[i]:.6f}"} for i in range(n_towns)]


class Crossings(unittest.TestCase):
    """sheet_towns.py: a graticule crossing named by its degrees, in a readings file and as a point."""

    def test_a_crossing_name_reads_both_ways(self):
        import sheet_towns as st
        self.assertEqual(st.crossing_ll("7E 50N"), (7.0, 50.0))
        self.assertEqual(st.crossing_ll("13.6667E 49N"), (13.6667, 49.0))
        self.assertEqual(st.crossing_ll("0.5W 48.5N"), (-0.5, 48.5))
        self.assertIsNone(st.CROSSING.fullmatch("Reims"))

    def test_readings_take_numbers_and_named_crossings_and_keep_the_last(self):
        import tempfile

        import sheet_towns as st
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
            f.write("# a comment\n12 2037,3966\n7E 50N 693,5750   # a seed\n12 none\n")
        self.assertEqual(st.readings(f.name), [["12", "none"], ["7E 50N", "693,5750"]])


class Margins(unittest.TestCase):
    """sheet_towns.py: a new sheet's first fit from points on its margins that lie on one labelled line each."""

    def test_a_line_name_reads(self):
        import sheet_towns as st
        self.assertEqual(st.line_value("1W"), ("lon", -1.0))
        self.assertEqual(st.line_value("49.5N"), ("lat", 49.5))
        self.assertIsNone(st.LINE.fullmatch("7E 50N"))

    def test_margins_solve_to_a_fit_good_to_a_few_pixels(self):
        import contextlib
        import io

        import sheet_towns as st
        rows = sheet(400, seed=3)
        fit = tf.Conic(rows)
        # the sheet's frame: meridians 2W..1E ticked where they meet the top edge (lat 50.3) and bottom (48.2),
        # parallels 49N, 49.5N, 50N where they meet the left edge (lon 2.2W) and right (1.3E)
        lines = []
        for lon in (-2, -1, 0, 1):
            for lat in (50.3, 48.2):
                x, y = fit.to_px([[lon, lat]])[0]
                lines.append(("lon", float(lon), float(x), float(y)))
        for lat in (49, 49.5, 50):
            for lon in (-2.2, 1.3):
                x, y = fit.to_px([[lon, lat]])[0]
                lines.append(("lat", float(lat), float(x), float(y)))
        with contextlib.redirect_stdout(io.StringIO()):
            seeds = st.conic_from_lines([], lines, n=fit.n)
        got = tf.Conic(seeds, n=fit.n)
        pts = [[-1.5, 49.2], [0.5, 50.1], [-0.3, 48.6]]
        self.assertLess(np.abs(got.to_px(pts) - fit.to_px(pts)).max(), 3)


class ConicFit(unittest.TestCase):
    def test_recovers_a_sheet_on_a_known_conic_both_ways(self):
        rows = sheet(40)
        fit = tf.Conic(rows)
        self.assertAlmostEqual(fit.n, tf.Conic.cone(45.0, 55.0), places=3)
        self.assertLess(fit.rms_px, 0.05)
        ll = fit.to_ll(fit.px)
        self.assertLess(np.abs(ll - fit.ll).max(), 1e-5)
        _res, loo = fit.residuals_km()
        self.assertLess(loo.max(), 0.01)

    def test_few_towns_take_the_usual_parallels_and_still_fit_locally(self):
        rows = [r for r in sheet(600, seed=2) if 6.4 <= float(r["lon"]) <= 8.0 and 50.1 <= float(r["lat"]) <= 51.1][:20]
        self.assertGreaterEqual(len(rows), 12)
        fit = tf.Conic(rows)
        self.assertAlmostEqual(fit.n, tf.Conic.cone(40.0, 56.0))
        self.assertLess(fit.rms_px, 0.5)   # the wrong parallels cost nothing over a degree or two

    def test_the_fit_follows_the_number_of_towns(self):
        self.assertIsInstance(tf.make_fit(sheet(20)), tf.Fit)
        self.assertIsInstance(tf.make_fit(sheet(tf.Conic.MIN)), tf.Conic)


if __name__ == "__main__":
    unittest.main(verbosity=1)
