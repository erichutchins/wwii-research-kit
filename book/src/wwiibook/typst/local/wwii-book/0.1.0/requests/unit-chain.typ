// Part of the wwii-book package (lib.typ imports it).
// A request function: `init` makes it with the book's asset lookup (get) and file loader (load).
#import "../core.typ": *
#import "../components/mark-key.typ": mark-key
#import "../components/unit-key.typ": unit-key

#let make-unit-chain(get, load) = {
  // A unit's chain of command from the kit's relations (army group to company), every link dated and cited:
  // view "timeline" over months (start, end), "ladder" on one day (on). `marks`: dated lines ((date:, words:)).
  let unit-chain(unit, view: "timeline", start: none, end: none, on: none, title: none, marks: (), width: 9.6in,
                 caption: none) = {
    let key-id = "chain:" + repr((unit, view, start, end, on, title, marks, width))
    _request("chain", key-id, (unit: unit, view: view, start: start, end: end, on: on, title: title, marks: marks,
      width: width / 1in))
    let a = get(key-id)
    let img = if a == none { _pending("chain · " + unit, height: 2in) } else { image(load(a.path), width: width) }
    if caption == none { img } else { std.figure(img, caption: caption) }
  }
  unit-chain
}
