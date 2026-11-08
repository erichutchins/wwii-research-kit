#!/usr/bin/env bash
# Whether a push can change what the pages show, for the CI's smoke test: prints pages=true or pages=false (a line for
# $GITHUB_OUTPUT), and each changed file, as doc or page, on stderr.
#
# false only when every file changed between BEFORE and AFTER is documentation:
#   - in the kit, Markdown (guides/, the READMEs, CLAUDE.md, the skills and agents in .claude/) and LICENSE: no page or
#     build reads them;
#   - in records/ (when the push moves the submodule), the READMEs and LICENSE. The records' other Markdown
#     (engagement.md, convoy.md, the operations' index.md, a battalion's projects) is data the pages draw: it counts.
# A missing or unreadable BEFORE (a run by hand, a new branch, a force push past it) answers true.
#
# Usage: tools/pages_changed.sh BEFORE [AFTER]     (AFTER defaults to HEAD; run from the kit)
set -euo pipefail
before=${1:-}
after=${2:-HEAD}

pages() { [ $# -gt 0 ] && echo "$*" >&2; echo "pages=true"; exit 0; }
# a commit here, or fetched by its hash (its tree alone: enough for a list of names)
have() { git -C "$1" cat-file -e "$2^{commit}" 2>/dev/null || git -C "$1" fetch -q --depth=1 --filter=blob:none origin "$2" 2>/dev/null; }

[[ $before =~ ^[0-9a-f]{40}$ && $before != 0000000000000000000000000000000000000000 ]] || pages "no earlier commit to compare with"
have . "$before" || pages "can't read $before"

docs=true
while IFS= read -r f; do
  case $f in
    "" | records) continue ;;   # records, the submodule's pointer: its own files are below
    *.md | .claude/* | LICENSE) echo "doc   $f" >&2 ;;
    *) echo "page  $f" >&2; docs=false ;;
  esac
done <<< "$(git diff --no-renames --name-only "$before" "$after")"

old=$(git rev-parse "$before:records" 2>/dev/null || true)
new=$(git rev-parse "$after:records")
if [ "$old" != "$new" ]; then
  [ -n "$old" ] && have records "$old" || pages "can't read the records' earlier commit ${old:-(none)}"
  while IFS= read -r f; do
    case $f in
      "") continue ;;
      README.md | */README.md | LICENSE) echo "doc   records/$f" >&2 ;;
      *) echo "page  records/$f" >&2; docs=false ;;
    esac
  done <<< "$(git -C records diff --no-renames --name-only "$old" "$new")"
fi

if [ "$docs" = true ]; then echo "pages=false"; else echo "pages=true"; fi
