// The frame's own figures (guides/OPERATIONS-VIEWER.md 4.1): the panels an engagement's page mounts after its story, by
// the engagement's id. Each panel is { id, heading, intro, mount(host, D) }: engagement.js makes a card with the heading and
// the intro, and mount draws into the card's body from the built engagement D (engagement.json) and the kit's
// silhouettes (silhouettes.js, loaded by then). A panel's module lives under site/panels/ and is loaded by
// engagement.html before this registry; an engagement with no entry here has no figures of its own. The styles are
// panels.css, scoped under .panel-card.
// Figures any engagement can have, each mounted where its `applies(D)` says so, after the engagement's own: the water
// column (panels/depth.js) wherever a boat's depth log is transcribed.
const PANELS_ANY = [window.DepthPanel].filter(Boolean);
const PANELS = {
  "haynsworth-1945-04-06": window.HaynsworthPanels || [],
};
