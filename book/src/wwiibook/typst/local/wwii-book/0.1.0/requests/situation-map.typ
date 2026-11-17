// Part of the wwii-book package (lib.typ imports it).
// A request function: `init` makes it with the book's asset lookup (get) and file loader (load).
#import "../core.typ": *
#import "../components/mark-key.typ": mark-key
#import "../components/unit-key.typ": unit-key

#let make-situation-map(get, load) = {
  // A slice of a day's 12th Army Group situation map as scanned, with the book's unit ringed in red (ours): the army's
  // own picture of the day, beside our map of the man's path.
  let situation-map(day, box, unit: none, width: 5.45in, caption: none) = {
    let key-id = "plate:" + day + ":" + repr(box) + ":" + repr(unit)
    _request("plate", key-id, (day: day, box: box, unit: unit))
    let a = get(key-id)
    let img = if a == none { _pending("situation map · " + day, height: 4in) } else { image(load(a.path), width: width) }
    if caption == none { img } else { std.figure(img, caption: caption) }
  }
  situation-map
}
