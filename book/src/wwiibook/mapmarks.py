"""The two marks every map in the book carries: a north arrow and a scale bar.

The book's rule: every map shows which way is north, and a scale: kilometres over statute miles on land, nautical miles
at sea. A perspective view (the oblique views) has no single scale, so its bar is the scale across the view at one
stated depth, and says so; its north arrow is the direction of north on the ground there, as the camera sees it.

  north(x, y, angle)                 an arrow with N; angle is clockwise from straight up, in degrees
  scale(x, y, pt_per_km, medium)     a bar: "land" km over mi, "sea" nautical miles; returns (svg, width)
  north_angle(project, lon, lat)     the screen angle of north at a point, from a function (lon, lat) -> (x, y)
"""
import math
from html import escape

INK, PAPER = "#000000", "#ffffff"
DISPLAY = "IBM Plex Sans, IBM Plex Sans Condensed, Arial Narrow, sans-serif"
KM_PER_MI, KM_PER_NM = 1.609344, 1.852
NICE = (0.1, 0.2, 0.25, 0.5, 1, 2, 2.5, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000, 2000, 5000)


def _nice(limit: float) -> float:
    """The largest round number not over `limit` (at least the smallest)."""
    best = NICE[0]
    for v in NICE:
        if v <= limit:
            best = v
    return best


def _num(v: float) -> str:
    return f"{v:g}" if v >= 1 else {0.1: "0.1", 0.2: "0.2", 0.25: "¼", 0.5: "½"}.get(v, f"{v:g}")


def _text(x, y, s, size=6.0, anchor="start", weight="normal", italic=False):
    style = ' font-style="italic"' if italic else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{DISPLAY}" font-size="{size}" fill="{INK}" '
            f'text-anchor="{anchor}" font-weight="{weight}"{style} stroke="{PAPER}" stroke-width="2" '
            f'stroke-linejoin="round" paint-order="stroke">{escape(s)}</text>')


def north(x: float, y: float, angle: float = 0.0, size: float = 13.0) -> str:
    """A north arrow standing at (x, y) (its foot), its tip toward north: `angle` clockwise from up, in degrees."""
    a = math.radians(angle)
    dx, dy = math.sin(a), -math.cos(a)
    tip = (x + dx * size, y + dy * size)
    px, py = -dy, dx                                   # across the arrow
    half = (x + dx * size * 0.45, y + dy * size * 0.45)
    left = (half[0] + px * 3.2, half[1] + py * 3.2)
    right = (half[0] - px * 3.2, half[1] - py * 3.2)
    return (f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{tip[0]:.1f}" y2="{tip[1]:.1f}" stroke="{PAPER}" stroke-width="2.6"/>'
            f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{tip[0]:.1f}" y2="{tip[1]:.1f}" stroke="{INK}" stroke-width="0.8"/>'
            f'<path d="M{left[0]:.1f},{left[1]:.1f} L{tip[0]:.1f},{tip[1]:.1f} L{right[0]:.1f},{right[1]:.1f} Z" '
            f'fill="{INK}" stroke="{PAPER}" stroke-width="0.5"/>'
            + _text(tip[0] + dx * 5, tip[1] + dy * 5 + 2.3, "N", 7, "middle", "bold"))


def north_angle(project, lon: float, lat: float, d: float = 0.01) -> float:
    """North's screen direction at (lon, lat), clockwise from up, for any projection `project(lon, lat) -> (x, y)`."""
    (x0, y0), (x1, y1) = project(lon, lat), project(lon, lat + d)
    return math.degrees(math.atan2(x1 - x0, -(y1 - y0)))


def scale(x: float, y: float, pt_per_km: float, medium: str = "land", max_len: float = 60.0,
          anchor: str = "start", note: str | None = None) -> tuple[str, float]:
    """A scale bar at (x, y) (its baseline's left end, or right end with anchor "end"). Land: kilometres above the
    line and statute miles below it, each its own round length; sea: nautical miles. `note` is set small under it
    (a perspective view's "across the view at ..."). Returns the svg and the bar's width."""
    out = []
    if medium == "sea":
        nm = _nice(max_len / (pt_per_km * KM_PER_NM))
        bars = [(nm * KM_PER_NM * pt_per_km, f"{_num(nm)} nautical mile{'' if nm == 1 else 's'}", -1)]
    else:
        km = _nice(max_len / pt_per_km)
        mi = _nice(max_len / (pt_per_km * KM_PER_MI))
        bars = [(km * pt_per_km, f"{_num(km)} km", -1), (mi * KM_PER_MI * pt_per_km, f"{_num(mi)} mi", 1)]
    width = max(L for L, _, _ in bars)
    x0 = x - width if anchor == "end" else x
    h = 10 + (9 if len(bars) > 1 else 0) + (7 if note else 0)
    note_w = len(note) * 5.2 * 0.47 if note else 0
    bx = min(x0, x0 + width - note_w)
    out.append(f'<rect x="{bx - 3:.1f}" y="{y - 10:.1f}" width="{x0 + width - bx + 6:.1f}" height="{h:.1f}" '
               f'fill="{PAPER}" fill-opacity="0.75"/>')
    out.append(f'<line x1="{x0:.1f}" y1="{y:.1f}" x2="{x0 + width:.1f}" y2="{y:.1f}" stroke="{INK}" stroke-width="0.8"/>')
    for L, words, side in bars:
        tick = 3 * side
        out.append(f'<path d="M{x0:.1f},{y:.1f} v{tick} M{x0 + L:.1f},{y:.1f} v{tick}" stroke="{INK}" '
                   'stroke-width="0.8" fill="none"/>')
        ty = y - 4 if side < 0 else y + 9
        out.append(_text(x0 + L / 2, ty, words, 6, "middle"))
    if note:                                           # set under the bar, ending where it ends
        out.append(f'<text x="{x0 + width:.1f}" y="{y + (16 if len(bars) > 1 else 8):.1f}" font-family="{DISPLAY}" '
                   f'font-size="5.2" font-style="italic" fill="{INK}" text-anchor="end" stroke="{PAPER}" '
                   f'stroke-width="2" stroke-linejoin="round" paint-order="stroke">{escape(note)}</text>')
    return "".join(out), width
