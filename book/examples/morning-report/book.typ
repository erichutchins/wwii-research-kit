// A morning-report page by its citation: the page is fetched from the National Archives (or the kit's scan cache),
// cropped to its heading, and set at its own size with its credit line.
//   uv run wwii-book build examples/morning-report/book.typ
#import "@local/wwii-book:0.1.0": *
#let wwii = init(assets: json("build/assets.json"), load: p => read(p, encoding: none))
#show: book

#eyebrow[14 April 1944 · the North Atlantic]
= Aboard transport

The battery's morning report for 14 April gives no place. Its station is a ship at sea, and the ship is not named.

#(wwii.facsimile)("rg64-469722323/p0712", crop: (0, 0, 1, 0.24),
  caption: [Morning report, HQ Battery, 128th AAA Gun Battalion, 14 April 1944: "Aboard transport"])
