# Scheduled-refresh integrity audit — does "refresh, then rebuild only after gates pass" actually run?

**Session** `arena/3242d896-nba1` · **branch** `arena/3242d896-nba1` · **base commit** `cd8fd27`
**Audit window** 2026-11-15 23:40Z – 2026-11-16 00:10Z · **Scope claimed** `COORDINATION.md` §43
**Verdict** The gate is honest. The pipeline it guards is not connected to anything.

---

## 0. What was audited and what was not

| In scope (read, executed, never edited) | Out of scope |
| --- | --- |
| `engine/fetch_official.py`, `engine/refresh_gate.py`, `.github/workflows/refresh-data.yml`, `scripts/probe_official.py`, `scripts/test_refresh_gate.py`, `engine/pipeline.py` (execution only) | `data/**`, `site/**`, `docs/**`, `command-center/**`, `scripts/**` edits, `data/content/**`, `index.html`, `picks.html`, `verification.html` — all held by the five live claims §41/§42 |

Five sessions held claims on the data and site surfaces when this audit began
(§41 `513516f6`, §41 `5ae0869e`, §41 `49f70042`, §41 `801ba27f`, §42 `4533630f`). This session
therefore claimed **only** the refresh pipeline and a new `verify/` namespace, and offers fixes as
requests rather than applying them.

---

## 1. The claim under test

The brief asks for one thing of the scheduler:

> "Extend the scheduled job to refresh the official schedule, standings, team statistics and injury
> report for each rolling slate, then rebuild only after freshness and provenance gates pass."

The repository asserts this is delivered. `COORDINATION.md` §38.2 records that the gate "correctly
skipped the rebuild", and §38.1 records the gate returning **BLOCK** as "the intended safe result
while the required structured/promoted inputs are absent". The wording is accurate. The finding below
is that those inputs are absent **by construction** — nothing in this repository ever writes them —
so the sentence "the rebuild is waiting for promotion" describes a state that cannot end.

---

## 2. Findings

Severity uses the repository's own scale (High / Medium / Low). Every row carries the exact evidence.
Reproduce everything with `python3 verify/2026-11-15-3242d896/reproduce.py`.

### R-43-01 (High) — The gate requires three promoted inputs that no code writes, so `ok=true` is unreachable

`engine/refresh_gate.py` lines 235–260 require `data/raw/standings.json`,
`data/raw/team_traditional.json` and `data/raw/team_opponent.json`, each with
`verification.verified == true`, `verification.source_url` equal to *this run's* check URL, and
`verification.source_sha256` equal to *this run's* response digest.

- **Those three files do not exist on `main`.** `find . -name standings.json -o -name team_traditional.json -o -name team_opponent.json` returns only `data/official/standings.json` (a differently-shaped, hand-captured file that is not read here).
- **No code writes them.** `grep -rn 'standings.json\|team_traditional.json\|team_opponent.json' --include=*.py .` returns only the gate itself (reader) and `scripts/test_refresh_gate.py` (fixture).
- The pipeline that *would* be skipped even if the gate passed — `engine/pipeline.py` — reads `data/raw/schedule_upcoming.json`, `data/raw/injuries.json`, `data/raw/team_advanced.json`, `data/raw/games_completed.json`, `data/raw/players_traditional.json`. It never reads the three required files. So even a passing gate would rebuild from snapshots that are not the ones the gate validated.
- **Evidence E2**: a record built from the *real* 22:44Z scheduled run — 8/8 primary sources HTTP 200 with that run's own SHA-256 digests, zero failed checks, zero changed captures, i.e. the best record the fetcher can physically produce — still returns **21 BLOCK lines**, three of them exactly `S8_standings lacks structured, verified promoted data`, `S9_team_traditional …`, `S10_team_opponent …`.

**Consequence.** The conditional rebuild step in `.github/workflows/refresh-data.yml` (step 6) can
never execute. The "then rebuild only after freshness and provenance gates pass" half of the brief is
not running, and cannot start until a promotion writer exists.

### R-43-02 (High) — The fetch step reports `success` and the job reports `success` while every parse fails

`.github/workflows/refresh-data.yml` marks *both* the fetch step and the gate step `continue-on-error:
true`, and the fetcher itself exits 0 on failure by design. The job therefore reports **success** even
when nothing parsed.

- Run [`43770932084`](https://github.com/wingbangboozle1-lang/NBA1/actions/runs/43770932084) (schedule, `main`, 22:44:12Z): job conclusion `success`; step 4 *Fetch official sources* `success`; step 5 *Require fresh provenance…* `success`; step 6 *Rebuild…* `skipped`. The record that run committed to `auto/refresh-20261115-224729` reports `failed = [["S1_season","expected 30 team rows, parsed 0"], ["S2_train",…], ["S4_schedule","no game links found"]]`.
- Run [`43731578639`](https://github.com/wingbangboozle1-lang/NBA1/actions/runs/43731578639) (schedule, 15:44:44Z): identical step pattern, same three parse failures in its committed record.
- `engine/fetch_official.py` line ~1050 returns 0 unconditionally ("Exit 0 even with failures: the caller decides"), and the gate step is `continue-on-error`, so no signal reaches the job.

The design intent ("a data problem must never break the published site") is legitimate, but the
result is that **a green refresh run carries no information**. A reader of the Actions tab sees
success; §38.2's prose is the only place that says otherwise.

### R-43-03 (Medium) — A scheduled run recorded `build_outcome: success` with zero provenance checks — and it is *not* a bypass

`origin/auto/refresh-20261115-114915` (commit 2026-11-15T11:49:15Z) contains
`data/raw/_last_refresh.json` with:

```
captured_at_utc : 2026-11-15T11:46:11Z
fetch_outcome   : success
build_outcome   : success        <-- a build step executed
source_checks   : []             <-- zero per-source provenance checks
failed          : 4 parse failures
```

At first reading that looks like the gate being bypassed. **It is not, and I corrected my own first
conclusion here after checking the run.** Run
[`43710500439`](https://github.com/wingbangboozle1-lang/NBA1/actions/runs/43710500439) (schedule,
2026-11-15T11:46:02Z, head `ef2e723`) shows why:

| Step | At `ef2e723` (that run) | At `cd8fd27` (today) |
| --- | --- | --- |
| 4 | *Verify the site builders still run* → runs `engine/pipeline.py` + `engine/build_site.py` **before** fetching, `continue-on-error` | — |
| 5 | *Discard builder churn (promotions happen only after verification)* → `git checkout -- .` | — |
| 6 | *Fetch official sources* | step 4 |
| — | no gate step at all | step 5 *Require fresh provenance…*, step 6 conditional rebuild |

So on `ef2e723` the "build" was a **pre-existing liveness check**, ran before the fetch, and its
output was discarded by `git checkout -- .` — no gated rebuild existed to skip. The gate landed later
(PR #104, `7a6f7ce`, merged as part of `cd8fd27`), and every run since (15:44Z, 22:44Z) correctly
skips the rebuild.

What survives as a finding is narrower but still real, and now proven by direct comparison rather
than by inference: `build_outcome: success` in a committed refresh record does **not** mean "the
gated rebuild passed" — on historical commits it means "a pre-fetch liveness build ran". The field is
ambiguous across the file's own history, so any reader (or any future audit) that treats it as a gate
receipt is wrong. See §6 S-43-04.

**Superseded note, kept deliberately:** my first pass also recorded that "no workflow run is listed
for that window" and flagged the record's provenance as unknown. That was wrong and was caused by
reading only the first page of `actions/runs`; with `per_page=100&created=2026-11-15` the run appears.
No part of this report now rests on that claim.

### R-43-04 (Medium) — The fetcher asks for injury editions under a filename that the official index proves does not exist

`engine/fetch_official.py` builds its injury candidates as
`Injury-Report_{YYYY}_{MM}_{DD}_{hh}_{mm}{AM|PM}.pdf` (`day.isoformat().replace('-', '_')`, line 775).
The official index uses **hyphens in the date and underscores only in the time**.

| Form | Example | Advertised on the official index? | Result in the scheduled run |
| --- | --- | --- | --- |
| hyphen form (*used* by the official index and by the repo's own `data/official/**` captures) | `Injury-Report_2026-11-15_05_30PM.pdf` | **Yes** ([official index](https://official.nba.com/nba-injury-report-2026-27-season/)) | HTTP 200, PDF archived |
| underscore form (*built* by the fetcher) | `Injury-Report_2026_11_15_05_15PM.pdf` | **No** — the string does not occur anywhere on the index page | HTTP 403 → recorded as "unavailable", never retried under the right name |

Evidence: the run-43770932084 record contains two 200/`pdf_valid` archives with hyphen names
(`Injury-Report_2026-11-15_05_15PM.pdf`, `…_05_30PM.pdf`, both present on
`origin/auto/refresh-20261115-224729`) — these came from the index scrape — and **six** 403s, all
underscore names. The repo's own comment at line 116 concedes "403 from ak-static is recorded as
unavailable at capture time, not as proof that the file does not exist"; for the underscore form the
official index *is* that proof.

**Consequence.** The injured-report side of the scheduled refresh retrieves only whatever the last two
index entries happen to be; its fixed-time edition probe is dead code that logs 403s.

### R-43-05 (Medium) — The build executes, its output is thrown away, and it is not reproducible from the committed tree

`.github/workflows/refresh-data.yml` step 8 runs `git checkout -- docs/data docs/b` after every
non-skipped build — so a passing rebuild produces no committed output. Whatever it wrote is discarded
before the capture commit is staged.

Separately, rebuilding a clean checkout of `cd8fd27` with the repository's own builders in dependency
order produces **13 files of difference** from what is committed:

| Builder | Files rewritten vs committed | Example |
| --- | --- | --- |
| `engine/pipeline.py` | `docs/data/{lines,teams,gameflow,meta,picks,sources}.json` | `docs/data/teams.json` 403 lines → 1 (`-402`); `docs/data/lines.json` `-380` |
| `engine/build_site.py` + `scripts/build_dashboard.py` | the same six under `site/data/` plus `site/pages/picks.html` | `meta.json` loses 32 lines of provenance prose |

The committed `docs/data/meta.json` and `site/data/meta.json` are **not** the output of
`engine/pipeline.py` — the builder replaces `injury_report`, `records`, `ratings_season_to_date_unchanged_note`
and `previous_ratings_season_to_date` with shorter strings, and drops `verification_rule` and the whole
`live_reverification` block. Those fields are provenance statements a reader relies on; re-running the
documented rebuild would silently delete them.

This is why R-43-05 matters even though the site is fine today: the repository has no working
`data → page` reproduction, so no "freshly refreshed" page can be traced to a build.

### R-43-07 (Low) — The committed scheduled-run record is 28 hours stale and describes a failure

`data/raw/_last_refresh.json` on `main` still reads `captured_at_utc: 2026-11-14T19:40:43Z`,
`build_outcome: failure`, no `source_checks`. The workflow only stages that file when a capture changed,
so three later successful runs left it untouched. On the tree itself the gate prints
`refresh run is stale or future-dated (27.96h)`.

**Consequence.** Nothing that reads the committed record can tell that the scheduler is running at all.
This is the one case where the site is *more* current than its own refresh evidence. The gate is what
caught it — 38 BLOCK lines, not a silent pass.

---

## 3. What is actually correct (verified, not assumed)

| Check | Result | Evidence |
| --- | --- | --- |
| Gate fails closed on stale runs, untrusted hosts, changed-unpromoted captures, digest mismatch, missing/tampered PDFs | **pass** — 7/7 unit tests | `python3 -m unittest scripts.test_refresh_gate -v` → `Ran 7 tests … OK` |
| Gate never mutates data; builders never run on gate failure | **pass** | workflow step 6 `if: steps.fetch.outcome == 'success' && steps.freshness.outputs.ok == 'true'`; `--max-age-hours 10` |
| Only official hosts are contacted | **pass** | `ALLOWED_HOSTS = {www.nba.com, official.nba.com, ak-static.cms.nba.com, stats.nba.com}`; enforced in `get()` before every request |
| Results feed covers today **and** yesterday (the "last night went final after capture" defect) | **pass** | `capture_results()` lines 656–667; a real improvement landed from PR #58 |
| Injury PDFs are stored byte-for-byte, content-addressed, with a sidecar timestamp | **pass** | `data/raw/injury_pdfs/*__<sha256>.pdf` + `.json` exist on `origin/auto/refresh-20261115-224729` (`…_05_15PM__e6605d35….pdf`, `…_05_30PM__0ff31c23….pdf`) |
| The gate would catch a tampered archived PDF | **pass** | `test_tampered_archived_pdf_blocks`; archive digest recomputed from the bytes |

The gate is genuinely well built. Its problem is that the thing behind the door does not exist.

---

## 4. Why this matters for the brief's other requirements

The scheduled refresh is the *only* mechanism that could keep the published horizon current. The
rolling-slate requirement ("generate picks for every upcoming slate up to 3 days in advance") depends
on it. Today the published horizon is `2026-11-15 .. 2026-11-18` and was built by
`scripts/originate_horizon.py` from **hand-captured** files under `data/official/**` — not from the
scheduler. The scheduler contributes nothing to the horizon. That is a design fact, not a defect in
the gate, and it belongs in the requirements traceability register (§43 request R-43-B).

---

## 5. Open questions raised by this audit (need information, not opinion)

| # | Question | What would answer it | Status |
| --- | --- | --- | --- |
| Q-43-01 | Which session or process was meant to write `data/raw/{standings,team_traditional,team_opponent}.json` with a `verification` block bound to the current run digest? | A commit, a script, or an explicit decision that these three sources are not model inputs and should be removed from `REQUIRED`/`promoted_paths` | **Open** |
| Q-43-02 | Should a scheduled refresh whose parsers fail three of eight primary sources report **green**? | A decision on job-level signalling (see §6 S-43-02) | **Open** |
| Q-43-03 | Should `git checkout -- docs/data docs/b` discard a passing rebuild, or commit it behind a verified-promotion PR? | A decision; the current text implies "discard", the brief implies "publish" | **Open** |
| Q-43-04 | Which builder is the canonical one for `docs/data/**` and `site/data/**`? Six scripts write these paths and at least two disagree with what is committed | A single declared entry point plus a CI check that regeneration is a no-op | **Open** |
| Q-43-05 | Is the underscore injury filename intentional (a probe for an alternate naming scheme) or a bug? | A note from the author; the official index settles which form exists | **Open** — the fetch record proves which form works |
| Q-43-06 | **Answered.** `auto/refresh-20261115-114915` was produced by run [`43710500439`](https://github.com/wingbangboozle1-lang/NBA1/actions/runs/43710500439) at 11:46:02Z on head `ef2e723`, using the pre-gate workflow whose step 4 was a pre-fetch liveness build. No gate was bypassed | — | **Closed** (see R-43-03) |
| Q-43-07 | Do the two standings disagreements found live (PHI 10-3 vs 11-3, IND 5-8 vs 5-9) reach any published line? | Team ratings in `data/derived/horizon_lines.json` match the official advanced capture exactly (34/34 games, 68 team-sides, 0 mismatches), so no — but the *displayed* records are stale | **Answered: no effect on lines; display-only** (see §7) |

---

## 6. Suggestions, cheapest first (none implemented here — offered to the owning scope)

| # | Suggestion | Effort | Unlocks | Risk if skipped |
| --- | --- | --- | --- | --- |
| S-43-01 | Delete `S8_standings`/`S9`/`S10` from `REQUIRED` + `promoted_paths`, **or** write the promotion step. Do not leave a requirement that cannot be met | S / M | Makes `ok=true` reachable; makes the gate's answer meaningful | The gate keeps returning BLOCK forever and the rebuild stays dead |
| S-43-02 | Add a job-level signal: `if: steps.fetch.outputs.parsed_ok != 'true'` → a failing annotation step (not a build break) so a scan of the Actions tab shows a red mark for "parsers failed" | S | A green run starts meaning something | Every future reader is misled by green |
| S-43-03 | Fix the injury filename to the hyphen form and probe the two newest *index* entries plus the two fixed times in that form | S | The fixed-time edition probe stops being dead code | Report currency depends on scraping luck |
| S-43-04 | Record the build outcome inside the committed capture commit (a build receipt), even when the output is discarded | S | "The rebuild ran and here is what it produced" becomes auditable | No way to tell a discarded rebuild from a skipped one |
| S-43-05 | Declare one canonical builder per output tree and add a CI check that re-running it is a no-op | M | Reproducibility; ends the six-writer overlap | Provenance prose keeps getting deleted on rebuild |
| S-43-06 | Have the workflow commit `_last_refresh.json` on every run (or copy it into the run artifact path the site reads) so the committed record is never 28 h stale | S | The refresh state is visible on the tree, not just in Actions | The site's own refresh evidence is the least current file in the repo |

---

## 7. Live official check performed anyway (so the audit is not purely structural)

Using this session's page-fetch channel (which reaches `www.nba.com`, unlike `curl` in this sandbox), I
read two official pages at **2026-11-15T23:45Z** and compared them to the committed captures. These are
read-only observations; nothing was edited.

| Official page | Read at | Compared against | Result |
| --- | --- | --- | --- |
| [`www.nba.com/games?date=2026-11-14`](https://www.nba.com/games?date=2026-11-14) | 23:44Z | `data/official/results_2026-11-14.json` (5 rows) | **5/5 games agree** on both final scores: DEN 116–NOP 108, DAL 117–CLE 127, BKN 110–MEM 129, DET 117–MIA 137, CHI 117–MIN 106 |
| [`www.nba.com/standings`](https://www.nba.com/standings) | 23:47Z | `data/official/standings_2026-11-15.json` (30 rows) | **27/29 rows agree** on W-L and win% after the 11/15 games; **2 differ**, both explained by games that went final after the capture: PHI `10-3` → now `11-3` (PHI beat IND), IND `5-8` → now `5-9` |
| [`www.nba.com/standings`](https://www.nba.com/standings) | 23:47Z | `data/derived/horizon_lines.json` team ratings | **68/68 team-sides agree** with `data/official/teams_advanced_2026-11-15.json` on OffRtg, DefRtg and Pace (max abs difference 0.0) |

Read #3 is the important one: the lines' **model inputs** are exactly the official advanced capture.
Read #2 is the reason the *displayed records* on the horizon will drift during a game day — they are
"post-11/14 records captured 2026-11-15", as the file itself says, and no scheduled job refreshes them
(R-43-01).

Two honest limits on this section: (a) the box-score page HTML for a *finished* game renders the
in-progress scoreboard rail above the table, so I used the official **games** page for finals and did
not claim quarter scores from a live read; (b) my fetch of
`www.nba.com/game/det-vs-mia-0022600233/box-score` returned the current slate rail before the box-score
table, so it is not cited as evidence for anything.

---

## 8. How to reproduce

```
python3 verify/2026-11-15-3242d896/reproduce.py          # all evidence, ~10 s, no network
python3 -m unittest scripts.test_refresh_gate -v         # 7/7 pass
python3 engine/refresh_gate.py --max-age-hours 10        # 38 BLOCK lines on the committed tree
```

`reproduce.py` writes `evidence.json` beside this report and prints the same tables. It touches no
repository file outside its own directory.
