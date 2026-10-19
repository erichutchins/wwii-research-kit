---
name: transcribe-patrol-report
description: >
  Transcribe a US submarine's WWII war patrol report (or a ship's war diary) from the National
  Archives scans into records/: find the folder, download and crop the pages, read every position,
  attack and depth entry exactly as typed, speed-check the track, cite every row, and update the
  inventory. Use when asked to add a boat or patrol, transcribe a report, map a submarine, or
  extend the fleet.
---

# Transcribing a war patrol report

The method, with the reasons behind it, is `guides/METHODS.md`; read it first. This is the
checklist.

## 1. Find and fetch

1. `python3 tools/nara.py find "<Name>"` lists the boat's folders (series 305243, M1752), one per
   patrol or date range. Note each folder's catalog ID and dates.
2. Add the boat to `records/inventory.yml` if it isn't there, every patrol with its status and
   folder (`available` once found).
3. `python3 tools/nara.py fetch <id>` downloads the scans to `sources/nara/rg367-<id>/` (never
   committed), then `python3 tools/nara.py index` adds the pages' public URLs to `records/scans.json`.

## 2. Find the pages

`uv run --with pillow python3 tools/crop_pages.py sheet <id>`: contact sheets. The dense grids
are the ship and aircraft contact tables and the attack sheets; the four-column table near the
end is the density layers. Note which pages hold what.

## 3. Read

- `crop_pages.py halves <id> <pages...>` and read each half. Faded cells: `crop_pages.py zoom`.
- Write `records/boats/<hull>-<name>/patrol-N/positions.csv` (columns in `records/README.md`):
  date, time, zone letter, latitude and longitude **exactly as typed**, `?` for an illegible
  character, and the page on every row (`rg367-<id>/pNN`).
- Check each table's header for its zone: tables are often GCT (Z) while the narrative is local.
- Ship contacts are the **target's** position: `on_track=no`.
- Never fix while typing. Corrections come later, in the `*_fix` columns.
- Optional, for a full record like BANG's: `depths.csv` (every dive, depth order and depth
  charge in the narrative, quoted), `layers.csv` (the density-layer table).
- A new boat needs a `ship.yml` (copy one from another boat of the same class).

## 4. Check

1. `uv run tools/check_track.py <name>/<n>` prints every leg. Each `TOO FAST` leg is a typo,
   a zone mix-up or a target position: find which on the scan, put the correction in
   `lat_fix`/`lon_fix`/`date_fix`/`time_fix` with the reason in `fix_note`, or set
   `on_track=no` when it can't be resolved. Repeat until 0 too-fast legs.
2. `uv run tools/check_track.py all --geojson` rebuilds the tracks and `ships.json`.
3. `uv run tools/check_sources.py` must pass (every row cited, inventory matches the folders).
4. Set the patrol's status in `inventory.yml` (`mapped` once it's on the map) and the files done.
5. Open `site/patrols.html?ship=<name>` in light and dark mode: every point should open its page.

## Rules

- Cite every source. A row without a page doesn't go in.
- The narrative, timed to the second, usually beats the attack summary table; record both.
- No rosters or crew lists in `records/`. Names the report carries stay as written.
