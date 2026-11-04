// engagement.html?e=<id>&view=account|records|working: one engagement from both sides' records, at three depths
// (guides/OPERATIONS-VIEWER.md, 4). Reads records/engagements/index.json and records/engagements/<id>/engagement.json
// (tools/build_engagement.py); the computation is engage.js's, the shared drawing engage-views.js's. Encodings:
// guides/ENGAGEMENTS.md. The account (the default) is one static screen: the outcome in the records' terms, the
// subjects, the span, the map with every mark shown, and three doors. The records is the chart-room sheet: the map
// with its clock and lanes and the two-sided log when the frame is clocked, the chronology when it is dated, the order
// of battle and the story; `&at=<ISO minute>` sets its clock. When the story is told in steps (the build's `steps`:
// entries carrying `step`, framed by the front matter), the story sits beside the map as the narrative, and each
// [[step:]] link in it (links.js) sets the clock to the step's time and the map to its framing; `&step=<id>` opens
// there, and the clock's playback marks the step it is in. The working is where our voice leads, labelled: the
// periscope, closing in, the frame's own figures (panels.js: the registry of each engagement's panels, each a module
// under site/panels/), the Sources view (one moment at a time, source by source), the claims board and how this was
// read. Each is a part of this one page, shown by the address. A frame whose records sit closer than a world coastline
// tells (Algiers) names a relief and a road map in its front matter, drawn under the marks.
(async () => {
  const E = Engage, esc = EV.esc;
  const index = await fetch(RECORDS + "engagements/index.json").then(r => r.json());
  const params = new URLSearchParams(location.search), want = params.get("e");
  const id = index.some(x => x.id === want) ? want : "tama-17-1944-04-29";
  const DEPTHS = ["account", "records", "working"];
  const VIEW = DEPTHS.includes(params.get("view")) ? params.get("view") : "account";
  const IN = v => VIEW === v;
  const address = (eid, view) => `?e=${encodeURIComponent(eid)}&view=${view}`;
  const [D, world] = await Promise.all([fetch(`${RECORDS}engagements/${id}/engagement.json`).then(r => r.json()),
    d3.json(EV.LAND_10M), SILHOUETTES]);
  const LAND = EV.land(world);
  // the map's base where the front matter asks for one: today's relief and coastline (records/relief/<name>/, the
  // tiles' box from the build) and the traced roads of 1942 (records/roads/)
  const ROADS = D.roads ? await d3.json(`${RECORDS}roads/${D.roads}-primary.geojson`).catch(() => null) : null;
  // the story's steps (the build's `steps`): each with the time of its earliest clocked entry and its framing; a
  // [[step:]] link's address opens the records depth at that step
  const STEPS = (D.steps || []).map(st => ({ ...st, ms: E.T(st.utc || st.key) }));
  const stepHref = st => `${address(id, "records")}${st.utc ? `&at=${encodeURIComponent(st.utc)}` : ""}&step=${encodeURIComponent(st.id)}`;
  const STEP_LINKS = Object.fromEntries(STEPS.map(st => [st.id, { href: stepHref(st) }]));
  const stepOf = sid => STEPS.find(st => st.id === sid);
  // the frame's own figures (panels.js), on the working
  const FIGURES = (typeof PANELS === "object" && PANELS[D.id]) || [];   // counted on every depth, mounted on the working
  const PANEL_LIST = IN("working") ? FIGURES : [];
  const crumb = document.getElementById("crumb");
  Chapter.crumb(id, crumb).then(() => { crumb.hidden = !crumb.innerHTML; }, () => { crumb.hidden = true; });

  // ---------- the picker: every engagement, by theatre, in date order
  const THEATRES = { pacific: "Pacific", mediterranean: "Mediterranean", europe: "Europe" };
  const sel = document.getElementById("engagement");
  sel.innerHTML = Object.entries(THEATRES).map(([k, name]) => {
    const xs = index.filter(x => x.theater === k);
    return xs.length ? `<optgroup label="${name}">${xs.map(x => `<option value="${x.id}"${x.id === id ? " selected" : ""}>${esc(x.title)}${x.boats.length ? " · " + esc(x.boats.join(", ")) : ""}</option>`).join("")}</optgroup>` : "";
  }).join("");
  sel.addEventListener("change", () => { location.search = address(sel.value, VIEW); });   // the depth stays

  // ---------- who's who, and their colours (colour follows the boat; the other side is ink; the press the lighter ink;
  // red is for hits). Who is the other side is the build's `opposed`, from each actor's nationality against the followed
  // subjects' (`own`, or the front matter's `against`); the press is told by its source's kind, never by a side.
  const PARTS = D.participants;
  const byId = Object.fromEntries(PARTS.map(p => [p.id, p]));
  const opposedOf = of => D.against ? D.against.includes(of) : !!of && !(D.own || []).includes(of);
  const LIGHTER = new Set(["press", "intelligence"]);   // not a record: the lighter ink, whichever side's
  const inkOf = x => LIGHTER.has(x.source_kind) ? "var(--ink-3)" : x.opposed ? "var(--japan)" : x.of ? "var(--ink-2)" : "var(--ink-3)";   // no `of`: a place
  const colour = id => byId[id]?.colour ? `var(--c${byId[id].colour})` : byId[id] ? inkOf(byId[id]) : "var(--ink-2)";
  const evColour = e => byId[e.actor] ? colour(e.actor) : inkOf(e);
  const nameOf = a => byId[a]?.name || a;
  const TRACKED = PARTS.filter(p => (D.tracks[p.id] || []).length);
  // one timeline lane per tracked ship or boat, then one per nationality for everyone else, named as the records name it
  // (E.nation: Japanese, German), never as a bloc; the press its own, and radio intelligence its own under its name
  // (FRUPAC): a source about the other side, not a subject, so never in a followed subject's lane
  const laneOf = e => byId[e.actor] && TRACKED.includes(byId[e.actor]) ? e.actor : e.source_kind === "press" ? "press"
    : e.source_kind === "intelligence" ? "intel:" + (e.actor || "") : "of:" + (e.of || "");
  const LANES = [...TRACKED.map(p => ({ id: p.id, name: p.name, colour: colour(p.id) })),
    ...[...new Set(D.events.map(e => laneOf(e)).filter(l => l === "press" || l.startsWith("of:") || l.startsWith("intel:")))].map(l => (l === "press"
      ? { id: l, name: "Press", colour: "var(--ink-3)" } : l.startsWith("intel:") ? { id: l, name: l.slice(6), colour: "var(--ink-3)" }
      : { id: l, name: E.nation(l.slice(3)), colour: opposedOf(l.slice(3)) ? "var(--japan)" : "var(--ink-2)" }))];

  // ---------- time: GMT where the records give a zone; otherwise the records' own local clock
  const tOf = e => E.T(e.utc || e.key);
  D.events.forEach(e => { e.ms = tOf(e); });
  const timed = D.events.filter(e => e.ms != null && !Number.isNaN(e.ms));
  let t0 = D.window ? E.T(D.window.from) : d3.min(timed, e => e.ms), t1 = D.window ? E.T(D.window.to) : d3.max(timed, e => e.ms);
  if (t1 - t0 < 3600e3) { t0 -= 1800e3; t1 += 1800e3; }
  // ---------- the tempo decides which view leads (guides/OPERATIONS-VIEWER.md, 3). Clocked: the map plays and the log
  // follows it, as below. Dated or monthly: there is no clock to play, so the time controls and the log go, the map
  // stands still with every mark shown, and the chronology leads, full width, where the log was.
  const TEMPO = E.tempo(D.events), CLOCKED = TEMPO === "clocked";
  // The clock plays only on the records depth of a clocked frame. The account's map is the same drawing with the clock
  // at the window's end: every track, mark and place shown, no play button, no lanes, no fading (zoom and pan stay).
  const PLAYS = CLOCKED && IN("records");
  // the story told in steps sits beside the map on the records depth, with the log behind a tab when the clock plays
  const STEPPED = IN("records") && STEPS.length > 0;
  if (!PLAYS) {
    document.querySelector(".time").hidden = true;
    document.querySelector(".side").hidden = !STEPPED;
    document.getElementById("action").classList.add(IN("account") ? "account" : "dated");
  }
  if (STEPPED) document.getElementById("action").classList.add("stepped");
  document.getElementById("action").hidden = IN("working");
  document.getElementById("account").hidden = !IN("account");
  document.getElementById("doors").hidden = !IN("account");
  document.getElementById("story").hidden = !IN("records") || STEPPED;   // beside the map instead, as the narrative
  // the clock the address asks for (`&at=1944-04-29T13:01Z`): the records depth of a clocked frame opens at that minute
  const AT = PLAYS && params.get("at") ? E.T(params.get("at")) : null;
  const OWN = D.clock && D.gmt ? D.clock : (D.theater === "pacific" && D.gmt ? "I" : "");
  const OWN_NAME = { I: "Item (Tokyo time)", B: "Baker", K: "King", H: "How" };
  document.getElementById("clock-zone").textContent = D.gmt ? "GMT" : "local time (the records give no zone)";
  const clockText = ms => `${E.hhmm(ms)} · ${E.day(ms)}`;

  // ---------- header and story
  const secs = D.sections || [];
  const top = secs.find(s => !s.heading);
  document.title = D.short || D.title;
  document.getElementById("eyebrow").textContent = D.eyebrow || "";
  document.getElementById("title").textContent = D.title;
  const render = s => Links.render(s, { cites: D.cites || {}, steps: STEP_LINKS });
  if (top && top.paras.length) document.getElementById("lede").innerHTML = render(top.paras[0].text);
  // the story's Sources (and What is missing) sections belong to the working, under how this was read; the rest is the
  // records' narrative; the Outcome and Clocks sections also go to the account
  const sourcesSec = s => /^sources\b|what('s| is) missing/i.test(s.heading || "");
  const sectionsHTML = list => list.map(s => {
    const paras = s === top ? s.paras.slice(1) : s.paras;
    if (!s.heading && !paras.length) return "";
    return `${s.heading ? `<h2>${esc(s.heading)}</h2>` : ""}${paras.map(p => `<p class="${p.aside ? "aside" : ""}">${render(p.text)}</p>`).join("")}`;
  }).join("");
  document.getElementById("story").innerHTML = sectionsHTML(secs.filter(s => !sourcesSec(s)));
  if (STEPPED) document.getElementById("narrative-text").innerHTML = sectionsHTML(secs.filter(s => s.heading && !sourcesSec(s)));
  const SOURCES_HTML = sectionsHTML(secs.filter(sourcesSec));
  document.getElementById("sources").innerHTML = SOURCES_HTML;
  document.getElementById("sources-card").hidden = !(IN("working") && SOURCES_HTML);

  // ---------- the convoy's path as the boats saw it (ours): the ship contacts, at the target's position, and the
  // Japanese record's positions, straight between them. Closing in is computed from it, and the account draws it dotted.
  // A sighting the report itself contradicts (its fix note says so) is left off, and listed.
  const contradicts = f => /contradict/i.test(f.fix || "");
  const contradicted = D.fixes.filter(f => f.kind === "ship" && contradicts(f));
  const seen = [...D.fixes.filter(f => f.kind === "ship" && !contradicts(f)).map(f => ({ utc: f.utc, lon: f.lon, lat: f.lat })),
                ...D.events.filter(e => e.origin === "japanese" && e.lat != null && e.utc).map(e => ({ utc: e.utc, lon: e.lon, lat: e.lat }))];
  const PATH = Object.keys(D.convoys).length ? E.observedPath(seen) : [];

  // ---------- legend: only the marks this engagement has
  const has = f => D.events.some(f);
  document.getElementById("legend").innerHTML = [
    ...TRACKED.map(p => `<span class="boat"><svg width="22" height="10"><line x1="1" y1="5" x2="21" y2="5" stroke="${colour(p.id)}" stroke-width="2.5"/></svg>${esc(p.name)}</span>`),
    has(e => e.kind === "attack") && `<span>${EV.legendMark.attack("var(--ink-2)")}Torpedo attack</span>`,
    D.fixes.some(f => f.on_track) && `<span><svg width="10" height="10" viewBox="-5 -5 10 10"><circle r="3.5" fill="var(--ink-2)"/></svg>Reported position</span>`,
    D.fixes.some(f => f.kind === "ship") && `<span>${EV.legendMark.sighted("var(--ink-2)")}Ship sighted (the target's position)</span>`,
    has(e => e.mark === "sunk" && e.lat != null) && `<span>${EV.legendMark.sunk}Sunk (Japanese record)</span>`,
    has(e => e.mark === "hit" && e.lat != null) && `<span>${EV.legendMark.hit}Hit, not sunk</span>`,
    has(e => e.mark === "miss" && e.lat != null) && `<span>${EV.legendMark.miss}Attacked, no damage</span>`,
    has(e => e.kind === "contact_report" && e.origin !== "frupac") && `<span><svg width="24" height="10"><line x1="1" y1="5" x2="23" y2="5" class="msg" stroke="var(--ink-2)"/></svg>Contact report, sender to each boat it went to</span>`,
    has(e => e.origin === "frupac" && e.lat != null) && `<span>${EV.legendMark.intel}Estimated by FRUPAC (US radio intelligence; the position read from the map)</span>`,
    D.fixes.some(f => !f.on_track && f.kind !== "ship") && `<span><svg width="12" height="12" viewBox="-6 -6 12 12"><circle r="4.5" fill="none" stroke="var(--ink-2)" stroke-width="1.4" stroke-dasharray="2 2"/></svg>Contradicted in the report</span>`,
    D.positions.length && `<span><svg width="10" height="10" viewBox="-5 -5 10 10"><rect x="-3" y="-3" width="6" height="6" fill="var(--ink-3)"/></svg>A place in the records</span>`,
    D.positions.some(r => r.lat2 != null) && `<span><svg width="16" height="12" viewBox="0 0 16 12"><rect x="1" y="1" width="14" height="10" fill="none" stroke="var(--ink-2)" stroke-width="1.2"/></svg>A grid square the record names (our decoding)</span>`,
    (D.relief || []).length && `<span><svg width="18" height="12" viewBox="0 0 18 12"><rect x="1" y="1" width="16" height="10" fill="var(--land)" stroke="var(--coast)"/></svg>Relief and coast: today's elevation (SRTM, USGS)</span>`,
    ROADS && `<span><svg width="22" height="10"><line x1="1" y1="5" x2="21" y2="5" class="road"/></svg>Primary roads of 1942 (OSS Map 967, traced, ± about 4 km)</span>`,
    IN("account") && PATH.length > 1 && `<span><svg width="26" height="8"><line x1="1" y1="4" x2="25" y2="4" stroke="var(--ink-3)" stroke-width="1.4" stroke-dasharray="2 4"/></svg><i>The convoy's path as the boats saw it (ours)</i></span>`,
  ].filter(Boolean).join("");

  // ---------- map
  const svg = d3.select("#map");
  const HATCH = EV.hatchDef(svg);   // the intelligence estimates' hatch (inferred, never solid)
  const gLand = svg.append("g"), gGrat = svg.append("g"), gRelief = svg.append("g"), gPlace = svg.append("g"), gPath = svg.append("g"), gTrk = svg.append("g"), gMsg = svg.append("g"),
        gNowName = svg.append("g"), gMk = svg.append("g"), gNow = svg.append("g"), gPulse = svg.append("g");
  let proj = null, BASE = null, W = 0, H = 0, quiet = false, t = t1, playing = false, raf = 0, lastT = null;
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const ZOOM_MAX = STEPS.length ? 48 : 12;   // a step's framing can be a few miles across (Haynsworth's station)
  const view = mapZoom(svg.node(), document.querySelector(".map-box"), () => { if (proj && !quiet) { drawStatic(); drawFrame(); } },
                       { capture: true, max: ZOOM_MAX, at: "bottom-right" });
  // the relief: inside each tile set's box, the sea, then the land through the elevation mask (a finer coastline than
  // the world atlas's), then the hillshade; placed by the projection, so placed again at every zoom. Today's ground:
  // harbour works since 1943 show as land. The roads over it, faint, for context.
  const RELIEF = (D.relief || []).map((r, i) => {
    const url = `${RECORDS}relief/${r.name}/`;
    const img = svg.select("defs").append("mask").attr("id", `relief-land-${i}`).attr("maskUnits", "userSpaceOnUse")
      .append("image").attr("href", url + "land.png").attr("preserveAspectRatio", "none");
    const g = gRelief.append("g").attr("class", "relief");
    g.append("rect").attr("class", "relief-sea");
    g.append("rect").attr("class", "relief-land").attr("mask", `url(#relief-land-${i})`);
    g.append("image").attr("href", url + "shade.png").attr("preserveAspectRatio", "none").attr("class", "relief-shade");
    return { box: r.box, els: [img, ...g.selectAll("rect, image").nodes().map(n => d3.select(n))] };
  });
  function drawBase() {
    RELIEF.forEach(r => {
      const [[w, s], [e, n]] = r.box, a = P(w, n), b = P(e, s);
      r.els.forEach(el => el.attr("x", a[0]).attr("y", a[1]).attr("width", b[0] - a[0]).attr("height", b[1] - a[1]));
    });
    gRelief.selectAll("path.road").data(ROADS ? [ROADS] : []).join("path").attr("class", "road").attr("d", d3.geoPath(proj));
  }
  const ruler = scaleBar(document.querySelector(".map-box"), { units: ["nm"] });
  const P = (lon, lat) => proj([lon, lat]);
  if (!D.box) document.querySelector(".map-box").hidden = true;

  function drawStatic() {
    if (!D.box || document.getElementById("action").hidden) return;   // (the working has no map: nothing to fit)
    const el = svg.node(); W = el.clientWidth; H = el.clientHeight;
    if (W < 120 || H < 120) return;   // not laid out yet (a resize in progress): a fit to nothing would draw inside out
    const b = D.box, m = Math.min(44, W * 0.06);
    proj = d3.geoMercator().fitExtent([[m, 26], [W - m, H - 34]], { type: "MultiPoint", coordinates: [[b[0], b[1]], [b[2], b[3]], [b[0], b[3]], [b[2], b[1]]] });
    view.bound(W, H);
    BASE = { scale: proj.scale(), translate: proj.translate() };   // the fit before the reader's zoom, for zoomToBox
    mapZoom.scaled(proj, BASE, view.transform());
    ruler.update(p => proj.invert(p));
    gLand.selectAll("path").data([LAND]).join("path").attr("class", "land").attr("d", d3.geoPath(proj));
    EV.graticule(gGrat, proj, W, H);
    drawBase();
    const inView = ([x, y]) => x > 30 && x < W - 30 && y > 24 && y < H - 24;
    gPlace.selectAll("*").remove();
    D.places.filter(p => inView(P(p.lon, p.lat))).forEach(p => gPlace.append("text").attr("class", "place")
      .attr("x", P(p.lon, p.lat)[0]).attr("y", P(p.lon, p.lat)[1]).attr("text-anchor", "middle").style("font-size", p.small ? "10px" : null).text(p.name));
    // the account: the convoy's observed path, dotted (ours; the caption says so)
    gPath.selectAll("path").data(IN("account") && PATH.length > 1 ? [PATH] : []).join("path").attr("class", "trk observed")
      .attr("d", d3.line().x(p => P(p.lon, p.lat)[0]).y(p => P(p.lon, p.lat)[1]));
    drawMarks();
  }

  function drawMarks() {
    const items = [];
    D.fixes.filter(f => f.kind !== "attack" && !f.ref.endsWith(" fired")).forEach(f =>
      items.push({ k: f.kind === "ship" ? "ship" : f.on_track ? "fix" : "off", f, ms: E.T(f.utc), lon: f.lon, lat: f.lat }));
    d3.groups(D.events.filter(e => e.kind === "attack" && e.lat != null), e => e.actor + Math.round(e.lat * 30) + "," + Math.round(e.lon * 30))
      .forEach(([, es]) => items.push({ k: "attack", es, ms: d3.min(es, e => e.ms), lon: es[0].lon, lat: es[0].lat, who: es[0].actor, doubt: es.every(e => e.note) }));
    d3.groups(D.events.filter(e => e.origin === "japanese" && e.lat != null), e => e.lat + "," + e.lon)
      .forEach(([, es]) => items.push({ k: "jp", es, ms: d3.min(es, e => e.ms), lon: es[0].lon, lat: es[0].lat }));
    // US radio intelligence's estimates (FRUPAC's notes with a mark of their own): hatched, under the records' marks
    d3.groups(D.events.filter(e => e.origin === "frupac" && e.lat != null), e => e.lat + "," + e.lon)
      .forEach(([, es]) => items.push({ k: "intel", es, ms: d3.min(es, e => e.ms), lon: es[0].lon, lat: es[0].lat }));
    D.positions.filter(r => r.lat != null).forEach(r => items.push({ k: "pos", r, ms: -Infinity, lon: r.lon, lat: r.lat }));
    const order = { pos: 0, intel: 1, off: 2, ship: 3, fix: 4, jp: 5, attack: 6 };
    items.sort((a, b) => order[a.k] - order[b.k]);
    const sel = gMk.selectAll("g.mk").data(items).join("g").attr("class", d => "mk " + d.k)
      .attr("transform", d => `translate(${P(d.lon, d.lat).map(v => v.toFixed(1))})`);
    sel.selectAll("*").remove();
    const labelled = new Set();
    sel.each(function (d) {
      const g = d3.select(this);
      if (d.k === "fix") { g.append("circle").attr("r", 5).attr("fill", "var(--surface)"); g.append("circle").attr("r", 3.5).attr("fill", colour(d.f.who)); }
      if (d.k === "off") g.append("circle").attr("r", 4.5).attr("fill", "none").attr("stroke", colour(d.f.who)).attr("stroke-width", 1.4).attr("stroke-dasharray", "2 2");
      if (d.k === "ship") g.append("circle").attr("r", 4.5).attr("fill", "var(--surface)").attr("stroke", colour(d.f.who)).attr("stroke-width", 1.8).attr("stroke-dasharray", contradicts(d.f) ? "2 2" : null);
      if (d.k === "attack") {
        g.append("path").attr("d", EV.shape.diamond).attr("transform", "scale(1.25)").attr("fill", "var(--surface)");
        g.append("path").attr("d", EV.shape.diamond).attr("transform", "scale(1.1)").attr("fill", d.doubt ? "var(--surface)" : colour(d.who))
          .attr("stroke", colour(d.who)).attr("stroke-width", d.doubt ? 1.6 : 0).attr("stroke-dasharray", d.doubt ? "2 2" : null);
      }
      if (d.k === "jp") {
        const worst = d.es.some(e => e.mark === "sunk") ? "sunk" : d.es.some(e => e.mark === "hit") ? "hit" : "miss";
        EV.outcomeMark(g, worst, d.es.every(e => e.basis === "secondary"));
        const names = d.es.flatMap(e => (e.title || "").replace(/ Maru/g, "").split(/ and |, /)).filter(Boolean), key = [...names].sort().join("+");
        if (names.length && !labelled.has(key)) {
          labelled.add(key);
          g.append("text").attr("class", "mk-label").attr("x", -9).attr("y", 4).attr("text-anchor", "end").text([...new Set(names)].join(" + "));
        }
      }
      if (d.k === "intel") EV.intelMark(g, HATCH);
      if (d.k === "pos" && d.r.lat2 != null && d.r.lon2 != null) {
        // a square the record names (a kana grid code decoded): its far corner is the row's lat2/lon2; hatched, since
        // the decoding is ours; dashed when the reading is only probable
        const [x2, y2] = P(d.r.lon2, d.r.lat2).map((v, i) => v - P(d.lon, d.lat)[i]);
        g.append("rect").attr("x", Math.min(0, x2)).attr("y", Math.min(0, y2)).attr("width", Math.abs(x2)).attr("height", Math.abs(y2))
          .attr("fill", HATCH).attr("stroke", inkOf(d.r)).attr("stroke-width", 1).attr("stroke-dasharray", d.r.basis === "probable" ? "4 3" : null);
        g.append("text").attr("class", "port").attr("x", Math.min(0, x2) + 4).attr("y", Math.min(0, y2) - 5).text(String(d.r.label).split(":")[0]);
      } else if (d.k === "pos") {
        g.append("rect").attr("x", -3).attr("y", -3).attr("width", 6).attr("height", 6).attr("fill", inkOf(d.r))
          .attr("fill-opacity", d.r.basis === "assumed" || d.r.basis === "approx" || d.r.basis === "hand-placed" ? 0.35 : 1);
        // few: labelled (many: on hover); a landmark (a 1942 sheet's name) only close in, where the names have room
        if (D.positions.length <= 15 && !(d.r.kind === "landmark" && view.transform().k < 4)) g.append("text").attr("class", "port").attr("x", 6).attr("y", -5).text(d.r.label);
      }
      g.append("circle").attr("r", 11).attr("fill", "transparent");
    });
    sel.on("mouseenter", (ev, d) => EV.showTip(ev, tipHTML(d))).on("mousemove", EV.moveTip).on("mouseleave", EV.hideTip)
      .on("click", (ev, d) => { if (d.ms > -Infinity) { stop(); setTime(d.ms); highlightRow(d.ms); } });
  }

  const srcLine = c => c && c.href ? `<div class="i">${esc(c.source_title || "")} ${esc(c.label || "")} · click a log entry for the page</div>` : "";
  // a FRUPAC note's relation to the attack its frupac.yml ties it to (records/README.md), in words before the relation itself
  const INTEL_RELATION = { match: "The same event as the attack: ", candidate: "A candidate for the attack (time and place fit; something doesn't): ", context: "Context, probably not this boat: " };
  function tipHTML(d) {
    if (d.k === "attack" || d.k === "jp") return d.es.map(e => `<div class="v">${esc(nameOf(e.actor))} · ${esc(e.title)}</div><div class="k">${clockText(e.ms)} ${D.gmt ? "GMT" : ""} · ${esc(e.local)}</div><div class="m">${esc(e.words)}</div>${(e.outcome || []).map(o => `<div class="m"><b>Japanese side (${esc(o.relation)}).</b> ${esc(o.note)}</div>`).join("")}${e.note ? `<div class="i">${esc(e.note)}</div>` : ""}`).join("<hr>");
    // US radio intelligence: the note as written, its relation to the attack it is tied to (ours), the map's zoom view
    if (d.k === "intel") return d.es.map(e => {
      const f = e.frupac || {}, boat = PARTS.find(p => p.track === e.unit);
      const tie = f.attack ? `${INTEL_RELATION[f.relation] || ""}<i>${esc(f.relation || "tied to")}</i> · ${esc(boat ? boat.name : "the boat")}'s ${esc(f.attack)}` : "tied to no attack";
      return `<div class="v">FRUPAC ${esc(f.id || "")} · ${esc(e.title)}</div><div class="k">${clockText(e.ms)} ${D.gmt ? "GMT" : ""} · ${esc(e.local)} <i>(zone assumed)</i></div><div class="m">${esc(e.words)}</div>`
        + `<div class="i">${tie}. US radio intelligence; the position is read from the map, not the note's.${f.zoom ? ` <a href="${esc(f.zoom)}" target="_blank" rel="noopener">the map ↗</a>` : ""}</div>`; }).join("<hr>");
    if (d.k === "pos") return `<div class="v">${esc(d.r.label)}</div><div class="k">${esc([d.r.date, d.r.time].filter(Boolean).join(" "))}${d.r.basis ? " · " + esc(d.r.basis) : ""}${d.r.resolved ? " · " + esc(d.r.resolved) : ""}</div>${d.r.note ? `<div class="m">${esc(d.r.note)}</div>` : ""}<div class="i">${esc(d.r.source || "")}</div>`;
    const f = d.f, what = d.k === "ship" ? "Sighted: the target's position, not the boat's" : d.k === "off" ? "Left off the track" : "Reported position";
    return `<div class="v">${esc(nameOf(f.who))} · ${esc(f.ref)}</div><div class="k">${esc(f.raw)} · ${clockText(E.T(f.utc))} GMT · ${esc(f.local)}</div><div class="m">${what}. ${esc(f.note)}</div>${f.fix ? `<div class="i">${esc(f.fix)}</div>` : ""}`;
  }

  // ---------- firing pulses, and contact reports (a ring on the sender's track and a dotted line to each recipient)
  // a boat whose attack table and narrative both time an attack pulses once, at the narrative's time (to the second)
  const attacks = D.events.filter(e => e.kind === "attack" && e.origin === "track");
  const num = e => e.actor + ":" + ((e.title.match(/Attack (\d+)/) || [])[1]);
  const narrated = new Set(attacks.filter(e => e.title.includes("(narrative)")).map(num));
  const fires = attacks.filter(e => e.title.includes("(narrative)") || !narrated.has(num(e)))
    .map(e => ({ ms: e.ms, at: () => E.posAt(D.tracks[e.actor] || [], e.ms) || [e.lon, e.lat] }));
  function pulse(f) {
    const [x, y] = P(...f.at());
    if (reduced) { const c = gPulse.append("circle").attr("class", "fire").attr("cx", x).attr("cy", y).attr("r", 14).attr("stroke-width", 2.5); setTimeout(() => c.remove(), 1100); return; }
    gPulse.append("circle").attr("class", "fire-core").attr("cx", x).attr("cy", y).attr("r", 6).transition().duration(700).attr("opacity", 0).remove();
    [0, 280].forEach(delay => gPulse.append("circle").attr("class", "fire").attr("cx", x).attr("cy", y).attr("r", 5).attr("stroke-width", 3)
      .transition().delay(delay).duration(1300).ease(d3.easeCubicOut).attr("r", 30).attr("stroke-width", 0.5).attr("opacity", 0).remove());
  }
  const MSGS = D.events.filter(e => e.kind === "contact_report" && e.ms != null);
  function drawMessages() {
    const live = MSGS.filter(m => t >= m.ms && t - m.ms < 3 * 3600e3);
    const rows = [];
    live.forEach(m => {
      const a = E.posAt(D.tracks[m.actor] || [], m.ms);
      if (!a) return;
      const fade = 1 - (t - m.ms) / (3 * 3600e3);
      rows.push({ k: "ring", a, m, fade });
      (m.to || []).forEach(r => { const b = E.posAt(D.tracks[r] || [], t); if (b) rows.push({ k: "line", a, b, m, fade }); });
    });
    gMsg.selectAll("*").remove();
    rows.forEach(r => {
      if (r.k === "ring") gMsg.append("circle").attr("cx", P(...r.a)[0]).attr("cy", P(...r.a)[1]).attr("r", 9).attr("fill", "none")
        .attr("stroke", colour(r.m.actor)).attr("stroke-width", 1.6).attr("opacity", r.fade);
      else gMsg.append("line").attr("class", "msg").attr("stroke", colour(r.m.actor)).attr("opacity", r.fade)
        .attr("x1", P(...r.a)[0]).attr("y1", P(...r.a)[1]).attr("x2", P(...r.b)[0]).attr("y2", P(...r.b)[1]);
    });
  }

  function drawFrame() {
    if (proj) {
      const line = d3.line().x(p => P(...p)[0]).y(p => P(...p)[1]);
      const rows = [], nows = [];
      TRACKED.forEach(p => {
        const pts = D.tracks[p.id], now = E.posAt(pts, t);
        const past = pts.filter(q => E.T(q.utc) <= t).map(q => [q.lon, q.lat]), ahead = pts.filter(q => E.T(q.utc) > t).map(q => [q.lon, q.lat]);
        if (now) { past.push(now); ahead.unshift(now); if (PLAYS) nows.push({ p, now }); }   // the "now" dot is the clock's
        rows.push({ id: p.id, cls: "past", pts: past }, { id: p.id, cls: "ahead", pts: ahead });
      });
      gTrk.selectAll("path").data(rows).join("path").attr("class", d => "trk " + d.cls).attr("stroke", d => colour(d.id)).attr("d", d => d.pts.length > 1 ? line(d.pts) : null);
      gMk.selectAll("g.mk").classed("future", d => PLAYS && d.ms > t);   // no clock: everything is shown
      if (lastT !== null && t !== lastT) fires.filter(f => (f.ms > lastT && f.ms <= t && t - lastT < 3 * 3600e3) || f.ms === t).forEach(pulse);
      lastT = t;
      drawMessages();
      const ng = gNow.selectAll("g").data(nows, d => d.p.id).join(enter => {
        const g = enter.append("g");
        g.append("circle").attr("r", 10).attr("fill", d => colour(d.p.id)).attr("opacity", 0.22);
        g.append("circle").attr("r", 5).attr("fill", d => colour(d.p.id)).attr("stroke", "var(--surface)").attr("stroke-width", 2);
        return g;
      });
      ng.attr("transform", d => `translate(${P(...d.now).map(v => v.toFixed(1))})`);
      gNowName.selectAll("text").data(nows, d => d.p.id).join("text").attr("class", "now-name").text(d => d.p.name)
        .attr("x", d => P(...d.now)[0] + 11).attr("y", d => P(...d.now)[1] - 9);
    }
    document.getElementById("clock").textContent = clockText(t);
    document.getElementById("clock-own").textContent = OWN ? `${OWN_NAME[OWN] || OWN} ${clockText(t + E.zoneHours(OWN) * 3600e3)}` : "";
    document.getElementById("scrub").value = t;
    drawCursor();
    updateLog();
    updateClosing();
    if (STEPPED && PLAYS) { const st = stepAt(t); if (st) markStep(st.id, playing); }
  }

  // ---------- the story's steps beside the map: a click on a [[step:]] link moves the clock to the step's time and the
  // map to its framing; the current step is marked, and the clock's playback marks the step it is in (the last one
  // begun). The log sits behind a tab when the clock plays; a dated frame shows the narrative alone.
  const stepAt = ms => { let k = null; STEPS.forEach(st => { if (st.ms != null && !Number.isNaN(st.ms) && st.ms <= ms) k = st; }); return k; };
  let CUR_STEP = null;
  function markStep(sid, scroll) {
    if (sid === CUR_STEP) return;
    CUR_STEP = sid;
    document.querySelectorAll("#narrative a.step").forEach(a => {
      const on = a.dataset.step === sid;
      a.classList.toggle("current", on);
      if (on) a.setAttribute("aria-current", "step"); else a.removeAttribute("aria-current");
    });
    document.querySelectorAll("#narrative-text p").forEach(para => para.classList.toggle("current", !!para.querySelector(`a.step[data-step="${CSS.escape(sid)}"]`)));
    const st = stepOf(sid);
    const view = st && st.view && st.view.name;
    document.getElementById("step-now").innerHTML = st ? `${esc(st.when || E.day(st.ms))}${view ? ` <span class="view">${esc(view)}</span>` : ""}` : "";
    if (scroll) {
      const a = document.querySelector(`#narrative a.step[data-step="${CSS.escape(sid)}"]`), box = document.getElementById("narrative");
      if (a) box.scrollTo({ top: Math.max(0, (a.closest("p") || a).offsetTop - box.clientHeight / 4), behavior: reduced ? "auto" : "smooth" });
    }
  }
  function goStep(sid, animate = true) {
    const st = stepOf(sid);
    if (!st) return;
    stop();
    if (PLAYS && st.ms != null && !Number.isNaN(st.ms)) setTime(st.ms);
    if (st.view && st.view.box) zoomToBox(st.view.box, animate);
    markStep(sid, true);
  }
  // frame the map on a box, [[west, south], [east, north]]: the zoom that fits it (never out past the map's own fit),
  // centred on it; the zoom's bounds keep it on the map
  function zoomToBox([[w, s], [e, n]], animate = true) {
    if (!proj || !BASE) return;
    const p0 = d3.geoMercator().scale(BASE.scale).translate(BASE.translate);
    const [x1, y1] = p0([w, n]), [x2, y2] = p0([e, s]);
    const k = Math.max(1, Math.min(ZOOM_MAX, Math.min(W / (x2 - x1), H / (y2 - y1)) * 0.92));
    const tr = d3.zoomIdentity.translate(W / 2 - k * (x1 + x2) / 2, H / 2 - k * (y1 + y2) / 2).scale(k);
    if (!animate || reduced) view.set(tr);
    else d3.select(svg.node()).transition().duration(700).ease(d3.easeCubicInOut).call(view.zoom.transform, tr);
  }
  if (STEPPED) {
    document.getElementById("narrative").hidden = false;
    document.getElementById("narrative").addEventListener("click", ev => {
      const a = ev.target.closest("a.step");
      if (a) { ev.preventDefault(); goStep(a.dataset.step); }
    });
    const tabs = document.getElementById("side-tabs");
    tabs.hidden = !PLAYS;
    document.getElementById("side-title").hidden = PLAYS;
    document.getElementById("log").hidden = true;
    if (PLAYS) tabs.querySelectorAll("button").forEach(b => b.addEventListener("click", () => {
      tabs.querySelectorAll("button").forEach(x => x.setAttribute("aria-selected", x === b));
      document.getElementById("narrative").hidden = b.dataset.pane !== "narrative";
      document.getElementById("log").hidden = b.dataset.pane !== "log";
      document.getElementById("side-sub").textContent = b.dataset.pane === "log" ? "Follows the clock; click an entry to go there" : "Each step sets the clock and the map; click one to go there";
    }));
    document.getElementById("side-title").textContent = "The story";
    document.getElementById("side-sub").textContent = PLAYS ? "Each step sets the clock and the map; click one to go there" : "Each step frames the map; click one to go there";
  }

  // ---------- the frame's own figures (panels.js): each engagement's panels, mounted on the working, a card each
  function drawPanels() {
    const host = document.getElementById("panels");
    host.hidden = !PANEL_LIST.length;
    if (host.hidden) return;
    host.innerHTML = "";
    PANEL_LIST.forEach(pn => {
      const card = document.createElement("section");
      card.className = "card panel-card";
      card.id = `panel-${pn.id}`;
      card.innerHTML = `<h2>${esc(pn.heading)}</h2>${pn.intro ? `<p class="below intro">${esc(pn.intro)}</p>` : ""}<div class="panel-body"></div>`;
      host.appendChild(card);
      pn.mount(card.querySelector(".panel-body"), D);
    });
  }

  // ---------- lanes
  const lanes = d3.select("#lanes");
  let lx = null;
  function drawLanes() {
    if (!PLAYS) return;
    const laneH = 17, top = 4, left = 104;
    lanes.style("height", `${top + LANES.length * laneH + 24}px`);
    const w = lanes.node().clientWidth;
    lx = d3.scaleUtc().domain([t0, t1]).range([left, w - 8]);
    lanes.selectAll("*").remove();
    LANES.forEach((L, i) => {
      const y = top + i * laneH + laneH / 2;
      lanes.append("line").attr("class", "lane-line").attr("x1", left).attr("x2", w - 8).attr("y1", y).attr("y2", y);
      lanes.append("text").attr("class", "lane-label").attr("x", 0).attr("y", y + 4).text(L.name.length > 14 ? L.name.slice(0, 13) + "…" : L.name);
      timed.filter(e => laneOf(e) === L.id && e.ms >= t0 && e.ms <= t1).forEach(e => {
        const x = lx(e.ms);
        if (e.kind === "attack") lanes.append("path").attr("d", EV.shape.diamond).attr("transform", `translate(${x},${y}) scale(0.95)`).attr("fill", L.colour);
        else if (e.mark) EV.outcomeMark(lanes.append("g").attr("transform", `translate(${x},${y}) scale(0.75)`), e.mark, e.basis === "secondary");
        else if (e.kind === "contact_report") lanes.append("circle").attr("cx", x).attr("cy", y).attr("r", 4).attr("fill", "none").attr("stroke", L.colour).attr("stroke-width", 1.6);
        else lanes.append("line").attr("x1", x).attr("x2", x).attr("y1", y - 4).attr("y2", y + 4).attr("stroke", e.kind === "depth_charge" ? L.colour : "var(--ink-3)").attr("stroke-width", 1.5);
      });
    });
    const axisY = top + LANES.length * laneH + 4, ax = lanes.append("g").attr("class", "axis");
    lx.ticks(w < 500 ? 4 : 8).forEach(d => {
      ax.append("line").attr("x1", lx(d)).attr("x2", lx(d)).attr("y1", top).attr("y2", axisY);
      ax.append("text").attr("x", lx(d)).attr("y", axisY + 12).attr("text-anchor", "middle").text(t1 - t0 > 3 * 86400e3 ? E.day(+d) : E.hhmm(+d) + (D.gmt ? "Z" : ""));
    });
    lanes.append("line").attr("class", "cursor").attr("y1", 0).attr("y2", axisY);
    const sc = document.getElementById("scrub");
    sc.min = t0; sc.max = t1; sc.step = 60000;
    drawCursor();
  }
  function drawCursor() { if (lx) lanes.select(".cursor").attr("x1", lx(t)).attr("x2", lx(t)); }
  lanes.on("click", ev => { if (!lx) return; stop(); setTime(+lx.invert(d3.pointer(ev)[0])); });
  document.getElementById("scrub").addEventListener("input", e => { stop(); setTime(+e.target.value); });

  // ---------- the chronology, when the frame has no clock to play: Engage's rows and columns, EV's drawing
  function drawChronology() {
    document.getElementById("chron-card").hidden = CLOCKED || !IN("records");
    if (CLOCKED || !IN("records")) return;
    EV.chronology(document.getElementById("chron"), { rows: E.chronologyRows(D.events, TEMPO), columns: E.chronologyColumns(D.events, PARTS), tempo: TEMPO, nameOf });
    document.getElementById("chron-title").textContent = TEMPO === "monthly" ? "The records, by the month" : "The records, by the day";
    document.getElementById("chron-note").textContent = (TEMPO === "monthly"
      ? "The entries carry months and days, not times, so there is no clock to play: the map shows every place and position at once, and each column is one record, its entries at the month they are dated. "
      : "The entries carry days, not times, so there is no clock to play: the map shows every place and position at once, and each column is one record, its entries at the day they are dated. ")
      + "A time is as the record wrote it; an entry with none is placed by the order of the account and says so. A station starts a bar in the unit's colour; a casualty or a shelling is named in red.";
  }

  // ---------- the two-sided log
  function drawLog() {
    if (!PLAYS) return;
    document.getElementById("log").innerHTML = D.events.map((e, i) => {
      const who = byId[e.actor];
      const shape = who && who.sil ? EV.sil(who.sil, evColour(e), { ftPx: 0.1, width: 40 }) : e.of === "jp" ? EV.sil("cargo", "var(--japan)", { width: 40 }) : "";
      const name = who ? who.name : e.actor || E.nation(e.of);
      // a source that isn't a record wears its kind and nationality ("intelligence · US"), as the chronology's columns do
      const chip = e.source_kind && e.source_kind !== "record" ? `<span class="chip">${esc(E.sourceKindWord(e.source_kind, e.source_of))}</span>` : "";
      const lang = e.lang || "ja";   // the record's own language: Japanese in its face, any other typed
      const what = e.title && e.title !== name ? `<span class="what">${esc(e.title)}</span>` : e.kind && e.kind !== "log" ? `<span class="what">${esc(e.kind.replace(/_/g, " "))}</span>` : "";
      const toWhom = e.to ? ` <span class="what">to ${e.to.map(r => esc(nameOf(r))).join(" and ")}</span>` : e.from ? ` <span class="what">from ${esc(nameOf(e.from))}</span>` : "";
      const placed = e.placed ? `<div class="assume">${esc(e.placed === "seq" ? "Time placed by the order of the account, not recorded" : e.placed)}</div>` : "";
      return `<div class="row entry${e.basis === "assumed" ? " assumed" : ""}" tabindex="0" data-t="${e.ms ?? ""}" style="--bar:${evColour(e)}">
        <div class="t${e.placed ? " placed" : ""}">${e.ms != null && e.local.length > 10 ? E.hhmm(e.ms) : ""}<small>${e.ms != null ? E.day(e.ms) : esc(e.local)}</small></div>
        <div class="body">
          <div class="who">${shape}<b>${esc(name)}</b>${chip}${what}${toWhom}<span class="own">${esc(e.local.slice(11))}</span></div>
          ${e.original ? `<div class="${lang === "ja" ? "ja" : "said"}" lang="${esc(lang)}" data-tr="${esc(e.translation || e.words || "")}">${esc(e.original)}</div><div class="tr">${esc(e.translation || e.words || "")} (translated)</div>` : `<div class="said">${esc(e.words || e.title || "")}</div>`}
          ${(e.outcome || []).map(o => `<div class="note"><b>Japanese side (${esc(o.relation.replace(/_/g, " "))}).</b> ${esc(o.note)}</div>`).join("")}
          ${e.note ? `<div class="assume">${esc(e.note)}</div>` : ""}${placed}
          ${e.source ? `<span class="src">${esc(e.source)}</span>` : ""} ${EV.cite(e.cite, "src alone")}
        </div></div>`;
    }).join("");
    document.querySelectorAll("#log .row").forEach(r => {
      const go = () => { if (r.dataset.t) { stop(); setTime(+r.dataset.t); } };
      r.addEventListener("click", ev => { if (!ev.target.closest("a")) go(); });
      r.addEventListener("keydown", ev => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); go(); } });
    });
  }
  let lastCurrent = null;
  function updateLog() {
    const rows = [...document.querySelectorAll("#log .row")];
    let cur = null;
    rows.forEach(r => { const f = r.dataset.t !== "" && +r.dataset.t > t; r.classList.toggle("future", f); if (!f && r.dataset.t !== "") cur = r; });
    rows.forEach(r => r.classList.toggle("current", r === cur));
    if (playing && cur && cur !== lastCurrent) scrollLog(cur);
    lastCurrent = cur;
  }
  function scrollLog(row) { const box = document.getElementById("log"); box.scrollTo({ top: Math.max(0, row.offsetTop - box.clientHeight / 3), behavior: reduced ? "auto" : "smooth" }); }
  function highlightRow(ms) { const r = [...document.querySelectorAll("#log .row")].find(r => +r.dataset.t === ms); if (r) scrollLog(r); }

  // ---------- closing in: each boat's distance from where the convoy was seen
  const boats = TRACKED.filter(p => p.kind === "submarine");
  const series = boats.map(b => ({ b, pts: E.closing(D.tracks[b.id], PATH, 160) })).filter(s => s.pts.length > 1);
  let cx = null, cy = null;
  function drawClosing() {
    const card = document.getElementById("closing-card");
    card.hidden = !(IN("working") && Object.keys(D.convoys).length && series.length);
    if (card.hidden) return;
    const s = d3.select("#closing"), w = s.node().clientWidth, h = 220, m = { l: 48, r: 90, t: 12, b: 26 };
    s.selectAll("*").remove();
    cx = d3.scaleUtc().domain([t0, t1]).range([m.l, w - m.r]);
    cy = d3.scaleLinear().domain([0, d3.max(series, x => d3.max(x.pts, p => p.nm)) * 1.05]).nice().range([h - m.b, m.t]);
    const ax = s.append("g").attr("class", "axis");
    cy.ticks(4).forEach(v => { ax.append("line").attr("x1", m.l).attr("x2", w - m.r).attr("y1", cy(v)).attr("y2", cy(v)); ax.append("text").attr("x", m.l - 6).attr("y", cy(v) + 4).attr("text-anchor", "end").text(v + " nm"); });
    cx.ticks(w < 500 ? 4 : 8).forEach(d => ax.append("text").attr("x", cx(d)).attr("y", h - 8).attr("text-anchor", "middle").text(t1 - t0 > 3 * 86400e3 ? E.day(+d) : E.hhmm(+d) + "Z"));
    MSGS.forEach(mm => s.append("line").attr("x1", cx(mm.ms)).attr("x2", cx(mm.ms)).attr("y1", m.t).attr("y2", h - m.b).attr("class", "msg").attr("stroke", colour(mm.actor)));
    D.events.filter(e => e.kind === "attack").forEach(e => s.append("path").attr("d", EV.shape.diamond).attr("transform", `translate(${cx(e.ms)},${h - m.b}) scale(0.8)`).attr("fill", colour(e.actor)));
    const line = d3.line().x(p => cx(p.ms)).y(p => cy(p.nm));
    series.forEach(x => {
      s.append("path").attr("class", "series").attr("stroke", colour(x.b.id)).attr("d", line(x.pts));
      const last = x.pts[x.pts.length - 1];
      s.append("text").attr("class", "direct").attr("x", cx(last.ms) + 6).attr("y", cy(last.nm) + 4).text(`${x.b.name} ${Math.round(last.nm)} nm`);
    });
    s.append("line").attr("class", "cursor").attr("id", "closing-cursor").attr("y1", m.t).attr("y2", h - m.b);
    s.append("rect").attr("x", m.l).attr("y", m.t).attr("width", w - m.l - m.r).attr("height", h - m.t - m.b).attr("fill", "transparent")
      .on("mousemove", ev => {
        const ms = +cx.invert(d3.pointer(ev)[0]);
        const vals = series.map(x => { const p = x.pts.reduce((a, b) => Math.abs(b.ms - ms) < Math.abs(a.ms - ms) ? b : a); return Math.abs(p.ms - ms) < 3600e3 ? `${x.b.name}: ${Math.round(p.nm)} nm` : `${x.b.name}: no position`; });
        EV.showTip(ev, `<div class="v">${clockText(ms)} GMT</div>${vals.map(v => `<div class="m">${esc(v)}</div>`).join("")}<div class="i">Computed from the tracks: a lead, not a record</div>`);
      }).on("mouseleave", EV.hideTip).on("click", ev => { stop(); setTime(+cx.invert(d3.pointer(ev)[0])); });
    document.getElementById("closing-note").innerHTML = `Each line is a boat's distance from where the convoy was seen (${PATH.length} sightings: the boats' ship contacts, at the target's position, and the Japanese record's positions), straight between sightings and only while both are known: computed, a lead, not a record. Dotted rules are contact reports; diamonds are attacks. The navigators disagree by a few miles, so the convoy's path zigzags.${contradicted.length ? ` Left out because the report itself contradicts them: ${contradicted.map(f => `${esc(nameOf(f.who))} ${esc(f.ref)} (${esc(f.fix)})`).join("; ")}.` : ""}`;
  }
  function updateClosing() { if (cx) d3.select("#closing-cursor").attr("x1", cx(t)).attr("x2", cx(t)); }

  // ---------- the Sources view and the claims board (guides/OPERATIONS-VIEWER.md 3, 4.3, 7.1): one table per moment. A
  // moment is a pairing of an attack with a Japanese record (the boat's claims.yml, `pairs`), or a question the
  // engagement's claims.yml leaves open; the computation is Engage's, the drawing EV's.
  const QUESTIONS_BY = E.claimMoments(D.claims);
  const MOMENTS = [...E.pairMoments(D), ...QUESTIONS_BY];
  function drawMoments() {
    const card = document.getElementById("moments-card");
    card.hidden = !(IN("working") && MOMENTS.length);
    if (card.hidden) return;
    const el = document.getElementById("moments");
    el.innerHTML = "";
    MOMENTS.forEach(m => { const div = document.createElement("div"); el.appendChild(div); EV.sources(div, m); });
    document.getElementById("moments-sub").textContent = `${n(MOMENTS.length, "moment")}: each column is one source, as typed, in its own language and on its own clock`;
  }
  function drawClaims() {
    document.getElementById("claims-card").hidden = !(IN("working") && D.claims.length);
    if (D.claims.length) EV.board(document.getElementById("claims"), QUESTIONS_BY);
  }

  // ---------- order of battle: the kit's silhouettes, true relative size where the library has the class
  function drawOOB() {
    const us = PARTS.filter(p => !p.opposed && !p.convoy && !p.unit), jp = PARTS.filter(p => p.opposed && !p.convoy);
    const ownName = (D.own || []).map(E.nation).join(" and ") || "US";
    const army = PARTS.filter(p => p.unit), t0 = d3.utcFormat("%Y-%m-%d")(new Date(E.T(D.window?.from || d3.min(D.events, e => e.key)) || 0));
    const plate = (name, kind, silId, fill, extra = "", cls = "", title = "") => `<div class="plate ${cls}" title="${esc(title)}">${EV.sil(silId, fill, { ftPx: 0.42 })}<div class="nm">${esc(name)}</div><div class="kd">${esc(kind)}</div>${extra}</div>`;
    const usPlates = us.map(p => plate(p.name + (p.hull ? ` (${p.hull})` : ""), [p.co, p.track ? `record: ${p.track}` : p.note].filter(Boolean).join(" · "), p.sil || EV.category(p.kind), colour(p.id), "", "", EV.silWords(p.sil)));
    const convoyHTML = Object.values(D.convoys).map(c => {
      const route = [c.from, ...(c.via || []), c.to].filter(Boolean).join(" → ");
      const ships = [...c.ships].sort((a, b) => (a.role.startsWith("escort") ? 0 : 1) - (b.role.startsWith("escort") ? 0 : 1));
      return `<h3><a href="convoys.html?c=${esc(c.id)}">Convoy ${esc(c.convoy)}</a> ${c.name_ja ? `<span lang="ja" data-tr="Convoy ${esc(c.convoy)}, as the Japanese records write it">${esc(c.name_ja)}</span>` : ""}</h3>
        <div class="muted" style="margin:-4px 0 10px">${esc(route)}${c.sailed ? ` · sailed ${esc(c.sailed)}` : ""}${c.cargo ? ` · ${esc(c.cargo)}` : ""}</div>
        <div class="plates">${ships.map(s => plate(s.ship, s.role, s.sil || EV.category(s.role), /sunk/.test(s.fate || "") ? "var(--ink)" : "var(--ink-3)",
          s.fate ? `<div class="fate">${esc(s.fate)}</div>` : "", s.basis === "secondary" ? "secondary" : "",
          `${EV.silWords(s.sil, s.sil_basis)}${s.basis === "secondary" ? "; named by a secondary source" : ""}`)).join("")}</div>
        <p class="muted">Silhouettes are drawn to one scale, from the class's own recognition plate where the library has it (hover for which); otherwise the kind of ship only. Italic names come from a secondary source.</p>`;
    }).join("");
    const jpHTML = jp.length ? `<h3>The target</h3><div class="plates">${jp.map(p => plate(p.name, p.note || p.kind, p.sil || EV.category(p.kind), "var(--ink-3)", "", "", "As the boat identified it")).join("")}</div>` : "";
    const armyHTML = army.length ? `<h3>The units</h3><ul class="units">${army.map(p => `<li><a href="army.html?unit=${encodeURIComponent(p.unit)}&amp;t=${t0}">${esc(p.name)}</a>${p.basis && p.basis !== "reported" ? ` <i>(${esc(p.basis)})</i>` : ""}${p.note ? ` <span class="muted">${esc(p.note)}</span>` : ""}</li>`).join("")}</ul>` : "";
    const usHTML = us.length ? `<h3>${us.length > 1 ? ownName : us[0].kind === "submarine" ? "The boat" : ownName}</h3><div class="plates">${usPlates.join("")}</div>` : "";
    document.getElementById("oob").innerHTML = `<div class="pack">${usHTML}${armyHTML}</div><div>${convoyHTML}${jpHTML}</div>`;
    // the account's "Who" already shows our own side's plates, so there the card is the other side's alone (the
    // convoy's ships and their fates, the target as the boat saw it), and goes when there is no other side drawn
    const card = document.getElementById("oob-card");
    card.classList.toggle("other", IN("account"));
    card.hidden = IN("working") || (IN("account") && !(convoyHTML || jpHTML));
  }

  // ---------- time and playback
  function setTime(ms) { t = Math.max(t0, Math.min(t1, ms)); drawFrame(); }
  const playBtn = document.getElementById("play");
  function stop() { playing = false; cancelAnimationFrame(raf); clearTimeout(raf); playBtn.textContent = "▶"; playBtn.setAttribute("aria-label", "Play"); }
  function play() {
    if (t >= t1) t = t0;
    playing = true; playBtn.textContent = "❚❚"; playBtn.setAttribute("aria-label", "Pause");
    if (reduced) {
      const times = timed.map(e => e.ms).filter(x => x > t).sort((a, b) => a - b);
      const step = () => { if (!playing) return; const nx = times.shift(); if (nx == null) { setTime(t1); stop(); return; } setTime(nx); raf = setTimeout(step, 1200); };
      step(); return;
    }
    let last = performance.now();
    const tick = now => { if (!playing) return; t += (now - last) * (t1 - t0) / 45000; last = now; if (t >= t1) { setTime(t1); stop(); return; } drawFrame(); raf = requestAnimationFrame(tick); };
    raf = requestAnimationFrame(tick);
  }
  playBtn.addEventListener("click", () => playing ? stop() : play());

  // ---------- the observer view (observer.js): each attack whose data sheet is transcribed; it lives in the working
  // (the card measures itself when mounted, so it is mounted only where it is shown); picking one moves the clock
  const observer = IN("working") ? Observer.mount({ D, colour, nameOf, setPageTime: ms => { stop(); setTime(ms); highlightRow(ms); } }) : { pick() {} };
  const sheetOf = e => e && e.kind === "attack" && D.sheets?.[e.actor]?.[e.title.replace(" (narrative)", "")] ? e : null;
  document.getElementById("log").addEventListener("click", ev => {
    const row = ev.target.closest(".row"), e = row && D.events[[...row.parentNode.children].indexOf(row)];
    if (sheetOf(e)) observer.pick(e.actor, e.title.replace(" (narrative)", ""));
  });
  gMk.on("click.observer", ev => { const d = d3.select(ev.target.closest("g.mk")).datum(); const e = d && d.es && d.es.find(sheetOf); if (e) observer.pick(e.actor, e.title.replace(" (narrative)", "")); });

  // ---------- the depths: the switch under the breadcrumb, with each depth's count; the account's card and doors
  // (guides/OPERATIONS-VIEWER.md, 4.1). Every number is counted from the frame's own JSON, never written in.
  // the item an entry was read from: its citation's stem (the archive's item: a microfilm roll, a JACAR reference, a
  // catalog page without its page number), so that a boat's track, depths, sheets and narrative, all one report, count
  // once; an entry with no citation counts by the record its source names
  const refStem = e => { const r = String(e.cite?.ref || ""); return /^https?:/.test(r) ? r.replace(/[?#].*$/, "") : r.split("/")[0].replace(/\s+p\d.*$/, ""); };
  const recordKey = e => refStem(e) || E.head(e.source) || String(e.actor || "");
  const ITEM = { jacar: "JACAR ", combinedfleet: "combinedfleet.com, " };
  const recordName = e => E.head(e.source) || (byId[e.actor] && /^rg\d/.test(refStem(e)) ? `${nameOf(e.actor)}'s report` : refStem(e).replace(/^(\w+):/, (m, k) => ITEM[k] || k + " ")) || nameOf(e.actor);
  const RECS = new Map();   // item -> name
  D.events.forEach(e => { if (!RECS.has(recordKey(e))) RECS.set(recordKey(e), recordName(e)); });
  // "records" only for the items whose source is a record (SOURCES.yml's kind, through the citation); every other kind
  // of source is counted apart, in the guide's order ("5 records · 1 intelligence · 2 secondary"); never "Axis", "Allied"
  const KIND_ORDER = ["record", "intelligence", "press", "assessment", "recollection", "secondary", "reference", "derived"];
  const ITEMS = new Map();   // source kind -> the items of that kind
  D.events.forEach(e => { const k = e.source_kind || "unsourced"; if (!ITEMS.has(k)) ITEMS.set(k, new Set()); ITEMS.get(k).add(recordKey(e)); });
  const n = (k, one, many = one + "s") => `${k} ${k === 1 ? one : many}`;
  const kindsLine = [...ITEMS].sort((a, b) => KIND_ORDER.indexOf(a[0]) - KIND_ORDER.indexOf(b[0]))
    .map(([k, items]) => k === "record" ? n(items.size, "record") : `${items.size} ${k}`).join(" · ");
  const LANGS = 1 + (D.events.some(e => e.original) ? 1 : 0);
  const SHEETS = Object.entries(D.sheets || {}).flatMap(([actor, byRef]) => Object.keys(byRef).map(ref => ({ actor, ref })));
  const QUESTIONS = QUESTIONS_BY.length;
  const CLOSING = !!(Object.keys(D.convoys).length && series.length);
  const working = [SHEETS.length && n(SHEETS.length, "attack sheet"), CLOSING && "closing in", FIGURES.length && n(FIGURES.length, "figure"), MOMENTS.length && n(MOMENTS.length, "moment"), QUESTIONS && n(QUESTIONS, "open question"), SOURCES_HTML && "sources"].filter(Boolean);
  const recordsLine = `${n(D.events.length, "entry", "entries")} · ${kindsLine} · ${n(LANGS, "language")}`;
  document.getElementById("depths").innerHTML = [["account", "The account", "one screen, nothing moves"], ["records", "The records", recordsLine],
    ["working", "The working", working.length ? working.join(" · ") : "nothing to show yet"]]
    .map(([v, name, line]) => `<a href="${esc(address(id, v))}"${IN(v) ? ' aria-current="page"' : ""}>${name}<small>${esc(line)}</small></a>`).join("");
  document.getElementById("working-none").hidden = !(IN("working") && !working.length);
  document.getElementById("working-none").textContent = "The working has nothing to show for this engagement yet: no attack sheet is transcribed, there is no convoy to close on, it has no figures of its own, no attack is paired with a record of the other side, the records leave no question listed, and the story has no sources section.";

  if (IN("account")) {
    // the outcome, in the records' terms: the story's Outcome section, its citations links as in the story
    const outcome = secs.find(s => /^outcome$/i.test(s.heading || ""));
    document.getElementById("outcome").innerHTML = outcome && outcome.paras.length ? outcome.paras.map(p => `<p>${render(p.text)}</p>`).join("")
      : `<p class="none">The story has no outcome section yet: what the records say is in the records depth, and the questions they leave open in the working.</p>`;
    // who: one row per participant, the followed subjects in their colours (the chronology's: the build's or the next
    // free of the three checked ones), the other side dashed; the hull, kind and CO as the JSON gives them; the
    // silhouette at the library's one scale, as the order of battle draws it
    const colsOf = Object.fromEntries(E.chronologyColumns(D.events, PARTS).filter(c => c.subject && c.participant).map(c => [c.participant, c.colour]));
    const used = new Set(PARTS.map(p => p.colour).filter(Boolean));
    let slot = 1;
    const barOf = p => {
      if (p.colour) return `var(--c${p.colour})`;
      if (colsOf[p.id]) return colsOf[p.id];
      if (!(p.track || p.unit)) return null;   // not followed: the other side, dashed
      while (used.has(slot)) slot++;           // a followed subject with no entries of its own (Neuburg's units): the next free slot
      return slot <= 3 ? `var(--c${slot++})` : "var(--ink)";
    };
    const convoyWords = p => { const c = D.convoys[p.convoy]; return c ? [[c.from, ...(c.via || []), c.to].filter(Boolean).join(" → "), c.sailed && `sailed ${c.sailed}`, c.ships.length && `${n(c.ships.length, "ship")} named in its record`].filter(Boolean).join("; ") : ""; };
    document.getElementById("who").innerHTML = PARTS.map(p => {
      const bar = barOf(p);
      const words = p.convoy ? [p.kind, convoyWords(p)] : [p.hull, p.kind === "army" ? "Army unit" : p.kind, p.co, p.basis && p.basis !== "reported" && `${p.basis}: not named by the engagement's own entries`];
      const sil = p.sil ? EV.sil(p.sil, bar || "var(--ink-3)", { ftPx: 0.42 }) : "";
      return `<div class="subj"><span class="bar${bar ? "" : " dash"}" style="${bar ? `--bar:${bar}` : ""}"></span><span class="n"><b>${esc(p.name)}</b> <i>${esc(words.filter(Boolean).join(" · "))}</i></span>${sil}</div>`;
    }).join("");
    // when: the window (GMT where the records give a zone) and its length; the Clocks section's first paragraph under it
    const fmt = d3.utcFormat(t1 - t0 > 3 * 86400e3 || !CLOCKED ? "%-d %B %Y" : "%-d %B %H%M"), hours = Math.round((t1 - t0) / 3600e3);
    const span = CLOCKED ? `${fmt(t0)} to ${fmt(t1)} ${D.gmt ? "GMT" : "local time (the records give no zone)"}, ${hours > 72 ? n(Math.round(hours / 24), "day") : n(hours, "hour")}`
      : `${fmt(t0)} to ${fmt(t1)}, by the records' own dates, ${n(Math.round((t1 - t0) / 86400e3) + 1, "day")}`;
    const clocks = secs.find(s => /^(the )?clocks?$/i.test(s.heading || ""));
    document.getElementById("when").innerHTML = `${esc(span)}.${clocks && clocks.paras.length ? ` <span class="k">${render(clocks.paras[0].text)}</span>` : ""}`;
    // the caption under the static map: what is drawn, and which of it is ours
    const placed = D.positions.some(r => r.lat != null && (r.basis === "assumed" || r.basis === "approx" || r.basis === "hand-placed"));
    document.getElementById("cap").textContent = ["The account is static: no clock, and nothing needs a hover; the records and the working have both.",
      TRACKED.length && "A line between a subject's reported positions is straight, and where it went between them is not recorded.",
      PATH.length > 1 && "The convoy's path, dotted, is computed from where the boats sighted it and where the Japanese record puts it: that is ours.",
      placed && "A faint square is a place we placed, not one the record gives."].filter(Boolean).join(" ");
    document.getElementById("cap").hidden = false;
    // the doors: the records and the working, with their counts; the journeys, each subject's own page
    const first = d3.utcFormat("%Y-%m-%d")(new Date(t0));
    const journey = p => {
      if (p.track) { const [alias, patrol] = [p.alias || p.track.split("/")[0], p.track.split("/")[1]]; return `<a href="patrols.html?ship=${encodeURIComponent(alias)}${patrol ? `&amp;patrol=${encodeURIComponent(patrol)}` : ""}">${esc(p.name)}${patrol ? ` patrol ${esc(patrol)}` : ", her track"}</a>`; }
      if (p.convoy) return `<a href="convoys.html?c=${encodeURIComponent(p.convoy)}">${esc(p.name)}: its ships and voyage</a>`;
      if (p.unit) return `<a href="army.html?unit=${encodeURIComponent(p.unit)}&amp;t=${first}">${esc(p.name)}: its stations</a>`;
      return "";
    };
    const journeys = PARTS.map(journey).filter(Boolean);
    const recordNames = [...new Set(RECS.values())], shown = recordNames.slice(0, 6);   // two FRUPAC maps are one name
    document.getElementById("doors").innerHTML = `
      <a class="door" href="${esc(address(id, "records"))}"><b>The records</b><span class="n"><span class="typed">${D.events.length}</span> ${D.events.length === 1 ? "entry" : "entries"} from ${esc(kindsLine)} in ${n(LANGS, "language")}${D.fixes.length ? `, and <span class="typed">${D.fixes.length}</span> ${D.fixes.length === 1 ? "fix" : "fixes"}` : ""}</span>
        <span class="list">${esc(shown.join(" · "))}${recordNames.length > shown.length ? ` · and ${recordNames.length - shown.length} more` : ""} · ${PLAYS || CLOCKED ? "the map with the clock, one lane per subject, and the two-sided log" : "the map, and the chronology by the day"}${STEPS.length ? `, with the story in ${n(STEPS.length, "step")} beside the map` : ""}</span></a>
      <a class="door" href="${esc(address(id, "working"))}"><b>The working</b><span class="n">${working.length ? esc(working.join("; ")) : "nothing to show yet"}</span>
        <span class="list">${esc([SHEETS.length && `at the periscope: ${SHEETS.map(s => `${nameOf(s.actor)} ${s.ref}`).join(", ")}`, CLOSING && "closing in", FIGURES.length && `figures: ${FIGURES.map(f => f.heading).join("; ")}`, MOMENTS.length && `source by source: ${n(MOMENTS.length, "moment")}`, QUESTIONS && "what the records leave open", SOURCES_HTML && "how this was read"].filter(Boolean).join(" · ")) || "no attack sheet, no closing in, no figure, no pair, no open question, no sources section"}</span></a>
      <div class="door"><b>Journeys</b><span class="n">each subject's own record, before and after</span>
        <span class="list">${journeys.length ? journeys.join(" · ") : "no subject here has a page of its own yet"}</span></div>`;
  }

  drawOOB(); drawMoments(); drawClaims(); drawPanels(); drawLog(); drawChronology(); drawStatic(); drawLanes(); drawClosing();
  if (AT != null && !Number.isNaN(AT)) { t = Math.max(t0, Math.min(t1, AT)); drawFrame(); highlightRow(t); } else drawFrame();
  // `&step=<id>`: open at that step (its time and its framing); otherwise the narrative marks the step the clock is in
  // `&step=<id>`: open at that step (its time and its framing); a stepped story with no step or minute asked for opens
  // at its first step, as the story page did; otherwise the narrative marks the step the clock is in
  const STEP0 = STEPPED && params.get("step") && stepOf(params.get("step"));
  if (STEP0) goStep(STEP0.id, false);
  else if (STEPPED && AT == null && STEPS.length) goStep(STEPS[0].id, false);
  else if (STEPPED && PLAYS) { const st = stepAt(t); if (st) markStep(st.id, false); }
  new ResizeObserver(() => { if (D.box) drawStatic(); drawLanes(); drawClosing(); drawFrame(); }).observe(document.querySelector(".wrap"));
})();
