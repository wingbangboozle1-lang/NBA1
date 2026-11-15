#!/usr/bin/env python3
"""Recompute the home-court pin and the travel-term status from the committed captures.

Writes data/derived/home_court_pin.json, which is what the day-roll page renders and what the
next line freeze reads. Pure arithmetic on files already in the repository: no fetch, no
estimation from memory. Run after any day roll.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "engine"))
import home_court                                                   # noqa: E402

d = home_court.pin(write=True)
print("measured home win rate  results feed : %s (%d games) -> HCA %s pts"
      % (d["measured"]["results_feed"]["home_win_rate"], d["measured"]["results_feed"]["games"],
         d["measured"]["results_feed"]["implied_hca_points"]))
print("measured home win rate  standings HOME: %s (%d home games) -> HCA %s pts"
      % (d["measured"]["official_standings_home_column"]["home_win_rate"],
         d["measured"]["official_standings_home_column"]["home_games"],
         d["measured"]["official_standings_home_column"]["implied_hca_points"]))
print("assumption currently in the published lines: %s pts ; fitted on residuals: %s"
      % (d["assumption_replaced"]["value_points"],
         (d["fitted_on_residials"] or {}).get("est")))
print("PINNED HCA:", d["pinned_hca_points"], "pts  ->", home_court.PIN_FILE[len(home_court.ROOT) + 1:])
print("travel:", d["travel"]["status"])
print(json.dumps({"adopted_for_pricing": False}, indent=0) and
      "adoption: adopted_for_pricing is NOT set, so no already-published line moves; set it only "
      "when a new freeze is taken")
