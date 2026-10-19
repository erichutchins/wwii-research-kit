# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
"""Build records/silhouettes/silhouettes.json for the pages from silhouettes.yml (hand-edited).

Categories and aircraft views are copied as they are; each ship's parts become one SVG path, `d`,
in feet with y flipped for SVG (above the waterline is negative). Every shape must cite a
SOURCES.yml entry; tools/check_sources.py checks that too.

Usage: uv run tools/build_silhouettes.py
"""
import math

import records
from records import RECORDS, rel

DIR = RECORDS / "silhouettes"


def f(n):
    """A coordinate as the pages print it: one decimal, rounded half up, no trailing .0."""
    v = math.floor(n * 10 + 0.5) / 10
    return str(int(v)) if v == int(v) else str(v)


def poly(pts):
    return "M" + "L".join(f"{f(x)},{f(-y)}" for x, y in pts) + "Z"


def ship_path(parts):
    """[box, x0, x1, top, base] | [poly, [[x, y], ...]] | [mast, x, top, base, w] | [gun, x0, x1, y, h] -> SVG path"""
    out = []
    for p in parts:
        kind, *a = p
        if kind == "poly":
            out.append(poly(a[0]))
        elif kind == "box":
            x0, x1, top, base = (a + [0])[:4]
            out.append(poly([[x0, base], [x0, top], [x1, top], [x1, base]]))
        elif kind == "gun":
            x0, x1, y, h = (a + [1.4])[:4]
            out.append(poly([[x0, y], [x0, y + h], [x1, y + h], [x1, y]]))
        elif kind == "mast":
            x, top, base, w = (a + [1.6])[:4]
            out.append(poly([[x - w / 2, base], [x - w / 2, top], [x + w / 2, top], [x + w / 2, base]]))
        else:
            raise SystemExit(f"unknown part {kind!r}")
    return " ".join(out)


def main():
    y = records.load_yaml(DIR / "silhouettes.yml")
    sources = records.load_yaml(RECORDS / "SOURCES.yml")
    for group in ("aircraft", "ships"):
        for k, s in y[group].items():
            missing = [x for x in s.get("sources", []) if x not in sources] or ([] if s.get("sources") else ["(none)"])
            if missing:
                raise SystemExit(f"{group}.{k}: sources {missing} not in SOURCES.yml")
    out = {"categories": y["categories"], "aircraft": y["aircraft"],
           "ships": {k: {**s, "d": ship_path(s["parts"])} for k, s in y["ships"].items()}}
    records.write_json(DIR / "silhouettes.json", out, separators=(",", ":"), ensure_ascii=False)
    print(f"wrote {rel(DIR / 'silhouettes.json')}: {len(out['categories']['shapes'])} categories, "
          f"{len(out['aircraft'])} aircraft, {len(out['ships'])} ships")


if __name__ == "__main__":
    main()
