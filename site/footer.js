// Page footer: where the kit and the records live, and when this copy of the site was built.
// The deploy workflow (.github/workflows/pages.yml) overwrites build.json next to the pages with the build
// time and each repository's commit and its date. The committed build.json is empty ({"built": null}),
// so a local copy shows the links only.
(() => {
  const KIT = "https://github.com/erichutchins/wwii-research-kit";
  const RECORDS_REPO = "https://github.com/erichutchins/wwii-unit-records";
  const day = iso => new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
  const stamp = iso => new Date(iso).toLocaleString("en-GB", { day: "numeric", month: "short", year: "numeric",
                                                              hour: "2-digit", minute: "2-digit", timeZone: "UTC" }) + " UTC";
  const link = (href, text) => { const a = document.createElement("a"); a.href = href; a.textContent = text; a.rel = "noopener"; return a; };

  const style = document.createElement("style");
  style.textContent = `.site-foot { max-width: 1080px; margin: 0 auto; padding: 14px 20px 22px; font: 12px/1.6 system-ui, sans-serif;
    color: inherit; opacity: 0.72; display: flex; flex-wrap: wrap; gap: 4px 18px; border-top: 1px solid currentColor;
    border-top-color: color-mix(in srgb, currentColor 18%, transparent); }
    .site-foot a { color: inherit; }`;
  document.head.append(style);

  const foot = document.createElement("footer");
  foot.className = "site-foot";
  const repos = document.createElement("span");
  repos.append(link(KIT, "Research kit on GitHub"), " · ", link(RECORDS_REPO, "Unit records on GitHub"));
  const built = document.createElement("span");
  foot.append(repos, built);
  document.body.append(foot);

  fetch(new URL("build.json", document.currentScript.src)).then(r => r.ok ? r.json() : null).catch(() => null).then(b => {
    if (!b || !b.built) return;
    const ver = (name, repo, c) => [`${name} `, link(`${repo}/commit/${c.sha}`, c.sha.slice(0, 7)), ` (${day(c.date)})`];
    built.append(`Built ${stamp(b.built)} from `, ...ver("kit", KIT, b.kit), " and ", ...ver("records", RECORDS_REPO, b.records));
  });
})();
