# wwii-book

Print books from the kit's records. A book is a [Typst](https://typst.app) file; its pages ask for what they need by
citation or by records path, and the build fetches, crops and stages it.

```typst
#import "@local/wwii-book:0.1.0": *
#let wwii = init(assets: json("build/assets.json"), load: p => read(p, encoding: none))
#show: book

#(wwii.facsimile)("rg64-469722323/p0712", crop: (0, 0, 1, 0.24),
  caption: [Morning report, HQ Battery, 128th AAA Gun Battalion, 14 April 1944])
#(wwii.records)("boats/ss-385-bang/patrol-1/attacks.csv", torpedo-ledger)
```

```bash
cd book
uv run wwii-book build examples/bang-patrol-1/book.typ     # -> examples/bang-patrol-1/book.pdf
uv run wwii-book fetch rg38-74802746/p16                   # one page into the scan cache
uv run pytest
```

The records and the scan cache are found as the kit's tools find them: `../records` and `../sources`, or wherever
`WWII_RECORDS` and `WWII_CACHE` point.

## How a build works

1. Typst compiles the book. Each request function (`facsimile`, `records`, `qr-tag`) writes a `<wwii-request>`
   metadata entry and draws a placeholder, so a book always compiles.
2. The build asks Typst for the requests (`typst query`), prepares each one into the book's `build/` folder (an
   archive page fetched through the kit's scan cache, turned, cropped and made greyscale; a records file as JSON; a
   QR code as SVG) and lists it in `build/assets.json`, under the key Typst gave it.
3. Typst compiles again with everything in place, and the build reports its warnings (`<wwii-warning>`: an image
   placed below 300 dpi).

A facsimile is placed at its own size at 300 dpi, or the column's width if that is narrower: a morning-report roll's
scans are about 1,800 pixels wide, so about six inches is the most they can print at.

## What's here

| Path | What it is |
| --- | --- |
| `src/wwiibook/cite.py` | A citation (`rg64-469722323/p0712`): archive, item, page, link, credit line |
| `src/wwiibook/nara.py` | A National Archives page image by citation, through the shared cache (both the tools' layouts) |
| `src/wwiibook/images.py` | Turn, crop, greyscale (Pillow) |
| `src/wwiibook/qr.py` | QR codes as SVG |
| `src/wwiibook/build.py` | The two-pass build |
| `src/wwiibook/geo.py` | Coastlines (world-atlas, cached in `<cache>/geo/`, TopoJSON decoded here) and a Mercator frame |
| `src/wwiibook/atlas/` | An atlas extent's pair of views: the period network reconstructed from IGN's 1:50,000 (`reconstruct.py`), the panorama, the oblique view, the QGIS export (`atlas/README.md`) |
| `src/wwiibook/chain.py` | A unit's chain of command over months, on one day, or as a row of patches, from `records/army/relations.csv` |
| `insignia/insignia.yml` | Shoulder sleeve insignia by unit id: the Commons file, its licence and credit, what is checked of its period |
| `src/wwiibook/figures.py` | An engagement's map and timeline as SVG, from `records/engagements/<id>/engagement.json` |
| `src/wwiibook/typst/local/wwii-book/0.1.0/` | The Typst package: page, components, request functions |
| `examples/` | Books built from the public records alone, naming no one's relative |

## An engagement's figures

`engagement-figure(id, figure: "map" | "timeline", follow: "bang", key: true)` draws from the same merged,
GMT-clocked `engagement.json` the site's engagement page reads, so the book and the page can't disagree. The map and the
timeline number the same marks the same way (attacks, the other side's records of attacks and losses, intelligence
notes, in time order); `key: true` sets them as a table: number, GMT, the time as the record types it, what, the
kit's note on the record (what the position is, a doubt, an assumed zone), and the citation. Unnumbered marks
(contacts, log entries, depth charges) are cited in groups, and the clocks the records kept are named. The timeline
shades night (sunrise and sunset at the engagement's centre) and joins each attack to the other side's record of it
with the minutes between the two.

## A unit's chain of command

`unit-chain(unit, view: "timeline" | "ladder" | "strip", start:, end:, on:, title:, marks:)` draws the formations above
a unit from the kit's `records/army/relations.csv`, where every link (`part_of`, `attached_to`, `under_command`) is a
dated, cited row. The chain is walked upward, each parent only for the days the child was linked to it, so a battery
attached to a division in five intervals shows the division's corps and army in those five intervals and nothing
between them.

- **timeline**: a row a level (theater, army group, army, corps, division, regiment, battalion), months across. Each bar
  carries the formation's patch and its name as the record prints it (shortened only where a bar is narrow: "V Corps,
  First US Army", then "V Corps"). Assigned or under command is filled; attached is hatched, in a lane below; a link
  the record infers is dashed; an end the record leaves open fades. A blank end stops the day before the unit's next
  link of the same kind at the same level begins, and is still drawn open. `marks` adds dated lines (an engagement).
  Leniently (`bridge`, 45 days by default), a formation that holds a level on both sides of a short gap is carried
  across it, pale and dashed, as assumed: a battery between two attachments to a division was still in the same
  army. An attachment's gap is not bridged (the attachments table lists them interval by interval: a gap is a
  detachment), nor a gap where the record says the unit was relieved ("(-)") and another formation follows.
- **ladder**: the chain on one day, top to bottom, each step with its patch, the link, since when, and the citation.
- **strip**: the chain on one day as a row of patches, for a chapter's opening.

Ships and battalions read `records/navy/relations.csv` the same way, with the Navy's levels: fleet, task force,
task group (a submarine's pack) and task unit above, squadron and division below (a submarine's are the ones each
patrol report went through, `reported_through`), and a Seabee battalion's brigade and regiment. Names shorten to the
Navy's abbreviations (TF, TG, TU, SubDiv, SubRon, DesRon, NCR); a bar too narrow for any form is named beside it.

A formation with no patch of its own (a regiment, a battalion, a company or battery) is drawn with its FM 21-30
symbol, read from its name: arm, echelon, letter, number. The patches are listed in `insignia/insignia.yml` with
their Commons source, licence and credit, and what has been checked of the years each was worn (the 45th Infantry
Division's Thunderbird, from 1939, not its earlier patch); the figure's notes list the patches it drew, so a book can
credit the CC BY-SA ones. `examples/unit-chain/` shows all three.

Not yet: JACAR and Library of Congress pages, Army engagements (fronts and stations rather than tracks), the
templates beyond the ledger and the engagement figures, fonts.
