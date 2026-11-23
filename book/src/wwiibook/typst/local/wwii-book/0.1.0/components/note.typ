// Part of the wwii-book package (lib.typ imports it).
#import "../core.typ": *

// ---------------------------------------------------------------- notes and source lines
// A citation carried by a component, or written with `note(...)`, becomes a numbered note. On the grid
// (`templates/grid.typ`: `on-grid` turns `_notes-on` on) the note is set in the outer column beside its call: the call
// is a superior figure in the text, the note its number, its words and its source line. Off the grid (the draft page
// the older examples use) a `note` falls back to a footnote and the components keep their own source lines.
//
// The source line resolves a citation to the page it names: `rg64-480601116/p0028` is "National Archives, RG 64,
// NAID 480601116, p. 28", linked to the catalog's viewer at that page, as `cite.py` writes it. A citation of another
// source (`hist313/p82`) is read against the book's `sources:` (a dictionary of the records' SOURCES.yml keys to the
// short title a note gives): "History of the 313th Infantry (1947), p. 82".

#let _notes-on = state("wwii-notes-on", false)
#let _notes-mode = state("wwii-notes-mode", "side")    // on the grid: "side" (the outer column), "end" (`endnotes`)
// or "part" (written out for a part's notes pages, `part-notes`)
#let _note-sources = state("wwii-note-sources", (:))
#let note-counter = counter("wwii-note")

#let _nara = regex("^rg(\d+)-(\d+)/p(\d+)$")
#let _other = regex("^([A-Za-z0-9_-]+)([:/])(.+)$")

// Where in a non-archive source: its last part read as a page ("p82" is "p. 82", "f1" is "f. 1"), after the parts
// before it when the citation is a path ("breakout/4/p74" is "4, p. 74", set after a title ending "ch." as "ch. 4,
// p. 74"). An identifier after a colon (`ddbzp:<id>/p1`) is the source's own and is left out: the title the book
// gives the source says which issue.
// A source the book gives as (title: [...], id: true) is one whose identifier names the item (a JACAR reference
// code): the identifier is kept after the title. A source may give its own short title, (title: [...], short: [...]),
// which a repeated citation on a part's notes pages uses (`short: true`).
#let _entry-title(entry, short: false) = {
  if type(entry) != dictionary { entry } else if short and "short" in entry { entry.short } else { entry.title }
}

#let _title(entry, sep, rest, short: false) = {
  let t = _entry-title(entry, short: short)
  if type(entry) == dictionary and entry.at("id", default: false) and sep == ":" [#t #rest.split("/").first()] else { t }
}

#let _locus(title, sep, rest) = {
  let parts = rest.split("/")
  let last = parts.last().replace(regex("^p(\d+)$"), m => "p. " + str(int(m.captures.at(0))))
    .replace(regex("^f(\d+)$"), m => "f. " + str(int(m.captures.at(0))))
  let middle = if sep == "/" { parts.slice(0, -1) } else { () }
  if middle.len() > 0 { [#title #middle.join(", "), #last] } else { [#title, #last] }
}

// A source whose items are cited "<key>-<item>/p<n>" (ok45th-17541/p23): its key is the part before the first hyphen,
// and the item is kept as the identifier, as for a JACAR reference code
#let _prefixed(cite, titles) = {
  let m = cite.match(regex("^([A-Za-z0-9_]+)-([^/:]+)/(.+)$"))
  if m == none or m.captures.at(0) not in titles { return none }
  let (key, item, rest) = m.captures
  (key: key, entry: titles.at(key), item: item, rest: rest)
}

// A citation's source line, read against `titles` (the book's sources). `short`: the form a repeated citation takes
// (an archive item by its NAID and page; another source by its own `short:` title where it gives one).
#let _source-line(cite, titles, short: false) = {
  let m = cite.match(_nara)
  let o = cite.match(_other)
  let pre = if o != none and o.captures.at(0) in titles { none } else { _prefixed(cite, titles) }
  if m != none {
    let (group, naid, page) = m.captures
    let p = str(int(page))
    link("https://catalog.archives.gov/id/" + naid + "?objectPage=" + p,
      if short [NAID #naid, p. #p] else [National Archives, RG #group, NAID #naid, p. #p])
  } else if o != none and o.captures.at(0) in titles {
    _locus(_title(titles.at(o.captures.at(0)), o.captures.at(1), o.captures.at(2), short: short), o.captures.at(1),
      o.captures.at(2))
  } else if pre != none {
    _locus([#_entry-title(pre.entry, short: short) #pre.item], ":", pre.rest)
  } else {
    raw(cite)
  }
}

// What a citation names, for telling a repeated citation from a first: an archive item by its NAID, another source by
// its key and its full title as the note gives it (an identifier kept after it, as a JACAR code is, included);
// `declared`: whether the source gives its own short title. Needs no context.
#let _cited(cite, titles) = {
  let m = cite.match(_nara)
  let o = cite.match(_other)
  let pre = if o != none and o.captures.at(0) in titles { none } else { _prefixed(cite, titles) }
  if m != none { return (key: "nara:" + m.captures.at(1), title: none, declared: true) }
  if o != none and o.captures.at(0) in titles {
    let e = titles.at(o.captures.at(0))
    return (key: o.captures.at(0), title: _title(e, o.captures.at(1), o.captures.at(2)),
            declared: type(e) == dictionary and "short" in e)
  }
  if pre != none {
    return (key: pre.key + "-" + pre.item, title: [#_entry-title(pre.entry) #pre.item],
            declared: type(pre.entry) == dictionary and "short" in pre.entry)
  }
  (key: "raw:" + cite, title: none, declared: true)
}

// A citation's source line. Needs context (it reads the book's sources). The citation is carried beside it, so a note
// written out for the part's notes pages (`_resolve`) can set the line from the citation there.
#let source-line(cite) = [#context _source-line(cite, _note-sources.get())#metadata(cite)<wwii-inline-cite>]

// A note's body with every source line in it resolved now, against `titles`: a note written out keeps no context
#let _resolve(c, titles) = {
  if type(c) != content { return c }
  if c.func() == metadata and c.has("label") and c.label == <wwii-inline-cite> { return _source-line(c.value, titles) }
  if repr(c.func()) == "context" { return [] }
  if c.has("children") { let r = c.children.map(x => _resolve(x, titles)).join(); return if r == none { [] } else { r } }
  if c.func() in (emph, strong) { return (c.func())(_resolve(c.body, titles)) }
  c
}

// A note's whole text: its words (without a closing full stop), then its source line.
// With `titles` the source line is resolved here (for a note written out, `part-notes`), not where it is set.
#let _note-text(body, cite, titles: none, short: false) = {
  if body != none { if titles == none { body } else { _resolve(body, titles) } }
  if body != none and cite != none { [. ] }
  if cite != none { if titles == none { source-line(cite) } else { _source-line(cite, titles, short: short) } }
  if body != none or cite != none { [.] }
}

// A numbered note at this point in the text: `note[Words]`, `note(cite: "rg64-480601116/p0028")`, or both.
#let note(..words, cite: none) = context {
  let body = words.pos().at(0, default: none)
  if not _notes-on.get() {
    footnote(_note-text(body, cite))
  } else {
    note-counter.step()
    let n = note-counter.get().first() + 1
    sym.wj   // the call never starts a line
    box(super(typographic: false, size: 0.62em, baseline: -0.42em, text(font: tokens.display, weight: "semibold",
        fill: tokens.ink, str(n))))
    [#metadata((n: n, body: body, cite: cite)) <wwii-note>]
    if _notes-mode.get() == "part" {
      // written out for the part's notes pages: its number, its chapter's title, and its whole text resolved here
      // a bare citation (no words of its own) carries its short form too, for `partnotes.abbreviate` to set where the
      // part has cited the source before; a note with words is set in full wherever it falls
      let opened = query(selector(heading.where(level: 1)).before(here()))
      let chapter = if opened.len() > 0 { opened.last().body } else { none }
      let titles = _note-sources.get()
      let cited = if cite != none { _cited(cite, titles) } else { none }
      [#metadata((n: n, chapter: chapter, text: _note-text(body, cite, titles: titles), cite: cite, cited: cited,
                  short: if body == none and cite != none { _note-text(none, cite, titles: titles, short: true) })
       ) <wwii-part-note>]
    }
  }
}

// The notes of one page, set in its outer column in the order of their numbers (the reading order: down the first
// column, then the second), each level with its call's line where it can be: a note that would overlap the one
// before it moves down, and the last notes move up if they would run off the foot. `x` and `width` are the column's,
// `head` and `foot` the text frame's, all from the page's top left corner.
#let _note-style(body) = {
  set text(font: tokens.body, size: 7.2pt, fill: tokens.ink, top-edge: 5.6pt, bottom-edge: -1.6pt, hyphenate: true)
  set par(justify: false, leading: 2.55pt, spacing: 2.55pt, first-line-indent: 0pt)
  body
}

#let _side-notes(x: 0pt, width: 110pt, head: 0pt, foot: 0pt, gap: 4.875pt) = context {
  let p = here().page()
  let here-notes = query(<wwii-note>).filter(m => m.location().page() == p)
  if here-notes.len() == 0 { return }
  let items = here-notes.map(m => {
    let v = m.value
    let words = _note-style(grid(columns: (11pt, width - 11pt),
      text(font: tokens.display, weight: "semibold", size: 7.2pt, str(v.n)), _note-text(v.body, v.cite)))
    // a call's position is its line's baseline; the note's first baseline is set level with it
    (y: m.location().position().y - 5.6pt, n: v.n, words: words, h: measure(words).height)
  }).sorted(key: it => it.n)
  // down: no overlaps
  let ys = ()
  let floor = head
  for it in items {
    let y = calc.max(it.y, floor)
    ys.push(y)
    floor = y + it.h + gap
  }
  // up: nothing past the foot
  let ceiling = foot
  for i in range(items.len() - 1, -1, step: -1) {
    let y = calc.min(ys.at(i), ceiling - items.at(i).h)
    ys.at(i) = calc.max(y, head)
    ceiling = ys.at(i) - gap
  }
  for (i, it) in items.enumerate() { place(top + left, dx: x, dy: ys.at(i), it.words) }
}

// ---------------------------------------------------------------- end notes
// With `on-grid.with(notes: "end")` the notes are set together where `endnotes()` stands: the ones called since the
// last end notes, in the text's two columns, in the book's type at a smaller size, each with its number as the text
// calls it and its source line as a side note gives it, each chapter's under the chapter's title (the numbers run on
// across chapters, or begin again, as the text's do). `section-sources` sets them before its sources, and `on-grid` closes the
// section with them, so a section sets nothing to have them; with the notes beside the text it sets nothing.
#let endnotes(heading: [Notes]) = context {
  if not _notes-mode.get() == "end" { return }
  let earlier = query(selector(<wwii-endnotes>).before(here()))
  let sel = selector(<wwii-note>).before(here())
  if earlier.len() > 0 { sel = selector(<wwii-note>).after(earlier.last().location()).before(here()) }
  let notes = query(sel)
  if notes.len() == 0 { return }
  // the chapter's figures still waiting to float go first, so the notes close the section after them
  place.flush()
  block(above: 20pt, below: 8pt, sticky: true, text(font: tokens.display, weight: "semibold", size: 9pt,
    tracking: 0.12em, upper(heading)))
  set text(font: tokens.body, size: 7.6pt, fill: tokens.ink, hyphenate: true, number-type: "lining", top-edge: 6pt,
           bottom-edge: -1.8pt)
  set par(justify: false, leading: 2.4pt, spacing: 3.6pt, first-line-indent: 0pt, hanging-indent: 13pt)
  let last = none
  for (i, m) in notes.enumerate() {
    let v = m.value
    // each chapter's notes under its title, so a reader finds a note by the chapter as well as by its number
    let opened = query(selector(std.heading.where(level: 1)).before(m.location()))
    let chapter = if opened.len() > 0 { opened.last().location() } else { none }
    if chapter != none and chapter != last {
      block(above: if i == 0 { 2pt } else { 9pt }, below: 4pt, sticky: true,
        text(font: tokens.display, size: 7.4pt, weight: "semibold", fill: tokens.muted, opened.last().body))
    }
    last = chapter
    par[#box(width: 13pt, text(font: tokens.display, weight: "semibold", size: 7.2pt, str(v.n)))#_note-text(v.body, v.cite)]
  }
  [#metadata("endnotes") <wwii-endnotes>]
}

// ---------------------------------------------------------------- a section's sources, at its end
// Every source the section's notes cite, gathered: one line a source, its pages in order, each page linked where the
// archive has a viewer. A section is the run of notes since the numbering last began at 1 (`running-text` restarts it),
// so `section-sources()` set at a chapter's end lists that chapter's. `titles` names an archive item where the book
// knows it ("74802831": "BANG, third war patrol report").
#let _page-num(s) = { let m = s.match(regex("\d+")); if m == none { 0 } else { int(m.text) } }

// The section's sources as entries: (key, head, naid, pages), `head` the line before its pages (a NARA item's
// pages are linked when it is set). Needs context.
// The notes are those since the last `section-sources` (or the book's start): a section that sets its sources at
// each chapter's end lists each chapter's, and one that sets them once at its end lists every chapter's, however
// often its numbering begins again. `whole`: every note before here.
#let _source-entries(titles, whole: false) = {
  let earlier = query(selector(<wwii-section-sources>).before(here()))
  let sel = selector(<wwii-note>).before(here())
  if earlier.len() > 0 and not whole { sel = selector(<wwii-note>).after(earlier.last().location()).before(here()) }
  let before = query(sel)
  if before.len() == 0 { return () }
  let groups = (:)          // a source's key -> (kind, label, pages)
  let order = ()
  for m in before {
    let c = m.value.cite
    if c == none { continue }
    let nara = c.match(_nara)
    let other = c.match(_other)
    let pm = c.match(regex("^([A-Za-z0-9_]+)-([^/:]+)/([pf]\\d+)$"))
    let (key, page) = if nara != none {
      ("rg" + nara.captures.at(0) + "-" + nara.captures.at(1), str(int(nara.captures.at(2))))
    } else if pm != none and pm.captures.at(0) in _note-sources.get() and not (other != none and other.captures.at(0) in _note-sources.get()) {
      (pm.captures.at(0) + "-" + pm.captures.at(1), pm.captures.at(2))
    } else if other != none {
      let parts = other.captures.at(2).split("/")
      (other.captures.at(0) + other.captures.at(1) + parts.slice(0, -1).join("/"), parts.last())
    } else { (c, none) }
    if key not in groups { groups.insert(key, (cite: c, pages: ())); order.push(key) }
    if page != none and page not in groups.at(key).pages { groups.at(key).pages.push(page) }
  }
  let known = _note-sources.get()
  let entries = ()
  for key in order {
    let g = groups.at(key)
    let pages = g.pages.sorted(key: _page-num)
    let nara = g.cite.match(_nara)
    if nara != none {
      let (group, naid, _) = nara.captures
      let item = titles.at(naid, default: none)
      entries.push((key: key, naid: naid, pages: pages,
                    head: [National Archives, RG #group, NAID #naid#if item != none [, #emph(item)]]))
    } else {
      let o = g.cite.match(_other)
      let pre = if o != none and o.captures.at(0) in known { none } else { _prefixed(g.cite, known) }
      let title = if o != none and o.captures.at(0) in known {
        _title(known.at(o.captures.at(0)), o.captures.at(1), o.captures.at(2))
      } else if pre != none {
        let t = if type(pre.entry) == dictionary { pre.entry.title } else { pre.entry }
        [#t #pre.item]
      } else { raw(key) }
      // a path's middle parts (a chapter) follow the title, as a note's source line sets them
      let middle = if pre == none and o != none and o.captures.at(1) == "/" { o.captures.at(2).split("/").slice(0, -1) } else { () }
      entries.push((key: key, naid: none, pages: pages, head: [#title#if middle.len() > 0 [ #middle.join(", ")]]))
    }
  }
  entries
}

// One source's line: its head, then its pages (a NARA item's linked to the catalog's viewer)
#let _source-par(e) = {
  let pages = e.pages
  if e.naid != none {
    par[#e.head, #if pages.len() > 1 [pp.] else [p.] #{
      pages.map(p => link("https://catalog.archives.gov/id/" + e.naid + "?objectPage=" + p, p)).join(", ")
    }.]
  } else {
    let kind = if pages.len() > 0 and pages.all(p => p.starts-with("f")) { "f" } else { "p" }
    let nums = pages.map(p => p.replace(regex("^[pf](\d+)$"), m => str(int(m.captures.at(0)))))
    // a page or folio gets "p." or "f."; any other locus (a year, a volume) is printed as it stands
    let paged = pages.len() > 0 and pages.all(p => p.match(regex("^[pf]\d+$")) != none)
    let lead = if not paged { "" } else if nums.len() > 1 { kind + kind + ". " } else { kind + ". " }
    par[#e.head#if nums.len() > 0 [, #lead#nums.join(", ")].]
  }
}

#let _sources-list(heading, entries) = {
  if entries.len() == 0 { return }
  block(above: 18pt, below: 6pt, sticky: true, text(font: tokens.display, weight: "semibold", size: 9pt, heading))
  set text(font: tokens.body, size: 7.6pt)
  set par(justify: false, hanging-indent: 10pt, spacing: 4pt, first-line-indent: 0pt)
  for e in entries { _source-par(e) }
}

// Set here; with the notes written out for the part's pages (`part-notes`), nothing is set: the titles are kept, and
// `on-grid` writes out the whole book's sources at its end (`_part-sources`)
#let _part-titles = state("wwii-part-titles", (:))
#let _section-sources(heading, titles) = {
  context {
    if _notes-mode.get() == "part" { _part-titles.update(t => t + titles) } else { _sources-list(heading, _source-entries(titles)) }
  }
  [#metadata("section-sources") <wwii-section-sources>]
}

// With the notes on the part's pages: every source the book's notes cite, and the book's own sources' titles (each
// key's title and short title, for `partnotes.abbreviate` to know a note that is a source's title alone)
#let _part-sources() = context {
  if _notes-mode.get() == "part" {
    [#metadata(_source-entries(_part-titles.final(), whole: true)) <wwii-part-sources>]
    let known = _note-sources.get()
    [#metadata(known.keys().map(k => {
      let e = known.at(k)
      (key: k, title: _entry-title(e), short: if type(e) == dictionary and "short" in e { e.short })
    })) <wwii-part-titles>]
  }
}

// With the notes at the end, the section's notes come first, then its sources
// The end mark: a small solid square at the end of a part's text, set against the measure's right edge, so a part
// closes on purpose before its notes. The volume's build asks for it on a part's last section (`--input end-mark=true`):
// the section's last `section-sources` sets it before the notes, or `on-grid` at the section's end when it has none.
// `section-sources(end-mark: true)` sets it where a part ends inside a section (one of several men's parts).
#let _end-mark() = block(above: 9pt, below: 0pt, width: 100%, align(right, box(width: 5.5pt, height: 5.5pt, fill: tokens.ink)))
#let end-mark = _end-mark
#let _end-mark-due() = sys.inputs.at("end-mark", default: "") == "true"

#let section-sources(heading: [Sources], titles: (:), end-mark: auto) = {
  [#metadata(none) <wwii-section-end>]
  if end-mark == true { _end-mark() } else if end-mark == auto and _end-mark-due() {
    // the section's last: none after it
    context if query(selector(<wwii-section-end>).after(here(), inclusive: false)).len() == 0 { _end-mark() }
  }
  endnotes()
  _section-sources(heading, titles)
}

// ---------------------------------------------------------------- a part's notes, on pages of their own
// With `on-grid.with(notes: "part")` (or `--input notes=part`) a section sets no notes and no sources: each note is
// written out (`<wwii-part-note>`: its number, its chapter's title and its whole text) and so are the sources
// (`<wwii-part-sources>`), and the build gathers them, section by section, into one file that sets them here, on pages
// of their own at the end of the part. `sections` is in the part's order, each `(title: [...], chapters: ((title:
// [...], notes: ((n, [text]), ...)), ...))`: a section's title (its first chapter's), then its chapters, each under its
// own title where the section has more than one (the first left untitled when its title is the section's), every note
// with its number as the text calls it. `sources` are the part's sources, one list (entries as `_source-entries` gives
// them). Set in three columns (or `columns`) in the book's type at 7.6 pt, the source lines as a side note gives them.
#let part-notes(name: none, heading: [Notes], sections: (), sources: (), columns: 3, gutter: 14pt) = {
  set page(columns: columns)
  set std.columns(gutter: gutter)
  place(top, float: true, scope: "parent", clearance: 22pt, block(width: 100%)[
    #set par(justify: false, first-line-indent: 0pt)
    #if name != none {
      block(below: 10pt, text(font: tokens.display, size: 8.5pt, weight: "semibold", tracking: 0.14em,
        fill: tokens.muted, upper(name)))
    }
    #{
      show std.heading: it => block(below: 12pt, text(font: tokens.display, size: 30pt, weight: "bold",
        top-edge: "cap-height", bottom-edge: "baseline", upper(it.body)))
      std.heading(level: 1, outlined: false, heading)
    }
    #line(length: 100%, stroke: 0.5pt + tokens.rule)
  ])
  set text(font: tokens.body, size: 7.6pt, fill: tokens.ink, hyphenate: true, number-type: "lining", top-edge: 6pt,
           bottom-edge: -1.8pt)
  set par(justify: false, leading: 2.4pt, spacing: 3.6pt, first-line-indent: 0pt, hanging-indent: 15pt)
  for (i, s) in sections.enumerate() {
    block(above: if i == 0 { 0pt } else { 14pt }, below: 5pt, sticky: true,
      text(font: tokens.display, weight: "semibold", size: 8pt, tracking: 0.1em, hyphenate: false, upper(s.title)))
    let several = s.chapters.len() > 1
    for (j, c) in s.chapters.enumerate() {
      if several and not (j == 0 and c.title == s.title) {
        block(above: if j == 0 { 2pt } else { 8pt }, below: 4pt, sticky: true,
          text(font: tokens.display, size: 7.4pt, weight: "semibold", fill: tokens.muted, hyphenate: false, c.title))
      }
      for (n, t) in c.notes {
        par[#box(width: 15pt, text(font: tokens.display, weight: "semibold", size: 7.2pt, str(n)))#t]
      }
    }
  }
  _sources-list(text(size: 8pt, tracking: 0.1em, upper[Sources]), sources)
}
