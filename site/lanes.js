// lanes.html: the convoys on their lanes (records/convoys/convoys.json; nodes from reference/lanes/lanes.yml). Times
// on this page are Tokyo time (the convoys' own), held as if GMT so the axes print them.
(async () => {
  const E = Engage, esc = EV.esc;
  const [J, world] = await Promise.all([fetch(RECORDS + "convoys/convoys.json").then(r => r.json()), d3.json(EV.LAND_50M)]);
  const LAND = EV.land(world), N = J.lanes;
  const tokyo = utc => E.T(utc) + 9 * 3600e3;
  // each convoy's span: its voyage where recorded, else its sailing and arrival, else the days it was met
  const C = J.convoys.filter(c => (c.route || []).length).map(c => {
    const ts = [...c.voyage.map(v => E.T(v.tokyo)), ...c.engagements.filter(e => e.window).flatMap(e => [tokyo(e.window.from), tokyo(e.window.to)]),
      /^\d{4}-\d\d-\d\d/.test(c.sailed || "") ? E.T(c.sailed.slice(0, 10)) : null, /^\d{4}-\d\d-\d\d/.test(c.arrived || "") ? E.T(c.arrived.slice(0, 10)) : null].filter(x => x != null);
    return { ...c, start: d3.min(ts) - 864e5 / 2, end: d3.max(ts) + 864e5 / 2, marks: c.hits.filter(h => h.lat != null) };
  });
  const EDGES = new Map();
  C.forEach(c => d3.pairs(c.route).forEach(([a, b]) => {
    const k = [a, b].sort().join("|");
    if (!EDGES.has(k)) EDGES.set(k, { a, b, convoys: new Set(), assumed: N[a].assumed || N[b].assumed });
    EDGES.get(k).convoys.add(c);
  }));
  const edges = [...EDGES.values()], PORTS = Object.entries(N).filter(([, n]) => n.port);
  const width = d3.scaleSqrt().domain([1, 3]).range([2.2, 8]).clamp(true);
  const extent = [[d3.min(PORTS, ([, n]) => n.lon) - 1, d3.min(PORTS, ([, n]) => n.lat) - 1], [d3.max(PORTS, ([, n]) => n.lon) + 1, d3.max(PORTS, ([, n]) => n.lat) + 1]];

  function frame(svg, W, H, pad) {
    const proj = d3.geoMercator().fitExtent([[pad, pad], [W - pad, H - pad]], { type: "MultiPoint", coordinates: extent });
    svg.attr("height", H).selectAll("*").remove();
    svg.append("path").attr("class", "land").attr("d", d3.geoPath(proj)(LAND));
    return { proj, seg: e => `M${proj([N[e.a].lon, N[e.a].lat])}L${proj([N[e.b].lon, N[e.b].lat])}` };
  }
  const mark = (g, h, r) => { g.attr("transform", g.attr("transform") + ` scale(${r / 5.5})`); EV.outcomeMark(g, h.mark || "miss", h.basis === "secondary"); };
  const hitTip = (c, h) => `<div class="v">${esc(c.convoy)}: ${esc(h.title)}</div><div class="k">${esc(h.local)}</div><div class="m">${esc((h.kind || "").replace(/_/g, " "))}, as the Japanese record has it</div>`;

  // ---------- the network, with a brush
  function drawNetwork() {
    const svg = d3.select("#lanemap"), W = svg.node().clientWidth, H = Math.round(Math.min(W * 0.62, 640));
    const { proj, seg } = frame(svg, W, H, 10);
    const gl = svg.append("g"), ga = svg.append("g"), gp = svg.append("g");
    PORTS.forEach(([, n]) => { const [x, y] = proj([n.lon, n.lat]), g = gp.append("g").attr("transform", `translate(${x},${y})`);
      g.append("circle").attr("r", 3.5).attr("fill", "var(--surface)").attr("stroke", "var(--ink)").attr("stroke-width", 1.5);
      g.append("text").attr("class", "port").attr("x", x > W * 0.7 ? -7 : 7).attr("text-anchor", x > W * 0.7 ? "end" : "start").attr("y", 4).text(n.name); });
    function render(range) {
      const on = c => !range || (c.end >= range[0] && c.start <= range[1]), act = C.filter(on);
      gl.selectAll("*").remove(); ga.selectAll("*").remove();
      edges.forEach(e => {
        const n = [...e.convoys].filter(on).length;
        gl.append("path").attr("class", "lane" + (n ? "" : " idle")).attr("d", seg(e)).attr("stroke-width", n ? width(n) : 1.4);
        gl.append("path").attr("class", "lane-hit").attr("d", seg(e))
          .on("mouseenter", ev => EV.showTip(ev, `<div class="v">${n || "No"} convoy${n === 1 ? "" : "s"} on this lane${range ? " in the months picked" : ""}</div>${[...e.convoys].map(c => `<div class="m">${esc(c.convoy)} · ${esc([c.from, c.to].join(" → "))}</div>`).join("")}<div class="i">${N[e.a].name} to ${N[e.b].name}: an assumed route</div>`))
          .on("mousemove", EV.moveTip).on("mouseleave", EV.hideTip);
      });
      act.forEach(c => c.marks.forEach(h => mark(ga.append("g").attr("transform", `translate(${proj([h.lon, h.lat])})`), h, 5.5)));
      ga.selectAll("g").data(act.flatMap(c => c.marks.map(h => [c, h]))).on("mouseenter", (ev, [c, h]) => EV.showTip(ev, hitTip(c, h))).on("mousemove", EV.moveTip).on("mouseleave", EV.hideTip);
      const sunk = d3.sum(act, c => c.marks.filter(h => h.mark === "sunk").length);
      document.getElementById("shown").innerHTML = range ? `<b>${E.day(+range[0])} – ${E.day(+range[1])} ${new Date(range[1]).getUTCFullYear()}</b>: ${act.length} convoy${act.length === 1 ? "" : "s"} (${act.map(c => esc(c.convoy)).join(", ") || "none"}); ${sunk} record${sunk === 1 ? "" : "s"} of a ship sunk`
        : `<b>All months</b>: ${C.length} convoys on ${edges.length} lane segments. Drag across the voyages below to pick months.`;
    }
    render(null);
    const sw = (w, cls = "lane") => `<svg width="30" height="12"><line x1="2" y1="6" x2="28" y2="6" class="${cls}" stroke-width="${w}"/></svg>`;
    document.getElementById("legend").innerHTML = [`<span>${sw(width(1))}1 convoy</span>`, `<span>${sw(width(2))}2</span>`, `<span>${sw(width(3))}3 or more</span>`,
      `<span>${sw(1.4, "lane idle")}no convoy in the months picked</span>`, `<span>${EV.legendMark.sunk}sunk</span>`, `<span>${EV.legendMark.hit}hit</span>`, `<span>${EV.legendMark.miss}attacked, no damage</span>`].join("");
    // the voyages against the months; brush to pick
    const st = d3.select("#brush"), SW = st.node().clientWidth, rowH = 16, left = 96, SH = 8 + C.length * rowH + 26;
    st.attr("height", SH).selectAll("*").remove();
    if (SW < left + 60) return;   // not laid out yet: the resize observer draws it again
    const x = d3.scaleUtc([d3.utcMonth.floor(new Date(d3.min(C, c => c.start))), d3.utcMonth.ceil(new Date(d3.max(C, c => c.end)))], [left, SW - 10]);
    st.append("g").attr("class", "axis").attr("transform", `translate(0,${SH - 22})`).call(d3.axisBottom(x).ticks(d3.utcMonth.every(1)).tickFormat(d3.utcFormat("%b %Y")).tickSizeOuter(0));
    C.forEach((c, i) => {
      const y = 8 + i * rowH;
      st.append("text").attr("class", "lane-label").attr("x", 0).attr("y", y + 10).text(c.convoy);
      st.append("rect").attr("x", x(c.start)).attr("y", y + 2).attr("height", 10).attr("rx", 2).attr("width", Math.max(4, x(c.end) - x(c.start))).attr("fill", "var(--ink-2)")
        .on("mouseenter", ev => EV.showTip(ev, `<div class="v">${esc(c.convoy)}</div><div class="m">${esc([c.from, ...(c.via || []), c.to].join(" → "))}</div><div class="i">${E.day(c.start)} – ${E.day(c.end)}: its voyage where recorded, else the days it was met</div>`))
        .on("mousemove", EV.moveTip).on("mouseleave", EV.hideTip);
    });
    const brush = d3.brushX().extent([[left, 0], [SW - 10, SH - 22]]).on("brush end", ({ selection }) => render(selection ? selection.map(x.invert) : null));
    st.append("g").attr("class", "brush").call(brush);
  }

  // ---------- month by month
  function drawMonths() {
    const box = document.getElementById("months");
    box.innerHTML = "";
    const months = d3.utcMonths(d3.utcMonth.floor(new Date(d3.min(C, c => c.start))), new Date(d3.max(C, c => c.end)));
    months.forEach(m0 => {
      const m1 = d3.utcMonth.offset(m0, 1), on = c => c.end >= m0 && c.start < m1, act = C.filter(on);
      const fig = d3.select(box).append("figure");
      fig.append("figcaption").html(`${d3.utcFormat("%B %Y")(m0)} <span>${act.map(c => esc(c.convoy)).join(", ") || "no convoy"}</span>`);
      const svg = fig.append("svg"), W = svg.node().clientWidth || 230;
      const { proj, seg } = frame(svg, W, Math.round(W * 0.85), 4);
      edges.forEach(e => { const n = [...e.convoys].filter(on).length; svg.append("path").attr("class", "lane" + (n ? "" : " idle")).attr("d", seg(e)).attr("stroke-width", n ? 1.4 + n : 1); });
      act.forEach(c => c.marks.filter(h => { const t = tokyo(h.utc); return t >= m0 && t < m1; })
        .forEach(h => mark(svg.append("g").attr("transform", `translate(${proj([h.lon, h.lat])})`), h, 3.5)));
    });
  }

  // ---------- one voyage as a timetable: distance along its route against time
  const pick = document.getElementById("pick");
  const withTimes = C.filter(c => c.voyage.length + c.marks.length >= 2);
  pick.innerHTML = withTimes.map(c => `<option value="${c.id}">${esc(c.convoy)} · ${esc([c.from, c.to].join(" → "))}</option>`).join("");
  pick.value = withTimes.some(c => c.id === "hi-67") ? "hi-67" : withTimes[0]?.id;
  pick.addEventListener("change", drawMarey);
  function drawMarey() {
    const c = C.find(x => x.id === pick.value), svg = d3.select("#marey");
    if (!c) return;
    const nodes = c.route.map(id => N[id]), cum = [0];
    for (let i = 1; i < nodes.length; i++) cum.push(cum[i - 1] + E.nm([nodes[i - 1].lon, nodes[i - 1].lat], [nodes[i].lon, nodes[i].lat]));
    function project(p) {   // a point -> distance along the route (nm), and how far off it lies
      let best = { d: Infinity, s: 0 };
      for (let i = 1; i < nodes.length; i++) {
        const a = nodes[i - 1], b = nodes[i], k = Math.cos((a.lat + b.lat) / 2 * Math.PI / 180);
        const ax = a.lon * k, bx = b.lon * k, px = p[0] * k;
        const u = Math.max(0, Math.min(1, ((px - ax) * (bx - ax) + (p[1] - a.lat) * (b.lat - a.lat)) / ((bx - ax) ** 2 + (b.lat - a.lat) ** 2 || 1)));
        const q = [a.lon + u * (b.lon - a.lon), a.lat + u * (b.lat - a.lat)], d = E.nm(p, q);
        if (d < best.d) best = { d, s: cum[i - 1] + u * (cum[i] - cum[i - 1]) };
      }
      return best;
    }
    // the known points: voyage stops at a port (that port's place on the route; the first time it's passed going out,
    // the next one on the way back), and the Japanese record's positions
    let lastIdx = 0;
    const pts = [];
    c.voyage.filter(v => v.place).forEach(v => {
      let i = c.route.indexOf(v.place, lastIdx); if (i < 0) i = c.route.indexOf(v.place);
      lastIdx = i;
      pts.push({ t: E.T(v.tokyo), s: cum[i], what: `${v.event} ${N[v.place].name}`, v, approx: v.approx || v.at.length <= 10 });
    });
    c.marks.forEach(h => { const pr = project([h.lon, h.lat]); pts.push({ t: tokyo(h.utc), s: pr.s, off: pr.d, h }); });
    pts.sort((a, b) => a.t - b.t);
    const W = svg.node().clientWidth, H = 440, L = 110, R = 24, T = 18, B = 34;
    svg.attr("height", H).selectAll("*").remove();
    const x = d3.scaleUtc([d3.utcDay.offset(d3.utcDay.floor(new Date(pts[0].t)), -1), d3.utcDay.offset(d3.utcDay.ceil(new Date(pts.at(-1).t)), 1)], [L, W - R]);
    const y = d3.scaleLinear([0, cum.at(-1)], [T, H - B]);
    svg.append("g").attr("class", "axis").attr("transform", `translate(0,${H - B})`).call(d3.axisBottom(x).ticks(W < 600 ? 5 : 10).tickFormat(d3.utcFormat("%-d %b")).tickSizeOuter(0));
    svg.append("text").attr("class", "speed").attr("x", W - R).attr("y", H - 2).attr("text-anchor", "end").text("Tokyo time");
    const seen = new Set();
    c.route.forEach((id, i) => { if (!N[id].port || seen.has(id + Math.round(cum[i]))) return; seen.add(id + Math.round(cum[i]));
      const g = svg.append("g").attr("class", "station").attr("transform", `translate(0,${y(cum[i])})`);
      g.append("line").attr("x1", L).attr("x2", W - R); g.append("text").attr("x", L - 8).attr("dy", 4).attr("text-anchor", "end").text(N[id].name); });
    d3.pairs(pts).forEach(([a, b]) => {
      svg.append("line").attr("class", "mline" + (a.approx || b.approx ? " unrec" : "")).attr("x1", x(a.t)).attr("y1", y(a.s)).attr("x2", x(b.t)).attr("y2", y(b.s));
      const hrs = (b.t - a.t) / 3600e3, kn = Math.abs(b.s - a.s) / hrs;
      if (hrs > 20) svg.append("text").attr("class", "speed").attr("x", (x(a.t) + x(b.t)) / 2 + 6).attr("y", (y(a.s) + y(b.s)) / 2 + (kn < 0.5 ? -8 : 0))
        .text(kn < 0.5 ? `${Math.round(hrs / 24)} days in port` : `${kn.toFixed(1)} kn${kn < 7 ? " (slow: a stop not recorded?)" : ""}`);
    });
    pts.forEach(p => {
      const g = svg.append("g").attr("transform", `translate(${x(p.t)},${y(p.s)})`);
      if (p.h) mark(g, p.h, 5); else g.append("circle").attr("r", 3.5).attr("fill", "var(--surface)").attr("stroke", "var(--ink)").attr("stroke-width", 1.5);
      g.on("mouseenter", ev => EV.showTip(ev, p.h ? hitTip(c, p.h) + `<div class="i">${Math.round(p.off)} nm off the assumed route</div>`
        : `<div class="v">${esc(c.convoy)} · ${esc(p.what)}</div><div class="k">${esc(p.v.at)}</div><div class="m">${esc(p.v.words || "")}</div><div class="i">${esc(p.v.source)} · ${esc(p.v.basis)}${p.approx ? " · the day only" : ""}</div>`))
        .on("mousemove", EV.moveTip).on("mouseleave", EV.hideTip);
    });
    document.getElementById("marey-note").textContent = `${c.convoy}'s known times: its voyage's stops and the Japanese record's positions, placed along its route (an assumed route, ${Math.round(cum.at(-1))} nm). The slope between two is its average speed; a flat line is time in port. A dotted line has an end recorded only to the day. Speeds are computed, not recorded: a slow leg may be an unrecorded stop, a lead.`;
  }

  const draw = () => { drawNetwork(); drawMonths(); drawMarey(); };
  draw();
  let rw = 0;
  new ResizeObserver(() => { const w = document.querySelector(".wrap").clientWidth; if (w !== rw) { rw = w; draw(); } }).observe(document.querySelector(".wrap"));
})();
