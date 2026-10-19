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
         the date / STATION / ORGANIZATION strip of each page, 6 to an image)

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


def heads(roll, pages, per=6, width=1400):
    """Morning-report header strips stacked for quick reading. The 1943-44
    form fills the frame, so the header sits in the top ~16% of the scan."""
    folder = CACHE / "nara" / f"rg64-{roll}"
    for s in range(0, len(pages), per):
        strips = []
        for p in pages[s:s + per]:
            img = Image.open(folder / f"p{int(p):04d}.jpg")
            w, h = img.size
            strip = ImageOps.autocontrast(img.crop((0, int(h * 0.02), w, int(h * 0.17))).convert("L"), cutoff=1)
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
        heads(args[0], args[1:])
    elif cmd == "zoom" and len(args) == 6:
        zoom(args[0], args[1], *map(int, args[2:]))
    else:
        sys.exit(__doc__)
