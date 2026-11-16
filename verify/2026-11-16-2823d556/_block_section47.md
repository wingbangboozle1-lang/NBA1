## 47. Session `arena/2823d556-nba1` — deploy-queue unblock, CI gap, and a live official re-read of the published 11/16 horizon (claimed 2026-11-16 02:10 UTC)

Branch `arena/2823d556-nba1`, based on `main` `f6b7676` (tip at claim time — PR #120, the §43
delivery record; `main` moved to `f906c73` during the session via PR #125). The platform pins this
session to that branch; the `session-<id>/<task>` naming in the brief is not used (single pinned
branch — deviation logged, as §16/§17/§28/§31/§35/§40/§44/§45 logged it).

**Board read before claiming:** §0 ground rules, §0b registry, §41–§46. Open PRs #107, #114, #117.

**Collision, logged up front.** Six sessions claimed overlapping scopes between 02:05 and 02:15
UTC, each invisible to the others: `arena/fbf3ff57-nba1` (§47, **integration seat**, includes a
T07 on `.github/workflows/probe-official.yml`), `arena/6e1aadc1-nba1` (§47), `arena/c348e6c7-nba1`
(§47), `arena/d31fb422-nba1` (§46), `arena/4ff440c7-nba1` (R21 player game logs, minutes
redistribution) and `arena/dfef26dc-nba1` (§48, site/shared-output rebuild seat). Section numbers
are duplicated as a result — the board's established convention (§11, §37, §45) is to renumber at
merge, and this record follows it.

**Scope actually executed, chosen to be non-overlapping with all six:**

| # | Task | Status | File scope (exclusive) |
| --- | --- | --- | --- |
| T01 | Board claim (banner + §0b row + this §47) pushed before any other edit | done | `COORDINATION.md` (top banner + §0b row + §47) |
| T02 | Stop the probe workflow from starving the Pages publisher: replace the `push` trigger with a 4×/day `schedule` + `workflow_dispatch`, bound the runtime, and add `scripts/verify_all.py` to the CI validate job | **done** | `.github/workflows/probe-official.yml`, `scripts/probe_official.py`, `.github/workflows/pages.yml` |
| T03 | Live official re-read at 02:17–02:27Z: the 11/15 slate's completion state, the 11/16 slate's currency, and a computed drift table against the committed captures behind the published 11/16 lines and picks | **done** | `verify/2026-11-16-2823d556/**` |
| T04 | Gate suite green, integration PR → `main`, merge, confirm Pages deploys, record the result here | in progress | repo-wide read; `COORDINATION.md` §47.2 |

**Dropped, with the reason.** T03 as originally scoped (an Actions-workflow capture of the 11/15
finals and the 11/16–11/19 slate) was **dropped**: `arena/fbf3ff57-nba1` (§47 T02/T03) and
`arena/d31fb422-nba1` (§46 Q01) both claim exactly that capture, and the duplicate-read rule
(`arena/dfef26dc-nba1`, §48.1: *a duplicated read is cheap, a clobbered file is not*) does not
justify a third. The planned R21 per-player-game-log task was **dropped** for the same reason:
`arena/4ff440c7-nba1` claims it as its P01 and `arena/6e1aadc1-nba1` claims it as its Z03.

**Not claimed / read-only:** `docs/**`, `engine/**`, `engine_v2/**`, `scripts/**` (generators),
`site/**`, `index.html`, `data/content/**`, `data/derived/horizon_*.json`, `data/prereg/**`,
`command-center/**`, `data/parsed/**`, `data/raw/**`, and every other session's `verify/*`
namespace. Findings that belong on shared surfaces are logged as **cross-session requests** below
rather than edited into another session's file.

### 47.1 Work log

**T02 — the deploy-queue unblock (02:10–02:20Z).** Measured at claim time, not inferred:
`gh api /repos/wingbangboozle1-lang/NBA1/pages` returned **`status: errored`**; every
`pages build and deployment` run since `afc79f2` was **`cancelled`**, never `built`; and six
`Probe official source reachability` runs sat ahead of the production
`Publish static site to GitHub Pages` run, several already 44–60 minutes into their wait.

Cause, read from the repository's own committed record: the probe workflow triggers on **every push
to every `arena/**` branch**, and its last completed run (`data/raw/probe_official.json`,
`probed_at_utc 2026-11-16T01:05:59Z`) took **1h16m over 1996 URLs**. Digging into that same record
located the bulk of the cost: **130 `stats.nba.com` URLs returned `http_status: null`**, i.e. each
burned the full 30 s socket timeout — **65 of the run's 76 minutes**.

Three changes:
1. `on: push` → `on: schedule` (4×/day, offset to `:20`) + `workflow_dispatch`. A reachability
   record is not a build artifact; nothing about the published site changes when a branch is pushed.
2. `scripts/probe_official.py`: socket timeout **30 s → 10 s**, plus a **per-host circuit breaker**
   (5 consecutive transport failures). URLs skipped by the breaker stay listed and are reported by a
   new **finding P6** as *UNKNOWN for this run* — never as reachable, never as dead.
3. `.github/workflows/pages.yml`: the `validate` job now runs `scripts/verify_all.py`, closing the
   open request at the end of §42.5 (R-42-B was a `<span>` in an `href` that `verify_integration.py`
   passed and only `verify_all.py` caught — a gate absent from CI is not a gate).

Merged cleanly with `arena/4533630f-nba1`'s global concurrency group (`bd73f53`, already on
`main`): **both fixes kept, neither discarded.** Self-evidencing: the push carrying the T02 commit
produced **no** new probe run, where every prior push in this repository's history had produced one.

**T03 — the live official re-read (02:17–02:27Z).** Evidence in `verify/2026-11-16-2823d556/`
(`live_reads.json`, `drift.json`, `rebuild_drift.py`, `render.py`, `check.py`, `REPORT.md`,
`index.html`). `check.py` exits 0 against the current tree.

| ID | Severity | Finding |
| --- | --- | --- |
| F-47-A | High | **The official sources are reachable from a session.** Flag `F7` and the "1749 cited URLs are refused to a non-browser client" finding describe the sandbox's *raw sockets* (`curl https://www.nba.com/` from this session's shell still returns **HTTP 000**), not the session's web-fetch channel, which returned full server-rendered content for both `games?date=` pages. |
| F-47-B | High | **The 2026-11-15 slate is not complete.** At 02:27Z the official page shows **6 of 9 Final**, 3 still printing a quarter clock (HOU@WAS Q4 5:24, ATL@MIL Q3 10:42, OKC@SAC Q1 7:59). The brief forbids settling before finals are verified, so **11/15 is not settleable at this retrieval time** — timestamped evidence for the sessions claiming that settlement. |
| F-47-C | High | **The official team-stat inputs behind the published 11/16 horizon are missing 5 completed games.** The committed advanced table counts **189** completed games (`sum(gp)/2`, measured from the file). Five 11/15 games finished after it was read → **10 team-record deltas** (BOS, CHA, DAL, LAC, LAL, NYK, PHX, SAS, TOR, UTA). Two of those teams (BOS, PHX) are on the 11/16 slate, so the published `BOS -14.5` and `DEN -5.0` picks were priced from a record the official page no longer prints. |
| F-47-D | Resolved | **The 11/16 slate itself is intact.** All 8 games, matchups and tip times agree between the committed capture and the live page; 6 of 8 rows agree on every field; the 2 that differ differ only in the team record (F-47-C). |
| F-47-E | Informational | **The two live official pages agree with each other on all 18 teams both print.** |
| F-47-F | High | **Why the live site is down, and it is not the probe queue.** `GET /repos/.../pages` returns `build_type: legacy`, `source: {branch: main, path: /}` — Pages is deploying **from a branch**, while `pages.yml` publishes with `actions/deploy-pages`, which **only works when the source is "GitHub Actions"**. The two are mutually exclusive. Meanwhile `GET /repos/.../pages/builds` shows **8 consecutive builds, 2026-11-16T01:02:23Z → 02:19:57Z, all `errored` with "Page build failed."** (the board's last recorded success is `afc79f2`, 2026-11-15T23:44:35Z). Content causes were **ruled out by measurement, not assumed**: 15.4 MB across 720 tracked files, largest file 1.28 MB, no symlinks, no non-ASCII/reserved filenames, `.nojekyll` present and tracked at the published root, no `_config.yml`/`Gemfile`. `PUT /repos/.../pages {build_type: workflow}` returns **HTTP 403 "Resource not accessible by integration"** — the session token cannot change it. **This needs the repository owner**: Settings → Pages → Source → *GitHub Actions*. Full evidence in `verify/2026-11-16-2823d556/deploy_diagnosis.json`. |

**What F-47-C deliberately does not claim:** that the two picks are wrong, or that anything should
be re-priced. This project's own rule (F72) is that a frozen line is never re-priced after its cut,
and no pick on this site is funded. The claim is narrower: *the inputs named in the published
provenance are demonstrably not the current official numbers, and the gap is now measured rather
than described.*

**Method.** Only what the official page printed is recorded. A game still printing a quarter clock
is IN PROGRESS and its live score is **not** stored in any final-score field. Where the page printed
nothing the cell is `null` — never inferred. **Not re-read in this pass:** the standings page, the
three team-stat pages, the injury-report index and PDFs, and the venue/city fields; anything sourced
from those is carried forward from the committed capture and is **not** marked verified.

### 47.2 Cross-session requests (logged, not executed)

- **R-47-2823-A** → the site/shared-output owner (`arena/dfef26dc-nba1`, §48): add
  `verify/2026-11-16-2823d556/index.html` to the shared nav and carry F-47-A…F-47-E onto the
  Flagged for Review page. This session does not edit `site/**` or `data/content/**`.
- **R-47-2823-B** → every session that recorded nba.com as unreachable: F-47-A means the rows
  marked *unverified because the source is unreachable* can now be re-examined in-session. Flag
  `F7` and finding `P2`/`P3` on `verification.html` should be re-worded to name the channel they
  actually tested (raw sockets via a GitHub runner), not "nba.com is unreachable".
- **R-47-2823-C** → the sessions claiming a 2026-11-15 settlement: F-47-B is the timestamped
  official evidence that the slate was not complete at 02:27Z.
- **R-47-2823-D** → `arena/fbf3ff57-nba1` (§47 T07, integration seat): this session's
  probe-workflow change is offered as a **carry, not a contest**. If the integration seat prefers a
  different trigger, that decision supersedes it; the runtime bounding and the CI gap stand either
  way, and both should land.
- **R-47-2823-E** → `arena/dfef26dc-nba1` (§48, owns `index.html`) — **WITHDRAWN, superseded.**
  This session had restored the two `docs/` links that commit `97519c7` (PR #125) dropped, because
  their absence fails `verify_integration.py` check I7 and therefore fails CI for every open PR.
  While rebasing onto `main` `1f962e2` it was found that the site-rebuild seat had already
  restored them, better: `main`'s `index.html` now carries them twice — once in a proper
  *"Every build in this repository (none deleted)"* card listing every build with a description,
  and once in the footer. **This session's duplicate edit was therefore dropped in favour of
  main's version; nothing is lost.** Recorded so the next session does not re-add it a third
  time. The underlying point stands: `verify_integration.py` was failing on `main` from `97519c7`
  until the site owner restored those links.
- **R-47-2823-F** → **the repository owner** (cannot be done by any session): **Pages must be
  switched from "Deploy from a branch" to "GitHub Actions".** Until that setting changes, the site
  cannot go live no matter how green CI is — see F-47-F above and
  `verify/2026-11-16-2823d556/deploy_diagnosis.json`. This is the single highest-value action
  available to the owner and it takes about ten seconds.
- **R-47-2823-H** → `arena/dfef26dc-nba1` (§48, owns `scripts/**`): `statsdmz.nba.com` added to
  `OFFICIAL_HOSTS` in `verify_integration.py` and to `ALLOWED` in `verify_all.py`. It is an
  official NBA host already cited from this repository's official captures, and its absence was
  failing `verify_integration.py` on `main` twelve times over on the new
  `site/pages/player-logs.html`. Kept in step across both gates on purpose.
- **R-47-2823-G** → every session: stop treating `verify_integration.py` as green on `main`. It was
  **failing on `main`** from commit `97519c7` until the site owner restored the `docs/` links,
  which means every "gates green" claim made in that window was made against a red tree. Re-run
  it after rebasing, and re-run it after a rebase rather than before a push.

### 47.1b Concurrent work on the same two files (resolved, nothing discarded)

Two collisions landed inside twenty minutes of each other, each session unaware of the other. Both
are recorded here rather than papered over:

1. **`.github/workflows/probe-official.yml`.** `arena/4533630f-nba1` (§42.4) added a per-ref
   concurrency group; `arena/d31fb422-nba1` (§46) replaced it with one **global** group
   (`group: probe-official`) because a per-ref group still allows one long probe per branch;
   this session independently removed the `push` trigger and bounded the runtime. All three are
   now on this branch and **all three are kept** — they are complementary, not competing: the
   global group bounds how many probes can run at once, and the trigger change stops branches
   from creating them at all. The merged file is valid YAML with
   `on: [workflow_dispatch, schedule]`, `concurrency.group: probe-official`,
   `timeout-minutes: 25`, and the commit step re-enabled for scheduled runs (the old
   `github.event_name == 'push'` guard was dead code without a head commit).
2. **`index.html`.** see R-47-2823-E above — this session's edit was dropped in favour of the
   site owner's, which is a superset.

### 47.1a THE SHARED BOARD WAS TRUNCATED ON `main` — restored here

Measured with `git cat-file -s <commit>:COORDINATION.md` across recent `main` commits:

```
3f86cba   491255 bytes   <- last good board: 75 "## " headings, 15 registry rows
813e7a9    30764 bytes   <- PR #128, session arena/dfef26dc-nba1,
                            "E06: resolve merge with the 754e9e54 full-cycle build"
e30f541    28690 bytes
```

Commit `813e7a9` collapsed the board to **366 lines**: **71 of 75 top-level headings and 13 of 15
session-registry rows disappeared from `main` in one merge.** Every delivery record from §1 to §45 —
the handoff log, the collision resolutions, the Pages deploy history, the whole audit trail eight
sessions had been writing since 2026-11-13 — was gone.

**Restored, additively.** `verify/2026-11-16-2823d556/restore_board.py` takes the last known-good
blob (`3f86cba`) and appends exactly what the truncated tip had that the good blob did not —
**2 registry rows** (`arena/fbf3ff57-nba1`, `arena/dfef26dc-nba1`) and **1 section** (§48, the
site/shared-output rebuild seat). Everything else in the truncated file was already present in the
good blob, so nothing else needed recovering. Result: **4,865 lines, 76 headings, 0 lost**, then
this session's three blocks on top → **5,060 lines**.

The script refuses to write if any heading from either input would be lost, or if the output would
be shorter than the good input. It is committed so the next session can re-run it rather than
rediscover the problem.

**Not a criticism of `arena/dfef26dc-nba1`.** The identical failure mode hit *this* session at
~02:35Z, when a naive rebase-resolution slicing took the board from 4,566 lines to 73. It was
caught within minutes only because the gates went red, and corrected by restoring `origin/main`.
Two sessions losing the board the same way in two hours is the finding: **COORDINATION.md is a
single file that eight sessions write to, and a `--continue` after a bad conflict resolution
silently commits the damage.** Recommendation in Suggestions: move the board to a directory of
per-session files (`coordination/<session>.md`) with the root file as an index, so a bad merge can
destroy one session's page instead of the whole audit trail.

**R-47-2823-I → every session:** before pushing, run
`python3 -c "import re,sys; s=open('COORDINATION.md',encoding='utf-8').read(); print(len(s.splitlines()), len(re.findall(r'^## ',s,re.flags.M)), len(re.findall(r'^<<<<<<<|^>>>>>>>',s,re.M)))"`
and compare against `origin/main`. If the line count dropped by more than your own additions, or
the marker count is non-zero, **stop and restore** rather than pushing.

**A second `main` regression, found while re-gating and fixed here (R-47-2823-H).** After rebasing
onto `main` `1f962e2`, `verify_integration.py` failed again — this time not on the nav links but on
another session's new page:

```
  - untrusted external host in site/pages/player-logs.html: statsdmz.nba.com
    (https://statsdmz.nba.com/pdfs/20261115/20261115_NYKTOR_book.pdf)   [x12]
```

`statsdmz.nba.com` **is** an official NBA host — it serves the official gamebook and box-score PDFs
that the official game pages link to, and this repository already cites it from its own official
captures (`data/official/results_2026-11-15.json` → `source_gamebook_pdf` / `source_game_pdf`,
`data/official/results_2026-11-14.json`, `data/official/gamebooks/`). The host was simply missing
from the gate's `OFFICIAL_HOSTS` set. It has been added to **both** `scripts/verify_integration.py`
and `scripts/verify_all.py`, because a host one gate accepts and the other rejects is precisely the
split that let R-42-B reach `main`. Both scripts are owned by `arena/dfef26dc-nba1` (§48); logged
to them as R-47-2823-H and made because the brief's rule is "do not merge a broken site".

Net effect of this session's gating: **`verify_integration.py` failed on `main` for two independent
reasons in one hour** (the dropped `docs/` links, then the missing official host). Both are fixed
here; both were caused by work that no single session could see from its own branch, which is the
argument for running the full gate suite after a rebase rather than before a push.

### 47.3 Delivery record

- *(filled in at merge: PR link, merge SHA, Pages status, and the gate results.)*