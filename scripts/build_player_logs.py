#!/usr/bin/env python3
"""build_player_logs.py — R21: per-player game logs for the players on stored official
injury reports.

Brief requirement (R21): "Capture per-player game logs (minutes, points, rebounds,
assists, and the opponent) for at least the players who appear on an injury report."

Design rules followed here, matching the repository's verification discipline:

  * Every published value is read verbatim from the archived official box-score
    pages (`data/raw/html/2026-11-15-801ba27f/boxscore__*.html.gz`) — server-rendered
    official nba.com pages captured with URL, retrieval timestamp, HTTP status and
    SHA-256 (see `_season_manifest.json`). The same parser that re-cut the model
    inputs from those pages (`scripts/model_801ba27f.py`) is reused here.
  * One row per player-game: date, player, team, opponent, minutes, points,
    rebounds, assists — each row linking to the official box-score page it came
    from. Nothing is inferred: a player with no row in any official box score is
    published with blank cells and an explicit flag, never a guess.
  * Player-name matching across surfaces is exact after the repository's published
    normalization (Last/First reorder, diacritics stripped, punctuation removed,
    casefolded — same rule as `engine/model_v2.py::norm_name`). No fuzzy matching:
    an official misspelling stays unmatched on purpose.
  * A player is "on an injury report" if some stored official injury-report
    edition names them. The editions used are listed in the output metadata with
    their source PDFs.

Outputs:
  data/derived/player_game_logs_2026_27.json   the machine-readable logs + coverage
  site/pages/player-logs.html                  (via build(bd)) the browsable page

Called from scripts/build_dashboard.py so a single rebuild regenerates the page;
run standalone to refresh just the data file and print the coverage summary.
"""
import glob
import json
import os
import re
import sys
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)

OUT_JSON = os.path.join(ROOT, "data", "derived", "player_game_logs_2026_27.json")

BOX_SRC = ("https://www.nba.com/game/<away>-vs-<home>-<game_id>/box-score "
           "(archived verbatim: data/raw/html/2026-11-15-801ba27f/boxscore__*.html.gz, "
           "retrieval-stamped + SHA-256 in _season_manifest.json)")
INJ_INDEX = "https://official.nba.com/nba-injury-report-2026-27-season/"


def norm_name(s):
    """Canonical player name — same rule as engine/model_v2.py::norm_name (copied
    verbatim so this script does not import the model; 'Last, First' is reordered,
    diacritics and punctuation stripped, casefolded. Official PDF misspellings
    remain unmatched on purpose — nothing is fuzzy-fitted)."""
    if not s:
        return ""
    s0 = s
    if "," in s0:
        last, first = s0.split(",", 1)
        s0 = first.strip() + " " + last.strip()
    s0 = unicodedata.normalize("NFKD", s0)
    s0 = "".join(c for c in s0 if not unicodedata.combining(c))
    s0 = s0.replace(".", "").replace("'", "")
    return re.sub(r"\s+", " ", s0).strip().lower()


def display_name(s):
    """'Last, First' -> 'First Last'; 'First Last' unchanged. Display only —
    matching always uses norm_name()."""
    if not s:
        return ""
    if "," in s:
        last, first = s.split(",", 1)
        return (first.strip() + " " + last.strip()).strip()
    return s.strip()


# ------------------------------------------------------------- injury editions

def _load_injury_rows():
    """Every player row in every stored official injury-report edition.

    Returns (appearances, editions_used) where appearances is
    norm_name -> list of {edition, label, retrieved_utc, status, team, matchup,
    source_url} and editions_used lists the edition files with their source PDFs.
    """
    appearances = {}
    editions_used = []
    seen_rows = set()

    def add_rows(rows, edition_id, label, retrieved, source_url, tricode_of=None):
        n = 0
        for r in rows:
            if isinstance(r, dict):
                player = r.get("player")
                status = r.get("status")
                team = (r.get("tricode") or r.get("team_printed")
                        or r.get("team_effective") or r.get("team"))
                matchup = r.get("matchup")
            elif isinstance(r, (list, tuple)) and len(r) >= 6:
                player, status, team, matchup = r[4], r[5], r[3], r[2]
            else:
                continue
            if not player or not status or str(status).upper() == "NOT YET SUBMITTED":
                continue
            key = norm_name(player)
            if not key:
                continue
            dedupe = (key, edition_id)
            if dedupe in seen_rows:
                continue
            seen_rows.add(dedupe)
            appearances.setdefault(key, []).append({
                "edition": edition_id,
                "label": label,
                "retrieved_utc": retrieved,
                "status": status,
                "team": team,
                "matchup": matchup,
                "source_url": source_url,
                "printed_name": display_name(player),
            })
            n += 1
        return n

    # 1) data/injury_reports/editions_2026-11-15.json — 75 editions of 2026-11-15
    p = os.path.join(ROOT, "data", "injury_reports", "editions_2026-11-15.json")
    if os.path.exists(p):
        doc = json.load(open(p))
        for e in doc.get("editions", []):
            add_rows(e.get("rows", []), e.get("edition", "?"),
                     e.get("revision_label"), e.get("retrieved_utc"),
                     e.get("source_url"))
        editions_used.append({
            "file": "data/injury_reports/editions_2026-11-15.json",
            "n_editions": len(doc.get("editions", [])),
            "source_index": doc.get("source_index") or INJ_INDEX,
        })

    # 2) data/parsed/injury_diffs/editions/*.json — PDF-extracted editions (rows
    #    are arrays: [game_date, time, matchup, team, player, status, reason])
    for p in sorted(glob.glob(os.path.join(ROOT, "data", "parsed", "injury_diffs",
                                           "editions", "*.json"))):
        doc = json.load(open(p))
        add_rows(doc.get("rows", []), doc.get("edition", os.path.basename(p)),
                 doc.get("label"), doc.get("retrieved_at_utc"),
                 doc.get("source_url"))
        editions_used.append({
            "file": os.path.relpath(p, ROOT),
            "source_url": doc.get("source_url"),
            "sha256": doc.get("sha256"),
        })

    # 3) transcribed editions in data/official/injury_*.json and
    #    data/injury_reports/*/rows.json
    for p in sorted(glob.glob(os.path.join(ROOT, "data", "official", "injury_*.json"))):
        if os.path.basename(p).startswith("injury_diff"):
            continue
        try:
            doc = json.load(open(p))
        except ValueError:
            continue
        if not isinstance(doc, dict) or "rows" not in doc:
            continue
        add_rows(doc.get("rows", []), doc.get("edition", os.path.basename(p)),
                 doc.get("revision_time_et"), doc.get("retrieved_utc"),
                 doc.get("source_url"))
        editions_used.append({
            "file": os.path.relpath(p, ROOT),
            "source_url": doc.get("source_url"),
        })
    for p in sorted(glob.glob(os.path.join(ROOT, "data", "injury_reports", "*",
                                           "rows.json"))):
        doc = json.load(open(p))
        rows = doc.get("rows", doc if isinstance(doc, list) else [])
        ed_dir = os.path.basename(os.path.dirname(p))
        src = None
        ed_p = os.path.join(os.path.dirname(p), "edition.json")
        if os.path.exists(ed_p):
            ed = json.load(open(ed_p))
            src = ed.get("source_url")
        add_rows(rows, ed_dir, ed_dir, None, src)
        editions_used.append({"file": os.path.relpath(p, ROOT), "source_url": src})

    return appearances, editions_used


# ------------------------------------------------------------- box-score logs

def _load_player_games():
    """One row per player-game from the archived official box scores of Final
    games only. A live or unplayed game carries no official final stat line, so
    it is never published as a log row. Also returns the set of every normalized
    player name that appears in ANY captured box score (Final or not), so a
    report player with no Final-game row can be classified honestly: listed in
    a box score but without a Final row yet vs no exact name in any box score.
    """
    import model_801ba27f as model

    games = model.load_games()
    rows = []
    corpus_names = set()
    n_final = 0
    for g in games:
        final = (g.get("game_status") == 3 or
                 str(g.get("game_status_text", "")).strip().lower() == "final")
        for side in (g["home"], g["away"]):
            for pl in side.get("players", []):
                name = pl.get("name")
                if not name:
                    continue
                corpus_names.add(norm_name(name))
                if not final:
                    continue
        if not final:
            continue
        n_final += 1
        home, away = g["home"], g["away"]
        for side, opp in ((home, away), (away, home)):
            for pl in side.get("players", []):
                name = pl.get("name")
                if not name:
                    continue
                rows.append({
                    "norm": norm_name(name),
                    "player": name,
                    "team": side.get("tricode"),
                    "opponent": opp.get("tricode"),
                    "date": g["date"],
                    "game_id": g.get("game_id"),
                    "minutes": pl.get("minutes"),
                    "points": pl.get("points"),
                    "rebounds": pl.get("rebounds"),
                    "assists": pl.get("assists"),
                    "box_score_url": g.get("source_url"),
                    "game_status_text": g.get("game_status_text"),
                })
    return rows, len(games), n_final, corpus_names


# ----------------------------------------------------------------- assembly

def build_data():
    appearances, editions_used = _load_injury_rows()
    log_rows, n_games, n_final, corpus_names = _load_player_games()

    by_norm = {}
    for r in log_rows:
        by_norm.setdefault(r["norm"], []).append(r)

    players = []
    n_with, n_no_final_row, n_no_exact_name = 0, 0, 0
    total_rows = 0
    for key in sorted(appearances):
        apps = sorted(appearances[key], key=lambda a: (a["retrieved_utc"] or "",
                                                       a["edition"]))
        games = sorted(by_norm.get(key, []), key=lambda r: (r["date"], r["game_id"] or ""))
        printed = apps[-1]["printed_name"]
        latest = apps[-1]
        if not games:
            if key in corpus_names:
                # The exact name IS in the official box-score corpus (at least
                # in a game that was not Final when captured) - no Final-game row
                # exists yet, so the R21 fields stay blank for now.
                bucket = "listed_in_box_scores_but_no_final_game_row_at_capture"
                n_no_final_row += 1
            else:
                # No player with this exact name in ANY captured official box
                # score: either the player has not appeared in a game this
                # season, or the report prints a name spelling that matches no
                # box-score name (e.g. the official PDF prints 'Embid' for
                # 'Embiid'). We do not guess which, and no fuzzy matching is
                # applied - published blank and flagged.
                bucket = "no_exact_name_in_any_official_box_score"
                n_no_exact_name += 1
        else:
            n_with += 1
            bucket = "logged"
            total_rows += len(games)
        players.append({
            "player": printed,
            "norm_name": key,
            "latest_status": latest["status"],
            "latest_edition": latest["edition"],
            "latest_edition_label": latest["label"],
            "latest_source_url": latest["source_url"],
            "teams_on_reports": sorted({a["team"] for a in apps if a.get("team")}),
            "appearances": apps,
            "games": games,
            "coverage": bucket,
        })

    doc = {
        "title": "Per-player game logs for players on stored official injury reports (R21)",
        "session": "arena/f03745ef-nba1",
        "rule": ("One row per player-game, read verbatim from the archived official "
                 "box-score pages of Final games. Fields: minutes, points, rebounds, "
                 "assists and the opponent, plus the team and date. A player or game "
                 "without an official box-score row is left blank and flagged — never "
                 "inferred. Name matching is exact after the published normalization "
                 "(no fuzzy matching)."),
        "box_score_source": BOX_SRC,
        "injury_index": INJ_INDEX,
        "injury_editions_used": editions_used,
        "summary": {
            "injury_report_players": len(players),
            "players_with_game_rows": n_with,
            "players_without_game_rows": n_no_final_row + n_no_exact_name,
            "players_listed_but_no_final_row": n_no_final_row,
            "players_no_exact_name_in_box_scores": n_no_exact_name,
            "player_game_rows_published": total_rows,
            "box_score_captures_games": n_games,
            "box_score_games_final": n_final,
        },
        "players": players,
    }
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    return doc


# ------------------------------------------------------------------- rendering

def build(bd):
    """Return {filename: html} for the shared dashboard build."""
    doc = build_data()
    s = doc["summary"]
    esc, elink, NA = bd.esc, bd.elink, bd.NA
    banner, table, h2 = bd.banner, bd.table, bd.h2

    def cell(v):
        if v is None or v == "":
            return NA
        return esc(v)

    body = []
    body.append(banner(
        "info", "What this page is (R21)",
        "<p>Per-player game logs for <b>%d</b> players who appear on a stored official "
        "injury-report edition: minutes, points, rebounds and assists with the opponent, "
        "one row per player-game, every row read verbatim from the archived official "
        "box-score page it links to (<b>%d</b> Final games parsed, <b>%d</b> player-game "
        "rows published).</p>"
        "<p><b>Blank cells are meaningful.</b> %d report players have no row in a Final "
        "game's official box score: %d are listed in a box score but had no Final-game "
        "row at capture time, and %d have no exact name in any captured official box "
        "score (either they have not appeared in a game this season, or the report "
        "prints a name spelling that matches no box-score name — e.g. the official PDF "
        "prints &lsquo;Embid&rsquo; where the box score prints &lsquo;Embiid&rsquo;; "
        "we do not guess which). They are listed with blank cells and a flag, never "
        "filled in by guesswork. Matching is exact after the published name "
        "normalization; nothing is fuzzy-fitted.</p>"
        % (s["injury_report_players"], s["box_score_games_final"],
           s["player_game_rows_published"], s["players_without_game_rows"],
           s["players_listed_but_no_final_row"],
           s["players_no_exact_name_in_box_scores"])))

    # --- coverage summary, one row per report player
    def why_blank(p):
        if p["coverage"] == "listed_in_box_scores_but_no_final_game_row_at_capture":
            return "listed in an official box score, but no Final-game row at capture time"
        if p["coverage"] == "no_exact_name_in_any_official_box_score":
            return ("no exact name in any captured official box score (has not appeared "
                    "this season, or the report prints a spelling that matches no "
                    "box-score name - not guessed, flag F108)")
        return ""

    cov_rows = []
    for p in doc["players"]:
        latest_src = p.get("latest_source_url") or INJ_INDEX
        cov_rows.append([
            esc(p["player"]),
            esc(", ".join(p["teams_on_reports"]) or None) if p["teams_on_reports"] else NA,
            esc(p["latest_status"]),
            esc(p["latest_edition_label"] or p["latest_edition"]),
            ("%d" % len(p["games"])) if p["games"] else NA,
            esc(why_blank(p)) if not p["games"] else "logged",
            elink(latest_src, "injury PDF"),
        ])
    body.append(h2("Coverage by report player",
                   "Every player named by a stored official injury-report edition, their "
                   "newest designation, and how many official game rows exist for them."))
    body.append(table(
        ["Player", "Team(s) on reports", "Newest status", "Newest edition",
         "Game rows", "Why blank", "Source"],
        cov_rows,
        note="The newest designation is the latest stored edition that names the player. "
             "A blank Game-rows cell means no official box-score row exists for that "
             "player in a Final game — the Why-blank column states which case applies; "
             "flagged on the Flagged for Review page (F108), not filled in."))

    # --- players with no game rows: explicit blank + flag table
    missing = [p for p in doc["players"] if not p["games"]]
    if missing:
        miss_rows = []
        for p in missing:
            src = p.get("latest_source_url") or INJ_INDEX
            miss_rows.append([
                esc(p["player"]),
                esc(", ".join(p["teams_on_reports"]) or None) if p["teams_on_reports"] else NA,
                esc(p["latest_status"]),
                NA, NA, NA, NA,
                esc(why_blank(p)),
                elink(src, "injury PDF"),
            ])
        body.append(h2("Report players with no official box-score row (blank + flagged)",
                       "The R21 fields cannot be confirmed for these players from any "
                       "official box score of a Final game in the archive. They are left "
                       "blank and published on the Flagged for Review page (flag F108)."))
        body.append(table(
            ["Player", "Team(s) on reports", "Newest status", "Minutes", "Points",
             "Rebounds", "Assists", "Why blank", "Source"],
            miss_rows,
            note="Every stat value is deliberately blank: no official Final-game "
                 "box-score row exists, so nothing is inferred."))

    # --- the game logs themselves
    log_rows = []
    for p in doc["players"]:
        for g in p["games"]:
            log_rows.append([
                esc(p["player"]),
                esc(g["date"]),
                esc(g["team"]),
                esc(g["opponent"]),
                cell(g["minutes"]),
                cell(g["points"]),
                cell(g["rebounds"]),
                cell(g["assists"]),
                elink(g["box_score_url"], "box score"),
            ])
    body.append(h2("Game logs (one row per player-game)",
                   "Minutes, points, rebounds and assists with the opponent, for every "
                   "report player with official game rows, sorted by player then date."))
    body.append(table(
        ["Player", "Date", "Team", "Opponent", "MIN", "PTS", "REB", "AST", "Source"],
        log_rows,
        note="MIN is the official minutes string (MM:SS) from the box score. Team and "
             "Opponent are the official team tri-codes of that game. Source is the "
             "official nba.com box-score page the row was read from (archived verbatim "
             "with URL, retrieval time and SHA-256)."))

    html = bd.page(
        "Per-player game logs (R21)",
        "Minutes, points, rebounds, assists and the opponent for the players on "
        "stored official injury reports — one row per game, each row from the "
        "official box score it links to.",
        "\n".join(body))
    return {"player-logs.html": html}


def main():
    doc = build_data()
    s = doc["summary"]
    print("players on stored injury reports : %d" % s["injury_report_players"])
    print("  with official game rows        : %d" % s["players_with_game_rows"])
    print("  without (blank + flagged)      : %d" % s["players_without_game_rows"])
    print("    ... listed, no Final row yet : %d" % s["players_listed_but_no_final_row"])
    print("    ... no exact name in boxes   : %d" % s["players_no_exact_name_in_box_scores"])
    print("player-game rows published       : %d" % s["player_game_rows_published"])
    print("Final games parsed               : %d / %d" % (s["box_score_games_final"],
                                                          s["box_score_captures_games"]))
    print("written: %s" % os.path.relpath(OUT_JSON, ROOT))


if __name__ == "__main__":
    main()
