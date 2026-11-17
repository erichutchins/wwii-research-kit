// An illustrated atlas's coordinated pair for Metz in January and February 1945 (book/atlas/metz): the 12th Army
// Group's front and divisions, with two units' own records on them, and beside them the old town's Catholic churches.
//   uv run wwii-book build examples/atlas-metz/book.typ
#import "@local/wwii-book:0.1.0": *
#let wwii = init(assets: json("build/assets.json"), load: p => read(p, encoding: none))
#show: book
#set page(width: 11in, height: 8.5in, margin: (x: 0.7in, top: 0.55in, bottom: 0.5in))

= Metz
#eyebrow[January – February 1945 · Lorraine]

#grid(columns: (6.1in, 3.1in), column-gutter: 0.35in,
  (wwii.atlas-view)("metz", view: "panorama", width: 6.1in,
    caption: [The front on 1 February 1945 (heavy) and 14 January (dashed), and the divisions as HQ Twelfth Army
    Group's map of 1 February places them; in red, the 9th Armored Division, in reserve north of Metz, and its
    headquarters' own stations (Bockange, then Ennery from 14 January). In blue, HQ Battery, 128th AAA Gun Battalion,
    at Metz from 20 January to 28 February: its record names the town, not the position, so its symbol stands on a
    leader beside it. Roads and railways from IGN's 1:50,000 (1953–57 editions).]),
  (wwii.atlas-view)("metz", view: "inset", width: 3.1in,
    caption: [The old town on IGN's 1:50,000 at full detail, with its Catholic churches: the cathedral and the
    parish churches and basilica a Sunday Mass would be in (today's buildings, from OpenStreetMap; convent and
    hospital chapels left out).]),
)

#pagebreak()

#(wwii.atlas-view)("metz", view: "oblique", width: 8.2in,
  caption: [The same ground, looking east from beyond the Moselle toward the Saar front: Thionville on the left,
  Metz on the right. Heights are exaggerated four times, and distances shrink with depth, so nothing here is to
  scale.])

#pagebreak()

#(wwii.situation-map)("1945-02-01", (5.95, 49.0, 6.85, 49.45), unit: "9ad", width: 9.6in,
  caption: [HQ Twelfth Army Group's situation map for 1 February 1945 over the same extent, as scanned: the source of
  the front and the divisions above. The red ring round the 9th Armored is ours. Library of Congress, Geography and
  Map Division.])
