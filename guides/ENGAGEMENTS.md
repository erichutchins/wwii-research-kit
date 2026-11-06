# Engagements: two sides, each in its own records, on one map and one clock

An engagement is two sides meeting at a place and a time: a pack against a convoy, a destroyer against a kamikaze
strike, an antiaircraft battery against a night raid. Each side kept its own records, in its own form and on its own
clock. The kit keeps each record as it is and lets them meet through ids, times and places, never by copying one into
the other. Every engagement is one folder, `records/engagements/<id>/`, and one page, `site/engagement.html?e=<id>`.

The convoys the boats met have their own records (`records/convoys/<id>/convoy.md`) and pages: `site/subject.html?s=<id>` (the ledger of every convoy is `site/subjects.html`)
(the ledger, and each convoy's voyage and ships) and `site/lanes.html` (the lanes, month by month, and a voyage as a
timetable). Haynsworth and Algiers are also told as stories: their `engagement.md` carries the account in steps
(`[[step:]]` links that set the clock and the map), and their figures are panels after the story (`site/panels/`).

This guide holds the reasons and the method. The schema, every file and every field, is `records/README.md` ("An
engagement", "A convoy", "A patrol's Japanese record"), and the validator is `tools/build_engagement.py`: it checks
that every participant, convoy, silhouette and position named exists, that every time parses with a zone, that every
entry and claim is cited in a form `SOURCES.yml` knows and every `[[link]]` resolves, and only then writes the JSON the
pages read. The fields aren't repeated here: when one is in question, read the README.

## What a page answers, at three scales

| Scale | Question | Where |
|---|---|---|
| Minutes and miles | What happened in the attack? | `engagement.html`: the map with a time slider, one lane per side, the two-sided log |
| Days and hundreds of miles | What was the convoy doing, and how did the boats close in? | `engagement.html` "Closing in"; the convoy's subject page: the voyage map and the ships against the days |
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
   attack goes with which record, and how sure the pairing is); `check_crossrefs.py` prints the minutes and miles
   between each pair. The skill `find-the-other-side` is the method. A convoy gets its own `convoy.md`: route, voyage,
   ships, each cited. What US radio intelligence knew of the convoy, a patrol's `frupac.yml` (each note as written, tied
   to an attack where it speaks to one), is read into the engagement the same way: a source about the convoy, not a
   participant.
3. **`engagement.md`.** The front matter names the participants and the window, the body tells the story. At most
   three participants have a US track, because the page has three checked colours and no fourth hue. An Army unit is
   named by its id in `army/units.csv` so the pages' breadcrumb (`site/chapter.js`) can follow it to its engagements
   and entries before and after; when no entry of the day names the unit itself, the participant says it is inferred,
   and why. The window is in GMT, like every clock on the pages. The story is a lede, then `##` sections (the outcome,
   the convoy as the boats saw it, reading the map, the clocks, the sources).
4. **`events.yml`** for what belongs to the engagement alone: a boat's narrative entries (contact reports and the
   messages received, each naming its sender and recipients), another record's entries (an air group's action report),
   and for an Army or a destroyer engagement, every entry of the day. **`claims.yml`** for the questions the records
   leave open.
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
| The light (`localNoon`, `light`) | daylight from the sun's altitude (none below −6°, full above +6°), the moon adding by its lit fraction and height; how far a ship shows in it is illustrative, not from a source. The observer view's Light choices: *As it was*; *Broad daylight*, the same local date at noon; *Night vision*, the scene as it was with the darkness lifted, drawn in a modern image intensifier's green (rendering only, illustrative, not from a source: the sun, the moon and the sky readout stay as computed) |
| Fire control | torpedo course = own course + gyro; track = torpedo course + 180 − target course; lead L: tan L = k·sin TA / (1 + k·cos TA), k = target speed / torpedo speed; angle on the bow = track − L |
| Apparent size | width = 2·atan(projected length / 2R), projected length = L·\|sin AOB\| + beam·\|cos AOB\|; height = atan(H/R) |
| An attack on one clock (`attackSheet`, `attackAt`) | seconds from the first torpedo, from `attacks.csv` as typed: each torpedo fired at its `interval` or `since_first` (a salvo the sheet gives no time for, 10 s after the last: assumed); the point of aim from the torpedoes' courses less each typed `offset` (the middle of the spread where none is typed); the target placed at the sheet's range on the bearing that point of aim and the fire-control angles give; boat and target steady on the sheet's courses and speeds; each torpedo runs to where it first reaches a hull of the target's assumed length, or past it. Torpedo speed: the sheet's where typed; the Mark 18's 27.7 knots from ATULE's sheet; the Mark 14's and 23's secondary. The torpedo's straight run and turn out of the tube are left out, so runs come out a few seconds short (SEAHORSE's Attack 3: 33 s against the narrative's 36) |
| The Torpedo Data Computer's dials (`tdcAt`) | at second *s*, what a TDC Mark 3 would show on the sheet's solution: own course and speed; the target aimed at (the next torpedo's, else the last's), its course and speed; true and relative bearing, range and angle on the bow (`attackAt`); distance to track = R·\|sin AOB\|; for the point of aim, lead L: sin L = k·sin AOB (the law of sines), torpedo course = bearing + L, gyro = torpedo course − own heading, the track, and the run = R·\|sin AOB\| / \|sin track\|; each side's gyro order adds its next tube's offset. Parallax, reach and turn left out, so the forward and after solvers order the same angles; tubes 1–6 forward, 7–10 aft. Drawn by `site/tdc.js` after OP 1056 (faces Figs. 98 and 102; dial readings pp. 72–73; scales pp. 267–270; distance to track Fig. 38) |

## How the pages draw it

### Encodings, the same on every page

| Meaning | Encoding |
|---|---|
| From the record | solid |
| From a secondary source (combinedfleet.com and the like) | outlined, or an italic name |
| Inferred | hatched |
| US radio intelligence's estimate (a FRUPAC note's mark, read off the map) | a hatched ring in the lighter ink, never solid; its entries chipped *intelligence · US* |
| Not recorded; an assumed route | dotted |
| Straight between known points, nothing recorded between | dashed |
| A ship sunk (the Japanese record) | red ✕ |
| A ship hit, not sunk | red ring |
| Attacked, no damage | open ink ring |
| A torpedo attack | diamond, in the boat's colour |
| A ship sighted | open ring in the boat's colour, at the target's position |
| A contact report | a ring on the sender's track, and a dotted line to each boat it went to |
| A time placed by the account's order | the time in italics, and the reason under the entry |
| The front, as a dated situation map drew it (`records/fronts/`) | a heavy line in the second ink, ticked as the 12th Army Group's maps tick it, on their own side: the staff's record of the day, context for the frame |
| A situation map's list (the enemy divisions it lists as facing the bridgehead) | under the map, its symbols in the map's order, said to be a list: listed, not placed |
| Several days' situation maps | the latest at the clock, or, in a dated frame (no clock to play), the day chosen on the bar under the map (the clocked frames' bar, a map at a time: a lane per followed unit's stations and per side's entries, a tick for each map's day, the play stepping through them): a step, never a glide between two maps, the old faded under the new |
| A unit on that map | the Army's symbol (FM 21-30): the map's own side an open box, solid; the enemy hatched in the lighter ink (the map's intelligence picture); in its area, not at a position |
| A followed unit's stations around the window | dots in its colour, joined dashed (straight between stations), lighter in the week before, an arrowhead at the last, no dates on the line (each dot's on hover; the day shown is the map's, or the one chosen on the bar); with a situation map, drawn to the day shown (the clock's, or the bar's), so the picture is one moment |
| A symbol that is a followed unit, or its division or command that day (`army/relations.csv`) | ringed in the subject's colour: heavy for the unit itself, light for its division or command |
| Whose side is whose | each side's 1944–45 vehicle marking (the US star in its circle, the Balkenkreuz) with its name, on its side of the front, in one place for every day's map (it marks a side, not anything at that spot, so it never moves as the days change); not flags (Germany's of 1945 carried the swastika) |

**Red is reserved for hits.** It is never a side's or a boat's colour.

### Colour

| Role | Light (paper #f6f5f1) | Dark (paper #141413) |
|---|---|---|
| The first US boat or ship | #2a6fc9 | #336cc0 |
| The second | #008f78 | #22a58e |
| The third | #6a3a9e | #a07fe0 |
| Hit | #c8323c | #e8525a |
| The other side, whatever its nationality (the Japanese record, a German corps' report) | ink (#1c1c1a / #ecebe5) | |

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

- **The observer view, further.** Built (`site/observer.js`, the engagement page's "At the periscope"): every attack
  whose data sheet is transcribed, from the plot above, through the periscope or from the bridge, with the sky and the
  solution on one clock; the build carries the sheets in `engagement.json`'s `sheets`. Beside the periscope, in tabs, the
  plot or the Torpedo Data Computer's Position Keeper and Angle Solver (`site/tdc.js`, display only: the dials turn with
  the clock to `tdcAt`'s values; the boat's computer assumed a Mark 3). Still to do:
  - the TDC's reach and turning radius (hand-set inputs on the real machine, OP 1056 p. 269) and the periscope-to-tube
    parallax, so the forward and after solvers differ as they did; the Mark 4's face (OP 1442, not yet found);
  - the narrative's timed bearings and ranges (`bearings.csv`), so the approach before firing is the record's and not
    the target held steady on the sheet's course;
  - TINOSA's own and target courses from her narrative (her report has only the summary table; reading it is a
    research lead, L73 in the family repository);
  - the Mark 14's and 23's speeds, and the periscope's fields of view (the *Submarine Periscope Manual*, NAVPERS
    16165), from primary sources;
  - the torpedo's straight run and turn out of the tube (USF 25(A)), and each target's own silhouette and size where the
    Japanese record names the ship;
  - for Haynsworth, the incoming plane's bearing, elevation and range from her action report and AA report, in the same
    view from her director.
- **The lanes from the charts.** Every waypoint in `reference/lanes/lanes.yml` is assumed. The escort divisions'
  charts draw and name the lanes (馬来直航路, the Malay direct route; the Hainan east route); tracing them would replace
  the assumptions.

## Open work, by engagement

- **TAMA-17 and TE-04** (`tama-17-1944-04-29`, `te-04-1944-05-03`):
  1. *Done.* The FRUPAC notes (`ss-385-bang/patrol-1/frupac.yml`, F01–F10) are read into the engagements like the
     Japanese records: every note inside the window is an entry (`actor: FRUPAC`, `of: us`, its source `intelligence ·
     US` through the map's citation, `about` the ship it names), and a note tied to an attack joins that attack's pairing
     as `intelligence` for the Sources view (BANG's Attack 1 beside J03 and F01–F03: 19 min and 4 nm from F01's dot, zone
     I assumed). Not as a third side with a lane of its own, as first planned: FRUPAC is a source about the convoy, not a
     participant, so it gets a column in the chronology and the Sources view, chipped *intelligence · US*, and on the map
     hatched rings in the lighter ink at the positions read off the maps (the inferred encoding, never solid), with their
     own legend line. The front page's replay lists the records alone. Still open: the museum's full-resolution scans
     (item 4) would turn the estimated positions into read ones.
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
