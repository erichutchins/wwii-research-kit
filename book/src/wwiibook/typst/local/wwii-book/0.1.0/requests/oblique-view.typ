// Part of the wwii-book package (lib.typ imports it).
// A request function: `init` makes it with the book's asset lookup (get) and file loader (load).
#import "../core.typ": *
#import "../components/mark-key.typ": mark-key
#import "../components/unit-key.typ": unit-key

#let make-oblique-view(get, load) = {
  // The ground in perspective from behind one side's line: a picture to read beside the plan map, not one to measure
  // on. Heights are exaggerated; the figure says by how much, and so should the caption.
  let oblique-view(box, azimuth: 180, tilt: 30, exaggeration: 4, zoom: 12, data: none, window: none, fronts: (),
                   units: none, highlight: none, labels: (), places: (), width: 5.45in, height: none,
                   caption: none) = {
    let key-id = "oblique:" + repr((box, azimuth, tilt, exaggeration, zoom, data, window, fronts, units, highlight,
                                     labels, places, width, height))
    _request("figure", key-id, (figure: "oblique", box: box, azimuth: azimuth, tilt: tilt, exaggeration: exaggeration,
      zoom: zoom, data: data, window: window, fronts: fronts, units: units, highlight: highlight, labels: labels,
      places: places, width: width / 1in, height: if height == none { none } else { height / 1in }))
    let a = get(key-id)
    let img = if a == none { _pending("oblique view", height: if height == none { 3in } else { height }) } else { image(load(a.path), width: width) }
    let who = if a != none and a.at("units", default: ()).len() > 0 { unit-key(a.units) } else { none }
    if caption == none { img; who } else { std.figure(img, caption: caption); who }
  }
  oblique-view
}
