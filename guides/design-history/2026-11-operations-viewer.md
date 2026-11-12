# The operations viewer: how the design was reached (November 2026)

A record of the redesign that produced the pages described in `guides/OPERATIONS-VIEWER.md`. That guide is the
specification; this file is history, kept because the code's comments cite its phases ("phase 6") and because the
reasons for a rule are easier to keep when what it replaced is written down. Counts here are as they stood on the
day named and are not kept up to date.

## Where the earlier model strained (3 November 2026)

The site had one page type that crossed sources, the engagement: two sides meeting at a place and a time, each in its
own records, on one map and one clock. It was built for a submarine pack against a convoy, and it was right for that.
The strain showed where the records didn't fit the sentence.

| Symptom | Where it showed | What it meant |
|---|---|---|
| A clock with nothing to play | Venafro, February 1944: every entry a day. Remagen: division positions by day | The lead view assumed a tempo of minutes; many frames have a tempo of days or months |
| Hand-built pages beside the generic one | `haynsworth.html`, `algiers.html`, each with steps, a day-column timeline, scale drawings, an evidence board | The generic page had no place for a story told in steps, a chronology in day columns or a frame's own figure |
| Four apps for one idea | `patrols.html`, `army.html`, `seabees.html`, `convoys.html` each drew one subject's own record; two families of CSS names | The subject's page is one page type with panels by record kind |
| The nav listed a ship | theatres, places, record types, one ship and one view in one bar | There was no navigation model, so the bar was a list of what existed |
| `side` did three jobs | `us, jp, allied, axis, de, press, geo`: a nationality, a coalition, a kind of source, a place | The press is not a side; a coalition word is vaguer than the records |
| The units' names were opaque | "Btry D, 106th AAA AW Bn (SP)" | A reader needs a line saying what each unit was |
| The other side's words were typed two ways | Japanese entries had `original` and `translation`; German ones quoted the original inside `words` | One rule for every language |
| The reconstruction sat inside the record | the convoy's observed path, *closing in*, the estimated kamikaze path | The page's structure, not only the map's encodings, should say which marks are the record's |
| Organization lived in three shapes | `army/relations.csv`, `seabees/parts.csv`, a convoy's `ships:` | One idea: dated membership of one subject in another |
| Leads lived in a README table | `army/README.md` | The same shape as a claims file's open questions, and the reader never saw them |

None of these was a defect in the records. They were the signs of a model built for one kind of record carrying five.

## The phases

Each phase deleted something and ended with the checks passing (`lint.py`, `smoke.py`, `check_builds.sh`,
`test_tools.py`, `engage.test.js`) and every page looked at in light and dark, on a desktop and a phone.

| Phase | Built | Deleted | Done |
|---|---|---|---|
| 1. One skin | one set of CSS variable names (`viz.css`) and one nav (`nav.js`) on every page | the second set of names and every fallback chain; seventeen copies of the nav | 3 Nov |
| 2. The depths | the account on `engagement.html` with the earlier page as its records depth; `?view=` | nothing | 3 Nov |
| 3. Chronology | the day-column chronology as a shared view; tempo derived (`Engage.tempo`) | `algiers.html`'s own timeline | 3 Nov |
| 4. Voices | `kind` and `of` in `SOURCES.yml`; entries tagged through their citations; `original`/`lang`/`translation` for every language; the Sources view | `side` and its vocabulary | 3 Nov |
| 5. Stories folded in | `[[step:]]`; Haynsworth's and Algiers' figures as panels (`site/panels.js`) | `haynsworth.html` and `algiers.html` as pages | 4 Nov |
| 6. Subjects | `subjects.json`; `subject.html` with the four apps as panels (`site/panels/`); relations from every dataset; `leads.yml` | `patrols.html`, `army.html`, `seabees.html`, `convoys.html` as pages; the README lead tables | 4 Nov |
| 7. Theatres | `theatre.html` for all four; the front page as an index; the breadcrumb everywhere; the notations in the glossary | the front page's inline replays and fleet list | 4 Nov |

On 6 November the three depths of phase 2 (the account, the records, the working) became two. The account's first
screen held nothing the records' sheet didn't and only sent the reader on, and *the working* named a method where a
reader wanted to know what was behind the door. The two are now one page in reading order, and the second depth is
named for what it holds: *Questions and sources* on an engagement, *Placement and leads* on a subject. The old
addresses (`view=account|records|working`) still arrive. The same day a dated frame with several days' situation
maps gained the clocked frames' bar, stepping a map at a time.

The old page addresses (`patrols.html?ship=`, `army.html?unit=`, `seabees.html?unit=`, `convoys.html?c=`,
`haynsworth.html`, `algiers.html`) are redirects that carry their parameters across, kept for links from outside.

## What the records taught along the way

Each of these became a rule in the specification.

- **Tempo.** A frame is clocked when more than half its entries carry a zoned time, not when any does: Remagen's
  corps report times ten entries of twenty-five and is a dated frame all the same.
- **Outcomes.** Every European engagement lacked an *Outcome* section when the first screen was built, so the page
  says "no outcome yet" and never invents one. The five were then written, each sentence a record's with its citation.
- **Sources with one witness.** A question every answer of which comes from one source (sixteen of Remagen's) made
  the Sources view repeat the claims board, so the view shows only questions with two or more sources.
- **A convoy is not a followed subject.** It is the other side's record, read against the boats' sightings.
- **Nationality cannot always say who faced whom.** Once three nationalities meet (Algiers), the engagement names
  `against:`.
- **Radio intelligence is a source, not a side.** The FRUPAC notes were first planned as a third lane; they are
  entries of kind *intelligence*, hatched on the map, in their own column of the Sources view. A note tied to an
  attack with no Japanese pairing is an entry and a mark but no moment.
- **Organizations had gaps.** The 67th CA (AA)'s units had no rows in `relations.csv`, so the card said so; the
  ORGANIZATION line on the reports is the source to read. A unit's "beside it" is by geometry until a relation names
  the unit.
- **Stages.** A subject's theatre is read from its positions; a battalion's stages are calendar years, since no
  countries divide the Pacific. The Pacific and the Atlantic had no theatre file, so each got one whose span is the
  one the records cover.
- **Notations.** The records type a zone time both `1500 A` and `1500A`; a pronoun after a time ("At 1604 I
  sighted") is real, so a lowercase word after the letter leaves it unmarked; the grid pattern had to learn what is
  not a grid reference (`KG 54`, `TF 58`, `JV 44`, `Mk 14`); a convoy's kana name is not a position code; the records
  never write the angle on the bow as a notation, only in words.

## What didn't fit, and is still open

Carried into the specification's §10: the story pages' own map layers (Haynsworth's picket ring and formation
schematic, Algiers' reach ring), the date beside a zone-lettered time on the engagement page, and the operations of
the war at sea.

## The mockups

`guides/mockups/` holds four screens drawn during the design from the records' own values: the TAMA-17 account
(`tama-17-account.html`) and its Sources view (`tama-17-working.html`, named for the third depth that no longer
exists), the Medical Detachment's account (`67ca-med-account.html`) and Venafro's chronology
(`venafro-chronology.html`). Nothing in them is live, and their captions cite the design's section numbers as they
stood on 3 November.
