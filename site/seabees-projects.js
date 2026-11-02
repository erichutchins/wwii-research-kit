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
