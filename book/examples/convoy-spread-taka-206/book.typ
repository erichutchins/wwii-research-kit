// A convoy that a coordinated attack group met, as a spread on the magazine grid: convoy TAKA-206, Keelung for Naha,
// and BANG, REDFISH and SHAD east of Formosa, 22-23 November 1944 (the kit's engagements/taka-206-1944-11-22): the
// convoy's whole route with the engagement's box joined to its map, the convoy's ships at one scale, and each attack's
// claim beside JANAC's credit and the Japanese records.
//   uv run wwii-book build examples/convoy-spread-taka-206/book.typ
#import "@local/wwii-book:0.1.0": *
#let wwii = init(assets: json("build/assets.json"), load: p => read(p, encoding: none))
#show: book.with(preset: "blurb-magazine")
#show: on-grid.with(sources: (jacar: (title: [JACAR], id: true)))

#let e = "taka-206-1944-11-22"

#part-title[East of Formosa, 1944]

#running-text(
  eyebrow: [22–23 November 1944 · east of Formosa · zones K (−10) and I (−9)],
  title: [Three boats, one convoy],
  standfirst: [Convoy TAKA-206 on its way from Keelung to Naha, the night three boats of one coordinated attack group
    met it, and what each side wrote down of it.],
)[
TAKA-206 was six merchant ships with four escorts, bound from Keelung for Naha; its sailing plan has it leaving
Keelung at 0800 on the 22nd by the escorts' clock.#note(cite: "jacar:C08030607900/p33") Its route between the two
ports is not traced from the escorts' charts: the overview draws it on the lanes of the time, up Formosa's east coast
by an assumed waypoint.

#across(at: top, (wwii.convoy-route)(e, width: 5.5in, key: false,
  caption: [Convoy TAKA-206's voyage and the engagement east of Formosa. Left, its lane from Keelung to Naha, dotted
  through an assumed waypoint; the open rings are ports, the solid dot its recorded sailing; the box is the map on the
  right. There, each boat's track in its own colour, from its own navigator's fixes; the marks are numbered in time
  order and keyed at the end of the section.]))

== The night

SHAD fired first, at 2338 by her clock: one salvo, fired by mistake at a torpedo boat, which
missed.#note(cite: "rg38-74848165/p26") Two minutes later the escort Manazuru fired a red flare for a surfaced
submarine, at 2240 by the escorts' clock, zone I, an hour behind the boats'.#note(cite: "jacar:C08030607900/p40")
BANG's first attack came nearly an hour after, at 0032 by her clock, 2332 by the escorts';#note(cite:
"rg38-74802868/p12") REDFISH fired first at 0104.#note(cite: "rg38-74837267/p43")

The minesweeper W-15 saw the convoy's second ship, Hozan Maru, torpedoed at 2339 by the escorts'
clock,#note(cite: "jacar:C08030607900/p40") and the Navy's summary has her sunk at 2337.#note(cite:
"jacar:C16120660200/p08") Both times fall within minutes of BANG's first attacks and some twenty-five minutes before
REDFISH's first. JANAC, after the war, credits REDFISH with her. The table sets the two side by side; it does not
settle them.

]

// The tally and the map's key run across the page and break from page to page: pages of one column.
#set page(columns: 1)
#heading(level: 2)[The convoy's ships]
#(wwii.convoy-ships)(e, parts: ("silhouettes",),
  caption: [Convoy TAKA-206 as W-15's battle report lists it, escorts then merchant ships, at one scale. A red cross is
  a ship the Japanese records have sunk; a red ring, one torpedoed and not sunk. Each is drawn from her own plate or her
  class's, as labelled; the ships no wartime manual draws are named, not drawn. BANG's own silhouette is set beside them for scale.])

#heading(level: 2)[Claimed, credited, recorded]
#(wwii.convoy-ships)(e, parts: ("tally",))

#heading(level: 2)[The map's marks]
#(wwii.convoy-route)(e, width: 5.5in, key: "only")
