"""Decode the Imperial Japanese Navy's kana position codes (地点符号), 1944-45.

Aircraft contact reports give positions as four characters, e.g. 「メキ三ツ」:
column kana, row kana, then a digit and a kana that place the point inside
the square. The first two kana name a 20' x 20' square on whole-degree
boundaries (戦史叢書 vol. 56, fig. 34 draws one). The kana for each column and
row are a scrambled alphabet that depends on the key in force, so each key is
rebuilt letter by letter from anchors: codes whose position is known some
other way. How the digit and last kana subdivide the square is not yet known.

Keys and anchors are hand-edited in reference/jgrid/ (columns in guides/JAPANESE-GRID.md).

  python3 tools/jgrid.py decode メキ三ツ [--key okinawa-1945 | leyte-1944 | formosa-1944]
  python3 tools/jgrid.py check          anchors vs. the key: inside their square, and where in it?
  python3 tools/jgrid.py key [KEY]      the letters known so far
"""
import csv
import math
import sys
from pathlib import Path

from records import REFERENCE  # noqa: E402

DATA = REFERENCE / "jgrid"
SIDE = 1 / 3  # degrees: 20 minutes


def deg(text):
    """'129-40E' -> 129.667; S and W negative."""
    d, m = text[:-1].split("-")
    v = int(d) + int(m) / 60
    return -v if text[-1] in "SW" else v


def dm(v, pos, neg):
    v_abs = abs(v) + 1e-9
    return f"{int(v_abs)}-{round(v_abs % 1 * 60):02d}{pos if v >= 0 else neg}"


def load_keys():
    keys = {}
    with open(DATA / "keys.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            keys.setdefault(r["key"], {"col": {}, "row": {}})[r["axis"]][r["letter"]] = r
    return keys


def decode(code, key):
    """(south, north, west, east, notes) for the code's square; None edges if a letter is unknown."""
    col, row = key["col"].get(code[0]), key["row"].get(code[1]) if len(code) > 1 else None
    notes = []
    w = e = s = n = None
    if col:
        w = deg(col["edge"]); e = w + SIDE
        notes.append(f"column {code[0]} ({col['confidence']})")
    else:
        notes.append(f"column {code[0]} not in key")
    if row:
        s = deg(row["edge"]); n = s + SIDE
        notes.append(f"row {code[1]} ({row['confidence']})")
    else:
        notes.append(f"row {code[1:2]} not in key")
    return s, n, w, e, notes


def describe(code, keyname, keys):
    s, n, w, e, notes = decode(code, keys[keyname])
    lat = f"{dm(s, 'N', 'S')} to {dm(n, 'N', 'S')}" if s is not None else "lat ?"
    lon = f"{dm(w, 'E', 'W')} to {dm(e, 'E', 'W')}" if w is not None else "lon ?"
    centre = (f"; centre {dm((s + n) / 2, 'N', 'S')} {dm((w + e) / 2, 'E', 'W')}"
              if s is not None and w is not None else "")
    return f"{code} [{keyname}]: {lat}, {lon}{centre}  ({'; '.join(notes)}; subdivision {code[2:] or '-'} not decoded)"


def check(keys):
    bad = 0
    with open(DATA / "anchors.csv", encoding="utf-8") as f:
        for a in csv.DictReader(f):
            if not a["lat"] or a["key"] not in keys or " or " in a["code"]:
                print(f"{a['id']:4} {a['code']:10} skipped (no position, or ambiguous code)")
                continue
            s, n, w, e, notes = decode(a["code"], keys[a["key"]])
            lat, lon = float(a["lat"]), float(a["lon"])
            if s is None or w is None:
                print(f"{a['id']:4} {a['code']:10} {'; '.join(x for x in notes if 'not in key' in x)}")
                continue
            dlat = max(s - lat, 0, lat - n) * 60
            dlon = max(w - lon, 0, lon - e) * 60 * math.cos(math.radians(lat))
            off = math.hypot(dlat, dlon)
            bad += off > 10
            where = f"{(lon - w) / SIDE:.2f} E, {(lat - s) / SIDE:.2f} N of SW corner"  # for the subdivision
            print(f"{a['id']:4} {a['code']:10} {'inside' if off == 0 else f'{off:.0f} nm outside'}  ({where})")
    return bad


def main(argv):
    keys = load_keys()
    cmd = argv[0] if argv else ""
    keyname = argv[argv.index("--key") + 1] if "--key" in argv else "okinawa-1945"
    if cmd == "decode" and len(argv) > 1:
        print(describe(argv[1], keyname, keys))
    elif cmd == "check":
        sys.exit(1 if check(keys) else 0)
    elif cmd == "key":
        for name in ([argv[1]] if len(argv) > 1 else keys):
            for axis in ("col", "row"):
                for letter, r in sorted(keys[name][axis].items(), key=lambda kv: deg(kv[1]["edge"])):
                    print(f"{name} {axis} {letter} from {r['edge']} ({r['confidence']})")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
