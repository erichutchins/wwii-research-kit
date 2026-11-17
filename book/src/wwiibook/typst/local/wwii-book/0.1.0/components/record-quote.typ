// Part of the wwii-book package (lib.typ imports it).
#import "../core.typ": *

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
