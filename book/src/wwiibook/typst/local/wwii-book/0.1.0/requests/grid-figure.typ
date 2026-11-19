// Part of the wwii-book package (lib.typ imports it).
// A request function: `init` makes it with the book's asset lookup (get) and file loader (load).
#import "../core.typ": *

#let make-grid-figure(get, load) = {
  // The grid section's figures (gridref.py, book/grids/cases.yml): view "zones", the grids the records use over
  // Europe and North Africa with their lettered 100 km squares; view "ladder", one worked case's reference read down
  // from its 100 km square to the point, on the period sheet.
  let grid-figure(view: "zones", case: none, width: 7.2in, columns: 2, caption: none) = {
    let key-id = "grid:" + repr((view, case, width, columns))
    _request("grid", key-id, (view: view, case: case, width: width / 1in, columns: columns))
    let a = get(key-id)
    let img = if a == none { _pending("grid · " + view, height: 3in) } else { image(load(a.path), width: width) }
    if caption == none { img } else { std.figure(img, caption: caption) }
  }
  grid-figure
}
