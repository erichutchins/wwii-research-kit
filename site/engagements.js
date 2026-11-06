// engagements.html: the index of every engagement (records/engagements/index.json, tools/build_engagement.py), by
// theatre and in date order, each row opening engagement.html?e=<id>: its dates, its lede in plain words (the build's),
// the subjects in it with their own pages, and what the page holds, every number counted by the build from the
// engagement's own files, never written in.
(async () => {
  const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const ALL = await fetch(RECORDS + "engagements/index.json").then(r => r.json());
  const THEATRES = [["pacific", "Pacific"], ["atlantic", "Atlantic"], ["mediterranean", "Mediterranean"], ["europe", "Europe"]];
  const n = (k, one, many = one + "s") => `${k} ${k === 1 ? one : many}`;
  // the dates as the spine gives them (chapter.js): one day, or the first and the last
  const day = s => Date.parse(String(s).slice(0, 10) + "T00:00Z");
  const fmt = d3.utcFormat("%-d %b %Y"), fmtDM = d3.utcFormat("%-d %b"), fmtD = d3.utcFormat("%-d");
  const dates = e => {
    const a = day(e.from), b = day(e.to || e.from);
    if (a === b) return fmt(a);
    const A = new Date(a), B = new Date(b);
    if (A.getUTCFullYear() === B.getUTCFullYear() && A.getUTCMonth() === B.getUTCMonth()) return `${fmtD(a)}–${fmt(b)}`;
    if (A.getUTCFullYear() === B.getUTCFullYear()) return `${fmtDM(a)} – ${fmt(b)}`;
    return `${fmt(a)} – ${fmt(b)}`;
  };
  const subjectHref = s => `subject.html?s=${encodeURIComponent(s.id)}${s.period ? `&amp;period=${encodeURIComponent(s.period)}` : ""}`;
  const holds = e => [n(e.entries, "entry", "entries") + (e.languages > 1 ? ` in ${n(e.languages, "language")}` : ""),
    e.claims && `${n(e.claims, "question")} the records leave open`, e.fronts && n(e.fronts, "situation map"),
    e.steps && `the story in ${n(e.steps, "step")}`, e.sheets && n(e.sheets, "attack sheet")].filter(Boolean).join(" · ");
  const row = e => `<div class="dates">${esc(dates(e))}</div>
    <div class="eng">
      <h3><a href="engagement.html?e=${encodeURIComponent(e.id)}">${esc(e.title)}</a></h3>
      ${e.lede ? `<p>${esc(e.lede)}</p>` : ""}
      <div class="with">${e.subjects.length ? `<i>with</i> ${e.subjects.map(s => `<a href="${subjectHref(s)}">${esc(s.name)}</a>`).join(", ")} · ` : ""}${esc(holds(e))}</div>
    </div>`;
  const out = [];
  for (const [id, name] of THEATRES) {
    const xs = ALL.filter(e => e.theater === id);
    if (!xs.length) continue;
    out.push(`<h2><a href="theatre.html?t=${id}">${name}</a> <span class="k">${n(xs.length, "engagement")} · <a href="theatre.html?t=${id}">the theatre</a>, its operations and every subject with a record there</span></h2>
      <div class="engs">${xs.map(row).join("")}</div>`);
  }
  document.getElementById("index").innerHTML = out.join("");
  const theatres = new Set(ALL.map(e => e.theater)).size;
  document.getElementById("count").textContent = `${n(ALL.length, "engagement")} so far, in ${n(theatres, "theatre")}, in date order.`;
})();
