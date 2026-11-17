// A unit's chain of command, from the kit's records/army/relations.csv: three units over the campaign, and one on
// a single day.
//   uv run wwii-book build examples/unit-chain/book.typ
#import "@local/wwii-book:0.1.0": *
#let wwii = init(assets: json("build/assets.json"), load: p => read(p, encoding: none))
#show: book
#set page(width: 11in, height: 8.5in, margin: (x: 0.7in, top: 0.55in, bottom: 0.5in))

= Who answered to whom
#eyebrow[Chains of command, June 1944 – May 1945]

#(wwii.unit-chain)("313inf-b", start: "1944-06-01", end: "1945-05-08", width: 9.6in,
  title: "Company B, 313th Infantry",
  caption: [Company B's chain from its first morning report in France (Cherbourg, 26 June 1944) to the end of the
  war: the regiment and division it belonged to, and the corps, armies and army groups the 79th Infantry Division
  was assigned or attached to, as the division's own order-of-battle tables date them. In January 1945 the
  regiment was attached to the 45th Division for a fortnight.])

#pagebreak()

#(wwii.unit-chain)("106aaa-d", start: "1944-08-01", end: "1945-05-08", width: 9.6in,
  title: "Battery D, 106th AAA AW Battalion (SP)",
  caption: [Battery D's battalion, and the 45th Infantry Division it was attached to from the landing in southern
  France, interval by interval as the division's attachments table gives them; above the division, its corps,
  army and army group in those intervals only.])

#pagebreak()

#grid(columns: (6.3in, 3in), column-gutter: 0.3in,
  (wwii.unit-chain)("9ad", start: "1944-07-15", end: "1945-05-08", width: 6.3in, title: "9th Armored Division",
    marks: ((date: "1944-12-16", words: "Ardennes"),),
    caption: [The 9th Armored Division's corps, armies and army group.]),
  (wwii.unit-chain)("106aaa-d", view: "ladder", on: "1944-12-01", width: 3in,
    caption: [Battery D's chain on 1 December 1944.]),
)

#pagebreak()

= On the day
#eyebrow[A chapter's opening: the chain in patches]

#(wwii.unit-chain)("313inf-b", view: "strip", on: "1944-07-04", width: 9.6in)
#v(0.3in)
#(wwii.unit-chain)("106aaa-d", view: "strip", on: "1945-03-20", width: 9.6in)
#v(0.3in)
#(wwii.unit-chain)("9ad", view: "strip", on: "1945-03-07", width: 9.6in)

#v(1fr)
#text(size: 7.5pt)[Shoulder sleeve insignia: US Army designs, in renderings from Wikimedia Commons, public domain except
the 12th Army Group's (Beringar, CC BY-SA 3.0), the 6th Army Group's (EclecticArkie, CC BY-SA 4.0), NATOUSA's
(Meghdhanu, CC BY-SA 4.0) and the First Army's before 1950 (Military editor, CC BY-SA 4.0).]

#pagebreak()

= At sea
#eyebrow[Two chains at once: the task organization above, the type command below]

#(wwii.unit-chain)("ss-385-bang", start: "1944-03-15", end: "1945-06-15", width: 9.6in, title: "USS BANG (SS-385)",
  caption: [BANG's six war patrols. Above, the operational chain: Task Force 17 (the Submarine Force, Pacific Fleet)
  under whose operation orders she sailed, and the coordinated attack groups (wolf packs) she patrolled in, with
  their commanders' task group numbers where the reports type them. Below, the submarine division and squadron each
  patrol report went through, and whose relief crew refitted her: the division at the base where the patrol
  ended, so it changes patrol by patrol. Between patrols, Task Force 17 is carried across (assumed).])

#pagebreak()

#(wwii.unit-chain)("dd-700-haynsworth", start: "1944-07-15", end: "1945-09-01", width: 9.6in,
  title: "USS Haynsworth (DD-700)",
  caption: [Haynsworth's task groups and units from her war diaries: shakedown at Bermuda, the Queen Mary's escort,
  the passage to the Pacific, the fast carriers with Halsey's Third Fleet (Task Group 38.2) and Spruance's Fifth
  (Task Group 58.3: the same carriers, renumbered), the Minami Daito bombardment, and on 9 April 1945 the unit that
  took her and two damaged carriers to Ulithi; then refresher training off California. Below, Destroyer Squadron 62,
  whose commander flew his pennant in her, and the division she exercised with.])

#pagebreak()

#(wwii.unit-chain)("20ncb", start: "1943-06-01", end: "1945-09-01", width: 9.6in,
  title: "20th Naval Construction Battalion",
  caption: [The 20th Seabees' commands from the monthly reports' routing (the Seabee Museum's chronology). In 1943-44
  its two sections were 1,000 miles apart: the 1st with the Seventh Fleet at Woodlark, Kiriwina and Milne Bay, the
  2nd with the Third Fleet in New Georgia and the Russells. Reunited in June 1944; on Okinawa in 1945 under the 42nd
  Regiment and 10th Brigade, then the 45th Regiment and 11th Brigade.])
