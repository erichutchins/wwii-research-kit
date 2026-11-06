---
name: trace-situation-map
description: >
  Trace a dated situation map (HQ Twelfth Army Group's daily maps, Library of Congress) into records/fronts/: read its
  title and write the day's YAML, fetch the scan, fit it to its towns by matching another day's sheet, trace the front by
  its ticked stretches and check every tick on the overlay, find and read the unit symbols as drawn (the bridgehead list
  as a list), write the units file and the generated GeoJSON, and check the sides. Use when asked to add a day's
  situation map, the front or the divisions on a day, or to extend an engagement's `fronts:`. For many days at once,
  guides/SITUATION-MAPS.md gives the order of work and the agent orchestration.
---

# Tracing a day's situation map

The files and what each column means are in `records/fronts/README.md`; read it first. The collection (415 days, 6 June
1944 to 26 July 1945) is catalogued in `records/fronts/sitmaps.csv` (`tools/loc_sitmaps.py`); a map is named
`12ag-YYYY-MM-DD`. Everything runs through one tool, `tools/trace_front.py` (its docstring says how it works). Its
working images go to `sources/fronts-work/<map>/` (git-ignored): you read them with the Read tool.

What you read and decide by hand for a day goes in **the day's YAML**, `records/fronts/<map>.yml`: the title as read,
which day's towns its own are matched to, and every box, flip and check with its reason. Never in the tool. That is what
lets several readers work days at once without touching one another's.

## 1. The title, and the day's YAML

```bash
uv run tools/trace_front.py 12ag-1945-03-08 --title      # the title block, from the Library's image service (no scan yet)
```

Read `title.jpg`. The sheets' wording changes through the collection: "TO ACCOMPANY G-3 REPORT NO. 276 / SITUATION AS
OF 081200 MAR. 1945" (1945), "SITUATION 1200 HRS 22 DECEMBER 1944 / TWELFTH ARMY GROUP" (late 1944, no report number),
"SITUATION - 2400 HRS 6 JUNE 1944 / HQ FUSAG" (June 1944, a 1:500,000 sheet of Normandy). The day must agree with the
catalogue's; if it doesn't, stop and report it. If the title stands elsewhere than the top left, give the region:
`--title X Y W H`.

Write `records/fronts/<map>.yml` from what the title says (the tool prints a skeleton): `as_of` as the sheet gives the
day and hour, `report` where there is one, `title` as read, `read` with the date you read it, `gcps_from` (below). Then:

```bash
uv run tools/trace_front.py 12ag-1945-03-08 --fetch      # the scan, about 6 MB, cached under sources/maps/loc/
```

## 2. The towns

```bash
uv run tools/trace_front.py 12ag-1945-03-08 --gcps-from       # matched to the YAML's gcps_from (both scans needed)
```

`gcps_from` is the base's `towns` in `records/fronts/bases.yml`: `towns-B11.csv` for any day of the 1:1,000,000 plate
(6 September 1944 to 6 April 1945; 81 towns across the sheet, so the trace covers the sheet), `towns-B13.csv` for
7–18 April 1945, `towns-B14.csv` for 19 April to 19 May and `towns-B15.csv` from 20 May (the sheets' graticule
crossings, 26, 60 and 58), `towns-B01.csv` to `towns-B08.csv` for the 1944 sheets to 5 September (their crossings, or
their margin ticks where the sheet draws no graticule inside), or a day's
name whose twenty were read by eye (the March days use `12ag-1945-03-07`, and keep their polynomial fit).

The daily sheets are printings of one base map for months at a time, so a day's towns are found by matching the rings
of a day already read. Match to a day whose towns were **read by eye** on that base sheet: the day's `base` in
`sitmaps.csv`, and that base's `towns` in `records/fronts/bases.yml` (on 22 December 1944 the sheet's 79 agree 71
within 4 px, the March twenty 20 of 20). It must report at least 12 towns agreeing (or six in ten, for a sheet with few crossings); a town off the transform is placed through it and says so. Don't edit the gcps
file by hand.

**A base without `towns` in `bases.yml`** (the 1:500,000 and 1:750,000 sheets of June–September 1944, north Germany
7–18 April 1945, the portrait 1:1,400,000 sheet from 19 April; `tools/sitmap_bases.py check` tells for a doubtful one)
has no points to match to (only the double sheet of 10 September 1944 now). Its control points are read once, across
the sheet, from its own graticule: the degree labels on its margins, where each labelled tick meets the neat line, to
seed the conic (`1W 2460,330`, `49.5N 60,2210`), then `tools/sheet_towns.py crops --graticule` round the conic's
prediction for every crossing on the sheet and a reader's pass or two over the crops (`guides/SITUATION-MAPS.md` §5),
into `records/fronts/towns-<base>.csv`, and `bases.yml` says so. A sheet that draws no graticule inside the map is
fitted on its margin ticks (`accept` on the margins file). Crossings spread over
the sheet, not a corner of it: the trace covers the points' spread and nothing outside it.

## 3. The front, and the check

```bash
uv run tools/trace_front.py 12ag-1945-03-08 --overlay --sides
```

Read `overlay-sheet.jpg` first: the whole traced area, small, enough to see where the front runs and which stretches
are magenta. Then read the overlay in parts (`--overlay /tmp/x.jpg --crop X Y W H`, scan coordinates on its edges;
`overlay.jpg` is the whole sheet at full size, too big to read at once). What to check, and what was learnt the hard way:

- **The 12th Army Group ticks its front on its own side** (the US side), not the enemy's: the legend's sample, and every
  stretch, has the US divisions on the ticked side. The red ticks the overlay draws (each run's right) must fall on the
  map's own ticks, on the US side. A run whose red ticks fall on the German side is turned the wrong way.
- A tick is counted only as the map draws one: a short stroke as dark as the line, attached to its edge, ending on paper.
  Darkness alone failed twice: the Rhine's blue is dark at its edge, and on a lighter sheet (10 March) the grey roads
  beside the front along the river passed for ticks and turned whole reaches the wrong way. If a reach along a river comes
  out wrong, look there first.
- Stretches that meet two at a time are one line and are turned together by their summed ticks (`line` in the output);
  a fork breaks the chain. A corridor's head is a short heavy arc, often set apart from its sides by the division's own
  symbol, with no ticks: it comes out `unsure`, and is usually ticked inside (the US side) once you look.
- Every blue line must be front. Across a whole sheet three kinds of heavy ink are not, and each is left out with a box
  in the YAML's `exclude` (a stretch is left out when its middle falls in a box; keep a box off the front's own
  stretches): **the title block's lettering** (top left on the 1:1,000,000 sheet: "SECRET", the situation's date, and
  from 1945 the report number and a signature), **the legend** (bottom left: U.S., British, Enemy and a sample of the
  front line, ticks and all), and **boundaries drawn heavy with no ticks** (army group boundaries, and an army
  boundary's last stretch to the front). Their places vary day to day: the title and legend are lettered by hand on
  each sheet. On 22 December 1944 (`records/fronts/12ag-1944-12-22.yml`, traced by hand to settle this) eleven boxes
  did it: the title, the legend, the First Canadian/Second British army boundary, the Twenty One/Twelfth army group
  boundary from Louvain to the front at Geilenkirchen (three boxes), the Twelfth/Sixth from south of Nancy along the
  Marne-Rhine canal to Sarrebourg and on to the front (three), the First/Third's end at Sierck, the Seventh/First
  French's stub on the Rhine, and one enemy division's box. A boundary is a heavy black line with no ticks either side
  (the grey ticked lines beside it are railways): `--look` at it before leaving it out.
- A magenta stretch, marked `?`, couldn't be told from its ticks or its neighbours. Look at it (`--look X,Y`): if it runs
  the right way (the map's ticks on its right), add it to `checked`; if not, to `flip`. Each with its reason.
- `--sides` runs the page's own side test on the towns: each should be on the side of the front the map shows it on
  that day (the west bank US, the east bank German, a corridor's inside US). One that isn't points to a wrong stretch
  (Neuwied, on the east bank by the corridors' heads, has caught most of them). A town whose ring sits under the line
  (Bad Godesberg, Königswinter, Cochem) can read either way: that is the line, not an error. The test only means
  something where the front runs through the towns' spread: a day whose front lies outside it (22 December 1944
  against the March towns) puts every town on one side, and the few stretches inside are fragments.
- **A town on the wrong side is a wrong stretch until shown otherwise.** Each line of `--sides` ends with the runs
  that decide the town (the overlay's numbers), each with its own side and its middle on the scan: `Zweibrücken own
  (US) by run 33 own at 4813,4157, ...`. The run whose own side is wrong is the one to look at, and its middle is the
  point for `flip`. Don't call a town far from the line a "test artefact" without that look: on the first five whole
  sheets (16–20 December 1944) three such towns, put down by their readers to the line's open end or the test, were
  each a stretch turned the wrong way (the Colmar pocket's west side, the Saar line toward Bitche, the Walcheren arc).
  The true artefact is rarer: a town off a corner of the line, where the two legs disagree and the test weighs them
  (Landau, off the corner where the Lauter front meets the Rhine). Check that too by the runs named.
- A `checked` stretch is a claim that the map's ticks were seen on the overlay's red ticks. At a small scale they are
  easy to misread; if `--sides` disagrees, believe `--sides` and look again, close (`--overlay /tmp/x.jpg --crop` a
  few hundred pixels, enlarged).
- A blunt dead-end spur with no ticks on either side can't be read: leave it out with a box, and say why.

Run the trace again after each change to the YAML until the overlay is right and nothing is `unsure` without a reason.

## 4. The unit symbols

```bash
uv run tools/trace_front.py 12ag-1945-03-08 --boxes      # boxes.jpg (numbered crops), boxes-overview.jpg, boxes.csv
```

Read every numbered box on `boxes.jpg` (on a whole sheet, its pages `boxes-1.jpg`, `boxes-2.jpg`, ...; the finder also
numbers the title's letters and other lettering: skip those, they are not symbols), then find the symbols the finder
missed on `boxes-overview.jpg` (on a whole sheet its tiles, `boxes-overview-1a.jpg` ...; unmarked boxes: usually one
touching its number or a line; about one in five) and read their scan coordinates off its edges. A label cut off at a
crop's edge is read on the overview. Magnify a
hard one with `--look X,Y ...`. Write what you read to `sources/fronts-work/<map>/reading.txt`, one symbol a line:

```
3 us xx armored 3              # box 3: a US armored division, "3"
12 de xx infantry 363          # a hatched (enemy) box with a cross
21 de xx infantry 272 list:bridgehead   # in the map's list facing the bridgehead: a list, not a place
@4880,1537 de xxxx - FIFTEENTH # missed by the finder: its centre on the scan; `-` for no arm (a headquarters)
```

As written, nothing more:

- `of`: `us` an open box, `de` a hatched box (the map's "Enemy", hatching both ways), `uk` the map's "British" (a box
  with broken, dashed hatching). Where a label marks the unit's own nation in a US or British box, that nation:
  `ca` ("CDN", "4 CDN"), `pl` ("POL"), `fr` ("2FR", "II FR"); the label stays as written. A grey road under an open
  box can look like hatching: look closer.
- `echelon`: the marks over the box, `x` brigade, `xx` division, `xxx` corps, `xxxx` army, `xxxxx` army group, `xxxxxx`
  the C in C. A corps or above carries its name inside the box.
- `arm`: `infantry` (crossed), `armored` (oval), `armored-infantry` (both), `airborne` (the curved mark), `unread` when the
  mark can't be made out, `-` for a headquarters.
- `label`: the designation exactly as written, its qualifier included: `9(-)` (less some units), `1(+)` (with others
  attached), `(ELMS)`, and the map's own `?`; `?` for a figure you can't read (don't fill in a number from another day).
  A qualifier is often written under or beside the number and can sit nearer a neighbour's box: read whose it is. The
  same division can be written differently on different days. The tie to the kit's units ignores the qualifier.
- From 10 March 1945 the map lists the enemy divisions facing the Remagen bridgehead: first a bracketed column at the
  sheet's right, from 14 March also a box ("BRIDGEHEAD N.-S.") with the bracketed column beside it, joined by a line to
  the bridgehead's south side. Every symbol in either is `list:bridgehead`, never a position. The column stands at about
  x 5210, past the overview's right edge on some days: look for it there (`--look 5215,2320 5215,2470`). Another day's
  sheet may list units the same way elsewhere: a bracket or a box joined to the line by a leader is a list.
- Read what the map draws in the traced area (the overview's extent), both sides, every echelon.

```bash
uv run tools/trace_front.py 12ag-1945-03-08 --units sources/fronts-work/12ag-1945-03-08/reading.txt
uv run tools/trace_front.py 12ag-1945-03-08 --check-units   # units.jpg: every symbol magnified beside its reading
```

Read `units.jpg` through once more against the map: it is where the qualifiers you missed show. Correct `reading.txt`
and write the units again; the reading is the source the CSV is made from.

The tool ties a US symbol to the kit's own units where that is certain (`UNIT_IDS`: the 9th Armored, the corps, the
armies); nothing else is tied.

## 5. Into the engagement

Add the map to the engagement's `fronts:` (in date order), then `uv run tools/build_engagement.py`, and look at the
page on that day (`engagement.html?e=<id>&on=1945-03-08`): the front, the symbols, the sides' marks, the list under the
map, light and dark. Update the table in `records/fronts/README.md` and `used_for` in `SOURCES.yml`. `check_sources.py`,
the lint and the smoke test must pass. A change in `records/` is public: no relatives' names.

## Working as one of several readers

When days are traced in parallel (the agent `situation-map-reader`, one day a job; `guides/SITUATION-MAPS.md`), each
reader writes only its own day's files (`<map>.yml`, `<map>-gcps.csv`, `<map>-units.csv`, `<map>.geojson`, its work
folder) and reports back as the agent's definition asks; the session bringing the days together reviews each, enters
the engagement's `fronts:` and the README's table, and commits. Nobody edits the tool for a day's sake. Before committing a run it runs
`tools/check_fronts.py FIRST LAST`, which sets each day beside the days either side and names a town whose side
changed for one day only, a stray stretch far behind the line (a town suddenly much nearer the front) and a front much
shorter than its neighbours'.
