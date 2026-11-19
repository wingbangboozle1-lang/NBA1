"""Cross-check the transcribed standings against the official games feed.

    python3 scripts/verify_standings_89f7b601.py

WHAT THIS IS FOR (COORDINATION.md §69, session `arena/89f7b601-nba1`)

The scheduled refresh cannot produce a standings table by itself. That is now a
*measured* statement, not a suspicion, and the measurement has three parts:

  1. The delivered HTML of `https://www.nba.com/standings` contains **zero**
     `<tr>` elements, zero `/team/` links and zero `rowSet`
     (`data/raw/session-89f7b601/capture_manifest.json`, runner run
     44477742276). The table is mounted client-side, so no string parse can
     reach it.
  2. `stats.nba.com` - the data layer behind that table, read out of the page's
     own JS chunk - is **unreachable from a GitHub runner**: 4 endpoints x 3
     attempts x 25s, every attempt `TimeoutError`, no HTTP status, in the same
     run. The 2026-11-19T06:13Z scheduled run recorded the same thing.
  3. A headless Chromium on the runner gets **HTTP-level "Access Denied"**
     (Akamai `errors.edgesuite.net`) on the same URL: the rendered page is 298
     bytes of denial, 0 tables (`render_manifest.json`, run 44481346010).

So the standings input is blocked twice over. What is **not** blocked is the
official per-date games feed (`https://www.nba.com/games?date=...`), which the
scheduled job already fetches successfully for every game day, and which prints
each team's record beside its score (`teamSubtitle`, e.g. `11-4`). That feed is
the same origin, the same league, and it is reachable.

This module therefore **verifies** the transcribed standings table against a
source the CI pipeline can actually read, team by team, and reports how many of
the 30 rows are independently corroborated. It promotes nothing and writes no
snapshot: it is a check with a number attached.

IMPORTANT LIMIT, stated rather than papered over: the games feed carries only
W-L. It cannot corroborate GB, conference/division records, home/road splits,
LAST10, streak, or any of the three team-stat tables. Those remain single-source
(transcribed from the page) and are flagged as such. This module reports exactly
which fields are corroborated and which are not, per team.

Exit codes: 0 = every team corroborated and no disagreement; 4 = at least one
disagreement (a real discrepancy: two official sources contradicting each
other); 5 = the feed did not name enough teams to check (inconclusive, not a
pass).
"""

import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "engine"))

STANDINGS_GLOB = "data/official/standings_*_*.json"
RESULTS_GLOB = "data/raw/_capture_results_*.json"
OUT = os.path.join(ROOT, "data", "official",
                   "standings_corroboration_89f7b601.json")

# The minimum number of distinct teams the feed must name before the check is
# allowed to report a pass. A feed that names 6 teams has not verified anything.
MIN_TEAMS = 30


def newest(pattern):
    files = sorted(glob.glob(os.path.join(ROOT, pattern)))
    return files[-1] if files else None


def load_standings():
    """The most recent transcribed standings table and its provenance."""
    best = None
    for path in sorted(glob.glob(os.path.join(ROOT, STANDINGS_GLOB))):
        try:
            with open(path, encoding="utf-8") as fh:
                d = json.load(fh)
        except (OSError, ValueError):
            continue
        rows = d.get("rows") or []
        if len(rows) != 30:
            continue
        stamp = str(d.get("retrieved_utc") or "")
        if best is None or stamp >= best[1]:
            best = (path, stamp, d)
    if best is None:
        return None
    path, stamp, d = best
    return {
        "path": os.path.relpath(path, ROOT),
        "retrieved_utc": stamp,
        "source_url": d.get("source_url"),
        "captured_by": d.get("captured_by"),
        "rows": d["rows"],
        "columns": d.get("columns"),
    }


def feed_records():
    """Every team's W-L as the official games feed printed it, with the date.

    Keyed by tricode -> {date: "W-L"}. Dates are the game day, taken from the
    file name, so a later date is a later record.
    """
    out = {}
    sources = []
    for path in sorted(glob.glob(os.path.join(ROOT, RESULTS_GLOB))):
        m = re.search(r"(\d{4}-\d{2}-\d{2})", os.path.basename(path))
        if not m:
            continue
        day = m.group(1)
        try:
            with open(path, encoding="utf-8") as fh:
                d = json.load(fh)
        except (OSError, ValueError):
            continue
        rows = (d.get("parse") or {}).get("finals_rows") or []
        used = 0
        for r in rows:
            for side, key in (("away", "away_record_printed"),
                              ("home", "home_record_printed")):
                team = r.get(side)
                rec = r.get(key)
                if not team or not isinstance(rec, str):
                    continue
                if not re.fullmatch(r"\d{1,2}-\d{1,2}", rec.strip()):
                    continue
                out.setdefault(team, {})[day] = rec.strip()
                used += 1
        if used:
            sources.append({"file": os.path.relpath(path, ROOT), "game_date": day,
                            "records_read": used,
                            "source_url": d.get("source_url")})
    return out, sources


def main():
    st = load_standings()
    if st is None:
        print("no 30-row transcribed standings table found")
        return 5
    official = {}
    for r in st["rows"]:
        official[r.get("abbr")] = (r.get("w"), r.get("l"))
    records, sources = feed_records()

    # Each team is checked against its LATEST printed record that is not later
    # than the standings read date - a record printed after the standings were
    # read would be comparing two different days.
    read_day = (st["retrieved_utc"] or "")[:10]
    per_team = []
    agree = disagree = absent = 0
    for team in sorted(official):
        w, l = official[team]
        days = sorted(d for d in records.get(team, {}) if d <= read_day)
        row = {"team": team, "standings_w": w, "standings_l": l}
        if not days:
            absent += 1
            row["status"] = "not_named_by_feed"
            row["feed_record"] = None
            row["feed_game_date"] = None
            row["feed_source_url"] = None
        else:
            day = days[-1]
            feed = records[team][day]
            fw, fl = (int(x) for x in feed.split("-"))
            row["feed_record"] = feed
            row["feed_game_date"] = day
            row["feed_source_url"] = f"https://www.nba.com/games?date={day}"
            if (fw, fl) == (w, l):
                agree += 1
                row["status"] = "agree"
            else:
                disagree += 1
                row["status"] = "DISAGREE"
                row["delta"] = {"w": w - fw, "l": l - fl}
        # Fields the feed cannot corroborate at all. Listed per team so the
        # site can render them as single-source rather than implying a check.
        row["uncorroborated_fields"] = [
            "rank", "win_pct", "gb", "conf_rec", "div_rec", "home", "road",
            "neutral", "ot", "last10", "streak"]
        per_team.append(row)

    checked = agree + disagree
    if checked < MIN_TEAMS:
        verdict = "INCONCLUSIVE"
        code = 5
        why = (f"the feed named only {checked} of the 30 teams with a usable "
               f"record on or before {read_day}; that is not a verification")
    elif disagree:
        verdict = "DISAGREEMENT"
        code = 4
        why = f"{disagree} team(s) disagree between two official sources"
    else:
        verdict = "CORROBORATED"
        code = 0
        why = (f"all {agree} teams the feed names agree exactly with the "
               f"transcribed table, on W and L")

    payload = {
        "title": "Standings corroboration against the official games feed",
        "generated_by": "scripts/verify_standings_89f7b601.py",
        "generated_for": "COORDINATION.md §69 (session arena/89f7b601-nba1)",
        "rule": ("A standings row is CORROBORATED only when a second official "
                 "source, read by the CI pipeline itself, prints the same W-L. "
                 "Fields the second source does not carry are listed as "
                 "uncorroborated rather than assumed."),
        "why_this_check_exists": (
            "The standings page cannot be parsed (0 <tr> in the delivered "
            "HTML), its data layer stats.nba.com times out from a runner "
            "(4 endpoints x 3 attempts, all TimeoutError), and headless "
            "Chromium on a runner receives Akamai 'Access Denied'. The per-date "
            "games feed is reachable and prints each team's record beside its "
            "score, so it is the only official second source the pipeline can "
            "read."),
        "verdict": verdict,
        "verdict_detail": why,
        "summary": {
            "teams_in_standings": len(official),
            "teams_checked": checked,
            "agree": agree,
            "disagree": disagree,
            "not_named_by_feed": absent,
            "read_day": read_day,
        },
        "standings_under_test": {
            "file": st["path"],
            "source_url": st["source_url"],
            "retrieved_utc": st["retrieved_utc"],
            "captured_by": st["captured_by"],
        },
        "feed_sources": sources,
        "per_team": per_team,
        "what_this_does_not_prove": [
            "It does not verify GB, conference or division records, home/road/"
            "neutral splits, OT records, LAST10 or streak: the games feed does "
            "not carry them.",
            "It does not verify the traditional, opponent or advanced team-stat "
            "tables at all; those have no second reachable official source and "
            "remain single-source (transcribed).",
            "It is not a substitute for the standings page: a printed record is "
            "a snapshot as at that game day, so a team idle since an earlier "
            "date is checked against that earlier date.",
        ],
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1)
        fh.write("\n")
    print(f"verdict: {verdict} - {why}")
    print(f"teams checked {checked}/{len(official)}; agree {agree}; "
          f"disagree {disagree}; not named {absent}")
    for row in per_team:
        if row["status"] == "DISAGREE":
            print(f"  DISAGREE {row['team']}: standings "
                  f"{row['standings_w']}-{row['standings_l']} vs feed "
                  f"{row['feed_record']} on {row['feed_game_date']}")
    print("wrote", os.path.relpath(OUT, ROOT))
    return code


if __name__ == "__main__":
    sys.exit(main())
