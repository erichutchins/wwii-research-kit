// Ship tracks: a boat's war patrols (patrols.html?ship=bang, the default) or a ship's war diary
// (patrols.html?ship=haynsworth). Renders the GeoJSON that tools/check_track.py builds from the
// hand-transcribed positions.csv files; each vessel's wording comes from its ship.yml, through
// records/ships.json. RECORDS and CACHE are set in config.js.

// What a ship.yml leaves out, by kind of vessel. A submarine's page reads as a set of war patrols.
const DEFAULTS = {
  submarine: {
    listTitle: "War patrols", daysLabel: "Days at sea", endText: "End of patrol",
    pageNoun: "report page", docAlt: "patrol report",
    introLink: "National Archives scans", introEnd: ". Click any point to see the page it came from.",
    labels: {},
    counts: [["Torpedo attacks", "attack"], ["Aircraft contacts", "air"]],
    legend: [{ cls: "fix", text: "Navigational fix" }, { cls: "air", text: "Aircraft contact" },
             { cls: "attack", text: "Torpedo attack" }, { cls: "ship", text: "Ship contact (target's position)" },
             { cls: "event", text: "Logged event", ifPresent: true },
             { cls: "off", text: "Fix left off the track", showOff: true }],
  },
  ship: {
    listTitle: "War diary", daysLabel: "Days covered", endText: "End of diary",
    pageNoun: "war diary page", docAlt: "war diary",
    introLink: "National Archives scans", introEnd: ". Click any point to see the page it came from.",
    labels: {}, counts: [["Air contacts logged", "air"]],
    legend: [{ cls: "fix", text: "War diary position" }, { cls: "air", text: "Air contact" },
             { cls: "event", text: "Logged event", ifPresent: true }],
  },
};
let SHIPS, SHIP, PATROLS, PORTS, PLACES, LABEL;

// Pick the vessel from ?ship= (folder name or name, e.g. ss-385-bang or bang) and fill in defaults.
function chooseShip(ships) {
  const q = new URLSearchParams(location.search).get("ship") ?? "bang";
  const s = ships.find(d => d.key === q || d.alias === q) ?? ships.find(d => d.alias === "bang") ?? ships[0];
  const title = `USS ${s.name} (${s.hull})`;
  const sub = s.kind === "submarine";
  const n = s.periods.length;
  return {
    ...DEFAULTS[sub ? "submarine" : "ship"], short: s.name, title,
    heading: `${title} — ${sub ? "war patrol tracks" : "ship tracks"}`,
    intro: `Every position ${s.name} reported in ${sub ? `the ${n === 1 ? "war patrol report" : `${n} war patrol reports`} transcribed so far` : "her war diary"}, transcribed from the `,
    ports: [], places: [], ...s,
  };
}

// Report section -> map class
const CLASS = { bt: "fix", noon: "fix", radar: "fix", narrative: "fix", diary: "fix", air: "air", attack: "attack", ship: "ship",
                event: "event" };
const BASE_LABEL = {
  bt: "Bathythermograph reading", noon: "Noon position", radar: "Radar intercept", diary: "War diary position",
  narrative: "Port / narrative", air: "Aircraft contact", attack: "Torpedo attack", ship: "Ship contact",
};
const SHAPE = {
  fix:    { type: d3.symbolCircle,   size: 40 },
  air:    { type: d3.symbolTriangle, size: 95 },
  attack: { type: d3.symbolDiamond,  size: 150 },
  ship:   { type: d3.symbolCircle,   size: 80 },
  event:  { type: d3.symbolStar,     size: 120 },
  off:    { type: d3.symbolCircle,   size: 55 },
};
const NM_PER_RADIAN = 3440.065;
const DAYS_PER_SECOND = 1.5;   // playback speed
const HIT_PX = 14;             // hover radius around a point (24px+ target)

const state = { patrol: null, t: null, playing: false, follow: true, logFilter: "events", showOff: true, k: 1 };
const MIN_LEG_HOURS = 2;       // course/speed are averaged over at least this long
const FOLLOW_EASE = 0.2;       // fraction of the way the camera catches up each frame
let DATA, LAND, proj, path, zoom, delaunay, hitPoints = [];

const svg = d3.select("#map");
const tip = document.getElementById("tip");
const fmtDay = d3.utcFormat("%-d %b %Y");
const fmtUTC = d3.utcFormat("%-d %b %Y · %H%M GCT");

// ── Data ────────────────────────────────────────────────────────────────────
d3.json(RECORDS + "ships.json").then(ships => {
  SHIPS = ships;
  SHIP = chooseShip(ships);
  ({ periods: PATROLS, ports: PORTS, places: PLACES } = SHIP);
  LABEL = { ...BASE_LABEL, ...SHIP.labels };
  return Promise.all([
    d3.json(RECORDS + SHIP.geojson),
    d3.json("https://cdn.jsdelivr.net/npm/world-atlas@2/land-50m.json"),
  ]);
}).then(([geo, world]) => {
  LAND = topojson.feature(world, world.objects.land);
  DATA = prepare(geo);
  applyShip();
  buildControls();
  new ResizeObserver(() => render()).observe(document.querySelector(".map-wrap"));
  // dives.html links here as patrols.html?patrol=2&t=1944-07-04T04:42Z
  const q = new URLSearchParams(location.search);
  const qp = +q.get("patrol");
  select(PATROLS.some(p => p.n === qp) ? qp : PATROLS.length === 1 ? PATROLS[0].n : null);
  if (state.patrol !== null && q.get("t")) {
    state.focus = true;   // open centred on the boat at that moment (see focusView)
    setTime(Date.parse(q.get("t")));
    render();
  }
});

function prepare(geo) {
  const points = geo.features.filter(f => f.properties.kind !== "track").map(f => {
    const p = f.properties;
    const off = !p.on_track && p.kind !== "ship" && !p.assumed;
    // a navigational fix that carries a log note (rescue, mine, earthquake...) gets its own marker
    const event = !off && p.kind === "noon" && p.note;
    return {
      patrol: p.patrol, kind: p.kind, cls: off ? "off" : event ? "event" : CLASS[p.kind], off,
      ref: p.ref, utc: new Date(p.utc), local: p.local, page: p.page, note: p.note, fix: p.fix, assumed: !!p.assumed,
      latRaw: p.lat_raw, lonRaw: p.lon_raw, lonlat: f.geometry.coordinates,
    };
  });
  const tracks = PATROLS.map(P => {
    const pts = points.filter(d => d.patrol === P.n && !d.off && d.kind !== "ship" && !d.assumed).sort((a, b) => a.utc - b.utc);
    const coords = pts.map(d => d.lonlat);
    let nm = 0;
    for (let i = 1; i < coords.length; i++) nm += d3.geoDistance(coords[i - 1], coords[i]) * NM_PER_RADIAN;
    return { ...P, pts, coords, times: pts.map(d => +d.utc), nm,
             all: points.filter(d => d.patrol === P.n).sort((a, b) => a.utc - b.utc) };
  });
  return { points, tracks };
}

// ── Controls ────────────────────────────────────────────────────────────────
// Page wording and ship picker.
function applyShip() {
  document.title = SHIP.heading;
  document.querySelector("header h1").textContent = SHIP.heading;
  // the National Archives folder: the ship.yml's, or the one the first point's page is in
  const naId = SHIP.catalogId ?? DATA.points.find(d => d.page)?.page.match(/^rg\d+-(\d+)\//)?.[1];
  const a = el("a", null, SHIP.introLink);
  a.href = `https://catalog.archives.gov/id/${naId}`; a.target = "_blank"; a.rel = "noopener";
  document.querySelector("header p").replaceChildren(SHIP.intro, a, SHIP.introEnd);
  document.getElementById("map").setAttribute("aria-label", `Map of ${SHIP.short}'s track`);
  document.getElementById("to-dives").hidden = !SHIP.dives;
  document.getElementById("show-off").closest("label").hidden = !DATA.points.some(p => p.off);
  const pick = document.getElementById("ship-pick");
  SHIPS.forEach(s => {
    const o = el("option", null, `USS ${s.name} (${s.hull})`);
    o.value = s.alias; o.selected = s.key === SHIP.key;
    pick.append(o);
  });
  pick.addEventListener("change", () => { location.search = `?ship=${pick.value}`; });
}

function buildControls() {
  const seg = document.getElementById("patrol-seg");
  seg.hidden = PATROLS.length === 1;   // one period: nothing to choose between
  [null, ...PATROLS.map(p => p.n)].forEach(n => {
    const b = document.createElement("button");
    b.textContent = n === null ? "All patrols" : `Patrol ${n}`;
    b.dataset.p = n ?? "";
    b.addEventListener("click", () => select(n));
    seg.appendChild(b);
  });
  document.getElementById("show-off").addEventListener("change", e => {
    state.showOff = e.target.checked;
    renderLegend(); renderSide(); render();
  });
  document.querySelectorAll("#log-filter button").forEach(b => b.addEventListener("click", () => {
    state.logFilter = b.dataset.f;
    document.querySelectorAll("#log-filter button").forEach(x => x.setAttribute("aria-pressed", x === b));
    renderSide();
    setTime(state.t);
  }));
  document.getElementById("play").addEventListener("click", togglePlay);
  document.getElementById("follow").addEventListener("change", e => setFollow(e.target.checked));
  buildGauge();
  document.getElementById("scrub").addEventListener("input", e => {
    stop();
    const tr = current();
    setTime(tr.times[0] + (tr.times.at(-1) - tr.times[0]) * (+e.target.value / 1000));
  });
  document.getElementById("zin").addEventListener("click", () => svg.transition().call(zoom.scaleBy, 1.8));
  document.getElementById("zout").addEventListener("click", () => svg.transition().call(zoom.scaleBy, 1 / 1.8));
  document.getElementById("zreset").addEventListener("click", () => svg.transition().call(zoom.transform, state.home));
  document.getElementById("scan-close").addEventListener("click", () => document.getElementById("scan").close());
  document.getElementById("scan-img").addEventListener("click", e => e.target.classList.toggle("full"));
}

const current = () => DATA.tracks.find(t => t.n === state.patrol);

function select(n) {
  stop();
  state.focus = false;
  state.patrol = n;
  document.querySelectorAll("#patrol-seg button").forEach(b => b.setAttribute("aria-pressed", b.dataset.p === String(n ?? "")));
  state.t = n === null ? null : current().times.at(-1);
  document.getElementById("timeline").hidden = n === null;
  document.getElementById("gauge").hidden = n === null;
  document.getElementById("log-filter").hidden = n === null;
  renderStats();
  renderLegend();
  renderSide();
  render();
  updateDivesLink();
}

// Keep the "Dive profile" nav link pointing at the same patrol and moment
function updateDivesLink() {
  const a = document.getElementById("to-dives");
  if (!a || !SHIP.dives) return;
  const q = new URLSearchParams();
  if (state.patrol !== null) {
    q.set("patrol", state.patrol);
    if (state.t !== null) q.set("t", new Date(state.t).toISOString().slice(0, 16) + "Z");
  }
  a.href = "dives.html" + (q.size ? `?${q}` : "");
}

// ── Map ─────────────────────────────────────────────────────────────────────
function render() {
  if (!DATA) return;
  const box = document.querySelector(".map-wrap").getBoundingClientRect();
  const W = Math.max(300, box.width), H = Math.max(300, box.height);
  svg.attr("viewBox", `0 0 ${W} ${H}`);
  svg.selectAll("*").remove();

  const shown = state.patrol === null ? DATA.tracks : [current()];
  const fitTo = { type: "MultiLineString", coordinates: shown.map(t => t.coords) };
  proj = d3.geoMercator().rotate([SHIP.rotate ?? -160, 0]).fitExtent([[30, 30], [W - 90, H - 30]], fitTo);
  path = d3.geoPath(proj);

  const g = svg.append("g").attr("class", "zoomable");
  g.append("path").datum(d3.geoGraticule().step([5, 5])()).attr("class", "graticule").attr("d", path);
  g.append("path").datum(LAND).attr("class", "land").attr("d", path);

  const places = g.append("g");
  PLACES.forEach(p => places.append("text").attr("class", "place").attr("text-anchor", "middle")
    .datum(proj([p.lon, p.lat])).text(p.name));
  PORTS.forEach(p => {
    const pg = places.append("g").datum(proj([p.lon, p.lat]));
    pg.append("circle").attr("class", "port-dot").attr("r", 3.5);
    pg.append("text").attr("class", "port-label").attr("x", 7).attr("y", 4).text(p.name);
  });

  const tg = g.append("g");
  if (state.patrol === null) {
    DATA.tracks.forEach(t => {
      const line = { type: "LineString", coordinates: t.coords };
      tg.append("path").datum(line).attr("class", `track other t${t.n}`).attr("d", path);
      tg.append("path").datum(line).attr("class", "track-hit").attr("d", path)
        .on("pointerenter", ev => { hotTrack(t.n); showTip(ev, trackTip(t)); })
        .on("pointermove", ev => moveTip(ev))
        .on("pointerleave", () => { hotTrack(null); hideTip(); })
        .on("click", () => { hideTip(); select(t.n); });
    });
  } else {
    const t = current();
    tg.append("path").datum({ type: "LineString", coordinates: t.coords }).attr("class", "track ahead").attr("d", path);
    tg.append("path").attr("class", "track past");
  }

  const mg = g.append("g").attr("class", "markers");
  hitPoints = [];
  if (state.patrol !== null) {
    const pts = current().all.filter(d => state.showOff || !d.off);
    // draw fixes first so contacts and attacks sit on top
    const order = { fix: 0, off: 1, ship: 2, event: 3, air: 4, attack: 5 };
    pts.sort((a, b) => order[a.cls] - order[b.cls]).forEach(d => {
      const [x, y] = proj(d.lonlat);
      d.x = x; d.y = y;
      const s = SHAPE[d.cls];
      const sym = d3.symbol(s.type, s.size)();
      const mk = mg.append("g").attr("class", `mk ${d.cls}`).datum([x, y]);
      mk.append("path").attr("class", "ring").attr("d", sym).attr("stroke-width", d.cls === "fix" ? 1.5 : 3);
      mk.append("path").attr("class", "shape").attr("d", sym);
      d.node = mk.node();
      hitPoints.push(d);
    });
    const sub = g.append("g").attr("class", "sub-marker").datum([0, 0]).style("display", "none");
    sub.append("circle").attr("class", "halo").attr("r", 13);
    sub.append("g").attr("class", "heading")
      .append("path").attr("class", "core").attr("d", "M0,-10 L6.5,7 L0,3.5 L-6.5,7 Z");
  }
  delaunay = d3.Delaunay.from(hitPoints, d => d.x, d => d.y);

  state.W = W; state.H = H;
  zoom = d3.zoom().scaleExtent([1, 80]).translateExtent([[-W, -H], [2 * W, 2 * H]])
    .on("zoom", ev => {
      g.attr("transform", ev.transform); state.k = ev.transform.k; rescale();
      // dragging the map while following hands control back to the reader (wheel zoom keeps following)
      if (state.playing && state.follow && /move/.test(ev.sourceEvent?.type)) setFollow(false);
      if (ev.sourceEvent) state.focus = false;   // the reader has taken over the view
    });
  svg.call(zoom).on("dblclick.zoom", null);
  state.home = homeView(W, H);
  svg.call(zoom.transform, state.focus ? focusView(W, H) : state.home);
  svg.on("pointermove", onHover).on("pointerleave", () => { setHover(null); })
     .on("click", () => { if (state.hover) openScan(state.hover); });
  rescale();

  if (state.patrol !== null) { drawStrip(); setTime(state.t); }
}

// A single patrol opens on its operating area rather than the long transit from
// Pearl or Midway: most fixes cluster on station, so fit to the fixes within
// 800 nm of the median position (zoom out or press ⟲ for the whole voyage).
const AREA_NM = 800;
function homeView(W, H) {
  if (state.patrol === null) return d3.zoomIdentity;
  const pts = current().pts;
  const centre = [d3.median(pts, d => (d.lonlat[0] + 360) % 360), d3.median(pts, d => d.lonlat[1])];
  const xy = SHIP.home ? SHIP.home.map(proj)   // a ship that crossed an ocean opens on the box given in its config
    : pts.filter(d => d3.geoDistance(centre, d.lonlat) * NM_PER_RADIAN < AREA_NM).map(d => proj(d.lonlat));
  if (xy.length < 2) return d3.zoomIdentity;
  const [x0, x1] = d3.extent(xy, d => d[0]), [y0, y1] = d3.extent(xy, d => d[1]);
  const k = Math.max(1, Math.min(12, 0.85 * Math.min(W / (x1 - x0 || 1), H / (y1 - y0 || 1))));
  return d3.zoomIdentity.translate(W / 2, H / 2).scale(k).translate(-(x0 + x1) / 2, -(y0 + y1) / 2);
}

// Deep links (patrols.html?patrol=2&t=...) open centred on the boat at that time
function focusView(W, H) {
  const [cx, cy] = proj(positionAt(current(), state.t));
  return d3.zoomIdentity.translate(W / 2, H / 2).scale(Math.max(state.home.k, 4)).translate(-cx, -cy);
}

// Keep markers and labels the same on-screen size at any zoom.
function rescale() {
  const k = state.k;
  svg.selectAll(".place, .zoomable > g > g, .mk, .sub-marker")
    .filter(function () { return Array.isArray(d3.select(this).datum()); })
    .attr("transform", d => `translate(${d[0]},${d[1]}) scale(${1 / k})`);
}

function onHover(ev) {
  if (!hitPoints.length) return;
  const t = d3.zoomTransform(svg.node());
  const [mx, my] = t.invert(d3.pointer(ev, svg.node()));
  const i = delaunay.find(mx, my);
  const d = hitPoints[i];
  const dist = d ? Math.hypot(d.x - mx, d.y - my) * t.k : Infinity;
  if (dist <= HIT_PX) { setHover(d); showTip(ev, pointTip(d)); }
  else setHover(null);
}

function setHover(d) {
  if (state.hover === d) return;
  if (state.hover) state.hover.node.classList.remove("hover");
  state.hover = d;
  svg.style("cursor", d ? "pointer" : null);
  if (d) d.node.classList.add("hover"); else hideTip();
}

function hotTrack(n) {
  svg.selectAll(".track.other").classed("hot", function () { return n !== null && this.classList.contains(`t${n}`); });
  svg.selectAll(".track.other.hot").raise();
  document.querySelectorAll(".pcard").forEach(c => c.classList.toggle("hot", +c.dataset.p === n));
}

// ── Time ────────────────────────────────────────────────────────────────────
function setTime(t) {
  const tr = current();
  if (!tr) return;
  const t0 = tr.times[0], t1 = tr.times.at(-1);
  t = Math.max(t0, Math.min(t1, t ?? t1));
  state.t = t;

  // BANG's interpolated position at t (great-circle between bracketing fixes)
  let i = d3.bisectRight(tr.times, t) - 1;
  i = Math.max(0, Math.min(i, tr.coords.length - 1));
  let pos = tr.coords[i];
  if (i < tr.coords.length - 1) {
    const f = (t - tr.times[i]) / (tr.times[i + 1] - tr.times[i] || 1);
    pos = d3.geoInterpolate(tr.coords[i], tr.coords[i + 1])(f);
  }
  svg.select(".track.past").attr("d", path({ type: "LineString", coordinates: [...tr.coords.slice(0, i + 1), pos] }));
  const atEnd = t >= t1;
  const leg = legAt(tr, i, t, pos);
  svg.select(".sub-marker").datum(proj(pos)).style("display", atEnd ? "none" : null)
    .select(".heading").attr("transform", leg.course === null ? null : `rotate(${leg.course})`);
  rescale();
  updateGauge(leg, atEnd);
  if (state.playing && state.follow) followBoat(proj(pos));
  svg.selectAll(".mk").classed("future", false);
  hitPoints.forEach(d => d.node.classList.toggle("future", +d.utc > t));

  document.getElementById("scrub").value = Math.round(((t - t0) / (t1 - t0)) * 1000);
  const day = Math.floor((t - t0) / 864e5) + 1, days = Math.ceil((t1 - t0) / 864e5);
  document.getElementById("now-local").textContent = `Day ${Math.min(day, days)} of ${days}`;
  document.getElementById("now-utc").textContent = fmtUTC(new Date(t));
  if (!state.playing) updateDivesLink();
  d3.select("#strip .playhead").attr("x1", stripX(t)).attr("x2", stripX(t));

  // Patrol log: mark the latest entry at or before t
  const rows = [...document.querySelectorAll("#list .row")];
  let cur = null;
  rows.forEach(r => { const past = +r.dataset.t <= t; r.classList.toggle("future", !past); r.classList.remove("current"); if (past) cur = r; });
  if (cur && !atEnd) {
    cur.classList.add("current");
    if (state.playing) {   // scroll the log only, never the page
      const list = document.getElementById("list");
      if (cur.offsetTop < list.scrollTop || cur.offsetTop + cur.offsetHeight > list.scrollTop + list.clientHeight)
        list.scrollTop = cur.offsetTop - list.clientHeight / 3;
    }
  }
}

let raf = null, lastFrame = null;
function togglePlay() { state.playing ? stop() : play(); }
function play() {
  const tr = current();
  if (state.t >= tr.times.at(-1)) state.t = tr.times[0];
  state.playing = true;
  if (state.follow && state.k < state.home.k) {
    const [x, y] = proj(positionAt(tr, state.t));
    svg.call(zoom.transform, d3.zoomIdentity.translate(state.W / 2, state.H / 2).scale(state.home.k).translate(-x, -y));
  }
  document.getElementById("play").textContent = "❚❚";
  document.getElementById("play").setAttribute("aria-label", "Pause");
  lastFrame = null;
  raf = requestAnimationFrame(tick);
}
function tick(now) {
  if (!state.playing) return;
  if (lastFrame !== null) setTime(state.t + (now - lastFrame) / 1000 * DAYS_PER_SECOND * 864e5);
  lastFrame = now;
  if (state.t >= current().times.at(-1)) return stop();
  raf = requestAnimationFrame(tick);
}
function stop() {
  state.playing = false;
  if (DATA) updateDivesLink();
  cancelAnimationFrame(raf);
  const b = document.getElementById("play");
  b.textContent = "▶"; b.setAttribute("aria-label", "Play");
}

function positionAt(tr, t) {
  const i = Math.max(0, Math.min(d3.bisectRight(tr.times, t) - 1, tr.coords.length - 1));
  if (i === tr.coords.length - 1) return tr.coords[i];
  return d3.geoInterpolate(tr.coords[i], tr.coords[i + 1])((t - tr.times[i]) / (tr.times[i + 1] - tr.times[i] || 1));
}

// Course and speed made good: the average implied by the reported fixes around t.
// Fixes minutes apart (attack sheets) would give nonsense speeds, so the leg is
// widened until it spans at least MIN_LEG_HOURS.
function legAt(tr, i, t, pos) {
  const n = tr.times.length;
  let a = i, b = Math.min(i + 1, n - 1);
  while (tr.times[b] - tr.times[a] < MIN_LEG_HOURS * 36e5 && b < n - 1) b++;
  while (tr.times[b] - tr.times[a] < MIN_LEG_HOURS * 36e5 && a > 0) a--;
  const hours = (tr.times[b] - tr.times[a]) / 36e5;
  const nm = d3.geoDistance(tr.coords[a], tr.coords[b]) * NM_PER_RADIAN;
  const toNext = d3.geoDistance(pos, tr.coords[b]) * NM_PER_RADIAN;
  const inPort = tr.pts[a].kind === "narrative" && tr.pts[b].kind === "narrative" && nm < 1;
  return {
    from: tr.pts[a], to: tr.pts[b], hours, nm, inPort,
    speed: hours > 0 ? nm / hours : 0,
    course: toNext > 0.5 ? bearing(pos, tr.coords[b]) : nm > 0.5 ? bearing(tr.coords[a], tr.coords[b]) : null,
  };
}

// Initial great-circle bearing from a to b, degrees true
function bearing(a, b) {
  const r = Math.PI / 180, [l1, p1] = [a[0] * r, a[1] * r], [l2, p2] = [b[0] * r, b[1] * r];
  const y = Math.sin(l2 - l1) * Math.cos(p2);
  const x = Math.cos(p1) * Math.sin(p2) - Math.sin(p1) * Math.cos(p2) * Math.cos(l2 - l1);
  return (Math.atan2(y, x) / r + 360) % 360;
}

function followBoat([x, y]) {
  const cur = d3.zoomTransform(svg.node());
  const tx = state.W / 2 - cur.k * x, ty = state.H / 2 - cur.k * y;
  svg.call(zoom.transform, d3.zoomIdentity
    .translate(cur.x + (tx - cur.x) * FOLLOW_EASE, cur.y + (ty - cur.y) * FOLLOW_EASE).scale(cur.k));
}

function setFollow(on) {
  state.follow = on;
  document.getElementById("follow").checked = on;
}

// ── Course & speed gauge ────────────────────────────────────────────────────
function buildGauge() {
  const c = d3.select("#compass").attr("viewBox", "-40 -40 80 80");
  c.append("circle").attr("class", "dial").attr("r", 33);
  d3.range(0, 360, 30).forEach(a => c.append("line").attr("class", a % 90 ? "tick" : "tick major")
    .attr("y1", -33).attr("y2", a % 90 ? -29 : -26).attr("transform", `rotate(${a})`));
  [["N", 0], ["E", 90], ["S", 180], ["W", 270]].forEach(([l, a]) => {
    const r = 20, x = r * Math.sin(a * Math.PI / 180), y = -r * Math.cos(a * Math.PI / 180);
    c.append("text").attr("class", "card").attr("x", x).attr("y", y + 3.5).attr("text-anchor", "middle").text(l);
  });
  c.append("path").attr("class", "needle").attr("d", "M0,-30 L5,0 L0,6 L-5,0 Z");
  c.append("circle").attr("class", "hub").attr("r", 2.5);
}

function updateGauge(leg, atEnd) {
  const gauge = document.getElementById("gauge");
  gauge.hidden = state.patrol === null;
  const needle = d3.select("#compass .needle");
  const set = (id, text) => { document.getElementById(id).textContent = text; };
  if (atEnd || leg.inPort) {
    needle.style("display", "none");
    set("g-course", "—"); set("g-speed", atEnd ? "Moored" : "In port");
    set("g-leg", atEnd ? SHIP.endText : `${portName(leg.from)} · ${fmtSpan(leg)}`);
    return;
  }
  needle.style("display", leg.course === null ? "none" : null).attr("transform", `rotate(${leg.course ?? 0})`);
  set("g-course", leg.course === null ? "—" : `${String(Math.round(leg.course) % 360).padStart(3, "0")}° T`);
  set("g-speed", leg.speed < 0.3 ? "Stationary" : `${leg.speed.toFixed(1)} kn`);
  set("g-leg", `Average from ${shortWhen(leg.from)} to ${shortWhen(leg.to)} · ${Math.round(leg.nm)} nm in ${fmtHours(leg.hours)}`);
}

const shortFmt = d3.utcFormat("%-d %b %H%M");
const shortWhen = d => `${shortFmt(d.utc)}Z`;
const fmtHours = h => h >= 48 ? `${(h / 24).toFixed(1)} days` : `${Math.round(h)} h`;
const fmtSpan = leg => fmtHours(leg.hours);
const portName = d => d.ref.replace(/^(arrive|depart|moor)\s+/i, "");

// Timeline strip: date axis plus a tick for every attack and aircraft contact
let stripX = () => 0;
function drawStrip() {
  const tr = current();
  const strip = d3.select("#strip");
  const W = strip.node().getBoundingClientRect().width || 600;
  strip.attr("viewBox", `0 0 ${W} 40`).selectAll("*").remove();
  const x = d3.scaleUtc().domain([tr.times[0], tr.times.at(-1)]).range([8, W - 8]);
  stripX = t => x(t);
  strip.append("g").attr("class", "axis").attr("transform", "translate(0,20)")
    .call(d3.axisBottom(x).ticks(Math.max(3, Math.floor(W / 90))).tickFormat(d3.utcFormat("%-d %b")).tickSizeOuter(0));
  tr.all.filter(d => d.cls === "air" || d.cls === "attack").forEach(d => {
    strip.append("path").attr("transform", `translate(${x(d.utc)},${d.cls === "attack" ? 9 : 12})`)
      .attr("d", d3.symbol(SHAPE[d.cls].type, d.cls === "attack" ? 60 : 30)())
      .attr("fill", `var(--series-${d.cls})`).attr("stroke", "var(--surface-1)").attr("stroke-width", 1);
  });
  strip.append("line").attr("class", "playhead").attr("y1", 0).attr("y2", 20)
    .attr("stroke", "var(--text-primary)").attr("stroke-width", 1.5);
  strip.on("click", ev => { stop(); setTime(+x.invert(d3.pointer(ev)[0])); });
}

// ── Side panel: patrol list or patrol log (the map's table view) ────────────
function renderSide() {
  const list = document.getElementById("list");
  list.replaceChildren();
  if (state.patrol === null) {
    document.getElementById("side-title").textContent = SHIP.listTitle;
    DATA.tracks.forEach(t => {
      const atk = t.all.filter(d => d.kind === "attack").length;
      const b = el("button", "pcard");
      b.dataset.p = t.n;
      b.append(el("div", "t", `Patrol ${t.n} · ${t.name}`), el("div", "d", t.area ? `${t.dates} · ${t.area}` : t.dates),
               el("div", "n", `${t.all.length} positions · ${atk} torpedo attack${atk === 1 ? "" : "s"}${t.co ? ` · ${t.co}` : ""}`));
      b.addEventListener("pointerenter", () => hotTrack(t.n));
      b.addEventListener("pointerleave", () => hotTrack(null));
      b.addEventListener("click", () => select(t.n));
      list.append(b);
    });
    return;
  }
  const tr = current();
  document.getElementById("side-title").textContent = PATROLS.length === 1 ? `${SHIP.short} log` : `Patrol ${tr.n} log`;
  const rows = tr.all.filter(d => (state.showOff || !d.off) &&
    (state.logFilter === "all" || d.cls !== "fix" || d.note || d.fix));
  rows.forEach(d => {
    const row = el("div", "row");
    row.dataset.t = +d.utc;
    row.tabIndex = 0;
    row.setAttribute("role", "button");
    row.append(iconFor(d));
    const body = el("div");
    body.append(el("div", "when", `${localWhen(d)} · ${d.latRaw} ${d.lonRaw}`), el("div", "what", title(d)));
    if (noteText(d)) body.append(el("div", "note", noteText(d)));
    if (d.fix) body.append(el("div", "fixnote", d.fix));
    const pg = el("a", "fixnote", `${cap(SHIP.pageNoun)} ${d.page.split("/p")[1]} ↗`);
    pg.href = "#"; pg.style.fontStyle = "normal";
    pg.addEventListener("click", e => { e.preventDefault(); e.stopPropagation(); openScan(d); });
    body.append(pg);
    row.append(body);
    const go = () => { stop(); setTime(+d.utc); flyTo(d); };
    row.addEventListener("click", go);
    row.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); go(); } });
    list.append(row);
  });
}

function flyTo(d) {
  if (d.x === undefined) return;
  const box = svg.node().viewBox.baseVal;
  const k = Math.max(state.k, 6);
  svg.transition().duration(600).call(zoom.transform,
    d3.zoomIdentity.translate(box.width / 2, box.height / 2).scale(k).translate(-d.x, -d.y));
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
  const fmt = d3.format(",.0f");
  const sel = state.patrol === null ? DATA.tracks : [current()];
  const pts = sel.flatMap(t => t.all);
  const count = k => pts.filter(d => d.kind === k).length;
  if (state.patrol === null) {
    const span = SHIP.span ?? `${fmtDay(d3.min(DATA.tracks, t => t.times[0]))} – ${fmtDay(d3.max(DATA.tracks, t => t.times.at(-1)))}`;
    tile("War patrols", String(PATROLS.length), span);
  } else {
    const t = current();
    tile(t.name, t.dates, t.co ?? "");
    tile(SHIP.daysLabel, fmt((t.times.at(-1) - t.times[0]) / 864e5));
  }
  tile("Distance between fixes", `${fmt(d3.sum(sel, t => t.nm))} nm`, "straight lines; actual distance was longer");
  tile("Positions reported", fmt(pts.filter(d => !d.assumed).length));
  SHIP.counts.forEach(([label, kind]) => tile(label, fmt(count(kind))));
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
  const shape = cls => g => g.append("path").attr("d", d3.symbol(SHAPE[cls].type, SHAPE[cls].size * 0.7)())
    .attr("class", "shape").attr("fill", { fix: "var(--text-secondary)", event: "var(--text-primary)", air: "var(--series-air)", attack: "var(--series-attack)" }[cls] || "none")
    .attr("stroke", cls === "ship" ? "var(--text-secondary)" : cls === "off" ? "var(--text-muted)" : null)
    .attr("stroke-width", 1.5).attr("stroke-dasharray", cls === "off" ? "2 2" : null);
  if (state.patrol === null) {
    item(g => g.append("line").attr("x1", -10).attr("x2", 10).attr("stroke", "var(--track-other)").attr("stroke-width", 2), "Patrol track");
    item(g => g.append("line").attr("x1", -10).attr("x2", 10).attr("stroke", "var(--series-track)").attr("stroke-width", 3), "Hovered patrol — click to open it");
    return;
  }
  item(g => g.append("line").attr("x1", -10).attr("x2", 10).attr("stroke", "var(--series-track)").attr("stroke-width", 2), "Track between fixes");
  SHIP.legend.filter(l => !l.ifPresent || current().all.some(d => d.cls === l.cls))
    .filter(l => !l.showOff || state.showOff).forEach(l => item(shape(l.cls), l.text));
  item(g => { g.append("circle").attr("r", 7).attr("fill", "var(--series-track)").attr("opacity", 0.25);
              g.append("path").attr("d", "M0,-10 L6.5,7 L0,3.5 L-6.5,7 Z").attr("transform", "rotate(45) scale(0.6)")
                .attr("fill", "var(--text-primary)"); }, `${SHIP.short}, pointing along her course`);
}

// ── Tooltip & scan viewer ───────────────────────────────────────────────────
function pointTip(d) {
  const f = document.createDocumentFragment();
  f.append(el("div", "v", localWhen(d)),
           el("div", "k", `${title(d)} · ${d.latRaw} ${d.lonRaw}`));
  if (noteText(d)) f.append(el("div", null, noteText(d)));
  if (d.fix) f.append(el("div", "i", d.fix));
  f.append(el("div", "m", `Click to view ${SHIP.pageNoun} ${d.page.split("/p")[1]}`));
  return f;
}
function trackTip(t) {
  const f = document.createDocumentFragment();
  f.append(el("div", "v", `Patrol ${t.n} · ${t.dates}`), el("div", "k", t.area), el("div", "m", "Click to open this patrol"));
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

function openScan(d) {
  const [folder, page] = d.page.split("/");
  const naId = folder.replace("rg367-", "");
  const n = parseInt(page.slice(1), 10);
  document.getElementById("scan-title").textContent = `${title(d)}, ${localWhen(d)} · ${SHIP.pageNoun} ${n}`;
  const img = document.getElementById("scan-img");
  img.classList.remove("full");
  setScanSrc(img, folder, page);
  img.alt = `Scan of ${SHIP.docAlt} page ${n}`;
  document.getElementById("scan-link").href = `https://catalog.archives.gov/id/${naId}?objectPage=${n}`;
  hideTip();
  document.getElementById("scan").showModal();
}

// ── Helpers ─────────────────────────────────────────────────────────────────
// Scans live in the cache's nara/ folder when downloaded (tools/nara.py fetch); otherwise
// load the same page from the National Archives (records/scans.json lists its URL).
let SCANS = null;
function setScanSrc(img, folder, page) {
  const key = `${folder}/${page}`;
  img.onerror = async () => {
    img.onerror = null;
    SCANS ??= await fetch(RECORDS + "scans.json").then(r => r.json()).catch(() => ({}));
    if (SCANS[key]) img.src = SCANS[key];
  };
  img.src = `${CACHE}nara/${key}.jpg`;
}

const cap = s => s[0].toUpperCase() + s.slice(1);

function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}

// "Air 3" -> "Aircraft contact No. 3"; narrative rows use their own wording ("depart Midway")
function title(d) {
  if (d.kind === "narrative") return d.ref[0].toUpperCase() + d.ref.slice(1);
  const no = ["air", "attack", "ship"].includes(d.kind) ? d.ref.replace(/^\D+/, "") : "";
  return no ? `${LABEL[d.kind]} No. ${no}` : LABEL[d.kind];
}

// The CSV note often restates the title ("Torpedo attack No. 2 (time 1616-32)"); keep only what's new.
function noteText(d) {
  const t = title(d);
  return d.note.toLowerCase().startsWith(t.toLowerCase()) ? d.note.slice(t.length).trim() : d.note;
}

// "1944-04-29 2256(K)" -> "29 Apr 1944 · 2256 K"   (time and zone as typed in the report)
function localWhen(d) {
  const m = /^(\d{4}-\d{2}-\d{2}) (\d{4})\((\w+)\)$/.exec(d.local);
  if (!m) return fmtUTC(d.utc);
  return `${fmtDay(new Date(`${m[1]}T00:00Z`))} · ${m[2]} ${m[3] === "Z" ? "GCT" : m[3]}`;
}

function iconFor(d) {
  const v = d3.create("svg").attr("width", 16).attr("height", 16);
  const s = SHAPE[d.cls];
  v.append("path").attr("transform", "translate(8,8)").attr("d", d3.symbol(s.type, s.size * 0.6)())
    .attr("fill", { fix: "var(--text-secondary)", event: "var(--text-primary)", air: "var(--series-air)", attack: "var(--series-attack)" }[d.cls] || "none")
    .attr("stroke", d.cls === "ship" ? "var(--text-secondary)" : d.cls === "off" ? "var(--text-muted)" : null)
    .attr("stroke-width", 1.5).attr("stroke-dasharray", d.cls === "off" ? "2 2" : null);
  return v.node();
}
