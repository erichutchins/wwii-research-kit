// haynsworth.html: USS Haynsworth (DD-700), 6 April 1945, from both sides' records.
// Reads records/engagements/haynsworth-1945-04-06/{timeline,positions,claims}.csv (hand-edited) and
// records/ships/dd-700-haynsworth/positions.csv (her track), from RECORDS (config.js). The narrative steps are below
// (STEPS); the entries in each step come from timeline.csv's `step` column.
//
// A page that wants more can set window.HAYNSWORTH_EXTRA before this script loads (the family's copy does, to tell
// one man's part in it):
//   dir      a folder with notes.csv (file, match, field, text: rewords rows; match is "date time kind" for the
//            timeline, "question|claim" for claims), extra_claims.csv (claims added after the question named in
//            `after`) and people.csv (both crews, drawn into #crewlists)
//   steps    { stepId: body } replacing a step's text
//   mount41  the damage profile's second line for mount 41
//   mark     a pattern; crew rows whose name matches it are shaded

const EXTRA = window.HAYNSWORTH_EXTRA || null;
const ENG = RECORDS + "engagements/haynsworth-1945-04-06/";
// The records cite by key where a row has no page of its own (SOURCES.yml): a book, or a point placed on a modern map
const REF_LINKS = { irons: "https://www.kamikazeimages.net/books/ships/haynsworth/index.htm", "hand-placed": "" };
const refUrl = ref => ref in REF_LINKS ? REF_LINKS[ref] : ref;
function overlay(rows, file, notes, matchOf) {
  const keyed = rows.map(r => [matchOf(r), r]);   // match on the records' wording: a note may change a field the match uses
  for (const n of notes.filter(n => n.file === file))
    for (const [k, r] of keyed) if (k === n.match) r[n.field] = n.text;
  return rows;
}
const NM = 1852;

// Map views, as [[west, south], [east, north]]
const VIEWS = {
  theater: { name: "Kyushu to Okinawa", b: [[127.55, 25.95], [131.45, 31.95]] },
  charts: { name: "Kyushu to Okinawa, with Izumi", b: [[127.4, 25.7], [131.5, 32.25]] },
  approach: { name: "The Ryukyus, Amami to Okinawa", b: [[128.55, 26.2], [130.75, 27.95]] },
  picket: { name: "TG 58.3 and its pickets, about 50 nm across", b: [[128.95, 26.38], [129.98, 27.22]] },
  close: { name: "Haynsworth's station", b: [[129.36, 26.62], [129.86, 27.04]] },
};

// What each step shows. `on`: position ids drawn at full strength (others dim); `layers`: extra layers.
const STEPS = [
  { id: "s1", until: "0530", when: "5 April, 1700, to 6 April, 0530", view: "picket", title: "The picket line",
    body: "Fast carrier Task Group 58.3 (Essex, Bunker Hill, Hancock, Cabot, three battleships and their screen) was east of the Ryukyus, launching strikes on Okinawa and the islands to its north. Three destroyers were posted 12 miles out from the formation as radar pickets, to see raids coming and to put the fighters on them before they reached the carriers. Haynsworth took station #1, bearing 060° from the group, at 1700 on 5 April.",
    on: ["centre", "st-hay", "st-weeks", "st-walker", "tf-0530"], layers: ["ring", "formation", "haytrack"] },
  { id: "s2", until: "0800", when: "6 April, 0700-0800", view: "approach", title: "Found",
    body: "At 0800 a Saiun scout of Reconnaissance Squadron 11 reported four carriers at メツ三ス. The Japanese Navy gave positions as a kana code for a square 20 minutes of latitude by 20 of longitude, about 20 miles across. The squares on the map are our decoding of those codes from other Japanese reports, not a Japanese chart. If the scout's navigation had been exact, the carriers it saw would be inside its square. TG 58.3 was about 20 miles west of it at 0800. So either the scout saw TG 58.3 and was 20-30 miles out, which is ordinary for a plane navigating by dead reckoning over open sea, or it saw another of TF 58's carrier groups. Either way, this square is where the morning's Suisei were sent.",
    centre: "centre-0800", on: ["sq-metsu", "hay-0800", "centre-0800"], layers: ["squares", "haytrack", "formation", "ring"] },
  { id: "s3", until: "1020", when: "1015-1020", view: "theater", title: "Launch from Kyushu",
    body: "Fifth Air Fleet sent 30 bomb-carrying Zeros and 23 Suisei dive bombers (US code name Judy) off one after another from 1015. The 210th Air Group's eleven Suisei left First Kokubu at 1020. The line drawn is the straight course to their aiming point, about 300 miles: their actual route isn't recorded, and none of the seven that didn't return left a track chart.",
    on: ["kokubu", "aim-210", "aim-252a", "aim-252b", "sq-metsu"], layers: ["route210", "squares", "formation"] },
  { id: "s4", until: "1200", when: "1056-1200", view: "approach", title: "The fighters meet them",
    body: "The task group's combat air patrol met the raids to the north and north-east, on Haynsworth's side of the formation. Essex's fighters shot down two Judys at 1140, 35 miles out on 035°, and another at 1159, 20 miles due north. The 210th's escort, over Amami at 1140, fought Hellcats ten minutes later. At noon Haynsworth was at 26-55N 129-31E. Between 1130 and 1420 the scouts reported four carrier groups, two of them at メキ三ツ and スキ三ツ (the second a probable reading); TG 58.3 at noon was 25-40 miles south of both.",
    on: ["k-1056", "k-1140", "k-1149", "k-1159", "esc-1150", "hay-1200", "centre", "st-hay", "st-weeks", "st-walker", "sq-meki", "sq-suki"], layers: ["kills", "formation", "ring", "squares"] },
  { id: "s5", until: "1227", when: "1201-1227", view: "picket", title: "Into the formation",
    body: "Seven Zekes were caught 15 miles north at 1201. Under cover of that fight a Judy slipped into the formation and dived on Cabot at 1226; its bomb missed by 100 yards and the plane fell off her bow. Bunker Hill's Marine Corsairs came home from the melee one short: 1st Lt. J. H. Carpenter was last seen diving on an enemy plane.",
    on: ["k-1201", "k-1223", "cabot-1226", "centre", "st-hay", "st-weeks", "st-walker"], layers: ["kills", "formation", "ring"] },
  { id: "s6", until: "1245", when: "1230-1245", view: "picket", title: "Bogey at 22 miles",
    body: "The 210th's report presumes all seven of its Suisei dived into the carrier force between 1230 and 1300. At 1232 Haynsworth's SC-3 radar had a bogey bearing 010°, 22 miles; she turned to 020° and the fighters were vectored onto it. At 1245 her crew heard a dog-fight and machine-gun fire to port, and a plane was splashed 1,500 yards off the port quarter.",
    on: ["bogey-1232", "st-hay", "hay-1200", "centre"], layers: ["ring", "formation"] },
  { id: "s7", until: "1250", when: "1245-1250", view: "close", title: "1250 Item",
    body: "A Judy came out of the low cloud in a steep dive with a Corsair on either side. All three pulled out short of the water, and the Judy flattened out and headed away. Haynsworth opened fire at 1,500 yards; the Judy turned to starboard, winged over and came back. Its bomb fell 1,000 yards abeam. The plane struck at the twin 40 mm mount 41, abaft the bridge, at 1250. The panels below the map follow the report step by step.",
    on: ["hit", "st-hay", "hay-1200"], layers: ["hit", "ring"] },
  { id: "s8", until: "1337", when: "1250-1337", view: "picket", title: "Fire",
    body: "A gasoline fireball went through Main Radio, the 40 mm platform, CIC and plot. Seven men were dead. The fire was under control in about ten minutes and out in about fifty-five. With her radio and radar gone she couldn't report: the squadron diary logs the hit at 1318 and South Dakota at 1321, when word reached them. Ten minutes after the hit, a suicide Zeke clipped Cabot's radar, and a friendly 5-inch shell killed three men on North Carolina.",
    on: ["hit", "cabot-1302", "centre", "st-hay", "st-weeks", "st-walker"], layers: ["hit", "formation", "ring"] },
  { id: "s9", until: "2000", when: "1400-2000", view: "theater", title: "The afternoon",
    body: "The 210th sent two more Suisei at 1400. One plane's track chart survives: it reached its farthest point at 1535 under rain cloud, ten-tenths at 500-900 metres, somewhere east-southeast of Amami and close to the task group, saw nothing, and flew home past the Tokara islands. It is the clearest record of the weather the morning's attackers used. Haynsworth was at 27-23N 130-05E at 2000.",
    on: ["t2-1410", "t2-1535", "t2-1603", "t2-1702", "t2-1722", "t2-1750", "hay-2000", "kokubu"], layers: ["track2", "wx", "haytrack", "formation"] },
  { id: "s9b", until: "2000", when: "6 April, the other charts", view: "charts", title: "The other Japanese charts",
    body: "Three more units drew the day, and the scouts drew where they saw the carriers. The clock runs through the afternoon; each plane shows only its last forty minutes. The 252nd Air Group's attack chart has two routes from Kokubu: west of the Tokara islands to Yokoate-jima, then three legs fanning south before turning west into the Okinawa anchorage, and east to Amami and back. Its crews who came down on Kikai-jima met Grummans off Amami at 1430. The Izumi Zeros flew down the west side of the islands to Tokunoshima, saw an escort carrier group and turned back without a fight. A Kushira torpedo Tenzan staged through Kikai-jima that evening. The circles are the carrier groups the T11 scouts reported, shown in their hours (1130-1420 and 1505-1535), placed from the war history's sketch to about 15 miles. Where a chart gives no times, the planes move at an assumed 150 knots from their recorded take-off: the 252nd's routes and the Izumi Zeros' outbound leg are timed that way, and the chart doesn't say whether the 252nd's legs are the plan or the flight.",
    on: ["kokubu"], layers: ["jptracks"] },
  { id: "s10", until: "2000", when: "6-9 April", view: "approach", title: "Afterwards",
    body: "Eleven of the wounded went across to South Dakota that day and three more on the 7th; five of them died aboard her, bringing the dead to twelve. According to Irons' history, the men killed outright were buried at sea on the evening of the 7th. On 9 April she left the group with the damaged Hancock and Cabot for Ulithi, Pearl Harbor and Mare Island.",
    on: ["hay-2000", "centre"], layers: ["haytrack", "formation"] },
];

const tip = document.getElementById("tip");
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
// A citation as shown: Chicago short form, the book's short title in italics ("Irons, Phalanx, 327–30"); the full
// reference is in the Sources list (BOOKS)
const cite = s => esc(s).replace(/\bPhalanx\b/g, "<i>Phalanx</i>");
const BOOKS = [{ match: /\bIrons\b/, url: REF_LINKS.irons,
  html: "Irons, Martin. <i>Phalanx Against the Divine Wind: Protecting the Fast Carrier Task Force During World War 2</i>. Merriam Press, 2017." }];
const t4 = t => t ? t.slice(0, 2) + t.slice(2) : "";

// Japanese grid codes in the text -> the square they name on the map (メツミス is how the 210th's report writes メツ三ス)
const GRID = { "メツ三ス": "sq-metsu", "メツミス": "sq-metsu", "メキ三ツ": "sq-meki", "スキ三ツ": "sq-suki" };
const rich = text => esc(text).replace(/「?(メツ三ス|メツミス|メキ三ツ|スキ三ツ)」?/g, (m, code) =>
  `<span class="gref" tabindex="0" data-sq="${GRID[code]}" title="Show this square on the map">${m}</span>`);
function markRefs(id, on) { document.querySelectorAll(`.gref[data-sq="${id}"]`).forEach(e => e.classList.toggle("hot", on)); }
function wireRefs(map) {
  document.querySelectorAll(".gref").forEach(el => {
    const on = () => { map.highlight(el.dataset.sq, true); markRefs(el.dataset.sq, true); };
    const off = () => { map.highlight(el.dataset.sq, false); markRefs(el.dataset.sq, false); };
    el.addEventListener("mouseenter", on); el.addEventListener("mouseleave", off);
    el.addEventListener("focus", on); el.addEventListener("blur", off);
  });
}

// "27-11N" -> 27.183
function dm(s) {
  const m = /^(\d+)-(\d+(?:\.\d+)?)(?:-(\d+))?([NSEW])$/.exec((s || "").trim());
  if (!m) return null;
  const v = +m[1] + (+m[2]) / 60 + (m[3] ? +m[3] / 3600 : 0);
  return /[SW]/.test(m[4]) ? -v : v;
}
// destination on a sphere: start [lon, lat], bearing (deg true), distance (nm)
function dest([lon, lat], brg, nm) {
  const R = 6371008.8, d = nm * NM / R, b = brg * Math.PI / 180, p1 = lat * Math.PI / 180, l1 = lon * Math.PI / 180;
  const p2 = Math.asin(Math.sin(p1) * Math.cos(d) + Math.cos(p1) * Math.sin(d) * Math.cos(b));
  const l2 = l1 + Math.atan2(Math.sin(b) * Math.sin(d) * Math.cos(p1), Math.cos(d) - Math.sin(p1) * Math.sin(p2));
  return [l2 * 180 / Math.PI, p2 * 180 / Math.PI];
}

const none = Promise.resolve([]);
Promise.all([
  d3.csv(ENG + "timeline.csv"), d3.csv(ENG + "positions.csv"), d3.csv(ENG + "claims.csv"),
  EXTRA ? d3.csv(EXTRA.dir + "people.csv") : none, EXTRA ? d3.csv(EXTRA.dir + "notes.csv") : none,
  EXTRA ? d3.csv(EXTRA.dir + "extra_claims.csv") : none,
  d3.csv(RECORDS + "ships/dd-700-haynsworth/positions.csv"),
  d3.json("https://cdn.jsdelivr.net/npm/world-atlas@2/land-10m.json"), SILHOUETTES,
]).then(([timeline, positions, claims, people, notes, extraClaims, hay, world]) => {
  for (const rows of [timeline, positions, claims, extraClaims]) rows.forEach(r => { r.ref = refUrl(r.ref); });
  overlay(timeline, "timeline", notes, r => `${r.date} ${r.time} ${r.kind}`);
  overlay(claims, "claims", notes, r => `${r.question}|${r.claim}`);
  for (const c of extraClaims) {   // each after the last claim of the question named in its `after` column
    const i = claims.findLastIndex(r => r.question === c.after);
    claims.splice(i < 0 ? claims.length : i + 1, 0, c);
  }
  for (const [id, body] of Object.entries(EXTRA?.steps ?? {})) STEPS.find(s => s.id === id).body = body;
  // resolve positions (some are bearing and distance from another)
  const P = new Map(positions.map(p => [p.id, p]));
  const resolve = (p, depth = 0) => {
    if (p.ll) return p.ll;
    if (p.lat && p.lon) p.ll = [+p.lon, +p.lat];
    else if (p.from && depth < 5) p.ll = dest(resolve(P.get(p.from), depth + 1), +p.brg || 0, +p.nm || 0);
    if (p.lat2 && p.lon2) p.ll2 = [+p.lon2, +p.lat2];
    return p.ll;
  };
  positions.forEach(p => resolve(p));

  // Haynsworth's own track, 5 Apr 2000 to 7 Apr 0800 (diary fixes)
  const hayTrack = hay.filter(r => r.source === "diary" && r.on_track === "yes" && r.date >= "1945-04-05" && r.date <= "1945-04-06")
    .filter(r => !(r.date === "1945-04-05" && r.time < "2000"))
    .map(r => ({ date: r.date, time: r.time, ll: [dm(r.lon_fix || r.lon_raw), dm(r.lat_fix || r.lat_raw)], page: r.page }));

  buildSteps(timeline);
  const map = buildMap(world, positions, P, hayTrack);
  observeSteps(map);
  wireRefs(map);
  buildPanels();
  buildProfile();
  buildScale100();
  buildPath();
  buildOOB();
  buildBoard(claims);
  if (people.length) buildCrews(people);
  buildSources(timeline, claims);
});

// ---------- narrative ----------
function buildSteps(timeline) {
  const host = d3.select("#steps");
  STEPS.forEach((s, i) => {
    const rows = timeline.filter(r => r.step === s.id);
    const el = host.append("div").attr("class", "step").attr("data-i", i);
    const c = el.append("div").attr("class", "card");
    c.append("div").attr("class", "when").text(s.when);
    c.append("h3").text(s.title);
    c.append("p").html(rich(s.body));
    const ul = c.append("div").attr("class", "entries");
    rows.forEach(r => {
      const bar = r.kind === "hit" ? "var(--fire)" : r.side === "jp" ? "var(--japan)" : "var(--c1)";
      const li = ul.append("div").attr("class", "entry").attr("style", `--bar:${bar}`);
      li.append("div").attr("class", "t" + (r.placed ? " placed" : ""))
        .attr("title", r.placed || null)
        .html((r.time ? (r.placed ? "~" : "") + esc(r.time) : "—") + (r.date !== "1945-04-06" ? `<small>${esc(+r.date.slice(8))} Apr</small>` : ""));
      const d = li.append("div").attr("class", "body");
      d.append("div").attr("class", "who").html(`<b>${esc(r.actor)}</b>${r.placed ? `<span class="what">${esc(r.placed)}</span>` : ""}`);
      // wholly the record's words: its typed face; otherwise our words, quoting it
      const quoted = /^"[^"]+"\.?$/.test(r.text.trim());
      d.append("div").attr("class", quoted ? "said" : "text").html(rich(quoted ? r.text.trim().replace(/^"|"\.?$/g, "") : r.text));
      d.append("div").html(r.ref ? `<a class="src alone" href="${esc(r.ref)}" target="_blank" rel="noopener">${cite(r.source)}</a>` : `<span class="src alone">${cite(r.source)}</span>`);
    });
  });
}

function observeSteps(map) {
  const steps = [...document.querySelectorAll(".step")];
  let cur = -1;
  const set = i => {
    if (i === cur) return;
    cur = i;
    steps.forEach((s, j) => s.classList.toggle("active", j === i));
    map.show(STEPS[i]);
  };
  // the step whose middle is nearest the reading line (lower on phones, where the map sits on top)
  const pick = () => {
    const mid = window.innerHeight * (window.innerWidth <= 900 ? 0.75 : 0.5);
    let best = 0, bd = Infinity;
    steps.forEach((s, j) => { const r = s.getBoundingClientRect(); const d = Math.abs((r.top + r.bottom) / 2 - mid); if (d < bd) { bd = d; best = j; } });
    set(best);
  };
  window.addEventListener("scroll", pick, { passive: true });
  set(0); pick();
}

// ---------- map ----------
function buildMap(world, positions, P, hayTrack) {
  const svg = d3.select("#map");
  const box = svg.node().getBoundingClientRect();
  let W = box.width || 800, H = box.height || 600;
  const defs = svg.append("defs");
  const hatch = (id, cls, gap = 6) => defs.append("pattern").attr("id", id).attr("patternUnits", "userSpaceOnUse").attr("width", gap).attr("height", gap)
    .attr("patternTransform", "rotate(45)").append("line").attr("x1", 0).attr("y1", 0).attr("x2", 0).attr("y2", gap).attr("class", cls).attr("stroke-width", 1.2);
  hatch("hatch-jp", "stroke-jp", 7); hatch("hatch-wx", "stroke-jp", 5); hatch("hatch-us", "stroke-us", 6);
  defs.selectAll("pattern line").attr("stroke-opacity", 0.35);

  const theater = VIEWS.theater.b;
  const outline = { type: "MultiPoint", coordinates: [theater[0], theater[1]] };
  const proj = d3.geoMercator().fitExtent([[0, 0], [W, H]], outline);
  const path = d3.geoPath(proj);
  // only the land polygons near the theatre (clipping the world polygon inverts it)
  const near = ring => ring.some(([x, y]) => x > 124 && x < 135 && y > 22 && y < 35);
  const landAll = topojson.feature(world, world.objects.land);
  const polys = (landAll.features || [landAll]).flatMap(f => f.geometry.type === "MultiPolygon" ? f.geometry.coordinates : [f.geometry.coordinates]);
  const land = { type: "MultiPolygon", coordinates: polys.filter(poly => near(poly[0])) };

  const gWorld = svg.append("g");
  gWorld.append("path").datum(d3.geoGraticule().step([0.5, 0.5]).extent([[126, 24], [133, 33]])()).attr("class", "grat").attr("d", path);
  gWorld.append("path").datum(land).attr("class", "land").attr("d", path);
  const gOver = svg.append("g");
  const gLab = svg.append("g");

  let T = { k: 1, x: 0, y: 0 };
  const xy = ll => { const p = proj(ll); return [T.x + T.k * p[0], T.y + T.k * p[1]]; };
  // The reader's own zoom and pan (mapzoom.js) moves the same view the story's steps set; the next step takes it back,
  // and ⟲ returns to the step's view. The view is kept in d3's zoom state too (sync), so a drag starts where the step left it.
  let syncing = false;
  const setView = t => { T = { k: t.k, x: t.x, y: t.y }; gWorld.attr("transform", `translate(${T.x},${T.y}) scale(${T.k})`); render(); };
  const view = mapZoom(svg.node(), svg.node().parentNode, t => {
    if (syncing) return;
    d3.select(gWorld.node()).interrupt(); clearTimeout(zoomTo.late);
    setView(t);
  }, { min: 0.5, max: 80 });
  view.reset = () => { if (lastView) zoomTo(lastView); };
  const sync = () => { syncing = true; view.set(d3.zoomIdentity.translate(T.x, T.y).scale(T.k)); syncing = false; };

  // ---- overlay items: each has draw(sel) using xy(), and a set of ids/layers for show()
  const items = [];
  const sqG = new Map();   // grid squares by id, for highlighting from the text
  const add = (layer, ids, draw) => items.push({ layer, ids: [].concat(ids || []), draw, g: gOver.append("g").attr("class", "mk") });

  const placeLabels = [
    ["Kyushu", 130.55, 31.55], ["Tanegashima", 131.2, 30.55], ["Yakushima", 130.2, 30.2], ["Tokara Is.", 129.55, 29.6],
    ["Amami-Ōshima", 129.0, 28.42], ["Kikai", 130.15, 28.38], ["Tokunoshima", 128.6, 27.8], ["Okinoerabu", 128.35, 27.36],
    ["Yoron", 128.5, 27.02], ["Okinawa", 127.85, 26.55], ["Iheya", 127.75, 27.1],
  ];

  // Haynsworth's track
  add("haytrack", [], g => {
    const upto = current ? "1945-04-06 " + current.until : "9";
    const pts = hayTrack.filter(p => p.date + " " + p.time <= upto);
    g.selectAll("*").remove();
    g.append("path").attr("class", "trk us").attr("d", d3.line()(pts.map(p => xy(p.ll))));
    pts.forEach(p => {
      const [x, y] = xy(p.ll);
      g.append("circle").attr("cx", x).attr("cy", y).attr("r", 3).attr("class", "fill-us").style("stroke", "var(--surface)").style("stroke-width", 1)
        .on("mousemove", e => showTip(e, `<div class="v">Haynsworth, ${+p.date.slice(8)} Apr ${p.time}</div><div class="k">diary fix</div><div class="i">Click for the page</div>`))
        .on("mouseleave", hideTip).on("click", () => openPage(p.page));
    });
  });
  // picket ring (assumed centre)
  const centreId = () => (current && current.centre) || "centre";
  add("ring", ["centre", "centre-0800"], g => {
    const c = P.get(centreId()).ll; const ring = d3.range(0, 361, 5).map(b => xy(dest(c, b, 12)));
    g.selectAll("*").remove();
    g.append("path").attr("class", "ring").attr("d", d3.line()(ring));
    const [lx, ly] = xy(dest(c, 150, 12.6));
    g.append("text").attr("class", "mk-label small").attr("x", lx).attr("y", ly + 12).text(centreId() === "centre" ? "12 nm picket ring (centre assumed)" : "12 nm picket ring at 0800 (derived)");
  });
  // the formation, schematically
  add("formation", ["centre", "centre-0800"], g => {
    const c = P.get(centreId()).ll; g.selectAll("*").remove();
    const [x, y] = xy(c);
    const r = Math.max(6, Math.min(40, (xy(dest(c, 90, 2.5))[0] - x)));
    g.append("circle").attr("cx", x).attr("cy", y).attr("r", r).attr("fill", "url(#hatch-us)").attr("class", "stroke-us").attr("stroke-width", 1).attr("stroke-dasharray", "2 2");
    if (r > 12) {
      const k = r / 2.5;
      [[0, 0, 0.13], [1.1, 40, 0.12], [1.1, 160, 0.12], [1.1, 280, 0.12], [2, 100, 0.09], [2, 220, 0.09], [2, 340, 0.09]].forEach(([d, b, s]) => {
        const [sx, sy] = xy(dest(c, b, d));
        g.append("path").attr("d", hullPlan(0.24)).attr("class", "fill-us").attr("transform", `translate(${sx},${sy}) rotate(20) scale(${Math.max(8, k * s * 5)})`);
      });
    }
    g.append("text").attr("class", "mk-label").attr("x", x).attr("y", y + r + 14).attr("text-anchor", "middle").text(centreId() === "centre" ? "TG 58.3 (1200)" : "TG 58.3 (0800, derived)");
    g.on("mousemove", e => showTip(e, `<div class="v">TG 58.3 (schematic)</div><div class="m">Essex, Bunker Hill, Hancock, Cabot; South Dakota, North Carolina, Washington; cruisers and destroyers. Ship positions inside the formation aren't recorded; the circle is centred on South Dakota's 1200 fix.</div>`))
      .on("mouseleave", hideTip).on("click", () => openRef(P.get("sd-1200").ref));
  });
  // scout squares
  positions.filter(p => p.kind === "square").forEach(p => add("squares", [p.id], g => {
    sqG.set(p.id, g);
    g.on("mouseenter.hl", () => markRefs(p.id, true)).on("mouseleave.hl", () => markRefs(p.id, false));
    g.selectAll("*").remove();
    const [a, b] = [xy([p.ll[0], p.ll2[1]]), xy([p.ll2[0], p.ll[1]])];
    g.append("rect").attr("class", "sq" + (p.basis === "probable" ? " probable" : "")).attr("x", a[0]).attr("y", a[1]).attr("width", b[0] - a[0]).attr("height", b[1] - a[1]);
    g.append("text").attr("class", "mk-label jp").attr("x", a[0] + 4).attr("y", a[1] - 5).text(p.label.split(":")[0]);
    tipFor(g, p);
  }));
  // 210th's assumed route
  add("route210", ["kokubu", "aim-210"], g => {
    g.selectAll("*").remove();
    const a = P.get("kokubu").ll, b = P.get("aim-210").ll;
    const line = d3.range(0, 1.0001, 0.05).map(t => xy(d3.geoInterpolate(a, b)(t)));
    g.append("path").attr("class", "trk jp assumed").attr("d", d3.line()(line));
    const m = xy(d3.geoInterpolate(a, b)(0.45));
    planeAt(g, "judy", m, bearingTo(a, b), 22, "fill-jp");
    g.append("text").attr("class", "mk-label jp").attr("x", m[0] + 16).attr("y", m[1]).text("210th, 11 Suisei, 1020 (route assumed)");
  });
  // CAP kills: the Japanese type, crossed out, in the US aircraft colour
  const killType = { "k-1056": "dinah", "k-1140": "judy", "k-1149": "zeke", "k-1159": "judy", "k-1201": "zeke", "k-1223": "zeke" };
  positions.filter(p => p.kind === "kill").forEach(p => add("kills", [p.id], g => {
    g.selectAll("*").remove();
    const [x, y] = xy(p.ll);
    if (killType[p.id]) planeAt(g, killType[p.id], [x, y], 200, 16, "fill-jp");
    g.append("path").attr("d", `M${x - 7},${y - 7}L${x + 7},${y + 7}M${x - 7},${y + 7}L${x + 7},${y - 7}`).attr("class", "stroke-air").attr("stroke-width", 2.4).attr("fill", "none");
    g.append("text").attr("class", "mk-label small").attr("x", x + 10).attr("y", y - 6).text(p.time + " " + p.label.replace(/ shot down.*| splashed.*| intercepted/, ""));
    tipFor(g, p);
  }));
  // generic point marks
  const pointKinds = { fix: "us", reported: "us", station: "us", base: "jp", aim: "jp", fight: "jp", attack: "us", radar: "us" };
  positions.filter(p => pointKinds[p.kind] && p.ll && !p.id.startsWith("hay-") && !/^(tz-|iz-|c252-|fig32-)/.test(p.id)).forEach(p => add(null, [p.id], g => {
    g.selectAll("*").remove();
    const [x, y] = xy(p.ll); const side = pointKinds[p.kind];
    if (p.kind === "station") {
      g.append("path").attr("d", hullPlan(0.24)).attr("class", "fill-us").attr("transform", `translate(${x},${y}) rotate(${p.id === "st-hay" ? 20 : 0}) scale(18)`);
      if (!(p.id === "st-hay" && current && current.layers.includes("hit")))   // the hit's own label says it
        g.append("text").attr("class", "mk-label").attr("x", x + 9).attr("y", y + 4).text(p.label.replace("Picket station #1: ", "#1 ").replace("Picket: ", ""));
    } else if (p.kind === "aim") {
      g.append("path").attr("d", `M${x - 6},${y}L${x + 6},${y}M${x},${y - 6}L${x},${y + 6}`).attr("class", "stroke-jp").attr("stroke-width", 1.5);
      g.append("circle").attr("cx", x).attr("cy", y).attr("r", 5).attr("fill", "none").attr("class", "stroke-jp").attr("stroke-width", 1.2);
      g.append("text").attr("class", "mk-label jp").attr("x", x + 8).attr("y", y + 12).text(p.label.replace(/ aiming point/, ""));
    } else if (p.kind === "base") {
      g.append("rect").attr("x", x - 4).attr("y", y - 4).attr("width", 8).attr("height", 8).attr("class", "fill-jp");
      g.append("text").attr("class", "mk-label jp").attr("x", x + 8).attr("y", y + 4).text(p.label.replace(/ airfield.*$/, ""));
    } else if (p.kind === "radar") {
      const h = P.get("hay-1200").ll; const a = xy(h);
      g.append("path").attr("d", `M${a[0]},${a[1]}L${x},${y}`).attr("class", "stroke-us").attr("stroke-dasharray", "1 4").attr("stroke-width", 1.6);
      g.append("circle").attr("cx", x).attr("cy", y).attr("r", 5).attr("fill", "none").attr("class", "stroke-us").attr("stroke-width", 1.6);
      g.append("text").attr("class", "mk-label").attr("x", x + 8).attr("y", y + 4).text("1232 bogey, 010° 22 mi");
    } else if (p.kind === "attack") {
      planeAt(g, p.id === "cabot-1302" ? "zeke" : "judy", [x, y], 160, 18, "fill-jp");
      g.append("text").attr("class", "mk-label small").attr("x", x + 12).attr("y", y + 16).text(p.time + " " + p.label);
    } else {
      g.append("circle").attr("cx", x).attr("cy", y).attr("r", 3.5).attr("class", "fill-" + side);
      g.append("text").attr("class", "mk-label small").attr("x", x + 7).attr("y", y + 4).text(p.label);
    }
    tipFor(g, p);
  }));
  // Haynsworth's noon and other fixes, labelled (the dots are drawn by the track)
  ["hay-0800", "hay-1200", "hay-2000"].forEach(id => add(null, [id], g => {
    const p = P.get(id); g.selectAll("*").remove();
    const [x, y] = xy(p.ll);
    g.append("circle").attr("cx", x).attr("cy", y).attr("r", 5).attr("fill", "none").attr("class", "stroke-us").attr("stroke-width", 1.5);
    g.append("text").attr("class", "mk-label").attr("x", x - 8).attr("y", y - 6).attr("text-anchor", "end").text("Haynsworth " + p.time);
    tipFor(g, p);
  }));
  // the hit
  add("hit", ["hit"], g => {
    const p = P.get("hit"); g.selectAll("*").remove();
    const [x, y] = xy(p.ll);
    g.append("circle").attr("cx", x).attr("cy", y).attr("r", 16).attr("class", "pulse").attr("opacity", 0.5);
    g.append("circle").attr("cx", x).attr("cy", y).attr("r", 7).attr("class", "fill-hit");
    g.append("text").attr("class", "mk-label").attr("x", x + 18).attr("y", y + 4).text("Hit, 1250");
    tipFor(g, p);
  });
  // the second attack's track (p12)
  add("track2", ["t2-1410", "t2-1535", "t2-1603", "t2-1702", "t2-1722", "t2-1750"], g => {
    g.selectAll("*").remove();
    const pts = positions.filter(p => p.kind === "track" && p.id.startsWith("t2-")).sort((a, b) => a.time.localeCompare(b.time));
    g.append("path").attr("class", "trk jp").attr("d", d3.line()(pts.map(p => xy(p.ll))));
    pts.forEach(p => {
      const [x, y] = xy(p.ll);
      const c = g.append("g");
      c.append("circle").attr("cx", x).attr("cy", y).attr("r", p.basis === "fix" ? 3.5 : 5).attr("class", p.basis === "fix" ? "fill-jp" : "").attr("fill", p.basis === "fix" ? null : "url(#hatch-jp)").attr("stroke", "var(--japan)");
      c.append("text").attr("class", "mk-label small").attr("x", x + 7).attr("y", y + 4).text(p.time);
      tipFor(c, p);
    });
    const m = xy(P.get("t2-1535").ll);
    g.append("text").attr("class", "mk-label jp").attr("x", m[0] + 10).attr("y", m[1] + 18).text("210th second attack, No. 2 plane (track chart)");
  });
  // the other Japanese charts of the day, animated: a clock runs 0900-2000 and each plane (and Haynsworth) shows only a
  // fading streak of its last STREAK minutes. Times are the charts' where they give them; elsewhere planes move at an
  // assumed ASSUMED_KT from their recorded take-off (labelled on the page). The scouts' carrier groups (fig32) show only
  // in their reported windows. With reduced motion, the paths are drawn faint and still.
  const STREAK = 40, ASSUMED_KT = 150, T0 = 9 * 60, T1 = 20 * 60;
  const jpIds = positions.filter(p => /^(tz-|iz-|c252-|fig32-)/.test(p.id) && p.ll).map(p => p.id);
  STEPS.find(st => st.id === "s9b").on.push(...jpIds);   // the step lights every point of these charts
  const mins = hhmm => +hhmm.slice(0, 2) * 60 + +hhmm.slice(2, 4);
  const nmBetween = (a, b) => {
    const r = Math.PI / 180, [l1, p1, l2, p2] = [a[0] * r, a[1] * r, b[0] * r, b[1] * r];
    return 2 * Math.asin(Math.sqrt(Math.sin((p2 - p1) / 2) ** 2 + Math.cos(p1) * Math.cos(p2) * Math.sin((l2 - l1) / 2) ** 2)) * 3440.065;
  };
  // a route: [id or ll, time "HHMM" or null]; untimed points get times at ASSUMED_KT from the last timed one
  const route = legs => {
    const pts = legs.map(([at, t]) => ({ ll: typeof at === "string" ? P.get(at) && P.get(at).ll : at, t: t ? mins(t) : null }))
      .filter(q => q.ll);
    for (let k = 1; k < pts.length; k++) if (pts[k].t === null) {
      pts[k].t = pts[k - 1].t + nmBetween(pts[k - 1].ll, pts[k].ll) / ASSUMED_KT * 60; pts[k].assumed = true;
    }
    return pts;
  };
  // between two timed points with untimed ones in between, spread the time by distance (no assumed speed)
  const spread = (pts, a, b) => {
    let d = 0; const cum = [0];
    for (let k = a + 1; k <= b; k++) { d += nmBetween(pts[k - 1].ll, pts[k].ll); cum.push(d); }
    for (let k = a + 1; k < b; k++) { pts[k].t = pts[a].t + (pts[b].t - pts[a].t) * cum[k - a] / d; pts[k].assumed = true; }
    return pts;
  };
  let movers = null;
  const buildMovers = () => {
    const timed = pre => positions.filter(p => p.id.startsWith(pre) && p.ll && p.kind === "track" && p.time && p.date === "1945-04-06")
      .sort((a, b) => a.time.localeCompare(b.time)).map(p => ({ ll: p.ll, t: mins(p.time) }));
    const east3 = spread(route([["kokubu", "1305"], ["c252-am", "1430"], ["c252-3d", null], ["c252-am", null], ["kikai-ref", "1550"]]), 1, 4);
    movers = [
      { name: "Haynsworth", us: true, pts: hayTrack.filter(p => p.date === "1945-04-06").map(p => ({ ll: p.ll, t: mins(p.time) })) },
      { name: "210th No. 2", pts: timed("t2-") },
      { name: "Kushira Tenzan", pts: timed("tz-") },
      { name: "Izumi Zeros", pts: route([["iz-0900", "0900"], ["iz-turn", null]]) },
      { name: "252nd 3D", pts: east3 },
      { name: "252nd 2D", pts: route([["kokubu", "1310"], ["kikai-ref", null], ["c252-2d", null], ["kikai-ref", null]]) },
      { name: "252nd 1-2/34D", pts: route([["kokubu", "1310"], ["c252-yw", null], ["c252-34a", null], ["c252-oki", null]]) },
      { name: "252nd 3-4/34D", pts: route([["kokubu", "1310"], ["c252-yw", null], ["c252-34b", null], ["c252-oki", null]]) },
      { name: "252nd 33D", pts: route([["kokubu", "1310"], ["c252-yw", null], ["c252-33", null], ["c252-oki", null]]) },
    ].filter(m => m.pts.length > 1);
  };
  const at = (pts, t) => {   // position at time t, or null outside the route's times
    if (t < pts[0].t || t > pts[pts.length - 1].t) return null;
    for (let k = 1; k < pts.length; k++) if (t <= pts[k].t) {
      const a = pts[k - 1], b = pts[k], f = b.t === a.t ? 1 : (t - a.t) / (b.t - a.t);
      return [a.ll[0] + (b.ll[0] - a.ll[0]) * f, a.ll[1] + (b.ll[1] - a.ll[1]) * f];
    }
    return null;
  };
  const windows = { "fig32-a2b2": [905, 935], "fig32-a3b4": [905, 935], "fig32-1130a": [690, 860], "fig32-1130b": [690, 860], "fig32-1130c": [690, 860] };
  const still = matchMedia("(prefers-reduced-motion: reduce)").matches;
  let clock = T0, lastFrame = null, raf = null;
  const fmt = t => String(Math.floor(t / 60)).padStart(2, "0") + String(Math.floor(t % 60)).padStart(2, "0");
  add("jptracks", jpIds, g => {
    if (!movers) buildMovers();
    g.selectAll("*").remove();
    if (still) {
      movers.forEach(m => g.append("path").attr("class", "trk " + (m.us ? "us" : "jp")).style("opacity", 0.35).attr("d", d3.line()(m.pts.map(q => xy(q.ll)))));
    } else {
      const labelled = [];
      movers.forEach(m => {
        const head = at(m.pts, clock); if (!head) return;
        const assumed = m.pts.some(q => q.assumed);
        // the streak: STREAK minutes in short pieces, fading toward the tail
        const n = 8;
        for (let k = 0; k < n; k++) {
          const ta = clock - STREAK * (k + 1) / n, tb = clock - STREAK * k / n;
          const a = at(m.pts, Math.max(ta, m.pts[0].t)), b = at(m.pts, Math.max(tb, m.pts[0].t));
          if (a && b) g.append("path").attr("class", "trk " + (m.us ? "us" : "jp")).style("opacity", 1 - k / n).style("stroke-dasharray", assumed ? "4 3" : "none").attr("d", d3.line()([xy(a), xy(b)]));
        }
        const [x, y] = xy(head);
        g.append("circle").attr("cx", x).attr("cy", y).attr("r", 3.5).attr("class", m.us ? "fill-us" : "fill-jp");
        if (labelled.some(([a, b]) => Math.hypot(a - x, b - y) < 14)) return;   // one label where heads coincide
        labelled.push([x, y]);
        g.append("text").attr("class", "mk-label small" + (m.us ? "" : " jp")).attr("x", x + 6).attr("y", y - 5).text(m.name + (assumed ? " (times assumed)" : ""));
      });
    }
    // the scouts' carrier groups, in their windows (always, when still)
    positions.filter(p => p.id.startsWith("fig32-") && windows[p.id] && p.ll).forEach(p => {
      const [w0, w1] = windows[p.id];
      if (!still && (clock < w0 - 10 || clock > w1 + 10)) return;
      const [x, y] = xy(p.ll); const c = g.append("g");
      c.append("circle").attr("cx", x).attr("cy", y).attr("r", 6).attr("fill", "none").attr("stroke", "var(--japan)");
      c.append("text").attr("class", "mk-label small").attr("x", x + 8).attr("y", y + 4).text(p.label.replace("T11 sketch: ", ""));
      tipFor(c, p);
    });
    // the bases stay put
    ["kokubu", "iz-0900"].forEach(id => { const p = P.get(id); if (!p || !p.ll) return; const [x, y] = xy(p.ll);
      const c = g.append("g"); c.append("rect").attr("x", x - 3).attr("y", y - 3).attr("width", 6).attr("height", 6).attr("class", "fill-jp"); tipFor(c, p); });
  });
  // the clock: about 40 seconds for the day, a pause at 2000, then again; runs only while the step is showing
  const tick = now => {
    raf = null;
    if (!current || current.id !== "s9b") { lastFrame = null; return; }
    if (lastFrame !== null) clock += (now - lastFrame) / 1000 * ((T1 - T0) / 40);
    lastFrame = now;
    if (clock > T1 + 60) clock = T0;   // the extra hour holds the end on screen before it starts again
    d3.select("#clock").html(`6 April, ${fmt(Math.min(clock, T1))}<small>Item</small>`);
    const it = items.find(o => o.layer === "jptracks"); if (it) it.draw(it.g);
    raf = requestAnimationFrame(tick);
  };
  const startClock = () => { if (!still && raf === null && current && current.id === "s9b") { lastFrame = null; raf = requestAnimationFrame(tick); } };
  add("wx", ["t2-1535"], g => {
    g.selectAll("*").remove();
    const c = P.get("t2-1535").ll; const ring = d3.range(0, 361, 15).map(b => xy(dest(c, b, 18 + 4 * Math.sin(b * 0.07))));
    g.append("path").attr("class", "wx").attr("d", d3.line().curve(d3.curveCatmullRomClosed)(ring.slice(0, -1)));
    const [x, y] = xy(dest(c, 200, 20));
    g.append("text").attr("class", "mk-label small").attr("x", x - 60).attr("y", y + 14).text("雨雲 rain cloud, 10/10, base 500-900 m (1535)");
  });
  // place names
  const drawLabels = () => {
    gLab.selectAll("*").remove();
    placeLabels.forEach(([n, lon, lat]) => { const [x, y] = xy([lon, lat]); gLab.append("text").attr("class", "place").attr("x", x).attr("y", y).text(n); });
  };

  // ---- legend
  const lg = d3.select("#legend");
  const sw = (svgInner, text) => lg.append("span").html(`<svg width="22" height="12" viewBox="0 0 22 12">${svgInner}</svg>${text}`);
  sw(`<path d="M1,6H21" class="trk us"/><circle cx="11" cy="6" r="3" class="fill-us"/>`, "Haynsworth's diary fixes");
  sw(`<path d="M1,6H21" class="trk jp"/>`, "Japanese track (chart)");
  sw(`<path d="M1,6H21" class="trk jp assumed"/>`, "Assumed route");
  sw(`<path d="M5,2L13,10M5,10L13,2" class="stroke-air" stroke-width="2.2" fill="none"/>`, "Shot down by US fighters");
  sw(`<rect x="2" y="1" width="18" height="10" class="sq"/>`, "Japanese grid square (decoded)");
  sw(`<circle cx="11" cy="6" r="5" class="fill-hit"/>`, "The hit");

  // ---- show a step
  let current = null;
  function render() {
    items.forEach(it => it.draw(it.g));
    drawLabels();
    applyVisibility();
  }
  function applyVisibility() {
    if (!current) return;
    const on = new Set(current.on), layers = new Set(current.layers);
    items.forEach(it => {
      const visibleLayer = it.layer ? layers.has(it.layer) : true;
      const lit = it.ids.some(id => on.has(id)) || (it.layer && layers.has(it.layer) && !it.ids.length);
      const strict = it.layer === "kills" || it.layer === "squares";   // these belong to their own step
      it.g.classed("off", !visibleLayer || (!it.layer && !lit && !isNear(it)) || (strict && !lit))
        .classed("dim", visibleLayer && !lit && !(it.layer && layers.has(it.layer)));
    });
  }
  // marks without a layer show only in steps that name them, except in the step's own view when close by
  const isNear = () => false;

  const targetFor = view => {
    const [[w, s], [e, n]] = VIEWS[view].b;
    const a = proj([w, n]), b = proj([e, s]);
    return [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2, Math.max(b[0] - a[0], (b[1] - a[1]) * W / H)];
  };
  function zoomTo(view, animate = true) {
    const target = targetFor(view);
    const from = [(W / 2 - T.x) / T.k, (H / 2 - T.y) / T.k, W / T.k];
    const set = ([cx, cy, w]) => { const k = W / w; setView({ k, x: W / 2 - k * cx, y: H / 2 - k * cy }); sync(); };
    if (!animate || matchMedia("(prefers-reduced-motion: reduce)").matches) { set(target); return; }
    const interp = d3.interpolateZoom(from, target);
    const ms = Math.min(1600, Math.max(500, interp.duration * 0.6));
    d3.select(gWorld.node()).interrupt().transition().duration(ms).ease(d3.easeCubicInOut)
      .tween("zoom", () => t => set(interp(t)));
    // if animation frames are throttled (a hidden tab), land on the view anyway
    clearTimeout(zoomTo.late); zoomTo.late = setTimeout(() => { d3.select(gWorld.node()).interrupt(); set(targetFor(view)); }, ms + 250);
  }
  let lastView = null;
  function show(step) {
    measure();
    current = step;
    d3.select("#clock").html(`${esc(step.when)}<small>Item</small>`);
    d3.select("#viewname").text(VIEWS[step.view].name);
    if (step.view !== lastView) { const first = lastView === null; lastView = step.view; zoomTo(step.view, !first); }
    render();
    startClock();
  }
  // refit when the stage's size changes (it isn't laid out yet when the map is built)
  function measure() {
    const b = svg.node().getBoundingClientRect();
    if (!b.width || !b.height || (Math.abs(b.width - W) < 2 && Math.abs(b.height - H) < 2)) return false;
    W = b.width; H = b.height; proj.fitExtent([[0, 0], [W, H]], outline);
    gWorld.selectAll("path").attr("d", path);
    d3.select(gWorld.node()).interrupt(); clearTimeout(zoomTo.late);
    T = { k: 1, x: 0, y: 0 }; sync();
    if (lastView) zoomTo(lastView, false);
    return true;
  }
  new ResizeObserver(() => measure()).observe(svg.node());
  // light up a grid square (from a code in the text), showing it even if the step doesn't
  function highlight(id, on) { const g = sqG.get(id); if (g) g.classed("hot", on).raise(); }
  const api = { show, zoomTo, xy, highlight, state: () => ({ T, W, H, lastView }) };
  window._hmap = api;
  return api;
}

function bearingTo(a, b) {
  const [l1, p1, l2, p2] = [a[0], a[1], b[0], b[1]].map(v => v * Math.PI / 180);
  const y = Math.sin(l2 - l1) * Math.cos(p2), x = Math.cos(p1) * Math.sin(p2) - Math.sin(p1) * Math.cos(p2) * Math.cos(l2 - l1);
  return (Math.atan2(y, x) * 180 / Math.PI + 360) % 360;
}
// an aircraft plan view centred at [x, y], nose toward `hdg`, `size` px span
function planeAt(g, type, [x, y], hdg, size, cls) {
  const a = AIRCRAFT[type].plan, s = size / a.w;
  return g.append("path").attr("d", a.d).attr("class", cls)
    .attr("transform", `translate(${x},${y}) rotate(${hdg}) scale(${s}) translate(${-a.w / 2},${-a.h / 2})`);
}
function tipFor(g, p) {
  g.attr("tabindex", 0).attr("role", "link").attr("aria-label", p.label)
    .on("mousemove", e => showTip(e, `<div class="v">${esc(p.label)}</div><div class="k">${esc(p.time ? p.time + " Item" : "")}${p.basis ? " · " + esc(p.basis) : ""}</div>${p.note ? `<div class="m">${esc(p.note)}</div>` : ""}<div class="i">${esc(p.source)}${p.ref ? " · click for the page" : ""}</div>`))
    .on("mouseleave", hideTip).on("click", () => openRef(p.ref)).on("keydown", e => { if (e.key === "Enter") openRef(p.ref); });
}
function showTip(e, html) { tip.innerHTML = html; tip.hidden = false; const w = tip.offsetWidth, h = tip.offsetHeight; tip.style.left = Math.min(innerWidth - w - 8, e.clientX + 14) + "px"; tip.style.top = Math.min(innerHeight - h - 8, e.clientY + 14) + "px"; }
function hideTip() { tip.hidden = true; }
function openRef(u) { if (u) window.open(u, "_blank", "noopener"); }
// "rg367-633422068/p03" -> the NARA catalog page
function openPage(page) {
  const m = /^rg367-(\d+)\/p(\d+)$/.exec(page || ""); if (m) openRef(`https://catalog.archives.gov/id/${m[1]}?objectPage=${+m[2]}`);
}

// ---------- attack panels ----------
function buildPanels() {
  const host = d3.select("#panels");
  const S = 220, C = S / 2, HDG = 20;
  // trueP: a true bearing; polar: relative to the bow (000 ahead, 090 starboard beam, 270 port beam)
  const trueP = (brg, r) => { const a = (brg - 90) * Math.PI / 180; return [C + r * Math.cos(a), C + r * Math.sin(a)]; };
  const polar = (rel, r) => trueP(HDG + rel, r);
  const add2 = (a, b) => [a[0] + b[0] - C, a[1] + b[1] - C];
  const hitPt = add2(polar(0, 6), polar(90, 3));   // abaft the bridge, starboard side (hull drawn 58 px long)
  const panels = [
    { n: "1232", cap: `Course changed to 020°. SC-3 radar: <q>bogey at 010°, distance 22 miles</q>. Fighters vectored out <q>merged with bogey on scope until raid had passed close aboard port beam</q>.`,
      draw: g => { arrow(g, trueP(10, 100), trueP(10, 42), "stroke-us", true); label(g, add2(trueP(10, 96), [C - 8, C + 4]), "bogey 010°, 22 mi", "end"); } },
    { n: "1245", cap: `<q>The sound of dog-fight and machine gun fire</q>, tracked from the port bow to the beam. A plane (<q>a Judy or Zeke</q>) splashed 1,500 yards on the port quarter.`,
      draw: g => { arcAt(g, 315, 270, 72); label(g, polar(300, 90), "dog-fight heard", "middle"); cross(g, polar(225, 72)); label(g, add2(polar(225, 72), [C + 10, C + 18]), "splashed, 1,500 yd", "start"); } },
    { n: "after 1245", cap: `A Judy <q>appeared out of the clouds in a very steep dive</q> with a Corsair on each side. All three <q>pulled up sharply short of the water</q>; the Corsairs went back into the cloud and the Judy <q>headed away from the ship</q>. Where, the report doesn't say; it is drawn on the side it came back from.`,
      draw: g => { plane(g, "corsair", polar(82, 58), HDG + 150, 22, "fill-air"); plane(g, "corsair", polar(118, 62), HDG + 150, 22, "fill-air"); plane(g, "judy", polar(100, 64), HDG + 120, 26, "fill-jp");
        label(g, add2(polar(100, 64), [C, C + 34]), "position not recorded", "middle", true); } },
    { n: "1250", cap: `Fire opened at 1,500 yards, altitude 150 ft. The Judy turned to starboard, <q>winged over</q> into the ship. Its bomb, <q>released or ... knocked off in the turn</q>, fell 1,000 yards abeam (the side isn't stated). <q>Striking at 1250 Item</q> abaft the bridge.`,
      draw: g => { arrowCurve(g, polar(52, 80), polar(40, 46), add2(hitPt, polar(70, 8))); plane(g, "judy", polar(52, 86), HDG + 230, 24, "fill-jp"); splash(g, polar(92, 92)); label(g, add2(polar(92, 92), [C + 8, C + 18]), "bomb, 1,000 yd abeam", "end");
        g.append("circle").attr("cx", hitPt[0]).attr("cy", hitPt[1]).attr("r", 6).attr("class", "fill-hit"); } },
  ];
  let G;
  const label = (g, [x, y], t, anchor = "start", it = false) => g.append("text").attr("class", "mk-label small").attr("x", x).attr("y", y).attr("text-anchor", anchor).style("font-style", it ? "italic" : null).text(t);
  const arrow = (g, a, b, cls, dashed) => g.append("path").attr("d", `M${a[0]},${a[1]}L${b[0]},${b[1]}`).attr("class", cls).attr("stroke-width", 1.6).attr("stroke-dasharray", dashed ? "3 3" : null).attr("marker-end", "url(#arr)").attr("fill", "none");
  const arrowCurve = (g, a, m, b) => g.append("path").attr("d", `M${a[0]},${a[1]}Q${m[0]},${m[1]} ${b[0]},${b[1]}`).attr("class", "stroke-jp").attr("stroke-width", 1.6).attr("stroke-dasharray", "4 3").attr("fill", "none").attr("marker-end", "url(#arr)");
  const arcAt = (g, b0, b1, r) => { const pts = d3.range(b0, b1 - 1, -4).map(b => polar(b, r)); g.append("path").attr("d", d3.line()(pts)).attr("class", "stroke-us").attr("stroke-width", 1.4).attr("stroke-dasharray", "2 3").attr("fill", "none"); };
  const cross = (g, [x, y]) => g.append("path").attr("d", `M${x - 6},${y - 6}L${x + 6},${y + 6}M${x - 6},${y + 6}L${x + 6},${y - 6}`).attr("class", "stroke-air").attr("stroke-width", 2.2);
  const splash = (g, [x, y]) => g.append("path").attr("d", `M${x - 7},${y}Q${x - 3},${y - 10} ${x},${y - 2}Q${x + 3},${y - 10} ${x + 7},${y}`).attr("class", "stroke-jp").attr("fill", "none").attr("stroke-width", 1.4);
  const plane = (g, type, p, hdg, size, cls) => planeAt(g, type, p, hdg, size, cls);

  panels.forEach(pn => {
    const c = host.append("div").attr("class", "card panel");
    c.append("div").attr("class", "num").text(pn.n);
    const svg = c.append("svg").attr("viewBox", `0 0 ${S} ${S}`).attr("role", "img").attr("aria-label", pn.n);
    if (!document.getElementById("arr")) svg.append("defs").append("marker").attr("id", "arr").attr("viewBox", "0 0 10 10").attr("refX", 9).attr("refY", 5).attr("markerWidth", 6).attr("markerHeight", 6).attr("orient", "auto-start-reverse")
      .append("path").attr("d", "M0,0L10,5L0,10Z").attr("fill", "var(--ink-2)");
    svg.append("circle").attr("cx", C).attr("cy", C).attr("r", 104).attr("fill", "none").attr("stroke", "var(--rule)");
    svg.append("text").attr("class", "mk-label small").attr("x", C).attr("y", 12).attr("text-anchor", "middle").text("N");
    svg.append("path").attr("d", hullPlan(0.11)).attr("class", "fill-us").attr("transform", `translate(${C},${C}) rotate(${HDG}) scale(58)`);
    svg.append("text").attr("class", "mk-label small").attr("x", polar(200, 40)[0]).attr("y", polar(200, 40)[1]).attr("text-anchor", "middle").text("020°");
    pn.draw(svg);
    c.append("div").attr("class", "cap").html(pn.cap);
  });
}

// ---------- damage profile ----------
function buildProfile() {
  const s = SHIPS.sumner, L = s.length, W = 1000, pad = 40, k = (W - 2 * pad) / L, H = 260, wl = 170;
  const svg = d3.select("#profile").attr("viewBox", `0 0 ${W} ${H}`);
  const defs = svg.append("defs");
  defs.append("pattern").attr("id", "hatch-fire").attr("patternUnits", "userSpaceOnUse").attr("width", 5).attr("height", 5).attr("patternTransform", "rotate(45)")
    .append("line").attr("x1", 0).attr("y1", 0).attr("x2", 0).attr("y2", 5).attr("class", "stroke-hit").attr("stroke-width", 1.6);
  const X = ft => pad + ft * k, Y = ft => wl - ft * k;
  // frames: 21 in apart, frame 0 at the forward perpendicular, after perpendicular at frame 210 (BuShips plans
  // DD692-S-01030-1 and DD692-S0101-601245; docs/HAYNSWORTH.md). AP pinned where the silhouette's stern meets the
  // waterline (x = 4 ft), which fits its stacks to the plan better than pinning FP to its stem
  const FR = f => 4 + (210 - f) * 21 / 12;
  const band = [FR(88), FR(65)];
  svg.append("rect").attr("x", X(band[0])).attr("y", Y(48)).attr("width", (band[1] - band[0]) * k).attr("height", (48 - 13) * k).attr("class", "dmg").attr("opacity", 0.9);
  svg.append("path").attr("d", s.d).attr("class", "sil").attr("transform", `translate(${pad},${wl}) scale(${k})`);
  svg.append("rect").attr("x", X(band[0])).attr("y", Y(48)).attr("width", (band[1] - band[0]) * k).attr("height", (48 - 13) * k).attr("fill", "url(#hatch-fire)").attr("stroke", "var(--fire)").attr("stroke-width", 1.5);
  svg.append("line").attr("x1", X(0)).attr("x2", X(L)).attr("y1", wl).attr("y2", wl).attr("stroke", "var(--ink-3)");
  for (let f = 0; f <= 210; f += 10) {
    const x = X(FR(f)); if (x < pad - 1) continue;
    svg.append("line").attr("class", "frame-tick").attr("x1", x).attr("x2", x).attr("y1", wl + 4).attr("y2", wl + (f % 50 ? 9 : 14));
    if (f % 20 === 0 || f === 65 || f === 88) svg.append("text").attr("class", "frame-lab").attr("x", x).attr("y", wl + 26).attr("text-anchor", "middle").text(f);
  }
  [65, 88].forEach(f => svg.append("text").attr("class", "frame-lab").attr("x", X(FR(f))).attr("y", wl + 40).attr("text-anchor", "middle").style("fill", "var(--fire)").text("fr. " + f));
  svg.append("text").attr("class", "frame-lab").attr("x", X(L)).attr("y", wl + 56).attr("text-anchor", "end").text("frames from the FP, 21 in apart (BuShips plans)");
  const m41 = [X(FR(90)), Y(27)];
  svg.append("circle").attr("cx", m41[0]).attr("cy", m41[1]).attr("r", 9).attr("fill", "var(--fire)").attr("stroke", "var(--surface)").attr("stroke-width", 2);
  const call = (x, y, tx, ty, lines, bold) => { svg.append("path").attr("class", "leader").attr("d", `M${x},${y}L${tx},${ty + 4}`); lines.forEach((l, i) => svg.append("text").attr("class", "callout" + (i === 0 && bold ? " b" : "")).attr("x", tx).attr("y", ty - (lines.length - 1 - i) * 15).attr("text-anchor", "middle").text(l)); };
  call(m41[0], m41[1] - 10, m41[0] - 110, 40, ["Mount 41, twin 40 mm (starboard)", EXTRA?.mount41 ?? "\"wrecked\""], true);
  call(X((band[0] + band[1]) / 2) + 40, Y(40), X((band[0] + band[1]) / 2) + 170, 30, ["Frames 65-88: radio transmitter room,", "Main Radio, CIC and plot"], false);
  call(X(FR(78)), Y(15), X(FR(78)) - 20, H - 6, ["Starboard bulwark, frames 70-79, destroyed"], false);
  svg.append("text").attr("class", "callout").attr("x", X(L)).attr("y", 16).attr("text-anchor", "end").text("Bow →");
  d3.select("#frame-note").text(`Profile: Sumner class, drawn to ONI 54-D (${s.plate}). Seen from starboard. Frames are 21 in apart, numbered aft from frame 0 at the forward perpendicular (Sumner booklet of general plans, 1968; DD 692 class general arrangement, 1947). On the 1947 plan's first level, frames 65-88 hold the captain's and executive officer's cabins, CIC (about frames 72-79), the chart and coding rooms, and the forward end of the radio transmitter room (starboard) and Radio Central (port), which run aft beside the forward uptake to about frame 92: the spaces the action report names. Mount 41 is drawn on the starboard platform beside the forward stack (about frames 87-93 on the 1947 plan), where Sumners carried twin 40 mm mounts 41 and 42; Haynsworth's own plan wasn't found, so its frame is the class arrangement, not hers. The ONI drawing is a recognition outline, so its stack and bridge sit a few feet off the plan.`);
}

// ---------- to scale: the Judy at 100 ft ----------
// Frames as in buildProfile: 21 in apart, frame 0 at the FP, AP (frame 210) at x = 4 ft on the silhouette
const FRAME = f => 4 + (210 - f) * 21 / 12;
const HIT_FRAME = 85;   // in the radio transmitter room, beside mount 41 (frames 65-92 on the class plan); assumed within that

function buildScale100() {
  const s = SHIPS.sumner, j = AIRCRAFT.judy, W = 1000, H = 400, left = 70, k = 720 / s.length, wl = 366;
  const svg = d3.select("#scale100").attr("viewBox", `0 0 ${W} ${H}`);
  const X = ft => left + ft * k, Y = ft => wl - ft * k;
  // height ruler and the two recorded heights
  const ru = svg.append("g").attr("class", "ruler");
  for (let f = 0; f <= 175; f += 25) {
    ru.append("line").attr("x1", left - 30).attr("x2", left - 24).attr("y1", Y(f)).attr("y2", Y(f));
    ru.append("text").attr("x", left - 34).attr("y", Y(f) + 3.5).attr("text-anchor", "end").text(f + " ft");
  }
  ru.append("line").attr("x1", left - 27).attr("x2", left - 27).attr("y1", Y(0)).attr("y2", Y(175));
  [[100, "100 ft (Irons)"], [150, "150 ft when fire opened at 1,500 yd (action report)"]].forEach(([f, t]) => {
    svg.append("line").attr("class", "ht-line").attr("x1", left - 24).attr("x2", W - 20).attr("y1", Y(f)).attr("y2", Y(f));
    svg.append("text").attr("class", "callout").attr("x", left - 18).attr("y", Y(f) - 5).text(t);
  });
  svg.append("line").attr("x1", 10).attr("x2", W - 10).attr("y1", wl).attr("y2", wl).attr("stroke", "var(--ink-3)");
  svg.append("text").attr("class", "frame-lab").attr("x", W - 20).attr("y", wl + 16).attr("text-anchor", "end").text("waterline, flat sea assumed");
  svg.append("path").attr("d", s.d).attr("class", "sil").attr("transform", `translate(${left},${wl}) scale(${k})`);
  // masthead
  const mast = [X(232), Y(84)];
  svg.append("path").attr("class", "leader").attr("d", `M${mast[0] + 4},${mast[1]}L${mast[0] + 70},${mast[1] + 8}`);
  svg.append("text").attr("class", "callout").attr("x", mast[0] + 74).attr("y", mast[1] + 12).text("masthead 84 ft (ONI 54-D)");
  // head-on Judy over the hit frame, at 150 ft (outline) and 100 ft (solid)
  const fs = j.span * k / j.front.w, hx = X(FRAME(HIT_FRAME));
  const front = (alt, cls) => svg.append("path").attr("d", j.front.d).attr("class", cls)
    .attr("transform", `translate(${hx - j.front.cx * fs},${Y(alt) - j.front.cy * fs}) scale(${fs})`);
  front(150, "ghost").attr("stroke-width", 1.2 / fs);
  front(100, "sil");
  svg.append("path").attr("class", "leader").attr("d", `M${hx},${Y(100) + 8}L${hx},${Y(30)}`).attr("stroke-dasharray", "2 3");
  svg.append("circle").attr("cx", hx).attr("cy", Y(24)).attr("r", 4).attr("class", "fill-hit");
  svg.append("text").attr("class", "callout b").attr("x", hx - 34).attr("y", Y(100) - 22).attr("text-anchor", "end").text("JUDY 33 head-on, 37′9½″ span");
  svg.append("text").attr("class", "callout").attr("x", hx - 34).attr("y", Y(100) - 8).attr("text-anchor", "end").text("at 100 ft it clears her masthead by 16 ft");
  svg.append("path").attr("class", "leader").attr("d", `M${hx},${Y(22)}L${hx},${wl + 8}`).attr("stroke-dasharray", "2 3");
  svg.append("text").attr("class", "callout").attr("x", hx).attr("y", wl + 22).attr("text-anchor", "middle").text(`hit, frame ~${HIT_FRAME} (starboard side, toward you)`);
  // side view, same scale, ahead of the bow, for length
  const ps = j.length * k / j.profile.w, px = X(s.length) + 50;
  svg.append("path").attr("d", j.profile.d).attr("class", "sil").attr("transform", `translate(${px},${Y(100) - j.profile.h * ps * 0.6}) scale(${ps})`);
  svg.append("text").attr("class", "callout").attr("x", px + j.length * k / 2).attr("y", Y(100) + 22).attr("text-anchor", "middle").text("side view, 33′7″");
  svg.append("text").attr("class", "frame-lab").attr("x", left).attr("y", 16).text("All heights and lengths in feet at one scale. Horizontal placement of the aircraft is for comparison only.");
}

// ---------- to scale: an estimated path ----------
function buildPath() {
  const KT = 1.68781, G = 32.174, VS = 25 * KT, L = SHIPS.sumner.length, BEAM = 41;
  // hit point in ship coordinates (x to starboard, y forward of amidships), ft
  const hitOff = [BEAM / 2, FRAME(HIT_FRAME) - L / 2];
  const ui = { vturn: document.getElementById("p-vturn"), bank: document.getElementById("p-bank"), vfinal: document.getElementById("p-vfinal"), start: document.getElementById("p-start") };
  const svg = d3.select("#pathmap"), W = 1000, H = 640;
  svg.attr("viewBox", `0 0 ${W} ${H}`);

  function solve() {
    const vT = +ui.vturn.value * KT, vF = +ui.vfinal.value * KT, bank = +ui.bank.value * Math.PI / 180;
    const r = vT * vT / (G * Math.tan(bank));
    const rel = +ui.start.value * Math.PI / 180;            // relative bearing of the plane from amidships at t = 0
    const R0 = 4500;                                         // 1,500 yd
    const P0 = [R0 * Math.sin(rel), R0 * Math.cos(rel)];
    const hdg0 = rel;                                        // heading directly away
    // right turn: centre to the right of the heading
    const C = [P0[0] + r * Math.cos(hdg0), P0[1] - r * Math.sin(hdg0)];
    const th0 = Math.atan2(P0[1] - C[1], P0[0] - C[0]);
    let tHit = 30, best = null;
    for (let it = 0; it < 40; it++) {
      const Hp = [hitOff[0], VS * tHit + hitOff[1]];
      let prev = null, found = null;
      for (let dth = 0; dth <= 2 * Math.PI; dth += 0.002) {
        const th = th0 - dth, T = [C[0] + r * Math.cos(th), C[1] + r * Math.sin(th)], d = [Math.sin(th), -Math.cos(th)];
        const w = [Hp[0] - T[0], Hp[1] - T[1]], cr = d[0] * w[1] - d[1] * w[0], dot = d[0] * w[0] + d[1] * w[1];
        if (prev !== null && Math.sign(cr) !== Math.sign(prev) && dot > 0) { found = { dth, T, w }; break; }
        prev = cr;
      }
      if (!found) break;                                      // the hit point is inside the turn: no straight run
      const arc = r * found.dth, straight = Math.hypot(...found.w);
      const t = arc / vT + straight / vF;
      best = { r, C, th0, dth: found.dth, T: found.T, Hp, arc, straight, tArc: arc / vT, t, vT, vF, P0 };
      if (Math.abs(t - tHit) < 0.01) break;
      tHit = t;
    }
    return best;
  }

  function draw() {
    d3.select("#o-vturn").text(ui.vturn.value + " kn");
    d3.select("#o-vfinal").text(ui.vfinal.value + " kn");
    svg.selectAll("*").remove();
    const s = solve();
    if (!s) { svg.append("text").attr("x", 20).attr("y", 30).attr("class", "callout").text("No path: the turn is wider than the room it had. Try a lower speed or more bank."); d3.select("#p-read").html(""); return; }
    // the path, sampled with times
    const pts = [];
    for (let a = 0; a <= s.dth; a += 0.01) { const th = s.th0 - a; pts.push({ p: [s.C[0] + s.r * Math.cos(th), s.C[1] + s.r * Math.sin(th)], t: a * s.r / s.vT }); }
    const n = 40;
    for (let i = 1; i <= n; i++) { const f = i / n; pts.push({ p: [s.T[0] + (s.Hp[0] - s.T[0]) * f, s.T[1] + (s.Hp[1] - s.T[1]) * f], t: s.tArc + f * s.straight / s.vF }); }
    // where it was 1,000 yd from the ship, coming back in (the bomb fell about 1,000 yd abeam)
    let far = 0, bomb = null;
    pts.forEach(q => { const d = Math.hypot(q.p[0], q.p[1] - VS * q.t); if (d > far) far = d; else if (!bomb && d <= 3000) bomb = q; });
    // fit everything to the view, one scale both ways
    const ext = [...pts.map(q => q.p), [0, 0], [0, VS * s.t], [-600, 0]];
    const xs = ext.map(p => p[0]), ys = ext.map(p => p[1]);
    const [x0, x1, y0, y1] = [Math.min(...xs) - 700, Math.max(...xs) + 700, Math.min(...ys) - 600, Math.max(...ys) + 700];
    const k = Math.min(W / (x1 - x0), H / (y1 - y0));
    const ox = (W - (x1 - x0) * k) / 2, oy = (H - (y1 - y0) * k) / 2;
    const P = ([x, y]) => [ox + (x - x0) * k, H - oy - (y - y0) * k];
    // 1,000 ft grid
    for (let gx = Math.ceil(x0 / 1000) * 1000; gx <= x1; gx += 1000) { const a = P([gx, y0]), b = P([gx, y1]); svg.append("line").attr("class", "grid-ft").attr("x1", a[0]).attr("x2", b[0]).attr("y1", a[1]).attr("y2", b[1]); }
    for (let gy = Math.ceil(y0 / 1000) * 1000; gy <= y1; gy += 1000) { const a = P([x0, gy]), b = P([x1, gy]); svg.append("line").attr("class", "grid-ft").attr("x1", a[0]).attr("x2", b[0]).attr("y1", a[1]).attr("y2", b[1]); }
    // 1,500 yd from the ship when fire opened
    const c0 = P([0, 0]);
    svg.append("circle").attr("cx", c0[0]).attr("cy", c0[1]).attr("r", 4500 * k).attr("class", "ring");
    const rl = P([4500 * Math.sin(-2.3), 4500 * Math.cos(-2.3)]);
    svg.append("text").attr("class", "mk-label small").attr("x", Math.min(W - 130, Math.max(8, rl[0]))).attr("y", Math.min(H - 40, Math.max(30, rl[1] - 6))).text("1,500 yd: fire opened");
    // the ship, to scale, when fire opened and at the hit, and her track
    const ship = (y, cls) => { const [x, yy] = P([0, y]); return svg.append("path").attr("d", hullPlan(BEAM / L)).attr("class", cls).attr("transform", `translate(${x},${yy}) scale(${L * k})`).attr("stroke-width", 1.4 / (L * k)); };
    const a0 = P([0, 0]), a1 = P([0, VS * s.t]);
    svg.append("line").attr("x1", a0[0]).attr("x2", a1[0]).attr("y1", a0[1]).attr("y2", a1[1]).attr("class", "stroke-us").attr("stroke-dasharray", "2 3");
    ship(0, "ghost-us"); ship(VS * s.t, "fill-us");
    svg.append("text").attr("class", "mk-label small").attr("x", a0[0] - 12).attr("y", a0[1] + 4).attr("text-anchor", "end").text("Haynsworth when fire opened");
    svg.append("text").attr("class", "mk-label").attr("x", a1[0] - 12).attr("y", a1[1] - 14).attr("text-anchor", "end").text(`at the hit, ${Math.round(VS * s.t).toLocaleString()} ft on`);
    // the plane's path, time ticks every 5 s
    svg.append("path").attr("class", "jpath").attr("d", d3.line()(pts.map(q => P(q.p))));
    for (let t = 5; t < s.t; t += 5) {
      const q = pts.reduce((b, x) => Math.abs(x.t - t) < Math.abs(b.t - t) ? x : b), [x, y] = P(q.p);
      svg.append("circle").attr("cx", x).attr("cy", y).attr("r", 2.6).attr("class", "tick-dot");
      svg.append("text").attr("class", "tick-lab").attr("x", x + 6).attr("y", y - 5).text(t + " s");
    }
    // aircraft, enlarged so they can be seen (true size is the ship's scale)
    const ENL = 4, sp = AIRCRAFT.judy.span * k * ENL;
    const hdgAt = (p, q) => Math.atan2(q[0] - p[0], q[1] - p[1]) * 180 / Math.PI;
    const s0 = P(s.P0); planeAt(svg, "judy", s0, hdgAt(pts[0].p, pts[1].p), sp, "fill-jp");
    svg.append("text").attr("class", "mk-label small").attr("x", s0[0] + 14).attr("y", s0[1] + 4).text("0 s, 150 ft, heading away");
    const last = pts[pts.length - 6], lp = P(last.p); planeAt(svg, "judy", lp, hdgAt(last.p, s.Hp), sp, "fill-jp");
    if (bomb) {
      const [bx, by] = P(bomb.p);
      svg.append("path").attr("d", `M${bx - 7},${by}Q${bx - 3},${by - 10} ${bx},${by - 2}Q${bx + 3},${by - 10} ${bx + 7},${by}`).attr("class", "stroke-jp").attr("fill", "none").attr("stroke-width", 1.4);
      svg.append("text").attr("class", "mk-label small").attr("x", bx + 10).attr("y", by + 14).text("1,000 yd off: about where the bomb fell");
    }
    const hp = P(s.Hp);
    svg.append("circle").attr("cx", hp[0]).attr("cy", hp[1]).attr("r", 5).attr("class", "fill-hit");
    svg.append("text").attr("class", "mk-label").attr("x", hp[0] + 9).attr("y", hp[1] + 18).text(`hit at ${Math.round(s.t)} s, starboard, frame ~${HIT_FRAME}`);
    // scale bar and heading
    const sb0 = [16, H - 18], sbl = 3000 * k;
    svg.append("line").attr("x1", sb0[0]).attr("x2", sb0[0] + sbl).attr("y1", sb0[1]).attr("y2", sb0[1]).attr("stroke", "var(--ink-2)").attr("stroke-width", 2);
    svg.append("text").attr("class", "tick-lab").attr("x", sb0[0]).attr("y", sb0[1] - 6).text("1,000 yd (3,000 ft)");
    svg.append("text").attr("class", "tick-lab").attr("x", W - 16).attr("y", 18).attr("text-anchor", "end").text(`ship's heading 020° is up · grid 1,000 ft · aircraft drawn ×${ENL}`);
    d3.select("#p-read").html(`<span>Turn radius <b>${Math.round(s.r).toLocaleString()} ft</b></span><span>Fire opened to hit <b>${Math.round(s.t)} s</b></span><span>Ship's advance <b>${Math.round(VS * s.t).toLocaleString()} ft</b> (${(VS * s.t / L).toFixed(1)} ship lengths)</span><span>Run in, straight <b>${Math.round(s.straight).toLocaleString()} ft</b></span>`);
  }
  Object.values(ui).forEach(el => el.addEventListener("input", draw));
  draw();
  d3.select("#path-note").text(`Recorded: course 020°, 25 knots (war diary); fire opened at 1,500 yards with the plane at 150 ft heading away; it turned to starboard; the bomb fell about 1,000 yards abeam; it hit the starboard side abaft the bridge banked 45° (action report p. 3); 100 ft and 300+ knots (Irons). Assumed: the plane's bearing from the ship when fire opened; a level turn at constant speed and bank (a real "wing over" climbs and slows at the top, which tightens it); a straight run from the end of the turn to the hit; the hit at frame ${HIT_FRAME}, within the frames the damage report names. The bomb mark is where the path is 1,000 yards from the ship coming back in; the bomb carried forward some distance after release, and the report doesn't say which side it fell on. Altitude isn't modelled here.`);
}

// ---------- order of battle and aircraft plates ----------
function buildOOB() {
  const ships = [
    ["sumner", "Haynsworth (DD-700)", "Picket #1, 060° 12 mi. Hit 1250. With her, in DesDiv 123: English, Charles S. Sperry, Ault (squadron flagship), Waldron (took station #1 after the hit). Pickets #2X and #12: J. W. Weeks, Walker"],
    ["essex", "Essex, Bunker Hill, Hancock", "Fleet carriers. Essex's fighters shot down the Judys at 1140 and 1159; Bunker Hill's Marine Corsairs (VMF-221) lost Lt. Carpenter"],
    ["independence", "Cabot (CVL-28)", "Light carrier. Bombed at 1226 (missed); radar clipped by a suicide Zeke at 1302"],
    ["southdakota", "South Dakota (BB-57)", "1200 fix 26-41-45N 129-25-30E, used here for the formation centre. Took Haynsworth's wounded; five died aboard"],
    ["northcarolina", "North Carolina, Washington", "Battleships. North Carolina hit by a friendly 5-inch shell at 1305; Washington shot down a suicide Zeke at 1302"],
    ["cleveland", "Astoria (CL-90)", "Light cruiser. Her AA report calls the 1226 Judy \"tentatively ... a Zeke\""],
  ];
  const maxL = 885, host = d3.select("#oob");
  ships.forEach(([k, nm, kd]) => {
    const s = SHIPS[k], w = 240, sc = w / maxL, h = 150 * sc + 6;
    const p = host.append("div").attr("class", "plate");
    p.append("svg").attr("viewBox", `0 ${-150 * sc - 2} ${w} ${h}`).attr("role", "img").attr("aria-label", s.name)
      .append("path").attr("d", s.d).attr("class", "sil").attr("transform", `scale(${sc})`);
    p.append("div").attr("class", "nm").text(nm);
    p.append("div").attr("class", "kd").text(s.name + ". " + kd);
  });
  host.append("div").attr("class", "kd").style("grid-column", "1 / -1").text("All drawn to one scale from the ONI recognition plates' printed lengths and heights. The group had more ships than the records read here name; only those named are shown.");
  const ah = d3.select("#airplates");
  [["judy", "Haynsworth's attacker, as her crew identified it. The 210th Air Group flew 9 Model 33s and 2 Model 12s that morning"],
   ["zeke", "About 30 bomb-carrying Zeros went at TF 58 with the Suisei. A Zeke 52 has the same two-row radial engine type and Type 97 guns"],
   ["corsair", "Two Corsairs were on the Judy's tail as it came out of the cloud"],
   ["dinah", "The group's CAP splashed a Dinah at 1056, 29 miles out on 330° (Essex chronology, p. 34). The model isn't recorded; this is the plate's Dinah 43"]].forEach(([k, kd]) => {
    const a = AIRCRAFT[k], sc = a.span / 41;
    const p = ah.append("div").attr("class", "plate");
    const svg = p.append("svg").attr("viewBox", "0 0 230 110").attr("role", "img").attr("aria-label", a.name);
    svg.append("path").attr("d", a.plan.d).attr("class", "sil").attr("transform", `translate(${56 - 50 * sc * 0.9},${4}) scale(${0.9 * sc})`);
    if (a.profile) svg.append("path").attr("d", a.profile.d).attr("class", "sil").attr("transform", `translate(${118},${44}) scale(${0.88 * a.length / 33.6})`);
    p.append("div").attr("class", "nm").text(a.name + " · " + a.type);
    p.append("div").attr("class", "kd").text(`${a.dims} (as printed on the plate). ${kd}. Silhouette: ${a.source}.`);
  });
}

// ---------- evidence board ----------
function buildBoard(claims) {
  const host = d3.select("#board");
  d3.groups(claims, c => c.question).forEach(([q, cs]) => {
    const card = host.append("div").attr("class", "card q");
    card.append("h3").text(q);
    const box = card.append("div").attr("class", "claims");
    cs.forEach(c => {
      const el = box.append("div").attr("class", "claim " + c.weight);
      el.append("span").attr("class", "wt").html(`<i></i>${esc(c.weight)}`);
      el.append("span").attr("class", "what").text(c.claim);
      if (c.note) el.append("span").attr("class", "nt").text(c.note);
      el.append("span").attr("class", "src").html(c.ref ? `<a href="${esc(c.ref)}" target="_blank" rel="noopener">${cite(c.source)}</a>` : cite(c.source));
    });
  });
}

// ---------- both crews ----------
function buildCrews(people) {
  const host = d3.select("#crewlists");
  const us = people.filter(p => p.side === "us"), jp = people.filter(p => p.side === "jp");
  const table = (title, sub, rows, cols) => {
    const c = host.append("div").attr("class", "card crew");
    c.append("h3").text(title); c.append("p").attr("class", "sub").text(sub);
    const t = c.append("table"); t.append("tr").selectAll("th").data(cols.map(d => d[0])).join("th").text(d => d);
    let grp = null;
    rows.forEach(r => {
      if (r.group !== grp) { grp = r.group; t.append("tr").attr("class", "grp").append("td").attr("colspan", cols.length).text(grp); }
      const tr = t.append("tr").classed("him", !!EXTRA?.mark && new RegExp(EXTRA.mark).test(r.name));
      cols.forEach(([, f]) => tr.append("td").html(f(r)));
    });
  };
  const src = r => r.ref ? `<a href="${esc(r.ref)}" target="_blank" rel="noopener">${esc(r.rank || "")}</a>` : esc(r.rank || "");
  table("USS Haynsworth", "Seven killed outright (Report of Casualties, 9 April 1945); five died of wounds aboard South Dakota by 9 April.", us,
    [["Name", r => `<b>${esc(r.name)}</b>${r.note ? `<span class="nt">${esc(r.note)}</span>` : ""}`], ["Rate", src], ["Station", r => esc(r.role)]]);
  table("210th Air Group, Suisei unit, first attack", "Seven crews not returned (crew list, C13120082800 p. 4). Ages and hometowns from compiled rosters, not the form.", jp,
    [["Name", r => `<b>${esc(r.name)}</b>${r.note ? `<span class="nt">${esc(r.note)}</span>` : ""}`], ["Rank", src], ["Plane", r => esc(r.role)], ["From", r => esc(r.from) + (r.born ? `<span class="nt">b. ${esc(r.born)}</span>` : "")]]);
}

function buildSources(timeline, claims) {
  // One line per record, by the first part of its citation; a book's citations ("in Irons, Phalanx") fold into its
  // full reference (Chicago bibliography form, BOOKS)
  const seen = new Map(), books = new Set();
  [...timeline, ...claims].forEach(r => {
    BOOKS.filter(b => b.match.test(r.source)).forEach(b => books.add(b));
    const first = r.source.split(/[;,]/)[0].trim();
    if (first && !BOOKS.some(b => b.match.test(r.source.split(";")[0])) && !seen.has(first))
      seen.set(first, r.ref ? r.ref.replace(/\?objectPage=\d+$/, "") : "");
  });
  const ul = d3.select("#sources");
  const lines = [...[...seen].map(([k, u]) => [k, u ? `<a href="${esc(u)}" target="_blank" rel="noopener">${esc(k)}</a>` : esc(k)]),
                 ...[...books].map(b => [b.html.replace(/<[^>]+>/g, ""), b.url ? `${b.html} <a href="${esc(b.url)}" target="_blank" rel="noopener">About the book</a>` : b.html])];
  lines.sort((a, b) => a[0].localeCompare(b[0])).forEach(([, html]) => ul.append("li").html(html));
  ul.append("li").text("Recognition plates: ONI 54-D, 54-CV, 54-R, 54-C (via coatneyhistory.com); CINCPAC-CINCPOA Bulletin 105-45 (HyperWar; NHHC); FM 30-30 (Internet Archive).");
}
