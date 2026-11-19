#!/usr/bin/env python3
"""Independent reader for the official NBA gamebook PDFs (session arena/eac340af-nba1).

WHY A SECOND READER
-------------------
The per-player game logs published on this site were parsed by
``scripts/e3d25abc_game_logs.py`` from the **stored official game pages**
(``https://www.nba.com/game/<away>-vs-<home>-<gameId>``).  The official
**gamebook PDF** of the same game is archived beside them
(``https://statsdmz.nba.com/pdfs/<YYYYMMDD>/<YYYYMMDD>_<AWAY><HOME>_book.pdf``),
content-addressed, with its SHA-256 recorded.

Reading the same published numbers out of a *different official artifact* is
what turns "published" into "verified": if the gamebook PDF and the game page
disagree about a player's minutes or points, that is a finding, not a
rounding difference.  This module is that second reader, and it is
deliberately written from the PDF primitives up rather than reusing the
injury-report reader in ``engine/injury_diff.py``:

* the gamebook PDFs are Chromium/Skia output with a **Type0 / Identity-H**
  subset font, so the text operators carry 2-byte *glyph ids*, not characters;
* each font carries a ``/ToUnicode`` CMap that maps those ids back to
  characters, and this reader applies the CMap of the font that is active at
  the moment a string is shown.

Nothing here invents a value: the reader only reports what the bytes contain,
and every extraction records the SHA-256 of the file it came from.
"""

from __future__ import annotations

import hashlib
import re
import zlib

OBJ_RE = re.compile(rb"(\d+)\s+0\s+obj(.*?)endobj", re.S)
STREAM_RE = re.compile(rb"stream\r?\n(.*?)endstream", re.S)


def _decompress(body: bytes) -> bytes:
    m = STREAM_RE.search(body)
    if not m:
        return b""
    data = m.group(1)
    if b"FlateDecode" in body.split(b"stream", 1)[0]:
        try:
            return zlib.decompress(data)
        except zlib.error:
            try:
                return zlib.decompressobj().decompress(data)
            except zlib.error:
                return b""
    return data


def parse_objects(raw: bytes) -> dict:
    """obj number -> (dict bytes, stream bytes)."""
    objs = {}
    for m in OBJ_RE.finditer(raw):
        num = int(m.group(1))
        body = m.group(2)
        head = body.split(b"stream", 1)[0]
        objs[num] = (head, _decompress(body))
    return objs


def parse_cmap(stream: bytes) -> dict:
    """Parse a ToUnicode CMap into {code(int): text(str)}."""
    text = stream.decode("latin-1", errors="replace")
    mapping: dict[int, str] = {}

    def _dst(tok: str) -> str:
        tok = tok.strip()
        if tok.startswith("<") and tok.endswith(">"):
            hexs = tok[1:-1]
        else:
            hexs = tok.strip("()")
        raw = bytes.fromhex(hexs)
        try:
            return raw.decode("utf-16-be")
        except UnicodeDecodeError:
            return raw.decode("latin-1", errors="replace")

    for blk in re.findall(r"beginbfchar(.*?)endbfchar", text, re.S):
        for src, dst in re.findall(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f\s]+)>", blk):
            mapping[int(src, 16)] = _dst(dst)
    for blk in re.findall(r"beginbfrange(.*?)endbfrange", text, re.S):
        for lo, hi, dst in re.findall(
            r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f\s]+)>", blk
        ):
            lo_i, hi_i = int(lo, 16), int(hi, 16)
            base = _dst(dst)
            if len(base) == 1 and hi_i - lo_i < 512:
                for k in range(lo_i, hi_i + 1):
                    mapping[k] = chr(ord(base) + (k - lo_i))
            else:
                mapping[lo_i] = base
    return mapping


def _font_maps(objs: dict) -> dict:
    """obj number of a font -> {code: text}."""
    out = {}
    for num, (head, _stream) in objs.items():
        if b"/Font" not in head:
            continue
        m = re.search(rb"/ToUnicode\s+(\d+)\s+0\s+R", head)
        if not m:
            continue
        cm = objs.get(int(m.group(1)))
        if not cm:
            continue
        out[num] = parse_cmap(cm[1])
    return out


def _page_fonts(objs: dict, page_head: bytes) -> dict:
    """resource name (/F1) -> font object number, for one page."""
    out = {}
    m = re.search(rb"/Font\s*<<(.*?)>>", page_head, re.S)
    if not m:
        # indirect resource dictionary
        rm = re.search(rb"/Resources\s+(\d+)\s+0\s+R", page_head)
        if rm:
            res = objs.get(int(rm.group(1)))
            if res:
                return _page_fonts(objs, res[0])
        return out
    for name, num in re.findall(rb"/([A-Za-z0-9_.]+)\s+(\d+)\s+0\s+R", m.group(1)):
        out[name.decode("latin-1")] = int(num)
    return out


TOKEN_RE = re.compile(
    rb"/([A-Za-z0-9_.]+)\s+[-0-9.]+\s+Tf|"
    rb"(-?[0-9.]+)\s+(-?[0-9.]+)\s+Td|"
    rb"(-?[0-9.]+)\s+(-?[0-9.]+)\s+(-?[0-9.]+)\s+(-?[0-9.]+)\s+(-?[0-9.]+)\s+(-?[0-9.]+)\s+Tm|"
    rb"<([0-9A-Fa-f\s]+)>\s*Tj|"
    rb"\((.*?)(?<!\\)\)\s*Tj",
    re.S,
)


def extract_lines(pdf_bytes: bytes) -> list:
    """Return a list of pages; each page is a list of lines; each line is
    [(x, text), ...] sorted left to right.

    A page is one content stream, in file order (the official gamebooks are
    one content stream per page).  Words are positioned by the Td/Tm chain
    inside each BT..ET block, which is enough to keep a table row together.
    """
    objs = parse_objects(pdf_bytes)
    fonts = _font_maps(objs)
    pages = []
    # page objects in document order
    page_nums = [
        num for num, (head, _s) in objs.items() if b"/Type" in head and b"/Page" in head
    ]
    page_nums.sort()
    for pnum in page_nums:
        head = objs[pnum][0]
        res_fonts = _page_fonts(objs, head)
        contents = []
        cm = re.search(rb"/Contents\s+(\d+)\s+0\s+R", head)
        if cm:
            contents = [int(cm.group(1))]
        else:
            cm = re.search(rb"/Contents\s*\[(.*?)\]", head, re.S)
            if cm:
                contents = [int(x) for x in re.findall(rb"(\d+)\s+0\s+R", cm.group(1))]
        words = []
        for cnum in contents:
            if cnum not in objs:
                continue
            text = objs[cnum][1].decode("latin-1", errors="replace")
            for block in re.findall(r"BT(.*?)ET", text, re.S):
                cur = None
                x = y = 0.0
                first = True
                for tok in TOKEN_RE.finditer(block.encode("latin-1", errors="replace")):
                    if tok.group(1) is not None:
                        cur = fonts.get(res_fonts.get(tok.group(1).decode("latin-1"), -1))
                        continue
                    if tok.group(2) is not None:
                        dx, dy = float(tok.group(2)), float(tok.group(3))
                        if first:
                            x, y = dx, dy
                            first = False
                        else:
                            x += dx
                            y += dy
                        continue
                    if tok.group(4) is not None:
                        x = float(tok.group(8))
                        y = float(tok.group(9))
                        first = False
                        continue
                    if tok.group(10) is not None:
                        hx = re.sub(rb"\s+", b"", tok.group(10))
                        try:
                            raw = bytes.fromhex(hx.decode("latin-1"))
                        except ValueError:
                            continue
                        s = _decode(raw, cur)
                        if s.strip():
                            words.append((x, y, s))
                        continue
                    if tok.group(11) is not None:
                        s = _pdf_unescape(tok.group(11).decode("latin-1"))
                        if s.strip():
                            words.append((x, y, s))
        pages.append(_group_lines(words))
    return pages


def _decode(raw: bytes, cmap: dict | None) -> str:
    if not cmap:
        return raw.decode("latin-1", errors="replace")
    out = []
    if len(raw) % 2 == 0 and raw[0] == 0:
        for i in range(0, len(raw), 2):
            code = (raw[i] << 8) | raw[i + 1]
            out.append(cmap.get(code, ""))
    else:
        for b in raw:
            out.append(cmap.get(b, chr(b)))
    return "".join(out)


def _pdf_unescape(s: str) -> str:
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            nxt = s[i + 1]
            if nxt in "nrtbf":
                out.append({"n": "\n", "r": "\r", "t": "\t", "b": "\b", "f": "\f"}[nxt])
                i += 2
                continue
            if nxt in "()\\":
                out.append(nxt)
                i += 2
                continue
            out.append(nxt)
            i += 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


def _group_lines(words, tol: float = 2.2):
    lines = []
    for x, y, w in sorted(words, key=lambda t: (t[1], t[0])):
        placed = False
        for line in lines:
            if abs(line[0] - y) <= tol:
                line[1].append((x, w))
                placed = True
                break
        if not placed:
            lines.append((y, [(x, w)]))
    out = []
    for _y, cells in sorted(lines, key=lambda l: l[0]):
        cells.sort()
        out.append([(x, w) for x, w in cells])
    return out


def read_pdf(path: str) -> dict:
    """Read one gamebook PDF and return its lines plus the file digest."""
    with open(path, "rb") as fh:
        raw = fh.read()
    pages = extract_lines(raw)
    return {
        "path": path,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
        "pages": pages,
    }


def page_text(page) -> str:
    return "\n".join(" ".join(w for _x, w in line) for line in page)


if __name__ == "__main__":  # small manual probe
    import json
    import sys

    doc = read_pdf(sys.argv[1])
    print(json.dumps({"sha256": doc["sha256"], "pages": len(doc["pages"])}, indent=1))
    for i, page in enumerate(doc["pages"][: int(sys.argv[2]) if len(sys.argv) > 2 else 2]):
        print(f"--- page {i + 1}")
        print(page_text(page)[:3000])
