// Every torpedo of one night's attacks as a silhouette, from the kit's records alone (torpedoes.py): BANG's four
// attacks on convoy TAMA-17, 29-30 April 1944, forward tubes and after tubes, hits in red as her sheets record them.
//   uv run wwii-book build examples/torpedo-salvos/book.typ
#import "@local/wwii-book:0.1.0": *
#let wwii = init(assets: json("build/assets.json"), load: p => read(p, encoding: none))
#show: book

#eyebrow[29–30 April 1944 · Luzon Strait]
= Twenty torpedoes at TAMA-17

#(wwii.torpedo-salvos)("boats/ss-385-bang/patrol-1/attacks.csv", attacks: ("Attack 1", "Attack 2", "Attack 3", "Attack 4"),
  key: true, caption: [BANG's four attacks on convoy TAMA-17, each torpedo as her attack sheets type it: the forward
  tubes pointing forward, the after tubes aft, in the order fired; red where the sheet records a hit])
