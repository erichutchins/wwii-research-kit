"""Where the tools find things, and how they name a boat or a ship.

  KIT        this kit (tools/, site/, reference/, guides/)
  RECORDS    the transcribed records: records/ (the wwii-unit-records repository), or
             wherever WWII_RECORDS points, so the tools can work on another dataset
  REFERENCE  reference tables (the Japanese kana grid keys and anchors)
  CACHE      downloaded scans and API caches (git-ignored, always re-downloadable):
             sources/ beside tools/, or wherever WWII_CACHE points

A boat (records/boats/<hull>-<name>/, war patrol reports, one patrol-N/ folder each) or a
ship (records/ships/<hull>-<name>/, a war diary, one positions.csv) is named by its folder,
`ss-385-bang`, or by the name alone, `bang`. A patrol is `<boat>/<n>`: `bang/1`,
`ss-384-parche/1`. Each has a hand-edited ship.yml (name, hull, class, speed limit, and the
map page's wording).
"""
import json
import os
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
RECORDS = Path(os.environ.get("WWII_RECORDS") or KIT / "records")
REFERENCE = KIT / "reference"
CACHE = Path(os.environ.get("WWII_CACHE") or KIT / "sources")


def load_yaml(path):
    import yaml  # PyYAML; the scripts that read YAML declare it for `uv run`
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def vessels():
    """Every boat and ship folder, boats first."""
    return [d for kind in ("boats", "ships") if (RECORDS / kind).is_dir()
            for d in sorted((RECORDS / kind).iterdir()) if (d / "ship.yml").exists()]


def vessel_dir(key):
    """'bang' or 'ss-385-bang' -> records/boats/ss-385-bang"""
    for d in vessels():
        if d.name == key or d.name.endswith("-" + key):
            return d
    raise SystemExit(f"no boat or ship named {key!r} under {RECORDS} (folders with a ship.yml)")


def ship(key):
    """The vessel's ship.yml, plus its folder."""
    d = vessel_dir(key)
    return {**load_yaml(d / "ship.yml"), "dir": d}


def patrols(key):
    """A boat's patrol numbers, from its patrol-N folders; [] for a ship's single record."""
    return sorted(int(p.name.split("-")[1]) for p in vessel_dir(key).glob("patrol-*"))


def units(key=None):
    """Track units: 'ss-385-bang/1' ... for a boat's patrols, 'dd-700-haynsworth' for a ship;
    every vessel's when key is None. A ship with no positions.csv yet (only a ship.yml) has none."""
    keys = [d.name for d in vessels()] if key is None else [vessel_dir(key).name]
    out = []
    for k in keys:
        ns = patrols(k)
        out += [f"{k}/{n}" for n in ns] if ns else [k] if (vessel_dir(k) / "positions.csv").exists() else []
    return out


def unit_dir(unit):
    """'bang/1' -> records/boats/ss-385-bang/patrol-1; 'haynsworth' -> records/ships/dd-700-haynsworth"""
    key, _, n = str(unit).partition("/")
    d = vessel_dir(key)
    return d / f"patrol-{n}" if n else d


def rel(path):
    """A path for printing: relative to the records or the kit when inside them."""
    path = Path(path).resolve()
    for base in (RECORDS.resolve().parent, KIT.resolve().parent):
        if path.is_relative_to(base):
            return str(path.relative_to(base))
    return str(path)


def write_json(path, obj, **kw):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, **kw)
