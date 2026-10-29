---
name: transcribe-morning-reports
description: >
  Rebuild an Army company's, battery's or detachment's WWII stations day by day from its morning
  reports (NARA RG 64, online 1940-1944): find the rolls and the unit's pages, locate the station
  changes, read them on the scan, place them (towns, offsets, grid references), and cite every
  page. Use when asked where an Army unit was, to trace a soldier's unit, or to add a unit to
  records/army/.
---

# Transcribing morning reports

Read `guides/MORNING-REPORTS.md` first: what the reports are, how the catalog numbers pages,
and the pitfalls. Formats are in `records/army/README.md`.

## Steps

1. **Rolls.** `python3 tools/morning_reports.py search "<designation as typed>" YYYY-MM`. A known
   date and a serial number (`serial <number>`) is the fastest way in.
2. **The unit's pages.** `unit <roll> '<regex>'`, then `locate '<phrase>|<phrase>' '<regex>'
   YYYY-MM YYYY-MM` for every month (a draft in `sources/drafts/`).
3. **Changes.** `changes sources/drafts/<draft>.csv`: the pages where the station changes.
4. **Read on the scan.** `fetch <roll> <pages>`, then
   `uv run --with pillow python3 tools/crop_pages.py heads <roll> <pages>`. The OCR finds pages;
   it is never the source of a value.
5. **Write the rows.** `records/army/stations.csv`: unit, date, the STATION line exactly as typed,
   place, offset, grid, page (`rg64-<roll>/pNNNN`), source (`mr`), note. Add the unit to
   `units.csv` and new places to `places.csv` (`python3 tools/geocode_places.py`, then check what
   it matched).
6. **Grid references.** `python3 tools/grid_ref.py <grid> <ref>` for each grid until one lands
   within a few km of the named town; record it in `grid_on`. A miss of 10–50 km is usually a
   slipped digit: place the row at the town and say so.
7. **Check.** `uv run tools/check_sources.py` must pass. Add the unit to `records/inventory.yml`.

**Book-type rolls (1940 – mid-1943) and many units**: `morning_reports.py classify` finds the panels and spacers,
`crop_pages.py thumbs` and `panel` read them; to share the reading out, one unit-run per
`.claude/agents/morning-report-reader.md` job, each returning a draft that `morning_reports.py checkdraft` checks
(`guides/MORNING-REPORTS.md`, "Book-type rolls" and "Reading at scale").

## Rules

- Cite every page. Other sources (a battalion journal, a division history, an after action
  report) get an entry in `records/SOURCES.yml` first, and a `source` code that says the
  position is the battalion's or the division's, drawn as assumed.
- The records are the unit's. Don't put a soldier's own path (his name, his serial number, a
  replacement depot or hospital only he passed through) in `records/`: that belongs to whoever
  is researching him, in their own repository.
