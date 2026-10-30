// German position systems explainer: the Kriegsmarine's naval grid squares in the Mediterranean
// (reference/naval-grid/{squares,anchors}.csv) and the German Army's reference points in Italy, 1944
// (reference/bezugspunkte/{ausgabe4,feb1944,jan1944,anchors}.csv). The decoding is ported from tools/naval_grid.py and
// tools/bezugspunkt.py; method, evidence and what's missing in guides/NAVAL-GRID.md and guides/BEZUGSPUNKTE.md.

const tip = document.getElementById("tip");

// ── Sources: the citation forms of records/SOURCES.yml, turned into links ─────────
const SRC = [
  // nara-t1022-2099: the catalog's object page
  [/^t1022-2099\/f(\d{4})$/, m => `https://catalog.archives.gov/id/337684135?objectPage=${+m[1]}`],
  // nara-t312: the frame JPEG
  [/^t312-(\d{4})\/f(\d{4})$/, m => `https://catalog.archives.gov/medialz/dc-metro/rg-242/12007587/T312-${m[1]}/T312-${m[1]}-${m[2]}.jpg`],
  // nara-t314: the frame TIFF
  [/^t314-(\d{4})\/f(\d{4})$/, m => `https://catalog.archives.gov/medialz/dc-metro/rg-242/12004195/T314/T314-${m[1]}/T314-${m[1]}-0${m[2]}.tif`],
  // skl-ktb (vols. 43-52, 1943) and skl-ktb-1944 (53-): the volume on the Internet Archive
  [/^skl:(\d+)\/p(\d+)$/, m => `https://archive.org/details/wardiarygermann${m[1]}${+m[1] >= 53 ? 1944 : 1943}germ`],
];
const srcUrl = s => { for (const [re, f] of SRC) { const m = re.exec(s.trim()); if (m) return f(m); } return null; };
const srcLink = s => { const u = srcUrl(s); return u ? `<a href="${u}" target="_blank" rel="noopener">${s}</a>` : s; };
const firstSrc = list => list.split(";").map(s => s.trim()).find(srcUrl);
const esc = s => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

// ── A zoomable map (as jgrid.html's): the page projects once, the zoom moves one group, and the marks keep their
// size on screen by dividing by the zoom (scale(g, k)) ─────────────────────────────────────────────────────────
function makeMap({ svg: sel, wrap: wsel, focus, units, draw, scale, max = 40 }) {
  const svg = d3.select(sel), wrap = document.querySelector(wsel);
  const m = { svg, proj: null, path: null, g: null, k: 1, ruler: null, zoom: null };
  m.render = () => {
    const { width: W, height: H } = wrap.getBoundingClientRect();
    if (!W || !H) return;
    svg.attr("viewBox", `0 0 ${W} ${H}`);
    m.W = W; m.H = H;
    m.proj = d3.geoMercator().fitExtent([[34, 20], [W - 20, H - 26]],
      { type: "MultiPoint", coordinates: [focus[0], focus[1], [focus[0][0], focus[1][1]], [focus[1][0], focus[0][1]]] });
    m.path = d3.geoPath(m.proj);
    svg.selectAll(":scope > g").remove();
    m.g = svg.append("g");
    draw(m);
    m.k = 1;
    m.ruler = m.ruler || scaleBar(wrap, { units, at: "bottom-left" });
    m.zoom = d3.zoom().scaleExtent([1, max]).on("zoom", e => {
      m.k = e.transform.k; m.g.attr("transform", e.transform);
      m.ruler.update(p => m.proj.invert(e.transform.invert(p)));
      scale(m, m.k);
    });
    svg.call(m.zoom).on("dblclick.zoom", null);
    m.ruler.update(p => m.proj.invert(p));
    scale(m, 1);
  };
  // zoom so that a [lon, lat] box fills about half the map
  m.zoomTo = (box, fill = 0.5) => {
    const [x0, y0] = m.proj([box[0][0], box[1][1]]), [x1, y1] = m.proj([box[1][0], box[0][1]]);
    const k = Math.max(1, Math.min(max, fill / Math.max((x1 - x0) / m.W, (y1 - y0) / m.H)));
    const t = d3.zoomIdentity.translate(m.W / 2 - k * (x0 + x1) / 2, m.H / 2 - k * (y0 + y1) / 2).scale(k);
    svg.transition().duration(600).call(m.zoom.transform, t);
  };
  wrap.querySelectorAll(".zoom-btns button").forEach(b => b.addEventListener("click", () => {
    const z = b.dataset.z;
    if (z === "reset") svg.transition().call(m.zoom.transform, d3.zoomIdentity);
    else svg.transition().call(m.zoom.scaleBy, z === "in" ? 1.6 : 1 / 1.6);
  }));
  new ResizeObserver(() => m.render()).observe(wrap);
  return m;
}
// stroke widths, dashes, radii and type that stay the same on screen as the map zooms
function px(sel, k, { sw, dash, r, font }) {
  if (sw != null) sel.style("stroke-width", `${sw / k}px`);
  if (dash) sel.style("stroke-dasharray", typeof dash === "function" ? function (d) { const v = dash(d, this); return v ? v.split(" ").map(x => x / k).join(" ") : null; } : dash.split(" ").map(x => x / k).join(" "));
  if (r != null) sel.attr("r", r / k);
  if (font != null) sel.style("font-size", `${font / k}px`);
}
function graticule(m, ext, step, fmtLon, fmtLat) {
  m.g.append("path").datum(d3.geoGraticule().extent(ext).step([step, step])()).attr("class", "graticule").attr("d", m.path);
}
function degLabels(m, focus, step, latStep = step) {
  const lab = m.g.append("g").attr("class", "deg");
  const f = (v, p, n) => `${Math.abs(v)}°${v < 0 ? n : p}`;
  for (let lon = Math.ceil(focus[0][0] / step) * step; lon <= focus[1][0]; lon += step)
    lab.append("text").attr("x", m.proj([lon, focus[0][1]])[0]).attr("y", m.proj([lon, focus[0][1]])[1]).attr("dy", "1.2em").attr("text-anchor", "middle").text(f(+lon.toFixed(2), "E", "W"));
  for (let lat = Math.ceil(focus[0][1] / latStep) * latStep; lat <= focus[1][1]; lat += latStep)
    lab.append("text").attr("x", m.proj([focus[0][0], lat])[0]).attr("y", m.proj([focus[0][0], lat])[1]).attr("dx", "-0.3em").attr("dy", "0.35em").attr("text-anchor", "end").text(f(+lat.toFixed(2), "N", "S"));
}
function place(e) {
  tip.style.display = "block";
  const r = tip.getBoundingClientRect();
  tip.style.left = `${Math.min(e.clientX + 14, innerWidth - r.width - 8)}px`;
  tip.style.top = `${Math.min(e.clientY + 14, innerHeight - r.height - 8)}px`;
}
const hideTip = () => { tip.style.display = "none"; };
const rect = (w, s, e, n) => ({ type: "Polygon", coordinates: [[[w, s], [w, n], [e, n], [e, s], [w, s]]] });

// ══ The naval grid (tools/naval_grid.py) ═════════════════════════════════════════════════════════════════════
const ROW = 54, COL = 72;   // minutes: a two-digit square's height and width
const NM_PER_RAD = 180 * 60 / Math.PI;   // a nautical mile as a minute of arc, as naval_grid.py's sphere
const mins = t => { const [d, m] = t.slice(0, -1).split("-"); const v = +d * 60 + +m; return /[SW]$/.test(t) ? -v : v; };
const dm = (v, p, n) => { const a = Math.abs(v), mm = +(a % 60).toFixed(1); return `${Math.floor(a / 60)}°${String(mm).padStart(2, "0")}′${v >= 0 ? p : n}`; };
const METHOD = {
  measured: { name: "measured", what: "edges measured on a full-scale chart's graticule", dash: null },
  "measured-lon": { name: "columns measured", what: "columns measured on a full-scale sheet; rows carried on the lattice measured elsewhere (that sheet has no latitude scale)", dash: null },
  read: { name: "read", what: "numbers read on the small-scale (Klein) sheets; edges from the lattice", dash: "5 3" },
  assumed: { name: "assumed", what: "assumed regular: not seen on a chart", dash: "1.5 3" },
};
let BLOCKS = new Map();

function nParse(code) {
  const m = /^\s*([A-Z]{2})\s*([0-9]{1,4})\s*$/.exec(code.toUpperCase());
  if (!m) throw new Error("expected two letters and 1–4 digits, e.g. CJ 9472");
  const digits = m[2].replace(/0+$/, "");
  if (digits.includes("0")) throw new Error("a 0 before a non-zero digit is not a keypad position");
  return [m[1], digits];
}
function nDecode(code) {
  const [sq, digits] = nParse(code);
  if (!digits) throw new Error(`${sq}: a large square alone is not decoded (its outline is irregular here)`);
  const blk = BLOCKS.get(sq + digits[0]);
  if (!blk) throw new Error(`${sq} ${digits[0]}: not digitized (large squares so far: ${[...new Set([...BLOCKS.values()].map(b => b.square))].join(", ")})`);
  if (digits.length > 1 && !blk.present.includes(digits[1]))
    throw new Error(`${sq} ${digits.slice(0, 2)}: not on the chart (block ${sq} ${digits[0]} has only ${[...blk.present].map(d => digits[0] + d).join(", ")})`);
  let n = mins(blk.lat_n), w = mins(blk.lon_w), h = 3 * ROW, wd = 3 * COL;
  const levels = [{ n, s: n - h, w, e: w + wd, code: `${sq} ${digits[0]}` }];
  for (let i = 1; i < digits.length; i++) {
    const k = +digits[i] - 1;
    h /= 3; wd /= 3; n -= Math.floor(k / 3) * h; w += (k % 3) * wd;
    levels.push({ n, s: n - h, w, e: w + wd, code: `${sq} ${digits.slice(0, i + 1)}` });
  }
  return { sq, digits, blk, n, s: n - h, w, e: w + wd, levels, lat: (n - h / 2) / 60, lon: (w + wd / 2) / 60 };
}
const nmBetween = (a, b) => d3.geoDistance(a, b) * NM_PER_RAD;

let NAV = { anchors: [], probe: null }, nmap;
const NFOCUS = [[-5.5, 30.2], [37, 46.2]];

function nDraw(m) {
  const { g, proj, path } = m;
  const defs = g.append("defs");
  // the patterns are redrawn to the zoom in nScale (patternTransform), so their lines stay fine
  defs.append("pattern").attr("id", "hatch-lon").attr("patternUnits", "userSpaceOnUse").attr("width", 5).attr("height", 5)
    .append("path").attr("d", "M2.5,0V5").attr("stroke", "var(--series-track)").attr("stroke-opacity", 0.35);
  defs.append("pattern").attr("id", "hatch-assumed").attr("patternUnits", "userSpaceOnUse").attr("width", 5).attr("height", 5)
    .append("path").attr("d", "M2.5,0V5").attr("stroke", "var(--series-track)").attr("stroke-opacity", 0.35);
  graticule(m, [[-10, 26], [42, 50]], 5);
  g.append("path").datum(LAND50).attr("class", "land").attr("d", path);
  degLabels(m, NFOCUS, 5);

  const blocks = [...BLOCKS.values()];
  // the large squares' letters, faint, at the middle of their blocks
  const bySq = d3.group(blocks, b => b.square);
  g.append("g").selectAll("text").data([...bySq]).join("text").attr("class", "lsq")
    .attr("x", ([, bs]) => d3.mean(bs, b => proj(b.c)[0])).attr("y", ([, bs]) => d3.mean(bs, b => proj(b.c)[1])).text(([s]) => s);
  // two-digit squares inside each block (the ones the chart prints)
  const sq2 = blocks.flatMap(b => [...b.present].map(d => {
    const k = +d - 1, n = b.n - Math.floor(k / 3) * ROW, w = b.w + (k % 3) * COL;
    return { b, d, geo: rect(w / 60, (n - ROW) / 60, (w + COL) / 60, n / 60), c: [(w + COL / 2) / 60, (n - ROW / 2) / 60] };
  }));
  g.append("g").selectAll("path").data(sq2).join("path").attr("class", "sq2").attr("d", d => path(d.geo));
  g.append("g").attr("class", "sl2g").selectAll("text").data(sq2).join("text").attr("class", "sl2")
    .attr("x", d => proj(d.c)[0]).attr("y", d => proj(d.c)[1]).text(d => d.b.block + d.d);
  // the blocks, each a link to its chart frame
  const bl = g.append("g").selectAll("a").data(blocks).join("a")
    .attr("href", b => srcUrl(firstSrc(b.frames))).attr("target", "_blank").attr("rel", "noopener")
    .on("mousemove", (e, b) => {
      const mt = METHOD[b.method] || { name: b.method, what: "" };
      tip.innerHTML = `<div class="v"><span class="mono">${b.square} ${b.block}</span></div>` +
        `<div class="k">${b.lat_s}–${b.lat_n}, ${b.lon_w}–${b.lon_e}</div>` +
        `<div class="m"><i>${mt.name}</i>: ${mt.what}</div>` +
        (b.present !== "123456789" ? `<div class="m">two-digit squares on the chart: ${[...b.present].map(d => b.block + d).join(", ")}</div>` : "") +
        (b.note ? `<div class="i">${esc(b.note)}</div>` : "") +
        `<div class="i">${b.frames} · click to open the frame</div>`;
      place(e);
    }).on("mouseleave", hideTip);
  bl.append("path").attr("class", b => `blk ${b.method}`).attr("d", b => path(rect(b.w / 60, b.s / 60, b.e / 60, b.n / 60)));
  g.append("g").selectAll("text").data(blocks).join("text").attr("class", "bl")
    .attr("x", b => proj([b.w / 60, b.n / 60])[0]).attr("y", b => proj([b.w / 60, b.n / 60])[1]).text(b => `${b.square} ${b.block}`);

  // the anchors: the place named, the cell decoded, joined
  const an = NAV.anchors.filter(a => a.d);
  g.append("g").selectAll("line").data(an.filter(a => a.at)).join("line").attr("class", "miss")
    .attr("x1", a => proj(a.at)[0]).attr("y1", a => proj(a.at)[1])
    .attr("x2", a => proj([a.d.lon, a.d.lat])[0]).attr("y2", a => proj([a.d.lon, a.d.lat])[1]);
  const ag = g.append("g").selectAll("a").data(an).join("a")
    .attr("href", a => srcUrl(a.source)).attr("target", "_blank").attr("rel", "noopener")
    .on("mousemove", (e, a) => { nAnchorTip(a); place(e); }).on("mouseleave", hideTip);
  ag.append("path").attr("class", "cell").attr("d", a => path(rect(a.d.w / 60, a.d.s / 60, a.d.e / 60, a.d.n / 60)));
  ag.filter(a => a.at).append("circle").attr("class", "stated").attr("cx", a => proj(a.at)[0]).attr("cy", a => proj(a.at)[1]);

  g.append("g").attr("class", "probe");
  nDrawProbe();
}
function nAnchorTip(a) {
  tip.innerHTML = `<div class="v"><span class="mono">${a.code}</span> <span class="k">${a.id}</span></div>` +
    `<div class="k">${a.date} · ${a.kind === "context" ? "context: no place stated" : a.kind === "named-distance" ? "place and distance named" : "place named, no distance"}</div>` +
    `<div class="m typed">"${esc(a.stated)}"</div>` +
    `<div class="m">decodes to ${dm(a.d.lat * 60, "N", "S")} ${dm(a.d.lon * 60, "E", "W")}${a.err != null ? `, ${a.err.toFixed(1)} nm from the place named` : ""}</div>` +
    `<div class="i">${a.source} · click to open the diary</div>`;
}
function nScale(m, k) {
  const g = m.g;
  g.selectAll("pattern").attr("patternTransform", function () { return `${this.id === "hatch-assumed" ? "rotate(45) " : ""}scale(${1 / k})`; });
  g.selectAll("pattern path").style("stroke-width", "1px");
  px(g.selectAll(".land, .graticule"), k, { sw: 0.6 });
  px(g.selectAll(".blk"), k, { sw: 1.2, dash: b => METHOD[b.method]?.dash });
  px(g.selectAll(".sq2"), k, { sw: 0.6 });
  px(g.selectAll(".deg text"), k, { font: 12.5 });
  const sqpx = Math.abs(m.proj([10, 38])[1] - m.proj([10, 38.9])[1]) * k;   // a two-digit square's height on screen
  px(g.selectAll(".bl"), k, { font: 11.5, sw: 3 });
  g.selectAll(".bl").attr("dx", `${0.25}em`).attr("dy", "1.05em").style("display", sqpx > 10 ? null : "none");
  g.selectAll(".sl2g").style("display", sqpx > 34 ? null : "none");
  px(g.selectAll(".sl2"), k, { font: Math.min(14, sqpx * 0.3), sw: 3 });
  px(g.selectAll(".lsq"), k, { font: Math.min(64, Math.max(24, 18 * Math.sqrt(k))) });
  g.selectAll(".lsq").style("display", sqpx > 60 ? "none" : null);
  px(g.selectAll(".cell"), k, { sw: 1.2 });
  px(g.selectAll("circle.stated"), k, { r: 3.5, sw: 1 });
  px(g.selectAll(".miss"), k, { sw: 1.2, dash: "3 2" });
  px(g.selectAll(".probe .lvl"), k, { sw: 1.5 });
  px(g.selectAll(".probe .ctr"), k, { r: 3.5, sw: 1.2 });
  px(g.selectAll(".probe .crn"), k, { r: 2 });
  px(g.selectAll(".probe text"), k, { font: 13.5, sw: 3 });
}

function nProbe(zoom) {
  const out = document.getElementById("nprobe-out"), code = document.getElementById("nprobe").value;
  NAV.probe = null;
  try {
    const d = nDecode(code), mt = METHOD[d.blk.method] || { name: d.blk.method, what: "" };
    NAV.probe = d;
    const lv = d.levels, size = l => `${(l.n - l.s)}′ × ${(l.e - l.w)}′`;
    const rest = d.digits.slice(2);
    out.innerHTML = `<div class="anatomy"><span class="a">${d.sq}</span> <span class="b">${d.digits.slice(0, 2)}</span><span class="c">${rest}</span></div>` +
      `<table><tbody>` +
      lv.map((l, i) => `<tr><td><span class="mono">${l.code}</span></td><td>${i === 0 ? "block" : i === 1 ? "square printed on the chart" : i === 2 ? "third digit" : "fourth digit: the smallest cell"}` +
        `${i ? ` <span class="keypad" style="grid-template-columns:repeat(3,14px);gap:1px;margin:0 0 0 6px">${[1, 2, 3, 4, 5, 6, 7, 8, 9].map(n => `<span class="${n === +d.digits[i] ? "on" : ""}" style="font-size:9px;padding:0;line-height:12px">${n}</span>`).join("")}</span>` : ""}</td>` +
        `<td>${dm(l.s, "N", "S")}–${dm(l.n, "N", "S")}, ${dm(l.w, "E", "W")}–${dm(l.e, "E", "W")} <span class="muted">(${size(l)})</span></td></tr>`).join("") +
      `<tr><td>centre</td><td colspan="2"><b>${dm(d.lat * 60, "N", "S")} ${dm(d.lon * 60, "E", "W")}</b> <span class="muted">= ${d.lat.toFixed(3)}, ${d.lon.toFixed(3)}; the cell is about ${((d.n - d.s)).toFixed(0)} × ${((d.e - d.w) * Math.cos(d.lat * Math.PI / 180)).toFixed(0)} nm</span></td></tr>` +
      `<tr><td>block ${d.sq} ${d.blk.block}</td><td colspan="2"><i>${mt.name}</i>: ${mt.what} (${d.blk.frames.split(";").map(s => srcLink(s.trim())).join(", ")})</td></tr>` +
      `</tbody></table>`;
  } catch (err) {
    out.innerHTML = `<span class="err">${esc(err.message)}</span>`;
  }
  nDrawProbe();
  if (zoom && NAV.probe && nmap.zoom) { const b = NAV.probe.levels[0]; nmap.zoomTo([[b.w / 60, b.s / 60], [b.e / 60, b.n / 60]], 0.6); }
}
function nDrawProbe() {
  if (!nmap || !nmap.g) return;
  const pg = nmap.g.select(".probe");
  pg.selectAll("*").remove();
  const d = NAV.probe;
  if (!d) return;
  const { proj, path } = nmap;
  pg.selectAll("path").data(d.levels).join("path").attr("class", (l, i) => `lvl${i === d.levels.length - 1 ? " last" : ""}`)
    .attr("d", l => path(rect(l.w / 60, l.s / 60, l.e / 60, l.n / 60)));
  const corners = [[d.w, d.n], [d.e, d.n], [d.e, d.s], [d.w, d.s]].map(([x, y]) => [x / 60, y / 60]);
  pg.selectAll("circle.crn").data(corners).join("circle").attr("class", "crn").attr("cx", c => proj(c)[0]).attr("cy", c => proj(c)[1]);
  pg.append("circle").attr("class", "ctr").attr("cx", proj([d.lon, d.lat])[0]).attr("cy", proj([d.lon, d.lat])[1]);
  pg.append("text").attr("x", proj([d.e / 60, d.n / 60])[0]).attr("y", proj([d.e / 60, d.n / 60])[1]).attr("dx", "0.4em").attr("dy", "-0.3em")
    .text(`${d.sq} ${d.digits}`);
  nScale(nmap, nmap.k);
}

function nTables() {
  const t = d3.select("#nanchors");
  t.html(`<thead><tr><th>Code</th><th>Date</th><th>The diary's words</th><th>Place named</th><th>Decoded centre</th><th class="num">Error</th><th>Source</th></tr></thead>`);
  t.append("tbody").selectAll("tr").data(NAV.anchors).join("tr").html(a =>
    `<td><span class="mono">${a.code}</span></td><td style="white-space:nowrap">${a.date}</td>` +
    `<td><span class="typed">"${esc(a.stated)}"</span></td>` +
    `<td>${a.at ? `${(+a.lat).toFixed(2)}, ${(+a.lon).toFixed(2)}` : `<span class="muted">none: context only</span>`}<div class="muted" style="font-size:13.5px">${esc(a.note)}</div></td>` +
    `<td style="white-space:nowrap">${a.d ? `${a.d.lat.toFixed(2)}, ${a.d.lon.toFixed(2)}` : `<span class="muted">${esc(a.err_text)}</span>`}</td>` +
    `<td class="num" style="white-space:nowrap">${a.err != null ? `${a.err.toFixed(1)} nm` : "—"}<div class="muted" style="font-size:13.5px;text-align:right">${a.kind === "named-distance" ? "a point" : a.kind === "named-loose" ? "loose" : ""}</div></td>` +
    `<td>${srcLink(a.source)}</td>`);
}

// ══ The Army's reference points (tools/bezugspunkt.py) ═════════════════════════════════════════════════════════
const DIRS = {
  n: 0, "nördl": 0, nordl: 0, "nördlich": 0,
  no: 45, ne: 45, nordostw: 45, "nordöstl": 45, nordostl: 45,
  o: 90, e: 90, "östl": 90, ostw: 90, ostl: 90,
  so: 135, se: 135, "südostw": 135, "südöstl": 135, sudostw: 135,
  s: 180, "südl": 180, sudl: 180, "südlich": 180,
  sw: 225, "südwestl": 225, sudwestl: 225, "südw": 225,
  w: 270, westl: 270, wl: 270,
  nw: 315, nordwestl: 315, nordw: 315,
};
const EDGES = { nordrand: "north", "südrand": "south", sudrand: "south", ostrand: "east", westrand: "west" };
// February 1944: the handwritten cover name -> the printed block (read on Tenth Army's situation maps, t312-0090;
// guide: "The February 1944 edition"), and the 11 the reports add to the printed point number (written beside 9N on
// t312-0090/f0250). As in tools/bezugspunkt.py; applying the +11 to every block is an inference.
const COVER = { XXIII: "8Z", XXIX: "8P", XII: "8V", XXVII: "9N", VIII: "5V", XXXV: "6X", XXIV: "8N", V: "1T" };
const COVER_SURE = new Set(["XXIII", "XXIX", "XXVII", "VIII", "XII"]);
const COVER_OFFSET = 11;
// January 1944: one printed letter per block, points from 01 (t312-0084/f0440; guide: "January 1944"). Block D's letter
// isn't printed on the frames read (inferred by elimination); block C's north-east corner fits to only about 1.3 km.
const EDITION = {
  jan1944: { name: "January 1944", color: "var(--series-air)" },
  feb1944: { name: "February 1944", color: "var(--series-attack)" },
  "4": { name: "4th edition", color: "var(--series-track)" },
};
let POINTS = { "4": new Map(), feb1944: new Map(), jan1944: new Map() }, ARMY = { anchors: [], probe: null, view: "all" }, amap;
const AFOCUS = [[13.18, 41.22], [14.12, 41.68]];
const ALL_EDS = ["4", "jan1944", "feb1944"];   // drawing order; a town printed on several is named on the last shown
const ED_ORDER = ["jan1944", "feb1944", "4"];  // the order in time, for the buttons and the legend
const precKm = (p, ed) => ed === "jan1944" && p.block === "C" ? 1.3 : 0.4;
const padPt = (pt, ed) => ed === "jan1944" ? String(+pt).padStart(2, "0") : pt;

// The block picks the edition: one letter (not I, V, X, L) is January; a Roman numeral or a digit and a letter is
// February. V, X, I and L are both January letters and February cover names: the edition chosen (the report's date) decides.
const editionOf = (b, chosen) => /^[A-Z]$/.test(b) && (!/^[IVXL]$/.test(b) || chosen === "jan1944") ? "jan1944"
  : (/^[IVXL]+$/.test(b) || /^\d[A-Z]$/.test(b)) ? "feb1944" : null;
function aParse(text) {
  const t = text.trim();
  const m = /\b([IVXL]+|\d\s?[A-Z]|[A-Z]|\d{1,3})\s*[ /-]?\s*(\d{1,3})\s*$/.exec(t);
  if (!m) throw new Error(`no block and point in "${text}"`);
  const block = m[1].replace(" ", ""), point = m[2], rest = t.slice(0, m.index).trim().toLowerCase();
  let km = null, bearing = null, edge = null;
  if (rest) {
    const d = /^(?:etwa\s+)?([\d.,]+)\s*(km|m)\s+(\S+)/.exec(rest);
    if (d) {
      km = parseFloat(d[1].replace(",", "."));
      if (d[2] === "m") km /= 1000;
      const word = d[3].replace(/\.+$/, "");
      if (!(word in DIRS)) throw new Error(`direction "${d[3]}" not known`);
      bearing = DIRS[word];
    } else {
      for (const [w, e] of Object.entries(EDGES)) if (rest.startsWith(w)) edge = e;
      if (!edge) throw new Error(`can't read the offset "${rest}"`);
    }
  }
  return { block, point, km, bearing, edge, words: rest };
}
function aOffset(lat, lon, km, bearing) {
  const b = bearing * Math.PI / 180;
  return [lat + km * Math.cos(b) / 111.2, lon + km * Math.sin(b) / (111.2 * Math.cos(lat * Math.PI / 180))];
}
function aDecode(text, edition = "4") {
  let { block, point, km, bearing, edge, words } = aParse(text);
  edition = editionOf(block, edition) || edition;
  const steps = [], given = { block, point };
  if (edition === "jan1944") {
    if (!/^[A-Z]$/.test(block)) return { error: `block ${block} is not in the January 1944 edition (one letter per block)`, edition };
    point = padPt(point, edition);
    if (block === "D") steps.push(`block letter <span class="mono">D</span> inferred (not printed on the frames read)`);
  } else if (edition === "feb1944" && /^[IVXL]+$/.test(block)) {
    if (!COVER[block]) return { error: `cover name ${block}: not read beside any block yet (February 1944 edition)`, edition };
    steps.push(`<span class="mono">${block}</span> = block <span class="mono">${COVER[block]}</span>${COVER_SURE.has(block) ? "" : " (tentative)"}, ` +
      `point ${point} − ${COVER_OFFSET} = printed <span class="mono">${+point - COVER_OFFSET}</span>`);
    block = COVER[block]; point = String(+point - COVER_OFFSET);
  } else if (edition === "4" && !/^\d+$/.test(block)) {
    return { error: `block ${block} is not in the ${EDITION[edition].name}`, edition };
  }
  const rows = POINTS[edition].get(`${block} ${point}`);
  if (!rows) return { error: `${steps.length ? steps.map(t => t.replace(/<[^>]+>/g, "")).join("; ") + "; " : ""}${block} ${point}: not read yet in the ${EDITION[edition].name}`, edition, steps };
  const r = rows[0];
  let lat = r.lat, lon = r.lon;
  const res = { edition, block, point, row: r, steps, given, pt: [r.lon, r.lat], dup: rows.length > 1 };
  if (km != null) { [lat, lon] = aOffset(lat, lon, km, bearing); res.offset = { km, bearing, words }; }
  if (edge) res.edge = edge;
  res.at = [lon, lat];
  return res;
}
const kmBetween = (a, b) => Math.hypot((a[1] - b[1]) * 111.2, (a[0] - b[0]) * 111.2 * Math.cos(b[1] * Math.PI / 180));

function aDraw(m) {
  const { g, proj, path } = m;
  graticule(m, [[12.5, 40.8], [14.8, 42]], 0.1);
  g.append("path").datum(LAND10).attr("class", "land").attr("d", path);
  degLabels(m, AFOCUS, 0.2, 0.1);
  const eds = ARMY.view === "all" ? ALL_EDS : [ARMY.view];
  const kmPx = Math.abs(proj([13.6, 41.4])[1] - proj([13.6, 41.4 + 1 / 111.2])[1]);   // 1 km on the map
  for (const ed of eds) {
    const pts = [...POINTS[ed].values()].flat();
    const eg = g.append("g").style("--c", EDITION[ed].color);
    eg.append("g").selectAll("circle").data(pts).join("circle").attr("class", "ring")
      .attr("cx", p => proj([p.lon, p.lat])[0]).attr("cy", p => proj([p.lon, p.lat])[1]).attr("r", p => precKm(p, ed) * kmPx);
    // the block's number at the middle of the points read in it (the block's printed edges aren't digitized)
    const byBlock = d3.group(pts, p => p.block);
    eg.append("g").selectAll("text").data([...byBlock]).join("text").attr("class", "bkl")
      .attr("x", ([, ps]) => d3.mean(ps, p => proj([p.lon, p.lat])[0])).attr("y", ([, ps]) => d3.mean(ps, p => proj([p.lon, p.lat])[1]))
      .text(([b, ps]) => ps[0].cover_name ? `${b} (${ps[0].cover_name})` : ed === "jan1944" && b === "D" ? "D (inferred)" : b);
    const a = eg.append("g").selectAll("a").data(pts).join("a")
      .attr("href", p => srcUrl(p.frame)).attr("target", "_blank").attr("rel", "noopener")
      .on("mousemove", (e, p) => { aPointTip(p, ed); place(e); }).on("mouseleave", hideTip);
    a.append("circle").attr("class", p => `pt${p.read === "read" ? "" : " uncertain"}`)
      .attr("cx", p => proj([p.lon, p.lat])[0]).attr("cy", p => proj([p.lon, p.lat])[1]);
    eg.append("g").attr("class", "ptlg").selectAll("text").data(pts).join("text").attr("class", "ptl")
      .attr("x", p => proj([p.lon, p.lat])[0]).attr("y", p => proj([p.lon, p.lat])[1]).text(p => p.point);
    // a town printed on several editions is named once (on the last edition drawn of those shown)
    const later = eds.slice(eds.indexOf(ed) + 1).flatMap(e => [...POINTS[e].values()].flat().filter(q => q.name_as_printed));
    const named = pts.filter(p => p.name_as_printed && !later.some(q => kmBetween([p.lon, p.lat], [q.lon, q.lat]) < 1.5));
    eg.append("g").selectAll("text").data(named).join("text").attr("class", "town")
      .attr("x", p => proj([p.lon, p.lat])[0]).attr("y", p => proj([p.lon, p.lat])[1]).text(p => p.name_as_printed);
  }
  // anchors with a known place: the place (a square) joined to the decoded point
  const an = ARMY.anchors.filter(a => a.d && a.d.at && a.expected && eds.includes(a.d.edition));
  g.append("g").selectAll("line").data(an).join("line").attr("class", "miss")
    .attr("x1", a => proj(a.expected)[0]).attr("y1", a => proj(a.expected)[1]).attr("x2", a => proj(a.d.at)[0]).attr("y2", a => proj(a.d.at)[1]);
  g.append("g").selectAll("a").data(an).join("a").attr("href", a => srcUrl(a.source)).attr("target", "_blank").attr("rel", "noopener")
    .on("mousemove", (e, a) => {
      tip.innerHTML = `<div class="v">${esc(a.place_as_written)}</div><div class="k"><span class="mono">${esc(a.code)}</span> · ${EDITION[a.d.edition].name}</div>` +
        `<div class="m">the place (OSM) is ${a.err.toFixed(2)} km from the decoded point</div><div class="i">${esc(a.document)} · ${a.source} · click to open</div>`;
      place(e);
    }).on("mouseleave", hideTip)
    .append("rect").attr("class", "expect").attr("x", a => proj(a.expected)[0]).attr("y", a => proj(a.expected)[1]);
  g.append("g").attr("class", "probe");
  aDrawProbe();
}
function aPointTip(p, ed) {
  tip.innerHTML = `<div class="v"><span class="mono">${p.block} ${p.point}</span>${p.name_as_printed ? ` ${esc(p.name_as_printed)}` : ""}</div>` +
    `<div class="k">${EDITION[ed].name}${p.cover_name ? ` · reported as <span class="mono">${p.cover_name} ${+p.point + COVER_OFFSET}</span>` : ""}</div>` +
    `<div class="m">${p.lat.toFixed(4)}, ${p.lon.toFixed(4)} <span class="prov">provisional (about ${precKm(p, ed)} km${precKm(p, ed) > 0.4 ? ": block C's north-east corner fits worse" : ""})</span></div>` +
    (ed === "jan1944" && p.block === "D" ? `<div class="m"><i>block letter D inferred: not printed on the frames read</i></div>` : "") +
    `<div class="m">${p.read === "read" ? "number read" : "number read with doubt"}</div>` +
    (p.note ? `<div class="i">${esc(p.note)}</div>` : "") +
    `<div class="i">${p.frame} px ${p.px_x},${p.px_y} · click to open the frame</div>`;
}
function aScale(m, k) {
  const g = m.g;
  px(g.selectAll(".land, .graticule"), k, { sw: 0.6 });
  px(g.selectAll(".deg text"), k, { font: 12.5 });
  px(g.selectAll(".ring"), k, { sw: 0.8, dash: "2 2" });
  px(g.selectAll("circle.pt"), k, { r: 3.2, sw: 1.2 });
  px(g.selectAll(".ptl"), k, { font: 11, sw: 2.5 });
  g.selectAll(".ptl").attr("dx", "0.45em").attr("dy", "-0.3em");
  g.selectAll(".ptlg").style("display", k >= 3 ? null : "none");
  px(g.selectAll(".bkl"), k, { font: 17, sw: 3 });
  px(g.selectAll(".town"), k, { font: 13, sw: 3 });
  g.selectAll(".town").attr("dx", "0.5em").attr("dy", "1.1em");
  px(g.selectAll(".miss"), k, { sw: 1.2, dash: "3 2" });
  g.selectAll("rect.expect").attr("width", 7 / k).attr("height", 7 / k).attr("transform", `translate(${-3.5 / k},${-3.5 / k})`).style("stroke-width", `${1 / k}px`);
  px(g.selectAll(".probe .ctr"), k, { r: 5, sw: 1.5 });
  px(g.selectAll(".probe .arrow"), k, { sw: 1.5 });
  px(g.selectAll(".probe text"), k, { font: 13.5, sw: 3 });
}
function aProbe(zoom) {
  const out = document.getElementById("aprobe-out"), sel = document.getElementById("aprobe-ed");
  ARMY.probe = null;
  let d;
  try { d = aDecode(document.getElementById("aprobe").value, sel.value); } catch (err) { d = { error: err.message }; }
  if (d.error) { out.innerHTML = `<span class="err">${esc(d.error)}</span>`; aDrawProbe(); return; }
  ARMY.probe = d;
  const r = d.row, frame = r.frame;
  out.innerHTML = `<div class="anatomy"><span class="a">${d.given.block}</span> <span class="b">${d.given.point}</span>` +
    (d.given.block !== d.block ? ` <span class="muted">=</span> <span class="a">${d.block}</span> <span class="b">${d.point}</span>` : "") + `</div>` +
    `<table><tbody><tr><td>edition</td><td>${EDITION[d.edition].name}${/^[IVXL]$/.test(d.given.block) ? " (chosen by the date: V, X, I and L are January letters and February cover names)" : editionOf(d.given.block) ? " (chosen by the block)" : ""}</td></tr>` +
    d.steps.map(s => `<tr><td>${d.edition === "jan1944" ? "block" : "cover name"}</td><td>${s}</td></tr>`).join("") +
    `<tr><td>point</td><td><span class="mono">${d.block} ${d.point}</span>${r.name_as_printed ? ` = ${esc(r.name_as_printed)}` : ""}: ${r.lat.toFixed(5)}, ${r.lon.toFixed(5)} ` +
    `<span class="muted">(${r.read === "read" ? "number read" : "number read with doubt"}; ${srcLink(frame)} px ${r.px_x},${r.px_y})</span>${d.dup ? ` <i>Two readings of this number in the block: one is wrong.</i>` : ""}</td></tr>` +
    (d.offset ? `<tr><td>offset</td><td>${d.offset.km} km at ${d.offset.bearing}° (<span class="mono">${esc(d.offset.words)}</span>)</td></tr>` : "") +
    (d.edge ? `<tr><td>edge</td><td>the ${d.edge} edge of the place at the point (no distance given: not moved)</td></tr>` : "") +
    `<tr><td>position</td><td><b>${d.at[1].toFixed(4)}, ${d.at[0].toFixed(4)}</b> <span class="prov">provisional: about ${precKm(r, d.edition)} km${d.offset ? ", plus the report's own rounding of the distance" : ""}</span></td></tr>` +
    `</tbody></table>`;
  if (ARMY.view !== "all" && ARMY.view !== d.edition) { ARMY.view = "all"; buildEdSeg(); amap.render(); }
  aDrawProbe();
  if (zoom && amap.zoom) { const [x, y] = d.at; amap.zoomTo([[x - 0.03, y - 0.025], [x + 0.03, y + 0.025]], 0.5); }
}
function aDrawProbe() {
  if (!amap || !amap.g) return;
  const pg = amap.g.select(".probe");
  pg.selectAll("*").remove();
  const d = ARMY.probe;
  if (!d) return;
  const { proj } = amap, [x0, y0] = proj(d.pt), [x1, y1] = proj(d.at);
  if (d.offset) pg.append("line").attr("class", "arrow").attr("x1", x0).attr("y1", y0).attr("x2", x1).attr("y2", y1);
  pg.append("circle").attr("class", "ctr").attr("cx", x1).attr("cy", y1);
  pg.append("text").attr("x", x1).attr("y", y1).attr("dx", "0.7em").attr("dy", "1.2em").text(document.getElementById("aprobe").value.trim());
  aScale(amap, amap.k);
}
function buildEdSeg() {
  const opts = [...ED_ORDER.map(key => ({ key, name: EDITION[key].name })), { key: "all", name: "All" }];
  d3.select("#ed-seg").selectAll("button").data(opts).join("button")
    .html(d => d.key === "all" ? d.name : `<span class="swatch" style="display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px;background:${EDITION[d.key].color}"></span>${d.name}`)
    .attr("aria-pressed", d => d.key === ARMY.view)
    .on("click", (e, d) => { ARMY.view = d.key; buildEdSeg(); amap.render(); });
}
function aTables() {
  const t = d3.select("#aanchors");
  t.html(`<thead><tr><th>Code</th><th>Place as written</th><th>Where it comes from</th><th>Edition</th><th class="num">Error</th><th>Notes</th></tr></thead>`);
  t.append("tbody").selectAll("tr").data(ARMY.anchors).join("tr").html(a =>
    `<td style="white-space:nowrap"><span class="mono">${esc(a.code)}</span></td><td>${esc(a.place_as_written)}</td>` +
    `<td>${esc(a.document)}${a.date ? `, ${esc(a.date)}` : ""} (${srcLink(a.source)})</td><td>${esc(a.edition)}</td>` +
    `<td class="num" style="white-space:nowrap">${a.err != null ? `${a.err.toFixed(2)} km` : `<span class="muted">not testable</span>`}</td>` +
    `<td class="muted" style="font-size:13.5px">${esc(a.note)}</td>`);
}

// ══ Load ══════════════════════════════════════════════════════════════════════════════════════════════════════
let LAND50, LAND10;
Promise.all([
  d3.csv(REFERENCE + "naval-grid/squares.csv"), d3.csv(REFERENCE + "naval-grid/anchors.csv"),
  d3.csv(REFERENCE + "bezugspunkte/ausgabe4.csv"), d3.csv(REFERENCE + "bezugspunkte/feb1944.csv"),
  d3.csv(REFERENCE + "bezugspunkte/jan1944.csv"), d3.csv(REFERENCE + "bezugspunkte/anchors.csv"),
  d3.json("https://cdn.jsdelivr.net/npm/world-atlas@2/land-50m.json"),
  d3.json("https://cdn.jsdelivr.net/npm/world-atlas@2/land-10m.json"),
]).then(([squares, nanchors, a4, feb, jan, aanchors, w50, w10]) => {
  LAND50 = topojson.feature(w50, w50.objects.land);
  LAND10 = topojson.feature(w10, w10.objects.land);

  // ── naval ──
  for (const b of squares) {
    Object.assign(b, { n: mins(b.lat_n), s: mins(b.lat_s), w: mins(b.lon_w), e: mins(b.lon_e) });
    b.c = [(b.w + b.e) / 120, (b.n + b.s) / 120];
    BLOCKS.set(b.square + b.block, b);
  }
  NAV.anchors = nanchors.map(a => {
    const r = { ...a, at: a.lat ? [+a.lon, +a.lat] : null };
    try { r.d = nDecode(a.code); } catch (err) { r.err_text = err.message; }
    if (r.d && r.at) r.err = nmBetween(r.at, [r.d.lon, r.d.lat]);
    return r;
  });
  // legend from the methods in the data, with their counts
  const count = d3.rollup(squares, v => v.length, b => b.method);
  const sw = mth => {
    const fill = mth === "measured-lon" ? "url(#key-lon)" : mth === "assumed" ? "url(#key-assumed)" : "var(--series-track)";
    const op = mth === "measured" ? 0.12 : mth === "read" ? 0.05 : 1;
    return `<svg width="22" height="14"><rect x="1" y="1" width="20" height="12" fill="${fill}" fill-opacity="${op}" stroke="var(--series-track)" stroke-width="1.2"${METHOD[mth].dash ? ` stroke-dasharray="${METHOD[mth].dash}"` : ""}/></svg>`;
  };
  document.getElementById("nlegend").innerHTML = Object.keys(METHOD).map(mth =>
    `<span title="${METHOD[mth].what}">${sw(mth)}<i>${METHOD[mth].name}</i>&nbsp;(${count.get(mth) || 0})</span>`).join("") +
    `<span><svg width="34" height="12"><circle cx="5" cy="6" r="3.5" fill="var(--text-primary)"/><line x1="9" y1="6" x2="22" y2="6" stroke="var(--text-primary)" stroke-opacity="0.6" stroke-dasharray="3 2"/><rect x="23" y="1" width="10" height="10" fill="var(--series-attack)" fill-opacity="0.35" stroke="var(--series-attack)"/></svg>place the diary names, and the cell its code decodes to</span>` +
    `<span><svg width="14" height="14"><rect x="1" y="1" width="12" height="12" fill="var(--series-air)" fill-opacity="0.45" stroke="var(--series-air)"/></svg>the code you typed</span>`;
  const ex = nDecode("CJ 9472"), exA = NAV.anchors.find(a => a.code === "CJ 9472");
  document.getElementById("ex-n-src").href = srcUrl("skl:55/p397");
  document.getElementById("ex-n-out").innerHTML = `On the chart's blocks it decodes to ${dm(ex.s, "N", "S")}–${dm(ex.n, "N", "S")}, ` +
    `${dm(ex.w, "E", "W")}–${dm(ex.e, "E", "W")}` +
    (exA && exA.err != null ? `, about ${exA.err.toFixed(0)} nm north of the coast the diary names (block CJ 9 was ${METHOD[ex.blk.method].name}, ` : ` (block CJ 9 was ${METHOD[ex.blk.method].name}, `) +
    `${ex.blk.frames.split(";").map(s => srcLink(s.trim())).join(", ")}).`;

  // ── army ──
  for (const [ed, rows] of [["4", a4], ["feb1944", feb], ["jan1944", jan]]) for (const r of rows) {
    r.lat = +r.lat; r.lon = +r.lon; r.frame = r.section_frame || r.frame;
    const key = `${r.block} ${r.point}`;
    POINTS[ed].set(key, [...(POINTS[ed].get(key) || []), r]);
  }
  document.getElementById("n-a4").textContent = a4.length;
  document.getElementById("n-a4b").textContent = new Set(a4.map(r => r.block)).size;
  document.getElementById("n-feb").textContent = feb.length;
  document.getElementById("n-jan").textContent = jan.length;
  document.getElementById("n-janb").textContent = new Set(jan.map(r => r.block)).size;
  ARMY.anchors = aanchors.map(a => {
    const r = { ...a };
    const ed = { "4": "4", "Feb 1944": "feb1944", "Jan 1944": "jan1944" }[a.edition];
    if (ed) { const d = aDecode(a.code, ed); if (!d.error) r.d = d; }
    if (a.expected_lat && r.d) { r.expected = [+a.expected_lon, +a.expected_lat]; r.err = kmBetween(r.d.pt, r.expected); }
    return r;
  });
  const exa = aDecode("XXIII 68");
  document.getElementById("ex-a-src").href = srcUrl("t314-0544/f0361");
  document.getElementById("tb-src").href = srcUrl("t312-0090/f0003");
  document.querySelectorAll("a[data-src]").forEach(a => { a.href = srcUrl(a.dataset.src); });
  // January: the XIV Panzer Corps' report of 12 Jan 1944
  const exj = ["M 28", "M 46", "C 11"].map(c => aDecode(c, "jan1944"));
  document.getElementById("ex-j-out").innerHTML = `On the January map (${srcLink(exj[0].row.frame)}) ` +
    exj.map(d => `<span class="mono">${d.block} ${d.point}</span> is ${d.row.lat.toFixed(4)}, ${d.row.lon.toFixed(4)}` +
      (d.row.name_as_printed ? ` (${esc(d.row.name_as_printed)})` : "") + (d.row.read === "read" ? "" : `, its number read with doubt`)).join("; ") +
    `. <span class="prov">Provisional: about 0.4 km in block M, about 1.3 km in block C</span>.`;
  const caira = ARMY.anchors.find(a => a.code === "XXIII 68");
  document.getElementById("ex-a-out").innerHTML = `Read on the February map (${srcLink(exa.row.frame)}), the point is ` +
    `${exa.row.lat.toFixed(4)}, ${exa.row.lon.toFixed(4)}${caira && caira.err != null ? `, ${caira.err.toFixed(2)} km from Caira` : ""}; ` +
    `<span class="prov">provisional, about 0.4 km</span>.`;
  document.getElementById("alegend").innerHTML =
    ED_ORDER.map(k => [k, EDITION[k]]).map(([k, e]) => `<span><svg width="22" height="14"><circle cx="11" cy="7" r="6" fill="${e.color}" fill-opacity="0.05" stroke="${e.color}" stroke-opacity="0.5" stroke-dasharray="2 2"/><circle cx="11" cy="7" r="3.2" fill="${e.color}"/></svg>${e.name}: a point, its ring the provisional ~${k === "jan1944" ? "0.4 km (block C, 1.3 km)" : "0.4 km"}</span>`).join("") +
    `<span><svg width="14" height="14"><circle cx="7" cy="7" r="3.2" fill="var(--surface-1)" stroke="var(--text-secondary)" stroke-width="1.2"/></svg>number read with doubt</span>` +
    `<span><svg width="34" height="12"><rect x="1" y="2.5" width="7" height="7" fill="var(--text-primary)"/><line x1="8" y1="6" x2="30" y2="6" stroke="var(--text-primary)" stroke-opacity="0.6" stroke-dasharray="3 2"/></svg>the named place (modern position), to its decoded point</span>`;

  nTables(); aTables(); buildEdSeg();
  nmap = makeMap({ svg: "#nmap", wrap: "#nwrap", focus: NFOCUS, units: ["nm"], draw: nDraw, scale: nScale, max: 60 });
  amap = makeMap({ svg: "#amap", wrap: "#awrap", focus: AFOCUS, units: ["km", "mi"], draw: aDraw, scale: aScale, max: 20 });
  for (const [id, f] of [["nprobe", nProbe], ["aprobe", aProbe]]) {
    const i = document.getElementById(id);
    i.addEventListener("input", () => f(false));
    i.addEventListener("change", () => f(true));
  }
  document.getElementById("aprobe-ed").addEventListener("change", () => aProbe(true));
  document.querySelectorAll(".try").forEach(b => b.addEventListener("click", () => {
    const i = document.getElementById(b.dataset.for); i.value = b.dataset.v;
    (b.dataset.for === "nprobe" ? nProbe : aProbe)(true);
  }));
  nProbe(false); aProbe(false);
});
