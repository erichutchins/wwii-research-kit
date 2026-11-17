// An illustrated atlas's coordinated pair: one geography (book/atlas/la-haye-du-puits/extent.yml) drawn from above and
// in perspective, in one projected frame (Lambert-93), with the army group's own map of the day beside it.
//   uv run wwii-book build examples/atlas-la-haye/book.typ
#import "@local/wwii-book:0.1.0": *
#let wwii = init(assets: json("build/assets.json"), load: p => read(p, encoding: none))
#show: book
#set page(width: 11in, height: 8.5in, margin: (x: 0.7in, top: 0.55in, bottom: 0.5in))

= La Haye-du-Puits
#eyebrow[8–11 July 1944 · the Cotentin]

#(wwii.atlas-view)("la-haye-du-puits", view: "panorama", width: 9.6in,
  caption: [The front on 11 July 1944 (heavy) and on 7 July (dashed), and the divisions where HQ Twelfth Army Group's
  situation map for 2400 hours on 11 July placed their symbols, which is the army group's picture of the day, not
  the ground each held. The roads and railways are those IGN's 1:50,000 prints (SCAN 50, 1950 series; sheets of
  1947 to 1959 editions here), on their modern alignment where a modern road runs along the sheet's line and on
  the sheet's own line where none does, joined where the sheet's ink breaks off: an illustration of the period
  network, not anyone's route. Rivers are today's courses (OpenStreetMap).
  Terrain from Copernicus GLO-30; the tinted low ground lies under 6 m, the marshes' ground, whose 1944 flooding
  the records describe, not the model.])

#pagebreak()

#(wwii.atlas-view)("la-haye-du-puits", view: "oblique", width: 9.6in,
  caption: [The same ground, extent, front and divisions, looking east from above the sea: the American divisions
  on the left (north), the German on the right (south), Mont Castre between them beyond La Haye-du-Puits; the
  tinted ground, under 6 m, is the low marsh ground. Heights are exaggerated five times, and
  distances shrink with depth, so nothing here is to scale. A stalk drawn dotted stands on ground the hills hide.])

#pagebreak()

#(wwii.situation-map)("1944-07-11", (-1.82, 49.185, -1.28, 49.375), width: 9.6in,
  caption: [HQ Twelfth Army Group's situation map for 2400 hours on 11 July 1944, over the same extent, as scanned:
  the source of the front and the divisions above. Library of Congress, Geography and Map Division, g5701s ict21036.])
