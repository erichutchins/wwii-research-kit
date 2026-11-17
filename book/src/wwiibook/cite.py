"""A citation, as the records write it, and what a page needs from it: the archive, the item, the page, a link and a
credit line.

  rg64-469722323/p0712   National Archives: record group 64, catalog item (NAID) 469722323, page 712

Only National Archives citations are read so far; JACAR (`jacar:C08030140600/p15`) and the Library of Congress come
next, each with its own fetcher.
"""
import re
from dataclasses import dataclass

NARA = re.compile(r"^rg(?P<group>\d+)-(?P<naid>\d+)/p(?P<page>\d+)$")


@dataclass(frozen=True)
class Cite:
    text: str      # as written in the records
    archive: str   # "nara"
    group: int     # record group
    item: str      # catalog ID (NAID)
    page: int      # 1-based page within the item

    @property
    def link(self) -> str:
        """The catalog's viewer, open at the page."""
        return f"https://catalog.archives.gov/id/{self.item}?objectPage={self.page}"

    @property
    def credit(self) -> str:
        return f"National Archives, RG {self.group}, NAID {self.item}, p. {self.page}"


def parse(text: str) -> Cite:
    m = NARA.match(text.strip())
    if not m:
        raise ValueError(f"not a citation this package can read yet: {text!r} (expected rg<group>-<naid>/p<page>)")
    return Cite(text.strip(), "nara", int(m["group"]), m["naid"], int(m["page"]))
