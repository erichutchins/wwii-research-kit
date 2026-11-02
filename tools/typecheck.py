# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Type-check Python files with ty, each against its own PEP 723 header: the packages it declares, the oldest Python
it claims.

Every tool here is a script whose header says what it needs (`uv run` builds its environment from that). ty checks a
set of files against one environment, which either lacks the scripts' packages (every import unresolved) or holds all
of them (an import a script never declared passes, and fails when someone runs it). So this groups the files by
header, has uv build each group's environment (cached after the first run), and runs ty once per group with that
environment and the header's minimum Python. A file with no header, or none giving requires-python, is an error:
`dependencies = []` declares the standard library alone. A shared module (records.py) declares what it imports
itself, like any script.

Usage: python3 tools/typecheck.py [--baseline FILE [--update-baseline]] PATH... [-- TY-ARGS...]
       PATHs are files or folders (every *.py under them); TY-ARGS go to `ty check` (--config-file, --extra-search-path).
       --update-baseline rewrites the baseline from this run, keeping the entries of files outside the PATHs.
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
import tomllib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

TY = ["uvx", "ty@0.0.95"]   # the one pin for ty: the kit's and the family's hooks and the kit's CI all run this
# PEP 723's reference expression for a metadata block
BLOCK = re.compile(r"(?m)^# /// (?P<type>[a-zA-Z0-9-]+)$\s(?P<content>(^#(| .*)$\s)+)^# ///$")


def header(path):
    """The file's `script` metadata as a dict, or None if it has none."""
    for m in BLOCK.finditer(path.read_text(encoding="utf-8")):
        if m["type"] == "script":
            lines = m["content"].splitlines(keepends=True)
            return tomllib.loads("".join(line[2:] if line.startswith("# ") else line[1:] for line in lines))
    return None


def floor(spec):
    """The oldest Python a requires-python allows: ">=3.10,<3.14" -> "3.10"."""
    m = re.search(r">=\s*(\d+\.\d+)", spec)
    return m[1] if m else None


def python_files(paths):
    for p in map(Path, paths):
        if p.is_file():
            yield p
            continue
        for q in sorted(p.rglob("*.py")):
            if not any(part.startswith((".", "__")) for part in q.relative_to(p).parts[:-1]):
                yield q


def check(group, ty_args, baseline, update):
    """uv's environment for the group's header, then ty over the group's files. Returns (ok, output, new baseline)."""
    first = str(group[0])
    sync = subprocess.run(["uv", "sync", "--quiet", "--script", first], capture_output=True, text=True)
    if sync.returncode:
        return False, f"uv sync --script {first}: {sync.stderr.strip()}", {}
    python = subprocess.run(["uv", "python", "find", "--script", first], capture_output=True, text=True,
                            check=True).stdout.strip()
    version = floor(header(group[0])["requires-python"])
    cmd = [*TY, "check", "--python", python, "--python-version", version, *ty_args]
    with tempfile.TemporaryDirectory() as tmp:
        written = Path(tmp) / "baseline.json"
        if update:
            cmd += ["--baseline", str(written), "--update-baseline"]
        elif baseline:
            cmd += ["--baseline", baseline]
        run = subprocess.run([*cmd, *map(str, group)], capture_output=True, text=True)
        found = json.loads(written.read_text())["files"] if update and written.exists() else {}
    ok = run.returncode == 0 or update
    return ok, (run.stdout + run.stderr).strip(), found


def main():
    argv = sys.argv[1:]
    ty_args = argv[argv.index("--") + 1:] if "--" in argv else []
    argv = argv[:argv.index("--")] if "--" in argv else argv
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("paths", nargs="+", metavar="PATH")
    ap.add_argument("--baseline", help="ty's JSON baseline: findings recorded there are not reported")
    ap.add_argument("--update-baseline", action="store_true", help="rewrite the baseline from this run")
    args = ap.parse_args(argv)
    if args.update_baseline and not args.baseline:
        ap.error("--update-baseline needs --baseline")

    groups, bad = {}, []
    for f in python_files(args.paths):
        meta = header(f)
        if meta is None or not floor(meta.get("requires-python", "")):
            bad.append(f"{f}: no PEP 723 header giving requires-python (\">=3.x\") and dependencies "
                       "(`dependencies = []` for the standard library alone)")
            continue
        key = (meta["requires-python"], tuple(sorted(meta.get("dependencies", []))))
        groups.setdefault(key, []).append(f)

    with ThreadPoolExecutor() as pool:
        results = list(pool.map(lambda g: check(g, ty_args, args.baseline, args.update_baseline), groups.values()))
    failed = 0
    for (spec, deps), group, (ok, output, _) in zip(groups, groups.values(), results):
        if not ok:
            failed += 1
            print(f"== Python {spec}, {', '.join(deps) or 'standard library'}: {len(group)} files", flush=True)
            print(output, flush=True)
    for line in bad:
        print(line)

    if args.update_baseline:
        path = Path(args.baseline)
        checked = {f.as_posix() for g in groups.values() for f in g}
        old = json.loads(path.read_text())["files"] if path.exists() else {}
        files = {k: v for k, v in old.items() if k not in checked}
        for _, _, found in results:
            files.update(found)
        path.write_text(json.dumps({"version": 0, "files": dict(sorted(files.items()))}, indent=2) + "\n")
        print(f"{path}: {sum(map(len, files.values()))} findings in {len(files)} files")

    n = sum(map(len, groups.values()))
    print(f"ty: {n} files in {len(groups)} environments; "
          + ("all passed" if not failed and not bad else f"{failed} environments with findings, {len(bad)} files with no header"))
    return 1 if failed or bad else 0


if __name__ == "__main__":
    sys.exit(main())
