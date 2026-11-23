// Part of the wwii-book package (lib.typ imports it).
// A request function: `init` makes it with the book's asset lookup (get) and file loader (load).
#import "../core.typ": *

#let make-silhouette(get, load) = {
  // A ship's recognition silhouette from the library (records/silhouettes), solid, `height` tall at its masthead:
  // `(wwii.silhouette)("buckley", height: 14pt)`. Its asset carries the class's name and the plate it was traced from.
  let silhouette(ship, height: 14pt, fill: none) = {
    let key = "silhouette:" + ship + if fill != none { ":" + fill.to-hex() } else { "" }
    _request("silhouette", key, (ship: ship, ..if fill != none { (fill: fill.to-hex()) }))
    let a = get(key)
    if a == none { box(width: 6 * height, height: height, stroke: (paint: tokens.muted, thickness: 0.5pt, dash: "dashed")) }
    else { box(image(load(a.path), height: height)) }
  }
  silhouette
}
