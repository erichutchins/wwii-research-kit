// tdc.html: the Torpedo Data Computer Mark 3's two faces (tdc.js, drawing only) through one attack, second by second,
// each dial keyed to a list that says what it is, what it reads now and where the value comes from. The attacks are
// every engagement's transcribed data sheets (records/engagements/index.json, each engagement.json's `sheets`, found and
// sized by observer.js's `attacks` and `targetsOf`); the values are engage.js's attackSheet and tdcAt, never redone here.
// The address: tdc.html?e=<engagement>&boat=<boat's id>&attack=<"Attack 1">; the page keeps it up to date.
(async () => {
  const E = Engage, esc = s => EV.esc(s);
  const pad3 = v => String(Math.round(((v % 360) + 360) % 360) % 360).padStart(3, "0");
  const side = v => `${Math.abs(Math.round(v))}° ${v >= 0 ? "starboard" : "port"}`;
  const lr = v => Math.abs(v) < 0.05 ? "0°" : `${Math.abs(v).toFixed(1).replace(/\.0$/, "")}° ${v > 0 ? "right" : "left"}`;
  const yd = v => `${Math.round(v).toLocaleString()} yd`;
  const $ = id => document.getElementById(id);
  const q = new URLSearchParams(location.search);

  const [index] = await Promise.all([fetch(RECORDS + "engagements/index.json").then(r => r.json()), SILHOUETTES.catch(() => null)]);
  const engs = index.filter(x => x.sheets);
  const sel = $("eng");
  sel.innerHTML = engs.map(x => `<option value="${esc(x.id)}">${esc(x.title)}</option>`).join("");
  const tdc = TDC.create($("tdc-pk"), $("tdc-as"), { keys: true });
  const slider = $("t"), playBtn = $("play");
  let D = null, list = [], cur = null, A = null, s = 0, timer = null;
  const nameOf = a => (D.participants.find(p => p.id === a) || {}).name || a;

  async function open(id, boat, attack) {
    stop();
    if (!engs.some(x => x.id === id)) id = engs[0].id;
    sel.value = id;
    D = await fetch(`${RECORDS}engagements/${id}/engagement.json`).then(r => r.json());
    list = Observer.attacks(D);
    $("attacks").innerHTML = list.map((x, i) => `<button type="button" data-i="${i}">${esc(nameOf(x.actor))} · ${esc(x.ref)} <span>${esc(x.ev.local.slice(11))}</span></button>`).join("");
    $("attacks").querySelectorAll("button").forEach(b => b.addEventListener("click", () => choose(+b.dataset.i)));
    let i = list.findIndex(x => x.actor === boat && x.ref === attack);
    if (i < 0) i = Math.max(0, list.findIndex(x => !E.attackSheet(x.sh.torpedoes).problems.length));
    choose(i);
  }
  sel.addEventListener("change", () => open(sel.value));

  function choose(i) {
    stop();
    cur = list[i];
    Object.assign(cur, Observer.targetsOf(D, cur.sh));
    A = E.attackSheet(cur.sh.torpedoes, { sizes: cur.tg.map(t => t.size) });
    $("attacks").querySelectorAll("button").forEach((b, j) => b.setAttribute("aria-pressed", i === j));
    const u = new URL(location.href);
    u.searchParams.set("e", D.id); u.searchParams.set("boat", cur.actor); u.searchParams.set("attack", cur.ref);
    history.replaceState(null, "", u);
    const w = cur.sh.words[0] || {};
    const back = `engagement.html?e=${encodeURIComponent(D.id)}`;
    $("about").innerHTML = `${esc(nameOf(cur.actor))}'s ${esc(cur.ref.replace(/^A/, "a"))}, ${esc(cur.ev.local.slice(0, 10))}, from her attack data sheet (${EV.cite(cur.sh.cite, "src")})` +
      `${w.description ? `: <span class="typed">${esc(w.description)}</span>` : ""}. ${A.torps.length} torpedo${A.torps.length === 1 ? "" : "es"} fired. ` +
      `The torpedoes' tracks against the ships: <a href="${back}">the engagement's page</a>, "At the periscope".`;
    const drawable = !A.problems.length;
    $("faces").hidden = !drawable; $("clockrow").hidden = !drawable; $("nodraw").hidden = drawable;
    if (!drawable) {
      $("nodraw").innerHTML = `<b>Not drawn:</b> ${A.problems.map(esc).join("; ")}. Without them the computer has nothing to turn to; the sheet's rows are on <a href="${back}">the engagement's page</a>.`;
      return;
    }
    slider.min = A.start; slider.max = Math.ceil(A.end); slider.step = 1;
    drawAssumed();
    update(0);
  }

  const clock = sec => {
    const ms = cur.t0 + sec * 1000 + E.zoneHours(cur.zone || "Z") * 3600e3, d = new Date(ms), p = n => String(n).padStart(2, "0");
    return `${p(d.getUTCHours())}${p(d.getUTCMinutes())}:${p(d.getUTCSeconds())}${cur.zone ? " " + cur.zone : ""}`;
  };
  const rel = sec => sec < 0 ? `${Math.round(-sec)} s before the first torpedo` : `${Math.round(sec)} s after the first torpedo`;

  function update(sec) {
    s = Math.max(A.start, Math.min(A.end, sec));
    slider.value = s;
    const d = E.tdcAt(A, s), len = cur.tg[d.target] ? cur.tg[d.target].size[0] : cur.tg[0].size[0];
    tdc.set(d, { time: s - A.start, length: len });
    $("clock").textContent = clock(s); $("rel").textContent = rel(s);
    legend(d, len);
  }

  // the legend: each dial's number on the face, its name as the manual's photograph names it, its value now, and where
  // that value comes from
  function legend(d, len) {
    const on = d.generating, T = A.targets[d.target] || {}, who = A.targets.length > 1 ? `target ${d.target + 1}` : "the target";
    const none = "—", sideOf = x => x && x.tube != null ? x : null, F = sideOf(d.fwd), Af = sideOf(d.aft);
    const pk = [
      ["target speed", on ? `${d.targetSpeed} kts` : none, `${who}'s speed, set in by hand: the sheet's typed speed`],
      ["angle solver range", on ? yd(d.range) : none, "the range the position keeper sends the angle solver: computed, from the sheet's range at firing and both ships' courses and speeds"],
      ["generating", on ? "on" : "off", "lit while the position keeper keeps the target moving: on whenever the sheet places a target"],
      ["target", on ? `bearing ${pad3(d.trueBearing)}° (the ring, less 180°); angle on the bow ${side(d.aob)} (the inner disc); target course ${pad3(d.targetCourse)}° at its zero${d.solved ? `; track ${Math.round(d.track)}°${d.side} (the arrow's tail)` : ""}` : none,
        "the target's true bearing and angle on the bow now, computed from the sheet; the track from the solution (OP 1056 pp. 72-73)"],
      ["range", on ? yd(d.range) : none, "the same range, read beside the target dial"],
      ["distance to track", on ? yd(d.distanceToTrack) : none, "how far the boat lies from the target's track: range × |sin angle on the bow| (OP 1056 Fig. 38); the arm stands at the angle on the bow, its × at the range"],
      ["own ship", on ? `bearing ${pad3(d.trueBearing)}° (the ring); relative bearing ${pad3(d.relBearing)}° (the inner disc)${F ? `; forward gyro ${pad3(F.gyroOrder)}°` : ""}${Af ? `; after gyro ${pad3(Af.gyroOrder)}°` : ""}` : none,
        "the target's bearing from own bow, and the gyro angles ordered (the arrowheads; the after one paler)"],
      ["time", `${Math.floor((s - A.start) / 60)} min ${Math.round((s - A.start) % 60)} s`, "the computer's clock, started at the start of this view (assumed)"],
      ["target length", `${len} ft`, cur.tg[d.target] && cur.tg[d.target].ship ? `the length of ${esc(cur.tg[d.target].ship.sil.name)}'s plate (which ship the target was is inferred)` : `assumed for a ${esc((cur.tg[d.target] || cur.tg[0]).kind)}${len < 300 ? " (below the dial's 300 ft, shown at 300)" : ""}`],
      ["relative target bearing", on ? `${pad3(d.relBearing)}°` : none, "true bearing less own course, on a 1-speed dial and a 36-speed dial (10° a turn) for the fine reading"],
      ["own speed", `${A.ownSpeed} kts`, "the sheet's own speed; the dial's numbers assumed (the manual says only that it matches the ship's log)"],
      ["own course", `${pad3(d.ownCourse)}°`, "own heading now: the sheet's course, turned through any gyro-angle change it types"],
    ];
    const solverSide = (x, name) => x ? `${name}: tube ${esc(x.tube)}, gyro ${pad3(x.gyroOrder)}°` : `${name}: no tube to fire`;
    const as = [
      ["gyro angle order", on && d.solved ? [solverSide(F, "forward"), solverSide(Af, "after")].join("; ") : none,
        "the gyro angle the next tube on each side is ordered: the point of aim's gyro plus that tube's offset; the solution is worked as in Torpedo fire control (the law of sines)"],
      ["correct solution", on && d.solved ? "on" : "off", "lit when the triangle closes: when the torpedo can reach the target's track at its speed"],
      ["offset angle", on && d.solved ? [F && `forward ${lr(F.offset)}`, Af && `after ${lr(Af.offset)}`].filter(Boolean).join("; ") || none : none, "the spread: each tube's angle off the point of aim, from the sheet's gyro angles"],
      ["torpedo run", on && d.solved ? yd(d.fwd ? d.fwd.run : d.aft.run) : none, "the torpedo's run to the target's track: distance to track / |sin track angle|"],
      ["depth-speed", on ? `${d.torpedoSpeed} kts; depth set ${d.depth != null ? d.depth + " ft" : "not typed"}` : none, "the next torpedo's speed (the sheet's, or its setting assumed) under the depth set as typed"],
    ];
    const li = (rows) => rows.map(([nm, v, w], i) => `<li><b class="n">${i + 1}</b><span class="nm">${nm}</span><span class="v">${esc(v)}</span><span class="w">${w}</span></li>`).join("");
    $("leg-pk").innerHTML = li(pk); $("leg-as").innerHTML = li(as);
  }

  // what the faces assume (the engagement page's observer view lists its own under the periscope)
  function drawAssumed() {
    const lens = cur.tg.map(t => t.size[0]), lowDepth = A.torps.some(t => (parseFloat(t.row.depth_set) || 99) < 10);
    const list = [`that ${esc(nameOf(cur.actor))}'s computer was a Mark 3 (no record read names its mark; the Mark 3's manual went to boats "SS 167-544 incl.", OP 1056 p. 277)`,
      "the forward and after angle solvers ordering the same angles (the periscope-to-tube distance, the torpedo's reach and its turn are left out, as in the engagement page's plot); tubes 1-6 forward, 7-10 aft",
      `the target's length, ${lens.join(" and ")} ft${lens.some(l => l < 300) ? " (below the dial's 300 ft, shown at 300)" : ""}`, "the own-speed dial's numbers (the manual says only that it matches the ship's log)",
      "the time dial started at the start of this view", "the Distance to Track lines read as thousands of yards", ...(lowDepth ? ["a depth set below the dial's 10 feet shown at 10"] : []),
      ...A.assumed.map(esc)];
    $("assumed").innerHTML = `The dials of a Torpedo Data Computer Mark 3, after its manual, OP 1056 (the faces Figs. 98 and 102, pp. 107 and 111; what the Target and Own Ship dials read, pp. 72-73; the scales, pp. 267-270; <a href="https://archive.org/details/mechanical-computer-technical-manuals">a scan</a>), turned to the solution computed from ${esc(nameOf(cur.actor))}'s sheet: what the computer would have shown on these figures, not a record of what it did show. Each dial reads at the orange index at its top. Assumed: ${list.join("; ")}. A reconstruction: a lead, not a record.`;
  }

  function stop() { if (timer) { timer.stop(); timer = null; } playBtn.textContent = "▶"; playBtn.setAttribute("aria-label", "Play"); }
  function play() {
    if (s >= A.end) s = A.start;
    playBtn.textContent = "❚❚"; playBtn.setAttribute("aria-label", "Pause");
    let last = null;
    timer = d3.timer(el => { const dt = last == null ? 0 : el - last; last = el; update(s + dt / 1000 * 10);   // ten times real time
      if (s >= A.end) stop(); });
  }
  slider.addEventListener("input", () => { stop(); update(+slider.value); });
  playBtn.addEventListener("click", () => timer ? stop() : play());

  await open(q.get("e") || "", q.get("boat"), q.get("attack"));
})();
