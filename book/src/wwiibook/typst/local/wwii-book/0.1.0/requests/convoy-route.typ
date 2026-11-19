// Part of the wwii-book package (lib.typ imports it).
// A request function: `init` makes it with the book's asset lookup (get) and file loader (load).
#import "../core.typ": *
#import "../components/mark-key.typ": mark-key

#let make-convoy-route(get, load) = {
  // A convoy's whole voyage beside the engagement (the site's overview, for print): on the left, or above when the
  // route and the map are both long and wide, the convoy's lane through reference/lanes/lanes.yml with its ports and
  // dated stops and a box where the engagement was; beside it the engagement map drawn to that box, two lines joining
  // them. `box` replaces the engagement's own; `key: true` sets the map's numbered marks, with their citations, and a
  // line giving the lane's basis (its assumed waypoints) and the voyage's sources; `key: "only"` sets the key alone,
  // for a figure floated across the columns whose key follows in the text (a float can't break across pages).
  let convoy-route(engagement, width: 7in, height: none, box: none, layout: "auto", caption: none, key: true) = {
    let key-id = "convoy-route:" + repr((engagement, width, height, box, layout))
    _request("convoy-route", key-id, (engagement: engagement, width: width / 1in,
      height: if height == none { none } else { height / 1in }, box: box, layout: layout))
    let a = get(key-id)
    if a == none {
      if key == "only" { return }
      std.figure(_pending("convoy route · " + engagement, height: if height == none { 2.6in } else { height }),
                 caption: caption, kind: image)
    } else {
      if key != "only" { std.figure(image(load(a.path), width: width), caption: caption) }
      if key != false {
        mark-key(a)
        linebreak()
        text(size: 6.5pt, fill: tokens.muted)[The overview: #a.route_line; #a.assumptions. #a.voyage_line.]
      }
    }
  }
  convoy-route
}
