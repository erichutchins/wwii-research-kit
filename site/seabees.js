// Seabee battalions in the Pacific: where a naval construction battalion, and each part of it, was.
// Renders records/seabees/seabees.json, which tools/build_seabees.py builds from the hand-transcribed
// CSVs in records/seabees/ (stations, parts, places, voyages and the ships' logged positions, and the
// day's weather from tools/fetch_station_weather.py).

const DAY = 864e5;
const DAYS_PER_SECOND = 20;    // playback speed
const KM_PER_DAY = 550;        // pace of a moving marker between stations (a transport, ~12 knots)
const HIT_PX = 14;             // hover radius around a station (24px+ target)
const R = 5;                   // station marker radius (10px)

// Labels for the seas and lands, and the views the region buttons jump to ([west, south], [east, north]);
// a battalion gets the buttons for the regions its stations are in.
const SEAS = [
  { name: "PACIFIC OCEAN", lon: -150, lat: 15 }, { name: "CORAL SEA", lon: 154, lat: -16 },
  { name: "SOLOMON SEA", lon: 154, lat: -8.4 }, { name: "PHILIPPINE SEA", lon: 133, lat: 20 },
  { name: "UNITED STATES", lon: -100, lat: 39 }, { name: "AUSTRALIA", lon: 140, lat: -25 },
  { name: "NEW GUINEA", lon: 144, lat: -6 },
];
const REGIONS = [
  ["Solomons", [[155.5, -23.5], [167.5, -7.5]]],
  ["New Guinea", [[145.5, -20], [155.5, -5]]],
  ["New Georgia", [[157.0, -8.9], [158.2, -8.1]]],
  ["Russells", [[158.9, -9.6], [160.3, -8.9]]],
  ["Marianas to Okinawa", [[123, 12], [150, 30]]],
  ["US", [[-124, 33], [-69, 43]]],
];

const state = { unit: null, t: null, playing: false, k: 1 };
let DATA, U, LAND50, LAND10, proj, path, zoom, g;

const svg = d3.select("#map");
const tip = document.getElementById("tip");
const fmtDay = d3.utcFormat("%-d %b %Y");
const parseDay = s => Date.parse(`${s}T12:00Z`);
const shortName = name => name.replace("Naval Construction Battalion", "NCB");

// ── Data ────────────────────────────────────────────────────────────────────
Promise.all([
  d3.json(RECORDS + "seabees/seabees.json"),
  d3.json("https://cdn.jsdelivr.net/npm/world-atlas@2/land-50m.json"),
]).then(([data, land]) => {
  LAND50 = topojson.feature(land, land.objects.land);
  DATA = data;
  DATA.rows.forEach(r => Object.assign(r, prepareRow(r)));
  data.voyages.forEach(v => {
    v.pts = v.positions.filter(q => q.on_track).map(q => ({ ...q, t: Date.parse(q.utc), lonlat: [q.lon, q.lat] }));
    (DATA.rows[v.to_id].arrivals ??= []).push(v);
  });
  buildControls();
  new ResizeObserver(() => render()).observe(document.querySelector(".map-wrap"));
  new ResizeObserver(() => { if (U) { drawStrip(); setTime(state.t); } }).observe(document.getElementById("strip"));
  // deep link: seabees.html?unit=20ncb&t=1943-07-01
  const q = new URLSearchParams(location.search);
  select(DATA.units[q.get("unit")] ? q.get("unit") : Object.keys(DATA.units)[0], { keepUrl: true });
  if (q.get("t")) setTime(parseDay(q.get("t")));
});

// What a station assumes, said in words (tooltips and the list)
function prepareRow(r) {
  const presumed = [];
  if (r.assumed === "place") presumed.push("Position assumed: the record names an island, a mail address or several places; the note says where it's drawn");
  if (r.assumed === "date") presumed.push("Date approximate: the source gives only the month, or the day of a transfer rather than an arrival; the note says which");
  if (r.assumed === "part") presumed.push("Which part of the battalion this was is assumed; the note says why");
  return { t: parseDay(r.date), lonlat: r.lat === null ? null : [r.lon, r.lat], unitName: DATA.units[r.unit]?.name ?? r.unit,
           presumed, hollow: r.assumed === "place" };
}

// One battalion: its rows, and a line per part (records/seabees/parts.csv), each with keyframes for
// its moving marker and the legs it draws.
function prepareUnit(unit) {
  const rows = DATA.rows.filter(r => r.unit === unit);
  const voyageFor = (a, b) => DATA.voyages.find(v => v.from_id === a.id && v.to_id === b.id);
  const legs = new Map();
  const lines = DATA.parts.filter(p => p.unit === unit).map(p => {
    const pts = p.ids.map(i => DATA.rows[i]);
    // keyframes hold at a station, then move at a steady pace to arrive on the next one's date;
    // along a logged voyage, the marker passes each logged position at its time
    const keys = [];
    pts.forEach((a, j) => {
      const b = pts[j + 1];
      keys.push({ t: a.t, at: a.lonlat, row: a });
      if (!b) return;
      const v = voyageFor(a, b);
      if (a.place !== b.place) {
        const key = `${a.id}-${b.id}`;
        if (!legs.has(key)) legs.set(key, { a, b, voyage: v, logged: !!(v && v.pts.length), assumed: a.hollow || b.hollow,
                                            coords: [a.lonlat, ...(v && v.pts.length ? v.pts.map(q => q.lonlat) : []), b.lonlat] });
      }
      if (v && v.pts.length) {
        v.pts.forEach(q => keys.push({ t: q.t, at: q.lonlat, row: a, to: b, voyage: v }));
        return;
      }
      const travel = Math.max(d3.geoDistance(a.lonlat, b.lonlat) * 6371 / KM_PER_DAY, 1) * DAY;
      // A stay that ends on a recorded departure (last_day) is left the day after. If the next
      // station is much further off than the voyage takes, where the part was in between isn't
      // recorded (the Rear Echelon while its groups were in New Georgia): no marker until it arrives.
      if (a.last_day && b.t - (a.t + DAY) > travel + 2 * DAY) {
        keys.push({ t: a.t + DAY, at: null, row: a, to: b });
        return;
      }
      const leave = a.last_day ? Math.min(a.t + DAY, b.t) : b.t - travel;
      keys.push({ t: Math.max(a.t, leave), at: a.lonlat, row: a, to: b, voyage: v });
    });
    keys.sort((x, y) => x.t - y.t);
    return { ...p, pts, keys, label: p.part === "battalion" ? shortName(DATA.units[unit].name) : p.part };
  });
  // When each line's marker shows: a part while it existed; a run of the battalion's own line from
  // its first station until the next split (or for good, after the last one)
  const splits = lines.filter(l => l.parent === "battalion").map(l => parseDay(l.from));
  lines.forEach(l => {
    if (l.part !== "battalion") { l.t0 = parseDay(l.from); l.t1 = parseDay(l.to); return; }
    l.t0 = l.pts[0].t;
    l.t1 = d3.min(splits.filter(s => s > l.pts.at(-1).t - DAY)) ?? Infinity;
  });
  // timeline rows: each line in the first row free at its start, so parts on record together each
  // get a row (the battalion's own runs, which never overlap its parts, stay on the first)
  const ends = [];
  lines.slice().sort((a, b) => a.t0 - b.t0 || (a.part === "battalion" ? -1 : 1)).forEach(l => {
    l.level = ends.findIndex(e => e <= l.t0);
    if (l.level < 0) l.level = ends.length;
    ends[l.level] = l.t1;
  });
  const t0 = d3.min(rows, r => r.t) - 7 * DAY, t1 = d3.max(rows, r => r.t) + 7 * DAY;
  const placed = rows.filter(r => r.lonlat);
  const km = d3.sum([...legs.values()], l => d3.sum(l.coords.slice(1), (c, j) => d3.geoDistance(l.coords[j], c)) * 6371);
  return { unit, name: DATA.units[unit].name, note: DATA.units[unit].note, rows, placed, lines, legs: [...legs.values()],
           km, t0, t1, voyages: DATA.voyages.filter(v => v.unit === unit) };
}

// ── Controls ───────────────────────────────────────────────────────────────
function buildControls() {
  const pick = document.getElementById("unit-pick");
  Object.entries(DATA.units).forEach(([id, u]) => {
    const years = d3.extent(DATA.rows.filter(r => r.unit === id), r => r.date.slice(0, 4));
    pick.append(Object.assign(el("option", null, `${u.name} (${years[0]}${years[1] !== years[0] ? `–${years[1]}` : ""})`), { value: id }));
  });
  pick.addEventListener("change", () => select(pick.value));
  document.getElementById("play").addEventListener("click", togglePlay);
  document.getElementById("scrub").addEventListener("input", e => {
    stop(); setTime(U.t0 + (U.t1 - U.t0) * (+e.target.value / 1000));
  });
  document.getElementById("zin").addEventListener("click", () => svg.transition().call(zoom.scaleBy, 2));
  document.getElementById("zout").addEventListener("click", () => svg.transition().call(zoom.scaleBy, 0.5));
  document.getElementById("zreset").addEventListener("click", () => svg.transition().duration(600).call(zoom.transform, d3.zoomIdentity));
  document.getElementById("scan-close").addEventListener("click", () => document.getElementById("scan").close());
  document.getElementById("scan-img").addEventListener("click", e => e.target.classList.toggle("full"));
}

function select(unit, { keepUrl = false } = {}) {
  stop();
  state.unit = unit;
  U = prepareUnit(unit);
  state.t = U.t1;
  document.getElementById("unit-pick").value = unit;
  if (!keepUrl) history.replaceState(null, "", `?unit=${unit}`);
  const regions = d3.select("#regions").html("");
  [["Whole war", null], ...REGIONS.filter(([, b]) => U.placed.some(r => inBox(r.lonlat, b)))]
    .forEach(([name, box]) => regions.append("button").text(name).on("click", () => fitBox(box)));
  renderStats();
  renderLegend();
  renderSide();
  drawStrip();
  render();
}
const inBox = ([lon, lat], [[w, s], [e, n]]) => lon >= w && lon <= e && lat >= s && lat <= n;

// ── Map ────────────────────────────────────────────────────────────────────
function render() {
  if (!U) return;
  const wrap = document.querySelector(".map-wrap").getBoundingClientRect();
  const W = wrap.width, H = wrap.height;
  if (!W || !H) return;
  svg.attr("viewBox", `0 0 ${W} ${H}`).selectAll("*").remove();
  // Mercator centred on 160°W, so the Pacific is whole and the United States and Okinawa both fit;
  // fitted to the legs, not only the stations: a long leg's great circle bows north of both ends
  proj = d3.geoMercator().rotate([160, 0]).fitExtent([[40, 70], [W - 90, H - 40]],
    { type: "FeatureCollection", features: U.legs.map(l => ({ type: "Feature", geometry:
      { type: "LineString", coordinates: [l.a.lonlat, l.b.lonlat] } })) });
  path = d3.geoPath(proj);
  g = svg.append("g");
  g.append("path").attr("class", "graticule").attr("d", path(d3.geoGraticule().step([10, 10])()));
  g.append("path").attr("class", "land").attr("d", path(LAND10 && LAND10 !== "loading" ? LAND10 : LAND50));
  g.append("g").selectAll("text").data(SEAS).join("text").attr("class", "sea-label")
    .attr("text-anchor", "middle").attr("transform", d => `translate(${proj([d.lon, d.lat])})`).text(d => d.name);
  g.append("g").selectAll("path").data(U.legs).join("path")
    .attr("class", d => `leg${d.assumed ? " assumed" : ""}`)
    .attr("d", d => path({ type: "LineString", coordinates: d.coords }))
    .append("title").text(d => d.voyage ? `${d.voyage.ships || "Ship not recorded"} · ${d.a.place} to ${d.b.place}${d.logged ? " (the ship's logged positions)" : ""}` : `${d.a.place} to ${d.b.place}`);
  g.append("g").attr("class", "labels");
  const mks = g.append("g").selectAll("g").data(U.placed).join("g")
    .attr("class", d => `mk${d.hollow ? " assumed" : ""}`)
    .attr("transform", d => `translate(${proj(d.lonlat)})`);
  mks.append("circle").attr("class", "ring");
  mks.append("circle").attr("class", "shape");
  g.append("g").attr("class", "who-g");
  zoom = d3.zoom().scaleExtent([1, 600]).on("zoom", ev => {
    g.attr("transform", ev.transform);
    state.k = ev.transform.k;
    rescale();
    if (state.k > 6 && !LAND10) loadDetail();
  }).on("end", placeLabels);
  svg.call(zoom).on("dblclick.zoom", null);
  svg.call(zoom.transform, d3.zoomIdentity);
  svg.on("pointermove", onHover).on("pointerleave", () => { hideTip(); setHover(null); })
     .on("click", ev => { const d = nearest(ev); if (d) openSource(d.links[0], d); });
  rescale();
  placeLabels();
  setTime(state.t);
}

// The 1:10m coastlines, once zoomed in far enough to see New Georgia's islands
function loadDetail() {
  LAND10 = "loading";
  d3.json("https://cdn.jsdelivr.net/npm/world-atlas@2/land-10m.json").then(land => {
    LAND10 = topojson.feature(land, land.objects.land);
    g?.select(".land").attr("d", path(LAND10));
  });
}

function rescale() {
  const k = state.k;
  g.selectAll(".mk .ring").attr("r", (R + 2) / k);
  g.selectAll(".mk .shape").attr("r", d => (d.hollow ? R - 1 : R) / k);
  g.selectAll(".sea-label").style("font-size", `${12 / k}px`).attr("display", k > 12 ? "none" : null);
  g.selectAll(".place-label").style("font-size", `${12 / k}px`).style("stroke-width", `${3 / k}px`);
  drawWho();
}

// Every place the battalion was, the most visited first; a label that would overlap one already
// placed is hidden.
function placeLabels() {
  if (!g) return;
  const k = state.k, tr = d3.zoomTransform(svg.node());
  const visits = d3.rollup(U.placed, v => v.length, r => r.place);
  const places = [...new Map(U.placed.map(r => [r.place, r])).values()]
    .sort((a, b) => visits.get(b.place) - visits.get(a.place));
  const boxes = [];
  const shown = places.filter(r => {
    const [x, y] = tr.apply(proj(r.lonlat));
    const w = r.place.length * 6.4 + 4, box = [x + 8, y - 8, x + 8 + w, y + 6];
    if (boxes.some(b => box[0] < b[2] && box[2] > b[0] && box[1] < b[3] && box[3] > b[1])) return false;
    boxes.push(box, [x - 7, y - 7, x + 7, y + 7]);
    return true;
  });
  g.select(".labels").selectAll("text").data(shown, d => d.place).join("text").attr("class", "place-label")
    .attr("transform", d => `translate(${proj(d.lonlat)})`).attr("x", 8 / k).attr("dy", "0.35em")
    .style("font-size", `${12 / k}px`).style("stroke-width", `${3 / k}px`).text(d => d.place);
}

function fitBox(box) {
  const wrap = document.querySelector(".map-wrap").getBoundingClientRect();
  if (!box) return svg.transition().duration(700).call(zoom.transform, d3.zoomIdentity);
  const [[x0, y1], [x1, y0]] = [proj(box[0]), proj(box[1])];
  const k = Math.min(600, 0.9 * Math.min(wrap.width / (x1 - x0), wrap.height / (y1 - y0)));
  svg.transition().duration(900).call(zoom.transform,
    d3.zoomIdentity.translate(wrap.width / 2, wrap.height / 2).scale(k).translate(-(x0 + x1) / 2, -(y0 + y1) / 2));
}

function flyTo(r) {
  if (!r.lonlat) return;
  const wrap = document.querySelector(".map-wrap").getBoundingClientRect();
  const k = Math.max(state.k, 4), [x, y] = proj(r.lonlat);
  svg.transition().duration(700).call(zoom.transform,
    d3.zoomIdentity.translate(wrap.width / 2, wrap.height / 2).scale(k).translate(-x, -y));
}

// ── Time ───────────────────────────────────────────────────────────────────
function positionAt(line, t) {
  const keys = line.keys;
  if (t <= keys[0].t) return { at: keys[0].at, row: keys[0].row };
  for (let i = 1; i < keys.length; i++) {
    if (t < keys[i].t) {
      const a = keys[i - 1], b = keys[i];
      if (!a.at) return { at: null, row: a.row, unknown: b.row };
      if (a.at === b.at) return { at: a.at, row: a.row };
      const f = (t - a.t) / (b.t - a.t);
      return { at: d3.geoInterpolate(a.at, b.at)(f), row: a.row, moving: b.to ?? b.row, voyage: a.voyage ?? b.voyage };
    }
  }
  return { at: keys.at(-1).at, row: keys.at(-1).row };
}

// The parts of the battalion on record on day t, and where each was
const active = t => U.lines.filter(l => t >= l.t0 && t < l.t1).map(l => ({ line: l, ...positionAt(l, t) }));

function setTime(t) {
  state.t = Math.max(U.t0, Math.min(U.t1, t));
  document.getElementById("scrub").value = Math.round(1000 * (state.t - U.t0) / (U.t1 - U.t0));
  document.getElementById("now-date").replaceChildren(el("b", null, fmtDay(new Date(state.t))));
  const pos = active(state.t);
  document.getElementById("now-where").textContent = pos.map(p => {
    const where = p.unknown ? `left ${p.row.place}; not recorded until ${p.unknown.place}, ${fmtDay(new Date(p.unknown.t))}` : p.moving ? `${p.row.place} → ${p.moving.place}${p.voyage?.ships ? ` (${p.voyage.ships.split(/[,;(]/)[0]}…)` : ""}` : p.row.place;
    return pos.length > 1 ? `${p.line.label}: ${where}` : where;
  }).join("   ·   ");
  if (g) {
    g.selectAll(".mk").classed("future", d => d.t > state.t);
    g.selectAll(".leg").classed("ahead", d => d.b.t > state.t);
    drawWho(pos.filter(p => p.at));
  }
  renderWeather(pos);
  d3.select("#strip .playhead").attr("x1", stripX(state.t)).attr("x2", stripX(state.t));
  highlightRows();
}

// A marker for each part on record, labelled with its name; names of markers close together are
// stacked a line apart.
function drawWho(pos = active(state.t).filter(p => p.at)) {
  if (!g) return;
  const k = state.k, seen = [];
  pos.forEach(p => {
    const [x, y] = proj(p.at).map(v => v * k);
    p.lift = seen.filter(([sx, sy]) => Math.hypot(sx - x, sy - y) < 60).length;
    seen.push([x, y]);
  });
  const who = g.select(".who-g").selectAll("g").data(pos).join(enter => {
    const w = enter.append("g").attr("class", "who");
    w.append("circle").attr("class", "halo");
    w.append("circle").attr("class", "core");
    w.append("text");
    return w;
  });
  who.attr("transform", d => `translate(${proj(d.at)})`);
  who.select(".halo").attr("r", 14.5 / k);
  who.select(".core").attr("r", 6 / k);
  who.select("text").attr("x", 10 / k).attr("y", d => (-8 - 15 * d.lift) / k).style("font-size", `${14.5 / k}px`)
    .style("stroke-width", `${3 / k}px`).text(d => d.line.label);
}

// The day's weather where each part was (tools/fetch_station_weather.py): what a wartime station
// within 150 km observed, when one did, and ERA5 at the place itself.
const C = v => `${Math.round(v)}°`;
function renderWeather(pos) {
  const box = document.getElementById("now-weather");
  const day = new Date(state.t).toISOString().slice(0, 10);
  const parts = [];
  for (const p of pos) {
    if (p.moving || p.unknown) continue;
    const w = DATA.weather[`${p.row.unit}|${p.row.place}|${day}`];
    if (!w || parts.some(x => x.place === p.row.place)) continue;
    parts.push({ place: p.row.place, f: Object.fromEntries(DATA.weather_fields.map((k, i) => [k, w[i]])) });
  }
  if (!parts.length) {
    box.textContent = pos.some(p => p.moving) ? "At sea or in transit: no weather for the voyage" : "";
    return;
  }
  box.replaceChildren(...parts.map(({ place, f }, i) => {
    const span = el("span");
    span.append(i ? " · " : "", el("b", null, place), ": ");
    if (f.isd_station) {
      span.append("observed at ", el("b", null, `${f.isd_name} (${f.isd_km} km)`), ` ${C(f.isd_tmax_c)}/${C(f.isd_tmin_c)} C, wind ${Math.round(f.isd_wind_mean_kn)} kn (to ${Math.round(f.isd_wind_max_kn)})`,
                  f.isd_precip_reports ? `, rain in ${f.isd_precip_reports} of ${f.isd_obs} reports` : ", no rain reported", "; ");
    } else span.append(el("span", "src", "no wartime station within 150 km; "));
    span.append(`ERA5 ${C(f.era5_tmax_c)}/${C(f.era5_tmin_c)} C, ${d3.format(".1f")(f.era5_precip_mm)} mm rain, wind to ${Math.round(f.era5_wind_max_kn)} kn `,
                el("span", "src", "(reanalysis, 0.25°)"));
    return span;
  }));
}

function togglePlay() { state.playing ? stop() : play(); }
function play() {
  if (state.t >= U.t1 - DAY) setTime(U.t0);
  state.playing = true;
  document.getElementById("play").textContent = "❚❚";
  let last = performance.now();
  const tick = now => {
    if (!state.playing) return;
    setTime(state.t + (now - last) / 1000 * DAYS_PER_SECOND * DAY);
    last = now;
    if (state.t >= U.t1) return stop();
    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}
function stop() { state.playing = false; document.getElementById("play").textContent = "▶"; }

// ── Timeline strip: the battalion and its parts, a row for each part on record at once, a tick per station ──
let stripX = () => 0;
function drawStrip() {
  const strip = d3.select("#strip");
  const W = strip.node().getBoundingClientRect().width || 600, ROW = 14;
  const levels = d3.max(U.lines, l => l.level) + 1, AXIS = 4 + levels * ROW + 6, H = AXIS + 18;
  strip.attr("viewBox", `0 0 ${W} ${H}`).style("height", `${H}px`).selectAll("*").remove();
  const x = d3.scaleUtc().domain([U.t0, U.t1]).range([8, W - 8]);
  stripX = t => x(t);
  U.lines.forEach(l => {
    const a = x(l.t0), b = x(Math.min(l.t1, U.t1)), y = 4 + l.level * ROW;
    strip.append("rect").attr("x", a).attr("y", y).attr("width", Math.max(1, b - a - 1)).attr("height", ROW - 2).attr("rx", 3)
      .attr("fill", "var(--series-track)").attr("opacity", l.part === "battalion" ? 1 : 0.75)
      .append("title").text(`${l.label}, ${fmtDay(new Date(l.t0))} – ${l.t1 < Infinity ? fmtDay(new Date(l.t1)) : "end"}${l.note ? `: ${l.note}` : ""}`);
    if (b - a > l.label.length * 5.6 + 10) strip.append("text").attr("class", "seg-label").attr("x", a + 5).attr("y", y + 9).text(l.label);
  });
  U.rows.forEach(r => strip.append("line").attr("x1", x(r.t)).attr("x2", x(r.t)).attr("y1", AXIS - 6).attr("y2", AXIS - 1)
    .attr("stroke", "var(--series-track)"));
  strip.append("g").attr("class", "axis").attr("transform", `translate(0,${AXIS})`)
    .call(d3.axisBottom(x).ticks(Math.max(3, Math.floor(W / 90))).tickFormat(d3.utcFormat("%b %Y")).tickSizeOuter(0));
  strip.append("line").attr("class", "playhead").attr("y1", 0).attr("y2", AXIS)
    .attr("stroke", "var(--text-primary)").attr("stroke-width", 1.5);
  strip.on("click", ev => { stop(); setTime(+x.invert(d3.pointer(ev)[0])); });
}

// ── Side panel: every station, with the ships that arrived there ───────────
function renderSide() {
  const list = document.getElementById("list");
  list.replaceChildren(el("div", "unit-note", U.note));
  document.getElementById("side-title").textContent = `Stations (${U.rows.length})`;
  U.rows.slice().sort((a, b) => a.t - b.t || a.id - b.id).forEach(r => list.append(stationRow(r)));
}

// Each entry (entry.css): the date; a bar in the colour of its mark (dashed where the place is assumed, muted where
// there's none); where, and which part of the battalion; the roll's words as typed; notes; the pages.
function stationRow(r) {
  const row = el("div", "row entry" + (!r.lonlat || r.hollow ? " assumed" : ""));
  row.style.setProperty("--bar", r.lonlat ? "var(--series-track)" : "var(--text-muted)");
  row.tabIndex = 0;
  row.setAttribute("role", "button");
  row.dataset.t = r.t;
  const t = el("div", "t", d3.utcFormat("%-d %b")(new Date(r.t)));
  t.append(el("small", null, d3.utcFormat("%Y")(new Date(r.t))));
  const body = el("div", "body");
  const who = el("div", "who");
  who.append(el("b", null, r.place ?? "No position"));
  if (r.part !== "battalion") who.append(el("span", "what", r.part));
  body.append(who, el("div", "said", r.station));
  if (r.note) body.append(el("div", "note", r.note));
  r.presumed.forEach(x => body.append(el("div", "assume", x)));
  body.append(linksBlock(r.links, r));
  (r.arrivals || []).forEach(v => body.append(shipBlock(v)));
  row.append(t, body);
  row.addEventListener("click", ev => { if (ev.target.closest("a")) return; stop(); setTime(r.t); flyTo(r); });
  row.addEventListener("keydown", ev => { if (ev.key === "Enter") { setTime(r.t); flyTo(r); } });
  return row;
}

// The ships of a crossing (voyages.csv), under the station where it arrived
const VOYAGE_STATUS = { confirmed: "In the ships' records", partial: "Equipment's craft recorded; the men's not",
  planned: "From the loading order (a plan, before it sailed)", ordered: "Ordered in the task group's war diary",
  named: "Named in the Bureau's history sheet", "not recorded": "Ship not recorded" };
function shipBlock(v) {
  const box = el("div", `ship ${v.status.replace(" ", "-")}`);
  box.append(el("div", "ship-head", `${fmtDay(new Date(parseDay(v.sailed)))} – ${fmtDay(new Date(parseDay(v.arrived)))}: ${v.ships || "ship not recorded"}`),
             el("div", "ship-status", VOYAGE_STATUS[v.status] ?? v.status));
  if (v.carried) box.append(el("div", null, `Aboard: ${v.carried}`));
  if (v.note) box.append(el("div", "ship-voyage", v.note));
  if (v.positions.length) {
    const logged = v.positions.filter(q => q.on_track).length;
    box.append(el("div", "ship-voyage", `${logged} logged positions drawn on the map${v.positions.length > logged ? `; ${v.positions.length - logged} left off (see the data)` : ""}${v.positions.some(q => q.fixed) ? "; one corrected for a typing slip" : ""}`));
  }
  box.append(linksBlock(v.links, { station: v.ships || "voyage", t: parseDay(v.sailed) }));
  return box;
}

function linksBlock(links, r) {
  const div = el("div", "links");
  links.forEach(l => {
    const a = Object.assign(el("a", null, `${l.label} ↗`), { href: l.url, target: "_blank", rel: "noopener" });
    if (l.scan) a.addEventListener("click", ev => { ev.preventDefault(); openSource(l, r); });
    div.append(a);
  });
  return div;
}

function highlightRows() {
  const rows = [...document.querySelectorAll("#list .row")];
  let cur = null;
  rows.forEach(row => { row.classList.remove("current"); row.classList.toggle("future", +row.dataset.t > state.t); if (+row.dataset.t <= state.t) cur = row; });
  cur?.classList.add("current");
}

function renderStats() {
  const tile = (label, value, sub) => { const t = el("div", "tile"); t.append(el("div", "label", label), el("div", "value", value), el("div", "sub", sub)); return t; };
  const first = U.rows.reduce((a, b) => a.t <= b.t ? a : b), last = U.rows.reduce((a, b) => a.t >= b.t ? a : b);
  const parts = U.lines.filter(l => l.part !== "battalion").length;
  const logged = U.voyages.filter(v => v.pts.length).length;
  document.getElementById("stats").replaceChildren(
    tile("Stations", U.rows.length, `${fmtDay(new Date(first.t))} – ${fmtDay(new Date(last.t))}`),
    tile("Places", new Set(U.placed.map(r => r.place)).size, "a station each, from the records"),
    tile("Parts", parts || "—", parts ? "groups that split off and rejoined" : "the battalion together throughout"),
    tile("Voyages", U.voyages.length, `${logged} along a ship's logged positions`),
    tile("Distance", `${d3.format(",")(Math.round(U.km / 1000) * 1000)} km`, "between stations, or a ship's logged track"),
  );
}

function renderLegend() {
  const lg = d3.select("#legend");
  lg.selectAll("*").remove();
  const item = (draw, text) => { const s = lg.append("span"); const v = s.append("svg").attr("width", 22).attr("height", 12); draw(v); s.append("span").text(text); };
  item(v => v.append("circle").attr("cx", 11).attr("cy", 6).attr("r", 5).attr("fill", "var(--series-track)"), "Station, as the record places it");
  if (U.placed.some(r => r.hollow))
    item(v => v.append("circle").attr("cx", 11).attr("cy", 6).attr("r", 4).attr("fill", "var(--surface-1)").attr("stroke", "var(--series-track)").attr("stroke-width", 2.5),
         "Position assumed: a stand-in point");
  item(v => v.append("line").attr("x1", 1).attr("x2", 21).attr("y1", 6).attr("y2", 6).attr("stroke", "var(--series-track)").attr("stroke-width", 2), "Between stations, or a ship's logged track");
  item(v => v.append("line").attr("x1", 1).attr("x2", 21).attr("y1", 6).attr("y2", 6).attr("stroke", "var(--series-track)").attr("stroke-width", 2).attr("stroke-dasharray", "5 4"), "An end assumed");
  item(v => { v.append("circle").attr("cx", 8).attr("cy", 6).attr("r", 5).attr("fill", "var(--series-track)").attr("opacity", 0.25);
              v.append("circle").attr("cx", 8).attr("cy", 6).attr("r", 3).attr("fill", "var(--text-primary)"); },
       "Where each part was that day");
}

// ── Tooltip & scan viewer ──────────────────────────────────────────────────
function nearest(ev) {
  if (!g) return null;
  const [x, y] = d3.pointer(ev, g.node());
  let best = null, bd = HIT_PX / state.k;
  U.placed.forEach(r => { const [px, py] = proj(r.lonlat); const d = Math.hypot(px - x, py - y); if (d < bd) { bd = d; best = r; } });
  return best;
}

let hovered = null;
function onHover(ev) {
  const d = nearest(ev);
  setHover(d);
  if (!d) return hideTip();
  // every station at this point, so stacked ones can all be read
  const here = U.placed.filter(r => r.place === d.place);
  const box = el("div");
  box.append(el("div", "v", d.place));
  here.slice(0, 6).forEach(r => {
    box.append(el("div", "k", `${fmtDay(new Date(r.t))}${r.part !== "battalion" ? ` · ${r.part}` : ""}`), el("div", "i", `“${r.station.slice(0, 140)}${r.station.length > 140 ? "…" : ""}”`));
    r.presumed.forEach(x => box.append(el("div", "m", x)));
  });
  if (here.length > 6) box.append(el("div", "m", `and ${here.length - 6} more in the list`));
  box.append(el("div", "m", "Click to see the page it came from"));
  showTip(ev, box);
}
function setHover(d) {
  if (d === hovered) return;
  hovered = d;
  g?.selectAll(".mk").classed("hover", r => d && r.place === d.place);
}
function showTip(ev, content) { tip.replaceChildren(content); tip.style.display = "block"; moveTip(ev); }
function moveTip(ev) {
  const r = tip.getBoundingClientRect();
  tip.style.left = `${Math.min(ev.clientX + 14, innerWidth - r.width - 8)}px`;
  tip.style.top = `${Math.min(ev.clientY + 14, innerHeight - r.height - 8)}px`;
}
function hideTip() { tip.style.display = "none"; }

// A scan in the local cache (tools/nara.py fetch; the Seabee Museum's PDFs rendered to pages) shows
// in the viewer; otherwise the link opens the archive's own page.
function openSource(l, r) {
  if (!l) return;
  hideTip();
  if (!l.scan) return window.open(l.url, "_blank", "noopener");
  document.getElementById("scan-title").textContent = `${r.station.slice(0, 80)}${r.station.length > 80 ? "…" : ""} · ${fmtDay(new Date(r.t))}`;
  const link = document.getElementById("scan-link");
  link.href = l.url;
  link.textContent = `${l.label} ↗`;
  const img = document.getElementById("scan-img"), missing = document.getElementById("scan-missing");
  img.classList.remove("full");
  img.hidden = false; missing.hidden = true;
  img.onerror = () => {
    img.hidden = true; missing.hidden = false;
    missing.replaceChildren(document.createTextNode("This page isn't in the local copy of the scans. "),
      Object.assign(el("a", null, "See it at the archive ↗"), { href: l.url, target: "_blank", rel: "noopener" }));
  };
  img.src = CACHE + l.scan;
  img.alt = `Scan: ${l.label}`;
  document.getElementById("scan").showModal();
}

function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}
