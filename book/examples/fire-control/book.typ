// An explainer on the grid: how a submarine's torpedo was aimed, the fire-control triangle and the Torpedo Data
// Computer, worked through BANG's Attack 3 of 19 September 1944 from her attack data sheet (records/boats/
// ss-385-bang/patrol-3/attacks.csv and attack_sheets.yml, rg38-74802831/p17-p18). Every figure's numbers are the
// kit's site/engage.js, run under Node by fire_control.py; the facts are the sources site/torpedo.html and
// site/tdc.html cite.
//   uv run wwii-book build examples/fire-control/book.typ
#import "@local/wwii-book:0.1.0": *
#let wwii = init(assets: json("build/assets.json"), load: p => read(p, encoding: none))
#show: book.with(preset: "blurb-magazine")
#show: on-grid.with(sources: (
  usf-25a: [_Current Doctrine, Submarines_, USF 25(A) (1944)],
  op635: [_Torpedoes Mark 14 and 23 Types_, OP 635 (1945)],
  op1056: [_Torpedo Data Computer Mark 3_, OP 1056 (1944)],
  rowland-boyd: [Rowland and Boyd, _U.S. Navy Bureau of Ordnance in World War II_ (1953)],
))

#let sh = "rg38-74802831"   // BANG's third war patrol report: the attack data sheet of Attack 3, p17-p18
#let E = "taka-909-1944-09-19"

#part-title[Reading the records]

#running-text(
  eyebrow: [Fire control · BANG, Attack 3 · 19 September 1944],
  title: [How a torpedo was aimed],
  standfirst: [A torpedo that takes most of a minute to arrive and a target that will not wait: the triangle that joins them, the
    machine that kept it solved, and one attack worked through from the numbers its sheet types.],
)[
Every attack in a submarine's war patrol report ends in a table of numbers. For BANG's third attack of her third
patrol, at 0915 on 19 September 1944, zone K (−10: ten hours ahead of GMT), the table gives four torpedoes, and for
each a gyro angle (351, 354, 357, 0) and a track angle (61S, 64S, 67S, 70S).#note(cite: sh + "/p18") Above it the
sheet gives the boat's own course and speed, 340° at 2 knots, at 65 feet, and the target's course, speed and range:
"Course: 090° Speed: 7.0 Range: 1400 yds."#note(cite: sh + "/p17")

== The problem

A torpedo takes time to arrive. At 1,400 yards a torpedo running at 46 knots, about 26 yards a second, is some fifty
seconds on its way, and a ship making 7 knots moves two hundred yards in that time. A torpedo fired at where the
target is will pass astern of where it has gone. The torpedo has to be aimed at where the target will be when the
torpedo gets there, and that point is fixed by both ships' speeds and by the angle at which the target is crossing.

Nor did the boat have to point at the target. A torpedo carried a gyro, and the gyro angle was set into it before
firing, "which causes the torpedo, immediately upon launching, to turn through an angle and steady on a course
differing from the direction of the torpedo tube axis". It is measured from the boat's bow, "from 0° clockwise
through 360°": a straight shot from a bow tube is 0°, from a stern tube 180°.#note(cite: "usf-25a/p37") The
torpedo's course is the boat's course plus the gyro angle. BANG's first torpedo, from tube 1, ran on 340° + 351°,
which is 331°.

The approach officer could measure three things. The target's bearing came from the periscope, radar or sound; its
range from the periscope's stadimeter, radar or echo ranging; and its angle on the bow by eye, from its
aspect.#note(cite: "usf-25a/p49") Looks were kept short: "Two or more brief exposures of less than 30 seconds are
preferable to a long exposure".#note(cite: "usf-25a/p41") From a run of looks the target's course and speed were
worked out. Attack 3 was harder than that: BANG "had to run under bow and beam escort to get in", below periscope
depth "using sound tracking only for 20 minutes prior to firing", with a "Final periscope set-up to TDC just before
firing".#note(cite: sh + "/p17")

== The triangle

The answer is a triangle. Its corners are the boat when she fires, the target at that moment, and the point of
intercept, "the intersection of torpedo and target tracks".#note(cite: "usf-25a/p38") Its angles have names, and the
doctrine defines each.#note(cite: "usf-25a/p37")

At the target is the _angle on the bow_: the "relative bearing of submarine from the target ship measured to
starboard or port from the target ship's head from 0° to 180°". At 0° the target is coming straight at the boat.

At the boat is the _lead_, which the doctrine calls the sight angle, "the angle between the bearing of the target at
the instant of firing and the torpedo track": how far ahead of the target the torpedo is aimed.

At the intercept is the _track angle_, "the angle at the point of intercept between the target ship's track and the
reversed direction of the torpedo track", measured, like the angle on the bow, from the target's head to starboard
or port. A track of 90° meets the target square on the beam. Because the angles of a triangle add to 180°, the track
angle is the angle on the bow and the lead added together.

The torpedo and the target reach the intercept at the same moment. In that time the torpedo runs its speed times
the time and the target its own speed times the same time, so the two sides of the triangle that end at the
intercept are in the ratio of the two speeds. Each side lies opposite one angle: the target's run opposite the
lead, the torpedo's run opposite the angle on the bow. The law of sines then gives the lead from the angle on the
bow and the ratio _k_ of the target's speed to the torpedo's, and the range drops out:

#align(center, block(above: 6.5pt, below: 6.5pt, text(size: 10pt)[sin _L_ = _k_ sin _AOB_]))

That working is the kit's, from the doctrine's definitions; it is what the site's engagement and fire-control pages
compute.#note(cite: "usf-25a/p37")[The plain triangle leaves out the torpedo's turn onto its gyro course, which the
doctrine corrects for as "advance and transfer", and the parallax between periscope and tube; on an angled shot it is
a degree or two and some tens of yards from what the computer set (inferred)] The lead grows with the target's
speed and is greatest when the target crosses square, at 90° on the bow; it shrinks as the target turns towards or
away. A slow target needs little lead. A 7-knot ship against a 46-knot torpedo gives _k_ = 7/46, about 0.15, and the
lead can never exceed nine degrees.

#across(at: top)[
  #grid(columns: (3.3in, 1fr), column-gutter: 12pt,
    (wwii.fire-control)("triangle", engagement: E, attack: "Attack 3", boat: "bang", width: 3.3in, key: true),
    [
      #set par(justify: false, first-line-indent: 0pt)
      #set text(size: 7.6pt, top-edge: 6pt, bottom-edge: -1.7pt)
      #v(6pt)
      #text(font: tokens.display, weight: "semibold", style: "italic")[BANG's Attack 3, 0915 K, 19 September 1944]
      #v(3pt)
      The fire-control triangle drawn to scale from the attack data sheet, north up. Own ship (blue) on 340° at 2
      knots; the target, 1,400 yards off on 090° at 7 knots. The solution puts her on a bearing of 328.1°, 58.1° on
      the starboard bow; the torpedo is led 7.4° ahead of her and meets her track at 65.5° on the starboard side,
      after a run of about 1,306 yards. The faint lines are the four torpedoes on own course plus each typed gyro
      angle, a divergent spread round that point of aim.
      #v(4pt)
      #text(size: 6.8pt, fill: tokens.muted)[Solved by the kit's _engage.js_ (_attackSheet_, _tdcAt_) from the
      sheet's typed numbers; what it assumes is set under the figure. Drawn for this research.]
    ])
]

== Track and gyro on the sheet

The kit's computation takes the sheet's own course, the target's course and speed, the range, and the gyro angles
as typed, and asks where the target must have been for those gyros to be a solution. Taking the point of aim as the
middle of the four gyros, 355.5°, the target was 1,400 yards away on a bearing of 328.1°, with an angle on the bow of
58.1° to starboard, and the torpedo led her by 7.4°: 58.1° and 7.4° make the 65.5° track at the point of aim. The
sheet types no torpedo speed; the power column is blank for the Mark 23,#note(cite: sh + "/p18") which was a Mark 14
"operated at high speed only", and the Mark 14's high speed was 46 knots.#note(cite: "op635/p13") The 46 knots used
here is therefore assumed, not typed.

The typed tracks check against the typed gyros. Own course 340° plus gyro 351° is a torpedo course of 331°; turned
round, 151°, and measured from the target's head on 090°, that is 61° on her starboard side, the 61S the sheet types.
Each of the four tracks follows from its gyro the same way.#note(cite: sh + "/p18")

== Why a spread

No solution was exact. The target's course and speed were estimates, and the range was measured in a look of
seconds. The doctrine was blunt: "Spreads are always used. The minimum spread
should cover at least 80% of the target length", widening up to 200% when the problem was less well
solved.#note(cite: "usf-25a/p53") A longitudinal spread fired along one track at different points of aim; a
divergent spread fanned the torpedoes at one point of aim with different gyro angles, which the doctrine found "more
difficult to evade".#note(cite: "usf-25a/p53")

Attack 3's spread was divergent. The sheet's words are "Fired four torpedoes spread 3, 1, 1, 3 from aft forward
using the offset knob on the TDC", and its spread line reads "Divergent, 2° between torpedoes".#note(cite: sh + "/p17") The gyros it types step three degrees, not two, and the figure draws them as typed.

The doctrine had preferences about the shot itself. "The best chances of hitting are with small gyro
angles",#note(cite: "usf-25a/p44") and "Track angles between 70° and 110° are considered best for all around
coverage".#note(cite: "usf-25a/p53") BANG's gyros were all within nine degrees of the bow; her tracks, 61° to 70°,
were just short of the best band.

#across(at: bottom)[
  #(wwii.fire-control)("aob", engagement: E, attack: "Attack 3", boat: "bang", width: 400pt,
    aobs: (20, 45, 90, 135, 160),
    caption: [The same shot at other angles on the bow: the range, the target's speed and the torpedo's as in
      Attack 3, each panel turned so the line of sight runs up the page. The lead is greatest with the target square
      on the beam and never more than about nine degrees at these speeds; the run lengthens as the target draws
      away. Solved by _engage.js_; 46 knots assumed.])
]

== The Torpedo Data Computer

The triangle had to be solved again at every look, with the target and the boat both moving. Between the periscope and the tubes stood the Torpedo Data Computer. "At the beginning of the war most submarines
carried the Torpedo Data Computer Mark 3"; a Mark 4 followed, because radar data "could be only partially utilized"
by the Mark 3.#note(cite: "rowland-boyd/p399") No record read here names the mark of BANG's computer. It is taken to be a Mark 3, whose manual went to boats "SS 167-544 incl." in June 1944.#note(cite: "op1056/p277")[Assumed]

The Mark 3 did its work in two parts.#note(cite: "op1056/p22")[The position keeper's equations are at p. 22, the
angle solver's at p. 29] The _position keeper_ held the target's position and kept it moving. Into it went the
target's estimated course and speed, set in by hand, and the boat's own course and speed, fed in automatically:
"data on the enemy's position and movement was manually inserted".#note(cite: "rowland-boyd/p399") From them it ran
the target forward from the last look and showed, on its dials, where she should be now: her bearing, her range, her
angle on the bow, the boat's distance from her track. These were the doctrine's "generated bearings", which a boat
could fire on between looks.#note(cite: "usf-25a/p52")

The _angle solver_ took the bearing and range the position keeper gave it and the torpedo's speed, and worked the
triangle continuously. "The gyro angle, track angle and torpedo run are continuously being computed … The computed
gyro angle is set on the torpedo continuously either automatically or by follow the pointer, spread angles being
superimposed as desired".#note(cite: "usf-25a/p50") The spread was an offset added to each tube's order: on Attack 3,
"the offset knob on the TDC".#note(cite: sh + "/p17")

#across(at: top)[
  #(wwii.fire-control)("tdc", width: 400pt,
    caption: [The Torpedo Data Computer Mark 3 as a diagram, each face's dials named as its manual's photographs
      name them: the Position Keeper, Fig. 98, and the Angle Solver, Fig. 102. What was measured and estimated went
      in on the left; the boat's own course and speed came from her instruments. Its generated bearing could be fired on between looks. Drawn for this research.])
]

On BANG's Attack 3 the faces would have stood like this at the moment of firing. The position keeper's _target_
dial: bearing 328°, angle on the bow 58° starboard, the target's course 090°; _target speed_ 7 knots; _range_ 1,400
yards; _distance to track_, the range times the sine of the angle on the bow, about 1,190 yards.#note(cite: "op1056/p47") The angle solver's _gyro angle order_, at the point of aim, 355.5°, with each tube's offset added; its
_torpedo run_ about 1,300 yards. These are the kit's solution set on the computer's faces, not a record of what it
showed.#note(cite: "op1056/p107")[The faces are the manual's Fig. 98, p. 107, and Fig. 102, p. 111]

== What it could not know

The computer knew only what it was told. Its target moved on the course and at the speed the approach officer had
set, and kept on them; if those were wrong, so was every bearing and every gyro it produced, and nothing inside it
could tell. A target that turned after the last look turned out of the solution.

The sheet's own remarks say where Attack 3 went: "Heard two timed hits in this AK", and of the misses, "One miss due
to spread, the other probably due to target maneuver during torpedo run or to control errors".#note(cite: sh + "/p17")
The sheet types the hits but not which torpedoes made them.#note(cite: sh + "/p18") The sheet's triangle is the one the boat fired on; whether the target kept to it is a question for the other side's records.

#section-sources(titles: ("74802831": "USS Bang, August 1944 - September 1944"))
]
