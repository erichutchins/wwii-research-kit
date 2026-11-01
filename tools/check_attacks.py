# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
"""Check every patrol's attacks.csv (the attack data sheets' torpedo columns) against fire-control arithmetic.

Each torpedo's track angle follows from the other values typed on the same sheet:

    torpedo course = own course + gyro angle                  (mod 360)
    track          = torpedo course + 180 - target course     (mod 360; up to 180 is starboard, beyond it port)

A typed track that disagrees with this by more than a few degrees is a misreading to check on the scan, or the sheet's
own inconsistency (one target solution for a whole salvo, own course swinging while firing). Values are never
changed: a real disagreement on the sheet is kept as typed and explained in attack_sheets.yml's `note`.

A time typed with seconds, 1616-32, is the minute 1616 in positions.csv; a sheet typing no zone leaves `zone` blank
(the attack's row in positions.csv has it). Also checked: the columns, every `attack` joining a `source=attack` row's `ref` in the patrol's positions.csv, the
date and time against that row, and every attack having an attack_sheets.yml entry (and the reverse). And the
firing times and aims: each attack's rows type either `interval` (seconds since the torpedo before) or `since_first`
(seconds since the salvo's first), never both, and `since_first` never goes back within a salvo; `offset` is an aim
off the point of aim (`1.5R`, `0`, `225'Aft`, `MOT`) and `spread` the kind of spread (`divergent`), never an offset.

  uv run tools/check_attacks.py            every patrol; exits 1 on a structural problem
  uv run tools/check_attacks.py bang/2     one patrol, every torpedo
"""
import csv
import re
import sys

import records
from records import RECORDS, rel

COLUMNS = ("attack,date,time,zone,tube,own_course,own_speed,own_depth,target_course,target_speed,target_range,"
           "target_draft,track,gyro,depth_set,power,hit,erratic,torpedo,interval,since_first,spread,offset,page").split(",")
OFFSET = re.compile(r"(\d+(\.\d+)?[RL]?|MOT|\d+'\s*(aft|ahead|fwd))", re.I)
NEAR, FAR = 3, 10   # degrees: within NEAR agrees; beyond FAR is listed as a disagreement


def num(s):
    m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*", s or "")
    return float(m[1]) if m else None


def courses(s):
    """'050' -> [50]; own course swinging while firing, '050-069' -> [50, 69] (the arc between tried); a target's
    zig typed as '210 - 260' -> [210, 260] (each end tried)"""
    parts = (s or "").split("-")
    vals = [num(p) for p in parts]
    return vals if parts and all(v is not None for v in vals) else []


def gyro_of(s):
    """'162' -> 162; an angle typed right or left of the bow, '15R' -> 15, '5L' -> 355"""
    m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*([RL]?)\s*", s or "")
    if not m:
        return None
    return float(m[1]) if m[2] != "L" else (360 - float(m[1])) % 360


def track_of(own, gyro, target):
    """-> (degrees, 'S' or 'P')"""
    t = (own + gyro + 180 - target) % 360
    return (t, "S") if t <= 180 else (360 - t, "P")


def typed_track(s):
    """'62S' -> (62, 'S'); a track typed without its side, '111' -> (111, ''), compared by size only"""
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*([SP]?)", (s or "").strip())
    return (float(m[1]), m[2]) if m else None


def miss(row):
    """degrees between the typed track and the computed one (the closest over a swinging own course or a zig), or None"""
    want, gyro = typed_track(row["track"]), gyro_of(row["gyro"])
    owns, targets = courses(row["own_course"]), courses(row["target_course"])
    if not (want and gyro is not None and targets and owns):
        return None, None
    signed = lambda deg, side: deg if side == "S" else -deg
    best = None
    lo, hi = min(owns), max(owns)
    for own, target in ((o, t) for o in ([lo, hi] if lo == hi else [lo + (hi - lo) * i / 20 for i in range(21)])
                        for t in set(targets)):
        deg, side = track_of(own, gyro, target)
        d = abs(deg - want[0]) if not want[1] else abs(((signed(deg, side) - signed(*want)) + 180) % 360 - 180)
        if best is None or d < best[0]:
            best = (d, f"{deg:.1f}{side}")
    return best


def timing(path, rows):
    """interval or since_first, one per attack; since_first never back within a salvo (a 0 starts the next);
    offset an aim, spread a kind"""
    out = []
    for a in dict.fromkeys(r["attack"] for r in rows):
        rs = [r for r in rows if r["attack"] == a]
        if {k for r in rs for k in ("interval", "since_first") if r[k]} == {"interval", "since_first"}:
            out.append(f"{rel(path)}: {a} types both interval and since_first")
        last = None
        for r in rs:
            v = num(r["since_first"])
            if v is not None and last is not None and 0 < v < last:
                out.append(f"{rel(path)}: {a} tube {r['tube']}: since_first {r['since_first']} after {last:g}")
            last = v if v is not None else last
            if r["offset"] and not OFFSET.fullmatch(r["offset"]):
                out.append(f"{rel(path)}: {a} tube {r['tube']}: offset {r['offset']!r} is not an aim (1.5R, 0, 225'Aft)")
            if r["spread"] and OFFSET.fullmatch(r["spread"]):
                out.append(f"{rel(path)}: {a} tube {r['tube']}: spread {r['spread']!r} is an offset: it goes in `offset`")
    return out


def patrol(folder, verbose):
    path = folder / "attacks.csv"
    problems, far = [], []
    with open(path, encoding="utf-8", newline="") as f:
        rd = csv.DictReader(f)
        if rd.fieldnames != COLUMNS:
            return [f"{rel(path)}: columns are {rd.fieldnames}, want {COLUMNS}"], [], 0
        rows = list(rd)
    with open(folder / "positions.csv", encoding="utf-8", newline="") as f:
        attacks = {r["ref"]: r for r in csv.DictReader(f) if r["source"] == "attack"}
    sheets = folder / "attack_sheets.yml"
    named = {e.get("attack") for e in (records.load_yaml(sheets) or [])} if sheets.exists() else set()
    for n, r in enumerate(rows, 2):
        where = f"{rel(path)}:{n} ({r['attack']} tube {r['tube']})"
        if any("," in v or '"' in v for v in r.values()):
            problems.append(f"{where}: a cell with a comma or quote")
        a = attacks.get(r["attack"])
        if a is None:
            problems.append(f"{where}: no source=attack row with ref {r['attack']!r} in positions.csv")
        elif (r["date"], r["time"][:4]) != (a["date"], a["time"]) or r["zone"] not in ("", a["zone"]):
            far.append(f"{where}: {r['date']} {r['time']} {r['zone']}, positions.csv has {a['date']} {a['time']} {a['zone']}")
        if not re.fullmatch(r"rg\d+-\d+/p\d+", r["page"]):
            problems.append(f"{where}: page {r['page']!r}")
        d, got = miss(r)
        if d is None:
            if verbose:
                print(f"  {where}: track not computable (track {r['track']!r} gyro {r['gyro']!r} own {r['own_course']!r} target {r['target_course']!r})")
            continue
        flag = "" if d <= NEAR else (" CHECK" if d <= FAR else " DISAGREES")
        if verbose:
            print(f"  {r['attack']:>10} tube {r['tube']:>2}: typed {r['track']:>5}, computed {got:>6} ({d:.1f}°){flag}")
        if d > FAR:
            far.append(f"{where}: typed track {r['track']}, computed {got} from own {r['own_course']} + gyro {r['gyro']} vs target {r['target_course']}")
        elif d > NEAR and not verbose:
            far.append(f"{where}: typed track {r['track']}, computed {got} ({d:.1f}° off)")
    problems += timing(path, rows)
    for a in sorted({r["attack"] for r in rows} - named):
        problems.append(f"{rel(sheets)}: no entry for {a}")
    for a in sorted(named - {r["attack"] for r in rows}):
        problems.append(f"{rel(sheets)}: {a} has no rows in attacks.csv")
    return problems, far, len(rows)


def main():
    want = sys.argv[1] if len(sys.argv) > 1 else None
    folders = sorted(p.parent for p in RECORDS.glob("boats/*/patrol-*/attacks.csv"))
    if want:
        boat, n = want.split("/")
        folders = [f for f in folders if f.parent.name.endswith("-" + boat) and f.name == f"patrol-{n}"]
    problems, total = [], 0
    for folder in folders:
        p, far, n = patrol(folder, bool(want))
        total += n
        problems += p
        print(f"{rel(folder)}: {n} torpedoes" + (f", {len(far)} to look at" if far else ""))
        for x in far:
            print(f"  look: {x}")
    for x in problems:
        print(f"PROBLEM: {x}")
    print(f"{total} torpedoes in {len(folders)} patrols, {len(problems)} problems")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
