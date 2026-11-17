"""The two-pass build, offline: the scan comes from a stub, the records from a temporary folder."""
import json
from pathlib import Path

import pymupdf
import pytest
from PIL import Image
from wwiibook import build, nara

BOOK = """#import "@local/wwii-book:0.1.0": *
#let wwii = init(assets: json("build/assets.json"), load: p => read(p, encoding: none))
#show: book
= Test
#(wwii.facsimile)("rg64-1/p7", crop: (0, 0, 1, 0.5), caption: [A stub page])
#(wwii.records)("boats/ss-1-test/patrol-1/attacks.csv", torpedo-ledger)
#(wwii.qr-tag)("https://example.org/engagement", dtg: "292256K APR 44")
"""

ATTACKS = """attack,date,time,zone,tube,gyro,depth_set,torpedo,hit
Attack 1,1944-04-29,2256,K,1,013,6,23,Miss
Attack 1,1944-04-29,2256,K,2,013,6,23,Hit
"""


@pytest.fixture
def book(tmp_path, monkeypatch):
    records = tmp_path / "records" / "boats" / "ss-1-test" / "patrol-1"
    records.mkdir(parents=True)
    (records / "attacks.csv").write_text(ATTACKS)
    monkeypatch.setenv("WWII_RECORDS", str(tmp_path / "records"))
    scan = tmp_path / "scan.png"
    Image.new("L", (1800, 2400), 255).save(scan)
    calls = []

    def page_image(cite):
        calls.append(cite.text)
        return scan

    monkeypatch.setattr(nara, "page_image", page_image)
    folder = tmp_path / "book"
    folder.mkdir()
    (folder / "book.typ").write_text(BOOK)
    return folder / "book.typ", calls


def text(pdf: Path) -> str:
    return "".join(p.get_text() for p in pymupdf.open(pdf))


def test_two_passes_fill_every_request(book):
    path, calls = book
    r = build(path)
    assert sorted(r.prepared) == sorted(["rg64-1/p7@0,0,1,0.5", "records:boats/ss-1-test/patrol-1/attacks.csv",
                                         "qr:https://example.org/engagement"])
    assert not r.failed
    out = text(r.pdf)
    assert "pending" not in out
    assert "National Archives, RG 64, NAID 1, p. 7" in out      # the facsimile's credit line
    assert "Attack 1" in out and "Hit" in out                    # the ledger, from the records
    assert "292256K APR 44" in out
    assert calls == ["rg64-1/p7"]


def test_second_build_reuses(book):
    path, calls = book
    build(path)
    r = build(path)
    assert r.prepared == [] and len(r.reused) == 3
    assert calls == ["rg64-1/p7"]                                # fetched once


def test_a_failed_request_leaves_its_placeholder(book, monkeypatch):
    path, _ = book

    def broken(cite):
        raise LookupError("no such page")

    monkeypatch.setattr(nara, "page_image", broken)
    r = build(path)
    assert [k for k, _ in r.failed] == ["rg64-1/p7@0,0,1,0.5"]
    assert "pending" in text(r.pdf)                              # the rest of the book still built
    assets = json.loads((path.parent / "build" / "assets.json").read_text())
    assert "rg64-1/p7@0,0,1,0.5" not in assets


def test_low_resolution_is_reported(book):
    path, _ = book
    path.write_text(path.read_text().replace('caption: [A stub page]', 'caption: [A stub page], width: 9in'))
    r = build(path)
    assert any("dpi" in w["message"] for w in r.warnings)


def test_a_missing_asset_file_is_prepared_again(book):
    path, _ = book
    build(path)
    for f in (path.parent / "build").glob("*.svg"):
        f.unlink()
    r = build(path)
    assert r.prepared == ["qr:https://example.org/engagement"] and not r.failed
