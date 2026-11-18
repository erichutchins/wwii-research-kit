// An attack on the Navy's maneuvering board, on the magazine grid: BANG's attacks 3 and 4 on convoy TAKA-909,
// 19 September 1944, from her attack data sheets (the kit's engagements/taka-909-1944-09-19/engagement.json), solved by
// the kit's site/engage.js; what BANG recorded of the hits, and the Japanese records' own account of the same minutes;
// a punched-card QR code to the engagement's page on the kit's site.
//   uv run wwii-book build examples/maneuvering-board/book.typ
#import "@local/wwii-book:0.1.0": *
#let wwii = init(assets: json("build/assets.json"), load: p => read(p, encoding: none))
#show: book.with(preset: "blurb-magazine")
#show: on-grid.with(sources: (
  jacar: (title: [JACAR], id: true),   // a JACAR reference code names the item, so it is kept
))

#let pr = "rg38-74802831"   // BANG's third war patrol report

#part-title[East of Formosa, 1944]

#running-text(
  eyebrow: [19 September 1944 · east of Formosa · zone K (−10)],
  title: [Bow and stern in fifty-five seconds],
  standfirst: [Two salvos at two ships of convoy TAKA-909, plotted as a fire-control party would have plotted them,
    and set beside what the convoy's escorts wrote down.],
)[
BANG had to "run under bow and beam escort to get in", tracking by sound alone for twenty minutes below periscope
depth.#note(cite: pr + "/p17") At 0915 she fired four torpedoes from the bow tubes at one AK "similar to ADEN MARU";
at 0915-55, fifty-five seconds later by the sheet's typed seconds, she fired four from the stern at a
second.#note(cite: pr + "/p19") Then she "went immediately to 400 feet as I had seen another escort ... at about 2000
yards with a 0° angle on the bow".#note(cite: pr + "/p07")

Plotted from the sheets' numbers, the two targets lay on either side of her: the first fine on the port bow at 1,400
yards, the second astern at 1,200. She fired from inside the convoy.

== What each side wrote down

The sheets type "2 Hits" for each salvo and do not say which torpedoes hit. For the first BANG claimed one AK damaged,
having "heard two timed hits"; for the second, one sunk, with "prolonged breaking up noises through
hull".#note(cite: pr + "/p17")#note(cite: pr + "/p19")

The convoy's escorts kept their own clock, zone I, an hour behind BANG's. The minesweeper W-15's diary has the
convoy's seventh ship, Tosei Maru, torpedoed at 0820: five minutes after BANG's first salvo, 0815 by the escorts'
clock.#note(cite: "jacar:C08030607800/p53") The 4th Surface Escort Division's diary has No. 2 Tosei Maru
sunk,#note(cite: "jacar:C08030144100/p12") and the Navy's daily summary of escort events calls her a 500-ton cargo
ship.#note(cite: "jacar:C16120660000/p07") No Japanese record names a second ship hit. Neither side's record says
which of BANG's two targets Tosei Maru was, and the board does not choose: her position, as W-15 reckoned it, lies
nine miles from where BANG reckoned her own, a gap of the size two navigators' dead reckoning often leaves.

#across(at: top, (wwii.maneuvering-board)("taka-909-1944-09-19", ("Attack 3", "Attack 4"), boat: "bang",
  width: 4.6in, parts: ("figure", "key"),
  caption: [BANG's attacks 3 and 4 on one board, own ship at the centre at 0915 K. In pencil, each target where the
  sheet's range and the solution put it at firing (A, forward; B, aft) and its course while the torpedoes ran,
  assumed steady. In BANG's blue, each torpedo on own course plus its typed gyro angle, drawn from the first ring out,
  as far as its run; a dashed ring is what BANG recorded of that salvo. In red, the Japanese records' ship torpedoed
  and sunk, placed by their own positions: off the board, so on its rim at their bearing and distance. The escort she
  dived from has no bearing in the record and is not drawn.]))

#(wwii.maneuvering-board)("taka-909-1944-09-19", ("Attack 3", "Attack 4"), boat: "bang", width: 4.6in,
  parts: ("japanese",), japanese-intro: [The Japanese records of 19 September that the kit holds for convoy TAKA-909,
    as written, with our translations. J02 and J04 both rest on the escorts' reports, so they count once.])

== See it move

The kit's page for this engagement plays the same records on one clock: BANG's track, the attacks, the escorts'
records and her depth through the four and a half hours of depth charges that followed.

#(wwii.punch-card)("https://erichutchins.github.io/wwii-research-kit/engagement.html?e=taka-909-1944-09-19",
  lines: ("U.S.S. BANG (SS-385)", "CONVOY TAKA-909", "182315Z SEP 44"))

#section-sources(titles: ("74802831": "USS Bang, August 1944 - September 1944"))
]
