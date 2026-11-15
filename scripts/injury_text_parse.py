#!/usr/bin/env python3
"""injury_text_parse.py - read the official injury-report PDF text layer.

    python3 scripts/injury_text_parse.py

The league publishes the injury report as a PDF whose text layer is laid out
in table cells: the extracted text is one fragment per line, not one row per
line. Reading it line by line therefore loses the row structure completely.

This module rebuilds the rows from the token stream:

    11/15/2026 | 01:00 | (ET) | IND@PHI | Indiana Pacers
    Furphy, Johnny | Out | Injury/Illness - Right ACL Repair / Surgery

The rules it uses, all of them visible in the published text:

  * a page header ("Injury Report: 11/15/26 06:30 AM Page 2 of 6") is removed;
  * a game header is the date, the tip time, the "(ET)" marker and the matchup;
  * a team is one of the thirty club names, matched as consecutive words;
  * a player is written "Surname, Firstname", so the comma marks the start of
    the name (a suffix such as "Jr." sits in front of the comma);
  * the status is one of the six words the league prints;
  * the reason is everything between this status and the next player name.

Nothing is inferred: a fragment that does not fit is left out and counted in
`unparsed_fragments` rather than being turned into a value.
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

STATUS_WORDS = ("NOT YET SUBMITTED", "Questionable", "Doubtful", "Probable",
                "Available", "Out")

# The club names the league prints, with the tricode used across the site.
TEAM_LABELS = [
    ("Atlanta Hawks", "ATL"), ("Boston Celtics", "BOS"),
    ("Brooklyn Nets", "BKN"), ("Charlotte Hornets", "CHA"),
    ("Chicago Bulls", "CHI"), ("Cleveland Cavaliers", "CLE"),
    ("Dallas Mavericks", "DAL"), ("Denver Nuggets", "DEN"),
    ("Detroit Pistons", "DET"), ("Golden State Warriors", "GSW"),
    ("Houston Rockets", "HOU"), ("Indiana Pacers", "IND"),
    ("LA Clippers", "LAC"), ("Los Angeles Clippers", "LAC"),
    ("Los Angeles Lakers", "LAL"), ("Memphis Grizzlies", "MEM"),
    ("Miami Heat", "MIA"), ("Milwaukee Bucks", "MIL"),
    ("Minnesota Timberwolves", "MIN"), ("New Orleans Pelicans", "NOP"),
    ("New York Knicks", "NYK"), ("Oklahoma City Thunder", "OKC"),
    ("Orlando Magic", "ORL"), ("Philadelphia 76ers", "PHI"),
    ("Phoenix Suns", "PHX"), ("Portland Trail Blazers", "POR"),
    ("Sacramento Kings", "SAC"), ("San Antonio Spurs", "SAS"),
    ("Toronto Raptors", "TOR"), ("Utah Jazz", "UTA"),
    ("Washington Wizards", "WAS"),
]

SUFFIXES = ("Jr.", "Sr.", "II", "III", "IV")

PAGE_HEADER_COLUMNS = ["Game", "Date", "Game", "Time", "Matchup", "Team",
                       "Player", "Name", "Current", "Status", "Reason"]


def _tokens(text):
    return text.split()


def _strip_page_headers(tokens):
    """Remove the repeated page header and the page-1 column header."""
    out = []
    i = 0
    n = len(tokens)
    while i < n:
        if tokens[i] == "Injury" and i + 1 < n and tokens[i + 1] == "Report:":
            j = i + 2
            # the header carries an optional date, an optional time and then
            # "Page <n> of <m>"
            while j < n and re.fullmatch(r"\d{1,2}/\d{1,2}/\d{2,4}", tokens[j]):
                j += 1
            if j < n and re.fullmatch(r"\d{1,2}:\d{2}", tokens[j]):
                j += 1
                if j < n and tokens[j] in ("AM", "PM"):
                    j += 1
            if j < n and tokens[j] == "Page":
                j += 1
                if j < n:
                    j += 1          # the page number
                if j < n and tokens[j] == "of":
                    j += 1
                if j < n:
                    j += 1          # the page count
            i = j
            continue
        if tokens[i:i + len(PAGE_HEADER_COLUMNS)] == PAGE_HEADER_COLUMNS:
            i += len(PAGE_HEADER_COLUMNS)
            continue
        out.append(tokens[i])
        i += 1
    return out


def _find_status(tokens, i):
    """The status starting at token i, or None."""
    if tokens[i] == "NOT" and i + 2 < len(tokens) and \
            tokens[i + 1] == "YET" and tokens[i + 2] == "SUBMITTED":
        return "NOT YET SUBMITTED", 3
    t = tokens[i]
    for st in STATUS_WORDS:
        if st == "NOT YET SUBMITTED":
            continue
        if t == st:
            return st, 1
    return None, 0


def _team_positions(tokens):
    """Every (start, end, name, tricode) team name found in the token stream."""
    found = []
    for name, tri in TEAM_LABELS:
        parts = name.split()
        for i in range(len(tokens) - len(parts) + 1):
            if tokens[i:i + len(parts)] == parts:
                found.append((i, i + len(parts), name, tri))
    # longest match wins, and one team name cannot start inside another
    found.sort(key=lambda r: (r[0], -(r[1] - r[0])))
    chosen = []
    last_end = -1
    for r in found:
        if r[0] >= last_end:
            chosen.append(r)
            last_end = r[1]
    return chosen


def _player_name(tokens, start, end):
    """Turn the name fragment into "Firstname Surname"."""
    frag = tokens[start:end]
    if not frag:
        return "", ""
    comma = None
    for k, t in enumerate(frag):
        if "," in t:
            comma = k
            break
    if comma is None:
        return " ".join(frag), ""
    last = frag[comma].split(",")[0]
    first = " ".join(frag[comma + 1:])
    surname = [last]
    k = comma - 1
    while k >= 0 and frag[k] in SUFFIXES:
        surname.insert(0, frag[k])
        k -= 1
    name = (first + " " + " ".join(surname)).strip()
    return name, " ".join(frag)


def parse(text):
    """Parse one official injury-report text layer into rows."""
    rows = []
    unparsed = []
    if not text:
        return {"rows": [], "unparsed_fragments": []}
    tokens = _strip_page_headers(_tokens(text))

    # locate every status token
    status_positions = []
    i = 0
    while i < len(tokens):
        st, size = _find_status(tokens, i)
        if st:
            status_positions.append((i, st, size))
            i += size
            continue
        i += 1

    teams = _team_positions(tokens)

    cur_date = None
    cur_time = None
    cur_matchup = None
    cur_team = None

    for idx, (pos, status, size) in enumerate(status_positions):
        # the game header is the nearest date/time/matchup before the row
        for j in range(pos - 1, -1, -1):
            t = tokens[j]
            if cur_matchup is None:
                m = re.fullmatch(r"[A-Z]{2,3}@[A-Z]{2,3}", t)
                if m:
                    cur_matchup = t
            if cur_time is None:
                m = re.fullmatch(r"\d{1,2}:\d{2}", t)
                if m:
                    cur_time = t
            if cur_date is None:
                m = re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}", t)
                if m:
                    cur_date = t
            if cur_date and cur_time and cur_matchup:
                break

        # the player name is the fragment between the previous row's end and
        # this status, beginning at the comma
        prev_end = status_positions[idx - 1][0] + status_positions[idx - 1][2] \
            if idx else 0
        comma_at = None
        for j in range(pos - 1, prev_end - 1, -1):
            if "," in tokens[j]:
                comma_at = j
                break
        if comma_at is None:
            unparsed.append({"fragment": " ".join(tokens[prev_end:pos + size]),
                             "status": status, "reason": "no player name found"})
            continue
        name_start = comma_at
        k = comma_at - 1
        while k >= prev_end and tokens[k] in SUFFIXES:
            name_start = k
            k -= 1
        player, printed = _player_name(tokens, name_start, pos)

        # the reason runs until the next player name
        next_start = None
        if idx + 1 < len(status_positions):
            npos = status_positions[idx + 1][0]
            for j in range(npos - 1, pos + size - 1, -1):
                if "," in tokens[j]:
                    next_start = j
                    break
            reason_end = next_start if next_start is not None else len(tokens)
        else:
            reason_end = len(tokens)
        reason = " ".join(tokens[pos + size:reason_end]).strip()
        reason = re.sub(r"\s+/\s+", " / ", reason)
        reason = re.sub(r"\s+-\s+", " - ", reason)

        # the team is the last club name before this row
        team = None
        team_name = None
        for (s, e, nm, tr) in teams:
            if e <= name_start:
                team = tr
                team_name = nm
            else:
                break
        if team is None:
            unparsed.append({"fragment": printed, "status": status,
                             "reason": "no team name found before this row"})

        if status == "NOT YET SUBMITTED":
            player = ""
            reason = ""

        rows.append({
            "game_date": cur_date,
            "game_time_et": cur_time,
            "matchup": cur_matchup,
            "team": team,
            "team_name_printed": team_name,
            "player": player,
            "player_printed": printed,
            "status": status,
            "reason": reason,
        })
    return {"rows": rows, "unparsed_fragments": unparsed}


def main():
    import gzip
    import json
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        ROOT, "data", "captures", "2026-11-15", "raw", "injury")
    files = sorted(f for f in os.listdir(src) if f.endswith(".txt.gz"))
    for f in files[:3]:
        with gzip.open(os.path.join(src, f), "rt", encoding="utf-8") as fh:
            out = parse(fh.read())
        print(f, "rows", len(out["rows"]), "unparsed", len(out["unparsed_fragments"]))
        for r in out["rows"][:6]:
            print("   ", json.dumps(r, ensure_ascii=False))
        for u in out["unparsed_fragments"][:4]:
            print("   UNPARSED", json.dumps(u, ensure_ascii=False))


if __name__ == "__main__":
    main()
