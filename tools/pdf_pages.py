#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pymupdf"]
# ///
"""Find and render pages of a downloaded PDF (Google Books volumes etc.).

No poppler needed; uv supplies PyMuPDF.

  tools/pdf_pages.py find <pdf> <regex> [--context N]   PDF page numbers whose text matches
  tools/pdf_pages.py text <pdf> <page> [<page>...]      the PDF's own OCR text for pages (1-based)
  tools/pdf_pages.py render <pdf> <page> [<page>...]    pNNN.jpg beside the PDF, 130 dpi, in pages/

Page numbers are the PDF's, not the book's printed numbers. The text layer is
Google's OCR: use it to find pages, then read the rendered image.
"""
import re
import sys
from pathlib import Path

import pymupdf as fitz


def main():
    cmd, args = (sys.argv[1], sys.argv[2:]) if len(sys.argv) > 2 else ("", [])
    if cmd == "find" and len(args) >= 2:
        ctx = int(args[args.index("--context") + 1]) if "--context" in args else 60
        pat = re.compile(args[1], re.I)
        for i, page in enumerate(fitz.open(args[0]), 1):
            text = re.sub(r"\s+", " ", page.get_text())
            for m in pat.finditer(text):
                print(f"p{i}\t…{text[max(0, m.start() - ctx):m.end() + ctx]}…")
    elif cmd == "text" and len(args) >= 2:
        doc = fitz.open(args[0])
        for n in args[1:]:
            print(f"--- p{n} ---\n{doc[int(n) - 1].get_text()}")
    elif cmd == "render" and len(args) >= 2:
        pdf = Path(args[0])
        out = pdf.parent / "pages"
        out.mkdir(exist_ok=True)
        doc = fitz.open(pdf)
        for n in args[1:]:
            path = out / f"p{int(n):03d}.jpg"
            doc[int(n) - 1].get_pixmap(dpi=130).save(path)
            print(path)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
