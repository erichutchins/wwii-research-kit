// The wwii-book Typst package: the page, the components, and the request functions.
//
// A request function (facsimile, records, qr-tag) writes a `<wwii-request>` metadata entry and draws a placeholder
// until the Python build has prepared it into the book's build/ folder; then it draws the real thing. Use:
//
//   #import "@local/wwii-book:0.1.0": *
//   #let wwii = init(assets: json("build/assets.json"), load: p => read(p, encoding: none))
//   #show: book
//
// The loader is a closure written in the book's own file, so it reads paths relative to the book, not to this package.

#let tokens = (
  ink: rgb("#1c221d"), muted: rgb("#5d675b"), rule: rgb("#c4cbbf"), accent: rgb("#a3241b"),
  other: rgb("#e4e7e9"), other-ink: rgb("#4d5963"), paper: rgb("#fbfaf6"), band: rgb("#171c18"), band-ink: rgb("#ecede6"),
  // Typst files Barlow Condensed under the family "Barlow", condensed
  display: ("Barlow", "Barlow Condensed", "Arial Narrow"),
  body: ("Source Serif 4", "Georgia"),
  typed: ("Courier Prime", "Courier New"),
)

// The man's name and the book's title, for the running heads; set by `book`.
#let _book-meta = state("wwii-book-meta", (name: "", title: ""))

// A 7 × 10 in page (trim; bleed is added at export), inside margin for the binding, running heads alternating by
// side (the book's man on the left, the chapter on the right), none on a page that opens a chapter, folios outside.
#let book(name: "", title: "", trim: (width: 7in, height: 10in), body) = {
  _book-meta.update((name: name, title: title))
  set page(width: trim.width, height: trim.height, binding: left,
           margin: (inside: 0.85in, outside: 0.7in, top: 0.85in, bottom: 0.9in),
    header: context {
      let p = here().page()
      let openers = query(heading.where(level: 1)).filter(h => h.location().page() == p)
      if openers.len() > 0 { return }
      let before = query(heading.where(level: 1).before(here()))
      let chapter = if before.len() > 0 { before.last().body } else { [] }
      set text(font: tokens.display, size: 7.5pt, tracking: 0.14em, fill: tokens.muted)
      if calc.even(p) { upper(_book-meta.get().name) } else { align(right, upper(chapter)) }
    },
    footer: context {
      let p = here().page()
      set text(font: tokens.display, size: 8.5pt, fill: tokens.muted)
      align(if calc.even(p) { left } else { right }, str(p))
    })
  set text(font: tokens.body, size: 10.2pt, fill: tokens.ink, lang: "en", region: "gb", hyphenate: true)
  set par(justify: true, leading: 0.68em, spacing: 0.68em, first-line-indent: (amount: 1.1em, all: false))
  show heading: set text(font: tokens.display, weight: "bold")
  show heading.where(level: 2): it => block(above: 1.5em, below: 0.7em,
    text(size: 10.5pt, weight: "semibold", tracking: 0.12em, upper(it.body)))
  set footnote.entry(separator: line(length: 25%, stroke: 0.5pt + tokens.rule), gap: 0.4em)
  show footnote.entry: set text(size: 7.6pt)
  show figure.caption: set text(size: 8pt)
  show figure.caption: set align(left)
  set figure(gap: 0.6em, supplement: none, numbering: none)
  body
}

#let eyebrow(body) = text(font: tokens.display, size: 8pt, weight: "semibold", tracking: 0.12em, fill: tokens.muted, upper(body))

#let typed(body) = text(font: tokens.typed, size: 0.92em, body)

// The record's words as typed, with where they come from.
#let record-quote(body, cite: none, source: none) = block(inset: (left: 11pt, y: 2pt), stroke: (left: 1.2pt + tokens.accent),
                                                          above: 1.1em, below: 1.1em)[
  #set par(justify: false, first-line-indent: 0pt, leading: 0.55em)
  #typed(body)
  #if source != none or cite != none {
    linebreak()
    text(size: 7.5pt, fill: tokens.muted)[#source#if source != none and cite != none [ · ]#if cite != none { raw(cite) }]
  }
]

#let _pending(label, height: 1.4in) = block(width: 100%, height: height, inset: 8pt,
  stroke: (paint: tokens.muted, thickness: 0.6pt, dash: "dashed"),
  align(center + horizon, text(size: 8pt, fill: tokens.muted)[pending: #raw(label)]))

#let _request(kind, key, args) = [#metadata((kind: kind, key: key, ..args)) <wwii-request>]
#let _warn(message) = [#metadata((message: message)) <wwii-warning>]

// The numbered marks of an engagement figure: number, GMT, the time as the record types it, what, and the citation;
// then the unnumbered marks' citations in groups, and which clock each record kept.
#let mark-key(a) = {
  set text(size: 7pt)
  set par(justify: false)
  table(
    columns: (auto, auto, auto, 1fr, auto),
    stroke: (x, y) => if y == 0 { (bottom: 0.7pt + tokens.ink) } else { (bottom: 0.25pt + tokens.rule) },
    inset: (x: 3pt, y: 2.5pt),
    table.header(..("", "GMT", "As typed", "What", "Source").map(h => text(font: tokens.display, weight: "semibold", upper(h)))),
    ..a.marks.map(m => (
      text(weight: "bold")[#m.n], m.gmt, text(font: tokens.typed, m.local),
      [#m.what#if m.note != "" [ \ #text(size: 6.3pt, fill: tokens.muted, style: "italic", m.note)]],
      text(font: tokens.typed, size: 6.5pt, fill: tokens.muted, m.cite),
    )).flatten(),
  )
  text(size: 6.5pt, fill: tokens.muted)[#a.zones. Unnumbered marks: #a.others.join("; ").]
}

// Who's who of the divisions on a map: the number as drawn, and its name worked out from the symbol.
#let unit-key(units) = {
  set text(size: 7pt)
  set par(justify: false, first-line-indent: 0pt, leading: 0.45em)
  let line(u) = [#text(font: tokens.display, weight: "bold", fill: if u.highlight { tokens.accent } else { tokens.ink }, u.number) #u.name]
  let ours = units.filter(u => u.side != "German")
  let theirs = units.filter(u => u.side == "German")
  block(above: 0.5em, below: 0.9em, grid(columns: (1fr, 1fr), gutter: 12pt,
    [#text(font: tokens.display, size: 6.5pt, weight: "semibold", tracking: 0.1em, fill: tokens.muted, upper[American]) \
     #ours.map(line).join([ · ])],
    [#text(font: tokens.display, size: 6.5pt, weight: "semibold", tracking: 0.1em, fill: tokens.muted, upper[German]) \
     #theirs.map(line).join([ · ])]))
}

#let init(assets: (:), load: none) = {
  let get(key) = assets.at(key, default: none)

  // An archive page by its citation, cropped to fractions (x, y, width, height) of the page after turning it
  // `rotate` degrees counter-clockwise. Placed at its own size at 300 dpi, or the column's width if that is
  // narrower; a `width` that pushes it below 300 dpi is reported as a warning.
  let facsimile(cite, crop: none, rotate: 0, width: auto, caption: none, highlight: (), bare: false) = {
    let key = cite + (if crop != none { "@" + crop.map(str).join(",") } else { "" }) + (if rotate != 0 { "@r" + str(rotate) } else { "" })
    _request("facsimile", key, (cite: cite, crop: crop, rotate: rotate))
    let a = get(key)
    let cap = [#caption#if caption != none [. ]#text(fill: tokens.muted)[#if a != none { a.credit } else { cite }]]
    if a == none {
      figure(_pending(cite), caption: cap, kind: image)
    } else {
      layout(size => {
        let natural = a.px.at(0) / 300 * 1in
        let w = if width == auto { calc.min(natural, size.width) } else if type(width) == ratio { size.width * width } else { width }
        let dpi = a.px.at(0) / (w / 1in)
        if dpi < 299 { _warn(cite + ": placed at " + str(calc.round(dpi)) + " dpi") }
        let h = w * a.px.at(1) / a.px.at(0)
        let img = box(width: w, height: h, {
          image(load(a.path), width: w)
          for hl in highlight {
            place(top + left, dx: hl.at(0) * w, dy: hl.at(1) * h, rect(width: hl.at(2) * w, height: hl.at(3) * h,
              stroke: 1.1pt + tokens.accent, fill: tokens.accent.transparentize(88%)))
          }
        })
        if bare { img } else { figure(img, caption: cap) }
      })
    }
  }

  // A records file (CSV, YAML or JSON, by its path under records/), handed to `body` as Typst data:
  //   #(wwii.records)("boats/ss-385-bang/patrol-1/attacks.csv", torpedo-ledger)
  // A placeholder until it is prepared. (A callback, because the request is content that has to be placed, and a
  // function can't both place content and return data.)
  let records(path, body) = {
    _request("records", "records:" + path, (path: path))
    let a = get("records:" + path)
    if a == none { _pending(path, height: 0.8in) } else { body(json(load(a.path))) }
  }

  // The QR tag: a Navy date-time group, the position and the citation, typed over a square code.
  let qr-tag(url, dtg: none, position: none, cite: none, label: "Scan for the chart") = {
    _request("qr", "qr:" + url, (url: url))
    let a = get("qr:" + url)
    box(stroke: 0.6pt + tokens.ink, inset: 7pt, width: 1.9in, {
      set par(justify: false, leading: 0.45em)
      set text(font: tokens.typed, size: 7pt)
      if dtg != none [*#dtg* \ ]
      if position != none [#position \ ]
      if cite != none [#text(fill: tokens.muted, cite) \ ]
      v(4pt)
      if a == none { _pending(url, height: 0.9in) } else { image(load(a.path), width: 0.9in) }
      v(3pt)
      text(font: tokens.display, size: 7pt, weight: "semibold", tracking: 0.1em, upper(label))
    })
  }

  // An engagement's map or timeline, drawn from the kit's engagements/<id>/engagement.json. Both number the same
  // marks the same way; `key: true` sets the numbered marks, with their citations, under the figure.
  let engagement-figure(id, figure: "map", width: 5.5in, box: none, window: none, follow: none, caption: none,
                        key: false) = {
    let key-id = "figure:" + figure + ":" + id + ":" + repr(width) + ":" + repr(box) + ":" + repr(window) + ":" + repr(follow)
    _request("figure", key-id, (figure: figure, engagement: id, width: width / 1in, box: box, window: window,
                                follow: follow))
    let a = get(key-id)
    if a == none {
      std.figure(_pending(figure + " · " + id, height: 2in), caption: caption, kind: image)
    } else {
      std.figure(image(load(a.path), width: width), caption: caption)
      if key { mark-key(a) }
    }
  }

  // A picture already in the scan cache (a photograph, a crop), by its path under the cache: placed as given,
  // or cropped to fill a box (`height` with fit "cover").
  let picture(path, width: 100%, height: auto, fit: "cover") = {
    _request("picture", "picture:" + path, (path: path))
    let a = get("picture:" + path)
    if a == none { _pending(path, height: if height == auto { 2in } else { height }) }
    else { image(load(a.path), width: width, height: height, fit: fit) }
  }

  // A person's route on one or more panels, from a stops file the family exports (data/route.json): how we know as
  // the line and the dot, how precisely as the ring; fronts are the kit's traced 12th Army Group lines for the days given.
  let route-map(data, panels: (), labels: (), fronts: (), window: none, width: 5.45in, height: none, legs: "full",
                caption: none) = {
    let key-id = "route:" + data + ":" + repr(panels) + repr(labels) + repr(fronts) + repr(window) + repr(width) + repr(height) + legs
    _request("figure", key-id, (figure: "route", data: data, panels: panels, labels: labels, fronts: fronts,
                                window: window, width: width / 1in, height: if height == none { none } else { height / 1in },
                                legs: legs))
    let a = get(key-id)
    let img = if a == none { _pending("route map · " + data, height: 3in) } else { image(load(a.path), width: width) }
    let who = if a != none and a.at("units", default: ()).len() > 0 { unit-key(a.units) } else { none }
    if caption == none { img; who } else { std.figure(img, caption: caption); who }
  }

  // The ground in perspective from behind one side's line: a picture to read beside the plan map, not one to measure
  // on. Heights are exaggerated; the figure says by how much, and so should the caption.
  let oblique-view(box, azimuth: 180, tilt: 30, exaggeration: 4, zoom: 12, data: none, window: none, fronts: (),
                   units: none, highlight: none, labels: (), places: (), width: 5.45in, height: none,
                   caption: none) = {
    let key-id = "oblique:" + repr((box, azimuth, tilt, exaggeration, zoom, data, window, fronts, units, highlight,
                                     labels, places, width, height))
    _request("figure", key-id, (figure: "oblique", box: box, azimuth: azimuth, tilt: tilt, exaggeration: exaggeration,
      zoom: zoom, data: data, window: window, fronts: fronts, units: units, highlight: highlight, labels: labels,
      places: places, width: width / 1in, height: if height == none { none } else { height / 1in }))
    let a = get(key-id)
    let img = if a == none { _pending("oblique view", height: if height == none { 3in } else { height }) } else { image(load(a.path), width: width) }
    let who = if a != none and a.at("units", default: ()).len() > 0 { unit-key(a.units) } else { none }
    if caption == none { img; who } else { std.figure(img, caption: caption); who }
  }

  // A slice of a day's 12th Army Group situation map as scanned, with the book's unit ringed in red (ours): the army's
  // own picture of the day, beside our map of the man's path.
  let situation-map(day, box, unit: none, width: 5.45in, caption: none) = {
    let key-id = "plate:" + day + ":" + repr(box) + ":" + repr(unit)
    _request("plate", key-id, (day: day, box: box, unit: unit))
    let a = get(key-id)
    let img = if a == none { _pending("situation map · " + day, height: 4in) } else { image(load(a.path), width: width) }
    if caption == none { img } else { std.figure(img, caption: caption) }
  }

  // An atlas extent's coordinated pair (book/atlas/<extent>/extent.yml): the panorama from above, the oblique view
  // of the same ground, both in one projected frame. `highlight` rings a division (its id in the day's units file).
  let atlas-view(extent, view: "panorama", width: 9.6in, highlight: none, highlight-words: none, azimuth: none,
                 tilt: none, exaggeration: none, caption: none) = {
    let key-id = "atlas:" + repr((extent, view, width, highlight, azimuth, tilt, exaggeration))
    _request("atlas", key-id, (extent: extent, view: view, width: width / 1in, highlight: highlight,
      highlight_words: highlight-words, azimuth: azimuth, tilt: tilt, exaggeration: exaggeration))
    let a = get(key-id)
    let img = if a == none { _pending(view + " · " + extent, height: 4in) } else { image(load(a.path), width: width) }
    if caption == none { img } else { std.figure(img, caption: caption) }
  }

  // A unit's chain of command from the kit's relations (army group to company), every link dated and cited:
  // view "timeline" over months (start, end), "ladder" on one day (on). `marks`: dated lines ((date:, words:)).
  let unit-chain(unit, view: "timeline", start: none, end: none, on: none, title: none, marks: (), width: 9.6in,
                 caption: none) = {
    let key-id = "chain:" + repr((unit, view, start, end, on, title, marks, width))
    _request("chain", key-id, (unit: unit, view: view, start: start, end: end, on: on, title: title, marks: marks,
      width: width / 1in))
    let a = get(key-id)
    let img = if a == none { _pending("chain · " + unit, height: 2in) } else { image(load(a.path), width: width) }
    if caption == none { img } else { std.figure(img, caption: caption) }
  }

  // An aircraft card: a photograph of the type (book/aircraft/photos.yml; one with a face only once approved), its
  // silhouettes, and the Allies' recognition manual's figures for it (records/air/aircraft.yml), as printed and cited.
  let aircraft-card(kind, photo: 0, width: 4.4in, caption: none) = {
    let key-id = "aircraft:" + repr((kind, photo, width))
    _request("aircraft", key-id, (type: kind, photo: photo, width: width / 1in))
    let a = get(key-id)
    let img = if a == none { _pending("aircraft · " + kind, height: 3in) } else { image(load(a.path), width: width) }
    if caption == none { img } else { std.figure(img, caption: caption) }
  }

  (facsimile: facsimile, records: records, qr-tag: qr-tag, engagement-figure: engagement-figure, picture: picture,
   route-map: route-map, oblique-view: oblique-view, situation-map: situation-map, atlas-view: atlas-view,
   unit-chain: unit-chain, aircraft-card: aircraft-card)
}

// One row per torpedo, from a patrol's attacks.csv as records() returns it.
#let torpedo-ledger(rows) = {
  set text(font: tokens.typed, size: 7.5pt)
  let result(r) = if r.hit == "" [—] else if r.hit == "Hit" [*Hit*] else [#r.hit]
  let heads = ("Attack", "Date", "Time", "Tube", "Torpedo", "Gyro", "Depth set", "Result")
  table(
    columns: 8,
    stroke: (x, y) => if y == 0 { (bottom: 0.8pt + tokens.ink) } else { (bottom: 0.3pt + tokens.rule) },
    inset: (x: 4pt, y: 3pt),
    table.header(..heads.map(h => text(font: tokens.display, weight: "semibold", size: 8pt, upper(h)))),
    ..rows.map(r => (r.attack, r.date, r.time + " " + r.zone, r.tube, "Mk " + r.torpedo, r.gyro, r.depth_set + " ft",
                     result(r))).flatten(),
  )
}


// ---------------------------------------------------------------- the evidence vocabulary
// Two questions, never one scale. How we know: reported (a record says so), derived (worked out from records),
// inferred (a reasoned step beyond them), assumed (taken as so for want of a record), or the family's account (told,
// not yet found in a record: shown beside the records, never ranked against them). How precisely: exact, a grid
// square, a town, an area. On maps the first is the line (solid, dashed), the second the ring.
#let _basis-style = (
  reported: (fill: tokens.ink, label: "reported"), derived: (fill: tokens.other-ink, label: "derived"),
  inferred: (fill: tokens.muted, label: "inferred"), assumed: (fill: tokens.accent, label: "assumed"),
  family: (fill: tokens.other-ink, label: "the family's account"),
)
#let basis(kind) = {
  let st = _basis-style.at(kind)
  box(inset: (x: 3pt, y: 1.2pt), outset: (y: 1pt), radius: 1.5pt, stroke: 0.5pt + st.fill,
      text(font: tokens.display, size: 6.5pt, weight: "semibold", tracking: 0.1em, fill: st.fill, upper(st.label)))
}
#let precision(words) = box(inset: (x: 3pt, y: 1.2pt), outset: (y: 1pt), radius: 1.5pt, fill: tokens.other,
  text(font: tokens.display, size: 6.5pt, weight: "semibold", tracking: 0.1em, fill: tokens.other-ink, upper(words)))

// ---------------------------------------------------------------- captions
// A photograph's own caption (as captioned at the time, quoted) is kept apart from ours (what it shows, what we
// infer, what it does not tell us).
#let photo-caption(original: none, ours: none, credit: none) = {
  set par(justify: false, first-line-indent: 0pt, leading: 0.5em)
  set text(size: 8pt)
  if original != none {
    block(below: 0.45em)[#text(font: tokens.display, size: 6.5pt, weight: "semibold", tracking: 0.12em,
      fill: tokens.muted, upper[As captioned at the time]) \ #text(style: "italic")["#original"]]
  }
  if ours != none { block(below: 0.45em, ours) }
  if credit != none { text(size: 7pt, fill: tokens.muted, credit) }
}

// ---------------------------------------------------------------- whole-page templates
#let chapter-opener(number: none, title: none, when: none, where: none, intro: none, picture: none, credit: none) = page(
  margin: 0pt, header: none, footer: none)[
  #if picture != none { block(width: 100%, height: 52%, clip: true, picture) }
  #pad(left: 0.85in, right: 0.75in, top: 0.35in)[
    #set par(justify: false)
    #if credit != none { place(top + right, dy: -0.28in, text(size: 6.5pt, fill: tokens.muted, credit)) }
    #if number != none { text(font: tokens.display, size: 11pt, weight: "semibold", tracking: 0.2em, fill: tokens.accent,
      upper[Chapter #number]) }
    #v(0.2em)
    #{
      show heading: it => block(text(size: 38pt, upper(it.body)))
      heading(level: 1, outlined: true, title)
    }
    #v(-0.3em)
    #text(font: tokens.display, size: 10pt, weight: "medium", tracking: 0.12em, fill: tokens.muted,
      upper[#when#if where != none [ · #where]])
    #v(1.1em)
    #set par(first-line-indent: 0pt)
    #text(size: 11.5pt, intro)
  ]
]

#let cover-photo(name: "", title: "", years: "", line: none, picture: none) = page(margin: 0pt, header: none, footer: none,
  fill: tokens.band)[
  #block(width: 100%, height: 64%, clip: true, picture)
  #pad(x: 0.7in, top: 0.32in)[
    #set par(justify: false, first-line-indent: 0pt)
    #set text(fill: tokens.band-ink)
    #text(font: tokens.display, size: 11pt, weight: "semibold", tracking: 0.22em, fill: rgb("#b8bfb2"), upper(title))
    #v(0.1em)
    #text(font: tokens.display, size: 46pt, weight: "bold", upper(name))
    #v(-0.6em)
    #text(font: tokens.display, size: 14pt, weight: "medium", tracking: 0.18em, years)
    #if line != none { v(0.5em); text(size: 10pt, style: "italic", fill: rgb("#c9cec3"), line) }
  ]
]

#let cover-type(name: "", title: "", years: "", epigraph: none, epigraph-source: none, serial: none) = page(
  margin: (x: 0.8in, top: 1.1in, bottom: 0.9in), header: none, footer: none, fill: tokens.paper)[
  #set par(justify: false, first-line-indent: 0pt, leading: 0.2em)
  #text(font: tokens.display, size: 11pt, weight: "semibold", tracking: 0.22em, fill: tokens.accent, upper(title))
  #v(0.6in)
  #text(font: tokens.display, size: 72pt, weight: "bold", tracking: -0.01em, upper(name))
  #v(-0.9em)
  #line(length: 100%, stroke: 1.2pt + tokens.ink)
  #v(0.2em)
  #text(font: tokens.display, size: 16pt, weight: "medium", tracking: 0.2em, years)
  #if serial != none { h(1fr); text(font: tokens.typed, size: 11pt, fill: tokens.muted, serial) }
  #v(1fr)
  #if epigraph != none {
    block(width: 100%, inset: (y: 14pt), stroke: (top: 0.5pt + tokens.rule, bottom: 0.5pt + tokens.rule))[
      #set par(justify: false, first-line-indent: 0pt)
      #text(font: tokens.typed, size: 15pt, epigraph)
      #if epigraph-source != none { v(0.4em); text(size: 8pt, fill: tokens.muted, epigraph-source) }
    ]
  }
]
