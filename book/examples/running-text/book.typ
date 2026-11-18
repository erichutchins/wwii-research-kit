// Running text on the magazine grid: two text columns and an outer note column, running heads and folios that
// alternate by side, numbered side notes made from the citations the components carry, a record quote, facsimiles
// with caption and credit. Filled from Company B, 313th Infantry's July 1944 in the kit's records (army/stations.csv,
// army/actions.csv, army/relations.csv) and the company's morning reports.
//   uv run wwii-book build examples/running-text/book.typ
#import "@local/wwii-book:0.1.0": *
#let wwii = init(assets: json("build/assets.json"), load: p => read(p, encoding: none))
#show: book.with(preset: "blurb-magazine")
#show: on-grid.with(sources: (
  hist313: [_History of the 313th Infantry in World War II_ (1947)],
  breakout: [Blumenson, _Breakout and Pursuit_ (1961), ch.],
  etoob-79ID: [_Order of Battle of the US Army, WWII: ETO_, 79th Infantry Division],
  ddbzp: [_Hamburger Tageblatt_, 12 July 1944],
  gallica: [_L'Ouest-Éclair_, 12 July 1944],
  lastampa: [_La Stampa_, 12 July 1944],
))

#let mr = "rg64-480601116"   // the company's morning reports, July 1944
#let jn = "rg64-478558151"   // and June

#part-title[The Cotentin, 1944]

#running-text(
  eyebrow: [Company B, 313th Infantry · 26 June to 11 July 1944],
  title: [Towards La Haye-du-Puits],
  standfirst: [A rifle company's fortnight, from the fall of Cherbourg to the high ground west of La Haye-du-Puits, as
    its morning reports give it day by day and as the regiment's history tells the two attacks between.],
)[
The 313th Infantry is listed first among the 79th Infantry Division's units,#note(cite: "etoob-79ID/p262") and Company B
one of the three rifle companies of its 1st Battalion. Each night the company's clerk typed a morning report: who had
joined and who had left, the strength, and, at the head of the form, where the company was. That heading is the
station, and it is all the company says of its own whereabouts. It is the spine of this chapter.

On 26 June the station was Cherbourg, the day the port fell.#note(cite: jn + "/p0425") The next day the company was at
La Glacerie, four miles south-west of a grid point on the French Lambert Zone I grid,#note(cite: jn + "/p0430")[The distance and bearing are
from the grid point, not from the hamlet; the position is made from both, and is a hamlet's, not a field's]
and on the 28th at Le Valdécie, inland on the road south.#note(cite: jn + "/p0433") The division had come under VII
Corps for the drive on the port. From 1 July it was under VIII Corps,#note(cite: "etoob-79ID/p262") and the company's stations turn south, through the hedgerow country towards La Haye-du-Puits.

== The march south

The reports for the first days of July read as a march. On the 2nd the station was Le Mesnil St Martin, at VT 0893;#note(cite: mr + "/p0009") on the 3rd, Barneville sur Mer, on the coast at VT 0395.#note(cite: mr + "/p0010") A
four-figure reference names a square of the grid a kilometre on a side, and the company is placed in that square, not
at a point within it. On the 4th the station was given as half a mile north of a grid point near Baudreville, on the eve of the attack south:

#record-quote(source: [Morning report, Co B, 313th Inf, 4 July 1944, station], cite: mr + "/p0012")[
  Baudreville, France \ 1/2 Mi N VT 1286 French Lambert Zone 1]

The clerk's form gives the place first, then the grid reference with its distance and bearing, then the grid it is
on. The distance and bearing run from the grid point, not from the village; where the two disagree, the village is
the clerk's nearest name and the grid point the more exact.

== The attack of 5 July

The regiment attacked at half past six on the morning of the 5th, in a column of battalions with the 1st leading,
toward a bridge south of Saint-Rémy-des-Landes that the history calls Concentration 55.#note(cite: "hist313/p81")
Company B was on the battalion's western flank:

#record-quote(source: [On 5 July 1944], cite: "hist313/p82")[
  The first attack was launched by the 1st Battalion, with A Company on the east and B Company on the west, attacking
  from a line of departure a hedgerow, which was just to the north of the creek. ... At that point they were met by a
  deadly concentration of heavy artillery ...]

Two attacks by the battalion were repulsed before nightfall, and the companies were withdrawn after dark. The history
says only that "Our losses had been extremely high".#note(cite: "hist313/p82") The Army's official history has the
regiment and the task force beside it driven several miles back.#note(cite: "breakout/4/p74") The history's account is
the regiment's, written after the war; the company's own report for the day gives its station and its men, not the
attack, and the ground of the attack is not given closer than the creek north of the bridge. The company is placed at
its station that day.

#across(at: bottom)[
  #(wwii.facsimile)(mr + "/p0014", crop: (0.08, 0.028, 0.86, 0.1), width: 95%, bare: true)
  #photo-caption(
    ours: [The heading of the company's morning report for 5 July 1944. The station is typed "2 Miles SW VO 1185": the
      clerk's VO for VT, which runs from this report to the 11th. Square O would put the company a hundred kilometres
      north, in the Channel; the figures fit square T, a kilometre or two from Saint-Rémy-des-Landes, and the company
      is placed at the village. The names below the heading are left out of the crop.],
    credit: [Facsimile], cite: mr + "/p0014")
]

The station that night was Saint-Rémy-des-Landes, two miles south-west of a grid point,#note(cite: mr + "/p0014")[Typed "VO 1185" for VT
1185; placed at the village] and it is the first of the reports to carry a slip the reader has to
catch. From the 5th the clerk types the square as VO where the figures belong to VT. Read as typed, the reference is
in the sea; read as VT, it is a kilometre or two from the village the station names. The kit's records keep the
reference as typed and place the company at the village, with the reason in the row's note. Nothing is overwritten:
the reading and the correction stand side by side, and either can be checked against the scan.

== Hedgerows

From the 7th the station was La Gosselinerie, a quarter of a mile north-west of VT 1584, and it stayed there through
the 10th.#note(cite: mr + "/p0018")[Typed "VO 1584"; placed at VT 1584 and a quarter mile north-west. Through 10 July]
Four days at one station is the longest stay in these reports. The reports do not say why the company held there; the
regimental history moves to the next attack. What the reports do give, day by day, is the company's strength and the
men it lost and gained, and those are the record's own count, not a reckoning made from the history.

On the 11th the regiment attacked again:

#record-quote(source: [On 11 July 1944], cite: "hist313/p83")[
  At 6:00 A.M. on that date the Regiment continued the attack to the south, again passing through the 315th Infantry.
  ... The attack was launched in a column of battalions, in order: 2d, 1st, 3d.]

The regiment's left boundary was the road from La Haye-du-Puits to Lessay; it crossed the stream and came up near
Angoville.#note(cite: "hist313/p83") Company B's station that night was La Surellerie, a quarter of a mile north-west
of VT 1683, about a kilometre and a half west of La Haye-du-Puits.#note(cite: mr + "/p0027")[Typed "VO 1683"; placed at VT 1683 and a
quarter mile north-west]

#across(at: top)[
  #grid(columns: (1fr, 1fr), column-gutter: 12pt,
    (wwii.facsimile)(mr + "/p0028", crop: (0.09, 0.04, 0.85, 0.095), bare: true),
    (wwii.facsimile)(mr + "/p0028", crop: (0.09, 0.55, 0.85, 0.21), bare: true))
  #photo-caption(
    ours: [The morning report for 11 July 1944, its heading (left) and its strength (right): five first lieutenants
      present, one absent and two second lieutenants absent; 130 enlisted men present for duty and 75 absent, of 205
      assigned. The record of events between them reads, in full, "4 EM Wounded". The ration section below is dated
      18 July.],
    credit: [Facsimile], cite: mr + "/p0028")
]

== The company's record of the day

The company's record of events for the 11th is three words and a figure:

#record-quote(source: [Morning report, Co B, 313th Inf, 11 July 1944, record of events], cite: mr + "/p0028")[
  4 EM Wounded]

The four men went to the 304th Medical Battalion's clearing station, and the first page of the same report lists them by name.#note(cite: mr + "/p0027") A fifth man wounded on the 11th was not entered until the report of 28 July.#note(cite: mr + "/p0058") A morning report is a ledger: an entry is made on the day the clerk learns of it, and the
date it gives for the event may be days earlier than the report it is typed on. A count of the wounded for a day is
therefore a count of the entries for that day, and it says so.

The strength section of the same report gives 130 enlisted men present for duty and 75 absent, of 205 assigned.#note(cite: mr + "/p0028")[As read from the scan; the strength is the report's own count] The absent are not named
there; the section gives only the totals. These are the record's figures, and they stand as typed.

== The other side

The German side of the same days survives here only as the newspapers printed the Wehrmacht's report. Of the fighting
on the 11th, the report of 12 July says the defence went on "im Abschnitt La Haye du Puits" without the enemy having
yet gained any real success.#note(cite: "ddbzp:O3SIITUMTQ4YJGXDOZ2EZUBUXJ7GSX2F/p1") A French paper of the same day,
under a Berlin dateline of the 11th, has the right wing of the First American Army still held near Montgardon.#note(cite: "gallica:bpt6k663315n/f1") An Italian paper has the Germans retake La Haye du Puits "per la quarta volta",
for the fourth time,#note(cite: "lastampa:1944-07-12/p1") which the American official history does not record.#note(cite: "breakout/7/p125") None of the three names a German unit opposite the company, and none is a record of
the company's ground: they are what the papers' readers were told of the same days.

== What the records hold

For these sixteen days the company's own record is a run of stations, a strength each day, and the men who came and
went. The attacks are the regiment's history's, written after the war by the regiment's officers, and the army's
history's; the company's reports say nothing of them beyond the wounded. Where the records place the company, the
place is a grid square or a hamlet, and the precision is the record's: a kilometre square where the clerk gave four
figures, a village where his grid letter was wrong. Where they do not, as on the ground of the attack of the 5th, the
company is placed at its station and the placing is said to be assumed.

The figures and the facsimiles in this chapter are the records'; the arrangement is drawn for this research. Every
note resolves to the page it was read from, and every page can be opened in the National Archives' catalogue at the
page the note gives.

#pagebreak()
#across(at: top)[
  #set par(justify: false, first-line-indent: 0pt)
  #set text(size: 7.8pt, top-edge: 6.1pt, bottom-edge: -1.7pt)
  #let st(date, typed-station, placed, how, prec, cite, n: none) = (date, typed(typed-station), placed, basis(how),
    precision(prec), if n == none { note(cite: cite) } else { note(cite: cite, n) })
  #block(below: 8pt, eyebrow[The company's stations as typed, 26 June to 11 July 1944])
  #table(columns: (38pt, 1fr, 92pt, auto, auto, 10pt), stroke: none, inset: (x: 3pt, y: 4.2pt),
    align: (left, left, left, left, left, left),
    table.hline(stroke: 0.6pt + tokens.ink),
    table.header(..([Date], [Station, as typed], [Placed at], [How we know], [How precisely], []).map(h =>
      text(font: tokens.display, size: 7pt, weight: "semibold", tracking: 0.08em, fill: tokens.muted, upper(h)))),
    table.hline(stroke: 0.4pt + tokens.rule),
    ..st([26 June], [Cherbourg, France], [Cherbourg], "reported", "town", jn + "/p0425"),
    ..st([27 June], [La Glacerie, France / 4 Miles SW VO 1819 French Lambert Zone 1], [La Glacerie], "derived",
      "hamlet", jn + "/p0430", n: [Made from the hamlet and the grid point together]),
    ..st([28 June], [Le Valdecie, France / 1 Mile S VT 1099 French Lambert Zone 1], [VT 1099], "derived",
      "grid square", jn + "/p0433", n: [The mile south of the grid point is not applied]),
    ..st([2 July], [Le Mesnil St Martin, France / VT 0893 French Lambert Zone 1], [VT 0893], "reported",
      "grid square", mr + "/p0009"),
    ..st([3 July], [Barneville Sur Mer, France / VT 0395 French Lambert Zone 1], [VT 0395], "reported",
      "grid square", mr + "/p0010"),
    ..st([4 July], [Baudreville, France / 1/2 Mi N VT 1286 French Lambert Zone 1], [Baudreville], "reported",
      "village", mr + "/p0012"),
    ..st([5 July], [St Remy des Landes, France / 2 Miles SW VO 1185 French Lambert Zone 1], [Saint-Rémy-des-Landes],
      "inferred", "village", mr + "/p0014", n: [VO read as VT; placed at the village]),
    ..st([7 July], [La Gosselinerie, France / 1/4 Mile NW VO 1584 French Lambert Zone 1], [VT 1584, ¼ mile NW],
      "inferred", "grid square", mr + "/p0018", n: [VO read as VT. Through 10 July]),
    ..st([11 July], [La Surellerie, France / 1/4 Mile NW VO 1683 French Lambert Zone 1], [VT 1683, ¼ mile NW],
      "inferred", "grid square", mr + "/p0027", n: [VO read as VT]),
    table.hline(stroke: 0.6pt + tokens.ink),
  )
  #block(above: 6pt, text(size: 7pt, fill: tokens.muted)[Table drawn for this research from the kit's records
    (army/stations.csv), each row read from the morning report its note names. _Reported_: as the record gives it;
    _derived_: worked out from the record's own figures; _inferred_: a step beyond them (the grid letter read as
    another). A station is placed only on the days the company reported it; nothing is drawn between them.])
]

== The ledger of stations

The table above sets the company's stations side by side as the clerk typed them, with where the kit places each and
on what footing. Read down, it is the chapter in brief: a port, two hamlets inland, four grid squares and a village on
the march south, and three stations whose grid letter had to be read as another before they could be placed at all.

Its notes continue the chapter's numbering, and its last column is the record's page. A station is not a track: the
company was somewhere between one report's station and the next, and the records do not say where, so nothing joins
them here or on a map.
]
