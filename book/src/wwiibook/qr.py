"""A QR code as SVG, square modules, high error correction (so a silhouette can later sit in its centre)."""
from pathlib import Path

import segno


def svg(url: str, dest: Path, dark: str = "#000000") -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    segno.make(url, error="h").save(str(dest), kind="svg", dark=dark, light=None, border=0, scale=10, xmldecl=False,
                                     svgns=True, nl=False)
    return dest


CARD, CARD_EDGE, CARD_INK = "#eadcb4", "#b9a77c", "#231f1a"
CTA_INK = "#8a5a0b"       # the book's call-to-action ink (core.typ tokens.cta-ink): the card's caption sends a reader on
HOLE = "#1d1a16"          # the dark backing seen through a hole
LIP = "#c9b78c"           # the card's cut edge, lit from the top left, inside a hole's top and left
MONO = "Courier Prime, Courier New, monospace"
COND = "IBM Plex Sans, IBM Plex Sans Condensed, Arial Narrow, sans-serif"


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def punch(url: str, dest: Path, fields: tuple[str, ...] = (), caption: str = "Scan to see it move",
          m: float = 2.6) -> Path:
    """The QR code as a punched card: buff stock with its corner cut, the code's modules punched through as an IBM
    card's holes turned to lie along the card's long way, so the dark backing shows through, each with the card's
    cut edge. The three finder squares are die-cut windows (one square ring and one square, each a single hole), since
    a scanner needs them unbroken. Four modules of plain card round the code are its quiet zone.

    `fields`: the typed fields down the card's left side, each a ship, a convoy, a date-time group; a field's lines
    split at "\n" ("U.S.S. BANG\n(SS-385)"); the first field in bold. The left side is as wide as the longest line,
    so no type reaches the quiet zone. Studied against eleven other styles, read clean and in simulated phone
    photographs by two decoders."""
    q = segno.make(url, error="m")
    M = [[bool(v) for v in row] for row in q.matrix]
    N = len(M)
    side, quiet = N * m, 4 * m
    bold, regular, step = 7.0, 6.2, 8.6
    lines: list[tuple[str, bool]] = []
    for k, f in enumerate(fields):
        if k:
            lines.append(("", False))
        lines += [(ln, k == 0) for ln in f.split("\n")]
    widest = max([len(t) * (bold if b else regular) * 0.6 for t, b in lines] + [40.0])   # Courier: 0.6 em a character
    left = 16 + widest + 2
    W, H = left + side + 2 * quiet, side + 2 * quiet + 4
    qx, qy = left + quiet, quiet + 2
    # a faint shadow under the card, down and to the right: three offset copies of its outline, each fainter, so it
    # stays vector and soft without a blur filter (which a PDF would rasterise); it lies outside the quiet zone
    card = f"M12,0 H{W:.1f} V{H:.1f} H0 V12 Z"
    b = [f'<path d="{card}" transform="translate({d:.1f},{d * 1.3:.1f})" fill="#000" fill-opacity="{a}"/>'
         for d, a in ((2.2, 0.035), (1.5, 0.05), (0.8, 0.07))]
    b.append(f'<path d="{card}" fill="{CARD}" stroke="{CARD_EDGE}" stroke-width="0.6"/>')
    for i, (t, is_bold) in enumerate(lines):
        if t:
            b.append(f'<text x="16" y="{22 + i * step:.1f}" font-family="{MONO}" font-size="{bold if is_bold else regular}" '
                     f'font-weight="{"bold" if is_bold else "normal"}" fill="{CARD_INK}">{_esc(t)}</text>')
    b.append(f'<text x="16" y="{H - 9:.1f}" font-family="{COND}" font-size="6" fill="{CTA_INK}" '
             f'font-style="italic">{_esc(caption)}</text>')

    def hole(x, y, w, h, rx=0.0):
        b.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" rx="{rx:.2f}" fill="{HOLE}"/>')
        t = min(w, h) * 0.12
        b.append(f'<path d="M{x:.2f},{y + h:.2f} V{y:.2f} H{x + w:.2f} v{t:.2f} H{x + t:.2f} V{y + h:.2f} Z" '
                 f'fill="{LIP}" opacity="0.55"/>')

    corners = ((0, 0), (0, N - 7), (N - 7, 0))
    for r0, c0 in corners:
        x0, y0 = qx + c0 * m, qy + r0 * m
        b.append(f'<path d="M{x0:.2f},{y0:.2f} h{7 * m:.2f} v{7 * m:.2f} h{-7 * m:.2f} Z M{x0 + m:.2f},{y0 + m:.2f} '
                 f'v{5 * m:.2f} h{5 * m:.2f} v{-5 * m:.2f} Z" fill="{HOLE}" fill-rule="evenodd"/>')
        t = m * 0.14
        b.append(f'<path d="M{x0:.2f},{y0 + 7 * m:.2f} V{y0:.2f} H{x0 + 7 * m:.2f} v{t:.2f} H{x0 + t:.2f} '
                 f'V{y0 + 7 * m:.2f} Z" fill="{LIP}" opacity="0.55"/>')
        hole(x0 + 2 * m, y0 + 2 * m, 3 * m, 3 * m)
    for r in range(N):
        for c in range(N):
            if M[r][c] and not any(r0 <= r < r0 + 7 and c0 <= c < c0 + 7 for r0, c0 in corners):
                x, y = qx + c * m, qy + r * m
                hole(x + m * 0.02, y + m * 0.24, m * 0.96, m * 0.52, m * 0.05)
    dest.parent.mkdir(parents=True, exist_ok=True)
    Ws, Hs = W + 3, H + 3.5             # room for the shadow
    dest.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{Ws:.1f}pt" height="{Hs:.1f}pt" '
                    f'viewBox="0 0 {Ws:.1f} {Hs:.1f}">{"".join(b)}</svg>')
    return dest
