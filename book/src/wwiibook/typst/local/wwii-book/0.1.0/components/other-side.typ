// Part of the wwii-book package (lib.typ imports it).
#import "../core.typ": *

// The other side's record, as written: each entry's original (in its own script and face) beside our translation,
// with the record's time as written and its page. `entries`: (record, local, ship, original, translation, cite, href),
// as an engagement's Japanese events carry them (maneuvering.py hands them on). The translation is ours; the
// original is the record's, so it is never abridged here.
#let _jacar = regex("^jacar:(\S+)\s+p(\d+)$")

#let other-side-source(cite, href) = {
  let m = if cite == none { none } else { cite.match(_jacar) }
  let words = if m != none [JACAR #m.captures.at(0), p. #str(int(m.captures.at(1)))] else { raw(cite) }
  if href != none { link(href, words) } else { words }
}

#let other-side(entries, heading: [The other side's record], intro: none) = {
  block(width: 100%, breakable: true, inset: (x: 8pt, y: 7pt), fill: tokens.other.lighten(40%),
        stroke: (left: 1.6pt + tokens.other-ink), {
    text(font: tokens.display, weight: "semibold", size: 8.5pt, heading)
    if intro != none { block(above: 3pt, below: 5pt, text(size: 7.6pt, fill: tokens.muted, intro)) }
    for e in entries {
      // the record's number and time as written, the original, then our translation under it and its page
      block(above: 8pt, below: 0pt, breakable: true, {
        text(font: tokens.display, weight: "semibold", size: 7.6pt)[#e.record#if e.local != none [ · #e.local]]
        if e.original != none {
          block(above: 3pt, below: 3pt, {
            set text(font: tokens.ja, size: 7.8pt, lang: "ja")
            set par(justify: false, leading: 0.62em)
            e.original
          })
        }
        set text(size: 7.6pt)
        set par(justify: false, leading: 0.5em)
        e.translation
        h(4pt)
        text(size: 6.8pt, fill: tokens.muted, other-side-source(e.cite, e.href))
      })
    }
  })
}
