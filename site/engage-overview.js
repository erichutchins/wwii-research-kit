// The engagement map's overview: the convoy's whole voyage on the lanes of the time, and a box where the map below is.
// Drawn in the map's top-right corner, over the map, when the engagement names a convoy with a route
// (records/convoys/convoys.json: each convoy's `route` through reference/lanes/lanes.yml, its `voyage`'s dated stops).
// Encodings as guides/ENGAGEMENTS.md: a leg through an assumed waypoint dotted, a leg straight between two ports dashed
// (nothing traced from a chart: the escorts' route charts are not yet read); the ports open rings, a dated stop a solid
// dot; the box in ink, moved and resized as the map below is zoomed and panned; the convoy's place at the clock, where
// the boats saw it, a hatched dot (ours). The reader can fold it away (the fold remembered for the visit).
const EngageOverview = (() => {
  const esc = s => EV.esc(s);
  function draw(host, { land, lanes, convoys, hatch }) {
    const routed = convoys.filter(c => (c.route || []).length > 1 && c.route.every(k => lanes[k]));
    if (!routed.length) return null;
    const N = lanes;
    const box = document.createElement("div");
    box.className = "overview";
    box.innerHTML = `<button type="button" class="overview-fold" aria-expanded="true" title="Fold the overview away">–</button>
      <div class="overview-body"><svg role="img" aria-label="Overview: the convoy's voyage on the lanes, and where the map is"></svg>
      <div class="overview-cap"></div></div>`;
    host.appendChild(box);
    const KEY = "engage-overview-folded";
    const fold = box.querySelector(".overview-fold"), body = box.querySelector(".overview-body");
    const setFold = on => { body.hidden = on; box.classList.toggle("folded", on); fold.textContent = on ? "overview" : "–";
      fold.setAttribute("aria-expanded", String(!on)); fold.title = on ? "Show the convoy's whole voyage" : "Fold the overview away"; };
    // folded at first on a narrow screen, where it would cover the map; the reader's choice remembered for the visit
    const kept = sessionStorage.getItem(KEY);
    setFold(kept ? kept === "1" : host.clientWidth < 560);
    fold.addEventListener("click", () => { const on = !body.hidden; setFold(on); sessionStorage.setItem(KEY, on ? "1" : "0"); if (!on) render(); });

    const svg = d3.select(box).select("svg");
    const pts = routed.flatMap(c => c.route.map(k => [N[k].lon, N[k].lat]));
    let proj = null, view = null, here = null;
    const W = () => Math.round(Math.min(230, Math.max(120, host.clientWidth * 0.26))), H = () => Math.round(W() * 1.1);
    function render() {
      const w = W(), h = H();
      svg.attr("width", w).attr("height", h).selectAll("*").remove();
      // the voyage and the map's box both in view, a little margin round them
      const all = view ? [...pts, ...view] : pts;
      const [x0, x1] = d3.extent(all, p => p[0]), [y0, y1] = d3.extent(all, p => p[1]), pad = 0.6;
      proj = d3.geoMercator().clipExtent([[0, 0], [w, h]]).fitExtent([[6, 6], [w - 6, h - 6]],
        { type: "MultiPoint", coordinates: [[x0 - pad, y0 - pad], [x1 + pad, y1 + pad]] });
      svg.append("rect").attr("class", "overview-sea").attr("width", w).attr("height", h);
      svg.append("path").attr("class", "land").attr("d", d3.geoPath(proj)(land));
      const P = (lon, lat) => proj([lon, lat]);
      routed.forEach(c => d3.pairs(c.route).forEach(([a, b]) => {
        const assumed = N[a].assumed || N[b].assumed;
        svg.append("path").attr("class", "overview-leg" + (assumed ? " assumed" : "")).attr("d", `M${P(N[a].lon, N[a].lat)}L${P(N[b].lon, N[b].lat)}`)
          .on("mouseenter", ev => EV.showTip(ev, `<div class="v">${esc(c.convoy)}: ${esc(N[a].name)} to ${esc(N[b].name)}</div><div class="i">${assumed ? `an assumed route: ${esc(N[a].assumed || N[b].assumed)}` : "straight between two ports"}; the lanes of the time (reference/lanes/lanes.yml), not traced from a chart</div>`))
          .on("mousemove", EV.moveTip).on("mouseleave", EV.hideTip);
      }));
      const ports = [...new Set(routed.flatMap(c => c.route))].filter(k => N[k].port);
      ports.forEach(k => {
        const [x, y] = P(N[k].lon, N[k].lat), right = x < w * 0.6;
        svg.append("circle").attr("class", "overview-port").attr("cx", x).attr("cy", y).attr("r", 3);
        svg.append("text").attr("class", "overview-name").attr("x", x + (right ? 6 : -6)).attr("y", y + 4).attr("text-anchor", right ? "start" : "end").text(N[k].name);
      });
      // the voyage's dated stops, the record's (the convoy's own page has them all)
      routed.forEach(c => (c.voyage || []).filter(v => N[v.place]).forEach(v => {
        const [x, y] = P(N[v.place].lon, N[v.place].lat);
        svg.append("circle").attr("cx", x).attr("cy", y).attr("r", 2.4).attr("fill", "var(--ink)")
          .on("mouseenter", ev => EV.showTip(ev, `<div class="v">${esc(c.convoy)}: ${esc(v.event || "")} ${esc(N[v.place].name)}</div><div class="k">${esc(v.at)}</div><div class="i">${esc(v.source)}</div>`))
          .on("mousemove", EV.moveTip).on("mouseleave", EV.hideTip);
      }));
      if (view) {
        const [[wl, s], [e, n]] = [view[0], view[1]], a = P(wl, n), b = P(e, s);
        const bw = Math.max(5, b[0] - a[0]), bh = Math.max(5, b[1] - a[1]);
        svg.append("rect").attr("class", "overview-box").attr("x", (a[0] + b[0]) / 2 - bw / 2).attr("y", (a[1] + b[1]) / 2 - bh / 2).attr("width", bw).attr("height", bh)
          .on("mouseenter", ev => EV.showTip(ev, `<div class="v">The map below</div><div class="i">where the boats met the convoy; it follows the map as you zoom</div>`))
          .on("mousemove", EV.moveTip).on("mouseleave", EV.hideTip);
      }
      svg.append("g").attr("class", "overview-now");
      drawHere();
    }
    function drawHere() {
      const g = svg.select("g.overview-now");
      g.selectAll("*").remove();
      if (here && proj) g.append("circle").attr("cx", proj(here)[0]).attr("cy", proj(here)[1]).attr("r", 3.6).attr("fill", hatch).attr("stroke", "var(--ink)").attr("stroke-width", 1.2);
    }
    const names = routed.map(c => `<a href="subject.html?s=${encodeURIComponent(c.id)}">${esc(c.convoy)}</a> ${esc([c.from, c.to].filter(Boolean).join(" → "))}${/^\d{4}/.test(c.sailed || "") ? `, sailed ${esc(E8(c.sailed))}` : ""}`);
    box.querySelector(".overview-cap").innerHTML = `${names.join("; ")}. <i>Its lane, through assumed waypoints, not its track</i>; the box is the map.`;
    render();
    return {
      // the map's view, [[west, south], [east, north]]: the box (the overview refitted to hold it and the voyage)
      view(b) { view = b; if (!body.hidden) render(); },
      // the convoy's place at the clock (as the boats saw it), or null
      here(p) { here = p; drawHere(); },
      resize: render,
    };
  }
  // "1944-04-28" -> "28 Apr 1944"
  function E8(s) { const d = new Date(s.slice(0, 10) + "T00:00Z"); return isNaN(d) ? s : d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" }); }
  return { draw };
})();
