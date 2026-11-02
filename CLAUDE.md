# CLAUDE.md

A kit for rebuilding WWII ships' and units' movements from their own records. Read
`guides/METHODS.md` before transcribing anything, `guides/MORNING-REPORTS.md` before
reading Army morning reports, and `guides/MUSTER-ROLLS.md` before following a Navy shore unit.
For film of a place and date, follow the skill `find-film` (rules in `records/film/README.md`).

## The rule: cite every source

- Every row carries the page it was read from (`page`, `ref`, `source` or `map`), in a form
  listed in `records/SOURCES.yml`. A new archive, book or site gets an entry there first.
- Every claim in a note, a guide or a page says where it comes from.
- `uv run tools/check_sources.py` must pass before a commit (the commit hook runs it). After citing a new National
  Archives item, run it with `--fetch` to add the item's catalog title to `citations.json`.

## Layout

- `records/`: the data (the wwii-unit-records repository, a submodule). Hand-edited CSV and YAML
  are the source of truth; fields in `records/README.md`. CSV only for numbers, dates and short codes (no cell
  ever needs a quote or a comma); anything with words goes in YAML or Markdown with front matter; JSON is generated.
  - `boats/<hull>-<name>/ship.yml` + `patrol-N/` (positions, depths, layers, attacks.csv and attack_sheets.yml,
    japanese.yml, claims.yml, frupac.yml); `ships/<hull>-<name>/`; `engagements/<id>/` (engagement.md, events.yml, claims.yml,
    positions.csv; `guides/ENGAGEMENTS.md`); `convoys/<id>/convoy.md`; `army/`; `seabees/`;
    `silhouettes/silhouettes.yml` (recognition silhouettes, each citing its plate).
  - `inventory.yml`: every report, found or not, and how far along it is. Update it with the work.
  - Generated, never edited: `*.geojson`, `ships.json`, `seafloor.csv`, `weather.csv`,
    `dives.json`, `engagements/*/engagement.json`, `engagements/index.json`, `convoys/convoys.json`, `silhouettes.json`, `scans.json`, `citations.json`,
    `army/army.json`, `army/seafloor.csv`, `seabees/seabees.json`, `reference/glossary.json`.
- `tools/`: Python. Every file opens with a PEP 723 header giving the oldest Python it runs on and the packages it
  imports (`dependencies = []` for the standard library alone; a shared module like `records.py` too), so `uv run`
  builds its environment and ty checks it against exactly that. `tools/records.py` finds the records and the cache.
- `reference/jgrid/`: the Japanese kana grid keys and anchors (hand-edited; `guides/JAPANESE-GRID.md`).
- `reference/lanes/lanes.yml`: the convoy lanes' ports and (assumed) waypoints, which a convoy's `route:` runs through.
- `reference/glossary.yml`: the terms the pages explain on hover, each citing its source (`tools/build_glossary.py` writes
  `glossary.json`, which `site/glossary.js` reads).
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

## Checks and hooks

The hooks run by themselves once installed (`uv tool install prek`, then `prek install` here and in `records/`;
`.pre-commit-config.yaml` in each). Before a commit (seconds): ruff and ty on the tools, the lint, the citations, the
computation's tests. Before a push (minutes), and in the CI: everything, with every build, the land check and every page
in a browser. A hook that fails is fixed, not skipped.

- `tools/lint.py`, in the manner of ruff: rule codes, `file:line` findings, settings and allowed exceptions (each with
  its reason) in `lint.toml`. References that point at nothing (REF), orphans nothing uses (ORF), file forms (FMT, CSV,
  YML), records that disagree (CON), the private list (PRV), ships inland (ACC). `--explain CODE`, `--rules`. Nothing
  is fixed automatically.
- `tools/smoke.py`: every page and every view the address opens, light and dark, desktop and phone, in a headless
  browser; fails on a console error, a failed request or an empty figure.
- `tools/test_tools.py`: the tools' computation against hand-worked cases (positions, zone letters, the grids'
  anchors, the land test); `site/engage.test.js` the engagement pages'.
- `tools/check_builds.sh`: every build checks out and its generated JSON is committed.
- ruff (`ruff.toml`: defects and orphans, not style) and ty through `tools/typecheck.py`: ty checks a set of files
  against one environment and doesn't yet read PEP 723 headers for several scripts (astral-sh/ty#691), so this groups
  the files by header, has uv build each group's environment (`uv sync --script`, which honours `requires-python`) and
  runs ty once per group at the header's oldest Python. Nothing is allowed unresolved: an import a header doesn't
  declare fails. A file with no header fails. Findings in the older tools are in `ty-baseline.json` (`--update-baseline`
  rewrites it), and new code adds none.
- The private list (`sources/private-terms.txt`, never committed) is written by the family repository that holds this
  kit; without it PRV001 checks nothing and says so.

## Commands

```bash
uv run tools/lint.py [--select REF,ORF] [--statistics] [--explain CODE]   # lint.toml; must report no problems
uv run tools/smoke.py [--quick] [--only engagement]   # every page in a browser (2-3 min; --quick under 1)
uv run tools/test_tools.py                    # the tools' computation against hand-worked cases
tools/check_builds.sh                         # every build: 0 problems, generated files up to date
uv run tools/typecheck.py --baseline ty-baseline.json tools -- --config-file ty.toml --extra-search-path tools   # ty, per header
prek run --all-files [--hook-stage pre-push]  # the hooks by hand
uv run tools/check_track.py all --geojson     # every track: 0 too-fast legs; GeoJSON, ships.json
uv run tools/check_track.py bang/1            # one patrol, leg by leg
uv run tools/check_sources.py [--fetch]       # citations resolve; inventory matches the folders
uv run tools/check_crossrefs.py               # attacks vs japanese.yml, minutes and miles apart
uv run tools/check_attacks.py [bang/2]        # attacks.csv: each torpedo's track against own course, gyro, target course
uv run tools/fetch_seafloor.py; uv run tools/fetch_weather.py   # after positions change (cached)
python3 tools/fetch_station_weather.py seabees  # a shore unit's daily weather: ISD stations + ERA5
uv run tools/build_dives.py                   # records/boats/ss-385-bang/dives.json
python3 tools/build_army.py                   # records/army/army.json (after editing records/army/); 0 problems
uv run tools/army_seafloor.py                 # records/army/seafloor.csv: the seafloor under the LST crossings
uv run tools/build_seabees.py                 # records/seabees/seabees.json (after records/seabees/ or its weather); 0 problems
uv run tools/build_silhouettes.py             # records/silhouettes/silhouettes.json (then build_engagement.py)
uv run tools/trace_silhouette.py PLATE.png --crop X Y W H [--symmetric] [--open 2] --preview /tmp/p.png   # trace a plate
uv run tools/build_engagement.py             # engagements and convoys -> their JSON; `check` in CI; 0 problems
uv run tools/build_glossary.py               # reference/glossary.yml -> glossary.json; every term cites its source
node site/engage.test.js                      # the engagement pages' shared computation (engage.js)
python3 tools/nara.py find "Bang" | fetch <id> | index
uv run tools/crop_pages.py sheet|halves|zoom|heads ...
python3 tools/morning_reports.py serial|unit|locate|changes|fetch ...
python3 tools/jacar.py search|meta|fetch ...;  python3 tools/jgrid.py decode|check|key ...
python3 tools/naval_grid.py decode|check|blocks ...   # Kriegsmarine naval squares, Mediterranean ("CJ 9472"; guides/NAVAL-GRID.md)
python3 tools/bezugspunkt.py decode|block|check ... [--date YYYY-MM-DD]  # German Army reference points, Italy 1944 ("71 35", "XXIII 68", "M 28"; guides/BEZUGSPUNKTE.md)
python3 tools/wayback.py list|fetch|crawl <domain> [--yes]   # an archived website -> sources/wayback/
python3 tools/frupac.py find|date ...;  python3 tools/gbooks.py search|meta|fetch ...  (key in .env)
python3 tools/grid_ref.py <grid> <ref>;  python3 tools/geocode_places.py [records/seabees/places.csv]
python3 tools/film.py nara|shots|search|meta|index|find ...   # film of a place and date: NARA moving images, listed YouTube channels (index = their uploads, saved; find = search it)
python3 tools/serve.py                        # http://localhost:8385/site/
```

After editing any CSV: `check_track.py all --geojson`, `build_dives.py`, `check_sources.py`; after `records/army/`,
`build_army.py` (and `army_seafloor.py` if a crossing changed); after `records/seabees/`, `build_seabees.py`; after
an engagement, a convoy, a patrol's japanese.yml or claims.yml, or any track, `build_engagement.py`; after
`reference/glossary.yml` or `records/SOURCES.yml`, `build_glossary.py`.

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
  colours were checked for colour-blind separation: don't add hues without checking again. The engagement pages
  (`engagement.html`, `convoys.html`, `lanes.html`) share `site/engage.css`, whose boat colours were checked with the
  hit red, every pair, both modes; their encodings (solid, outlined, hatched, dotted; red only for hits) are in
  `guides/ENGAGEMENTS.md`, and their computation is `site/engage.js`, never redone in a page. The engagement page's
  observer view (`site/observer.js`) draws each attack from its sheet with `engage.js`'s `attackSheet` and `attackAt`.
- Verify changes in a browser: light and dark mode, every ship on `patrols.html`, every engagement on
  `engagement.html`, no console errors.

## Don't

- Commit anything under `sources/`, or `.env`.
- Copy the FRUPAC maps (CC BY-NC-ND): link them.
- Publish or post anything outside the repository without asking.
