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
//   Engage.localNoon(ms, zone)        ms of local noon (in that zone letter) on the same local date
//   Engage.light(sky, nightVision)    {day, L, V}: daylight 0-1, the light 0-1 and how far a ship shows (yards,
//                                     illustrative); nightVision lifts L and V as a dark-adapted eye or an image
//                                     intensifier might (illustrative, not from a source), the sun and moon unchanged
//   Engage.attackSheet(rows, {length, beam})   an attack data sheet (attacks.csv's rows for one attack) on one clock: each
//                                     torpedo's firing second, course and run, each target placed from the gyro and
//                                     track, and the list of what's assumed
//   Engage.attackAt(A, s)             the boat, the targets and the torpedoes s seconds after the first torpedo
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
  function localNoon(ms, zone) {
    const local = ms + zoneHours(zone || "Z") * 3600e3, d = new Date(local);
    return ms + (Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate(), 12) - local);
  }
  // How far a ship shows is illustrative: daylight from the sun's altitude (0 below -6 degrees, 1 above +6), the moon
  // adding by its lit fraction and height. Night vision lifts the darkness (illustrative, not from a source).
  function light(sk, nightVision) {
    const m = sk.moon, day = Math.max(0, Math.min(1, (sk.sun.altitude + 6) / 12));
    const moonLight = m.altitude > 0 ? m.fraction * Math.sqrt(Math.sin(rad(m.altitude))) : 0;
    let L = Math.min(1, day + (1 - day) * (0.04 + 0.5 * moonLight)), V = 600 + 18000 * day + (1 - day) * 3400 * moonLight;
    if (nightVision) { L = Math.max(L, 0.5); V = Math.max(V, 8000); }
    return { day, L, V };
  }
  // ---------- an attack data sheet (attacks.csv's rows, as typed) worked through on one clock: seconds from the first
  // torpedo, yards, x east and y north, the boat at the origin when she fired. Every value is the sheet's except those
  // listed in `assumed`, which the page shows.
  const num = s => { const m = /^\s*(\d+(?:\.\d+)?)\s*$/.exec(s ?? ""); return m ? +m[1] : null; };
  // '162' -> 162; right or left of the bow, '15R' -> 15, '5L' -> 355
  const gyroOf = s => { const m = /^\s*(\d+(?:\.\d+)?)\s*([RL]?)\s*$/.exec(s ?? ""); return m ? (m[2] === "L" ? norm(-m[1]) : +m[1]) : null; };
  // '050' -> [50]; a course swinging while firing, '050-069' -> [50, 69]; a zig, '210 - 260' -> [210, 260]
  const coursesOf = s => { const v = String(s ?? "").split("-").map(num); return v.length && v.every(x => x != null) ? v : []; };
  // an aim off the point of aim in degrees, right positive: '1.5R' -> 1.5, '1L' -> -1, '0' -> 0; along the target ('225'Aft') -> null
  const offsetOf = s => { const m = /^\s*(\d+(?:\.\d+)?)\s*([RL]?)\s*$/.exec(s ?? ""); return m ? (m[2] === "L" ? -m[1] : +m[1]) : null; };
  // seconds into the day of a typed time: '2354' or, with seconds, '1616-32'
  const secOf = s => { const m = /^(\d\d)(\d\d)(?:-(\d\d))?$/.exec(s ?? ""); return m ? m[1] * 3600 + m[2] * 60 + (+m[3] || 0) : null; };
  // Torpedo speeds where the sheet types none. The Mark 18's is ATULE's sheet's "Mk 18 speed 27.7" (rg367-74802211/p33),
  // which SEAHORSE's narrative bears out (560 yards in 36 seconds, rg367-74845019/p09); the Mark 14's and 23's are
  // commonly given figures, not yet from a primary source (ENGAGEMENTS.md, "Still to build"). A typed speed is always used.
  const TORPEDO_KNOTS = { "14": { high: 46, low: 31.5 }, "23": { high: 46 }, "18": { high: 27.7 } };
  const YD_S = kn => kn * 2025.37 / 3600;   // knots -> yards a second
  function torpedoKnots(r) {
    const typed = num(r.power);
    if (typed) return { knots: typed, basis: "sheet" };
    const mark = String(r.torpedo || "").split("-")[0], mk = TORPEDO_KNOTS[mark] || TORPEDO_KNOTS["14"];
    return { knots: /^low/i.test(r.power || "") && mk.low ? mk.low : mk.high, basis: mark === "18" ? "atule" : "assumed" };
  }
  const SALVO_GAP = 10;   // seconds: a salvo whose own time the sheet doesn't give starts this long after the last
  function firingTimes(rows) {
    const t0 = secOf(rows[0].time);
    let base = 0, last = 0;
    return rows.map((r, i) => {
      const ts = secOf(r.time), typedLater = ts != null && t0 != null && ts > t0;
      const iv = r.since_first != null ? num(r.since_first) : num(r.interval), since = r.since_first != null;
      if (i === 0) return { s: 0 };
      if (iv === null || iv === 0) {          // a dash, a blank or 0 after the first: the next salvo
        base = typedLater ? Math.max(ts - t0, last) : last + SALVO_GAP;
        last = base;
        return { s: base, assumed: !typedLater };
      }
      last = since ? base + iv : last + iv;
      return { s: last };
    });
  }
  function attackSheet(rows, opts = {}) {
    const assumed = [], problems = [];
    const n = rows.length, tf = firingTimes(rows);
    const own = rows.map((r, i) => { const c = coursesOf(r.own_course); return c.length ? c[0] + (c.length > 1 && n > 1 ? (c[c.length - 1] - c[0]) * i / (n - 1) : 0) : null; });
    const swinging = rows.some(r => coursesOf(r.own_course).length > 1);
    const ownSpeed = num(rows[0].own_speed) ?? 0;
    const surface = rows.some(r => /surface/i.test(r.own_depth || "")) || (num(rows[0].own_depth) ?? 99) < 25;
    if (own.some(c => c == null)) problems.push("the sheet types no own course");
    if (tf.some(x => x.assumed)) assumed.push(`a salvo the sheet gives no time for starts ${SALVO_GAP} s after the last torpedo`);
    // one target for each set of target data the rows carry (a sheet may aim at two)
    const key = r => [r.target_course, r.target_speed, r.target_range].join("|");
    const groups = [...new Set(rows.map(key))];
    const torps = rows.map((r, i) => {
      const g = gyroOf(r.gyro), sp = torpedoKnots(r);
      return { i, tube: r.tube, row: r, s: tf[i].s, timeAssumed: !!tf[i].assumed, course: own[i] != null && g != null ? norm(own[i] + g) : null,
               knots: sp.knots, speedBasis: sp.basis, offset: offsetOf(r.offset), hitTyped: /hit/i.test(r.hit || ""), target: groups.indexOf(key(r)) };
    });
    if (torps.some(t => t.speedBasis === "atule")) assumed.push("the Mark 18's speed, 27.7 knots: not typed on this sheet, but on ATULE's (rg367-74802211/p33)");
    if (torps.some(t => t.speedBasis === "assumed")) assumed.push("the Mark 14's and 23's speed, 46 knots at high power and 31.5 at low: not typed on the sheet; secondary figures");
    if (swinging) assumed.push("own course turning evenly between the typed courses while firing");
    assumed.push("each torpedo on its course from the moment it leaves the tube (its straight run and turn onto the gyro angle are left out, so runs come out a few seconds short)",
                 "the boat steady on the sheet's course and speed", "the target steady on the sheet's course and speed, before firing as after: the narrative's bearings aren't transcribed yet");
    const ownAt = s => {   // the boat: steady speed; the heading turning evenly across a swing
      const last = tf[n - 1].s || 1, k = Math.max(0, Math.min(1, s / last)), h = own[0] == null ? 0 : own[0] + ((own[n - 1] ?? own[0]) - own[0]) * (swinging ? k : 0);
      // position: integrate the heading (straight where it doesn't swing)
      const steps = swinging ? 12 : 1; let x = 0, y = 0;
      for (let j = 0; j < steps; j++) { const sj = s * (j + 0.5) / steps, kj = Math.max(0, Math.min(1, sj / last)), hj = own[0] == null ? 0 : own[0] + ((own[n - 1] ?? own[0]) - own[0]) * (swinging ? kj : 0);
        x += Math.sin(rad(hj)) * YD_S(ownSpeed) * s / steps; y += Math.cos(rad(hj)) * YD_S(ownSpeed) * s / steps; }
      return { p: [x, y], heading: norm(h) };
    };
    const targets = groups.map((gk, gi) => {
      const ts = torps.filter(t => t.target === gi), r = ts[0].row;
      const course = coursesOf(r.target_course)[0], speed = num(r.target_speed) ?? 0, range = num(r.target_range);
      const zig = coursesOf(r.target_course).length > 1;
      // the point of aim: the torpedoes' courses, less each one's typed offset; with no offsets typed, their mean
      const first = ts.filter(t => t.s - ts[0].s < 30 && t.course != null);
      const aims = first.map(t => t.offset != null ? t.course - t.offset : t.course);
      if (course == null || range == null || !aims.length) return { course, speed, range, ok: false };
      const aim = norm(aims[0] + d3mean(aims.map(a => ((a - aims[0] + 540) % 360) - 180)));
      const sp = d3mean(first.map(t => t.knots));
      const fc = fireControl({ ownCourse: aim, gyro: 0, targetCourse: course, targetSpeed: speed, torpedoSpeed: sp });
      const signedAob = fc.aob;   // fireControl's aob is already signed (starboard +, port -)
      const bearing = norm(course + signedAob + 180), at = ts[0].s, from = ownAt(at).p;
      const p0 = [from[0] + range * Math.sin(rad(bearing)), from[1] + range * Math.cos(rad(bearing))];
      return { course, speed, range, zig, ok: true, bearing, aob: signedAob, lead: fc.lead, track: fc.track, side: fc.side, at, p0, typedTrack: r.track,
               noOffsets: first.every(t => t.offset == null) && first.length > 1 };
    });
    if (targets.some(t => t.zig)) assumed.push("the target on the first of the courses typed for its zig");
    if (targets.some(t => t.noOffsets)) assumed.push("the point of aim in the middle of the spread (the sheet types the kind of spread, not each torpedo's offset)");
    if (targets.some(t => !t.ok)) problems.push("the sheet doesn't give the target's course and range, so the target can't be placed");
    const targetAt = (gi, s) => { const T = targets[gi]; if (!T.ok) return null; const v = YD_S(T.speed);
      return [T.p0[0] + Math.sin(rad(T.course)) * v * (s - T.at), T.p0[1] + Math.cos(rad(T.course)) * v * (s - T.at)]; };
    // each torpedo's run: to where it first reaches the target's hull (a line of the target's length, `opts.length`
    // feet, on its course), or, missing, how far from the hull it passed
    const halfL = (opts.length || 400) / 6, halfB = (opts.beam || 55) / 6;   // feet -> half the length and beam in yards
    torps.forEach(t => {
      const T = targets[t.target];
      if (t.course == null || !T.ok) return;
      const from = ownAt(t.s).p, v = YD_S(t.knots), vt = [Math.sin(rad(t.course)) * v, Math.cos(rad(t.course)) * v];
      const tp = targetAt(t.target, t.s), u = [Math.sin(rad(T.course)), Math.cos(rad(T.course))], vT = [u[0] * YD_S(T.speed), u[1] * YD_S(T.speed)];
      const r0 = [from[0] - tp[0], from[1] - tp[1]], dv = [vt[0] - vT[0], vt[1] - vT[1]];   // the torpedo, from the target
      const gap = tau => { const x = r0[0] + dv[0] * tau, y = r0[1] + dv[1] * tau, along = x * u[0] + y * u[1], across = x * u[1] - y * u[0];
        return Math.hypot(Math.max(0, Math.abs(along) - halfL), Math.max(0, Math.abs(across) - halfB)); };
      const centre = Math.max(0, -(r0[0] * dv[0] + r0[1] * dv[1]) / (dv[0] ** 2 + dv[1] ** 2));
      let run = centre, passed = gap(centre);
      for (let tau = 0; tau <= centre * 2 + 20; tau += 0.1) { const g = gap(tau); if (g === 0) { run = tau; passed = 0; break; } if (g < passed) { passed = g; run = tau; } }
      Object.assign(t, { from, v: vt, run, runYd: run * v, passed, end: t.hitTyped ? run : Math.max(run * 1.5, 4000 / v) });
    });
    const end = Math.max(30, ...torps.filter(t => t.end != null).map(t => t.s + t.end)) + 15;
    return { rows, torps, targets, surface, ownSpeed, assumed, problems, start: -240, end, ownAt, targetAt };
  }
  const d3mean = xs => xs.reduce((a, b) => a + b, 0) / xs.length;
  // Everything at second s: the boat, each target (bearing, range, angle on the bow), each torpedo running or done
  function attackAt(A, s) {
    const o = A.ownAt(s);
    const targets = A.targets.map((T, gi) => {
      const p = A.targetAt(gi, s);
      if (!p) return null;
      const hitAt = d3min(A.torps.filter(t => t.target === gi && t.hitTyped && t.run != null).map(t => t.s + t.run));
      const q = hitAt != null && s > hitAt ? A.targetAt(gi, hitAt) : p;   // a hit ship stops where she was hit
      const dx = q[0] - o.p[0], dy = q[1] - o.p[1], bearing = norm(deg(Math.atan2(dx, dy)));
      return { p: q, bearing, range: Math.hypot(dx, dy), aob: ((bearing + 180 - T.course + 540) % 360) - 180, course: T.course, hit: hitAt != null && s >= hitAt };
    });
    const torps = A.torps.filter(t => t.from && s >= t.s).map(t => {
      const run = Math.min(s - t.s, t.end);
      return { t, p: [t.from[0] + t.v[0] * run, t.from[1] + t.v[1] * run], done: s - t.s >= t.end };
    });
    return { own: o, targets, torps };
  }
  const d3min = xs => xs.length ? Math.min(...xs) : null;
  // What a Torpedo Data Computer Mark 3's dials show at second s, from the sheet's solution (the dials: OP 1056 pp. 72-73,
  // 107, 111). The position keeper: own course and speed; the target aimed at (the next torpedo's, else the last fired),
  // its course and speed as the sheet gives them; its true and relative bearing, range and angle on the bow, from
  // attackAt; the distance from own ship to its track, range × sin(angle on the bow). The angle solver, for the point of
  // aim: the lead angle (sin L = k sin AOB, the law of sines in the fire-control triangle, k = target speed / torpedo
  // speed), the torpedo course (bearing + L), the gyro angle (from own heading), the track angle, and the run
  // (range × sin AOB / sin track). The gyro angle order adds the offset of each side's next tube. Parallax, the reach and
  // the turn are left out here as in attackSheet, so the forward and after solvers order the same angles; forward tubes
  // are 1-6, after 7-10, as in the fleet boats (Gato, Balao, Tench). No solution (k sin AOB beyond 1: the target too fast
  // for the torpedo on that bearing) leaves the angle solvers without one.
  function tdcAt(A, s) {
    const q = attackAt(A, s), own = q.own;
    const order = [...A.torps].sort((a, b) => a.s - b.s);
    const next = order.find(t => t.s >= s) || order[order.length - 1];
    const gi = next ? next.target : 0, T = A.targets[gi], at = q.targets[gi];
    const nextOn = aft => order.find(t => t.s >= s && (+t.tube >= 7) === aft) || [...order].reverse().find(t => (+t.tube >= 7) === aft);
    const base = { ownCourse: own.heading, ownSpeed: A.ownSpeed, target: gi, generating: !!(T && T.ok && at) };
    if (!base.generating) return { ...base, solved: false, fwd: null, aft: null };
    const relBearing = norm(at.bearing - own.heading), k = T.speed / next.knots, sinL = k * Math.sin(rad(at.aob));
    const out = { ...base, targetCourse: T.course, targetSpeed: T.speed, trueBearing: at.bearing, relBearing, range: at.range,
                  aob: at.aob, distanceToTrack: at.range * Math.abs(Math.sin(rad(at.aob))), torpedoSpeed: next.knots, depth: num(next.row.depth_set),
                  solved: Math.abs(sinL) <= 1, hit: at.hit };
    if (!out.solved) return { ...out, fwd: null, aft: null };
    const lead = deg(Math.asin(sinL)), torpedoCourse = norm(at.bearing + lead), gyro = norm(torpedoCourse - own.heading);
    const ta = ((torpedoCourse + 180 - T.course + 540) % 360) - 180;
    const run = Math.abs(Math.sin(rad(ta))) > 1e-6 ? at.range * Math.abs(Math.sin(rad(at.aob))) / Math.abs(Math.sin(rad(ta))) : at.range;
    const side = aft => { const t = nextOn(aft), offset = t && t.offset != null ? t.offset : 0;
      return { gyroOrder: norm(gyro + offset), offset, run, tube: t ? t.tube : null }; };
    return { ...out, lead, torpedoCourse, gyro, track: Math.abs(ta), side: ta >= 0 ? "S" : "P", fwd: side(false), aft: side(true) };
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
  return { zoneHours, toUTC, T, coord, offset, nm, posAt, observedPath, closing, fireControl, apparentSize, sky, localNoon, light, story, hhmm, day,
           gyroOf, coursesOf, offsetOf, firingTimes, torpedoKnots, attackSheet, attackAt, tdcAt };
})();
if (typeof module !== "undefined") module.exports = Engage;
