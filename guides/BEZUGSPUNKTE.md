# German Army reference points (Bezugspunkte) in Italy, 1944

German reports from the Cassino and Garigliano front in 1944 don't give places as grid references. They give them as
codes: "71 35", "2 km südwestl. 60 22", "61 t Panzer am Nordrand XXIII 89". Each code is a **block number plus a point
number** on a secret overlay map, the *Bezugspunktkarte* (reference-point map). The decoder is `tools/bezugspunkt.py`.
The points read so far are in `reference/bezugspunkte/ausgabe4.csv` and the tests in `reference/bezugspunkte/anchors.csv`.
Started 30 Oct 2026 (lead L67).

## The key

The 4th edition is filmed at the head of NARA T-312 roll 90 (A.O.K. 10, KTB Anlagen, March 1944; catalog naId 333528157).
It is one large printed map, filmed in sections. Each section is marked with a card ("SECTION 5"). The title block on
Section 5 (`t312-0090/f0003`) reads, as printed:

> Geheim! / Italien 1 : 100 000 / Zusammendruck Gaeta / Maßstab 1:100000 (1 cm der Karte = 1 km der Natur) /
> Bezugspunktkarte 1:100000 / 4. Ausgabe / Achtung! Diese Karte darf nicht in die vordere Linie mitgenommen werden. /
> [boxed:] Dies ist ein geheimer Gegenstand im Sinne des § 88 Reichsstrafgesetzbuches (Fassung vom 24. April 1934). ... /
> BEARBEITUNG u. DRUCK: VERM.u.KART. ABT. (mot) 573

The roll's first frames are:

| Frame | Card | What it is |
|---|---|---|
| f0001 | | roll title ("T 312 - 90") |
| f0002 | Section 6 | Zusammendruck Gaeta: Sperlonga to the Volturno: Pontecorvo, Cassino, Esperia, Ausonia, Castelforte, Minturno, Mignano |
| f0003 | Section 5 | Zusammendruck Gaeta: San Felice Circeo to the Garigliano, with the title block |
| f0004 | Section 4 | Zusammendruck Gaeta (not yet read) |
| f0005 | Section 3 | north of Sections 5-6: Castro dei Volsci, Ceprano and the Liri valley up to Sora, blocks 89, 85, 31, 41, 57, 64 |
| f0006 | Section 2 | blocks 95, 84, 75, 55, 93, 49 (not yet placed) |
| f0007 | Section 1 | a separate sheet, **Zusammendruck Pescara**, Bezugspunktkarte 4. Ausgabe, stamped "O.B. ... März 44"; blocks 24, 87, 36, 30, 60, 13, 34, 95 |
| f0008-f0012 | Sections 6, 5, 4, 3, 2 | a second copy of the Gaeta sections (same blocks) |

Full-resolution frames are about 6,400 × 4,900 px (`https://catalog.archives.gov/medialz/dc-metro/rg-242/12007587/T312-0090/T312-0090-NNNN.jpg`).
At this size 1 km on the ground is about 83 px.

### How the code works (read on the map)

- The 1:100,000 Italian base is cut by heavy lines into **irregular blocks**, roughly 15-25 km across. Each block carries a
  large hatched **two-digit block number**. The numbers are not in sequence on the ground: 61, 59 and 42 lie side by side
  from west to east, with 64 north of 59 and 41 and 57 north of 61.
- Inside each block, **points are numbered from about 11 upward** (up to about 90), each a small circle drawn on a town,
  summit, crossroads or bridge. The number is written beside the circle.
- A code is **block, then point**: "71 35" is the circle numbered 35 in block 71, which is drawn on Sonnino. The same
  point number recurs in every block.
- Offsets are measured from a point ("2 km südwestl. 60 22", "600m NW XXIII 72"), and "Nordrand" means the north edge of
  the place at the point. The decoder applies distances along the eight compass directions. It reports an edge but
  doesn't move the point for it.

### Editions

- **4th edition** (this key): Arabic block numbers. It is filmed with the March 1944 Anlagen, and A.O.K. 10's May 1944
  traffic uses the same form ("60 22", Gruppe Hauck, 11.5.1944, `t312-0092` p. 6, OCR only). It was in use by the
  **end of February**: the Chief of Staff's situation map for "28+29. Februar 44" is drawn on the 4th edition's
  Zusammendruck Pescara (title box, `t312-0090/f0083`, read on the scan), while the map for 21 Feb (`f0113`) still
  carries the digit+letter blocks. So the change came between 21 and 28 Feb 1944 (read on the two maps; the exact day
  and any issuing order are not found).
- **February 1944** (to about 21-28 Feb): an earlier edition whose printed blocks are **a digit and a letter** (8Z, 8P,
  6X ...). The reports write a **Roman numeral** for the block and **add 11** to the point number: "XXIII 68" = Caira =
  printed **8Z 57**. Decoded by `feb1944.csv`; see "The February 1944 edition" below.
- **January 1944**: a letter and two digits ("V 37" = "NO Corigliano", `t314-0547/f0289`). Probably another edition.
- **"8 Z 18"** (XIV Pz.K. Ia, 1 Feb 1944, `t314-0546/f0838-0848`): the February edition by its printed block name.
  Printed 8Z 18 is a circle near Castrocielo (f0203), a plausible command post; whether the Ia's numbers are printed
  ones (no +11) is an **inference** from that one case.

## The February 1944 edition

**The map.** Tenth Army's situation maps for February 1944 (Ia, Anlagen zum KTB 5, Lagekarten; T-312 roll 90, filmed in
reverse: 1-10 Feb ≈ `f0215-f0296`, 11-20 Feb ≈ `f0131-f0214`, 21-29 Feb ≈ `f0071-f0130`) are drawn in sections on a
Bezugspunktkarte 1:100,000 whose large hatched block labels are **a digit and a letter**. No title box survives on the
February sections read (the inset "Blattübersicht der Karten 1:100 000" is on section 7), so the edition's number is
not known: it is the one before the 4th (2nd or 3rd). The base carries the **same Gauss-Krüger km grid** as the 4th
edition (margin figures "4620", "3400"; zone 3, 15°E, Bessel), so it was georeferenced the same way.

**The cover names.** Beside some blocks a Roman numeral is written by hand. These are the reports' block names:

| Printed block | Written beside it | Area | Frames | How sure |
|---|---|---|---|---|
| 8Z | XXIII | Cassino, Liri valley to Pignataro, Cervaro, S. Vittore | f0213, f0215 | read (plain on f0213) |
| 8P | XXIX | Monti Ausoni, Monte S. Biagio | f0213, f0215 | read |
| 9N | XXVII **+ 11** | Adriatic coast (section 2) | f0250 (map of 6 Feb), f0113 (21 Feb, cut: "XX...") | read |
| 5V | VIII | section 2 / 3 | f0113 | read |
| 8V | XII | Gaeta, Formia, the coast to Minturno | f0213 | read, faint pencil (earlier read "XI"); XII fits the reports' "Küstenstreifen O XII 65" |
| 6X | XXXV | Esperia, Pico, Ausonia hills | f0213, f0215 | top of the numeral cut; XXXVI not excluded |
| 8N | XXIV | section 2 | f0113 | faint: XXIV or XXV |
| 1T | V | north of Cassino (Casalattico, Atina) | f0215 | faint, tentative |
| 7T, 7P, 7Q | X?, III?, XX..? | Frosinone; Adriatic; Sora | f0215, f0113, f0073 | marks, not read |
| 9V, 3R, 9R | none seen | | f0213, f0215 | the reports' "IV" (middle Garigliano) is probably 3R: not read |

The numerals are the same wherever a block carries one (8Z on two 1-10 Feb maps; 9N on 6 and 21 Feb). Several maps of
11-20 Feb (`f0153`, `f0203`) carry none, so no change within the month can be seen; the reports keep "XXIII 89" for
Cassino from 7 to 12 Feb.

**The +11.** "XXVII + 11" is written beside 9N (`f0250`). The reports' 8Z numbers are the printed ones plus 11:
Caira is printed 57 and reported "XXIII 68"; Cassino is printed 78 and reported "Nordrand XXIII 89"; Terelle is printed
53, and the enemy came "auf den Strassen von XXIII 68 bis XXIII 64" (Caira to Terelle). So a report's "XXIII nn" is
printed 8Z (nn − 11). That the same +11 holds for every block is an **inference** (read for 9N, tested for 8Z only). The
Ia's "8 Z 18" orders appear to use the printed block and number without the offset (inference). The decoder applies
both: `decode "XXIII 68"` and `decode "8Z 57"` give the same circle.

**Points read** (`reference/bezugspunkte/feb1944.csv`): 67 circles of block 8Z on section 5 of a 1-10 Feb map
(`t312-0090/f0215`), from Castrocielo and Pignataro to Terelle, Cassino, Sant'Elia, Cervaro and S. Vittore (printed
numbers 14-124). Circles found by a Hough transform and read by eye; positions from the frame's own 2-km grid lines
(647 + 607 lines, fitted to 7 and 4 px, about 0.1 km). Points `?` where the number is covered by drawn symbols or its
circle is ambiguous; Caira, Cassino and 61 were read on `f0203` (11-20 Feb), where they are clean. Section 7 (8Z's
south: Ausonia, Castelforte, Minturno, the Garigliano; and blocks 3R, 8V) is not read yet.

**The test.** Nine towns printed beside their circles, none used in the fit, against OSM: Terelle 0.02 km, Caira
0.07, Cassino 0.10, Villa S. Lucia 0.12, Cervaro 0.25, S. Vittore 0.26, Sant'Elia 0.28, Pignataro Interamna 0.58, Piedimonte S. Germano 0.72. Median
0.25 km. (Pignataro had read 1.9 km: its expected position was OSM's first answer, the commune boundary's point, 1.6 km
from the village. OSM ranks a boundary first for many Italian communes; `tools/geocode_places.py` now prefers the
settlement, and `--audit` lists rows placed on a boundary.) The reports fit the ground: "XXIII 68" decodes to Caira at 0.07 km; "600 m NW XXIII 72" is 600 m NW of the
abbey of Monte Cassino (printed 61), "etwa 2,9 km SO XXIII 50" is the heights by Albaneta and Point 593 (2.9 km SE of
Villa S. Lucia, printed 39), both where the fighting was on 7 Feb (`t314-0547/f0740`). Rows in `anchors.csv`
(edition "Feb 1944").

## Method

1. **Sections.** Frames f0001-f0012 were downloaded at full resolution and identified from their cards and contents (table above).
2. **Georeferencing: the printed km grid.** The margins carry kilometre-grid figures every 2 km, and the grid lines are
   printed across the whole map. Read on full-resolution margin strips (30 Oct 2026):
   - Section 6 (f0002), bottom margin, west to east: 66, 68, ... 98, then **"34 00"** (x ≈ 2815 px), 02, 04 ... 38, and
     "40" at the corner, where the right margin's corner figure is **"4558"**. Right margin, bottom to top: 4558, **"4560"**
     (y ≈ 3975 px), 62 ... 94. The sheet is pasted from several pieces (seams near x ≈ 760 and 2330 px).
   - Section 5 (f0003), lower-left corner: **"33 34"** (easting) and **"45 58"** (northing; the earlier reading "4550" was
     wrong); bottom margin 36 (x ≈ 358 px), 38, 40 ...; left margin 4560 (y ≈ 4108 px), 62, 64 ...

   **Which grid.** Eastings in the 3,300-3,440 km range with northings of 4,558-4,594 km are a Gauss-Krüger grid with a
   zone prefix 3: central meridian **15°E**, false easting 3,500 km (Gaeta about 3,380 km). The **Italian Gauss-Boaga
   east zone is ruled out** by the figures (its false easting of 2,520 km gives eastings near 2,400 here, not 3,400).
   The ellipsoid and scale were tested against 17 towns on Section 6: the grid's northings match **Bessel 1841 with
   scale factor 1.0** (mean town offset +67 m north), against -450 m for Hayford with scale 1.0 and +1.4 km for Hayford
   or WGS84 with 0.9996 (UTM-like). So: **transverse Mercator, Bessel, k0 = 1, central meridian 15°E, false easting
   3,500 km, no false northing**: the German Army's Gauss-Krüger practice (6° zones numbered from 3°E, zone 3). The
   grid's name isn't printed on the sections read: that name is an **inference** from the figures and the fit. The
   datum (the Bessel-based Italian or German network) isn't known; its shift from WGS84 here is of the order of 100-200 m
   and is inside the noise below (the mean town offset is +167 m E, +67 m N, and removing it doesn't improve the
   leave-one-out residuals).

   **The fit.** The grid lines were found by machine: in 600 px windows every 300 px, the period and phase of thin straight
   lines across the window (166-170 px per 2 km, about 83-85 px per km). Each line was labelled from the margin figures
   (by its nearest even kilometre under a first linear model), and the labels fitted with a cubic polynomial, then used
   locally: a decoded pixel takes a weighted affine fit to the labelled lines within about 1 km (`local` model), which
   follows the pasted seams. On Section 6, **682 easting and 659 northing line observations; rms 7.9 px (95 m) in
   easting and 4.6 px (55 m) in northing** after rejecting spurious lines. Laid back over the frame the fitted lines sit
   on the printed ones. The projection maths (Krüger series, standard-library Python) is in the working scripts (below).

   **Test on independent towns** (no town is used in the grid fit): 17 towns on Section 6, each placed by eye on 2x
   zoomed tiles (the town's houses, or the circle drawn on it), against OSM Nominatim. **rms 0.44 km, median 0.34 km**:
   Campodimele, SS. Cosma e Damiano, Pignataro, Vallemaio, Aquino, S. Vittore, Ausonia, Coreno under 0.25 km; Itri,
   Sessa, Cervaro, Mignano, Lenola, Piedimonte 0.34-0.58 km; Conca, Pontecorvo, S. Pietro Infine 0.66-0.78 km (S. Pietro
   was rebuilt on a new site after 1943, so OSM's point may not be the town on the map). Fitting a constant or linear
   shift through the towns does **not** lower the leave-one-out error (0.42 and 0.50 km), so the remaining error is not
   a datum shift or a tilt: it is in the town positions (by eye, and OSM's point for each comune) and in the old
   Italian 1:100,000 base itself. **The target of 300 m is not met on modern coordinates**: the grid fit is the map's
   own coordinate system to about 0.1 km, but a decoded point is good to about **0.4 km against the ground today**.
   The positions in `ausgabe4.csv` (Section 6) moved by a median 0.19 km (at most 0.39 km) from the town fit.
   - Section 5 (f0003): **not yet refitted.** The grid is detected (602 easting, 457 northing lines), the northings fit
     (rms 5 px), but the eastings are mislabelled across a pasted seam (residuals jump by about 100 px near x ≈ 3300 px;
     rms 27 px). Its two rows (71 35, 48 19) keep the earlier town fit (rms 464 m). To finish: split the frame at its seams
     and label each piece from its own margin figures, or label window by window from the neighbours.
   - Working scripts (not in the kit): `sources/drafts/bezugspunkte-fit/` (git-ignored) (`grid.py` finds the line combs, `fitgrid.py`
     labels and fits, `model.py` the global and local models, `tmx.py` the projection, `towntest2.py` the town test,
     `rebuild.py` rewrites the Section 6 rows).
3. **Points.** Numbers were read by eye on full-resolution crops shown at 0.83 scale. Each reading was snapped to a
   circle found by a Hough transform when one lay within 20 px (the note says how far). Otherwise the position is the
   eye reading (to about ±15 px, ±0.2 km). Uncertain numbers are marked `?` in `read`. Where the same number was read
   twice in one block, both readings are marked: one of them is wrong.
4. **Names.** `name_as_printed` is filled only where a town name is printed against the circle. A trailing `?` means
   the name is near the circle but could belong to the place next to it.

## What has been read (4th edition)

`ausgabe4.csv`: 183 rows, from Section 6 (f0002) unless noted. The block from Cervaro to Venafro is **88**: its outlined
numeral is on Section 4 (f0004, px ≈ 3640,4010), inside one outline with points 11-26, 38-40, 49, 50 and the annotation
"3. alg. S.D."; on Section 4 the same block's points 51-88 run on over Pozzilli (57), Lucenteforte (58), Venafro (50) and
Roccaravindola (about 66): read on the frame, not yet in the table.

| Block | Area | Points read |
|---|---|---|
| 61 | Lenola, Campodimele, Esperia, M. Fammera, S. Oliva | 40 |
| 59 | Ausonia, Coreno, Vallemaio, Castelforte, SS. Cosma e Damiano, Minturno, the lower Garigliano | 32 |
| 64 | Pontecorvo, Aquino, Pignataro, Cassino, S. Angelo in Theodice | 29 |
| 42 | S. Vittore, S. Pietro Infine, Mignano, Rocca d'Evandro | 26 |
| 57 | Pico, S. Giovanni Incarico | 15 |
| 68 | Itri, Formia, Scauri | 15 |
| 41 | Vallecorsa, Falvaterra (the block's southern part) | 13 |
| 88 | Cervaro, Conca Casale, Viticuso; 88 50 is Venafro (block number read on Section 4, f0004) | 11 |
| 71, 48 | Sonnino (71 35), Terracina (48 19, block to confirm), on Section 5 (f0003) | 2 |

The block numbers 64, 57 and 41 were read on Section 3 (f0005), where the blocks continue north. They are marked in the
note. Point 57 of block 64 lies by the name "Cassino" but its reading is uncertain.

## Anchors and accuracy

`anchors.csv` tests the decoder against places named in the documents. The five map anchors are names printed beside
circles on the key itself. They test the georeferencing, not the code:

| Code | Place | Error |
|---|---|---|
| 71 35 | Sonnino | 0.54 km (Section 5: earlier town fit, Sonnino used in it) |
| 48 19 | Terracina | 0.58 km (Section 5: earlier town fit, Terracina used in it) |
| 42 85 | S. Pietro Infine | 0.78 km (grid fit; the town was rebuilt on a new site) |
| 42 57 | Mignano | 0.47 km (grid fit) |
| 61 27 | Lenola | 0.55 km (grid fit) |

The Section 6 anchors are now independent of the fit (the grid fit uses no towns). None of the report anchors can be tested yet. "60 22" (11 May 1944) is in block 60, which is on the Pescara sheet
(Section 1, f0007), not yet georeferenced, and the report doesn't name the place. "XXIII 68" and "V 37" belong to
earlier editions. A decoded point is good to **about 0.4 km** against modern coordinates (Section 6, grid fit), about half a kilometre on Section 5.

## What's missing

- The rest of the 4th edition: Sections 2 and 4 (f0006, f0004), the north of Section 3 (Sora, Arce, Roccasecca), the
  east of Section 6 (blocks 50, 77 and the Volturno), the west of Section 5 (blocks 86, 71, 48), and the Pescara sheet.
  Block 88's points on Section 4 (51-88: Pozzilli, Lucenteforte, Roccaravindola, Montaquila, Filignano).
- Section 5's grid fit: a piecewise fit (seam at x ≈ 3530 px; the left margin steps at y ≈ 2115) is good east of the seam
  (7.6 px) but not west of it (18-23 px; six towns not used in the fit, rms 632 m, southern towns east, northern west, about
  1.2 km apart: a further seam or shear). So 71 35 and 48 19 keep the earlier town fit. Next: trace single vertical lines
  across the left piece to find the break. Then Sections 3, 2, 4 the same way. Getting under 300 m against modern coordinates will need better town positions than OSM's comune points (e.g. the church or castle of each old centre), or accepting the old base map's own error.
- **The earlier editions** (Roman and lettered blocks, January-February 1944). Leads are in `sources/drafts/german-army-codes.md`:
  A.O.K. 10's Lagekarten for February 1944 (index at `t312-0088/f0005-0008`), the tail of roll 89 (early February), and
  Höh. Art. Kdr. 316's files.
- Report anchors of March-May 1944 that name a place with its code (T-312 rolls 91-92, OCR'd, will find candidates; read them on the scan).

## Proposed SOURCES entries

For `records/SOURCES.yml`, in the existing entries' form (to be added by the calling session):

```yaml
nara-t312:
  title: Records of German Field Commands, Armies (NARA microfilm publication T-312)
  by: German Army (Armeeoberkommandos); filmed by the American Historical Association / NARA
  held: U.S. National Archives and Records Administration (NARA), Record Group 242
  id: T-312 (catalog series naId 12007587)
  url: https://catalog.archives.gov/id/12007587
  rights: Public domain (captured records filmed by the U.S. government)
  cite: t312-<roll, 4 digits>/f<frame, 4 digits>      # e.g. t312-0090/f0003
  match: '^t312-(\d{4})/f(\d{4})$'
  link: https://catalog.archives.gov/medialz/dc-metro/rg-242/12007587/T312-{1}/T312-{1}-{2}.jpg
  used_for: >-
    reference/bezugspunkte: the Bezugspunktkarte 1:100000, 4. Ausgabe (Verm.u.Kart.Abt. (mot) 573), filmed in
    sections on roll 90 (A.O.K. 10, KTB Anlagen, March 1944; catalog naId 333528157), f0002-f0012.
  note: >-
    Frames are the catalog's file numbers (the objectPage, and the number in the frame URL). Rolls 88-90 have no
    OCR; 91 and 92 (April and May 1944, naIds 333531002 for 92) have.

osm-nominatim:   # only if not already present under another key
  title: OpenStreetMap Nominatim geocoder
  by: OpenStreetMap contributors
  url: https://nominatim.openstreetmap.org/
  rights: ODbL 1.0
  cite: OSM Nominatim
  used_for: town coordinates used to georeference the Bezugspunktkarte sections and to test its anchors
```

If the kit already cites T-314 frames in the form `t314-0547/f0740`, give them a matching `nara-t314` entry (series
naId 12007589 to be confirmed in the catalog).
