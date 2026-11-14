# Independent integration verification — 2026-11-14

**Session:** `arena/bca884e9-nba1`  
**Scope:** repeatable local checks of the existing NBA line-origination site, integration outputs, source-link structure, rendered pages, and internal links. No model, captured source data, or shared site page was changed.  
**Result:** structural/build checks pass; data correctness and external-source reachability are **not** established by these checks.

## What was run and what it establishes

- `python3 scripts/verify_all.py` — **PASS**. Rebuilt the repository's site outputs and ran the existing integration gate. It reported `VERIFY OK`, 36 schedule rows checked with no mismatch in its comparison, plus a diagnostic note about a displayed injury-report/schedule time difference for DET@MIA. This is a local, reproducible checker result—not proof that every published value was independently read from NBA.com during this session.
- `python3 scripts/check_links.py` — **PASS** for the two legacy builds: 59 pages, 2,078 links, 879 data rows, 0 broken internal links, 0 non-approved hosts, 0 unsourced rows under that check's definition, and 1 explicitly unverified row. Its output explicitly says it checks the allowed host, not the external HTTP response; NBA.com could not be fetched from this sandbox.
- `python3 scripts/check_rendered.py` — **PASS** for Command Center: 17 pages, 707 rendered table rows, no rows without links or with malformed cells. This runs a DOM shim; it does not test CSS or real-browser behavior.
- `python3 scripts/verify_integration.py` — **PASS with warnings**: 202 JSON files parsed; 122 HTML files and 11,918 static links scanned; 0 errors; 44 warnings. The summary says 5,733 of 5,940 data rows have an official source link. Warnings include rows without official NBA links and three appearances of the literal text `None`; see the existing [Flagged for Review register](../../site/pages/flagged.html) (notably F34 and F37) and the generated checker output. A GitHub link or a general page-level source does not prove that a particular cell matches its cited NBA source.
- `python3 scripts/verify_dashboard.py` — **PASS**: 18 pages, 958 table rows checked, 937 with official source links, and all internal links resolved under this build's rules.
- `python3 -m engine_v2.check_site` — **PASS**: all 20 origination pages and their rendered tables were checked; rows in these tables carried an approved source link.
- `node scripts/render_check.mjs` — **PASS after installing the workflow's declared-on-demand `jsdom` dependency without changing the lockfile**: 122 pages, 8,099 content blocks, 7,297 rendered table rows, 0 pages with problems. This is a DOM-level check, not a visual/browser/accessibility audit.

The successful checks test complementary subsets and use different criteria. Their counts should not be summed as though they describe one deduplicated table population.

## Findings that remain open

1. **Structure is not factual verification.** Approved-host and row-link tests establish that a link exists and points to an allowed domain, not that the cited page supports the exact value in that row. The repository already records this limitation as F34; retain it as a hard boundary on all `verified` wording until a row-to-source comparison exists.
2. **A cross-build link-coverage gap remains visible to the integration checker.** Its current run reports 207 rows without a direct official NBA link (5,733/5,940 coverage), alongside three `None` text warnings. Some rows may be explanatory or internal by design, but each must be individually classified and explicitly marked as having no applicable official value/source rather than being silently treated as verified. Existing register entry F37 discusses five earlier pages; compare its scope to the current 44-warning output before declaring the current warning set resolved.
3. **Published copies are not one uniform build.** The repository intentionally preserves multiple dashboards and snapshots. The root page is a switcher, and each build has different dates and checks. Readers should follow each page's stated capture date and its own Flagged-for-Review page; do not treat a pass for one build as a pass for every other build.
4. **External reachability was not checked live here.** The link checker itself reports that outbound access to NBA.com is blocked from this sandbox. Official references are supplied below for manual review; HTTP status, page contents, and currentness are not asserted by this report.
5. **Injury time discrepancy:** the integrated site flags that the 11/13 injury-report transcription prints 07:00 ET for DET@MIA while the schedule page lists 8:00 PM ET. Both captured claims remain separately visible; the difference was not reconciled by this session. See the [source-check page](../../site/pages/source-check.html) and [Flagged for Review](../../site/pages/flagged.html).

## Recommended next steps

- Add a value-level comparison for each captured schedule, score, injury designation, and player statistic: record the source URL, capture/edition time, source text or stable identifier, normalized value, and comparison result. Fail the verification gate on mismatches unless the exact row is explicitly listed as unverified on Flagged for Review.
- Make the coverage audit enumerate every exception with page, table, row, reason, and decision. A row without an applicable official NBA fact should be visibly labeled `not available` / `not applicable`; it must not be described as independently verified.
- Keep model-derived figures visibly separate from official inputs. Link every input row to its official source and point to the method for each calculated output; do not present model output as an official NBA statistic or sportsbook line.
- Preserve the existing block on funding/publishing actionable picks until the independent closing-price source, sufficient pre-registered out-of-sample volume, calibration, and all required validation gates are available. Player-prop combos should remain blocked when game-level distributions or verified minutes inputs are absent.
- Run the full render, link, source-value, and build checks in CI against one defined canonical entry point and test the deployed GitHub Pages URL after publication. This report does not claim a new deployment or live-browser check.

## Official references for manual review

These are reference links already used by the project. They are **not** live-fetched or independently confirmed during this run.

- [NBA schedule](https://www.nba.com/schedule) and [NBA games and scores](https://www.nba.com/games) — fixtures, game status, and final scores.
- [NBA official injury-report index](https://official.nba.com/nba-injury-report-2026-27-season/) — report editions and submission policy; individual editions are linked from the site's injury rows.
- [NBA Stats — Teams Advanced](https://www.nba.com/stats/teams/advanced) and [Players Traditional](https://www.nba.com/stats/players/traditional) — official statistic tables; the project flags client-rendering and coverage limits rather than filling missing values.
- [NBA Stats glossary](https://www.nba.com/stats/help/glossary) — official definitions for statistics such as per-possession ratings.
- [GitHub Pages custom workflows documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages) — deployment mechanism reference, not a source for NBA facts.

## Reproduction

From the repository root:

```sh
python3 scripts/verify_all.py
python3 scripts/check_links.py
python3 scripts/check_rendered.py
python3 scripts/verify_integration.py
python3 scripts/verify_dashboard.py
python3 -m engine_v2.check_site
npm install --no-save --package-lock=false jsdom
node scripts/render_check.mjs
```
