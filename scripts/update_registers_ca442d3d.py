#!/usr/bin/env python3
"""Append this session's measured evidence to the two content registers.

Additive by design: no existing row is deleted and no existing flag id is
overwritten - evidence text is appended to the row it belongs to, and new flags
carry this session's own prefix (F-CA-*) so a crowded board cannot collide on a
number. Run: python3 scripts/update_registers_ca442d3d.py
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = "session arena/ca442d3d-nba1 (COORDINATION \u00a763)"

REQ = {
 "R01": ("Refresh-run evidence, measured 2026-11-17 by " + S + ": the scheduled run on main "
         "(44078416610, ~12:1xZ) still reports \"expected 30 team rows, parsed 0\" for "
         "S1/S2/S8/S9/S10. The cause is now measured rather than assumed: a runner fetched all five "
         "pages at HTTP 200 with the bytes stored content-addressed "
         "(data/raw/session-ca442d3d/pages/*.json.gz + sidecars). The standings page is 254,060 bytes "
         "and contains \"wins\" 0 times, \"losses\" 0 times, \"team\" 0 times; the three team-stat pages "
         "(322,550 / 322,487 / 322,487 bytes) likewise contain no team-record keys - the tables are "
         "rendered client-side, so no HTML parser can read them (flag F-CA-02). The same runner read of "
         "www.nba.com/games?date=YYYY-MM-DD does carry the full scoreboard JSON (gameStatus, per-team "
         "score, per-period scores and win/loss records), which makes the per-day scoreboard page the "
         "parseable official source for schedule, results and records (R02). Push-triggered refresh runs "
         "on session branches are cancelled by the shared refresh-official-global concurrency group "
         "(3 of 3 this session) - flag F-CA-04."),
 "R02": ("Extended 2026-11-17 by " + S + ": scripts/build_results_feed_ca442d3d.py re-cuts a game day "
         "from a stored official capture and cross-checks it. On 2026-11-16 it emitted 8 of 8 settled "
         "rows, 0 quarter-sum failures, and agreed with all 8 rows of the committed feed and with all 8 "
         "finals embedded in data/settlement/settlement_2026-11-16.json. On 2026-11-17 it emitted 0 "
         "settled rows and excluded all 5 games as not-final (they had not tipped) - nothing inferred. "
         "Output: data/official/results_feed_2026_11_16_ca442d3d.json."),
 "R04": ("Chain rule moved into the scheduled path by " + S + ": engine/promote_official.py runs the "
         "consecutive-edition diff as part of promotion (diff_injury_chain) and carries row_audit + "
         "player_rows into the promotion proof, so status-change detection no longer depends on a session "
         "remembering to run engine/injury_diff.py by hand; engine/fetch_official.py capture_injury is "
         "index-driven (every edition the official index lists, newest first, capped per run, "
         "already-archived editions skipped) instead of four hard-coded clock times; and the F-X01 "
         "row-dropping defect is fixed (flag F-CA-01). The row stays partial on measured grounds: the "
         "newest edition committed in this repository is still 2026-11-16 01:15 PM, because every "
         "capture run this session armed through the shared refresh workflow was cancelled (F-CA-04). "
         "The code path is in place and the next refresh that is not cancelled produces the 11/17 diffs."),
 "R09": ("Wired into the legacy engine by " + S + ": engine/pipeline.py pins params['hca'] to "
         "sigma_margin * Phi^-1(measured home-win rate) computed by engine/hca.compute_hca over the "
         "official completed-game corpus that run read - 0.5135 over 74 games -> 0.59 pts, replacing the "
         "fitted 3.51 - and writes provenance to data/hca_measured.json. Re-measured on the current feed "
         "(205 decided games through 2026-11-16): rate 0.5171 (106/205), sigma_margin 16.868, "
         "HCA 0.72 pts, Wilson 95% lower bound 0.4490 - "
         "data/derived/hca_pin_2026_11_17_ca442d3d.json. The pin published on the site (0.5204 / 0.87 "
         "pts) was measured on a different sample; the numbers are listed side by side, not blended - "
         "flag F-CA-03 asks the register owner to name one corpus of record. reference_line's flat 2.0 "
         "is left alone deliberately: that number is the deliberately naive benchmark the strategies are "
         "scored against, not a claim about home court."),
 "R30": ("Line-by-line pass by " + S + " over the injury-parse and capture path: "
         "engine/injury_diff.py (parse_rows, load_edition, diff_editions, main), engine/injury_cells.py, "
         "engine/fetch_official.py (capture_injury and the results capture), engine/promote_official.py "
         "(promote_injuries, diff_injury_chain), engine/pipeline.py (the HCA pin) and "
         "engine/model_v2.py:load_results. Fixed F-X01 in the engine; found and fixed a case-sensitive "
         "Final marker in this session's own capture script before any value depended on it; measured the "
         "shell-page parse cause (F-CA-02) and the concurrency cancellation (F-CA-04). Not reviewed line "
         "by line: docs/**, command-center/** and the other builds' page templates."),
 "R32": ("Verification channel measured 2026-11-17 by " + S + ": nba.com and ak-static are unreachable "
         "from this sandbox (a direct request returns no route), so every official value this session "
         "committed comes from either (a) a first-hand read of the official page through the agent fetch "
         "channel - www.nba.com/schedule, /games?Date=2026-11-16 and the official.nba.com injury index, "
         "read at 15:4x-15:5x UTC - or (b) bytes captured by a runner and stored content-addressed under "
         "data/raw/session-ca442d3d/ with a sha256 and retrieval timestamp per sidecar. Any value the page "
         "does not print is left null by scripts/build_results_feed_ca442d3d.py and reported, never "
         "filled in."),
}

FLAGS = [
 {"id": "F-CA-01", "severity": "High", "status": "resolved",
  "title": "RESOLVED - engine/injury_diff.py silently dropped 7 player rows per injury-report edition (F-X01)",
  "detail": ("Fixed 2026-11-17 by " + S + ". Reproduced first-hand on the committed official PDF bytes "
             "before any edit: for Injury-Report_2026-11-16_01_15PM the engine's word-band parser returned "
             "80 rows and reported unparsed: 0 while seven player rows were absent from its output - Jerome "
             "(Ty), Pippen Jr. (Scotty), Post (Quinten), Saunders (Richie) and Stewart (Isaiah) for Memphis "
             "in MEM@WAS, and Reese (Julian) and Watford (Trendon) for New Orleans in GSW@NOP. The "
             "per-clipped-rectangle reader that session arena/07920bdc-nba1 had published as a verification "
             "script is now ported into the engine as engine/injury_cells.py and is the primary pass of "
             "load_edition; the word-band parser is kept as a cross-check, and every edition carries "
             "row_audit with silent_drop_detected, so a row one reader sees and the published output does "
             "not is an error rather than a silent omission. Verified on the same bytes after the change: 87 "
             "rows / 76 player rows, 0 unassigned cell text, and all 100 archived editions parse with no "
             "disagreement between the two readers. Pinned by 10 tests in scripts/test_injury_diff.py, which "
             "now run in CI on every pull request."),
  "affected": "engine/injury_diff.py, engine/injury_cells.py, scripts/test_injury_diff.py, .github/workflows/pages.yml",
  "links": [{"label": "engine/injury_cells.py (repo)",
             "url": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/engine/injury_cells.py"},
            {"label": "engine/injury_diff.py (repo)",
             "url": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/engine/injury_diff.py"},
            {"label": "Official injury-report index (source of the archived PDFs)",
             "url": "https://official.nba.com/nba-injury-report-2026-27-season/"}]},
 {"id": "F-CA-02", "severity": "Medium", "status": "open",
  "title": "The standings page and all three team-stat pages embed no table data - the refresh \"parsed 0\" is a property of the official page, not of our parser",
  "detail": ("Measured 2026-11-17 by " + S + " on bytes a runner fetched at HTTP 200 and stored "
             "content-addressed under data/raw/session-ca442d3d/ (sha256 and retrieval timestamp in each "
             "sidecar): www.nba.com/standings (254,060 bytes) contains the strings \"wins\", \"losses\" and "
             "\"team\" zero times, and www.nba.com/stats/teams/{traditional,opponent,advanced} (322,550 / "
             "322,487 / 322,487 bytes) contain none of them either. Each ships a __NEXT_DATA__ shell whose "
             "table is filled client-side. engine/refresh_gate.py's BLOCK on those five sources is therefore "
             "correct behaviour for an HTML reader and cannot be fixed by parsing harder. The parseable "
             "official source for records, scores and per-period scores is "
             "www.nba.com/games?date=YYYY-MM-DD, whose embedded scoreboard JSON carries gameStatus, "
             "periods[] and wins/losses - proved by scripts/build_results_feed_ca442d3d.py, which read 8/8 "
             "finals with their quarter lines out of that JSON for 2026-11-16. A decision is needed and was "
             "not taken here: whether the refresh should promote standings and team-record rows derived from "
             "per-day scoreboard captures, which changes what \"the official standings source\" means."),
  "affected": "engine/refresh_gate.py, engine/fetch_official.py, engine/promote_official.py, R01, R20",
  "links": [{"label": "Official standings page (the shell)", "url": "https://www.nba.com/standings"},
            {"label": "Official team traditional page (the shell)",
             "url": "https://www.nba.com/stats/teams/traditional"},
            {"label": "Official per-day scoreboard (embedded JSON)",
             "url": "https://www.nba.com/games?date=2026-11-16"}]},
 {"id": "F-CA-03", "severity": "Medium", "status": "needs review",
  "title": "Four different home-court pins are in the repository, each measured on a different sample; no corpus of record is named",
  "detail": ("Measured 2026-11-17 by " + S + ": 0.5204 -> 0.87 pts (102/196 home/road games from the "
             "standings capture; session arena/23ec1e32-nba1 published this as \"the\" pin); 0.5263 -> "
             "1.108 pts (190 finals through 2026-11-15, data/derived/measured_constants_2026_27.json); "
             "0.5171 -> 0.72 pts (205 decided rows through 2026-11-16, quarter sums asserted, "
             "data/derived/hca_pin_2026_11_17_ca442d3d.json); 0.5135 -> 0.59 pts (74-game train corpus, "
             "the legacy engine pin this session wired into engine/pipeline.py). All four are arithmetically "
             "right on their own sample - the spread is sample choice, not error. It matters because the pin "
             "moves every spread and every total, and because a reader cannot currently tell which number a "
             "published line used. Proposed for the register owner: name one corpus of record (this seat "
             "proposes the per-game feed through the latest settled game day, 0.5171 / 0.72 pts as of "
             "2026-11-16), print the sample beside every pin, and re-derive it when each game day settles. "
             "Nothing was blended or overwritten here."),
  "affected": "data/derived/measured_constants_2026_27.json, data/derived/hca_pin_2026_11_17_ca442d3d.json, data/hca_measured.json, data/derived/horizon_lines.json",
  "links": [{"label": "Re-measured pin on 205 games (repo)",
             "url": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/data/derived/hca_pin_2026_11_17_ca442d3d.json"},
            {"label": "\u00a761 delivery record for the published 0.5204 pin (repo)",
             "url": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/COORDINATION.md"},
            {"label": "Official scoreboard the feed rows come from", "url":"https://www.nba.com/games"}]},
 {"id": "F-CA-04", "severity": "Medium", "status": "open",
  "title": "Push-triggered refresh runs on session branches are cancelled by the shared concurrency group, so session-armed captures never land",
  "detail": ("Measured 2026-11-17 by " + S + ": .github/workflows/refresh-data.yml sets "
             "concurrency.group: refresh-official-global with cancel-in-progress: true - one slot shared by "
             "every branch (added by session arena/c348e6c7-nba1, COORDINATION \u00a747.2, to stop run "
             "starvation, and kept on top of PR #117). With several sessions pushing in the same minutes, "
             "3 of 3 refresh runs armed from arena/ca442d3d-nba1 were cancelled within about two minutes, "
             "each in favour of another branch's run. The consequence is not cosmetic: the injury-PDF "
             "capture, promotion and consecutive-edition diff this workflow performs are exactly what would "
             "move R04's chain to 2026-11-17, so that row cannot close while every session arms the same "
             "single slot. Proposed (owner of the workflow file, not applied here): scope the group to the "
             "git ref for non-main branches so only the scheduled main runs share one slot. This session's "
             "own capture workflow uses a per-ref group and completed and committed back to the branch "
             "(run 44120656545), which is the evidence that the alternative works."),
  "affected": ".github/workflows/refresh-data.yml, R01, R04",
  "links": [{"label": "Cancelled run 44119703033",
             "url": "https://github.com/wingbangboozle1-lang/NBA1/actions/runs/44119703033"},
            {"label": "Completed per-branch capture run 44120656545",
             "url": "https://github.com/wingbangboozle1-lang/NBA1/actions/runs/44120656545"},
            {"label": "refresh-data.yml (repo)",
             "url": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/.github/workflows/refresh-data.yml"}]},
]


def main() -> int:
    rp = os.path.join(ROOT, "data", "content", "requirements.json")
    rq = json.load(open(rp, encoding="utf-8"))
    rows = {r["id"]: r for r in rq["rows"]}
    touched = []
    for k, v in REQ.items():
        r = rows[k]
        ev = (r.get("evidence") or "").rstrip()
        if S.split()[1] in ev and "2026-11-17" in ev:
            continue                      # already appended (idempotent re-run)
        r["evidence"] = f"{ev} {v}".strip() if ev else v
        touched.append(k)
    json.dump(rq, open(rp, "w", encoding="utf-8"), indent=1)

    fp = os.path.join(ROOT, "data", "content", "flagged.json")
    fl = json.load(open(fp, encoding="utf-8"))
    have = {i.get("id") for i in fl["items"]}
    added = [i for i in FLAGS if i["id"] not in have]
    fl["items"].extend(added)
    json.dump(fl, open(fp, "w", encoding="utf-8"), indent=1)
    print(f"requirements rows appended: {touched or 'none (already present)'}")
    print(f"flags appended: {[i['id'] for i in added] or 'none'}; total {len(fl['items'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
