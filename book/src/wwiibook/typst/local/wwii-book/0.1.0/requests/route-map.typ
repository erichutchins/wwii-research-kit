// Part of the wwii-book package (lib.typ imports it).
// A request function: `init` makes it with the book's asset lookup (get) and file loader (load).
#import "../core.typ": *
#import "../components/mark-key.typ": mark-key
#import "../components/unit-key.typ": unit-key

#let make-route-map(get, load) = {
  // A person's route on one or more panels, from a stops file the family exports (data/route.json): how we know as
  // the line and the dot, how precisely as the ring; fronts are the kit's traced 12th Army Group lines for the days given.
  let route-map(data, panels: (), labels: (), fronts: (), window: none, width: 5.45in, height: none, legs: "full",
                caption: none) = {
    let key-id = "route:" + data + ":" + repr(panels) + repr(labels) + repr(fronts) + repr(window) + repr(width) + repr(height) + legs
    _request("figure", key-id, (figure: "route", data: data, panels: panels, labels: labels, fronts: fronts,
                                window: window, width: width / 1in, height: if height == none { none } else { height / 1in },
                                legs: legs))
    let a = get(key-id)
    let img = if a == none { _pending("route map · " + data, height: 3in) } else { image(load(a.path), width: width) }
    let who = if a != none and a.at("units", default: ()).len() > 0 { unit-key(a.units) } else { none }
    if caption == none { img; who } else { std.figure(img, caption: caption); who }
  }
  route-map
}
