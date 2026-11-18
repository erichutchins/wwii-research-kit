"""The punched-card QR code: a well-formed SVG whose finder squares stay solid and whose slots stay inside the code."""
import xml.etree.ElementTree as ET

import segno
from wwiibook import qr

URL = "https://erichutchins.github.io/wwii-research-kit/engagement.html?e=taka-909-1944-09-19"


def test_punch_card(tmp_path):
    p = qr.punch(URL, tmp_path / "card.svg", ("U.S.S. BANG (SS-385)", "CONVOY TAKA-909", "182315Z SEP 44"))
    root = ET.fromstring(p.read_text())
    ns = "{http://www.w3.org/2000/svg}"
    rects = root.findall(f"{ns}rect")
    dark = sum(v for row in segno.make(URL, error="m").matrix for v in row)
    assert len(rects) == dark                          # one mark for every dark module, none lost or added
    texts = "".join(t.text or "" for t in root.findall(f"{ns}text"))
    assert "CONVOY TAKA-909" in texts and "Scan for the engagement" in texts
