// Part of the wwii-book package (lib.typ imports it).
#import "../core.typ": *
#import "../core.typ": eyebrow as _eyebrow
#import "../components/note.typ": note-counter
#import "grid.typ": *

// ---------------------------------------------------------------- running text
// A chapter of running text on the grid: it opens a new page (a recto unless `recto: false`) with the chapter's head
// across both text columns (eyebrow, title, standfirst), then its text in two columns with its notes beside them in
// the outer column, numbered from 1 in each chapter. Use inside `#show: on-grid`:
//
//   #running-text(eyebrow: [July 1944 · the Cotentin], title: [Company B], standfirst: [...])[ ...text... ]
#let running-text(title: none, eyebrow: none, standfirst: none, recto: true, body) = {
  pagebreak(weak: true, to: if recto { "odd" } else { none })
  note-counter.update(0)
  place(top, float: true, scope: "parent", clearance: 26pt, block(width: 100%)[
    #set par(justify: false, first-line-indent: 0pt)
    #if eyebrow != none { block(below: 10pt, _eyebrow(eyebrow)) }
    #{
      show heading: it => block(below: 12pt, text(font: tokens.display, size: 30pt, weight: "bold",
        top-edge: "cap-height", bottom-edge: "baseline", upper(it.body)))
      heading(level: 1, title)
    }
    #if standfirst != none {
      block(width: 82%, text(size: 12pt, style: "italic", top-edge: 9.4pt, bottom-edge: -2.6pt,
        par(leading: 4pt, standfirst)))
    }
    #line(length: 100%, stroke: 0.5pt + tokens.rule)
  ])
  body
}

// Something set across both text columns, at the top or the foot of a page (a facsimile, a photograph, a wide table),
// with the text flowing round it.
#let across(at: top, body) = place(at, float: true, scope: "parent", clearance: 18pt, block(width: 100%, body))
