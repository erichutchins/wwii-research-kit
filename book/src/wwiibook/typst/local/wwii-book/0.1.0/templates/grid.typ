// Part of the wwii-book package (lib.typ imports it).
#import "../core.typ": *
#import "../components/note.typ": _notes-on, _notes-mode, _note-sources, _side-notes, endnotes, note-counter

// ---------------------------------------------------------------- the grid
// The magazine page's grid, inside Blurb's safe area (core.typ's `blurb-magazine`: trim 612 x 792 pt, bleed 9 pt top,
// bottom and outside, safe 18 pt from the outer edges and 45 pt from the binding). Measured from the trim:
//
//   inside 54 pt | two text columns of 194 pt, gutter 12 pt | 12 pt | the note column, 110 pt | outside 36 pt
//   top 54 pt to the first baseline's line, 52 lines of 13 pt, bottom 62 pt
//
// The text is Libertinus Serif at 10 pt on a 13 pt baseline, heads IBM Plex Sans Condensed Bold; notes 7.2 pt
// on 9.75 pt (three lines of notes to four of text). The outer column is the right on a recto (odd page), the left
// on a verso. Running heads sit over the whole live area (text and notes): the part on a verso, the chapter on a
// recto, none on a page that opens a chapter; folios at the foot, outside.
//
// Notes beside the text or at the end: `on-grid.with(notes: "end")` (or `--input notes=end`, which overrides it, for
// a proof both ways) gives the note column up. The text's two columns then run across the whole live area, inside
// 54 pt to outside 36 pt (two columns of 252 pt, gutter 18 pt), the calls stay in the text, and the notes are set
// at the section's end (`endnotes`, which `section-sources` sets before its sources, and which closes the section
// in any case), numbered as in the text. A figure written to reach into the note column the grid's way (moved
// outward by the column and its gap on a verso, `-note-reach`, and widened by them, `100% + note-reach`: a
// section's `outer`) is set at the full measure, which is the same span.
#let grids = (
  blurb-magazine: (inside: 54pt, outside: 36pt, top: 54pt, bottom: 62pt, note: 110pt, note-gap: 12pt, gutter: 12pt,
                   end-gutter: 18pt, size: 10pt, baseline: 13pt, head: 20pt, foot: 22pt),
)

// How far a figure reaches out of the text columns into the note column: the column and its gap (122 pt).
#let note-reach(preset: "blurb-magazine") = { let g = grids.at(preset); g.note + g.note-gap }

// The part, for the verso's running head: `#part-title[The Cotentin]` (it draws nothing).
#let _part = state("wwii-grid-part", none)
#let part-title(body) = _part.update(body)

// The text's line: a fixed 9.5 pt line box (its top and bottom edges fixed, so every face and size sits alike) and
// 3.5 pt of leading make the 13 pt baseline.
#let _edges(size) = (top-edge: size * 0.78, bottom-edge: -size * 0.22)

#let on-grid(preset: "blurb-magazine", sources: (:), notes: "side", body) = {
  let p = presets.at(preset)
  let g = grids.at(preset)
  assert(g.inside >= p.safe.binding and g.outside >= p.safe.edge, message: "the grid's margins are inside the safe area")
  let mode = sys.inputs.at("notes", default: notes)
  assert(mode in ("side", "end"), message: "notes: \"side\" or \"end\", not " + repr(mode))
  let side = mode == "side"
  let reach = note-reach(preset: preset)
  let notes-w = if side { reach } else { 0pt }      // the note column and its gap, where there is one
  let lead = g.baseline - g.size
  _notes-on.update(true)
  _notes-mode.update(mode)
  _note-sources.update(sources)
  set page(
    margin: (inside: g.inside, outside: g.outside + notes-w + p.bleed.outside,
             top: g.top + p.bleed.top, bottom: g.bottom + p.bleed.bottom),
    columns: 2, header-ascent: g.head, footer-descent: g.foot,
    header: context {
      if query(heading.where(level: 1)).any(h => h.location().page() == here().page()) { return }
      let recto = recto-at(here().page())
      let before = query(heading.where(level: 1).before(here()))
      let chapter = if before.len() > 0 { before.last().body } else { [] }
      set text(font: tokens.display, size: 7.5pt, tracking: 0.14em, fill: tokens.muted, top-edge: "cap-height",
               bottom-edge: "baseline")
      let words = if recto { upper(chapter) } else { upper(_part.get()) }
      move(dx: if recto { 0pt } else { -notes-w }, box(width: 100% + notes-w,
        stack(spacing: 4pt, align(if recto { right } else { left }, words), line(length: 100%, stroke: 0.4pt + tokens.rule))))
    },
    footer: context {
      let n = folio(here().page())
      let recto = calc.odd(n)
      set text(font: tokens.display, size: 8.5pt, weight: "medium", fill: tokens.muted)
      move(dx: if recto { 0pt } else { -notes-w }, box(width: 100% + notes-w,
        align(if recto { right } else { left }, str(n))))
    },
    foreground: if side { context {
      let recto = recto-at(here().page())
      // the trim's left edge is the binding on a recto and the bleed's inner edge on a verso
      let x = if recto { p.trim.width - g.outside - g.note } else { p.bleed.outside + g.outside }
      _side-notes(x: x, width: g.note, head: p.bleed.top + g.top,
                  foot: p.bleed.top + p.trim.height - g.bottom, gap: g.baseline * 0.375)
    } })
  set columns(gutter: if side { g.gutter } else { g.end-gutter })
  // with no note column, a figure that reached into it is set at the full measure: the same span
  show move.where(dx: -reach): it => if side { it } else { it.body }
  show box.where(width: 100% + reach): it => if side { it } else { box(width: 100%, it.body) }
  set text(font: tokens.body, size: g.size, .._edges(g.size), number-type: "old-style")
  set par(justify: true, leading: lead, spacing: lead, first-line-indent: (amount: 1.2em, all: false),
          linebreaks: "optimized")
  show heading.where(level: 2): it => block(above: g.baseline + lead, below: lead, sticky: true,
    text(font: tokens.display, size: 9pt, weight: "semibold", tracking: 0.12em, .._edges(g.size), upper(it.body)))
  body
  endnotes()      // the end notes not set yet: none once `section-sources` has set them, none beside the text
}
