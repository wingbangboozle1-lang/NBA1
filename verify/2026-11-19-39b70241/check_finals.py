import json
for f in ["data/official/results_2026-11-17_39b70241.json","data/official/results_2026-11-18_39b70241.json"]:
    d=json.load(open(f)); ok=0
    for r in d["rows"]:
        assert sum(r["away_quarters"])==r["away_pts"], r
        assert sum(r["home_quarters"])==r["home_pts"], r
        ok+=1
    print(f, ok, "games, all quarter sums match finals")
