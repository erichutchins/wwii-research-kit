// Part of the wwii-book package (lib.typ imports it).
// A request function: `init` makes it with the book's asset lookup (get) and file loader (load).
#import "../core.typ": *
#import "../components/other-side.typ": other-side-source

// A convoy that several boats attacked (convoy_ships.py, from the kit's engagement.json, the boats' attack data sheets
// and the Japanese records). `parts` chooses what this call sets, so a page can place them apart from one asset:
// "silhouettes" (the convoy's ships at one scale, each marked with her fate as the Japanese records give it: a red
// cross sunk, a red ring damaged) and "tally" (one row an attack: the boat's claim as typed, JANAC's entries as
// printed, the Japanese record paired with it and how; then a line a boat of what each record counts).
#let make-convoy-ships(get, load) = {
  let head(h) = text(font: tokens.display, weight: "semibold", style: "italic", h)
  let small(body) = text(size: 6.4pt, fill: tokens.muted, body)
  let page-of(ref, words, href) = if ref.starts-with("jacar:") { other-side-source(ref, href) } else if href != none {
    link(href, words) } else { words }

  let claim-cell(c) = {
    let bits = ()
    if c.sunk != "" { bits.push([Sunk: #typed(c.sunk)]) }
    if c.damaged != "" { bits.push([Damaged: #typed(c.damaged)]) }
    if c.hits != "" { bits.push([Hits: #typed(c.hits)]) }
    if c.determined_by != "" { bits.push([Determined by: #typed(c.determined_by)]) }
    if bits.len() == 0 { bits.push(text(fill: tokens.muted)[No ship claimed]) }
    bits.join(linebreak())
    if c.cite != "" { linebreak(); small(c.cite) }
  }

  let janac-cell(js) = if js.len() == 0 { text(fill: tokens.muted)[No entry] } else {
    js.map(j => [#j.ship, #j.tons tons#if j.type != "" [ (#j.type)], #j.date: credits #j.agent#if j.probable [
      #small[(probable agent: the list's asterisk)]] #small(page-of(j.ref, j.page, j.href))]).join(v(3pt))
  }

  let record-cell(rs) = if rs.len() == 0 { text(fill: tokens.muted)[No Japanese record paired with it] } else {
    rs.map(r => {
      text(font: tokens.display, weight: "semibold")[#r.id#if r.unit != "" [ (#r.unit)]#if r.local != "" [ · #r.local]]
      if not r.primary { small[ · a secondary account] }
      linebreak()
      if r.original != "" { text(font: tokens.ja, size: 6.6pt, lang: "ja", r.original); linebreak() }
      [#r.translation ]
      small(page-of(r.ref, r.page, r.href))
      linebreak()
      text(size: 6.4pt)[_Paired as #r.relation:_ #r.relation_words.]
    }).join(v(3pt))
  }

  // `width`: the silhouettes' width; `auto` takes the width of the block it is set in (`across` both columns).
  // The tally is as wide as its container: on the magazine grid, set it where the page has one column across both.
  let convoy-ships(engagement, width: auto, parts: ("silhouettes", "tally"), caption: none) = {
    if width == auto { return layout(size => convoy-ships(engagement, width: size.width, parts: parts, caption: caption)) }
    let key-id = "convoyships:" + engagement + ":" + repr(width)
    _request("convoyships", key-id, (engagement: engagement, width: width / 1in))
    let a = get(key-id)
    if a == none {
      std.figure(_pending("convoy ships · " + engagement + " · " + parts.join(", "), height: 1.6in),
                 caption: caption, kind: image)
      return
    }
    if "silhouettes" in parts {
      std.figure(image(load(a.path), width: width), caption: caption)
      block(above: 3pt, small[Plates from the kit's silhouette library (records/silhouettes: #a.silhouette_sources.join(", ")),
        drawn for this research at one scale. *Sources:* #a.cites.map(c => if c.starts-with("jacar:") {
          other-side-source(c, none) } else { raw(c) }).join("; ").])
    }
    if "tally" in parts {
      let t = a.tally
      if "silhouettes" in parts { v(8pt) }
      set text(size: 7pt, top-edge: "cap-height", bottom-edge: "baseline")
      set par(justify: false, leading: 0.6em, spacing: 0.6em, first-line-indent: 0pt)
      table(
        columns: (0.95in, 1.25fr, 0.95fr, 1.7fr),
        stroke: (x, y) => if y == 0 { (bottom: 0.7pt + tokens.ink) } else { (bottom: 0.25pt + tokens.rule) },
        inset: (x: 3pt, y: 3pt),
        table.header(..("Boat and attack", "Her claim, as typed", "JANAC (1947), as printed",
                        "The Japanese record, and how it is paired").map(head)),
        ..t.rows.map(r => (
          {
            text(font: tokens.display, weight: "bold", fill: rgb(r.colour), r.name)
            [ #r.attack]
            for tm in r.times {
              linebreak()
              typed(tm.typed)
              if tm.gmt != "" { linebreak(); small[#tm.gmt#if r.times.len() > 1 [ (#tm.from)]] }
            }
          },
          claim-cell(r.claim),
          janac-cell(r.janac),
          record-cell(r.records),
        )).flatten(),
      )
      v(4pt)
      block(breakable: false, {
        set text(size: 7pt, top-edge: "cap-height", bottom-edge: "baseline")
        for b in t.boats {
          block(above: 3pt, below: 0pt, [
            #text(font: tokens.display, weight: "bold", fill: rgb(b.colour), b.name):
            #b.attacks #if b.attacks == 1 [attack] else [attacks] on the convoy; claimed #b.claimed_sunk sunk and
            #b.claimed_damaged damaged (the ships her sheets name, counted as typed).
            JANAC credits #if b.janac.len() == 0 [none] else [#b.janac.len(): #b.janac.map(j =>
              [#j.ship (#j.tons#if j.probable [, probable])]).join(", ")].
            Losses in the Japanese records paired with her attacks: #if b.japanese_paired.len() == 0 [none] else {
              b.japanese_paired.map(p => [#p.ship (#p.relations.join(", "))]).join(", ") }.])
        }
        block(above: 4pt, below: 0pt, t.lost_words)
        block(above: 4pt, small[A pairing is a lead, not a finding: _hit_ means the attack caused that record; _probable_,
          time and place point to it though another boat is credited or was attacking too; _possible_, more than one
          attack could explain the record. JANAC is the postwar Joint Army-Navy Assessment Committee's list; its
          credits are an assessment, set beside the records, not one of them. *Sources:*
          #t.pages.join("; ").])
      })
    }
  }
  convoy-ships
}
