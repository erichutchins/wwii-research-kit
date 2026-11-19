// The wwii-book Typst package: the page, the components, and the request functions.
//
// A request function (facsimile, records, qr-tag) writes a `<wwii-request>` metadata entry and draws a placeholder
// until the Python build has prepared it into the book's build/ folder; then it draws the real thing. Use:
//
//   #import "@local/wwii-book:0.1.0": *
//   #let wwii = init(assets: json("build/assets.json"), load: p => read(p, encoding: none))
//   #show: book
//
// The loader is a closure written in the book's own file, so it reads paths relative to the book, not to this package.

#import "core.typ": *
#import "components/record-quote.typ": *
#import "components/mark-key.typ": *
#import "components/unit-key.typ": *
#import "components/torpedo-ledger.typ": *
#import "components/basis.typ": *
#import "components/photo-caption.typ": *
#import "templates/chapter-opener.typ": *
#import "templates/covers.typ": *
#import "components/note.typ": note, source-line, note-counter, section-sources, endnotes, part-notes
#import "components/other-side.typ": other-side, other-side-source
#import "components/call-to-action.typ": see-it-move, cta-mark
#import "templates/grid.typ": on-grid, part-title, grids, note-reach, end-mark
#import "templates/running-text.typ": running-text, across, across-all, balance, ship-line, map-frame
#import "requests/facsimile.typ": make-facsimile
#import "requests/records.typ": make-records
#import "requests/qr-tag.typ": make-qr-tag, make-punch-card
#import "requests/engagement-figure.typ": make-engagement-figure
#import "requests/picture.typ": make-picture
#import "requests/route-map.typ": make-route-map
#import "requests/oblique-view.typ": make-oblique-view
#import "requests/situation-map.typ": make-situation-map
#import "requests/atlas-view.typ": make-atlas-view
#import "requests/unit-chain.typ": make-unit-chain
#import "requests/aircraft-card.typ": make-aircraft-card
#import "requests/maneuvering-board.typ": make-maneuvering-board
#import "requests/fire-control.typ": make-fire-control
#import "requests/convoy-route.typ": make-convoy-route
#import "requests/convoy-ships.typ": make-convoy-ships
#import "requests/torpedo-salvos.typ": make-torpedo-salvos
#import "requests/silhouette.typ": make-silhouette
#import "requests/grid-figure.typ": make-grid-figure

// The request functions, made with the book's assets and loader: `#let wwii = init(...)`, then `(wwii.atlas-view)(...)`.
#let init(assets: (:), load: none) = {
  let get(key) = assets.at(key, default: none)
  (facsimile: make-facsimile(get, load), records: make-records(get, load), qr-tag: make-qr-tag(get, load), punch-card: make-punch-card(get, load), engagement-figure: make-engagement-figure(get, load), picture: make-picture(get, load), route-map: make-route-map(get, load), oblique-view: make-oblique-view(get, load), situation-map: make-situation-map(get, load), atlas-view: make-atlas-view(get, load), unit-chain: make-unit-chain(get, load), aircraft-card: make-aircraft-card(get, load), maneuvering-board: make-maneuvering-board(get, load), fire-control: make-fire-control(get, load), convoy-route: make-convoy-route(get, load), convoy-ships: make-convoy-ships(get, load), torpedo-salvos: make-torpedo-salvos(get, load), silhouette: make-silhouette(get, load), grid-figure: make-grid-figure(get, load))
}
