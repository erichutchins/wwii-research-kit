// Army units' stations, 1940–1945: where each battery, company, detachment and division was,
// from its own records. Renders records/army/army.json, which tools/build_army.py builds from
// the hand-transcribed CSVs in records/army/ (each station as typed, placed at its town, offset
// or grid reference, with its page).

let RULER = null;   // scalebar.js
const DAY = 864e5;
const DAYS_PER_SECOND = 8;     // playback speed
const HIT_PX = 14;             // hover radius around a station (24px+ target)
const ACT_DX = 13;             // on-screen offset between actions drawn at the same point
const ONLINE_UNTIL = Date.parse("1945-01-01T00:00Z");   // NARA has digitized morning reports through Dec 1944
const MUSEUM = "https://cdm17494.contentdm.oclc.org/digital/collection/ok45th/id/";  // 45th Infantry Division Museum
const AAR_BOOK = "https://books.google.com/books?id=ee9mAAAAMAAJ";                  // Third Army's report, Vol. II
// Sources only linked, never shown (records/SOURCES.yml)
const LINKED = {
  gi9ad: ["https://www.lonesentry.com/gi_stories_booklets/9tharmored/", "“The 9th: The Story of the 9th Armored Division” (G.I. Stories booklet, 1945), at Lone Sentry"],
  wiki9ad: ["https://en.wikipedia.org/wiki/9th_Armored_Division_(United_States)", "Wikipedia: 9th Armored Division (United States)"],
};
// stations.csv `source`s that give a headquarters' or a division's position rather than the unit's own:
// drawn hollow, with dashed legs, and called assumed
const ASSUMED = {
  bn: "The battalion command post, from the battalion's journal or history; the battery assumed nearby",
  regt: "The Regimental Headquarters Battery's morning report: the detachment's own reports for these months are missing, so it is assumed with regimental headquarters",
  hist: "Battalion headquarters' position in the 894th's printed history (1945); the detachment assumed with it",
  aar: "The battalion's symbol on Third Army's antiaircraft situation maps, or its move in the report's text; the headquarters battery assumed with it",
  div: "The division's position (sometimes one combat command's), from division-level sources; drawn as assumed",
};

const LABELS = [
  { name: "ITALY", lon: 13.6, lat: 42.6 }, { name: "FRANCE", lon: 3.2, lat: 46.6 },
  { name: "GERMANY", lon: 10.2, lat: 50.6 }, { name: "SWITZERLAND", lon: 8.1, lat: 46.75 },
  { name: "TYRRHENIAN SEA", lon: 12.0, lat: 40.0 }, { name: "LIGURIAN SEA", lon: 8.6, lat: 43.6 },
  { name: "MEDITERRANEAN SEA", lon: 5.5, lat: 39.5 }, { name: "CORSICA", lon: 9.05, lat: 42.15 },
  { name: "SICILY", lon: 14.1, lat: 37.55 }, { name: "SARDINIA", lon: 9.0, lat: 40.05 },
  { name: "ALGERIA", lon: 2.6, lat: 35.2 }, { name: "TUNISIA", lon: 9.4, lat: 34.6 },
  { name: "AUSTRIA", lon: 14.2, lat: 47.5 }, { name: "BELGIUM", lon: 4.6, lat: 50.6 },
  { name: "SPAIN", lon: -3.7, lat: 40.2 }, { name: "ENGLAND", lon: -1.6, lat: 52.6 },
  { name: "CZECHOSLOVAKIA", lon: 15.2, lat: 49.8 }, { name: "ENGLISH CHANNEL", lon: -2.6, lat: 50.1 },
  { name: "ADRIATIC SEA", lon: 16.0, lat: 42.9 }, { name: "ATLANTIC OCEAN", lon: -14, lat: 46 },
  { name: "UNITED STATES", lon: -92, lat: 38 },
];
// Cities along the routes. Tier 1 always shows; tiers 2 and 3 appear as the map zooms in (by
// pixels per degree), and any label that would overlap one already placed is hidden: tier 1
// first, then the country and sea names, then the rest, west to east within each.
const CITIES = [
  ...[["Rome", 12.4964, 41.9028], ["Naples", 14.2681, 40.8518], ["Marseille", 5.3698, 43.2965],
      ["Lyon", 4.8357, 45.764], ["Strasbourg", 7.7521, 48.5734], ["Palermo", 13.3615, 38.1157],
      ["Paris", 2.3522, 48.8566], ["London", -0.1276, 51.5072], ["Glasgow", -4.2518, 55.8642],
      ["Algiers", 3.0588, 36.7538], ["Oran", -0.6337, 35.6971], ["Tunis", 10.1815, 36.8065],
      ["Munich", 11.582, 48.1351], ["Nuremberg", 11.0767, 49.4521], ["Frankfurt", 8.6821, 50.1109],
      ["Leipzig", 12.3731, 51.3397], ["New York", -74.006, 40.7128], ["Washington", -77.0369, 38.9072]]
    .map(c => [...c, 1]),
  ...[["Grenoble", 5.7245, 45.1885], ["Épinal", 6.4503, 48.1724], ["Nancy", 6.1844, 48.6921],
      ["Besançon", 6.0241, 47.238], ["Dijon", 5.0415, 47.322], ["Toulon", 5.928, 43.1242],
      ["Saarbrücken", 6.9969, 49.2402], ["Mannheim", 8.4660, 49.4875], ["Würzburg", 9.9534, 49.7913],
      ["Augsburg", 10.8978, 48.3705], ["Stuttgart", 9.1829, 48.7758], ["Salerno", 14.7681, 40.6824],
      ["Anzio", 12.6278, 41.4476], ["Bizerte", 9.8739, 37.2744], ["Metz", 6.1757, 49.1193],
      ["Karlsruhe", 8.4037, 49.0069], ["Southampton", -1.4044, 50.9097], ["Cherbourg", -1.6250, 49.6425],
      ["Plymouth", -4.1427, 50.3755], ["Birmingham", -1.8904, 52.4862], ["Rennes", -1.6778, 48.1173],
      ["Le Mans", 0.1996, 48.0061], ["Troyes", 4.0744, 48.2973], ["Koblenz", 7.5886, 50.3569],
      ["Liège", 5.5797, 50.6326], ["Luxembourg", 6.1296, 49.6116], ["Constantine", 6.6147, 36.365],
      ["Siena", 11.3308, 43.3188], ["Norfolk", -76.2859, 36.8508], ["Philadelphia", -75.1652, 39.9526],
      ["Nashville", -86.7816, 36.1627], ["El Paso", -106.485, 31.7619]].map(c => [...c, 2]),
  ...[["Sainte-Maxime", 6.6358, 43.3091], ["Avignon", 4.8055, 43.9493], ["Rambervillers", 6.6359, 48.3453],
      ["Lunéville", 6.4964, 48.5894], ["Saverne", 7.3622, 48.7416], ["Haguenau", 7.7905, 48.8156],
      ["Sarreguemines", 7.0709, 49.1095], ["Worms", 8.3611, 49.6341], ["Darmstadt", 8.6512, 49.8728],
      ["Aschaffenburg", 9.1355, 49.9807], ["Fulda", 9.6753, 50.5558], ["Ingolstadt", 11.4251, 48.7665],
      ["Caserta", 14.3329, 41.0723], ["Cassino", 13.8306, 41.4898], ["Gela", 14.2509, 37.0663],
      ["Sétif", 5.4137, 36.1898], ["Tébessa", 8.1242, 35.4042], ["Toul", 5.8913, 48.6753],
      ["Remagen", 7.2306, 50.5748], ["Thionville", 6.1683, 49.3579], ["Grafenwöhr", 11.9067, 49.7174],
      ["Plattling", 12.8735, 48.7775], ["Karlovy Vary", 12.8716, 50.2319], ["Civitavecchia", 11.7969, 42.0924],
      ["La Haye-du-Puits", -1.5434, 49.2895], ["Valognes", -1.4706, 49.5088], ["Weymouth", -2.4547, 50.6144],
      ["Étampes", 2.1606, 48.4344]].map(c => [...c, 3]),
].map(([name, lon, lat, tier]) => ({ name, lon, lat, tier }));
const TIER_PX_PER_DEG = { 0: 0, 1: 0, 2: 35, 3: 80 };   // zoom needed before a tier shows

const state = { unit: null, t: null, playing: false, k: 1, acts: true };
let DATA, LAND, BORDERS, ROADS, proj, path, zoom, hitPoints = [];

const svg = d3.select("#map");
const tip = document.getElementById("tip");
const fmtDay = d3.utcFormat("%-d %b %Y");
const fmtMonth = d3.utcFormat("%b %Y");
const parseDay = s => Date.parse(`${s}T12:00Z`);

// ── Data ────────────────────────────────────────────────────────────────────
Promise.all([
  d3.json(RECORDS + "army/army.json"),
  d3.json("https://cdn.jsdelivr.net/npm/world-atlas@2/countries-50m.json"),
  d3.json(RECORDS + "roads/oss967-primary.geojson").catch(() => null),   // the primary roads of 1942 (OSS Map 967): faint context
]).then(([data, world, roads]) => {
  ROADS = roads;
  LAND = topojson.feature(world, world.objects.land);
  BORDERS = topojson.mesh(world, world.objects.countries, (a, b) => a !== b);
  DATA = prepare(data);
  buildControls();
  new ResizeObserver(() => render()).observe(document.querySelector(".map-wrap"));
  // deep link: army.html?unit=106aaa-d&t=1944-08-15
  const q = new URLSearchParams(location.search);
  select(DATA.units.some(u => u.unit === q.get("unit")) ? q.get("unit") : DATA.units.find(u => u.overseas).unit, { keepUrl: true });
  if (q.get("t")) setTime(parseDay(q.get("t")));
});

function prepare(data) {
  const units = data.units.map(u => {
    const rows = u.stations.map(r => ({
      ...r, unit: u.unit, unitName: u.name, t: parseDay(r.date), plotted: r.lat !== null,
      lonlat: r.lat === null ? null : [r.lon, r.lat], bn: r.source in ASSUMED, presumed: ASSUMED[r.source],
    }));
    // Keyframes for the moving marker: a unit holds its station until the day before the next
    // one (reports are "ending 2400"), then moves. A stretch with no position (at sea, en route)
    // is crossed in a straight line, or along the waypoints in routes.csv, drawn dashed and
    // called assumed.
    const keys = [], legs = [];
    const pts = rows.filter(r => r.plotted);
    pts.forEach((a, i) => {
      keys.push({ t: a.t, at: a.lonlat });
      const b = pts[i + 1];
      if (!b) return;
      const gap = rows.filter(r => !r.plotted && r.t > a.t && r.t < b.t);
      const leave = gap.length ? gap[0].t : Math.max(a.t, b.t - DAY);
      keys.push({ t: leave, at: a.lonlat });
      const route = data.routes.find(rt => rt.unit === u.unit && rt.from === a.date && rt.to === b.date);
      const coords = [a.lonlat, ...(route ? route.points : []), b.lonlat];
      // time along the leg in proportion to distance, so the marker keeps a steady pace
      const cum = [0];
      for (let j = 1; j < coords.length; j++) cum.push(cum[j - 1] + d3.geoDistance(coords[j - 1], coords[j]));
      const times = cum.map(c => leave + (b.t - leave) * (c / (cum.at(-1) || 1)));
      for (let j = 1; j < coords.length - 1; j++) keys.push({ t: times[j], at: coords[j] });
      if (route) b.routeNote = route.note;
      // also dashed when the arriving row says the route is assumed (a crossing the reports don't
      // date) and when either end is a headquarters' or division's position rather than the unit's
      legs.push({ from: a, to: b, coords, times, gap,
                  assumed: gap.length > 0 || !!route || /route assumed/i.test(b.note) || a.bn || b.bn });
    });
    const km = d3.sum(legs, l => d3.sum(l.coords.slice(1), (c, j) => d3.geoDistance(l.coords[j], c)) * 6371);
    // engagements and casualties from the battalion's histories (actions.csv)
    const acts = u.actions.map(a => ({ ...a, act: true, unit: u.unit, unitName: u.name, t: parseDay(a.date),
                                      lonlat: [a.lon, a.lat], station: actionTitle(a) }));
    // overseas: any station east of 30°W (the 113th Infantry's units never left the United States)
    const overseas = pts.some(r => r.lon > -30);
    return { ...u, short: u.short || u.unit, rows, pts, keys, legs, km, acts, overseas,
             t0: rows[0].t, t1: rows.at(-1).t };
  });
  return { units };
}

// "Engaged aircraft: aircraft destroyed · Battery D" — a short label for an action
const RESULT = { destroyed: "aircraft destroyed", probable: "aircraft probably destroyed", hits: "hits observed",
                 none: "no result", unknown: "result unknown", friendly: "fired on a plane later identified as friendly",
                 captured: "prisoners taken", neutralized: "target neutralized", wounded: "a man wounded",
                 killed: "a man died of wounds", injured: "a man injured" };
const KIND = { air: "Engaged aircraft", ground: "Ground fire", casualty: "Casualty", event: "" };
function actionTitle(a) {
  if (a.kind === "event") return "Landed in southern France";
  const who = /^(all|battalion)/.test(a.who) ? `Battalion (${a.who})`
    : /^[A-D](, [A-D])+$/.test(a.who) ? `Batteries ${a.who}`
    : `Battery ${a.who.replace(/Plt$/, "Platoon").replace(/det$/, "detachment")}`;
  return `${KIND[a.kind]}: ${RESULT[a.result] ?? a.result} · ${who}`;
}

const chosen = () => DATA.units.find(u => u.unit === state.unit);
const actsOf = u => (state.acts ? u.acts : []);
const span = () => [chosen().t0 - 2 * DAY, chosen().t1 + 2 * DAY];

// ── Controls ────────────────────────────────────────────────────────────────
function buildControls() {
  const pick = document.getElementById("unit-pick");
  [["Overseas", true], ["In the United States only", false]].forEach(([label, overseas]) => {
    const grp = el("optgroup"); grp.label = label;
    DATA.units.filter(u => u.overseas === overseas).forEach(u =>
      grp.append(Object.assign(el("option", null, `${u.name} (${new Date(u.t0).getUTCFullYear()}–${new Date(u.t1).getUTCFullYear()})`), { value: u.unit })));
    if (grp.children.length) pick.append(grp);
  });
  pick.addEventListener("change", () => select(pick.value));
  const box = document.getElementById("acts-toggle");
  box.addEventListener("change", () => { state.acts = box.checked; select(state.unit); });
  document.getElementById("play").addEventListener("click", togglePlay);
  document.getElementById("scrub").addEventListener("input", e => {
    stop();
    const [t0, t1] = span();
    setTime(t0 + (t1 - t0) * (+e.target.value / 1000));
  });
  document.getElementById("zin").addEventListener("click", () => svg.transition().call(zoom.scaleBy, 1.8));
  document.getElementById("zout").addEventListener("click", () => svg.transition().call(zoom.scaleBy, 1 / 1.8));
  document.getElementById("zreset").addEventListener("click", () => svg.transition().call(zoom.transform, d3.zoomIdentity));
  document.getElementById("scan-close").addEventListener("click", () => document.getElementById("scan").close());
  document.getElementById("scan-img").addEventListener("click", e => e.target.classList.toggle("full"));
}

function select(unit, { keepUrl = false } = {}) {
  stop();
  state.unit = unit;
  document.getElementById("unit-pick").value = unit;
  const n = chosen().acts.length;
  document.getElementById("acts-check").hidden = n === 0;
  document.getElementById("acts-count").textContent = `(${n})`;
  state.t = span()[1];   // open at the end, every track drawn
  if (!keepUrl) history.replaceState(null, "", `?unit=${unit}`);
  renderStats();
  renderLegend();
  renderSide();
  render();
}

// ── Map ─────────────────────────────────────────────────────────────────────
function render() {
  if (!DATA) return;
  const box = document.querySelector(".map-wrap").getBoundingClientRect();
  const W = Math.max(300, box.width), H = Math.max(300, box.height);
  svg.attr("viewBox", `0 0 ${W} ${H}`);
  svg.selectAll("*").remove();

  const u = chosen();
  // fit to the unit's stations; the opening view is the theatre, and stations in the United States
  // (west of 30°W) are a zoom-out away, unless the unit never left
  const all = u.legs.length ? u.legs.flatMap(l => l.coords) : u.pts.map(r => r.lonlat);
  let coords = all.filter(c => c[0] > -30);
  if (coords.length < 2) coords = all;
  const [lo0, lo1] = d3.extent(coords, c => c[0]), [la0, la1] = d3.extent(coords, c => c[1]);
  const pad = Math.max(1, (la1 - la0) / 6);
  proj = d3.geoConicConformal().parallels([la0 + pad, la1 - pad > la0 + pad ? la1 - pad : la0 + pad + 2])
    .rotate([-(lo0 + lo1) / 2, 0])
    .fitExtent([[40, 30], [W - 40, H - 30]], { type: "MultiPoint", coordinates: coords });
  path = d3.geoPath(proj);
  document.getElementById("hint").textContent = "Scroll or pinch to zoom · drag to pan · borders are today's"
    + (u.overseas && u.pts.some(r => r.lon < -30) ? " · zoom out for the United States" : "");

  const g = svg.append("g").attr("class", "zoomable");
  g.append("path").datum(d3.geoGraticule().step([2, 2])()).attr("class", "graticule").attr("d", path);
  g.append("path").datum(LAND).attr("class", "land").attr("d", path);
  g.append("path").datum(BORDERS).attr("class", "border").attr("d", path);
  if (ROADS) g.append("path").datum(ROADS).attr("class", "road").attr("d", path)
    .append("title").text("Primary roads, 1942, as OSS Map 967 drew them (traced; ± about 4 km)");

  const labels = g.append("g");
  // country and sea names: placed before the cities, centred, and hidden on overlap too
  const areaNodes = LABELS.map(p => {
    const node = labels.append("text").attr("class", "place").attr("text-anchor", "middle")
      .datum(proj([p.lon, p.lat])).text(p.name).node();
    const w = p.name.length * 7.6;
    return { c: { tier: 0, lon: p.lon }, node, w, x0: -w / 2 };
  });
  cityNodes = CITIES.map(c => {
    const cg = labels.append("g").attr("class", "city").datum(proj([c.lon, c.lat]));
    cg.append("circle").attr("class", "city-dot").attr("r", 3);
    cg.append("text").attr("class", "city-label").attr("x", 6).attr("y", 4).text(c.name);
    return { c, node: cg.node(), w: 6 + c.name.length * 6.2, x0: -4 };
  }).concat(areaNodes);

  const tg = g.append("g");
  u.legs.forEach(l => tg.append("path").datum({ type: "LineString", coordinates: l.coords })
    .attr("class", `track ahead${l.assumed ? " assumed" : ""}`).attr("d", path));
  u.pastPath = tg.append("path").attr("class", "track past");
  u.pastAssumed = tg.append("path").attr("class", "track past assumed");

  const mg = g.append("g");
  hitPoints = [];
  u.pts.forEach(d => {
    const [x, y] = proj(d.lonlat);
    d.x = x; d.y = y;
    const mk = mg.append("g").attr("class", `mk${d.bn ? " bn" : ""}`).datum([x, y]);
    mk.append("circle").attr("class", "ring").attr("r", 4.5);
    mk.append("circle").attr("class", "shape").attr("r", 4.5);
    d.node = mk.node();
    hitPoints.push(d);
  });
  // action diamonds sit above the stations; same hover/click as stations. Several actions at
  // one point (or one on a station) are fanned out sideways by ACT_DX px.
  const taken = new Map(hitPoints.map(h => [`${h.x},${h.y}`, 1]));
  actsOf(u).forEach(d => {
    const [x, y] = proj(d.lonlat);
    d.x = x; d.y = y;
    const key = `${x},${y}`, n = taken.get(key) ?? 0;
    taken.set(key, n + 1);
    d.dx = n * ACT_DX;
    const mk = mg.append("g").attr("class", `act ${d.kind}`).datum([x, y]);
    const inner = mk.append("g").attr("transform", `translate(${d.dx},0)`);
    inner.append("path").attr("class", "ring").attr("d", "M0,-7L7,0L0,7L-7,0Z");
    inner.append("path").attr("class", "shape").attr("d", "M0,-6L6,0L0,6L-6,0Z");
    d.node = mk.node();
    hitPoints.push(d);
  });
  const w = g.append("g").attr("class", "who").datum([0, 0]).style("display", "none");
  w.append("circle").attr("class", "halo").attr("r", 14);
  w.append("circle").attr("class", "core").attr("r", 6);
  w.append("text").attr("x", 11).attr("y", -9).text(u.short);
  u.marker = w;

  zoom = d3.zoom().scaleExtent([0.25, 60]).translateExtent([[-4 * W, -2 * H], [3 * W, 3 * H]])
    .on("zoom", ev => {
    (RULER = RULER || scaleBar(svg.node().parentNode, { units: ["km", "mi"] })).update(p => proj.invert(ev.transform.invert(p)));   // the distance ruler
    g.attr("transform", ev.transform); state.k = ev.transform.k; rescale();
  });
  svg.call(zoom).on("dblclick.zoom", null);
  svg.call(zoom.transform, d3.zoomIdentity);
  svg.on("pointermove", onHover).on("pointerleave", () => setHover(null))
     .on("click", () => { if (state.hover) openScan(state.hover); });
  rescale();
  drawStrip();
  setTime(state.t);
}

// Keep markers and labels the same on-screen size at any zoom.
function rescale() {
  const k = state.k;
  svg.selectAll(".place, .zoomable > g > g, .mk, .act, .who")
    .filter(function () { return Array.isArray(d3.select(this).datum()); })
    .attr("transform", d => `translate(${d[0]},${d[1]}) scale(${1 / k})`);
  placeCities();
}

// Show the city labels the zoom allows, skipping any that would overlap one already shown
let cityNodes = [];
function placeCities() {
  if (!proj) return;
  const pxPerDeg = proj.scale() * state.k * Math.PI / 180;
  const rank = { 1: 0, 0: 1, 2: 2, 3: 3 };   // main cities, then country/sea names, then smaller towns
  const order = [...cityNodes].sort((a, b) => rank[a.c.tier] - rank[b.c.tier] || a.c.lon - b.c.lon);
  const boxes = [];
  order.forEach(n => {
    const [x, y] = d3.select(n.node).datum().map(v => v * state.k);
    const box = [x + n.x0, y - 8, x + n.x0 + n.w, y + 8];
    const show = pxPerDeg >= TIER_PX_PER_DEG[n.c.tier]
      && !boxes.some(b => box[0] < b[2] && box[2] > b[0] && box[1] < b[3] && box[3] > b[1]);
    if (show) boxes.push(box);
    n.node.style.display = show ? null : "none";
  });
}

function onHover(ev) {
  if (!hitPoints.length) return;
  const t = d3.zoomTransform(svg.node());
  const [mx, my] = t.invert(d3.pointer(ev, svg.node()));
  // nearest on screen, counting the sideways fan-out of actions drawn at one point
  const screen = h => Math.hypot((h.x - mx) * t.k + (h.dx ?? 0), (h.y - my) * t.k);
  const d = d3.least(hitPoints, screen);
  if (d && screen(d) <= HIT_PX) { setHover(d); showTip(ev, d.act ? actionTip(d) : pointTip(d)); }
  else setHover(null);
}

function setHover(d) {
  if (state.hover === d) return;
  if (state.hover) state.hover.node.classList.remove("hover");
  state.hover = d;
  svg.style("cursor", d ? "pointer" : null);
  if (d) d.node.classList.add("hover"); else hideTip();
}

// ── Time ────────────────────────────────────────────────────────────────────
function positionAt(u, t) {
  const k = u.keys;
  if (!k.length || t < k[0].t) return null;
  if (t >= k.at(-1).t) return k.at(-1).at;
  const i = d3.bisectRight(k.map(x => x.t), t) - 1;
  const a = k[i], b = k[i + 1];
  if (a.at === b.at) return a.at;
  return d3.geoInterpolate(a.at, b.at)((t - a.t) / (b.t - a.t || 1));
}

// The station a unit reported on day t (the last row on or before it)
const rowAt = (u, t) => u.rows.filter(r => r.t <= t).at(-1) ?? null;

function setTime(t, { fromList = false } = {}) {
  const [t0, t1] = span();
  state.t = Math.max(t0, Math.min(t1, t));
  document.getElementById("scrub").value = Math.round(1000 * (state.t - t0) / (t1 - t0));
  document.getElementById("now-date").replaceChildren(el("b", null, fmtDay(new Date(state.t))));
  const u = chosen();
  // the marker shows from the unit's first station to its last (the records stop there)
  const pos = state.t <= u.t1 + DAY ? positionAt(u, state.t) : null;
  if (u.marker) {
    u.marker.style("display", pos ? null : "none");
    if (pos) u.marker.datum(proj(pos));
  }
  // track covered so far: solid for known legs, dashed for assumed ones
  const solid = [], dashed = [];
  u.legs.forEach(l => {
    if (l.from.t > state.t) return;
    const done = l.coords.filter((c, j) => l.times[j] <= state.t);
    const line = l.to.t <= state.t ? l.coords : [l.coords[0], ...done.slice(1), positionAt(u, state.t)];
    (l.assumed ? dashed : solid).push(line);
  });
  u.pastPath?.attr("d", path({ type: "MultiLineString", coordinates: solid }));
  u.pastAssumed?.attr("d", path({ type: "MultiLineString", coordinates: dashed }));
  u.pts.forEach(d => d.node?.classList.toggle("future", d.t > state.t));
  u.acts.forEach(d => d.node?.classList.toggle("future", d.t > state.t));
  rescale();
  document.getElementById("now-where").textContent = rowAt(u, state.t)?.station ?? "";
  d3.select("#strip .playhead").attr("x1", stripX(state.t)).attr("x2", stripX(state.t));
  highlightRows(!fromList);
}

function togglePlay() { state.playing ? stop() : play(); }
function play() {
  if (state.t >= span()[1]) state.t = span()[0];
  state.playing = true;
  state.last = null;
  Object.assign(document.getElementById("play"), { textContent: "❚❚", ariaLabel: "Pause" });
  requestAnimationFrame(tick);
}
function tick(now) {
  if (!state.playing) return;
  const dt = state.last === null ? 0 : (now - state.last) / 1000;
  state.last = now;
  setTime(state.t + dt * DAYS_PER_SECOND * DAY);
  if (state.t >= span()[1]) stop(); else requestAnimationFrame(tick);
}
function stop() {
  state.playing = false;
  Object.assign(document.getElementById("play"), { textContent: "▶", ariaLabel: "Play" });
}

// Timeline strip: the unit's stations, a tick per station, each span hatched where the position
// is a headquarters' or division's (assumed), and the months after December 1944, when the
// morning reports aren't online, set off.
let stripX = () => 0;
function drawStrip() {
  const strip = d3.select("#strip");
  const W = strip.node().getBoundingClientRect().width || 600;
  const u = chosen(), LEFT = 8, AXIS = 22, H = AXIS + 18;
  strip.attr("viewBox", `0 0 ${W} ${H}`).style("height", `${H}px`).selectAll("*").remove();
  const x = d3.scaleUtc().domain(span()).range([LEFT, W - 8]);
  stripX = t => x(t);
  strip.append("defs").append("pattern").attr("id", "hatch").attr("width", 5).attr("height", 5)
    .attr("patternUnits", "userSpaceOnUse").attr("patternTransform", "rotate(45)")
    .append("line").attr("y2", 5).attr("stroke", "var(--surface-1)").attr("stroke-width", 2);
  const [t0, t1] = span();
  if (t1 > ONLINE_UNTIL) {
    const a = x(Math.max(ONLINE_UNTIL, t0));
    strip.append("rect").attr("x", a).attr("y", 0).attr("width", x(t1) - a).attr("height", AXIS - 2)
      .attr("fill", "var(--wash)")
      .append("title").text("1945: morning reports not yet online at NARA; positions from the units' own histories and journals, Third Army's report and division sources");
  }
  const y = 3;
  u.rows.forEach((r, j) => {
    const next = u.rows[j + 1], a = x(r.t), b = x(next ? next.t : u.t1 + DAY);
    const seg = strip.append("rect").attr("x", a).attr("y", y).attr("width", Math.max(1, b - a)).attr("height", 12)
      .attr("fill", r.plotted ? "var(--series-track)" : "var(--text-muted)");
    seg.append("title").text(`${fmtDay(new Date(r.t))}: ${r.station}${r.bn ? " (position assumed)" : ""}`);
    if (r.bn) strip.append("rect").attr("x", a).attr("y", y).attr("width", Math.max(0, b - a)).attr("height", 12)
      .attr("fill", "url(#hatch)").attr("pointer-events", "none");
    strip.append("line").attr("x1", a).attr("x2", a).attr("y1", y + 12).attr("y2", y + 15)
      .attr("stroke", "var(--series-track)");
  });
  actsOf(u).forEach(a => strip.append("path").attr("d", "M0,-2.5L2.5,0L0,2.5L-2.5,0Z")
    .attr("transform", `translate(${x(a.t)},${y + 6})`).attr("fill", "var(--series-attack)").attr("stroke", "var(--text-primary)")
    .attr("stroke-width", 1).append("title").text(`${fmtDay(new Date(a.t))}: ${a.station}`));
  strip.append("g").attr("class", "axis").attr("transform", `translate(0,${AXIS})`)
    .call(d3.axisBottom(x).ticks(Math.max(3, Math.floor((W - LEFT) / 90))).tickFormat(fmtMonth).tickSizeOuter(0));
  strip.append("line").attr("class", "playhead").attr("y1", 0).attr("y2", AXIS)
    .attr("stroke", "var(--text-primary)").attr("stroke-width", 1.5);
  strip.on("click", ev => { stop(); setTime(+x.invert(d3.pointer(ev)[0])); });
}

// ── Side panel: the units (all-units view), or one unit's stations and actions ─
function renderSide() {
  const list = document.getElementById("list");
  list.replaceChildren();
  const u = chosen();
  list.append(el("div", "unit-note", u.note));
  const rows = [...u.rows, ...actsOf(u)].sort((a, b) => a.t - b.t || (a.act ? 1 : 0) - (b.act ? 1 : 0));
  const nActs = rows.filter(r => r.act).length;
  document.getElementById("side-title").textContent =
    `Stations (${rows.length - nActs})${nActs ? ` and actions (${nActs})` : ""}`;
  rows.forEach(r => list.append(r.act ? actionRow(r) : stationRow(r)));
}

// Each entry (entry.css): the date; a bar in the colour of its mark (dashed where the position is the battalion's or
// isn't known); where, with the grid reference as typed; the STATION line as typed; how it was placed; the page.
function dayCol(t) {
  const d = el("div", "t", d3.utcFormat("%-d %b")(new Date(t)));
  d.append(el("small", null, d3.utcFormat("%Y")(new Date(t))));
  return d;
}

function stationRow(r) {
  const row = el("div", "row entry" + (!r.plotted || r.bn ? " assumed" : ""));
  row.style.setProperty("--bar", r.plotted ? "var(--series-track)" : "var(--text-muted)");
  row.tabIndex = 0;
  row.setAttribute("role", "button");
  row.dataset.t = r.t;
  const body = el("div", "body");
  const who = el("div", "who");
  who.append(el("b", null, r.place || "No position"));
  if (r.grid) who.append(el("span", "own", r.grid));
  body.append(who, el("div", "said", r.station));
  const placed = placedText(r);
  if (placed) body.append(el("div", "note", placed));
  (r.ships || []).forEach(sh => body.append(shipBlock(sh)));
  if (r.arrived_by) body.append(el("div", "note", `Landed from ${r.arrived_by.map(shipName).join(" or ")} (see the crossing above)`));
  if (r.presumed) body.append(el("div", "assume", r.presumed));
  if (r.routeNote) body.append(el("div", "assume", r.routeNote));
  if (r.note) body.append(el("div", "note", r.note));
  body.append(pageLink(r, pageLabel(r)));
  row.append(dayCol(r.t), body);
  const go = () => { stop(); setTime(r.t, { fromList: true }); if (r.plotted) flyTo(r); };
  row.addEventListener("click", go);
  row.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); go(); } });
  return row;
}

function actionRow(r) {
  const row = el("div", "row entry action");
  row.style.setProperty("--bar", "var(--series-attack)");
  row.tabIndex = 0;
  row.setAttribute("role", "button");
  row.dataset.t = r.t;
  row.dataset.act = "1";
  const body = el("div", "body");
  const who = el("div", "who");
  who.append(el("b", null, r.station));
  if (r.time) who.append(el("span", "own", r.time));
  body.append(who, el("div", "said", r.text), el("div", "note", actionPlaced(r)));
  if (r.note) body.append(el("div", "note", r.note));
  body.append(pageLink(r, pageLabel(r)));
  row.append(dayCol(r.t), body);
  const go = () => { stop(); setTime(r.t, { fromList: true }); flyTo(r); };
  row.addEventListener("click", go);
  row.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); go(); } });
  return row;
}

function pageLink(r, text) {
  const a = el("a", "src alone", text);
  a.href = "#";
  a.addEventListener("click", e => { e.preventDefault(); e.stopPropagation(); openScan(r); });
  return a;
}

// How an action's map point was made
function actionPlaced(a) {
  if (a.placed === "grid") return `Mapped at grid ${a.grid}, the position the report gives`;
  if (a.placed === "place") return `Mapped at ${a.place}`;
  return "The report gives no usable position: mapped at the battery's station that day";
}

function highlightRows(scroll) {
  const rows = [...document.querySelectorAll("#list .row")];
  const mine = rows.filter(r => !r.dataset.act);
  const cur = mine.filter(r => +r.dataset.t <= state.t).at(-1);
  mine.forEach(r => { r.classList.toggle("current", r === cur); r.classList.toggle("future", +r.dataset.t > state.t); });
  // scroll the log's own list, never the window: scrollIntoView also scrolled the page on load
  const list = document.getElementById("list");
  if (cur && scroll && (cur.offsetTop < list.scrollTop || cur.offsetTop + cur.offsetHeight > list.scrollTop + list.clientHeight))
    list.scrollTop = cur.offsetTop - list.clientHeight / 3;
  rows.filter(r => r.dataset.act).forEach(r => r.classList.toggle("future", +r.dataset.t > state.t));
}

function flyTo(d) {
  if (d.x === undefined) return;
  const box = svg.node().viewBox.baseVal;
  const k = Math.max(state.k, 4);
  svg.transition().duration(600).call(zoom.transform,
    d3.zoomIdentity.translate(box.width / 2, box.height / 2).scale(k).translate(-d.x, -d.y));
}

// "Mapped 10 mi SE of Battipaglia" — how the map point was made from the typed station
function placedText(r) {
  if (!r.plotted) return "No position given — not on the map (route between neighbours assumed)";
  const town = r.offset ? `${r.offset} of ${r.place}` : r.place;
  const g = r.grid_check, km = g && `${g.km_from_town.toFixed(1)} km`;
  const atTown = r.offset ? `Mapped ${town}` : `Mapped at ${town}`;
  return r.placed === "grid" ? `Mapped at the grid reference ${r.grid} (${g.on}${g.square_from_town ? ", square assumed from the town" : ""}), ${km} from ${town}${r.offset ? " as typed" : ""}` :
    r.placed === "grid-place" ? `Mapped at ${r.place}, from the grid reference (${r.place_note})` :
    !g ? atTown :
    g.cell_m >= 10000 ? `${atTown} (the grid reference ${r.grid} is only good to 10 km)` :
    `${atTown} (the grid reference ${r.grid} falls ${km} away; see the note)`;
}

// The ship of a sea crossing (records/army/ships.csv): what the report typed, whether the ship is
// identified, its history and the voyage as the unit's records give it
const SHIP_STATUS = { confirmed: "Ship identified", candidate: "Possible identification, unconfirmed",
                      unknown: "Ship not identified", none: "Crossing not recorded" };
const shipName = sh => sh.ship || "an unrecorded ship";
function shipBlock(sh) {
  const box = el("div", `ship ${sh.status}`);
  box.append(el("div", "ship-head", sh.ship ? `${sh.ship} · ${SHIP_STATUS[sh.status]}` : SHIP_STATUS[sh.status]));
  if (sh.about) box.append(el("div", null, sh.about));
  if (sh.voyage) box.append(el("div", "ship-voyage", sh.voyage));
  sh.links.forEach(u => {
    const navy = /history\.navy\.mil/.test(u);
    const label = !navy ? `${new URL(u).hostname} ↗` : sh.status === "confirmed" ? "Navy ship history (DANFS) ↗"
                : "Navy history of the hull with that number (DANFS) ↗";
    const a = el("a", null, label);
    a.href = u; a.target = "_blank"; a.rel = "noopener";
    a.addEventListener("click", e => e.stopPropagation());
    box.append(a);
  });
  return box;
}

// Where a row comes from (records/SOURCES.yml): a morning report (nara-catalog, rg64-…), the
// 106th AAA's monthly records and journal (ok45th-…), the 894th's history (hist894/…), Third
// Army's report (aar3/…), or a source only linked (gi9ad, wiki9ad)
const kindOf = r => r.page.startsWith("ok45th-") ? "museum" : r.page.startsWith("hist894/") ? "hist"
  : r.page.startsWith("aar3/") ? "aar" : LINKED[r.page] ? "linked" : "mr";
const SOURCE_NAME = { museum: "106th AAA record", hist: "894th AAA history", aar: "Third Army report", mr: "Morning report" };
const SOURCE_TITLE = { mr: "Morning reports", museum: "The 106th AAA's histories and journal", hist: "The 894th's printed history",
                       aar: "Third Army's after action report", linked: "Division sources" };
const pageNo = r => r.page.includes("/p") ? parseInt(r.page.split("/p")[1], 10) : "";
const pageLabel = r => kindOf(r) === "linked" ? `${LINKED[r.page][1]} ↗`
  : `${SOURCE_NAME[kindOf(r)]}, ${kindOf(r) === "aar" ? "PDF " : ""}page ${pageNo(r)} ↗`;
const clickText = d => kindOf(d) === "linked" ? `Click to open ${LINKED[d.page][1]} ↗`
  : `Click to view ${SOURCE_NAME[kindOf(d)].replace(/^Morning/, "morning")} ${kindOf(d) === "aar" ? "PDF " : ""}page ${pageNo(d)}`;

// ── Stats & legend ──────────────────────────────────────────────────────────
function renderStats() {
  const box = document.getElementById("stats");
  box.replaceChildren();
  const fmt = d3.format(",.0f");
  const tile = (label, value, sub) => { const t = el("div", "tile"); t.append(el("div", "label", label), el("div", "value", value), el("div", "sub", sub)); box.append(t); };
  const u = chosen();
  tile("Stations", u.rows.length, `${fmtDay(new Date(u.t0))} – ${fmtDay(new Date(u.t1))}`);
  tile("Distance", `${fmt(u.km)} km`, "between stations (straight lines and drawn routes)");
  const assumed = u.rows.filter(r => r.bn).length;
  tile("Own position", `${u.rows.length - assumed} of ${u.rows.length}`,
       assumed ? `${assumed} assumed from a headquarters' or division's position` : "every station from the unit's own records");
  if (u.acts.length) tile("Actions", u.acts.length, "from the unit's own records");
  // the sources this unit's stations cite, most-cited first
  const cited = d3.rollups(u.rows, v => v.length, kindOf).sort((a, b) => b[1] - a[1]).map(([k]) => SOURCE_TITLE[k]);
  tile(cited.length > 1 ? "Sources" : "Source", cited[0], cited.slice(1).join("; ") || " ");
}

function renderLegend() {
  const lg = document.getElementById("legend");
  lg.replaceChildren();
  const item = (draw, text) => {
    const s = el("span");
    const v = d3.create("svg").attr("width", 22).attr("height", 12);
    draw(v.append("g").attr("transform", "translate(11,6)"));
    s.append(v.node(), document.createTextNode(text));
    lg.append(s);
  };
  const u = chosen();
  item(g => { g.append("line").attr("x1", -10).attr("x2", 10).attr("stroke", "var(--series-track)").attr("stroke-width", 2.5);
              g.append("circle").attr("r", 3.5).attr("fill", "var(--series-track)"); },
       "Station on the unit's morning report or in its own records");
  if (u.rows.some(r => r.bn))
    item(g => g.append("circle").attr("r", 3.5).attr("fill", "var(--surface-1)").attr("stroke", "var(--series-track)").attr("stroke-width", 2),
         "A headquarters' or division's position: the unit's own assumed, legs dashed");
  item(g => g.append("line").attr("x1", -10).attr("x2", 10).attr("stroke", "var(--series-track)")
    .attr("stroke-width", 2).attr("stroke-dasharray", "5 4"), "Route assumed: at sea, or along a 1942 road (no position given)");
  if (ROADS) item(g => g.append("line").attr("x1", -10).attr("x2", 10).attr("class", "road"), "Primary roads of 1942 (OSS Map 967, traced)");
  if (actsOf(u).length)
    item(g => g.append("path").attr("d", "M0,-5L5,0L0,5L-5,0Z").attr("fill", "var(--series-attack)")
                .attr("stroke", "var(--text-primary)").attr("stroke-width", 1.2),
         "In action, from the unit's own records (hollow: casualty)");
  item(g => { g.append("rect").attr("x", -10).attr("y", -5).attr("width", 20).attr("height", 10).attr("fill", "var(--series-track)");
              [-12, -6, 0, 6].forEach(x0 => g.append("line").attr("x1", x0).attr("y1", 5).attr("x2", x0 + 10).attr("y2", -5)
                .attr("stroke", "var(--surface-1)").attr("stroke-width", 2));
              g.append("rect").attr("x", -11).attr("y", -6).attr("width", 22).attr("height", 12).attr("fill", "none")
                .attr("stroke", "var(--surface-1)").attr("stroke-width", 2); },
       "Timeline hatched: position assumed");
}

// ── Tooltip & scan viewer ───────────────────────────────────────────────────
function pointTip(d) {
  const f = document.createDocumentFragment();
  f.append(el("div", "v", d.station), el("div", "k", `${fmtDay(new Date(d.t))} · ${d.unitName.split(" / ")[0]}`),
           el("div", null, placedText(d)));
  if (d.presumed) f.append(el("div", "i", `Assumed: ${d.presumed}`));
  if (d.routeNote) f.append(el("div", "i", "Route there drawn approximately (not in the reports)."));
  if (d.note) f.append(el("div", "i", d.note));
  if (d.arrived_by) f.append(el("div", "k", `Came by sea: ${d.arrived_by.map(sh => `${shipName(sh)} (${SHIP_STATUS[sh.status].toLowerCase()})`).join(" or ")}`));
  (d.ships || []).forEach(sh => f.append(el("div", "k", sh.ship ? `Ship: ${sh.ship} (${SHIP_STATUS[sh.status].toLowerCase()})` : SHIP_STATUS[sh.status])));
  f.append(el("div", "m", clickText(d)));
  return f;
}
function actionTip(d) {
  const f = document.createDocumentFragment();
  f.append(el("div", "v", d.station), el("div", "k", `${fmtDay(new Date(d.t))}${d.time ? ` ${d.time}` : ""} · ${d.unitName.split(" / ")[0]}`),
           el("div", null, `“${d.text.length > 220 ? d.text.slice(0, 220) + "…" : d.text}”`),
           el("div", "i", actionPlaced(d)));
  if (d.note) f.append(el("div", "i", d.note));
  f.append(el("div", "m", clickText(d)));
  return f;
}
function showTip(ev, content) { tip.replaceChildren(content); tip.style.display = "block"; moveTip(ev); }
function moveTip(ev) {
  const r = tip.getBoundingClientRect();
  const x = ev.clientX + 14 + r.width > innerWidth ? ev.clientX - r.width - 14 : ev.clientX + 14;
  const y = ev.clientY + 14 + r.height > innerHeight ? ev.clientY - r.height - 14 : ev.clientY + 14;
  tip.style.left = `${x}px`; tip.style.top = `${y}px`;
}
function hideTip() { tip.style.display = "none"; }

// Show a page: the local copy in the cache when there is one, otherwise a link to the archive's
// own copy. NARA's morning reports are TIFFs, which browsers won't show (tools/morning_reports.py
// fetch saves JPEGs to nara/); the museum's records are PDFs (rendered to 45th-museum/); the
// 894th's history isn't online (rendered to 894th-history/); Third Army's report is on Google
// Books (rendered to googlebooks/pages/).
function openScan(d) {
  hideTip();
  const kind = kindOf(d);
  if (kind === "linked") return window.open(LINKED[d.page][0], "_blank", "noopener");
  const [folder, page] = d.page.split("/"), n = pageNo(d);
  const id = folder.replace(/^(ok45th|rg64)-/, "");
  const where = {
    mr: { url: `https://catalog.archives.gov/id/${id}?objectPage=${n}`, link: "Open in National Archives catalog ↗",
          src: `nara/${folder}/${page}.jpg`, fetch: `python3 tools/morning_reports.py fetch ${id} ${n}` },
    museum: { url: `${MUSEUM}${id}`, link: "Open at the 45th Infantry Division Museum ↗",
              src: `45th-museum/${folder}/${page}.jpg`, note: `The record is a PDF there; this is its page ${n}.` },
    hist: { url: null, link: "894th AAA Bn History and Combat Diary, 1940–1945 (not online)",
            src: `894th-history/${page}.jpg`, note: "The kit read a retyped copy made in 2012 (hist894 in the records' SOURCES.yml)." },
    aar: { url: AAR_BOOK, link: "Third Army After Action Report, Vol. II, on Google Books ↗",
           src: `googlebooks/pages/p${String(n).padStart(3, "0")}.png`, note: `It's page ${n} of the book's full-view PDF.` },
  }[kind];
  document.getElementById("scan-title").textContent = `${d.station} · ${fmtDay(new Date(d.t))} · ${kind === "aar" ? "PDF " : ""}page ${n}`;
  const link = document.getElementById("scan-link");
  if (where.url) link.href = where.url; else link.removeAttribute("href");
  link.textContent = where.link;
  document.getElementById("scan-credit").hidden = kind !== "museum";
  const img = document.getElementById("scan-img"), missing = document.getElementById("scan-missing");
  img.classList.remove("full");
  img.hidden = false; missing.hidden = true;
  img.onerror = () => {
    img.hidden = true; missing.hidden = false;
    // the source, and on this machine, how to get the page into the cache
    const parts = [where.url ? Object.assign(el("a", null, where.link), { href: where.url, target: "_blank", rel: "noopener" }) : el("span", null, where.link)];
    if (where.note) parts.push(el("div", "fixnote", where.note));
    if (LOCAL) parts.push(el("div", "fixnote", `Not in your local copy of the scans${where.fetch ? `: ${where.fetch}` : ""}`));
    missing.replaceChildren(...parts);
  };
  img.src = CACHE + where.src;
  img.alt = `${SOURCE_NAME[kind]}, page ${n}`;
  document.getElementById("scan").showModal();
}

function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}
