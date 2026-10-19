r"""FRUPAC war maps: find the Fleet Radio Unit Pacific map overlays for a ship
or a date.

The National Museum of the Pacific War's FRUPAC map collection is on UNT's
Portal to Texas History. Its search pages are behind a bot check, but the
catalog is harvestable through the library's OAI-PMH feed (set
collection:FRUPAC). The maps themselves are CC BY-NC-ND, so they are linked
and read in the zoom viewer, never copied.

Commands:
  python3 tools/frupac.py harvest              catalog -> sources/frupac/catalog.json
  python3 tools/frupac.py find "\bBang\b"     maps whose title/description/keywords match (a regex;
                                                 plain "Bang" also hits Sabang, Palembang)
  python3 tools/frupac.py date 1944-06-29 [3]  maps covering a date (+/- N days)

The zoom viewer (https://texashistory.unt.edu/ark:/67531/<ark>/m1/1/zoom/)
serves full-resolution tiles; the plain page images are only ~1500 px wide.
"""
import json
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, timedelta

from records import CACHE, rel  # noqa: E402
CATALOG = CACHE / "frupac" / "catalog.json"
OAI = "https://texashistory.unt.edu/oai/"
NS = {"oai": "http://www.openarchives.org/OAI/2.0/", "dc": "http://purl.org/dc/elements/1.1/"}


def harvest():
    maps, params = [], {"verb": "ListRecords", "metadataPrefix": "oai_dc", "set": "collection:FRUPAC"}
    while True:
        with urllib.request.urlopen(f"{OAI}?{urllib.parse.urlencode(params)}", timeout=90) as r:
            root = ET.parse(r).getroot()
        for rec in root.iterfind(".//oai:record", NS):
            dc = lambda tag: [e.text or "" for e in rec.iterfind(f".//dc:{tag}", NS)]
            ark = rec.findtext(".//oai:identifier", namespaces=NS).rsplit("/", 1)[-1]
            maps.append({"ark": ark, "title": "".join(dc("title")), "date": "".join(dc("date")),
                         "description": " ".join(dc("description")), "subjects": dc("subject")})
        token = root.findtext(".//oai:resumptionToken", namespaces=NS)
        print(f"  {len(maps)} maps", file=sys.stderr)
        if not token:
            break
        params = {"verb": "ListRecords", "resumptionToken": token}
    CATALOG.parent.mkdir(parents=True, exist_ok=True)
    json.dump(sorted(maps, key=lambda m: m["date"]), open(CATALOG, "w"), indent=1, ensure_ascii=False)
    print(f"wrote {rel(CATALOG)} ({len(maps)} maps)")


def catalog():
    if not CATALOG.exists():
        harvest()
    return json.load(open(CATALOG))


def span(d):
    """'1944-06-29', '1944-06-29/1944-07-05' or '1944-05' -> (first, last) day."""
    a, _, b = d.partition("/")
    first = date.fromisoformat(a if len(a) == 10 else a + "-01")
    if b:
        return first, date.fromisoformat(b if len(b) == 10 else b + "-28")
    if len(a) == 7:   # a whole month
        nxt = (first.replace(day=28) + timedelta(days=4)).replace(day=1)
        return first, nxt - timedelta(days=1)
    return first, first


def show(m):
    print(f"{m['date']:<23} {m['ark']}  {m['title']}")
    print(f"{'':<23} https://texashistory.unt.edu/ark:/67531/{m['ark']}/m1/1/zoom/")


def main():
    cmd, args = (sys.argv[1], sys.argv[2:]) if len(sys.argv) > 1 else ("", [])
    if cmd == "harvest":
        harvest()
    elif cmd == "find" and args:
        pat = re.compile(args[0], re.I)
        for m in catalog():
            if pat.search(" ".join([m["title"], m["description"], *m["subjects"]])):
                show(m)
    elif cmd == "date" and args:
        day, pad = date.fromisoformat(args[0]), timedelta(days=int(args[1]) if len(args) > 1 else 0)
        for m in catalog():
            if not re.match(r"\d{4}-\d\d", m["date"]):
                continue
            first, last = span(m["date"])
            if first - pad <= day <= last + pad:
                show(m)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
