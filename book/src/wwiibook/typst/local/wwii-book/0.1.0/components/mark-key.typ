// Part of the wwii-book package (lib.typ imports it).
#import "../core.typ": *

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
