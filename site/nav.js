// The navigation bar at the top of every page's header: one copy, written into the page's placeholder
// (<nav class="nav" aria-label="The kit" data-nav></nav>) as the page is parsed, so a page added to the kit is added
// to the bar here and nowhere else. The link to the page being read is marked aria-current="page" (the stylesheets
// underline it); a page opened by its address (theatre.html?t=pacific) marks the link with the same query. The bar is
// the shape of guides/OPERATIONS-VIEWER.md 5.3 and nothing else: the engagements (every one read from both sides, the
// kit's way in), the four theatres, the subjects (every boat, ship, unit, battalion and convoy, each on its own page),
// reading the records (the explainers), researching a relative; no ship, no view, no place. The breadcrumb under it
// (chapter.css, Chapter.trail) does the walking.
// Load it right after the placeholder: it then fills the bar before the rest of the header is parsed, so nothing shifts
// or flashes. Loaded anywhere else (deferred, or in the head), it fills the bar once the document is parsed.
// The links are the kit's pages, relative to this script, so a family's pages (which load it as kit/site/nav.js) link
// to the kit's pages, not to their own folder.
(() => {
  const SITE = new URL(".", document.currentScript.src);
  const BAR =
    '<a class="home" href="index.html">WWII research kit</a>' +
    '<span class="grp"><a href="engagements.html">Engagements</a></span>' +
    '<span class="grp"><a href="theatre.html?t=pacific">Pacific</a><a href="theatre.html?t=europe">Europe</a>' +
      '<a href="theatre.html?t=mediterranean">Mediterranean</a><a href="theatre.html?t=atlantic">Atlantic</a></span>' +
    '<span class="grp ref"><a href="subjects.html">Subjects</a></span>' +
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
      if (!u.hash && u.pathname === here && (!u.search || u.search === location.search)) a.setAttribute("aria-current", "page");
    }
  }

  if (document.querySelector("nav[data-nav]")) fill();
  else addEventListener("DOMContentLoaded", fill);
})();
