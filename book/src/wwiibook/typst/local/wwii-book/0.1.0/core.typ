// The wwii-book package's core: the tokens, the page, the type, and the request plumbing every template uses.

// The palette, with what to expect of each in print. Soft-proofed on 19 Nov 2026 against Blurb's ICC profile (CMYK,
// X-Rite, March 2010; relative colorimetric, black point compensation) with `wwii-book softproof <profile.icc>`;
// ΔE00 is the shift from screen to print (under 2 hard to see, 2-5 visible side by side):
//   ink #000000            the press's darkest black prints a touch lighter than screen black (L* 9, ΔE00 5.6): normal
//                          written as CMYK 0/0/0/100, so text and rules reach the press as black ink alone (Blurb:
//                          "100% Black ink" for text), never as an RGB black the press would build from four inks
//   paper #fbfaf6          a warm ground for figures; it prints as a faint tint on white stock (ΔE00 0.8), never as the
//                          paper's own colour
//   hit #c8323c            red for hits only; holds well (ΔE00 1.6)
//   accent #a3241b         shifts a little lighter and warmer (ΔE00 3.4)
//   boat 1 #2a6fc9         loses some saturation (#3b6fb3 in print, ΔE00 2.3)
//   boat 2 #008f78         holds (ΔE00 1.1)
//   boat 3 #6a3a9e         a little greyer, not darker (lightness unchanged, ΔE00 3.8)
//   cta #c98a1b / cta-ink #8a5a0b   the call to action (where the book sends a reader to the kit's site): amber for
//                          marks and rules (ΔE00 2.0), dark amber for words (prints a little lighter, ΔE00 5.6)
//   the hit red, the three boats and the amber stay well apart in print: the closest pair is boat 1 and boat 3
//   (ΔE00 22.8)
#let tokens = (
  ink: cmyk(0%, 0%, 0%, 100%), muted: rgb("#5d675b"), rule: rgb("#c4cbbf"), accent: rgb("#a3241b"),
  other: rgb("#e4e7e9"), other-ink: rgb("#4d5963"), paper: rgb("#fbfaf6"), band: rgb("#171c18"), band-ink: rgb("#ecede6"),
  cta: rgb("#c98a1b"), cta-ink: rgb("#8a5a0b"),
  // Typst files IBM Plex Sans Condensed under the family "IBM Plex Sans", condensed
  display: ("IBM Plex Sans", "IBM Plex Sans Condensed", "Shippori Mincho", "Noto Serif JP Symbols", "Arial Narrow"),
  // every face falls back to Shippori Mincho for Japanese (a record's original quoted in a note or a key), then to
  // a subset of Noto Serif JP for the few marks the originals use that Shippori lacks (✓ ─ ｜ ∠, half-width kana)
  // Libertinus Serif: built into Typst (SIL OFL), so present wherever Typst runs, with no font file to ship
  body: ("Libertinus Serif", "Shippori Mincho", "Noto Serif JP Symbols", "Georgia"),
  typed: ("Courier Prime", "Shippori Mincho", "Noto Serif JP Symbols", "Courier New"),
  // the typewriter for effect, where a record's look matters more than its reading (no degree sign: Courier Prime
  // stands in for it)
  typed-effect: ("TT2020 Style E", "Courier Prime", "Shippori Mincho", "Noto Serif JP Symbols"),
  ja: ("Shippori Mincho", "Noto Serif JP Symbols", "Noto Serif JP"),   // Japanese: the original beside the translation
)

// The man's name and the book's title, for the running heads; set by `book`.
#let _book-meta = state("wwii-book-meta", (name: "", title: ""))

// The printers' page geometries. `trim` is the finished page; `bleed` is added outside it on the edges the printer
// trims (none at the binding, where the pages are bound); `safe` is how far critical content stays inside the trim;
// `margin` is the book's own text frame, measured from the trim. "draft" is the examples' 7 × 10 in page with no
// bleed. "blurb-magazine": Blurb's Premium Magazine, 8.5 × 11 in, softcover, from its PDF-to-Book specifications
// (17 Nov 2026): the page PDF 621 × 810 pt, bleed 9 pt top, bottom and outside, safe 18 pt from the outer edges and
// 45 pt from the binding (its page gives 36 in one place and 45 in another: the larger is kept).
#let presets = (
  draft: (trim: (width: 7in, height: 10in), bleed: (top: 0pt, bottom: 0pt, outside: 0pt),
          safe: (edge: 0pt, binding: 0pt), margin: (inside: 0.85in, outside: 0.7in, top: 0.85in, bottom: 0.9in)),
  blurb-magazine: (trim: (width: 612pt, height: 792pt), bleed: (top: 9pt, bottom: 9pt, outside: 9pt),
                   safe: (edge: 18pt, binding: 45pt),
                   margin: (inside: 0.8in, outside: 0.65in, top: 0.8in, bottom: 0.85in)),
)

// The page in use, for templates that place things to the trim or the bleed (a full-bleed photograph, an endpaper).
#let _book-page = state("wwii-book-page", presets.draft)

// The page: a preset's trim plus its bleed, the book's margins outside the safe area, running heads alternating by
// side (the book's man on the left, the chapter on the right), none on a page that opens a chapter, folios outside.
#let book(name: "", title: "", preset: "draft", trim: none, body) = {
  let g = presets.at(preset)
  if trim != none { g.trim = trim }
  _book-meta.update((name: name, title: title))
  _book-page.update(g)
  let m = g.margin
  set page(width: g.trim.width + g.bleed.outside, height: g.trim.height + g.bleed.top + g.bleed.bottom, binding: left,
           margin: (inside: calc.max(m.inside, g.safe.binding), outside: calc.max(m.outside, g.safe.edge) + g.bleed.outside,
                    top: calc.max(m.top, g.safe.edge) + g.bleed.top, bottom: calc.max(m.bottom, g.safe.edge) + g.bleed.bottom),
    header: context {
      let p = here().page()
      let openers = query(heading.where(level: 1)).filter(h => h.location().page() == p)
      if openers.len() > 0 { return }
      let before = query(heading.where(level: 1).before(here()))
      let chapter = if before.len() > 0 { before.last().body } else { [] }
      set text(font: tokens.display, size: 7.5pt, tracking: 0.14em, fill: tokens.muted)
      if calc.even(p) { upper(_book-meta.get().name) } else { align(right, upper(chapter)) }
    },
    footer: context {
      let p = here().page()
      set text(font: tokens.display, size: 8.5pt, fill: tokens.muted)
      align(if calc.even(p) { left } else { right }, str(p))
    })
  set text(font: tokens.body, size: 10.2pt, fill: tokens.ink, lang: "en", region: "gb", hyphenate: true)
  set par(justify: true, leading: 0.68em, spacing: 0.68em, first-line-indent: (amount: 1.1em, all: false))
  // raw text (a citation key shown as it stands) in the typewriter face, not Typst's default monospace
  show raw: set text(font: tokens.typed)
  show heading: set text(font: tokens.display, weight: "bold")
  show heading.where(level: 2): it => block(above: 1.5em, below: 0.7em,
    text(size: 10.5pt, weight: "bold", tracking: 0.12em, upper(it.body)))
  set footnote.entry(separator: line(length: 25%, stroke: 0.5pt + tokens.rule), gap: 0.4em)
  show footnote.entry: set text(size: 7.6pt)
  show figure.caption: set text(size: 8pt)
  show figure.caption: set align(left)
  set figure(gap: 0.6em, supplement: none, numbering: none)
  body
}

#let eyebrow(body) = text(font: tokens.display, size: 8pt, weight: "semibold", tracking: 0.12em, fill: tokens.muted, upper(body))

#let typed(body) = text(font: tokens.typed, size: 0.92em, body)

#let _pending(label, height: 1.4in) = block(width: 100%, height: height, inset: 8pt,
  stroke: (paint: tokens.muted, thickness: 0.6pt, dash: "dashed"),
  align(center + horizon, text(size: 8pt, fill: tokens.muted)[pending: #raw(label)]))

#let _request(kind, key, args) = [#metadata((kind: kind, key: key, ..args)) <wwii-request>]
#let _warn(message) = [#metadata((message: message)) <wwii-warning>]
