---
name: add-silhouette
description: >
  Add a recognition silhouette (an aircraft, a ship class, or a generic kind of ship for the battle
  pages) to records/silhouettes/silhouettes.yml from a wartime recognition plate: find and cite the
  plate, trace an aircraft's views from the scan or draw a ship's profile to the plate's printed
  heights, build silhouettes.json, link it from the ships it draws, and check it on the page. Use when
  asked to add, draw, trace or fix a silhouette, or when a page needs an aircraft or ship class that
  isn't there yet.
---

# Adding a silhouette

Every silhouette comes from a plate: a wartime recognition manual's drawing of that aircraft or
class, with its printed dimensions. **Never draw one from memory.** If no plate can be found, say so
and leave it out (the file's header notes there is no Hellcat for exactly this reason).

The conventions are in the header of `records/silhouettes/silhouettes.yml`. Read it first.

## 1. Find the plate and cite it

- **Japanese aircraft**: CINCPAC-CINCPOA Bulletin 105-45, *Japanese Operational Aircraft* (TAIC
  silhouettes; April 1945 edition in the NHHC online reading room, July 1945 revision on HyperWar).
- **US aircraft**: FM 30-30 / BuAer 3, *Recognition Pictorial Manual* (April 1943, Internet Archive).
- **Ships**: the ONI 54 series (ONI 54-D destroyers, 54-CV carriers, 54-R battleships, 54-C cruisers;
  ONI 208-J for Japanese ships, ONI 222-J for Japanese merchant ships). The plate prints the height of
  the bow, stern, bridge, stack and mast, and the length.
- Download the plate to `sources/` (never commit it). `tools/pdf_pages.py render` turns a PDF page into
  an image; `tools/gbooks.py` and `tools/nara.py` fetch from Google Books and the National Archives.
- If the manual isn't in `records/SOURCES.yml` yet, add an entry (title, by, held, url, rights,
  used_for). Every entry in silhouettes.yml lists its sources by id.

## 2a. An aircraft: trace it

Crop each view (plan, profile, head-on) and trace it:

```bash
uv run tools/trace_silhouette.py PLATE.png --crop X Y W H --symmetric --open 2 --name plan --preview /tmp/plan.png
uv run tools/trace_silhouette.py PLATE.png --crop X Y W H --open 2 --name profile --preview /tmp/profile.png
uv run tools/trace_silhouette.py PLATE.png --crop X Y W H --symmetric --name front --preview /tmp/front.png
```

- `--symmetric` for plan and head-on views (mirrors about the centre line, as the existing ones are);
  never for a profile.
- `--open N` drops antennas, pitot tubes and wires thinner than about 2N pixels. Too large a value
  rounds off wingtips: look at the preview.
- The plan and head-on views come out 100 units across the span; the profile 100 units across the
  length. For a head-on view, add `cx` and `cy` (the cowling or spinner centre) by hand.
- Open every preview: the red outline must follow the plate's edge everywhere except the details you
  meant to drop.

Then add the entry under `aircraft:`: `name` (the Allied code name and model, as the plate gives it),
`type`, `dims` and `span`/`length` (in feet, as printed), `source` (manual, edition, page),
`sources` (ids), and the views the tool printed.

## 2b. A ship class: draw it to the plate

Under `ships:`, give `name` (the class, as the plate names it), `length` in feet, `plate` (the manual,
date, and every height it prints, e.g. "ONI 54-D, 22 Jan 1944: bow 20', stern 10', bridge 35' ..."),
`sources`, and `parts`, in feet from the stern (x = 0) and the waterline (y = 0), bow to the right:

- the hull first, as one `[poly, [[x, y], ...]]` from the stern at the waterline;
- then superstructure: `[box, x0, x1, top, base]`, `[poly, ...]`, `[mast, x, top, base, width]`,
  `[gun, x0, x1, y, height]`;
- every printed height must be met (bow, stern, bridge, stack, mast, length); between them, follow the
  plate's drawing. Leave out details smaller than about 4 ft. Label parts with a comment (`# mount 53`).

## 2c. A generic kind of ship (battle pages)

Under `categories.shapes`, one path in the 120 × 24 box, bow to the right, waterline at y = 22, every
subpath clockwise. These stand for a kind of ship, not a class, so they stay generic; add one only
when an engagement needs a kind that isn't there (an `escorts` or `ships` entry whose `type` is new).

## 3. Build, link, check

```bash
uv run tools/build_silhouettes.py      # silhouettes.json; fails if a source id is missing
uv run tools/build_battle.py           # only after changing categories
```

- A ship class: add `silhouette: <key>` to the `ship.yml` of each vessel of that class
  (`records/ships/...` or `records/boats/...`). The link runs from the ship to the silhouette only.
- `uv run tools/check_track.py all --geojson` (rewrites `ships.json`), then
  `uv run tools/check_sources.py`, which fails on an uncited silhouette or a `silhouette:` that names
  nothing.
- Open `site/silhouettes.html` in light and dark mode: the new silhouette, at the same scale as the
  others, with its plate and the ships it draws.
