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
#let _locus(title, sep, rest) = {
  let parts = rest.split("/")
  let last = parts.last().replace(regex("^p(\d+)$"), m => "p. " + m.captures.at(0))
    .replace(regex("^f(\d+)$"), m => "f. " + m.captures.at(0))
  let middle = if sep == "/" { parts.slice(0, -1) } else { () }
  if middle.len() > 0 { [#title #middle.join(", "), #last] } else { [#title, #last] }
}

// A citation's source line. Needs context (it reads the book's sources).
#let source-line(cite) = context {
  let m = cite.match(_nara)
  let o = cite.match(_other)
  let titles = _note-sources.get()
  if m != none {
    let (group, naid, page) = m.captures
    let p = str(int(page))
    link("https://catalog.archives.gov/id/" + naid + "?objectPage=" + p)[National Archives, RG #group, NAID #naid, p. #p]
  } else if o != none and o.captures.at(0) in titles {
    _locus(titles.at(o.captures.at(0)), o.captures.at(1), o.captures.at(2))
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
