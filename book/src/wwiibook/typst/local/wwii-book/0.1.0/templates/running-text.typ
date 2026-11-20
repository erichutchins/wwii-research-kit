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
//
// `opener: "column"` opens the chapter where the text before it ends instead, with no new page: a smaller head of the
// same family set within one text column (the eyebrow as before, the title at 17 pt, a short standfirst at 10.5 pt),
// three lines of space above it and the opener's rule under it, the whole a whole number of the grid's lines so the
// text after it stays on the baseline. It keeps with the text that follows (never alone at a column's foot), restarts
// the notes as the full opener does, and leaves the page its running head. For the shorter chapters of a section,
// where a new page for each would leave the one before it ending partway down a page; `recto` is ignored.
#let _column-opener(title, eyebrow, standfirst, preset) = {
  let g = grids.at(preset)
  let lead = g.baseline - g.size
  let head = block(width: 100%, {
    set par(justify: false, first-line-indent: 0pt, leading: lead, spacing: lead)
    if eyebrow != none { block(above: 0pt, below: 7pt, _eyebrow(eyebrow)) }
    {
      show heading: it => block(above: 0pt, below: 7pt, text(font: tokens.display, size: 17pt, weight: "bold",
        top-edge: "cap-height", bottom-edge: "baseline", par(leading: 4pt, upper(it.body))))
      set text(hyphenate: false)
      [#heading(level: 1, title) <wwii-column-head>]
    }
    if standfirst != none {
      block(above: 0pt, below: 7pt, text(size: 10.5pt, style: "italic", .._edges(10.5pt),
        par(leading: g.baseline - 10.5pt, standfirst)))
    }
    block(above: 0pt, below: 0pt, line(length: 100%, stroke: 0.5pt + tokens.rule))
  })
  // a whole number of lines, less the leading after the last, so the text after it keeps the baseline: below the head
  // its first line sits where the grid's next line falls, at a column's top or partway down one
  block(width: 100%, above: lead + 3 * g.baseline, below: lead, breakable: false, sticky: true, layout(size => {
    let h = measure(block(width: size.width, head)).height
    block(width: 100%, height: calc.ceil((h + lead) / g.baseline) * g.baseline - lead, head)
  }))
}

#let running-text(title: none, eyebrow: none, standfirst: none, recto: true, restart-notes: true, opener: "page",
                  preset: "blurb-magazine", body) = {
  assert(opener in ("page", "column"), message: "opener: \"page\" or \"column\", not " + repr(opener))
  if opener == "page" { pagebreak(weak: true, to: if recto { parity("odd") } else { none }) }
  // a chapter restarts its notes at 1; a part continuing the same section (restart-notes: false) carries them on
  if restart-notes { note-counter.update(0) }
  if opener == "column" { _column-opener(title, eyebrow, standfirst, preset) } else {
    place(top, float: true, scope: "parent", clearance: 26pt, block(width: 100%)[
      #set par(justify: false, first-line-indent: 0pt)
      #if eyebrow != none { block(below: 10pt, _eyebrow(eyebrow)) }
      #{
        show heading: it => block(below: 12pt, text(font: tokens.display, size: 30pt, weight: "bold",
          top-edge: "cap-height", bottom-edge: "baseline", upper(it.body)))
        { set text(hyphenate: false); heading(level: 1, title) }
      }
      #if standfirst != none {
        block(width: 82%, text(size: 12pt, style: "italic", top-edge: 9.4pt, bottom-edge: -2.6pt,
          par(leading: 4pt, standfirst)))
      }
      #line(length: 100%, stroke: 0.5pt + tokens.rule)
    ])
  }
  body
}

// Something set across both text columns, at the top or the foot of a page (a facsimile, a photograph, a wide table),
// with the text flowing round it.
#let across(at: top, body) = place(at, float: true, scope: "parent", clearance: 18pt, block(width: 100%, body))
