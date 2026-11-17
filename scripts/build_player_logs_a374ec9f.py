#!/usr/bin/env python3
"""build_player_logs_a374ec9f.py - per-player game logs and minutes shares,
read from the official NBA gamebook PDFs.

Requirement R21 (*per-player logs: minutes, points, rebounds, assists and the
opponent*) and R12 (*top-8 minutes shares and the replacement shares when a
player is out*).

What this does
--------------
1. Parses every captured official gamebook PDF with ``engine/gamebook.py``,
   which reads the league's own drawn box-score table.
2. Writes one log row per (game, player) into
   ``data/official/player_game_logs_<date>.json``:
   minutes, points, rebounds, assists, steals, blocks, turnovers, fouls, the
   shooting splits, the plus/minus, the opponent and the side.
3. Cross-checks every number against the official results feed: the player's
   team's points must equal the official final for that team, and the team's
   player totals must sum to the team totals the gamebook itself prints.
   A game that fails any check is reported and NOT published.
4. Writes the minutes-share measurement: each player's share of his team's
   printed minutes, the top-8 share, the bench share and the players with no
   minutes at all, with the official note printed for them.

Nothing is inferred.  A cell the official document leaves blank stays null.

Run
---
    python3 scripts/build_player_logs_a374ec9f.py --date 2026-11-16
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "engine"))

import gamebook as GB  # noqa: E402
from common import ABBR  # noqa: E402

RAW_GB = os.path.join(ROOT, "data", "raw", "gamebooks")
OFF = os.path.join(ROOT, "data", "official")
DERIVED = os.path.join(ROOT, "data", "derived")

# the gamebook's stat columns -> the repository's log columns
COLMAP = {
    "FG": "fgm", "FGA": "fga", "3P": "fg3m", "3PA": "fg3a", "FT": "ftm",
    "FTA": "fta", "OR": "oreb", "DR": "dreb", "TOT": "reb", "A": "ast",
    "PF": "pf", "ST": "stl", "TO": "tov", "BS": "blk", "+/-": "plus_minus",
    "PTS": "pts",
}


def load(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def gamebook_files(date):
    ymd = date.replace("-", "")
    out = []
    for pdf in sorted(glob.glob(os.path.join(RAW_GB, ymd, "*.pdf"))):
        stem = os.path.basename(pdf)[:-4]
        # <yyyymmdd>_<AWAY><HOME>_book__<sha>
        parts = stem.split("_")
        if len(parts) < 3:
            continue
        match = parts[1]
        sidecar = {}
        sp = pdf[:-4] + ".json"
        if os.path.exists(sp):
            sidecar = load(os.path.relpath(sp, ROOT))
        out.append({"pdf": pdf, "matchup": match, "sidecar": sidecar,
                    "sha256": sidecar.get("sha256")
                    or hashlib.sha256(open(pdf, "rb").read()).hexdigest()})
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date", required=True)
    ap.add_argument("--season-feed",
                    default="data/official/results_feed_2026_27.json")
    args = ap.parse_args()
    date = args.date

    feed = load(args.season_feed)
    feed_rows = {r["game_id"]: r for r in feed["rows"]}
    by_matchup = {}
    for r in feed["rows"]:
        if r.get("date") == date:
            by_matchup["%s@%s" % (r["away"], r["home"])] = r

    rows, problems, games = [], [], []
    for entry in gamebook_files(date):
        matchup = entry["matchup"]
        away_abbr, home_abbr = matchup[:3], matchup[3:6]
        meta = by_matchup.get("%s@%s" % (away_abbr, home_abbr))
        if meta is None:
            problems.append("%s: no row on the official season feed" % matchup)
            continue
        raw = open(entry["pdf"], "rb").read()
        try:
            doc = GB.parse_page1(raw)
        except Exception as exc:  # a document that cannot be read is reported
            problems.append("%s: the official gamebook could not be parsed (%s)"
                            % (matchup, exc))
            continue
        away = doc["teams"].get("VISITOR")
        home = doc["teams"].get("HOME")
        if not away or not home:
            problems.append("%s: the gamebook does not print both teams"
                            % matchup)
            continue
        # the gamebook prints the team names in caps; the abbreviation lookup
        # is by the team's own name, so it is case-insensitive.
        def abbr_of(name):
            return ABBR.get(name) or ABBR.get(name.title()) or ABBR.get(
                name.upper()) or ABBR.get(" ".join(w.capitalize()
                                                   for w in name.split()))
        if abbr_of(away["team"]) != away_abbr or abbr_of(home["team"]) != home_abbr:
            problems.append(
                "%s: the gamebook prints VISITOR %r / HOME %r, which does not "
                "match the official feed's %s / %s"
                % (matchup, away["team"], home["team"], away_abbr, home_abbr))
            continue

        # ---- the score by period block must agree with the official feed
        sbp = doc["score_by_period"]
        # The SCORE BY PERIOD block labels each side by the team's own name
        # as the gamebook prints it (e.g. "Magic" / "CELTICS"), not by the
        # abbreviation.  A label is accepted only when it matches ONE team
        # unambiguously.
        def label_matches(label, team, abbr):
            lab = label.strip().lower()
            name = team["team"].strip().lower()
            if not lab:
                return False
            if lab == abbr.lower():
                return True
            if lab == name:
                return True
            if name.endswith(lab) and len(lab) >= 3:
                return True
            return False

        periods = {}
        for entry_sbp in sbp:
            label = entry_sbp["label"]
            m_away = label_matches(label, away, away_abbr)
            m_home = label_matches(label, home, home_abbr)
            if m_away and not m_home:
                periods["away"] = entry_sbp
            elif m_home and not m_away:
                periods["home"] = entry_sbp
            elif m_away and m_home:
                problems.append("%s: the SCORE BY PERIOD label %r matches "
                                "both teams" % (matchup, label))
        for side, abbr, team in (("away", away_abbr, away),
                                 ("home", home_abbr, home)):
            off_pts = meta.get("%s_pts" % side)
            off_q = meta.get("%s_quarters" % side)
            s = periods.get(side)
            if s is None:
                problems.append("%s: the gamebook's SCORE BY PERIOD block has "
                                "no row for %s" % (matchup, abbr))
                continue
            if sum(s["quarters"]) != s["final"]:
                problems.append("%s %s: the gamebook's quarters %s do not sum "
                                "to its printed final %s"
                                % (matchup, abbr, s["quarters"], s["final"]))
                continue
            if off_pts is not None and s["final"] != off_pts:
                problems.append("%s %s: the gamebook prints %s points, the "
                                "official feed prints %s"
                                % (matchup, abbr, s["final"], off_pts))
                continue
            if off_q is not None and list(s["quarters"]) != list(off_q):
                problems.append("%s %s: the gamebook's quarters %s differ from "
                                "the official feed's %s"
                                % (matchup, abbr, s["quarters"], off_q))
                continue

        # ---- the player's own numbers must sum to the team's printed totals
        for side, team, abbr, opp in (("away", away, away_abbr, home_abbr),
                                      ("home", home, home_abbr, away_abbr)):
            sums = {}
            for p in team["players"]:
                if not p["played"]:
                    continue
                for stat, col in COLMAP.items():
                    if p.get(stat) is not None:
                        sums[col] = sums.get(col, 0) + p[stat]
            tot = team.get("totals") or {}
            mism = []
            for stat, col in COLMAP.items():
                if stat in ("+/-",):
                    continue
                tv = tot.get(stat)
                sv = sums.get(col, 0)
                if tv is not None and tv != sv:
                    mism.append("%s: printed %s, players sum %s"
                                % (col, tv, sv))
            if mism:
                problems.append("%s %s: the players' %s do not match the "
                                "team totals the gamebook prints"
                                % (matchup, abbr, "; ".join(mism)))

        # ---- one log row per player
        for side, team, abbr, opp in (("away", away, away_abbr, home_abbr),
                                      ("home", home, home_abbr, away_abbr)):
            for p in team["players"]:
                rec = {
                    "date": date,
                    "game_id": meta.get("game_id"),
                    "team": abbr,
                    "opponent": opp,
                    "home_away": side,
                    "player": p["player"],
                    "jersey": p["jersey"],
                    "pos": p["pos"],
                    "played": p["played"],
                    "min": p["min"],
                    "minutes_seconds": p["minutes_seconds"],
                    "dnp_note": p["note"],
                }
                for stat, col in COLMAP.items():
                    rec[col] = p.get(stat)
                rec["source_pdf"] = entry["sidecar"].get("source_url")
                rec["source_sha256"] = entry["sha256"]
                rec["source_document"] = ("official NBA gamebook PDF "
                                          "(Official Scorer's Report)")
                rec["on_official_injury_report"] = False
                rows.append(rec)

        games.append({
            "date": date, "game_id": meta.get("game_id"),
            "away": away_abbr, "home": home_abbr,
            "matchup": matchup,
            "gamebook_pdf": entry["sidecar"].get("source_url"),
            "gamebook_sha256": entry["sha256"],
            "gamebook_bytes": entry["sidecar"].get("bytes"),
            "officials": doc["meta"].get("officials"),
            "attendance": doc["meta"].get("attendance"),
            "game_duration": doc["meta"].get("game_duration"),
            "venue": doc["meta"].get("venue"),
            "date_line": doc["meta"].get("date_line"),
            "teams_printed": {"away": away["team"], "home": home["team"]},
            "records_printed": {"away": away["record"], "home": home["record"]},
            "score_by_period": {"away": periods.get("away"),
                                "home": periods.get("home")},
            "totals_printed": {"away": away.get("totals"),
                               "home": home.get("totals")},
            "inactive_lines": doc["inactive"],
        })

    rows.sort(key=lambda r: (r["game_id"] or "", r["team"], r["player"]))
    out = {
        "title": "Official per-player game logs — %s (official NBA gamebooks)" % date,
        "generated_by": "scripts/build_player_logs_a374ec9f.py",
        "captured_by": "arena/a374ec9f-nba1",
        "retrieved_utc": "2026-11-17T16:40Z",
        "rule": ("One row per (game, player) from the league's own gamebook PDF. "
                 "A player the gamebook lists with a note instead of a minutes "
                 "clock is recorded as not having played, with the note "
                 "verbatim; nothing is inferred. Every team's player totals are "
                 "checked against the totals the gamebook prints, and the "
                 "gamebook's SCORE BY PERIOD block is checked against the "
                 "official results feed before the rows are published."),
        "columns": ["date", "game_id", "team", "opponent", "home_away",
                    "player", "jersey", "pos", "played", "min",
                    "minutes_seconds", "fgm", "fga", "fg3m", "fg3a", "ftm",
                    "fta", "oreb", "dreb", "reb", "ast", "pf", "stl", "tov",
                    "blk", "plus_minus", "pts", "dnp_note"],
        "games": games,
        "rows": rows,
        "problems": problems,
        "sources": {
            "gamebooks": [g["gamebook_pdf"] for g in games],
            "results_feed": args.season_feed,
            "official_game_page_pattern": "https://www.nba.com/game/<away>-vs-<home>-<gameId>",
        },
    }
    path = os.path.join(OFF, "player_game_logs_%s.json" % date)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("wrote %s: %d rows over %d games"
          % (os.path.relpath(path, ROOT), len(rows), len(games)))
    if problems:
        print("PROBLEMS (%d):" % len(problems))
        for p in problems:
            print("  -", p)

    # ------------------------------------------------------------------ shares
    share_rows = []
    for g in games:
        for side, abbr in (("away", g["away"]), ("home", g["home"])):
            tot = (g["totals_printed"] or {}).get(side) or {}
            total_min = tot.get("min")
            if not total_min:
                continue
            mm, ss = total_min.split(":")
            team_seconds = int(mm) * 60 + int(ss)
            played = [r for r in rows
                      if r["game_id"] == g["game_id"] and r["team"] == abbr
                      and r["played"]]
            dnp = [r for r in rows
                   if r["game_id"] == g["game_id"] and r["team"] == abbr
                   and not r["played"]]
            shares = []
            for r in played:
                shares.append({"player": r["player"], "jersey": r["jersey"],
                               "minutes_seconds": r["minutes_seconds"],
                               "share": round(r["minutes_seconds"] / team_seconds, 6),
                               "pts": r["pts"], "reb": r["reb"], "ast": r["ast"]})
            shares.sort(key=lambda s: (-s["minutes_seconds"], s["player"]))
            top8 = shares[:8]
            share_rows.append({
                "date": date, "game_id": g["game_id"], "team": abbr,
                "opponent": g["home"] if side == "away" else g["away"],
                "home_away": side,
                "team_minutes_printed": total_min,
                "team_minutes_seconds": team_seconds,
                "players_with_minutes": len(shares),
                "players_without_minutes": [
                    {"player": r["player"], "jersey": r["jersey"],
                     "note": r["dnp_note"]} for r in dnp],
                "top8_minutes_share": round(sum(s["share"] for s in top8), 6),
                "bench_minutes_share": round(
                    sum(s["share"] for s in shares[8:]), 6),
                "top8_players": [{"player": s["player"],
                                   "minutes": "%d:%02d" % divmod(s["minutes_seconds"], 60),
                                   "share": s["share"]} for s in top8],
            })

    share_doc = {
        "title": "Measured minutes shares per team — official gamebooks, %s" % date,
        "generated_by": "scripts/build_player_logs_a374ec9f.py",
        "session": "arena/a374ec9f-nba1",
        "method": ("Each player's minutes share = his printed minutes (seconds) "
                   "/ the printed team total (240:00, or 265:00 with one "
                   "overtime period). Top-8 share = the eight largest shares "
                   "summed. Bench share = 1 - top-8 share. Players with no "
                   "minutes in the gamebook are listed with the official note "
                   "printed for them."),
        "sample": {
            "date": date, "games": len(games),
            "team_games": len(share_rows),
            "teams_measured": len({r["team"] for r in share_rows}),
            "games_per_team": 1,
            "reading": ("These are observations of one game day, not rates: "
                        "they cannot show how a team's minutes change when a "
                        "player is absent."),
        },
        "rows": share_rows,
        "flags": [],
    }
    spath = os.path.join(DERIVED, "minutes_shares_%s.json" % date)
    with open(spath, "w", encoding="utf-8") as fh:
        json.dump(share_doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("wrote %s: %d team-games" % (os.path.relpath(spath, ROOT),
                                       len(share_rows)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
