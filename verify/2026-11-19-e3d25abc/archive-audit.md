# Injury-report archive audit — 2026-11-19, session `arena/e3d25abc-nba1`

Audited 154 archived PDFs (152 distinct official editions) by recomputing every SHA-256 from the bytes. Machine-readable: `verify/2026-11-19-e3d25abc/archive-audit.json`.

| Day | Files | Editions | Fully clean | 16-hex truncated names | No retrieval stamp |
| --- | --- | --- | --- | --- | --- |
| 2026-11-15 | 83 | 81 | 83 | 76 | 0 |
| 2026-11-16 | 17 | 17 | 17 | 0 | 0 |
| 2026-11-17 | 20 | 20 | 20 | 0 | 0 |
| 2026-11-18 | 30 | 30 | 30 | 0 | 0 |
| 2026-11-19 | 4 | 4 | 4 | 0 | 0 |

## Findings


### Same official edition stored twice

* `Injury-Report_2026-11-15_05_15PM`: 2 files, bytes identical: **True** — `Injury-Report_2026-11-15_05_15PM__e6605d35bf4acfcb.pdf`, `Injury-Report_2026-11-15_05_15PM__e6605d35bf4acfcb8e980247521796233ea3663648db4218d58a9a79c6e827ab.pdf`
* `Injury-Report_2026-11-15_05_30PM`: 2 files, bytes identical: **True** — `Injury-Report_2026-11-15_05_30PM__0ff31c236dda6c0d.pdf`, `Injury-Report_2026-11-15_05_30PM__0ff31c236dda6c0dfc750665c94f47bed83c1d7f900b678195367421b115be89.pdf`

### Diff-chain shape

* 151 published diff(s) pair two adjacent editions in the sorted order;
* 0 do not (listed in the JSON);
* 2 compare an edition with itself, which is only possible because the same edition is stored under two filenames;
* 0 edition(s) have no parse record under `data/parsed/injury_diffs/editions/`.
