// Part of the wwii-book package (lib.typ imports it).
#import "../core.typ": *

// One row per torpedo, from a patrol's attacks.csv as records() returns it.
#let torpedo-ledger(rows) = {
  set text(font: tokens.typed, size: 7.5pt)
  let result(r) = if r.hit == "" [—] else if r.hit == "Hit" [*Hit*] else [#r.hit]
  let heads = ("Attack", "Date", "Time", "Tube", "Torpedo", "Gyro", "Depth set", "Result")
  table(
    columns: 8,
    stroke: (x, y) => if y == 0 { (bottom: 0.8pt + tokens.ink) } else { (bottom: 0.3pt + tokens.rule) },
    inset: (x: 4pt, y: 3pt),
    table.header(..heads.map(h => text(font: tokens.display, weight: "semibold", size: 8pt, upper(h)))),
    ..rows.map(r => (r.attack, r.date, r.time + " " + r.zone, r.tube, "Mk " + r.torpedo, r.gyro, r.depth_set + " ft",
                     result(r))).flatten(),
  )
}
