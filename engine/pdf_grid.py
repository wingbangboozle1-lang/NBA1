"""pdf_grid.py - read a table out of an official NBA PDF, from the bytes.

Why this module exists
----------------------
The official **gamebook** PDFs (the league's own box-score documents at
``statsdmz.nba.com``) are not plain-text PDFs.  Their body text is drawn with
Type0/CID fonts under an ``Identity-H`` encoding, so every glyph is a raw
code that only means something once the font's ``ToUnicode`` CMap has been
applied.  They also position their text with ``Tm``/``Td`` inside nested
``cm`` transforms, and they draw their table as a grid of filled rectangles.

Three things therefore have to be recovered before a cell can be read:

1. the **text**, by decoding each drawn string with the ``ToUnicode`` CMap of
   the font that is active at that point in the content stream;
2. the **position** of every run, by tracking the graphics-state stack
   (``q``/``Q``) and the ``cm`` transforms, so text and rectangles end up in
   one common space;
3. the **grid** itself, because the gamebook draws the column separators and
   the row rules as filled rectangles rather than as lines.

With those three, every glyph can be placed in the cell the document itself
declares, and a cell that the document leaves empty stays empty - it is never
filled in from a guess or from a second-hand text render.

What it returns
---------------
For each page, a list of tables; each table is a list of rows; each row is a
list of cell strings (plus the row's y coordinate).  The cell order is the
left-to-right order of the table's own column bands, which is the order the
gamebook prints.

Standard library only - the scheduled refresh runner installs nothing.
"""

from __future__ import annotations

import re
import zlib

# --------------------------------------------------------------------- objects

OBJ_RE = re.compile(rb"(?<![0-9])(\d+)\s+(\d+)\s+obj\b(.*?)\bendobj", re.S)


def parse_objects(raw):
    """{object number: {'dict': bytes, 'stream': bytes|None}}."""
    objs = {}
    for m in OBJ_RE.finditer(raw):
        num = int(m.group(1))
        body = m.group(3)
        si = body.find(b"stream")
        stream = None
        if si >= 0:
            head = body[:si]
            data = body[si + 6:]
            data = data.lstrip(b"\r\n")
            ei = data.rfind(b"endstream")
            if ei >= 0:
                data = data[:ei]
            if b"/FlateDecode" in head:
                try:
                    data = zlib.decompress(data)
                except zlib.error:
                    data = b""
            stream = data
            body = head
        objs[num] = {"dict": body, "stream": stream}
    return objs


def resolve(objs, token):
    """Resolve a /Name N 0 R style token to an object number, or None."""
    m = re.match(rb"\s*(\d+)\s+(\d+)\s+R", token)
    if m:
        return int(m.group(1))
    return None


def get_ref(body, key):
    """The object number a /key N 0 R entry points at, or None."""
    m = re.search(rb"/" + key.encode() + rb"\s+(\d+)\s+\d+\s+R", body)
    return int(m.group(1)) if m else None


# ------------------------------------------------------------------- ToUnicode

BFCHAR_RE = re.compile(rb"beginbfchar(.*?)endbfchar", re.S)
BFRANGE_RE = re.compile(rb"beginbfrange(.*?)endbfrange", re.S)
HEX_RE = re.compile(rb"<([0-9A-Fa-f]*)>")


def _utf16be(hexstr):
    raw = bytes.fromhex(hexstr.decode("ascii"))
    if len(raw) % 2:
        raw += b"\x00"
    try:
        return raw.decode("utf-16-be")
    except UnicodeDecodeError:
        return raw.decode("latin-1", "replace")


def parse_cmap(stream):
    """A ToUnicode CMap -> {code: text}."""
    out = {}
    if not stream:
        return out
    for block in BFCHAR_RE.finditer(stream):
        pairs = HEX_RE.findall(block.group(1))
        for i in range(0, len(pairs) - 1, 2):
            out[int(pairs[i], 16)] = _utf16be(pairs[i + 1])
    for block in BFRANGE_RE.finditer(stream):
        body = block.group(1)
        # a range can be <lo> <hi> <dst> or <lo> <hi> [ <d1> <d2> ... ]
        for m in re.finditer(rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*(\[(?:[^\]]*)\]|<[0-9A-Fa-f]*>)",
                             body, re.S):
            lo = int(m.group(1), 16)
            hi = int(m.group(2), 16)
            dst = m.group(3)
            if dst.startswith(b"["):
                items = HEX_RE.findall(dst)
                for i, item in enumerate(items):
                    if lo + i <= hi:
                        out[lo + i] = _utf16be(item)
            else:
                base = HEX_RE.findall(dst)
                if not base:
                    continue
                start = int(base[0], 16)
                width = len(base[0]) // 4
                for i in range(hi - lo + 1):
                    code = start + i
                    out[lo + i] = chr(code) if width <= 1 else _utf16be(
                        ("%0*X" % (len(base[0]), code)).encode("ascii").decode())
    return out


def build_fonts(objs):
    """{font object number: {'cmap': {...}, 'bytes': 1|2, 'type': str}}."""
    fonts = {}
    for num, obj in objs.items():
        body = obj["dict"]
        if b"/Type /Font" not in body and b"/Type/Font" not in body:
            continue
        tu = get_ref(body, "ToUnicode")
        cmap = parse_cmap(objs[tu]["stream"]) if tu in objs else {}
        subtype = "simple"
        if b"/Type0" in body:
            subtype = "type0"
        elif b"/Type3" in body:
            subtype = "type3"
        fonts[num] = {"cmap": cmap, "bytes": 2 if subtype == "type0" else 1,
                      "type": subtype}
    return fonts


# ------------------------------------------------------------------- matrices

def mat_mul(a, b):
    """Matrix a (applied first) then b."""
    return (a[0] * b[0] + a[1] * b[2],
            a[0] * b[1] + a[1] * b[3],
            a[2] * b[0] + a[3] * b[2],
            a[2] * b[1] + a[3] * b[3],
            a[4] * b[0] + a[5] * b[2] + b[4],
            a[4] * b[1] + a[5] * b[3] + b[5])


def apply(m, x, y):
    return (m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5])


IDENTITY = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


# -------------------------------------------------------------------- scanner

TOKEN_RE = re.compile(rb"""
    (?P<hex><[0-9A-Fa-f\s]*>)
  | (?P<str>\((?:[^()\\]|\\.|\((?:[^()\\]|\\.)*\))*\))
  | (?P<arr>\[)
  | (?P<arrend>\])
  | (?P<name>/[^\s/\[\]<>(){}]+)
  | (?P<num>[-+]?(?:\d+\.?\d*|\.\d+))
  | (?P<op>[A-Za-z'"*]+)
""", re.X | re.S)


def tokenize(stream):
    """Yield (kind, value) tokens."""
    for m in TOKEN_RE.finditer(stream):
        kind = m.lastgroup
        yield kind, m.group(kind)


def decode_literal(raw):
    """PDF literal string -> bytes."""
    out = bytearray()
    i = 0
    while i < len(raw):
        c = raw[i]
        if c == 0x5C and i + 1 < len(raw):
            nxt = raw[i + 1]
            mapping = {0x6E: 10, 0x72: 13, 0x74: 9, 0x62: 8, 0x66: 12}
            if nxt in mapping:
                out.append(mapping[nxt])
                i += 2
                continue
            if 0x30 <= nxt <= 0x37:
                j = i + 1
                oct_digits = ""
                while j < len(raw) and len(oct_digits) < 3 and 0x30 <= raw[j] <= 0x37:
                    oct_digits += chr(raw[j])
                    j += 1
                out.append(int(oct_digits, 8) & 0xFF)
                i = j
                continue
            out.append(nxt)
            i += 2
            continue
        out.append(c)
        i += 1
    return bytes(out)


def decode_with_cmap(data, font):
    """Raw codes -> text, using the font's ToUnicode CMap."""
    cmap = font["cmap"] if font else {}
    width = font["bytes"] if font else 1
    out = []
    if width == 2:
        for i in range(0, len(data) - 1, 2):
            code = (data[i] << 8) | data[i + 1]
            out.append(cmap.get(code, ""))
    else:
        for byte in data:
            out.append(cmap.get(byte, chr(byte) if 32 <= byte < 127 else ""))
    return "".join(out)


# ----------------------------------------------------------------- page walk

def page_objects(objs):
    """The page objects in document order."""
    pages = []
    for num, obj in objs.items():
        if b"/Type /Page" in obj["dict"] and b"/Type /Pages" not in obj["dict"]:
            pages.append(num)
    # document order is not guaranteed by object number; follow /Kids when the
    # page tree is reachable, otherwise fall back to the object order.
    kids_order = []
    for num, obj in objs.items():
        if b"/Type /Pages" in obj["dict"] or b"/Type/Pages" in obj["dict"]:
            km = re.search(rb"/Kids\s*\[(.*?)\]", obj["dict"], re.S)
            if km:
                for m in re.finditer(rb"(\d+)\s+\d+\s+R", km.group(1)):
                    kid = int(m.group(1))
                    if kid in objs and b"/Type /Page" in objs[kid]["dict"]:
                        kids_order.append(kid)
    if len(kids_order) == len(pages):
        return kids_order
    return sorted(pages)


def page_fonts(objs, page_num):
    """{font resource name: font object number} for one page."""
    body = objs[page_num]["dict"]
    res = body
    rm = re.search(rb"/Resources\s+(\d+)\s+\d+\s+R", body)
    if rm:
        res = objs[int(rm.group(1))]["dict"]
    fm = re.search(rb"/Font\s*<<(.*?)>>", res, re.S)
    if not fm:
        fr = re.search(rb"/Font\s+(\d+)\s+\d+\s+R", res)
        if not fr:
            return {}
        fm = re.search(rb"<<(.*?)>>", objs[int(fr.group(1))]["dict"], re.S)
        if not fm:
            return {}
    out = {}
    for m in re.finditer(rb"/([^\s/]+)\s+(\d+)\s+\d+\s+R", fm.group(1)):
        out[m.group(1).decode("latin-1")] = int(m.group(2))
    return out


def page_font_resources(objs, page_num):
    """{resource name: font object number} for one page."""
    body = objs[page_num]["dict"]
    res = body
    rm = re.search(rb"/Resources\s+(\d+)\s+\d+\s+R", body)
    if rm and int(rm.group(1)) in objs:
        res = objs[int(rm.group(1))]["dict"]
    fm = re.search(rb"/Font\s*<<(.*?)>>", res, re.S)
    if not fm:
        fr = re.search(rb"/Font\s+(\d+)\s+\d+\s+R", res)
        if not fr or int(fr.group(1)) not in objs:
            return {}
        fm = re.search(rb"<<(.*?)>>", objs[int(fr.group(1))]["dict"], re.S)
        if not fm:
            return {}
    out = {}
    for m in re.finditer(rb"/([^\s/]+)\s+(\d+)\s+\d+\s+R", fm.group(1)):
        out[m.group(1).decode("latin-1")] = int(m.group(2))
    return out


def page_streams(objs, page_num):
    """The content streams of one page, in order."""
    body = objs[page_num]["dict"]
    cm = re.search(rb"/Contents\s+(\d+)\s+\d+\s+R", body)
    if cm:
        num = int(cm.group(1))
        st = objs.get(num, {}).get("stream")
        return [st] if st else []
    cm = re.search(rb"/Contents\s*\[(.*?)\]", body, re.S)
    if cm:
        out = []
        for m in re.finditer(rb"(\d+)\s+\d+\s+R", cm.group(1)):
            st = objs.get(int(m.group(1)), {}).get("stream")
            if st:
                out.append(st)
        return out
    return []


# ------------------------------------------------------------------ extraction

def _segment(fragments):
    """One logical string: its fragments joined in x order.

    A PDF draws a string as many positioned fragments; the logical string is
    what the reader sees.  Keeping it whole matters: a long note printed in a
    narrow column ("DNP - Coach's Decision") overflows the column it starts
    in, and splitting it at the column edges would corrupt every column to
    its right.
    """
    frs = sorted(fragments, key=lambda f: f["x"])
    text = "".join(f["text"] for f in frs)
    return {"x": frs[0]["x"], "y": frs[0]["y"], "text": text,
            "x_end": frs[-1]["x"], "n": len(frs)}


def extract_page(objs, fonts, page_num):
    """Return {'runs': [...], 'tables': [...]} for one page.

    A run is {'x','y','text'} in device space.  A table is
    {'x_edges': [...], 'y_edges': [...], 'cells': {row_index: {col_index: text}}}
    """
    ctm = IDENTITY
    stack = []
    tm = IDENTITY
    tlm = IDENTITY
    font_res = page_font_resources(objs, page_num)
    cur_font = None
    cur_size = 0.0
    runs = []
    seg = []          # the fragments of the logical string being assembled
    rects = []          # (x, y, w, h) in device space
    clips = []          # (x, y, w, h) clip rectangles in device space
    operands = []
    in_array = False
    arr_items = []

    for kind, value in tokenize(b"\n".join(page_streams(objs, page_num))):
        if kind == "num":
            operands.append(float(value))
            continue
        if kind == "name":
            operands.append(("name", value[1:].decode("latin-1")))
            continue
        if kind == "str":
            operands.append(("str", decode_literal(value[1:-1])))
            continue
        if kind == "hex":
            hexs = re.sub(rb"\s+", b"", value[1:-1])
            if len(hexs) % 2:
                hexs += b"0"
            operands.append(("str", bytes.fromhex(hexs.decode("ascii"))))
            continue
        if kind == "arr":
            in_array = True
            arr_items = []
            continue
        if kind == "arrend":
            in_array = False
            operands.append(("arr", arr_items))
            continue
        if kind == "op":
            op = value.decode("latin-1")
            if op == "q":
                stack.append(ctm)
            elif op == "Q":
                ctm = stack.pop() if stack else IDENTITY
            elif op == "ET":
                if seg:
                    runs.append(_segment(seg))
                seg = []
            elif op == "cm" and len(operands) >= 6:
                m = tuple(operands[-6:])
                ctm = mat_mul(m, ctm)
            elif op == "BT":
                tm = tlm = IDENTITY
                seg = []
            elif op == "Tm" and len(operands) >= 6:
                tm = tlm = tuple(operands[-6:])
                if seg:
                    runs.append(_segment(seg))
                seg = []
            elif op in ("Td", "TD") and len(operands) >= 2:
                dx, dy = operands[-2], operands[-1]
                tlm = mat_mul((1, 0, 0, 1, dx, dy), tlm)
                tm = tlm
            elif op == "Tf" and len(operands) >= 2:
                nm = operands[-2]
                if isinstance(nm, tuple) and nm[0] == "name":
                    objnum = font_res.get(nm[1])
                    cur_font = fonts.get(objnum) if objnum is not None else None
                if isinstance(operands[-1], float):
                    cur_size = operands[-1]
            elif op == "re" and len(operands) >= 4:
                x, y, w, h = operands[-4:]
                x0, y0 = apply(ctm, x, y)
                x1, y1 = apply(ctm, x + w, y + h)
                rects.append((min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0)))
            elif op == "W*":
                pass
            elif op == "n" and rects and clips is not None:
                # a path that is only clipped: record the clip rectangle
                r = rects[-1]
                clips.append(r)
            elif op in ("Tj", "TJ", "'", '"'):
                for item in operands:
                    if isinstance(item, tuple) and item[0] == "str":
                        text = decode_with_cmap(item[1], cur_font)
                        if text:
                            px, py = apply(mat_mul(tm, ctm), 0, 0)
                            seg.append({"x": px, "y": py, "text": text})
                    elif isinstance(item, tuple) and item[0] == "arr":
                        for sub in item[1]:
                            if isinstance(sub, tuple) and sub[0] == "str":
                                text = decode_with_cmap(sub[1], cur_font)
                                if text:
                                    px, py = apply(mat_mul(tm, ctm), 0, 0)
                                    seg.append({"x": px, "y": py, "text": text})
            operands = []
            continue
        # inside a TJ array: numbers are kerning offsets, strings are text
        if in_array:
            if kind == "num":
                arr_items.append(value)
            elif kind == "str":
                arr_items.append(("str", decode_literal(value[1:-1])))
            elif kind == "hex":
                hexs = re.sub(rb"\s+", b"", value[1:-1])
                if len(hexs) % 2:
                    hexs += b"0"
                arr_items.append(("str", bytes.fromhex(hexs.decode("ascii"))))
            continue
        operands = []
    return {"runs": runs, "rects": rects, "clips": clips}


def build_tables(page):
    """Turn the page's rectangles into tables with column bands and row spans.

    The gamebook draws a table's COLUMN separators as short rectangles that
    sit ON each horizontal rule: at a rule's y there is one rectangle per
    column band, and the bands are contiguous.  So the column edges are the
    rectangles' x edges, in order, with no merging.

    The rows are not drawn - only the top and bottom rule of each table is -
    so the rows come from the text baselines inside the table's vertical span
    (which is what a reader does).  Both the columns and the row bands are
    the document's own geometry; nothing is assumed about the layout.
    """
    rects = page["rects"]
    if not rects:
        return []
    lines = {}
    for x, y, w, h in rects:
        key = round(y, 1)
        lines.setdefault(key, []).append((x, x + w))
    # a rule with many rectangles is a table rule; one rectangle is a page rule
    rule_ys = sorted(y for y, spans in lines.items() if len(spans) >= 4)
    if not rule_ys:
        return []
    tables = []
    for y in rule_ys:
        spans = sorted(lines[y])
        edges = []
        for a, b in spans:
            if not edges:
                edges.append(a)
            edges.append(b)
        tables.append({"rule_y": y, "x_edges": edges})
    # group rules into tables: consecutive rules that share their column
    # geometry bound one table, and the vertical span is (first rule, last rule)
    groups = []
    for t in tables:
        if groups and t["x_edges"] == groups[-1][-1]["x_edges"]:
            groups[-1].append(t)
        else:
            groups.append([t])
    out = []
    for g in groups:
        if len(g) < 2:
            continue
        out.append({"x_edges": g[0]["x_edges"],
                    "y_top": g[0]["rule_y"],
                    "y_bottom": g[-1]["rule_y"],
                    "n_rules": len(g)})
    return out


def page_cells(page, tables, row_tol=2.5):
    """Place every run into the cell the document's own grid declares.

    Columns come from the drawn column bands.  Rows are the text baselines
    inside the table's vertical span, grouped so that words drawn on the same
    baseline share a row.
    """
    cells = []
    for t in tables:
        edges = t["x_edges"]
        top, bottom = t["y_top"], t["y_bottom"]
        inside = [r for r in page["runs"] if top - 0.5 <= r["y"] <= bottom + 0.5]
        # group the runs into text lines by y
        lines = []
        for run in sorted(inside, key=lambda r: (r["y"], r["x"])):
            if lines and abs(run["y"] - lines[-1][0]) <= row_tol:
                lines[-1][1].append(run)
            else:
                lines.append([run["y"], [run]])
        grid = []
        for _y, runs in lines:
            row = [""] * (len(edges) - 1)
            for r in sorted(runs, key=lambda r: r["x"]):
                # the band the string STARTS in owns the whole string
                ci = None
                for i in range(len(edges) - 1):
                    a, b = edges[i], edges[i + 1]
                    if a - 1.0 <= r["x"] < b - 0.5:
                        ci = i
                        break
                if ci is None:
                    continue
                row[ci] += r["text"]
            grid.append([c.strip() for c in row])
        cells.append({"x_edges": edges, "y_top": top, "y_bottom": bottom,
                      "rows": grid})
    return cells


def read_tables(pdf_bytes, page_index=0):
    """Convenience: the tables of one page of a PDF, as lists of cell strings."""
    objs = parse_objects(pdf_bytes)
    fonts = build_fonts(objs)
    pages = page_objects(objs)
    if page_index >= len(pages):
        return []
    page = extract_page(objs, fonts, pages[page_index])
    tables = build_tables(page)
    return page_cells(page, tables)
