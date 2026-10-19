# /// script
# requires-python = ">=3.9"
# dependencies = ["pillow"]
# ///
"""Trace a silhouette from a recognition plate into a path for records/silhouettes/silhouettes.yml.

The plates print each view as a solid black silhouette. This takes a scan (or a rendered PDF page),
crops one view, and outlines it the way the existing aircraft were made:

  1. threshold to black and white (--threshold, 0-255: darker than this is the silhouette)
  2. optionally open the shape by N pixels (--open N) to drop antennas, pitot tubes and wires
  3. keep the largest connected shape (labels, arrows and the plate's text fall away)
  4. fill holes (panel lines and lettering inside the silhouette)
  5. optionally mirror it about its own centre line (--symmetric, for plan and head-on views)
  6. trace the outline, simplify it (--simplify, in output units), and scale it so the width is
     --width units (100: span for plan and head-on views, length for a profile)

  uv run tools/trace_silhouette.py PLATE.jpg --crop X Y W H [--symmetric] [--open 2] [--name plan]
      -> prints a line to paste under the aircraft:  plan: { w: 100, h: 86.8, d: "M50.7,0.0L..." }
  uv run tools/trace_silhouette.py PLATE.jpg --crop X Y W H --preview /tmp/check.png
      -> also writes the traced outline over the crop, to compare by eye

Check the preview: the outline should follow the plate's edge everywhere except where you meant it
not to (dropped antennas). Record the plate, page and edition in the entry's `source`, and cite it.
"""
import argparse
import sys

from PIL import Image, ImageDraw


def binary(img, threshold):
    """Image -> set-free 2D list of 0/1 (1 = dark)."""
    g = img.convert("L")
    w, h = g.size
    px = g.load()
    return [[1 if px[x, y] < threshold else 0 for x in range(w)] for y in range(h)]


def neighbours(x, y, w, h):
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        if 0 <= x + dx < w and 0 <= y + dy < h:
            yield x + dx, y + dy


def erode(b, n):
    h, w = len(b), len(b[0])
    for _ in range(n):
        b = [[1 if b[y][x] and all(b[j][i] for i, j in neighbours(x, y, w, h)) else 0 for x in range(w)] for y in range(h)]
    return b


def dilate(b, n):
    h, w = len(b), len(b[0])
    for _ in range(n):
        b = [[1 if b[y][x] or any(b[j][i] for i, j in neighbours(x, y, w, h)) else 0 for x in range(w)] for y in range(h)]
    return b


def largest_component(b):
    h, w = len(b), len(b[0])
    seen = [[False] * w for _ in range(h)]
    best = []
    for y in range(h):
        for x in range(w):
            if b[y][x] and not seen[y][x]:
                comp, stack = [], [(x, y)]
                seen[y][x] = True
                while stack:
                    cx, cy = stack.pop()
                    comp.append((cx, cy))
                    for nx in range(cx - 1, cx + 2):
                        for ny in range(cy - 1, cy + 2):
                            if 0 <= nx < w and 0 <= ny < h and b[ny][nx] and not seen[ny][nx]:
                                seen[ny][nx] = True
                                stack.append((nx, ny))
                if len(comp) > len(best):
                    best = comp
    out = [[0] * w for _ in range(h)]
    for x, y in best:
        out[y][x] = 1
    return out


def fill_holes(b):
    """Background not reachable from the border is a hole: fill it."""
    h, w = len(b), len(b[0])
    outside = [[False] * w for _ in range(h)]
    stack = [(x, y) for x in range(w) for y in (0, h - 1)] + [(x, y) for y in range(h) for x in (0, w - 1)]
    while stack:
        x, y = stack.pop()
        if outside[y][x] or b[y][x]:
            continue
        outside[y][x] = True
        stack.extend(neighbours(x, y, w, h))
    return [[0 if outside[y][x] else 1 for x in range(w)] for y in range(h)]


def mirror(b):
    """OR the shape with its reflection about the centre of its bounding box."""
    h, w = len(b), len(b[0])
    xs = [x for row in b for x, v in enumerate(row) if v]
    c2 = min(xs) + max(xs)            # twice the centre column
    out = [row[:] for row in b]
    for y in range(h):
        for x in range(w):
            if b[y][x] and 0 <= c2 - x < w:
                out[y][c2 - x] = 1
    return out


def outline(b):
    """Outer boundary of the shape as pixel-corner points, clockwise on screen (y down).

    Every filled pixel's edge that faces an empty pixel becomes a directed edge, oriented so the
    shape is on its right; chaining them gives closed loops, and the longest is the outline."""
    h, w = len(b), len(b[0])
    on = lambda x, y: 0 <= x < w and 0 <= y < h and b[y][x]
    nxt = {}
    for y in range(h):
        for x in range(w):
            if not b[y][x]:
                continue
            if not on(x, y - 1): nxt.setdefault((x, y), []).append((x + 1, y))
            if not on(x + 1, y): nxt.setdefault((x + 1, y), []).append((x + 1, y + 1))
            if not on(x, y + 1): nxt.setdefault((x + 1, y + 1), []).append((x, y + 1))
            if not on(x - 1, y): nxt.setdefault((x, y + 1), []).append((x, y))
    loops = []
    while nxt:
        start = next(iter(nxt))
        loop, p = [start], start
        while True:
            outs = nxt[p]
            q = outs.pop()
            if not outs:
                del nxt[p]
            if q == start:
                break
            loop.append(q)
            p = q
            if p not in nxt:
                break
        loops.append(loop)
    pts = max(loops, key=len)
    # keep only the corners
    n = len(pts)
    return [pts[i] for i in range(n)
            if (pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]) != (pts[(i + 1) % n][0] - pts[i][0], pts[(i + 1) % n][1] - pts[i][1])]


def rdp(pts, eps):
    """Ramer-Douglas-Peucker simplification of an open polyline."""
    if len(pts) < 3:
        return pts
    (x1, y1), (x2, y2) = pts[0], pts[-1]
    dx, dy = x2 - x1, y2 - y1
    norm = (dx * dx + dy * dy) ** 0.5 or 1e-9
    dist = [abs(dy * (x - x1) - dx * (y - y1)) / norm for x, y in pts[1:-1]]
    i = max(range(len(dist)), key=dist.__getitem__)
    if dist[i] <= eps:
        return [pts[0], pts[-1]]
    left, right = rdp(pts[:i + 2], eps), rdp(pts[i + 1:], eps)
    return left[:-1] + right


def trace(img, threshold=128, open_px=0, symmetric=False, width=100.0, simplify=0.3):
    b = binary(img, threshold)
    if open_px:
        b = dilate(erode(b, open_px), open_px)
    b = fill_holes(largest_component(b))
    if symmetric:
        b = mirror(b)
    pts = outline(b)
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    x0, y0, k = min(xs), min(ys), width / (max(xs) - min(xs))
    pts = [((x - x0) * k, (y - y0) * k) for x, y in pts]
    # simplify as a closed loop: split at the point farthest from the start
    far = max(range(len(pts)), key=lambda i: (pts[i][0] - pts[0][0]) ** 2 + (pts[i][1] - pts[0][1]) ** 2)
    loop = rdp(pts[:far + 1], simplify)[:-1] + rdp(pts[far:] + [pts[0]], simplify)[:-1]
    h = round((max(ys) - min(ys)) * k, 1)
    d = "M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in loop) + "Z"
    return {"w": round(width, 1), "h": h, "d": d, "points": loop, "k": k, "x0": x0, "y0": y0}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("image")
    ap.add_argument("--crop", nargs=4, type=int, metavar=("X", "Y", "W", "H"), help="the view, in image pixels")
    ap.add_argument("--threshold", type=int, default=128)
    ap.add_argument("--open", type=int, default=0, dest="open_px", help="drop details thinner than 2N pixels")
    ap.add_argument("--symmetric", action="store_true", help="mirror about the centre line (plan, head-on)")
    ap.add_argument("--width", type=float, default=100.0)
    ap.add_argument("--simplify", type=float, default=0.3, help="tolerance in output units")
    ap.add_argument("--name", default="plan", help="the view's key in the YAML: plan, front, profile")
    ap.add_argument("--preview", help="write the outline over the crop to this PNG")
    a = ap.parse_args()
    img = Image.open(a.image)
    if a.crop:
        x, y, w, h = a.crop
        img = img.crop((x, y, x + w, y + h))
    t = trace(img, a.threshold, a.open_px, a.symmetric, a.width, a.simplify)
    print(f'{a.name}: {{ w: {t["w"]:g}, h: {t["h"]:g}, d: "{t["d"]}" }}')
    print(f"{len(t['points'])} points", file=sys.stderr)
    if a.preview:
        p = img.convert("RGB")
        dr = ImageDraw.Draw(p)
        pts = [(x / t["k"] + t["x0"], y / t["k"] + t["y0"]) for x, y in t["points"]]
        dr.line(pts + [pts[0]], fill=(220, 30, 30), width=max(1, round(p.size[0] / 400)))
        p.save(a.preview)
        print(f"preview -> {a.preview}", file=sys.stderr)


if __name__ == "__main__":
    main()
