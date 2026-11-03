// The libraries the pages load from a CDN, one pinned address each. A page's <script src> must match these exactly;
// change a version here and in every page that loads it (grep the old address), never in one page alone.
//   D3 7.9.0              https://cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js
//   topojson-client 3.1.0 https://cdn.jsdelivr.net/npm/topojson-client@3.1.0/dist/topojson-client.min.js
//   js-yaml 4.1.0         https://cdn.jsdelivr.net/npm/js-yaml@4.1.0/dist/js-yaml.min.js   (index.html)
//   suncalc 1.9.0         https://cdn.jsdelivr.net/npm/suncalc@1.9.0/suncalc.min.js        (engagement.html)
// The land and country outlines (world-atlas@2 on jsdelivr) are fetched by the scripts that draw them.
//
// Where the pages load from, relative to site/.
//   RECORDS    the transcribed records (records/, the wwii-unit-records repository)
//   REFERENCE  reference tables (the Japanese kana grid)
//   CACHE      local copies of the scans (tools/nara.py fetch; git-ignored). Optional: a page
//              falls back to the archive's own copy when a scan isn't here.
//   LOCAL      served from this machine (tools/serve.py), where the cache and the kit's tools are;
//              the published site has neither, so its messages don't mention them.
const RECORDS = "../records/";
const REFERENCE = "../reference/";
const CACHE = "../sources/";
const LOCAL = /^(localhost|127\.0\.0\.1|\[::1\])$/.test(location.hostname);
