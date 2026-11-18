// Part of the wwii-book package (lib.typ imports it).
// A request function: `init` makes it with the book's asset lookup (get) and file loader (load).
#import "../core.typ": *

// An attack on the Navy's maneuvering board: own ship at the centre, each target where the kit's fire-control
// solution (site/engage.js) puts it at firing, each torpedo on own course + its typed gyro. `key: true` sets, under
// the board, the sheet's numbers as typed beside what follows from them, what is assumed, and the pages.
#let make-maneuvering-board(get, load) = {
  let maneuvering-board(engagement, attacks, boat: none, width: 5.5in, sizes: none, caption: none, key: true) = {
    let key-id = "board:" + engagement + ":" + attacks.join("+") + ":" + repr(boat) + ":" + repr(width) + ":" + repr(sizes)
    _request("board", key-id, (engagement: engagement, attacks: attacks, boat: boat, width: width / 1in, sizes: sizes))
    let a = get(key-id)
    if a == none {
      std.figure(_pending("maneuvering board · " + attacks.join(", "), height: width), caption: caption, kind: image)
    } else {
      std.figure(image(load(a.path), width: width), caption: caption)
      if key {
        set text(size: 7pt)
        set par(justify: false)
        let head(h) = text(font: tokens.display, weight: "semibold", style: "italic", h)
        table(
          columns: (auto, auto, auto, auto, auto, auto, 1fr),
          stroke: (x, y) => if y == 0 { (bottom: 0.7pt + tokens.ink) } else { (bottom: 0.25pt + tokens.rule) },
          inset: (x: 3pt, y: 2.2pt),
          table.header(..("", "Target", "Range", "Bearing", "Angle on the bow", "Lead", "Track").map(head)),
          ..a.targets.map(t => (
            text(weight: "bold", t.letter), [#t.attack: course #typed[#str(t.course)]°, #typed[#str(t.speed)] kn],
            typed[#str(t.range) yds], [#calc.round(t.bearing)° #text(fill: tokens.muted)[derived]],
            [#calc.abs(calc.round(t.aob))° #if t.aob >= 0 [starboard] else [port]],
            [#calc.abs(calc.round(t.lead, digits: 1))°],
            [#calc.round(t.track)#t.side at the point of aim (typed #typed[#t.typed_track])]),
          ).flatten(),
        )
        v(2pt)
        table(
          columns: (auto, auto, auto, auto, auto, auto),
          stroke: (x, y) => if y == 0 { (bottom: 0.7pt + tokens.ink) } else { (bottom: 0.25pt + tokens.rule) },
          inset: (x: 3pt, y: 2pt),
          table.header(..("Tube", "Gyro, typed", "Torpedo course", "Track, typed", "Track, derived", "Run to the target").map(head)),
          ..a.torpedoes.map(t => (typed(t.tube), typed(t.gyro), [#t.course°], typed(t.track), [#t.derived_track],
                                  [about #t.run_yd yds])).flatten(),
        )
        text(size: 6.5pt, fill: tokens.muted)[
          #if a.disagree.len() > 0 [*Not as typed.* #a.disagree.join("; "). ]
          *Assumed:* #a.assumed.join("; "). *Sources:* the attack data sheets, #a.cites.map(typed).join(", ").]
      }
    }
  }
  maneuvering-board
}
