// An illustrated atlas's coordinated pair for Palermo in 1943 (book/atlas/palermo): one battery's own record, the
// night raids on the harbour other batteries of its regiment record, and the wartime sheets the battery worked from.
//   uv run wwii-book build examples/atlas-palermo/book.typ
#import "@local/wwii-book:0.1.0": *
#let wwii = init(assets: json("build/assets.json"), load: p => read(p, encoding: none))
#show: book
#set page(width: 11in, height: 8.5in, margin: (x: 0.7in, top: 0.55in, bottom: 0.5in))

= Palermo
#eyebrow[July 1943 – April 1944 · Sicily]

#(wwii.atlas-view)("palermo", view: "panorama", width: 6.6in,
  caption: [Battery C, 62nd Coast Artillery (AA), from its own reports: south-west of the city by its grid reference
  on 24 July 1943, two days after Palermo fell, then at the port from 30 July to April 1944 (its symbol, FM 21-30).
  In grey, raids on the harbour that Battery D, 62nd CA, records engaging. No
  front: the island was the Allies' from mid-August. Roads and railways from the War Office's 1943 Italy 1:50,000
  (GSGS 4229): the period network, not anyone's route.])

#pagebreak()

#(wwii.atlas-view)("palermo", view: "oblique", width: 9.6in,
  caption: [The same ground, looking north-north-east from the mountains over the Conca d'Oro to the bay: Monreale
  on its slope at left, the port beyond the city. Heights are exaggerated twice, and distances shrink with depth,
  so nothing here is to scale.])

#pagebreak()

#(wwii.atlas-view)("palermo", view: "sheet", width: 7.8in,
  caption: [The sheets themselves: GSGS 4229, Italy 1:50,000, sheets 249-I to IV, 250-III and 258-I (War Office,
  1943; Army Map Service reprint), placed by their own blue South Italy Zone grid, the grid the battery's reports
  use ("419445 Sheet 249-II NE"); the white corner is open sea, on a sheet not to hand. The rings are ours. University
  of Texas Libraries, PCL Map Collection.])
