# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
"""Bundle a submarine engagement into records/battles/<id>.json for site/battle.html?e=<id>.

An engagement is one convoy action, or a pack's run of them, from one or more
boats' war patrol reports beside the Japanese record. Each has a folder,
records/engagements/<id>/, holding the hand-edited parts:

  engagement.yml   title, boats (each with her patrol, as bang/1), the actions
                   (GMT windows, convoy, ships, escorts, outcome), place names
                   for the map, and the page's notes. Fields: guides/BATTLES.md.
  notes.csv        optional narrative log entries read from the scans:
                   boat,date,time,zone,text,page (time and zone as typed)

Everything else comes from the patrol folders the boats name: positions.csv
(attacks, fixes, sightings), depths.csv where transcribed (depth charges and
deep dives), and, for the folders listed in "japanese", japanese.csv and
crossrefs.json. Coastline is Natural Earth 10m land, clipped and embedded; it
is downloaded once to the cache (sources/naturalearth/).

Usage: uv run tools/build_battle.py                  every engagement -> records/battles/
       uv run tools/build_battle.py <id>             one engagement
       uv run tools/build_battle.py [<id>] --standalone OUT.html
              also a single-file copy of battle.html with that engagement inlined
              (with no id: every engagement, chosen by OUT.html#<id> or the picker)
       uv run tools/build_battle.py new <id> <patrol> [<patrol> ...]
              draft records/engagements/<id>/engagement.yml from the patrols'
              attacks and Japanese records, to finish by hand

Run check_track.py and check_crossrefs.py first: this reads their inputs and
crossrefs.json.
"""
import csv
import json
import sys
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

import records
from check_crossrefs import load_japanese
from check_track import load, patrol_dir, to_utc
from records import KIT, RECORDS, rel

LAND_URL = "https://cdn.jsdelivr.net/npm/world-atlas@2.0.2/land-10m.json"
land_path = records.CACHE / "naturalearth" / "land-10m.json"
ENGAGEMENTS = RECORDS / "engagements"
OUT = RECORDS / "battles"
SCANS = json.load(open(RECORDS / "scans.json"))
MAX_BOATS = 3  # the page's categorical colours are checked for three boats; check again before adding a fourth

# Silhouette categories drawn on the page: records/silhouettes/silhouettes.yml. Merchant ships are all drawn as a
# generic cargo ship and escorts by kind; none is any one ship's own plan. Each engagement carries the shapes.
SILHOUETTES = records.load_yaml(RECORDS / "silhouettes" / "silhouettes.yml")["categories"]
SIL_TYPES = set(SILHOUETTES["shapes"])
SIL_NOTE = SILHOUETTES["note"]


def iso(t):
    return f"{t:%Y-%m-%dT%H:%MZ}"


def parse_iso(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%MZ")


def scan_url(page):
    return SCANS.get(page, "")


def boat_from_folder(patrol):
    """'bang/1' or 'ss-385-bang/1' -> BANG patrol 1, named from her ship.yml."""
    d = patrol_dir(patrol)
    y = records.load_yaml(d.parent / "ship.yml")
    unit = f"{d.parent.name}/{d.name.split('-')[1]}"
    return {"id": y["name"].lower(), "name": y["name"], "hull": y["hull"], "co": "", "patrol": unit, "patrol_no": int(d.name.split("-")[1])}


def fix_out(boat, r):
    return {"boat": boat, "utc": iso(r["utc"]), "lat": round(r["lat"], 4), "lon": round(r["lon"], 4),
            "kind": r["source"], "ref": r["ref"], "on_track": r["on_track"] == "yes",
            "local": f"{r['date_fix'] or r['date']} {r['time_fix'] or r['time']} ({r['zone']})",
            "raw": f"{r['lat_raw']} {r['lon_raw']}", "note": r["note"], "fix": r["fix_note"],
            "page": r["page"], "scan": scan_url(r["page"])}


def decode_land(path, box):
    """TopoJSON land -> list of rings ([lon, lat]) that touch the box."""
    topo = json.load(open(path))
    sx, sy = topo["transform"]["scale"]
    tx, ty = topo["transform"]["translate"]
    arcs = []
    for arc in topo["arcs"]:
        x = y = 0
        pts = []
        for dx, dy in arc:
            x += dx
            y += dy
            pts.append((x * sx + tx, y * sy + ty))
        arcs.append(pts)

    def arc_pts(i):
        return arcs[i] if i >= 0 else arcs[~i][::-1]

    w, s, e, n = box
    rings = []
    for geom in topo["objects"]["land"]["geometries"]:
        polys = geom["arcs"] if geom["type"] == "MultiPolygon" else [geom["arcs"]]
        for poly in polys:
            for ring in poly:
                pts = []
                for i in ring:
                    seg = arc_pts(i)
                    pts.extend(seg if not pts else seg[1:])
                clipped = clip(pts, box)
                if len(clipped) >= 3:
                    rings.append([[round(x, 3), round(y, 3)] for x, y in clipped])
    return rings


def simplify(ring, tol):
    """Douglas-Peucker on a closed ring (lon/lat), for the small locator map."""
    def dp(pts):
        if len(pts) < 3:
            return pts
        (x0, y0), (x1, y1) = pts[0], pts[-1]
        dx, dy = x1 - x0, y1 - y0
        norm = (dx * dx + dy * dy) ** 0.5 or 1e-12
        i, dmax = 0, 0
        for k in range(1, len(pts) - 1):
            d = abs(dy * (pts[k][0] - x0) - dx * (pts[k][1] - y0)) / norm
            if d > dmax:
                i, dmax = k, d
        return dp(pts[:i + 1])[:-1] + dp(pts[i:]) if dmax > tol else [pts[0], pts[-1]]
    half = len(ring) // 2
    out = dp(ring[:half + 1])[:-1] + dp(ring[half:])
    return out if len(out) >= 4 else []


def clip(pts, box):
    """Sutherland-Hodgman: clip a ring to the lon/lat box."""
    w, s, e, n = box
    edges = [(lambda p: p[0] >= w, lambda a, b: (w, a[1] + (b[1] - a[1]) * (w - a[0]) / (b[0] - a[0]))),
             (lambda p: p[0] <= e, lambda a, b: (e, a[1] + (b[1] - a[1]) * (e - a[0]) / (b[0] - a[0]))),
             (lambda p: p[1] >= s, lambda a, b: (a[0] + (b[0] - a[0]) * (s - a[1]) / (b[1] - a[1]), s)),
             (lambda p: p[1] <= n, lambda a, b: (a[0] + (b[0] - a[0]) * (n - a[1]) / (b[1] - a[1]), n))]
    for inside, cross in edges:
        if not pts:
            break
        out, prev = [], pts[-1]
        for cur in pts:
            if inside(cur):
                if not inside(prev):
                    out.append(cross(prev, cur))
                out.append(cur)
            elif inside(prev):
                out.append(cross(prev, cur))
            prev = cur
        pts = out
    return pts


def fleet(action):
    """Convoy ships and escorts as {name, kind, type, sunk}; type picks the silhouette.
    Ships are written as in engagement.yml: "Takegawa*" (a merchant, sunk), "Daiyoku (Taiyoku)*", or an
    object for anything else: a tanker, or a ship known only as the submarine identified it."""
    def maru(s):  # "Daiyoku (Taiyoku)*" -> "Daiyoku Maru (Taiyoku)"
        base, _, alt = s.rstrip("*").partition(" (")
        return f"{base} Maru" + (f" ({alt}" if alt else "")
    ships = [{"name": s["name"], "kind": s.get("kind", "Merchant"), "type": s.get("type", "cargo"), "sunk": s.get("sunk", False)}
             if isinstance(s, dict) else {"name": maru(s), "kind": "Merchant", "type": "cargo", "sunk": s.endswith("*")}
             for s in action["ships"]]
    escorts = [{"name": e["name"], "kind": e["kind"], "type": e["type"], "sunk": e.get("sunk", False)}
               for e in action["escorts"]]
    return ships, escorts


def ship_type(title, action):
    """Silhouette for a Japanese event, from the first ship it names (None for shore stations)."""
    ships, escorts = fleet(action)
    for s in ships + escorts:
        # the ship's own name word: "Takegawa", "Tosei" in "No. 2 Tosei Maru", "Harukaze"
        key = next((w for w in s["name"].split() if w not in ("No.", "Maru") and not w[0].isdigit()), "")
        if key and key in title:
            return s["type"]
    return None


def crossrefs(eng):
    """(boat id, attack ref) -> outcome notes, from the crossrefs.json of each folder in "japanese".
    An attack in a folder's crossrefs is that folder's own boat's unless it names another ("ss-384-parche/1")."""
    by_patrol = {b["patrol"]: b["id"] for b in eng["boats"]}
    out = {}
    for folder in eng.get("japanese", []):
        path = patrol_dir(folder) / "crossrefs.json"
        if not path.exists():
            continue
        for x in json.load(open(path, encoding="utf-8")):
            other = x["attack"].rpartition(":")[0]
            boat = by_patrol.get(other or folder)
            notes = out.setdefault((boat, x["attack"].rpartition(":")[2]), [])
            if x["note"] not in notes and not x["note"].startswith("see the"):
                notes.append(x["note"])
    return {k: " ".join(n if n.endswith((".", ")")) else n + "." for n in v) for k, v in out.items()}


def japanese_records(folder):
    """japanese.csv rows with GMT times. A record of one day's event that gives no time takes the time of the attack
    crossrefs.csv matches it to, and says so in "untimed". Monthly tables (date "1944-04") and records matching no
    attack keep utc None."""
    matched = {}
    path = patrol_dir(folder) / "crossrefs.json"
    for x in json.load(open(path, encoding="utf-8")) if path.exists() else []:
        matched.setdefault(x["japanese"]["id"], (x["attack"].rpartition(":")[2], parse_iso(x["submarine"]["utc"])))
    out = []
    for j in load_japanese(folder).values():
        j["untimed"] = ""
        if not j["utc"] and j["id"] in matched and len(j["date"]) == 10:
            ref, j["utc"] = matched[j["id"]]
            j["untimed"] = f"The record gives no time; drawn at the time of the attack it matches ({ref})."
        out.append(j)
    return out


def load_notes(folder):
    path = folder / "notes.csv"
    return list(csv.DictReader(open(path, encoding="utf-8"))) if path.exists() else []


def build_action(eng, action, notes, outcomes):
    start, end = parse_iso(action["start"]), parse_iso(action["end"])
    fixes, tracks = [], {}
    for b in eng["boats"]:
        rows = load(b["patrol"])
        on = [r for r in rows if r["on_track"] == "yes"]
        before = [r for r in on if r["utc"] < start][-1:]
        after = [r for r in on if r["utc"] > end][:1]
        inside = [r for r in rows if start <= r["utc"] <= end]
        # a boat with no position in the window wasn't there: no track, rather than a line between distant fixes
        on_inside = [r for r in inside if r["on_track"] == "yes"]
        tracks[b["id"]] = [fix_out(b["id"], r) for r in before + on_inside + after] if on_inside else []
        fixes += [fix_out(b["id"], r) for r in inside]

    events = []
    for f in fixes:
        if f["kind"] == "attack" or f["ref"].endswith(" fired"):
            events.append({"utc": f["utc"], "side": f["boat"], "type": "attack", "title": f["ref"].replace(" fired", " (narrative)"),
                           "text": f["note"], "outcome": outcomes.get((f["boat"], f["ref"]), ""), "local": f["local"],
                           "doubt": f["fix"] if (not f["on_track"] or f["fix"]) else "",
                           "page": f["page"], "scan": f["scan"], "lat": f["lat"], "lon": f["lon"]})
        elif f["kind"] in ("ship", "air"):  # contacts from the report's tables: the target's position for ships
            events.append({"utc": f["utc"], "side": f["boat"], "type": "contact",
                           "title": {"ship": "Ship contact", "air": "Aircraft contact"}[f["kind"]] + f" ({f['ref'].split()[-1]})",
                           "text": f["note"], "local": f["local"], "doubt": "", "page": f["page"], "scan": f["scan"]})
    # each boat's depth log, where transcribed: depth charges, passing depths and orders of 300 ft or more
    for b in eng["boats"]:
        path = patrol_dir(b["patrol"]) / "depths.csv"
        if not path.exists():
            continue
        for r in csv.DictReader(open(path, encoding="utf-8")):
            if not r["time"]:
                continue
            t = to_utc(r["date"], r["time"], r["zone"])
            if start <= t <= end and (r["event"] in ("charges", "passing") or (r["event"] == "depth" and r["depth_ft"] and int(r["depth_ft"]) >= 300)):
                title = {"charges": "Depth charges", "passing": f"Passing {r['depth_ft']} ft", "depth": f"Ordered {r['depth_ft']} ft"}[r["event"]]
                if r["charges"]:
                    title += f" ({r['charges']})"
                events.append({"utc": iso(t), "side": b["id"], "type": "dive", "title": title, "text": r["quote"],
                               "local": f"{r['date']} {r['time']} ({r['zone']})", "page": r["page"], "scan": scan_url(r["page"])})
    for n in notes:
        t = to_utc(n["date"], n["time"], n["zone"])
        if start <= t <= end:
            events.append({"utc": iso(t), "side": n["boat"], "type": "log", "title": "Log", "text": n["text"],
                           "local": f"{n['date']} {n['time']} ({n['zone']})", "page": n["page"], "scan": scan_url(n["page"])})
    sinkings = []
    for folder in eng.get("japanese", []):
        for j in japanese_records(folder):
            untimed = j["untimed"]
            if not (j["utc"] and start <= j["utc"] <= end):
                continue
            secondary = j["source"].startswith("combinedfleet")
            hit = j["event"] in ("torpedoed", "sank", "attacked_no_damage")
            title = j["ship"].replace("; ", " and ") or (f"Ship not named ({j['convoy']})" if hit else j["convoy"])
            ev = {"utc": iso(j["utc"]), "side": "japan", "type": j["event"], "title": title,
                  "text": j["translation"], "original": j["original"], "local": f"{j['date']} {j['time'] or 'no time'} (I, Tokyo)",
                  "page": f"{j['source']} {j['page']}".strip(), "scan": j["url"],
                  "doubt": " ".join(x for x in ("Secondary source (combinedfleet.com)." if secondary else "", untimed) if x),
                  "ship_type": ship_type(j["ship"], action) if j["ship"] else ("cargo" if hit else None)}
            if j["lat"] is not None:
                ev["lat"], ev["lon"] = round(j["lat"], 4), round(j["lon"], 4)
                if hit:
                    sinkings.append(ev)
            events.append(ev)
    # other US records (an air group's action report): their own lane; positions they give are marked estimated
    others = []
    for side in eng.get("others", []):
        for o in side["events"]:
            t = to_utc(o["date"], o["time"], o["zone"])
            if not start <= t <= end:
                continue
            ev = {"utc": iso(t), "side": side["id"], "type": o.get("type", "record"), "title": o["title"], "text": o["text"],
                  "local": f"{o['date']} {o['time']} ({o['zone']})", "doubt": o.get("doubt", ""),
                  "page": o.get("page", ""), "scan": o.get("scan", ""), "ship_type": side.get("type")}
            if "lat" in o:
                ev["lat"], ev["lon"], ev["estimated"] = o["lat"], o["lon"], o.get("estimated", "")
                others.append(ev)
            events.append(ev)
    events.sort(key=lambda e: e["utc"])

    pts = [(f["lon"], f["lat"]) for f in fixes] + [(e["lon"], e["lat"]) for e in sinkings + others]
    if not pts:
        sys.exit(f"{action['id']}: no positions between {action['start']} and {action['end']}")
    lons, lats = [p[0] for p in pts], [p[1] for p in pts]
    box = [min(lons) - 0.35, min(lats) - 0.3, max(lons) + 0.35, max(lats) + 0.3]
    ships, escorts = fleet(action)
    return {**{k: v for k, v in action.items() if k not in ("ships", "escorts")},
            "ships": ships, "escorts": escorts, "sil_note": SIL_NOTE,
            "box": [round(v, 3) for v in box], "tracks": tracks, "fixes": fixes, "events": events, "sinkings": sinkings,
            "estimates": others}


def check(eng_id, eng):
    """Fail on what would break the page; warn on what a reader would miss."""
    if not 1 <= len(eng["boats"]) <= MAX_BOATS:
        sys.exit(f"{eng_id}: {len(eng['boats'])} boats; the page's colours are checked for 1-{MAX_BOATS}")
    for a in eng["actions"]:
        for e in a["escorts"] + [x for x in a["ships"] if isinstance(x, dict)]:
            if e.get("type", "cargo") not in SIL_TYPES:
                sys.exit(f"{eng_id} {a['id']}: {e['name']} has type {e['type']!r}; use one of {sorted(SIL_TYPES)}")
    missing = [f"{b['id']}.co" for b in eng["boats"] if not b["co"]]
    missing += [f"{k}" for k in ("title", "lede") if not eng.get(k)]
    missing += [f"{a['id']}.{k}" for a in eng["actions"] for k in ("label", "outcome") if not a.get(k)]
    missing += [f"{a['id']}.convoy or target_label" for a in eng["actions"] if not (a.get("convoy") or a.get("target_label"))]
    if missing:
        print(f"  {eng_id}: still to fill in: {', '.join(missing)}")


def build(eng_id, land_topo):
    folder = ENGAGEMENTS / eng_id
    eng = records.load_yaml(folder / "engagement.yml")
    check(eng_id, eng)
    notes, outcomes = load_notes(folder), crossrefs(eng)
    actions = [build_action(eng, a, notes, outcomes) for a in eng["actions"]]
    # locator inset: every action's box, padded to at least 7 degrees across so the coast shows
    w, s = min(a["box"][0] for a in actions), min(a["box"][1] for a in actions)
    e, n = max(a["box"][2] for a in actions), max(a["box"][3] for a in actions)
    cx, cy, half = (w + e) / 2, (s + n) / 2, max((e - w) / 2 + 1.2, (n - s) / 2 + 1.2, 3.5)
    inset = [round(cx - half, 3), round(cy - half, 3), round(cx + half, 3), round(cy + half, 3)]
    # coastline: full detail around each action (wide enough for any map shape), simplified for the locator
    for a in actions:
        w0, s0, e0, n0 = a["box"]
        r = max(e0 - w0, n0 - s0) + 0.5
        a["land"] = decode_land(land_topo, [(w0 + e0) / 2 - r, (s0 + n0) / 2 - r, (w0 + e0) / 2 + r, (s0 + n0) / 2 + r])
    tol = half / 200
    inset_land = [[[round(x, 2), round(y, 2)] for x, y in r] for r in (simplify(r, tol) for r in decode_land(land_topo, inset)) if r]
    data = {"id": eng_id, **{k: eng.get(k, "") for k in ("title", "short", "eyebrow", "lede")},
            "places": eng.get("places", []), "notes": eng.get("notes", []),
            "boats": [{k: b[k] for k in ("id", "name", "hull", "co", "patrol_no")} for b in eng["boats"]],
            "others": [{k: o.get(k, "") for k in ("id", "name", "type")} for o in eng.get("others", [])],
            "actions": actions, "inset": inset, "inset_land": inset_land, "silhouettes": SILHOUETTES["shapes"]}
    OUT.mkdir(exist_ok=True)
    path = OUT / f"{eng_id}.json"
    json.dump(data, open(path, "w", encoding="utf-8"), separators=(",", ":"), ensure_ascii=False)
    print(f"{rel(path)}: {sum(len(a['events']) for a in actions)} events, {len(inset_land)} locator rings, "
          f"{round(path.stat().st_size / 1024)} KB")
    for a in actions:
        print(f"  {a['id']} {a['box']} tracks {({k: len(v) for k, v in a['tracks'].items()})}, "
              f"{len(a['fixes'])} fixes, {len(a['sinkings'])} Japanese positions")
    return data


def write_index():
    """records/battles/index.json: the engagements, in date order, for the page's picker."""
    index = []
    for path in sorted(OUT.glob("*.json")):
        if path.name == "index.json":
            continue
        d = json.load(open(path, encoding="utf-8"))
        index.append({"id": d["id"], "short": d["short"] or d["title"], "title": d["title"], "start": d["actions"][0]["start"],
                      "boats": [b["name"] for b in d["boats"]], "actions": [a["label"] for a in d["actions"]]})
    index.sort(key=lambda x: x["start"])
    json.dump(index, open(OUT / "index.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)


def draft(eng_id, patrols):
    """A first engagement.yml from the patrols' attack rows: attacks less than 18 hours apart are one action,
    whose window opens at the last ship contact up to 12 hours before the first attack (or 6 hours before it)
    and closes 6 hours after the last. Convoy and ships come from the Japanese records inside the window."""
    folder = ENGAGEMENTS / eng_id
    if (folder / "engagement.yml").exists():
        sys.exit(f"{folder / 'engagement.yml'} exists; edit it instead")
    boats = [boat_from_folder(p) for p in patrols]
    rows = [r for p in patrols for r in load(p)]
    attacks = sorted((r for r in rows if r["source"] == "attack"), key=lambda r: r["utc"])
    if not attacks:
        sys.exit("no attack rows in " + ", ".join(patrols))
    groups = [[attacks[0]]]
    for r in attacks[1:]:
        (groups[-1].append(r) if r["utc"] - groups[-1][-1]["utc"] < timedelta(hours=18) else groups.append([r]))
    japanese = [p for p in patrols if (patrol_dir(p) / "japanese.csv").exists()]
    ja = [j for p in japanese for j in japanese_records(p) if j["utc"]]
    actions = []
    for g in groups:
        first, last = g[0]["utc"], g[-1]["utc"]
        contacts = [r["utc"] for r in rows if r["source"] == "ship" and first - timedelta(hours=12) <= r["utc"] <= first]
        start = (min(contacts) if contacts else first) - timedelta(hours=2 if contacts else 6)
        start, end = start.replace(minute=0), (last + timedelta(hours=6)).replace(minute=0)
        inside = [j for j in ja if start <= j["utc"] <= end]
        convoys = sorted({j["convoy"] for j in inside if j["convoy"]})
        ships = []
        for j in inside:
            for s in j["ship"].split("; "):
                name = s.replace(" Maru", "") + ("*" if j["event"] == "sank" else "")
                if s and s.endswith("Maru") and name.rstrip("*") not in [x.rstrip("*") for x in ships]:
                    ships.append(name)
                elif name.endswith("*") and name.rstrip("*") in ships:
                    ships[ships.index(name.rstrip("*"))] = name
        local = f"{first + timedelta(hours=9):%-d %B %Y}"
        actions.append({"id": (convoys[0] if convoys else f"{first:%Y%m%d}").lower().replace(" ", ""),
                        "label": local, "convoy": " / ".join(convoys), "start": iso(start), "end": iso(end),
                        "route": "", "ships": ships, "ships_note": "", "escorts": [], "outcome": ""})
    eng = {"title": "", "short": "", "eyebrow": "", "lede": "", "boats": boats, "japanese": japanese,
           "actions": actions, "places": [], "notes": []}
    folder.mkdir(parents=True, exist_ok=True)
    import yaml
    (folder / "engagement.yml").write_text(yaml.safe_dump(eng, sort_keys=False, allow_unicode=True, width=100))
    print(f"wrote {rel(folder / 'engagement.yml')}: {len(actions)} action(s) from {len(attacks)} attacks")
    for a in actions:
        print(f"  {a['id']}: {a['start']} to {a['end']}, convoy {a['convoy'] or '?'}, ships {a['ships']}")
    print("Fill in the titles, captains, escorts, route and outcome (guides/BATTLES.md), then run build_battle.py", eng_id)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if args[:1] == ["new"]:
        if len(args) < 3:
            sys.exit(__doc__)
        draft(args[1], args[2:])
        sys.exit()
    if not land_path.exists():
        land_path.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(LAND_URL, land_path)
    ids = [a for a in args if not a.endswith(".html")] or sorted(p.name for p in ENGAGEMENTS.iterdir() if (p / "engagement.yml").exists())
    built = {i: build(i, land_path) for i in ids}
    write_index()
    if "--standalone" in sys.argv:
        # one engagement named on the command line: that one inlined; none named: every engagement, with the picker
        out = Path(sys.argv[sys.argv.index("--standalone") + 1])
        if len(built) == 1:
            payload = next(iter(built.values()))
        else:
            payload = {"index": json.load(open(OUT / "index.json", encoding="utf-8")), "engagements": built}
        page = (KIT / "site" / "battle.html").read_text()
        inline = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
        page = page.replace('<script type="application/json" id="data"></script>',
                            f'<script type="application/json" id="data">{inline}</script>')
        out.write_text(page)
        print("wrote", out, f"({round(out.stat().st_size / 1024)} KB)")
