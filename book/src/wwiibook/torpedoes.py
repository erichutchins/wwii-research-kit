"""Each torpedo an attack fired, as a small silhouette: grouped by attack into the forward tubes and the after tubes,
red where the attack sheet records a hit, outlined where it records a miss or no result. The form of a torpedo ledger
for a reader who wants the shape of an attack, not its columns (`components/torpedo-ledger.typ` is the table).

  salvos(rows, attacks=None) -> list of attacks, in firing order, each with its forward, after and unplaced torpedoes
  salvo_svg(salvos, width_in=None) -> svg
  prepare(req, build) -> the asset: the SVG in the book's build/ folder, with the attacks and their citations

`rows` are a boat's `attacks.csv` (records/boats/<boat>/patrol-N/attacks.csv): one row a torpedo, in the order the
sheet types them. Tubes 1-6 are forward and 7-10 aft (the Gato and Balao classes' ten tubes; `FORWARD` and `AFTER`); a
row with no tube is set apart as "tube not recorded". `hit` as typed: "Hit" is a hit; "Miss", a blank or anything
else is drawn outlined, the sheet recording no hit for it. Nothing is inferred: a torpedo the Japanese record shows
hitting, which the sheet does not, stays outlined. Red is the book's colour for hits only.

Some sheets type the result once for the salvo ("2 Hits", `hits` in the patrol's attack_sheets.yml) and not by tube.
Then no torpedo is coloured (which tubes hit is not recorded): the salvo's count is written beside it, with a red dot
a hit.
"""
import csv
import re
from html import escape
from pathlib import Path

import yaml

from . import halo, paths

INK, MUTED, RULE, PAPER = "#000000", "#5d675b", "#c4cbbf", "#fbfaf6"
HIT = "#c8323c"
DISPLAY = "IBM Plex Sans, IBM Plex Sans Condensed, Arial Narrow, sans-serif"
TYPED = "Courier Prime, Courier New, Courier, monospace"
FORWARD = range(1, 7)
AFTER = range(7, 11)

LENGTH, BODY, PITCH = 30.0, 4.0, 7.0      # a torpedo's drawn length and diameter, and the step between two, in points
LABEL_W = 86.0                            # the attack's label column (the whole fits a 194 pt column)
GROUP_W = LENGTH + 16.0                   # a group: the tube numbers and the torpedoes
GAP = 14.0                                # between the after group and the forward group (the boat between them)
ROW_GAP = 9.0


def state(hit: str) -> str:
    """'hit' where the sheet records a hit, else 'miss' where it records a miss, else 'none' (nothing recorded)."""
    h = (hit or "").strip().lower()
    if h.startswith("hit"):
        return "hit"
    if h.startswith("miss"):
        return "miss"
    return "none"


def sheet_hits(sheets: list[dict] | None) -> dict[str, int]:
    """The hits each attack's sheets count for the salvo ("2 Hits"), by attack, where they type a count."""
    out: dict[str, int] = {}
    for sh in sheets or []:
        m = re.match(r"\s*(\d+)\s*hit", str(sh.get("hits") or ""), re.I)
        if m:
            out[sh["attack"]] = out.get(sh["attack"], 0) + int(m.group(1))
    return out


def salvos(rows: list[dict], attacks: list[str] | None = None, sheets: list[dict] | None = None) -> list[dict]:
    """The rows grouped by attack, in the order the sheets give them; `attacks` keeps only those named. `sheets`, the
    patrol's attack_sheets.yml, gives the salvo's count of hits where a sheet types one and no torpedo's is typed."""
    counted = sheet_hits(sheets)
    out: dict[str, dict] = {}
    for r in rows:
        name = r.get("attack", "")
        if attacks is not None and name not in attacks:
            continue
        a = out.setdefault(name, {"attack": name, "date": r.get("date", ""), "times": [], "zone": r.get("zone", ""),
                                  "forward": [], "after": [], "unplaced": [], "pages": [], "salvo_hits": 0})
        t = r.get("time", "")
        if t and t not in a["times"]:
            a["times"].append(t)
        if r.get("page") and r["page"] not in a["pages"]:
            a["pages"].append(r["page"])
        tube = (r.get("tube") or "").strip()
        n = int(tube) if tube.isdigit() else None
        torpedo = {"tube": tube, "state": state(r.get("hit", "")), "hit": r.get("hit", ""), "mark": r.get("torpedo", "")}
        group = "forward" if n in FORWARD else "after" if n in AFTER else "unplaced"
        a[group].append(torpedo)
    for a in out.values():
        if not any(t["state"] == "hit" for g in ("forward", "after", "unplaced") for t in a[g]):
            a["salvo_hits"] = counted.get(a["attack"], 0)
    if attacks is not None:
        missing = [x for x in attacks if x not in out]
        if missing:
            raise ValueError(f"no torpedo rows for {', '.join(missing)}")
        return [out[x] for x in attacks]
    return list(out.values())


def _day(d: str) -> str:
    months = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
    try:
        y, m, dd = d.split("-")
        return f"{int(dd)} {months[int(m) - 1]} {y}"
    except ValueError:
        return d


def _text(x, y, s, size=6.4, fill=INK, anchor="start", weight="normal", italic=False, family=DISPLAY):
    style = ' font-style="italic"' if italic else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{family}" font-size="{size}" font-weight="{weight}"{style} '
            f'fill="{fill}" text-anchor="{anchor}">{escape(s)}</text>')


def torpedo(x: float, y: float, st: str, heading: int = 1) -> str:
    """One torpedo, its nose at x (pointing right with heading 1, left with -1), centred on y: a rounded nose, the
    body, the tapering tail, the fins and the propeller. Red for a hit; outlined in ink otherwise."""
    d, r = heading, BODY / 2
    tail = x - d * LENGTH
    nose = x - d * r * 1.6
    taper = tail + d * LENGTH * 0.16
    fill = HIT if st == "hit" else PAPER
    stroke = HIT if st == "hit" else INK
    body = (f"M{nose:.2f},{y - r:.2f} Q{x:.2f},{y - r:.2f} {x:.2f},{y:.2f} Q{x:.2f},{y + r:.2f} {nose:.2f},{y + r:.2f} "
            f"L{taper:.2f},{y + r:.2f} L{tail + d * 1.2:.2f},{y + r * 0.45:.2f} L{tail + d * 1.2:.2f},{y - r * 0.45:.2f} "
            f"L{taper:.2f},{y - r:.2f} Z")
    fins = (f"M{tail + d * 3.2:.2f},{y - r * 1.25:.2f} L{tail + d * 3.2:.2f},{y + r * 1.25:.2f} "
            f"M{tail:.2f},{y - r * 0.8:.2f} L{tail:.2f},{y + r * 0.8:.2f}")
    return (f'<g class="torpedo {st}"><path d="{body}" fill="{fill}" stroke="{stroke}" stroke-width="0.6" '
            f'stroke-linejoin="round"/><path d="{fins}" stroke="{stroke}" stroke-width="0.7" fill="none"/></g>')


def _group(x: float, y: float, items: list[dict], heading: int) -> list[str]:
    """A column of torpedoes in firing order; the nose at x; each tube's number beside its nose."""
    out = []
    for i, t in enumerate(items):
        cy = y + i * PITCH + PITCH / 2
        out.append(torpedo(x, cy, t["state"], heading))
        out.append(_text(x + heading * 3.0, cy + 2.0, t["tube"] or "?", 5.4, MUTED, "start" if heading > 0 else "end",
                         family=TYPED))
    return out


def salvo_svg(attacks: list[dict], width_in: float | None = None) -> str:
    unplaced = any(a["unplaced"] for a in attacks)
    w = LABEL_W + GROUP_W + GAP + GROUP_W + (GAP + GROUP_W if unplaced else 0)
    if width_in:
        w = max(w, width_in * 72)
    xa = LABEL_W + 12.0                            # the after group's noses, pointing aft (left), numbers before them
    xf = LABEL_W + GROUP_W + GAP + LENGTH          # the forward group's noses, pointing forward (right)
    xu = xf + GAP + LENGTH + 14.0
    body = [_text(xa + LENGTH / 2, 8, "after tubes", 6.2, MUTED, "middle", italic=True),
            _text(xf - LENGTH / 2, 8, "forward tubes", 6.2, MUTED, "middle", italic=True)]
    if unplaced:
        body.append(_text(xu - LENGTH / 2, 8, "tube not recorded", 6.2, MUTED, "middle", italic=True))
    y = 14.0
    for a in attacks:
        n = max(len(a["forward"]), len(a["after"]), len(a["unplaced"]), 1)
        h = n * PITCH
        body.append(f'<line class="row" x1="0" y1="{y - 3:.1f}" x2="{w:.1f}" y2="{y - 3:.1f}" stroke="{RULE}" '
                    'stroke-width="0.4"/>')
        body.append(_text(0, y + 7, a["attack"], 7.2, INK, weight="bold"))
        when = "–".join(a["times"]) + (f" {a['zone']}" if a["zone"] else "")
        body.append(_text(0, y + 15, f"{when} · {_day(a['date'])}", 6.0, MUTED, family=TYPED))
        fired = len(a["forward"]) + len(a["after"]) + len(a["unplaced"])
        hits = sum(t["state"] == "hit" for g in ("forward", "after", "unplaced") for t in a[g])
        if a["salvo_hits"]:
            body.append(_text(0, y + 23, f"{fired} fired; the sheet counts", 6.0, MUTED, italic=True))
            body.append(_text(0, y + 31, f"{a['salvo_hits']} hit{'s' if a['salvo_hits'] != 1 else ''}, not by tube",
                              6.0, MUTED, italic=True))
            for i in range(a["salvo_hits"]):
                body.append(f'<circle class="salvo-hit" cx="{68 + i * 5:.1f}" cy="{y + 29:.1f}" r="1.8" fill="{HIT}"/>')
            h = max(h, 34.0)
        else:
            body.append(_text(0, y + 23, f"{fired} fired; {hits} recorded as hit{'s' if hits != 1 else ''}", 6.0,
                              MUTED, italic=True))
        body += _group(xa, y, a["after"], -1)
        body += _group(xf, y, a["forward"], 1)
        body += _group(xu, y, a["unplaced"], 1)
        mid = LABEL_W + GROUP_W + GAP / 2 - 2
        body.append(f'<line x1="{mid:.1f}" y1="{y:.1f}" x2="{mid:.1f}" y2="{y + h:.1f}" stroke="{RULE}" '
                    'stroke-width="0.6"/>')
        y += max(h, 26.0) + ROW_GAP
    # the key
    y += 2
    body.append(torpedo(LENGTH, y + 3, "hit"))
    body.append(_text(LENGTH + 6, y + 5, "a hit, as the attack sheet records it", 6.2, INK))
    y += PITCH + 3
    body.append(torpedo(LENGTH, y + 3, "miss"))
    body.append(_text(LENGTH + 6, y + 5, "a miss, or no result recorded", 6.2, INK))
    if any(a["salvo_hits"] for a in attacks):
        y += PITCH + 3
        body.append(f'<circle cx="{LENGTH - 2:.1f}" cy="{y + 3:.1f}" r="1.8" fill="{HIT}"/>')
        body.append(_text(LENGTH + 6, y + 5, "a hit the sheet counts for the salvo, not by tube", 6.2, INK))
    h = y + 9
    return halo.layer(f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.1f}pt" height="{h:.1f}pt" '
                      f'viewBox="0 0 {w:.1f} {h:.1f}">{"".join(body)}</svg>')


def prepare(req: dict, build: Path) -> dict:
    src = paths.records() / req["path"]
    with src.open(newline="") as f:
        rows = list(csv.DictReader(f))
    sheet_file = src.parent / "attack_sheets.yml"
    sheets = yaml.safe_load(sheet_file.read_text()) if sheet_file.exists() else None
    groups = salvos(rows, req.get("attacks"), sheets)
    svg = salvo_svg(groups, req.get("width"))
    from .build import _slug
    name = f"{_slug(req['key'])}.svg"
    (build / name).write_text(svg)
    w = float(svg.split('width="', 1)[1].split("pt", 1)[0]) / 72
    cites = list(dict.fromkeys(p for a in groups for p in a["pages"]))
    return {"kind": "torpedoes", "path": f"build/{name}", "source": req["path"], "width": round(w, 3),
            "attacks": groups, "cites": cites,
            "counts": {"fired": sum(len(a[g]) for a in groups for g in ("forward", "after", "unplaced")),
                       "hits": sum(t["state"] == "hit" for a in groups for g in ("forward", "after", "unplaced")
                                   for t in a[g])}}
