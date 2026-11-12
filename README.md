# WWII research kit

Tools, guides and pages for working out where a ship or unit of the Second World War was, day by day, from the
records it kept at the time, and for setting the other side's record of the same hours beside it.

**Site:** <https://erichutchins.github.io/wwii-research-kit/>. Start with
[About, method and limits](https://erichutchins.github.io/wwii-research-kit/about.html).

## What it covers

The records read so far are US submarine war patrol reports, ships' war diaries and action reports, Army morning
reports and unit histories, Navy muster rolls and Twelfth Army Group's daily situation maps; and, for the other side,
the Imperial Japanese Navy's war diaries and escort reports (through JACAR) and German corps, army and naval staff
records (National Archives microfilm). The transcriptions are a separate repository,
[wwii-unit-records](https://github.com/erichutchins/wwii-unit-records), held here as `records/`:

| | |
|---|---|
| 25 submarines | USS BANG (SS-385) for all six war patrols; the others for one or two patrols each |
| 23 surface ships | four at length from their war diaries, the rest for one day |
| About thirty Army units | mostly anti-aircraft artillery, station by station |
| 2 naval construction battalions | from their muster rolls |
| 11 Japanese convoys, 24 engagements | each engagement page says which sides' records are entered |
| The front in Europe | the daily situation maps from 6 June 1944 |

The selection is not a sample of the war. It began with one submarine and grew along one family's research: the
units its members served in, those beside them and those that met them. The records name units and ships, never
those people. `records/inventory.yml` lists every report looked for, found or not.

## The rules

1. **Cite every source.** Every value carries the page it was read from, in a short form listed in
   `records/SOURCES.yml`: `rg38-74802746/p05` is National Archives Record Group 38, catalog item 74802746, page 5.
   `tools/check_sources.py` fails on a citation that doesn't resolve, a row without one, and a record group that
   disagrees with the catalog's.
2. **Record what was typed.** Values are read on the scan image, never taken from text recognition, and recorded
   exactly as typed. A correction goes beside the typed value with its reason, never over it.
3. **Label what isn't reported.** Every value is reported, derived, inferred or assumed, in the data and on the page.
4. **Name the limits.** One researcher working with an AI agent read these pages; there has been no independent
   second reading. Absence from the records searched is not evidence of absence.

## What's here

| Folder | What |
|---|---|
| `site/` | The pages: static HTML and D3, no build step |
| `guides/` | How each archive works and how its records are read; start at [guides/README.md](guides/README.md) |
| `tools/` | Python: find and download records, crop scans for reading, check transcriptions, build the pages' data ([tools/README.md](tools/README.md)) |
| `reference/` | The Japanese kana grid keys, the German grids' keys, the convoy lanes and the glossary |
| `records/` | The data: the wwii-unit-records repository, a submodule, with its own [README](records/README.md) |
| `CLAUDE.md`, `.claude/` | The rules and step-by-step workflows an AI agent follows here |

## Run it

```bash
git clone --recurse-submodules https://github.com/erichutchins/wwii-research-kit.git
cd wwii-research-kit
python3 tools/serve.py        # then open http://localhost:8385/site/
```

Viewing needs nothing else. The tools need Python 3.9 or later and run with [uv](https://docs.astral.sh/uv/), which
fetches what each one imports. Scans are never committed: they download to `sources/` (git-ignored), and the pages
fall back to the archive's own copy.

```bash
python3 tools/nara.py find "Wahoo"                  # a submarine's war patrol report folders
python3 tools/nara.py fetch 74802746                # its scans -> sources/nara/rg38-74802746/
uv run tools/crop_pages.py halves 74802746 03 04    # readable halves
uv run tools/check_track.py bang/1                  # speed-check a transcribed patrol
uv run tools/check_sources.py                       # every citation resolves
python3 tools/morning_reports.py unit 578447414 'Btry.{0,4}D.{0,6}62'   # a unit's morning reports
python3 tools/jacar.py search "日達丸"               # Japanese records
python3 tools/jgrid.py decode メキ三ツ               # a Japanese kana position code
python3 tools/grid_ref.py lambert2 J-762365         # an Army grid reference -> latitude and longitude
```

To work on your own ship or unit, point the tools at your own records folder with `WWII_RECORDS=/path/to/records`.
[Researching a relative](https://erichutchins.github.io/wwii-research-kit/relatives.html) says where to start.

## Corrections and contributions

Corrections are welcome as issues on the [records](https://github.com/erichutchins/wwii-unit-records/issues): which
mark, and what the page says instead. A transcription of another ship or unit is welcome as a pull request there.
The kit and its data are two repositories, so a change to the records is committed and pushed in `records/` first
and the kit then records the new version; `CLAUDE.md` has the checks that run before a commit and a push.

## Licence and citation

Code: MIT. The records: CC BY 4.0 (`records/LICENSE`). The original records keep their own terms, listed source by
source in `records/SOURCES.yml`. To cite: the original record for any value, and for the transcription, Eric
Hutchins, *WWII unit records and research kit*, the site's address and the version date at the foot of its pages.
