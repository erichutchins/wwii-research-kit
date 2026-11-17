// Part of the wwii-book package (lib.typ imports it).
// A request function: `init` makes it with the book's asset lookup (get) and file loader (load).
#import "../core.typ": *
#import "../components/mark-key.typ": mark-key
#import "../components/unit-key.typ": unit-key

#let make-records(get, load) = {
  // A records file (CSV, YAML or JSON, by its path under records/), handed to `body` as Typst data:
  //   #(wwii.records)("boats/ss-385-bang/patrol-1/attacks.csv", torpedo-ledger)
  // A placeholder until it is prepared. (A callback, because the request is content that has to be placed, and a
  // function can't both place content and return data.)
  let records(path, body) = {
    _request("records", "records:" + path, (path: path))
    let a = get("records:" + path)
    if a == none { _pending(path, height: 0.8in) } else { body(json(load(a.path))) }
  }
  records
}
