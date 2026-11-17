// Part of the wwii-book package (lib.typ imports it).
#import "../core.typ": *

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
