// USS Haynsworth (DD-700), 6 April 1945: the figures of her engagement (panels.js registers them for
// engagement.html?e=haynsworth-1945-04-06, after the story). The drawing is the former story page's, mounted into a host
// element by each panel instead of into the page's own ids: the last five minutes as the action report tells them, in
// schematic panels; the Judy beside the ship to scale at 100 and 150 ft; an estimated path for the last half-minute,
// with the assumptions as controls; where she was hit, by frame; TG 58.3 and its pickets as the 6 April records name
// them; and the aircraft, from the recognition plates. Silhouettes come from records/silhouettes/silhouettes.yml
// through silhouettes.js (SHIPS, AIRCRAFT, hullPlan); nothing here is drawn from memory. Colours are the page's
// (engage.css): the US side slot 1, US aircraft slot 3, the Japanese side ink, the hit red; anything assumed is hatched
// or dashed and says so.
window.HaynsworthPanels = (() => {
  const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  // an aircraft plan view centred at [x, y], nose toward `hdg`, `size` px span
  function planeAt(g, type, [x, y], hdg, size, cls) {
    const a = AIRCRAFT[type].plan, s = size / a.w;
    return g.append("path").attr("d", a.d).attr("class", cls)
      .attr("transform", `translate(${x},${y}) rotate(${hdg}) scale(${s}) translate(${-a.w / 2},${-a.h / 2})`);
  }
  // Frames: 21 in apart, frame 0 at the forward perpendicular, after perpendicular at frame 210 (BuShips plans
  // DD692-S-01030-1 and DD692-S0101-601245). AP pinned where the silhouette's stern meets the waterline (x = 4 ft),
  // which fits its stacks to the plan better than pinning FP to its stem
  const FRAME = f => 4 + (210 - f) * 21 / 12;
  const HIT_FRAME = 85;   // in the radio transmitter room, beside mount 41 (frames 65-92 on the class plan); assumed within that
  const note = (host, text) => host.append("p").attr("class", "schem-note").text(text);

  // ---------- 1245 to 1250: the attack, as the action report tells it
  function sequence(host) {
    const h = d3.select(host);
    const plates = h.append("div").attr("class", "hp-plates");
    const S = 220, C = S / 2, HDG = 20;
    // trueP: a true bearing; polar: relative to the bow (000 ahead, 090 starboard beam, 270 port beam)
    const trueP = (brg, r) => { const a = (brg - 90) * Math.PI / 180; return [C + r * Math.cos(a), C + r * Math.sin(a)]; };
    const polar = (rel, r) => trueP(HDG + rel, r);
    const add2 = (a, b) => [a[0] + b[0] - C, a[1] + b[1] - C];
    const hitPt = add2(polar(0, 6), polar(90, 3));   // abaft the bridge, starboard side (hull drawn 58 px long)
    const panels = [
      { n: "1232", cap: `Course changed to 020°. SC-3 radar: <q>bogey at 010°, distance 22 miles</q>. Fighters vectored out <q>merged with bogey on scope until raid had passed close aboard port beam</q>.`,
        draw: g => { arrow(g, trueP(10, 100), trueP(10, 42), "stroke-us", true); label(g, add2(trueP(10, 96), [C - 8, C + 4]), "bogey 010°, 22 mi", "end"); } },
      { n: "1245", cap: `<q>The sound of dog-fight and machine gun fire</q>, tracked from the port bow to the beam. A plane (<q>a Judy or Zeke</q>) splashed 1,500 yards on the port quarter.`,
        draw: g => { arcAt(g, 315, 270, 72); label(g, polar(300, 90), "dog-fight heard", "middle"); cross(g, polar(225, 72)); label(g, add2(polar(225, 72), [C + 10, C + 18]), "splashed, 1,500 yd", "start"); } },
      { n: "after 1245", cap: `A Judy <q>appeared out of the clouds in a very steep dive</q> with a Corsair on each side. All three <q>pulled up sharply short of the water</q>; the Corsairs went back into the cloud and the Judy <q>headed away from the ship</q>. Where, the report doesn't say; it is drawn on the side it came back from.`,
        draw: g => { planeAt(g, "corsair", polar(82, 58), HDG + 150, 22, "fill-air"); planeAt(g, "corsair", polar(118, 62), HDG + 150, 22, "fill-air"); planeAt(g, "judy", polar(100, 64), HDG + 120, 26, "fill-jp");
          label(g, add2(polar(100, 64), [C, C + 34]), "position not recorded", "middle", true); } },
      { n: "1250", cap: `Fire opened at 1,500 yards, altitude 150 ft. The Judy turned to starboard, <q>winged over</q> into the ship. Its bomb, <q>released or ... knocked off in the turn</q>, fell 1,000 yards abeam (the side isn't stated). <q>Striking at 1250 Item</q> abaft the bridge.`,
        draw: g => { arrowCurve(g, polar(52, 80), polar(40, 46), add2(hitPt, polar(70, 8))); planeAt(g, "judy", polar(52, 86), HDG + 230, 24, "fill-jp"); splash(g, polar(92, 92)); label(g, add2(polar(92, 92), [C + 8, C + 18]), "bomb, 1,000 yd abeam", "end");
          g.append("circle").attr("cx", hitPt[0]).attr("cy", hitPt[1]).attr("r", 6).attr("class", "fill-hit"); } },
    ];
    const label = (g, [x, y], t, anchor = "start", it = false) => g.append("text").attr("class", "mk-label small").attr("x", x).attr("y", y).attr("text-anchor", anchor).style("font-style", it ? "italic" : null).text(t);
    const arrow = (g, a, b, cls, dashed) => g.append("path").attr("d", `M${a[0]},${a[1]}L${b[0]},${b[1]}`).attr("class", cls).attr("stroke-width", 1.6).attr("stroke-dasharray", dashed ? "3 3" : null).attr("marker-end", "url(#hp-arr)").attr("fill", "none");
    const arrowCurve = (g, a, m, b) => g.append("path").attr("d", `M${a[0]},${a[1]}Q${m[0]},${m[1]} ${b[0]},${b[1]}`).attr("class", "stroke-jp").attr("stroke-width", 1.6).attr("stroke-dasharray", "4 3").attr("fill", "none").attr("marker-end", "url(#hp-arr)");
    const arcAt = (g, b0, b1, r) => { const pts = d3.range(b0, b1 - 1, -4).map(b => polar(b, r)); g.append("path").attr("d", d3.line()(pts)).attr("class", "stroke-us").attr("stroke-width", 1.4).attr("stroke-dasharray", "2 3").attr("fill", "none"); };
    const cross = (g, [x, y]) => g.append("path").attr("d", `M${x - 6},${y - 6}L${x + 6},${y + 6}M${x - 6},${y + 6}L${x + 6},${y - 6}`).attr("class", "stroke-air").attr("stroke-width", 2.2);
    const splash = (g, [x, y]) => g.append("path").attr("d", `M${x - 7},${y}Q${x - 3},${y - 10} ${x},${y - 2}Q${x + 3},${y - 10} ${x + 7},${y}`).attr("class", "stroke-jp").attr("fill", "none").attr("stroke-width", 1.4);

    panels.forEach(pn => {
      const c = plates.append("div").attr("class", "card hp-panel");
      c.append("div").attr("class", "num").text(pn.n);
      const svg = c.append("svg").attr("viewBox", `0 0 ${S} ${S}`).attr("role", "img").attr("aria-label", pn.n);
      if (!document.getElementById("hp-arr")) svg.append("defs").append("marker").attr("id", "hp-arr").attr("viewBox", "0 0 10 10").attr("refX", 9).attr("refY", 5).attr("markerWidth", 6).attr("markerHeight", 6).attr("orient", "auto-start-reverse")
        .append("path").attr("d", "M0,0L10,5L0,10Z").attr("fill", "var(--ink-2)");
      svg.append("circle").attr("cx", C).attr("cy", C).attr("r", 104).attr("fill", "none").attr("stroke", "var(--rule)");
      svg.append("text").attr("class", "mk-label small").attr("x", C).attr("y", 12).attr("text-anchor", "middle").text("N");
      svg.append("path").attr("d", hullPlan(0.11)).attr("class", "fill-us").attr("transform", `translate(${C},${C}) rotate(${HDG}) scale(58)`);
      svg.append("text").attr("class", "mk-label small").attr("x", polar(200, 40)[0]).attr("y", polar(200, 40)[1]).attr("text-anchor", "middle").text("020°");
      pn.draw(svg);
      c.append("div").attr("class", "cap").html(pn.cap);
    });
    note(h, "Silhouettes: JUDY 33 from TAIC's plate (CINCPAC-CINCPOA Bulletin 105-45, July 1945); F4U from FM 30-30 (April 1943). Hull outline schematic.");
  }

  // ---------- to scale: the Judy at 100 ft
  function scale100(host) {
    const s = SHIPS.sumner, j = AIRCRAFT.judy, W = 1000, H = 400, left = 70, k = 720 / s.length, wl = 366;
    const svg = d3.select(host).append("div").attr("class", "card damage").append("svg").attr("class", "wide").attr("viewBox", `0 0 ${W} ${H}`)
      .attr("role", "img").attr("aria-label", "Haynsworth in profile with a Judy drawn to the same scale at 100 and 150 feet");
    const X = ft => left + ft * k, Y = ft => wl - ft * k;
    // height ruler and the two recorded heights
    const ru = svg.append("g").attr("class", "ruler");
    for (let f = 0; f <= 175; f += 25) {
      ru.append("line").attr("x1", left - 30).attr("x2", left - 24).attr("y1", Y(f)).attr("y2", Y(f));
      ru.append("text").attr("x", left - 34).attr("y", Y(f) + 3.5).attr("text-anchor", "end").text(f + " ft");
    }
    ru.append("line").attr("x1", left - 27).attr("x2", left - 27).attr("y1", Y(0)).attr("y2", Y(175));
    [[100, "100 ft (Irons)"], [150, "150 ft when fire opened at 1,500 yd (action report)"]].forEach(([f, t]) => {
      svg.append("line").attr("class", "ht-line").attr("x1", left - 24).attr("x2", W - 20).attr("y1", Y(f)).attr("y2", Y(f));
      svg.append("text").attr("class", "callout").attr("x", left - 18).attr("y", Y(f) - 5).text(t);
    });
    svg.append("line").attr("x1", 10).attr("x2", W - 10).attr("y1", wl).attr("y2", wl).attr("stroke", "var(--ink-3)");
    svg.append("text").attr("class", "frame-lab").attr("x", W - 20).attr("y", wl + 16).attr("text-anchor", "end").text("waterline, flat sea assumed");
    svg.append("path").attr("d", s.d).attr("class", "sil").attr("transform", `translate(${left},${wl}) scale(${k})`);
    // masthead
    const mast = [X(232), Y(84)];
    svg.append("path").attr("class", "leader").attr("d", `M${mast[0] + 4},${mast[1]}L${mast[0] + 70},${mast[1] + 8}`);
    svg.append("text").attr("class", "callout").attr("x", mast[0] + 74).attr("y", mast[1] + 12).text("masthead 84 ft (ONI 54-D)");
    // head-on Judy over the hit frame, at 150 ft (outline) and 100 ft (solid)
    const fs = j.span * k / j.front.w, hx = X(FRAME(HIT_FRAME));
    const front = (alt, cls) => svg.append("path").attr("d", j.front.d).attr("class", cls)
      .attr("transform", `translate(${hx - j.front.cx * fs},${Y(alt) - j.front.cy * fs}) scale(${fs})`);
    front(150, "ghost").attr("stroke-width", 1.2 / fs);
    front(100, "sil");
    svg.append("path").attr("class", "leader").attr("d", `M${hx},${Y(100) + 8}L${hx},${Y(30)}`).attr("stroke-dasharray", "2 3");
    svg.append("circle").attr("cx", hx).attr("cy", Y(24)).attr("r", 4).attr("class", "fill-hit");
    svg.append("text").attr("class", "callout b").attr("x", hx - 34).attr("y", Y(100) - 22).attr("text-anchor", "end").text("JUDY 33 head-on, 37′9½″ span");
    svg.append("text").attr("class", "callout").attr("x", hx - 34).attr("y", Y(100) - 8).attr("text-anchor", "end").text("at 100 ft it clears her masthead by 16 ft");
    svg.append("path").attr("class", "leader").attr("d", `M${hx},${Y(22)}L${hx},${wl + 8}`).attr("stroke-dasharray", "2 3");
    svg.append("text").attr("class", "callout").attr("x", hx).attr("y", wl + 22).attr("text-anchor", "middle").text(`hit, frame ~${HIT_FRAME} (starboard side, toward you)`);
    // side view, same scale, ahead of the bow, for length
    const ps = j.length * k / j.profile.w, px = X(s.length) + 50;
    svg.append("path").attr("d", j.profile.d).attr("class", "sil").attr("transform", `translate(${px},${Y(100) - j.profile.h * ps * 0.6}) scale(${ps})`);
    svg.append("text").attr("class", "callout").attr("x", px + j.length * k / 2).attr("y", Y(100) + 22).attr("text-anchor", "middle").text("side view, 33′7″");
    svg.append("text").attr("class", "frame-lab").attr("x", left).attr("y", 16).text("All heights and lengths in feet at one scale. Horizontal placement of the aircraft is for comparison only.");
  }

  // ---------- to scale: an estimated path
  function path(host) {
    const KT = 1.68781, G = 32.174, VS = 25 * KT, L = SHIPS.sumner.length, BEAM = 41;
    // hit point in ship coordinates (x to starboard, y forward of amidships), ft
    const hitOff = [BEAM / 2, FRAME(HIT_FRAME) - L / 2];
    const h = d3.select(host);
    const card = h.append("div").attr("class", "card path-card");
    card.append("div").attr("class", "path-ctl").html(`
        <label>Speed in the turn <input type="range" data-p="vturn" min="150" max="320" step="10" value="220"> <output data-o="vturn"></output></label>
        <label>Bank in the turn <select data-p="bank"><option value="45">45°</option><option value="60" selected>60°</option><option value="70">70°</option></select></label>
        <label>Speed on the run in <input type="range" data-p="vfinal" min="200" max="360" step="10" value="300"> <output data-o="vfinal"></output></label>
        <label>Where it was when fire opened <select data-p="start"><option value="90" selected>abeam (090° relative)</option><option value="60">on the starboard bow (060°)</option><option value="120">on the starboard quarter (120°)</option></select></label>`);
    const ui = Object.fromEntries(["vturn", "bank", "vfinal", "start"].map(k => [k, card.select(`[data-p="${k}"]`).node()]));
    const out = Object.fromEntries(["vturn", "vfinal"].map(k => [k, card.select(`[data-o="${k}"]`)]));
    const W = 1000, H = 640;
    const svg = card.append("svg").attr("class", "wide").attr("viewBox", `0 0 ${W} ${H}`).attr("role", "img").attr("aria-label", "Plan view, to scale, of an estimated path of the Judy from 1,500 yards to the hit");
    const read = card.append("div").attr("class", "path-read");

    function solve() {
      const vT = +ui.vturn.value * KT, vF = +ui.vfinal.value * KT, bank = +ui.bank.value * Math.PI / 180;
      const r = vT * vT / (G * Math.tan(bank));
      const rel = +ui.start.value * Math.PI / 180;            // relative bearing of the plane from amidships at t = 0
      const R0 = 4500;                                         // 1,500 yd
      const P0 = [R0 * Math.sin(rel), R0 * Math.cos(rel)];
      const hdg0 = rel;                                        // heading directly away
      // right turn: centre to the right of the heading
      const C = [P0[0] + r * Math.cos(hdg0), P0[1] - r * Math.sin(hdg0)];
      const th0 = Math.atan2(P0[1] - C[1], P0[0] - C[0]);
      let tHit = 30, best = null;
      for (let it = 0; it < 40; it++) {
        const Hp = [hitOff[0], VS * tHit + hitOff[1]];
        let prev = null, found = null;
        for (let dth = 0; dth <= 2 * Math.PI; dth += 0.002) {
          const th = th0 - dth, T = [C[0] + r * Math.cos(th), C[1] + r * Math.sin(th)], d = [Math.sin(th), -Math.cos(th)];
          const w = [Hp[0] - T[0], Hp[1] - T[1]], cr = d[0] * w[1] - d[1] * w[0], dot = d[0] * w[0] + d[1] * w[1];
          if (prev !== null && Math.sign(cr) !== Math.sign(prev) && dot > 0) { found = { dth, T, w }; break; }
          prev = cr;
        }
        if (!found) break;                                      // the hit point is inside the turn: no straight run
        const arc = r * found.dth, straight = Math.hypot(...found.w);
        const t = arc / vT + straight / vF;
        best = { r, C, th0, dth: found.dth, T: found.T, Hp, arc, straight, tArc: arc / vT, t, vT, vF, P0 };
        if (Math.abs(t - tHit) < 0.01) break;
        tHit = t;
      }
      return best;
    }

    function draw() {
      out.vturn.text(ui.vturn.value + " kn");
      out.vfinal.text(ui.vfinal.value + " kn");
      svg.selectAll("*").remove();
      const s = solve();
      if (!s) { svg.append("text").attr("x", 20).attr("y", 30).attr("class", "callout").text("No path: the turn is wider than the room it had. Try a lower speed or more bank."); read.html(""); return; }
      // the path, sampled with times
      const pts = [];
      for (let a = 0; a <= s.dth; a += 0.01) { const th = s.th0 - a; pts.push({ p: [s.C[0] + s.r * Math.cos(th), s.C[1] + s.r * Math.sin(th)], t: a * s.r / s.vT }); }
      const n = 40;
      for (let i = 1; i <= n; i++) { const f = i / n; pts.push({ p: [s.T[0] + (s.Hp[0] - s.T[0]) * f, s.T[1] + (s.Hp[1] - s.T[1]) * f], t: s.tArc + f * s.straight / s.vF }); }
      // where it was 1,000 yd from the ship, coming back in (the bomb fell about 1,000 yd abeam)
      let far = 0, bomb = null;
      pts.forEach(q => { const d = Math.hypot(q.p[0], q.p[1] - VS * q.t); if (d > far) far = d; else if (!bomb && d <= 3000) bomb = q; });
      // fit everything to the view, one scale both ways
      const ext = [...pts.map(q => q.p), [0, 0], [0, VS * s.t], [-600, 0]];
      const xs = ext.map(p => p[0]), ys = ext.map(p => p[1]);
      const [x0, x1, y0, y1] = [Math.min(...xs) - 700, Math.max(...xs) + 700, Math.min(...ys) - 600, Math.max(...ys) + 700];
      const k = Math.min(W / (x1 - x0), H / (y1 - y0));
      const ox = (W - (x1 - x0) * k) / 2, oy = (H - (y1 - y0) * k) / 2;
      const P = ([x, y]) => [ox + (x - x0) * k, H - oy - (y - y0) * k];
      // 1,000 ft grid
      for (let gx = Math.ceil(x0 / 1000) * 1000; gx <= x1; gx += 1000) { const a = P([gx, y0]), b = P([gx, y1]); svg.append("line").attr("class", "grid-ft").attr("x1", a[0]).attr("x2", b[0]).attr("y1", a[1]).attr("y2", b[1]); }
      for (let gy = Math.ceil(y0 / 1000) * 1000; gy <= y1; gy += 1000) { const a = P([x0, gy]), b = P([x1, gy]); svg.append("line").attr("class", "grid-ft").attr("x1", a[0]).attr("x2", b[0]).attr("y1", a[1]).attr("y2", b[1]); }
      // 1,500 yd from the ship when fire opened
      const c0 = P([0, 0]);
      svg.append("circle").attr("cx", c0[0]).attr("cy", c0[1]).attr("r", 4500 * k).attr("class", "ring");
      const rl = P([4500 * Math.sin(-2.3), 4500 * Math.cos(-2.3)]);
      svg.append("text").attr("class", "mk-label small").attr("x", Math.min(W - 130, Math.max(8, rl[0]))).attr("y", Math.min(H - 40, Math.max(30, rl[1] - 6))).text("1,500 yd: fire opened");
      // the ship, to scale, when fire opened and at the hit, and her track
      const ship = (y, cls) => { const [x, yy] = P([0, y]); return svg.append("path").attr("d", hullPlan(BEAM / L)).attr("class", cls).attr("transform", `translate(${x},${yy}) scale(${L * k})`).attr("stroke-width", 1.4 / (L * k)); };
      const a0 = P([0, 0]), a1 = P([0, VS * s.t]);
      svg.append("line").attr("x1", a0[0]).attr("x2", a1[0]).attr("y1", a0[1]).attr("y2", a1[1]).attr("class", "stroke-us").attr("stroke-dasharray", "2 3");
      ship(0, "ghost-us"); ship(VS * s.t, "fill-us");
      svg.append("text").attr("class", "mk-label small").attr("x", a0[0] - 12).attr("y", a0[1] + 4).attr("text-anchor", "end").text("Haynsworth when fire opened");
      svg.append("text").attr("class", "mk-label").attr("x", a1[0] - 12).attr("y", a1[1] - 14).attr("text-anchor", "end").text(`at the hit, ${Math.round(VS * s.t).toLocaleString()} ft on`);
      // the plane's path, time ticks every 5 s
      svg.append("path").attr("class", "jpath").attr("d", d3.line()(pts.map(q => P(q.p))));
      for (let t = 5; t < s.t; t += 5) {
        const q = pts.reduce((b, x) => Math.abs(x.t - t) < Math.abs(b.t - t) ? x : b), [x, y] = P(q.p);
        svg.append("circle").attr("cx", x).attr("cy", y).attr("r", 2.6).attr("class", "tick-dot");
        svg.append("text").attr("class", "tick-lab").attr("x", x + 6).attr("y", y - 5).text(t + " s");
      }
      // aircraft, enlarged so they can be seen (true size is the ship's scale)
      const ENL = 4, sp = AIRCRAFT.judy.span * k * ENL;
      const hdgAt = (p, q) => Math.atan2(q[0] - p[0], q[1] - p[1]) * 180 / Math.PI;
      const s0 = P(s.P0); planeAt(svg, "judy", s0, hdgAt(pts[0].p, pts[1].p), sp, "fill-jp");
      svg.append("text").attr("class", "mk-label small").attr("x", s0[0] + 14).attr("y", s0[1] + 4).text("0 s, 150 ft, heading away");
      const last = pts[pts.length - 6], lp = P(last.p); planeAt(svg, "judy", lp, hdgAt(last.p, s.Hp), sp, "fill-jp");
      if (bomb) {
        const [bx, by] = P(bomb.p);
        svg.append("path").attr("d", `M${bx - 7},${by}Q${bx - 3},${by - 10} ${bx},${by - 2}Q${bx + 3},${by - 10} ${bx + 7},${by}`).attr("class", "stroke-jp").attr("fill", "none").attr("stroke-width", 1.4);
        svg.append("text").attr("class", "mk-label small").attr("x", bx + 10).attr("y", by + 14).text("1,000 yd off: about where the bomb fell");
      }
      const hp = P(s.Hp);
      svg.append("circle").attr("cx", hp[0]).attr("cy", hp[1]).attr("r", 5).attr("class", "fill-hit");
      svg.append("text").attr("class", "mk-label").attr("x", hp[0] + 9).attr("y", hp[1] + 18).text(`hit at ${Math.round(s.t)} s, starboard, frame ~${HIT_FRAME}`);
      // scale bar and heading
      const sb0 = [16, H - 18], sbl = 3000 * k;
      svg.append("line").attr("x1", sb0[0]).attr("x2", sb0[0] + sbl).attr("y1", sb0[1]).attr("y2", sb0[1]).attr("stroke", "var(--ink-2)").attr("stroke-width", 2);
      svg.append("text").attr("class", "tick-lab").attr("x", sb0[0]).attr("y", sb0[1] - 6).text("1,000 yd (3,000 ft)");
      svg.append("text").attr("class", "tick-lab").attr("x", W - 16).attr("y", 18).attr("text-anchor", "end").text(`ship's heading 020° is up · grid 1,000 ft · aircraft drawn ×${ENL}`);
      read.html(`<span>Turn radius <b>${Math.round(s.r).toLocaleString()} ft</b></span><span>Fire opened to hit <b>${Math.round(s.t)} s</b></span><span>Ship's advance <b>${Math.round(VS * s.t).toLocaleString()} ft</b> (${(VS * s.t / L).toFixed(1)} ship lengths)</span><span>Run in, straight <b>${Math.round(s.straight).toLocaleString()} ft</b></span>`);
    }
    Object.values(ui).forEach(el => el.addEventListener("input", draw));
    draw();
    note(h, `Recorded: course 020°, 25 knots (war diary); fire opened at 1,500 yards with the plane at 150 ft heading away; it turned to starboard; the bomb fell about 1,000 yards abeam; it hit the starboard side abaft the bridge banked 45° (action report p. 3); 100 ft and 300+ knots (Irons). Assumed: the plane's bearing from the ship when fire opened; a level turn at constant speed and bank (a real "wing over" climbs and slows at the top, which tightens it); a straight run from the end of the turn to the hit; the hit at frame ${HIT_FRAME}, within the frames the damage report names. The bomb mark is where the path is 1,000 yards from the ship coming back in; the bomb carried forward some distance after release, and the report doesn't say which side it fell on. Altitude isn't modelled here.`);
  }

  // ---------- where she was hit: the damage profile by frame
  function damage(host) {
    const s = SHIPS.sumner, L = s.length, W = 1000, pad = 40, k = (W - 2 * pad) / L, H = 260, wl = 170;
    const h = d3.select(host);
    const svg = h.append("div").attr("class", "card damage").append("svg").attr("class", "wide").attr("viewBox", `0 0 ${W} ${H}`)
      .attr("role", "img").attr("aria-label", "Profile of a Sumner-class destroyer with the damaged frames marked");
    const defs = svg.append("defs");
    defs.append("pattern").attr("id", "hp-hatch-fire").attr("patternUnits", "userSpaceOnUse").attr("width", 5).attr("height", 5).attr("patternTransform", "rotate(45)")
      .append("line").attr("x1", 0).attr("y1", 0).attr("x2", 0).attr("y2", 5).attr("class", "stroke-hit").attr("stroke-width", 1.6);
    const X = ft => pad + ft * k, Y = ft => wl - ft * k;
    const band = [FRAME(88), FRAME(65)];
    svg.append("rect").attr("x", X(band[0])).attr("y", Y(48)).attr("width", (band[1] - band[0]) * k).attr("height", (48 - 13) * k).attr("class", "dmg").attr("opacity", 0.9);
    svg.append("path").attr("d", s.d).attr("class", "sil").attr("transform", `translate(${pad},${wl}) scale(${k})`);
    svg.append("rect").attr("x", X(band[0])).attr("y", Y(48)).attr("width", (band[1] - band[0]) * k).attr("height", (48 - 13) * k).attr("fill", "url(#hp-hatch-fire)").attr("stroke", "var(--hit)").attr("stroke-width", 1.5);
    svg.append("line").attr("x1", X(0)).attr("x2", X(L)).attr("y1", wl).attr("y2", wl).attr("stroke", "var(--ink-3)");
    for (let f = 0; f <= 210; f += 10) {
      const x = X(FRAME(f)); if (x < pad - 1) continue;
      svg.append("line").attr("class", "frame-tick").attr("x1", x).attr("x2", x).attr("y1", wl + 4).attr("y2", wl + (f % 50 ? 9 : 14));
      if (f % 20 === 0 || f === 65 || f === 88) svg.append("text").attr("class", "frame-lab").attr("x", x).attr("y", wl + 26).attr("text-anchor", "middle").text(f);
    }
    [65, 88].forEach(f => svg.append("text").attr("class", "frame-lab").attr("x", X(FRAME(f))).attr("y", wl + 40).attr("text-anchor", "middle").style("fill", "var(--hit)").text("fr. " + f));
    svg.append("text").attr("class", "frame-lab").attr("x", X(L)).attr("y", wl + 56).attr("text-anchor", "end").text("frames from the FP, 21 in apart (BuShips plans)");
    const m41 = [X(FRAME(90)), Y(27)];
    svg.append("circle").attr("cx", m41[0]).attr("cy", m41[1]).attr("r", 9).attr("fill", "var(--hit)").attr("stroke", "var(--surface)").attr("stroke-width", 2);
    const call = (x, y, tx, ty, lines, bold) => { svg.append("path").attr("class", "leader").attr("d", `M${x},${y}L${tx},${ty + 4}`); lines.forEach((l, i) => svg.append("text").attr("class", "callout" + (i === 0 && bold ? " b" : "")).attr("x", tx).attr("y", ty - (lines.length - 1 - i) * 15).attr("text-anchor", "middle").text(l)); };
    call(m41[0], m41[1] - 10, m41[0] - 110, 40, ["Mount 41, twin 40 mm (starboard)", "\"wrecked\""], true);
    call(X((band[0] + band[1]) / 2) + 40, Y(40), X((band[0] + band[1]) / 2) + 120, 30, ["Frames 65-88: radio transmitter room,", "Main Radio, CIC and plot"], false);
    call(X(FRAME(78)), Y(15), X(FRAME(78)) - 20, H - 6, ["Starboard bulwark, frames 70-79, destroyed"], false);
    svg.append("text").attr("class", "callout").attr("x", X(L)).attr("y", 16).attr("text-anchor", "end").text("Bow →");
    note(h, `Profile: Sumner class, drawn to ONI 54-D (${s.plate}). Seen from starboard. Frames are 21 in apart, numbered aft from frame 0 at the forward perpendicular (Sumner booklet of general plans, 1968; DD 692 class general arrangement, 1947). On the 1947 plan's first level, frames 65-88 hold the captain's and executive officer's cabins, CIC (about frames 72-79), the chart and coding rooms, and the forward end of the radio transmitter room (starboard) and Radio Central (port), which run aft beside the forward uptake to about frame 92: the spaces the action report names. Mount 41 is drawn on the starboard platform beside the forward stack (about frames 87-93 on the 1947 plan), where Sumners carried twin 40 mm mounts 41 and 42; Haynsworth's own plan wasn't found, so its frame is the class arrangement, not hers. The ONI drawing is a recognition outline, so its stack and bridge sit a few feet off the plan.`);
  }

  // ---------- TG 58.3 and its pickets, as named in the 6 April records
  function oob(host) {
    const ships = [
      ["sumner", "Haynsworth (DD-700)", "Picket #1, 060° 12 mi. Hit 1250. With her, in DesDiv 123: English, Charles S. Sperry, Ault (squadron flagship), Waldron (took station #1 after the hit). Pickets #2X and #12: J. W. Weeks, Walker"],
      ["essex", "Essex, Bunker Hill, Hancock", "Fleet carriers. Essex's fighters shot down the Judys at 1140 and 1159; Bunker Hill's Marine Corsairs (VMF-221) lost Lt. Carpenter"],
      ["independence", "Cabot (CVL-28)", "Light carrier. Bombed at 1226 (missed); radar clipped by a suicide Zeke at 1302"],
      ["southdakota", "South Dakota (BB-57)", "1200 fix 26-41-45N 129-25-30E, used here for the formation centre. Took Haynsworth's wounded; five died aboard"],
      ["northcarolina", "North Carolina, Washington", "Battleships. North Carolina hit by a friendly 5-inch shell at 1305; Washington shot down a suicide Zeke at 1302"],
      ["cleveland", "Astoria (CL-90)", "Light cruiser. Her AA report calls the 1226 Judy \"tentatively ... a Zeke\""],
    ];
    const maxL = 885, grid = d3.select(host).append("div").attr("class", "hp-oob");
    ships.forEach(([k, nm, kd]) => {
      const s = SHIPS[k], w = 240, sc = w / maxL, h = 150 * sc + 6;
      const p = grid.append("div").attr("class", "hp-plate");
      p.append("svg").attr("viewBox", `0 ${-150 * sc - 2} ${w} ${h}`).attr("role", "img").attr("aria-label", s.name)
        .append("path").attr("d", s.d).attr("class", "sil").attr("transform", `scale(${sc})`);
      p.append("div").attr("class", "nm").text(nm);
      p.append("div").attr("class", "kd").text(s.name + ". " + kd);
    });
    grid.append("div").attr("class", "kd").style("grid-column", "1 / -1").text("All drawn to one scale from the ONI recognition plates' printed lengths and heights. The group had more ships than the records read here name; only those named are shown.");
  }

  // ---------- the aircraft, from the recognition plates
  function aircraft(host) {
    const ah = d3.select(host).append("div").attr("class", "hp-air");
    [["judy", "Haynsworth's attacker, as her crew identified it. The 210th Air Group flew 9 Model 33s and 2 Model 12s that morning"],
     ["zeke", "About 30 bomb-carrying Zeros went at TF 58 with the Suisei. A Zeke 52 has the same two-row radial engine type and Type 97 guns"],
     ["corsair", "Two Corsairs were on the Judy's tail as it came out of the cloud"],
     ["dinah", "The group's CAP splashed a Dinah at 1056, 29 miles out on 330° (Essex chronology, p. 34). The model isn't recorded; this is the plate's Dinah 43"]].forEach(([k, kd]) => {
      const a = AIRCRAFT[k], sc = a.span / 41;
      const p = ah.append("div").attr("class", "hp-plate");
      const svg = p.append("svg").attr("viewBox", "0 0 230 110").attr("role", "img").attr("aria-label", a.name);
      svg.append("path").attr("d", a.plan.d).attr("class", "sil").attr("transform", `translate(${56 - 50 * sc * 0.9},${4}) scale(${0.9 * sc})`);
      if (a.profile) svg.append("path").attr("d", a.profile.d).attr("class", "sil").attr("transform", `translate(${118},${44}) scale(${0.88 * a.length / 33.6})`);
      p.append("div").attr("class", "nm").text(a.name + " · " + a.type);
      p.append("div").attr("class", "kd").text(`${a.dims} (as printed on the plate). ${kd}. Silhouette: ${a.source}.`);
    });
  }

  return [
    { id: "sequence", heading: "1245 to 1250: the attack, as the action report tells it",
      intro: "Haynsworth's action report (9 April 1945, p. 3) describes the last five minutes in order but gives only two times, 1245 and 1250. These panels follow its wording. They are schematic: the ship's heading (020°) and the directions are from the report, but the distances are not to scale and the aircraft's exact paths are not recorded.",
      mount: sequence },
    { id: "scale100", heading: "To scale: 100 feet",
      intro: "Irons has the Judy coming in at 100 ft and over 300 knots; the action report has it at 150 ft when the ship opened fire at 1,500 yards. Here are both heights beside Haynsworth, everything in feet at one scale, seen from her starboard beam, the side it hit. Head-on, as the starboard 40 mm crews saw it, the plane is drawn over the frame where it struck.",
      mount: scale100 },
    { id: "path", heading: "To scale: an estimated path for the last half-minute",
      intro: "Seen from above, to scale. What is recorded: the ship on 020° at 25 knots; the Judy heading away from her when she opened fire at 1,500 yards; its turn to starboard; the bomb falling about 1,000 yards abeam; the hit on her starboard side abaft the bridge, wings banked 45°. What isn't: where the plane was relative to the ship, how fast it turned, and how tightly. Those are the controls below, and the path follows from them: a turn's radius is fixed by speed and bank (r = v² / g·tan bank).",
      mount: path },
    { id: "damage", heading: "Where she was hit",
      intro: "The damage report (airmailgram 090010, action report pp. 7-9) and the war diary locate the hit by frame number: frames 65-88 of the main deckhouse, the radio transmitter room, Main Radio and CIC; the starboard bulwark at frames 70-79 \"completely destroyed\"; the twin 40 mm mount 41 \"wrecked\".",
      mount: damage },
    { id: "oob", heading: "TG 58.3 and its pickets, as named in the 6 April records", intro: "", mount: oob },
    { id: "aircraft", heading: "The aircraft", intro: "", mount: aircraft },
  ];
})();
