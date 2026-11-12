# Engagements: two sides, each in its own records, on one map and one clock

An engagement is two sides meeting at a place and a time: a pack against a convoy, a destroyer against a kamikaze
strike, an anti-aircraft battery against a night raid. Each side kept its own records, in its own form and on its own
clock. The kit keeps each record as it is and lets them meet through ids, times and places, never by copying one into
the other. Every engagement is one folder, `records/engagements/<id>/`, and one page, `site/engagement.html?e=<id>`;
the index of every one, by theatre, is `site/engagements.html`, the nav bar's first link.

Each convoy the boats met has its own record (`records/convoys/<id>/convoy.md`) and subject page
(`site/subject.html?s=<id>`: its voyage and its ships day by day); `site/subjects.html` lists every convoy, and
`site/lanes.html` shows the lanes month by month, with a voyage as a timetable. Haynsworth and Algiers are also told
as stories: their `engagement.md` carries the account in steps (`[[step:]]` links that set the clock and the map),
and their figures are panels after the story (`site/panels/`).

This guide holds the reasons and the method. The schema, every file and every field, is in the records' own
documentation (`records/README.md` and the field reference it points to: "An engagement", "A convoy", "A patrol's
Japanese record"), and the validator is `tools/build_engagement.py`: it checks
that every participant, convoy, silhouette and position named exists, that every time parses with a zone, that every
entry and claim is cited in a form `SOURCES.yml` knows and every `[[link]]` resolves, and only then writes the JSON the
pages read. The fields aren't repeated here: when one is in question, read them there.

## What a page answers, at three scales

| Scale | Question | Where |
|---|---|---|
| Minutes and miles | What happened in the attack? | `engagement.html`: the map with a time slider (each boat surfaced or down, the convoy where it was seen, its course at each firing, the depth charges), one lane per side, the two-sided log |
| Days and hundreds of miles | What was the convoy doing, and how did the boats close in? | `engagement.html`: the overview in the map's corner (the convoy's whole voyage on its lane, a box where the map is), "Closing in"; the convoy's subject page: the voyage map and the ships against the days |
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

| Format | For | The test |
|---|---|---|
| CSV | tables: numbers, dates, codes and short references, one value per cell (`positions.csv`, `depths.csv`, `layers.csv`); RFC 4180, so a cell that carries a note or a quotation is quoted | every row has the same few short fields |
| YAML | structured records that carry words: `events.yml`, `claims.yml`, `japanese.yml`, `frupac.yml`, a convoy's `ships:` | several fields per item, and one of them is prose |
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
| Zone to GMT | the Navy's zone letters: A–M (no J) for the zones east of Greenwich, one to twelve hours ahead of GMT; N–Y west, one to twelve hours behind; Z = GMT; the war diaries' half-hour zones. The Navy's *zone description* is the number added to local time to get GMT, so it carries the opposite sign: zone I is "−9", nine hours ahead. Japanese records keep Tokyo time, which is zone I. A record's "GCT" is quoted as typed; the pages' own clock is labelled GMT, and each entry shows GMT and the record's time side by side |
| A bearing and distance | from a known point (`from`, `brg`, `nm` in `positions.csv`), resolved by the build |
| A track at a moment | straight between the participant's own fixes, never beyond the first or last |
| A convoy's observed path | where it was seen: the boats' ship contacts (the target's position) and the Japanese record's positions, one point per minute. A sighting the report itself contradicts (its `fix_note` says so) is left out, and listed under the chart |
| Closing in | each boat's distance from that path, only while both are known; after the last sighting, an attack means "within torpedo range", not a number |
| Speed along a lane | between a voyage's known points; a slow leg may be an unrecorded stop (a lead) |
| The sky | sun and moon, bearing, altitude, phase and lit fraction, from SunCalc |
| The light (`localNoon`, `light`) | daylight from the sun's altitude (none below −6°, full above +6°), the moon adding by its lit fraction and height; how far a ship shows in it is illustrative, not from a source (see "The observer view's light", below) |
| Fire control | torpedo course = own course + gyro; track = torpedo course + 180 − target course; lead L: tan L = k·sin TA / (1 + k·cos TA), k = target speed / torpedo speed; angle on the bow = track − L |
| Apparent size | width = 2·atan(projected length / 2R), projected length = L·\|sin AOB\| + beam·\|cos AOB\|; height = atan(H/R) |
| An attack on one clock (`attackSheet`, `attackAt`) | seconds from the first torpedo, from `attacks.csv` as typed, with boat and target steady on the sheet's courses and speeds (see "An attack from its sheet", below) |
| A depth charge's shock (`peakPressure`, `seaPressure`, `DC_SETTINGS`) | peak pressure 52.4 × (kg^⅓ / m)^1.13 MPa for TNT (Cole 1948; another explosive taken as TNT, assumed); the sea's own pressure ρgh, 1,025 kg/m³; the Japanese pistols' settings as War Damage Report 58 gives them (para 3-10: the Type 95's 98, 197, 292 ft, the Type 2's to 480). The damage bands are the Bureau's for 300 lb of TNT against the light-hulled boats (15-12), never a boat's own limit |
| The Torpedo Data Computer's dials (`tdcAt`) | at second *s*, what a TDC Mark 3 would show on the sheet's solution (see "The Torpedo Data Computer", below) |

**An attack from its sheet.** Each torpedo is fired at its `interval` or `since_first`; a salvo the sheet gives no
time for is put 10 s after the last (assumed). The point of aim is the torpedoes' courses less each typed `offset`,
or the middle of the spread where none is typed. The target is placed at the sheet's range, on the bearing that point
of aim and the fire-control angles give. Each torpedo runs to where it first reaches a hull of the target's assumed
length, or past it. Torpedo speed is the sheet's where typed; the Mark 18's 27.7 knots is from ATULE's sheet; the
Mark 14's and 23's are from secondary sources. The torpedo's straight run and turn out of the tube are left out, so
runs come out a few seconds short (SEAHORSE's Attack 3: 33 s against the narrative's 36).

**The Torpedo Data Computer.** The dials show own course and speed; the target aimed at (the next torpedo's, else the
last's), its course and speed; true and relative bearing, range and angle on the bow (`attackAt`); distance to track
= R·|sin AOB|. For the point of aim, the lead L is sin L = k·sin AOB (the law of sines); torpedo course = bearing +
L; gyro = torpedo course − own heading; the run = R·|sin AOB| / |sin track|; each side's gyro order adds its next
tube's offset. Tubes 1–6 are forward, 7–10 aft. Parallax, reach and the torpedo's turn are left out, so the forward
and after solvers order the same angles, as the real machine's did not. That the boat's computer was a Mark 3 is
assumed. The dials are on their own page, `site/tdc.html` (`tdc-page.js`; `tdc.html?e=<engagement>&boat=<id>&attack=<Attack 1>`, which the observer view links for its attack): a clock over the attack's seconds, each dial numbered and listed with its value and where it comes from. Drawn by `site/tdc.js` after OP 1056 (faces, Figs. 98 and 102; dial readings, pp. 72–73; scales, pp.
267–270; distance to track, Fig. 38).

**The observer view's light.** Three choices: *As it was*; *Broad daylight*, the same local date at noon; *Night
vision*, the scene as it was with the darkness lifted. The last is drawn in the green of a modern image intensifier,
which no boat of 1944 carried: it is a rendering to make a night attack legible, labelled illustrative on the page,
and the sun, the moon and the sky readout stay as computed.

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
| A boat on the surface, then submerged (her depth log: the build's `dives`) | her track thick, then thin; her dot at the clock filled, then open, its label "down, 60 ft"; a wash behind her lane while she was down |
| The convoy at the clock, on its observed path | a hatched dot in the other side's ink, with its name (ours) |
| The convoy's course and speed as a boat's attack sheet types it | an arrow in the other side's ink from her attack position (the target was within the sheet's range), the length an hour's run at the typed speed (ours); shown once the clock passes the firing |
| Depth charges the boat logged | an eight-rayed burst in the other side's ink, where she was then (straight between her fixes: placed, ours) |
| The water column (`site/panels/depth.js`, on every engagement whose boat's depth log is transcribed) | her depth against the clock, solid from each log entry to the next, dashed where the log gives no depth (60 ft, assumed); a "passing" entry a point on the way to the depth ordered before it; the counter-attack's entries as rules in the other side's ink, the span her words give ("the next 4½ hours") shaded; the pistols' settings as dashed rules; the layer from her bathythermograph card as two washes (isothermal, then the gradient); the section to scale (one foot across = one foot down), her silhouette keel at the logged depth, an escort's on the surface set to one side (not placed), a charge at each setting straight above her (illustrative: no charge's place is recorded) with the Bureau's rings, the seafloor under her track drawn or, below the figure, said |
| The convoy's whole voyage, beside the map (the overview, `site/engage-overview.js`) | its lane through `reference/lanes/lanes.yml`, dotted through an assumed waypoint and dashed straight between two ports; ports open rings, dated stops solid dots; a box in ink where the map is, following its zoom; foldable |
| An aircraft's path, whatever its basis (`routes.yml`, `by: air`); a unit's moves on the ground have none | chevrons along the line, pointing the way it flew; in its group's colour where the route names an `actor`, else its side's ink |
| An aircraft's course as its form types it (`routes.yml`, `reported`), drawn back from where it was typed | solid, an arrowhead; the length ours |
| A course as a squadron's sketch map draws it (`sketched`) | long dashes; no arrowhead where the sketch's direction isn't sure |
| A path no record gives (`inferred`): a straight line between two places | dotted, in the side's ink |
| A weapon's range as the manual prints it, round where the battery was (`reach.yml`) | a ring in the side's ink, a faint wash; solid if the battery's place and weapon are both its own record's, dashed otherwise; labelled with the weapon and range |
| A bombing target the record names (`positions.csv`, `kind` `target`) | a ring with a cross, in the ink of the side it belongs to |
| A ship sunk (the Japanese record) | red ✕ |
| A ship hit, not sunk | red ring |
| Attacked, no damage | open ink ring |
| A torpedo attack | diamond, in the boat's colour |
| A ship sighted | open ring in the boat's colour, at the target's position |
| A contact report | a ring on the sender's track, and a dotted line to each boat it went to |
| A time placed by the account's order | the time in italics, and the reason under the entry |
| The front, as a dated situation map drew it (`records/fronts/`) | a heavy line in the second ink, ticked as Twelfth Army Group's maps tick it, on their own side: the staff's record of the day, context for the frame |
| A situation map's list (the enemy divisions it lists as facing the bridgehead) | under the map, its symbols in the map's order, said to be a list: listed, not placed |
| Several days' situation maps | the latest at the clock; in a dated frame, the day chosen on the bar under the map (a tick for each map's day, play stepping through them). A step, never a glide between two maps, the old faded under the new |
| A unit on that map | the Army's symbol (FM 21-30): the map's own side an open box, solid; the enemy hatched in the lighter ink (the map's intelligence picture); in its area, not at a position |
| A followed unit's stations around the window | dots in its colour, joined dashed (straight between stations), lighter in the week before, an arrowhead at the last; each dot's date on hover. With a situation map, drawn to the day shown, so the picture is one moment |
| A symbol that is a followed unit, or its division or command that day (`army/relations.csv`) | ringed in the subject's colour: heavy for the unit itself, light for its division or command |
| Whose side is whose | each side's 1944–45 vehicle marking (the US star in its circle, the Balkenkreuz) with its name, on its side of the front, in one place for every day's map: it marks a side, not anything at that spot. Not flags (Germany's of 1945 carried the swastika) |

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

Open questions about an engagement are in its `claims.yml`, on its page behind *Questions and sources*; what a
computation leaves out is said beside it above and under the view it affects.

**Counter-attacks are engagements of their own** (`bang-counterattack-1944-09-19` is the first): the hunt after an
attack, the boat against the escorts that hunted her, with the water column as its figure. The escorts' doctrine is
from S-24, *Japanese Anti-Submarine Warfare* (pp. 11-15 and 45); each boat's class curve, the water column's inner
ring, is read off figure 15-2 of War Damage Report 58 into `engage.js`'s `hullRange`. The explainer is
`site/depthcharge.html`. Not yet read: the Naval Technical Mission's report O-08, *Japanese Depth Charges*.
