# Navy muster rolls: following a shore unit

How the Seabee battalions in `records/seabees/` were rebuilt, and how to do the next one. The
rolls were made to account for men, not places, so a battalion's stations come from three kinds of
evidence put together: the rolls' few place entries, the Bureau of Yards and Docks' log of the
battalion, and published histories.

## The rolls

NARA RG 24, *Muster Rolls of U.S. Navy Ships, Stations, and Other Naval Activities*, series
[594996](https://catalog.archives.gov/id/594996). One file unit per battalion (search the catalog
for "<n>th Construction Battalion"), filmed in date order, with OCR. Per quarter:

- the **forwarding sheet** (NAVPERS 605): the date forwarded and "From": a code name ("White
  Poppy"), a Navy number ("Navy 250"), a camp ("Camp Parks"), or only "c/o FPO, San Francisco";
- the **roll** (605a): every man, rating, date of enlistment, date first received on board;
- the monthly **Reports of Changes** (605b): received, transferred, re-rated, died, each with the
  place sent to or come from;
- the **recapitulation** (605d): numbers brought forward and carried forward.

`tools/morning_reports.py` works on any catalog file unit: `pages <id> "<text>"` finds pages by
OCR (a service number, "Navy", "Forwarded", "Hosp"), `text <id> <pages>` prints the OCR, and
`fetch <id> <pages>` downloads the scans. It caches under `sources/nara/rg64-<id>/`; for a muster
roll make the folder `rg24-<id>` and link `rg64-<id>` to it, so cache and citations agree.

## Places from the rolls

- **Forwarding sheets.** Read every one (`text` the pages around each recapitulation, then the
  scan). A code name or Navy number dates the battalion there.
- **Navy numbers** in the transfers (`To USN Base Hosp. Navy #3245`): look them up in the NHHC
  *Navy Numbers* list (`SOURCES.yml` `navy-numbers`). A run of transfers to a local hospital or
  base places the battalion there; a single transfer to a distant hospital (Navy 10, Aiea, from
  Okinawa) is an evacuation and places nothing.
- **Mass entries**: a whole battalion transferred or received on one day (to a training center
  for leave, from a replacement depot) dates a move.
- **Men left behind** on the day it sailed (transferred to the depot) date the sailing.
- **Burials** name the cemetery.

Read each value on the scan; the OCR only finds the page.

## Places from the battalion's history sheet

The Navy Seabee Museum has scanned the Bureau of Yards and Docks' "Historical Information" cards
for most battalions (`SOURCES.yml` `ncbhist`): embarkations with dates, and a log quoting the
battalion's monthly reports ("arrived Guadalcanal 14 Jun'43, Russell Is. 16 Jun'43"). These are
the best dates of sailing and arriving. The margin date is when the entry was logged.

## Parts of a battalion

Battalions split: two sailings, a forward echelon, detachments of a company or less. Give each
part its own `part` in `stations.csv`, and say in `units.csv` how the rolls name them (they may
number sections differently from the history sheet). A roll that lists a whole part together
doesn't say which group of it a man was in.

## Checks

`stations.csv` columns are in `records/seabees/README.md`. Mark `assumed` when a row is put on
the 15th of a month, or drawn at a stand-in point (an island, a mail address); the note says
which. Then `uv run tools/check_sources.py` (with `--fetch` after citing a new file unit), and
update `records/inventory.yml`.
