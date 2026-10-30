"""Decode Kriegsmarine naval grid squares (Marinequadrate) in the Mediterranean, e.g. "CJ 9472".

The code is two letters (a large square, Großquadrat) and up to four digits. The first digit is a
3x3 block of the large square and each further digit a 3x3 split of the one before, numbered like a
telephone keypad (1 NW, 2 N, 3 NE, 4 W, 5 centre, 6 E, 7 SW, 8 S, 9 SE). Two digits ("CJ 94") are
the squares printed on the chart, 54' of latitude high; four digits are the ~6 nm cell. A digit 0
means "not given" and the code is decoded to the level above it.

In the Mediterranean the large squares are not all regular (CH and CJ follow the coasts), so the
blocks are read from wartime charts: reference/naval-grid/squares.csv, one row per block (square +
first digit) with its edges and how they were obtained (guides/NAVAL-GRID.md). Inside a block the
split is regular: two-digit squares 54' x 72', third digit 18' x 24', fourth 6' x 8' (the chart's
lattice in this band, measured on NARA T-1022 roll 2099 frame 200; the 8' columns re-measured from 17°18'E to
about 38°E on frames 74 and 91; the rows from 28°44' to 39°48'N at about 39°E on frame 348). The lattice holds south of 45°36'N only: north of it (BH, BJ) the columns are 10'
wide (frame 74), so a square there needs its own cell width before it is added to squares.csv.

  python3 tools/naval_grid.py decode "CJ 9472"     the cell's corners and centre
  python3 tools/naval_grid.py check                anchors.csv: decoded position against the place named
  python3 tools/naval_grid.py blocks               the blocks digitized so far
"""
import csv
import math
import re
import sys

from records import REFERENCE  # noqa: E402

DATA = REFERENCE / "naval-grid"
ROW, COL = 54, 72  # minutes: a two-digit square's height and width


def minutes(text):
    """'40-12N' -> 2412; S and W negative."""
    d, m = text[:-1].split("-")
    v = int(d) * 60 + int(m)
    return -v if text[-1] in "SW" else v


def dm(v, pos, neg):
    a = abs(v)
    return f"{int(a // 60)}-{a % 60:04.1f}{pos if v >= 0 else neg}".replace(".0", "")


def load_blocks():
    with open(DATA / "squares.csv", encoding="utf-8") as f:
        return {(r["square"], r["block"]): r for r in csv.DictReader(f)}


def parse(code):
    m = re.fullmatch(r"\s*([A-Z]{2})\s*([0-9]{1,4})\s*", code.upper())
    if not m:
        raise ValueError(f"{code!r}: expected two letters and 1-4 digits, e.g. 'CJ 9472'")
    digits = m.group(2).rstrip("0")
    if "0" in digits:
        raise ValueError(f"{code!r}: a 0 before a non-zero digit is not a keypad position")
    return m.group(1), digits


def decode(code, blocks):
    """(north, south, west, east) in minutes, the block row and the digits used."""
    sq, digits = parse(code)
    if not digits:
        raise ValueError(f"{code!r}: a large square alone is not decoded (its outline is irregular here)")
    blk = blocks.get((sq, digits[0]))
    if blk is None:
        known = sorted({s for s, _ in blocks})
        raise LookupError(f"{sq} {digits[0]}: not digitized (large squares so far: {', '.join(known)}; "
                          f"see guides/NAVAL-GRID.md)")
    if len(digits) > 1 and digits[1] not in blk["present"]:
        raise LookupError(f"{sq} {digits[:2]}: not on the chart (block {sq} {digits[0]} has only "
                          f"{', '.join(digits[0] + d for d in blk['present'])})")
    n, w = minutes(blk["lat_n"]), minutes(blk["lon_w"])
    h, wd = 3 * ROW, 3 * COL
    for d in digits[1:]:
        k = int(d) - 1
        h, wd = h / 3, wd / 3
        n -= (k // 3) * h
        w += (k % 3) * wd
    return n, n - h, w, w + wd, blk, digits


def describe(code, blocks):
    n, s, w, e, blk, digits = decode(code, blocks)
    lat, lon = (n + s) / 2, (w + e) / 2
    size = f"{(n - s):g}' x {(e - w):g}'"
    return (f"{code}: {dm(s, 'N', 'S')} to {dm(n, 'N', 'S')}, {dm(w, 'E', 'W')} to {dm(e, 'E', 'W')} ({size}); "
            f"centre {dm(lat, 'N', 'S')} {dm(lon, 'E', 'W')} = {lat / 60:.3f}, {lon / 60:.3f}  "
            f"[block {blk['square']} {blk['block']}: {blk['method']}]")


def nm(lat1, lon1, lat2, lon2):
    """Distance in nautical miles (degrees in), on a sphere."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    c = math.sin(p1) * math.sin(p2) + math.cos(p1) * math.cos(p2) * math.cos(dl)
    return math.degrees(math.acos(max(-1, min(1, c)))) * 60


def check(blocks):
    bad = 0
    with open(DATA / "anchors.csv", encoding="utf-8") as f:
        for a in csv.DictReader(f):
            try:
                n, s, w, e, blk, _ = decode(a["code"], blocks)
            except (ValueError, LookupError) as err:
                print(f"{a['id']:4} {a['code']:9} {err}")
                bad += 1
                continue
            lat, lon = (n + s) / 120, (w + e) / 120
            line = f"{a['id']:4} {a['code']:9} decoded {lat:.3f} {lon:.3f}"
            if a["lat"]:
                err = nm(lat, lon, float(a["lat"]), float(a["lon"]))
                line += f"  expected {float(a['lat']):.3f} {float(a['lon']):.3f}  {err:5.1f} nm  ({a['kind']})"
                if a["error_nm"] and abs(err - float(a["error_nm"])) > 0.5:
                    line += f"  [anchors.csv says {a['error_nm']} nm: update it]"
                    bad += 1
            else:
                line += f"  (no position stated: {a['kind']})"
            print(line)
    return bad


def main(argv):
    blocks = load_blocks()
    cmd = argv[0] if argv else ""
    try:
        if cmd == "decode" and len(argv) > 1:
            bad = 0
            for code in argv[1:]:
                try:
                    print(describe(code, blocks))
                except (ValueError, LookupError) as err:
                    print(err)
                    bad += 1
            sys.exit(1 if bad else 0)
        elif cmd == "check":
            sys.exit(1 if check(blocks) else 0)
        elif cmd == "blocks":
            for b in blocks.values():
                print(f"{b['square']} {b['block']}  {b['lat_s']} to {b['lat_n']}  {b['lon_w']} to {b['lon_e']}  "
                      f"{b['method']:8} {b['frames']}")
        else:
            sys.exit(__doc__)
    except (ValueError, LookupError) as err:
        sys.exit(str(err))


if __name__ == "__main__":
    main(sys.argv[1:])
