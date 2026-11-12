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
//   Engage.tempo(events)              "clocked", "dated" or "monthly": a frame's tempo, derived from its entries, never stored
//   Engage.chronologyRows(events, tempo)        the chronology's spine: hours, days or months, each with its entries in order
//   Engage.chronologyColumns(events, participants)   one column per record, the followed subjects first, each with its nationality and colour
//   Engage.nation(code)                             a nationality code as the records give it -> its word ("de" -> "German"), never a bloc
//   Engage.sourceKindWord(kind, of)   a source's kind and nationality in a chip's words ("record · US", "French press", "secondary")
//   Engage.columnChip(column)         a chronology column's chip: the record's own words, then its source's kind and nationality
//   Engage.hitKind(kind)              whether an entry's kind is a hit (named in the hit red on the chronology)
//   Engage.apart(a, b)                {minutes, nm} between two placed records ({utc, lat, lon}): check_crossrefs.py's arithmetic
//   Engage.pairMoments(D)             the Sources view's moments of a clocked frame: each attack-record pair with every source that speaks to it
//   Engage.claimMoments(claims)       the questions the records leave open, each with its answers by source (the Sources view) and
//                                     merged by their words (the claims board)
//   Engage.badge(claim)               an answer's badge: its source's kind, and its weight where that differs
//   Engage.frontSide(runs, [lon, lat])   which side of a situation map's front a point lies: 1 on the enemy's (the
//                                     runs' left, as records/fronts/ stores them), -1 on the map's own, by the nearest leg
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
    // (`opts.sizes`, one [length, beam] in feet for each target, where a sheet's targets differ: a DD and an AO)
    const half = gi => { const [L, B] = (opts.sizes && opts.sizes[gi]) || [opts.length || 400, opts.beam || 55]; return [L / 6, B / 6]; };   // feet -> half, in yards
    torps.forEach(t => {
      const T = targets[t.target];
      if (t.course == null || !T.ok) return;
      const [halfL, halfB] = half(t.target);
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

  // A built engagement (engagement.json) as a story reads it (the front page's Haynsworth figure): its own entries in
  // the order events.yml gives them, with the record's date and time apart, and the claims; `ref` is the page's link.
  function story(D) {
    const timeline = D.events.filter(e => e.origin === "events").sort((a, b) => a.n - b.n).map(e => ({
      date: e.local.slice(0, 10), time: e.local.slice(11, 15), placed: e.placed || "", of: e.of || "", opposed: !!e.opposed,
      source_kind: e.source_kind || "", source_of: e.source_of || "", actor: e.actor, kind: e.kind,
      text: e.words || "", original: e.original || "", lang: e.lang || "", translation: e.translation || "",
      source: e.source || "", ref: e.cite.href, pos: e.pos || "", step: e.step || "" }));
    const claims = D.claims.map(c => ({ question: c.question, claim: c.answer, weight: c.weight, source: c.source || "", ref: c.cite.href, note: c.note || "" }));
    return { timeline, claims };
  }
  const MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const hhmm = ms => { const d = new Date(ms); return pad(d.getUTCHours()) + pad(d.getUTCMinutes()); };
  const day = ms => { const d = new Date(ms); return `${d.getUTCDate()} ${MON[d.getUTCMonth()]}`; };

  // ---------- the chronology (guides/OPERATIONS-VIEWER.md, 2.3 and 3). A frame's tempo is derived from its entries and
  // never stored: "clocked" when more than half of them carry a GMT time (`utc`: a typed time with its zone, or on the
  // engagement's clock), so that one clock is meaningful and the map plays; otherwise "monthly" when the entries span
  // more than about 90 days (a unit's year); otherwise "dated", the entries carrying days (Venafro, Algiers). More than
  // half, not any: Remagen's III Corps report times ten entries of twenty-five over ten days, the rest "the period
  // 110600 to 120600", and a clock played over it would pass most of the record in silence.
  const DAY_MS = 86400e3;
  const dayOf = e => String(e.local || e.key || e.utc || "").slice(0, 10);            // the day as the record writes it
  const typedTime = e => e.local && e.local.length > 10 ? e.local.slice(11, 15) : null;   // "1610"; null when none is written
  function tempo(events) {
    const es = (events || []).filter(e => dayOf(e));
    if (!es.length) return "dated";
    if (es.filter(e => e.utc).length > es.length / 2) return "clocked";
    const ms = es.map(e => T(dayOf(e))).filter(x => x != null && !Number.isNaN(x));
    return ms.length && Math.max(...ms) - Math.min(...ms) > 90 * DAY_MS ? "monthly" : "dated";
  }
  // The spine's rows: one per hour (clocked), day (dated) or month (monthly) that has entries, in time order, each
  // with its entries: those with a time first, by the time (GMT when clocked, else as typed), then those the account
  // places, in its order (`n`). A row is {key, ms, label, day, entries}; `day` names the day beside an hour's label.
  // When clocked, an entry with no time of its own gets a row of the day's, at its start; an entry dated to a month
  // alone gets the month's row.
  const monthLabel = k => `${MON[+k.slice(5, 7) - 1]} ${k.slice(0, 4)}`;
  function chronologyRows(events, tempo) {
    const rows = new Map();
    (events || []).forEach((e, i) => {
      const d = dayOf(e);
      if (!d) return;
      let key, ms, label, dayName = null;
      if (tempo === "clocked" && e.utc) {
        const dt = new Date(T(e.utc));
        ms = Date.UTC(dt.getUTCFullYear(), dt.getUTCMonth(), dt.getUTCDate(), dt.getUTCHours());
        key = new Date(ms).toISOString().slice(0, 13); label = hhmm(ms); dayName = day(ms);
      } else if (tempo === "monthly" || d.length < 10) {
        key = d.slice(0, 7); ms = Date.UTC(+key.slice(0, 4), +key.slice(5, 7) - 1, 1); label = monthLabel(key);
      } else {
        key = d; ms = Date.UTC(+d.slice(0, 4), +d.slice(5, 7) - 1, +d.slice(8, 10)); label = day(ms);
      }
      if (Number.isNaN(ms)) return;
      if (!rows.has(key)) rows.set(key, { key, ms, label, day: dayName, entries: [] });
      rows.get(key).entries.push({ e, i });
    });
    const out = [...rows.values()].sort((a, b) => a.ms - b.ms);
    const years = new Set(out.map(r => r.key.slice(0, 4)));
    const at = x => {
      if (tempo === "clocked" && x.e.utc) return T(x.e.utc);
      const hm = typedTime(x.e), t = hm ? T(`${dayOf(x.e)}T${hm.slice(0, 2)}:${hm.slice(2)}`) : null;
      return t != null && !Number.isNaN(t) ? t : null;
    };
    out.forEach(r => {
      if (years.size > 1 && r.key.length === 10) r.label += " " + r.key.slice(0, 4);
      if (years.size > 1 && r.day) r.day += " " + r.key.slice(0, 4);
      r.entries = r.entries.sort((a, b) => {
        const ta = at(a), tb = at(b);
        if (ta != null && tb != null) return ta - tb || a.i - b.i;
        if (ta != null || tb != null) return ta != null ? -1 : 1;
        return (a.e.n ?? a.i) - (b.e.n ?? b.i) || a.i - b.i;
      }).map(x => x.e);
    });
    return out;
  }
  // One column per record. An entry joins a participant's column when its actor is that participant (its id or name,
  // or the name's head: "Battery A (1st Bn)" is Battery A, 67th CA (AA)); else the column of its source's record, the
  // text before the first comma or colon ("XIV Panzer Corps, tactical reports: 5. Geb.Div., ..." is XIV Panzer
  // Corps'; the dates and pages after it vary from entry to entry); else its actor's. The followed subjects (a
  // participant the build marks `followed`, or with a track, a unit or a colour) come first, in the participants'
  // order, each in its colour (the build's, else the next free of the three checked ones; a fourth subject is ink),
  // then the other columns by nationality, the subjects' first and then in order of appearance, in ink (the press, told
  // by its source's kind, in the lighter ink, unless it is the other side's: its bulletins in print are still its claims). A column's nationality (`of`), whether it is the other side (`opposed`)
  // and its source's kind are its entries' (the most common). A column is {key, name, of, opposed, source_kind, colour,
  // subject, participant, record, entries}.
  const head = s => String(s || "").split(/,| \(/)[0].trim();
  const stem = s => String(s || "").split(/[,:;]/)[0].trim();
  function chronologyColumns(events, participants) {
    const parts = participants || [], lc = s => head(s).toLowerCase();
    const match = e => parts.find(p => p.id === e.actor || p.name === e.actor) || (head(e.actor) ? parts.find(p => lc(p.name) === lc(e.actor)) : null);
    const cols = new Map();
    (events || []).forEach((e, i) => {
      const p = match(e), key = p ? "p:" + p.id : e.source ? "s:" + stem(e.source) : "a:" + (head(e.actor) || "?");
      if (!cols.has(key)) cols.set(key, { key, name: p ? p.name : key.slice(2), participant: p || null, subject: !!(p && (p.followed || p.track || p.unit || p.colour)), entries: [], first: i });
      cols.get(key).entries.push(e);
    });
    const all = [...cols.values()];
    const most = (es, f) => { const n = new Map(); es.forEach(e => n.set(f(e), (n.get(f(e)) || 0) + 1)); return [...n].sort((a, b) => b[1] - a[1])[0][0]; };
    all.forEach(c => {
      c.of = most(c.entries, e => e.of || ""); c.opposed = most(c.entries, e => !!e.opposed); c.source_kind = most(c.entries, e => e.source_kind || "");
      c.source_of = most(c.entries, e => e.source_of || "");
      c.record = recordWords(c.entries.map(e => e.source), c.name);
    });
    const subjects = parts.map(p => all.find(c => c.participant === p && c.subject)).filter(Boolean);
    const used = new Set(parts.map(p => p.colour).filter(Boolean));
    let slot = 1;
    subjects.forEach(c => {
      let n = c.participant.colour;
      if (!n) { while (used.has(slot)) slot++; n = slot <= 3 ? slot++ : null; }
      c.colour = n ? `var(--c${n})` : "var(--ink)";
    });
    const others = all.filter(c => !subjects.includes(c)).sort((a, b) => a.first - b.first);
    const order = [...new Set([...subjects, ...others].map(c => c.of))];
    others.sort((a, b) => order.indexOf(a.of) - order.indexOf(b.of) || a.first - b.first);
    others.forEach(c => { c.colour = !c.opposed && (c.source_kind === "press" || c.source_kind === "intelligence") ? "var(--ink-3)" : "var(--ink)"; });   // the other side's claims, even in print, in ink; our own press and intelligence, not records, in the lighter ink
    return [...subjects, ...others].map(c => ({ key: c.key, name: c.name, of: c.of, opposed: c.opposed, source_kind: c.source_kind, source_of: c.source_of, colour: c.colour,
                                                subject: c.subject, participant: c.participant ? c.participant.id : null, record: c.record, entries: c.entries }));
  }
  // A nationality as the records give it, in a word: the other side is named as the records name it (German, Italian,
  // Japanese), never as a bloc (guides/OPERATIONS-VIEWER.md 2.4). An unknown code is shown as typed, in capitals.
  const NATIONS = { us: "US", jp: "Japanese", de: "German", it: "Italian", uk: "British", fr: "French", au: "Australian", nz: "New Zealand",
                    ca: "Canadian", nl: "Dutch", pl: "Polish", in: "Indian", za: "South African" };
  const nation = code => NATIONS[code] || (code ? String(code).toUpperCase() : "");
  // A source's kind and whose it is, as a chip says it (2.4): "record · US", "intelligence · US", "assessment · US", "French
  // press"; a later history, a reference, a recollection or a derivation by its kind alone, since its author's nationality is
  // not a voice in the records. Never "Axis" or "Allied".
  const KIND_ALONE = new Set(["secondary", "reference", "recollection", "derived"]);
  function sourceKindWord(kind, of) {
    const k = String(kind || ""), n = nation(of);
    if (!k) return n;
    if (k === "press") return n ? `${n} press` : k;
    if (KIND_ALONE.has(k)) return k;
    return n ? `${k} · ${n}` : k;
  }
  // The chip under a chronology column's name: the record's own words where its sources give them ("morning report"), then
  // its source's kind and nationality where its entries carry a citation's kind; without one, the nationality alone.
  const columnChip = c => [c.record, c.source_kind ? sourceKindWord(c.source_kind, c.source_of || c.of) : nation(c.of)].filter(Boolean).join(" · ");
  // The record in the sources' own words: of each source text's pieces (anything in brackets dropped, then split at
  // commas, colons and semicolons), the first that isn't the column's name or its head, a date, a page, a folio or a
  // volume ("morning report", "tactical reports", "operations record book"); the most common across the column, or ""
  // when the sources carry only a name, a date and a page (a newspaper's issue, a war diary's page).
  const NOISE = [/^(\d{1,2} )?(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*( \d{4})?\b/i, /^\d{1,2}\b.*\b(19|20)\d\d\b/, /^\d{4}\b/,
                 /^(p|pp|f|ff|vol|no|nos|image|images|form|frame|frames|air|rg|t)\b\.?\s*\d/i, /^\d+(\.|$)/];
  function recordWords(sources, name) {
    const unbracket = s => String(s || "").replace(/\s*\([^)]*\)/g, "");
    const names = new Set(unbracket(name).split(/,\s*/).map(x => x.trim().toLowerCase()));
    const h = head(name).toLowerCase(), counts = new Map();
    sources.forEach(s => {
      const pieces = unbracket(s).split(/[,:;]\s*/).map(x => x.trim()).filter(Boolean)
        .map(x => h && x.toLowerCase().startsWith(h) ? x.slice(h.length).replace(/^[\s,:;-]+/, "") : x)
        .filter(x => x && !names.has(x.toLowerCase()) && !NOISE.some(re => re.test(x)));
      if (pieces.length) counts.set(pieces[0], (counts.get(pieces[0]) || 0) + 1);
    });
    const best = [...counts].sort((a, b) => b[1] - a[1])[0];
    return best ? best[0] : "";
  }
  // The kinds the chronology names in the hit red. Red is reserved for hits (ENGAGEMENTS.md, "Encodings"); a casualty,
  // a shelling, a loss or a ship torpedoed is a hit on the unit or the ship, so these take it, and nothing else does.
  const HIT_KINDS = new Set(["casualty", "shelled", "hit", "damage", "loss", "sank", "sunk", "torpedoed", "kill"]);
  const hitKind = kind => HIT_KINDS.has(String(kind || "").toLowerCase());

  // ---------- the Sources view (guides/OPERATIONS-VIEWER.md 3 and 7.1): for a moment, every source that speaks to it, side by
  // side, with the arithmetic between them done here and never stored.
  // The minutes and nautical miles between two placed records, as tools/check_crossrefs.py prints them: `b` after `a` is
  // positive; a value either lacks (no time, no position) is null. Each is {utc, lat, lon}.
  const placed = x => !!x && x.lat != null && x.lon != null;
  function apart(a, b) {
    const ta = a && a.utc ? T(a.utc) : null, tb = b && b.utc ? T(b.utc) : null;
    return { minutes: ta != null && tb != null ? Math.round((tb - ta) / 60000) : null,
             nm: placed(a) && placed(b) ? nm([a.lon, a.lat], [b.lon, b.lat]) : null };
  }
  // A clocked frame's moments: each pairing of an attack with a Japanese record (`pairs`, from the boat's claims.yml). Its
  // sources, in order: the boat's attack data sheet (its typed time, position and words; her narrative's attack entry where
  // no sheet is transcribed), the record as written, the FRUPAC notes tied to the attack (the pair's `intelligence`, from the
  // boat's frupac.yml: US radio intelligence, zone I assumed, position read off the map), then every entry of another kind
  // of source (an assessment, a later history, the press) within two hours that names the same ship or the same attack. A
  // source is {role, name, sub, kind, of, zone, typed, utc, lat, lon, raw, basis, position, assumed, words: [{typed} |
  // {original, lang, translation} | {ours}], cite}; `apart` holds the arithmetic between the first source and each other;
  // `ours` is the pairing's relation and note, the one row in our voice besides the GMT and placed rows.
  const NEAR_MS = 2 * 3600e3;
  const zoneOf = local => { const m = /\s([A-Z]{1,2})$/.exec(String(local || "")); return m ? m[1] : ""; };
  const RELATION = { hit: "a hit: the attack caused this record", miss: "a miss: the same moment, no damage",
                     probable: "probable: time and place point to this attack, but another boat is credited or was attacking too",
                     possible: "possible: the times fit, but more than one attack could explain the record",
                     no_loss: "no loss: a claimed sinking with no matching entry in the loss list" };
  function pairMoments(D) {
    const byId = Object.fromEntries((D.participants || []).map(p => [p.id, p]));
    const nameOf = id => byId[id] ? byId[id].name : id;
    return (D.pairs || []).map(x => {
      const ref = x.attack.replace(/ fired$/, ""), r = x.record, fixes = D.fixes || [];
      const fix = fixes.find(f => f.who === x.boat && f.ref === x.attack) || fixes.find(f => f.who === x.boat && f.ref === ref) || {};
      const sheet = D.sheets && D.sheets[x.boat] && D.sheets[x.boat][ref];
      const narrative = (D.events || []).find(e => e.actor === x.boat && e.kind === "attack" && e.title === x.attack.replace(/ fired$/, " (narrative)"));
      const t0 = sheet && sheet.torpedoes[0] || {}, w = sheet && sheet.words[0] || {};
      const typedSheet = t0.time ? [t0.date, t0.time, t0.zone || zoneOf(fix.local)].filter(Boolean).join(" ") : fix.local || x.utc;
      const attack = {
        role: "attack", name: `${nameOf(x.boat)}, ${sheet ? "attack data sheet" : "narrative"}, ${ref}`, sub: byId[x.boat] && byId[x.boat].track ? "war patrol report" : "",
        kind: (fix.cite && fix.cite.kind) || "record", of: (fix.cite && fix.cite.of) || (byId[x.boat] && byId[x.boat].of) || "", zone: t0.zone || zoneOf(fix.local),
        typed: typedSheet, utc: fix.utc || x.utc, lat: fix.lat, lon: fix.lon, raw: fix.raw || "", basis: fix.fix || (fix.assumed ? "assumed" : fix.lat != null ? "reported" : ""),
        words: sheet ? [w.description && { typed: w.description }, w.sunk && { typed: `Sunk: ${w.sunk}` }, w.damaged && { typed: `Damaged: ${w.damaged}` }].filter(Boolean)
                     : [narrative && narrative.words && { typed: narrative.words }, fix.note && !narrative && { typed: fix.note }].filter(Boolean),
        cite: (sheet && sheet.cite) || fix.cite || (narrative && narrative.cite) || null };
      const record = {
        role: "record", name: `${r.ship || r.convoy || "Japanese record"}, ${r.id}`, sub: [r.cite && r.cite.source_title, String(r.event || "").replace(/_/g, " ")].filter(Boolean).join(" · "),
        kind: (r.cite && r.cite.kind) || "record", of: (r.cite && r.cite.of) || "jp", zone: r.zone || "",
        typed: [r.date, r.time, r.zone].filter(Boolean).join(" "), utc: r.utc, lat: r.lat, lon: r.lon, raw: [r.lat_raw, r.lon_raw].filter(Boolean).join(" "),
        basis: r.lat != null ? "reported" : "", words: [r.original ? { original: r.original, lang: r.lang || "ja", translation: r.translation } : r.translation && { typed: r.translation }, r.note && { ours: r.note }].filter(Boolean),
        cite: r.cite || null };
      // US radio intelligence: the FRUPAC notes the boat's frupac.yml ties to this attack (`intelligence` on the pair), each
      // as written, on its own time (none when the note gives none), at the position read off the map, with the map's zoom
      // view as its page; the relation and the note are ours
      const intelligence = (x.intelligence || []).map(f => ({
        role: "intelligence", name: `FRUPAC ${f.id}`,
        sub: [f.map_date && `war map, ${f.map_date}`, String(f.event || "").replace(/_/g, " "), f.dtg && `DTG ${f.dtg}`].filter(Boolean).join(" · "),
        kind: (f.cite && f.cite.kind) || "intelligence", of: (f.cite && f.cite.of) || "us", zone: "",
        typed: f.time ? `${f.date} ${f.time}` : f.date || "", utc: f.utc, lat: f.lat, lon: f.lon, raw: "",
        position: f.lat != null ? "a blue dot on the overlay, read against the printed grid" : "", basis: f.lat != null ? "estimated, about ±0.2°" : "",
        assumed: f.utc ? "FRUPAC's zone assumed I" : "",
        words: [f.text && { typed: f.text }, (f.relation || f.note) && { ours: [f.relation, f.note].filter(Boolean).join(": ") }].filter(Boolean),
        cite: f.zoom ? { href: f.zoom, ref: f.zoom, label: "map" } : f.cite || null }));
      const ships = String(r.ship || "").split(/;\s*/).filter(Boolean), boatName = nameOf(x.boat), at = T(x.utc);
      const near = (D.events || []).filter(e => e.source_kind && e.source_kind !== "record" && !(e.record === r.id && e.origin === "japanese") && e.actor !== x.boat
          && e.origin !== "frupac" && e.utc && Math.abs(T(e.utc) - at) <= NEAR_MS).filter(e => {
        const text = [e.title, e.actor, e.ship, e.words, e.translation, e.note].map(v => String(v || "")).join(" ");
        return ships.some(n => text.includes(n)) || (text.includes(ref) && text.includes(boatName));
      }).map(e => ({
        role: "near", name: e.title && e.title !== e.actor ? `${nameOf(e.actor)}, ${e.title}` : nameOf(e.actor), sub: head(e.source) || (e.cite && e.cite.source_title) || "",
        kind: e.source_kind, of: e.source_of || "", zone: zoneOf(e.local), typed: e.local || "", utc: e.utc, lat: e.lat, lon: e.lon, raw: "",
        basis: e.lat != null ? (e.basis || "placed") : "",
        words: [e.original ? { original: e.original, lang: e.lang || "ja", translation: e.translation || e.words } : e.words && { typed: e.words }, e.note && { ours: e.note }].filter(Boolean),
        cite: e.cite || null }));
      const sources = [attack, record, ...intelligence, ...near];
      return { key: `${x.boat}:${x.attack}:${r.id}`, boat: x.boat, attack: ref, record: r.id, utc: x.utc, sources,
               apart: sources.slice(1).map((s, i) => ({ a: 0, b: i + 1, ...apart(attack, s) })),
               ours: { relation: x.relation, words: RELATION[x.relation] || x.relation, note: x.note || "" } };
    });
  }
  // The questions the records leave open (claims.yml), each with its answers twice over: by source, for the Sources view
  // (one column per record named in `source`, its answers as typed with their pages), and merged by their words, for the
  // claims board (repetition isn't corroboration: two answers in the same words are one line with both citations).
  function claimMoments(claims) {
    const qs = new Map();
    (claims || []).forEach(c => {
      if (!qs.has(c.question)) qs.set(c.question, { question: c.question, columns: [], answers: [] });
      const q = qs.get(c.question), src = head(c.source) || (c.cite && c.cite.source_title) || "?";
      let col = q.columns.find(k => k.name === src);
      if (!col) q.columns.push(col = { name: src, kind: c.source_kind || "", of: c.source_of || "", answers: [] });
      col.answers.push(c);
      const same = q.answers.find(a => a.answer === c.answer);
      if (same) { same.cites.push(c.cite); same.sources.push(c.source || ""); if (c.note && !same.notes.includes(c.note)) same.notes.push(c.note); }
      else q.answers.push({ answer: c.answer, notes: c.note ? [c.note] : [], sources: [c.source || ""], cites: [c.cite], ...badge(c) });
    });
    return [...qs.values()];
  }
  // An answer's badge (7.1): its source's kind, from the citation, in place of its own weight where the two agree; the weight
  // kept beside it where they differ (a record used as a recollection, a later history quoting a record). An inference is
  // ours and no source's, so it keeps its own mark.
  function badge(c) {
    const kind = c.source_kind || c.weight || "", w = c.weight || "";
    const mark = w === "inference" ? "inference" : kind;
    return { mark, words: w && w !== mark ? `${mark} · as ${w}` : mark };
  }

  // ---------- a point against a traced front (records/fronts/), which may be many short stretches. The runs are stored
  // with the enemy's side on their left. Every leg within half again the nearest leg's distance votes its side (the sign
  // of the cross product: positive, a turn to the left, is the enemy's), weighted by how squarely the point lies to its
  // side (the sine of the angle) and by its nearness, so a short stretch the point lies along, beyond its end, counts for
  // little. On a plane scaled by the cosine of the latitude (a few hundred km at most). 1 the enemy's side, -1 the map's
  // own, 0 when nothing tells.
  function frontSide(runs, p) {
    const k = Math.cos(p[1] * Math.PI / 180), X = q => [q[0] * k, q[1]], [px, py] = X(p);
    const legs = [];
    runs.forEach(run => { for (let i = 1; i < run.length; i++) {
      const [ax, ay] = X(run[i - 1]), [bx, by] = X(run[i]), dx = bx - ax, dy = by - ay, L = Math.hypot(dx, dy);
      if (!L) continue;
      const u = Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / (L * L)));
      legs.push({ d: Math.hypot(px - ax - u * dx, py - ay - u * dy), sin: (dx * (py - ay) - dy * (px - ax)) / (L * (Math.hypot(px - ax, py - ay) || 1e-9)) });
    } });
    if (!legs.length) return 0;
    const near = Math.min(...legs.map(l => l.d));
    return Math.sign(legs.filter(l => l.d <= near * 1.5 + 1e-9).reduce((v, l) => v + l.sin / (l.d + 1e-6), 0));
  }

  return { frontSide, zoneHours, toUTC, T, coord, offset, nm, posAt, observedPath, closing, fireControl, apparentSize, sky, localNoon, light, story, hhmm, day,
           gyroOf, coursesOf, offsetOf, firingTimes, torpedoKnots, attackSheet, attackAt, tdcAt,
           tempo, chronologyRows, chronologyColumns, recordWords, hitKind, head, nation, sourceKindWord, columnChip,
           apart, pairMoments, claimMoments, badge };
})();
if (typeof module !== "undefined") module.exports = Engage;
