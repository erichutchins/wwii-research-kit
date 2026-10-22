// Zone letters explainer: the Navy's lettered time zones over the Pacific, with every
// transcribed position coloured by the zone it was logged in. Reads the GeoJSON that
// tools/check_track.py builds; each point's "local" is the time and zone as typed.

// Hours ahead of Greenwich, as in check_track.py's ZONES (K = zone description -10).
const OFFSET = { Z: 0, A: 1, B: 2, C: 3, D: 4, E: 5, F: 6, G: 7, H: 8, I: 9, IK: 9.5, K: 10, KL: 10.5, L: 11, LM: 11.5, M: 12,
                 N: -1, O: -2, P: -3, Q: -4, R: -5, S: -6, T: -7, U: -8, UV: -8.5, V: -9, VW: -9.5,
                 W: -10, WX: -10.5, X: -11, XY: -11.5, Y: -12 };
const BANDS = ["G", "H", "I", "K", "L", "M", "Y", "X", "W", "V", "U"];   // whole-hour zones drawn, west to east

// The groups the page compares: BANG, the other submarines transcribed so far, and USS Haynsworth's
// war diary. Each vessel's track file is listed in records/ships.json.
let SHIPS;
function groups(ships) {
  const group = (key, label, list) => ({ key, label, boats: list.map(s => s.name), files: list.map(s => RECORDS + s.geojson) });
  return [
    group("bang", "BANG", ships.filter(s => s.alias === "bang")),
    group("subs", "Other submarines", ships.filter(s => s.kind === "submarine" && s.alias !== "bang")),
    group("haynsworth", "USS Haynsworth", ships.filter(s => s.alias === "haynsworth")),
  ];
}
const PORTS = [
  { name: "Pearl Harbor", lon: -157.97, lat: 21.35 }, { name: "Midway", lon: -177.37, lat: 28.21 },
  { name: "Guam", lon: 144.65, lat: 13.45 }, { name: "Tokyo", lon: 139.69, lat: 35.69 },
];
const PLACES = [
  { name: "FORMOSA", lon: 121.0, lat: 23.7 }, { name: "LUZON", lon: 121.1, lat: 16.6 },
  { name: "CHINA", lon: 112.5, lat: 29.0 }, { name: "JAPAN", lon: 136.0, lat: 37.5 },
  { name: "MARIANAS", lon: 147.5, lat: 17.5 }, { name: "MARSHALL IS.", lon: 168.0, lat: 9.0 },
];

// Moments from the reports, for the clock table: the instant in GCT, and the zone the boat's clock kept.
const MOMENTS = [
  { label: "Attack 1, Apr 1944", utc: "1944-04-29T12:56Z", boat: "K",
    note: "BANG's first torpedo at convoy TAMA-17 in the Luzon Strait (Patrol 1, attack sheet: 29 Apr 1944 2256 K)." },
  { label: "Leaving Pearl, Mar 1944", utc: "1944-03-30T01:30Z", boat: "VW",
    note: "BANG, PARCHE and TINOSA leave Pearl Harbor for Midway (Patrol 1 narrative: 29 Mar 1944 1600 VW). In Tokyo it was already the 30th." },
  { label: "Earthquake, May 1945", utc: "1945-05-01T23:00Z", boat: "I",
    note: "BANG feels an earthquake, submerged off Formosa (Patrol 6 narrative: 2 May 1945 0800 I). In Washington it was still 1 May." },
];
const CLOCKS = [
  { name: "Washington (Eastern War Time)", zone: "Q" },
  { name: "Pearl Harbor (Hawaii war time)", zone: "VW" },
  { name: "Midway", zone: "Y" },
  { name: "Greenwich (GCT)", zone: "Z" },
  { name: "Guam and Saipan", zone: "K" },
  { name: "Tokyo, and every Japanese record", zone: "I" },
];

const state = { ship: "bang", zone: "K", moment: 0 };
const ALL = {};          // ship key -> points
let LAND, proj, path;
const svg = d3.select("#map");
const tip = document.getElementById("tip");

const fmtZone = z => {
  const h = OFFSET[z];
  if (h === 0) return "GMT";
  const a = Math.abs(h), s = Number.isInteger(a) ? a : `${Math.floor(a)}½`;
  return `GMT${h > 0 ? "+" : "−"}${s}`;
};
const describe = z => (OFFSET[z] === 0 ? "0" : (OFFSET[z] > 0 ? "−" : "+") + fmtZone(z).slice(4));
const fmtWhen = d3.utcFormat("%a %-d %b · %H%M");
const fmtShort = d3.utcFormat("%-d %b %Y %H%M");

d3.json(RECORDS + "ships.json").then(ships => {
  SHIPS = groups(ships);
  return Promise.all([
    ...SHIPS.map(s => Promise.all(s.files.map(f => d3.json(f).catch(() => null)))),
    d3.json("https://cdn.jsdelivr.net/npm/world-atlas@2/land-50m.json"),
  ]);
}).then(res => {
  const world = res.pop();
  LAND = topojson.feature(world, world.objects.land);
  SHIPS.forEach((s, i) => {
    ALL[s.key] = { points: [], tracks: [] };
    res[i].forEach((g, j) => {
      if (!g) return;
      const boat = s.key === "subs" ? s.boats[j] : s.label;
      for (const f of g.features) {
        if (f.geometry.type === "LineString") { ALL[s.key].tracks.push(f); continue; }
        const m = /^(\S+) (\d{4})\((\w+)\)$/.exec(f.properties.local || "");
        if (!m || !(m[3] in OFFSET)) continue;
        ALL[s.key].points.push({ ...f.properties, boat, zone: m[3], date: m[1], time: m[2],
                                 lon: f.geometry.coordinates[0], lat: f.geometry.coordinates[1] });
      }
    });
  });
  buildControls();
  buildCounts();
  buildMoments();
  new ResizeObserver(() => render()).observe(document.querySelector(".map-wrap"));
});

function buildControls() {
  const seg = d3.select("#ship-seg");
  seg.selectAll("button").data(SHIPS).join("button").text(d => d.label)
    .on("click", (e, d) => { state.ship = d.key; zoneButtons(); render(); });
  zoneButtons();
}

function zoneButtons() {
  d3.selectAll("#ship-seg button").attr("aria-pressed", d => d.key === state.ship);
  const used = [...new Set(ALL[state.ship].points.map(p => p.zone))];
  // west to east across the map: zones ahead of Greenwich by most hours first... then the date line... then Z
  const lonOf = z => (z === "Z" ? 1e9 : ((OFFSET[z] * 15) + 360) % 360);
  used.sort((a, b) => lonOf(a) - lonOf(b));
  if (!used.includes(state.zone)) state.zone = used.includes("K") ? "K" : used.includes("I") ? "I" : used[0];
  d3.select("#zone-seg").selectAll("button").data(used, d => d).join("button").text(d => d)
    .attr("title", d => `${d}: ${fmtZone(d)}`)
    .attr("aria-pressed", d => d === state.zone)
    .on("click", (e, d) => { state.zone = d; zoneButtons(); render(); });
}

// A zone's band: 15 degrees centred on its meridian, densified along the parallels.
// M and Y share the 180th meridian: each is the half on its own side of the date line.
const edges = z => {
  const c = OFFSET[z] * 15;
  return z === "M" ? [172.5, 180] : z === "Y" ? [180, 187.5] : [c - 7.5, c + 7.5];
};
const mid = z => d3.mean(edges(z));
function band(z) {
  const [a, b] = edges(z), ring = [];
  for (let x = a; x <= b; x += 0.5) ring.push([x, -30]);
  for (let x = b; x >= a; x -= 0.5) ring.push([x, 70]);
  ring.push(ring[0]);
  return { type: "Polygon", coordinates: [ring.reverse()] };
}

// Degrees east of a zone's meridian (-180..180)
const offMeridian = (lon, z) => ((lon - OFFSET[z] * 15 + 540) % 360) - 180;

function render() {
  const box = document.querySelector(".map-wrap").getBoundingClientRect();
  const W = box.width, H = box.height;
  svg.attr("viewBox", `0 0 ${W} ${H}`);
  proj = d3.geoMercator().rotate([-178, 0])
    .fitExtent([[10, 44], [W - 10, H - 10]], { type: "MultiPoint", coordinates: [[103, -2], [-147, 44]] });
  path = d3.geoPath(proj);
  svg.selectAll("*").remove();

  const g = svg.append("g");
  BANDS.forEach((z, i) => g.append("path").datum(band(z)).attr("d", path)
    .attr("class", `band${i % 2 ? " alt" : ""}${z === state.zone ? " on" : ""}`));
  g.append("path").datum(d3.geoGraticule().step([15, 15])()).attr("class", "graticule").attr("d", path);
  g.append("path").datum(LAND).attr("class", "land").attr("d", path);
  g.append("path").datum({ type: "LineString", coordinates: d3.range(-30, 71, 1).map(y => [180, y]) })
    .attr("class", "dateline").attr("d", path);
  const [dlx] = proj([180, 0]);
  g.append("text").attr("class", "dl-label").attr("x", dlx + 5).attr("y", H - 14).text("Date line");

  for (const p of PLACES) {
    const [x, y] = proj([p.lon, p.lat]);
    g.append("text").attr("class", "place").attr("x", x).attr("y", y).attr("text-anchor", "middle").text(p.name);
  }

  // Tracks, then points: the chosen zone's on top
  const data = ALL[state.ship];
  g.append("g").selectAll("path").data(data.tracks).join("path").attr("class", "track").attr("d", path);
  const pts = [...data.points].sort((a, b) => (a.zone === state.zone) - (b.zone === state.zone));
  g.append("g").selectAll("circle").data(pts).join("circle")
    .attr("class", d => `pt${d.zone === state.zone ? " on" : ""}`)
    .attr("r", d => (d.zone === state.zone ? 3.6 : 2.2))
    .attr("cx", d => proj([d.lon, d.lat])[0]).attr("cy", d => proj([d.lon, d.lat])[1])
    .on("mousemove", (e, d) => showTip(e, d)).on("mouseleave", hideTip)
    .on("click", (e, d) => openPage(d.page));

  for (const p of PORTS) {
    const [x, y] = proj([p.lon, p.lat]);
    g.append("circle").attr("class", "port").attr("cx", x).attr("cy", y).attr("r", 3.5);
    g.append("text").attr("class", "port-label").attr("x", x + 6).attr("y", y + 4).text(p.name);
  }

  // Letters along the top: click a band to choose its zone
  const top = svg.append("g");
  top.append("rect").attr("x", 0).attr("y", 0).attr("width", W).attr("height", 40).attr("fill", "var(--surface-1)").attr("opacity", 0.85);
  for (const z of BANDS) {
    const [x] = proj([mid(z), 0]);
    if (x < 8 || x > W - 8) continue;
    top.append("text").attr("class", `zl${z === state.zone ? " on" : ""}`).attr("x", x).attr("y", 18).text(z);
    top.append("text").attr("class", "zo").attr("x", x).attr("y", 32).text(fmtZone(z));
    const [x0, x1] = edges(z).map(e => proj([e, 0])[0]);
    top.append("rect").attr("class", "band-hit").attr("x", Math.min(x0, x1)).attr("y", 0)
      .attr("width", Math.abs(x1 - x0)).attr("height", 40)
      .on("click", () => { if (data.points.some(p => p.zone === z)) { state.zone = z; zoneButtons(); render(); } })
      .append("title").text(`Zone ${z}: clocks ${fmtZone(z)}, zone description ${describe(z)}`);
  }
  caption();
}

function caption() {
  const z = state.zone, ship = SHIPS.find(s => s.key === state.ship);
  const pts = ALL[state.ship].points.filter(p => p.zone === z);
  const el = document.getElementById("caption");
  const head = `<b>${pts.length}</b> ${ship.label === "BANG" ? "of BANG's" : ship.label === "USS Haynsworth" ? "of Haynsworth's" : "of the other boats'"} positions are logged in <b>${z}</b> (${fmtZone(z)}, zone description ${describe(z)}).`;
  if (z === "Z") { el.innerHTML = `${head} Greenwich time, used for tables, not a place: these positions are wherever the ship was.`; return; }
  if (!Number.isInteger(OFFSET[z])) { el.innerHTML = `${head} A half-hour zone, between ${z[0]} and ${z[1]}.`; return; }
  // west of the zone's band = the clock runs ahead of the sun there
  const [lo, hi] = edges(z).map(e => offMeridian(e, z));
  const west = pts.filter(p => offMeridian(p.lon, z) < lo), east = pts.filter(p => offMeridian(p.lon, z) > hi);
  const inside = pts.length - west.length - east.length;
  const hrs = arr => {
    const m = d3.max(arr, p => Math.abs(offMeridian(p.lon, z))) / 15;
    return `up to ${m.toFixed(1).replace(/\.0$/, "")} h`;
  };
  el.innerHTML = `${head} ${inside} are inside ${z}'s band.` +
    (west.length ? ` ${west.length} are west of it, where a ${z} clock ran ahead of the sun (${hrs(west)}).` : "") +
    (east.length ? ` ${east.length} are east of it, where it ran behind (${hrs(east)}).` : "");
}

function showTip(e, d) {
  const utc = new Date(d.utc.replace("Z", ":00Z"));
  tip.innerHTML = `<div class="v">${d.date} ${d.time} ${d.zone}</div>` +
    `<div class="k">${d.boat}${d.patrol ? ` · Patrol ${d.patrol}` : ""} · ${d.ref || d.kind}</div>` +
    `<div class="m">= ${fmtShort(utc)} GCT · ${d.lat_raw} ${d.lon_raw}</div>` +
    `<div class="i">Click to open the ${d.page.split("/")[1]} scan in the National Archives catalog</div>`;
  tip.style.display = "block";
  const r = tip.getBoundingClientRect();
  tip.style.left = `${Math.min(e.clientX + 14, innerWidth - r.width - 8)}px`;
  tip.style.top = `${Math.min(e.clientY + 14, innerHeight - r.height - 8)}px`;
}
function hideTip() { tip.style.display = "none"; }

// "rg367-74802746/p16" -> the catalog viewer on that page
function openPage(page) {
  const m = /^rg\d+-(\d+)\/p(\d+)$/.exec(page || "");
  if (m) window.open(`https://catalog.archives.gov/id/${m[1]}?objectPage=${+m[2]}`, "_blank", "noopener");
}

function buildMoments() {
  d3.select("#moment-seg").selectAll("button").data(MOMENTS).join("button").text(d => d.label)
    .on("click", (e, d) => { state.moment = MOMENTS.indexOf(d); moment(); });
  moment();
}

function moment() {
  const m = MOMENTS[state.moment];
  d3.selectAll("#moment-seg button").attr("aria-pressed", (d, i) => i === state.moment);
  document.getElementById("moment-note").textContent = m.note;
  const t = Date.parse(m.utc);
  const rows = CLOCKS.map(c => ({ ...c, boat: c.zone === m.boat }));
  if (!rows.some(r => r.boat)) rows.push({ name: "BANG's clock", zone: m.boat, boat: true });
  d3.select("#clocks").selectAll("tr").data(rows).join("tr").attr("class", d => (d.boat ? "boat" : null))
    .html(d => `<td>${d.name}</td><td><b>${d.zone}</b> <span class="muted">${fmtZone(d.zone)}</span></td>` +
      `<td class="big">${fmtWhen(new Date(t + OFFSET[d.zone] * 36e5))}</td>` +
      `<td class="muted">${d.boat ? "← BANG's clock" : ""}</td>`);
}

function buildCounts() {
  const zones = [...new Set(Object.values(ALL).flatMap(s => s.points.map(p => p.zone)))]
    .sort((a, b) => OFFSET[b] - OFFSET[a] || a.localeCompare(b));
  const count = (k, z) => ALL[k].points.filter(p => p.zone === z).length || "";
  const t = d3.select("#counts");
  t.append("thead").html(`<tr><th>Letter</th><th>Clocks</th><th>Zone description</th>${SHIPS.map(s => `<th>${s.label}</th>`).join("")}</tr>`);
  t.append("tbody").selectAll("tr").data(zones).join("tr")
    .html(z => `<td><b>${z}</b></td><td>${fmtZone(z)}</td><td class="mono">${describe(z)}</td>` +
      SHIPS.map(s => `<td class="num">${count(s.key, z)}</td>`).join(""));
}
