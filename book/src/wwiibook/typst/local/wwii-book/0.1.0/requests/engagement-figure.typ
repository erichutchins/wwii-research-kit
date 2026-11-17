// Part of the wwii-book package (lib.typ imports it).
// A request function: `init` makes it with the book's asset lookup (get) and file loader (load).
#import "../core.typ": *
#import "../components/mark-key.typ": mark-key
#import "../components/unit-key.typ": unit-key

#let make-engagement-figure(get, load) = {
  // An engagement's map or timeline, drawn from the kit's engagements/<id>/engagement.json. Both number the same
  // marks the same way; `key: true` sets the numbered marks, with their citations, under the figure.
  let engagement-figure(id, figure: "map", width: 5.5in, box: none, window: none, follow: none, caption: none,
                        key: false) = {
    let key-id = "figure:" + figure + ":" + id + ":" + repr(width) + ":" + repr(box) + ":" + repr(window) + ":" + repr(follow)
    _request("figure", key-id, (figure: figure, engagement: id, width: width / 1in, box: box, window: window,
                                follow: follow))
    let a = get(key-id)
    if a == none {
      std.figure(_pending(figure + " · " + id, height: 2in), caption: caption, kind: image)
    } else {
      std.figure(image(load(a.path), width: width), caption: caption)
      if key { mark-key(a) }
    }
  }
  engagement-figure
}
