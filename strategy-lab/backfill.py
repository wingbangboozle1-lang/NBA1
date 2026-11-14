"""Module 1 - backfill verification and completeness proof for the season game log.

Three independent official instruments have to agree before this repository is allowed to
say what its own game log is worth:

  A. the 23 rows this session read off the two day pages that the repository holds as
     fixtures without results - compared row by row with the copy already committed;
  B. the per-date game count printed in the official calendar block on the same pages;
  C. the per-team games-played column of the official team table.

A. is a second reading of the same pages by a different session. B. and C. are different
pages measuring the same quantity, which is what turns "we think two dates are missing"
into a number.
"""
from __future__ import annotations

from statools import rnd

DAY_PAGE = "https://www.nba.com/games?date="
TEAM_TABLE = "https://www.nba.com/stats/teams/advanced"


def run(ctx):
    log, mine = ctx["log"], ctx["mine"]
    fixtures_repo, fin13 = ctx["fixtures_repo"], ctx["fin13"]
    teams_official, games = ctx["teams_official"], ctx["games"]

    # ---- A. the fixture rows, row by row
    rows = []
    mine_by_id = {f["game_id"]: f for f in mine["fixtures"]}
    repo_by_id = {f["game_id"]: f for f in fixtures_repo}
    match = disagree = 0
    for gid in sorted(set(mine_by_id) | set(repo_by_id)):
        a, b = mine_by_id.get(gid), repo_by_id.get(gid)
        ref = a or b
        if a and b:
            same = (a["date"] == b["date"] and a["away"] == b["away"]
                    and a["home"] == b["home"])
            match += 1 if same else 0
            disagree += 0 if same else 1
            verdict = "MATCH" if same else "DISAGREE"
        else:
            disagree += 1
            verdict = "PRESENT IN ONLY ONE READING"
        rows.append({
            "date": ref["date"], "game_id": gid,
            "fixture": f"{ref['away']}@{ref['home']}",
            "status_printed": (a or {}).get("status_printed", "FINAL"),
            "score_this_session": "printed as '-'",
            "score_in_repo": "absent from the log",
            "verdict": verdict,
            "source_url": ref["source_url"],
            "day_page": ref.get("day_page") or (DAY_PAGE + ref["date"]),
        })

    # ---- B. per-date completeness against the official calendar block
    cal = mine["calendar_game_counts"]
    counts = {f"2026-10-{k.zfill(2)}": v for k, v in cal["october_2026"].items()
              if f"2026-10-{k.zfill(2)}" >= "2026-10-20"}
    counts.update({f"2026-11-{k.zfill(2)}": v for k, v in cal["november_2026"].items()})
    per_date = {}
    for g in games:
        slot = per_date.setdefault(g["date"], {"scored": 0, "fixture": 0, "horizon": 0})
        slot[g["kind"]] += 1
    date_rows, bad_dates = [], []
    for date in sorted(counts):
        if date > "2026-11-17":
            continue
        got = per_date.get(date, {"scored": 0, "fixture": 0, "horizon": 0})
        total = got["scored"] + got["fixture"] + got["horizon"]
        exp = counts[date]
        okflag = total == exp
        if not okflag:
            bad_dates.append(date)
        date_rows.append({
            "date": date, "official_calendar_count": exp,
            "scored_rows": got["scored"], "fixture_rows": got["fixture"],
            "unplayed_rows": got["horizon"], "rows_total": total,
            "verdict": "match" if okflag else "MISMATCH",
            "source_url": DAY_PAGE + date,
        })

    # ---- C. per-team reconciliation against the official games-played column
    log_gp = {}
    for g in games:
        if g["kind"] == "horizon":
            continue
        log_gp[g["away"]] = log_gp.get(g["away"], 0) + 1
        log_gp[g["home"]] = log_gp.get(g["home"], 0) + 1
    team_rows, bad_teams = [], []
    for abbr, t in sorted(teams_official.items()):
        fin = sum(1 for r in fin13 if abbr in (r["away"], r["home"]))
        want = t["gp"] + fin
        have = log_gp.get(abbr, 0)
        okflag = have == want
        if not okflag:
            bad_teams.append(abbr)
        team_rows.append({
            "team": abbr, "name": t["team"],
            "official_gp_through_11_12": t["gp"], "finals_11_13": fin,
            "expected_rows": want, "rows_in_repaired_log": have,
            "scored_rows_only": sum(1 for g in games if g["kind"] == "scored"
                                    and abbr in (g["away"], g["home"])),
            "verdict": "match" if okflag else "MISMATCH",
            "source_url": t.get("source_url") or TEAM_TABLE,
        })

    # ---- the second reading of the 11/13 finals
    inc = mine["incidental_official_read_of_2026-11-13_finals"]["finals_2026_11_13"]
    repo13 = {r["game_id"]: r for r in fin13}
    fin_rows, fin_ok, fin_bad = [], 0, 0
    for r in inc:
        b = repo13.get(r["game_id"])
        same = bool(b) and b["away"] == r["away"] and b["home"] == r["home"] \
            and b["away_score"] == r["away_pts"] and b["home_score"] == r["home_pts"]
        fin_ok += 1 if same else 0
        fin_bad += 0 if same else 1
        fin_rows.append({
            "game_id": r["game_id"], "fixture": f"{r['away']}@{r['home']}",
            "read_by_this_session": f"{r['away_pts']}-{r['home_pts']}",
            "in_repo_transcription": f"{b['away_score']}-{b['home_score']}" if b else "not found",
            "cup_group_printed": r["cup_group_printed"],
            "verdict": "agree" if same else "DISAGREE",
            "source_url": (b or {}).get("source_url") or
            f"https://www.nba.com/game/{r['away'].lower()}-vs-{r['home'].lower()}-{r['game_id']}",
        })

    scored_n = sum(1 for g in games if g["kind"] == "scored")
    fixture_n = sum(1 for g in games if g["kind"] == "fixture")
    horizon_n = sum(1 for g in games if g["kind"] == "horizon")
    return {
        "as_of": "2026-11-14",
        "summary": {
            "scored_games": scored_n,
            "fixtures_without_published_scores": fixture_n,
            "unplayed_horizon_games": horizon_n,
            "fixture_rows_compared": len(rows),
            "fixture_rows_matching_repo": match,
            "fixture_rows_disagreeing": disagree,
            "dates_checked": len(date_rows),
            "dates_mismatched": len(bad_dates),
            "dates_mismatched_list": bad_dates,
            "teams_checked": len(team_rows),
            "teams_mismatched": len(bad_teams),
            "teams_mismatched_list": bad_teams,
            "finals_11_13_agreeing": fin_ok,
            "finals_11_13_disagreeing": fin_bad,
            "log_rows_before_this_session": len(log["games"]),
            "team_slots_the_log_covers": scored_n * 2,
            "team_slots_the_official_table_implies": sum(t["gp"] for t in teams_official.values())
            + 2 * len(fin13),
        },
        "fixture_rows": rows,
        "date_rows": date_rows,
        "team_rows": team_rows,
        "finals_rows": fin_rows,
        "sources": {
            "day_pages": [mine["day_pages"]["2026-10-24"]["url"],
                          mine["day_pages"]["2026-11-02"]["url"]],
            "calendar_block": [cal["october_source_url"], cal["november_source_url"]],
            "team_table": TEAM_TABLE,
            "log_in_repo": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/data/official/gamelog.json",
        },
        "method_note": (
            "The official day page for an archived date renders the fixture (both teams, a game id, "
            "the word FINAL) and prints '-' in every score, record and leader cell. The same page for a "
            "recent date prints the score. That asymmetry is the reason 23 games of this season cannot be "
            "graded from official pages: the results exist, the page this repository is allowed to read "
            "does not show them. The fixtures are therefore used to repair the SCHEDULE layer and never "
            "to supply a score."
        ),
        "irregularity": (
            "Reproduced a third time by a different session on 2026-11-14 at 10:38-10:44 UTC: 8 games on "
            "2026-10-24 and 15 on 2026-11-02, all FINAL, all with an empty score cell. No score inferred."
        ),
    }
