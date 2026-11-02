// The battalion's work, project by project: a section per main construction project
// (records/seabees/projects/<id>.md, built into seabees.json's `projects` by tools/build_seabees.py), in the order
// the battalion reached them, each with its dates, what was built, a button that flies the map to it, the records'
// account, and "Afterwards": a short history of how the base was used later, each paragraph labelled by its
// evidence (record, secondary, inference, not known) and every one context, not the battalion's act. Then the
// other stations (projects/also-at.md).
//
//   seabeeProjects(container, data, unit, {
//     locate(lonlat, project),   // fly the map there and set the date
//     open(link, row),           // a citation (the page's scan viewer; row = {station, t})
//     extra(project) -> Node,    // optional: a family page's own line (where the relative's part was)
//   })
// Shared by the kit's site/seabees.html and a family's page.

const PROJECT_EVIDENCE = {
  record: ["Record", "Read on the scan of a wartime record"],
  secondary: ["Secondary", "A published history"],
  inference: ["Inference", "Ours, from the records cited; not a record's statement"],
  "not known": ["Not known", "Not found in the records read so far"],
};
const FILM_RELEVANCE = {
  "place-date": ["The place at the time, not the battalion", "Filmed where the battalion was, while it was there; the film doesn't name it"],
  context: ["Context: the same operation or work, not the battalion", "Another unit, another day or a nearby place; the note says how far off"],
};
const FILM_DATE_BASIS = { catalogue: "the catalogue's date", "shot card": "the shot card's date", "stated-in-film": "dated in the film", inferred: "date inferred" };
const PROJECT_BASIS = { reported: "", derived: "derived", inferred: "inferred", assumed: "assumed" };

function seabeeProjects(container, data, unit, opts = {}) {
  const mk = (tag, cls, text) => {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined) e.textContent = text;
    return e;
  };
  const day = s => new Date(`${s}T12:00Z`).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
  const month = s => new Date(`${s}T12:00Z`).toLocaleDateString("en-GB", { month: "short", year: "numeric", timeZone: "UTC" });
  const projects = (data.projects || []).filter(p => p.unit === unit);
  const also = (data.also_at || {})[unit] || [];
  container.replaceChildren();
  container.hidden = !projects.length;
  if (!projects.length) return;

  const cite = (l, row) => {
    const a = mk("a", "proj-cite", l.label);
    a.href = l.url;
    a.target = "_blank";
    a.rel = "noopener";
    a.title = l.cite;
    if (l.scan && opts.open) a.addEventListener("click", ev => { ev.preventDefault(); opts.open(l, row); });
    return a;
  };
  const para = (p, row) => {
    const e = mk("p", "proj-para");
    if (p.evidence) {
      const [label, title] = PROJECT_EVIDENCE[p.evidence];
      const tag = mk("span", `ev ev-${p.evidence.replace(" ", "-")}`, label);
      tag.title = title;
      e.append(tag, " ");
    }
    p.segs.forEach(([k, v]) => {
      if (k === "t") e.append(v);
      else if (k === "i") e.append(mk("i", null, v));
      else e.append(cite(v, row));
    });
    return e;
  };
  // A film of the place (records/film/clips.csv): what it shows, its date and basis, what it is to the battalion,
  // and where to see it. Neither kind is the battalion unless its shot list names it.
  const filmBlock = c => {
    const box = mk("div", `proj-film ${c.relevance}`);
    const [rel, relTitle] = FILM_RELEVANCE[c.relevance] || [c.relevance, ""];
    const top = mk("div", "proj-film-head");
    const tag = mk("span", "proj-film-rel", rel);
    tag.title = relTitle;
    top.append(mk("b", null, c.place), ` · ${filmDate(c.date)} `, mk("span", "proj-prec", `(${FILM_DATE_BASIS[c.date_basis] || c.date_basis})`), " · ", tag);
    const shows = mk("p", "proj-film-shows", c.shows);
    const links = mk("div", "proj-film-links");
    const a = mk("a", null, `National Archives, ${c.archive_id}`);
    Object.assign(a, { href: c.link.url, target: "_blank", rel: "noopener", title: "The archive's catalogue page: the shot list, and the film where it is online" });
    links.append(a);
    if (c.youtube) {
      const y = mk("a", null, "a copy on YouTube");
      Object.assign(y, { href: c.youtube, target: "_blank", rel: "noopener", title: "A re-upload, to watch; the catalogue is the source" });
      links.append(" · ", y);
    }
    const more = mk("details", "proj-film-note");
    more.append(mk("summary", null, "What it is to the battalion"), mk("p", null, c.note));
    box.append(top, shows, links, more);
    return box;
  };
  const filmDate = s => s.length === 10 ? day(s) : s.length === 7 ? month(`${s}-01`) : s;
  const dates = p => {
    const a = `${day(p.from)}${PROJECT_BASIS[p.from_basis] ? ` (${PROJECT_BASIS[p.from_basis]}: ${month(p.from)})` : ""}`;
    const b = `${day(p.to)}${PROJECT_BASIS[p.to_basis] ? ` (${PROJECT_BASIS[p.to_basis]})` : ""}`;
    return `${a} – ${b}`;
  };

  const head = mk("div", "proj-head");
  head.append(mk("h2", null, "The battalion's work, project by project"),
    mk("p", null, "Its main construction projects, in the order it reached them: what it built, from its own records and " +
      "the Navy's history of the bases, and afterwards how each base was used later in the war. Afterwards is context: " +
      "a squadron flying from a strip, or boats repaired at a base, is not the battalion's act. Each paragraph says " +
      "what kind of evidence it rests on."));
  const key = mk("p", "proj-key");
  Object.entries(PROJECT_EVIDENCE).forEach(([k, [label, title]]) => {
    key.append(mk("span", `ev ev-${k.replace(" ", "-")}`, label), mk("span", "proj-key-t", ` ${title.toLowerCase()} `));
  });
  head.append(key);
  const index = mk("nav", "proj-index");
  index.setAttribute("aria-label", "Projects");
  projects.forEach((p, i) => {
    const a = mk("a", null, `${i + 1}. ${p.places[0].name.split(",")[0]}`);
    a.href = `#proj-${p.id}`;
    index.append(a);
  });
  if (also.length) {
    const a = mk("a", null, "Also at");
    a.href = "#proj-also";
    index.append(a);
  }
  head.append(index);
  container.append(head);

  const grid = mk("div", "proj-grid");
  projects.forEach((p, i) => {
    const row = { station: p.title, t: Date.parse(`${p.from}T12:00Z`) };
    const art = mk("article", "proj card");
    art.id = `proj-${p.id}`;
    const h = mk("h3");
    h.append(mk("span", "proj-n", `${i + 1}`), ` ${p.title}`);
    const when = mk("div", "proj-when");
    when.append(dates(p), " · ", p.part === "battalion" ? "the battalion" : `the ${p.part}`, " · ");
    p.dates_links.forEach((l, j) => { if (j) when.append(", "); when.append(cite(l, row)); });
    art.append(h, when);
    const locs = mk("div", "proj-locs");
    p.places.forEach(pl => {
      const b = mk("button", "proj-locate");
      b.type = "button";
      b.append(mk("span", "proj-pin", "◎"), ` ${pl.name}`, mk("span", "proj-prec", ` · ${pl.precision}`));
      b.title = pl.placed || `Drawn at the station "${pl.station}" (places.csv). Click to show it on the map, on ${day(p.from)}.`;
      b.addEventListener("click", () => opts.locate?.([pl.lon, pl.lat], p));
      locs.append(b);
    });
    art.append(locs);
    const ul = mk("ul", "proj-built");
    p.built.forEach(b => ul.append(mk("li", null, b)));
    art.append(ul);
    const fam = opts.extra?.(p);
    if (fam) art.append(fam);
    art.append(mk("h4", null, "What the records say"));
    art.append(...(p.account || []).map(x => para(x, row)));
    if (p.film?.length) {
      art.append(mk("h4", null, "Film"));
      p.film.forEach(c => art.append(filmBlock(c)));
    }
    const ah = mk("h4", null, "Afterwards");
    ah.append(mk("span", "proj-ctx", " · context, not the battalion's act"));
    art.append(ah, ...(p.afterwards || []).map(x => para(x, row)));
    grid.append(art);
  });
  if (also.length) {
    const art = mk("article", "proj card proj-also");
    art.id = "proj-also";
    art.append(mk("h3", null, "Also at"),
      mk("p", "proj-when", "Where else the battalion, or a part of it, trained, staged or worked on something smaller."));
    const ul = mk("ul", "proj-also-list");
    also.forEach(s => {
      const li = mk("li");
      const row = { station: s.place, t: Date.parse(`${s.from}T12:00Z`) };
      const name = s.lat === null ? mk("b", null, s.place) : mk("button", "proj-locate proj-locate-sm");
      if (s.lat !== null) {
        name.type = "button";
        name.append(mk("span", "proj-pin", "◎"), ` ${s.place}`);
        name.addEventListener("click", () => opts.locate?.([s.lon, s.lat], s));
      }
      li.append(name, mk("span", "proj-also-when", ` ${month(s.from)} – ${month(s.to)}. `), s.what, " ");
      s.links.forEach((l, j) => { if (j) li.append(", "); li.append(cite(l, row)); });
      ul.append(li);
    });
    art.append(ul);
    grid.append(art);
  }
  container.append(grid);
}

// The projects on a page's map: a numbered square per project place, held a little up and to the left of the place
// on a short leader (so the station's own dot stays visible beneath it), stacked upwards where two would overlap;
// each links to its section below. A project after the map's date is faded, as the stations are.
//
//   const pm = seabeeProjectMarks(layer, data, unit, proj);   // layer: a d3 <g> inside the zoomed group
//   pm.rescale(k); pm.setTime(t); pm.at(ev.target) -> mark | null; pm.tip(mark) -> Node
function seabeeProjectMarks(layer, data, unit, proj) {
  const projects = (data.projects || []).filter(p => p.unit === unit);
  const marks = projects.flatMap((p, i) => p.places.map(pl => ({ p, n: i + 1, pl, xy: proj([pl.lon, pl.lat]),
                                                                  t: Date.parse(`${p.from}T12:00Z`) })));
  const gs = layer.attr("class", "pmks").selectAll("g").data(marks).join("g").attr("class", "pmk")
    .attr("transform", d => `translate(${d.xy})`);
  gs.append("line").attr("class", "pmk-lead").attr("x1", 0).attr("y1", 0);
  const a = gs.append("a").attr("href", d => `#proj-${d.p.id}`)
    .attr("aria-label", d => `Project ${d.n}: ${d.p.title}. ${d.pl.name}, placed to the ${d.pl.precision}. Read its section.`);
  a.append("rect").attr("class", "pmk-box");
  a.append("text").attr("class", "pmk-n").attr("text-anchor", "middle").attr("dy", "0.36em").text(d => d.n);
  const S = 17, OFF = 15;   // the square's side and its offset from the place, in screen pixels
  return {
    rescale(k) {
      const boxes = [];
      marks.forEach(d => {   // stacked in screen space (scale k; the zoom's translation doesn't change overlaps)
        const x = d.xy[0] * k - OFF;
        let y = d.xy[1] * k - OFF;
        while (boxes.some(([bx, by]) => Math.abs(bx - x) < S + 2 && Math.abs(by - y) < S + 2)) y -= S + 3;
        boxes.push([x, y]);
        d.off = [-OFF / k, (y - d.xy[1] * k) / k];
      });
      gs.select("line").attr("x2", d => d.off[0]).attr("y2", d => d.off[1]);
      gs.select("rect").attr("x", d => d.off[0] - S / 2 / k).attr("y", d => d.off[1] - S / 2 / k)
        .attr("width", S / k).attr("height", S / k);
      gs.select("text").attr("x", d => d.off[0]).attr("y", d => d.off[1]).style("font-size", `${11.5 / k}px`);
    },
    setTime(t) { gs.classed("future", d => d.t > t); },
    at(target) { const n = target?.closest?.(".pmk"); return n ? d3.select(n).datum() : null; },
    tip(d) {
      const div = (cls, text) => { const e = document.createElement("div"); e.className = cls; e.textContent = text; return e; };
      const day = s => new Date(`${s}T12:00Z`).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
      const box = document.createElement("div");
      box.append(div("v", `${d.n}. ${d.p.title}`), div("k", `${day(d.p.from)} – ${day(d.p.to)}`),
        div("i", `${d.pl.name}: placed to the ${d.pl.precision}${d.pl.placed ? ` (${d.pl.placed})` : ", at the station's point"}`),
        div("m", "A project, not a station; click to read its section"));
      return box;
    },
  };
}
