// Text with links written by name, as a page shows it. The hand-edited Markdown (records/operations/ and a family's
// own files) writes a link as [[kind:name|label]], not as an address, so the same text works on the kit's pages and
// on a family's, which sit in different folders; tools/build_operations.py checks every one. This turns them into
// links, and handles the little Markdown the text uses: *italics*, **bold**, `code`, and [words](address).
//
//   Links.render(text, { cites, family })
//     cites    the resolved citations: operations.json's "cites" ({ "howe-nwa/35/p676": {href, short, page} })
//     family   on a family's page: { root: the family site's address, pages: [its own pages' names] }
//
// Paths are worked out from this script's own address, so it works wherever the kit is.
const Links = (() => {
  const KIT_SITE = new URL(".", document.currentScript.src);
  const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const a = (href, label, title) =>
    `<a href="${esc(href)}"${title ? ` title="${esc(title)}"` : ""}${/^https?:/.test(href) && !href.startsWith(location.origin) ? ' target="_blank" rel="noopener"' : ""}>${label}</a>`;

  function link(kind, name, label, ctx) {
    const [target, day] = name.split("@");
    const t = day ? `&t=${day}` : "";
    const fam = ctx.family;
    switch (kind) {
      case "op": return a(`#op-${target}`, label || esc(target));
      case "ship": return a(new URL(`patrols.html?ship=${encodeURIComponent(target)}`, KIT_SITE).href, label || esc(target));
      case "unit": return a(new URL(`army.html?unit=${encodeURIComponent(target)}${t}`, KIT_SITE).href, label || esc(target));
      case "convoy": return a(new URL(`convoys.html?c=${encodeURIComponent(target)}`, KIT_SITE).href, label || esc(target));
      case "engagement": return a(new URL(`engagement.html?e=${encodeURIComponent(target)}`, KIT_SITE).href, label || esc(target));
      case "page": {
        const href = fam && fam.pages.includes(target) ? new URL(`${target}.html`, fam.root).href : new URL(`${target}.html`, KIT_SITE).href;
        return a(href, label || esc(target));
      }
      case "who":
        if (fam) return a(new URL(`army.html?who=${encodeURIComponent(target)}${t}`, fam.root).href, label || esc(target));
    }
    return `<span class="link-unknown" title="[[${esc(kind)}:${esc(name)}]] isn't a link this page knows">${label || esc(name)}</span>`;
  }

  // a run of citations side by side becomes one bracket: (Howe p. 675; Howe p. 667)
  function cites(list, ctx) {
    return `<span class="src">(${list.map(c => {
      const r = (ctx.cites || {})[c];
      return r ? a(r.href, `${esc(r.short)}${r.page ? ` p.&nbsp;${esc(r.page)}` : ""}`, r.title) : esc(c);
    }).join("; ")})</span>`;
  }

  function render(text, ctx = {}) {
    const code = [];
    let s = esc(text).replace(/`([^`]+)`/g, (_, c) => `\u0000${code.push(c) - 1}\u0000`);
    s = s.replace(/(?:\s*\[\[cite:[^\]]+\]\])+/g, run => " " + cites([...run.matchAll(/\[\[cite:([^\]]+)\]\]/g)].map(m => m[1].trim()), ctx));
    s = s.replace(/\[\[(\w+):([^\]|]+)(?:\|([^\]]+))?\]\]/g, (_, kind, name, label) => link(kind, name.trim(), label, ctx));
    s = s.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (_, label, href) => a(href.replace(/&amp;/g, "&"), label));
    s = s.replace(/\*\*([^*\s][^*]*)\*\*/g, "<b>$1</b>");
    s = s.replace(/(^|[\s(])\*([^*\s][^*]*)\*/g, "$1<i>$2</i>");
    return s.replace(/\u0000(\d+)\u0000/g, (_, i) => `<code>${code[+i]}</code>`);
  }

  return { render };
})();
