// USS BANG dive profile.
// Renders records/boats/ss-385-bang/dives.json (tools/build_dives.py): the depth log transcribed from
// each war patrol report, the report's density-layer (bathythermograph) table,
// ETOPO1 seafloor and ERA5 weather along the track, and the track fixes (used to
// place the boat for sun and moon).

const PATROLS = [
  { n: 1, name: "First War Patrol",  dates: "29 Mar – 14 May 1944" },
  { n: 2, name: "Second War Patrol", dates: "6 Jun – 2 Aug 1944" },
  { n: 3, name: "Third War Patrol",  dates: "27 Aug – 29 Sep 1944" },
  { n: 4, name: "Fourth War Patrol", dates: "25 Oct – 5 Dec 1944" },
  { n: 5, name: "Fifth War Patrol",  dates: "2 Jan – 24 Feb 1945" },
  { n: 6, name: "Sixth War Patrol",  dates: "25 Mar – 18 May 1945" },
];
// Zone letter -> hours ahead of GCT, as in tools/check_track.py
const ZONES = { Z: 0, M: 12, K: 10, I: 9, H: 8, X: -11, Y: -12, VW: -9.5, W: -10 };
const FT_PER_M = 3.28084;
const PERISCOPE_FT = 60;     // keel depth at periscope depth (assumed when a dive gives no depth)
const RADAR_DEPTH_FT = 40;   // decks awash / radar depth
const TEST_DEPTH_FT = 400;   // Balao-class rated test depth
const DESCENT_FT_PER_MIN = 100;
const BOAT_MAX_FT = 650;     // top panel range
const LAYER_HOLD = 30 * 36e5; // a bathythermograph reading is drawn until the next one, at most this long
const HOUR = 36e5, DAY = 864e5;
const SPEEDS = [{ label: "1 hr/s", v: HOUR }, { label: "4 hr/s", v: 4 * HOUR }, { label: "1 day/s", v: DAY }];
const WEATHER_WORDS = /\b(sea state|state \d|force \w+|wind|seas\b|squall|snow|overcast|calm|rough|barometer|visibility|rain|tide rips)/i;

const LABEL = {
  dive: "Submerged", surface: "Surfaced", periscope: "Periscope depth", radar_depth: "Radar depth",
  depth: "Depth order", passing: "Passing depth", bottom: "Sat on the bottom", charges: "Depth charges", quake: "Earthquake",
};

const state = { patrol: 2, domain: null, filter: "notable", playing: false, t: null, speed: 1 };
let DATA, P, x;
const svg = d3.select("#chart");
const tip = document.getElementById("tip");

d3.json(RECORDS + "boats/ss-385-bang/dives.json").then(data => {
  DATA = data;
  buildControls();
  const q = new URLSearchParams(location.search);
  const qp = +q.get("patrol");
  const t = q.get("t") ? Date.parse(q.get("t")) : null;
  select(DATA.patrols.some(p => p.patrol === qp) ? qp : 2, t);
  new ResizeObserver(() => { render(); renderDayNight(); }).observe(document.querySelector(".chart-wrap"));
});

// ── Model ───────────────────────────────────────────────────────────────────
function prepare(raw) {
  const events = raw.events.map(e => ({ ...e, t: Date.parse(e.utc), zone: /\((\w+)\)$/.exec(e.local)[1] }));
  const seafloor = raw.seafloor.map(([u, m]) => [Date.parse(u), Math.min(0, m) * -FT_PER_M]);
  const fixes = raw.fixes.map(([u, lon, lat]) => [Date.parse(u), (lon + 360) % 360, lat]);
  const start = Date.parse(raw.start), end = Date.parse(raw.end);
  const layers = raw.layers.map(l => ({ ...l, t: Date.parse(l.utc) }));
  layers.forEach((l, i) => { l.t1 = Math.min(layers[i + 1]?.t ?? end, l.t + LAYER_HOLD); });
  const weather = raw.weather.map(([u, wind, dir, gust, cloud, rain, temp, pres]) =>
    ({ t: Date.parse(u), wind, dir, gust, cloud, rain, temp, pres }));
  // set the module-level P first: positionAt/depthAt below read it
  const sky = (raw.sky ?? []).map(n => ({ ...n, t: Date.parse(n.utc) }));
  P = { n: raw.patrol, start, end, events, seafloor, fixes, layers, weather, sky,
        routine: raw.routine.map(r => ({ ...r, t0: Date.parse(r.from), t1: Date.parse(r.to) })) };
  P.nights = nightSpans(P);
  P.unlogged = unloggedDays(P);
  P.profile = buildProfile(P);
  P.moments = keyMoments(P);
  P.remarks = events.filter(e => WEATHER_WORDS.test(e.quote));
  return P;
}

// Depth over time: hold each depth until the next logged event, then change at
// about 100 ft/min. Dives with no depth given assume periscope depth. Two kinds
// of assumed entries fill gaps in the log (marked `assumed`, never listed):
//  - "routine": on days covered by "submerged during daylight" with no itemized
//    times, dive at sunrise and surface at sunset;
//  - "dark": if a dive has no surfacing logged before the next night, surface
//    half an hour after dark, as the boats did to charge batteries.
function buildProfile(P) {
  const routine = P.unlogged.flatMap(u => [
    { t: u.t0, event: "dive", assumed: "routine" }, { t: u.t1, event: "surface", assumed: "routine" }]);
  const queue = [...P.events, ...routine].sort((a, b) => a.t - b.t);
  const pts = [{ t: P.start, d: 0, src: null }];
  let d = 0, subSince = null;
  for (let qi = 0; qi < queue.length; qi++) {
    const e = queue[qi];
    if (d > 0 && subSince !== null && e.assumed !== "dark") {
      const night = P.nights.find(([a]) => a > subSince + HOUR);
      const surfaceAt = night ? night[0] + 30 * 60e3 : null;
      // a logged surfacing during that same night is believed; one after the next sunrise is not
      if (surfaceAt && surfaceAt < e.t - HOUR && (e.event !== "surface" || e.t > night[1])) {
        queue.splice(qi, 0, { t: surfaceAt, event: "surface", assumed: "dark" });
        qi--; continue;
      }
    }
    let next = d;
    if (e.event === "surface") next = 0;
    else if (e.event === "dive" || e.event === "periscope") next = PERISCOPE_FT;
    else if (e.event === "radar_depth") next = RADAR_DEPTH_FT;
    else if ((e.event === "depth" || e.event === "bottom") && e.depth_ft) next = e.depth_ft;
    if (next === d) continue;
    const last = pts.at(-1);
    const t0 = Math.max(e.t, last.t);
    pts.push({ t: t0, d, src: last.src });
    const ramp = Math.max(1, Math.abs(next - d) / DESCENT_FT_PER_MIN) * 60e3;
    pts.push({ t: t0 + ramp, d: next, src: e });
    if (d === 0 && next > 0) subSince = t0;
    if (next === 0) subSince = null;
    d = next;
  }
  pts.push({ t: P.end, d, src: pts.at(-1).src });
  return pts;
}

function depthAt(t) {
  const pts = P.profile;
  const i = d3.bisector(p => p.t).right(pts, t) - 1;
  if (i < 0) return { d: 0, src: null };
  const a = pts[i], b = pts[i + 1];
  if (!b || b.t === a.t) return a;
  return { d: a.d + (b.d - a.d) * (t - a.t) / (b.t - a.t), src: t >= b.t ? b.src : a.src };
}

// The report's clock changed zone as the boat moved west; use the zone of the
// latest log entry at or before t.
function zoneAt(t) {
  const i = d3.bisector(e => e.t).right(P.events, t) - 1;
  return (P.events[Math.max(0, i)] ?? { zone: "Z" }).zone;
}

function seafloorAt(t) {
  const s = P.seafloor;
  const i = Math.max(0, Math.min(s.length - 1, d3.bisector(p => p[0]).center(s, t)));
  return s[i][1];
}

function weatherAt(t) {
  const w = P.weather;
  if (!w.length) return null;
  const i = Math.max(0, Math.min(w.length - 1, d3.bisector(p => p.t).center(w, t)));
  return Math.abs(w[i].t - t) <= 2 * HOUR ? w[i] : null;
}

function layerAt(t) {
  const i = d3.bisector(l => l.t).right(P.layers, t) - 1;
  const l = P.layers[i];
  return l && t <= l.t1 ? l : null;
}

function positionAt(t) {
  const f = P.fixes;
  const i = Math.max(0, Math.min(f.length - 2, d3.bisector(p => p[0]).right(f, t) - 1));
  const a = f[i], b = f[i + 1];
  const k = Math.max(0, Math.min(1, (t - a[0]) / (b[0] - a[0] || 1)));
  return [a[1] + (b[1] - a[1]) * k, a[2] + (b[2] - a[2]) * k];
}

// ── Sun and moon (low-precision almanac formulae; good to about a degree) ────
const RAD = Math.PI / 180;
function altitude(ra, dec, t, lon, lat) {
  const d = t / DAY - 10957.5;
  const ha = (280.16 + 360.9856235 * d) * RAD + lon * RAD - ra;
  return Math.asin(Math.sin(lat * RAD) * Math.sin(dec) + Math.cos(lat * RAD) * Math.cos(dec) * Math.cos(ha)) / RAD;
}
function sunAltitude(t, lon, lat) {
  const d = t / DAY - 10957.5;
  const g = (357.529 + 0.98560028 * d) * RAD;
  const L = (280.459 + 0.98564736 * d + 1.915 * Math.sin(g) + 0.020 * Math.sin(2 * g)) * RAD;
  const e = (23.439 - 0.00000036 * d) * RAD;
  return altitude(Math.atan2(Math.cos(e) * Math.sin(L), Math.cos(L)), Math.asin(Math.sin(e) * Math.sin(L)), t, lon, lat);
}
function moonAltitude(t, lon, lat) {
  const d = t / DAY - 10957.5;
  const L = (218.316 + 13.176396 * d) * RAD, Mm = (134.963 + 13.064993 * d) * RAD, F = (93.272 + 13.229350 * d) * RAD;
  const l = L + 6.289 * RAD * Math.sin(Mm), b = 5.128 * RAD * Math.sin(F), e = 23.4397 * RAD;
  const ra = Math.atan2(Math.sin(l) * Math.cos(e) - Math.tan(b) * Math.sin(e), Math.cos(l));
  const dec = Math.asin(Math.sin(b) * Math.cos(e) + Math.cos(b) * Math.sin(e) * Math.sin(l));
  return altitude(ra, dec, t, lon, lat);
}
const SYNODIC = 29.530588853, NEW_MOON_2000 = Date.UTC(2000, 0, 6, 18, 14);
const moonAge = t => (((t - NEW_MOON_2000) / DAY) % SYNODIC + SYNODIC) % SYNODIC;
const moonLit = t => (1 - Math.cos(2 * Math.PI * moonAge(t) / SYNODIC)) / 2;
function moonName(t) {
  const a = moonAge(t) / SYNODIC;
  return a < 0.03 || a > 0.97 ? "new moon" : a < 0.22 ? "waxing crescent" : a < 0.28 ? "first quarter"
    : a < 0.47 ? "waxing gibbous" : a < 0.53 ? "full moon" : a < 0.72 ? "waning gibbous" : a < 0.78 ? "last quarter" : "waning crescent";
}
// SVG path of the lit part of the moon (radius r), as seen from the northern hemisphere
function moonPath(t, r) {
  const k = moonLit(t), waxing = moonAge(t) < SYNODIC / 2;
  const rx = r * Math.abs(1 - 2 * k), bulge = k < 0.5 ? 0 : 1;
  const p = `M0,${-r} A${r},${r} 0 0 1 0,${r} A${rx},${r} 0 0 ${bulge} 0,${-r} Z`;
  return { d: p, mirror: !waxing };
}

function nightSpans(P) {
  const spans = [], step = 10 * 60e3;
  let open = null;
  for (let t = P.start; t <= P.end; t += step) {
    const [lon, lat] = positionAt(t);
    const night = sunAltitude(t, lon, lat) < -0.833;
    if (night && open === null) open = t;
    if (!night && open !== null) { spans.push([open, t]); open = null; }
  }
  if (open !== null) spans.push([open, P.end]);
  return spans;
}

// Daylight stretches inside a "submerged during daylight" summary that have no
// itemized dive or surface entry — the only places the hatch belongs.
function unloggedDays(P) {
  const out = [];
  const logged = P.events.filter(e => ["dive", "surface", "depth", "periscope"].includes(e.event)).map(e => e.t);
  for (const r of P.routine) {
    const nights = P.nights.filter(([a, b]) => b > r.t0 && a < r.t1);
    for (let i = 0; i < nights.length - 1; i++) {
      const day0 = Math.max(r.t0, nights[i][1]), day1 = Math.min(r.t1, nights[i + 1][0]);
      if (day1 > day0 && !logged.some(t => t >= day0 - HOUR && t <= day1 + HOUR)) out.push({ t0: day0, t1: day1, r });
    }
  }
  return out;
}

// Days worth jumping to: deep depth orders, depth charges, the bottom, the quake
function keyMoments(P) {
  const notable = P.events.filter(e => (e.depth_ft ?? 0) >= 300 || e.charges || ["bottom", "quake", "charges"].includes(e.event));
  return d3.groups(notable, e => e.local.slice(0, 10)).map(([day, es]) => {
    const deepest = d3.max(es, e => e.depth_ft ?? 0);
    const charges = d3.sum(es, e => e.charges ?? 0);
    const bottom = es.find(e => e.event === "bottom");
    const quake = es.find(e => e.event === "quake");
    const what = bottom ? `on the bottom, ${bottom.depth_ft} ft` : quake ? "earthquake"
      : [deepest ? `${deepest} ft` : null, charges ? `${charges} ${P.n === 6 ? "bomb" : "depth charge"}${charges === 1 ? "" : "s"}` : null]
          .filter(Boolean).join(" · ") || "depth charging heard";
    return { day, what, t0: d3.min(es, e => e.t), t1: d3.max(es, e => e.t) };
  });
}

// ── Controls ────────────────────────────────────────────────────────────────
function buildControls() {
  const seg = document.getElementById("patrol-seg");
  PATROLS.forEach(p => {
    const b = el("button", null, `Patrol ${p.n}`);
    b.dataset.p = p.n;
    b.addEventListener("click", () => select(p.n));
    seg.append(b);
  });
  document.querySelectorAll("#log-filter button").forEach(b => b.addEventListener("click", () => {
    state.filter = b.dataset.f;
    document.querySelectorAll("#log-filter button").forEach(x => x.setAttribute("aria-pressed", x === b));
    renderSide();
  }));
  const speeds = document.getElementById("speed");
  SPEEDS.forEach((s, i) => {
    const b = el("button", null, s.label);
    b.setAttribute("aria-pressed", i === state.speed);
    b.addEventListener("click", () => {
      state.speed = i;
      speeds.querySelectorAll("button").forEach((x, j) => x.setAttribute("aria-pressed", j === i));
    });
    speeds.append(b);
  });
  document.getElementById("play").addEventListener("click", () => state.playing ? stop() : play());
  document.getElementById("scan-close").addEventListener("click", () => document.getElementById("scan").close());
  document.getElementById("scan-img").addEventListener("click", e => e.target.classList.toggle("full"));
}

function select(n, focusT = null) {
  stop();
  state.patrol = n;
  prepare(DATA.patrols.find(p => p.patrol === n));
  document.querySelectorAll("#patrol-seg button").forEach(b => b.setAttribute("aria-pressed", +b.dataset.p === n));
  state.domain = focusT ? [focusT - 18 * HOUR, focusT + 18 * HOUR] : [P.start, P.end];
  state.t = focusT;
  renderChips();
  renderStats();
  renderLegend();
  renderSide();
  render();
  renderDayNight();
  updateReadout(state.t ?? P.start);
}

function setDomain(dom, fromBrush = false) {
  const span = Math.max(dom[1] - dom[0], 2 * HOUR);
  const mid = (dom[0] + dom[1]) / 2;
  let a = mid - span / 2, b = mid + span / 2;
  if (a < P.start) { b += P.start - a; a = P.start; }
  if (b > P.end) { a -= b - P.end; b = P.end; }
  state.domain = [Math.max(P.start, a), Math.min(P.end, b)];
  document.querySelectorAll(".chip").forEach(c => c.setAttribute("aria-pressed",
    c.dataset.t0 ? +c.dataset.t0 === state.domain[0] : state.domain[0] === P.start && state.domain[1] === P.end));
  drawMain();
  if (!fromBrush) moveBrush();
  updateMapLink();
}

function renderChips() {
  const box = document.getElementById("chips");
  box.replaceChildren(el("span", "lbl", "Jump to:"));
  const whole = el("button", "chip", "Whole patrol");
  whole.addEventListener("click", () => setDomain([P.start, P.end]));
  box.append(whole);
  P.moments.forEach(m => {
    const c = el("button", "chip", `${fmtDay(m.day)} · ${m.what}`);
    const pad = 8 * HOUR;
    const dom = [Math.max(P.start, m.t0 - pad), Math.min(P.end, m.t1 + pad)];
    c.dataset.t0 = dom[0];
    c.addEventListener("click", () => { stop(); setDomain(dom); });
    box.append(c);
  });
}

// ── Playback ────────────────────────────────────────────────────────────────
// The playhead advances at the chosen speed; the view keeps the span it had
// (36 h if it was showing the whole patrol) and pages forward to follow it.
let raf = null, lastFrame = null;
function play() {
  if (state.t === null || state.t >= P.end) state.t = state.domain[0] === P.start && state.domain[1] === P.end ? P.start : state.domain[0];
  if (state.domain[1] - state.domain[0] > 6 * DAY) setDomain([state.t - 6 * HOUR, state.t + 30 * HOUR]);
  state.playing = true;
  const b = document.getElementById("play");
  b.textContent = "❚❚"; b.setAttribute("aria-label", "Pause");
  lastFrame = null;
  raf = requestAnimationFrame(tick);
}
function tick(now) {
  if (!state.playing) return;
  if (lastFrame !== null) {
    state.t = Math.min(P.end, state.t + (now - lastFrame) / 1000 * SPEEDS[state.speed].v);
    const span = state.domain[1] - state.domain[0];
    if (state.t > state.domain[0] + 0.75 * span || state.t < state.domain[0])
      setDomain([state.t - 0.25 * span, state.t + 0.75 * span]);
    setPlayhead(state.t);
  }
  lastFrame = now;
  if (state.t >= P.end) return stop();
  raf = requestAnimationFrame(tick);
}
function stop() {
  state.playing = false;
  cancelAnimationFrame(raf);
  const b = document.getElementById("play");
  if (b) { b.textContent = "▶"; b.setAttribute("aria-label", "Play"); }
}
function setPlayhead(t) {
  if (!G.playhead) return;
  const show = t !== null && t >= state.domain[0] && t <= state.domain[1];
  G.playhead.style("display", show ? null : "none");
  if (show) {
    G.playhead.attr("transform", `translate(${x(t)},0)`);
    G.playDot.attr("cy", G.yA(depthAt(t).d));
  }
  d3.select("#strip-play").attr("x1", G.xo(t)).attr("x2", G.xo(t));
  dayNightCursor(t);
  updateReadout(t);
  highlightRow(lastEventBefore(t), false);
}
function lastEventBefore(t) {
  const rows = P.events.filter(e => state.filter === "all" || !["dive", "surface", "periscope"].includes(e.event));
  const i = d3.bisector(e => e.t).right(rows, t) - 1;
  return i >= 0 && t - rows[i].t < 12 * HOUR ? rows[i] : null;
}

// Live readout above the chart (playback or hover)
function updateReadout(t) {
  const box = document.getElementById("readout");
  if (!P || t === null) { box.replaceChildren(); return; }
  const d = depthAt(t), sea = seafloorAt(t), w = weatherAt(t), l = layerAt(t);
  const [lon, lat] = positionAt(t);
  const sun = sunAltitude(t, lon, lat), moon = moonAltitude(t, lon, lat);
  const item = (k, v) => { const s = el("span", "ro"); s.append(el("span", "k", k), el("b", null, v)); return s; };
  const glyph = d3.create("svg").attr("width", 16).attr("height", 16).attr("class", "ro-moon");
  drawMoon(glyph.append("g").attr("transform", "translate(8,8)"), t, 6.5);
  const moonItem = item("Moon", `${Math.round(moonLit(t) * 100)}% lit, ${moon > 0 ? "up" : "set"}`);
  moonItem.prepend(glyph.node());
  box.replaceChildren(
    item("Time", fmtLocal(t)),
    item("Depth", d.d < 1 ? "surface" : `${Math.round(d.d)} ft`),
    item("Seafloor", `${d3.format(",")(Math.round(sea / 10) * 10)} ft`),
    item("Sun", sun > 0 ? "day" : sun > -6 ? "twilight" : "night"),
    moonItem,
    item("Wind", w ? `${Math.round(w.wind)} kn ${compass(w.dir)}` : "—"),
    item("Layer", l ? layerText(l) : "—"),
  );
}

// ── Chart ───────────────────────────────────────────────────────────────────
const M = { top: 46, right: 18, left: 58 };
let G = {};

function render() {
  if (!P) return;
  const box = document.querySelector(".chart-wrap").getBoundingClientRect();
  const W = Math.max(500, box.width), H = Math.max(520, box.height);
  svg.attr("viewBox", `0 0 ${W} ${H}`).selectAll("*").remove();

  const ovH = 40, axisH = 22, gap = 30, hW = 54, gapW = 26;
  const avail = H - M.top - axisH - gap - gapW - hW - ovH - 34;
  const hA = Math.round(avail * 0.66), hB = avail - hA;
  const yA0 = M.top, yW0 = yA0 + hA + gapW, yB0 = yW0 + hW + gap;
  G = { W, H, hA, hB, hW, yA0, yW0, yB0, yAx: yB0 + hB, yOv: H - ovH - 6, ovH };

  const defs = svg.append("defs");
  const hatch = defs.append("pattern").attr("id", "hatch").attr("patternUnits", "userSpaceOnUse")
    .attr("width", 6).attr("height", 6).attr("patternTransform", "rotate(45)");
  hatch.append("line").attr("x1", 0).attr("y1", 0).attr("x2", 0).attr("y2", 6)
    .attr("stroke", "var(--text-muted)").attr("stroke-width", 1).attr("opacity", 0.5);
  const grad = defs.append("linearGradient").attr("id", "layer-grad").attr("x1", 0).attr("x2", 0).attr("y1", 0).attr("y2", 1);
  grad.append("stop").attr("offset", "0%").attr("stop-color", "var(--layer)").attr("stop-opacity", 0.05);
  grad.append("stop").attr("offset", "100%").attr("stop-color", "var(--layer)").attr("stop-opacity", 0.32);
  [["clipA", yA0, hA], ["clipW", yW0, hW], ["clipB", yB0, hB]].forEach(([id, y, h]) =>
    defs.append("clipPath").attr("id", id).append("rect").attr("x", M.left).attr("y", y).attr("width", W - M.left - M.right).attr("height", h));

  G.main = svg.append("g");
  drawOverview();
  drawMain();
  moveBrush();
  updateMapLink();
}

function drawMain() {
  const { W, hA, hB, hW, yA0, yW0, yB0, yAx } = G;
  const g = G.main.html("");
  x = d3.scaleUtc().domain(state.domain).range([M.left, W - M.right]);
  const zone = zoneAt((state.domain[0] + state.domain[1]) / 2), offset = ZONES[zone] * HOUR;
  const xl = d3.scaleUtc().domain(state.domain.map(t => t + offset)).range(x.range()); // logged-zone clock for ticks
  const yA = d3.scaleLinear().domain([0, BOAT_MAX_FT]).range([yA0, yA0 + hA]);
  const maxSea = Math.max(1000, d3.max(P.seafloor, s => s[1]) * 1.05);
  const yB = d3.scaleLinear().domain([0, maxSea]).range([yB0, yB0 + hB]);
  G.yA = yA;
  const inDom = (t0, t1) => t1 >= state.domain[0] && t0 <= state.domain[1];
  const span = state.domain[1] - state.domain[0];
  const cw = W - M.left - M.right;

  // Night shading (all panels)
  const nights = g.append("g");
  P.nights.filter(([a, b]) => inDom(a, b)).forEach(([a, b]) => {
    const x0 = Math.max(M.left, x(a)), x1 = Math.min(W - M.right, x(b));
    [[yA0, hA], [yW0, hW], [yB0, hB]].forEach(([y, h]) =>
      nights.append("rect").attr("class", "night").attr("x", x0).attr("width", Math.max(0, x1 - x0)).attr("y", y).attr("height", h));
  });

  // Moon phase for each day, above panel A (at local midnight on the report's clock)
  const days = d3.utcDay.range(new Date(state.domain[0] + offset), new Date(state.domain[1] + offset)).map(d => +d - offset);
  const dayPx = cw / Math.max(1, span / DAY);
  const moonStep = dayPx >= 18 ? 1 : dayPx >= 9 ? 2 : 4;
  days.forEach((t, i) => {
    if (i % moonStep) return;
    const mg = g.append("g").attr("transform", `translate(${x(t)},${yA0 - 26})`);
    drawMoon(mg, t, 6);
    mg.append("title").text(`${fmtLocal(t).slice(0, 11)} — ${moonName(t)}, ${Math.round(moonLit(t) * 100)}% lit`);
  });
  if (dayPx >= 60) days.forEach(t => {
    const a = moonName(t);
    if (a === "full moon" || a === "new moon")
      g.append("text").attr("class", "moon-label").attr("x", x(t) + 10).attr("y", yA0 - 22).text(a);
  });

  // ── Panel A: BANG's depth ──
  g.append("text").attr("class", "panel-title").attr("x", M.left).attr("y", yA0 - 6).text("BANG's depth (feet)");
  g.append("g").attr("class", "axis grid").attr("transform", `translate(${M.left},0)`)
    .call(d3.axisLeft(yA).ticks(6).tickSize(-cw).tickFormat(d => d === 0 ? "surface" : d));

  const aClip = g.append("g").attr("clip-path", "url(#clipA)");

  // Temperature layer from the report's density-layer table: warm water down to
  // the top of the layer, then a falling temperature down to the bottom of it
  P.layers.filter(l => inDom(l.t, l.t1)).forEach(l => {
    const x0 = x(l.t), x1 = x(l.t1);
    const top = l.iso_ft ?? 0, bottom = l.grad_ft && l.grad_ft > top ? l.grad_ft : null;
    if (bottom) aClip.append("rect").attr("class", "layer-band").attr("x", x0).attr("width", Math.max(1, x1 - x0))
      .attr("y", yA(top)).attr("height", yA(bottom) - yA(top));
    if (l.iso_ft) aClip.append("line").attr("class", "layer-top").attr("x1", x0).attr("x2", x1).attr("y1", yA(top)).attr("y2", yA(top));
    if (x1 - x0 > 90) aClip.append("text").attr("class", "layer-label").attr("x", x0 + 4).attr("y", (bottom ? yA(bottom) : yA(top)) + 13)
      .text(layerText(l));
  });

  // Seafloor in panel A when it comes within the boat's range (e.g. the Yellow Sea)
  const si0 = Math.max(0, d3.bisector(s => s[0]).left(P.seafloor, state.domain[0]) - 1);
  const si1 = Math.min(P.seafloor.length, d3.bisector(s => s[0]).right(P.seafloor, state.domain[1]) + 1);
  const seaA = P.seafloor.slice(si0, si1);
  aClip.append("path").attr("class", "seafloor")
    .attr("d", d3.area().x(s => x(s[0])).y0(yA0 + hA + 2).y1(s => yA(Math.min(s[1], BOAT_MAX_FT + 10)))(seaA));

  // Routine spans: submerged by day but times not logged
  P.unlogged.filter(r => inDom(r.t0, r.t1)).forEach(r => {
    const x0 = Math.max(M.left, x(r.t0)), x1 = Math.min(W - M.right, x(r.t1));
    aClip.append("rect").attr("class", "routine").attr("x", x0).attr("width", x1 - x0)
      .attr("y", yA(0)).attr("height", yA(PERISCOPE_FT) - yA(0));
    if (x1 - x0 > 230) aClip.append("text").attr("class", "routine-label").attr("x", x0 + 6).attr("y", yA(PERISCOPE_FT) + 14)
      .text("Submerged by day — times not logged");
  });

  aClip.append("line").attr("class", "test-depth").attr("x1", M.left).attr("x2", W - M.right)
    .attr("y1", yA(TEST_DEPTH_FT)).attr("y2", yA(TEST_DEPTH_FT));
  g.append("text").attr("class", "test-label").attr("x", W - M.right - 4).attr("y", yA(TEST_DEPTH_FT) - 5)
    .attr("text-anchor", "end").text("rated test depth 400 ft");

  aClip.append("path").attr("class", "profile")
    .attr("d", d3.line().x(p => x(p.t)).y(p => yA(p.d))(P.profile.filter((p, i, a) =>
      inDom(p.t, p.t) || inDom(a[i - 1]?.t ?? p.t, a[i + 1]?.t ?? p.t))));

  // Logged depth orders: dots, with labels on the deep ones (deepest first)
  const orders = P.events.filter(e => (e.event === "depth" || e.event === "bottom") && e.depth_ft && inDom(e.t, e.t));
  const labelMin = span > 10 * DAY ? 400 : span > 2 * DAY ? 300 : 0;
  const placed = [];
  orders.map(e => ({ e, px: x(e.t + Math.abs(e.depth_ft - depthAt(e.t - 1).d) / DESCENT_FT_PER_MIN * 60e3), py: yA(e.depth_ft) }))
    .sort((a, b) => b.e.depth_ft - a.e.depth_ft)
    .forEach(({ e, px, py }) => {
      aClip.append("circle").attr("class", "order").attr("cx", px).attr("cy", py).attr("r", 3.5);
      if (e.depth_ft >= labelMin && placed.every(([qx, qy]) => Math.abs(qx - px) > 40 || Math.abs(qy - py) > 22)) {
        aClip.append("text").attr("class", "order-label").attr("x", px).attr("y", py + 15).attr("text-anchor", "middle").text(`${e.depth_ft}`);
        placed.push([px, py]);
      }
    });

  // Depth charges / bombs, and the earthquake
  P.events.filter(e => inDom(e.t, e.t) && (e.charges || e.event === "charges" || e.event === "passing")).forEach(e => {
    const d = e.event === "passing" ? e.depth_ft : depthAt(e.t).d;
    aClip.append("path").attr("class", "charge").attr("transform", `translate(${x(e.t)},${yA(d)})`)
      .attr("d", d3.symbol(d3.symbolStar, Math.min(50 + 26 * Math.sqrt(e.charges ?? 1), 420))());
  });
  P.events.filter(e => inDom(e.t, e.t) && e.event === "quake").forEach(e => {
    aClip.append("path").attr("class", "note-mark").attr("transform", `translate(${x(e.t)},${yA(depthAt(e.t).d)})`)
      .attr("d", d3.symbol(d3.symbolDiamond, 90)());
  });

  // ── Weather strip: ERA5 wind (one axis: knots), cloud and rain, plus the captain's remarks ──
  g.append("text").attr("class", "panel-title").attr("x", M.left).attr("y", yW0 - 6).text("Weather at her position (ERA5)");
  const wIn = P.weather.filter(w => w.t >= state.domain[0] - 2 * HOUR && w.t <= state.domain[1] + 2 * HOUR);
  const cloudH = 10;
  const yWind = d3.scaleLinear().domain([0, Math.max(25, d3.max(P.weather, w => w.gust ?? 0))]).nice()
    .range([yW0 + hW, yW0 + cloudH + 4]);
  g.append("g").attr("class", "axis grid").attr("transform", `translate(${M.left},0)`)
    .call(d3.axisLeft(yWind).ticks(2).tickSize(-cw).tickFormat(d => d === 0 ? "0 kn" : `${d}`));
  const wClip = g.append("g").attr("clip-path", "url(#clipW)");
  const barW = Math.max(1, x(state.domain[0] + HOUR) - x(state.domain[0]));
  wIn.forEach(w => {
    if (w.cloud > 5) wClip.append("rect").attr("class", "cloud").attr("x", x(w.t) - barW / 2).attr("width", barW + 0.5)
      .attr("y", yW0).attr("height", cloudH).attr("opacity", w.cloud / 100);
    if (w.rain >= 0.5) wClip.append("rect").attr("class", "rain").attr("x", x(w.t) - 1).attr("width", 2)
      .attr("y", yW0 + 1).attr("height", Math.min(cloudH - 2, 2 + w.rain * 1.5));
  });
  wClip.append("path").attr("class", "wind-area")
    .attr("d", d3.area().x(w => x(w.t)).y0(yWind(0)).y1(w => yWind(w.wind)).defined(w => w.wind !== null)(wIn));
  wClip.append("path").attr("class", "gust").attr("d", d3.line().x(w => x(w.t)).y(w => yWind(w.gust)).defined(w => w.gust !== null)(wIn));
  if (span <= 4 * DAY) wIn.filter((w, i) => i % (span <= DAY ? 2 : 6) === 0 && w.wind >= 3).forEach(w =>
    wClip.append("path").attr("class", "wind-arrow")
      .attr("transform", `translate(${x(w.t)},${yWind(w.wind) - 7}) rotate(${w.dir + 180})`)
      .attr("d", "M0,-5 L3,2 L0,0.5 L-3,2 Z"));
  P.remarks.filter(e => inDom(e.t, e.t)).forEach(e =>
    wClip.append("path").attr("class", "remark").attr("d", d3.symbol(d3.symbolTriangle, 46)())
      .attr("transform", `translate(${x(e.t)},${yW0 + cloudH + 8}) rotate(180)`));

  // ── Panel B: seafloor ──
  g.append("text").attr("class", "panel-title").attr("x", M.left).attr("y", yB0 - 8).text("Water depth below her (feet)");
  g.append("g").attr("class", "axis grid").attr("transform", `translate(${M.left},0)`)
    .call(d3.axisLeft(yB).ticks(3).tickSize(-cw).tickFormat(d => d === 0 ? "surface" : d3.format(",")(d)));
  const bClip = g.append("g").attr("clip-path", "url(#clipB)");
  bClip.append("path").attr("class", "seafloor").attr("d", d3.area().x(s => x(s[0])).y0(yB0 + hB + 2).y1(s => yB(s[1]))(seaA));
  bClip.append("rect").attr("class", "bang-zone").attr("x", M.left).attr("width", cw)
    .attr("y", yB(0)).attr("height", Math.max(1.5, yB(BOAT_MAX_FT) - yB(0)));
  g.append("text").attr("class", "bang-zone-label").attr("x", W - M.right - 4).attr("y", yB(BOAT_MAX_FT) + 12)
    .attr("text-anchor", "end").text("▲ BANG's whole world: the top 650 ft");

  // Time axis on the logged clock
  const fmt = span > 6 * DAY ? d3.utcFormat("%-d %b") : span > 1.5 * DAY ? d3.utcFormat("%-d %b %H%M") : d3.utcFormat("%H%M");
  g.append("g").attr("class", "axis").attr("transform", `translate(0,${yAx})`)
    .call(d3.axisBottom(xl).ticks(Math.max(3, Math.floor(cw / 110))).tickFormat(fmt).tickSizeOuter(0));
  g.append("text").attr("class", "panel-sub").attr("x", W - M.right).attr("y", yAx + 32).attr("text-anchor", "end")
    .text(`Times in zone ${zone} (GMT${offset >= 0 ? "+" : ""}${offset / HOUR}), the clock the report used here`);

  // Playhead
  G.playhead = g.append("g").attr("class", "playhead").style("display", "none");
  G.playhead.append("line").attr("y1", yA0 - 14).attr("y2", yB0 + hB);
  G.playDot = G.playhead.append("circle").attr("r", 5);

  // Crosshair + hover layer
  const cross = g.append("g").style("display", "none");
  cross.append("line").attr("class", "crosshair").attr("y1", yA0 - 14).attr("y2", yB0 + hB);
  const dotA = cross.append("circle").attr("class", "cross-dot").attr("r", 4);
  const dotB = cross.append("circle").attr("class", "cross-dot").attr("r", 4);
  g.append("rect").attr("class", "hit").attr("x", M.left).attr("y", yA0 - 34)
    .attr("width", cw).attr("height", yB0 + hB - yA0 + 34)
    .on("pointermove", ev => {
      const [mx, my] = d3.pointer(ev);
      const near = nearestEvent(mx, my >= yW0 && my <= yW0 + hW ? P.remarks : P.events);
      const tt = near ? near.t : x.invert(mx).getTime();
      const d = depthAt(tt), sea = seafloorAt(tt);
      cross.style("display", null).attr("transform", `translate(${x(tt)},0)`);
      dotA.attr("cy", yA(d.d)); dotB.attr("cy", yB(sea));
      showTip(ev, hoverTip(tt, d, sea, near));
      if (!state.playing) { highlightRow(near); updateReadout(tt); }
    })
    .on("pointerleave", () => { cross.style("display", "none"); hideTip(); if (!state.playing) updateReadout(state.t ?? state.domain[0]); })
    .on("click", ev => {
      const [mx, my] = d3.pointer(ev);
      const near = nearestEvent(mx, my >= yW0 && my <= yW0 + hW ? P.remarks : P.events);
      if (near) openScan(near);
      else { state.t = x.invert(mx).getTime(); setPlayhead(state.t); }
    })
    .on("dblclick", () => setDomain([P.start, P.end]));
  setPlayhead(state.t);
}

// Logged event within 8 px of the pointer (snaps the crosshair to it)
function nearestEvent(mx, list) {
  let best = null, bestDx = 8;
  for (const e of list) {
    const dx = Math.abs(x(e.t) - mx);
    if (dx < bestDx) { best = e; bestDx = dx; }
  }
  return best;
}

// Overview strip with brush
let brush;
function drawOverview() {
  const { W, yOv, ovH } = G;
  const ov = svg.append("g").attr("class", "overview");
  const xo = d3.scaleUtc().domain([P.start, P.end]).range([M.left, W - M.right]);
  const yo = d3.scaleLinear().domain([0, BOAT_MAX_FT]).range([yOv, yOv + ovH]);
  ov.append("rect").attr("class", "frame").attr("x", M.left).attr("y", yOv).attr("width", W - M.left - M.right).attr("height", ovH);
  P.nights.forEach(([a, b]) => ov.append("rect").attr("class", "night").attr("x", xo(a)).attr("width", xo(b) - xo(a))
    .attr("y", yOv).attr("height", ovH));
  ov.append("path").attr("class", "profile").attr("d", d3.line().x(p => xo(p.t)).y(p => yo(p.d))(P.profile));
  P.events.filter(e => e.charges || e.event === "charges").forEach(e =>
    ov.append("path").attr("class", "charge").attr("transform", `translate(${xo(e.t)},${yo(depthAt(e.t).d)})`)
      .attr("d", d3.symbol(d3.symbolStar, 40)()));
  ov.append("line").attr("id", "strip-play").attr("class", "strip-play").attr("y1", yOv).attr("y2", yOv + ovH)
    .attr("x1", -10).attr("x2", -10);
  ov.append("text").attr("class", "panel-sub").attr("x", M.left).attr("y", yOv - 5)
    .text("Whole patrol — drag to choose the span shown above; double-click the chart to reset");
  brush = d3.brushX().extent([[M.left, yOv], [W - M.right, yOv + ovH]])
    .on("brush end", ev => {
      if (!ev.sourceEvent) return;
      if (!ev.selection) return setDomain([P.start, P.end]);
      setDomain(ev.selection.map(v => xo.invert(v).getTime()), true);
    });
  G.brushG = ov.append("g").attr("class", "brush").call(brush);
  G.xo = xo;
}

function moveBrush() {
  if (!G.brushG) return;
  const whole = state.domain[0] <= P.start && state.domain[1] >= P.end;
  G.brushG.call(brush.move, whole ? null : state.domain.map(G.xo));
}

// ── Day and night: one row per day on the report's clock ────────────────────
// Sun (day / twilight / night), moonlight (moon above the horizon, brighter the
// fuller it is), when BANG was submerged, and depth charges.
const DN = { left: 92, right: 14, top: 26, row: 12, gap: 2 };
let DNG = {};
function renderDayNight() {
  if (!P) return;
  const svgDN = d3.select("#daynight");
  const W = Math.max(500, document.querySelector(".daynight").getBoundingClientRect().width - 2);
  const zoneOf = t => ZONES[zoneAt(t)] * HOUR;
  // local days on the report's clock, first to last
  const first = d3.utcDay.floor(new Date(P.start + zoneOf(P.start))), last = d3.utcDay.floor(new Date(P.end + zoneOf(P.end)));
  const dayList = d3.utcDay.range(first, d3.utcDay.offset(last, 1));
  const H = DN.top + dayList.length * (DN.row + DN.gap) + 10;
  svgDN.attr("viewBox", `0 0 ${W} ${H}`).attr("height", H).selectAll("*").remove();
  const xh = d3.scaleLinear().domain([0, 24]).range([DN.left, W - DN.right]);
  svgDN.append("g").attr("class", "axis").attr("transform", `translate(0,${DN.top - 4})`)
    .call(d3.axisTop(xh).tickValues([0, 3, 6, 9, 12, 15, 18, 21, 24]).tickFormat(h => `${String(h % 24).padStart(2, "0")}00`).tickSizeOuter(0));
  const step = 15 * 60e3, cell = xh(step / HOUR) - xh(0);
  dayList.forEach((day, i) => {
    const y = DN.top + i * (DN.row + DN.gap);
    const off = zoneOf(+day + 12 * HOUR - zoneOf(+day));
    const t0 = +day - off;                      // local midnight in UTC ms
    const row = svgDN.append("g").attr("class", "dn-row").attr("transform", `translate(0,${y})`);
    row.append("text").attr("class", "dn-date").attr("x", DN.left - 22).attr("y", DN.row - 2).attr("text-anchor", "end")
      .text(d3.utcFormat("%-d %b")(day));
    const mg = row.append("g").attr("transform", `translate(${DN.left - 11},${DN.row / 2})`);
    drawMoon(mg, t0 + 12 * HOUR, 5);
    mg.append("title").text(`${moonName(t0 + 12 * HOUR)}, ${Math.round(moonLit(t0 + 12 * HOUR) * 100)}% lit`);
    // Sky: merge consecutive 15-min cells of the same state into one rect
    let runStart = 0, runCls = null, runOp = 0;
    const flush = (k) => {
      if (runCls && k > runStart) row.append("rect").attr("class", runCls).attr("x", xh(runStart * 0.25)).attr("width", (k - runStart) * cell + 0.3)
        .attr("y", 0).attr("height", DN.row).attr("opacity", runOp || null);
    };
    for (let k = 0; k <= 96; k++) {
      const t = t0 + k * step;
      let cls = null, op = 0;
      if (k < 96 && t >= P.start && t <= P.end) {
        const [lon, lat] = positionAt(t);
        const s = sunAltitude(t, lon, lat);
        if (s > -0.833) cls = "sky-day";
        else if (s > -6) cls = "sky-twilight";
        else {
          const m = moonAltitude(t, lon, lat);
          if (m > 0) { cls = "sky-moon"; op = Math.round((0.25 + 0.75 * moonLit(t)) * 4) / 4; }
          else cls = "sky-night";
        }
      }
      if (cls !== runCls || op !== runOp) { flush(k); runStart = k; runCls = cls; runOp = op; }
    }
    // Submerged (from the depth profile)
    const pts = P.profile;
    for (let j = 0; j < pts.length - 1; j++) {
      const a = Math.max(pts[j].t, t0), b = Math.min(pts[j + 1].t, t0 + DAY);
      if (b > a && pts[j].d > 0 && pts[j + 1].d > 0)
        row.append("rect").attr("class", "dn-sub").attr("x", xh((a - t0) / HOUR)).attr("width", Math.max(1, xh((b - t0) / HOUR) - xh((a - t0) / HOUR)))
          .attr("y", DN.row * 0.3).attr("height", DN.row * 0.4);
    }
    P.unlogged.filter(r => r.t1 > t0 && r.t0 < t0 + DAY).forEach(r => {
      const a = Math.max(r.t0, t0), b = Math.min(r.t1, t0 + DAY);
      row.append("rect").attr("class", "dn-unlogged").attr("x", xh((a - t0) / HOUR)).attr("width", xh((b - t0) / HOUR) - xh((a - t0) / HOUR))
        .attr("y", DN.row * 0.3).attr("height", DN.row * 0.4);
    });
    P.events.filter(e => e.t >= t0 && e.t < t0 + DAY && (e.charges || e.event === "charges" || e.event === "quake")).forEach(e =>
      row.append("path").attr("class", e.event === "quake" ? "note-mark" : "charge")
        .attr("transform", `translate(${xh((e.t - t0) / HOUR)},${DN.row / 2})`)
        .attr("d", d3.symbol(e.event === "quake" ? d3.symbolDiamond : d3.symbolStar, e.event === "quake" ? 40 : Math.min(30 + 10 * Math.sqrt(e.charges ?? 1), 140))()));
    row.append("rect").attr("class", "dn-hit").attr("x", DN.left).attr("width", W - DN.left - DN.right).attr("height", DN.row + DN.gap)
      .on("pointermove", ev => {
        const t = t0 + xh.invert(d3.pointer(ev)[0]) * HOUR;
        showTip(ev, dayNightTip(t));
      })
      .on("pointerleave", hideTip)
      .on("click", ev => {
        const t = t0 + xh.invert(d3.pointer(ev)[0]) * HOUR;
        stop(); state.t = t;
        setDomain([t - 12 * HOUR, t + 12 * HOUR]);
        document.querySelector(".chart-card").scrollIntoView({ behavior: "smooth", block: "start" });
      });
  });
  // The captains' own sky notes, ringed
  P.sky.forEach(n => {
    const local = n.t + zoneOf(n.t), i = Math.floor((local - +first) / DAY);
    const h = (local - +d3.utcDay.floor(new Date(local))) / HOUR;
    svgDN.append("circle").attr("class", "dn-sky").attr("cx", xh(h)).attr("cy", DN.top + i * (DN.row + DN.gap) + DN.row / 2).attr("r", 6)
      .append("title").text(`Report: "${n.quote}"`);
  });
  renderSkyNotes();
  DNG = { svg: svgDN, xh, first: +first, zoneOf };
  DNG.cursor = svgDN.append("g").attr("class", "dn-cursor").style("display", "none");
  DNG.cursor.append("rect").attr("x", DN.left - 2).attr("width", W - DN.left - DN.right + 4).attr("height", DN.row + 2).attr("y", -1);
  DNG.cursor.append("line").attr("y1", -3).attr("y2", DN.row + 3);
  dayNightCursor(state.t);
}

// Compare each sky note with the computed moon for that night
function renderSkyNotes() {
  const box = document.getElementById("sky-notes");
  box.replaceChildren();
  if (!P.sky.length) { box.hidden = true; return; }
  box.hidden = false;
  box.append(el("div", "sky-head", "Checking the sky against the captain's log"));
  P.sky.forEach(n => {
    const [lon, lat] = positionAt(n.t);
    const events = [];
    let prev = null;
    for (let t = n.t - 6 * HOUR; t < n.t + 14 * HOUR; t += 60e3) {
      const [lo, la] = positionAt(t);
      const up = moonAltitude(t, lo, la) > 0;
      if (prev !== null && up !== prev) events.push(`moon${up ? "rise" : "set"} ${fmtLocal(t).slice(-6)}`);
      prev = up;
    }
    const up = moonAltitude(n.t, lon, lat) > 0;
    const calc = `${moonName(n.t)}, ${Math.round(moonLit(n.t) * 100)}% lit, ${up ? "up" : "down"} at ${fmtLocal(n.t).slice(-6)}`
      + (events.length ? ` · ${events.slice(0, 2).join(", ")}` : "");
    const row = el("div", "sky-row");
    const g = d3.create("svg").attr("width", 18).attr("height", 18);
    drawMoon(g.append("g").attr("transform", "translate(9,9)"), n.t, 7.5);
    const body = el("div");
    const pg = el("a", null, `p. ${parseInt(n.page.split("/p")[1], 10)} ↗`);
    pg.href = "#";
    pg.addEventListener("click", ev => { ev.preventDefault(); openScan({ ...n, event: "sky" }); });
    const q = el("div", null, `${localWhen(n)} — “${n.quote}” `);
    q.append(pg);
    body.append(q, el("div", "sky-calc", `This page computes: ${calc}`));
    row.append(g.node(), body);
    box.append(row);
  });
}

function dayNightCursor(t) {
  if (!DNG.cursor) return;
  if (t === null || t === undefined) return DNG.cursor.style("display", "none");
  const local = t + DNG.zoneOf(t);
  const i = Math.floor((local - DNG.first) / DAY);
  const h = (local - d3.utcDay.floor(new Date(local))) / HOUR;
  DNG.cursor.style("display", null).attr("transform", `translate(0,${DN.top + i * (DN.row + DN.gap)})`);
  DNG.cursor.select("line").attr("x1", DNG.xh(h)).attr("x2", DNG.xh(h));
}

function dayNightTip(t) {
  const [lon, lat] = positionAt(t);
  const s = sunAltitude(t, lon, lat), m = moonAltitude(t, lon, lat), d = depthAt(t);
  const f = document.createDocumentFragment();
  f.append(el("div", "v", fmtLocal(t)));
  f.append(el("div", "k", `${s > -0.833 ? "Daylight" : s > -6 ? "Twilight" : m > 0 ? "Night, moon up" : "Night, moon down"} · ${moonName(t)}, ${Math.round(moonLit(t) * 100)}% lit`));
  f.append(el("div", "k", d.d < 1 ? "BANG on the surface" : `BANG at ${Math.round(d.d)} ft`));
  f.append(el("div", "m", "Click to open this moment in the dive profile"));
  return f;
}

// ── Side panel: the depth log (the chart's table view) ──────────────────────
function renderSide() {
  const list = document.getElementById("list");
  list.replaceChildren();
  document.getElementById("side-title").textContent = `Patrol ${P.n} depth log`;
  const rows = P.events.filter(e => state.filter === "all" || !["dive", "surface", "periscope"].includes(e.event));
  rows.forEach(e => {
    const row = el("div", "row");
    row.dataset.t = e.t;
    row.tabIndex = 0;
    row.append(iconFor(e));
    const body = el("div");
    const what = el("div", "what", LABEL[e.event]);
    if (e.depth_ft) what.append(el("span", "badge", `${e.depth_ft} ft`));
    if (e.charges) what.append(el("span", "badge", `${e.charges} ${P.n === 6 ? "bombs" : "charges"}`));
    body.append(el("div", "when", localWhen(e)), what, el("div", "note", e.quote));
    if (e.context) body.append(el("div", "context", e.context));
    const links = el("div");
    const pg = el("a", null, `Report page ${parseInt(e.page.split("/p")[1], 10)} ↗`);
    pg.href = "#";
    pg.addEventListener("click", ev => { ev.preventDefault(); ev.stopPropagation(); openScan(e); });
    const mp = el("a", null, "On the map ↗");
    mp.href = `patrols.html?patrol=${P.n}&t=${e.utc}`;
    mp.addEventListener("click", ev => ev.stopPropagation());
    links.append(pg, mp);
    body.append(links);
    row.append(body);
    const go = () => { stop(); state.t = e.t; setDomain([e.t - 6 * HOUR, e.t + 6 * HOUR]); };
    row.addEventListener("click", go);
    row.addEventListener("keydown", ev => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); go(); } });
    list.append(row);
  });
}

function highlightRow(e, scroll = true) {
  document.querySelectorAll("#list .row.current").forEach(r => r.classList.remove("current"));
  if (!e) return;
  const row = document.querySelector(`#list .row[data-t="${e.t}"]`);
  if (!row) return;
  row.classList.add("current");
  const list = document.getElementById("list");
  if (row.offsetTop < list.scrollTop || row.offsetTop > list.scrollTop + list.clientHeight - row.offsetHeight)
    list.scrollTop = row.offsetTop - list.clientHeight / 3;
}

// ── Stats & legend ──────────────────────────────────────────────────────────
function renderStats() {
  const box = document.getElementById("stats");
  box.replaceChildren();
  const tile = (label, value, sub) => {
    const t = el("div", "tile");
    t.append(el("div", "label", label), el("div", "value", value));
    if (sub) t.append(el("div", "sub", sub));
    box.append(t);
  };
  const meta = PATROLS.find(p => p.n === P.n);
  tile(meta.name, meta.dates);
  const deep = d3.greatest(P.events.filter(e => e.depth_ft), e => e.depth_ft);
  tile("Deepest logged", deep ? `${deep.depth_ft} ft` : "—",
       deep ? `${fmtDay(deep.local.slice(0, 10))} · seafloor ${d3.format(",")(Math.round(seafloorAt(deep.t) / 10) * 10)} ft below` : "");
  const charges = d3.sum(P.events, e => e.charges ?? 0);
  tile(P.n === 6 ? "Bombs dropped on her" : "Depth charges counted", d3.format(",")(charges),
       charges ? "as tallied in the report" : "none aimed at her");
  const strongest = d3.greatest(P.layers.filter(l => l.iso_deg && l.grad_deg && l.grad_ft > (l.iso_ft ?? 0)), l => l.iso_deg - l.grad_deg);
  tile("Strongest temperature layer", strongest ? `${strongest.iso_deg}° → ${strongest.grad_deg}°F` : "—",
       strongest ? `${fmtDay(strongest.utc.slice(0, 10))} · from ${strongest.iso_ft ?? 0} to ${strongest.grad_ft} ft` : "no layer recorded");
  const windiest = d3.greatest(P.weather, w => w.gust ?? 0);
  tile("Windiest (ERA5)", windiest ? `${Math.round(windiest.wind)} kn, gusts ${Math.round(windiest.gust)}` : "—",
       windiest ? fmtLocal(windiest.t).slice(0, 11) : "");
}

function renderLegend() {
  const lg = document.getElementById("legend");
  lg.replaceChildren();
  const item = (draw, text) => {
    const s = el("span");
    const v = d3.create("svg").attr("width", 22).attr("height", 14);
    draw(v.append("g").attr("transform", "translate(11,7)"));
    s.append(v.node(), document.createTextNode(text));
    lg.append(s);
  };
  const swatch = (fill, stroke = "var(--border)") => g => g.append("rect").attr("x", -9).attr("y", -6).attr("width", 18).attr("height", 12)
    .attr("fill", fill).attr("stroke", stroke);
  item(g => g.append("line").attr("x1", -10).attr("x2", 10).attr("stroke", "var(--series-track)").attr("stroke-width", 2), "BANG's depth");
  item(g => g.append("circle").attr("r", 3.5).attr("fill", "var(--series-track)"), "Depth ordered");
  item(g => g.append("path").attr("d", d3.symbol(d3.symbolStar, 70)()).attr("fill", "var(--series-attack)"),
       P.n === 6 ? "Bombs (size = number)" : "Depth charges (size = number)");
  item(g => { g.append("rect").attr("x", -9).attr("y", -6).attr("width", 18).attr("height", 12).attr("fill", "url(#layer-grad)");
              g.append("line").attr("x1", -9).attr("x2", 9).attr("y1", -6).attr("y2", -6).attr("class", "layer-top"); },
       "Temperature layer (report)");
  item(g => g.append("line").attr("x1", -10).attr("x2", 10).attr("stroke", "var(--text-muted)").attr("stroke-dasharray", "4 3"), "Test depth");
  item(swatch("var(--seafloor)", "var(--seafloor-edge)"), "Seafloor");
  item(swatch("var(--night)"), "Night");
  item(g => g.append("path").attr("d", "M-9,5 L-4,0 L1,2 L9,-5 L9,6 L-9,6 Z").attr("class", "wind-area"), "Wind (ERA5)");
  item(g => g.append("path").attr("d", d3.symbol(d3.symbolTriangle, 46)()).attr("transform", "rotate(180)").attr("class", "remark"), "Captain's weather note");
  if (P.unlogged.length) item(swatch("url(#hatch)"), "Submerged, times not logged");
}

// ── Tooltip, scan viewer, links ─────────────────────────────────────────────
function hoverTip(t, d, sea, e) {
  const f = document.createDocumentFragment();
  const [lon, lat] = positionAt(t);
  const s = sunAltitude(t, lon, lat);
  const assumed = !e && d.src && ["dive", "periscope"].includes(d.src.event);
  const w = weatherAt(t), l = layerAt(t);
  const note = d.src?.assumed === "dark" ? " (assumed surfaced after dark; no surfacing logged)"
    : d.src?.assumed === "routine" ? " (assumed: daily dive, times not logged)" : assumed ? " (periscope depth assumed)" : "";
  f.append(el("div", "v", (d.d < 1 ? "On the surface" : `${Math.round(d.d)} ft`) + note));
  f.append(el("div", "k", `${fmtLocal(t)} · ${s > -0.833 ? "day" : s > -6 ? "twilight" : "night"} · ${moonName(t)} (${Math.round(moonLit(t) * 100)}%)`));
  f.append(el("div", "k", `Seafloor ${d3.format(",")(Math.round(sea / 10) * 10)} ft below the surface (${d3.format(",")(Math.round(sea / FT_PER_M))} m)`));
  if (l) f.append(el("div", "k", `Layer: ${layerText(l, true)}`));
  if (w) f.append(el("div", "k", `ERA5: wind ${Math.round(w.wind)} kn from ${compass(w.dir)} (gusts ${Math.round(w.gust)}), cloud ${Math.round(w.cloud)}%, ${Math.round(w.temp * 9 / 5 + 32)}°F air, ${Math.round(w.pres)} hPa`));
  if (e) {
    f.append(el("div", null, `${localWhen(e)} — ${e.quote}`));
    if (e.context) f.append(el("div", "i", e.context));
    f.append(el("div", "m", `Click to read report page ${parseInt(e.page.split("/p")[1], 10)}`));
  }
  return f;
}
function showTip(ev, content) { tip.replaceChildren(content); tip.style.display = "block"; moveTip(ev); }
function moveTip(ev) {
  const r = tip.getBoundingClientRect();
  const xx = ev.clientX + 14 + r.width > innerWidth ? ev.clientX - r.width - 14 : ev.clientX + 14;
  const yy = ev.clientY + 14 + r.height > innerHeight ? ev.clientY - r.height - 14 : ev.clientY + 14;
  tip.style.left = `${xx}px`; tip.style.top = `${yy}px`;
}
function hideTip() { tip.style.display = "none"; }

function openScan(e) {
  const [folder, page] = e.page.split("/");
  const n = parseInt(page.slice(1), 10);
  document.getElementById("scan-title").textContent = `${LABEL[e.event] ?? "Report"}, ${localWhen(e)} · report page ${n}`;
  const img = document.getElementById("scan-img");
  img.classList.remove("full");
  setScanSrc(img, folder, page);
  img.alt = `Scan of patrol report page ${n}`;
  document.getElementById("scan-link").href = `https://catalog.archives.gov/id/${folder.replace("rg367-", "")}?objectPage=${n}`;
  hideTip();
  stop();
  document.getElementById("scan").showModal();
}

function updateMapLink() {
  const t = state.t ?? (state.domain[0] + state.domain[1]) / 2;
  document.getElementById("to-map").href = `patrols.html?patrol=${P.n}&t=${new Date(t).toISOString().slice(0, 16)}Z`;
}

// ── Helpers ─────────────────────────────────────────────────────────────────
// Scans live in the cache's nara/ folder when downloaded (tools/nara.py fetch); otherwise
// load the same page from the National Archives (records/scans.json lists its URL).
// If the archive's copy won't load either, the page's catalog link stands in for it.
let SCANS = null;
function setScanSrc(img, folder, page) {
  const key = `${folder}/${page}`, missing = document.getElementById("scan-missing");
  const fail = () => {
    img.hidden = true; missing.hidden = false;
    const src = document.getElementById("scan-link");
    missing.replaceChildren(Object.assign(el("a", null, src.textContent), { href: src.href, target: "_blank", rel: "noopener" }));
  };
  img.hidden = false; missing.hidden = true;
  img.onerror = async () => {
    SCANS ??= await fetch(RECORDS + "scans.json").then(r => r.json()).catch(() => ({}));
    if (SCANS[key]) { img.onerror = fail; img.src = SCANS[key]; } else fail();
  };
  img.src = `${CACHE}nara/${key}.jpg`;
}

function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}
function drawMoon(g, t, r) {
  g.append("circle").attr("class", "moon-dark").attr("r", r);
  const { d, mirror } = moonPath(t, r);
  g.append("path").attr("class", "moon-lit").attr("d", d).attr("transform", mirror ? "scale(-1,1)" : null);
  g.append("circle").attr("class", "moon-rim").attr("r", r);
}
function layerText(l, long = false) {
  const parts = [];
  if (l.iso_ft) parts.push(`${l.iso_deg ?? "?"}°F to ${l.iso_ft} ft`);
  else if (l.iso_deg) parts.push(`${l.iso_deg}°F at surface`);
  if (l.grad_ft && l.grad_deg) parts.push(`cooling to ${l.grad_deg}°F at ${l.grad_ft} ft`);
  return parts.join(", ") + (long && l.note ? ` (${l.note})` : "");
}
const compass = deg => deg === null || deg === undefined ? "" : ["N", "NE", "E", "SE", "S", "SW", "W", "NW"][Math.round(deg / 45) % 8];
const fmtDay = iso => d3.utcFormat("%-d %b %Y")(new Date(`${iso}T00:00Z`));
const fmtLocal = t => { const z = zoneAt(t); return `${d3.utcFormat("%-d %b %Y · %H%M")(new Date(t + ZONES[z] * HOUR))} ${z}`; };
function localWhen(e) {
  const m = /^(\d{4}-\d{2}-\d{2}) (\d{4})\((\w+)\)$/.exec(e.local);
  return m ? `${fmtDay(m[1])} · ${m[2]} ${m[3] === "Z" ? "GCT" : m[3]}` : e.utc;
}
function iconFor(e) {
  const v = d3.create("svg").attr("width", 16).attr("height", 16);
  const g = v.append("g").attr("transform", "translate(8,8)");
  if (e.charges || e.event === "charges") g.append("path").attr("d", d3.symbol(d3.symbolStar, 60)()).attr("fill", "var(--series-attack)");
  else if (e.event === "quake") g.append("path").attr("d", d3.symbol(d3.symbolDiamond, 50)()).attr("fill", "var(--text-primary)");
  else if (e.event === "surface") g.append("path").attr("d", "M-5,3 L0,-4 L5,3").attr("fill", "none").attr("stroke", "var(--text-secondary)").attr("stroke-width", 1.5);
  else if (["dive", "periscope", "radar_depth"].includes(e.event)) g.append("path").attr("d", "M-5,-3 L0,4 L5,-3").attr("fill", "none").attr("stroke", "var(--text-secondary)").attr("stroke-width", 1.5);
  else g.append("circle").attr("r", 4).attr("fill", "var(--series-track)");
  return v.node();
}
