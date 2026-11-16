#!/usr/bin/env python3
"""Parse every captured official injury PDF and diff consecutive editions.

    python3 scripts/injury_ledger_801ba27f.py

Session `arena/801ba27f-nba1`, COORDINATION.md §41 task H02/H03.

Every injury PDF this session captured is stored byte-for-byte under
`data/raw/injury_pdfs/` with a JSON sidecar holding the official URL, the
first retrieval timestamp, the byte count and the SHA-256 of the bytes. This
script reads those stored bytes - it fetches nothing - extracts the status
table from each edition, and diffs each edition against the one published
immediately before it, so a status change is a computed fact and not a
hand-written note.

Parsing is deliberately conservative. If an edition cannot be parsed into at
least one row it is reported as a parse failure, never silently skipped.
"""

import datetime
import glob
import json
import os
import re

try:
    from pypdf import PdfReader
except ImportError:                                            # pragma: no cover
    PdfReader = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_DIR = os.path.join(ROOT, "data", "raw", "injury_pdfs")
OUT_DIR = os.path.join(ROOT, "data", "injury_reports")
LEDGER = os.path.join(OUT_DIR, "editions_2026-11-15.json")
DIFF = os.path.join(OUT_DIR, "diff_2026-11-15.json")

STATUS_WORDS = ("Out", "Available", "Questionable", "Probable", "Doubtful")

# "Furphy, Johnny" / "Jackson Jr., Jaren" / "de Larrea, Sergio" / "Lively II, Dereck"
NAME_RE = re.compile(r"^([A-Z][\wÀ-ÿ'’\.\- ]*?(?: [IVX]+)?, [A-Z][\wÀ-ÿ'’\.\-]*(?: [\wÀ-ÿ'’\.\-]+)*)$")
DATE_RE = re.compile(r"^(\d{2})/(\d{2})/(\d{2})$")
GAMEDATE_RE = re.compile(r"^(\d{2}/\d{2}/\d{4})$")
TIME_RE = re.compile(r"^(\d{2}:\d{2})\s*\(ET\)$")
MATCHUP_RE = re.compile(r"^([A-Z]{3}@[A-Z]{3})$")

TEAM_NAMES = [
    "Atlanta Hawks", "Boston Celtics", "Brooklyn Nets", "Charlotte Hornets",
    "Chicago Bulls", "Cleveland Cavaliers", "Dallas Mavericks", "Denver Nuggets",
    "Detroit Pistons", "Golden State Warriors", "Houston Rockets",
    "Indiana Pacers", "LA Clippers", "Los Angeles Lakers", "Memphis Grizzlies",
    "Miami Heat", "Milwaukee Bucks", "Minnesota Timberwolves",
    "New Orleans Pelicans", "New York Knicks", "Oklahoma City Thunder",
    "Orlando Magic", "Philadelphia 76ers", "Phoenix Suns",
    "Portland Trail Blazers", "Sacramento Kings", "San Antonio Spurs",
    "Toronto Raptors", "Utah Jazz", "Washington Wizards",
]

TRICODE = {
    "Atlanta Hawks": "ATL", "Boston Celtics": "BOS", "Brooklyn Nets": "BKN",
    "Charlotte Hornets": "CHA", "Chicago Bulls": "CHI",
    "Cleveland Cavaliers": "CLE", "Dallas Mavericks": "DAL",
    "Denver Nuggets": "DEN", "Detroit Pistons": "DET",
    "Golden State Warriors": "GSW", "Houston Rockets": "HOU",
    "Indiana Pacers": "IND", "LA Clippers": "LAC", "Los Angeles Lakers": "LAL",
    "Memphis Grizzlies": "MEM", "Miami Heat": "MIA", "Milwaukee Bucks": "MIL",
    "Minnesota Timberwolves": "MIN", "New Orleans Pelicans": "NOP",
    "New York Knicks": "NYK", "Oklahoma City Thunder": "OKC",
    "Orlando Magic": "ORL", "Philadelphia 76ers": "PHI", "Phoenix Suns": "PHX",
    "Portland Trail Blazers": "POR", "Sacramento Kings": "SAC",
    "San Antonio Spurs": "SAS", "Toronto Raptors": "TOR", "Utah Jazz": "UTA",
    "Washington Wizards": "WAS",
}


def edition_sort_key(name):
    """Sort `Injury-Report_2026-11-15_06_15PM.pdf` chronologically."""
    m = re.match(r"Injury-Report_(\d{4}-\d{2}-\d{2})_(\d{2})_(\d{2})(AM|PM)\.pdf", name)
    if not m:
        return ("", 0, 0)
    d, hh, mm, ap = m.groups()
    h = int(hh) % 12
    if ap == "PM":
        h += 12
    return (d, h, int(mm))


def pdf_text(path):
    if PdfReader is None:
        raise RuntimeError("pypdf is required: pip install --break-system-packages pypdf")
    r = PdfReader(path)
    return "\n".join((p.extract_text() or "") for p in r.pages)


NAME_SUFFIXES = {"Jr.", "Sr.", "II", "III", "IV", "V"}
STATUS_SET = set(STATUS_WORDS)
# Prefixes of every multi-word team name, so a name split across lines such as
# "Indiana" / "Pacers" or "Los" / "Angeles" / "Lakers" can be re-joined.
TEAM_PREFIXES = set()
for _t in TEAM_NAMES:
    _w = _t.split()
    for _k in range(1, len(_w)):
        TEAM_PREFIXES.add(" ".join(_w[:_k]))


def _find_team(lines, start, end):
    """Return (team, index) for a team name found in lines[start:end], else (None, None)."""
    buf = []
    for i in range(start, min(end, len(lines))):
        w = lines[i]
        if not w or w in STATUS_SET or GAMEDATE_RE.match(w) or TIME_RE.match(w) \
                or MATCHUP_RE.match(w) or NAME_RE.match(w):
            if buf:
                buf = []
            continue
        cand = (" ".join(buf + [w])).strip()
        if cand in TEAM_NAMES:
            return cand, i
        if cand in TEAM_PREFIXES or (len(cand.split()) == 1
                                     and cand[:1].isupper()
                                     and cand.rstrip(".").isalpha()
                                     and len(cand) <= 12
                                     and any(n.startswith(cand + " ") for n in TEAM_NAMES)):
            buf.append(w)
        else:
            buf = []
    return None, None


def parse_edition(text):
    """Parse an injury-report edition into one row per player status.

    The PDF prints the repeating columns (date, tip, matchup, team) only when
    they change, and its text layer wraps arbitrarily - "Indiana" and "Pacers"
    land on separate lines - so the parse is anchored on the status words,
    which are the only column that appears on every single row.
    """
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    # Drop the running page furniture ("Page 1 of 6", the repeated header block).
    header_words = {"Page", "Injury", "Report:", "Game", "Date", "Time", "Matchup",
                    "Team", "Player", "Name", "Current", "Status", "Reason"}
    status_idx = [i for i, l in enumerate(lines) if l in STATUS_SET]

    rows = []
    state = {"date": None, "time": None, "matchup": None, "team": None}

    def keywords(chunk_lines):
        """Update the carried columns from a chunk; return leftover lines."""
        out = []
        i = 0
        while i < len(chunk_lines):
            l = chunk_lines[i]
            if GAMEDATE_RE.match(l):
                state["date"] = l
            elif TIME_RE.match(l):
                state["time"] = l
            elif MATCHUP_RE.match(l):
                state["matchup"] = l
            else:
                team, at = _find_team(chunk_lines, i, i + 3)
                if team:
                    state["team"] = team
                    i = at
                else:
                    if l in header_words and not out:
                        pass
                    else:
                        out.append(l)
            i += 1
        return out

    prev_end = 0
    for si in status_idx:
        chunk = lines[prev_end:si]
        prev_end = si + 1
        left = keywords(chunk)
        # The player name is the shortest trailing run of the leftover lines
        # that reads as "Surname, First ...".
        name, reason_lines = None, left
        for j in range(len(left) - 1, -1, -1):
            cand = " ".join(left[j:])
            if NAME_RE.match(cand):
                name = cand
                reason_lines = left[:j]
                # "Cenac" / "Jr.," / "Christopher": re-attach a dropped prefix
                # when the surname is a generational suffix.
                if j >= 1 and cand.split(",")[0].strip() in NAME_SUFFIXES:
                    name = left[j - 1] + " " + cand
                    reason_lines = left[:j - 1]
                break
        reason = " ".join(reason_lines)
        reason = re.sub(r"\s+", " ", reason).replace("- ", "-").strip()
        rows.append({
            "game_date": state["date"], "game_time_et": state["time"],
            "matchup": state["matchup"], "team": state["team"],
            "tricode": TRICODE.get(state["team"]),
            "player": name,
            "status": lines[si],
            "reason": reason,
        })
    return rows


def dedupe(rows):
    seen, out = set(), []
    for r in rows:
        k = (r["game_date"], r["matchup"], r["team"], r["player"], r["status"])
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
    return out


def main():
    if PdfReader is None:
        print("pypdf missing; nothing parsed")
        return 1
    os.makedirs(OUT_DIR, exist_ok=True)
    pdfs = sorted([p for p in glob.glob(os.path.join(PDF_DIR, "Injury-Report_2026-11-15_*.pdf"))],
                  key=lambda p: edition_sort_key(os.path.basename(p).split("__")[0] + ".pdf"))
    editions = []
    for p in pdfs:
        base = os.path.basename(p)
        edition_label = base.split("__")[0]
        side = p[:-4] + ".json"
        meta = json.load(open(side)) if os.path.exists(side) else {}
        rec = {
            "edition": edition_label,
            "revision_label": meta.get("revision_label"),
            "source_url": meta.get("url"),
            "retrieved_utc": meta.get("retrieved_utc"),
            "bytes": meta.get("bytes"),
            "sha256": meta.get("sha256"),
            "pdf_signature_ok": meta.get("pdf_signature_ok"),
            "stored_file": os.path.relpath(p, ROOT),
            "rows": [],
            "parse_status": None,
        }
        try:
            text = pdf_text(p)
            rows = dedupe(parse_edition(text))
            rec["rows"] = rows
            rec["n_rows"] = len(rows)
            rec["parse_status"] = "ok" if rows else "no rows parsed"
        except Exception as exc:                              # noqa: BLE001
            rec["parse_status"] = "FAILED: %s: %s" % (type(exc).__name__, exc)
            rec["n_rows"] = 0
        editions.append(rec)

    json.dump({"title": "Official NBA injury report editions, 2026-11-15",
               "session": "arena/801ba27f-nba1",
               "built_utc": datetime.datetime.now(datetime.timezone.utc)
                                .strftime("%Y-%m-%dT%H:%M:%SZ"),
               "source_index": "https://official.nba.com/nba-injury-report-2026-27-season/",
               "pdf_host": "https://ak-static.cms.nba.com/referee/injury/",
               "rule": ("every edition the official index linked for 2026-11-15 was "
                        "downloaded, stored by content hash, parsed, and diffed against "
                        "the edition published immediately before it"),
               "editions": editions},
              open(LEDGER, "w"), indent=1)

    # Consecutive diff.
    diffs = []
    for a, b in zip(editions, editions[1:]):
        prev = {(r["team"], r["player"]): r for r in a["rows"]}
        cur = {(r["team"], r["player"]): r for r in b["rows"]}
        changes = []
        for k in sorted(set(prev) | set(cur)):
            p, c = prev.get(k), cur.get(k)
            if p is None:
                changes.append({"team": k[0], "player": k[1],
                                "change": "ADDED", "from": None,
                                "to": c["status"], "reason": c.get("reason")})
            elif c is None:
                changes.append({"team": k[0], "player": k[1],
                                "change": "REMOVED", "from": p["status"],
                                "to": None, "reason": p.get("reason")})
            elif p["status"] != c["status"]:
                changes.append({"team": k[0], "player": k[1],
                                "change": "STATUS_CHANGE", "from": p["status"],
                                "to": c["status"], "reason": c.get("reason")})
            elif p.get("reason") != c.get("reason"):
                changes.append({"team": k[0], "player": k[1],
                                "change": "REASON_CHANGE", "from": p["status"],
                                "to": c["status"], "reason": c.get("reason"),
                                "reason_before": p.get("reason")})
        diffs.append({
            "from_edition": a["edition"], "to_edition": b["edition"],
            "from_revision_label": a["revision_label"],
            "to_revision_label": b["revision_label"],
            "from_sha256": a["sha256"], "to_sha256": b["sha256"],
            "from_retrieved_utc": a["retrieved_utc"], "to_retrieved_utc": b["retrieved_utc"],
            "n_rows_before": a["n_rows"], "n_rows_after": b["n_rows"],
            "n_status_changes": sum(1 for c in changes if c["change"] == "STATUS_CHANGE"),
            "changes": changes,
        })
    total_status = sum(d["n_status_changes"] for d in diffs)
    json.dump({"title": "Consecutive official injury-report diffs, 2026-11-15",
               "session": "arena/801ba27f-nba1",
               "built_utc": datetime.datetime.now(datetime.timezone.utc)
                                .strftime("%Y-%m-%dT%H:%M:%SZ"),
               "n_editions": len(editions),
               "n_consecutive_pairs": len(diffs),
               "n_status_changes_total": total_status,
               "diffs": diffs},
              open(DIFF, "w"), indent=1)

    print("editions: %d   parsed ok: %d" %
          (len(editions), sum(1 for e in editions if e["parse_status"] == "ok")))
    bad = [e for e in editions if e["parse_status"] != "ok"]
    for e in bad[:5]:
        print("  PROBLEM", e["edition"], e["parse_status"])
    print("consecutive pairs: %d   status changes: %d" % (len(diffs), total_status))
    for d in diffs:
        if d["n_status_changes"]:
            for c in d["changes"]:
                if c["change"] == "STATUS_CHANGE":
                    print("   %s -> %s  %-22s %s: %s -> %s" %
                          (d["from_revision_label"], d["to_revision_label"],
                           c["team"], c["player"], c["from"], c["to"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
