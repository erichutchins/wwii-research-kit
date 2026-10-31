# Engagements: two sides, each in its own records, on one map and one clock

An engagement is two sides meeting at a place and a time: a pack against a convoy, a destroyer against a kamikaze
strike, an antiaircraft battery against a night raid. Each side kept its own records, in its own form and on its own
clock. The kit keeps each record as it is and lets them meet through ids, times and places, never by copying one into
the other. Every engagement is one folder, `records/engagements/<id>/`, and one page, `site/engagement.html?e=<id>`.

The convoys the boats met have their own records (`records/convoys/<id>/convoy.md`) and pages: `site/convoys.html`
(the ledger, and each convoy's voyage and ships) and `site/lanes.html` (the lanes, month by month, and a voyage as a
timetable). Haynsworth and Algiers are also told as stories (`haynsworth.html`, `algiers.html`), read from the same
engagement.

Fields are in `records/README.md` ("An engagement", "A convoy", "A patrol's Japanese record");
`tools/build_engagement.py` checks them all and builds the JSON the pages read.

## What a page answers, at three scales

| Scale | Question | Where |
|---|---|---|
| Minutes and miles | What happened in the attack? | `engagement.html`: the map with a time slider, one lane per side, the two-sided log |
| Days and hundreds of miles | What was the convoy doing, and how did the boats close in? | `engagement.html` "Closing in"; `convoys.html`: the voyage map and the ships against the days |
| Months and an ocean | Where was the war at sea fought, and how did it move? | `lanes.html`: the network, month by month, a voyage's timetable |

## The rules this rests on

The kit's rules (`CLAUDE.md`, `guides/METHODS.md`) apply throughout. The ones that shape engagements:

1. **Cite every entry**: the build fails on an entry, a claim, a ship or a voyage stop without a citation that
   `SOURCES.yml` knows.
2. **Keep each record's own structure.** A war patrol report, an escort diary and an action report stay as
   transcribed, in their own folders. An engagement names its participants' records (`track: ss-385-bang/1`,
   `convoy: te-04`) and a window; their tracks, attacks, depth charges and Japanese records are read from there.
   `events.yml` holds only what belongs to the engagement alone.
3. **Computed, never stored.** Distances, positions between fixes, a convoy's path from its sightings, speeds along a
   lane, the sky, a firing solution: `site/engage.js` computes them on the page. What it computes is a lead until a
   record says so, and the page says which is which.
4. **Label every inference and assumption**, in the data (`basis`, `placed`, `assumed`) and on the page (below).
5. **Repetition isn't corroboration**: two secondary sites repeating one list count once.
6. **No numbers on conclusions.** `claims.yml` ranks nothing; it lists each answer with the kind of evidence for it.
7. **Name the other side as the records do.**

### Formats

Nothing hand-edited with words goes in CSV.

| Format | For | The test |
|---|---|---|
| CSV | numbers, dates, codes and short references, one value per cell (`positions.csv`, `depths.csv`, `layers.csv`) | no cell ever needs a quotation mark or a comma |
| YAML | structured records that carry words: `events.yml`, `claims.yml`, `japanese.yml`, `frupac.yml`, a convoy's `ships:` | several fields per item, and one of them is words |
| Markdown with YAML front matter | one thing with prose: `engagement.md`, `convoy.md` | someone will read it as text, or edit it on a phone |
| JSON | generated only (`engagement.json`, `index.json`, `convoys.json`); CI checks it is up to date | if you want to edit it, edit its source |

Quotes are typed as they are, never escaped. In prose, links are written by name, `[[kind:id|words]]` (`cite`, `op`,
`ship`, `unit`, `page`, `convoy`, `engagement`), and a name that doesn't exist fails the build. A file converted to a
new format is converted for good: no reader for the old one is kept.

## Making an engagement

1. **The tracks.** Each US participant's own record, transcribed and speed-checked: a boat's `positions.csv` (attack
   sheets as `source=attack`, ship contacts at the target's position, `on_track=no`), a ship's war diary
   (`check_track.py`, 0 too-fast legs). `depths.csv` adds depth charges and deep dives where it exists.
2. **The other side.** A patrol's `japanese.yml` (the records as written, with translations) and `claims.yml` (which
   attack goes with which record, and how: `hit`, `miss`, `probable`, `possible`, `no_loss`); `check_crossrefs.py`
   prints the minutes and miles between each pair. The skill `find-the-other-side` is the method. A convoy gets its own
   `convoy.md`: route, voyage, ships, each cited.
3. **`engagement.md`.** The participants (at most three with a US track: the page's checked colours), the window in
   GMT, map labels, and the story: a lede, then `##` sections (the outcome, the convoy as the boats saw it, reading the
   map, the clocks, the sources).
4. **`events.yml`** for what belongs to the engagement alone: a boat's narrative entries (contact reports with `to:`,
   messages received with `from:`), another record's entries (an air group's action report), and for an Army or a
   destroyer engagement, every entry of the day. **`claims.yml`** for the questions the records leave open.
5. **Build and look.** `uv run tools/build_engagement.py` (0 problems), `uv run tools/check_sources.py`, then the page
   in light and dark mode, with no console errors.

## Computation (`site/engage.js`, tested by `node site/engage.test.js`)

| What | How |
|---|---|
| A position as typed | `DD-MM.mN`; a `lat_fix`/`lon_fix` overrides; `?` in a digit means unreadable, so none |
| Zone to GMT | Navy letters: A–M (no J) east, +1…+12; N–Y west, −1…−12; Z = 0; the war diaries' half-hour zones. Japanese records are I (+9, Tokyo). Pages show GMT and the record's own time side by side |
| A bearing and distance | from a known point (`from`, `brg`, `nm` in `positions.csv`), resolved by the build |
| A track at a moment | straight between the participant's own fixes, never beyond the first or last |
| A convoy's observed path | where it was seen: the boats' ship contacts (the target's position) and the Japanese record's positions, one point per minute. A sighting the report itself contradicts (its `fix_note` says so) is left out, and listed under the chart |
| Closing in | each boat's distance from that path, only while both are known; after the last sighting, an attack means "within torpedo range", not a number |
| Speed along a lane | between a voyage's known points; a slow leg may be an unrecorded stop (a lead) |
| The sky | sun and moon, bearing, altitude, phase and lit fraction, from SunCalc |
| Fire control | torpedo course = own course + gyro; track = torpedo course + 180 − target course; lead L: tan L = k·sin TA / (1 + k·cos TA), k = target speed / torpedo speed; angle on the bow = track − L |
| Apparent size | width = 2·atan(projected length / 2R), projected length = L·\|sin AOB\| + beam·\|cos AOB\|; height = atan(H/R) |

## How the pages draw it

### Encodings, the same on every page

| Meaning | Encoding |
|---|---|
| From the record | solid |
| From a secondary source (combinedfleet.com and the like) | outlined, or an italic name |
| Inferred | hatched |
| Not recorded; an assumed route | dotted |
| Straight between known points, nothing recorded between | dashed |
| A ship sunk (the Japanese record) | red ✕ |
| A ship hit, not sunk | red ring |
| Attacked, no damage | open ink ring |
| A torpedo attack | diamond, in the boat's colour |
| A ship sighted | open ring in the boat's colour, at the target's position |
| A contact report | a ring on the sender's track, and a dotted line to each boat it went to |
| A time placed by the account's order | the time in italics, and the reason under the entry |

**Red is reserved for hits.** It is never a side's or a boat's colour.

### Colour

| Role | Light (paper #f6f5f1) | Dark (paper #141413) |
|---|---|---|
| The first US boat or ship | #2a6fc9 | #336cc0 |
| The second | #008f78 | #22a58e |
| The third | #6a3a9e | #a07fe0 |
| Hit | #c8323c | #e8525a |
| The Japanese side | ink (#1c1c1a / #ecebe5) | |

Checked with the dataviz validator, every pair, both modes. The older dark blue #5b93e0 passes with the teal and the
red but fails beside the purple, so it isn't used. More than three boats: small multiples or a picker, never a fourth
hue. Colour follows the boat across every view of a page; text never wears it except a boat's own label.

### Reading

- Labels only where they earn it: the ports, the boats' names, direct labels on at most three lines.
- Every mark has a tooltip; every entry links to its page, the scan where it is online.
- Times: GMT on the axes and the clock, with the record's own time and zone beside each entry ("0603 H", "1250").
  An engagement whose records give no zone (`clock` left out) is shown on its records' local time, and says so.
- Assumptions are said under the view they affect, not only in a page note.
- Silhouettes come from the kit's library (`records/silhouettes/`) at one scale, so plates compare true size: the
  ship's own or her class's plate where there is one (the tooltip says which, and whether a type stands for her),
  otherwise the kind of ship.

## Still to build

- **The observer view**: the periscope (or a ship's director, or a battery's sight) with the target at its true size and
  angle on the bow, the sky as computed, and the firing solution on the same clock. The family repository's
  `periscope-concept.html` is the prototype (SEAHORSE's Attack 3, 4 July 1944). Each attack's data sheet is now rows: a
  patrol's `attacks.csv` and `attack_sheets.yml` (fields in `records/README.md`, checked by `tools/check_attacks.py`);
  it still needs the narrative's timed bearings. For Haynsworth, the incoming plane's
  bearing, elevation and range from her action report and AA report play the same part.
- **The lanes from the charts.** Every waypoint in `reference/lanes/lanes.yml` is assumed. The escort divisions'
  charts draw and name the lanes (馬来直航路, the Malay direct route; the Hainan east route); tracing them would replace
  the assumptions.

## Open work, by engagement

- **TAMA-17 and TE-04** (`tama-17-1944-04-29`, `te-04-1944-05-03`):
  1. The FRUPAC notes (`ss-385-bang/patrol-1/frupac.yml`, F01–F10) as a third side, US radio intelligence, with its
     own lane and estimated positions.
  2. Who sank Kinrei Maru: a Japanese primary record (her movement log, or TE-04's escorts' reports: CD-1, Kazan
     Maru, Maeshima). The 3–4 May sinking times and attributions are still combinedfleet.com's.
  3. PARCHE's and TINOSA's depth logs (TINOSA: 55 depth charges on 3–4 May).
  4. Full-resolution FRUPAC scans from the museum (28 Apr – 5 May 1944, `metapth1733007`–`metapth1733014`, and the
     April and May summaries), with permission to georeference them.
- **HI-67, No. 91** (`hi-67-1944-06-29`, `no-91-1944-07-04`): BANG's Patrol 2 narrative isn't read past the tables;
  HI-67's merchants' dates in the convoy (the escort charts' columns); Sarawak Maru's identity before her silhouette.
- **No. 3905, TAKA-909** (`no-3905-1944-09-09`, `taka-909-1944-09-19`): neither Japanese record gives a time; a primary
  record for No. 3905 (Yokosuka) would add one, and its place disagrees with BANG's by about 188 nm.
- **TAKA-206** (`taka-206-1944-11-22`): BANG's Patrol 4 narrative (folder 74802868, pp. 9–11); who sank Hozan Maru
  (W-15 logged her torpedoed seven minutes after BANG's Attack 1; the postwar credit is REDFISH's).
- **The lone tanker, the convoy east of Formosa, the Yellow Sea freighter**: no Japanese record found yet.
- **The Corzine rescue** (`bang-corzine-1945-04-21`): Ishigaki's own record of the 21 April raid (only Miyako-jima's
  action summary has been found, context only); BANG's Section U log before 18 April.
- **Haynsworth, Algiers, Filignano, Venafro, Neuburg**: the open questions are in each `claims.yml` and the research
  leads that built them.
