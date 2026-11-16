# Injury-report archive

Every edition of the official NBA injury report that has been read from the
official index <https://official.nba.com/nba-injury-report-2026-27-season/> is archived here, one directory per edition.

Each edition directory holds:

| File | What it is |
| --- | --- |
| `edition.json` | the edition's metadata: revision stamp, publication time, retrieval time, official URL, row hash, row counts, extraction artefacts |
| `rows.json` | the verbatim row transcription of that edition |
| `diff_vs_*.json` | the row-by-row diff against the previous edition |

**Binary PDFs are not archived here.** The binary PDF is NOT archived in this sandbox: the shell egress allowlist has no route to ak-static.cms.nba.com, and the only available route to it is the text-extraction fetch channel, which returns extracted text rather than bytes. What is stored is the verbatim row transcription, the SHA-256 of the transcribed row text, the official PDF URL on every row, the edition revision stamp and the retrieval time. This archive is therefore a text archive and is not represented as a binary one.

## Editions

| Edition (UTC id) | Revision stamp | Rows | Player rows | Team blocks | Status changes vs previous | Official source |
| --- | --- | --- | --- | --- | --- | --- |
| `2026-11-14_0130PM` | Injury Report: 11/14/26 01:30 PM | 50 | 50 | 0 | - | [PDF](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_01_30PM.pdf) |
| `2026-11-15_0615AM` | 2026-11-15 06:15 AM ET (edition stamp printed on every PDF page) | 101 | 84 | 17 | 0 | [PDF](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15AM.pdf) |
| `2026-11-15_0615PM` | 2026-11-15 06:15 PM ET | 155 | 149 | 6 | 16 | [PDF](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15PM.pdf) |

## Files

### 2026-11-14_0130PM

- `data/injury_reports/2026-11-14_0130PM/edition.json`
- `data/injury_reports/2026-11-14_0130PM/rows.json`
- official source: https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-14_01_30PM.pdf

### 2026-11-15_0615AM

- `data/injury_reports/2026-11-15_0615AM/edition.json`
- `data/injury_reports/2026-11-15_0615AM/rows.json`
- `data/injury_reports/2026-11-15_0615AM/diff_vs_2026-11-14_0130PM.json`
- official source: https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15AM.pdf

### 2026-11-15_0615PM

- `data/injury_reports/2026-11-15_0615PM/edition.json`
- `data/injury_reports/2026-11-15_0615PM/rows.json`
- `data/injury_reports/2026-11-15_0615PM/diff_vs_2026-11-15_0615AM.json`
- official source: https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-15_06_15PM.pdf

_Archive index rebuilt 2026-11-15T23:47:10Z by verify/2026-11-15-49f70042/build_injury_archive.py._
