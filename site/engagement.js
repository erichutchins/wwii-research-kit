// engagement.html?e=<id>[&view=questions]: one engagement from both sides' records, at two depths
// (guides/OPERATIONS-VIEWER.md, 4). Reads records/engagements/index.json and records/engagements/<id>/engagement.json
// (tools/build_engagement.py); the computation is engage.js's, the shared drawing engage-views.js's. Encodings:
// guides/ENGAGEMENTS.md. The page (the default) reads top to bottom: the outcome in the records' terms, the subjects
// and the span; the map, with its clock and lanes and the two-sided log when the frame is clocked (`&at=<ISO minute>`
// sets the clock), the chronology when it is dated; the order of battle; the story; then the frame's own figures,
// where our voice leads and is labelled: the periscope, the panels (panels.js: the registry of each engagement's
// panels, each a module under site/panels/), closing in. When the story is told in steps (the build's `steps`:
// entries carrying `step`, framed by the front matter), the story sits beside the map as the narrative, and each
// [[step:]] link in it (links.js) sets the clock to the step's time and the map to its framing; `&step=<id>` opens
// there, and the clock's playback marks the step it is in. Questions and sources (view=questions) is the claims
// board, the Sources view (one moment at a time, source by source, where more than one source speaks to a question)
// and how this was read. Both are parts of this one page, shown by the address; the old addresses
// (view=account|records|working) open the page or the questions. A frame whose records sit closer than a world
// coastline tells (Algiers) names a relief and a road map in its front matter, drawn under the marks; a frame inland
// (Remagen) a relief with its rivers, and a dated situation map's front and units (records/fronts/), with each followed
// unit's way in.
(async () => {
  const E = Engage, esc = EV.esc;
  const index = await fetch(RECORDS + "engagements/index.json").then(r => r.json());
  const params = new URLSearchParams(location.search), want = params.get("e");
  const id = index.some(x => x.id === want) ? want : "tama-17-1944-04-29";
  // the two depths: the page, and the questions behind it; the old three-depth addresses still arrive
  const VIEW = ["questions", "working"].includes(params.get("view")) ? "questions" : "page";
  const IN = v => VIEW === v;
  const address = (eid, view) => `?e=${encodeURIComponent(eid)}${view === "questions" ? "&view=questions" : ""}`;
  const [D, world] = await Promise.all([fetch(`${RECORDS}engagements/${id}/engagement.json`).then(r => r.json()),
    d3.json(EV.LAND_10M), SILHOUETTES]);
  const LAND = EV.land(world);
  // the map's base where the front matter asks for one: today's relief and coastline (records/relief/<name>/, the
  // tiles' box from the build) and the traced roads of 1942 (records/roads/)
  const ROADS = D.roads ? await d3.json(`${RECORDS}roads/${D.roads}-primary.geojson`).catch(() => null) : null;
  // a relief built with its rivers (Natural Earth): for a frame inland, where the relief shows a valley and not its river
  const RIVERS = (await Promise.all((D.relief || []).filter(r => r.rivers)
    .map(r => d3.json(`${RECORDS}relief/${r.name}/rivers.geojson`).catch(() => null)))).filter(Boolean);
  // the dated situation maps (records/fronts/, the front matter's `fronts`, in date order): each one's front line and unit
  // symbols, the staff's picture of its day, drawn under the records as context; the page shows the latest at its clock,
  // or steps through them when there is no clock
  const SITMAPS = (await Promise.all((D.fronts || []).map(f => d3.json(`${RECORDS}fronts/${f.name}.geojson`)
    .then(gj => ({ meta: f, gj }), () => null)))).filter(Boolean);
  // the story's steps (the build's `steps`): each with the time of its earliest clocked entry and its framing; a
  // [[step:]] link's address opens the page at that step
  const STEPS = (D.steps || []).map(st => ({ ...st, ms: E.T(st.utc || st.key) }));
  const stepHref = st => `${address(id, "page")}${st.utc ? `&at=${encodeURIComponent(st.utc)}` : ""}&step=${encodeURIComponent(st.id)}`;
  const STEP_LINKS = Object.fromEntries(STEPS.map(st => [st.id, { href: stepHref(st) }]));
  const stepOf = sid => STEPS.find(st => st.id === sid);
  // the frame's own figures (panels.js), after the story
  const FIGURES = [...((typeof PANELS === "object" && PANELS[D.id]) || []),
    ...(typeof PANELS_ANY === "object" ? PANELS_ANY.filter(f => f.applies(D)).map(f => f.panel) : [])];
  const PANEL_LIST = IN("page") ? FIGURES : [];
  // the breadcrumb: the theatre, the operation and the engagement before and after (chapter.js); the page opened with
  // no engagement named is the picker, and says so
  const crumb = document.getElementById("crumb");
  if (!want) { crumb.innerHTML = Chapter.trail(["Engagements"]); crumb.hidden = false; }
  else Chapter.crumb(id, crumb).then(() => { crumb.hidden = !crumb.innerHTML; }, () => { crumb.hidden = true; });

  // ---------- the picker: every engagement, by theatre, in date order
  const THEATRES = { pacific: "Pacific", europe: "Europe", mediterranean: "Mediterranean", atlantic: "Atlantic" };
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
  // each sheet's front, its placed symbols and the ones it only lists (a box of the divisions facing the bridgehead, not
  // positions), its hour in words, and its time: the sheets' "1200" taken as A (GMT+1), the army group's own time, assumed
  SITMAPS.forEach(S => {
    S.runs = S.gj.features.filter(f => f.properties.kind === "front").map(f => f.geometry.coordinates);
    const units = S.gj.features.filter(f => f.properties.kind === "unit")
      .map(f => ({ ...f.properties, lon: f.geometry.coordinates[0], lat: f.geometry.coordinates[1], opposed: opposedOf(f.properties.of) }));
    S.placed = units.filter(u => !u.list);
    S.listed = units.filter(u => u.list);
    // the sheets write their hour two ways: "071200 MAR 1945" (day, hour) and "1200 HRS 16 DECEMBER 1944"
    S.hhmm = (/^(\d{4}) HRS/.exec(S.meta.as_of) || /^\d{2}(\d{4})/.exec(S.meta.as_of) || [, "1200"])[1];
    S.hour = `${S.hhmm} on ${d3.utcFormat("%-d %B %Y")(new Date(S.meta.date))}`;
    S.ms = E.T(`${S.meta.date}T${String(Number(S.hhmm.slice(0, 2)) - 1).padStart(2, "0")}:${S.hhmm.slice(2)}Z`);
  });
  // the sheet drawn now, and what the drawing reads of it
  let SITMAP = null, FRONT = null, FRONT_RUNS = [], FRONT_UNITS = [], FRONT_HOUR = "";
  const useSitmap = S => { SITMAP = S; FRONT = S ? S.gj : null; FRONT_RUNS = S ? S.runs : []; FRONT_UNITS = S ? S.placed : []; FRONT_HOUR = S ? S.hour : ""; };
  const sitmapAt = ms => SITMAPS.reduce((cur, S) => (S.ms <= ms ? S : cur), SITMAPS[0] || null);
  useSitmap(SITMAPS[0] || null);
  const SITMAP_DAYS = SITMAPS.map(S => d3.utcFormat("%-d")(new Date(S.meta.date)));
  // the sheets' days in words: listed within one month ("7, 8 and 17 March 1945"); across months, the span ("each day
  // from 16 December 1944 to 3 January 1945", or "on 12 days from ... to ..." when some are missing)
  const SITMAP_WHEN = (() => {
    if (SITMAPS.length < 2) return "";
    const first = new Date(SITMAPS[0].meta.date), last = new Date(SITMAPS[SITMAPS.length - 1].meta.date), dmy = d3.utcFormat("%-d %B %Y");
    if (first.getUTCMonth() === last.getUTCMonth() && first.getUTCFullYear() === last.getUTCFullYear())
      return `on ${SITMAP_DAYS.slice(0, -1).join(", ")} and ${SITMAP_DAYS[SITMAP_DAYS.length - 1]} ${d3.utcFormat("%B %Y")(first)}`;
    const every = Math.round((last - first) / 86400e3) + 1 === SITMAPS.length;
    return `${every ? "each day" : `on ${SITMAPS.length} days`} from ${dmy(first)} to ${dmy(last)}`;
  })();
  const STATIONS = D.stations || {};
  const ROUTE_DASH = { reported: null, sketched: "7 4", inferred: "1.5 4" };   // routes.yml's line by basis
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
  // each followed subject's colour, the same in the who at the top and on the map: the build's, else the chronology's
  // column, else the next free of the three checked ones (a followed unit with no entries of its own, Neuburg's); the
  // other side has none (dashed in the who)
  // a participant a route names as its actor (routes.yml: the bombers) takes a colour too, so its paths read as its own
  const ROUTED = new Set((D.routes || []).map(r => r.actor).filter(Boolean));
  const SUBJECT_COLOUR = (() => {
    const colsOf = Object.fromEntries(E.chronologyColumns(D.events, PARTS).filter(c => c.subject && c.participant).map(c => [c.participant, c.colour]));
    const used = new Set(PARTS.map(p => p.colour).filter(Boolean));
    let slot = 1;
    return Object.fromEntries(PARTS.map(p => {
      if (p.colour) return [p.id, `var(--c${p.colour})`];
      if (colsOf[p.id]) return [p.id, colsOf[p.id]];
      if (!(p.track || p.unit || ROUTED.has(p.id))) return [p.id, null];
      while (used.has(slot)) slot++;
      return [p.id, slot <= 3 ? `var(--c${slot++})` : "var(--ink)"];
    }));
  })();

  // ---------- the tempo decides which view leads (guides/OPERATIONS-VIEWER.md, 3). Clocked: the map plays and the log
  // follows it, as below. Dated or monthly: there is no clock to play, so the time controls and the log go, the map
  // stands still with every mark shown, and the chronology leads, full width, where the log was.
  const TEMPO = E.tempo(D.events), CLOCKED = TEMPO === "clocked";
  // The clock plays on the page of a clocked frame, stopped until pressed: it opens at the window's end (or `&at=`), so
  // every track, mark and place is shown first.
  const PLAYS = CLOCKED && IN("page");
  if (PLAYS) useSitmap(sitmapAt(params.get("at") ? E.T(params.get("at")) : t1));
  // a dated frame has no clock to play; its page steps through the day maps instead (`&on=1945-03-13`) on the
  // clocked frames' bar, a map at a time (drawDays), the stations drawn to the map's day
  const STEPPER = !PLAYS && IN("page") && SITMAPS.length > 1;
  if (STEPPER) useSitmap(SITMAPS.find(S => S.meta.date === params.get("on")) || SITMAPS[0]);
  // the story told in steps sits beside the map, with the log behind a tab when the clock plays
  const STEPPED = IN("page") && STEPS.length > 0;
  if (!PLAYS) {
    document.querySelector(".time").hidden = !STEPPER;
    document.querySelector(".side").hidden = !STEPPED;
    document.getElementById("action").classList.add("dated");
  }
  if (STEPPED) document.getElementById("action").classList.add("stepped");
  document.getElementById("action").hidden = IN("questions");
  document.getElementById("account").hidden = IN("questions");
  document.getElementById("picker").hidden = IN("questions");
  document.getElementById("story").hidden = IN("questions") || STEPPED;   // beside the map instead, as the narrative
  // the clock the address asks for (`&at=1944-04-29T13:01Z`): the page of a clocked frame opens at that minute
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
  // the story's Sources (and What is missing) sections belong to the questions, under how this was read; the rest is
  // the records' narrative; the Outcome and Clocks sections also go to the top of the page
  const sourcesSec = s => /^sources\b|what('s| is) missing/i.test(s.heading || "");
  const outcomeSec = s => /^outcome$/i.test(s.heading || "");   // at the top of the page, so not again in the story
  const sectionsHTML = list => list.map(s => {
    const paras = s === top ? s.paras.slice(1) : s.paras;
    if (!s.heading && !paras.length) return "";
    return `${s.heading ? `<h2>${esc(s.heading)}</h2>` : ""}${paras.map(p => `<p class="${p.aside ? "aside" : ""}">${render(p.text)}</p>`).join("")}`;
  }).join("");
  document.getElementById("story").innerHTML = sectionsHTML(secs.filter(s => !sourcesSec(s) && !outcomeSec(s)));
  if (STEPPED) document.getElementById("narrative-text").innerHTML = sectionsHTML(secs.filter(s => s.heading && !sourcesSec(s) && !outcomeSec(s)));
  const SOURCES_HTML = sectionsHTML(secs.filter(sourcesSec));
  document.getElementById("sources").innerHTML = SOURCES_HTML;
  document.getElementById("sources-card").hidden = !(IN("questions") && SOURCES_HTML);

  // ---------- the convoy's path as the boats saw it (ours): the ship contacts, at the target's position, and the
  // Japanese record's positions, straight between them. Closing in is computed from it, and the map draws it dotted, to
  // the clock.
  // A sighting the report itself contradicts (its fix note says so) is left off, and listed.
  const contradicts = f => /contradict/i.test(f.fix || "");
  const contradicted = D.fixes.filter(f => f.kind === "ship" && contradicts(f));
  const seen = [...D.fixes.filter(f => f.kind === "ship" && !contradicts(f)).map(f => ({ utc: f.utc, lon: f.lon, lat: f.lat })),
                ...D.events.filter(e => e.origin === "japanese" && e.lat != null && e.utc).map(e => ({ utc: e.utc, lon: e.lon, lat: e.lat }))];
  const PATH = Object.keys(D.convoys).length ? E.observedPath(seen) : [];
  // the convoy at the clock: on that path, straight between sightings, never beyond them (ours, hatched)
  const CONVOY_NAME = Object.values(D.convoys).map(c => c.convoy).join(" / ");
  const convoyAt = ms => PATH.length > 1 ? E.posAt(PATH, ms) : null;
  // each boat's depth log as states (the build's `dives`: surfaced or submerged, the depth where logged), so the track
  // is drawn thick on the surface and thin under it, and the boat's dot is open while she is down
  const DIVES = D.dives || {};
  const stateAt = (id, ms) => { let k = null; (DIVES[id] || []).forEach(x => { if (E.T(x.utc) <= ms) k = x; }); return k; };
  // the convoy's course and speed as each boat's attack sheet types them: the boat's estimate at the moment she fired,
  // drawn from her attack position (the target was then within the sheet's range of her, a mile or two; the convoy's
  // computed path can be miles off, as the navigators disagree), or from the path where the attack has no position; the
  // length an hour's run at the typed speed (ours). The turns between one sheet and the next are the convoy's evasions.
  const COURSES = Object.entries(D.sheets || {}).flatMap(([who, sh]) => Object.entries(sh).map(([name, a]) => {
    const r = (a.torpedoes || [])[0] || {}, c = parseFloat(r.target_course), k = parseFloat(r.target_speed);
    if (!(c >= 0) || !(k > 0) || !r.date || !r.time || !r.zone) return null;
    let ms; try { ms = E.toUTC(r.date, r.time, r.zone); } catch { return null; }   // a zone the sheet types that isn't a zone letter: off the clock
    const ev = D.events.find(e => e.kind === "attack" && e.actor === who && e.title === name && e.lat != null);
    const at = ev ? [ev.lon, ev.lat] : convoyAt(ms);
    return at && { who, name, course: c, kts: k, ms, at, onPath: !ev, local: `${r.date} ${r.time} ${r.zone}`, cite: a.cite };
  })).filter(Boolean);
  // the escorts' depth charges, as the boat logged them, at where she was then (straight between her fixes: placed, ours)
  const CHARGES = D.events.filter(e => e.kind === "depth_charge" && e.utc && D.tracks[e.actor]).map(e => ({ e, ms: E.T(e.utc), at: E.posAt(D.tracks[e.actor], E.T(e.utc)) })).filter(d => d.at);

  // ---------- legend: only the marks this engagement has
  const has = f => D.events.some(f);
  const KEY_AIR = c => `<svg width="30" height="10"><line x1="1" y1="5" x2="29" y2="5" stroke="${c}" stroke-width="1.8"/><path class="chevron" d="M8,1L12.5,5L8,9M19,1L23.5,5L19,9" stroke="${c}"/></svg>`;
  const KEY_GROUND = c => `<svg width="30" height="10"><line x1="1" y1="5" x2="29" y2="5" class="way" stroke="${c}"/><circle cx="15" cy="5" r="3.2" fill="${c}"/></svg>`;
  document.getElementById("legend").innerHTML = [
    // who is who on the map: our side's followed units and air groups in their colours, the other side in its ink;
    // a unit's moves on the ground plain, an aircraft's path chevroned
    ...PARTS.filter(p => !TRACKED.includes(p) && SUBJECT_COLOUR[p.id] && ((STATIONS[p.id] || []).length > 1 || ROUTED.has(p.id))).map(p =>
      `<span class="boat">${ROUTED.has(p.id) ? KEY_AIR(SUBJECT_COLOUR[p.id]) : KEY_GROUND(SUBJECT_COLOUR[p.id])}${esc(p.name)}${ROUTED.has(p.id) ? ": in the air" : ": on the ground"}</span>`),
    ...[...new Set((D.routes || []).filter(r => r.opposed && r.by === "air").map(r => r.of))].map(of =>
      `<span class="boat">${KEY_AIR("var(--japan)")}${esc(E.nation(of))} aircraft</span>`),
    ...[...new Set(D.positions.filter(r => r.opposed && r.lat != null).map(r => r.of))].map(of =>
      `<span class="boat"><svg width="10" height="10" viewBox="-5 -5 10 10"><rect x="-3.5" y="-3.5" width="7" height="7" fill="var(--japan)"/></svg>${esc(E.nation(of))}: a place or a unit on the ground (its ink)</span>`),
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
    D.positions.some(r => r.kind === "target") && `<span><svg width="18" height="18" viewBox="-9 -9 18 18"><circle r="5.5" fill="none" stroke="var(--ink-2)" stroke-width="1.4"/><circle r="1.8" fill="var(--ink-2)"/><path d="M-9,0H-4M4,0H9M0,-9V-4M0,4V9" stroke="var(--ink-2)" stroke-width="1.4"/></svg>A bombing target, as the record names it</span>`,
    D.positions.length && `<span><svg width="10" height="10" viewBox="-5 -5 10 10"><rect x="-3" y="-3" width="6" height="6" fill="var(--ink-3)"/></svg>A place in the records</span>`,
    D.positions.some(r => r.lat2 != null) && `<span><svg width="16" height="12" viewBox="0 0 16 12"><rect x="1" y="1" width="14" height="10" fill="none" stroke="var(--ink-2)" stroke-width="1.2"/></svg>A map grid square a report names: the maps were ruled in squares, and a report could give a square, not a point, so the whole square is drawn (our decoding)</span>`,
    (D.relief || []).length && `<span><svg width="18" height="12" viewBox="0 0 18 12"><rect x="1" y="1" width="16" height="10" fill="var(--land)" stroke="var(--coast)"/></svg>Relief and coast: today's elevation (SRTM, USGS)${RIVERS.length ? "; rivers from Natural Earth" : ""}</span>`,
    FRONT && `<span>${EV.legendMark.front}<span>The front at ${SITMAPS.length < 2 ? esc(FRONT_HOUR) : `1200 ${esc(SITMAP_WHEN)}, ${STEPPER ? "the day chosen under the map" : "the latest at the clock"}`}, as the <a href="${esc(SITMAP.meta.cite.href)}" target="_blank" rel="noopener">12th Army Group's ${SITMAPS.length > 1 ? "maps" : "map"}</a> drew it (traced, ± about ${Math.max(1, Math.round(SITMAP.meta.fit_km * 2))} km), ticked as the map ticks it, on its own side</span></span>`,
    FRONT_UNITS.some(u => !u.opposed) && `<span>${EV.legendMark.unitUs}A US division or corps on that map: in its area, not at a position</span>`,
    FRONT_UNITS.some(u => u.opposed) && `<span>${EV.legendMark.unitEnemy}The enemy as that map placed them (US intelligence)</span>`,
    (D.rings || []).length && `<span><svg width="20" height="14" viewBox="0 0 20 14"><circle cx="10" cy="7" r="6" fill="var(--ink-2)" fill-opacity=".05" stroke="var(--ink-2)" stroke-width="1.2"${(D.rings || []).some(r => r.basis !== "reported") ? ' stroke-dasharray="4 2"' : ""}/></svg>A weapon's reach: its range as the field manual gives it, round where the battery was${(D.rings || []).some(r => r.basis !== "reported") ? " (dashed: the battery's place or its weapon not its own record's)" : ""}</span>`,
    ...["reported", "sketched", "inferred"].filter(b => (D.routes || []).some(r => r.basis === b)).map(b => `<span><svg width="26" height="10"><line x1="1" y1="5" x2="25" y2="5" stroke="var(--ink-2)" stroke-width="${b === "reported" ? 2.2 : 1.6}" stroke-linecap="round"${ROUTE_DASH[b] ? ` stroke-dasharray="${ROUTE_DASH[b]}"` : ""}/></svg>${{ reported: "An aircraft's course as its form types it (the length ours)", sketched: "A course as a squadron's sketch map draws it (traced, ± a few km)", inferred: "<i>A path no record gives: a straight line between two places (ours)</i>" }[b]}</span>`),
    Object.values(STATIONS).some(rows => rows.length > 1) && `<span><svg width="26" height="10"><line x1="1" y1="5" x2="25" y2="5" class="way" stroke="var(--ink-2)"/></svg>A unit's stations, joined straight; lighter in the week before the engagement</span>`,
    ROADS && `<span><svg width="22" height="10"><line x1="1" y1="5" x2="21" y2="5" class="road"/></svg>Primary roads of 1942 (OSS Map 967, traced, ± about 4 km)</span>`,
    PATH.length > 1 && `<span><svg width="26" height="8"><line x1="1" y1="4" x2="25" y2="4" stroke="var(--ink-3)" stroke-width="1.4" stroke-dasharray="2 4"/></svg><i>The convoy's path as the boats saw it (ours; to the clock)</i></span>`,
    PATH.length > 1 && PLAYS && `<span><svg width="16" height="16" viewBox="-8 -8 16 16"><circle r="6" fill="url(#hatch-intel)" stroke="var(--japan)" stroke-width="1.4"/></svg><i>The convoy at the clock, on that path (ours)</i></span>`,
    COURSES.length && `<span><svg width="26" height="10"><path d="M2,5H23M18,1.5L23,5L18,8.5" fill="none" stroke="var(--japan)" stroke-width="1.5"/></svg>The convoy's course and speed as a boat's attack sheet types it (her estimate as she fired; the length an hour's run, ours)</span>`,
    Object.keys(DIVES).some(id => D.tracks[id]) && `<span><svg width="30" height="10"><line x1="1" y1="5" x2="13" y2="5" stroke="var(--ink-2)" stroke-width="2"/><line x1="16" y1="5" x2="29" y2="5" stroke="var(--ink-2)" stroke-width="1"/></svg>Surfaced, then submerged (her depth log; her dot open while she was down)</span>`,
    CHARGES.length && `<span><svg width="16" height="16" viewBox="-8 -8 16 16"><path d="${d3.range(8).map(i => { const a = i * Math.PI / 4, r0 = i % 2 ? 2.5 : 3, r1 = i % 2 ? 5 : 7; return `M${r0 * Math.cos(a)},${r0 * Math.sin(a)}L${r1 * Math.cos(a)},${r1 * Math.sin(a)}`; }).join("")}" stroke="var(--japan)" stroke-width="1.3"/></svg>Depth charges, as the boat logged them, where she was (placed, ours)</span>`,
  ].filter(Boolean).join("");

  // ---------- map
  const svg = d3.select("#map");
  const HATCH = EV.hatchDef(svg);   // the intelligence estimates' hatch (inferred, never solid)
  // the overview in the map's corner: the convoy's whole voyage on the lanes of the time, and the box where this map is
  // (engage-overview.js); only for an engagement that names a convoy with a route
  const CONVOYS_J = Object.keys(D.convoys).length && D.box ? await fetch(RECORDS + "convoys/convoys.json").then(r => r.json()).catch(() => null) : null;
  const OVERVIEW = CONVOYS_J ? EngageOverview.draw(document.querySelector(".map-box"), { land: LAND, lanes: CONVOYS_J.lanes,
    convoys: CONVOYS_J.convoys.filter(c => D.convoys[c.id]), hatch: HATCH }) : null;
  const gLand = svg.append("g"), gGrat = svg.append("g"), gRelief = svg.append("g"), gFront = svg.append("g"), gWay = svg.append("g"), gRing = svg.append("g"), gRoute = svg.append("g"), gPlace = svg.append("g"), gPath = svg.append("g"), gCourse = svg.append("g"), gCharge = svg.append("g"), gTrk = svg.append("g"), gMsg = svg.append("g"),
        gNowName = svg.append("g"), gMk = svg.append("g"), gConvoy = svg.append("g"), gNow = svg.append("g"), gPulse = svg.append("g");
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
    gRelief.selectAll("path.river-edge").data(RIVERS).join("path").attr("class", "river-edge").attr("d", d3.geoPath(proj));
    gRelief.selectAll("path.river").data(RIVERS).join("path").attr("class", "river").attr("d", d3.geoPath(proj));
  }
  // the situation map's picture: the front, then each unit's symbol (hover: what the map says, and what it doesn't)
  function drawFront(inView) {
    gFront.selectAll("*").remove();
    if (!FRONT) return;
    EV.frontLine(gFront, FRONT_RUNS, P);
    const ECH = { xx: "division", xxx: "corps", xxxx: "army", xxxxx: "army group", xxxxxx: "theatre command" };
    const REL = { part_of: "part of", under_command: "under", attached_to: "attached to" };
    const unitName = id => PARTS.find(p => p.unit === id)?.name || id;
    FRONT_UNITS.filter(u => inView(P(u.lon, u.lat))).forEach(u => {
      const ties = (SITMAP.meta.ties || {})[u.unit] || [], own = ties.find(t => !t.path.length);
      const tie = ties.length ? { colour: SUBJECT_COLOUR[(own || ties[0]).participant] || "var(--ink-2)", own: !!own } : null;
      const tieHTML = ties.map(t => `<div class="m"><b>${esc(byId[t.participant].name)}</b>${t.path.length
        ? `: ${t.path.map((x, i) => `${REL[x.relation] || x.relation} ${i === t.path.length - 1 ? `this ${ECH[u.echelon] || "unit"}` : esc(unitName(x.other))} (${EV.cite(x.cite)})`).join(", ")} on ${esc(d3.utcFormat("%-d %B")(new Date(SITMAP.meta.date)))}`
        : ": this symbol, a subject here"}</div>`).join("");
      const g = gFront.append("a").attr("href", SITMAP.meta.cite.href).attr("target", "_blank").attr("rel", "noopener")
        .append("g").attr("class", "mk unit").attr("transform", `translate(${P(u.lon, u.lat).map(v => v.toFixed(1))})`);
      EV.unitSymbol(g, u, HATCH, tie);
      g.append("rect").attr("x", -14).attr("y", -12).attr("width", 28).attr("height", 22).attr("fill", "transparent");
      g.on("mouseenter", ev => EV.showTip(ev, `<div class="v">${esc(E.nation(u.of))} ${esc(ECH[u.echelon] || u.echelon)} <span class="typed">${esc(u.label)}</span>${u.arm && u.arm !== "unread" ? ` <i>(${esc(u.arm)})</i>` : ""}</div>`
        + `<div class="k">${esc(SITMAP.meta.cite.source_title)} · situation at ${esc(FRONT_HOUR)}</div>`
        + tieHTML + `<div class="m">${u.opposed ? "Where the US army group placed it: its intelligence picture of the day, not the unit's own record." : "Where the army group placed its own unit that day."} A symbol stands in its unit's area, not at a position.</div>`
        + `<div class="i">Traced from the scan (the fit ± ${esc(SITMAP.meta.fit_km)} km) · click for the map</div>`))
        .on("mousemove", EV.moveTip).on("mouseleave", EV.hideTip);
    });
    drawListed();   // the day's list, under the map
  }
  // each river's name once, along its longest stretch in view, reading left to right (or down, for one running north and
  // south), as a map letters water (in italics, spaced), where that stretch is clearest of the marks
  function drawRiverNames(busy) {
    gRelief.selectAll(".river-names").remove();
    const names = gRelief.append("g").attr("class", "river-names"), longest = {};
    RIVERS.flatMap(fc => fc.features).forEach(f => {
      const pts = f.geometry.coordinates.map(c => P(c[0], c[1])).filter(([x, y]) => x > 20 && x < W - 20 && y > 20 && y < H - 20);
      const len = d3.sum(pts.slice(1), (q, i) => Math.hypot(q[0] - pts[i][0], q[1] - pts[i][1]));
      const name = f.properties.name;
      if (name && len > 160 && len > (longest[name]?.len || 0)) longest[name] = { len, pts };
    });
    Object.entries(longest).forEach(([name, { len, pts }], i) => {
      const [a, b] = [pts[0], pts[pts.length - 1]];
      const run = Math.abs(b[0] - a[0]) >= Math.abs(b[1] - a[1]) ? (b[0] < a[0] ? [...pts].reverse() : pts) : (b[1] < a[1] ? [...pts].reverse() : pts);
      // the clearest place along it for a name about 60 px long
      const along = [0], need = name.length * 11;
      run.slice(1).forEach((q, k) => along.push(along[k] + Math.hypot(q[0] - run[k][0], q[1] - run[k][1])));
      const at = o => run[Math.max(0, d3.bisectLeft(along, o) - 1)];
      let off = len * 0.3, clear = -1;
      for (let o = 20; o < len - need - 20; o += 15) {
        const c = d3.min([0, 0.5, 1].map(f => at(o + f * need)), q => d3.min(busy, b2 => Math.hypot(b2[0] - q[0], b2[1] - q[1])) ?? 999);
        if (c > clear) { clear = c; off = o; }
      }
      names.append("path").attr("id", `river-${i}`).attr("d", d3.line().curve(d3.curveBasis)(run)).attr("fill", "none");
      names.append("text").attr("class", "river-name").attr("dy", -5).append("textPath").attr("href", `#river-${i}`).attr("startOffset", off.toFixed(0)).text(name);
    });
  }
  // which side is whose: each side's mark (EV.insignia) and its name, on its side of the front (Engage.frontSide), where
  // the map is clearest within a few miles of the line: away from the symbols, the stations and the places
  // the map's list (the enemy divisions it lists as facing the bridgehead), under the map on the page, not over the
  // drawing: its symbols in the order the map lists them, each with its designation as written; a list, not positions
  const overlays = () => {   // the map's own controls over the drawing, in the svg's pixels: the side marks keep clear of them
    const at = svg.node().getBoundingClientRect();
    return [...document.querySelectorAll(".map-box .scalebar, .map-box .zoom-btns")].filter(el => !el.hidden)
      .map(el => { const r = el.getBoundingClientRect(); return [r.left - at.left, r.top - at.top, r.right - at.left, r.bottom - at.top]; });
  };
  const LISTED = document.createElement("div");
  LISTED.className = "sitmap-list";
  LISTED.hidden = true;
  document.querySelector(".map-box").after(LISTED);
  function drawListed() {
    const L = SITMAP ? [...SITMAP.listed].sort((a, b) => a.y - b.y || a.x - b.x) : [];
    LISTED.hidden = !L.length;
    if (!L.length) return;
    const sym = u => { const w = 24 + String(u.label).length * 6.4, el = d3.create("svg").attr("width", w * 1.4).attr("height", 34).attr("viewBox", `-12 -14 ${w} 26`);
      EV.unitSymbol(el.append("g"), u, HATCH); return el.node().outerHTML; };
    // a list the fronts README names has its words; any other (a box or margin note the README doesn't name yet) is
    // shown together, as listed and not placed, without its working name
    const items = us => `<div class="items">${us.map(u => `<span title="${esc(E.nation(u.of))} ${esc(u.label)}: listed, not placed">${sym(u)}</span>`).join("")}</div>`;
    const known = L.filter(u => u.list === "bridgehead"), other = L.filter(u => u.list !== "bridgehead");
    LISTED.innerHTML = (known.length ? `<p><i>Facing the bridgehead, as the map at ${esc(FRONT_HOUR)} lists them</i> (a list beside the bridgehead on the map, not positions):</p>${items(known)}` : "")
      + (other.length ? `<p><i>Listed elsewhere on the map at ${esc(FRONT_HOUR)}</i> (in a box or a note, not at a position):</p>${items(other)}` : "");
  }
  const busyPoints = () => [...(FRONT ? FRONT_UNITS.map(u => P(u.lon, u.lat)) : []),
    ...overlays().flatMap(([x0, y0, x1, y1]) => d3.range(x0, x1 + 1, 16).flatMap(x => d3.range(y0, y1 + 1, 16).map(y => [x, y]))), ...Object.values(STATIONS).flat().map(r => P(r.lon, r.lat)),
    ...D.positions.filter(r => r.lat != null).map(r => P(r.lon, r.lat))];
  // which side is whose: each side's mark (EV.insignia) and its name. One place for each, chosen once for every day's map
  // (on its side of the front in all of them, Engage.frontSide; clear of all their symbols, the stations and the places;
  // near the line), so stepping from day to day never moves it: it marks a side, not anything at that spot. Under the
  // map's own side, the map's hour, where nothing else on the map gives it (a clock that plays); the stepper
  // gives the day where there is one.
  let sidesAt = null;   // [[x, y, side], ...] for the current zoom, kept while the day changes
  function drawSides(fresh = false) {
    gFront.selectAll(".side").remove();
    if (!FRONT || !proj) { drawRiverNames(busyPoints()); return; }
    const own = SITMAPS.flatMap(S => S.placed).find(u => !u.opposed)?.of, enemy = SITMAPS.flatMap(S => S.placed).find(u => u.opposed)?.of;
    const shown = SITMAPS;   // every day's map: the page can show each
    if (fresh || !sidesAt) {
      const lines = shown.map(S => S.runs.map(r => r.map(c => P(c[0], c[1]))));
      const toLine = (line, [x, y]) => d3.min(line.flatMap(r => r.slice(1).map((b, i) => {
        const a = r[i], dx = b[0] - a[0], dy = b[1] - a[1], L2 = dx * dx + dy * dy || 1, u = Math.max(0, Math.min(1, ((x - a[0]) * dx + (y - a[1]) * dy) / L2));
        return Math.hypot(x - a[0] - u * dx, y - a[1] - u * dy);
      }))) ?? 999;
      const busy = [...shown.flatMap(S => S.placed.map(u => P(u.lon, u.lat))), ...busyPoints()];
      const rows = side => (side === -1 && !STEPPER ? [0, 26, 40] : [0, 26]), half = side => (side === -1 && !STEPPER ? 70 : 14);
      sidesAt = [];
      [-1, 1].forEach(side => {
        let best = null;
        for (let y = 40; y < H - 60; y += 12) for (let x = 40 + half(side); x < W - 60 - half(side); x += 12) {
          const ds = lines.map(l => toLine(l, [x, y]));
          if (Math.min(...ds) < 40 || Math.min(...ds) > 160) continue;
          const ll = proj.invert([x, y]);
          if (!shown.every(S => E.frontSide(S.runs, ll) === side)) continue;
          const clear = d3.min(rows(side).flatMap(r => [x - half(side), x, x + half(side)].map(cx => [cx, y + r])),
            ([cx, cy]) => d3.min(busy, q => Math.hypot(q[0] - cx, (q[1] - cy) * 1.6)) ?? 999);
          const score = Math.min(clear, 90) - y * 0.15;   // clear ground first, then the top of the map
          if (clear >= 26 && (!best || score > best.score)) best = { x, y, score };
        }
        if (best) sidesAt.push([best.x, best.y, side]);
      });
    }
    const busy = busyPoints();
    sidesAt.forEach(([x, y, side]) => {
      const of = side === -1 ? own : enemy;
      if (!of) return;
      const g = gFront.append("g").attr("class", "side").attr("transform", `translate(${x},${y})`);
      EV.insignia(g, of);
      g.append("text").attr("class", "side-name").attr("y", 26).attr("text-anchor", "middle").text(E.nation(of));
      if (side === -1 && !STEPPER) g.append("text").attr("class", "front-date").attr("y", 40).attr("text-anchor", "middle").text(`the front at ${FRONT_HOUR}`);
      busy.push([x, y], [x, y + 22], [x, y + 36]);
    });
    drawRiverNames(busy);
  }
  // each followed unit's stations (its own record) from a week before the window to its end, joined straight and dashed
  // (where it went between them is not recorded), the days before lighter, an arrowhead at the last; each dot links to its
  // page, and gives its date on hover (the day shown is the stepper's or the map's, so the line carries no dates)
  const dm = d3.utcFormat("%-d %b"), dayOf = d3.utcFormat("%Y-%m-%d");
  // to what day the ways are drawn: with a clock, to the clock's day; with a situation map chosen on the map, to the
  // map's day, so the picture is one moment; otherwise all of them
  const waysTo = () => PLAYS ? dayOf(new Date(t)) : SITMAPS.length && STEPPER ? SITMAP.meta.date : "9999";
  let waysDrawn = null;
  function drawWays(limit = waysTo()) {
    waysDrawn = limit;
    gWay.selectAll("*").remove();
    PARTS.forEach(p => {
      const rows = (STATIONS[p.id] || []).filter(r => r.date <= limit);
      if (!rows.length) return;
      const pts = rows.map(r => P(r.lon, r.lat)), c = SUBJECT_COLOUR[p.id] || colour(p.id);
      const k = rows.findIndex(r => r.inside), split = k < 0 ? rows.length - 1 : k;
      if (split > 0) gWay.append("path").attr("class", "way before").attr("stroke", c).attr("d", d3.line()(pts.slice(0, split + 1)));
      if (split < pts.length - 1) gWay.append("path").attr("class", "way").attr("stroke", c).attr("d", d3.line()(pts.slice(split)));
      // the arrowhead, along the last leg that has a length
      let j = pts.length - 1;
      while (j > 0 && Math.hypot(pts[j][0] - pts[j - 1][0], pts[j][1] - pts[j - 1][1]) < 1) j--;
      if (j > 0) {
        const [bx, by] = pts[pts.length - 1], [ax, ay] = pts[j - 1], a = Math.atan2(by - ay, bx - ax) * 180 / Math.PI;
        gWay.append("path").attr("d", "M0,0L-9,-4.5L-9,4.5Z").attr("fill", c).attr("transform", `translate(${bx.toFixed(1)},${by.toFixed(1)}) rotate(${a.toFixed(1)}) translate(-4,0)`);
      }
      rows.forEach((r, i) => {
        const g = gWay.append("a").attr("href", r.cite.href || null).attr("target", "_blank").attr("rel", "noopener")
          .append("g").attr("class", "mk").attr("transform", `translate(${pts[i].map(v => v.toFixed(1))})`);
        g.append("circle").attr("r", 4.6).attr("fill", "var(--surface)");
        g.append("circle").attr("r", 3.2).attr("fill", c).attr("fill-opacity", r.inside ? 1 : 0.6);
        g.append("circle").attr("r", 9).attr("fill", "transparent");
        g.on("mouseenter", ev => EV.showTip(ev, `<div class="v">${esc(p.name)} · ${esc(dm(new Date(r.date)))}</div><div class="k">${esc(r.place)}${r.precision ? " · " + esc(r.precision) : ""}</div><div class="m">${esc(r.words)}</div><div class="i">${esc(r.cite.source_title || "")} ${esc(r.cite.label || "")} · click for the page</div>`))
          .on("mousemove", EV.moveTip).on("mouseleave", EV.hideTip);
      });

    });
  }
  // a land frame (no followed ship or boat: the Army's) in statute miles, as its reports give them, and kilometres; a sea
  // frame in nautical miles
  const ON_LAND = !PARTS.some(p => p.track);
  const ruler = scaleBar(document.querySelector(".map-box"), { units: ON_LAND ? ["mi", "km"] : ["nm"] });
  const P = (lon, lat) => proj([lon, lat]);
  if (!D.box) document.querySelector(".map-box").hidden = true;

  // routes.yml: paths through the air as the records give them, each in its side's ink: a course typed on a form (solid,
  // drawn back from the position it was typed at, for a length that is ours), a squadron's sketch (dashed), a straight
  // line between two places where no record gives the path (dotted). An arrowhead at the end where the direction is sure.
  const ROUTE_WORD = { reported: "as the record types it", sketched: "as a sketch map draws it", inferred: "inferred: no record gives the path" };
  function drawRoutes() {
    gRoute.selectAll("*").remove();
    (D.routes || []).forEach(r => {
      const pts = r.points.map(([lon, lat]) => P(lon, lat)), c = (r.actor && SUBJECT_COLOUR[r.actor]) || inkOf(r);
      const g = gRoute.append("g").attr("class", "route");
      // an aircraft's path: chevrons along it, pointing the way it flew, so air reads apart from a unit's moves on the ground
      if (r.by === "air") airChevrons(g, pts, c, r.arrow);
      g.append("path").attr("d", d3.line()(pts)).attr("fill", "none").attr("stroke", c).attr("stroke-linecap", "round")
        .attr("stroke-width", r.basis === "reported" ? 2.2 : 1.6).attr("stroke-dasharray", ROUTE_DASH[r.basis]);
      if (r.arrow) {
        const [bx, by] = pts[pts.length - 1], [ax, ay] = pts[pts.length - 2], a = Math.atan2(by - ay, bx - ax) * 180 / Math.PI;
        g.append("path").attr("d", "M0,0L-8,-4L-8,4Z").attr("fill", c).attr("transform", `translate(${bx.toFixed(1)},${by.toFixed(1)}) rotate(${a.toFixed(1)}) translate(-3,0)`);
      }
      g.append("path").attr("d", d3.line()(pts)).attr("fill", "none").attr("stroke", "transparent").attr("stroke-width", 12)
        .on("mouseenter", ev => EV.showTip(ev, `<div class="v">${esc(r.label)}</div><div class="k">${r.time ? esc(r.time) + " · " : ""}${esc(ROUTE_WORD[r.basis] || r.basis)}</div><div class="m">${esc(r.resolved)}${r.note ? ". " + esc(r.note) : ""}</div><div class="i">${esc(r.source)}</div>`))
        .on("mousemove", EV.moveTip).on("mouseleave", EV.hideTip)
        .on("click", () => { if (r.cite && r.cite.href) window.open(r.cite.href, "_blank", "noopener"); });
    });
  }

  // chevrons every CHEVRON px along a polyline (clear of an arrowhead at its end), each turned to its segment
  const CHEVRON = 30;
  function airChevrons(g, pts, c, arrow) {
    const segs = d3.pairs(pts).map(([a, b]) => ({ a, b, len: Math.hypot(b[0] - a[0], b[1] - a[1]) })), total = d3.sum(segs, d => d.len);
    for (let at = CHEVRON / 2; at < total - (arrow ? 16 : 6); at += CHEVRON) {
      let rest = at, sg = segs[0];
      for (sg of segs) { if (rest <= sg.len) break; rest -= sg.len; }
      if (!sg.len) continue;
      const t = rest / sg.len, x = sg.a[0] + t * (sg.b[0] - sg.a[0]), y = sg.a[1] + t * (sg.b[1] - sg.a[1]);
      const deg = Math.atan2(sg.b[1] - sg.a[1], sg.b[0] - sg.a[0]) * 180 / Math.PI;
      g.append("path").attr("class", "chevron").attr("d", "M-3,-4L1.5,0L-3,4").attr("stroke", c)
        .attr("transform", `translate(${x.toFixed(1)},${y.toFixed(1)}) rotate(${deg.toFixed(1)})`);
    }
  }

  // reach.yml: a weapon's range as the manual gives it, a circle round where the battery was, in the side's ink; dashed
  // where the battery's place or its weapon is not its own record's (assumed, inferred). Labelled with the weapon and range.
  function drawRings() {
    gRing.selectAll("*").remove();
    const path = d3.geoPath(proj);
    (D.rings || []).forEach(r => {
      const c = (r.actor && SUBJECT_COLOUR[r.actor]) || inkOf(r), circle = d3.geoCircle().center([r.lon, r.lat]).radius(r.km / 111.195).precision(2)();
      const g = gRing.append("g").attr("class", "ring");
      g.append("path").attr("d", path(circle)).attr("fill", c).attr("fill-opacity", 0.05).attr("stroke", c).attr("stroke-width", 1.2)
        .attr("stroke-dasharray", r.basis === "reported" ? null : "6 3");
      // labelled only where the ring is big enough on the screen to carry it (zoomed out, it would sit on the places' names)
      const [x, y] = P(r.lon, r.lat + r.km / 111.195), [, cy] = P(r.lon, r.lat);
      if (cy - y >= 34) g.append("text").attr("class", "ring-label").attr("x", x).attr("y", y - 4).attr("text-anchor", "middle").text(`${r.weapon}, ${d3.format(",")(r.range_yd)} yd`);
      g.append("path").attr("d", path(circle)).attr("fill", "none").attr("stroke", "transparent").attr("stroke-width", 10)
        .on("mouseenter", ev => EV.showTip(ev, `<div class="v">${esc(r.label)}</div><div class="k">${esc(r.weapon)} · ${d3.format(",")(r.range_yd)} yards (${r.km.toFixed(1)} km) · ${esc(r.basis)}</div><div class="m">${esc(r.note)}</div><div class="i">${esc(r.source)}</div>`))
        .on("mousemove", EV.moveTip).on("mouseleave", EV.hideTip);
    });
  }

  function drawStatic() {
    if (!D.box || document.getElementById("action").hidden) return;   // (the questions have no map: nothing to fit)
    const el = svg.node(); W = el.clientWidth; H = el.clientHeight;
    if (W < 120 || H < 120) return;   // not laid out yet (a resize in progress): a fit to nothing would draw inside out
    const b = D.box, m = Math.min(44, W * 0.06);
    // clipped to the frame (and a frame's width around it, for panning): the world's coast at this scale is otherwise megabytes
    proj = d3.geoMercator().clipExtent([[-W, -H], [2 * W, 2 * H]]).fitExtent([[m, 26], [W - m, H - 34]], { type: "MultiPoint", coordinates: [[b[0], b[1]], [b[2], b[3]], [b[0], b[3]], [b[2], b[1]]] });
    view.bound(W, H);
    BASE = { scale: proj.scale(), translate: proj.translate() };   // the fit before the reader's zoom, for zoomToBox
    mapZoom.scaled(proj, BASE, view.transform());
    ruler.update(p => proj.invert(p));
    gLand.selectAll("path").data([LAND]).join("path").attr("class", "land").attr("d", d3.geoPath(proj));
    EV.graticule(gGrat, proj, W, H);
    drawBase();
    const inView = ([x, y]) => x > 30 && x < W - 30 && y > 24 && y < H - 24;
    drawFront(inView);
    drawWays();
    drawRings();
    drawRoutes();
    drawSides(true);
    gPlace.selectAll("*").remove();
    D.places.filter(p => inView(P(p.lon, p.lat))).forEach(p => gPlace.append("text").attr("class", "place")
      .attr("x", P(p.lon, p.lat)[0]).attr("y", P(p.lon, p.lat)[1]).attr("text-anchor", "middle").style("font-size", p.small ? "10px" : null).text(p.name));
    drawPath();
    drawMarks();
    drawCourses();
    if (OVERVIEW) { const a = proj.invert([0, H]), b = proj.invert([W, 0]); OVERVIEW.view([[a[0], a[1]], [b[0], b[1]]]); }
  }
  // the convoy's course and speed at each attack, as the sheet types it: an arrow in the convoy's ink, from where it was
  function drawCourses() {
    const arrow = d => { const [x, y] = P(...d.at), end = E.offset(d.at[0], d.at[1], d.course, d.kts), [x2, y2] = P(...end);
      const a = Math.atan2(y2 - y, x2 - x), h = 6;
      return `M${x},${y}L${x2},${y2}M${x2 - h * Math.cos(a - 0.45)},${y2 - h * Math.sin(a - 0.45)}L${x2},${y2}L${x2 - h * Math.cos(a + 0.45)},${y2 - h * Math.sin(a + 0.45)}`; };
    gCourse.selectAll("g").data(COURSES).join(enter => { const g = enter.append("g").attr("class", "course"); g.append("path").attr("class", "course-halo"); g.append("path").attr("class", "course-line"); g.append("path").attr("class", "course-hit"); return g; })
      .call(g => g.selectAll("path").attr("d", function () { return arrow(d3.select(this.parentNode).datum()); }))
      .on("mouseenter", (ev, d) => EV.showTip(ev, `<div class="v">${esc(CONVOY_NAME || "The target")}: course ${esc(String(d.course).padStart(3, "0"))}°, ${esc(d.kts)} knots</div><div class="k">${esc(nameOf(d.who))}'s ${esc(d.name)} sheet, ${esc(d.local)}</div><div class="m">${esc(nameOf(d.who))}'s estimate of the target at the moment of firing, as typed. Drawn from ${d.onPath ? "where the convoy was then, on its path as the boats saw it (the attack has no typed position)" : `${esc(nameOf(d.who))}'s attack position: the target was within the sheet's range of her`}; the length is an hour's run at that speed (ours).</div>`))
      .on("mousemove", EV.moveTip).on("mouseleave", EV.hideTip)
      .on("click", (ev, d) => { stop(); setTime(d.ms); highlightRow(d.ms); });
    gCharge.selectAll("g").data(CHARGES).join(enter => { const g = enter.append("g").attr("class", "charge");
      g.append("path").attr("d", d3.range(8).map(i => { const a = i * Math.PI / 4, r0 = i % 2 ? 2.5 : 3, r1 = i % 2 ? 6 : 8; return `M${r0 * Math.cos(a)},${r0 * Math.sin(a)}L${r1 * Math.cos(a)},${r1 * Math.sin(a)}`; }).join(""));
      g.append("circle").attr("r", 9).attr("fill", "transparent"); return g; })
      .attr("transform", d => `translate(${P(...d.at).map(v => v.toFixed(1))})`)
      .on("mouseenter", (ev, d) => EV.showTip(ev, `<div class="v">${esc(d.e.title)}</div><div class="k">${esc(d.e.local)}</div><div class="m">${esc(d.e.words || "")}</div><div class="i">The escorts' counter-attack as ${esc(nameOf(d.e.actor))} logged it; drawn where she was then, straight between her fixes (placed, ours)</div>`))
      .on("mousemove", EV.moveTip).on("mouseleave", EV.hideTip)
      .on("click", (ev, d) => { stop(); setTime(d.ms); highlightRow(d.ms); });
    showByClock();
  }
  function showByClock() {
    gCourse.selectAll("g.course").classed("future", d => PLAYS && d.ms > t);
    gCharge.selectAll("g.charge").classed("future", d => PLAYS && d.ms > t);
  }

  // the convoy's observed path, dotted (ours; the legend says so), as far as the clock
  function drawPath() {
    const upTo = PLAYS ? PATH.filter(p => E.T(p.utc) <= t) : PATH;
    gPath.selectAll("path").data(upTo.length > 1 ? [upTo] : []).join("path").attr("class", "trk observed")
      .attr("d", d3.line().x(p => P(p.lon, p.lat)[0]).y(p => P(p.lon, p.lat)[1]));
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
    // a place's label only where it has room: two places a few pixels apart (a bridge and its town) would print over
    // each other, so the second keeps its mark and gives its name on hover
    const taken = [];
    // the label as drawn: its own box, so a long italic label isn't guessed short
    const roomFor = (d, node) => {
      const bb = node.getBBox(), [x, y] = P(d.lon, d.lat), b = [x + bb.x - 2, y + bb.y - 1, x + bb.x + bb.width + 2, y + bb.y + bb.height + 1];
      if (taken.some(t => b[0] < t[2] && t[0] < b[2] && b[1] < t[3] && t[1] < b[3])) return false;
      taken.push(b); return true;
    };
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
        const tx = g.append("text").attr("class", "port").attr("x", Math.min(0, x2) + 4).attr("y", Math.min(0, y2) - 5).text(String(d.r.label).split(":")[0]);
        if (!roomFor(d, tx.node())) tx.remove();
      } else if (d.k === "pos" && d.r.kind === "target") {
        // a bombing target the record names: a ring and its cross, in the ink of the side it belongs to
        const c = inkOf(d.r);
        g.append("circle").attr("r", 7).attr("fill", "var(--surface)").attr("stroke", c).attr("stroke-width", 1.6);
        g.append("circle").attr("r", 2.2).attr("fill", c);
        g.append("path").attr("d", "M-10,0H-4M4,0H10M0,-10V-4M0,4V10").attr("stroke", c).attr("stroke-width", 1.6);
        const tx = g.append("text").attr("class", "port").attr("x", 11).attr("y", -7).text(String(d.r.label).split(":")[0]);
        if (!roomFor(d, tx.node())) tx.remove();
      } else if (d.k === "pos") {
        g.append("rect").attr("x", -3).attr("y", -3).attr("width", 6).attr("height", 6).attr("fill", inkOf(d.r))
          .attr("fill-opacity", d.r.basis === "assumed" || d.r.basis === "approx" || d.r.basis === "hand-placed" ? 0.35 : 1);
        // few: labelled (many: on hover); a landmark (a 1942 sheet's name) only close in, where the names have room
        if (D.positions.length <= 15 && !(d.r.kind === "landmark" && view.transform().k < 4)) {
          const tx = g.append("text").attr("class", "port").attr("x", 6).attr("y", -5).text(String(d.r.label).split(":")[0]);
          if (!roomFor(d, tx.node())) tx.remove();
        }
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

  // another day's map in the last one's place: a step, never a glide (between two sheets nothing is drawn that neither
  // gives), the old faded out under the new
  function switchSitmap(S) {
    if (!proj) { useSitmap(S); return; }
    const old = gFront.node().cloneNode(true);
    gFront.node().parentNode.insertBefore(old, gFront.node());
    d3.select(old).attr("pointer-events", "none").transition().duration(reduced ? 0 : 500).attr("opacity", 0).remove();
    useSitmap(S);
    drawFront(([x, y]) => x > 30 && x < W - 30 && y > 24 && y < H - 24);
    if (waysTo() !== waysDrawn) drawWays();
    drawSides();
    gFront.attr("opacity", 0).transition().duration(reduced ? 0 : 500).attr("opacity", 1);
  }
  function drawFrame() {
    if (proj && PLAYS && (STATIONS && Object.keys(STATIONS).length) && waysTo() !== waysDrawn) drawWays();
    // the clock passing a sheet's hour: that day's front and symbols take the last one's place (a step, never a glide:
    // between two sheets nothing is drawn that neither gives), the old faded out under the new
    if (proj && PLAYS && SITMAPS.length > 1 && sitmapAt(t) !== SITMAP) switchSitmap(sitmapAt(t));
    if (proj) {
      if (PLAYS) drawPath();
      const line = d3.line().x(p => P(...p)[0]).y(p => P(...p)[1]);
      const rows = [], nows = [];
      TRACKED.forEach(p => {
        const pts = D.tracks[p.id], now = E.posAt(pts, t);
        // the track cut at the clock and at each change of state in the boat's depth log (thin where she was down)
        const cuts = [...pts.map(q => E.T(q.utc)), ...(DIVES[p.id] || []).map(x => E.T(x.utc)), ...(now ? [t] : [])]
          .filter(ms => ms >= E.T(pts[0].utc) && ms <= E.T(pts[pts.length - 1].utc));
        const times = [...new Set(cuts)].sort((a, b) => a - b);
        d3.pairs(times).forEach(([a, b]) => {
          const st = stateAt(p.id, a), under = st && st.state === "submerged";
          rows.push({ id: p.id, cls: (PLAYS && a >= t ? "ahead" : "past") + (under ? " under" : ""), pts: [E.posAt(pts, a), E.posAt(pts, b)] });
        });
        if (now && PLAYS) nows.push({ p, now, st: stateAt(p.id, t) });   // the "now" dot is the clock's
      });
      gTrk.selectAll("path").data(rows).join("path").attr("class", d => "trk " + d.cls).attr("stroke", d => colour(d.id)).attr("d", d => d.pts.length > 1 ? line(d.pts) : null);
      showByClock();
      // the convoy where the boats saw it, at the clock: hatched (ours), with its name
      const cnow = PLAYS ? convoyAt(t) : null;
      const cg = gConvoy.selectAll("g").data(cnow ? [cnow] : []).join(enter => { const g = enter.append("g").attr("class", "convoy-now");
        g.append("circle").attr("r", 7).attr("fill", HATCH).attr("stroke", "var(--japan)").attr("stroke-width", 1.4);
        g.append("text").attr("class", "now-name").attr("x", -10).attr("y", 4).attr("text-anchor", "end").text(CONVOY_NAME);
        g.append("circle").attr("r", 10).attr("fill", "transparent")
          .on("mouseenter", ev => EV.showTip(ev, `<div class="v">${esc(CONVOY_NAME)}, at the clock</div><div class="i">Where the convoy was, straight between where the boats sighted it and where the Japanese record puts it: computed, ours, not a record</div>`))
          .on("mousemove", EV.moveTip).on("mouseleave", EV.hideTip);
        return g; });
      cg.attr("transform", d => `translate(${P(...d).map(v => v.toFixed(1))})`);
      if (OVERVIEW) OVERVIEW.here(cnow);
      gMk.selectAll("g.mk").classed("future", d => PLAYS && d.ms > t);   // no clock: everything is shown
      if (lastT !== null && t !== lastT) fires.filter(f => (f.ms > lastT && f.ms <= t && t - lastT < 3 * 3600e3) || f.ms === t).forEach(pulse);
      lastT = t;
      drawMessages();
      const ng = gNow.selectAll("g").data(nows, d => d.p.id).join(enter => {
        const g = enter.append("g");
        g.append("circle").attr("r", 10).attr("fill", d => colour(d.p.id)).attr("opacity", 0.22);
        g.append("circle").attr("class", "dot").attr("r", 5).attr("stroke-width", 2);
        return g;
      });
      // open while she is down (her depth log), filled on the surface
      ng.select("circle.dot").attr("fill", d => d.st && d.st.state === "submerged" ? "var(--surface)" : colour(d.p.id))
        .attr("stroke", d => d.st && d.st.state === "submerged" ? colour(d.p.id) : "var(--surface)");
      ng.attr("transform", d => `translate(${P(...d.now).map(v => v.toFixed(1))})`);
      gNowName.selectAll("text").data(nows, d => d.p.id).join("text").attr("class", "now-name")
        .text(d => d.p.name + (d.st ? d.st.state === "submerged" ? ` · down${d.st.depth ? ", " + d.st.depth : ""}` : " · surfaced" : ""))
        .attr("x", d => P(...d.now)[0] + 11).attr("y", d => P(...d.now)[1] - 9);
    }
    if (PLAYS) {
      document.getElementById("clock").textContent = clockText(t);
      document.getElementById("clock-own").textContent = OWN ? `${OWN_NAME[OWN] || OWN} ${clockText(t + E.zoneHours(OWN) * 3600e3)}` : "";
      document.getElementById("scrub").value = t;
    }
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

  // ---------- the frame's own figures (panels.js): each engagement's panels, after the story, a card each
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
    if (STEPPER) return drawDays();
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
      // the hours she was down, from her depth log: a wash behind her lane
      (DIVES[L.id] || []).forEach((x, k, all) => {
        if (x.state !== "submerged") return;
        let j = k + 1; while (j < all.length && all[j].state === "submerged") j++;
        if (k > 0 && all[k - 1].state === "submerged") return;   // one wash for a run of depths
        const a = Math.max(t0, E.T(x.utc)), b = Math.min(t1, j < all.length ? E.T(all[j].utc) : t1);
        if (b > a) lanes.append("rect").attr("class", "lane-under").attr("x", lx(a)).attr("width", lx(b) - lx(a)).attr("y", y - 6).attr("height", 12)
          .append("title").text(`${L.name} submerged, ${E.hhmm(a)}–${E.hhmm(b)}Z (her depth log)`);
      });
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
  function drawCursor() { const at = STEPPER ? SITMAP.ms : t; if (lx) lanes.select(".cursor").attr("x1", lx(at)).attr("x2", lx(at)); }
  lanes.on("click", ev => {
    if (!lx) return;
    if (STEPPER) { const at = +lx.invert(d3.pointer(ev)[0]); stopDays(); goDay(d3.minIndex(SITMAPS, S => Math.abs(S.ms - at))); return; }
    stop(); setTime(+lx.invert(d3.pointer(ev)[0]));
  });
  document.getElementById("scrub").addEventListener("input", e => { if (STEPPER) { stopDays(); goDay(+e.target.value); return; } stop(); setTime(+e.target.value); });

  // ---------- the day maps' timeline (a dated frame's page with several situation maps): the clocked frames'
  // bar, a day at a time. The lanes are the followed units' stations and each side's entries, each at its day (or its
  // minute where the record gives one); the axis has a tick for each map's day; the cursor is the map shown, at its hour.
  // The play steps a map at a time (never a glide); the slider and a click on the lanes go to the nearest map.
  function drawDays() {
    const laneH = 17, top = 4, dayMs = 86400e3;
    const ROWS = [...PARTS.filter(p => (STATIONS[p.id] || []).length).map(p => ({ id: p.id, name: p.short || p.name, colour: SUBJECT_COLOUR[p.id] || colour(p.id), stations: STATIONS[p.id] })), ...LANES];
    lanes.style("height", `${top + ROWS.length * laneH + 24}px`);
    lanes.selectAll("*").remove();
    // a unit's name is long ("60th Armored Infantry Battalion"): the lanes start past the longest, up to a third of the bar
    const w = lanes.node().clientWidth, probe = lanes.selectAll("text.lane-label").data(ROWS).join("text").attr("class", "lane-label").text(L => L.name);
    const left = Math.max(104, Math.min(w / 3, d3.max(probe.nodes(), n => n.getComputedTextLength()) + 14));
    const fit = name => { probe.text(name); return probe.node().getComputedTextLength() <= left - 14; };
    ROWS.forEach(L => { let name = L.name; while (!fit(name) && name.length > 4) name = name.slice(0, -2) + "…"; L.label = name; }); from = E.T(SITMAPS[0].meta.date), to = E.T(SITMAPS[SITMAPS.length - 1].meta.date) + dayMs;
    lx = d3.scaleUtc().domain([from, to]).range([left, w - 8]);
    const atDay = e => e.utc ? e.ms : E.T(dayOf(new Date(e.ms))) + dayMs / 2;   // a day's entry at the day's middle
    lanes.selectAll("*").remove();
    ROWS.forEach((L, i) => {
      const y = top + i * laneH + laneH / 2;
      lanes.append("line").attr("class", "lane-line").attr("x1", left).attr("x2", w - 8).attr("y1", y).attr("y2", y);
      lanes.append("text").attr("class", "lane-label").attr("x", 0).attr("y", y + 4).text(L.label);
      if (L.stations) L.stations.map(r => E.T(r.date) + dayMs / 2).filter(x => x >= from && x <= to)
        .forEach(x => lanes.append("circle").attr("cx", lx(x)).attr("cy", y).attr("r", 3.2).attr("fill", L.colour));
      else timed.filter(e => laneOf(e) === L.id).map(atDay).filter(x => x >= from && x <= to)
        .forEach(x => lanes.append("line").attr("x1", lx(x)).attr("x2", lx(x)).attr("y1", y - 4).attr("y2", y + 4).attr("stroke", L.colour === "var(--japan)" ? L.colour : "var(--ink-3)").attr("stroke-width", 1.5));
    });
    const axisY = top + ROWS.length * laneH + 4, ax = lanes.append("g").attr("class", "axis"), every = w < 500 ? 3 : 1;
    SITMAPS.forEach((S, i) => {
      const x = lx(S.ms);
      ax.append("line").attr("x1", x).attr("x2", x).attr("y1", top).attr("y2", axisY);
      if (i % every === 0) ax.append("text").attr("x", x).attr("y", axisY + 12).attr("text-anchor", "middle").text(E.day(S.ms));
    });
    lanes.append("line").attr("class", "cursor").attr("y1", 0).attr("y2", axisY);
    const sc = document.getElementById("scrub");
    sc.min = 0; sc.max = SITMAPS.length - 1; sc.step = 1;
    readDay();
  }
  // the readout: the map's day and hour as the sheet gives them, and its report
  function readDay() {
    document.getElementById("clock").textContent = `${SITMAP.hhmm} · ${E.day(SITMAP.ms)}`;
    document.getElementById("clock-zone").textContent = "the 12th Army Group's situation map";
    const rep = /G-3 report no\. (\d+)/.exec(SITMAP.meta.title || "");
    document.getElementById("clock-own").textContent = rep ? `to accompany its G-3 report no. ${rep[1]}` : "";
    document.getElementById("scrub").value = SITMAPS.indexOf(SITMAP);
    drawCursor();
  }
  function goDay(i) {
    if (SITMAPS[i] === SITMAP) return;
    switchSitmap(SITMAPS[i]); readDay();
    const q = new URLSearchParams(location.search); q.set("on", SITMAP.meta.date); history.replaceState(null, "", `?${q}`);
  }
  let dayTimer = 0;
  function stopDays() { clearInterval(dayTimer); dayTimer = 0; playBtn.textContent = "▶"; playBtn.setAttribute("aria-label", "Play"); }
  function playDays() {
    let i = SITMAPS.indexOf(SITMAP);
    if (i === SITMAPS.length - 1) i = -1;
    playBtn.textContent = "❚❚"; playBtn.setAttribute("aria-label", "Pause");
    const next = () => { i++; goDay(i); if (i >= SITMAPS.length - 1) stopDays(); };
    next(); dayTimer = setInterval(next, 1600);
  }

  // ---------- the chronology, when the frame has no clock to play: Engage's rows and columns, EV's drawing
  function drawChronology() {
    document.getElementById("chron-card").hidden = CLOCKED || !IN("page");
    if (CLOCKED || !IN("page")) return;
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
    card.hidden = !(IN("page") && Object.keys(D.convoys).length && series.length);
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
  // a question every answer of which comes from one source has nothing to set side by side: the board alone shows it
  const MOMENTS = [...E.pairMoments(D), ...QUESTIONS_BY.filter(q => q.columns.length > 1)];
  function drawMoments() {
    const card = document.getElementById("moments-card");
    card.hidden = !(IN("questions") && MOMENTS.length);
    if (card.hidden) return;
    const el = document.getElementById("moments");
    el.innerHTML = "";
    MOMENTS.forEach(m => { const div = document.createElement("div"); el.appendChild(div); EV.sources(div, m); });
    document.getElementById("moments-sub").textContent = `${n(MOMENTS.length, "moment")}: each column is one source, as typed, in its own language and on its own clock`;
  }
  function drawClaims() {
    document.getElementById("claims-card").hidden = !(IN("questions") && D.claims.length);
    if (D.claims.length) EV.board(document.getElementById("claims"), QUESTIONS_BY);
  }

  // ---------- order of battle: the kit's silhouettes, true relative size where the library has the class
  function drawOOB() {
    const us = PARTS.filter(p => !p.opposed && !p.convoy && !p.unit), jp = PARTS.filter(p => p.opposed && !p.convoy);
    const ownName = (D.own || []).map(E.nation).join(" and ") || "US";
    const army = PARTS.filter(p => p.unit), t0 = d3.utcFormat("%Y-%m-%d")(new Date(E.T(D.window?.from || d3.min(D.events, e => e.key)) || 0));
    // a plate: the silhouette, the name, the kind, a fate; the pack's plates (one a row, the words beside) crop each
    // silhouette to its own height (`fit`) so it sits level with its name
    const plate = (name, kind, silId, fill, extra = "", cls = "", title = "", fit = false) => `<div class="plate ${cls}" title="${esc(title)}">${EV.sil(silId, fill, { ftPx: 0.42, fit })}<div class="words"><div class="nm">${esc(name)}</div><div class="kd">${esc(kind)}</div>${extra}</div></div>`;
    const usPlates = us.map(p => plate(p.name + (p.hull ? ` (${p.hull})` : ""), [p.co, p.track ? `record: ${p.track}` : p.note].filter(Boolean).join(" · "), p.sil || EV.category(p.kind), SUBJECT_COLOUR[p.id] || colour(p.id), "", "", EV.silWords(p.sil), true));
    const convoyHTML = Object.values(D.convoys).map(c => {
      const route = [c.from, ...(c.via || []), c.to].filter(Boolean).join(" → ");
      const ships = [...c.ships].sort((a, b) => (a.role.startsWith("escort") ? 0 : 1) - (b.role.startsWith("escort") ? 0 : 1));
      return `<h3><a href="subject.html?s=${esc(c.id)}">Convoy ${esc(c.convoy)}</a> ${c.name_ja ? `<span lang="ja" data-tr="Convoy ${esc(c.convoy)}, as the Japanese records write it">${esc(c.name_ja)}</span>` : ""}</h3>
        <div class="muted" style="margin:-4px 0 10px">${esc(route)}${c.sailed ? ` · sailed ${esc(c.sailed)}` : ""}${c.cargo ? ` · ${esc(c.cargo)}` : ""}</div>
        <div class="plates">${ships.map(s => plate(s.ship, s.role, s.sil || EV.category(s.role), /sunk/.test(s.fate || "") ? "var(--ink)" : "var(--ink-3)",
          s.fate ? `<div class="fate">${esc(s.fate)}</div>` : "", s.basis === "secondary" ? "secondary" : "",
          `${EV.silWords(s.sil, s.sil_basis)}${s.basis === "secondary" ? "; named by a secondary source" : ""}`)).join("")}</div>
        <p class="muted">Silhouettes are drawn to one scale, from the class's own recognition plate where the library has it (hover for which); otherwise the kind of ship only. Italic names come from a secondary source.</p>`;
    }).join("");
    // a boat's target, or else the other side by its nationality as the records give it (German, never a bloc)
    const boatPage = PARTS.some(p => p.kind === "submarine"), otherName = [...new Set(jp.map(p => E.nation(p.of)).filter(Boolean))].join(" and ") || "The other side";
    const jpHTML = jp.length ? `<h3>${boatPage ? "The target" : esc(otherName)}</h3><div class="plates">${jp.map(p => plate(p.name, p.note || p.kind, p.sil || EV.category(p.kind), "var(--ink-3)", "", "", boatPage ? "As the boat identified it" : EV.silWords(p.sil), !boatPage)).join("")}</div>` : "";
    const armyHTML = army.length ? `<h3>The units</h3><ul class="units">${army.map(p => `<li><a href="subject.html?s=${encodeURIComponent(p.unit)}&amp;t=${t0}">${esc(p.name)}</a>${p.basis && p.basis !== "reported" ? ` <i>(${esc(p.basis)})</i>` : ""}${p.note ? ` <span class="muted">${esc(p.note)}</span>` : ""}</li>`).join("")}</ul>` : "";
    const usHTML = us.length ? `<h3>${us.length > 1 ? ownName : us[0].kind === "submarine" ? "The boat" : ownName}</h3><div class="plates">${usPlates.join("")}</div>` : "";
    document.getElementById("oob").innerHTML = `<div class="pack">${usHTML}${armyHTML}</div><div>${convoyHTML}${jpHTML}</div>`;
    document.getElementById("oob-card").hidden = IN("questions");
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
  playBtn.addEventListener("click", () => STEPPER ? (dayTimer ? stopDays() : playDays()) : playing ? stop() : play());

  // ---------- the observer view (observer.js): each attack whose data sheet is transcribed, among the figures (the
  // card measures itself when mounted, so it is mounted only where it is shown); picking one moves the clock
  const observer = IN("page") ? Observer.mount({ D, colour, nameOf, setPageTime: ms => { stop(); setTime(ms); highlightRow(ms); } }) : { pick() {} };
  const sheetOf = e => e && e.kind === "attack" && D.sheets?.[e.actor]?.[e.title.replace(" (narrative)", "")] ? e : null;
  document.getElementById("log").addEventListener("click", ev => {
    const row = ev.target.closest(".row"), e = row && D.events[[...row.parentNode.children].indexOf(row)];
    if (sheetOf(e)) observer.pick(e.actor, e.title.replace(" (narrative)", ""));
  });
  gMk.on("click.observer", ev => { const d = d3.select(ev.target.closest("g.mk")).datum(); const e = d && d.es && d.es.find(sheetOf); if (e) observer.pick(e.actor, e.title.replace(" (narrative)", "")); });

  // ---------- the depths: the switch under the lede, each saying what it holds; the outcome, who and when at the top
  // of the page (guides/OPERATIONS-VIEWER.md, 4.1). Every number is counted from the frame's own JSON, never written in.
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
  const figures = [SHEETS.length && "at the periscope", FIGURES.length && n(FIGURES.length, "figure"), CLOSING && "closing in"].filter(Boolean);
  const pageLine = ["the outcome", PLAYS || CLOCKED ? "the map with its clock" : "the map", `${n(D.events.length, "entry", "entries")} from ${kindsLine}`, STEPS.length ? "the story in steps" : "the story", ...figures].join(" · ");
  const questions = [QUESTIONS && `${n(QUESTIONS, "question")} the records leave open`, MOMENTS.length && "answers side by side", SOURCES_HTML && "how this was read"].filter(Boolean);
  document.getElementById("depths").innerHTML = [["page", "The engagement", pageLine], ["questions", "Questions and sources", questions.length ? questions.join(" · ") : "nothing listed yet"]]
    .map(([v, name, line]) => `<a href="${esc(address(id, v))}"${IN(v) ? ' aria-current="page"' : ""}>${name}<small>${esc(line)}</small></a>`).join("");
  document.getElementById("working-none").hidden = !(IN("questions") && !questions.length);
  document.getElementById("working-none").textContent = "Nothing is listed for this engagement yet: the records leave no question listed, no attack is paired with a record of the other side, and the story has no sources section.";

  if (IN("page")) {
    // the outcome, in the records' terms: the story's Outcome section, its citations links as in the story
    const outcome = secs.find(outcomeSec);
    document.getElementById("outcome").innerHTML = outcome && outcome.paras.length ? outcome.paras.map(p => `<p>${render(p.text)}</p>`).join("")
      : `<p class="none">The story has no outcome section yet: what the records say is below, and the questions they leave open are under Questions and sources.</p>`;
    // who: one row per participant, the followed subjects in their colours (the chronology's: the build's or the next
    // free of the three checked ones), the other side dashed; the hull, kind and CO as the JSON gives them; the
    // silhouette at the library's one scale, as the order of battle draws it
    const barOf = p => SUBJECT_COLOUR[p.id];
    const convoyWords = p => { const c = D.convoys[p.convoy]; return c ? [[c.from, ...(c.via || []), c.to].filter(Boolean).join(" → "), c.sailed && `sailed ${c.sailed}`, c.ships.length && `${n(c.ships.length, "ship")} named in its record`].filter(Boolean).join("; ") : ""; };
    // each subject's own page (subject.html?s=…, guides/OPERATIONS-VIEWER.md 5.2): a boat at the patrol, a unit on the day
    const first = d3.utcFormat("%Y-%m-%d")(new Date(t0));
    const journey = p => {
      if (p.track) { const [key, patrol] = p.track.split("/"); return `subject.html?s=${encodeURIComponent(key)}${patrol ? `&amp;period=${encodeURIComponent(patrol)}` : ""}`; }
      if (p.convoy) return `subject.html?s=${encodeURIComponent(p.convoy)}`;
      if (p.unit) return `subject.html?s=${encodeURIComponent(p.unit)}&amp;t=${first}`;
      return "";
    };
    document.getElementById("who").innerHTML = PARTS.map(p => {
      const bar = barOf(p);
      const words = p.convoy ? [p.kind, convoyWords(p)] : [p.hull, p.kind === "army" ? "Army unit" : p.kind, p.co, p.basis && p.basis !== "reported" && `${p.basis}: not named by the engagement's own entries`];
      const sil = p.sil ? EV.sil(p.sil, bar || "var(--ink-3)", { ftPx: 0.42, fit: true }) : "";
      const own = journey(p);
      const name = own ? `<a href="${own}" title="${esc(p.name)}: its own page, before and after this">${esc(p.name)}</a>` : esc(p.name);
      return `<div class="subj"><span class="bar${bar ? "" : " dash"}" style="${bar ? `--bar:${bar}` : ""}"></span><span class="n"><b>${name}</b> <i>${esc(words.filter(Boolean).join(" · "))}</i></span>${sil}</div>`;
    }).join("");
    // when: the window (GMT where the records give a zone) and its length; the Clocks section's first paragraph under it
    const fmt = d3.utcFormat(t1 - t0 > 3 * 86400e3 || !CLOCKED ? "%-d %B %Y" : "%-d %B %H%M"), hours = Math.round((t1 - t0) / 3600e3);
    const span = CLOCKED ? `${fmt(t0)} to ${fmt(t1)} ${D.gmt ? "GMT" : "local time (the records give no zone)"}, ${hours > 72 ? n(Math.round(hours / 24), "day") : n(hours, "hour")}`
      : `${fmt(t0)} to ${fmt(t1)}, by the records' own dates, ${n(Math.round((t1 - t0) / 86400e3) + 1, "day")}`;
    const clocks = secs.find(s => /^(the )?clocks?$/i.test(s.heading || ""));
    document.getElementById("when").innerHTML = `${esc(span)}.${clocks && clocks.paras.length ? ` <span class="k">${render(clocks.paras[0].text)}</span>` : ""}`;
    // the caption under the static map: what is drawn, and which of it is ours
    const placed = D.positions.some(r => r.lat != null && (r.basis === "assumed" || r.basis === "approx" || r.basis === "hand-placed"));
    document.getElementById("cap").textContent = [
      PLAYS && "The clock is stopped at the window's end, so every track and mark is shown; press play to watch the day pass. Each mark opens its entry.",
      TRACKED.length && "A line between a subject's reported positions is straight, and where it went between them is not recorded.",
      PATH.length > 1 && "The convoy's path, dotted, is computed from where the boats sighted it and where the Japanese record puts it: that is ours.",
      placed && "A faint square is a place we placed, not one the record gives.",
      FRONT && `The front and the units are the 12th Army Group's map at ${FRONT_HOUR}, traced: the army group's picture of that day, context for the records, not their positions.${SITMAPS.length > 1 ? (STEPPER ? ` The bar under the map steps through its maps, ${SITMAP_WHEN}, a day at a time.` : " As the clock passes noon, the next day's map takes its place.") : ""}`,
      Object.values(STATIONS).some(rows => rows.length > 1) && `A unit's dashed line joins its stations straight: where it went between them is not recorded.${FRONT && (STEPPER || PLAYS) ? " Its stations are drawn to the map's day, so the picture is one moment." : ""}`].filter(Boolean).join(" ");
    document.getElementById("cap").hidden = false;
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
