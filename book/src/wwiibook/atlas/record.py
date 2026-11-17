"""A unit's own record on an atlas extent: its dated positions and the actions it reports (its engagements with
aircraft, for an anti-aircraft battery), as the kit's records/army/army.json resolves them, each with how precisely
it is placed. Unit names only: the people are the family layer's.

An extent asks for them by unit and window (extent.yml `stations:`). Consecutive positions at one place are one mark,
with the span of its dates.
"""
import json
import math
from functools import cache

from .. import paths
from .extent import Extent

COLOURS = ["#a3241b", "#1d5e86", "#6b3d8f"]     # a unit's colour, in the order the extent names them
MONTHS = ["", "Jan", "Feb", "Mar", "Apr", "May", "June", "July", "Aug", "Sept", "Oct", "Nov", "Dec"]


def day(s: str) -> str:
    return f"{int(s[8:10])} {MONTHS[int(s[5:7])]}"


@cache
def _army() -> dict:
    return {u["unit"]: u for u in json.loads((paths.records() / "army" / "army.json").read_text())["units"]}


def _metres(a: dict, b: dict) -> float:
    return math.hypot((a["lon"] - b["lon"]) * 111320 * math.cos(math.radians(a["lat"])), (a["lat"] - b["lat"]) * 110570)


def stations(unit: dict) -> list[dict]:
    """The unit's placed stations in date order, an entry placed only by a loose offset from a town folded into the
    next entry when that one gives a grid reference for the same place and offset within 30 days: the offset was a
    description of the same position, and the earlier date is kept as `assumed_from` (that it hadn't moved is
    assumed, as the kit's notes on such rows say)."""
    rows = sorted((x for x in unit["stations"] if x.get("lat") is not None), key=lambda x: x["date"])
    out: list[dict] = []
    held = None
    for k, st in enumerate(rows):
        nxt = rows[k + 1] if k + 1 < len(rows) else None
        if (st.get("placed") == "town" and st.get("offset") and nxt and str(nxt.get("placed", "")).startswith("grid")
                and nxt.get("place") == st.get("place") and nxt.get("offset") == st.get("offset")
                and (_days(st["date"], nxt["date"]) <= 30)):
            held = held or st["date"]
            continue
        out.append({**st, "assumed_from": held} if held else st)
        held = None
    return out


def _days(a: str, b: str) -> int:
    from datetime import date
    return (date.fromisoformat(b[:10]) - date.fromisoformat(a[:10])).days


def marks(ex: Extent) -> list[dict]:
    """Positions ({"kind": "station"}) and actions ({"kind": "action"}) inside the extent for each unit it names,
    each with the unit's colour and symbol. The one marked `current` takes the unit's symbol: where it was on the
    extent's date, if that is on the map, else its longest stay on the map."""
    w, s, e, n = ex.bbox_lonlat
    out: list[dict] = []
    for i, want in enumerate(ex.stations):
        colour = COLOURS[i % len(COLOURS)]
        unit = _army().get(want["unit"])
        if not unit:
            continue
        lo, hi = want.get("from", ""), want.get("to", "9999")
        sym = {"of": "us", **want["symbol"]} if want.get("symbol") else None   # none: its dots only

        def inside(r):
            return r.get("lat") is not None and w <= r["lon"] <= e and s <= r["lat"] <= n and \
                lo <= (r.get("assumed_from") or r["date"]) and r["date"] <= hi
        run: dict | None = None
        mine = []
        rows = stations(unit)
        after = {id(x): (rows[k + 1]["date"] if k + 1 < len(rows) else x["date"]) for k, x in enumerate(rows)}
        on_date = next((x for x in reversed(rows) if (x.get("assumed_from") or x["date"]) <= ex.date), None)
        for st in (x for x in rows if inside(x)):
            # one mark for consecutive positions within 500 m of each other: the same place, kept
            if run and _metres(st, run) < 500:
                run["to"] = st["date"]
                run["pages"].append(st["page"])
                run["until"] = after[id(st)]
                run["rows"].append(id(st))
                continue
            run = {"kind": "station", "unit": unit["unit"], "short": unit["short"], "colour": colour, "symbol": sym,
                   "place": st["place"].split(" (")[0], "from": st["date"], "to": st["date"],
                   "assumed_from": st.get("assumed_from"), "lon": st["lon"], "lat": st["lat"],
                   "placed": st["placed"], "grid": st.get("grid") or "", "offset": st.get("offset") or "",
                   "pages": [st["page"]], "current": False, "until": after[id(st)], "rows": [id(st)],
                   "reach": want.get("reach")}
            mine.append(run)
        # the unit's symbol: where it was on the map's date, if that is on the map; else its longest stay here
        if mine:
            here = [m for m in mine if on_date is not None and id(on_date) in m["rows"]]
            pick = here[0] if here else max(mine, key=lambda m: _days(m["assumed_from"] or m["from"], m["until"]))
            pick["current"] = True
        for m in mine:
            m.pop("rows")
        out += mine
        for a in sorted((x for x in unit.get("actions", []) if inside(x) and x.get("kind") == "air"),
                        key=lambda x: (x["date"], x["time"])):
            out.append({"kind": "action", "unit": unit["unit"], "short": unit["short"], "colour": colour,
                        "date": a["date"], "time": a["time"], "result": a["result"], "placed": a["placed"],
                        "lon": a["lon"], "lat": a["lat"], "pages": [a["page"]], "text": a["text"]})
    return out


def raids(ex: Extent) -> list[dict]:
    """Engagements with aircraft that other units in the records report inside the extent, within the named units'
    windows: the other side, where the records see it."""
    if not ex.stations:
        return []
    w, s, e, n = ex.bbox_lonlat
    lo = min(x.get("from", "") for x in ex.stations)
    hi = max(x.get("to", "9999") for x in ex.stations)
    named = {x["unit"] for x in ex.stations}
    out = []
    for uid, unit in _army().items():
        if uid in named:
            continue
        for a in unit.get("actions", []):
            if a.get("kind") == "air" and a.get("lat") is not None and w <= a["lon"] <= e and s <= a["lat"] <= n \
                    and lo <= a["date"] <= hi:
                out.append({"kind": "raid", "unit": uid, "short": unit["short"], "date": a["date"], "time": a["time"],
                            "result": a["result"], "placed": a["placed"], "lon": a["lon"], "lat": a["lat"],
                            "pages": [a["page"]], "text": a["text"]})
    return sorted(out, key=lambda r: (r["date"], r["time"]))


def _key(text: str) -> str:
    import unicodedata
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return "".join(ch for ch in t if ch.isalnum())


def at_town(ex: Extent, m: dict, places: list[dict], within: float = 2500) -> str | None:
    """The map's own label for the town this position is, if it is one: the record names the place, with no offset,
    and a place of that name (or period name) lies within `within` metres. The town's label then names it once, and
    the position's mark carries only its dates."""
    if m["kind"] != "station" or m.get("offset"):
        return None
    want = _key(m["place"])
    for f in places:
        label = ex.label(f["properties"]["name"])[0]
        if want not in (_key(label), _key(f["properties"]["name"])):
            continue
        lon, lat = f["geometry"]["coordinates"]
        if math.hypot((lon - m["lon"]) * 111320 * math.cos(math.radians(lat)), (lat - m["lat"]) * 110570) <= within:
            return f["properties"]["name"]
    return None


def name(m: dict) -> str:
    """A position's label, as the record gives it: a grid reference as typed, with the town and offset the entry
    also names, so a point 8 km from the town doesn't wear the town's name alone; else the place, and its offset."""
    if m["placed"].startswith("grid") and m.get("grid") and m.get("offset"):
        return f"{m['grid']} ({m['place']}, {m['offset']})"
    return f"{m['place']}, {m['offset']}" if m.get("offset") else m["place"]


def span(m: dict) -> str:
    out = day(m["from"]) if m["from"] == m["to"] else f"{day(m['from'])} – {day(m['to'])}"
    return f"{out}; from {day(m['assumed_from'])}, assumed" if m.get("assumed_from") else out
