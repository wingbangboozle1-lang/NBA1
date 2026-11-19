#!/usr/bin/env python3
"""test_settle_seal_cdf3a108.py — pin the pre-tip seal-selection behaviour of
scripts/settle_slate.py (session arena/cdf3a108-nba1, §74 C06).

Why this exists: an amended pre-tip publication (entry type
`pre_tip_publication` with `supersedes_entry`) carries the same archive
basenames in a later archive directory. Settlement must grade the LATEST seal
the ledger committed to — the one whose bytes hash to the recorded digest — and
must REFUSE anything that no entry committed to. These tests run offline on a
throwaway tree; no repository file is touched.

Cases:
  1. two seals -> the amended one is graded
  2. one seal  -> it is graded (backwards compatible with every existing slate)
  3. no seal matches its recorded digest -> exit 4, nothing graded
"""
import hashlib
import json
import os
import sys
import tempfile
import unittest

import importlib.util

_spec = importlib.util.spec_from_file_location(
    "settle_slate",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "scripts", "settle_slate.py"))
ss = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ss)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def canon(d):
    return json.dumps(d, sort_keys=True).encode()


def write(root, rel, obj):
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1)
    return rel


def write_bytes(root, rel, b):
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as f:
        f.write(b)
    return rel


def picks_doc(pick_line):
    return {
        "singles": [{
            "date": "2026-11-19", "game_id": "T1", "matchup": "AWAY@HOME",
            "pick": {"pick_side": "SINGLE-SPREAD-v1", "pick_line": pick_line,
                     "pick_prob": 0.6, "gate": "PASS"},
        }],
        "parlays": [], "sgp_candidates": [],
    }


def lines_doc():
    return {"games": [{"game_id": "T1", "matchup": "AWAY@HOME"}]}


RESULTS = {
    "rows": [{
        "date": "2026-11-19", "game_id": "T1", "home": "HOME", "away": "AWAY",
        "home_pts": 110, "away_pts": 100, "status": "FINAL", "game_status": 3,
        "home_quarters": [28, 27, 30, 25], "away_quarters": [25, 25, 25, 25],
        "ot_periods": 0,
        "source_url": "https://www.nba.com/game/test",
    }]
}

RULES = {"rules": {"single": "TEAM -x.x must win by more than x.x; exactly x.x is a PUSH"}}


def build_tree(root, seals):
    """seals: list of (entry_no, archive_dir, picks_bytes, lines_bytes)."""
    entries = []
    head = "GENESIS"
    for n, d, pb, lb in seals:
        pr = write_bytes(root, f"data/archive/{d}/horizon_picks_2026-11-19.json", pb)
        lr = write_bytes(root, f"data/archive/{d}/horizon_lines_2026-11-19.json", lb)
        e = {
            "entry": n, "type": "pre_tip_publication", "at_utc": f"2026-11-19T0{n}:00Z",
            "files": {pr: sha(pb), lr: sha(lb)},
            "prev": head,
        }
        if n > 1:
            e["supersedes_entry"] = n - 1
        entries.append(e)
        head = sha(canon(e))
    write(root, "data/ledger/ledger.json",
          {"title": "t", "chain_rule": "r", "entries": entries, "head": head})
    write(root, "data/official/results_2026-11-19.json", RESULTS)
    write(root, "data/settlement/settlement_2026-11-14.json", RULES)


class SealSelection(unittest.TestCase):
    def _run(self, root):
        old_root = ss.ROOT
        ss.ROOT = root
        try:
            import contextlib, io
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = ss.main(["--slate", "2026-11-19", "--by", "unit-test"])
            return rc, buf.getvalue()
        finally:
            ss.ROOT = old_root

    def test_amended_seal_is_graded(self):
        with tempfile.TemporaryDirectory() as root:
            orig = json.dumps(picks_doc("HOME -4.5"), indent=1).encode()
            amended = json.dumps(picks_doc("HOME -3.5"), indent=1).encode()
            build_tree(root, [
                (1, "seal_2026-11-19T0545Z", orig, json.dumps(lines_doc(), indent=1).encode()),
                (2, "seal_2026-11-19T1300Z", amended, json.dumps(lines_doc(), indent=1).encode()),
            ])
            rc, out = self._run(root)
            self.assertEqual(rc, 0, out)
            self.assertIn("superseding entry 1", out)
            settle = json.load(open(os.path.join(
                root, "data/settlement/settlement_2026-11-19.json")))
            graded = settle["singles"][0]["pick_line"]
            self.assertEqual(graded, "HOME -3.5",
                             "the amended pre-tip seal must be the one graded")

    def test_single_seal_backwards_compatible(self):
        with tempfile.TemporaryDirectory() as root:
            orig = json.dumps(picks_doc("HOME -4.5"), indent=1).encode()
            build_tree(root, [
                (1, "2026-11-19", orig, json.dumps(lines_doc(), indent=1).encode()),
            ])
            rc, out = self._run(root)
            self.assertEqual(rc, 0, out)
            settle = json.load(open(os.path.join(
                root, "data/settlement/settlement_2026-11-19.json")))
            self.assertEqual(settle["singles"][0]["pick_line"], "HOME -4.5")

    def test_uncommitted_bytes_refused(self):
        with tempfile.TemporaryDirectory() as root:
            orig = json.dumps(picks_doc("HOME -4.5"), indent=1).encode()
            build_tree(root, [
                (1, "2026-11-19", orig, json.dumps(lines_doc(), indent=1).encode()),
            ])
            # tamper: replace the sealed bytes without a ledger commitment
            with open(os.path.join(root, "data/archive/2026-11-19/"
                                       "horizon_picks_2026-11-19.json"), "wb") as f:
                f.write(json.dumps(picks_doc("HOME -9.5"), indent=1).encode())
            rc, out = self._run(root)
            self.assertEqual(rc, 4, out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
