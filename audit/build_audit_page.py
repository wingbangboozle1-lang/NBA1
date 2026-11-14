#!/usr/bin/env python3
"""X04: build docs/audit/index.html from the audit reports (static HTML, no JavaScript).

Refuses to build unless both checkers report zero mismatches. Every table row carries
a link to an official NBA.com page; repository-only evidence is labelled as such.

Run from the repository root:  python3 audit/build_audit_page.py
"""
import html, json, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
def load(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)
E = lambda s: html.escape(str(s), quote=True)

rep1 = load("audit/results/x01_x02_report.json")
rep3 = load("audit/stats/x03_report.json")
if rep1["mismatch_count"] or rep3["mismatch_count"]:
    raise SystemExit("refusing to build: checker reports mismatches")

off_scores = load("audit/results/official_scores_2026-11-06_to_12.json")
off_team = load("audit/stats/official_team_advanced.json")
irr = load("audit/irregularities.json")
games_repo = load("data/raw/games_completed.json")
ix = {c: i for i, c in enumerate(games_repo["cols"])}
repo_by_id = {r[ix["game_id"]]: r for r in games_repo["rows"]}
stored_team = {r["team"]: r for r in load("data/teams_advanced_2026_27.json")["rows"]}
raw_team = load("data/raw/team_advanced.json")
raw_train = next(w for w in raw_team["windows"] if w["window_id"].startswith("train"))
raw_train_by_team = {r[0]: dict(zip(raw_team["cols"], r)) for r in raw_train["rows"]}
bt2 = load("docs/data/backtest.json")

OK = '<span class="badge ok">match</span>'
def status(ok): return OK if ok else '<span class="badge high">MISMATCH</span>'
def link(url, label="nba.com"): return f'<a href="{E(url)}" target="_blank" rel="noopener">{E(label)}</a>'

# ---- games table ---------------------------------------------------------------
game_rows = []
n_match = 0
for g in off_scores["games"]:
    r = repo_by_id[g["game_id"]]
    ok = (r[ix["away_pts"]] == g["away_pts"] and r[ix["home_pts"]] == g["home_pts"]
          and r[ix["away"]] == g["away"] and r[ix["home"]] == g["home"])
    n_match += ok
    ot = " (OT)" if g["status"].startswith("Final/OT") else ""
    neutral = " (neutral)" if "Neutral" in g["status"] else ""
    game_rows.append(
        f'<tr><td>{E(g["date"])}</td><td class="mono">{E(g["game_id"])}</td>'
        f'<td>{E(g["away"])} @ {E(g["home"])}{neutral}</td>'
        f'<td class="num">{g["away_pts"]}–{g["home_pts"]}{E(ot)}</td>'
        f'<td class="num">{r[ix["away_pts"]]}–{r[ix["home_pts"]]}</td>'
        f'<td>{status(ok)}</td><td>{link(g["url"], "NBA.com game page")}</td></tr>')

# ---- team tables ---------------------------------------------------------------
TEAM_COLS = ["gp", "w", "l", "off_rtg", "def_rtg", "net_rtg", "pace", "poss"]
def team_table(rows_official, stored_lookup, source_url, stored_label):
    out = []
    n_ok = 0
    for r in rows_official:
        o = dict(zip(off_team["_meta"]["columns"], r))
        s = stored_lookup[o["team"]]
        def sv(k):
            if stored_label == "raw":
                k2 = {"off_rtg": "ortg", "def_rtg": "drtg", "net_rtg": "netr"}.get(k, k)
                return s[k2]
            return s[k]
        ok = all(abs(float(sv(k)) - float(o[k])) < 1e-9 for k in TEAM_COLS)
        n_ok += ok
        out.append(
            f'<tr><td>{E(o["team"])}</td>'
            + "".join(f'<td class="num">{o[k]:,}</td>' if k == "poss" else f'<td class="num">{o[k]}</td>' for k in TEAM_COLS)
            + f'<td>{status(ok)}</td><td>{link(source_url, "NBA.com Teams > Advanced")}</td></tr>')
    return out, n_ok

team_hdr = ("<tr><th>Team</th><th>GP</th><th>W</th><th>L</th><th>OffRtg</th><th>DefRtg</th>"
            "<th>NetRtg</th><th>Pace</th><th>Poss (total)</th><th>Stored = official</th><th>Source</th></tr>")
season_rows, season_ok = team_table(off_team["season_to_date"], stored_team,
    off_team["_meta"]["windows"]["season_to_date"]["source_url"], "stored")
train_rows, train_ok = team_table(off_team["train_2026-10-20_2026-11-05"], raw_train_by_team,
    off_team["_meta"]["windows"]["train_2026-10-20_2026-11-05"]["source_url"], "raw")

# ---- backtest re-derivation -----------------------------------------------------
m = rep1["x02_backtests"]["docs_data_backtest_51"]["rederived"]
bt_rows = []
for k in ["straight_up_model", "straight_up_ref", "mae_margin_model", "mae_total_model", "brier_model", "brier_ref"]:
    stated = m[f"{k}_stated"]
    rederived = m[k]
    bt_rows.append(f'<tr><td>{E(k)}</td><td class="num">{E(rederived)}</td><td class="num">{E(stated)}</td>'
                   f'<td>{status(str(rederived) == str(stated))}</td>'
                   f'<td>{link("https://www.nba.com/games?date=2026-11-06", "NBA.com games pages 11/06–11/12")}</td></tr>')

# ---- irregularities ---------------------------------------------------------------
sev_cls = {"High": "high", "Medium": "medium", "Low": "low", "Info": "info"}
irr_rows = []
for it in irr["items"]:
    links = " · ".join(f'<a href="{E(l["url"])}" target="_blank" rel="noopener">{E(l["label"])}</a>' for l in it["links"])
    if not any("nba.com" in l["url"] or "docs.github.com" in l["url"] for l in it["links"]):
        links += ' <span class="faint small">(repository evidence; no NBA value involved)</span>'
    irr_rows.append(
        f'<tr><td class="mono">{E(it["id"])}</td><td><span class="badge {sev_cls[it["severity"]]}">{E(it["severity"])}</span></td>'
        f'<td>{E(it["area"])}</td><td>{E(it["finding"])}<div class="faint small">Evidence: {E(it["evidence"])}</div></td>'
        f'<td>{links}</td><td>{E(it["suggested_action"])}</td></tr>')

page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Independent audit — NBA1</title>
<meta name="description" content="Independent re-verification of final scores, backtest arithmetic and team advanced stats against NBA.com, with an irregularity register.">
<link rel="stylesheet" href="../assets/site.css">
<style>.badge.ok{{color:var(--green);border-color:#256146;background:#0e2119}}</style>
</head>
<body>
<header class="top">
  <div class="top-inner">
    <a class="brand" href="../b/index.html">NBA<span>1</span></a>
    <nav class="main">
      <a href="../b/index.html">Build B overview</a>
      <a href="../index.html">Build A snapshot</a>
      <a href="../b/pages/flagged.html">Flagged (B)</a>
      <a href="../b/pages/sources.html">Sources (B)</a>
      <a href="#irregularities">Irregularities</a>
      <a href="https://github.com/wingbangboozle1-lang/NBA1/blob/main/COORDINATION.md" target="_blank" rel="noopener">Coordination board</a>
    </nav>
    <span class="stamp">checked 2026-11-14</span>
  </div>
</header>
<main>
<div class="wrap">

<h1>Independent audit</h1>
<p class="lede">Re-checks of stored results and statistics against official NBA.com pages, done line by line by a separate session
(<code>arena-9abdf3f7</code>). Each check is script-driven and reproducible from the repository. A value is marked
<span class="badge ok">match</span> only when the stored number equals the official number. Nothing was corrected.</p>

<div class="banner info"><div class="ico">i</div><div><p>This audit covers <b>results, backtest arithmetic and team statistics</b>.
It does not verify betting lines, odds, player minutes, injury rows or model outputs. Those are listed as not verified at the foot of the page.</p></div></div>

<h2>Summary</h2>
<table>
<thead><tr><th>Check</th><th>Scope</th><th>Rows / cells</th><th>Matching</th><th>Result</th><th>Source</th></tr></thead>
<tbody>
<tr><td>X01 · Final scores</td><td>51 games, 11/06–11/12, <code>data/raw/games_completed.json</code></td><td class="num">{len(off_scores["games"])} games</td><td class="num">{n_match}</td><td>{status(n_match == len(off_scores["games"]))}</td><td><a href="https://www.nba.com/games?date=2026-11-06" target="_blank" rel="noopener">11/06</a> · <a href="https://www.nba.com/games?date=2026-11-07" target="_blank" rel="noopener">11/07</a> · <a href="https://www.nba.com/games?date=2026-11-08" target="_blank" rel="noopener">11/08</a> · <a href="https://www.nba.com/games?date=2026-11-09" target="_blank" rel="noopener">11/09</a> · <a href="https://www.nba.com/games?date=2026-11-10" target="_blank" rel="noopener">11/10</a> · <a href="https://www.nba.com/games?date=2026-11-11" target="_blank" rel="noopener">11/11</a> · <a href="https://www.nba.com/games?date=2026-11-12" target="_blank" rel="noopener">11/12</a></td></tr>
<tr><td>X02 · Backtest, 14 rows</td><td><code>data/derived/backtest.json</code>: totals, margins, winners, OT</td><td class="num">{rep1["x02_backtests"]["data_derived_backtest_14"]["rows"]} rows</td><td class="num">{rep1["x02_backtests"]["data_derived_backtest_14"]["rows_matching"]}</td><td>{status(rep1["x02_backtests"]["data_derived_backtest_14"]["rows"] == rep1["x02_backtests"]["data_derived_backtest_14"]["rows_matching"])}</td><td><a href="https://www.nba.com/games?date=2026-11-06" target="_blank" rel="noopener">11/06</a> · <a href="https://www.nba.com/games?date=2026-11-07" target="_blank" rel="noopener">11/07</a> · <a href="https://www.nba.com/games?date=2026-11-08" target="_blank" rel="noopener">11/08</a> · <a href="https://www.nba.com/games?date=2026-11-09" target="_blank" rel="noopener">11/09</a> · <a href="https://www.nba.com/games?date=2026-11-10" target="_blank" rel="noopener">11/10</a> · <a href="https://www.nba.com/games?date=2026-11-11" target="_blank" rel="noopener">11/11</a> · <a href="https://www.nba.com/games?date=2026-11-12" target="_blank" rel="noopener">11/12</a></td></tr>
<tr><td>X02 · Backtest, 51 rows</td><td><code>docs/data/backtest.json</code>: fields and re-derived headline metrics</td><td class="num">{rep1["x02_backtests"]["docs_data_backtest_51"]["rows"]} rows</td><td class="num">{rep1["x02_backtests"]["docs_data_backtest_51"]["rows_matching_official_fields"]}</td><td>{status(rep1["x02_backtests"]["docs_data_backtest_51"]["rows_matching_official_fields"] == 51)}</td><td><a href="https://www.nba.com/games?date=2026-11-06" target="_blank" rel="noopener">11/06</a> · <a href="https://www.nba.com/games?date=2026-11-07" target="_blank" rel="noopener">11/07</a> · <a href="https://www.nba.com/games?date=2026-11-08" target="_blank" rel="noopener">11/08</a> · <a href="https://www.nba.com/games?date=2026-11-09" target="_blank" rel="noopener">11/09</a> · <a href="https://www.nba.com/games?date=2026-11-10" target="_blank" rel="noopener">11/10</a> · <a href="https://www.nba.com/games?date=2026-11-11" target="_blank" rel="noopener">11/11</a> · <a href="https://www.nba.com/games?date=2026-11-12" target="_blank" rel="noopener">11/12</a></td></tr>
<tr><td>X03 · Team advanced, season to date</td><td><code>data/teams_advanced_2026_27.json</code> and <code>data/raw/team_advanced.json</code></td><td class="num">30 teams</td><td class="num">{season_ok}</td><td>{status(season_ok == 30)}</td><td>{link(off_team["_meta"]["windows"]["season_to_date"]["source_url"], "NBA.com Teams > Advanced")}</td></tr>
<tr><td>X03 · Team advanced, training window</td><td><code>data/raw/team_advanced.json</code>, 10/20–11/05</td><td class="num">30 teams</td><td class="num">{train_ok}</td><td>{status(train_ok == 30)}</td><td>{link(off_team["_meta"]["windows"]["train_2026-10-20_2026-11-05"]["source_url"], "NBA.com Teams > Advanced (10/20–11/05)")}</td></tr>
</tbody>
</table>
<p class="faint small">Corruption test: the checker was run once on a copy with two planted errors and reported both, so a clean result is not a blind pass.</p>

<h2>X01 · Final scores vs NBA.com</h2>
<p class="small">Official values read from the NBA.com Games &amp; Scores page for each date, all chunks. The first team listed on each card is the away team. Every row links to its own game page.</p>
<div class="tablewrap"><table>
<thead><tr><th>Date</th><th>Game ID</th><th>Matchup</th><th>Official (away–home)</th><th>Stored</th><th>Status</th><th>Source</th></tr></thead>
<tbody>
{chr(10).join(game_rows)}
</tbody></table></div>

<h2>X03 · Team advanced stats, season to date</h2>
<p class="small">Official values from NBA.com Teams &gt; Advanced (season to date). Pace and possessions are shown as published. Possessions are season totals.</p>
<div class="tablewrap"><table>
<thead>{team_hdr}</thead>
<tbody>
{chr(10).join(season_rows)}
</tbody></table></div>

<h2>X03 · Team advanced stats, training window 10/20–11/05</h2>
<p class="small">Official values for the window the backtest uses to set ratings. The page's own Date From and Date To fields read 10/20/2026 and 11/05/2026.</p>
<div class="tablewrap"><table>
<thead>{team_hdr}</thead>
<tbody>
{chr(10).join(train_rows)}
</tbody></table></div>

<h2>X02 · Backtest headline metrics, re-derived</h2>
<p class="small">Recomputed from the 51 stored rows' own fields (probabilities, errors and results), not from the stored summary.
Results match what the stored summary reports. These metrics depend on the model inputs, which were not checked.</p>
<div class="tablewrap"><table>
<thead><tr><th>Metric</th><th>Re-derived</th><th>Stored</th><th>Status</th><th>Source</th></tr></thead>
<tbody>
{chr(10).join(bt_rows)}
</tbody></table></div>

<h2 id="irregularities">Irregularity register</h2>
<p class="small">Every issue found in this audit, with evidence and a link. None blocks publication, and none was silently corrected.
Severity: <span class="badge high">High</span> could mislead a reader or run unreviewed code;
<span class="badge medium">Medium</span> data or label is wrong or stale;
<span class="badge low">Low</span> precision or wording; <span class="badge info">Info</span> a limit on this audit.</p>
<div class="tablewrap"><table>
<thead><tr><th>ID</th><th>Severity</th><th>Area</th><th>Finding</th><th>Links</th><th>Suggested action</th></tr></thead>
<tbody>
{chr(10).join(irr_rows)}
</tbody></table></div>

<h2>Not verified in this audit</h2>
<ul class="small">
<li>Betting lines, odds and prices: no price source was checked.</li>
<li>Injury-report rows and player minutes: outside this audit's scope (covered by other sessions' claims).</li>
<li>Model outputs (projected totals, spreads and probabilities): only their arithmetic against the stored results was checked.</li>
<li>The team table's as-of time: the official page shows no capture time (I-08).</li>
</ul>

<h2>Method and reproduction</h2>
<ul class="small">
<li>Official values were transcribed from fetch-tool reads of the NBA.com pages and stored with the URLs in <code>audit/results/official_scores_2026-11-06_to_12.json</code> and <code>audit/stats/official_team_advanced.json</code>.</li>
<li>Run <code>python3 audit/results/check_results.py</code>, <code>python3 audit/stats/check_team_advanced.py</code>, then <code>python3 audit/build_audit_page.py</code>. The page builder refuses to run if either checker reports a mismatch.</li>
<li>Reports: <code>audit/results/x01_x02_report.json</code> and <code>audit/stats/x03_report.json</code>.</li>
</ul>

</div>
</main>
</body>
</html>
"""
out = os.path.join(ROOT, "docs", "audit", "index.html")
with open(out, "w", encoding="utf-8") as fh:
    fh.write(page)
print("wrote", os.path.relpath(out, ROOT), "| games", n_match, "/", len(off_scores["games"]),
      "| season", season_ok, "/30 | train", train_ok, "/30 | irregularities", len(irr["items"]))
