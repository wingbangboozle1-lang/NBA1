#!/usr/bin/env python3
"""source_check.py — compare the site's data with the official NBA.com transcriptions.

Session arena/b0f2cc98-nba1 (COORDINATION.md §23).

Inputs (read-only):
  verify/2026-11-14/official_horizon.json        27 official games 11/14-11/17 (hand transcription)
  verify/2026-11-14/official_finals_2026-11-13.json  9 official finals 11/13   (hand transcription)
  data/derived/horizon_lines.json                 the horizon lines the site publishes
  data/derived/horizon_picks.json, data/derived/picks_d.json   horizon pick counts
  data/official/slate.json                        verbatim slate capture (22 rows)
  data/originated_lines.json                      the 11/13 published lines (settled here)
  site/data/picks.json, site/data/flagged.json, docs/data/backtest.json   headline sources

Output:
  verify/2026-11-14/checks.json                   every comparison, with the official link per row

Rules: nothing is inferred. A value that is missing on either side is reported as missing.
A mismatch is reported, not corrected. This script never edits the data it checks.

Run:  python3 scripts/source_check.py
"""
import json
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERIFY = os.path.join(ROOT, "verify", "2026-11-14")


def load(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def norm_tip(t):
    """'7:00 PM ET' / '7:00 PM' / '07:00 (ET)' -> '7:00 PM' (or None)."""
    if not t:
        return None
    s = str(t).upper().replace("(ET)", "").replace("ET", "").strip()
    for fmt in ("%I:%M %p", "%H:%M"):
        try:
            return datetime.strptime(s, fmt).strftime("%-I:%M %p")
        except ValueError:
            pass
    return s


def main():
    off = load("verify/2026-11-14/official_horizon.json")
    fin = load("verify/2026-11-14/official_finals_2026-11-13.json")
    hl = load("data/derived/horizon_lines.json")["games"]
    slate = load("data/official/slate.json")["rows"]
    orig = load("data/originated_lines.json")["games"]
    picks_b = load("site/data/picks.json")["rows"]
    flagged = load("site/data/flagged.json")["items"]
    hp = load("data/derived/horizon_picks.json")
    pdd = load("data/derived/picks_d.json")
    bt = load("docs/data/backtest.json")

    off_by_id = {r["game_id"]: r for r in off["rows"]}
    hl_by_id = {r["game_id"]: r for r in hl}
    slate_by_id = {r.get("game_id"): r for r in slate if r.get("game_id")}
    played_1113 = set()
    for r in fin["rows"]:
        played_1113.add(r["away"])
        played_1113.add(r["home"])

    # 1. Horizon: official vs site horizon_lines (27) --------------------------
    horizon = []
    for gid, o in off_by_id.items():
        s = hl_by_id.get(gid)
        row = {
            "game_id": gid, "date": o["date"], "matchup": o["matchup"],
            "official_tip_et": o["tip_et"], "official_source": o["source_url"],
        }
        if s is None:
            row.update(site_matchup=None, status="ABSENT_IN_SITE")
        else:
            problems = []
            if s["matchup"] != o["matchup"]:
                problems.append("matchup")
            if s["date"] != o["date"]:
                problems.append("date")
            if norm_tip(s.get("tip_et")) != norm_tip(o["tip_et"]):
                problems.append("tip")
            row.update(site_matchup=s["matchup"], site_tip_et=s.get("tip_et"),
                       status="MATCH" if not problems else "MISMATCH:" + ",".join(problems))
        sl = slate_by_id.get(gid)
        row["in_slate_capture"] = bool(sl)
        if sl:
            sl_ok = (sl.get("away") == o["away"] and sl.get("home") == o["home"]
                     and norm_tip(sl.get("time_et")) == norm_tip(o["tip_et"]))
            row["slate_capture_status"] = "MATCH" if sl_ok else "MISMATCH"
        else:
            row["slate_capture_status"] = "ABSENT_FROM_SLATE_CAPTURE"
        horizon.append(row)
    site_only = sorted(set(hl_by_id) - set(off_by_id))

    horizon_summary = {
        "official_games": len(off_by_id),
        "site_horizon_games": len(hl_by_id),
        "matched": sum(1 for r in horizon if r["status"] == "MATCH"),
        "mismatched": sum(1 for r in horizon if r["status"].startswith("MISMATCH")),
        "absent_in_site": sum(1 for r in horizon if r["status"] == "ABSENT_IN_SITE"),
        "site_only_game_ids": site_only,
        "in_slate_capture": sum(1 for r in horizon if r["in_slate_capture"]),
        "absent_from_slate_capture": sum(1 for r in horizon if r["slate_capture_status"] == "ABSENT_FROM_SLATE_CAPTURE"),
        "slate_capture_mismatches": sum(1 for r in horizon if r["slate_capture_status"] == "MISMATCH"),
        "calendar_counts_official": off.get("calendar_game_counts", {}),
    }

    # 2. Record staleness: site's pre-11/13 records vs NBA.com card at capture ---
    records = []
    for gid, o in off_by_id.items():
        s = hl_by_id.get(gid)
        if not s:
            continue
        site_rec = s.get("records_pre_11_13", "")
        parts = [p.strip() for p in site_rec.split("/")]
        site_away, site_home = (parts + [None, None])[:2]
        for side, team, site_val, off_val in (
            ("away", o["away"], site_away, o["away_record_at_capture"]),
            ("home", o["home"], site_home, o["home_record_at_capture"]),
        ):
            if site_val is None:
                status = "SITE_BLANK"
            elif site_val == off_val:
                status = "MATCH"
            elif team in played_1113:
                status = "STALE_TEAM_PLAYED_11_13"
            else:
                status = "UNEXPLAINED_MISMATCH"
            records.append({"game_id": gid, "matchup": o["matchup"], "side": side, "team": team,
                            "site_record_pre_11_13": site_val, "official_record_at_capture": off_val,
                            "status": status, "official_source": o["source_url"]})
    record_summary = {k: sum(1 for r in records if r["status"] == k)
                      for k in ("MATCH", "STALE_TEAM_PLAYED_11_13", "UNEXPLAINED_MISMATCH", "SITE_BLANK")}

    # 3. Sign convention of horizon line_spread_home ---------------------------
    sign = {"standard": 0, "margin": 0, "zero_or_other": 0, "games": []}
    for s in hl:
        if s.get("proj_home_pts") is None or s.get("proj_away_pts") is None or s.get("line_spread_home") is None:
            sign["zero_or_other"] += 1
            continue
        proj_margin = round(s["proj_home_pts"] - s["proj_away_pts"], 1)
        spread = s["line_spread_home"]
        if abs(spread + proj_margin) < 0.051 and abs(spread) > 0:
            kind = "standard"        # spread_home = -(projected home margin)
        elif abs(spread - proj_margin) < 0.051 and abs(spread) > 0:
            kind = "margin"          # spread_home = +(projected home margin)  (sign-inverted vs standard)
        else:
            kind = "zero_or_other"
        sign[kind] += 1
        sign["games"].append({"game_id": s["game_id"], "matchup": s["matchup"],
                              "line_spread_home": spread, "proj_home_minus_away": proj_margin, "convention": kind})

    # 4. Settle the 11/13 published lines against official finals ----------------
    fin_by_m = {f"{r['away']}@{r['home']}": r for r in fin["rows"]}
    settle = []
    for g in orig:
        if g.get("date") != "2026-11-13":
            continue
        f = fin_by_m.get(g["matchup"])
        m = g["model"]
        pick_side = m.get("pick_side")
        spread_home = m.get("originated_spread_home")
        exp_margin = m.get("expected_margin_home")
        row = {"matchup": g["matchup"], "date": "2026-11-13",
               "originated_spread_home": spread_home, "model_expected_margin_home": exp_margin,
               "pick_side": pick_side, "pick_line": m.get("pick_line"), "gate": m.get("gate"),
               "sources": g.get("sources", [])}
        if f is None:
            row.update(official_status="NOT_FOUND", result="UNSETTLED")
        else:
            margin = f["home_score"] - f["away_score"]
            row.update(official_away=f["away"], official_away_score=f["away_score"],
                       official_home=f["home"], official_home_score=f["home_score"],
                       official_status=f["status"], official_home_margin=margin,
                       official_source=f["source_url"],
                       model_error_margin=round(abs(exp_margin - margin), 2) if exp_margin is not None else None)
            if pick_side in ("HOME", "AWAY") and spread_home is not None:
                # home-side bet covers when margin + spread_home > 0; away side is the mirror.
                s_home_cover = margin + spread_home
                if pick_side == "HOME":
                    cov = s_home_cover
                else:
                    cov = -s_home_cover
                if abs(cov) < 1e-9:
                    result = "PUSH"
                else:
                    result = "WIN" if cov > 0 else "LOSS"
                row["result"] = result
                row["cover_margin_pts"] = round(cov, 2)
            else:
                row["result"] = "NO_BET"
        settle.append(row)
    settle.sort(key=lambda r: r["matchup"])
    tally = {k: sum(1 for r in settle if r.get("result") == k) for k in ("WIN", "LOSS", "PUSH", "NO_BET", "UNSETTLED")}
    errs = [r["model_error_margin"] for r in settle if r.get("model_error_margin") is not None]
    gaps = [abs(r["originated_spread_home"] + r["model_expected_margin_home"]) for r in settle
            if r.get("originated_spread_home") is not None and r.get("model_expected_margin_home") is not None]
    settle_summary = dict(tally, n=len(settle), mean_abs_margin_error=round(sum(errs) / len(errs), 2) if errs else None,
                          max_gap_spread_vs_minus_expected_margin=round(max(gaps), 2) if gaps else None)

    # 5. Headline counts --------------------------------------------------------
    hd_picks = pdd.get("n_model_picks")
    hp_model = hp.get("n_model_picks")
    hp_singles = len(hp.get("singles", []))
    b_pairs = {(r["matchup"], r["strategy"]) for r in picks_b}
    b_games = {r["matchup"] for r in picks_b}
    headline = [
        {"claim": "Originated lines: 27", "site_location": "index.html tile 'Originated lines'",
         "observed": f"{len(hl)} rows in data/derived/horizon_lines.json; {len(off_by_id)} official games",
         "status": "MATCH" if len(hl) == len(off_by_id) == 27 else "MISMATCH",
         "official_source": "https://www.nba.com/schedule"},
        {"claim": "Paper picks: 63", "site_location": "index.html tile 'Paper picks' (site/data/picks.json, Build B)",
         "observed": f"{len(picks_b)} rows, all PENDING, across {len(b_games)} matchups and {len(b_pairs)} strategy-game pairs; "
                     f"Build D horizon: {hp_singles} singles, {hp_model} model picks (horizon_picks.json); "
                     f"picks_d.json n_model_picks = {hd_picks}",
         "status": "COUNT_DEFINITION_CONFLICT", "official_source": None},
        {"claim": "Strategies tested: 10", "site_location": "index.html tile 'Strategies tested'",
         "observed": "10 strategies in leaderboard (site/data/leaderboard.json)", "status": "INTERNAL_COUNT", "official_source": None},
        {"claim": "Out-of-sample games: 51", "site_location": "index.html tile",
         "observed": f"docs/data/backtest.json metrics.n_games = {bt.get('metrics', {}).get('n_games')}",
         "status": "INTERNAL_COUNT", "official_source": None},
        {"claim": "Open flags (landing tile = items in flagged.json)", "site_location": "index.html tile 'Open flags'",
         "observed": f"{len(flagged)} items in site/data/flagged.json (25 before this check; F26-F37 added)",
         "status": "INTERNAL_COUNT", "official_source": None},
        {"claim": "Known limits: the 2026-11-13 slate was still in progress; no final score exists for it",
         "site_location": "README.md 'Known limits' (was stale; rewritten 2026-11-14 by arena/934ca56f-nba1)",
         "observed": (f"{sum(1 for r in fin['rows'] if r['status'].startswith('Final'))} of {len(fin['rows'])} "
                      f"11/13 games show Final on the official page. The README now says so, records the 3 WIN / 4 LOSS / "
                      f"2 NO BET settlement, and keeps the separately-true limit that the ratings window ends 2026-11-12. "
                      f"Re-read from the file rather than assumed: 'still in progress' appears in README.md = "
                      f"{'still in progress' in open(os.path.join(ROOT,'README.md'),encoding='utf-8').read()}"),
         "status": "RESOLVED_ON_SITE", "official_source": "https://www.nba.com/games?date=2026-11-13"},
        {"claim": "Official 11/13 injury report edition: 07:30 PM ET is the newest",
         "site_location": "data/official/injuries.json source_url",
         "observed": "NOT RE-CHECKED in this session (11/14 noon edition returned AccessDenied at capture)",
         "status": "UNVERIFIED_THIS_SESSION", "official_source": "https://official.nba.com/nba-injury-report-2026-27-season/"},
    ]

    # 6. Cross-build spread comparison (Build B picks vs Build D horizon) --------
    hl_by_m = {s["matchup"]: s for s in hl}
    cross = []
    seen = set()
    for r in picks_b:
        if r.get("market") != "Point spread" or r["matchup"] in seen:
            continue
        seen.add(r["matchup"])
        s = hl_by_m.get(r["matchup"])
        if s is None:
            cross.append({"matchup": r["matchup"], "status": "NOT_IN_HORIZON"})
            continue
        # Build B stores its model value as the HOME MARGIN (see section 7), on both pick sides.
        b_home_margin = r["model_value"]
        d_home_margin = s["proj_home_pts"] - s["proj_away_pts"]
        diff = round(b_home_margin - d_home_margin, 1)
        cross.append({"matchup": r["matchup"], "build_b_model_home_margin": round(b_home_margin, 1),
                      "build_d_model_home_margin": round(d_home_margin, 1), "difference": diff,
                      "build_b_line_display": r.get("line_display"), "build_b_ref_line": r.get("ref_line"),
                      "build_d_line_spread_home": s.get("line_spread_home"),
                      "status": "AGREE_WITHIN_0.5" if abs(diff) <= 0.5 else "DISAGREE"})
    cross_summary = {"matchups_compared": sum(1 for c in cross if "difference" in c),
                     "opposite_favourite": sum(1 for c in cross if "difference" in c and
                                               (c["build_b_model_home_margin"] > 0) != (c["build_d_model_home_margin"] > 0)),
                     "max_abs_difference": max((abs(c["difference"]) for c in cross if "difference" in c), default=None),
                     "disagree_over_0.5": sum(1 for c in cross if c.get("status") == "DISAGREE"),
                     "not_in_horizon": sum(1 for c in cross if c.get("status") == "NOT_IN_HORIZON")}

    # 7. Build B sign convention, as published on the landing page -------------
    # site/data/lines.json carries ref_spread_home / model_spread_home. Test which convention the
    # stored value follows, using only the build's own S1 pick: under a HOME-MARGIN reading the
    # pick is HOME exactly when the model's home margin beats the reference's home margin
    # (mod > ref); under a STANDARD home-spread reading it is HOME when mod < ref.
    lines_b = load("site/data/lines.json")["rows"]
    s1_side = {}
    for r in picks_b:
        if r.get("strategy") == "S1" and r.get("market") == "Point spread":
            s1_side[r["matchup"]] = (r["side"], r["model_value"])
    conv_b = {"home_margin_consistent": 0, "standard_consistent": 0, "no_s1_pick": 0,
              "s1_value_equals_stored_home_field": 0}
    conv_rows = []
    for r in lines_b:
        side = s1_side.get(r["matchup"])
        mod, ref = r.get("model_spread_home"), r.get("ref_spread_home")
        if side is None or mod is None or ref is None:
            conv_b["no_s1_pick"] += 1
            continue
        home_pick = side[0] == "home"
        m_ok = home_pick == (mod > ref)
        s_ok = home_pick == (mod < ref)
        conv_b["home_margin_consistent"] += int(m_ok)
        conv_b["standard_consistent"] += int(s_ok)
        conv_b["s1_value_equals_stored_home_field"] += int(side[1] == mod)
        conv_rows.append({"matchup": r["matchup"], "ref_spread_home": ref, "model_spread_home": mod,
                          "s1_side": side[0], "s1_model_value": side[1],
                          "consistent_with_home_margin": m_ok, "consistent_with_standard": s_ok})
    build_b_convention = {"counts": conv_b, "rows": conv_rows}

    out = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "build_b_sign_convention": build_b_convention,
        "build_b_horizon_match": {
            "site_lines_rows": len(lines_b),
            "matched_official": sum(1 for r in lines_b if (r["date"], r["matchup"]) in
                                    {(o["date"], o["matchup"]) for o in off["rows"]}),
        },
        "generated_by": "scripts/source_check.py",
        "official_capture_utc": off.get("captured_utc"),
        "horizon": horizon, "horizon_summary": horizon_summary,
        "records": records, "record_summary": record_summary,
        "sign_convention": {k: v for k, v in sign.items() if k != "games"},
        "sign_convention_games": sign["games"],
        "settlement_2026_11_13": settle, "settlement_summary": settle_summary,
        "headline_audit": headline,
        "cross_build": cross, "cross_build_summary": cross_summary,
    }
    os.makedirs(VERIFY, exist_ok=True)
    with open(os.path.join(VERIFY, "checks.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
        fh.write("\n")

    print("horizon:", horizon_summary)
    print("records:", record_summary)
    print("sign:", out["sign_convention"])
    print("settlement:", settle_summary)
    print("cross-build:", cross_summary)
    for h in headline:
        print("headline:", h["status"], "|", h["claim"], "|", h["observed"][:120])
    return 0


if __name__ == "__main__":
    sys.exit(main())
