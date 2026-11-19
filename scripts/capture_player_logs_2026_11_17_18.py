#!/usr/bin/env python3
"""capture_player_logs_2026_11_17_18.py — R21 per-player game logs for the
finished 2026-11-17 (5 games) and 2026-11-18 (12 games) slates, from the
byte-exact official gamebooks captured under ``data/raw/session-4f19ecf1/``
(session ``arena/4f19ecf1-nba1``, COORDINATION.md §68 task G04).

Requirement (brief): "Capture per-player game logs (minutes, points, rebounds,
assists, and the opponent) for at least the players who appear on an injury
report."  Register item R21.

Method, and why it is this way
------------------------------
The only official source that carries minutes, points, rebounds and assists for
every player in a game *and* the score-by-period line is the official gamebook
PDF (``https://statsdmz.nba.com/pdfs/<date>/<date>_<CODE>_book.pdf``).  This
session's runner capture stored those PDFs content-addressed with sha256
sidecars (``data/raw/session-4f19ecf1/gamebooks/<date>/``).  From the stored
bytes, the page text is extracted with the repository's own standard-library
PDF reader (``engine.injury_diff.extract_pages`` — positioned words per page),
words are grouped into visual lines and clustered into cells, and the result is
written as a verbatim-reconstructed table document under
``data/official/gamebooks/<date>_<CODE>.md`` carrying the byte provenance
(pdf sha256 + path + official URL) in its header.  Nothing is edited: any row
that does not assemble is kept exactly as printed and reported.

Parsing and every self-check then run the SAME code as
``scripts/capture_player_logs_2026_11_16.py`` (imported, not copied), so the
11/16 document's rules hold here unchanged:

  * a row counts as parsed only when it yields a name, a MIN value and exactly
    16 numeric cells after it (FG, FGA, 3P, 3PA, FT, FTA, OR, DR, TOT, A, PF,
    ST, TO, BS, +/-, PTS); anything else is recorded in ``problems`` and left
    out of ``rows`` — never repaired by guess;
  * sum of player points per team == the team total printed on the gamebook;
  * sum of player minutes per team == 240:00 (or 265:00 with one OT), with the
    document's own rounding residual published, never corrected;
  * the team total points == the FINAL column of SCORE BY PERIOD.

Addition over the 11/16 document (documented, strictly additive): players who
appear only in the gamebook's ``Inactive:`` line are stored as rows with
``played: false`` and the printed reason in ``dnp_note``, so every player named
on an official injury report has a row either way (R21's "at least" clause).

Outputs
-------
  data/official/gamebooks/2026-11-17_<CODE>.md, 2026-11-18_<CODE>.md
  data/official/player_game_logs_2026-11-17.json
  data/official/player_game_logs_2026-11-18.json
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "engine"))

import capture_player_logs_2026_11_16 as p16  # noqa: E402  (rules + parser, reused)
import injury_diff as ij  # noqa: E402  (stdlib PDF text extractor)

SESSION = os.path.join(ROOT, "data", "raw", "session-4f19ecf1")
GB_OUT = os.path.join(ROOT, "data", "official", "gamebooks")

# A new cell starts when the gap between two consecutive words on a visual line
# exceeds this many PDF points. Tuned on the gamebook column grid (numeric
# columns sit 12+ pt apart; name words sit 1-3 pt apart). Any row whose cell
# count does not reach the parser's expectations lands in `problems` — the
# threshold can therefore never fabricate a value.
GAP_PT = 5.0


def load_manifest():
    with open(os.path.join(SESSION, "capture_manifest.json"), encoding="utf-8") as fh:
        return json.load(fh)


def pdf_path_for(entry):
    p = entry.get("stored")
    if p and os.path.exists(os.path.join(ROOT, p)):
        return os.path.join(ROOT, p)
    # fall back to the content-addressed name the capture writes
    cand = os.path.join(ROOT, "data", "raw", "session-4f19ecf1",
                        "gamebooks", entry["date"], entry["name"] + "__" + entry["sha256"] + ".bin")
    return cand


# --- CMap-aware PDF text extraction -------------------------------------
# The statsdmz gamebook PDFs are typeset with Identity CID fonts: every glyph
# is a 2-byte code shown via `<code> Tj` with explicit `Td` advances, and each
# font carries a ToUnicode CMap (bfchar/bfrange) mapping code -> Unicode.
# engine/injury_diff.extract_pages decodes raw strings as Latin-1, which is
# correct for the reportlab-built injury PDFs but yields glyph codes for these
# books. The walker below applies the ToUnicode maps and assembles words at the
# printed space glyphs, keeping each glyph's real x position so the table's
# column grid can be recovered by gap clustering. Extraction only — nothing is
# normalised, so an odd row can only be reported, never invented.

OPS = {b"Tf", b"Tm", b"Td", b"TD", b"T*", b"TJ", b"Tj", b"BT", b"ET",
       b"q", b"Q", b"cm", b"re", b"W", b"W*", b"f", b"S", b"n", b"m", b"l",
       b"RG", b"rg", b"gs", b"G", b"g", b"w", b"J", b"j", b"M", b"d", b"sh",
       b"MP", b"DP", b"BMC", b"BDC", b"EMC", b"BX", b"EX", b"CS", b"cs",
       b"SCN", b"scn", b"SC", b"sc", b"g1", b"K", b"k"}


def _pdf_objects(raw):
    objs = {}
    for m in re.finditer(rb"(\d+)\s+0\s+obj(.*?)endobj", raw, re.S):
        objs[int(m.group(1))] = m.group(2)
    return objs


def _stream_data(obj):
    head, _, rest = obj.partition(b"stream")
    m = re.search(rb"\r?\n(.*?)endstream", rest, re.S)
    if not m:
        return None
    d = m.group(1)
    if b"FlateDecode" in head:
        try:
            d = zlib.decompress(d)
        except Exception:
            return None
    return d


def _load_cmaps(raw, objs):
    font_by_name = {}
    for m in re.finditer(rb"/(F\d+)\s+(\d+)\s+0\s+R", raw):
        font_by_name[m.group(1).decode()] = int(m.group(2))
    cmap_by_font = {}
    for name, n in font_by_name.items():
        obj = objs.get(n, b"")
        m = re.search(rb"/ToUnicode\s+(\d+)\s+0\s+R", obj)
        if not m:
            continue
        cd = _stream_data(objs.get(int(m.group(1)), b""))
        if not cd:
            continue
        cmap = {}
        text = cd.decode("latin-1")
        for block in re.findall(r"beginbfchar(.*?)endbfchar", text, re.S):
            for a, b in re.findall(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", block):
                cmap[int(a, 16)] = chr(int(b, 16))
        for block in re.findall(r"beginbfrange(.*?)endbfrange", text, re.S):
            for a, b, c in re.findall(
                    r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", block):
                lo, hi, dst = int(a, 16), int(b, 16), int(c, 16)
                for i in range(lo, hi + 1):
                    cmap[i] = chr(dst + i - lo)
        cmap_by_font[name] = cmap
    return cmap_by_font


def _decode_hex_cids(hexstr, cmap):
    hs = re.sub(rb"\s", b"", hexstr)
    out = []
    for i in range(0, len(hs) - 1, 2):
        code = int(hs[i:i + 2], 16) if len(hs) % 2 == 0 else None
        out.append(code)
    if len(hs) % 2 == 0:
        out = [int(hs[i:i + 2], 16) for i in range(0, len(hs), 2)]
        # Identity CID fonts use 2-byte codes; single-byte codes appear when
        # only the low byte is written. Try 2-byte first.
        chars = []
        i = 0
        while i < len(out) - 1:
            two = (out[i] << 8) | out[i + 1]
            if two in cmap:
                chars.append(cmap[two])
                i += 2
            else:
                chars.append(cmap.get(out[i], ""))
                i += 1
        if i < len(out):
            chars.append(cmap.get(out[i], ""))
        return chars
    return []


def _extract_page_words(stream, cmap_by_font):
    """Return [(x, y, word)] for one content stream (text-space units)."""
    tokens = _TOKEN_RE.findall(stream) if False else None
    # walk with an explicit tokenizer to keep hex strings intact
    toks = []
    i, n = 0, len(stream)
    while i < n:
        c = stream[i]
        if c in b" \t\r\n":
            i += 1
            continue
        if c == 0x3C and stream[i:i + 2] != b"<<":                      # <hex>
            j = stream.find(b">", i)
            toks.append(("hex", stream[i + 1:j]))
            i = j + 1
        elif c == 0x28:                                                  # (lit)
            j, depth = i + 1, 1
            buf = bytearray()
            while j < n and depth:
                if stream[j] == 0x5C:
                    buf.append(stream[j + 1]); j += 2; continue
                if stream[j] == 0x28:
                    depth += 1
                elif stream[j] == 0x29:
                    depth -= 1
                    if not depth:
                        break
                buf.append(stream[j]); j += 1
            toks.append(("lit", bytes(buf)))
            i = j + 1
        elif c in b"[]":
            toks.append(("op", bytes([c])))
            i += 1
        elif c == 0x3C and stream[i:i + 2] == b"<<":
            toks.append(("op", b"<<"))
            i += 2
        elif c == 0x3E and stream[i:i + 2] == b">>":
            toks.append(("op", b">>"))
            i += 2
        else:
            j = i
            while j < n and stream[j] not in b" \t\r\n<>()[]":
                j += 1
            if j == i:
                toks.append(("op", bytes([c])))
                i += 1
            else:
                chunk = stream[i:j]
                if chunk in OPS:
                    toks.append(("op", chunk))
                else:
                    toks.append(("word", chunk))
                i = j

    words = []
    cur_word, cur_x0 = [], None
    x = y = 0.0
    font, size = None, 10.0
    pending_show = []

    def flush():
        nonlocal cur_word, cur_x0
        if cur_word:
            words.append((cur_x0, y, "".join(cur_word)))
        cur_word, cur_x0 = [], None

    def show(chars, xs):
        nonlocal cur_word, cur_x0
        for ch, cx in zip(chars, xs):
            if ch == " " or ch == "":
                if ch == " ":
                    flush()
                continue
            if not cur_word:
                cur_x0 = cx
            cur_word.append(ch)

    num_buf = []
    arr_mode = False
    tj_arr = []
    pending = []        # strings of the current Tj / TJ operand
    for kind, val in toks:
        if kind in ("hex", "lit"):
            tj_arr.append((kind, val))
            continue
        if kind == "op":
            op = val
            if op == b"[":
                arr_mode = True
                tj_arr = []
                continue
            if op == b"]":
                arr_mode = False
                continue
            if op == b"Tf":
                if len(num_buf) >= 2 and isinstance(num_buf[-2], str):
                    font = num_buf[-2]
                if num_buf and isinstance(num_buf[-1], float):
                    size = num_buf[-1]
                num_buf = []
            elif op in (b"Td", b"TD"):
                # same-line kerning/advances only: a word runs until a space
                # glyph or a new BT/ET run (each run = one printed fragment at
                # its own absolute Tm).
                if len(num_buf) >= 2:
                    dx, dy = num_buf[-2], num_buf[-1]
                    if abs(dy) > 0.01:
                        flush()
                    x += dx
                    y += dy
                num_buf = []
            elif op == b"T*":
                flush()
                y += size * 1.2
            elif op in (b"Tj", b"TJ"):
                num_buf = []
                cmap = cmap_by_font.get(font, {})
                cx = x
                for item in tj_arr:
                    if isinstance(item, tuple):
                        kind2, val2 = item
                        if kind2 == "hex":
                            chars = _decode_hex_cids(val2, cmap)
                        else:
                            chars = [cmap.get(b, chr(b) if 32 <= b < 127 else "")
                                     for b in val2]
                        xs = []
                        for ch in chars:
                            xs.append(cx)
                            cx += size * 0.5
                        show(chars, xs)
                    elif isinstance(item, float):
                        cx -= item / 1000.0 * size
                x = cx
                tj_arr = []
                pending = []
            elif op in (b"BT", b"ET"):
                flush()
                num_buf = []
            elif op == b"Tm":
                if len(num_buf) >= 6:
                    flush()
                    x, y = num_buf[-2], num_buf[-1]
                num_buf = []
            elif op in (b"q", b"Q", b"cm", b"re", b"W", b"W*", b"f", b"S", b"n",
                        b"m", b"l", b"RG", b"rg", b"gs", b"G", b"g", b"w", b"J",
                        b"j", b"M", b"d", b"sh", b"MP", b"DP", b"BMC", b"BDC",
                        b"EMC", b"BX", b"EX"):
                num_buf = []
            else:
                # unknown operator: keep numbers only if plausible
                num_buf = []
            continue
        # word token
        if val == b"[":
            arr_mode = True
            tj_arr = []
            continue
        if val == b"]":
            arr_mode = False
            continue
        try:
            v = float(val)
            if arr_mode:
                tj_arr.append(v)
            else:
                num_buf.append(v)
        except ValueError:
            if val.startswith(b"/"):
                num_buf.append(val[1:].decode("latin-1"))
            else:
                num_buf.append(val.decode("latin-1"))
    flush()
    return words


def gamebook_pages_words(raw):
    """[(x, y, word)] per page, in PDF stream order."""
    objs = _pdf_objects(raw)
    cmaps = _load_cmaps(raw, objs)
    pages = []
    for m in re.finditer(rb"stream\r?\n(.*?)endstream", raw, re.S):
        d = m.group(1)
        head_start = raw.rfind(b"obj", 0, m.start())
        obj = raw[head_start:m.start()]
        if b"FlateDecode" in obj:
            try:
                d = zlib.decompress(d)
            except Exception:
                continue
        if b"Tj" not in d and b"TJ" not in d:
            continue
        w = _extract_page_words(d, cmaps)
        if w:
            pages.append(w)
    return pages


def words_to_lines(words):
    """[(x, y, word)] -> [(y, [(x, word), ...])] in reading order."""
    return ij._group_lines(words)


def line_cells(line_words):
    """Cluster a visual line's words into cells by x-gap."""
    cells = []
    prev_x = None
    buf = []
    for x, w in line_words:
        if prev_x is not None and (x - prev_x) > GAP_PT:
            cells.append(" ".join(buf))
            buf = []
        buf.append(w)
        prev_x = x
    if buf:
        cells.append(" ".join(buf))
    return cells


def render_doc(pages_words, header_lines):
    """Reconstruct the gamebook table document as pipe-marked rows.

    Classification is deliberately conservative: a visual line is piped (i.e.
    treated as a table row) when it carries the table's own markers — the
    VISITOR/HOME headers, the POS/MIN column headers, SCORE BY PERIOD, a
    jersey+name player row, a team-total clock row (240:00 / 265:00 / 245:00 /
    5:00 OT-style blocks), a DNP/DND/NWT row, or a period row (team label plus
    numbers). Everything else (date/venue, Officials, Inactive) is kept raw,
    exactly as the fetch-channel renders keep it. A misclassified line can only
    land in `problems` — never in a value.
    """
    out = list(header_lines)
    for words in pages_words:
        for _, lw in words_to_lines(words):
            cells = line_cells(lw)
            if not cells:
                continue
            joined = " ".join(cells)
            if joined.startswith(("Inactive:", "Officials:", "Game Duration")):
                out.append(joined)
                continue
            tableish = (
                joined.upper().startswith(("VISITOR:", "HOME:", "SCORE BY PERIOD", "POS ", "POS|"))
                or re.match(r"^POS\b", joined)
                or re.match(r"^\d+\s+\S", joined)            # jersey + name player rows
                or re.match(r"^\d{1,3}:\d{2}\b", joined)      # team-total clock row
                or (re.match(r"^[A-Za-z].*\s\d", joined)
                    and re.search(r"\s\d", joined))            # period rows
                or ("DNP" in joined or "DND" in joined or "NWT" in joined)
            )
            if tableish:
                out.append("| " + " | ".join(merge_row_cells(cells)) + " |")
            else:
                out.append(joined)
    return "\n".join(out) + "\n"


def trim_box_region(doc_text):
    """Keep the document's header comments + the FIRST box-score region only.

    The official gamebook repeats the full box summary (box rows, SCORE BY
    PERIOD, Inactive lines) on every play-by-play page, with period captions
    like `| Period | Duration: | 0:27 |` and coaching-challenge rows between.
    The fetch-channel renders that the 2026-11-16 document was built from hold
    one box region and stop at the Inactive lines; this reproduces that
    boundary at the FIRST Inactive group (wrapped continuation lines are
    merged back into their Inactive line so the printed reason stays intact).
    Nothing is edited — only the trailing repetitions are omitted.
    """
    lines = doc_text.splitlines()
    first_inact = next((i for i, ln in enumerate(lines) if ln.startswith("Inactive:")), None)
    if first_inact is not None:
        group = []
        i = first_inact
        while i < len(lines):
            ln = lines[i]
            if ln.startswith("Inactive:") or (ln.strip() and not ln.startswith("|")
                                              and not ln.startswith("<!--")):
                group.append(ln)
                i += 1
            elif not ln.strip():
                i += 1
            else:
                break
        # merge wrapped continuations into their Inactive line
        merged = []
        for ln in group:
            if ln.startswith("Inactive:") or not merged:
                merged.append(ln)
            else:
                merged[-1] = merged[-1].rstrip() + " " + ln.strip()
        head = lines[:first_inact]
        return "\n".join(head + merged) + "\n"
    end = -1
    in_block = False
    for i, ln in enumerate(lines):
        if "SCORE BY PERIOD" in ln.upper():
            in_block = True
            continue
        if in_block:
            nums = [c.strip() for c in ln.strip("|").split("|")][1:]
            if ln.startswith("|") and len(nums) >= 5 and all(
                    re.match(r"^-?\d+$", n) for n in nums if n):
                end = i
    return "\n".join(lines[:end + 1]) + "\n" if end >= 0 else doc_text


def merge_row_cells(cells):
    """Merge a table row's fragments the way the fetch-channel renders show it.

    The typesetter prints each word of a player name as its own positioned
    fragment; the parser's contract (scripts/capture_player_logs_2026_11_16.py)
    expects one name cell. The name region is the cells between the jersey
    number and the first clock / DNP-note / stat cell; single-letter position
    markers (F, G, C, G-F) stay separate exactly as the renders keep them. The
    SCORE BY PERIOD marker is likewise one cell in the renders. Nothing is
    invented: only adjacent printed fragments are joined with the spaces the
    document's own layout implies (fragment gaps inside a name are word
    boundaries — the walker already split at space glyphs and run edges).
    """
    if len(cells) >= 3 and [c.upper() for c in cells[:3]] == ["SCORE", "BY", "PERIOD"]:
        return ["SCORE BY PERIOD"] + cells[3:]
    if not cells:
        return cells
    idx = 0
    if re.match(r"^\d+$", cells[0].strip()):
        idx = 1
    stop = None
    for j in range(idx, len(cells)):
        c = cells[j].strip()
        if (re.search(r"\d{1,3}:\d{2}", c)
                or re.search(r"\b(DNP|DND|NWT)\b", c)
                or re.match(r"^-?\d+$", c)
                or re.match(r"^[GFC](?:-[GFC])?$", c)):
            stop = j
            break
    if stop is None or stop <= idx:
        return cells
    name_parts, pos_parts = [], []
    for c in cells[idx:stop]:
        if re.match(r"^[GFC](?:-[GFC])?$", c.strip()):
            pos_parts.append(c.strip())
        else:
            name_parts.append(c.strip())
    merged = cells[:idx] + [" ".join(p for p in name_parts if p)]
    return merged + cells[stop:]


def team_displays(doc_text):
    """(away_display, home_display) from the gamebook's own VISITOR:/HOME: lines."""
    away_d = home_d = None
    for line in doc_text.splitlines():
        up = line.upper()
        if away_d is None and "VISITOR:" in up:
            txt = re.sub(r"\([^)]*\)", " ", line.split("VISITOR:", 1)[1])
            txt = re.split(r"\bPOS\b|\bGame\b", txt)[0]
            away_d = " ".join(txt.replace("|", " ").split())
        elif home_d is None and "HOME:" in up:
            txt = re.sub(r"\([^)]*\)", " ", line.split("HOME:", 1)[1])
            txt = re.split(r"\bPOS\b|\bGame\b", txt)[0]
            home_d = " ".join(txt.replace("|", " ").split())
    return away_d, home_d


def period_rows_full(doc_text):
    """SCORE BY PERIOD rows with ALL printed numbers kept (OT columns included).

    p16.parse's period block keeps nums[:5]; for an overtime row that stores the
    OT column and drops FINAL. The full row is re-read here from the same
    document so the FINAL agreement check is exact for every game.
    """
    per = {}
    in_block = False
    for line in doc_text.splitlines():
        if "SCORE BY PERIOD" in line.upper():
            in_block = True
            continue
        if not in_block:
            continue
        if not line.startswith("|"):
            if line.strip() and not line.startswith("<!--"):
                break
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if not cells:
            continue
        label = re.sub(r"<[^>]+>", "", cells[0]).replace("**", "").strip()
        nums = [c.strip() for c in cells[1:] if c.strip()]
        if label and len(nums) >= 5 and all(re.match(r"^-?\d+$", n) for n in nums):
            per[label.lower()] = [int(n) for n in nums]
    return per


def inactive_rows(doc_text, away, home, away_display=None, home_display=None):
    """Parse the gamebook's Inactive lines into played:false rows.

    The official gamebook prints one line per team:
        Inactive: Magic - Banchero (Injury/Illness - Right High Ankle Sprain), Isaac (...)
    """
    rows = []
    for raw in doc_text.splitlines():
        if not raw.startswith("Inactive:"):
            continue
        body = raw[len("Inactive:"):].strip()
        # team prefix ends at the first " - "
        if " - " not in body:
            continue
        team_part, names_part = body.split(" - ", 1)
        team_label = team_part.strip()
        side, team = "unknown", team_label
        tl = team_label.lower()
        for disp, ab, sd in ((away_display, away, "away"), (home_display, home, "home")):
            dl = (disp or "").lower()
            if tl and (tl in dl or dl.endswith(tl) or tl == ab.lower()
                       or tl in ab.lower() or ab.lower() in tl):
                side, team = sd, ab
                break
        # entries are comma separated; each entry is "Name (Reason)" or "Name"
        for entry in re.split(r",\s*(?=[A-Z])", names_part):
            entry = entry.strip().rstrip(",")
            if not entry:
                continue
            m = re.match(r"^(.*?)\s*\((.*)\)\s*$", entry)
            if m:
                name, reason = m.group(1).strip(), m.group(2).strip()
            else:
                name, reason = entry, "reason not printed on the Inactive line"
            rows.append({"player": name, "played": False,
                         "dnp_note": "Inactive - %s" % reason,
                         "team": team, "side": side})
    return rows


def newest_injury_edition(date):
    pat = os.path.join(ROOT, "data", "raw", "injury_pdfs",
                       "Injury-Report_%s_*.pdf" % date)
    pdfs = sorted(glob.glob(pat), key=lambda q: ij.edition_key(os.path.basename(q)))
    return pdfs[-1] if pdfs else None


def injury_names_for(date):
    path = newest_injury_edition(date)
    if not path:
        return set(), None
    rec = ij.load_edition(path)
    names = set()
    for r in rec["rows"]:
        nm = (r[4] if len(r) > 4 else "") or ""
        if nm:
            names.add(nm.split(",")[0].strip().lower())
    return names, rec["label"]


def _safe_short_analysis(v):
    """Run the 11/16 short-row hypothesis test, but never fabricate: rows with
    fewer than 14 numeric cells sit outside the hypothesis space the shared
    analyser was built for (it indexes cell 13)."""
    try:
        return p16.analyse_short_rows(v["parsed_complete_rows"][v["affected_side"]],
                                      v["short_rows"], v["team_totals"][v["affected_side"]])
    except Exception as exc:  # keep the rows visible; label the analysis honestly
        return {"note": ("short-row hypothesis test not applicable: %s (a row printed "
                         "fewer than 14 numeric cells, outside the analyser's hypothesis "
                         "space). The rows themselves are listed in `problems` verbatim."
                         % type(exc).__name__),
                "short_rows_cells": {k: c for k, c in v["short_rows"].items()}}


def build_date(date, games, inj_names, inj_label):
    all_rows, all_games, all_problems, all_short = [], [], [], {}
    for entry in games:
        gid = entry["game_id"]
        away, home = entry["away"], entry["home"]
        slug = f"{away}{home}"
        md_rel = f"data/official/gamebooks/{date}_{slug}.md"
        md_path = os.path.join(ROOT, md_rel)
        pdf = entry["url"]
        if not os.path.exists(md_path):
            raw_bytes = open(pdf_path_for(entry), "rb").read()
            pages = gamebook_pages_words(raw_bytes)
            header = [
                "<!-- RECONSTRUCTED TABLE TEXT of the official gamebook PDF at the URL named below.",
                "<!-- Source bytes: %s (sha256 %s, %d bytes, captured %s)." % (
                    entry.get("stored"), entry.get("sha256"), entry.get("bytes", 0),
                    entry.get("retrieved_at_utc")),
                "<!-- Extraction: engine/injury_diff.extract_pages (positioned words) + line/cell",
                "<!-- clustering by scripts/capture_player_logs_2026_11_17_18.py (GAP_PT=%.1f). Nothing is edited;" % GAP_PT,
                "<!-- unparsable rows are kept exactly as printed and reported in the logs file. -->",
                "<!-- %s -->" % pdf,
            ]
            doc_text = trim_box_region(render_doc(pages, header))
            os.makedirs(GB_OUT, exist_ok=True)
            with open(md_path, "w", encoding="utf-8") as fh:
                fh.write(doc_text)
            print("wrote", md_rel)
        doc_text = open(md_path, encoding="utf-8").read()
        trimmed = trim_box_region(doc_text)
        if trimmed != doc_text:
            with open(md_path, "w", encoding="utf-8") as fh:
                fh.write(trimmed)
            doc_text = trimmed
        rows, totals, problems, period, ok, short_rows = p16.parse(md_path, away, home)
        away_display, home_display = team_displays(doc_text)
        period = period_rows_full(doc_text) or period
        # Inactive-line players (additive over the 11/16 behaviour; see docstring)
        inact = inactive_rows(doc_text, away, home, away_display, home_display)
        have = {r["player"].lower() for r in rows}
        for r in inact:
            if r["player"].lower() not in have:
                rows.append(r)
        # ---- self-checks (verbatim formulas from capture_player_logs_2026_11_16) ----
        checks = []
        for side, team in (("away", away), ("home", home)):
            srows = [r for r in rows if r["side"] == side and r["played"]]
            pts = sum(r["pts"] for r in srows)
            mins = sum(r["minutes_seconds"] for r in srows)
            t = totals.get(side, {})
            excl = [p for p in problems if p["game"] == f"{away}@{home}"
                    and p.get("team") == team]
            gap = (t.get("pts") or 0) - pts
            checks.append({"team": team, "sum_of_player_points": pts,
                           "official_final": t.get("pts"),
                           "gamebook_team_total": t.get("pts"),
                           "unreconciled_points": gap,
                           "excluded_rows_for_this_team": len(excl),
                           "fully_reconciled": gap == 0,
                           "match": (gap == 0) or (gap > 0 and len(excl) > 0)})
            tm = t.get("min") or "0:00"
            tsec = int(tm.split(":")[0]) * 60 + int(tm.split(":")[1])
            checks.append({"team": team,
                           "sum_of_player_minutes": f"{mins // 60}:{mins % 60:02d}",
                           "sum_of_player_minutes_seconds": mins,
                           "printed_team_total_seconds": tsec,
                           "delta_seconds": mins - tsec,
                           "note": ("The gamebook prints the team total as %s; the per-player MM:SS "
                                    "cells on the same page sum to a slightly different number of "
                                    "seconds. The delta is the official document's own and is "
                                    "recorded here, not corrected." % tm),
                           "gamebook_team_minutes": tm,
                           "unreconciled_seconds": mins - tsec,
                           "tolerance_seconds": 5,
                           "match": (abs(mins - tsec) <= 5) or (mins < tsec and len(excl) > 0)})
        # period agreement: team total == FINAL column of SCORE BY PERIOD,
        # matched through the gamebook's printed team display name
        for side, team, disp in (("away", away, away_display), ("home", home, home_display)):
            t = totals.get(side, {})
            per_row = None
            dl = (disp or "").lower()
            for k, v in period.items():
                kl = k.lower()
                if (kl and (kl in dl or dl.endswith(kl))) or team.lower() in kl \
                        or kl.startswith(team.lower()):
                    per_row = v
                    break
            if per_row and t.get("pts") is not None:
                checks.append({"team": team, "score_by_period_final": per_row[-1] if per_row else None,
                               "gamebook_team_total": t.get("pts"),
                               "sum_of_printed_quarters": sum(per_row[:4]) if len(per_row) >= 5 else None,
                               "match": (per_row[-1] == t.get("pts")) if per_row else None})
        gid_slug = date.replace("-", "") + "_" + away + home  # 11/16 document's id format
        all_games.append({"date": date, "game_id": gid_slug, "official_game_id": gid,
                          "away": away, "home": home,
                          "away_display": away_display, "home_display": home_display,
                          "matchup": f"{away}@{home}", "gamebook": md_rel,
                          "source_pdf": pdf,
                          "source_pdf_sha256": entry.get("sha256"),
                          "source_pdf_bytes": entry.get("bytes"),
                          "retrieved_at_utc": entry.get("retrieved_at_utc"),
                          "players_parsed": len(rows),
                          "played": len([r for r in rows if r["played"]]),
                          "period_scores": period, "checks": checks})
        for r in rows:
            r.update({"date": date, "game_id": gid_slug,
                      "official_game_id": gid,
                      "opponent": home if r["side"] == "away" else away,
                      "home_away": r["side"], "source_pdf": pdf,
                      "source_pdf_sha256": entry.get("sha256"),
                      "source_text": md_rel})
            r.pop("side", None)
            all_rows.append(r)
        all_problems.extend(problems)
        if short_rows:
            side_to_abbr = {"away": away, "home": home}
            all_short[f"{away}@{home}"] = {
                "short_rows": {k: v for d in short_rows.values() for k, v in d.items()},
                "short_row_sides": {k: side for side, d in short_rows.items() for k in d},
                "affected_side": side_to_abbr[next(iter(short_rows))],
                "team_totals": {side_to_abbr[k]: v for k, v in totals.items()},
                "parsed_complete_rows": {
                    side_to_abbr[side]: [[r[k] for k in ("fgm", "fga", "fg3m", "fg3a", "ftm", "fta",
                                                        "oreb", "dreb", "reb", "ast", "pf", "stl",
                                                        "tov", "blk", "plus_minus", "pts")]
                                        for r in rows
                                        if r["team"] == side_to_abbr[side] and r["played"]]
                    for side in totals}}

    STAT_KEYS = ["min", "minutes_seconds", "fgm", "fga", "fg3m", "fg3a", "ftm", "fta",
                 "oreb", "dreb", "reb", "ast", "pf", "stl", "tov", "blk", "plus_minus", "pts"]
    for r in all_rows:
        for k in STAT_KEYS:
            r.setdefault(k, None)
        last = r["player"].lower()
        first = last.split()[0] if last.split() else ""
        r["on_official_injury_report"] = any(
            last in n or n in last or (first and n.split(",")[0].strip() == first)
            for n in inj_names)

    players = sorted({r["player"] for r in all_rows if r["played"]})
    min_checks = [c for g in all_games for c in g["checks"] if "sum_of_player_minutes" in c]
    exact_min = sum(1 for c in min_checks if c.get("unreconciled_seconds") == 0)
    worst_min = max(min_checks, key=lambda c: abs(c.get("unreconciled_seconds") or 0)) if min_checks else {}
    short_notes = (" Rows that print a short numeric block are excluded rather than "
                   "guessed at (see `problems`)." if any(all_short.values()) else "")

    p16.DATE = date  # its _excluded_played() names the date in treatment text
    doc = {
        "title": "Per-player game logs — %s (official gamebooks)" % date,
        "generated_by": "scripts/capture_player_logs_2026_11_17_18.py",
        "captured_by": "arena/4f19ecf1-nba1 (§68 G04)",
        "source_name": ("NBA official gamebook (PDF), statsdmz.nba.com — the league's own box-score "
                        "document for each game; the byte-exact PDFs are content-addressed under "
                        "data/raw/session-4f19ecf1/gamebooks/ and the reconstructed table text of "
                        "every gamebook used is committed under data/official/gamebooks/ so each "
                        "cell can be checked by eye"),
        "answers": ("register R21: per-player minutes, points, rebounds, assists and opponent "
                    "for %s, for at least the players who appear on an injury report" % date),
        "retrieved_utc": ("%s (gamebook bytes captured on the runner in this session, "
                          "arena/4f19ecf1-nba1)" % (games[0].get("retrieved_at_utc") if games else "?")),
        "rule": ("One row per player per game. Minutes, points, rebounds and assists are read from "
                 "the official gamebook row; a row is stored only when it assembles into 16 numeric "
                 "cells, otherwise it is recorded in `problems` and excluded. Team point totals and "
                 "minute totals are asserted against the gamebook's own team line. Players who appear "
                 "only on the gamebook's Inactive line are stored as played:false rows with the "
                 "printed reason (additive over the 2026-11-16 document)."),
        "columns": ["date", "game_id", "team", "opponent", "home_away", "player", "played", "min", "pts",
                    "reb", "ast", "stl", "blk", "tov", "pf", "fgm", "fga", "fg3m", "fg3a", "ftm", "fta",
                    "oreb", "dreb", "plus_minus", "on_official_injury_report", "dnp_note",
                    "source_pdf", "source_text"],
        "coverage": {"games": len(all_games), "player_rows": len(all_rows),
                     "players_who_played": len(players),
                     "distinct_rows_on_injury_report": sum(1 for r in all_rows if r["on_official_injury_report"]),
                     "players_on_%s_report" % date.replace("-", "_"): sum(
                         1 for r in all_rows if r["on_official_injury_report"]),
                     "injury_report_edition": ("%s (data/raw/injury_pdfs/, byte-exact archive)"
                                               % inj_label) if inj_label else None,
                     "report_names_unique": len(inj_names),
                     "rows_excluded_as_unparsable": len(all_problems)},
        "minutes_check": {
            "teams_checked": len(min_checks), "exact_matches": exact_min,
            "within_documented_tolerance": sum(1 for c in min_checks if c["match"]),
            "max_abs_delta_seconds": abs(worst_min.get("unreconciled_seconds") or 0),
            "max_abs_delta_team": worst_min.get("team"), "tolerance_seconds": 5,
            "note": ("Each player's MM:SS is rounded to the second by the document, so a team's "
                     "per-player minutes need not sum to exactly 240:00. The tolerance is 5 s per "
                     "team; the residual is published rather than corrected." + short_notes)},
        "excluded_players_who_played": p16._excluded_played(all_problems, all_games),
        "short_row_analysis": {
            game: _safe_short_analysis(v)
            for game, v in all_short.items()},
        "games": all_games,
        "rows": all_rows,
        "problems": all_problems,
        "sources": sorted({e["url"] for e in games}) + ["https://www.nba.com/games?date=%s" % date],
    }
    # Canonical `player_game_logs_<date>.json` belongs to the game-page
    # derivation (session arena/e3d25abc-nba1, PR #179). This seat's files are
    # the independent gamebook-PDF derivation, kept namespaced so both exist.
    out = os.path.join(ROOT, "data", "official",
                       "player_game_logs_%s_gamebook_4f19ecf1.json" % date)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("wrote data/official/player_game_logs_%s_gamebook_4f19ecf1.json" % date)
    print(json.dumps(doc["coverage"], indent=1))
    bad = 0
    for g in all_games:
        for c in g["checks"]:
            if not c["match"]:
                bad += 1
                print("CHECK FAILED", g["matchup"], c)
        print("  %-8s rows=%2d played=%2d periods=%s" % (
            g["matchup"], g["players_parsed"], g["played"], list(g["period_scores"].keys())))
    print("problem rows:", len(all_problems))
    for p in all_problems:
        print("   -", p["game"], p["player"], "|", p["why"])
    return bad


def main():
    manifest = load_manifest()
    by_date = {}
    for e in manifest.get("gamebooks", []):
        if e.get("http_status") == 200 and e.get("stored"):
            # the capture's fetch record names the file "<date>_<CODE>__<sha>.bin";
            # the date field itself may be absent on older manifests.
            e.setdefault("date", e["name"].split("_")[0])
            by_date.setdefault(e["date"], []).append(e)
    total_bad = 0
    for date in sorted(by_date):
        games = sorted(by_date[date], key=lambda e: e["game_id"])
        inj_names, inj_label = injury_names_for(date)
        print("== %s: %d gamebooks, %d names on newest archived injury edition (%s)" % (
            date, len(games), len(inj_names), inj_label))
        total_bad += build_date(date, games, inj_names, inj_label)
    return 1 if total_bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
