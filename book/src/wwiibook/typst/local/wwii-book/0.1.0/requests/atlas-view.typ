// Part of the wwii-book package (lib.typ imports it).
// A request function: `init` makes it with the book's asset lookup (get) and file loader (load).
#import "../core.typ": *
#import "../components/mark-key.typ": mark-key
#import "../components/unit-key.typ": unit-key

#let make-atlas-view(get, load) = {
  // An atlas extent's coordinated pair (book/atlas/<extent>/extent.yml): the panorama from above, the oblique view
  // of the same ground, both in one projected frame. `highlight` rings a division (its id in the day's units file).
  let atlas-view(extent, view: "panorama", width: 9.6in, highlight: none, highlight-words: none, azimuth: none,
                 tilt: none, exaggeration: none, caption: none) = {
    let key-id = "atlas:" + repr((extent, view, width, highlight, azimuth, tilt, exaggeration))
    _request("atlas", key-id, (extent: extent, view: view, width: width / 1in, highlight: highlight,
      highlight_words: highlight-words, azimuth: azimuth, tilt: tilt, exaggeration: exaggeration))
    let a = get(key-id)
    let img = if a == none { _pending(view + " · " + extent, height: 4in) } else { image(load(a.path), width: width) }
    if caption == none { img } else { std.figure(img, caption: caption) }
  }
  atlas-view
}
