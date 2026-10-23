// The front page's figures and lists, drawn from the records (RECORDS, config.js):
//   the Luzon Strait replay        battles/luzon-strait-1944.json (built by tools/build_battle.py)
//   Haynsworth's four times        engagements/haynsworth-1945-04-06/claims.csv ("When was she hit?")
//   the 20th Seabees' parts        seabees/seabees.json
//   Solar and UGS 72               ships/de-221-solar/track.geojson
//   Neuburg's five minutes         engagements/neuburg-1945-04-26/timeline.csv
//   every ship's track             ships.json and each ship's track geojson
//   what else, and what's wanted   ships.json, army/army.json, battles/index.json, inventory.yml

const css = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
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
const fmtDate = d3.utcFormat("%-d %b %Y");

// ── The one-clock replay ────────────────────────────────────────────────────────────────────────
async function replay() {
  const battle = await d3.json(RECORDS + "battles/luzon-strait-1944.json");
  const act = battle.actions[0];
  const boats = battle.boats.map((b, i) => ({ ...b, color: `var(--c${i + 1})` }));
  const color = Object.fromEntries(boats.map(b => [b.id, b.color]));
  const T = s => Date.parse(s);
  const t0 = T(act.start), t1 = T(act.end);
  const tracks = Object.fromEntries(boats.map(b => [b.id, (act.tracks[b.id] || []).filter(p => p.on_track)
    .map(p => ({ ...p, t: T(p.utc) })).sort((a, b) => a.t - b.t)]));
  const events = [...act.events, ...act.sinkings].map(e => ({ ...e, t: T(e.utc) })).sort((a, b) => a.t - b.t);
  // one Japanese entry can be listed twice (once per ship it names); keep one
  const seen = new Set();
  const evs = events.filter(e => { const k = e.side + e.utc + e.title + e.type; if (seen.has(k)) return false; seen.add(k); return true; });
  const us = evs.filter(e => e.side !== "japan"), jp = evs.filter(e => e.side === "japan");

  document.getElementById("luzon-side").innerHTML = `<p>${esc(act.convoy)}: ${esc(act.route)}</p>
    <p>${esc(act.outcome)}</p><p>Times are GMT. Each boat kept its own zone; the convoy's record is in Tokyo time.</p>`;

  // the map
  const W = 640, H = 560;
  const [x0, y0, x1, y1] = act.box;
  const proj = d3.geoMercator().fitExtent([[0, 0], [W, H]], { type: "MultiPoint", coordinates: [[x0, y0], [x1, y1]] });
  const path = d3.geoPath(proj);
  const svg = d3.select("#replay-map").append("svg").attr("viewBox", [0, 0, W, H])
    .attr("role", "img").attr("aria-label", "Map of the Luzon Strait with the three submarines' tracks and the convoy's losses");
  svg.append("path").attr("class", "grat").attr("d", path(d3.geoGraticule().step([1, 1])()));
  svg.append("path").attr("class", "land").attr("d", path({ type: "MultiPolygon", coordinates: act.land.map(r => [r]) }));
  for (const p of battle.places || []) {
    const xy = proj([p.lon, p.lat]);
    if (xy && xy[0] > 30 && xy[0] < W - 30 && xy[1] > 14 && xy[1] < H - 8)
      svg.append("text").attr("class", "place").attr("x", xy[0]).attr("y", xy[1]).attr("text-anchor", "middle").text(p.name);
  }
  const gFuture = svg.append("g"), gTrail = svg.append("g"), gMarks = svg.append("g"), gBoats = svg.append("g");
  for (const b of boats) gFuture.append("path").attr("class", "trail-future").attr("stroke", b.color)
    .attr("d", d3.line(p => proj([p.lon, p.lat])[0], p => proj([p.lon, p.lat])[1])(tracks[b.id]));
  const trails = Object.fromEntries(boats.map(b => [b.id, gTrail.append("path").attr("class", "trail").attr("stroke", b.color)]));
  const boatG = Object.fromEntries(boats.map(b => {
    const g = gBoats.append("g");
    g.append("circle").attr("r", 5).attr("fill", b.color).attr("stroke", "var(--paper)").attr("stroke-width", 1.5);
    g.append("text").attr("class", "boat-label").attr("x", 9).attr("y", 4).attr("fill", b.color).text(b.name);
    return [b.id, g];
  }));
  // what the convoy recorded, and the boats' attacks, appear as their minute passes
  const hits = jp.filter(e => e.lat != null).map(e => ({ e, xy: proj([e.lon, e.lat]) }));
  const attacks = boats.flatMap(b => tracks[b.id].filter(p => p.kind === "attack").map(p => ({ b, p, xy: proj([p.lon, p.lat]) })));
  const contacts = act.fixes.filter(f => f.kind === "ship").map(f => ({ f, t: T(f.utc), xy: proj([f.lon, f.lat]) }));

  const at = (tr, t) => {
    if (!tr.length) return null;
    if (t <= tr[0].t) return { xy: proj([tr[0].lon, tr[0].lat]), before: true };
    for (let i = 1; i < tr.length; i++) if (t <= tr[i].t) {
      const a = tr[i - 1], b = tr[i], k = (t - a.t) / (b.t - a.t || 1);
      const A = proj([a.lon, a.lat]), B = proj([b.lon, b.lat]);
      return { xy: [A[0] + (B[0] - A[0]) * k, A[1] + (B[1] - A[1]) * k], i };
    }
    const z = tr[tr.length - 1]; return { xy: proj([z.lon, z.lat]), after: true };
  };

  // the scrubber
  const scrub = document.getElementById("scrub");
  scrub.min = t0; scrub.max = t1; scrub.step = 60000;
  const ss = d3.select("#scrub-svg");
  function drawScrub() {
    const w = ss.node().getBoundingClientRect().width || 400;
    ss.selectAll("*").remove();
    const x = d3.scaleUtc([t0, t1], [0, w]);
    ss.append("line").attr("class", "axis-line").attr("x1", 0).attr("x2", w).attr("y1", 23).attr("y2", 23);
    for (const e of us) ss.append("line").attr("class", "tick-us").attr("stroke", color[e.side] || "var(--ink-3)")
      .attr("x1", x(e.t)).attr("x2", x(e.t)).attr("y1", 12).attr("y2", 22);
    for (const e of jp) ss.append("line").attr("class", "tick-jp").attr("x1", x(e.t)).attr("x2", x(e.t)).attr("y1", 24).attr("y2", 34);
    for (const h of d3.utcHour.every(6).range(t0, t1 + 1)) {
      ss.append("text").attr("class", "axis-text").attr("x", x(h)).attr("y", 46).attr("text-anchor", "middle").text(d3.utcFormat("%H%M")(h));
    }
    ss.append("line").attr("class", "cursor").attr("y1", 6).attr("y2", 40);
    ss.node().__x = x;
  }
  drawScrub();
  new ResizeObserver(() => { drawScrub(); set(+scrub.value); }).observe(ss.node());

  // One entry: our GMT time; a bar in the boat's colour (the map's track colour) down its left edge; the name, and at
  // the right the record's own clock; then the record's words, and the page they're on.
  const pageOf = cite => { const m = /p0*(\d+)\s*$/.exec(cite || ""); return m ? `p. ${m[1]}` : "page"; };
  const titleAdds = e => e.title && e.title !== "Log" && !(e.text || "").toLowerCase().includes(e.title.toLowerCase().split(/\W+/)[0]);
  const entry = (e, old) => {
    const boat = boats.find(b => b.id === e.side);
    const u = pageUrl(e.page, e.scan);
    const own = /^\S+ (\d{4}) \(([^),]+)/.exec(e.local || "");   // "1944-04-29 2300 (K)" -> 2300 K
    const cite = u ? ` <a class="src" href="${esc(u)}" target="_blank" rel="noopener" title="${esc(e.page || "")}">${pageOf(e.page)}</a>` : "";
    const words = e.original
      ? `<span class="ja" lang="ja">${esc(e.original)}</span><span class="tr">${esc(e.text)} (translated)${cite}</span>`
      : `<span class="said">${esc(boat && titleAdds(e) ? e.text : (e.text && e.text !== e.title ? e.text : e.title))}${cite}</span>`;
    return `<li class="entry" style="--bar:${boat ? boat.color : "var(--ink)"}" title="${esc(e.local || "")}">
      <span class="t">${d3.utcFormat("%H%M")(e.t)}</span>
      <span class="body"><span class="who"><b>${esc(boat ? boat.name : e.title)}</b>${boat && titleAdds(e) ? `<span class="what">${esc(e.title)}</span>` : ""}${own ? `<span class="own">${own[1]} ${esc(own[2])}</span>` : ""}</span>${words}</span></li>`;
  };
  const logUS = document.getElementById("log-us"), logJP = document.getElementById("log-jp"), now = document.getElementById("now");
  function set(t) {
    scrub.value = t;
    const x = ss.node().__x; ss.select(".cursor").attr("x1", x(t)).attr("x2", x(t));
    now.innerHTML = `${d3.utcFormat("%H%M GMT")(new Date(t))}<small>${d3.utcFormat("%-d April 1944")(new Date(t))}</small>`;
    for (const b of boats) {
      const tr = tracks[b.id], p = at(tr, t);
      const done = tr.filter(q => q.t <= t).map(q => proj([q.lon, q.lat]));
      if (p && !p.before && !p.after) done.push(p.xy);
      trails[b.id].attr("d", done.length > 1 ? d3.line()(done) : null);
      boatG[b.id].attr("transform", p ? `translate(${p.xy})` : null).attr("opacity", !p || p.before || p.after ? .35 : 1);
    }
    gMarks.selectAll("*").remove();
    for (const c of contacts.filter(c => c.t <= t && t - c.t < 3 * 3600e3))
      gMarks.append("path").attr("class", "convoy").attr("d", d3.symbol(d3.symbolCross, 30)()).attr("transform", `translate(${c.xy}) rotate(45)`)
        .append("title").text(`${c.f.ref}: the convoy as ${c.f.boat.toUpperCase()} reported it, ${c.f.raw}`);
    for (const a of attacks.filter(a => T(a.p.utc) <= t))
      gMarks.append("path").attr("d", d3.symbol(d3.symbolTriangle, 46)()).attr("fill", a.b.color)
        .attr("transform", `translate(${a.xy})`).append("title").text(`${a.b.name} ${a.p.ref}`);
    for (const h of hits.filter(h => h.e.t <= t)) {
      gMarks.append("circle").attr("class", "hit").attr("r", 5).attr("cx", h.xy[0]).attr("cy", h.xy[1])
        .style("cursor", "pointer").on("click", () => open(pageUrl(h.e.page, h.e.scan)))
        .append("title").text(`${h.e.title}: ${h.e.text}`);
      if (t - h.e.t < 40 * 60e3) gMarks.append("circle").attr("class", "hit-ring").attr("r", 12).attr("cx", h.xy[0]).attr("cy", h.xy[1]);
    }
    const lastUS = us.filter(e => e.t <= t).slice(-3).reverse(), lastJP = jp.filter(e => e.t <= t).slice(-2).reverse();
    logUS.innerHTML = lastUS.length ? lastUS.map((e, i) => entry(e, i > 0)).join("") : `<li class="none">Nothing yet.</li>`;
    logJP.innerHTML = lastJP.length ? lastJP.map((e, i) => entry(e, i > 0)).join("") : `<li class="none">Nothing yet: the convoy is still sailing from Takao.</li>`;
  }
  scrub.addEventListener("input", () => { stop(); set(+scrub.value); });

  // Play: the whole night in about forty seconds, pausing on each paired moment
  const btn = document.getElementById("play");
  let timer = null, last = 0;
  const step = (t1 - t0) / 40000;
  function tick(ts) {
    if (!timer) return;
    const dt = last ? ts - last : 16; last = ts;
    const t = Math.min(t1, +scrub.value + dt * step);
    set(t);
    if (t >= t1) return stop();
    timer = requestAnimationFrame(tick);
  }
  function stop() { if (timer) cancelAnimationFrame(timer); timer = null; last = 0; btn.textContent = "Play"; }
  btn.addEventListener("click", () => {
    if (timer) return stop();
    if (+scrub.value >= t1) set(t0);
    btn.textContent = "Pause"; timer = requestAnimationFrame(tick);
  });
  // open on the first pairing: BANG's first attack and the convoy's record of the same minutes
  const first = jp.find(e => e.type === "torpedoed");
  set(first ? first.t + 60e3 : t0);
}

// ── Haynsworth: one hit, four times ───────────────────────────────────────────────────────────
async function haynsworth() {
  const claims = (await d3.csv(RECORDS + "engagements/haynsworth-1945-04-06/claims.csv")).filter(c => c.question === "When was she hit?");
  const host = d3.select("#fig-haynsworth");
  const W = 860, H = 210, m = { l: 20, r: 20 };
  const mins = s => { const m = /(\d{2})(\d{2})/.exec(s); return m ? +m[1] * 60 + +m[2] : null; };
  const x = d3.scaleLinear([12 * 60 + 40, 13 * 60 + 30], [m.l, W - m.r]);
  const svg = host.append("svg").attr("viewBox", [0, 0, W, H]).attr("role", "img")
    .attr("aria-label", "When was she hit: the times four records give, from 1250 to 1321");
  svg.append("line").attr("class", "leader").attr("x1", x.range()[0]).attr("x2", x.range()[1]).attr("y1", 60).attr("y2", 60);
  for (let t = 12 * 60 + 40; t <= 13 * 60 + 30; t += 10) {
    svg.append("line").attr("class", "leader").attr("x1", x(t)).attr("x2", x(t)).attr("y1", 56).attr("y2", 64);
    svg.append("text").attr("class", "lab-3").attr("x", x(t)).attr("y", 48).attr("text-anchor", "middle")
      .text(`${Math.floor(t / 60)}${String(t % 60).padStart(2, "0")}`);
  }
  // labels alternate below the line so neighbours don't collide
  claims.forEach((c, i) => {
    const t = mins(c.claim); if (t == null) return;
    const bound = /about|under control/i.test(c.claim), late = /received/i.test(c.claim);
    const y = 60, ly = 96 + (i % 2) * 58;
    const g = svg.append("g").style("cursor", "pointer").attr("tabindex", 0).attr("role", "link")
      .attr("aria-label", `${c.claim}, ${c.source}`)
      .on("click", () => open(pageUrl(c.ref))).on("keydown", e => { if (e.key === "Enter") open(pageUrl(c.ref)); });
    g.append("line").attr("class", "leader").attr("x1", x(t)).attr("x2", x(t)).attr("y1", y).attr("y2", ly - 14);
    g.append("circle").attr("class", bound ? "mark-dash" : late ? "mark-open" : "mark").attr("cx", x(t)).attr("cy", y).attr("r", 7);
    if (i === 0) g.append("circle").attr("cx", x(t)).attr("cy", y).attr("r", 13).attr("fill", "none").attr("stroke", "var(--fire)").attr("stroke-width", 1.5);
    const anchor = x(t) > W - 260 ? "end" : "start";
    g.append("text").attr("class", "lab-t").attr("x", x(t) + (anchor === "end" ? 6 : -6)).attr("y", ly).attr("text-anchor", anchor).text(c.claim.replace(/ \(.*\)$/, "").replace(/ Item$/, ""));
    g.append("text").attr("class", "lab-2").attr("x", x(t) + (anchor === "end" ? 6 : -6)).attr("y", ly + 19).attr("text-anchor", anchor).text(c.source.replace(/\s*\(.*\)$/, ""));
  });
  const note = claims.find(c => /received/i.test(c.claim));
  host.append("p").attr("class", "readout").html(`Filled: the time a record gives for the hit. Dashed: a bound (the fire was
    under control by then). Open: when the news arrived${note ? ` (${esc(note.source.replace(/,.*$/, ""))}: ${esc(note.note.replace(/^"[^"]*"\.\s*/, "").replace(/^./, c => c.toLowerCase()))})` : ""}.`);
}

// ── The 20th Seabees: parts splitting and rejoining ─────────────────────────────────────────────
async function seabees() {
  const S = await d3.json(RECORDS + "seabees/seabees.json");
  const rows = new Map(S.rows.map(r => [r.id, r]));
  const parts = S.parts.filter(p => p.unit === "20ncb").map(p => {
    const rr = p.ids.map(i => rows.get(i));
    return { name: p.part, rows: rr, a: Date.parse(rr[0].date), b: Date.parse(rr[rr.length - 1].date),
      places: [...new Set(rr.map(r => r.place))], first: rr[0].place, last: rr[rr.length - 1].place };
  }).sort((p, q) => p.a - q.a);
  // lanes: the battalion together on lane 0; each part takes the first lane free when it starts
  const free = [];
  for (const p of parts) {
    if (p.name === "battalion") { p.lane = 0; continue; }
    let l = 1; while ((free[l] ?? -Infinity) > p.a) l++;
    p.lane = l; free[l] = p.b + 1;
  }
  // where each part came from and went back to: the part on another lane holding the same place that day
  const near = (p, t, place) => parts.find(q => q !== p && q.lane !== p.lane && q.a <= t && t <= q.b && q.places.includes(place))
    || parts.find(q => q !== p && q.name === "battalion" && Math.abs(q.a - t) < 864e5 * 2 || q !== p && q.name === "battalion" && Math.abs(q.b - t) < 864e5 * 2);
  const lanes = d3.max(parts, p => p.lane);
  const W = 860, laneH = 36, top = 46, H = top + (lanes + 1) * laneH + 34;
  const x = d3.scaleUtc([Date.UTC(1942, 7, 1), Date.UTC(1945, 8, 15)], [120, W - 10]);
  const y = l => top + l * laneH;
  const host = d3.select("#fig-seabees");
  const svg = host.append("svg").attr("viewBox", [0, 0, W, H]).attr("role", "img").attr("aria-label", "The 20th Naval Construction Battalion's parts, 1942 to 1945");
  for (const yr of [1943, 1944, 1945]) {
    const xx = x(Date.UTC(yr, 0, 1));
    svg.append("line").attr("stroke", "var(--rule)").attr("x1", xx).attr("x2", xx).attr("y1", top - 42).attr("y2", H - 24);
    svg.append("text").attr("class", "lab-3").attr("x", xx + 4).attr("y", top - 30).text(yr);
  }
  svg.append("text").attr("class", "lab-2").attr("x", 0).attr("y", y(0) + 5).text("The battalion");
  const read = document.getElementById("seabees-read");
  const show = p => {
    read.innerHTML = p ? `<b>${esc(p.name[0].toUpperCase() + p.name.slice(1))}</b>, ${fmtDate(p.a)} to ${fmtDate(p.b)}: <span class="typed">${p.places.map(esc).join(" → ")}</span>`
      : "Point at a part to see where it went.";
  };
  show(null);
  for (const p of parts) {
    const cls = p.lane === 0 ? "lane-line" : "lane-part";
    const from = p.lane ? near(p, p.a, p.first) : null, to = p.lane ? near(p, p.b, p.last) : null;
    const pts = [];
    if (from) pts.push([x(p.a) - 8, y(from.lane)]);
    pts.push([x(p.a), y(p.lane)], [x(p.b), y(p.lane)]);
    if (to) pts.push([x(p.b) + 8, y(to.lane)]);
    const d = d3.line().curve(d3.curveMonotoneX)(pts);
    const g = svg.append("g");
    g.append("path").attr("class", "lane-hit").attr("d", d)
      .on("pointerenter", () => { g.select(".lane-part").classed("on", true); show(p); })
      .on("pointerleave", () => { g.select(".lane-part").classed("on", false); show(null); });
    g.append("path").attr("class", cls).attr("d", d);
    if (p.lane) {
      const end = x(p.a) > W - 170;
      svg.append("text").attr("class", "lab-3").attr("x", end ? x(p.a) - 10 : x(p.a) + 14).attr("y", y(p.lane) + (end ? 4 : -7))
        .attr("text-anchor", end ? "end" : "start").text(p.name);
    }
  }
  // the battalion's own stations, labelled where it was whole
  for (const [label, t] of [["Nouméa", Date.UTC(1943, 0, 20)], ["Banika", Date.UTC(1944, 6, 1)], ["Okinawa", Date.UTC(1945, 5, 10)]])
    svg.append("text").attr("class", "lab-2").attr("x", x(t)).attr("y", y(0) - 9).attr("text-anchor", "middle").text(label);
}

// ── Solar and UGS 72 ────────────────────────────────────────────────────────────────────────────
async function solar() {
  const [geo, world] = await Promise.all([d3.json(RECORDS + "ships/de-221-solar/track.geojson"),
    d3.json("https://cdn.jsdelivr.net/npm/world-atlas@2/land-50m.json")]);
  const land = topojsonFeature(world);
  const pts = geo.features.filter(f => f.geometry.type === "Point" && f.properties.on_track && f.properties.utc)
    .map(f => ({ ...f.properties, t: Date.parse(f.properties.utc), ll: f.geometry.coordinates })).sort((a, b) => a.t - b.t);
  const hits = geo.features.filter(f => f.properties.kind === "ship" && /hit/.test(f.properties.ref));
  const leg = pts.filter(p => p.t >= Date.UTC(1945, 1, 2) && p.t <= Date.UTC(1945, 1, 18, 12));
  const W = 860, H = 330;
  const proj = d3.geoMercator().rotate([35, 0]).fitExtent([[10, 10], [W - 10, H - 10]], { type: "MultiPoint", coordinates: pts.map(p => p.ll) });
  const path = d3.geoPath(proj);
  const host = d3.select("#fig-solar");
  const svg = host.append("svg").attr("viewBox", [0, 0, W, H]).attr("role", "img").attr("aria-label", "USS Solar's war diary positions, September 1944 to October 1945, with convoy UGS 72 in colour");
  svg.append("defs").append("clipPath").attr("id", "solar-clip").append("rect").attr("width", W).attr("height", H);
  const g = svg.append("g").attr("clip-path", "url(#solar-clip)");
  g.append("path").attr("class", "grat").attr("d", path(d3.geoGraticule().step([10, 10])()));
  g.append("path").attr("class", "land").attr("d", path(land));
  g.append("path").attr("class", "track-faint").attr("d", path({ type: "LineString", coordinates: pts.map(p => p.ll) }));
  g.append("path").attr("class", "track-hot").attr("d", path({ type: "LineString", coordinates: leg.map(p => p.ll) }));
  for (const f of hits) {
    const [hx, hy] = proj(f.geometry.coordinates), p = f.properties;
    g.append("circle").attr("class", "hit").attr("r", 6).attr("cx", hx).attr("cy", hy).style("cursor", "pointer")
      .on("click", () => open(pageUrl(p.page))).append("title").text(p.note);
    g.append("path").attr("class", "leader").attr("d", `M${hx},${hy}L${hx - 40},${hy - 60}L${hx - 60},${hy - 60}`);
    g.append("text").attr("class", "lab").attr("x", hx - 64).attr("y", hy - 56).attr("text-anchor", "end").text("17 February 1945");
    g.append("text").attr("class", "lab-2").attr("x", hx - 64).attr("y", hy - 38).attr("text-anchor", "end").text("two ships in the convoy hit");
    document.getElementById("solar-side").innerHTML = `<p class="typed">“${esc(p.note)}”</p>
      <p>War diary, <a href="${esc(pageUrl(p.page))}" target="_blank" rel="noopener">${esc(p.page)}</a>. The diary
      says “torpedo or mine”; the other side's record of that morning is still to find.</p>`;
  }
  const a = proj(leg[0].ll);
  g.append("text").attr("class", "lab-2").attr("x", a[0] + 8).attr("y", a[1] + 18).text("UGS 72 sails, 2 February");
  host.append("p").attr("class", "readout").text("Grey: every position in her war diaries, September 1944 to October 1945. Blue: convoy UGS 72, 2 to 17 February 1945.");
}
// world-atlas's land, without loading topojson-client for one call
function topojsonFeature(topo) {
  const o = topo.objects.land, arcs = topo.arcs, [sx, sy] = topo.transform.scale, [tx, ty] = topo.transform.translate;
  const decoded = arcs.map(arc => { let x = 0, y = 0; return arc.map(([dx, dy]) => [(x += dx) * sx + tx, (y += dy) * sy + ty]); });
  const ring = idx => idx.flatMap((i, k) => { const a = i < 0 ? decoded[~i].slice().reverse() : decoded[i]; return k ? a.slice(1) : a; });
  const geoms = o.type === "GeometryCollection" ? o.geometries : [o];
  return { type: "MultiPolygon", coordinates: geoms.flatMap(g => g.type === "Polygon" ? [g.arcs.map(ring)] : g.arcs.map(p => p.map(ring))) };
}

// ── Neuburg: three records on one five-minute clock ─────────────────────────────────────────────
async function neuburg() {
  const rows = (await d3.csv(RECORDS + "engagements/neuburg-1945-04-26/timeline.csv")).filter(r => r.date === "1945-04-26" && r.time);
  const lanes = [
    { key: "fired", label: "106th AAA AW Bn fired on them", match: r => r.actor === "106th AAA AW Bn" && r.kind === "engage" },
    { key: "lost", label: "17th Bomb Group lost", match: r => /Bomb Sq/.test(r.actor) },
    { key: "claimed", label: "JV 44 claimed (secondary)", match: r => r.actor === "JV 44" && r.kind === "claim" },
    { key: "saw", label: "189th FA Bn watched", match: r => r.actor === "189th FA Bn" && r.kind === "witness" },
  ];
  const mins = t => +t.slice(0, 2) * 60 + +t.slice(2);
  const W = 860, top = 44, laneH = 58, H = top + lanes.length * laneH + 10;
  const x = d3.scaleLinear([11 * 60 + 42, 12 * 60 + 2], [250, W - 30]);
  const host = d3.select("#fig-neuburg");
  const svg = host.append("svg").attr("viewBox", [0, 0, W, H]).attr("role", "img").attr("aria-label", "Neuburg, 26 April 1945: four records' times, 1145 to 1200");
  for (let t = 11 * 60 + 45; t <= 12 * 60; t += 5) {
    svg.append("line").attr("stroke", "var(--rule)").attr("x1", x(t)).attr("x2", x(t)).attr("y1", top - 12).attr("y2", H - 6);
    svg.append("text").attr("class", "lab-3").attr("x", x(t)).attr("y", top - 20).attr("text-anchor", "middle").text(`${Math.floor(t / 60)}${String(t % 60).padStart(2, "0")}`);
  }
  const read = host.append("p").attr("class", "readout").attr("aria-live", "polite");
  const say = r => read.html(r ? `<b>${esc(r.time)}</b>, ${esc(r.actor)}: <span class="typed">${esc(r.text)}</span> <a href="${esc(pageUrl(r.ref))}" target="_blank" rel="noopener">${esc(r.source)}</a>`
    : "Point at a mark to read the record.");
  say(null);
  lanes.forEach((l, i) => {
    const yy = top + i * laneH + laneH / 2;
    svg.append("text").attr("class", "lab").attr("x", 0).attr("y", yy + 5).text(l.label);
    svg.append("line").attr("class", "leader").attr("x1", x.range()[0]).attr("x2", x.range()[1]).attr("y1", yy).attr("y2", yy).attr("stroke-dasharray", "1 4");
    for (const r of rows.filter(l.match)) {
      const t = mins(r.time);
      if (t < x.domain()[0] || t > x.domain()[1]) continue;
      const g = svg.append("g").style("cursor", "pointer").attr("tabindex", 0).attr("role", "link").attr("aria-label", `${r.time} ${r.actor}`)
        .on("pointerenter", () => say(r)).on("focus", () => say(r)).on("click", () => open(pageUrl(r.ref)));
      const span = /From (\d{4})B to (\d{4})B/.exec(r.text);
      if (span) g.append("rect").attr("class", "span-bar").attr("x", x(mins(span[1]))).attr("y", yy - 7).attr("height", 14).attr("rx", 3)
        .attr("width", x(mins(span[2])) - x(mins(span[1])));
      else g.append("circle").attr("class", l.key === "claimed" ? "mark-open" : r.placed ? "mark-dash" : l.key === "lost" ? "hit" : "mark")
        .attr("cx", x(t)).attr("cy", yy).attr("r", 7);
      const name = /"([^"]+)"/.exec(r.text.replace(/""/g, '"'));
      const tag = l.key === "lost" ? (/No\. 25/.test(r.text) ? "No. 25" : name?.[1]) : l.key === "saw" ? "“At 1200” (a round number)" : l.key === "fired" ? "six Me 262s, “without result”" : "";
      if (tag) g.append("text").attr("class", "lab-2").attr("x", x(t)).attr("y", yy - 13).attr("text-anchor", "middle").text(tag);
    }
  });
}

// ── Every ship's track: a small map of each vessel, opening its page on patrols.html ─────────────
async function fleet() {
  const [ships, world] = await Promise.all([d3.json(RECORDS + "ships.json"), d3.json("https://cdn.jsdelivr.net/npm/world-atlas@2/land-110m.json")]);
  const land = topojsonFeature(world);
  const withTracks = ships.filter(s => s.geojson);
  const geos = await Promise.all(withTracks.map(s => d3.json(RECORDS + s.geojson)));
  const hullNo = s => +/\d+/.exec(s.hull)[0];
  const groups = [
    ["Submarines: war patrol reports", withTracks.filter(s => s.kind === "submarine")],
    ["Surface ships: war diaries", withTracks.filter(s => s.kind !== "submarine")],
  ];
  const host = d3.select("#fleet");
  const W = 320, H = 200;
  for (const [title, list] of groups) {
    if (!list.length) continue;
    host.append("h3").attr("class", "fleet-head").text(title);
    const grid = host.append("div").attr("class", "fleet");
    for (const s of list.sort((a, b) => hullNo(a) - hullNo(b))) {
      const geo = geos[withTracks.indexOf(s)];
      const lines = geo.features.filter(f => f.geometry.type === "LineString");
      const points = geo.features.filter(f => f.geometry.type === "Point");
      const attacks = points.filter(f => f.properties.kind === "attack");
      const url = `patrols.html?ship=${s.alias}`;
      const name = s.kind === "submarine" ? `USS ${s.name}` : (s.title || `USS ${s.name}`).replace(/\s*\(.*\)$/, "");
      const card = grid.append("div").attr("class", "ship-card");

      // the map: every track the ship's records give, fitted to them
      const proj = d3.geoMercator().rotate([s.rotate ?? -160, 0])
        .fitExtent([[14, 14], [W - 14, H - 14]], { type: "MultiPoint", coordinates: points.map(f => f.geometry.coordinates) })
        .clipExtent([[0, 0], [W, H]]);
      const path = d3.geoPath(proj);
      const svg = card.append("a").attr("class", "thumb").attr("href", url)
        .append("svg").attr("viewBox", [0, 0, W, H]).attr("role", "img").attr("aria-label", `Map of ${name}'s tracks`);
      svg.append("path").attr("class", "grat").attr("d", path(d3.geoGraticule().step([10, 10])()));
      svg.append("path").attr("class", "land").attr("d", path(land));
      for (const f of lines) svg.append("path").attr("class", "trk").attr("d", path(f));
      for (const f of attacks) {
        const p = f.properties, xy = proj(f.geometry.coordinates);
        svg.append("circle").attr("class", p.assumed ? "atk assumed" : "atk").attr("r", 3).attr("cx", xy[0]).attr("cy", xy[1])
          .on("click", e => { e.preventDefault(); open(pageUrl(p.page)); })
          .append("title").text(`${p.ref || "Attack"}, ${p.local}${p.assumed ? " (position assumed)" : ""}: ${p.page}`);
      }

      // what it is, when, and how much the records give
      const per = s.periods, many = per.length > 1;
      const span = many ? `${per.length} war patrols, ${d3.utcFormat("%b %Y")(d3.min(lines, f => Date.parse(f.properties.start)))} – ${d3.utcFormat("%b %Y")(d3.max(lines, f => Date.parse(f.properties.end)))}`
        : `${per[0].name[0] + per[0].name.slice(1).toLowerCase()}, ${per[0].dates}`;
      const nAtk = attacks.length;
      card.append("h3").html(`<a href="${url}">${esc(name)}</a> <span class="hull">${esc(s.hull)}</span>`);
      card.append("p").text(`${s.class}-class ${s.kind}`);
      card.append("p").text(span);
      if (!many && per[0].area) card.append("p").text(per[0].area);
      card.append("p").text(`${points.length} positions${s.kind === "submarine" ? ` · ${nAtk} torpedo attack${nAtk === 1 ? "" : "s"}` : ""}`);
      if (many) card.append("p").attr("class", "pn")
        .html(`Patrol ${per.map(p => `<a href="${url}&amp;patrol=${p.n}" title="${esc(`${p.name}, ${p.dates}${p.area ? `: ${p.area}` : ""}`)}">${p.n}</a>`).join(" ")}`);
    }
  }
}

// ── What else is in each chapter, and what's still to find ──────────────────────────────────────
async function lists() {
  const [ships, army, battles, invText] = await Promise.all([d3.json(RECORDS + "ships.json"), d3.json(RECORDS + "army/army.json"),
    d3.json(RECORDS + "battles/index.json"), d3.text(RECORDS + "inventory.yml")]);
  const inv = jsyaml.load(invText);
  const word = { mapped: "on the map", transcribed: "transcribed, not yet drawn", available: "<b>found, not transcribed</b>",
    found: "<b>found, not transcribed</b>", "not-searched": "<b>not looked for yet</b>", missing: "looked for, not found" };
  const month = d => d3.utcFormat("%b %Y")(new Date(d));
  const row = (when, what, state, todo) => `<tr class="${todo ? "todo" : ""}"><td class="when">${when}</td><td class="what">${what}</td><td class="state">${state}</td></tr>`;
  const table = (id, title, rows) => { document.getElementById(id).innerHTML = `<h4>${title}</h4><table><tbody>${rows.join("")}</tbody></table>`; };

  // Pacific: the engagements, then each vessel and battalion (a boat's patrols on one row), by date
  const periodStart = dates => { const [a, b = a] = dates.split("–").map(x => x.trim()); const yr = /\d{4}/.exec(b)?.[0];
    return Date.parse(/\d{4}/.test(a) ? `${a} UTC` : /[A-Za-z]/.test(a) ? `${a} ${yr} UTC` : `${a} ${b.replace(/^\d+\s*/, "")} UTC`); };
  const pac = [];
  for (const b of battles) pac.push([Date.parse(b.start), row(month(Date.parse(b.start)), `<a href="battle.html?e=${b.id}">${esc(b.title)}</a>`, "both sides, one clock")]);
  for (const s of ships.filter(s => s.alias !== "solar")) {
    const d = d3.min(s.periods, p => periodStart(p.dates));
    const sub = s.kind === "submarine";
    const what = sub && s.periods.length > 1
      ? `${s.name} (${s.hull}), war patrols ${s.periods.map(p => `<a href="patrols.html?ship=${s.alias}&amp;patrol=${p.n}">${p.n}</a>`).join(", ")}`
      : `<a href="patrols.html?ship=${s.alias}">${sub ? `${s.name} (${s.hull}), ${esc(s.periods[0].name.toLowerCase())}` : `USS ${s.name} (${s.hull}), ${esc(s.periods[0].name)}`}</a>`;
    pac.push([d, row(month(d), what, "on the map")]);
  }
  const ordinal = n => n + (/1[123]$/.test(n) ? "th" : { 1: "st", 2: "nd", 3: "rd" }[n % 10] || "th");
  for (const [k, u] of Object.entries(inv.seabees || {})) if (u.record?.from)
    pac.push([Date.parse(u.record.from), row(month(Date.parse(u.record.from)), `<a href="seabees.html?unit=${k}">${ordinal(parseInt(k))} Naval Construction Battalion</a>`, word[u.record.status] || u.record.status)]);
  pac.sort((a, b) => a[0] - b[0]);
  const pacTodo = [];
  for (const [hull, b] of Object.entries(inv.boats || {})) {
    if (!b.folder) pacTodo.push(row("", `${b.name} (${hull}): ${esc(b.note || "")}`, Object.keys(b.patrols || {}).length ? word[Object.values(b.patrols)[0].status] : word["not-searched"], true));
  }
  const cs = inv.commands?.comsubpac?.records || {};
  const n = s => Object.values(cs).filter(r => r.status === s).length;
  pacTodo.push(row("1944–45", "Submarine Force, Pacific: its monthly war diaries", `${n("transcribed")} transcribed, <b>${n("available")} found, not transcribed</b>`, true));
  table("also-pacific", "Also in the Pacific, by date", [...pac.map(r => r[1]), ...pacTodo]);

  // Atlantic: Solar's records
  const sol = Object.entries(inv.ships?.["DE-221"]?.records || {}).map(([k, r]) =>
    row(/^\d{4}-\d{2}$/.test(k) ? month(k + "-01") : "", `USS Solar (DE-221): ${esc(r.note || k)}`, word[r.status] || r.status, r.status !== "mapped"));
  table("also-atlantic", "Also in the Atlantic", sol);

  // Europe: the Army units by date, and what's still to find
  const eur = army.units.map(u => {
    const a = u.stations[0].date, b = u.stations[u.stations.length - 1].date;
    return [Date.parse(a), row(month(a), `<a href="army.html?unit=${u.unit}">${esc(u.name)}</a>, to ${month(b)}`, `${u.stations.length} stations on the map`)];
  }).sort((a, b) => a[0] - b[0]).map(r => r[1]);
  const after = part => { const m = /^after-(\d{4})-(\d{2})$/.exec(part); return m ? `its records after ${d3.utcFormat("%B %Y")(new Date(Date.UTC(+m[1], +m[2] - 1)))} (not online)` : part; };
  for (const [k, u] of Object.entries(inv.units || {})) for (const [part, r] of Object.entries(u)) if (part !== "record")
    eur.push(row("", `${esc(army.units.find(x => x.unit === k)?.name || k)}: ${after(part)}`, word[r.status] || r.status, true));
  table("also-europe", "Also in North Africa and Europe, by date", eur);

  // Wanted: everything the inventory knows of and nobody has done
  const wanted = [];
  for (const [hull, b] of Object.entries(inv.boats || {})) if (!b.folder) wanted.push(`${b.name} (${hull}) war patrol reports: ${esc(b.note || "")}`);
  if (n("available")) wanted.push(`The Submarine Force, Pacific war diary: ${n("available")} months found and waiting to be transcribed`);
  for (const [k, r] of Object.entries(inv.ships?.["DE-221"]?.records || {})) if (r.status === "found") wanted.push(`USS Solar: ${esc(r.note)}`);
  wanted.push("The Japanese and German records of the attacks still read from one side only (the Strait of Gibraltar, 17 February 1945; JV 44 on 26 April 1945)");
  document.getElementById("wanted").innerHTML = wanted.map(w => `<li>${w}</li>`).join("");
}

// A figure whose records don't load says so in its place instead of leaving a blank
const failed = (sel, what) => err => {
  console.error(err);
  const p = document.createElement("p");
  p.className = "readout";
  p.textContent = `The records for this ${what} didn't load. Reload the page to try again.`;
  document.querySelector(sel).replaceChildren(p);
};
replay().catch(failed("#replay", "replay"));
haynsworth().catch(failed("#fig-haynsworth", "figure"));
seabees().catch(failed("#fig-seabees", "figure"));
solar().catch(failed("#fig-solar", "map"));
neuburg().catch(failed("#fig-neuburg", "figure"));
fleet().catch(failed("#fleet", "list"));
lists().catch(failed("#wanted", "list"));
