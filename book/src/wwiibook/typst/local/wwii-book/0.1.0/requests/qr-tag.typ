// Part of the wwii-book package (lib.typ imports it).
// A request function: `init` makes it with the book's asset lookup (get) and file loader (load).
#import "../core.typ": *
#import "../components/mark-key.typ": mark-key
#import "../components/unit-key.typ": unit-key

#let make-qr-tag(get, load) = {
  // The QR tag: a Navy date-time group, the position and the citation, typed over a square code.
  let qr-tag(url, dtg: none, position: none, cite: none, label: "Scan for the chart") = {
    _request("qr", "qr:" + url, (url: url))
    let a = get("qr:" + url)
    box(stroke: 0.6pt + tokens.ink, inset: 7pt, width: 1.9in, {
      set par(justify: false, leading: 0.45em)
      set text(font: tokens.typed, size: 7pt)
      if dtg != none [*#dtg* \ ]
      if position != none [#position \ ]
      if cite != none [#text(fill: tokens.muted, cite) \ ]
      v(4pt)
      if a == none { _pending(url, height: 0.9in) } else { image(load(a.path), width: 0.9in) }
      v(3pt)
      text(font: tokens.display, size: 7pt, weight: "semibold", tracking: 0.1em, upper(label))
    })
  }
  qr-tag
}
