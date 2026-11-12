# The German Army's reference points (Bezugspunkte) in Italy, 1944

German reports from the Cassino and Garigliano front in 1944 don't give places as grid references. They give them as
a **block plus a point number** on a secret overlay map, the *Bezugspunktkarte* (reference-point map). This guide sets
out how the code works, which editions of the map have been keyed and how firmly, how accurate a decoded point is, and
what is still open. The decoder is `tools/bezugspunkt.py`. The points read so far are in
`reference/bezugspunkte/` (`jan1944.csv`, `feb1944.csv`, `ausgabe4.csv`, one file per edition) and the tests in
`reference/bezugspunkte/anchors.csv`. The readings below were made on 30 October 2026.

```bash
python3 tools/bezugspunkt.py decode "71 35"                    # also "2 km SW 60 22", "Nordrand 61 27"
python3 tools/bezugspunkt.py decode "XXIII 68" --date 1944-02-07   # the edition in force on the report's date
python3 tools/bezugspunkt.py check                             # anchors.csv: decoded against the expected place
```

The records are those of Tenth Army (Armeeoberkommando 10, "A.O.K. 10" on the film) and of XIV Panzer Corps
("XIV Pz.K."), on National Archives microfilm T-312 and T-314. Frames are cited `t312-<roll>/f<frame>` and
`t314-<roll>/f<frame>`. Three terms recur: the war diary (*Kriegstagebuch*, KTB), its appendices (*Anlagen*) and the
operations section of a staff (*Ia*), whose situation maps (*Lagekarten*) the reference points are drawn on.

## 1. What the code looks like

"71 35", "2 km südwestl. 60 22", "Nordrand XXIII 89", "M 28": a block, then a point, sometimes with an offset or an
edge before them. "XXIII 68" in XIV Panzer Corps' reports of February 1944 is Caira, north of Cassino; the decoder
places it 0.07 km from the village (section 4).

The map the codes refer to is printed. The title block of the 4th edition (`t312-0090/f0003`) reads:

> Geheim! / Italien 1 : 100 000 / Zusammendruck Gaeta / Maßstab 1:100000 (1 cm der Karte = 1 km der Natur) /
> Bezugspunktkarte 1:100000 / 4. Ausgabe / Achtung! Diese Karte darf nicht in die vordere Linie mitgenommen werden. /
> [boxed:] Dies ist ein geheimer Gegenstand im Sinne des § 88 Reichsstrafgesetzbuches (Fassung vom 24. April 1934). ... /
> BEARBEITUNG u. DRUCK: VERM.u.KART. ABT. (mot) 573

("Secret! ... Composite sheet Gaeta ... Reference-point map 1:100,000, 4th edition. Attention! This map must not be
taken into the front line ... Prepared and printed by Survey and Map Detachment (mot) 573.")

## 2. How it works

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

### The three editions

Each edition renumbered the blocks and the points, so a code can only be decoded with the report's date
(`--date`). **V, X, I and L** are both January block letters and February cover names.

| In use | Printed block | As the reports write it | Key file |
|---|---|---|---|
| January 1944 | one letter (M, D, C, H, V ...), points from 01 | the printed letter and number: "M 28" | `jan1944.csv` |
| February 1944, to between 21 and 28 Feb | a digit and a letter (8Z, 8P, 6X ...) | a Roman numeral for the block, and the printed point number plus 11: "XXIII 68" = printed 8Z 57 | `feb1944.csv` |
| From the end of February 1944 (the 4th edition), still in May | a two-digit number (61, 59, 42 ...), points from about 11 | the printed numbers: "71 35" | `ausgabe4.csv` |

**January 1944.** A separate edition with **one printed letter per block** and points numbered from 01 ("V 37" = "NO
Corigliano", `t314-0547/f0289`; circle 37 of block V is about 1 km NE of the printed Corigliano, `t312-0084/f0470`). No
Roman cover names and no +11. Its numbers are unrelated to February's (Caira is D 43 in January, 8Z 57 in February).
The maps are Tenth Army's January situation maps on **T-312 roll 84**, filmed in reverse (1-10 Jan f0436-f0502). Blocks M
(Venafro, Filignano, Acquafondata, Vallerotonda, Viticuso, Cervaro), D (S. Elia, Cassino; the letter isn't printed on the
frames read, so D is inferred by elimination), C (the Mainarde) and H (Atina, Belmonte) are keyed from section 6
(`f0440`) into `jan1944.csv`: 87 points, the frame's 2-km grid fitted (about 80 m) with no towns used. The town test is in section 4.
XIV Panzer Corps' reports of 12 Jan 1944 decode on it: M 28 Vallerotonda, M 30 Cervaro, D 12 S. Elia, C 10 M. Marrone.

**February 1944.** An edition whose printed blocks are **a digit and a letter** (8Z, 8P, 6X ...). The reports write a
**Roman numeral** for the block and **add 11** to the point number: "XXIII 68" = Caira = printed **8Z 57**.

*The map.* Tenth Army's situation maps for February 1944 (Ia, Anlagen zum KTB 5, Lagekarten: the operations section's
maps, appendices to war diary 5; T-312 roll 90, filmed in
reverse: 1-10 Feb ≈ `f0215-f0296`, 11-20 Feb ≈ `f0131-f0214`, 21-29 Feb ≈ `f0071-f0130`) are drawn in sections on a
Bezugspunktkarte 1:100,000 whose large hatched block labels are **a digit and a letter**. No title box survives on the
February sections read (the inset "Blattübersicht der Karten 1:100 000" is on section 7), so the edition's number is
not known: it is the one before the 4th (2nd or 3rd). The base carries the **same Gauss-Krüger km grid** as the 4th
edition (margin figures "4620", "3400"; zone 3, 15°E, Bessel), so it was georeferenced the same way.

*The cover names.* Beside some blocks a Roman numeral is written by hand. These are the reports' block names:

| Printed block | Written beside it | Area | Frames | How sure |
|---|---|---|---|---|
| 8Z | XXIII | Cassino, Liri valley to Pignataro, Cervaro, S. Vittore | f0213, f0215 | read (plain on f0213) |
| 8P | XXIX | Monti Ausoni, Monte S. Biagio | f0213, f0215 | read |
| 9N | XXVII **+ 11** | Adriatic coast (section 2) | f0250 (map of 6 Feb), f0113 (21 Feb, cut: "XX...") | read |
| 5V | VIII | section 2 / 3 | f0113 | read |
| 8V | XII | Gaeta, Formia, the coast to Minturno | f0213 | read, faint pencil; XII, not XI: it fits the reports' "Küstenstreifen O XII 65" (coastal strip east of XII 65) |
| 6X | XXXV | Esperia, Pico, Ausonia hills | f0213, f0215 | top of the numeral cut; XXXVI not excluded |
| 8N | XXIV | section 2 | f0113 | faint: XXIV or XXV |
| 1T | V | north of Cassino (Casalattico, Atina) | f0215 | faint, tentative |
| 7T, 7P, 7Q | X?, III?, XX..? | Frosinone; Adriatic; Sora | f0215, f0113, f0073 | marks, not read |
| 9V, 3R, 9R | none seen | | f0213, f0215 | the reports' "IV" (middle Garigliano) is probably 3R: not read |

The numerals are the same wherever a block carries one (8Z on two 1-10 Feb maps; 9N on 6 and 21 Feb). Several maps of
11-20 Feb (`f0153`, `f0203`) carry none, so no change within the month can be seen; the reports keep "XXIII 89" for
Cassino from 7 to 12 Feb.

*The +11.* "XXVII + 11" is written beside 9N (`f0250`). The reports' 8Z numbers are the printed ones plus 11:
Caira is printed 57 and reported "XXIII 68"; Cassino is printed 78 and reported "Nordrand XXIII 89"; Terelle is printed
53, and the enemy came "auf den Strassen von XXIII 68 bis XXIII 64" (Caira to Terelle). So a report's "XXIII nn" is
printed 8Z (nn − 11). That the same +11 holds for every block is an **inference** (read for 9N, tested for 8Z only). The
Ia's "8 Z 18" orders appear to use the printed block and number without the offset (inference). The decoder applies
both: `decode "XXIII 68"` and `decode "8Z 57"` give the same circle.

*"8 Z 18"* (XIV Panzer Corps, Ia, 1 Feb 1944, `t314-0546/f0838-0848`) is the February edition by its printed block
name. Printed 8Z 18 is a circle near Castrocielo (f0203), a plausible command post; whether the Ia's numbers are
printed ones (no +11) is an **inference** from that one case.

**The 4th edition** (from the end of February 1944). Arabic block numbers. It is filmed at the head of T-312 roll 90
(Tenth Army, appendices to the war diary, March 1944; catalog naId 333528157), and Tenth Army's May 1944 traffic uses
the same form ("60 22", Gruppe Hauck, 11.5.1944, `t312-0092` p. 6, OCR only). It was in use by the **end of
February**: the Chief of Staff's situation map for "28+29. Februar 44" is drawn on the 4th edition's Zusammendruck
Pescara (title box, `t312-0090/f0083`, read on the scan), while the map for 21 Feb (`f0113`) still carries the
digit+letter blocks. So the change came between 21 and 28 Feb 1944 (read on the two maps; the exact day and any
issuing order are not found).

It is one large printed map, filmed in sections. Each section is marked with a card ("SECTION 5"). The roll's first
frames are:

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

## 3. What is established, what is probable, what is open

**Established.** The form of the code (block, then point, with offsets from the point) and the three editions and
their dates, each read on the maps. For the 4th edition, the printed grid and its georeferencing on Section 6. For
February, the cover name XXIII = 8Z and the +11 in that block, tested against nine towns and against where the reports
put the fighting. For January, blocks M, C and H as printed.

**Probable** (each an inference, marked so where it is used). That February's +11 holds for every block (read for 9N,
tested for 8Z only). That the Ia's "8 Z 18" form uses printed numbers without the offset. That January's block D is
the Cassino block (its letter isn't printed on the frames read). The name of the 4th edition's kilometre grid
(section 4). The faint cover names in the table above (6X, 8N, 1T).

**Open.** Most of every edition is unread: the lists below say what is in each key file, and section 6 what is not.

### January 1944 (`jan1944.csv`)

87 points in blocks M, D, C and H, from section 6 of a 1-10 January map (`t312-0084/f0440`).

### February 1944 (`feb1944.csv`)

67 circles of block 8Z on section 5 of a 1-10 Feb map
(`t312-0090/f0215`), from Castrocielo and Pignataro to Terelle, Cassino, Sant'Elia, Cervaro and S. Vittore (printed
numbers 14-124). Circles found by a Hough transform and read by eye; positions from the frame's own 2-km grid lines
(647 + 607 lines, fitted to 7 and 4 px, about 0.1 km). Points `?` where the number is covered by drawn symbols or its
circle is ambiguous; Caira, Cassino and 61 were read on `f0203` (11-20 Feb), where they are clean. Section 7 (8Z's
south: Ausonia, Castelforte, Minturno, the Garigliano; and blocks 3R, 8V) is not read yet.

### The 4th edition (`ausgabe4.csv`)

183 rows, from Section 6 (f0002) unless noted. The block from Cervaro to Venafro is **88**: its outlined
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

## 4. Accuracy

A decoded point of the 4th edition is good to **about 0.4 km** against modern coordinates on Section 6 and about half
a kilometre on Section 5; February's block 8Z to a median 0.25 km; January's blocks to a median 0.30 km, with block C
good to about 1.3 km. In each case the map's own grid is fitted to about 0.1 km, and the rest of the error is in the
town positions and in the old Italian 1:100,000 base.

### The 4th edition: the printed kilometre grid

Frames f0001-f0012 were downloaded at full resolution and identified from their cards and contents (the table in
section 2). The margins carry kilometre-grid figures every 2 km, and the grid lines are printed across the whole map.
Read on full-resolution margin strips:

- Section 6 (f0002), bottom margin, west to east: 66, 68, ... 98, then **"34 00"** (x ≈ 2815 px), 02, 04 ... 38, and
  "40" at the corner, where the right margin's corner figure is **"4558"**. Right margin, bottom to top: 4558, **"4560"**
  (y ≈ 3975 px), 62 ... 94. The sheet is pasted from several pieces (seams near x ≈ 760 and 2330 px).
- Section 5 (f0003), lower-left corner: **"33 34"** (easting) and **"45 58"** (northing; read as 58, not 50, in agreement with Section 6's corner figure, 4558); bottom margin 36 (x ≈ 358 px), 38, 40 ...; left margin 4560 (y ≈ 4108 px), 62, 64 ...

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
on the printed ones. The projection is computed with the Krüger series; the working scripts are not in the kit.

**Test on independent towns** (no town is used in the grid fit): 17 towns on Section 6, each placed by eye on 2x
zoomed tiles (the town's houses, or the circle drawn on it), against OSM Nominatim. **rms 0.44 km, median 0.34 km**:
Campodimele, SS. Cosma e Damiano, Pignataro, Vallemaio, Aquino, S. Vittore, Ausonia, Coreno under 0.25 km; Itri,
Sessa, Cervaro, Mignano, Lenola, Piedimonte 0.34-0.58 km; Conca, Pontecorvo, S. Pietro Infine 0.66-0.78 km (S. Pietro
was rebuilt on a new site after 1943, so OSM's point may not be the town on the map). Fitting a constant or linear
shift through the towns does **not** lower the leave-one-out error (0.42 and 0.50 km), so the remaining error is not
a datum shift or a tilt: it is in the town positions (by eye, and OSM's point for each comune) and in the old
Italian 1:100,000 base itself. **A target of 300 m against modern coordinates is not met**: the grid fit is the map's
own coordinate system to about 0.1 km, but a decoded point is good to about **0.4 km against the ground today**.
The positions in `ausgabe4.csv` (Section 6) moved by a median 0.19 km (at most 0.39 km) from the town fit.
- Section 5 (f0003): **not fitted to the grid.** The grid is detected (602 easting, 457 northing lines), the northings fit
  (rms 5 px), but the eastings are mislabelled across a pasted seam (residuals jump by about 100 px near x ≈ 3300 px;
  rms 27 px). Its two rows (71 35, 48 19) are placed by a fit to towns instead (rms 464 m).

**Points.** Numbers were read by eye on full-resolution crops shown at 0.83 scale. Each reading was snapped to a
circle found by a Hough transform when one lay within 20 px (the note says how far). Otherwise the position is the
eye reading (to about ±15 px, ±0.2 km). Uncertain numbers are marked `?` in `read`. Where the same number was read
twice in one block, both readings are marked: one of them is wrong.

**Names.** `name_as_printed` is filled only where a town name is printed against the circle. A trailing `?` means
the name is near the circle but could belong to the place next to it.

### The 4th edition: anchors

`anchors.csv` tests the decoder against places named in the documents. The five map anchors are names printed beside
circles on the key itself. They test the georeferencing, not the code:

| Code | Place | Error |
|---|---|---|
| 71 35 | Sonnino | 0.54 km (Section 5: town fit, Sonnino used in it) |
| 48 19 | Terracina | 0.58 km (Section 5: town fit, Terracina used in it) |
| 42 85 | S. Pietro Infine | 0.78 km (grid fit; the town was rebuilt on a new site) |
| 42 57 | Mignano | 0.47 km (grid fit) |
| 61 27 | Lenola | 0.55 km (grid fit) |

The Section 6 anchors are independent of the fit (the grid fit uses no towns). None of the report anchors can be tested yet. "60 22" (11 May 1944) is in block 60, which is on the Pescara sheet
(Section 1, f0007), not yet georeferenced, and the report doesn't name the place. "XXIII 68" and "V 37" belong to
earlier editions. A decoded point is good to **about 0.4 km** against modern coordinates (Section 6, grid fit), about half a kilometre on Section 5.

### February 1944

Nine towns printed beside their circles, none used in the fit, against OSM: Terelle 0.02 km, Caira
0.07, Cassino 0.10, Villa S. Lucia 0.12, Cervaro 0.25, S. Vittore 0.26, Sant'Elia 0.28, Pignataro Interamna 0.58, Piedimonte S. Germano 0.72. Median
0.25 km. (Pignataro's expected position is the village, not OSM's first answer, which is the commune boundary's point 1.6 km
away and would give 1.9 km. OSM ranks a boundary first for many Italian communes; `tools/geocode_places.py` prefers
the settlement, and `--audit` lists rows placed on a boundary.) The reports fit the ground: "XXIII 68" decodes to Caira at 0.07 km; "600 m NW XXIII 72" is 600 m NW of the
abbey of Monte Cassino (printed 61), "etwa 2,9 km SO XXIII 50" is the heights by Albaneta and Point 593 (2.9 km SE of
Villa S. Lucia, printed 39), both where the fighting was on 7 Feb (`t314-0547/f0740`). Rows in `anchors.csv`
(edition "Feb 1944").

### January 1944

The frame's 2-km grid is fitted (about 80 m) with no towns used. Test: 23 towns printed beside their circles against OSM place nodes, median 0.30 km, rms 0.55 km; M and D within 0.04-0.38 km, but block C's north-east corner 1.0-1.3 km off (Castelnuovo, Scapoli, Castel S. Vincenzo): treat C as good to about 1.3 km.

## 5. Sources

- **Tenth Army's records**: National Archives microfilm T-312 (Record Group 242), `nara-t312` in
  `records/SOURCES.yml`. Roll 90: the 4th edition at its head (f0002-f0012) and the February 1944 situation maps;
  roll 84: the January 1944 situation maps; rolls 91-92 (April and May 1944) have OCR. Full-resolution frames are at
  `https://catalog.archives.gov/medialz/dc-metro/rg-242/12007587/T312-0090/T312-0090-NNNN.jpg`.
- **XIV Panzer Corps' records**: T-314 rolls 546 and 547 (`nara-t314`): the reports that use the codes.
- **Town positions**: OpenStreetMap, through its Nominatim geocoder (`osm-nominatim`), for the tests only. No town is
  used in a grid fit.
- **Not found**: the order that issued an edition or changed it, the exact day of the change in February, and the
  number of the February edition.

## 6. Open questions

- The rest of the 4th edition: Sections 2 and 4 (f0006, f0004), the north of Section 3 (Sora, Arce, Roccasecca), the
  east of Section 6 (blocks 50, 77 and the Volturno), the west of Section 5 (blocks 86, 71, 48), and the Pescara sheet.
  Block 88's points on Section 4 (51-88: Pozzilli, Lucenteforte, Roccaravindola, Montaquila, Filignano).
- Section 5's grid fit: a piecewise fit (seam at x ≈ 3530 px; the left margin steps at y ≈ 2115) is good east of the seam
  (7.6 px) but not west of it (18-23 px; six towns not used in the fit, rms 632 m, southern towns east, northern west, about
  1.2 km apart: a further seam or shear). So 71 35 and 48 19 keep the town fit. Single vertical lines traced
  across the left piece would find the break; Sections 3, 2 and 4 need the same fit. Getting under 300 m against modern coordinates will need better town positions than OSM's comune points (e.g. the church or castle of each old centre), or accepting the old base map's own error.
- **The earlier editions** (Roman and lettered blocks, January-February 1944): the rest of
  Tenth Army's situation maps for February 1944 (index at `t312-0088/f0005-0008`), the tail of roll 89 (early February), and
  the files of Höherer Artillerie-Kommandeur 316 (a senior artillery command). February's section 7 (8Z's south,
  and blocks 3R and 8V) and the cover names not yet read; January's other blocks.
- Report anchors of March-May 1944 that name a place with its code (T-312 rolls 91-92, OCR'd, will find candidates; read them on the scan).
