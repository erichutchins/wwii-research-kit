# Expanding to the Pacific submarine fleet

Plan for repeating the BANG work ([METHODS.md](METHODS.md)) for other US
submarines of the Pacific war.

## How big is it

- Series 305243 (microfilm M1752, 82 reels) holds war patrol reports for
  every US submarine. US submarines made roughly 1,500 war patrols in the
  Pacific, by roughly 250 boats.
- The catalog groups reports into folders by date range, usually one
  patrol per folder. BANG's six patrols are in five folders of 36–65 pages,
  about 2.5 MB per page.
- Estimate for the whole series: **~1,500 folders, ~75,000 pages, ~190 GB
  of scans.** Never commit scans. Download one boat at a time, work, and
  delete (or keep locally); the pages load from NARA when a local copy is
  missing.
- BANG's committed data is 3 MB for 6 patrols, so the whole fleet would be
  about 750 MB. That's fine for git. If it grows past about 1 GB, move
  `weather.csv` and `seafloor.csv` out (they can be regenerated) and keep
  only the transcriptions in git.

Finding a boat's folders:

```bash
python3 tools/nara.py find "Wahoo"
python3 tools/nara.py find "Tang"
```

(Spot-checked: WAHOO, TANG and BARB are all there, 24–84 pages per folder.)

## Where to start

Suggested order:

1. **BANG's wolfpack partners.** PARCHE and TINOSA (Patrol 1);
   SEAHORSE and GROWLER (Patrol 2); REDFISH and SHAD (Patrol 4);
   SPADEFISH, ATULE and POMPON (Patrol 5); SNOOK and BURRFISH (Patrol 6);
   SEGUNDO and JACK (passage home). Their reports describe the same
   convoys and nights from another boat's position, so each boat
   cross-checks BANG and the reverse. The convoy of 29–30 April 1944 should
   appear in BANG's, PARCHE's and TINOSA's reports.
2. **Other boats in the same areas and months**: the Luzon Strait
   ("Convoy College") and east of Formosa, 1944–45.
3. **Famous boats** (WAHOO, TANG, BARB) to test the pipeline on reports by
   other captains and yeomen.
4. **Early-war reports (1941 to late 1943).** NARA notes these are less
   uniform: the daily narrative is there, but the tables vary. Expect more
   reading per patrol and fewer table positions; the narrative will be the
   main source.

## Progress

- **PARCHE Patrol 1, TINOSA Patrol 6** (BANG's Patrol 1 partners):
  positions transcribed in `records/boats/`. `check_track.py`,
  `check_crossrefs.py` and `pack_timeline.py` read that layout; the pages
  and the other scripts still read BANG only. Depths and layers not yet done.

## Changes the code needs first

The code was written for one boat. What has been generalized, and what hasn't yet:

| Was BANG-specific | Now |
|---|---|
| `data/patrol-N/` for BANG, `data/boats/` for the others | Every boat in `records/boats/<hull>-<name>/patrol-N/`, every war-diary ship in `records/ships/<hull>-<name>/` |
| `PATROLS` and `SHIPS` arrays (names, dates, area, captain) in `patrols.js` | Each vessel's hand-edited `ship.yml`, gathered into `records/ships.json` by `check_track.py --geojson` |
| `MAX_KTS = 20.5` in `check_track.py` | `max_kts` in `ship.yml` |
| `CONTEXT` and `SKY_NOTES` in `build_dives.py` | Per-boat `dives.yml` |
| Page title and text say "BANG" | `patrols.html?ship=<name>` with a ship picker; the wording comes from `ship.yml`, with defaults by kind of vessel |
| Tools take a patrol number | Tools take `<boat>/<patrol>` (`bang/1`), a boat (`bang`), or `all` |

Still to do:

| BANG-specific today | Change to |
|---|---|
| `PORTS` per vessel in `ship.yml` | A shared `records/ports.yml` with all the bases: Fremantle, Brisbane, Exmouth Gulf, Majuro, Manus, Subic Bay, Dutch Harbor, … |
| `TEST_DEPTH_FT = 400` in `dives.js` | Per class: Gato 300 ft, Balao and Tench 400 ft, S-boats about 200 ft |
| `ZONES` (only the letters these reports used) | All US Navy zone letters, Z, A–M and N–Y, with the half-hour zones the reports used |
| `dives.html` reads BANG's `dives.json` and says "BANG" | `dives.html?ship=<name>` for any boat with a `depths.csv` |

Once there are many boats, add:

- **Fleet map**: every patrol of every boat, filtered by date, playable,
  so you can watch submarines converge on a convoy.
- **Cross-references**: a `meetings.csv` of wolfpack rendezvous and shared
  convoys linking boats' log entries, and JANAC / Japanese records of each
  sinking.

## Work per patrol (checklist)

1. `python3 tools/nara.py fetch <ids>`
2. `uv run --with pillow python3 tools/crop_pages.py sheet <id>` to find the
   narrative, the contact tables, the attack sheets and the density layers.
3. Transcribe `positions.csv` from the tables and noon positions.
4. Run `check_track.py`, then resolve every flag with `*_fix` or `on_track=no` and a `fix_note`.
5. Transcribe `depths.csv` from the narrative: every dive, surfacing, depth, depth charge and summary span.
6. Transcribe `layers.csv` from the density-layer table.
7. `fetch_seafloor.py`, `fetch_weather.py`, `build_dives.py`.
8. Look at both pages for that patrol. Check that the dive pattern follows
   day and night, that depth charges sit at believable depths, and that the
   track has no oddities.
9. Check the sky notes, plus anything else the captain logged that can be
   checked independently (moonrise or moonset, seafloor soundings, "sat on
   the bottom").
10. Commit with the patrol in the message: `ss-385-bang patrol 3: positions, depths, layers`.

BANG took about one long working session per stage across all six patrols
(positions, then depths, then layers). Plan on roughly 150–250 page-halves
read per patrol.

## Keeping quality up at scale

- **Second reader.** For a sample of pages per boat (say 10%), have a
  separate Claude session transcribe them from scratch without seeing the
  CSV, then diff. Investigate every disagreement against the scan.
- **The speed check is necessary but not sufficient.** It catches gross
  typos (wrong degree, wrong date) but not a few minutes of latitude.
  Cross-boat checks catch more.
- **Never overwrite a raw value.** Corrections always go in `*_fix` columns
  with a reason.
- **Mark uncertainty.** `?` for illegible digits, `(time not stated)` in quotes.

## Running it remotely with Claude

`CLAUDE.md` at the repo root tells a Claude session how the project works.
For Claude Code sessions in the cloud:

- The environment needs network access to `catalog.archives.gov` (scans),
  `coastwatch.pfeg.noaa.gov` (ETOPO1), `archive-api.open-meteo.com` (ERA5),
  and for viewing pages `d3js.org` and `cdn.jsdelivr.net`.
- Scans don't persist between cloud sessions. Each session downloads the
  boat it's working on (about 50 MB per patrol).
- Good remote task sizes: "transcribe positions for PARCHE patrol 2";
  "generalize the code for multiple boats (see FLEET.md)"; "second-read
  pages 3–12 of folder 74802746 and diff against depths.csv".
