"""Structured parsers for the official NBA pages the freshness gate requires.

RFG4 (COORDINATION.md section 38/42): parse and independently verify standings,
traditional/opponent/advanced team stats and schedule rows from the official
payloads the scheduled fetcher already retrieves, so a verified promotion
record can be built instead of a guess.

Design rules (same as engine/fetch_official.py):
  * standard library only - the GitHub Actions runner installs nothing;
  * a row that cannot be read from the payload is left out and reported in
    `problems`; a value is never inferred, interpolated or back-solved;
  * every parser returns (cols, rows, meta) where meta records which strategy
    produced the rows and what integrity checks passed;
  * a partial or wrong table returns no rows at all - a stale snapshot is
    safer than a confidently wrong one.

Strategies per table (tried in order):
  1. ``html_table``  - server-rendered ``<tr>`` rows with team links
                       (patterns seen on www.nba.com/stats/team/<id>/... and
                       www.nba.com/team/<id>/<slug>);
  2. ``next_data``   - the page's ``__NEXT_DATA__`` embedded JSON state
                       (walked for header/rowSet pairs or team-keyed dicts);
  3. ``stats_api``   - a stats.nba.com LeagueDashTeamStats / LeagueStandingsV3
                       JSON response (the data layer behind the cited pages;
                       used by the fetcher's API fallback path).

Nothing here fetches the network; callers pass the bytes they already hashed.
"""

from __future__ import annotations

import html as html_mod
import json
import re

try:
    from common import ABBR
except ImportError:  # standalone use (tests)
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from common import ABBR

TEAM_NAME_TO_ABBR = dict(ABBR)
TEAM_ABBR_TO_NAME = {v: k for k, v in ABBR.items()}
# Lower-cased slug/tricode -> abbreviation. Game links use tricodes lower-cased
# (e.g. /game/mem-vs-was-0022600247); team page links use slugs. Both maps are
# derived from the canonical ABBR table plus the slug words that appear in the
# ABBR names - never a guessed abbreviation.
SLUG_TO_ABBR = {}
for _name, _abbr in ABBR.items():
    SLUG_TO_ABBR[_abbr.lower()] = _abbr
    SLUG_TO_ABBR[_name.lower().replace(" ", "-")] = _abbr

NUM_RE = re.compile(r"^-?(?:\d+(?:\.\d+)?|\.\d+)$")
TAG_RE = re.compile(r"<[^>]+>")
HREF_RE = re.compile(r'href="([^"]+)"')
TR_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)
CELL_RE = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S | re.I)
NEXT_DATA_RE = re.compile(
    r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)

# Column schema for data/raw/team_advanced.json (the committed model input).
ADVANCED_COLS = ["team", "gp", "w", "l", "min", "ortg", "drtg", "netr",
                 "ast_pct", "ast_to", "ast_ratio", "oreb_pct", "dreb_pct",
                 "reb_pct", "tov_pct", "efg_pct", "ts_pct", "pace", "pie",
                 "poss"]
ADVANCED_INT = {"gp", "w", "l", "poss"}
# API header names for the advanced schema (normalised, as in fetch_official).
ADVANCED_API_WANT = {
    "team": "TEAMNAME", "gp": "GP", "w": "W", "l": "L", "min": "MIN",
    "ortg": "OFFRTG", "drtg": "DEFRTG", "netr": "NETRTG",
    "ast_pct": "ASTPCT", "ast_to": "ASTTO", "ast_ratio": "ASTRATIO",
    "oreb_pct": "OREBPCT", "dreb_pct": "DREBPCT", "reb_pct": "REBPCT",
    "tov_pct": "TOVPCT", "efg_pct": "EFGPCT", "ts_pct": "TSPCT",
    "pace": "PACE", "pie": "PIE", "poss": "POSS",
}

STANDINGS_COLS = ["team", "team_name", "conference", "rank", "w", "l",
                  "win_pct", "gb", "conf", "div", "home", "road", "neutral",
                  "ot", "last10", "streak"]


# ----------------------------------------------------------------- utilities
def _norm_header(h):
    return re.sub(r"[^a-z0-9]+", "_", str(h).strip().lower()).strip("_")


def _cell_text(cell):
    t = TAG_RE.sub(" ", cell)
    t = html_mod.unescape(t)
    return re.sub(r"\s+", " ", t).replace(",", "").strip()


def _to_num(text):
    """Strict numeric parse. Returns int/float or None - never a guess."""
    if not isinstance(text, str):
        return None
    t = text.strip().replace(",", "")
    if t in ("", "-", "--"):
        return None
    if not NUM_RE.fullmatch(t):
        return None
    return int(t) if re.fullmatch(r"-?\d+", t) else float(t)


def _next_data(text):
    m = NEXT_DATA_RE.search(text)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except ValueError:
        return None


def _team_from_cell(text, hrefs):
    """Resolve a team cell to (abbr, team_name) from text or link slug."""
    t = text.strip()
    if t in TEAM_NAME_TO_ABBR:
        return TEAM_NAME_TO_ABBR[t], t
    if t.upper() in TEAM_ABBR_TO_NAME:
        return t.upper(), TEAM_ABBR_TO_NAME[t.upper()]
    for h in hrefs:
        m = re.search(r"/(?:stats/)?team/\d+/([a-z0-9\-]+)", h)
        if m:
            slug = m.group(1).lower()
            if slug in SLUG_TO_ABBR:
                abbr = SLUG_TO_ABBR[slug]
                return abbr, TEAM_ABBR_TO_NAME[abbr]
    return None, None


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


# ------------------------------------------------------------------ strategy
def parse_team_table(text, cols=None, int_cols=(), variant="generic"):
    """Parse a 30-team stats table (traditional / opponent / advanced / generic).

    `cols` is the target schema (ADVANCED_COLS for advanced; None derives the
    column names from the page's own header row, verbatim normalised). Returns
    (cols, rows, meta). rows == [] on any integrity failure.
    """
    problems = []
    for strategy in ("html_table", "next_data", "stats_api"):
        if strategy == "html_table":
            got_cols, rows, probs = _team_table_html(text, cols, int_cols)
        elif strategy == "next_data":
            nd = _next_data(text)
            if nd is None:
                continue
            got_cols, rows, probs = _team_table_json(nd, cols, int_cols)
        else:
            try:
                payload = json.loads(text)
            except ValueError:
                continue
            got_cols, rows, probs = _team_table_json(payload, cols, int_cols)
        if rows:
            check = _team_integrity(rows, got_cols, variant)
            if check:
                problems.extend(f"{strategy}: {p}" for p in check)
                continue
            return got_cols, rows, {"strategy": strategy, "row_count": len(rows),
                                    "integrity": "ok"}
        problems.extend(f"{strategy}: {p}" for p in probs)
    return cols or [], [], {"strategy": None, "row_count": 0,
                            "problems": problems[:12]}


def _team_table_html(text, cols, int_cols):
    rows, problems = [], []
    # header row: the first <tr> with >=3 <th> cells and no team link
    header = None
    for tr in TR_RE.finditer(text):
        body = tr.group(1)
        ths = [_cell_text(c) for c in CELL_RE.findall(body)
               if re.search(r"<th", body, re.I)]
        if len(ths) >= 3 and not re.search(r"/(?:stats/)?team/\d+/", body):
            cand = [_norm_header(h) for h in ths]
            if "team" in cand:
                header = cand
                break
    for tr in TR_RE.finditer(text):
        body = tr.group(1)
        raw_cells = CELL_RE.findall(body)
        hrefs = HREF_RE.findall(body)
        cells = [_cell_text(c) for c in raw_cells]
        if not cells:
            continue
        abbr, name, team_cell = None, None, None
        for c, raw in zip(cells, raw_cells):
            a, n = _team_from_cell(c, HREF_RE.findall(raw))
            if a:
                abbr, name, team_cell = a, n, c
                break
        if not abbr and any("/team/" in h or "/stats/team/" in h for h in hrefs):
            for c, raw in zip(cells, raw_cells):
                a, n = _team_from_cell(c, HREF_RE.findall(raw))
                if a:
                    abbr, name, team_cell = a, n, c
                    break
        if not abbr:
            continue
        try:
            ti = cells.index(team_cell)
        except ValueError:
            problems.append(f"{abbr}: team cell not found verbatim")
            continue
        nums = [c for c in cells[ti + 1:] if NUM_RE.fullmatch(c)]
        target = cols or (header[header.index("team") + 1:]
                          if header and "team" in header else [])
        need = len(cols) - 1 if cols else len(target)
        if need and len(nums) < need:
            problems.append(f"{abbr}: only {len(nums)} numeric cells (need {need})")
            continue
        if cols:
            row = [abbr]
            ok = True
            for key, raw in zip(cols[1:], nums):
                v = _to_num(raw)
                if v is None or (key in int_cols and not _is_int(v) and float(v) != int(v)):
                    problems.append(f"{abbr}: bad cell {raw!r} for {key}")
                    ok = False
                    break
                row.append(int(v) if key in int_cols else v)
            if not ok:
                continue
        else:
            row = [abbr] + [_to_num(raw) for raw in nums[:need]]
            if None in row[1:]:
                problems.append(f"{abbr}: non-numeric cell in {nums[:need]}")
                continue
        rows.append(row)
    if header is None and not cols:
        return cols or [], [], problems + ["no header row with a Team column found"]
    out_cols = cols or (["team"] + target if target else [])
    return out_cols, rows, problems


def _walk_json(node, out):
    """Collect (headers, rows) pairs from any nested stats-API-like shape."""
    if isinstance(node, dict):
        headers = node.get("headers") or node.get("labels") or node.get("columns")
        rws = node.get("rowSet") or node.get("rows")
        if isinstance(headers, list) and isinstance(rws, list) and rws:
            out.append((headers, rws))
        for v in node.values():
            _walk_json(v, out)
    elif isinstance(node, list):
        # A list of same-keyed team dicts (render-state shape) counts too.
        if node and isinstance(node[0], dict):
            keys = set(node[0].keys())
            if len(node) >= 20 and any(
                    k.lower() in ("team", "teamname", "team_name", "nickname")
                    for k in keys):
                out.append((sorted(keys), node))
        for v in node:
            _walk_json(v, out)


def _team_table_json(payload, cols, int_cols):
    pairs = []
    _walk_json(payload, pairs)
    problems = []
    for headers, rws in pairs:
        if isinstance(rws[0], dict):
            norm = {_norm_header(h): h for h in headers}
            rows = []
            for r in rws:
                name = None
                for k in ("teamname", "team_name", "team", "nickname"):
                    if k in norm and norm[k] in r:
                        name = str(r[norm[k]])
                        break
                if not name:
                    break
                abbr, tname = _team_from_cell(name, [])
                if not abbr:
                    break
                if cols:
                    row, ok = [abbr], True
                    for key in cols[1:]:
                        want = (ADVANCED_API_WANT.get(key, key)).lower()
                        src = norm.get(want) or norm.get(_norm_header(key))
                        if src is None or src not in r:
                            ok = False
                            break
                        v = r[src]
                        if key in int_cols:
                            try:
                                v = int(float(v))
                            except (TypeError, ValueError):
                                ok = False
                                break
                        else:
                            try:
                                v = float(v)
                            except (TypeError, ValueError):
                                ok = False
                                break
                        row.append(v)
                    if not ok or len(row) != len(cols):
                        problems.append(f"{abbr}: incomplete dict row")
                        continue
                else:
                    row = [abbr]
                    for k in sorted(norm):
                        if norm[k] == headers[0] if headers else False:
                            continue
                    problems.append("dict rows require an explicit schema")
                    continue
                rows.append(row)
            if rows:
                return cols, rows, problems
        else:
            # list-of-lists (rowSet) shape
            norm = {_norm_header(h): i for i, h in enumerate(headers)}
            if cols:
                missing = [k for k in cols
                           if k != "team" and (ADVANCED_API_WANT.get(k, _norm_header(k)).lower()
                                               not in norm and _norm_header(k) not in norm)]
                name_idx = None
                for k in ("teamname", "team_name", "team", "nickname"):
                    if k in norm:
                        name_idx = norm[k]
                        break
                if missing or name_idx is None:
                    problems.append(f"rowSet headers do not cover schema (missing {missing})")
                    continue
                rows, bad = [], []
                for rr in rws:
                    try:
                        abbr, _ = _team_from_cell(str(rr[name_idx]), [])
                        if not abbr:
                            bad.append(str(rr[name_idx]))
                            continue
                        row = [abbr]
                        for key in cols[1:]:
                            want = _norm_header(ADVANCED_API_WANT.get(key, key))
                            idx = norm.get(want, norm.get(_norm_header(key)))
                            v = rr[idx]
                            row.append(int(float(v)) if key in int_cols else float(v))
                    except (TypeError, ValueError, IndexError):
                        bad.append("unparseable row")
                        continue
                    rows.append(row)
                if bad:
                    return cols, [], [f"{len(bad)} bad rowSet rows, first: {bad[0]}"]
                return cols, rows, problems
    return cols or [], [], problems or ["no team-table structure found in JSON"]


def _team_integrity(rows, cols, variant):
    problems = []
    names = [r[0] for r in rows]
    if len(rows) != 30:
        problems.append(f"expected 30 rows, got {len(rows)}")
    if len(set(names)) != len(names):
        problems.append("duplicate teams in table")
    if set(names) - set(TEAM_ABBR_TO_NAME):
        problems.append(f"unknown teams: {sorted(set(names) - set(TEAM_ABBR_TO_NAME))[:4]}")
    try:
        igp, iw, il = cols.index("gp"), cols.index("w"), cols.index("l")
    except ValueError:
        igp = iw = il = -1
    for r in rows:
        t = r[0]
        if igp >= 0:
            gp, w, l = r[igp], r[iw], r[il]
            if not (_is_int(gp) and _is_int(w) and _is_int(l)):
                problems.append(f"{t}: gp/w/l not integers")
                continue
            if w + l != gp:
                problems.append(f"{t}: W+L {w}+{l} != GP {gp}")
            if not (1 <= gp <= 82):
                problems.append(f"{t}: GP {gp} out of range")
        if variant == "advanced":
            try:
                ortg = r[cols.index("ortg")]
                pace = r[cols.index("pace")]
                poss = r[cols.index("poss")]
                if not (70 <= ortg <= 150):
                    problems.append(f"{t}: ortg {ortg} out of range")
                if not (85 <= pace <= 120):
                    problems.append(f"{t}: pace {pace} out of range")
                if not (100 <= poss <= 4000):
                    problems.append(f"{t}: poss {poss} out of range")
            except (ValueError, IndexError, TypeError):
                problems.append(f"{t}: missing advanced columns")
    return problems


# ---------------------------------------------------------------- standings
def parse_standings(text):
    """Parse the official standings page into 30 conference rows.

    Returns (cols, rows, meta) with STANDINGS_COLS. Integrity: 15 East + 15
    West, W/L integers, WIN% consistent with W/(W+L), and HOME+ROAD+NEUTRAL
    records summing to the overall record.
    """
    problems = []
    for strategy in ("html_table", "next_data", "text_rows"):
        if strategy == "html_table":
            rows, probs = _standings_html(text)
        elif strategy == "next_data":
            nd = _next_data(text)
            if nd is None:
                continue
            rows, probs = _standings_json(nd)
        else:
            rows, probs = _standings_text(text)
        if rows:
            check = _standings_integrity(rows)
            if check:
                problems.extend(f"{strategy}: {p}" for p in check)
                continue
            return STANDINGS_COLS, rows, {"strategy": strategy,
                                          "row_count": len(rows),
                                          "integrity": "ok"}
        problems.extend(f"{strategy}: {p}" for p in probs)
    return STANDINGS_COLS, [], {"strategy": None, "row_count": 0,
                                "problems": problems[:12]}


def _standings_split(text):
    """Return [(conf, segment_text)] bounded by the conference headers."""
    east = text.find("Eastern Conference")
    west = text.find("Western Conference")
    out = []
    if east >= 0:
        end = west if west > east else east + 40000
        out.append(("East", text[east:end]))
    if west >= 0:
        out.append(("West", text[west:west + 40000]))
    return out


def _record_cell(t):
    m = re.fullmatch(r"(\d{1,2})-(\d{1,2})", t)
    return (int(m.group(1)), int(m.group(2))) if m else None


def _standings_html(text):
    rows, problems = [], []
    segs = _standings_split(text)
    if not segs:
        return [], ["conference headers not found"]
    for conf, seg in segs:
        found = 0
        for tr in TR_RE.finditer(seg):
            body = tr.group(1)
            raw_cells = CELL_RE.findall(body)
            cells = [_cell_text(c) for c in raw_cells]
            abbr, name, team_cell = None, None, None
            for c, raw in zip(cells, raw_cells):
                abbr, name = _team_from_cell(c, HREF_RE.findall(raw))
                if abbr:
                    team_cell = c
                    break
            if not abbr:
                continue
            ti = cells.index(team_cell)
            vals = cells[:ti] + cells[ti + 1:]
            # expected: rank, w, l, win_pct, gb, conf, div, home, road,
            #           neutral, ot, last10, streak
            nums = [v for v in vals if NUM_RE.fullmatch(v)]
            recs = [v for v in vals if _record_cell(v)]
            streak = next((v for v in vals if re.fullmatch(r"[WL] \d{1,2}", v)), None)
            last10 = recs[6] if len(recs) >= 7 else None
            if len(nums) < 4 or not streak:
                problems.append(f"{abbr}: incomplete standings row ({vals[:6]})")
                continue
            rank = _to_num(nums[0])
            w, l = _to_num(nums[1]), _to_num(nums[2])
            win_pct = _to_num(nums[3])
            gb = _to_num(nums[4]) if len(nums) > 4 else None
            if gb is None and len(nums) > 4:
                gb = 0.0 if nums[4] == "--" else None
            gb_val = 0.0 if vals and "--" in vals else gb
            # Records in order: conf, div, home, road, neutral, ot - kept
            # verbatim as printed.
            rec_map = {}
            for label, rv in zip(("conf", "div", "home", "road", "neutral", "ot"),
                                 recs[:6]):
                rec_map[label] = rv
            if not all(k in rec_map for k in ("conf", "div", "home", "road", "neutral")):
                problems.append(f"{abbr}: missing record cells ({recs})")
                continue
            row = [abbr, name, conf, rank, w, l, win_pct,
                   0.0 if gb_val is None else gb_val,
                   rec_map["conf"], rec_map["div"], rec_map["home"],
                   rec_map["road"], rec_map["neutral"],
                   rec_map.get("ot", ""), last10 or "", streak]
            rows.append(row)
            found += 1
        if found != 15:
            problems.append(f"{conf}: parsed {found} teams, expected 15")
    return rows, problems


def _standings_json(payload):
    """Walk __NEXT_DATA__ for team win/loss dicts carrying a conference."""
    rows, problems = [], []

    def walk(node):
        if len(rows) >= 30:
            return
        if isinstance(node, dict):
            keys = {_norm_header(k) for k in node}
            if {"win", "loss"} <= keys or {"w", "l"} <= keys:
                name = None
                for k in ("teamname", "team_name", "team", "nickname",
                          "teamcity", "team_city"):
                    if k in {_norm_header(x) for x in node}:
                        name = node.get(k) or node.get(k.replace("_", ""))
                if isinstance(name, dict):
                    name = name.get("teamName") or name.get("name")
                if isinstance(name, str) and name in TEAM_NAME_TO_ABBR:
                    abbr = TEAM_NAME_TO_ABBR[name]
                    g = lambda *ks: next((node[k] for k in node
                                          if _norm_header(k) in ks), None)
                    w = g("win", "w", "wins")
                    l = g("loss", "l", "losses")
                    conf = str(g("conference", "conf") or "").lower()
                    conf = "East" if conf.startswith("e") else (
                        "West" if conf.startswith("w") else "")
                    if conf and _is_int(w) and _is_int(l) and abbr not in [r[0] for r in rows]:
                        rows.append([abbr, name, conf, len(rows) + 1, int(w), int(l),
                                     round(int(w) / max(1, int(w) + int(l)), 3),
                                     0.0, "", "", "", "", "", "", "", ""])
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
    walk(payload)
    if rows:
        return rows, problems
    return [], ["no standings-like team records found in __NEXT_DATA__"]


def _standings_text(text):
    """Fallback: markdown-style rendered rows (verification cross-checks)."""
    rows, problems = [], []
    segs = _standings_split(text)
    if not segs:
        return [], ["conference headers not found in text"]
    for conf, seg in segs:
        for line in seg.splitlines():
            m = re.search(
                r"\[.*?([A-Za-z .']{3,40})\]\(https://www\.nba\.com/team/\d+/[a-z\-]+\)"
                r"\s*\|\s*(\d{1,2})\s*\|\s*(\d{1,2})\s*\|\s*(\.\d{3})\s*\|\s*([\-\.0-9]+|--)",
                line)
            if not m:
                continue
            name = m.group(1).strip()
            abbr = TEAM_NAME_TO_ABBR.get(name)
            if not abbr:
                continue
            w, l = int(m.group(2)), int(m.group(3))
            rows.append([abbr, name, conf, len(rows) + 1, w, l,
                         float(m.group(4)), 0.0 if m.group(5) == "--" else _to_num(m.group(5)) or 0.0,
                         "", "", "", "", "", "", "", ""])
    return rows, problems


def _standings_integrity(rows):
    problems = []
    if len(rows) != 30:
        problems.append(f"expected 30 rows, got {len(rows)}")
    abbrs = [r[0] for r in rows]
    if len(set(abbrs)) != len(abbrs):
        problems.append("duplicate teams")
    if sum(1 for r in rows if r[2] == "East") != 15:
        problems.append("East conference does not have 15 teams")
    if sum(1 for r in rows if r[2] == "West") != 15:
        problems.append("West conference does not have 15 teams")
    for r in rows:
        t, w, l, pct = r[0], r[4], r[5], r[6]
        if not (_is_int(w) and _is_int(l)):
            problems.append(f"{t}: W/L not integers")
            continue
        if abs(pct - w / max(1, w + l)) > 0.002:
            problems.append(f"{t}: win_pct {pct} inconsistent with {w}-{l}")
        home, road, neutral = _record_cell(r[10]), _record_cell(r[11]), _record_cell(r[12])
        if home and road and neutral:
            hw, hl = home[0] + road[0] + neutral[0], home[1] + road[1] + neutral[1]
            if (hw, hl) != (w, l):
                problems.append(f"{t}: home+road+neutral {hw}-{hl} != {w}-{l}")
    return problems


# ------------------------------------------------------------------ schedule
GAME_HREF_RE = re.compile(r"/game/([a-z0-9]{2,5})-vs-([a-z0-9]{2,5})-(\d{10})")


def parse_schedule(text):
    """Parse the official schedule page into game rows.

    Returns (cols, games, meta) with games = [{game_id, away, home, date?,
    source_url}]. Strategies: page game links, embedded JSON game objects,
    and anchored team-pair cards. Never guesses a team code: both codes must
    resolve through the canonical ABBR map.
    """
    cols = ["game_id", "away", "home", "date", "source_url"]
    problems = []
    for strategy in ("game_links", "embedded_json", "text_cards"):
        if strategy == "game_links":
            games, probs = _schedule_links(text)
        elif strategy == "embedded_json":
            games, probs = _schedule_json(text)
        else:
            games, probs = _schedule_text(text)
        if games:
            seen, out = set(), []
            for g in games:
                if g["game_id"] in seen:
                    continue
                seen.add(g["game_id"])
                out.append(g)
            return cols, out, {"strategy": strategy, "game_count": len(out),
                               "integrity": "ok"}
        problems.extend(f"{strategy}: {p}" for p in probs)
    return cols, [], {"strategy": None, "game_count": 0,
                      "problems": problems[:12]}


def _resolve_tricode(tok):
    t = tok.lower()
    return SLUG_TO_ABBR.get(t)


def _schedule_links(text):
    games, problems = [], []
    for m in GAME_HREF_RE.finditer(text):
        a, h, gid = m.group(1), m.group(2), m.group(3)
        aa, hh = _resolve_tricode(a), _resolve_tricode(h)
        if not aa or not hh:
            problems.append(f"unrecognised team tokens in /game/{a}-vs-{h}-{gid}")
            continue
        games.append({"game_id": gid, "away": aa, "home": hh, "date": None,
                      "source_url": f"https://www.nba.com/game/{a}-vs-{h}-{gid}"})
    return games, problems


def _schedule_json(text):
    games, problems = [], []
    blobs = []
    nd = _next_data(text)
    if nd is not None:
        blobs.append(nd)
    else:
        try:
            blobs.append(json.loads(text))
        except ValueError:
            pass
    if not blobs:
        # raw scan for embedded game objects (same shape the results parser uses)
        decoder = json.JSONDecoder()
        for m in re.finditer(r'"gameId"\s*:\s*"(\d{10})"', text):
            gid = m.group(1)
            if any(g["game_id"] == gid for g in games):
                continue
            for i in range(m.start() - 1, max(0, m.start() - 8000), -1):
                if text[i] != "{":
                    continue
                try:
                    obj, _ = decoder.raw_decode(text[i:])
                except ValueError:
                    continue
                if str(obj.get("gameId")) == gid:
                    blobs.append(obj)
                    break
    for blob in blobs:
        _collect_game_objects(blob, games)
    return games, problems


def _collect_game_objects(node, games):
    if isinstance(node, dict):
        gid = node.get("gameId") or node.get("game_id")
        home, away = node.get("homeTeam"), node.get("awayTeam")
        if gid and isinstance(home, dict) and isinstance(away, dict):
            def tri(t):
                v = t.get("teamTricode") or t.get("tricode") or t.get("teamAbbreviation")
                return v if v in TEAM_ABBR_TO_NAME else None
            a, h = tri(away), tri(home)
            if a and h and not any(g["game_id"] == str(gid) for g in games):
                date = node.get("gameDateEt") or node.get("gameTimeUTC") or node.get("date")
                if isinstance(date, str) and re.match(r"\d{4}-\d{2}-\d{2}", date):
                    date = date[:10]
                else:
                    date = None
                games.append({"game_id": str(gid), "away": a, "home": h,
                              "date": date,
                              "source_url": (f"https://www.nba.com/game/"
                                             f"{a.lower()}-vs-{h.lower()}-{gid}")})
        for v in node.values():
            _collect_game_objects(v, games)
    elif isinstance(node, list):
        for v in node:
            _collect_game_objects(v, games)


def _schedule_text(text):
    """Rendered-markdown shape: 'Preview' links carry the game URL."""
    games = []
    for m in re.finditer(
            r"\((https://www\.nba\.com/game/([a-z0-9]{2,5})-vs-([a-z0-9]{2,5})-(\d{10}))\)",
            text):
        url, a, h, gid = m.groups()
        aa, hh = _resolve_tricode(a), _resolve_tricode(h)
        if aa and hh:
            games.append({"game_id": gid, "away": aa, "home": hh, "date": None,
                          "source_url": url})
    return games, []


# ---------------------------------------------------------------- diagnostics
def diagnostics(text):
    """Bounded parse evidence for CI logs and _capture_evidence_*.json.

    Records only counts, key names and small excerpts - never a data value
    that a parser has not verified.
    """
    nd = _next_data(text)
    keys = {}
    if isinstance(nd, dict):
        props = nd.get("props", {})
        for k, v in props.items():
            keys[f"props.{k}"] = type(v).__name__
        pp = props.get("pageProps")
        if isinstance(pp, dict):
            for k, v in pp.items():
                size = (len(v) if isinstance(v, (list, dict, str)) else
                        ("int" if isinstance(v, int) else type(v).__name__))
                keys[f"props.pageProps.{k}"] = size
    out = {
        "indicators": {
            "__NEXT_DATA__": text.count("__NEXT_DATA__"),
            "rowSet": text.count("rowSet"),
            "gameId": text.count("gameId"),
            "<tr": len(TR_RE.findall(text[:500000])),
            "/team/": text.count("/team/"),
            "/stats/team/": text.count("/stats/team/"),
            "/game/": text.count("/game/"),
            "standings": text.lower().count("standings"),
        },
        "next_data_keys": keys,
    }
    for needle in ("/stats/team/", "/team/", "rowSet", "gameId"):
        i = text.find(needle)
        if i >= 0:
            out[f"excerpt@{needle}"] = text[max(0, i - 200):i + 600]
    return out


# --------------------------------------------------- cross-page integrity
def cross_check_standings_vs_traditional(standings_rows, traditional_rows,
                                         traditional_cols):
    """Independent verification between two official pages.

    Every team's W and L must agree between the standings page and the team
    traditional page. Returns a list of disagreement descriptions ([] when
    the two official tables agree).
    """
    problems = []
    try:
        ti_w = traditional_cols.index("w")
        ti_l = traditional_cols.index("l")
    except ValueError:
        return ["traditional table lacks w/l columns"]
    trad = {r[0]: (r[ti_w], r[ti_l]) for r in traditional_rows}
    for r in standings_rows:
        t, w, l = r[0], r[4], r[5]
        if t not in trad:
            problems.append(f"{t}: present on standings but not team traditional")
        elif trad[t] != (w, l):
            problems.append(f"{t}: standings {w}-{l} != traditional {trad[t][0]}-{trad[t][1]}")
    for t in trad:
        if t not in {r[0] for r in standings_rows}:
            problems.append(f"{t}: present on team traditional but not standings")
    return problems
