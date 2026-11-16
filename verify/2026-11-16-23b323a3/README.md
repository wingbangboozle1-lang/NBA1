# Evidence namespace — session `arena/23b323a3-nba1`

COORDINATION §50. Everything here is reproducible from committed files; nothing is a
screenshot of a claim.

| File | What it proves | How to re-run |
| --- | --- | --- |
| `verify_settlement_2026-11-15.py` | The 2026-11-15 settlement re-grades to exactly what it says, from the official finals, without trusting the settlement file's own verdicts. Checks the precondition (9 finals, every quarters row sums to its printed final, every row carries an official `source_url`), then re-applies the published rule to each single and re-sums the units. | `python3 verify/2026-11-16-23b323a3/verify_settlement_2026-11-15.py` → **0 failures**, record `5-4-0`, `+0.60` units. |
| `verify_settlement_2026-11-15.out` | The recorded output of the above, so the result is visible without running it. | — |
| `ledger_chain_check.py` | Re-hashes the ledger chain independently of `scripts/verify_ledger.py` (different implementation, same rule) and confirms the recorded `head` is the hash of the last entry. | `python3 verify/2026-11-16-23b323a3/ledger_chain_check.py` |
| `official_reads_2026-11-16.json` | The exact official URLs read first-hand in this session, what each was read for, and the values transcribed from it. This is the provenance record behind the three completed finals and the arena-name correction. | — |

## Official sources read first-hand this session

| Source | Read for | Result |
| --- | --- | --- |
| <https://www.nba.com/games?date=2026-11-15> | state of all nine 11/15 games | 9 of 9 print Final |
| <https://statsdmz.nba.com/pdfs/20261115/20261115_HOUWAS_book.pdf> | HOU@WAS quarter scores | 36-31 / 37-23 / 46-34 / 28-31 = 147-119 |
| <https://statsdmz.nba.com/pdfs/20261115/20261115_ATLMIL_book.pdf> | ATL@MIL quarter scores + attendance | 18-37 / 37-16 / 32-27 / 26-26 = 113-106; attendance 11,474 |
| <https://statsdmz.nba.com/pdfs/20261115/20261115_OKCSAC_book.pdf> | OKC@SAC quarter scores | 32-24 / 30-26 / 32-30 / 31-23 = 125-103 |
| <https://www.nba.com/schedule?date=2026-11-17> | venue names, for auditing the repo's arena table | LAC → **Intuit Dome, Inglewood, CA**; PHI → **Xfinity Mobile Arena**; PHX → **Mortgage Matchup Center**; the eight 11/16 games and their tips |
| <https://www.nba.com/standings> | home/road records (cross-check of the HCA anchor already in the tree) | 2026-27 season standings render; used as a reachability + format check, no value transcribed into the model by this pass |
| <https://official.nba.com/nba-injury-report-2026-27-season/> | injury-report index, submission rules, and the 11/16 edition list | index reachable; rules text transcribed verbatim into the note below |
| <https://www.nba.com/stats/players/traditional?Season=2026-27&SeasonType=Regular+Season&PerMode=PerGame> | whether a national per-player minutes table is readable from here | **471 player rows**, reachable — reading was interrupted, so the capture was NOT extended (see F110) |

### Injury-report submission rules, transcribed verbatim from the official index

> "By 5 p.m. local time the day before a game (other than the second day of a back-to-back),
> teams must designate a participation status and identify a specific injury, illness, other
> medical condition, or other reason for any player whose participation in the game may be
> affected for any reason. For the second game of a back-to-back, teams must report the above
> information by 1 p.m. local time on the day of the game. In addition, teams are required to
> submit a game-day injury report between 11 a.m. and 1 p.m. local time (and between 8 and 10
> a.m. for tip-offs 5 p.m. or earlier) on game days (besides the second game of a
> back-to-back)."

This is the rule the horizon's `availability_provenance` field is derived from: a pick whose
game date has no edition yet is marked provisional rather than "nobody is injured".
