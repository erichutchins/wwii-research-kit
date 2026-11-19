// Part of the wwii-book package (lib.typ imports it).
// A request function: `init` makes it with the book's asset lookup (get) and file loader (load).
#import "../core.typ": *
#import "../components/mark-key.typ": mark-key
#import "../components/unit-key.typ": unit-key

#let make-oblique-view(get, load) = {
  // The ground in perspective from behind one side's line: a picture to read beside the plan map, not one to measure
  // on. Heights are exaggerated; the figure says by how much, and so should the caption.
  let oblique-view(box, azimuth: 180, tilt: 30, exaggeration: 4, zoom: 12, data: none, window: none, fronts: (),
                   units: none, highlight: none, labels: (), places: (), rivers: 0, legs: "full", waters: (),
                   moves: (), key: true, width: 5.45in, height: none, caption: none) = {
    // waters: ((name, lon, lat), ...), a river's name set on it. moves: ((from: (lon, lat), to: (lon, lat), of: "us",
    // label: "...", bend: 0.12), ...), movement arrows, approximate. key: the key drawn under the picture (units,
    // command post, front with its date, river, arrows); false leaves the old unit list under the figure.
    let key-id = "oblique:" + repr((box, azimuth, tilt, exaggeration, zoom, data, window, fronts, units, highlight,
                                     labels, places, rivers, legs, waters, moves, key, width, height))
    _request("figure", key-id, (figure: "oblique", box: box, azimuth: azimuth, tilt: tilt, exaggeration: exaggeration,
      zoom: zoom, data: data, window: window, fronts: fronts, units: units, highlight: highlight, labels: labels,
      places: places, rivers: rivers, legs: legs, waters: waters, moves: moves, keyed: key, width: width / 1in, height: if height == none { none } else { height / 1in }))
    let a = get(key-id)
    let img = if a == none { _pending("oblique view", height: if height == none { 3in } else { height }) } else { image(load(a.path), width: width) }
    let who = if a != none and not a.at("keyed", default: false) and a.at("units", default: ()).len() > 0 { unit-key(a.units) } else { none }
    if caption == none { img; who } else { std.figure(img, caption: caption); who }
  }
  oblique-view
}
