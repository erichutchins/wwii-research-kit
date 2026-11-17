"""Where the records and the scan cache are: the same places, and the same variables, as the kit's tools/records.py.

  RECORDS  the transcribed records: <kit>/records, or wherever WWII_RECORDS points
  CACHE    downloaded scans and API caches (git-ignored, always re-downloadable): <kit>/sources, or WWII_CACHE
  TYPST    the `wwii-book` Typst package shipped with this one, as a Typst package path (local/wwii-book/<version>)
  FONTS    the fonts the package's pages are set in, bundled so a book looks the same on any machine
"""
import os
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent
KIT = PACKAGE.parents[2]          # <kit>/book/src/wwiibook -> <kit>
TYPST = PACKAGE / "typst"
FONTS = PACKAGE / "fonts"        # Barlow Condensed, Source Serif 4, Courier Prime (SIL Open Font License, beside them)


def records() -> Path:
    return Path(os.environ.get("WWII_RECORDS") or KIT / "records")


def cache() -> Path:
    return Path(os.environ.get("WWII_CACHE") or KIT / "sources")
