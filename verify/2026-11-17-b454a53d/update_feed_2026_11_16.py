#!/usr/bin/env python3
"""Re-cut the 2026-11-16 rows of data/official/results_feed_2026_27.json from the verified
official file data/official/results_2026-11-16.json. Same convention as the 11/15 rows
(0e9c924f, §50 N04): scores, quarters, arena, attendance, officials and source URLs come from the
official capture; possessions / offensive & defensive rating / pace are NOT captured for these
games and are left null (never inferred). Every other row is untouched."""
import datetime, json, os
ROOT = "/home/user/NBA1"
NOW = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
off = json.load(open(os.path.join(ROOT, "data/official/results_2026-11-16.json")))
feed_p = os.path.join(ROOT, "data/official/results_feed_2026_27.json")
feed = json.load(open(feed_p, encoding="utf-8"))
by_id = {r["game_id"]: r for r in off["rows"]}
changed = 0
for row in feed["rows"]:
    if row["date"] != "2026-11-16":
        continue
    o = by_id[row["game_id"]]
    assert (o["away"], o["home"]) == (row["away"], row["home"]), row["game_id"]
    assert o["status"] == "FINAL" and sum(o["away_quarters"]) == o["away_pts"] and sum(o["home_quarters"]) == o["home_pts"]
    row.update({
        "game_status": 3, "game_status_text": "Final",
        "home_pts": o["home_pts"], "away_pts": o["away_pts"],
        "home_quarters": o["home_quarters"], "away_quarters": o["away_quarters"],
        "ot_periods": o["ot_periods"], "margin_home": o["home_pts"] - o["away_pts"],
        "total_pts": o["home_pts"] + o["away_pts"],
        "home_poss": None, "away_poss": None, "home_off_rtg": None, "away_off_rtg": None,
        "home_pace": None, "away_pace": None,
        "arena": o["venue"], "arena_city": o["city"].split(",")[0], "arena_state": o["city"].split(",")[1].strip(),
        "attendance": o["attendance"], "officials": o["officials"],
        "source_url": o["source_url"], "source_date_url": o["source_date_url"],
    })
    changed += 1
assert changed == 8, changed
finals = sum(1 for r in feed["rows"] if r.get("game_status") == 3)
feed["count_final"] = finals
feed["last_updated_utc"] = NOW
feed["last_updated_by"] = ("arena/b454a53d-nba1: the eight 2026-11-16 rows re-cut to FINAL from data/official/results_2026-11-16.json "
                           "(official LINESCORES, quarter sums asserted). poss/rtg/pace left null: the box-score inputs were not captured.")
with open(feed_p, "w", encoding="utf-8") as fh:
    json.dump(feed, fh, indent=1, ensure_ascii=False); fh.write("\n")
print("feed rows changed:", changed, "count_final:", finals, "of", feed["count"])
