# audit/ — independent re-verification (session `arena-9abdf3f7`)

Re-checks stored results and statistics against official NBA.com pages. Read-only: nothing under `data/` or `docs/data/` is changed.

| Path | What it is |
| --- | --- |
| `results/official_scores_2026-11-06_to_12.json` | 51 official final scores, each with its NBA.com game URL and the date page it was read from |
| `results/check_results.py` | Compares the stored scores (`data/raw/games_completed.json`) and both backtest files against the official values; re-derives headline metrics |
| `results/x01_x02_report.json` | Output of the checker |
| `stats/official_team_advanced.json` | Official Teams > Advanced rows for the season to date and for 10/20–11/05, with the URLs |
| `stats/check_team_advanced.py` | Compares the stored team tables with the official values |
| `stats/x03_report.json` | Output of the checker |
| `irregularities.json` | Irregularity register (I-01 to I-10) with evidence, links and suggested actions |
| `build_audit_page.py` | Builds `docs/audit/index.html`; refuses to build if either checker reports a mismatch |

Reproduce from the repository root:

```
python3 audit/results/check_results.py
python3 audit/stats/check_team_advanced.py
python3 audit/build_audit_page.py
```

Limits: the official values were read with a fetch tool, not a browser, and the team-stats page shows no capture time (see I-08). Odds, lines, injury rows and player minutes are out of scope.
