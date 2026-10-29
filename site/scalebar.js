// A distance ruler for a map, kept true as the reader zooms. The page owns its projection and zoom; it calls
// update() whenever the view changes, with a function that turns a point on the map's box (px) into [lon, lat].
//
//   const ruler = scaleBar(hostElement, { units: ["nm"] });          // sea maps; ["km", "mi"] for land
//   ruler.update(([x, y]) => proj.invert(transform.invert([x, y])));
//
// The ruler measures across the middle of the map, so on a Mercator map it is right for the map's centre latitude
// (its tooltip says so). Each unit gets its own bar, a round length (1, 2 or 5 × a power of ten) no wider than MAX px.
function scaleBar(host, { units = ["nm"], at = "bottom-left", max = 120 } = {}) {
  if (!document.getElementById("scalebar-style")) {
    const style = document.createElement("style");
    style.id = "scalebar-style";
    // either page family's colours: viz.css (--text-..., --border) or home.css, battle.html, haynsworth.html (--ink...)
    style.textContent = `
      .scalebar { position: absolute; left: 10px; bottom: var(--scalebar-bottom, 10px); z-index: 2; pointer-events: auto;
        padding: 3px 6px 2px; border-radius: 2px; font: 12.5px/1.2 var(--font-ui, var(--serif, Georgia, serif));
        color: var(--text-secondary, var(--ink-2)); background: color-mix(in srgb, var(--surface-1, var(--surface, var(--paper, #fff)))
        85%, transparent); border: 1px solid var(--border, var(--rule)); }
      .scalebar.bottom-right { left: auto; right: 10px; }
      .scalebar.top-left { bottom: auto; top: 10px; }
      .scalebar .row { display: flex; align-items: center; gap: 6px; white-space: nowrap; }
      .scalebar .bar { height: 5px; border: 1.5px solid currentColor; border-top: 0; box-sizing: border-box; }
      .scalebar[hidden] { display: none; }`;
    document.head.append(style);
  }
  if (getComputedStyle(host).position === "static") host.style.position = "relative";
  const el = document.createElement("div");
  el.className = `scalebar ${at}`;
  el.title = "Distance at the middle of the map; it changes as you zoom";
  host.append(el);
  const M = { nm: 1852, km: 1000, mi: 1609.344 };
  const R = 6371008.8;
  const metres = ([l1, p1], [l2, p2]) => {
    const r = Math.PI / 180;
    return 2 * R * Math.asin(Math.sqrt(Math.sin((p2 - p1) * r / 2) ** 2 + Math.cos(p1 * r) * Math.cos(p2 * r) * Math.sin((l2 - l1) * r / 2) ** 2));
  };
  const nice = v => { const e = 10 ** Math.floor(Math.log10(v)), f = v / e; return (f >= 5 ? 5 : f >= 2 ? 2 : 1) * e; };
  const fmt = v => v >= 1 ? String(Math.round(v)) : String(+v.toPrecision(1));
  return {
    el,
    update(invert) {
      const w = host.clientWidth, h = host.clientHeight;
      if (!w || !h) return;
      const a = invert([w / 2 - 50, h / 2]), b = invert([w / 2 + 50, h / 2]);
      if (!a || !b || a.some(v => !isFinite(v)) || b.some(v => !isFinite(v))) { el.hidden = true; return; }
      const mpp = metres(a, b) / 100;
      if (!(mpp > 0)) { el.hidden = true; return; }
      el.hidden = false;
      el.innerHTML = units.map(u => {
        const d = nice(max * mpp / M[u]), px = d * M[u] / mpp;
        return `<div class="row"><div class="bar" style="width:${px.toFixed(1)}px"></div><span>${fmt(d)} ${u}</span></div>`;
      }).join("");
    },
  };
}
