// Zoom and pan for the maps that don't build their own (the front page, zones.html, battle.html, haynsworth.html):
// the +, − and ⟲ buttons the map pages have (patrols.html), drag to pan, pinch or ⌘/Ctrl-scroll to zoom.
//
//   const view = mapZoom(svgNode, hostElement, t => redraw(t), { capture, max, at });
//
// The page draws; this only reports the view. onZoom(transform) runs on every change, and the page either rescales its
// projection by it (battle.html, zones.html: see mapZoom.scaled) or moves its layers and keeps its marks their size
// (index.html). capture: true is for a map that fills its page (battle.html): the scroll wheel and a one-finger drag
// move the map, as on patrols.html. Otherwise the page is one you read down: a plain scroll and a one-finger swipe
// still move the page, and a note on the map says how to zoom it.
// at: where the buttons sit ("top-right", "bottom-right", "top-left"); row: side by side rather than stacked, for a short map.
function mapZoom(svgNode, host, onZoom, { capture = false, max = 16, min = 1, at = "top-right", row = false } = {}) {
  if (!document.getElementById("mapzoom-style")) {
    const style = document.createElement("style");
    style.id = "mapzoom-style";
    // either page family's colours: viz.css (--text-..., --border) or home.css, battle.html, haynsworth.html (--ink...)
    style.textContent = `
      .zoom-btns { position: absolute; right: 10px; top: 10px; display: flex; flex-direction: column; gap: 4px; z-index: 3; }
      .zoom-btns.bottom-right { top: auto; bottom: 30px; }
      .zoom-btns.top-left { right: auto; left: 10px; }
      .zoom-btns.row { flex-direction: row; }
      .zoom-btns button { font: 21.5px/1 var(--serif, Georgia, serif); width: 30px; height: 30px; padding: 0; border-radius: 2px;
        cursor: pointer; background: var(--surface-1, var(--surface, var(--paper)));
        color: var(--text-secondary, var(--ink-2)); border: 1px solid var(--border, var(--rule)); }
      .zoom-btns button:hover { background: var(--wash); color: var(--text-primary, var(--ink)); }
      .zoom-note { position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%); z-index: 3; pointer-events: none;
        padding: 6px 12px; border-radius: 3px; font: 16px var(--serif, Georgia, serif); white-space: nowrap;
        background: color-mix(in srgb, var(--surface-1, var(--surface, var(--paper))) 92%, transparent);
        color: var(--text-primary, var(--ink)); border: 1px solid var(--border, var(--rule));
        box-shadow: 0 2px 10px rgba(0,0,0,0.12); opacity: 0; transition: opacity 180ms; }
      .zoom-note.on { opacity: 1; }
      svg.zoomable { cursor: grab; }
      svg.zoomable:active { cursor: grabbing; }
      @media (pointer: coarse) { .zoom-btns button { width: 40px; height: 40px; } }
      @media (prefers-reduced-motion: reduce) { .zoom-note { transition: none; } }`;
    document.head.append(style);
  }
  const svg = d3.select(svgNode).classed("zoomable", true);
  if (getComputedStyle(host).position === "static") host.style.position = "relative";

  const mac = /Mac|iPhone|iPad/.test(navigator.platform);
  const zoom = d3.zoom().scaleExtent([min, max])
    .filter(e => {
      if (e.type === "wheel") return capture || e.ctrlKey || e.metaKey;
      if (e.type.startsWith("touch")) return capture || e.touches.length > 1;
      return !e.ctrlKey && !e.button;
    })
    // a trackpad pinch arrives as small ctrl-wheel steps; a mouse wheel with Ctrl held, as big ones
    .wheelDelta(e => -e.deltaY * (e.deltaMode === 1 ? 0.05 : e.deltaMode ? 1 : 0.002) * (e.ctrlKey && Math.abs(e.deltaY) < 40 ? 10 : 1))
    .on("zoom", e => onZoom(e.transform, e));
  svg.call(zoom).on("dblclick.zoom", null);

  // the buttons
  const btns = document.createElement("div");
  btns.className = `zoom-btns ${at}${row ? " row" : ""}`;
  const button = (label, text, act) => {
    const b = document.createElement("button");
    b.type = "button"; b.textContent = text; b.setAttribute("aria-label", label); b.title = label;
    b.addEventListener("click", act);
    btns.append(b);
  };
  const ease = sel => matchMedia("(prefers-reduced-motion: reduce)").matches ? sel : sel.transition().duration(350);
  button("Zoom in", "+", () => ease(svg).call(zoom.scaleBy, 1.8));
  button("Zoom out", "−", () => ease(svg).call(zoom.scaleBy, 1 / 1.8));
  button("Reset the view", "⟲", () => view.reset());
  host.append(btns);

  // on a page you read down, a scroll or a swipe that passes over the map says how to move it
  if (!capture) {
    const note = document.createElement("div");
    note.className = "zoom-note"; note.setAttribute("aria-hidden", "true");
    host.append(note);
    let hide;
    const say = text => { note.textContent = text; note.classList.add("on"); clearTimeout(hide); hide = setTimeout(() => note.classList.remove("on"), 1300); };
    svgNode.addEventListener("wheel", e => { if (!e.ctrlKey && !e.metaKey) say(`${mac ? "⌘" : "Ctrl"} + scroll to zoom the map`); }, { passive: true });
    svgNode.addEventListener("touchmove", e => { if (e.touches.length === 1) say("Two fingers to move the map"); }, { passive: true });
  }

  const view = {
    zoom,
    transform: () => d3.zoomTransform(svgNode),
    reset: () => ease(svg).call(zoom.transform, d3.zoomIdentity),
    // set the view without an animation
    set: t => svg.call(zoom.transform, t),
    // pan only within the map as drawn (the box it was fitted to), at any zoom
    bound: (W, H) => { zoom.extent([[0, 0], [W, H]]).translateExtent([[0, 0], [W, H]]); },
  };
  return view;
}

// A fitted projection's scale and translate, zoomed by t: every point it gives lands where t would move it
// (p -> t.k * p + t.x), so a page that draws through its projection redraws at the reader's view.
mapZoom.scaled = (proj, base, t) => proj.scale(base.scale * t.k).translate([base.translate[0] * t.k + t.x, base.translate[1] * t.k + t.y]);
