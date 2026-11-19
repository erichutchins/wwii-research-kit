// The grid section: how a unit's typed grid reference finds its place, from the grid's lettered 100 km squares to the
// hundred metres of a six-figure reference. Two worked cases from the kit's records, each a unit's own morning report
// read down onto the map it worked from: Battery C, 62nd CA (AA) at Lake Bizerte (North West Africa grid, July 1943)
// and Company B, 313th Infantry at La Haye-du-Puits (French Lambert Zone I, July 1944). The period instructions are
// the ones a 1942 Army Map Service sheet prints in its margin. Figures: gridref.py, book/grids/cases.yml.
//   uv run wwii-book build examples/grid-references/book.typ
#import "@local/wwii-book:0.1.0": *
#let wwii = init(assets: json("build/assets.json"), load: p => read(p, encoding: none))
#show: book.with(preset: "blurb-magazine")
#show: on-grid.with(sources: (
  princeton-amsalger: [Army Map Service, _Alger and vicinity_, sheet 3 of 7 (1942)],
  gsgs-tunisia-50k: [G.S.G.S. 4225, _Tunisia 1:50,000_ (1942), sheet],
  ok45th: [45th Infantry Division, G-2 Periodic Report No. 219],
  grid: [Position computed from the reference (the kit's tools/grid_ref.py)],
))

#let bz = "rg64-427182819"   // Battery C, 62nd CA (AA): July 1943
#let mr = "rg64-480601116"   // Company B, 313th Infantry: July 1944

#part-title[Reading the records]

#running-text(
  eyebrow: [North Africa and Europe · 1942 to 1945],
  title: [The grid],
  standfirst: [Where a unit's clerk could, he gave the station as a grid reference: a letter and four or six figures
    that a reader with the right map could put to within a kilometre, or a hundred metres. This is how those figures
    find their place.],
)[
Every Allied map sheet of North Africa and Europe was printed with a military grid: straight lines a kilometre apart,
numbered in the margins, drawn not on the latitude and longitude but on the map's own projection, so that every
square is square and every distance can be counted off in kilometres. Each grid belongs to a zone. Inside it the
lines are numbered from a false origin far to the south-west, so that every figure is positive and grows to the east
and the north.

The figures repeat every 100 kilometres. To say which hundred, each 100 km square carries a letter, A to Z without I,
five to a row from the north-west; on some grids a second letter names the 500 km square the hundred lie in. A full
reference is therefore a letter, then the figures east, then the figures north: read right, then up.

The sheets themselves say how. An Army Map Service sheet of Algiers, printed in 1942, sets it out in its margin, with
a worked example: the point Mon Rouge is in square H; its square's west edge is the line 74, and the point three
tenths east of it; the south edge is 07, and the point two tenths north. Its reference is H743072, "To nearest 100
metres".#note(cite: "princeton-amsalger")[The sheet prints the grid's definition beside it: "N. W. Africa Zone Grid
(Purple)", Lambert Conical Orthomorphic, Clarke 1880, origin 34° N on the Greenwich meridian, false origin 1,000,000
m east and 500,000 m north]

== The grids the records use

The Army records in this kit give references on six grids. In Tunisia and Algeria in 1942 and 1943 it was the British
North West Africa grid, printed in purple on the War Office's Tunisia sheets;#note(cite: "gsgs-tunisia-50k/6") in Sicily
and Italy the two Italian zones; in Normandy in the summer of 1944 the French Lambert Zone I, which the clerks of the
79th Infantry Division typed by name; and from the autumn of 1944 across eastern France and into Germany the Lambert
grid the Allies called Nord de Guerre, on which the 45th Infantry Division's intelligence officer put two crashed
bombers near Neuburg an der Donau in April 1945, in square T.#note(cite: "ok45th-5343/p06")

The map that follows draws three of them with their lettered squares, as the kit's tools letter them, over the ground
the records' references fall on, and every station in the records that a unit gave by grid. On the North West Africa
grid the letters repeat in every 500 km block, and no record read prefixes the block: a reference is put in the block
nearest the town the same report names. On Lambert Zone I the 500 km square is V, and the clerks typed it.

== Two references, read down

Battery C, 62nd Coast Artillery (Antiaircraft), gave its station from 4 to 7 July 1943 as "J 775914 Sheet 6,
1:50,000 Br N.W.A. Grid": square J, 77.5 kilometres east, 91.4 north, on the sheet of Djebel Ichkeul.#note(cite: bz + "/p0546")[The
report of 5 July. On the 4th's, a serial number stamped over the station covers the letter] Read
down, it falls on the south-east shore of Lake Bizerte, about eight kilometres east of Ferryville, where the battery's
June report had put it "on east shore of Lake Bizerte".#note(cite: "grid")[The square letter is the nearest J to
Ferryville; one J further would be 500 km away]

Company B, 313th Infantry, gave its station on 11 July 1944 as "1/4 Mile NW VO 1683 French Lambert Zone 1".#note(cite: mr + "/p0027")
Four figures name a kilometre square, not a point. And here the letter is wrong: from 5 July the clerk typed square O
where the figures belong to square T, a hundred kilometres to the south. Read as typed, the company is in the
Channel; read as VT, it is a kilometre and a half west of La Haye-du-Puits, where the regiment's attack of the 11th
went in.#note(cite: mr + "/p0014")[The kit keeps the reference as typed and places the company at VT 1683, with the
reason in the row's note] A letter is a hundred kilometres. A wrong letter is easy to catch, because the figures
still fit the town; a wrong figure is not.
]

#pagebreak()
#across-all(at: top)[
  #(wwii.grid-figure)(view: "zones", width: 7.2in)
  #photo-caption(
    ours: [The grids the records use, with their 100 km squares lettered as the kit's tools letter them: the North
      West Africa grid (purple; its letters repeat in every 500 km block, the heavy lines), the French Lambert Zone I
      (blue; the 500 km square V) and the Nord de Guerre (green; one block). Each is drawn over the ground the
      records' references fall on, not the zone's official limits. A dot is a station a unit gave by grid; the two
      rings are the references read down on the next pages, and the dashed ring is the second one as its clerk typed
      it.],
    credit: [Drawn for this book from the kit's grid definitions (tools/grid_ref.py)])
]

#pagebreak()
#across-all(at: top)[
  #(wwii.facsimile)(bz + "/p0546", crop: (0.1, 0.035, 0.85, 0.085), width: 4.6in, bare: true)
  #v(6pt)
  #(wwii.grid-figure)(view: "ladder", case: "bizerte", width: 6.7in)
  #photo-caption(
    ours: [Battery C, 62nd CA (AA), 5 July 1943: its morning report's heading, and its station read down from the
      100 km square J to the hundred metres the six figures name. Panels 1 and 2 draw the coast in the grid's own
      projection; panels 3 and 4 the War Office's own sheet, resampled into the grid by its purple lines, and the
      kit's computed grid lies on the sheet's printed one.],
    credit: [Facsimile; G.S.G.S. 4225 sheet 6, University of Texas Libraries], cite: bz + "/p0546")
]

#pagebreak()
#across-all(at: top)[
  #(wwii.facsimile)(mr + "/p0027", crop: (0.08, 0.035, 0.86, 0.1), width: 4.6in, bare: true)
  #v(6pt)
  #(wwii.grid-figure)(view: "ladder", case: "la-haye", width: 5.9in)
  #photo-caption(
    ours: [Company B, 313th Infantry, 11 July 1944: "VO 1683" as typed, read as VT. Panel 1 hatches square O, where
      the letter as typed would put the company. Four figures name the whole kilometre square. In panels 3 and 4 the
      nearest map online, IGN's 1950 series, resampled into the 1944 grid (blue); it prints a later kilometre grid of
      its own in magenta. The names below the report's heading are left out of the crop.],
    credit: [Facsimile; IGN SCAN 50 Historique], cite: mr + "/p0027")
]

#pagebreak()
#across-all(at: top)[
  #(wwii.picture)("maps/princeton/gridbox.jpg", width: 85%)
  #photo-caption(
    original: [TO GIVE A GRID REFERENCE ON THIS SHEET],
    ours: [The instructions in the margin of an Army Map Service sheet of Algiers, 1942, with their worked example:
      Mon Rouge, square H, 74 and three tenths east, 07 and two tenths north: H743072, to the nearest 100 metres.
      The blue figures are printed so on the sheet.],
    credit: [Army Map Service, Alger and vicinity, sheet 3 of 7 (1942); Princeton University Library],
    cite: "princeton-amsalger")
]
