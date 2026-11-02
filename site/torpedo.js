// torpedo.html: the attack triangle you can set, and BANG's Attack 1 worked from her sheet. Every number is computed
// by engage.js (fireControl, attackSheet); this file only sets up the inputs and draws.
(() => {
  const $ = id => document.getElementById(id);
  const pad3 = a => String(Math.round(((a % 360) + 360) % 360)).padStart(3, "0");
  const f1 = x => x.toFixed(1), fyd = x => Math.round(x).toLocaleString("en-US");

  // ---------- the triangle. A one-torpedo sheet, made up from the inputs, run through Engage.attackSheet: the boat at
  // the origin on course 000, still, the target dead ahead. The gyro angle is found by stepping it until the angle on
  // the bow fireControl gives back is the one set.
  const seg = id => { const el = $(id); el.addEventListener("click", e => { const b = e.target.closest("button"); if (!b) return;
    el.querySelectorAll("button").forEach(x => x.setAttribute("aria-pressed", x === b)); draw(); });
    return () => el.querySelector("[aria-pressed=true]").dataset.v; };
  const side = seg("side-seg"), power = seg("power-seg");
  ["speed", "aob", "range", "own"].forEach(id => $(id).addEventListener("input", draw));

  function solve(speed, aob, sideV, range, knots, own = 0) {
    const signed = sideV === "S" ? aob : -aob;
    // AOB = bearing of the boat from the target, from the target's head; the target bears 000 from the boat
    const targetCourse = (180 - signed + 360) % 360;
    let gyro = 0;
    for (let i = 0; i < 60; i++) {
      const fc = Engage.fireControl({ ownCourse: 0, gyro, targetCourse, targetSpeed: speed, torpedoSpeed: knots });
      const err = signed - fc.aob;   // fireControl's aob is signed: starboard +, port -
      gyro = gyro + err;
      if (Math.abs(err) < 1e-6) break;
    }
    gyro = ((gyro % 360) + 360) % 360;
    const fc = Engage.fireControl({ ownCourse: 0, gyro, targetCourse, targetSpeed: speed, torpedoSpeed: knots });
    const row = { time: "1200", tube: "1", own_course: "000", own_speed: String(own), own_depth: "60", target_course: pad3(targetCourse),
      target_speed: String(speed), target_range: String(range), track: "", gyro: gyro.toFixed(3), power: String(knots),
      hit: "Hit", torpedo: "14", since_first: "0", offset: "" };
    const A = Engage.attackSheet([row], { length: 1, beam: 1 });   // a point target: the run is to the intercept itself
    return { targetCourse, gyro, fc, A, t: A.torps[0], T: A.targets[0] };
  }

  const svg = d3.select("#tri");
  function draw() {
    const speed = +$("speed").value, aob = +$("aob").value, range = +$("range").value, sv = side(), knots = +power(), own = +$("own").value;
    $("o-own").textContent = own ? `${own} kn` : "stopped";
    $("o-speed").textContent = `${speed} kn`; $("o-aob").textContent = `${aob}° ${sv === "S" ? "starboard" : "port"}`;
    $("o-range").textContent = `${fyd(range)} yd`;
    const S = solve(speed, aob, sv, range, knots, own), t = S.t, T = S.T;
    const boatAtHit = S.A.ownAt(t.run).p;   // where the boat is when the torpedo arrives (engage.js: steady course and speed)
    // drawn at the width it is shown, so the labels keep their size on a phone
    const W = Math.round(Math.min(720, Math.max(320, svg.node().parentNode.clientWidth || 720))), H = Math.round(W < 500 ? W * 1.05 : W * 0.72), m = W < 500 ? 70 : 40;
    svg.attr("viewBox", `0 0 ${W} ${H}`);
    // the intercept: where the torpedo reaches the target
    const hit = [t.from[0] + t.v[0] * t.run, t.from[1] + t.v[1] * t.run];
    const pts = [[0, 0], T.p0, hit, boatAtHit];
    const xs = pts.map(p => p[0]), ys = pts.map(p => p[1]);
    const span = Math.max(d3.max(xs) - d3.min(xs), d3.max(ys) - d3.min(ys), 600) * 1.15;
    const k = Math.min((W - 2 * m) / span, (H - 2 * m) / span);
    const cx = (d3.max(xs) + d3.min(xs)) / 2, cy = (d3.max(ys) + d3.min(ys)) / 2;
    const P = p => [W / 2 + (p[0] - cx) * k, H / 2 - (p[1] - cy) * k];
    svg.selectAll("*").remove();
    // range rings from the boat, every 500 yards
    const B = P([0, 0]);
    for (let r = 500; r <= span * 1.5; r += 500) {
      svg.append("circle").attr("class", "grid-ring").attr("cx", B[0]).attr("cy", B[1]).attr("r", r * k);
      if (r % 1000 === 0) svg.append("text").attr("class", "ring-label").attr("x", B[0] + r * k * 0.87 + 3).attr("y", B[1] - r * k * 0.5 - 3).text(`${fyd(r)} yd`);
    }
    const line = (a, b, cls) => svg.append("line").attr("class", cls).attr("x1", P(a)[0]).attr("y1", P(a)[1]).attr("x2", P(b)[0]).attr("y2", P(b)[1]);
    line([0, 0], T.p0, "sight");
    line(T.p0, hit, "tgt-path");
    line([0, 0], hit, "torp");
    if (own) { line([0, 0], boatAtHit, "torp-pre"); const Bh = P(boatAtHit);
      svg.append("path").attr("class", "boat").attr("opacity", 0.45).attr("transform", `translate(${Bh[0]},${Bh[1]})`).attr("d", "M0,-11 L6,6 L0,3 L-6,6 Z"); }
    // the angles: at the boat (lead), at the target (angle on the bow), at the intercept (180 - track)
    const ang = (o, a, b, label, r = 46) => {
      const O = P(o), A = P(a), Bp = P(b);
      const a1 = Math.atan2(A[1] - O[1], A[0] - O[0]), a2 = Math.atan2(Bp[1] - O[1], Bp[0] - O[0]);
      let d = a2 - a1; while (d > Math.PI) d -= 2 * Math.PI; while (d < -Math.PI) d += 2 * Math.PI;
      if (Math.abs(d) < 0.01) return;
      const arc = d3.path(); arc.arc(O[0], O[1], r, a1, a1 + d, d < 0);
      svg.append("path").attr("class", "arc").attr("d", arc.toString());
      // the boat's label inside its angle; the others outside the triangle, away from its centre
      const C = [(B[0] + P(T.p0)[0] + P(hit)[0]) / 3, (B[1] + P(T.p0)[1] + P(hit)[1]) / 3];
      const mid = a1 + d / 2, outside = o[0] !== 0 || o[1] !== 0;
      let ux = Math.cos(mid), uy = Math.sin(mid), dist = r + 16;
      if (outside) { const vx = O[0] - C[0], vy = O[1] - C[1], n = Math.hypot(vx, vy) || 1; ux = vx / n; uy = vy / n; dist = 18; }
      svg.append("text").attr("class", "arc-label").attr("x", O[0] + ux * dist).attr("y", O[1] + uy * dist + 4)
        .attr("text-anchor", ux > 0.3 ? "start" : ux < -0.3 ? "end" : "middle").text(label);
    };
    const back = [T.p0[0] - Math.sin(S.targetCourse * Math.PI / 180) * 300, T.p0[1] - Math.cos(S.targetCourse * Math.PI / 180) * 300];
    ang([0, 0], T.p0, hit, `lead ${f1(Math.abs(S.fc.lead))}°`);
    const ahead = [T.p0[0] + Math.sin(S.targetCourse * Math.PI / 180) * 300, T.p0[1] + Math.cos(S.targetCourse * Math.PI / 180) * 300];
    ang(T.p0, ahead, [0, 0], `angle on the bow ${aob}°`, 34);
    ang(hit, back, [0, 0], `intercept: track ${f1(S.fc.track)}°${S.fc.side}`, 30);
    // the boat (heading up), the target at firing (a bar along its course), the intercept
    svg.append("path").attr("class", "boat").attr("transform", `translate(${B[0]},${B[1]})`).attr("d", "M0,-11 L6,6 L0,3 L-6,6 Z");
    const Tp = P(T.p0);
    svg.append("rect").attr("class", "tgt").attr("x", -16).attr("y", -5).attr("width", 32).attr("height", 10).attr("rx", 4)
      .attr("transform", `translate(${Tp[0]},${Tp[1]}) rotate(${S.targetCourse - 90})`);
    // keep every label inside the figure
    svg.selectAll("text.arc-label").each(function () { const b = this.getBBox(), x = +this.getAttribute("x");
      if (b.x < 4) this.setAttribute("x", x + 4 - b.x); else if (b.x + b.width > W - 4) this.setAttribute("x", x - (b.x + b.width - W + 4)); });
    const Hp = P(hit);
    svg.append("circle").attr("class", "hitpt").attr("cx", Hp[0]).attr("cy", Hp[1]).attr("r", 5);
    const g = S.gyro, gyroText = g < 0.05 || g > 359.95 ? "000 (straight)" : `${pad3(g)} (${g <= 180 ? f1(g) + "° right" : f1(360 - g) + "° left"})`;
    const limit = (g > 90 && g < 270) ? "beyond the Mark 14-1A's 90° right or left; a Mark 14-3A reached 160° (OP 635 pp. 13–14), or fire from the stern tubes" : "";
    const runOk = t.runYd > (knots === 46 ? 4500 : 9000) ? `longer than the ${knots === 46 ? "4,500" : "9,000"} yards OP 635 gives at ${knots} knots` : "";
    $("readout").innerHTML = [
      ["Gyro angle", gyroText], ["Track angle", `${f1(S.fc.track)}° ${S.fc.side}`], ["Lead angle", `${f1(Math.abs(S.fc.lead))}°`],
      ["Target course", `${pad3(S.targetCourse)}°`], ["Torpedo run", `${fyd(t.runYd)} yd`], ["Time of run", `${Math.round(t.run)} s`]
    ].map(([a, b]) => `<div><i>${a}</i><b>${b}</b></div>`).join("");
    // the working: the numbers going into the equations above (engage.js's results, shown against the formulas)
    const rad = d => d * Math.PI / 180, kk = speed / knots, L = Math.abs(S.fc.lead);
    const mth = x => `<math>${x}</math>`, n = x => `<mn>${x}</mn>`, o = x => `<mo>${x}</mo>`, sinm = "<mi>sin</mi><mo>&#x2061;</mo><mspace width='0.22em'/>";
    $("working").innerHTML = speed === 0 ? "A stopped target: no lead, and the gyro angle is the target's bearing." :
      `The working: ${mth(`<mi>k</mi>${o("=")}<mfrac>${n(speed)}${n(knots)}</mfrac>${o("=")}${n(kk.toFixed(3))}`)};
       ${mth(`${sinm}<mi>L</mi>${o("=")}${n(kk.toFixed(3))}${o("&#xD7;")}${sinm}${n(aob + "°")}${o("=")}${n((kk * Math.sin(rad(aob))).toFixed(3))}`)},
       so ${mth(`<mi>L</mi>${o("=")}${n(f1(L) + "°")}`)};
       ${mth(`<mi>TA</mi>${o("=")}${n(aob + "°")}${o("+")}${n(f1(L) + "°")}${o("=")}${n(f1(S.fc.track) + "°")}`)};
       ${mth(`<msub><mi>D</mi><mi>&#x3C4;</mi></msub>${o("=")}<mfrac><mrow>${n(fyd(range))}${o("&#xD7;")}${sinm}${n(aob + "°")}</mrow><mrow>${sinm}${n(f1(S.fc.track) + "°")}</mrow></mfrac>${o("=")}${n(fyd(t.runYd) + " yd")}`)}.`
      + (own ? ` While it runs, the boat makes ${fyd(Math.hypot(boatAtHit[0], boatAtHit[1]))} yards at ${own} knots; nothing above changes.` : "");
    const notes = [limit, runOk, t.runYd < 500 ? "under the doctrine's 500-yard minimum run (USF 25(A) p. 50)" : ""].filter(Boolean);
    $("tri-caption").textContent = `Own course 000, target bearing 000 at ${fyd(range)} yards, on course ${pad3(S.targetCourse)} at ${speed} knots; torpedo at ${knots} knots.`
      + (notes.length ? " Note: " + notes.join("; ") + "." : "") + " Advance, transfer and parallax are left out.";
  }
  draw();
  let rt; window.addEventListener("resize", () => { clearTimeout(rt); rt = setTimeout(draw, 150); });

  // ---------- BANG, Attack 1: the sheet's rows through Engage.attackSheet
  const PAGE = "https://catalog.archives.gov/id/74802746?objectPage=";
  d3.csv(RECORDS + "boats/ss-385-bang/patrol-1/attacks.csv").then(all => {
    const rows = all.filter(r => r.attack === "Attack 1");
    const A = Engage.attackSheet(rows, { length: 400, beam: 55 });
    const head = ["Tube", "Mark", "Fired (s)", "Gyro (typed)", "Torpedo course", "Track (typed)", "Track (worked)", "Aimed at", "Run (worked)", "At the aimed target (worked)", "Hit or miss (typed)"];
    const tb = d3.select("#sheet");
    tb.append("thead").append("tr").selectAll("th").data(head).join("th").text(d => d);
    const body = tb.append("tbody");
    A.torps.forEach(t => {
      const r = t.row, T = A.targets[t.target];
      const fc = Engage.fireControl({ ownCourse: +r.own_course, gyro: Engage.gyroOf(r.gyro), targetCourse: +r.target_course, targetSpeed: +r.target_speed, torpedoSpeed: t.knots });
      const tr = body.append("tr");
      [r.tube, r.torpedo, t.s, r.gyro, pad3(t.course), r.track, `${Math.round(fc.track)}${fc.side}`,
       `${r.target_draft === "10" ? "DD" : "AO"} ${fyd(+r.target_range)} yd`, `${fyd(t.runYd)} yd, ${Math.round(t.run)} s`,
       `${Math.floor((t.s + t.run) / 60)}m ${String(Math.round((t.s + t.run) % 60)).padStart(2, "0")}s`].forEach((v, i) =>
        tr.append("td").attr("class", [3, 5].includes(i) ? "mono" : null).text(v));
      tr.append("td").attr("class", "mono").text(r.hit).append("a").attr("href", PAGE + r.page.split("/p")[1]).text(" p" + r.page.split("/p")[1]);
    });
    const ao = A.torps.find(t => t.row.tube === "6"), dd = A.torps.find(t => t.row.tube === "2");
    const at = t => `${Math.floor((t.s + t.run) / 60)}m ${String(Math.round((t.s + t.run) % 60)).padStart(2, "0")}s`;
    $("sheet-check").innerHTML = `<p><b>The checks.</b> Every typed track agrees with own course 090 + gyro + 180 − target course 160, to within a
      degree (the two columns). The sheet's remarks time the explosions: "Torpedoes hit at 02m 10s; 02m 12s; and 02m 39s. after firing"
      (remarks, <a href="${PAGE}16">pp. 16–18</a>). Worked on the sheet's tanker solution, tube 6 (fired ${ao.s} s after the first) reaches the AO
      ${at(ao)} after the first torpedo: the third explosion, to within a second or so. Tubes 1–4 were aimed on the destroyer's
      solution at 1,800 yards, which they would have reached in about ${Math.round(dd.run)} s; the first two explosions came at about 130 s,
      which fits the AK in line beyond her, about 1,200 yards farther, where the boat saw the one hit (inferred: the sheet puts the AK
      at 3,000 yards and says "It is believed that the first two hits were in this AK", <a href="${PAGE}18">p18</a>).</p>`;
    $("sheet-assumed").textContent = "Worked by engage.js, assuming: " + A.assumed.join("; ") + ". OP 635 gives the Mark 14's and 23's high speed as 46 knots (pp. 13–14).";
  }).catch(e => { $("sheet-check").textContent = "The attack sheet could not be loaded: " + e.message; });
})();
