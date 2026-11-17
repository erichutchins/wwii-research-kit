// Part of the wwii-book package (lib.typ imports it).
#import "../core.typ": *

// Who's who of the divisions on a map: the number as drawn, and its name worked out from the symbol.
#let unit-key(units) = {
  set text(size: 7pt)
  set par(justify: false, first-line-indent: 0pt, leading: 0.45em)
  let line(u) = [#text(font: tokens.display, weight: "bold", fill: if u.highlight { tokens.accent } else { tokens.ink }, u.number) #u.name]
  let ours = units.filter(u => u.side != "German")
  let theirs = units.filter(u => u.side == "German")
  block(above: 0.5em, below: 0.9em, grid(columns: (1fr, 1fr), gutter: 12pt,
    [#text(font: tokens.display, size: 6.5pt, weight: "semibold", tracking: 0.1em, fill: tokens.muted, upper[American]) \
     #ours.map(line).join([ · ])],
    [#text(font: tokens.display, size: 6.5pt, weight: "semibold", tracking: 0.1em, fill: tokens.muted, upper[German]) \
     #theirs.map(line).join([ · ])]))
}
