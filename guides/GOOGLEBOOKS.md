# Google Books

Google has digitized many US Army manuals, unit histories and after-action
reports. Full-view (public domain) volumes can be downloaded as PDFs. The
Third Army *After Action Report, Vol. II* (`ee9mAAAAMAAJ`) placed the 9th
Armored and the 128th AAA at Metz in 1945 (`records/army/`).

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

## Volumes used

| id | volume | notes |
|---|---|---|
| `ee9mAAAAMAAJ` | Third Army, After Action Report, 1 Aug 1944 - 9 May 1945, Vol. II | 772 pp, full view; PDF in `sources/googlebooks/` (older flat layout) |
| `2bCT3veahzQC` | DANFS vol. III (G-K), 912 pp | Haynsworth entry on PDF p309 (printed 278), **read on the scan**: commissioned 22 Jun 1944 (Comdr Robert Brodie Jr.), "crashed by a kamikaze 6 April", repairs at Mare Island, three battle stars. No casualty count and no names of the dead. |
| `mxQzAAAAMAAJ` | DANFS N-S, p. 545 (same page in `CScXx-a_0vwC`, `X5GnoNV8TqMC`) | **Solar (DE-221)**, **read on the scan** (PDF `sources/googlebooks/mxQzAAAAMAAJ/`, PDF p574): commissioned 15 Feb 1944 (Lt. Comdr. Hadlai A. Hull); convoys to Casablanca (Apr-May 1944) and three to the Mediterranean; COTCLANT from 16 Dec 1944; UGS 72 "lost two tankers at the entrance to the Straits of Gibraltar"; GUS 74; GUS 86 and V-E news; submarine training out of New London; explosion 30 Apr 1946 at Earle N.J. **"claimed the lives of 165 sailors and injured 65 others"** (the scan prints 165 and 65, so it is not an OCR slip; disagrees with the "seven killed" in `KAY-MAHONEY.md`: unresolved, DANFS may itself be wrong); sunk at sea 9 Jun 1946. |
| `TNBT-jpBl1QC` | *Building the Navy's Bases*, vol. 2, p. 291 (OCR text) | **20th NCB at Woodlark and Kiriwina**: at the 30 Jun 1943 Woodlark landing a naval base unit "to which about 500 men of the 20th Construction Battalion were attached" did housing, roads, a 30-mile road net by October, water system, PT pier; in Sep 1943 "12 officers and 306 men of the 20th" went to Kiriwina to build two taxiways, back at Woodlark 28 Oct. This is the Forward Echelon James was *not* on. |
| `Pjl440Jq0tQC` | *Marines in the Central Solomons*, pp. 28, 45 (OCR) | New Georgia order of battle: "most of the 24th and part of the 20th Naval Construction Battalions" in the Western Landing Force; "parts of the 20th and 24th" in the Eastern Landing Force. At Wickham Anchorage (Vangunu, Oloana Bay, 30 Jun 1943), Lt. Col. Brown's force had "half of the 20th NCB" with his 2d Bn, 103d Infantry. |
| `i_hpqxraveMC` | *Cartwheel*, p. 81 (OCR) | **Segi Point**: airfield work began 30 Jun 1943; "the Seabees of the 20th Naval Construction Battalion had the strip ready for limited operations as a fighter staging field by 11 July", working under floodlights at night. |

## Leads found 2026-10-14 (from API snippets only; not downloaded or read)

| id | volume | for |
|---|---|---|
| `TNBT-jpBl1QC` | *Building the Navy's Bases in World War II* (1947), vol. 2 (also `cI7rEUDQ6lEC`) | The 20th NCB: snippets mention "about 500 men of the 20th Construction Battalion" in a naval base unit, and the 20th at Rendova building a PT base |
| `i_hpqxraveMC` | *Cartwheel* (Army Green Book, 1959) | 20th NCB had the Wickham Anchorage strip ready |
| `Pjl440Jq0tQC` | *Marines in the Central Solomons* (1952) | 20th NCB index entries (pp. 28-29, 45) |
| `mxQzAAAAMAAJ` | DANFS N-S (1959; also `CScXx-a_0vwC`, `X5GnoNV8TqMC`) | USS Solar (DE-221) entry: check the convoy names |
| `ZPqXdSbi9JwC` | *All Hands*, 1946 | Solar explosion 30 Apr 1946 (court of inquiry, findings not made public) |
| `E_LmA-j53eEC` | *Investigation of the National Defense Program* | lists "Solar (DE221) - Explosion 4-30-46, Rear Adm. Foster, 14 May 1946": a named investigation report to look for |
| `2bCT3veahzQC` | DANFS H-K (1968) | the Haynsworth entry; casualty count |
| `Y-ZxfseVa-YC` | DANFS A-B (1991) | Essex entry: "Kamikaze attacks on 6 and 7 April damaged Haynsworth and Hancock" |

Not found: Irons' *Phalanx Against the Divine Wind* (in copyright), 9th/8th/4th
Armored Division unit histories, the MOS list of 1945 (TM 12-427).

## *Building the Navy's Bases*, vol. 2 (`TNBT-jpBl1QC`, PDF in `sources/googlebooks/TNBT-jpBl1QC/`)

Whole-book search for the 20th NCB (PDF pages; index entries at p510 point to book pp. 222, 279, 291, 418):
p251 (Nouméa, 21 Oct 1942), p270 (**the 20th landed at Viru Harbor** to build a PT base; the same
sentence says the **47th** Bn landed at Segi Point, whereas *Cartwheel* p81 credits the 20th's Seabees with
the Segi strip: sources disagree), p292-293 (Banika sections), p295-296 (Viru: first echelon tried to enter
the harbor 30 Jun, was driven off, landed 2 Jul; second echelon 1 Jul; third 3 Jul; built roads and a
sector of the defense line; PT base plan abandoned; stayed until October), p297 (Bau Island PT base from
Oct 1943, Doke Doke boat pool, Nov 1943 docking at Munda), p310 and p322 (Woodlark, Kiriwina).
