# CLAUDE.md

A kit for rebuilding WWII ships' and units' movements from their own records. Read
`guides/METHODS.md` before transcribing anything, `guides/MORNING-REPORTS.md` before
reading Army morning reports, and `guides/MUSTER-ROLLS.md` before following a Navy shore unit.

## The rule: cite every source

- Every row carries the page it was read from (`page`, `ref`, `source` or `map`), in a form
  listed in `records/SOURCES.yml`. A new archive, book or site gets an entry there first.
- Every claim in a note, a guide or a page says where it comes from.
- `uv run tools/check_sources.py` must pass before a commit. After citing a new National
  Archives item, run it with `--fetch` to add the item's catalog title to `citations.json`.

## Layout

- `records/`: the data (the wwii-unit-records repository, a submodule). Hand-edited CSV and YAML
  are the source of truth; columns in `records/README.md`.
  - `boats/<hull>-<name>/ship.yml` + `patrol-N/` (positions, depths, layers, japanese, crossrefs,
    frupac); `ships/<hull>-<name>/`; `engagements/<id>/engagement.yml`; `army/`; `seabees/`;
    `silhouettes/silhouettes.yml` (recognition silhouettes, each citing its plate).
  - `inventory.yml`: every report, found or not, and how far along it is. Update it with the work.
  - Generated, never edited: `*.geojson`, `ships.json`, `seafloor.csv`, `weather.csv`,
    `crossrefs.json`, `pack_timeline.csv`, `dives.json`, `battles/`, `silhouettes.json`, `scans.json`, `citations.json`,
    `army/army.json`, `seabees/seabees.json`.
- `tools/`: Python. Standard library only, except scripts with a PEP 723 header (PyYAML,
  Pillow, PyMuPDF), run with `uv run`. `tools/records.py` finds the records and the cache.
- `reference/jgrid/`: the Japanese kana grid keys and anchors (hand-edited; `guides/JAPANESE-GRID.md`).
- `site/`: static pages, D3 v7 from a CDN, no build step. `config.js` holds the paths.
- `sources/`: downloaded scans and caches. **Git-ignored. Never commit.**

## Transcription rules

- Read the scan images directly (crop to halves first). Don't use OCR text as a value; OCR only
  finds pages.
- Record date, time, zone letter and coordinates **exactly as typed**. Use `?` for an illegible
  character.
- Never overwrite a raw value. Corrections go in `lat_fix` / `lon_fix` / `date_fix` / `time_fix`
  with a reason in `fix_note`. Unresolvable fixes get `on_track=no`.
- Ship-contact positions are the **target's**, never the boat's track (`on_track=no`).
- Zone letters: reports switch zones mid-patrol, and tables are often in GCT (Z) while the
  narrative is local. Check each table's header. Boats in one pack kept different zones.
- A summary-of-attacks table can disagree with its own narrative. The narrative, timed to the
  second, usually wins; record both.
- Quotes are the record's words, abridged with `...`; editorial notes go in parentheses.
- Label every assumption: in the data (`assumed`, `placed`, `basis` columns), and on the page
  (hatching, dashed lines, "assumed" in tooltips).

## People

The records are the units', not the people's. Don't add rosters, crew lists, service histories or
a person's own path (a replacement depot, a hospital) to `records/`, and don't follow anyone by
name. Names the records carry (a captain, a pack commander, a rescued aviator) stay as written:
nothing is redacted.

## Commands

```bash
uv run tools/check_track.py all --geojson     # every track: 0 too-fast legs; GeoJSON, ships.json
uv run tools/check_track.py bang/1            # one patrol, leg by leg
uv run tools/check_sources.py [--fetch]       # citations resolve; inventory matches the folders
uv run tools/check_crossrefs.py               # attacks vs japanese.csv -> crossrefs.json
uv run tools/fetch_seafloor.py; uv run tools/fetch_weather.py   # after positions change (cached)
python3 tools/fetch_station_weather.py seabees  # a shore unit's daily weather: ISD stations + ERA5
uv run tools/build_dives.py                   # records/boats/ss-385-bang/dives.json
python3 tools/build_army.py                   # records/army/army.json (after editing records/army/); 0 problems
uv run tools/build_seabees.py                 # records/seabees/seabees.json (after records/seabees/ or its weather); 0 problems
uv run tools/build_silhouettes.py             # records/silhouettes/silhouettes.json (then build_battle.py)
uv run tools/trace_silhouette.py PLATE.png --crop X Y W H [--symmetric] [--open 2] --preview /tmp/p.png   # trace a plate
uv run tools/build_battle.py [<id>]           # records/battles/ (new <id> <patrol>... drafts one)
python3 tools/nara.py find "Bang" | fetch <id> | index
uv run --with pillow python3 tools/crop_pages.py sheet|halves|zoom|heads ...
python3 tools/morning_reports.py serial|unit|locate|changes|fetch ...
python3 tools/jacar.py search|meta|fetch ...;  python3 tools/jgrid.py decode|check|key ...
python3 tools/frupac.py find|date ...;  python3 tools/gbooks.py search|meta|fetch ...  (key in .env)
python3 tools/grid_ref.py <grid> <ref>;  python3 tools/geocode_places.py [records/seabees/places.csv]
python3 tools/serve.py                        # http://localhost:8385/site/
```

After editing any CSV: `check_track.py all --geojson`, `build_dives.py`, `check_sources.py`; after `records/army/`,
`build_army.py`; after `records/seabees/`, `build_seabees.py`.

## Pages

- Every mark links to its source page (the scan viewer falls back to the archive's URL from
  `records/scans.json`).
- Silhouettes are data, not drawing code: shapes in `records/silhouettes/silhouettes.yml`; `site/silhouettes.js`
  only loads them (the `SILHOUETTES` promise) and draws hull symbols. Never draw one from memory: trace a plate
  or work to its printed dimensions, and cite it.
- Type has three voices, each with one job: ET Book for the kit's own words, TT2020 style E for the records' typed
  words (`.typed`, `.mono`, `code`; `--typed`), Shippori Mincho for Japanese (`[lang="ja"]`; the original before our
  translation). Fonts are in `site/fonts/fonts.css`. Special Elite only for the front page's masthead. No capitals for
  labels: italics instead.
- Every page has the same navigation bar, at the top of its header (copy it from any page).
- Colours are CSS variables in `site/viz.css` with light and dark values. The three categorical
  colours were checked for colour-blind separation: don't add hues without checking again.
- Verify changes in a browser: light and dark mode, every ship on `patrols.html`, no console errors.

## Don't

- Commit anything under `sources/`, or `.env`.
- Copy the FRUPAC maps (CC BY-NC-ND): link them.
- Publish or post anything outside the repository without asking.
