// Part of the wwii-book package (lib.typ imports it).
// A request function: `init` makes it with the book's asset lookup (get) and file loader (load).
#import "../core.typ": *
#import "../components/mark-key.typ": mark-key
#import "../components/unit-key.typ": unit-key

#let make-aircraft-card(get, load) = {
  // An aircraft card: a photograph of the type (book/aircraft/photos.yml; one with a face only once approved), its
  // silhouettes, and the Allies' recognition manual's figures for it (records/air/aircraft.yml), as printed and cited.
  let aircraft-card(kind, photo: 0, width: 4.4in, caption: none) = {
    let key-id = "aircraft:" + repr((kind, photo, width))
    _request("aircraft", key-id, (type: kind, photo: photo, width: width / 1in))
    let a = get(key-id)
    let img = if a == none { _pending("aircraft · " + kind, height: 3in) } else { image(load(a.path), width: width) }
    if caption == none { img } else { std.figure(img, caption: caption) }
  }
  aircraft-card
}
