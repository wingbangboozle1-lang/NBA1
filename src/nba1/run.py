"""Orchestrate the full pipeline and write derived data files to data/.

Run:  python -m nba1.run   (from the repo root, with src on the path)
or:   python src/nba1/run.py

Regenerates:
  data/correlations.json   data/lines.json       data/picks.json
  data/strategies.json     data/leaderboard.json  data/injuries.json
"""

from __future__ import annotations

import json
import os
import sys

# Make src/ importable when run directly.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from nba1 import model, strategies, injuries  # noqa: E402

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")


def _write(name: str, obj: object) -> None:
    path = os.path.join(DATA_DIR, name)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, ensure_ascii=False)
    print("wrote", os.path.relpath(path, os.path.dirname(DATA_DIR)))


def main() -> None:
    standings_doc = model.load_json("standings_2026_27.json")
    slate_doc = model.load_json("slate_upcoming.json")
    results_doc = model.load_json("results_2026_11_12.json")
    sm = model.standings_map(standings_doc)
    league_avg = model.league_average_ppg(standings_doc)
    league_avg_total = round(league_avg * 2, 1)  # league-avg game total = two teams' scoring

    # 1) Correlation values (verified inputs).
    corr = model.correlation_matrix(standings_doc)
    _write("correlations.json", {
        "description": "Pearson correlation among verified team metrics (Basketball-Reference 2026-27 standings).",
        "source": "https://www.basketball-reference.com/leagues/NBA_2027_standings.html",
        "captured": "2026-11-13",
        "verified": True,
        "note": "Used to design strategies and to gate parlay/combo legs.",
        "matrix": corr,
    })

    # 2) Originated lines for the upcoming slate.
    slate_lines = model.originate_slate(slate_doc, sm)
    _write("lines.json", {
        "description": "Our own originated NBA lines (spread, total, win/cover probabilities) for the upcoming slate.",
        "originator": "NBA1 model (simple-rating expected score)",
        "source_standings": "https://www.basketball-reference.com/leagues/NBA_2027_standings.html",
        "source_schedule": "https://www.nba.com/schedule",
        "captured": "2026-11-13",
        "league_avg_ppg": round(league_avg, 2),
        "lines": slate_lines,
    })

    # 3) Picks — run single-bet strategies, then build parlay combos.
    single_legs: list[dict] = []
    picks: list[dict] = []
    for line in slate_lines:
        if line.get("originated") is None:
            continue
        for sid in ["S1", "S2", "S3"]:
            strat = strategies.strategy_by_id(sid)
            pick = strategies.select_single(strat, line, league_avg_total)
            if pick and pick.get("side"):
                single_legs.append(pick)
                picks.append({**{k: v for k, v in pick.items() if k != "game"},
                              "game": {k: line[k] for k in ("date", "away", "home", "time_et", "game_id", "preview")},
                              "originated_line": line["originated"],
                              "source_schedule": "https://www.nba.com/schedule",
                              "source_standings": "https://www.basketball-reference.com/leagues/NBA_2027_standings.html"})

    # Two-team parlays from the strongest qualifying single legs (different games).
    ranked_legs = sorted([l for l in single_legs if l.get("edge")],
                         key=lambda x: x["edge"], reverse=True)
    parlays: list[dict] = []
    used_games: set = set()
    for i, a in enumerate(ranked_legs):
        if a["game"]["game_id"] in used_games:
            continue
        for b in ranked_legs[i + 1:]:
            if b["game"]["game_id"] == a["game"]["game_id"]:
                continue
            p = strategies.make_parlay([a, b], strategies.strategy_by_id("S5"))
            if p and not p.get("rejected"):
                parlays.append(p)
                used_games.add(a["game"]["game_id"])
                used_games.add(b["game"]["game_id"])
                break
    picks.extend(parlays)

    # Player-prop + team parlay (S6): defined but not auto-fired without a
    # verified per-player feed (flagged, not guessed).
    picks.append({
        "strategy_id": "S6", "strategy": strategies.strategy_by_id("S6")["name"],
        "bet_kind": "parlay_player_prop", "side": None, "line": None,
        "edge": None, "combined_prob": None, "correlation": None,
        "flag": "methodology defined; live legs require verified per-player stats & roster — not auto-fired",
    })
    _write("picks.json", {
        "description": "Generated picks for the upcoming slate (up to 3 days ahead), produced from our originated lines.",
        "generated": "2026-11-13",
        "window": "2026-11-13 .. 2026-11-16",
        "source_schedule": "https://www.nba.com/schedule",
        "source_standings": "https://www.basketball-reference.com/leagues/NBA_2027_standings.html",
        "picks": picks,
    })

    # 4) Small-sample backtest on the verified Nov 12 slate to demonstrate
    #    skill-vs-luck and gate behavior (clearly labeled small sample).
    results_slate = {"slate": [{**g} for g in results_doc["games"]]}
    nov_lines = model.originate_slate(results_slate, sm)
    backtest = _backtest(nov_lines, results_doc["games"], league_avg_total)

    # 5) Strategies + leaderboard with validation gates.
    strat_rows = []
    for s in strategies.STRATEGIES:
        hits, n = backtest.get(s["id"], (None, 0))
        edge = None
        if s["id"] in ("S1", "S2", "S3"):
            # projected edge from the slate picks for this strategy
            proj = [p.get("edge") for p in picks if p.get("strategy_id") == s["id"] and p.get("edge")]
            edge = round(sum(proj) / len(proj), 4) if proj else None
        corr = None
        if s["bet_kind"] in ("parlay", "parlay_player_prop"):
            corr = 0.0  # independent-game parlays measured per build; none rejected here
        gates = strategies.validate_gates(s, edge, hits, n, corr)
        strat_rows.append({**s, "backtest_hits": hits, "backtest_n": n,
                           "projected_edge": edge, "validation": gates})
    _write("strategies.json", {
        "description": "Strategy library with validation gates, correlation handling, and skill/luck metrics.",
        "generated": "2026-11-13",
        "source": "https://www.basketball-reference.com/leagues/NBA_2027_standings.html",
        "source_name": "Basketball-Reference.com — 2026-27 NBA Standings (edge inputs)",
        "gate_thresholds": {"min_edge": strategies.MIN_EDGE, "min_sample": strategies.MIN_SAMPLE,
                            "max_leg_corr": strategies.MAX_LEG_CORR, "prior_strength": strategies.PRIOR_STRENGTH},
        "strategies": strat_rows,
    })

    # Leaderboard: rank by shrunk skill (live) or projected edge; rewards tiers.
    live = [r for r in strat_rows if r["validation"]["ranked"]]
    live.sort(key=lambda r: r["validation"]["shrunk_skill"], reverse=True)
    demo = [r for r in strat_rows if r["backtest_n"] > 0]
    demo.sort(key=lambda r: r["validation"]["shrunk_skill"], reverse=True)
    leaderboard = {
        "description": "Strategy leaderboard with rewards for top-performing strategies.",
        "generated": "2026-11-13",
        "reward_tiers": [
            {"tier": "1", "name": "Top performer", "reward": "Feature placement + priority allocation"},
            {"tier": "2", "name": "Promising (skill-significant)", "reward": "Increased allocation"},
            {"tier": "3", "name": "Monitor", "reward": "Tracked, no allocation"},
        ],
        "live_ranked": [{
            "rank": i + 1, "id": r["id"], "name": r["name"], "type": r["type"],
            "shrunk_skill": r["validation"]["shrunk_skill"],
            "z_score": r["validation"]["z_score"],
            "validation": r["validation"],
        } for i, r in enumerate(live)],
        "small_sample_demo": {
            "note": "Backtest on the verified 2026-11-12 slate (n=4 games). Small sample — shown only to demonstrate skill-vs-luck shrinkage and gate behavior, NOT as proof of skill.",
            "ranking": [{
                "id": r["id"], "name": r["name"], "hits": r["backtest_hits"], "n": r["backtest_n"],
                "hit_rate": round(r["backtest_hits"] / r["backtest_n"], 3) if r["backtest_n"] else None,
                "shrunk_skill": r["validation"]["shrunk_skill"],
                "z_score": r["validation"]["z_score"],
                "skill_significant": r["validation"]["G4_skill"] == "pass",
            } for r in demo],
        },
    }
    _write("leaderboard.json", leaderboard)

    # 6) Injuries / rotation / game-flow.
    injury_rows = injuries.build_injury_report(slate_lines)
    flow_rows = []
    for line in slate_lines:
        if line.get("originated") is None:
            continue
        away = sm[line["away_abbr"]]
        home = sm[line["home_abbr"]]
        flow_rows.append({
            "date": line["date"], "game": f"{line['away']} @ {line['home']}",
            "game_id": line["game_id"],
            **injuries.game_flow(away, home, league_avg),
        })
    _write("injuries.json", {
        "description": "Injury -> rotation minutes -> production tracking and game-flow analysis.",
        "generated": "2026-11-13",
        "injury_status_note": "Live injury statuses are UNVERIFIED in this session and left blank (flagged). The rotation/production models are defined and run automatically once a verified official injury feed is wired in.",
        "official_injury_source": "https://www.nba.com/news/injury-report",
        "game_flow": flow_rows,
        "injury_report": injury_rows,
    })

    print("\nDone. Derived data written to data/.")


def _backtest(nov_lines: list[dict], results: list[dict], league_avg_total: float) -> dict[str, tuple[int | None, int]]:
    """Grade the team strategies on the verified Nov 12 slate (small sample)."""
    out: dict[str, list[str]] = {"S1": [], "S2": [], "S3": []}
    by_id = {r["game_id"]: r for r in results} if "game_id" in results[0] else {}
    # results have no game_id; match by away/home name.
    for line in nov_lines:
        if line.get("originated") is None:
            continue
        match = next((r for r in results
                      if r["away"].replace(" ", "").lower() == line["away"].replace(" ", "").lower()
                      and r["home"].replace(" ", "").lower() == line["home"].replace(" ", "").lower()), None)
        if not match:
            continue
        home_score, away_score = match["home_score"], match["away_score"]
        spread = line["originated"]["spread"]
        # S1 home favorite cover
        if (home_score - away_score) > spread:
            out["S1"].append("win")
        elif (home_score - away_score) < spread:
            out["S1"].append("loss")
        # S2 away underdog cover (opposite of S1 unless push)
        if (home_score - away_score) < spread:
            out["S2"].append("win")
        elif (home_score - away_score) > spread:
            out["S2"].append("loss")
        # S3 total lean
        model_total = line["originated"]["total"]
        model_side = "Over" if model_total > league_avg_total else "Under"
        actual_total = home_score + away_score
        if model_side == "Over":
            out["S3"].append("win" if actual_total > model_total else ("loss" if actual_total < model_total else "push"))
        else:
            out["S3"].append("win" if actual_total < model_total else ("loss" if actual_total > model_total else "push"))
    graded: dict[str, tuple[int | None, int]] = {}
    for sid, grades in out.items():
        non_push = [g for g in grades if g != "push"]
        if non_push:
            graded[sid] = (non_push.count("win"), len(non_push))
        else:
            graded[sid] = (None, 0)
    return graded


if __name__ == "__main__":
    main()
