#!/usr/bin/env python3
"""build_minutes_shares.py — measured minutes shares per team from official gamebooks.

Brief line this answers (register R12): "Model minutes redistribution explicitly: for
each team, the top-8 minutes shares and the replacement shares when a player is out."

What is measured here, and what is not
--------------------------------------
Measured (from the league's own gamebook PDFs, committed verbatim under
data/official/gamebooks/):
  * per team and game: each player's minutes share of the printed team total
    (240:00 = 14,400 s), the top-8 minutes share, and the bench remainder;
  * the players who were out in that game, with the official reason printed in the
    gamebook (Inactive lines and DNP / DND rows).

NOT measured (written as an explicit blocked row, never estimated):
  * replacement shares. Measuring who absorbs a missing player's minutes needs the
    same team's games with and without that player. The repository holds one date
    (2026-11-15, one game per team), so there is no with/without contrast.

Rules
-----
1. Every value is a cell of the gamebook text. Nothing is inferred or rounded into a
   different value. Shares are computed from integer seconds.
2. The printed team total (240:00) is the denominator. The sum of the player rows is
   checked against it. A difference is written to `flags`, not silently fixed.
3. A top-8 cut that is tied at the 8th/9th boundary is marked `tie_at_8`.
4. Each row links the official nba.com game page (from data/official/results_*.json)
   and the official statsdmz gamebook PDF named in the gamebook header.

Run:  python3 scripts/build_minutes_shares.py
"""
from __future__ import annotations

import glob
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import capture_player_logs as cpl  # noqa: E402  (the gamebook parser used everywhere in the repo)

GAMEBOOKS = os.path.join(ROOT, "data", "official", "gamebooks")
# Q02 scope (COORDINATION section 50): the six 11/15 gamebooks written by arena/d31fb422-nba1.
# The three gamebooks added for Q01 (HOUWAS, ATLMIL, OKCSAC) are excluded here, as logged.
SCOPE_GAMEBOOKS = [
    "2026-11-15_CHALAC.md", "2026-11-15_DALBOS.md", "2026-11-15_INDPHI.md",
    "2026-11-15_LALPHX.md", "2026-11-15_NYKTOR.md", "2026-11-15_SASUTA.md",
]
EXCLUDED_GAMEBOOKS = ["2026-11-15_ATLMIL.md", "2026-11-15_HOUWAS.md", "2026-11-15_OKCSAC.md"]
RESULTS = [
    os.path.join(ROOT, "data", "official", "results_2026-11-15.json"),
]
OUT = os.path.join(ROOT, "data", "derived", "minutes_shares.json")
PAGE = os.path.join(ROOT, "site", "pages", "minutes.html")
TEAM_SECONDS = 240 * 60  # regulation team total 240:00 (kept for the header comment; per-game totals come from the gamebook)

RX_GB_URL = re.compile(r"(https://statsdmz\.nba\.com/pdfs/\d{8}/\d{8}_([A-Z]{6})_book\.pdf)")
RX_TOTAL_MIN = re.compile(r"(\d{1,3}):(\d{2})")


def _fmt(sec: int) -> str:
    return "%d:%02d" % (sec // 60, sec % 60)


def load_results():
    rows = {}
    for path in RESULTS:
        d = json.load(open(path, encoding="utf-8"))
        for r in d["rows"]:
            if r.get("away_pts") is None or r.get("home_pts") is None:
                continue
            rows[(r["date"], r["away"], r["home"])] = r
    return rows


def printed_totals(raw: str):
    """The two printed team-total rows (page 1: visitor, then home), as (line, seconds).

    A team-total row is a table row with a MM:SS cell and no letters: player rows always
    carry a name and DNP rows carry a note, so neither can match."""
    hits = []
    for ln in raw.splitlines():
        if not ln.startswith("|") or re.search(r"[A-Za-z]", ln):
            continue
        m = RX_TOTAL_MIN.search(ln)
        if m:
            hits.append((ln, int(m.group(1)) * 60 + int(m.group(2))))
    if len(hits) < 2:
        raise SystemExit("gamebook has fewer than two printed team-total rows")
    return hits[0], hits[1]


def _e(x) -> str:
    return html.escape("" if x is None else str(x), quote=True)


def _pct(x) -> str:
    return "" if x is None else "%.1f%%" % (100 * x)


def render_page(doc) -> str:
    """Plain HTML from the JSON above. Each row links its official game page and gamebook PDF."""
    body = []
    body.append("<h1>Minutes shares &middot; measured from official gamebooks</h1>")
    body.append("<p class=\"lede\">Scope: the six 11/15/2026 gamebooks named in the data file. "
                "Each share is a player's printed minutes divided by the printed team total. "
                "Top-8 is the sum of the eight largest shares. Nothing is estimated: a blank cell means the "
                "value is not in the gamebook.</p>")
    body.append("<p class=\"note\"><strong>Reading limit:</strong> " + _e(doc["sample"]["reading"]) + "</p>")
    body.append("<h2>Team-game shares</h2>")
    body.append("<div class=\"tablewrap\"><table class=\"dash\"><thead><tr>"
                "<th>Game</th><th>Team</th><th>Final</th><th>Players used</th>"
                "<th>Printed total</th><th>Player-minutes sum</th><th>Top-8 share</th><th>Bench share</th>"
                "<th>Top 8 (minutes)</th><th>Not played (official note)</th><th>Source</th>"
                "</tr></thead><tbody>")
    for r in doc["rows"]:
        top8 = "; ".join("%s %s (%s)" % (t["player"], t["min"], _pct(t["share"])) for t in r["top8"])
        outs = "; ".join("%s: %s" % (o["player"], o["official_note"]) for o in r["out_or_not_played"])
        sum_cell = _e(r["player_minutes_sum"])
        if r["player_minutes_sum"] != r["printed_team_total"]:
            sum_cell += ' <span class="flag">FLAG: differs from printed total</span>'
        cells = [
            _e(r["game"]), _e(r["team"]), _e(r["team_final"]), _e(r["players_played"]),
            _e(r["printed_team_total"]), sum_cell, _e(_pct(r["top8_share"])), _e(_pct(r["bench_share"])),
            _e(top8), _e(outs) or "&mdash;",
            '<a href="%s" rel="noopener">game page</a> &middot; <a href="%s" rel="noopener">gamebook PDF</a>'
            % (_e(r["source_game_page"]), _e(r["source_gamebook_pdf"])),
        ]
        body.append("<tr>" + "".join("<td>%s</td>" % c for c in cells) + "</tr>")
    body.append("</tbody></table></div>")
    body.append("<h2>Replacement shares &mdash; blocked</h2>")
    rep = doc["replacement_shares"]
    body.append("<div class=\"tablewrap\"><table class=\"dash\"><thead><tr><th>Measure</th><th>Status</th>"
                "<th>Why, and what would unblock it</th><th>Source</th></tr></thead><tbody><tr>"
                "<td>Replacement share when a player is out</td><td><strong>%s</strong></td>"
                "<td>%s <em>Unblock:</em> %s</td>"
                "<td><span class=\"na\" title=\"Blocked, because no measured value exists and so there is no source to link\">&mdash;</span></td>"
                "</tr></tbody></table></div>" % (_e(rep["status"]), _e(rep["reason"]), _e(rep["unblock"])))
    if doc["flags"]:
        body.append("<h2>Flags</h2><ul>")
        for f in doc["flags"]:
            body.append("<li><strong>%s</strong> &middot; %s &middot; %s: player minutes sum to %s, printed total %s. "
                        "%s. <a href=\"%s\" rel=\"noopener\">official gamebook</a></li>" % (
                            _e(f["kind"]), _e(f["game"]), _e(f["team"]), _e(f["player_sum"]),
                            _e(f["printed_total"]), _e(f["treatment"]), _e(f["source"])))
        body.append("</ul>")
    body.append("<p class=\"note\">Scope note: " + _e(doc["scope_note"]) + "</p>")
    body.append("<p class=\"note\">Method: " + _e(doc["method"]) + "</p>")
    body.append("<p class=\"note\">Generated by scripts/build_minutes_shares.py from data/derived/minutes_shares.json.</p>")
    return (
        "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        "<title>Minutes shares &middot; NBA1</title>\n<link rel=\"stylesheet\" href=\"../assets/site.css\">\n"
        "</head>\n<body>\n<a class=\"skip\" href=\"#main\">Skip to content</a>\n"
        "<header class=\"topbar\"><div class=\"wrap topbar-in\"><a class=\"brand\" href=\"../../index.html\">"
        "<span class=\"mark\">NBA1</span><span class=\"brand-txt\">Originated lines &amp; strategy lab</span></a>"
        "</div></header>\n<main id=\"main\" class=\"wrap\">\n" + "\n".join(body) +
        "\n</main>\n</body>\n</html>\n")


def build():
    results = load_results()
    rows, flags, sample_games = [], [], []
    for fname in SCOPE_GAMEBOOKS:
        path = os.path.join(GAMEBOOKS, fname)
        m = re.match(r"(\d{4}-\d{2}-\d{2})_([A-Z]{3})([A-Z]{3})\.md$", fname)
        if not m:
            raise SystemExit("unexpected gamebook file name: %s" % fname)
        date, away, home = m.group(1), m.group(2), m.group(3)
        raw = open(path, encoding="utf-8").read()
        if not os.path.exists(path):
            raise SystemExit("scope gamebook missing: %s" % fname)
        gb = RX_GB_URL.search("\n".join(raw.splitlines()[:6]))
        if not gb:
            raise SystemExit("no statsdmz source URL in header of %s" % fname)
        gb_url = gb.group(1)
        if gb.group(2) != away + home:
            raise SystemExit("gamebook URL %s does not match file %s" % (gb_url, fname))
        res = results.get((date, away, home))
        if res is None:
            raise SystemExit("no official final in results feed for %s" % fname)
        meta, teams, _ = cpl.parse_gamebook(path)
        if len(teams) != 2:
            raise SystemExit("expected two team blocks in %s" % fname)
        tot_lines = printed_totals(raw)
        ot_periods = res.get("ot_periods") or 0
        # five players on the floor for the full game clock: 5 x (48:00 + 5:00 per OT) = 240:00 or 265:00 for one OT
        expected_total = 5 * (48 * 60 + 300 * ot_periods)
        for _line, _secs in tot_lines:
            if _secs != expected_total:
                raise SystemExit("%s: printed team total %s != %s (5 x game clock, %d OT)" % (fname, _fmt(_secs), _fmt(expected_total), ot_periods))
        inactive = cpl.inactive_lists(raw)
        sample_games.append({"date": date, "away": away, "home": home,
                             "game_id": res["game_id"], "gamebook_pdf": gb_url,
                             "game_page": res["source_url"]})
        final_pts = {"away": res["away_pts"], "home": res["home_pts"]}
        abbr = {"away": away, "home": home}
        opp = {"away": home, "home": away}
        for side, tdata, (printed, printed_secs) in (("away", teams[0], tot_lines[0]), ("home", teams[1], tot_lines[1])):
            played = [r for r in tdata["rows"] if r["played"]]
            secs = sum(r["minutes_seconds"] for r in played)
            pts = sum(r["pts"] for r in tdata["rows"] if r["pts"] is not None)
            if pts != final_pts[side]:
                raise SystemExit("%s %s: player points %s != official final %s" % (fname, side, pts, final_pts[side]))
            if secs != printed_secs:
                flags.append({
                    "kind": "minutes_sum_mismatch",
                    "game": "%s %s @ %s" % (date, away, home),
                    "team": abbr[side],
                    "player_sum": _fmt(secs),
                    "printed_total": _fmt(printed_secs),
                    "treatment": "printed total used as denominator; difference not redistributed",
                    "source": gb_url,
                })
            ranked = sorted(played, key=lambda r: (-r["minutes_seconds"], r["player"]))
            top8 = ranked[:8]
            tie = len(ranked) > 8 and ranked[7]["minutes_seconds"] == ranked[8]["minutes_seconds"]
            top8_secs = sum(r["minutes_seconds"] for r in top8)
            outs = []
            for r in tdata["rows"]:
                if not r["played"]:
                    outs.append({"player": r["player"], "official_note": (r.get("dnp_note") or "").strip() or "not played"})
            inact_key = None
            if inactive:
                # the gamebook labels each Inactive line with the team's short name
                for k in inactive:
                    if k.lower() in (tdata["team_name"].lower(), tdata["team_name"].split()[-1].lower()):
                        inact_key = k
                if inact_key is None and len(inactive) == 2:
                    inact_key = list(inactive.keys())[0 if side == "away" else 1]
            inactive_names = inactive[inact_key]["raw"] if inact_key else None
            rows.append({
                "date": date,
                "game": "%s %s @ %s" % (date, away, home),
                "side": side,
                "team": abbr[side],
                "team_name": tdata["team_name"],
                "opponent": opp[side],
                "team_final": final_pts[side],
                "players_played": len(played),
                "player_minutes_sum": _fmt(secs),
                "printed_team_total": _fmt(printed_secs),
                "overtime_periods": ot_periods,
                "top8_share": round(top8_secs / printed_secs, 4),
                "top8": [{"player": r["player"], "min": r["min"],
                          "share": round(r["minutes_seconds"] / printed_secs, 4)} for r in top8],
                "bench_share": round(1 - top8_secs / printed_secs, 4),
                "tie_at_8": bool(tie),
                "out_or_not_played": outs,
                "inactive_official": inactive_names,
                "source_game_page": res["source_url"],
                "source_gamebook_pdf": gb_url,
            })
    rows.sort(key=lambda r: (r["date"], r["game"], r["side"]))
    doc = {
        "title": "Measured minutes shares per team — official gamebooks, 2026-11-15",
        "generated_by": "scripts/build_minutes_shares.py",
        "session": "arena/2042a559-nba1 (COORDINATION §50, task Q02)",
        "method": ("Each player's minutes share = his printed minutes (seconds) / the printed team total "
                   "(240:00, or 265:00 in a game with one overtime period). Top-8 share = the eight largest shares summed. Bench share = 1 − top-8 "
                   "share. Out = players with no minutes in the gamebook, with the official note printed for them."),
        "sample": {
            "date": "2026-11-15",
            "games": len(sample_games),
            "team_games": len(rows),
            "teams_measured": len({r["team"] for r in rows}),
            "games_per_team": 1,
            "reading": ("One game per team. These are observations of one game day, not rates: they cannot "
                        "show how a team's minutes change when a player is absent."),
        },
        "replacement_shares": {
            "status": "blocked",
            "reason": ("Replacement share = the minutes a teammate gains when a named player is out. "
                       "Measuring it needs the same team's games with and without that player. The "
                       "repository holds one date, so there is no with/without contrast for any player."),
            "unblock": ("Capture the official gamebook for every completed 2026-27 game (the same statsdmz "
                        "PDFs), parse them with scripts/capture_player_logs.py, and compare each player's "
                        "minutes in games he missed against games he played."),
        },
        "games": sample_games,
        "scope_note": ("Six gamebooks (Q02 scope). Excluded, not measured here: " + ", ".join(
            EXCLUDED_GAMEBOOKS) + ". Their files exist under data/official/gamebooks/ and parse with the same code."),
        "rows": rows,
        "flags": flags,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return doc


def main():
    doc = build()
    with open(PAGE, "w", encoding="utf-8") as fh:
        fh.write(render_page(doc))
    print("wrote", os.path.relpath(PAGE, ROOT))
    print("games: %d  team-games: %d  teams: %d  flags: %d" %
          (doc["sample"]["games"], doc["sample"]["team_games"], doc["sample"]["teams_measured"], len(doc["flags"])))
    print("wrote", os.path.relpath(OUT, ROOT))


if __name__ == "__main__":
    main()
