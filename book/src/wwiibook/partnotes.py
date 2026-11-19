"""A part's notes on pages of their own (`on-grid.with(notes: "part")`, `--input notes=part`).

A section built in this mode sets no notes: each note is written out as Typst metadata (`<wwii-part-note>`: its
number, its chapter's title and its whole text, its source line resolved against the section's own sources) and so
are the section's sources (`<wwii-part-sources>`). `collect` reads them back with `typst query`; `sections` groups a
part's notes by section (a run of notes numbered from 1: a book file, or a chapter that begins its numbering again)
and by chapter; `merge_sources` makes one list of the part's sources, each source's pages joined; `write` writes the
Typst file that sets them with `part-notes`, which the build then compiles like any other piece of the book.

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
    """A section's notes and sources as written out in the "part" mode (`inputs` gain `notes: part`)."""
    book = Path(book).resolve()
    inputs = {**(inputs or {}), "notes": "part"}
    notes = _query(book, "<wwii-part-note>", book.parent, inputs)
    sources = [e for lst in _query(book, "<wwii-part-sources>", book.parent, inputs) for e in lst]
    return {"notes": notes, "sources": sources}


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


def write(path: Path | str, sections_: list[dict], sources: list[dict], name: str | None = None,
          part: str | None = None, heading: str = "Notes", columns: int = 3, preset: str = "blurb-magazine") -> Path:
    """The Typst file that sets a part's notes on pages of their own: `name` above the heading, `part` the versos'
    running head."""
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
    for e in sources:
        pages = ", ".join(_str(p) for p in e["pages"])
        naid = _str(e["naid"]) if e.get("naid") else "none"
        L.append(f"  (key: {_str(e['key'])}, naid: {naid}, pages: ({pages}{',' if len(e['pages']) == 1 else ''}), "
                 f"head: [{markup(e['head'])}]),")
    L.append("))")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(L) + "\n")
    return path
