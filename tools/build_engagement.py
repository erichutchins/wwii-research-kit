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
the engagements that met it and where the boats saw it, for the convoys' subject pages and subjects.html's ledger).

  uv run tools/build_engagement.py           check everything, then write
  uv run tools/build_engagement.py check     check only; exits 1 on a problem or if a JSON file is out of date (CI)

It checks that every participant, convoy, silhouette and position named exists; that every time parses, with a zone
letter or the engagement's `clock`; that every entry and claim is cited, in a form SOURCES.yml knows; that every
[[link]] in the story resolves (a [[step:]] link names a step some entry carries); and that every pairing in a
patrol's claims.yml names an attack and a record that exist.

The story's steps (guides/OPERATIONS-VIEWER.md 3, "Story"): an entry's `step` names the step it belongs to, and a
[[step:<id>|words]] link in the story sets the page's clock to the step's time (its earliest entry's) and the map to its
framing. The front matter's `steps` gives a step its framing, `view` (the name of one of `views`, each a `name` and a
`box` [[west, south], [east, north]], or a box written inline) and its `when` in words; a step with no view is framed on
its entries' positions. The build writes `steps`, in time order, each with its time, words, view and count of entries.
`relief` (a records/relief/<name>/ or a list of them, coarse first) and `roads` (records/roads/<name>-primary.geojson)
name the map's base where the records' places are closer than a world coastline tells (Algiers); a relief built with its
rivers carries them. `fronts` names the traced situation maps (records/fronts/<name>.geojson: the front line and the unit
symbols as the staff drew them on a day), in date order, drawn as context under the records: the account shows the first,
the page the latest at the clock. A participant followed by its `unit` brings
its stations (records/army/army.json, those placed) from APPROACH_DAYS before the window to its end: where it came from.

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
               `intelligence` on a pair: the FRUPAC notes tied to its attack (frupac.yml's `attack`), each as written with
               its own time, estimated position, relation and zoom view.
US radio intelligence is read like the Japanese records: a tracked boat's frupac.yml inside the window becomes entries
(`origin: frupac`, actor FRUPAC, `of: us`, `about` the ship the note names, the words as written, `source_kind:
intelligence` through the map's citation), on the clock with zone I assumed and on the map at the position read off the
map, both said to be ours (`basis: assumed`, `pos_basis: approx`, the note). A source about the convoy, not a participant:
no track, no lane of its own on the map.
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
ARMY = {u["unit"]: u.get("stations") or [] for u in json.load(open(RECORDS / "army" / "army.json", encoding="utf-8"))["units"]}
with open(RECORDS / "army" / "relations.csv", encoding="utf-8", newline="") as f:
    RELATIONS = list(csv.DictReader(f))   # a unit's division and command on a date: ties a situation map's symbol to a subject
with open(RECORDS / "army" / "units.csv", encoding="utf-8", newline="") as f:
    ARMY_UNITS = {r["unit"] for r in csv.DictReader(f)}   # a participant's `unit:` (followed from one engagement to the next)
APPROACH_DAYS = 7   # a unit's stations this many days before the window are drawn with it: the way it came
MAX_BOATS = 3   # the page's three categorical colours are checked for three boats; check again before a fourth

FM = {"title", "short", "eyebrow", "theater", "clock", "window", "participants", "places", "against", "steps", "views",
      "relief", "roads", "fronts"}
STEP = {"view", "when"}      # a step's framing and its words; its time and entries come from events.yml
VIEW = {"name", "box"}       # a named framing of the map
PART = {"id", "name", "of", "kind", "sil", "hull", "co", "track", "convoy", "unit", "basis", "note"}
EVENT = {"at", "placed", "of", "actor", "kind", "to", "from", "title", "words", "original", "lang", "translation", "source",
         "ref", "pos", "step", "basis", "note"}
CLAIM = {"question", "answer", "weight", "source", "ref", "note"}
PAIRING = {"attack", "record", "relation", "note", "janac"}
# JANAC's entry for the loss a pairing is about (records/SCHEMA.md, "A patrol's claims"): as printed, with both its pages
JANAC = {"ship", "date", "type", "tons", "lat_raw", "lon_raw", "agent", "probable", "ref", "appendix", "note"}
SHIP = {"ship", "role", "number", "from", "to", "cargo", "cargo_t", "cargo_for", "fate", "source", "page", "basis",
        "note", "sil", "sil_basis"}
CONVOY_FM = {"convoy", "name_ja", "plain", "from", "to", "via", "sailed", "arrived", "size", "cargo", "attacked_by", "sources",
             "route", "voyage", "ships"}
STOP = {"at", "place", "event", "words", "source", "basis", "approx"}
LANES = records.load_yaml(records.REFERENCE / "lanes" / "lanes.yml")["nodes"]
NATION = re.compile(r"[a-z]{2}")   # `of` and `lang`: a two-letter code (us, jp, de, it, uk, fr; de, it, ja)
WEIGHTS = {"record", "photo", "recollection", "inference", "secondary"}
BASIS = {"reported", "derived", "inferred", "assumed", "secondary"}
# what an entry is; add a word here (and to records/README.md) rather than inventing one in a single file
# routes.yml: a path's fields, and how it is known: a course or track the record types or draws to scale (reported), a
# sketch map's line (sketched), or a line between places where the record gives no path (inferred)
ROUTE = {"id", "label", "of", "actor", "by", "basis", "arrow", "points", "from", "to", "course", "drawn_km", "time", "source", "ref", "note"}
ROUTE_BASIS = {"reported", "sketched", "inferred"}
ROUTE_BY = {"air", "ground", "sea"}   # what moved: the page marks an aircraft's path apart from a unit's or a ship's
# a ship's log.yml (records/SCHEMA.md, "A ship's log"): her own lines of helm, course and speed between her fixes, from
# which the build reckons her path (a route of basis `reckoned`: computed here, never hand-entered)
LOG = {"date", "time", "zone", "time_fix", "fix_note", "helm", "course", "speed", "event", "depth_m", "charges", "original",
       "translation", "source", "page", "note"}
LOG_EVENT = {"contact_report", "charges_heard", "action_stations", "stand_down", "ship_torpedoed", "depth_charge",
             "sonar_contact", "search", "survivors", "rescue", "rejoin", "torpedo_wake", "torpedoed", "fire", "beached"}
# a log line's event -> the entry's kind on the page (KINDS); the rest are `log`, a line of her log
LOG_KIND = {"depth_charge": "depth_charge", "contact_report": "contact_report", "sonar_contact": "sighting", "rescue": "rescue",
            "survivors": "rescue", "ship_torpedoed": "witness", "torpedo_wake": "sighting", "torpedoed": "hit", "fire": "damage", "beached": "damage"}
COURSE = re.compile(r"(?:([NS]) (\d+)° ([EW])|([NSEW]))")
# reach.yml: a weapon's range round a position; basis says how much is the record's: the weapon and the place both in the
# unit's records (reported), the weapon inferred (a sister battery's, say), or the place assumed (near the unit it defended)
REACH = {"id", "label", "of", "actor", "at", "weapon", "range_yd", "basis", "source", "ref", "note"}
REACH_BASIS = {"reported", "inferred", "assumed"}
KINDS = {"position", "sighting", "contact_report", "received", "order", "attack", "hit", "sank", "damage", "miss",
         "rescue", "depth_charge", "air_attack", "status", "loss_list", "weather", "log", "ditched",
         # the Army's and Haynsworth's timelines
         "station", "scout", "launch", "cap", "turnback", "fight", "radar", "loss", "casualty", "report", "burial",
         "departure", "arrival", "shelled", "assignment", "move", "engage", "claim", "witness", "context", "air",
         "communique", "patrol", "warning", "raid", "fire", "kill", "probable", "silence", "scramble", "bulletin", "visit",
         # US radio intelligence (a FRUPAC note of a ship attacked; the note's own word stays in `frupac.event`)
         "attacked"}
# a Japanese record's event -> the mark the pages draw: sunk (red cross), hit (red ring), miss (open ring)
MARK = {"sank": "sunk", "torpedoed": "hit", "attacked_no_damage": "miss"}
# a FRUPAC note (records/README.md, frupac.yml): its fields, and its `event` -> the kind the pages know (KINDS). A note
# whose event isn't here fails the build: add the word here (and its kind to KINDS if none fits) rather than in a file.
FRUPAC = {"id", "map", "map_date", "view", "text", "dtg", "date", "time", "lat_est", "lon_est", "ship", "event", "attack",
          "relation", "note"}
FRUPAC_KIND = {"torpedoed": "hit", "sank": "sank", "sinking": "damage", "attacked": "attacked", "torpedo_attack": "attacked",
               "attack_reported": "attacked", "torpedo_track": "sighting", "sub_contact": "sighting", "sub_sighted": "sighting",
               "df_sub": "position", "position": "position", "convoy": "position", "arrival": "arrival", "claim": "claim",
               "contact_report": "report"}
# the entry's title where the note names no ship: the event in words
FRUPAC_TITLE = {"df_sub": "D/F fix on a submarine", "sub_contact": "Submarine contact", "sub_sighted": "Submarine sighted",
                "torpedo_track": "Torpedo track", "torpedo_attack": "Torpedo attack", "attack_reported": "Attack reported",
                "attacked": "Ship attacked", "torpedoed": "Ship torpedoed", "sinking": "In danger of sinking", "sank": "Ship sunk",
                "convoy": "Convoy", "position": "Position", "arrival": "Arrival", "claim": "Claim", "contact_report": "Contact report"}
FRUPAC_RELATION = {"match", "candidate", "context"}
FRUPAC_ZOOM = "https://texashistory.unt.edu/ark:/67531/{map}/m1/1/zoom/"
# what is ours in a FRUPAC entry, said on the entry (the README's assumption paragraph): the zone, and the position
FRUPAC_ZONE = "Zone I (Tokyo time) assumed: the note writes no zone letter, and the matched notes bear it out."
FRUPAC_POS = "The position is read off the map from where the mark sits (about ±0.1–0.3°), not the note's."
AT = re.compile(r"(\d{4}-\d{2}(?:-\d{2})?)(?: (\d{4})(?: ([A-Z]{1,2}))?)?")


def unplaced(unit, ref):
    """True if the patrol's positions.csv has the attack `ref` but check_track's load() left it out because its
    position has an unread figure (a `?`): paired in claims.yml, not drawn."""
    path = patrol_dir(unit) / "positions.csv"
    if not path.exists():
        return False
    with open(path, newline="", encoding="utf-8") as fh:
        return any(r.get("source") == "attack" and r.get("ref") == ref for r in csv.DictReader(fh))


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
            for k in set(x) - PAIRING:
                self.bad(w, f"unknown field {k!r} (known: {', '.join(sorted(PAIRING))})")
            x = {**x, "janac": [self.janac(e, f"{w} janac {e.get('ship') if isinstance(e, dict) else e!r}") for e in x.get("janac") or []]}
            other, _, ref = str(x["attack"]).rpartition(":")
            arows = rows if not other else load(other)
            a = next((r for r in arows if r["ref"] == ref), None)
            if a is None and not unplaced(other or unit, ref):
                self.bad(w, f"no attack {ref!r} in {other or unit}'s positions.csv")
            if x.get("record") not in ja:
                self.bad(w, f"no record {x.get('record')!r} in japanese.yml")
            if a is not None and x.get("record") in ja:
                pairs.append({**x, "unit": other or unit, "attack_ref": ref, "attack_utc": a["utc"], "ja": ja[x["record"]]})
        return rows, ja, pairs

    def janac(self, e, where):
        """A pairing's `janac` entry -> the loss as JANAC prints it, checked: the ship, the date, the agent as printed
        (a boat's name from the appendix, or "Submarine", "Army Mine" ...), `probable` (the list's asterisk), the list's
        page (`ref`, janac:3 or janac:4) and, for a submarine's credit, the appendix's (`appendix`, janac:6)."""
        if not isinstance(e, dict):
            self.bad(where, "a janac entry is a mapping (ship, date, agent, probable, ref, ...)")
            return {}
        for k in set(e) - JANAC:
            self.bad(where, f"unknown field {k!r} (known: {', '.join(sorted(JANAC))})")
        for k in ("ship", "date", "agent", "ref"):
            if not e.get(k):
                self.bad(where, f"no {k!r}")
        if not isinstance(e.get("probable"), bool):
            self.bad(where, "`probable` is true (the list prints the agent with an asterisk) or false")
        if e.get("ref") and not re.match(r"janac:[34]/p\d+$", str(e["ref"])):
            self.bad(where, f"`ref` {e['ref']!r} is a page of the lists (janac:3/pN or janac:4/pN)")
        if e.get("appendix") and not re.match(r"janac:6/p\d+$", str(e["appendix"])):
            self.bad(where, f"`appendix` {e['appendix']!r} is a page of the appendix (janac:6/pN)")
        d = e.get("date")
        return {"ship": str(e.get("ship") or ""), "date": d.isoformat() if isinstance(d, date) else str(d or ""),
                "type": str(e.get("type") or ""), "tons": str(e.get("tons") or ""), "lat_raw": str(e.get("lat_raw") or ""), "lon_raw": str(e.get("lon_raw") or ""),
                "lat": parse_coord(str(e.get("lat_raw") or "")), "lon": parse_coord(str(e.get("lon_raw") or "")),
                "agent": str(e.get("agent") or ""), "probable": e.get("probable") is True, "note": str(e.get("note") or "").strip(),
                "cite": self.cite(e.get("ref"), where), **({"appendix": self.cite(e["appendix"], where)} if e.get("appendix") else {})}

    def frupac(self, unit, rows, path=None):
        """A boat's FRUPAC notes (frupac.yml, records/README.md "US radio intelligence"), each checked and read for the
        pages: its time in GMT with zone I assumed (the notes write no zone; the README's assumption), its position as
        estimated from the map (`lat_est`/`lon_est`, or none), the attack it is tied to (a row in `rows`, or another
        boat's as `<boat>/<n>:<ref>`) and its map's citation. `path` names the file when it isn't the patrol's own (tests)."""
        path = path or patrol_dir(unit) / "frupac.yml"
        out = []
        for i, f in enumerate(records.load_yaml(path) or [] if path.exists() else [], 1):
            w = f"{rel(path)} {f.get('id') or f'#{i}'}"
            for k in set(f) - FRUPAC:
                self.bad(w, f"unknown field {k!r} (known: {', '.join(sorted(FRUPAC))})")
            if f.get("event") not in FRUPAC_KIND:
                self.bad(w, f"event {f.get('event')!r} has no kind in FRUPAC_KIND; add it there rather than in a file")
            if f.get("relation") and f["relation"] not in FRUPAC_RELATION:
                self.bad(w, f"relation {f['relation']!r} is not one of {', '.join(sorted(FRUPAC_RELATION))}")
            if not f.get("text"):
                self.bad(w, "no `text` (the note as written)")
            dd = f["date"].isoformat() if isinstance(f.get("date"), date) else str(f.get("date", ""))
            time = str(f.get("time") or "")
            local, t, key = self.when(f"{dd} {time} I" if time else dd, "I", w)
            lat, lon = num(f.get("lat_est")), num(f.get("lon_est"))
            if (lat is None) != (lon is None):
                self.bad(w, "`lat_est` and `lon_est` go together")
            attack_unit, attack_utc = "", None
            other, _, ref = str(f.get("attack") or "").rpartition(":")
            if ref:
                arows = rows if not other else load(other)
                a = next((r for r in arows if r["ref"] == ref), None)
                if a is None:
                    self.bad(w, f"no attack {ref!r} in {other or unit}'s positions.csv")
                else:
                    attack_unit, attack_utc = other or unit, a["utc"]
            m = str(f.get("map", ""))
            zoom = FRUPAC_ZOOM.format(map=m) + (f"?{f['view']}" if f.get("view") else "")
            cite = {**self.cite(m, w), "href": zoom, "label": "map"}   # the map, framed on the note: where it is legible
            out.append({**f, "id": str(f.get("id", "")), "date": dd, "time": time, "map": m, "map_date": str(f.get("map_date", "")),
                        "dtg": str(f.get("dtg") or ""), "ship": str(f.get("ship") or ""), "local": local, "utc": t, "key": key,
                        "unit": unit, "lat": lat, "lon": lon, "attack_ref": ref, "attack_unit": attack_unit, "attack_utc": attack_utc,
                        "zoom": zoom, "cite": cite})
        return out

    def frupac_events(self, notes, start, end):
        """The FRUPAC notes inside the window as entries: US intelligence about the other side's ship (`about`), its words
        as written, placed on the clock with zone I assumed and on the map at its estimated position, and said to be so
        (`basis: assumed`, `pos_basis: approx`, the note). A note of one day's event with no time is drawn at the time of
        the attack it is tied to, and says so; one tied to nothing stays off the clock. `frupac` carries the note's own
        fields (its id, event, relation, attack, map and zoom view) for the pages."""
        out = []
        for f in notes:
            t, untimed = f["utc"], ""
            if not t and f["attack_utc"] and len(f["date"]) == 10:
                t = f["attack_utc"]
                untimed = f"The note gives no time; drawn at the time of the attack it is tied to ({f['attack_ref']})."
            if not (t and start <= t <= end):
                continue
            ship = f["ship"]
            ev = {"origin": "frupac", "of": "us", "actor": "FRUPAC", "about": ship, "kind": FRUPAC_KIND.get(f.get("event"), "report"),
                  "title": ship.replace("; ", " and ") or FRUPAC_TITLE.get(f.get("event"), str(f.get("event", "")).replace("_", " ")),
                  "words": f.get("text", ""), "local": f["local"], "utc": iso(t), "key": iso(t), "unit": f["unit"],
                  "source": f"FRUPAC war map, {f['map_date']}", "cite": f["cite"], "basis": "assumed",
                  "note": " ".join(x for x in (untimed, FRUPAC_ZONE if f["utc"] else "", FRUPAC_POS if f["lat"] is not None else "",
                                               f.get("note", "")) if x),
                  "frupac": {k: f.get(k, "") for k in ("id", "ship", "event", "attack", "relation", "map", "map_date", "view", "zoom", "dtg")}}
            if f["lat"] is not None:
                ev.update({"lat": round(f["lat"], 4), "lon": round(f["lon"], 4), "pos_basis": "approx", "pos_note": FRUPAC_POS})
            out.append(ev)
        return out

    @staticmethod
    def intel(f):
        """A FRUPAC note beside the attack it is tied to, for a pair's `intelligence` (the Sources view): the note as
        written, its own time (none when it gives none: the view says so, and computes nothing from a placed time), its
        estimated position, how it relates to the attack (`relation`, `note`), and its map's zoom view."""
        return {"id": f["id"], "event": f.get("event", ""), "ship": f["ship"], "relation": f.get("relation", ""), "note": f.get("note", ""),
                "map": f["map"], "map_date": f["map_date"], "view": f.get("view", ""), "zoom": f["zoom"], "text": f.get("text", ""),
                "dtg": f["dtg"], "date": f["date"], "time": f["time"], "local": f["local"], "utc": iso(f["utc"]),
                "lat": round(f["lat"], 4) if f["lat"] is not None else None, "lon": round(f["lon"], 4) if f["lon"] is not None else None,
                "cite": f["cite"]}

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
        own = sorted({p["of"] for p in parts if p["followed"] and p.get("of") and not p["opposed"]})
        # our side's ships and boats with a track take the page's categorical colours, in order (colour follows the boat);
        # the other side's (an escort followed through her own diary) is drawn in its side's ink, as every opposed mark is
        coloured = [p for p in parts if p.get("track") and not p["opposed"]]
        if len(coloured) > MAX_BOATS:
            self.bad(where, f"{len(coloured)} tracks; the page's colours are checked for {MAX_BOATS}: split it or check a fourth")
        for i, b in enumerate(coloured, 1):
            b["colour"] = i
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
                                             "lat": num(r.get("lat")), "lon": num(r.get("lon")),
                                             "lat2": num(r.get("lat2")), "lon2": num(r.get("lon2")), "cite": self.cite(r.get("ref"), w)})
        for r in positions.values():
            self.place(r, positions, f"{rel(pos_path)} {r['id']}")

        # routes.yml: paths, each a run of points, a straight line between two of this engagement's positions, or a typed
        # course drawn back from one (records/README.md, "An engagement's routes")
        routes = []
        rt_path = d / "routes.yml"
        for i, rt in enumerate(records.load_yaml(rt_path) or [] if rt_path.exists() else [], 1):
            r = self.route(rt, positions, f"{rel(rt_path)} #{i} ({rt.get('id')})")
            if r and r.get("actor") and r["actor"] not in ids:
                self.bad(f"{rel(rt_path)} #{i} ({rt.get('id')})", f"actor {r['actor']!r} is not a participant (a route's actor takes its colour)")
            if r:
                routes.append({**r, "opposed": opposed(r["of"])})

        # reach.yml: a weapon's range drawn as a ring round where it was (records/README.md, "An engagement's reach")
        rings = []
        rc_path = d / "reach.yml"
        for i, rc in enumerate(records.load_yaml(rc_path) or [] if rc_path.exists() else [], 1):
            r = self.ring(rc, positions, f"{rel(rc_path)} #{i} ({rc.get('id')})")
            if r and r.get("actor") and r["actor"] not in ids:
                self.bad(f"{rel(rc_path)} #{i} ({rc.get('id')})", f"actor {r['actor']!r} is not a participant (a ring's actor takes its colour)")
            if r:
                rings.append({**r, "opposed": opposed(r["of"])})

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

        # the story's steps: every [[step:]] link names a step some entry carries; the front matter frames them
        carried = {e["step"] for e in events if e.get("step")}
        self.chk.links(body, where, steps=carried)
        views = self.views(fm.get("views"), where)
        steps = self.steps(fm.get("steps"), views, events, positions, carried, where)
        relief = self.relief(fm.get("relief"), where)
        roads = self.roads(fm.get("roads"), where)
        fronts = [f for f in (self.front(n, where, parts) for n in (fm.get("fronts") or [])) if f]
        if [f["date"] for f in fronts] != sorted(f["date"] for f in fronts):
            self.bad(where, "`fronts` must be in date order")

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
        tracks, fixes, seen_ja, japanese, pairs, sheets, notes, dives, water = {}, [], set(), [], [], {}, [], {}, {}
        reckoned = []   # a ship's path reckoned from her log (routes of basis `reckoned`)
        for p in parts:
            if not p.get("track") or not start:
                continue
            rows, ja, prs = self.patrol(p["track"])
            notes += self.frupac(p["track"], rows)
            on = [r for r in rows if r["on_track"] == "yes"]
            inside = [r for r in rows if start <= r["utc"] <= end]
            on_inside = [r for r in inside if r["on_track"] == "yes"]
            # the fix either side of the window carries the line in and out. A boat's patrol is one record, so its next
            # fix serves however far off; a ship's diaries can leave months between (an escort read for two convoys),
            # so hers serves only within two days, and she isn't drawn straight across the gap
            near = timedelta(days=2) if "/" not in p["track"] else timedelta.max / 2
            before = [r for r in on if r["utc"] < start and start - r["utc"] <= near][-1:]
            after = [r for r in on if r["utc"] > end and r["utc"] - end <= near][:1]
            tracks[p["id"]] = [self.fix(p, r) for r in before + on_inside + after] if on_inside else []
            rk, logged = self.reckon(p, rows, start, end)
            if rk:
                # her reckoned path is her track: it replaces the straight line between her fixes (the more accurate
                # path wins), and her written fixes are drawn as reported positions on it
                timed = rk.pop("timed")
                tracks[p["id"]] = [{"who": p["id"], "of": p.get("of", ""), "utc": iso(t), "lat": round(la, 4), "lon": round(lo, 4),
                                    "kind": "reckoned", "ref": "", "on_track": True, "local": "", "raw": "", "note": "", "fix": "",
                                    "assumed": False, "cite": rk["cite"]} for t, la, lo in timed]
                p["reckoned"] = True
                fixes += [self.fix(p, r) for r in inside]
                reckoned.append(rk)
            events += logged
            if p.get("kind") == "submarine":
                fixes += [self.fix(p, r) for r in inside]
                events += self.depths(p, start, end)
                st = self.dive_states(p, start, end)
                if st:
                    dives[p["id"]] = st
                    water[p["id"]] = self.water(p, start, end)
                sh = self.sheets(p, {r["ref"] for r in inside if r["source"] == "attack"})
                if sh:
                    sheets[p["id"]] = sh
            for j in ja.values():
                if (p["track"], j["id"]) not in seen_ja:
                    seen_ja.add((p["track"], j["id"]))
                    japanese.append(j)
            pairs += prs
        # each unit's stations, placed, from APPROACH_DAYS before the window to its end (its own record's places)
        stations = {}
        for p in parts:
            if p.get("unit") and start and end:
                rows = [r for r in ARMY.get(p["unit"], []) if r.get("lat") is not None
                        and (start - timedelta(days=APPROACH_DAYS)).date().isoformat() <= r["date"] <= end.date().isoformat()]
                stations[p["id"]] = [{"date": r["date"], "lat": r["lat"], "lon": r["lon"], "place": r.get("place", ""),
                                      "words": r.get("station", ""), "precision": r.get("precision", ""),
                                      "inside": r["date"] >= start.date().isoformat(),
                                      "cite": self.cite(r.get("page"), f"{where}: {p['unit']} {r['date']}")} for r in rows]
        by_unit = {p["track"]: p["id"] for p in parts if p.get("track")}
        outcome = {}
        for x in pairs:
            outcome.setdefault((by_unit.get(x["unit"]), x["attack_ref"]), []).append(x)
        moments = [self.pair(x, by_unit) for x in pairs if x["unit"] in by_unit and start <= x["attack_utc"] <= end]
        intel = self.frupac_events(notes, start, end)
        inside = {(e["unit"], e["frupac"]["id"]) for e in intel}
        for m in moments:   # the FRUPAC notes tied to the pair's attack, among those inside the window
            m["intelligence"] = [self.intel(f) for f in notes if (f["unit"], f["id"]) in inside
                                 and by_unit.get(f["attack_unit"]) == m["boat"] and f["attack_ref"] == m["attack"]]
        events += self.fix_events(fixes, outcome)
        events += self.japanese_events(japanese, pairs, start, end)
        events += intel
        events = [self.tagged({**e, "opposed": opposed(e.get("of", ""))}) for e in events]
        events.sort(key=lambda e: e["key"])

        # the map's extent: tracks inside the window, sightings, Japanese positions, this engagement's places
        pts = [(f["lon"], f["lat"]) for f in fixes] + [(e["lon"], e["lat"]) for e in events if e.get("lat") is not None]
        pts += [(r["lon"], r["lat"]) for r in positions.values() if r.get("lat") is not None]
        pts += [(f["lon"], f["lat"]) for p in parts if p.get("kind") != "submarine" for f in tracks.get(p["id"], [])]
        pts += [(r["lon"], r["lat"]) for rows in stations.values() for r in rows]
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
                "steps": steps, "relief": relief, "roads": roads, "fronts": fronts, "stations": stations,
                "tracks": tracks, "dives": dives, "water": water, "fixes": fixes, "events": events, "claims": claims, "pairs": moments,
                "positions": list(positions.values()), **({"routes": routes + reckoned} if routes or reckoned else {}), **({"rings": rings} if rings else {}), "convoys": conv, "sheets": sheets}

    # ------------------------------------------------------------------ the story's steps and the map's base
    @staticmethod
    def box_ok(b):
        """[[west, south], [east, north]], west of east and south of north."""
        try:
            (w, s), (e, n) = b
            return all(isinstance(v, (int, float)) for v in (w, s, e, n)) and w < e and s < n
        except (TypeError, ValueError):
            return False

    def views(self, fm_views, where):
        """`views`: name -> {name: words, box: [[w, s], [e, n]]}, the map's framings the steps name."""
        out = {}
        for vid, v in (fm_views or {}).items() if isinstance(fm_views, dict) else []:
            w = f"{where} view {vid}"
            if not isinstance(v, dict):
                self.bad(w, "a view is {name: words, box: [[west, south], [east, north]]}")
                continue
            for k in set(v) - VIEW:
                self.bad(w, f"unknown field {k!r} (known: {', '.join(sorted(VIEW))})")
            if not self.box_ok(v.get("box")):
                self.bad(w, "`box` is [[west, south], [east, north]], west of east and south of north")
                continue
            out[vid] = {"name": str(v.get("name") or vid), "box": v["box"]}
        if fm_views is not None and not isinstance(fm_views, dict):
            self.bad(where, "`views` is a mapping of a view's id to {name, box}")
        return out

    def steps(self, fm_steps, views, events, positions, carried, where):
        """The steps the entries carry, in time order, each framed: by its front-matter `view` (a name in `views`, or a
        box inline), or else on its own entries' positions, padded as the map's box is; `when` in words, if given."""
        fm_steps = fm_steps or {}
        if not isinstance(fm_steps, dict):
            self.bad(where, "`steps` is a mapping of a step's id to {view, when}")
            fm_steps = {}
        for sid, st in fm_steps.items():
            w = f"{where} step {sid}"
            if sid not in carried:
                self.bad(w, f"no entry in events.yml carries step {sid!r}")
            if not isinstance(st, dict):
                self.bad(w, "a step is {view: a view's id or [[west, south], [east, north]], when: words}")
                continue
            for k in set(st) - STEP:
                self.bad(w, f"unknown field {k!r} (known: {', '.join(sorted(STEP))})")
            v = st.get("view")
            if v is not None and not (isinstance(v, str) and v in views) and not self.box_ok(v):
                self.bad(w, f"view {v!r} is not one of the front matter's views ({', '.join(sorted(views)) or 'none'}) or a box")
        out = []
        for sid in carried:
            es = [e for e in events if e.get("step") == sid]
            # the step's time: its earliest entry on the clock (one with a GMT time), else its earliest by key
            first = min([e for e in es if e["utc"]] or es, key=lambda e: e["utc"] or e["key"])
            given = fm_steps.get(sid)
            st = given if isinstance(given, dict) else {}
            v = st.get("view")
            if isinstance(v, str) and v in views:
                view = {**views[v], "id": v, "basis": "given"}
            elif self.box_ok(v):
                view = {"name": "", "box": v, "basis": "given"}
            else:
                pts = [(positions[e["pos"]]["lon"], positions[e["pos"]]["lat"]) for e in es
                       if e.get("pos") in positions and positions[e["pos"]].get("lat") is not None]
                pts += [(positions[e["pos"]]["lon2"], positions[e["pos"]]["lat2"]) for e in es
                        if e.get("pos") in positions and positions[e["pos"]].get("lat2") is not None]
                view = None
                if pts:
                    lons, lats = [x for x, _ in pts], [y for _, y in pts]
                    view = {"name": "", "basis": "entries",
                            "box": [[round(min(lons) - 0.35, 3), round(min(lats) - 0.3, 3)], [round(max(lons) + 0.35, 3), round(max(lats) + 0.3, 3)]]}
            out.append({"id": sid, "utc": first["utc"], "key": first["key"], "local": first["local"],
                        "when": str(st.get("when") or ""), "view": view, "entries": len(es)})
        return sorted(out, key=lambda x: (x["utc"] or x["key"], x["id"]))

    def relief(self, names, where):
        """`relief`: a records/relief/<name>/ (or a list, coarse first), each with its box from relief.json."""
        out = []
        for n in ([names] if isinstance(names, str) else names or []):
            path = RECORDS / "relief" / str(n) / "relief.json"
            if not path.exists():
                self.bad(where, f"relief {n!r} has no records/relief/{n}/relief.json (tools/build_relief.py)")
                continue
            meta = json.load(open(path, encoding="utf-8"))
            out.append({"name": str(n), "box": meta["box"], "source": meta.get("source", ""), "rivers": bool(meta.get("rivers"))})
        return out

    def roads(self, name, where):
        """`roads`: a traced road map, records/roads/<name>-primary.geojson."""
        if not name:
            return ""
        if not (RECORDS / "roads" / f"{name}-primary.geojson").exists():
            self.bad(where, f"roads {name!r} has no records/roads/{name}-primary.geojson")
            return ""
        return str(name)

    @staticmethod
    def commands(unit, date):
        """The units a unit belonged to or was under on a date, from army/relations.csv (part_of, under_command,
        attached_to; an undated row always holds), two steps up: [(other, [(relation, other, page), ...]), ...]."""
        def holds(r):
            lo, hi = r["from"].strip("."), r["to"].strip(".")
            return (not lo or lo <= date) and (not hi or date <= hi)
        out, todo = [], [(unit, [])]
        while todo:
            u, path = todo.pop(0)
            for r in RELATIONS:
                if r["unit"] == u and r["relation"] in ("part_of", "under_command", "attached_to") and holds(r):
                    step = path + [(r["relation"], r["other"], r["page"])]
                    out.append((r["other"], step))
                    if len(step) < 2:
                        todo.append((r["other"], step))
        return out

    def front(self, name, where, parts=()):
        """`front`: a traced situation map, records/fronts/<name>.geojson: its date, hour, title, citation and fit, and
        `ties`: which of its symbols are a followed unit, or its division or command on the map's date (army/relations.csv),
        each with the relations that tie it and their citations."""
        if not name:
            return None
        path = RECORDS / "fronts" / f"{name}.geojson"
        if not path.exists():
            self.bad(where, f"front {name!r} has no records/fronts/{name}.geojson (tools/trace_front.py)")
            return None
        gj = json.load(open(path, encoding="utf-8"))
        meta = gj["properties"]
        on_map = {f["properties"].get("unit") for f in gj["features"] if f["properties"].get("unit")}
        ties = {}
        for p in parts:
            if not p.get("unit"):
                continue
            for other, path in [(p["unit"], [])] + self.commands(p["unit"], meta["date"]):
                if other in on_map:
                    ties.setdefault(other, []).append({"participant": p["id"], "path": [
                        {"relation": rel, "other": o, "cite": self.cite(pg, f"{where}: {p['unit']} {rel} {o}")} for rel, o, pg in path]})
        return {"name": str(name), **{k: meta[k] for k in ("date", "as_of", "title", "fit_km", "box")},
                "cite": self.cite(meta["cite"], where), "ties": ties}

    @staticmethod
    def pair(x, by_unit):
        """A pairing from a patrol's claims.yml, for the Sources view: the attack (its ref and GMT), the boat, the
        Japanese record it is paired with as written (its time, position, original and translation, its page), and
        how (`relation`, `note`). The page does the arithmetic between the two (Engage.apart), never the build."""
        j = x["ja"]
        return {"attack": x["attack_ref"], "boat": by_unit[x["unit"]], "utc": iso(x["attack_utc"]),
                "relation": x.get("relation", ""), "note": x.get("note", ""), "janac": x.get("janac") or [],
                "record": {"id": j["id"], "event": j.get("event", ""), "ship": j.get("ship", ""), "convoy": j.get("convoy", ""),
                           "date": j["date"], "time": str(j.get("time") or ""), "zone": j.get("zone", "I") if j.get("time") else "",
                           "local": j["local"], "utc": iso(j["utc"]),
                           "lat": round(j["lat"], 4) if j["lat"] is not None else None, "lon": round(j["lon"], 4) if j["lon"] is not None else None,
                           "lat_raw": j.get("lat_raw", ""), "lon_raw": j.get("lon_raw", ""),
                           "original": j.get("original", ""), "lang": "ja" if j.get("original") else "",
                           "translation": j.get("translation", ""), "note": j.get("note", ""), "cite": j["cite"]}}

    def ring(self, rc, positions, where):
        """A reach.yml entry -> its ring: the place it is drawn round and the range in km (a yard is 0.9144 m), or None."""
        for k in set(rc) - REACH:
            self.bad(where, f"unknown field {k!r} (known: {', '.join(sorted(REACH))})")
        if rc.get("basis") not in REACH_BASIS:
            self.bad(where, f"basis {rc.get('basis')!r} is not one of {', '.join(sorted(REACH_BASIS))}")
        self.nation(rc.get("of") or None, "of", where, required=True)
        at, yd = positions.get(rc.get("at")), num(rc.get("range_yd"))
        if not at or at.get("lat") is None:
            self.bad(where, f"`at` {rc.get('at')!r} is not a placed position in positions.csv")
            return None
        if yd is None or yd <= 0:
            self.bad(where, "`range_yd` must be the range in yards, as the manual gives it")
            return None
        return {"id": str(rc.get("id") or ""), "label": str(rc.get("label") or ""), "of": rc.get("of") or "",
                **({"actor": str(rc["actor"])} if rc.get("actor") else {}), "at": rc["at"], "lon": at["lon"], "lat": at["lat"], "range_yd": yd, "km": round(yd * 0.9144 / 1000, 3),
                "basis": rc.get("basis"), "weapon": str(rc.get("weapon") or ""), "source": str(rc.get("source") or ""),
                "note": str(rc.get("note") or "").strip(), "cite": self.cite(rc.get("ref"), where)}

    def route(self, rt, positions, where):
        """A routes.yml entry -> its points: given (each a {lat, lon} or a position id), a straight line between two
        positions (`from`, `to`: the path between them isn't recorded), or a course as typed drawn back from a position
        (`to`, `course` in degrees, `drawn_km`: the line's length is ours, not the record's)."""
        for k in set(rt) - ROUTE:
            self.bad(where, f"unknown field {k!r} (known: {', '.join(sorted(ROUTE))})")
        if rt.get("basis") not in ROUTE_BASIS:
            self.bad(where, f"basis {rt.get('basis')!r} is not one of {', '.join(sorted(ROUTE_BASIS))}")
        self.nation(rt.get("of") or None, "of", where, required=True)
        if rt.get("by") not in ROUTE_BY:
            self.bad(where, f"by {rt.get('by')!r} is not one of {', '.join(sorted(ROUTE_BY))}")

        def at(pid):
            p = positions.get(pid)
            if not p or p.get("lat") is None:
                self.bad(where, f"{pid!r} is not a placed position in positions.csv")
                return None
            return [p["lon"], p["lat"]]
        pts, how = [], ""
        if rt.get("points"):
            for q in rt["points"]:
                if isinstance(q, str):
                    pts.append(at(q))
                elif isinstance(q, dict) and num(q.get("lat")) is not None and num(q.get("lon")) is not None:
                    pts.append([num(q["lon"]), num(q["lat"])])
                else:
                    self.bad(where, f"point {q!r} is neither {{lat, lon}} nor a position id")
            how = "as given"
        elif rt.get("to") and rt.get("course") is not None:
            end, course, km = at(rt["to"]), num(rt.get("course")), num(rt.get("drawn_km"))
            if course is None or km is None:
                self.bad(where, "a course needs `course` (degrees) and `drawn_km` (the length to draw)")
            elif end:
                back = math.radians(course + 180)
                pts = [[end[0] + km * math.sin(back) / (111.32 * math.cos(math.radians(end[1]))), end[1] + km * math.cos(back) / 110.57], end]
                how = f"the course as typed, {course:g}°, into {positions[rt['to']].get('label') or rt['to']}; the line's length ({km:g} km) is drawn, not recorded"
        elif rt.get("from") and rt.get("to"):
            pts = [at(rt["from"]), at(rt["to"])]
            how = "straight between two places: the path between them is not recorded"
        else:
            self.bad(where, "a route needs `points`, `from` and `to`, or `to` with `course` and `drawn_km`")
        if len(pts) < 2 or any(q is None for q in pts):
            return None
        return {"id": str(rt.get("id") or ""), "label": str(rt.get("label") or ""), "of": rt.get("of") or "",
                **({"actor": str(rt["actor"])} if rt.get("actor") else {}), "by": rt.get("by"), "basis": rt.get("basis"), "arrow": bool(rt.get("arrow", True)), "time": str(rt.get("time") or ""),
                "points": [[round(x, 4), round(y, 4)] for x, y in pts], "resolved": how,
                "source": str(rt.get("source") or ""), "note": str(rt.get("note") or "").strip(), "cite": self.cite(rt.get("ref"), where)}

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

    @staticmethod
    def course_deg(s):
        """A course as a Japanese log writes it, converted to N 65° E (or N, S, E, W) -> degrees true, or None."""
        m = COURSE.fullmatch(str(s or "").strip())
        if not m:
            return None
        if m.group(4):
            return {"N": 0, "E": 90, "S": 180, "W": 270}[m.group(4)]
        a = int(m.group(2))
        return {("N", "E"): a, ("S", "E"): 180 - a, ("S", "W"): 180 + a, ("N", "W"): 360 - a}[(m.group(1), m.group(3))] % 360

    def reckon(self, p, rows, start, end):
        """A ship's log.yml -> (her path reckoned between her fixes, as a route of basis `reckoned`, or None; her log's
        lines inside the window as entries, each placed where the reckoning puts her then). From each fix
        on her track she runs on the last course and speed logged (the speeds by word from ship.yml `speeds`) to the
        next line or fix; at a fix the reckoning starts again from it, and the distance it was off is said in the note.
        Helm orders between courses aren't modelled. Points inside the window only."""
        d = records.RECORDS / "ships" / p["track"]
        path = d / "log.yml"
        if "/" in p["track"] or not path.exists():
            return None, []
        y = records.load_yaml(d / "ship.yml") or {}
        # a speed word whose knots are null (towed, say) is known to be unknown: from it she has no place until a fix
        speeds = {k: (v or {}).get("kts") for k, v in (y.get("speeds") or {}).items()}
        items, first = [], None
        for i, e in enumerate(records.load_yaml(path) or [], 1):
            w = f"{rel(path)} #{i} ({e.get('time') or 'untimed'})"
            for k in set(e) - LOG:
                self.bad(w, f"unknown field {k!r} (known: {', '.join(sorted(LOG))})")
            if e.get("event") and e["event"] not in LOG_EVENT:
                self.bad(w, f"event {e['event']!r} is not one of {', '.join(sorted(LOG_EVENT))}")
            if e.get("speed") and e["speed"] not in speeds:
                self.bad(w, f"speed {e['speed']!r} has no knots in ship.yml `speeds`")
            if e.get("course") and self.course_deg(e["course"]) is None:
                self.bad(w, f"course {e['course']!r} is not written as N 65° E, or N, S, E, W")
            cite = self.cite(e.get("source"), w, e.get("page", ""))
            first = first or cite
            e = {**e, "cite": cite}
            hhmm = str(e.get("time_fix") or e.get("time") or "")
            if not hhmm or "?" in hhmm:
                if items:   # an untimed line goes with the line before it, in the record's order
                    items[-1][2].setdefault("then", []).append(e)
                continue   # untimed, or read with doubt and not corrected: no place in the reckoning
            dd = e["date"].isoformat() if isinstance(e.get("date"), date) else str(e.get("date", ""))
            _, t, _ = self.when(f"{dd} {hhmm} {e.get('zone', 'I')}", "I", w)
            if t:
                items.append((t, 1, e))
        fixes = sorted((r for r in rows if r["on_track"] == "yes"), key=lambda r: r["utc"])
        items.sort(key=lambda x: (x[0], x[1]))
        if not items:
            return None, []
        anchor = [r for r in fixes if r["utc"] <= items[0][0]][-1:]
        if not anchor:
            return None, []
        timeline = sorted([(r["utc"], 0, r) for r in fixes if anchor[0]["utc"] <= r["utc"] <= items[-1][0]] + items, key=lambda x: (x[0], x[1]))
        lat, lon, t0, crs, kts = anchor[0]["lat"], anchor[0]["lon"], anchor[0]["utc"], None, None
        pts, off, entries, timed = [], [], [], []
        lost = False   # after a silence of more than 12 hours her position is unknown until her next fix
        for t, kind, x in timeline:
            if t - t0 > timedelta(hours=12):
                lost, crs, kts = True, None, None
            # under way with no course or speed logged yet: she didn't stay at the fix, and where she went isn't known
            if t > t0 and not lost and (kts is None or (kts and crs is None)):
                lost = True
            if crs is not None and kts and not lost:
                dist = kts * (t - t0).total_seconds() / 3600
                lat += dist * math.cos(math.radians(crs)) / 60
                lon += dist * math.sin(math.radians(crs)) / 60 / math.cos(math.radians(lat))
            t0 = t
            if kind == 0:
                if x is not anchor[0] and not lost:
                    nm = 60 * math.hypot(x["lat"] - lat, (x["lon"] - lon) * math.cos(math.radians(lat)))
                    off.append(f"{nm:.0f} nm off her {x['time_fix'] or x['time']} {x['zone']} fix")
                lat, lon, lost = x["lat"], x["lon"], False
            else:
                if x.get("speed") and speeds.get(x["speed"]) is None:
                    lost = True   # towed, or another speed with no figure: where she went isn't known
                if not lost:
                    crs = self.course_deg(x.get("course")) if x.get("course") else crs
                    kts = speeds.get(x["speed"]) if x.get("speed") else kts
                if start <= t <= end:   # an unplaced line still goes in the chronology, with no place on the map
                    entries.append(self.log_entry(p, x, t, None if lost else lat, None if lost else lon))
            if start <= t <= end and not lost:
                pts.append([round(lon, 4), round(lat, 4)])
                timed.append((t, lat, lon))
        if len(pts) < 2:
            return None, entries
        sp = ", ".join(f"{k} {v.get('kts')} kt ({v.get('basis')})" for k, v in (y.get("speeds") or {}).items() if v.get("kts"))
        return {"id": f"{p['id']}-reckoned", "label": f"{p['name']}: her path reckoned from her log", "of": p.get("of", ""),
                "actor": p["id"], "by": "sea", "basis": "reckoned", "arrow": False, "points": pts, "time": "",
                "resolved": "reckoned from her log's courses and speeds, run on from each fix she wrote; ours",
                "note": f"Speeds: {sp}. Helm orders between courses are not modelled" + (f"; the reckoning was {'; '.join(off)}" if off else ""),
                "source": "her log (log.yml)", "ref": first["ref"] if first else "", "cite": first or {}, "opposed": p.get("opposed", False),
                "timed": timed}, entries

    def log_entry(self, p, x, t, lat, lon):
        """A line of a ship's log -> an engagement entry, placed where her reckoning puts her then (ours)."""
        kind = LOG_KIND.get(x.get("event", ""), "log")
        title = (f"Depth-charge attack, {x['depth_m']} m ({x['charges']} charges)" if kind == "depth_charge"
                 else re.split(r"(?<!No)\. |; ", str(x.get("translation", "")))[0].strip()[:70])
        then = x.get("then") or []
        words = " ".join([str(x.get("translation", "")).strip()] + [f"Then, untimed: {str(y.get('translation', '')).strip()}" for y in then])
        orig = " ".join([str(x.get("original", ""))] + [str(y.get("original", "")) for y in then])
        hhmm = x.get("time_fix") or x.get("time")
        return {"origin": "log", "of": p.get("of", ""), "actor": p["id"], "kind": kind, "title": title, "words": words,
                "original": orig, "lang": "ja", "translation": words,
                "local": f"{x['date'].isoformat() if isinstance(x['date'], date) else x['date']} {hhmm} {x.get('zone', 'I')}",
                "utc": iso(t), "key": iso(t), **({"lat": round(lat, 4), "lon": round(lon, 4), "placed": "reckoned"} if lat is not None else {}),
                "basis": "reported", "cite": x["cite"],
                "note": " ".join(s for s in ["Placed where her reckoning puts her then (ours; her speeds assumed)." if lat is not None
                                             else "Not placed: her log gives no course and speed to reckon from here (towed, or after a silence) until her next fix.",
                                             f"The time corrected from {x['time']}: {x['fix_note']}" if x.get("time_fix") else "",
                                             str(x.get("note", "")).strip()] + [str(y.get("note", "")).strip() for y in then] if s)}

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
            # a row that counts charges is the counter-attack, whatever the depth it also logs (BANG's 80 of 19 September
            # are typed on her depth order's row)
            counted = bool(r["charges"]) and r["event"] in ("depth", "passing")
            if start <= t <= end and (r["event"] in ("charges", "passing") or deep):
                title = {"charges": "Depth charges", "passing": f"Passing {r['depth_ft']} ft", "depth": f"Ordered {r['depth_ft']} ft"}[r["event"]]
                if counted and r["event"] == "depth":
                    title = f"Depth charges, at {r['depth_ft']} ft"
                out.append({"origin": "depths", "of": p.get("of", ""), "actor": p["id"],
                            "kind": "depth_charge" if r["event"] == "charges" or counted else "status",
                            "title": title + (f" ({r['charges']})" if r["charges"] else ""), "words": r["quote"],
                            "local": f"{r['date']} {r['time']} {r['zone']}", "utc": iso(t), "key": iso(t),
                            "cite": self.cite(r["page"], f"{p['track']} depths {r['date']} {r['time']}")})
        return out

    def dive_states(self, p, start, end):
        """A boat's depth log as states, where transcribed: surfaced or submerged (with the depth when the log gives one),
        each from the logged time until the next, the window opening on the last state before it."""
        path = patrol_dir(p["track"]) / "depths.csv"
        out = []
        for r in csv.DictReader(open(path, encoding="utf-8")) if path.exists() else []:
            if not r["time"] or r["event"] not in ("dive", "surface", "radar_depth", "periscope", "depth", "passing"):
                continue
            t = datetime.strptime(f"{r['date']} {r['time']}", "%Y-%m-%d %H%M") - timedelta(hours=ZONES[r["zone"]])
            depth = {"depth": f"{r['depth_ft']} ft", "passing": f"passing {r['depth_ft']} ft"}.get(r["event"]) or {"radar_depth": "radar depth", "periscope": "periscope depth"}.get(r["event"], "")
            state = {"utc": iso(t), "state": "surfaced" if r["event"] == "surface" else "submerged", "depth": depth,
                     "charges": r["charges"], "proximity": r["proximity"], "words": r["quote"], "local": f"{r['date']} {r['time']} {r['zone']}",
                     "cite": self.cite(r["page"], f"{p['track']} depths {r['date']} {r['time']}")}
            if t <= start:
                out = [state]
            elif t <= end:
                out.append(state)
        return out

    def water(self, p, start, end):
        """The water a boat dived in, for the depth figure: the seafloor under her track inside the window (seafloor.csv,
        NOAA ETOPO1 at her positions, straight between fixes, so as placed as the track) and her bathythermograph
        readings of the window's days and the day either side (layers.csv, as typed)."""
        d = patrol_dir(p["track"])
        floor = []
        if (d / "seafloor.csv").exists():
            for r in csv.DictReader(open(d / "seafloor.csv", encoding="utf-8")):
                if r["seafloor_m"] and start - timedelta(hours=1) <= parse_iso(r["utc"]) <= end + timedelta(hours=1):
                    floor.append({"utc": r["utc"], "m": -float(r["seafloor_m"])})
        days = {(start + timedelta(days=k)).date().isoformat() for k in range(-1, (end - start).days + 2)}
        layers = []
        if (d / "layers.csv").exists():
            for r in csv.DictReader(open(d / "layers.csv", encoding="utf-8")):
                if (r.get("date_fix") or r["date"]) in days:
                    layers.append({"date": r.get("date_fix") or r["date"], "time": r["time_gct"], "iso_ft": r["iso_ft"], "iso_deg": r["iso_deg"],
                                   "grad_ft": r["grad_ft"], "grad_deg": r["grad_deg"], "note": r.get("note", ""),
                                   "cite": self.cite(r["page"], f"{p['track']} layers {r['date']}")})
        return {"seafloor": floor, "layers": layers}

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
    """A convoy for its subject page and the ledger: its record, the engagements that met it, and where the boats saw it."""
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


def plain_lede(e):
    """The story's first paragraph in plain words: a [[kind:name|label]] link is its label (or its name), a Markdown link
    its text; for the index page, where the lede stands without the page's links."""
    top = next((s for s in e.get("sections") or [] if not s["heading"]), None)
    if not top or not top["paras"]:
        return ""
    text = top["paras"][0]["text"]
    text = re.sub(r"\[\[(?:cite:[^\]|]*)(?:\|([^\]]*))?\]\]", lambda m: m.group(1) or "", text)   # a bare citation goes
    text = re.sub(r"\[\[[a-z]+:([^\]|]*)(?:\|([^\]]*))?\]\]", lambda m: m.group(2) or m.group(1), text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


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
                     # each subject with a page of its own (subject.html?s=<id>): a boat at its patrol, a unit, a convoy
                     "subjects": [{"id": p["track"].split("/")[0] if p.get("track") else p.get("unit") or p["convoy"], "name": p.get("name", p["id"]),
                                   **({"period": p["track"].split("/")[1]} if p.get("track") and "/" in p["track"] else {})}
                                  for p in e["participants"] if p.get("track") or p.get("unit") or p.get("convoy")],
                     "boats": [p["name"] for p in e["participants"] if p.get("kind") == "submarine"],
                     "convoys": list(e["convoys"]), "box": e["box"],
                     # for the index page: the lede in plain words, and what the engagement has
                     "lede": plain_lede(e), "entries": len(e["events"]), "claims": len(e["claims"]),
                     "languages": len({x.get("lang") or "en" for x in e["events"]}),
                     # entries from the other side's own records (a nationality the subjects faced, in a record of its
                     # own: not our record of them, not a later history): what "read from both sides" has to rest on
                     "other_side": sum(1 for x in e["events"] if x.get("opposed") and x.get("source_kind") == "record"
                                       and x.get("source_of") == x.get("of")),
                     "fronts": len(e.get("fronts") or []), "steps": len(e.get("steps") or []), "sheets": sum(len(v) for v in (e.get("sheets") or {}).values()),
                     "outcome": any(s["heading"].lower() == "outcome" for s in e.get("sections") or [])} for e in engs), key=lambda x: x["from"])
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
