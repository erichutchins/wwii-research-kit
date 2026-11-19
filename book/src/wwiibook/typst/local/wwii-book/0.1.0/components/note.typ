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
#let _note-sources = state("wwii-note-sources", (:))
#let note-counter = counter("wwii-note")

#let _nara = regex("^rg(\d+)-(\d+)/p(\d+)$")
#let _other = regex("^([A-Za-z0-9_-]+)([:/])(.+)$")

// Where in a non-archive source: its last part read as a page ("p82" is "p. 82", "f1" is "f. 1"), after the parts
// before it when the citation is a path ("breakout/4/p74" is "4, p. 74", set after a title ending "ch." as "ch. 4,
// p. 74"). An identifier after a colon (`ddbzp:<id>/p1`) is the source's own and is left out: the title the book
// gives the source says which issue.
// A source the book gives as (title: [...], id: true) is one whose identifier names the item (a JACAR reference
// code): the identifier is kept after the title.
#let _title(entry, sep, rest) = {
  if type(entry) == dictionary {
    if entry.at("id", default: false) and sep == ":" [#entry.title #rest.split("/").first()] else { entry.title }
  } else { entry }
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

// A citation's source line. Needs context (it reads the book's sources).
#let source-line(cite) = context {
  let m = cite.match(_nara)
  let o = cite.match(_other)
  let titles = _note-sources.get()
  let pre = if o != none and o.captures.at(0) in titles { none } else { _prefixed(cite, titles) }
  if m != none {
    let (group, naid, page) = m.captures
    let p = str(int(page))
    link("https://catalog.archives.gov/id/" + naid + "?objectPage=" + p)[National Archives, RG #group, NAID #naid, p. #p]
  } else if o != none and o.captures.at(0) in titles {
    _locus(_title(titles.at(o.captures.at(0)), o.captures.at(1), o.captures.at(2)), o.captures.at(1), o.captures.at(2))
  } else if pre != none {
    let title = if type(pre.entry) == dictionary { pre.entry.title } else { pre.entry }
    _locus([#title #pre.item], ":", pre.rest)
  } else {
    raw(cite)
  }
}

// A note's whole text: its words (without a closing full stop), then its source line.
#let _note-text(body, cite) = {
  if body != none { body }
  if body != none and cite != none { [. ] }
  if cite != none { source-line(cite) }
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

// ---------------------------------------------------------------- a section's sources, at its end
// Every source the section's notes cite, gathered: one line a source, its pages in order, each page linked where the
// archive has a viewer. A section is the run of notes since the numbering last began at 1 (`running-text` restarts it),
// so `section-sources()` set at a chapter's end lists that chapter's. `titles` names an archive item where the book
// knows it ("74802831": "BANG, third war patrol report").
#let _page-num(s) = { let m = s.match(regex("\d+")); if m == none { 0 } else { int(m.text) } }

#let section-sources(heading: [Sources], titles: (:)) = context {
  let before = query(selector(<wwii-note>).before(here()))
  if before.len() == 0 { return }
  let start = before.len() - 1
  while start > 0 and before.at(start).value.n != 1 { start -= 1 }
  let groups = (:)          // a source's key -> (kind, label, pages)
  let order = ()
  for m in before.slice(start) {
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
  block(above: 18pt, below: 6pt, sticky: true, text(font: tokens.display, weight: "semibold", size: 9pt, heading))
  set text(font: tokens.body, size: 7.6pt)
  set par(justify: false, hanging-indent: 10pt, spacing: 4pt, first-line-indent: 0pt)
  for key in order {
    let g = groups.at(key)
    let pages = g.pages.sorted(key: _page-num)
    let nara = g.cite.match(_nara)
    if nara != none {
      let (group, naid, _) = nara.captures
      let item = titles.at(naid, default: none)
      par[National Archives, RG #group, NAID #naid#if item != none [, #emph(item)], #if pages.len() > 1 [pp.] else [p.] #{
        pages.map(p => link("https://catalog.archives.gov/id/" + naid + "?objectPage=" + p, p)).join(", ")
      }.]
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
      let kind = if pages.len() > 0 and pages.all(p => p.starts-with("f")) { "f" } else { "p" }
      let nums = pages.map(p => p.replace(regex("^[pf](\d+)$"), m => str(int(m.captures.at(0)))))
      // a page or folio gets "p." or "f."; any other locus (a year, a volume) is printed as it stands
      let paged = pages.len() > 0 and pages.all(p => p.match(regex("^[pf]\d+$")) != none)
      let lead = if not paged { "" } else if nums.len() > 1 { kind + kind + ". " } else { kind + ". " }
      par[#title#if middle.len() > 0 [ #middle.join(", ")]#if nums.len() > 0 [, #lead#nums.join(", ")].]
    }
  }
}
