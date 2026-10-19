# Army morning reports: a unit's stations, day by day

How the Army units in `records/army/` were placed, and how to do the same for another
company, battery or detachment. The tool is `tools/morning_reports.py`; the formats are in
`records/army/README.md`.

## What they are

A morning report is one form per company, battery or detachment per day: the date, the
**STATION**, the ORGANIZATION, every soldier whose status changed that day (serial number,
name, grade, what happened), and a RECORD OF EVENTS. The National Archives hold them in Record
Group 64, series [85713825](https://catalog.archives.gov/id/85713825), as microfilm rolls of
1,000–4,000 pages filmed month by month in unit-number order.

- **Online: January 1940 – December 1944.** 1945–46 are on microfilm only, at the National
  Personnel Records Center in St. Louis. For 1945, look for the unit's own histories and
  journals (a division museum, the Army Heritage and Education Center) and its army's after
  action report (Google Books has several in full view: `guides/GOOGLEBOOKS.md`).
- 1940 – mid-1943 reports are book-type (bound, often handwritten, often filmed sideways);
  from mid-1943 they are the printed WD AGO form 1.
- A soldier appears only on a day his status changes, so a missing name proves nothing.

## The catalog

Each roll is a "file unit" with its own catalog ID. The catalog's front end uses
unauthenticated endpoints (full-text search of the OCR, the matching pages of a roll, one page's
OCR), which `morning_reports.py` wraps. Pages are numbered in the order the catalog viewer shows
them (`objectPage`), and that is how rows cite them: `rg64-<roll>/p0960` is
`https://catalog.archives.gov/id/<roll>?objectPage=960`.

The OCR is good enough to **find** pages and never good enough to **read** them: every value is
read from the scan.

## Workflow for one unit

1. **Find the rolls.** Search the OCR for the unit's designation as a clerk would type it
   (`Btry "D" 106th AAA AW Bn`, `Med Det 67th CA`):
   `python3 tools/morning_reports.py search "106th AAA" 1944-08`. Start from one known date (a
   soldier's serial number from his discharge papers works: `serial <number>`).
2. **Find the unit's run of pages in a roll.** Units are filmed in number order, so a unit's
   month is a run of consecutive pages: `unit <roll> 'Btry.{0,4}D.{0,6}106'`.
3. **Every month.** `locate '106th AAA' 'D.{0,8}106' 1944-07 1944-12` walks month by month and
   writes a draft (`sources/drafts/*.csv`) of each month's pages with the OCR'd station.
4. **Find the changes.** `changes sources/drafts/<draft>.csv` lists the pages where the station
   text changes: those are the pages to read.
5. **Read them on the scan.** `fetch <roll> <pages>` downloads them;
   `uv run --with pillow python3 tools/crop_pages.py heads <roll> <pages>` makes strips of each
   page's date / STATION / ORGANIZATION header, six to an image. Record the station **exactly as
   typed** ("Pozzouli"), the page, and the record of events that explains a move.
6. **Place it.** `places.csv` gives each named place coordinates (`tools/geocode_places.py`
   looks new ones up in OpenStreetMap and says what it matched). A station like "10 Mi SE
   Battipaglia" keeps the distance and bearing in `offset`. A grid reference goes in `grid`;
   `tools/grid_ref.py` decodes it, and `site/grids.html` explains which grid a reference is on
   (six grids between Sicily and Bavaria) and checks every one against its named town.

Only **changes** of station are recorded; a unit stays where its last row puts it. Rows from
another source (a battalion's command post from its journal, a division's position) say so in
`source` and are drawn as assumed.

## Pitfalls seen so far

- A typist can keep the old 100 km square letter after crossing into the next square; a
  reference that misses its town by 10–50 km is usually one slipped digit. Place the row at the
  town and say which digit in the note.
- Book-type reports for a detachment can be missing for whole months; the regimental
  headquarters battery's reports may cover them (cite them as such: `source` = `regt`).
- The catalog answers bursts of requests with an error page; the tool backs off and retries.
