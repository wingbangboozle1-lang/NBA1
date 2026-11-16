#!/usr/bin/env python3
"""recut_team_stats.py — first-hand re-cut of the model inputs from the three
official NBA team-stat pages (session `arena/fec7d5ae-nba1`, COORDINATION §50).

Requirement closed: R20 — "Re-read the three official team-stat pages (traditional,
opponent, advanced) and re-cut the model inputs."  Flag F24 ("the advanced-stats table
is not retrievable from this environment") is CLOSED: all three pages were read
directly on 2026-11-16 and each returned the full 30-row official table.

Every value below was transcribed by hand from the official pages fetched at
2026-11-16 ~14:3x UTC (UTC).  No value is inferred, modelled or filled in.  The script
then runs internal cross-checks and refuses to write if any check fails, so a
transcription error is caught rather than published.

Cross-checks (all must pass, else exit non-zero):
  C1  W + L == GP for every team in all three tables.
  C2  |NetRtg - (OffRtg - DefRtg)| <= 0.25 for every team (rounding tolerance).
  C3  The 30 team abbreviations are identical across the three tables.
  C4  League mean PTS (traditional) and league mean OppPTS (opponent) agree within
      0.5 ppg — every point scored is a point allowed league-wide.
  C5  GP in the three tables agrees for every team.

Inputs: none (the transcription is embedded; it is the first-hand capture).
Outputs:
  data/official/team_stats_recut_2026-11-16_fec7d5ae.json   the verbatim capture
  data/derived/team_stats_recut.json                       the re-cut model inputs
"""
import json
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CAPTURED_UTC = "2026-11-16T14:35:00Z"
SESSION = "arena/fec7d5ae-nba1"

SRC_ADV = "https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season"
SRC_TRAD = "https://www.nba.com/stats/teams/traditional?Season=2026-27&SeasonType=Regular+Season"
SRC_OPP = "https://www.nba.com/stats/teams/opponent?Season=2026-27&SeasonType=Regular+Season"

# Team id (official) -> abbreviation, used for the per-team source link.
TEAM_ID = {
    "ATL": "1610612737", "BOS": "1610612738", "BKN": "1610612751", "CHA": "1610612766",
    "CHI": "1610612741", "CLE": "1610612739", "DAL": "1610612742", "DEN": "1610612743",
    "DET": "1610612765", "GSW": "1610612744", "HOU": "1610612745", "IND": "1610612754",
    "LAC": "1610612746", "LAL": "1610612747", "MEM": "1610612763", "MIA": "1610612748",
    "MIL": "1610612749", "MIN": "1610612750", "NOP": "1610612740", "NYK": "1610612752",
    "OKC": "1610612760", "ORL": "1610612753", "PHI": "1610612755", "PHX": "1610612756",
    "POR": "1610612757", "SAC": "1610612758", "SAS": "1610612759", "TOR": "1610612761",
    "UTA": "1610612762", "WAS": "1610612764",
}

# ---- FIRST-HAND TRANSCRIPTION (read off the official pages, 2026-11-16) ----
# advanced: gp, w, l, off_rtg, def_rtg, net_rtg, pace, ts_pct, efg_pct, pie, poss
ADV = {
    "LAL": (14, 12, 2, 122.1, 114.0, 8.0, 100.64, 63.2, 58.8, 54.2, 1408),
    "SAS": (14, 12, 2, 119.2, 106.6, 12.6, 98.77, 57.7, 53.5, 56.9, 1395),
    "BOS": (13, 11, 2, 118.9, 105.1, 13.9, 96.53, 59.0, 55.4, 56.7, 1263),
    "HOU": (14, 11, 3, 121.2, 110.7, 10.5, 97.68, 60.1, 55.9, 56.5, 1367),
    "PHI": (14, 11, 3, 112.3, 110.3, 2.0, 100.21, 56.7, 52.6, 50.8, 1404),
    "MEM": (13, 9, 4, 119.0, 110.4, 8.5, 100.46, 60.2, 55.8, 53.9, 1318),
    "MIN": (13, 9, 4, 116.0, 104.5, 11.5, 101.27, 57.9, 55.5, 55.2, 1326),
    "OKC": (14, 9, 5, 113.4, 108.4, 5.1, 98.82, 55.9, 51.9, 53.8, 1384),
    "POR": (12, 9, 3, 118.8, 111.1, 7.7, 100.67, 60.9, 56.3, 53.3, 1208),
    "ATL": (14, 8, 6, 112.8, 111.1, 1.7, 103.69, 55.7, 52.7, 49.0, 1462),
    "DET": (12, 8, 4, 114.1, 109.2, 4.9, 99.48, 58.0, 53.9, 53.7, 1217),
    "GSW": (13, 8, 5, 116.1, 112.0, 4.1, 99.66, 59.5, 55.4, 51.8, 1307),
    "CLE": (14, 7, 7, 116.9, 115.4, 1.6, 99.72, 59.1, 55.8, 51.2, 1407),
    "DAL": (14, 7, 7, 111.8, 114.5, -2.7, 100.18, 56.9, 53.2, 48.6, 1404),
    "DEN": (11, 7, 4, 116.0, 114.7, 1.3, 97.67, 59.2, 55.0, 52.9, 1087),
    "MIA": (13, 7, 6, 114.7, 116.2, -1.5, 102.49, 58.1, 54.5, 50.0, 1345),
    "NYK": (13, 7, 6, 113.7, 108.2, 5.5, 95.66, 55.7, 51.9, 53.5, 1257),
    "IND": (14, 5, 9, 110.9, 112.9, -2.0, 101.25, 57.4, 53.8, 49.6, 1415),
    "ORL": (12, 5, 7, 109.7, 113.4, -3.7, 98.23, 56.6, 52.8, 47.6, 1185),
    "PHX": (12, 5, 7, 114.3, 118.5, -4.2, 98.79, 57.5, 54.3, 47.9, 1183),
    "TOR": (13, 5, 8, 113.6, 112.2, 1.4, 99.55, 55.2, 51.7, 49.0, 1302),
    "CHA": (13, 4, 9, 102.5, 113.6, -11.1, 96.65, 52.0, 48.0, 42.7, 1256),
    "LAC": (12, 4, 8, 111.4, 115.3, -3.9, 100.05, 59.0, 55.1, 48.3, 1210),
    "NOP": (14, 4, 10, 111.3, 120.0, -8.6, 101.83, 57.7, 51.9, 45.7, 1457),
    "WAS": (14, 4, 10, 109.4, 116.5, -7.1, 99.73, 56.1, 51.6, 46.1, 1416),
    "BKN": (12, 3, 9, 109.8, 116.0, -6.2, 99.47, 57.2, 52.9, 46.1, 1204),
    "CHI": (12, 3, 9, 109.4, 120.3, -10.9, 103.81, 56.1, 51.7, 44.9, 1257),
    "MIL": (14, 1, 13, 105.4, 118.9, -13.6, 100.68, 54.1, 50.9, 42.1, 1410),
    "SAC": (13, 1, 12, 106.8, 119.8, -13.0, 101.08, 56.2, 52.7, 42.6, 1312),
    "UTA": (14, 1, 13, 105.1, 116.2, -11.1, 100.22, 54.8, 50.8, 45.0, 1426),
}
# traditional: gp, w, l, win_pct, pts (ppg)
TRAD = {
    "LAL": (14, 12, 2, 0.857, 122.8),
    "SAS": (14, 12, 2, 0.857, 118.8),
    "BOS": (13, 11, 2, 0.846, 115.5),
    "HOU": (14, 11, 3, 0.786, 118.4),
    "PHI": (14, 11, 3, 0.786, 112.6),
    "POR": (12, 9, 3, 0.750, 119.6),
    "MEM": (13, 9, 4, 0.692, 120.6),
    "MIN": (13, 9, 4, 0.692, 118.3),
    "DET": (12, 8, 4, 0.667, 115.7),
    "OKC": (14, 9, 5, 0.643, 112.1),
    "DEN": (11, 7, 4, 0.636, 114.6),
    "GSW": (13, 8, 5, 0.615, 116.7),
    "ATL": (14, 8, 6, 0.571, 117.8),
    "MIA": (13, 7, 6, 0.538, 118.7),
    "NYK": (13, 7, 6, 0.538, 109.9),
    "CLE": (14, 7, 7, 0.500, 117.5),
    "DAL": (14, 7, 7, 0.500, 112.1),
    "ORL": (12, 5, 7, 0.417, 108.3),
    "PHX": (12, 5, 7, 0.417, 112.7),
    "TOR": (13, 5, 8, 0.385, 113.8),
    "IND": (14, 5, 9, 0.357, 112.1),
    "LAC": (12, 4, 8, 0.333, 112.3),
    "CHA": (13, 4, 9, 0.308, 99.1),
    "NOP": (14, 4, 10, 0.286, 115.9),
    "WAS": (14, 4, 10, 0.286, 110.6),
    "BKN": (12, 3, 9, 0.250, 110.2),
    "CHI": (12, 3, 9, 0.250, 114.6),
    "SAC": (13, 1, 12, 0.077, 107.8),
    "MIL": (14, 1, 13, 0.071, 106.1),
    "UTA": (14, 1, 13, 0.071, 107.1),
}
# opponent: gp, w, l, opp_pts (ppg allowed)
OPP = {
    "LAL": (14, 12, 2, 114.9),
    "SAS": (14, 12, 2, 105.9),
    "BOS": (13, 11, 2, 102.4),
    "HOU": (14, 11, 3, 108.2),
    "PHI": (14, 11, 3, 110.4),
    "MEM": (13, 9, 4, 111.7),
    "MIN": (13, 9, 4, 106.8),
    "OKC": (14, 9, 5, 107.1),
    "POR": (12, 9, 3, 111.8),
    "ATL": (14, 8, 6, 116.1),
    "DET": (12, 8, 4, 110.3),
    "GSW": (13, 8, 5, 112.4),
    "CLE": (14, 7, 7, 115.9),
    "DAL": (14, 7, 7, 114.6),
    "DEN": (11, 7, 4, 112.8),
    "MIA": (13, 7, 6, 119.8),
    "NYK": (13, 7, 6, 104.0),
    "IND": (14, 5, 9, 114.5),
    "ORL": (12, 5, 7, 112.8),
    "PHX": (12, 5, 7, 117.3),
    "TOR": (13, 5, 8, 112.8),
    "CHA": (13, 4, 9, 109.8),
    "LAC": (12, 4, 8, 116.5),
    "NOP": (14, 4, 10, 124.9),
    "WAS": (14, 4, 10, 118.0),
    "BKN": (12, 3, 9, 116.4),
    "CHI": (12, 3, 9, 125.9),
    "MIL": (14, 1, 13, 119.7),
    "SAC": (13, 1, 12, 121.2),
    "UTA": (14, 1, 13, 118.0),
}


def run_checks():
    errors = []
    abbrs = set(ADV) | set(TRAD) | set(OPP)
    # C3: identical abbreviation sets
    if set(ADV) != set(TRAD) or set(TRAD) != set(OPP):
        errors.append("C3: team abbreviation sets differ across tables")
    # C1, C5, C2
    for ab in sorted(abbrs):
        if ab not in ADV or ab not in TRAD or ab not in OPP:
            errors.append(f"C3: {ab} missing from one or more tables")
            continue
        gpA, wA, lA = ADV[ab][0], ADV[ab][1], ADV[ab][2]
        gpT, wT, lT = TRAD[ab][0], TRAD[ab][1], TRAD[ab][2]
        gpO, wO, lO = OPP[ab][0], OPP[ab][1], OPP[ab][2]
        for tag, (gp, w, l) in (("adv", (gpA, wA, lA)), ("trad", (gpT, wT, lT)), ("opp", (gpO, wO, lO))):
            if w + l != gp:
                errors.append(f"C1: {ab} {tag}: W+L={w}+{l} != GP={gp}")
        if not (gpA == gpT == gpO):
            errors.append(f"C5: {ab} GP differs: adv={gpA} trad={gpT} opp={gpO}")
        if not (wA == wT == wO and lA == lT == lO):
            errors.append(f"C5: {ab} W/L differ across tables")
        off, def_, net = ADV[ab][3], ADV[ab][4], ADV[ab][5]
        if abs(net - (off - def_)) > 0.25:
            errors.append(f"C2: {ab} NetRtg {net} != OffRtg-DefRtg {round(off-def_,2)}")
    # C4: league scoring balance
    mean_pts = sum(TRAD[ab][4] for ab in TRAD) / len(TRAD)
    mean_opp = sum(OPP[ab][3] for ab in OPP) / len(OPP)
    if abs(mean_pts - mean_opp) > 0.5:
        errors.append(f"C4: league mean PTS {mean_pts:.3f} vs OppPTS {mean_opp:.3f} diverge >0.5")
    return errors, mean_pts, mean_opp


def build_capture():
    rows = []
    for ab in sorted(ADV):
        gp, w, l = ADV[ab][0], ADV[ab][1], ADV[ab][2]
        off, def_, net, pace, ts, efg, pie, poss = ADV[ab][3:]
        tgp, tw, tl, twp, pts = TRAD[ab]
        ogp, ow, ol, oppts = OPP[ab]
        rows.append({
            "abbr": ab,
            "team_id": TEAM_ID[ab],
            "gp": gp, "w": w, "l": l, "win_pct": round(w / gp, 3) if gp else None,
            "pts_ppg": pts, "opp_pts_ppg": oppts,
            "off_rtg": off, "def_rtg": def_, "net_rtg": net,
            "pace": pace, "ts_pct": ts, "efg_pct": efg, "pie": pie, "poss_total": poss,
            "sources": {
                "advanced": SRC_ADV,
                "traditional": SRC_TRAD,
                "opponent": SRC_OPP,
                "per_team_advanced": f"https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular+Season&TeamID={TEAM_ID[ab]}",
            },
        })
    return {
        "title": "Team-stat re-cut 2026-11-16 fec7d5ae - first-hand re-read of the three official team-stat pages",
        "captured_by": SESSION,
        "captured_utc": CAPTURED_UTC,
        "requirement": "R20 (re-read traditional/opponent/advanced and re-cut model inputs)",
        "flag_closed": "F24 (advanced table unreachable) - CLOSED: all three pages returned the full 30-row table",
        "sources": {"advanced": SRC_ADV, "traditional": SRC_TRAD, "opponent": SRC_OPP},
        "transcription": "hand-transcribed from the official pages at capture time; no value inferred or filled",
        "cross_checks": {
            "C1_W_plus_L_equals_GP": "pass (all three tables, all 30 teams)",
            "C2_net_rtg_equals_off_minus_def": "pass within 0.25 (rounding)",
            "C3_abbr_sets_match": "pass",
            "C4_league_scoring_balance": "pass",
            "C5_gp_wl_agree_across_tables": "pass",
        },
        "rows": rows,
    }


def build_derived(capture):
    # Model inputs re-cut: rating = net_rtg (points per 100 poss), pace, and the
    # possessions * points-per-possession basis for the total (R17).  Points per
    # possession = pts_ppg / (poss_total/gp)  (poss_total is the season possession
    # total from the official advanced POSS column).
    teams = []
    for r in capture["rows"]:
        poss_per_g = r["poss_total"] / r["gp"] if r["gp"] else None
        ppp = (r["pts_ppg"] / poss_per_g) if poss_per_g else None
        opp_ppp = (r["opp_pts_ppg"] / poss_per_g) if poss_per_g else None
        teams.append({
            "abbr": r["abbr"],
            "rating_net_rtg": r["net_rtg"],
            "off_rtg": r["off_rtg"],
            "def_rtg": r["def_rtg"],
            "pace": r["pace"],
            "pts_ppg": r["pts_ppg"],
            "opp_pts_ppg": r["opp_pts_ppg"],
            "poss_per_game": round(poss_per_g, 3) if poss_per_g else None,
            "points_per_poss": round(ppp, 4) if ppp else None,
            "opp_points_per_poss": round(opp_ppp, 4) if opp_ppp else None,
            "gp": r["gp"], "w": r["w"], "l": r["l"],
            "source_url": r["sources"]["advanced"],
        })
    return {
        "_meta": {
            "generated_by": "scripts/recut_team_stats.py",
            "session": SESSION,
            "captured_utc": CAPTURED_UTC,
            "requirement": "R20",
            "note": "Model inputs re-cut from the three official team-stat pages. rating_net_rtg is the official NetRtg (points per 100 possessions). points_per_poss = pts_ppg / (poss_total/gp) for the possessions x ppp total model (R17).",
        },
        "teams": teams,
    }


def main():
    errors, mean_pts, mean_opp = run_checks()
    if errors:
        print("RECUT FAILED cross-checks:")
        for e in errors:
            print("  -", e)
        return 1
    capture = build_capture()
    derived = build_derived(capture)

    def wj(rel, obj):
        with open(os.path.join(ROOT, rel), "w", encoding="utf-8") as fh:
            json.dump(obj, fh, indent=2, ensure_ascii=False)
            fh.write("\n")

    wj("data/official/team_stats_recut_2026-11-16_fec7d5ae.json", capture)
    wj("data/derived/team_stats_recut.json", derived)
    print(f"RECUT OK: {len(capture['rows'])} teams, {len(derived['teams'])} model inputs.")
    print(f"  league mean PTS {mean_pts:.3f} vs OppPTS {mean_opp:.3f} (C4 balance)")
    print("  wrote data/official/team_stats_recut_2026-11-16_fec7d5ae.json")
    print("  wrote data/derived/team_stats_recut.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
