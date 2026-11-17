// An engagement from several records at once: three boats' war patrol reports, the Japanese convoy's own logs and
// FRUPAC's intercept notes, kept on four different clocks, drawn on one map and one GMT timeline from the kit's
// engagements/tama-17-1944-04-29/engagement.json, with one key for both.
//   uv run wwii-book build examples/tama-17/book.typ
#import "@local/wwii-book:0.1.0": *
#let wwii = init(assets: json("build/assets.json"), load: p => read(p, encoding: none))
#show: book

#eyebrow[29–30 April 1944 · Luzon Strait]
= Convoy TAMA-17

Four records kept four clocks. BANG wrote her patrol report in zone K, ten hours ahead of Greenwich; PARCHE and the
Japanese convoy's masters kept zone I, nine hours ahead; TINOSA kept zone H. Set on one clock, they agree. BANG fired
her first attack at 2256 K, which is 1256 GMT; Takegawa Maru's log has her torpedoed at 2201 I, 1301 GMT. BANG's
fourth attack, at 0518 K, and Nittatsu Maru's master's "0419", I, are one minute apart.

#(wwii.engagement-figure)("tama-17-1944-04-29", figure: "map", width: 5.5in, follow: "bang", box: (117.9, 17.95, 120.55, 19.85),
  caption: [The night of 29–30 April. BANG's track in red, PARCHE's and TINOSA's in black; small circles are the
  convoy where each boat reported it; dotted lines join an attack to the Japanese record of it.])

#(wwii.engagement-figure)("tama-17-1944-04-29", figure: "timeline", width: 5.5in, follow: "bang", key: true,
  caption: [The same records on one GMT clock. Each attack is joined to the Japanese record of it, with the minutes
  between the two.])
