// Part of the wwii-book package (lib.typ imports it).
#import "../core.typ": *

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
