// The Torpedo Data Computer Mark 3's two faces on tdc.html (tdc-page.js), turning with an attack's clock.
// Drawing only: the values are engage.js's tdcAt. The layout and every dial's name are from OP 1056's photographs
// (Fig. 98, the Position Keeper, p. 107; Fig. 102, the Angle Solver, p. 111), each scale from its appendix (pp. 267-270),
// what the Target and Own Ship dials read from pp. 72-73, the Distance to Track indicator from Fig. 38 (p. 47). Each dial is
// an engraved disc turning under a fixed index at the top (p. 111): a disc is drawn once and turned to its value. The
// lettering is drawn plainly, in the kit's type: the scans don't show the engraving finely enough to copy.
const TDC = (() => {
  const NS = "http://www.w3.org/2000/svg", rad = d => d * Math.PI / 180;
  const el = (parent, tag, attrs = {}, text) => {
    const e = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
    if (text != null) e.textContent = text;
    parent.appendChild(e); return e;
  };
  const turn = (g, cx, cy, deg) => g.setAttribute("transform", `rotate(${-deg} ${cx} ${cy})`);
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const pad3 = v => String(Math.round(((v % 360) + 360) % 360) % 360).padStart(3, "0");

  // a scale on a disc at value 0: v lies v / perTurn of a turn clockwise from the index
  function scale(g, cx, cy, r, { min, max, perTurn, minor, major, label = v => v, size = 9.5, len = [4, 8], mod }) {
    const n = Math.round((max - min) / minor);
    for (let i = 0; i <= n; i++) {
      const v = min + i * minor;
      if (mod && v >= min + mod - 1e-9) break;
      const a = v / perTurn * 360, isMaj = Math.abs(v / major - Math.round(v / major)) < 1e-6, L = isMaj ? len[1] : len[0];
      const s = Math.sin(rad(a)), c = Math.cos(rad(a));
      el(g, "line", { x1: cx + s * r, y1: cy - c * r, x2: cx + s * (r - L), y2: cy - c * (r - L), class: isMaj ? "tdc-maj" : "tdc-min" });
      const t = isMaj ? label(v) : "";
      if (t !== "") {
        const rt = r - L - size * 0.85, x = cx + s * rt, y = cy - c * rt;
        el(g, "text", { x, y, "font-size": size, class: "tdc-num", transform: `rotate(${a} ${x} ${y})` }, t);
      }
    }
  }
  const disc = (g, cx, cy, r, cls = "tdc-disc") => el(g, "circle", { cx, cy, r, class: cls });
  const index = (g, cx, cy, r) => el(g, "path", { d: `M${cx - 5} ${cy - r - 9}L${cx + 5} ${cy - r - 9}L${cx} ${cy - r + 1}Z`, class: "tdc-index" });
  const hub = (g, cx, cy, r = 8) => { el(g, "circle", { cx, cy, r, class: "tdc-hub" }); el(g, "circle", { cx, cy, r: 2.5, class: "tdc-pin" }); };
  const title = (g, x, y, t) => el(g, "text", { x, y, class: "tdc-title" }, t);
  // one dial: a disc with its scale, turned as a whole
  function dial(g, cx, cy, r, sc, name, ny) {
    disc(g, cx, cy, r); const rot = el(g, "g"); scale(rot, cx, cy, r - 3, sc); index(g, cx, cy, r); hub(g, cx, cy);
    if (name) title(g, cx, ny ?? cy + r + 17, name);
    return v => turn(rot, cx, cy, v / sc.perTurn * 360);
  }
  // a 1-speed dial and its 36-speed (10° a turn)
  function pair(g, x1, x2, y, r, name) {
    const a = dial(g, x1, y, r, { min: 0, max: 360, perTurn: 360, minor: 5, major: 10, mod: 360, label: v => v % 30 ? "" : pad3(v), size: 8.5 });
    const b = dial(g, x2, y, r, { min: 0, max: 10, perTurn: 10, minor: 1 / 6, major: 1, mod: 10, size: 9 });
    el(g, "line", { x1: x1 + r + 4, y1: y, x2: x2 - r - 4, y2: y, class: "tdc-link" });
    title(g, (x1 + x2) / 2, y + r + 17, name);
    return v => { a(v); b(((v % 10) + 10) % 10); };
  }
  // a ship's outline, bow up at the inner disc's zero
  function ship(g, cx, cy, len, letters) {
    const w = len * 0.2;
    el(g, "path", { d: `M${cx} ${cy - len / 2}C${cx + w} ${cy - len / 4} ${cx + w} ${cy + len / 3} ${cx + w * 0.7} ${cy + len / 2}L${cx - w * 0.7} ${cy + len / 2}C${cx - w} ${cy + len / 3} ${cx - w} ${cy - len / 4} ${cx} ${cy - len / 2}Z`, class: "tdc-ship" });
    if (letters) { el(g, "text", { x: cx + w * 1.9, y: cy, class: "tdc-sp" }, "S"); el(g, "text", { x: cx - w * 1.9, y: cy, class: "tdc-sp" }, "P"); }
  }
  // an arrow on an inner disc, read at one end (Own Ship: its head; Target: its tail)
  function arrow(g, cx, cy, r, byHead, cls) {
    const a = el(g, "g", { class: cls });
    el(a, "line", { x1: cx, y1: cy - r, x2: cx, y2: cy + r * 0.55 });
    if (byHead) el(a, "path", { d: `M${cx} ${cy - r}l-5 9l10 0Z` });
    else { el(a, "path", { d: `M${cx} ${cy + r * 0.55}l-5 -9l10 0Z` }); el(a, "path", { d: `M${cx - 5} ${cy - r + 8}L${cx} ${cy - r}L${cx + 5} ${cy - r + 8}`, fill: "none" }); }
    return v => turn(a, cx, cy, -v);
  }
  function counter(g, x, y, name, beside) {
    const cells = [0, 1, 2, 3].map(i => { el(g, "rect", { x: x + i * 17, y, width: 15, height: 20, rx: 2, class: "tdc-cell" });
      return el(g, "text", { x: x + i * 17 + 7.5, y: y + 11, class: "tdc-digit" }, "0"); });
    if (beside) el(g, "text", { x: x + 74, y: y + 15, class: "tdc-title", "text-anchor": "start", style: "text-anchor: start" }, name);
    else title(g, x + 33, y + 34, name);
    return v => { const s = String(clamp(Math.round(v / 2) * 2, 0, 9998)).padStart(4, "0"); cells.forEach((c, i) => { c.textContent = s[i]; }); };
  }
  function lamp(g, x, y, name, small) {
    el(g, "circle", { cx: x, cy: y, r: small ? 13 : 17, class: "tdc-socket" });
    const glow = el(g, "circle", { cx: x, cy: y, r: small ? 15 : 20, class: "tdc-glow" }), l = el(g, "circle", { cx: x, cy: y, r: small ? 8 : 10, class: "tdc-lamp" });
    title(g, x, y + (small ? 29 : 34), name);
    return on => { l.classList.toggle("on", !!on); glow.classList.toggle("on", !!on); };
  }
  function bezel(svg, w, h) {
    el(svg, "rect", { x: 6, y: 6, width: w - 12, height: h - 12, rx: 18, class: "tdc-bezel" });
    const nx = Math.round(w / 70), ny = Math.round(h / 70);
    for (let i = 0; i <= nx; i++) for (const y of [17, h - 17]) el(svg, "circle", { cx: 24 + i * (w - 48) / nx, cy: y, r: 4, class: "tdc-bolt" });
    for (let i = 1; i < ny; i++) for (const x of [17, w - 17]) el(svg, "circle", { cx: x, cy: i * h / ny, r: 4, class: "tdc-bolt" });
  }

  // a numbered key beside a dial, for the page's legend (create's `keys`)
  const keyAt = (g, x, y, n) => { const k = el(g, "g", { class: "tdc-key" }); el(k, "circle", { cx: x, cy: y, r: 10 }); el(k, "text", { x, y }, n); };

  function create(pk, as, { keys = false } = {}) {
    const set = {};
    // ---- the Position Keeper (Fig. 98): 640 × 800
    pk.setAttribute("viewBox", "0 0 640 800"); pk.innerHTML = ""; bezel(pk, 640, 800);
    el(pk, "rect", { x: 46, y: 46, width: 548, height: 708, rx: 10, class: "tdc-plate" });
    let g = el(pk, "g");
    const C = [150, 320, 490], R = [158, 318, 500, 664];
    // target speed: 44/45-speed, about 41 knots a turn, stopped at 0 and 40; every half knot, numbered every knot
    set.targetSpeed = dial(g, C[0], R[0], 58, { min: 0, max: 40, perTurn: 41, minor: 0.5, major: 1, label: v => v % 5 ? "" : v, size: 8.5 }, "target speed");
    set.asRange = counter(g, C[0] - 33, R[0] + 82, "angle solver range");
    set.generating = lamp(g, C[0], R[1] + 30, "generating");
    // the Target dial (30): the ring reads true target bearing less 180° at the index, the inner disc the angle on the bow;
    // its zero (the target's bow) reads target course on the ring; the arrow tails read the track angles
    const tR = 68, tr = 48;
    disc(g, C[1], R[0], tR); const tRing = el(g, "g");
    scale(tRing, C[1], R[0], tR - 3, { min: 0, max: 360, perTurn: 360, minor: 2, major: 10, mod: 360, label: v => v % 30 ? "" : v, size: 8 });
    const tIn = el(g, "g"); disc(tIn, C[1], R[0], tr, "tdc-inner");
    scale(tIn, C[1], R[0], tr - 2, { min: 0, max: 360, perTurn: 360, minor: 2, major: 10, mod: 360, label: v => v % 30 ? "" : (v <= 180 ? v : 360 - v), size: 7.5 });
    ship(tIn, C[1], R[0], 36, true);
    const tArrF = arrow(tIn, C[1], R[0], tr - 16, false, "tdc-arrow"), tArrA = arrow(tIn, C[1], R[0], tr - 16, false, "tdc-arrow aft");
    index(g, C[1], R[0], tR); hub(g, C[1], R[0], 6); title(g, C[1], R[0] - tR - 14, "target");
    set.target = (brg, aob, trkF, trkA) => { turn(tRing, C[1], R[0], brg - 180); turn(tIn, C[1], R[0], aob); tArrF(trkF); tArrA(trkA); };
    set.range = counter(g, C[1] - 33, R[0] + tR + 8, "range", true);   // its name beside it: the Own Ship dial's index is below
    // the Own Ship dial (12): the ring reads true target bearing, the inner disc relative target bearing; its zero (own bow)
    // reads own course on the ring; the arrowheads read the gyro angles
    const oy = R[1] + 20;
    disc(g, C[1], oy, tR); const oRing = el(g, "g");
    scale(oRing, C[1], oy, tR - 3, { min: 0, max: 360, perTurn: 360, minor: 2, major: 10, mod: 360, label: v => v % 30 ? "" : v, size: 8 });
    const oIn = el(g, "g"); disc(oIn, C[1], oy, tr, "tdc-inner");
    scale(oIn, C[1], oy, tr - 2, { min: 0, max: 360, perTurn: 360, minor: 2, major: 10, mod: 360, label: v => v % 30 ? "" : v, size: 7.5 });
    ship(oIn, C[1], oy, 36, false);
    const oArrF = arrow(oIn, C[1], oy, tr - 16, true, "tdc-arrow"), oArrA = arrow(oIn, C[1], oy, tr - 16, true, "tdc-arrow aft");
    index(g, C[1], oy, tR); hub(g, C[1], oy, 6); title(g, C[1], oy + tR + 18, "own ship");
    set.ownShip = (brg, rel, gF, gA) => { turn(oRing, C[1], oy, brg); turn(oIn, C[1], oy, rel); oArrF(gF); oArrA(gA); };
    // distance to track (Fig. 38): an arm at the target's angle, its X at the range, read against lines 0-8 each side
    // (the lines' numbers taken as thousands of yards: inferred from the range stop at 8,000 yards, p. 270)
    const dx = C[2], dy = R[0] - 6, U = 6.25;   // U: one thousand yards
    el(g, "rect", { x: dx - 60, y: dy - 56, width: 120, height: 112, rx: 12, class: "tdc-disc" });
    for (let i = -16; i <= 16; i++) el(g, "line", { x1: dx + i * U / 2, y1: dy - 46, x2: dx + i * U / 2, y2: dy + 40, class: i % 2 ? "tdc-min" : "tdc-maj" });
    for (let n = 0; n <= 8; n += 2) for (const sgn of n ? [-1, 1] : [1]) el(g, "text", { x: dx + sgn * n * U, y: dy + 49, "font-size": 7, class: "tdc-num" }, n);
    const arm = el(g, "g"); el(arm, "line", { x1: dx, y1: dy + 40, x2: dx, y2: dy - 46, class: "tdc-arm" });
    const nut = el(arm, "text", { x: dx, y: dy, class: "tdc-x" }, "×");
    hub(g, dx, dy, 5); title(g, dx, dy + 72, "distance to track");
    set.dtt = (aob, range) => { turn(arm, dx, dy, -aob); nut.setAttribute("y", dy - clamp(range / 1000, 0, 8) * U); };
    // time: outer 60 minutes a turn, inner 60 seconds
    disc(g, C[2], oy, 58); const tm = el(g, "g");
    scale(tm, C[2], oy, 55, { min: 0, max: 60, perTurn: 60, minor: 1, major: 5, mod: 60, size: 8.5 });
    const ts = el(g, "g"); disc(ts, C[2], oy, 36, "tdc-inner");
    scale(ts, C[2], oy, 34, { min: 0, max: 60, perTurn: 60, minor: 1, major: 5, mod: 60, size: 7, len: [3, 6] });
    index(g, C[2], oy, 58); hub(g, C[2], oy, 6); title(g, C[2], oy + 75, "time");
    set.time = sec => { turn(tm, C[2], oy, sec / 60 / 60 * 360); turn(ts, C[2], oy, (sec % 60) / 60 * 360); };
    // target length: 1500 feet a turn, 300-1000
    set.length = dial(g, C[0], R[2], 58, { min: 300, max: 1000, perTurn: 1500, minor: 20, major: 100, label: v => v % 200 === 100 ? v : "", size: 8 }, "target length");
    set.relBearing = pair(g, C[1], C[2], R[2], 58, "relative target bearing");
    // own speed: graduated to the ship's log (its numbers here assumed: 0-20 knots)
    set.ownSpeed = dial(g, C[0], R[3], 58, { min: 0, max: 20, perTurn: 24, minor: 0.5, major: 1, label: v => v % 5 ? "" : v, size: 8.5 }, "own speed");
    set.ownCourse = pair(g, C[1], C[2], R[3], 58, "own course");
    // the keys, in the legend's order: down the left column, then the middle and right, row by row
    if (keys) [[C[0] - 66, R[0] - 52], [C[0] - 52, R[0] + 92], [C[0] - 30, R[1] + 6], [C[1] - 76, R[0] - 60], [C[1] - 47, R[0] + tR + 18],
      [dx - 66, dy - 52], [C[1] - 76, oy - 60], [C[2] - 66, oy - 52], [C[0] - 66, R[2] - 52], [C[1] - 66, R[2] - 52],
      [C[0] - 66, R[3] - 52], [C[1] - 66, R[3] - 52]].forEach(([x, y], i) => keyAt(pk, x, y, i + 1));

    // ---- the Angle Solver (Fig. 102): 760 × 520, after and forward
    as.setAttribute("viewBox", "0 0 760 520"); as.innerHTML = ""; bezel(as, 760, 520);
    el(as, "rect", { x: 40, y: 44, width: 680, height: 430, rx: 10, class: "tdc-plate" });
    g = el(as, "g");
    el(g, "line", { x1: 380, y1: 58, x2: 380, y2: 460, class: "tdc-rule" });
    const side = (x0, name) => {
      const k = el(g, "g");
      el(k, "text", { x: x0 + 170, y: 80, class: "tdc-side" }, name);
      const gyro = pair(k, x0 + 85, x0 + 255, 160, 56, "gyro angle order");
      const ok = lamp(k, x0 + 170, 262, "correct solution", true);
      const off = dial(k, x0 + 85, 370, 48, { min: -35, max: 35, perTurn: 72, minor: 1, major: 5, label: v => v === 0 ? "0" : (v % 10 ? "" : Math.abs(v) + (v > 0 ? "R" : "L")), size: 8 }, "offset angle", 436);
      const run = dial(k, x0 + 255, 370, 48, { min: 300, max: 6800, perTurn: 7111, minor: 100, major: 500, label: v => v % 1000 ? "" : v / 1000 + "k", size: 8 }, "torpedo run", 436);
      return (s, solved) => { k.classList.toggle("idle", !s);
        if (s) { gyro(s.gyroOrder); off(clamp(s.offset, -35, 35)); run(clamp(s.run, 300, 6800)); } ok(solved && s); };
    };
    set.aft = side(40, "aft"); set.fwd = side(380, "fwd.");
    // depth-speed: torpedo speed (25-60 knots, 40 a turn) under the transparent depth-set dial (10-50 feet)
    const cx = 380, cy = 268;
    el(g, "circle", { cx, cy, r: 46, class: "tdc-disc" }); const spd = el(g, "g");
    scale(spd, cx, cy, 43, { min: 25, max: 60, perTurn: 40, minor: 1, major: 5, size: 8 });
    const dep = el(g, "g"); el(dep, "circle", { cx, cy, r: 26, class: "tdc-glass" });
    scale(dep, cx, cy, 24, { min: 10, max: 50, perTurn: 60, minor: 5, major: 10, size: 6.5, len: [2, 4] });
    index(g, cx, cy, 46); hub(g, cx, cy, 5);
    el(g, "rect", { x: cx - 42, y: cy + 52, width: 84, height: 16, class: "tdc-plate" }); title(g, cx, cy + 64, "depth-speed");
    if (keys) [[x0k => x0k + 85 - 64, 110], [x0k => x0k + 170 - 36, 262], [x0k => x0k + 85 + 46, 326], [x0k => x0k + 255 + 46, 326]]
      .forEach(([fx, y], i) => { for (const x0k of [40, 380]) keyAt(as, fx(x0k), y, i + 1); });
    if (keys) keyAt(as, cx - 50, cy - 44, 5);
    set.depthSpeed = (kn, ft) => { turn(spd, cx, cy, kn / 40 * 360); turn(dep, cx, cy, clamp(ft, 10, 50) / 60 * 360); };

    return {
      // d: engage.js's tdcAt; o: { time (seconds on the clock), length (the target's assumed feet) }
      set(d, o) {
        set.ownCourse(d.ownCourse); set.ownSpeed(clamp(d.ownSpeed, 0, 20)); set.generating(d.generating);
        set.length(clamp(o.length, 300, 1000)); set.time(Math.max(0, o.time));
        if (!d.generating) { set.fwd(null, false); set.aft(null, false); return; }
        set.targetSpeed(clamp(d.targetSpeed, 0, 40)); set.asRange(d.range); set.range(d.range);
        set.relBearing(d.relBearing); set.dtt(d.aob, d.range);
        const sgn = d.side === "P" ? -1 : 1, trk = d.solved ? sgn * d.track : 0;
        set.target(d.trueBearing, d.aob, trk, trk);
        set.ownShip(d.trueBearing, d.relBearing, d.fwd ? d.fwd.gyroOrder : 0, d.aft ? d.aft.gyroOrder : 0);
        set.fwd(d.fwd && d.fwd.tube != null ? d.fwd : null, d.solved); set.aft(d.aft && d.aft.tube != null ? d.aft : null, d.solved);
        set.depthSpeed(d.torpedoSpeed, d.depth ?? 10);
      },
    };
  }
  return { create };
})();
