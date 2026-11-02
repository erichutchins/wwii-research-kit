#!/bin/sh
# Every build checks out (0 problems) and every generated file it writes is up to date: what the CI runs
# (.github/workflows/pages.yml), and the pre-push hook (.pre-commit-config.yaml). Run from the kit.
#
# The generated files are in records/, a submodule: `git diff` from the kit sees no change inside it, so the
# comparison is made in records/ itself.
set -e
uv run --quiet tools/check_sources.py > /dev/null
python3 tools/build_army.py
uv run --quiet tools/build_seabees.py
uv run --quiet tools/build_operations.py
uv run --quiet tools/build_dives.py
uv run --quiet tools/build_engagement.py check
uv run --quiet tools/build_glossary.py check
out=$(uv run --quiet tools/check_attacks.py 2>&1) || { echo "$out"; exit 1; }; echo "$out" | tail -1
node site/engage.test.js > /dev/null
out=$(uv run --quiet tools/test_tools.py 2>&1) || { echo "$out"; exit 1; }; echo "$out" | tail -1
uv run --quiet tools/check_track.py all -q > /tmp/check_track.txt
if grep -v ": 0 too-fast legs" /tmp/check_track.txt; then echo "a track has too-fast legs"; exit 1; fi
git -C records diff --exit-code --stat -- army/army.json seabees/seabees.json operations/operations.json \
  boats/ss-385-bang/dives.json || { echo "a generated file is out of date: commit it"; exit 1; }
echo "builds: all up to date"
