// The marks every map carries (CLAUDE.md, "Pages"): a north arrow and a distance ruler, kilometres over statute miles
// on land, nautical miles at sea. Two forms, one computation.
//
// An interactive map, kept true as the reader zooms. The page owns its projection and zoom; it calls update() whenever
// the view changes, with a function that turns a point on the map's box (px) into [lon, lat]:
//
//   const ruler = scaleBar(hostElement, { units: ["nm"] });          // sea maps; ["km", "mi"] for land
//   ruler.update(([x, y]) => proj.invert(transform.invert([x, y])));
//
// A static map (an SVG drawn once, a figure or a panel), the marks drawn into the SVG itself:
//
//   mapMarks(svg, p => proj.invert(p), W, H, { units: ["km", "mi"] });
//
// The ruler measures across the middle of the map, so on a Mercator map it is right for the map's centre latitude
// (its tooltip says so). Each unit gets its own bar, a round length (1, 2 or 5 × a power of ten) no wider than MAX px.
// North is worked out the same way, from the point straight above the map's middle, so a rotated, conic or zoomed
// view points the arrow where north is there.
const MAPMARKS = (() => {
  const M = { nm: 1852, km: 1000, mi: 1609.344 };
  const R = 6371008.8, r = Math.PI / 180;
  const metres = ([l1, p1], [l2, p2]) =>
    2 * R * Math.asin(Math.sqrt(Math.sin((p2 - p1) * r / 2) ** 2 + Math.cos(p1 * r) * Math.cos(p2 * r) * Math.sin((l2 - l1) * r / 2) ** 2));
  const nice = v => { const e = 10 ** Math.floor(Math.log10(v)), f = v / e; return (f >= 5 ? 5 : f >= 2 ? 2 : 1) * e; };
  const fmt = v => v >= 1 ? String(Math.round(v)) : String(+v.toPrecision(1));
  const ok = p => p && p.every(v => isFinite(v));
  // metres per px across the middle, and north's angle there (degrees clockwise from straight up), or null
  function measure(invert, w, h) {
    const a = invert([w / 2 - 50, h / 2]), b = invert([w / 2 + 50, h / 2]);
    const c = invert([w / 2, h / 2]), up = invert([w / 2, h / 2 - 20]);
    if (!ok(a) || !ok(b) || !ok(c) || !ok(up)) return null;
    const mpp = metres(a, b) / 100;
    if (!(mpp > 0)) return null;
    const dl = (up[0] - c[0]) * r, p1 = c[1] * r, p2 = up[1] * r;
    const bearing = Math.atan2(Math.sin(dl) * Math.cos(p2), Math.cos(p1) * Math.sin(p2) - Math.sin(p1) * Math.cos(p2) * Math.cos(dl));
    return { mpp, north: -bearing / r };
  }
  const bars = (units, mpp, max) => units.map(u => { const d = nice(max * mpp / M[u]); return { px: d * M[u] / mpp, words: `${fmt(d)} ${u}` }; });
  // the arrow, pointing up before its rotation; the N stays upright at its tip
  const arrow = (deg, k = 1) => {
    const t = deg * r, nx = Math.sin(t) * 13 * k, ny = -Math.cos(t) * 13 * k;
    return `<g class="north-arrow" transform="rotate(${deg.toFixed(1)})"><path d="M0,${-9 * k} L${3.6 * k},${2 * k} L0,${-0.5 * k} L${-3.6 * k},${2 * k}Z" fill="currentColor"/>`
      + `<path d="M0,${-0.5 * k}V${7 * k}" stroke="currentColor" stroke-width="1.2"/></g>`
      + `<text x="${nx.toFixed(1)}" y="${(ny + 3.5).toFixed(1)}" text-anchor="middle" font-weight="600" fill="currentColor">N</text>`;
  };
  return { measure, bars, arrow };
})();

function scaleBar(host, { units = ["nm"], at = "bottom-left", max = 120 } = {}) {
  if (!document.getElementById("scalebar-style")) {
    const style = document.createElement("style");
    style.id = "scalebar-style";
    // the pages' shared tokens (viz.css): --ink..., --rule, --surface, --wash
    style.textContent = `
      .scalebar { position: absolute; left: 10px; bottom: var(--scalebar-bottom, 10px); z-index: 2; pointer-events: auto;
        display: flex; align-items: center; gap: 8px;
        padding: 3px 6px 2px; border-radius: 2px; font: 12.5px/1.2 var(--serif);
        color: var(--ink-2); background: color-mix(in srgb, var(--surface)
        85%, transparent); border: 1px solid var(--rule); }
      .scalebar.bottom-right { left: auto; right: 10px; }
      .scalebar.top-left { bottom: auto; top: 10px; }
      div.scalebar > svg.north { position: static; inset: auto; margin: 0; width: 26px; height: 32px; flex: none; }   /* over a page's own map svg rules */
      div.scalebar > svg.north text { font: 11px var(--serif); }
      .scalebar .sb-row { display: flex; align-items: center; gap: 6px; white-space: nowrap; }
      .scalebar .sb-bar { height: 5px; border: 1.5px solid currentColor; border-top: 0; box-sizing: border-box; }
      .scalebar[hidden] { display: none; }`;
    document.head.append(style);
  }
  if (getComputedStyle(host).position === "static") host.style.position = "relative";
  const el = document.createElement("div");
  el.className = `scalebar ${at}`;
  el.title = "North, and the distance at the middle of the map; it changes as you zoom";
  host.append(el);
  return {
    el,
    update(invert) {
      const w = host.clientWidth, h = host.clientHeight;
      if (!w || !h) return;
      const m = MAPMARKS.measure(invert, w, h);
      if (!m) { el.hidden = true; return; }
      el.hidden = false;
      el.innerHTML = `<svg class="north" viewBox="-15 -18 30 36" aria-label="north">${MAPMARKS.arrow(m.north)}</svg>`
        + `<div class="sb-rows">${MAPMARKS.bars(units, m.mpp, max).map(b =>
          `<div class="sb-row"><div class="sb-bar" style="width:${b.px.toFixed(1)}px"></div><span>${b.words}</span></div>`).join("")}</div>`;
    },
  };
}

// The same marks drawn into a static SVG (a d3 selection or an element) of W × H, in a corner (`at`), clear of a
// margin `pad`. `max` is the longest bar in px; a small map gets a small one.
function mapMarks(svg, invert, W, H, { units = ["nm"], at = "bottom-right", max = Math.min(90, W * 0.22), pad = 6 } = {}) {
  const node = svg.node ? svg.node() : svg;
  const m = MAPMARKS.measure(invert, W, H);
  node.querySelector(":scope > g.mapmarks")?.remove();
  if (!m) return null;
  const bs = MAPMARKS.bars(units, m.mpp, max), bw = Math.max(...bs.map(b => b.px));
  const small = W < 260, fs = small ? 9 : 11, rowH = small ? 11 : 13, arrowW = small ? 16 : 22;
  const w = arrowW + 6 + Math.max(bw, ...bs.map(b => b.words.length * fs * 0.5)) + 8, h = Math.max(bs.length * rowH + 6, small ? 26 : 34);
  const x = at.endsWith("left") ? pad : W - pad - w, y = at.startsWith("top") ? pad : H - pad - h;
  const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
  g.setAttribute("class", "mapmarks");
  g.setAttribute("transform", `translate(${x.toFixed(1)},${y.toFixed(1)})`);
  g.setAttribute("style", `color: var(--ink-2); font: ${fs}px var(--serif)`);
  g.setAttribute("pointer-events", "none");
  const k = small ? 0.75 : 1;
  g.innerHTML = `<rect width="${w.toFixed(1)}" height="${h}" rx="2" fill="var(--surface)" fill-opacity="0.85" stroke="var(--rule)"/>`
    + `<g transform="translate(${(arrowW / 2 + 3).toFixed(1)},${(h / 2 + 4 * k).toFixed(1)})">${MAPMARKS.arrow(m.north, k)}</g>`
    + bs.map((b, i) => {
      const bx = arrowW + 6, by = 4 + i * rowH + rowH * 0.55;
      return `<path d="M${bx},${by - 4}V${by}H${(bx + b.px).toFixed(1)}V${by - 4}" fill="none" stroke="currentColor" stroke-width="1.2"/>`
        + `<text x="${(bx + b.px + 4).toFixed(1)}" y="${by + 1}" fill="currentColor">${b.words}</text>`;
    }).join("");
  // the text sits after each bar: widen the box to hold the longest bar and its words
  const need = arrowW + 6 + Math.max(...bs.map(b => b.px + 4 + b.words.length * fs * 0.56)) + 8;
  g.querySelector("rect").setAttribute("width", need.toFixed(1));
  if (!at.endsWith("left")) g.setAttribute("transform", `translate(${(W - pad - need).toFixed(1)},${y.toFixed(1)})`);
  node.append(g);
  return g;
}
