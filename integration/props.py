"""Player-prop lines and same-game-multi correlation, measured from the captured game logs.

This module exists because a prop number is only defensible if the dispersion around the
mean is measured. The repo's two earlier builds each published prop projections with the
probability field left blank, because at the time there was no per-game player data in the
repository at all (see data/live/player_game_logs.json, `why`).

Sample: 12 official NBA.com "Last 5 Games" rows across 3 players, 9 of them complete
across every column. That is enough to compute a number and an honest interval, and not
enough to call it a league truth. Every table this module writes carries n, the interval
and a verdict field, and the verdict is "not usable for staking" for every row.
"""

import os

from common import (OUT, block_bootstrap, dump, fisher_ci, joint_bounds, load, mean,
                   norm_cdf, pearson, sd, wilson)


def num(v, nd=2):
    """Round for JSON, keeping None as None so the page renders a blank cell."""
    return None if v is None else round(float(v), nd)

STATS = {
    "pts": "Points",
    "reb": "Rebounds",
    "ast": "Assists",
    "min": "Minutes",
    "fgm": "Field goals made",
}


def stat_values(player, stat):
    """Rows that actually carry this stat. A truncated chunk is dropped, never padded."""
    return [g[stat] for g in player["games"] if g.get(stat) is not None]


def line_ladder(values, offsets=(-4.5, -2.5, -0.5, 0.5, 2.5, 4.5)):
    """Hit rate at candidate lines around the sample median.

    With n = 4 a hit rate can only be 0%, 25%, 50%, 75% or 100%, so the empirical column
    is decorative on its own; the Wilson interval beside it is the part that is read.
    """
    med = sorted(values)[len(values) // 2] if values else None
    rows = []
    for off in offsets:
        line = round(med + off, 1) if med is not None else None
        over = sum(1 for v in values if v > line)
        lo, hi = wilson(over, len(values))
        rows.append({
            "line": line,
            "over_count": over, "n": len(values),
            "empirical_over_rate": round(over / len(values), 4) if values else None,
            "wilson_95_lo": round(lo, 4), "wilson_95_hi": round(hi, 4),
            "model_over_prob": round(1.0 - norm_cdf((line - mean(values)) / sd(values)), 4)
            if len(values) > 2 and sd(values) else None,
        })
    return rows


def main():
    logs = load("data", "live", "player_game_logs.json")
    lines = load("integration", "out", "lines.json") if os.path.exists(
        os.path.join(OUT, "lines.json")) else None

    players_out = []
    pair_corr = []
    for p in logs["players"]:
        per_stat = {}
        for key, label in STATS.items():
            vals = stat_values(p, key)
            if not vals:
                per_stat[key] = {"label": label, "n": 0, "mean": None, "sd": None,
                                 "cv": None, "ci_95_block_bootstrap": None, "usable_for_staking": False,
                                 "flag": "no complete rows for this stat"}
                continue
            m, s = mean(vals), (sd(vals) if len(vals) > 1 else None)
            ci = block_bootstrap(vals)
            per_stat[key] = {
                "label": label, "n": len(vals), "values": vals,
                "games": [g["date"] for g in p["games"] if g.get(key) is not None],
                "mean": num(m), "sd": num(s),
                "cv": num(s / m, 3) if s and m else None,
                "ci_95_block_bootstrap": [num(ci[0]), num(ci[1])] if ci else None,
                "season_header_reference": (p.get("header_line") or {}).get(key),
                "ladder": line_ladder(vals),
                "usable_for_staking": False,
                "flag": f"n={len(vals)} is below any threshold worth staking on; the 95% "
                        "interval on the mean spans "
                        + (f"{num(ci[0],1)}–{num(ci[1],1)}" if ci else "unquantified")
                        + ", which is wider than the line itself",
            }
        # pairwise correlation between the stats a bettor would parlay in one game
        for i, a in enumerate(list(STATS)):
            for b in list(STATS)[i + 1:]:
                both = [(g[a], g[b]) for g in p["games"]
                        if g.get(a) is not None and g.get(b) is not None]
                if len(both) < 3:
                    continue
                xs, ys = [x for x, _ in both], [y for _, y in both]
                r = pearson(xs, ys)
                ci = fisher_ci(r, len(both))
                lo, hi = ci if ci else (None, None)
                pair_corr.append({
                    "player": p["player"], "team": p["team"],
                    "pair": f"{STATS[a]} × {STATS[b]}", "n": len(both),
                    "pearson_r": num(r, 3), "fisher_95": [num(lo, 3), num(hi, 3)],
                    "dates": [g["date"] for g in p["games"]
                              if g.get(a) is not None and g.get(b) is not None],
                    "source_url": p["player_page"],
                    "interpretation": "same-game co-movement inside 4–3 logged games; "
                                      "not a league correlation parameter",
                })
        players_out.append({
            "player": p["player"], "team": p["team"], "position": p["position"],
            "player_page": p["player_page"], "header_line": p.get("header_line"),
            "games_transcribed": len(p["games"]), "stats": per_stat,
        })

    # ---- SGP joint probability bounds for the one parlay the desk can price at all
    jokic = next((x for x in players_out if x["player"].startswith("Nikola")), None)
    sgp = []
    if jokic and jokic["stats"]["pts"]["n"] >= 3 and jokic["stats"]["reb"]["n"] >= 3:
        p_over = jokic["stats"]["pts"]["ladder"][3]["model_over_prob"]
        r_over = jokic["stats"]["reb"]["ladder"][3]["model_over_prob"]
        jb = joint_bounds(p_over, r_over)
        sgp.append({
            "legs": "Jokić points O + Jokić rebounds O",
            "p_a": p_over, "p_b": r_over,
            "independent": num(p_over * r_over, 4) if r_over else None,
            "frechet_lo": num(jb["lo"], 4), "frechet_hi": num(jb["hi"], 4),
            "measured_rho": next((c["pearson_r"] for c in pair_corr
                                  if c["player"].startswith("Nikola")
                                  and c["pair"].startswith("Points")), None),
            "note": "The Fréchet bounds are what is certain without a correlation estimate; "
                     "the measured ρ on 4 logged games is printed next to them to show how "
                     "far from settled it is.",
            "usable_for_staking": False,
        })

    out = {
        "title": "Player props — measured dispersion, and why it is not yet bettable",
        "sample": {
            "players": [p["player"] for p in players_out],
            "player_games": sum(len(p["games"]) for p in logs["players"]),
            "complete_rows": sum(1 for p in logs["players"] for g in p["games"]
                                 if not g["truncated"]),
            "captured_utc": logs["retrieved_utc"],
            "official_sources": [p["player_page"] for p in logs["players"]],
        },
        "irregularities_carried_from_capture": logs.get("irregularities", []),
        "players": players_out,
        "within_player_correlation": pair_corr,
        "sgp_bounds": sgp,
        "coverage_limit": {
            "statement": "3 of 30 rosters' worth of star players, 4 games each. No role "
                         "player, no teammate, no opponent-adjustment, no pace adjustment.",
            "what_it_blocks": "Any slate-wide prop table, any 'every upcoming game' prop "
                              "coverage, and any comparison against a market number.",
            "what_would_fix_it": "The full per-game log for each player of interest "
                                 "(player game-log pages are readable one player at a time "
                                 "from this sandbox), plus a prices feed for the market side.",
        },
        "verdict": "NOT USABLE FOR STAKING. Published so the number, its interval and its "
                   "gap are all visible rather than quietly rounded into a pick.",
    }
    dump("props.json", out)
    print(f"props · players={len(players_out)} pairs={len(pair_corr)} "
          f"sgp={len(sgp)} rows_usable_for_staking=0")
    return out


if __name__ == "__main__":
    main()
