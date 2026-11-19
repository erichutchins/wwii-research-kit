// Part of the wwii-book package (lib.typ imports it).
#import "../core.typ": *

// The call to action: where the book sends a reader to the kit's public site (an engagement playing on one clock, a
// page to explore). Its words in the dark amber, a small mark in the amber; nothing else in the book wears either.
//   #see-it-move[The kit's page for this engagement plays the same records on one clock.]
#let cta-mark = text(fill: tokens.cta, size: 0.9em, sym.triangle.filled.small.r)

#let see-it-move(label: [See it move], body) = block(above: 1.2em, below: 0.6em, {
  text(font: tokens.display, weight: "bold", size: 7.5pt, tracking: 0.9pt, fill: tokens.cta-ink, upper(label))
  h(4pt)
  cta-mark
  h(6pt)
  body
})
