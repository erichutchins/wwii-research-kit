# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
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

# What a source in records/SOURCES.yml is (its `kind`, required on every entry; guides/OPERATIONS-VIEWER.md 2.4). Here,
# once, because check_sources.py refuses an entry outside it and the builds tag every row with its source's kind
# through its citation (build_engagement.py: `source_kind`).
SOURCE_KINDS = {
    "record",         # written at the time by the subject or its command: patrol reports, war diaries, morning reports
    "intelligence",   # what one side knew of the other at the time: the FRUPAC overlays
    "press",          # published at the time: a newspaper, a communiqué, a bulletin
    "assessment",     # an official reckoning after the fact: JANAC, an order of battle compiled by the theater historian
    "recollection",   # told later by someone who was there: a memoir, an interview, a crew's association
    "secondary",      # a later history or site, repeating records we haven't seen
    "reference",      # not a witness: charts, plates, grids, manuals, gazetteers, datasets
    "derived",        # a method, not an outside source: a position worked out from a grid reference
}


def load_yaml(path):
    """Load a records YAML file, refusing a key given twice in one mapping: PyYAML would keep the last silently, but
    the pages' js-yaml rejects the whole file, so a duplicate breaks the site while every tool still passes."""
    with open(path, encoding="utf-8") as f:
        return load_yaml_text(f.read(), path)


def load_yaml_text(text, path="<text>"):
    """load_yaml for YAML already read, e.g. a Markdown file's front matter; `path` names it in errors."""
    import yaml  # PyYAML; the scripts that read YAML declare it for `uv run`
    from yaml.constructor import ConstructorError
    from yaml.resolver import BaseResolver

    class Strict(yaml.SafeLoader):
        pass

    def mapping(loader, node, deep=False):
        seen = set()
        for k, _ in node.value:
            key = loader.construct_object(k, deep=deep)
            if key in seen:
                raise ConstructorError(None, None, f"duplicate key {key!r} in {path}", k.start_mark)
            seen.add(key)
        return yaml.SafeLoader.construct_mapping(loader, node, deep)

    Strict.add_constructor(BaseResolver.DEFAULT_MAPPING_TAG, mapping)
    return yaml.load(text, Loader=Strict)


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
