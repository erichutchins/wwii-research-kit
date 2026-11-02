// Tests for engage.js: node site/engage.test.js (exits 1 on a failure). The cases are from the records.
const E = require("./engage.js");
let failed = 0;
const near = (a, b, tol, what) => {
  const ok = Math.abs(a - b) <= tol;
  if (!ok) failed++;
  console.log(`${ok ? "ok  " : "FAIL"} ${what}: ${typeof a === "number" ? a.toFixed(3) : a} (want ${b} ± ${tol})`);
};
const iso = ms => new Date(ms).toISOString().slice(0, 16) + "Z";

// Zones: TINOSA's 0603 H on 3 May 1944 is 2203 GMT on the 2nd; BANG's K is -10; Tokyo (I) is +9; Haynsworth's
// half-hour zones; Z is GMT
near(E.zoneHours("H"), 8, 0, "zone H"); near(E.zoneHours("K"), 10, 0, "zone K"); near(E.zoneHours("I"), 9, 0, "zone I (no J)");
near(E.zoneHours("M"), 12, 0, "zone M"); near(E.zoneHours("N"), -1, 0, "zone N"); near(E.zoneHours("Y"), -12, 0, "zone Y");
near(E.zoneHours("KL"), 10.5, 0, "zone KL"); near(E.zoneHours("Z"), 0, 0, "zone Z");
const t = E.toUTC("1944-05-03", "0603", "H");
console.log(iso(t) === "1944-05-02T22:03Z" ? "ok  " : (failed++, "FAIL"), "0603 H on 3 May =", iso(t));
near(E.T("1944-05-02T22:03Z"), t, 0, "T() reads the build's ISO time");

// Positions as typed
near(E.coord("19-21N"), 19.35, 1e-9, "19-21N"); near(E.coord("115-50E"), 115.8333, 1e-4, "115-50E");
near(E.coord("26-42.5N"), 26.7083, 1e-4, "26-42.5N"); near(E.coord("157-58W"), -157.9667, 1e-4, "157-58W");
console.log(E.coord("1?-21N") === null ? "ok  " : (failed++, "FAIL"), "an unreadable digit gives null");

// A bearing and distance: picket station #1, 12 miles bearing 060 from the group (Haynsworth's war diary)
const [lon, lat] = E.offset(129.1667, 26.8333, 60, 12);
near(E.nm([129.1667, 26.8333], [lon, lat]), 12, 0.05, "12 nm offset comes back as 12 nm");

// A track is straight between fixes, and never runs beyond its first or last fix
const track = [{ utc: "1944-05-03T00:00Z", lon: 120, lat: 20 }, { utc: "1944-05-03T02:00Z", lon: 121, lat: 21 }];
near(E.posAt(track, E.T("1944-05-03T01:00Z"))[0], 120.5, 1e-9, "halfway in time is halfway along");
console.log(E.posAt(track, E.T("1944-05-03T03:00Z")) === null ? "ok  " : (failed++, "FAIL"), "no position after the last fix");

// Closing in: only while both the boat's track and the convoy's observed path are known
const path = E.observedPath([{ utc: "1944-05-03T01:00Z", lon: 121, lat: 20 }, { utc: "1944-05-03T03:00Z", lon: 121, lat: 21 }]);
const c = E.closing(track, path, 10);
near(E.T(new Date(c[0].ms).toISOString()), E.T("1944-05-03T01:00Z"), 0, "closing starts at the first sighting");
near(c[c.length - 1].ms, E.T("1944-05-03T02:00Z"), 0, "and ends at the boat's last fix");

// Fire control, SEAHORSE's Attack 3, 4 July 1944 (her attack data sheet): own course 040, gyro 162, target course
// 320 at 7.5 knots, Mk 18 at 29 knots (secondary) -> torpedo course 202, a 62 starboard track
const f = E.fireControl({ ownCourse: 40, gyro: 162, targetCourse: 320, targetSpeed: 7.5, torpedoSpeed: 29 });
near(f.torpedoCourse, 202, 0, "torpedo course"); near(f.track, 62, 0, "track angle"); console.log(f.side === "S" ? "ok  " : (failed++, "FAIL"), "starboard track");
near(f.lead, 11.7, 0.2, "lead angle"); near(f.aob, 50.3, 0.3, "angle on the bow");

// Apparent size: a 420 ft ship at 595 yards, broadside, spans 2 atan(210 / 1785) = 13.42 degrees; bow-on, only her beam
const s = E.apparentSize({ length: 420, beam: 56, height: 60, range: 595 * 3, aob: 90 });
near(s.width, 13.42, 0.01, "apparent width broadside");
near(E.apparentSize({ length: 420, beam: 56, height: 60, range: 595 * 3, aob: 0 }).width, 1.80, 0.01, "apparent width bow-on");

// The typed forms on the attack sheets (records/README.md, attacks.csv)
near(E.gyroOf("162"), 162, 0, "gyro 162"); near(E.gyroOf("5L"), 355, 0, "gyro 5L"); near(E.gyroOf("10R"), 10, 0, "gyro 10R");
near(E.offsetOf("1.5R"), 1.5, 0, "offset 1.5R"); near(E.offsetOf("1L"), -1, 0, "offset 1L");
console.log(E.offsetOf("225'Aft") === null ? "ok  " : (failed++, "FAIL"), "an offset along the target is not in degrees");
console.log(E.coursesOf("050-069").join() === "50,69" ? "ok  " : (failed++, "FAIL"), "own course swinging 050-069");
// Firing times: SEAHORSE types the gap since the torpedo before (0, 9, 7, 47 ...); BANG patrol 1 the time since the
// first (0, 8, 16, 24, 45, 53); PARCHE's Attack 2 restarts at 0 for its second target, at a time the sheet doesn't give
const ft = rows => E.firingTimes(rows).map(x => x.s + (x.assumed ? "?" : "")).join();
console.log(ft([0, 9, 7, 47].map(v => ({ time: "2355", interval: String(v) }))) === "0,9,16,63" ? "ok  " : (failed++, "FAIL"), "intervals add up");
console.log(ft([0, 8, 16, 24].map(v => ({ time: "2256", since_first: String(v) }))) === "0,8,16,24" ? "ok  " : (failed++, "FAIL"), "since_first is read as it is");
console.log(ft([0, 8, 8, 8, 0, 8].map(v => ({ time: "0106", interval: String(v) }))) === "0,8,16,24,34?,42" ? "ok  " : (failed++, "FAIL"), "a second salvo with no time: assumed 10 s on");
console.log(ft([{ time: "1508", since_first: "0" }, { time: "1508", since_first: "8" }, { time: "1509", since_first: "0" }]) === "0,8,60" ? "ok  " : (failed++, "FAIL"), "a second salvo at a later typed minute starts then");

// SEAHORSE's Attack 3 on her sheet (rg367-74845019/p29-30): the target placed from the gyro and track; her narrative
// (p09) has the first hit 36 seconds after firing, "a torpedo run of 560 yards"
const sea3 = [{ time: "2354", tube: "7", own_course: "040", own_speed: "3", own_depth: "64", target_course: "320", target_speed: "7.5", target_range: "595", track: "62S", gyro: "162", power: "---", hit: "Hit", torpedo: "18", interval: "0", spread: "divergent" },
              { time: "2354", tube: "8", own_course: "040", own_speed: "3", own_depth: "64", target_course: "320", target_speed: "7.5", target_range: "595", track: "63S", gyro: "163", power: "---", hit: "Hit", torpedo: "18", interval: "10", spread: "divergent" }];
const A = E.attackSheet(sea3), T0 = A.targets[0];
near(T0.track, 62.5, 0.1, "the point of aim's track, mid-spread"); near(T0.bearing, 190.8, 1, "target's bearing at firing");
// (to the hull of a 400 ft ship; the computation leaves out the torpedo's straight run and turn out of the tube, so short)
near(A.torps[0].run, 36, 4, "tube 7's run, seconds (narrative: 36)"); near(A.torps[0].runYd, 560, 60, "tube 7's run, yards (narrative: 560)");
near(E.attackAt(A, 0).targets[0].range, 595, 0.5, "the range at firing is the sheet's");
console.log(A.surface === false ? "ok  " : (failed++, "FAIL"), "64 ft is a periscope attack");
// PARCHE's Attack 2: two targets on one sheet, each torpedo with the one it was aimed at
const two = E.attackSheet([{ time: "0106", own_course: "100", target_course: "010", target_speed: "8", target_range: "1500", gyro: "350", interval: "0" },
                           { time: "0106", own_course: "100", target_course: "010", target_speed: "8", target_range: "2200", gyro: "355", interval: "0" }]);
near(two.targets.length, 2, 0, "two targets, from two ranges");

// The periscope view's light: "Broad daylight" is the same local date at noon; "Night vision" lifts the darkness
// (illustrative) without moving the sun or the moon
const tinosa = E.toUTC("1944-05-03", "0603", "H");
console.log(iso(E.localNoon(tinosa, "H")) === "1944-05-03T04:00Z" ? "ok  " : (failed++, "FAIL"), "local noon on 3 May, zone H =", iso(E.localNoon(tinosa, "H")));
const dark = { sun: { bearing: 0, altitude: -30 }, moon: { bearing: 90, altitude: -10, fraction: 0, phase: 0 } };
near(E.light(dark).day, 0, 0, "no daylight with the sun 30° down"); near(E.light(dark).L, 0.04, 0.001, "a moonless night's light");
near(E.light(dark, true).L, 0.5, 0.001, "night vision lifts the light"); near(E.light(dark, true).V, 8000, 0, "night vision: a ship shows farther");
near(E.light({ sun: { bearing: 180, altitude: 60 }, moon: dark.moon }, true).L, 1, 0, "night vision leaves daylight as it was");

process.exit(failed ? 1 : 0);
