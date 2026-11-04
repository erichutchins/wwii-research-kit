// The navigation bar at the top of every page's header: one copy, written into the page's placeholder
// (<nav class="nav" aria-label="The kit" data-nav></nav>) as the page is parsed, so a page added to the kit is added
// to the bar here and nowhere else. The link to the page being read is marked aria-current="page" (the stylesheets
// underline it). The bar is the shape of guides/OPERATIONS-VIEWER.md 5.3 as far as phase 6 takes it: the theatres,
// the subjects (every boat, ship, unit, battalion and convoy, each on its own page), the engagements, reading the
// records, researching a relative; no ship, no view, no single app.
// Load it right after the placeholder: it then fills the bar before the rest of the header is parsed, so nothing shifts
// or flashes. Loaded anywhere else (deferred, or in the head), it fills the bar once the document is parsed.
// The links are the kit's pages, relative to this script, so a family's pages (which load it as kit/site/nav.js) link
// to the kit's pages, not to their own folder.
(() => {
  const SITE = new URL(".", document.currentScript.src);
  const BAR =
    '<a class="home" href="index.html">WWII research kit</a>' +
    '<span class="grp"><a class="lbl" href="index.html#pacific">Pacific</a><a href="lanes.html">Sea lanes</a></span>' +
    '<span class="grp"><a class="lbl" href="index.html#europe">Algiers to Germany</a>' +
      '<a href="index.html#stage-algiers">Algiers</a><a href="index.html#stage-sicily">Sicily</a>' +
      '<a href="index.html#stage-italy">Italy</a><a href="index.html#stage-france">France</a>' +
      '<a href="index.html#stage-germany">Germany</a></span>' +
    '<span class="grp ref"><a class="lbl" href="subjects.html">Every theater</a>' +
      '<a href="subjects.html">Subjects</a><a href="engagement.html">Engagements</a></span>' +
    '<span class="grp"><a class="lbl" href="index.html#reference">Reading the records</a><a href="zones.html">Time zones</a>' +
      '<span class="sub"><span class="lbl">Grids:</span><a href="jgrid.html">Japanese</a><a href="grids.html">US Army</a>' +
        '<a href="german.html">German</a></span>' +
      '<span class="sub"><span class="lbl">How it worked:</span><a href="torpedo.html">Torpedoes</a></span>' +
      '<a href="silhouettes.html">Silhouettes</a></span>' +
    '<a href="relatives.html">Researching a relative</a>';

  function fill() {
    const nav = document.querySelector("nav[data-nav]");
    if (!nav || nav.childElementCount) return;
    nav.innerHTML = BAR;
    const elsewhere = new URL(".", location.href).href !== SITE.href;   // a family's page: the kit's pages are in another folder
    const here = location.pathname.replace(/\/$/, "/index.html");
    for (const a of nav.querySelectorAll("a")) {
      const u = new URL(a.getAttribute("href"), SITE);
      if (elsewhere) a.href = u.href;
      else if (u.hash && u.pathname === here) a.href = u.hash;   // the front page's own sections: scroll, don't reload
      if (!u.hash && u.pathname === here) a.setAttribute("aria-current", "page");
    }
  }

  if (document.querySelector("nav[data-nav]")) fill();
  else addEventListener("DOMContentLoaded", fill);
})();
