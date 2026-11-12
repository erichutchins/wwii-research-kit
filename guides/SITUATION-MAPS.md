# The situation maps: the collection, and how a day is traced

The Library of Congress holds *World War II Military Situation Maps from 1944 to 1945*: 415 daily sheets from 6 June
1944 to 26 July 1945, drawn at the headquarters that became Twelfth Army Group (SOURCES.yml `loc-12ag`; the only day
missing is 12 November 1944). The sheets' own titles name the headquarters: "HQ FUSAG" (First U.S. Army Group) to 15
July 1944, "Twelfth Army Group" from 16 July. Each sheet is the staff's picture of a day: the front line as it was
drawn there, its own divisions and corps, and the enemy's as its intelligence placed them. For the engagement pages
they are context under the records (`records/fronts/README.md`): a symbol stands in its unit's area, not at a
position, and the line is a drawing at the map's hour, not a survey.

The front is traced on 365 days, every sheet from 6 June 1944 to 7 June 1945 but the double sheet of 10 September
1944; the unit symbols are read on 98 of them. The 49 sheets from 8 June to 26 July 1945 are not traced: they are
post-war sheets that draw the line of contact bare, with no ticked front (`records/fronts/README.md`). This guide says what the collection is, what tracing a day means, how a sheet is
fitted to the ground and how a run of days is checked. The steps for one day are the skill `trace-situation-map`;
running many days at once with reader agents is in the same skill ("Bringing a run of days together"). The
collection's numbers are from its catalogue (`records/fronts/sitmaps.csv`, `tools/loc_sitmaps.py`).

## 1. What the collection is

| | |
|---|---|
| Sheets | 415, one a day, 6 June 1944 – 26 July 1945; 12 November 1944 is not in the collection |
| Items | each a Library item (an LCCN) with one scan, resource id `ict21001` to `ict21417`, rising with the date (two ids unused) |
| Also catalogued | one composite sheet (the Bulge, `2001628569`, no daily scan) and the collection's own record, both left out of the catalogue |
| Scans | JPEG 2000, about 6 MB each (2.5 GB in all), about 6,650 × 5,980 px landscape to 18 April 1945, about 5,950 × 6,680 px portrait from 19 April (10 September 1944 is a double sheet, 13,008 px wide) |
| Service | the scan by one address on the tile server (no bot check); any region at any size by IIIF (`info.json`, regions by pixel, sizes by width or percent), a crop in under a second |
| Base maps | fifteen printings (`records/fronts/bases.yml`, B01–B15; each day's in `sitmaps.csv`, grouped by their overviews with `tools/sitmap_bases.py`; every one but the double sheet of 10 September has its control points, `towns-<base>.csv`): 1:500,000 sheets of Normandy (6 June – 4 August), then Brittany, the Loire, the Seine, changing every few days in August; a 1:750,000 sheet 2–5 September; one 1:1,000,000 plate of north-west Europe from 6 September 1944 to 6 April 1945, placed three ways on the paper (the March towns register on all three: 211 days from one reading); a 1:1,000,000 sheet of north Germany 7–18 April; a portrait 1:1,400,000 sheet of Germany from 19 April, with red boundaries from 20 May |
| Titles | the wording changes: "SITUATION - 2400 HRS 6 JUNE 1944, HQ FUSAG"; "SITUATION 1200 HRS 22 DECEMBER 1944, TWELFTH ARMY GROUP" (no report number); "TO ACCOMPANY G-3 REPORT NO. 275, SITUATION AS OF 071200 MAR. 1945" |
| Dates | the catalogue's date is the title's on every sheet checked (eleven in March, one in December, one in June) |

The fact that makes a long run possible: **the daily sheets are printings of one base map for months at a time**, so
one day's control points, read by eye once, are found on every other day of that base by matching. 7 March 1945's
twenty towns match 22 December 1944's sheet 20 of 20, at a median of half a pixel.

## 2. What tracing a day means

Six stages, in order. Three are a tool's alone; three need someone to look.

| Stage | Who | What |
|---|---|---|
| **Catalogue** | tool (`loc_sitmaps.py list`, `sizes`) | the listing and each scan's size into `sitmaps.csv` |
| **Fetch** | tool (`loc_sitmaps.py fetch`) | the scans into `sources/maps/loc/`, a second apart, resumable: 2.5 GB, about half an hour, once |
| **Title** | a reader (`trace_front.py --title`, from IIIF, before fetching) | the day's hour and report number read on the sheet; the day's YAML written |
| **Fit** | tool (`--gcps-from`) on a known base; a reader once per new base (§3) | the sheet fitted to the ground through its base's control points |
| **Front** | tool (`--overlay --sides`), then a reader | the heavy ink's stretches turned by their ticks; the reader checks the overlay, decides the few stretches the ticks don't settle (`flip`, `checked`, `exclude`, each with its reason) and reruns |
| **Symbols** | a reader (`--boxes`, `reading.txt`, `--units`, `--check-units`) | every unit symbol read as drawn: 40 to 70 a day on the March 1945 sheets, by far the longest stage |

The front and the symbols are separable: a day can have its line traced and no symbols read, and the page draws what
it has. Every day's front is traced; the symbols are read where an engagement or a followed unit needs them. A front
line on every day is the context the engagement pages need; the enemy's divisions on a quiet Tuesday in Lorraine are
a catalogue nobody has asked for.

## 3. Fitting a sheet to the ground

Each of the fifteen base printings (`records/fronts/bases.yml`) has one file of control points,
`records/fronts/towns-<base>.csv`, read once. Every base has one but the double sheet of 10 September 1944: two
plates pasted on one scan, each to be read as its own base from its own margins when that day is wanted.

- **The fit is the sheet's own projection**, a conformal conic with an affine to the scan (`trace_front.Conic`,
  tested in `test_fronts.py`), not a polynomial, which holds over a few degrees and not over a sheet. A day takes the
  conic once it has 30 points or any graticule crossing (`make_fit`). The control points must spread over the whole
  sheet: the tool traces only inside their spread.
- **Graticule crossings are better control than towns.** The sheets print a meridian and a parallel every degree (every
  half degree at 1:500,000), and a crossing is an exact point: no geocoder's centroid (a city's is a kilometre from
  its ring), no name to match. `sheet_towns.py crops --graticule` crops the sheet round the conic's prediction for
  each crossing, and a reader reads each centre in one or two passes.
- **A new sheet's first fit comes from its margins**: where each labelled meridian's tick meets the top or bottom neat
  line and each labelled parallel's the left or right (`1W 2460,330`, `49.5N 60,2210`). `conic_from_lines` solves
  these as a similarity: a free affine's shear is not pinned by two edges, and put a sheet's far corners degrees out.
- **A printing scanned differently gets its own file.** The May 1945 printing of the 1:1,400,000 sheet is 1.7 per cent
  larger on the scan than April's, and April's points register on it at 1 of 13.

How well each base fits (rms over its control points; `bases.yml` carries the caveats):

| Base | Sheet | Control | Fit |
|---|---|---|---|
| B01 | Normandy, 1:500,000 | 34 crossings | 0.14 km |
| B02 | Brittany, 1:500,000 | 31 crossings | 0.22 km |
| B03, B04 | the Loire, mid-August 1944 | 10 and 9 crossings | 0.6 and 0.5 km: the sheets' kilometre grid runs 50 to 100 px from the graticule and was taken for it in places |
| B05–B08 | 22 August – 5 September 1944 | 16, 11, 14 and 13 margin ticks (no graticule is drawn inside the map) | 0.14 to 0.48 km |
| B09, B11, B12 | north-west Europe, 1:1,000,000: one plate placed three ways on the paper (211 days) | 81 towns (`towns-B11.csv`) | 0.72 km; 0.75 km leave-one-out; 1.8 km at worst (Turnhout) |
| B13 | north Germany, 1:1,000,000 | 26 crossings | 0.50 km; 1.1 km at worst |
| B14 | Germany, 1:1,400,000 | 60 crossings | 0.82 km; 1.8 km at worst |
| B15 | its May 1945 printing | 58 crossings | 0.67 km |

The plate's towns were geocoded with Nominatim and each ring's centre read on a 20 px grid; the plate's graticule crossings
agree with that fit within 10 px. The March 1945 days keep their own twenty towns, so their committed GeoJSON does
not move. The days were grouped into bases by `sitmap_bases.py` (phase correlation of each day's line work at 12.5
per cent, checked on contact sheets); scan sizes alone don't tell one base from another, since the trims vary from
day to day.

## 4. What a whole sheet leaves out, and what goes wrong

Three things are boxed out of a trace by hand, each day, with a reason: the title block's lettering, the legend, and
boundaries drawn heavy with no ticks. The title and the legend are lettered by hand on each sheet and wander a few
hundred pixels, so neither can be boxed once for a base.

The errors found on review, in the 46 days from 16 December 1944 to 31 January 1945 (ten days corrected):

- a stretch turned the wrong way: the Colmar pocket's west side, the Saar line toward Bitche, the Rhine bank south of
  Strasbourg, the Walcheren arcs (five days);
- the Westwall band's outline taken for front (one day);
- boundaries traced as front far behind the line, which no town's side showed because the stray ink lay deep in the
  rear (four days);
- an `exclude` box drawn too wide, hiding a stretch of front beside the title.

## 5. Checking a run of days

Nothing a reader does is checked by another reader. The checks are the tool's, and the reviewer's eyes on the overlay.

- **The towns' agreement**: a day reports at least 12 control points agreeing with its base's.
- **The sides test** (`--sides`): every town falls on its own side of the front, and the runs that decide each town
  are named with their place on the scan. A town on the wrong side is a wrong stretch until a close look shows
  otherwise: of the first three so reported, two were stretches turned the wrong way.
- **The neighbours** (`tools/check_fronts.py FIRST LAST`): each day set beside the days either side. It names a town
  whose side differs from both neighbours', a town suddenly much nearer the front (a stray stretch behind the line),
  and a front much shorter than both neighbours'. Over the 46 days above, once corrected, it flags only Haguenau,
  whose ring sits on the Moder line from 22 January 1945. Run it on every run before committing.
- **The review**: a day that passes every check gets a look at its overlay's thumbnail and at each stretch it turned
  by hand; a day that fails one is read in full.
- **A new base sheet stops the run** until its control points are read (§3).

## 6. What stays as it is

The rules in the skill and `records/fronts/README.md` hold at any scale: a tick counted only as the map draws one;
the map ticks its own side; every blue line must be front; labels as written; a list is a list; every hand decision
with its reason; the front's `how` on every run and `fit_km` on every feature, so the page can say what is a
reconstruction. Repetition isn't corroboration, on a map as in a record.
