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
