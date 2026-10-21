# Methods: from patrol report scans to an interactive record

How the USS BANG (SS-385) data in this repository was collected, transcribed,
checked, enriched and presented. Written so the same process can be repeated
for other submarines, by a person or by Claude.

The work was done in October 2026 using Claude (Anthropic) in Claude Code:
Claude read the page scans and wrote the code. Every number on the pages traces back to a specific
scanned page, and every correction to the 1944–45 originals is recorded next
to the value as it was typed.

---

## 1. Collecting

### What survives, and where

| Record | Where | Online? | Used |
|---|---|---|---|
| **War patrol reports**: the captain's report of each patrol (narrative, contact tables, attack sheets, density layers, weather) | NARA catalog series 305243 "U.S. Submarine War Patrol Reports" (listed under record group 367, "Records of the Office of the Chief of Naval Operations"), microfilm publication **M1752** | Yes, Fold3 scans of the microfilm, about 2460×3217 px per page | **Primary source** |
| Second copies of the same reports | RG 38 "World War II War Diaries, Other Operational Records and Histories" | Yes | Not yet (a cross-check source for illegible pages) |
| Muster rolls (crew lists) | RG 24, series 594996 | Yes (Ancestry scans) | No (out of scope for now) |
| Deck logs (hour-by-hour logbooks) | RG 24, series 594258 "Logbooks of U.S. Navy Ships and Stations" | **Only from 1951 on**; WWII-era submarine deck logs are not digitized | No |

The 2011 file `SS-385_BANG Deck Log.ocr.pdf` (not in the repo) is the
same war patrol reports, from microfilm reel AR-51-78, not the deck logs.
Its OCR text was too garbled to use for numbers. The new scans were
re-read from scratch.

### The catalog API

The National Archives catalog's web front end calls an unauthenticated JSON
endpoint:

```
https://catalog.archives.gov/proxy/records/search?naId=<catalog id>
https://catalog.archives.gov/proxy/records/search?q="USS Bang"&limit=100
```

A record's `ancestors` give its record group and series, and its
`digitalObjects` list every page's public JPG URL. `tools/nara.py` wraps
this:

```bash
python3 tools/nara.py find "Bang"                  # list the boat's folders
python3 tools/nara.py fetch 74802746 74802784 ...  # download scans to sources/nara/rg367-<id>/
python3 tools/nara.py index                        # records/scans.json: page -> public URL
```

BANG's six patrols are in five folders. Patrols 4 and 5 share folder
74802868: Patrol 4 is pages 2–37 and Patrol 5 is pages 38–65. In total
that is 226 pages, 577 MB. Scans are **not committed**. They can always be
re-downloaded, and the web pages load a page from NARA when there is no
local copy.

### Anatomy of a 1944–45 patrol report

Reports after late 1943 follow a fixed format, which is what makes this
work repeatable across boats:

| Section | Contents | What we take from it |
|---|---|---|
| Endorsements, roster | Cover letters, officer and crew list | (crew names, not used yet) |
| (A) Prologue, (B) Narrative | Day-by-day log with times and zone letters | Dives, surfacings, depth orders, depth charges, weather, the captain's words |
| (C) Weather, (D) Tidal information | Summaries | Context |
| (E) Navigational aids, (F) Ship contacts | Table: time, **position of the target**, type, range | Positions (marked as the target's, not BANG's) |
| (G) Aircraft contacts | Table: time, **BANG's position**, plane type, range, BANG's speed and course | Positions |
| (H) Attack data sheets | One per torpedo attack: time, position, torpedoes, target | Attack positions |
| (I)–(N) Mines, anti-sub measures, major defects, radio, radar, sound | Text | Radar-intercept logs give positions (Patrols 4–6) |
| **(O) Density layers** | Bathythermograph table: time, position, isothermal depth and temperature, negative-gradient depth and temperature | Daily positions **and** water temperature by depth |
| (P)–(R) Health, personnel, miles and fuel | Text and tables | Cross-checks (fuel table has distances) |

Patrol 6 (a different captain) logged a "Posit" (position) every day at noon
in the narrative instead of a daily density-layer reading.

---

## 2. Transcribing

### Why not OCR

The 2011 OCR text read 19°26′N as `19-2611`, 119°12′E as `1195-12E`, and
column alignment was lost entirely. For tables of numbers that is useless.
Instead **Claude read each page image directly** (Claude can read images)
and typed what it saw into CSV, one table at a time.

### Workflow per patrol

1. **Find the pages.** Make a contact sheet of every page in the folder
   (`crop_pages.py sheet <id>`). Tables are easy to spot at thumbnail
   size: the dense grids are contacts and attack sheets, and the
   four-column table near the end is the density layers.
2. **Crop for reading.** Read each page as overlapping top and bottom
   halves at 1800 px wide (`crop_pages.py halves <id> <pages…>`).
   Faded cells get a contrast-stretched zoom (`crop_pages.py zoom`).
   Whole pages are too dense to read reliably in one view.
3. **Transcribe exactly as typed.** Write the date, time, zone letter,
   latitude and longitude as they appear on the page, plus the page number
   (`rg367-74802746/p16` means `sources/nara/rg367-74802746/p16.jpg`).
   Mark an unreadable digit with `?`. Never "fix" while typing.
4. **Check.** Run `uv run tools/check_track.py bang/N`, then resolve every
   flagged leg (see §3).
5. **Record corrections separately.** Put a correction in
   `lat_fix`/`lon_fix`/`date_fix`/`time_fix`, with the reason in
   `fix_note`. If a fix contradicts its neighbours and the error can't be
   identified, set `on_track=no`. It stays on the map as a dashed ring but
   is left off the track line.

What was transcribed:

| File | Rows | From |
|---|---|---|
| `records/boats/ss-385-bang/patrol-N/positions.csv` | 321 positions, 315 usable | Density-layer, aircraft, ship-contact and radar tables, attack sheets, noon positions, port arrivals and departures |
| `records/boats/ss-385-bang/patrol-N/depths.csv` | 408 log entries | Every narrative page: dives, surfacings, depth orders, "passing" depths, depth charges, routine summaries |
| `records/boats/ss-385-bang/patrol-N/layers.csv` | 83 readings | The density-layer tables |

Column definitions are in [`records/README.md`](README.md).

### Conventions that matter

- **Times are kept in the zone the report used.** The reports use US Navy
  zone letters: Z = GCT (Greenwich), K = −10, I = −9, M = −12, Y = +12,
  X = +11, W = +10, VW = +9½. Navy "−10" means local time is GCT + 10.
  Boats changed zone as they moved west, and some tables are in GCT while
  the narrative is in local time, so every row carries its zone.
  Conversion to UTC happens in code (`check_track.py`, `ZONES`).
- **Ship-contact positions are the target's position**, not the
  submarine's. They are kept for the map but never used for the track.
- **Port positions** (Pearl Harbor, Midway, Saipan, Guam) aren't in the
  reports. Standard harbor coordinates are used and the note says so.
  Arrival times not given are set to noon, also noted.
- **"Passing" depths** ("first depth charges as we passed 350 feet") are
  depths the boat went through, not depths ordered. They're a separate
  event type so the depth line doesn't turn back at them.
- **Missing times.** When the narrative gives no time ("went deep"), the
  row gets the best estimate and the quote says why in parentheses.

---

## 3. Checking

### The speed check

`tools/check_track.py` converts every fix to UTC, sorts them, and flags
any leg BANG couldn't have sailed: more than 20.5 knots (Balao-class
surfaced top speed) plus 30 nm for navigational error. Every flagged leg in
all six patrols was resolved, with the reasoning recorded:

| Patrol | Problem as typed | Resolution |
|---|---|---|
| 1 | 24 Apr latitude 28-56N (mainland China) | → 20-56N, which fits fixes before and after at ~3 kt |
| 1 | "3 May 2015" bathythermograph reading, 122 nm from an attack 3 h earlier | → 2 May; fits aircraft contacts 8–9 |
| 1 | 30 Apr latitude typed "19-25E" | Read as 19-25N |
| 2 | 10 Jun time 2317, then 27 kt to the next fix | → 0317 (all other outbound readings ~0300–0400 GCT) |
| 2 | 25 Jun longitude 141-40E, between fixes at 121°E | → 121-40E |
| 2 | Five aircraft/temperature-reading fixes contradict their neighbours | Kept, off the track |
| 3 | 24 Sep reading typed with local date | → 23 Sep (matches an aircraft contact 2 min earlier) |
| 4 | Aircraft contact 12 longitude typed 122 over 123 | 122, which matches a radar fix 35 min earlier |
| 5 | 15 Feb radar fix 70 nm from three agreeing aircraft fixes | Kept, off the track |

### Independent cross-checks

These outside sources agree with the transcription and the code:

| Check | Report says | Independent value |
|---|---|---|
| Seafloor where Patrol 5 "sat on the bottom" (12 Feb 1945) | 228 ft | ETOPO1: 210 ft |
| Moonset, night of 29–30 Apr 1944 | 0222 | Computed: 0222 |
| Moonset, night of 3–4 Jul 1944 | 0445 | Computed: 0443 |
| Night of 18 Apr 1944 "moonless" | — | Computed: moon down 1524–0446 |
| Wind rising to force 5 from N, night of 1–2 May 1945 | — | ERA5: 24 kn from NE by morning |
| Patrol 6 "miles steamed" table: Guam→area, area→Saipan, Saipan→Pearl | 1,474 / 1,584 / 3,520 nm | Track: 1,427 / 1,472 / 3,244 nm (3–8% short, as straight lines between noon fixes should be) |
| Same table, "in area" | 5,555 nm | Track: 1,540 nm. Daily noon fixes miss the back-and-forth patrolling, which is why distance on station is a minimum |

---

## 4. Enriching with outside data

| Data | Source | Script | Notes |
|---|---|---|---|
| Seafloor depth | NOAA **ETOPO1**, 1 arc-minute, via NOAA CoastWatch ERDDAP (`etopo180`) | `fetch_seafloor.py` | Sampled every 2 nm along the track. Fetched as 1°×1° tiles and cached in `sources/etopo1/` (636 tiles, 12 MB) |
| Weather | **ERA5** reanalysis (ECMWF, 0.25°, hourly, 1940–), via the Open-Meteo archive API | `fetch_weather.py` | Wind, gusts, cloud, rain, air temperature, pressure at the boat's position, 4 positions per day. Cached in `sources/era5/`. The Open-Meteo marine API (waves, sea temperature) has **no** 1940s data |
| Sun and moon | Computed in the browser (low-precision almanac formulas, about 1°) | `dives.js` | Sunrise/sunset, twilight, moon phase, moonrise/moonset at the interpolated position |
| Earthquakes | USGS ComCat (includes ISC-GEM), ISC bulletin (FDSN), Taiwan CWA catalog | (one-off search) | Nothing found for the 2 May 1945 rumble. See `records/README.md` for why that's expected |

### The Japanese side

The strongest check on an attack sheet is the target's own record. JACAR
(Japan Center for Asian Historical Records) puts the Defense Ministry's
Imperial Navy archive online free: war diaries, action reports, convoy
escort statistics, and the movement logs that masters of navy-controlled
merchant ships kept. `tools/jacar.py` searches it and downloads a
record as a PDF of page scans (no text layer).

| Record type | What it gives |
|---|---|
| Designated-ship movement tables (指定船舶行動表) | One ship's ports, dates and cargo, and for a lost ship, the master's or a survivor's account of the sinking, with time and position |
| Escort division war diaries (海上護衛隊戦時日誌) | Narrative of the month; a day-by-day chart of each escort's convoy; an attached table listing convoys that met submarines and every ship lost, with tonnage |
| Guard district war diaries (警備府戦時日誌) | Radio log: air patrols, convoy cover, weather |

How it was done for Patrol 1:

1. Identify the convoy from secondary sources (combinedfleet.com ship
   records name convoys, escorts and sinking times).
2. Search JACAR for the escort command's war diary for that month and the
   ship's movement log (`jacar.py search "日達丸"`). Search reaches OCR
   text but matches loosely, so check every hit.
3. Read the page images. Printed pages read well at 110 dpi. Handwritten
   tables need 200–300 dpi crops, and horizontal text of the period runs
   right to left (`(七一マタ)` is タマ一七, TAMA-17).
4. Transcribe into `japanese.csv` as written, with a translation and the
   page, and pair the records with attacks in `crossrefs.csv`.
5. `check_crossrefs.py` converts both sides to GMT and reports the gaps.

Patrols 2–4 added two lessons:

- **Which command kept the convoy.** Trunk convoys (HI-, MI-, TAMA-) are in
  the 1st Surface Escort Division's diary, whose monthly route charts mark
  each attack with time and position. Local convoys off Formosa and the
  Nansei Shoto (TAKA-, KATA-) are in the 4th Surface Escort Division's diary
  and in the war diaries and battle reports (戦闘詳報) of the individual
  escorts, which log the attack minute by minute. Get the escorts' names
  from combinedfleet.com, then search JACAR for the ship
  (`jacar.py search "第三十号海防艦"`). Merchant names written in kana
  (さらわく丸) are not in JACAR's search text; search for the escort or diary.
- **Reading without rendering.** If pages can't be rendered locally, read
  them in JACAR's own viewer, a PDF.js page at
  `/bundles/apps/pdfjs/web/viewer.html?file=…` (the path is in the iframe on
  `/das/image/<code>`). Its page numbers are the PDF's, the same as `pNN`.

The Imperial Navy kept Tokyo time (zone I, −9). With that assumption,
Nittatsu Maru's log and BANG's attack sheets agree to 1–7 minutes on four
attacks; see `records/README.md` for the table. The one large gap (86 minutes,
Attack 5) is against a secondary source.

US radio intelligence's own picture is in the FRUPAC war maps (National
Museum of the Pacific War, via the Portal to Texas History). Its search
pages are behind a bot check, but the catalog is harvestable through the
library's OAI-PMH feed (`https://texashistory.unt.edu/oai/`, set
`collection:FRUPAC`); `tools/frupac.py` does that and finds maps by ship
or date. Read the maps in the site's zoom viewer, which serves full-resolution
tiles (the page images are too small for the pencil). For each note near one
of BANG's attacks:

1. Copy the text as written into `frupac.csv`, with the message date-time
   group, the event time, and the zoom-viewer query that frames it.
2. Estimate the mark's position: against the printed 1-degree grid where the
   map has one; on bare tracing overlays, against the red meridian labels
   (`120`, `130`, …), assumed to sit on 20N. Write it in decimal degrees and treat
   it as ±0.1–0.3°.
3. Tie it to an attack with `match`, `candidate` or `context`, and say why.
   `check_crossrefs.py` prints the gap, reading the note's time as zone I.

Limits to keep in mind:

- **ETOPO1 along a straight line between fixes.** The real track wandered,
  especially on station. Near coasts and reefs, the seafloor under the
  interpolated line may not be what was under the boat.
- **ERA5 in 1944** rests on few observations in the western Pacific. Trust
  fronts, monsoon and typhoons more than exact winds, and trust the
  captain's notes over both.

---

## 5. Analysis

- **Track.** Straight lines (great circles) between the transcribed fixes
  in time order. Distance between fixes is a minimum: on station a boat
  zig-zagged all day between once-a-day fixes.
- **Course and speed "made good"** (map gauge). The average implied by the
  fixes around a moment, with legs widened to at least 2 hours so that
  attack-sheet fixes minutes apart don't give silly speeds. This is not
  speed through the water. On station it reads low (0.8 kn on 20 Apr 1944).
- **Depth over time** (`buildProfile` in `dives.js`):
  - Each logged depth is held until the next entry, changing at about
    100 ft/min.
  - A dive with no depth given is drawn at periscope depth (about 60 ft).
    Radar depth is about 40 ft.
  - Days summarised as "submerged during daylight" with no times are
    drawn as a sunrise dive and a sunset surfacing, hatched.
  - If a dive has no logged surfacing before the next night, the boat is
    assumed to surface 30 minutes after dark to charge batteries.
  - All assumed values are labelled as assumed in the tooltip.
- **Temperature layers.** A reading is drawn from its time until the next
  reading, at most 30 h. It shows warm water from the surface to the
  isothermal depth, then the cooling ("negative gradient") down to its
  stated depth.
- **Moments.** The jump-to buttons pick days with depth orders of 300 ft or
  more, depth charges, sitting on the bottom, or the earthquake.

---

## 6. Presenting

Two static pages with no build step: plain HTML plus [D3 v7](https://d3js.org)
from a CDN. Serve the folder with `python3 tools/serve.py`, which turns
caching off so edits show on reload.

| Page | What it shows |
|---|---|
| `patrols.html` + `patrols.js` | Map of every patrol, playback following the boat, course/speed gauge, patrol log, report-page viewer |
| `army.html` + `army.js` | Map of one Army unit at a time (`records/army/army.json`): its stations as typed, routes and sea crossings, Battery D's engagements, playback, station log, page viewer |
| `seabees.html` + `seabees.js` | Map of one Seabee battalion at a time (`records/seabees/seabees.json`): each part's line and where it was that day, ships along their logged positions, the day's weather, playback, station log, page viewer |
| `dives.html` + `dives.js` | Dive profile: depth, temperature layers, weather strip, seafloor, moon phases, playback, and a day-and-night chart with one row per day |
| `zones.html` + `zones.js` | Explainer: the Navy's lettered time zones over the Pacific, every position coloured by its typed zone, one moment on six clocks |
| `grids.html` + `grids.js` | Explainer (Europe): the five map grids in the Army records, their lettered 100 km squares, a decoder, and every reference checked against its named town |
| `viz.css` | Shared colour roles, controls, tooltip, scan viewer, explainer layout |

Design rules followed:

- **Every mark links to its source page.** Click a point or log row to see
  the scan, with a link to the same page in the National Archives catalog.
- **Raw and corrected values are both shown.** Tooltips give the value as
  typed and the correction with its reason.
- **Colour.** Three categorical colours (track blue, attack orange, aircraft
  and temperature-layer aqua) checked for colour-blind separation in light
  and dark mode with a palette validator. Shape distinguishes marks too
  (diamond = attack, triangle = aircraft, star = depth charges), so nothing
  depends on colour alone. Light and dark modes each have their own
  colours.
- **One axis per panel.** Depth, wind and seafloor each get their own
  panel and scale.
- **Assumptions are visible.** Hatched = not logged; dashed ring = left off
  the track; tooltips say "assumed".
- **Deep links.** `patrols.html?patrol=2&t=1944-07-04T04:42Z` and the same
  for `dives.html`. The two pages link to each other at the same moment.

---

## 7. Reproducing everything from scratch

```bash
python3 tools/nara.py fetch 74802746 74802784 74802831 74802868 74802934   # ~577 MB of scans
uv run tools/check_track.py all --geojson   # validate tracks, write GeoJSON
uv run tools/fetch_seafloor.py              # ETOPO1 along tracks
uv run tools/fetch_weather.py               # ERA5 along tracks
uv run tools/build_dives.py                 # bundle records/boats/ss-385-bang/dives.json
uv run tools/check_crossrefs.py             # attacks vs. Japanese records -> crossrefs.json
python3 tools/serve.py                       # http://localhost:8385/patrols.html
```

To re-read the Japanese records: `python3 tools/jacar.py fetch C08050103200 C08030140600 C08030140700 C08030512800`
(needs poppler's `pdftoppm` to render pages).
To list the FRUPAC maps for BANG: `python3 tools/frupac.py find "\bBang\b"`
(harvests the catalog into `sources/frupac/` on first use).

Only `nara.py fetch` is needed to view the scans locally. The generated
files in `records/` are committed, so the pages work right after cloning.
