// Part of the wwii-book package (lib.typ imports it).
// A request function: `init` makes it with the book's asset lookup (get) and file loader (load).
#import "../core.typ": *

// How a torpedo was aimed (fire_control.py), every value the kit's site/engage.js under Node:
//   view: "triangle"  an attack's fire-control triangle, north up, to scale (needs engagement and attack)
//   view: "aob"       the same shot at other angles on the bow, a small multiple (engagement, attack, aobs)
//   view: "tdc"       the Torpedo Data Computer Mark 3 as a diagram, its dials named as its manual names them
// `key: true` (the triangle) sets under it the sheet's numbers as typed beside what follows from them, what is
// assumed, and the pages.
#let make-fire-control(get, load) = {
  let fire-control(view, engagement: none, attack: none, boat: none, aobs: none, width: 5.5in, caption: none,
                   key: false) = {
    let key-id = ("firecontrol:" + view + ":" + repr(engagement) + ":" + repr(attack) + ":" + repr(boat) + ":"
      + repr(aobs) + ":" + repr(width))
    _request("firecontrol", key-id, (view: view, engagement: engagement, attack: attack, boat: boat, aobs: aobs,
                                     width: width / 1in))
    let a = get(key-id)
    if a == none {
      std.figure(_pending("fire control · " + view + if attack != none { " · " + attack } else { "" },
        height: width * 0.6), caption: caption, kind: image)
    } else {
      std.figure(image(load(a.path), width: width), caption: caption)
      if key and view == "triangle" {
        set text(size: 7pt)
        set par(justify: false, first-line-indent: 0pt)
        let head(h) = text(font: tokens.display, weight: "semibold", style: "italic", h)
        table(
          columns: (auto, auto, auto, auto, 1fr),
          stroke: (x, y) => if y == 0 { (bottom: 0.7pt + tokens.ink) } else { (bottom: 0.25pt + tokens.rule) },
          inset: (x: 3pt, y: 2pt),
          table.header(..("Tube", "Gyro, typed", "Torpedo course", "Track, typed", "Track, from course and gyro")
            .map(head)),
          ..a.torpedoes.map(t => (typed(t.tube), typed(t.gyro), [#calc.round(t.course)°], typed(t.track),
                                  [#t.derived_track])).flatten(),
        )
        text(size: 6.5pt, fill: tokens.muted)[
          #if a.disagree.len() > 0 [*Not as typed.* #a.disagree.join("; "). ]
          *Assumed:* #a.assumed.join("; "). *Source:* the attack data sheet, #a.cites.map(typed).join(", ").]
      }
    }
  }
  fire-control
}
