// Part of the wwii-book package (lib.typ imports it).
#import "../core.typ": *

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
