# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
"""Every engagement and convoy, from the hand-edited records to the JSON the pages read.

An engagement (records/engagements/<id>/) is two sides meeting at a place and a time, each in its own records:
  engagement.md   front matter (title, window, the participants, map labels) and the story, in Markdown
  events.yml      entries that belong to this engagement alone (a boat's narrative, an action report, a diary)
  claims.yml      the questions the records leave open, and each answer's evidence
  positions.csv   places that belong to this engagement alone (stations, reference points, bearings from a point)
The participants' own records are read where they are, never copied: a boat's patrol (positions.csv, depths.csv,
japanese.yml and claims.yml: which attack goes with which Japanese record), a ship's war diary, a convoy's
convoy.md. Fields: records/README.md ("An engagement", "A convoy"); the model: guides/ENGAGEMENTS.md.

Writes records/engagements/<id>/engagement.json for site/engagement.html?e=<id>, records/engagements/index.json
(every engagement, for the pickers and the front page) and records/convoys/convoys.json (every convoy with its ships,
the engagements that met it and where the boats saw it, for site/convoys.html).

  uv run tools/build_engagement.py           check everything, then write
  uv run tools/build_engagement.py check     check only; exits 1 on a problem or if a JSON file is out of date (CI)

It checks that every participant, convoy, silhouette and position named exists; that every time parses, with a zone
letter or the engagement's `clock`; that every entry and claim is cited, in a form SOURCES.yml knows; that every
[[link]] in the story resolves; and that every pairing in a patrol's claims.yml names an attack and a record that exist.

Sides are not stored (guides/OPERATIONS-VIEWER.md 2.4: a nationality as the record gives it, never a bloc). The records
carry `of`, the nationality of a participant, of an entry's actor (left out when the actor is a participant, whose `of`
it takes) and of a position (empty for a place); SOURCES.yml carries each source's `kind` and `of`. From those the
build derives, for the pages, what `side` used to say:
  followed     on a participant: it has a track or a unit, a subject the page follows and colours. A convoy is the other
               side's record, read against the followed boats' sightings of it, and is not followed here.
  own          on the engagement: the nationalities of the followed subjects.
  against      on the engagement: whom the subjects faced, as the records name them. Hand-edited in the front matter only
               when more than two nationalities meet (Algiers: `against: [de, it]`, with the RAF and the French press
               beside Battery C); left out, it is every nationality that isn't the subjects' own.
  opposed      on a participant, an entry and a position: its `of` (or its actor's) is among `against`.
  source_kind  on an entry, a claim and a position: its citation's SOURCES.yml `kind` (record, press, secondary, ...);
  source_of    and that source's nationality. The press is told apart by its source's kind, not by a side.
A record's own language stays its own: an entry whose record isn't in English carries `original`, `lang` (a two-letter
code) and `translation` instead of `words`; a patrol's japanese.yml entries arrive the same way (`lang: ja`).
  pairs        on the engagement: each pairing in a tracked boat's claims.yml whose attack falls in the window, for the
               Sources view (guides/OPERATIONS-VIEWER.md 7.1): {attack, boat, utc, relation, note, record: {id, event,
               ship, date, time, zone, local, utc, lat, lon, lat_raw, lon_raw, original, lang, translation, note, cite}}.
               The minutes and miles between the two are computed on the page (Engage.apart), as check_crossrefs.py does.
"""
import csv
import json
import math
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import records
from build_operations import Checker, resolve_cite, sections, split
from check_track import ZONES, load, parse_coord, patrol_dir
from records import RECORDS, rel

ENG = RECORDS / "engagements"
CONVOYS = RECORDS / "convoys"
SCANS = json.load(open(RECORDS / "scans.json", encoding="utf-8"))
SIL = json.load(open(RECORDS / "silhouettes" / "silhouettes.json", encoding="utf-8"))
SIL_IDS = set(SIL["categories"]["shapes"]) | set(SIL["ships"]) | set(SIL["aircraft"])
with open(RECORDS / "army" / "units.csv", encoding="utf-8", newline="") as f:
    ARMY_UNITS = {r["unit"] for r in csv.DictReader(f)}   # a participant's `unit:` (followed from one engagement to the next)
MAX_BOATS = 3   # the page's three categorical colours are checked for three boats; check again before a fourth

FM = {"title", "short", "eyebrow", "theater", "clock", "window", "participants", "places", "against"}
PART = {"id", "name", "of", "kind", "sil", "hull", "co", "track", "convoy", "unit", "basis", "note"}
EVENT = {"at", "placed", "of", "actor", "kind", "to", "from", "title", "words", "original", "lang", "translation", "source",
         "ref", "pos", "step", "basis", "note"}
CLAIM = {"question", "answer", "weight", "source", "ref", "note"}
SHIP = {"ship", "role", "number", "from", "to", "cargo", "cargo_t", "cargo_for", "fate", "source", "page", "basis",
        "note", "sil", "sil_basis"}
CONVOY_FM = {"convoy", "name_ja", "from", "to", "via", "sailed", "arrived", "size", "cargo", "attacked_by", "sources",
             "route", "voyage", "ships"}
STOP = {"at", "place", "event", "words", "source", "basis", "approx"}
LANES = records.load_yaml(records.REFERENCE / "lanes" / "lanes.yml")["nodes"]
NATION = re.compile(r"[a-z]{2}")   # `of` and `lang`: a two-letter code (us, jp, de, it, uk, fr; de, it, ja)
WEIGHTS = {"record", "photo", "recollection", "inference", "secondary"}
BASIS = {"reported", "derived", "inferred", "assumed", "secondary"}
# what an entry is; add a word here (and to records/README.md) rather than inventing one in a single file
KINDS = {"position", "sighting", "contact_report", "received", "order", "attack", "hit", "sank", "damage", "miss",
         "rescue", "depth_charge", "air_attack", "status", "loss_list", "weather", "log", "ditched",
         # the Army's and Haynsworth's timelines
         "station", "scout", "launch", "cap", "turnback", "fight", "radar", "loss", "casualty", "report", "burial",
         "departure", "arrival", "shelled", "assignment", "move", "engage", "claim", "witness", "context", "air",
         "communique", "patrol", "warning", "raid", "fire", "kill", "probable", "silence", "scramble", "bulletin", "visit"}
# a Japanese record's event -> the mark the pages draw: sunk (red cross), hit (red ring), miss (open ring)
MARK = {"sank": "sunk", "torpedoed": "hit", "attacked_no_damage": "miss"}
AT = re.compile(r"(\d{4}-\d{2}(?:-\d{2})?)(?: (\d{4})(?: ([A-Z]{1,2}))?)?")


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def iso(t):
    return f"{t:%Y-%m-%dT%H:%MZ}" if t else None


def parse_iso(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%MZ")


class Build:
    def __init__(self):
        self.chk = Checker()
        self.problems = self.chk.problems
        self.cited = []    # every citation resolved, for check_sources.py's count

    def bad(self, where, what):
        self.problems.append(f"{where}: {what}")

    # ------------------------------------------------------------------ citations
    def cite(self, ref, where, page=""):
        """A citation -> {ref, href, label}; a problem if SOURCES.yml doesn't know it."""
        ref = str(ref or "").strip()
        if ";" in ref:   # several pages: the first is the entry's link, the rest are listed with it
            first, *rest = [self.cite(x, where) for x in re.split(r"\s*;\s*", ref) if x]
            return {**first, "ref": ref, "more": rest}
        full =f"{ref} {page}".strip() if page and ref.startswith("jacar:") else (f"{ref}/{page}" if page else ref)
        if not ref:
            self.bad(where, "no citation (ref)")
            return {"ref": "", "href": "", "label": ""}
        r = resolve_cite(full, self.chk.srcs) or resolve_cite(ref, self.chk.srcs)
        if not r:
            self.bad(where, f"citation {full!r} matches no source in SOURCES.yml")
            return {"ref": full, "href": "", "label": full}
        self.cited.append(full)
        href = SCANS.get(full) or (full if full.startswith("http") else r["href"])
        pg = page.lstrip("p") if page else r["page"]
        label = f"p. {int(pg)}" if pg and pg.isdigit() else (r["short"] if not full.startswith("http") else "page")
        src = self.source(full) or self.source(ref)
        return {"ref": full, "href": href, "label": label, "source_title": r["short"],
                "kind": src.get("kind", ""), "of": src.get("of", "")}

    def source(self, cite):
        """The SOURCES.yml entry a citation resolves to (the first whose `match` fits), or {}."""
        return next((s for pat, s in self.chk.srcs.values() if pat.match(cite)), {})

    @staticmethod
    def tagged(row):
        """A row with a `cite` -> the same row with its source's kind and nationality beside it."""
        c = row.get("cite") or {}
        return {**row, "source_kind": c.get("kind", ""), "source_of": c.get("of", "")}

    # ------------------------------------------------------------------ times
    def when(self, at, clock, where):
        """'1944-05-03 0603 H' (or a date alone, or with the engagement's clock) -> (local, utc or None, sort key)."""
        s = at.isoformat() if isinstance(at, date) else str(at or "").strip()
        m = AT.fullmatch(s)
        if not m:
            self.bad(where, f"`at` {s!r} is not 'YYYY-MM-DD HHMM Z' (a date alone, or a month, if no time is recorded)")
            return s, None, s
        day, hhmm, zone = m.groups()
        zone = zone or (clock if hhmm else "")
        if zone and zone not in ZONES:
            self.bad(where, f"zone {zone!r} is not a zone letter (check_track.ZONES)")
            zone = ""
        local = " ".join(x for x in (day, hhmm, m.group(3) or "") if x)
        if hhmm and zone and len(day) == 10:
            t = datetime.strptime(f"{day} {hhmm}", "%Y-%m-%d %H%M") - timedelta(hours=ZONES[zone])
            return local, t, iso(t)
        key = f"{day}T{hhmm[:2]}:{hhmm[2:]}" if hhmm else day
        return local, None, key

    # ------------------------------------------------------------------ nationalities and voices
    def nation(self, code, field, where, required=False):
        """`of` (and `lang`, `against`): a two-letter code as the records give a nationality, or nothing."""
        if code is None:
            if required:
                self.bad(where, f"no `{field}` (a nationality as the record gives it: us, jp, de, it, uk, fr, ...)")
            return
        if not isinstance(code, str) or not NATION.fullmatch(code):
            self.bad(where, f"{field} {code!r} is not a two-letter code (us, jp, de, it, uk, fr, ...)")

    def voice(self, e, where):
        """An entry's words: `words` (English, or our words quoting the record), or the record's own language in
        `original` with `lang` and our `translation`; one or the other, never neither."""
        if e.get("original"):
            if not e.get("translation"):
                self.bad(where, "`original` (the record's own words) needs our `translation` beside it")
            self.nation(e.get("lang"), "lang", where, required=True)
        elif e.get("translation") or e.get("lang"):
            self.bad(where, "`translation` and `lang` go with `original` (the record's words in its own language)")
        if not (e.get("words") or e.get("original")):
            self.bad(where, "no `words` and no `original`: an entry carries the record's words, or ours quoting it")

    # ------------------------------------------------------------------ a convoy
    def convoy(self, d):
        where = rel(d / "convoy.md")
        fm, body = split(d / "convoy.md")
        for k in set(fm) - CONVOY_FM:
            self.bad(where, f"unknown field {k!r} (known: {', '.join(sorted(CONVOY_FM))})")
        ships = []
        for i, s in enumerate(fm.get("ships") or [], 1):
            w = f"{where} ships #{i} ({s.get('ship', '?')})"
            for k in set(s) - SHIP:
                self.bad(w, f"unknown field {k!r}")
            if not s.get("ship"):
                self.bad(w, "`ship` is missing")
            if s.get("sil") and s["sil"] not in SIL_IDS:
                self.bad(w, f"silhouette {s['sil']!r} is not in silhouettes.yml")
            c = self.cite(s.get("source"), w, s.get("page", "")) if s.get("source") else self.cite("", w)
            ships.append({**{k: (v.isoformat() if isinstance(v, date) else v) for k, v in s.items()}, "cite": c})
        for c in fm.get("sources") or []:
            self.cite(str(c), f"{where} sources")
        for n in fm.get("route") or []:
            if n not in LANES:
                self.bad(f"{where} route", f"{n!r} is not a node in reference/lanes/lanes.yml")
        voyage = []
        for i, s in enumerate(fm.get("voyage") or [], 1):
            w = f"{where} voyage #{i}"
            for k in set(s) - STOP:
                self.bad(w, f"unknown field {k!r} (known: {', '.join(sorted(STOP))})")
            if s.get("place") and s["place"] not in LANES:
                self.bad(w, f"place {s['place']!r} is not a node in reference/lanes/lanes.yml")
            local, t, key = self.when(s.get("at"), "I", w)
            voyage.append({**s, "at": local, "utc": iso(t), "key": key, "tokyo": key if not t else iso(t + timedelta(hours=9))[:16],
                           "cite": self.cite(s.get("source"), w)})
        self.chk.links(body, where)
        out = {k: (v.isoformat() if isinstance(v, date) else v) for k, v in fm.items() if k not in ("ships", "voyage")}
        return {"id": d.name, **out, "voyage": voyage, "ships": ships, "sections": sections(body)}

    # ------------------------------------------------------------------ a patrol's own records
    def patrol(self, unit):
        """A participant's track rows, and for a boat's patrol its Japanese record and the pairings."""
        rows = load(unit)
        d = patrol_dir(unit)
        ja = {}
        jp_path = d / "japanese.yml"
        for j in records.load_yaml(jp_path) or [] if jp_path.exists() else []:
            w = f"{rel(jp_path)} {j.get('id')}"
            dd = j["date"].isoformat() if isinstance(j.get("date"), date) else str(j.get("date", ""))
            local, t, key = self.when(f"{dd} {j['time']} {j.get('zone', 'I')}" if j.get("time") else dd, "I", w)
            ja[j["id"]] = {**j, "date": dd, "local": local, "utc": t, "key": key, "unit": unit,
                           "lat": parse_coord(j.get("lat_raw", "")), "lon": parse_coord(j.get("lon_raw", "")),
                           "cite": self.cite(j.get("source"), w, j.get("page", ""))}
        pairs = []
        cl_path = d / "claims.yml"
        for x in records.load_yaml(cl_path) or [] if cl_path.exists() else []:
            w = f"{rel(cl_path)} {x.get('attack')}"
            other, _, ref = str(x["attack"]).rpartition(":")
            arows = rows if not other else load(other)
            a = next((r for r in arows if r["ref"] == ref), None)
            if a is None:
                self.bad(w, f"no attack {ref!r} in {other or unit}'s positions.csv")
            if x.get("record") not in ja:
                self.bad(w, f"no record {x.get('record')!r} in japanese.yml")
            if a is not None and x.get("record") in ja:
                pairs.append({**x, "unit": other or unit, "attack_ref": ref, "attack_utc": a["utc"], "ja": ja[x["record"]]})
        return rows, ja, pairs

    def sheets(self, p, refs):
        """A boat's attack data sheets (attacks.csv and attack_sheets.yml) for the attacks in `refs`: the torpedoes'
        rows as typed, the sheet's words, and its page. The observer view computes from them; nothing is changed."""
        d = patrol_dir(p["track"])
        path, ypath = d / "attacks.csv", d / "attack_sheets.yml"
        if not path.exists():
            return {}
        words = {}
        for e in (records.load_yaml(ypath) or []) if ypath.exists() else []:
            words.setdefault(e["attack"], []).append({k: v for k, v in e.items() if k != "attack"})
        out = {}
        for r in csv.DictReader(open(path, encoding="utf-8", newline="")):
            if r["attack"] not in refs:
                continue
            a = out.setdefault(r["attack"], {"torpedoes": [], "words": words.get(r["attack"], []),
                                             "cite": self.cite(r["page"], f"{rel(path)} {r['attack']}")})
            a["torpedoes"].append({k: v for k, v in r.items() if k not in ("attack", "page") and v != ""})
        return out

    # ------------------------------------------------------------------ an engagement
    def engagement(self, d, convoys):
        where = rel(d / "engagement.md")
        fm, body = split(d / "engagement.md")
        for k in set(fm) - FM:
            self.bad(where, f"unknown field {k!r} (known: {', '.join(sorted(FM))})")
        if not fm.get("title"):
            self.bad(where, "`title` is missing")
        clock = fm.get("clock", "")
        parts, ids = [], set()
        for p in fm.get("participants") or []:
            w = f"{where} participant {p.get('id', '?')}"
            for k in set(p) - PART:
                self.bad(w, f"unknown field {k!r}")
            if p.get("id") in ids:
                self.bad(w, "id given twice")
            ids.add(p.get("id"))
            self.nation(p.get("of"), "of", w, required=True)
            p = dict(p)
            if p.get("track"):
                try:
                    if not (patrol_dir(p["track"]) / "positions.csv").exists():
                        self.bad(w, f"track {p['track']!r} has no positions.csv")
                    y = records.ship(p["track"].split("/")[0])
                    p.setdefault("sil", y.get("silhouette") or ("submarine" if p.get("kind") == "submarine" else ""))
                    p.setdefault("hull", y.get("hull", ""))
                    p["alias"] = y["dir"].name
                except SystemExit as e:
                    self.bad(w, str(e))
            if p.get("basis") and p["basis"] not in BASIS:
                self.bad(w, f"basis {p['basis']!r} is not one of {', '.join(sorted(BASIS))}")
            if p.get("unit") and p["unit"] not in ARMY_UNITS:
                self.bad(w, f"unit {p['unit']!r} is not in records/army/units.csv")
            if p.get("convoy") and p["convoy"] not in convoys:
                self.bad(w, f"convoy {p['convoy']!r} has no records/convoys/{p['convoy']}/convoy.md")
            if p.get("sil") and p["sil"] not in SIL_IDS:
                self.bad(w, f"silhouette {p['sil']!r} is not in silhouettes.yml")
            parts.append(p)
        # the ships and boats with a track take the page's categorical colours, in order (colour follows the boat)
        coloured = [p for p in parts if p.get("track")]
        if len(coloured) > MAX_BOATS:
            self.bad(where, f"{len(coloured)} tracks; the page's colours are checked for {MAX_BOATS}: split it or check a fourth")
        for i, b in enumerate(coloured, 1):
            b["colour"] = i
        # who the page follows, whose they are, and whom they faced (the docstring: derived, never stored, but for `against`)
        for p in parts:
            p["followed"] = bool(p.get("track") or p.get("unit"))
        own = sorted({p["of"] for p in parts if p["followed"] and p.get("of")})
        against = fm.get("against")
        if against is not None:
            if not isinstance(against, list) or not against:
                self.bad(where, "`against` is a list of nationalities, as the records name the other side ([de, it])")
                against = None
            else:
                for x in against:
                    self.nation(x, "against", where)
        opposed = (lambda of: of in against) if against else (lambda of: bool(of) and of not in own)
        of_actor = {p["id"]: p.get("of", "") for p in parts}
        for p in parts:
            p["opposed"] = opposed(p.get("of", ""))
        self.chk.links(body, where)
        secs = sections(body)
        cites = {c: resolve_cite(c, self.chk.srcs) for c in re.findall(r"\[\[cite:([^\]|]+)", body)}

        # this engagement's own places
        positions = {}
        pos_path = d / "positions.csv"
        for r in csv.DictReader(open(pos_path, encoding="utf-8")) if pos_path.exists() else []:
            w = f"{rel(pos_path)} {r['id']}"
            if "of" not in r:
                self.bad(w, "positions.csv has no `of` column (the nationality of whose position it is; empty for a place)")
            self.nation(r.get("of") or None, "of", w)
            positions[r["id"]] = self.tagged({**r, "of": r.get("of", ""), "opposed": opposed(r.get("of", "")),
                                             "lat": num(r.get("lat")), "lon": num(r.get("lon")), "cite": self.cite(r.get("ref"), w)})
        for r in positions.values():
            self.place(r, positions, f"{rel(pos_path)} {r['id']}")

        # entries from events.yml
        events = []
        ev_path = d / "events.yml"
        for i, e in enumerate(records.load_yaml(ev_path) or [] if ev_path.exists() else [], 1):
            w = f"{rel(ev_path)} #{i} ({e.get('at')})"
            for k in set(e) - EVENT:
                self.bad(w, f"unknown field {k!r} (known: {', '.join(sorted(EVENT))})")
            if e.get("kind") not in KINDS:
                self.bad(w, f"kind {e.get('kind')!r} is not in the vocabulary (KINDS); add it there if it's new")
            of = e.get("of") or of_actor.get(e.get("actor"), "")
            if not of:
                self.bad(w, f"no `of` (the actor's nationality), and actor {e.get('actor')!r} is not a participant to take it from")
            else:
                self.nation(of, "of", w)
            self.voice(e, w)
            for k in ("to", "from"):
                for x in ([e[k]] if isinstance(e.get(k), str) else e.get(k) or []):
                    if x not in ids:
                        self.bad(w, f"`{k}` {x!r} is not a participant")
            if e.get("pos") and e["pos"] not in positions:
                self.bad(w, f"pos {e['pos']!r} is not in positions.csv")
            if e.get("basis") and e["basis"] not in BASIS:
                self.bad(w, f"basis {e['basis']!r} is not one of {', '.join(sorted(BASIS))}")
            local, t, key = self.when(e.get("at"), clock, w)
            ev = {k: v for k, v in e.items() if k != "at"}
            ev.update({"origin": "events", "n": i, "of": of, "local": local, "utc": iso(t), "key": key, "cite": self.cite(e.get("ref"), w)})
            if e.get("pos") in positions and positions[e["pos"]].get("lat") is not None:
                ev["lat"], ev["lon"] = positions[e["pos"]]["lat"], positions[e["pos"]]["lon"]
            events.append(ev)

        # the window: as given, or the span of the timed entries
        win = fm.get("window") or {}
        if win:
            try:
                start, end = parse_iso(win["from"]), parse_iso(win["to"])
            except (KeyError, ValueError, TypeError):
                self.bad(where, "`window` must be {from: YYYY-MM-DDTHH:MMZ, to: ...} in GMT")
                start = end = None
        else:
            ts = [parse_iso(e["utc"]) for e in events if e["utc"]]
            start, end = (min(ts) - timedelta(hours=1), max(ts) + timedelta(hours=1)) if ts else (None, None)
        if start:   # entries before or after the window (a report written days later) stay in the log, off the clock
            for e in events:
                e["outside"] = bool(e["utc"]) and not start <= parse_iso(e["utc"]) <= end

        # each participant's own record, inside the window
        tracks, fixes, seen_ja, japanese, pairs, sheets = {}, [], set(), [], [], {}
        for p in parts:
            if not p.get("track") or not start:
                continue
            rows, ja, prs = self.patrol(p["track"])
            on = [r for r in rows if r["on_track"] == "yes"]
            inside = [r for r in rows if start <= r["utc"] <= end]
            on_inside = [r for r in inside if r["on_track"] == "yes"]
            before, after = [r for r in on if r["utc"] < start][-1:], [r for r in on if r["utc"] > end][:1]
            tracks[p["id"]] = [self.fix(p, r) for r in before + on_inside + after] if on_inside else []
            if p.get("kind") == "submarine":
                fixes += [self.fix(p, r) for r in inside]
                events += self.depths(p, start, end)
                sh = self.sheets(p, {r["ref"] for r in inside if r["source"] == "attack"})
                if sh:
                    sheets[p["id"]] = sh
            for j in ja.values():
                if (p["track"], j["id"]) not in seen_ja:
                    seen_ja.add((p["track"], j["id"]))
                    japanese.append(j)
            pairs += prs
        by_unit = {p["track"]: p["id"] for p in parts if p.get("track")}
        outcome = {}
        for x in pairs:
            outcome.setdefault((by_unit.get(x["unit"]), x["attack_ref"]), []).append(x)
        moments = [self.pair(x, by_unit) for x in pairs if x["unit"] in by_unit and start <= x["attack_utc"] <= end]
        events += self.fix_events(fixes, outcome)
        events += self.japanese_events(japanese, pairs, start, end)
        events = [self.tagged({**e, "opposed": opposed(e.get("of", ""))}) for e in events]
        events.sort(key=lambda e: e["key"])

        # the map's extent: tracks inside the window, sightings, Japanese positions, this engagement's places
        pts = [(f["lon"], f["lat"]) for f in fixes] + [(e["lon"], e["lat"]) for e in events if e.get("lat") is not None]
        pts += [(r["lon"], r["lat"]) for r in positions.values() if r.get("lat") is not None]
        pts += [(f["lon"], f["lat"]) for p in parts if p.get("kind") != "submarine" for f in tracks.get(p["id"], [])]
        box = None
        if pts:
            lons, lats = [x for x, _ in pts], [y for _, y in pts]
            box = [round(min(lons) - 0.35, 3), round(min(lats) - 0.3, 3), round(max(lons) + 0.35, 3), round(max(lats) + 0.3, 3)]

        claims = []
        cl_path = d / "claims.yml"
        for i, c in enumerate(records.load_yaml(cl_path) or [] if cl_path.exists() else [], 1):
            w = f"{rel(cl_path)} #{i} ({c.get('question', '?')})"
            for k in set(c) - CLAIM:
                self.bad(w, f"unknown field {k!r}")
            if c.get("weight") not in WEIGHTS:
                self.bad(w, f"weight {c.get('weight')!r} is not one of {', '.join(sorted(WEIGHTS))}")
            claims.append(self.tagged({**c, "cite": self.cite(c.get("ref"), w)}))

        conv = {p["convoy"]: convoys[p["convoy"]] for p in parts if p.get("convoy") in convoys}
        return {"id": d.name, **{k: fm.get(k, "") for k in ("title", "short", "eyebrow", "theater", "clock")},
                "window": {"from": iso(start), "to": iso(end)} if start else None, "gmt": bool(start),
                "participants": parts, "own": own, "against": against,
                "places": fm.get("places") or [], "sections": secs, "cites": cites, "box": box,
                "tracks": tracks, "fixes": fixes, "events": events, "claims": claims, "pairs": moments,
                "positions": list(positions.values()), "convoys": conv, "sheets": sheets}

    @staticmethod
    def pair(x, by_unit):
        """A pairing from a patrol's claims.yml, for the Sources view: the attack (its ref and GMT), the boat, the
        Japanese record it is paired with as written (its time, position, original and translation, its page), and
        how (`relation`, `note`). The page does the arithmetic between the two (Engage.apart), never the build."""
        j = x["ja"]
        return {"attack": x["attack_ref"], "boat": by_unit[x["unit"]], "utc": iso(x["attack_utc"]),
                "relation": x.get("relation", ""), "note": x.get("note", ""),
                "record": {"id": j["id"], "event": j.get("event", ""), "ship": j.get("ship", ""), "convoy": j.get("convoy", ""),
                           "date": j["date"], "time": str(j.get("time") or ""), "zone": j.get("zone", "I") if j.get("time") else "",
                           "local": j["local"], "utc": iso(j["utc"]),
                           "lat": round(j["lat"], 4) if j["lat"] is not None else None, "lon": round(j["lon"], 4) if j["lon"] is not None else None,
                           "lat_raw": j.get("lat_raw", ""), "lon_raw": j.get("lon_raw", ""),
                           "original": j.get("original", ""), "lang": "ja" if j.get("original") else "",
                           "translation": j.get("translation", ""), "note": j.get("note", ""), "cite": j["cite"]}}

    def place(self, r, positions, where):
        """A positions.csv row -> lat/lon: its own, or bearing and distance from another row."""
        if r["lat"] is None and r.get("from") and not r.get("resolved"):
            base = positions.get(r["from"])
            if not base:
                self.bad(where, f"`from` {r['from']!r} is not a position here")
                return
            if base.get("lat") is None:
                self.place(base, positions, where)
            brg, dist = num(r.get("brg")), num(r.get("nm"))
            if base.get("lat") is not None and brg is not None and dist is not None:
                r["lat"] = round(base["lat"] + dist * math.cos(math.radians(brg)) / 60, 5)
                r["lon"] = round(base["lon"] + dist * math.sin(math.radians(brg)) / (60 * math.cos(math.radians(base["lat"]))), 5)
                r["resolved"] = f"{brg:g}° {dist:g} nm from {base.get('label') or r['from']}"

    def fix(self, p, r):
        return {"who": p["id"], "of": p.get("of", ""), "utc": iso(r["utc"]), "lat": round(r["lat"], 4), "lon": round(r["lon"], 4),
                "kind": r["source"], "ref": r["ref"], "on_track": r["on_track"] == "yes",
                "local": f"{r['date_fix'] or r['date']} {r['time_fix'] or r['time']} {r['zone']}",
                "raw": f"{r['lat_raw']} {r['lon_raw']}", "note": r["note"], "fix": r["fix_note"],
                "assumed": bool(r.get("assumed")), "cite": self.cite(r["page"], f"{p['track']} {r['ref']}") if r.get("page") else {}}

    def fix_events(self, fixes, outcome):
        out = []
        for f in fixes:
            if f["kind"] == "attack" or f["ref"].endswith(" fired"):
                paired = outcome.get((f["who"], f["ref"].replace(" fired", "")), [])
                out.append({"origin": "track", "of": f["of"], "actor": f["who"], "kind": "attack",
                            "title": f["ref"].replace(" fired", " (narrative)"), "words": f["note"], "local": f["local"],
                            "utc": f["utc"], "key": f["utc"], "lat": f["lat"], "lon": f["lon"], "cite": f["cite"],
                            "note": f["fix"] if (not f["on_track"] or f["fix"]) else "",
                            "outcome": [{"relation": x["relation"], "record": x["record"], "note": x.get("note", "")} for x in paired]})
            elif f["kind"] in ("ship", "air"):
                out.append({"origin": "track", "of": f["of"], "actor": f["who"], "kind": "sighting",
                            "title": {"ship": "Ship contact", "air": "Aircraft contact"}[f["kind"]] + f" ({f['ref'].split()[-1]})",
                            "words": f["note"], "local": f["local"], "utc": f["utc"], "key": f["utc"], "cite": f["cite"],
                            "target": f["kind"] == "ship", "lat": f["lat"], "lon": f["lon"]})
        return out

    def depths(self, p, start, end):
        """A boat's depth log, where transcribed: depth charges, passing depths, and orders of 300 ft or more."""
        path = patrol_dir(p["track"]) / "depths.csv"
        out = []
        for r in csv.DictReader(open(path, encoding="utf-8")) if path.exists() else []:
            if not r["time"]:
                continue
            t = datetime.strptime(f"{r['date']} {r['time']}", "%Y-%m-%d %H%M") - timedelta(hours=ZONES[r["zone"]])
            deep = r["event"] == "depth" and r["depth_ft"] and int(r["depth_ft"]) >= 300
            if start <= t <= end and (r["event"] in ("charges", "passing") or deep):
                title = {"charges": "Depth charges", "passing": f"Passing {r['depth_ft']} ft", "depth": f"Ordered {r['depth_ft']} ft"}[r["event"]]
                out.append({"origin": "depths", "of": p.get("of", ""), "actor": p["id"],
                            "kind": "depth_charge" if r["event"] == "charges" else "status",
                            "title": title + (f" ({r['charges']})" if r["charges"] else ""), "words": r["quote"],
                            "local": f"{r['date']} {r['time']} {r['zone']}", "utc": iso(t), "key": iso(t),
                            "cite": self.cite(r["page"], f"{p['track']} depths {r['date']} {r['time']}")})
        return out

    def japanese_events(self, japanese, pairs, start, end):
        """The Japanese records inside the window. A record of one day's event that gives no time is drawn at the time
        of the attack its pairing names, and says so; monthly tables and unpaired untimed records stay off the clock."""
        matched = {}
        for x in pairs:
            matched.setdefault((x["unit"], x["record"]), x)
        out = []
        for j in japanese:
            t, untimed = j["utc"], ""
            if not t and (j["unit"], j["id"]) in matched and len(j["date"]) == 10:
                x = matched[(j["unit"], j["id"])]
                t = x["attack_utc"]
                untimed = f"The record gives no time; drawn at the time of the attack it matches ({x['attack_ref']})."
            if not (t and start <= t <= end):
                continue
            secondary = str(j.get("source", "")).startswith("combinedfleet")
            ev = {"origin": "japanese", "of": "jp", "actor": j.get("ship", "") or j.get("convoy", ""),
                  "kind": j.get("event", ""), "mark": MARK.get(j.get("event", "")), "record": j["id"], "unit": j["unit"],
                  "title": (j.get("ship", "") or "").replace("; ", " and ") or j.get("convoy", ""), "ship": j.get("ship", ""),
                  "convoy": j.get("convoy", ""), "words": j.get("translation", ""), "original": j.get("original", ""),
                  "lang": "ja" if j.get("original") else "", "translation": j.get("translation", ""),
                  "local": f"{j['date']} {j.get('time') or 'no time'} I", "utc": iso(t), "key": iso(t), "cite": j["cite"],
                  "basis": "secondary" if secondary else "reported",
                  "note": " ".join(x for x in ("Secondary source (combinedfleet.com)." if secondary else "", untimed, j.get("note", "")) if x)}
            if j["lat"] is not None and j["lon"] is not None:
                ev["lat"], ev["lon"] = round(j["lat"], 4), round(j["lon"], 4)
            out.append(ev)
        return out


def convoy_summary(c, engs):
    """A convoy for site/convoys.html: its record, the engagements that met it, and where the boats saw it."""
    met = [e for e in engs if c["id"] in e["convoys"]]
    sightings, hits, attacks = [], [], []
    for e in met:
        names = {p["id"]: p.get("name", p["id"]) for p in e["participants"]}
        for f in e["fixes"]:
            if f["kind"] == "ship":
                sightings.append({"who": f["who"], "name": names.get(f["who"]), "utc": f["utc"], "lat": f["lat"],
                                  "lon": f["lon"], "ref": f["ref"], "local": f["local"], "cite": f["cite"], "engagement": e["id"]})
        for ev in e["events"]:
            if ev["origin"] == "japanese" and ev.get("lat") is not None:
                hits.append({k: ev.get(k) for k in ("title", "kind", "mark", "utc", "local", "lat", "lon", "cite", "basis")} | {"engagement": e["id"]})
            if ev["kind"] == "attack" and ev.get("lat") is not None:
                attacks.append({"who": ev["actor"], "name": names.get(ev["actor"]), "title": ev["title"], "utc": ev["utc"],
                                "lat": ev["lat"], "lon": ev["lon"], "cite": ev["cite"], "engagement": e["id"]})
    boats = sorted({p["id"]: p for e in met for p in e["participants"] if p.get("kind") == "submarine"}.values(), key=lambda p: p["id"] != "bang")
    return {**c, "engagements": [{"id": e["id"], "title": e["title"], "short": e["short"], "window": e["window"]} for e in met],
            "boats": [{"id": b["id"], "name": b["name"], "hull": b.get("hull", "")} for b in boats],
            "sightings": sightings, "hits": hits, "attacks": attacks}


def build():
    b = Build()
    convoys = {d.name: b.convoy(d) for d in sorted(CONVOYS.iterdir()) if (d / "convoy.md").exists()}
    engs = [b.engagement(d, convoys) for d in sorted(ENG.iterdir()) if (d / "engagement.md").exists()]
    index = sorted(({"id": e["id"], "title": e["title"], "short": e["short"], "theater": e["theater"],
                     "from": e["window"]["from"] if e["window"] else min((x["key"] for x in e["events"]), default=""),
                     "to": e["window"]["to"] if e["window"] else max((x["key"] for x in e["events"]), default=""),
                     "units": [{"unit": p["unit"], "name": p.get("name", p["id"]), "basis": p.get("basis", "reported")}
                               for p in e["participants"] if p.get("unit")],
                     "participants": [p.get("name", p["id"]) for p in e["participants"]],
                     "boats": [p["name"] for p in e["participants"] if p.get("kind") == "submarine"],
                     "convoys": list(e["convoys"]), "box": e["box"]} for e in engs), key=lambda x: x["from"])
    cv = sorted((convoy_summary(c, engs) for c in convoys.values()),
                key=lambda c: (c["engagements"][0]["window"] or {}).get("from", "") if c["engagements"] else str(c.get("sailed") or ""))
    out = {ENG / e["id"] / "engagement.json": e for e in engs}
    out[ENG / "index.json"] = index
    out[CONVOYS / "convoys.json"] = {"lanes": LANES, "convoys": cv}
    return b, out, engs


def text(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), default=str) + "\n"


def main():
    checking = sys.argv[1:2] == ["check"]
    b, out, engs = build()
    stale = [p for p, obj in out.items() if not p.exists() or p.read_text(encoding="utf-8") != text(obj)]
    for p in b.problems:
        print(f"PROBLEM: {p}")
    if b.problems:
        print(f"{len(b.problems)} problem(s)" + ("" if checking else "; nothing written"))
        sys.exit(1)
    if checking:
        for p in stale:
            print(f"OUT OF DATE: {rel(p)} (run uv run tools/build_engagement.py)")
        print(f"{len(engs)} engagements checked" + (f"; {len(stale)} file(s) out of date" if stale else ""))
        sys.exit(1 if stale else 0)
    for p, obj in out.items():
        p.write_text(text(obj), encoding="utf-8")
    for e in engs:
        print(f"{e['id']}: {len(e['participants'])} participants, {len(e['events'])} entries, {len(e['claims'])} claims")
    print(f"wrote {len(out)} files ({len(stale)} changed)")


if __name__ == "__main__":
    main()
