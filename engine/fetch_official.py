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

ALLOWED_HOSTS = {"www.nba.com", "official.nba.com", "ak-static.cms.nba.com"}

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
FINAL_RE = re.compile(r"\bFinal(?:/OT\d*)?\b")
RECORD_RE = re.compile(r"\b\d{1,2}-\d{1,2}\b")

# Injury-report editions are published at fixed times on game days. The first
# three names are proven to exist for 2026-11-13 (HTTP 200 in the probe
# record); 07_30PM is included because a session captured that edition name
# from the official index page. An edition that returns 403 is recorded as
# unavailable at capture time - ak-static answers 403 both for absent objects
# and for some clients, so 403 is never treated as proof of absence.
INJURY_EDITION_TIMES = ("12_00PM", "03_00PM", "05_15PM", "07_30PM")
INJURY_HOST = "https://ak-static.cms.nba.com/referee/injury/"


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
    """Pull the 30-team advanced table out of the rendered page.

    The nba.com stats pages embed their table data as JSON. We look for the
    per-team rows rather than trying to scrape <td> cells, because the table is
    client-rendered. If the JSON cannot be found, we return [] and the caller
    leaves the existing file alone rather than writing garbage.
    """
    out = []
    # The embedded payload lists resultSets[0].rowSet as [teamId, teamName, ...]
    for m in re.finditer(r'"rowSet"\s*:\s*\[(.*?)\]\s*,\s*"name"\s*:', text, re.S):
        body = m.group(1)
        for row in re.finditer(r"\[(.*?)\]", body, re.S):
            cells = re.findall(r'-?\d+\.?\d*|"([^"]*)"', row.group(1))
            vals = [c if isinstance(c, str) else c for c in cells]
            if len(vals) >= 26 and isinstance(vals[1], str) and vals[1] in ABBR:
                out.append(vals)
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
    # Edition names look like Injury-Report_2026-11-13_05_15PM.pdf: the date
    # contains hyphens. The pre-execution version of this pattern used
    # [0-9_]+ after the prefix, which can never consume "2026-11-13" and so
    # returned zero editions on every page - found by the unit test in
    # COORDINATION.md section 15 (R02) before the first executed run.
    links = re.findall(
        r'https://ak-static\.cms\.nba\.com/referee/injury/(Injury-Report_[0-9\-_]+PM\.pdf)',
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


# ---------------------------------------------------------------- game results
def excerpt_around(text, needle, before=800, span=4000):
    """Bounded raw-text excerpt around the first occurrence of `needle`."""
    i = text.find(needle)
    if i < 0:
        return None
    start = max(0, i - before)
    return text[start:start + span]


def parse_games_page(text, known):
    """Parse one https://www.nba.com/games?date=... page into finals rows.

    `known` maps game_id -> {away, home, date} from the committed snapshots
    (data/raw/games_completed.json + data/raw/schedule_upcoming.json).

    Rules:
      * a game id can occur several times in the raw HTML (card link, box
        score link, embedded schedule JSON). EVERY occurrence is tried; a
        game counts as final only when one of its own slices contains the
        status word - the first-executed run showed that trusting the first
        occurrence alone misses the score card entirely;
      * tags and hrefs are stripped before reading, so attributes cannot be
        mistaken for text;
      * the status word "Final" (or "Final/OTn") must be present - a game
        that is live or scheduled is recorded as not_final, never guessed;
      * the away score is the last integer before the status, the home score
        the first integer after it; records (6-5) are removed first so they
        cannot be mistaken for scores;
      * anything that does not satisfy these rules lands in `unparsed` with a
        reason. No score is ever inferred.

    Returns (rows, not_final, unparsed, occurrences).
    """
    rows, not_final, unparsed = [], [], []
    parsed = {}          # gid -> row
    final_seen = set()   # gid had Final in at least one slice
    occurrences = {}     # gid -> number of times linked
    matches = list(GAME_LINK_RE.finditer(text))
    for i, m in enumerate(matches):
        away, home, gid = m.group(1).upper(), m.group(2).upper(), m.group(3)
        occurrences[gid] = occurrences.get(gid, 0) + 1
        if gid in parsed:
            continue
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        # The slice is bounded by the next /game/ link, which for a finished
        # game is commonly that same game's "Box score" link - i.e. the slice
        # covers one card-shaped region of the page.
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
        ot_m = re.search(r"/OT(\d+)", status)
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
    return rows, not_final, unparsed, occurrences



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
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    if today not in dates:
        dates.append(today)
    for d in dates:
        url = f"https://www.nba.com/games?date={d}"
        try:
            raw = get(url)
        except Exception as exc:                       # noqa: BLE001
            failed.append((f"results {d}", f"fetch failed: {exc}"))
            continue
        text = as_text(raw)
        rows, not_final, unparsed, occurrences = parse_games_page(text, known)
        # dedupe unparsed reasons per game (a game can fail on several slices)
        seen_unparsed = set()
        unparsed = [u for u in unparsed
                    if not (u["game_id"] in seen_unparsed
                            or seen_unparsed.add(u["game_id"]))]
        mismatches, candidates = compare_to_snapshot(rows, known, committed)
        parsed_ids = {r["game_id"] for r in rows}
        missed = sorted(gid for gid, c in committed.items()
                        if c["date"] == d and gid not in parsed_ids)
        log(f"  {d}: {len(rows)} finals, {len(not_final)} not final, "
            f"{len(unparsed)} unparsed, {len(mismatches)} snapshot mismatches, "
            f"{len(missed)} committed finals missed")
        payload = {
            "captured_at_utc": now,
            "source_url": url,
            "page_bytes": len(raw),
            "page_sha256": hashlib.sha256(raw).hexdigest(),
            "parse": {"strategy": "anchor-text v2 (every link occurrence tried)",
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


def capture_injury(now, changed, failed, index_editions):
    """Fetch the newest report PDFs fully; probe today's/yesterday's editions.

    Every HTTP status is recorded. 403 means 'unavailable to this client at
    this time', never 'does not exist'.
    """
    candidates = []
    for e in index_editions[:2]:
        candidates.append(e)
    today = datetime.datetime.now(datetime.timezone.utc).date()
    for delta in (0, 1):
        day = today - datetime.timedelta(days=delta)
        for t in INJURY_EDITION_TIMES:
            name = f"Injury-Report_{day.isoformat().replace('-', '_')}_{t}.pdf"
            if name not in candidates:
                candidates.append(name)
    results = []
    for edition in candidates[:12]:
        url = INJURY_HOST + edition
        rec = {"edition": edition, "url": url, "http_status": None,
               "bytes": 0, "sha256": None, "attempts": 0}
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
                                     "content_type": "application/pdf"}):
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

        if kind == "teams_advanced":
            rows = parse_teams_advanced(text)
            if len(rows) != 30:
                failed.append((key, f"expected 30 team rows, parsed {len(rows)}"))
                log(f"  SKIPPED: parsed {len(rows)} rows - keeping the existing snapshot")
                needles = ["rowSet", "resultSets", "Boston Celtics"]
                if write_if_changed(
                        os.path.join(RAW, f"_capture_evidence_{key}.json"),
                        {"captured_at_utc": now, "source_url": url,
                         "status": "parse_failed",
                         "indicators": {n: text.count(n) for n in needles},
                         "failure_evidence": [
                             {"around": n, "excerpt": e} for n in needles
                             for e in [excerpt_around(text, n)] if e][:2],
                         "note": "Bounded raw-HTML evidence for the next parser "
                                 "iteration. The committed snapshot is untouched."}):
                    changed.append(f"evidence {key}")
                continue
            log(f"  parsed {len(rows)} team rows")
            # A full rewrite of team_advanced.json needs the window metadata and
            # every column; only rewrite when all 30 rows for both windows parse.
            # Here we just record the raw capture for a human/verifier to diff.
            if write_if_changed(os.path.join(RAW, f"_capture_{key}.json"),
                                {"captured_at_utc": now, "source_url": url,
                                 "row_count": len(rows),
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
