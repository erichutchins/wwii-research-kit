"""Make readable crops of scanned report pages for transcription.

A full scan (about 2460 x 3217 px) is too dense to read reliably in one view;
the transcription workflow reads pages as overlapping top/bottom halves, plus
contact sheets to find which pages hold which tables.

  uv run --with pillow python3 tools/crop_pages.py halves 74802784 08 09 10
      -> /tmp/bang/74802784_p08_a.jpg (top half), _b.jpg (bottom half), ...
  uv run --with pillow python3 tools/crop_pages.py sheet 74802784
      -> /tmp/bang/sheet_74802784_1.jpg ... (24 labelled thumbnails per sheet)
  uv run --with pillow python3 tools/crop_pages.py zoom 74802868 11 1550 700 700 260
      -> /tmp/bang/74802868_p11_zoom.jpg (x y w h in full-scan pixels, contrast-stretched)

  uv run --with pillow python3 tools/crop_pages.py heads 578447414 918 953 960
      -> /tmp/bang/heads_578447414_1.jpg ... (Army morning reports, rg64-<roll>:
         the date / STATION / ORGANIZATION strip of each page, 6 to an image; pages as
         "918 953" or "918-930,953"; add `tall` for the book-type forms of 1940 - mid-1943,
         whose ORGANIZATION line sits lower)

  uv run --with pillow python3 tools/crop_pages.py thumbs 427179736 700-760
      -> /tmp/bang/thumbs_427179736_1.jpg ... (Army morning reports: 32 labelled page
         thumbnails per sheet, to tell fronts, sideways panels and backs apart at a glance)
  uv run --with pillow python3 tools/crop_pages.py panel 427179736 709 [ccw]
      -> /tmp/bang/panel_427179736_p0709_a.jpg, _b.jpg (a sideways "Station and record of
         events" panel turned upright (clockwise by default) and cut into two readable halves)

Output goes to $CROP_DIR (default /tmp/bang).
"""
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

from records import CACHE  # noqa: E402
OUT = Path(os.environ.get("CROP_DIR", "/tmp/bang"))


def scan(na_id, page):
    return Image.open(CACHE / "nara" / f"rg367-{na_id}" / f"p{int(page):02d}.jpg")


def heads(roll, pages, per=6, width=1400, bottom=0.17):
    """Morning-report header strips stacked for quick reading. The 1943-44
    form fills the frame, so the header sits in the top ~16% of the scan."""
    folder = CACHE / "nara" / f"rg64-{roll}"
    for s in range(0, len(pages), per):
        strips = []
        for p in pages[s:s + per]:
            img = Image.open(folder / f"p{int(p):04d}.jpg")
            w, h = img.size
            strip = ImageOps.autocontrast(img.crop((0, int(h * 0.02), w, int(h * bottom))).convert("L"), cutoff=1)
            strips.append((p, fit(strip, width)))
        canvas = Image.new("L", (width, sum(st.height + 26 for _, st in strips)), 255)
        draw = ImageDraw.Draw(canvas)
        y = 0
        for p, st in strips:
            draw.text((6, y + 6), f"p{int(p):04d}", fill=0)
            canvas.paste(st, (0, y + 26))
            y += st.height + 26
        path = OUT / f"heads_{roll}_{s // per + 1}.jpg"
        canvas.save(path, quality=88)
        print(path)


def rg64_pages(roll, spec):
    out = []
    for part in spec:
        for piece in str(part).split(","):
            a, _, b = piece.partition("-")
            out += range(int(a), int(b or a) + 1)
    folder = CACHE / "nara" / f"rg64-{roll}"
    have = [p for p in out if (folder / f"p{p:04d}.jpg").exists()]
    if len(have) < len(out):
        print(f"not fetched (morning_reports.py fetch {roll} ...): "
              f"{','.join(str(p) for p in out if p not in have)}", file=sys.stderr)
    return folder, have


def thumbs(roll, spec, per=32, cols=8, thumb=(240, 320)):
    folder, pages = rg64_pages(roll, spec)
    for s in range(0, len(pages), per):
        batch = pages[s:s + per]
        rows = (len(batch) + cols - 1) // cols
        canvas = Image.new("L", (cols * (thumb[0] + 6), rows * (thumb[1] + 24)), 255)
        draw = ImageDraw.Draw(canvas)
        for i, p in enumerate(batch):
            t = ImageOps.autocontrast(Image.open(folder / f"p{p:04d}.jpg").convert("L"), cutoff=1)
            t.thumbnail(thumb)
            x, y = (i % cols) * (thumb[0] + 6), (i // cols) * (thumb[1] + 24)
            canvas.paste(t, (x, y + 20))
            draw.text((x + 4, y + 4), f"p{p:04d}", fill=0)
        path = OUT / f"thumbs_{roll}_{s // per + 1}.jpg"
        canvas.save(path, quality=85)
        print(path)


def panel(roll, page, turn="cw", width=1700):
    """The book-type reports' "Station and record of events" panel is filmed sideways:
    turn the page upright and cut it into overlapping halves along the lines."""
    folder, pages = rg64_pages(roll, [page])
    if not pages:
        return
    img = Image.open(folder / f"p{pages[0]:04d}.jpg").convert("L")
    img = ImageOps.autocontrast(img.rotate(-90 if turn == "cw" else 90, expand=True), cutoff=1)
    w, h = img.size
    for tag, x0 in (("a", 0), ("b", int(w * 0.40))):
        path = OUT / f"panel_{roll}_p{pages[0]:04d}_{tag}.jpg"
        fit(img.crop((x0, 0, min(w, x0 + int(w * 0.60)), h)), width).save(path, quality=90)
        print(path)


def fit(img, width):
    return img.resize((width, round(img.height * width / img.width)), Image.LANCZOS)


def halves(na_id, pages):
    for p in pages:
        img = scan(na_id, p)
        w, h = img.size
        # overlapping halves so no line is cut in two
        for tag, top in (("a", int(h * 0.05)), ("b", int(h * 0.47))):
            crop = img.crop((0, top, w, min(h, top + int(h * 0.53))))
            path = OUT / f"{na_id}_p{int(p):02d}_{tag}.jpg"
            fit(crop, 1800).save(path, quality=88)
            print(path)


def sheet(na_id, per=24, cols=8, thumb=(330, 430)):
    pages = sorted((CACHE / "nara" / f"rg367-{na_id}").glob("p*.jpg"))
    for s in range(0, len(pages), per):
        batch = pages[s:s + per]
        rows = (len(batch) + cols - 1) // cols
        canvas = Image.new("RGB", (cols * (thumb[0] + 6), rows * (thumb[1] + 30)), "white")
        draw = ImageDraw.Draw(canvas)
        for i, p in enumerate(batch):
            t = Image.open(p)
            t.thumbnail(thumb)
            x, y = (i % cols) * (thumb[0] + 6), (i // cols) * (thumb[1] + 30)
            canvas.paste(t, (x, y + 24))
            draw.text((x + 4, y + 4), p.stem, fill="black")
        path = OUT / f"sheet_{na_id}_{s // per + 1}.jpg"
        canvas.save(path, quality=85)
        print(path)


def zoom(na_id, page, x, y, w, h):
    crop = ImageOps.autocontrast(scan(na_id, page).crop((x, y, x + w, y + h)).convert("L"), cutoff=2)
    path = OUT / f"{na_id}_p{int(page):02d}_zoom.jpg"
    fit(crop, max(1400, w)).save(path, quality=90)
    print(path)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    cmd, args = (sys.argv[1], sys.argv[2:]) if len(sys.argv) > 2 else ("", [])
    if cmd == "halves":
        halves(args[0], args[1:])
    elif cmd == "sheet":
        sheet(args[0])
    elif cmd == "heads":
        tall = "tall" in args[1:]
        _, pages = rg64_pages(args[0], [a for a in args[1:] if a != "tall"])
        heads(args[0], pages, per=4 if tall else 6, bottom=0.32 if tall else 0.17)
    elif cmd == "thumbs" and len(args) >= 2:
        thumbs(args[0], args[1:])
    elif cmd == "panel" and len(args) >= 2:
        panel(args[0], args[1], args[2] if len(args) > 2 else "cw")
    elif cmd == "zoom" and len(args) == 6:
        zoom(args[0], args[1], *map(int, args[2:]))
    else:
        sys.exit(__doc__)
