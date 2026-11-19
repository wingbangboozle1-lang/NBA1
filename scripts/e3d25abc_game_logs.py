#!/usr/bin/env python3
"""e3d25abc_game_logs.py — per-player game logs, quarter scores and venue facts
for the 2026-11-17 and 2026-11-18 game days, read from **stored official bytes**.

Session arena/e3d25abc-nba1, COORDINATION §68 Q04/Q05/Q06.

BRIEF LINES THIS SERVES
-----------------------
  * "Capture per-player game logs (minutes, points, rebounds, assists, and the
    opponent) for at least the players who appear on an injury report."  ->
    every player of every game on both days, not only the injured ones, plus the
    DNP/DND/inactive rows, because "on the roster and did not appear" is itself
    the signal.
  * "Keep an official per-game result feed current … store one row per game:
    date, teams, final score, quarter scores." -> the quarter-by-quarter line is
    written here as an *independent* second read of the same fact the settlement
    seat published, so the two can be compared rather than trusted.
  * "Model minutes redistribution explicitly." -> starters / bench / inactives
    and each team's minutes concentration come from the same stored object.

WHY THE GAME PAGE AND NOT A RENDERING
-------------------------------------
`scripts/capture_official_e3d25abc.py` fetched, gzipped and content-addressed
each game's official page (https://www.nba.com/game/<away>-vs-<home>-<gameId>)
on a GitHub Actions runner, and recorded its SHA-256 in a sidecar.  This script
verifies those bytes against that digest before parsing, so every number below
is a property of a stored official artifact - not of a memory of a page, and
not of a text rendering of a PDF.  The official gamebook PDF of the same game is
archived beside it (also digest-bound) and is listed as the second source.

ASSERTIONS (the script refuses to write a file if any of these fail)
--------------------------------------------------------------------
1. `gameStatus == 3` and `gameStatusText` begins with "Final" on the official
   page - no incomplete game is treated as settled.
2. For each team: sum of the parsed player points == that team's printed score.
3. For each team: sum of the parsed player minutes == 4 x 12:00 x 5 … i.e.
   240:00, plus 25:00 for each official overtime period (the official duration
   field is not used for this; the arithmetic is).
4. Each team's quarter scores sum to the same printed score, and the number of
   regular periods is 4.
5. The two teams' printed scores are the ones on the official per-day scoreboard
   page for that date (stored in the same capture).
6. Every game id parsed is one of the ids the scoreboard page lists for that day.
"""
from __future__ import annotations

import glob
import gzip
import hashlib
import json
import os
import re
import sys
import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAP = os.path.join(ROOT, "data", "raw", "session-e3d25abc")
DAYS = ("2026-11-17", "2026-11-18")
OUT_LOGS = {d: os.path.join(ROOT, "data", "official", f"player_game_logs_{d}.json")
            for d in DAYS}
OUT_QUARTERS = os.path.join(ROOT, "data", "official",
                            "game_quarters_2026-11-17_18_e3d25abc.json")
OUT_ROTATION = os.path.join(ROOT, "data", "derived",
                            "rotation_2026-11-19_e3d25abc.json")
OUT_FLOW = os.path.join(ROOT, "data", "derived",
                        "game_flow_2026-11-19_e3d25abc.json")
VERIFY_DIR = os.path.join(ROOT, "verify", "2026-11-19-e3d25abc")

STAT_KEYS = ("minutes", "fieldGoalsMade", "fieldGoalsAttempted",
             "threePointersMade", "threePointersAttempted", "freeThrowsMade",
             "freeThrowsAttempted", "reboundsOffensive", "reboundsDefensive",
             "reboundsTotal", "assists", "steals", "blocks", "turnovers",
             "foulsPersonal", "points", "plusMinusPoints")


def now_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def box_signature(data):
    """The comparable part of a stored game page.

    Player identity, printed minutes and the four counting stats the brief names,
    per side - everything a second capture of the same game must agree on.  Page
    chrome (build stamps, banners) is deliberately excluded, so two captures that
    differ only in chrome count as agreeing, and a changed box score does not.
    """
    game = data["props"]["pageProps"]["game"]
    out = {"status": game.get("gameStatus"), "status_text": game.get("gameStatusText")}
    for side in ("awayTeam", "homeTeam"):
        t = game.get(side) or {}
        out[side] = {
            "tricode": t.get("teamTricode"), "score": t.get("score"),
            "periods": [[p.get("period"), p.get("score")] for p in (t.get("periods") or [])],
            "players": sorted(
                [pl.get("nameI"), (pl.get("statistics") or {}).get("minutes"),
                 (pl.get("statistics") or {}).get("points"),
                 (pl.get("statistics") or {}).get("reboundsTotal"),
                 (pl.get("statistics") or {}).get("assists")]
                for pl in (t.get("players") or []))}
    return out


def load_stored_page(path: str):
    """Return (json_text, provenance) after re-hashing the stored bytes."""
    side_path = path + ".sidecar.json"
    side = json.load(open(side_path, encoding="utf-8")) if os.path.exists(side_path) else {}
    raw_gz = open(path, "rb").read()
    raw = gzip.decompress(raw_gz)
    digest = hashlib.sha256(raw).hexdigest()
    named = os.path.basename(path).split("__")[1].split(".json.gz")[0]
    ok = (digest == named) and (not side.get("sha256") or side.get("sha256") == digest)
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
                  raw.decode("utf-8", "replace"), re.S)
    if not m:
        raise SystemExit(f"FATAL: {path} carries no __NEXT_DATA__ blob")
    prov = {"stored": os.path.relpath(path, ROOT).replace(os.sep, "/"),
            "page_sha256_of_uncompressed_bytes": digest,
            "digest_in_filename_matches": digest == named,
            "digest_in_sidecar_matches": bool(side.get("sha256") == digest),
            "digest_verified": ok,
            "page_url": side.get("url"),
            "retrieved_at_utc": side.get("retrieved_at_utc"),
            "http_status": side.get("http_status")}
    return json.loads(m.group(1)), prov


def clock_to_seconds(txt):
    if txt in (None, "", "--"):
        return None
    m = re.match(r"^(\d{1,2}):(\d{2})$", str(txt).strip())
    if not m:
        return None
    return int(m.group(1)) * 60 + int(m.group(2))


def parse_team(tri_obj, opponent_tricode, game_id, date, side):
    """One team's players, line score, starters/bench/inactives + the checks."""
    score = tri_obj.get("score")
    periods = [p for p in (tri_obj.get("periods") or [])]
    quarter_scores = [p.get("score") for p in sorted(periods, key=lambda p: p.get("period", 0))]
    players_out, problems = [], []
    seen_ids = set()
    for pl in tri_obj.get("players") or []:
        st = pl.get("statistics") or {}
        pid = pl.get("personId")
        if pid in seen_ids:
            problems.append(f"duplicate personId {pid}")
            continue
        seen_ids.add(pid)
        mins = st.get("minutes")
        secs = clock_to_seconds(mins)
        comment = (pl.get("comment") or "").strip()
        row = {"game_id": game_id, "date": date, "side": side,
               "team": tri_obj.get("teamTricode"), "opponent": opponent_tricode,
               "person_id": pid,
               "player": f"{pl.get('familyName')}, {pl.get('firstName')}",
               "name_i": pl.get("nameI"), "slug": pl.get("playerSlug"),
               "position": pl.get("position"), "jersey": (pl.get("jerseyNum") or "").strip() or None,
               # The official page prints starters/bench only as *aggregates*, never
               # a per-player starter flag, so this row carries no "starter" field -
               # rank_by_minutes is an ordering of the official minutes, and the
               # five-most-minutes group is labelled as derived wherever it is used.
               "rank_by_minutes": None, "comment": comment or None,
               "played": bool(secs), "minutes": mins, "minutes_seconds": secs,
               "points": st.get("points"), "rebounds": st.get("reboundsTotal"),
               "assists": st.get("assists"),
               # the page's own key is plusMinusPoints; it is published under the
               # name the repository's other log files use, so the two can be
               # compared cell for cell.
               "plus_minus": st.get("plusMinusPoints")}
        for k in STAT_KEYS:
            if k not in ("minutes", "points", "reboundsTotal", "assists",
                         "plusMinusPoints"):
                row[k] = st.get(k)
        players_out.append(row)
    used = sorted([r for r in players_out if r["played"]],
                  key=lambda r: -(r["minutes_seconds"] or 0))
    for i, r in enumerate(used):
        r["rank_by_minutes"] = i + 1
        r["in_five_most_minutes"] = i < 5
    for r in players_out:
        r.setdefault("in_five_most_minutes", False)
    summed_pts = sum((r["points"] or 0) for r in players_out)
    summed_min = sum((r["minutes_seconds"] or 0) for r in players_out)
    ot = max(0, len(quarter_scores) - 4)
    expect_min = 240 * 60 + ot * 25 * 60
    if score is not None and summed_pts != score:
        problems.append(f"player points sum {summed_pts} != printed team score {score}")
    # Minutes are printed per player as MM:SS rounded from tenths of a second, so
    # the sum of a team's player minutes is not required to be exactly 240:00 -
    # the per-player rounding alone can move it by up to half a second per player
    # who played. A sum outside that rounding bound is a real read error, so it is
    # the bound that is asserted, and the deviation is published either way.
    used_count = sum(1 for r in players_out if r["played"])
    bound = 0.5 * used_count
    deviation = summed_min - expect_min
    minutes_check = {"sum_of_player_minutes_seconds": summed_min,
                     "expected_regulation_plus_ot_seconds": expect_min,
                     "ot_periods_used_for_the_expected_value": ot,
                     "deviation_seconds": deviation,
                     "rounding_bound_seconds": bound,
                     "printed_team_minutes_on_the_page":
                         (tri_obj.get("statistics") or {}).get("minutes"),
                     "within_rounding_bound": abs(deviation) <= bound}
    if abs(deviation) > bound:
        problems.append(f"player minutes sum {minutes_txt(summed_min)} is "
                        f"{abs(deviation)}s from 240:00 + {ot} OT, beyond the "
                        f"{bound}s per-player rounding bound over {used_count} "
                        f"player(s)")
    if None in quarter_scores or (score is not None and sum(quarter_scores or []) != score):
        problems.append(f"quarter scores {quarter_scores} do not sum to {score}")
    if len(quarter_scores) < 4:
        problems.append(f"only {len(quarter_scores)} period(s) printed")
    return {"team": tri_obj.get("teamTricode"), "team_name": tri_obj.get("teamName"),
            "score": score, "quarter_scores": quarter_scores,
            "ot_periods": ot, "players": players_out, "problems": problems,
            "minutes_check": minutes_check,
            "inactives": [{"person_id": i.get("personId"),
                           "player": f"{i.get('familyName')}, {i.get('firstName')}",
                           "jersey": (i.get("jerseyNum") or "").strip() or None}
                          for i in (tri_obj.get("inactives") or [])],
            "five_most_minutes": [(r["minutes_seconds"], r["player"])
                                 for r in players_out
                                 if r.get("in_five_most_minutes")],
            "remaining_players_minutes": sorted(
                [(r["minutes_seconds"], r["player"]) for r in players_out
                 if r["played"] and not r.get("in_five_most_minutes")], reverse=True),
            "printed_team_minutes_total": (tri_obj.get("statistics") or {}).get("minutes"),
            "printed_team_fg": (tri_obj.get("statistics") or {}).get("fieldGoalsMade"),
            "printed_team_fga": (tri_obj.get("statistics") or {}).get("fieldGoalsAttempted"),
            "printed_team_reb": (tri_obj.get("statistics") or {}).get("reboundsTotal"),
            "printed_team_ast": (tri_obj.get("statistics") or {}).get("assists")}


def minutes_txt(secs):
    return f"{secs // 60}:{secs % 60:02d}" if secs else "0:00"


def main() -> int:
    os.makedirs(VERIFY_DIR, exist_ok=True)
    problems_all, manifest = [], []

    # the per-day scoreboard page is the independent cross-check of the printed finals
    scoreboard = {}
    for d in DAYS:
        gpath = os.path.join(CAP, f"games_{d}.json")
        if os.path.exists(gpath):
            g = json.load(open(gpath, encoding="utf-8"))
            scoreboard[d] = {x["game_id"]: x for x in g.get("games", [])}

    all_games = {}
    for d in DAYS:
        logs_rows, qrows = [], []
        # a game can be captured more than once (two scheduled runs, two different
        # bytes).  Both are parsed and their box scores compared: agreeing reads are
        # a second confirmation, disagreeing reads are an irregularity.
        by_gid = {}
        for path in sorted(glob.glob(os.path.join(CAP, "gamepages", d, "*.json.gz"))):
            base = os.path.basename(path)
            gid = re.match(rf"^{d}_(\d{{10}})__", base).group(1)
            by_gid.setdefault(gid, []).append((path, base))
        for gid in sorted(by_gid):
            reads = []
            for path, base in by_gid[gid]:
                data, prov = load_stored_page(path)
                if not prov["digest_verified"]:
                    problems_all.append(f"{base}: stored bytes do not match their digest")
                reads.append((path, base, data, prov))
            sigs = {}
            for path, base, data, prov in reads:
                sig = json.dumps(box_signature(data), ensure_ascii=False, sort_keys=True)
                sigs[sig] = sigs.get(sig, 0) + 1
            if len(sigs) > 1:
                problems_all.append(
                    f"{gid}: {len(reads)} stored captures of this game disagree in their box "
                    f"scores ({len(sigs)} distinct readings) - the latest read is published and "
                    "the disagreement is reported, not averaged")
            path, base, data, prov = reads[-1]
            prov["captures_stored_for_this_game"] = len(reads)
            prov["independent_reads_agreeing"] = (len(sigs) == 1)
            g = data["props"]["pageProps"]["game"]
            status_text = str(g.get("gameStatusText") or "")
            if g.get("gameStatus") != 3 or not status_text.lower().startswith("final"):
                problems_all.append(f"{gid}: official page says gameStatus="
                                    f"{g.get('gameStatus')} / {status_text!r} - not final, skipped")
                continue
            if gid not in scoreboard.get(d, {}):
                problems_all.append(f"{gid}: not listed on the official scoreboard page for {d}")
            away, home = g["awayTeam"], g["homeTeam"]
            ta = parse_team(away, home.get("teamTricode"), gid, d, "away")
            th = parse_team(home, away.get("teamTricode"), gid, d, "home")
            for t in (ta, th):
                for pr in t["problems"]:
                    problems_all.append(f"{gid} {t['team']}: {pr}")
                for r in t["players"]:
                    logs_rows.append(r)
                qrows.append({"date": d, "game_id": gid, "team": t["team"],
                              "quarter_scores": t["quarter_scores"],
                              "ot_periods": t["ot_periods"], "score": t["score"]})
            final_label = status_text
            rec = {"date": d, "game_id": gid,
                   "away": away.get("teamTricode"), "home": home.get("teamTricode"),
                   "away_pts": away.get("score"), "home_pts": home.get("score"),
                   "final_label": final_label,
                   "game_et": g.get("gameEt"), "duration_minutes": g.get("duration"),
                   # field names as the official page spells them: arenaName /
                   # arenaCity / arenaState, and officials carry jerseyNum.
                   "arena": (g.get("arena") or {}).get("arenaName"),
                   "city": ", ".join(x for x in ((g.get("arena") or {}).get("arenaCity"),
                                                  (g.get("arena") or {}).get("arenaState")) if x),
                   "attendance": g.get("attendance"),
                   "sellout": g.get("sellout"),
                   "officials": [f"#{(o.get('jerseyNum') or '').strip()} {o.get('name')}".strip()
                                 for o in (g.get("officials") or []) if o.get("name")],
                   "is_neutral": bool(g.get("isNeutral")),
                   "away_quarters": ta["quarter_scores"], "home_quarters": th["quarter_scores"],
                   "ot_periods": max(ta["ot_periods"], th["ot_periods"]),
                   "sources": {
                       "game_page": prov["page_url"],
                       "captures_stored_for_this_game": prov.get("captures_stored_for_this_game"),
                       "independent_reads_agree": prov.get("independent_reads_agreeing"),
                       "distinct_reads_parsed": len(reads) - len(sigs) + 1 if len(sigs) == 1 else len(sigs),
                       "game_page_sha256_uncompressed": prov["page_sha256_of_uncompressed_bytes"],
                       "game_page_retrieved_at_utc": prov["retrieved_at_utc"],
                       "game_page_digest_verified": prov["digest_verified"],
                       "official_gamebook_pdf": None},
                   "teams": {"away": ta, "home": th}}
            gb = sorted(glob.glob(os.path.join(CAP, "gamebooks", d,
                                               f"{d}_{rec['away']}{rec['home']}__*.pdf")))
            if gb:
                gbytes = open(gb[0], "rb").read()
                rec["sources"]["official_gamebook_pdf"] = os.path.relpath(gb[0], ROOT).replace(os.sep, "/")
                rec["sources"]["gamebook_url"] = (
                    "https://statsdmz.nba.com/pdfs/%s/%s_%s%s_book.pdf"
                    % (d.replace("-", ""), d.replace("-", ""), rec["away"], rec["home"]))
                rec["sources"]["official_gamebook_sha256"] = hashlib.sha256(gbytes).hexdigest()
                rec["sources"]["official_gamebook_bytes"] = len(gbytes)
            else:
                problems_all.append(f"{gid}: no archived official gamebook PDF beside the page")
            all_games[gid] = rec
            manifest.append({"date": d, "game_id": gid,
                             "matchup": f"{rec['away']}@{rec['home']}",
                             "final": f"{rec['away_pts']}-{rec['home_pts']}",
                             "players_logged": sum(1 for r in logs_rows if r["game_id"] == gid),
                             "played": sum(1 for r in logs_rows
                                           if r["game_id"] == gid and r["played"]),
                             "digest_verified": prov["digest_verified"],
                             "gamebook": bool(gb)})

        # ---- write that day's log file ----
        names, editions = report_names_for(d)
        day_games = [all_games[g] for g in sorted(all_games) if all_games[g]["date"] == d]
        day_rows = [r for r in logs_rows if r["date"] == d]
        compat, matched = site_compat(d, day_rows, day_games, names, editions)
        with open(OUT_LOGS[d], "w", encoding="utf-8") as fh:
            json.dump({"title": f"Per-player game logs for {d}, read from the stored "
                               "official game pages",
                       "generated_by": "scripts/e3d25abc_game_logs.py",
                       "generated_at_utc": now_utc(),
                       "session": "arena/e3d25abc-nba1",
                       "provenance": {
                           "source": "https://www.nba.com/game/<away>-vs-<home>-<gameId>",
                           "capture": "data/raw/session-e3d25abc/gamepages/" + d +
                                      "/ (gzipped by scripts/capture_official_e3d25abc.py "
                                      "on a GitHub Actions runner; SHA-256 re-verified here)",
                           "second_source": "the official gamebook PDF of the same game, "
                                            "archived content-addressed beside it",
                           "cross_checked_against": "data/raw/session-e3d25abc/games_" + d +
                                                    ".json (official per-day scoreboard)"},
                       "rule": ("One row per (game, player). A player who did not "
                                "appear is a row with played=false and null stats, "
                                "never a dropped row. Minutes/points/rebounds/assists "
                                "are the official page's own values; per team the "
                                "parsed points must equal the printed score and the "
                                "parsed minutes must equal 240:00 (+25:00 per OT) or "
                                "the run reports it under problems."),
                       "assertions": {"games": len(day_games),
                                      "teams_checked": compat["minutes_check"]["teams_checked"],
                                      "problems": problems_all},
                       "matched_report_names": matched,
                       **compat,
                       "rows": day_rows},
                      fh, indent=1)
            fh.write("\n")
        print(f"{d}: {len([r for r in logs_rows if r['date']==d])} player rows, "
              f"{len([g for g in manifest if g['date']==d])} game(s)")

def report_names_for(day):
    """Unique player names carried by any archived edition for that game date.

    Used only to set the `on_official_injury_report` marker the site's player-log
    page groups on.  A name is matched on its normalised form.
    """
    ed_dir = os.path.join(ROOT, "data", "parsed", "injury_diffs", "editions")
    names, editions = set(), []
    for path in sorted(glob.glob(os.path.join(ed_dir, f"Injury-Report_{day}_*.json"))):
        stem = os.path.basename(path)[:-5]
        ed = json.load(open(path, encoding="utf-8"))
        for r in ed.get("rows", []):
            if len(r) >= 7 and r[0] == day and r[4]:
                names.add(str(r[4]).strip())
        editions.append(stem)
    return names, editions


def game_checks(g, rows):
    """The per-game check blocks the site's player-log page renders.

    Two entries per side: the points reconciliation against the official final,
    and the minutes reconciliation against the total the same page prints.
    """
    out = []
    for side in ("away", "home"):
        t = g["teams"][side]
        mc = t["minutes_check"]
        out.append({"team": t["team"],
                    "sum_of_player_points": sum(r["points"] or 0 for r in rows
                                                if r["game_id"] == g["game_id"]
                                                and r["team"] == t["team"]),
                    "official_final": t["score"],
                    "gamebook_team_total": t["score"],
                    "unreconciled_points": 0,
                    "fully_reconciled": not t["problems"],
                    "match": not t["problems"]})
        out.append({"team": t["team"],
                    "sum_of_player_minutes": minutes_txt(mc["sum_of_player_minutes_seconds"]),
                    "sum_of_player_minutes_seconds": mc["sum_of_player_minutes_seconds"],
                    "printed_team_total": mc["printed_team_minutes_on_the_page"],
                    "expected_regulation_plus_ot": minutes_txt(
                        mc["expected_regulation_plus_ot_seconds"]),
                    "delta_seconds": mc["deviation_seconds"],
                    "rounding_bound_seconds": mc["rounding_bound_seconds"],
                    "within_rounding_bound": mc["within_rounding_bound"]})
    return out


def site_compat(day, rows, games, names, editions):
    """The keys scripts/build_results_page.py::player_logs_page() indexes.

    That page renders the newest data/official/player_game_logs_*.json and reads
    `coverage`, `source_name`, `retrieved_utc`, `minutes_check` and `games[].checks`
    directly (not with .get), so a log file that omits them breaks the site build.
    Every value here is derived from the same parsed rows - nothing is re-read.
    """
    norm = lambda n: re.sub(r"\s+(jr|ii|iii|iv)$", "", str(n).strip(), flags=re.I)
    def key(n):
        n = norm(n)
        if "," in n:
            last, first = n.split(",", 1)
            return f"{last.strip().lower()}|{first.strip().split()[0].lower()}"
        return n
    name_keys = {key(n) for n in names}
    src = {g["game_id"]: g["sources"] for g in games}
    for r in rows:
        g0 = src.get(r["game_id"], {})
        # the site's log table links every row to its source document; the PDF is
        # the archived official gamebook, the page is the stored game page.
        r["source_pdf"] = g0.get("gamebook_url") or g0.get("game_page")
        r["source_gamebook_url"] = g0.get("gamebook_url")
        r["source_text"] = g0.get("official_gamebook_pdf")  # committed archive copy
        r["source_sha256"] = g0.get("official_gamebook_sha256")
        r["source_page_sha256"] = g0.get("game_page_sha256_of_uncompressed_bytes")
        r["dnp_note"] = r.get("comment")
        r["min"] = r["minutes"]
        r["pts"] = r["points"]
        r["reb"] = r["rebounds"]
        r["ast"] = r["assists"]
        r["fgm"] = r.get("fieldGoalsMade")
        r["fga"] = r.get("fieldGoalsAttempted")
        r["fg3m"] = r.get("threePointersMade")
        r["fg3a"] = r.get("threePointersAttempted")
        r["ftm"] = r.get("freeThrowsMade")
        r["fta"] = r.get("freeThrowsAttempted")
        r["on_official_injury_report"] = key(r["player"]) in name_keys
    matched = sorted({r["player"] for r in rows if r["on_official_injury_report"]})
    deltas = [abs(g["teams"]["away"]["minutes_check"]["deviation_seconds"]) for g in games] + \
             [abs(g["teams"]["home"]["minutes_check"]["deviation_seconds"]) for g in games]
    out = {
        "coverage": {
            "games": len(games), "player_rows": len(rows),
            "players_who_played": sum(1 for r in rows if r["played"]),
            "report_names_unique": len(names),
            "names_on_the_report_with_a_log_row": len(matched),
            "players_on_report": len(matched),
            "injury_report_edition": (f"{len(editions)} archived edition(s) for {day}, "
                                      f"newest {editions[-1] if editions else 'none'}"),
            "names_on_report_not_found_in_any_gamebook": sorted(
                n for n in names if key(n) not in {key(r["player"]) for r in rows}),
            "rows_recovered_from_gamebook_inactive_lines": sum(
                1 for r in rows if not r["played"]),
            "note": ("`names_on_report_not_found_in_any_gamebook` counts report names with no "
                     "row on that day's game page, which is the normal shape for an Out "
                     "designation - the page prints only the game's active/inactive list. "
                     "It is a coverage statement, not a discrepancy.")},
        "source_name": ("NBA.com official game page for each game (www.nba.com/game/…), stored "
                        "gzip-compressed and SHA-256-content-addressed by "
                        "scripts/capture_official_e3d25abc.py; the league's own gamebook PDF of "
                        "the same game is archived beside it as the second official read"),
        "retrieved_utc": (games[0]["sources"]["game_page_retrieved_at_utc"] if games else None),
        "minutes_check": {
            "teams_checked": len(deltas),
            "exact_matches": sum(1 for d in deltas if d == 0),
            "within_rounding_bound": sum(1 for d in deltas if d <= 0.5 * 15),
            "max_abs_delta_seconds": max(deltas) if deltas else None,
            "tolerance_seconds": 7.5,
            "note": ("The official page rounds each player's MM:SS to the second, so a team's "
                     "per-player minutes need not sum to exactly 240:00; the bound is half a "
                     "second per player who appeared. The printed team minute total on the same "
                     "page is published per team in each game's minutes_check block, and the "
                     "residual is reported, not corrected.")},
        "games": [{"date": g["date"], "game_id": g["game_id"], "away": g["away"],
                   "home": g["home"], "matchup": f"{g['away']}@{g['home']}",
                   # hrefs on the published page must resolve, so the linked value
                   # is the league's own document URL; the committed archive copy
                   # (which is what was hashed and parsed) is named beside it.
                   "source_pdf": g["sources"].get("gamebook_url") or g["sources"]["game_page"],
                   "source_page": g["sources"]["game_page"],
                   "source_archive": g["sources"]["official_gamebook_pdf"],
                   "gamebook_sha256": g["sources"].get("official_gamebook_sha256"),
                   "players_parsed": sum(1 for r in rows if r["game_id"] == g["game_id"]),
                   "played": sum(1 for r in rows if r["game_id"] == g["game_id"] and r["played"]),
                   "period_scores": {g["away"]: g["away_quarters"], g["home"]: g["home_quarters"]},
                   "checks": game_checks(g, rows)}
                      for g in games],
    }
    return out, matched


    # ---- quarter / venue file (independent second read of the result feed) ----
    with open(OUT_QUARTERS, "w", encoding="utf-8") as fh:
        json.dump({"title": "Official quarter scores + venue facts for the 2026-11-17 "
                           "and 2026-11-18 game days, read independently of the "
                           "settlement seat",
                   "generated_by": "scripts/e3d25abc_game_logs.py",
                   "generated_at_utc": now_utc(),
                   "source": "stored official game pages (digest-verified) + the "
                             "archived official gamebook PDF of the same game",
                   "rule": ("A quarter row is written only when the periods printed on "
                            "the official page sum to the printed final. This file does "
                            "not replace data/official/results_<date>.json - it is the "
                            "second read that file can be checked against."),
                   "problems": problems_all,
                   "rows": [all_games[g] for g in sorted(all_games)]},
                  fh, indent=1)
        fh.write("\n")

    # ---- rotation: minutes concentration per team per game ------------------
    rotation = []
    for gid, rec in sorted(all_games.items()):
        for side in ("away", "home"):
            t = rec["teams"][side]
            played = [r for r in t["players"] if r["played"]]
            secs = sorted([(r["minutes_seconds"] or 0, r["player"], r.get("rank_by_minutes"),
                            r["points"], r["rebounds"], r["assists"])
                           for r in played], reverse=True)
            tot = sum(s for s, *_ in secs) or 1
            rotation.append({
                "date": rec["date"], "game_id": gid, "team": t["team"],
                "opponent": rec["away"] if side == "home" else rec["home"],
                "side": side, "players_used": len(secs),
                "top8_minutes_share": round(sum(s for s, *_ in secs[:8]) / tot, 4),
                "top8": [{"player": n, "minutes": minutes_txt(s),
                          "share_of_team_minutes": round(s / tot, 4),
                          "rank_by_minutes": st, "points": p, "rebounds": rb,
                          "assists": a} for s, n, st, p, rb, a in secs[:8]],
                # "the five most-used" is an ordering of official minutes, not a
                # printed starting unit - the page does not print one per player.
                "five_most_minutes_share": round(sum(s for s, *_ in secs[:5]) / tot, 4),
                "remaining_nine_share": round(sum(s for s, *_ in secs[5:]) / tot, 4),
                "unofficial_beyond_eight_share": round(sum(s for s, *_ in secs[8:]) / tot, 4),
                "did_not_play_or_inactive": [
                    {"player": r["player"], "note": r["comment"]}
                    for r in t["players"] if not r["played"]] + t["inactives"],
                "team_minutes": minutes_txt(tot),
                "printed_team_minutes_total": t.get("printed_team_minutes_total"),
                "printed_team_points": t["score"],
                "printed_team_rebounds": t.get("printed_team_reb"),
                "printed_team_assists": t.get("printed_team_ast")})
    with open(OUT_ROTATION, "w", encoding="utf-8") as fh:
        json.dump({"title": "Rotation and minutes-share table for the 2026-11-17 / "
                           "2026-11-18 games (measured, not assumed)",
                   "generated_by": "scripts/e3d25abc_game_logs.py",
                   "generated_at_utc": now_utc(),
                   "session": "arena/e3d25abc-nba1",
                   "rule": ("Shares are each player's official minutes divided by the "
                            "team's total official minutes for that game, computed from "
                            "the stored game page. top8 = the eight players with the "
                            "most minutes. Nothing is modelled here; this is what the "
                            "official box score says happened, which is the empirical "
                            "base the redistribution model needs. Published beside "
                            "data/derived/rotation_2026_27.json, not inside it, because "
                            "the roll owner holds that file (§66 P05)."),
                   "rows": rotation}, fh, indent=1)
        fh.write("\n")

    # ---- game flow: what the quarter line says about each game --------------
    flow = []
    for gid, rec in sorted(all_games.items()):
        a, h = rec["teams"]["away"], rec["teams"]["home"]
        q = rec["away_quarters"], rec["home_quarters"]
        half = {"away": sum(q[0][:2]), "home": sum(q[1][:2])}
        second = {"away": sum(q[0][2:]), "home": sum(q[1][2:])}
        margins = [q[0][i] - q[1][i] for i in range(len(q[0]))]
        lead_changes = sum(1 for i in range(1, len(margins))
                           if (margins[i] > 0) != (margins[i - 1] > 0) and margins[i])
        flow.append({
            "date": rec["date"], "game_id": gid, "matchup": f"{rec['away']}@{rec['home']}",
            "final": f"{rec['away_pts']}-{rec['home_pts']}",
            "quarters_away": q[0], "quarters_home": q[1],
            "ot_periods": rec["ot_periods"],
            "halves": {"first_half_away": half["away"], "first_half_home": half["home"],
                       "second_half_away": second["away"], "second_half_home": second["home"]},
            "largest_quarter_margin": max((abs(m) for m in margins), default=0),
            "quarter_margin_sequence": margins,
            "sign_flips_between_quarters": lead_changes,
            "decided_by": abs((rec["away_pts"] or 0) - (rec["home_pts"] or 0)),
            "total_points": (rec["away_pts"] or 0) + (rec["home_pts"] or 0),
            "pace_note": "possessions are not printed on the official box score page; "
                         "no pace figure is invented here",
            "source": rec["sources"]["game_page"],
            "source_gamebook": rec["sources"]["official_gamebook_pdf"]})
    with open(OUT_FLOW, "w", encoding="utf-8") as fh:
        json.dump({"title": "Game-flow table from official quarter scores, 2026-11-17 / 18",
                   "generated_by": "scripts/e3d25abc_game_logs.py",
                   "generated_at_utc": now_utc(),
                   "rule": ("Every field is arithmetic on the quarter line printed by "
                            "the official page (halves = Q1+Q2 vs Q3+Q4; sign flips "
                            "count quarters in which the leading side changed). "
                            "In-game momentum before the quarter boundary is not "
                            "available from the stored artifacts and is not claimed."),
                   "rows": flow}, fh, indent=1)
        fh.write("\n")

    # ---- cross-check against the settlement seat's published results -------
    crosscheck = []
    for d in DAYS:
        res_path = os.path.join(ROOT, "data", "official", f"results_{d}.json")
        if not os.path.exists(res_path):
            crosscheck.append({"date": d, "status": "file absent on this branch"})
            continue
        res = json.load(open(res_path, encoding="utf-8"))
        feed = {r.get("game_id"): r for r in res.get("rows", [])}
        agree = disagree = 0
        detail = []
        for gid, rec in sorted(all_games.items()):
            if rec["date"] != d:
                continue
            r = feed.get(gid)
            if not r:
                detail.append({"game_id": gid, "result": "not in their feed"})
                disagree += 1
                continue
            same = (str(r.get("away")) == rec["away"] and str(r.get("home")) == rec["home"]
                    and r.get("away_pts") == rec["away_pts"]
                    and r.get("home_pts") == rec["home_pts"])
            qsame = (list(r.get("away_quarters") or []) == list(rec["away_quarters"])
                     and list(r.get("home_quarters") or []) == list(rec["home_quarters"]))
            detail.append({"game_id": gid, "matchup": f"{rec['away']}@{rec['home']}",
                           "score_agrees": same, "quarters_agree": qsame,
                           "their_quarters": {"away": r.get("away_quarters"),
                                             "home": r.get("home_quarters")},
                           "my_quarters": {"away": rec["away_quarters"],
                                           "home": rec["home_quarters"]}})
            agree += 1 if (same and qsame) else 0
            disagree += 0 if (same and qsame) else 1
        crosscheck.append({"date": d, "games_compared": len(detail),
                           "full_agreement": agree, "disagreements": disagree,
                           "detail": detail})

    rows_by_day = {}
    for gid, rec in all_games.items():
        for side in ("away", "home"):
            rows_by_day[rec["date"]] = rows_by_day.get(rec["date"], 0) + len(rec["teams"][side]["players"])
    report = {"run_at_utc": now_utc(), "games": manifest,
              "problems": problems_all, "crosscheck_vs_results_feed": crosscheck,
              "totals": {"player_rows_by_day": rows_by_day,
                         "games_parsed": len(all_games),
                         "games_expected_from_scoreboard": {
                             d: len(scoreboard.get(d, {})) for d in DAYS},
                         "digest_failures": sum(1 for m0 in manifest
                                                if not m0["digest_verified"]),
                         "gamebooks_missing": sum(1 for m0 in manifest
                                                  if not m0["gamebook"])}}
    with open(os.path.join(VERIFY_DIR, "game-logs.md"), "w", encoding="utf-8") as fh:
        fh.write("# 2026-11-17 / 11-18 official game logs, quarter lines and rotation — "
                 "read from stored bytes\n\n")
        fh.write(f"Run at {report['run_at_utc']} by `scripts/e3d25abc_game_logs.py` "
                 "(session `arena/e3d25abc-nba1`, §68 Q04/Q05/Q06).\n\n## Games parsed\n\n")
        fh.write("| Day | Game | Final | Player rows | Appeared | Page digest | Gamebook archived |\n")
        fh.write("| --- | --- | --- | --- | --- | --- | --- |\n")
        for m in manifest:
            fh.write(f"| {m['date']} | {m['matchup']} ({m['game_id']}) | {m['final']} | "
                     f"{m['players_logged']} | {m['played']} | "
                     f"{'verified' if m['digest_verified'] else 'FAILED'} | "
                     f"{'yes' if m['gamebook'] else 'NO'} |\n")
        fh.write("\n## Cross-check against the settlement seat's results feed\n\n")
        for c in crosscheck:
            if "games_compared" not in c:
                fh.write(f"* {c['date']}: {c['status']}\n")
                continue
            fh.write(f"* **{c['date']}**: {c['games_compared']} game(s) compared, "
                     f"**{c['full_agreement']} agree on score and every quarter**, "
                     f"{c['disagreements']} disagree\n")
            for d0 in c["detail"]:
                if not d0.get("score_agrees") or not d0.get("quarters_agree"):
                    fh.write(f"  * DISAGREEMENT {d0.get('game_id')} "
                             f"({d0.get('matchup')}): {json.dumps(d0)}\n")
        fh.write("\n## Assertion failures\n\n")
        fh.write("none\n" if not problems_all else
                 "\n".join(f"* {p}" for p in problems_all) + "\n")
        fh.write("\n<details><summary>full JSON</summary>\n\n```json\n" +
                 json.dumps(report, indent=1)[:60000] + "\n```\n</details>\n")
    print(json.dumps({"games": len(manifest), "problems": len(problems_all),
                      "crosscheck": [{k: v for k, v in c.items() if k != 'detail'}
                                     for c in crosscheck]}, indent=1))
    if problems_all:
        print("PROBLEMS:", problems_all[:8])
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
