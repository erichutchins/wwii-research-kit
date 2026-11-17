// Part of the wwii-book package (lib.typ imports it).
#import "../core.typ": *

// ---------------------------------------------------------------- whole-page templates
#let chapter-opener(number: none, title: none, when: none, where: none, intro: none, picture: none, credit: none) = page(
  margin: 0pt, header: none, footer: none)[
  #if picture != none { block(width: 100%, height: 52%, clip: true, picture) }
  #pad(left: 0.85in, right: 0.75in, top: 0.35in)[
    #set par(justify: false)
    #if credit != none { place(top + right, dy: -0.28in, text(size: 6.5pt, fill: tokens.muted, credit)) }
    #if number != none { text(font: tokens.display, size: 11pt, weight: "semibold", tracking: 0.2em, fill: tokens.accent,
      upper[Chapter #number]) }
    #v(0.2em)
    #{
      show heading: it => block(text(size: 38pt, upper(it.body)))
      heading(level: 1, outlined: true, title)
    }
    #v(-0.3em)
    #text(font: tokens.display, size: 10pt, weight: "medium", tracking: 0.12em, fill: tokens.muted,
      upper[#when#if where != none [ · #where]])
    #v(1.1em)
    #set par(first-line-indent: 0pt)
    #text(size: 11.5pt, intro)
  ]
]
