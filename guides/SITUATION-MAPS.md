# The situation maps: the whole collection, and how to work through it

HQ Twelfth Army Group drew a situation map every day from the landings to the end of the war in Europe, and the Library
of Congress holds the run: *World War II Military Situation Maps from 1944 to 1945*, 415 daily sheets from 6 June 1944
to 26 July 1945 (SOURCES.yml `loc-12ag`; the only day missing is 12 November 1944). Each sheet is the army group's own
picture of a day: the front line as the staff drew it, its own divisions and corps, and the enemy's as its intelligence
placed them. For the engagement pages they are context under the records (`records/fronts/README.md`): a symbol stands
in its unit's area, not at a position, and the line is a drawing at the map's hour, not a survey.

Eleven days are traced (7–17 March 1945, for Remagen), six by a person and the tool together and five by agents from
the skill `trace-situation-map`. This guide is what the collection is, what processing it means, which parts a tool does
alone and which need a reader, and how to run readers in parallel at a cost that makes the whole run reasonable. The
numbers for the collection are from its catalogue (`records/fronts/sitmaps.csv`, `tools/loc_sitmaps.py`) and from
trials on 6 November 2026; the costs are estimates from the March days, and say so.

## 1. What the collection is

| | |
|---|---|
| Sheets | 415, one a day, 6 June 1944 – 26 July 1945; 12 November 1944 is not in the collection |
| Items | each a Library item (an LCCN) with one scan, resource id `ict21001` to `ict21417`, rising with the date (two ids unused) |
| Also catalogued | one composite sheet (the Bulge, `2001628569`, no daily scan) and the collection's own record, both left out of the catalogue |
| Scans | JPEG 2000, about 6 MB each (2.5 GB in all), about 6,650 × 5,980 px landscape to 18 April 1945, about 5,950 × 6,680 px portrait from 19 April (10 September 1944 is a double sheet, 13,008 px wide) |
| Service | the scan by one address on the tile server (no bot check); any region at any size by IIIF (`info.json`, regions by pixel, sizes by width or percent), a crop in under a second |
| Base maps | fifteen printings (`records/fronts/bases.yml`, B01–B15; each day's in `sitmaps.csv`, grouped by their overviews with `tools/sitmap_bases.py`): 1:500,000 sheets of Normandy (6 June – 4 August), then Brittany, the Loire, the Seine, changing every few days in August; a 1:750,000 sheet 2–5 September; one 1:1,000,000 plate of north-west Europe from 6 September 1944 to 6 April 1945, placed three ways on the paper (the March towns register on all three: 211 days from one reading); a 1:1,000,000 sheet of north Germany 7–18 April; a portrait 1:1,400,000 sheet of Germany from 19 April, with red boundaries from 20 May |
| Titles | the wording changes: "SITUATION - 2400 HRS 6 JUNE 1944, HQ FUSAG"; "SITUATION 1200 HRS 22 DECEMBER 1944, TWELFTH ARMY GROUP" (no report number); "TO ACCOMPANY G-3 REPORT NO. 275, SITUATION AS OF 071200 MAR. 1945" |
| Dates | the catalogue's date is the title's on every sheet checked (eleven in March, one in December, one in June) |

The one fact that makes a long run possible: **the daily sheets are printings of one base map for months at a time**,
so one day's towns, read by eye once, find themselves on every other day of that base by matching. 7 March 1945's
twenty towns match 22 December 1944's sheet 20 of 20, median half a pixel. A new base costs one reading of its towns;
every other day of it costs nothing.

## 2. What processing a day means

Five stages, in order. Three are a tool's alone; two need someone to look.

| Stage | Who | What | Cost |
|---|---|---|---|
| **Catalogue** | tool (`loc_sitmaps.py list`, `sizes`) | the listing and each scan's size into `sitmaps.csv` | done; minutes to redo |
| **Fetch** | tool (`loc_sitmaps.py fetch`) | the scans into `sources/maps/loc/`, a second apart, resumable | 2.5 GB, about half an hour, once |
| **Title** | a reader (`trace_front.py --title`, from IIIF, before fetching) | the day's hour and report read on the sheet; the day's YAML written | one image |
| **Towns** | tool (`--gcps-from`) on a known base; a reader once per new base | the fit, 20 towns, about half a km | nothing, or an hour once per base |
| **Front** | tool (`--overlay --sides`), then a reader | the heavy ink's stretches turned by their ticks; the reader checks the overlay, decides the few stretches the ticks don't settle (`flip`, `checked`, `exclude`), reruns | 2–6 images, a few decisions |
| **Symbols** | a reader (`--boxes`, `reading.txt`, `--units`, `--check-units`) | every unit symbol read as drawn | 40–70 symbols a day on the March sheets: the dear part |

The front and the symbols are separable: a day can have its line traced and no symbols read, and the page draws what it
has. That is the lever on cost: **trace every day's front; read the symbols where they matter.**

What the trial on 22 December 1944 taught about the fit: the twenty towns of 7 March box the Remagen country
(Grevenbroich to the Moselle), and the tool traces only inside the towns' spread. On 22 December the front lay west of
that box, so only four fragments were found and the side test put every town on the enemy's side, correctly and
uselessly. For a whole base sheet the towns must spread over the whole sheet, forty or so, and the fit should become
the sheet's own projection (a conformal conic, as the sheet names it) rather than a polynomial, which is good over a
few degrees and not over a sheet. That is the first piece of tool work before a long run (§5).

## 3. The readers

One day is one job. The job is the agent `situation-map-reader` (`.claude/agents/`), which follows the skill, writes
only its own day's four files and its work folder, and reports back in a fixed shape: the title as read; the towns'
agreement; every stretch it turned, confirmed or left out, with its reason; the symbols read and the ones it is unsure
of; what the reviewer should look at first. It never edits the tool, an engagement or a page, and never commits.

The day's YAML is what makes parallel work safe. In March the five agents each needed boxes, flips and checks, and the
tool held them in one dictionary, so each agent reported its points and one person entered them; now each day's
decisions live in `records/fronts/<map>.yml`, with their reasons, and the tool reads them. Readers touch nothing in
common.

A reader's images are the cost. From the March days, a day's symbols took a reader about 40–60 tool calls and some ten
to fifteen image reads (the title, the overlay in two or three parts, two sheets of numbered boxes, the overview, a few
magnified looks, the check sheet); the front alone about 15 calls and four or five images. The tool's images are made
to be read cheaply: numbered contact sheets rather than the scan, magnified crops of the doubtful places only, and the
title and any look fetched as a small IIIF crop when the scan isn't needed.

## 4. The orchestration

A **conductor** session plans, spawns readers, reviews and commits. Readers run five at a time (the Library's servers
are shared, and five was the number that worked in March); a run is one base sheet or one month.

```
conductor                                   readers (situation-map-reader, one day each, five at a time)
─────────                                   ──────────────────────────────────────────────────────────
1 status: loc_sitmaps.py status            
2 fetch the run's scans first (one process,
  a second apart), so readers never queue
  on the tile server
3 confirm the base: sitmaps.csv's `base` and
  bases.yml's `towns` (sitmap_bases.py check
  on a base without them); if new, read its
  towns by eye (one day), commit
4 for each day in the run  ──────────────▶  title → YAML → towns → front, overlay, sides → [symbols] → report
5 review each report: open the overlay of
  every flip and check, the units sheet
  where symbols were read; send back what's
  wrong (the reader keeps its context)
6 lint, check_builds, the engagement's page
  on three days of the run, light and dark
7 commit the run in records/, then the kit
```

Rules of the road, from March:

- **Fetch before you spawn.** One process fetches the run's scans a second apart; five readers fetching at once is five
  times the load on a shared server and a 429 for everyone. Readers read titles through IIIF (one small crop) and find
  the scan already cached.
- **A reader's doubt is a `flip`/`checked` line with a reason, never a silent choice.** The reviewer reads the reasons,
  not the whole overlay: the overlay is opened only where a reason is thin or a sides test complains.
- **A new base sheet stops the run.** The reader says so in its report (the title block or the extent differs, the
  towns' match fails) and the conductor reads that base's towns before any more days are spawned on it.
- **Symbols are a scope, not a default.** The job says `front` or `front and symbols`.
- **Review samples, then reads everything that failed a check.** The tool's checks (the towns' agreement, the
  `unsure` count, the sides test) are the triage; a day that passes them all gets a look at its overlay's thumbnail and
  its flips; a day that fails one gets read.
- **Commit by run, in the records first.** A month of days is one records commit and one kit commit (the pointer, the
  README's table), after the checks.

The same shape as a Workflow script, for a session that has the Workflow tool:

```js
export const meta = { name: 'trace-situation-maps', description: 'Trace one run of days, five readers at a time, then review',
                      phases: [{ title: 'Trace' }, { title: 'Review' }] }
const DAYS = args.days            // ['12ag-1945-03-18', ...], one base sheet, scans already fetched
const SCOPE = args.scope || 'front'
const reports = await pipeline(DAYS,
  d => agent(`Trace ${d}: towns from ${args.towns}; scope ${SCOPE}. Follow the skill trace-situation-map and report as your definition asks.`,
             { label: `trace:${d}`, phase: 'Trace', subagent_type: 'situation-map-reader', schema: REPORT_SCHEMA }),
  r => r.unsure > 0 || r.sides_wrong.length || r.towns_agreeing < 12
       ? agent(`Review ${r.map}: open its overlay at ${JSON.stringify(r.flips.concat(r.checked))}; say what is wrong, or that it stands.`,
               { label: `review:${r.map}`, phase: 'Review', schema: VERDICT_SCHEMA })
       : Promise.resolve({ map: r.map, stands: true, sampled: false }))
return { reports }
```

The pipeline reviews each day as it finishes, so a run of thirty days keeps five readers busy and the reviewer never
waits for the slowest. The concurrency limit is the Library's, not the model's.

## 5. The order of work, and what it costs

Costs are estimates. The March readers were Sonnet-class; a day's symbols cost on the order of a dollar or two in model
time, a day's front on the order of a quarter to a half; the conductor's review on the order of a half to one per day
read in full, far less for a day that passes its checks and is sampled. Tool runs are minutes of CPU and no model time.
The Library's servers cost patience: a second between requests, and a run's scans fetched once.

| Scope | Days | Tool work first | Reader work | Model cost, rough |
|---|---|---|---|---|
| **A. Catalogue, sizes, fetch** | 415 | none (done, and `fetch`) | none | nothing: 2.5 GB on disk, about half an hour |
| **B. The control points of each base sheet** | done for the 1:1,000,000 plate (81 towns, 211 days), north Germany (26 crossings, 12 days) and the 1:1,400,000 sheet (60 crossings, 31 days; its red-overprinted printing from 20 May, B15, is read from its own scan); left: the eight 1944 sheets to 5 September | none: the conic fit, `sheet_towns.py --graticule` and the `bases` step are built | one reader per base, two passes of about two minutes (about 250,000 tokens a sheet); the two-day sheets of August 1944 only when an engagement wants them | a few dollars a base |
| **C. Every day's front** | 415 | B | the front job: a reader a day, 15 calls | low hundreds of dollars, a week of five readers at a few hours a day |
| **D. Symbols where they matter** | the engagements' windows, the Bulge (16 December – 25 January), the Rhine crossings (7–31 March), the landings (6 June – 31 July): about 120 days | C | the symbols job: a reader a day, 40–60 calls | low hundreds of dollars |
| **E. Symbols everywhere** | the other ~300 days | D | the same | several hundred to a thousand dollars; 20,000 symbols to review |

A is done but for the fetch; B is done for every sheet from 6 September 1944 to the end (the 1:1,000,000 plate from
its towns, north Germany and the 1:1,400,000 sheets from their graticules), and what remains of it is the 1944 sheets,
each the same job: `sheet_towns.py crops --graticule` round a conic seeded by three or four crossings read on the
sheet's margins, a reader's pass or two, `accept`. Do them as their days are wanted: the Normandy sheet (B01) for June,
the rest of August only for an engagement there. Then C as the first long run, D by engagement as the kit's
Army units are followed into those days, and E only if a page wants it: a front line on every day is the context the
engagement pages need; the enemy's divisions on a quiet Tuesday in Lorraine are a catalogue nobody has asked for.

What B needs in the tool, in order:

1. Done (6 November 2026): `sitmap_bases.py` fetched each day's overview (IIIF, 12.5 %, 64 MB in all), grouped the
   days by phase correlation of their line work (each day joins the earlier day it matches best, or starts a base), and
   wrote each day's base into the catalogue; the fifteen groups were checked on contact sheets and are described in
   `records/fronts/bases.yml`. `sitmap_bases.py check` then matched 7 March's towns on the first day of each
   1:1,000,000 group: 20 of 20 on 6 September 1944, 19 of 20 on 21 March 1945, 0 of 20 on 7 April 1945. The scan sizes
   alone don't tell: the trims vary day to day. The whole step cost one small worker and no reading of the maps.
2. Done for the 1:1,000,000 plate (6 November 2026): `records/fronts/towns-B11.csv`, 81 towns across the sheet
   (`tools/sheet_towns.py`). The fit is the sheet's own projection, a conformal conic with an affine to the scan
   (`trace_front.Conic`, tested in `test_fronts.py`): fitted to the March twenty alone it put a town at the sheet's far
   edge within 40 px of its ring, so the tool cropped the sheet round the conic's prediction for 103 candidate towns
   (geocoded with Nominatim) and a reader read each ring's centre off a 20 px grid; 61 were read, the rest were under
   the overprint, drawn as an area or off the sheet. With 81 towns the conic fits at 0.72 km rms, 0.75 km leave-one-out,
   1.8 km at worst (Turnhout), over the whole sheet; a day's trace from these covers the sheet. A ring finder by
   template matching was tried first and lost to letters' bowls and road junctions: the reader does it at a glance, in
   two passes of a minute each. A day takes the conic once it has 30 points or more, or any graticule crossing
   (`make_fit`); the March twenty stay for the March days (their GeoJSON must not move).

   **Better than towns: the sheet's graticule.** The sheets print a meridian and a parallel every degree, and a
   crossing is an exact control point: no geocoder's centroid (a city's is a kilometre from its ring), no name to
   match, nothing to look up. `sheet_towns.py crops --graticule` makes the candidates itself and labels each crop with
   the crossing's name; a new sheet is seeded by three or four crossings read on its margins, where the degrees are
   printed, or by a sister sheet's crossings shifted by the two scans' offset (`sitmap_bases.py check` prints it). The
   first pass from rough seeds reads a dozen crossings (the parallels are faint); the second, from the fit to those,
   has the crossing under the cross and reads most of the rest. Done this way on 6 November 2026 for the north
   Germany sheet (B13, `towns-B13.csv`: 26 crossings, 0.50 km rms, 1.1 km at worst, which register on 13 April at 25 of
   26) and the 1:1,400,000 sheet (B14, `towns-B14.csv`: 60 crossings, 0.82 km rms, 1.8 km at worst, which register on
   1 May at 57 of 60), each two reader passes of about two minutes. The 1:1,000,000 plate's crossings agreed with its
   towns' fit within 10 px, so `towns-B11.csv` stands.
3. Done: `--gcps-from towns-B11.csv` matches the sheet's towns on any day of the plate (22 December 1944: 71 of 79
   within 4 px of one affine transform, the rest placed through it), and the trace covers the sheet.
4. A `--base` overview in the work folder of each day so a reviewer can see at a glance where the front is on the
   sheet before opening the overlay.

## 6. What stays as it is

The rules in the skill and the README hold at any scale: a tick counted only as the map draws one; the map ticks its
own side; every blue line must be front; labels as written; a list is a list; every hand decision with its reason; the
front's `how` on every run and `fit_km` on every feature, so the page can say what is ours. Nothing a reader does is
checked by another reader: the checks are the tool's (the towns' agreement, the sides test, `unsure`) and the
reviewer's eyes on the overlay. Repetition isn't corroboration, on a map as in a record.
