// An attack on the Navy's maneuvering board: BANG's attacks 3 and 4 on convoy TAKA-909, 19 September 1944, from her
// attack data sheets (kit's engagements/taka-909-1944-09-19/engagement.json), solved by the kit's site/engage.js.
//   uv run wwii-book build examples/maneuvering-board/book.typ
#import "@local/wwii-book:0.1.0": *
#let wwii = init(assets: json("build/assets.json"), load: p => read(p, encoding: none))
#show: book

#eyebrow[19 September 1944 · east of Formosa]
= Bow and stern in fifty-five seconds

BANG had to "run under bow and beam escort to get in", tracking by sound alone for twenty minutes below periscope
depth (#typed[rg38-74802831/p17]). At 0915, zone K (−10), she fired four torpedoes from the bow tubes at one AK
"similar to ADEN MARU"; at 0915-55 she fired four from the stern at a second, the attack sheets' typed seconds
(#typed[p17], #typed[p19]). Then she "went immediately to 400 feet as I had seen another escort ... at about 2000
yards with a 0° angle on the bow" (#typed[p07]). The sheets type two hits for each salvo and do not say which torpedoes
hit.

Plotted from the sheets' numbers, the two targets lay on either side of her, one fine on the port bow and one astern:
she fired from inside the convoy.

#(wwii.maneuvering-board)("taka-909-1944-09-19", ("Attack 3", "Attack 4"), boat: "bang", width: 5in,
  caption: [BANG's attacks 3 and 4 on one board, own ship at the centre at 0915 K. In pencil, each target where the
  sheet's range and the solution put it at firing (A, forward; B, aft) and its course while the torpedoes ran, assumed
  steady; in red, each torpedo on own course plus its typed gyro angle, as far as its run. The escort she dived from
  has no bearing in the record and is not drawn.])
