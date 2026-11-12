# The Kriegsmarine's naval grid squares (Marinequadrate) in the Mediterranean

The German Naval Staff's war diary, the U-boat war diaries and the German signals give positions as naval grid
squares. This guide sets out how the grid works, which squares of the Mediterranean have been read off the wartime
charts and how firmly, how accurate a decoded position is, and what is still open. The decoder is
`tools/naval_grid.py`. The blocks read so far are in `reference/naval-grid/squares.csv`, and the test positions (the
anchors) are in `reference/naval-grid/anchors.csv`. The measurements below were made on 30 October 2026.

```bash
python3 tools/naval_grid.py decode "CJ 9472" CN3282 "CJ 94"   # corners and centre of each cell
python3 tools/naval_grid.py check                              # anchors: decoded against the place named
python3 tools/naval_grid.py blocks                             # what is digitized
```

Frames are cited as `t1022-2099/f<frame>`: National Archives microfilm T-1022, roll 2099, here "f0200" for short.

## 1. What the code looks like

"three destroyers heading north in CJ 9472 at the northern coast of Sicily" (`skl:55/p397`, the Naval Staff's war
diary, the *Kriegstagebuch* or KTB, in the US Navy's translation): two letters and up to four digits. The decoder
places CJ 9472 37 nm north of Cefalù (anchor N6, section 4).

## 2. How it works

- **The large square (Großquadrat) is two letters.** Its regular size is 486 nm on a side, so 8°06′ of latitude
  high. The OKM's own instruction (chart 3001, *Quadratkarten*, edition of 10.VIII.1944, quoted by Schmidt, p. 23)
  says: "Die Großquadrate haben im allgemeinen 486 sm Kantenlänge mit Ausnahmen derjeniger, die wegen der Anlehnung
  an den Verlauf der Küste in eine unregelmäßige Form gebracht werden mußten." The grid sits on a Mercator chart.
  Its rows are equal arcs of latitude. Its columns are a whole number of minutes of longitude wide, and that number
  is reset at *Sprunglinien*, "jump lines" (Schmidt, pp. 12-13, 22).
- **Each digit splits the square before it 3 × 3, numbered like a telephone keypad**: 1 NW, 2 N, 3 NE, 4 W,
  5 centre, 6 E, 7 SW, 8 S, 9 SE. The first digit is a block of the large square. The first two digits ("CJ 94") are
  the squares printed large on the chart. The third digit is printed small in each of their nine parts as "10",
  "20" ... "90", read on T-1022 roll 2099, f0200. The fourth digit is the smallest cell, about 6 nm. That the fourth
  digit is also keypad-numbered comes from the published definition (Schmidt; navalgrid.com): the chart draws those
  cells but doesn't number them. A trailing 0 means the digit wasn't given, which matches the chart's "x0" labels.
- **In this part of the Mediterranean the lattice is 6′ × 8′.** Measured on frame f0200 (below), the fourth-digit
  cells are 6′ of latitude by 8′ of longitude. So a two-digit square is 54′ × 72′ (1°12′), a block is 2°42′ × 3°36′,
  and a regular large square is 8°06′ × 10°48′. Row edges fall on latitudes ≡ 36′ (mod 54′): 45°36′, 37°30′, 29°24′
  for the large squares and 40°12′, 39°18′, 38°24′ … between them. Column edges fall on 6°30′E ± k·72′.
- **CH and CJ are irregular.** Their blocks don't all line up:
  - **CJ's west column** (CJ 1, 4, 7, Sardinia) sits one two-digit row (54′) south of CJ 2/3/5/6/8/9. CJ 77-79
    reach 36°36′N, so **CN 11-13 do not exist**: CN 1 holds only 14-19.
  - **CH's two western columns** (CH 1, 2, 4, 5, 7, 8) sit one row south of CH 3/6/9.
  - CH's southern edge steps along the Algerian coast, and DJ lies below it (f0318). That outline is not digitized:
    the decoder places the blocks, not the outline.
  - CK, CO and CP, east of 17°18′E, are regular on the 1892 G sheet (f0074, f0091): nine blocks each, all 81
    two-digit squares printed, on the same 8′ columns. **CQ is offset**: its west edge is CP 8's (31°42′E), so CQ 1
    lies under CP 8 and CQ 2 under CP 9 (f0091, the heavy lines run down from CP into CQ).
- **North of 45°36′N the columns are 10′ wide.** On f0074 the grid lines of BH and BJ, above CK's top edge, fall on
  whole 10′ of longitude from 14°20′ to 34°30′E, and the BH|BJ edge (23°00′E) doesn't line up with CK's block edges.
  This is the jump line at 45°36′ that Schmidt describes (p. 22). The decoder holds only squares south of it.

## 3. What is established, what is probable, what is open

**Established.** The keypad numbering of the first three digits, read on the charts; the 6′ × 8′ lattice south of
45°36′N, measured against the charts' own scales on two sheets (section 4); the layout of CH, CJ, CN, CO and CP and of
CK's and CQ's columns. Every block in `squares.csv` carries how its edges were obtained in `method`:

| `method` | What it means | Blocks |
|---|---|---|
| `measured` | columns and rows both measured against a chart's scale | the blocks of CH, CJ and CN on f0200; CO 1-9 and CP 1-9 (columns on f0091, rows on f0348) |
| `measured-lon` | columns measured; rows carried on the 54′ lattice | CK; CQ (its top edge is measured, the rows below its top row aren't seen) |
| `read` | layout read on a small-scale ("Klein") frame, edges carried on the measured lattice | the blocks of CH, CJ and CN beyond f0200 |
| `assumed` | placed as a regular block, not seen | none: f0074 and f0091 show the CK and CO blocks once assumed |

**Probable.** That the fourth digit is keypad-numbered like the first three: the chart draws those cells but doesn't
number them, and the numbering comes from the published definition (Schmidt; navalgrid.com). That the lattice holds
west of about 3°20′E, where CH 1, 2, 4, 5, 7 and 8 are computed out to 4°18′W without a graticule to test them.

**Open.** CK's rows north of 39°48′N; the outline of CH's southern edge and of DJ; CL, CM and CQ below its top row;
the squares north of 45°36′N, where the columns are 10′ wide and the decoder holds nothing; the partial jump line at
34°N that Schmidt mentions. Section 6 lists them with where to look.

## 4. Accuracy

A four-digit cell is about 6 nm. The lattice is measured to under 1′ rms on each sheet; against places named in the
war diary the decoder is right to 2.4 nm where the diary gives a distance and the place is at sea, and to 11-49 nm
where it gives only a description.

### The measurement on f0200 (1890 G)

- **The margin fit.** The scale bars' 10′ edges were located by image analysis on the full-resolution frame (9680 ×
  7088 px).
  - A single linear fit to the bottom scale (3°20′-12°50′E) gives **1.8′ rms and 3.6′ at worst**, so the whole sheet
    fails the 2′ test. The cause is a fold near 5°E, where about 6′ of the scale is lost in the film.
  - East of the fold (6°-12°50′E), the fit is **0.8′ rms, 2.0′ at worst**.
  - The right-hand latitude scale gives **1.6′ rms in Mercator minutes, 4.1′ at worst**. The paper is curled and
    taped at about 36°N.
  - So no single sheet-wide affine was used. Each grid line was read **against the scale beside it**, by linear
    interpolation between the nearest bar edges. Fold and curl affect the grid and the scale alike.
- **The lattice.**
  - 45 vertical grid lines at the bottom edge (6°30′-12°45′E) lie on 6°30′ + k·8′, with a mean offset of −0.5′ and
    **0.65′ rms (1.3′ max)**.
  - 47 horizontal lines at the right edge (33°40′-39°00′N) lie on multiples of 6′, at **0.38′ rms (0.74′ max)**.
  - The edges in `squares.csv` are those **snapped** values (whole 6′ and 8′ steps), not the raw measurements.
  - The heavy lines confirm the block edges: 6°30′E (CH|CJ, CH|CN), 10°06′E (left edge of CN 21), and 37°30′N (top
    of CN 2).
- **Beyond f0200 the edges are extrapolated.** The block layout was read on the Klein frames, and the edges were
  carried on the measured lattice: `method` = `read` in `squares.csv`. A block not seen at all would be
  placed as a regular block, `method` = `assumed`; none is left, since f0074 and f0091 show the CK and CO blocks.
  Not tested against a graticule:
  - CK's rows north of 39°48′N (its top at 45°36′N, where the 10′ columns begin): the rows east of 13°E are
    measured on f0348 from 28°44′ to 39°48′N (below), but no sheet with a latitude scale beside CK 1-6 has been found;
  - that it holds west of about 3°20′E (CH 1, 2, 4, 5, 7 and 8 are computed out to 4°18′W);
  - the partial jump line at 34°N that Schmidt mentions. The 8′ spacing was measured at about 34°N on f0200 between
    3°20′ and 12°50′E, so if the jump exists it lies elsewhere.

### The second sheet (1892 G, f0074 and f0091)

Measured the same way as f0200, on the full-resolution frames (9696 × 7088 and 9680 × 7072 px): the 10′
bars of the longitude scale located by image analysis, each bar's minutes counted from the printed degree labels,
and each grid line read against the scale by interpolation between bar edges. Both frames are tilted by 1-2° and
curled, so each line's own slope was measured (between two bands 300 px apart) and the line extended along it to
the scale. Only longitudes could be measured: neither frame shows a latitude scale.

- **CO and CP (f0091, at about 30°-35°N).** 143 vertical lines from 17°18′ to about 37°40′E lie on 17°18′ + k·8′
  (the same lattice as f0200's 6°30′ + k·8′): mean −0.3′, **0.60′ rms, 1.5′ max**. Left out: 23°13′-23°45′, where the
  scale's bars are damaged (+3′ there), and east of 37°40′, where the scale has a gap from 38°10′ to 40°20′ (−2′ to
  −4′). The heavy block edges, each checked on a crop: CN|CO **17°18.8′**, CO 1|2 20°52.9′, CO 2|3 24°30.2′, CO|CP
  **28°06.6′**, CP 7|8 about 31°42′, CP 8|9 35°18′ (35°17.8′-35°19.8′ as the slope is taken), CP's east edge
  38°52′ (in the scale's gap).
- **CK (f0074, at about 45°N, so north of 40°15′N).** Lines measured just below CK's top edge and extended about
  1550 px up to the top scale: 44 lines from 17°10′ to 23°00′E on the 8′ lattice at **1.0′ rms (3.3′ max)**, 73 lines
  to 28°E at 1.4′ rms; the longer extension and the sheet join at 28° make this sheet looser than f0091. Block edges:
  CJ|CK 17°20.5′, CK 1|2 20°55.6′, CK 2|3 **24°29.9′**. CK's east edge lies on the sheet join and was not measured.
- **BH and BJ (f0074, north of 45°36′N).** The lines fall on whole 10′: about 80% of the detected lines within 1.5′
  of a multiple of 10′ (rms 0.8′-1.1′ in four stretches from 14°20′ to 34°30′E); the rest are numerals and coast
  picked up as lines.
- **So the 8′ column width holds from 6°30′ to about 38°E south of 45°36′N**, on two sheets, and changes to 10′ at
  45°36′. The edges in `squares.csv` for CK, CO, CP and CQ are snapped to the lattice; `method` = `measured-lon`
  marks a block whose columns were measured but whose rows are carried on the 54′ lattice.

### The rows east of 13°E (1892 G, f0348)

The 1892 G sheet's east end (f0348, 9696 × 7088 px) shows its right-hand margin: a latitude
scale from 28° to 40°N beside the land east of CP (Syria, Iraq), about 1,100 px east of CP's east edge (38°54′E).

- **The method.** The 10′ bars of the scale were located by image analysis, following the scale's border line down
  the frame. Each bar edge was given its minutes from the printed labels (36° read on a crop; the rest by a Mercator
  fit to the unbroken run of bars, rounded to 10′; 4 of 46 edges, at gaps in the bars, dropped). Each row line was
  found in two bands 500 px apart inside CP 3, 6 and 9, extended along its own slope to the scale, and read against
  it by interpolation between bar edges in Mercator ordinate.
- **The rows lie on the same lattice as f0200's.** 99 row lines from 29°24′ to 39°48′N fall on whole 6′ at **mean
  −0.1′, 0.56′ rms, 1.8′ max**. A free stretch doesn't improve the fit (factor 0.9985). The 8 lines south of 29°24′
  (to 28°44′N, CQ's top row) read +2.3′, where the scale runs into a fold near the sheet's corner.
- **The large-square rows break where the decoder puts them.** The two heaviest lines are at **37°30′N (+0.9′)** and
  **29°24′N (+0.9′)**: CO's and CP's top and bottom edges (and CQ's top). The lines of the third digit (every 18′)
  are drawn heavier than the rest (mean line darkness 151 against 113), and they fall on whole multiples of 18′. So the
  two-digit squares sit on 36′ (mod 54′), the same phase as f0200 (inference from the line weights; the dashed
  block edges at 34°48′ and 32°06′ were not picked up).
- **f0335 is a warning.** On the same view filmed for an earlier chart (f0335), the margin is curled and wavy: the
  rows read against it drift by up to ±3′ (2.2′ rms) and the scale itself departs from a Mercator fit by up to 4′ at
  its ends. A curled margin can't test the rows to better than half a cell; f0348's flat margin can.
- **What this covers.** The rows were measured at 38°-39°E. They run straight across the sheet from CP into CO
  (f0091), so `squares.csv` marks CO 1-9 and CP 1-9 `measured` in both directions; CQ keeps `measured-lon` (its
  top edge is measured, the rows below its top row aren't seen). The band 37°30′-39°48′N is CK 7-9's band too, but it
  was measured in CM 9, east of CK, so CK stays `measured-lon`.

### The anchors (`check`)

| id | code | as written | error to the stated place |
|---|---|---|---|
| N1 | CN 3282 | "15 miles southeast of Syracuse" (`skl:47/p297`) | **2.4 nm** |
| N2 | CO 5721 | "60 miles west of Derna" (`skl:50/p84`) | **11.7 nm** (decoded 32°57′N 21°22′E; the stated place is 32°46′N 21°27′E) |
| N3 | CK 7281 | "south of the Straits of Otranto" (`skl:51/p416`) | 42 nm south of the strait's middle: fits "south of" |
| N4 | CO 3381 | "off the southeast coast of Kos" (`skl:51/p263`) | 11 nm from Kardamena, mid-coast: decoded off Cape Agios Fokas, Kos's eastern point. Read on the page image (the OCR has "33^1") |
| N5 | CH 8376 | "off Algier" (`skl:55/p279`) | 49 nm west of Algiers (off Tipaza-Cherchell) |
| N6 | CJ 9472 | "at the northern coast of Sicily" (`skl:55/p397`) | 37 nm north of Cefalù |
| N7-N9 | CJ 5284, CJ 5941, CN 3254 | context only: no place stated | CJ 5284 decodes beside Civitavecchia, whose evacuation the same entry reports |

What the anchors show:
- The two anchors with a stated distance (N1, N2) are where the code has to be right. N1 confirms the lattice and the
  CN layout east of f0200 to within the cell. N2 confirms CO's position to about two cells. Its 11 nm offset is
  mostly north, and it is not the grid: CO's columns are 8′ (f0091) and its rows lie on the lattice at 33°N to
  within 0.4′ (f0348). The likelier reason is the stated place itself: a point 60 nm due west of Derna (32°46′N
  21°27′E) is on land, a few miles south of the Cyrenaican coast (which runs from about 32°54′N at Apollonia to 32°43′N
  at Tolmeita: approximate, not checked on a chart here), while CO 5721 is the cell just off that coast. So "60 miles
  west of Derna" reads as a description of the boat's stretch of coast, not a bearing.
- The loose ones (N3-N6) fall in the right sea and on the right side of the named place, but 11-49 nm from it. They
  test the block layout, not the edges.

## 5. Sources

- **The charts**: NARA T-1022 roll 2099 (naId 337684135), the Naval Staff U-boat section's Mediterranean operation
  charts, 1942-44, drawn on OKM Quadratkarten 1890 G, 1891 G and 1892 G and their "Klein" (small, 1:3,300,000) editions.
  Frames: https://catalog.archives.gov/id/337684135?objectPage=N. The frames used:
  - **f0200**: 1890 G "Mittelmeer westlicher Teil" at full scale (imprint "Oberkommando der Kriegsmarine Berlin
    1937", "Berichtigt 1940 V"), situation of 13 XI 42. It shows CH, CJ and CN with every two-digit square, a bottom
    scale at 2′ intervals from 2°30′ to 13°E and a right-hand scale from 34° to 40°N. **The lattice is measured here.**
  - **f0262**: a mosaic of 1890 G (Klein) and the Mittlerer Teil (Klein) sheets, with BF, BG, BH, CH, CJ and CK. Read
    here: the numbering of CH 1-9, all of CJ and CK's west column.
  - **f0314**: a mosaic strip (Klein) with CH, CJ, CN and CO, and CK's south row. Read here: CN 1-9, CO 1, 2, 4, 5,
    7 and 8, and the CJ 8/9 rows.
  - **f0318**: a Klein strip with CH, DJ and CN, and a bottom graticule. Read here: CN 4-9 complete, and CH's south
    edge.
  - **f0074** (section B): the top of 1892 G "... östlicher Teil und Schwarzes Meer" at full scale, with BH, BJ,
    CJ 3, CK, CL, CM; a top scale 13°30′-34°30′E (10′ bars, minute boxes; "Anschluß Nr. 1891 G" at 18°30′, and a
    sheet join at 28°E, labelled twice). No latitude scale on the frame. **CK's columns are measured here.**
  - **f0091** (section D): the bottom of 1892 G at full scale, with CN's east column, CO, CP and the top row of CQ; a
    bottom scale 17°-41°E (imprint "Herausgegeben vom Oberkommando der Kriegsmarine, Berlin 1937"; a sheet join at
    28°E). No latitude scale on the frame. **CO's and CP's columns are measured here.**
  - **f0348** (and f0335, f0352): the east end of the same 1892 G sheet at full scale, with CM 9, CP 3, 6, 9 and
    CQ 2, and the sheet's **right-hand latitude scale, 28° to 40°N, at 42°E** (10′ bars, minute boxes), a bottom
    scale 36°-42°E, and the imprints "Berichtigt 1943, I" and "Gedruckt im Oberkommando der Kriegsmarine". Charts of
    the series PG/33377 (frames 319-360; card on f0329). **CO's and CP's rows are measured on f0348.** f0335 is the
    same view with the margin curled (below); f0352's margin is folded and was not measured.
  - The measurements were made on the catalog's full-resolution frames (f0200, f0074, f0091, f0335, f0348, f0352);
    the working scripts are not in the kit.
- **The structure**: Ulrich Schmidt, *Die Marinequadratsysteme der deutschen Seestreitkräfte. Ein Werkstattbericht
  aus den Archiven* (Stand 19.09.2026), Zenodo, https://doi.org/10.5281/zenodo.22848807, CC BY-NC-ND 4.0. It is cited
  here, not copied: see it for the figures. The pages used:
  - p. 12-13: equal-arc rows, and cell widths reset at jump lines (Sprunglinien), including "eine partielle bei 34° N";
  - p. 22: the jump line at 45°36′ running east through the B and C squares; 1892 G still lacks CT and MA in December
    1942;
  - p. 23: the chart editions (1890 G and 1891 G, 1937), the coast-following edges of AO, BF, CH and CJ, and the OKM
    quotation above.
- **The method of a modern converter**: navalgrid.com, the "Naval Grid Calculator" method page (read from a PDF
  of the page saved 30 Oct 2026). It has 536 large squares, 465 of them regular and 71 irregular (rectangular,
  partial or polygonal), each stored as corner coordinates on the Mercator chart. Its Mediterranean data are not
  published on the page, so it could not be used as a check.
- **The anchors**: the Naval Staff's war diary in the Office of Naval Intelligence's translation
  (`skl:<volume>/p<printed page>`; `skl-ktb` and `skl-ktb-1944` in `records/SOURCES.yml`). The squares
  were found in the OCR, and the page numbers come from the printed footers. CO 5721's and CO 3381's pages were
  checked on the archive.org page images.
- The chart roll, Schmidt and navalgrid.com are `nara-t1022-2099`, `schmidt-marinequadrate` and `navalgrid` in
  `records/SOURCES.yml`.

## 6. Open questions

1. **Rows north of 40°N east of 13°E** (CK 1-6, and CK's top at 45°36′N). Measured south of 39°48′N (f0348, above).
   Searched on reduced views of frames 111-229 and 319-728 (every 20th row and column of each TIFF): 168-206 are 1890 G sections (CH, CJ, CN);
   111-167 are sections of Italy, the Adriatic and the Aegean, many filmed sideways (BH along one side), with f0133
   and f0160 the Black Sea cut-out of 1892 G (BJ, BK, CL); 207-229 and 319-360 are mosaics and 1892 G sections, f0335,
   f0348 and f0352 with the east margin; 361 onwards are the U-boat type papers of PG/33378, not charts (sampled every
   5th frame). Frames 1-73 (the Arctic charts, PG/33365) were not viewed. No full-scale 1891 G was seen. Still to
   check: the sideways sections (f0112, f0125 and the like) have a margin strip along one long side that may be 1892 G's
   west margin near 13°E with a latitude scale beside CK and BH: one of them at full resolution; then the U-boat track
   charts drawn "aufzulegen auf 1891 G / 1892 G" (rolls 2838, 2889-2892, 3074, 3375-3396).
2. **CH west of 3°20′E** against f0318's bottom graticule, which runs from about 8°W to 18°E. Also Spain
   (CH 1, 4, 7) and the CG/CH boundary at 4°18′W.
3. **What wasn't seen:** CL and CM (their irregular Black Sea and Aegean edges, on f0074 and f0091); CQ
   below its top row; BH and BJ with 10′ columns (the decoder would need a cell width per block); CT/MA (Schmidt:
   not on 1892 G in Dec 1942).
4. **Better anchors.** The diary OCR (vols. 47-55) has no further square given with a distance from a named
   place, and none beyond N3-N6 with a place in parentheses. Candidates: U-boat sinkings
   the diary gives by square (U-375 CH 8295, U-593 CH 9544, U-431 CH 7496, U-380 CJ 8687, U-616 CJ 9443, U-642 CJ
   8395, U-565 CJ 8845) against the Allied loss positions, and the U-boats' track charts (Wegekarten).
5. **The outline of CH's southern edge and of DJ** (f0318), if codes there turn up.
