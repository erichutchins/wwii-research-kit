# /// script
# requires-python = ">=3.10,<3.14"
# dependencies = ["numpy", "scipy", "pillow", "scikit-image"]
# ///
"""Read the landing-place arrows of OSS Map No. 967 (1942) into records/roads/oss967-landings.csv.

OSS Map No. 967, "Algeria and Tunisia: Principal Highways and Landing Places", 22 August 1942
(SOURCES.yml `oss-967`). Its legend has two arrows: a solid one, "Minor Beaches and Landing Places",
and a hollow one, "Extensive Beaches". Each points at the coast; the place is the arrow's point.

    uv run tools/oss967_landings.py                 # records/roads/oss967-landings.csv
    uv run tools/oss967_landings.py --overlay /tmp/l.jpg   # every arrow ringed on the scan, to check

How it works: the scan is fitted to its towns exactly as tools/trace_roads.py does (the same
records/roads/oss967-gcps.csv). An arrow is drawn apart from the roads and the coast, so it is a
separate patch of ink: one 70-260 px long and at least 2.2 times as long as it is wide, with one end
clearly wider than the other (the head). The point of the head is the place. A hollow arrow's tail is
two strokes, so its tail is wider than a solid arrow's (over 16 px). Dash-dot frontiers, two title
letters, the legend's own arrows and an island's outline pass the same test; they are dropped by the
boxes in NOT_ARROWS. Arrows that touch each other merge into one patch and fail the test; those were
read by eye on the full scan and are listed in BY_EYE. Every arrow was checked on the scan (28 Oct 2026).

The map is dated three months before the Torch landings (8 Nov 1942): these are the beaches as the
OSS saw them, not where the landings came.
"""
import argparse
import csv
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

sys.path.insert(0, str(Path(__file__).resolve().parent))
from trace_roads import FRAME, REC, SCAN, Fit, km  # noqa: E402

Image.MAX_IMAGE_PIXELS = None

# (x0, y0, x1, y1) on the full scan: marks that pass the arrow test but are not landing places
NOT_ARROWS = [
    ((1150, 642, 3800, 1900), "the title lettering"),
    ((1400, 3100, 2100, 5500), "the Algeria-Morocco frontier, dash-dot"),
    ((7600, 1950, 8350, 4400), "the Algeria-Tunisia frontier, dash-dot"),
    ((10450, 4500, 10600, 4900), "the Tunisia-Libya frontier, dash-dot"),
    ((7500, 5300, 8000, 5700), "the legend's own arrows"),
    ((10200, 3040, 10320, 3120), "Kerkennah's outline"),
]
# (x, y, kind, note): arrows touching another, which the test can't separate, read on the scan
BY_EYE = [
    (2628, 2342, "extensive", "east of Arzew, the first of three; touches the next"),
    (7990, 1490, "extensive", "between Bône and La Calle; touches its neighbours"),
    (10575, 4360, "stretch_end", "the south end of \"SANDY COASTLINE WITH EXTENSIVE BEACHES\", at Ben Gardane"),
]
# the banner's north end is drawn with the same hollow arrow; it marks a stretch, not one place
STRETCH_ENDS = [((9780, 1740, 9850, 1790), "the north end of \"SANDY COASTLINE WITH EXTENSIVE BEACHES\", Gulf of Hammamet")]


def inside(box, x, y):
    return box[0] <= x <= box[2] and box[1] <= y <= box[3]


def detect(g):
    ink = g < 150
    lab, _ = ndi.label(ink, structure=np.ones((3, 3)))
    found = []
    for i, sl in enumerate(ndi.find_objects(lab), 1):
        if sl is None:
            continue
        h, w = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        if not 70 <= max(h, w) <= 260:
            continue
        m = ndi.binary_fill_holes(lab[sl] == i)
        ys, xs = np.nonzero(m)
        ys, xs = ys + sl[0].start, xs + sl[1].start
        cx, cy = xs.mean(), ys.mean()
        if not (FRAME[0] + 30 < cx < FRAME[2] - 30 and FRAME[1] + 30 < cy < FRAME[3] - 30):
            continue
        P = np.stack([xs - cx, ys - cy], 1).astype(float)
        ev, evec = np.linalg.eigh(np.cov(P.T))
        ax = evec[:, 1]
        length, width = 4 * np.sqrt(ev[1]), 4 * np.sqrt(ev[0])
        if length < 80 or length / max(width, 1) < 2.2:
            continue
        t, s = P @ ax, P @ np.array([-ax[1], ax[0]])
        lo, hi = np.ptp(s[t < np.percentile(t, 30)]), np.ptp(s[t > np.percentile(t, 70)])
        if max(lo, hi) < 1.25 * min(lo, hi):
            continue  # no head
        head_hi = hi > lo
        k = np.argmax(t) if head_hi else np.argmin(t)
        tail = t < np.percentile(t, 15) if head_hi else t > np.percentile(t, 85)
        found.append((int(xs[k]), int(ys[k]), "extensive" if np.ptp(s[tail]) > 16 else "minor"))
    return found


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--overlay")
    a = ap.parse_args()
    fit = Fit(list(csv.DictReader(open(REC / "roads" / "oss967-gcps.csv"))))
    _, loo = fit.residuals_km()
    fit_km = round(float(np.sqrt((loo ** 2).mean())), 1)

    g = np.asarray(Image.open(SCAN).convert("L"))
    rows = []
    for x, y, kind in detect(g):
        if any(inside(b, x, y) for b, _ in NOT_ARROWS):
            continue
        note = next((n for b, n in STRETCH_ENDS if inside(b, x, y)), "")
        rows.append((x, y, "stretch_end" if note else kind, "detected", note))
    rows += [(x, y, kind, "by eye", note) for x, y, kind, note in BY_EYE]
    rows.sort(key=lambda r: (r[0] > 9700 and r[1] > 1700, r[1] if r[0] > 9700 and r[1] > 1700 else r[0]))  # west to east, then down the east coast

    towns = list(csv.DictReader(open(REC / "roads" / "oss967-gcps.csv")))
    tll = np.array([[float(t["lon"]), float(t["lat"])] for t in towns])
    out = REC / "roads" / "oss967-landings.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "kind", "x", "y", "read", "lat", "lon", "fit_km", "near", "source", "note"])
        for n, (x, y, kind, read, note) in enumerate(rows, 1):
            lon, lat = fit.to_ll([x, y])[0]
            d = km(np.repeat([[lon, lat]], len(tll), 0), tll)
            j = int(d.argmin())
            w.writerow([f"L{n:03d}", kind, x, y, read, f"{lat:.4f}", f"{lon:.4f}", fit_km,
                        f"{d[j]:.0f} km from {towns[j]['town']}", "oss-967", note])
    kinds = {k: sum(r[2] == k for r in rows) for k in ("minor", "extensive", "stretch_end")}
    print(f"{len(rows)} arrows ({kinds}) -> {out.relative_to(REC.parent)}; fit {fit_km} km")

    if a.overlay:
        im = Image.open(SCAN).convert("RGB")
        d = ImageDraw.Draw(im)
        for x, y, kind, read, _ in rows:
            c = {"minor": (220, 0, 0), "extensive": (0, 100, 255), "stretch_end": (0, 160, 0)}[kind]
            d.ellipse([x - 20, y - 20, x + 20, y + 20], outline=c, width=6)
        for b, _ in NOT_ARROWS:
            d.rectangle(b, outline=(150, 150, 150), width=4)
        im.resize((im.width // 4, im.height // 4)).save(a.overlay)


if __name__ == "__main__":
    main()
