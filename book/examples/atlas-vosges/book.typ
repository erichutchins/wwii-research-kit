// An illustrated atlas's coordinated pair for the Northern Vosges in January 1945 (book/atlas/northern-vosges), with
// one battery's own record on it: the positions and engagements of Battery D, 106th AAA AW Bn (SP), from its reports.
//   uv run wwii-book build examples/atlas-vosges/book.typ
#import "@local/wwii-book:0.1.0": *
#let wwii = init(assets: json("build/assets.json"), load: p => read(p, encoding: none))
#show: book
#set page(width: 11in, height: 8.5in, margin: (x: 0.7in, top: 0.55in, bottom: 0.5in))

= The Northern Vosges
#eyebrow[December 1944 – February 1945 · Operation Nordwind]

#(wwii.atlas-view)("northern-vosges", view: "panorama", width: 7.9in,
  caption: [The front on 29 January 1945 (heavy), after VI Corps fell back to the Moder, and on 31 December (dashed);
  divisions as the army group's map of 29 January places them. In red, Battery D, 106th AAA AW Bn (SP), from its
  own reports: positions placed by grid square or town, and the aircraft it engaged. Roads and railways from IGN's
  1:50,000 (1939 and 1953–56 editions): an illustration of the period network, not anyone's route.])

#pagebreak()

#(wwii.atlas-view)("northern-vosges", view: "oblique", width: 9.6in,
  caption: [The same ground, looking north from behind the American line toward the German: the forested Vosges
  to the left and ahead, the open country toward Haguenau to the right. Where a ridge hides the front, the line
  breaks. Heights are exaggerated four times, and distances shrink with depth, so the scale bar holds only across the view's middle distance.])

#pagebreak()

#(wwii.situation-map)("1945-01-29", (7.15, 48.76, 7.9, 49.075), width: 9.6in,
  caption: [HQ Twelfth Army Group's situation map for 29 January 1945 over the same extent, as scanned: the source of
  the front and the divisions above. Library of Congress, Geography and Map Division.])
