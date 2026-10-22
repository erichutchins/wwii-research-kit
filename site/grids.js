// Map grids explainer: the six military grids the Army records use, drawn as their
// lettered 100 km squares, with every grid reference in records/army/stations.csv and
// actions.csv decoded on its grid and compared with the town the same entry names.
// The Lambert maths is tools/ndg_grid.py's, generalised to the other zones.

const ELLIPSOIDS = {
  clarke1880: { a: 6378249.2, f: 1 / 293.4660213 },   // Clarke 1880 (IGN): the French grids
  bessel: { a: 6377397.155, f: 1 / 299.1528128 },     // Bessel 1841: the Italian grids
};
const PARIS = 2.33722917;
const MINOR = "ABCDEFGHJKLMNOPQRSTUVWXYZ";            // 100 km squares, five a row from the north-west
const MAJOR = "VWXYZQRSTULMNOPFGHJKABCDE";            // South Italy's 500 km squares, five a row from the south-west

// Each grid: projection, how its squares are lettered, and the area these records use it in
// (where the squares are drawn; not the zone's official limits).
const GRIDS = [
  { key: "italy", name: "South Italy Zone", short: "S. Italy", color: "var(--series-air)",
    ell: "bessel", lat0: 39.5, lon0: 14, k0: 0.99906, fe: 700000, fn: 600000,
    letters: "major", box: [[8.0, 36.4], [18.6, 43.2]],
    params: "Lambert conformal conic, Bessel 1841; origin 39°30′N 14°E, scale 0.99906, false origin 700 km west and 600 km south" },
  // Projection from sigterritoires.fr; its 100 km letters sit in a 500 km block (lettered W)
  // whose SW corner is 500 km E, 200 km N: the Bologna sheets' index puts M at 600-700 E,
  // 400-500 N, and the 894th medical detachment's two Siena references fall in Q
  { key: "nitaly", name: "North Italy Zone", short: "N. Italy", color: "var(--series-air)",
    ell: "bessel", lat0: 45.9, lon0: 14, k0: 0.9989, fe: 800000, fn: 601000,
    letters: [500000, 200000], block: "W", box: [[10.0, 42.9], [13.0, 44.4]], dash: "5 3",
    params: "Lambert conformal conic, Bessel 1841; origin 45.9°N 14°E, scale 0.9989, false easting 800 km, false northing 601 km" },
  // Lambert I: its letters fit a block from 0 km E, 0 km N, lettered V (Co. B, 313th Infantry, Normandy 1944;
  // the 128th AAA's HQ battery from Cherbourg to Rennes and Le Mans, June-August 1944)
  { key: "lam1", name: "Lambert Zone I (Nord)", short: "Lambert I", color: "var(--series-attack)",
    ell: "clarke1880", lat0: 49.5, lon0: PARIS, k0: 0.99987734, fe: 600000, fn: 200000,
    letters: [0, 0], block: "V", box: [[-2.8, 47.7], [0.6, 50.1]],
    params: "Lambert conformal conic, Clarke 1880; origin 49.5°N (55 grad) on the Paris meridian, scale 0.99987734, false easting 600 km, false northing 200 km" },
  { key: "lam3", name: "Lambert Zone III (Sud)", short: "Lambert III", color: "var(--series-attack)",
    ell: "clarke1880", lat0: 44.1, lon0: PARIS, k0: 0.99987750, fe: 600000, fn: 200000,
    letters: [500000, 0], box: [[3.6, 42.9], [7.9, 45.5]], dash: "5 3",
    params: "Lambert conformal conic, Clarke 1880; origin 44.1°N (49 grad) on the Paris meridian, scale 0.9998775, false easting 600 km, false northing 200 km" },
  { key: "lam2", name: "Lambert Zone II (Centre)", short: "Lambert II", color: "var(--series-attack)",
    ell: "clarke1880", lat0: 46.8, lon0: PARIS, k0: 0.99987742, fe: 600000, fn: 200000,
    letters: [500000, 0], box: [[3.6, 45.4], [7.4, 48.3]],
    params: "Lambert conformal conic, Clarke 1880; origin 46.8°N (52 grad) on the Paris meridian, scale 0.99987742, false easting 600 km, false northing 200 km" },
  { key: "ndg", name: "Nord de Guerre", short: "Nord de Guerre", color: "var(--series-track)",
    ell: "clarke1880", lat0: 49.5, lon0: PARIS + 5.4, k0: 0.99950908, fe: 500000, fn: 300000,
    letters: [400000, 100000], west: [-100000, 100000], box: [[1.8, 47.4], [12.8, 50.7]],
    params: "Lambert conformal conic, Clarke 1880; origin 49.5°N (55 grad), 6 grad east of Paris (7.737°E), scale 0.99950908, false easting 500 km, false northing 300 km" },
];
const BY_KEY = Object.fromEntries(GRIDS.map(g => [g.key, g]));

// ── Lambert conformal conic, one standard parallel (as in tools/ndg_grid.py) ──
function lcc(g) {
  const { a, f } = ELLIPSOIDS[g.ell], e = Math.sqrt(2 * f - f * f), rad = Math.PI / 180;
  const m = p => Math.cos(p) / Math.sqrt(1 - (e * Math.sin(p)) ** 2);
  const t = p => Math.tan(Math.PI / 4 - p / 2) / ((1 - e * Math.sin(p)) / (1 + e * Math.sin(p))) ** (e / 2);
  const p0 = g.lat0 * rad, n = Math.sin(p0), F = m(p0) / (n * t(p0) ** n), r0 = a * F * t(p0) ** n * g.k0;
  return {
    fwd([lon, lat]) {
      const r = a * F * t(lat * rad) ** n * g.k0, th = n * (lon - g.lon0) * rad;
      return [g.fe + r * Math.sin(th), g.fn + r0 - r * Math.cos(th)];
    },
    inv([x, y]) {
      const dx = x - g.fe, dy = r0 - (y - g.fn);
      const tt = (Math.sign(n) * Math.hypot(dx, dy) / (a * F * g.k0)) ** (1 / n);
      let p = Math.PI / 2 - 2 * Math.atan(tt);
      for (let i = 0; i < 10; i++) p = Math.PI / 2 - 2 * Math.atan(tt * ((1 - e * Math.sin(p)) / (1 + e * Math.sin(p))) ** (e / 2));
      return [Math.atan2(dx, dy) / n / rad + g.lon0, p / rad];
    },
  };
}
GRIDS.forEach(g => { g.proj = lcc(g); });

// The 100 km square (SW corner, metres) a letter names, and the letter of the square at (x, y)
function squareOrigin(g, letter, major) {
  const i = MINOR.indexOf(letter), row = Math.floor(i / 5), col = i % 5;
  if (g.letters === "major") {
    const j = MAJOR.indexOf(major || "R");
    return [(j % 5) * 500000 + col * 100000, Math.floor(j / 5) * 500000 + (4 - row) * 100000];
  }
  const [e0, n0] = major === "V" && g.west ? g.west : g.letters;
  return [e0 + col * 100000, n0 + (4 - row) * 100000];
}
function squareLabel(g, x, y) {
  if (g.letters === "major") {
    const j = Math.floor(y / 500000) * 5 + Math.floor(x / 500000);
    const i = (4 - Math.floor((y % 500000) / 100000)) * 5 + Math.floor((x % 500000) / 100000);
    return MAJOR[j].toLowerCase() + MINOR[i];
  }
  const blocks = [[g.letters, (g.block || "").toLowerCase()], ...(g.west ? [[g.west, "V"]] : [])];
  for (const [[e0, n0], pre] of blocks) {
    const col = Math.floor((x - e0) / 100000), row = 4 - Math.floor((y - n0) / 100000);
    if (col >= 0 && col < 5 && row >= 0 && row < 5) return pre + MINOR[row * 5 + col];
  }
  return "";
}

// Digits -> metres into the square, at the centre of the last digit's cell
function digitsXY(d) {
  const k = d.length / 2, unit = 10 ** (5 - k);
  return [+d.slice(0, k) * unit + unit / 2, +d.slice(k) * unit + unit / 2, unit];
}

// Decode a reference on a grid. With no letter, the square is the one nearest `near` (a town's lon/lat).
function decode(g, ref, near) {
  const m = /^([A-Z]{0,2})[-\s]?(\d{2}|\d{4}|\d{6}|\d{8})$/.exec(ref.toUpperCase().replace(/Ø/g, "0").replace(/\s+/g, " ").trim());
  if (!m) return null;
  const [dx, dy, cell] = digitsXY(m[2]);
  let x, y;
  if (m[1]) {
    const letter = m[1].at(-1), major = m[1].length === 2 ? m[1][0] : null;
    if (!MINOR.includes(letter) || (major && g.letters !== "major" && !(major === "V" && g.west) && major !== g.block)) return null;
    const [x0, y0] = squareOrigin(g, letter, major);
    [x, y] = [x0 + dx, y0 + dy];
  } else {
    if (!near) return null;
    const [tx, ty] = g.proj.fwd(near);
    let best = Infinity;
    for (const i of [-1, 0, 1]) for (const j of [-1, 0, 1]) {
      const cx = (Math.floor(tx / 100000) + i) * 100000 + dx, cy = (Math.floor(ty / 100000) + j) * 100000 + dy;
      const d = Math.hypot(cx - tx, cy - ty);
      if (d < best) { best = d; [x, y] = [cx, cy]; }
    }
  }
  return { lonlat: g.proj.inv([x, y]), xy: [x, y], cell, inferred: !m[1] };
}

// Which grid an entry's reference is on: the `grid_on` column, worked out by testing every grid
// against the towns the entries name (the checks table at the bottom of the page shows the result)
const GRID_ON = { "italy-s": "italy", "italy-n": "nitaly", lambert1: "lam1", lambert3: "lam3", lambert2: "lam2", ndg: "ndg", "ndg-w": "ndg" };

// "2.75 mi NE" -> the town moved by the typed offset
const BEARING = { N: 0, NNE: 22.5, NE: 45, ENE: 67.5, E: 90, ESE: 112.5, SE: 135, SSE: 157.5, S: 180,
                  SSW: 202.5, SW: 225, WSW: 247.5, W: 270, WNW: 292.5, NW: 315, NNW: 337.5 };
function applyOffset([lon, lat], off) {
  const m = /^([\d.]+) (mi|km|yd) ([NSEW]{1,3})$/.exec(off || "");
  if (!m) return [lon, lat];
  const km = +m[1] * { mi: 1.609, km: 1, yd: 0.0009144 }[m[2]], b = BEARING[m[3]] * Math.PI / 180;
  return [lon + (km * Math.sin(b)) / (111.32 * Math.cos(lat * Math.PI / 180)), lat + (km * Math.cos(b)) / 110.57];
}
const km = (a, b) => d3.geoDistance(a, b) * 6371;

// ── Page ──────────────────────────────────────────────────────────────────────
const state = { grid: "all", probe: null };
let LAND, BORDERS, REFS = [], SQUARES = {}, proj, path, zoom, k = 1;
const svg = d3.select("#map"), tip = document.getElementById("tip");
const UNIT = { "106aaa-d": "Btry D, 106th AAA", "62ca-c": "Btry C, 62nd CA", "67ca-med": "Med Det, 67th CA / 894th AAA",
               "313inf-b": "Co B, 313th Infantry", "128aaa-hq": "HQ Btry, 128th AAA" };
const PAGE_URL = page => {
  let m = /^rg64-(\d+)\/p(\d+)$/.exec(page);
  if (m) return `https://catalog.archives.gov/id/${m[1]}?objectPage=${+m[2]}`;
  m = /^ok45th-(\d+)\//.exec(page);
  if (m) return `https://cdm17494.contentdm.oclc.org/digital/collection/ok45th/id/${m[1]}`;
  return null;
};

Promise.all([
  d3.csv(RECORDS + "army/stations.csv"), d3.csv(RECORDS + "army/actions.csv"), d3.csv(RECORDS + "army/places.csv"),
  d3.json("https://cdn.jsdelivr.net/npm/world-atlas@2/countries-50m.json"),
]).then(([stations, actions, places, world]) => {
  LAND = topojson.feature(world, world.objects.land);
  BORDERS = topojson.mesh(world, world.objects.countries, (a, b) => a !== b);
  // Places placed from a grid reference in the first place can't check one
  const P = Object.fromEntries(places.filter(p => p.lat && p.source !== "grid").map(p => [p.place, [+p.lon, +p.lat]]));
  for (const [kind, rows] of [["station", stations], ["action", actions]]) {
    for (const r of rows) {
      if (!r.grid || r.grid.includes("?")) continue;
      const sheet = /^(\d{6}) Sheet/.exec(r.grid);
      const ref = sheet ? sheet[1] : r.grid.replace(/\s+/g, " ");
      const town = P[r.place] ? applyOffset(P[r.place], r.offset) : null;
      const key = GRID_ON[r.grid_on] ?? null;
      // ndg-w: the western 500 km block, lettered V (the 894th medical detachment's December pages type "VZ-6457")
      const read = r.grid_on === "ndg-w" && !/^V/.test(ref) ? `V${ref}` : ref;
      const out = { ...r, kind, ref: read, town, key, sheet: !!sheet };
      if (key) {
        const d = decode(BY_KEY[key], read, town);
        if (d) Object.assign(out, d, { dist: town ? km(d.lonlat, town) : null });
      }
      REFS.push(out);
    }
  }
  REFS.sort((a, b) => a.date.localeCompare(b.date));
  for (const g of GRIDS) SQUARES[g.key] = squares(g);
  buildControls();
  buildTables();
  new ResizeObserver(() => render()).observe(document.querySelector(".map-wrap"));
  document.getElementById("probe").addEventListener("input", e => probe(e.target.value));
  probe(document.getElementById("probe").value);
});

// Every 100 km square whose centre falls in the grid's box, as a lon/lat polygon
function squares(g) {
  const [[w, s], [e, n]] = g.box, out = [];
  const corners = [[w, s], [e, s], [w, n], [e, n], [(w + e) / 2, n], [(w + e) / 2, s]].map(c => g.proj.fwd(c));
  const [x0, x1] = d3.extent(corners, c => c[0]), [y0, y1] = d3.extent(corners, c => c[1]);
  for (let x = Math.floor(x0 / 1e5) * 1e5; x < x1; x += 1e5) for (let y = Math.floor(y0 / 1e5) * 1e5; y < y1; y += 1e5) {
    const [clon, clat] = g.proj.inv([x + 5e4, y + 5e4]);
    if (clon < w || clon > e || clat < s || clat > n) continue;
    const ring = [];
    for (let i = 0; i <= 10; i++) ring.push([x + i * 1e4, y]);
    for (let i = 0; i <= 10; i++) ring.push([x + 1e5, y + i * 1e4]);
    for (let i = 10; i >= 0; i--) ring.push([x + i * 1e4, y + 1e5]);
    for (let i = 10; i >= 0; i--) ring.push([x, y + i * 1e4]);
    out.push({ g, label: squareLabel(g, x + 5e4, y + 5e4), centre: [clon, clat],
               geo: { type: "Polygon", coordinates: [ring.map(p => g.proj.inv(p)).reverse()] } });
  }
  return out;
}

function buildControls() {
  const opts = [{ key: "all", short: "All grids" }, ...GRIDS];
  d3.select("#grid-seg").selectAll("button").data(opts).join("button").text(d => d.short)
    .on("click", (e, d) => { state.grid = d.key; render(); });
  d3.select("#zin").on("click", () => svg.transition().call(zoom.scaleBy, 1.6));
  d3.select("#zout").on("click", () => svg.transition().call(zoom.scaleBy, 1 / 1.6));
  d3.select("#zreset").on("click", () => svg.transition().call(zoom.transform, d3.zoomIdentity));
}

function render() {
  const box = document.querySelector(".map-wrap").getBoundingClientRect(), W = box.width, H = box.height;
  d3.selectAll("#grid-seg button").attr("aria-pressed", d => d.key === state.grid);
  svg.attr("viewBox", `0 0 ${W} ${H}`);
  const focus = state.grid === "all" ? [[-1.8, 36.6], [12.6, 50.4]] : BY_KEY[state.grid].box;
  proj = d3.geoConicConformal().parallels([40, 50]).rotate([-9, 0])
    .fitExtent([[24, 24], [W - 24, H - 24]], { type: "MultiPoint", coordinates: [focus[0], focus[1], [focus[0][0], focus[1][1]], [focus[1][0], focus[0][1]]] });
  path = d3.geoPath(proj);
  svg.selectAll("*").remove();
  const g = svg.append("g");
  g.append("path").datum(LAND).attr("class", "land").attr("d", path);
  g.append("path").datum(BORDERS).attr("class", "border").attr("d", path);

  const shown = GRIDS.filter(gr => state.grid === "all" || gr.key === state.grid);
  const sq = g.append("g");
  for (const gr of shown) {
    const s = sq.append("g").attr("class", `sqs ${gr.key}`).style("--c", gr.color);
    s.selectAll("path").data(SQUARES[gr.key]).join("path").attr("class", "sq").attr("d", d => path(d.geo))
      .attr("stroke-dasharray", gr.dash || null);
    s.selectAll("text").data(SQUARES[gr.key]).join("text").attr("class", "sql")
      .attr("x", d => proj(d.centre)[0]).attr("y", d => proj(d.centre)[1] + 5).text(d => d.label);
  }

  // Each reference: a line from where its grid puts it to the town the entry names
  const refs = REFS.filter(r => r.lonlat && (state.grid === "all" || r.key === state.grid));
  g.append("g").selectAll("line").data(refs.filter(r => r.town)).join("line").attr("class", "miss")
    .attr("x1", d => proj(d.lonlat)[0]).attr("y1", d => proj(d.lonlat)[1])
    .attr("x2", d => proj(d.town)[0]).attr("y2", d => proj(d.town)[1]);
  g.append("g").selectAll("circle.town").data(refs.filter(r => r.town)).join("circle").attr("class", "town")
    .attr("cx", d => proj(d.town)[0]).attr("cy", d => proj(d.town)[1]).attr("r", 2);
  g.append("g").selectAll("circle.ref").data(refs).join("circle")
    .attr("class", d => `ref${d.inferred ? " inferred" : ""}`).style("--c", d => BY_KEY[d.key].color)
    .attr("cx", d => proj(d.lonlat)[0]).attr("cy", d => proj(d.lonlat)[1]).attr("r", 4.5)
    .on("mousemove", (e, d) => showTip(e, d)).on("mouseleave", hideTip)
    .on("click", (e, d) => { const u = PAGE_URL(d.page); if (u) window.open(u, "_blank", "noopener"); });

  g.append("g").attr("class", "probe");
  drawProbe();

  k = 1;
  zoom = d3.zoom().scaleExtent([1, 24]).on("zoom", e => {
    k = e.transform.k;
    g.attr("transform", e.transform);
    scaleMarks();
  });
  svg.call(zoom);
  scaleMarks();
}

// Keep labels and markers the same size on screen as the map zooms
function scaleMarks() {
  const g = svg.select("g");
  g.selectAll(".sql").style("font-size", `${Math.min(24, 16 + 2 * k) / k}px`);
  g.selectAll("circle.ref").attr("r", 4.5 / k).style("stroke-width", 1.5 / k);
  g.selectAll("circle.town").attr("r", 2 / k);
  g.selectAll("line.miss").style("stroke-width", 1 / k);
  g.selectAll(".sq").style("stroke-width", 1 / k);
  g.selectAll(".probe path").attr("d", d3.symbol(d3.symbolStar, 160 / k / k)()).style("stroke-width", 1.2 / k);
  g.selectAll(".probe text").style("font-size", `${14.5 / k}px`).style("stroke-width", `${3 / k}px`);
}

// The decoder's reference, read on every grid that can read it
function drawProbe() {
  const pg = svg.select(".probe");
  if (pg.empty()) return;
  pg.selectAll("*").remove();
  for (const p of state.probe || []) {
    if (state.grid !== "all" && p.g.key !== state.grid) continue;
    const [x, y] = proj(p.lonlat);
    const s = pg.append("g").attr("transform", `translate(${x},${y})`).style("--c", p.g.color);
    s.append("path");
    s.append("text").attr("x", 0).attr("y", 0).attr("dy", "-0.8em").attr("text-anchor", "middle").text(p.g.short);
  }
  scaleMarks();
}

function showTip(e, d) {
  const gr = BY_KEY[d.key];
  const how = d.inferred ? `No square letter typed: square taken as the one nearest ${d.place}` : `Square ${d.ref.match(/^[A-Z]+/)[0]}`;
  tip.innerHTML = `<div class="v">${d.ref}</div>` +
    `<div class="k">${gr.name} · ${how}</div>` +
    `<div class="m">${d.date} · ${UNIT[d.unit] || d.unit} · ${d.kind === "station" ? d.station : d.text.slice(0, 120) + (d.text.length > 120 ? "…" : "")}</div>` +
    (d.dist != null ? `<div class="m">${d.dist.toFixed(1)} km from ${d.place}${d.offset ? ` + ${d.offset}` : ""}, the place the entry names</div>` : "") +
    (d.note ? `<div class="i">${d.note.length > 220 ? d.note.slice(0, 220) + "…" : d.note}</div>` : "") +
    `<div class="i">Click to open the page</div>`;
  tip.style.display = "block";
  const r = tip.getBoundingClientRect();
  tip.style.left = `${Math.min(e.clientX + 14, innerWidth - r.width - 8)}px`;
  tip.style.top = `${Math.min(e.clientY + 14, innerHeight - r.height - 8)}px`;
}
function hideTip() { tip.style.display = "none"; }

// The decoder: one reference read on every grid
function probe(text) {
  const out = document.getElementById("probe-out");
  const ref = text.trim();
  state.probe = null;
  if (!ref) { out.innerHTML = ""; drawProbe(); return; }
  const rows = GRIDS.map(g => ({ g, d: decode(g, ref) })).filter(r => r.d);
  if (!rows.length) {
    out.innerHTML = `<span class="muted">Type a letter and an even number of digits, e.g. <span class="mono">V-044572</span>, <span class="mono">Q-8623</span> or <span class="mono">rN 25</span>.</span>`;
    drawProbe(); return;
  }
  state.probe = rows.map(r => ({ g: r.g, lonlat: r.d.lonlat }));
  const near = ll => {
    const t = REFS.filter(r => r.town).map(r => ({ p: r.place, d: km(ll, r.town) })).sort((a, b) => a.d - b.d)[0];
    return t && t.d < 25 ? `${t.d.toFixed(0)} km from ${t.p}` : "";
  };
  out.innerHTML = `<table><thead><tr><th>Read on</th><th>Lands at</th><th>Nearest place in these records</th></tr></thead><tbody>` +
    rows.map(r => `<tr><td><span class="swatch" style="background:${r.g.color}"></span>${r.g.name}</td>` +
      `<td class="mono">${r.d.lonlat[1].toFixed(3)}°N ${r.d.lonlat[0].toFixed(3)}°E</td><td>${near(r.d.lonlat)}</td></tr>`).join("") +
    `</tbody></table><div class="muted">Precision: a ${r0(rows[0].d.cell)} square. Stars on the map.</div>`;
  drawProbe();
}
const r0 = u => (u >= 1000 ? `${u / 1000} km` : `${u} m`);

// Per grid: every reference, as typed, and how far it falls from the place its entry names
function buildTables() {
  const wrap = d3.select("#checks");
  for (const g of GRIDS) {
    const rows = REFS.filter(r => r.key === g.key && r.lonlat);
    const d = rows.filter(r => r.dist != null).map(r => r.dist);
    const sec = wrap.append("div").attr("class", "check");
    sec.append("h3").html(`<span class="swatch" style="background:${g.color}"></span>${g.name}`);
    sec.append("p").attr("class", "muted").text(`${rows.length} references, ${d.length} that name a town to check against. ` +
      `Median distance from the place: ${d3.median(d).toFixed(1)} km.`);
    const t = sec.append("table");
    t.append("thead").html("<tr><th>Date</th><th>Unit</th><th>As typed</th><th>Precision</th><th>Place the entry names</th><th>Apart</th></tr>");
    t.append("tbody").selectAll("tr").data(rows).join("tr").html(r =>
      `<td>${r.date}</td><td>${UNIT[r.unit] || r.unit}</td><td class="mono">${r.grid}${r.inferred ? " <span class=\"muted\">(square from the town)</span>" : ""}</td>` +
      `<td>${r0(r.cell)}</td>` +
      `<td>${r.town ? r.place + (r.offset ? `, ${r.offset}` : "") : `<span class="muted">${r.place ? "placed from this grid reference" : "none"}</span>`}</td>` +
      `<td class="num">${r.dist != null ? r.dist.toFixed(1) + " km" : ""}</td>`);
  }
  const left = REFS.filter(r => !r.lonlat);
  const sec = wrap.append("div").attr("class", "check");
  sec.append("h3").text("Not decoded");
  const t = sec.append("table");
  t.append("thead").html("<tr><th>Date</th><th>Unit</th><th>As typed</th><th>Place</th></tr>");
  t.append("tbody").selectAll("tr").data(left).join("tr").html(r =>
    `<td>${r.date}</td><td>${UNIT[r.unit] || r.unit}</td><td class="mono">${r.grid}</td><td>${r.place || ""}</td>`);
}
