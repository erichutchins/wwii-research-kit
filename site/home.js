// The front page (index.html): the four theatres' cards, each with its span and what its records hold (chapter.js:
// operations/operations.json, engagements/index.json, subjects.json) and one featured figure, static, drawn from the
// records (RECORDS, config.js); and what's wanted, from inventory.yml.
//   Pacific         the Luzon Strait at the end of the night of 29–30 April 1944: the three boats' tracks and the convoy's
//                   losses, engagements/tama-17-1944-04-29/engagement.json (built by tools/build_engagement.py)
//   Atlantic        Solar's crossings and UGS 72, ships/de-221-solar/track.geojson
//   Mediterranean   the theatre's operations' areas and its engagements on one map
//   Europe          Neuburg's five minutes, engagements/neuburg-1945-04-26/engagement.json

const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
// A row's citation as a link: a National Archives page (rg38-140065945/p03), a JACAR item, or a URL as it stands
function pageUrl(cite, scan) {
  let m = /^rg\d+-(\d+)\/p0*(\d+)$/.exec(cite || "");
  if (m) return `https://catalog.archives.gov/id/${m[1]}?objectPage=${m[2]}`;
  m = /^jacar:(C\d{11})/.exec(cite || "");
  if (m) return `https://www.jacar.archives.go.jp/das/image/${m[1]}`;
  m = /^ok45th-(\d+)\/p(\d+)$/.exec(cite || "");
  if (m) return `https://cdm17494.contentdm.oclc.org/digital/collection/ok45th/id/${m[1]}`;
  if (/^https?:\/\//.test(cite || "")) return cite;
  return scan || null;
}
const open = u => { if (u) window.open(u, "_blank", "noopener"); };
// (topojsonFeatures is chapter.js's)
const topojsonFeature = topo => ({ type: "MultiPolygon", coordinates: topojsonFeatures(topo, "land").flatMap(f => f.geometry.coordinates) });
const LAND_10M = "https://cdn.jsdelivr.net/npm/world-atlas@2/land-10m.json", LAND_50M = "https://cdn.jsdelivr.net/npm/world-atlas@2/land-50m.json";
const svgIn = (sel, W, H, label) => d3.select(sel).append("svg").attr("viewBox", [0, 0, W, H]).attr("role", "img").attr("aria-label", label);

// ── The theatres' spans and what their records hold ─────────────────────────────────────────────
async function cards() {
  const C = await Chapter.load();
  const T0 = s => Date.parse(`${String(s).slice(0, 10)}T12:00Z`), mon = d3.utcFormat("%B %Y");
  const n = (k, one, many = one + "s") => `${k} ${k === 1 ? one : many}`;
  for (const t of C.theatres) {
    const first = t.op ? t.op.from : d3.min(t.subjects, s => s.first), last = t.op && t.op.to ? t.op.to : t.op ? null : d3.max(t.subjects, s => s.last);
    document.getElementById(`span-${t.id}`).textContent = first ? (last ? `${mon(T0(first))} – ${mon(T0(last))}` : `from ${mon(T0(first))}`) : "";
    document.getElementById(`holds-${t.id}`).textContent = [Chapter.held(t.engagements), n(t.subjects.length, "subject"), t.campaigns.length && `${n(t.campaigns.length, "operation")} entered`].filter(Boolean).join("; ") + ".";
  }
}

// ── The engagements: every one, by theatre, in date order ───────────────────────────────────────
async function engagements() {
  const ALL = await d3.json(RECORDS + "engagements/index.json");
  const day = s => Date.parse(String(s).slice(0, 10) + "T00:00Z"), fmt = d3.utcFormat("%-d %b %Y"), fmtD = d3.utcFormat("%-d"), fmtDM = d3.utcFormat("%-d %b");
  const dates = e => {
    const a = day(e.from), b = day(e.to || e.from), A = new Date(a), B = new Date(b);
    if (a === b) return fmt(a);
    if (A.getUTCFullYear() === B.getUTCFullYear() && A.getUTCMonth() === B.getUTCMonth()) return `${fmtD(a)}–${fmt(b)}`;
    return A.getUTCFullYear() === B.getUTCFullYear() ? `${fmtDM(a)} – ${fmt(b)}` : `${fmt(a)} – ${fmt(b)}`;
  };
  const cols = [["pacific", "Pacific"], ["europe", "Europe"], ["mediterranean", "Mediterranean"], ["atlantic", "Atlantic"]]
    .map(([id, name]) => [name, ALL.filter(e => e.theater === id)]).filter(([, xs]) => xs.length);
  document.getElementById("englist").innerHTML = cols.map(([name, xs]) => `<div><h3>${esc(name)}</h3><ul>${xs.map(e =>
    `<li><span class="dates">${esc(dates(e))}</span><a href="engagement.html?e=${encodeURIComponent(e.id)}">${esc(e.title)}</a></li>`).join("")}</ul></div>`).join("");
}

// ── Pacific: the Luzon Strait at the end of the night ───────────────────────────────────────────
async function pacific() {
  const [D, land] = await Promise.all([d3.json(RECORDS + "engagements/tama-17-1944-04-29/engagement.json"), d3.json(LAND_10M)]);
  const boats = D.participants.filter(p => p.kind === "submarine").map((b, i) => ({ ...b, color: `var(--c${i + 1})` }));
  const W = 560, H = 440, [x0, y0, x1, y1] = D.box;
  const proj = d3.geoMercator().fitExtent([[0, 0], [W, H]], { type: "MultiPoint", coordinates: [[x0, y0], [x1, y1]] }).clipExtent([[0, 0], [W, H]]);
  const path = d3.geoPath(proj), P = p => proj([p.lon, p.lat]);
  const svg = svgIn("#fig-pacific", W, H, "Map of the Luzon Strait with the three submarines' tracks and the convoy's losses");
  svg.append("path").attr("class", "grat").attr("d", path(d3.geoGraticule().step([1, 1])()));
  svg.append("path").attr("class", "land").attr("d", path(topojsonFeature(land)));
  for (const p of D.places) {
    const xy = P(p);
    if (xy[0] > 30 && xy[0] < W - 30 && xy[1] > 14 && xy[1] < H - 8) svg.append("text").attr("class", "place").attr("x", xy[0]).attr("y", xy[1]).attr("text-anchor", "middle").text(p.name);
  }
  for (const b of boats) {
    const tr = (D.tracks[b.id] || []).filter(p => p.on_track).sort((p, q) => Date.parse(p.utc) - Date.parse(q.utc));
    svg.append("path").attr("class", "trail").attr("stroke", b.color).attr("d", d3.line(p => P(p)[0], p => P(p)[1])(tr));
    for (const p of tr.filter(p => p.kind === "attack")) svg.append("path").attr("d", d3.symbol(d3.symbolDiamond, 46)()).attr("fill", b.color).attr("transform", `translate(${P(p)})`)
      .append("title").text(`${b.name} ${p.ref}`);
    const end = tr[tr.length - 1];
    if (end) svg.append("text").attr("class", "boat-label").attr("x", P(end)[0] + 8).attr("y", P(end)[1] + 4).attr("fill", b.color).text(b.name);
  }
  // the convoy's record: a ship sunk (red cross) or hit (red ring), at the position the Japanese record gives
  for (const e of D.events.filter(e => e.origin === "japanese" && e.lat != null && (e.mark === "sunk" || e.mark === "hit"))) {
    const g = svg.append("g").attr("transform", `translate(${P(e)})`).style("cursor", "pointer").on("click", () => open(e.cite && e.cite.href));
    if (e.mark === "sunk") g.append("path").attr("class", "sunk").attr("d", "M-5,-5L5,5M5,-5L-5,5");
    else g.append("circle").attr("class", "hit-ring").attr("r", 5.5);
    g.append("title").text(`${e.title}: ${e.translation || e.words}`);
  }
  d3.select("#fig-pacific").append("p").attr("class", "readout").html(`The three boats' tracks from their patrol reports, each in its own colour; a diamond, an attack. A red cross, a ship the convoy's record gives as sunk; a red ring, hit. Each boat's report kept its own zone and the convoy's record Tokyo time; the engagement page puts them on one clock.`);
}

// ── Atlantic: Solar and UGS 72 ──────────────────────────────────────────────────────────────────
async function atlantic() {
  const [geo, world] = await Promise.all([d3.json(RECORDS + "ships/de-221-solar/track.geojson"), d3.json(LAND_50M)]);
  const pts = geo.features.filter(f => f.geometry.type === "Point" && f.properties.on_track && f.properties.utc)
    .map(f => ({ ...f.properties, t: Date.parse(f.properties.utc), ll: f.geometry.coordinates })).sort((a, b) => a.t - b.t);
  const hits = geo.features.filter(f => f.properties.kind === "ship" && /hit/.test(f.properties.ref));
  const leg = pts.filter(p => p.t >= Date.UTC(1945, 1, 2) && p.t <= Date.UTC(1945, 1, 18, 12));
  const W = 560, H = 300;
  const proj = d3.geoMercator().rotate([35, 0]).fitExtent([[10, 10], [W - 10, H - 10]], { type: "MultiPoint", coordinates: pts.map(p => p.ll) }).clipExtent([[0, 0], [W, H]]);
  const path = d3.geoPath(proj);
  const svg = svgIn("#fig-atlantic", W, H, "USS Solar's war diary positions, September 1944 to October 1945, with convoy UGS 72 in colour");
  svg.append("path").attr("class", "grat").attr("d", path(d3.geoGraticule().step([10, 10])()));
  svg.append("path").attr("class", "land").attr("d", path(topojsonFeature(world)));
  svg.append("path").attr("class", "track-faint").attr("d", path({ type: "LineString", coordinates: pts.map(p => p.ll) }));
  svg.append("path").attr("class", "track-hot").attr("d", path({ type: "LineString", coordinates: leg.map(p => p.ll) }));
  for (const f of hits) {
    const [hx, hy] = proj(f.geometry.coordinates), p = f.properties;
    const at = svg.append("g").attr("transform", `translate(${hx},${hy})`);
    at.append("path").attr("class", "leader").attr("d", "M0,0L-40,-60L-60,-60");
    at.append("circle").attr("class", "hit").attr("r", 6).style("cursor", "pointer").on("click", () => open(pageUrl(p.page))).append("title").text(p.note);
    at.append("text").attr("class", "lab").attr("x", -64).attr("y", -56).attr("text-anchor", "end").text("17 February 1945");
    at.append("text").attr("class", "lab-2").attr("x", -64).attr("y", -38).attr("text-anchor", "end").text("two ships in the convoy hit");
  }
  const a = proj(leg[0].ll);
  svg.append("text").attr("class", "lab-2").attr("x", a[0] + 8).attr("y", a[1] + 18).text("UGS 72 sails, 2 February");
  d3.select("#fig-atlantic").append("p").attr("class", "readout").text("Grey: every position in her war diaries, September 1944 to October 1945. Blue: convoy UGS 72, 2 to 17 February 1945.");
}

// ── Mediterranean: the operations' areas and the engagements on one map ─────────────────────────
async function mediterranean() {
  const [C, world] = await Promise.all([Chapter.load(), d3.json(LAND_50M)]);
  const T = C.theatres.find(t => t.id === "mediterranean"), a = T.op.area;
  const W = 560, H = 300;
  const proj = d3.geoMercator().fitExtent([[0, 0], [W, H]], { type: "MultiPoint", coordinates: [[a[0], a[1]], [a[2], a[3]]] }).clipExtent([[0, 0], [W, H]]);
  const path = d3.geoPath(proj);
  const svg = svgIn("#fig-mediterranean", W, H, "The Mediterranean: the operations' areas, hatched, and the engagements");
  svg.append("defs").append("pattern").attr("id", "hatch-home").attr("patternUnits", "userSpaceOnUse").attr("width", 3.5).attr("height", 3.5).attr("patternTransform", "rotate(45)")
    .append("line").attr("x1", 0).attr("y1", 0).attr("x2", 0).attr("y2", 3.5).attr("stroke", "var(--ink-3)").attr("stroke-width", 1);
  svg.append("path").attr("class", "grat").attr("d", path(d3.geoGraticule().step([5, 5])()));
  svg.append("path").attr("class", "land").attr("d", path(topojsonFeature(world)));
  const rect = ([w, s, e, n]) => ({ type: "Polygon", coordinates: [[[w, s], [w, n], [e, n], [e, s], [w, s]]] });   // clockwise: an exterior ring
  for (const c of T.campaigns.filter(c => c.op.area)) svg.append("path").attr("class", "area").attr("fill", "url(#hatch-home)").attr("d", path(rect(c.op.area)))
    .append("title").text(`${c.op.name} (area drawn by hand)`);
  const labelled = [];   // a label only where no earlier one sits within 14 px (Venafro and Filignano share a valley)
  for (const e of T.engagements) {
    const [x, y] = proj([(e.box[0] + e.box[2]) / 2, (e.box[1] + e.box[3]) / 2]);
    const g = svg.append("a").attr("href", e.href).attr("transform", `translate(${x.toFixed(1)},${y.toFixed(1)})`);
    g.append("title").text(e.title);
    g.append("circle").attr("class", "mark").attr("r", 4.5);
    if (!labelled.some(([lx, ly]) => Math.hypot(lx - x, ly - y) < 14)) { labelled.push([x, y]); g.append("text").attr("class", "lab").attr("x", 8).attr("y", 4).text(e.short || e.title); }
  }
  d3.select("#fig-mediterranean").append("p").attr("class", "readout").text(`Hatched: the ${T.campaigns.length} operations' areas, drawn by hand (ours). A mark: an engagement, at the middle of its box.`);
}

// ── Europe: Neuburg, three records on one five-minute clock ─────────────────────────────────────
async function europe() {
  const rows = Engage.story(await d3.json(RECORDS + "engagements/neuburg-1945-04-26/engagement.json")).timeline.filter(r => r.date === "1945-04-26" && r.time);
  const lanes = [
    { key: "fired", label: "106th AAA AW Bn fired on them", match: r => r.actor === "106th AAA AW Bn" && r.kind === "engage" },
    { key: "lost", label: "17th Bomb Group lost", match: r => /Bomb Sq/.test(r.actor) },
    { key: "claimed", label: "JV 44 claimed (secondary)", match: r => r.actor === "JV 44" && r.kind === "claim" },
    { key: "saw", label: "189th FA Bn watched", match: r => r.actor === "189th FA Bn" && r.kind === "witness" },
  ];
  const mins = t => +t.slice(0, 2) * 60 + +t.slice(2);
  const W = 560, top = 44, laneH = 52, H = top + lanes.length * laneH + 10;
  const x = d3.scaleLinear([11 * 60 + 42, 12 * 60 + 2], [200, W - 20]);
  const svg = svgIn("#fig-europe", W, H, "Neuburg, 26 April 1945: four records' times, 1145 to 1200");
  for (let t = 11 * 60 + 45; t <= 12 * 60; t += 5) {
    svg.append("line").attr("stroke", "var(--rule)").attr("x1", x(t)).attr("x2", x(t)).attr("y1", top - 12).attr("y2", H - 6);
    svg.append("text").attr("class", "lab-3").attr("x", x(t)).attr("y", top - 20).attr("text-anchor", "middle").text(`${Math.floor(t / 60)}${String(t % 60).padStart(2, "0")}`);
  }
  lanes.forEach((l, i) => {
    const yy = top + i * laneH + laneH / 2;
    svg.append("text").attr("class", "lab").attr("x", 0).attr("y", yy + 5).text(l.label);
    svg.append("line").attr("class", "leader").attr("x1", x.range()[0]).attr("x2", x.range()[1]).attr("y1", yy).attr("y2", yy).attr("stroke-dasharray", "1 4");
    for (const r of rows.filter(l.match)) {
      const t = mins(r.time);
      if (t < x.domain()[0] || t > x.domain()[1]) continue;
      const g = svg.append("g").style("cursor", "pointer").on("click", () => open(pageUrl(r.ref)));
      g.append("title").text(`${r.time}, ${r.actor}: ${r.text} (${r.source})`);
      const span = /From (\d{4})B to (\d{4})B/.exec(r.text);
      if (span) g.append("rect").attr("class", "span-bar").attr("x", x(mins(span[1]))).attr("y", yy - 7).attr("height", 14).attr("rx", 3).attr("width", x(mins(span[2])) - x(mins(span[1])));
      else g.append("circle").attr("class", l.key === "claimed" ? "mark-open" : r.placed ? "mark-dash" : l.key === "lost" ? "hit" : "mark").attr("cx", x(t)).attr("cy", yy).attr("r", 7);
      const name = /"([^"]+)"/.exec(r.text.replace(/""/g, '"'));
      const tag = l.key === "lost" ? (/No\. 25/.test(r.text) ? "No. 25" : name?.[1]) : l.key === "saw" ? "“At 1200” (a round number)" : l.key === "fired" ? "six Me 262s, “without result”" : "";
      if (tag) g.append("text").attr("class", "lab-2").attr("x", x(t)).attr("y", yy - 13).attr("text-anchor", "middle").text(tag);
    }
  });
  d3.select("#fig-europe").append("p").attr("class", "readout").text("The Army's B time and German summer time were both UTC+2: no conversion. Filled: from the record; dashed: placed by us; open: a secondary account not yet checked against a German record. Each mark opens its page.");
}

// ── Wanted: everything the inventory knows of and nobody has done ───────────────────────────────
async function wanted() {
  const inv = jsyaml.load(await d3.text(RECORDS + "inventory.yml"));
  const list = [];
  for (const [hull, b] of Object.entries(inv.boats || {})) if (!b.folder) list.push(`${b.name} (${hull}) war patrol reports: ${esc(b.note || "")}`);
  const cs = Object.values(inv.commands?.comsubpac?.records || {}).filter(r => r.status === "available").length;
  if (cs) list.push(`The Submarine Force, Pacific war diary: ${cs} months found and waiting to be transcribed`);
  for (const r of Object.values(inv.ships?.["DE-221"]?.records || {})) if (r.status === "found") list.push(`USS Solar: ${esc(r.note)}`);
  list.push("The other side's own records of the attacks still read from one side only: the German (the Strait of Gibraltar, 17 February 1945; JV 44 on 26 April 1945; Remagen and the Ardennes) and the Japanese (BANG in the Yellow Sea, 10 February 1945)");
  document.getElementById("wanted").innerHTML = list.map(w => `<li>${w}</li>`).join("");
}

// A figure whose records don't load says so in its place instead of leaving a blank
const failed = (sel, what) => err => {
  console.error(err);
  const p = document.createElement("p");
  p.className = "readout";
  p.textContent = `The records for this ${what} didn't load. Reload the page to try again.`;
  document.querySelector(sel).replaceChildren(p);
};
cards().catch(failed("#theatres .intro", "page"));
engagements().catch(failed("#englist", "list"));
pacific().catch(failed("#fig-pacific", "map"));
atlantic().catch(failed("#fig-atlantic", "map"));
mediterranean().catch(failed("#fig-mediterranean", "map"));
europe().catch(failed("#fig-europe", "figure"));
wanted().catch(failed("#wanted", "list"));
