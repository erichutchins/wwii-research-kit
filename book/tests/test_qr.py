"""The punched-card QR code: a well-formed SVG, one hole for every dark module outside the finders, the finders as
die-cut windows, and the typed fields clear of the code's quiet zone."""
import re
import xml.etree.ElementTree as ET

import segno
from wwiibook import qr

URL = "https://erichutchins.github.io/wwii-research-kit/engagement.html?e=taka-909-1944-09-19"
NS = "{http://www.w3.org/2000/svg}"


def test_punch_card(tmp_path):
    p = qr.punch(URL, tmp_path / "card.svg", ("U.S.S. BANG\n(SS-385)", "CONVOY\nTAKA-909", "182315Z\nSEP 44"))
    root = ET.fromstring(p.read_text())
    M = segno.make(URL, error="m").matrix
    N = len(M)
    corners = ((0, 0), (0, N - 7), (N - 7, 0))
    outside = sum(1 for r in range(N) for c in range(N)
                  if M[r][c] and not any(r0 <= r < r0 + 7 and c0 <= c < c0 + 7 for r0, c0 in corners))
    holes = [e for e in root.findall(f"{NS}rect") if e.get("fill") == qr.HOLE]
    assert len(holes) == outside + 3                   # every module's hole, and each finder's square core
    windows = [e for e in root.findall(f"{NS}path") if e.get("fill-rule") == "evenodd"]
    assert len(windows) == 3                           # each finder's ring, cut as one
    # the holes lie along the card's long way
    modules = [e for e in holes if e.get("width") != e.get("height")]      # the cores are square; the modules aren't
    assert len(modules) == outside
    assert all(float(e.get("width")) > float(e.get("height")) for e in modules)
    texts = [e for e in root.findall(f"{NS}text")]
    assert [t.text for t in texts[:2]] == ["U.S.S. BANG", "(SS-385)"]
    # no typed line reaches the quiet zone: the code's first hole is at least four modules right of the widest line
    code_x = min(float(e.get("x")) for e in holes)
    widest = max(16 + len(t.text) * float(t.get("font-size")) * 0.6 for t in texts if t.get("font-family", "").startswith("Courier"))
    assert code_x - widest >= 4 * 2.6
    W, H = (float(re.match(r"[\d.]+", root.get(k)).group()) for k in ("width", "height"))
    assert 1.3 < W / H < 1.7                           # the squarer card
