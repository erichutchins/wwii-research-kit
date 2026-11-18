# The atlas: one geography, two coordinated views

An atlas extent is a stretch of a campaign drawn twice in one projected frame:

- **the panorama**: wide and from above, the military situation leading;
- **the oblique view**: the same ground, front and divisions, seen from a low camera.

A third page gives the historical reference as scanned:
- the army group's own map of the day, where one exists;
- otherwise the period sheet itself, with the units' positions ringed.

```bash
cd book
uv run wwii-book atlas la-haye-du-puits --qgis       # reconstruct if needed, draw the views, write the GeoPackage
uv run wwii-book atlas bizerte --reconstruct           # rebuild the network from the sources
uv run wwii-book build examples/atlas-la-haye/book.typ # the pair and the plate as book pages
```

In a book: `atlas-view("<extent>", view: "panorama" | "oblique" | "sheet" | "inset", highlight: "<unit id>")`.

| Extent | Theatre | Period map | Front | The units' own records |
| --- | --- | --- | --- | --- |
| `la-haye-du-puits` | Normandy, July 1944 | IGN 1:50,000, red roads (1947–59) | 12th Army Group, 7 and 11 July | none |
| `northern-vosges` | Alsace, Dec 1944 – Feb 1945 | IGN 1:50,000, black roads (1939, 1953–56) | 12th Army Group, 31 Dec and 29 Jan | Battery D, 106th AAA AW Bn (SP) |
| `bizerte` | Tunisia, May – Oct 1943 | GSGS 4225, Tunisia 1:50,000 (1942) | none (after the Axis surrender) | Battery C, 62nd CA; Med. Det., 67th CA |
| `palermo` | Sicily, July 1943 – Apr 1944 | GSGS 4229, Italy 1:50,000 (1943) | none (the island taken) | Battery C, 62nd CA; other batteries' raids |
| `neuburg` | Bavaria, 26 April 1945 | none yet (no wartime German sheet in the atlas) | 12th Army Group, 26 April | the engagement `neuburg-1945-04-26`: the bombers' and jets' paths, losses and the guns' reach |
| `metz` | Lorraine, Jan – Feb 1945 | IGN 1:50,000, black roads (1953–57) | 12th Army Group, 14 Jan and 1 Feb | 9th Armored HQ; HQ Battery, 128th AAA Gun Bn; the old town's Catholic churches (inset) |

## An extent

`atlas/<name>/extent.yml` names everything and copies nothing.

**What it sets:**
- the box;
- the CRS: Lambert-93 in France, the UTM zone elsewhere (32N for Tunisia);
- the days of the fronts and divisions in `records/fronts/`, if there are any;
- the situation map's day;
- the units whose own records to draw (`stations:`, by unit and window);
- the locator's box and towns;
- the towns to name large;
- the period names of today's places (`names:`, e.g. Menzel Bourguiba → Ferryville);
- the period map (`sources.period_map`, with its options);
- the camera.

**Where the views read their data:**
- the fronts and divisions from the kit's `records/fronts/`;
- the units' positions and engagements from `records/army/army.json`, placed as the kit places them;
- the terrain from the cache;
- the network and woods from `infrastructure/`.

## Layers

| Layer | Source | Kept as |
| --- | --- | --- |
| period network, woods | the period map: IGN SCAN 50 Historique, 1950 series (WMTS, with each sheet's edition from its WFS index); or the Allies' wartime GSGS sheets (`gsgs.py`) | `infrastructure/*.geojson`, derived, every feature attributed |
| alignments | OpenStreetMap, Geofabrik's regional extract | used for alignment only |
| terrain | Copernicus DEM GLO-30, doi:10.5270/ESA-c5d3d65 | `build/dem-*.tif`, resampled to the extent's CRS |
| fronts, divisions | HQ Twelfth Army Group situation maps, as the kit traces them (`records/fronts/`) | read in place |
| a unit's positions and engagements | its own reports, as the kit transcribes and places them (`records/army/`) | read in place |

The sources are cached under `<cache>/ign`, `<cache>/maps`, `<cache>/copernicus` and `<cache>/osm`. Each download
keeps a `.source.json` note saying where it came from and when.

## The period map

**IGN's 1:50,000** covers France. Its 1950 series mixes editions, and they print roads in one of two ways
(`scan50_roads`):
- **red** (`la-haye-du-puits`), on the old *type 1922* sheets: solid main roads, dashed lesser ones;
- **black** (`northern-vosges`), cased with a white fill, on the later editions and some pre-war ones.

**The wartime GSGS sheets** cover North Africa, Sicily, Italy and Germany, where IGN doesn't reach. The units'
reports give positions on their grids, so each is the map the unit itself worked from. The series is described in
`atlas/sheets/<series>.yml`: the grid, the grid's ink, the library's address, and each sheet's file. Each sheet's
first labelled easting and northing were read by eye from its margin.

A GSGS sheet is placed by its own military grid:
1. The grid's lines are found on the scan. Each is followed band by band, since scans are often turned a degree or
   so.
2. They are numbered on a 1 km lattice from the sheet's labels. A stray stretch of the same ink is dropped.
3. Every crossing is converted to latitude and longitude through the grid's projection, as the kit's
   `tools/grid_ref.py` defines it.
4. A second-order polynomial is fitted to some 600 crossings a sheet.

Where the series prints each sheet's frame as a graticule (Italy's quarter sheets: 15' of longitude by 10' of
latitude, east of the Rome meridian), the frame is in the series file. The mosaic cuts each sheet to it. The frame
also checks the numbering: a first line set close to the frame can be lost, numbering every line one too late. So
shifts of up to 2 km are tried, and the one whose predicted frame runs darkest along the sheet's printed neat-line is
kept (249-IV and 250-III were one easting off, 258-I one northing).

The sea, printed as a fine ruled tint, is taken out by finding thin strokes darker than what is round them, after a
blur that removes the ruling. Italy's six sheets fit to 8–40 m. Battery C's "419445 Sheet 249-II NE" falls within
50 m of where the kit places it.

For Tunisia's six sheets the fit is within 6 to 18 m. The battery's own "J 775914" falls where the kit places it.
Sheets share their edge lines, so their footprints tile. Today's roads land within about 100 m of the sheet's lines
(a 1936 French survey, copied in 1942), so the matching tolerance is wider there (`road_tol_m: 80`).

## How the period network is reconstructed (`src/wwiibook/atlas/reconstruct.py`)

The period map establishes what existed. A modern way is reference, never proof. It is kept only where the sheet's
road ink runs beside it:
- within 30 m on IGN's sheets, 80 m on the wartime ones;
- within 25° of the ink's direction, read at the nearest ink, so a road crossing the line doesn't count.

Railways need dark line work within 25 m.

**What is drawn:**
- **Matched ways** are drawn on today's alignment. OSM's pieces are first joined end to end where nothing else meets
  them (OSM splits a road at every bridge and change of class), so a road is tested as a whole.
- **Short gaps** are closed where the modern road strays from the sheet's line but the sheet still shows the road
  nearby: a gap of up to 600 m inside one matched road, or a connecting stretch of up to 400 m whose both ends meet
  the kept network, in each case with road ink within 60 m along at least half of it. The data marks them
  (`bridged_m`, `connector`).
- **Red ink that no modern road explains** is traced from the sheet itself: a road since realigned or gone, or a
  misreading. It is drawn like the rest; the data keeps `geometry_source: traced:<sheet>`. Nothing is traced from
  black ink, which is also lettering, buildings and railways.
- **Loose ends are joined.** A road's end that meets no other road is carried in a straight line to the nearest road
  within 300 m (`joined_m`). A road under 600 m that still meets nothing at either end is marked `isolated` and left
  out of the views. The network is an illustration, best effort, not a survey.
- **The network is background.** It is drawn thin and quiet under the military layer, and continuous where the sheet
  is, so that no stretch stands out as a route anyone took. The records give the units' stations, not the roads
  between them.
- **Main or lesser** (`road_class`) is read from IGN's red ink (solid or dashed: along a dashed road, the distance to
  the ink jumps at every gap). On black and GSGS sheets it is OSM's class: trunk, primary and secondary are main. The
  data says which (`period_class`).
- **Woods** are the sheet's green, closed over its tree signs and traced as polygons: the period's woodland.
- **Junctions** are the branch points of IGN's red network.
- **River crossings** are where a period road or railway crosses a river. The views mark only those of main roads
  and railways.

**What every feature carries:**
- `source`: the sheet and its edition;
- `source_date`;
- `geometry_source`: `osm:way/<id>[,<id>...]` or `traced:<sheet>`;
- `validity`: what the source shows, and what that does and doesn't establish for the battle's year (the extent's
  `date`);
- `confidence`;
- `note`.

**Limits to keep in mind:**
- **Edition dates.** An edition more than three years after the battle says "likely in 1944, but post-war work may
  show". One before it says "there in 1939; one built since wouldn't show".
- **Railways.** OSM's railways include abandoned and razed lines. One the sheet doesn't show is kept in the data
  as `not seen` and is not drawn as the period's.
- **Not used for roads.** The 12th Army Group's 1:500,000 sheets are too generalised for roads, so none are
  extracted from them. They appear only as the plate.
- **Names.** Places are OSM's, in the local language, or in the extent's `language` (French for Tunisia, as its
  sheets name them). An extent's `names:` gives a place its period name, with today's beneath it.

**Churches**, for an extent that asks (`churches: true`; only `metz` so far):
- **On the panorama and the oblique view:** the Catholic cathedral, marked and named.
- **On the inset:** the town's Catholic churches, numbered, with a key. Only those a Sunday Mass would be in: named
  as a church, basilica or cathedral, so not a convent's or a hospital's chapel, nor an unnamed building.
- **Source:** OSM's Christian places of worship. Catholic means in communion with Rome, so Roman and Eastern
  Catholic alike; an untagged one is taken as Catholic.
- **Caveat:** today's buildings. One OSM dates after 1945 is dropped; whether the rest stood then is checked by hand.

**The inset** (`inset:` a box, a title, a zoom) is a detail at a larger scale, set beside the panorama: the period
map itself at its full detail (IGN's 1:50,000 at twice the panorama's tiles), with the churches on it. Metz's is the
old town, between the Moselle and the Seille.

## The units' own records (`record.py`)

An extent's `stations:` names units, a window, and each unit's symbol. Each unit is drawn in its own colour, as
`army.json` places it.

**Its symbol** is the Army's own (FM 21-30, October 1943, charts 13, 14 and 26), the same set the 12th Army Group's
maps use for divisions:
- anti-aircraft artillery: a triangle in the box;
- artillery other than anti-aircraft: a dot;
- Medical Corps: the box quartered by a cross;
- self-propelled: the box drawn with a tail;
- size above the box: I a battery or company, II a battalion, III a regiment or group, X a brigade;
- a battery's letter to the left, its unit's number to the right.

The symbol stands where the unit was on the map's date, if that is on the map, else at its longest stay on the
map. Its other positions are dots. A unit placed only by a town (HQ Battery, 128th AAA "Metz") has its symbol on a
short leader beside the town's point, so it doesn't cover the town's landmarks. A unit whose symbol the army group's
map already draws (the 9th Armored Division, in red) shows its own stations as dots only.

**Each position** shows how precisely the record places it:
- a position placed by grid reference: a dotted 1 km square, labelled with the reference as typed, and with the town
  and offset the entry also names, so a point 8 km from a town doesn't wear the town's name alone;
- a position placed by a town: a dotted ring about a kilometre across. Where the map already names that town, the
  mark carries only its dates, and the town's label names it once;
- consecutive positions within 500 m of each other: one mark, with the span of their dates;
- an entry placed only by a loose offset ("3 mi E" of a town, which can land in a lake) is folded into the next entry
  that gives a grid reference for the same place and offset within 30 days. Its date is kept as "from …, assumed",
  as the kit's notes on such rows say.

**No lines join a unit's positions.** A straight line between two dated positions isn't the way the unit went:
it crosses lakes and hills the unit never crossed, and on the oblique view worse. A move is said in words, in a label
or the caption; a route is drawn only where a record gives the route itself.

**The other side**, where the records see it:
- the aircraft the unit engaged;
- in grey, the aircraft other units in the records engaged inside the map and the window (Battery B, 62nd CA's Ju 88
  on 6 July 1943). These are placed where the reporting unit was, unless the report gives a grid reference.

Where a front's own map is wanting (Tunisia after 13 May 1943), that is all the other side the map shows. Leads L128
(where the summer 1943 raids' bombs fell) and L129 (the Army's own May 1943 sketches of the front round Mateur) are
the way to more.

Unit names only: the people are the family layer's.

## The renderers

**The panorama (`panorama.py`, SVG)** draws its layers bottom to top:
1. the terrain: shaded, with 20 m contours and the low ground under 6 m tinted;
2. the woods, as the sheet prints them;
3. rivers;
4. roads and railways, in warm greys, kept below the military layer;
5. the day's front and an earlier one;
6. the divisions as FM 21-30 symbols (corps and armies are left off at this scale);
7. the units' own positions and engagements;
8. the towns, placed clear of the symbols.

It also carries:
- a locator in the campaign;
- a scale bar;
- an arrow pointing to true north (a projected grid's north is a few degrees off it);
- a legend that names only what the map shows.

**The oblique view (`oblique.py`)** is a voxel-space render of the same grid:
- **The ground** is tinted, lit and contoured, with the woods and network drawn onto it, so roads climb and drop
  with the land.
- **The context margin** round the extent is paler, so the extent's edge doesn't read as a cliff. The picture ends
  a little below the extent's near edge, and below the nearest land over open sea.
- **The front** is a vector through the same camera, hidden by a depth buffer where a rise covers it.
- **Divisions** stand on stalks. A stalk is dotted when its foot is hidden.
- **Units' positions** and labels show only where the ground shows them.
- **A compass rose lies on the ground** near a lower corner, drawn through the same camera. Its ring is an ellipse and
  its needle is foreshortened toward true north, so the picture shows which way it looks without a word. The
  caption line says only that heights are exaggerated, and by how much.
- **Hills:** a few named summits are labelled, the highest first and none within 6 km of another.
- **The camera** suits the ground:
  - La Haye-du-Puits: 15° tilt, heights ×5. Tilt 8° hides too much behind the first ridge, and 25° starts to read
    as a plan. Heights ×3 flatten the bocage; ×9 makes Mont Castre a mountain.
  - The Vosges: 22°, ×4, so the ridges don't hide the valleys.
  - Bizerte: 25°, ×3.

**The sheet (`sheetview.py`)** is the period map over the extent, as scanned, with the units' positions ringed in
their colours. The rings are ours.

## QGIS 3D, evaluated

`--qgis` writes the extent as QGIS data:
- `build/<extent>.gpkg`: every layer, in the extent's CRS, attributes intact, plus the fronts, the units and the
  extent's outline;
- `build/dem-20m.tif`.

Open both, set the project CRS to the extent's, and use View › 3D Map Views to drape the layers on the DEM.

**What QGIS 3D does well:**
- exploring interactively, to choose the camera;
- checking that layers sit on the ground;
- vertical exaggeration;
- extruded or billboard symbols.

**What it lacks for the book:**
- **Print.** The 3D view exports only a raster image, with no vector labels.
- **Labels.** It has no label placement that avoids the units' symbols.
- **Hidden lines.** It has no depth-tested vector overlay to break the front where a ridge hides it.
- **Rebuilding.** A camera saved in a project file can't be rebuilt from `extent.yml` by a command.

**Three.js or MapLibre** would add a browser and a headless capture to the build, for a picture the voxel renderer
already makes from the same grid in about ten seconds.

**Recommendation:**
- Keep the book's oblique view in Python, where it is reproducible and prints as vector over raster.
- Use the GeoPackage in QGIS to scout cameras and check the reconstruction against the SCAN 50 layer, which QGIS can
  load from the same WMTS.
- Take MapLibre up only for the interactive site, where its 3D terrain and the same GeoJSON would serve directly.

This evaluation is from QGIS's documented 3D features and from the data written here. QGIS was not installed for
this prototype, so it has not been run.

## Licences

- OpenStreetMap data is © OpenStreetMap contributors, ODbL. The derived `infrastructure/` layers carry OSM
  alignments, so they are ODbL too.
- IGN's SCAN 50 Historique is under the Licence Ouverte (Etalab).
- The GSGS sheets are public domain scans from the University of Texas Libraries' PCL Map Collection.
- Copernicus DEM GLO-30 is © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018, provided under
  COPERNICUS by the European Union and ESA.

## The air view

An extent's `air:` block (a box at the scale of the sea between the airfields, a target, a window) draws the raids on
the target from `records/air/raids.csv` and the fields from `records/air/airfields.csv` (`atlas/air.py`). A raid
whose airfield a source names gets a thick, tapered, curved arrow from that field toward the target; the defending
fighters' arrows run from their fields to where they would meet the raiders. Arrows show direction only: no record
read gives a raid's route, so they are drawn wide and curved to read as "from there, toward here", never as tracks
(the rule for positions). Raids with no named field are listed in the column beside the map, as the raiding side's
record words them, with the defenders' own record of the same night where one exists. The extent's own units stand
at their positions in their FM 21-30 symbols, set off on leaders, and an AA unit with a `reach` (weapon, range in
yards, basis, page) has its guns' reach drawn as a ring, dashed where the gun is inferred; the panorama draws the
same ring at its own scale.


## The air war's two halves: the air view and the mission view

The air view (`air:`, `atlas/air.py`) draws raids on a target the units below defended: the raiders' fields, wide
arrows toward the target, the defending fighters' arrows to meet them (Bizerte, 1943: German night bombers, Allied
night fighters). The mission view (`mission:`, `atlas/mission.py`) is its complement: one day's mission flown over
the units, and the fighters sent up against it (Neuburg, 26 April 1945: the 17th Bomb Group's B-26s from Dijon, JV 44's
Me 262s from Munich-Riem). It is two pages:

- `view: "mission"`: the airfields' map. Each side's legs out and home are **notional**: wide, pale, curved arrows from
  its recorded field (`records/air/airfields.csv`) to the first point of its recorded path and back from the last,
  since the records give the ends and the fight, never the route between. The briefed target is ringed and said to
  be only that. The day's front from `records/fronts/`.
- `view: "fight"`: the box drawn large, from the engagement's own records (`engagement.json`): the routes by their
  basis (a course as typed solid, a squadron's sketch dashed), the losses, a report's grid square hatched, the guns'
  reach round their (often assumed) place, and the fighters' attack as the accounts describe it (head-on, over and
  round to attack from behind), computed from the sketched course and the loss, never stored, labelled notional.
  The minutes beside it are the engagement's entries inside `window`, as typed.

## The section: what the guns could see and reach

`sightline:` (`atlas/sightline.py`, `view: "sightline"`) is a vertical section along an aircraft's course (a route
of the engagement; with `back_km`/`on_km`, its typed course carried through its last point), from a battery's
position (a ring's `at`, assumed where the ring says so). Computed, never stored: the ground (Copernicus GLO-30), the
lowest height in sight from the guns over each point (a straight ray clearing the ground between, with the earth's
curve and refraction, k = 4/3), and each gun's reach where its sphere cuts the section. The heights the records type
are drawn above the guns' ground, since no record says above what: the page says so. GLO-30 includes today's woods.
