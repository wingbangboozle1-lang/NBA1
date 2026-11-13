"""NBA1 — originate lines, build strategies, generate picks.

This package is the self-contained engine for the NBA1 project. It takes the
verified seed data captured from official sources (see data/*.json) and:

  * originates our own NBA lines (spreads, totals, player props),
  * defines betting strategies (single bet, parlay, player-prop combos),
  * runs validation gates (edge, sample size, correlation, skill significance),
  * computes correlation values and removes luck via shrinkage,
  * generates picks for every upcoming slate (up to 3 days ahead),
  * tracks injuries -> rotation minutes -> production and game-flow.

No manual input is required: run ``python -m nba1.run`` to regenerate all
derived data files under data/.
"""

__version__ = "1.0.0"
