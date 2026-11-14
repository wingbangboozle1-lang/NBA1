#!/usr/bin/env python3
"""Build the Edge Lab pages (lines.html, gameflow.html) from verified data.

Sources (all official NBA-operated):
  data/slate_full.json       schedule/records/prior results — nba.com slate + game pages
  data/injuries_0515.json    official injury report PDF 11/13/26 05:15 PM ET
  data/leaders.json          official season-leader tables on nba.com slate pages

Outputs:
  data/originated_lines.json audit record of every model output (reproducible)
  lines.html                 originated lines, picks, parlays, props, correlation, leaderboard
  gameflow.html              injury impact + rest/schedule game-flow analysis

Model "RecordLine-1" parameters below are THIS PROJECT'S ASSUMPTIONS, not official
values. They are rendered as assumptions on the page and flagged. Outputs are
model-originated paper picks — never presented as market prices or validated bets.

Fails (exit 1) when a data row that must have a source has none, or when a source
host is outside the allow-list, or when a rendered table row lacks an official link.
"""
import html
import json
import math
import os
import re
import sys
from datetime import date
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

ALLOWED_HOSTS = {
    "www.nba.com", "nba.com", "official.nba.com", "ak-static.cms.nba.com", "cdn.nba.com",
}

# ---- Model RecordLine-1 assumptions (documented, flagged, not official) ----
PRIOR_W, PRIOR_G = 3.0, 6.0     # smoothing: +3 wins / +6 games toward .500
HCA = 2.5                        # home-court points
K = 35.0                         # points per 1.000 smoothed win-pct difference
SIGMA = 11.0                     # points scale for win probability
CONF_MARGIN = 3.0                # pick gate: |expected margin| >= 3.0
PROP_ROUND = 0.5                 # prop combo line rounding step

errors = []


def load(name):
    with open(os.path.join(DATA, name + ".json"), encoding="utf-8") as f:
        return json.load(f)


def esc(v):
    return html.escape("" if v is None else str(v))


def check_url(url, where, required=True):
    if not url:
        if required:
            errors.append(f"{where}: missing source link")
        return
    p = urlparse(url)
    if p.scheme != "https" or p.netloc not in ALLOWED_HOSTS:
        errors.append(f"{where}: source host not allowed: {url}")


def a(url, label):
    check_url(url, f"link {label}")
    return f'<a href="{esc(url)}" target="_blank" rel="noopener">{esc(label)}</a>'


def fmt(v, nd=1):
    if v is None:
        return "—"
    return f"{v:.{nd}f}"


def parse_rec(rec):
    if not rec or "-" not in rec:
        return None, None
    w, l = rec.split("-")
    return int(w), int(l)


def smoothed(w, g):
    return (w + PRIOR_W) / (g + PRIOR_G)


def home_margin(p_home, p_away):
    return K * (p_home - p_away) + HCA


def p_home_win(margin):
    return 1.0 / (1.0 + math.exp(-margin / SIGMA))


def round_half(x):
    return round(x * 2) / 2


# ---------------------------------------------------------------- data
slate = load("slate_full")
inj = load("injuries_0515")
leaders = load("leaders")

# flatten games
games = []
for s in slate["slates"]:
    for g in s["games"]:
        row = dict(g)
        row["date"] = s["date"]
        row["slate_url"] = s["slate_url"]
        games.append(row)

# ------------------------------------------------- rest / back-to-back
# last game date per team from prior_games + earlier window slates
last_game = {}  # team -> (date, slate_url)
for p in slate["prior_games"]:
    for g in p["games"]:
        for t in (g["away"], g["home"]):
            last_game[t] = (p["date"], p["slate_url"])

rest_info = {}  # (date, team) -> dict
for s in slate["slates"]:
    d = date.fromisoformat(s["date"])
    for g in s["games"]:
        for t, url in ((g["away"], s["slate_url"]), (g["home"], s["slate_url"])):
            lg = last_game.get(t)
            if lg is None:
                rest_info[(s["date"], t)] = {"rest_days": None, "b2b": None,
                                             "last_date": None, "last_slate_url": None}
            else:
                ld = date.fromisoformat(lg[0])
                rest_days = (d - ld).days - 1
                rest_info[(s["date"], t)] = {
                    "rest_days": rest_days, "b2b": rest_days == 0,
                    "last_date": lg[0], "last_slate_url": lg[1]}
        # advance last_game with this game (window-internal chains)
        for t in (g["away"], g["home"]):
            last_game[t] = (s["date"], s["slate_url"])

# sanity: every team in window must have a prior game in Nov 9-16 data
for k, v in rest_info.items():
    if v["rest_days"] is None:
        errors.append(f"rest: no prior game found for {k}")

# ------------------------------------------------- originated lines + picks
for g in games:
    aw, al = parse_rec(g["away_record"])
    hw, hl = parse_rec(g["home_record"])
    if None in (aw, al, hw, hl):
        g["model"] = None
        continue
    p_a = smoothed(aw, aw + al)
    p_h = smoothed(hw, hw + hl)
    margin = home_margin(p_h, p_a)
    ph = p_home_win(margin)
    spread_home = -round_half(margin)  # home line (negative = home favored)
    if spread_home == 0:
        spread_home = 0.0  # avoid '-0.0' display
    if margin >= CONF_MARGIN:
        pick_side, pick_line = "HOME", f"{g['home']} {spread_home:+.1f}"
    elif margin <= -CONF_MARGIN:
        pick_side, pick_line = "AWAY", f"{g['away']} {-spread_home:+.1f}"
    else:
        pick_side, pick_line = "PASS", None
    g["model"] = {
        "p_home_smoothed": round(p_h, 3),
        "p_away_smoothed": round(p_a, 3),
        "expected_margin_home": round(margin, 1),
        "originated_spread_home": spread_home,
        "p_home_win": round(ph, 3),
        "ml_home_decimal": round(1.0 / ph, 2),
        "ml_away_decimal": round(1.0 / (1.0 - ph), 2),
        "pick_side": pick_side,
        "pick_line": pick_line,
        "gate": ("G-CFG pass (|margin| ≥ 3.0); paper pick — G4/G5 market gates blocked"
                 if pick_side != "PASS" else "G-CFG fail (|margin| < 3.0) — no bet"),
    }

n_picks = sum(1 for g in games if g.get("model") and g["model"]["pick_side"] != "PASS")

# ------------------------------------------------- player status lookup
def name_key(name):
    parts = re.split(r"[^A-Za-z]+", name.lower())
    return frozenset(p for p in parts if p)


# Latest official edition per game date (session arena/f80dcc4a-nba1, W05):
#   2026-11-13 games -> the 05:15 PM ET edition (inj) — FROZEN basis of the published 11/13 batch
#   2026-11-14 games -> the 08:00 PM ET edition (inj0800), the newest published edition at 2026-11-14T01:12Z,
#                       which prints status rows for all five 11/14 games (source: its hub listing)
#   2026-11-15..17   -> no report published yet at capture time; rows stay gated (G-INJ)
with open(os.path.join(DATA, "raw", "injury_report_2026-11-13_08_00PM.json"), encoding="utf-8") as _f:
    inj0800 = json.load(_f)
check_url(inj0800["source_url"], "injury report 8:00 PM edition")

status_index = {}  # (date, team, namekey) -> (status, reason)
nys_teams = set()  # (date, team) pairs whose submission read NOT YET SUBMITTED
for r in inj["rows"]:
    if r["player"]:
        status_index[(r["game_date"], r["team"], name_key(r["player"]))] = (r["status"], r["reason"])
    elif r.get("team") and r["status"] == "NOT YET SUBMITTED":
        nys_teams.add((r["game_date"], r["team"]))
for r in inj0800["rows"]:
    if r["game_date"] != "2026-11-14":
        continue  # 11/13 rows of this edition are informational only; 11/13 stays on the frozen 05:15 PM basis
    if r["player"] and r.get("team"):
        status_index[(r["game_date"], r["team"], name_key(r["player"]))] = (r["status"], r["reason"])
    elif r.get("team") and r["status"] == "NOT YET SUBMITTED":
        nys_teams.add((r["game_date"], r["team"]))


def edition_for(date_str):
    """Which official injury-report edition covers this game date at build time."""
    if date_str == "2026-11-13":
        return inj
    if date_str == "2026-11-14":
        return inj0800
    return None  # day-before reports for 11/15-11/17 not yet published at capture (flag W-F2)

team_abbr_to_name = {}
for g in games:
    team_abbr_to_name[g["away"]] = g["away_name"]
    team_abbr_to_name[g["home"]] = g["home_name"]
name_to_abbr = {v: k for k, v in team_abbr_to_name.items()}

leader_by_team = {l["team"]: l for l in leaders["leaders"]}

# ------------------------------------------------- prop combos
prop_rows = []
for g in games:
    for side in ("away", "home"):
        abbr = g[side]
        lg = leader_by_team.get(abbr)
        if lg is None:
            continue
        src = lg["source_url"]
        check_url(src, f"leader {abbr}")
        team_name = g[f"{side}_name"]
        if lg["player"] is None:
            prop_rows.append({
                "date": g["date"], "game": f"{g['away']}@{g['home']}", "team": team_name,
                "player": None, "ppg": None, "rpg": None, "apg": None, "line": None,
                "status": None, "status_reason": None,
                "signal": "BLANK — leader stats not displayed on official page (flagged)",
                "src_leader": src, "src_inj": (edition_for(g["date"]) or inj)["source_url"] if edition_for(g["date"]) else inj["hub_url"],
                "blank": lg.get("blank_reason"),
            })
            continue
        combo = round((lg["ppg"] + lg["rpg"] + lg["apg"]) / PROP_ROUND) * PROP_ROUND
        st = status_index.get((g["date"], team_name, name_key(lg["player"])))
        ed = edition_for(g["date"])
        src_inj = ed["source_url"] if ed else inj["hub_url"]
        if ed is None:
            status = "Report not yet published for this date"
            status_reason = None
            sig = "BLOCKED — status report not yet due/published (G-INJ)"
        elif st is None and (g["date"], team_name) in nys_teams:
            status = "Team report NOT YET SUBMITTED"
            status_reason = None
            sig = "BLOCKED — team report not yet submitted (G-INJ)"
        elif st is None:
            status = "Not listed on report"
            status_reason = None
            sig = "BLOCKED — no market number, no game-log variance (G-PROP)"
        else:
            status, status_reason = st
            if status in ("Out", "Doubtful"):
                sig = "NO BET — officially out/doubtful"
            elif status == "Questionable":
                sig = "PASS — availability risk unquantified"
            else:
                sig = "BLOCKED — no market number, no game-log variance (G-PROP)"
        prop_rows.append({
            "date": g["date"], "game": f"{g['away']}@{g['home']}", "team": team_name,
            "player": lg["player"], "ppg": lg["ppg"], "rpg": lg["rpg"], "apg": lg["apg"],
            "line": combo, "status": status, "status_reason": status_reason,
            "signal": sig, "src_leader": src, "src_inj": src_inj, "blank": None,
        })

# ------------------------------------------------- parlays (Fréchet bounds)
def rho_bounds(p1, p2):
    denom = math.sqrt(p1 * (1 - p1) * p2 * (1 - p2))
    if denom == 0:
        return None, None
    lb_joint = max(0.0, p1 + p2 - 1.0)
    ub_joint = min(p1, p2)
    rho_lb = (lb_joint - p1 * p2) / denom
    rho_ub = (ub_joint - p1 * p2) / denom
    return rho_lb, rho_ub


parlay_rows = []
by_date = {}
for g in games:
    if g.get("model") and g["model"]["pick_side"] != "PASS":
        by_date.setdefault(g["date"], []).append(g)
for d, picks in sorted(by_date.items()):
    picks = sorted(picks, key=lambda x: -x["model"]["p_home_win"] if x["model"]["pick_side"] == "HOME"
                   else -(1 - x["model"]["p_home_win"]))
    pairs = [(0, 1), (0, 2), (1, 2)]
    for i, j in pairs:
        if i >= len(picks) or j >= len(picks):
            continue
        g1, g2 = picks[i], picks[j]

        def leg_prob(g):
            m = g["model"]
            return m["p_home_win"] if m["pick_side"] == "HOME" else 1 - m["p_home_win"]

        p1, p2 = leg_prob(g1), leg_prob(g2)
        rho_lb, rho_ub = rho_bounds(p1, p2)
        lb_joint = max(0.0, p1 + p2 - 1.0)
        ub_joint = min(p1, p2)
        parlay_rows.append({
            "date": d,
            "leg1": f"{g1['away']}@{g1['home']} — {g1['model']['pick_line']}",
            "leg2": f"{g2['away']}@{g2['home']} — {g2['model']['pick_line']}",
            "p1": round(p1, 3), "p2": round(p2, 3),
            "joint_lb": round(lb_joint, 3), "joint_ub": round(ub_joint, 3),
            "rho_lb": None if rho_lb is None else round(rho_lb, 3),
            "rho_ub": None if rho_ub is None else round(rho_ub, 3),
            "fair_odds_lb": round(1.0 / ub_joint, 2) if ub_joint > 0 else None,
            "fair_odds_ub": round(1.0 / lb_joint, 2) if lb_joint > 0 else None,
            "src1": g1["preview_url"], "src2": g2["preview_url"],
        })

# ------------------------------------------------- injury impact (per game)
abbr_to_full = team_abbr_to_name
full_to_abbr = name_to_abbr

inj_impact = []
for g in games:
    ed = edition_for(g["date"])
    entry = {"date": g["date"], "game": f"{g['away']}@{g['home']}", "preview": g["preview_url"],
             "slate": g["slate_url"], "teams": []}
    for side in ("away", "home"):
        abbr = g[side]
        team_name = g[f"{side}_name"]
        rows = [r for r in (ed["rows"] if ed else []) if r["team"] == team_name and r["game_date"] == g["date"]]
        outs = [r for r in rows if r["status"] == "Out" and r["player"]]
        doubtful = [r for r in rows if r["status"] == "Doubtful"]
        quest = [r for r in rows if r["status"] == "Questionable"]
        prob = [r for r in rows if r["status"] == "Probable"]
        nys = any(r["status"] == "NOT YET SUBMITTED" for r in rows)
        lg = leader_by_team.get(abbr)
        known_out_ppg = []
        unknown_out = 0
        for r in outs:
            if lg and lg["player"] and name_key(lg["player"]) == name_key(r["player"]) and lg["ppg"] is not None:
                known_out_ppg.append((r["player"], lg["ppg"]))
            else:
                unknown_out += 1
        entry["teams"].append({
            "team": team_name, "n_out": len(outs), "doubtful": len(doubtful),
            "questionable": len(quest), "probable": len(prob),
            "nys": nys, "no_report": ed is None,
            "known_out_ppg": known_out_ppg,
            "unknown_out": unknown_out,
            "out_names": [r["player"] for r in outs],
            "src": ed["source_url"] if ed else inj["hub_url"],
        })
    inj_impact.append(entry)

# ------------------------------------------------- audit record
audit = {
    "model": "RecordLine-1",
    "assumptions": {
        "smoothing": f"+{PRIOR_W:.0f} wins / +{PRIOR_G:.0f} games toward .500",
        "home_court_points": HCA, "scale_K": K, "sigma": SIGMA,
        "pick_gate_margin": CONF_MARGIN,
        "note": "All parameters are this project's assumptions, not official values. "
                "Totals are not originated (no pace/efficiency inputs). Market comparison "
                "gates (G4/G5) are blocked: no odds feed is connected.",
    },
    "inputs_basis": {
        "records": "per-slate records_as_of stamps in data/slate_full.json (11/13 rows frozen at 2026-11-13T22:45Z pick basis; 11/14-11/17 re-verified against official slate pages 2026-11-14T00:52-01:32Z — see data/raw/records_2026-11-14.json)",
        "injury_editions": {
            "2026-11-13": "injuries_0515.json (official PDF 11/13/26 05:15 PM ET) — frozen basis of the published 11/13 batch",
            "2026-11-14": "data/raw/injury_report_2026-11-13_08_00PM.json (official PDF 11/13/26 08:00 PM ET, newest published edition at capture 2026-11-14T01:12Z; prints rows for all five 11/14 games)",
            "2026-11-15..17": "no edition published at capture time (day-before deadlines not reached) — prop/impact rows gated G-INJ, hub: https://official.nba.com/nba-injury-report-2026-27-season/",
        },
    },
    "generated_at_utc": slate["as_of_utc"],
    "games": [
        {
            "date": g["date"], "matchup": f"{g['away']}@{g['home']}", "time_et": g["time_et"],
            "away_record": g["away_record"], "home_record": g["home_record"],
            "rest_away": rest_info[(g["date"], g["away"])],
            "rest_home": rest_info[(g["date"], g["home"])],
            "model": g["model"],
            "sources": [g["slate_url"], g["preview_url"]],
        }
        for g in games
    ],
    "parlays": parlay_rows,
    "prop_rows": prop_rows,
    "n_model_picks": n_picks,
}
with open(os.path.join(DATA, "originated_lines.json"), "w", encoding="utf-8") as f:
    json.dump(audit, f, indent=1, ensure_ascii=False)

# ==================================================================== pages
NAV = [
    ("index.html", "Executive summary"),
    ("lines.html", "Originated lines & picks"),
    ("gameflow.html", "Injuries & game flow"),
    ("research.html", "Strategy lab"),
    ("slate.html", "Upcoming slate"),
    ("suggestions.html", "Questions & suggestions"),
    ("review.html", "Flagged for review"),
    ("sources.html", "Source register"),
]


def page(filename, title, body, active):
    links = []
    for href, label in NAV:
        cls = ' class="active"' if href == active else ""
        links.append(f'<a href="{href}"{cls}>{esc(label)}</a>')
    nav = "".join(links)
    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)} | NBA Lines Lab</title><link rel="stylesheet" href="subpages.css"></head><body><header class="topbar"><div class="top-inner"><a class="brand" href="index.html"><span class="brand-mark">N</span> NBA Lines Lab</a><div class="top-note">Edge Lab · data as of 2026-11-14 · official sources only</div></div></header><div class="layout"><nav class="side" aria-label="Main navigation"><div class="nav-label">Workspace</div>{nav}<div class="side-foot">Every data row links to an official NBA source.<br>Blank = unverified, never zero.</div></nav><main class="main">{body}</main></div>
<footer class="foot"><p>Model outputs are paper records, not betting advice. Gambling in NL is regulated — see <a href="suggestions.html">Questions &amp; suggestions (Q-03/Q-04)</a>. Assumptions are flagged; unverified values are blank.</p><p>Generated by <code>scripts/build_edge_site.py</code> from <code>data/*.json</code>.</p></footer>
<script src="app.js"></script></body></html>"""
    with open(os.path.join(ROOT, filename), "w", encoding="utf-8") as f:
        f.write(doc)


def table(headers, rows, tid):
    head = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body = []
    for r in rows:
        cells = []
        for c in r:
            cells.append(c if isinstance(c, str) and (c.startswith("<a ") or c.startswith("<span")) else f"<td>{esc(c)}</td>")
        # allow raw cell strings that are anchors
        out = []
        for c in r:
            if isinstance(c, str) and c.startswith(("<a ", "<span", "<em", "<strong", "<b")):
                out.append(f"<td>{c}</td>")
            else:
                out.append(f"<td>{esc(c)}</td>")
        body.append("<tr>" + "".join(out) + "</tr>")
    search = (f'<input class="filter" type="search" placeholder="Filter rows…" '
              f'data-target="{tid}" aria-label="Filter rows">')
    return (f'{search}<div class="tablewrap"><table id="{tid}"><thead><tr>{head}</tr></thead>'
            f'<tbody>{"".join(body)}</tbody></table></div>')


def verify_row_links(html_text, name):
    """Every tbody row on the page must contain an official https link."""
    from html.parser import HTMLParser

    class P(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.in_row = False
            self.in_tbody = False
            self.links = []
            self.bad = []

        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if tag == "tbody":
                self.in_tbody = True
            if tag == "tr" and self.in_tbody:
                self.in_row, self.links = True, []
            if tag == "a" and self.in_row and attrs.get("href"):
                self.links.append(attrs["href"])

        def handle_endtag(self, tag):
            if tag == "tr" and self.in_row:
                ok = any((urlparse(h).hostname or "") in ALLOWED_HOSTS for h in self.links)
                if not ok:
                    self.bad.append(self.getpos())
                self.in_row = False
            if tag == "tbody":
                self.in_tbody = False

    p = P()
    p.feed(html_text)
    for pos in p.bad:
        errors.append(f"{name}: table row without official source link at {pos}")


# ------------------------------------------------------------ lines.html
slate_blocks = []
for s in slate["slates"]:
    rows = []
    for g in [x for x in games if x["date"] == s["date"]]:
        m = g["model"]
        ra = rest_info[(g["date"], g["away"])]
        rh = rest_info[(g["date"], g["home"])]
        b2b = (" · B2B" if ra["b2b"] else "") , (" · B2B" if rh["b2b"] else "")
        rest_cell = f"{fmt(ra['rest_days'],0)}d{b2b[0]} / {fmt(rh['rest_days'],0)}d{b2b[1]}"
        if m is None:
            spread = pcell = ml = pick = "— (record blank)"
        else:
            fav = g["home"] if m["expected_margin_home"] > 0 else g["away"]
            spread = f"{g['home']} {m['originated_spread_home']:+.1f}"
            pcell = fmt(m["p_home_win"], 3)
            ml = f"H {m['ml_home_decimal']:.2f} / A {m['ml_away_decimal']:.2f}"
            if m["pick_side"] == "PASS":
                pick = '<span class="flag">PASS — gate G-CFG</span>'
            else:
                pick = f'<strong>{esc(m["pick_line"])}</strong> <span class="tag">paper</span>'
        rows.append([
            esc(g["time_et"]),
            f"{esc(g['away'])} ({esc(g['away_record'])}) @ {esc(g['home'])} ({esc(g['home_record'])})",
            esc(rest_cell), esc(spread), esc(pcell), esc(ml), pick,
            a(g["slate_url"], "slate"), a(g["preview_url"], "game"),
        ])
    slate_blocks.append(
        f"<h3>{esc(s['date'])} — {len(rows)} games</h3>" +
        table(["Time (ET)", "Matchup (records)", "Rest away / home", "Originated spread (home)",
               "P(home win)", "Fair ML decimal", "Model pick", "Slate source", "Game source"],
              rows, f"slate-{s['date']}"))

parlay_tbl = table(
    ["Date", "Leg 1", "Leg 2", "P(leg1)", "P(leg2)", "P(joint) bounds", "ρ bounds (from marginals)",
     "Fair decimal odds range", "Status", "Sources"],
    [[esc(p["date"]), esc(p["leg1"]), esc(p["leg2"]), fmt(p["p1"], 3), fmt(p["p2"], 3),
      f"[{fmt(p['joint_lb'], 3)}, {fmt(p['joint_ub'], 3)}]",
      f"[{fmt(p['rho_lb'], 3)}, {fmt(p['rho_ub'], 3)}]",
      f"{fmt(p['fair_odds_lb'], 2)} – {fmt(p['fair_odds_ub'], 2)}",
      '<span class="flag">BLOCKED — no market price (G4/G5); empirical ρ pending game logs (G7)</span>',
      a(p["src1"], "game 1") + " " + a(p["src2"], "game 2")]
     for p in parlay_rows],
    "parlays")

prop_tbl = table(
    ["Date", "Game", "Team", "Player", "PPG", "RPG", "APG", "Originated combo line (P+R+A)",
     "Status (official report)", "Signal / gate", "Leader source", "Status source"],
    [[esc(r["date"]), esc(r["game"]), esc(r["team"]),
      esc(r["player"]) if r["player"] else '<span class="flag">blank — not displayed (flagged)</span>',
      fmt(r["ppg"]) if r["ppg"] is not None else '<span class="flag">blank</span>',
      fmt(r["rpg"]) if r["rpg"] is not None else '<span class="flag">blank</span>',
      fmt(r["apg"]) if r["apg"] is not None else '<span class="flag">blank</span>',
      fmt(r["line"]) if r["line"] is not None else '<span class="flag">blank</span>',
      esc(r["status"]) if r["status"] else '<span class="flag">blank</span>',
      esc(r["signal"]),
      a(r["src_leader"], "leaders"), a(r["src_inj"], "report")]
     for r in prop_rows],
    "props")

corr_struct = """
<ul class="bullets">
<li><strong>Same-game parlays:</strong> legs share pace and game script, so joint outcomes are generally not independent. Point estimate of ρ requires co-occurrence counts from official game logs — <em>pending (blank), never estimated by feel</em>.</li>
<li><strong>Cross-game parlays (the cards above):</strong> different games are treated as only bounded-dependent — ρ is therefore reported as an interval implied by the marginals (Fréchet–Hoeffding bounds), which is exact given only the two probabilities.</li>
<li><strong>Spread vs total (same game):</strong> mechanically linked through margin and pace; quantitative value pending official play-by-play — blank.</li>
<li><strong>Player combo vs team win:</strong> direction ambiguous (blowouts cut star minutes); value pending game logs — blank.</li>
<li><strong>Prop legs of the same player (e.g., Pts and Ast):</strong> positively co-driven by usage; empirical value pending — blank.</li>
</ul>"""

board_rows = [
    ["S-01", "Single bet — model moneyline favorite (RecordLine-1)", "PAPER",
     "G1 pass · G-CFG pass · G2/G3/G4/G5/G6/G8 not run", "", "",
     a("https://www.nba.com/games?date=2026-11-13", "slate basis")],
    ["S-02", "Single bet — model spread side at originated line", "PAPER",
     "G1 pass · G-CFG pass · G2/G3/G4/G5/G6/G8 not run", "", "",
     a("https://www.nba.com/games?date=2026-11-13", "slate basis")],
    ["S-03", "2-leg cross-game parlay (Fréchet-bounded)", "GATED",
     "G1 pass · G7 blocked (empirical ρ) · G4/G5 blocked (no odds)", "", "",
     a("https://www.nba.com/games?date=2026-11-13", "slate basis")],
    ["S-04", "Player prop combo (Pts+Reb+Ast)", "GATED",
     "G1 pass · G-PROP blocked (no market number / no game logs)", "", "",
     a("https://official.nba.com/nba-injury-report-2026-27-season/", "status rules")],
    ["S-05", "Injury-availability prop filter", "GATED",
     "G1 pass · G-INJ blocked for 11/15–17 (reports not yet published)", "", "",
     a("https://official.nba.com/nba-injury-report-2026-27-season/", "status rules")],
]
leaderboard = table(
    ["ID", "Strategy", "Status", "Gates", "Settled record", "ROI", "Source"],
    [[esc(c) if not isinstance(c, str) or not c.startswith("<a") else c for c in row]
     for row in board_rows],
    "leaderboard")
# blanks in record/ROI must render as flagged blanks
leaderboard = leaderboard.replace("<td></td>", '<td><span class="flag">blank — no settled results yet</span></td>')

lines_body = f"""
<p class="crumb">Workspace / Originated lines & picks</p>
<header class="page-head"><div class="kicker">Edge Lab</div><h1>Originated lines & picks</h1>
<p>Our own lines for every game in the window (Nov 13–17, 2026), generated by model <strong>RecordLine-1</strong> from official NBA records. The Nov 13 rows are the frozen pick basis published before that slate tipped; the Nov 14–17 rows are today's slate plus the maximum three days ahead the brief asks for. These are <em>our</em> numbers — not sportsbook prices. Every pick is a paper record gated behind the validation framework.</p></header>

<div class="notice warn"><strong>Read this first.</strong> Model parameters below are documented assumptions, not official values. No market odds feed is connected, so market-comparison gates (G4 closing-line value, G5 price edge) are <strong>blocked</strong> — nothing here is a validated bet or betting advice. Player totals (over/under team totals) are not originated: pace/efficiency inputs are missing. See <a href="review.html" target="_blank" rel="noopener">Flagged for review</a>.</div>

<h2>Model RecordLine-1 — formula and assumptions</h2>
<ul class="bullets">
<li>Smoothed win probability: <code>p = (W + 3) / (G + 6)</code> — a +3-win / +6-game shrink toward .500 (<em>assumption</em>; early-season records are noisy).</li>
<li>Expected home margin: <code>35.0 × (p_home − p_away) + 2.5</code> — scale <code>K = 35.0</code> points per 1.000 pct difference and home-court <code>+2.5</code> pts (<em>assumptions, not official values</em>).</li>
<li>Win probability: <code>P(home) = 1 / (1 + e^(−margin / 11.0))</code> with σ = 11.0 (<em>assumption</em>).</li>
<li>Originated spread = −expected margin rounded to 0.5. Fair ML decimal odds = 1/p (no margin baked in).</li>
<li>Pick gate <strong>G-CFG</strong>: pick only when |expected margin| ≥ 3.0; otherwise PASS (no bet).</li>
<li>Inputs: official records from <a href="https://www.nba.com/games?date=2026-11-13" target="_blank" rel="noopener">NBA.com slate pages</a> (cross-checked on official game pages). Reproducible audit: <code>data/originated_lines.json</code>.</li>
</ul>

<h2>Picks by slate (Nov 13–17, 2026)</h2>
<p class="note">Rest = days off before the game, computed only from official NBA schedule pages for Nov 9–17 (B2B = back-to-back). Record basis: the Nov 13 rows use the records as displayed 2026-11-13 pre-tip (frozen); the Nov 14–17 rows use records re-read from the official slate pages 2026-11-14T00:52–01:32Z (transcripts in <code>data/raw/captures/session-w/</code>), when the Nov 13 games were still in progress and therefore not yet included in any record. "Paper" = model pick, not market-validated.</p>
{"".join(slate_blocks)}

<h2>Parlay cards (cross-game, 2 legs) — correlation as bounds, not guesses</h2>
<p class="note">Joint-probability bounds are Fréchet–Hoeffding bounds computed exactly from the two model marginals; ρ bounds follow from those joints. The independence price (1/(p₁·p₂)) is an assumption, shown only inside the bounds. Empirical ρ and market prices are pending → status BLOCKED.</p>
{parlay_tbl}

<h2>Player prop combos (Pts + Reb + Ast)</h2>
<p class="note">Originated line = official season PPG+RPG+APG (sum, rounded to 0.5) from NBA.com leader tables; status from the official injury-report edition covering each game date (11/13 games: the 5:15 PM ET edition; 11/14 games: the 8:00 PM ET edition of 11/13, the newest published at capture; 11/15–11/17: no report published yet at capture → gated). No market number exists to beat, so every signal stays gated: Out/Doubtful → NO BET; Questionable → PASS; otherwise BLOCKED pending market number + game-log variance. The LAL/CHA/TOR leader cells that read "-" on the 2026-11-13 capture are now displayed on the official pages and were filled from them (2026-11-14T01:31Z read).</p>
{prop_tbl}

<h2>Correlation values — what is determined and what is blank</h2>
{corr_struct}

<h2>Leaderboard (gated)</h2>
<p class="note">Settled record and ROI stay blank until each strategy clears its gates. A blank is never a zero.</p>
{leaderboard}
"""
page("lines.html", "Originated lines & picks", lines_body, "lines.html")

# ------------------------------------------------------------ gameflow.html
impact_blocks = []
for e in inj_impact:
    rows = []
    for t in e["teams"]:
        if t.get("no_report"):
            out_cell = '<span class="flag">report not yet published (G-INJ)</span>'
            known = "—"
        elif t["nys"]:
            out_cell = '<span class="flag">NOT YET SUBMITTED</span>'
            known = "—"
        else:
            out_cell = str(t["n_out"])
            if t["known_out_ppg"]:
                known = ", ".join(f"{esc(n)} ({fmt(p)} PPG)" for n, p in t["known_out_ppg"])
            else:
                known = '<span class="flag">blank — leader PPG unknown</span>' if t["n_out"] else "—"
        rows.append([
            esc(t["team"]), out_cell,
            "—" if t.get("no_report") else fmt(t["doubtful"], 0),
            "—" if t.get("no_report") else fmt(t["questionable"], 0),
            "—" if t.get("no_report") else fmt(t["probable"], 0), known,
            esc(", ".join(t["out_names"])) if t["out_names"] and not t["nys"] and not t.get("no_report") else "—",
            a(t["src"], "report"), a(e["preview"], "game"),
        ])
    impact_blocks.append(
        f"<h3>{esc(e['date'])} · {esc(e['game'])}</h3>" +
        table(["Team", "Out", "Doubtful", "Questionable", "Probable",
               "Known PPG of officially-out leader", "Out players (as printed)", "Report source", "Game source"],
              rows, f"impact-{e['date']}-{e['game'].replace('@','-')}"))

unattr_all = [(r, inj["source_url"], "05:15 PM ET edition") for r in inj["unattributed_rows"]] + \
             [(r, inj0800["source_url"], "08:00 PM ET edition") for r in inj0800["unattributed_rows"]]
unattr_tbl = table(
    ["Date", "Player", "Status", "Reason (as printed)", "Team", "Edition", "Source"],
    [[esc(r["game_date"]), esc(r["player"]), esc(r["status"]), esc(r["reason"]),
      '<span class="flag">blank — team cell not printed (flagged)</span>',
      esc(edition_label), a(src_url, "PDF")]
     for r, src_url, edition_label in unattr_all],
    "unattributed")

rest_rows = []
for g in games:
    ra = rest_info[(g["date"], g["away"])]
    rh = rest_info[(g["date"], g["home"])]
    rest_rows.append([
        esc(g["date"]), esc(g["time_et"]), esc(f"{g['away']}@{g['home']}"),
        f"{fmt(ra['rest_days'],0)}d" + (" · B2B" if ra["b2b"] else ""),
        f"{fmt(rh['rest_days'],0)}d" + (" · B2B" if rh["b2b"] else ""),
        esc(ra["last_date"] or "—"), esc(rh["last_date"] or "—"),
        a(ra["last_slate_url"] or g["slate_url"], "prior slate"),
        a(g["slate_url"], "slate"),
    ])
rest_tbl = table(["Date", "Time (ET)", "Matchup", "Away rest", "Home rest",
                  "Away last game", "Home last game", "Prior source", "Slate source"],
                 rest_rows, "rest")

gf_body = f"""
<p class="crumb">Workspace / Injuries & game flow</p>
<header class="page-head"><div class="kicker">Edge Lab</div><h1>Injury impact & game flow</h1>
<p>Official injury reports (the 5:15 PM ET edition for the Nov 13 games; the 8:00 PM ET edition of Nov 13 for the Nov 14 games — the newest published at capture time), rotation-impact context built only from officially printed values, and schedule-derived rest/fatigue factors for all 36 games.</p></header>

<div class="notice warn"><strong>Quantified minutes/production impact is blocked.</strong> The NBA does not publish projected minutes in the injury report, and no verified game-log/minutes feed is connected in this project. What can be stated officially: who is Out/Doubtful/Questionable/Probable, and how much scoring the officially-out <em>team leader</em> accounts for (blank where the leader's PPG is not on an official page). Everything else is left blank and flagged — no minutes are invented.</div>

<h2>Report coverage</h2>
<ul class="bullets">
<li>11/13 games — source: <a href="{esc(inj['source_url'])}" target="_blank" rel="noopener">official PDF 11/13/26 05:15 PM ET</a> (frozen basis of the published 11/13 batch). {len(inj['rows'])} attributed rows, {len(inj['unattributed_rows'])} rows with blank team (flagged below).</li>
<li>11/14 games — source: <a href="{esc(inj0800['source_url'])}" target="_blank" rel="noopener">official PDF 11/13/26 08:00 PM ET</a>, the newest edition listed on the <a href="{esc(inj0800['hub_url'])}" target="_blank" rel="noopener">official hub</a> at capture (2026-11-14T01:12Z). It prints rows for all five 11/14 games: {len([r for r in inj0800['rows'] if r['game_date']=='2026-11-14'])} attributed rows plus five NOT YET SUBMITTED team submissions (New Orleans, Cleveland, Memphis, Chicago, Miami — day-before deadlines not yet due). {len(inj0800['unattributed_rows'])} rows have blank team and are flagged below.</li>
<li>11/15, 11/16 and 11/17: day-before reports were not yet published at capture — injury columns for those slates stay gated (G-INJ) and show <i>unknown</i>, never "no injuries".</li>
<li>The 11/14-dated report editions do not exist yet at capture (they publish on 11/14); the earlier AccessDenied on the 11/14 12:00 PM URL is consistent with a not-yet-published file. Tracked as flag W-F2.</li>
<li>Always use the latest timestamped report — statuses move between editions (five status changes between the 3:00 PM and 5:15 PM editions are recorded in <code>data/audit/injury_edition_diff.json</code>).</li>
</ul>

<h2>Per-game injury impact (all games, Nov 13–17)</h2>
{"".join(impact_blocks)}

<h2>Rows with no printed team — blank, flagged, excluded from analysis</h2>
{unattr_tbl}

<h2>Rest & schedule fatigue (all 36 games, Nov 9–17 official schedule)</h2>
<p class="note">Rest days computed strictly from official NBA.com slate pages (Nov 9 through Nov 17): days off = calendar days between last scheduled game and this game minus 1. B2B = back-to-back. Every team in the window has a prior game inside Nov 9–13.</p>
{rest_tbl}

<h2>Game-flow notes (officially grounded)</h2>
<ul class="bullets">
<li><strong>Back-to-backs on 11/14:</strong> New Orleans, Cleveland, Miami, Memphis and Chicago all play 11/13 and 11/14 (0 days rest) — from the official schedule above. (An earlier draft of this note omitted Miami; corrected 2026-11-14 and flagged W-F8.)</li>
<li><strong>Back-to-backs on 11/15:</strong> Dallas only (11/14 → 11/15).</li>
<li><strong>Back-to-backs on 11/16:</strong> Boston, Philadelphia, Washington, Houston and Phoenix (all play 11/15 and 11/16).</li>
<li><strong>Back-to-backs on 11/17:</strong> Portland and Minnesota (both play 11/16 and 11/17, both at Target Center — the POR@MIN matchup repeats inside 48 hours; flagged W-F6).</li>
<li><strong>OT fatigue:</strong> Detroit beat Washington 144–140 in double OT on 11/12 (<a href="https://www.nba.com/games?date=2026-11-12" target="_blank" rel="noopener">official slate</a>); Detroit then plays 11/14 (1 day off), Washington 11/15 (2 days off).</li>
<li><strong>NBA Cup context (11/13 slate only):</strong> group labels are printed on the official game cards (East A/B/C, West A/B/C) — shown in the picks table's game links; Cup games add travel/urgency context but no verified numeric adjustment is applied to the model.</li>
<li><strong>Attrition example (official rows only):</strong> Golden State lists Curry, Butler III, Porzingis, Moody and Williams as Out at 5:15 PM; San Antonio lists Harris and Quaintance Out with Fox and Vassell Questionable — usage shifts are directionally obvious but <em>not quantified</em> (no minutes feed).</li>
</ul>
"""
page("gameflow.html", "Injuries & game flow", gf_body, "gameflow.html")

# ------------------------------------------------- verify rendered pages
for name in ("lines.html", "gameflow.html"):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        verify_row_links(f.read(), name)

if errors:
    print("EDGE BUILD FAILED")
    for e in errors:
        print("-", e)
    sys.exit(1)
print(f"built lines.html + gameflow.html · games={len(games)} model_picks={n_picks} "
      f"parlays={len(parlay_rows)} props={len(prop_rows)} impact_rows={sum(len(e['teams']) for e in inj_impact)} "
      f"unattributed={len(inj['unattributed_rows'])}")
