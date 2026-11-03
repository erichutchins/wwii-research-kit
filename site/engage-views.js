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
  // (Engage.hitKind) has its kind in the hit red. The DOM is rows of groups of cells, one group per nationality (the
  // press of a nationality its own group, since its voice is its source's kind, not a side): on a desktop the groups
  // are `display: contents`, so the cells sit in one grid under the headers; on a phone chron.css stacks each row's
  // groups and names the record on each cell. Every entry links to its page (EV.cite). The chip under a column's name
  // is the record's own words and its source's kind and nationality (Engage.columnChip: "morning report · record · US",
  // "French press"); the other side is named as the records name it (Engage.nation), never as a bloc.
  const groupOf = c => (c.source_kind === "press" ? "press:" : "") + (c.of || "");
  const groupName = c => (c.source_kind === "press" ? [Engage.nation(c.of), "press"] : [Engage.nation(c.of)]).filter(Boolean).join(" ");
  function chronology(el, { rows, columns, tempo = "dated", nameOf = a => a } = {}) {
    const groups = [...new Set(columns.map(groupOf))];
    const ordered = groups.flatMap(g => columns.filter(c => groupOf(c) === g));   // the header's order is the cells'
    const colOf = new Map();
    ordered.forEach(c => c.entries.forEach(e => colOf.set(e, c)));
    const corner = { clocked: "GMT", dated: "dated", monthly: "month" }[tempo] || "";
    const parts = [`<div class="chron-h chron-corner">${esc(corner)}</div>`];
    ordered.forEach(c => parts.push(`<div class="chron-h" style="--bar:${c.colour}"><b>${esc(c.name)}</b><span class="chip">${esc(Engage.columnChip(c))}</span></div>`));
    const hold = new Set();   // the columns a station's bar is running down
    rows.forEach(r => {
      parts.push(`<div class="chron-row"><div class="chron-d">${esc(r.label)}${r.day ? `<small>${esc(r.day)}</small>` : ""}</div>`);
      groups.forEach(g => {
        const cs = ordered.filter(c => groupOf(c) === g), any = r.entries.some(e => cs.includes(colOf.get(e)));
        parts.push(`<div class="chron-side${any ? "" : " empty"}" data-side="${esc(groupName(cs[0]))}">`);
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
    const lang = e.lang || "ja";   // the record's own language (the build's `lang`): Japanese in its face, any other typed
    const words = e.original ? `<div class="${lang === "ja" ? "ja" : "said"}" lang="${esc(lang)}" data-tr="${esc(e.translation || e.words || "")}">${esc(e.original)}</div><div class="tr">${esc(e.translation || e.words || "")}</div>`
                             : `<div class="said">${esc(e.words || e.title || "")}</div>`;
    const outcome = (e.outcome || []).map(o => `<div class="note"><b>Japanese side (${esc(String(o.relation || "").replace(/_/g, " "))}).</b> ${esc(o.note)}</div>`).join("");
    const placed = e.placed && e.placed !== "seq" ? `<div class="assume">${esc(e.placed)}</div>` : "";
    return `<div class="entry${Engage.hitKind(e.kind) ? " hit" : ""}${e.kind === "station" ? " stn" : ""}${e.basis === "assumed" ? " assumed" : ""}" style="--bar:${c.colour}"><div class="body">
      <div class="who">${t}${who}${what ? `<span class="what">${esc(what)}</span>` : ""}${toWhom}</div>
      ${words}${outcome}${e.note ? `<div class="note">${esc(e.note)}</div>` : ""}${placed}
      ${e.source ? `<span class="src">${esc(e.source)}</span>` : ""} ${cite(e.cite, "src alone")}</div></div>`;
  }


  // ---------- the Sources view (guides/OPERATIONS-VIEWER.md 3 and 7.1; the look: guides/mockups/tama-17-working.html): one
  // moment, every source that speaks to it, as a table whose columns are sources (sources.css). A pair moment
  // (Engage.pairMoments) has the rows as typed, in GMT (ours), position as typed, placed (ours), the words, the page, and
  // last, hatched, what we make of it: the pairing's relation and note from the boat's claims.yml; under the table the
  // minutes and miles between the first source and each other, computed on the page (Engage.apart). A question moment
  // (Engage.claimMoments) has its answers grouped by source, as typed with their notes, and their pages; the hatched row is
  // left out, since the engagement's claims.yml weighs each answer and says nothing of the question as a whole. Each
  // column's chips are its source's kind and nationality (Engage.sourceKindWord) and its clock. Nothing in a column is
  // corrected to agree with another.
  const chips = (...xs) => xs.filter(Boolean).map(x => `<span class="chip">${esc(x)}</span>`).join("");
  const colHead = (name, sub, ...cs) => `<th><b>${esc(name)}</b>${sub ? esc(sub) : ""}${cs.some(Boolean) ? "<br>" : ""}${chips(...cs)}</th>`;
  const none = words => `<span class="none">${esc(words)}</span>`;
  const words = ws => ws.map(w => w.original ? `<span class="${w.lang === "ja" ? "ja" : "said typed"}" lang="${esc(w.lang)}" data-tr="${esc(w.translation || "")}">${esc(w.original)}</span><span class="tr">${esc(w.translation || "")}</span>`
                            : w.typed ? `<span class="said typed">${esc(w.typed)}</span>` : w.ours ? `<span class="ours">${esc(w.ours)}</span>` : "").join("");
  const dayOf = utc => { const ms = Engage.T(utc); return ms == null || Number.isNaN(ms) ? "" : `${Engage.day(ms)} ${new Date(ms).getUTCFullYear()}`; };
  const deg = (v, pos, neg) => `${Math.abs(v).toFixed(3)} ${v >= 0 ? pos : neg}`;
  const short = name => String(name || "").split(",")[0];
  // the page as cited, with its item ("rg367-74802746/p16 ↗", "jacar:C08050103200 p23 ↗"; a catalogue address by its label)
  const pageOf = c => c && c.href ? [c, ...(c.more || [])].map(x => `<a href="${esc(x.href)}" target="_blank" rel="noopener">${esc(/^https?:/.test(x.ref || "") ? x.label || "page" : x.ref || x.label)} ↗</a>`).join(" ") : cite(c);
  function sources(el, m) {
    const parts = [];
    if (m.sources) {   // a pair: an attack and the record of the same minutes
      const S = m.sources, n = S.length;
      parts.push(`<h3><span><b>${esc(short(S[0].name))}, ${esc(m.attack)}</b> · ${esc(dayOf(m.utc))}: the same minutes, source by source</span><span>minutes and miles computed here</span></h3>`);
      parts.push(`<div class="srcs"><table style="--n:${n}"><colgroup><col class="row-head"></colgroup><thead><tr><th></th>${S.map(s => colHead(s.name, s.sub, Engage.sourceKindWord(s.kind, s.of), s.zone ? `zone ${s.zone}` : s.utc ? "no zone written" : "no time")).join("")}</tr></thead><tbody>`);
      parts.push(`<tr><th>as typed</th>${S.map(s => `<td>${s.typed ? `<span class="typed">${esc(s.typed)}</span>` : none("no time")}</td>`).join("")}</tr>`);
      parts.push(`<tr class="same"><th>in GMT <span class="ours">(ours)</span></th>${S.map(s => `<td>${s.utc ? `${Engage.hhmm(Engage.T(s.utc))} GMT, ${esc(dayOf(s.utc))}${s.zone ? "" : ` <span class="ours">zone assumed</span>`}` : none("no time")}</td>`).join("")}</tr>`);
      parts.push(`<tr><th>position as typed</th>${S.map(s => `<td>${s.raw ? `<span class="typed">${esc(s.raw)}</span>${s.role === "record" ? ` <span class="ours">(read from the original)</span>` : ""}` : s.lat != null ? `<span class="ours">a position placed by its entry</span>` : none("none")}</td>`).join("")}</tr>`);
      parts.push(`<tr class="same"><th>placed <span class="ours">(ours)</span></th>${S.map(s => `<td>${s.lat != null ? `${deg(s.lat, "N", "S")} ${deg(s.lon, "E", "W")} · <i>${esc(s.basis || "placed")}</i>` : none("—")}</td>`).join("")}</tr>`);
      parts.push(`<tr><th>the words</th>${S.map(s => `<td>${words(s.words) || none("none")}</td>`).join("")}</tr>`);
      parts.push(`<tr><th>page</th>${S.map(s => `<td class="src">${pageOf(s.cite) || none("no page")}</td>`).join("")}</tr>`);
      if (m.ours && (m.ours.words || m.ours.note)) parts.push(`<tr class="ours-row"><th>what we make of it</th><td colspan="${n}">${esc(m.ours.words)}${m.ours.note ? `. ${esc(m.ours.note)}` : ""} <span class="src">(the boat's claims.yml: ${esc(m.attack)} → ${esc(m.record)}, <i>${esc(m.ours.relation)}</i>)</span></td></tr>`);
      parts.push("</tbody></table></div>");
      const cross = m.apart.filter(x => x.minutes != null || x.nm != null).map(x => {
        const a = S[x.a], b = S[x.b];
        return `<span>${esc(short(a.name))}'s ${/sheet/.test(a.name) ? "sheet" : "entry"} ↔ ${esc(short(b.name))}'s ${b.role === "record" ? "record" : "entry"}: `
          + [x.minutes != null && `<b>${x.minutes} min</b>`, x.nm != null && `<b>${x.nm.toFixed(1)} nm</b>`].filter(Boolean).join(", ")
          + (b.zone ? "" : ` <span class="ours">(its zone assumed)</span>`) + "</span>";
      });
      if (cross.length) parts.push(`<div class="cross">${cross.join("")}</div>`);
      else parts.push(`<p class="cap">The record gives no time and no position for this moment, so there is nothing to compute between the two.</p>`);
    } else {   // a question: its answers by source
      const C = m.columns, n = C.length;
      parts.push(`<h3><span><b>${esc(m.question)}</b></span><span>each source's answer, as typed</span></h3>`);
      parts.push(`<div class="srcs"><table style="--n:${n}"><colgroup><col class="row-head"></colgroup><thead><tr><th></th>${C.map(c => colHead(c.name, "", Engage.sourceKindWord(c.kind, c.of))).join("")}</tr></thead><tbody>`);
      parts.push(`<tr><th>as typed</th>${C.map(c => `<td>${c.answers.map(a => `<div class="a"><b>${esc(a.answer)}</b>${a.note ? `<span class="n">${esc(a.note)}</span>` : ""}${a.weight && a.weight !== c.kind ? `<span class="ours">as ${esc(a.weight)}</span>` : ""}</div>`).join("")}</td>`).join("")}</tr>`);
      parts.push(`<tr><th>page</th>${C.map(c => `<td class="src">${[...new Set(c.answers.map(a => pageOf(a.cite)))].filter(Boolean).join(" ") || none("no page")}</td>`).join("")}</tr>`);
      parts.push("</tbody></table></div>");
    }
    el.classList.add("moment");
    el.innerHTML = parts.join("");
  }
  // The claims board under the Sources view (7.1): each question's answers merged by their words (Engage.claimMoments),
  // badged by the kind of evidence each is (Engage.badge; the marks in sources.css), with every citation.
  function board(el, questions) {
    el.classList.add("board");
    el.innerHTML = questions.map(q => `<div class="q"><h3>${esc(q.question)}</h3><div class="ans">${q.answers.map(a =>
      `<span class="w ${esc(a.mark)}">${esc(a.words || "unweighed")}</span><span class="a"><b>${esc(a.answer)}</b>${a.notes.length ? ` <span class="n">${a.notes.map(esc).join(" ")}</span>` : ""} <span class="src">${[...new Set(a.sources)].filter(Boolean).map(esc).join("; ")} ${a.cites.map(c => cite(c)).join(" ")}</span></span>`).join("")}</div></div>`).join("");
  }

  return { esc, showTip, moveTip, hideTip, cite, sil, category, silWords, land, LAND_10M, LAND_50M, graticule, shape, outcomeMark, legendMark, chronology, sources, board };
})();
