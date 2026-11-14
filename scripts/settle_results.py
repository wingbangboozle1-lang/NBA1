#!/usr/bin/env python3
"""Settle published paper picks against promoted official finals.

    python3 scripts/settle_results.py --date 2026-11-13

Grades the RecordLine picks in data/originated_lines.json against the promoted
snapshot data/raw/games_completed_<date>.json (written by scripts/promote_finals.py
only after two independent official reads agreed).

Grading rules, stated because they are where a lazy implementation cheats:
  * a pick is graded ONLY against a promoted official FINAL score;
  * side pick HOME wins iff the final home margin > 0; AWAY iff < 0;
  * spread pick covers iff the final margin beats the originated spread
    (home spread +X: home covers iff margin + X > 0);
  * a PASS row is recorded as PASS, never as a loss or a win;
  * nothing is inferred: a game without a promoted final stays ungraded.

Output data/settled_picks_<date>.json: one row per game with the pick, the
final score, the result, and the official source URL of the game.
"""

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return json.load(fh)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    args = ap.parse_args()
    d = args.date

    finals_path = ("data", "raw", f"games_completed_{d}.json")
    if not os.path.exists(os.path.join(ROOT, *finals_path)):
        sys.exit(f"no promoted finals snapshot: {os.path.join(*finals_path)}")
    finals = load(*finals_path)
    fin = {r[7]: {"away": r[1], "away_pts": r[2], "home": r[3], "home_pts": r[4],
                  "ot": r[5]} for r in finals["rows"]}

    lines = load("data", "originated_lines.json")
    games = [g for g in lines["games"] if g["date"] == d]
    if not games:
        sys.exit(f"no published picks dated {d}")

    rows, w = [], 0
    for g in games:
        # game id lives inside the official game-page URL slug:
        # https://www.nba.com/game/nyk-vs-ind-0022600034 -> 0022600034
        gid = None
        for s in g.get("sources", []):
            if "/game/" in s:
                gid = s.rstrip("/").split("-")[-1]
                break
        f = fin.get(gid) if gid else None
        m = g.get("model") or {}
        pick = m.get("pick_side", "—")
        line = m.get("pick_line")
        row = {
            "date": d,
            "matchup": g["matchup"],
            "game_id": gid,
            "pick_side": pick,
            "pick_line": line,
            "gate": m.get("gate"),
            "official_source": next((s for s in g.get("sources", []) if "/game/" in s), None)
            or g.get("sources", [None])[0],
            "settled": bool(f),
        }
        if f is None:
            row.update({"result": "— (no promoted final)", "final_score": "—",
                        "settled_reason": "no official FINAL captured for this game yet"})
        else:
            margin = f["home_pts"] - f["away_pts"]
            row["final_score"] = (f"{f['away']} {f['away_pts']} @ {f['home']} "
                                  f"{f['home_pts']}" + (" (OT)" if f["ot"] else ""))
            row["settled_reason"] = (f"official FINAL transcribed from {finals['source_url']} "
                                     f"and promoted after two agreeing reads "
                                     f"(snapshot data/raw/games_completed_{d}.json)")
            if pick == "HOME":
                won = margin > 0
            elif pick == "AWAY":
                won = margin < 0
            else:
                won = None
            if won is None:
                row["result"] = "PASS — gate G-CFG, no bet"
            else:
                row["result"] = "WIN" if won else "LOSS"
                w += won
            # spread leg: only when a line exists and a side was picked.
            # The line token is the picked team's own spread (e.g. "IND +2.5");
            # the picked team covers iff its margin + its spread > 0.
            if line and pick in ("HOME", "AWAY"):
                spread = float(line.rsplit(" ", 1)[1])
                picked_margin = margin if pick == "HOME" else -margin
                cover = (picked_margin + spread) > 0
                row["spread_result"] = "COVER" if cover else "NO COVER"
        rows.append(row)

    n_pick = sum(1 for r in rows if r.get("result", "").startswith(("WIN", "LOSS")))
    out = {
        "settled_at_utc": __import__("datetime").datetime
        .now(__import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "date": d,
        "finals_snapshot": f"data/raw/games_completed_{d}.json",
        "finals_source_url": finals["source_url"],
        "picks_source": "data/originated_lines.json (RecordLine-1, generated "
                        + lines.get("generated_at_utc", "—") + ")",
        "record": f"{w}-{n_pick - w}" if n_pick else "—",
        "note": "Paper picks graded against our own originated lines. A record here is "
                "descriptive bookkeeping of published picks, not evidence of skill: see "
                "the validation gates and the luck decomposition before quoting it. "
                "PASS rows are never counted as wins or losses.",
        "rows": rows,
    }
    dst = os.path.join(ROOT, "data", f"settled_picks_{d}.json")
    with open(dst, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    graded = [r for r in rows if r["settled"]]
    print(f"settled {len(graded)}/{len(rows)} rows -> data/settled_picks_{d}.json "
          f"record {out['record']}")


if __name__ == "__main__":
    main()
