// engagement.html?e=<id>: one engagement from both sides' records. Reads records/engagements/index.json and
// records/engagements/<id>/engagement.json (tools/build_engagement.py); the computation is engage.js's, the shared
// drawing engage-views.js's. Encodings: guides/ENGAGEMENTS.md.
(async () => {
  const E = Engage, esc = EV.esc;
  const index = await fetch(RECORDS + "engagements/index.json").then(r => r.json());
  const want = new URLSearchParams(location.search).get("e");
  const id = index.some(x => x.id === want) ? want : "tama-17-1944-04-29";
  const [D, world] = await Promise.all([fetch(`${RECORDS}engagements/${id}/engagement.json`).then(r => r.json()),
    d3.json(EV.LAND_10M), SILHOUETTES]);
  const LAND = EV.land(world);
  const crumb = document.getElementById("crumb");
  Chapter.crumb(id, crumb).then(() => { crumb.hidden = !crumb.innerHTML; }, () => { crumb.hidden = true; });

  // ---------- the picker: every engagement, by theatre, in date order
  const THEATRES = { pacific: "Pacific", mediterranean: "Mediterranean", europe: "Europe" };
  const sel = document.getElementById("engagement");
  sel.innerHTML = Object.entries(THEATRES).map(([k, name]) => {
    const xs = index.filter(x => x.theater === k);
    return xs.length ? `<optgroup label="${name}">${xs.map(x => `<option value="${x.id}"${x.id === id ? " selected" : ""}>${esc(x.title)}${x.boats.length ? " · " + esc(x.boats.join(", ")) : ""}</option>`).join("")}</optgroup>` : "";
  }).join("");
  sel.addEventListener("change", () => { location.search = "?e=" + encodeURIComponent(sel.value); });

  // ---------- who's who, and their colours (colour follows the boat; the Japanese side is ink; red is for hits)
  const PARTS = D.participants;
  const byId = Object.fromEntries(PARTS.map(p => [p.id, p]));
  const SIDE_NAME = { us: "US", jp: "Japanese", allied: "Allied", axis: "Axis", de: "German", press: "Press", geo: "Place" };
  const sideColour = s => (s === "jp" || s === "axis" || s === "de") ? "var(--japan)" : s === "press" || s === "geo" ? "var(--ink-3)" : "var(--ink-2)";
  const colour = idOrSide => byId[idOrSide]?.colour ? `var(--c${byId[idOrSide].colour})` : byId[idOrSide] ? sideColour(byId[idOrSide].side) : sideColour(idOrSide);
  const evColour = e => byId[e.actor] ? colour(e.actor) : sideColour(e.side);
  const nameOf = a => byId[a]?.name || a;
  const TRACKED = PARTS.filter(p => (D.tracks[p.id] || []).length);
  // one lane per tracked ship or boat, then one per side for everyone else
  const laneOf = e => byId[e.actor] && TRACKED.includes(byId[e.actor]) ? e.actor : "side:" + e.side;
  const LANES = [...TRACKED.map(p => ({ id: p.id, name: p.name, colour: colour(p.id) })),
    ...[...new Set(D.events.map(e => laneOf(e)).filter(l => l.startsWith("side:")))].map(l => ({ id: l, name: SIDE_NAME[l.slice(5)] || l.slice(5), colour: sideColour(l.slice(5)) }))];

  // ---------- time: GMT where the records give a zone; otherwise the records' own local clock
  const tOf = e => E.T(e.utc || e.key);
  D.events.forEach(e => { e.ms = tOf(e); });
  const timed = D.events.filter(e => e.ms != null && !Number.isNaN(e.ms));
  let t0 = D.window ? E.T(D.window.from) : d3.min(timed, e => e.ms), t1 = D.window ? E.T(D.window.to) : d3.max(timed, e => e.ms);
  if (t1 - t0 < 3600e3) { t0 -= 1800e3; t1 += 1800e3; }
  // ---------- the tempo decides which view leads (guides/OPERATIONS-VIEWER.md, 3). Clocked: the map plays and the log
  // follows it, as below. Dated or monthly: there is no clock to play, so the time controls and the log go, the map
  // stands still with every mark shown, and the chronology leads, full width, where the log was.
  const TEMPO = E.tempo(D.events), CLOCKED = TEMPO === "clocked";
  if (!CLOCKED) {
    document.querySelector(".time").hidden = true;
    document.querySelector(".side").hidden = true;
    document.getElementById("action").classList.add("dated");
  }
  const OWN = D.clock && D.gmt ? D.clock : (D.theater === "pacific" && D.gmt ? "I" : "");
  const OWN_NAME = { I: "Item (Tokyo time)", B: "Baker", K: "King", H: "How" };
  document.getElementById("clock-zone").textContent = D.gmt ? "GMT" : "local time (the records give no zone)";
  const clockText = ms => `${E.hhmm(ms)} · ${E.day(ms)}`;

  // ---------- header and story
  const secs = D.sections || [];
  const top = secs.find(s => !s.heading);
  document.title = D.short || D.title;
  document.getElementById("eyebrow").textContent = D.eyebrow || "";
  document.getElementById("title").textContent = D.title;
  const render = s => Links.render(s, { cites: D.cites || {} });
  if (top && top.paras.length) document.getElementById("lede").innerHTML = render(top.paras[0].text);
  document.getElementById("story").innerHTML = secs.map((s, i) => {
    const paras = s === top ? s.paras.slice(1) : s.paras;
    if (!s.heading && !paras.length) return "";
    return `${s.heading ? `<h2>${esc(s.heading)}</h2>` : ""}${paras.map(p => `<p class="${p.aside ? "aside" : ""}">${render(p.text)}</p>`).join("")}`;
  }).join("");

  // ---------- legend: only the marks this engagement has
  const has = f => D.events.some(f);
  document.getElementById("legend").innerHTML = [
    ...TRACKED.map(p => `<span class="boat"><svg width="22" height="10"><line x1="1" y1="5" x2="21" y2="5" stroke="${colour(p.id)}" stroke-width="2.5"/></svg>${esc(p.name)}</span>`),
    has(e => e.kind === "attack") && `<span>${EV.legendMark.attack("var(--ink-2)")}Torpedo attack</span>`,
    D.fixes.some(f => f.on_track) && `<span><svg width="10" height="10" viewBox="-5 -5 10 10"><circle r="3.5" fill="var(--ink-2)"/></svg>Reported position</span>`,
    D.fixes.some(f => f.kind === "ship") && `<span>${EV.legendMark.sighted("var(--ink-2)")}Ship sighted (the target's position)</span>`,
    has(e => e.mark === "sunk" && e.lat != null) && `<span>${EV.legendMark.sunk}Sunk (Japanese record)</span>`,
    has(e => e.mark === "hit" && e.lat != null) && `<span>${EV.legendMark.hit}Hit, not sunk</span>`,
    has(e => e.mark === "miss" && e.lat != null) && `<span>${EV.legendMark.miss}Attacked, no damage</span>`,
    has(e => e.kind === "contact_report") && `<span><svg width="24" height="10"><line x1="1" y1="5" x2="23" y2="5" class="msg" stroke="var(--ink-2)"/></svg>Contact report, sender to each boat it went to</span>`,
    D.fixes.some(f => !f.on_track && f.kind !== "ship") && `<span><svg width="12" height="12" viewBox="-6 -6 12 12"><circle r="4.5" fill="none" stroke="var(--ink-2)" stroke-width="1.4" stroke-dasharray="2 2"/></svg>Contradicted in the report</span>`,
    D.positions.length && `<span><svg width="10" height="10" viewBox="-5 -5 10 10"><rect x="-3" y="-3" width="6" height="6" fill="var(--ink-3)"/></svg>A place in the records</span>`,
  ].filter(Boolean).join("");

  // ---------- map
  const svg = d3.select("#map");
  const gLand = svg.append("g"), gGrat = svg.append("g"), gPlace = svg.append("g"), gTrk = svg.append("g"), gMsg = svg.append("g"),
        gNowName = svg.append("g"), gMk = svg.append("g"), gNow = svg.append("g"), gPulse = svg.append("g");
  let proj = null, W = 0, H = 0, quiet = false, t = t1, playing = false, raf = 0, lastT = null;
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const view = mapZoom(svg.node(), document.querySelector(".map-box"), () => { if (proj && !quiet) { drawStatic(); drawFrame(); } },
                       { capture: true, max: 12, at: "bottom-right" });
  const ruler = scaleBar(document.querySelector(".map-box"), { units: ["nm"] });
  const P = (lon, lat) => proj([lon, lat]);
  if (!D.box) document.querySelector(".map-box").hidden = true;

  function drawStatic() {
    if (!D.box) return;
    const el = svg.node(); W = el.clientWidth; H = el.clientHeight;
    const b = D.box, m = Math.min(44, W * 0.06);
    proj = d3.geoMercator().fitExtent([[m, 26], [W - m, H - 34]], { type: "MultiPoint", coordinates: [[b[0], b[1]], [b[2], b[3]], [b[0], b[3]], [b[2], b[1]]] });
    view.bound(W, H);
    mapZoom.scaled(proj, { scale: proj.scale(), translate: proj.translate() }, view.transform());
    ruler.update(p => proj.invert(p));
    gLand.selectAll("path").data([LAND]).join("path").attr("class", "land").attr("d", d3.geoPath(proj));
    EV.graticule(gGrat, proj, W, H);
    const inView = ([x, y]) => x > 30 && x < W - 30 && y > 24 && y < H - 24;
    gPlace.selectAll("*").remove();
    D.places.filter(p => inView(P(p.lon, p.lat))).forEach(p => gPlace.append("text").attr("class", "place")
      .attr("x", P(p.lon, p.lat)[0]).attr("y", P(p.lon, p.lat)[1]).attr("text-anchor", "middle").style("font-size", p.small ? "10px" : null).text(p.name));
    drawMarks();
  }

  function drawMarks() {
    const items = [];
    D.fixes.filter(f => f.kind !== "attack" && !f.ref.endsWith(" fired")).forEach(f =>
      items.push({ k: f.kind === "ship" ? "ship" : f.on_track ? "fix" : "off", f, ms: E.T(f.utc), lon: f.lon, lat: f.lat }));
    d3.groups(D.events.filter(e => e.kind === "attack" && e.lat != null), e => e.actor + Math.round(e.lat * 30) + "," + Math.round(e.lon * 30))
      .forEach(([, es]) => items.push({ k: "attack", es, ms: d3.min(es, e => e.ms), lon: es[0].lon, lat: es[0].lat, who: es[0].actor, doubt: es.every(e => e.note) }));
    d3.groups(D.events.filter(e => e.origin === "japanese" && e.lat != null), e => e.lat + "," + e.lon)
      .forEach(([, es]) => items.push({ k: "jp", es, ms: d3.min(es, e => e.ms), lon: es[0].lon, lat: es[0].lat }));
    D.positions.filter(r => r.lat != null).forEach(r => items.push({ k: "pos", r, ms: -Infinity, lon: r.lon, lat: r.lat }));
    const order = { pos: 0, off: 1, ship: 2, fix: 3, jp: 4, attack: 5 };
    items.sort((a, b) => order[a.k] - order[b.k]);
    const sel = gMk.selectAll("g.mk").data(items).join("g").attr("class", d => "mk " + d.k)
      .attr("transform", d => `translate(${P(d.lon, d.lat).map(v => v.toFixed(1))})`);
    sel.selectAll("*").remove();
    const labelled = new Set();
    sel.each(function (d) {
      const g = d3.select(this);
      if (d.k === "fix") { g.append("circle").attr("r", 5).attr("fill", "var(--surface)"); g.append("circle").attr("r", 3.5).attr("fill", colour(d.f.who)); }
      if (d.k === "off") g.append("circle").attr("r", 4.5).attr("fill", "none").attr("stroke", colour(d.f.who)).attr("stroke-width", 1.4).attr("stroke-dasharray", "2 2");
      if (d.k === "ship") g.append("circle").attr("r", 4.5).attr("fill", "var(--surface)").attr("stroke", colour(d.f.who)).attr("stroke-width", 1.8).attr("stroke-dasharray", contradicts(d.f) ? "2 2" : null);
      if (d.k === "attack") {
        g.append("path").attr("d", EV.shape.diamond).attr("transform", "scale(1.25)").attr("fill", "var(--surface)");
        g.append("path").attr("d", EV.shape.diamond).attr("transform", "scale(1.1)").attr("fill", d.doubt ? "var(--surface)" : colour(d.who))
          .attr("stroke", colour(d.who)).attr("stroke-width", d.doubt ? 1.6 : 0).attr("stroke-dasharray", d.doubt ? "2 2" : null);
      }
      if (d.k === "jp") {
        const worst = d.es.some(e => e.mark === "sunk") ? "sunk" : d.es.some(e => e.mark === "hit") ? "hit" : "miss";
        EV.outcomeMark(g, worst, d.es.every(e => e.basis === "secondary"));
        const names = d.es.flatMap(e => (e.title || "").replace(/ Maru/g, "").split(/ and |, /)).filter(Boolean), key = [...names].sort().join("+");
        if (names.length && !labelled.has(key)) {
          labelled.add(key);
          g.append("text").attr("class", "mk-label").attr("x", -9).attr("y", 4).attr("text-anchor", "end").text([...new Set(names)].join(" + "));
        }
      }
      if (d.k === "pos") {
        g.append("rect").attr("x", -3).attr("y", -3).attr("width", 6).attr("height", 6).attr("fill", sideColour(d.r.side))
          .attr("fill-opacity", d.r.basis === "assumed" || d.r.basis === "approx" || d.r.basis === "hand-placed" ? 0.35 : 1);
        if (D.positions.length <= 15) g.append("text").attr("class", "port").attr("x", 6).attr("y", -5).text(d.r.label);   // many: on hover
      }
      g.append("circle").attr("r", 11).attr("fill", "transparent");
    });
    sel.on("mouseenter", (ev, d) => EV.showTip(ev, tipHTML(d))).on("mousemove", EV.moveTip).on("mouseleave", EV.hideTip)
      .on("click", (ev, d) => { if (d.ms > -Infinity) { stop(); setTime(d.ms); highlightRow(d.ms); } });
  }

  const srcLine = c => c && c.href ? `<div class="i">${esc(c.source_title || "")} ${esc(c.label || "")} · click a log entry for the page</div>` : "";
  function tipHTML(d) {
    if (d.k === "attack" || d.k === "jp") return d.es.map(e => `<div class="v">${esc(nameOf(e.actor))} · ${esc(e.title)}</div><div class="k">${clockText(e.ms)} ${D.gmt ? "GMT" : ""} · ${esc(e.local)}</div><div class="m">${esc(e.words)}</div>${(e.outcome || []).map(o => `<div class="m"><b>Japanese side (${esc(o.relation)}).</b> ${esc(o.note)}</div>`).join("")}${e.note ? `<div class="i">${esc(e.note)}</div>` : ""}`).join("<hr>");
    if (d.k === "pos") return `<div class="v">${esc(d.r.label)}</div><div class="k">${esc([d.r.date, d.r.time].filter(Boolean).join(" "))}${d.r.basis ? " · " + esc(d.r.basis) : ""}${d.r.resolved ? " · " + esc(d.r.resolved) : ""}</div>${d.r.note ? `<div class="m">${esc(d.r.note)}</div>` : ""}<div class="i">${esc(d.r.source || "")}</div>`;
    const f = d.f, what = d.k === "ship" ? "Sighted: the target's position, not the boat's" : d.k === "off" ? "Left off the track" : "Reported position";
    return `<div class="v">${esc(nameOf(f.who))} · ${esc(f.ref)}</div><div class="k">${esc(f.raw)} · ${clockText(E.T(f.utc))} GMT · ${esc(f.local)}</div><div class="m">${what}. ${esc(f.note)}</div>${f.fix ? `<div class="i">${esc(f.fix)}</div>` : ""}`;
  }

  // ---------- firing pulses, and contact reports (a ring on the sender's track and a dotted line to each recipient)
  // a boat whose attack table and narrative both time an attack pulses once, at the narrative's time (to the second)
  const attacks = D.events.filter(e => e.kind === "attack" && e.origin === "track");
  const num = e => e.actor + ":" + ((e.title.match(/Attack (\d+)/) || [])[1]);
  const narrated = new Set(attacks.filter(e => e.title.includes("(narrative)")).map(num));
  const fires = attacks.filter(e => e.title.includes("(narrative)") || !narrated.has(num(e)))
    .map(e => ({ ms: e.ms, at: () => E.posAt(D.tracks[e.actor] || [], e.ms) || [e.lon, e.lat] }));
  function pulse(f) {
    const [x, y] = P(...f.at());
    if (reduced) { const c = gPulse.append("circle").attr("class", "fire").attr("cx", x).attr("cy", y).attr("r", 14).attr("stroke-width", 2.5); setTimeout(() => c.remove(), 1100); return; }
    gPulse.append("circle").attr("class", "fire-core").attr("cx", x).attr("cy", y).attr("r", 6).transition().duration(700).attr("opacity", 0).remove();
    [0, 280].forEach(delay => gPulse.append("circle").attr("class", "fire").attr("cx", x).attr("cy", y).attr("r", 5).attr("stroke-width", 3)
      .transition().delay(delay).duration(1300).ease(d3.easeCubicOut).attr("r", 30).attr("stroke-width", 0.5).attr("opacity", 0).remove());
  }
  const MSGS = D.events.filter(e => e.kind === "contact_report" && e.ms != null);
  function drawMessages() {
    const live = MSGS.filter(m => t >= m.ms && t - m.ms < 3 * 3600e3);
    const rows = [];
    live.forEach(m => {
      const a = E.posAt(D.tracks[m.actor] || [], m.ms);
      if (!a) return;
      const fade = 1 - (t - m.ms) / (3 * 3600e3);
      rows.push({ k: "ring", a, m, fade });
      (m.to || []).forEach(r => { const b = E.posAt(D.tracks[r] || [], t); if (b) rows.push({ k: "line", a, b, m, fade }); });
    });
    gMsg.selectAll("*").remove();
    rows.forEach(r => {
      if (r.k === "ring") gMsg.append("circle").attr("cx", P(...r.a)[0]).attr("cy", P(...r.a)[1]).attr("r", 9).attr("fill", "none")
        .attr("stroke", colour(r.m.actor)).attr("stroke-width", 1.6).attr("opacity", r.fade);
      else gMsg.append("line").attr("class", "msg").attr("stroke", colour(r.m.actor)).attr("opacity", r.fade)
        .attr("x1", P(...r.a)[0]).attr("y1", P(...r.a)[1]).attr("x2", P(...r.b)[0]).attr("y2", P(...r.b)[1]);
    });
  }

  function drawFrame() {
    if (proj) {
      const line = d3.line().x(p => P(...p)[0]).y(p => P(...p)[1]);
      const rows = [], nows = [];
      TRACKED.forEach(p => {
        const pts = D.tracks[p.id], now = E.posAt(pts, t);
        const past = pts.filter(q => E.T(q.utc) <= t).map(q => [q.lon, q.lat]), ahead = pts.filter(q => E.T(q.utc) > t).map(q => [q.lon, q.lat]);
        if (now) { past.push(now); ahead.unshift(now); nows.push({ p, now }); }
        rows.push({ id: p.id, cls: "past", pts: past }, { id: p.id, cls: "ahead", pts: ahead });
      });
      gTrk.selectAll("path").data(rows).join("path").attr("class", d => "trk " + d.cls).attr("stroke", d => colour(d.id)).attr("d", d => d.pts.length > 1 ? line(d.pts) : null);
      gMk.selectAll("g.mk").classed("future", d => CLOCKED && d.ms > t);   // no clock: everything is shown
      if (lastT !== null && t !== lastT) fires.filter(f => (f.ms > lastT && f.ms <= t && t - lastT < 3 * 3600e3) || f.ms === t).forEach(pulse);
      lastT = t;
      drawMessages();
      const ng = gNow.selectAll("g").data(nows, d => d.p.id).join(enter => {
        const g = enter.append("g");
        g.append("circle").attr("r", 10).attr("fill", d => colour(d.p.id)).attr("opacity", 0.22);
        g.append("circle").attr("r", 5).attr("fill", d => colour(d.p.id)).attr("stroke", "var(--surface)").attr("stroke-width", 2);
        return g;
      });
      ng.attr("transform", d => `translate(${P(...d.now).map(v => v.toFixed(1))})`);
      gNowName.selectAll("text").data(nows, d => d.p.id).join("text").attr("class", "now-name").text(d => d.p.name)
        .attr("x", d => P(...d.now)[0] + 11).attr("y", d => P(...d.now)[1] - 9);
    }
    document.getElementById("clock").textContent = clockText(t);
    document.getElementById("clock-own").textContent = OWN ? `${OWN_NAME[OWN] || OWN} ${clockText(t + E.zoneHours(OWN) * 3600e3)}` : "";
    document.getElementById("scrub").value = t;
    drawCursor();
    updateLog();
    updateClosing();
  }

  // ---------- lanes
  const lanes = d3.select("#lanes");
  let lx = null;
  function drawLanes() {
    if (!CLOCKED) return;
    const laneH = 17, top = 4, left = 104;
    lanes.style("height", `${top + LANES.length * laneH + 24}px`);
    const w = lanes.node().clientWidth;
    lx = d3.scaleUtc().domain([t0, t1]).range([left, w - 8]);
    lanes.selectAll("*").remove();
    LANES.forEach((L, i) => {
      const y = top + i * laneH + laneH / 2;
      lanes.append("line").attr("class", "lane-line").attr("x1", left).attr("x2", w - 8).attr("y1", y).attr("y2", y);
      lanes.append("text").attr("class", "lane-label").attr("x", 0).attr("y", y + 4).text(L.name.length > 14 ? L.name.slice(0, 13) + "…" : L.name);
      timed.filter(e => laneOf(e) === L.id && e.ms >= t0 && e.ms <= t1).forEach(e => {
        const x = lx(e.ms);
        if (e.kind === "attack") lanes.append("path").attr("d", EV.shape.diamond).attr("transform", `translate(${x},${y}) scale(0.95)`).attr("fill", L.colour);
        else if (e.mark) EV.outcomeMark(lanes.append("g").attr("transform", `translate(${x},${y}) scale(0.75)`), e.mark, e.basis === "secondary");
        else if (e.kind === "contact_report") lanes.append("circle").attr("cx", x).attr("cy", y).attr("r", 4).attr("fill", "none").attr("stroke", L.colour).attr("stroke-width", 1.6);
        else lanes.append("line").attr("x1", x).attr("x2", x).attr("y1", y - 4).attr("y2", y + 4).attr("stroke", e.kind === "depth_charge" ? L.colour : "var(--ink-3)").attr("stroke-width", 1.5);
      });
    });
    const axisY = top + LANES.length * laneH + 4, ax = lanes.append("g").attr("class", "axis");
    lx.ticks(w < 500 ? 4 : 8).forEach(d => {
      ax.append("line").attr("x1", lx(d)).attr("x2", lx(d)).attr("y1", top).attr("y2", axisY);
      ax.append("text").attr("x", lx(d)).attr("y", axisY + 12).attr("text-anchor", "middle").text(t1 - t0 > 3 * 86400e3 ? E.day(+d) : E.hhmm(+d) + (D.gmt ? "Z" : ""));
    });
    lanes.append("line").attr("class", "cursor").attr("y1", 0).attr("y2", axisY);
    const sc = document.getElementById("scrub");
    sc.min = t0; sc.max = t1; sc.step = 60000;
    drawCursor();
  }
  function drawCursor() { if (lx) lanes.select(".cursor").attr("x1", lx(t)).attr("x2", lx(t)); }
  lanes.on("click", ev => { if (!lx) return; stop(); setTime(+lx.invert(d3.pointer(ev)[0])); });
  document.getElementById("scrub").addEventListener("input", e => { stop(); setTime(+e.target.value); });

  // ---------- the chronology, when the frame has no clock to play: Engage's rows and columns, EV's drawing
  function drawChronology() {
    document.getElementById("chron-card").hidden = CLOCKED;
    if (CLOCKED) return;
    EV.chronology(document.getElementById("chron"), { rows: E.chronologyRows(D.events, TEMPO), columns: E.chronologyColumns(D.events, PARTS), tempo: TEMPO, sideName: s => SIDE_NAME[s] || s, nameOf });
    document.getElementById("chron-title").textContent = TEMPO === "monthly" ? "The records, by the month" : "The records, by the day";
    document.getElementById("chron-note").textContent = (TEMPO === "monthly"
      ? "The entries carry months and days, not times, so there is no clock to play: the map shows every place and position at once, and each column is one record, its entries at the month they are dated. "
      : "The entries carry days, not times, so there is no clock to play: the map shows every place and position at once, and each column is one record, its entries at the day they are dated. ")
      + "A time is as the record wrote it; an entry with none is placed by the order of the account and says so. A station starts a bar in the unit's colour; a casualty or a shelling is named in red.";
  }

  // ---------- the two-sided log
  function drawLog() {
    if (!CLOCKED) return;
    document.getElementById("log").innerHTML = D.events.map((e, i) => {
      const who = byId[e.actor];
      const shape = who && who.sil ? EV.sil(who.sil, evColour(e), { ftPx: 0.1, width: 40 }) : e.side === "jp" ? EV.sil("cargo", "var(--japan)", { width: 40 }) : "";
      const name = who ? who.name : e.actor || SIDE_NAME[e.side];
      const what = e.title && e.title !== name ? `<span class="what">${esc(e.title)}</span>` : e.kind && e.kind !== "log" ? `<span class="what">${esc(e.kind.replace(/_/g, " "))}</span>` : "";
      const toWhom = e.to ? ` <span class="what">to ${e.to.map(r => esc(nameOf(r))).join(" and ")}</span>` : e.from ? ` <span class="what">from ${esc(nameOf(e.from))}</span>` : "";
      const placed = e.placed ? `<div class="assume">${esc(e.placed === "seq" ? "Time placed by the order of the account, not recorded" : e.placed)}</div>` : "";
      return `<div class="row entry${e.basis === "assumed" ? " assumed" : ""}" tabindex="0" data-t="${e.ms ?? ""}" style="--bar:${evColour(e)}">
        <div class="t${e.placed ? " placed" : ""}">${e.ms != null && e.local.length > 10 ? E.hhmm(e.ms) : ""}<small>${e.ms != null ? E.day(e.ms) : esc(e.local)}</small></div>
        <div class="body">
          <div class="who">${shape}<b>${esc(name)}</b>${what}${toWhom}<span class="own">${esc(e.local.slice(11))}</span></div>
          ${e.original ? `<div class="ja" lang="ja">${esc(e.original)}</div><div class="tr">${esc(e.words)} (translated)</div>` : `<div class="said">${esc(e.words || e.title || "")}</div>`}
          ${(e.outcome || []).map(o => `<div class="note"><b>Japanese side (${esc(o.relation.replace(/_/g, " "))}).</b> ${esc(o.note)}</div>`).join("")}
          ${e.note ? `<div class="assume">${esc(e.note)}</div>` : ""}${placed}
          ${e.source ? `<span class="src">${esc(e.source)}</span>` : ""} ${EV.cite(e.cite, "src alone")}
        </div></div>`;
    }).join("");
    document.querySelectorAll("#log .row").forEach(r => {
      const go = () => { if (r.dataset.t) { stop(); setTime(+r.dataset.t); } };
      r.addEventListener("click", ev => { if (!ev.target.closest("a")) go(); });
      r.addEventListener("keydown", ev => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); go(); } });
    });
  }
  let lastCurrent = null;
  function updateLog() {
    const rows = [...document.querySelectorAll("#log .row")];
    let cur = null;
    rows.forEach(r => { const f = r.dataset.t !== "" && +r.dataset.t > t; r.classList.toggle("future", f); if (!f && r.dataset.t !== "") cur = r; });
    rows.forEach(r => r.classList.toggle("current", r === cur));
    if (playing && cur && cur !== lastCurrent) scrollLog(cur);
    lastCurrent = cur;
  }
  function scrollLog(row) { const box = document.getElementById("log"); box.scrollTo({ top: Math.max(0, row.offsetTop - box.clientHeight / 3), behavior: reduced ? "auto" : "smooth" }); }
  function highlightRow(ms) { const r = [...document.querySelectorAll("#log .row")].find(r => +r.dataset.t === ms); if (r) scrollLog(r); }

  // ---------- closing in: each boat's distance from where the convoy was seen
  const boats = TRACKED.filter(p => p.kind === "submarine");
  // a sighting the report itself contradicts (its fix note says so) is left off the convoy's path, and listed
  const contradicts = f => /contradict/i.test(f.fix || "");
  const contradicted = D.fixes.filter(f => f.kind === "ship" && contradicts(f));
  const seen = [...D.fixes.filter(f => f.kind === "ship" && !contradicts(f)).map(f => ({ utc: f.utc, lon: f.lon, lat: f.lat })),
                ...D.events.filter(e => e.origin === "japanese" && e.lat != null && e.utc).map(e => ({ utc: e.utc, lon: e.lon, lat: e.lat }))];
  const PATH = E.observedPath(seen);
  const series = boats.map(b => ({ b, pts: E.closing(D.tracks[b.id], PATH, 160) })).filter(s => s.pts.length > 1);
  let cx = null, cy = null;
  function drawClosing() {
    const card = document.getElementById("closing-card");
    card.hidden = !(Object.keys(D.convoys).length && series.length);
    if (card.hidden) return;
    const s = d3.select("#closing"), w = s.node().clientWidth, h = 220, m = { l: 48, r: 90, t: 12, b: 26 };
    s.selectAll("*").remove();
    cx = d3.scaleUtc().domain([t0, t1]).range([m.l, w - m.r]);
    cy = d3.scaleLinear().domain([0, d3.max(series, x => d3.max(x.pts, p => p.nm)) * 1.05]).nice().range([h - m.b, m.t]);
    const ax = s.append("g").attr("class", "axis");
    cy.ticks(4).forEach(v => { ax.append("line").attr("x1", m.l).attr("x2", w - m.r).attr("y1", cy(v)).attr("y2", cy(v)); ax.append("text").attr("x", m.l - 6).attr("y", cy(v) + 4).attr("text-anchor", "end").text(v + " nm"); });
    cx.ticks(w < 500 ? 4 : 8).forEach(d => ax.append("text").attr("x", cx(d)).attr("y", h - 8).attr("text-anchor", "middle").text(t1 - t0 > 3 * 86400e3 ? E.day(+d) : E.hhmm(+d) + "Z"));
    MSGS.forEach(mm => s.append("line").attr("x1", cx(mm.ms)).attr("x2", cx(mm.ms)).attr("y1", m.t).attr("y2", h - m.b).attr("class", "msg").attr("stroke", colour(mm.actor)));
    D.events.filter(e => e.kind === "attack").forEach(e => s.append("path").attr("d", EV.shape.diamond).attr("transform", `translate(${cx(e.ms)},${h - m.b}) scale(0.8)`).attr("fill", colour(e.actor)));
    const line = d3.line().x(p => cx(p.ms)).y(p => cy(p.nm));
    series.forEach(x => {
      s.append("path").attr("class", "series").attr("stroke", colour(x.b.id)).attr("d", line(x.pts));
      const last = x.pts[x.pts.length - 1];
      s.append("text").attr("class", "direct").attr("x", cx(last.ms) + 6).attr("y", cy(last.nm) + 4).text(`${x.b.name} ${Math.round(last.nm)} nm`);
    });
    s.append("line").attr("class", "cursor").attr("id", "closing-cursor").attr("y1", m.t).attr("y2", h - m.b);
    s.append("rect").attr("x", m.l).attr("y", m.t).attr("width", w - m.l - m.r).attr("height", h - m.t - m.b).attr("fill", "transparent")
      .on("mousemove", ev => {
        const ms = +cx.invert(d3.pointer(ev)[0]);
        const vals = series.map(x => { const p = x.pts.reduce((a, b) => Math.abs(b.ms - ms) < Math.abs(a.ms - ms) ? b : a); return Math.abs(p.ms - ms) < 3600e3 ? `${x.b.name}: ${Math.round(p.nm)} nm` : `${x.b.name}: no position`; });
        EV.showTip(ev, `<div class="v">${clockText(ms)} GMT</div>${vals.map(v => `<div class="m">${esc(v)}</div>`).join("")}<div class="i">Computed from the tracks: a lead, not a record</div>`);
      }).on("mouseleave", EV.hideTip).on("click", ev => { stop(); setTime(+cx.invert(d3.pointer(ev)[0])); });
    document.getElementById("closing-note").innerHTML = `Each line is a boat's distance from where the convoy was seen (${PATH.length} sightings: the boats' ship contacts, at the target's position, and the Japanese record's positions), straight between sightings and only while both are known: computed, a lead, not a record. Dotted rules are contact reports; diamonds are attacks. The navigators disagree by a few miles, so the convoy's path zigzags.${contradicted.length ? ` Left out because the report itself contradicts them: ${contradicted.map(f => `${esc(nameOf(f.who))} ${esc(f.ref)} (${esc(f.fix)})`).join("; ")}.` : ""}`;
  }
  function updateClosing() { if (cx) d3.select("#closing-cursor").attr("x1", cx(t)).attr("x2", cx(t)); }

  // ---------- what the records leave open
  function drawClaims() {
    document.getElementById("claims-card").hidden = !D.claims.length;
    document.getElementById("claims").innerHTML = d3.groups(D.claims, c => c.question).map(([q, cs]) => `<div class="claim"><h3>${esc(q)}</h3><ul>${cs.map(c =>
      `<li><span class="w">${esc(c.weight)}</span><span><span class="a"><b>${esc(c.answer)}</b></span>${c.note ? ` <span class="n">${esc(c.note)}</span>` : ""} <span class="src">${esc(c.source || "")}</span> ${EV.cite(c.cite)}</span></li>`).join("")}</ul></div>`).join("");
  }

  // ---------- order of battle: the kit's silhouettes, true relative size where the library has the class
  function drawOOB() {
    const us = PARTS.filter(p => p.side !== "jp" && !p.convoy && !p.unit), jp = PARTS.filter(p => p.side === "jp" && !p.convoy);
    const army = PARTS.filter(p => p.unit), t0 = d3.utcFormat("%Y-%m-%d")(new Date(E.T(D.window?.from || d3.min(D.events, e => e.key)) || 0));
    const plate = (name, kind, silId, fill, extra = "", cls = "", title = "") => `<div class="plate ${cls}" title="${esc(title)}">${EV.sil(silId, fill, { ftPx: 0.42 })}<div class="nm">${esc(name)}</div><div class="kd">${esc(kind)}</div>${extra}</div>`;
    const usPlates = us.map(p => plate(p.name + (p.hull ? ` (${p.hull})` : ""), [p.co, p.track ? `record: ${p.track}` : p.note].filter(Boolean).join(" · "), p.sil || EV.category(p.kind), colour(p.id), "", "", EV.silWords(p.sil)));
    const convoyHTML = Object.values(D.convoys).map(c => {
      const route = [c.from, ...(c.via || []), c.to].filter(Boolean).join(" → ");
      const ships = [...c.ships].sort((a, b) => (a.role.startsWith("escort") ? 0 : 1) - (b.role.startsWith("escort") ? 0 : 1));
      return `<h3><a href="convoys.html?c=${esc(c.id)}">Convoy ${esc(c.convoy)}</a> ${c.name_ja ? `<span lang="ja">${esc(c.name_ja)}</span>` : ""}</h3>
        <div class="muted" style="margin:-4px 0 10px">${esc(route)}${c.sailed ? ` · sailed ${esc(c.sailed)}` : ""}${c.cargo ? ` · ${esc(c.cargo)}` : ""}</div>
        <div class="plates">${ships.map(s => plate(s.ship, s.role, s.sil || EV.category(s.role), /sunk/.test(s.fate || "") ? "var(--ink)" : "var(--ink-3)",
          s.fate ? `<div class="fate">${esc(s.fate)}</div>` : "", s.basis === "secondary" ? "secondary" : "",
          `${EV.silWords(s.sil, s.sil_basis)}${s.basis === "secondary" ? "; named by a secondary source" : ""}`)).join("")}</div>
        <p class="muted">Silhouettes are drawn to one scale, from the class's own recognition plate where the library has it (hover for which); otherwise the kind of ship only. Italic names come from a secondary source.</p>`;
    }).join("");
    const jpHTML = jp.length ? `<h3>The target</h3><div class="plates">${jp.map(p => plate(p.name, p.note || p.kind, p.sil || EV.category(p.kind), "var(--ink-3)", "", "", "As the boat identified it")).join("")}</div>` : "";
    const armyHTML = army.length ? `<h3>The units</h3><ul class="units">${army.map(p => `<li><a href="army.html?unit=${encodeURIComponent(p.unit)}&amp;t=${t0}">${esc(p.name)}</a>${p.basis && p.basis !== "reported" ? ` <i>(${esc(p.basis)})</i>` : ""}${p.note ? ` <span class="muted">${esc(p.note)}</span>` : ""}</li>`).join("")}</ul>` : "";
    const usHTML = us.length ? `<h3>${us.length > 1 ? "US" : us[0].kind === "submarine" ? "The boat" : "US"}</h3><div class="plates">${usPlates.join("")}</div>` : "";
    document.getElementById("oob").innerHTML = `<div class="pack">${usHTML}${armyHTML}</div><div>${convoyHTML}${jpHTML}</div>`;
  }

  // ---------- time and playback
  function setTime(ms) { t = Math.max(t0, Math.min(t1, ms)); drawFrame(); }
  const playBtn = document.getElementById("play");
  function stop() { playing = false; cancelAnimationFrame(raf); clearTimeout(raf); playBtn.textContent = "▶"; playBtn.setAttribute("aria-label", "Play"); }
  function play() {
    if (t >= t1) t = t0;
    playing = true; playBtn.textContent = "❚❚"; playBtn.setAttribute("aria-label", "Pause");
    if (reduced) {
      const times = timed.map(e => e.ms).filter(x => x > t).sort((a, b) => a - b);
      const step = () => { if (!playing) return; const nx = times.shift(); if (nx == null) { setTime(t1); stop(); return; } setTime(nx); raf = setTimeout(step, 1200); };
      step(); return;
    }
    let last = performance.now();
    const tick = now => { if (!playing) return; t += (now - last) * (t1 - t0) / 45000; last = now; if (t >= t1) { setTime(t1); stop(); return; } drawFrame(); raf = requestAnimationFrame(tick); };
    raf = requestAnimationFrame(tick);
  }
  playBtn.addEventListener("click", () => playing ? stop() : play());

  // ---------- the observer view (observer.js): each attack whose data sheet is transcribed; picking one moves the clock
  const observer = Observer.mount({ D, colour, nameOf, setPageTime: ms => { stop(); setTime(ms); highlightRow(ms); } });
  const sheetOf = e => e && e.kind === "attack" && D.sheets?.[e.actor]?.[e.title.replace(" (narrative)", "")] ? e : null;
  document.getElementById("log").addEventListener("click", ev => {
    const row = ev.target.closest(".row"), e = row && D.events[[...row.parentNode.children].indexOf(row)];
    if (sheetOf(e)) observer.pick(e.actor, e.title.replace(" (narrative)", ""));
  });
  gMk.on("click.observer", ev => { const d = d3.select(ev.target.closest("g.mk")).datum(); const e = d && d.es && d.es.find(sheetOf); if (e) observer.pick(e.actor, e.title.replace(" (narrative)", "")); });

  drawOOB(); drawClaims(); drawLog(); drawChronology(); drawStatic(); drawLanes(); drawClosing(); drawFrame();
  new ResizeObserver(() => { if (D.box) drawStatic(); drawLanes(); drawClosing(); drawFrame(); }).observe(document.querySelector(".wrap"));
})();
