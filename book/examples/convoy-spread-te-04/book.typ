// A convoy that a coordinated attack group met, as a spread on the magazine grid: convoy TE-04, Yulin for Moji by way
// of Keelung, and BANG, PARCHE and TINOSA north of the South China Sea, 3-4 May 1944 (the kit's
// engagements/te-04-1944-05-03): the convoy's whole route with the engagement's box joined to its map, the convoy's
// ships at one scale, and each attack's claim beside JANAC's credit and the Japanese records.
//   uv run wwii-book build examples/convoy-spread-te-04/book.typ
#import "@local/wwii-book:0.1.0": *
#let wwii = init(assets: json("build/assets.json"), load: p => read(p, encoding: none))
#show: book.with(preset: "blurb-magazine")
#show: on-grid.with(sources: (jacar: (title: [JACAR], id: true)))

#let e = "te-04-1944-05-03"

#part-title[Luzon Strait, 1944]

#running-text(
  eyebrow: [3–4 May 1944 · north of the South China Sea · zones H (−8), I (−9) and K (−10)],
  title: [Five ore ships],
  standfirst: [Convoy TE-04 on its long way north from Hainan, the night three boats met it in turn, and what each
    side wrote down of it.],
)[
TE-04 left Yulin, on Hainan, on 30 April 1944,#note(cite: "jacar:C08030140600/p33") bound for Moji by way of
Keelung. Its route is not traced from the escorts' charts: the overview draws it on the lanes of the time, by
waypoints each assumed for the reason the lanes give.

#across(at: top, (wwii.convoy-route)(e, width: 5.5in, key: false, box: (117.1, 20.55, 119.05, 21.2),
  caption: [Convoy TE-04's voyage and the engagement. Above, its lane from Yulin by Keelung to Moji, dotted through
  assumed waypoints; the open rings are ports, the solid dot its recorded sailing; the box is the map below. There,
  each boat's track in its own colour, from its own navigator's fixes; the marks are numbered in time order and keyed
  at the end of the section.]))

== Three boats, three clocks

The three boats kept three clocks that night: TINOSA zone H,#note(cite: "rg38-74856363/p26") PARCHE zone I, the
escorts' Tokyo time,#note(cite: "rg38-74828582/p20") and BANG zone K.#note(cite: "rg38-74802746/p25") The table gives
each time as typed and in GMT, so the order of the attacks can be read straight down it.

== Who sank which

JANAC, the Navy's postwar committee, credited each loss to a boat. Two of the sunk ships' own movement logs time
their sinkings to the other boat's attack. Kinrei Maru's log has her sunk at 0109,#note(cite:
"jacar:C08050104500/p30") three minutes after PARCHE's second attack at 0106;#note(cite: "rg38-74828582/p20") JANAC
credits her to BANG. Taiyoku Maru's log has her sunk at 0237,#note(cite: "jacar:C08050105400/p10") five minutes
after BANG's fifth attack at 0232 by the same clock;#note(cite: "rg38-74802746/p25") JANAC credits her to PARCHE.
Each boat's navigator and each ship's log kept its own reckoning. The table sets the claims, the credits and the
records side by side; it does not settle them.
]

// The ships, the tally and the map's key run across the page and break from page to page: pages of one column.
#set page(columns: 1)
#heading(level: 2)[The convoy's ships]
#(wwii.convoy-ships)(e, parts: ("silhouettes",),
  caption: [Convoy TE-04's ships as the 1st Surface Escort Division's chart and loss list and combinedfleet.com name
  them, escorts then merchant ships, at one scale; each ship's silhouette is her class's plate, or a type standing for
  her, as labelled. A red cross is a ship the Japanese records have sunk. BANG's own silhouette is set beside them for
  scale.])

#heading(level: 2)[Claimed, credited, recorded]
#(wwii.convoy-ships)(e, parts: ("tally",))

#heading(level: 2)[The map's marks]
#(wwii.convoy-route)(e, width: 5.5in, key: "only", box: (117.1, 20.55, 119.05, 21.2))
