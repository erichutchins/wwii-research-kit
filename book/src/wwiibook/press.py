"""The book's PDF made ready for the press, after Typst has written it.

Typst writes a page as its MediaBox alone, its black as RGB and its file as PDF 1.7. A print-on-demand press wants
more, and these steps add it without touching what is drawn (nothing is rasterised, no colour but black is changed):

- `boxes`: every page's TrimBox (the trimmed page) and BleedBox (the whole sheet). The bleed runs off the top, the
  bottom and the outside edge, so the trim sits against the binding edge: on the left of a recto (an odd page; page 1 is
  a recto) and the right of a verso.
- `black_to_k`: every RGB or ICC-based pure black (0 0 0), in text and in drawings, rewritten as CMYK 0/0/0/100, so
  text prints in black ink alone rather than in a black the press builds from four inks. Typst's own text and rules
  already arrive as CMYK black (core.typ's `ink`); this catches the figures, whose SVG has no way to say CMYK.
- `finish` is both, and the build runs it on every book.
- `pdfx`: a PDF/X-3:2002 copy for upload: PDF 1.3, the output intent, the markers, perceptual rendering, no links,
  outline, tags or XMP, and no transparency groups (refused while any live transparency is left).

`inspect` reads the same things back for preflight.
"""
from __future__ import annotations

import datetime
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import pikepdf
from pikepdf import Array, Dictionary, Name, Operator, Stream, String

BLEED = 9.0                         # points: Blurb's bleed at the top, bottom and outside edge
TRIMS = {(621.0, 810.0): (612.0, 792.0)}   # a sheet size (trim plus bleed) and its trim: core.typ's blurb-magazine
REGISTRY = "http://www.color.org"
CONDITION = "CGATS TR 001"          # Blurb's preset: U.S. Web Coated (SWOP) v2, the characterization CGATS TR 001
PROFILES = ("/usr/share/color/icc/ghostscript/default_cmyk.icc",   # Ghostscript's "Artifex CMYK SWOP Profile"
            "/usr/share/ghostscript/iccprofiles/default_cmyk.icc")
TEXT_SHOW = {"Tj", "TJ", "'", '"'}
PAINT = {"S", "s", "f", "F", "f*", "B", "B*", "b", "b*"}


def trim_box(media: tuple[float, float, float, float], recto: bool) -> tuple[float, float, float, float]:
    """The TrimBox for a page: inset by the bleed at the top, the bottom and the outside edge. A page whose size is not
    a known sheet (a draft) is its own trim."""
    x0, y0, x1, y1 = media
    trim = TRIMS.get((round(x1 - x0, 1), round(y1 - y0, 1)))
    if trim is None:
        return media
    dx, dy = (x1 - x0) - trim[0], ((y1 - y0) - trim[1]) / 2
    return (x0, y0 + dy, x1 - dx, y1 - dy) if recto else (x0 + dx, y0 + dy, x1, y1 - dy)


def _media(page: pikepdf.Page) -> tuple[float, float, float, float]:
    x0, y0, x1, y1 = (float(v) for v in page.obj.MediaBox)
    return min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)


def boxes(pdf: pikepdf.Pdf) -> None:
    for i, page in enumerate(pdf.pages):
        media = _media(page)
        page.obj.TrimBox = Array(trim_box(media, recto=i % 2 == 0))
        page.obj.BleedBox = Array(media)


# --- colour in content streams -------------------------------------------------------------------------------------

def _space(name, resources) -> str:
    """A colour space operand reduced to a kind: rgb, gray, cmyk, icc3, icc1, icc4, pattern, separation, other."""
    if isinstance(name, Name):
        s = str(name)
        if s in ("/DeviceRGB", "/RGB"):
            return "rgb"
        if s in ("/DeviceGray", "/G"):
            return "gray"
        if s in ("/DeviceCMYK", "/CMYK"):
            return "cmyk"
        if s == "/Pattern":
            return "pattern"
        cs = resources.get("/ColorSpace", {}) if resources is not None else {}
        if s in cs:
            return _space(cs[s], None)
        return "other"
    if isinstance(name, Array) and len(name):
        head = str(name[0])
        if head == "/ICCBased":
            return f"icc{int(name[1].get('/N', 3))}"
        if head in ("/Separation", "/DeviceN"):
            return "separation"
        if head == "/Pattern":
            return "pattern"
        if head == "/CalRGB":
            return "icc3"
        if head == "/CalGray":
            return "icc1"
        if head == "/Indexed":
            return "indexed"
        if head == "/Lab":
            return "lab"
    return "other"


def _is_black(kind: str, nums: list[float]) -> bool:
    return (kind in ("rgb", "icc3") and len(nums) == 3 and all(abs(v) < 1e-6 for v in nums)) or \
        (kind == "icc1" and len(nums) == 1 and abs(nums[0]) < 1e-6)


def _nums(operands) -> list[float] | None:
    try:
        return [float(v) for v in operands]
    except (TypeError, ValueError):
        return None          # a pattern name among them


@dataclass
class _Colour:
    fill: str = "gray"            # the colour space the stream believes is current
    stroke: str = "gray"
    fill_name: object = None      # its operand, to set it again after a rewrite
    stroke_name: object = None
    fill_k: bool = False          # a rewrite left DeviceCMYK current where the stream believes `fill`
    stroke_k: bool = False
    fill_value: str = "gray0"     # what the current colour is, for the census: rgb-black, k-black, rich-black, gray0, ...
    stroke_value: str = "gray0"

    def copy(self) -> _Colour:
        return _Colour(**self.__dict__)


def _value(kind: str, nums: list[float] | None) -> str:
    if nums is None:
        return "pattern"
    if _is_black(kind, nums):
        return "rgb-black"
    if kind == "cmyk" and len(nums) == 4:
        c, m, y, k = nums
        if k >= 0.999 and max(c, m, y) < 1e-6:
            return "k-black"
        if k >= 0.999:
            return "rich-black"
        return "cmyk"
    if kind == "gray" and len(nums) == 1:
        return "gray0" if nums[0] < 1e-6 else "gray"
    if kind == "separation":
        return "spot"
    return kind


def _rewrite(instructions, resources, census: Counter | None = None, convert: bool = True) -> tuple[list, int]:
    """Walk one content stream: count what colour each text run and each painted path is in (census), and rewrite
    pure RGB or ICC black as CMYK 0/0/0/100 (convert). Returns the instructions and how many colours changed."""
    out, st, stack, changed = [], _Colour(), [], 0
    for ins in instructions:
        if isinstance(ins, pikepdf.ContentStreamInlineImage):
            out.append(ins)
            continue
        ops, op = list(ins.operands), str(ins.operator)
        if op == "q":
            stack.append(st.copy())
        elif op == "Q" and stack:
            st = stack.pop()
        elif op in ("cs", "CS"):
            kind = _space(ops[0], resources) if ops else "other"
            if op == "cs":
                st.fill, st.fill_name, st.fill_k = kind, ops[0], False
                st.fill_value = "gray0" if kind == "gray" else ("k-black" if kind == "cmyk" else kind + "-initial")
            else:
                st.stroke, st.stroke_name, st.stroke_k = kind, ops[0], False
                st.stroke_value = "gray0" if kind == "gray" else ("k-black" if kind == "cmyk" else kind + "-initial")
        elif op in ("sc", "scn", "SC", "SCN"):
            fill = op in ("sc", "scn")
            kind = st.fill if fill else st.stroke
            nums = _nums(ops)
            if convert and nums is not None and _is_black(kind, nums):
                out.append(pikepdf.ContentStreamInstruction([0, 0, 0, 1], Operator("k" if fill else "K")))
                changed += 1
                if fill:
                    st.fill_k, st.fill_value = True, "k-black"
                else:
                    st.stroke_k, st.stroke_value = True, "k-black"
                continue
            if (st.fill_k if fill else st.stroke_k):     # the stream's own space again, before its colour
                name = st.fill_name if fill else st.stroke_name
                out.append(pikepdf.ContentStreamInstruction([name], Operator("cs" if fill else "CS")))
                if fill:
                    st.fill_k = False
                else:
                    st.stroke_k = False
            if fill:
                st.fill_value = _value(kind, nums)
            else:
                st.stroke_value = _value(kind, nums)
        elif op in ("rg", "RG"):
            fill = op == "rg"
            nums = _nums(ops)
            if convert and nums is not None and _is_black("rgb", nums):
                out.append(pikepdf.ContentStreamInstruction([0, 0, 0, 1], Operator("k" if fill else "K")))
                changed += 1
                kind, v = "cmyk", "k-black"
            else:
                kind, v = "rgb", _value("rgb", nums)
            if fill:
                st.fill, st.fill_k, st.fill_value = kind, False, v
            else:
                st.stroke, st.stroke_k, st.stroke_value = kind, False, v
            if kind == "cmyk":
                continue
        elif op in ("g", "G", "k", "K"):
            fill = op in ("g", "k")
            kind = "gray" if op in ("g", "G") else "cmyk"
            v = _value(kind, _nums(ops))
            if fill:
                st.fill, st.fill_k, st.fill_value = kind, False, v
            else:
                st.stroke, st.stroke_k, st.stroke_value = kind, False, v
        elif census is not None and op in TEXT_SHOW:
            census["text " + st.fill_value] += 1
        elif census is not None and op in PAINT:
            if op in ("S", "s", "B", "B*", "b", "b*"):
                census["stroke " + st.stroke_value] += 1
            if op not in ("S", "s"):
                census["fill " + st.fill_value] += 1
        out.append(ins)
    return out, changed


def _streams(pdf: pikepdf.Pdf) -> Iterator[tuple[object, object, bool]]:
    """Every content stream once: (owner, resources, is_page). Pages, then the form XObjects and tiling patterns they
    use, at any depth (a form without resources uses its caller's)."""
    seen: set[tuple[int, int]] = set()
    todo: list[tuple[object, object, bool]] = []
    for page in pdf.pages:
        todo.append((page, page.obj.get("/Resources"), True))
    while todo:
        owner, res, is_page = todo.pop(0)
        if not is_page:
            key = owner.objgen  # type: ignore[attr-defined]
            if key in seen or key == (0, 0):
                continue
            seen.add(key)
        yield owner, res, is_page
        if res is None:
            continue
        for kind in ("/XObject", "/Pattern"):
            for _, x in (res.get(kind) or {}).items():
                if isinstance(x, Stream) and (x.get("/Subtype") == "/Form" or x.get("/PatternType") == 1):
                    todo.append((x, x.get("/Resources", res), False))


def _parse(owner, is_page: bool):
    return pikepdf.parse_content_stream(owner.obj if is_page else owner)


def black_to_k(pdf: pikepdf.Pdf) -> int:
    total = 0
    for owner, res, is_page in _streams(pdf):
        instructions, changed = _rewrite(_parse(owner, is_page), res)
        if changed:
            data = pikepdf.unparse_content_stream(instructions)
            if is_page:
                owner.obj.Contents = pdf.make_stream(data)  # type: ignore[attr-defined]
            else:
                owner.write(data)  # type: ignore[attr-defined]
            total += changed
    return total


def finish(path: Path | str) -> int:
    """The build's last step: page boxes and black ink, in place. Returns how many black colours were rewritten."""
    path = Path(path)
    with pikepdf.open(path, allow_overwriting_input=True) as pdf:
        boxes(pdf)
        n = black_to_k(pdf)
        pdf.save(path)
    return n


# --- reading it back -----------------------------------------------------------------------------------------------

@dataclass
class Inspection:
    version: str = ""
    trim: list[str] = field(default_factory=list)          # pages whose boxes are missing or wrong
    soft_masks: int = 0                                    # images with an SMask
    alpha_states: int = 0                                  # graphics states with CA or ca below 1, or an SMask
    blend_states: int = 0                                  # graphics states with a blend mode other than Normal
    groups: int = 0                                        # transparency groups (pages and forms)
    spot: int = 0                                          # Separation and DeviceN colour spaces
    colour: Counter = field(default_factory=Counter)       # "text rgb-black": n, "fill k-black": n, ...
    pdfx: dict = field(default_factory=dict)               # the PDF/X markers found
    links: int = 0
    outline: bool = False

    @property
    def transparency(self) -> int:
        return self.soft_masks + self.alpha_states + self.blend_states


def _alpha(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 1.0


def inspect(path: Path | str) -> Inspection:
    r = Inspection()
    with pikepdf.open(path) as pdf:
        r.version = pdf.pdf_version
        for i, page in enumerate(pdf.pages):
            media = _media(page)
            want = trim_box(media, recto=i % 2 == 0)
            tb, bb = page.obj.get("/TrimBox"), page.obj.get("/BleedBox")
            if tb is None:
                r.trim.append(f"page {i + 1}: no TrimBox")
            elif any(abs(float(a) - b) > 0.5 for a, b in zip(tb, want)):
                r.trim.append(f"page {i + 1}: TrimBox {[round(float(v), 1) for v in tb]}, not {list(want)}")
            if bb is None:
                r.trim.append(f"page {i + 1}: no BleedBox")
            elif any(abs(float(a) - b) > 0.5 for a, b in zip(bb, media)):
                r.trim.append(f"page {i + 1}: BleedBox is not the MediaBox")
            r.links += sum(1 for a in page.obj.get("/Annots", []) if a.get("/Subtype") == "/Link")
        for obj in pdf.objects:
            if not isinstance(obj, (Dictionary, Stream)):
                continue
            if obj.get("/Subtype") == "/Image" and isinstance(obj.get("/SMask"), Stream):
                r.soft_masks += 1
            if obj.get("/Type") == "/ExtGState" or ("/ca" in obj or "/CA" in obj):
                if _alpha(obj.get("/CA", 1)) < 1 or _alpha(obj.get("/ca", 1)) < 1 or \
                        isinstance(obj.get("/SMask"), Dictionary):
                    r.alpha_states += 1
                bm = obj.get("/BM")
                if bm is not None and str(bm if not isinstance(bm, Array) else bm[0]) not in ("/Normal", "/Compatible"):
                    r.blend_states += 1
            g = obj.get("/Group")
            if isinstance(g, Dictionary) and g.get("/S") == "/Transparency":
                r.groups += 1
            for _, cs in (obj.get("/ColorSpace") or {}).items() if isinstance(obj.get("/ColorSpace"), Dictionary) else ():
                if _space(cs, None) == "separation":
                    r.spot += 1
        for owner, res, is_page in _streams(pdf):
            _rewrite(_parse(owner, is_page), res, census=r.colour, convert=False)
        info = pdf.trailer.get("/Info") or {}
        r.pdfx = {k: str(info[k]) for k in ("/GTS_PDFXVersion", "/Trapped", "/Title") if k in info}
        r.outline = "/Outlines" in pdf.Root
        intents = pdf.Root.get("/OutputIntents") or []
        for oi in intents:
            if oi.get("/S") == "/GTS_PDFX":
                r.pdfx["intent"] = str(oi.get("/OutputConditionIdentifier", ""))
                r.pdfx["registry"] = str(oi.get("/RegistryName", ""))
                prof = oi.get("/DestOutputProfile")
                r.pdfx["profile"] = f"{int(prof.get('/N', 0))} channels" if isinstance(prof, Stream) else "none"
    return r


# --- PDF/X-3 ---------------------------------------------------------------------------------------------------------

def profile_description(data: bytes) -> str:
    """An ICC profile's description tag (v2 'desc' or v4 'mluc'), for the output intent's name."""
    n = int.from_bytes(data[128:132], "big")
    for k in range(n):
        sig, off, size = data[132 + 12 * k:136 + 12 * k], *(int.from_bytes(data[136 + 12 * k + j:140 + 12 * k + j], "big")
                                                             for j in (0, 4))
        if sig != b"desc":
            continue
        tag = data[off:off + size]
        if tag[:4] == b"desc":
            length = int.from_bytes(tag[8:12], "big")
            return tag[12:12 + length].rstrip(b"\0").decode("latin-1")
        if tag[:4] == b"mluc":
            rec_len, o = int.from_bytes(tag[16:20], "big"), int.from_bytes(tag[24:28], "big")
            return tag[o:o + rec_len].decode("utf-16-be")
    return "CMYK output profile"


def find_profile(given: Path | str | None = None) -> Path:
    """The output profile: the one given, else a CMYK SWOP profile known on this machine (Ghostscript's)."""
    import os
    for p in (given, os.environ.get("WWII_OUTPUT_PROFILE"), *PROFILES):
        if p and Path(p).is_file():
            return Path(p)
    raise FileNotFoundError("no CMYK output profile: pass --profile <file.icc> (U.S. Web Coated (SWOP) v2, from "
                            "Adobe's ICC profiles, or Ghostscript's default_cmyk.icc: apt-get install ghostscript)")


def pdfx(src: Path | str, out: Path | str, profile: Path | str | None = None, title: str | None = None) -> dict:
    """Write a PDF/X-3:2002 copy of a finished book. Refuses a book that still has live transparency."""
    src, out = Path(src), Path(out)
    prof = find_profile(profile)
    data = prof.read_bytes()
    if data[16:20] != b"CMYK" or data[12:16] != b"prtr":
        raise ValueError(f"{prof}: not a CMYK output profile")
    desc = profile_description(data)
    with pikepdf.open(src) as pdf:
        boxes(pdf)
        black = black_to_k(pdf)
        left = Inspection()
        for obj in pdf.objects:
            if isinstance(obj, (Dictionary, Stream)):
                if obj.get("/Subtype") == "/Image" and isinstance(obj.get("/SMask"), Stream):
                    left.soft_masks += 1
                if _alpha(obj.get("/CA", 1)) < 1 or _alpha(obj.get("/ca", 1)) < 1:
                    left.alpha_states += 1
        if left.transparency:
            raise ValueError(f"{src}: {left.soft_masks} soft-masked images and {left.alpha_states} translucent "
                             "graphics states: make them solid at the source (wwiibook.solid) before the press pass")
        groups = 0
        for obj in pdf.objects:
            if isinstance(obj, (Dictionary, Stream)) and "/Group" in obj:
                del obj["/Group"]          # with nothing translucent inside, a group draws exactly as without one
                groups += 1
            if isinstance(obj, Stream) and obj.get("/Subtype") == "/Image":
                obj.Intent = Name.Perceptual
        links = 0
        for page in pdf.pages:
            links += len(page.obj.get("/Annots", []))
            if "/Annots" in page.obj:
                del page.obj["/Annots"]
            page.contents_add(pdf.make_stream(b"/Perceptual ri\n"), prepend=True)
        for k in ("/Outlines", "/PageMode", "/Names", "/Dests", "/OpenAction", "/StructTreeRoot", "/MarkInfo",
                  "/Metadata", "/Lang", "/AcroForm"):
            if k in pdf.Root:
                del pdf.Root[k]
        icc = pdf.make_stream(data)
        icc.N = 4
        pdf.Root.OutputIntents = Array([Dictionary(
            Type=Name.OutputIntent, S=Name.GTS_PDFX, OutputConditionIdentifier=String(CONDITION),
            RegistryName=String(REGISTRY), OutputCondition=String(desc), Info=String(desc), DestOutputProfile=icc)])
        now = datetime.datetime.now(datetime.UTC).strftime("D:%Y%m%d%H%M%SZ")
        old = pdf.trailer.get("/Info") or Dictionary()
        name = title or str(old.get("/Title", "")) or src.stem
        info = Dictionary(Title=String(name), Creator=String(str(old.get("/Creator", "Typst"))),
                          Producer=String("wwii-book press (pikepdf)"), CreationDate=String(str(old.get("/CreationDate", now))),
                          ModDate=String(now), Trapped=Name("/False"), GTS_PDFXVersion=String("PDF/X-3:2002"))
        pdf.trailer.Info = pdf.make_indirect(info)
        pdf.remove_unreferenced_resources()
        pdf.save(out, force_version="1.3", object_stream_mode=pikepdf.ObjectStreamMode.disable,
                 compress_streams=True, fix_metadata_version=False)
    return {"pdf": str(out), "profile": str(prof), "condition": desc, "black": black, "groups": groups, "links": links}
