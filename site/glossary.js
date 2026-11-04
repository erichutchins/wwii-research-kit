// The glossary: explains the records' abbreviations and terms, and links the ships (to subject.html), without crowding the page.
// Reads reference/glossary.json (built by tools/build_glossary.py from the hand-edited glossary.yml, whose header says
// how) and records/ships.json. Only the first use of a term on the page is marked, including what the page's script draws later (lists, panels, steps): a dotted underline, no
// colour. Pointing at it, focusing it or tapping it opens a small card with the explanation, its source (linked) and,
// for a ship, a link to its track. Skipped: links, buttons, form controls, headings, the nav, the footer, SVG, Japanese,
// the map tooltips (#tip), and anything inside [data-no-gloss].
// The records' notations (glossary.json's `patterns`: a time with its zone letter, a grid reference, a kana position code,
// an attack sheet's angles) are marked the same way, each distinct value once per passage; their card names the notation,
// shows the value in the typed voice (a zone-lettered time with its GMT when engage.js is on the page), the explanation,
// its source, and a link to the explainer page opened at that value.
// The same card gives the English of any original quoted in its own language: an element with `lang` and `data-tr`
// (the page's script sets the translation there as it draws the entry) opens it on hover, focus or tap, whatever the
// page, even where the translation is also printed under the original.
// Paths are relative to this script, so the family pages (which load it as kit/site/glossary.js) work too.
(() => {
  const HERE = new URL(".", document.currentScript.src);
  const KIT = new URL("../", HERE);
  const SKIP = "a, button, select, option, input, textarea, label, script, style, svg, h1, h2, h3, h4, nav, footer, code, " +
               "[lang='ja'], #tip, .gloss, .gloss-card, [data-no-gloss]";

  const style = document.createElement("style");
  style.textContent = `
    .gloss { text-decoration: underline dotted; text-decoration-thickness: 1px; text-underline-offset: 3px;
             text-decoration-color: color-mix(in srgb, currentColor 55%, transparent); cursor: help; }
    .gloss:hover, .gloss:focus-visible { text-decoration-color: currentColor; }
    [data-tr] { cursor: help; text-decoration: underline dotted; text-decoration-thickness: 1px; text-underline-offset: 4px;
                text-decoration-color: color-mix(in srgb, currentColor 35%, transparent); }
    [data-tr]:hover, [data-tr]:focus-visible { text-decoration-color: currentColor; }
    .gloss-card .gloss-tr { font-size: 16px; line-height: 1.45; }
    .gloss-card .gloss-lang { display: block; margin-top: 5px; font-size: 13px; color: var(--ink-2); font-style: italic; }
    .gloss-card { position: absolute; z-index: 1000; max-width: min(340px, calc(100vw - 24px)); padding: 9px 12px 10px;
      font: 15.5px/1.45 et-book, Palatino, "Palatino Linotype", Georgia, serif; font-style: normal; font-weight: normal;
      color: var(--ink); background: var(--surface);
      border: 1px solid var(--rule); border-radius: 6px; box-shadow: 0 4px 14px rgba(0,0,0,.12); }
    .gloss-card b { display: block; font-weight: 600; margin-bottom: 2px; }
    .gloss-card .gloss-val { display: block; margin: 1px 0 4px; font-family: var(--typed, "TT2020 Style E", "Courier New", monospace); font-size: 14.5px; }
    .gloss-card .gloss-val .gloss-gmt { font-family: et-book, Palatino, Georgia, serif; font-size: 13.5px; color: var(--ink-2); }
    .gloss-card a { color: inherit; display: inline-block; margin-top: 4px; }
    .gloss-card .gloss-src { display: block; margin-top: 5px; font-size: 13px; color: var(--ink-2); }
    .gloss-card .gloss-src a { margin-top: 0; }`;
  document.head.append(style);

  // if glossary.json is missing, the ships are still linked and the console says why the terms aren't explained
  const ready = Promise.all([
    fetch(new URL("reference/glossary.json", KIT)).then(r => r.ok ? r.json() : Promise.reject(new Error(r.status)))
      .catch(err => { console.warn(`glossary.json didn't load, so terms aren't explained: ${err.message}`); return {}; }),
    fetch(new URL("records/ships.json", KIT)).then(r => r.ok ? r.json() : []).catch(() => []),
  ]).then(([g, ships]) => build(g, ships));

  const reEsc = s => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const exact = s => /[A-Z]{2}/.test(s);          // AAA, CP, Med Det, BANG: match exactly; ordinary words ignore case

  // One entry per thing to explain; each with the forms that find it. Ships: "USS Name", "Name (HULL)", a submarine's
  // name in capitals as the reports type it, and the bare name only where glossary.yml's ships.bare allows it.
  function build(g, ships) {
    const entries = [];
    for (const t of g.terms || []) {
      entries.push({ title: t.term, says: t.says, see: t.see && new URL(t.see, HERE).href,
        seeText: "More", sources: t.sources || [], forms: [t.term, ...(t.match || [])] });
      // phrases that contain the term but mean something else ("AP Hill"): found first (they're longer), never marked
      if (t.unless?.length) entries.push({ skip: true, forms: t.unless });
    }
    const bare = new Set(g.ships?.bare || []);
    const here = new URLSearchParams(location.search).get("s");   // the subject page's own ship isn't linked to itself
    for (const s of ships) {
      const forms = [`USS ${s.name}`, `${s.name} (${s.hull})`];
      if (s.kind === "submarine" || bare.has(s.name)) forms.push(s.name);
      const self = here && [s.alias, s.key, s.name.toLowerCase()].includes(here.toLowerCase());
      entries.push({ title: `USS ${s.name} (${s.hull})`,
        says: `${s.class ? s.class + "-class " : ""}${s.kind}.`,
        see: self ? null : new URL(`site/subject.html?s=${encodeURIComponent(s.alias)}`, KIT).href,
        seeText: s.kind === "submarine" ? "Her patrols, on her own page" : "Her war diary, on her own page", forms });
    }
    // longest forms first, so "USS Haynsworth" wins over "Haynsworth" and "AAA" over "AA"
    const forms = entries.flatMap(e => e.forms.map(f => ({ f, e }))).sort((a, b) => b.f.length - a.f.length);
    const byExact = new Map(), byLower = new Map();
    for (const { f, e } of forms) (exact(f) ? byExact : byLower).set(exact(f) ? f : f.toLowerCase(), e);
    if (!forms.length) return null;
    // an abbreviation followed by digits is a grid reference ("VT 0893", "RN 25"), not the abbreviation
    const alt = forms.map(({ f }) => exact(f) ? `(?:${reEsc(f)})` : `(?:(?i:${reEsc(f)}))`);
    let re;
    try { re = new RegExp(`(?<![\\w-])(${alt.join("|")})(?![\\w-])(?![\\s-]*\\d)`, "g"); }
    catch { // engines without inline (?i:): fall back to a case-sensitive match of each form and its capitalised form
      const cap = s => s[0].toUpperCase() + s.slice(1);
      const plain = forms.flatMap(({ f }) => exact(f) ? [f] : [f, cap(f)]).map(reEsc);
      re = new RegExp(`(?<![\\w-])(${plain.join("|")})(?![\\w-])(?![\\s-]*\\d)`, "g");
    }
    return { re, find: m => byExact.get(m) || byLower.get(m.toLowerCase()), patterns: patterns(g) };
  }

  // The notations: each pattern as glossary.yml wrote it (a form both engines read alike), compiled here; one that
  // doesn't compile in this browser is reported and skipped, and a glossary.json without `patterns` has none.
  const PAGE_NAME = { zones: "zones", grids: "grids", jgrid: "Japanese grid", german: "German grids", torpedo: "torpedo" };
  function patterns(g) {
    const out = [];
    for (const p of g.patterns || []) {
      try { out.push({ ...p, re: new RegExp(p.pattern, "g") }); }
      catch (err) { console.warn(`glossary pattern ${p.id} skipped: ${err.message}`); }
    }
    return out;
  }
  // "zones.html?zone=$2" with the match's groups filled in, and the link's words
  function seeOf(p, m) {
    if (!p.see) return null;
    const href = p.see.replace(/\$(\d)/g, (_, n) => encodeURIComponent(m[+n] ?? ""));
    const page = PAGE_NAME[p.see.split(".")[0]] || p.see.split(".")[0];
    return { href: new URL(href, HERE).href, text: `See it on the ${page} page` };
  }
  // A zone-lettered time's GMT, when engage.js's zone arithmetic is on the page (never redone here): with a date from
  // the element (data-date, or a time[datetime] around it) the instant, otherwise the zone's offset alone
  function gmtOf(span, m) {
    // engage.js declares Engage with const, so it is a global binding, not a property of window
    const E = typeof Engage !== "undefined" ? Engage : null;   // eslint-disable-line no-undef
    if (!E || !E.zoneHours) return "";
    let h;
    try { h = E.zoneHours(m[2]); } catch { return ""; }
    const sign = h < 0 ? "−" : "+", a = Math.abs(h), hh = Number.isInteger(a) ? a : `${Math.floor(a)}½`;
    const off = h === 0 ? "GMT" : `GMT${sign}${hh}`;
    const date = span.closest("[data-date]")?.getAttribute("data-date") || span.closest("time[datetime]")?.getAttribute("datetime") || "";
    const d = /^\d{4}-\d{2}-\d{2}/.exec(date);
    if (!d || !E.toUTC) return off;
    const t = new Date(E.toUTC(d[0], m[1], m[2]));
    if (Number.isNaN(+t)) return off;
    const pad = n => String(n).padStart(2, "0");
    return `${pad(t.getUTCHours())}${pad(t.getUTCMinutes())} GMT, ${t.getUTCDate()} ${["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][t.getUTCMonth()]} ${t.getUTCFullYear()} (${off})`;
  }

  // Mark the first use of each entry on the page. A long page can mark a part as its own passage, where each term is
  // marked again, with data-gloss-passage (e.g. a chapter a reader jumps straight to).
  // The page remembers the use it marked; if the page's script redraws that panel and the mark is gone, the next use
  // is marked instead (so a station's note, redrawn as the reader moves along the timeline, keeps its mark).
  const PASSAGE = "[data-gloss-passage]";
  const marked = new WeakMap();                 // passage element -> Map(entry -> its marked span)
  function mark(roots, G) {
    const nodes = [];
    for (const root of roots) {
      if (!root || root.nodeType !== 1 || root.closest(SKIP)) continue;
      const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
        acceptNode: n => n.data.trim().length < 2 || n.parentElement.closest(SKIP) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT });
      while (walker.nextNode()) nodes.push(walker.currentNode);
    }
    for (const node of nodes) {
      const key = node.parentElement.closest(PASSAGE) || document.body;
      const seen = marked.get(key) || marked.set(key, new Map()).get(key);
      G.re.lastIndex = 0;
      const text = node.data, found = [], here = new Set();   // here: marked in this text, not yet on the page
      let m;
      // the terms first (a term's phrase can hold digits a notation would claim), then each notation where no term is
      while ((m = G.re.exec(text))) {
        const e = G.find(m[1]);
        if (!e || e.skip) continue;
        found.push({ at: m.index, end: m.index + m[1].length, text: m[1], e, key: e });
      }
      for (const p of G.patterns) {
        p.re.lastIndex = 0;
        while ((m = p.re.exec(text))) {
          if (!m[0]) { p.re.lastIndex++; continue; }
          const at = m.index, end = at + m[0].length;
          if (found.some(f => f.at < end && at < f.end)) continue;
          const key = `${p.id}\0${m[0]}`;   // a distinct value once per passage
          const see = seeOf(p, m);
          found.push({ at, end, text: m[0], key, e: { pattern: p, m: [...m], title: p.name, says: p.says,
            see: see && see.href, seeText: see && see.text, sources: p.sources || [] } });
        }
      }
      found.sort((a, b) => a.at - b.at);
      const parts = [];
      let at = 0;
      for (const f of found) {
        if (f.at < at || here.has(f.key) || seen.get(f.key)?.isConnected) continue;
        here.add(f.key);
        parts.push(text.slice(at, f.at));
        const span = document.createElement("span");
        span.className = "gloss"; span.tabIndex = 0; span.textContent = f.text;
        span.setAttribute("role", "button"); span.setAttribute("aria-label", `${f.text}: what this means`);
        span.__gloss = f.e;
        seen.set(f.key, span);
        parts.push(span);
        at = f.end;
      }
      if (parts.length) { parts.push(text.slice(at)); node.replaceWith(...parts); }
    }
  }

  // An original in its own language: the translation the page's script put in data-tr opens the card too
  const LANG = { ja: "Japanese", de: "German", fr: "French", it: "Italian" };
  const OWNERS = ".gloss, [data-tr]";
  function markTr(roots) {
    for (const root of roots) {
      if (!root || root.nodeType !== 1) continue;
      const els = root.matches("[data-tr]") ? [root] : [];
      els.push(...root.querySelectorAll("[data-tr]"));
      for (const el of els) if (!el.hasAttribute("tabindex")) {
        el.tabIndex = 0; el.setAttribute("role", "button"); el.setAttribute("aria-label", "the English of this");
      }
    }
  }

  // The card: one, reused; hover or focus opens it, tap toggles it, Escape or a tap elsewhere closes it.
  const card = document.createElement("div");
  card.className = "gloss-card"; card.setAttribute("role", "tooltip"); card.hidden = true;
  let owner = null, hideTimer = null, shownAt = 0;
  function show(span) {
    clearTimeout(hideTimer);
    if (owner !== span || card.hidden) shownAt = Date.now();
    const e = span.__gloss; owner = span;
    card.replaceChildren();
    if (span.hasAttribute("data-tr")) {
      const b = document.createElement("b"); b.textContent = "In English";
      const t = document.createElement("span"); t.className = "gloss-tr"; t.textContent = span.getAttribute("data-tr");
      card.append(b, t);
      const from = LANG[span.getAttribute("lang")];
      const s = document.createElement("span"); s.className = "gloss-lang";
      s.textContent = from ? `Our translation; the ${from} is the record's own words.` : "Our translation; the original is the record's own words.";
      card.append(s);
    } else {
    const b = document.createElement("b"); b.textContent = e.title;
    card.append(b);
    if (e.pattern) {   // a notation: the value as typed, and a zone-lettered time's GMT
      const v = document.createElement("span"); v.className = "gloss-val"; v.textContent = span.textContent;
      const gmt = e.pattern.id === "zone-time" ? gmtOf(span, e.m) : "";
      if (gmt) { const g = document.createElement("span"); g.className = "gloss-gmt"; g.textContent = ` = ${gmt}`; v.append(g); }
      card.append(v);
    }
    card.append(document.createTextNode(e.says || ""));
    if (e.see) { const a = document.createElement("a"); a.href = e.see; a.textContent = `${e.seeText} →`; card.append(document.createElement("br"), a); }
    if (e.sources?.length) {
      const src = document.createElement("span"); src.className = "gloss-src"; src.append("Source: ");
      e.sources.forEach((s, i) => {
        const a = document.createElement("a"); a.href = s.href; a.target = "_blank"; a.rel = "noopener";
        // a second page of the same source reads "another page", not its name again
        a.textContent = e.sources.slice(0, i).some(p => p.short === s.short) ? "another page" : s.short;
        if (s.title) a.title = s.title;
        src.append(...(i ? ["; ", a] : [a]));
      });
      card.append(src);
    }
    }
    if (!card.isConnected) document.body.append(card);
    card.hidden = false;
    const r = span.getBoundingClientRect(), w = card.offsetWidth, h = card.offsetHeight;
    const left = Math.max(12, Math.min(r.left, innerWidth - w - 12));
    const top = r.bottom + 6 + h > innerHeight && r.top > h + 6 ? r.top - h - 6 : r.bottom + 6;
    card.style.left = `${left + scrollX}px`; card.style.top = `${top + scrollY}px`;
  }
  const hide = () => { hideTimer = setTimeout(() => { card.hidden = true; owner = null; }, 120); };
  document.addEventListener("mouseover", ev => { const s = ev.target.closest?.(OWNERS); if (s) show(s); else if (ev.target.closest?.(".gloss-card")) clearTimeout(hideTimer); });
  document.addEventListener("mouseout", ev => { if (ev.target.closest?.(OWNERS + ", .gloss-card")) hide(); });
  document.addEventListener("focusin", ev => { if (ev.target.matches?.(OWNERS)) show(ev.target); });
  document.addEventListener("focusout", ev => { if (ev.target.matches?.(OWNERS)) hide(); });
  document.addEventListener("click", ev => {
    const s = ev.target.closest?.(OWNERS);
    // a tap on a phone fires mouseover (which opens the card) just before click: that click must not close it again
    if (s) { ev.preventDefault(); ev.stopPropagation();
      if (owner === s && !card.hidden && Date.now() - shownAt > 500) { card.hidden = true; owner = null; } else show(s); return; }
    if (!ev.target.closest?.(".gloss-card")) { card.hidden = true; owner = null; }
  }, true);
  document.addEventListener("keydown", ev => {
    if (ev.key === "Escape") { card.hidden = true; owner = null; }
    if ((ev.key === "Enter" || ev.key === " ") && ev.target.matches?.(OWNERS)) { ev.preventDefault(); show(ev.target); }
  });

  // The page as it loads, then whatever the page's script draws later (lists, panels, steps).
  ready.then(G => {
    const go = () => {
      if (G) mark([document.body], G);
      markTr([document.body]);
      const pending = new Set();
      let queued = false;
      const obs = new MutationObserver(records => {
        for (const r of records) for (const n of r.addedNodes)
          if (n.nodeType === 1 && !n.classList.contains("gloss") && !n.classList.contains("gloss-card")) pending.add(n);
          else if (n.nodeType === 3 && r.target.nodeType === 1 && !r.target.classList.contains("gloss")) pending.add(r.target);
        if (pending.size && !queued) {
          queued = true;
          requestAnimationFrame(() => {
            obs.disconnect();
            // only the outermost of what was added (a list of 100 stations is walked once, not once per row)
            const outer = [...pending].filter(n => n.isConnected && ![...pending].some(p => p !== n && p.contains(n)));
            if (G) mark(outer, G);
            markTr(outer);
            pending.clear(); queued = false;
            obs.observe(document.body, { childList: true, subtree: true });
          });
        }
      });
      obs.observe(document.body, { childList: true, subtree: true });
    };
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", go); else go();
  });
})();
