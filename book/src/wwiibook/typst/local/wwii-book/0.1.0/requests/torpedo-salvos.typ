// Part of the wwii-book package (lib.typ imports it).
// A request function: `init` makes it with the book's asset lookup (get) and file loader (load).
#import "../core.typ": *

#let make-torpedo-salvos(get, load) = {
  // Each torpedo of the named attacks as a small silhouette (torpedoes.py, from a boat's attacks.csv): one row an
  // attack, its forward tubes pointing forward and its after tubes aft, in the order fired, each tube's number beside
  // it; red where the attack sheet records a hit, outlined for a miss or no result. `attacks` names the sheets' attacks
  // ("Attack 1"); none draws every attack in the file. Drawn at its own size (a column holds it) unless `width` is
  // given. `key: true` adds a line citing the sheets' pages.
  let torpedo-salvos(path, attacks: none, width: none, caption: none, key: false) = {
    let key-id = "torpedo-salvos:" + repr((path, attacks))
    _request("torpedoes", key-id, (path: path, attacks: attacks))
    let a = get(key-id)
    if a == none {
      std.figure(_pending("torpedoes · " + path, height: 1.6in), caption: caption, kind: image)
    } else {
      std.figure(image(load(a.path), width: if width == none { a.width * 1in } else { width }), caption: caption)
      if key {
        text(size: 6.5pt, fill: tokens.muted)[As the attack sheets type them: #a.cites.join(", ").]
      }
    }
  }
  torpedo-salvos
}
