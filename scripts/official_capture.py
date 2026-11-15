#!/usr/bin/env python3
"""official_capture.py — fetch + parse the official NBA sources, with provenance.

    python3 scripts/official_capture.py              # full capture
    DEBUG_DUMP=1 python3 scripts/official_capture.py # also save raw bytes
    CAPTURE_DATES=2026-11-15,2026-11-16 python3 scripts/official_capture.py

WHY THIS RUNS IN CI
-------------------
The agent sandbox has no outbound network (curl to nba.com returns 000). GitHub
runners do, but only with the league's own web-client header set — proven by
`data/raw/probe_official.json` (`retried_with_browser_headers`: 9/14 refused URLs
answer 200 including `stats/teams/*`, `schedule`, `games?date=`, `game/<slug>`,
the injury index and the injury PDFs). A plain client gets 403.

DESIGN RULES, in order
----------------------
1. ONLY official hosts are contacted. The allowlist below is enforced before any
   request is made; a URL outside it is a hard error, never a silent fetch.
2. Every fetch records: exact URL, HTTP status, byte count, SHA-256 of the bytes,
   the UTC retrieval timestamp and the parser version that read it. That record
   IS the provenance; a value with no record is never published.
3. Nothing here overwrites a committed snapshot. Everything lands in
   `data/capture/<run_id>/` for the gate + verifier to promote.
4. A failed or empty parse is recorded as a FINDING, not patched over. A parser
   that returns 0 rows writes 0 rows and says so.
5. Exit code is always 0. A dead source is a finding, not a build failure.

Output layout (all under data/capture/<run_id>/):
    manifest.json      one record per fetch: url, status, bytes, sha256, fetched_at
    parsed/*.json      parser outputs
    injury_pdf/*.pdf   the injury PDF bytes, named by their own edition stamp
    _debug/*.html      raw HTML, ONLY when DEBUG_DUMP=1
"""

from __future__ import annotations

import datetime
import hashlib
import html as htmlmod
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import zlib
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAPTURE = os.path.join(ROOT, "data", "capture")

# ---------------------------------------------------------------- allowlist
# Only these hosts may ever be contacted. Enforced in fetch().
ALLOWED_HOSTS = {
    "www.nba.com",
    "official.nba.com",
    "ak-static.cms.nba.com",
    "cdn.nba.com",
}

# The header set proven by data/raw/probe_official.json to return 200 on
# www.nba.com / official.nba.com. Do not "simplify" these away.
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/pdf,application/json,*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nba.com/",
    "Origin": "https://www.nba.com",
    "x-nba-stats-origin": "stats",
    "x-nba-stats-token": "true",
    "Connection": "keep-alive",
}

SEASON = "2026-27"
SEASON_TYPE = "Regular+Season"

GAME_LINK_RE = re.compile(r"/game/([a-z]{3})-vs-([a-z]{3})-(\d{10})")
ABBR_RE = re.compile(r"\b(ATL|BOS|BKN|CHA|CHI|CLE|DAL|DEN|DET|GSW|HOU|IND|LAC|LAL|"
                     r"MEM|MIA|MIL|MIN|NOP|NYK|OKC|ORL|PHI|PHX|POR|SAC|SAS|TOR|UTA|WAS)\b")
TEAM_NAME_RE = re.compile(
    r"\b(Atlanta Hawks|Boston Celtics|Brooklyn Nets|Charlotte Hornets|Chicago Bulls|"
    r"Cleveland Cavaliers|Dallas Mavericks|Denver Nuggets|Detroit Pistons|"
    r"Golden State Warriors|Houston Rockets|Indiana Pacers|LA Clippers|"
    r"Los Angeles Lakers|Memphis Grizzlies|Miami Heat|Milwaukee Bucks|"
    r"Minnesota Timberwolves|New Orleans Pelicans|New York Knicks|"
    r"Oklahoma City Thunder|Orlando Magic|Philadelphia 76ers|Phoenix Suns|"
    r"Portland Trail Blazers|Sacramento Kings|San Antonio Spurs|Toronto Raptors|"
    r"Utah Jazz|Washington Wizards)\b")

NAME_TO_ABBR = {
    "Atlanta Hawks": "ATL", "Boston Celtics": "BOS", "Brooklyn Nets": "BKN",
    "Charlotte Hornets": "CHA", "Chicago Bulls": "CHI", "Cleveland Cavaliers": "CLE",
    "Dallas Mavericks": "DAL", "Denver Nuggets": "DEN", "Detroit Pistons": "DET",
    "Golden State Warriors": "GSW", "Houston Rockets": "HOU", "Indiana Pacers": "IND",
    "LA Clippers": "LAC", "Los Angeles Lakers": "LAL", "Memphis Grizzlies": "MEM",
    "Miami Heat": "MIA", "Milwaukee Bucks": "MIL", "Minnesota Timberwolves": "MIN",
    "New Orleans Pelicans": "NOP", "New York Knicks": "NYK",
    "Oklahoma City Thunder": "OKC", "Orlando Magic": "ORL",
    "Philadelphia 76ers": "PHI", "Phoenix Suns": "PHX",
    "Portland Trail Blazers": "POR", "Sacramento Kings": "SAC",
    "San Antonio Spurs": "SAS", "Toronto Raptors": "TOR",
    "Utah Jazz": "UTA", "Washington Wizards": "WAS",
}


def log(msg):
    print(f"[{datetime.datetime.now(datetime.timezone.utc):%H:%M:%S}] {msg}", flush=True)


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ------------------------------------------------------------------- fetching
class FetchRecord(dict):
    pass


def fetch(url, tries=3, sleep=4.0):
    """Fetch one allowed URL. Returns a provenance record (never raises)."""
    host = url.split("/")[2]
    rec = FetchRecord(url=url, host=host, allowed=host in ALLOWED_HOSTS,
                      http_status=None, bytes=0, sha256=None,
                      fetched_at_utc=utcnow(), error=None, data=None)
    if host not in ALLOWED_HOSTS:
        rec["error"] = f"host not on the official allowlist: {host}"
        log(f"  REFUSED (off-allowlist) {host}")
        return rec
    last = None
    for attempt in range(1, tries + 1):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=60) as fh:
                data = fh.read()
                rec["http_status"] = fh.status
                rec["bytes"] = len(data)
                rec["sha256"] = hashlib.sha256(data).hexdigest()
                rec["last_modified"] = fh.headers.get("Last-Modified")
                rec["content_type"] = fh.headers.get("Content-Type")
                rec["data"] = data
                log(f"  {fh.status} {len(data):>8}B  {url}")
                return rec
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            rec["http_status"] = e.code
        except Exception as e:                                   # noqa: BLE001
            last = f"{type(e).__name__}: {e}"
        if attempt < tries:
            time.sleep(sleep * attempt)
    rec["error"] = last
    log(f"  ERR {last}  {url}")
    return rec


# --------------------------------------------------------------- html helpers
class TableExtractor(HTMLParser):
    """Collect every <table> as a list of rows of cell text."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables = []
        self._t = None
        self._row = None
        self._cell = None

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self._t = []
        elif tag == "tr" and self._t is not None:
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._cell is not None:
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self._row:
                self._t.append(self._row)
            self._row = None
        elif tag == "table" and self._t is not None:
            self.tables.append(self._t)
            self._t = None

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)


def tables(html_text):
    p = TableExtractor()
    try:
        p.feed(html_text)
    except Exception:                                            # noqa: BLE001
        pass
    return p.tables


def text_of(html_text):
    """Tag-stripped, whitespace-normalised text (for regex over rendered copy)."""
    t = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", html_text)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    t = htmlmod.unescape(t)
    return re.sub(r"[ \t\xa0]+", " ", t)


def decode(data):
    for enc in ("utf-8", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", "replace")


# ---------------------------------------------------------------- pdf handling
def pdf_text(data):
    """Extract the text of an NBA injury PDF.

    Tries pypdf if it is installed; otherwise falls back to inflating the
    content streams with zlib and pulling the strings out of the Tj/TJ operators.
    The league's reports are machine-generated text PDFs, so the fallback is
    faithful enough to diff editions. Whatever happens, the exact bytes and their
    SHA-256 are stored beside the text, so the text can always be re-derived.
    """
    try:
        import io
        import pypdf                                             # noqa: PLC0415
        r = pypdf.PdfReader(io.BytesIO(data))
        return "\n".join((pg.extract_text() or "") for pg in r.pages)
    except Exception:                                            # noqa: BLE001
        pass
    out = []
    for m in re.finditer(rb"stream\r?\n", data):
        start = m.end()
        end = data.find(b"endstream", start)
        if end < 0:
            continue
        raw = data[start:end]
        try:
            dec = zlib.decompress(raw)
        except Exception:                                        # noqa: BLE001
            continue
        txt = []
        # (string) Tj  and  [(a) -1 (b)] TJ
        for tm in re.finditer(rb"\(((?:\\.|[^\\()])*)\)\s*Tj|\[((?:[^\[\]]|\\[\[\]])*)\]\s*TJ", dec):
            if tm.group(1) is not None:
                txt.append(tm.group(1))
            elif tm.group(2) is not None:
                for im in re.finditer(rb"\(((?:\\.|[^\\()])*)\)", tm.group(2)):
                    txt.append(im.group(1))
        if txt:
            out.append(b" ".join(txt).decode("latin-1"))
    s = "\n".join(out)
    s = (s.replace("\\(", "(").replace("\\)", ")").replace("\\\\", "\\"))
    return s


# -------------------------------------------------------------------- parsers
PARSER_VERSION = "2026-11-15.1"


NEXT_DATA_RE = re.compile(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S)


def next_data(html_text):
    """The JSON the page server-renders. Returns {} when the page has none.

    Why this is the parser's entry point: nba.com's /games and /game pages ship
    their data inside this blob. The standings and /stats pages do NOT - they
    hydrate from a client-side call - which is why this project reads per-game
    box scores (the primary source) instead of the summary tables.
    """
    m = NEXT_DATA_RE.search(html_text)
    if not m:
        return {}
    try:
        return json.loads(m.group(1))
    except Exception:                                            # noqa: BLE001
        return {}


def _periods(team):
    return [{"period": p.get("period"), "type": p.get("periodType"),
             "score": p.get("score")} for p in (team.get("periods") or [])]


def _qscores(team):
    """Quarter scores as a plain list, or None when the page prints none."""
    ps = team.get("periods") or []
    if not ps:
        return None
    return [p.get("score") for p in ps]


def _card_to_row(card, date, source_url):
    home = card.get("homeTeam") or {}
    away = card.get("awayTeam") or {}
    return {
        "date": date,
        "game_id": card.get("gameId"),
        "away": away.get("teamTricode"),
        "home": home.get("teamTricode"),
        "away_team_name": away.get("teamName"),
        "home_team_name": home.get("teamName"),
        "away_team_id": away.get("teamId"),
        "home_team_id": home.get("teamId"),
        "away_wins": away.get("wins"), "away_losses": away.get("losses"),
        "home_wins": home.get("wins"), "home_losses": home.get("losses"),
        "away_record": away.get("teamSubtitle"),
        "home_record": home.get("teamSubtitle"),
        "away_pts": away.get("score"), "home_pts": home.get("score"),
        "away_quarters": _qscores(away), "home_quarters": _qscores(home),
        "away_periods": _periods(away), "home_periods": _periods(home),
        "status_label": card.get("gameStatusText"),
        "game_status": card.get("gameStatus"),
        "period": card.get("period"),
        "tip_time_et": card.get("gameTimeEastern"),
        "tip_time_utc": card.get("gameTimeUtc"),
        "season_type": card.get("seasonType"),
        "game_url": card.get("shareUrl") or (
            f"https://www.nba.com/game/{str(away.get('teamSlug') or '')}-vs-"
            f"{str(home.get('teamSlug') or '')}-{card.get('gameId')}"),
        "source_url": source_url,
    }


def parse_games_page(html_text, date):
    """www.nba.com/games?date=<d>: every game card the page server-renders.

    Fields the page does not print stay None; nothing is inferred. Quarter
    scores come from the card's own `periods` array.
    """
    nd = next_data(html_text)
    src = f"https://www.nba.com/games?date={date}"
    cards, seen = [], set()
    try:
        modules = nd["props"]["pageProps"]["gameCardFeed"]["modules"]
    except Exception:                                            # noqa: BLE001
        modules = []
    for mod in modules or []:
        for c in (mod.get("cards") or []):
            cd = c.get("cardData") or {}
            gid = cd.get("gameId")
            if not gid or gid in seen:
                continue
            if cd.get("leagueId") not in (None, "00"):
                continue
            seen.add(gid)
            cards.append(_card_to_row(cd, date, src))
    return {"parser_version": PARSER_VERSION, "rows": cards, "row_count": len(cards),
            "source_url": src, "has_next_data": bool(nd)}


def parse_standings(html_text):
    """www.nba.com/standings — the 30 official rows, including HOME and ROAD splits.

    The home/road split is what pins home-court advantage to a MEASURED rate
    instead of a fitted one, so it is captured verbatim.
    """
    out = []
    for t in tables(html_text):
        header = None
        for row in t:
            cells = [c for c in row if c not in ("", "|")]
            if not cells:
                continue
            low = [c.lower() for c in cells]
            if "team" in low and "w" in low and "l" in low:
                header = low
                continue
            if header is None:
                continue
            try:
                i_team = header.index("team")
                i_w = header.index("w")
                i_l = header.index("l")
            except ValueError:
                continue
            tm = TEAM_NAME_RE.search(cells[i_team]) if i_team < len(cells) else None
            if not tm:
                continue

            def col(*names):
                for n in names:
                    if n in header:
                        j = header.index(n)
                        if j < len(cells):
                            return cells[j]
                return None

            out.append({
                "team": NAME_TO_ABBR[tm.group(1)],
                "team_name": tm.group(1),
                "w": int(cells[i_w]),
                "l": int(cells[i_l]),
                "win_pct": col("win%"),
                "gb": col("gb"),
                "conf": col("conf"),
                "home": col("home"),
                "road": col("road"),
                "last10": col("last10"),
                "streak": col("streak"),
                "source_url": "https://www.nba.com/standings",
            })
    # de-duplicate, keep first
    seen, rows = set(), []
    for r in out:
        if r["team"] in seen:
            continue
        seen.add(r["team"])
        rows.append(r)
    return {"parser_version": PARSER_VERSION, "rows": rows, "row_count": len(rows)}


def parse_stats_teams(html_text, source_url):
    """www.nba.com/stats/teams/{traditional,opponent,advanced} — the 30-row table."""
    best = None
    for t in tables(html_text):
        header = None
        rows = []
        for row in t:
            cells = [c for c in row if c not in ("", "|")]
            if not cells:
                continue
            low = [c.lower() for c in cells]
            if "team" in low and "gp" in low:
                header = [c for c in cells]
                continue
            if header is None:
                continue
            tm = TEAM_NAME_RE.search(cells[0]) if cells else None
            if not tm:
                continue
            rows.append([NAME_TO_ABBR[tm.group(1)]] + cells[1:])
        if header and len(rows) >= 25:
            # drop the trailing "RANK" columns - they are duplicates of the values
            keep = [i for i, h in enumerate(header) if "rank" not in h.lower()]
            hdr = ["TEAM"] + [header[i] for i in keep if i > 0]
            rws = []
            for r in rows:
                rws.append([r[0]] + [r[i] if i < len(r) else "" for i in keep if i > 0])
            best = {"parser_version": PARSER_VERSION, "source_url": source_url,
                    "columns": hdr, "rows": rws, "row_count": len(rws)}
            break
    if best is None:
        return {"parser_version": PARSER_VERSION, "source_url": source_url,
                "columns": [], "rows": [], "row_count": 0,
                "finding": "no 30-row team table found in the rendered HTML"}
    return best


def parse_injury_index(html_text):
    """official.nba.com injury hub — every published PDF edition for each day."""
    out = []
    for m in re.finditer(
            r'href="(https://ak-static\.cms\.nba\.com/referee/injury/'
            r'Injury-Report_(\d{4})-(\d{2})-(\d{2})_(\d{2})_(\d{2})(AM|PM)\.pdf)"',
            html_text):
        url = m.group(1)
        hh, mm, ap = int(m.group(5)), m.group(6), m.group(7)
        out.append({
            "url": url,
            "date": f"{m.group(2)}-{m.group(3)}-{m.group(4)}",
            "edition_label": f"{hh}:{mm} {ap} ET",
            "edition_hour24": (hh % 12) + (12 if ap == "PM" else 0),
            "edition_minute": int(mm),
            "file": url.rsplit("/", 1)[-1],
        })
    seen, rows = set(), []
    for r in sorted(out, key=lambda r: (r["date"], r["edition_hour24"], r["edition_minute"])):
        if r["url"] in seen:
            continue
        seen.add(r["url"])
        rows.append(r)
    return {"parser_version": PARSER_VERSION,
            "source_url": "https://official.nba.com/nba-injury-report-2026-27-season/",
            "editions": rows, "edition_count": len(rows)}


STATUS_WORDS = ("Out", "Doubtful", "Questionable", "Probable", "Available")
STATUS_RE = re.compile(r"\b(Out|Doubtful|Questionable|Probable|Available)\b")
# The league prints every player as "Last, First" in the PDF.
PLAYER_RE = re.compile(
    r"([A-Z][A-Za-z'\-]*[A-Za-z],\s+[A-Z][A-Za-z'.\-]+(?:\s+[A-Z][A-Za-z'.\-]+)*?)"
    r"(?=\s+(?:Out|Doubtful|Questionable|Probable|Available)\b)")
# Each game block opens with  <time> (ET) AWAY@HOME. The date is printed only on
# the first line of each page, so it is optional and carried forward.
GAME_BLOCK_RE = re.compile(
    r"(?:(\d{2}/\d{2}/\d{4})\s+)?(\d{1,2}:\d{2})\s*\(ET\)\s+([A-Z]{3}@[A-Z]{3})")
# The league's own revision stamp, printed in the page header.
REVISION_RE = re.compile(r"Injury\s+Report:\s*(\d{2}/\d{2}/\d{2})\s+(\d{1,2}:\d{2})\s*(AM|PM)", re.I)


def parse_injury_pdf(text):
    """The league PDF: one row per player — game, team, player, status, reason.

    The PDF's text layer arrives as one token per line, so the tokens are
    rejoined first and then segmented on the structures the league actually
    prints: a game block header (`<date> <time> (ET) AWAY@HOME`), a club name from
    the official 30-club list, a player printed as `Last, First`, and one of the
    five official status words. Anything the PDF does not print is left null.

    The league's own revision stamp (`Injury Report: <date> <time>`) is returned
    separately from the retrieval time — they are different facts and the site
    shows both.
    """
    joined = re.sub(r"\s+", " ", text)
    joined = re.sub(r"Page \d+ of \d+", " ", joined)
    rev = None
    mr = REVISION_RE.search(joined)
    if mr:
        rev = f"{mr.group(1)} {mr.group(2)} {mr.group(3).upper()} ET"

    blocks = []
    gs = list(GAME_BLOCK_RE.finditer(joined))
    last_date = None
    for i, g in enumerate(gs):
        start = g.end()
        end = gs[i + 1].start() if i + 1 < len(gs) else len(joined)
        last_date = g.group(1) or last_date
        blocks.append({"game_date": last_date, "game_time_et": g.group(2) + " (ET)",
                       "matchup": g.group(3), "body": joined[start:end]})

    rows = []
    for b in blocks:
        body = b["body"]
        # locate the club segments inside this game block
        clubs = [(m.start(), m.end(), m.group(1)) for m in TEAM_NAME_RE.finditer(body)]
        for ci, (c_start, c_end, club) in enumerate(clubs):
            c_end2 = clubs[ci + 1][0] if ci + 1 < len(clubs) else len(body)
            seg = body[c_end:c_end2]
            players = list(PLAYER_RE.finditer(seg))
            for pi, pm in enumerate(players):
                p_end = players[pi + 1].start() if pi + 1 < len(players) else len(seg)
                tail = seg[pm.end():p_end].strip()
                ms = STATUS_RE.search(tail)
                status = ms.group(1) if ms else None
                reason = tail[ms.end():].strip() if ms else (tail or None)
                reason = re.sub(r"^Injury/Illness\s*-\s*", "", reason or "").strip() or None
                # the page header of the next page can trail the last row
                reason = re.sub(r"\s*Injury\s+Report:.*$", "", reason or "").strip() or None
                rows.append({
                    "game_date": b["game_date"],
                    "game_time_et": b["game_time_et"],
                    "matchup": b["matchup"],
                    "team_name": club,
                    "team": NAME_TO_ABBR[club],
                    "player": re.sub(r"\s+", " ", pm.group(1)).strip(),
                    "status": status,
                    "reason": reason,
                })
    return {"parser_version": PARSER_VERSION, "rows": rows, "row_count": len(rows),
            "revision_stamp_et": rev, "game_blocks": len(blocks)}


def parse_game_page(html_text, gid):
    """www.nba.com/game/<slug>: the official box score for one game.

    This is the richest official artefact in the project. It prints, per team:
    the team box score (everything the possession model needs), the period
    scores, every player's minutes / points / rebounds / assists, the starters,
    the bench and the inactives; and per game: the arena, the attendance, the
    neutral-site flag, the tip time and the officials.
    """
    nd = next_data(html_text)
    g = {}
    try:
        g = nd["props"]["pageProps"]["game"]
    except Exception:                                            # noqa: BLE001
        g = {}
    out = {"game_id": gid, "parser_version": PARSER_VERSION, "has_next_data": bool(nd)}
    if not g:
        return out
    ar = g.get("arena") or {}
    out.update({
        "status_label": g.get("gameStatusText"),
        "game_status": g.get("gameStatus"),
        "period": g.get("period"),
        "tip_time_utc": g.get("gameTimeUTC"),
        "tip_time_et": g.get("gameEt"),
        "neutral": g.get("isNeutral"),
        "attendance": g.get("attendance"),
        "arena_name": ar.get("arenaName"),
        "arena_city": ar.get("arenaCity"),
        "arena_state": ar.get("arenaState"),
        "arena_country": ar.get("arenaCountry"),
        "game_label": g.get("gameLabel"),
        "game_sub_label": g.get("gameSubLabel"),
        "officials": [o.get("name") for o in (g.get("officials") or [])],
    })
    for side in ("awayTeam", "homeTeam"):
        t = g.get(side) or {}
        key = "away" if side == "awayTeam" else "home"
        st = t.get("statistics") or {}
        out[key] = t.get("teamTricode")
        out[f"{key}_team_id"] = t.get("teamId")
        out[f"{key}_pts"] = t.get("score")
        out[f"{key}_wins"] = t.get("teamWins")
        out[f"{key}_losses"] = t.get("teamLosses")
        out[f"{key}_quarters"] = _qscores(t)
        out[f"{key}_stats"] = st
        players = []
        for p in (t.get("players") or []):
            ps = p.get("statistics") or {}
            players.append({
                "person_id": p.get("personId"),
                "name": f"{p.get('firstName','')} {p.get('familyName','')}".strip(),
                "slug": p.get("playerSlug"),
                "position": p.get("position"),
                "min": ps.get("minutes"),
                "pts": ps.get("points"),
                "reb": ps.get("reboundsTotal"),
                "ast": ps.get("assists"),
                "fgm": ps.get("fieldGoalsMade"),
                "fga": ps.get("fieldGoalsAttempted"),
                "fg3m": ps.get("threePointersMade"),
                "fg3a": ps.get("threePointersAttempted"),
                "ftm": ps.get("freeThrowsMade"),
                "fta": ps.get("freeThrowsAttempted"),
                "oreb": ps.get("reboundsOffensive"),
                "dreb": ps.get("reboundsDefensive"),
                "tov": ps.get("turnovers"),
                "stl": ps.get("steals"),
                "blk": ps.get("blocks"),
                "pf": ps.get("foulsPersonal"),
                "plus_minus": ps.get("plusMinusPoints"),
            })
        out[f"{key}_players"] = players
        out[f"{key}_inactives"] = [
            {"person_id": p.get("personId"),
             "name": f"{p.get('firstName','')} {p.get('familyName','')}".strip()}
            for p in (t.get("inactives") or [])]
    return out


def parse_player_gamelog(html_text, player_id):
    """www.nba.com/player/<id>/... game log — one row per game played."""
    rows = []
    for t_ in tables(html_text):
        header = None
        for row in t_:
            cells = [c for c in row if c not in ("", "|")]
            if not cells:
                continue
            low = [c.lower() for c in cells]
            if any(k in low for k in ("min", "pts")) and any(
                    k in low for k in ("reb", "ast")):
                header = low
                continue
            if header is None:
                continue
            try:
                i_min = next(i for i, h in enumerate(header) if h.startswith("min"))
                i_pts = next(i for i, h in enumerate(header) if h.startswith("pts"))
                i_reb = next(i for i, h in enumerate(header) if h.startswith("reb"))
                i_ast = next(i for i, h in enumerate(header) if h.startswith("ast"))
            except StopIteration:
                continue

            def val(i):
                return cells[i] if i < len(cells) else None

            rows.append({"player_id": str(player_id), "min": val(i_min), "pts": val(i_pts),
                         "reb": val(i_reb), "ast": val(i_ast),
                         "opponent": val(1) if len(cells) > 1 else None})
    return {"parser_version": PARSER_VERSION, "player_id": str(player_id),
            "rows": rows, "row_count": len(rows)}


# ---------------------------------------------------------------------- main
def main():
    today = os.environ.get("CAPTURE_TODAY") or \
        datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    dates = os.environ.get("CAPTURE_DATES")
    if dates:
        slate_dates = [d.strip() for d in dates.split(",") if d.strip()]
    else:
        d0 = datetime.date.fromisoformat(today)
        slate_dates = [(d0 + datetime.timedelta(days=i)).isoformat() for i in range(0, 4)]
    horizon_end = slate_dates[-1]
    season_start = os.environ.get("SEASON_START", "2026-10-20")
    # every league day from the season opener to the end of the horizon
    d0 = datetime.date.fromisoformat(season_start)
    d1 = datetime.date.fromisoformat(horizon_end)
    all_dates = [(d0 + datetime.timedelta(days=i)).isoformat()
                 for i in range((d1 - d0).days + 1)]
    result_dates = [d for d in all_dates if d < slate_dates[0]]
    debug = os.environ.get("DEBUG_DUMP") == "1"
    only = set(x.strip() for x in os.environ.get("DEBUG_ONLY", "").split(",") if x.strip())
    wanted = (lambda s: (not only) or (s in only))

    run_id = os.environ.get("RUN_ID") or \
        datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    run_dir = os.path.join(CAPTURE, run_id)
    parsed_dir = os.path.join(run_dir, "parsed")
    pdf_dir = os.path.join(run_dir, "injury_pdf")
    dbg_dir = os.path.join(run_dir, "_debug")
    for d in (parsed_dir, pdf_dir, dbg_dir):
        os.makedirs(d, exist_ok=True)

    manifest = {
        "run_id": run_id,
        "created_at_utc": utcnow(),
        "season": SEASON,
        "season_start": season_start,
        "slate_dates": slate_dates,
        "result_dates": result_dates,
        "all_dates": all_dates,
        "allowed_hosts": sorted(ALLOWED_HOSTS),
        "parser_version": PARSER_VERSION,
        "fetches": [],
        "findings": [],
    }

    def save(name, obj):
        with open(os.path.join(parsed_dir, name), "w", encoding="utf-8") as fh:
            json.dump(obj, fh, indent=1)
        return obj

    def record(rec, parser=None, out=None):
        if rec is None:
            return None
        r = {k: v for k, v in rec.items() if k != "data"}
        if parser:
            r["parser"] = parser
        if out is not None:
            r["parsed_rows"] = out.get("row_count") if isinstance(out, dict) else None
        manifest["fetches"].append(r)
        return r

    # ---- 1. every league day: the official schedule / result card ---------
    games = {}
    for d in all_dates:
        if not wanted("games"):
            break
        url = f"https://www.nba.com/games?date={d}"
        rec = fetch(url)
        if rec.get("data"):
            if debug:
                open(os.path.join(dbg_dir, f"games_{d}.html"), "wb").write(rec["data"])
            p = parse_games_page(decode(rec["data"]), d)
            save(f"games_{d}.json", p)
            games[d] = p
            record(rec, "parse_games_page", p)
        else:
            record(rec, "parse_games_page")
            manifest["findings"].append(
                {"level": "error", "detail": f"games?date={d} not captured: "
                 f"{rec.get('error') or rec.get('http_status')}"})
    if games:
        manifest["findings"].append(
            {"level": "info", "detail": "cards per date: " + ", ".join(
                f"{d[-5:]}:{len(g['rows'])}" for d, g in sorted(games.items()))})

    # ---- 2. standings (page fetches 200; it publishes no table in its HTML)
    rec = fetch("https://www.nba.com/standings") if wanted("standings") else None
    if rec and rec.get("data"):
        if debug:
            open(os.path.join(dbg_dir, "standings.html"), "wb").write(rec["data"])
        p = parse_standings(decode(rec["data"]))
        save("standings.json", p)
        record(rec, "parse_standings", p)
        manifest["findings"].append(
            {"level": "error" if p["row_count"] != 30 else "info",
             "detail": f"standings page fetched ({rec['bytes']}B) but publishes "
                       f"{p['row_count']} table rows in its HTML: the table is hydrated "
                       f"client-side. Standings are therefore derived from official "
                       f"per-game results and cross-checked, never transcribed blind."})

    # ---- 3. the three official team-stat pages (same finding) -------------
    for slug in (("traditional", "opponent", "advanced") if wanted("teams") else ()):
        url = (f"https://www.nba.com/stats/teams/{slug}?Season={SEASON}"
               f"&SeasonType={SEASON_TYPE}")
        rec = fetch(url)
        if rec and rec.get("data"):
            if debug:
                open(os.path.join(dbg_dir, f"teams_{slug}.html"), "wb").write(rec["data"])
            p = parse_stats_teams(decode(rec["data"]), url)
            save(f"teams_{slug}.json", p)
            record(rec, "parse_stats_teams", p)
            manifest["findings"].append(
                {"level": "error" if p["row_count"] != 30 else "info",
                 "detail": f"teams/{slug} fetched ({rec['bytes']}B) but publishes "
                           f"{p['row_count']} table rows in its HTML (client-side "
                           f"hydration). Model inputs are re-cut from the official "
                           f"per-game box scores instead - the primary source."})
        else:
            record(rec, "parse_stats_teams")

    # ---- 4. players traditional (same finding) ----------------------------
    url = (f"https://www.nba.com/stats/players/traditional?Season={SEASON}"
           f"&SeasonType={SEASON_TYPE}")
    rec = fetch(url) if wanted("players") else None
    if rec and rec.get("data"):
        p = parse_stats_teams(decode(rec["data"]), url)
        save("players_traditional.json", p)
        record(rec, "parse_stats_teams", p)

    # ---- 5. injury index ---------------------------------------------------
    rec = fetch("https://official.nba.com/nba-injury-report-2026-27-season/") if wanted("injury") else None
    editions = []
    if rec and rec.get("data"):
        if debug:
            open(os.path.join(dbg_dir, "injury_index.html"), "wb").write(rec["data"])
        p = parse_injury_index(decode(rec["data"]))
        save("injury_index.json", p)
        record(rec, "parse_injury_index", p)
        editions = p["editions"]
        manifest["findings"].append(
            {"level": "info", "detail": f"injury index: {len(editions)} PDF editions published"})
    else:
        record(rec, "parse_injury_index")

    # ---- 6. injury PDFs ----------------------------------------------------
    # Every edition published for the slate window, newest last, plus the last
    # edition of each previous league day so consecutive diffs are possible.
    want = []
    by_date = {}
    for e in editions:
        by_date.setdefault(e["date"], []).append(e)
    for d in sorted(set(result_dates) | set(slate_dates)):
        for e in by_date.get(d, []):
            want.append(e)
    want = want[-60:]
    if debug:
        want = want[-6:]
    pdf_rows = []
    # The league republishes the same report under a new timestamp many times a
    # day. Every edition is FETCHED and every edition's own SHA-256, URL and
    # retrieval time are recorded; the bytes are archived once per distinct
    # report (plus always the newest), so the archive stays complete without
    # storing the same bytes dozens of times.
    seen_content = set()
    for idx, e in enumerate(want if wanted("injury") else []):
        rec = fetch(e["url"])
        if not rec.get("data"):
            record(rec, "parse_injury_pdf")
            continue
        fn = e["file"]
        txt = pdf_text(rec["data"])
        p = parse_injury_pdf(txt)
        content_sha = hashlib.sha256(json.dumps(p["rows"], sort_keys=True).encode()).hexdigest()
        keep = (content_sha not in seen_content) or (idx == len(want) - 1)
        seen_content.add(content_sha)
        if keep:
            with open(os.path.join(pdf_dir, fn), "wb") as fh:
                fh.write(rec["data"])
            with open(os.path.join(pdf_dir, fn + ".txt"), "w", encoding="utf-8") as fh:
                fh.write(txt)
        p["content_sha256"] = content_sha
        p["duplicate_of"] = None if keep else "an earlier edition with identical content"

        p.update({"edition_url": e["url"], "edition_label": e["edition_label"],
                  "edition_date": e["date"],
                  "pdf_sha256": rec["sha256"], "pdf_bytes": rec["bytes"],
                  "pdf_archived": bool(keep),
                  "pdf_stored_path": (f"data/capture/{run_id}/injury_pdf/{fn}" if keep else None),
                  "http_last_modified": rec.get("last_modified"),
                  "retrieved_at_utc": rec["fetched_at_utc"]})
        pdf_rows.append(p)
        rec["stored_path"] = f"data/capture/{run_id}/injury_pdf/{fn}" if keep else None
        record(rec, "parse_injury_pdf", p)
    if pdf_rows:
        save("injury_pdfs.json", {"parser_version": PARSER_VERSION,
                                  "editions": pdf_rows, "edition_count": len(pdf_rows)})
        manifest["findings"].append(
            {"level": "info", "detail": f"{len(pdf_rows)} injury PDF editions archived "
             f"({sum(p['row_count'] for p in pdf_rows)} player-rows parsed)"})

    # ---- 7. box scores for every completed game ---------------------------
    # One row per finished game: date, teams, final, quarter scores, both team
    # box scores (the possession model's inputs) and every player's line.
    played = []
    for d in sorted(games):
        for r in games[d]["rows"]:
            if (r.get("status_label") or "").lower().startswith("final"):
                played.append((d, r))
    if debug:
        played = played[:2]
    box = []
    for d, r in (played if wanted("gamepages") else []):
        url = r["game_url"]
        rec = fetch(url)
        if not rec.get("data"):
            record(rec, "parse_game_page")
            continue
        if debug:
            open(os.path.join(dbg_dir, f"game_{r['game_id']}.html"), "wb").write(rec["data"])
        p = parse_game_page(decode(rec["data"]), r["game_id"])
        p.update({"date": d, "game_url": url, "page_sha256": rec["sha256"],
                  "retrieved_at_utc": rec["fetched_at_utc"],
                  "away": r["away"], "home": r["home"],
                  "away_pts_card": r["away_pts"], "home_pts_card": r["home_pts"]})
        box.append(p)
        record(rec, "parse_game_page", p)
    if box:
        save("boxscores.json", {"parser_version": PARSER_VERSION, "rows": box,
                                "row_count": len(box)})
        manifest["findings"].append(
            {"level": "info", "detail": f"{len(box)} official box scores captured; "
             f"{sum(1 for b in box if b.get('away_quarters') and b.get('home_quarters'))} "
             f"carry quarter scores for both teams"})

    # ---- 8. URL probe (structure discovery, recorded not assumed) ---------
    probes = []
    if os.environ.get("PROBE_URLS") and wanted("probe"):
        for u in [x for x in os.environ["PROBE_URLS"].split("|") if x]:
            rec = fetch(u, tries=1)
            body = ""
            if rec.get("data"):
                body = text_of(decode(rec["data"]))[:600]
            probes.append({"url": u, "http_status": rec["http_status"],
                           "bytes": rec["bytes"], "error": rec.get("error"),
                           "text_head": body})
            record(rec, "probe")
        save("url_probe.json", {"probes": probes})

    manifest["finished_at_utc"] = utcnow()
    with open(os.path.join(run_dir, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1)
    with open(os.path.join(CAPTURE, "LATEST"), "w", encoding="utf-8") as fh:
        fh.write(run_id)
    log(f"run {run_id}: {len(manifest['fetches'])} fetches, "
        f"{len(manifest['findings'])} findings")
    for f in manifest["findings"]:
        log(f"  [{f['level']}] {f['detail']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
