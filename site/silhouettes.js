// Recognition silhouettes, in the manner of the wartime plates. The shapes and the plates they come from are
// data: records/silhouettes/silhouettes.yml (hand-edited, every shape cited), built into silhouettes.json by
// tools/build_silhouettes.py. This file loads them and draws the plan-view hull used for map symbols.
//
// SILHOUETTES is a promise; when it resolves, AIRCRAFT (traced aircraft: plan, front and profile views, span
// 100 units), SHIPS (ship profiles in feet, stern at x = 0, waterline at y = 0, with `d` ready to draw) and
// SIL_CATEGORIES (one generic shape per kind of ship, viewBox 0 0 120 24) are set on window. The JSON is found
// relative to this script, so a page anywhere can load it from wherever the kit is.

const SILHOUETTES_URL = new URL("../records/silhouettes/silhouettes.json", document.currentScript.src).href;
const SILHOUETTES = fetch(SILHOUETTES_URL).then(r => r.json()).then(s => {
  Object.assign(window, { AIRCRAFT: s.aircraft, SHIPS: s.ships, SIL_CATEGORIES: s.categories });
  return s;
});

// Plan view of a hull for map symbols, bow up, length 1 and beam as a fraction of length.
function hullPlan(beam = 0.11) {
  const b = beam / 2;
  return `M${-b * 0.9},0.5L${-b},-0.15Q${-b * 0.95},-0.38 0,-0.5Q${b * 0.95},-0.38 ${b},-0.15L${b * 0.9},0.5Z`;
}
