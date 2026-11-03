# WWII research kit

Tools, guides and reference pages for rebuilding where a WWII ship or unit was, day by day,
from its own records — and for doing it with an AI agent such as Claude Code. Built on US
submarine war patrol reports, a destroyer's war diary, Army morning reports and battalion
histories, and the Imperial Japanese Navy's records of the same days.

**Site:** <https://erichutchins.github.io/wwii-research-kit/>, the pages in `site/`: ship tracks, a submarine's dive profile,
convoy battles on one clock with the Japanese side, and explainers for the reports' time zones,
the Japanese Navy's kana position grid and the Army's map grids. Every mark links to the scanned
page it came from.

## The rule: cite every source

Every value carries the page it was read from, in a short form listed in
`records/SOURCES.yml` (`rg367-74802746/p05`: National Archives item 74802746, page 5).
`tools/check_sources.py` fails on any citation that doesn't resolve and any row without one.
Values are recorded exactly as typed; corrections go beside them with a reason, never over them.

## What's here

| Folder | What |
|---|---|
| `tools/` | Python: find and download records (National Archives catalog, JACAR, Google Books, FRUPAC maps), crop scans for reading, check transcriptions, build the pages' data |
| `guides/` | How each archive works and how the records were read: [METHODS](guides/METHODS.md), [morning reports](guides/MORNING-REPORTS.md), [Navy muster rolls](guides/MUSTER-ROLLS.md), [engagements](guides/ENGAGEMENTS.md), [the Japanese grid](guides/JAPANESE-GRID.md), [the Kriegsmarine's naval squares](guides/NAVAL-GRID.md), [the German Army's reference points](guides/BEZUGSPUNKTE.md), [Google Books](guides/GOOGLEBOOKS.md), [expanding to the fleet](guides/FLEET.md); where the pages are going: [the operations viewer](guides/OPERATIONS-VIEWER.md) |
| `reference/` | Reference tables: the Japanese kana grid keys and the positions they were worked out from |
| `site/` | The pages (static HTML and D3, no build step) |
| `records/` | The data: the [wwii-unit-records](https://github.com/erichutchins/wwii-unit-records) repository, a submodule |
| `CLAUDE.md`, `.claude/skills/` | The rules and workflows an agent follows here |

## Run it

```bash
git clone --recurse-submodules https://github.com/erichutchins/wwii-research-kit.git
cd wwii-research-kit
python3 tools/serve.py        # then open http://localhost:8385/site/
```

Viewing needs nothing else. The tools need Python 3.9+; the ones that read YAML run with
[uv](https://docs.astral.sh/uv/) (`uv run tools/check_track.py ...`), which fetches PyYAML.
Scans are never committed: they download to `sources/` (git-ignored), and the pages fall back
to the archive's own copy.

```bash
python3 tools/nara.py find "Wahoo"                  # a submarine's war patrol report folders
python3 tools/nara.py fetch 74802746                # its scans -> sources/nara/rg367-74802746/
uv run tools/crop_pages.py halves 74802746 03 04   # readable halves
uv run tools/check_track.py bang/1                  # speed-check a transcribed patrol
uv run tools/check_sources.py                       # every citation resolves
python3 tools/morning_reports.py unit 578447414 'Btry.{0,4}D.{0,6}62'   # a unit's morning reports
python3 tools/jacar.py search "日達丸"               # Japanese records
python3 tools/jgrid.py decode メキ三ツ               # a Japanese kana position code
python3 tools/grid_ref.py lambert2 J-762365         # an Army grid reference -> lat/lon
```

To work on your own boat or unit, point the tools at your own records folder with
`WWII_RECORDS=/path/to/records`.

### Two repositories

The kit and its data are two repositories. `records/` is a submodule, the
[wwii-unit-records](https://github.com/erichutchins/wwii-unit-records) repository, with its own hooks
(`records/.pre-commit-config.yaml`), which call the kit's tools from `../tools/`, so they run in a checkout of the kit.
A change that touches the records is committed and pushed in `records/` first; the kit then commits the new submodule
pointer. The CI (`.github/workflows/pages.yml`) checks out recursively, runs the kit's checks and publishes `site/`,
`reference/` and `records/` together, so a pointer to a records commit that was never pushed fails it. The generated
files live in `records/`, so `tools/check_builds.sh` compares them there (`git -C records diff`).

There is a third layer above these two: a private family repository holds the kit as `kit/` (`tools/serve.py` runs
from either). It writes the private list, `sources/private-terms.txt`, that the lint's rule PRV001 reads (without it
the rule checks nothing, and says so), and it runs the kit's `tools/smoke.py` over its own pages through `views()` and
`run()`. Nothing in the kit or the records depends on it.

## Licence

Code: MIT. The records have their own licence (CC BY 4.0, `records/LICENSE`).
