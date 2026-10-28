"""Convert a WWII grid reference on any of the six grids the Army records use to latitude/longitude.

Which grid a reference is on is in the data (`grid_on` in records/army/stations.csv and
actions.csv), worked out by decoding every reference on every grid and checking it
against the town the same entry names (grids.html shows the checks):

  italy-s   South Italy Zone (British "Modified British System"). Lambert, Bessel 1841,
            origin 39.5 N 14 E, scale 0.99906, false E 700 km, N 600 km. 500 km squares
            lettered VWXYZ / QRSTU / LMNOP / FGHJK / ABCDE from the south-west, written
            lower case ("rN"); 100 km squares A-Z without I, five a row from the north-west.
            A reference with one letter is in square r, where all of these fall.
  italy-n   North Italy Zone. Lambert, Bessel 1841, origin 45.9 N 14 E, scale 0.9989, false
            E 800 km, N 601 km (sigterritoires.fr; reproduces Camerata Picena 477434 to 100 m).
            Its 100 km letters sit in a 500 km block ("w") from 500 km E, 200 km N: the
            Bologna sheets' index has M at 600-700 E, 400-500 N.
  lambert3  French Lambert Zone III (Sud). Clarke 1880 (IGN), origin 44.1 N (49 grad) on the
            Paris meridian, scale 0.9998775, false E 600 km, N 200 km.
  lambert2  Lambert Zone II (Centre): origin 46.8 N (52 grad), scale 0.99987742, same false
            origin. Both zones' 100 km letters fit one 500 km block from 500 km E, 0 km N.
  lambert1  Lambert Zone I (Nord): origin 49.5 N (55 grad), scale 0.99987734, same false
            origin. Its 100 km letters sit in a block from 0 km E, 0 km N, lettered V
            (Normandy, June-July 1944: Co. B, 313th Infantry typed "VT 1099" at Le Valdecie).
  nwa       British "North West Africa" Grid (Tunisia, Algeria, Morocco, 1942-43). Lambert, Clarke 1880,
            origin 34 N on the Greenwich meridian, false E 1,000 km, N 500 km, metres, as printed on AMS
            "Alger and vicinity" (1942) sheet 3 of 7 (princeton-amsalger); scale 0.9994 from sigterritoires.fr.
            The 100 km letters, A-Z without I, five a row from the north-west, repeat in every 500 km block
            from 0 km N: give a town, and the block nearest it is used. Fixed by the same sheet's worked
            example, Mon Rouge (Algiers) = H743072 (block from 1000 km E, 500 km N; full northing 807 km, as
            the sheet's small figures say), and Battery C, 62nd CA's July 1943 J references at Lake Bizerte
            (the next block east). Whether a block letter was ever prefixed is not known.
  ndg       Lambert "Nord de Guerre" (tools/ndg_grid.py): letters in the block from
            400 km E, 100 km N.
  ndg-w     The same grid's western block, from -100 km E, 100 km N (lettered V: the 894th AAA medical detachment's
            detachment typed "VZ-6457" at Contrexeville).

A reference with no square letter ("518247", "591564 Sheet 271-IV") can't say which 100 km
square it is in. Given `near` (a town the entry names) it is put in the square nearest that
town, and the result says so.

  python3 tools/grid_ref.py ndg V-044572 italy-s "RN 25" lambert2 J-762365
"""
import math
import re
import sys

ELLIPSOIDS = {"clarke1880": (6378249.2, 1 / 293.4660213), "bessel": (6377397.155, 1 / 299.1528128)}
PARIS = 2.33722917
MINOR = "ABCDEFGHJKLMNOPQRSTUVWXYZ"
MAJOR = "VWXYZQRSTULMNOPFGHJKABCDE"

# name, ellipsoid, lat0, lon0, k0, false easting, false northing, 100 km letter block (SW corner) or
# "major", and the block's own letter if references may carry it
GRIDS = {
    "italy-s":  ("South Italy Zone", "bessel", 39.5, 14.0, 0.99906, 700000, 600000, "major", None),
    "italy-n":  ("North Italy Zone", "bessel", 45.9, 14.0, 0.9989, 800000, 601000, (500000, 200000), "W"),
    "lambert1": ("Lambert Zone I", "clarke1880", 49.5, PARIS, 0.99987734, 600000, 200000, (0, 0), "V"),
    "lambert3": ("Lambert Zone III", "clarke1880", 44.1, PARIS, 0.99987750, 600000, 200000, (500000, 0), None),
    "lambert2": ("Lambert Zone II", "clarke1880", 46.8, PARIS, 0.99987742, 600000, 200000, (500000, 0), None),
    "nwa":      ("British N.W. Africa Grid", "clarke1880", 34.0, 0.0, 0.9994, 1000000, 500000, "repeat", None),
    "ndg":      ("Nord de Guerre", "clarke1880", 49.5, PARIS + 5.4, 0.99950908, 500000, 300000, (400000, 100000), None),
    "ndg-w":    ("Nord de Guerre (western block)", "clarke1880", 49.5, PARIS + 5.4, 0.99950908, 500000, 300000, (-100000, 100000), "V"),
}


class Lambert:
    """Lambert conformal conic with one standard parallel, on an ellipsoid."""

    def __init__(self, ell, lat0, lon0, k0, fe, fn):
        a, f = ELLIPSOIDS[ell]
        self.a, self.e, self.lon0, self.k0, self.fe, self.fn = a, math.sqrt(2 * f - f * f), lon0, k0, fe, fn
        p0 = math.radians(lat0)
        self.n = math.sin(p0)
        self.F = self._m(p0) / (self.n * self._t(p0) ** self.n)
        self.r0 = a * self.F * self._t(p0) ** self.n * k0

    def _m(self, p):
        return math.cos(p) / math.sqrt(1 - (self.e * math.sin(p)) ** 2)

    def _t(self, p):
        e = self.e
        return math.tan(math.pi / 4 - p / 2) / ((1 - e * math.sin(p)) / (1 + e * math.sin(p))) ** (e / 2)

    def fwd(self, lat, lon):
        r = self.a * self.F * self._t(math.radians(lat)) ** self.n * self.k0
        th = self.n * math.radians(lon - self.lon0)
        return self.fe + r * math.sin(th), self.fn + self.r0 - r * math.cos(th)

    def inv(self, x, y):
        e, dx, dy = self.e, x - self.fe, self.r0 - (y - self.fn)
        tt = (math.copysign(math.hypot(dx, dy), self.n) / (self.a * self.F * self.k0)) ** (1 / self.n)
        p = math.pi / 2 - 2 * math.atan(tt)
        for _ in range(10):
            p = math.pi / 2 - 2 * math.atan(tt * ((1 - e * math.sin(p)) / (1 + e * math.sin(p))) ** (e / 2))
        return math.degrees(p), math.degrees(math.atan2(dx, dy) / self.n) + self.lon0


PROJ = {k: Lambert(*g[1:7]) for k, g in GRIDS.items()}


def parse(ref):
    """'M-425325' / 'rN 25' / 'Q9435' / '591564 Sheet 271-IV' -> (letters, digits)."""
    s = ref.strip().upper().replace("Ø", "0")
    s = re.sub(r"\s+SHEET\b.*$", "", s)
    m = re.fullmatch(r"([A-Z]{0,2})[-\s]?(\d{2}|\d{4}|\d{6}|\d{8})", s)
    if not m:
        raise ValueError(f"not a grid reference: {ref!r}")
    return m[1], m[2]


def square_origin(system, letter, major):
    g = GRIDS[system]
    i = MINOR.index(letter)
    row, col = divmod(i, 5)
    if g[7] == "repeat":   # the letters repeat in every 500 km block; decode() picks the block nearest the town
        return col * 100000, (4 - row) * 100000
    if g[7] == "major":
        j = MAJOR.index(major or "R")
        return (j % 5) * 500000 + col * 100000, (j // 5) * 500000 + (4 - row) * 100000
    if major and major != g[8]:
        raise ValueError(f"{system} has no 500 km square {major}")
    e0, n0 = g[7]
    return e0 + col * 100000, n0 + (4 - row) * 100000


def decode(system, ref, near=None):
    """-> dict(lat, lon, cell (metres per last digit), inferred (no square letter typed))."""
    letters, d = parse(ref)
    k = len(d) // 2
    unit = 10 ** (5 - k)
    dx, dy = int(d[:k]) * unit + unit / 2, int(d[k:]) * unit + unit / 2
    proj = PROJ[system]
    if letters:
        if letters[-1] not in MINOR:
            raise ValueError(f"no 100 km square {letters[-1]}")
        x0, y0 = square_origin(system, letters[-1], letters[0] if len(letters) == 2 else None)
        x, y = x0 + dx, y0 + dy
        if GRIDS[system][7] == "repeat":
            if near is None:
                raise ValueError(f"{system}: square letters repeat every 500 km; give a town near {ref!r}")
            tx, ty = proj.fwd(*near)
            x, y = min(((x + i * 500000, y + j * 500000) for i in range(-1, 6) for j in range(-1, 3)),
                       key=lambda c: math.hypot(c[0] - tx, c[1] - ty))
    else:
        if near is None:
            raise ValueError(f"{ref!r} has no square letter; give a town near it")
        x, y = _nearest(*proj.fwd(*near), dx, dy)
    lat, lon = proj.inv(x, y)
    return {"lat": lat, "lon": lon, "cell": unit, "inferred": not letters}


def _nearest(tx, ty, dx, dy):
    """The point (square origin + dx, dy) nearest (tx, ty), over the town's square and its neighbours."""
    cands = [((math.floor(tx / 1e5) + i) * 1e5 + dx, (math.floor(ty / 1e5) + j) * 1e5 + dy)
             for i in (-1, 0, 1) for j in (-1, 0, 1)]
    return min(cands, key=lambda c: math.hypot(c[0] - tx, c[1] - ty))


if __name__ == "__main__":
    args = sys.argv[1:]
    for system, ref in zip(args[::2], args[1::2]):
        r = decode(system, ref)
        print(f"{GRIDS[system][0]:32} {ref:12} {r['lat']:.4f} {r['lon']:.4f}  (to {r['cell']} m)")
