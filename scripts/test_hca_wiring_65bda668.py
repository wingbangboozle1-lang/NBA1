#!/usr/bin/env python3
"""R09 residual (COORDINATION section 76): the legacy reference line reads the
measured home-court pin, never a literal 2.0.

Checks:
  1. measured_hca_points() returns data/hca_measured.json's hca_points.
  2. A missing or malformed pin file raises (no silent flat fallback).
  3. reference_line() adds exactly the measured HCA to the home margin.
  4. No engine/ or scripts/ source still passes flat_hca=2.0 at a call site.
"""
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "engine"))

import model_core  # noqa: E402
from common import ABBR  # noqa: E402

PIN = os.path.join(ROOT, "data", "hca_measured.json")


def _table():
    block = []
    for i, name in enumerate(sorted(ABBR)):
        row = {"team": name, "gp": 10, "w": 5, "l": 5,
               "ortg": 105.0 + (i % 7), "drtg": 108.0 - (i % 5),
               "pace": 99.0 + (i % 4), "netr": 0.0}
        for k in ("tov_pct", "efg_pct", "ts_pct", "oreb_pct", "dreb_pct",
                  "reb_pct", "ast_pct", "pie", "poss"):
            row[k] = 0.5
        block.append(row)
    return model_core.RatingTable(block, "TEST", "TEST", "test")


class HcaWiringTest(unittest.TestCase):
    def test_reads_pinned_value(self):
        with open(PIN, encoding="utf-8") as fh:
            expected = float(json.load(fh)["hca_points"])
        self.assertEqual(model_core.measured_hca_points(), expected)

    def test_missing_file_raises(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(RuntimeError):
                model_core.measured_hca_points(os.path.join(d, "absent.json"))

    def test_malformed_value_raises(self):
        with tempfile.TemporaryDirectory() as d:
            for bad in ({"hca_points": None}, {"hca_points": "0.5"}, {"hca_points": True}, {}):
                p = os.path.join(d, "pin.json")
                with open(p, "w", encoding="utf-8") as fh:
                    json.dump(bad, fh)
                with self.assertRaises(RuntimeError, msg=repr(bad)):
                    model_core.measured_hca_points(p)

    def test_reference_line_uses_measured_hca(self):
        t = _table()
        names = sorted(ABBR.values())
        home, away = names[0], names[1]
        hca = model_core.measured_hca_points()
        ref = model_core.reference_line(t, home, away)
        base = model_core.base_line(t, home, away, shrink_k=None)
        self.assertAlmostEqual(ref["hca"], hca, places=9)
        self.assertAlmostEqual(ref["margin"] - base["margin"], hca, places=9)
        self.assertAlmostEqual(ref["h_pts"] - base["h_pts"], hca / 2.0, places=9)

    def test_explicit_override_still_honoured(self):
        t = _table()
        names = sorted(ABBR.values())
        ref = model_core.reference_line(t, names[0], names[1], flat_hca=3.5)
        base = model_core.base_line(t, names[0], names[1], shrink_k=None)
        self.assertAlmostEqual(ref["margin"] - base["margin"], 3.5, places=9)

    def test_no_literal_flat_hca_call_site_remains(self):
        offenders = []
        for sub in ("engine", "scripts"):
            for dp, _, files in os.walk(os.path.join(ROOT, sub)):
                for f in files:
                    if not f.endswith(".py") or f == os.path.basename(__file__):
                        continue
                    path = os.path.join(dp, f)
                    with open(path, encoding="utf-8") as fh:
                        for n, line in enumerate(fh, 1):
                            if "flat_hca=2.0" in line.replace(" ", ""):
                                offenders.append(f"{os.path.relpath(path, ROOT)}:{n}")
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
