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
// A port track: own course 000, gyro 010, target course 240 (track 50P). The target lies off the bow to port of the
// torpedo's course, and a torpedo fired on the solution reaches her hull (fireControl's aob is already signed)
const port = E.attackSheet([{ time: "0100", own_course: "000", target_course: "240", target_speed: "8", target_range: "1500", gyro: "010", interval: "0", hit: "Hit" }]);
console.log(port.targets[0].side === "P" ? "ok  " : (failed++, "FAIL"), "a 50P track is a port track");
near(port.targets[0].bearing, 16.8, 0.2, "a port-track target's bearing at firing (46 kn: lead 6.8, aob 43.2P)");
near(port.torps[0].passed, 0, 0, "the port-track torpedo reaches the hull");

// The Torpedo Data Computer's dials (tdcAt). BANG's first attack, patrol 1 (rg367-74802746/p16): four bow tubes on the
// destroyer at 1800 yards with offsets 1½R ½R ½L 1½L, then two at the tanker. At the moment of firing the angle
// solver's point of aim is attackSheet's (the four aims' middle: gyro 013.4), and its angles must agree with fireControl's
const bang1 = [["1", "013", "1.5R", "0", "23", "1800", "123S"], ["2", "013", "0.5R", "8", "23", "1800", "123S"], ["3", "013.5", "0.5L", "16", "23", "1800", "123S"],
               ["4", "014", "1.5L", "24", "14-3A", "1800", "123S"], ["5", "345", "1R", "45", "14-3A", "2800", "95S"], ["6", "344", "1L", "53", "14-3A", "2800", "95S"]]
  .map(([tube, gyro, offset, since, torpedo, range, trk]) => ({ time: "2256", tube, own_course: "090", own_speed: "2.5", own_depth: "60", target_course: "160", target_speed: "10.5",
        target_range: range, track: trk, gyro, depth_set: "6", power: torpedo === "23" ? "-" : "High", hit: "Hit", torpedo, since_first: since, offset }));
const AB = E.attackSheet(bang1, { length: 350, beam: 34 }), d0 = E.tdcAt(AB, 0);
const fc0 = E.fireControl({ ownCourse: 90, gyro: d0.gyro, targetCourse: 160, targetSpeed: 10.5, torpedoSpeed: 46 });
near(d0.gyro, 13.4, 0.05, "TDC: the point of aim's gyro at firing (the four aims' middle)");
near(d0.fwd.gyroOrder, 14.9, 0.05, "TDC: the gyro order adds tube 1's offset, 1½R");
near(d0.aob, fc0.aob, 0.05, "TDC: its angle on the bow agrees with fireControl's for that gyro");
near(d0.track, fc0.track, 0.05, "TDC: its track angle agrees with fireControl's"); near(d0.range, 1800, 0.5, "TDC: the range at firing is the sheet's");
near(d0.relBearing, (d0.trueBearing - 90 + 360) % 360, 1e-9, "TDC: relative bearing is true bearing less own course");
// the fire-control triangle, worked separately: the run over the range is sin AOB over sin track; distance to track is R sin AOB
near(d0.fwd.run, 1800 * Math.sin(d0.aob * Math.PI / 180) / Math.sin(d0.track * Math.PI / 180), 0.5, "TDC: torpedo run from the triangle");
near(d0.distanceToTrack, 1800 * Math.sin(d0.aob * Math.PI / 180), 0.5, "TDC: distance to track, range × sin AOB");
console.log(d0.side === "S" && d0.fwd.tube === "1" && d0.aft.tube === null ? "ok  " : (failed++, "FAIL"), "TDC: starboard track; tube 1 next forward; no after tube on this sheet");
const d9 = E.tdcAt(AB, 9), d30 = E.tdcAt(AB, 30);
console.log(d9.fwd.tube === "3" && d9.fwd.offset === -0.5 ? "ok  " : (failed++, "FAIL"), "TDC: at 9 s the next forward tube is 3, offset ½L");
console.log(d30.target === 1 && Math.round(d30.range) > 2700 ? "ok  " : (failed++, "FAIL"), "TDC: at 30 s it is on the second target, the tanker");
const dS = E.tdcAt(A, 0);   // SEAHORSE's stern tubes: the after solver's
console.log(dS.aft.tube === "7" && dS.fwd.tube === null ? "ok  " : (failed++, "FAIL"), "TDC: SEAHORSE's tube 7 is an after tube");
near(dS.gyro, 162.5, 0.1, "TDC: SEAHORSE's point of aim, gyro 162½ (mid-spread)");

// The periscope view's light: "Broad daylight" is the same local date at noon; "Night vision" lifts the darkness
// (illustrative) without moving the sun or the moon
const tinosa = E.toUTC("1944-05-03", "0603", "H");
console.log(iso(E.localNoon(tinosa, "H")) === "1944-05-03T04:00Z" ? "ok  " : (failed++, "FAIL"), "local noon on 3 May, zone H =", iso(E.localNoon(tinosa, "H")));
const dark = { sun: { bearing: 0, altitude: -30 }, moon: { bearing: 90, altitude: -10, fraction: 0, phase: 0 } };
near(E.light(dark).day, 0, 0, "no daylight with the sun 30° down"); near(E.light(dark).L, 0.04, 0.001, "a moonless night's light");
near(E.light(dark, true).L, 0.5, 0.001, "night vision lifts the light"); near(E.light(dark, true).V, 8000, 0, "night vision: a ship shows farther");
near(E.light({ sun: { bearing: 180, altitude: 60 }, moon: dark.moon }, true).L, 1, 0, "night vision leaves daylight as it was");

// The chronology (guides/OPERATIONS-VIEWER.md 2.3 and 3). The tempo is derived from the entries, never stored.
const ok = (cond, what) => console.log(cond ? "ok  " : (failed++, "FAIL"), what);
const ev = (local, extra = {}) => ({ local, key: local.replace(" ", "T").replace(/(\d\d)(\d\d)$/, "$1:$2"), utc: null, ...extra });
// Venafro's shape: days, times as typed with no zone, the German reports placed by the account's order; three batteries followed
// (`of` is each actor's nationality; `opposed` and `source_kind` are the build's, from the followed subjects and SOURCES.yml)
const PARTS = [{ id: "battery-e", name: "Battery E, 67th CA (AA)", of: "us", unit: "67ca-e", followed: true }, { id: "battery-h", name: "Battery H, 67th CA (AA)", of: "us", unit: "67ca-h", followed: true },
               { id: "battery-a", name: "Battery A, 67th CA (AA)", of: "us", unit: "67ca-a", followed: true }];
const venafro = [
  ev("1944-01-17 1610", { actor: "Battery E", kind: "station", of: "us", source_kind: "record", n: 1, source: "Battery E, 67th CA (AA), morning report (record of events), 17 Jan 1944" }),
  ev("1944-02-12 0900", { actor: "Battery H", kind: "station", of: "us", source_kind: "record", n: 4, source: "Battery H, 67th CA (AA), morning report (record of events), 12 Feb 1944" }),
  ev("1944-02-14", { actor: "5. Geb.Div.", kind: "report", of: "de", opposed: true, source_kind: "record", n: 6, placed: "seq", source: "XIV Panzer Corps, tactical reports: 5. Geb.Div., Tagesmeldung vom 14.2.44" }),
  ev("1944-02-14 1740", { actor: "Battery E", kind: "casualty", of: "us", source_kind: "record", n: 5, source: "Battery E morning report, 14 Feb 1944" }),
  ev("1944-02-14", { actor: "5. Geb.Div.", kind: "report", of: "de", opposed: true, source_kind: "record", n: 7, placed: "seq", source: "XIV Panzer Corps, tactical reports: 5. Geb.Div., Nachmeldung zur Tagesmeldung vom 14.2.44" }),
  ev("1944-02-14 0900", { actor: "Battery A (1st Bn)", kind: "shelled", of: "us", source_kind: "record", n: 8, source: "Battery A morning report, 14 Feb 1944" }),
  ev("1944-02-21", { actor: "Arko 414", kind: "report", of: "de", opposed: true, source_kind: "record", n: 9, placed: "seq", source: "XIV Panzer Corps, tactical reports: Arko 414, Tagesmeldung vom 21.2.44" }),
];
ok(E.tempo(venafro) === "dated", "tempo: days and times as typed, no zone -> dated");
const clocked = [{ local: "1944-04-29 1603 K", key: "1944-04-29T06:03Z", utc: "1944-04-29T06:03Z" }, { local: "1944-04-29 1640 K", key: "1944-04-29T06:40Z", utc: "1944-04-29T06:40Z" }, { local: "1944-04-29 1710 K", key: "1944-04-29T07:10Z", utc: "1944-04-29T07:10Z" }];
ok(E.tempo(clocked) === "clocked", "tempo: every entry on GMT -> clocked");
// Remagen's shape: ten entries timed in zone A, fifteen "the period 110600 to 120600" over ten days: more than half untimed, so dated
const remagen = [...Array(10)].map((_, i) => ({ local: `1945-03-0${(i % 3) + 7} 1${i}00 A`, key: `1945-03-0${(i % 3) + 7}T0${i}:00Z`, utc: `1945-03-0${(i % 3) + 7}T0${i}:00Z` }))
  .concat([...Array(15)].map((_, i) => ({ local: `1945-03-${String(7 + (i % 10)).padStart(2, "0")}`, key: `1945-03-${String(7 + (i % 10)).padStart(2, "0")}`, utc: null, placed: "The day's total; no times typed" })));
ok(E.tempo(remagen) === "dated", "tempo: ten timed entries of twenty-five -> dated, not clocked");
ok(E.tempo([ev("1942-09-10"), ev("1943-02-01")]) === "monthly", "tempo: a span of more than 90 days with no times -> monthly");
ok(E.tempo([]) === "dated", "tempo: nothing -> dated");
// the spine: days with entries, timed entries first by the time as typed, then the placed ones in the account's order
const rows = E.chronologyRows(venafro, "dated");
ok(rows.map(r => r.key).join() === "1944-01-17,1944-02-12,1944-02-14,1944-02-21", "rows: one per day that has entries, in order");
ok(rows[0].label === "17 Jan" && rows[2].label === "14 Feb", "rows: labelled by the day, no year within one year");
ok(rows[2].entries.map(e => e.actor + (e.n ? ":" + e.n : "")).join("|") === "Battery A (1st Bn):8|Battery E:5|5. Geb.Div.:6|5. Geb.Div.:7", "rows: 0900, 1740, then the placed entries by n");
ok(E.chronologyRows([ev("1942-12-30 0800"), ev("1943-01-02")], "dated")[0].label === "30 Dec 1942", "rows: the year is said when the rows cross one");
const hours = E.chronologyRows(clocked, "clocked");
ok(hours.map(r => r.label).join() === "0600,0700" && hours[0].entries.length === 2 && hours[0].day === "29 Apr", "rows, clocked: one per GMT hour, the day beside it");
ok(E.chronologyRows([ev("1944-02-14"), ev("1944-02-20"), ev("1944-03-01")], "monthly").map(r => r.label).join() === "Feb 1944,Mar 1944", "rows, monthly: one per month");
// the columns: the followed batteries first in the participants' order and colours, then the German record by its source's stem
const cols = E.chronologyColumns(venafro, PARTS);
ok(cols.map(c => c.name).join("|") === "Battery E, 67th CA (AA)|Battery H, 67th CA (AA)|Battery A, 67th CA (AA)|XIV Panzer Corps", "columns: the subjects, then the other side's record");
ok(cols.map(c => c.colour).join() === "var(--c1),var(--c2),var(--c3),var(--ink)", "columns: the three checked colours for the subjects, ink for the other side");
ok(cols.map(c => c.of).join() === "us,us,us,de" && cols[3].opposed && !cols[0].opposed && cols[3].entries.length === 3, "columns: each carries its nationality and whether it is the other side; the three German reports share one column");
// Algiers' shape: the city's paper (a press source, by its kind) in the lighter ink; the Allied communiqué it prints is a column of its own by its actor
const algiers = E.chronologyColumns([
  ev("1943-05-13", { actor: "L'Écho d'Alger", kind: "report", of: "fr", source_kind: "press", source_of: "fr", n: 1, source: "L'Écho d'Alger, 13 May 1943" }),
  ev("1943-05-13", { actor: "Luftflotte 2", kind: "raid", of: "de", opposed: true, source_kind: "record", source_of: "de", n: 2, source: "German Naval Staff war diary, 13 May 1943, vol. 45, p. 163" }),
  ev("1943-05-14", { actor: "L'Écho d'Alger", kind: "report", of: "fr", source_kind: "press", source_of: "fr", n: 3, source: "L'Écho d'Alger, 14 May 1943" }),
  ev("1943-06-05", { actor: "Comando Supremo", kind: "bulletin", of: "it", opposed: true, source_kind: "press", source_of: "it", n: 4, source: "La Stampa, 6 June 1943, p. 1" }),
], [{ id: "battery-c", name: "Battery C, 62nd CA (AA)", of: "us", unit: "62ca-c", followed: true }]);
ok(algiers.map(c => c.name + ":" + c.colour + ":" + c.source_kind).join("|") === "L'Écho d'Alger:var(--ink-3):press|German Naval Staff war diary:var(--ink):record|La Stampa:var(--ink):press",
   "columns: the press in the lighter ink by its source's kind; the other side's record, and its bulletins in print, in ink");
ok(E.nation("de") === "German" && E.nation("jp") === "Japanese" && E.nation("uk") === "British" && E.nation("") === "" && E.nation("xx") === "XX", "nation: a code as the records give it, in a word; never a bloc");
ok(cols[2].entries.length === 1 && cols[2].participant === "battery-a", "columns: 'Battery A (1st Bn)' is Battery A's");
ok(/^morning report/.test(cols[0].record) && cols[3].record === "tactical reports", "columns: the record in the sources' words");
const boats = E.chronologyColumns([{ actor: "bang", of: "us", local: "1944-04-29 1603 K", source: "" }, { actor: "Nittatsu Maru", of: "jp", opposed: true, local: "1944-04-29", source: "" }],
                                   [{ id: "bang", name: "BANG", of: "us", colour: 2, track: "ss-385-bang/1", followed: true }, { id: "tama-17", name: "Convoy TAMA-17", of: "jp", convoy: "tama-17", followed: false }]);
ok(boats.map(c => c.name + ":" + c.colour).join("|") === "BANG:var(--c2)|Nittatsu Maru:var(--ink)", "columns: a boat by its id in the build's colour; a ship with no source by its actor");
ok(E.recordWords(["German Naval Staff war diary, 12 May 1943 (ONI translation), vol. 45, p. 152"], "German Naval Staff war diary") === "", "record words: a name, a date and a page say nothing more");
ok(E.recordWords(["No. 153 Squadron RAF, operations record book, Form 540 (summary of events), AIR 27/1027/37, p. 3"], "No. 153 Squadron RAF") === "operations record book", "record words: the record book");
ok(E.recordWords(["La Stampa, 14 Jan 1944, p. 1 (the German communiqué, Berlin, 13 Jan)"], "La Stampa") === "", "record words: a bracketed note's commas don't make pieces");
ok(E.hitKind("casualty") && E.hitKind("shelled") && !E.hitKind("station") && !E.hitKind("report"), "hit kinds: a casualty and a shelling, not a station or a report");
ok(E.head("Battery A (1st Bn)") === "Battery A" && E.head("Battery E, sections 2, 4, 6, 8") === "Battery E", "head: the name before a comma or a bracket");

// Sources and voices (guides/OPERATIONS-VIEWER.md 2.4, 7.1): a source's kind and whose it is, in a chip's words; never a bloc
ok(E.sourceKindWord("record", "us") === "record · US" && E.sourceKindWord("intelligence", "us") === "intelligence · US" && E.sourceKindWord("assessment", "us") === "assessment · US", "source kind: a record, intelligence, an assessment, with whose it is");
ok(E.sourceKindWord("press", "fr") === "French press" && E.sourceKindWord("press", "") === "press", "source kind: the press by its nationality");
ok(E.sourceKindWord("secondary", "us") === "secondary" && E.sourceKindWord("reference", "us") === "reference" && E.sourceKindWord("recollection", "us") === "recollection", "source kind: a later history, a reference, a recollection by the kind alone");
ok(E.sourceKindWord("record", "") === "record" && E.sourceKindWord("", "jp") === "Japanese" && E.sourceKindWord("", "") === "", "source kind: without a nationality, the kind; without a kind, the nationality");
ok(!/axis|allied/i.test(Object.values({ a: E.sourceKindWord("record", "de"), b: E.sourceKindWord("record", "jp"), c: E.sourceKindWord("press", "it") }).join()), "source kind: the other side named as the records name it");
// the column chips: the record's own words, then its source's kind and nationality where the entries carry one
ok(E.columnChip(cols[0]) === "morning report (record of events) · record · US" || /^morning report.* · record · US$/.test(E.columnChip(cols[0])), "column chip: 'morning report · record · US' (" + E.columnChip(cols[0]) + ")");
ok(E.columnChip(cols[3]) === "tactical reports · record · German", "column chip: the other side's record by its nationality");
ok(E.columnChip(algiers[0]) === "French press" && E.columnChip(algiers[2]) === "Italian press", "column chip: the press by its nationality, no record words");
ok(E.columnChip(boats[1]) === "Japanese", "column chip: an entry with no citation falls back to the nationality alone");
ok(cols[3].source_of === "" && algiers[0].source_of === "fr", "columns: each carries its source's nationality where its entries do");

// The cross-references' arithmetic (tools/check_crossrefs.py, moved here): BANG's Attack 1 at 2256 K, 29 April 1944, at
// 19-26N 118-45E; Nittatsu Maru's log has Takegawa Maru torpedoed at 2201 I at 19-20N 118-50E. By hand: 1256 and 1301 GMT,
// 5 minutes; 6' of latitude and 5' of longitude at 19.4° (4.72 nm) are 7.6 nm apart
const sheet1 = { utc: "1944-04-29T12:56Z", lat: E.coord("19-26N"), lon: E.coord("118-45E") }, j03 = { utc: "1944-04-29T13:01Z", lat: E.coord("19-20N"), lon: E.coord("118-50E") };
near(E.apart(sheet1, j03).minutes, 5, 0, "apart: the sheet at 2256 K and the log at 2201 I are 5 minutes apart");
near(E.apart(sheet1, j03).nm, 7.6, 0.05, "apart: 19-26N 118-45E and 19-20N 118-50E are 7.6 nm apart");
near(E.apart(j03, sheet1).minutes, -5, 0, "apart: the other way round is negative");
ok(E.apart(sheet1, { utc: "1944-04-29T13:01Z" }).nm === null && E.apart({ lat: 1, lon: 1 }, j03).minutes === null, "apart: null where either lacks a position or a time");

// The Sources view's moments from a frame's JSON, in TAMA-17's shape: a pair's sources are the sheet, the record and the
// entries of other kinds within two hours that name the ship; the arithmetic between the sheet and each
const tama = {
  participants: [{ id: "bang", name: "BANG", of: "us", track: "ss-385-bang/1", colour: 1, followed: true }],
  fixes: [{ who: "bang", ref: "Attack 1", utc: "1944-04-29T12:56Z", lat: 19.4333, lon: 118.75, raw: "19-26N 118-45E", local: "1944-04-29 2256 K", on_track: true, assumed: false, fix: "", note: "Torpedo attack No. 1", cite: { ref: "rg367-74802746/p16", href: "#", label: "p. 16", kind: "record", of: "us" } }],
  sheets: { bang: { "Attack 1": { torpedoes: [{ date: "1944-04-29", time: "2256", zone: "K" }], words: [{ description: "Convoy consisting of at least 12 ships", sunk: "None.", damaged: "One 7000 ton AK probably sunk." }], cite: { ref: "rg367-74802746/p16", href: "#", label: "p. 16", kind: "record", of: "us" } } } },
  events: [
    { actor: "FRUPAC", title: "Yoshima Maru", kind: "report", words: "Yoshima Maru / att. by torp / 2215/29", note: "frupac.yml ties this note to BANG's Attack 1", local: "1944-04-29 2215", utc: "1944-04-29T13:15Z", lat: 19.4, lon: 118.7, basis: "estimated", source: "FRUPAC overlay, 29 April", source_kind: "intelligence", source_of: "us", cite: { ref: "metapth1733008", href: "#", label: "map", kind: "intelligence", of: "us" } },
    { actor: "combinedfleet", title: "Takegawa Maru", kind: "sank", words: "Takegawa Maru sunk by BANG", local: "1944-04-29 2155 I", utc: "1944-04-29T12:55Z", source: "combinedfleet.com", source_kind: "secondary", source_of: "", cite: { ref: "combinedfleet:Nittatsu_t", href: "#", label: "page", kind: "secondary", of: "" } },
    { actor: "JANAC", title: "Kinrei Maru", kind: "loss", words: "Kinrei Maru to BANG", local: "1944-05-04", utc: "1944-05-03T16:06Z", source: "JANAC", source_kind: "assessment", source_of: "us", cite: { ref: "janac:4/p59", href: "#", label: "p. 59", kind: "assessment", of: "us" } },
    { origin: "japanese", record: "J03", actor: "Takegawa Maru", kind: "torpedoed", utc: "1944-04-29T13:01Z", source_kind: "record", source_of: "jp" },
    { actor: "bang", kind: "attack", title: "Attack 1", words: "Torpedo attack No. 1", utc: "1944-04-29T12:56Z", source_kind: "record", source_of: "us" }],
  pairs: [{ attack: "Attack 1", boat: "bang", utc: "1944-04-29T12:56Z", relation: "hit", note: "Takegawa Maru (1,930 GRT), TAMA-17",
            record: { id: "J03", event: "torpedoed", ship: "Takegawa Maru", date: "1944-04-29", time: "2201", zone: "I", local: "1944-04-29 2201 I", utc: "1944-04-29T13:01Z", lat: 19.3333, lon: 118.8333, lat_raw: "19-20N", lon_raw: "118-50E",
                      original: "二九日二二時〇一分…竹川丸敵潜水艦ノ魚雷攻撃ヲ受ケ", lang: "ja", translation: "At 2201 on the 29th … Takegawa Maru was torpedoed", note: "Nittatsu Maru's own movement log", cite: { ref: "jacar:C08050103200 p23", href: "#", label: "p. 23", source_title: "JACAR", kind: "record", of: "jp" } } }] };
const M = E.pairMoments(tama);
ok(M.length === 1 && M[0].sources.length === 4, "moments: one pair, four sources (the sheet, the record, FRUPAC and combinedfleet; JANAC is days away)");
ok(M[0].sources.map(s => s.role + ":" + E.sourceKindWord(s.kind, s.of)).join("|") === "attack:record · US|record:record · Japanese|near:intelligence · US|near:secondary", "moments: the sources' kinds, in order");
ok(M[0].sources[0].typed === "1944-04-29 2256 K" && M[0].sources[0].raw === "19-26N 118-45E" && M[0].sources[0].words.map(w => w.typed).join("|") === "Convoy consisting of at least 12 ships|Sunk: None.|Damaged: One 7000 ton AK probably sunk.", "moments: the sheet as typed, its position and its words");
ok(M[0].sources[1].words[0].lang === "ja" && M[0].sources[1].raw === "19-20N 118-50E" && M[0].sources[1].zone === "I", "moments: the record in its own language, its position as written, its zone");
near(M[0].apart[0].minutes, 5, 0, "moments: the sheet and the log, 5 minutes"); near(M[0].apart[0].nm, 7.6, 0.05, "moments: and 7.6 nm");
near(M[0].apart[1].minutes, 19, 0, "moments: the sheet and FRUPAC, 19 minutes"); near(M[0].apart[1].nm, 3.46, 0.05, "moments: and 3.5 nm (2' of latitude, 3' of longitude at 19.4°)");
ok(M[0].apart[2].nm === null && M[0].apart[2].minutes === -1, "moments: combinedfleet has no position, and is a minute before the sheet");
ok(M[0].ours.relation === "hit" && /^a hit/.test(M[0].ours.words) && M[0].ours.note === "Takegawa Maru (1,930 GRT), TAMA-17", "moments: what we make of it is the pairing's relation and note");
ok(E.pairMoments({ participants: [], fixes: [], events: [], pairs: [] }).length === 0, "moments: none without pairs");

// The questions the records leave open: answers by source for the view, merged by their words for the board, each badged
// by its source's kind, the weight kept where it differs; an inference keeps its own mark
const claims = [
  { question: "When was she hit?", answer: "1250 Item", weight: "record", source: "Haynsworth action report, p. 3", source_kind: "record", source_of: "us", cite: { ref: "a" } },
  { question: "When was she hit?", answer: "1250 Item", weight: "record", source: "Haynsworth war diary, p. 3", source_kind: "record", source_of: "us", cite: { ref: "b" } },
  { question: "When was she hit?", answer: "1245", weight: "recollection", source: "Irons, Phalanx", source_kind: "secondary", source_of: "", note: "told later", cite: { ref: "c" } },
  { question: "Who flew it?", answer: "a Judy of the 210th", weight: "inference", source: "the two records together", source_kind: "record", source_of: "jp", cite: { ref: "d" } }];
const Q = E.claimMoments(claims);
ok(Q.length === 2 && Q[0].question === "When was she hit?", "questions: one moment per question, in order");
ok(Q[0].columns.map(c => c.name + ":" + c.kind).join("|") === "Haynsworth action report:record|Haynsworth war diary:record|Irons:secondary", "questions: the answers by source, each with its source's kind");
ok(Q[0].answers.length === 2 && Q[0].answers[0].cites.length === 2 && Q[0].answers[0].sources.length === 2, "board: two answers in the same words are one line with both citations");
ok(Q[0].answers[0].mark === "record" && Q[0].answers[0].words === "record", "board: badged by the source's kind where the weight agrees");
ok(Q[0].answers[1].mark === "secondary" && Q[0].answers[1].words === "secondary · as recollection" && Q[0].answers[1].notes[0] === "told later", "board: the weight kept where it differs from the kind");
ok(Q[1].answers[0].mark === "inference" && Q[1].answers[0].words === "inference", "board: an inference keeps its own mark");
ok(E.badge({ weight: "record", source_kind: "" }).mark === "record" && E.badge({ weight: "photo", source_kind: "secondary" }).words === "secondary · as photo", "badge: without a kind the weight; a photo in a later history");

process.exit(failed ? 1 : 0);
