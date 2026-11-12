// The water column: a boat's depth through an engagement, and the water she was in, to scale. A figure for every
// engagement whose boat's depth log is transcribed (the build's `dives` and `water`; panels.js mounts it wherever
// DepthPanel.applies). Two views of the same hours:
//   - her depth against the clock, the counter-attack's logged entries on it (the count and her words), the Japanese
//     pistols' settings as War Damage Report 58 gives them (para 3-10), and the layer from her bathythermograph card;
//   - a section to scale at a moment the reader picks (one foot across = one foot down): her silhouette with its keel at
//     the logged depth, an escort's on the surface (not placed: no record says where), a charge at each setting
//     directly above her and the Bureau's damage distances round it, and the seafloor under her track.
// What is the record's: her depths, words and counts, the layer, the settings. What is ours: the depths between log
// entries (held until the next), periscope and radar depth drawn at 60 ft, the charges' places (nowhere recorded), the
// distances' application to her (the Bureau's are for 300 lb of TNT against the lighter-hulled boats, para 15-12), and
// the peak pressures (Cole's similitude, engage.js). Each is said under the figure. The explainer: depthcharge.html.
window.DepthPanel = (() => {
  const E = Engage, esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const SHALLOW = 60;   // periscope or radar depth, or "submerged" with no depth: drawn at 60 ft (assumed)
  const FT_M = 0.3048;
  // the Bureau's distances for 300 lb of TNT against a light-hulled boat (WDR 58, 15-12): lethal within 25 ft, serious to
  // 40-50, moderate to minor 50-100 and beyond
  const BANDS = [[25, "lethal", "presumed lethal: rupture almost certain"], [50, "serious", "rupture or marked deformation possible"], [100, "moderate", "moderate to minor damage to equipment and fittings"]];
  // the Type 2's Mod 1 charge, 357 lb (WDR 58, 3-9), taken as TNT (assumed), for the peak pressures
  const CHARGE_LB = 357;
  let HULL = { ft: 25, curve: "ss212" };   // set per boat in mount()
  // a "passing" entry is a moment on the way to the depth ordered before it: after it she is held at that order
  const depthOf = st => {
    if (!st || st.state === "surfaced") return 0;
    if (st.goingTo != null) return st.goingTo;
    const m = /(\d+)\s*ft/.exec(st.depth || "");
    return m ? +m[1] : SHALLOW;
  };
  const assumedDepth = st => st && st.state === "submerged" && !/\d+\s*ft/.test(st.depth || "");
  const boats = D => (D.participants || []).filter(p => (D.dives || {})[p.id] && D.dives[p.id].some(s => s.state === "submerged"));

  function mount(host, D) {
    const B = boats(D)[0], states = D.dives[B.id].map((s, i, all) => {
      if (!/^passing/.test(s.depth || "")) return s;
      const order = [...all.slice(0, i)].reverse().find(o => /^\d+\s*ft/.test(o.depth || ""));
      return order ? { ...s, passing: +/(\d+)/.exec(s.depth)[1], goingTo: +/(\d+)/.exec(order.depth)[1] } : s;
    }), water = (D.water || {})[B.id] || { seafloor: [], layers: [] };
    const t0 = E.T(D.window.from), t1 = E.T(D.window.to);
    HULL = E.hullRange(CHARGE_LB, B.hull);
    const stateAt = ms => { let k = null; states.forEach(s => { if (E.T(s.utc) <= ms) k = s; }); return k; };
    const charges = (D.events || []).filter(e => e.actor === B.id && e.kind === "depth_charge" && e.utc).map(e => ({ e, ms: E.T(e.utc) }));
    // the reading nearest the window's middle; the layer is the record's, its depths as typed
    const mid = (t0 + t1) / 2;
    const layer = [...(water.layers || [])].sort((a, b) => Math.abs(E.T(a.date) - mid) - Math.abs(E.T(b.date) - mid))[0];
    const floorAt = ms => { const f = (water.seafloor || []).map(r => ({ utc: r.utc, lon: r.m, lat: 0 })); const p = E.posAt(f, ms); return p ? p[0] / FT_M : null; };
    const deepest = Math.max(...states.map(depthOf), 100);
    const maxY = Math.max(520, Math.ceil((deepest + 90) / 50) * 50);
    const h = d3.select(host);
    const ship = window.SHIPS && SHIPS[B.sil];
    const escort = (D.participants || []).find(p => p.of !== "us" && p.sil && window.SHIPS && SHIPS[p.sil]);
    const colour = `var(--c${B.colour || 1})`;
    let at = charges.length ? charges[0].ms : t0;

    // ---------- the clock: her depth through the hours
    const chart = h.append("svg").attr("class", "dp-chart").attr("role", "img").attr("aria-label", `${B.name}'s depth through the engagement`);
    const sect = h.append("div").attr("class", "dp-section");
    const controls = sect.append("div").attr("class", "dp-controls");
    controls.append("label").attr("for", "dp-at").text("The moment: ");
    const slider = controls.append("input").attr("id", "dp-at").attr("type", "range").attr("min", t0).attr("max", t1).attr("step", 60000).property("value", at);
    const readMoment = controls.append("output").attr("class", "dp-when");
    const svg = sect.append("svg").attr("class", "dp-water").attr("role", "img").attr("aria-label", "The water column to scale");
    const table = sect.append("div").attr("class", "dp-table");
    const notes = h.append("div").attr("class", "dp-notes");

    // the width inside the card's padding
    const inner = () => { const cs = getComputedStyle(host); return (host.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight)) || 800; };
    function drawChart() {
      const W = inner(), H = 240, m = { l: 52, r: 112, t: 14, b: 26 };
      chart.attr("width", W).attr("height", H).selectAll("*").remove();
      const x = d3.scaleUtc().domain([t0, t1]).range([m.l, W - m.r]), y = d3.scaleLinear().domain([0, maxY]).range([m.t, H - m.b]);
      // the layer: isothermal to iso_ft, the gradient below it to grad_ft (as typed on her card)
      if (layer && +layer.iso_ft) chart.append("rect").attr("class", "dp-iso").attr("x", m.l).attr("width", W - m.r - m.l).attr("y", y(0)).attr("height", y(+layer.iso_ft) - y(0));
      if (layer && +layer.grad_ft) chart.append("rect").attr("class", "dp-grad").attr("x", m.l).attr("width", W - m.r - m.l).attr("y", y(+layer.iso_ft || 0)).attr("height", y(Math.min(+layer.grad_ft, maxY)) - y(+layer.iso_ft || 0));
      // the pistols' settings
      E.DC_SETTINGS["Type 2"].filter(f => f <= maxY).forEach(f => {
        chart.append("line").attr("class", "dp-setting").attr("x1", m.l).attr("x2", W - m.r).attr("y1", y(f)).attr("y2", y(f));
        chart.append("text").attr("class", "dp-setting-label").attr("x", W - m.r + 4).attr("y", y(f) + 4).text(`${f} ft${E.DC_SETTINGS["Type 95"].includes(f) ? "" : " (Type 2)"}`);
      });
      // her depth: a step from each log entry to the next; dashed where the log gives no depth (60 ft assumed)
      const pts = states.map(s => ({ ms: Math.max(t0, E.T(s.utc)), d: depthOf(s), assumed: assumedDepth(s), s }));
      d3.pairs([...pts, { ms: t1, d: pts[pts.length - 1].d }]).forEach(([a, b]) => {
        if (b.ms <= a.ms) return;
        chart.append("path").attr("class", "dp-depth" + (a.assumed ? " assumed" : "")).attr("stroke", colour)
          .attr("d", `M${x(a.ms)},${y(a.d)}H${x(b.ms)}V${y(b.d)}`);
      });
      pts.forEach(p => chart.append("circle").attr("class", "dp-log").attr("cx", x(p.ms)).attr("cy", y(p.s.passing ?? p.d)).attr("r", 3).attr("fill", colour)
        .on("mouseenter", ev => EV.showTip(ev, `<div class="v">${esc(p.s.state === "surfaced" ? "Surfaced" : p.s.depth || "Submerged")}</div><div class="k">${esc(p.s.local)}</div><div class="m">${esc(p.s.words)}</div>${p.assumed ? `<div class="i">no depth logged: drawn at ${SHALLOW} ft (assumed)</div>` : ""}`))
        .on("mousemove", EV.moveTip).on("mouseleave", EV.hideTip).on("click", () => setAt(p.ms)));
      // the counter-attack, as she logged it: a mark at each entry, with the count
      charges.forEach(c => {
        // "during the next 4½ hours", "within the next 45 minutes": her own span, shaded
        const sp = /next\s+(\d+)(½)?\s+(hours?|minutes?)/i.exec(c.e.words || "");
        if (sp) {
          const dur = ((+sp[1]) + (sp[2] ? 0.5 : 0)) * (/hour/i.test(sp[3]) ? 3600e3 : 60e3);
          chart.append("rect").attr("class", "dp-span").attr("x", x(c.ms)).attr("width", Math.max(1, x(Math.min(t1, c.ms + dur)) - x(c.ms))).attr("y", m.t).attr("height", H - m.b - m.t);
        }
        const g = chart.append("g").attr("class", "dp-charge").attr("transform", `translate(${x(c.ms)},${m.t})`);
        g.append("line").attr("y1", 0).attr("y2", H - m.b - m.t);
        const n = /\((\d+)\)/.exec(c.e.title) || /\b(\d+)\s+(?:more\s+)?(?:depth )?charges/i.exec(c.e.words || "");
        g.append("text").attr("x", 4).attr("y", 10).text(n ? `${n[1]} charges` : "charges");
        g.append("rect").attr("x", -6).attr("width", 12).attr("height", H - m.b - m.t).attr("fill", "transparent")
          .on("mouseenter", ev => EV.showTip(ev, `<div class="v">${esc(c.e.title)}</div><div class="k">${esc(c.e.local)}</div><div class="m">${esc(c.e.words)}</div><div class="i">${esc(B.name)}'s count and words; where the charges went off is not recorded</div>`))
          .on("mousemove", EV.moveTip).on("mouseleave", EV.hideTip).on("click", () => setAt(c.ms));
      });
      chart.append("g").attr("class", "axis").attr("transform", `translate(0,${H - m.b})`).call(d3.axisBottom(x).ticks(W < 560 ? 4 : 8).tickFormat(d => E.hhmm(+d) + "Z"));
      chart.append("g").attr("class", "axis").attr("transform", `translate(${m.l},0)`).call(d3.axisLeft(y).ticks(6).tickFormat(d => `${d} ft`));
      chart.append("line").attr("class", "dp-cursor").attr("x1", x(at)).attr("x2", x(at)).attr("y1", m.t).attr("y2", H - m.b);
      chart.on("click", ev => { const [px] = d3.pointer(ev); if (px >= m.l && px <= W - m.r) setAt(+x.invert(px)); });
    }

    // ---------- the section to scale at the moment
    function drawSection() {
      const W = inner(), span = 900, pad = 46;   // feet across
      const TOP = 64, k = (W - pad - 12) / span, Hft = maxY + 40, H = Math.round(Hft * k) + TOP + 14;
      svg.attr("width", W).attr("height", H).selectAll("*").remove();
      const X = ft => pad + (ft + span / 2) * k, Y = ft => TOP + ft * k;
      const st = stateAt(at), dep = depthOf(st), floor = floorAt(at);
      svg.append("rect").attr("class", "dp-sea").attr("x", X(-span / 2)).attr("y", Y(0)).attr("width", span * k).attr("height", Y(maxY) - Y(0));
      if (layer && +layer.iso_ft) {
        svg.append("rect").attr("class", "dp-iso").attr("x", X(-span / 2)).attr("y", Y(0)).attr("width", span * k).attr("height", (+layer.iso_ft) * k);
        svg.append("text").attr("class", "dp-note").attr("x", X(span / 2) - 6).attr("y", Y(+layer.iso_ft) - 6).attr("text-anchor", "end").text(`isothermal, ${layer.iso_deg}°, to ${layer.iso_ft} ft`);
      }
      if (layer && +layer.grad_ft) {
        svg.append("rect").attr("class", "dp-grad").attr("x", X(-span / 2)).attr("y", Y(+layer.iso_ft || 0)).attr("width", span * k).attr("height", (Math.min(+layer.grad_ft, maxY) - (+layer.iso_ft || 0)) * k);
        svg.append("text").attr("class", "dp-note").attr("x", X(span / 2) - 6).attr("y", Y(Math.min(+layer.grad_ft, maxY)) - 6).attr("text-anchor", "end").text(`the gradient: ${layer.grad_deg}° at ${layer.grad_ft} ft (her card)`);
      }
      svg.append("line").attr("class", "dp-surface").attr("x1", X(-span / 2)).attr("x2", X(span / 2)).attr("y1", Y(0)).attr("y2", Y(0));
      d3.range(0, maxY + 1, 100).forEach(f => svg.append("text").attr("class", "dp-depth-label").attr("x", pad - 6).attr("y", Y(f) + 4).attr("text-anchor", "end").text(`${f} ft`));
      // the seafloor: drawn if it is in the figure, said if it is below it
      if (floor != null && floor <= maxY) svg.append("rect").attr("class", "dp-floor").attr("x", X(-span / 2)).attr("y", Y(floor)).attr("width", span * k).attr("height", Y(maxY + 40) - Y(floor));
      else if (floor != null) svg.append("text").attr("class", "dp-floor-label").attr("x", X(-span / 2) + 6).attr("y", Y(maxY) + 14)
        .text(`the seafloor: about ${(Math.round(floor / 100) * 100).toLocaleString("en-US")} ft (${Math.round(floor * FT_M / 10) * 10} m), far below the figure`);
      // an escort on the surface, its place not recorded: set to one side, labelled so
      if (escort) {
        const s = SHIPS[escort.sil];
        svg.append("path").attr("class", "dp-escort").attr("d", s.d).attr("transform", `translate(${X(-span / 2 + 30)},${Y(0)}) scale(${k})`);
        svg.append("text").attr("class", "dp-note").attr("x", X(-span / 2 + 30)).attr("y", 12).text(`${escort.name}, to scale (where it was is not recorded)`);
      }
      // a charge at each setting, directly above her (illustrative), with the Bureau's distances round each
      const settings = E.DC_SETTINGS["Type 2"].filter(f => f <= maxY);
      // the 100 ft ring only round the setting nearest her, so the five don't drown each other
      const nearest = st && st.state === "submerged" ? settings.reduce((a, b) => Math.abs(b - dep) < Math.abs(a - dep) ? b : a) : null;
      settings.forEach(f => {
        const g = svg.append("g").attr("class", "dp-burst").attr("transform", `translate(${X(0)},${Y(f)})`);
        // her class's distance for the Type 2's charge (figure 15-2), then the Bureau's outer bands (15-12)
        [...BANDS].reverse().filter(([r]) => r > 25 && (r < 100 || f === nearest)).forEach(([r, cls]) => g.append("circle").attr("class", `dp-band ${cls}`).attr("r", r * k));
        g.append("circle").attr("class", "dp-band lethal").attr("r", HULL.ft * k);
        g.append("circle").attr("class", "dp-charge-dot").attr("r", 3);
        g.append("text").attr("class", "dp-setting-label").attr("x", -50 * k - 6).attr("y", 4).attr("text-anchor", "end").text(`${f} ft`);
      });
      // her silhouette, keel at the logged depth (the gauge's reference, assumed), bow to the right
      if (ship && st && st.state === "submerged") {
        const L = +ship.length;
        svg.append("path").attr("class", "dp-boat").attr("fill", colour).attr("d", ship.d)
          .attr("transform", `translate(${X(-L / 2)},${Y(dep)}) scale(${k})`);
        svg.append("text").attr("class", "dp-boat-label").attr("x", X(L / 2) + 6).attr("y", Y(dep) - 4).text(`${B.name}, ${assumedDepth(st) ? `${st.depth || "submerged"} (drawn at ${SHALLOW} ft, assumed)` : `${dep} ft`}`);
      } else if (ship) {
        svg.append("path").attr("class", "dp-boat").attr("fill", colour).attr("d", ship.d).attr("transform", `translate(${X(-+ship.length / 2)},${Y(0) + 15 * k}) scale(${k})`);
        svg.append("text").attr("class", "dp-boat-label").attr("x", X(+ship.length / 2) + 6).attr("y", Y(0) - 4).text(`${B.name}, surfaced`);
      }
      readMoment.text(`${new Date(at).toISOString().slice(11, 16)}Z · ${st ? (st.state === "surfaced" ? "surfaced" : `down, ${st.depth || "depth not logged"}`) : "before her log"} · the sea on her hull: ${dep ? `${Math.round(E.seaPressure(dep))} psi` : "0"}`);
      // what each setting meant at her depth, if a charge set for it had gone off straight above her
      const kg = CHARGE_LB * 0.45359;
      const rows = settings.map(f => {
        const dist = Math.abs(dep - f), band = !dep ? "—" : dist <= HULL.ft ? `within her class's ${HULL.curve === "ss285" ? "rupture" : "deformation"} distance (${Math.round(HULL.ft)} ft)`
          : (BANDS.find(([r]) => r > 25 && dist <= r) || [0, "", "beyond 100 ft: little damage expected"])[2];
        return `<tr><td class="mono">${f} ft</td><td>${dep ? `${dist} ft ${f < dep ? "above" : f > dep ? "below" : "level"}` : "—"}</td><td>${dep ? `${Math.round(E.peakPressure(kg, Math.max(dist, 3) * FT_M) * 145.04).toLocaleString("en-US")} psi` : "—"}</td><td>${esc(band)}</td></tr>`;
      }).join("");
      table.html(`<table class="sheet"><thead><tr><th>A charge set for</th><th>from her keel</th><th>peak pressure (computed)</th><th>the Bureau's distances</th></tr></thead><tbody>${rows}</tbody></table>`);
    }
    function setAt(ms) { at = Math.max(t0, Math.min(t1, ms)); slider.property("value", at); drawChart(); drawSection(); }
    slider.on("input", ev => setAt(+ev.target.value));

    const layerWords = layer ? `isothermal to ${layer.iso_ft} ft at ${layer.iso_deg}°, then a gradient to ${layer.grad_ft} ft at ${layer.grad_deg}° (her bathythermograph card, ${esc(layer.date)}${layer.time ? ` ${esc(layer.time)} GCT` : ""}${layer.cite?.href ? `, <a href="${esc(layer.cite.href)}" target="_blank" rel="noopener">${esc(layer.cite.label)}</a>` : ""})` : "no bathythermograph reading for these days";
    notes.html(`<p class="below">The record's: her depths and her words as she logged them (each mark opens the entry), the
      count of charges where she gave one, the layer (${layerWords}), and the Japanese pistols' settings, ${E.DC_SETTINGS["Type 2"].join(", ")} ft
      for the Type 2 and ${E.DC_SETTINGS["Type 95"].join(", ")} ft for the Type 95 (<a href="https://www.ibiblio.org/hyperwar/USN/rep/WDR/WDR58/WDR58-3.html">War Damage Report 58</a>, para 3-10);
      the deepest the Type 2 was normally set was 390 ft and the Type 95 could not go below 292 (3-12). The Japanese
      officers questioned after the war said the same: "Maximum depth setting of charges usually carried was 120 meters
      and a proportionate number of charges with this setting was included in each pattern" (<a href="https://www.fischer-tropsch.org/primary_documents/gvt_reports/USNAVY/USNTMJ%20Reports/USNTMJ-200I-0244-0309%20Report%20S-24.pdf#page=15">NavTechJap S-24</a>, p. 12).</p>
      <p class="below"><i>Ours, and assumed:</i> her depth held from one log entry to the next; periscope or radar depth, or
      "submerged" with no depth, drawn at ${SHALLOW} ft (dashed); her keel at the logged depth; a charge at each setting
      straight above her, since where any went off is not recorded. The rings round each: the inner, shaded, ${Math.round(HULL.ft)} ft,
      the Bureau's figure 15-2 read at the Type 2's 357 lb for ${esc(B.name)}'s hull (${esc(B.hull || "")}: ${esc(HULL.what)};
      read off the plate, about ± 2 ft, and drawn there "for shallow submergence condition only": the distance grows with
      depth, by how much is not given); the outer two, 50 and 100 ft, the Bureau's bands of serious and of moderate to
      minor damage (<a href="https://www.ibiblio.org/hyperwar/USN/rep/WDR/WDR58/WDR58-15.html">15-12</a>). The peak pressures for the Type 2's 357 lb charge taken as TNT, from Cole's
      similitude, the distance to her keel, not to her hull. The seafloor is NOAA ETOPO1's under her track, placed as
      the track is. <a href="depthcharge.html">Depth charges</a> explains the rest.</p>`);
    drawChart(); drawSection();
    let lastW = host.clientWidth;
    new ResizeObserver(() => { if (host.clientWidth !== lastW) { lastW = host.clientWidth; drawChart(); drawSection(); } }).observe(host);
  }
  return { applies: D => boats(D).length > 0 && !!D.window, panel: { id: "water-column", heading: "The water column", intro: "Her depth through the hours, and the water she was in, to scale: the Japanese depth charges' settings, the layer, the seafloor.", mount } };
})();
