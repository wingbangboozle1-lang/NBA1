#!/usr/bin/env python3
"""Recompute the pinned home-court advantage from the official standings.

Requirement line this answers: "Pin home-court advantage to the measured home-win
rate instead of fitting it freely." (register R09)

The anchor the model is pinned to is `home_wins / home_games` over the official
standings HOME and ROAD columns. This script holds the 30 standings rows as
transcribed from https://www.nba.com/standings in this session (2026-11-16,
14:3xZ) and:

  1. re-adds them, checking home_wins == road_losses and road_wins == home_losses
  2. prints the anchor the CURRENT standings imply
  3. compares it with the anchor the model actually used
  4. explains any difference by name

It deliberately does NOT write the model input. Changing a pinned model input is
an origination step (scripts/build_horizon_v2.py) and belongs to a run that can
also read the official pages; doing it here would put a hand-edited number into
the published lines.

Run: python3 verify/2026-11-16-23b323a3/verify_hca_anchor.py
"""
import json, math, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Transcribed by hand from https://www.nba.com/standings (2026-27 Regular Season)
# at 2026-11-16T14:3xZ. Columns: abbr, W, L, HOME 'W-L', ROAD 'W-L'.
STANDINGS = [
    ("BOS", 11, 2, "6-0", "5-2"), ("PHI", 11, 3, "6-2", "5-1"), ("DET", 8, 4, "3-2", "5-2"),
    ("ATL", 8, 6, "3-3", "5-3"), ("MIA", 7, 6, "3-3", "4-3"), ("NYK", 7, 6, "4-3", "3-3"),
    ("CLE", 7, 7, "5-2", "2-5"), ("ORL", 5, 7, "1-4", "4-3"), ("TOR", 5, 8, "2-4", "3-4"),
    ("IND", 5, 9, "2-4", "3-4"), ("CHA", 4, 9, "3-4", "1-5"), ("WAS", 4, 10, "2-4", "2-6"),
    ("BKN", 3, 9, "1-3", "2-6"), ("CHI", 3, 9, "1-4", "2-5"), ("MIL", 1, 13, "1-7", "0-6"),
    ("SAS", 12, 2, "5-2", "7-0"), ("LAL", 12, 2, "5-1", "7-1"), ("HOU", 11, 3, "7-1", "4-2"),
    ("POR", 9, 3, "3-2", "6-1"), ("MIN", 9, 4, "5-2", "4-2"), ("MEM", 9, 4, "3-4", "6-0"),
    ("OKC", 9, 5, "5-0", "4-5"), ("DEN", 7, 4, "2-2", "4-2"), ("GSW", 8, 5, "6-1", "2-4"),
    ("DAL", 7, 7, "5-2", "2-5"), ("PHX", 5, 7, "5-4", "0-3"), ("LAC", 4, 8, "4-3", "0-5"),
    ("NOP", 4, 10, "3-6", "1-4"), ("SAC", 1, 12, "0-8", "1-4"), ("UTA", 1, 13, "1-7", "0-6"),
]

Phi = lambda x: 0.5 * (1 + math.erf(x / math.sqrt(2)))
def probit(p):
    lo, hi = -8.0, 8.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if Phi(mid) < p:
            lo = mid
        else:
            hi = mid
    return lo

fails = []
hw = hl = rw = rl = 0
neutral = []
for ab, w, l, h, r in STANDINGS:
    a, b = map(int, h.split("-")); c, d = map(int, r.split("-"))
    hw += a; hl += b; rw += c; rl += d
    if a + b + c + d != w + l:
        neutral.append((ab, w, l, h, r, w + l - (a + b + c + d)))

if hw != rl:
    fails.append("home_wins %d != road_losses %d" % (hw, rl))
if rw != hl:
    fails.append("road_wins %d != home_losses %d" % (rw, hl))

hg = hw + hl
rate = hw / hg

used = json.load(open(os.path.join(ROOT, "data/derived/horizon_lines_v2.json"),
                     encoding="utf-8"))["_meta"]["home_court_anchor"]
sigma = used["sigma_margin_used"]
hca_now = sigma * probit(rate)

print("standings rows           : %d" % len(STANDINGS))
print("home W-L                 : %d-%d  (%d games)" % (hw, hl, hg))
print("road W-L                 : %d-%d  (%d games)" % (rw, rl, rw + rl))
print("cross-checks             : home_wins==road_losses %s, road_wins==home_losses %s"
      % (hw == rl, rw == hl))
print("rows where HOME+ROAD != W+L (neutral-site games): %s" % (neutral or "none"))
print()
print("anchor from THIS read    : %.4f  (%d/%d)" % (rate, hw, hg))
SC = used["standings_cross_check"]
print("anchor the model used    : %.4f  (%d/%d games)  [the standings-anchor cross-check; "
      "the final-score corpus separately measures %.4f on %d games]"
      % (SC["home_win_rate"], round(SC["home_games"] * SC["home_win_rate"]), SC["home_games"],
         used["measured_home_win_rate_from_final_scores"], used["games_measured"]))
# F113's mislabeling: the top-level rate and the cross-check rate must be the
# same number now that both are measured on the same finished games.
if abs(used["measured_home_win_rate"] - SC["home_win_rate"]) > 5e-5:
    print("  ...and the top-level anchor field says %.4f, so the two standings-derived "
          "numbers in this file disagree with each other: see F113."
          % used["measured_home_win_rate"])
    fails.append("top-level anchor rate disagrees with standings_cross_check (F113 still open)")
else:
    print("  ...and the top-level anchor field says %.4f: the two standings-derived "
          "numbers agree (F113's mislabeling is resolved)."
          % used["measured_home_win_rate"])
print("sigma_margin used        : %.2f" % sigma)
print("HCA from this read       : %.2f points" % hca_now)
print("HCA published            : %.2f points" % used["hca_points"])
if abs(hca_now - used["hca_points"]) > 0.011:
    fails.append("published hca_points does not match sigma * probit(fresh standings rate)")
print()
# Can the difference be explained exactly, by name?
newly = json.load(open(os.path.join(ROOT, "data/official/results_2026-11-15.json"),
                      encoding="utf-8"))["rows"]
late = [r for r in newly if r["game_id"] in ("0022600242", "0022600243", "0022600244")]
away_wins = [r for r in late if r["away_pts"] > r["home_pts"]]
# The capture records rates and game counts, not raw win counts for every column, so the
# pre-capture win totals are reconstructed from its own published rate x its own game count.
# That is arithmetic on the capture's own numbers, not a new measurement.
_scw = round(SC["home_games"] * SC["home_win_rate"])          # home wins at capture
_scrw = round(SC["home_games"] * SC["road_win_rate"])          # road wins at capture
print("  capture-implied at read  : home %d/%d, road wins %d"
      % (_scw, SC["home_games"], _scrw))
dg = hg - SC["home_games"]; dw = hw - _scw; drw = rw - _scrw
print("delta since that capture : %+d games, %+d home wins, %+d road wins"
      % (dg, dw, drw))
explained = (dg == len(late) and dw == 0 and drw == len(away_wins) == len(late))
reconciled = (dg == 0 and dw == 0 and drw == 0)
if explained:
    print("explained by the %d 11/15 games that finished after the capture (%s, all away wins): %s"
          % (len(late), ", ".join("%s@%s" % (r["away"], r["home"]) for r in late), explained))
elif reconciled:
    # The anchor this script compares against was re-captured after every
    # 11/15 final was in (standings_2026-11-16_1835Z_23ec1e32.json), so the
    # drift against this script's own 14:3xZ read is zero by construction.
    # That is the reconciled state, not a stale one: both reads transcribed
    # the same 102-94 / 94-102 standings, so no game finished between them.
    print("reconciled: the published anchor already includes every game in this "
          "script's own 14:3xZ standings read (both reads are 102-94 / 94-102)")
else:
    print("explained by the %d 11/15 games that finished after the capture (%s, all away wins): %s"
          % (len(late), ", ".join("%s@%s" % (r["away"], r["home"]) for r in late), explained))
    fails.append("the anchor drift is NOT explained by the late 11/15 finals; re-read the standings")

if fails:
    result = "FAILURES: %d" % len(fails)
elif reconciled:
    result = "the published anchor is current and reconciled (zero drift against this read)"
else:
    result = "the published anchor is stale but exactly reconcilable"
print("\nRESULT: %s" % result)
for f in fails:
    print("  -", f)
print("NOTE: this script does not rewrite the model input. Re-derivation belongs to "
      "scripts/build_horizon_v2.py on a run that reads the official pages (finding F113).")
sys.exit(1 if fails else 0)
