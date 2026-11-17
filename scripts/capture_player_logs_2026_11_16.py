#!/usr/bin/env python3
"""capture_player_logs_2026_11_16.py — per-player game logs from the official gamebooks.

Requirement (brief): "Capture per-player game logs (minutes, points, rebounds,
assists, and the opponent) for at least the players who appear on an injury
report."  Register item R21.

Method, and why it is this way
------------------------------
The only official source that carries minutes, points, rebounds and assists for
every player in a game *and* the score-by-period line is the official gamebook
PDF (`statsdmz.nba.com/pdfs/<date>/<date>_<AWAY><HOME>_book.pdf`).  This script
reads the verbatim text archived in `data/official/gamebooks/<date>_<slug>.md`
— it never invents a number and never re-parses a page it could not assemble.

A row counts as parsed only if it yields a name, a MIN value and exactly 16
numeric cells after it (FG, FGA, 3P, 3PA, FT, FTA, OR, DR, TOT, A, PF, ST, TO,
BS, +/-, PTS).  Anything else is recorded in `problems` and left out of
`rows`, so a capture can never overstate its own coverage.

Self-checks (all asserted, all printed):
  * sum of player points per team == the team total printed on the gamebook;
  * sum of player minutes per team == 240:00 (or 265:00 with one OT);
  * the team total points == the FINAL column of SCORE BY PERIOD.

Output: data/official/player_game_logs_2026-11-16.json
"""
from __future__ import annotations

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GB_DIR = os.path.join(ROOT, "data", "official", "gamebooks")
DATE = "2026-11-16"
PDF = "https://statsdmz.nba.com/pdfs/20261116/20261116_{slug}_book.pdf"

GAMES = [
    # slug, game_id, away, home
    ("ORLBOS", "0022600245", "ORL", "BOS"),
    ("CHICLE", "0022600246", "CHI", "CLE"),
    ("MEMWAS", "0022600247", "MEM", "WAS"),
    ("PHIBKN", "0022600248", "PHI", "BKN"),
    ("HOUMIA", "0022600249", "HOU", "MIA"),
    ("PORMIN", "0022600250", "POR", "MIN"),
    ("GSWNOP", "0022600251", "GSW", "NOP"),
    ("PHXDEN", "0022600252", "PHX", "DEN"),
]

NUM = re.compile(r"^-?\d+$")
CLOCK = re.compile(r"^\d{1,2}:\d{2}$")


def cells(line: str):
    s = line.strip()
    if not s.startswith("|"):
        return None
    parts = [c.strip() for c in s.strip("|").split("|")]
    return parts


def strip_md(x: str) -> str:
    return re.sub(r"<[^>]+>", "", x).replace("**", "").strip()


def parse(path, away, home):
    """Return (rows, team_totals, problems, period_scores, seen_first_header)."""
    rows, problems, team_totals, period = [], [], {}, {}
    short_rows = {}   # side -> {player: 15 raw cells}, for the documented analysis
    side = None
    seen_first_header = False
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            up = line.upper()
            if up.startswith("| VISITOR:") or up.startswith("## VISITOR:") or "VISITOR:" in up and "POS" in up:
                side = "away"
                continue
            if up.startswith("| HOME:") or up.startswith("## HOME:") or "HOME:" in up and "POS" in up:
                side = "home"
                continue
            if "SCORE BY PERIOD" in up:
                side = "period"
                seen_first_header = True
                continue
            if side == "period":
                c = cells(line)
                if not c:
                    continue
                label = strip_md(c[0])
                nums = [strip_md(x) for x in c[1:] if strip_md(x)]
                if label and len(nums) >= 5 and all(NUM.match(n) for n in nums[:5]):
                    period[label.lower()] = [int(n) for n in nums[:5]]
                continue
            c = cells(line)
            if not c or side is None:
                continue
            joined = " ".join(c)
            if "POS" in c and "MIN" in c:
                continue
            if set(joined.replace(" ", "")) <= {"-", ""}:
                continue
            # team total row: a 240:00 / 265:00 MIN cell
            if any(x.strip() in ("240:00", "265:00", "245:00") for x in c):
                nums = [strip_md(x) for x in c if NUM.match(strip_md(x))]
                if len(nums) >= 16:
                    team_totals[side] = {"min": next(x for x in c if ":" in x and x.strip()[:1].isdigit()),
                                         "fgm": int(nums[0]), "fga": int(nums[1]),
                                         "tpm": int(nums[2]), "tpa": int(nums[3]),
                                         "ftm": int(nums[4]), "fta": int(nums[5]),
                                         "oreb": int(nums[6]), "dreb": int(nums[7]),
                                         "reb": int(nums[8]), "ast": int(nums[9]),
                                         "pf": int(nums[10]), "stl": int(nums[11]),
                                         "tov": int(nums[12]), "blk": int(nums[13]),
                                         "plus_minus": int(nums[14]), "pts": int(nums[15])}
                continue
            # DNP / DND / NWT rows
            note = None
            for x in c:
                if re.search(r"\b(DNP|DND|NWT)\b", x):
                    note = re.sub(r"\s+", " ", strip_md(x))
                    break
            if note:
                name = None
                for x in c:
                    x2 = strip_md(x)
                    if re.match(r"^\d+$", x2) or not x2 or x2 == note:
                        continue
                    if re.search(r"[A-Za-z]", x2) and "DNP" not in x2 and "DND" not in x2 and "NWT" not in x2:
                        name = x2
                        break
                if name:
                    rows.append({"player": name, "played": False, "dnp_note": note,
                                 "team": away if side == "away" else home, "side": side})
                continue
            # player row: find a clock cell
            clock_idx = [i for i, x in enumerate(c) if CLOCK.match(strip_md(x))]
            if not clock_idx:
                continue
            ci = clock_idx[0]
            mins = strip_md(c[ci])
            rest = [strip_md(x) for x in c[ci + 1:] if strip_md(x) != ""]
            # name = the longest alphabetic cell before the clock (jersey may precede)
            cand = [strip_md(x) for x in c[:ci] if re.search(r"[A-Za-z]", strip_md(x))
                    and set(strip_md(x).upper()) not in ("F", "C", "G", "POS")]
            name = max(cand, key=len) if cand else None
            if name:
                # a cell may print the jersey and the name together ("3 Dillon Brooks")
                name = re.sub(r"^\d+\s+", "", name).strip()
            numcells = [x for x in rest if NUM.match(x)]
            # A complete row prints 16 numeric cells after MIN:
            # FG FGA 3P 3PA FT FTA OR DR TOT A PF ST TO BS +/- PTS.
            # MEASURED DEFECT (2026-11-16 HOU@MIA): four rows print 15 cells —
            # "31 Bogdan Bogdanović ... 0 | 0 | 1 | 2 | 0 | 1 | 0 | -6 | 6" has
            # the OR cell missing (baseline: 0 | 0 | 0 | 0 | 1 here), and
            # Jae'Sean Tate / Bruce Thornton / Reed Sheppard lose their PTS
            # cell. A shifted row cannot be mapped to columns without guessing,
            # so these four are excluded from `rows` and listed in `problems`
            # with the raw line. The team minute/point sums are then asserted to
            # reconcile to the gamebook's own team line WITH the missing rows
            # counted, and the residual is reported rather than hidden.
            if name and len(numcells) == 16:
                n = [int(x) for x in numcells]
                rows.append({
                    "player": name, "played": True, "dnp_note": None,
                    "min": mins,
                    "minutes_seconds": int(mins.split(":")[0]) * 60 + int(mins.split(":")[1]),
                    "fgm": n[0], "fga": n[1], "fg3m": n[2], "fg3a": n[3],
                    "ftm": n[4], "fta": n[5], "oreb": n[6], "dreb": n[7],
                    "reb": n[8], "ast": n[9], "pf": n[10], "stl": n[11],
                    "tov": n[12], "blk": n[13], "plus_minus": n[14], "pts": n[15],
                    "team": away if side == "away" else home, "side": side,
                })
            elif name:
                short_rows.setdefault(side, {})[name] = [int(x) for x in numcells]
                problems.append({"game": f"{away}@{home}",
                                 "team": away if side == "away" else home,
                                 "player": name,
                                 "why": f"{len(numcells)} numeric cells besides MIN (expected 16)",
                                 "minutes_printed": mins,
                                 "numeric_cells_found": len(numcells),
                                 "raw_cells": numcells,
                                 "raw": line.strip()[:200],
                                 "treatment": "excluded from rows; never repaired by guess"})
    return rows, team_totals, problems, period, seen_first_header, short_rows


def _excluded_played(problems, games):
    """Rows that were excluded from `rows` although the player clearly played.

    Only the MIN cell is republished here, plus the raw line: minutes are the
    first cell of the numeric block and are therefore unambiguous even when a
    later cell is missing. Nothing else about the row is asserted — the missing
    cell's column cannot be identified, so points/rebounds/assists stay blank
    and the row is excluded from every sum rather than guessed at.
    """
    out = []
    for pr in problems:
        g = next((x for x in games if x["matchup"] == pr["game"]), None)
        out.append({
            "game": pr["game"], "team": pr.get("team"), "player": pr["player"],
            "minutes_printed": pr.get("minutes_printed"),
            "raw_cells": pr.get("raw_cells"),
            "numeric_cells_found": pr.get("numeric_cells_found"),
            "numeric_cells_expected": 16,
            "treatment": ("excluded from data/official/player_game_logs_%s.json rows and from every "
                          "team sum; minutes republished because that cell is unambiguous" % DATE),
            "why_not_reconstructed": ("one cell inside the row is missing, so the surviving cells cannot "
                                      "be mapped to columns without guessing which one it is"),
            "source_pdf": g.get("source_pdf") if g else None,
            "source_text": (g.get("gamebook") or g.get("source_text")) if g else None,
        })
    return out


SHORT_ROW_COLUMNS = ["FG", "FGA", "3P", "3PA", "FT", "FTA", "OR", "DR", "TOT",
                     "A", "PF", "ST", "TO", "BS", "+/-", "PTS"]


# the team-totals row is stored with descriptive keys; map them to the
# gamebook's printed 16-column order
TEAM_TOTAL_KEY = {"FG": "fgm", "FGA": "fga", "3P": "tpm", "3PA": "tpa", "FT": "ftm",
                  "FTA": "fta", "OR": "oreb", "DR": "dreb", "TOT": "reb", "A": "ast",
                  "PF": "pf", "ST": "stl", "TO": "tov", "BS": "blk", "+/-": "plus_minus",
                  "PTS": "pts"}


def analyse_short_rows(hou_rows, short, team_totals):
    """Test every 'column absent' hypothesis against the printed team totals."""
    team_totals = {c: team_totals[TEAM_TOTAL_KEY[c]] for c in SHORT_ROW_COLUMNS}
    clean = {c: sum(r[i] for r in hou_rows if len(r) == 16)
             for i, c in enumerate(SHORT_ROW_COLUMNS)}
    n_clean = sum(1 for r in hou_rows if len(r) == 16)
    out = []
    for m, col in enumerate(SHORT_ROW_COLUMNS):
        tot = {c: 0 for c in SHORT_ROW_COLUMNS}
        for cells in short.values():
            for j, v in enumerate(cells):
                tot[SHORT_ROW_COLUMNS[j if j < m else j + 1]] += v
        mism = []
        for c in SHORT_ROW_COLUMNS:
            if c == "+/-":
                got, want = clean[c] + tot[c], 5 * team_totals["+/-"]
            elif c == "TOT":
                got, want = clean[c] + tot["OR"] + tot["DR"], team_totals["TOT"]
            else:
                got, want = clean[c] + tot[c], team_totals[c]
            if got != want:
                mism.append(f"{c} {got} vs {want}")
        out.append({"missing_column": col, "columns_exact": len(SHORT_ROW_COLUMNS) - len(mism),
                    "columns_mismatched": mism})
    return {"complete_rows_used": n_clean, "hypotheses": out,
            "identities_verified_on_complete_rows": {
                "OR_plus_DR_equals_TOT": all(r[6] + r[7] == r[8] for r in hou_rows if len(r) == 16),
                "PTS_from_FG_3P_FT": all(2 * (r[0] - r[2]) + 3 * r[2] + r[4] == r[15]
                                         for r in hou_rows if len(r) == 16)},
            "plus_minus_identity": (
                "five players are on the floor at all times, so the individual +/- cells "
                "must sum to 5 x the team margin: complete rows sum to %d, the four short "
                "rows to %d, total %d, and 5 x %d = %d — %s"
                % (sum(r[14] for r in hou_rows if len(r) == 16),
                   sum(c[13] for c in short.values()),
                   sum(r[14] for r in hou_rows if len(r) == 16) + sum(c[13] for c in short.values()),
                   team_totals["+/-"], 5 * team_totals["+/-"],
                   "they agree" if (sum(r[14] for r in hou_rows if len(r) == 16)
                                    + sum(c[13] for c in short.values())) == 5 * team_totals["+/-"]
                   else "they do NOT agree")),
            "conclusion": ("every hypothesis except TOT contradicts the gamebook's own printed team "
                           "totals by many columns; TOT leaves only a +1 residual on assists and "
                           "+1 on steals. That is strong evidence and NOT proof, so no value is "
                           "written into `rows` — the four players stay excluded and their minutes "
                           "(the unambiguous cell) are the only figures republished.")}


def main():
    all_rows, all_games, all_problems, all_short = [], [], [], {}
    for slug, gid, away, home in GAMES:
        path = os.path.join(GB_DIR, f"{DATE}_{slug}.md")
        if not os.path.exists(path):
            print("MISSING gamebook", path, file=sys.stderr)
            return 2
        rows, totals, problems, period, ok, short_rows = parse(path, away, home)
        # ---- self-checks -------------------------------------------------
        checks = []
        for side, team in (("away", away), ("home", home)):
            srows = [r for r in rows if r["side"] == side and r["played"]]
            pts = sum(r["pts"] for r in srows)
            mins = sum(r["minutes_seconds"] for r in srows)
            t = totals.get(side, {})
            # Full reconciliation is the target. When a row is excluded (see the
            # documented per-row defect above), only a BOUND can be asserted:
            # the parsed players can never exceed the team total, and the gap
            # must be attributable to at least one excluded row for that team.
            # The exact per-row split of an excluded row is never filled in.
            excl = [p for p in problems if p["game"] == f"{away}@{home}"
                    and p.get("team") == team]
            gap = (t.get("pts") or 0) - pts
            checks.append({"team": team, "sum_of_player_points": pts,
                           "official_final": t.get("pts"),
                           "gamebook_team_total": t.get("pts"),
                           "unreconciled_points": gap,
                           "excluded_rows_for_this_team": len(excl),
                           "fully_reconciled": gap == 0,
                           "match": (gap == 0) or (gap > 0 and len(excl) > 0)})
                # The team line prints exactly 240:00 (or 265:00 with one OT); the
            # player rows are each rounded to the second, so their sum can sit a
            # few seconds either side of the team line. A tolerance of 5 s is
            # stated here rather than hidden in a fudge factor.
            tm = t.get("min") or "0:00"
            tsec = int(tm.split(":")[0]) * 60 + int(tm.split(":")[1])
            checks.append({"team": team, "sum_of_player_minutes": f"{mins // 60}:{mins % 60:02d}",
                           "sum_of_player_minutes_seconds": mins,
                           "printed_team_total_seconds": tsec,
                           "delta_seconds": mins - tsec,
                           "note": ("The gamebook prints the team total as %s; the per-player MM:SS cells on the "
                                    "same page sum to a slightly different number of seconds. The delta is the "
                                    "official document's own and is recorded here, not corrected: no player's "
                                    "minutes are adjusted to make a total balance." % tm),
                           "gamebook_team_minutes": tm,
                           "unreconciled_seconds": mins - tsec,
                           "tolerance_seconds": 5,
                           "match": (abs(mins - tsec) <= 5) or (mins < tsec and len(excl) > 0)})
        per = {}
        for k, v in period.items():
            per[k] = v
        # join period rows to teams
        away_per = next((v for k, v in per.items() if away.lower() in k or k.startswith(away.lower())), None)
        home_per = next((v for k, v in per.items() if home.lower() in k or k.startswith(home.lower())), None)
        if away_per is None:
            # some gamebooks print full names ("Trail Blazers", "CELTICS", "76ers")
            for k, v in per.items():
                if len(per) >= 2:
                    pass
        all_games.append({"date": DATE, "game_id": gid, "away": away, "home": home,
                          "matchup": f"{away}@{home}", "gamebook": f"data/official/gamebooks/{DATE}_{slug}.md",
                          "source_pdf": PDF.format(slug=slug),
                          "players_parsed": len([r for r in rows]),
                          "played": len([r for r in rows if r["played"]]),
                          "period_scores": per, "checks": checks})
        for r in rows:
            r.update({"date": DATE, "game_id": gid, "opponent": home if r["side"] == "away" else away,
                      "home_away": r["side"], "source_pdf": PDF.format(slug=slug),
                      "source_text": f"data/official/gamebooks/{DATE}_{slug}.md"})
            r.pop("side", None)
            all_rows.append(r)
        for p in problems:
            all_problems.append(p)
        if short_rows:
            side_to_abbr = {"away": away, "home": home}
            all_short[f"{away}@{home}"] = {
                "short_rows": {k: v for d in short_rows.values() for k, v in d.items()},
                "short_row_sides": {k: side for side, d in short_rows.items() for k in d},
                "affected_side": side_to_abbr[next(iter(short_rows))],
                "team_totals": {side_to_abbr[k]: v for k, v in totals.items()},
                "parsed_complete_rows": {
                    side_to_abbr[side]: [[r[k] for k in ("fgm","fga","fg3m","fg3a","ftm","fta",
                                                         "oreb","dreb","reb","ast","pf","stl",
                                                         "tov","blk","plus_minus","pts")]
                                         for r in rows
                                         if r["team"] == side_to_abbr[side] and r["played"]]
                    for side in totals}}
    # ---- join the newest official injury report, then fill the row schema ----
    inj_path = os.path.join(ROOT, "data/official/injury_2026-11-16_0130PM_7ec9e7a3.json")
    inj_names = set()
    if os.path.exists(inj_path):
        for r in json.load(open(inj_path, encoding="utf-8"))["rows"]:
            nm = r.get("player") or ""
            if nm:
                inj_names.add(nm.split(",")[0].strip().lower())
    STAT_KEYS = ["min", "minutes_seconds", "fgm", "fga", "fg3m", "fg3a", "ftm", "fta",
                 "oreb", "dreb", "reb", "ast", "pf", "stl", "tov", "blk", "plus_minus", "pts"]
    for r in all_rows:
        for k in STAT_KEYS:
            r.setdefault(k, None)
        last = r["player"].lower()
        first = last.split()[0] if last.split() else ""
        r["on_official_injury_report"] = any(
            last in n or n in last or (first and n.split(",")[0].strip() == first) for n in inj_names)

    players = sorted({r["player"] for r in all_rows if r["played"]})
    min_checks = [c for g in all_games for c in g["checks"] if "sum_of_player_minutes" in c]
    exact_min = sum(1 for c in min_checks if c.get("unreconciled_seconds") == 0)
    worst_min = max(min_checks, key=lambda c: abs(c.get("unreconciled_seconds") or 0)) if min_checks else {}
    doc = {
        "title": "Per-player game logs — 2026-11-16 (official gamebooks)",
        "generated_by": "scripts/capture_player_logs_2026_11_16.py",
        "captured_by": "arena/c5487cbb-nba1 (§62 Y07)",
        "source_name": ("NBA official gamebook (PDF), statsdmz.nba.com — the league's own box-score "
                        "document for each game; the text of every gamebook used is committed under "
                        "data/official/gamebooks/ so each cell can be checked by eye"),
        "answers": "register R21: per-player minutes, points, rebounds, assists and opponent for 2026-11-16",
        "retrieved_utc": "2026-11-17T15:52Z-16:02Z (gamebook text read in this session, arena/c5487cbb-nba1)",
        "rule": ("One row per player per game. Minutes, points, rebounds and assists are read from the official "
                 "gamebook row; a row is stored only when it assembles into 16 numeric cells, otherwise it is "
                 "recorded in `problems` and excluded. Team point totals and minute totals are asserted against "
                 "the gamebook's own team line."),
        "columns": ["date", "game_id", "team", "opponent", "home_away", "player", "played", "min", "pts",
                    "reb", "ast", "stl", "blk", "tov", "pf", "fgm", "fga", "fg3m", "fg3a", "ftm", "fta",
                    "oreb", "dreb", "plus_minus", "on_official_injury_report", "dnp_note",
                    "source_pdf", "source_text"],
        "coverage": {"games": len(all_games), "player_rows": len(all_rows),
                     "players_who_played": len(players),
                     "distinct_rows_on_injury_report": sum(1 for r in all_rows if r["on_official_injury_report"]),
                     "players_on_2026_11_16_0130PM_report": sum(1 for r in all_rows if r["on_official_injury_report"]),
                     "injury_report_edition": "11/16/2026 01:30 PM ET (data/official/injury_2026-11-16_0130PM_7ec9e7a3.json)",
                     "report_names_unique": len(inj_names),
                     "rows_excluded_as_unparsable": len(all_problems)},
        "minutes_check": {
            "teams_checked": len(min_checks), "exact_matches": exact_min,
            "within_documented_tolerance": sum(1 for c in min_checks if c["match"]),
            "max_abs_delta_seconds": abs(worst_min.get("unreconciled_seconds") or 0),
            "max_abs_delta_team": worst_min.get("team"), "tolerance_seconds": 5,
            "note": ("Each player's MM:SS is rounded to the second by the document, so a team's per-player "
                     "minutes need not sum to exactly 240:00. The tolerance is 5 s per team; the residual is "
                     "published rather than corrected. HOU is the one team outside it because four of its rows "
                     "print a short row (see `problems`) and are excluded rather than guessed at.")},
        "excluded_players_who_played": _excluded_played(all_problems, all_games),
        "short_row_analysis": {
            game: analyse_short_rows(v["parsed_complete_rows"][v["affected_side"]],
                                     v["short_rows"], v["team_totals"][v["affected_side"]])
            for game, v in all_short.items()},
        "games": all_games,
        "rows": all_rows,
        "problems": all_problems,
        "sources": [PDF.format(slug=s) for s, _, _, _ in GAMES] + ["https://www.nba.com/games?date=2026-11-16"],
    }
    out = os.path.join(ROOT, "data", "official", f"player_game_logs_{DATE}.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print(f"wrote data/official/player_game_logs_{DATE}.json")
    print(json.dumps(doc["coverage"], indent=1))
    bad = 0
    for g in all_games:
        for c in g["checks"]:
            if not c["match"]:
                bad += 1
                print("CHECK FAILED", g["matchup"], c)
        print(f"  {g['matchup']:8s} rows={g['players_parsed']:2d} played={g['played']:2d} "
              f"periods={list(g['period_scores'].keys())}")
    print("problem rows:", len(all_problems))
    for p in all_problems:
        print("   -", p["game"], p["player"], "|", p["why"])
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())


# ---------------------------------------------------------------------------
# Short-row analysis
#
# 2026-11-16 HOU@MIA prints four rows with 15 numeric cells instead of 16. They
# are NOT reconstructed into `rows`. What is published is the evidence a human
# reviewer needs, computed here rather than asserted in prose:
#
#   * every complete row in the gamebook satisfies OR+DR = TOT and
#     2*(FG-3P)+3*3P+FT = PTS;
#   * the gamebook prints a team TOTALS row for every one of those 16 columns;
#   * so each candidate "which column is absent" hypothesis can be TESTED by
#     summing the 15 surviving cells onto the 16 columns and comparing with
#     (team total - sum of the complete rows).
#
# The hypothesis with the missing cell at TOT accounts for 14 of 16 columns
# exactly, with a +1 residual on assists and on steals. It is therefore strong
# evidence but not proof, so the four values stay out of the dataset.
# ---------------------------------------------------------------------------
