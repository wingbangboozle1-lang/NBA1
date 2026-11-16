#!/usr/bin/env python3
"""S02 (session arena/3ff8ff0f-nba1, COORDINATION 56.1).

First-hand transcription of the official NBA.com standings table, read 2026-11-16
at ~18:2x UTC with the repo's fetch channel (fetch_page on https://www.nba.com/standings,
"Group By: Conference", "Section: Overall").  Every cell below is copied from the printed
table; nothing is inferred.  The file re-derives the measured home-win rate that
requirement R09 pins home-court advantage to, and it is asserted against the league's own
internal identities before it is written:

  * per team:  home_w + road_w + neutral_w == w   (and the same for losses)
  * per team:  round(w / (w + l), 3) == the printed WIN%
  * league:    home_wins == road_losses  and  road_wins == home_losses
  * league:    (home_games + road_games) / 2 + neutral_team_games / 2 == total games,
               which must equal (sum of all wins) as printed on the page

Anything that fails stops the write.
"""
import json
import os
import urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "official",
                   "standings_2026-11-16_1825Z_3ff8ff0f.json")
SOURCE_URL = "https://www.nba.com/standings"
PRIOR = os.path.join(ROOT, "data", "official",
                     "standings_2026-11-16_0213Z_dfef26dc.json")

# conference, rank, abbr, w, l, win_pct, gb, conf, div, home, road, neutral, ot, last10, streak
ROWS = [
    ("East", 1, "BOS", 11, 2, ".846", "--", "10-1", "4-0", "6-0", "5-2", "0-0", "1-0", "9-1", "W 6"),
    ("East", 2, "PHI", 11, 3, ".786", "0.5", "11-3", "3-1", "6-2", "5-1", "0-0", "0-0", "8-2", "W 2"),
    ("East", 3, "DET", 8, 4, ".667", "2.5", "8-3", "0-0", "3-2", "5-2", "0-0", "1-0", "6-4", "L 1"),
    ("East", 4, "ATL", 8, 6, ".571", "3.5", "8-2", "4-1", "3-3", "5-3", "0-0", "0-1", "6-4", "W 1"),
    ("East", 5, "MIA", 7, 6, ".538", "4", "4-2", "1-1", "3-3", "4-3", "0-0", "1-0", "7-3", "W 4"),
    ("East", 6, "NYK", 7, 6, ".538", "4", "7-6", "2-3", "4-3", "3-3", "0-0", "1-0", "7-3", "W 1"),
    ("East", 7, "CLE", 7, 7, ".500", "4.5", "5-5", "1-0", "5-2", "2-5", "0-0", "1-0", "4-6", "W 1"),
    ("East", 8, "ORL", 5, 7, ".417", "5.5", "3-4", "0-2", "1-4", "4-3", "0-0", "0-1", "5-5", "W 3"),
    ("East", 9, "TOR", 5, 8, ".385", "6", "4-4", "0-3", "2-4", "3-4", "0-0", "0-1", "3-7", "L 4"),
    ("East", 10, "IND", 5, 9, ".357", "6.5", "3-6", "0-1", "2-4", "3-4", "0-1", "0-0", "3-7", "L 1"),
    ("East", 11, "CHA", 4, 9, ".308", "7", "4-7", "2-2", "3-4", "1-5", "0-0", "0-0", "2-8", "L 2"),
    ("East", 12, "WAS", 4, 10, ".286", "7.5", "4-8", "2-3", "2-4", "2-6", "0-0", "0-1", "2-8", "L 7"),
    ("East", 13, "BKN", 3, 9, ".250", "7.5", "2-7", "0-2", "1-3", "2-6", "0-0", "0-1", "3-7", "L 1"),
    ("East", 14, "CHI", 3, 9, ".250", "7.5", "2-8", "1-0", "1-4", "2-5", "0-0", "1-0", "2-8", "W 2"),
    ("East", 15, "MIL", 1, 13, ".071", "10.5", "1-10", "1-2", "1-7", "0-6", "0-0", "0-0", "0-10", "L 10"),
    ("West", 1, "SAS", 12, 2, ".857", "--", "11-2", "2-1", "5-2", "7-0", "0-0", "1-0", "10-0", "W 12"),
    ("West", 2, "LAL", 12, 2, ".857", "--", "7-2", "5-1", "5-1", "7-1", "0-0", "0-0", "9-1", "W 8"),
    ("West", 3, "HOU", 11, 3, ".786", "1", "6-3", "2-1", "7-1", "4-2", "0-0", "0-0", "7-3", "W 4"),
    ("West", 4, "POR", 9, 3, ".750", "2", "9-3", "4-0", "3-2", "6-1", "0-0", "0-0", "7-3", "W 3"),
    ("West", 5, "MIN", 9, 4, ".692", "2.5", "5-2", "1-0", "5-2", "4-2", "0-0", "0-1", "6-4", "L 1"),
    ("West", 6, "MEM", 9, 4, ".692", "2.5", "7-3", "1-1", "3-4", "6-0", "0-0", "0-1", "6-4", "W 2"),
    ("West", 7, "OKC", 9, 5, ".643", "3", "6-5", "1-2", "5-0", "4-5", "0-0", "0-0", "5-5", "W 1"),
    ("West", 8, "DEN", 7, 4, ".636", "3.5", "5-4", "0-2", "2-2", "4-2", "1-0", "1-0", "7-3", "W 2"),
    ("West", 9, "GSW", 8, 5, ".615", "3.5", "6-5", "3-2", "6-1", "2-4", "0-0", "1-0", "8-2", "L 2"),
    ("West", 10, "DAL", 7, 7, ".500", "5", "3-5", "1-3", "5-2", "2-5", "0-0", "0-0", "5-5", "L 3"),
    ("West", 11, "PHX", 5, 7, ".417", "6", "3-7", "2-2", "5-4", "0-3", "0-0", "0-0", "4-6", "L 1"),
    ("West", 12, "LAC", 4, 8, ".333", "7", "3-6", "1-4", "4-3", "0-5", "0-0", "0-1", "3-7", "W 2"),
    ("West", 13, "NOP", 4, 10, ".286", "8", "3-8", "1-1", "3-6", "1-4", "0-0", "2-1", "4-6", "L 6"),
    ("West", 14, "SAC", 1, 12, ".077", "10.5", "1-10", "0-2", "0-8", "1-4", "0-0", "0-0", "1-9", "L 6"),
    ("West", 15, "UTA", 1, 13, ".071", "11", "1-11", "0-2", "1-7", "0-6", "0-0", "0-2", "0-10", "L 12"),
]


def rec(s):
    w, l = s.split("-")
    return int(w), int(l)


def main():
    rows, hw, hg, rw, rg, nw, nl = [], 0, 0, 0, 0, 0, 0
    for (conf, rank, abbr, w, l, pct, gb, conf_rec, div_rec, home, road, neutral,
         ot, last10, streak) in ROWS:
        h_w, h_l = rec(home)
        r_w, r_l = rec(road)
        n_w, n_l = rec(neutral)
        assert h_w + r_w + n_w == w, f"{abbr}: splits {h_w}+{r_w}+{n_w} != w {w}"
        assert h_l + r_l + n_l == l, f"{abbr}: splits {h_l}+{r_l}+{n_l} != l {l}"
        assert ".%03d" % round(1000 * w / (w + l)) == pct, \
            f"{abbr}: computed {w}/{w+l} does not print {pct}"
        hw += h_w; hg += h_w + h_l
        rw += r_w; rg += r_w + r_l
        nw += n_w; nl += n_l
        rows.append({"conference": conf, "rank": rank, "abbr": abbr, "w": w, "l": l,
                     "win_pct": pct, "gb": gb, "conf_rec": conf_rec, "div_rec": div_rec,
                     "home": home, "road": road, "neutral": neutral, "ot": ot,
                     "last10": last10, "streak": streak})
    assert len(rows) == 30 and (hg + rg) % 2 == 0
    games_from_wl = sum(r["w"] for r in rows)
    games_from_splits = (hg + rg) // 2 + (nw + nl) // 2
    assert hw == rg - rw, f"home wins {hw} != road losses {rg - rw}"
    assert rw == hg - hw, f"road wins {rw} != home losses {hg - hw}"
    assert games_from_wl == games_from_splits, \
        f"games from W-L {games_from_wl} != games from splits {games_from_splits}"
    rate = round(hw / hg, 4)

    doc = {
        "title": "NBA 2026-27 regular-season standings, read 2026-11-16T18:25Z",
        "captured_by": "arena/3ff8ff0f-nba1",
        "retrieved_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_url": SOURCE_URL,
        "read_method": ("the official standings table as rendered by nba.com, read "
                        "first-hand in this session (Group By: Conference, Section: "
                        "Overall). Every cell transcribed as printed; the league's own "
                        "splits identities asserted before the file was written."),
        "season": "2026-27",
        "rows": rows,
        "measured_home_win_rate": {
            "home_wins": hw, "home_losses": hg - hw, "home_games": hg,
            "road_wins": rw, "road_losses": rg - rw, "road_games": rg,
            "neutral_wins": nw, "neutral_losses": nl, "neutral_team_games": nw + nl,
            "home_win_rate": rate,
            "games_played_league_wide": games_from_wl,
            "cross_check": f"home_wins({hw}) must equal road_losses({rg - rw}): OK",
            "cross_check_2": f"road_wins({rw}) must equal home_losses({hg - hw}): OK",
            "cross_check_3": (f"sum of printed wins ({games_from_wl}) must equal games "
                              f"implied by the HOME/ROAD/NEUTRAL splits "
                              f"({games_from_splits}): OK"),
            "use": ("this is the measured home-win rate the model pins home-court "
                    "advantage to (R09: pin HCA to the measured home-win rate, do not "
                    "fit it freely)"),
            "caveat": ("the standings reflect every game the league has scored FINAL at "
                       "read time; games tipped after this read are not in it. 11/16's "
                       "eight games had not started at read time (13:2x ET)."),
        },
        "measured_home_court_anchor": {
            "home_win_rate": rate,
            "road_win_rate": round(rw / rg, 4),
            "home_wins": hw, "home_games": hg,
            "home_losses": hg - hw,
            "road_wins": rw, "road_games": rg,
            "road_losses": rg - rw,
            "neutral_team_games": nw + nl,
            "games_played": games_from_wl,
            "measured_from": "the official standings HOME and ROAD columns, summed across all 30 teams",
            "cross_checks": [f"home_wins({hw}) must equal road_losses({rg - rw}): OK",
                             f"road_wins({rw}) must equal home_losses({hg - hw}): OK"],
            "source_url": SOURCE_URL,
            "retrieved_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
            "supersedes": os.path.basename(PRIOR),
        },
    }

    # diff against the capture this supersedes - the board's diff discipline
    if os.path.exists(PRIOR):
        prior = json.load(open(PRIOR, encoding="utf-8"))
        pa = prior["measured_home_court_anchor"]
        by_prev = {r["abbr"]: r for r in prior["rows"]}
        changed = []
        for r in rows:
            pr = by_prev.get(r["abbr"])
            if not pr:
                changed.append({"abbr": r["abbr"], "note": "not in the prior capture"})
                continue
            d = {k: [pr[k], r[k]] for k in ("w", "l", "home", "road", "neutral", "ot",
                                            "conf_rec", "div_rec", "last10", "streak")
                 if pr[k] != r[k]}
            if d:
                changed.append({"abbr": r["abbr"], "fields": d})
        doc["delta_vs_prior_capture"] = {
            "prior_file": os.path.basename(PRIOR),
            "prior_home_win_rate": pa["home_win_rate"],
            "prior_home_games": pa["home_games"], "prior_home_wins": pa["home_wins"],
            "prior_games_played": sum(r["w"] for r in prior["rows"]),
            "new_home_win_rate": rate, "new_home_games": hg, "new_home_wins": hw,
            "games_added": games_from_wl - sum(r["w"] for r in prior["rows"]),
            "home_wins_added": hw - pa["home_wins"],
            "rows_changed": len(changed),
            "detail": changed,
        }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1)
    print("wrote", os.path.relpath(OUT, ROOT))
    print(f"home-win rate {hw}/{hg} = {rate}  (games played {games_from_wl}, "
          f"neutral team-games {nw + nl})")
    if "delta_vs_prior_capture" in doc:
        print("delta:", json.dumps({k: v for k, v in
                                    doc["delta_vs_prior_capture"].items() if k != "detail"}))


if __name__ == "__main__":
    main()
