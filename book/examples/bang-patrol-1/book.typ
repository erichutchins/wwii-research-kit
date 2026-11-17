// A page of USS BANG's first war patrol, built from the kit's records alone: the attack data sheet as a facsimile,
// the Japanese record as typed, every torpedo of the patrol, and a QR tag to the engagement's interactive page.
//   uv run wwii-book build examples/bang-patrol-1/book.typ
#import "@local/wwii-book:0.1.0": *
#let wwii = init(assets: json("build/assets.json"), load: p => read(p, encoding: none))
#show: book

#eyebrow[29–30 April 1944 · Luzon Strait]
= Convoy TAMA-17

#grid(columns: (1fr, auto), gutter: 14pt,
  [
    BANG made her first attack at 2256 on 29 April 1944 (zone K), at 19-26N 118-45E, on a convoy bound from Takao
    for Manila. Its escort, the destroyer Harukaze, had left Takao with it at 1300 the day before.

    #record-quote(cite: "jacar:C08030140600/p15", source: [1st Surface Escort Division, movements table, April 1944; translated])[
      Departs Takao 1300 escorting convoy TAMA-17 (enemy-submarine suppression)
    ]
  ],
  (wwii.qr-tag)("https://erichutchins.github.io/wwii-research-kit/engagement.html?e=tama-17-1944-04-29",
    dtg: "292256K APR 44", position: "19-26N 118-45E", cite: "rg38-74802746/p16"),
)

#(wwii.facsimile)("rg38-74802746/p16", crop: (0, 0, 1, 0.5),
  caption: [BANG's attack data sheet for her first attack, 29 April 1944])

== Every torpedo of the patrol
#(wwii.records)("boats/ss-385-bang/patrol-1/attacks.csv", torpedo-ledger)
