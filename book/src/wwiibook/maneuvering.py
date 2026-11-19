"""An attack plotted on a maneuvering board, the Navy's polar plotting sheet, for print.

The board is drawn as the period's sheet was laid out: true bearings round the rim, every degree ticked, ten range
rings, own ship at the centre. On it go the attack data sheet's numbers and what follows from them: each target where
the solution puts it at the moment of firing, its course while the torpedoes ran, and each torpedo on its course
(own course + the gyro angle as typed), as far as its run.

The fire-control solution is not worked out here. It is the kit's own, `Engage.attackSheet` in `site/engage.js`, run
under Node, so the book's plot and the site's engagement page (and its TDC explainer) can't disagree. What it assumes
comes back with it and is printed under the figure.

  board(engagement, attacks, width_in)   -> (svg, notes)

A sheet's numbers are printed as typed (gyro 351, track 61S); everything placed from them is derived and drawn in
pencil; a typed value the derived geometry disagrees with is flagged in the notes, not corrected.
"""
import json
import math
import shutil
import subprocess
from html import escape
from typing import Any

from . import figures, halo, paths

INK, MUTED, PAPER = figures.INK, figures.MUTED, figures.PAPER
BOAT = "#2a6fc9"       # the first US boat's colour (guides/ENGAGEMENTS.md, "Colour"): her torpedoes and what she recorded
HIT = "#c8323c"        # red is reserved for hits: here, the other side's record of a ship hit or sunk
SHEET = "#6f8a78"      # the board's printed ink: a muted green, light enough that the plot reads over it in greyscale
SHEET_LIGHT = "#b9c8bc"
PENCIL = "#2b2f2c"
DISPLAY, TYPED, SERIF = figures.DISPLAY, figures.TYPED, figures.SERIF

NODE = """
const E = require(process.argv[1]);
const rows = JSON.parse(require("fs").readFileSync(0, "utf8"));
const out = rows.map(r => { const A = E.attackSheet(r.rows, r.opts || {});
  return { attack: r.attack, assumed: A.assumed, problems: A.problems, ownSpeed: A.ownSpeed,
    targets: A.targets.map(t => ({ ok: t.ok, course: t.course, speed: t.speed, range: t.range, bearing: t.bearing,
      aob: t.aob, lead: t.lead, track: t.track, side: t.side, at: t.at, p0: t.p0, typedTrack: t.typedTrack })),
    torps: A.torps.map(t => ({ tube: t.tube, s: t.s, course: t.course, knots: t.knots, speedBasis: t.speedBasis,
      from: t.from, v: t.v, run: t.run, runYd: t.runYd, passed: t.passed, gyro: t.row.gyro, track: t.row.track,
      target: t.target })) }; });
process.stdout.write(JSON.stringify(out));
"""


def solve(sheets: list[dict]) -> list[dict]:
    """Each attack's rows through the kit's Engage.attackSheet. `sheets`: [{attack, rows, opts?}]."""
    node = shutil.which("node")
    if not node:
        raise RuntimeError("the maneuvering board needs Node (it runs the kit's site/engage.js)")
    engage = str(paths.KIT / "site" / "engage.js")
    r = subprocess.run([node, "-e", NODE, engage], input=json.dumps(sheets), capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def _signed_track(s: str | None) -> float | None:
    """A typed track angle, starboard positive: '61S' -> 61, '76P' -> -76."""
    s = (s or "").strip().upper()
    if not s or s[-1] not in "SP":
        return None
    try:
        v = float(s[:-1])
    except ValueError:
        return None
    return v if s[-1] == "S" else -v


def _seconds(typed: str) -> int:
    """An attack sheet's time as typed, '0915' or '0915-55', in seconds of the day."""
    m = typed.strip().split("-")
    hhmm = m[0].zfill(4)
    return int(hhmm[:2]) * 3600 + int(hhmm[2:4]) * 60 + (int(m[1]) if len(m) > 1 and m[1].isdigit() else 0)


def derived_track(torpedo_course: float, target_course: float) -> float:
    """Track angle from the torpedo's course and the target's, starboard positive (as Engage.fireControl)."""
    t = (torpedo_course + 180 - target_course) % 360
    return t - 360 if t > 180 else t


def disagreements(solved: list[dict], tolerance: float = 3.0) -> list[str]:
    """Where a sheet's typed track angle and the track that own course + typed gyro give part by more than
    `tolerance` degrees: said, never corrected."""
    out = []
    for a in solved:
        bad = []
        for t in a["torps"]:
            typed = _signed_track(t["track"])
            T = a["targets"][t["target"]]
            if typed is None or t["course"] is None or T["course"] is None:
                continue
            d = derived_track(t["course"], T["course"])
            if abs(d - typed) > tolerance:
                bad.append((t["tube"], t["track"], d))
        if bad:
            gives = ", ".join(f"{abs(d):.0f}{'S' if d >= 0 else 'P'}" for _, _, d in bad)
            typed = ", ".join(tr for _, tr, _ in bad)
            out.append(f"{a['attack']}: the tracks typed ({typed}) are not what own course and the typed gyros give "
                       f"against the target's course ({gives}); drawn from the gyros, the typed tracks printed as typed")
    return out


# ---------------------------------------------------------------- drawing

def _t(x, y, s, size=6.5, fill=INK, family=DISPLAY, anchor="middle", weight="normal", italic=False, halo_=False, rotate=None):
    rot = f' transform="rotate({rotate:.1f} {x:.1f} {y:.1f})"' if rotate is not None else ""
    style = ' font-style="italic"' if italic else ""
    h = f' stroke="{PAPER}" stroke-width="2.2" stroke-linejoin="round" paint-order="stroke"' if halo_ else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{family}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}" font-weight="{weight}"{style}{h}{rot}>{escape(s)}</text>')


def _hull(cx, cy, heading, length, beam, fill, stroke, sw=0.5):
    """A ship in plan, to scale: a pointed bow, a rounded stern, heading in degrees true (up is north)."""
    L, B = length / 2, beam / 2
    d = (f"M 0 {-L:.2f} C {B * 0.9:.2f} {-L * 0.55:.2f} {B:.2f} {-L * 0.2:.2f} {B:.2f} {L * 0.55:.2f} "
         f"Q {B:.2f} {L:.2f} 0 {L:.2f} Q {-B:.2f} {L:.2f} {-B:.2f} {L * 0.55:.2f} "
         f"C {-B:.2f} {-L * 0.2:.2f} {-B * 0.9:.2f} {-L * 0.55:.2f} 0 {-L:.2f} Z")
    return (f'<path d="{d}" transform="translate({cx:.2f} {cy:.2f}) rotate({heading:.1f})" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{sw}"/>')


def _sheet(cx, cy, R, rings, ring_yd, scale_at=45.0) -> list[str]:
    """The printed board: rings, the 10° radials, every degree ticked at the rim, the bearing figures."""
    b = [f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{R:.1f}" fill="none" stroke="{SHEET}" stroke-width="0.8"/>']
    for i in range(1, rings):
        r = R * i / rings
        dash = "" if i % 5 == 0 else ' stroke-dasharray="1.2 1.6"'
        b.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="none" stroke="{SHEET}" '
                 f'stroke-width="{0.5 if i % 5 == 0 else 0.35}"{dash}/>')
    for d in range(0, 360, 10):
        a = math.radians(d)
        x1, y1 = cx + R * 0.1 * math.sin(a), cy - R * 0.1 * math.cos(a)
        x2, y2 = cx + R * math.sin(a), cy - R * math.cos(a)
        b.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{SHEET_LIGHT}" stroke-width="0.35"/>')
    for d in range(360):
        a = math.radians(d)
        k = 0.035 if d % 10 == 0 else 0.022 if d % 5 == 0 else 0.012
        x1, y1 = cx + R * math.sin(a), cy - R * math.cos(a)
        x2, y2 = cx + R * (1 + k) * math.sin(a), cy - R * (1 + k) * math.cos(a)
        b.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{SHEET}" stroke-width="0.3"/>')
    for d in range(0, 360, 10):
        a = math.radians(d)
        x, y = cx + R * 1.085 * math.sin(a), cy - R * 1.085 * math.cos(a) + 2.2
        b.append(_t(x, y, f"{d:03d}", 5.6, SHEET, TYPED))
    # the range scale in yards along one radial (`scale_at`, chosen clear of the plot)
    a = math.radians(scale_at)
    for i in range(2, rings, 2):          # the rim carries the bearings, not a range
        r = R * i / rings
        b.append(_t(cx + r * math.sin(a), cy - r * math.cos(a) + 1.6, f"{i * ring_yd:,}", 4.6, SHEET, TYPED, halo_=True))
    return b


def _bearing_nm(lat0, lon0, lat1, lon1):
    """Bearing (degrees true) and distance (nautical miles) from one position to another: plane sailing, fine at a
    few miles."""
    dn = (lat1 - lat0) * 60
    de = (lon1 - lon0) * 60 * math.cos(math.radians((lat0 + lat1) / 2))
    return math.degrees(math.atan2(de, dn)) % 360, math.hypot(dn, de)


def board(engagement: str, attacks: list[str], width_in: float = 5.5, boat: str | None = None,
          ring_yd: int = 150, rings: int = 10, sizes: dict | None = None) -> tuple[str, dict]:
    """One or more attacks fired close together (a bow and a stern salvo) on one board, own ship at the centre at
    the first firing. `sizes`: {attack: [length, beam]} in feet for each target, where known; else 400 by 55,
    assumed (Engage's default), and said so."""
    d = figures.load(engagement)
    sheets = d["sheets"][boat] if boat else next(iter(d["sheets"].values()))
    sizes = sizes or {}
    req = [{"attack": a, "rows": sheets[a]["torpedoes"],
            "opts": ({"length": sizes[a][0], "beam": sizes[a][1]} if a in sizes else {})} for a in attacks]
    solved = solve(req)

    W = width_in * 72
    R = W * 0.36
    cx, cy = W * 0.5, R * 1.17
    H = cy + R * 1.17 + 14            # room under the rim for the legend, clear of the bearing figures
    yd = R / (rings * ring_yd)            # points a yard
    body = [f'<rect width="{W:.1f}" height="{H:.1f}" fill="{PAPER}"/>']
    # the range scale and own ship's label go on the bearings farthest from every target and torpedo
    used = [T["bearing"] for a in solved for T in a["targets"] if T["ok"]]
    used += [t["course"] for a in solved for t in a["torps"] if t["course"] is not None]
    used += [float(sheets[a]["torpedoes"][0]["own_course"]) for a in attacks]
    def clearance(b):
        return min(abs((b - u + 180) % 360 - 180) for u in used) if used else 180
    clear = sorted(range(0, 360, 5), key=clearance, reverse=True)
    scale_at = clear[0]
    label_at = next((b for b in clear[1:] if abs((b - scale_at + 180) % 360 - 180) > 60), (scale_at + 180) % 360)
    body += _sheet(cx, cy, R, rings, ring_yd, scale_at)

    def P0(x_yd, y_yd):                    # yards east and north of own ship at the first firing -> points
        return cx + x_yd * yd, cy - y_yd * yd

    # the first attack's clock is the board's: a later salvo is placed by its sheet's typed time since then
    # ("0915-55" is 55 seconds after 0915), own ship having run on at her sheet's course and speed meanwhile
    t0 = [_seconds(sheets[a]["torpedoes"][0]["time"]) for a in attacks]
    t0 = [t - t0[0] for t in t0]
    own_course = None
    marks: list[dict] = []
    labels = "ABCDEFG"
    for ai, a in enumerate(solved):
        rows = sheets[a["attack"]]["torpedoes"]
        own_course = own_course if own_course is not None else float(rows[0]["own_course"])
        oc0 = math.radians(float(rows[0]["own_course"]))
        adv = a["ownSpeed"] * 2025.4 / 3600 * t0[ai]
        dx, dy = math.sin(oc0) * adv, math.cos(oc0) * adv

        def P(x_yd, y_yd, dx=dx, dy=dy):   # yards from own ship at this salvo -> points on the board
            return cx + (x_yd + dx) * yd, cy - (y_yd + dy) * yd
        for gi, T in enumerate(a["targets"]):
            if not T["ok"]:
                continue
            letter = labels[len(marks)]
            Lft, Bft = sizes.get(a["attack"], (400, 55))
            x0, y0 = T["p0"]
            run = max((t["run"] or 0) for t in a["torps"] if t["target"] == gi)
            v = T["speed"] * 2025.4 / 3600
            c = math.radians(T["course"])
            x1, y1 = x0 + math.sin(c) * v * (run + 8), y0 + math.cos(c) * v * (run + 8)
            # the bearing at firing (derived): a fine pencil line from own ship
            px, py = P(x0, y0)
            ox0, oy0 = P(0, 0)
            body.append(f'<line x1="{ox0:.1f}" y1="{oy0:.1f}" x2="{px:.1f}" y2="{py:.1f}" stroke="{PENCIL}" '
                        f'stroke-width="0.35" stroke-dasharray="3 1.2 0.6 1.2"/>')
            # the target's course while the torpedoes ran: assumed steady, so dashed
            qx, qy = P(x1, y1)
            body.append(f'<line x1="{px:.1f}" y1="{py:.1f}" x2="{qx:.1f}" y2="{qy:.1f}" stroke="{PENCIL}" '
                        f'stroke-width="0.6" stroke-dasharray="2 1.5"/>')
            body.append(_hull(px, py, T["course"], Lft / 3 * yd, Bft / 3 * yd, "#fbfaf6", PENCIL, 0.6))
            body.append(_hull(qx, qy, T["course"], Lft / 3 * yd, Bft / 3 * yd, "#d9ddd6", PENCIL, 0.4))
            # the letter astern of her at firing, the course and speed ahead of her at the run's end
            ux_, uy_ = math.sin(c), -math.cos(c)
            body.append(_t(px - ux_ * 14, py - uy_ * 14 + 3, letter, 9, PENCIL, DISPLAY, weight="bold", halo_=True))
            body.append(_t(qx + ux_ * 9, qy + uy_ * 9 + 2, f"{T['course']:03.0f}° · {T['speed']:.0f} kn", 5.4, PENCIL,
                           TYPED, anchor="start" if ux_ >= 0 else "end", halo_=True))
            # what BANG recorded: the sheet's hits, and sunk or damaged, ringed in her colour where the run ended
            w = (sheets[a["attack"]].get("words") or [{}])
            w = w[0] if isinstance(w, list) and w else (w if isinstance(w, dict) else {})
            claim = "sunk" if w.get("sunk") else "damaged" if w.get("damaged") else None
            heard = w.get("hits")
            if heard or claim:
                rr = Lft / 3 * yd * 0.75 + 3
                body.append(f'<circle cx="{qx:.1f}" cy="{qy:.1f}" r="{rr:.1f}" fill="none" stroke="{BOAT}" '
                            f'stroke-width="0.9" stroke-dasharray="2.2 1.2"/>')
                words = " · ".join(x for x in (f"{heard.lower()} heard" if heard else None,
                                               f"claimed {claim}" if claim else None) if x)
                below = qy > cy
                body.append(_t(qx, qy + (rr + 7 if below else -rr - 3), f"BANG: {words}", 5.4, INK, DISPLAY,
                               italic=True, halo_=True))
            marks.append({"letter": letter, "attack": a["attack"], "heard": heard, "claim": claim, "bearing": round(T["bearing"], 1),
                          "range": T["range"], "course": T["course"], "speed": T["speed"],
                          "aob": round(T["aob"], 1), "lead": round(T["lead"], 1),
                          "track": round(T["track"], 1), "side": T["side"], "typed_track": "–".join(dict.fromkeys(
                              [tt["track"] for tt in a["torps"] if tt["target"] == gi][::max(1, sum(1 for tt in a["torps"] if tt["target"] == gi) - 1)])),
                          "size_assumed": a["attack"] not in sizes})
        # the torpedoes: own course + gyro as typed, each as far as its run, then a short dotted run on
        for t in a["torps"]:
            if t["course"] is None or t["run"] is None:
                continue
            fx, fy = t["from"]
            vx, vy = t["v"]
            ex, ey = fx + vx * t["run"], fy + vy * t["run"]
            # drawn from the first ring out, so the salvos don't cross over own ship at the centre
            sp = math.hypot(vx, vy)
            fx, fy = fx + vx / sp * ring_yd, fy + vy / sp * ring_yd
            ox, oy = fx + vx * (t["run"] + 6), fy + vy * (t["run"] + 6)
            sx, sy = P(fx, fy)
            exx, eyy = P(ex, ey)
            oxx, oyy = P(ox, oy)
            body.append(f'<line x1="{sx:.1f}" y1="{sy:.1f}" x2="{exx:.1f}" y2="{eyy:.1f}" stroke="{BOAT}" stroke-width="0.7"/>')
            body.append(f'<line x1="{exx:.1f}" y1="{eyy:.1f}" x2="{oxx:.1f}" y2="{oyy:.1f}" stroke="{BOAT}" '
                        f'stroke-width="0.5" stroke-dasharray="0.6 1.4"/>')
        # the salvo's label beside its fan, part way out, along the middle torpedo's course
        ts = [t for t in a["torps"] if t["course"] is not None and t["run"] is not None]
        if ts:
            mid = ts[len(ts) // 2]
            vx, vy = mid["v"]
            n_ = math.hypot(vx, vy)
            ux, uy = vx / n_, vy / n_
            k = 0.42 * mid["runYd"]
            mx, my = P(mid["from"][0] + ux * k, mid["from"][1] + uy * k)
            ang = math.degrees(math.atan2(-uy, ux))      # the line's angle on the page
            if ang > 90 or ang < -90:
                ang += 180
            perp = (-uy, -ux) if ux * uy >= 0 else (uy, ux)
            lx_, ly_ = mx + perp[0] * 9, my + perp[1] * 9
            kinds = sorted({str(t.get("torpedo") or "") for t in sheets[a["attack"]]["torpedoes"]} - {""})
            body.append(_t(lx_, ly_, f"tubes {ts[0]['tube']}–{ts[-1]['tube']}"
                           + (f" · Mark {', '.join(kinds)}" if kinds else ""), 5.6, BOAT, DISPLAY, weight="bold",
                           halo_=True, rotate=ang))
    # own ship at the centre, to scale (a Balao, 312 ft by 27), on the sheet's course, and her way during the salvos
    body.append(_hull(cx, cy, own_course or 0, 312 / 3 * yd, 27 / 3 * yd, BOAT, BOAT, 0.3))
    for a in solved:
        last = max(t["s"] for t in a["torps"]) + t0[-1]
        oc = math.radians(own_course or 0)
        v = a["ownSpeed"] * 2025.4 / 3600
        ax, ay = P0(math.sin(oc) * v * (last + 30), math.cos(oc) * v * (last + 30))
        body.append(f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{ax:.1f}" y2="{ay:.1f}" stroke="{BOAT}" stroke-width="0.5"/>')
    la = math.radians(label_at)
    lx, ly = cx + R * 0.3 * math.sin(la), cy - R * 0.3 * math.cos(la)
    body.append(_t(lx, ly + 2, f"own ship · {own_course or 0:03.0f}° · {solved[0]['ownSpeed']:.0f} kn", 5.6, BOAT, TYPED,
                   anchor="start" if math.sin(la) >= 0 else "end", halo_=True))
    # the other side's record of a ship hit or sunk, in red: where it puts her, from where BANG's sheet puts BANG. Each
    # position is its own record's reckoning; a few miles' gap between two navigators is usual, so a mark off the
    # board sits on the rim at its bearing with its distance, not pulled in
    own = next((e for e in d["events"] if e.get("kind") == "attack" and e.get("title") == attacks[0]
                and e.get("lat") is not None), None)
    japanese: list[dict] = []
    for e in d["events"]:
        if e.get("origin") != "japanese":
            continue
        rec = {"record": e.get("record"), "local": e.get("local"), "ship": e.get("ship") or e.get("actor"),
               "kind": e.get("kind"), "original": e.get("original"), "translation": e.get("translation") or e.get("words"),
               "cite": (e.get("cite") or {}).get("ref"), "href": (e.get("cite") or {}).get("href")}
        if own and e.get("kind") in ("torpedoed", "sank", "hit") and e.get("lat") is not None:
            brg, nm = _bearing_nm(own["lat"], own["lon"], e["lat"], e["lon"])
            rec.update(bearing=round(brg), nm=round(nm, 1))
        japanese.append(rec)
    placed = [j for j in japanese if "bearing" in j]
    for k, j in enumerate(sorted(placed, key=lambda j: j["bearing"])):
        a_ = math.radians(j["bearing"])
        r_yd = j["nm"] * 2025.4
        on = r_yd <= rings * ring_yd
        rr = r_yd * yd if on else R
        x, y = cx + rr * math.sin(a_), cy - rr * math.cos(a_)
        s_ = 3.2
        body.append(f'<path d="M{x - s_:.1f},{y - s_:.1f} L{x + s_:.1f},{y + s_:.1f} M{x - s_:.1f},{y + s_:.1f} '
                    f'L{x + s_:.1f},{y - s_:.1f}" stroke="{HIT}" stroke-width="1.3"/>')
        when = (j["local"] or "").split(" ", 1)[-1] if j.get("local") and " " in j["local"] else "no time"
        what = "torpedoed" if j["kind"] in ("torpedoed", "hit") else "sunk"
        # labelled inside the rim, toward the centre, so a label never runs off the sheet
        inward = math.sin(a_) >= 0
        lx_ = x + (-8 if inward else 8)
        ly_ = y + 2 + k * 8 - (len(placed) - 1) * 4
        anchor = "end" if inward else "start"
        body.append(_t(lx_, ly_, f"{j['ship']} {what}, {when} ({j['record']})", 5.4, HIT, DISPLAY, anchor=anchor,
                       halo_=True))
        if not on:
            body.append(_t(lx_, ly_ + 6.5, f"{j['nm']:.1f} nm on {j['bearing']:03d}°, off the board", 4.8, INK,
                           DISPLAY, anchor=anchor, italic=True, halo_=True))
    # the sheet's legend, in its corner, as the printed board carries its scale
    body.append(_t(8, H - 18, "Maneuvering board", 6.8, SHEET, DISPLAY, anchor="start", weight="bold", italic=True))
    body.append(_t(8, H - 10, f"bearings true · rings {ring_yd} yards · drawn for this research", 5.4, SHEET, DISPLAY,
                   anchor="start", italic=True))
    body.append(_t(W - 8, H - 10, f"ships in plan outline, to scale · 1 in = {72 / yd:.0f} yards", 5.4, SHEET, DISPLAY,
                   anchor="end", italic=True))

    svg = halo.split(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.1f}pt" height="{H:.1f}pt" '
                     f'viewBox="0 0 {W:.1f} {H:.1f}">{"".join(body)}</svg>')
    assumed: list[str] = []
    for a in solved:
        for s in a["assumed"]:
            if s not in assumed:
                assumed.append(s)
    if any(m["size_assumed"] for m in marks):
        assumed.append("each target drawn 400 ft by 55 (not given on the sheet)")
    cites: list[str] = []
    for a in attacks:
        w = sheets[a].get("words") or []
        for x in (w if isinstance(w, list) else [w]):
            for k in ("page", "table_page"):
                if isinstance(x, dict) and x.get(k) and x[k] not in cites:
                    cites.append(x[k])
    torps: list[dict[str, Any]] = [{"attack": a["attack"], "tube": t["tube"], "gyro": t["gyro"], "track": t["track"],
                                    "course": t["course"], "run_yd": round(t["runYd"] or 0),
                                    "derived_track": (lambda dd: f"{abs(dd):.0f}{'S' if dd >= 0 else 'P'}")(
                                        derived_track(t["course"], a["targets"][t["target"]]["course"]))}
                                   for a in solved for t in a["torps"] if t["course"] is not None]
    return svg, {"japanese": japanese, "own_position": own and {"lat": own["lat"], "lon": own["lon"]},
                 "targets": marks, "torpedoes": torps, "assumed": assumed, "disagree": disagreements(solved),
                 "problems": [p for a in solved for p in a["problems"]], "cites": cites, "t0": t0}
