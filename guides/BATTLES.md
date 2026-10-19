# Battle pages: one engagement at a time, from the reports on both sides

`battle.html` draws a submarine engagement (a convoy action, or a pack's run
of them) on one map and one GMT timeline: each boat's track and torpedo
attacks from her war patrol report, beside the Japanese record of the same
minutes. It is built to repeat for any patrol: everything specific to an
engagement lives in its own folder under `records/engagements/`, and
`battle.html?e=<id>` shows it. A picker on the page lists them all.

Every BANG patrol has one:

| id | Boats | Actions | Japanese records |
|---|---|---|---|
| `luzon-strait-1944` | BANG, PARCHE, TINOSA (Patrol 1 pack) | TAMA-17, 29–30 Apr 1944; TE-04, 3–4 May 1944 | Nittatsu Maru's log, 1st Surface Escort Division diary |
| `bang-patrol-2` | BANG, SEAHORSE, GROWLER | Lone tanker, 14 Jun; HI-67, 29 Jun; a convoy in the South China Sea, 4 Jul 1944 | 1st Surface Escort Division diary (HI-67 only) |
| `bang-patrol-3` | BANG | No. 3905, 9 Sep; TAKA-909, 19 Sep; an unidentified convoy, 20–21 Sep 1944 | combinedfleet.com (No. 3905), 4th Surface Escort Division diary (TAKA-909); neither gives a time |
| `bang-patrol-4` | BANG, REDFISH, SHAD | TAKA-206, 22–23 Nov 1944 | Minesweeper W-15's battle report |
| `bang-patrol-5` | BANG, ATULE (SPADEFISH and POMPON transcribed but elsewhere that day) | A small freighter, Yellow Sea, 10 Feb 1945 | None found yet |
| `bang-patrol-6` | BANG, with CHENANGO's air group as a second US record | Rescue of Ens. Donald E. Corzine, 21–22 Apr 1945 | Miyako-jima Guard Unit's telegram (context only) |

## Making a page for another engagement

1. **Transcribe the boats' tracks**: `positions.csv` for each boat's patrol
   (attack sheets as `source=attack`, ship contacts, fixes), checked with
   `check_track.py` (0 too-fast legs). Another boat goes in
   `records/boats/<hull>-<name>/patrol-N/` (`guides/FLEET.md`). `depths.csv`
   adds depth charges and deep dives to the boat's lane where it exists.
2. **Japanese side** (optional, but it is the point): `japanese.csv` and
   `crossrefs.csv` in the patrol folder, then `check_crossrefs.py`
   (`records/README.md` has the columns; `jacar.py` finds the records).
3. **Draft the engagement**:
   `uv run tools/build_battle.py new <id> <patrol> [<patrol> ...]`, e.g.
   `new bang-patrol-4 4` or `new luzon-strait-1944 1 ss-384-parche/1 ss-283-tinosa/6`.
   It groups the attacks into actions (less than 18 hours apart is one
   action), sets each GMT window from the first ship contact to six hours
   after the last attack, and takes the convoy and ship names from the
   Japanese records inside the window.
4. **Finish `engagement.yml` by hand** (fields below): title and lede,
   captains, each action's label, route, full ship list, escorts with their
   silhouette category, outcome, a few place names, and the page's notes
   (how to read the map, the clocks each side kept, sources). Say in the
   notes what is missing, e.g. a pack-mate whose report isn't transcribed.
5. **Narrative log** (optional): `notes.csv` beside it, one row per entry
   read from the scans: `boat,date,time,zone,text,page`, time and zone as
   typed, the captain's words abridged with `...`.
6. `uv run tools/build_battle.py <id>`: it fails on what would break the
   page (more than three boats, an unknown silhouette) and lists fields
   still empty. Then check `battle.html?e=<id>` in light and dark mode at
   desktop and phone widths.

### engagement.yml

| Field | |
|---|---|
| `title`, `short`, `eyebrow`, `lede` | Page heading; `short` names it in the picker and the browser tab |
| `boats[]` | `id` (lower case, used in `notes.csv`), `name`, `hull`, `co`, `patrol` (folder key as for `check_track.py`: `"4"`, `"ss-384-parche/1"`), `patrol_no`. One to three boats; they take the categorical colours in this order |
| `japanese[]` | Patrol folders whose `japanese.csv` and `crossrefs.json` to read |
| `actions[]` | `id`, `label`, `convoy` (or, where none is identified, `target_label`: "Lone tanker"), `start`/`end` (GMT, `1944-11-22T10:00Z`), `route`, `ships`, `ships_note`, `escorts[]` (`name`, `kind`, `type`), `outcome`. More than one action gives the page a switcher |
| `ships[]` | A merchant as its name without "Maru", `*` = sunk (`"Hozan*"`, `"Daiyoku (Taiyoku)*"`), or an object `{name, kind, type, sunk}` for a tanker or a ship known only as the boat identified it (`{"name": "Freighter (AK)", "kind": "As BANG identified it", "type": "cargo"}`) |
| `escorts[].type`, `ships[].type` | Silhouette: `destroyer`, `escort` (kaibokan, torpedo boat, minesweeper, minelayer), `gunboat` (any auxiliary, i.e. a converted merchant or fishing vessel), `cargo`, `tanker` |
| `places[]` | `name`, `lon`, `lat`, optional `small`; `inset: [lon, lat]` also labels it on the locator |
| `notes[]` | `head`, `text`: paragraphs under the page |
| `others[]` | Another US record with its own lane in ink: `id`, `name`, `type` (silhouette, e.g. `fighter`), `events[]` (`date`, `time`, `zone`, `title`, `text`, `page`, `scan`, optional `type: "ditched"`, `doubt`, and `lat`/`lon` with `estimated` for a position the record gives only roughly, drawn as a dashed ring). Used for CHENANGO's aircraft action report on the Patrol 6 page |

### Data flow

```
records/engagements/<id>/engagement.yml, notes.csv   hand-edited: the engagement
<each boat's patrol folder>/positions.csv          tracks, attacks, sightings
<each boat's patrol folder>/depths.csv             depth charges and deep dives, where transcribed
<folders in "japanese">/japanese.csv, crossrefs.json   Japanese records and their links to attacks
sources/naturalearth/land-10m.json                 coastline (downloaded on first run, git-ignored)
        │
        ▼  uv run tools/build_battle.py [<id>]
records/battles/<id>.json, records/battles/index.json  ──►  battle.html?e=<id>
```

`uv run tools/build_battle.py <id> --standalone OUT.html` writes a single
file with that engagement inlined, for sharing without a server; with no id
it inlines every engagement (about 300 KB), chosen by the picker or
`OUT.html#<id>`. That all-engagement copy is published as a private Claude
artifact: https://claude.ai/artifact/MhAUbtjatciPtNYmsKRK5u

What the builder decides (change it in `build_battle.py`):

- Map area: the extent of every fix and Japanese position in the window,
  padded 0.3°. A boat's track includes her last fix before and first after
  the window so she enters and leaves the map. The locator inset is at least
  7° across.
- Events: attack rows (attack sheets and narrative "… fired" rows), ship
  and aircraft contacts, depth charges, passing depths and orders of 300 ft
  or more, `notes.csv`, and Japanese events. A Japanese hit that names no
  ship is drawn as "Ship not named (<convoy>)" with the merchant silhouette.
  A Japanese record of one day's event that gives no time is drawn at the
  time of the attack `crossrefs.csv` matches it to, and says so (Patrol 3);
  monthly loss tables are left out.
- Coastline: full detail around each action, Douglas-Peucker simplified for
  the locator inset, which covers every action of the engagement.

## The page

- **Map** (D3, Mercator fitted to each action's area): each boat's track
  through her reported positions, torpedo attacks as diamonds in the
  boat's colour, ship sightings (the target's
  position), Japanese-recorded hit and sinking positions (✕, with the ship's
  silhouette), and positions a report contradicts (dashed). Attacks carry
  no labels: as the clock passes each firing time a red ring pulses at the
  boat's position on her track (`--fire`; a still ring under reduced
  motion), and the attack's diamond appears and stays. Where a boat's
  summary table and narrative both time an attack, only the narrative's
  time pulses. Hover a diamond for the boat and attack number. Japanese
  labels that would cover another label or mark move up or down to the
  nearest free slot, with a leader line. The boats' names move with them, under the
  marks layer, each in whichever spot around her covers least of the labels,
  marks and other boats. 20-nm scale bar, deg-min graticule, locator inset.
- **Timeline**: one lane per boat plus one for the Japanese side, in GMT,
  with Tokyo time alongside. Play, click, or scrub; the map shows each boat's
  interpolated position at that moment and fades what hasn't happened yet.
- **Log**, beside the map and the same height as the map card: every event in
  GMT order with the boat's own local time and zone, the captain's words, the
  Japanese-side outcome of each attack (from `crossrefs.json`), and a link to
  the report page or Japanese source. During playback it scrolls inside its
  own panel (`scrollLog`, never `scrollIntoView`, which would also scroll the
  page away from the map). Below 760 px wide it stacks under the map.
- **Order of battle**, below: the boats and their captains, the convoy's
  escorts and ships, and the outcome, as recognition plates in the manner of
  the wartime ONI silhouette books. Sunk ships are solid ink; the rest grey.
- Silhouettes (`SIL` in `battle.html`, profile, bow right, viewBox
  120 × 24) are five categories: fleet submarine (Gato/Balao), destroyer,
  escort, auxiliary gunboat, merchant ship. Every merchant is drawn as the
  same generic three-island cargo ship, and none is to scale; the page says
  so under the plates. Submarines appear in the plates and the log, not on
  the map.
- Colours: boats take the three validated categorical slots in the order
  `engagement.yml` lists them (`--c1` blue, `--c2` orange, `--c3` aqua;
  all-pairs colour-blind check passes in light and dark). The Japanese side
  is ink, not a fourth hue. Every mark also has a shape or a text label, so
  nothing relies on colour alone. The firing pulse adds one red (`--fire`),
  close to PARCHE's orange for red-green colour-blind readers; the pulse is
  also told apart by its expanding ring and its moment, and it lasts about a
  second.

## luzon-strait-1944: BANG, PARCHE and TINOSA against two convoys

BANG's Patrol 1 coordinated attack group, under Capt. G. E. Peterson in
PARCHE, against two convoys in the Luzon Strait:

| Night | Convoy | Route | Losses (Japanese loss list) |
|---|---|---|---|
| 29–30 April 1944 | TAMA-17 | Takao → Manila | Takegawa Maru and Nittatsu Maru, both to BANG |
| 3–4 May 1944 | TE-04 | Yulin → Japan, iron ore | Five ships, 30,542 GRT; which boat sank which is open |

Rebuild after any change to its inputs:

```bash
uv run tools/check_track.py all --geojson
uv run tools/check_track.py ss-384-parche/1 --geojson
uv run tools/check_track.py ss-283-tinosa/6 --geojson
uv run tools/check_crossrefs.py
uv run tools/pack_timeline.py          # text timeline -> records/boats/ss-385-bang/patrol-1/pack_timeline.csv
uv run tools/build_battle.py luzon-strait-1944
```

### Assumptions shown on the page

- Positions are each navigator's dead reckoning; three boats place the same
  convoy several miles apart. Lines between positions are straight.
- Clocks: BANG zone K (−10), PARCHE I (−9), TINOSA H (−8) on station.
  Japanese records are taken as Tokyo time (I). On 29–30 April this matches
  Nittatsu Maru's own log to 1–7 minutes.
- TINOSA's summary-of-attacks table contradicts her narrative for Attacks 1
  and 2 (and is an hour off for Attack 3). Both are drawn; the table rows are
  dashed with the reason.
- The 3–4 May sinking times and attributions are combinedfleet.com's
  (secondary), flagged in the log. See `records/README.md`, "The wolfpack".
- Ship silhouettes show categories, not individual ships, and are not to scale.

### Findings the page shows

- 29–30 April: BANG alone sank Takegawa Maru and Nittatsu Maru; PARCHE and
  TINOSA's morning attacks (nine minutes apart) match no Japanese loss.
- 3–4 May: the boats' own reports put the order as TINOSA (1509 GCT),
  PARCHE (1606, 1627), BANG (1732), TINOSA (1849, 2009, 0050). The secondary
  source's sinking times fit that order but not its attributions; Kinrei
  Maru (JANAC: BANG) is timed to the minute PARCHE fired.

### Open work, roughly in order

1. **FRUPAC layer.** `records/boats/ss-385-bang/patrol-1/frupac.csv` (F01–F10) holds the
   radio-intelligence notes for both nights: Yashima Maru "att. by torp" and
   "fired on … from sub" (29 Apr), Wales Maru's sub contact and torpedo track
   (30 Apr, which fits PARCHE and TINOSA's morning attack), D/F fixes on a
   submarine (3 May), and "rec torp attack" (4 May). `lat_est`/`lon_est` are
   estimates read off the map. Add them as a third side ("US radio
   intelligence") with its own lane, marked as estimated positions.
2. **Estimated convoy tracks.** Transcribe the target data from each attack
   sheet (target course, speed, range and bearing at firing; 13 sheets across
   the three boats) and combine with the ship-contact sightings and Nittatsu
   Maru's course (S55°E after the rescue) to draw each convoy's track, marked
   as estimated. The same data gives a captain's-eye diagram of each attack.
3. **Who sank Kinrei Maru.** Needs a Japanese primary record: Kinrei Maru's
   movement log (ship tables, キ volume, JACAR) or TE-04's escort reports
   (kaibokan CD-1, Kazan Maru, Maeshima). Searches so far found neither.
4. **PARCHE and TINOSA depth logs.** Only positions are transcribed for them;
   their narratives (TINOSA: 55 depth charges on 3–4 May) would add dives and
   depth charges to their lanes, as BANG's already are.
5. **Boat markers over marks.** Boat names dodge the labels, but a boat's
   dot sits on her own attack diamond until she moves off it.
6. **Full-resolution FRUPAC scans.** First request to the museum (via the
   Portal to Texas History contact form): daily maps 28 Apr – 5 May 1944
   (`metapth1733007`–`metapth1733014`), 19 Apr – 19 May 1944
   (`metapth1733532`), and the April and May 1944 summaries
   (`metapth1733511`, `metapth1733512`), with permission to georeference and
   transcribe (the collection is CC BY-NC-ND). Later batches: the maps that
   name BANG (`python3 tools/frupac.py find "\bBang\b"`) and the dates of
   her other attacks (`frupac.py date`).
7. **Ships' own silhouettes.** The merchant plates are one generic cargo
   ship. ONI 208-J (Japanese merchant ships) has a silhouette for most named
   Marus; matching each ship to it would make the plates, and TINOSA's
   "tanker" identification, checkable.

## bang-patrol-4: BANG against convoy TAKA-206

BANG's seven attacks of 22–23 November 1944 (0032–0314 K) against the six
ships of TAKA-206 (Keelung for Naha), beside minesweeper W-15's battle
report. Three ships were sunk; the postwar credit gives BANG two and
REDFISH one.

Open work:

1. **REDFISH and SHAD.** BANG's pack-mates that night. REDFISH's report
   would settle Hozan Maru, which W-15 logged torpedoed seven minutes after
   BANG's Attack 1 and the US Navy chronology credits to REDFISH.
2. **Narrative log.** No `notes.csv` yet: BANG's Patrol 4 narrative
   (folder 74802868, pages 9–11, where the contact and the night's aircraft are) would add the approach, the radar picture
   and the escorts' counterattack.
3. **FRUPAC.** `records/boats/ss-385-bang/patrol-4/frupac.csv` has a torpedo track at Attack 7's
   time and REDFISH's report for the pack (FRUPAC open work above).

## bang-patrol-6: the rescue of Ensign Corzine

BANG, ordered from her lifeguard station northeast of Formosa at 1415 I on
21 April 1945, took aboard Ens. Donald E. Corzine (CHENANGO, F6F-5) at 0737 I
on the 22nd after fourteen hours in his raft. His squadron's aircraft action
report (Air Group 25, ACA No. 50, NARA 140031168 p248) has him hit by medium
AA over Ishigaki airfield and ditching "about twenty miles East of the
Island"; the page draws that as an estimated position. BANG's own narrative
(p11–13) is `notes.csv`; her Section U radar log for 18–25 April (p35–36) is
in `records/boats/ss-385-bang/patrol-6/positions.csv`, including a 2200 position on the 21st
(125-14E as typed) that contradicts the narrative and is off the track.

Open work:

1. **Ishigaki's own record** of the 21 April raid and its AA claim. Only
   Miyako-jima's action summary has been found (JACAR C19010021200 p42,
   `records/boats/ss-385-bang/patrol-6/japanese.csv` J01, context only). Next leads: the Navy
   Ministry incoming-telegram files C19010031100 and 参考電綴 C19010041900,
   C19010043400.
2. **Section U before 18 April** (report p27–34, from 30 March) is not
   transcribed.
3. **SNOOK** left the pack the first night "to return to port" (BURRFISH
   p03) and has no report for this patrol; her loss needs another source.

## bang-patrol-2, bang-patrol-3, bang-patrol-5

BANG alone, from her attack sheets, contact tables and depth log. Open work
for all three:

1. **Narrative log.** No `notes.csv` yet; the scans aren't read past the
   tables. The narrative pages around each attack would give the approach
   and the captain's words, as Patrol 1's do.
2. **Japanese records** for the actions with none: Patrol 2's lone tanker
   (14 Jun) and 4 July convoy, Patrol 3's 20–21 September convoy, and
   Patrol 5's freighter. Patrol 3's two records have no times; a primary
   record for convoy No. 3905 (Yokosuka) would add one.
3. **Pack-mates** are transcribed (`records/README.md`, "BANG's other pack-mates").
4. **FRUPAC**: each patrol's `frupac.csv` has notes for these attacks
   (claims, D/F fixes, the convoy's make-up).
