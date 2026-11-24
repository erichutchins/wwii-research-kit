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
    """One part as a subpath, always wound the same way as a box (clockwise on the page), so a nonzero fill draws
    overlapping parts (a mast over the hull) as one shape and never punches a hole."""
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, list(pts[1:]) + list(pts[:1])))
    if area > 0:
        pts = list(pts)[::-1]
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
    for group in ("aircraft", "ships", "vehicles"):
        for k, s in y[group].items():
            missing = [x for x in s.get("sources", []) if x not in sources] or ([] if s.get("sources") else ["(none)"])
            if missing:
                raise SystemExit(f"{group}.{k}: sources {missing} not in SOURCES.yml")
    # `crop` (the traced section of the plate's scan) is for finding and retracing, not for the pages: left out
    out = {"categories": y["categories"],
           "aircraft": {k: {f: v for f, v in a.items() if f != "crop"} for k, a in y["aircraft"].items()},
           "ships": {k: {**{f: v for f, v in s.items() if f != "crop"}, "d": ship_path(s["parts"])}
                     for k, s in y["ships"].items()},
           # vehicles: side views in feet, rear at x = 0, the ground at y = 0, drawn as ships are
           "vehicles": {k: {**{f: v for f, v in s.items() if f != "crop"}, "d": ship_path(s["parts"])}
                        for k, s in y.get("vehicles", {}).items()}}
    records.write_json(DIR / "silhouettes.json", out, separators=(",", ":"), ensure_ascii=False)
    print(f"wrote {rel(DIR / 'silhouettes.json')}: {len(out['categories']['shapes'])} categories, "
          f"{len(out['aircraft'])} aircraft, {len(out['ships'])} ships, {len(out['vehicles'])} vehicles")


if __name__ == "__main__":
    main()
