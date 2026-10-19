# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
"""One clock for a wolfpack: every boat's torpedo attacks and the Japanese-side
events, merged and sorted by GMT, so you can read who fired when.

Usage: uv run tools/pack_timeline.py [START END]
       (defaults to BANG/PARCHE/TINOSA, 29 Apr - 5 May 1944; START/END as 1944-04-29T00:00)

Writes records/boats/ss-385-bang/patrol-1/pack_timeline.csv. Attack-sheet rows marked off the track
(on_track=no) are still listed, with their fix note, because a doubtful
summary-table time is part of the story; narrative firing rows (ref "... fired")
are listed beside them.
"""
import csv
import sys
from datetime import datetime

from check_crossrefs import load_japanese
import records
from check_track import load

PACK = {"ss-385-bang": "ss-385-bang/1", "ss-384-parche": "ss-384-parche/1", "ss-283-tinosa": "ss-283-tinosa/6"}
JAPANESE = "ss-385-bang/1"  # japanese.csv lives with BANG's Patrol 1 for now


def rows(start, end):
    out = []
    for boat, patrol in PACK.items():
        for r in load(patrol):
            if (r["source"] == "attack" or r["ref"].endswith(" fired")) and start <= r["utc"] <= end:
                out.append({"utc": r["utc"], "side": boat, "what": r["ref"],
                            "local": f"{r['date']} {r['time']}({r['zone']})",
                            "position": f"{r['lat_fix'] or r['lat_raw']} {r['lon_fix'] or r['lon_raw']}",
                            "detail": r["note"], "doubt": r["fix_note"] if r["on_track"] == "no" or r["time_fix"] else "",
                            "source": r["page"]})
    for j in load_japanese(JAPANESE).values():
        if j["utc"] and start <= j["utc"] <= end:
            out.append({"utc": j["utc"], "side": "japanese", "what": f"{j['ship']} {j['event']}".strip(),
                        "local": f"{j['date']} {j['time']}({j['zone']})",
                        "position": f"{j['lat_raw']} {j['lon_raw']}".strip(),
                        "detail": j["translation"], "doubt": "secondary source" if j["source"].startswith("combinedfleet") else "",
                        "source": f"{j['source']} {j['page']}".strip()})
    return sorted(out, key=lambda r: r["utc"])


def main():
    start, end = (datetime.fromisoformat(a) for a in sys.argv[1:3]) if len(sys.argv) > 2 else (
        datetime(1944, 4, 29), datetime(1944, 5, 5))
    out = rows(start, end)
    for r in out:
        flag = "  [?]" if r["doubt"] else ""
        print(f"{r['utc']:%m-%d %H%MZ}  {r['side']:<14} {r['what']:<34} {r['local']:<20} {r['position']:<22}{flag}")
    path = records.unit_dir(JAPANESE) / "pack_timeline.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["utc", "side", "what", "local", "position", "detail", "doubt", "source"])
        w.writeheader()
        for r in out:
            w.writerow({**r, "utc": f"{r['utc']:%Y-%m-%dT%H:%MZ}"})
    print(f"wrote {records.rel(path)} ({len(out)} events)")


if __name__ == "__main__":
    main()
