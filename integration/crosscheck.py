#!/usr/bin/env python3
"""Cross-check this session's slate capture against Build C's independent capture.

Two captures of the same official pages, read hours apart by different sessions, are the only
free reproducibility test available here: no second data vendor exists. Agreement is not proof
that either is right — both could mis-read the same page the same way — but a DISAGREEMENT is
proof that at least one is wrong, which is why this runs before the desk publishes a line.

Sources compared:
  data/live/slate_2026_11_14_to_16.json                  (this session, 11/14–11/16)
  data/raw/official_schedule_capture_2026-11-14.json     (Build C, 11/13–11/17)
"""

import re

from common import dump, load

US_STATE = re.compile(r", [A-Z]{2}$")


def main():
    mine = load("data", "live", "slate_2026_11_14_to_16.json")
    theirs = load("data", "raw", "official_schedule_capture_2026-11-14.json")
    cols = theirs["cols"]
    their_by_id = {}
    for row in theirs["rows"]:
        g = dict(zip(cols, row))
        their_by_id[str(g.get("game_id"))] = g

    rows, agree, disagree, missing = [], 0, 0, 0
    for g in mine["games"]:
        t = their_by_id.get(str(g["game_id"]))
        if not t:
            missing += 1
            rows.append({"date": g["date"], "matchup": f"{g['away']}@{g['home']}",
                         "game_id": g["game_id"], "verdict": "not in the other capture",
                         "their_row": None,
                         "source_url": g["source_url"],
                         "their_source": theirs["sources"]["schedule"]})
            continue
        same_away = t.get("away") == g["away"]
        same_home = t.get("home") == g["home"]
        def clock(x):
            m = re.search(r"(\d{1,2}:\d{2})", str(x or ""))
            return m.group(1) if m else None
        tips_match = clock(t.get("tip_et")) == clock(g["time_et"]) if clock(g["time_et"]) else None
        ok = same_away and same_home
        if ok:
            agree += 1
        else:
            disagree += 1
        rows.append({
            "date": g["date"], "game_id": g["game_id"],
            "matchup_this_session": f"{g['away']}@{g['home']}",
            "matchup_other_capture": f"{t.get('away')}@{t.get('home')}",
            "tip_this_session": g["time_et"], "tip_other_capture": t.get("tip_et") or t.get("time_et"),
            "venue_other_capture": t.get("venue"), "city_other_capture": t.get("city"),
            "neutral_site_inferred": (False if (t.get("city") and US_STATE.search(t["city"])) else None),
            "verdict": ("match" if ok else "MISMATCH — a team is on the wrong side"),
            "tip_agrees": tips_match,
            "source_url": g["source_url"],
            "their_source": theirs["sources"].get(f"games_{g['date']}", theirs["sources"]["schedule"]),
        })

    out = {
        "purpose": "reproducibility of the slate capture against an independent official capture",
        "this_session": {"file": "data/live/slate_2026_11_14_to_16.json",
                         "games": len(mine["games"]), "read": mine["retrieved_utc"]},
        "other_capture": {"file": "data/raw/official_schedule_capture_2026-11-14.json",
                          "games": len(theirs["rows"]), "by": theirs["captured_by"],
                          "method": theirs["capture_method"][:400]},
        "counts": {"compared": len(rows), "match": agree, "mismatch": disagree,
                   "absent_from_other": missing},
        "tip_time_note": "tips are compared on the clock alone (7:00 PM), because the two captures "
                         "write the suffix differently; a mismatch on the hour is a real conflict",
        "venue_note": "venue and city exist only in the other capture; this desk inherits them "
                      "for the neutral-site veto and says so on every row that uses them",
        "rows": rows,
    }
    dump("crosscheck.json", out)
    print(f"crosscheck · compared={len(rows)} match={agree} mismatch={disagree} "
          f"absent={missing}")
    return out


if __name__ == "__main__":
    main()
