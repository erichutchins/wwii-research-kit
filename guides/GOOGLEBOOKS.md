# Google Books

Google has digitized many US Army manuals, unit histories and after-action
reports. Full-view (public domain) volumes can be downloaded as PDFs. The
Third Army *After Action Report, Vol. II* (`ee9mAAAAMAAJ`) is the worked case:
it placed the 9th Armored Division and the 128th AAA Gun Battalion at Metz in
1945 (`records/army/`).

`tools/gbooks.py` wraps the Books API v1. It needs `GOOGLE_BOOKS_API_KEY` in
the environment or the git-ignored `.env` in the repo root (the keyless quota is
zero). Never print or commit the key.

## Workflow

1. `python3 tools/gbooks.py search "<keywords>" --full`. Plain keywords work
   better than `inauthor:`: the catalog's author strings are odd (Third Army is
   "United States. Army. Army, 3rd"). Try `intitle:`, a unit number, a place.
2. `meta <id>`: check `viewability` is `ALL_PAGES` and `pdf` is true.
3. `fetch <id>` says what it would download; add `--yes` (after the researcher agrees,
   since PDFs can be 100 MB) to save the PDF and `pNN.jpg` pages to
   `sources/googlebooks/<id>/`. If Google refuses the signed link, the researcher
   downloads it by hand from `books.google.com/books?id=<id>` into that folder.
4. Read the page images. The PDF's OCR text is only a lead for finding pages.
5. Cite by volume id and **PDF page number**, e.g. `(Google Books ee9mAAAAMAAJ, p558)`,
   and say whether the line was read on the scan or from OCR.

The API returns metadata only; it cannot search inside a volume. The scripted
PDF download is usually refused (HTTP 429), so expect to download by hand: get a
fresh signed link from `volumes/<id>` (`accessInfo.pdf.downloadLink`) or use the
Download PDF button, and save it as `sources/googlebooks/<id>/<id>.pdf`.

Find and read pages with `tools/pdf_pages.py` (a PEP 723 script: `uv` supplies
PyMuPDF, no poppler needed):

```bash
tools/pdf_pages.py find sources/googlebooks/<id>/<id>.pdf 'regex'   # PDF pages + context
tools/pdf_pages.py render sources/googlebooks/<id>/<id>.pdf 309     # pages/p309.jpg, read it
```

PDF page numbers differ from the printed ones (DANFS III: PDF 309 = printed 278).
Single OCR pages are also at `books.google.com/books?id=<id>&pg=PA<printed>&output=text`.

## Volumes the records cite

| id | volume | notes |
|---|---|---|
| `ee9mAAAAMAAJ` | Third Army, *After Action Report, 1 Aug 1944 - 9 May 1945*, Vol. II | 772 pp, full view; cited in `records/army/` (`records/SOURCES.yml`) |

A volume read for a lead but not cited by a record belongs in the researcher's own notes, with
its id, the PDF page and whether the line was read on the scan or from OCR text.
