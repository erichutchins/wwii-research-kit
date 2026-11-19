"""A convoy attacked by several boats, for print: its ships as silhouettes at one scale, and a tally setting each
boat's own claims beside JANAC's postwar credit and the Japanese records.

Everything is read from the kit's records: the engagement (records/engagements/<id>/engagement.json: the convoy's
ships, the pairings of each attack with a Japanese record, and JANAC's entries for each loss, as printed), each boat's
attack data sheets (boats/<hull>/patrol-N/attack_sheets.yml: what she claimed, in her own words) and each patrol's
Japanese records (japanese.yml, for the monthly loss lists the engagement does not carry as events).

The silhouettes are the library's (records/silhouettes/silhouettes.json), in feet, drawn as site/engage-views.js
draws them: stern at x = 0, waterline at y = 0, every ship at the same points to the foot. A ship whose `sil` is only a
kind of ship (a category: no plate, no length) is not drawn; she is listed by name under the plates.

A ship's fate is what the Japanese records say: sunk where a primary record (JACAR) has her sunk or lists her in a
month's losses, damaged where one has her torpedoed and not sunk, nothing otherwise. A secondary account
(combinedfleet.com) alone is said in words and never marked red. Nothing here weighs or scores: the counts are the
records' own entries.
"""
import json
import re
from functools import cache
from html import escape
from pathlib import Path

import yaml

from . import paths

INK, MUTED, RULE, RED = "#000000", "#586257", "#c4cbbf", "#c8323c"
BOATS = ("#2a6fc9", "#008f78", "#6a3a9e")     # guides/ENGAGEMENTS.md, "Colour": the boats in participant order
DISPLAY = "IBM Plex Sans, IBM Plex Sans Condensed, Arial Narrow, sans-serif"
SERIF = "Libertinus Serif, Georgia, serif"
JA = "Shippori Mincho, Noto Serif JP, serif"

RELATION = {   # records/SCHEMA.md, a patrol's claims.yml
    "hit": "the attack caused that record",
    "miss": "the same moment, no damage",
    "probable": "time and place point to this attack, but another boat is credited or was attacking too",
    "possible": "the times fit, but more than one attack could explain the record",
    "no_loss": "a claimed sinking with no matching entry in the Japanese loss list",
}
SUNK_EVENTS = {"sank"}
DAMAGE_EVENTS = {"torpedoed", "damaged", "hit"}
KANJI = dict(zip("〇一二三四五六七八九", "0123456789"))
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
NUMBER = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}


# ---------------------------------------------------------------------------------------------------------- the records

@cache
def _engagement(eid: str) -> dict:
    return json.loads((paths.records() / "engagements" / eid / "engagement.json").read_text())


@cache
def _ships() -> dict:
    return json.loads((paths.records() / "silhouettes" / "silhouettes.json").read_text())["ships"]


@cache
def _yaml(path: str) -> list:
    p = Path(path)
    return (yaml.safe_load(p.read_text()) or []) if p.exists() else []


def _boats(e: dict) -> list[dict]:
    """The US boats, in participant order, each with her colour and her patrol's folder."""
    out = []
    for p in e["participants"]:
        if p.get("of") != "us" or p.get("kind") != "submarine":
            continue
        alias, n = p["track"].split("/")
        out.append({**p, "colour_hex": BOATS[(p.get("colour") or len(out) + 1) - 1],
                    "dir": paths.records() / "boats" / alias / f"patrol-{n}", "patrol": n})
    return out


def _sheets(boat: dict) -> dict:
    return {s["attack"]: s for s in _yaml(str(boat["dir"] / "attack_sheets.yml"))}


def _base(attack: str) -> str:
    """'Attack 2 fired' and 'Attack 2 (narrative)' are Attack 2."""
    return re.sub(r"\s*(\(narrative\)|fired)\s*$", "", attack).strip()


def _names(ship: str | None) -> list[str]:
    return [s.strip() for s in re.split(r";| and ", ship or "") if s.strip()]


def _primary(cite: dict | None) -> bool:
    return bool(cite) and cite.get("kind") == "record" and cite.get("of") == "jp"


def ref_words(ref: str) -> str:
    """A citation as a reader finds it: JACAR C08030607900, p. 47; JANAC 4, p. 76; a National Archives page as it
    stands (rg38-74802868/p12)."""
    m = re.match(r"^jacar:(\S+)\s+p0*(\d+)$", ref)
    if m:
        return f"JACAR {m.group(1)}, p. {m.group(2)}"
    m = re.match(r"^janac:(\d)/p(\d+)$", ref)
    if m:
        return f"JANAC {m.group(1)}, p. {m.group(2)}"
    m = re.match(r"^combinedfleet:(\S+)$", ref)
    if m:
        return f"combinedfleet.com/{m.group(1)}.htm (secondary)"
    return ref


def _japanese_records(e: dict) -> list[dict]:
    """Every Japanese record the engagement draws on, once: its events, its pairings' records, and the loss lists in
    the boats' japanese.yml (which name the convoy's losses by name and tonnage)."""
    seen, out = set(), []

    def add(r: dict):
        k = (r.get("id"), (r.get("cite") or {}).get("ref"), r.get("ship") or "", r.get("event"))
        if k not in seen:
            seen.add(k)
            out.append(r)
    for x in e["events"]:
        if x.get("of") == "jp" and x.get("origin") == "japanese":
            add({**x, "event": x["kind"], "id": x.get("record")})
    for p in e["pairs"]:
        add(p["record"])
    convoys = {str(c.get("convoy") or k).upper() for k, c in e["convoys"].items()}
    for b in _boats(e):
        for r in _yaml(str(b["dir"] / "japanese.yml")):
            if r.get("event") != "loss_list" or str(r.get("convoy", "")).upper() not in convoys:
                continue
            src = str(r["source"])
            ref = f"{src} {r['page']}" if r.get("page") else src
            jacar = src.startswith("jacar:")
            add({**r, "unit": f"{b['alias']}/{b['patrol']}",
                 "cite": {"ref": ref, "kind": "record" if jacar else "secondary", "of": "jp" if jacar else "",
                          "href": f"https://www.jacar.archives.go.jp/das/image/{src.split(':', 1)[1]}" if jacar
                          else None}})
    return out


def fates(engagement: str) -> dict[str, dict]:
    """Each convoy ship's fate as the Japanese records give it: {'mark': 'sunk' | 'damaged' | None, 'words', 'refs'}."""
    e = _engagement(engagement)
    recs = _japanese_records(e)
    out = {}
    for c in e["convoys"].values():
        for s in c["ships"]:
            name = s["ship"]
            sunk = [r for r in recs if r.get("event") in SUNK_EVENTS and name in _names(r.get("ship"))]
            listed = [r for r in recs if r.get("event") == "loss_list" and name in (r.get("translation") or "")]
            hit = [r for r in recs if r.get("event") in DAMAGE_EVENTS and name in _names(r.get("ship"))]
            prim_sunk = [r for r in sunk + listed if _primary(r.get("cite"))]
            prim_hit = [r for r in hit if _primary(r.get("cite"))]
            if prim_sunk:
                first = next((r for r in prim_sunk if r.get("event") == "sank"), None)
                if first:
                    w = _when((first.get("local") or "").replace(" no time", ""), None)["typed"] or first.get("date", "")
                    words = f"sunk {w}" + ("" if re.search(r"\d{4} ", w) else " (no time given)")
                else:
                    words = "sunk, in the month's loss list"
                out[name] = {"mark": "sunk", "words": words, "refs": sorted({r["cite"]["ref"] for r in prim_sunk})}
            elif prim_hit:
                out[name] = {"mark": "damaged", "words": "torpedoed, not recorded as sunk",
                             "refs": sorted({r["cite"]["ref"] for r in prim_hit})}
            elif sunk:
                out[name] = {"mark": None, "words": "sunk in a secondary account only; no Japanese record yet",
                             "refs": sorted({r["cite"]["ref"] for r in sunk})}
            else:
                out[name] = {"mark": None, "words": "", "refs": []}
    return out


def tonnage(s: dict) -> str:
    """Her tonnage where the records give it, and of what kind: a ship's own `tons`, else the convoy table's
    displacement (kanji digits, positional) or the loss list's GRT, as her note quotes them."""
    if s.get("tons") or s.get("tonnage"):
        return f"{s.get('tons') or s.get('tonnage')} tons"
    note = s.get("note") or ""
    m = re.search(r"displacement ([〇一二三四五六七八九]+)", note)
    if m:
        return f"{int(''.join(KANJI[ch] for ch in m.group(1))):,} tons displacement, as written"
    m = re.search(r"(\d{3,6}) GRT", note)
    if m:
        return f"{int(m.group(1)):,} GRT (loss list)"
    return ""


def written(s: dict) -> str:
    """Her name in the record's own characters, where her note quotes them ('written 真鶴')."""
    m = re.search(r"[Ww]ritten ([^\s,;(]+)", s.get("note") or "")
    return m.group(1) if m and re.search(r"[぀-鿿]", m.group(1)) else ""


def basis_words(sil: str, basis: str | None) -> str:
    """What the silhouette is, as engage-views.js's silWords says it, for print."""
    name = _ships()[sil]["name"]
    if basis == "representative":
        return f"a type standing for her, assumed: {name}"
    if basis and basis.startswith("class, assumed"):
        why = basis.split(":", 1)[1].strip() if ":" in basis else ""
        return f"her class, assumed: {name}" + (f" ({why})" if why else "")
    if basis and basis.startswith("own"):     # the manual draws her by name (alone, or with a sister on one plate)
        return f"her own plate: {name}"
    return f"her class: {name}"


# ------------------------------------------------------------------------------------------------------- the silhouettes

def _t(x, y, s, size=7.0, fill=INK, anchor="start", weight="normal", family=DISPLAY, italic=False):
    it = ' font-style="italic"' if italic else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{family}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}" font-weight="{weight}"{it}>{escape(s)}</text>')


def _wrap(s: str, chars: int) -> list[str]:
    out, line = [], ""
    for w in s.split():
        if line and len(line) + len(w) + 1 > chars:
            out.append(line)
            line = w
        else:
            line = (line + " " + w).strip()
    return out + ([line] if line else [])


def _height(d: str) -> float:
    """The silhouette's highest point above the waterline, in feet (the site's own rule, engage-views.js `fit`)."""
    return max([-float(v) for v in re.findall(r",(-?[\d.]+)", d)] + [1.0])


def _mark(kind: str | None, x: float, y: float, r: float = 3.2) -> str:
    if kind == "sunk":
        return (f'<path data-fate="sunk" d="M{x - r:.1f},{y - r:.1f}L{x + r:.1f},{y + r:.1f}M{x - r:.1f},{y + r:.1f}'
                f'L{x + r:.1f},{y - r:.1f}" stroke="{RED}" stroke-width="1.5" stroke-linecap="round" fill="none"/>')
    if kind == "damaged":
        return (f'<circle data-fate="damaged" cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" stroke="{RED}" stroke-width="1.2" '
                f'fill="none"/>')
    return ""


def _order(c: dict) -> list[dict]:
    """By role: escorts, then merchant ships, each in the convoy's own order."""
    rank = {"escort": 0, "merchant": 1}
    return sorted(c["ships"], key=lambda s: rank.get(s.get("role"), 2))


def silhouettes(engagement: str, width_in: float = 6.9) -> tuple[str, dict]:
    """The convoy's ships that have a plate, side views at one scale, labelled; a 100-ft bar and the first boat's own
    silhouette with a plate, for scale; the ships with no plate listed by name under them."""
    e, lib = _engagement(engagement), _ships()
    fate = fates(engagement)
    boats = _boats(e)
    W = width_in * 72
    convoy = next(iter(e["convoys"].values()))
    ships = _order(convoy)
    drawn = [s for s in ships if s.get("sil") in lib]
    plain = [s for s in ships if s.get("sil") not in lib]
    boat = next((b for b in boats if b.get("sil") in lib), None)
    lengths = [float(lib[s["sil"]]["length"]) for s in drawn] + ([float(lib[boat["sil"]]["length"])] if boat else [])
    cols = 3 if W >= 380 else 2
    gap = 14.0
    cw = (W - gap * (cols - 1)) / cols
    k = (cw - 2) / max(lengths + [100.0])          # points to the foot, the same for every plate
    sky = max([_height(lib[s["sil"]]["d"]) for s in drawn] + [30.0]) * k + 4

    body, y = [], 0.0
    cites = {s["cite"]["ref"] for s in ships if s.get("cite")}
    groups = [("escort", "Escorts"), ("merchant", "Merchant ships")]
    groups += [(r, str(r).capitalize()) for r in sorted({str(s.get("role")) for s in drawn} - {"escort", "merchant"})]
    for role, head in groups:
        row = [s for s in drawn if str(s.get("role")) == role]
        if not row:
            continue
        y += 9
        body.append(_t(0, y, head.upper(), 6.4, MUTED, weight="bold"))
        body.append(f'<line x1="0" y1="{y + 3:.1f}" x2="{W:.1f}" y2="{y + 3:.1f}" stroke="{RULE}" stroke-width="0.5"/>')
        y += 6
        for i in range(0, len(row), cols):
            line_h = 0.0
            for j, s in enumerate(row[i:i + cols]):
                x = j * (cw + gap)
                sh = lib[s["sil"]]
                wl = y + sky
                body.append(f'<path data-ship="{escape(s["ship"])}" data-sil="{s["sil"]}" data-length="{sh["length"]}" '
                            f'transform="translate({x:.2f},{wl:.2f}) scale({k:.6f})" d="{sh["d"]}" fill="{INK}"/>')
                body.append(f'<line x1="{x:.1f}" y1="{wl + 0.4:.1f}" x2="{x + cw - 2:.1f}" y2="{wl + 0.4:.1f}" '
                            f'stroke="{RULE}" stroke-width="0.4"/>')
                f = fate.get(s["ship"], {})
                ty = wl + 11
                tx = x
                if f.get("mark"):
                    body.append(_mark(f["mark"], x + 3.4, ty - 2.6))
                    tx = x + 10
                body.append(_t(tx, ty, s["ship"], 7.8, INK, weight="bold"))
                ja = written(s)
                if ja:
                    body.append(_t(tx + len(s["ship"]) * 3.7 + 5, ty, ja, 7.0, INK, family=JA))
                ly = ty + 8.2
                body.append(_t(x, ly, " · ".join(v for v in (str(s.get("role") or ""), tonnage(s)) if v), 6.2, INK))
                for ln in _wrap(basis_words(s["sil"], s.get("sil_basis")) + f", {sh['length']} ft", int(cw / 3.05)):   # 5.8 pt serif italic: about 3 pt a character
                    ly += 7.0
                    body.append(_t(x, ly, ln, 5.8, MUTED, family=SERIF, italic=True))
                if f.get("words"):
                    for ln in _wrap(f"{f['words']} ({'; '.join(ref_words(r) for r in f['refs'])})", int(cw / 2.7)):
                        ly += 7.0
                        body.append(_t(x, ly, ln, 5.8, INK))
                    cites |= set(f["refs"])
                line_h = max(line_h, ly - y)
            y += line_h + 10

    # for scale: the first boat with a plate, and a 100-ft bar, both at the ships' scale
    y += 2
    body.append(f'<line x1="0" y1="{y:.1f}" x2="{W:.1f}" y2="{y:.1f}" stroke="{RULE}" stroke-width="0.5"/>')
    y += 8
    if boat:
        sh = lib[boat["sil"]]
        wl = y + _height(sh["d"]) * k + 2
        body.append(f'<path data-ship="{escape(boat["name"])}" data-sil="{boat["sil"]}" data-length="{sh["length"]}" '
                    f'transform="translate(0,{wl:.2f}) scale({k:.6f})" d="{sh["d"]}" fill="{boat["colour_hex"]}"/>')
        bx = float(sh["length"]) * k + 10
        body.append(_t(bx, wl - 5, boat["name"], 7.6, boat["colour_hex"], weight="bold"))
        body.append(_t(bx, wl + 3, f"{sh['name']}, {sh['length']} ft, for scale", 6.0, MUTED, family=SERIF,
                       italic=True))
        y = wl
    sx = W - 100 * k - 2
    body.append(f'<path data-bar="100" d="M{sx:.2f},{y - 3:.1f}V{y:.1f}H{sx + 100 * k:.2f}V{y - 3:.1f}" '
                f'stroke="{INK}" stroke-width="0.8" fill="none"/>')
    body.append(f'<line x1="{sx + 50 * k:.1f}" y1="{y - 2:.1f}" x2="{sx + 50 * k:.1f}" y2="{y:.1f}" stroke="{INK}" '
                f'stroke-width="0.6"/>')
    body.append(_t(sx + 50 * k, y - 5, "100 ft", 6.2, INK, anchor="middle"))
    body.append(_t(sx - 6, y, "every ship at one scale", 5.8, MUTED, anchor="end", family=SERIF, italic=True))

    # ships with no plate: by name, not drawn
    if plain:
        y += 14
        body.append(_t(0, y, "NOT DRAWN: NO PLATE IN THE LIBRARY FOR THESE SHIPS OR THEIR CLASS", 6.2, MUTED,
                       weight="bold"))
        for s in plain:
            f = fate.get(s["ship"], {})
            cites |= set(f.get("refs", []))
            what = ", ".join(v for v in (str(s.get("role") or ""), tonnage(s), f.get("words", "")) if v)
            if f.get("refs"):
                what += f" ({'; '.join(ref_words(r) for r in f['refs'])})"
            y += 8.4
            if f.get("mark"):
                body.append(_mark(f["mark"], 3.0, y - 2.4, 2.6))
            body.append(_t(10, y, s["ship"], 6.8, INK, weight="bold"))
            ja = written(s)
            if ja:
                body.append(_t(84, y, ja, 6.4, INK, family=JA))
            for n, ln in enumerate(_wrap(what, int((W - 150) / 2.75))):
                if n:
                    y += 7.2
                body.append(_t(146, y, ln, 6.2, INK))
    H = y + 6
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.1f}pt" height="{H:.1f}pt" viewBox="0 0 {W:.1f} '
           f'{H:.1f}">{"".join(body)}</svg>')
    notes = {
        "pt_per_ft": k, "drawn": [s["ship"] for s in drawn], "not_drawn": [s["ship"] for s in plain],
        "scale_boat": boat["name"] if boat else None, "fates": fate,
        "silhouette_sources": sorted({src for s in drawn for src in lib[s["sil"]].get("sources", [])}
                                     | (set(lib[boat["sil"]].get("sources", [])) if boat else set())),
        "cites": sorted(cites),
    }
    return svg, notes


# --------------------------------------------------------------------------------------------------------------- tally

def _abridge(s: str | None, words: int = 28) -> str:
    w = (s or "").split()
    return " ".join(w) if len(w) <= words else " ".join(w[:words]).rstrip(",;:.") + " ..."


def _clean(s) -> str:
    s = "" if s is None else str(s).strip()
    return "" if s.lower().rstrip(".") in ("none", "", "--", "0") else s


def count_claim(words: str | None) -> int:
    """How many ships a sheet's typed claim names: each sentence that opens with a count ('One medium AK', '(2) AK
    similar to ...', '1-AO 7,500'). 'None', '--' and 'Unknown' name none."""
    s = _clean(words)
    if not s or s.lower().startswith("unknown"):
        return 0
    dash = re.findall(r"(?:^|\s)(\d+)-A[A-Z]", s)
    if dash:
        return sum(int(d) for d in dash)
    n = 0
    for sent in re.split(r"(?<=\.)\s+", s):
        sent = re.sub(r"^\*?\s*\((UN|EC|EU)\)\s*", "", sent.strip())
        if re.match(r"^\(\d+\)", sent):
            n += 1
            continue
        n += NUMBER.get(sent.split(" ", 1)[0].lower().rstrip("."), 0)
    return n


def _when(local: str, utc: str | None) -> dict:
    """'1944-11-23 0032 K' as typed, and its GMT."""
    m = re.match(r"^(\d{4})-(\d\d)-(\d\d)(?:\s+(\d{4}(?:-\d\d)?))?(?:\s+([A-Z]))?$", (local or "").strip())
    if m:
        day = f"{int(m.group(3))} {MONTHS[int(m.group(2)) - 1]} {m.group(1)}"
        typed = f"{m.group(4)} {m.group(5) or ''}".strip() + f", {day}" if m.group(4) else \
            f"{day}" + (f" (zone {m.group(5)})" if m.group(5) else "")
    else:
        typed = local
    g = re.match(r"^(\d{4})-(\d\d)-(\d\d)T(\d\d):(\d\d)Z$", utc or "")
    gmt = f"{g.group(4)}{g.group(5)} GMT, {int(g.group(3))} {MONTHS[int(g.group(2)) - 1]}" if g else ""
    return {"typed": typed, "gmt": gmt, "utc": utc}


def tally(engagement: str) -> dict:
    """The table's rows, one per attack on the convoy, and a line per boat of what the records count."""
    e = _engagement(engagement)
    boats = _boats(e)
    byid = {b["id"]: b for b in boats}
    units: dict[tuple, list[str]] = {}   # which patrols' japanese.yml hold a record id (J numbers run within a patrol)
    for b in boats:
        for j in _yaml(str(b["dir"] / "japanese.yml")):
            ref = f"{j['source']} {j['page']}" if j.get("page") else str(j.get("source"))
            units.setdefault((j.get("id"), ref, j.get("event")), []).append(f"{b['name']} patrol {b['patrol']}")

    def file_of(rec: dict, b: dict) -> str:
        """The patrol whose japanese.yml holds the record: the attacking boat's own where it holds it too."""
        found = units.get((rec.get("id"), rec["cite"]["ref"], rec.get("event"))) or []
        own = f"{b['name']} patrol {b['patrol']}"
        return own if own in found else (found[0] if found else "")
    rows: dict[tuple[str, str], dict] = {}
    for x in e["events"]:
        if x.get("of") != "us" or x.get("kind") != "attack" or x.get("actor") not in byid:
            continue
        r = rows.setdefault((x["actor"], _base(x["title"])), {"times": [], "pairs": []})
        r["times"].append({**_when(x.get("local", ""), x.get("utc")),
                           "from": "narrative" if "narrative" in x["title"] else "attack data sheet",
                           "cite": x["cite"]["ref"]})
    for p in e["pairs"]:
        if p["boat"] in byid:
            rows.setdefault((p["boat"], _base(p["attack"])), {"times": [], "pairs": []})["pairs"].append(p)

    out = []
    for (bid, attack), r in rows.items():
        b = byid[bid]
        s = _sheets(b).get(attack, {})
        sunk = _clean(s.get("sunk") or s.get("sunk_or_damaged"))
        damaged = _clean(s.get("damaged") or s.get("damaged_or_probably_sunk"))
        claim = {"sunk": sunk, "damaged": damaged, "hits": _clean(s.get("hits")),
                 "determined_by": _abridge(_clean(s.get("determined_by")), 26),
                 "n_sunk": count_claim(sunk), "n_damaged": count_claim(damaged), "cite": s.get("page") or ""}
        janac, seen = [], set()
        for p in r["pairs"]:
            for j in p.get("janac") or []:
                k = (j["ship"], j["cite"]["ref"])
                if k not in seen:
                    seen.add(k)
                    janac.append({"ship": j["ship"], "date": j.get("date", ""), "type": j.get("type", ""),
                                  "tons": j["tons"], "agent": j["agent"], "probable": bool(j.get("probable")),
                                  "ref": j["cite"]["ref"], "page": ref_words(j["cite"]["ref"]),
                                  "href": j["cite"].get("href"),
                                  "appendix": ref_words((j.get("appendix") or {}).get("ref") or "")})
        records, rseen = [], set()
        for p in r["pairs"]:
            rec = p["record"]
            k = (rec.get("id"), rec["cite"]["ref"], rec.get("event"))
            if k in rseen:
                continue
            rseen.add(k)
            records.append({
                "id": rec.get("id", ""), "unit": file_of(rec, b),
                "event": rec.get("event", ""), "ship": rec.get("ship", ""), "local": rec.get("local", ""),
                "original": rec.get("original") or "", "translation": _abridge(rec.get("translation"), 30),
                "ref": rec["cite"]["ref"], "page": ref_words(rec["cite"]["ref"]), "href": rec["cite"].get("href"),
                "primary": _primary(rec["cite"]), "relation": p["relation"],
                "relation_words": RELATION.get(p["relation"], p["relation"]),
            })
        times = r["times"] or [{**_when("", p["utc"]), "from": "pairing", "cite": ""} for p in r["pairs"][:1]]
        out.append({"boat": bid, "name": b["name"], "colour": b["colour_hex"], "attack": attack, "times": times,
                    "utc": min((t["utc"] or "" for t in times), default=""), "claim": claim, "janac": janac,
                    "records": records})
    out.sort(key=lambda r: (r["utc"] or "", r["name"], r["attack"]))

    lost = [n for n, f in fates(engagement).items() if f["mark"] == "sunk"]
    every_janac = {(j["ship"], j["ref"]): j for row in out for j in row["janac"]}
    boats_out = []
    for b in boats:
        mine = [r for r in out if r["boat"] == b["id"]]
        credited = sorted((j for j in every_janac.values() if j["agent"].upper() == b["name"].upper()),
                          key=lambda j: j["ship"])
        paired: dict[str, set] = {}
        for r in mine:
            for rec in r["records"]:
                if rec["event"] in SUNK_EVENTS and rec["primary"]:
                    for n in _names(rec["ship"]):
                        paired.setdefault(n, set()).add(rec["relation"])
        boats_out.append({
            "boat": b["id"], "name": b["name"], "colour": b["colour_hex"], "attacks": len(mine),
            "claimed_sunk": sum(r["claim"]["n_sunk"] for r in mine),
            "claimed_damaged": sum(r["claim"]["n_damaged"] for r in mine),
            "janac": [{"ship": j["ship"], "tons": j["tons"], "probable": j["probable"], "page": j["page"]}
                      for j in credited],
            "japanese_paired": [{"ship": n, "relations": sorted(v)} for n, v in sorted(paired.items())],
        })
    refs = sorted({r["claim"]["cite"] for r in out if r["claim"]["cite"]}
                  | {t["cite"] for r in out for t in r["times"] if t["cite"]}
                  | {j["ref"] for r in out for j in r["janac"]} | {x["ref"] for r in out for x in r["records"]})
    return {"engagement": engagement, "title": e.get("title", ""), "rows": out, "boats": boats_out, "lost": lost,
            "lost_words": f"The Japanese records list {len(lost)} of the convoy's ships as sunk"
                          + (f": {', '.join(lost)}." if lost else "."),
            "refs": refs, "pages": [ref_words(x) for x in refs]}


def prepare(req: dict, build: Path) -> dict:
    """The build's preparer: the silhouettes' SVG in build/, the tally in the asset itself."""
    svg, notes = silhouettes(req["engagement"], req.get("width") or 6.9)
    slug = re.sub(r"[^a-z0-9]+", "-", req["key"].lower()).strip("-")
    (Path(build) / f"{slug}.svg").write_text(svg)
    return {"kind": "convoyships", "path": f"build/{slug}.svg", **notes, "tally": tally(req["engagement"])}
