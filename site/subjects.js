// subjects.html: the index of every subject (records/subjects.json, tools/build_subjects.py) by kind and theatre, each
// row opening subject.html?s=<id>. The convoys' section is the ledger convoys.html kept until phase 6: one row per convoy
// with what the records give (● from a Japanese record, ◐ only from a secondary source, ○ not found yet), read from
// records/convoys/convoys.json, so it doubles as the list of what to look for next.
(async () => {
  const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const [ALL, J] = await Promise.all([fetch(RECORDS + "subjects.json").then(r => r.json()),
    fetch(RECORDS + "convoys/convoys.json").then(r => r.ok ? r.json() : { convoys: [] }).catch(() => ({ convoys: [] }))]);
  const href = s => `subject.html?s=${encodeURIComponent(s.alias || s.id)}`;
  const link = (s, text) => `<a href="${esc(href(s))}">${text || esc(s.short || s.name)}</a>`;
  const mon = d3.utcFormat("%b %Y"), T = s => s ? Date.parse(`${String(s).slice(0, 10)}T12:00Z`) : NaN;
  const span = s => !s.first || !s.last ? "" : mon(T(s.first)) === mon(T(s.last)) ? mon(T(s.first)) : `${mon(T(s.first))} – ${mon(T(s.last))}`;
  const THEATRE = { pacific: "Pacific", atlantic: "Atlantic", mediterranean: "Mediterranean", europe: "Europe", home: "In the United States only", "": "No record of its own yet" };
  const hullNo = s => +(/\d+/.exec(s.hull || "") || [0])[0];
  const out = [];

  // boats and ships: by hull number, each patrol a link
  // `side`: our ships, or the other side's (each followed through a record she kept herself), each in its own list
  const vessels = (kind, title, note, side = "us") => {
    const xs = ALL.filter(s => s.kind === kind && (s.of || "us") === side).sort((a, b) => hullNo(a) - hullNo(b) || a.name.localeCompare(b.name));
    if (!xs.length) return;
    out.push(`<h2>${title}</h2><p class="key">${note}</p><div class="ledger-wrap"><table class="ledger"><thead><tr><th>Subject</th><th>What it was</th><th>${kind === "boat" ? "Patrols" : "Record"}</th><th>When</th><th class="num">Positions</th><th>Status</th></tr></thead><tbody>${xs.map(s => {
      const periods = kind === "boat" ? s.periods.map(p => `<a href="${esc(href(s))}&amp;period=${p.n}" title="${esc(`${p.name}, ${p.dates}${p.area ? `: ${p.area}` : ""}`)}">${p.n}</a>`).join(" ") : esc(s.periods[0]?.name || "");
      const fixes = s.periods.reduce((a, p) => a + (p.fixes || 0), 0);
      const status = [...new Set(s.periods.map(p => p.status).filter(Boolean))].join(", ") + (s.periods[0]?.months ? ` · ${s.periods[0].months.filter(m => /mapped|partial/.test(m.status)).length} of ${s.periods[0].months.length} months` : "");
      return `<tr><td class="nm">${link(s, esc(s.name))}</td><td class="plain">${esc(s.plain)}</td><td class="pn">${periods}</td><td class="st">${esc(span(s))}</td><td class="num">${fixes}</td><td class="st">${esc(status)}</td></tr>`;
    }).join("")}</tbody></table></div>`);
  };
  vessels("boat", "Submarines", "War patrol reports (NARA series 305243); each patrol opens the boat's page on that patrol.");
  vessels("ship", "Surface ships", "War diaries (NARA RG 38). Most of the carriers, battleships and cruisers are read for 6 April 1945 only, the day USS Haynsworth was hit.");
  vessels("ship", "Japanese ships", "Each followed through a record she kept herself: her war diary or battle report (JACAR), in Tokyo time (zone I). A ship only named in another's record stays a name in it.", "jp");

  // Army units, by theatre
  const units = ALL.filter(s => s.kind === "unit");
  if (units.length) {
    out.push(`<h2>Army units</h2><p class="key">Morning reports (NARA RG 64), battalion histories and journals, the ETO order of battle; each row is the unit's record, never a person's.</p>`);
    for (const th of ["europe", "mediterranean", "home", ""]) {
      const xs = units.filter(s => s.theatre === th).sort((a, b) => (a.first || "9").localeCompare(b.first || "9") || a.name.localeCompare(b.name));
      if (!xs.length) continue;
      out.push(`<h3>${THEATRE[th]}</h3><div class="ledger-wrap"><table class="ledger"><thead><tr><th>Unit</th><th>What it was</th><th>When</th><th class="num">Stations</th><th>Engagements</th><th>Status</th></tr></thead><tbody>${xs.map(s =>
        `<tr><td class="nm">${link(s, esc(s.name))}</td><td class="plain">${esc(s.plain)}</td><td class="st">${esc(span(s))}</td><td class="num">${s.records.stations || 0}</td><td>${s.engagements.map(e => `<a href="engagement.html?e=${esc(e.id)}">${esc(e.short || e.title)}</a>`).join(", ")}</td><td class="st">${esc(s.status || "")}</td></tr>`).join("")}</tbody></table></div>`);
    }
  }

  // Seabee battalions
  const bns = ALL.filter(s => s.kind === "battalion");
  if (bns.length) out.push(`<h2>Seabee battalions</h2><p class="key">Muster rolls (NARA RG 24) and the Bureau of Yards and Docks' history sheets.</p><div class="ledger-wrap"><table class="ledger"><thead><tr><th>Battalion</th><th>What it was</th><th>When</th><th class="num">Stations</th><th class="num">Parts</th><th class="num">Projects</th><th>Status</th></tr></thead><tbody>${bns.map(s =>
    `<tr><td class="nm">${link(s, esc(s.name))}</td><td class="plain">${esc(s.plain)}</td><td class="st">${esc(span(s))}</td><td class="num">${s.records.stations || 0}</td><td class="num">${s.records.parts || 0}</td><td class="num">${s.records.projects || 0}</td><td class="st">${esc(s.status || "")}</td></tr>`).join("")}</tbody></table></div>`);

  // the convoys: the ledger, as convoys.html kept it
  const CV = J.convoys || [];
  if (CV.length) {
    const sunk = c => c.ships.filter(s => /^sunk/.test(s.fate || "")).length;
    const grade = xs => xs.some(s => s.basis === "reported" || s.basis === "inferred") ? "●" : xs.length ? "◐" : "○";
    const words = { "●": "from a Japanese record", "◐": "only from a secondary source", "○": "not found yet" };
    const dot = (g, what) => `<td class="dot" title="${esc(what)}: ${words[g]}">${g}</td>`;
    const route = c => [c.from, ...(c.via || []), c.to].filter(Boolean).join(" → ");
    out.push(`<h2>Convoys</h2><p class="key">Each convoy as its own escorts' records give it (the escort divisions' war diaries and charts, via JACAR); a secondary source, flagged, fills the gaps. ● from a Japanese record · ◐ only from a secondary source · ○ not found yet. A row with open circles is what to look for next.</p>
      <div class="ledger-wrap"><table class="ledger"><thead><tr><th>Convoy</th><th>What it was</th><th>Route</th><th>Met</th><th>Boats</th><th class="num">Ships named</th><th class="num">Sunk</th>
      <th title="Its sailing, from any record">Sailing</th><th title="Its ships, as named">Ships</th><th title="Its escorts">Escorts</th><th title="Stops along the way">Stops</th><th title="Where the boats saw it">Seen</th></tr></thead>
      <tbody>${CV.map(c => {
        const S = ALL.find(s => s.id === c.id) || { id: c.id, alias: c.id, plain: "" };
        const merch = c.ships.filter(s => !/escort/.test(s.role)), esc_ = c.ships.filter(s => /escort/.test(s.role));
        const sailing = c.voyage.find(v => v.event === "sailed");
        return `<tr><td class="nm"><a href="${esc(href(S))}">${esc(c.convoy)}</a> ${c.name_ja ? `<span lang="ja" data-tr="Convoy ${esc(c.convoy)}, as the Japanese records write it">${esc(c.name_ja)}</span>` : ""}</td><td class="plain">${esc(S.plain)}</td><td>${esc(route(c))}</td>
          <td>${c.engagements.map(e => `<a href="engagement.html?e=${esc(e.id)}">${esc(e.short)}</a>`).join(", ")}</td><td>${esc(c.boats.map(b => b.name).join(", "))}</td>
          <td class="num">${c.ships.length}</td><td class="num">${sunk(c)}</td>
          ${dot(sailing ? (sailing.basis === "secondary" ? "◐" : "●") : /secondary/.test(c.sailed || "") ? "◐" : c.sailed ? "●" : "○", "Sailing")}
          ${dot(grade(merch), "Ships")}${dot(grade(esc_), "Escorts")}${dot(c.voyage.filter(v => v.event !== "sailed").length ? grade(c.voyage) : "○", "Stops")}
          ${dot(c.sightings.length ? "●" : "○", "Seen by the boats")}</tr>`;
      }).join("")}</tbody></table></div>`);
  }

  // commands
  const cmds = ALL.filter(s => s.kind === "command");
  if (cmds.length) out.push(`<h2>Commands</h2><div class="ledger-wrap"><table class="ledger"><thead><tr><th>Command</th><th>What it was</th><th>Transcribed</th><th>Found</th></tr></thead><tbody>${cmds.map(s =>
    `<tr><td class="nm">${link(s, esc(s.name))}</td><td class="plain">${esc(s.plain)}</td><td class="st">${s.periods.filter(p => /transcribed|mapped/.test(p.status)).map(p => esc(mon(T(p.month + "-15")))).join(", ")}</td><td class="st">${s.periods.filter(p => p.status === "available").length} months found, not transcribed</td></tr>`).join("")}</tbody></table></div>`);

  document.getElementById("index").innerHTML = out.join("");
})();
