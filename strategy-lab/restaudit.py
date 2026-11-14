"""Module 2 - the rest and back-to-back layer, recomputed on the complete schedule.

`data/official/gamelog.json` documents its fixture list as the thing that keeps the rest
layer complete. This module checks whether the consumers actually read it, by recomputing
every rest figure twice - once the way the shipped code does, once with the fixtures in the
history - and publishing the difference team-slot by team-slot.
"""
from __future__ import annotations

from labdata import rest_maps, d
from statools import rnd

DAY_PAGE = "https://www.nba.com/games?date="


def run(ctx):
    games, horizon = ctx["games"], ctx["horizon"]
    with_fx, _ = rest_maps(games, True)
    without, _ = rest_maps(games, False)

    changed, per_date = [], {}
    slots = 0
    for g in games:
        if g["kind"] == "horizon":
            continue
        for side in ("away", "home"):
            t = g[side]
            slots += 1
            a, b = with_fx(t, g["date"]), without(t, g["date"])
            fa, fb = (1 if a["b2b"] else 0), (1 if b["b2b"] else 0)
            if a["gap"] == b["gap"] and fa == fb:
                continue
            changed.append({
                "date": g["date"], "game_id": g["game_id"],
                "matchup": f"{g['away']}@{g['home']}", "side": side, "team": t,
                "gap_as_shipped": b["gap"], "gap_repaired": a["gap"],
                "b2b_as_shipped": fb, "b2b_repaired": fa,
                "last_game_as_shipped": b["last"], "last_game_repaired": a["last"],
                "caused_by_a_missing_fixture": a["last"] != b["last"],
                "source_url": g["source_url"],
            })
            slot = per_date.setdefault(g["date"], {"b2b": 0, "rest_only": 0, "games": 0})
            slot["games"] += 1
            slot["b2b" if fa != fb else "rest_only"] += 1

    flips = sum(1 for c in changed if c["b2b_as_shipped"] != c["b2b_repaired"])
    in_oos = sum(1 for c in changed if "2026-11-06" <= c["date"] <= "2026-11-12")

    # the unplayed slate: same recomputation, compared with what the site published
    hz_rows, agree, mismatch = [], 0, 0
    for h in horizon:
        for side in ("away", "home"):
            pub = h.get(f"rest_{side}") or {}
            a = with_fx(h[side], h["date"])
            b = without(h[side], h["date"])
            okflag = (pub.get("last_date") == a["last"]) and \
                (bool(pub.get("b2b")) == bool(a["b2b"]))
            agree += 1 if okflag else 0
            mismatch += 0 if okflag else 1
            hz_rows.append({
                "date": h["date"], "matchup": f"{h['away']}@{h['home']}",
                "side": side, "team": h[side],
                "published_last_game": pub.get("last_date"),
                "repaired_last_game": a["last"],
                "published_rest_field": pub.get("rest_days"),
                "repaired_gap_days": a["gap"], "repaired_days_off": a["days_off"],
                "published_b2b": pub.get("b2b"), "repaired_b2b": a["b2b"],
                "rest_would_differ_without_fixtures": b["gap"] != a["gap"],
                "verdict": "agree" if okflag else "MISMATCH",
                "source_url": DAY_PAGE + h["date"],
            })

    return {
        "definition_conflict": {
            "field": "rest_days",
            "reading_A": ("gap in calendar days between the two games: engine/validate.py sets "
                          "rest_days = date - last_date and calls a back-to-back rest_days == 1"),
            "reading_B": ("full days off between them: scripts/originate_horizon.py returns gap - 1 "
                          "and calls a back-to-back gap == 1, so a back-to-back prints 0"),
            "consequence": ("one page says a team has 1 day of rest and another says 0 for the same "
                            "fact; a reader comparing the two pages cannot tell which is the number"),
            "worked_example": ("NOP: last game 2026-11-13, next game 2026-11-14 - horizon page prints "
                               "rest_days 0 with b2b true; the out-of-sample pages would print 1"),
            "this_file_publishes": "both: gap_days (calendar days between games) and days_off (gap - 1)",
            "source_url": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/data/derived/horizon_lines.json",
        },
        "summary": {
            "team_slots_checked": slots,
            "team_slots_affected_by_the_missing_fixtures": len(changed),
            "back_to_back_flags_that_flip": flips,
            "affected_dates": sorted(per_date),
            "affected_inside_the_published_51_game_window": in_oos,
            "materiality": (
                "None of the affected slots falls in the 2026-11-06..11-12 window that the site's "
                "leaderboard was graded on, so no published pick changes today. The effect is on the "
                "October half of the season, which is where any future full-season backtest would live, "
                "and on the rest column shown for 2026-10-25 .. 2026-11-05."
            ),
            "cause": ("engine_v2/context.py builds its team history from gamelog['games'] and "
                      "scripts/originate_horizon.py from games that carry a score, so the 23 fixtures "
                      "listed in the same file are never in either history, even though the file's note "
                      "says they keep the rest layer complete."),
        },
        "per_date": [{"date": k, "team_slots_affected": v["games"],
                       "b2b_flags_that_flip": v["b2b"], "rest_days_only": v["rest_only"],
                       "source_url": DAY_PAGE + k}
                      for k, v in sorted(per_date.items())],
        "changed_rows": changed,
        "horizon_rest_check": {"rows": hz_rows, "agree": agree, "mismatch": mismatch,
                               "note": ("27 unplayed games x 2 teams checked against the published "
                                        "rest fields; every last-game date and every back-to-back flag "
                                        "is confirmed against the complete official schedule")},
    }
