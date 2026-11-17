# /// script
# requires-python = ">=3.11"
# dependencies = ["boto3>=1.34"]
# ///
"""Mirror the public part of the scan cache (`sources/`) to an S3-compatible bucket (Cloudflare R2), so that a cloud
session, which starts without the cache, can pull what the tools and the book's examples read instead of fetching it
again from the archives (slow, and rate-limited).

Only the folders listed in PUBLIC are ever sent: archive scans and the re-downloadable map, terrain and OpenStreetMap
caches. Nothing else under `sources/` is touched, so anything a family layer keeps there stays on the machine that has it.

  uv run tools/cache_sync.py status                 what would be sent, by folder (no credentials needed)
  uv run tools/cache_sync.py push [folder ...]      upload new and changed files
  uv run tools/cache_sync.py pull [folder ...]      download what is missing locally

Credentials, from the environment (never from a file in the repository):
  R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, and optionally R2_BUCKET (default wwii-cache) or
  R2_ENV_FILE, a file of KEY=value lines to read them from (outside the repository, e.g. ~/.config/wwii/r2.env).
"""
import hashlib
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = Path(os.environ.get("WWII_CACHE") or ROOT / "sources")

# public archive scans and re-downloadable caches: what the tools and the examples read
PUBLIC = [
    "nara", "jacar", "gallica", "lastampa", "loc", "chronicling", "hyperwar", "dtic", "dtic-remagen", "archive-org",
    "tna", "etoob", "fm-30-30-ia", "fm-4-155", "manuals", "tdc-manuals", "oni-207", "oni226", "oni-merchant", "usanjor",
    "janac-ia", "frupac", "ntmj", "ndl-ussbs", "t312", "t314", "t315", "t1022", "luftwaffe", "seabee-museum",
    "silhouettes", "silhouettes-ja", "insignia", "air-photos", "commons",
    "geo", "natural-earth", "naturalearth", "terrain-tiles", "etopo1", "copernicus", "ign", "maps", "gsgs-italy",
    "osm", "osm-rail", "era5", "isd", "german-grids",
]


def _env():
    f = os.environ.get("R2_ENV_FILE")
    if f and Path(f).expanduser().exists():
        for line in Path(f).expanduser().read_text().splitlines():
            k, _, v = line.partition("=")
            if k.strip() and not line.lstrip().startswith("#"):
                os.environ.setdefault(k.strip(), v.strip())
    missing = [k for k in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY") if not os.environ.get(k)]
    if missing:
        sys.exit("missing " + ", ".join(missing) + " (see the docstring)")


def _client():
    import boto3
    _env()
    return boto3.client("s3", endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
                        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
                        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"], region_name="auto")


def _bucket() -> str:
    return os.environ.get("R2_BUCKET", "wwii-cache")


def _folders(args: list[str]) -> list[str]:
    bad = [a for a in args if a not in PUBLIC]
    if bad:
        sys.exit("not in the public list: " + ", ".join(bad))
    return args or PUBLIC


def _local(folders):
    for d in folders:
        base = CACHE / d
        if base.is_dir():
            for p in base.rglob("*"):
                if p.is_file() and not p.name.startswith("."):
                    yield p


def _md5(p: Path) -> str:
    h = hashlib.md5()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _remote(s3, prefix: str) -> dict[str, tuple[int, str]]:
    out = {}
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=_bucket(), Prefix=prefix):
        for o in page.get("Contents", []):
            out[o["Key"]] = (o["Size"], o["ETag"].strip('"'))
    return out


def status(args):
    total = 0
    for d in _folders(args):
        files = list(_local([d]))
        size = sum(p.stat().st_size for p in files)
        total += size
        if files:
            print(f"{d:16s} {len(files):7d} files {size / 1e9:8.2f} GB")
    print(f"{'total':16s} {'':7s}       {total / 1e9:8.2f} GB")


def push(args):
    s3 = _client()
    for d in _folders(args):
        have = _remote(s3, d + "/")
        todo = []
        for p in _local([d]):
            key = p.relative_to(CACHE).as_posix()
            r = have.get(key)
            if not r or r[0] != p.stat().st_size or ("-" not in r[1] and r[1] != _md5(p)):
                todo.append((p, key))
        print(f"{d}: {len(todo)} to send", flush=True)
        with ThreadPoolExecutor(8) as ex:
            list(ex.map(lambda t: s3.upload_file(str(t[0]), _bucket(), t[1]), todo))


def pull(args):
    s3 = _client()
    for d in _folders(args):
        have = _remote(s3, d + "/")
        todo = [k for k, (size, _) in have.items()
                if not (CACHE / k).exists() or (CACHE / k).stat().st_size != size]
        print(f"{d}: {len(todo)} to fetch", flush=True)

        def get(k):
            (CACHE / k).parent.mkdir(parents=True, exist_ok=True)
            s3.download_file(_bucket(), k, str(CACHE / k))
        with ThreadPoolExecutor(8) as ex:
            list(ex.map(get, todo))


if __name__ == "__main__":
    cmd, *rest = sys.argv[1:] or ["status"]
    {"status": status, "push": push, "pull": pull}[cmd](rest)
