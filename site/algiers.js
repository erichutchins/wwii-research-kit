// algiers.html: Algiers under the night bombers, May–June 1943, from both sides' records.
// Reads records/engagements/algiers-1943/{timeline,positions,claims}.csv (hand-edited), from RECORDS (config.js).
// The narrative steps are below (STEPS); the entries in each step come from timeline.csv's `step` column. Positions
// given as direction and distance from another (`from`, `brg`, `nm`) are resolved here (dest). Silhouettes come from
// records/silhouettes/ (SILHOUETTES, silhouettes.js). Modelled on haynsworth.js.

const ENG = RECORDS + "engagements/algiers-1943/";
// Rows that cite by key rather than a page: points placed on a modern map
const REF_LINKS = { "hand-placed": "", "OSM Nominatim": "", "princeton-amsalger": "https://maps.princeton.edu/catalog/princeton-bk128c659" };
// Shaded relief and a land mask from today's elevation (tools/build_relief.py; SOURCES.yml aws-terrain-tiles)
const RELIEFS = ["algiers", "algiers-town"].map(n => RECORDS + "relief/" + n + "/");   // coarse first; the finer one is drawn on top
const refUrl = ref => ref in REF_LINKS ? REF_LINKS[ref] : ref;
const isUrl = u => /^https?:/.test(u || "");
const NM = 1852;
// The battery's reach. Its own reports don't name its guns; its sister gun batteries of the 1st Bn, 62nd CA (AA), name
// 90 mm: Battery A at Algiers in the same raids, "went into action w/ 90mm Guns" (12 May 1943) and "fired 453 rds 90mm"
// (13 May; rg64-427180737/p0633), Battery B at Oran "Fired 35 rounds of 90MM" (20 Jan 1943; rg64-427181738/p0557). So
// the 90 mm is drawn, labelled inferred: maximum horizontal range "as limited by fuze or tracer", FM 4-155 (1940)
// table A, printed p. 8 (checked on the page image); FM 4-110 (1942) para 4 gives the same figure (3-inch: 11,100 yd).
const YD = 0.9144;
const GUNS = [["90 mm (inferred)", 12600]];
const RANGE_REF = "https://archive.org/details/FM_4_155_S_A_A_A_R_D_1940";
// great-circle distance in metres
function metres([lon1, lat1], [lon2, lat2]) {
  const r = Math.PI / 180, a = Math.sin((lat2 - lat1) * r / 2) ** 2 + Math.cos(lat1 * r) * Math.cos(lat2 * r) * Math.sin((lon2 - lon1) * r / 2) ** 2;
  return 2 * 6371008.8 * Math.asin(Math.sqrt(a));
}
const fmtDist = m => `≈ ${(m / 1609.344).toFixed(m < 8000 ? 1 : 0)} mi (${(Math.round(m / YD / 100) * 100).toLocaleString("en-US")} yd)`;

// Map views, as [[west, south], [east, north]]
const VIEWS = {
  med: { name: "The western Mediterranean (context only)", b: [[-1.5, 35.2], [15.5, 42.4]] },
  bay: { name: "The Bay of Algiers, about 30 nm across", b: [[2.72, 36.6], [3.42, 37.08]] },
  city: { name: "Algiers, its harbour and Maison Blanche", b: [[2.86, 36.66], [3.31, 36.86]] },
  town: { name: "The city and the battery's ground, about 8 nm across", b: [[2.955, 36.715], [3.115, 36.815]] },
};

// How far a reported point may be off: the battery's note gives "within about a mile"; the others are the records'
// round figures, and the ring is our assumption (said so in the tooltip).
const UNC = {
  "battery-c": [0.87, "within about a mile (the position's note)"],
  "turn-0512": [0.87, "about ±1 mile, assumed: the record's \"about two miles\" is a round figure"],
  "kill-0604": [2.2, "about ±2.5 miles, assumed: the record's \"15 miles\" is a round figure, and \"North\" a rough direction"],
};

// What each step shows. `on`: position ids drawn at full strength (others dim or hidden); `layers`: extra layers.
const STEPS = [
  { id: "ctx", when: "May–June 1943", view: "med", title: "Where the raiders came from",
    body: "The German Naval Staff's war diary reports the raids on Algiers under Luftflotte 2 and by number only: thirty bombers on 12 May, 70 Ju 88s in its 13 May entry, 19 bombers on 4 June. It names no units and no airfields. The Ju 88 Kampfgeschwader of Luftflotte 2 in Sardinia and Italy are candidates, not identified. Sardinia is hatched here as context only: the records read don't say where these raids took off.",
    on: ["algiers"], layers: ["context"] },
  { id: "s0", when: "30 April – May 1943", view: "bay", title: "The defences",
    body: "Battery C, 62nd Coast Artillery (AA), \"arrived position 4 mi west of Algiers\" at 1705 on 30 April, after 270 miles from Châteaudun-du-Rhumel; through May its reports read \"Usual camp duties 4 mi West of Algiers\". The report gives a direction and a distance, not a grid, so the battery's mark is good to about a mile. East of the city, No. 153 Squadron RAF flew Beaufighter night fighters from Maison Blanche, the Algiers airfield, with AI radar, under ground-control stations known by their call-signs (\"Mumsie\", \"Madbrain\", \"Funless\", \"Perform\").",
    on: ["battery-c", "maison-blanche", "algiers", "harbour"], layers: [] },
  { id: "m12", when: "12 May, 1935–2140", view: "town", title: "12 May: one Ju 88 destroyed",
    body: "F/Sgt G.L. Linklater and Sgt L.V. Anthony went up on patrol in Beaufighter V.8632 at 1935. In Algiers Bay they were told of bandits 40 miles to the north at 16,000 ft, then 5 miles away at 12,000. Battery C \"fired on hostile targets 2050 to 2125\". The squadron's summary has the enemy aircraft, \"taking evasive action from A.A.\", turn south about two miles west of Algiers; the Beaufighter closed, gave a two-second burst, and the Ju 88 \"blew up and fell into the sea\". The mark is where it turned, not where it fell. The record names no battery: whose fire it was evading, and whether the two records' times are on one clock, stay open (below). The German war diary has thirty bombers over Algiers that night, hitting the harbour, with no units or losses. The next day's communiqué claimed at least three destroyed by the anti-aircraft guns and the night fighters; L'Écho d'Alger called the D.C.A.'s reaction \"très violente et efficace\".",
    on: ["battery-c", "turn-0512", "harbour", "maison-blanche", "algiers"], layers: ["range"] },
  { id: "m13", when: "13 May, 0820 and 1930–2230", view: "town", title: "13 May: a probable",
    body: "At 0820 Battery C fired for two minutes, in daylight; nothing about it is in the paper. That evening F/Lt S.S. Duff and Sgt R. Perfect patrolled from 1930 to 2230 in Beaufighter EL.162. After a long chase they badly \"mauled\" a Ju 88 but didn't see it fall into the sea, and were awarded a probable; where isn't recorded. The battery fired from 2136 to 2228. The war diary's 13 May entry has 70 Ju 88s attacking Algiers and hits on six steamers: most likely this night, possibly a fuller count of the 12th. L'Écho d'Alger reported a violent barrage, and neither damage nor casualties. The Italian bulletins and German communiqués printed on 14 and 15 May don't mention Algiers.",
    on: ["battery-c", "harbour", "maison-blanche", "algiers"], layers: ["range"] },
  { id: "j4", when: "4 June, 2205–2325", view: "bay", title: "4 June: two missing",
    body: "W/O R.J. Smith and Sgt J.J. Sanderson scrambled from Maison Blanche at 2205 in Beaufighter V.8694. Battery C fired from 2225 to 2235. The squadron's summary: \"At long last the Hun has made an appearance\", the crew's first, a Ju 88 15 miles north of Algiers. The war diary has 19 bombers attacking Algiers that evening, the target covered by a smoke screen, and two planes missing. The next day the Italian bulletin and the German communiqué said the port had been bombed. The Beaufighter's claim accounts for one of the two missing, if it is right; the records read don't say what became of the other.",
    on: ["kill-0604", "battery-c", "maison-blanche", "harbour", "algiers"], layers: ["range"] },
  { id: "after", when: "5–6 June", view: "town", title: "The morning after",
    body: "L'Écho d'Alger of 5 June reported damage and some casualties; Admiral Muselier and the inspector general of civil defence went to the damaged areas. The Allied communiqué, printed the next day, gave a few enemy aircraft, some casualties, damage to civilian property and two bombers destroyed, the number the German war diary has missing. On the Saturday morning Generals Giraud and Catroux visited the bombed quarters, where clearing and rescue went on; Catroux called on Muslim families who had lost their homes. Where in the city the bombs fell isn't in these records, so the map marks only the harbour, the target the German and Italian reports name.",
    on: ["harbour", "algiers"], layers: [] },
];

// Who an entry belongs to, for its bar and its column
const barOf = r => r.side === "axis" ? "var(--axis)" : r.side === "press" ? "var(--ink-3)" : /153 Sqn/.test(r.actor) ? "var(--c3)" : "var(--c1)";
const MONTH = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const dayOf = d => `${+d.slice(8)} ${MONTH[+d.slice(5, 7) - 1]}`;

const tip = document.getElementById("tip");
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

// destination on a sphere: start [lon, lat], bearing (deg true), distance (nm)
function dest([lon, lat], brg, nm) {
  const R = 6371008.8, d = nm * NM / R, b = brg * Math.PI / 180, p1 = lat * Math.PI / 180, l1 = lon * Math.PI / 180;
  const p2 = Math.asin(Math.sin(p1) * Math.cos(d) + Math.cos(p1) * Math.sin(d) * Math.cos(b));
  const l2 = l1 + Math.atan2(Math.sin(b) * Math.sin(d) * Math.cos(p1), Math.cos(d) - Math.sin(p1) * Math.sin(p2));
  return [l2 * 180 / Math.PI, p2 * 180 / Math.PI];
}

Promise.all([
  d3.csv(ENG + "timeline.csv"), d3.csv(ENG + "positions.csv"), d3.csv(ENG + "claims.csv"),
  d3.json("https://cdn.jsdelivr.net/npm/world-atlas@2/land-10m.json"), SILHOUETTES, d3.json(RECORDS + "roads/oss967-primary.geojson").catch(() => null), Promise.all(RELIEFS.map(u => d3.json(u + "relief.json").then(j => ({ ...j, url: u })).catch(() => null))),
]).then(([timeline, positions, claims, world, , roads, reliefs]) => {
  for (const rows of [timeline, positions, claims]) rows.forEach(r => { r.ref = refUrl(r.ref); });
  const P = new Map(positions.map(p => [p.id, p]));
  const resolve = (p, depth = 0) => {
    if (p.ll) return p.ll;
    if (p.lat && p.lon) p.ll = [+p.lon, +p.lat];
    else if (p.from && depth < 5) p.ll = dest(resolve(P.get(p.from), depth + 1), +p.brg || 0, +p.nm || 0);
    return p.ll;
  };
  positions.forEach(p => resolve(p));

  buildSteps(timeline);
  const map = buildMap(world, positions, P, reliefs.filter(Boolean), roads);
  observeSteps(map);
  buildTimeline(timeline);
  buildBoard(claims);
  buildSources(timeline, positions, claims);
});

// ---------- an entry, as entry.css draws it ----------
function entry(host, r, { date = true } = {}) {
  const li = host.append("div").attr("class", "entry").attr("style", `--bar:${barOf(r)}`);
  li.append("div").attr("class", "t" + (r.placed ? " placed" : ""))
    .attr("title", r.placed ? "Time not recorded: placed by the order of the account" : null)
    .html((r.time ? esc(r.time) : "—") + (date ? `<small>${esc(dayOf(r.date))}</small>` : ""));
  const d = li.append("div").attr("class", "body");
  d.append("div").attr("class", "who").html(`<b>${esc(r.actor)}</b>${r.placed === "seq" ? `<span class="what seq">time not recorded</span>` : ""}`);
  // wholly the record's words: its typed face; otherwise our words, quoting it
  const quoted = /^"[^"]+"\.?$/.test(r.text.trim());
  d.append("div").attr("class", quoted ? "said" : "text").text(quoted ? r.text.trim().replace(/^"|"\.?$/g, "") : r.text);
  d.append("div").html(r.ref ? `<a class="src alone" href="${esc(r.ref)}" target="_blank" rel="noopener">${esc(r.source)}</a>` : `<span class="src alone">${esc(r.source)}</span>`);
}

// ---------- narrative ----------
function buildSteps(timeline) {
  const host = d3.select("#steps");
  STEPS.forEach((s, i) => {
    const rows = timeline.filter(r => r.step === s.id);
    const el = host.append("div").attr("class", "step").attr("data-i", i);
    const c = el.append("div").attr("class", "card");
    c.append("div").attr("class", "when").text(s.when);
    c.append("h3").text(s.title);
    c.append("p").text(s.body);
    const ul = c.append("div").attr("class", "entries");
    rows.forEach(r => entry(ul, r));
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
function buildMap(world, positions, P, reliefs, roads) {
  const svg = d3.select("#map");
  const box = svg.node().getBoundingClientRect();
  let W = box.width || 800, H = box.height || 600;
  const defs = svg.append("defs");
  const hatch = (id, cls, gap = 6) => defs.append("pattern").attr("id", id).attr("patternUnits", "userSpaceOnUse").attr("width", gap).attr("height", gap)
    .attr("patternTransform", "rotate(45)").append("line").attr("x1", 0).attr("y1", 0).attr("x2", 0).attr("y2", gap).attr("class", cls).attr("stroke-width", 1.2);
  hatch("hatch-ax", "stroke-ax", 7); hatch("hatch-us", "stroke-us", 6);
  defs.selectAll("pattern line").attr("stroke-opacity", 0.35);

  const med = VIEWS.med.b;
  const outline = { type: "MultiPoint", coordinates: [med[0], med[1]] };
  const proj = d3.geoMercator().fitExtent([[0, 0], [W, H]], outline);
  const path = d3.geoPath(proj);
  // only the land polygons near the western Mediterranean (clipping the world polygon inverts it)
  const near = ring => ring.some(([x, y]) => x > -10 && x < 25 && y > 28 && y < 48);
  const landAll = topojson.feature(world, world.objects.land);
  const polys = (landAll.features || [landAll]).flatMap(f => f.geometry.type === "MultiPolygon" ? f.geometry.coordinates : [f.geometry.coordinates]);
  const land = { type: "MultiPolygon", coordinates: polys.filter(poly => near(poly[0])) };
  // Sardinia, for the context step: the land polygon whose outline lies inside its box
  const inBox = ring => ring.every(([x, y]) => x > 8 && x < 10 && y > 38.8 && y < 41.4);
  const sardinia = { type: "MultiPolygon", coordinates: polys.filter(poly => inBox(poly[0]) && poly[0].length > 50) };

  const gWorld = svg.append("g");
  gWorld.append("path").datum(d3.geoGraticule().step([1, 1]).extent([[-5, 33], [20, 45]])()).attr("class", "grat").attr("d", path);
  gWorld.append("path").datum(land).attr("class", "land").attr("d", path);
  // the relief: inside its box, paint the sea, then the land through the elevation mask (a finer coastline than the
  // world atlas's), then the hillshade. Today's ground: harbour works since 1943 show as land.
  const rdefs = svg.append("defs");
  const placers = reliefs.map((relief, i) => {
    const maskImg = rdefs.append("mask").attr("id", `relief-land-${i}`).attr("maskUnits", "userSpaceOnUse")
      .append("image").attr("href", relief.url + "land.png").attr("preserveAspectRatio", "none");
    const r = gWorld.append("g").attr("class", "relief");
    r.append("rect").attr("class", "relief-sea");
    r.append("rect").attr("class", "relief-land").attr("mask", `url(#relief-land-${i})`);
    r.append("image").attr("href", relief.url + "shade.png").attr("preserveAspectRatio", "none").attr("class", "relief-shade");
    // placed in the projection's own units, so placed again whenever measure() refits the projection
    return () => {
      const [[rw, rs], [re, rn]] = relief.box, a = proj([rw, rn]), b = proj([re, rs]);
      const box = { x: a[0], y: a[1], width: b[0] - a[0], height: b[1] - a[1] };
      for (const el of [maskImg, ...r.selectAll("rect, image").nodes().map(n => d3.select(n))]) el.attr("x", box.x).attr("y", box.y).attr("width", box.width).attr("height", box.height);
    };
  });
  const placeRelief = () => placers.forEach(f => f());
  placeRelief();
  // the primary roads of 1942 (OSS Map 967, traced; about ±4 km): faint, for context
  if (roads) gWorld.append("path").datum(roads).attr("class", "road").attr("d", path);
  const gOver = svg.append("g");
  const gLab = svg.append("g");

  let T = { k: 1, x: 0, y: 0 };
  const xy = ll => { const p = proj(ll); return [T.x + T.k * p[0], T.y + T.k * p[1]]; };
  const nmPx = (ll, nm) => Math.abs(xy(dest(ll, 90, nm))[0] - xy(ll)[0]);
  let syncing = false;
  const setView = t => { T = { k: t.k, x: t.x, y: t.y }; gWorld.attr("transform", `translate(${T.x},${T.y}) scale(${T.k})`); render();
    ruler.update(([x, y]) => proj.invert([(x - T.x) / T.k, (y - T.y) / T.k])); };
  const ruler = scaleBar(svg.node().parentNode, { units: ["km", "mi"] });
  const view = mapZoom(svg.node(), svg.node().parentNode, t => {
    if (syncing) return;
    d3.select(gWorld.node()).interrupt(); clearTimeout(zoomTo.late);
    setView(t);
  }, { min: 0.5, max: 200 });
  view.reset = () => { if (lastView) zoomTo(lastView); };
  const sync = () => { syncing = true; view.set(d3.zoomIdentity.translate(T.x, T.y).scale(T.k)); syncing = false; };

  const items = [];
  const add = (layer, ids, draw) => items.push({ layer, ids: [].concat(ids || []), draw, g: gOver.append("g").attr("class", "mk") });

  // place names: [name, lon, lat, the smallest view (zoom k) they show at, the largest]
  const placeLabels = [
    ["Spain", -0.8, 38.9, 0, 3], ["Balearic Is.", 2.6, 39.95, 0, 3], ["Sardinia", 9.0, 41.65, 0, 3], ["Corsica", 9.05, 42.25, 0, 3],
    ["Sicily", 13.6, 37.95, 0, 3], ["Italy", 15.3, 41.0, 0, 3], ["Algeria", 2.2, 35.6, 0, 3], ["Tunisia", 9.2, 35.5, 0, 3],
    ["Bay of Algiers", 3.13, 36.82, 10, 1e9], ["Cap Matifou", 3.24, 36.83, 10, 1e9], ["Mediterranean", 4.2, 37.6, 0, 3],
  ];

  // context: Sardinia hatched, labelled as context, and a note that the bases aren't recorded
  add("context", [], g => {
    g.selectAll("*").remove();
    if (!sardinia.coordinates.length) return;
    const d = d3.geoPath(d3.geoTransform({ point(x, y) { const p = xy([x, y]); this.stream.point(p[0], p[1]); } }))(sardinia);
    g.append("path").attr("class", "ctx").attr("d", d);
    const [x, y] = xy([8.2, 39.4]);
    ["Luftflotte 2's Ju 88 units in Sardinia and Italy:", "candidates (context, not recorded)"].forEach((t, i) =>
      g.append("text").attr("class", "ctx-label").attr("x", x - 6).attr("y", y + 16 * i).attr("text-anchor", "end").text(t));
    g.on("mousemove", e => showTip(e, `<div class="v">Sardinia (context)</div><div class="m">Candidates for the raiders are the Ju 88 Kampfgeschwader of Luftflotte 2 in Sardinia and Italy (KG 76, KG 54 and others). The war diary gives numbers, not units or bases, so where these raids took off is not recorded.</div><div class="i">German Naval Staff war diary, May–June 1943 · click for the volume</div>`))
      .on("mouseleave", hideTip).on("click", () => openRef("https://archive.org/details/wardiarygermann451943germ"));
  });

  // the battery's reach: the 90 mm gun's maximum horizontal range (inferred), and the distance to each reported aircraft
  add("range", [], g => {
    g.selectAll("*").remove();
    const b = P.get("battery-c"); if (!b?.ll || T.k <= 6) return;
    const [bx, by] = xy(b.ll);
    GUNS.forEach(([gun, yd], i) => {
      const r = nmPx(b.ll, yd * YD / NM);
      g.append("circle").attr("cx", bx).attr("cy", by).attr("r", r).attr("class", "reach");
      g.append("text").attr("class", "mk-label small reach-label").attr("x", bx + r * Math.cos(-Math.PI / 4 - i * 0.12)).attr("y", by + r * Math.sin(-Math.PI / 4 - i * 0.12))
        .attr("dx", 4).text(`${gun}: ${yd.toLocaleString("en-US")} yd`);
    });
    const show = current ? new Set(current.on) : new Set();
    ["turn-0512", "kill-0604"].filter(id => show.has(id)).forEach(id => {
      const q = P.get(id); if (!q?.ll) return;
      const [qx, qy] = xy(q.ll), m = metres(b.ll, q.ll);
      const out = GUNS.every(([, yd]) => m > yd * YD);
      g.append("line").attr("x1", bx).attr("y1", by).attr("x2", qx).attr("y2", qy).attr("class", "dist");
      const short = m < 9000;   // a short line: put the label under the battery's own
      g.append("text").attr("class", "mk-label small").attr("text-anchor", short ? (bx < 260 ? "start" : "middle") : "start")
        .attr("x", short ? (bx < 260 ? Math.max(8, bx - 40) : bx) : (bx + qx) / 2 + 6).attr("y", short ? by + nmPx(b.ll, 0.87) + 34 : (by + qy) / 2)
        .text(`${short ? "to the turn: " : ""}${fmtDist(m)} from the battery${out ? ": beyond a 90 mm gun's range" : ", within a 90 mm gun's range"}`);
    });
    g.selectAll("circle.reach").on("mousemove", e => showTip(e, `<div class="v">Battery C's reach</div><div class="m">A 90 mm gun's maximum horizontal range, "as limited by fuze or tracer": 12,600 yd (FM 4-155, 1940, table A, p. 8; the same in FM 4-110, 1942). <b>Inferred</b>: Battery C's own reports don't name its guns, but Battery A of the same battalion fired 90 mm guns in these raids at Algiers (12–13 May 1943), and Battery B fired 90 mm at Oran in January. A 3-inch gun would reach 11,100 yd. Against aircraft at height the reach along the ground is shorter.</div><div class="i">FM 4-155 · click to open</div>`))
      .on("mouseleave", hideTip).on("click", () => openRef(RANGE_REF));
  });

  // Algiers in the context view: a dot and a name (the city mark's own label shows at the closer views)
  // the points
  positions.forEach(p => add(null, [p.id], g => {
    g.selectAll("*").remove();
    if (!p.ll) return;
    const [x, y] = xy(p.ll);
    const close = T.k > 6;   // the bay and city views
    if (p.id === "algiers") {
      g.append("circle").attr("cx", x).attr("cy", y).attr("r", close ? 5 : 3.5).attr("class", close ? "approx" : "fill-ax");
      g.append("text").attr("class", "mk-label").attr("x", x + 8).attr("y", y + (close ? 18 : 4)).text(close ? "Algiers (centre, approx)" : "Algiers");
    } else if (p.kind === "landmark") {   // 1942 sheet's names, at the city scale only
      if (T.k < 60) return;   // the town view only
      const fix = p.basis === "fix";
      g.append("rect").attr("x", x - 2.5).attr("y", y - 2.5).attr("width", 5).attr("height", 5).attr("class", fix ? "lm fix" : "lm");
      g.append("text").attr("class", "lm-label").attr("x", x + 6).attr("y", y + 4).text(p.label);
    } else if (p.kind === "point") {   // the harbour: the raiders' named target
      if (!close) return;
      g.append("circle").attr("cx", x).attr("cy", y).attr("r", 7).attr("class", "approx").style("stroke", "var(--axis)");
      g.append("path").attr("d", `M${x - 10},${y}H${x - 4}M${x + 4},${y}H${x + 10}M${x},${y - 10}V${y - 4}M${x},${y + 4}V${y + 10}`).attr("class", "stroke-ax").attr("stroke-width", 1.4);
      g.append("text").attr("class", "mk-label ax").attr("x", x + 12).attr("y", y - 8).text("Harbour, the named target (approx)");
    } else if (p.kind === "base") {
      if (!close) return;
      g.append("rect").attr("x", x - 5).attr("y", y - 5).attr("width", 10).attr("height", 10).attr("class", "approx").style("stroke", "var(--c3)");
      planeAt(g, "beaufighter", [x, y - 20], 0, 30, "fill-air");
      g.append("text").attr("class", "mk-label").attr("x", x).attr("y", y + 22).attr("text-anchor", "middle").text("Maison Blanche, 153 Sqn (approx)");
    } else if (p.kind === "battery") {
      if (!close) return;
      const u = UNC[p.id];
      const r = u ? nmPx(p.ll, u[0]) : 0;
      if (u) g.append("circle").attr("cx", x).attr("cy", y).attr("r", r).attr("class", "unc");
      g.append("circle").attr("cx", x).attr("cy", y).attr("r", 5).attr("class", "fill-us").style("stroke", "var(--surface)").style("stroke-width", 1.2);
      g.append("text").attr("class", "mk-label").attr("x", x).attr("y", y + Math.max(r, 6) + 16).attr("text-anchor", "middle").text("Battery C, “4 mi West” (reported, ±)");
    } else if (p.kind === "kill") {
      if (!close) return;
      const u = UNC[p.id];
      const r = u ? nmPx(p.ll, u[0]) : 0;
      if (u) g.append("circle").attr("cx", x).attr("cy", y).attr("r", r).attr("class", "unc ax");
      if (p.id === "turn-0512") {   // where it turned south: not where it fell
        planeAt(g, "ju88", [x, y], 180, 26, "fill-ax");
        const [ax, ay] = [x, y + 16];
        g.append("path").attr("d", `M${ax},${ay}V${ay + 18}M${ax - 4},${ay + 12}L${ax},${ay + 18}L${ax + 4},${ay + 12}`).attr("class", "stroke-ax").attr("stroke-width", 1.5).attr("fill", "none");
        const ty = y - Math.max(r, 14) - 26;
        g.append("text").attr("class", "mk-label small").attr("x", x + 20).attr("y", ty).attr("text-anchor", "end").text("12 May: the Ju 88 turned south here (reported, ±)");
        g.append("text").attr("class", "mk-label small").attr("x", x + 20).attr("y", ty + 15).attr("text-anchor", "end").text("then fell into the sea: where, not recorded");
      } else {
        planeAt(g, "ju88", [x, y], 200, 26, "fill-ax");
        g.append("path").attr("d", `M${x - 8},${y - 8}L${x + 8},${y + 8}M${x - 8},${y + 8}L${x + 8},${y - 8}`).attr("class", "stroke-air").attr("stroke-width", 2.6).attr("fill", "none");
        g.append("text").attr("class", "mk-label small").attr("x", x + Math.max(r, 14) + 6).attr("y", y + 4).text("4 June: Ju 88 destroyed, “15 miles North” (reported, ±)");
      }
    }
    tipFor(g, p);
  }));

  const drawLabels = () => {
    gLab.selectAll("*").remove();
    placeLabels.filter(([, , , lo, hi]) => T.k >= lo && T.k < hi).forEach(([n, lon, lat]) => {
      const [x, y] = xy([lon, lat]); gLab.append("text").attr("class", "place").attr("x", x).attr("y", y).text(n);
    });
  };

  // ---- legend
  const lg = d3.select("#legend");
  const sw = (svgInner, text) => lg.append("span").html(`<svg width="22" height="14" viewBox="0 0 22 14">${svgInner}</svg>${text}`);
  sw(`<circle cx="11" cy="7" r="6" class="unc"/><circle cx="11" cy="7" r="3" class="fill-us"/>`, "Battery C, reported (ring: how far off it may be)");
  sw(`<rect x="6" y="2" width="10" height="10" class="approx" style="stroke:var(--c3)"/>`, "153 Sqn's airfield (placed by hand)");
  sw(`<rect x="8" y="4" width="6" height="6" class="lm"/>`, "Landmark named on the AMS 1942 Alger sheet (today's site)");
  if (roads) sw(`<line x1="1" y1="7" x2="21" y2="7" class="road"/>`, "Primary roads of 1942 (OSS Map 967, traced, ± about 4 km)");
  sw(`<rect x="2" y="2" width="18" height="10" class="relief-land"/><rect x="2" y="2" width="18" height="10" fill="url(#hatch-ax)" opacity=".25"/>`, "Relief and coast: today's elevation (SRTM, USGS)");
  sw(`<circle cx="11" cy="7" r="6" class="reach"/>`, "Battery C's maximum range, 90 mm gun (inferred from its sister batteries; FM 4-155)");
  sw(`<circle cx="11" cy="7" r="6" class="unc ax"/><path d="M5,1L17,13M5,13L17,1" class="stroke-air" stroke-width="2.2" fill="none"/>`, "Ju 88 claimed by a Beaufighter, reported (ring assumed)");
  sw(`<circle cx="11" cy="7" r="5" class="approx" style="stroke:var(--axis)"/>`, "Placed by hand or geocoded (approx)");
  sw(`<rect x="2" y="2" width="18" height="10" class="ctx"/>`, "Context only, not recorded");

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
      const lit = it.ids.some(id => on.has(id)) || (it.layer && layers.has(it.layer));
      // the kill marks belong to their own night
      const own = it.ids.some(id => P.get(id)?.kind === "kill");
      const landmark = it.ids.some(id => P.get(id)?.kind === "landmark");   // background: always on, never dimmed
      it.g.classed("off", !landmark && (!visibleLayer || (own && !lit))).classed("dim", !landmark && visibleLayer && !lit && !own);
    });
  }
  const targetFor = v => {
    const [[w, s], [e, n]] = VIEWS[v].b;
    const a = proj([w, n]), b = proj([e, s]);
    return [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2, Math.max(b[0] - a[0], (b[1] - a[1]) * W / H)];
  };
  function zoomTo(v, animate = true) {
    const target = targetFor(v);
    const from = [(W / 2 - T.x) / T.k, (H / 2 - T.y) / T.k, W / T.k];
    const set = ([cx, cy, w]) => { const k = W / w; setView({ k, x: W / 2 - k * cx, y: H / 2 - k * cy }); sync(); };
    if (!animate || matchMedia("(prefers-reduced-motion: reduce)").matches) { set(target); return; }
    const interp = d3.interpolateZoom(from, target);
    const ms = Math.min(1600, Math.max(500, interp.duration * 0.6));
    d3.select(gWorld.node()).interrupt().transition().duration(ms).ease(d3.easeCubicInOut)
      .tween("zoom", () => t => set(interp(t)));
    clearTimeout(zoomTo.late); zoomTo.late = setTimeout(() => { d3.select(gWorld.node()).interrupt(); set(targetFor(v)); }, ms + 250);
  }
  let lastView = null;
  function show(step) {
    measure();
    current = step;
    d3.select("#clock").html(`${esc(step.when)}<small>times as written</small>`);
    d3.select("#viewname").text(VIEWS[step.view].name);
    if (step.view !== lastView) { const first = lastView === null; lastView = step.view; zoomTo(step.view, !first); }
    render();
  }
  function measure() {
    const b = svg.node().getBoundingClientRect();
    if (!b.width || !b.height || (Math.abs(b.width - W) < 2 && Math.abs(b.height - H) < 2)) return false;
    W = b.width; H = b.height; proj.fitExtent([[0, 0], [W, H]], outline);
    gWorld.selectAll("path").attr("d", path);
    placeRelief();
    d3.select(gWorld.node()).interrupt(); clearTimeout(zoomTo.late);
    T = { k: 1, x: 0, y: 0 }; sync();
    if (lastView) zoomTo(lastView, false);
    return true;
  }
  new ResizeObserver(() => measure()).observe(svg.node());
  const api = { show, zoomTo, xy, state: () => ({ T, W, H, lastView }) };
  window._amap = api;
  return api;
}

// an aircraft plan view centred at [x, y], nose toward `hdg`, `size` px span (shapes from SILHOUETTES)
function planeAt(g, type, [x, y], hdg, size, cls) {
  const a = AIRCRAFT[type].plan, s = size / a.w;
  return g.append("path").attr("d", a.d).attr("class", cls)
    .attr("transform", `translate(${x},${y}) rotate(${hdg}) scale(${s}) translate(${-a.w / 2},${-a.h / 2})`);
}
function tipFor(g, p) {
  const u = UNC[p.id];
  const prec = p.basis === "reported" ? `reported, ± ${u ? u[1] : "not stated"}` : p.basis === "approx" ? "approx: placed by hand or geocoded, not from the record" : p.basis;
  const how = p.from ? `${p.brg}°, ${p.nm} nm from ${P_LABEL(p.from)} (as the record gives it: direction and distance)` : "";
  g.attr("tabindex", 0).attr("role", "link").attr("aria-label", p.label)
    .on("mousemove", e => showTip(e, `<div class="v">${esc(p.label)}</div><div class="k">${esc(prec)}</div>${how ? `<div class="m">${esc(how)}</div>` : ""}${p.note ? `<div class="m">${esc(p.note)}</div>` : ""}<div class="i">${esc(p.source)}${isUrl(p.ref) ? " · click for the page" : ""}</div>`))
    .on("mouseleave", hideTip).on("click", () => openRef(p.ref)).on("keydown", e => { if (e.key === "Enter") openRef(p.ref); });
}
const P_LABEL = id => id === "algiers" ? "the city's centre" : id;
function showTip(e, html) { tip.innerHTML = html; tip.hidden = false; const w = tip.offsetWidth, h = tip.offsetHeight; tip.style.left = Math.min(innerWidth - w - 8, e.clientX + 14) + "px"; tip.style.top = Math.min(innerHeight - h - 8, e.clientY + 14) + "px"; }
function hideTip() { tip.hidden = true; }
function openRef(u) { if (isUrl(u)) window.open(u, "_blank", "noopener"); }

// ---------- the nights side by side ----------
function buildTimeline(timeline) {
  const host = d3.select("#timeline");
  const cols = [["allied", "The defenders"], ["axis", "The attackers"], ["press", "The newspaper"]];
  host.append("div").attr("class", "tl-head").html(`<span>Dated</span>${cols.map(([, n]) => `<span>${n}</span>`).join("")}`);
  d3.groups(timeline, r => r.date).forEach(([date, rows]) => {
    const row = host.append("div").attr("class", "tl-row");
    row.append("div").attr("class", "day").text(dayOf(date) + " 1943");
    cols.forEach(([side, name]) => {
      const col = row.append("div").attr("class", "col").attr("data-side", name);
      rows.filter(r => r.side === side).forEach(r => entry(col, r, { date: false }));
    });
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
      el.append("span").attr("class", "src").html(isUrl(c.ref) ? `<a href="${esc(c.ref)}" target="_blank" rel="noopener">${esc(c.source)}</a>` : esc(c.source));
    });
  });
}

// ---------- sources: one line per page cited, with every citation of it ----------
function buildSources(timeline, positions, claims) {
  const byRef = new Map();
  // the entries' own citations first; a position or claim adds a line only for a page no entry cites
  [...timeline, ...claims, ...positions].forEach(r => {
    const key = isUrl(r.ref) ? r.ref : "~" + r.source;
    if (!byRef.has(key)) byRef.set(key, r.source);
  });
  const lines = [...byRef].map(([k, text]) => {
    return [text, k.startsWith("~") ? esc(text) : `<a href="${esc(k)}" target="_blank" rel="noopener">${esc(text)}</a>`];
  });
  const ul = d3.select("#sources");
  lines.sort((a, b) => a[0].localeCompare(b[0])).forEach(([, html]) => ul.append("li").html(html));
  const sil = ["ju88", "beaufighter"].map(k => AIRCRAFT[k]).filter(Boolean);
  ul.append("li").text("Silhouettes: " + sil.map(a => `${a.name.replace(/^JU/, "Ju").replace(/^BEAUFIGHTER$/, "Beaufighter")}, ${a.source}`).join("; ") + ".");
  d3.select("#sil-note").text("Map silhouettes are drawn to show the type, not to scale or at a recorded heading: the Ju 88 at 12 May points south because the record says it turned south; the others' headings are not recorded.");
}
