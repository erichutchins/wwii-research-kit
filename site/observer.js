// The observer view on engagement.html: one attack as the boat saw it, from her attack data sheet (the engagement's
// `sheets`, a patrol's attacks.csv and attack_sheets.yml, built by tools/build_engagement.py). The plot from above,
// the view through the periscope (or from the bridge, for a surface attack) with the target at its true angular size
// and angle on the bow, the sky as computed, and the firing solution, all on one clock in seconds from the first
// torpedo. Beside the periscope, the plot: the torpedo tracks against the moving ships. The Torpedo Data Computer's faces
// for the same attack are on their own page (tdc.html, tdc-page.js), which reads the attacks and their targets from
// `attacks` and `targetsOf` here. The computation is engage.js's (attackSheet, attackAt, sky); every assumption is listed
// under the view.
// It replaces the family repository's periscope prototype (SEAHORSE's Attack 3), retired 1 Nov 2026.
const Observer = (() => {
  const E = Engage, esc = s => EV.esc(s);
  const rad = d => d * Math.PI / 180, deg = r => r * 180 / Math.PI;
  const norm = a => ((a % 360) + 540) % 360 - 180;   // -180..180
  const pad3 = a => String(Math.round(((a % 360) + 360) % 360)).padStart(3, "0");
  // fields of view, degrees across: secondary sources, to check against the Submarine Periscope Manual (NAVPERS 16165)
  const FIELDS = { periscope: [["low", "Low power", 32], ["high", "High power", 8]], bridge: [["binoculars", "Binoculars, 7×", 7]] };
  // a target's assumed size by kind (feet: length, beam, the outline's height above the waterline comes from its shape)
  const SIZE = { cargo: [400, 55], tanker: [450, 60], destroyer: [350, 34], escort: [250, 30], gunboat: [200, 30], submarine: [300, 27], carrier: [750, 90] };
  // the target's kind: the first kind of ship the sheet's description names ("1 large AK ... escorted by two DD's")
  const KINDS = [["carrier", /\bCVL?\b|carrier/i], ["tanker", /\bAO\b|tanker/i], ["destroyer", /\bDD'?s?\b|destroyer/i], ["escort", /\bDE\b|\bPC\b|escort|frigate|kaibokan|minesweeper/i],
                 ["gunboat", /gunboat|\bPG\b/i], ["cargo", /\bAK\b|\bAP\b|freighter|transport|maru|cargo/i]];
  const kindOf = words => {
    const hits = KINDS.map(([k, re]) => [k, (words || "").search(re)]).filter(([, i]) => i >= 0).sort((a, b) => a[1] - b[1]);
    return hits.length ? hits[0][0] : "cargo";
  };
  const LIGHT = { was: "As it was", day: "Broad daylight", night: "Night vision" };

  // an engagement's attacks whose sheets are transcribed, in time order: each with its sheet, its log entry, its time,
  // the first torpedo to the second where the sheet types it (t0) and the zone its local time is written in
  function attacks(D) {
    const list = [];
    for (const [actor, byRef] of Object.entries(D.sheets || {}))
      for (const [ref, sh] of Object.entries(byRef)) {
        const ev = D.events.find(e => e.kind === "attack" && e.actor === actor && e.title === ref);
        if (!ev) continue;
        const ms = E.T(ev.utc), first = sh.torpedoes[0].time.match(/-(\d\d)$/);
        list.push({ actor, ref, sh, ev, ms, t0: ms + (first ? +first[1] * 1000 : 0), zone: (ev.local.match(/ ([A-Z]{1,2})$/) || [])[1] || "" });
      }
    return list.sort((a, b) => a.ms - b.ms);
  }

  // an attack's targets, each as drawn: its kind, its class's outline where the engagement names one, its assumed size;
  // `kind` the sheet's target's kind, `unsure` when several targets' kinds can't be told apart
  function targetsOf(D, sh) {
    const words = sh.words[0] || {};
    let unsure = false;
    // the target's kind: what the sheet claims it hit or sank names the boat's own target ("One fleet type destroyer"),
    // where its description may name the whole force; failing those, the description and the target line
    const claimed = [words.sunk, words.damaged].filter(w => w && !/^none\.?$/i.test(w.trim())).join(" ");
    const kind0 = claimed && KINDS.some(([, re]) => re.test(claimed)) ? kindOf(claimed) : kindOf([words.description, words.target_line].join(" "));
    // her class's own outline, where the engagement names a ship of that kind on the other side with one (one only, so
    // the choice is not ours to make among several); otherwise the generic outline for the kind, at its assumed size
    const profile = kind => {
      const own = (D.participants || []).filter(p => p.of !== "us" && p.kind === kind && window.SHIPS && SHIPS[p.sil]);
      const ship = own.length === 1 ? { who: own[0], sil: SHIPS[own[0].sil] } : null;
      return { kind, ship, size: ship ? [+ship.sil.length, SIZE[kind][1]] : SIZE[kind] };
    };
    // each target its own: a sheet aimed at two (BANG's "Target: DD ... Range: 1800 yds. / AK ... / AO ... Range: 2800
    // yds.") names each in its target line; the target whose range a segment types takes that segment's kind
    const segs = String(words.target_line || "").split(/\s\/\s/);
    // or a description that numbers them ("(1) Medium freighter ... (2) ...", "1 - Large AO ... 2 - Lare AK"): item n is
    // the target the target line numbers n (its part holding that target's range), else the n-th target fired at
    const items = [...String(words.description || "").matchAll(/(?:^|\s)(?:\((\d)\)|(\d)\s+-)\s*(.+?)(?=\s(?:\(\d\)|\d\s+-)|$)/g)]
      .map(m => ({ n: +(m[1] || m[2]), text: m[3] })).filter(x => KINDS.some(([, re]) => re.test(x.text)));
    const parts = String(words.target_line || "").split(/\((\d)\)/);   // ["...", "1", "28' ... 2600.", "2", "25' ... 3000."]
    const numbered = T => { for (let i = 1; i < parts.length - 1; i += 2) if (T.range != null && (parts[i + 1].replace(/,/g, "").match(/\d+/g) || []).map(Number).includes(+T.range)) return +parts[i]; return null; };
    const kindFor = (T, gi, all) => {
      const seg = segs.find(g => { const m = g.match(/range:?\s*([\d,]+)/i); return m && T.range != null && +m[1].replace(/,/g, "") === +T.range; });
      if (seg && KINDS.some(([, re]) => re.test(seg))) return kindOf(seg);
      if (all.length > 1 && items.length === all.length) {
        const it = items.find(x => x.n === (numbered(T) ?? gi + 1));
        if (it) return kindOf(it.text);
      }
      // several targets, and a claim naming several kinds ("One DD and two AK's") with nothing to say which was which:
      // the generic merchant, not the first kind named for all of them
      if (all.length > 1 && new Set(KINDS.filter(([, re]) => re.test(claimed)).map(([k]) => k)).size > 1) { unsure = true; return "cargo"; }
      return kind0;
    };
    const tg = E.attackSheet(sh.torpedoes, {}).targets.map((T, gi, all) => profile(kindFor(T, gi, all)));
    return { kind: kind0, unsure, tg };
  }

  function mount({ D, colour, nameOf, setPageTime }) {
    const card = document.getElementById("observer-card");
    const list = attacks(D);
    card.hidden = !list.length;
    if (!list.length) return { pick() {} };

    let cur = null, A = null, s = 0, power = "low", light = "was", train = 0, timer = null, aimAt = 0;
    const pick = document.getElementById("obs-pick");
    pick.innerHTML = list.map((x, i) => `<button type="button" data-i="${i}" style="--bar:${colour(x.actor)}">${esc(nameOf(x.actor))} · ${esc(x.ref)} <span>${esc(x.ev.local.slice(11))}</span></button>`).join("");
    pick.querySelectorAll("button").forEach(b => b.addEventListener("click", () => choose(+b.dataset.i, true)));
    const slider = document.getElementById("obs-t");
    slider.addEventListener("input", () => { stop(); update(+slider.value); });
    const playBtn = document.getElementById("obs-play");
    playBtn.addEventListener("click", () => timer ? stop() : play());
    document.getElementById("obs-light").innerHTML = Object.entries(LIGHT).map(([k, v]) => `<option value="${k}">${v}</option>`).join("");
    document.getElementById("obs-light").addEventListener("change", e => { light = e.target.value; update(s); });
    // ---------- choosing an attack
    function choose(i, sync) {
      stop();
      cur = list[i];
      pick.querySelectorAll("button").forEach((b, j) => b.setAttribute("aria-pressed", i === j));
      Object.assign(cur, targetsOf(D, cur.sh));
      A = E.attackSheet(cur.sh.torpedoes, { sizes: cur.tg.map(t => t.size) });
      const view = A.surface ? "bridge" : "periscope";
      if (!FIELDS[view].some(f => f[0] === power)) power = FIELDS[view][0][0];
      document.getElementById("obs-power").innerHTML = FIELDS[view].map(([k, label]) => `<button type="button" data-p="${k}" aria-pressed="${k === power}">${label}</button>`).join("");
      document.querySelectorAll("#obs-power button").forEach(b => b.addEventListener("click", () => {
        power = b.dataset.p; document.querySelectorAll("#obs-power button").forEach(x => x.setAttribute("aria-pressed", x === b)); update(s); }));
      document.getElementById("obs-scope-h").textContent = A.surface ? "From the bridge" : "Through the periscope";
      slider.min = A.start; slider.max = Math.ceil(A.end); slider.step = 1;
      train = 0; aimAt = 0;
      // a sheet that can't place the target (TINOSA's summary table: no own or target course) shows its rows only
      const drawable = !A.problems.length;
      card.querySelectorAll(".obs-ctrl, .obs-read, .obs-stage").forEach(el => { el.hidden = !drawable; });
      drawTorpTable(); drawWords();
      // the same attack's Torpedo Data Computer, on its own page
      const tdcLink = document.getElementById("obs-tdc");
      tdcLink.href = `tdc.html?e=${encodeURIComponent(D.id)}&boat=${encodeURIComponent(cur.actor)}&attack=${encodeURIComponent(cur.ref)}`;
      tdcLink.hidden = !drawable;
      if (drawable) { layoutPlot(); update(-60); }
      if (sync && setPageTime) setPageTime(cur.ms);
    }

    // ---------- the plot, from above: yards, north up, the boat at the origin when she fired
    const plot = d3.select("#obs-plot");
    let k = 1, sx = x => x, sy = y => y;
    const P = p => [sx(p[0]), sy(p[1])];
    const gGrid = plot.append("g"), gTrk = plot.append("g"), gLos = plot.append("g"), gTorp = plot.append("g"), gShip = plot.append("g"), gLbl = plot.append("g");
    function layoutPlot() {
      const W = plot.node().clientWidth, H = Math.round(Math.min(640, Math.max(340, W)));
      plot.attr("height", H);
      const pts = [[0, 0]];
      for (let t = A.start; t <= A.end; t += 5) {
        const q = E.attackAt(A, t);
        pts.push(q.own.p, ...q.targets.filter(Boolean).map(x => x.p), ...q.torps.map(x => x.p));
      }
      const xs = pts.map(p => p[0]), ys = pts.map(p => p[1]);
      const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys), m = 34;
      k = Math.min((W - 2 * m) / Math.max(200, x1 - x0), (H - 2 * m) / Math.max(200, y1 - y0));
      const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
      sx = x => W / 2 + (x - cx) * k; sy = y => H / 2 - (y - cy) * k;
      gGrid.selectAll("*").remove(); gTrk.selectAll("*").remove(); gLbl.selectAll("*").remove();
      const span = Math.max(x1 - x0, y1 - y0), step = span > 6000 ? 1000 : span > 2500 ? 500 : 200;
      for (let x = Math.floor((cx - W / 2 / k) / step) * step; sx(x) < W; x += step) gGrid.append("line").attr("class", "obs-grid").attr("x1", sx(x)).attr("x2", sx(x)).attr("y1", 0).attr("y2", H);
      for (let y = Math.floor((cy - H / 2 / k) / step) * step; sy(y) > 0; y += step) gGrid.append("line").attr("class", "obs-grid").attr("y1", sy(y)).attr("y2", sy(y)).attr("x1", 0).attr("x2", W);
      gGrid.append("line").attr("class", "obs-bar").attr("x1", W - 16 - step * k).attr("x2", W - 16).attr("y1", H - 14).attr("y2", H - 14);
      gGrid.append("text").attr("class", "obs-lbl").attr("x", W - 16 - step * k / 2).attr("y", H - 20).attr("text-anchor", "middle").text(`${step.toLocaleString()} yd`);
      gGrid.append("text").attr("class", "obs-lbl").attr("x", W - 14).attr("y", 20).attr("text-anchor", "end").text("N ↑");
      // the targets' tracks: before firing dashed (held on the sheet's course: assumed), after solid
      A.targets.forEach((T, gi) => {
        if (!T.ok) return;
        const before = d3.range(A.start, T.at + 1, 5).map(t => P(A.targetAt(gi, t))), after = d3.range(T.at, A.end, 5).map(t => P(E.attackAt(A, t).targets[gi].p));
        gTrk.append("path").attr("class", "obs-trk assumed").attr("d", d3.line()(before));
        gTrk.append("path").attr("class", "obs-trk").attr("d", d3.line()(after));
        const lp = P(A.targetAt(gi, A.start));
        gLbl.append("text").attr("class", "obs-lbl").attr("x", lp[0] + 8).attr("y", lp[1] + 4)
          .text(`${A.targets.length > 1 ? `target ${gi + 1}: ` : ""}${pad3(T.course)}°, ${T.speed} kts (sheet)`);
      });
      const own = d3.range(A.start, A.end, 5).map(t => P(A.ownAt(t).p));
      gTrk.append("path").attr("class", "obs-trk own").attr("stroke", colour(cur.actor)).attr("d", d3.line()(own));
    }
    // a hull from above at true scale where that's visible, else a symbol: the kit's hullPlan (bow up, length 1)
    const planPath = (ft, beamFt) => { const s2 = Math.max(ft / 3 * k, 14) / 1; return hullPlan(beamFt / ft).replace(/(-?[\d.]+),(-?[\d.]+)/g, (_, x, y) => `${(-y * s2).toFixed(2)},${(+x * s2).toFixed(2)}`); };

    function drawPlot(q) {
      gLos.selectAll("*").remove(); gTorp.selectAll("*").remove(); gShip.selectAll("*").remove();
      const tg = q.targets[aimAt];
      if (tg) gLos.append("line").attr("class", "obs-los").attr("stroke", colour(cur.actor)).attr("x1", P(q.own.p)[0]).attr("y1", P(q.own.p)[1]).attr("x2", P(tg.p)[0]).attr("y2", P(tg.p)[1]);
      q.torps.forEach(x => {
        gTorp.append("line").attr("class", "obs-torp").attr("x1", P(x.t.from)[0]).attr("y1", P(x.t.from)[1]).attr("x2", P(x.p)[0]).attr("y2", P(x.p)[1]);
        if (x.done && x.t.hitTyped) gTorp.append("path").attr("class", "obs-hit").attr("d", "M-6,-6L6,6M6,-6L-6,6").attr("transform", `translate(${P(x.p)})`);
        else if (!x.done) gTorp.append("circle").attr("r", 2.5).attr("fill", "var(--ink)").attr("cx", P(x.p)[0]).attr("cy", P(x.p)[1]);
      });
      q.targets.forEach((T, gi) => { const [L, B] = cur.tg[gi].size; if (T) gShip.append("path").attr("d", planPath(L, B)).attr("fill", "var(--japan)").attr("opacity", T.hit ? 0.45 : 1)
        .attr("transform", `translate(${P(T.p)}) rotate(${T.course - 90})`); });
      const sil = window.SHIPS && SHIPS.balao;
      gShip.append("path").attr("d", planPath(sil ? +sil.length : 312, 27.3)).attr("fill", colour(cur.actor)).attr("transform", `translate(${P(q.own.p)}) rotate(${q.own.heading - 90})`);
      gShip.append("text").attr("class", "obs-lbl").attr("x", P(q.own.p)[0] - 12).attr("y", P(q.own.p)[1] + 20).attr("text-anchor", "end").attr("fill", colour(cur.actor)).style("font-weight", 600).text(nameOf(cur.actor));
    }

    // ---------- the view: periscope or bridge
    const scope = d3.select("#obs-scope");
    let S = 400, r = 190;
    const defs = scope.append("defs");
    const view = scope.append("g");
    const skyR = view.append("rect"), seaR = view.append("rect"), stars = view.append("g"), bodies = view.append("g"), shipG = view.append("g"), ticks = view.append("g");
    const reticle = scope.append("g").attr("class", "obs-reticle"), rim = scope.append("circle").attr("fill", "none").attr("stroke", "#000").attr("stroke-width", 14);
    const brgTxt = scope.append("text").attr("class", "obs-scopetxt").attr("text-anchor", "middle"), offTxt = scope.append("text").attr("class", "obs-scopetxt");
    const STARS = d3.range(420).map(i => ({ b: (i * 137.508) % 360, a: 2 + ((i * 61.8) % 70), m: 0.3 + ((i * 7) % 10) / 14 }));
    function layoutScope() {
      S = Math.min(scope.node().parentNode.clientWidth, 760); r = S / 2 - 10;   // the whole column
      scope.attr("width", S).attr("height", S);
      defs.html(`<clipPath id="obs-eye"><circle cx="${S / 2}" cy="${S / 2}" r="${r}"/></clipPath>
        <linearGradient id="obs-skyg" x1="0" y1="0" x2="0" y2="1"><stop id="obs-sky0" offset="0"/><stop id="obs-sky1" offset="1"/></linearGradient>
        <linearGradient id="obs-glit" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f3eed8" stop-opacity=".55"/><stop offset="1" stop-color="#f3eed8" stop-opacity="0"/></linearGradient>
        <filter id="obs-soft" x="-50%" y="0" width="200%" height="100%"><feGaussianBlur stdDeviation="7 2"/></filter>
        <filter id="obs-nv" color-interpolation-filters="sRGB"><feColorMatrix type="matrix" values="0.04 0.12 0.02 0 0.01  0.45 1.15 0.30 0 0.07  0.06 0.18 0.03 0 0.02  0 0 0 1 0"/></filter>`);
      view.attr("clip-path", "url(#obs-eye)");
      skyR.attr("width", S).attr("height", S).attr("fill", "url(#obs-skyg)");
      seaR.attr("width", S).attr("y", S / 2).attr("height", S / 2);
      reticle.selectAll("*").remove();
      reticle.append("line").attr("x1", S / 2 - r).attr("x2", S / 2 + r).attr("y1", S / 2).attr("y2", S / 2);
      reticle.append("line").attr("y1", S / 2 - r).attr("y2", S / 2 + r).attr("x1", S / 2).attr("x2", S / 2);
      rim.attr("cx", S / 2).attr("cy", S / 2).attr("r", r);
      brgTxt.attr("x", S / 2).attr("y", S - 22); offTxt.attr("x", 22).attr("y", 30);
    }
    scope.style("cursor", "ew-resize").call(d3.drag().on("drag", ev => { train = norm(train - ev.dx / ((2 * r) / field())); update(s); }))
      .on("dblclick", () => { train = 0; update(s); });
    const field = () => [...FIELDS.periscope, ...FIELDS.bridge].find(f => f[0] === power)[2];
    const mix = (a, b, t) => d3.interpolateRgb(a, b)(Math.max(0, Math.min(1, t)));

    // the light: the sun and moon computed for the time and place; how far a ship shows is illustrative
    function lightAt(ms) {
      const when = light === "day" ? E.localNoon(ms, cur.zone) : ms;
      const sk = E.sky(when, cur.ev.lat, cur.ev.lon);
      if (!sk) return null;
      const raw = E.light(sk), seen = light === "night" ? E.light(sk, true) : raw;
      return { day: raw.day, L: seen.L, V: seen.V, rawL: raw.L, sun: sk.sun, moon: sk.moon, when };
    }
    function moonPath(R, phase) {
      const f = Math.cos(phase * 2 * Math.PI), waxing = phase < 0.5, rx = Math.abs(f) * R;
      return `M0,${-R}A${R},${R} 0 0 ${waxing ? 1 : 0} 0,${R}A${rx},${R} 0 0 ${(f > 0) === waxing ? 0 : 1} 0,${-R}Z`;
    }
    function drawScope(q, lt) {
      const tg = q.targets[aimAt] || q.targets.find(Boolean);
      const BT = tg ? tg.bearing : q.own.heading, B = (BT + train + 360) % 360, fv = field(), ppd = (2 * r) / fv, cx = S / 2, hy = S / 2;
      const L = lt ? lt.L : 1, day = lt ? lt.day : 1;
      const skyLow = mix(mix("#05080d", "#2a3a55", L * 2), "#c7dcef", day);
      d3.select("#obs-sky0").attr("stop-color", mix(mix("#020407", "#141f33", L * 2), "#7fb0de", day));
      d3.select("#obs-sky1").attr("stop-color", skyLow);
      seaR.attr("fill", mix(mix("#010203", "#0b1422", L * 2), "#3c6385", day));
      stars.selectAll("*").remove(); bodies.selectAll("*").remove(); ticks.selectAll("*").remove(); shipG.selectAll("*").remove();
      // night vision: drawn in a modern image intensifier's green (#obs-nv), the stars as the darkness has them
      view.attr("filter", light === "night" ? "url(#obs-nv)" : null);
      const starA = Math.max(0, 0.9 - (lt ? lt.rawL : 1) * 2.2);
      if (starA > 0.02) for (const st of STARS) { const x = cx + norm(st.b - B) * ppd, y = hy - st.a * ppd;
        if (Math.hypot(x - cx, y - hy) < r && y < hy) stars.append("circle").attr("cx", x).attr("cy", y).attr("r", 0.7 + st.m * 0.6).attr("fill", "#dfe6f0").attr("opacity", starA * st.m); }
      const step = fv > 20 ? 5 : 1;
      for (let b = Math.ceil((B - fv / 2) / step) * step; b <= B + fv / 2; b += step) {
        const x = cx + norm(b - B) * ppd;
        ticks.append("line").attr("x1", x).attr("x2", x).attr("y1", hy - 4).attr("y2", hy + 4).attr("stroke", "#9fb3c8").attr("opacity", .6);
        if (b % (step * 2) === 0) ticks.append("text").attr("x", x).attr("y", hy + 16).attr("text-anchor", "middle").attr("class", "obs-tick").text(pad3(b));
      }
      offTxt.text("");
      if (lt) {
        const su = lt.sun, sdx = norm(su.bearing - B) * ppd, sdy = -su.altitude * ppd;
        if (su.altitude > -1 && Math.abs(sdx) < r) {
          if (su.altitude < 40) bodies.append("rect").attr("x", cx + sdx - 4 * ppd).attr("width", 8 * ppd).attr("y", hy).attr("height", S - hy).attr("fill", "url(#obs-glit)").attr("filter", "url(#obs-soft)").attr("opacity", 0.9);
          if (Math.hypot(sdx, sdy) < r) bodies.append("circle").attr("cx", cx + sdx).attr("cy", hy + sdy).attr("r", Math.max(5, 0.27 * ppd)).attr("fill", "#fffbe9");
        }
        const m = lt.moon, mdx = norm(m.bearing - B) * ppd, mdy = -m.altitude * ppd, show = m.altitude > 0 && m.fraction > 0.01 && day < 0.9;
        if (show && Math.abs(mdx) < r) {
          bodies.append("rect").attr("x", cx + mdx - 2.5 * ppd).attr("width", 5 * ppd).attr("y", hy).attr("height", S - hy).attr("fill", "url(#obs-glit)").attr("filter", "url(#obs-soft)").attr("opacity", m.fraction * Math.min(1, 0.4 + 30 / Math.max(m.altitude, 1)));
          if (Math.hypot(mdx, mdy) < r) bodies.append("path").attr("d", moonPath(Math.max(4, 0.26 * ppd), m.phase)).attr("transform", `translate(${cx + mdx},${hy + mdy})`).attr("fill", "#efe9d2");
          else offTxt.text(`moon above the view: ${Math.round(m.altitude)}° up, ${Math.round(m.fraction * 100)}% lit`);
        } else if (show) offTxt.text(`moon off to the ${norm(m.bearing - B) < 0 ? "left" : "right"}: ${pad3(m.bearing)}°, ${Math.round(m.altitude)}° up, ${Math.round(m.fraction * 100)}% lit`);
        else if (day < 0.5) offTxt.text("no moon up");
      }
      // each target: its outline, foreshortened by the angle on the bow, at its angular size
      q.targets.forEach((T, gi) => {
        const g = cur.tg[gi], [Lft, Bft] = g.size, shape = g.ship ? g.ship.sil.d : window.SIL_CATEGORIES && (SIL_CATEGORIES.shapes[g.kind] || SIL_CATEGORIES.shapes.cargo);
        if (!T || !shape) return;
        const projFt = Lft * Math.abs(Math.sin(rad(T.aob))) + Bft * Math.abs(Math.cos(rad(T.aob)));
        const vis = lt ? 1 - Math.exp(-Math.pow(lt.V / T.range, 1.5)) : 1;
        const hull = mix(mix(skyLow, "#020304", 0.97), "#2d3237", day);
        // a class outline is in feet (x from the stern, y up from the waterline as negative), the generic one in its
        // 120 x 24 box with the waterline at 22: each scaled to the target's angular size, foreshortened by the angle on the bow
        const wide = 2 * deg(Math.atan(projFt / 3 / 2 / T.range)) * ppd, flip = T.aob < 0 ? -1 : 1;
        const tr = g.ship
          ? `translate(${cx + norm(T.bearing - B) * ppd},${hy}) scale(${flip * wide / Lft},${deg(Math.atan(1 / 3 / T.range)) * ppd}) translate(${-Lft / 2},0)`
          : `translate(${cx + norm(T.bearing - B) * ppd},${hy}) scale(${flip * wide / 118},${deg(Math.atan(Lft / 118 / 3 / T.range)) * ppd}) translate(-60,-22)`;
        shipG.append("path").attr("d", shape).attr("fill", T.hit ? mix(hull, "#7a2a20", 0.4) : hull).attr("opacity", vis).attr("transform", tr);
      });
      // a target outside the field of view: a marker at the rim, on the horizon, on the side to train towards
      const KIND_WORD = { cargo: "AK", tanker: "AO", destroyer: "DD", escort: "escort", gunboat: "gunboat", submarine: "submarine", carrier: "CV" };
      q.targets.forEach((T, gi) => {
        if (!T || q.targets.filter(Boolean).length < 2) return;
        const d = norm(T.bearing - B);
        if (Math.abs(d) * ppd < r - 8) return;
        const left = d < 0, label = `${left ? "◂ " : ""}target ${gi + 1}, ${cur.tg[gi].ship ? cur.tg[gi].ship.who.name : KIND_WORD[cur.tg[gi].kind] || cur.tg[gi].kind}: ${pad3(T.bearing)}°, ${Math.round(T.range).toLocaleString("en-US")} yd${left ? "" : " ▸"}`;
        shipG.append("text").attr("class", "obs-tick obs-off").attr("x", left ? cx - r + 16 : cx + r - 16).attr("y", hy + 36 + gi * 16)
          .attr("text-anchor", left ? "start" : "end").attr("fill", "#e6edf5").text(label);
      });
      brgTxt.text(`true bearing ${pad3(B)}°${train ? "  ·  double-click: back on the target" : ""}`);
      return { B, fv };
    }

    // ---------- the sky from above: zenith in the middle, horizon round the edge, north up
    const skyc = d3.select("#obs-sky"), SC = 200, SR = SC / 2 - 20;
    skyc.attr("width", SC).attr("height", SC);
    const altR = a => SR * (90 - a) / 90, at2 = (b, a) => [SC / 2 + altR(a) * Math.sin(rad(b)), SC / 2 - altR(a) * Math.cos(rad(b))];
    function drawSky(lt, B, BT, fv) {
      skyc.selectAll("*").remove();
      const L = lt ? lt.rawL : 1, day = lt ? lt.day : 1;
      skyc.append("circle").attr("cx", SC / 2).attr("cy", SC / 2).attr("r", SR).attr("fill", mix(mix("#05080d", "#2a3a55", L * 2), "#c7dcef", day)).attr("stroke", "var(--ink-3)");
      for (const a of [30, 60]) skyc.append("circle").attr("cx", SC / 2).attr("cy", SC / 2).attr("r", altR(a)).attr("fill", "none").attr("stroke", "#9fb3c8").attr("stroke-opacity", .35).attr("stroke-dasharray", "2 3");
      for (const [b, n] of [[0, "N"], [90, "E"], [180, "S"], [270, "W"]]) { const [x, y] = at2(b, -13); skyc.append("text").attr("class", "obs-lbl").attr("x", x).attr("y", y + 4).attr("text-anchor", "middle").text(n); }
      const arc = d3.arc().innerRadius(altR(fv / 2)).outerRadius(SR).startAngle(rad(B - fv / 2)).endAngle(rad(B + fv / 2));
      skyc.append("path").attr("d", arc()).attr("transform", `translate(${SC / 2},${SC / 2})`).attr("fill", "#9fb3c8").attr("fill-opacity", .35).attr("stroke", "#9fb3c8");
      const [tx, ty] = at2(BT, 0); skyc.append("circle").attr("cx", tx).attr("cy", ty).attr("r", 3.5).attr("fill", "var(--ink)").attr("stroke", "var(--surface)");
      if (!lt) return;
      if (lt.sun.altitude > 0) { const [x, y] = at2(lt.sun.bearing, lt.sun.altitude); skyc.append("circle").attr("cx", x).attr("cy", y).attr("r", 7).attr("fill", "#ffd34d").attr("stroke", "#c79a1e"); }
      if (lt.moon.altitude > 0 && lt.moon.fraction > 0.01) { const [x, y] = at2(lt.moon.bearing, lt.moon.altitude); skyc.append("circle").attr("cx", x).attr("cy", y).attr("r", 6.5).attr("fill", "#2a2d33");
        skyc.append("path").attr("d", moonPath(6.5, lt.moon.phase)).attr("transform", `translate(${x},${y})`).attr("fill", "#efe9d2"); }
    }

    // ---------- the readout, the clock, the torpedoes and the sheet's words
    const clock = sec => {
      const ms = cur.t0 + sec * 1000 + E.zoneHours(cur.zone || "Z") * 3600e3, d = new Date(ms), p = n => String(n).padStart(2, "0");
      return `${p(d.getUTCHours())}${p(d.getUTCMinutes())}:${p(d.getUTCSeconds())}${cur.zone ? " " + cur.zone : ""}`;
    };
    const rel = sec => sec < 0 ? `${Math.round(-sec)} s before firing` : `${Math.round(sec)} s after the first torpedo`;
    function drawReadout(q, lt) {
      const T = q.targets[aimAt], TS = A.targets[aimAt], fired = q.torps.length;
      const cells = [
        ["Time", clock(s), rel(s)],
        ["Target bearing", T ? pad3(T.bearing) + "° T" : "—", "computed"],
        ["Range", T ? Math.round(T.range).toLocaleString() + " yd" : "—", s === 0 && TS.ok ? `sheet: ${TS.range}` : "computed"],
        ["Angle on the bow", T ? `${Math.abs(Math.round(T.aob))}° ${T.aob >= 0 ? "starboard" : "port"}` : "—", "computed"],
        ["Target", TS.ok ? `${pad3(TS.course)}°, ${TS.speed} kts` : "—", "the sheet's"],
        ["Torpedoes", fired ? `${fired} of ${A.torps.length} fired` : "not yet fired", fired ? `hits typed: ${A.torps.filter(t => t.hitTyped && q.torps.some(x => x.t === t)).length}` : ""],
      ];
      document.getElementById("obs-read").innerHTML = cells.map(([k, v, n]) => `<div><div class="k">${k}</div><div class="v">${esc(v)}</div><div class="n">${esc(n)}</div></div>`).join("");
      document.getElementById("obs-clock").textContent = clock(s);
      const sk = lt ? `${{ was: "", day: "Broad daylight: the same date at local noon. ", night: "Night vision: the scene as it was, the darkness lifted and drawn in a modern image intensifier's green; the rendering is illustrative, not from a source, and the sun and moon are as computed. " }[light]}Sun ${pad3(lt.sun.bearing)}°, ${lt.sun.altitude >= 0 ? Math.round(lt.sun.altitude) + "° up" : Math.round(-lt.sun.altitude) + "° below the horizon"}; moon ${pad3(lt.moon.bearing)}°, ${lt.moon.altitude >= 0 ? Math.round(lt.moon.altitude) + "° up" : "below the horizon"}, ${Math.round(lt.moon.fraction * 100)}% lit (computed for ${cur.ev.lat.toFixed(2)}°, ${cur.ev.lon.toFixed(2)}°). How far a ship shows in this light, about ${(Math.round(lt.V / 100) * 100).toLocaleString()} yards here, is illustrative, not from a source.` : "The sun and moon need SunCalc, which didn't load.";
      document.getElementById("obs-light-note").textContent = sk;
    }
    function drawTorpTable() {
      const head = `<tr><th>Tube</th><th>Fired</th><th>Torpedo</th><th>Gyro</th><th>Track typed</th><th>Track computed</th><th>Run (computed)</th><th>Typed</th></tr>`;
      const rows = A.torps.map(t => {
        const T = A.targets[t.target], g = E.gyroOf(t.row.gyro), own = t.course != null && g != null ? t.course - g : null;
        const fc = own != null && T.ok ? E.fireControl({ ownCourse: own, gyro: g, targetCourse: T.course, targetSpeed: T.speed, torpedoSpeed: t.knots }) : null;
        const off = fc && /^\d/.test(t.row.track || "") ? Math.abs(norm((fc.side === "S" ? fc.track : -fc.track) - (parseFloat(t.row.track) * (/P$/.test(t.row.track) ? -1 : 1)))) : null;
        // a typed hit that the computation has passing clear: said as a gap, since the assumptions below can open one
        const clear = t.passed > 20 ? `passing ${Math.round(t.passed)} yd clear of the hull${t.hitTyped ? "*" : ""}` : t.hitTyped ? "" : "reaching the hull";
        const run = t.run != null ? `${Math.round(t.run)} s, ${Math.round(t.runYd).toLocaleString()} yd${clear ? ", " + clear : ""}` : "—";
        return `<tr><td>${esc(t.tube)}</td><td>${t.s} s${t.timeAssumed ? " (assumed)" : ""}</td><td>Mk ${esc(t.row.torpedo || "?")}, ${t.knots} kts${{ assumed: " (assumed)", sheet: " (sheet)", atule: " (ATULE's sheet)" }[t.speedBasis]}</td><td class="typed">${esc(t.row.gyro || "")}</td><td class="typed">${esc(t.row.track || "")}</td><td>${fc ? `${fc.track.toFixed(0)}${fc.side}${off != null && off > 10 ? " <b>disagrees</b>" : ""}` : "—"}</td><td>${run}</td><td class="typed">${esc(t.row.hit || "")}</td></tr>`;
      }).join("");
      const starred = A.torps.some(t => t.hitTyped && t.passed > 20);
      document.getElementById("obs-torps").innerHTML = `<table class="obs-table">${head}${rows}</table>` +
        `<p class="below">Track computed: own course plus gyro, against the target's course (the same arithmetic as tools/check_attacks.py); "disagrees" is more than 10° from the track typed, kept as typed.` +
        `${starred ? " * Typed a hit, but on these figures the torpedo passes clear: the point of aim, the target's size and the steady courses are assumed (below), so this is a gap in the reconstruction, not a finding about the sheet." : ""}</p>`;
    }
    function drawWords() {
      const w = cur.sh.words, first = w[0] || {};
      const parts = [first.type_attack && `<p><i>Type attack.</i> <span class="typed">${esc(first.type_attack)}</span></p>`,
        first.description && `<p><i>Target.</i> <span class="typed">${esc(first.description)}</span></p>`,
        first.remarks && `<p><i>Remarks.</i> <span class="typed">${esc(first.remarks)}</span></p>`,
        ...w.filter(x => x.note).map(x => `<p class="assume">${esc(x.note)}</p>`)].filter(Boolean);
      if (A.problems.length) {
        document.getElementById("obs-words").innerHTML = parts.join("") +
          `<p class="below"><b>Not drawn:</b> ${A.problems.map(esc).join("; ")}. The rows above are what ${esc(nameOf(cur.actor))}'s report types (${EV.cite(cur.sh.cite, "src")}); the courses are in her narrative, still to be read for this view.</p>`;
        return;
      }
      const list = [...A.assumed.map(esc), ...cur.tg.map((g, gi) => { const who = cur.tg.length > 1 ? `target ${gi + 1}${A.targets[gi].range != null ? ` (${A.targets[gi].range} yds at firing)` : ""}` : "the target";
          return g.ship ? `${who} drawn as ${esc(g.ship.who.name)}, the one ${esc(g.kind)} the engagement names on the other side, in her class's outline (${esc(g.ship.sil.name)}, ${g.size[0]} ft, from its plate): which ship the sheet's target was is ours, inferred`
            : `${who}'s size, a ${g.kind} of ${g.size[0]} ft (assumed${cur.tg.length > 1 ? (cur.unsure ? ": the sheet names several kinds and not which target was which, so a merchant ship" : ", the kind from the sheet's own words for each target where it gives them") : ""}), drawn as the kit's generic outline`; }),
        "the fields of view (periscope 32° and 8°, binoculars 7°: secondary sources, to check against the Submarine Periscope Manual, NAVPERS 16165)"];
      document.getElementById("obs-words").innerHTML = parts.join("") +
        `<p class="below">From ${esc(nameOf(cur.actor))}'s attack data sheet, as typed: ${EV.cite(cur.sh.cite, "src")}. Computed from it, and assumed: ${list.join("; ")}. A reconstruction, not a photograph: a lead, not a record.</p>`;
    }

    // ---------- the clock
    function update(sec) {
      s = Math.max(A.start, Math.min(A.end, sec));
      slider.value = s;
      const q = E.attackAt(A, s);
      const firing = q.torps.length ? q.torps[q.torps.length - 1].t.target : 0;
      if (!train) aimAt = firing;
      const lt = lightAt(cur.t0 + s * 1000);
      drawPlot(q);
      const { B, fv } = drawScope(q, lt);
      const tg = q.targets[aimAt];
      drawSky(lt, B, tg ? tg.bearing : B, fv);
      drawReadout(q, lt);
    }
    function stop() { if (timer) { timer.stop(); timer = null; } playBtn.textContent = "▶"; playBtn.setAttribute("aria-label", "Play"); }
    function play() {
      if (s >= A.end) s = A.start;
      playBtn.textContent = "❚❚"; playBtn.setAttribute("aria-label", "Pause");
      let last = null;
      timer = d3.timer(el => { const dt = last == null ? 0 : el - last; last = el; update(s + dt / 1000 * 10);   // ten times real time
        if (s >= A.end) stop(); });
    }
    let lastW = 0;   // redraw when the card's width changes, not its height (the readout and notes change that)
    function resize() { const w = card.clientWidth; if (!cur || A.problems.length || w === lastW) return; lastW = w; layoutPlot(); layoutScope(); update(s); }
    layoutScope();
    choose(Math.max(0, list.findIndex(x => !E.attackSheet(x.sh.torpedoes).problems.length)), false);   // the first that can be drawn
    new ResizeObserver(() => resize()).observe(card);
    return {
      // the page's clock reached an attack (a log entry or a mark clicked): show it
      pick(actor, ref) { const i = list.findIndex(x => x.actor === actor && x.ref === ref); if (i >= 0 && list[i] !== cur) choose(i, false); },
    };
  }
  return { mount, attacks, targetsOf };
})();
