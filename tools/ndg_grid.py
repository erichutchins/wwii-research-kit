"""Convert a WWII "Nord de Guerre" grid reference (e.g. Y-888629) to latitude/longitude.

The 106th AAA's 1945 records give positions on the Central Europe 1/100,000
sheets as a 100 km square letter and an easting-northing (M-425325: square M,
42.5 km east, 32.5 km north). The grid is the French Lambert "Nord de Guerre"
projection, which the Allies used from eastern France into Bavaria:

  Clarke 1880 (IGN) ellipsoid; Lambert conformal conic, one standard parallel
  at 49.5 N (55 grad); central meridian 6 grad east of Paris (7.7372 E);
  scale 0.99950908; false easting 500 km, false northing 300 km.

The 100 km squares are lettered A-Z without I, five to a row, west to east,
from the north; in this 500 km block V is the square 400-500 km east and
100-200 km north. Checked against named towns in the reports (Rehaincourt
V-062744, Lauf O-567067, Altenfurt T-495955: each within 1 km).

Typists sometimes kept the old letter after crossing into the next square
(Gersfeld "N-550079" for H-550079); pass the corrected letter, and say so in
the data's note.

  python3 tools/ndg_grid.py Y-888629 T-685059
"""
import math
import re
import sys

A, F_ = 6378249.2, 1 / 293.4660213          # Clarke 1880 (IGN)
E_ = math.sqrt(2 * F_ - F_ * F_)
LAT0 = math.radians(49.5)
LON0 = math.radians(2.33722917 + 5.4)       # Paris + 6 grad
K0 = 0.99950908
LETTERS = "ABCDEFGHJKLMNOPQRSTUVWXYZ"


def _m(p):
    return math.cos(p) / math.sqrt(1 - (E_ * math.sin(p)) ** 2)


def _t(p):
    return math.tan(math.pi / 4 - p / 2) / ((1 - E_ * math.sin(p)) / (1 + E_ * math.sin(p))) ** (E_ / 2)


N_ = math.sin(LAT0)
FF = _m(LAT0) / (N_ * _t(LAT0) ** N_)
R0 = A * FF * _t(LAT0) ** N_ * K0


def to_latlon(easting, northing):
    """Lambert Nord de Guerre metres -> (lat, lon) in degrees."""
    x, y = easting - 500000, R0 - (northing - 300000)
    r = math.copysign(math.hypot(x, y), N_)
    tt = (r / (A * FF * K0)) ** (1 / N_)
    p = math.pi / 2 - 2 * math.atan(tt)
    for _ in range(10):
        p = math.pi / 2 - 2 * math.atan(tt * ((1 - E_ * math.sin(p)) / (1 + E_ * math.sin(p))) ** (E_ / 2))
    return math.degrees(p), math.degrees(math.atan2(x, y) / N_ + LON0)


def grid(ref):
    """'M-425325' / 'Q-8623' / 'M655298' -> (lat, lon). 4, 6 or 8 digits."""
    m = re.fullmatch(r"([A-HJ-Z])-?(\d{4}|\d{6}|\d{8})", ref.strip().upper().replace("Ø", "0"))
    if not m:
        raise ValueError(f"not a grid reference: {ref!r}")
    row, col = divmod(LETTERS.index(m[1]), 5)
    d = m[2]
    k = len(d) // 2
    unit = 10 ** (5 - k)                      # metres per last digit
    e = (400 + col * 100) * 1000 + int(d[:k]) * unit + unit / 2
    n = (500 - row * 100) * 1000 + int(d[k:]) * unit + unit / 2
    return to_latlon(e, n)


if __name__ == "__main__":
    for ref in sys.argv[1:]:
        lat, lon = grid(ref)
        print(f"{ref:12} {lat:.4f} {lon:.4f}")
