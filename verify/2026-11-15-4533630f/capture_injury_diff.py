#!/usr/bin/env python3
"""capture_injury_diff.py — a REAL consecutive-edition status diff.

Both editions were read on the official PDF host in this pass:
  06:15 AM ET  https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15AM.pdf
  06:15 PM ET  https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15PM.pdf

SCOPE LIMIT, stated because it matters: each PDF is paginated and the reader returns it in
chunks. This diff covers the rows printed in the FIRST chunk of each edition (the IND@PHI,
LAL@PHX, CHA@LAC, SAS@UTA, DAL@BOS, NYK@TOR, HOU@WAS and ATL@MIL blocks). Rows that only appear
in later chunks are NOT compared and are not claimed to be unchanged.

Everything below is a pair of `Current Status` cells copied from the two PDFs. No status is
inferred, and a player absent from an edition is recorded as absent - not as "Out".
"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
H = "https://ak-static.cms.nba.com/referee/injury/"
AM = H + "Injury-Report_2026-11-15_06_15AM.pdf"
PM = H + "Injury-Report_2026-11-15_06_15PM.pdf"

# (matchup, team, player_as_printed, status_0615AM, status_0615PM, note)
CHANGES = [
    ("IND@PHI", "Indianapolis Pacers (IND)", "McConnell, T.J.", "Probable", "Available", ""),
    ("IND@PHI", "Indianapolis Pacers (IND)", "Nembhard, Andrew", "Questionable", "Out",
     "downgraded to Out on game day"),
    ("IND@PHI", "Indianapolis Pacers (IND)", "Nesmith, Aaron", "Questionable", "Available", ""),
    ("IND@PHI", "Philadelphia 76ers (PHI)", "Embid, Joel", "Out", "Out",
     "printed 'Embid' in the 06:15 AM edition, corrected to 'Embiid' in the 06:15 PM edition - "
     "a name-keyed diff would treat these as two different players"),
    ("LAL@PHX", "Los Angeles Lakers (LAL)", "James, Bronny", "Questionable", "Available", ""),
    ("LAL@PHX", "Phoenix Suns (PHX)", "Sexton, Collin", "Questionable", "Available", ""),
    ("LAL@PHX", "Phoenix Suns (PHX)", "Thiero, Adou", "Questionable", "Available", ""),
    ("LAL@PHX", "Phoenix Suns (PHX)", "Timme, Drew", "(absent)", "Out", "row added"),
    ("CHA@LAC", "LA Clippers (LAC)", "Martinelli, Nick", "(absent)", "Out", "row added"),
    ("SAS@UTA", "San Antonio Spurs (SAS)", "Fox, De'Aaron", "(absent)", "Out",
     "row added on game day - a starter-scale absence invisible to the 06:15 AM read"),
    ("DAL@BOS", "Dallas Mavericks (DAL)", "(entire team block)", "NOT YET SUBMITTED",
     "8 players submitted", "Aldama, Biberovic, Christie, de Larrea, Gafford (Available), "
     "Irving (Out), Lively II, Martin (Available) - the model's edition contained NO Dallas "
     "participation data at all"),
    ("DAL@BOS", "Boston Celtics (BOS)", "Carter, Devin", "Questionable", "Available", ""),
    ("DAL@BOS", "Boston Celtics (BOS)", "Cenac Jr., Christopher", "Questionable", "Available", ""),
    ("NYK@TOR", "Toronto Raptors (TOR)", "Barnes, Scottie", "Questionable", "Available", ""),
    ("HOU@WAS", "Houston Rockets (HOU)", "Adams, Steven", "Probable", "Available", ""),
    ("HOU@WAS", "Washington Wizards (WAS)", "Carrington, Bub", "Questionable", "Available", ""),
]

# status -> share of a player's minutes the model should treat as available
# (same convention the repo already uses in scripts/originate_horizon.py: STATUS_PLAY_PROB)
WEIGHT = {"Out": 0.00, "Doubtful": 0.25, "Questionable": 0.50,
          "Probable": 0.80, "Available": 1.00, "(absent)": None}


def main():
    rows = []
    for g, team, player, a, p, note in CHANGES:
        delta = None
        if WEIGHT.get(a) is not None and WEIGHT.get(p) is not None:
            delta = round(WEIGHT[p] - WEIGHT[a], 2)
        rows.append({
            "matchup": g, "team": team, "player_as_printed": player,
            "status_0615AM_et": a, "status_0615PM_et": p, "changed": a != p,
            "availability_weight_delta": delta, "note": note,
            "source_0615AM": AM, "source_0615PM": PM,
        })
    changed = [r for r in rows if r["changed"]]
    down = [r for r in changed if (WEIGHT.get(r["status_0615AM_et"]) or 0) > (WEIGHT.get(r["status_0615PM_et"]) or 0)]
    up = [r for r in changed if (WEIGHT.get(r["status_0615AM_et"]) or 0) < (WEIGHT.get(r["status_0615PM_et"]) or 0)]
    doc = {
        "title": "Consecutive official injury-report editions, diffed: 11/15 06:15 AM ET vs 11/15 06:15 PM ET",
        "retrieved_utc": "2026-11-16T00:40Z..00:50Z",
        "edition_a": {"stamp": "11/15/26 06:15 AM ET", "url": AM,
                      "the_edition_the_published_model_inputs_used": True},
        "edition_b": {"stamp": "11/15/26 06:15 PM ET", "url": PM,
                      "last_edition_listed_on_the_official_index_at_read_time": True},
        "scope": ("First reader chunk of each edition only (IND@PHI, LAL@PHX, CHA@LAC, SAS@UTA, "
                  "DAL@BOS, NYK@TOR, HOU@WAS, ATL@MIL). Rows printed only in later chunks are "
                  "not compared and are not claimed unchanged."),
        "availability_weight_convention": WEIGHT,
        "convention_note": ("The weights are the repo's existing convention "
                            "(scripts/originate_horizon.py STATUS_PLAY_PROB). The two editions' "
                            "printed status cells are the evidence; the weight only translates "
                            "them and is labelled as a model convention, not an official value."),
        "rows_compared": len(rows),
        "status_changed": len(changed),
        "downgrades": len(down),
        "upgrades": len(up),
        "rows": rows,
    }
    json.dump(doc, open(os.path.join(HERE, "injury_diff.json"), "w"), indent=1, ensure_ascii=False)
    print(f"rows compared {len(rows)}, changed {len(changed)} "
          f"(downgrades {len(down)}, upgrades {len(up)})")
    for r in changed:
        print(f'  {r["matchup"]:9s} {r["player_as_printed"]:26s} {r["status_0615AM_et"]:13s} -> '
              f'{r["status_0615PM_et"]:14s} {r["note"][:60]}')


if __name__ == "__main__":
    main()
