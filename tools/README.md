# The tools

Every tool here is a Python script with a PEP 723 header (the oldest Python it runs on, the packages it imports), so
`uv run tools/<name>.py` builds its environment; one that imports nothing but the standard library also runs as
`python3 tools/<name>.py`. `records.py` is the shared module: where the records (`records/`, or `WWII_RECORDS`) and the
cache (`sources/`, or `WWII_CACHE`) are, and how a boat or a ship is named (`ss-385-bang`, `bang`, `bang/1`). Each
tool's docstring says more than this list; the rules are in `CLAUDE.md`.

## The checks

| Command | What it does | When |
|---|---|---|
| `uv run tools/lint.py [--select REF,ORF] [--statistics] [--explain CODE] [--rules]` | References that point at nothing (REF), orphans (ORF), file forms (FMT, CSV, YML), records that disagree (CON), the private list (PRV), ships inland (ACC); settings and allowed exceptions in `lint.toml` | Before a commit (the hook runs it without ACC; the push hook and the CI with it). Must report no problems |
| `uv run tools/check_sources.py [--fetch]` | Every citation resolves to `records/SOURCES.yml` and every source there has a `kind` (`records.SOURCE_KINDS`), every row has one, the inventory matches the folders; `--fetch` adds a newly cited National Archives item's title to `citations.json` | Before a commit (the hook); after citing anything new |
| `tools/check_builds.sh` | Every build checks out with 0 problems and its generated JSON is committed | Before a push (the hook) and in the CI |
| `tools/pages_changed.sh BEFORE [AFTER]` | Whether a push can change what the pages show: `pages=false` only when every file it changes is documentation (the kit's Markdown, the records' READMEs and LICENSE; the records' other Markdown is data), each file listed as doc or page | In the CI, which skips the smoke test on `pages=false` |
| `uv run tools/smoke.py [--quick] [--only engagement] [--shard I/N] [--list] [--install]` | Every page and every view the address opens, light and dark, desktop and phone, in a headless browser; fails on a console error, a failed request or an empty figure (2-3 min; `--quick` under 1). `--install` once first, for the Chromium its pinned Playwright drives; the CI runs it in four `--shard`s | Before a push (the hook) and in the CI; after any change to `site/` |
| `uv run tools/test_tools.py` | The tools' computation against hand-worked cases: positions as typed, zone letters, the grids' anchors, the land test | Before a commit (the hook, when `tools/` or `reference/` changed) |
| `uv run tools/test_fronts.py` | The situation maps' fit: the conic recovers a sheet drawn on a known conformal conic, both ways; the choice of fit by the number of towns | Before a commit (the hook, when `trace_front.py` or `sheet_towns.py` changed) |
| `node site/engage.test.js` | The engagement pages' shared computation (`site/engage.js`) | Before a commit (the hook, when `site/engage*` changed) |
| `uv run tools/typecheck.py --baseline ty-baseline.json tools -- --config-file ty.toml --extra-search-path tools` | ty over every tool, grouped by header, each group in its own environment at its header's oldest Python; findings in the older tools are in `ty-baseline.json` (`--update-baseline` rewrites it) | Before a commit (the hook) and in the CI; new code adds no finding |
| `uv run tools/check_track.py all --geojson`, `… bang/1` | Every track (or one patrol, leg by leg): 0 too-fast legs; writes the GeoJSON and `ships.json` | After editing any `positions.csv` |
| `uv run tools/check_crossrefs.py [bang/1 \| bang \| all]` | A boat's attacks beside the Japanese records and FRUPAC notes paired with them: minutes and miles apart | After editing a patrol's `japanese.yml`, `claims.yml` or `frupac.yml` |
| `uv run tools/check_attacks.py [bang/2]` | Each torpedo's track in `attacks.csv` recomputed from own course, gyro and target course; lists the ones that disagree, changes nothing | After transcribing an attack data sheet (`check_builds.sh` runs it) |

## Finding and fetching records

| Command | What it does | When |
|---|---|---|
| `python3 tools/nara.py find "Bang" \| fetch <id> … \| index` | The National Archives catalog: a boat's war patrol report folders; their scans to `sources/nara/rg367-<id>/`; `records/scans.json`, each page's public URL | Starting a boat; after citing new pages (`index`) |
| `python3 tools/morning_reports.py serial \| unit \| locate \| changes \| fetch …` | Army morning reports (NARA RG 64): the rolls, a unit's pages, where its station changed, the scans | Following an Army unit (`guides/MORNING-REPORTS.md`) |
| `uv run tools/crop_pages.py sheet \| halves \| zoom \| heads \| thumbs \| panel …` | Readable crops of a scanned page: a contact sheet of a folder, overlapping halves, a contrast-stretched zoom, a morning report's heading | Before reading any scan (`guides/METHODS.md`) |
| `python3 tools/jacar.py search \| meta \| fetch …` | JACAR, the Imperial Navy's records: search the catalog, a record's title and pages, its scans to `sources/jacar/<code>/` | Finding the other side of an attack (the skill `find-the-other-side`) |
| `python3 tools/frupac.py harvest \| find \| date …` | The FRUPAC radio-intelligence maps on the Portal to Texas History: harvest the catalog, the maps naming a ship, the maps covering a date (linked, never copied) | The same |
| `python3 tools/gbooks.py search \| meta \| fetch …` | Google Books: digitized manuals and histories; a volume's access; its PDF when full view (key in `.env`) | Looking for a printed history or manual (`guides/GOOGLEBOOKS.md`) |
| `uv run tools/pdf_pages.py find \| text \| render <pdf> …` | A downloaded PDF: the pages whose text matches, their OCR text, and the pages rendered to read | After `gbooks.py fetch`, or any PDF in `sources/` |
| `python3 tools/wayback.py list \| fetch \| crawl <domain> [--yes]` | A lost website from the Wayback Machine, as captured, to `sources/wayback/<domain>/`, with each capture's address to cite | A source that is only on an archived site |
| `python3 tools/film.py nara \| shots \| search \| meta \| index \| find …` | Film of a place and date: the National Archives' moving images, and the listed archives' YouTube channels (`index` saves their uploads; `find` searches it) | The skill `find-film` (`records/film/README.md`) |

## Decoding a position

| Command | What it does | When |
|---|---|---|
| `python3 tools/jgrid.py decode \| check \| key …` | The Imperial Navy's four-character kana position codes, by the key in force; `check` runs the anchors against the key | A Japanese air report gives a code (`guides/JAPANESE-GRID.md`) |
| `python3 tools/naval_grid.py decode \| check \| blocks …` | Kriegsmarine naval grid squares in the Mediterranean ("CJ 9472"), from the blocks read off the wartime charts | A German naval record gives a square (`guides/NAVAL-GRID.md`) |
| `python3 tools/bezugspunkt.py decode \| block \| check … [--date YYYY-MM-DD]` | The German Army's reference points in Italy, 1944 ("71 35", "XXIII 68", "M 28"), by the edition in force on the date | A German Army report from the Cassino front gives one (`guides/BEZUGSPUNKTE.md`) |
| `python3 tools/grid_ref.py <grid> <ref> …` | An Army grid reference on any of the six grids the records use (`italy-s`, `lambert2`, `ndg`, …) to latitude and longitude | Placing an Army station or action given as a grid reference |
| `python3 tools/ndg_grid.py Y-888629 …` | The "Nord de Guerre" grid alone (eastern France into Bavaria, the 106th AAA's 1945 records); `grid_ref.py ndg …` is the same conversion | The same, when only that grid is in question |
| `python3 tools/geocode_places.py [records/seabees/places.csv] [--audit]` | Coordinates for the places a `places.csv` names, from OpenStreetMap, rows with none only; hand-placed points stay | After adding a place with no coordinates |

## Outside data along the records

| Command | What it does | When |
|---|---|---|
| `uv run tools/fetch_seafloor.py [bang/1 …]` | The seafloor under each track (NOAA ETOPO1), cached by tile in `sources/etopo1/` | After positions change |
| `uv run tools/fetch_weather.py [bang/1 …]` | Hourly ERA5 weather along each track (Open-Meteo), cached in `sources/era5/` | After positions change |
| `python3 tools/fetch_station_weather.py seabees` | A shore unit's daily weather at its stations: ISD observations where a station was near, ERA5 everywhere | After a shore unit's stations change |
| `uv run tools/army_seafloor.py` | The seafloor under the Army units' LST crossings (`records/army/seafloor.csv`) | After `build_army.py`, if a crossing changed |
| `uv run tools/build_relief.py algiers 2.72 36.60 3.42 37.08 --zoom 12 [--rivers]` | Shaded relief and a land mask for a map view (`records/relief/<view>/`), from the AWS Terrain Tiles: today's ground, not the war's; with `--rivers`, Natural Earth's rivers inside the box | Adding a map view that needs relief |

## The builds

Each writes a generated file in `records/`, which is committed and never edited; `check_builds.sh` runs them all and
fails if one is out of date.

| Command | What it does | When |
|---|---|---|
| `uv run tools/check_track.py all --geojson` | `track.geojson`, `tracks.geojson`, `ships.json` (above) | After editing any `positions.csv` |
| `uv run tools/build_dives.py [boat]` | `records/boats/ss-385-bang/dives.json`: the depth logs, layers, seafloor and weather for the dive-profile page | After editing a patrol's CSVs |
| `python3 tools/build_army.py` | `records/army/army.json`; checks the Army transcriptions; 0 problems | After editing `records/army/` |
| `uv run tools/build_seabees.py` | `records/seabees/seabees.json`; checks the Seabee transcriptions; 0 problems | After editing `records/seabees/` or its weather |
| `uv run tools/build_operations.py [check FILE …]` | `records/operations/operations.json` from the operations' Markdown; every citation and `[[link]]` resolves; `check` for other files' links | After editing `records/operations/` |
| `uv run tools/build_engagement.py [check]` | Every engagement's `engagement.json`, `engagements/index.json`, `convoys/convoys.json`; checks every field (`guides/ENGAGEMENTS.md`); `check` alone in the CI | After an engagement, a convoy, a patrol's `japanese.yml`, `claims.yml` or `frupac.yml`, or any track |
| `uv run tools/build_subjects.py [check]` | `records/subjects.json`: every subject the pages follow (boats, ships, Army units, Seabee battalions, convoys, commands) with its plain line, periods, organizations from every dataset, engagements and record counts; fails on a subject without a `plain` line; `check` alone in the CI | After any of the builds above, a `plain` line, `army/units.yml`, `seabees/units.yml`, `army/leads.yml`, `army/relations.csv` or `seabees/parts.csv` |
| `uv run tools/build_silhouettes.py` | `records/silhouettes/silhouettes.json` from `silhouettes.yml`; every shape cites its plate | After editing a silhouette (then `build_engagement.py`) |
| `uv run tools/trace_silhouette.py PLATE.png --crop X Y W H [--symmetric] [--open 2] --preview /tmp/p.png` | A silhouette traced from a recognition plate's scan into a path for `silhouettes.yml` | Adding a silhouette (the skill `add-silhouette`) |
| `uv run tools/build_glossary.py [check]` | `reference/glossary.json` from `reference/glossary.yml`; every term cites its source; each notation pattern compiles, matches its example and none of its `not` forms, and links a page in `site/` | After editing `reference/glossary.yml` or `records/SOURCES.yml` |
| `uv run tools/trace_roads.py [--write-routes] [--overlay /tmp/o.jpg]` | The primary roads of OSS Map No. 967 (Algeria and Tunisia, 1942) traced from the scan to `records/roads/oss967-primary.geojson`, and the Army's road moves routed along them | Once per scan; again if a road move or a control point changes |
| `uv run tools/loc_sitmaps.py list \| sizes \| status \| fetch DATE [DATE] \| fetch B12 \| crop ITEM X Y W H \| overview ITEM` | The Library of Congress's situation maps: the collection's listing into `records/fronts/sitmaps.csv` (415 days) and each scan's size; where every day stands (fetched, traced, read); the scans of a day, a run of days or a base sheet's days into `sources/maps/loc/`; a region or the whole sheet from the Library's IIIF service, no scan needed | `list` when the collection changes (it hasn't); `fetch` before tracing; `status` to plan |
| `uv run tools/sheet_towns.py crops B13 --graticule [--step 0.5] --with margins.txt \| crops B11 candidates.csv [--with readings.txt] \| accept B13 readings.txt` | A whole base sheet's control points (`records/fronts/towns-<base>.csv`): a gridded crop of the sheet round where the conic fit puts each of the sheet's graticule crossings (`--graticule`, the better way: exact points; a new sheet's first fit solved from the degree labels on its margins, `1W 2460,330` a line) or each candidate town (geocoded with Nominatim), for a reader to read the crossing or the ring's centre off; the readings into the file, and the conic's residuals, the points that disagree most first; a sheet with no graticule inside is fitted on its margin ticks | Once per base sheet, before its days are traced across the sheet |
| `uv run tools/sitmap_bases.py fetch \| group [--write] \| check B12 [--towns MAP]` | Which base map each day is printed on: every day's overview (12.5 %, through IIIF), the days grouped by phase correlation of their line work (contact sheets and a report in `sources/fronts-work/bases/`; `--write` puts each day's base into `sitmaps.csv`), and a check of whether a day's towns, read by eye, register on a base's first day (the same plate, or a sheet whose towns must be read). What each base is: `records/fronts/bases.yml` | `group` once (done); `check` before tracing a day on a base without `towns` |
| `uv run tools/trace_front.py 12ag-1945-03-08 [--title \| --fetch \| --gcps-from [MAP] \| --boxes \| --look X,Y ... \| --units FILE \| --overlay \| --sides]` | A dated situation map, any day in the catalogue: read its title (from the Library, before fetching) and write the day's YAML, `records/fronts/<map>.yml`; fetch the scan; fit it to its towns (matched to another day's sheet); trace the front (through waypoints, or its stretches turned by their ticks) and check it on an overlay; find and number the symbols' boxes and write the units read; the page's side test on the towns; then `records/fronts/<map>.geojson`. The order of work is the skill `trace-situation-map`; many days at once, `guides/SITUATION-MAPS.md` | Once per map; again if a town, a box, a flip or a symbol changes |
| `uv run tools/check_fronts.py 1944-12-16 1945-01-31` | A run of traced days set beside one another: a town whose side differs from both neighbours' (a stretch turned the wrong way), a town much nearer the front than on both neighbours (heavy ink traced as front far behind the line, which the side test misses; the nearest stretch named), a front much shorter than both neighbours' (a stretch lost). Leads for the reviewer, each looked at on the overlay | After a run of days is traced, before it is committed |
| `uv run tools/neighbours.py 60aib 1944-12-27 1945-01-03 [--radius 20] [--json]` | Who was beside a unit and who faced it, day by day, from the situation maps whose symbols are read: measured from the unit's own station (or the nearest formation above it with one), every friendly and enemy symbol within the radius with its distance and bearing, each enemy one across the traced front or not, the attachments the records give that day, and over the run each neighbour's days and distances with where to read its records. Computed leads, never stored | To find whose records may mention a unit, and the other side's, for an engagement or a stretch of a unit's track |
| `uv run tools/oss967_landings.py [--overlay /tmp/l.jpg]` | The same map's landing-place arrows read into `records/roads/oss967-landings.csv` | Once per scan, with `trace_roads.py` |

## Viewing

| Command | What it does | When |
|---|---|---|
| `python3 tools/serve.py [port]` | Serves the folder at `http://localhost:8385/site/` with caching off, so edits show on reload | Looking at the pages |
