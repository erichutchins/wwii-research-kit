// Part of the wwii-book package (lib.typ imports it).
#import "../core.typ": *
#import "note.typ": _notes-on, source-line

// ---------------------------------------------------------------- captions
// A photograph's own caption (as captioned at the time, quoted) is kept apart from ours (what it shows, what we
// infer, what it does not tell us). The credit says whose it is ("drawn for this research" for our figures); `cite`
// names the archive page it shows (a facsimile) and is set as its source line, resolved to that page. On the grid
// (`on-grid`) the caption is set on the notes' line, the credit in the display face.
#let _photo-caption-draft(original, ours, credit, cite) = {
  set par(justify: false, first-line-indent: 0pt, leading: 0.5em)
  set text(size: 8pt)
  if original != none {
    block(below: 0.45em)[#text(font: tokens.display, size: 6.5pt, weight: "semibold", tracking: 0.12em,
      fill: tokens.muted, upper[As captioned at the time]) \ #text(style: "italic")["#original"]]
  }
  if ours != none { block(below: 0.45em, ours) }
  if credit != none { text(size: 7pt, fill: tokens.muted, credit) }
  if cite != none { block(above: 0.3em, text(size: 7pt, fill: tokens.muted, source-line(cite))) }
}

#let _photo-caption-grid(original, ours, credit, cite) = block(above: 6.5pt, below: 0pt, {
  set par(justify: false, first-line-indent: 0pt, leading: 2.55pt, spacing: 4.875pt)
  set text(size: 7.6pt, top-edge: 5.9pt, bottom-edge: -1.7pt)
  if original != none {
    [#text(font: tokens.display, size: 6.5pt, weight: "semibold", tracking: 0.12em, fill: tokens.muted,
      upper[As captioned at the time]) #text(style: "italic")["#original"]]
    parbreak()
  }
  if ours != none { ours; parbreak() }
  if credit != none or cite != none {
    text(font: tokens.display, size: 6.8pt, weight: "medium", tracking: 0.04em, fill: tokens.muted)[#credit#if credit != none and cite != none [ · ]#if cite != none { source-line(cite) }]
  }
})

#let photo-caption(original: none, ours: none, credit: none, cite: none) = context {
  if _notes-on.get() { _photo-caption-grid(original, ours, credit, cite) } else { _photo-caption-draft(original, ours, credit, cite) }
}
