# The guides

How the records were found, read, checked and put on the pages, in the order to read them.
Each guide is the method for one kind of record or one notation, with the worked cases it was
set by. The rules an agent follows are in [`CLAUDE.md`](../CLAUDE.md); the tools are listed in
[`tools/README.md`](../tools/README.md); the data's fields are in the records' own
[README](../records/README.md).

## 1. The common method

- [METHODS.md](METHODS.md): from scans to a checked, cited record. Collecting, transcribing as
  typed, checking, enriching with outside data, analysis. The worked case is a submarine's war
  patrol reports; a ship's war diary is read the same way. Read this first.

## 2. By record

- [MORNING-REPORTS.md](MORNING-REPORTS.md): an Army company's, battery's or detachment's stations
  day by day, from its morning reports (National Archives, Record Group 64).
- [MUSTER-ROLLS.md](MUSTER-ROLLS.md): a Navy shore unit, such as a Seabee battalion, from its
  muster rolls (Record Group 24), which account for men and not for places.
- [JAPANESE-RECORDS.md](JAPANESE-RECORDS.md): the Imperial Navy's record of an attack (JACAR), and
  US radio intelligence's war maps of the same day.
- [SITUATION-MAPS.md](SITUATION-MAPS.md): HQ Twelfth Army Group's daily situation maps (Library of
  Congress), traced into a front and the divisions on it.

## 3. Position systems

The records give positions in their own codes. Each guide says how the code works, what is keyed
and how far to trust it.

- [JAPANESE-GRID.md](JAPANESE-GRID.md): the Imperial Navy's four-character kana position codes.
- [NAVAL-GRID.md](NAVAL-GRID.md): the Kriegsmarine's naval grid squares in the Mediterranean.
- [BEZUGSPUNKTE.md](BEZUGSPUNKTE.md): the German Army's reference points in Italy, 1944.

The US Army's map grids and the Navy's zone letters have explainer pages and no guide:
`site/grids.html` and `site/zones.html`.

## 4. The pages

- [ENGAGEMENTS.md](ENGAGEMENTS.md): putting two sides' records of one event on one map and one
  clock: the files, the rules, the encodings and the computation.
- [OPERATIONS-VIEWER.md](OPERATIONS-VIEWER.md): how the site is organised: subjects, theatres,
  engagements, the views and the navigation. Read it before adding a page or a view.

## 5. Finding aids

- [GOOGLEBOOKS.md](GOOGLEBOOKS.md): digitized manuals, unit histories and after-action reports on
  Google Books.

The skills in `.claude/skills/` are these methods as checklists for an agent:
`transcribe-patrol-report`, `transcribe-morning-reports`, `find-the-other-side`,
`trace-situation-map`, `find-film`, `add-silhouette`.
