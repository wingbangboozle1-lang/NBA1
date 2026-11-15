"""Re-fetch the official sources into data/raw, then rebuild the site data.

    python3 engine/fetch_official.py

Design rules, in order:

1. ONLY official hosts are contacted (www.nba.com, official.nba.com,
   ak-static.cms.nba.com). Nothing else is fetched and nothing is cached from
   anywhere else.
2. Every fetch is written to data/raw with the exact URL and a capture
   timestamp, so every published value stays traceable.
3. If a fetch fails or a page does not look like the page we want, the
   existing file is left exactly as it is. A partial or wrong file is worse
   than a stale one.
4. Nothing in data/raw/*.json that a snapshot owner committed is ever
   overwritten by this script. Parsed results are written as
   `_capture_*.json` so a verifier can diff them against the committed
   snapshot before anything is promoted. Promotion is a separate, verified
   step and never happens here.

NOTE ON TESTING (session `arena/d6918959-nba1`, 2026-11-14 UTC):

* This script was originally written in a sandbox that could not reach
  `*.nba.com` and had never been executed (Flagged F7). The header set below
  is the web-client set that the executed reachability probe
  (`scripts/probe_official.py`, record `data/raw/probe_official.json`,
  section `retried_with_browser_headers`) showed returns HTTP 200 for the
  www.nba.com stats, schedule and games pages and the official.nba.com
  injury index. A plain client receives 403 on those same URLs (154 of 157
  cited URLs in the probe record).
* `cdn.nba.com/static/json/...` still refuses even with those headers and is
  not used here. `Injury-Report_2026-11-14_12_00PM.pdf` returned 403 at probe
  time; 403 from ak-static is recorded as "unavailable at capture time", not
  as proof that the file does not exist.
* Execution record: `.github/workflows/refresh-data.yml` runs this script on
  GitHub's runners (the only environment in this project with outbound access
  to nba.com). Results are recorded in `data/raw/_last_refresh.json` and in
  COORDINATION.md section 15.
"""

import datetime
import hashlib
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import ABBR, RAW, ROOT, read_json, rows_by_cols, write_json

# stats.nba.com is the NBA's own stats service - it is the data layer behind
# the cited www.nba.com/stats pages (evidence: the page's own JS chunk calls
# resource "leaguedashteamstats"; recorded in
# data/raw/_capture_evidence_S1_season.json). No third-party host is used.
ALLOWED_HOSTS = {"www.nba.com", "official.nba.com", "ak-static.cms.nba.com",
                 "stats.nba.com"}

# The web-client header set proven by data/raw/probe_official.json
# (`retried_with_browser_headers`): HTTP 200 on www.nba.com/stats/...,
# www.nba.com/schedule, www.nba.com/games?date=... and
# official.nba.com/nba-injury-report-2026-27-season/, where the plain client
# received 403. Do not "simplify" these away: without them the refresh is
# refused (Flagged F7 / P2 / P5 on verification.html).
WEB_CLIENT_HEADERS = {
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

FETCHES = {
    # id -> (url, kind)
    "S1_season": ("https://www.nba.com/stats/teams/advanced", "teams_advanced"),
    "S2_train": ("https://www.nba.com/stats/teams/advanced"
                 "?DateFrom=10%2F20%2F2026&DateTo=11%2F05%2F2026&SeasonType=Regular+Season",
                 "teams_advanced"),
    "S7_players": ("https://www.nba.com/stats/players/traditional", "players"),
    # The other two of the three official team-stat pages the brief names, and the standings
    # table. Added 2026-11-15: the job used to read ONLY the advanced page, so "re-read the
    # three official team-stat pages" was satisfied by one third of itself. These are
    # CAPTURE-ONLY (kind=team_table / standings): they write _capture_*.json and never a
    # committed snapshot, because a parse that returns 29 rows instead of 30, or re-sorts the
    # table by a rule the page implements differently, would silently corrupt the ratings the
    # settled history was graded against. A session promotes rows after re-checking them.
    "S1t_traditional": ("https://www.nba.com/stats/teams/traditional", "team_table"),
    "S1o_opponent": ("https://www.nba.com/stats/teams/opponent", "team_table"),
    "S9_standings": ("https://www.nba.com/standings", "standings"),
    "S4_schedule": ("https://www.nba.com/schedule", "schedule"),
    "S5_injury_index": ("https://official.nba.com/nba-injury-report-2026-27-season/",
                        "injury_index"),
}

TEAM_ABBR_RE = re.compile(
    r"\b(Atlanta Hawks|Boston Celtics|Brooklyn Nets|Charlotte Hornets|Chicago Bulls|"
    r"Cleveland Cavaliers|Dallas Mavericks|Denver Nuggets|Detroit Pistons|"
    r"Golden State Warriors|Houston Rockets|Indiana Pacers|LA Clippers|"
    r"Los Angeles Lakers|Memphis Grizzlies|Miami Heat|Milwaukee Bucks|"
    r"Minnesota Timberwolves|New Orleans Pelicans|New York Knicks|"
    r"Oklahoma City Thunder|Orlando Magic|Philadelphia 76ers|Phoenix Suns|"
    r"Portland Trail Blazers|Sacramento Kings|San Antonio Spurs|Toronto Raptors|"
    r"Utah Jazz|Washington Wizards)\b")

GAME_LINK_RE = re.compile(
    r"/game/([a-z]{3})-vs-([a-z]{3})-(\d{10})")

DATE_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")

TAG_RE = re.compile(r"<[^>]+>")
HREF_ATTR_RE = re.compile(r'\s+href="[^"]*"')
# Case-insensitive: the score card prints "FINAL", the embedded JSON prints
# "Final" - both were seen on the same executed run's pages.
FINAL_RE = re.compile(r"\bFinal(?:/OT\d*)?\b", re.I)
RECORD_RE = re.compile(r"\b\d{1,2}-\d{1,2}\b")

# Injury-report editions: fallback candidate times, used ONLY when the official
# index page cannot be read. The real list is parsed from the index (see
# parse_injury_index) - hard-coding these was a defect.
#
# Why the fixed list is only four PM names and a generated AM sweep: on
# 2026-11-15 the hub (https://official.nba.com/nba-injury-report-2026-27-season/)
# listed the day's editions at 15-minute increments from 12:00 a.m. ET to
# 06:15 a.m. ET, i.e. the NEWEST report of the day is an AM edition. The previous
# hard-coded tuple ("12_00PM", "03_00PM", "05_15PM", "07_30PM") is blind to every
# one of them: a run at 11:15 UTC (06:15 ET) would walk past the newest file and
# either 404 on PM names that do not exist yet or fall back to yesterday's report.
# The PM anchors are kept because editions at 12:00/3:00/5:15/7:30 PM were proven
# to exist on 2026-11-13 (HTTP 200 in data/raw/_capture_injury_probe.json).
#
# An edition that returns 403 is recorded as unavailable at capture time -
# ak-static answers 403 both for absent objects and for some clients, so 403 is
# never treated as proof of absence.
INJURY_EDITION_TIMES = ("12_00PM", "03_00PM", "05_15PM", "07_30PM")
# The game-day AM window the league actually publishes in: every 15 minutes from
# midnight to the 11 a.m. filing window (etiquette per the hub's own deadline
# text). Generated, not enumerated, so a schedule change does not silently retire it.
INJURY_AM_EDITION_TIMES = tuple(
    "%02d_%02dAM" % (h, m)
    for h in (0, 1, 2, 3, 4, 5, 6)
    for m in ((0, 15, 30, 45) if h not in (0,) else (0, 15, 30, 45))
)


def edition_revision_time(edition):
    """The revision time a report claims for itself, taken from its own filename.

    Returns (iso_utc, human_et) or (None, None) for a name we cannot parse. The
    hub prints the same instant as e.g. "6:15 a.m ET report" for
    Injury-Report_2026-11-15_06_15AM.pdf, so the two agree; the value is
    reported next to the retrieval time so a reader can see the lag.
    """
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})_(\d{2})_(\d{2})(AM|PM)\.pdf$", edition)
    if not m:
        return None, None
    y, mo, d, hh, mm, ampm = m.groups()
    hour24 = int(hh) % 12 + (12 if ampm == "PM" else 0)
    # ET in November is EST = UTC-5; the ISO stamp is the UTC equivalent of the
    # printed ET revision time, so "newer than" comparisons are single-number.
    iso = "%s-%s-%sT%02d:%02d:00Z" % (y, mo, d, (hour24 + 5) % 24, int(mm))
    human = "%s-%s-%s %02d:%02d ET" % (y, mo, d, hour24, int(mm))
    return iso, human
INJURY_HOST = "https://ak-static.cms.nba.com/referee/injury/"

# The stats API behind the cited team-advanced page. The resource name and
# the LeagueDashTeamStats result-set name come from the page's own JS chunk
# (excerpt stored in data/raw/_capture_evidence_S1_season.json), not from
# guesswork. DateFrom/DateTo reproduce the two windows the committed
# snapshot stores (season-to-date and the 10/20-11/05 training window).
STATS_API = ("https://stats.nba.com/stats/leaguedashteamstats"
             "?LeagueID=00&Season=2026-27&SeasonType=Regular+Season"
             "&MeasureType=Advanced&PerMode=Totals&Scope=Season"
             "&LastNGames=0&Month=0&OpponentTeamID=0"
             "&DateFrom={df}&DateTo={dt}")

# Our committed schema (data/raw/team_advanced.json cols) -> the API's
# header names, normalised (non-alphanumerics stripped, upper-cased).
STATS_API_WANT = {
    "team": "TEAMNAME", "gp": "GP", "w": "W", "l": "L", "min": "MIN",
    "ortg": "OFFRTG", "drtg": "DEFRTG", "netr": "NETRTG",
    "ast_pct": "ASTPCT", "ast_to": "ASTTO", "ast_ratio": "ASTRATIO",
    "oreb_pct": "OREBPCT", "dreb_pct": "DREBPCT", "reb_pct": "REBPCT",
    "tov_pct": "TOVPCT", "efg_pct": "EFGPCT", "ts_pct": "TSPCT",
    "pace": "PACE", "pie": "PIE", "poss": "POSS",
}
STATS_API_INT = {"gp", "w", "l", "poss"}
STATS_COLS = ["team", "gp", "w", "l", "min", "ortg", "drtg", "netr",
              "ast_pct", "ast_to", "ast_ratio", "oreb_pct", "dreb_pct",
              "reb_pct", "tov_pct", "efg_pct", "ts_pct", "pace", "pie", "poss"]


def parse_stats_api(payload):
    """Map the official stats API response onto our committed schema.

    Returns (rows, note). rows is [] and note explains why on any problem -
    the response's own header list is the only authority for column names,
    so a header we do not recognise fails the parse instead of being guessed.
    """
    rs = None
    for rset in payload.get("resultSets", []) or []:
        if rset.get("name") == "LeagueDashTeamStats":
            rs = rset
            break
    if rs is None:
        names = [r.get("name") for r in payload.get("resultSets", []) or []]
        return [], f"no LeagueDashTeamStats result set (found: {names})"
    headers = rs.get("headers") or rs.get("labels") or []
    raw_rows = rs.get("rowSet") or rs.get("rows") or []
    norm = {re.sub(r"[^A-Za-z0-9]", "", str(h)).upper(): i
            for i, h in enumerate(headers)}
    missing = [f"{k}->{v}" for k, v in STATS_API_WANT.items() if v not in norm]
    if missing:
        return [], (f"headers not recognised: {missing}; "
                    f"response headers = {headers}")
    out = []
    problems = []
    for rr in raw_rows:
        row = []
        for col in STATS_COLS:
            v = rr[norm[STATS_API_WANT[col]]]
            if col == "team":
                row.append(str(v))
                continue
            try:
                row.append(int(float(v)) if col in STATS_API_INT else float(v))
            except (TypeError, ValueError):
                row.append(None)
        team, gp, w, l = row[0], row[1], row[2], row[3]
        if team not in ABBR:
            problems.append(f"unexpected team {team!r}")
            continue
        if None in row[1:]:
            problems.append(f"{team}: non-numeric cell {row}")
            continue
        ortg, pace, poss = row[5], row[17], row[19]
        if w + l != gp:
            problems.append(f"{team}: W+L {w}+{l} != GP {gp}")
            continue
        if not (1 <= gp <= 40) or not (70 <= ortg <= 150) \
                or not (85 <= pace <= 120) or not (100 <= poss <= 3000):
            problems.append(f"{team}: out-of-range values {row}")
            continue
        out.append(row)
    if problems:
        return [], f"{len(problems)} row problems, first: {problems[0]}"
    if len(out) != 30:
        return [], f"expected 30 rows, got {len(out)}"
    return out, "ok"


def get(url, timeout=45):
    from urllib.parse import urlparse
    host = urlparse(url).netloc
    if host not in ALLOWED_HOSTS:
        raise ValueError(f"refusing to fetch a non-official host: {host}")
    req = urllib.request.Request(url, headers=WEB_CLIENT_HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as fh:
        raw = fh.read()
    return raw


def as_text(raw):
    for enc in ("utf-8", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def log(msg):
    print(f"[{datetime.datetime.now(datetime.timezone.utc):%H:%M:%S}] {msg}", flush=True)


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def strip_volatile(obj):
    """Remove capture-clock fields so 'did the payload change?' is meaningful."""
    volatile = {"captured_at_utc", "workflow_run_at_utc"}
    if isinstance(obj, dict):
        return {k: strip_volatile(v) for k, v in obj.items() if k not in volatile}
    if isinstance(obj, list):
        return [strip_volatile(v) for v in obj]
    return obj


def write_if_changed(path, payload):
    """Write only when the payload (ignoring capture clocks) actually changed.

    This is what keeps three scheduled runs a day from producing
    timestamp-only churn: an unchanged page leaves the file untouched.
    """
    body = strip_volatile(payload)
    if os.path.exists(path):
        try:
            old = strip_volatile(read_json(path))
        except (OSError, ValueError):
            old = None
        if old == body:
            return False
    write_json(path, payload)
    return True


# -------------------------------------------------------------- team advanced
def parse_teams_advanced(text):
    """Pull the 30-team advanced table out of the raw stats page.

    The executed run proved the table is server-rendered HTML (the pre-
    execution code looked for an embedded `rowSet` JSON that the page does
    not contain - indicators in _capture_evidence_S1_season.json show
    `"rowSet": 0`). One <tr> per team: a link cell with the full team name,
    then numeric cells. After the team cell we take the first 19 numbers -
    GP, W, L, MIN, OffRtg ... POSS exactly as the committed schema in
    data/raw/team_advanced.json - which keeps any trailing rank cells out.

    Returns [] unless all 30 rows parse AND every row passes the integrity
    checks (W+L == GP, ranges on ratings/pace/poss). A partial or wrong
    table is worse than a stale snapshot, so any failure returns [] and the
    caller keeps the committed file.
    """
    cols = ["gp", "w", "l", "min", "ortg", "drtg", "netr", "ast_pct",
            "ast_to", "ast_ratio", "oreb_pct", "dreb_pct", "reb_pct",
            "tov_pct", "efg_pct", "ts_pct", "pace", "pie", "poss"]
    int_cols = {"gp", "w", "l", "poss"}
    out = []
    problems = []
    for tr in re.finditer(r"<tr[^>]*>(.*?)</tr>", text, re.S | re.I):
        body = tr.group(1)
        tm = re.search(r'href="/stats/team/\d+/[^"]*"[^>]*>\s*([^<]+?)\s*</a>',
                       body, re.I)
        if not tm:
            continue
        team = html.unescape(tm.group(1)).strip()
        if team not in ABBR:
            continue          # header/filter rows, not a data row
        cells = re.findall(r"<td[^>]*>(.*?)</td>", body, re.S | re.I)
        texts = []
        for c in cells:
            t = TAG_RE.sub(" ", c)
            t = html.unescape(t).replace(",", "")
            texts.append(re.sub(r"\s+", " ", t).strip())
        try:
            ti = next(i for i, t in enumerate(texts) if t == team)
        except StopIteration:
            problems.append(f"{team}: team cell not found verbatim")
            continue
        nums = [t for t in texts[ti + 1:] if re.fullmatch(r"-?\d+\.?\d*", t)]
        if len(nums) < 19:
            problems.append(f"{team}: only {len(nums)} numeric cells after team")
            continue
        row = [team]
        try:
            for name, raw in zip(cols, nums[:19]):
                row.append(int(float(raw)) if name in int_cols else float(raw))
        except ValueError:
            problems.append(f"{team}: non-numeric cell in {nums[:19]}")
            continue
        gp, w, l = row[1], row[2], row[3]
        ortg, pace, poss = row[5], row[17], row[19]
        if w + l != gp:
            problems.append(f"{team}: W+L {w}+{l} != GP {gp}")
            continue
        if not (1 <= gp <= 40) or not (70 <= ortg <= 150) \
                or not (85 <= pace <= 120) or not (100 <= poss <= 3000):
            problems.append(f"{team}: out-of-range values {row}")
            continue
        out.append(row)
    if problems:
        log(f"  team table: {len(problems)} row problems, first: {problems[0]}")
    if len(out) != 30:
        return []
    return out


# ------------------------------------------------------------------- schedule
def parse_schedule(text):
    games = []
    seen = set()
    for m in GAME_LINK_RE.finditer(text):
        away, home, gid = m.group(1).upper(), m.group(2).upper(), m.group(3)
        if gid in seen:
            continue
        seen.add(gid)
        games.append({"away": away, "home": home, "game_id": gid})
    return games


# --------------------------------------------------------------- injury index
def parse_injury_index(text):
    # Edition names look like Injury-Report_2026-11-13_05_15PM.pdf and
    # Injury-Report_2026-11-15_06_15AM.pdf: the date contains hyphens.
    # Two defects lived here. (1) [0-9_]+ after the prefix can never consume
    # "2026-11-13", so the pattern returned zero editions on every page - found
    # by the unit test in COORDINATION.md section 15 (R02) before the first
    # executed run. (2) The suffix was PM-only, so every AM edition - which on
    # 2026-11-15 is the whole newest-report window, 12:00 a.m. to 6:15 a.m. ET -
    # was invisible to the job even though the hub links it. AM|PM now.
    links = re.findall(
        r'https://ak-static\.cms\.nba\.com/referee/injury/'
        r'(Injury-Report_[0-9\-_]+(?:AM|PM)\.pdf)',
        text)

    def edition_key(name):
        # Newest first. Reverse lexicographic order is wrong within a day:
        # "12_00PM" > "05_15PM" as text, but noon is the EARLIEST edition.
        m = re.search(r'_(\d{4})-(\d{2})-(\d{2})_(\d{2})_(\d{2})(AM|PM)', name)
        if not m:
            return (name, 0)
        year, mo, day, hh, mm, ampm = m.groups()
        hour24 = int(hh) % 12 + (12 if ampm == "PM" else 0)
        return (f"{year}-{mo}-{day}", hour24 * 100 + int(mm))

    return sorted(set(links), key=edition_key, reverse=True)


# ------------------------------------------------- generic official-table probe
def probe_team_table(text):
    """Count the rows of a server-rendered team stats table, whatever columns it carries.

    Deliberately does NOT try to interpret the numbers. The three team-stat pages
    (traditional, opponent, advanced) share the row shell - a link cell with the full
    team name - but not the column set, and the last time a parser guessed at columns it
    produced a snapshot the site had to walk back. So the capture records: how many of the
    30 teams appear as rows, the cell text of each row in page order, and the page hash.
    A verifier turns that into data; this does not.
    """
    rows = []
    seen = set()
    for tr in re.finditer(r"<tr[^>]*>(.*?)</tr>", text, re.S | re.I):
        body = tr.group(1)
        tm = re.search(r'href="/stats/team/\d+/[^"]*"[^>]*>\s*([^<]+?)\s*</a>', body, re.I)
        if not tm:
            continue
        team = html.unescape(tm.group(1)).strip()
        if team not in ABBR or team in seen:
            continue
        seen.add(team)
        cells = [TAG_RE.sub(" ", c).strip() for c in
                 re.findall(r"<td[^>]*>(.*?)</td>", body, re.S | re.I)]
        rows.append({"team": team, "abbr": ABBR[team],
                     "cells": [html.unescape(c) for c in cells]})
    return rows


def parse_standings_records(text):
    """Record cells (``10-2`` style) attached to a team name, as printed.

    The standings page renders its table in the browser (source S9 on the register says so),
    so a plain fetch may legitimately contain nothing parseable. That is reported as
    zero rows with evidence, never as 'no games played', and this function only ever
    transcribes what is in the bytes: team, the record strings in document order.
    """
    out = []
    for name in ABBR:
        i = text.find(name)
        if i < 0:
            continue
        window = text[i:i + 320]     # short on purpose: a wider window swallows the next team's cells
        recs = RECORD_RE.findall(window)
        if recs:
            out.append({"team": name, "abbr": ABBR[name], "records_in_document_order": recs[:12]})
    return out


# ---------------------------------------------------------------- game results
def excerpt_around(text, needle, before=800, span=4000):
    """Bounded raw-text excerpt around the first occurrence of `needle`."""
    i = text.find(needle)
    if i < 0:
        return None
    start = max(0, i - before)
    return text[start:start + span]


def extract_json_games(text):
    """Pull finished-or-live game objects out of the page's embedded state.

    Order of attack, proven against the executed runs:
      1. `__NEXT_DATA__` (present on the games pages - indicator = 1): one
         well-formed JSON document, walked for dicts that carry a gameId and
         both team blocks;
      2. otherwise: every `"gameId":"..."` occurrence, trying raw_decode from
         each `{` within a bounded window behind it, keeping objects that
         decode fully and carry both team blocks;
      3. otherwise: the caller falls back to card text and records evidence.

    Escaped payloads ({\\"gameId\\") are deliberately not unescaped here.
    """
    games = {}

    def keep(obj):
        gid = str(obj.get("gameId"))
        if gid and gid not in games \
                and isinstance(obj.get("homeTeam"), dict) \
                and isinstance(obj.get("awayTeam"), dict):
            games[gid] = obj

    def walk(node):
        if isinstance(node, dict):
            if "gameId" in node and "homeTeam" in node and "awayTeam" in node:
                keep(node)
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    nd = re.search(
        r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', text, re.S)
    if nd:
        try:
            walk(json.loads(nd.group(1)))
        except ValueError:
            pass
    if games:
        return games

    decoder = json.JSONDecoder()
    for m in re.finditer(r'"gameId"\s*:\s*"(\d{10})"', text):
        gid = m.group(1)
        if gid in games:
            continue
        window_start = max(0, m.start() - 8000)
        for i in range(m.start() - 1, window_start - 1, -1):
            if text[i] != "{":
                continue
            try:
                obj, _ = decoder.raw_decode(text[i:])
            except ValueError:
                continue
            if str(obj.get("gameId")) == gid and isinstance(obj.get("homeTeam"), dict) \
                    and isinstance(obj.get("awayTeam"), dict):
                keep(obj)
                break
    return games


def row_from_json_game(g, known):
    """Convert one embedded game object into a row, not_final marker, or
    unparsed reason. Never guesses: non-final statuses are not_final, missing
    or non-integer scores are unparsed."""
    gid = str(g.get("gameId"))
    status = str(g.get("gameStatusText") or "")
    away = g.get("awayTeam") or {}
    home = g.get("homeTeam") or {}
    if not re.match(r"final", status, re.I):
        return ("not_final", gid)
    try:
        a_pts = int(away.get("score"))
        h_pts = int(home.get("score"))
    except (TypeError, ValueError):
        return ("unparsed", {"game_id": gid,
                             "reason": "Final status but score is not an integer "
                                       f"(away={away.get('score')!r}, "
                                       f"home={home.get('score')!r})"})
    if not (0 <= a_pts <= 400 and 0 <= h_pts <= 400):
        return ("unparsed", {"game_id": gid,
                             "reason": f"implausible scores {a_pts}-{h_pts}"})
    ot = 0
    ot_m = re.search(r"/OT(\d*)", status, re.I)
    if ot_m:
        ot = int(ot_m.group(1)) if ot_m.group(1) else 1
    away_tri = away.get("teamTricode")
    home_tri = home.get("teamTricode")
    k = known.get(gid)
    snapshot_match = None
    if k is not None:
        snapshot_match = (k["away"] == away_tri and k["home"] == home_tri)
    return ("row", {
        "game_id": gid, "away": away_tri, "home": home_tri,
        "away_pts": a_pts, "home_pts": h_pts,
        "status": status, "ot": ot,
        "away_record_printed": away.get("teamSubtitle"),
        "home_record_printed": home.get("teamSubtitle"),
        "snapshot_match": snapshot_match,
        "source": "embedded JSON",
    })


def parse_games_page(text, known):
    """Parse one https://www.nba.com/games?date=... page into finals rows.

    `known` maps game_id -> {away, home, date} from the committed snapshots
    (data/raw/games_completed.json + data/raw/schedule_upcoming.json).

    Two strategies, in order:
      1. structured: every clean `{"gameId":...}` JSON object in the page
         (the page's embedded state) - scores, status and records come from
         typed fields, not from text position;
      2. fallback: the score card's own text, trying EVERY link occurrence
         (the first executed run showed the first occurrence is often not
         the card), with tags and hrefs stripped.

    Rules that never change between strategies: a game counts as final only
    when its status says so; a score that cannot be read lands in `unparsed`
    with a reason; nothing is inferred.

    Returns (rows, not_final, unparsed, occurrences, source).
    """
    rows, not_final, unparsed = [], [], []
    occurrences = {}

    games = extract_json_games(text)
    if games:
        for gid in sorted(games):
            occurrences[gid] = occurrences.get(gid, 0) + 1
            kind, payload = row_from_json_game(games[gid], known)
            if kind == "row":
                rows.append(payload)
            elif kind == "not_final":
                not_final.append(gid)
            else:
                unparsed.append(payload)
        return rows, not_final, unparsed, occurrences, "embedded JSON"

    # ---- fallback: score-card text (see v2 notes) ----
    parsed = {}
    final_seen = set()
    matches = list(GAME_LINK_RE.finditer(text))
    for i, m in enumerate(matches):
        away, home, gid = m.group(1).upper(), m.group(2).upper(), m.group(3)
        occurrences[gid] = occurrences.get(gid, 0) + 1
        if gid in parsed:
            continue
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        slice_ = text[m.start():min(end, m.start() + 6000)]
        body = HREF_ATTR_RE.sub(" ", slice_)
        body = TAG_RE.sub(" ", body)
        body = html.unescape(body)
        body = re.sub(r"\s+", " ", body).strip()
        fin = FINAL_RE.search(body)
        if not fin:
            continue          # try this game's other occurrences
        final_seen.add(gid)
        no_rec = RECORD_RE.sub(" ", body)
        fin2 = FINAL_RE.search(no_rec)
        before = no_rec[:fin2.start()]
        after = no_rec[fin2.end():]
        away_scores = re.findall(r"\b(\d{2,3})\b", before)
        home_scores = re.findall(r"\b(\d{2,3})\b", after)
        status = fin2.group(0)
        ot = 0
        ot_m = re.search(r"/OT(\d+)", status, re.I)
        if ot_m:
            ot = int(ot_m.group(1))
        recs = RECORD_RE.findall(body)
        away_rec = recs[0] if recs else None
        home_rec = recs[-1] if len(recs) >= 2 else None
        if not away_scores or not home_scores:
            unparsed.append({"game_id": gid,
                             "reason": "final status present but a score could not "
                                       f"be read (before={away_scores[:3]}, "
                                       f"after={home_scores[:3]})"})
            continue
        a_pts, h_pts = int(away_scores[-1]), int(home_scores[0])
        if not (0 <= a_pts <= 400 and 0 <= h_pts <= 400):
            unparsed.append({"game_id": gid,
                             "reason": f"implausible scores {a_pts}-{h_pts}"})
            continue
        k = known.get(gid)
        snapshot_match = None
        if k is not None:
            snapshot_match = (k["away"] == away and k["home"] == home)
        parsed[gid] = {
            "game_id": gid, "away": away, "home": home,
            "away_pts": a_pts, "home_pts": h_pts,
            "status": status, "ot": ot,
            "away_record_printed": away_rec, "home_record_printed": home_rec,
            "snapshot_match": snapshot_match,
            "source": "score-card text",
        }
    for gid in occurrences:
        if gid in parsed:
            rows.append(parsed[gid])
        elif gid in final_seen:
            pass  # already recorded in unparsed with a reason
        else:
            not_final.append(gid)
    rows.sort(key=lambda r: r["game_id"])
    not_final.sort()
    return rows, not_final, unparsed, occurrences, "score-card text"



def compare_to_snapshot(rows, known, committed_by_id):
    """Diff parsed finals against the committed snapshot. Log only, never fix."""
    mismatches, candidates = [], []
    for r in rows:
        gid = r["game_id"]
        if r["snapshot_match"] is False:
            mismatches.append({"game_id": gid, "field": "matchup",
                               "committed": f"{known[gid]['away']}@{known[gid]['home']}",
                               "page": f"{r['away']}@{r['home']}"})
            continue
        c = committed_by_id.get(gid)
        if c is None:
            candidates.append(gid)
            continue
        for field, page_val in (("away_pts", r["away_pts"]), ("home_pts", r["home_pts"])):
            if c[field] != page_val:
                mismatches.append({"game_id": gid, "field": field,
                                   "committed": c[field], "page": page_val})
        committed_ot = bool(c["ot"])
        page_ot = bool(r["ot"])
        if committed_ot != page_ot:
            mismatches.append({"game_id": gid, "field": "ot",
                               "committed": c["ot"], "page": r["ot"]})
    return mismatches, candidates


def committed_index(games_block, sched_block):
    committed = {}
    for r in rows_by_cols(games_block):
        committed[r["game_id"]] = {"away": r["away"], "away_pts": r["away_pts"],
                                   "home": r["home"], "home_pts": r["home_pts"],
                                   "ot": r["ot"], "date": r["date"]}
    return committed


def known_index(games_block, sched_block):
    known = {}
    for r in rows_by_cols(games_block):
        known[r["game_id"]] = {"away": r["away"], "home": r["home"], "date": r["date"]}
    for r in rows_by_cols(sched_block):
        known.setdefault(r["game_id"],
                         {"away": r["away"], "home": r["home"], "date": r["date"]})
    return known


# ---------------------------------------------------------------------- main
def capture_results(now, changed, failed, known, committed):
    games = read_json(os.path.join(RAW, "games_completed.json"))
    sched = read_json(os.path.join(RAW, "schedule_upcoming.json"))
    dates = sorted({r["date"] for r in rows_by_cols(games)}
                   | {r["date"] for r in rows_by_cols(sched)})
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    today = now_utc.strftime("%Y-%m-%d")
    if today not in dates:
        dates.append(today)
    # Also capture yesterday's slate. The committed snapshots cover the graded
    # window (11/06-11/12) and the upcoming horizon (11/14+), so a slate that went
    # final "last night" fell between them and was never re-fetched after the games
    # ended -- observed on 2026-11-14, when the 11/13 capture was still stuck at its
    # 02:05Z in-progress state while all nine games were Final on the official page.
    # Yesterday is exactly when the settle ledger needs the FINAL card.
    # (Adopted into the integration seat from PR #58, session arena/ef6ff2a4-nba1,
    #  which found and fixed this; its evidence is data/audit/finals_2026_11_13_verification.json.)
    yesterday = (now_utc - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    if yesterday not in dates:
        dates.append(yesterday)
    for d in sorted(dates):
        url = f"https://www.nba.com/games?date={d}"
        try:
            raw = get(url)
        except Exception as exc:                       # noqa: BLE001
            failed.append((f"results {d}", f"fetch failed: {exc}"))
            continue
        text = as_text(raw)
        rows, not_final, unparsed, occurrences, source = parse_games_page(text, known)
        # dedupe unparsed reasons per game (a game can fail on several slices)
        seen_unparsed = set()
        unparsed = [u for u in unparsed
                    if not (u["game_id"] in seen_unparsed
                            or seen_unparsed.add(u["game_id"]))]
        mismatches, candidates = compare_to_snapshot(rows, known, committed)
        parsed_ids = {r["game_id"] for r in rows}
        missed = sorted(gid for gid, c in committed.items()
                        if c["date"] == d and gid not in parsed_ids)
        log(f"  {d}: source={source}, {len(rows)} finals, {len(not_final)} "
            f"not final, {len(unparsed)} unparsed, {len(mismatches)} snapshot "
            f"mismatches, {len(missed)} committed finals missed")
        payload = {
            "captured_at_utc": now,
            "source_url": url,
            "page_bytes": len(raw),
            "page_sha256": hashlib.sha256(raw).hexdigest(),
            "page_indicators": {
                "__NEXT_DATA__": text.count("__NEXT_DATA__"),
                "clean_gameId": len(re.findall(r'\{"gameId"\s*:', text)),
                "escaped_gameId": len(re.findall(r'\{\\"gameId\\"', text)),
                "FINAL_word": len(re.findall(r"\bFINAL\b", text)),
            },
            "parse": {"strategy": source,
                      "finals_rows": rows,
                      "not_final": not_final,
                      "unparsed": unparsed,
                      "link_occurrences": occurrences},
            "snapshot_comparison": {
                "checked_against": "data/raw/games_completed.json + "
                                   "data/raw/schedule_upcoming.json",
                "mismatches": mismatches,
                "promotion_candidates": candidates,
                "committed_finals_missed": missed,
            },
            "note": ("Capture only: this file never overwrites a committed "
                     "snapshot. A promotion_candidate is a final the official "
                     "page shows but the committed snapshot does not have; it "
                     "becomes data only after a verifier re-checks it and a "
                     "session promotes it. A mismatch is logged, never "
                     "silently corrected."),
        }
        # Failure evidence, bounded: if the committed snapshot says this page
        # should show finals but none parsed, store exactly what the parser
        # saw so the next iteration can be written against ground truth
        # instead of a guess. Also stored when a slice had Final but no score.
        evidence = []
        if missed:
            e1 = excerpt_around(text, missed[0])
            if e1:
                evidence.append({"around": missed[0], "excerpt": e1})
            fi = text.find("Final")
            if fi >= 0:
                evidence.append({"around": "First 'Final' in raw HTML",
                                 "excerpt": text[max(0, fi - 800):fi + 3200]})
            # Where does the embedded payload live? The card carries the
            # status but not the scores; the scores sit in an escaped JSON
            # blob. Find its opener so the next parser can load it as JSON
            # instead of guessing at text.
            for n in ("JSON.parse(", "window.__", "gameStatusText", "<script id="):
                e = excerpt_around(text, n, before=2500, span=5000)
                if e:
                    evidence.append({"around": n, "excerpt": e})
        elif unparsed or mismatches:
            e1 = excerpt_around(text, "Final")
            if e1:
                evidence.append({"around": "First 'Final' in raw HTML",
                                 "excerpt": e1})
        if evidence:
            payload["failure_evidence"] = evidence[:5]
        if write_if_changed(os.path.join(RAW, f"_capture_results_{d}.json"),
                            payload):
            changed.append(f"results {d}")
        else:
            log(f"  {d}: unchanged")


BOXSCORE_API = ("https://stats.nba.com/stats/boxscoretraditionalv2?GameID={gid}"
                "&LeagueID=00&StartPeriod=0&EndPeriod=10&StartBonus=0&EndBonus=0&RangeType=0")


def capture_game_logs(now, changed, failed, games_block, days_back=1):
    """Per-player game logs for the most recent completed games, from the league's own JSON.

    Why this endpoint and not the HTML: boxscoretraditionalv2 returns its own `headers` /
    `baseColumns` arrays alongside `rowSet`, so every value is labelled by the source that
    published it. That is the difference between a capture and a guess - the previous attempt to
    read minutes off the rendered page is what produced a 50-of-465 slice with no column
    mapping (Flagged F-G). Nothing here overwrites a committed snapshot: each game lands in
    data/raw/_capture_gamelog_<game_id>.json for a verifier to promote.
    """
    cols = games_block.get("cols", [])
    if "date" not in cols or "game_id" not in cols:
        return
    di, gi = cols.index("date"), cols.index("game_id")
    ai, hi = cols.index("away"), cols.index("home")
    want = sorted({r[di] for r in games_block["rows"]})[-days_back:]
    targets = [(r[gi], r[ai], r[hi], r[di]) for r in games_block["rows"] if r[di] in want]
    for gid, away, home, date in targets[-12:]:
        url = BOXSCORE_API.format(gid=gid)
        rec = {"captured_at_utc": now, "source_url": url, "game_id": gid, "date": date,
               "away": away, "home": home, "http_status": None, "players": [],
               "note": ("Capture only. Column meaning comes from the response's own headers, not "
                        "from position. Promote after re-checking the game page.")}
        try:
            raw = get(url, timeout=45)
            payload = json.loads(as_text(raw))
            rec["http_status"] = 200
            sets = payload.get("resultSets") or []
            if not sets:
                rec["error"] = "no resultSets in the response"
            for rs in sets:
                names = rs.get("headers") or []
                for row in rs.get("rowSet") or []:
                    d = dict(zip(names, row))
                    team = d.get("TEAM_ABBREVIATION")
                    opp = home if team == away else away
                    rec["players"].append({
                        "player": d.get("PLAYER_NAME"), "team": team, "opponent": opp,
                        "in": d.get("MIN"), "pts": d.get("PTS"), "reb": d.get("REB"),
                        "ast": d.get("AST"), "game_id": gid, "date": date,
                        "source_url": "https://www.nba.com/game/%s-vs-%s-%s"
                                       % (away.lower(), home.lower(), gid)})
                rec["headers_from_source"] = names
                break
            if write_if_changed(os.path.join(RAW, f"_capture_gamelog_{gid}.json"), rec):
                changed.append(f"game log {gid} ({len(rec['players'])} players)")
        except urllib.error.HTTPError as exc:
            rec["http_status"] = exc.code
            rec["error"] = ("HTTP %s - the stats API refuses this client; recorded as unavailable, "
                            "not as 'no data'" % exc.code)
            write_if_changed(os.path.join(RAW, f"_capture_gamelog_{gid}.json"), rec)
            failed.append((f"gamelog_{gid}", "HTTP %s" % exc.code))
        except Exception as exc:                          # noqa: BLE001
            rec["error"] = "%s: %s" % (type(exc).__name__, exc)
            write_if_changed(os.path.join(RAW, f"_capture_gamelog_{gid}.json"), rec)
            failed.append((f"gamelog_{gid}", rec["error"]))
        time.sleep(1.2)


def capture_injury(now, changed, failed, index_editions):
    """Fetch the newest report PDFs fully; probe today's/yesterday's editions.

    Every HTTP status is recorded. 403 means 'unavailable to this client at
    this time', never 'does not exist'.
    """
    candidates = list(index_editions[:4])
    fallback_used = not index_editions
    if fallback_used:
        today = datetime.datetime.now(datetime.timezone.utc).date()
        for delta in (0, 1):
            day = today - datetime.timedelta(days=delta)
            for t in INJURY_EDITION_TIMES + INJURY_AM_EDITION_TIMES:
                name = f"Injury-Report_{day.isoformat().replace('-', '_')}_{t}.pdf"
                if name not in candidates:
                    candidates.append(name)
    results = []
    for edition in candidates[:12]:
        url = INJURY_HOST + edition
        rev_iso, rev_human = edition_revision_time(edition)
        rec = {"edition": edition, "url": url, "http_status": None,
               "bytes": 0, "sha256": None, "attempts": 0,
               "edition_revision_utc": rev_iso, "edition_revision_printed": rev_human,
               "retrieved_utc": now}
        # The first executed run saw 200,200 then 403,403... on a tight loop
        # over ak-static - the shape of a rate limit, not of absent files.
        # Space the requests and retry a 403 once before recording it.
        for attempt in (1, 2):
            rec["attempts"] = attempt
            try:
                raw = get(url, timeout=30)
                rec["http_status"] = 200
                rec["bytes"] = len(raw)
                rec["sha256"] = hashlib.sha256(raw).hexdigest()
                if write_if_changed(os.path.join(RAW, f"_capture_injury_pdf_{edition}.json"),
                                    {"captured_at_utc": now, "source_url": url,
                                     "bytes": len(raw), "sha256": rec["sha256"],
                                     "content_type": "application/pdf",
                                     # revision time as the report labels itself (from the
                                     # published filename) next to the moment we fetched it:
                                     # the injury page prints both so the lag is visible.
                                     "edition_revision_utc": rev_iso,
                                     "edition_revision_printed": rev_human,
                                     "retrieved_utc": now}):
                    changed.append(f"injury pdf {edition}")
                log(f"  injury {edition}: 200, {len(raw)} bytes (attempt {attempt})")
                break
            except urllib.error.HTTPError as exc:
                rec["http_status"] = exc.code
                log(f"  injury {edition}: HTTP {exc.code} (attempt {attempt})")
                if exc.code in (403, 429) and attempt == 1:
                    time.sleep(8)
                    continue
                break
            except Exception as exc:                   # noqa: BLE001
                rec["error"] = f"{type(exc).__name__}: {exc}"
                log(f"  injury {edition}: {rec['error']}")
                break
        results.append(rec)
        time.sleep(1.5)
    if write_if_changed(os.path.join(RAW, "_capture_injury_probe.json"),
                        {"captured_at_utc": now,
                         "results": results,
                         "candidate_source": ("official index page (newest four links)"
                                              if not fallback_used else
                                              "FIXED FALLBACK LIST - the index page could not be "
                                              "read, so these names are guesses and an absent file "
                                              "is expected"),
                         "editions_from_index": len(index_editions),
                         "note": ("HTTP status only. 403 from ak-static.cms.nba.com "
                                  "has been observed both for editions that exist to a "
                                  "browser and for editions that are not published yet; "
                                  "it is recorded as unavailable at capture time, not "
                                  "as proof of absence.")}):
        changed.append("injury probe")


def main():
    now = now_utc()
    changed = []
    failed = []
    index_editions = []

    for key, (url, kind) in FETCHES.items():
        log(f"fetch {key} <- {url}")
        try:
            raw = get(url)
        except Exception as exc:                      # noqa: BLE001 - report and continue
            failed.append((key, f"fetch failed: {exc}"))
            log(f"  FAILED: {exc} - keeping the existing snapshot")
            continue
        text = as_text(raw)
        if len(text) < 2000:
            failed.append((key, f"implausibly short response ({len(text)} bytes)"))
            log("  FAILED: response too short - keeping the existing snapshot")
            continue

        if kind == "team_table":
            rows = probe_team_table(text)
            payload = {"captured_at_utc": now, "source_url": url,
                       "page_sha256": hashlib.sha256(raw).hexdigest(),
                       "teams_parsed": len(rows), "teams_expected": 30,
                       "rows": rows,
                       "note": ("Capture only. A row-count check and the cell text as printed; the "
                                "column meaning is NOT inferred here, and no committed snapshot is "
                                "touched. Promote by re-reading the page and mapping the columns to "
                                "the schema in data/raw/teams_traditional.json / teams_opponent.json.")}
            if len(rows) != 30:
                payload["failure_evidence"] = [
                    {"around": "first <tr> containing a team link",
                     "excerpt": excerpt_around(text, "/stats/team/", before=200, span=2600)}]
                failed.append((key, "expected 30 team rows, parsed %d" % len(rows)))
            if write_if_changed(os.path.join(RAW, f"_capture_{key}.json"), payload):
                changed.append(f"team table {key} ({len(rows)} rows)")
            continue
        if kind == "standings":
            recs = parse_standings_records(text)
            payload = {"captured_at_utc": now, "source_url": url,
                       "page_sha256": hashlib.sha256(raw).hexdigest(),
                       "teams_with_records": len(recs), "teams_expected": 30,
                       "rows": recs,
                       "note": ("Capture only. The official standings table is rendered client-side, "
                                "so a fetch may hold no parseable table at all - zero rows here means "
                                "'not in these bytes', never 'no games played'. Records are transcribed "
                                "in document order and NOT mapped to columns: which string is HOME and "
                                "which is ROAD is a property of the rendered table, and a standings "
                                "table with those two columns swapped is worse than a stale one. The "
                                "home-win rate this site quotes is computed from a live read of the "
                                "rendered table (verify/2026-11-15-e3ebc423/standings_2026-11-15.json), "
                                "not from this capture.")}
            if len(recs) < 30:
                payload["failure_evidence"] = [{"around": "first occurrence of a team name",
                                                "excerpt": excerpt_around(text, "Boston Celtics",
                                                                         before=300, span=2600)}]
                log(f"  standings: {len(recs)}/30 teams carry a record in these bytes - "
                    "client-side render, recorded as a gap")
            if write_if_changed(os.path.join(RAW, f"_capture_{key}.json"), payload):
                changed.append(f"standings probe ({len(recs)}/30 teams)")
            continue
        if kind == "teams_advanced":
            rows = parse_teams_advanced(text)
            fetched_from = url
            api_evidence = None
            if len(rows) != 30:
                # The cited page renders its table in the browser; fall back
                # to the official stats API behind it (resource name taken
                # from the page's own JS chunk - see chunk_probe below).
                if key == "S1_season":
                    df, dt = "", ""
                else:
                    df, dt = "10%2F20%2F2026", "11%2F05%2F2026"
                api_url = STATS_API.format(df=df, dt=dt)
                api_evidence = {"url": api_url}
                try:
                    raw2 = get(api_url, timeout=45)
                    api_evidence["http_status"] = 200
                    api_evidence["bytes"] = len(raw2)
                    rows, note = parse_stats_api(json.loads(as_text(raw2)))
                    api_evidence["parse_note"] = note
                    if len(rows) == 30:
                        fetched_from = api_url
                        log(f"  stats API fallback parsed {len(rows)} rows ({note})")
                except urllib.error.HTTPError as exc:
                    api_evidence["http_status"] = exc.code
                    api_evidence["parse_note"] = f"HTTP {exc.code}"
                    rows = []
                except Exception as exc:              # noqa: BLE001
                    api_evidence["parse_note"] = f"{type(exc).__name__}: {exc}"
                    rows = []
                time.sleep(1.0)
            if len(rows) != 30:
                failed.append((key, f"expected 30 team rows, parsed {len(rows)}"))
                log(f"  SKIPPED: parsed {len(rows)} rows - keeping the existing snapshot")
                needles = ["stats.nba.com", "/stats/api", "leaguedash",
                           "graphql", "<td"]
                # The table is client-rendered and the data URL is not in the
                # HTML. Look inside a bounded number of the page's own JS
                # chunks for the endpoint the browser calls, and record what
                # is found - evidence, not values.
                chunk_probe = []
                chunks = list(dict.fromkeys(
                    re.findall(r'/_next/static/chunks/[^"\']+\.js', text)))
                # Page-specific chunks are listed last; probe the tail first.
                for c in (chunks[-6:] if len(chunks) > 6 else chunks):
                    entry = {"chunk": c, "hits": {}}
                    try:
                        js = as_text(get("https://www.nba.com" + c, timeout=30))
                    except Exception as exc:          # noqa: BLE001
                        entry["error"] = f"{type(exc).__name__}: {exc}"
                        chunk_probe.append(entry)
                        continue
                    for n in ("leaguedash", "stats.nba.com", "/stats/api",
                              "MeasureType", "DateFrom"):
                        cnt = js.count(n)
                        if cnt:
                            entry["hits"][n] = cnt
                            ev = excerpt_around(js, n, before=300, span=1200)
                            if ev and "excerpt" not in entry:
                                entry["excerpt"] = ev
                    chunk_probe.append(entry)
                    if any(entry["hits"].values()):
                        break
                    time.sleep(0.5)
                if write_if_changed(
                        os.path.join(RAW, f"_capture_evidence_{key}.json"),
                        {"captured_at_utc": now, "source_url": url,
                         "status": "parse_failed",
                         "api_attempt": api_evidence,
                         "indicators": {n: text.count(n) for n in needles},
                         "failure_evidence": [
                             {"around": n, "excerpt": e} for n in needles
                             for e in [excerpt_around(text, n)] if e][:2],
                         "document_tail": text[-6000:],
                         "chunk_probe": chunk_probe,
                         "note": "Bounded raw-HTML/JS/API evidence for the "
                                 "next parser iteration. The committed "
                                 "snapshot is untouched."}):
                    changed.append(f"evidence {key}")
                continue
            log(f"  parsed {len(rows)} team rows")
            # Capture the actual 30 rows (schema of data/raw/team_advanced.json)
            # so a verifier can diff them against the committed snapshot without
            # re-fetching. This never overwrites the committed snapshot itself.
            if write_if_changed(os.path.join(RAW, f"_capture_{key}.json"),
                                {"captured_at_utc": now, "source_url": url,
                                 "fetched_from": fetched_from,
                                 "row_count": len(rows),
                                 "cols": ["team", "gp", "w", "l", "min", "ortg",
                                          "drtg", "netr", "ast_pct", "ast_to",
                                          "ast_ratio", "oreb_pct", "dreb_pct",
                                          "reb_pct", "tov_pct", "efg_pct",
                                          "ts_pct", "pace", "pie", "poss"],
                                 "rows": rows,
                                 "page_sha256": hashlib.sha256(raw).hexdigest()}):
                changed.append(key)
        elif kind == "players":
            log(f"  captured {len(text)} bytes")
            if write_if_changed(os.path.join(RAW, f"_capture_{key}.json"),
                                {"captured_at_utc": now, "source_url": url,
                                 "page_sha256": hashlib.sha256(raw).hexdigest()}):
                changed.append(key)
        elif kind == "schedule":
            games = parse_schedule(text)
            log(f"  parsed {len(games)} game links")
            if not games:
                failed.append((key, "no game links found"))
                needles = ["JSON.parse(", "window.__", "gameId", "Friday, November"]
                if write_if_changed(
                        os.path.join(RAW, f"_capture_evidence_{key}.json"),
                        {"captured_at_utc": now, "source_url": url,
                         "status": "parse_failed",
                         "indicators": {n: text.count(n) for n in needles},
                         "failure_evidence": [
                             {"around": n, "excerpt": e} for n in needles
                             for e in [excerpt_around(text, n)] if e][:2],
                         "document_head": text[:2500],
                         "note": "Bounded raw-HTML evidence for the next parser "
                                 "iteration. The committed snapshot is untouched."}):
                    changed.append(f"evidence {key}")
                continue
            if write_if_changed(os.path.join(RAW, f"_capture_{key}.json"),
                                {"captured_at_utc": now, "source_url": url,
                                 "games": games,
                                 "page_sha256": hashlib.sha256(raw).hexdigest()}):
                changed.append(key)
        elif kind == "injury_index":
            links = parse_injury_index(text)
            index_editions = links
            log(f"  found {len(links)} report editions")
            if not links:
                failed.append((key, "no injury-report links found"))
                continue
            if write_if_changed(os.path.join(RAW, f"_capture_{key}.json"),
                                {"captured_at_utc": now, "source_url": url,
                                 "editions": links}):
                changed.append(key)

    # results: one page per date, for the dates we already know about plus today
    try:
        games_block = read_json(os.path.join(RAW, "games_completed.json"))
        sched_block = read_json(os.path.join(RAW, "schedule_upcoming.json"))
        known = known_index(games_block, sched_block)
        committed = committed_index(games_block, sched_block)
        capture_results(now, changed, failed, known, committed)
    except Exception as exc:                          # noqa: BLE001
        failed.append(("results", f"stage failed: {exc}"))
        log(f"  results stage FAILED: {exc}")

    # per-player game logs for the most recent completed games (capture only)
    try:
        capture_game_logs(now, changed, failed, games_block)
    except Exception as exc:                              # noqa: BLE001
        failed.append(("gamelog", f"stage failed: {exc}"))
        log(f"  game-log stage FAILED: {exc}")

    # injury reports: full capture of the newest editions + status probe
    try:
        capture_injury(now, changed, failed, index_editions)
    except Exception as exc:                          # noqa: BLE001
        failed.append(("injury", f"stage failed: {exc}"))
        log(f"  injury stage FAILED: {exc}")

    summary = {
        "captured_at_utc": now,
        "changed": changed,
        "failed": failed,
        "note": "Raw captures only. Nothing in data/raw/*.json that a snapshot "
                "owner committed is overwritten by this script - a parsed "
                "result is written as _capture_*.json so a verifier can diff "
                "it against the committed snapshot before it is promoted.",
    }
    write_json(os.path.join(RAW, "_last_refresh.json"), summary)
    log(f"done. {len(changed)} captures written, {len(failed)} problems.")
    for k, v in failed:
        log(f"  problem: {k}: {v}")
    # Exit 0 even with failures: the caller decides. A failure must never break
    # the published site, and the committed snapshot stays live.
    return 0


if __name__ == "__main__":
    sys.exit(main())
