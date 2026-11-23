// Part of the wwii-book package (lib.typ imports it).
// A request function: `init` makes it with the book's asset lookup (get) and file loader (load).
#import "../core.typ": *
#import "../components/mark-key.typ": mark-key
#import "../components/unit-key.typ": unit-key

#let make-picture(get, load) = {
  // A picture already in the scan cache (a photograph, a crop), by its path under the cache: placed as given,
  // or cropped to fill a box (`height` with fit "cover").
  let picture(path, width: 100%, height: auto, fit: "cover") = {
    _request("picture", "picture:" + path, (path: path))
    let a = get("picture:" + path)
    if a == none { _pending(path, height: if height == auto { 2in } else { height }) }
    else {
      // one photo treatment across the book: a photograph or a scan (JPEG) in a hairline frame, so a pale sky or a
      // page's margin keeps its edge on white paper; a drawing or a badge (PNG, SVG) unframed
      let img = image(load(a.path), width: width, height: height, fit: fit)
      if lower(a.path).ends-with(".jpg") or lower(a.path).ends-with(".jpeg") {
        box(stroke: 0.3pt + tokens.ink, img)
      } else { img }
    }
  }
  picture
}
