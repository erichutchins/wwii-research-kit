// The air war's other half (book/atlas/neuburg): an American day mission and the German jets sent up against it, the
// complement of the Bizerte example's German night raids and the Allied night fighters. Three pages: the mission at
// the scale of the airfields, the fight drawn large from the records, and the ground under the bombers' course as the
// guns below saw it. No period network: no wartime German sheet is in the atlas yet.
//   uv run wwii-book build examples/atlas-neuburg/book.typ
#import "@local/wwii-book:0.1.0": *
#let wwii = init(assets: json("build/assets.json"), load: p => read(p, encoding: none))
#show: book
#set page(width: 11in, height: 8.5in, margin: (x: 0.7in, top: 0.55in, bottom: 0.5in))

= Neuburg an der Donau
#eyebrow[26 April 1945 · Bavaria]

#(wwii.atlas-view)("neuburg", view: "mission", width: 9.4in,
  caption: [The mission. The 17th Bomb Group's B-26s flew "out of Dijon for Lechfeld airfield", as their Missing Air
  Crew Reports type it; six Me 262s of Jagdverband 44 took off from Munich-Riem at 1130 (published accounts) and met
  them over the Danube at Neuburg. The records give the ends of each flight and the minutes of the fight, never the
  route between: the wide arrows are notional, drawn from each recorded field to the recorded fight and back. The
  front is the 12th Army Group's situation map at noon that day.])

#pagebreak()

#(wwii.atlas-view)("neuburg", view: "fight", width: 9.4in,
  caption: [The fight, 1145 to 1152, from the records: the formation's course in and its turn for home as the 432nd
  Bomb Squadron's sketch draws them (traced; good to a few kilometres), each lost B-26's course as its form types it,
  and the hatched square where the 45th Infantry Division's G-2 put two crashes. The jets' attack is notional: met
  nearly head-on, over, and round to attack from behind (Ethell and Price, 1979; the gunners' "5 o'clock rear"). The
  rings are Battery D, 106th AAA AW Battalion's guns' reach (FM 4-155), round Bergen: the battery was defending the
  189th Field Artillery there, so its place is assumed. Shaded relief: the AWS Terrain Tiles.])

#pagebreak()

#(wwii.atlas-view)("neuburg", view: "sightline", width: 9.4in,
  caption: [What the guns could see and reach. A section along Big Red's typed course through its last known
  position: the ground (Copernicus GLO-30), the heights the records type for the jets, and the 37 mm guns' reach where
  it cuts the section. The battalion's history has Batteries C and D firing "10 rounds 37mm and 159 rounds .50 cal."
  from 1145 to 1147, "without result".])
