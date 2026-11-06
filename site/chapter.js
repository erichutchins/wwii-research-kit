// The four theatres as one chronology each: the theatre pages' spine (theatre.html, theatre.js), the stages of the
// Mediterranean and Europe, the subjects' runs through them, and the breadcrumb on every page (guides/OPERATIONS-VIEWER.md
// 5.3). Reads army/army.json, operations/operations.json, engagements/index.json, subjects.json and world-atlas's
// countries (RECORDS, config.js).
//
// A theatre's engagements are the index's rows with its `theater` (the records' spelling; the kit's prose and ids say
// theatre), its operations the files under records/operations/<theater>/. A station's stage is the country it lies in,
// by today's borders (world-atlas), Sicily cut from Italy by the Strait of Messina; a station on a coast the 1:50m
// outline misses goes to the country with the nearest coast, within about 20 km (further out, at sea, it's in no
// stage). The five stages belong to the Mediterranean (Algiers, Sicily, Italy) and Europe (France, Germany), numbered
// across the two, and no country divides the Pacific or the Atlantic. A unit's time in a stage runs from its first
// station there to its first station after. The campaigns are records/operations/ (not the theaters), placed by the
// middle of their areas; an engagement by the middle of its box, and under a campaign of its theatre only when its
// whole span lies within the campaign's dates (otherwise it stands on its own between them). An engagement's units are
// its participants with a `unit:` (records/README.md, "An engagement"), its boats the names in `boats`: those are
// followed from one engagement to the next.

// world-atlas's land (or its countries, one feature each), without loading topojson-client for two calls
function topojsonFeatures(topo, key) {
  const o = topo.objects[key], arcs = topo.arcs, [sx, sy] = topo.transform.scale, [tx, ty] = topo.transform.translate;
  const decoded = arcs.map(arc => { let x = 0, y = 0; return arc.map(([dx, dy]) => [(x += dx) * sx + tx, (y += dy) * sy + ty]); });
  const ring = idx => idx.flatMap((i, k) => { const a = i < 0 ? decoded[~i].slice().reverse() : decoded[i]; return k ? a.slice(1) : a; });
  const geoms = o.type === "GeometryCollection" ? o.geometries : [o];
  return geoms.filter(g => g.arcs).map(g => ({ type: "Feature", properties: g.properties || {},
    geometry: { type: "MultiPolygon", coordinates: g.type === "Polygon" ? [g.arcs.map(ring)] : g.arcs.map(p => p.map(ring)) } }));
}

const Chapter = (() => {
  // the explainers each theatre's records need ("reading the records here")
  const THEATRES = [
    { id: "pacific", name: "Pacific", reading: [
      ["zones.html", "Time zones", "each boat kept its own zone; the convoys' records kept Tokyo time"],
      ["jgrid.html", "The Japanese Navy's position codes", "the kana grid the other side's records give a position in"],
      ["torpedo.html", "Torpedo fire control", "the attack data sheets' numbers"],
      ["silhouettes.html", "Recognition silhouettes", "the ships and aircraft the records name, to their plates"],
      ["dives.html", "A submarine's dives", "BANG's depth through every dive and depth-charge attack"],
      ["lanes.html", "The sea lanes", "the convoys the boats met, on the lanes they sailed"]] },
    { id: "europe", name: "Europe", reading: [["grids.html", "The Army's map grids", "the grid references in the reports"]] },
    { id: "mediterranean", name: "Mediterranean", reading: [
      ["grids.html", "The Army's map grids", "the grid references in the reports, from Sicily on"],
      ["german.html", "The German Army's reference points", "how the other side's reports in Italy give a position"],
      ["zones.html", "Time zones", "the Army's zone letters beside the Navy's"]] },
    { id: "atlantic", name: "Atlantic", reading: [["zones.html", "Time zones", "the war diary's zone letters, changing with the convoy's longitude"]] },
  ];
  const STAGES = [
    { id: "algiers", theatre: "mediterranean", name: "Algiers", where: "Algeria and Tunisia", countries: ["Algeria", "Tunisia", "Morocco"] },
    { id: "sicily", theatre: "mediterranean", name: "Sicily", where: "Sicily", countries: [] },
    { id: "italy", theatre: "mediterranean", name: "Italy", where: "the Italian mainland", countries: ["Italy", "San Marino", "Vatican"] },
    { id: "france", theatre: "europe", name: "France", where: "France, Belgium and Luxembourg", countries: ["France", "Belgium", "Luxembourg", "Netherlands"] },
    { id: "germany", theatre: "europe", name: "Germany", where: "Germany, Austria and Czechoslovakia", countries: ["Germany", "Austria", "Czechia"] },
  ];
  const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const day = d => Date.parse(String(d).slice(0, 10) + "T00:00Z");
  const mon = d3.utcFormat("%b %Y"), fmt = d3.utcFormat("%-d %b %Y"), iso = d3.utcFormat("%Y-%m-%d");
  const span = (a, b) => mon(a) === mon(b) ? mon(a) : `${mon(a)} – ${mon(b)}`;
  const days = (a, b) => a === b ? fmt(a) : `${fmt(a)} – ${fmt(b)}`;
  const href = e => `engagement.html?e=${encodeURIComponent(e.id)}`;
  const theatreHref = (t, hash) => `theatre.html?t=${encodeURIComponent(t)}${hash ? `#${hash}` : ""}`;

  let loaded;
  const load = () => loaded ??= build();

  async function build() {
    const [army, world, ops, index, subjects] = await Promise.all([d3.json(RECORDS + "army/army.json"),
      d3.json("https://cdn.jsdelivr.net/npm/world-atlas@2/countries-50m.json"), d3.json(RECORDS + "operations/operations.json"),
      d3.json(RECORDS + "engagements/index.json"), d3.json(RECORDS + "subjects.json")]);
    // every country of Europe and North Africa (Britain too, so a station there is in no stage)
    const areas = topojsonFeatures(world, "countries").map(f => ({ f, s: STAGES.find(s => s.countries.includes(f.properties.name)),
      polys: f.geometry.coordinates.map(p => ({ p, b: d3.geoBounds({ type: "Polygon", coordinates: p }) })) }))
      .filter(a => a.polys.some(({ b: [[w, s], [e, n]] }) => e > -20 && w < 30 && n > 25 && s < 60));
    const sicily = STAGES[1];
    // (memoised by position: a unit's stations repeat the same place for weeks, and a point-in-country test over every
    // outline is the slowest thing the pages compute)
    const memo = new Map();
    const stageOf = ([lon, lat]) => {
      if (lon == null || lat == null) return null;
      const key = `${lon},${lat}`;
      if (memo.has(key)) return memo.get(key);
      const s = stageAt(lon, lat);
      memo.set(key, s);
      return s;
    };
    const stageAt = (lon, lat) => {
      const inBox = ([[w, s], [e, n]], pad) => lon >= w - pad && lon <= e + pad && lat >= s - pad && lat <= n + pad;
      let hit = areas.find(a => a.polys.some(({ b }) => inBox(b, 0)) && d3.geoContains(a.f, [lon, lat]));
      if (!hit) {   // off the outline (a harbour, a beach): the country with the nearest coast, within about 20 km
        let best = 0.003;
        for (const a of areas) for (const { p, b } of a.polys) if (inBox(b, 0.3)) for (const xy of p[0]) {
          const d = d3.geoDistance(xy, [lon, lat]);
          if (d < best) { best = d; hit = a; }
        }
      }
      if (!hit?.s) return null;
      return hit.s.id === "italy" && lat < 38.35 && lon < 15.62 && lon > 12 ? sicily : hit.s;
    };
    const middle = ([w, s, e, n]) => stageOf([(w + e) / 2, (s + n) / 2]);

    // each unit's runs through the stages
    const runs = new Map(STAGES.map(s => [s, []])), home = [];
    // (a unit entered only for its relations, a battalion of a division with no stations yet, has no runs to place)
    for (const u of army.units.filter(u => u.stations.some(x => x.date))) {
      const st = u.stations.filter(x => x.date).map(x => ({ ...x, t: day(x.date), s: stageOf([x.lon, x.lat]) }));
      const rs = new Map();
      st.forEach((x, i) => {
        if (!x.s) return;
        const r = rs.get(x.s) || { from: x.t, to: x.t, n: 0 };
        const next = st.slice(i + 1).find(y => y.s !== x.s);
        r.to = Math.max(r.to, next ? next.t : x.t); r.n++;
        rs.set(x.s, r);
      });
      if (!rs.size) home.push(u);
      for (const [s, r] of rs) runs.get(s).push({ u, ...r });
    }

    const campaigns = ops.operations.filter(o => o.kind !== "theater")
      .map(o => ({ op: o, theatre: o.theater, stage: o.area ? middle(o.area) : null, from: day(o.from), to: o.to ? day(o.to) : Infinity,
        engagements: [], href: theatreHref(o.theater, `op-${o.id}`) }));
    const engagements = index.filter(x => x.box).map(x => ({ ...x, theatre: x.theater, t0: day(x.from), t1: day(x.to || x.from) }))
      .map(x => ({ ...x, stage: middle(x.box), href: href(x) })).sort((a, b) => a.t0 - b.t0);
    for (const e of engagements) {
      // the narrowest campaign of its theatre (and stage, where the theatre has stages) that holds its whole span
      const c = campaigns.filter(c => c.theatre === e.theatre && c.stage === e.stage && c.from <= e.t0 && e.t1 <= c.to).sort((a, b) => (a.to - a.from) - (b.to - b.from))[0];
      if (c) { e.campaign = c; c.engagements.push(e); }
    }
    // a theatre (or one of its stages) in date order: its campaigns (with their engagements), and the engagements outside any campaign
    const items = (t, s) => [...campaigns.filter(c => c.theatre === t && (!s || c.stage === s)).map(c => ({ campaign: c, t: c.from })),
      ...engagements.filter(e => e.theatre === t && (!s || e.stage === s) && !e.campaign).map(e => ({ engagement: e, t: e.t0 }))].sort((a, b) => a.t - b.t);
    const stages = STAGES.map((s, i) => {
      const rs = runs.get(s).sort((a, b) => a.from - b.from);
      return { ...s, n: i + 1, runs: rs, t0: d3.min(rs, r => r.from), t1: d3.max(rs, r => r.to), items: items(s.theatre, s) };
    });
    const theatres = THEATRES.map(t => ({ ...t, op: ops.operations.find(o => o.kind === "theater" && o.theater === t.id) || null,
      campaigns: campaigns.filter(c => c.theatre === t.id), engagements: engagements.filter(e => e.theatre === t.id), items: items(t.id),
      stages: stages.filter(s => s.theatre === t.id), subjects: subjects.filter(s => s.theatre === t.id), href: theatreHref(t.id) }));
    // each unit's own entries (army/actions.csv: a raid fired on, a shelling, a man lost), the steps between engagements
    const actions = Object.fromEntries(army.units.map(u => [u.unit, (u.actions || []).filter(a => a.date).map(a => ({ ...a, t: day(a.date) }))]));
    // stageOf: a [lon, lat] -> its stage, for the subject pages' strips; home: the units with no station in any stage
    return { theatres, stages, engagements, subjects, home, actions, ops, army, stageOf };
  }

  // an engagement's units, as a short line: "Battery F, Battery G (inferred)"
  const unitsLine = e => e.units.map(u => `${esc(u.name)}${u.basis !== "reported" ? ` <i title="${esc(u.basis)}: not named by the engagement's own entries">(${esc(u.basis)})</i>` : ""}`).join(", ");
  const opDates = c => c.op.to ? days(c.from, c.to) : `from ${fmt(c.from)}`;

  // a theatre's or a stage's spine: its campaigns in date order (each with its engagements and their units or boats),
  // and the engagements outside any campaign standing between them; `ops` is operations.json, for the citations
  function spineHTML(items, ops) {
    const cite = o => ops?.cites?.[o.ref[0]];
    const opName = o => cite(o) ? `<a href="${esc(cite(o).href)}" title="${esc(cite(o).title || cite(o).short)}">${esc(o.name)}</a>` : esc(o.name);
    const who = e => e.units.length ? unitsLine(e) : e.boats.length ? esc(e.boats.join(", ")) : "";
    const eng = e => `<li class="eng"><span class="dates">${days(e.t0, e.t1)}</span> <a href="${e.href}">${esc(e.title)}</a>${who(e) ? ` <span class="who">${who(e)}</span>` : ""}</li>`;
    const spine = items.map(it => it.campaign
      ? `<li class="camp" id="op-${esc(it.campaign.op.id)}"><span class="dates">${opDates(it.campaign)}</span> <span class="name">${opName(it.campaign.op)}</span>${it.campaign.engagements.length ? `<ul>${it.campaign.engagements.map(eng).join("")}</ul>` : ""}</li>`
      : eng(it.engagement)).join("");
    return spine ? `<ol class="spine">${spine}</ol>` : `<p class="none">No operation or engagement in the records here yet.</p>`;
  }

  // one stage of a theatre page: its heading and where it is, and every unit with stations there, opening on the Army
  // map on the day it arrived
  function stageHTML(s) {
    const units = s.runs.map(r => `<tr><td class="when">${span(r.from, r.to)}</td><td class="what"><a href="subject.html?s=${r.u.unit}&amp;t=${iso(r.from)}">${esc(r.u.name)}</a></td><td class="state">${r.n} station${r.n === 1 ? "" : "s"} here</td></tr>`).join("");
    return `
      <h3 id="stage-${s.id}"><span class="n">${s.n}</span> ${s.name}${s.runs.length ? ` <span class="when">${span(s.t0, s.t1)}</span>` : ""}</h3>
      <p class="where">${esc(s.where[0].toUpperCase() + s.where.slice(1))}.${s.runs.length ? ` <a href="subject.html?s=${s.runs[0].u.unit}&amp;t=${iso(s.t0)}">The Army map on ${fmt(s.t0)}</a>, the first station here.` : ""}</p>
      ${units ? `<div class="also"><table><tbody>${units}</tbody></table></div>` : `<p class="none">No unit with a station here yet.</p>`}`;
  }

  // the breadcrumb's trail, the same markup on every page (chapter.css): each part {href, text, dates?}, the last the
  // page itself; a part given as a string is the page
  const trail = parts => `<div class="trail">${parts.filter(Boolean).map((p, i, all) => {
    if (typeof p === "string") p = { text: p };
    const dates = p.dates ? ` <span class="dates">${esc(p.dates)}</span>` : "";
    return i === all.length - 1 && !p.href ? `<span aria-current="page">${esc(p.text)}</span>${dates}` : `<a href="${esc(p.href)}">${esc(p.text)}</a>${dates}`;
  }).join(" / ")}</div>`;

  // the engagement pages' breadcrumb: the theatre, the stage and the operation it falls in, the engagement before and
  // after in its theatre, and each followed subject's (a unit's, a boat's) own before and after
  async function crumb(id, el) {
    const C = await load();
    const e = C.engagements.find(x => x.id === id);
    if (!e) { el.hidden = true; return; }
    const T = C.theatres.find(t => t.id === e.theatre), s = e.stage && C.stages.find(x => x.id === e.stage.id);
    const i = T.engagements.indexOf(e), prev = T.engagements[i - 1], next = T.engagements[i + 1];
    const step = (x, rel) => x ? `<a rel="${rel}" href="${x.href}">${rel === "prev" ? "← " : ""}${esc(x.short || x.title)}${rel === "next" ? " →" : ""}</a>`
      : `<span class="none">${rel === "prev" ? "← the first" : "the last →"}</span>`;
    const arrow = (dir, html) => `${dir < 0 ? "← " : ""}${html}${dir > 0 ? " →" : ""}`;
    const none = dir => `<span class="none">${dir < 0 ? "nothing before in the records" : "nothing after in the records"}</span>`;
    const link = x => `<a href="${x.href}">${esc(x.short || x.title)}</a>`;
    // a unit's step before or after this engagement: its nearest other engagement, or else its nearest entry in the
    // records (army/actions.csv), which opens the unit's own page on that day
    const ofUnit = (u, dir) => {
      const engs = T.engagements.filter(x => x !== e && x.units.some(v => v.unit === u.unit)).map(x => ({ t: dir < 0 ? x.t1 : x.t0, html: link(x) }));
      const acts = (C.actions[u.unit] || []).map(a => ({ t: a.t, html: `<a href="subject.html?s=${encodeURIComponent(u.unit)}&amp;t=${a.date}" title="${esc(a.text)}">${fmt(a.t)}</a>: <span class="said">${esc(a.text.length > 64 ? a.text.slice(0, 62).replace(/\s+\S*$/, "") + " …" : a.text)}</span>` }));
      const xs = [...engs, ...acts].filter(x => dir < 0 ? x.t < e.t0 : x.t > e.t1).sort((a, b) => dir * (a.t - b.t));
      return xs.length ? arrow(dir, xs[0].html) : none(dir);
    };
    // a boat's: its nearest other engagement in the theatre
    const ofBoat = (name, dir) => {
      const xs = T.engagements.filter(x => x !== e && x.boats.includes(name) && (dir < 0 ? x.t1 < e.t0 : x.t0 > e.t1)).sort((a, b) => dir * (a.t0 - b.t0));
      return xs.length ? arrow(dir, link(xs[0])) : none(dir);
    };
    const units = e.units.map(u => `<tr><td class="u">${esc(u.name)}${u.basis !== "reported" ? ` <i title="not named by this engagement's own entries">(${esc(u.basis)})</i>` : ""}</td>
      <td>${ofUnit(u, -1)}</td><td>${ofUnit(u, 1)}</td><td><a href="subject.html?s=${encodeURIComponent(u.unit)}&amp;t=${iso(e.t0)}">its stations on its own page</a></td></tr>`);
    const boats = e.boats.map(name => {
      const S = C.subjects.find(x => x.kind === "boat" && x.short === name), period = S?.engagements.find(x => x.id === e.id)?.period;
      const own = S ? `<a href="subject.html?s=${encodeURIComponent(S.alias || S.id)}${period ? `&amp;period=${esc(period)}` : ""}">${period ? `her patrol ${esc(period)}` : "her track"} on her own page</a>` : "";
      return `<tr><td class="u">${esc(name)}</td><td>${ofBoat(name, -1)}</td><td>${ofBoat(name, 1)}</td><td>${own}</td></tr>`;
    });
    const follow = [...units, ...boats].join("");
    el.innerHTML = trail([{ href: T.href, text: T.name }, s && { href: theatreHref(T.id, `stage-${s.id}`), text: `${s.n} ${s.name}` },
      e.campaign && { href: e.campaign.href, text: e.campaign.op.short || e.campaign.op.name, dates: opDates(e.campaign) }, e.short || e.title]) + `
      <div class="seq">${step(prev, "prev")}<span class="what">in date order, every engagement in the ${esc(T.name)}</span>${step(next, "next")}</div>
      ${follow ? `<table class="follow"><caption>Follow a subject: what its records give before and after this</caption><tbody>${follow}</tbody></table>` : ""}`;
  }

  return { THEATRES, STAGES, load, spineHTML, stageHTML, trail, crumb, theatreHref };
})();
