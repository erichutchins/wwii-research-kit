"""A QR code as SVG, square modules, high error correction (so a silhouette can later sit in its centre)."""
from pathlib import Path

import segno


def svg(url: str, dest: Path, dark: str = "#1c221d") -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    segno.make(url, error="h").save(str(dest), kind="svg", dark=dark, light=None, border=0, scale=10, xmldecl=False,
                                     svgns=True, nl=False)
    return dest


CARD, CARD_EDGE, CARD_PRINT, CARD_INK = "#eadcb4", "#b9a77c", "#b0644b", "#231f1a"
MONO = "Courier Prime, Courier New, monospace"
COND = "Barlow, Barlow Condensed, Arial Narrow, sans-serif"


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def punch(url: str, dest: Path, lines: tuple[str, ...] = (), caption: str = "Scan for the engagement") -> Path:
    """The QR code as a punched card: buff stock with its corner cut, the card's printed digit columns, the modules
    punched as slots. The finder squares stay solid and a quiet zone of four modules stays clear of the print, so it
    scans as any QR code does. `lines`: up to three typed lines at the card's head (a ship, a convoy, a date-time
    group)."""
    q = segno.make(url, error="m")
    M = [[bool(v) for v in row] for row in q.matrix]
    N = len(M)
    H = 136.0
    m = (H - 24) / (N + 8)                   # a module, with four modules of quiet zone above and below
    side = N * m
    W = 150 + side + 8 * m
    qx, qy = W - side - 4 * m - 6, (H - side) / 2
    b = [f'<path d="M14,0 H{W:.1f} V{H:.1f} H0 V14 Z" fill="{CARD}" stroke="{CARD_EDGE}" stroke-width="0.6"/>']
    for col in range(int((qx - 4 * m - 22) / 4.1)):
        x = 18 + col * 4.1
        for row in range(10):
            b.append(f'<text x="{x:.1f}" y="{40 + row * 8.6:.1f}" font-family="{MONO}" font-size="4.2" fill="{CARD_PRINT}" '
                     f'text-anchor="middle">{row}</text>')
    for i, s in enumerate(lines[:3]):
        b.append(f'<text x="18" y="{12 + i * 8.5:.1f}" font-family="{MONO}" font-size="{6.2 if i == 0 else 5.4}" '
                 f'font-weight="{"bold" if i == 0 else "normal"}" fill="{CARD_INK}">{_esc(s)}</text>')
    b.append(f'<text x="18" y="{H - 6:.1f}" font-family="{COND}" font-size="5" fill="#7d5a3c" '
             f'letter-spacing="0.4" font-style="italic">{_esc(caption)}</text>')

    def finder(r, c):
        return any(r0 <= r < r0 + 7 and c0 <= c < c0 + 7 for r0, c0 in ((0, 0), (0, N - 7), (N - 7, 0)))
    for r in range(N):
        for c in range(N):
            if not M[r][c]:
                continue
            x, y = qx + c * m, qy + r * m
            if finder(r, c):
                b.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{m + 0.05:.2f}" height="{m + 0.05:.2f}" fill="{CARD_INK}"/>')
            else:
                b.append(f'<rect x="{x + m * 0.12:.2f}" y="{y:.2f}" width="{m * 0.76:.2f}" height="{m + 0.05:.2f}" '
                         f'rx="{m * 0.1:.2f}" fill="{CARD_INK}"/>')
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.1f}pt" height="{H:.1f}pt" '
                    f'viewBox="0 0 {W:.1f} {H:.1f}">{"".join(b)}</svg>')
    return dest
