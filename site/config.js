// Where the pages load from, relative to site/.
//   RECORDS    the transcribed records (records/, the wwii-unit-records repository)
//   REFERENCE  reference tables (the Japanese kana grid)
//   CACHE      local copies of the scans (tools/nara.py fetch; git-ignored). Optional: a page
//              falls back to the archive's own copy when a scan isn't here.
const RECORDS = "../records/";
const REFERENCE = "../reference/";
const CACHE = "../sources/";
