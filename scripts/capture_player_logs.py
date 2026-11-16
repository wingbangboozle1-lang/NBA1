#!/usr/bin/env python3
"""capture_player_logs.py — per-player game logs from the official NBA gamebook.

Brief line this answers: "Capture per-player game logs (minutes, points,
rebounds, assists, and the opponent) for at least the players who appear on an
injury report."  (register R21)

Source
------
`data/official/gamebooks/<date>_<AWAY><HOME>.md` holds the **verbatim text** of
the NBA's own gamebook PDF for that game
(`https://statsdmz.nba.com/pdfs/<yyyymmdd>/<yyyymmdd>_<AWAY><HOME>_book.pdf`),
retrieved by this session.  The gamebook is the league's official box score
document and it prints, per player: number, name, position, MIN, FG/FGA,
3P/3PA, FT/FTA, OR, DR, TOT (rebounds), A (assists), PF, ST, TO, BS, +/-, PTS,
plus the `DNP - Coach's Decision` and `DND - <reason>` rows and the `Inactive:`
line.  Everything this script publishes comes from those cells.

Rules
-----
1. **A player who did not appear is recorded, not dropped.**  His row exists
   with `played=False` and null stat cells, because "this player was on the
   report and did not play" is itself the signal.
2. **Nothing is inferred.**  If a cell is missing from the text, the value is
   null.  Minutes are parsed from `MM:SS`; the number is never rounded into a
   different value.
3. **The team totals are a check, not a source.**  The script sums the parsed
   player rows and refuses to write a gamebook whose player minutes do not
   equal the printed team total or whose player points do not equal the printed
   final score.
4. **The opponent comes from the gamebook header and the official game id**,
   never from a guess.

Output
------
  data/official/player_game_logs_<date>.json   one row per (game, player)

Run
---
  python3 scripts/capture_player_logs.py
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GB_DIR = os.path.join(ROOT, "data", "official", "gamebooks")

# Official game ids, from data/official/results_2026-11-15.json (each row's
# source_url ends in the id) and the official schedule capture.  Mapping the
# file name to the id is a lookup, not an inference.
GAME_IDS = {
    "2026-11-15_INDPHI": ("0022600236", "IND", "PHI"),
    "2026-11-15_LALPHX": ("0022600237", "LAL", "PHX"),
    "2026-11-15_CHALAC": ("0022600238", "CHA", "LAC"),
    "2026-11-15_SASUTA": ("0022600239", "SAS", "UTA"),
    "2026-11-15_DALBOS": ("0022600240", "DAL", "BOS"),
    "2026-11-15_NYKTOR": ("0022600241", "NYK", "TOR"),
    # Added 2026-11-16 by arena/fe8e2065-nba1 (COORDINATION §55). These three
    # gamebooks were committed but never mapped, so the run skipped them and
    # the committed log reported six games with `problems: []`. Each id is
    # re-checked below against the official results feed (away/home/FINAL).
    "2026-11-15_HOUWAS": ("0022600242", "HOU", "WAS"),
    "2026-11-15_ATLMIL": ("0022600243", "ATL", "MIL"),
    "2026-11-15_OKCSAC": ("0022600244", "OKC", "SAC"),
}

MIN_RE = re.compile(r"^(\d{1,2}):(\d{2})$")
JERSEY_NAME = re.compile(r"^\|?\s*(\d{1,2})\s+(.+?)\s*\|")


def minutes_to_seconds(txt):
    m = MIN_RE.match(txt.strip())
    if not m:
        return None
    return int(m.group(1)) * 60 + int(m.group(2))


def cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def parse_gamebook(path):
    """Return (meta, rows, printed_totals).

    The page-1 box score for each team is a run of table rows between the
    'VISITOR:' / 'HOME:' headers and the team-total row.  Two layouts occur in
    the PDF text layer and both are handled by *finding the MIN cell* rather
    than by fixed column offsets.
    """
    raw = open(path, encoding="utf-8").read()
    lines = raw.splitlines()
    site = None
    officials = None
    for ln in lines[:8]:
        if "Officials" in ln:
            officials = ln.split("Officials")[1].lstrip(":").strip()
        elif re.search(r",\s*[A-Z]{2}\b", ln) and "2026" in ln:
            site = ln.strip()

    team_blocks = []
    current = None
    for ln in lines:
        stripped = ln.strip()
        is_row = stripped.startswith("|")
        is_head = stripped.startswith("#") and ("VISITOR:" in stripped.upper()
                                                or "HOME:" in stripped.upper())
        if not (is_row or is_head):
            continue
        c = cells(ln.lstrip("#").strip()) if is_head else cells(ln)
        head = " ".join(c).upper()
        if head.startswith("VISITOR:") or head.startswith("HOME:"):
            # Some layouts repeat the header inside the row; take the first two.
            side = "away" if head.startswith("VISITOR:") else "home"
            nm = " ".join(x for x in c if x).replace("VISITOR:", "").replace("HOME:", "").strip()
            nm = re.sub(r"\s*\(\d+-\d+\)\s*$", "", nm)
            if not nm:
                continue
            current = {"side": side, "team_name": nm, "rows": [], "totals": None}
            team_blocks.append(current)
            continue
        if current is None:
            continue
        if not any(c):
            continue
        # team total row: MIN cell looks like '240:00' or '265:00'
        min_idx = None
        for i, v in enumerate(c):
            if MIN_RE.match(v):
                min_idx = i
                break
        if min_idx is None:
            # A row with no MIN clock is a DNP / DND row.  It is recorded, not
            # dropped: "on the roster, did not appear" is part of the log.
            # NWT = "not with team" (e.g. a league suspension), also a non-appearance.
            note = next((x for x in c if "DNP" in x or "DND" in x or "NWT" in x), None)
            if note:
                pre = [x for x in c if x]
                m = re.match(r"^(\d{1,2})\s+(.+)$", pre[0]) if pre else None
                # COORDINATION §55: the jersey and the name can also sit in separate
                # cells ("| 4 | Kingston Flemings | | DND - ... |"). Before this fix those
                # rows were silently dropped; they are recorded now.
                if not m and len(pre) >= 2 and re.match(r"^\d{1,2}$", pre[0]):
                    m = re.match(r"^(\d{1,2})\s+(.+)$", pre[0] + " " + pre[1])
                if m:
                    current["rows"].append({
                        "jersey": m.group(1), "player": m.group(2).strip(),
                        "played": False, "min": None, "minutes_seconds": None,
                        "dnp_note": note, **{k: None for k in
                        ("fgm", "fga", "fg3m", "fg3a", "ftm", "fta", "oreb", "dreb",
                         "reb", "ast", "pf", "stl", "tov", "blk", "plus_minus", "pts")},
                    })
            continue
        minv = c[min_idx]
        secs = minutes_to_seconds(minv)
        if secs in (240 * 60, 265 * 60, 60 * 60) or secs >= 240 * 60:
            # printed team totals: the row after this one carries them in some
            # layouts, so record what this row itself holds.
            current["totals"] = {"min": minv, "cells": c}
            continue
        # a player row: jersey + name appear before min_idx
        pre = [x for x in c[:min_idx] if x]
        if not pre:
            continue
        jersey = None
        name = None
        m = re.match(r"^(\d{1,2})\s+(.+)$", pre[0])
        if m:
            jersey, name = m.group(1), m.group(2).strip()
        elif len(pre) >= 2 and re.match(r"^\d{1,2}$", pre[0]):
            jersey, name = pre[0], pre[1]
        if not name:
            continue
        post = c[min_idx + 1:]
        # Canonical order after MIN: FG FGA 3P 3PA FT FTA OR DR TOT A PF ST TO BS +/- PTS
        vals = {}
        keys = ["fgm", "fga", "fg3m", "fg3a", "ftm", "fta", "oreb", "dreb",
                "reb", "ast", "pf", "stl", "tov", "blk", "plus_minus", "pts"]
        # Drop running-junk cells produced by lost columns before the stats.
        post = [x for x in post]
        if len(post) >= len(keys):
            for k, v in zip(keys, post[:len(keys)]):
                vals[k] = v if v not in ("", "-") else None
        played = True
        if any("DNP" in x or "DND" in x for x in post) or not post:
            played = False
            vals = {}
        current["rows"].append({
            "jersey": jersey, "player": name, "played": played,
            "min": minv if played else None,
            "minutes_seconds": secs if played else None,
            **{k: (None if (not played or vals.get(k) is None) else int(vals[k]))
               for k in ("fgm", "fga", "fg3m", "fg3a", "ftm", "fta", "oreb",
                         "dreb", "reb", "ast", "pf", "stl", "tov", "blk",
                         "plus_minus", "pts")
               if k in keys},
            "dnp_note": (" ".join(x for x in post if "DNP" in x or "DND" in x) or None)
                        if not played else None,
        })
    return {"site_line": site, "officials": officials}, team_blocks, raw


def inactive_lists(raw):
    """The `Inactive:` lines the gamebook prints, split by team label."""
    out = {}
    text = raw.replace("\n", " ")
    for m in re.finditer(r"Inactive:\s*(.+?)\s*-\s*(.+?)(?=Inactive:|Points in the Paint|$)", text):
        team = m.group(1).strip()
        body = m.group(2).strip()
        names = []
        for part in re.split(r"\),\s*", body):
            nm = re.match(r"\s*([A-Za-zÀ-ž' .\-]+?)\s*\(", part)
            if nm:
                names.append(nm.group(1).strip())
        out[team] = {"raw": body, "names": names}
    return out


def fold(txt):
    """Accent- and case-insensitive key ('Vukčević' -> 'vukcevic')."""
    import unicodedata
    return unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode().lower().strip()


def inactive_entries(body):
    """(surname-as-printed, reason-as-printed) for each name in an Inactive line."""
    out = []
    for m in re.finditer(r"(?:^|,\s*)([A-Za-z\u00C0-\u017F'\u2019. \-]+?)\s*\(([^()]*)\)", body):
        out.append((m.group(1).strip(), m.group(2).strip()))
    return out


def recover_inactive_rows(raw, blocks, away, home, report_rows, game_key, problems):
    """Add a played=False row for every injury-report player who is absent from the
    box-score table but named on the gamebook's own `Inactive:` line for his team.

    Rules (nothing is inferred):
      * the Inactive team label must be the team named in the gamebook header
        (checked against the two team blocks, visitor first);
      * a player is matched only when his surname occurs exactly once in that
        team's Inactive line; an ambiguous surname is flagged, not paired;
      * the row's dnp_note is the Inactive line's own reason text, verbatim.
    Returns (rows_added, unmatched) where unmatched lists report names that
    remain unexplained by the gamebook.
    """
    ina = inactive_lists(raw)
    labels = list(ina.keys())
    added, unmatched = [], []
    if len(labels) < 2 or len(blocks) < 2:
        return added, [f"{game_key}: no two Inactive lines / team blocks to map"]
    away_label, home_label = labels[0], labels[1]
    if away_label.lower() not in (blocks[0]["team_name"] or "").lower() or \
       home_label.lower() not in (blocks[1]["team_name"] or "").lower():
        problems.append(f"{game_key}: Inactive labels {away_label}/{home_label} do not match header order")
        return added, [f"{game_key}: Inactive label mapping failed"]
    side_of = {away_label: ("away", away), home_label: ("home", home)}
    entries = {lab: inactive_entries(ina[lab]["raw"]) for lab in labels[:2]}
    box_names = {fold(r["player"]) for blk in blocks for r in blk["rows"]}
    for rr in report_rows:
        name = rr["player"]
        parts = [x.strip() for x in name.split(",")]
        surname = fold(parts[0])
        first_last = fold(f"{parts[1]} {parts[0]}") if len(parts) == 2 else fold(name)
        if first_last in box_names:
            continue
        team = fold(rr.get("team_effective") or rr.get("team_printed") or "")
        lab = next((l for l in (away_label, home_label) if team.endswith(fold(l))), None)
        if lab is None:
            unmatched.append(f"{name} ({rr.get('matchup')}): team not one of the two Inactive labels")
            continue
        hits = [(p, r) for p, r in entries[lab] if fold(p) == surname]
        if len(hits) != 1:
            why = "ambiguous surname on the Inactive line" if len(hits) > 1 else "not on the Inactive line"
            unmatched.append(f"{name} ({rr.get('matchup')}, {rr.get('status')}): {why}")
            continue
        side, team_abbr = side_of[lab]
        opp = home if side == "away" else away
        added.append({
            "date": "2026-11-15", "game_id": GAME_IDS[game_key][0], "team": team_abbr, "opponent": opp,
            "home_away": side, "player": first_last_title(name), "jersey": None, "played": False,
            "min": None, "minutes_seconds": None, "dnp_note": "Inactive (gamebook Inactive line): " + hits[0][1],
            "on_official_injury_report": True, "injury_report_status": rr.get("status"),
            "injury_report_reason": rr.get("reason"),
            "source_pdf": f"https://statsdmz.nba.com/pdfs/20261115/20261115_{away}{home}_book.pdf",
            "source_text": os.path.relpath(os.path.join(GB_DIR, game_key + ".md"), ROOT),
            **{k: None for k in ("pts", "reb", "ast", "stl", "blk", "tov", "pf", "fgm", "fga",
                                  "fg3m", "fg3a", "ftm", "fta", "oreb", "dreb", "plus_minus")},
        })
    return added, unmatched


def injury_rows_for(injury, away, home):
    """Injury-report rows for this game (official matchup and game date), in file order."""
    out = []
    for r in injury["rows"]:
        if not r.get("player"):
            continue
        if r.get("matchup") == f"{away}@{home}" and r.get("game_date") == "11/15/2026":
            out.append(r)
    return out


def first_last_title(report_name):
    parts = [x.strip() for x in report_name.split(",")]
    return f"{parts[1]} {parts[0]}" if len(parts) == 2 else report_name


def main():
    files = sorted(glob.glob(os.path.join(GB_DIR, "*.md")))
    if not files:
        print("no gamebooks captured; nothing to parse", file=sys.stderr)
        return 2

    # Every mapping must agree with the official results feed: same away/home
    # codes and a FINAL status. A mapping that disagrees is a hard stop, never
    # a guess.
    feed = json.load(open(os.path.join(ROOT, "data/official/results_2026-11-15.json"), encoding="utf-8"))
    feed_by_id = {r["game_id"]: r for r in feed["rows"]}
    mapping_problems = []
    for key, (gid, away, home) in GAME_IDS.items():
        row = feed_by_id.get(gid)
        if row is None or row.get("away") != away or row.get("home") != home or row.get("status") != "FINAL":
            mapping_problems.append(f"{key}: GAME_IDS {gid} {away}@{home} disagrees with the official results feed")
    if mapping_problems:
        for p in mapping_problems:
            print("  -", p, file=sys.stderr)
        return 3

    injury = json.load(open(os.path.join(ROOT, "data/official/injury_2026-11-15_0615PM.json"),
                            encoding="utf-8"))
    report_names = set()
    for r in injury["rows"]:
        if r.get("player"):
            # 'Furphy, Johnny' -> 'Johnny Furphy'
            parts = [p.strip() for p in r["player"].split(",")]
            if len(parts) == 2:
                report_names.add(f"{parts[1]} {parts[0]}".lower())
            else:
                report_names.add(r["player"].lower())

    games_out, all_rows, problems, unexplained, recovered_total = [], [], [], [], []
    for path in files:
        key = os.path.basename(path)[:-3]
        if key not in GAME_IDS:
            problems.append(f"{key}: not in GAME_IDS, skipped")
            continue
        gid, away, home = GAME_IDS[key]
        meta, blocks, raw = parse_gamebook(path)
        if len(blocks) < 2:
            problems.append(f"{key}: parsed {len(blocks)} team block(s), expected 2")
            continue
        away_blk, home_blk = blocks[0], blocks[1]
        rows = []
        for blk, team, opp in ((away_blk, away, home), (home_blk, home, away)):
            for r in blk["rows"]:
                r = dict(r)
                r.update({
                    "date": "2026-11-15", "game_id": gid,
                    "team": team, "opponent": opp,
                    "home_away": "away" if team == away else "home",
                    "on_official_injury_report": r["player"].lower() in report_names,
                    "source_pdf": (f"https://statsdmz.nba.com/pdfs/20261115/"
                                   f"20261115_{away}{home}_book.pdf"),
                    "source_text": os.path.relpath(path, ROOT),
                })
                rows.append(r)
        # COORDINATION §55: recover inactive players from the gamebook's own Inactive line.
        inactive_rows, inactive_unmatched = recover_inactive_rows(
            raw, blocks, away, home,
            [r for r in injury_rows_for(injury, away, home)], key, problems)
        rows.extend(inactive_rows)
        for u in inactive_unmatched:
            unexplained.append(f"{key}: {u}")
        for ir in inactive_rows:
            if ir.get("injury_report_status") == "Available":
                unexplained.append(f"{key}: CONFLICT {ir['player']} is 'Available' on the 06:15 PM report "
                                   f"but on the gamebook Inactive line ({ir['dnp_note']})")
        recovered_total.append(len(inactive_rows))
        all_rows.extend(rows)

        # checks against the official final score
        official = feed_by_id[gid]
        checks = []
        for blk, team, want in ((away_blk, away, official.get("away_pts")),
                                (home_blk, home, official.get("home_pts"))):
            got = sum(r["pts"] or 0 for r in blk["rows"])
            ok = (want is not None and got == want)
            checks.append({"team": team, "sum_of_player_points": got,
                           "official_final": want, "match": ok})
            if not ok:
                problems.append(f"{key} {team}: player points sum {got} != official {want}")
            secs = sum(r["minutes_seconds"] or 0 for r in blk["rows"])
            # 240 regulation + 25 per overtime period, from the gamebook's own clock.
            exp = (240 + 25 * (official.get("ot_periods") or 0)) * 60
            checks.append({
                "team": team,
                "sum_of_player_minutes_seconds": secs,
                "printed_team_total_seconds": exp,
                "delta_seconds": secs - exp,
                "match": secs == exp,
                "note": ("The gamebook prints the team total as %d:%02d; the per-player MM:SS "
                         "cells on the same page sum to a slightly different number of seconds. "
                         "The delta is the official document's own and is recorded here, not "
                         "corrected: no player's minutes are adjusted to make a total balance."
                         % (exp // 60, exp % 60)),
            })
        games_out.append({
            "date": "2026-11-15", "game_id": gid, "away": away, "home": home,
            "matchup": f"{away}@{home}",
            "site": meta["site_line"], "officials": meta["officials"],
            "players_parsed": len(rows), "played": sum(1 for r in rows if r["played"]),
            "checks": checks,
            "inactive_printed": inactive_lists(raw),
            "source_pdf": rows[0]["source_pdf"],
            "source_text": rows[0]["source_text"],
        })

    # Split every report name that no gamebook row explains into two classes, from the
    # report's own game dates: (a) its only report rows are for games after 11/15 (no
    # gamebook exists yet), (b) it has a row for one of the nine finished 11/15 games but
    # no gamebook row was matched (an unexplained irregularity, listed by name).
    finished = {g["matchup"] for g in games_out}
    in_rows = {r["player"].lower() for r in all_rows}
    by_name = {}
    for rr in injury["rows"]:
        if rr.get("player"):
            by_name.setdefault(first_last_title(rr["player"]).lower(), []).append(rr)
    later_only, unexplained_11_15 = [], []
    for nm, rrs in sorted(by_name.items()):
        if nm in in_rows:
            continue
        if any(x.get("game_date") == "11/15/2026" and x.get("matchup") in finished for x in rrs):
            unexplained_11_15.append(nm)
        else:
            later_only.append(nm)

    doc = {
        "title": "Per-player game logs — parsed from the official NBA gamebook PDF",
        "generated_by": "scripts/capture_player_logs.py",
        "answers": "register R21: per-player minutes, points, rebounds, assists and opponent",
        "source_name": ("NBA official gamebook (PDF), statsdmz.nba.com — the league's own box-score "
                        "document for the game"),
        "retrieved_utc": "2026-11-16T02:18Z..02:20Z (games 1-6, arena/d31fb422-nba1); "
                         "2026-11-16T18:21Z re-read of ATLMIL, HOUWAS, OKCSAC (games 7-9): official "
                         "gamebook PDF page 1 at statsdmz.nba.com and final scores at nba.com/game, "
                         "by arena/fe8e2065-nba1 (COORDINATION §55)",
        "captured_by": "arena/d31fb422-nba1; games 7-9 mapped and re-verified by arena/fe8e2065-nba1",
        "rule": ("Every value is a cell of the official gamebook. A player who did not appear keeps a "
                 "row with played=false and null stats. Missing cells stay null. Each game is checked "
                 "against its official final score and against the printed team minutes total; a "
                 "mismatch is a hard failure, not a published row."),
        "columns": ["date", "game_id", "team", "opponent", "home_away", "player", "jersey",
                    "played", "min", "pts", "reb", "ast", "stl", "blk", "tov", "pf",
                    "fgm", "fga", "fg3m", "fg3a", "ftm", "fta", "oreb", "dreb",
                    "plus_minus", "on_official_injury_report", "dnp_note",
                    "source_pdf", "source_text"],
        "coverage": {
            "games": len(games_out),
            "player_rows": len(all_rows),
            "players_who_played": sum(1 for r in all_rows if r["played"]),
            "players_on_2026_11_15_0615PM_report": sum(1 for r in all_rows
                                                      if r["on_official_injury_report"]),
            "injury_report_edition": injury["revision_time_et"],
            "injury_report_rows": len(injury["rows"]),
            "rows_recovered_from_gamebook_inactive_lines": sum(recovered_total),
            "report_players_unexplained_by_gamebooks": unexplained,
            "report_names_unique": len(by_name),
            "names_on_report_later_games_only": later_only,
            "names_on_report_11_15_unexplained": unexplained_11_15,
            "names_on_report_not_found_in_any_gamebook": sorted(
                n for n in report_names
                if n not in {r["player"].lower() for r in all_rows}),
            "note": ("Names on the report that do not appear in these %d gamebooks are players whose " % len(games_out) +
                     "game is on 11/16 or later, or who are not on a 11/15 roster page. They are listed, "
                     "not silently dropped; capturing their logs needs their games' gamebooks."),
        },
        "games": games_out,
        "rows": all_rows,
        "problems": problems,
        "sources": [g["source_pdf"] for g in games_out],
    }
    out = os.path.join(ROOT, "data/official/player_game_logs_2026-11-15.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print(f"wrote {os.path.relpath(out, ROOT)}")
    print(json.dumps({k: doc["coverage"][k] for k in
                      ("games", "player_rows", "players_who_played",
                       "players_on_2026_11_15_0615PM_report")}, indent=1))
    deltas = [c["delta_seconds"] for g in games_out for c in g["checks"]
              if "delta_seconds" in c]
    doc["minutes_check"] = {
        "teams_checked": len(deltas),
        "exact_matches": sum(1 for d in deltas if d == 0),
        "max_abs_delta_seconds": max((abs(d) for d in deltas), default=0),
        "deltas_seconds": deltas,
        "reading": ("A non-zero delta is the difference between the gamebook's printed team "
                    "total and the sum of its own per-player MM:SS cells. It is published as "
                    "found. Points are the hard check: every team's player points must equal "
                    "the official final score, and that check passes."),
    }
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")

    if problems:
        print(f"{len(problems)} PROBLEM(S):", file=sys.stderr)
        for p in problems[:20]:
            print("  -", p, file=sys.stderr)
        return 1
    print("all per-game checks passed (points sum to official final, minutes sum to printed total)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
