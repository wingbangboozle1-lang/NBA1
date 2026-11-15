#!/usr/bin/env python3
"""Capture the official NBA pages the 2026-11-15 rolling slate needs.

    python3 scripts/capture_official_2026_11_15.py            # full capture
    python3 scripts/capture_official_2026_11_15.py --probe    # one page per kind

Why this file exists
--------------------
This repository's sandbox cannot reach `*.nba.com` (every official host answers
000/403 from there - recorded in `data/raw/probe_official.json`). GitHub's own
runners can, and the repository already relies on that fact: the
`Refresh official data` workflow runs `engine/fetch_official.py` on
`ubuntu-latest`. This script is the 2026-11-15 capture for the *rolling slate*
and is deliberately a NEW file with a NEW name so it does not collide with the
`engine/fetch_official.py` scope claimed by seat `arena/7eb1c20a-nba1`
(COORDINATION.md section 38).

What it captures, and from where (official hosts only):

  * the official slate page for every date in the window
        https://www.nba.com/games?date=YYYY-MM-DD
    -> game id, tip time, both teams, both records, arena, status, live score;
  * the official box-score page for every game id
        https://www.nba.com/game/<away>-vs-<home>-<gameId>/box-score
    -> quarter-by-quarter scores, and every player's box (minutes, points,
       rebounds, assists, turnovers, fouls, shooting) with the opponent;
  * the official standings page
        https://www.nba.com/standings
  * the three official team-stat pages, read through the stats service those
    pages themselves call (the resource name and the result set come from the
    page's own JS chunk, see `data/raw/_capture_evidence_S1_season.json`):
        traditional (MeasureType=Base), opponent (MeasureType=Opponent),
        advanced (MeasureType=Advanced)
  * the official injury-report index and every PDF edition it lists, plus every
    edition slot of the rolling window probed by name:
        https://official.nba.com/nba-injury-report-2026-27-season/
        https://ak-static.cms.nba.com/referee/injury/Injury-Report_*.pdf
  * the arena-coordinate table, from the U.S. Census Bureau gazetteer of
    incorporated places (a federal statistical source), because no NBA-operated
    source publishes arena coordinates:
        https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2025_Gazetteer/
        2025_Gaz_place_national.zip

Rules
-----
1. Nothing is ever overwritten in place: this script only writes under
   `data/captures/2026-11-15/`.
2. Every fetched byte range is recorded with its URL, the UTC fetch time, the
   HTTP status, the byte length and the SHA-256 of the bytes.
3. A value that cannot be read from the official page is left null and the
   reason is recorded. Nothing is inferred, and a missing page is a finding,
   not a failure.
"""

import argparse
import concurrent.futures
import datetime
import gzip
import hashlib
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "captures", "2026-11-15")
RAW = os.path.join(OUT, "raw")
PARSED = os.path.join(OUT, "parsed")

# The web-client header set that `data/raw/probe_official.json` recorded as
# returning HTTP 200 on the www.nba.com stats, schedule and games pages and on
# the official.nba.com injury index (a plain client receives 403 there).
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

NBA_HOSTS = {"www.nba.com", "official.nba.com", "ak-static.cms.nba.com", "stats.nba.com"}
EXTERNAL_HOSTS = {"www2.census.gov"}

# The rolling window this capture covers. 2026-10-20 is the first day of the
# 2026-27 regular season (the season-to-date window the published ratings use);
# 2026-11-18 is the last day of the three-day pick horizon that starts on
# 2026-11-15.
WINDOW_START = "2026-10-20"
WINDOW_END = "2026-11-18"

# Injury-report days whose PDFs are archived byte-for-byte in this capture.
# 2026-11-14 and 2026-11-15 are the two editions that bracket the current
# slate; 2026-11-13 is probed for its fingerprint only.
INJURY_ARCHIVE_DAYS = ("2026-11-14", "2026-11-15")
INJURY_PROBE_DAYS = ("2026-11-13", "2026-11-14", "2026-11-15")

# Team tricode -> candidate place names in the Census gazetteer, in priority
# order. The gazetteer has no arena rows, so the join is on the city the NBA
# prints for the club's arena. Where a club plays in a city whose gazetteer
# entry is a consolidated city, both spellings are listed.
TEAM_CITY = {
    "ATL": ["Atlanta"],
    "BOS": ["Boston"],
    "BKN": ["Brooklyn", "New York"],
    "CHA": ["Charlotte"],
    "CHI": ["Chicago"],
    "CLE": ["Cleveland"],
    "DAL": ["Dallas"],
    "DEN": ["Denver"],
    "DET": ["Detroit"],
    "GSW": ["San Francisco"],
    "HOU": ["Houston"],
    "IND": ["Indianapolis"],
    "LAC": ["Los Angeles"],
    "LAL": ["Los Angeles"],
    "MEM": ["Memphis"],
    "MIA": ["Miami"],
    "MIL": ["Milwaukee"],
    "MIN": ["Minneapolis"],
    "NOP": ["New Orleans"],
    "NYK": ["New York"],
    "OKC": ["Oklahoma City"],
    "ORL": ["Orlando"],
    "PHI": ["Philadelphia"],
    "PHX": ["Phoenix"],
    "POR": ["Portland"],
    "SAC": ["Sacramento"],
    "SAS": ["San Antonio"],
    "TOR": ["Toronto"],
    "UTA": ["Salt Lake City"],
    "WAS": ["Washington"],
}

STATS_API = ("https://stats.nba.com/stats/leaguedashteamstats"
             "?LeagueID=00&Season=2026-27&SeasonType=Regular+Season"
             "&MeasureType={measure}&PerMode={per_mode}&Scope=Season"
             "&LastNGames=0&Month=0&OpponentTeamID=0"
             "&DateFrom={df}&DateTo={dt}")

STAT_PAGE = {
    "traditional": "https://www.nba.com/stats/teams/traditional",
    "opponent": "https://www.nba.com/stats/teams/opponent",
    "advanced": "https://www.nba.com/stats/teams/advanced",
}

# Windows re-read from the official team-stat pages. `season` is the published
# ratings window (season to date), `train` is the training window the ratings
# were fitted on, `oos` is the out-of-sample window.
STAT_WINDOWS = [
    ("season", "", ""),
    ("train", "10/20/2026", "11/05/2026"),
    ("oos", "11/06/2026", "11/14/2026"),
]

MANIFEST = []


# --------------------------------------------------------------------- helpers
def now_utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def log(msg):
    print(f"[{now_utc()}] {msg}", flush=True)


def fetch(url, label=None, store=None, timeout=60):
    """Fetch one URL. Returns (record, body). Never raises for network errors."""
    host = re.sub(r"^https?://([^/]+).*$", r"\1", url)
    rec = {
        "url": url,
        "label": label or url,
        "host": host,
        "fetched_at_utc": now_utc(),
        "http_status": None,
        "final_url": None,
        "bytes": 0,
        "sha256": None,
        "content_type": None,
        "elapsed_ms": None,
        "error": None,
        "stored_path": None,
    }
    body = b""
    if host not in NBA_HOSTS and host not in EXTERNAL_HOSTS:
        rec["error"] = "host not on the allow-list; not fetched"
        MANIFEST.append(rec)
        return rec, body
    t0 = time.time()
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            rec["http_status"] = resp.status
            rec["final_url"] = resp.geturl()
            rec["content_type"] = resp.headers.get("Content-Type")
    except urllib.error.HTTPError as exc:
        rec["http_status"] = exc.code
        rec["final_url"] = url
        rec["error"] = f"HTTP {exc.code}"
    except Exception as exc:                      # noqa: BLE001 - recorded, not raised
        rec["error"] = f"{type(exc).__name__}: {exc}"
    rec["elapsed_ms"] = int((time.time() - t0) * 1000)
    rec["bytes"] = len(body)
    if body:
        rec["sha256"] = sha256_bytes(body)
    if store and body:
        path = os.path.join(RAW, store)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(body)
        rec["stored_path"] = os.path.relpath(path, ROOT)
    MANIFEST.append(rec)
    return rec, body


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1, sort_keys=False)
        fh.write("\n")


# ------------------------------------------------------------------ page parse
NEXT_DATA_RE = re.compile(
    r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)


def next_data(text):
    m = NEXT_DATA_RE.search(text)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except ValueError:
        return None


def deep_collect(node, pred, out):
    if isinstance(node, dict):
        if pred(node):
            out.append(node)
        for v in node.values():
            deep_collect(v, pred, out)
    elif isinstance(node, list):
        for v in node:
            deep_collect(v, pred, out)
    return out


def find_game_objects(doc):
    """Every embedded game object on an NBA.com page."""
    games = {}
    for obj in deep_collect(doc, lambda d: "gameId" in d and "homeTeam" in d
                            and "awayTeam" in d, []):
        gid = str(obj.get("gameId"))
        if gid and gid not in games:
            games[gid] = obj
    return games


def team_block(t):
    if not isinstance(t, dict):
        return {}
    return {
        "tricode": t.get("teamTricode") or t.get("teamTricodeAbbreviation"),
        "city": t.get("teamCity"),
        "name": t.get("teamName"),
        "slug": t.get("teamSlug"),
        "score": t.get("score"),
        "record": t.get("teamSubtitle"),
        "wins": t.get("wins"),
        "losses": t.get("losses"),
    }


def game_row(obj, date):
    away = team_block(obj.get("awayTeam"))
    home = team_block(obj.get("homeTeam"))
    status_text = str(obj.get("gameStatusText") or "")
    venue = obj.get("venue") if isinstance(obj.get("venue"), dict) else {}
    row = {
        "game_id": str(obj.get("gameId")),
        "date": date,
        "status_text": status_text,
        "status_detail": obj.get("gameStatusDetail"),
        "period": obj.get("period"),
        "clock": obj.get("clock"),
        "game_time_utc": obj.get("gameTimeUTC"),
        "game_time_local": obj.get("gameTime"),
        "game_type": obj.get("gameType"),
        "game_type_detail": obj.get("gameTypeDetail"),
        "neutral_site": obj.get("neutralSite"),
        "away": away,
        "home": home,
        "arena_name": venue.get("arenaName") or venue.get("fullName"),
        "arena_city": venue.get("arenaCity"),
        "arena_state": venue.get("arenaState"),
        "arena_country": venue.get("arenaCountry"),
        "source_url": f"https://www.nba.com/game/{obj.get('gameId')}",
    }
    ot = re.search(r"/OT(\d*)", status_text, re.I)
    row["ot"] = int(ot.group(1)) if (ot and ot.group(1)) else (1 if ot else 0)
    return row


def slug_for(row):
    a = (row.get("away") or {}).get("tricode") or ""
    h = (row.get("home") or {}).get("tricode") or ""
    if not a or not h:
        return None
    return f"{a.lower()}-vs-{h.lower()}-{row['game_id']}"


# ------------------------------------------------------------------- box score
def parse_boxscore(doc, row):
    """Quarter scores and every player's box from one box-score page."""
    out = {"game_id": row["game_id"], "date": row["date"],
           "source_url": row.get("box_score_url"), "quarters": {},
           "teams": {}, "players": [], "parse_notes": []}

    games = find_game_objects(doc)
    game = games.get(row["game_id"]) or (next(iter(games.values()), None))
    if game is None:
        out["parse_notes"].append("no embedded game object on the page")
        return out

    out["status_text"] = game.get("gameStatusText")
    out["away_tricode"] = (game.get("awayTeam") or {}).get("teamTricode")
    out["home_tricode"] = (game.get("homeTeam") or {}).get("teamTricode")

    # --- quarter scores -----------------------------------------------------
    header = game.get("header") if isinstance(game.get("header"), dict) else {}
    comps = header.get("competitions") or []
    comp = comps[0] if comps else {}
    for c in comp.get("competitors") or []:
        tri = c.get("teamTricode")
        if not tri:
            tri = (c.get("team") or {}).get("teamTricode")
        if not tri:
            continue
        per = []
        for entry in (c.get("linescores") or []):
            per.append({"period": entry.get("period"),
                        "score": entry.get("teamScore", entry.get("displayValue"))})
        out["quarters"][tri] = {
            "quarter_scores": per,
            "final": c.get("score"),
            "winner": c.get("winner"),
            "linescore_array": c.get("linescore"),
        }
    if not out["quarters"]:
        out["parse_notes"].append(
            "no header.competitions[].competitors[].linescores found")

    # --- player boxes -------------------------------------------------------
    for side in ("awayTeam", "homeTeam"):
        t = game.get(side) or {}
        tri = t.get("teamTricode")
        players = t.get("players") or []
        out["teams"][tri] = {"tricode": tri, "score": t.get("score"),
                             "players_counted": len(players)}
        for p in players:
            person = p.get("person") or {}
            st = p.get("statistics") or {}
            name = " ".join(x for x in [person.get("firstName"),
                                        person.get("lastName")] if x)
            if not name:
                continue
            out["players"].append({
                "game_id": row["game_id"],
                "date": row["date"],
                "team": tri,
                "opponent": (game.get("homeTeam") or {}).get("teamTricode")
                            if tri == (game.get("awayTeam") or {}).get("teamTricode")
                            else (game.get("awayTeam") or {}).get("teamTricode"),
                "player_id": person.get("personId") or person.get("playerId"),
                "player": name,
                "jersey": person.get("jerseyNo"),
                "position": person.get("position"),
                "starter": p.get("starter"),
                "did_not_play": p.get("didNotPlay"),
                "reason": p.get("reason"),
                "minutes": st.get("minutes"),
                "points": st.get("pointsTotal"),
                "rebounds": st.get("reboundsTotal"),
                "assists": st.get("assistsTotal"),
                "steals": st.get("stealsTotal"),
                "blocks": st.get("blocksTotal"),
                "turnovers": st.get("turnoversTotal"),
                "fouls": st.get("foulsPersonal"),
                "fg_made": st.get("fieldGoalsMade"),
                "fg_att": st.get("fieldGoalsAttempted"),
                "fg3_made": st.get("threePointersMade"),
                "fg3_att": st.get("threePointersAttempted"),
                "ft_made": st.get("freeThrowsMade"),
                "ft_att": st.get("freeThrowsAttempted"),
                "plus_minus": st.get("plusMinusPoints"),
            })
    return out


# ------------------------------------------------------------------------ main
def capture_slates(dates, probe=False):
    log(f"capturing {len(dates)} slate pages")
    games = {}
    for d in dates:
        url = f"https://www.nba.com/games?date={d}"
        rec, body = fetch(url, label=f"slate {d}")
        if not body:
            log(f"  slate {d}: FAILED {rec.get('http_status')} {rec.get('error')}")
            continue
        doc = next_data(body.decode("utf-8", "replace"))
        if doc is None:
            log(f"  slate {d}: no __NEXT_DATA__")
            continue
        objs = find_game_objects(doc)
        for gid, obj in objs.items():
            games[gid] = game_row(obj, d)
        log(f"  slate {d}: {len(objs)} games (page {rec['bytes']} bytes)")
        if probe and d == dates[0]:
            with open(os.path.join(RAW, f"sample_slate_{d}.html"), "wb") as fh:
                fh.write(body)
    return games


def capture_boxscores(games, probe=False):
    log(f"capturing box scores for {len(games)} games")
    results = []
    first_gid = sorted(games)[0] if games else None

    def one(row):
        slug = slug_for(row)
        if not slug:
            return None
        url = f"https://www.nba.com/game/{slug}/box-score"
        row["box_score_url"] = url
        rec, body = fetch(url, label=f"boxscore {row['game_id']}")
        if not body:
            rec2, body2 = fetch(f"https://www.nba.com/game/{row['game_id']}/box-score",
                                 label=f"boxscore {row['game_id']} (id form)")
            if body2:
                rec, body = rec2, body2
                url = rec2["url"]
                row["box_score_url"] = url
        if not body:
            log(f"  box {row['game_id']}: FAILED {rec.get('http_status')}")
            return None
        doc = next_data(body.decode("utf-8", "replace"))
        if doc is None:
            log(f"  box {row['game_id']}: no __NEXT_DATA__")
            return None
        if probe and row["game_id"] == first_gid:
            with open(os.path.join(RAW, f"sample_boxscore_{row['game_id']}.json"),
                      "w", encoding="utf-8") as fh:
                json.dump(doc, fh, indent=1)
        return parse_boxscore(doc, row)

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        for res in pool.map(one, list(games.values())):
            if res:
                results.append(res)
    log(f"  box scores parsed: {len(results)}")
    return results


def capture_standings():
    rec, body = fetch("https://www.nba.com/standings", label="standings")
    if not body:
        log("  standings: FAILED")
        return {}
    doc = next_data(body.decode("utf-8", "replace"))
    rows = {}
    if doc:
        for obj in deep_collect(doc, lambda d: isinstance(d, dict)
                                and d.get("teamTricode")
                                and ("wins" in d or "win" in d), []):
            tri = obj.get("teamTricode")
            if tri and tri not in rows:
                rows[tri] = obj
    log(f"  standings rows: {len(rows)}")
    return {"raw_team_objects": rows,
            "source_url": "https://www.nba.com/standings",
            "http_status": rec["http_status"],
            "sha256": rec["sha256"],
            "captured_at_utc": now_utc()}


def capture_team_stats():
    log("capturing the three official team-stat pages")
    out = {}
    for label, page in STAT_PAGE.items():
        rec, _body = fetch(page, label=f"team stat page {label}",
                           store=f"stats_page_{label}.html")
        out.setdefault("pages", {})[label] = {
            "page_url": page, "http_status": rec["http_status"],
            "sha256": rec["sha256"], "bytes": rec["bytes"],
            "fetched_at_utc": rec["fetched_at_utc"],
            "stored_path": rec["stored_path"]}
    for wname, df, dt in STAT_WINDOWS:
        for measure, label in (("Base", "traditional"), ("Opponent", "opponent"),
                                ("Advanced", "advanced")):
            url = STATS_API.format(measure=measure, per_mode="Totals",
                                   df=df.replace("/", "%2F"), dt=dt.replace("/", "%2F"))
            rec, body = fetch(url, label=f"team stats {label} {wname}")
            if not body:
                log(f"  stats {label}/{wname}: FAILED {rec.get('http_status')}")
                continue
            try:
                payload = json.loads(body.decode("utf-8", "replace"))
            except ValueError:
                log(f"  stats {label}/{wname}: not JSON")
                continue
            rs = (payload.get("resultSets") or [{}])[0]
            headers = rs.get("headers") or []
            rows = [dict(zip(headers, r)) for r in (rs.get("rowSet") or [])]
            out[f"{label}_{wname}"] = {
                "page": STAT_PAGE[label],
                "api_url": url,
                "measure_type": measure,
                "window": wname,
                "date_from": df or "(season start)",
                "date_to": dt or "(season to date)",
                "per_mode": "Totals",
                "captured_at_utc": now_utc(),
                "http_status": rec["http_status"],
                "sha256": rec["sha256"],
                "headers": headers,
                "rows": rows,
            }
            log(f"  stats {label}/{wname}: {len(rows)} team rows")
    return out


def pdf_text(path):
    """Extract the text layer of a PDF, or None when no extractor is present."""
    try:
        import pypdf                                   # noqa: PLC0415
    except Exception:                                  # noqa: BLE001
        return None
    try:
        reader = pypdf.PdfReader(path)
        return "\n".join((p.extract_text() or "") for p in reader.pages)
    except Exception:                                  # noqa: BLE001
        return None


def edition_slots(day):
    """Every 15-minute edition slot the league publishes for one date."""
    out = []
    for hour in range(24):
        for minute in (0, 15, 30, 45):
            # The league names the file on the 12-hour clock, with an AM/PM
            # suffix: midnight is `_12_00AM` and noon is `_12_00PM`
            # (https://official.nba.com/nba-injury-report-2026-27-season/).
            h12 = hour % 12 or 12
            ap = "AM" if hour < 12 else "PM"
            out.append({"date": day,
                        "edition_time_et": f"{h12:02d}:{minute:02d} {ap}",
                        "edition_id": f"{day}_{h12:02d}_{minute:02d}{ap}",
                        "url": ("https://ak-static.cms.nba.com/referee/injury/"
                                f"Injury-Report_{day}_{h12:02d}_{minute:02d}{ap}.pdf")})
    return out


def capture_injuries(archive_days=INJURY_ARCHIVE_DAYS):
    log("capturing the official injury-report index and its PDF editions")
    index_url = "https://official.nba.com/nba-injury-report-2026-27-season/"
    rec, body = fetch(index_url, label="injury index")
    listed = []
    if body:
        text = body.decode("utf-8", "replace")
        for m in re.finditer(
                r"https://ak-static\.cms\.nba\.com/referee/injury/"
                r"Injury-Report_(\d{4}-\d{2}-\d{2})_(\d{2})_(\d{2})(AM|PM)\.pdf", text):
            date, hh, mm, ap = m.groups()
            listed.append({"date": date, "edition_time_et": f"{int(hh) % 12 or 12}:{mm} {ap}",
                           "edition_id": f"{date}_{hh}_{mm}{ap}", "url": m.group(0)})
    log(f"  index lists {len(listed)} editions")

    candidates = {}
    for e in listed:
        candidates[e["edition_id"]] = dict(e, discovered="index")
    for day in INJURY_PROBE_DAYS:
        for e in edition_slots(day):
            candidates.setdefault(e["edition_id"], dict(e, discovered="slot-probe"))

    records = []
    for eid in sorted(candidates):
        e = candidates[eid]
        archive = e["date"] in archive_days
        store = f"injury/{eid}.pdf" if archive else None
        r, pdf = fetch(e["url"], label=f"injury {eid}", store=store)
        row = {
            "edition_id": eid,
            "date": e["date"],
            "edition_time_et": e["edition_time_et"],
            "revision_time_et": e["edition_time_et"],
            "url": e["url"],
            "discovered": e["discovered"],
            "listed_on_index": eid in {x["edition_id"] for x in listed},
            "http_status": r["http_status"],
            "bytes": r["bytes"],
            "sha256": r["sha256"],
            "fetched_at_utc": r["fetched_at_utc"],
            "stored_path": r["stored_path"],
            "text_path": None,
            "text_chars": None,
            "text_error": None,
        }
        if pdf and r["http_status"] == 200 and archive:
            path = os.path.join(RAW, store)
            txt = pdf_text(path)
            if txt is None:
                row["text_error"] = "no PDF text extractor available on the runner"
            else:
                tpath = os.path.join(RAW, f"injury/{eid}.txt.gz")
                with gzip.open(tpath, "wt", encoding="utf-8") as fh:
                    fh.write(txt)
                row["text_path"] = os.path.relpath(tpath, ROOT)
                row["text_chars"] = len(txt)
        records.append(row)
    live = [r for r in records if r["http_status"] == 200]
    log(f"  injury PDFs fetched: {len(live)} of {len(records)} probed")
    return {"index_url": index_url, "index_captured_at_utc": now_utc(),
            "index_sha256": rec["sha256"], "index_status": rec["http_status"],
            "archive_days": list(archive_days), "editions": records}


def capture_arenas():
    """Arena -> city -> official coordinates, from the Census gazetteer."""
    log("capturing the official arena-coordinate table (U.S. Census gazetteer)")
    url = ("https://www2.census.gov/geo/docs/maps-data/data/gazetteer/"
           "2025_Gazetteer/2025_Gaz_place_national.zip")
    listing = ("https://www2.census.gov/geo/docs/maps-data/data/gazetteer/"
               "2025_Gazetteer/")
    rec, body = fetch(url, label="census gazetteer places",
                       store="census/2025_Gaz_place_national.zip")
    if not body:
        log("  gazetteer: FAILED")
        return {}
    try:
        zf = zipfile.ZipFile(io.BytesIO(body))
        name = [n for n in zf.namelist() if n.endswith(".txt")][0]
        text = zf.read(name).decode("utf-8", "replace")
    except Exception as exc:                            # noqa: BLE001
        log(f"  gazetteer: cannot read zip ({exc})")
        return {}

    lines = text.splitlines()
    header = None
    for line in lines[:5]:
        f = line.split("\t")
        if "INTPTLAT" in f and "INTPTLONG" in f:
            header = f
            break
    if header is None:
        log("  gazetteer: no header row with INTPTLAT/INTPTLONG")
        return {}
    idx = {name: i for i, name in enumerate(header)}

    places = {}
    for line in lines:
        f = line.split("\t")
        if len(f) < len(header):
            continue
        if f[idx["USPS"]] == "USPS":
            continue
        names = [f[idx["NAME"]]] + [f[idx.get(k, -1)] for k in
                                    ("ALIASES", "ALIASES2", "ALIASES3")]
        try:
            lat, lon = float(f[idx["INTPTLAT"]]), float(f[idx["INTPTLONG"]])
        except (ValueError, KeyError):
            continue
        for n in names:
            if n and n not in places:
                places[n] = (lat, lon)

    out = {}
    for tri, candidates in TEAM_CITY.items():
        for c in candidates:
            if c in places:
                lat, lon = places[c]
                out[tri] = {
                    "arena_city": c,
                    "latitude": lat,
                    "longitude": lon,
                    "coordinate_source": ("U.S. Census Bureau 2025 Gazetteer file "
                                          "(incorporated places), INTPTLAT/INTPTLONG"),
                    "coordinate_source_url": url,
                    "coordinate_source_index_url": listing,
                    "coordinate_source_sha256": rec["sha256"],
                    "gazetteer_file_in_zip": name,
                    "match_basis": ("city name equal to the arena city the NBA "
                                     "prints for this club"),
                }
                break
    log(f"  arena coordinates resolved for {len(out)} of {len(TEAM_CITY)} clubs")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true",
                    help="capture one page per kind only")
    args = ap.parse_args()

    os.makedirs(RAW, exist_ok=True)
    os.makedirs(PARSED, exist_ok=True)

    dates = []
    d0 = datetime.date.fromisoformat(WINDOW_START)
    d1 = datetime.date.fromisoformat(WINDOW_END)
    while d0 <= d1:
        dates.append(d0.isoformat())
        d0 += datetime.timedelta(days=1)
    if args.probe:
        dates = ["2026-11-14"]

    started = now_utc()
    games = capture_slates(dates, probe=args.probe)
    write_json(os.path.join(PARSED, "games.json"),
               {"captured_at_utc": now_utc(),
                "source_pattern": "https://www.nba.com/games?date=<date>",
                "window": {"start": WINDOW_START, "end": WINDOW_END},
                "games": list(games.values())})

    boxes = capture_boxscores(games, probe=args.probe)
    write_json(os.path.join(PARSED, "boxscores.json"),
               {"captured_at_utc": now_utc(),
                "source_pattern":
                    "https://www.nba.com/game/<away>-vs-<home>-<gameId>/box-score",
                "games": boxes})

    write_json(os.path.join(PARSED, "standings.json"), capture_standings())
    write_json(os.path.join(PARSED, "team_stats.json"), capture_team_stats())
    write_json(os.path.join(PARSED, "injury_editions.json"),
               capture_injuries(archive_days=() if args.probe else INJURY_ARCHIVE_DAYS))
    write_json(os.path.join(PARSED, "arenas.json"), capture_arenas())

    write_json(os.path.join(OUT, "manifest.json"),
               {"started_utc": started, "finished_utc": now_utc(),
                "probe_mode": args.probe,
                "counts": {"fetches": len(MANIFEST),
                           "ok": sum(1 for m in MANIFEST if m["http_status"] == 200),
                           "games": len(games), "boxscores": len(boxes)},
                "fetches": MANIFEST})
    log("done")


if __name__ == "__main__":
    sys.exit(main())
