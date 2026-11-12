// depthcharge.html: the explainer's three figures. The settings are War Damage Report 58's (Engage.DC_SETTINGS), the
// charges' weights its paragraph 3-9, the damage distances its 15-12; the peak pressure is Cole's similitude and the sea's
// pressure rho g h (Engage.peakPressure, Engage.seaPressure); the silhouette is the kit's (silhouettes.js). Everything
// computed says so on the page; nothing here is a record of any one attack.
(async () => {
  const E = Engage;
  await SILHOUETTES;
  const BALAO = window.SHIPS && SHIPS.balao, KAIBOKAN = window.SHIPS && SHIPS.kaibokan2;
  const LB_KG = 0.45359, FT_M = 0.3048, SOUND_FTS = 4900;   // sea water, about 1,500 m/s
  const CHARGES = { "Type 95": 220, "Type 2": 357 };   // lb: the Mod. 0 and the Mod. 1 (WDR 58, 3-9)
  const BANDS = [[25, "lethal", "presumed lethal"], [50, "serious", "rupture or marked deformation possible"], [100, "moderate", "moderate to minor damage"]];
  const psi = (lb, ft) => E.peakPressure(lb * LB_KG, Math.max(ft, 3) * FT_M) * 145.038;
  const fmt = n => Math.round(n).toLocaleString("en-US");
  const inner = el => { const cs = getComputedStyle(el); return el.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight); };
  const params = new URLSearchParams(location.search);

  // ---------- 1. the settings against her depth
  const ladderDepth = document.getElementById("ladder-depth"), ladderType = document.getElementById("ladder-type"), ladderHull = document.getElementById("ladder-hull");
  if (params.get("depth")) ladderDepth.value = params.get("depth");
  function ladder() {
    const host = document.getElementById("ladder-fig"), W = inner(host), dep = +ladderDepth.value, type = ladderType.value;
    const hull = E.hullRange(CHARGES[type], ladderHull.value);
    document.getElementById("ladder-depth-out").textContent = dep ? `${dep} ft · the sea on her hull ${fmt(E.seaPressure(dep))} psi` : "surfaced";
    const span = 700, maxY = 640, TOP = 84, pad = 46, k = (W - pad - 8) / span, H = TOP + maxY * k + 10;
    const X = f => pad + (f + span / 2) * k, Y = f => TOP + f * k;
    const svg = d3.select("#ladder").attr("width", W).attr("height", H);
    svg.selectAll("*").remove();
    svg.append("rect").attr("class", "sea").attr("x", X(-span / 2)).attr("y", Y(0)).attr("width", span * k).attr("height", maxY * k);
    svg.append("line").attr("class", "surface").attr("x1", X(-span / 2)).attr("x2", X(span / 2)).attr("y1", Y(0)).attr("y2", Y(0));
    d3.range(0, maxY + 1, 100).forEach(f => svg.append("text").attr("class", "note").attr("x", pad - 6).attr("y", Y(f) + 4).attr("text-anchor", "end").text(`${f} ft`));
    if (KAIBOKAN) {
      svg.append("path").attr("class", "dc").attr("d", KAIBOKAN.d).attr("transform", `translate(${X(-span / 2 + 20)},${Y(0)}) scale(${k})`);
      svg.append("text").attr("class", "note").attr("x", X(-span / 2 + 20) + 320 * k).attr("y", Y(0) - 6).text(`${KAIBOKAN.name}, to scale`);
    }
    const settings = E.DC_SETTINGS[type];
    const nearest = dep ? settings.reduce((a, b) => Math.abs(b - dep) < Math.abs(a - dep) ? b : a) : null;
    E.DC_SETTINGS["Type 2"].forEach(f => {
      const on = settings.includes(f);
      svg.append("line").attr("class", "setting" + (on ? "" : " off")).attr("x1", X(-span / 2)).attr("x2", X(span / 2)).attr("y1", Y(f)).attr("y2", Y(f));
      if (!on) return;
      const g = svg.append("g").attr("transform", `translate(${X(0)},${Y(f)})`);
      [...BANDS].reverse().filter(([r]) => r > 25 && (r < 100 || f === nearest)).forEach(([r, cls]) => g.append("circle").attr("class", `band ${cls}`).attr("r", r * k));
      g.append("circle").attr("class", "band lethal").attr("r", hull.ft * k);
      g.append("circle").attr("class", "dc").attr("r", 3);
      g.append("text").attr("class", "lbl").attr("x", -50 * k - 6).attr("y", 4).attr("text-anchor", "end").text(`${f} ft`);
    });
    if (BALAO) {
      const L = +BALAO.length, y = dep ? Y(dep) : Y(0) + 15 * k;
      svg.append("path").attr("class", "boat").attr("d", BALAO.d).attr("transform", `translate(${X(-L / 2)},${y}) scale(${k})`);
      svg.append("text").attr("class", "boat-lbl").attr("x", X(L / 2) + 6).attr("y", y - 4).text(`BALAO class, ${dep ? `keel at ${dep} ft` : "surfaced"}`);
    }
    const kept = settings.filter(f => f <= dep + 100);
    document.getElementById("ladder-table").innerHTML = dep ? `<table class="dc-table"><thead><tr><th>Set for</th><th>From her keel</th><th>Peak pressure, the ${type} (${CHARGES[type]} lb as TNT; computed)</th><th>The Bureau's band</th></tr></thead><tbody>${settings.map(f => {
      const d = Math.abs(dep - f), band = d <= hull.ft ? `within the hull's ${hull.curve === "ss285" ? "rupture" : "deformation"} distance (${Math.round(hull.ft)} ft)` : (BANDS.find(([r]) => r > 25 && d <= r) || [0, "", "beyond 100 ft"])[2];
      return `<tr><td>${f} ft</td><td>${d} ft ${f < dep ? "above" : f > dep ? "below" : ""}</td><td>${fmt(psi(CHARGES[type], d))} psi</td><td>${band}</td></tr>`;
    }).join("")}</tbody></table>${kept.length ? "" : `<p class="below">No ${type} setting reaches within 100 ft of her.</p>`}` : "";
  }
  [ladderDepth, ladderType, ladderHull].forEach(el => el.addEventListener("input", ladder));

  // ---------- the patterns, as report S-24 draws them (p. 13): figure 5 from above, as drawn (no distances given; the
  // positions are the figure's, in its own units), and figure 4 in depth, the charges 50 m apart as it marks
  const FIG5 = [   // [x, row, setting m], read off the figure: three rows across the escort's track
    [405, 0, 60], [470, 0, 90], [540, 0, 30], [605, 0, 60], [680, 0, 120], [750, 0, 120],
    [360, 1, 90], [425, 1, 120], [495, 1, 60], [560, 1, 90], [630, 1, 30], [690, 1, 90], [760, 1, 60],
    [405, 2, 60], [470, 2, 90], [540, 2, 30], [605, 2, 60], [680, 2, 120], [750, 2, 120]];
  const FIG4 = { 30: [0, 1, 2, 3], 60: [0.5, 1.5, 2.5], 90: [0, 1, 2, 3], 120: [0.5, 1.5, 2.5] };   // in 50 m steps
  const M_FT = 1 / FT_M, patDepth = document.getElementById("pat-depth");
  function patterns() {
    const host = document.getElementById("pattern-fig"), W = inner(host), dep = +patDepth.value;
    document.getElementById("pat-depth-out").textContent = `${dep} ft`;
    const svg = d3.select("#pattern").attr("width", W);
    svg.selectAll("*").remove();
    // above: figure 5's plan, as drawn
    const px = d3.scaleLinear().domain([300, 800]).range([60, Math.min(W - 20, 700)]), rowY = r => 34 + r * 28;
    svg.append("text").attr("class", "note").attr("x", 0).attr("y", 14).text("A kaibokan's pattern from above (S-24, figure 5), as drawn: settings in meters");
    if (KAIBOKAN) {
      const s = 70 / +KAIBOKAN.length;
      svg.append("path").attr("class", "dc").attr("d", KAIBOKAN.d).attr("transform", `translate(${px(300) - 70},${rowY(1) + 4}) scale(${s})`).attr("opacity", .6);
    }
    FIG5.forEach(([x, r, m]) => {
      svg.append("circle").attr("class", "dc").attr("cx", px(x)).attr("cy", rowY(r)).attr("r", 3.5);
      svg.append("text").attr("class", "lbl").attr("x", px(x) + 6).attr("y", rowY(r) + 4).text(m);
    });
    // below: figure 4 in depth, to scale, beside her
    const top = rowY(2) + 46, maxY = 620, spanFt = 4 * 50 * M_FT + 400, k = Math.min((W - 60) / spanFt, 420 / maxY);
    const X = ft => 50 + ft * k, Y = ft => top + ft * k;
    svg.attr("height", Y(maxY) + 12);
    svg.append("text").attr("class", "note").attr("x", 0).attr("y", top - 18).text("A destroyer's pattern in depth (S-24, figure 4), to scale: 50 m apart, settings 30-120 m");
    svg.append("rect").attr("class", "sea").attr("x", X(0)).attr("y", Y(0)).attr("width", spanFt * k).attr("height", maxY * k);
    svg.append("line").attr("class", "surface").attr("x1", X(0)).attr("x2", X(spanFt)).attr("y1", Y(0)).attr("y2", Y(0));
    d3.range(0, maxY + 1, 100).forEach(f => svg.append("text").attr("class", "note").attr("x", 44).attr("y", Y(f) + 4).attr("text-anchor", "end").text(`${f} ft`));
    const x0 = 120;
    Object.entries(FIG4).forEach(([m, xs]) => {
      const ft = +m * M_FT;
      svg.append("text").attr("class", "lbl").attr("x", X(x0 + 3.5 * 50 * M_FT) + 4).attr("y", Y(ft) + 4).text(`set for ${m} m (${Math.round(ft)} ft)`);
      xs.forEach(i => {
        const cx = X(x0 + i * 50 * M_FT), cy = Y(ft);
        svg.append("circle").attr("class", "band lethal").attr("cx", cx).attr("cy", cy).attr("r", E.hullRange(357, "SS-285").ft * k);
        svg.append("circle").attr("class", "dc").attr("cx", cx).attr("cy", cy).attr("r", 2.5);
      });
    });
    if (BALAO) {
      const L = +BALAO.length;
      svg.append("path").attr("class", "boat").attr("d", BALAO.d).attr("transform", `translate(${X(x0 + 1.5 * 50 * M_FT - L / 2)},${Y(dep)}) scale(${k})`);
      const deepest = 120 * M_FT;
      svg.append("text").attr("class", "boat-lbl").attr("x", X(x0 + 1.5 * 50 * M_FT + L / 2) + 6).attr("y", Y(dep) - 3)
        .text(dep > deepest + 25 ? `keel at ${dep} ft: ${Math.round(dep - deepest)} ft below the deepest setting` : `keel at ${dep} ft: inside the pattern's depths`);
    }
  }
  patDepth.addEventListener("input", patterns);

  // ---------- the hull: figure 15-2's two curves, as read
  function hullFig() {
    const host = document.getElementById("hull-fig"), W = inner(host), H = 280, m = { l: 56, r: 150, t: 12, b: 38 };
    const svg = d3.select("#hull").attr("width", W).attr("height", H);
    svg.selectAll("*").remove();
    const x = d3.scaleLinear().domain([0, 600]).range([m.l, W - m.r]), y = d3.scaleLinear().domain([0, 80]).range([H - m.b, m.t]);
    Object.entries(E.HULL_CURVES).forEach(([key, c]) => {
      svg.append("path").attr("class", "curve").attr("stroke", key === "ss285" ? "var(--series-track)" : "var(--ink-2)").attr("stroke-dasharray", key === "ss285" ? null : "5 3")
        .attr("d", d3.line().curve(d3.curveMonotoneX).x(p => x(p[0])).y(p => y(p[1]))(c.pts));
      const last = c.pts[c.pts.length - 1];
      svg.append("text").attr("class", "note").attr("x", x(last[0]) + 6).attr("y", y(last[1]) + 4).text(key === "ss285" ? "SS-285 class: rupture" : "SS-212 class: deformation");
    });
    Object.entries(CHARGES).forEach(([name, lb]) => {
      svg.append("line").attr("class", "setting").attr("x1", x(lb)).attr("x2", x(lb)).attr("y1", y(0)).attr("y2", y(80));
      svg.append("text").attr("class", "note").attr("x", x(lb) + 4).attr("y", m.t + 10).text(`${name}, ${lb} lb`);
    });
    svg.append("g").attr("class", "axis").attr("transform", `translate(0,${H - m.b})`).call(d3.axisBottom(x).ticks(6).tickFormat(d => `${d} lb`));
    svg.append("g").attr("class", "axis").attr("transform", `translate(${m.l},0)`).call(d3.axisLeft(y).ticks(4).tickFormat(d => `${d} ft`));
    svg.append("text").attr("class", "note").attr("x", x(300)).attr("y", H - 4).attr("text-anchor", "middle").text("the charge, lb TNT; up, the distance from the pressure hull");
  }

  // ---------- 2. the wave, the surface and the seafloor
  const wSet = document.getElementById("w-set"), wBoat = document.getElementById("w-boat"), wFloor = document.getElementById("w-floor"), wX = document.getElementById("w-x");
  const SETS = E.DC_SETTINGS["Type 2"];
  let tWave = null, raf = 0;
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  function wave() {
    const host = document.getElementById("wave-fig"), W = inner(host);
    const setting = SETS[+wSet.value], dep = +wBoat.value, floor = +wFloor.value, dx = +wX.value;
    // set deeper than the sea: it lies on the bottom and fires "once water seeps in" (WDR 58, 3-11)
    const onBottom = setting >= floor, set = onBottom ? floor - 2 : setting;
    if (dep > floor - 20) { wBoat.value = floor - 20; return wave(); }
    document.getElementById("w-set-out").textContent = onBottom ? `${setting} ft: on the bottom at ${floor} ft` : `${setting} ft`;
    document.getElementById("w-boat-out").textContent = `${dep} ft`;
    document.getElementById("w-floor-out").textContent = `${floor} ft (${Math.round(floor * FT_M)} m)`;
    document.getElementById("w-x-out").textContent = `${dx} ft`;
    // one foot across = one foot down; the height held to about 520 px, the width filled
    const TOP = 14, pad = 46, maxY = Math.max(floor + 40, 300), k = Math.min((W - pad - 8) / 900, 520 / maxY), span = (W - pad - 8) / k, H = TOP + maxY * k + 6;
    const X = f => pad + (f + span / 2 - 150) * k, Y = f => TOP + f * k;
    const svg = d3.select("#wave").attr("width", W).attr("height", H);
    svg.selectAll("*").remove();
    svg.append("defs").append("clipPath").attr("id", "w-clip").append("rect").attr("x", X(-span / 2 + 150)).attr("y", Y(0)).attr("width", span * k).attr("height", floor * k);
    svg.append("rect").attr("class", "sea").attr("x", X(-span / 2 + 150)).attr("y", Y(0)).attr("width", span * k).attr("height", floor * k);
    svg.append("rect").attr("class", "floor").attr("x", X(-span / 2 + 150)).attr("y", Y(floor)).attr("width", span * k).attr("height", Math.max(0, H - Y(floor)));
    svg.append("line").attr("class", "surface").attr("x1", X(-span / 2 + 150)).attr("x2", X(span / 2 + 150)).attr("y1", Y(0)).attr("y2", Y(0));
    d3.range(0, maxY + 1, 100).forEach(f => svg.append("text").attr("class", "note").attr("x", pad - 6).attr("y", Y(f) + 4).attr("text-anchor", "end").text(`${f} ft`));
    if (BALAO) {
      const L = +BALAO.length;
      svg.append("path").attr("class", "boat").attr("d", BALAO.d).attr("transform", `translate(${X(dx - L / 2)},${Y(dep)}) scale(${k})`);
    }
    svg.append("circle").attr("class", "dc").attr("cx", X(0)).attr("cy", Y(set)).attr("r", 3.5);
    // the paths to her keel's middle: direct, by the surface (the image above it) and by the seafloor (the image below it)
    const direct = Math.hypot(dx, dep - set), surf = Math.hypot(dx, dep + set), bot = Math.hypot(dx, (2 * floor - set) - dep);
    const ms = d => d / SOUND_FTS * 1000;
    const r = tWave == null ? null : Math.max(0, tWave) * SOUND_FTS / 1000;   // feet the wave has gone
    const g = svg.append("g").attr("clip-path", "url(#w-clip)");
    if (r != null) {
      g.append("circle").attr("class", "wave").attr("cx", X(0)).attr("cy", Y(set)).attr("r", r * k);
      if (r > set) g.append("circle").attr("class", "wave surf").attr("cx", X(0)).attr("cy", Y(-set)).attr("r", r * k);
      if (r > floor - set) g.append("circle").attr("class", "wave bot").attr("cx", X(0)).attr("cy", Y(2 * floor - set)).attr("r", r * k);
    }
    const P = psi(357, direct);
    document.getElementById("w-read").innerHTML = [
      [`${(ms(direct)).toFixed(1)} ms`, `the direct wave reaches her keel, ${Math.round(direct)} ft`],
      [`${fmt(P)} psi`, "its peak there (357 lb as TNT; computed)"],
      [`+${(ms(surf) - ms(direct)).toFixed(1)} ms`, "then the surface's tension wave"],
      onBottom ? [`at once`, "the seafloor's: the charge lies on it (up to double, on rock)"] : [`+${(ms(bot) - ms(direct)).toFixed(1)} ms`, `then the seafloor's (up to the same again, on rock)`],
      [`${fmt(E.seaPressure(dep))} psi`, "the sea already on her hull"],
    ].map(([b, i]) => `<div><b>${b}</b><i>${i}</i></div>`).join("");
  }
  [wSet, wBoat, wFloor, wX].forEach(el => el.addEventListener("input", () => { tWave = null; cancelAnimationFrame(raf); wave(); }));
  document.getElementById("w-play").addEventListener("click", () => {
    cancelAnimationFrame(raf);
    const floor = +wFloor.value, end = (2 * floor + 400) / SOUND_FTS * 1000, slow = 400, start = performance.now();
    if (reduced) { tWave = end * 0.6; wave(); return; }
    const step = now => { tWave = (now - start) / slow; if (tWave > end) { tWave = null; wave(); return; } wave(); raf = requestAnimationFrame(step); };
    raf = requestAnimationFrame(step);
  });

  // ---------- 3. the curve: peak pressure against distance
  function curve() {
    const host = document.getElementById("curve-fig"), W = inner(host), H = 300, m = { l: 62, r: 120, t: 12, b: 36 };
    const svg = d3.select("#curve").attr("width", W).attr("height", H);
    svg.selectAll("*").remove();
    const x = d3.scaleLog().domain([10, 600]).range([m.l, W - m.r]), y = d3.scaleLog().domain([50, 20000]).range([H - m.b, m.t]);
    [[0, 25, .14], [25, 50, .08], [50, 100, .04]].forEach(([a, b, o]) => svg.append("rect").attr("class", "zone").attr("fill-opacity", o)
      .attr("x", x(Math.max(a, 10))).attr("width", x(b) - x(Math.max(a, 10))).attr("y", m.t).attr("height", H - m.b - m.t));
    Object.entries(CHARGES).forEach(([name, lb], i) => {
      const pts = d3.range(10, 601, 2).map(d => [d, psi(lb, d)]);
      svg.append("path").attr("class", "curve").attr("stroke", i ? "var(--series-track)" : "var(--ink-2)").attr("stroke-dasharray", i ? null : "5 3")
        .attr("d", d3.line().x(p => x(p[0])).y(p => y(p[1]))(pts));
      svg.append("text").attr("class", "note").attr("x", W - m.r + 6).attr("y", y(psi(lb, 600)) + 4).text(`${name}, ${lb} lb`);
    });
    [200, 450].forEach(f => {
      const p = E.seaPressure(f);
      svg.append("line").attr("class", "setting").attr("x1", m.l).attr("x2", W - m.r).attr("y1", y(p)).attr("y2", y(p));
      svg.append("text").attr("class", "note").attr("x", m.l + 6).attr("y", y(p) - 5).text(`the sea's own pressure at ${f} ft`);
    });
    svg.append("g").attr("class", "axis").attr("transform", `translate(0,${H - m.b})`).call(d3.axisBottom(x).tickValues([10, 25, 50, 100, 200, 400]).tickFormat(d => `${d} ft`));
    svg.append("g").attr("class", "axis").attr("transform", `translate(${m.l},0)`).call(d3.axisLeft(y).tickValues([100, 300, 1000, 3000, 10000]).tickFormat(d => `${fmt(d)} psi`));
    svg.append("text").attr("class", "note").attr("x", x(10) + 4).attr("y", m.t + 12).text("the Bureau's bands");
  }

  const all = () => { ladder(); patterns(); hullFig(); wave(); curve(); };
  all();
  let lastW = 0;
  new ResizeObserver(() => { const w = document.querySelector(".doc").clientWidth; if (w !== lastW) { lastW = w; all(); } }).observe(document.querySelector(".doc"));
})();
