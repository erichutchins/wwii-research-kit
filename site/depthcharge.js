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
  const ladderDepth = document.getElementById("ladder-depth"), ladderType = document.getElementById("ladder-type");
  if (params.get("depth")) ladderDepth.value = params.get("depth");
  function ladder() {
    const host = document.getElementById("ladder-fig"), W = inner(host), dep = +ladderDepth.value, type = ladderType.value;
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
      [...BANDS].reverse().filter(([r]) => r < 100 || f === nearest).forEach(([r, cls]) => g.append("circle").attr("class", `band ${cls}`).attr("r", r * k));
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
      const d = Math.abs(dep - f), band = (BANDS.find(([r]) => d <= r) || [0, "", "beyond 100 ft"])[2];
      return `<tr><td>${f} ft</td><td>${d} ft ${f < dep ? "above" : f > dep ? "below" : ""}</td><td>${fmt(psi(CHARGES[type], d))} psi</td><td>${band}</td></tr>`;
    }).join("")}</tbody></table>${kept.length ? "" : `<p class="below">No ${type} setting reaches within 100 ft of her.</p>`}` : "";
  }
  [ladderDepth, ladderType].forEach(el => el.addEventListener("input", ladder));

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

  const all = () => { ladder(); wave(); curve(); };
  all();
  let lastW = 0;
  new ResizeObserver(() => { const w = document.querySelector(".doc").clientWidth; if (w !== lastW) { lastW = w; all(); } }).observe(document.querySelector(".doc"));
})();
