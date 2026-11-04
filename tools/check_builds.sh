#!/bin/sh
# Every build checks out (0 problems) and every generated file it writes is up to date: what the CI runs
# (.github/workflows/pages.yml), and the pre-push hook (.pre-commit-config.yaml). Run from the kit.
#
# The generated files are in records/, a submodule: `git diff` from the kit sees no change inside it, so the
# comparison is made in records/ itself, build by build, so a stale file is named with the tool that rebuilds it.
# Each build runs first, then its files are diffed; a file a build writes that git doesn't track yet fails too.
#
# Guarded here, every generated file that a tool can reproduce from the committed records alone:
#   citations.json (check_sources.py --fetch: reuses the entries it has, so the catalog is only asked about an
#     item not yet in the file, which is exactly when the file is stale; up to date, it runs offline),
#   every track.geojson, every boat's tracks.geojson and ships.json (check_track.py all --geojson),
#   army/army.json, seabees/seabees.json, operations/operations.json, boats/ss-385-bang/dives.json,
#   silhouettes/silhouettes.json, and through their own `check`: engagements/*/engagement.json,
#   engagements/index.json, convoys/convoys.json (build_engagement.py), subjects.json (build_subjects.py, after the army,
#   seabees and engagement builds it reads) and reference/glossary.json (build_glossary.py).
# Not guarded, because the committed file can't be rebuilt without the network or the git-ignored sources/ cache:
#   scans.json (nara.py index reads sources/nara/*/urls.txt; without the cache it only rewrites what it has),
#   seafloor.csv, weather.csv, army/seafloor.csv, seabees/weather.csv (NOAA, ERA5, ISD downloads),
#   relief/ (terrain tiles) and roads/oss967-primary.geojson (traced from a scan in sources/).
set -e
tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT
stale=0

# The files a build writes, against the commit: prints the diff's stat, names the build, and returns 1 if any differ
# or any is not yet tracked (a new patrol's track.geojson, say).
fresh() {
  what=$1; shift
  ok=0
  git -C records diff --exit-code --stat -- "$@" || ok=1
  untracked=$(git -C records ls-files --others --exclude-standard -- "$@")
  if [ -n "$untracked" ]; then echo "$untracked" | sed 's/^/ not committed: /'; ok=1; fi
  [ $ok = 0 ] || { echo "out of date: $what (commit the files above)"; return 1; }
}

out=$(uv run --quiet tools/check_sources.py --fetch 2>&1) || { echo "$out"; exit 1; }
fresh "citations.json (check_sources.py --fetch)" citations.json || stale=1

uv run --quiet tools/check_track.py all --geojson -q > "$tmp"
if grep "too-fast legs" "$tmp" | grep -v ": 0 too-fast legs"; then echo "a track has too-fast legs"; exit 1; fi
fresh "the tracks and ships.json (check_track.py all --geojson)" \
  'boats/*/patrol-*/track.geojson' 'boats/*/tracks.geojson' 'ships/*/track.geojson' ships.json || stale=1

python3 tools/build_army.py
fresh "army/army.json (build_army.py)" army/army.json || stale=1
uv run --quiet tools/build_seabees.py
fresh "seabees/seabees.json (build_seabees.py)" seabees/seabees.json || stale=1
uv run --quiet tools/build_operations.py
fresh "operations/operations.json (build_operations.py)" operations/operations.json || stale=1
uv run --quiet tools/build_dives.py
fresh "boats/ss-385-bang/dives.json (build_dives.py)" boats/ss-385-bang/dives.json || stale=1
uv run --quiet tools/build_silhouettes.py > /dev/null
fresh "silhouettes/silhouettes.json (build_silhouettes.py)" silhouettes/silhouettes.json || stale=1
uv run --quiet tools/build_engagement.py check
uv run --quiet tools/build_subjects.py check
uv run --quiet tools/build_glossary.py check

out=$(uv run --quiet tools/check_attacks.py 2>&1) || { echo "$out"; exit 1; }; echo "$out" | tail -1
node site/engage.test.js > /dev/null
out=$(uv run --quiet tools/test_tools.py 2>&1) || { echo "$out"; exit 1; }; echo "$out" | tail -1

[ $stale = 0 ] || { echo "a generated file is out of date: commit it"; exit 1; }
echo "builds: all up to date"
