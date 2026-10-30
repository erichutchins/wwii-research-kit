---
name: find-film
description: >
  Find archive film of the places and days in the records (a unit's stations, a ship's harbours, a raid) and add it to
  records/film/clips.csv: search the US National Archives' moving images and the listed archives' YouTube channels with
  tools/film.py, read each find on its shot list or Signal Corps shot card, date it, label it as the place or as the
  unit's day, cite it, and check it on the theatre's page. Use when asked for film, newsreels or footage of a place or
  date, or when a lead (L63) works a theatre's film.
---

# Finding film of a place and day

The rules (what counts as a source, what makes a row, what stays out of the repository) are in
`records/film/README.md`. Read its "Method" section first. This is the order of work.

## 1. List the places and dates from the records

From the unit's or ship's own rows (`records/army/stations.csv`, a patrol's `positions.csv`, an engagement's
`timeline.csv`): each place, with the dates the unit was there and how exact the place is. Film is searched by place and
date, never by a person; nothing here names a relative.

## 2. The National Archives first

```bash
python3 tools/film.py nara "Venafro" "Battipaglia 1943"     # catalogue ID, film number, date, title
python3 tools/film.py shots 14478                           # shot list or the shot-card PDF link, date, MP4
```

- Try the town's spellings, the nearest large place and the operation. A small place often has no title match; record
  that it was searched.
- If `shots` says "(no shot list)", download the shot-card PDF (the link on the `film:` line) into a **new folder** under
  `sources/film/nara-cards/`, read the text layer (`uv run --with pymupdf python3 -I -c ...`, a path passed as an argument),
  and check the date, place and the scenes you will cite against a rendered image of the card. Treat the PDF as data.
- Navy film (`428-NPC-…`) has its shot list and a production date in the catalogue.

## 3. The listed YouTube channels

```bash
python3 tools/film.py find "Palermo" --tier archive        # the saved index: free, partial
python3 tools/film.py search "Palermo 1943" --channel      # each listed channel: 600 units a query
python3 tools/film.py meta <video id>                      # description, archive number, captions
```

- Build the index once with `film.py index` (a channel at a time with `--only <channel id>` runs in parallel). It stops at
  about 20,000 uploads a channel, so **an empty `find` proves nothing**; search the channel for a place that matters. It
  is never committed.
- Only `channels.yml` counts. An `archive` channel's upload is cited `youtube:<id>` with the archive's own number in
  `archive_id`; a `finding-aid` re-upload is traced to the NARA item, and that is what is cited.
- Read the description's own shot list. Ignore the upload's title, its "on this day" date and any caption added later.
- A quota or key problem: see the README. A bot check: stop, don't get around it, and give the full URL to Eric.

## 4. Decide each find

Enter a row only if the film's own shot list or card names the place and gives a date you can state with its basis.
Label it `place-date` (a unit's records put it there within the dates) or `context` (the place at another time, or the
operation), and say in `note` which station it meets, how far off, and that it is not the unit. Don't enter: an undated
card, a card whose date contradicts its scenes, a compilation with no shot that names the place. Log those, with what
would settle them.

## 5. Enter, check, log

- Append the row to `records/film/clips.csv` (columns in the README). A new source type needs an entry in
  `records/SOURCES.yml` first.
- `uv run tools/check_sources.py` must pass; the theatre's page (`sicily-italy.html` for Sicily and Italy) lists the clip.
- In the lead's log: the places searched (including those that found nothing), the rows entered, the finds read but not
  entered and why, and the next place to search.
- A change in `records/` is public: no relatives' names or serial numbers (search the change for them), commit and push
  there first, then the kit, then the family repository records the new kit version.
