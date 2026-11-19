"""A part's notes on pages of their own (`on-grid.with(notes: "part")`, `--input notes=part`).

A section built in this mode sets no notes: each note is written out as Typst metadata (`<wwii-part-note>`: its
number, its chapter's title and its whole text, its source line resolved against the section's own sources) and so
are the section's sources (`<wwii-part-sources>`) and its sources' titles (`<wwii-part-titles>`). `collect` reads
them back with `typst query`; `abbreviate` gives a repeated citation its short form; `sections` groups a part's notes
by section (a run of notes numbered from 1: a book file, or a chapter that begins its numbering again) and by chapter;
`merge_sources` makes one list of the part's sources, each source's pages joined; `write` writes the Typst file that
sets them with `part-notes`, which the build then compiles like any other piece of the book.

Repeated citations: within a part's notes, the first note citing a source gives it in full and a later note that is
the citation alone gives its short form: an archive item by its NAID and page ("NAID 125583404, p. 6"); another source
by the short title its entry declares (`(title: [...], short: [...])`), or else its title with the parenthesised
asides left out ("_Calexico Chronicle_, 29 January 1942, p. 1"). A note with words of its own is never shortened, and
a note that is a source's title alone (a family paper cited by its name) counts as a citation of that source.

The notes' texts come back from Typst as content (a tree of elements in JSON); `markup` writes that tree as Typst
markup again: text, spaces, smart quotes, emphasis, strong, links, raw, super- and subscripts, and line breaks, with
anything else set as its plain text.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .build import _query


def _str(s: str) -> str:
    return json.dumps(s, ensure_ascii=False)          # a Typst string literal: JSON's escapes are Typst's


def plain(node) -> str:
    """The text of a content tree, without its markup."""
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return "".join(plain(n) for n in node)
    f = node.get("func")
    if f in ("text", "symbol"):
        return node.get("text", "")
    if f == "space":
        return " "
    if f == "smartquote":
        return '"' if node.get("double", True) else "'"
    if f == "raw":
        return node.get("text", "")
    return "".join(plain(node[k]) for k in ("children", "body", "text") if k in node and not isinstance(node[k], str))


def markup(node) -> str:
    """A content tree from `typst query` as Typst markup that sets it again. Every piece starts with `#`, so no bare
    text can run into the expression before it."""
    if node is None:
        return ""
    if isinstance(node, str):
        return "#" + _str(node) if node else ""
    if isinstance(node, list):
        return "".join(markup(n) for n in node)
    f = node.get("func")
    if f == "sequence":
        return "".join(markup(c) for c in node.get("children", []))
    if f in ("text", "symbol"):
        return markup(node.get("text", ""))
    if f == "space":
        return '#" "'
    if f == "smartquote":
        return f"#smartquote(double: {'true' if node.get('double', True) else 'false'})"
    if f == "linebreak":
        return "#linebreak()"
    if f in ("emph", "strong", "super", "sub", "underline", "smallcaps"):
        return f"#{f}[{markup(node.get('body'))}]"
    if f == "link":
        dest = node.get("dest")
        if isinstance(dest, str):
            return f"#link({_str(dest)})[{markup(node.get('body'))}]"
        return markup(node.get("body"))
    if f == "raw":
        return f"#raw({_str(node.get('text', ''))})"
    if f in ("box", "styled", "context", "strike", "highlight", "h"):
        return markup(node.get("body") or node.get("child")) if (node.get("body") or node.get("child")) else ""
    return markup(plain(node))


def collect(book: Path | str, inputs: dict[str, str] | None = None) -> dict:
    """A section's notes, sources and sources' titles as written out in the "part" mode (`inputs` gain `notes:
    part`)."""
    book = Path(book).resolve()
    inputs = {**(inputs or {}), "notes": "part"}
    notes = _query(book, "<wwii-part-note>", book.parent, inputs)
    sources = [e for lst in _query(book, "<wwii-part-sources>", book.parent, inputs) for e in lst]
    titles = [e for lst in _query(book, "<wwii-part-titles>", book.parent, inputs) for e in lst]
    return {"notes": notes, "sources": sources, "titles": titles}


def _flat(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def strip_asides(node):
    """A content tree with its parenthesised asides left out (a bracket opened in one piece and closed in another
    too), and the spaces they leave before punctuation closed up: a title's derived short form."""
    depth = 0

    def walk(n):
        nonlocal depth
        if n is None:
            return None
        if isinstance(n, str):
            n = {"func": "text", "text": n}
        if isinstance(n, list):
            return [x for x in (walk(c) for c in n) if x is not None]
        f = n.get("func")
        if f in ("text", "symbol", "space"):
            out = []
            for ch in (" " if f == "space" else n.get("text", "")):
                if ch == "(":
                    depth += 1
                elif ch == ")" and depth:
                    depth -= 1
                elif not depth:
                    out.append(ch)
            return {"func": "text", "text": "".join(out)}
        if depth:
            return None
        if f == "sequence":
            return {**n, "children": [x for x in (walk(c) for c in n.get("children", [])) if x is not None]}
        if "body" in n and not isinstance(n["body"], str):
            return {**n, "body": walk(n["body"])}
        return n

    tree = walk(node)
    # merge the text pieces of each sequence, then close up the spaces the asides left
    def tidy(n):
        if isinstance(n, dict) and n.get("func") == "sequence":
            kids, merged = [tidy(c) for c in n["children"]], []
            for k in kids:
                if merged and k.get("func") == "text" and merged[-1].get("func") == "text":
                    merged[-1] = {"func": "text", "text": merged[-1]["text"] + k["text"]}
                else:
                    merged.append(k)
            for k in merged:
                if k.get("func") == "text":
                    k["text"] = re.sub(r" +", " ", re.sub(r"\s+(?=[,.;:])", "", k["text"]))
            return {**n, "children": merged}
        if isinstance(n, dict) and n.get("func") == "text":
            return {**n, "text": re.sub(r" +", " ", re.sub(r"\s+(?=[,.;:])", "", n["text"]))}
        if isinstance(n, dict) and isinstance(n.get("body"), dict):
            return {**n, "body": tidy(n["body"])}
        return n
    tree = tidy(tree)
    # across pieces too: a space ending one text piece before the punctuation that opens the next
    texts: list[dict] = []

    def gather(n):
        if isinstance(n, dict):
            if n.get("func") == "text":
                texts.append(n)
            for k in ("children", "body"):
                gather(n.get(k))
        elif isinstance(n, list):
            for c in n:
                gather(c)
    gather(tree)
    texts = [t for t in texts if t["text"]]
    for a, b in zip(texts, texts[1:]):
        if re.match(r"[,.;:]", b["text"]):
            a["text"] = a["text"].rstrip()
    return tree


def abbreviate(parts: list[list[dict]], titles: list[list[dict]] | None = None) -> list[list[dict]]:
    """The part's notes, a list for each of its book files in order (as `collect` gives them), with every repeated
    citation in its short form (see the module's note). `titles`: each file's sources' titles (`collect`'s), to know a
    note that is a source's title alone. The notes are copied; their `text` is replaced where shortened."""
    seen: set[str] = set()
    out = []
    for i, notes in enumerate(parts):
        known = [t for t in (titles[i] if titles else []) if _flat(plain(t.get("title")))]
        lst = []
        for v in notes:
            v = dict(v)
            whole = _flat(plain(v.get("text")))
            c = v.get("cited")
            if c:
                ident = c["key"] + "|" + _flat(plain(c.get("title")))
                if v.get("short") is not None and ident in seen:
                    v["text"] = v["short"] if c.get("declared") else strip_asides(v["short"])
                seen.add(ident)
            for t in known:                    # a source named in a note's words, or a note that is its title alone
                head = _flat(plain(t["title"]))
                ident = "title:" + t["key"] + "|" + head
                if not c and whole.rstrip(".") == head and ident in seen:
                    short = t.get("short") or strip_asides(t["title"])
                    v["text"] = {"func": "sequence", "children": [short, {"func": "text", "text": "."}]}
                if len(head) >= 20 and head in whole:
                    seen.add(ident)
            lst.append(v)
        out.append(lst)
    return out


def sections(parts: list[list[dict]]) -> list[dict]:
    """The part's notes, a list for each of its book files in order, grouped: a section is a run of notes from 1 (a
    file, or within a file wherever the numbering begins again), titled by its first chapter; under it its chapters
    in order, each with its notes as (number, text)."""
    out: list[dict] = []
    for notes in parts:
        cur = None
        for v in notes:
            ch = plain(v.get("chapter")).strip()
            if cur is None or v["n"] == 1 or v["n"] <= cur["last"]:
                cur = {"title": v.get("chapter"), "chapters": [], "last": 0}
                out.append(cur)
            if not cur["chapters"] or plain(cur["chapters"][-1]["title"]).strip() != ch:
                cur["chapters"].append({"title": v.get("chapter"), "notes": []})
            cur["chapters"][-1]["notes"].append((v["n"], v["text"]))
            cur["last"] = v["n"]
    for s in out:
        del s["last"]
    return out


def _page_key(p: str) -> tuple:
    m = re.search(r"\d+", p)
    return (int(m.group()) if m else 0, p)


def merge_sources(lists: list[list[dict]]) -> list[dict]:
    """One list of the part's sources, in the order first cited, each source's pages from every section joined."""
    merged: dict[str, dict] = {}
    for lst in lists:
        for e in lst:
            have = merged.setdefault(e["key"], {**e, "pages": []})
            have["pages"] += [p for p in e["pages"] if p not in have["pages"]]
    for e in merged.values():
        e["pages"].sort(key=_page_key)
    return list(merged.values())


def write(path: Path | str, sections_: list[dict], sources: list[dict] | None = None, name: str | None = None,
          part: str | None = None, heading: str = "Notes", columns: int = 3, preset: str = "blurb-magazine") -> Path:
    """The Typst file that sets a part's notes on pages of their own: `name` above the heading, `part` the versos'
    running head; `sources`, the part's sources listed after its notes (none: the book's sources are listed
    elsewhere, as a volume's back matter lists them)."""
    path = Path(path)
    L = ['// Generated by wwiibook.partnotes: a part\'s notes, gathered from its sections. Not edited by hand.',
         '#import "@local/wwii-book:0.1.0": *',
         f'#show: book.with(preset: {_str(preset)}{", name: " + _str(name) if name else ""})',
         f'#show: on-grid.with(preset: {_str(preset)}, notes: "part")']
    if part:
        L.append(f"#part-title[{markup(part)}]")
    L.append(f"#part-notes(heading: [{markup(heading)}], name: {('[' + markup(name) + ']') if name else 'none'}, "
             f"columns: {columns}, sections: (")
    for s in sections_:
        L.append(f"  (title: [{markup(s['title'])}], chapters: (")
        for c in s["chapters"]:
            L.append(f"    (title: [{markup(c['title'])}], notes: (")
            L += [f"      ({n}, [{markup(t)}])," for n, t in c["notes"]]
            L.append("    )),")
        L.append("  )),")
    L.append("), sources: (")
    for e in sources or []:
        pages = ", ".join(_str(p) for p in e["pages"])
        naid = _str(e["naid"]) if e.get("naid") else "none"
        L.append(f"  (key: {_str(e['key'])}, naid: {naid}, pages: ({pages}{',' if len(e['pages']) == 1 else ''}), "
                 f"head: [{markup(e['head'])}]),")
    L.append("))")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(L) + "\n")
    return path
