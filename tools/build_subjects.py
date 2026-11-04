# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
"""Every subject the pages follow, in one registry: records/subjects.json, for site/subject.html and site/subjects.html.

A subject (guides/OPERATIONS-VIEWER.md 2.1) is something the records follow: a boat (boats/<hull>-<name>/ship.yml),
a ship (ships/<hull>-<name>/ship.yml), an Army unit (army/units.csv), a Seabee battalion (seabees/units.csv), a convoy
(convoys/<id>/convoy.md) and a command (commands/comsubpac/command.yml). Each entry:

  id, alias        the folder key (ss-385-bang) and the short key the addresses also take (bang); a unit's, a
                   battalion's, a convoy's or a command's id alone
  kind             boat, ship, unit, battalion, convoy, command; `vessel` is a boat's or ship's kind (submarine, ...)
  name, short      the designation as the records give it, and the short form the lists and crumbs use
  plain            what it was, in a line, in our words: ship.yml `plain`, army/units.yml and seabees/units.yml
                   (`{unit: {plain}}`, beside the CSVs, since words go in YAML), convoy.md `plain`, command.yml `plain`.
                   Hand-edited; the build fails on a subject without one
  of               its nationality as the records give it (us, jp)
  theatre          pacific, atlantic, mediterranean, europe or home (never overseas), from where its positions lie
  note             the unit's or battalion's note (units.csv), a convoy's first paragraph
  periods          a boat's patrols (inventory.yml's status, dates and files; ship.yml's name, area, CO; the track's
                   fixes and attacks), a ship's one record with its months (inventory.yml), a unit's or battalion's
                   months with stations (the source in force each month, and whether it is assumed), a convoy's voyage,
                   a command's months
  relations        dated membership of this subject in another, one shape wherever the records keep it: army/relations.csv
                   (both ways: `dir` says whether the subject is the row's unit or its other), seabees/parts.csv (a part
                   of the battalion), a convoy's `ships:` (a ship in the convoy), ComSubPac's disposition.csv (a boat in a
                   task unit or under refit) and task_organization.csv (the force's task groups):
                   {relation, dir, other, other_name, from, to, basis, ref, cite, note}
  engagements      the engagements the subject is a participant in (engagements/<id>/engagement.json: a track, a unit or
                   a convoy), each with the period it falls in
  records          which of its record files exist, with a count each (positions, attacks, depths, japanese, frupac,
                   stations, actions, ships, routes, parts, voyages, projects, ...)
  leads            the leads about it (army/leads.yml: statement, said_by, searched, still, ref)
  box, first, last the bounding box of its positions [west, south, east, north] and its first and last dates

Derived, never stored: a unit's stages (chapter.js), the coverage bar (from `periods`), the speed check (on the page).

  uv run tools/build_subjects.py           check everything, then write records/subjects.json
  uv run tools/build_subjects.py check     check only; exits 1 on a problem or if the file is out of date (CI)
"""
import csv
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import records
from build_operations import resolve_cite, sections, sources, split
from records import RECORDS, rel

OUT = RECORDS / "subjects.json"
# stations.csv sources that give a headquarters' or a division's position, not the unit's own (army/README.md)
ASSUMED = {"bn", "regt", "hist", "aar", "div"}
SOURCE_WORDS = {"mr": "its own morning reports", "btry": "the battery's own position in the battalion's records",
                "bn": "the battalion command post (the battery assumed nearby)",
                "regt": "the Regimental HQ Battery's morning reports (the detachment's own missing)",
                "hist": "the 894th's printed history (the battalion's position)",
                "aar": "Third Army's antiaircraft situation maps (the battalion's symbol)",
                "div": "division-level sources (the division's position)", "cp": "the order of battle's command posts",
                "uaar": "its own after action reports",
                "muster": "its muster rolls", "wardiary": "the war diaries of the ships that carried it",
                "ncbhist": "its history sheet (the Seabee Museum)", "bases": "Building the Navy's Bases", "mcsol": "Marines in the Central Solomons"}
LEAD_FIELDS = {"statement", "units", "said_by", "ref", "searched", "still"}
PACK = re.compile(r"^17\.(1[1-9]|2[0-4])\b")   # ComSubPac's coordinated attack groups, G 17.11 through G 17.24


def read_csv(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return [{k: (v or "").strip() for k, v in r.items()} for r in csv.DictReader(f)]


def jload(path):
    return json.loads(path.read_text(encoding="utf-8"))


def iso(v):
    return v.isoformat() if isinstance(v, date) else (str(v) if v not in (None, "") else "")


def box_of(points):
    pts = [(lon, lat) for lon, lat in points if lon is not None and lat is not None]
    if not pts:
        return None
    return [round(min(p[0] for p in pts), 3), round(min(p[1] for p in pts), 3),
            round(max(p[0] for p in pts), 3), round(max(p[1] for p in pts), 3)]


def months_between(a, b):
    """'1942-09-01', '1945-05-14' -> ['1942-09', ..., '1945-05']"""
    y, m = int(a[:4]), int(a[5:7])
    out = []
    while f"{y:04d}-{m:02d}" <= b[:7]:
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out


def task_group(tu, task_org):
    """A task unit's group title from task_organization.csv: 17.18.2 is in G 17.18, one of "G 17.11 through G 17.24
    inclusive", the Coordinated Attack Groups; 17.1.7 in G 17.1, the Empire Patrol Group."""
    tg = tu.rsplit(".", 1)[0] if tu.count(".") > 1 else tu
    for g in task_org:
        ids = re.findall(r"\d+\.\d+", g["unit"])
        if len(ids) == 1 and ids[0] == tg:
            return g["title"]
        if len(ids) == 2 and ids[0].split(".")[0] == tg.split(".")[0] and int(ids[0].split(".")[1]) <= int(tg.split(".")[1]) <= int(ids[1].split(".")[1]):
            return g["title"]
    return ""


class Build:
    def __init__(self):
        self.problems = []
        self.srcs = sources()
        self.cited = []

    def bad(self, where, what):
        self.problems.append(f"{where}: {what}")

    def cite(self, ref, where, required=True):
        """A citation (or several, `;`-separated) -> [{ref, href, short, page}]; a problem if none resolves."""
        out = []
        for c in [x.strip() for x in re.split(r"\s*;\s*", str(ref or "")) if x.strip()]:
            r = resolve_cite(c, self.srcs)
            if not r:
                self.bad(where, f"citation {c!r} matches no source in SOURCES.yml")
                continue
            self.cited.append(c)
            out.append({"ref": c, "href": r["href"], "short": r["short"], "page": r["page"]})
        if required and not out:
            self.bad(where, "no citation")
        return out

    def relation(self, relation, other, other_name, frm="", to="", basis="reported", ref="", note="", where="", direction="of", required=True):
        return {"relation": relation, "dir": direction, "other": other, "other_name": other_name, "from": iso(frm), "to": iso(to),
                "basis": basis or "reported", "ref": str(ref or ""), "cite": self.cite(ref, where, required), "note": note or ""}

    # ------------------------------------------------------------------ the engagements, by subject
    def engagements(self):
        """subject key -> [{id, title, short, theater, from, to, period}], from each engagement.json's participants."""
        by = {}
        idx = jload(RECORDS / "engagements" / "index.json") if (RECORDS / "engagements" / "index.json").exists() else []
        for x in idx:
            p = RECORDS / "engagements" / x["id"] / "engagement.json"
            if not p.exists():
                continue
            e = jload(p)
            head = {"id": e["id"], "title": e["title"], "short": e.get("short", ""), "theater": e.get("theater", ""),
                    "from": x.get("from", ""), "to": x.get("to", "")}
            for pt in e.get("participants", []):
                if pt.get("track"):
                    key, _, n = pt["track"].partition("/")
                    by.setdefault(key, []).append({**head, "period": int(n) if n else 1, "as": pt.get("name", "")})
                if pt.get("unit"):
                    by.setdefault(pt["unit"], []).append({**head, "period": "", "as": pt.get("name", ""), "basis": pt.get("basis", "reported")})
                if pt.get("convoy"):
                    by.setdefault(pt["convoy"], []).append({**head, "period": 1, "as": pt.get("name", "")})
        return by

    # ------------------------------------------------------------------ boats and ships
    def vessels(self, inv, engs, disposition, task_org):
        out = []
        for d in records.vessels():
            y = records.load_yaml(d / "ship.yml")
            where = rel(d / "ship.yml")
            if not y.get("plain"):
                self.bad(where, "no `plain` line (what she was, in a line, ours; guides/OPERATIONS-VIEWER.md 2.1)")
            boat = d.parent.name == "boats"
            hull = y["hull"]
            m = y.get("map", {}) or {}
            periods_in = {int(p["n"]): p for p in m.get("periods", []) if "n" in p}
            geo = d / ("tracks.geojson" if boat else "track.geojson")
            feats = jload(geo)["features"] if geo.exists() else []
            def pts(n=None):
                return [f for f in feats if f["geometry"]["type"] == "Point" and (n is None or f["properties"].get("patrol") == n)]
            periods, recs = [], {}
            if boat:
                inv_b = (inv.get("boats") or {}).get(hull) or {}
                for n in records.patrols(d.name):
                    pd = d / f"patrol-{n}"
                    files = {p.stem: p for p in pd.iterdir() if p.suffix in (".csv", ".yml")}
                    for k, p in files.items():
                        recs[k] = recs.get(k, 0) + (sum(1 for _ in csv.DictReader(p.open(encoding="utf-8"))) if p.suffix == ".csv"
                                                    else len(records.load_yaml(p) or []))
                    ip = ((inv_b.get("patrols") or {}).get(n) or {})
                    pp = periods_in.get(n, {})
                    fixes = pts(n)
                    track = [f for f in fixes if f["properties"].get("on_track")]
                    periods.append({"n": n, "name": pp.get("name", f"Patrol {n}"), "dates": pp.get("dates", ""), "area": pp.get("area", ""),
                                    "co": pp.get("co", ""), "status": ip.get("status", ""), "from": iso(ip.get("first_fix")), "to": iso(ip.get("last_fix")),
                                    "files": ip.get("files", []), "nara": ip.get("nara", []), "note": ip.get("note", ""),
                                    "fixes": len(track), "attacks": sum(1 for f in fixes if f["properties"]["kind"] in ("attack", "gun")),
                                    "box": box_of([f["geometry"]["coordinates"] for f in track])})
                    if not ip:
                        self.bad(where, f"patrol {n} is not in inventory.yml")
            else:
                inv_s = ((inv.get("ships") or {}).get(hull) or {}).get("records") or {}
                months = [{"month": k, **{kk: v for kk, v in r.items() if kk in ("status", "nara", "files", "note")}} for k, r in inv_s.items()
                          if re.fullmatch(r"\d{4}-\d{2}", str(k))]
                fixes = pts()
                track = [f for f in fixes if f["properties"].get("on_track")]
                days = sorted(f["properties"]["utc"][:10] for f in fixes if f["properties"].get("utc"))
                pp = periods_in.get(1, {})
                if (d / "positions.csv").exists():
                    recs["positions"] = sum(1 for _ in csv.DictReader((d / "positions.csv").open(encoding="utf-8")))
                periods.append({"n": 1, "name": pp.get("name", "War diary"), "dates": pp.get("dates", ""), "area": pp.get("area", ""),
                                "co": pp.get("co", ""), "status": "mapped" if track else "", "from": days[0] if days else "",
                                "to": days[-1] if days else "", "months": months, "fixes": len(track),
                                "attacks": sum(1 for f in fixes if f["properties"]["kind"] in ("attack", "gun")),
                                "box": box_of([f["geometry"]["coordinates"] for f in track])})
            if y.get("dives"):
                recs["dives"] = 1
            all_track = [f["geometry"]["coordinates"] for f in pts() if f["properties"].get("on_track")]
            box = box_of(all_track)
            theatre = "pacific" if not all_track else ("pacific" if sum(1 for lon, _ in all_track if lon > 100 or lon < -100) * 2 >= len(all_track) else "atlantic")
            firsts = [p["from"] for p in periods if p["from"]]
            lasts = [p["to"] for p in periods if p["to"]]
            # ComSubPac's dispositions: the boat in a task unit (a coordinated attack group) or under refit, on each day listed
            relations = []
            for r in disposition:
                if r["name"].upper() == y["name"].upper():
                    tu = r["unit"]
                    group = task_group(tu, task_org) if tu else ""
                    relations.append(self.relation("in_unit" if tu else "disposed", "comsubpac",
                                                   f"Task Unit {tu}, {group.rstrip('.')}" if tu and group else (f"Task Unit {tu}" if tu else r["section"]),
                                                   r["date"], "", "reported", r["page"], (r["note"] or "") + (f" (listed under {r['section']})" if tu else ""),
                                                   f"comsubpac/disposition.csv {r['date']} {r['boat']}"))
            out.append({"id": d.name, "alias": y["name"].lower(), "kind": "boat" if boat else "ship", "vessel": y.get("kind", ""),
                        "name": f"USS {y['name']} ({hull})", "short": y["name"] if boat else f"USS {y['name']}", "hull": hull,
                        "class": y.get("class", ""), "silhouette": y.get("silhouette", ""), "plain": y.get("plain", ""), "of": "us",
                        "theatre": theatre, "note": "", "dives": bool(y.get("dives")), "max_kts": y.get("max_kts"),
                        "geojson": str(geo.relative_to(RECORDS)) if geo.exists() else None, "catalogId": m.get("catalogId"),
                        "periods": periods, "relations": relations, "engagements": sorted(engs.get(d.name, []), key=lambda e: e["from"]),
                        "records": recs, "leads": [], "box": box, "first": min(firsts) if firsts else "", "last": max(lasts) if lasts else ""})
        return out

    # ------------------------------------------------------------------ Army units
    def army(self, inv, engs, leads):
        army = RECORDS / "army"
        units = read_csv(army / "units.csv")
        plain = records.load_yaml(army / "units.yml") if (army / "units.yml").exists() else {}
        for k in plain:
            if k not in {u["unit"] for u in units}:
                self.bad("army/units.yml", f"{k!r} is not a unit in units.csv")
        built = jload(army / "army.json") if (army / "army.json").exists() else {"units": [], "routes": []}
        by_unit = {u["unit"]: u for u in built["units"]}
        rels = read_csv(army / "relations.csv")
        ships = read_csv(army / "ships.csv")
        routes = read_csv(army / "routes.csv")
        out = []
        for u in units:
            uid = u["unit"]
            where = f"army/units.csv {uid}"
            p = (plain.get(uid) or {}).get("plain", "")
            if not p:
                self.bad(where, "no `plain` line in army/units.yml (what it was, in a line, ours)")
            b = by_unit.get(uid, {"stations": [], "actions": []})
            st = b["stations"]
            placed = [s for s in st if s.get("lat") is not None]
            periods = []
            if st:
                dates = [s["date"] for s in st]
                for mo in months_between(min(dates), max(dates)):
                    mid = f"{mo}-15"
                    rows = [s for s in st if s["date"][:7] == mo]
                    inforce = [s for s in st if s["date"] <= mid] or rows[:1]
                    src = inforce[-1]["source"] if inforce else ""
                    periods.append({"month": mo, "stations": len(rows), "source": src, "assumed": src in ASSUMED,
                                    "sources": sorted({s["source"] for s in rows}),
                                    "places": [s["place"] for s in rows if s.get("place")][:6]})
            relations = []
            for r in rels:
                if r["unit"] == uid:
                    relations.append(self.relation(r["relation"], r["other"], r["other_name"], r["from"], r["to"], r["basis"], r["page"], r["note"],
                                                   f"army/relations.csv {uid} {r['relation']} {r['other']}", "of"))
                elif r["other"] == uid:
                    relations.append(self.relation(r["relation"], r["unit"], next((x["name"] for x in units if x["unit"] == r["unit"]), r["unit"]),
                                                   r["from"], r["to"], r["basis"], r["page"], r["note"],
                                                   f"army/relations.csv {r['unit']} {r['relation']} {uid}", "to"))
            recs = {"stations": len(st), "placed": len(placed), "actions": len(b.get("actions", [])),
                    "ships": sum(1 for s in ships if s["unit"] == uid), "routes": len({(r["from_date"], r["to_date"]) for r in routes if r["unit"] == uid}),
                    "relations": len(relations)}
            recs = {k: v for k, v in recs.items() if v}
            pts = [(s["lon"], s["lat"]) for s in placed]
            overseas = [(lon, lat) for lon, lat in pts if lon > -12 and not (lat > 49.5 and lon < 2)]
            # where it was: the Mediterranean or Europe by most of its stations overseas; home if it never left the United
            # States and Britain; nothing for a unit entered for its relations alone, with no station yet
            theatre = "" if not st else "home" if not overseas else ("mediterranean" if sum(1 for _, lat in overseas if lat < 44) * 2 >= len(overseas) else "europe")
            inv_u = ((inv.get("units") or {}).get(uid) or {})
            status = (inv_u.get("record") or {}).get("status", "")
            out.append({"id": uid, "alias": uid, "kind": "unit", "name": u["name"], "short": u.get("short") or uid, "plain": p, "of": "us",
                        "theatre": theatre, "note": u.get("note", ""), "status": status, "periods": periods, "relations": relations,
                        "engagements": sorted(engs.get(uid, []), key=lambda e: e["from"]), "records": recs,
                        "leads": [ld for ld in leads if uid in ld.get("units", [])], "box": box_of(pts),
                        "first": st[0]["date"] if st else "", "last": st[-1]["date"] if st else ""})
        return out

    # ------------------------------------------------------------------ Seabee battalions
    def seabees(self, inv, engs):
        sb = RECORDS / "seabees"
        units = read_csv(sb / "units.csv")
        plain = records.load_yaml(sb / "units.yml") if (sb / "units.yml").exists() else {}
        for k in plain:
            if k not in {u["unit"] for u in units}:
                self.bad("seabees/units.yml", f"{k!r} is not a unit in units.csv")
        built = jload(sb / "seabees.json") if (sb / "seabees.json").exists() else {"rows": [], "parts": [], "voyages": [], "projects": []}
        parts = read_csv(sb / "parts.csv")
        pat = [re.compile(s["match"]) for s in records.load_yaml(RECORDS / "SOURCES.yml").values() if isinstance(s, dict) and s.get("match")]
        out = []
        for u in units:
            uid = u["unit"]
            p = (plain.get(uid) or {}).get("plain", "")
            if not p:
                self.bad(f"seabees/units.csv {uid}", "no `plain` line in seabees/units.yml (what it was, in a line, ours)")
            rows = sorted([r for r in built["rows"] if r["unit"] == uid], key=lambda r: (r["date"], r["id"]))
            placed = [r for r in rows if r.get("lat") is not None]
            periods = []
            if rows:
                for mo in months_between(rows[0]["date"], rows[-1]["date"]):
                    mid = f"{mo}-15"
                    rs = [r for r in rows if r["date"][:7] == mo]
                    inforce = [r for r in rows if r["date"] <= mid] or rs[:1]
                    src = inforce[-1]["source"] if inforce else ""
                    periods.append({"month": mo, "stations": len(rs), "source": src, "assumed": any(r.get("assumed") for r in rs),
                                    "sources": sorted({r["source"] for r in rs}), "places": [r["place"] for r in rs if r.get("place")][:6],
                                    "parts": sorted({r["part"] for r in rs})})
            relations = []
            for r in parts:
                if r["unit"] != uid:
                    continue
                # the note cites its pages in prose ("(ncbhist-020/p2, p11)", "p11-p12"): the first page of a range is the citation
                refs = [m.group(1) for m in re.finditer(r"([A-Za-z0-9:_-]+/p\d+)(?:-p?\d+)?", r["note"]) if any(q.match(m.group(1)) for q in pat)]
                relations.append(self.relation("part", f"{uid}:{r['part']}", r["part"], r["from"], r["to"], "reported", ";".join(dict.fromkeys(refs)),
                                               f"{r['note']}{' (split from ' + r['parent'] + ')' if r['parent'] != 'battalion' else ''}",
                                               f"seabees/parts.csv {uid} {r['part']}", "to", required=False))
            voyages = [v for v in built["voyages"] if v["unit"] == uid]
            projects = [x for x in built.get("projects", []) if x["unit"] == uid]
            recs = {k: v for k, v in {"stations": len(rows), "placed": len(placed), "parts": sum(1 for r in parts if r["unit"] == uid),
                                       "voyages": len(voyages), "logged_voyages": sum(1 for v in voyages if v.get("positions")),
                                       "projects": len(projects), "weather": sum(1 for k in built.get("weather", {}) if k.startswith(uid + "|"))}.items() if v}
            inv_u = ((inv.get("seabees") or {}).get(uid) or {}).get("record") or {}
            out.append({"id": uid, "alias": uid, "kind": "battalion", "name": u["name"], "short": re.sub(r"Naval Construction Battalion", "NCB", u["name"]),
                        "plain": p, "of": "us", "theatre": "pacific", "note": u.get("note", ""), "status": inv_u.get("status", ""),
                        "periods": periods, "relations": relations, "engagements": sorted(engs.get(uid, []), key=lambda e: e["from"]),
                        "records": recs, "leads": [], "box": box_of([(r["lon"], r["lat"]) for r in placed]),
                        "first": rows[0]["date"] if rows else "", "last": rows[-1]["date"] if rows else ""})
        return out

    # ------------------------------------------------------------------ convoys
    def convoys(self, engs):
        out = []
        built = jload(RECORDS / "convoys" / "convoys.json") if (RECORDS / "convoys" / "convoys.json").exists() else {"lanes": {}, "convoys": []}
        lanes = built.get("lanes", {})
        for d in sorted((RECORDS / "convoys").iterdir()):
            if not (d / "convoy.md").exists():
                continue
            fm, body = split(d / "convoy.md")
            where = rel(d / "convoy.md")
            if not fm.get("plain"):
                self.bad(where, "no `plain` line (what it was, in a line, ours)")
            c = next((x for x in built["convoys"] if x["id"] == d.name), {})
            relations = []
            for s in fm.get("ships") or []:
                ref = f"{s.get('source', '')} {s.get('page', '')}".strip() if str(s.get("source", "")).startswith("jacar:") else str(s.get("source", ""))
                relations.append(self.relation("in_convoy", re.sub(r"\W+", "-", s["ship"].lower()).strip("-"), s["ship"], s.get("from", ""), s.get("to", ""),
                                               s.get("basis", "reported"), ref, "; ".join(x for x in [s.get("role", ""), s.get("fate", "")] if x),
                                               f"{where} ships {s['ship']}", "to"))
            stops = [{"at": iso(v.get("at")), "place": v.get("place", ""), "event": v.get("event", ""), "words": v.get("words", ""),
                      "basis": v.get("basis", ""), "approx": bool(v.get("approx"))} for v in fm.get("voyage") or []]
            pts = [(lanes[n]["lon"], lanes[n]["lat"]) for n in fm.get("route") or [] if n in lanes]
            pts += [(x["lon"], x["lat"]) for k in ("sightings", "hits", "attacks") for x in c.get(k, [])]
            paras = sections(body)
            first = next((p["text"] for s in paras for p in s["paras"] if not p.get("aside")), "")
            sailed, arrived = re.sub(r"\s*\(.*\)$", "", iso(fm.get("sailed"))), re.sub(r"\s*\(.*\)$", "", iso(fm.get("arrived")))
            es = sorted(engs.get(d.name, []), key=lambda e: e["from"])
            ships = fm.get("ships") or []
            recs = {k: v for k, v in {"ships": len(ships), "reported": sum(1 for s in ships if s.get("basis") == "reported"),
                                       "secondary": sum(1 for s in ships if s.get("basis") == "secondary"), "stops": len(stops),
                                       "route": len(fm.get("route") or []), "sightings": len(c.get("sightings", [])), "hits": len(c.get("hits", []))}.items() if v}
            out.append({"id": d.name, "alias": d.name, "kind": "convoy", "name": f"Convoy {fm.get('convoy', d.name)}", "short": str(fm.get("convoy", d.name)),
                        "name_ja": fm.get("name_ja", ""), "plain": fm.get("plain", ""), "of": "jp", "theatre": "pacific", "note": first,
                        "route_words": " → ".join(x for x in [fm.get("from"), *(fm.get("via") or []), fm.get("to")] if x),
                        "periods": [{"n": 1, "name": "The voyage", "from": sailed, "to": arrived, "stops": stops, "status": "mapped" if pts else ""}],
                        "relations": relations, "engagements": es, "records": recs, "leads": [], "box": box_of(pts),
                        "first": sailed or (es[0]["from"][:10] if es else ""), "last": arrived or (es[-1]["to"][:10] if es else "")})
        return out

    # ------------------------------------------------------------------ commands
    def commands(self, inv, task_org):
        out = []
        d = RECORDS / "commands" / "comsubpac"
        if not (d / "command.yml").exists():
            return out
        y = records.load_yaml(d / "command.yml")
        if not y.get("plain"):
            self.bad(rel(d / "command.yml"), "no `plain` line")
        recs_inv = (((inv.get("commands") or {}).get("comsubpac") or {}).get("records") or {})
        periods = [{"month": k, "status": r.get("status", ""), "nara": r.get("nara", []), "files": r.get("files", [])} for k, r in recs_inv.items()]
        relations = [self.relation("task_group", g["unit"], g["title"].rstrip("."), "1944-10", "1944-10", "reported", g["page"], "",
                                   f"comsubpac/task_organization.csv {g['unit']}", "to") for g in task_org]
        recs = {p.stem: sum(1 for _ in csv.DictReader(p.open(encoding="utf-8"))) for p in sorted(d.glob("*.csv"))}
        done = [p["month"] for p in periods if p["status"] in ("transcribed", "mapped")]
        out.append({"id": "comsubpac", "alias": "comsubpac", "kind": "command", "name": y["name"], "short": y.get("short", "ComSubPac"),
                    "plain": y.get("plain", ""), "of": y.get("of", "us"), "theatre": "pacific", "note": "", "periods": periods,
                    "relations": relations, "engagements": [], "records": recs, "leads": [], "box": None,
                    "first": f"{done[0]}-01" if done else "", "last": f"{done[-1]}-31" if done else ""})
        return out

    def leads(self):
        p = RECORDS / "army" / "leads.yml"
        out = []
        units = {u["unit"] for u in read_csv(RECORDS / "army" / "units.csv")}
        for i, ld in enumerate(records.load_yaml(p) or [] if p.exists() else [], 1):
            where = f"army/leads.yml #{i}"
            for k in sorted(set(ld) - LEAD_FIELDS):
                self.bad(where, f"unknown field {k!r}")
            for k in sorted(LEAD_FIELDS - set(ld)):
                self.bad(where, f"missing field {k!r}")
            for u in ld.get("units", []):
                if u not in units:
                    self.bad(where, f"unit {u!r} is not in units.csv")
            cites = [c for r in ld.get("ref", []) for c in self.cite(str(r), where)]
            out.append({**{k: str(ld.get(k, "")) for k in ("statement", "said_by", "searched", "still")}, "units": ld.get("units", []),
                        "ref": [str(r) for r in ld.get("ref", [])], "cite": cites})
        return out


def build():
    b = Build()
    inv = records.load_yaml(RECORDS / "inventory.yml")
    cs = RECORDS / "commands" / "comsubpac"
    disposition, task_org = read_csv(cs / "disposition.csv"), read_csv(cs / "task_organization.csv")
    engs = b.engagements()
    leads = b.leads()
    subjects = b.vessels(inv, engs, disposition, task_org) + b.army(inv, engs, leads) + b.seabees(inv, engs) + b.convoys(engs) + b.commands(inv, task_org)
    ids = [s["id"] for s in subjects] + [s["alias"] for s in subjects]
    for k, n in {k: ids.count(k) for k in set(ids)}.items():
        if n > 1 and k not in {s["id"] for s in subjects if s["alias"] == k}:
            b.bad("subjects", f"id {k!r} is used {n} times")
    return b, subjects


def text(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), default=str) + "\n"


def main():
    checking = sys.argv[1:2] == ["check"]
    b, subjects = build()
    for p in b.problems:
        print(f"PROBLEM: {p}")
    if b.problems:
        print(f"{len(b.problems)} problem(s)" + ("" if checking else "; nothing written"))
        sys.exit(1)
    body = text(subjects)
    stale = not OUT.exists() or OUT.read_text(encoding="utf-8") != body
    kinds = {}
    for s in subjects:
        kinds[s["kind"]] = kinds.get(s["kind"], 0) + 1
    if checking:
        if stale:
            print(f"OUT OF DATE: {rel(OUT)} (run uv run tools/build_subjects.py)")
        print(f"{len(subjects)} subjects checked" + ("; out of date" if stale else ""))
        sys.exit(1 if stale else 0)
    OUT.write_text(body, encoding="utf-8")
    print(f"wrote {rel(OUT)}: {len(subjects)} subjects (" + ", ".join(f"{n} {k}" for k, n in kinds.items()) + f"), {len(b.problems)} problems")


if __name__ == "__main__":
    main()
