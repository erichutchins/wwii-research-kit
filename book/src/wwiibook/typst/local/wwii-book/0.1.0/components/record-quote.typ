// Part of the wwii-book package (lib.typ imports it).
#import "../core.typ": *
#import "note.typ": _notes-on, note

// The record's words as typed, with where they come from. Off the grid, the source and the citation are set under
// the quote. On the grid (`on-grid`), the quote ends in a note call and its source and citation become that numbered
// note in the outer column, the source line resolving the citation to its archive page; the quote keeps the text's
// 13 pt baseline (the typewriter's double spacing, as the records were typed).
#let _record-quote-draft(body, cite, source) = block(inset: (left: 11pt, y: 2pt), stroke: (left: 1.2pt + tokens.accent),
                                                     above: 1.1em, below: 1.1em)[
  #set par(justify: false, first-line-indent: 0pt, leading: 0.55em)
  #typed(body)
  #if source != none or cite != none {
    linebreak()
    text(size: 7.5pt, fill: tokens.muted)[#source#if source != none and cite != none [ · ]#if cite != none { raw(cite) }]
  }
]

#let _record-quote-grid(body, cite, source) = block(inset: (left: 10pt), stroke: (left: 1.2pt + tokens.accent),
                                                    above: 16.5pt, below: 16.5pt)[
  #set par(justify: false, first-line-indent: 0pt)
  #set text(font: tokens.typed, size: 8.6pt, top-edge: 7.41pt, bottom-edge: -2.09pt, number-type: "lining")
  #body#if source != none or cite != none { note(source, cite: cite) }
]

#let record-quote(body, cite: none, source: none) = context {
  if _notes-on.get() { _record-quote-grid(body, cite, source) } else { _record-quote-draft(body, cite, source) }
}
