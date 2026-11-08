# CLAUDE.md

A kit for rebuilding WWII ships' and units' movements from their own records. Read
`guides/METHODS.md` before transcribing anything, `guides/MORNING-REPORTS.md` before
reading Army morning reports, and `guides/MUSTER-ROLLS.md` before following a Navy shore unit.
For film of a place and date, follow the skill `find-film` (rules in `records/film/README.md`). For a day's situation map
(the front and the divisions, `records/fronts/`), follow the skill `trace-situation-map`; for many days of the Library's
collection at once, `guides/SITUATION-MAPS.md` (the catalogue is `tools/loc_sitmaps.py`, one day a reader agent).

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
  - Generated, never edited: `*.geojson`, `ships.json`, `seafloor.csv`, `weather.csv`, `fronts/sitmaps.csv` (from the Library's API),
    `dives.json`, `engagements/*/engagement.json`, `engagements/index.json`, `convoys/convoys.json`, `silhouettes.json`, `scans.json`, `citations.json`,
    `army/army.json`, `army/seafloor.csv`, `seabees/seabees.json`, `reference/glossary.json`.
- `tools/`: Python. Every file opens with a PEP 723 header giving the oldest Python it runs on and the packages it
  imports (`dependencies = []` for the standard library alone; a shared module like `records.py` too), so `uv run`
  builds its environment and ty checks it against exactly that. The floors differ on purpose: most tools run on 3.9,
  a few claim 3.10 or 3.11 for something they use (`tomllib` in `lint.py` and `typecheck.py`), ruff targets 3.11
  because uv runs the newest Python, and ty checks each tool at its own header's floor, so a header that claims older
  than the code needs fails. `tools/records.py` finds the records and the cache.
- `reference/jgrid/`: the Japanese kana grid keys and anchors (hand-edited; `guides/JAPANESE-GRID.md`).
- `reference/lanes/lanes.yml`: the convoy lanes' ports and (assumed) waypoints, which a convoy's `route:` runs through.
- `reference/glossary.yml`: the terms the pages explain on hover, each citing its source, and the records' notations as
  `patterns` (a regular expression, read alike by JavaScript and Python, and the explainer page opened at the value:
  `zones.html?zone=K`, `grids.html?ref=`, `jgrid.html?code=`, `german.html?ref=`, `torpedo.html?track=`), checked and
  written to `glossary.json` by `tools/build_glossary.py`, which `site/glossary.js` reads.
- `site/`: static pages, no build step. D3 7.9.0, topojson-client, js-yaml and suncalc come from a CDN, each at the one
  pinned address listed at the top of `config.js` (a page's `<script src>` must match it exactly); `config.js` also holds
  the paths.
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
in a browser (the CI skips the pages when a push changes documentation alone: `tools/pages_changed.sh`). A hook that
fails is fixed, not skipped.

Two repositories, three layers. `records/` is its own repository (wwii-unit-records) with its own hooks, which call the
kit's tools from `../tools/`. A change that touches the records is committed and pushed in `records/` first, then the
kit commits the new submodule pointer; the CI (`.github/workflows/pages.yml`) checks out recursively, so a pointer to
an unpushed records commit fails it, and `check_builds.sh` compares the generated files inside `records/`. Above the
kit sits a private family repository that holds it as `kit/`: it writes `sources/private-terms.txt` for the lint's
PRV001 and runs the kit's `smoke.py` over its own pages (`views()` and `run()`).

- `tools/lint.py`, in the manner of ruff: rule codes, `file:line` findings, settings and allowed exceptions (each with
  its reason) in `lint.toml`. References that point at nothing (REF), orphans nothing uses (ORF), file forms (FMT, CSV,
  YML), records that disagree (CON), the private list (PRV), ships inland (ACC). `--explain CODE`, `--rules`. Nothing
  is fixed automatically.
- `tools/smoke.py`: every page and every view the address opens, light and dark, desktop and phone, in a headless
  browser; fails on a console error, a failed request or an empty figure.
- `tools/test_tools.py`: the tools' computation against hand-worked cases (positions, zone letters, the grids'
  anchors, the land test); `site/engage.test.js` the engagement pages'.
- `tools/check_builds.sh`: every build checks out, and every generated file a tool can rebuild from the committed records
  alone (the tracks and `ships.json`, `citations.json`, `silhouettes.json`, the army, seabees, operations, dives,
  engagement and glossary JSON) is committed and up to date, named with its build when it isn't; `scans.json` and the
  downloaded seafloor, weather and relief files are not checked, since they need the network or `sources/`.
- ruff (`ruff.toml`: defects and orphans, not style) and ty through `tools/typecheck.py`: ty checks a set of files
  against one environment and doesn't yet read PEP 723 headers for several scripts (astral-sh/ty#691), so this groups
  the files by header, has uv build each group's environment (`uv sync --script`, which honours `requires-python`) and
  runs ty once per group at the header's oldest Python. Nothing is allowed unresolved: an import a header doesn't
  declare fails. A file with no header fails. Findings in the older tools are in `ty-baseline.json` (`--update-baseline`
  rewrites it), and new code adds none.
- The private list (`sources/private-terms.txt`, never committed) is written by the family repository that holds this
  kit; without it PRV001 checks nothing and says so.

## Commands

The ones an agent runs most. Every tool, what it does and when to run it: `tools/README.md`.

```bash
uv run tools/lint.py [--select REF,ORF] [--explain CODE]   # lint.toml; must report no problems
uv run tools/check_sources.py [--fetch]       # citations resolve; inventory matches the folders
tools/check_builds.sh                         # every build: 0 problems, generated files up to date
uv run tools/test_tools.py                    # the tools' computation against hand-worked cases
uv run tools/smoke.py [--quick] [--only engagement]  # every page in a browser (2-3 min; --quick under 1; --install first)
uv run tools/build_engagement.py              # engagements and convoys -> their JSON; `check` in CI; 0 problems
prek run --all-files [--hook-stage pre-push]  # the hooks by hand
```

After editing any CSV: `check_track.py all --geojson`, `build_dives.py`, `check_sources.py`; after `records/army/`,
`build_army.py` (and `army_seafloor.py` if a crossing changed); after `records/seabees/`, `build_seabees.py`; after
`records/operations/`, `build_operations.py`; after an engagement, a convoy, a patrol's japanese.yml or claims.yml, or
any track, `build_engagement.py`; after `reference/glossary.yml` or `records/SOURCES.yml`, `build_glossary.py`; after any of
those, a `plain` line, `army/units.yml`, `seabees/units.yml`, `army/leads.yml`, `relations.csv` or `parts.csv`, `build_subjects.py`.

## Pages

Where the pages are going (subjects, frames, the two depths; the design, checked against TAMA-17 and the 67th CA (AA)'s
Medical Detachment): `guides/OPERATIONS-VIEWER.md`. Read it before adding a page or a view.

- Every mark links to its source page (the scan viewer falls back to the archive's URL from
  `records/scans.json`).
- Silhouettes are data, not drawing code: shapes in `records/silhouettes/silhouettes.yml`; `site/silhouettes.js`
  only loads them (the `SILHOUETTES` promise) and draws hull symbols. Never draw one from memory: trace a plate
  or work to its printed dimensions, and cite it.
- Type has three voices, each with one job: ET Book for the kit's own words, TT2020 style E for the records' typed
  words (`.typed`, `.mono`, `code`; `--typed`), Shippori Mincho for Japanese (`[lang="ja"]`; the original before our
  translation; the element carries `lang` and `data-tr`, the translation, so `glossary.js` opens the English in its card on
  hover, focus or tap). `glossary.js` also marks the records' notations (`glossary.yml` `patterns`: a zone-lettered time, a
  grid reference, a kana code, an attack sheet's angles), each distinct value once per passage, with a card that names the
  notation, shows the value in the typed voice and links the explainer opened at it; a page that prints a zone-lettered time
  may carry its date in `data-date` (or a `time[datetime]` around it) so the card can give the GMT through `Engage.toUTC`.
  Fonts are in `site/fonts/fonts.css`. Special Elite only for the front page's masthead. No capitals for
  labels: italics instead.
- Every page has the same navigation bar, at the top of its header: an empty `<nav class="nav" aria-label="The kit"
  data-nav></nav>` followed by `<script src="nav.js"></script>`, which `site/nav.js` fills as the page is parsed (so
  nothing shifts) and marks the current page on (the query too: `theatre.html?t=pacific`). The bar is the guide's §5.3
  and nothing else: *Engagements* (`engagements.html`, the index of every one: the way in), the four theatres, *Subjects*,
  *Reading the records* (the explainers), *Researching a relative*; its links live in `nav.js` alone. Under it, every
  page has the breadcrumb, `<nav class="crumb" id="crumb" aria-label="Where this is in the kit">`, one markup (`chapter.css`'s `.crumb .trail`, written by `Chapter.trail(parts)` or, where it is
  constant, in the page's HTML): *Pacific / the operation / the engagement*, *Subjects / BANG / Patrol 1*, *Reading the
  records / Time zones*. The engagement page's crumb (`Chapter.crumb`) adds the engagement before and after in its
  theatre and each followed unit's or boat's own before and after.
- `theatre.html?t=pacific|atlantic|mediterranean|europe` (`site/theatre.js`, `theatre.css`) is one page for the four
  theatres, built from `chapter.js`: the theatre's file in `records/operations/<theater>/index.md` (name, span, cited
  paragraphs), a static map of its records, the spine (operations in date order, engagements under them), the subjects
  here (the units' runs through the five stages, which the Mediterranean and Europe share and number across; the Pacific's
  boats, ships, battalions, convoys and command by date), what is also in the records and still to find (`inventory.yml`),
  and the explainers its records need. The front page is an index: the engagements by theatre, four theatre cards with
  one static figure each, then the shelf. `engagements.html` (`engagements.js`) is the index of every engagement, from
  `engagements/index.json`, whose rows carry each one's lede in plain words, its subjects and its counts for it.
- Colours and fonts are one set of CSS variables, named in `site/viz.css` (`--page`, `--surface`, `--ink`, `--ink-2`,
  `--ink-3`, `--rule`, `--wash`, `--land`, `--coast`, `--sea-grid`, `--pencil`; `--serif`, `--typed`, `--ja`), light
  and dark; `site/engage.css`, `site/home.css` and the two story pages set the same names to their own checked values,
  so a shared script writes `var(--ink)` and gets the page's, never a fallback chain. The three categorical
  colours were checked for colour-blind separation: don't add hues without checking again. The engagement pages
  (`engagement.html`, `subject.html`, `lanes.html`) share `site/engage.css`, whose boat colours were checked with the
  hit red, every pair, both modes; their encodings (solid, outlined, hatched, dotted; red only for hits) are in
  `guides/ENGAGEMENTS.md`, and their computation is `site/engage.js`, never redone in a page. The engagement page's
  observer view (`site/observer.js`) draws each attack from its sheet with `engage.js`'s `attackSheet` and `attackAt`;
  beside its periscope, in tabs, the Torpedo Data Computer's faces (`site/tdc.js`, drawing only, the values `tdcAt`'s).
- Verify changes in a browser: light and dark mode, every subject on `subject.html` (a boat, a ship, a unit, a
  battalion, a convoy, its page and its placement), every engagement on `engagement.html` (the page and its questions), no
  console errors.

## Don't

- Commit anything under `sources/`, or `.env`.
- Copy the FRUPAC maps (CC BY-NC-ND): link them.
- Publish or post anything outside the repository without asking.
