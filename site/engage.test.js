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
// 320 at 7.5 knots, Mk 18 at 29 knots -> torpedo course 202, a 62 starboard track
const f = E.fireControl({ ownCourse: 40, gyro: 162, targetCourse: 320, targetSpeed: 7.5, torpedoSpeed: 29 });
near(f.torpedoCourse, 202, 0, "torpedo course"); near(f.track, 62, 0, "track angle"); console.log(f.side === "S" ? "ok  " : (failed++, "FAIL"), "starboard track");
near(f.lead, 11.7, 0.2, "lead angle"); near(f.aob, 50.3, 0.3, "angle on the bow");

// Apparent size: a 420 ft ship at 595 yards, broadside, spans 2 atan(210 / 1785) = 13.42 degrees; bow-on, only her beam
const s = E.apparentSize({ length: 420, beam: 56, height: 60, range: 595 * 3, aob: 90 });
near(s.width, 13.42, 0.01, "apparent width broadside");
near(E.apparentSize({ length: 420, beam: 56, height: 60, range: 595 * 3, aob: 0 }).width, 1.80, 0.01, "apparent width bow-on");

process.exit(failed ? 1 : 0);
