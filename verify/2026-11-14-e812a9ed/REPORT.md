# Independent site QA — session `arena/e812a9ed-nba1`

**Checked:** 2026-11-14 UTC  
**Base:** `203833304a2d16594aac6d30802b5d0939106adc` (`main`)  
**Purpose:** independently run the repository's existing validators and report discrepancies without editing data, model code, generated site pages, navigation, or another session's files.

## What was run

All commands below completed successfully (exit code 0):

- `python3 scripts/check_site.py` — 15 root dashboard pages; 1,264 table rows checked and every row in its scope had an official NBA/GitHub source link; local links resolved.
- `python3 scripts/verify_integration.py` — 202 JSON files parsed; 122 HTML files and 11,918 static links scanned; no errors. It reports **5,733 of 5,940 HTML table data rows** with an official NBA source link, leaving **207 rows without one**, plus **44 warnings**.
- `python3 scripts/check_links.py` — 59 pages, 2,078 links, 879 table rows; no broken internal links, unapproved hosts, or unsourced rows in its scanned `docs/` and `command-center/` scope; one explicitly unverified row is permitted and reasoned.
- `python3 scripts/check_rendered.py` — 17 Command Center pages; 707 rendered rows; zero rows without links and zero invalid cells. This uses a DOM shim, not a browser, and does not test CSS.
- `python3 strategy-lab/check.py` — 8 pages and 479 rows; all 479 contain an official NBA link; zero problems.
- `python3 -m engine_v2.check_site` — 20 Origination Desk pages; all listed page tables passed the source-link check.
- `python3 scripts/verify_all.py` — builders, checker, and data audits passed. It also reported 36 official games for 11/13–11/17, 36 published rows compared, zero mismatches, and matching calendar counts. Those are the script's committed-capture comparisons, not a fresh NBA.com fetch by this session.

The independent integration checker deliberately counts all `<tr>` data rows across every HTML file. Its 207 rows are therefore an audit warning, not a claim that every such row contains an NBA-derived fact: some are repository-review, source-register, methodology, suggestion, or decision rows. The site brief nonetheless sets a blanket row-source standard. Each such row needs either an official NBA citation or an explicit, reviewed classification as non-NBA content; do not silently count this gap as resolved.

## Findings requiring review

1. **Conflicting skill/luck headline in the primary dashboard.** `index.html:75` says no strategy has cleared the skill gate and describes S1's 23–9 record as inside the luck range. `index.html:76` says S1's p-value is 0.020, says it is outside what luck alone produces, and that G4 passes. The executive summary also says the strategy remains unfunded because other gates fail. The combined conclusion may be “one statistical gate passed, strategy not funded,” but the banner's assertion that the result is inside the luck band conflicts with the detailed statement. This session did not re-estimate the underlying result; preserve the gate distinction and reconcile the wording against its registered test and multiplicity correction before changing a headline.

2. **Multiple site vintages remain visible and report different windows/results.** The root dashboard describes 27 games (14–17 Nov) and a 60-game out-of-sample window. `origination/index.html:61–69` describes 22 lines (14–16 Nov), a 101-game walk-forward window, and a different model/leaderboard. `README.md` describes both and the root page says multiple builds are preserved, but root navigation/“every build” links do not clearly identify `origination/index.html` or `strategy-lab/index.html` as separately dated research products. Do not merge their metrics into one result; label each page with its capture/version and add explicit entry links from the canonical landing page when the integration owner next regenerates it.

3. **Row-source coverage is incomplete under the blanket requirement.** `scripts/verify_integration.py` reports 207/5,940 rows without an NBA link and names examples such as `command-center/index.html`, `docs/audit/index.html`, `origination/pages/repo-review.html`, `site/pages/repo-review.html`, and several decision pages. The direct per-page counts produced by a static audit of the same HTML include 28/28 rows in `origination/pages/repo-review.html`, 7/30 in `site/pages/repo-review.html`, and 11/11 in `docs/suggestions.html` without an official NBA URL. These are likely partly non-data rows, but the source policy needs to distinguish an NBA fact from an internal recommendation/methodology row or provide the provenance needed. A passing scoped checker does not establish compliance for every HTML page.

4. **Visible placeholder text is still present.** The integration checker flags `slate.html:69–70` (`None`) and `docs/pages/strategies.html:20` (`None`). Replace only after tracing each value to a source; otherwise render an explicit blank/unverified value and register it on the Flagged for Review page.

5. **Coordination board numbering is duplicated.** A heading scan found repeated section numbers (6, 8, 11, 12, 15, 17, 18, 20, 21, 23, 24, 25 and 26); §15 and §18 occur three times. This report did not renumber or delete board history. A single integration owner should reconcile duplicates while preserving the historical records and current ownership notes.

## Deployment and workflow state

- GitHub Pages API reports `status: built`, public URL `https://wingbangboozle1-lang.github.io/NBA1/`, source `main:/`, HTTPS enforced: <https://api.github.com/repos/wingbangboozle1-lang/NBA1/pages>.
- The latest Pages deployment visible to this session is successful: <https://github.com/wingbangboozle1-lang/NBA1/actions/runs/43597387021> (main commit `203833304a2d16594aac6d30802b5d0939106adc`). An earlier Pages publish at commit `f481d41b0061d04c70ecde09e87ff416dea309a6` also succeeded: <https://github.com/wingbangboozle1-lang/NBA1/actions/runs/43596810753>.
- This verifies GitHub's Pages build/deployment state, not that this session could fetch every published page or external NBA page in a browser. No fresh NBA.com HTTP fetch was performed here; the official-data audit relies on the committed captures and the repository's recorded checks.
- At audit time, open PRs #63, #65, #66, #75, and #80 were all reported `DIRTY` against `main`; #66 is explicitly the final-integration PR. This session made no attempt to merge, close, or edit another session's work.

## Official source references for manual review

These are official NBA source URLs already recorded in the repository's source register and captures. They are linked here as review starting points, not represented as freshly fetched by this session:

- NBA schedule: <https://www.nba.com/schedule>
- NBA game calendar / scores, 14 Nov 2026: <https://www.nba.com/games?date=2026-11-14>
- NBA advanced team statistics: <https://www.nba.com/stats/teams/advanced>
- Official 2026–27 injury-report index: <https://official.nba.com/nba-injury-report-2026-27-season/>
- Committed source register: [`../../data/raw/sources.json`](../../data/raw/sources.json)
- Committed horizon/source checks: [`../2026-11-14/official_horizon.json`](../2026-11-14/official_horizon.json), [`../2026-11-14/checks.json`](../2026-11-14/checks.json)

## Cross-session requests (not implemented here)

The affected root dashboard, generated pages, and data are outside this session's exclusive scope. The integration owner should:

- Reconcile the banner/executive S1 luck-gate wording against the underlying validation definitions and publish one consistent verdict.
- Add dated entry links for `origination/` and `strategy-lab/`, while preserving the distinction among their sample windows and model versions.
- Classify the 207 no-NBA-link rows. For each NBA claim, add the precise official URL; for non-NBA internal-method rows, label them as such and ensure they do not masquerade as verified NBA facts. Keep remaining gaps on Flagged for Review.
- Resolve the three leaked `None` strings without imputing values.
- Deduplicate coordination headings in a controlled integration-only pass.

No value was filled or changed by this audit. No result in this report should be treated as a wager recommendation or evidence of an edge against sportsbook prices.
