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

#let make-punch-card(get, load) = {
  // The QR code as a punched card (1940s tabulating stock) that still scans: up to three typed lines at its head (a
  // ship, a convoy, a date-time group), the code's modules punched as slots. Links only to the kit's public pages.
  let punch-card(url, lines: (), caption: "Scan for the engagement", width: 100%) = {
    let key = "punch:" + url + ":" + lines.join("|") + ":" + caption
    _request("qr", key, (url: url, style: "punch", lines: lines, caption: caption))
    let a = get(key)
    if a == none { _pending("punch card · " + url, height: width * 0.45) } else { image(load(a.path), width: width) }
  }
  punch-card
}
