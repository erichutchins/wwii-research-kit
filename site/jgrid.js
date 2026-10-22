// Japanese position codes explainer: the kana grid keys rebuilt so far (reference/jgrid/keys.csv), drawn as
// the 20' column and row strips each key's letters name, with the anchors that placed them
// (reference/jgrid/anchors.csv). The decoding is tools/jgrid.py's; method and evidence in guides/JAPANESE-GRID.md.

const SIDE = 1 / 3;  // degrees: a square is 20' x 20'
const KEYS = [
  { key: "formosa-1944", name: "Formosa 1944", suffix: "へ", color: "var(--series-track)",
    what: "base point 鵝鑾鼻 (Garanbi), 10-27 Oct 1944", box: [[120.4, 14.2], [129.4, 25.0]] },
  { key: "leyte-1944", name: "Manila 1944", suffix: "ヤ", color: "var(--series-attack)",
    what: "base point Manila or Cavite, 24-28 Oct 1944", box: [[120.4, 11.6], [127.4, 15.6]] },
  { key: "okinawa-1945", name: "Okinawa 1945", suffix: "", color: "var(--series-air)",
    what: "Kyushu-Okinawa, April 1945, no suffix", box: [[127.4, 26.2], [131.2, 29.6]] },
];
const BY_KEY = Object.fromEntries(KEYS.map(k => [k.key, k]));
const BY_SUFFIX = { "へ": "formosa-1944", "ヤ": "leyte-1944" };

// Base points the suffixes name, and Kanoya, where the April 1945 searches flew from
const BASES = [
  { name: "鵝鑾鼻 Garanbi (へ)", lonlat: [120.85, 21.90] },
  { name: "Manila (ヤ)", lonlat: [120.98, 14.58] },
  { name: "Kanoya", lonlat: [130.85, 31.40] },
];

// Where the flight itself put a contact (sortie pages of JACAR C13120398700), for the chart boxes it can be
// checked against: the "How far to trust the chart" table in guides/JAPANESE-GRID.md
const FLIGHT = {
  F1: { lonlat: [123.12, 22.92], text: "F13's track sketch: about 140 nm out on its 064° line" },
  F8: { lonlat: [123.53, 22.12], text: "F18 on its 085° line at 0045" },
  F2: { lonlat: [125.50, 22.10], text: "F19's own signal at 0100: N22°06′ E125°30′" },
  F11: { lonlat: [125.22, 18.58], text: "KEA95: end of its 129° 290 nm leg, plus the 50 km radar range" },
  M5: { lonlat: [127.00, 13.17], text: "KEA95's track sketch: \"E127° N13°10′\" at 0325" },
};

const STYLE = { drawn: null, good: null, probable: "5 3", tentative: "1.5 3" };
const deg = t => { const [d, m] = t.slice(0, -1).split("-"); const v = +d + +m / 60; return /[SW]$/.test(t) ? -v : v; };
const dm = (v, p) => `${Math.floor(v + 1e-9)}°${String(Math.round((v + 1e-9) % 1 * 60)).padStart(2, "0")}′${p}`;
const nm = (a, b) => d3.geoDistance(a, b) * 3440.1;

// ── Decoding (as tools/jgrid.py) ───────────────────────────────────────────
let LETTERS = {};   // key -> { col: {kana: row}, row: {kana: row} }
function decode(code, key) {
  const k = LETTERS[key] || { col: {}, row: {} }, c = k.col[code[0]], r = k.row[code[1]];
  return {
    c, r,
    w: c ? deg(c.edge) : null, s: r ? deg(r.edge) : null,
  };
}
function splitCode(text) {
  const t = text.replace(/[\s「」()（）]/g, "");
  const last = t.at(-1);
  if (t.length >= 5 && BY_SUFFIX[last]) return { code: t.slice(0, -1), key: BY_SUFFIX[last], suffix: last };
  return { code: t, key: null, suffix: "" };
}

// ── Page ──────────────────────────────────────────────────────────────────────
const state = { view: "all", hot: null, probe: null };
let LAND, ANCHORS = [], proj, path, zoom, k = 1;
const svg = d3.select("#map"), tip = document.getElementById("tip");
const SOURCE_URL = s => {
  const m = /^jacar:(C\d+)$/.exec(s);
  if (m) return `https://www.jacar.archives.go.jp/das/image/${m[1]}`;
  if (/^sosho:/.test(s)) return "https://www.nids.mod.go.jp/military_history_search/";
  return null;
};
const SOURCE_NAME = s => /^sosho:0*(\d+)/.test(s) ? `戦史叢書 vol. ${/^sosho:0*(\d+)/.exec(s)[1]}` : s.replace(/^jacar:/, "JACAR ");

Promise.all([
  d3.csv(REFERENCE + "jgrid/keys.csv"), d3.csv(REFERENCE + "jgrid/anchors.csv"),
  d3.json("https://cdn.jsdelivr.net/npm/world-atlas@2/land-50m.json"),
]).then(([keys, anchors, world]) => {
  LAND = topojson.feature(world, world.objects.land);
  for (const r of keys) {
    (LETTERS[r.key] ??= { col: {}, row: {} })[r.axis][r.letter] = r;
  }
  for (const kd of KEYS) {
    const L = LETTERS[kd.key];
    const cols = Object.values(L.col).map(r => deg(r.edge)), rows = Object.values(L.row).map(r => deg(r.edge));
    // Strips run across the extent of the other axis's known letters, a square either side
    kd.extent = [[d3.min(cols) - SIDE, d3.min(rows) - SIDE], [d3.max(cols) + 2 * SIDE, d3.max(rows) + 2 * SIDE]];
  }
  ANCHORS = anchors.filter(a => a.lat && BY_KEY[a.key]).map(a => {
    const lonlat = [+a.lon, +a.lat], ambiguous = a.code.includes(" or ");
    const d = ambiguous ? {} : decode(a.code, a.key);
    let off = null;
    if (d.c && d.r) {
      const dlat = Math.max(d.s - lonlat[1], 0, lonlat[1] - d.s - SIDE) * 60;
      const dlon = Math.max(d.w - lonlat[0], 0, lonlat[0] - d.w - SIDE) * 60 * Math.cos(lonlat[1] * Math.PI / 180);
      off = Math.hypot(dlat, dlon);
    }
    return { ...a, lonlat, ambiguous, d, off, flight: FLIGHT[a.id] };
  });
  buildControls();
  buildTables();
  new ResizeObserver(() => render()).observe(document.querySelector(".map-wrap"));
  document.getElementById("probe").addEventListener("input", () => probe());
  document.getElementById("probe-key").addEventListener("change", () => probe());
  probe();
});

function buildControls() {
  const opts = [{ key: "all", name: "All keys" }, ...KEYS];
  d3.select("#key-seg").selectAll("button").data(opts).join("button")
    .html(d => d.color ? `<span class="swatch" style="background:${d.color}"></span>${d.name}` : d.name)
    .on("click", (e, d) => { state.view = d.key; render(); });
  d3.select("#zin").on("click", () => svg.transition().call(zoom.scaleBy, 1.6));
  d3.select("#zout").on("click", () => svg.transition().call(zoom.scaleBy, 1 / 1.6));
  d3.select("#zreset").on("click", () => svg.transition().call(zoom.transform, d3.zoomIdentity));
}

function render() {
  const box = document.querySelector(".map-wrap").getBoundingClientRect(), W = box.width, H = box.height;
  d3.selectAll("#key-seg button").attr("aria-pressed", d => d.key === state.view);
  svg.attr("viewBox", `0 0 ${W} ${H}`);
  const focus = state.view === "all" ? [[119.6, 11.6], [131.4, 31.8]] : BY_KEY[state.view].box;
  proj = d3.geoMercator().fitExtent([[28, 20], [W - 20, H - 28]],
    { type: "MultiPoint", coordinates: [focus[0], focus[1], [focus[0][0], focus[1][1]], [focus[1][0], focus[0][1]]] });
  path = d3.geoPath(proj);
  svg.selectAll("*").remove();
  const g = svg.append("g");
  g.append("path").datum(d3.geoGraticule().extent([[110, 5], [140, 36]]).step([1, 1])()).attr("class", "graticule").attr("d", path);
  g.append("path").datum(LAND).attr("class", "land").attr("d", path);
  // Degree labels along the focus box's south and west edges
  const lab = g.append("g").attr("class", "deg");
  const step = proj([121, 20])[0] - proj([120, 20])[0] < 40 ? 2 : 1;
  for (let lon = Math.ceil(focus[0][0] / step) * step; lon <= focus[1][0]; lon += step)
    lab.append("text").attr("x", proj([lon, focus[0][1]])[0]).attr("y", proj([lon, focus[0][1]])[1]).attr("dy", "1.2em").attr("text-anchor", "middle").text(`${lon}°E`);
  for (let lat = Math.ceil(focus[0][1]); lat <= focus[1][1]; lat++)
    lab.append("text").attr("x", proj([focus[0][0], lat])[0]).attr("y", proj([focus[0][0], lat])[1]).attr("dx", "-0.3em").attr("dy", "0.35em").attr("text-anchor", "end").text(`${lat}°N`);

  const shown = KEYS.filter(kd => state.view === "all" || kd.key === state.view);
  const rect = (w, s, e, n) => ({ type: "Polygon", coordinates: [[[w, s], [w, n], [e, n], [e, s], [w, s]]] });
  for (const kd of shown) {
    const L = LETTERS[kd.key], [[w, s], [e, n]] = kd.extent;
    const kg = g.append("g").attr("class", "key").style("--c", kd.color);
    const strips = [
      ...Object.values(L.col).map(r => ({ r, geo: rect(deg(r.edge), s, deg(r.edge) + SIDE, n), at: [deg(r.edge) + SIDE / 2, n] })),
      ...Object.values(L.row).map(r => ({ r, geo: rect(w, deg(r.edge), e, deg(r.edge) + SIDE), at: [w, deg(r.edge) + SIDE / 2] })),
    ];
    kg.selectAll("path.strip").data(strips).join("path").attr("class", "strip").attr("d", d => path(d.geo))
      .attr("stroke-dasharray", d => STYLE[d.r.confidence]);
    kg.selectAll("text.sl").data(strips).join("text").attr("class", d => `sl ${d.r.axis}`)
      .attr("x", d => proj(d.at)[0]).attr("y", d => proj(d.at)[1]).text(d => d.r.letter)
      .on("mousemove", (ev, d) => showStripTip(ev, d.r, kd)).on("mouseleave", hideTip);
    // Every square both letters are known for, labelled with its two kana when zoomed in
    const cells = [];
    for (const c of Object.values(L.col)) for (const r of Object.values(L.row))
      cells.push({ code: c.letter + r.letter, at: [deg(c.edge) + SIDE / 2, deg(r.edge) + SIDE / 2] });
    kg.selectAll("text.cl").data(cells).join("text").attr("class", "cl")
      .attr("x", d => proj(d.at)[0]).attr("y", d => proj(d.at)[1]).text(d => d.code);
  }

  g.append("g").attr("class", "hotsq");
  const bases = g.append("g");
  for (const b of BASES) {
    const [x, y] = proj(b.lonlat);
    bases.append("path").attr("class", "base").attr("transform", `translate(${x},${y})`);
    bases.append("text").attr("class", "base-label").attr("x", x).attr("y", y).text(b.name);
  }

  const anchors = ANCHORS.filter(a => state.view === "all" || a.key === state.view);
  const fl = anchors.filter(a => a.flight);
  g.append("g").selectAll("line").data(fl).join("line").attr("class", "miss")
    .attr("x1", d => proj(d.lonlat)[0]).attr("y1", d => proj(d.lonlat)[1])
    .attr("x2", d => proj(d.flight.lonlat)[0]).attr("y2", d => proj(d.flight.lonlat)[1]);
  g.append("g").selectAll("circle.flight").data(fl).join("circle").attr("class", "flight")
    .attr("cx", d => proj(d.flight.lonlat)[0]).attr("cy", d => proj(d.flight.lonlat)[1])
    .on("mousemove", (e, d) => showFlightTip(e, d)).on("mouseleave", hideTip);
  g.append("g").selectAll("circle.anchor").data(anchors).join("circle")
    .attr("class", d => `anchor${d.d.c && d.d.r ? "" : " open"}`).style("--c", d => BY_KEY[d.key].color)
    .attr("cx", d => proj(d.lonlat)[0]).attr("cy", d => proj(d.lonlat)[1])
    .on("mousemove", (e, d) => { showTip(e, d); hot(d); }).on("mouseleave", () => { hideTip(); hot(null); })
    .on("click", (e, d) => { const u = SOURCE_URL(d.source); if (u) window.open(u, "_blank", "noopener"); });

  g.append("g").attr("class", "probe");
  drawProbe();

  k = 1;
  zoom = d3.zoom().scaleExtent([1, 30]).on("zoom", e => { k = e.transform.k; g.attr("transform", e.transform); scaleMarks(); });
  svg.call(zoom);
  scaleMarks();
}

// Keep marks the same size on screen as the map zooms; square labels appear once a square is big enough
function scaleMarks() {
  const g = svg.select("g"), px = proj ? proj([125, 20 + SIDE])[1] - proj([125, 20])[1] : 0;
  const side = Math.abs(px) * k;
  g.selectAll(".land, .graticule").style("stroke-width", 0.6 / k);
  g.selectAll(".strip").style("stroke-width", 1 / k);
  g.selectAll(".sl").style("font-size", `${Math.min(17, Math.max(10, side * 0.8)) / k}px`).style("stroke-width", `${3 / k}px`);
  g.selectAll(".sl.col").attr("dy", `${-0.4}em`);
  g.selectAll(".sl.row").attr("dx", `${-0.35}em`).attr("dy", "0.35em");
  g.selectAll(".cl").style("display", side > 26 ? null : "none").style("font-size", `${Math.min(16, side * 0.4) / k}px`);
  g.selectAll(".deg text").style("font-size", `${13 / k}px`);
  g.selectAll(".base").attr("d", d3.symbol(d3.symbolTriangle, 70 / k / k)()).style("stroke-width", 1.2 / k);
  g.selectAll(".base-label").style("font-size", `${13 / k}px`).attr("dx", `${0.8}em`).attr("dy", "0.35em").style("stroke-width", `${3 / k}px`);
  g.selectAll("circle.anchor").attr("r", 4.5 / k).style("stroke-width", 1.5 / k);
  g.selectAll("circle.flight").attr("r", 3 / k).style("stroke-width", 1.2 / k);
  g.selectAll("line.miss").style("stroke-width", 1.2 / k);
  g.selectAll(".hotsq path, .probe path").style("stroke-width", 2.5 / k);
}

// The square an anchor's code names, while the pointer is on it
function hot(a) {
  const hg = svg.select(".hotsq");
  hg.selectAll("*").remove();
  if (!a || !a.d.c || !a.d.r) return;
  const { w, s } = a.d;
  hg.append("path").style("--c", BY_KEY[a.key].color)
    .attr("d", path({ type: "Polygon", coordinates: [[[w, s], [w, s + SIDE], [w + SIDE, s + SIDE], [w + SIDE, s], [w, s]]] }));
  scaleMarks();
}

function showTip(e, a) {
  const kd = BY_KEY[a.key], d = a.d;
  const col = d.c ? `column ${a.code[0]} ${dm(d.w, "E")}–${dm(d.w + SIDE, "E")} (${d.c.confidence})` : `column ${a.code[0]} not placed`;
  const row = d.r ? `row ${a.code[1]} ${dm(d.s, "N")}–${dm(d.s + SIDE, "N")} (${d.r.confidence})` : `row ${a.code[1]} not placed`;
  tip.innerHTML = `<div class="v">${a.code}${a.ambiguous ? "" : kd.suffix} <span class="k">${a.id}</span></div>` +
    `<div class="k">${kd.name} key · ${a.date}${a.time ? " " + a.time : ""}</div>` +
    `<div class="m">${a.stated}</div>` +
    `<div class="m">Measured ${dm(a.lonlat[1], "N")} ${dm(a.lonlat[0], "E")}</div>` +
    (a.ambiguous ? "" : `<div class="m">${col}<br>${row}</div>`) +
    (a.off != null ? `<div class="m">${a.off === 0 ? "Inside the square its code names" : `${a.off.toFixed(0)} nm outside the square its code names`}</div>` : "") +
    (a.flight ? `<div class="m">The flight put it ${nm(a.lonlat, a.flight.lonlat).toFixed(0)} nm away: ${a.flight.text}</div>` : "") +
    (a.note ? `<div class="i">${a.note}</div>` : "") +
    `<div class="i">${SOURCE_NAME(a.source)}${a.page ? " " + a.page : ""}${SOURCE_URL(a.source) ? " · click to open" : ""}</div>`;
  place(e);
}
function showFlightTip(e, a) {
  tip.innerHTML = `<div class="v">${a.code}${BY_KEY[a.key].suffix}, by the flight's own account</div>` +
    `<div class="k">${a.flight.text}</div><div class="m">${nm(a.lonlat, a.flight.lonlat).toFixed(0)} nm from where the chart plots it (${a.id})</div>`;
  place(e);
}
function showStripTip(e, r, kd) {
  const v = deg(r.edge);
  const span = r.axis === "col" ? `${dm(v, "E")}–${dm(v + SIDE, "E")}` : `${dm(v, "N")}–${dm(v + SIDE, "N")}`;
  tip.innerHTML = `<div class="v">${r.axis === "col" ? "Column" : "Row"} ${r.letter}: ${span}</div>` +
    `<div class="k">${kd.name} key · ${r.confidence}</div><div class="i">${r.evidence}</div>`;
  place(e);
}
function place(e) {
  tip.style.display = "block";
  const r = tip.getBoundingClientRect();
  tip.style.left = `${Math.min(e.clientX + 14, innerWidth - r.width - 8)}px`;
  tip.style.top = `${Math.min(e.clientY + 14, innerHeight - r.height - 8)}px`;
}
function hideTip() { tip.style.display = "none"; }

// ── Decoder ───────────────────────────────────────────────────────────────────
function probe() {
  const out = document.getElementById("probe-out"), sel = document.getElementById("probe-key");
  const { code, key: fromSuffix, suffix } = splitCode(document.getElementById("probe").value);
  const key = fromSuffix || sel.value;
  if (fromSuffix) sel.value = fromSuffix;
  state.probe = null;
  if (code.length < 2) { out.innerHTML = `<span class="muted">Type at least the two kana, e.g. <span class="mono">ホク三テへ</span>.</span>`; drawProbe(); return; }
  const d = decode(code, key), kd = BY_KEY[key];
  state.probe = { key, d };
  const col = d.c ? `<b>${dm(d.w, "E")}</b> to ${dm(d.w + SIDE, "E")} <span class="muted">(${d.c.confidence})</span>` : `<span class="muted">column ${code[0]} not placed in this key</span>`;
  const row = d.r ? `<b>${dm(d.s, "N")}</b> to ${dm(d.s + SIDE, "N")} <span class="muted">(${d.r.confidence})</span>` : `<span class="muted">row ${code[1]} not placed in this key</span>`;
  out.innerHTML = `<div class="anatomy"><span class="a">${code[0]}</span><span class="b">${code[1]}</span><span class="c">${code.slice(2)}</span><span class="muted">${suffix}</span></div>` +
    `<table><tbody><tr><td>Key</td><td><span class="swatch" style="background:${kd.color}"></span>${kd.name} <span class="muted">(${kd.what}${fromSuffix ? `; chosen by the suffix ${suffix}` : ""})</span></td></tr>` +
    `<tr><td>Column ${code[0]}</td><td>${col}</td></tr><tr><td>Row ${code[1]}</td><td>${row}</td></tr>` +
    (d.c && d.r ? `<tr><td>Square</td><td>centre ${dm(d.s + SIDE / 2, "N")} ${dm(d.w + SIDE / 2, "E")}, about 20 × 19 nm</td></tr>` : "") +
    `<tr><td>${code.slice(2) || "—"}</td><td class="muted">the point within the square: not decoded</td></tr></tbody></table>`;
  drawProbe();
}
function drawProbe() {
  const pg = svg.select(".probe");
  if (pg.empty()) return;
  pg.selectAll("*").remove();
  const p = state.probe;
  if (!p || (state.view !== "all" && state.view !== p.key)) return;
  const kd = BY_KEY[p.key], [[w, s], [e, n]] = kd.extent, d = p.d;
  const geo = d.c && d.r ? [d.w, d.s, d.w + SIDE, d.s + SIDE] : d.c ? [d.w, s, d.w + SIDE, n] : d.r ? [w, d.s, e, d.s + SIDE] : null;
  if (!geo) return;
  const [x0, y0, x1, y1] = geo;
  pg.append("path").style("--c", kd.color).attr("class", d.c && d.r ? "full" : "partial")
    .attr("d", path({ type: "Polygon", coordinates: [[[x0, y0], [x0, y1], [x1, y1], [x1, y0], [x0, y0]]] }));
  scaleMarks();
}

// ── The keys so far ──────────────────────────────────────────────────────────
function buildTables() {
  const wrap = d3.select("#keys");
  for (const kd of KEYS) {
    const L = LETTERS[kd.key];
    const sec = wrap.append("div").attr("class", "keytab");
    sec.append("h3").html(`<span class="swatch" style="background:${kd.color}"></span>${kd.name}` +
      `${kd.suffix ? ` <span class="mono">(…${kd.suffix})</span>` : ""} <span class="muted">${kd.what}</span>`);
    for (const [axis, label, p] of [["col", "Columns, west to east", "E"], ["row", "Rows, south to north", "N"]]) {
      const rs = Object.values(L[axis]).sort((a, b) => deg(a.edge) - deg(b.edge));
      const line = sec.append("div").attr("class", "letters");
      line.append("span").attr("class", "muted").text(label);
      // Gaps between known letters show as dots, one per unplaced 20' strip
      let prev = null;
      for (const r of rs) {
        const v = deg(r.edge);
        if (prev != null) for (let i = Math.round((v - prev) / SIDE) - 1; i > 0; i--) line.append("span").attr("class", "gap").text("·");
        line.append("span").attr("class", `lt ${r.confidence}`).style("--c", kd.color)
          .attr("title", `${r.letter}: ${dm(v, p)} (${r.confidence}). ${r.evidence}`)
          .html(`<b>${r.letter}</b><small>${dm(v, p)}</small>`);
        prev = v;
      }
    }
  }
}
