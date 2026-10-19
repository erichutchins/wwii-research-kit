---
name: find-the-other-side
description: >
  Find the Japanese record of a US submarine attack (or a kamikaze attack, or an air contact):
  identify the convoy and ships from secondary sources, search JACAR for the Imperial Navy's war
  diaries, escort reports and ship movement logs, transcribe the entries as written with a
  translation, decode kana position codes, pair them with the US record, and check the FRUPAC
  radio-intelligence maps. Use when asked what the Japanese side recorded, whether a ship was
  sunk, or to build a battle page.
---

# The other side

Read `guides/METHODS.md` ("The Japanese side") and, for position codes, `guides/JAPANESE-GRID.md`.

## Steps

1. **Identify the convoy.** combinedfleet.com's Tabular Records of Movement name the convoy,
   ships and escorts for most sinkings. They are secondary: cite them as `combinedfleet:<page>`
   and keep looking for the primary record.
2. **Search JACAR.** `python3 tools/jacar.py search "<ship or convoy in Japanese>" [YYYY-MM YYYY-MM]`
   finds reference codes (the search reaches the OCR); `meta <code>` shows the title and page
   count; `fetch <code>` downloads the pages to `sources/jacar/<code>/`. Look for: the escort
   division's war diary (戦時日誌), the escort ship's battle report (戦闘詳報), the guard district's
   radio log, and the designated-ship movement tables (指定船舶行動表) for merchant ships.
3. **Transcribe as written.** `japanese.csv` in the patrol's folder: the original text, an English
   translation beside it, date, time and zone (Tokyo time, zone I, unless the record says
   otherwise), position as given, `source` (`jacar:<code>`) and `page`.
4. **Positions in code.** Aircraft and some escort reports give 4-character kana codes (メキ三ツ):
   `python3 tools/jgrid.py decode <code> --key <key>`. If the key isn't known yet, the code is an
   anchor candidate: see `reference/jgrid/` and the guide.
5. **Pair them.** `crossrefs.csv` (attack, Japanese row, relation, note), then
   `uv run tools/check_crossrefs.py`: minutes and miles apart for each pair.
6. **FRUPAC.** `python3 tools/frupac.py find "\b<Name>\b"` and `date <YYYY-MM-DD> 1` list the
   radio-intelligence map overlays; read them in the zoom viewer (never copy: CC BY-NC-ND) into
   `frupac.csv`.
7. `uv run tools/check_sources.py`; then a battle page: `uv run tools/build_battle.py new <id> <patrol>...`
   and `guides/BATTLES.md`.
