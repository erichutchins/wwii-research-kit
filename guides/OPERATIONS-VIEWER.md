# The operations viewer: one model for ships, units and the war around them

The specification of the kit's pages: the model they are built on (subjects and the organizations they belong to;
their movements, stations and events; the frames put round them; the sources each claim rests on), the views of a
frame, the two depths of reading, the navigation and the visual hierarchy. Read it before adding a page or a view.
The section numbers are cited from the code (`guides/OPERATIONS-VIEWER.md 2.4`), so they are kept stable.

Two cases run through it, and every rule here was checked against both: convoy TAMA-17 in the Luzon Strait, 29–30
April 1944 (three war patrol reports, a Japanese escort diary and a ship's movement log, the FRUPAC overlays, two
secondary sources), and the Medical Detachment, 67th Coast Artillery (AA), from Paterson, New Jersey in September
1942 to Hüttenfeld, Germany in May 1945.

The rules of `CLAUDE.md`, `guides/METHODS.md` and `guides/ENGAGEMENTS.md` stand throughout: cite every entry, keep
each record's own structure, compute rather than store, label every assumption, repetition isn't corroboration, no
numbers on conclusions, name the other side as the records do, and follow units and ships, never people.
`guides/ENGAGEMENTS.md` owns the map's encodings, the colours and the computation; this guide cites it and does not
restate them. How the design was reached, and the pages it replaced, is in
`guides/design-history/2026-11-operations-viewer.md`.

## 1. What the pages have to carry

The kit began with one kind of page: a submarine pack against a convoy, replayed on one clock. The records now hold
five kinds of subject and tempos from minutes to years, and three things follow for every page.

- **A clock is one view's device, not the page's.** A convoy battle is timed to the minute; a battery's month at
  Venafro is a list of days; a detachment's war is three years of stations.
- **A source's kind is not a side.** A newspaper, a radio-intelligence overlay, a postwar assessment and an escort's
  diary are kinds of source, each with its own weight, and the page shows them as such.
- **The record and the reconstruction are told apart.** The entries as typed and the layers computed from them share
  a page; the reader sees at a glance which is which, in the type, on the map and in the page's order.

## 2. The model

Four kinds of thing, each with a word the pages use consistently.

### 2.1 Subjects and organizations

A **subject** is something the records follow: a boat (`boats/ss-385-bang`), a ship (`ships/dd-700-haynsworth`), an
Army unit (`army/units.csv`: a battery, a company, a detachment, a division), a Seabee battalion or a part of one
(`seabees/units.csv`, `parts.csv`), a convoy (`convoys/hi-67`), a command (`commands/comsubpac`). Every subject has
an id, a name as the records give it, a kind, and the records that are its own. `tools/build_subjects.py` writes them
all to `records/subjects.json`, the one registry the subject page, the breadcrumb and the lint read. The other side's
units appear as the records name them (Harukaze; 5. Geb.Div.; No. 153 Squadron RAF).

An **organization** is dated membership of one subject in another, each row cited: Battery D *part of* the 106th AAA
AW Bn; BANG *in pack* with PARCHE and TINOSA; Takegawa Maru *in convoy* TAMA-17 as its tenth ship; the Forward
Echelon *part of* the 20th NCB from 13 May 1943; the 67th CA (AA)'s 2nd Battalion *redesignated* the 894th AAA AW Bn
on 20 March 1944. `army/relations.csv` has the shape (unit, relation, other, from, to, basis, page, note); a convoy's
`ships:`, a battalion's `parts.csv` and ComSubPac's `task_organization.csv` say the same thing in their own records,
and the build reads them into one shape.

**People are not subjects.** The records are the units'; no one is followed by name, and names the records carry stay
as written in the entry that carries them. A family's own site may attach a person to a subject by date on its own
pages (§10); nothing on the kit's side depends on it.

**Name a unit first by what it was.** A unit's designation is its only name in these records, and "Medical
Detachment, 67th CA (AA) / 894th AAA AW Bn" tells most readers nothing. Each subject has a `plain` line in the kit's
voice (`army/units.yml`, `seabees/units.yml`, `ship.yml`, `convoy.md`, `command.yml`): what kind of thing it was and
what it did, in a sentence a reader without the Army's vocabulary can follow (*the aid men of an anti-aircraft
regiment, a section with each battalion*; *a fleet submarine of the Balao class, on her first war patrol*). The pages
lead with the plain line as the eyebrow and give the designation as the title; lists and breadcrumbs show both. The
designation stays exactly as the records write it, a redesignation is an organization row and not a second name, and
a subject without a `plain` line fails the build.

### 2.2 Movements, stations and events

Everything a record says a subject did is one of three things:

| Primitive | Meaning | Where the records hold it |
|---|---|---|
| **Movement** | from here at one time to there at another | a track's fixes (`positions.csv`, `on_track=yes`), a sea crossing (`army/ships.csv`, `seabees/voyages.csv`), a convoy's `voyage`, a leg the record doesn't trace (`routes.csv`: always assumed) |
| **Station** | here from one time until the next change | the STATION line (`army/stations.csv`, `seabees/stations.csv`: a row lasts until the next), a boat in port (ComSubPac's `disposition.csv`), a picket station |
| **Event** | at a time (or placed), here, something happened | an attack, a hit, a sinking, a depth charging, a sighting, a raid fired on, a casualty, a communiqué (`events.yml`, `attacks.csv`, `depths.csv`, `army/actions.csv`, `japanese.yml`, `frupac.yml`) |

Each is drawn and read differently: a movement is a line, a station is a stay (a mark that holds, a bar on a
chronology), an event is a point in time. A unit's war is mostly stations; a patrol is mostly movement; an attack is
events. One chronology can hold all three, and one map.

### 2.3 Frames

A **frame** is what is put round a set of subjects and a span of time to ask a question. There are three:

| Frame | Question | Scale | Records | Page |
|---|---|---|---|---|
| **Journey** | Where was this subject, and what did it do, in its own record? | a patrol, a voyage, a unit's war | a boat's `patrol-N/`, a ship's `positions.csv`, a unit's rows in `army/`, a battalion's in `seabees/`, a `convoy.md` | `subject.html?s=<id>` |
| **Engagement** | What happened when these subjects met, each in its own records? | minutes to a month | `engagements/<id>/` | `engagement.html?e=<id>` |
| **Operation** | What was the war doing here, and what did it mean? | a campaign or a phase | `operations/<theater>/<id>.md` | its place on `theatre.html?t=<theater>` |

Frames nest and cross. An engagement lies inside an operation (Venafro inside the Cassino fighting) or between two; a
journey crosses many of both. The ladder the pages walk is **theatre → operation → engagement → entry**, and the
thread that crosses it is the **subject**: from any engagement, each subject's own before and after. An operation is
**context, not participation**: a unit with stations inside its area and dates is a lead until its own record says it
took part (`records/operations/README.md`).

A frame's **tempo** is derived from its entries and never stored (`Engage.tempo`, tested):

- *clocked* when more than half its entries carry a time with a zone, so that one clock is meaningful (TAMA-17,
  Haynsworth). More than half, not any: Remagen's corps report times ten entries of twenty-five, and a clock played
  over it would pass most of the record in silence;
- *monthly* when the entries span more than about ninety days (a unit's war);
- *dated* otherwise: the entries carry days (Venafro, Algiers' three nights).

The tempo decides which view leads (§3).

### 2.4 Sources and voices

Every entry cites a page in a form `records/SOURCES.yml` knows. Each source entry there carries two hand-edited
fields: `kind`, what sort of source it is, and `of`, the nationality of its author. `check_sources.py` fails on a
source without a kind, and the build tags every entry, claim, station and fix with its source's kind and nationality
through its citation.

| `kind` | Meaning | Examples |
|---|---|---|
| `record` | written at the time by the subject or its command | war patrol reports, war diaries, morning reports, muster rolls, the escort divisions' war diaries, XIV Panzer Corps' daily reports |
| `intelligence` | what one side knew of the other at the time | the FRUPAC overlays |
| `press` | published at the time | L'Écho d'Alger, the Allied communiqués, the Italian and German bulletins |
| `assessment` | an official reckoning after the fact | JANAC (the Joint Army–Navy Assessment Committee's 1947 loss list) |
| `recollection` | told later by someone who was there | a crewman's memoir |
| `secondary` | a later history or site, repeating records not seen here | combinedfleet.com, Wikipedia, a division's printed booklet |
| `reference` | not a witness: charts, plates, terrain, grids | ONI 54, the Bezugspunktkarte, ETOPO1 |
| `derived` | a method, not an outside source | a grid reference decoded |

There is no `side`. An entry's actor is a subject, whose nationality the registry knows, or a name as the record
gives it with its nationality (`of`) beside it. Who faced whom follows from the frame's subjects; where three
nationalities meet and nationality alone cannot say, the engagement names `against:` (Algiers: `[de, it]`, so No. 153
Squadron's record is not coloured as the enemy's). A convoy is not a followed subject on an engagement: it is the
other side's record, read against the boats' sightings of it.

Not "Axis" and "Allied". They are the period's own words and historians still use them, but they are coalition words,
and the records are never that vague: the other side here is the Imperial Navy's 1st Surface Escort Division, XIV
Panzer Corps, Luftflotte 2, an Italian bulletin. The pair is also wrong at the edges the records reach: the French at
Oran in November 1942, Italy after September 1943. A nationality, as the record gives it, and never a bloc.

The pages have two **voices**, and the type carries them (`CLAUDE.md`, Pages):

- **The record's voice**: the words as typed, in the record's own language with the kit's translation beside it.
  Every entry whose record is not in English has `original`, `lang` and `translation`.
- **The kit's voice**: the account, the notes, the computed layers, the claims weighed. Everything in this voice is a
  **reconstruction**, and the page says so wherever it stands next to a record: the hatching and dashes on the map,
  *assumed* and *inferred* in the data (`basis`, `placed`), and a place of its own in the page's order (§4).

## 3. Views

Four views of one frame, each answering a different question. No view is forced into step with another.

| View | Question | What it is |
|---|---|---|
| **Map** | Where? | the subjects' movements, stations and events on the ground; with a clock and lanes when the tempo is clocked, static otherwise |
| **Chronology** | In what order, by whose account? | a spine of hours, days or months (by the tempo), one column per source, every entry at its time; an entry placed by the order of the account (`placed: seq`) says so; stations as bars, events as marks (`EV.chronology`, `site/chron.css`) |
| **Sources** | What does each source say, and where do they disagree? | for one moment or question: the entries from each source side by side, as typed and as placed, with the minutes and miles between them computed on the page (`Engage.apart`); under it the claims board, each answer badged with its source's kind (`EV.sources`) |
| **Story** | What is made of it? | the account in the kit's voice. A paragraph may carry a step (`[[step:id|words]]`), a step being the entries that name it; a step link sets the map, the clock and the view. The frame's own figures (scale drawings, an estimated path, the periscope) are panels registered in `site/panels.js` |

Which leads is decided by the tempo and nothing else:

- *clocked*: the map with its clock leads, the two-sided log beside it (the chronology at hour grain).
- *dated*: the chronology in day columns leads; the map is static, with no play button. The one exception is a frame
  with several days' situation maps (`fronts:`; Remagen, the Bulge): it steps through them on the clocked frames' own
  bar, a map at a time. The axis has a tick for each map's day, play steps and never glides, and the subjects'
  stations are drawn to the day shown.
- *monthly*: the journey's strip of stages leads, with the map under it.

The map's encodings are `guides/ENGAGEMENTS.md`'s, unchanged. Colour follows the **followed subject** (at most three,
the checked colours), whatever it is: in an Army frame the three colours are three batteries. The other side is ink
wherever it appears.

## 4. Two depths

Every frame page is one page that reads top to bottom, from the records' own summary to the records themselves to
the kit's figures, and behind it one more depth, where the questions are. The reader goes down by scrolling and
across by one switch, which sits under the lede and names each depth by what it holds.

### 4.1 The page

The title, the eyebrow (theatre · operation), the lede, the switch. Under it, in order:

1. **The outcome in the records' own terms**, beside *who* (the subjects with their silhouettes, each name a link to
   its own page) and *when* (the span, the clocks). Every number here is counted from the frame's own JSON, never
   written in. An engagement whose story has no *Outcome* section says so instead of inventing one.
2. **The map**, with its clock and lanes when the tempo is clocked (the clock opens stopped at the window's end, so
   every track and mark is shown), and the two-sided log beside it; the chronology under it when the frame is dated.
   A story told in steps sits beside the map as the narrative. Nothing here is the kit's except the GMT conversion
   and the placement of each mark, and both say how they were done (the zone letter beside each time; `basis` on each
   position). The convoy's observed path is dotted, and its caption says it is a reconstruction.
3. **The order of battle**, in silhouettes at the library's one scale.
4. **The story**, the narrative from `engagement.md`.
5. **The figures**, where the kit's voice leads and is labelled: the periscope and the Torpedo Data Computer, the
   frame's own panels, *closing in*, each with the assumptions it rests on stated under it.

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│ Pacific · Luzon Strait · Coordinated attack group, Capt. G. E. Peterson                          │
│ Convoy TAMA-17, 29–30 April 1944                                                                 │
│ BANG's first attacks: four approaches on a Takao–Manila convoy over one night, with PARCHE and   │
│ TINOSA closing in on her reports; beside them the convoy's own record of the same minutes.       │
│ ┌──────────────────────────────────────────────┬─────────────────────────────────────────┐       │
│ │ The engagement                               │ Questions and sources                   │       │
│ │ the outcome · the map with its clock ·       │ 4 questions the records leave open ·    │       │
│ │ 49 entries from 5 records · the story · …    │ answers side by side · how this was read│       │
│ └──────────────────────────────────────────────┴─────────────────────────────────────────┘       │
├──────────────────────────────────────────────────┬───────────────────────────────────────────────┤
│ Outcome, by the records                          │ Who   ▬ BANG  ▬ PARCHE  ▬ TINOSA  ╌ TAMA-17   │
│  Japanese loss list: Takegawa Maru, Nittatsu     │ When  29 Apr 0600 – 30 Apr 0800 GMT, 26 hours │
│  Maru, both to BANG. No loss matches …           │                                               │
├──────────────────────────────────────────────────┴───────────────────────────────────────────────┤
│ [the map, the clock stopped at the end: three tracks, the path dotted, two ✕]  │ [both sides' log]│
│ Order of battle · The story · At the periscope · Closing in                                      │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Questions and sources

Behind the switch (`?view=questions`): what the records leave open. The claims board (`claims.yml`), each answer
badged with the kind of evidence it is; the Sources view for each question more than
one source speaks to; and *how this was read*: the sources' section of `engagement.md`, what is still missing, and
the explainers for the notations the frame uses (§5.4). A question every answer of which comes from one source has
nothing to set side by side, so the board alone shows it.

### 4.3 Addresses

The two depths are one page with two parts, not two pages. An entry's address (`&at=1944-04-29T13:01Z`) opens the
page at that minute, a step's (`&step=s7`) at that step, and a claim's opens the questions. Addresses from the earlier
three-depth design (`view=account|records|working`) still arrive: on the page, or on the second depth for `working`.

A subject page (§5.2) has the same switch with three parts: the page, *Engagements* (`?view=engagements`) and, as its
second depth, *Placement and leads* (`?view=placement`).

## 5. Navigation

### 5.1 The shape of the site

```
Front page                 an index: the engagements by theatre, four theatre cards with one static figure each,
│                          the explainers, do this yourself, what's wanted
├─ Engagements             the way in: every engagement by theatre and in date order, each with its lede, its
│                          subjects and what its page holds (engagements.html)
├─ Theatre (4)             Pacific · Europe · Mediterranean · Atlantic (theatre.html?t=): its operations in date
│   │                      order (the spine), each with its engagements; its subjects; its explainers
│   ├─ Operation           what it was for and what it meant, cited; its area and dates; the engagements inside it;
│   │                      the subjects with stations inside it (context, not participation)
│   │   └─ Engagement      the page › questions and sources (§4)
│   └─ Subject (journey)   the page › engagements › placement and leads (§5.2)
├─ Subjects                the index of every subject (subjects.html)
├─ Reading the records     the explainers: time zones, the grids (Japanese, US Army, German), torpedo fire control,
│                          silhouettes
├─ Researching a relative
└─ About and method        what the kit covers, how it was read, and its limits (about.html)
```

`theatre.html` is one page for the four theatres, built by `site/chapter.js` from the theatre's file in
`records/operations/<theater>/index.md`: a static map of its records (the operations' hand-drawn areas hatched as
reconstructions, each engagement a mark, the subjects' tracks faint), the spine, the subjects, what is in the records
and still to find (`inventory.yml`), and the explainers its records need. A theatre's span is the one the records
cover, not the war's. The Mediterranean and Europe share five stages (Algiers, Sicily, Italy, France, Germany),
numbered across the two pages; the Pacific's spine is its engagements alone until an operation of its war is entered.

### 5.2 One subject page

`subject.html?s=<id>` is one journey page for a boat, a ship, a unit, a battalion, a convoy or a command. It opens on
the subject's card: the plain line as the eyebrow, the designation as the title, its silhouette, its organizations
over time, the periods of its record (patrols; months; voyages) and a strip map of the whole journey, stage by stage,
with a coverage bar saying which source gives each stage. A unit's stages follow the countries its stations cross; a
battalion's are calendar years, since no countries divide the Pacific. Under the card, on the same page, is the record
itself: the map with the date strip and the list of its own entries, each opening its scan. A stage row lands on it
at that patrol or day.

The panels that only one kind of record has are modules under `site/panels/`, loaded by record kind:

| Panel | Shown when the subject has |
|---|---|
| a boat's patrols or a ship's diary; attacks from the data sheets, with the Japanese record and the FRUPAC notes beside them (`patrols.js`) | `positions.csv`; `attacks.csv`, `japanese.yml`, `frupac.yml` |
| stations, actions and sea crossings, with the ship, her silhouette and the seafloor under the drawn line (`army.js`) | rows in `army/`; `army/ships.csv`, `routes.csv` |
| the parts and echelons, and the construction projects (`seabees.js`) | `parts.csv`; `seabees/projects/` |
| the convoy's voyage and its ships day by day (`convoy.js`) | `convoy.md` `ships:` |

BANG's dive profile is its own page (`dives.html`).

*Engagements*: the engagements the subject was in, in date order, a boat's grouped by patrol and anything else's by
year. Each is the Engagements index's row with a locator under the dates. A unit's "beside it" is by geometry (an
engagement whose box holds one of its stations inside its window) until a relation names the unit, and the page says
which it is.

*Placement and leads*: how each position was placed (at a town, by an offset, by a grid reference, assumed with a
headquarters), the speed check of the legs, the organizations with their pages, the leads and open questions about
the subject (`army/leads.yml`), and the sources' coverage month by month. Where a file has nothing for the subject,
the card says so.

### 5.3 The nav bar and the breadcrumb

The bar on every page is the shape of §5.1 and nothing else: *Engagements* first, the four theatres, *Subjects*,
*Reading the records*, *Researching a relative*, *About and method*. No ship, no view, no place. Its links live in `site/nav.js` alone,
which fills the placeholder on each page as the page is parsed, so adding a theatre is one edit.

The breadcrumb does the walking (`Chapter.trail`): *Pacific / the operation / Convoy TAMA-17*, and on a subject page
*Subjects / BANG / Patrol 1*. The engagement page's crumb adds the engagement before and after in its theatre and
each followed subject's own before and after. An engagement with no operation round it stands between the two
nearest.

### 5.4 The explainers, reached from the notation

The explainers (`zones.html`, `jgrid.html`, `grids.html`, `german.html`, `torpedo.html`, `silhouettes.html`) have
their shelf under *Reading the records*, and are also reached from wherever their notation appears. The notations are
`patterns` in `reference/glossary.yml` (a regular expression and a target each: a zone-lettered time, an Army grid
reference, a German reference point, a naval square, a kana code, a track angle, a gyro angle), checked by
`build_glossary.py`. `glossary.js` marks each distinct value once per passage, with a card that links the explainer
opened at that value, so no page writes the links by hand. The patterns know what is not a notation: `KG 54`,
`TF 58` and `Mk 14` are not grid references, a convoy's kana name is not a position code, and a lowercase word after
a zone letter ("At 1604 I sighted") leaves the time unmarked.

## 6. Visual hierarchy

The type's three voices and the colours are set out in `CLAUDE.md` (Pages) and `guides/ENGAGEMENTS.md`. The page's
order gives them their places: the eye should tell, without reading, which words are the record's.

| Element | Treatment |
|---|---|
| The frame's title and lede | the largest type on the page, in the kit's voice; the eyebrow above gives the theatre and operation |
| The outcome | a short paragraph, every sentence of which is a record's statement with its citation; never a verdict of the kit's |
| A subject | its name as the records give it, its kind in italics, its silhouette at the library's one scale |
| An entry | `entry.css`'s block: GMT at the left, the record's own time and zone at the right in the typed voice, the words typed, the note under it, the citation last |
| An original and its translation | the original first in its own voice and language, the translation under it, a little smaller |
| A computed layer | hatched or dotted on the map; in text, an italic *assumed* or *computed* with the assumption under the figure, not in a footnote |
| Depth | the top of the page has no controls; the map has the clock, the filters and the scan viewer; the figures have sliders and tabs; the questions have the board. A control is a sign the reader has gone down the page |

A page should read as a well-made entry in a reference work at the top, a chart-room sheet in the middle and a
researcher's desk at the bottom.

## 7. The two worked cases

### 7.1 Convoy TAMA-17, 29–30 April 1944

`records/engagements/tama-17-1944-04-29/`; `engagement.html?e=tama-17-1944-04-29`.

**The records.** Three war patrol reports on three clocks (BANG zone K, PARCHE zone I, TINOSA zone H:
`rg38-74802746`, `rg38-74828582`, `rg38-74856363`); the 1st Surface Escort Division's movements table and Nittatsu
Maru's movement table (JACAR `C08030140600`, `C08050103200`), in Tokyo time; the FRUPAC overlays of 29 and 30 April
(estimated positions, no zone written); combinedfleet.com for the convoy list (secondary); JANAC's credit
(assessment). Tempo: clocked.

**The page.** The wireframe in §4.1: three tracks, the convoy's observed path dotted, the two sinkings and the miss.
The outcome sets the Japanese loss list and BANG's claim side by side. The lanes under the map are one per followed
boat and one for the convoy's record. The FRUPAC notes are entries of kind *intelligence*, their positions hatched
(estimated from where the pencil mark sits on the overlay, zone I assumed and said on each): radio intelligence is a
source about the convoy, not a participant with a lane of its own.

**Questions and sources.** The build pairs each attack with the other side's record of it (`pairs`, from the patrol's
`claims.yml` and `japanese.yml`), and each pairing is a moment in the Sources view:

```
Attack 1 · the same minutes, source by source                                   minutes and miles computed here
┌─────────────────┬───────────────────┬────────────────────┬────────────────────┬──────────────────┐
│ BANG, sheet 1   │ Nittatsu Maru's   │ Escort division,   │ FRUPAC overlay     │ combinedfleet    │
│ record · us     │ table · record·jp │ April table · jp   │ intelligence · us  │ secondary        │
├─────────────────┼───────────────────┼────────────────────┼────────────────────┼──────────────────┤
│ 2256 K          │ 二二時〇一分         │ (Harukaze: 敵潜制圧) │ 2215/29            │ 29 Apr 1944      │
│ = 1256 GMT      │ 2201 I = 1301 GMT │ no time            │ = 1315 GMT, assumed│ no time          │
│ 19-26N 118-45E  │ 19-20N 118-50E    │                    │ 19.4 N 118.7 E     │                  │
│ "One 7000 ton AK│ the tenth ship,   │                    │ "Yoshima Maru /    │ Takegawa Maru    │
│  probably sunk" │ Takegawa Maru,    │                    │  att. by torp"     │ sunk, BANG       │
│ p16 ↗           │ p23 ↗             │ p15 ↗              │ map ↗              │ ↗                │
└─────────────────┴───────────────────┴────────────────────┴────────────────────┴──────────────────┘
Between BANG's sheet and the table: 5 min, 7.6 nm.  Between the sheet and FRUPAC: 19 min, 4 nm (FRUPAC's zone assumed I).
```

The columns are sources; the chips under each head give its kind and nationality; the arithmetic is done on the page
by `engage.js` and labelled. The claims board under it is `claims.yml`, each answer badged by its source's kind.
Repetition isn't corroboration: a secondary source repeating the loss list is one column, and the board merges
repeated answers and counts them once. A FRUPAC note tied to an attack with no Japanese pairing is an entry and a
mark but no moment, since moments are pairings.

**The journeys.** From the names at the top of the page: BANG's subject page at patrol 1
(`subject.html?s=bang&period=1`), the convoy's (`subject.html?s=tama-17`) with its ships day by day, and the lane's
month (`lanes.html`). The crumb gives TE-04, four days later, as the next engagement.

### 7.2 The Medical Detachment, 67th Coast Artillery (AA), 1942–1945

`army/units.csv` `67ca-med`; `subject.html?s=67ca-med`.

**The records.** 62 station rows in `army/stations.csv` from 1 September 1942 (Paterson, N.J.) to 14 May 1945
(Hüttenfeld): the detachment's own morning reports through December 1944, the Regimental Headquarters Battery's for
the months its own are missing (`source=regt`, assumed), and the 894th's printed history for 1945 (the battalion's
position, the detachment assumed with it). Three sea crossings in `army/ships.csv`; the Atlantic and the train rides
as assumed routes (`routes.csv`). Tempo: monthly.

**The page.** The journey in five stages, with one sentence per stage in the records' words and a coverage bar under
each: *own morning reports*, *regimental headquarters' (assumed)*, *the battalion's history*. The engagements along
the way are stops on the strip, and the page is honest about them: Venafro is batteries E, H and A's engagement, the
detachment's own record for those weeks says only where it was, so the strip marks it *beside it*, not *in it*. The
operations from Torch to Central Europe are a band under the strip: context, each linking to its place on the theatre
page. Under the strip, the record: the map with the date strip, the stations as typed with their pages, the crossings
opened from the station they start at.

**Placement and leads.** The placement table; the speed check of the legs (a motor convoy's eight miles in an
afternoon is fine; a station a day's march off the route is a question); the organizations as a dated list with their
pages; and the coverage month by month, which is the answer to "how is it known where it was in March 1943?" (*the
regimental headquarters battery's report; the detachment's own are missing; assumed with regimental headquarters*).

## 8. What the records carry for the pages

Hand-edited, each checked by a build or the lint:

| Field or file | Where | For |
|---|---|---|
| `kind`, `of` on every source | `records/SOURCES.yml` | the voices (§2.4) |
| `original`, `lang`, `translation` on every entry not in English | `events.yml`, `japanese.yml` | one rule for every language |
| `of` on a participant, an entry or a position; `against:` on an engagement where nationality can't say who faced whom | `engagement.md`, `events.yml`, `positions.csv` | no `side` (§2.4) |
| `plain` on every subject | `army/units.yml`, `seabees/units.yml`, `ship.yml`, `convoy.md`, `command.yml` | the name a reader can follow (§2.1) |
| the relations of each dataset | `army/relations.csv`, `seabees/parts.csv`, a convoy's `ships:`, ComSubPac's `task_organization.csv` | organizations (§2.1) |
| `leads.yml`: `statement`, `said_by`, `searched`, `still`, `ref` | `army/leads.yml` | statements about a unit no cited page supports yet, with what was searched; a lead resolved becomes a row |
| `operation:` on an engagement, optional | `engagement.md` front matter | only when the placement by area and date is wrong |
| `views`, `steps`; `[[step:id|words]]` in prose | `engagement.md`, `site/links.js` | the story sets the map and the clock (§3) |
| `fronts:`, `relief:`, `roads:` | `engagement.md` front matter | the situation maps and the ground under a dated frame |
| the notations as `patterns` | `reference/glossary.yml` | the explainers reached from the notation (§5.4) |

Generated: `subjects.json`, `engagements/*/engagement.json`, `engagements/index.json`, `operations/operations.json`.

Derived on the page, never stored: a frame's tempo; a subject's stages; which view leads; the minutes and miles
between two entries; a source's columns; a unit's coverage by month.

## 9. How the pages came to this

The model replaced four separate apps (`patrols.html`, `army.html`, `seabees.html`, `convoys.html`) and two
hand-built story pages (`haynsworth.html`, `algiers.html`) in seven phases in November 2026: one skin, the depths,
the chronology, the voices, the stories folded in, the subjects (phase 6, which the panels' comments cite) and the
theatres. The old addresses are one-line redirects that carry their parameters across, kept so links from outside
still arrive. The phases, what each deleted and what the records taught along the way are in
`guides/design-history/2026-11-operations-viewer.md`; the mockups in `guides/mockups/` date from the same design and
are not live pages.

## 10. Open questions

- **Colour for more than three followed subjects.** The 62nd CA (AA) has fourteen units with stations around Oran and
  Algiers in 1942–43. Small multiples (one map per battery at one scale) or a picker: to be tried on the 62nd and the
  20th NCB.
- **The convoy's own page.** Its observed path is computed from the boats' ship contacts and the Japanese positions.
  On the convoy's page it is the lead layer and it is a reconstruction; the page must say so in its first line.
- **Operations of the war at sea.** None is entered for the Pacific or the Atlantic. The lanes' month-by-month view
  is the nearest thing to that war's own frame.
- **Dates beside times.** The engagement page prints no date beside its times, so a zone card gives the offset and
  not the GMT until the page carries `data-date` (the hook is in `glossary.js`).
- **Map layers the story pages had.** Haynsworth's picket ring, formation schematic and assumed route, and Algiers'
  reach ring, have no place on the generic map yet; each would be a further panel.
- **The family seam.** A person is never a subject of the kit. A family's own site attaches one to a subject by date
  on its own pages: `subject.html` accepts `&who=…&t=…` beside `s=` and ignores `who`, so a family's script may read
  it there, and `[[who:…]]` in `site/links.js` resolves only on a family's pages. The lint keeps refusing a person's
  name in `records/` (PRV001).
