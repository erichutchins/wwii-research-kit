# /// script
# requires-python = ">=3.10,<3.14"
# dependencies = ["numpy", "scipy", "pillow", "scikit-image", "pyyaml"]
# ///
"""Which base map each of the 415 daily situation maps (SOURCES.yml `loc-12ag`) is printed on: the `bases` step of
guides/SITUATION-MAPS.md (section 5, item 1). Image work only; nothing here reads a map's content.

    uv run tools/sitmap_bases.py fetch                    # every day's overview (12.5 %, ~150 KB) -> sources/maps/loc/overviews/<item>.jpg
    uv run tools/sitmap_bases.py group [--threshold T] [--write]   # group the days by base -> sources/fronts-work/bases/;
                                                                   #   --write: each day's base into sitmaps.csv
    uv run tools/sitmap_bases.py check B12 [--towns 12ag-1945-03-07]   # does that day's set of towns register on the base's first day?

`fetch` goes through loc_sitmaps.get (a second between requests, this kit named), one process, skipping files already
here, progress every 25. `group` loads each overview as greyscale and resizes it to a common 256 x 256 canvas (aspect
ratio ignored, so landscape, portrait and the double-wide sheet all compare; a trim of a few per cent is then a small
shift, which the matching allows for), high-passes it (a difference of Gaussians, so the coast, rivers, roads and
graticule dominate the paper tone and the broad blotches of overprint) and compares two images by phase correlation:
the height of the correlation peak within a shift of 5 % of the width. Days are taken in date order; a day joins the
base of the earlier day it matches best (any earlier day stands for its group: the overprint drifts, so the first day of
a group is a poor yardstick for its last) if that score reaches the threshold, else it
starts a new base, so a base can recur after a gap. The threshold is chosen from the distribution of day-to-previous-day
scores (the middle of the widest empty stretch among the low scores) unless given. Output: similarity.csv,
bases-draft.csv, contact-Bnn.jpg (first, middle, last day of each group) and report.md in sources/fronts-work/bases/;
with --write, the `base` column of records/fronts/sitmaps.csv. What each base is, once looked at, is hand-written in
records/fronts/bases.yml. `check` fetches a base's first day's scan (if it isn't cached) and runs trace_front.register:
a day's towns, read by eye, matched on it and checked against one affine transform. 19 or 20 of 20 agreeing is the same
plate, however the sheet is trimmed or placed (6 September 1944, 7 March and 21 March 1945 are one plate, offset by up
to 1,760 px); 0 of 20 is another sheet, whose towns must be read by eye before a day of it is traced. Nothing is written.
"""
import argparse
import csv
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).parent))
import loc_sitmaps

KIT = loc_sitmaps.KIT
OV = loc_sitmaps.CACHE / "overviews"
OUT = KIT / "sources" / "fronts-work" / "bases"
N = 256            # the common canvas
SHIFT = 0.05       # allowed shift, fraction of the width


def cmd_fetch(a):
    rows = loc_sitmaps.read_catalogue()
    OV.mkdir(parents=True, exist_ok=True)
    failed = []
    for i, r in enumerate(rows, 1):
        dest = OV / f"{r['item']}.jpg"
        if dest.exists() and dest.stat().st_size > 1000:
            continue
        try:
            body, _ = loc_sitmaps.get(f"{loc_sitmaps.IIIF.format(item=r['item'])}/full/pct:12.5/0/default.jpg")
            if body[:2] != b"\xff\xd8":
                raise ValueError("not a JPEG (bot check?)")
            dest.write_bytes(body)
        except Exception as e:
            failed.append(f"{r['item']} {r['date']}: {e}")
            print("   FAILED", failed[-1])
            if len(failed) >= 5:
                sys.exit("five failures; stopping")
        if i % 25 == 0:
            print(f"   {i}/{len(rows)} ({r['date']})", flush=True)
    print(f"done; {len(failed)} failed")
    for f in failed:
        print("  ", f)


def prep(path):
    im = Image.open(path).convert("L")
    size = im.size
    a = np.asarray(im.resize((N, N), Image.Resampling.LANCZOS), dtype=np.float64)
    hp = ndimage.gaussian_filter(a, 1.0) - ndimage.gaussian_filter(a, 5.0)
    hp = np.clip(hp, -3 * hp.std(), 3 * hp.std())   # a few dark blots must not dominate
    hp = (hp - hp.mean()) / (hp.std() + 1e-9)
    hp *= np.outer(np.hanning(N), np.hanning(N))
    return size, hp


def score(F1, F2):
    """Phase correlation: the peak of the whitened cross-power spectrum within the allowed shift."""
    C = F1 * np.conj(F2)
    C /= np.abs(C) + 1e-9
    c = np.fft.fftshift(np.real(np.fft.ifft2(C)))
    m = int(SHIFT * N)
    cc = N // 2
    box = c[cc - m:cc + m + 1, cc - m:cc + m + 1]
    # the peak's neighbourhood (3 x 3), so a sub-pixel peak is not split between cells
    return float(ndimage.uniform_filter(box, 3, mode="constant").max() * 9)


def gap_split(x, below=0.6):
    """The midpoint of the widest empty stretch among the scores under `below`: the break between the days that
    plainly do not match their neighbour and the rest (Otsu's split landed inside the matching mode, at 0.59)."""
    x = np.sort(np.asarray(x))
    x = x[x < below]
    i = int(np.argmax(np.diff(x)))
    return float((x[i] + x[i + 1]) / 2)


def cmd_group(a):
    rows = sorted(loc_sitmaps.read_catalogue(), key=lambda r: (r["date"], r["item"]))
    OUT.mkdir(parents=True, exist_ok=True)
    missing, days, F = [], [], {}
    for r in rows:
        p = OV / f"{r['item']}.jpg"
        if not p.exists():
            missing.append(r)
            continue
        _, hp = prep(p)
        F[r["item"]] = np.fft.fft2(hp)
        days.append(r)
    prev = [None] + [score(F[days[i]["item"]], F[days[i - 1]["item"]]) for i in range(1, len(days))]
    ps = np.array(prev[1:])
    print("day-to-previous-day score distribution (percentiles 0 5 10 25 50 75 90 100):")
    print("  ", np.round(np.percentile(ps, [0, 5, 10, 25, 50, 75, 90, 100]), 3))
    hist, edges = np.histogram(ps, bins=20)
    for h, e in zip(hist, edges):
        print(f"   {e:6.3f} {'#' * int(h)}")
    thr = a.threshold if a.threshold is not None else gap_split(ps)
    print(f"threshold {thr:.3f}", "(given)" if a.threshold is not None else "(widest gap in the low scores)")
    reps, base_of, best_sc, second, seen = [], {}, {}, {}, []   # reps: [(id, first item)]
    for d in days:
        it = d["item"]
        by = {}   # best score to any earlier day of each base
        for ps_it in seen:
            sc1 = score(F[it], F[ps_it])
            b = base_of[ps_it]
            if sc1 > by.get(b, 0):
                by[b] = sc1
        sc = sorted(((v, b) for b, v in by.items()), reverse=True)
        if sc and sc[0][0] >= thr:
            base_of[it], best_sc[it] = sc[0][1], sc[0][0]
            second[it] = sc[1] if len(sc) > 1 else (0, "")
        else:
            bid = f"B{len(reps) + 1:02d}"
            reps.append((bid, it))
            base_of[it], best_sc[it] = bid, sc[0][0] if sc else 1.0
            second[it] = sc[0] if sc else (0, "")
        seen.append(it)
    # score of each day to its own group's representative, and doubtful days
    own = {}
    for d in days:
        it = d["item"]
        rep = dict(reps)[base_of[it]]
        own[it] = 1.0 if it == rep else score(F[it], F[rep])
    with open(OUT / "similarity.csv", "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["item", "date", "prev_score", "best_base", "best_score"])
        for i, d in enumerate(days):
            w.writerow([d["item"], d["date"], "" if prev[i] is None else f"{prev[i]:.3f}", base_of[d["item"]], f"{best_sc[d['item']]:.3f}"])
    with open(OUT / "bases-draft.csv", "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["item", "date", "base", "score", "width", "height"])
        for d in days:
            w.writerow([d["item"], d["date"], base_of[d["item"]], f"{own[d['item']]:.3f}", d["width"], d["height"]])
    # contact sheets and report
    band = 0.15 * thr
    lines = ["# Bases draft", "", f"{len(days)} days grouped, {len(missing)} without an overview.", "",
             f"Threshold {thr:.3f} ({'given' if a.threshold is not None else 'widest gap among the low day-to-previous-day scores'}).",
             "Day-to-previous percentiles (0 5 10 25 50 75 90 100): " + ", ".join(f"{v:.3f}" for v in np.percentile(ps, [0, 5, 10, 25, 50, 75, 90, 100])), "",
             "| id | first | last | days | typical scan size | days below threshold to the group's first day |", "|---|---|---|---|---|---|"]
    for bid, _rep in reps:
        g = [d for d in days if base_of[d["item"]] == bid]
        sizes: dict[tuple, int] = {}
        for d in g:
            k = (round(int(d["width"]), -2), round(int(d["height"]), -2)) if d["width"] else ("?", "?")
            sizes[k] = sizes.get(k, 0) + 1
        typ = max(sizes, key=lambda k: sizes[k])
        low = sum(1 for d in g if own[d["item"]] < thr)
        lines.append(f"| {bid} | {g[0]['date']} | {g[-1]['date']} | {len(g)} | {typ[0]} x {typ[1]} (n={sizes[typ]}) | {low} |")
        picks = [g[0], g[len(g) // 2], g[-1]]
        tiles = []
        for d in picks:
            im = Image.open(OV / f"{d['item']}.jpg").convert("RGB")
            im.thumbnail((620, 620))
            t = Image.new("RGB", (620, 650), "white")
            t.paste(im, (0, 30))
            ImageDraw.Draw(t).text((4, 8), f"{bid}  {d['date']}  {d['item']}", fill="black")
            tiles.append(t)
        sheet = Image.new("RGB", (620 * 3, 650), "white")
        for k, t in enumerate(tiles):
            sheet.paste(t, (620 * k, 0))
        sheet.save(OUT / f"contact-{bid}.jpg", quality=80)
    lines += ["", "## Doubtful assignments", "", f"Best score within {band:.3f} of the threshold, or a second base within 15 % of the best.", "",
              "| date | item | base | score to first day | best score | runner-up |", "|---|---|---|---|---|---|"]
    for d in days:
        it = d["item"]
        s2, b2 = second[it]
        near = abs(best_sc[it] - thr) < band
        two = b2 and b2 != base_of[it] and s2 >= thr and s2 > 0.85 * best_sc[it]
        if near or two:
            lines.append(f"| {d['date']} | {it} | {base_of[it]} | {own[it]:.3f} | {best_sc[it]:.3f} | {b2} {s2:.3f} |")
    lines += ["", "## Overviews not fetched", ""] + ([f"- {r['item']} {r['date']}" for r in missing] or ["none"])
    (OUT / "report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines[:5 + 2 + len(reps)]))
    if a.write:
        for r in rows:
            r["base"] = base_of.get(r["item"], "")
        loc_sitmaps.write_catalogue(rows)
        print(f"wrote the base of each day into {loc_sitmaps.rel(loc_sitmaps.CATALOGUE)}")


def cmd_check(a):
    import trace_front
    rows = [r for r in loc_sitmaps.read_catalogue() if r.get("base") == a.base]
    if not rows:
        sys.exit(f"no day of {a.base} in the catalogue: group --write first")
    first = min(rows, key=lambda r: r["date"])
    src = trace_front.sitmap(a.towns)
    if not (trace_front.REC / f"{a.towns}-gcps.csv").exists():
        sys.exit(f"{a.towns} has no towns (records/fronts/{a.towns}-gcps.csv)")
    for item in (src.item, first["item"]):
        loc_sitmaps.fetch_item(item)
    other = np.asarray(Image.open(loc_sitmaps.scan_path(first["item"])).convert("L"))
    towns, _found, ok, res, _, (dx, dy) = trace_front.register(src, other)
    n = int(ok.sum())
    med = f"{np.median(res[ok]):.1f}" if n else "-"
    print(f"{a.towns}'s towns on {a.base}'s first day, 12ag-{first['date']} ({first['item']}): {n} of {len(towns)} agree, "
          f"median {med} px, the sheets offset {dx:+d}, {dy:+d} px")
    for t, g, e in zip(towns, ok, res):
        if not g:
            print(f"   {t['town']}: {e:.0f} px off the transform")
    print("the same plate: this day's towns serve the base" if n >= 12 else
          "not this plate: the base's towns must be read by eye (the skill, step 2)")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fetch").set_defaults(fn=cmd_fetch)
    g = sub.add_parser("group")
    g.add_argument("--threshold", type=float)
    g.add_argument("--write", action="store_true", help="each day's base into records/fronts/sitmaps.csv")
    g.set_defaults(fn=cmd_group)
    c = sub.add_parser("check")
    c.add_argument("base", help="B01 ... as sitmaps.csv has it")
    c.add_argument("--towns", default="12ag-1945-03-07", help="the day whose towns, read by eye, to match")
    c.set_defaults(fn=cmd_check)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
