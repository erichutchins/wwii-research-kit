// Part of the wwii-book package (lib.typ imports it).
// A request function: `init` makes it with the book's asset lookup (get) and file loader (load).
#import "../core.typ": *
#import "../components/mark-key.typ": mark-key
#import "../components/unit-key.typ": unit-key

#let make-facsimile(get, load) = {
  // An archive page by its citation, cropped to fractions (x, y, width, height) of the page after turning it
  // `rotate` degrees counter-clockwise. Placed at its own size at 300 dpi, or the column's width if that is
  // narrower; a `width` that pushes it below 300 dpi is reported as a warning.
  let facsimile(cite, crop: none, rotate: 0, width: auto, caption: none, highlight: (), bare: false) = {
    let key = cite + (if crop != none { "@" + crop.map(str).join(",") } else { "" }) + (if rotate != 0 { "@r" + str(rotate) } else { "" })
    _request("facsimile", key, (cite: cite, crop: crop, rotate: rotate))
    let a = get(key)
    let cap = [#caption#if caption != none [. ]#text(fill: tokens.muted)[#if a != none { a.credit } else { cite }]]
    if a == none {
      figure(_pending(cite), caption: cap, kind: image)
    } else {
      layout(size => {
        let natural = a.px.at(0) / 300 * 1in
        let w = if width == auto { calc.min(natural, size.width) } else if type(width) == ratio { size.width * width } else { width }
        let dpi = a.px.at(0) / (w / 1in)
        if dpi < 299 { _warn(cite + ": placed at " + str(calc.round(dpi)) + " dpi") }
        let h = w * a.px.at(1) / a.px.at(0)
        let img = box(width: w, height: h, {
          image(load(a.path), width: w)
          for hl in highlight {
            place(top + left, dx: hl.at(0) * w, dy: hl.at(1) * h, rect(width: hl.at(2) * w, height: hl.at(3) * h,
              stroke: 1.1pt + tokens.accent, fill: tokens.accent.transparentize(88%)))
          }
        })
        if bare { img } else { figure(img, caption: cap) }
      })
    }
  }
  facsimile
}
