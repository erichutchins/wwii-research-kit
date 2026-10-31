// The computation every engagement page shares (guides/ENGAGEMENTS.md, "Computation"). Positions, clocks, tracks,
// distances, fire control, apparent size and the sky are worked out here, once, and never stored: what a page computes
// is a lead until a record says so. Tested by `node site/engage.test.js`.
//
//   Engage.zoneHours("K")             10: a Navy zone letter's hours ahead of GMT (A-M east without J, N-Y west, Z = 0)
//   Engage.toUTC("1944-05-03", "0603", "H")   milliseconds GMT
//   Engage.T(s)                       an ISO time as the build writes it ("1944-05-03T22:03Z") -> ms; a local time with
//                                     no zone ("1943-05-12T23:40") is held as if GMT, for ordering on a local clock
//   Engage.coord("19-21N")            19.35 (degrees; minutes may carry decimals; "?" in a digit -> null)
//   Engage.offset(lon, lat, brg, nm)  [lon, lat] that bearing and distance away (short distances, plane sailing)
//   Engage.nm(a, b)                   great-circle distance in nautical miles between [lon, lat] points
//   Engage.posAt(pts, ms)             [lon, lat] along a track of {utc, lon, lat}, straight between fixes, never beyond
//                                     the first or last fix (null outside them)
//   Engage.observedPath(points)       a convoy's path from where it was seen (other boats' contacts, the Japanese
//                                     record's positions): sorted, one point per minute
//   Engage.closing(track, path, n)    [{ms, nm}] from a boat's track to the convoy's path, only while both are known
//   Engage.fireControl({...})         torpedo course, track angle, lead angle and angle on the bow from the attack sheet
//   Engage.apparentSize({...})        a target's angular width and height at a range and angle on the bow
//   Engage.sky(ms, lat, lon)          sun and moon: bearing, altitude, the moon's phase and lit fraction (SunCalc)
const Engage = (() => {
  const ZONE_LETTERS_E = "ABCDEFGHIKLM", ZONE_LETTERS_W = "NOPQRSTUVWXY";
  // the half-hour zones the war diaries type (tools/check_track.py ZONES)
  const HALF = { KL: 10.5, IK: 9.5, LM: 11.5, TU: -7.5, UV: -8.5, VW: -9.5, WX: -10.5, XY: -11.5 };
  function zoneHours(z) {
    if (z === "Z") return 0;
    if (z in HALF) return HALF[z];
    const e = ZONE_LETTERS_E.indexOf(z), w = ZONE_LETTERS_W.indexOf(z);
    if (e >= 0) return e + 1;
    if (w >= 0) return -(w + 1);
    throw new Error(`zone ${z} is not a zone letter`);
  }
  const pad = n => String(n).padStart(2, "0");
  function toUTC(date, hhmm, zone) {
    const [y, m, d] = date.split("-").map(Number);
    return Date.UTC(y, m - 1, d, +hhmm.slice(0, 2), +hhmm.slice(2, 4)) - zoneHours(zone) * 3600e3;
  }
  function T(s) {
    if (s == null || s === "") return null;
    if (/^\d{4}-\d{2}$/.test(s)) s += "-01";
    if (/^\d{4}-\d{2}-\d{2}$/.test(s)) s += "T12:00";
    return Date.parse(/Z$/.test(s) ? s : s + "Z");
  }
  function coord(s) {
    const m = /^(\d+)-(\d+(?:\.\d+)?)(?:-(\d+(?:\.\d+)?))?([NSEW])$/.exec(String(s || "").trim());
    if (!m) return null;
    const v = +m[1] + m[2] / 60 + (m[3] ? m[3] / 3600 : 0);
    return /[SW]/.test(m[4]) ? -v : v;
  }
  const rad = d => d * Math.PI / 180, deg = r => r * 180 / Math.PI;
  function offset(lon, lat, brg, dist) {
    const dlat = dist * Math.cos(rad(brg)) / 60;
    return [lon + dist * Math.sin(rad(brg)) / (60 * Math.cos(rad(lat))), lat + dlat];
  }
  function nm(a, b) {
    const [l1, p1, l2, p2] = [rad(a[0]), rad(a[1]), rad(b[0]), rad(b[1])];
    const c = Math.sin(p1) * Math.sin(p2) + Math.cos(p1) * Math.cos(p2) * Math.cos(l2 - l1);
    return deg(Math.acos(Math.min(1, Math.max(-1, c)))) * 60;
  }
  function posAt(pts, ms) {
    if (!pts || !pts.length) return null;
    const t0 = T(pts[0].utc), t1 = T(pts[pts.length - 1].utc);
    if (ms < t0 || ms > t1) return null;
    for (let i = 1; i < pts.length; i++) {
      const a = pts[i - 1], b = pts[i], ta = T(a.utc), tb = T(b.utc);
      if (ms <= tb) { const k = tb === ta ? 1 : (ms - ta) / (tb - ta); return [a.lon + (b.lon - a.lon) * k, a.lat + (b.lat - a.lat) * k]; }
    }
    return [pts[pts.length - 1].lon, pts[pts.length - 1].lat];
  }
  function observedPath(points) {
    const byMinute = new Map();
    points.filter(p => p.utc && p.lat != null && p.lon != null).forEach(p => {
      const k = T(p.utc), q = byMinute.get(k);
      if (q) { q.lon = (q.lon * q.n + p.lon) / (q.n + 1); q.lat = (q.lat * q.n + p.lat) / (q.n + 1); q.n++; q.from.push(p); }
      else byMinute.set(k, { utc: p.utc, lon: p.lon, lat: p.lat, n: 1, from: [p] });
    });
    return [...byMinute.values()].sort((a, b) => T(a.utc) - T(b.utc));
  }
  function closing(track, path, steps = 120) {
    if (!track.length || path.length < 2) return [];
    const lo = Math.max(T(track[0].utc), T(path[0].utc)), hi = Math.min(T(track[track.length - 1].utc), T(path[path.length - 1].utc));
    if (!(hi > lo)) return [];
    const out = [];
    for (let i = 0; i <= steps; i++) {
      const ms = lo + (hi - lo) * i / steps, a = posAt(track, ms), b = posAt(path, ms);
      if (a && b) out.push({ ms, nm: nm(a, b) });
    }
    return out;
  }
  // Fire control (USF 25(A); docs: submarine-tactics.md in the family repository): courses in degrees true, speeds in knots.
  //   torpedo course = own course + gyro angle; track angle = torpedo course + 180 - target course;
  //   lead angle L: tan L = k sin(TA) / (1 + k cos(TA)), k = target speed / torpedo speed; angle on the bow = TA - L.
  const norm = a => ((a % 360) + 360) % 360;
  function fireControl({ ownCourse, gyro, targetCourse, targetSpeed, torpedoSpeed }) {
    const torpedoCourse = norm(ownCourse + gyro);
    const track = norm(torpedoCourse + 180 - targetCourse);
    const ta = track > 180 ? track - 360 : track, k = targetSpeed / torpedoSpeed;
    const lead = deg(Math.atan2(k * Math.sin(rad(ta)), 1 + k * Math.cos(rad(ta))));
    return { torpedoCourse, track: Math.abs(ta), side: ta >= 0 ? "S" : "P", lead, aob: ta - lead };
  }
  // A target's apparent size: projected length = L |sin AOB| + beam |cos AOB|; width = 2 atan(projected / 2R); height = atan(H / R).
  function apparentSize({ length, beam, height, range, aob }) {
    const proj = length * Math.abs(Math.sin(rad(aob))) + beam * Math.abs(Math.cos(rad(aob)));
    return { width: deg(2 * Math.atan(proj / 2 / range)), height: deg(Math.atan(height / range)), projected: proj };
  }
  // The sky, from SunCalc (loaded by the page): azimuths from north, clockwise, in degrees true.
  function sky(ms, lat, lon) {
    const S = typeof SunCalc !== "undefined" ? SunCalc : null;
    if (!S) return null;
    const d = new Date(ms), sun = S.getPosition(d, lat, lon), moon = S.getMoonPosition(d, lat, lon), ill = S.getMoonIllumination(d);
    const az = a => norm(deg(a) + 180);
    return { sun: { bearing: az(sun.azimuth), altitude: deg(sun.altitude) },
             moon: { bearing: az(moon.azimuth), altitude: deg(moon.altitude), fraction: ill.fraction, phase: ill.phase, waxing: ill.phase < 0.5 } };
  }
  // A built engagement (engagement.json) as the story pages (haynsworth.html, algiers.html) read it: its own entries in
  // the order events.yml gives them, with the record's date and time apart, and the claims; `ref` is the page's link.
  function story(D) {
    const timeline = D.events.filter(e => e.origin === "events").sort((a, b) => a.n - b.n).map(e => ({
      date: e.local.slice(0, 10), time: e.local.slice(11, 15), placed: e.placed || "", side: e.side, actor: e.actor, kind: e.kind,
      text: e.words, source: e.source || "", ref: e.cite.href, pos: e.pos || "", step: e.step || "" }));
    const claims = D.claims.map(c => ({ question: c.question, claim: c.answer, weight: c.weight, source: c.source || "", ref: c.cite.href, note: c.note || "" }));
    return { timeline, claims };
  }
  const MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const hhmm = ms => { const d = new Date(ms); return pad(d.getUTCHours()) + pad(d.getUTCMinutes()); };
  const day = ms => { const d = new Date(ms); return `${d.getUTCDate()} ${MON[d.getUTCMonth()]}`; };
  return { zoneHours, toUTC, T, coord, offset, nm, posAt, observedPath, closing, fireControl, apparentSize, sky, story, hhmm, day };
})();
if (typeof module !== "undefined") module.exports = Engage;
