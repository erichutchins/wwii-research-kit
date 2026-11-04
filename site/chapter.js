// "From Algiers to Germany" as one chronology, for the front page's stages and the engagement pages' breadcrumb.
// Reads army/army.json, operations/operations.json, engagements/index.json and world-atlas's countries (RECORDS, config.js).
//
// A station's stage is the country it lies in, by today's borders (world-atlas), Sicily cut from Italy by the
// Strait of Messina; a station on a coast the 1:50m outline misses goes to the country with the nearest coast,
// within about 20 km (further out, at sea, it's in no stage). A unit's time in a stage runs from its first station there
// to its first station after. The campaigns are records/operations/ (not the theaters), placed by the middle of their
// areas; an engagement by the middle of its box, and under a campaign only when its whole span lies within the
// campaign's dates (otherwise it stands on its own between them). An engagement's units are its participants with a
// `unit:` (records/README.md, "An engagement"): only those are followed from one engagement to the next.

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
  const STAGES = [
    { id: "algiers", name: "Algiers", where: "Algeria and Tunisia", countries: ["Algeria", "Tunisia", "Morocco"] },
    { id: "sicily", name: "Sicily", where: "Sicily", countries: [],
      reading: [["grids.html", "The Army's map grids", "the grid references in the reports, from Sicily on"]] },
    { id: "italy", name: "Italy", where: "the Italian mainland", countries: ["Italy", "San Marino", "Vatican"],
      reading: [["german.html", "The German Army's reference points", "how the other side's reports in Italy give a position"]] },
    { id: "france", name: "France", where: "France, Belgium and Luxembourg", countries: ["France", "Belgium", "Luxembourg", "Netherlands"] },
    { id: "germany", name: "Germany", where: "Germany, Austria and Czechoslovakia", countries: ["Germany", "Austria", "Czechia"] },
  ];
  const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const day = d => Date.parse(String(d).slice(0, 10) + "T00:00Z");
  const mon = d3.utcFormat("%b %Y"), fmt = d3.utcFormat("%-d %b %Y"), iso = d3.utcFormat("%Y-%m-%d");
  const span = (a, b) => mon(a) === mon(b) ? mon(a) : `${mon(a)} – ${mon(b)}`;
  const days = (a, b) => a === b ? fmt(a) : `${fmt(a)} – ${fmt(b)}`;
  const href = e => `engagement.html?e=${encodeURIComponent(e.id)}`;

  let loaded;
  const load = () => loaded ??= build();

  async function build() {
    const [army, world, ops, index] = await Promise.all([d3.json(RECORDS + "army/army.json"),
      d3.json("https://cdn.jsdelivr.net/npm/world-atlas@2/countries-50m.json"), d3.json(RECORDS + "operations/operations.json"),
      d3.json(RECORDS + "engagements/index.json")]);
    // every country of Europe and North Africa (Britain too, so a station there is in no stage)
    const areas = topojsonFeatures(world, "countries").map(f => ({ f, s: STAGES.find(s => s.countries.includes(f.properties.name)),
      polys: f.geometry.coordinates.map(p => ({ p, b: d3.geoBounds({ type: "Polygon", coordinates: p }) })) }))
      .filter(a => a.polys.some(({ b: [[w, s], [e, n]] }) => e > -20 && w < 30 && n > 25 && s < 60));
    const sicily = STAGES[1];
    const stageOf = ([lon, lat]) => {
      if (lon == null || lat == null) return null;
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
      .map(o => ({ op: o, stage: middle(o.area), from: day(o.from), to: o.to ? day(o.to) : Infinity, engagements: [] }))
      .filter(c => c.stage);
    const engagements = index.filter(x => x.theater !== "pacific" && x.box).map(x => ({ ...x, t0: day(x.from), t1: day(x.to || x.from) }))
      .map(x => ({ ...x, stage: middle(x.box), href: href(x) })).filter(x => x.stage).sort((a, b) => a.t0 - b.t0);
    for (const e of engagements) {
      // the narrowest campaign of its stage that holds its whole span
      const c = campaigns.filter(c => c.stage === e.stage && c.from <= e.t0 && e.t1 <= c.to).sort((a, b) => (a.to - a.from) - (b.to - b.from))[0];
      if (c) { e.campaign = c; c.engagements.push(e); }
    }
    const stages = STAGES.map((s, i) => {
      const rs = runs.get(s).sort((a, b) => a.from - b.from);
      // the stage in date order: its campaigns (with their engagements), and the engagements outside any campaign
      const items = [...campaigns.filter(c => c.stage === s).map(c => ({ campaign: c, t: c.from })),
        ...engagements.filter(e => e.stage === s && !e.campaign).map(e => ({ engagement: e, t: e.t0 }))].sort((a, b) => a.t - b.t);
      return { ...s, n: i + 1, runs: rs, t0: d3.min(rs, r => r.from), t1: d3.max(rs, r => r.to), items };
    });
    // each unit's own entries (army/actions.csv: a raid fired on, a shelling, a man lost), the steps between engagements
    const actions = Object.fromEntries(army.units.map(u => [u.unit, (u.actions || []).filter(a => a.date).map(a => ({ ...a, t: day(a.date) }))]));
    return { stages, engagements, home, actions };
  }

  // an engagement's units, as a short line: "Battery F, Battery G (inferred)"
  const unitsLine = e => e.units.map(u => `${esc(u.name)}${u.basis !== "reported" ? ` <i title="${esc(u.basis)}: not named by the engagement's own entries">(${esc(u.basis)})</i>` : ""}`).join(", ");
  const opDates = c => c.op.to ? days(c.from, c.to) : `from ${fmt(c.from)}`;

  // one stage of the front page: the campaigns as its spine, each with its engagements and their units
  function stageHTML(s, ops) {
    const cite = o => ops?.cites?.[o.ref[0]];
    const opName = o => cite(o) ? `<a href="${esc(cite(o).href)}" title="${esc(cite(o).title || cite(o).short)}">${esc(o.name)}</a>` : esc(o.name);
    const eng = e => `<li class="eng"><span class="dates">${days(e.t0, e.t1)}</span> <a href="${e.href}">${esc(e.title)}</a>${e.units.length ? ` <span class="who">${unitsLine(e)}</span>` : ""}</li>`;
    const spine = s.items.map(it => it.campaign
      ? `<li class="camp"><span class="dates">${opDates(it.campaign)}</span> <span class="name">${opName(it.campaign.op)}</span>${it.campaign.engagements.length ? `<ul>${it.campaign.engagements.map(eng).join("")}</ul>` : ""}</li>`
      : eng(it.engagement)).join("");
    const units = s.runs.map(r => `<tr><td class="when">${span(r.from, r.to)}</td><td class="what"><a href="army.html?unit=${r.u.unit}&amp;t=${iso(r.from)}">${esc(r.u.name)}</a></td><td class="state">${r.n} station${r.n === 1 ? "" : "s"} here</td></tr>`).join("");
    return `
      <h3><span class="n">${s.n}</span> ${s.name}${s.runs.length ? ` <span class="when">${span(s.t0, s.t1)}</span>` : ""}</h3>
      <p class="where">${esc(s.where[0].toUpperCase() + s.where.slice(1))}.${s.runs.length ? ` <a href="army.html?unit=${s.runs[0].u.unit}&amp;t=${iso(s.t0)}">The Army map on ${fmt(s.t0)}</a>, the first station here.` : ""}</p>
      ${spine ? `<ol class="spine">${spine}</ol>` : `<p class="none">No campaign or engagement in the records here yet.</p>`}
      ${s.reading ? `<p class="reading"><i>Reading the records here:</i> ${s.reading.map(([h, t, w]) => `<a href="${h}">${esc(t)}</a>, ${esc(w)}`).join("; ")}</p>` : ""}
      ${units ? `<div class="also"><table><tbody>${units}</tbody></table></div>` : ""}`;
  }

  // the engagement pages' breadcrumb: where it falls in the chapter, the engagement before and after, and each unit's own
  async function crumb(id, el) {
    const C = await load();
    const i = C.engagements.findIndex(e => e.id === id);
    if (i < 0) { el.hidden = true; return; }   // not in the chapter (the Pacific)
    const e = C.engagements[i], s = C.stages.find(x => x.id === e.stage.id), prev = C.engagements[i - 1], next = C.engagements[i + 1];
    const step = (x, rel) => x ? `<a rel="${rel}" href="${x.href}">${rel === "prev" ? "← " : ""}${esc(x.short || x.title)}${rel === "next" ? " →" : ""}</a>`
      : `<span class="none">${rel === "prev" ? "← the first" : "the last →"}</span>`;
    // a unit's step before or after this engagement: its nearest other engagement, or else its nearest entry in the
    // records (army/actions.csv), which opens the Army map on that day
    const ofUnit = (u, dir) => {
      const engs = C.engagements.filter(x => x !== e && x.units.some(v => v.unit === u.unit))
        .map(x => ({ t: dir < 0 ? x.t1 : x.t0, html: `<a href="${x.href}">${esc(x.short || x.title)}</a>` }));
      const acts = (C.actions[u.unit] || []).map(a => ({ t: a.t, html: `<a href="army.html?unit=${encodeURIComponent(u.unit)}&amp;t=${a.date}" title="${esc(a.text)}">${fmt(a.t)}</a>: <span class="said">${esc(a.text.length > 64 ? a.text.slice(0, 62).replace(/\s+\S*$/, "") + " …" : a.text)}</span>` }));
      const xs = [...engs, ...acts].filter(x => dir < 0 ? x.t < e.t0 : x.t > e.t1).sort((a, b) => dir * (a.t - b.t));
      return xs.length ? `${dir < 0 ? "← " : ""}${xs[0].html}${dir > 0 ? " →" : ""}` : `<span class="none">${dir < 0 ? "nothing before in the records" : "nothing after in the records"}</span>`;
    };
    const units = e.units.map(u => `<tr><td class="u">${esc(u.name)}${u.basis !== "reported" ? ` <i title="not named by this engagement's own entries">(${esc(u.basis)})</i>` : ""}</td>
      <td>${ofUnit(u, -1)}</td><td>${ofUnit(u, 1)}</td><td><a href="army.html?unit=${encodeURIComponent(u.unit)}&amp;t=${iso(e.t0)}">its stations on the Army map</a></td></tr>`).join("");
    el.innerHTML = `
      <div class="trail"><a href="index.html#europe">Algiers to Germany</a> / <a href="index.html#stage-${s.id}">${s.n} ${s.name}</a>${e.campaign ? ` / ${esc(e.campaign.op.short || e.campaign.op.name)} <span class="dates">${opDates(e.campaign)}</span>` : ""} / <span aria-current="page">${esc(e.short || e.title)}</span></div>
      <div class="seq">${step(prev, "prev")}<span class="what">in date order, every engagement in the chapter</span>${step(next, "next")}</div>
      ${units ? `<table class="follow"><caption>Follow a unit: what its records give before and after this</caption><tbody>${units}</tbody></table>` : ""}`;
  }

  return { STAGES, load, stageHTML, crumb };
})();
