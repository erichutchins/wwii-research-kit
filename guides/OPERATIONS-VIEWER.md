# The operations viewer: one model for ships, units and the war around them

A design for the pages, written against the records as they stand on 3 November 2026. It reconsiders the mental model
the site grew up with (a submarine pack against a convoy, replayed on one clock) and proposes the one the records now
need: subjects and the organizations they belong to; their movements, stations and events; the frames we put round
them; the sources each claim rests on; and three depths of reading, from a clean account to the working. Nothing here
changes a transcription rule. Everything here is checked against two cases: convoy TAMA-17 in the Luzon Strait, 29–30
April 1944 (three patrol reports, a Japanese escort diary and a ship's movement log, the FRUPAC overlays, two secondary
sources), and the Medical Detachment, 67th Coast Artillery (AA), from Paterson, New Jersey in September 1942 to
Hüttenfeld, Germany in May 1945. Four screens of it are drawn, from the records' own values, in `guides/mockups/`
(open them in a browser; nothing in them is live): the TAMA-17 account and its Sources view for Attack 1, the Medical
Detachment's account, and Venafro's chronology.

The rules of `CLAUDE.md`, `guides/METHODS.md` and `guides/ENGAGEMENTS.md` stand throughout: cite every entry, keep each
record's own structure, compute rather than store, label every assumption, repetition isn't corroboration, no numbers on
conclusions, name the other side as the records do, and follow units and ships, never people.

## 1. Where the present model strains

The site has one cross-source page type, the engagement (`engagement.html?e=…`): *two sides meeting at a place and a
time, each in its own records, on one map and one clock*. It is exactly right for what it was built for. The strain
shows where the records don't fit that sentence.

| Symptom | Where it shows | What it tells us |
|---|---|---|
| A clock with nothing to play | Venafro, February 1944: every entry is a day, `placed: seq`; the German reports are "the same day and nearly the same place at most". Remagen, the 9th Armored: division positions by day | The engagement's lead view (map + clock + lanes) assumes a tempo of minutes. Many frames have a tempo of days or months |
| Hand-built pages beside the generic one | `haynsworth.html` (1,146 lines of its own script), `algiers.html` (479), each with steps, a day-column timeline, scale drawings, an evidence board; `chapter.js` names them as the engagement's "own page" | The generic page has no place for a story told in steps, a chronology in day columns, or a frame-specific working figure, so each one grew a page |
| Four side-list apps for one idea | `patrols.html`, `army.html`, `seabees.html`, `convoys.html` each draw one subject's own record: a map, a date strip, a list of its entries, a scan viewer. Two families of CSS tokens (`viz.css` `--text-primary`; `engage.css` `--ink`), bridged by `entry.css` | The subject's own page is one page type with record-specific panels, not four |
| The nav lists a ship | The bar on every page: theatres (Pacific), places (Algiers, Sicily, …), record types (Ship tracks, Army units), one ship (Haynsworth), one view (Dives), and the explainers | There is no navigation model, so the bar is a list of what exists. It can't take a tenth engagement or a second destroyer |
| `side` does three jobs | `us, jp, allied, axis, de, press, geo`: a nationality, a belligerent, a kind of source (the press), and "a place" | The press is not a side. A newspaper, a radio-intelligence overlay, a postwar assessment and an escort's diary are *kinds of source*, each with its own weight, and the page should show them as such. And a coalition word is vaguer than the records, which always name a navy, a corps, a squadron |
| The units' names are opaque | "Medical Detachment, 67th CA (AA) / 894th AAA AW Bn", "Btry D, 106th AAA AW Bn (SP)": the designations are the records', and with the family's names kept out of the public repository they are the only names there are | A reader needs to be told, in a line, what each unit was before its designation means anything |
| The other side's words are typed two ways | A Japanese entry has `original` and `translation`; a German one quotes the original inside `words` with the translation in parentheses | One rule for every language the records speak |
| The reconstruction sits inside the record | The convoy's observed path, "closing in", the estimated kamikaze path, the periscope view are drawn from the records but are ours; they share the page with the entries as typed | The reader needs to see at a glance which marks are the record's and which are our working. The encodings (solid, hatched, dotted) carry this on the map; the page's structure doesn't yet |
| Organization lives in three shapes | `army/relations.csv` (part of, attached to, under command, took part), `seabees/parts.csv` (echelons and sections), a convoy's `ships:` list, ComSubPac's task organization | One idea, dated membership of one subject in another, each row cited |
| Leads live in a README table | `army/README.md` "Leads": statements no cited page supports yet, with what was searched | The same shape as `claims.yml`'s open questions, and the reader never sees them |

None of these is a defect in the records. They are the signs of a model built for one kind of record now carrying
five.

## 2. The model

Four kinds of thing, each with a word the pages use consistently. The records already hold all four; the change is to
name them and build the pages on them.

### 2.1 Subjects and organizations

A **subject** is something the records follow: a boat (`boats/ss-385-bang`), a ship (`ships/dd-700-haynsworth`), an
Army unit (`army/units.csv`: a battery, a company, a detachment, a division), a Seabee battalion or a part of one
(`seabees/units.csv`, `parts.csv`), a convoy (`convoys/hi-67`), a force or command (`commands/comsubpac`), and the
other side's as the records name them (Harukaze; 5. Geb.Div.; No. 153 Squadron RAF). Every subject has an id, a name as
the records give it, a kind, and the records that are its own.

An **organization** is dated membership of one subject in another, each row cited: Battery D *part of* the 106th AAA AW
Bn; the 9th Armored *attached to* Third Army from 9 January 1945; BANG *in pack* 17.x with PARCHE and TINOSA; Takegawa
Maru *in convoy* TAMA-17 as its tenth ship; the Forward Echelon *part of* the 20th NCB from 13 May 1943; the 67th CA
(AA)'s 2nd Battalion *redesignated* the 894th AAA AW Bn on 20 March 1944. `army/relations.csv` has the shape (unit,
relation, other, from, to, basis, page, note); the convoy's `ships:`, the battalion's `parts.csv` and ComSubPac's
`task_organization.csv` say the same thing in their own records and should be read into the same registry by the
build.

**People are not subjects here.** The kit's rule stands: the records are the units', no one is followed by name, and
names the records carry stay as written in the entry that carries them. A family's own site attaches a person to a
subject by date (`[[who:…]]` in `site/links.js`, `army.html?who=`); the model leaves that seam where it is and puts
nothing on the kit's side of it. The family site is not built yet; the seam is reserved, not used.

**Name a unit first by what it was.** With people's names out of the public records, a unit's designation is its only
name, and "Medical Detachment, 67th CA (AA) / 894th AAA AW Bn" tells a reader nothing. Each subject gets a `plain` line
in our voice (in `units.csv`, `ship.yml`, `convoy.md`): what kind of thing it was and what it did, in a sentence a reader
without the Army's vocabulary can follow (*the aid men of an anti-aircraft regiment, a section with each battalion*;
*a fleet submarine of the Balao class, on her first patrol*; *a Takao–Manila convoy of seventeen ships and escorts*). The
pages lead with the plain line as the eyebrow and give the designation as the title; lists and breadcrumbs show both.
The designation stays exactly as the records write it, and a redesignation is an organization row, not a second name.

### 2.2 Movements, stations and events

Everything a record says a subject did is one of three things:

| Primitive | Meaning | Where the records already hold it |
|---|---|---|
| **Movement** | from here at one time to there at another | a track's fixes (`positions.csv`, `on_track=yes`), a sea crossing (`army/ships.csv`, `seabees/voyages.csv`, `voyage_positions.csv`), a convoy's `voyage`, a leg the record doesn't trace (`routes.csv`: always assumed) |
| **Station** | here from one time until the next change | the STATION line (`army/stations.csv`, `seabees/stations.csv`: a row lasts until the next), a boat under refit or in port (ComSubPac's `disposition.csv`), a picket station (`kind: station`), a battery's gun position |
| **Event** | at a time (or placed), here, something happened | an attack, a hit, a sinking, a depth charging, a sighting, a message sent and received, a raid fired on, a casualty, a communiqué (`events.yml`, `attacks.csv`, `depths.csv`, `army/actions.csv`, `japanese.yml`, `frupac.yml`) |

The distinction matters for the pages because each is drawn and read differently: a movement is a line (solid where
fixed, dashed between fixes, dotted where assumed), a station is a stay (a mark that holds, a bar on a chronology), an
event is a point in time (a mark, an entry). A unit's war is mostly stations; a patrol is mostly movement; an attack
is events. The same chronology can hold all three, and the same map.

### 2.3 Frames

A **frame** is what we put round a set of subjects and a span of time to ask a question. There are three, at three
scales, and the records already have folders for all of them:

| Frame | Question | Scale | Records | Today's page |
|---|---|---|---|---|
| **Journey** | Where was this subject, and what did it do, in its own record? | a patrol, a voyage, a unit's year, a battalion's war | a boat's `patrol-N/`, a ship's `positions.csv`, a unit's rows in `army/`, a battalion's in `seabees/`, a convoy's `convoy.md` | `patrols.html`, `army.html`, `seabees.html`, `convoys.html` |
| **Engagement** | What happened when these subjects met, each in its own records? | minutes to a month | `engagements/<id>/` | `engagement.html`, `haynsworth.html`, `algiers.html` |
| **Operation** | What was the war doing here, and what did it mean? | a campaign, an operation, a phase | `operations/<theater>/<id>.md` | the front page's stages (`chapter.js`); no page of its own |

Frames nest and cross. An engagement lies inside an operation (Venafro inside the Cassino fighting) or between two; a
journey crosses many engagements and operations (the Medical Detachment's war crosses Torch, Tunisia, Salerno, the
Winter Line, Dragoon, the Rhineland). The ladder the pages walk is **theatre → operation → engagement → entry**, and
the thread that crosses it is the **subject**: from any engagement, each subject's journey before and after
(`chapter.js`'s "Follow a unit" already does this for Europe). An operation is **context, not participation**: a unit
with stations inside its area and dates is a lead until its own record says it took part (`operations/README.md`).

A frame's **tempo** is derived from its entries, never stored: *clocked* when entries carry times with a zone (one clock
is meaningful: TAMA-17, Haynsworth); *dated* when they carry days (Venafro, Algiers' three nights, a convoy's voyage);
*monthly* when a journey spans years (a unit's war). The tempo decides which view leads (§3).

### 2.4 Sources and voices

Every entry already cites a page in a form `records/SOURCES.yml` knows. The proposal adds **one hand-edited field per
source entry there** (not per row): what kind of source it is, and whose.

| `kind` | Meaning | Examples in SOURCES.yml |
|---|---|---|
| `record` | written at the time by the subject or its command | war patrol reports, war diaries, morning reports, muster rolls, the escort divisions' war diaries, XIV Panzer Corps' Tagesmeldungen |
| `intelligence` | what one side knew of the other at the time | the FRUPAC overlays |
| `press` | published at the time | L'Écho d'Alger (`gallica:`), the Allied communiqués, the Italian and German bulletins |
| `assessment` | an official reckoning after the fact | JANAC |
| `recollection` | told later by someone who was there | Irons (Haynsworth) |
| `secondary` | a later history or site, repeating records we haven't seen | combinedfleet.com, Wikipedia, the G.I. Stories booklet |
| `reference` | not a witness: charts, plates, terrain, grids | ONI 54, the Bezugspunktkarte, ETOPO1 |
| `derived` | a method, not an outside source (already there) | a grid reference decoded |

and `of`: the nationality of the source's author (`us`, `jp`, `de`, `it`, `uk`, `fr`, …), which is what today's `side`
mostly means. The build then tags every entry, claim, station and fix with its source's kind and nationality through
its citation. `side` goes altogether: an entry's actor is a subject (whose nationality the registry knows) or a name as
the record gives it with its nationality beside it, and who faced whom in a frame follows from its subjects.
`check_sources.py` fails on a source without a kind.

Not "Axis" and "Allied". They are the period's own words for the coalitions and historians still use them, so they are
not dated; but they are coalition words, and the records are never that vague: the other side in these records is the
Imperial Navy's 1st Surface Escort Division, XIV Panzer Corps, Luftflotte 2, an Italian bulletin. The pair is also wrong
at the edges the records reach: the French at Oran in November 1942, Italy after September 1943. The rule already
says it: name the other side as the records do. So a nationality, as the record gives it, and never a bloc.

This gives the pages two **voices**, and the type already has them (`CLAUDE.md`, Pages):

- **The record's voice**: the words as typed, in TT2020 (`.typed`), in the record's own language with our translation
  beside it. Rule: every entry whose record is not in English has `original`, `lang` and `translation`, as the Japanese
  entries do now; a German report's words move out of `words` into `original` (`lang: de`), the translation into
  `translation`. Shippori Mincho for `lang="ja"`; the typed voice for `lang="de"` (the Tagesmeldungen were typed).
- **Our voice**: the account, the notes, the computed layers, the claims we weigh, in ET Book. Everything in this voice
  is a **reconstruction**, and the page says so wherever it stands next to a record: the hatching and dashes on the
  map, *assumed* and *inferred* in the data (`basis`, `placed`), and now a place of its own in the page's structure
  (§4).

## 3. Views

Four views of the same frame, each answering a different question. They are complementary. No view is forced into
synchrony with another: the clock is one view's device, not the page's.

| View | Question | What it is | Tempo it suits |
|---|---|---|---|
| **Map** | Where? | the subjects' movements, stations and events on the ground; with a clock when the tempo is clocked (today's engagement map and lanes), without one otherwise (a static map with the marks, a date strip at most) | all |
| **Chronology** | In what order, by whose account? | a spine of time (hours, days or months, by the tempo), one column per source (or per side when there are many sources, each side opening into its sources), every entry at its time; `placed: seq` entries in italics; stations as bars, events as marks, movements as arrows between stations | all; it is the lead view for dated and monthly frames |
| **Sources** | What does each source actually say, and where do they disagree? | for a moment or a question: the entries from each source side by side, as typed and as placed by us, with the minutes and miles between them computed on the page (`check_crossrefs.py`'s arithmetic, moved into `engage.js`); under it the claims board, each answer with its source's kind | all |
| **Story** | What do we make of it? | the account in our voice, in steps that set the other views (a paragraph can carry a step, as `events.yml`'s `step` does for Haynsworth and Algiers), with the working figures a frame has (scale drawings, an estimated path, the periscope, the dive profile) | all |

Which leads is decided by the tempo and nothing else:

- *clocked*: Map with the clock leads, Chronology beside it (today's two-sided log is the chronology at hour grain).
- *dated*: Chronology in day columns leads (Algiers' "nights side by side" is the prototype; it becomes a shared view in
  `engage-views.js` and `algiers.html`'s own copy goes); the Map is static with the places and stations, no play button.
- *monthly*: the journey's strip (stages, as `chapter.js` computes them) leads, with the Map under it.

The map keeps its encodings as they are (`guides/ENGAGEMENTS.md`, "Encodings"); they are the model's first implementation
and they hold: solid from the record, outlined from a secondary source, hatched inferred, dotted assumed, dashed between
known points, red only for hits. Colour follows the **followed subject** (at most three, the checked colours), not "the US
boat": in an Army frame the three colours are three batteries; the other side is ink wherever it appears.

## 4. Three depths

Progressive disclosure is the page's structure, not an afterthought. Every frame page has three depths, and the reader
chooses to go down.

### 4.1 The account (what you see first)

One screen, two at most. The title, the eyebrow (theatre · operation), the lede, **the outcome in the records' own
terms**, the subjects with their silhouettes, the span, a **static** map (the tracks and the marks, no clock), and one
summary line per side: *BANG fired 24 torpedoes in four attacks; the Japanese record has two ships sunk and one
missed*. Then three doors: *the records* (how many entries, from how many sources, in how many languages), *the
working* (how many questions the records leave open), and the subjects' own journeys. Nothing on this screen moves,
nothing needs a hover, and every number on it is the records' or says it is ours.

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│ Pacific · Luzon Strait · Coordinated attack group, Capt. G. E. Peterson                          │
│ Convoy TAMA-17, 29–30 April 1944                                                                 │
│ BANG's first attacks: four approaches on a Takao–Manila convoy over one night, with PARCHE and   │
│ TINOSA closing in on her reports; beside them the convoy's own record of the same minutes.       │
├──────────────────────────────────────────┬───────────────────────────────────────────────────────┤
│                                          │ Outcome, by the records                               │
│   [static map: three tracks, the        │  Japanese loss list: Takegawa Maru, Nittatsu Maru,     │
│    convoy's observed path dotted,        │  both to BANG. No loss matches PARCHE's or TINOSA's   │
│    two red ✕, one red ring]              │  attacks next morning.                                │
│                                          │ Who                                                   │
│                                          │  ▬ BANG  ▬ PARCHE  ▬ TINOSA   ╌ Convoy TAMA-17 (9)    │
│                                          │ When    29 Apr 0600 – 30 Apr 0800 GMT (26 h)          │
├──────────────────────────────────────────┴───────────────────────────────────────────────────────┤
│ The records ›  44 entries · 5 records · 2 languages · 27 fixes   The working ›  3 pairs, 4 open  │
│ Journeys ›  BANG patrol 1 · PARCHE patrol 1 · TINOSA patrol 6 · convoy TAMA-17 · the lane        │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 The records (on demand)

The frame's entries, every one as typed and linking to its page. This is today's engagement page: the map with its
clock and lanes when the tempo is clocked; the chronology; filters by subject, side, source kind and entry kind; the
record's voice throughout, with originals and translations. Nothing here is ours except the GMT conversion and the
placement of each mark, and both say how they were done (the zone letter beside each time; `basis` on each position).

### 4.3 The working (on demand)

Where our voice is allowed to lead, and labelled: the Sources view for each question; the claims board (`claims.yml`)
and the leads (`leads.yml`, §8) under *what the records leave open*; the computed layers (the convoy's observed path and
*closing in*, the estimated path, the sky, the firing solution) each with the assumptions it rests on stated under it;
the frame's own figures (the periscope and the Torpedo Data Computer, the dive profile, Haynsworth's frames and the
Judy to scale); the cross-references (minutes and miles between a pair of entries); and *how this was read*: the
sources' section of `engagement.md`, the explainers for the notations the frame uses (§5.4).

The three depths are one page with three parts (`?view=account|records|working`, the account by default), not three
pages: the address of an entry (`&at=1944-04-29T13:01Z`) opens the records depth at that minute, and a claim's address
opens the working at that question. A story page's steps (Haynsworth's, Algiers') become the account's and the records'
narrative, so the two hand-built pages become two engagements with their own working figures registered, and `OWN_PAGE`
in `chapter.js` goes.

## 5. Navigation

### 5.1 The shape of the site

```
Front page                 the theatres, each with its featured frames; what's new; what's wanted; do this yourself
├─ Theatre (4)             Pacific · Atlantic · Mediterranean · Europe: its operations in date order (the spine), each
│                          with its engagements; its subjects; its explainers ("reading the records here")
│   ├─ Operation           what it was for and what it meant, cited; its area and dates; the engagements inside it;
│   │                      the subjects with stations inside it (context, not participation)
│   │   └─ Engagement      account › records › working (§4)
│   └─ Subject (journey)   account › records › working: the subject's own record, period by period (a patrol, a month,
│                          a voyage); the engagements it was in as stops; the operations around it as a band
├─ Reading the records     the explainers: time zones, the three grids, torpedo fire control, silhouettes, the glossary
├─ Researching a relative
└─ Do this yourself
```

Today's `index.html` carries the theatres, the stages, the fleet list and the featured replays on one long page. The
theatres become pages of their own (`theatre.html?t=pacific`), each built as "Algiers to Germany" is built today
(`chapter.js`: operations as the spine, engagements under them, subjects' runs through the stages), and the front page
becomes an index with one featured figure per theatre, static. The Europe chapter's five stages (Algiers, Sicily,
Italy, France, Germany) are that theatre's own grouping and stay.

### 5.2 One subject page

`subject.html?s=<id>` replaces the four side-list apps. Its account is the subject's card: name as the records give
it, kind, silhouette, its organizations over time (a dated list: part of, attached to, in pack, in convoy), the
periods of its record (patrols; months; voyages) and how far each is along (`inventory.yml`'s status), and a static map
of the whole journey. Its records depth is the map with the date strip and the list of its own entries, which is what
the four apps draw now; the panels that only one kind of record has are shown only when it has them:

| Panel | Shown when the subject has |
|---|---|
| dives and depth charges (today `dives.html`) | `depths.csv` |
| attacks from the data sheets, the Japanese record and the FRUPAC notes beside them | `attacks.csv`, `japanese.yml`, `frupac.yml` |
| sea crossings with the ship, her silhouette and the seafloor under the drawn line (today `army.html` "How they travelled") | `army/ships.csv`, `routes.csv` |
| the parts and echelons (today `seabees.html`) | `parts.csv` |
| the ships of the convoy day by day (today `convoys.html`'s roster) | `convoy.md` `ships:` |
| construction projects | `seabees/projects/` |

Its working depth: the leads and open questions about the subject, the placement bases (how many stations are at a
town, an offset, a grid reference, a headquarters assumed), the speed check's results, the sources' coverage month by
month (§7.3).

The four apps are the first version of these panels, not wasted work: `patrols.js`, `army.js`, `seabees.js` and
`convoys.js` each become a panel module the subject page loads by record kind, and the four CSS token sets become one.

### 5.3 The nav bar and the breadcrumb

The bar on every page is the shape of §5.1 and nothing else: the four theatres, *Subjects*, *Reading the records*,
*Researching a relative*. No ship, no view, no place. It is one HTML fragment every page includes (`footer.js` already
writes the footer this way), so adding a theatre is one edit.

The breadcrumb does the walking: *Pacific / the Luzon Strait, April–May 1944 / Convoy TAMA-17 / Attack 1*, and on a
subject page *Subjects / BANG / Patrol 1 / 29 April*. `chapter.js`'s crumb (stage, campaign, the engagement before and
after, each unit's step before and after) is the breadcrumb for every theatre, not Europe alone: an engagement with no
operation round it stands between the two nearest, as it does now.

### 5.4 The explainers, reached from the notation

The explainers (`zones.html`, `jgrid.html`, `grids.html`, `german.html`, `torpedo.html`, `silhouettes.html`) keep their
shelf under *Reading the records*. They are also reached from wherever their notation appears: a time with a zone
letter (`2201 I`) carries a link to the zones page at that letter; a grid reference (`V-044572`, `XXIII 97`, `CJ 9472`)
to the grid page at that grid; a kana code (`メキ三ツ`) to the Japanese grid page; a track angle or gyro on an attack
sheet to the torpedo page; a silhouette to its plate. `glossary.js` already marks terms on first use and opens a card
with the explanation and its source; the notations become glossary patterns (a regular expression and a target per
notation, in `reference/glossary.yml`), so no page writes the links by hand. Each theatre page lists the explainers its
records need ("reading the records here", as the stages do now).

## 6. Visual hierarchy

The type's three voices are the backbone, and the depths give them their places: ET Book for the account and the
working; TT2020 for every typed word of a record; Shippori Mincho for Japanese. The eye should be able to tell, without
reading, which words are the record's. No capitals for labels, italics instead.

| Element | Treatment |
|---|---|
| The frame's title and lede | the largest type on the page, in our voice; the eyebrow above it gives the theatre and operation |
| The outcome | a short paragraph in our voice, every sentence of which is a record's statement with its citation; never a verdict of ours |
| A subject | its name as the records give it, in small capitals' place an italic kind, and its silhouette at the library's one scale |
| An entry | `entry.css`'s block: our time at the left, the record's own time and zone at the right in the typed voice, the words typed, the note in our voice under it, the citation last |
| An original and its translation | the original first in its own voice and language, the translation under it in ours, a hair smaller |
| A computed layer | hatched or dotted on the map; in text, an italic *assumed* or *computed* with the assumption under the figure, not in a footnote |
| The colours | the three checked colours for the followed subjects, ink for everyone else, red for hits only; text never wears a colour except a subject's own label |
| Depth | the account has no controls; the records have the clock, filters and the scan viewer; the working has the sliders and the tabs. A control is a sign the reader has gone down a depth |

A page should read as a well-made entry in a reference work at the top, a chart-room sheet in the middle, and a
researcher's desk at the bottom.

## 7. The two test cases

### 7.1 Convoy TAMA-17, 29–30 April 1944 (`records/engagements/tama-17-1944-04-29/`)

**What the records are.** Three war patrol reports on three clocks (BANG zone K, PARCHE zone I, TINOSA zone H:
`rg367-74802746`, `74828582`, `74856363`); the 1st Surface Escort Division's movements table and Nittatsu Maru's
movement log (JACAR `C08030140600`, `C08050103200`), in Tokyo time; the FRUPAC overlays of 29 and 30 April
(`metapth1733008`, …; estimated positions, no zone written); combinedfleet.com for the convoy list and the 3–4 May
sinkings (secondary); JANAC's credit (assessment). Tempo: clocked.

**The account.** The wireframe in §4.1. The static map shows the three tracks, the convoy's observed path dotted (ours,
and the caption says so), the two sinkings and the miss. The outcome quotes the loss list and BANG's claim side by
side in two sentences. The doors: 44 entries from five records in two languages (the three narratives, Nittatsu Maru's
log and the escort division's diary) and 27 fixes; the working's three attack–record pairs from BANG's `claims.yml`
and the four open items that today sit in `guides/ENGAGEMENTS.md`'s "Open work" (this engagement has no `claims.yml`
of its own, which is what `leads.yml` in §8 is for); the three patrols, the convoy and the lane.

**The records.** The page as it is today, with two changes. The lanes under the map are per followed subject (the three
boats) and one for the convoy's record, as now; the log beside it becomes the chronology at hour grain, its columns the
sources (BANG's narrative, BANG's attack sheets, PARCHE, TINOSA, the escort division, Nittatsu Maru's log), collapsible
to two sides on a phone. The FRUPAC notes appear here as entries in their own column, kind *intelligence*, their
positions on the map hatched (estimated from where the pencil mark sits), not as a third side with a lane of its own:
radio intelligence is a source about the convoy, not a participant.

**The working.** Three figures the frame already has (the periscope and the TDC for each attack with a sheet; *closing
in*; the sky) stay as they are, under their assumptions. The Sources view, new, is where this frame earns the model:

```
Attack 1 · the same minutes, source by source                                   minutes and miles computed here
┌─────────────────┬───────────────────┬────────────────────┬────────────────────┬──────────────────┬───────────────┐
│ BANG, sheet 1   │ Nittatsu Maru's   │ Escort division,   │ FRUPAC overlay     │ combinedfleet    │ JANAC         │
│ record · us     │ log · record · jp │ April table · jp   │ intelligence · us  │ secondary        │ assessment    │
├─────────────────┼───────────────────┼────────────────────┼────────────────────┼──────────────────┼───────────────┤
│ 2256 K          │ 二二時〇一分         │ (Harukaze: 敵潜制圧) │ 2215/29            │ 29 Apr 1944      │ 29 Apr 1944   │
│ = 1256 GMT      │ 2201 I = 1301 GMT │ no time            │ = 1315 GMT, assumed│ no time          │ no time       │
│ 19-26N 118-45E  │ 北緯一九度二〇分 …   │                    │ 19.4 N 118.7 E     │                  │ 19-26N 118-45E│
│ as typed        │ 19-20N 118-50E    │                    │ estimated ±0.2°    │                  │ (BANG's)      │
│ "One 7000 ton AK│ 第十番船竹川丸 …     │                    │ "Yoshima Maru /    │ Takegawa Maru    │ Takegawa Maru │
│  probably sunk" │ the tenth ship,   │                    │  att. by torp"     │ sunk, BANG       │ 1,930 t, BANG │
│ Sunk: None.     │ Takegawa Maru,    │                    │                    │                  │ not probable  │
│                 │ torpedoed         │                    │                    │                  │               │
│ p16 ↗           │ p23 ↗             │ p15 ↗              │ map ↗              │ ↗                │ 4/p58 ↗       │
└─────────────────┴───────────────────┴────────────────────┴────────────────────┴──────────────────┴───────────────┘
Between BANG's sheet and the log: 5 min, 7.6 nm.  Between the sheet and FRUPAC: 19 min, 4 nm (FRUPAC's zone assumed I).
What the records leave open
 ◼ record      Which ship did Attack 1 hit?  Takegawa Maru (the log, J03)        ◻ intelligence  "Yashima Maru" (F01, F02)
 ◼ assessment  JANAC credits her to BANG     ◇ inference  Yashima may be a misread intercept or another ship (our note)
```

The columns are sources, the chips under each column head its kind and nationality, and the arithmetic (zone to GMT,
the distance between two positions) is done on the page by `engage.js` and labelled. The claims board under it is
`claims.yml` as it is, each answer badged by its source's kind instead of its own `weight` where the two agree, and
`weight` kept where a record is used as a recollection would be. Repetition isn't corroboration: combinedfleet and
JANAC repeating the loss list show as one column each, and the board counts them once.

**The journeys.** From the account's doors: BANG's subject page at patrol 1 (`patrols.html?ship=bang&patrol=1` today),
with her dives and the FRUPAC notes beside each attack; the convoy's page (`convoys.html?c=tama-17` today) with its
ships day by day; the lane's month (`lanes.html`). The breadcrumb: *Pacific / the Luzon Strait, April–May 1944 /
TAMA-17*, with TE-04 four days later as the next engagement.

### 7.2 The Medical Detachment, 67th Coast Artillery (AA), 1942–1945 (`army/units.csv` `67ca-med`)

**What the records are.** 62 station rows in `army/stations.csv` from 1 September 1942 (Paterson, N.J.) to 14 May
1945 (Hüttenfeld), from the detachment's morning reports (NARA rolls 792–794) through December 1944, the Regimental
Headquarters Battery's for the months the detachment's own are missing (`source=regt`, assumed), and the 894th's
printed history for 1945 (`hist894`, the battalion's position, the detachment assumed with it). Three sea crossings
in `army/ships.csv` (USS Ancon in UGF-4, January 1943, confirmed; "Ship # 416" to Naples, October 1943, a candidate;
USS Florence Nightingale to France, September 1944, confirmed), the Atlantic and the train rides as assumed routes
(`routes.csv`). Its organizations: part of the 67th CA (AA), redesignated the 894th AAA AW Bn on 20 March 1944. Around
it: the 67th's batteries' engagements at Venafro and Acquafondata (`venafro-1944-02`, batteries E, H and A, not the
detachment), the operations from Torch to Central Europe (`operations/`), and the leads in `army/README.md`. Tempo:
monthly.

**The account.** The journey in stages, as `chapter.js` computes them from the stations' countries, with one sentence
per stage in the records' words and a coverage bar under each saying which source gives the stage:

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│ Mediterranean and Europe · 67th Coast Artillery (AA) → 894th AAA AW Bn                           │
│ Medical Detachment, 67th CA (AA): Paterson to Hüttenfeld, 1942–1945                              │
│ Where the detachment was, day by day, from its own morning reports to December 1944 and the      │
│ battalion's history for 1945. Sixty-two changes of station, three sea crossings, five countries  │
│ after the Atlantic.                                                                              │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│  [strip map: five small panels at one scale, the track solid where its own report places it,     │
│   dashed where assumed, the crossings dotted; one red-free palette: one subject, one colour]     │
│   1 Home and the Atlantic  2 Algeria and Tunisia  3 Italy        4 France        5 Germany       │
│   Sep 42 – Jan 43          Jan 43 – Oct 43        Oct 43 – Sep 44  Sep 44 – Apr 45  Apr – May 45 │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 2 Algeria and Tunisia, Jan – Oct 1943                                                            │
│   "Disembarked at Mers-el-Kebir at 10.00 A.M. Campsite La Senia Airport." (26 Jan 1943)          │
│   17 stations · the war around it: Torch (ended), Tunisia (12 Nov 42 – 13 May 43): context, not  │
│   participation · reading the records here: the British North West Africa grid                   │
│   coverage  ▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇  own morning reports  ░░░░  regimental HQ's (assumed)│
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│ The records ›  62 stations · 3 crossings · two record series   The working ›  7 assumed legs     │
│ Beside it ›  Batteries E and H at Venafro, Feb 1944 (the same battalion, not the detachment)     │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

The engagements along the way are stops on the strip, and the account is honest about them: Venafro is the batteries'
engagement, the detachment's own record for those weeks says only where it was, so the strip marks it *beside it*, not
*in it*. The operations are a band under the strip (context), each a door to its operation page.

**The records.** Today's `army.html` for this unit: the map with the date strip and playback, the list of stations as
typed with their pages, the crossings opened from the station they start at, and the panels the record has (the
seafloor under the LST line; the ship's silhouette). The chronology at month grain adds what the map can't show: the
stations as bars, the crossings as arrows, the redesignation as a mark on the organization row, and a column for each
source so the hand-over from the morning reports to the history on 1 January 1945 is a visible seam.

**The working.** The placement table (how many stations are placed at a town, an offset, a grid reference, a
headquarters assumed with the detachment nearby, and which); the leads about the unit, each with what was searched
and what is still to search (`leads.yml`, §8; today `army/README.md`'s table holds the 9th Armored's, none yet for this
detachment); the speed check of the legs (a motor convoy's 8 miles in an afternoon is fine; a station a day's march
off the route is a question); the relations as a dated list with their pages; the coverage month by
month, which is the honest answer to "how do we know where it was in March 1943?" (*the regimental headquarters
battery's report; the detachment's own are missing; assumed with regimental headquarters*). Press belongs here too when
it comes: L'Écho d'Alger on an Oran raid the battery fired on is a `press` column beside the morning report's "Fired on
hostile targets", and the page says which is which.

**The breadcrumb.** *Subjects / Medical Detachment, 67th CA (AA) / Italy, Oct 1943 – Sep 1944 / 17 Oct 1943*, and from
any station, the operation it sat inside and the engagement nearest in time.

## 8. What changes in the records

Additive, and small; nothing is re-transcribed.

| Change | Where | Why |
|---|---|---|
| `kind` and `of` on every source entry | `records/SOURCES.yml` (99 entries); `check_sources.py` fails on a missing kind | the voices (§2.4): the build tags every row through its citation |
| `original`, `lang`, `translation` on every entry whose record isn't in English; `words` keeps the translation for a German entry until it is moved | `events.yml` | one rule for every language; the German entries at Venafro and Neuburg move first |
| `side` retired; an actor's nationality `of` on an entry whose actor isn't a subject | `events.yml`, `build_engagement.py`'s `SIDES` | the press is a source kind; a place is a position; a bloc is vaguer than the record |
| `plain` on every subject: what it was, in a line, ours | `army/units.csv`, `seabees/units.csv`, `ship.yml`, `convoy.md` | the opaque designations get a name a reader can follow (§2.1) |
| a relations file beside each dataset read into one registry: `convoys/<id>` ships, `seabees/parts.csv`, ComSubPac's task organization, a pack's boats | the build (`subjects.json`, generated) | organizations (§2.1); the subject page's card |
| `subjects.json`: every subject across `boats/`, `ships/`, `army/units.csv`, `seabees/units.csv`, `convoys/`, `commands/`, with kind, periods, status and relations | generated by the build; `ships.json` is its first half | one registry for the subject page, the breadcrumb and the lint's deep links |
| `leads.yml` beside `claims.yml` (and in `army/`, `seabees/`): `statement`, `said_by`, `searched`, `still`, `ref` | hand-edited; the README tables move into it | the working shows them; a lead resolved becomes a row |
| `operation:` on an engagement, optional | `engagement.md` front matter | only when the geometric placement (`chapter.js`) is wrong |
| `step` links in prose: `[[step:s3|at 1250 she was hit]]` | `engagement.md`, `links.js` | the story sets the clock; the hand-built pages fold into the generic one |
| the notations as glossary patterns | `reference/glossary.yml` | the explainers reached from the notation (§5.4) |

Derived, never stored: a frame's tempo; a subject's stages; which view leads; the minutes and miles between two
entries; a source's columns; a unit's coverage by month.

## 9. What stays, what goes, and in what order

**Stays, as it is**: the records' folders and every transcription rule; `engage.js` and its tests (the computation, now
also the cross-reference arithmetic); the observer view and the TDC; *closing in*; the dive profile; the convoys'
roster and the lanes' timetable; the encodings and the three checked colours; the scan viewer; the glossary; the
explainers; the Europe chapter's stages.

**Goes, once replaced** (the kit's rule: a file converted is converted for good): `haynsworth.html` and `algiers.html`
as pages (their steps and figures become their engagements' story and working); the per-page nav fragment; `viz.css`'s
token set; `OWN_PAGE` and the Europe-only test in `chapter.js`; `side` and its `SIDES` vocabulary.

Each phase deletes something and ends with the checks green (`lint.py`, `smoke.py`, `check_builds.sh`,
`test_tools.py`, `engage.test.js`), the lint's REF002 rewritten for the new addresses, and every page looked at in
light and dark on a desktop and a phone.

| Phase | Build | Delete | Proves |
|---|---|---|---|
| 1. One skin | one token set and one nav fragment on every page: the vocabulary defined once in `viz.css`'s header, each page family keeping its own values under the one set of names | the second set of names and every fallback chain (`entry.css`, `glossary.js`); the seventeen copies of the nav | the two page families were one |
| 2. The depths | the account on `engagement.html` (static map, outcome, doors) with the present page as its records depth, `?view=`; the working gathers the claims, the computed layers, the figures | nothing yet | progressive disclosure on the existing data |
| 3. Chronology | the day-column chronology as a shared view; tempo derived; the dated frames (Venafro, Algiers, Remagen) lead with it | `algiers.html`'s own timeline | the clock is one view's device |
| 4. Voices | `kind`/`of` in SOURCES.yml; entries tagged through citations; `original`/`lang`/`translation` for German; the Sources view for TAMA-17 and Algiers | `side` and `SIDES` | sources as columns; press beside the records; the other side named as the records name it |
| 5. Stories folded in | `[[step:]]`; Haynsworth's and Algiers' figures as working panels of their engagements | `haynsworth.html`, `algiers.html`, `OWN_PAGE` | one engagement page for every tempo and every kind of figure |
| 6. Subjects | `subjects.json`; `subject.html` with the four apps as panels; relations from every dataset; leads | `patrols.html`, `army.html`, `seabees.html`, `convoys.html` as pages (their scripts live on as panels); the README lead tables | one journey page for a boat, a ship, a unit, a battalion, a convoy |
| 7. Theatres | `theatre.html` from `chapter.js` for all four; the front page as an index; the breadcrumb everywhere; notations in the glossary | the front page's inline replays and fleet list | the ladder theatre → operation → engagement → entry, and the subject thread across it |

Phases 1–3 need no change to the records. Phase 4 touches `SOURCES.yml` and two engagements' `events.yml`. Phases 6 and
7 are the large ones and come last, when the earlier phases have shown the model holds on the pages that exist.

**Done** (3 November 2026): phase 1 (`site/nav.js`; one token vocabulary, `site/viz.css`, every page's colours unchanged
to the pixel) and phase 3 (`Engage.tempo`, `chronologyRows`, `chronologyColumns` in `engage.js`, tested; `EV.chronology`
in `engage-views.js` with `site/chron.css`; Venafro, Filignano, Remagen and Algiers lead with it on `engagement.html`,
and `algiers.html`'s own timeline is gone). Two things the data taught: a frame counts as clocked when *more than half*
its entries carry a time with a zone, not any of them, because Remagen's corps report times ten entries of twenty-five
and is a dated frame all the same; and the columns group by the record named in each entry's `source` (the text before
its first comma or colon) until phase 4 gives every source a `kind`, which should replace that heuristic. Phase 2 is next.

## 10. Open questions

- **Colour for more than three followed subjects.** The 62nd CA (AA) has fourteen units with stations around Oran and
  Algiers in 1942–43. Small multiples (one map per battery at one scale) or a picker, as the rule says; the account's
  strip map is already small multiples by stage. Which the subject page uses for a battalion with many parts is to be
  tried on the 62nd and the 20th NCB.
- **The convoy as a subject with a record of its own against the boats' sightings of it.** The convoy's observed path
  is computed from the boats' ship contacts and the Japanese positions. On the convoy's own page it is the lead layer
  and it is ours; the account must say so in its first line.
- **Operations without a page of their own yet.** The Pacific has none in `operations/`; the lanes' month-by-month view
  is the nearest thing to the war at sea's own frame, and may be the Pacific theatre page's spine until the operations
  are written.
- **The family seam.** A family's site reaches `army.html?who=` today; the subject page must take the same address so
  the seam holds (`subject.html?s=67ca-med&who=…&t=…`), and the kit's lint must keep refusing a person's name in
  `records/` (PRV001).
- **Addresses.** `engagement.html?e=`, `patrols.html?ship=`, `army.html?unit=`, `seabees.html?unit=`, `convoys.html?c=`
  are linked from outside the kit. Each old address redirects to the new one for good (a one-line page, like the
  Pages workflow's root), and the lint checks both forms until the old pages are gone.
