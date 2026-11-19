# 2026-11-17 / 11-18 official game logs, quarter lines and rotation — read from stored bytes

Run at 2026-11-19T06:01:12Z by `scripts/e3d25abc_game_logs.py` (session `arena/e3d25abc-nba1`, §68 Q04/Q05/Q06).

## Games parsed

| Day | Game | Final | Player rows | Appeared | Page digest | Gamebook archived |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-11-17 | NYK@TOR (0022600253) | 111-102 | 27 | 21 | verified | yes |
| 2026-11-17 | POR@MIN (0022600254) | 105-106 | 25 | 19 | verified | yes |
| 2026-11-17 | DET@SAS (0022600255) | 105-93 | 23 | 19 | verified | yes |
| 2026-11-17 | CHA@LAL (0022600256) | 114-118 | 26 | 22 | verified | yes |
| 2026-11-17 | UTA@LAC (0022600257) | 132-107 | 25 | 22 | verified | yes |
| 2026-11-18 | MEM@CLE (0022600258) | 124-121 | 25 | 22 | verified | yes |
| 2026-11-18 | HOU@IND (0022600259) | 119-104 | 27 | 27 | verified | yes |
| 2026-11-18 | MIL@MIA (0022600260) | 130-137 | 27 | 24 | verified | yes |
| 2026-11-18 | PHI@ORL (0022600261) | 121-116 | 25 | 19 | verified | yes |
| 2026-11-18 | CHI@BKN (0022600262) | 137-107 | 26 | 26 | verified | yes |
| 2026-11-18 | WAS@TOR (0022600263) | 103-99 | 26 | 21 | verified | yes |
| 2026-11-18 | DET@NOP (0022600264) | 122-109 | 25 | 21 | verified | yes |
| 2026-11-18 | ATL@OKC (0022600265) | 117-112 | 24 | 21 | verified | yes |
| 2026-11-18 | BOS@DEN (0022600266) | 101-105 | 27 | 22 | verified | yes |
| 2026-11-18 | GSW@DAL (0022600267) | 94-116 | 25 | 25 | verified | yes |
| 2026-11-18 | UTA@LAL (0022600268) | 109-97 | 28 | 25 | verified | yes |
| 2026-11-18 | PHX@SAC (0022600269) | 128-107 | 26 | 26 | verified | yes |

## Cross-check against the settlement seat's results feed

* **2026-11-17**: 5 game(s) compared, **5 agree on score and every quarter**, 0 disagree
* **2026-11-18**: 12 game(s) compared, **12 agree on score and every quarter**, 0 disagree

## Assertion failures

none

<details><summary>full JSON</summary>

```json
{
 "run_at_utc": "2026-11-19T06:01:12Z",
 "games": [
  {
   "date": "2026-11-17",
   "game_id": "0022600253",
   "matchup": "NYK@TOR",
   "final": "111-102",
   "players_logged": 27,
   "played": 21,
   "digest_verified": true,
   "gamebook": true
  },
  {
   "date": "2026-11-17",
   "game_id": "0022600254",
   "matchup": "POR@MIN",
   "final": "105-106",
   "players_logged": 25,
   "played": 19,
   "digest_verified": true,
   "gamebook": true
  },
  {
   "date": "2026-11-17",
   "game_id": "0022600255",
   "matchup": "DET@SAS",
   "final": "105-93",
   "players_logged": 23,
   "played": 19,
   "digest_verified": true,
   "gamebook": true
  },
  {
   "date": "2026-11-17",
   "game_id": "0022600256",
   "matchup": "CHA@LAL",
   "final": "114-118",
   "players_logged": 26,
   "played": 22,
   "digest_verified": true,
   "gamebook": true
  },
  {
   "date": "2026-11-17",
   "game_id": "0022600257",
   "matchup": "UTA@LAC",
   "final": "132-107",
   "players_logged": 25,
   "played": 22,
   "digest_verified": true,
   "gamebook": true
  },
  {
   "date": "2026-11-18",
   "game_id": "0022600258",
   "matchup": "MEM@CLE",
   "final": "124-121",
   "players_logged": 25,
   "played": 22,
   "digest_verified": true,
   "gamebook": true
  },
  {
   "date": "2026-11-18",
   "game_id": "0022600259",
   "matchup": "HOU@IND",
   "final": "119-104",
   "players_logged": 27,
   "played": 27,
   "digest_verified": true,
   "gamebook": true
  },
  {
   "date": "2026-11-18",
   "game_id": "0022600260",
   "matchup": "MIL@MIA",
   "final": "130-137",
   "players_logged": 27,
   "played": 24,
   "digest_verified": true,
   "gamebook": true
  },
  {
   "date": "2026-11-18",
   "game_id": "0022600261",
   "matchup": "PHI@ORL",
   "final": "121-116",
   "players_logged": 25,
   "played": 19,
   "digest_verified": true,
   "gamebook": true
  },
  {
   "date": "2026-11-18",
   "game_id": "0022600262",
   "matchup": "CHI@BKN",
   "final": "137-107",
   "players_logged": 26,
   "played": 26,
   "digest_verified": true,
   "gamebook": true
  },
  {
   "date": "2026-11-18",
   "game_id": "0022600263",
   "matchup": "WAS@TOR",
   "final": "103-99",
   "players_logged": 26,
   "played": 21,
   "digest_verified": true,
   "gamebook": true
  },
  {
   "date": "2026-11-18",
   "game_id": "0022600264",
   "matchup": "DET@NOP",
   "final": "122-109",
   "players_logged": 25,
   "played": 21,
   "digest_verified": true,
   "gamebook": true
  },
  {
   "date": "2026-11-18",
   "game_id": "0022600265",
   "matchup": "ATL@OKC",
   "final": "117-112",
   "players_logged": 24,
   "played": 21,
   "digest_verified": true,
   "gamebook": true
  },
  {
   "date": "2026-11-18",
   "game_id": "0022600266",
   "matchup": "BOS@DEN",
   "final": "101-105",
   "players_logged": 27,
   "played": 22,
   "digest_verified": true,
   "gamebook": true
  },
  {
   "date": "2026-11-18",
   "game_id": "0022600267",
   "matchup": "GSW@DAL",
   "final": "94-116",
   "players_logged": 25,
   "played": 25,
   "digest_verified": true,
   "gamebook": true
  },
  {
   "date": "2026-11-18",
   "game_id": "0022600268",
   "matchup": "UTA@LAL",
   "final": "109-97",
   "players_logged": 28,
   "played": 25,
   "digest_verified": true,
   "gamebook": true
  },
  {
   "date": "2026-11-18",
   "game_id": "0022600269",
   "matchup": "PHX@SAC",
   "final": "128-107",
   "players_logged": 26,
   "played": 26,
   "digest_verified": true,
   "gamebook": true
  }
 ],
 "problems": [],
 "crosscheck_vs_results_feed": [
  {
   "date": "2026-11-17",
   "games_compared": 5,
   "full_agreement": 5,
   "disagreements": 0,
   "detail": [
    {
     "game_id": "0022600253",
     "matchup": "NYK@TOR",
     "score_agrees": true,
     "quarters_agree": true,
     "their_quarters": {
      "away": [
       23,
       31,
       26,
       31
      ],
      "home": [
       29,
       21,
       33,
       19
      ]
     },
     "my_quarters": {
      "away": [
       23,
       31,
       26,
       31
      ],
      "home": [
       29,
       21,
       33,
       19
      ]
     }
    },
    {
     "game_id": "0022600254",
     "matchup": "POR@MIN",
     "score_agrees": true,
     "quarters_agree": true,
     "their_quarters": {
      "away": [
       17,
       31,
       31,
       26
      ],
      "home": [
       29,
       20,
       30,
       27
      ]
     },
     "my_quarters": {
      "away": [
       17,
       31,
       31,
       26
      ],
      "home": [
       29,
       20,
       30,
       27
      ]
     }
    },
    {
     "game_id": "0022600255",
     "matchup": "DET@SAS",
     "score_agrees": true,
     "quarters_agree": true,
     "their_quarters": {
      "away": [
       26,
       29,
       23,
       27
      ],
      "home": [
       33,
       21,
       18,
       21
      ]
     },
     "my_quarters": {
      "away": [
       26,
       29,
       23,
       27
      ],
      "home": [
       33,
       21,
       18,
       21
      ]
     }
    },
    {
     "game_id": "0022600256",
     "matchup": "CHA@LAL",
     "score_agrees": true,
     "quarters_agree": true,
     "their_quarters": {
      "away": [
       34,
       32,
       28,
       17,
       3
      ],
      "home": [
       30,
       29,
       22,
       30,
       7
      ]
     },
     "my_quarters": {
      "away": [
       34,
       32,
       28,
       17,
       3
      ],
      "home": [
       30,
       29,
       22,
       30,
       7
      ]
     }
    },
    {
     "game_id": "0022600257",
     "matchup": "UTA@LAC",
     "score_agrees": true,
     "quarters_agree": true,
     "their_quarters": {
      "away": [
       35,
       23,
       30,
       44
      ],
      "home": [
       29,
       33,
       24,
       21
      ]
     },
     "my_quarters": {
      "away": [
       35,
       23,
       30,
       44
      ],
      "home": [
       29,
       33,
       24,
       21
      ]
     }
    }
   ]
  },
  {
   "date": "2026-11-18",
   "games_compared": 12,
   "full_agreement": 12,
   "disagreements": 0,
   "detail": [
    {
     "game_id": "0022600258",
     "matchup": "MEM@CLE",
     "score_agrees": true,
     "quarters_agree": true,
     "their_quarters": {
      "away": [
       30,
       41,
       29,
       24
      ],
      "home": [
       37,
       35,
       27,
       22
      ]
     },
     "my_quarters": {
      "away": [
       30,
       41,
       29,
       24
      ],
      "home": [
       37,
       35,
       27,
       22
      ]
     }
    },
    {
     "game_id": "0022600259",
     "matchup": "HOU@IND",
     "score_agrees": true,
     "quarters_agree": true,
     "their_quarters": {
      "away": [
       39,
       23,
       31,
       26
      ],
      "home": [
       28,
       18,
       30,
       28
      ]
     },
     "my_quarters": {
      "away": [
       39,
       23,
       31,
       26
      ],
      "home": [
       28,
       18,
       30,
       28
      ]
     }
    },
    {
     "game_id": "0022600260",
     "matchup": "MIL@MIA",
     "score_agrees": true,
     "quarters_agree": true,
     "their_quarters": {
      "away": [
       23,
       25,
       38,
       44
      ],
      "home": [
       34,
       40,
       38,
       25
      ]
     },
     "my_quarters": {
      "away": [
       23,
       25,
       38,
       44
      ],
      "home": [
       34,
       40,
       38,
       25
      ]
     }
    },
    {
     "game_id": "0022600261",
     "matchup": "PHI@ORL",
     "score_agrees": true,
     "quarters_agree": true,
     "their_quarters": {
      "away": [
       27,
       37,
       28,
       29
      ],
      "home": [
       40,
       29,
       28,
       19
      ]
     },
     "my_quarters": {
      "away": [
       27,
       37,
       28,
       29
      ],
      "home": [
       40,
       29,
       28,
       19
      ]
     }
    },
    {
     "game_id": "0022600262",
     "matchup": "CHI@BKN",
     "score_agrees": true,
     "quarters_agree": true,
     "their_quarters": {
      "away": [
       37,
       39,
       35,
       26
      ],
      "home": [
       21,
       30,
       26,
       30
      ]
     },
     "my_quarters": {
      "away": [
       37,
       39,
       35,
       26
      ],
      "home": [
       21,
       30,
       26,
       30
      ]
     }
    },
    {
     "game_id": "0022600263",
     "matchup": "WAS@TOR",
     "score_agrees": true,
     "quarters_agree": true,
     "their_quarters": {
      "away": [
       29,
       20,
       29,
       25
      ],
      "home": [
       23,
       24,
       32,
       20
      ]
     },
     "my_quarters": {
      "away": [
       29,
       20,
       29,
       25
      ],
      "home": [
       23,
       24,
       32,
       20
      ]
     }
    },
    {
     "game_id": "0022600264",
     "matchup": "DET@NOP",
     "score_agrees": true,
     "quarters_agree": true,
     "their_quarters": {
      "away": [
       31,
       36,
       25,
       30
      ],
      "home": [
       31,
       29,
       26,
       23
      ]
     },
     "my_quarters": {
      "away": [
       31,
       36,
       25,
       30
      ],
      "home": [
       31,
       29,
       26,
       23
      ]
     }
    },
    {
     "game_id": "0022600265",
     "matchup": "ATL@OKC",
     "score_agrees": true,
     "quarters_agree": true,
     "their_quarters": {
      "away": [
       31,
       33,
       19,
       34
      ],
      "home": [
       29,
       22,
       32,
       29
      ]
     },
     "my_quarters": {
      "away": [
       31,
       33,
       19,
       34
      ],
      "home": [
       29,
       22,
       32,
       29
      ]
     }
    },
    {
     "game_id": "0022600266",
     "matchup": "BOS@DEN",
     "score_agrees": true,
     "quarters_agree": true,
     "their_quarters": {
      "away": [
       30,
       31,
       19,
       21
      ],
      "home": [
       24,
       25,
       31,
       25
      ]
     },
     "my_quarters": {
      "away": [
       30,
       31,
       19,
       21
      ],
      "home": [
       24,
       25,
       31,
       25
      ]
     }
    },
    {
     "game_id": "0022600267",
     "matchup": "GSW@DAL",
     "score_agrees": true,
     "quarters_agree": true,
     "their_quarters": {
      "away": [
       25,
       24,
       23,
       22
      ],
      "home": [
       35,
       27,
       30,
       24
      ]
     },
     "my_quarters": {
      "away": [
       25,
       24,
       23,
       22
      ],
      "home": [
       35,
       27,
       30,
       24
      ]
     }
    },
    {
     "game_id": "0022600268",
     "matchup": "UTA@LAL",
     "score_agrees": true,
     "quarters_agree": true,
     "their_quarters": {
      "away": [
       29,
       27,
       22,
       31
      ],
      "home": [
       34,
       20,
       22,
       21
      ]
     },
     "my_quarters": {
      "away": [
       29,
       27,
       22,
       31
      ],
      "home": [
       34,
       20,
       22,
       21
      ]
     }
    },
    {
     "game_id": "0022600269",
     "matchup": "PHX@SAC",
     "score_agrees": true,
     "quarters_agree": true,
     "their_quarters": {
      "away": [
       36,
       29,
       34,
       29
      ],
      "home": [
       31,
       29,
       24,
       23
      ]
     },
     "my_quarters": {
      "away": [
       36,
       29,
       34,
       29
      ],
      "home": [
       31,
       29,
       24,
       23
      ]
     }
    }
   ]
  }
 ],
 "totals": {
  "player_rows_by_day": {
   "2026-11-17": 126,
   "2026-11-18": 311
  },
  "games_parsed": 17,
  "games_expected_from_scoreboard": {
   "2026-11-17": 5,
   "2026-11-18": 12
  },
  "digest_failures": 0,
  "gamebooks_missing": 0
 }
}
```
</details>
