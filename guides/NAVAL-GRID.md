# Kriegsmarine naval grid squares (Marinequadrate) in the Mediterranean

The German Naval Staff's war diary, the U-boat war diaries and the German signals give positions as naval grid
squares: "three destroyers heading north in CJ 9472 at the northern coast of Sicily" (`skl:55/p397`). The decoder is
`tools/naval_grid.py`. The blocks read so far are in `reference/naval-grid/squares.csv`, and the test positions are in
`reference/naval-grid/anchors.csv`. Started 30 Oct 2026 (lead L67).

```bash
python3 tools/naval_grid.py decode "CJ 9472" CN3282 "CJ 94"   # corners and centre of each cell
python3 tools/naval_grid.py check                              # anchors: decoded against the place named
python3 tools/naval_grid.py blocks                             # what is digitized
```

## How the grid works

- **The large square (Großquadrat) is two letters.** Its regular size is 486 nm on a side, so 8°06′ of latitude
  high. The OKM's own instruction (chart 3001, *Quadratkarten*, edition of 10.VIII.1944, quoted by Schmidt, p. 23)
  says: "Die Großquadrate haben im allgemeinen 486 sm Kantenlänge mit Ausnahmen derjeniger, die wegen der Anlehnung
  an den Verlauf der Küste in eine unregelmäßige Form gebracht werden mußten." The grid sits on a Mercator chart.
  Its rows are equal arcs of latitude. Its columns are a whole number of minutes of longitude wide, and that number
  is reset at "Sprunglinien" (Schmidt, pp. 12-13, 22).
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
  - CK and CO, east of 17°18′E, look regular on the frames seen.

## Sources

- **The charts**: NARA T-1022 roll 2099 (naId 337684135), the Naval Staff U-boat section's Mediterranean operation
  charts, 1942-44, drawn on OKM Quadratkarten 1890 G, 1891 G and 1892 G and their "Klein" (1:3,300,000) editions.
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
  - Saved at full resolution: `sources/t1022/2099/full/f0200.jpg`. The 2400-px views are in
    `sources/t1022/2099/`. The roll is described in `sources/drafts/naval-grid-med.md`.
- **The structure**: Ulrich Schmidt, *Die Marinequadratsysteme der deutschen Seestreitkräfte. Ein Werkstattbericht
  aus den Archiven* (Stand 19.09.2026), Zenodo, https://doi.org/10.5281/zenodo.22848807, CC BY-NC-ND 4.0. It is cited
  here, not copied: see it for the figures. The pages used:
  - p. 12-13: equal-arc rows, and cell widths reset at Sprunglinien, including "eine partielle bei 34° N";
  - p. 22: the Sprunglinie at 45°36′ running east through the B and C squares; 1892 G still lacks CT and MA in December
    1942;
  - p. 23: the chart editions (1890 G and 1891 G, 1937), the coast-following edges of AO, BF, CH and CJ, and the OKM
    quotation above.
- **The method of a modern converter**: navalgrid.com, the "Naval Grid Calculator" method page (Eric's PDF, 30 Oct
  2026, `sources/german-grids/`). It has 536 large squares, 465 of them regular and 71 irregular (rectangular,
  partial or polygonal), each stored as corner coordinates on the Mercator chart. Its Mediterranean data are not
  published on the page, so it could not be used as a check.
- **The anchors**: the Naval Staff's war diary in the ONI translation (`skl:<volume>/p<printed page>`). The squares
  were found in the OCR, and the page numbers come from the printed footers. CO 5721's page was checked on the
  archive.org page image.

## How well: the measurement (f0200)

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
  carried on the measured lattice: `method` = `read` in `squares.csv`. The CK and CO blocks not seen at all are
  placed as regular blocks: `method` = `assumed`. Not tested against a graticule:
  - that the 8′ column width holds north of 40°15′N and east of 12°50′E;
  - that it holds west of about 3°20′E (CH 1, 2, 4, 5, 7 and 8 are computed out to 4°18′W);
  - the partial jump line at 34°N that Schmidt mentions. The 8′ spacing was measured at about 34°N on f0200 between
    3°20′ and 12°50′E, so if the jump exists it lies elsewhere.

## How well: the anchors (`check`)

| id | code | as written | error to the stated place |
|---|---|---|---|
| N1 | CN 3282 | "15 miles southeast of Syracuse" (`skl:47/p297`) | **2.4 nm** |
| N2 | CO 5721 | "60 miles west of Derna" (`skl:50/p84`) | **11.7 nm** (decoded 32°57′N 21°22′E; the stated place is 32°46′N 21°27′E) |
| N3 | CK 7281 | "south of the Straits of Otranto" (`skl:51/p416`) | 42 nm south of the strait's middle: fits "south of" |
| N4 | CO 3341 | "off the southeast coast of Kos" (`skl:51/p263`) | 24 nm (decoded off Kalymnos/Leros); OCR "33^1", not read on the page |
| N5 | CH 8376 | "off Algier" (`skl:55/p279`) | 49 nm west of Algiers (off Tipaza-Cherchell) |
| N6 | CJ 9472 | "at the northern coast of Sicily" (`skl:55/p397`) | 37 nm north of Cefalù |
| N7-N9 | CJ 5284, CJ 5941, CN 3254 | context only: no place stated | CJ 5284 decodes beside Civitavecchia, whose evacuation the same entry reports |

What the anchors show:
- The two anchors with a stated distance (N1, N2) are where the code has to be right. N1 confirms the lattice and the
  CN layout east of f0200 to within the cell. N2 confirms CO's position to about two cells. Its 11 nm north of the
  stated place could be the boat's reckoning, the diarist's rounding ("60 miles"), or a CO column width other than 8′.
  The second can't be told from one anchor.
- The loose ones (N3-N6) fall in the right sea and on the right side of the named place, but 24-49 nm from it. They
  test the block layout, not the edges.

## Not done (where to resume)

1. **Measure a second sheet.** The 1891 G (Mittlerer Teil) and 1892 G full-scale sheets, with graticule, should
   confirm the 8′ width and the edges of CJ 3/6/9, CN 3/6/9, CK and CO. Frames 230-318 of roll 2099 are Klein
   mosaics; f0074 and f0091 are 1892 G at full scale. Measure them the same way, with scale bars located by image
   analysis and grid lines read against the scale beside them.
2. **Check CH west of 3°20′E** against f0318's bottom graticule, which runs from about 8°W to 18°E. Also check Spain
   (CH 1, 4, 7) and the CG/CH boundary at 4°18′W.
3. **Fill in what wasn't seen:** CK 2, 3, 5, 6, 8, 9 and CO 3, 6, 9. Add CM, CP, CQ, and CT/MA (Schmidt: not on
   1892 G in Dec 1942).
4. **Read N4's square on the page image** (`skl:51/p263`, CO 3341 or 3371?). Collect better anchors: U-boat sinkings
   the diary gives by square (U-375 CH 8295, U-593 CH 9544, U-431 CH 7496, U-380 CJ 8687, U-616 CJ 9443, U-642 CJ
   8395, U-565 CJ 8845) against the Allied loss positions, and the U-boat Wegekarten listed in
   `sources/drafts/naval-grid-med.md`.
5. **The outline of CH's southern edge and of DJ** (f0318), if codes there turn up.

## Proposed SOURCES entries

For the calling session to add to `records/SOURCES.yml`. The diary is already there (`skl-ktb`, `skl-ktb-1944`).
`reference/naval-grid/anchors.csv` cites it, so its `used_for` lines could add that file.

```yaml
nara-t1022-2099:
  title: Records of the German Navy, T-1022 roll 2099 (Naval Staff U-boat section, operation charts, Arctic and Mediterranean, 1942-44)
  by: Oberkommando der Kriegsmarine, Seekriegsleitung; filmed by the US Navy (ONI), 1946
  held: NARA, RG 242, series "Copies of Records of the German Navy" (naId 315246058); microfilm publication T1022
  id: NAID 337684135
  url: https://catalog.archives.gov/id/337684135
  rights: Public domain (captured records; US government microfilm)
  cite: t1022-2099/f<frame>, e.g. t1022-2099/f0200 (1890 G, Mittelmeer westlicher Teil, situation of 13 XI 42)
  match: '^t1022-2099/f(\d{4})$'
  link: https://catalog.archives.gov/id/337684135?objectPage={1}
  used_for: reference/naval-grid/squares.csv (the Mediterranean grid squares, measured and read), guides/NAVAL-GRID.md
  note: >-
    The frame is the catalog's object page (the TIFF's number, T1022-2099-0NNNN.tif). Operation charts drawn on OKM
    Quadratkarten 1890 G, 1891 G and 1892 G, full scale and "Klein" (1:3,300,000), filmed in lettered sections.
    Frame 729 is a PDF of the whole roll; its OCR is the only text the catalog holds.

schmidt-marinequadrate:
  title: Die Marinequadratsysteme der deutschen Seestreitkräfte. Ein Werkstattbericht aus den Archiven (Stand 19.09.2026)
  by: Ulrich Schmidt
  held: Zenodo
  id: doi:10.5281/zenodo.22848807
  url: https://doi.org/10.5281/zenodo.22848807
  rights: CC BY-NC-ND 4.0 (cite; don't copy the figures, whose rights lie with the archives named)
  cite: schmidt-mqs/p<page>, e.g. schmidt-mqs/p23
  match: '^schmidt-mqs/p(\d+)$'
  used_for: guides/NAVAL-GRID.md (the grid's structure, jump lines, the irregular CH and CJ, the OKM's instruction on chart 3001)
  note: >-
    Reconstructs the Kaiserliche Marine, Reichsmarine and Kriegsmarine grid systems from the charts in the
    Bundesarchiv (RM 6/KART) and NARA T-1022. Pages are the PDF's printed page numbers.

navalgrid:
  title: Naval Grid Calculator (method page)
  by: navalgrid.com
  held: navalgrid.com (website)
  url: https://navalgrid.com
  rights: Website; cited, not copied
  cite: navalgrid
  match: '^navalgrid$'
  used_for: guides/NAVAL-GRID.md (the count and kinds of large squares; corner-coordinate storage on the Mercator chart)
  note: >-
    Read from a PDF of the method page saved 30 Oct 2026 (the site's certificate failed to the fetch tool). Its
    Mediterranean square data are not published on the page.
```
