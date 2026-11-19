# Test discovery import-safety fix — 2026-11-19

## Finding

`python3 -m unittest discover -s scripts -p 'test_*.py'` originally failed to import `scripts/test_noise_band_refusal.py`. That file ran its assertions at module import and called `sys.exit(0)`, which unittest reported as an import error (`SystemExit: 0`). The same script's standalone assertions all passed, so this was a test-runner integration defect, not evidence of a failed R10 rule.

## Change

Moved the existing six-case verification into `main()` and added the standard `if __name__ == '__main__'` entry point. Direct execution retains the prior checks and exit-code behavior; importing the module no longer runs the cases or exits the test process. Also used context managers for the two JSON files read by this script.

## Verification

- `python3 scripts/test_noise_band_refusal.py` — PASS; 0 assertion failures.
- `python3 -m unittest discover -s scripts -p 'test_*.py'` — PASS; 109 tests, 3 skipped.
- `git diff --check` — PASS.

The suite emitted pre-existing `ResourceWarning`s from `test_capture_official_ca442d3d.py` and `test_promote_official.py`; they did not fail the suite and are outside this task's file scope.

No NBA data, model values, published picks, or source claims were changed. This fix does not validate any betting strategy or change the bet-surface gates.
