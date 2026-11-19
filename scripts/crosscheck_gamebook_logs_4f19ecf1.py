#!/usr/bin/env python3
"""crosscheck_gamebook_logs_4f19ecf1.py — two-reader audit of the 11/17–11/18
per-player game logs (R21).

Two independent derivations of the same official record exist in this repo:

  * `data/official/player_game_logs_2026-11-1[78].json` — session
    `arena/e3d25abc-nba1` (PR #179), parsed from the nba.com game-page
    `__NEXT_DATA__` player blocks.
  * `data/official/player_game_logs_2026-11-1[78]_gamebook_4f19ecf1.json` —
    session `arena/4f19ecf1-nba1` (§72), parsed by
    `scripts/capture_player_logs_2026_11_17_18.py` from the byte-exact official
    gamebook PDFs (Identity-CID ToUnicode extraction), with the 2026-11-16
    document's parser rules and self-checks.

This script joins the two row sets by game and player name and compares every
stat both carry. Disagreements are published verbatim, never reconciled by
hand. Output: verify/2026-11-19-4f19ecf1/crosscheck_gamebook_vs_gamepage.{json,md}
"""
from __future__ import annotations

import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "verify", "2026-11-19-4f19ecf1")

FIELDS = [
    # (gamebook key, game-page key, label)
    ("minutes_seconds", "minutes_seconds", "minutes_seconds"),
    ("pts", "points", "pts"),
    ("reb", "rebounds", "reb"),
    ("ast", "assists", "ast"),
    ("plus_minus", "plus_minus", "plus_minus"),
    ("stl", "steals", "stl"),
    ("blk", "blocks", "blk"),
    ("tov", "turnovers", "tov"),
    ("pf", "foulsPersonal", "pf"),
    ("fgm", "fieldGoalsMade", "fgm"),
    ("fga", "fieldGoalsAttempted", "fga"),
    ("fg3m", "threePointersMade", "fg3m"),
    ("fg3a", "threePointersAttempted", "fg3a"),
    ("ftm", "freeThrowsMade", "ftm"),
    ("fta", "freeThrowsAttempted", "fta"),
    ("oreb", "offensiveRebounds", "oreb"),
    ("dreb", "defensiveRebounds", "dreb"),
]


def norm(name: str) -> str:
    n = (name or "").strip().lower()
    n = n.replace(".", "")
    if "," in n:  # "Hart, Josh" -> "josh hart"
        last, _, first = n.partition(",")
        n = (first.strip() + " " + last.strip()).strip()
    return re.sub(r"\s+", " ", n)


def load(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
        return json.load(fh)


def index_rows(doc):
    idx = {}
    for r in doc["rows"]:
        gid = r.get("official_game_id") or r.get("game_id")
        key = (r["date"], gid, r.get("team"), norm(r["player"]))
        idx[key] = r
    return idx


def compare(date):
    theirs = load(f"data/official/player_game_logs_{date}.json")
    mine = load(f"data/official/player_game_logs_{date}_gamebook_4f19ecf1.json")
    t_idx, m_idx = index_rows(theirs), index_rows(mine)
    # match also on name-only within the same game (game ids use the same
    # official format in both files, so date+game_id is the join key)
    by_game_name = {}
    for (d, gid, team, nm), r in t_idx.items():
        by_game_name[(d, gid, team, nm)] = r

    agreed = 0
    disagreements = []
    coverage_notes = []
    only_gamebook = []
    only_gamepage = []
    compared_fields = 0
    matched = 0
    for key, mrow in sorted(m_idx.items()):
        trow = by_game_name.get(key)
        if trow is None:
            # the gamebook keeps Inactive-line surnames as single-name rows;
            # the game page lists full names — try surname containment, same
            # team only (two teams can carry the same surname in one game)
            def _tok(n):
                return tuple(sorted(n.split()))
            cand = [(k, r) for k, r in by_game_name.items()
                    if k[0] == key[0] and k[1] == key[1] and k[2] == key[2]
                    and (k[3].endswith(" " + key[3]) or key[3].endswith(" " + k[3])
                         or _tok(k[3]) == _tok(key[3]))]
            if len(cand) == 1:
                trow = cand[0][1]
            else:
                only_gamebook.append(
                    {"date": key[0], "game_id": key[1], "team": key[2],
                     "player": mrow["player"],
                     "played": mrow.get("played"), "dnp_note": mrow.get("dnp_note"),
                     "pts": mrow.get("pts")})
                continue
        matched += 1
        diffs = {}
        one_sided = {}
        for gk, pk, label in FIELDS:
            gv, pv = mrow.get(gk), trow.get(pk)
            if gv is None and pv is None:
                continue
            if gv is None or pv is None:
                # a field one derivation does not carry is a coverage note,
                # not a disagreement
                one_sided[label] = {"gamebook": gv, "game_page": pv}
                continue
            compared_fields += 1
            if gv != pv:
                diffs[label] = {"gamebook": gv, "game_page": pv}
        gb_played, pg_played = bool(mrow.get("played")), bool(trow.get("played"))
        if gb_played != pg_played:
            diffs["played"] = {"gamebook": gb_played, "game_page": pg_played}
        if diffs:
            disagreements.append(
                {"date": key[0], "game_id": key[1],
                 "player_gamebook": mrow["player"], "player_game_page": trow["player"],
                 "diffs": diffs, "fields_carried_by_one_reader_only": one_sided})
        else:
            agreed += 1
            if one_sided:
                coverage_notes.append(
                    {"date": key[0], "game_id": key[1],
                     "player_gamebook": mrow["player"],
                     "fields_carried_by_one_reader_only": sorted(one_sided)})
    for key, trow in sorted(by_game_name.items()):
        def _tok(n):
            return tuple(sorted(n.split()))
        if key not in m_idx and not any(
                k[0] == key[0] and k[1] == key[1] and k[2] == key[2]
                and (k[3].endswith(" " + key[3]) or key[3].endswith(" " + k[3])
                     or _tok(k[3]) == _tok(key[3]))
                for k in m_idx):
            only_gamepage.append(
                {"date": key[0], "game_id": key[1], "team": key[2],
                 "player": trow["player"],
                 "played": trow.get("played"), "comment": trow.get("comment"),
                 "points": trow.get("points")})
    return {"date": date,
            "rows_gamebook": len(m_idx), "rows_game_page": len(t_idx),
            "matched_rows": matched, "identical_rows": agreed,
            "compared_fields": compared_fields,
            "one_sided_field_notes": len(coverage_notes),
            "one_sided_field_labels": sorted({f for n in coverage_notes
                                              for f in n["fields_carried_by_one_reader_only"]}),
            "disagreements": disagreements,
            "only_in_gamebook": only_gamebook,
            "only_in_game_page": only_gamepage}


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    results = [compare("2026-11-17"), compare("2026-11-18")]
    summary = {
        "title": "Two-reader audit: gamebook-PDF logs vs game-page logs, 2026-11-17/18",
        "generated_by": "scripts/crosscheck_gamebook_logs_4f19ecf1.py",
        "session": "arena/4f19ecf1-nba1 (§72)",
        "reader_a": ("data/official/player_game_logs_2026-11-1[78].json — session "
                     "arena/e3d25abc-nba1 (PR #179), nba.com game-page __NEXT_DATA__"),
        "reader_b": ("data/official/player_game_logs_2026-11-1[78]_gamebook_4f19ecf1.json — "
                     "session arena/4f19ecf1-nba1, byte-exact official gamebook PDFs"),
        "rule": ("Rows joined by date + game_id + normalized player name (surname-only "
                 "gamebook rows matched by containment within the same game). Every stat "
                 "both files carry is compared; disagreements are published verbatim and "
                 "never reconciled by hand."),
        "results": results,
    }
    path = os.path.join(OUT_DIR, "crosscheck_gamebook_vs_gamepage.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=1, ensure_ascii=False)
        fh.write("\n")

    md = ["# Two-reader audit — gamebook PDFs vs game pages (2026-11-17/18)", "",
          "Reader A: `data/official/player_game_logs_2026-11-1[78].json` "
          "(game-page derivation, session `arena/e3d25abc-nba1`, PR #179).",
          "Reader B: `data/official/player_game_logs_2026-11-1[78]_gamebook_4f19ecf1.json` "
          "(byte-exact gamebook PDFs, session `arena/4f19ecf1-nba1`).", ""]
    for r in results:
        md.append(f"## {r['date']}")
        md.append("")
        md.append(f"- rows: gamebook {r['rows_gamebook']} / game-page {r['rows_game_page']}"
                  f" — matched {r['matched_rows']}, identical {r['identical_rows']},"
                  f" compared fields {r['compared_fields']}")
        md.append(f"- disagreements: **{len(r['disagreements'])}**")
        for d in r["disagreements"]:
            md.append(f"  - {d['player_gamebook']} ({d['game_id']}): "
                      + json.dumps(d["diffs"], ensure_ascii=False))
        md.append(f"- only in gamebook: {len(r['only_in_gamebook'])}"
                  + (" — " + ", ".join(x["player"] for x in r["only_in_gamebook"])
                     if r["only_in_gamebook"] else ""))
        md.append(f"- only in game page: {len(r['only_in_game_page'])}"
                  + (" — " + ", ".join(x["player"] for x in r["only_in_game_page"])
                     if r["only_in_game_page"] else ""))
        md.append("")
    md_path = os.path.join(OUT_DIR, "crosscheck_gamebook_vs_gamepage.md")
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(md) + "\n")
    for r in results:
        print(r["date"], "matched", r["matched_rows"], "identical", r["identical_rows"],
              "disagreements", len(r["disagreements"]),
              "only-gb", len(r["only_in_gamebook"]),
              "only-pg", len(r["only_in_game_page"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
