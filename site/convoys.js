// convoys.html?c=<id>: every convoy the boats met (records/convoys/convoys.json, tools/build_engagement.py).
// Routes run through reference/lanes/lanes.yml's nodes: a leg touching an assumed waypoint is dotted, a leg straight
// between two ports dashed. Ships' bars: solid from a Japanese record, outlined from a secondary source, hatched where
// inferred, dotted where the record gives no date. Encodings: guides/ENGAGEMENTS.md.
(async () => {
  const E = Engage, esc = EV.esc;
  const [J, world] = await Promise.all([fetch(RECORDS + "convoys/convoys.json").then(r => r.json()), d3.json(EV.LAND_50M), SILHOUETTES]);
  const LAND = EV.land(world), N = J.lanes, CV = J.convoys;
  const want = new URLSearchParams(location.search).get("c");
  let cur = CV.find(c => c.id === want) || CV.find(c => c.id === "te-04") || CV[0];

  // ---------- the ledger
  const sunk = c => c.ships.filter(s => /^sunk/.test(s.fate || "")).length;
  const grade = xs => xs.some(s => s.basis === "reported" || s.basis === "inferred") ? "●" : xs.length ? "◐" : "○";
  const words = { "●": "from a Japanese record", "◐": "only from a secondary source", "○": "not found yet" };
  const dot = (g, what) => `<td class="dot" title="${esc(what)}: ${words[g]}">${g}</td>`;
  const route = c => [c.from, ...(c.via || []), c.to].filter(Boolean).join(" → ");
  document.getElementById("ledger").innerHTML = `<thead><tr><th>Convoy</th><th>Route</th><th>Met</th><th>Boats</th><th class="num">Ships named</th><th class="num">Sunk</th>
    <th title="Its sailing, from any record">Sailing</th><th title="Its ships, as named">Ships</th><th title="Its escorts">Escorts</th><th title="Stops along the way">Stops</th><th title="Where the boats saw it">Seen</th></tr></thead>
    <tbody>${CV.map(c => {
      const merch = c.ships.filter(s => !/escort/.test(s.role)), esc_ = c.ships.filter(s => /escort/.test(s.role));
      const sailing = c.voyage.find(v => v.event === "sailed");
      return `<tr data-id="${esc(c.id)}" tabindex="0"><td class="nm">${esc(c.convoy)} ${c.name_ja ? `<span lang="ja" data-tr="Convoy ${esc(c.convoy)}, as the Japanese records write it">${esc(c.name_ja)}</span>` : ""}</td><td>${esc(route(c))}</td>
        <td>${c.engagements.map(e => `<a href="engagement.html?e=${esc(e.id)}">${esc(e.short)}</a>`).join(", ")}</td><td>${esc(c.boats.map(b => b.name).join(", "))}</td>
        <td class="num">${c.ships.length}</td><td class="num">${sunk(c)}</td>
        ${dot(sailing ? (sailing.basis === "secondary" ? "◐" : "●") : /secondary/.test(c.sailed || "") ? "◐" : c.sailed ? "●" : "○", "Sailing")}
        ${dot(grade(merch), "Ships")}${dot(grade(esc_), "Escorts")}${dot(c.voyage.filter(v => v.event !== "sailed").length ? grade(c.voyage) : "○", "Stops")}
        ${dot(c.sightings.length ? "●" : "○", "Seen by the boats")}</tr>`;
    }).join("")}</tbody>`;
  document.querySelectorAll("#ledger tbody tr").forEach(tr => {
    const go = () => { cur = CV.find(c => c.id === tr.dataset.id); history.replaceState(null, "", "?c=" + cur.id); draw(); };
    tr.addEventListener("click", ev => { if (!ev.target.closest("a")) go(); });
    tr.addEventListener("keydown", ev => { if (ev.key === "Enter") go(); });
  });

  // ---------- the picked convoy
  const boatColour = (c, id) => `var(--c${c.boats.findIndex(b => b.id === id) + 1})`;
  function draw() {
    const c = cur;
    document.querySelectorAll("#ledger tbody tr").forEach(tr => tr.setAttribute("aria-selected", tr.dataset.id === c.id));
    document.getElementById("v-eyebrow").textContent = `Convoy ${c.convoy}${c.name_ja ? " · " + c.name_ja : ""}`;
    document.getElementById("v-title").textContent = route(c);
    document.getElementById("v-lede").innerHTML = [c.sailed && `Sailed ${esc(c.sailed)}`, c.arrived && `arrived ${esc(c.arrived)}`, c.size && `${esc(c.size)} ships`,
      c.cargo && esc(c.cargo), c.engagements.length && `met by ${esc(c.boats.map(b => b.name).join(", "))}: ${c.engagements.map(e => `<a href="engagement.html?e=${esc(e.id)}">${esc(e.title)}</a>`).join("; ")}`].filter(Boolean).join(" · ");
    document.getElementById("v-story").innerHTML = c.sections.map(s => `${s.heading ? `<h2>${esc(s.heading)}</h2>` : ""}${s.paras.map(p => `<p>${Links.render(p.text)}</p>`).join("")}`).join("");
    drawMap(c);
    drawRoster(c);
  }

  function drawMap(c) {
    const svg = d3.select("#vmap"), W = svg.node().clientWidth, H = svg.node().clientHeight;
    svg.selectAll("*").remove();
    const nodes = (c.route || []).map(id => ({ id, ...N[id] }));
    const pts = [...nodes.map(n => [n.lon, n.lat]), ...c.sightings.map(s => [s.lon, s.lat]), ...c.hits.map(h => [h.lon, h.lat]), ...c.attacks.map(a => [a.lon, a.lat])];
    if (!pts.length) return;
    const proj = d3.geoMercator().fitExtent([[30, 30], [W - 30, H - 30]], { type: "MultiPoint", coordinates: pts });
    const path = d3.geoPath(proj);
    svg.append("path").attr("class", "land").attr("d", path(LAND));
    EV.graticule(svg.append("g"), proj, W, H);
    // the route, leg by leg: dotted where a leg touches an assumed waypoint, dashed straight between two ports
    d3.pairs(nodes).forEach(([a, b]) => svg.append("line").attr("class", "route " + (a.assumed || b.assumed ? "assumed" : "straight"))
      .attr("x1", proj([a.lon, a.lat])[0]).attr("y1", proj([a.lon, a.lat])[1]).attr("x2", proj([b.lon, b.lat])[0]).attr("y2", proj([b.lon, b.lat])[1]));
    [...new Map(nodes.filter(n => n.port).map(n => [n.id, n])).values()].forEach(n => {
      const [x, y] = proj([n.lon, n.lat]), g = svg.append("g").attr("transform", `translate(${x},${y})`);
      g.append("circle").attr("r", 3.5).attr("fill", "var(--surface)").attr("stroke", "var(--ink)").attr("stroke-width", 1.5);
      const stops = c.voyage.filter(v => v.place === n.id);
      g.append("text").attr("class", "port").attr("x", x > W - 120 ? -7 : 7).attr("text-anchor", x > W - 120 ? "end" : "start").attr("y", 4)
        .text(n.name + (stops.length ? " · " + stops.map(v => `${v.event} ${E.day(E.T(v.tokyo))}`).join(", ") : ""));
    });
    const mk = (lon, lat) => svg.append("g").attr("class", "mk").attr("transform", `translate(${proj([lon, lat])})`);
    c.sightings.forEach(s => mk(s.lon, s.lat).call(g => g.append("circle").attr("r", 4.5).attr("fill", "var(--surface)").attr("stroke", boatColour(c, s.who)).attr("stroke-width", 1.8))
      .on("mouseenter", ev => EV.showTip(ev, `<div class="v">${esc(s.name)} · ${esc(s.ref)}</div><div class="k">${esc(s.local)}</div><div class="m">Sighted: the convoy's position as the boat reported it</div>`)).on("mousemove", EV.moveTip).on("mouseleave", EV.hideTip));
    c.attacks.forEach(a => mk(a.lon, a.lat).call(g => g.append("path").attr("d", EV.shape.diamond).attr("fill", boatColour(c, a.who)))
      .on("mouseenter", ev => EV.showTip(ev, `<div class="v">${esc(a.name)} · ${esc(a.title)}</div><div class="k">${E.hhmm(E.T(a.utc))} GMT ${E.day(E.T(a.utc))}</div>`)).on("mousemove", EV.moveTip).on("mouseleave", EV.hideTip));
    c.hits.forEach(h => mk(h.lon, h.lat).call(g => EV.outcomeMark(g, h.mark || "miss", h.basis === "secondary"))
      .on("mouseenter", ev => EV.showTip(ev, `<div class="v">${esc(h.title)}</div><div class="k">${esc(h.local)}</div><div class="m">${esc((h.kind || "").replace(/_/g, " "))} (the Japanese record)</div>`)).on("mousemove", EV.moveTip).on("mouseleave", EV.hideTip));
    document.getElementById("v-legend").innerHTML = [
      ...c.boats.map(b => `<span class="boat"><svg width="12" height="12" viewBox="-6 -6 12 12"><path d="${EV.shape.diamond}" fill="${boatColour(c, b.id)}"/></svg>${esc(b.name)}</span>`),
      `<span>${EV.legendMark.sighted("var(--ink-2)")}Sighted</span>`, `<span>${EV.legendMark.sunk}Sunk</span>`, `<span>${EV.legendMark.hit}Hit</span>`,
      `<span><svg width="26" height="8"><line x1="1" y1="4" x2="25" y2="4" class="route assumed"/></svg>Assumed route</span>`,
      `<span><svg width="26" height="8"><line x1="1" y1="4" x2="25" y2="4" class="route straight"/></svg>Straight between ports</span>`].join("");
    document.getElementById("v-mapnote").textContent = "The route is drawn through reference waypoints, none yet traced from the escorts' charts: an assumption, not a track. The marks are the records': where the boats saw and attacked the convoy, and where the Japanese record puts a ship hit.";
  }

  function drawRoster(c) {
    const svg = d3.select("#roster"), W = svg.node().clientWidth;
    svg.selectAll("*").remove();
    const day = s => s ? E.T(String(s).slice(0, 10)) : null;
    const dates = [...c.voyage.map(v => E.T(v.tokyo)), ...c.ships.flatMap(s => [day(s.from), day(s.to)]), ...c.engagements.flatMap(e => e.window ? [E.T(e.window.from), E.T(e.window.to)] : []),
      day(/^\d{4}-\d\d-\d\d/.test(c.sailed || "") ? c.sailed : null)].filter(x => x != null);
    const lo = d3.utcDay.offset(d3.utcDay.floor(new Date(d3.min(dates))), -1), hi = d3.utcDay.offset(d3.utcDay.ceil(new Date(d3.max(dates))), 1);
    const ships = [...c.ships].sort((a, b) => (/escort/.test(a.role) ? 0 : 1) - (/escort/.test(b.role) ? 0 : 1));
    const rowH = 20, top = 46, left = Math.min(170, W * 0.32), H = top + ships.length * rowH + 30;
    svg.attr("height", H);
    const x = d3.scaleUtc([lo, hi], [left, W - 12]);
    const ax = svg.append("g").attr("class", "axis");
    x.ticks(d3.utcDay.every(Math.max(1, Math.round((hi - lo) / 864e5 / 8)))).forEach(d => {
      ax.append("line").attr("x1", x(d)).attr("x2", x(d)).attr("y1", top - 6).attr("y2", H - 24);
      ax.append("text").attr("x", x(d)).attr("y", H - 8).attr("text-anchor", "middle").text(E.day(+d));
    });
    // the engagements, shaded; the voyage's stops along the top
    c.engagements.filter(e => e.window).forEach(e => svg.append("rect").attr("x", x(E.T(e.window.from))).attr("y", top - 6).attr("height", H - 24 - top + 6)
      .attr("width", Math.max(2, x(E.T(e.window.to)) - x(E.T(e.window.from)))).attr("fill", "var(--wash)"));
    c.voyage.forEach((v, i) => {
      const xx = x(E.T(v.tokyo));
      svg.append("line").attr("x1", xx).attr("x2", xx).attr("y1", top - 10).attr("y2", H - 24).attr("stroke", "var(--ink-3)").attr("stroke-dasharray", v.approx ? "2 3" : null);
      const right = xx > W - 110;
      svg.append("text").attr("class", "lbl").attr("x", right ? xx - 3 : xx + 3).attr("text-anchor", right ? "end" : "start").attr("y", 14 + (i % 2) * 15).text(`${v.event}${v.place ? " " + (N[v.place]?.name || v.place) : ""}`)
        .on("mouseenter", ev => EV.showTip(ev, `<div class="v">${esc(v.at)}</div><div class="m">${esc(v.words || v.event)}</div><div class="i">${esc(v.source)} · ${esc(v.basis)}${v.approx ? " · approximate" : ""}</div>`)).on("mousemove", EV.moveTip).on("mouseleave", EV.hideTip);
    });
    const defs = svg.append("defs");
    defs.append("pattern").attr("id", "hatch").attr("width", 5).attr("height", 5).attr("patternUnits", "userSpaceOnUse").attr("patternTransform", "rotate(45)")
      .append("line").attr("y2", 5).attr("stroke", "var(--ink-2)").attr("stroke-width", 1.6);
    const start = c.voyage.length ? E.T(c.voyage[0].tokyo) : +lo, end = +hi;
    ships.forEach((s, i) => {
      const y = top + i * rowH, g = svg.append("g").attr("transform", `translate(0,${y})`);
      g.append("text").attr("class", "lbl" + (/^sunk/.test(s.fate || "") ? " b" : "")).attr("x", 0).attr("y", 13).style("font-style", s.basis === "secondary" ? "italic" : null)
        .text((s.ship.length > 22 ? s.ship.slice(0, 21) + "…" : s.ship) + (/escort/.test(s.role) ? " ·e" : ""));
      const a = day(s.from), b = day(s.to) != null ? day(s.to) + 864e5 * 0.5 : null;
      const x0 = x(a ?? start), x1 = x(b ?? end);
      // dates not recorded: a dotted line to the edge of what's known
      if (a == null || b == null) g.append("line").attr("x1", x0).attr("x2", x1).attr("y1", 9).attr("y2", 9).attr("stroke", "var(--ink-3)").attr("stroke-dasharray", "1.5 3").attr("stroke-linecap", "round").attr("stroke-width", 1.6);
      if (a != null || b != null) {
        const bx0 = a != null ? x(a) : x(b) - 6, bx1 = b != null ? x(b) : x(a) + 6;
        g.append("rect").attr("class", "bar").attr("x", bx0).attr("y", 3).attr("height", 12).attr("width", Math.max(4, bx1 - bx0))
          .attr("fill", s.basis === "secondary" ? "var(--surface)" : s.basis === "inferred" ? "url(#hatch)" : "var(--ink-2)").attr("stroke", "var(--ink-2)");
      }
      if (s.fate && b != null) {
        const m = g.append("g").attr("transform", `translate(${x(b)},9) scale(0.8)`);
        EV.outcomeMark(m, /^sunk/.test(s.fate) ? "sunk" : /torpedoed|damage/.test(s.fate) ? "hit" : "miss");
      }
      g.append("rect").attr("x", 0).attr("y", 0).attr("width", W).attr("height", rowH).attr("fill", "transparent")
        .on("mouseenter", ev => EV.showTip(ev, `<div class="v">${esc(s.ship)}</div><div class="k">${esc(s.role)}${s.from ? " · from " + esc(s.from) : ""}${s.to ? " · to " + esc(s.to) : ""}</div>${s.fate ? `<div class="m">${esc(s.fate)}</div>` : ""}${s.note ? `<div class="m">${esc(s.note)}</div>` : ""}<div class="i">${esc(s.source || "")} ${esc(s.page || "")} · ${esc(s.basis || "")}</div>`))
        .on("mousemove", EV.moveTip).on("mouseleave", EV.hideTip);
    });
    document.getElementById("v-rosternote").textContent = "Solid: dates from a Japanese record; outlined: a secondary source; hatched: inferred; dotted: the record gives no date, so the ship is shown across what's known of the voyage. ·e marks an escort. Shaded: the days of the engagements. Dates are Tokyo time.";
  }

  draw();
  let rw = 0;
  new ResizeObserver(() => { const w = document.querySelector(".wrap").clientWidth; if (w !== rw) { rw = w; draw(); } }).observe(document.querySelector(".wrap"));
})();
