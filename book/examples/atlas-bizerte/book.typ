// An illustrated atlas's coordinated pair for Lake Bizerte in the summer of 1943 (book/atlas/bizerte), with two units'
// own records on it, and the wartime sheets they worked from as the third page. No front: the Axis in Tunisia had
// surrendered on 13 May; these were the anti-aircraft defences of the ports gathering for Sicily.
//   uv run wwii-book build examples/atlas-bizerte/book.typ
#import "@local/wwii-book:0.1.0": *
#let wwii = init(assets: json("build/assets.json"), load: p => read(p, encoding: none))
#show: book
#set page(width: 11in, height: 8.5in, margin: (x: 0.7in, top: 0.55in, bottom: 0.5in))

= Lake Bizerte
#eyebrow[May – October 1943 · Tunisia]

#(wwii.atlas-view)("bizerte", view: "panorama", width: 7.5in,
  caption: [Two units' own records, by date, each with its Army symbol where it stayed: in red, Battery C, 62nd CA
  (AA), on the lake's south-east shore by its grid references (its 20 June entry, "3 mi east of Ferryville", taken
  to be the same place); in blue, the 67th's medical detachment. In grey, a Ju 88 Battery B reports bringing down on 6 July. Roads and railways from
  the War Office's 1942 Tunisia 1:50,000: the period network, not anyone's route.])

#pagebreak()

#(wwii.atlas-view)("bizerte", view: "oblique", width: 9.6in,
  caption: [The same ground, looking north across Lake Bizerte to the town and the sea, Garaet el Ichkeul and
  Jebel Ichkeul on the left. Heights are exaggerated three times, and distances shrink with depth, so nothing here
  is to scale.])

#pagebreak()

#(wwii.atlas-view)("bizerte", view: "sheet", width: 9.6in,
  caption: [The sheets themselves: GSGS 4225, Tunisia 1:50,000, sheets 2, 3, 6, 7, 12 and 13 (War Office, 1942;
  Army Map Service reprint), placed by their own purple North-West Africa grid, the grid the battery's reports
  use ("J 775914 Sheet 6"). The rings are ours. University of Texas Libraries, PCL Map Collection.])
