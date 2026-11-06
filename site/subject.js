// subject.html?s=<id>[&view=placement]: one journey page for every subject the records follow (a boat, a ship, an Army
// unit, a Seabee battalion, a convoy, a command), at two depths (guides/OPERATIONS-VIEWER.md 4, 5.2, 7.2).
// Reads records/subjects.json (tools/build_subjects.py: the registry of every subject, with its plain line, periods,
// organizations, engagements and record counts), and for the depths the subject's own built records (ships.json and its
// track GeoJSON, army/army.json, seabees/seabees.json, convoys/convoys.json), operations/operations.json for the war
// around it and chapter.js for a unit's stages.
//   The page (the default), top to bottom: the plain line as the eyebrow and the designation as the title; what it was;
//   a lede computed from the record; its organizations as dated rows with their pages; the strip map (one small panel
//   per stage, patrol or voyage, legs solid where its own report places both ends, dashed where an end is assumed,
//   dotted at sea); the coverage bar by month and source; the stage rows with the war around them (operations whose
//   area and dates hold a station: context, not participation; beside it, the engagements the subject or its battalion
//   was in); then the record itself, today's app for its kind as a panel (site/panels/*.js): the map with the date
//   strip and the entries list, the scan dialog shared (#scan), &period= (a patrol) and &t= (a day or a minute) carried
//   in the address; a stage row's link lands on it (#records) at that period or day.
//   Placement and leads (view=placement): how each station was placed, the speed check of the legs (computed here from
//   the fixes), the relations with their pages, the leads, the coverage by month. The old addresses
//   (view=account|records|working) open the page or the placement.
// &who=…&t=… is the family seam (links.js, `who`): a family's own script reads `who`; the kit ignores it.
(async () => {
  const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const params = new URLSearchParams(location.search);
  const ALL = await fetch(RECORDS + "subjects.json").then(r => r.json());
  const want = params.get("s");
  const S = ALL.find(x => x.id === want || x.alias === want) || ALL.find(x => x.id === "ss-385-bang") || ALL[0];
  // the two depths: the page, and how it was placed; the old three-depth addresses still arrive
  const VIEW = ["placement", "working"].includes(params.get("view")) ? "placement" : "page";
  const IN = v => VIEW === v;
  const address = (view, extra = {}) => {
    const q = new URLSearchParams({ s: S.alias || S.id });
    if (view === "placement") q.set("view", view);
    for (const [k, v] of Object.entries(extra)) if (v != null && v !== "") q.set(k, v);
    return `?${q}`;
  };
  const KIND_WORD = { boat: "a submarine", ship: "a ship", unit: "an Army unit", battalion: "a Seabee battalion", convoy: "a convoy", command: "a command" };
  const NATION = { us: "US", jp: "Japanese", de: "German", it: "Italian", uk: "British", fr: "French" };
  const fmtDay = d3.utcFormat("%-d %b %Y"), fmtMon = d3.utcFormat("%b %Y"), fmtMonth = d3.utcFormat("%B %Y");
  const T = s => s ? Date.parse(String(s).length > 10 ? s : `${s.slice(0, 10)}T12:00Z`) : NaN;
  const year = s => String(s || "").slice(0, 4);
  const years = S.first && S.last ? (year(S.first) === year(S.last) ? year(S.first) : `${year(S.first)}–${year(S.last)}`) : "";
  const n = (k, one, many = one + "s") => `${k} ${k === 1 ? one : many}`;
  const span = (a, b) => !a || !b ? "" : fmtMon(a) === fmtMon(b) ? fmtMon(a) : `${fmtMon(a)} – ${fmtMon(b)}`;
  const linkTo = (x, text) => `<a href="subject.html?s=${encodeURIComponent(x.alias || x.id)}">${text || esc(x.short || x.name)}</a>`;
  const byId = Object.fromEntries(ALL.flatMap(x => [[x.id, x], [x.alias, x]]));
  // the address keeps the reader's place: the period and the day or minute, as a panel reports them
  let last = "";
  const onState = ({ period, t } = {}) => {
    const cur = new URLSearchParams(location.search);
    if (period !== undefined) { if (period == null || period === "all") cur.delete("period"); else cur.set("period", period); }
    if (t !== undefined) { if (t == null) cur.delete("t"); else cur.set("t", t); }
    const next = `?${cur}`;
    if (next !== last && next !== location.search) { last = next; history.replaceState(null, "", next); }
  };

  // ---------- header: the plain line first, then the designation; the lede comes with the data
  document.title = IN("placement") ? `${S.short || S.name} · placement and leads` : S.short || S.name;
  document.getElementById("eyebrow").textContent = [S.plain, NATION[S.of] || S.of, years].filter(Boolean).join(" · ");
  document.getElementById("title").innerHTML = esc(S.name) + (S.name_ja ? ` <span lang="ja" data-tr="Convoy ${esc(S.short)}, as the Japanese records write it">${esc(S.name_ja)}</span>` : "");
  const sources = S.kind === "boat" ? "ship.yml" : S.kind === "ship" ? "ship.yml" : S.kind === "unit" ? "army/units.yml" : S.kind === "battalion" ? "seabees/units.yml" : S.kind === "convoy" ? "convoy.md" : "command.yml";
  // the plain line is the eyebrow (and the breadcrumb): here the record's own note on the unit, or the plain line alone
  document.getElementById("plain").innerHTML = `<b>What it was.</b> ${S.note ? esc(S.note) : esc(S.plain[0].toUpperCase() + S.plain.slice(1)) + "."} <span class="src">(${S.note ? (S.kind === "convoy" ? "its record" : "units.csv") : esc(sources)})</span> <span class="k">The plain words are ours; the designation is the records'.</span>`;

  // ---------- the record itself, under the journey: the panel for the subject's kind. Mounted first, since it needs
  // none of the journey's data (the rows, the world atlas, the operations), so it draws as soon as its own records
  // arrive; the journey fills in above it
  const HAS_RECORD = S.kind === "unit" || S.kind === "battalion" ? !!(S.records || {}).stations : S.kind === "boat" || S.kind === "ship" ? !!S.geojson : S.kind === "convoy";
  if (IN("page")) {
    const host = document.getElementById("records");
    host.hidden = false;
    document.getElementById("records-h").hidden = false;
    if (S.kind === "command") document.getElementById("lede").textContent = "The command's rows are in the records; this page draws nothing of them yet.";
    const PANEL = { boat: window.PatrolsPanel, ship: window.PatrolsPanel, unit: window.ArmyPanel, battalion: window.SeabeesPanel, convoy: window.ConvoyPanel }[S.kind];
    host.classList.add({ boat: "p-patrols", ship: "p-patrols", unit: "p-army", battalion: "p-seabees", convoy: "p-convoy", command: "p-command" }[S.kind]);
    if (PANEL && HAS_RECORD) PANEL.mount(host, S, { period: params.get("period"), t: params.get("t"), onState });
    else if (PANEL) host.innerHTML = `<p class="account-none">No record of its own is entered for this ${esc((KIND_WORD[S.kind] || S.kind).replace(/^an? /, ""))} yet${S.relations.length ? ": it is here for its relations, under Placement and leads" : ""}.</p>`;
    else host.innerHTML = `<p class="account-none">No panel draws a ${esc(KIND_WORD[S.kind] || S.kind)}'s rows yet: ${Object.entries(S.records || {}).map(([k, v]) => `${k}.csv (${v} rows)`).join(", ")} are in <a href="https://github.com/erichutchins/wwii-unit-records/tree/main/commands/comsubpac">the records</a>.</p>`;
  }

  // ---------- the subject's own built records, by kind
  const WORLD = d3.json("https://cdn.jsdelivr.net/npm/world-atlas@2/land-110m.json").then(w => topojson.feature(w, w.objects.land)).catch(() => null);
  const OPS = fetch(RECORDS + "operations/operations.json").then(r => r.ok ? r.json() : { operations: [] }).catch(() => ({ operations: [] }));
  const INDEX = fetch(RECORDS + "engagements/index.json").then(r => r.ok ? r.json() : []).catch(() => []);
  const ASSUMED = { bn: "the battalion command post, the battery assumed nearby", regt: "the Regimental HQ Battery's report, the detachment's own missing",
    hist: "the 894th's printed history, the battalion's position", aar: "Third Army's situation maps, the battalion's symbol", div: "the division's position" };
  const OWN_WORDS = { mr: "its own morning reports", btry: "its own position in the battalion's records", cp: "the order of battle's command posts",
    uaar: "its own after action reports", muster: "its muster rolls", wardiary: "the ships' war diaries", ncbhist: "its history sheet",
    bases: "Building the Navy's Bases", mcsol: "Marines in the Central Solomons" };
  const AT_SEA = /\b(at sea|aboard|on board)\b/i;
  const sourceWords = k => ASSUMED[k] || OWN_WORDS[k] || k;
  // the same, short and without a comma, for the lede's list
  const LEDE_WORDS = { bn: "the battalion's journal", regt: "the Regimental HQ Battery's reports", hist: "the 894th's printed history", aar: "Third Army's situation maps", div: "division-level sources", btry: "the battalion's records" };
  const ledeWords = k => LEDE_WORDS[k] || OWN_WORDS[k] || k;

  // Every kind becomes one shape for the journey and the placement: `rows` (its stations or fixes in order, each with a
  // time, a point or none, whether its position is the subject's own or assumed, its source and its words), `legs`
  // between consecutive placed rows (own, assumed, sea or rail), and `stages` (the strip's panels: a unit's by chapter.js's
  // countries, a boat's by patrol, a battalion's by year, a ship's or a convoy's one).
  let rows = [], legs = [], stages = [], extra = {};
  if (S.kind === "boat" || S.kind === "ship") {
    const geo = S.geojson ? await d3.json(RECORDS + S.geojson) : { features: [] };
    const pts = geo.features.filter(f => f.geometry.type === "Point").map(f => ({ ...f.properties, lonlat: f.geometry.coordinates, t: Date.parse(f.properties.utc) })).sort((a, b) => a.t - b.t);
    rows = pts.map(p => ({ t: p.t, date: p.utc.slice(0, 10), lonlat: p.lonlat, own: !p.assumed, offtrack: !p.on_track || p.kind === "ship", kind: p.kind,
                           words: p.ref, source: p.kind, period: p.patrol, page: p.page, note: p.note }));
    const track = rows.filter(r => !r.offtrack && r.own);
    for (let i = 1; i < track.length; i++) if (track[i].period === track[i - 1].period) legs.push({ a: track[i - 1], b: track[i], coords: [track[i - 1].lonlat, track[i].lonlat], style: "own", period: track[i].period });
    stages = S.periods.map(p => ({ id: String(p.n), name: S.kind === "boat" ? `Patrol ${p.n}` : p.name, sub: p.name !== `Patrol ${p.n}` && S.kind === "boat" ? p.name : "",
      from: T(p.from), to: T(p.to), rows: rows.filter(r => r.period === p.n), legs: legs.filter(l => l.period === p.n), period: p }));
  } else if (S.kind === "unit") {
    const army = await d3.json(RECORDS + "army/army.json");
    const u = army.units.find(x => x.unit === S.id) || { stations: [], actions: [] };
    rows = u.stations.map(s => ({ t: T(s.date), date: s.date, lonlat: s.lat == null ? null : [s.lon, s.lat], own: !(s.source in ASSUMED), source: s.source, words: s.station,
                                  place: s.place, placed: s.placed, grid: s.grid, offset: s.offset, page: s.page, note: s.note, ships: s.ships || [], arrived_by: s.arrived_by || [] }));
    extra.actions = u.actions || [];
    const placed = rows.filter(r => r.lonlat);
    placed.forEach((a, i) => {
      const b = placed[i + 1];
      if (!b) return;
      const gap = rows.filter(r => !r.lonlat && r.t > a.t && r.t < b.t);
      const route = army.routes.find(rt => rt.unit === S.id && rt.from === a.date && rt.to === b.date);
      const ships = [...rows.filter(r => r.t >= a.t && r.t < b.t).flatMap(r => r.ships), ...b.arrived_by];
      const sea = route?.by === "sea" || (!route?.by && (ships.length > 0 || gap.some(r => AT_SEA.test(r.words))));
      const assumed = gap.length > 0 || !!route || /route assumed/i.test(b.note || "") || !a.own || !b.own;
      legs.push({ a, b, coords: [a.lonlat, ...(route ? route.points : []), b.lonlat], style: sea ? "sea" : route?.by === "rail" ? "rail" : assumed ? "assumed" : "own", by: route?.by || (sea ? "sea" : ""), note: route?.note || "", ships });
    });
    // stages: chapter.js's countries (Algiers to Germany), the rows before the first as home and the crossing
    const C = await Chapter.load().catch(() => null);
    const stageOf = C && C.stageOf ? r => (r.lonlat ? C.stageOf(r.lonlat) : null) : () => null;
    // (a row in no country, at sea or in Britain or the United States, stays with the run before it; the rows before the
    // first country are home, and the crossing to it; a run that comes back to a country is its own stage)
    const runs = [];
    rows.forEach(r => {
      const s = stageOf(r);
      const cur = runs[runs.length - 1];
      if (!s) { if (cur) cur.rows.push(r); else runs.push({ stage: null, rows: [r] }); return; }
      if (cur && cur.stage && cur.stage.id === s.id) cur.rows.push(r);
      else runs.push({ stage: s, rows: [r] });
    });
    stages = runs.map((run, i) => {
      const s = run.stage;
      const first = run.rows[0], lastRow = run.rows[run.rows.length - 1];
      const next = runs[i + 1]?.rows[0];
      const name = s ? s.name : runs.length > 1 ? "Home and the Atlantic" : "Home";
      const where = s ? s.where : runs.length > 1 ? "the United States, then the crossing" : "the United States";
      const legsIn = legs.filter(l => l.a.t >= first.t && l.a.t <= lastRow.t);
      return { id: s ? `${s.id}-${i}` : `home-${i}`, name, where, home: !s, stage: s, from: first.t, to: next ? next.t : lastRow.t, rows: run.rows, legs: legsIn, reading: s?.reading };
    });
  } else if (S.kind === "battalion") {
    const sb = await d3.json(RECORDS + "seabees/seabees.json");
    const urows = sb.rows.filter(r => r.unit === S.id).sort((a, b) => a.date.localeCompare(b.date) || a.id - b.id);
    rows = urows.map(r => ({ t: T(r.date), date: r.date, lonlat: r.lat == null ? null : [r.lon, r.lat], own: r.assumed !== "place", assumed: r.assumed, source: r.source, words: r.station,
                             place: r.place, part: r.part, page: (r.links[0] || {}).cite || "", note: r.note, id: r.id }));
    const byRowId = Object.fromEntries(urows.map(r => [r.id, r]));
    const voyages = sb.voyages.filter(v => v.unit === S.id);
    extra.parts = sb.parts.filter(p => p.unit === S.id);
    extra.voyages = voyages;
    extra.projects = (sb.projects || []).filter(p => p.unit === S.id);
    // one leg per step of each part's line (parts.csv), as the map draws them; a voyage's logged positions along it
    const seen = new Set();
    extra.parts.forEach(p => {
      const ids = p.ids.map(i => byRowId[i]).filter(Boolean);
      for (let i = 1; i < ids.length; i++) {
        const a = ids[i - 1], b = ids[i], key = `${a.id}-${b.id}`;
        if (seen.has(key) || a.lat == null || b.lat == null || a.place === b.place) continue;
        seen.add(key);
        const v = voyages.find(x => x.from_id === a.id && x.to_id === b.id);
        const logged = v && v.positions.filter(q => q.on_track).map(q => [q.lon, q.lat]);
        const ra = rows.find(r => r.id === a.id), rb = rows.find(r => r.id === b.id);
        legs.push({ a: ra, b: rb, coords: [[a.lon, a.lat], ...(logged || []), [b.lon, b.lat]], style: v ? "sea" : (a.assumed === "place" || b.assumed === "place") ? "assumed" : "own", voyage: v });
      }
    });
    // stages by year: a battalion's war has no countries to go by
    const ys = [...new Set(rows.map(r => year(r.date)))];
    stages = ys.map((y, i) => {
      const rs = rows.filter(r => year(r.date) === y), next = rows.find(r => year(r.date) === ys[i + 1]);
      return { id: y, name: y, where: [...new Set(rs.map(r => r.place).filter(Boolean))].slice(0, 5).join(", "), from: rs[0].t, to: next ? next.t : rs[rs.length - 1].t,
               rows: rs, legs: legs.filter(l => l.a && year(l.a.date) === y) };
    });
  } else if (S.kind === "convoy") {
    const J = await fetch(RECORDS + "convoys/convoys.json").then(r => r.json());
    const c = J.convoys.find(x => x.id === S.id) || { route: [], voyage: [], ships: [], sightings: [], hits: [], attacks: [], engagements: [] };
    extra.convoy = c;
    const N = J.lanes;
    const nodes = (c.route || []).map(id => ({ id, ...N[id] }));
    rows = c.voyage.map(v => ({ t: Engage.T(v.tokyo), date: String(v.tokyo || v.key || "").slice(0, 10), lonlat: v.place && N[v.place] ? [N[v.place].lon, N[v.place].lat] : null,
                                own: v.basis === "reported", source: v.basis, words: `${v.event}${v.place && N[v.place] ? " " + N[v.place].name : ""}${v.words ? ": " + v.words : ""}`, cite: v.cite }));
    for (let i = 1; i < nodes.length; i++) legs.push({ a: nodes[i - 1], b: nodes[i], coords: [[nodes[i - 1].lon, nodes[i - 1].lat], [nodes[i].lon, nodes[i].lat]], style: nodes[i - 1].assumed || nodes[i].assumed ? "sea" : "assumed" });
    extra.marks = [...c.sightings.map(s => ({ lonlat: [s.lon, s.lat], kind: "sighted" })), ...c.hits.map(h => ({ lonlat: [h.lon, h.lat], kind: h.mark || "miss" })), ...c.attacks.map(a => ({ lonlat: [a.lon, a.lat], kind: "attack" }))];
    stages = [{ id: "voyage", name: "The voyage", where: S.route_words, from: T(S.first), to: T(S.last || S.first), rows, legs, nodes }];
  }
  const placedRows = rows.filter(r => r.lonlat);
  const ownRows = rows.filter(r => r.own);
  const assumedRows = rows.filter(r => !r.own);
  const assumedLegs = legs.filter(l => l.style !== "own");
  const seaLegs = legs.filter(l => l.style === "sea");

  // ---------- the depths switch, with each depth's counts (every number is the records' or says it is ours)
  const recs = S.records || {};
  const recordsLine = S.kind === "unit" ? [n(recs.stations || 0, "station"), recs.actions && n(recs.actions, "action"), recs.ships && n(recs.ships, "crossing"), `${n(new Set(rows.map(r => r.source)).size, "record series")}`].filter(Boolean).join(" · ")
    : S.kind === "battalion" ? [n(recs.stations || 0, "station"), recs.parts && n(recs.parts, "part"), recs.voyages && n(recs.voyages, "voyage"), recs.projects && n(recs.projects, "project")].filter(Boolean).join(" · ")
    : S.kind === "convoy" ? [n(recs.ships || 0, "ship"), recs.stops && n(recs.stops, "stop"), recs.sightings && n(recs.sightings, "sighting", "sightings")].filter(Boolean).join(" · ")
    : S.kind === "command" ? Object.entries(recs).map(([k, v]) => `${v} ${k.replace(/_/g, " ")}`).join(" · ")
    : [n(recs.positions || 0, "position"), recs.attacks && n(recs.attacks, "attack"), recs.depths && n(recs.depths, "depth entry", "depth entries"), recs.japanese && n(recs.japanese, "Japanese record"), recs.frupac && n(recs.frupac, "FRUPAC note")].filter(Boolean).join(" · ");
  const workingLine = [assumedLegs.length && n(assumedLegs.length, "assumed leg"), assumedRows.length && `${assumedRows.length} ${S.kind === "convoy" ? "not from a record" : "assumed"}`,
    (S.kind === "unit" || S.kind === "battalion") && "the coverage", S.kind !== "convoy" && S.kind !== "command" && "the speed check", S.leads.length && n(S.leads.length, "lead")].filter(Boolean).join(" · ");
  const stagesWord = S.kind === "boat" ? n(stages.length, "patrol") : S.kind === "ship" ? "one record" : S.kind === "convoy" ? "one voyage" : n(stages.length, "stage");
  const KIND_TAB = { boat: "The boat", ship: "The ship", unit: "The unit", battalion: "The battalion", convoy: "The convoy", command: "The command" };
  document.getElementById("depths").innerHTML = [["page", KIND_TAB[S.kind] || "The subject", `the journey in ${stagesWord} · ${recordsLine || "nothing drawn yet"}`],
    ["placement", "Placement and leads", workingLine || "nothing to show yet"]]
    .map(([v, name, line]) => `<a href="${esc(address(v, { period: params.get("period"), t: params.get("t") }))}"${IN(v) ? ' aria-current="page"' : ""}>${name}<small>${esc(line)}</small></a>`).join("");

  // ---------- the breadcrumb: Subjects / the subject / its period; for a unit, its engagements before and after
  const periodWanted = params.get("period");
  const crumbPeriod = () => {
    if (S.kind === "boat" && periodWanted && periodWanted !== "all") { const p = S.periods.find(x => String(x.n) === periodWanted); return p ? `Patrol ${p.n}` : ""; }
    if (params.get("t")) return fmtDay(new Date(T(params.get("t"))));
    return "";
  };
  const crumbEl = document.getElementById("crumb");
  // (the guide's wording, 5.3: Subjects / BANG / Patrol 1; the theatre's link is in the account's "the war around" rows)
  const trail = Chapter.trail([{ href: "subjects.html", text: "Subjects" }, crumbPeriod() ? { href: address("page"), text: S.name } : S.name, crumbPeriod()]);
  const engs = S.engagements || [];
  const tNow = params.get("t") ? T(params.get("t")) : null;
  const before = tNow == null ? null : engs.filter(e => T(e.to || e.from) < tNow).pop(), after = tNow == null ? null : engs.find(e => T(e.from) > tNow);
  const seq = engs.length ? `<div class="seq">${tNow != null ? (before ? `<a rel="prev" href="engagement.html?e=${esc(before.id)}">← ${esc(before.short || before.title)}</a>` : `<span class="none">← nothing before in the engagements</span>`) : ""}<span class="what">${S.kind === "boat" || S.kind === "ship" ? "the engagements she was in" : S.kind === "convoy" ? "where the boats met it" : "the engagements it was in"}: ${engs.map(e => `<a href="engagement.html?e=${esc(e.id)}">${esc(e.short || e.title)}</a>${e.period && S.kind === "boat" ? ` <span class="dates">(patrol ${esc(e.period)})</span>` : ""}`).join(", ")}</span>${tNow != null ? (after ? `<a rel="next" href="engagement.html?e=${esc(after.id)}">${esc(after.short || after.title)} →</a>` : `<span class="none">nothing after in the engagements →</span>`) : ""}</div>` : "";
  crumbEl.innerHTML = trail + seq;
  crumbEl.hidden = false;

  // ---------- the strip map: one small panel per stage, all drawn the same way
  const strokeFor = { own: { dash: null, w: 2 }, assumed: { dash: "5 4", w: 2 }, rail: { dash: "10 3 2 3", w: 2 }, sea: { dash: "2 4", w: 1.4 } };
  function stripPanel(stage, LAND) {
    const W = 220, H = 190;
    // the panel is fitted to the stage's own positions (a leg out of it is drawn and clipped); a convoy's to its route and marks
    const own = stage.rows.filter(r => r.lonlat && !r.offtrack).map(r => r.lonlat);
    const pts = own.length ? [...own, ...(stage.nodes || []).map(nd => [nd.lon, nd.lat]), ...(S.kind === "convoy" ? (extra.marks || []).map(m => m.lonlat) : [])]
      : [...stage.legs.flatMap(l => l.coords), ...(stage.nodes || []).map(nd => [nd.lon, nd.lat])];
    const svg = d3.create("svg").attr("viewBox", `0 0 ${W} ${H}`).attr("role", "img").attr("aria-label", stage.name);
    if (pts.length < 1) { svg.append("text").attr("class", "lbl2").attr("x", 10).attr("y", H / 2).text("no position placed"); return svg.node(); }
    const lons = pts.map(p => (p[0] + 360) % 360), wide = d3.max(lons) - d3.min(lons) > 180;   // a track across the date line
    const geoPts = { type: "MultiPoint", coordinates: pts.length === 1 ? [pts[0], [pts[0][0] + 0.5, pts[0][1] + 0.5], [pts[0][0] - 0.5, pts[0][1] - 0.5]] : pts };
    const proj = d3.geoMercator().rotate([S.kind === "boat" || S.kind === "ship" || S.kind === "convoy" || S.kind === "battalion" ? -160 : 0, 0])
      .fitExtent([[18, 18], [W - 18, H - 24]], geoPts);
    const path = d3.geoPath(proj);
    svg.append("defs").append("clipPath").attr("id", `clip-${stage.id}`).append("rect").attr("width", W).attr("height", H);
    const g = svg.append("g").attr("clip-path", `url(#clip-${stage.id})`);
    const [w, nn] = proj.invert([0, 0]), [e, s] = proj.invert([W, H]);
    const spanDeg = Math.abs(e - w), step = spanDeg > 60 ? 20 : spanDeg > 20 ? 10 : spanDeg > 8 ? 2 : spanDeg > 3 ? 1 : spanDeg > 1 ? 0.5 : 0.1;
    g.append("path").attr("class", "grat").attr("d", path(d3.geoGraticule().step([step, step])()));
    if (LAND) g.append("path").attr("class", "land").attr("d", path(LAND));
    stage.legs.forEach(l => {
      const st = strokeFor[l.style] || strokeFor.own;
      g.append("path").attr("d", path({ type: "LineString", coordinates: l.coords })).attr("fill", "none").attr("stroke", "var(--c1)")
        .attr("stroke-width", st.w).attr("stroke-dasharray", st.dash).attr("stroke-linejoin", "round").attr("stroke-linecap", "round");
    });
    const shown = stage.rows.filter(r => r.lonlat && !r.offtrack);
    shown.forEach(r => {
      const [x, y] = proj(r.lonlat);
      const c = g.append("circle").attr("cx", x).attr("cy", y).attr("r", S.kind === "boat" || S.kind === "ship" ? 1.8 : 3.2);
      if (r.own) c.attr("fill", "var(--c1)").attr("class", "fix"); else c.attr("fill", "var(--page)").attr("stroke", "var(--c1)").attr("stroke-width", 1.8);
    });
    if (S.kind === "boat" || S.kind === "ship") stage.rows.filter(r => r.kind === "attack" || r.kind === "gun").forEach(r => {
      const [x, y] = proj(r.lonlat);
      g.append("path").attr("d", "M0,-5L5,0L0,5L-5,0Z").attr("transform", `translate(${x},${y})`).attr("fill", "var(--c2)").attr("stroke", "var(--page)").attr("stroke-width", 1);
    });
    (S.kind === "convoy" ? extra.marks || [] : []).forEach(m => {
      const [x, y] = proj(m.lonlat);
      if (m.kind === "sunk") g.append("path").attr("d", "M-4,-4L4,4M4,-4L-4,4").attr("transform", `translate(${x},${y})`).attr("stroke", "var(--hit)").attr("stroke-width", 2);
      else if (m.kind === "hit") g.append("circle").attr("cx", x).attr("cy", y).attr("r", 4).attr("fill", "none").attr("stroke", "var(--hit)").attr("stroke-width", 2);
      else if (m.kind === "attack") g.append("path").attr("d", "M0,-5L5,0L0,5L-5,0Z").attr("transform", `translate(${x},${y})`).attr("fill", "var(--c2)");
      else g.append("circle").attr("cx", x).attr("cy", y).attr("r", 3.5).attr("fill", "var(--page)").attr("stroke", "var(--c1)").attr("stroke-width", 1.5);
    });
    // a few labels: the first and the last place, and the most visited between them
    const labelled = new Set(), labels = [];
    const named = shown.filter(r => r.place);
    const visits = d3.rollup(named, v => v.length, r => r.place);
    const candidates = [named[0], named[named.length - 1], ...[...visits.entries()].sort((a, b) => b[1] - a[1]).map(([p]) => named.find(r => r.place === p))].filter(Boolean);
    for (const r of candidates) {
      if (labelled.has(r.place) || labels.length >= 4) continue;
      const [x, y] = proj(r.lonlat);
      if (labels.some(([lx, ly]) => Math.abs(lx - x) < 60 && Math.abs(ly - y) < 12)) continue;
      labelled.add(r.place); labels.push([x, y]);
      g.append("text").attr("class", "lbl2").attr("x", x + 5).attr("y", y - 5).text(r.place);
    }
    (stage.nodes || []).filter(nd => nd.port).forEach(nd => { const [x, y] = proj([nd.lon, nd.lat]); g.append("text").attr("class", "lbl2").attr("x", x + 5).attr("y", y - 5).text(nd.name); });
    // a scale bar at the panel's centre latitude: a round length (10, 100, 1000 km or nm)
    const midLat = (nn + s) / 2, unit = S.kind === "unit" || S.kind === "battalion" ? "km" : "nm", perDeg = unit === "km" ? 111.32 : 60;
    const kmPerPx = Math.abs(proj.invert([1, H / 2])[0] - proj.invert([0, H / 2])[0]) * perDeg * Math.cos(midLat * Math.PI / 180);
    const len = [1, 10, 100, 1000, 5000].reverse().find(v => v / kmPerPx < W * 0.5) || 1;
    svg.append("line").attr("x1", 10).attr("y1", H - 10).attr("x2", 10 + len / kmPerPx).attr("y2", H - 10).attr("stroke", "var(--ink-2)").attr("stroke-width", 1.5);
    svg.append("text").attr("class", "lbl2").attr("x", 10).attr("y", H - 14).text(`${len} ${unit}`);
    if (wide) svg.append("title").text("The track crosses the date line");
    return svg.node();
  }

  // ---------- the war around a stage: operations whose area and dates hold a station (context, not participation),
  // and the engagements beside it (the subject's own, or its battalion's, or one whose box holds a station in its window)
  const inBox = ([lon, lat], [w, s, e, nn]) => lon >= w && lon <= e && lat >= s && lat <= nn;
  function warAround(stage, ops, index) {
    const placed = stage.rows.filter(r => r.lonlat);
    const campaigns = ops.filter(o => o.kind !== "theater" && o.area).filter(o => {
      const from = T(o.from), to = o.to ? T(o.to) : Infinity;
      return placed.some(r => inBox(r.lonlat, o.area) && r.t <= to && (stage.to >= from));
    }).map(o => ({ ...o, when: `${fmtDay(new Date(T(o.from)))}${o.to ? ` – ${fmtDay(new Date(T(o.to)))}` : " on"}` }));
    const mine = engs.filter(e => T(e.from) <= stage.to && T(e.to || e.from) >= stage.from);
    const mineIds = new Set(mine.map(e => e.id));
    // the same battalion's or regiment's: the other subjects that share a parent in relations.csv
    const parents = new Set(S.relations.filter(r => r.dir === "of" && r.relation === "part_of").map(r => r.other));
    const kin = ALL.filter(x => x.id !== S.id && x.kind === S.kind && x.relations.some(r => r.dir === "of" && r.relation === "part_of" && parents.has(r.other)));
    const kinEngs = kin.flatMap(k => (k.engagements || []).map(e => ({ ...e, who: k }))).filter(e => !mineIds.has(e.id) && T(e.from) <= stage.to && T(e.to || e.from) >= stage.from);
    // an engagement near a station in its window, the subject not named in it
    const near = index.filter(x => x.box && !mineIds.has(x.id) && !kinEngs.some(k => k.id === x.id)).filter(x => {
      const from = T(x.from), to = T(x.to || x.from);
      const inForce = stage.rows.filter((r, i) => r.lonlat && r.t <= to && (stage.rows[i + 1] ? stage.rows[i + 1].t : stage.to) >= from);
      return inForce.some(r => inBox(r.lonlat, [x.box[0] - 0.15, x.box[1] - 0.15, x.box[2] + 0.15, x.box[3] + 0.15]));
    });
    return { campaigns, mine, kinEngs, near };
  }

  // where a stage row lands: the record below, at that patrol or day
  const recordAt = s => address("page", S.kind === "boat" ? { period: s.id } : S.kind === "unit" || S.kind === "battalion" ? { t: new Date(s.from).toISOString().slice(0, 10) } : {}) + "#records";
  if (IN("page")) {
    const [LAND, ops, index] = await Promise.all([WORLD, OPS, INDEX]);
    const OPLIST = ops.operations || [];
    const host = document.getElementById("account");
    host.hidden = false;
    // the lede, computed from the record
    const firstPlace = placedRows[0]?.place || "", lastPlace = placedRows[placedRows.length - 1]?.place || "";
    const seriesWords = [...new Set(rows.map(r => r.source))].map(ledeWords).filter(Boolean);
    const lede = S.kind === "unit" ? `Where the unit was, day by day, from ${seriesWords.join(", ").replace(/, ([^,]*)$/, " and $1")}${firstPlace && lastPlace ? `: ${firstPlace} to ${lastPlace}` : ""}, ${span(new Date(S.first), new Date(S.last))}. ${n(rows.length, "change of station", "changes of station")}${seaLegs.length ? `, ${n(seaLegs.length, "sea crossing")}` : ""}${stages.filter(s => s.stage).length > 1 ? `, ${n(stages.filter(s => s.stage).length, "country", "countries")} after the Atlantic` : ""}.`
      : S.kind === "battalion" ? `Where the battalion, and each part of it, was, from ${seriesWords.join(", ").replace(/, ([^,]*)$/, " and $1")}${firstPlace && lastPlace ? `: ${firstPlace} to ${lastPlace}` : ""}, ${span(new Date(S.first), new Date(S.last))}. ${n(rows.length, "station")}, ${n(recs.parts || 0, "part")} that split off and rejoined, ${n((extra.voyages || []).length, "voyage")}.`
      : S.kind === "boat" ? `Every position she reported in ${n(S.periods.length, "war patrol report")}, ${span(new Date(S.first), new Date(S.last))}: ${n(rows.filter(r => !r.offtrack).length, "fix", "fixes")} on the track, ${n(recs.attacks || 0, "attack")}${recs.depths ? `, ${n(recs.depths, "depth entry", "depth entries")}` : ""}${recs.japanese ? `, and the Japanese record of ${n(recs.japanese, "entry", "entries")} beside them` : ""}.`
      : S.kind === "ship" ? `Every position in her war diary, ${span(new Date(S.first), new Date(S.last))}: ${n(rows.filter(r => !r.offtrack).length, "fix", "fixes")} on the track${S.periods[0]?.months?.length ? `; ${n(S.periods[0].months.filter(m => m.status === "mapped" || m.status === "partial").length, "month")} of ${S.periods[0].months.length} in the inventory transcribed` : ""}.`
      : S.kind === "convoy" ? `${S.route_words}${S.first ? `, sailed ${fmtDay(new Date(T(S.first)))}` : ""}: ${n(recs.ships || 0, "ship")} named (${recs.reported || 0} by a Japanese record, ${recs.secondary || 0} by a secondary source), ${n(recs.stops || 0, "stop")} dated, met by the boats in ${n(engs.length, "engagement")}. The route is drawn through assumed waypoints, and the convoy's path as the boats saw it is ours.`
      : `Its war diary for October 1944: ${Object.entries(recs).map(([k, v]) => `${v} ${k.replace(/_/g, " ")} rows`).join(", ")}; ${n(S.periods.filter(p => p.status === "available").length, "month")} more found and not transcribed.`;
    document.getElementById("lede").textContent = lede;
    document.getElementById("lede").classList.add("computed");

    // its organizations, as the records give them
    const relWords = { part_of: ["part of", "has as a part"], attached_to: ["attached to", "has attached"], under_command: ["under the command of", "commands"], took_part: ["took part in", ""],
      in_unit: ["in", ""], disposed: ["listed", ""], part: ["", "a part of it:"], in_convoy: ["", "in it:"], task_group: ["", "its task group:"] };
    const dates = r => r.from || r.to ? `${esc(r.from.replace(/^\.\./, "by ").replace(/\.\.$/, " on"))}${r.to && r.to !== r.from ? ` – ${esc(r.to.replace(/^\.\./, "by ").replace(/\.\.$/, " on"))}` : r.to === "" && r.from && !/\.\.$/.test(r.from) && r.relation !== "disposed" && r.relation !== "in_unit" && r.relation !== "in_convoy" ? " –" : ""}` : "<small>undated</small>";
    const relLine = r => {
      const [of, to] = relWords[r.relation] || [r.relation.replace(/_/g, " "), r.relation.replace(/_/g, " ")];
      const other = byId[r.other] ? linkTo(byId[r.other], esc(r.other_name)) : esc(r.other_name);
      const word = r.dir === "of" ? of : to;
      return `<span class="d">${dates(r)}</span><span>${word ? `<i>${esc(word)}</i> ` : ""}${other}${r.basis && r.basis !== "reported" ? ` <i>(${esc(r.basis)})</i>` : ""}${r.note ? ` <span class="n">${esc(r.note.length > 160 ? r.note.slice(0, 158).replace(/\s+\S*$/, "") + " …" : r.note)}</span>` : ""} ${r.cite.map(c => `<a class="src" href="${esc(c.href)}" target="_blank" rel="noopener" title="${esc(c.ref)}">(${esc(c.short)}${c.page ? ` p. ${esc(c.page.replace(/^0+/, ""))}` : ""})</a>`).join(" ")}</span>`;
    };
    const rels = S.relations.slice().sort((a, b) => (a.from || a.to || "").localeCompare(b.from || b.to || ""));
    const orgTitle = S.kind === "convoy" ? "Its ships, as the records name them" : S.kind === "command" ? "Its task organization, as the diary gives it" : S.kind === "battalion" ? "Its parts, as the records give them" : "Its organizations, as the records give them";
    const orgNone = S.kind === "unit" ? "No relation of this unit is in relations.csv yet (part of, attached to, under command); units.csv's note above says what its reports call it. A relation is added when its page is read." : "None recorded.";
    const orgHTML = `<div class="card pad"><h3>${orgTitle}</h3>${rels.length ? `<div class="org">${(rels.length > 14 ? rels.slice(0, 14) : rels).map(relLine).join("")}</div>${rels.length > 14 ? `<p class="k">and ${rels.length - 14} more, under Placement and leads.</p>` : ""}` : `<p class="account-none">${orgNone}</p>`}</div>`;

    // the strip map and its key
    const stripHTML = `<h2 class="sec">The journey, ${S.kind === "boat" ? "patrol by patrol" : S.kind === "ship" ? "as her diary gives it" : S.kind === "convoy" ? "the voyage" : "stage by stage"}</h2>
      <div class="strip${stages.length < 4 ? " few" : ""}" style="--n:${stages.length <= 5 ? Math.max(1, stages.length) : stages.length <= 6 ? 3 : stages.length <= 8 ? 4 : 5}"></div>
      <div class="strip-key">
        <span><svg width="22" height="8"><line x1="1" y1="4" x2="21" y2="4" stroke="var(--c1)" stroke-width="2"/></svg>${S.kind === "boat" || S.kind === "ship" ? "straight between her reported positions" : S.kind === "convoy" ? "straight between two ports" : "its own report places both ends"}</span>
        ${assumedLegs.some(l => l.style === "assumed") ? `<span><svg width="22" height="8"><line x1="1" y1="4" x2="21" y2="4" stroke="var(--c1)" stroke-width="2" stroke-dasharray="5 4"/></svg>an end is assumed, or the route is</span>` : ""}
        ${legs.some(l => l.style === "rail") ? `<span><svg width="22" height="8"><line x1="1" y1="4" x2="21" y2="4" stroke="var(--c1)" stroke-width="2" stroke-dasharray="10 3 2 3"/></svg>by train, the route assumed</span>` : ""}
        ${seaLegs.length ? `<span><svg width="22" height="8"><line x1="1" y1="4" x2="21" y2="4" stroke="var(--c1)" stroke-width="1.4" stroke-dasharray="2 4"/></svg>${S.kind === "convoy" ? "through an assumed waypoint" : "at sea, the way not recorded (or a ship's logged positions)"}</span>` : ""}
        ${S.kind === "unit" || S.kind === "battalion" ? `<span><svg width="10" height="10"><circle cx="5" cy="5" r="3.2" fill="var(--c1)"/></svg>station, as typed</span>${assumedRows.length ? `<span><svg width="10" height="10"><circle cx="5" cy="5" r="3.2" fill="none" stroke="var(--c1)" stroke-width="1.8"/></svg>${S.kind === "unit" ? "station assumed with a headquarters" : "position assumed: a stand-in point"}</span>` : ""}` : ""}
        ${S.kind === "boat" || S.kind === "ship" ? `<span><svg width="10" height="10"><path d="M5,0L10,5L5,10L0,5Z" fill="var(--c2)"/></svg>an attack</span>` : ""}
        ${S.kind === "convoy" ? `<span><svg width="10" height="10"><circle cx="5" cy="5" r="3.5" fill="none" stroke="var(--c1)" stroke-width="1.5"/></svg>sighted by a boat</span><span><svg width="10" height="10"><path d="M1,1L9,9M9,1L1,9" stroke="var(--hit)" stroke-width="2"/></svg>sunk (the Japanese record)</span>` : ""}
      </div>`;

    // the coverage bar by month and source (a unit's or a battalion's record)
    let covHTML = "";
    if ((S.kind === "unit" || S.kind === "battalion") && S.periods.length) {
      const cls = p => !p.source ? "gap" : p.source === "hist" ? "other" : p.assumed ? "assumed" : "own";
      const bySrc = d3.rollups(rows, v => v.length, r => r.source);
      covHTML = `<div class="cov">${S.periods.map(p => `<i class="${cls(p)}" title="${esc(fmtMonth(new Date(T(p.month + "-15"))))}: ${esc(p.stations ? `${p.stations} station${p.stations === 1 ? "" : "s"}, ${sourceWords(p.source)}` : p.source ? `no change; still placed by ${sourceWords(p.source)}` : "no station")}"></i>`).join("")}<span class="lbl">coverage, ${esc(span(new Date(S.first), new Date(S.last)))}</span></div>
        <div class="cov-key">${bySrc.map(([k, v]) => `<span><i class="${k === "hist" ? "other" : k in ASSUMED ? "assumed" : "own"}" style="${k === "hist" ? "" : ""}"></i>${esc(sourceWords(k))} (${v})${k in ASSUMED ? ", assumed" : ""}</span>`).join("")}</div>`;
    }

    // the stage rows
    const first = s => s.rows.find(r => r.words) || s.rows[0];
    const stageRows = stages.map((s, i) => {
      const w = warAround(s, OPLIST, index);
      const places = [...new Set(s.rows.filter(r => r.place).map(r => r.place))];
      const f = first(s);
      const fs = f ? `<span class="first">${S.kind === "convoy" || f.lang === "ja" ? `<span class="ja" lang="ja">` : ""}“${esc(String(f.words).length > 140 ? String(f.words).slice(0, 138) + "…" : f.words)}”${S.kind === "convoy" ? "</span>" : ""} <small>(${esc(fmtDay(new Date(f.t)))}${f.source && S.kind === "unit" && !f.own ? `, ${esc(sourceWords(f.source))}` : ""})</small></span>` : "";
      const counts = S.kind === "boat" || S.kind === "ship" ? `${n(s.rows.filter(r => !r.offtrack).length, "fix", "fixes")}${s.period ? ` · ${n(s.period.attacks || 0, "attack")}` : ""}${s.period?.co ? ` · ${esc(s.period.co)}` : ""}${s.period?.status ? ` · <i>${esc(s.period.status)}</i>` : ""}` : `${n(s.rows.length, "station")}`;
      // each operation links to its place on its theatre's page (theatre.html?t=…#op-…): the subject's way up to the theatre
      const ctx = w.campaigns.length ? `<div class="ctx">The war around it: ${w.campaigns.map(o => `<a href="${esc(Chapter.theatreHref(o.theater, `op-${o.id}`))}">${esc(o.name)}</a> (${esc(o.when)})`).join(", ")}. <i>Context, not participation.</i></div>` : "";
      const beside = [...w.mine.map(e => `<a href="engagement.html?e=${esc(e.id)}">${esc(e.short || e.title)}</a>${e.as && e.basis && e.basis !== "reported" ? ` <i>(${esc(e.basis)})</i>` : ""}`),
        ...w.kinEngs.map(e => `<a href="engagement.html?e=${esc(e.id)}">${esc(e.short || e.title)}</a> (${linkTo(e.who)}: the same ${S.kind === "unit" ? "battalion's" : "pack's"}, not ${S.kind === "boat" ? "hers" : "its own"})`),
        ...w.near.map(e => `<a href="engagement.html?e=${esc(e.id)}">${esc(e.short || e.title)}</a> (nearby, in its window; this ${S.kind === "boat" ? "boat" : "unit"} isn't named in it)`)];
      const besideHTML = beside.length ? `<div class="ctx">${w.mine.length ? "In it: " : "Beside it: "}${beside.join("; ")}.</div>` : "";
      const reading = s.reading ? `<div class="ctx"><i>Reading the records here:</i> ${s.reading.map(([h, t2, w2]) => `<a href="${esc(h)}">${esc(t2)}</a>, ${esc(w2)}`).join("; ")}</div>` : "";
      const where = S.kind === "unit" ? (places.slice(0, 7).join(", ") + (places.length > 7 ? ` … ${places[places.length - 1]}` : "")) : s.where || places.slice(0, 6).join(", ");
      const link = `<a href="${esc(recordAt(s))}">the record, below ↓</a>`;
      return `<div class="stage"><div class="when">${esc(span(new Date(s.from), new Date(s.to)) || fmtMon(new Date(s.from)))}</div><div>
        <b>${i + 1} ${esc(s.name)}</b>${s.sub ? ` <i>${esc(s.sub)}</i>` : ""}${where ? ` · ${esc(where)}` : ""} · ${counts} · ${link}<br>${fs}${ctx}${besideHTML}${reading}</div></div>`;
    }).join("");


    host.innerHTML = `${orgHTML}${stripHTML}${covHTML}<div class="stages">${stageRows}</div>`;
    const strip = host.querySelector(".strip");
    stages.forEach((s, i) => {
      const a = document.createElement("a");
      a.className = "spanel";
      a.href = recordAt(s);
      a.innerHTML = `<h3>${i + 1} ${esc(s.name)}<span>${esc(span(new Date(s.from), new Date(s.to)) || fmtMon(new Date(s.from)))} · ${S.kind === "boat" || S.kind === "ship" ? n(s.rows.filter(r => !r.offtrack).length, "fix", "fixes") : S.kind === "convoy" ? n(s.rows.length, "stop") : n(s.rows.length, "station")}</span></h3>`;
      a.append(stripPanel(s, LAND));
      strip.append(a);
    });
    document.getElementById("cap").textContent = `${S.kind === "boat" || S.kind === "ship" ? "A line between reported positions is straight, and where she went between them is not recorded." : S.kind === "convoy" ? "The route is drawn through reference waypoints, none traced from a chart: an assumption, not a track." : "A station holds until the next change; a dashed leg is drawn on an assumed route, a hollow station is a headquarters' position with the unit assumed near it."}`;
    document.getElementById("cap").hidden = false;
  }

  // ---------- placement and leads: the placement table, the speed check, the relations, the leads, the coverage by month
  if (IN("placement")) {
    const host = document.getElementById("working");
    host.hidden = false;
    document.getElementById("lede").textContent = "Where our voice leads, and is labelled: how each position was placed, what the speed check says of the legs, the organizations with their pages, the leads, and the coverage month by month.";
    const card = (title, body, note = "") => `<section class="card wk"><h2>${title}</h2>${body}${note ? `<p class="below">${note}</p>` : ""}</section>`;
    const table = (head, body) => `<div class="wrapx"><table><thead><tr>${head.map(h => `<th>${h}</th>`).join("")}</tr></thead><tbody>${body}</tbody></table></div>`;
    const parts = [];
    // placement
    if (S.kind === "unit") {
      const how = r => !r.lonlat ? "no position given: in the log, not on the map" : !r.own ? `with a headquarters: ${sourceWords(r.source)}` : r.placed === "grid" ? `at the grid reference (${r.grid})` : r.placed === "grid-place" ? "at a place made from the grid reference" : r.offset ? `at an offset from a town (${r.offset})` : "at the town named";
      const groups = d3.rollups(rows, v => v, r => how(r).replace(/ \(.*\)$/, ""));
      parts.push(card("How each station was placed", table(["placement", "stations", "which"], groups.map(([k, v]) => `<tr><td>${esc(k)}</td><td class="num">${v.length}</td><td>${v.slice(0, 8).map(r => `${esc(r.date)}${r.place ? ` ${esc(r.place)}` : ""}`).join("; ")}${v.length > 8 ? ` … and ${v.length - 8} more` : ""}</td></tr>`).join("")),
        "A station is placed at the town its STATION line names, at the offset the line gives from it, or at its grid reference when that is to 1 km or better and falls within 8 km of the town (tools/build_army.py). A row whose source is a headquarters' (the battalion's journal, the regimental battery's report, a printed history, a situation map) is the headquarters' position with the unit assumed nearby: drawn hollow, its legs dashed."));
    } else if (S.kind === "battalion") {
      const how = r => !r.lonlat ? "no position" : r.assumed === "place" ? "position assumed: a stand-in point for an island, an address or several places" : r.assumed === "date" ? "date approximate (the month, or a transfer's day)" : r.assumed === "part" ? "which part is assumed" : "at the place the record names";
      const groups = d3.rollups(rows, v => v, how);
      parts.push(card("How each station was placed", table(["placement", "stations", "which"], groups.map(([k, v]) => `<tr><td>${esc(k)}</td><td class="num">${v.length}</td><td>${v.slice(0, 8).map(r => `${esc(r.date)} ${esc(r.place || "")}${r.part !== "battalion" ? ` (${esc(r.part)})` : ""}`).join("; ")}${v.length > 8 ? ` … and ${v.length - 8} more` : ""}</td></tr>`).join("")),
        "The rolls rarely say where the battalion was: a station is a code name, a Navy number or a transfer that places it near a base (records/seabees/README.md). `assumed` on a row says what it assumes."));
    } else if (S.kind === "boat" || S.kind === "ship") {
      const SRC = { bt: "bathythermograph table", noon: "noon position", radar: "radar intercept", narrative: "port, arrival or departure (the narrative)", diary: "war diary position", action: "AA action form", air: "aircraft contact (own position)", attack: "attack data sheet", gun: "gun attack", ship: "ship contact (the target's position)", event: "logged event" };
      const groups = d3.rollups(rows, v => v, r => r.source);
      parts.push(card("Where each position comes from", table(["part of the report", "positions", "on the track", "left off"], groups.map(([k, v]) => `<tr><td>${esc(SRC[k] || k)}</td><td class="num">${v.length}</td><td class="num">${v.filter(r => !r.offtrack).length}</td><td class="num">${v.filter(r => r.offtrack).length}</td></tr>`).join("")),
        `A ship contact is the target's position, never the boat's, so it is off the track; a fix that contradicts its neighbours is left off and says why (fix_note). ${rows.filter(r => !r.own).length ? `${n(rows.filter(r => !r.own).length, "event")} with no position of its own is placed between the fixes either side and marked assumed.` : ""}`));
    } else if (S.kind === "convoy") {
      const ships = extra.convoy.ships || [];
      const g = d3.rollups(ships, v => v, s => s.basis || "reported");
      parts.push(card("What the records give of it", table(["basis", "ships", "which"], g.map(([k, v]) => `<tr><td>${esc(k)}</td><td class="num">${v.length}</td><td>${v.map(s => esc(s.ship)).join(", ")}</td></tr>`).join("")) +
        table(["stop", "basis", "source"], rows.map(r => `<tr><td>${esc(r.words)} <span class="typed">${esc(r.date)}</span></td><td>${esc(r.source)}</td><td>${r.cite && r.cite.href ? `<a href="${esc(r.cite.href)}" target="_blank" rel="noopener">${esc(r.cite.label || r.cite.ref)}</a>` : ""}</td></tr>`).join("")),
        "Reported: a Japanese record names the ship in the convoy. Secondary: combinedfleet.com or another later list, repeating records not read here. Inferred: ours, from a record that doesn't name the convoy. The route runs through assumed waypoints (reference/lanes/lanes.yml), none traced from the escorts' charts."));
    }
    // the speed check, computed here from the fixes (tools/check_track.py's and build_army.py's arithmetic)
    if (S.kind === "boat" || S.kind === "ship" || S.kind === "unit" || S.kind === "battalion") {
      const NM = 3440.065, KM = 6371;
      const seaUnit = S.kind === "boat" || S.kind === "ship";
      const limitWords = seaUnit ? `${S.max_kts} knots, the vessel's limit in ship.yml, plus 30 nm of dead reckoning` : S.kind === "unit" ? "350 km a day on the road (build_army.py), a leg by sea or air exempt" : "900 km a day (a fast transport, build_seabees.py), a leg by train exempt";
      const checked = legs.map(l => {
        const dist = d3.sum(l.coords.slice(1), (c, j) => d3.geoDistance(l.coords[j], c)) * (seaUnit ? NM : KM);
        const hours = Math.max((l.b.t - l.a.t) / 36e5, seaUnit ? 0.01 : 24), days = Math.max(1, Math.round(hours / 24));
        const rate = seaUnit ? dist / hours : dist / days;
        const exempt = seaUnit ? false : S.kind === "unit" ? (l.style === "sea" || /\b(sea|ship|convoy|air|flew|LST|LCT)\b/i.test(l.b.note || "")) : (l.style === "sea" || /by train/i.test(l.b.note || ""));
        const fast = seaUnit ? dist > S.max_kts * hours + 30 : (!exempt && rate > (S.kind === "unit" ? 350 : 900));
        // ranked as the check ranks them: at sea by the distance over what the limit allows in the time (two fixes
        // minutes apart give no speed worth printing), on land by the rate
        const excess = seaUnit ? dist - S.max_kts * hours : rate;
        return { l, dist, hours, days, rate, fast, exempt, excess };
      }).sort((a, b) => b.excess - a.excess);
      const fast = checked.filter(x => x.fast);
      const show = [...fast, ...checked.filter(x => !x.fast).slice(0, 6)];
      const when = r => seaUnit ? `${fmtDay(new Date(r.t))} ${esc(r.words)}` : `${fmtDay(new Date(r.t))} ${esc(r.place || "(no place)")}`;
      parts.push(card(`The speed check: ${fast.length ? `<span class="fast">${n(fast.length, "leg")} too fast</span>` : "no leg too fast"}`,
        table(["from", "to", seaUnit ? "nm" : "km", seaUnit ? "hours" : "days", seaUnit ? "knots" : "km a day", seaUnit ? "over the limit, nm" : ""], show.map(x => `<tr${x.fast ? ' class="fast"' : ""}><td>${when(x.l.a)}</td><td>${when(x.l.b)}</td><td class="num">${Math.round(x.dist)}</td><td class="num">${seaUnit ? x.hours.toFixed(1) : x.days}</td><td class="num">${seaUnit && x.hours < 0.5 ? "—" : x.rate.toFixed(1)}</td><td>${seaUnit ? `${x.excess > 0 ? "+" : ""}${Math.round(x.excess)} ` : ""}${x.fast ? "too fast" : x.exempt ? `by ${x.l.style === "sea" ? "sea" : x.l.style === "rail" ? "train" : "sea or air (the note says)"}` : x.l.style !== "own" ? `${x.l.style === "sea" ? "at sea" : "assumed"} leg` : ""}</td></tr>`).join("")),
        `Each leg's distance is measured along the line the map draws (straight between fixes, or along the assumed route) against the time between its ends; the limit is ${limitWords}. ${fast.length ? "A leg too fast is a reading to check against the scan." : "The fastest legs are listed, so the figure can be seen as well as the verdict."} The arithmetic is tools/check_track.py's and build_army.py's, done again here on the page.`));
    }
    // relations
    if (S.relations.length) {
      parts.push(card(S.kind === "convoy" ? "Its ships, each with its page" : "Its organizations, each with its page",
        table(["from", "to", "relation", "other", "basis", "page", "note"], S.relations.map(r => `<tr><td class="typed">${esc(r.from)}</td><td class="typed">${esc(r.to)}</td><td>${esc(r.dir === "to" && r.relation === "part_of" ? "has as a part" : r.relation.replace(/_/g, " "))}</td><td>${byId[r.other] ? linkTo(byId[r.other], esc(r.other_name)) : esc(r.other_name)}</td><td>${esc(r.basis)}</td><td>${r.cite.map(c => `<a href="${esc(c.href)}" target="_blank" rel="noopener">${esc(c.ref)}</a>`).join("; ")}</td><td>${esc(r.note)}</td></tr>`).join("")),
        "One shape wherever the records keep it: army/relations.csv, seabees/parts.csv, a convoy's ships:, ComSubPac's dispositions and task organization (tools/build_subjects.py). A relation computed from positions (near, the same path, inside an operation's area) is never stored."));
    }
    // leads
    parts.push(card(`What the records leave open: ${S.leads.length ? n(S.leads.length, "lead") : "no lead listed for this subject yet"}`,
      S.leads.map(ld => `<div class="lead"><b>${esc(ld.statement)}</b><span><span class="k">said by</span> ${esc(ld.said_by)} ${ld.cite.map(c => `<a href="${esc(c.href)}" target="_blank" rel="noopener">(${esc(c.ref)})</a>`).join(" ")}</span><span><span class="k">searched</span> ${esc(ld.searched)}</span><span><span class="k">still to search</span> ${esc(ld.still)}</span></div>`).join(""),
      "A lead is a statement found in research notes or a secondary source that no record cited here supports yet (records/army/leads.yml). It stays here, not in the data, until a page says so."));
    // coverage by month
    if ((S.kind === "unit" || S.kind === "battalion") && S.periods.length) {
      parts.push(card("The coverage, month by month", table(["month", "stations", "placed by", "", "places"], S.periods.map(p => `<tr><td>${esc(fmtMonth(new Date(T(p.month + "-15"))))}</td><td class="num">${p.stations}</td><td>${esc(p.source ? sourceWords(p.source) : "")}</td><td>${p.assumed ? "assumed" : ""}</td><td>${p.places.map(esc).join(", ")}${(p.parts || []).filter(x => x !== "battalion").length ? ` <i>(${p.parts.filter(x => x !== "battalion").map(esc).join(", ")})</i>` : ""}</td></tr>`).join("")),
        "How we know where it was in a month: the record series in force then (a station holds until the next change). Where the subject's own reports are missing, the headquarters' are used and the row is assumed."));
    }
    if (S.kind === "ship" && S.periods[0]?.months?.length) {
      parts.push(card("Her diaries, month by month (inventory.yml)", table(["month", "status", "note"], S.periods[0].months.map(m => `<tr><td>${esc(fmtMonth(new Date(T(m.month + "-15"))))}</td><td>${esc(m.status)}</td><td>${esc(m.note || "")}</td></tr>`).join(""))));
    }
    if (S.kind === "boat") {
      parts.push(card("Her patrols, in the inventory", table(["patrol", "status", "fixes", "attacks", "files", "note"], S.periods.map(p => `<tr><td>${p.n} ${esc(p.name)}</td><td>${esc(p.status)}</td><td class="num">${p.fixes}</td><td class="num">${p.attacks}</td><td>${p.files.map(esc).join(", ")}</td><td>${esc(p.note)}</td></tr>`).join(""))));
    }
    if (S.kind === "command") {
      parts.push(card("Its war diaries, month by month (inventory.yml)", table(["month", "status", "catalog"], S.periods.map(p => `<tr><td>${esc(fmtMonth(new Date(T(p.month + "-15"))))}</td><td>${esc(p.status)}</td><td>${(p.nara || []).map(id => `<a href="https://catalog.archives.gov/id/${id}" target="_blank" rel="noopener">${id}</a>`).join(", ")}</td></tr>`).join(""))));
    }
    host.innerHTML = parts.join("");
  }
})();
