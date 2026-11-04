// theatre.html?t=pacific|atlantic|mediterranean|europe: one theatre of the four, as chapter.js works it out
// (guides/OPERATIONS-VIEWER.md 5.1). The head is the theatre's file in records/operations/<theater>/index.md: its name,
// its span and its paragraphs with their citations (links.js renders them, as the engagement page renders a story), and
// what the records hold, counted here. The map is static: the extent of the theatre's engagements' boxes, its
// operations' areas and its subjects' boxes; land from world-atlas; the operations' hand-drawn areas hatched, since they
// are ours; each engagement a mark at the middle of its box, opening its page (marks that would overlap become one,
// pointing at the spine); the followed subjects' tracks and stations in the lightest ink. Then the spine, the subjects
// here (the units' runs through the stages for the Mediterranean and Europe, which share the five stages; the boats'
// patrols, the ships, the battalions by calendar year, the convoys and the command by date for the Pacific; Solar's
// record for the Atlantic), what is also in the records and still to find (inventory.yml), and the explainers this
// theatre's records need. #stage-<id> and #op-<id> land on a stage or an operation once the page is drawn.
(async () => {
  const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const params = new URLSearchParams(location.search);
  const worldLoading = d3.json(EV.LAND_50M);   // fetched while chapter.js works the theatres out
  const C = await Chapter.load();
  const T = C.theatres.find(t => t.id === params.get("t")) || C.theatres[0];
  const ops = C.ops, op = T.op, subs = T.subjects;
  const T0 = s => Date.parse(`${String(s).slice(0, 10)}T12:00Z`);
  const fmt = d3.utcFormat("%-d %B %Y"), mon = d3.utcFormat("%b %Y"), year = d3.utcFormat("%Y");
  const span = (a, b) => !a || !b ? "" : mon(T0(a)) === mon(T0(b)) ? mon(T0(a)) : `${mon(T0(a))} – ${mon(T0(b))}`;
  const n = (k, one, many = one + "s") => `${k} ${k === 1 ? one : many}`;
  const subjHref = (s, extra = "") => `subject.html?s=${encodeURIComponent(s.alias || s.id)}${extra}`;
  const render = text => Links.render(text, { cites: ops.cites || {} });

  // ---------- the head
  document.title = T.name;
  document.getElementById("crumb").innerHTML = Chapter.trail([T.name]);
  document.getElementById("title").textContent = op ? op.name : T.name;
  const first = op ? op.from : d3.min(subs, s => s.first), last = op && op.to ? op.to : op ? null : d3.max(subs, s => s.last);
  document.getElementById("span").textContent = first ? (last ? `${fmt(T0(first))} – ${fmt(T0(last))}` : `from ${fmt(T0(first))}`) : "";
  if (op && op.note) { const el = document.getElementById("note"); el.textContent = op.note; el.hidden = false; }
  const KINDS = [["boat", "boat"], ["ship", "ship"], ["unit", "Army unit"], ["battalion", "Seabee battalion"], ["convoy", "convoy"], ["command", "command"]];
  const kinds = KINDS.map(([k, w]) => { const c = subs.filter(s => s.kind === k).length; return c ? n(c, w) : ""; }).filter(Boolean);
  document.getElementById("holds").innerHTML = `What the records hold here: ${n(T.engagements.length, "engagement")} read from both sides; ${n(subs.length, "subject")}${kinds.length ? ` (${kinds.join(", ")})` : ""}; ${n(T.campaigns.length, "operation or campaign", "operations and campaigns")} entered with their dates and areas.`;
  const secs = (op ? op.sections : []).filter(s => s.heading && s.paras.length);
  if (secs.length) {
    const head = document.getElementById("head");
    head.innerHTML = secs.map(s => `<h2>${esc(s.heading)}</h2>${s.paras.map(p => `<p class="${p.aside ? "aside" : ""}">${render(p.text)}</p>`).join("")}`).join("");
    head.hidden = false;
  }

  // ---------- the map
  const world = await worldLoading;
  const LAND = EV.land(world);
  const box = document.getElementById("map-box"), svg = d3.select("#map");
  const norm = lon => lon > 180 ? lon - 360 : lon;
  const corners = [];
  // a box written in signed degrees that is wider than 180° crosses the 180th meridian, and its corners say nothing
  // about its extent (a track from Pearl Harbor to Luzon has them both near the meridian): the theatre's own area holds it
  const addBox = ([w, s, e, n]) => { if (e - w > 180 && e <= 180) return; corners.push([norm(w), s], [norm(e), n]); };
  T.engagements.forEach(e => addBox(e.box));
  T.campaigns.forEach(c => c.op.area && addBox(c.op.area));
  if (op && op.area) addBox(op.area);
  // a subject's box only inside the theatre's own area (a unit's stations at home, before it sailed, are not the theatre)
  const clip = ([w, s, e, n]) => { const a = op && op.area; if (!a) return [w, s, e, n]; const b = [Math.max(w, a[0]), Math.max(s, a[1]), Math.min(e, a[2]), Math.min(n, a[3])]; return b[0] < b[2] && b[1] < b[3] ? b : null; };
  subs.forEach(s => { const b = s.box && clip(s.box); if (b) addBox(b); });
  const [w0, e0] = op && op.area ? [op.area[0], op.area[2]] : d3.extent(corners, c => c[0]);
  const ruler = scaleBar(box, { units: T.id === "pacific" || T.id === "atlantic" ? ["nm"] : ["km"] });
  // (the ring runs clockwise, as d3-geo wants an exterior ring; the other way round fills the rest of the sphere)
  const rect = ([w, s, e, n]) => ({ type: "Polygon", coordinates: [[[norm(w), s], [norm(w), n], [norm(e), n], [norm(e), s], [norm(w), s]]] });
  let tracks = [];   // the followed subjects' tracks and stations, as geo lines, once loaded
  function draw() {
    const W = box.clientWidth, H = box.clientHeight;
    if (W < 120 || H < 120 || !corners.length) return;
    svg.selectAll("*").remove();
    const HATCH = EV.hatchDef(svg, "hatch-ours");
    const proj = d3.geoMercator().rotate([-(w0 + e0) / 2, 0]).fitExtent([[14, 14], [W - 14, H - 14]], { type: "MultiPoint", coordinates: corners });
    const path = d3.geoPath(proj);
    const [lonA] = proj.invert([0, H / 2]), [lonB] = proj.invert([W, H / 2]);
    const wide = ((lonB - lonA) + 360) % 360 || 360;
    const step = wide > 80 ? 20 : wide > 30 ? 10 : wide > 10 ? 5 : 1;
    svg.append("path").attr("class", "grat").attr("d", path(d3.geoGraticule().step([step, step])()));
    svg.append("path").attr("class", "land").attr("d", path(LAND));
    svg.append("g").attr("class", "trks").selectAll("path").data(tracks).join("path").attr("class", "trk").attr("d", path);
    // the operations' areas: hatched, ours; a name where it has room
    const placed = [];
    const room = (x, y, w) => { const hit = placed.some(b => Math.abs(b.y - y) < 15 && x < b.x + b.w && x + w > b.x); if (!hit) placed.push({ x, y, w }); return !hit; };
    const gA = svg.append("g");
    for (const c of T.campaigns.filter(c => c.op.area)) {
      const a = c.op.area, g = gA.append("g");
      g.append("path").attr("class", "area").attr("fill", HATCH).attr("d", path(rect(a))).append("title").text(`${c.op.name}: ${c.op.from}${c.op.to ? ` – ${c.op.to}` : ""} (area drawn by hand)`);
      const [x, y] = proj([norm(a[0]), a[3]]), name = c.op.short || c.op.name;
      if (x > 0 && y > 0 && x < W && y < H && room(x + 4, y + 13, name.length * 6.5)) g.append("text").attr("class", "area-label").attr("x", x + 4).attr("y", y + 13).text(name);
    }
    // the engagements: a mark at the middle of each box; marks within 12 px of each other become one, pointing at the spine
    const marks = T.engagements.map(e => ({ e, xy: proj([norm((e.box[0] + e.box[2]) / 2), (e.box[1] + e.box[3]) / 2]) })).filter(m => m.xy && m.xy.every(isFinite));
    const groups = [];
    for (const m of marks) {
      const g = groups.find(g => Math.hypot(g.xy[0] - m.xy[0], g.xy[1] - m.xy[1]) < 12);
      if (g) g.es.push(m.e); else groups.push({ xy: m.xy, es: [m.e] });
    }
    const gE = svg.append("g");
    for (const g of groups) {
      const one = g.es.length === 1, label = one ? (g.es[0].short || g.es[0].title) : n(g.es.length, "engagement");
      const a = gE.append("a").attr("href", one ? g.es[0].href : "#spine").attr("transform", `translate(${g.xy.map(v => v.toFixed(1))})`);
      a.append("title").text(g.es.map(e => e.title).join("\n"));
      a.append("circle").attr("class", "mark").attr("r", one ? 4.5 : 6);
      const right = g.xy[0] < W - 160;
      if (room(right ? g.xy[0] + 8 : g.xy[0] - 8 - label.length * 6.5, g.xy[1] + 4, label.length * 6.5))
        a.append("text").attr("class", "mark-label").attr("x", right ? 8 : -8).attr("y", 4).attr("text-anchor", right ? "start" : "end").text(label);
    }
    ruler.update(p => proj.invert(p));
  }
  draw();
  new ResizeObserver(() => draw()).observe(box);
  document.getElementById("cap").textContent = `Land: today's coastline (world-atlas). Hatched: the operations' areas, drawn by hand (ours). A mark: an engagement, at the middle of its box; a larger mark stands for several close together. Faint lines: the followed subjects' tracks and stations.`;
  // the tracks and stations, in the lightest ink, once they arrive (the map stands without them)
  const line = coords => coords.length > 1 ? { type: "LineString", coordinates: coords } : null;
  const loads = subs.filter(s => s.geojson).map(s => d3.json(RECORDS + s.geojson).then(g => g.features.filter(f => f.geometry.type === "LineString").map(f => f.geometry)));
  const dated = rows => rows.filter(r => r.lat != null && r.lon != null).sort((a, b) => a.date.localeCompare(b.date)).map(r => [r.lon, r.lat]);
  loads.push(Promise.resolve(C.army.units.filter(u => subs.some(s => s.id === u.unit)).map(u => line(dated(u.stations))).filter(Boolean)));
  if (subs.some(s => s.kind === "battalion")) loads.push(d3.json(RECORDS + "seabees/seabees.json").then(S =>
    d3.groups(S.rows.filter(r => subs.some(s => s.id === r.unit)), r => r.unit + "/" + r.part).map(([, rs]) => line(dated(rs))).filter(Boolean)));
  Promise.allSettled(loads).then(rs => { tracks = rs.filter(r => r.status === "fulfilled").flatMap(r => r.value); draw(); });

  // ---------- the spine
  document.getElementById("spine-body").innerHTML = Chapter.spineHTML(T.items, ops);

  // ---------- the subjects here
  const row = (when, what, state, todo) => `<tr class="${todo ? "todo" : ""}"><td class="when">${when}</td><td class="what">${what}</td><td class="state">${state}</td></tr>`;
  const table = rows => rows.length ? `<table><tbody>${rows.join("")}</tbody></table>` : "";
  const out = [];
  if (T.stages.length) {
    // the stages: this theatre's, numbered across the two that have them; each points across to the other theatre's
    const all = C.stages, mine = T.stages, before = all[all.indexOf(mine[0]) - 1], after = all[all.indexOf(mine[mine.length - 1]) + 1];
    const across = s => `<p class="across"><a href="${Chapter.theatreHref(s.theatre, `stage-${s.id}`)}">${s === before ? `← ${s.n} ${esc(s.name)}` : `${s.n} ${esc(s.name)} →`}</a>, ${s === before ? "where the units came from, in the" : "where the units went on, in"} ${esc(C.theatres.find(t => t.id === s.theatre).name)}</p>`;
    out.push(`<p class="where">The Army units in the records, in the order they went, each stage with every unit that had a station there, opening on the Army map on the day it arrived.</p>`);
    if (before) out.push(across(before));
    out.push(...mine.map(s => `<div class="stage">${Chapter.stageHTML(s)}</div>`));
    if (after) out.push(across(after));
  }
  // the vessels, battalions, convoys and commands, by the date of their first record
  const rows = [];
  for (const s of subs.filter(s => s.kind !== "unit")) {
    const when = span(s.first, s.last), t = T0(s.first || "9999");
    if (s.kind === "boat") {
      const patrols = s.periods.map(p => `<a href="${subjHref(s, `&amp;period=${p.n}&amp;view=records`)}" title="${esc(`${p.name}, ${p.dates}`)}">${p.n}</a>`).join(", ");
      rows.push([t, row(when, `<a href="${subjHref(s)}">${esc(s.name)}</a>, <i>${esc(s.plain)}</i>: war patrol${s.periods.length === 1 ? "" : "s"} ${patrols}`, [...new Set(s.periods.map(p => p.status))].join(", "))]);
    } else if (s.kind === "ship") {
      rows.push([t, row(when, `<a href="${subjHref(s)}">${esc(s.name)}</a>, <i>${esc(s.plain)}</i>`, esc(s.periods.map(p => p.name).join("; ")))]);
    } else if (s.kind === "battalion") {
      for (const [y, ps] of d3.groups(s.periods, p => p.month.slice(0, 4)))
        rows.push([T0(`${y}-01-01`), row(y, `<a href="${subjHref(s, `&amp;t=${ps[0].month}-01&amp;view=records`)}">${esc(s.name)}</a>, <i>${esc(s.plain)}</i>`, `${n(ps.filter(p => p.stations).length, "month")} with stations`)]);
    } else if (s.kind === "convoy") {
      rows.push([t, row(when, `<a href="${subjHref(s)}">${esc(s.name)}</a>, <i>${esc(s.plain)}</i>`, s.engagements.length ? `met: ${s.engagements.map(e => `<a href="engagement.html?e=${esc(e.id)}">${esc(e.short || e.title)}</a>`).join(", ")}` : "its voyage")]);
    } else if (s.kind === "command") {
      const done = s.periods.filter(p => /transcribed|mapped/.test(p.status));
      rows.push([t, row(when, `<a href="${subjHref(s)}">${esc(s.name)}</a>, <i>${esc(s.plain)}</i>`, `${n(done.length, "month")} of the war diary transcribed`)]);
    }
  }
  rows.sort((a, b) => a[0] - b[0]);
  if (rows.length) out.push(`<div class="also">${table(rows.map(r => r[1]))}</div>`);
  if (!out.length) out.push(`<p class="none">No subject with a record here yet.</p>`);
  document.getElementById("subjects-body").innerHTML = out.join("");

  // ---------- also in the records, and still to find (inventory.yml)
  const inv = jsyaml.load(await d3.text(RECORDS + "inventory.yml"));
  const word = { mapped: "on the map", transcribed: "transcribed, not yet drawn", available: "<b>found, not transcribed</b>",
    found: "<b>found, not transcribed</b>", "not-searched": "<b>not looked for yet</b>", missing: "looked for, not found", "in-progress": "in progress" };
  const also = [];
  if (T.id === "pacific") {
    for (const [hull, b] of Object.entries(inv.boats || {})) if (!b.folder)
      also.push(row("", `${esc(b.name)} (${esc(hull)}): ${esc(b.note || "")}`, Object.keys(b.patrols || {}).length ? word[Object.values(b.patrols)[0].status] : word["not-searched"], true));
    const cs = inv.commands?.comsubpac?.records || {}, k = s => Object.values(cs).filter(r => r.status === s).length;
    if (Object.keys(cs).length) also.push(row("1944–45", "Submarine Force, Pacific: its monthly war diaries", `${k("transcribed")} transcribed, <b>${k("available")} found, not transcribed</b>`, true));
  }
  if (T.id === "atlantic") for (const [k, r] of Object.entries(inv.ships?.["DE-221"]?.records || {}))
    also.push(row(/^\d{4}-\d{2}$/.test(k) ? mon(T0(k + "-01")) : "", `USS Solar (DE-221): ${esc(r.note || k)}`, word[r.status] || r.status, r.status !== "mapped"));
  if (T.id === "europe") for (const u of C.home)
    also.push(row(mon(T0(u.stations[0].date)), `<a href="subject.html?s=${esc(u.unit)}">${esc(u.name)}</a>, to ${mon(T0(u.stations[u.stations.length - 1].date))}`, "in the United States and Britain only", false));
  // a unit's missing parts (its records after the months online) go with the unit's theatre; a unit never overseas with Europe
  const after = part => { const m = /^after-(\d{4})-(\d{2})$/.exec(part); return m ? `its records after ${d3.utcFormat("%B %Y")(new Date(Date.UTC(+m[1], +m[2] - 1)))} (not online)` : part; };
  for (const [k, u] of Object.entries(inv.units || {})) {
    const S = C.subjects.find(s => s.id === k), th = S && S.theatre === "mediterranean" ? "mediterranean" : "europe";
    if (th !== T.id) continue;
    for (const [part, r] of Object.entries(u)) if (part !== "record") also.push(row("", `${esc(S ? S.name : k)}: ${after(part)}`, word[r.status] || r.status, true));
  }
  if (also.length) { document.getElementById("also-body").innerHTML = table(also); document.getElementById("also").hidden = false; }

  // ---------- reading the records here
  document.getElementById("reading-body").innerHTML = T.reading.map(([h, t, w]) => `<li><a href="${h}">${esc(t)}</a>, ${esc(w)}</li>`).join("");

  // a deep link to a stage or an operation (#stage-italy, #op-cassino) lands on it now that it is drawn
  if (/^#(stage|op)-/.test(location.hash)) document.querySelector(location.hash)?.scrollIntoView();
})();
