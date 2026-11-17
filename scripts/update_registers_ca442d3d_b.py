#!/usr/bin/env python3
"""Append flags F-CA-05/F-CA-06 and the R19 evidence line (additive)."""
import json

MAIN = "__main__"
F06 = (
    "Session arena/ca442d3d-nba1, 2026-11-17. When the unit-test step was added to the `validate` "
    "job of .github/workflows/pages.yml it failed on `ubuntu-latest` while all 10 modules passed in "
    "the sandbox and in a clean clone of the same commit. Cause, read off the runner through a "
    "branch-scoped diagnostic workflow that commits its own output back into "
    "data/ci/unit-test-diagnostic.md (the runner's log blob host and the check-annotation endpoint "
    "are both unreachable from the agent sandbox, which is why this class of failure has kept being "
    "unreadable in this repo - cf. arena/825bb504-nba1 62.4): the image now ships Python 3.14, where "
    "\"NO TESTS RAN\" is an error, and `scripts/test_gate_roundtrip.py` is not a unittest module at "
    "all - it is a script that ends in a `" + MAIN + "` guard calling `sys.exit(main())`, so "
    "`python3 -m unittest` imported it, ran zero tests and exited 0 on Python 3.11. Its assertions "
    "have therefore never run in any harness, and once they were made to run they found F-CA-05. "
    "`scripts/test_noise_band_refusal.py` is the mirror case: no TestCase and no main guard, it "
    "`sys.exit()`s from module scope, so under `-m unittest` the reported result is whatever the "
    "import happens to produce. The step now selects the runner per file (unittest modules by module "
    "name, script-style files as scripts), treats \"Ran 0 tests\" and \"NO TESTS RAN\" as a failure on "
    "every interpreter, runs every file before exiting so one failure cannot mask the next, and emits "
    "the failing tail as a `::error::` annotation so it is readable through the API. Two follow-ups "
    "for whoever owns those files: give test_noise_band_refusal.py a main guard so it can be run both "
    "ways, and adopt \"a test file that executes zero tests is a build error\" repo-wide."
)

NEW = [
 {"id": "F-CA-05", "severity": "Medium", "status": "resolved",
  "title": "RESOLVED - a capture whose promotion candidates were already in the feed was never reconciled, so the freshness gate blocked on a fully-settled day (the mechanism behind flag F140)",
  "detail": ("Found 2026-11-17 by session arena/ca442d3d-nba1 by *executing* "
             "scripts/test_gate_roundtrip.py as the script it is, and fixed in "
             "engine/promote_official.py. The promoter cleared a day's `snapshot_comparison` only when it "
             "appended a row that run - the guard was `if original != comparison or appended:`, and "
             "`original` is a copy of `comparison`, so the first half is always false. A re-capture of a "
             "day the feed already contained therefore left `promotion_candidates` populated, and "
             "engine/refresh_gate.py (hardened by arena/825bb504-nba1, 62) blocks on a non-empty candidate "
             "list with \"official results for <date> do not reconcile to promoted finals\". That is the "
             "same surface arena/b454a53d-nba1 recorded as F140 - a refresh that captured the 11/16 finals "
             "but neither promoted nor settled them - and it is why a day could still look unsettled to the "
             "gate after being settled by hand. Promotion now reconciles when every listed candidate is in "
             "the feed's own id set, records `reconciled_without_append: true` so the two paths stay "
             "distinguishable, and fails loudly if a candidate is still absent after the append pass. "
             "`python3 scripts/test_gate_roundtrip.py` -> ROUNDTRIP: PASS, promote exit 0, gate exit 0, "
             "14 promoted, 0 blocked."),
  "affected": "engine/promote_official.py, engine/refresh_gate.py, scripts/test_gate_roundtrip.py, data/raw/_capture_results_*.json",
  "links": [{"label": "engine/promote_official.py (repo)",
             "url": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/engine/promote_official.py"},
            {"label": "engine/refresh_gate.py (repo)",
             "url": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/engine/refresh_gate.py"},
            {"label": "End-to-end roundtrip test (repo)",
             "url": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/scripts/test_gate_roundtrip.py"},
            {"label": "Official scoreboard the results captures come from",
             "url": "https://www.nba.com/games?date=2026-11-16"}]},
 {"id": "F-CA-06", "severity": "High", "status": "resolved",
  "title": "RESOLVED - two of this repository's test files could never fail in CI, and the test step this seat added turned main red because of it",
  "detail": F06,
  "affected": ".github/workflows/pages.yml, scripts/test_gate_roundtrip.py, scripts/test_noise_band_refusal.py, data/ci/unit-test-diagnostic.md, .github/workflows/ci-diag-ca442d3d.yml",
  "links": [{"label": "pages.yml (repo)",
             "url": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/.github/workflows/pages.yml"},
            {"label": "Runner diagnostic output (repo)",
             "url": "https://github.com/wingbangboozle1-lang/NBA1/blob/main/data/ci/unit-test-diagnostic.md"},
            {"label": "Failing Pages run on main 44123742284",
             "url": "https://github.com/wingbangboozle1-lang/NBA1/actions/runs/44123742284"}]},
]

R19 = ("Reconciliation path hardened 2026-11-17 by session arena/ca442d3d-nba1 (COORDINATION 65.6): "
       "engine/promote_official.py now resolves a day's promotion candidates against the feed's own id "
       "set, so a settled day cannot sit unreconciled and block the freshness gate (flag F-CA-05, the "
       "mechanism behind F140); proved end-to-end by scripts/test_gate_roundtrip.py (gate exit 0, 14 "
       "promoted, 0 blocked), which now actually executes in CI (F-CA-06).")


def main():
    fp = "data/content/flagged.json"
    fl = json.load(open(fp, encoding="utf-8"))
    have = {i["id"] for i in fl["items"]}
    add = [i for i in NEW if i["id"] not in have]
    fl["items"].extend(add)
    json.dump(fl, open(fp, "w", encoding="utf-8"), indent=1)

    rp = "data/content/requirements.json"
    rq = json.load(open(rp, encoding="utf-8"))
    touched = []
    for r in rq["rows"]:
        if r["id"] == "R19" and "F-CA-05" not in (r.get("evidence") or ""):
            r["evidence"] = f"{(r.get('evidence') or '').rstrip()} {R19}".strip()
            touched.append(r["id"])
    json.dump(rq, open(rp, "w", encoding="utf-8"), indent=1)
    print("flags added:", [i["id"] for i in add], "| total", len(fl["items"]),
          "| requirements touched:", touched or "none")


if __name__ == "__main__":
    main()
