// What the engagement pages draw the same way (engagement.html, convoys.html, lanes.html): tooltips, silhouettes,
// citation links, the land. The computation is in engage.js; the encodings are guides/ENGAGEMENTS.md's
// ("Encodings, the same on every page").
const EV = (() => {
  const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const tip = () => document.getElementById("tip");
  function showTip(ev, html) { const t = tip(); t.innerHTML = html; t.hidden = false; moveTip(ev); }
  function moveTip(ev) {
    const t = tip(), r = t.getBoundingClientRect();
    let x = ev.clientX + 14, y = ev.clientY + 14;
    if (x + r.width > innerWidth - 8) x = ev.clientX - r.width - 14;
    if (y + r.height > innerHeight - 8) y = ev.clientY - r.height - 14;
    t.style.left = Math.max(8, x) + "px"; t.style.top = Math.max(8, y) + "px";
  }
  function hideTip() { tip().hidden = true; }

  // A citation as the build resolved it ({href, label, more}) -> the page link(s)
  function cite(c, cls = "src") {
    if (!c || !c.href) return c && c.label ? `<span class="${cls}">${esc(c.label)}</span>` : "";
    const one = x => `<a class="${cls}" href="${esc(x.href)}" target="_blank" rel="noopener" title="${esc(x.ref)}">${esc(x.label || "page")}</a>`;
    return [c, ...(c.more || [])].map(one).join(" ");
  }

  // A silhouette from the kit's library (silhouettes.js; wait on SILHOUETTES): a ship's own class profile in feet,
  // drawn `ftPx` pixels to the foot so plates compare true size, or else the generic shape for its kind.
  function sil(id, fill, opts = {}) {
    const { ftPx = 0.38, width = 150, cls = "sil" } = opts;
    const ship = window.SHIPS && SHIPS[id];
    if (ship) {
      const L = +ship.length, H = Math.max(L * 0.3, 30), w = L * ftPx;
      return `<svg class="${cls}" viewBox="-2 ${-H} ${L + 4} ${H + 3}" width="${w.toFixed(0)}" height="${(w * (H + 3) / (L + 4)).toFixed(0)}" preserveAspectRatio="xMinYMax meet" aria-hidden="true"><path d="${ship.d}" fill="${fill}"/></svg>`;
    }
    const cat = window.SIL_CATEGORIES && SIL_CATEGORIES.shapes[id in (window.SIL_CATEGORIES?.shapes || {}) ? id : category(id)];
    return cat ? `<svg class="${cls}" viewBox="0 0 120 24" width="${width}" height="${width / 5}" aria-hidden="true"><path d="${cat}" fill="${fill}"/></svg>` : "";
  }
  // the generic shape for a kind of ship or a silhouette id with no category of its own
  function category(kind) {
    const k = String(kind || "").toLowerCase();
    if (/submarine|balao|gato/.test(k)) return "submarine";
    if (/tanker|oiler/.test(k)) return "tanker";
    if (/destroyer|kamikaze|wakatake|sumner|fletcher|torpedo/.test(k)) return "destroyer";
    if (/gunboat/.test(k)) return "gunboat";
    if (/escort|kaibokan|shimushu|mikura|chidori|shirataka|minesweeper|minelayer|buckley/.test(k)) return "escort";
    if (/fighter|aircraft|air group|judy|zeke|corsair/.test(k)) return "fighter";
    return "cargo";
  }
  // what the silhouette is: her own plate, her class's, a type standing for her, or only the kind of ship
  function silWords(id, basis) {
    if (window.SHIPS && SHIPS[id]) {
      const n = SHIPS[id].name;
      return basis === "representative" ? `${n}: a representative type, not her own plate` :
             basis && basis.startsWith("class, assumed") ? `${n}: her class, assumed (${basis.slice(16)})` : n;
    }
    return "The kind of ship only (no plate in the library yet)";
  }

  const land = world => topojson.feature(world, world.objects.land);
  const LAND_10M = "https://cdn.jsdelivr.net/npm/world-atlas@2/land-10m.json";
  const LAND_50M = "https://cdn.jsdelivr.net/npm/world-atlas@2/land-50m.json";

  // the grid lines and their labels for a projection's visible extent
  function graticule(g, proj, W, H) {
    const dm = (v, pos, neg) => { const a = Math.abs(v), d = Math.floor(a + 1e-9), m = Math.round((a - d) * 60); return `${d}°${m ? String(m).padStart(2, "0") + "′" : ""}${v >= 0 ? pos : neg}`; };
    const [w, n] = proj.invert([0, 0]), [e, s] = proj.invert([W, H]);
    const span = e - w, step = span > 30 ? 10 : span > 12 ? 5 : span > 4 ? 1 : span > 1.5 ? 0.5 : span > 0.6 ? 1 / 6 : 1 / 12;
    g.selectAll("*").remove();
    d3.range(Math.ceil(s / step) * step, n, step).forEach(la => {
      const y = proj([w, la])[1];
      g.append("line").attr("class", "grat").attr("x1", 0).attr("x2", W).attr("y1", y).attr("y2", y);
      g.append("text").attr("class", "grat-label").attr("x", 6).attr("y", y - 4).text(dm(la, "N", "S"));
    });
    d3.range(Math.ceil(w / step) * step, e, step).forEach(lo => {
      const x = proj([lo, s])[0];
      g.append("line").attr("class", "grat").attr("y1", 0).attr("y2", H).attr("x1", x).attr("x2", x);
      g.append("text").attr("class", "grat-label").attr("x", x + 4).attr("y", H - 8).text(dm(lo, "E", "W"));
    });
  }

  const shape = { diamond: "M0,-6L6,0L0,6L-6,0Z", cross: "M-5,-5L5,5M5,-5L-5,5" };
  // the marks a Japanese record's outcome gets: sunk (red cross), hit (red ring), attacked without damage (open ring)
  function outcomeMark(g, mark, dashed) {
    if (mark === "sunk") {
      g.append("path").attr("d", shape.cross).attr("stroke", "var(--surface)").attr("stroke-width", 5);
      g.append("path").attr("d", shape.cross).attr("stroke", "var(--hit)").attr("stroke-width", 2.4).attr("stroke-dasharray", dashed ? "3 1.5" : null);
    } else if (mark === "hit") {
      g.append("circle").attr("r", 5.5).attr("fill", "none").attr("stroke", "var(--hit)").attr("stroke-width", 2.4).attr("stroke-dasharray", dashed ? "3 1.5" : null);
    } else {
      g.append("circle").attr("r", 5.5).attr("fill", "var(--surface)").attr("stroke", "var(--japan)").attr("stroke-width", 1.6).attr("stroke-dasharray", dashed ? "3 1.5" : null);
    }
  }
  const legendMark = {
    sunk: `<svg width="12" height="12" viewBox="-6 -6 12 12"><path d="${shape.cross}" stroke="var(--hit)" stroke-width="2.2"/></svg>`,
    hit: `<svg width="14" height="14" viewBox="-7 -7 14 14"><circle r="5" fill="none" stroke="var(--hit)" stroke-width="2.2"/></svg>`,
    miss: `<svg width="14" height="14" viewBox="-7 -7 14 14"><circle r="5" fill="none" stroke="var(--japan)" stroke-width="1.6"/></svg>`,
    attack: c => `<svg width="12" height="12" viewBox="-6 -6 12 12"><path d="${shape.diamond}" fill="${c}"/></svg>`,
    sighted: c => `<svg width="12" height="12" viewBox="-6 -6 12 12"><circle r="4.5" fill="none" stroke="${c}" stroke-width="1.8"/></svg>`,
  };

  // ---------- the chronology (guides/OPERATIONS-VIEWER.md, 3): a spine of hours, days or months at the left, one column
  // per record, every entry at its row in entry.css's block, the time (or "no time recorded", in italics) leading the
  // who line, since the spine already gives the day and the block's own time column is folded away (chron.css). The
  // rows and columns are Engage's (chronologyRows, chronologyColumns; engage.js must be loaded). A station starts a bar
  // in the column's colour that runs down the column from its row; an entry whose kind is a hit on the unit
  // (Engage.hitKind) has its kind in the hit red. The DOM is rows of side groups of cells: on a desktop the groups are
  // `display: contents`, so the cells sit in one grid under the headers; on a phone chron.css stacks each row's sides
  // and names the record on each cell. Every entry links to its page (EV.cite).
  const SIDE_WORDS = { us: "US", jp: "Japanese", allied: "Allied", axis: "Axis", de: "German", it: "Italian", uk: "British", fr: "French", press: "Press", geo: "Place" };
  function chronology(el, { rows, columns, tempo = "dated", sideName = s => SIDE_WORDS[s] || s || "", nameOf = a => a } = {}) {
    const sides = [...new Set(columns.map(c => c.side))];
    const ordered = sides.flatMap(s => columns.filter(c => c.side === s));   // the header's order is the cells'
    const colOf = new Map();
    ordered.forEach(c => c.entries.forEach(e => colOf.set(e, c)));
    const corner = { clocked: "GMT", dated: "dated", monthly: "month" }[tempo] || "";
    const parts = [`<div class="chron-h chron-corner">${esc(corner)}</div>`];
    ordered.forEach(c => parts.push(`<div class="chron-h" style="--bar:${c.colour}"><b>${esc(c.name)}</b><span class="chip">${esc([c.record, sideName(c.side)].filter(Boolean).join(" · "))}</span></div>`));
    const hold = new Set();   // the columns a station's bar is running down
    rows.forEach(r => {
      parts.push(`<div class="chron-row"><div class="chron-d">${esc(r.label)}${r.day ? `<small>${esc(r.day)}</small>` : ""}</div>`);
      sides.forEach(s => {
        const cs = ordered.filter(c => c.side === s), any = r.entries.some(e => cs.includes(colOf.get(e)));
        parts.push(`<div class="chron-side${any ? "" : " empty"}" data-side="${esc(sideName(s))}">`);
        cs.forEach(c => {
          const es = r.entries.filter(e => colOf.get(e) === c);
          if (es.some(e => e.kind === "station")) hold.add(c.key);
          parts.push(`<div class="chron-c${hold.has(c.key) ? " hold" : ""}" style="--bar:${c.colour}" data-col="${esc(c.name)}">${es.map(e => chronEntry(e, c, nameOf)).join("")}</div>`);
        });
        parts.push("</div>");
      });
      parts.push("</div>");
    });
    el.classList.add("chron");
    el.style.setProperty("--n", ordered.length);
    el.innerHTML = parts.join("");
  }
  function chronEntry(e, c, nameOf) {
    const timed = e.local && e.local.length > 10;
    const t = timed ? `<span class="t">${esc(e.local.slice(11))}</span>` : `<span class="t placed">no time recorded</span>`;
    const actor = String(nameOf(e.actor) || ""), h = Engage.head(actor);
    const who = actor && !(h === Engage.head(c.name) && h === actor.trim()) ? `<b>${esc(actor)}</b>` : "";   // named when it isn't the column's own name
    const what = e.title && e.title !== actor ? e.title : e.kind && e.kind !== "log" ? e.kind.replace(/_/g, " ") : "";
    const toWhom = e.to ? `<span class="what">to ${e.to.map(r => esc(nameOf(r))).join(" and ")}</span>` : e.from ? `<span class="what">from ${esc(nameOf(e.from))}</span>` : "";
    const lang = e.lang || "ja";   // an original is Japanese unless the build says otherwise (a German one is typed)
    const words = e.original ? `<div class="${lang === "ja" ? "ja" : "said"}" lang="${esc(lang)}">${esc(e.original)}</div><div class="tr">${esc(e.translation || e.words || "")}</div>`
                             : `<div class="said">${esc(e.words || e.title || "")}</div>`;
    const outcome = (e.outcome || []).map(o => `<div class="note"><b>Japanese side (${esc(String(o.relation || "").replace(/_/g, " "))}).</b> ${esc(o.note)}</div>`).join("");
    const placed = e.placed && e.placed !== "seq" ? `<div class="assume">${esc(e.placed)}</div>` : "";
    return `<div class="entry${Engage.hitKind(e.kind) ? " hit" : ""}${e.kind === "station" ? " stn" : ""}${e.basis === "assumed" ? " assumed" : ""}" style="--bar:${c.colour}"><div class="body">
      <div class="who">${t}${who}${what ? `<span class="what">${esc(what)}</span>` : ""}${toWhom}</div>
      ${words}${outcome}${e.note ? `<div class="note">${esc(e.note)}</div>` : ""}${placed}
      ${e.source ? `<span class="src">${esc(e.source)}</span>` : ""} ${cite(e.cite, "src alone")}</div></div>`;
  }

  return { esc, showTip, moveTip, hideTip, cite, sil, category, silWords, land, LAND_10M, LAND_50M, graticule, shape, outcomeMark, legendMark, chronology };
})();
