"""How a torpedo was aimed, for print: the fire-control triangle of one attack, drawn to scale; the same triangle as
the angle on the bow changes; and the Torpedo Data Computer as a diagram, its dials named as OP 1056 names them.

Nothing is solved here. Every angle, bearing and run is the kit's own, from `site/engage.js` run under Node
(`attackSheet` places the target from the sheet's numbers, `tdcAt` works the shot as the computer's angle solver
would, `fireControl` the plain triangle), so the book, the site's Torpedo fire control page and its TDC page can't
disagree. What engage.js assumes comes back with it and is printed under the figure.

  triangle(engagement, attack, width_in, boat)      -> (svg, notes)   the attack's triangle, north up, to scale
  aob_strip(engagement, attack, width_in, boat, aobs) -> (svg, notes) the same range and speeds at other angles on the bow
  tdc_diagram(width_in)                             -> (svg, notes)   inputs, position keeper, angle solver, tubes
  prepare(req, build)                               -> asset          the book's preparer (kind "firecontrol")

A sheet's numbers are printed as typed (gyro 351, track 61S); everything placed from them is derived and drawn in
pencil or in the boat's blue; the typed values the drawing does not follow are said in the notes.
"""
import hashlib
import json
import math
import re
import shutil
import subprocess
from html import escape
from pathlib import Path

from . import figures, halo, paths

INK, MUTED, PAPER, RULE = figures.INK, figures.MUTED, figures.PAPER, figures.RULE
BLUE = "#2a6fc9"        # BANG's blue, as the site draws her: the boat and her torpedoes (red is kept for hits)
PENCIL = "#2b2f2c"
FAINT = "#9fb6d9"       # the spread's other torpedoes, lighter than the point of aim's
DISPLAY, TYPED, SERIF = figures.DISPLAY, figures.TYPED, figures.SERIF

NODE = """
const E = require(process.argv[1]);
const req = JSON.parse(require("fs").readFileSync(0, "utf8"));
const pick = (A, s) => { const T = A.targets[0], d = E.tdcAt(A, s);
  return { ok: T.ok, course: T.course, speed: T.speed, range: T.range, bearing: T.bearing, aob: T.aob, lead: T.lead,
    track: T.track, side: T.side, p0: T.p0, torpedoCourse: d.torpedoCourse, gyro: d.gyro, run: d.fwd ? d.fwd.run : null,
    distanceToTrack: d.distanceToTrack, relBearing: d.relBearing, torpedoSpeed: d.torpedoSpeed, solved: d.solved }; };
const A = E.attackSheet(req.rows);
const out = { assumed: A.assumed, problems: A.problems, ownSpeed: A.ownSpeed, aim: pick(A, 0),
  torps: A.torps.map(t => ({ tube: t.tube, s: t.s, course: t.course, knots: t.knots, speedBasis: t.speedBasis,
    gyro: t.row.gyro, track: t.row.track, fc: E.fireControl({ ownCourse: +t.row.own_course, gyro: +t.row.gyro,
      targetCourse: +t.row.target_course, targetSpeed: +t.row.target_speed, torpedoSpeed: t.knots }) })),
  sweep: [] };
// The same sheet fired at other angles on the bow: one torpedo, its gyro found (by halving, on fireControl) so that
// the target shows the angle asked; then attackSheet and tdcAt as for the sheet itself.
const r0 = req.rows[0], norm = a => ((a % 360) + 360) % 360;
const aobOf = g => E.fireControl({ ownCourse: +r0.own_course, gyro: g, targetCourse: +r0.target_course,
  targetSpeed: +r0.target_speed, torpedoSpeed: A.torps[0].knots }).aob;
for (const want of req.aobs || []) {
  // the track angle runs from want (no lead) to want + 90 (more lead than any torpedo faster than its target needs),
  // short of 180 (a track past it is the other side's)
  let lo = want, hi = Math.min(want + 90, 179.99);
  const gyroFor = ta => norm(+r0.target_course + ta - 180 - +r0.own_course);
  for (let i = 0; i < 60; i++) { const mid = (lo + hi) / 2; if (aobOf(gyroFor(mid)) < want) lo = mid; else hi = mid; }
  const row = { ...r0, gyro: String(gyroFor((lo + hi) / 2)), track: "", offset: "" };
  out.sweep.push({ want, ...pick(E.attackSheet([row]), 0) });
}
process.stdout.write(JSON.stringify(out));
"""


def solve(rows: list[dict], aobs: list[float] | None = None) -> dict:
    """A sheet's rows through the kit's Engage (attackSheet, tdcAt, fireControl)."""
    node = shutil.which("node")
    if not node:
        raise RuntimeError("the fire-control figures need Node (they run the kit's site/engage.js)")
    engage = str(paths.KIT / "site" / "engage.js")
    r = subprocess.run([node, "-e", NODE, engage], input=json.dumps({"rows": rows, "aobs": aobs or []}),
                       capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def sheet(engagement: str, attack: str, boat: str | None = None) -> dict:
    d = figures.load(engagement)
    sheets = d["sheets"][boat] if boat else next(iter(d["sheets"].values()))
    return sheets[attack]


def _side(v: float) -> str:
    return "starboard" if v >= 0 else "port"


# ---------------------------------------------------------------- drawing

def _t(x, y, s, size=6.5, fill=INK, family=DISPLAY, anchor="middle", weight="normal", italic=False, halo_=True,
       rotate=None):
    rot = f' transform="rotate({rotate:.1f} {x:.1f} {y:.1f})"' if rotate is not None else ""
    style = ' font-style="italic"' if italic else ""
    h = f' stroke="{PAPER}" stroke-width="2.2" stroke-linejoin="round" paint-order="stroke"' if halo_ else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{family}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}" font-weight="{weight}"{style}{h}{rot}>{escape(s)}</text>')


def _line(a, b, stroke=PENCIL, width=0.6, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{a[0]:.2f}" y1="{a[1]:.2f}" x2="{b[0]:.2f}" y2="{b[1]:.2f}" stroke="{stroke}" '
            f'stroke-width="{width}"{d} stroke-linecap="round"/>')


def _hull(cx, cy, heading, length, beam, fill, stroke, sw=0.5):
    """A ship in plan, to scale: a pointed bow, a rounded stern, heading in degrees on the page (up is 0)."""
    L, B = length / 2, beam / 2
    d = (f"M 0 {-L:.2f} C {B * 0.9:.2f} {-L * 0.55:.2f} {B:.2f} {-L * 0.2:.2f} {B:.2f} {L * 0.55:.2f} "
         f"Q {B:.2f} {L:.2f} 0 {L:.2f} Q {-B:.2f} {L:.2f} {-B:.2f} {L * 0.55:.2f} "
         f"C {-B:.2f} {-L * 0.2:.2f} {-B * 0.9:.2f} {-L * 0.55:.2f} 0 {-L:.2f} Z")
    return (f'<path d="{d}" transform="translate({cx:.2f} {cy:.2f}) rotate({heading:.1f})" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{sw}"/>')


def _arc(c, r, a0, a1, stroke=PENCIL, width=0.6):
    """An arc about page point c, radius r points, from bearing a0 to a1 (degrees on the page, clockwise from up),
    the short way round."""
    d = ((a1 - a0 + 540) % 360) - 180
    p0 = (c[0] + r * math.sin(math.radians(a0)), c[1] - r * math.cos(math.radians(a0)))
    p1 = (c[0] + r * math.sin(math.radians(a0 + d)), c[1] - r * math.cos(math.radians(a0 + d)))
    sweep = 1 if d > 0 else 0
    return (f'<path d="M {p0[0]:.2f} {p0[1]:.2f} A {r:.2f} {r:.2f} 0 0 {sweep} {p1[0]:.2f} {p1[1]:.2f}" fill="none" '
            f'stroke="{stroke}" stroke-width="{width}"/>')


def _arrowhead(tip, bearing, size=3.2, fill=PENCIL):
    a = math.radians(bearing)
    ux, uy = math.sin(a), -math.cos(a)
    px, py = -uy, ux
    b = (tip[0] - ux * size, tip[1] - uy * size)
    return (f'<path d="M {tip[0]:.2f} {tip[1]:.2f} L {b[0] + px * size * 0.42:.2f} {b[1] + py * size * 0.42:.2f} '
            f'L {b[0] - px * size * 0.42:.2f} {b[1] - py * size * 0.42:.2f} Z" fill="{fill}"/>')


def _bearing(a, b):
    """The bearing from yards-point a to b, degrees true (x east, y north)."""
    return math.degrees(math.atan2(b[0] - a[0], b[1] - a[1])) % 360


def _along(p, bearing, d):
    return (p[0] + d * math.sin(math.radians(bearing)), p[1] + d * math.cos(math.radians(bearing)))


def _svg(W, H, body):
    return halo.split(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.1f}pt" height="{H:.1f}pt" '
                      f'viewBox="0 0 {W:.1f} {H:.1f}">{"".join(body)}</svg>')


def _cites(sh: dict) -> list[str]:
    out: list[str] = []
    w = sh.get("words") or []
    for x in (w if isinstance(w, list) else [w]):
        for k in ("page", "table_page"):
            if isinstance(x, dict) and x.get(k) and x[k] not in out:
                out.append(x[k])
    return out


def triangle(engagement: str, attack: str, width_in: float = 3.2, boat: str | None = None) -> tuple[str, dict]:
    """The attack's fire-control triangle, north up, to scale: own ship at firing, the target where the sheet's range
    and the solution put her, the intercept where the point of aim's torpedo meets her track; the angle on the bow at
    the target, the lead at the boat, the track angle at the intercept; the spread's torpedoes on own course plus each
    typed gyro."""
    sh = sheet(engagement, attack, boat)
    rows = sh["torpedoes"]
    S = solve(rows)
    a = S["aim"]
    if not a["ok"] or not a["solved"]:
        raise ValueError(f"{attack}: engage.js gives no solution ({'; '.join(S['problems'])})")
    own_course = float(rows[0]["own_course"])
    B = (0.0, 0.0)
    T = tuple(a["p0"])
    I = _along(B, a["torpedoCourse"], a["run"])

    # the frame: every point in yards, with room for the labels round them
    xs = [B[0], T[0], I[0]] + [_along(B, t["course"], a["run"] * 1.1)[0] for t in S["torps"]]
    ys = [B[1], T[1], I[1]]
    pad_l, pad_r, pad_t, pad_b = 0.70, 0.42, 0.10, 0.12
    span_x = max(xs) - min(xs)
    W = width_in * 72
    yd = W / (span_x * (1 + pad_l + pad_r))
    H = (max(ys) - min(ys)) * yd * (1 + pad_t + pad_b) + 34

    def P(p):
        return (W * pad_l / (1 + pad_l + pad_r) + (p[0] - min(xs)) * yd,
                (max(ys) - p[1]) * yd + (max(ys) - min(ys)) * yd * pad_t + 6)

    b, t, i = P(B), P(T), P(I)
    body = [f'<rect width="{W:.1f}" height="{H:.1f}" fill="{PAPER}"/>']
    # the target's track, assumed steady: from astern of her through the intercept and on
    body.append(_line(P(_along(T, a["course"] + 180, 120)), P(_along(I, a["course"], 260)), PENCIL, 0.55, "2 1.5"))
    # the line of sight at firing
    body.append(_line(b, t, PENCIL, 0.45, "3 1.2 0.6 1.2"))
    # the spread as typed: own course + each gyro, faint, a little past the point of aim's run
    for tp in S["torps"]:
        if tp["course"] is not None:
            body.append(_line(b, P(_along(B, tp["course"], a["run"] * 1.08)), FAINT, 0.5))
    # the point of aim's torpedo, the triangle's third side
    body.append(_line(b, i, BLUE, 0.9))
    body.append(_arrowhead(i, a["torpedoCourse"], 3.6, BLUE))
    # own ship's head
    body.append(_line(b, P(_along(B, own_course, 230)), BLUE, 0.6))
    body.append(_arrowhead(P(_along(B, own_course, 230)), own_course, 3.0, BLUE))
    # the ships, to scale: the target 400 by 55 ft (assumed, engage.js's default), own ship 312 by 27
    body.append(_hull(t[0], t[1], a["course"], 400 / 3 * yd, 55 / 3 * yd, "#fbfaf6", PENCIL, 0.6))
    body.append(_hull(b[0], b[1], own_course, 312 / 3 * yd, 27 / 3 * yd, BLUE, BLUE, 0.3))
    body.append(f'<circle cx="{i[0]:.2f}" cy="{i[1]:.2f}" r="1.6" fill="{PAPER}" stroke="{INK}" stroke-width="0.7"/>')

    # the three angles, each labelled clear of the triangle with a leader to its arc
    def leader(frm, to, words, value, anchor, colour=PENCIL):
        body.append(_line(frm, (to[0] + (3 if anchor == "start" else -3), to[1] - 2), colour, 0.35))
        body.append(_t(to[0] + (4 if anchor == "start" else -4), to[1], words, 6.0, colour, DISPLAY, anchor, italic=True))
        body.append(_t(to[0] + (4 if anchor == "start" else -4), to[1] + 7.5, value, 5.8, colour, TYPED, anchor))

    def arc_mid(c, r, a0, a1):
        m_ = a0 + (((a1 - a0 + 540) % 360) - 180) / 2
        return (c[0] + r * math.sin(math.radians(m_)), c[1] - r * math.cos(math.radians(m_)))

    los_from_t = _bearing(T, B)
    body.append(_arc(t, 18, a["course"], los_from_t))
    am = arc_mid(t, 18, a["course"], los_from_t)
    leader(am, (t[0] - 6, t[1] + 42), "angle on the bow", f"{abs(a['aob']):.1f}° {_side(a['aob'])}", "end")

    back = (a["torpedoCourse"] + 180) % 360
    body.append(_arc(i, 16, a["course"], back))
    tmid = arc_mid(i, 16, a["course"], back)
    leader(tmid, (i[0] + 34, i[1] + 30), "track angle", f"{a['track']:.1f}° {_side(1 if a['side'] == 'S' else -1)}",
           "start")

    r_b = 0.42 * math.dist(b, t)
    body.append(_arc(b, r_b, a["bearing"], a["torpedoCourse"], INK, 0.7))
    lend = (b[0] + r_b * math.sin(math.radians(a["bearing"])), b[1] - r_b * math.cos(math.radians(a["bearing"])))
    leader(lend, (lend[0] - 16, lend[1] + 4), "lead", f"{a['lead']:.1f}°", "end", INK)

    # the gyro angle: own head to the torpedo's course
    r_g = 30
    body.append(_arc(b, r_g, own_course, a["torpedoCourse"], BLUE, 0.6))
    body.append(_t(b[0] + 6, b[1] - r_g + 2, f"gyro {a['gyro']:.1f}°", 5.6, BLUE, TYPED, "start"))

    # what each corner and side is
    body.append(_t(t[0] - 12, t[1] - 9, "target at firing", 6.2, PENCIL, DISPLAY, "end", italic=True))
    body.append(_t(t[0] - 12, t[1] - 1.5, f"{a['course']:03.0f}° · {a['speed']:.0f} kn", 5.6, PENCIL, TYPED, "end"))
    body.append(_t(i[0] + 4, i[1] - 5, "intercept", 6.2, INK, DISPLAY, "start", italic=True))
    los = P(_along(B, a["bearing"], a["range"] * 0.62))
    body.append(_t(los[0] - 6, los[1], f"range {a['range']:,.0f} yds", 5.8, PENCIL, TYPED, "end"))
    body.append(_t(los[0] - 6, los[1] + 7.5, f"bearing {a['bearing']:.1f}°", 5.8, PENCIL, TYPED, "end"))
    edge = max((tp["course"] for tp in S["torps"] if tp["course"] is not None),
               key=lambda c: ((c - a["torpedoCourse"] + 540) % 360) - 180)
    run = P(_along(B, edge, a["run"] * 0.55))
    body.append(_t(run[0] + 6, run[1], "torpedo run", 6.0, BLUE, DISPLAY, "start", italic=True))
    body.append(_t(run[0] + 6, run[1] + 7.5, f"{a['run']:,.0f} yds on {a['torpedoCourse']:.1f}°", 5.8, BLUE, TYPED,
                   "start"))
    body.append(_t(b[0] - 8, b[1] + 2, "own ship", 6.2, BLUE, DISPLAY, "end", italic=True))
    body.append(_t(b[0] - 8, b[1] + 9.5, f"{own_course:03.0f}° · {S['ownSpeed']:.0f} kn", 5.8, BLUE, TYPED, "end"))

    # north, a scale of 500 yards, the credit
    nx, ny = W - 12, 12
    body.append(_line((nx, ny + 16), (nx, ny), INK, 0.6))
    body.append(_arrowhead((nx, ny), 0, 3.2, INK))
    body.append(_t(nx, ny - 3, "N", 6.0, INK, DISPLAY, weight="bold", halo_=False))
    sx, sy = 8, H - 20
    body.append(_line((sx, sy), (sx + 500 * yd, sy), INK, 0.6))
    for k in range(0, 6):
        body.append(_line((sx + k * 100 * yd, sy - (2 if k % 5 else 3)), (sx + k * 100 * yd, sy), INK, 0.4))
    body.append(_t(sx + 500 * yd + 4, sy + 2, "500 yards", 5.4, MUTED, DISPLAY, "start", italic=True, halo_=False))
    body.append(_t(8, H - 8, "drawn to scale for this research from the attack data sheet", 5.4, MUTED, DISPLAY,
                   "start", italic=True, halo_=False))

    torps = [{"tube": tp["tube"], "gyro": tp["gyro"], "track": tp["track"], "course": tp["course"],
              "derived_track": f"{tp['fc']['track']:.0f}{tp['fc']['side']}", "knots": tp["knots"]}
             for tp in S["torps"]]
    not_typed = [f"tube {x['tube']}: typed {x['track']}, own course and gyro give {x['derived_track']}"
                 for x in torps if x["track"] and x["track"].strip().upper() != x["derived_track"]]
    notes = {"attack": attack, "own_course": own_course, "own_speed": S["ownSpeed"],
             "target": {k: a[k] for k in ("course", "speed", "range")},
             "bearing": round(a["bearing"], 1), "aob": round(a["aob"], 1), "lead": round(a["lead"], 1),
             "track": round(a["track"], 1), "side": a["side"], "gyro": round(a["gyro"], 1),
             "torpedo_course": round(a["torpedoCourse"], 1), "run_yd": round(a["run"]),
             "distance_to_track": round(a["distanceToTrack"]), "torpedo_knots": a["torpedoSpeed"],
             "k": round(a["speed"] / a["torpedoSpeed"], 3), "torpedoes": torps, "disagree": not_typed,
             "assumed": S["assumed"] + ["the target drawn 400 ft by 55 (not given on the sheet)"],
             "problems": S["problems"], "cites": _cites(sh)}
    return _svg(W, H, body), notes


def aob_strip(engagement: str, attack: str, width_in: float = 5.5, boat: str | None = None,
              aobs: tuple[float, ...] = (20, 45, 90, 135, 160)) -> tuple[str, dict]:
    """The attack's triangle beside the same shot at other angles on the bow: the same range, target speed and
    torpedo speed, each panel turned so the line of sight runs up the page, all at one scale."""
    sh = sheet(engagement, attack, boat)
    S = solve(sh["torpedoes"], list(aobs))
    panels = sorted([{**S["aim"], "want": None}] + S["sweep"], key=lambda p: p["aob"])
    W = width_in * 72
    n = len(panels)
    pw = W / n
    rng = max(p["range"] for p in panels)
    yd = pw * 1.1 / rng
    top, foot = 8, 50
    fig_h = rng * yd * 1.16
    H = top + fig_h + foot
    body = [f'<rect width="{W:.1f}" height="{H:.1f}" fill="{PAPER}"/>']
    out = []
    for k, p in enumerate(panels):
        x0 = pw * k
        cx = x0 + pw * 0.5
        b = (cx, top + fig_h - 4)
        turn = p["bearing"]       # turned through the bearing, so the line of sight runs up the page

        def Q(pt, b=b, turn=turn):
            r, brg = math.hypot(*pt), math.degrees(math.atan2(pt[0], pt[1])) - turn
            return (b[0] + r * yd * math.sin(math.radians(brg)), b[1] - r * yd * math.cos(math.radians(brg)))
        T = tuple(p["p0"])
        I = _along((0, 0), p["torpedoCourse"], p["run"])
        t, i = Q(T), Q(I)
        this = p["want"] is None
        clip = f"fc-aob-{k}"
        body.append(f'<clipPath id="{clip}"><rect x="{x0 + 1:.1f}" y="0" width="{pw - 2:.1f}" '
                    f'height="{top + fig_h:.1f}"/></clipPath><g clip-path="url(#{clip})">')
        body.append(_line(Q(_along(T, p["course"] + 180, 400)), Q(_along(I, p["course"], 400)), PENCIL, 0.45,
                          "2 1.5"))
        body.append(_line(b, t, PENCIL, 0.4, "3 1.2 0.6 1.2"))
        body.append(_line(b, i, BLUE, 0.9 if this else 0.7))
        body.append(_arrowhead(i, (p["torpedoCourse"] - turn) % 360, 3.0, BLUE))
        body.append(_hull(t[0], t[1], (p["course"] - turn) % 360, 400 / 3 * yd, 55 / 3 * yd, "#fbfaf6", PENCIL, 0.5))
        body.append(f'<circle cx="{i[0]:.2f}" cy="{i[1]:.2f}" r="1.4" fill="{PAPER}" stroke="{INK}" '
                    f'stroke-width="0.6"/>')
        body.append("</g>")
        body.append(f'<circle cx="{b[0]:.2f}" cy="{b[1]:.2f}" r="1.8" fill="{BLUE}"/>')
        y0 = top + fig_h + 9
        body.append(_t(cx, y0, "as fired" if this else "the same shot", 5.6, BLUE if this else MUTED, DISPLAY,
                       italic=True, halo_=False))
        body.append(_t(cx, y0 + 8.5, f"angle on the bow {abs(p['aob']):.0f}°", 6.0, INK, DISPLAY, italic=True,
                       halo_=False, weight="bold" if this else "normal"))
        body.append(_t(cx, y0 + 17, f"lead {p['lead']:.1f}°", 5.6, INK, TYPED, halo_=False))
        body.append(_t(cx, y0 + 24.5, f"track {p['track']:.1f}°", 5.6, INK, TYPED, halo_=False))
        body.append(_t(cx, y0 + 32, f"run {p['run']:,.0f} yds", 5.6, MUTED, TYPED, halo_=False))
        if k:
            body.append(_line((x0, top), (x0, H - 12), RULE, 0.4))
        out.append({"aob": round(p["aob"], 1), "lead": round(p["lead"], 1), "track": round(p["track"], 1),
                    "run_yd": round(p["run"]), "as_fired": this})
    body.append(_t(4, H - 3, f"line of sight up the page · target {S['aim']['speed']:.0f} kn, torpedo "
                   f"{S['aim']['torpedoSpeed']:.0f} kn, range {rng:,.0f} yds · one scale · drawn for this research",
                   5.2, MUTED, DISPLAY, "start", italic=True, halo_=False))
    return _svg(W, H, body), {"panels": out, "assumed": S["assumed"], "cites": _cites(sh),
                              "k": round(S["aim"]["speed"] / S["aim"]["torpedoSpeed"], 3)}


# The computer, as the site's TDC page draws it after OP 1056: the dials of each face by the names its photographs give
# them (the Position Keeper, Fig. 98, p. 107; the Angle Solver, Fig. 102, p. 111), as site/tdc.js names them.
PK_DIALS = ["target speed", "target length", "own course", "own speed", "target", "own ship", "range",
            "relative target bearing", "distance to track", "angle solver range", "generating", "time"]
AS_DIALS = ["gyro angle order", "offset angle", "torpedo run", "depth-speed", "correct solution"]


def _tdc_dials() -> tuple[list[str], list[str]]:
    """The dial names as site/tdc.js and tdc-page.js letter them, read from those files so the two can't drift."""
    names = set()
    for f in ("tdc.js", "tdc-page.js"):
        names |= set(re.findall(r'"([a-z][a-z -]+)"', (paths.KIT / "site" / f).read_text()))
    return [d for d in PK_DIALS if d in names], [d for d in AS_DIALS if d in names]


def tdc_diagram(width_in: float = 5.5) -> tuple[str, dict]:
    """The Torpedo Data Computer Mark 3 as a diagram: what went in and from where, the position keeper running the
    target forward, the angle solver working the shot, the gyro orders to the tubes, and the generated bearing back to
    the periscope to be checked."""
    pk, sv = _tdc_dials()
    W = width_in * 72
    col = [12, W * 0.27, W * 0.565, W * 0.83]
    wid = [W * 0.2, W * 0.22, W * 0.205, W * 0.165]
    pk_y, as_y = 8, 30
    pk_h = 22 + 9 + 8.2 * len(pk) + 4
    as_h = 22 + 9 + 8.2 * len(sv) + 4
    H = pk_y + pk_h + 30
    body = [f'<rect width="{W:.1f}" height="{H:.1f}" fill="{PAPER}"/>']

    def box(x, y, w, h, title, sub, lines, ink=INK, fill="#f1f2ec"):
        b = [f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="2" fill="{fill}" stroke="{ink}" '
             f'stroke-width="0.7"/>']
        b.append(_t(x + 6, y + 11, title, 7.4, ink, DISPLAY, "start", weight="bold", halo_=False))
        b.append(_t(x + 6, y + 19, sub, 5.4, MUTED, DISPLAY, "start", italic=True, halo_=False))
        for k, ln in enumerate(lines):
            b.append(_t(x + 8, y + 29 + 8.2 * k, ln, 6.0, ink, DISPLAY, "start", italic=True, halo_=False))
        return b

    def arrow(a, b_, colour=INK, width=0.8, dash=None):
        ang = math.degrees(math.atan2(b_[0] - a[0], -(b_[1] - a[1])))
        return [_line(a, b_, colour, width, dash), _arrowhead(b_, ang, 3.4, colour)]

    # what went in, and from where
    ins = [("Periscope, radar, sound", "bearing, range", "measured at each look", PENCIL),
           ("By eye", "angle on the bow", "estimated", PENCIL),
           ("From a series of looks", "target course, speed", "set in by hand", PENCIL),
           ("Own instruments", "own course, speed", "fed in automatically", BLUE)]
    y = pk_y + 4
    for k, (title, what, how, ink) in enumerate(ins):
        body.append(_t(col[0], y + 7, title, 6.0, ink, DISPLAY, "start", weight="bold", halo_=False))
        body.append(_t(col[0] + 4, y + 15.5, what, 6.0, ink, DISPLAY, "start", italic=True, halo_=False))
        body.append(_t(col[0] + 4, y + 23.5, how, 5.4, MUTED, DISPLAY, "start", italic=True, halo_=False))
        body += arrow((col[0] + wid[0], y + 13), (col[1] - 2, pk_y + 30 + k * 16), BLUE if k == 3 else INK, 0.6)
        y += 32
    body += box(col[1], pk_y, wid[1], pk_h, "Position Keeper", "runs the target on from the last look", pk)
    body += box(col[2], as_y, wid[2], as_h, "Angle Solver", "works the shot, continuously", sv)
    body += box(col[3], as_y, wid[3], 50, "The torpedoes", "a gyro angle set in each", ["forward tubes 1–6",
                "after tubes 7–10"], BLUE, "#eef3fb")
    body.append(_t(col[3] + 4, as_y + 60, "automatically, or by", 5.6, MUTED, DISPLAY, "start", italic=True,
                   halo_=False))
    body.append(_t(col[3] + 4, as_y + 68, "“follow the pointer”", 5.6, MUTED, DISPLAY, "start", italic=True,
                   halo_=False))
    # position keeper -> angle solver: the bearing and range now; angle solver -> tubes: the gyro orders
    gx = (col[1] + wid[1] + col[2]) / 2
    body += arrow((col[1] + wid[1], as_y + 30), (col[2] - 1, as_y + 30))
    body.append(_t(gx, as_y + 18, "bearing and", 5.4, INK, DISPLAY, italic=True, halo_=False))
    body.append(_t(gx, as_y + 25, "range now", 5.4, INK, DISPLAY, italic=True, halo_=False))
    ox = (col[2] + wid[2] + col[3]) / 2
    body += arrow((col[2] + wid[2], as_y + 30), (col[3] - 1, as_y + 30), BLUE)
    body.append(_t(ox, as_y + 18, "gyro angle", 5.4, BLUE, DISPLAY, italic=True, halo_=False))
    body.append(_t(ox, as_y + 25, "orders", 5.4, BLUE, DISPLAY, italic=True, halo_=False))
    # the torpedo's speed and depth into the solver, from below
    ty = as_y + as_h + 18
    body += arrow((col[2] + wid[2] / 2, ty), (col[2] + wid[2] / 2, as_y + as_h + 1), INK, 0.6)
    body.append(_t(col[2] + wid[2] / 2, ty + 8, "the torpedo's speed, depth set", 5.6, INK, DISPLAY, italic=True,
                   halo_=False))
    # the check: the generated bearing back to the periscope, round the outside
    gy = pk_y + pk_h + 12
    px = col[1] + wid[1] * 0.5
    body.append(_line((px, pk_y + pk_h), (px, gy), PENCIL, 0.6, "2.5 1.5"))
    body.append(_line((px, gy), (4, gy), PENCIL, 0.6, "2.5 1.5"))
    body.append(_line((4, gy), (4, pk_y + 9), PENCIL, 0.6, "2.5 1.5"))
    body += arrow((4, pk_y + 9), (col[0] - 2, pk_y + 9), PENCIL, 0.6)
    body.append(_t(px - 4, gy - 3, "generated bearing, to fire on between looks", 5.6, PENCIL, DISPLAY, "end",
                   italic=True))
    body.append(_t(W - 4, H - 4, "Torpedo Data Computer Mark 3 · its dials as its manual's photographs name them · "
                   "drawn for this research", 5.2, MUTED, DISPLAY, "end", italic=True, halo_=False))
    return _svg(W, H, body), {"position_keeper": pk, "angle_solver": sv,
                              "cites": ["op1056/p107", "op1056/p111", "usf-25a/p50", "rowland-boyd/p399"]}


def prepare(req: dict, build: Path) -> dict:
    """The preparer for a `fire-control` request: view "triangle", "aob" or "tdc"."""
    view = req["view"]
    if view == "triangle":
        svg, notes = triangle(req["engagement"], req["attack"], req.get("width") or 3.2, req.get("boat"))
    elif view == "aob":
        svg, notes = aob_strip(req["engagement"], req["attack"], req.get("width") or 5.5, req.get("boat"),
                               tuple(req.get("aobs") or (20, 45, 90, 135, 160)))
    elif view == "tdc":
        svg, notes = tdc_diagram(req.get("width") or 5.5)
    else:
        raise ValueError(f"no fire-control view {view!r}")
    key = req["key"]
    name = re.sub(r"[^A-Za-z0-9]+", "-", key).strip("-")[:60] + "-" + hashlib.sha1(key.encode()).hexdigest()[:8] + ".svg"
    (build / name).write_text(svg)
    return {"kind": "firecontrol", "path": f"build/{name}", **notes}
