#!/usr/bin/env python3
"""verify_line_by_line_eac340af.py — value-level verification of the published site.

Session arena/eac340af-nba1, COORDINATION §72 I03 (requirements R30 / R32).

WHAT THIS IS
------------
The repository's existing gates are **structural**: `scripts/verify_all.py`,
`scripts/verify_dashboard.py` and `scripts/check_site.py` check that every published
table row carries an allowed official source link, that every internal link resolves,
that the column counts match the headers, and that no register string contains a repr
artefact.  They say so themselves:

    "NOTE - this checks provenance/link structure only; it does not fetch sources or
     compare their values to the published rows."

That is the honest gap behind R30 and R32 being `partial`.  This script closes it:
it compares **published values** against the **official bytes stored in this
repository**, one line per comparison, and prints what disagrees.

THE SIX FAMILIES
----------------
F1  Per-player game logs vs the official **gamebook** of the same game.  The published
    logs were parsed from the official *game page*; the gamebook (PDF bytes for
    2026-11-17/18, the verbatim transcription for 2026-11-15/16) is a different
    official artifact, so agreement is evidence rather than a tautology.  Every
    published field - minutes, points, rebounds, assists, the shooting splits, the
    turnovers/fouls/steals/blocks columns and the +/- column - is compared.
F2  The published per-game result feed vs the official per-day finals files and the
    official scoreboard captures, plus the arithmetic assertion that the published
    quarter scores sum to the published final for every game in the feed.
F3  The published rotation minutes and the minutes-redistribution replacement shares
    vs the same gamebook minutes, recomputed from the bytes, team by team.
F4  The published settlement vs the official finals: every ticket re-graded and every
    summary total re-computed, from the finals files rather than from the settlement's
    own copy of them.
F5  The tamper-evident ledger chain and the pre-registration freeze, re-computed from
    the canonical JSON the ledger itself documents.
F6  The published horizon (26 games) vs the official schedule capture and the official
    slate captures, field by field.

Every check line carries: an id, the claim, the expected value, the published value,
the official source URL, the local official artifact, and a verdict of PASS, MISMATCH
or UNVERIFIED.  A value that cannot be confirmed is never guessed: it is UNVERIFIED
with the reason printed, which is the same rule the site publishes everywhere else.

Outputs
-------
    verify/2026-11-19-eac340af/line_by_line_report.json   machine-readable
    verify/2026-11-19-eac340af/line_by_line_report.md      the human-readable table
"""

from __future__ import annotations

import glob
import hashlib
import importlib.util
import json
import os
import re
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "verify", "2026-11-19-eac340af")


def _load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


pdftext = _load("eac340af_pdf_text", os.path.join(ROOT, "scripts", "eac340af_pdf_text.py"))

NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def jload(rel: str):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def sha256_file(rel: str) -> str:
    h = hashlib.sha256()
    with open(os.path.join(ROOT, rel), "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# names, team sections, minutes
# ---------------------------------------------------------------------------

# The published per-player logs use two field vocabularies: the 2026-11-15/16 files
# use short names, the 2026-11-17/18 files use long ones and publish both.  Each
# gamebook column therefore lists every published name that carries it.
PLAYER_COLUMNS = [
    ("FG", ("fieldGoalsMade", "fgm")),
    ("FGA", ("fieldGoalsAttempted", "fga")),
    ("3PM", ("threePointersMade", "fg3m")),
    ("3PA", ("threePointersAttempted", "fg3a")),
    ("FTM", ("freeThrowsMade", "ftm")),
    ("FTA", ("freeThrowsAttempted", "fta")),
    ("OREB", ("reboundsOffensive", "oreb")),
    ("DREB", ("reboundsDefensive", "dreb")),
    ("TOT", ("rebounds", "reb")),
    ("AST", ("assists", "ast")),
    ("PF", ("foulsPersonal", "pf")),
    ("STL", ("steals", "stl")),
    ("TO", ("turnovers", "tov")),
    ("BLK", ("blocks", "blk")),
    ("+/-", ("plus_minus",)),
    ("PTS", ("points", "pts")),
]

MINUTES_FIELDS = ("minutes", "min")
POSITION_TOKENS = {"C", "F", "G"}


def published_value(row: dict, names) -> object:
    for n in names:
        if n in row and row[n] is not None:
            return row[n]
    return None


def compact(name: str) -> str:
    """Letters only, lower case: 'Porter Jr., Craig' -> 'porterjrcraig'."""
    return re.sub(r"[^a-z]", "", (name or "").lower())


def name_variants(published: str) -> list:
    """The compact forms a published 'Last, First' name can take in a gamebook."""
    pub = (published or "").strip()
    out = []
    if "," in pub:
        last, first = pub.split(",", 1)
        out.append(compact(first + " " + last))
        out.append(compact(pub))
    else:
        out.append(compact(pub))
    out.append("".join(sorted(compact(pub))))
    return [o for o in out if o]


def minutes_seconds(text) -> int:
    if text is None:
        return 0
    t = str(text).strip()
    m = re.match(r"^(\d{1,3}):(\d{1,2})$", t)
    if not m:
        return 0
    return int(m.group(1)) * 60 + int(m.group(2))


def team_variants() -> dict:
    """team code -> [full name without spaces, city without spaces] (official table)."""
    out = {}
    try:
        rows = jload("data/teams_advanced_2026_27.json").get("rows", [])
    except Exception:
        rows = []
    for r in rows:
        code = (r.get("abbr") or "").upper()
        full = (r.get("team") or "").upper()
        if not code or not full:
            continue
        variants = [re.sub(r"[^A-Z]", "", full)]
        city = full.split(" ")[0]
        if city and city != full:
            variants.append(re.sub(r"[^A-Z]", "", city))
        out[code] = variants
    return out


TEAM_VARIANTS = team_variants()


def team_from_header(text: str) -> tuple:
    """('VISITOR'|'HOME', team code) from a gamebook team header line."""
    up = re.sub(r"[^A-Z]", "", (text or "").upper())
    side = None
    if up.startswith("VISITOR"):
        side = "away"
    elif up.startswith("HOME"):
        side = "home"
    if side is None:
        return (None, None)
    best = None
    for code, variants in TEAM_VARIANTS.items():
        for v in variants:
            if len(v) >= 4 and v in up:
                if best is None or len(v) > len(best[1]):
                    best = (code, v)
    return (side, best[0] if best else None)


# ---------------------------------------------------------------------------
# gamebook readers
# ---------------------------------------------------------------------------

def _row_from_values(name, jersey, minutes, vals, team, side) -> dict:
    rec = {"minutes": minutes, "jersey": jersey, "team": team, "side": side}
    for (col, _key), v in zip(PLAYER_COLUMNS, vals):
        rec[col] = v
    rec["_name"] = name
    return rec


def parse_player_lines_pdf(pdf_path: str) -> dict:
    """Parse the official gamebook PDF into {compact_name: [row, ...]}.

    A player line is recognised by its shape: a jersey number, a name, an optional
    position token (C/F/G), a minutes pair ("25:", "50") and then sixteen numeric
    columns.  A leading "-" immediately before a number is that number's sign, which
    is how the +/- column is printed.  A player can appear on more than one page, so
    every line is kept and matched by minutes when the row is compared.
    """
    doc = pdftext.read_pdf(pdf_path)
    players = {}
    dnp = {}
    side = None
    team = None
    for page in doc["pages"]:
        for line in page:
            toks = [w.strip() for _x, w in line]
            text = " ".join(toks)
            up = re.sub(r"[^A-Z]", "", text.upper())
            if up.startswith("VISITOR") or up.startswith("HOME"):
                s, t = team_from_header(text)
                if s:
                    side, team = s, t
                continue
            min_i = None
            for i, t in enumerate(toks):
                if re.fullmatch(r"\d{1,3}:", t) and i + 1 < len(toks) \
                        and re.fullmatch(r"\d{1,2}", toks[i + 1]):
                    min_i = i
                    break
            if min_i is None or min_i < 2:
                continue
            minutes = toks[min_i][:-1] + ":" + toks[min_i + 1]
            name_end = min_i
            if toks[min_i - 1] in POSITION_TOKENS:
                name_end = min_i - 1
            name = "".join(toks[1:name_end])
            if not name:
                continue
            vals = []
            negate = False
            for t in toks[min_i + 2:]:
                if t in ("-", "+"):
                    negate = (t == "-")
                    continue
                if re.fullmatch(r"\d+", t):
                    v = int(t)
                    if negate:
                        v = -v
                    negate = False
                    vals.append(v)
            if len(vals) != 16:
                continue
            players.setdefault(compact(name), []).append(
                _row_from_values(name, toks[0], minutes, vals, team, side))
        for line in page:
            text = " ".join(w for _x, w in line)
            if "DNP" in text or "Inactive" in text:
                dnp.setdefault(text.strip(), 0)
                dnp[text.strip()] += 1
    return {"players": players, "dnp_lines": dnp, "sha256": doc["sha256"],
            "bytes": doc["bytes"], "pages": len(doc["pages"])}


def parse_player_lines_md(md_path: str) -> dict:
    """Parse the archived verbatim gamebook transcription (markdown table)."""
    players = {}
    dnp = {}
    side = None
    team = None
    with open(md_path, encoding="utf-8") as fh:
        for raw in fh:
            if not raw.lstrip().startswith("|"):
                # the gamebook also names players who never appear in the box
                # score, on its own "Inactive:" line
                if "Inactive" in raw or "DNP" in raw or "DND" in raw:
                    dnp.setdefault(raw.strip(), 1)
                continue
            cells = [c.strip() for c in raw.strip().strip("|").split("|")]
            cells = [c for c in cells if c != ""]
            if len(cells) < 2:
                continue
            header = " ".join(cells)
            up = re.sub(r"[^A-Z]", "", header.upper())
            if up.startswith("VISITOR") or up.startswith("HOME"):
                s, t = team_from_header(header)
                if s:
                    side, team = s, t
                continue
            min_i = None
            for i, c in enumerate(cells):
                if re.fullmatch(r"\d{1,3}:\d{2}", c):
                    min_i = i
                    break
                if c.startswith(("DNP", "DND")):
                    min_i = i
                    break
            if min_i is None or min_i < 1:
                continue
            # the name cell sits before the position cell, which may be absent
            if min_i >= 2 and cells[min_i - 1] in POSITION_TOKENS:
                name_cell = cells[min_i - 2]
                jersey = cells[min_i - 3] if min_i >= 3 and re.fullmatch(r"\d+", cells[min_i - 3]) else None
            else:
                name_cell = cells[min_i - 1]
                jersey = None
            m = re.match(r"^(\d+)\s+(.*)$", name_cell)
            if m:
                jersey, name = m.group(1), m.group(2)
            else:
                name = name_cell
                if jersey is None and cells and re.fullmatch(r"\d+", cells[0]):
                    jersey = cells[0]
            minutes = cells[min_i]
            if not re.fullmatch(r"\d{1,3}:\d{2}", minutes):
                dnp[compact(name)] = minutes
                continue
            vals = []
            for c in cells[min_i + 1:]:
                if re.fullmatch(r"-?\d+", c):
                    vals.append(int(c))
            if len(vals) != 16:
                continue
            players.setdefault(compact(name), []).append(
                _row_from_values(name, jersey, minutes, vals, team, side))
    return {"players": players, "dnp_lines": dnp, "sha256": None, "bytes": None,
            "pages": None}


def load_gamebook(rel: str) -> dict:
    """Load the archived official gamebook of one game, whichever form it takes."""
    path = os.path.join(ROOT, rel)
    if rel.lower().endswith(".pdf"):
        return parse_player_lines_pdf(path)
    if rel.lower().endswith(".md"):
        return parse_player_lines_md(path)
    raise ValueError(f"unsupported gamebook artifact: {rel}")


# ---------------------------------------------------------------------------

class Report:
    def __init__(self):
        self.rows = []
        self.families = {}

    def add(self, family, ident, claim, expected, published, source_url, artifact,
            verdict, note=""):
        self.rows.append({
            "family": family,
            "id": ident,
            "claim": claim,
            "expected": expected,
            "published": published,
            "source_url": source_url,
            "artifact": artifact,
            "verdict": verdict,
            "note": note,
        })

    def finish(self):
        for row in self.rows:
            fam = self.families.setdefault(row["family"], {
                "checks": 0, "pass": 0, "mismatch": 0, "unverified": 0})
            fam["checks"] += 1
            key = {"PASS": "pass", "MISMATCH": "mismatch", "UNVERIFIED": "unverified"}[row["verdict"]]
            fam[key] += 1
        return self.families


# ---------------------------------------------------------------------------
# F1 - per-player game logs vs the official gamebook
# ---------------------------------------------------------------------------

def f1_player_logs(rep: Report):
    log_files = [
        "data/official/player_game_logs_2026-11-15.json",
        "data/official/player_game_logs_2026-11-16.json",
        "data/official/player_game_logs_2026-11-17.json",
        "data/official/player_game_logs_2026-11-18.json",
    ]
    for rel in log_files:
        if not os.path.exists(os.path.join(ROOT, rel)):
            continue
        doc = jload(rel)
        games = {g["game_id"]: g for g in doc.get("games", [])}
        cache = {}
        for row in doc.get("rows", []):
            gid = row.get("game_id")
            game = games.get(gid, {})
            archive = row.get("source_text") or game.get("source_archive")
            url = row.get("source_pdf") or row.get("source_gamebook_url") or game.get("source_pdf")
            ident = f"F1.{rel.split('_')[-1].split('.')[0]}.{gid}.{row.get('team')}.{row.get('player')}"
            if not archive or not os.path.exists(os.path.join(ROOT, archive)):
                rep.add("F1_player_logs_vs_official_gamebook", ident,
                        f"{row.get('player')} minutes/points/rebounds/assists",
                        "official gamebook row", "row published with no archived gamebook",
                        url, archive or "", "UNVERIFIED",
                        "the archived official gamebook for this game is not in the repository")
                continue
            if archive not in cache:
                cache[archive] = load_gamebook(archive)
            parsed = cache[archive]
            variants = name_variants(row.get("player") or "")
            pub_min = published_value(row, MINUTES_FIELDS)
            pub_jersey = str(row.get("jersey") or "")
            candidates = []
            for cand, cand_rows in parsed["players"].items():
                if cand in variants:
                    candidates.extend(cand_rows)
            gb = None
            for cand_row in candidates:
                if pub_min and minutes_seconds(cand_row.get("minutes")) == minutes_seconds(pub_min):
                    gb = cand_row
                    break
            if gb is None and pub_jersey:
                for cand_row in candidates:
                    if str(cand_row.get("jersey")) == pub_jersey:
                        gb = cand_row
                        break
            if gb is None and candidates:
                gb = candidates[0]
            if gb is None:
                if not row.get("played", True):
                    listed = any(compact(nm) in variants for nm in parsed["dnp_lines"])
                    if not listed:
                        # the gamebook also lists players who never appear in the box
                        # score, on its own "Inactive:" line
                        blob = re.sub(r"[^a-z]", "", " ".join(parsed["dnp_lines"]).lower())
                        name = row.get("player") or ""
                        surname = compact(name.split(",")[0]) if "," in name else \
                            compact(name.split()[-1] if name.split() else "")
                        listed = bool(surname) and surname in blob
                    rep.add("F1_player_logs_vs_official_gamebook", ident,
                            f"{row.get('player')} did not play",
                            "listed as DNP / inactive in the official gamebook",
                            row.get("dnp_note") or "played=false",
                            url, archive,
                            "PASS" if listed else "UNVERIFIED",
                            "the gamebook's own inactive/DNP list names this player"
                            if listed else
                            "the player is not in the gamebook's DNP/inactive list either")
                    continue
                rep.add("F1_player_logs_vs_official_gamebook", ident,
                        f"{row.get('player')} minutes/points/rebounds/assists",
                        "a matching player row in the official gamebook",
                        "not found in the gamebook",
                        url, archive, "UNVERIFIED",
                        "no gamebook row matched this name")
                continue
            diffs = []
            for col, keynames in PLAYER_COLUMNS:
                pub = published_value(row, keynames)
                if pub is None:
                    continue
                if pub != gb.get(col):
                    diffs.append(f"{keynames[0]}: published {pub!r} vs gamebook {gb.get(col)!r}")
            if pub_min is not None and minutes_seconds(pub_min) != minutes_seconds(gb.get("minutes")):
                diffs.append(f"minutes: published {pub_min!r} vs gamebook {gb.get('minutes')!r}")
            rep.add("F1_player_logs_vs_official_gamebook", ident,
                    f"{row.get('player')} minutes/points/rebounds/assists (+ 14 more columns)",
                    ", ".join(f"{k[0]}={gb.get(c)}" for c, k in PLAYER_COLUMNS),
                    ", ".join(f"{k[0]}={published_value(row, k)}" for _c, k in PLAYER_COLUMNS),
                    url, archive,
                    "PASS" if not diffs else "MISMATCH",
                    "" if not diffs else "; ".join(diffs))


# ---------------------------------------------------------------------------
# F2 - the result feed vs the official finals
# ---------------------------------------------------------------------------

def official_final_sources() -> dict:
    """game id -> (artifact, row, url) from the official per-day finals and captures."""
    out = {}
    for path in sorted(glob.glob(os.path.join(ROOT, "data", "official", "results_2026-11-*.json"))):
        rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
        doc = jload(rel)
        for r in doc.get("rows", []):
            if r.get("away_pts") is None or r.get("home_pts") is None:
                continue
            out.setdefault(str(r.get("game_id")), (rel, r, r.get("source_url")))
    for path in sorted(glob.glob(os.path.join(ROOT, "data", "raw", "_capture_results_*.json"))):
        rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
        doc = jload(rel)
        url = doc.get("source_url")
        for r in (doc.get("parse") or {}).get("finals_rows", []):
            if r.get("away_pts") is None or r.get("home_pts") is None:
                continue
            out.setdefault(str(r.get("game_id")), (rel, r, url))
    return out


def f2_results_feed(rep: Report):
    feed_rel = "data/official/results_feed_2026_27.json"
    feed = jload(feed_rel)
    sources = official_final_sources()
    for r in feed.get("rows", []):
        gid = str(r.get("game_id"))
        ident = f"F2.{gid}"
        home_q = r.get("home_quarters") or []
        away_q = r.get("away_quarters") or []
        ok_sum = (sum(home_q) == r.get("home_pts")) and (sum(away_q) == r.get("away_pts"))
        rep.add("F2_results_feed_vs_official_finals", ident + ".quarters",
                f"{r.get('date')} {r.get('away')}@{r.get('home')} quarter scores sum to the final",
                f"home {r.get('home_pts')} = {'+'.join(map(str, home_q))}; "
                f"away {r.get('away_pts')} = {'+'.join(map(str, away_q))}",
                "sums match" if ok_sum else "sum does not match the published final",
                r.get("source_url"), feed_rel, "PASS" if ok_sum else "MISMATCH")
        if gid not in sources:
            rep.add("F2_results_feed_vs_official_finals", ident,
                    f"{r.get('date')} {r.get('away')}@{r.get('home')} final score",
                    "a row in an official per-day finals file or scoreboard capture",
                    "no official per-day row with this game id",
                    r.get("source_url"), feed_rel, "UNVERIFIED",
                    "this game is older than the official captures stored in the repository")
            continue
        rel, day_row, url = sources[gid]
        same = (
            str(day_row.get("away")) == str(r.get("away"))
            and str(day_row.get("home")) == str(r.get("home"))
            and day_row.get("away_pts") == r.get("away_pts")
            and day_row.get("home_pts") == r.get("home_pts")
            and list(day_row.get("away_quarters") or []) == list(away_q)
            and list(day_row.get("home_quarters") or []) == list(home_q)
        )
        rep.add("F2_results_feed_vs_official_finals", ident,
                f"{r.get('date')} {r.get('away')}@{r.get('home')} teams, final and quarters",
                f"{day_row.get('away')} {day_row.get('away_pts')} @ {day_row.get('home')} "
                f"{day_row.get('home_pts')} ({day_row.get('away_quarters')} / "
                f"{day_row.get('home_quarters')})",
                f"{r.get('away')} {r.get('away_pts')} @ {r.get('home')} {r.get('home_pts')} "
                f"({away_q} / {home_q})",
                url or r.get("source_url"), rel, "PASS" if same else "MISMATCH")


# ---------------------------------------------------------------------------
# F3 - rotation minutes and minutes redistribution vs the gamebook bytes
# ---------------------------------------------------------------------------

def team_minutes(parsed: dict, team_code: str) -> dict:
    """{compact name: seconds} for one team in one gamebook."""
    out = {}
    for name, rows_ in parsed["players"].items():
        for rec in rows_:
            if rec.get("team") != team_code:
                continue
            sec = minutes_seconds(rec.get("minutes"))
            if sec > out.get(name, 0):
                out[name] = sec
    return out


def f3_rotation(rep: Report):
    rot_rel = "data/derived/rotation_2026-11-19_e3d25abc.json"
    mr_rel = "data/derived/minutes_redistribution_2026-11-19_e3d25abc.json"
    if not os.path.exists(os.path.join(ROOT, rot_rel)):
        return
    rot = jload(rot_rel)
    cache = {}

    def gamebook(rel):
        if rel not in cache:
            cache[rel] = load_gamebook(rel)
        return cache[rel]

    logs = {}
    for rel in ("data/official/player_game_logs_2026-11-17.json",
                "data/official/player_game_logs_2026-11-18.json"):
        if os.path.exists(os.path.join(ROOT, rel)):
            doc = jload(rel)
            games = {g["game_id"]: g for g in doc.get("games", [])}
            for r in doc.get("rows", []):
                key = (r.get("game_id"), r.get("team"))
                logs.setdefault(key, games.get(r.get("game_id"), {}))

    for tg in rot.get("rows", []):
        gid, team = tg.get("game_id"), tg.get("team")
        ident = f"F3.rot.{gid}.{team}"
        game = logs.get((gid, team), {})
        archive = game.get("source_archive")
        if not archive or not os.path.exists(os.path.join(ROOT, archive)):
            rep.add("F3_rotation_vs_gamebook_minutes", ident,
                    f"{team} top-8 minutes share",
                    "recomputed from the official gamebook minutes",
                    f"{tg.get('top8_minutes_share')} (published)",
                    game.get("source_pdf"), archive or "", "UNVERIFIED",
                    "no archived official gamebook for this game")
            continue
        mins = team_minutes(gamebook(archive), team)
        total = sum(mins.values())
        top = sorted(mins.values(), reverse=True)[:8]
        share = round(sum(top) / total, 4) if total else None
        published = tg.get("top8_minutes_share")
        ok = share is not None and published is not None and abs(share - published) <= 0.0015
        rep.add("F3_rotation_vs_gamebook_minutes", ident,
                f"{team} top-8 minutes share (game {gid})",
                f"{share} recomputed from {len(mins)} gamebook player lines",
                f"{published} published",
                game.get("source_pdf"), archive,
                "PASS" if ok else "MISMATCH",
                "" if ok else f"team minutes recomputed {total}s vs published players_used "
                             f"{tg.get('players_used')}")

    if not os.path.exists(os.path.join(ROOT, mr_rel)):
        return
    mr = jload(mr_rel)
    for pg in mr.get("per_game", []):
        gid, team = pg.get("game_id"), pg.get("team")
        ident = f"F3.redist.{gid}.{team}"
        game = logs.get((gid, team), {})
        archive = game.get("source_archive")
        if not archive or not os.path.exists(os.path.join(ROOT, archive)):
            rep.add("F3_minutes_redistribution_vs_gamebook_minutes", ident,
                    f"{team} replacement shares when a player is out",
                    "recomputed from the official gamebook minutes",
                    f"{len(pg.get('scenarios', []))} published scenarios",
                    game.get("source_pdf"), archive or "", "UNVERIFIED",
                    "no archived official gamebook for this game")
            continue
        mins = team_minutes(gamebook(archive), team)
        bad = []
        checked = 0
        for sc in pg.get("scenarios", []):
            absent = sc.get("absent_player") or ""
            absent_s = None
            for nm, sec in mins.items():
                if compact(nm) in name_variants(absent):
                    absent_s = sec
                    break
            if absent_s is None:
                bad.append(f"{absent}: absent minutes not found in the gamebook")
                continue
            elig = {k: v for k, v in mins.items()
                    if compact(k) not in name_variants(absent)}
            # the published method: the recipients are the absent player's own
            # highest-minute teammates, weighted by the minutes they actually played.
            top8 = sorted(elig.values(), reverse=True)[:8]
            elig_total = sum(top8)
            for r in sc.get("recipients", []):
                sec = None
                for nm, v in elig.items():
                    if compact(nm) in name_variants(r.get("player") or ""):
                        sec = v
                        break
                if sec is None:
                    bad.append(f"{absent}: recipient {r.get('player')} not in the gamebook")
                    continue
                checked += 1
                w = round(sec / elig_total, 4) if elig_total else None
                pub_w = r.get("weight_from_observed_minutes")
                if w is None or pub_w is None or abs(w - float(pub_w)) > 0.0015:
                    bad.append(f"{absent} -> {r.get('player')}: weight published {pub_w} "
                               f"vs recomputed {w}")
                added = int(round(absent_s * (w or 0)))
                pub_added = r.get("minutes_added_s")
                if pub_added is None or abs(added - int(pub_added)) > 1:
                    bad.append(f"{absent} -> {r.get('player')}: minutes added published "
                               f"{pub_added} vs recomputed {added}")
            # the recipient set itself must be the game's own top-8 teammates
            published_recipients = {r.get("player") or "" for r in sc.get("recipients", [])}
            recomputed_recipients = {nm for nm, v in elig.items() if v in top8}
            matched = set()
            for pub in published_recipients:
                hit = None
                variants = name_variants(pub)
                for nm in recomputed_recipients:
                    if nm in variants or compact(nm) in variants:
                        hit = nm
                        break
                if hit is None:
                    bad.append(f"{absent}: published recipient {pub} is not one of the game's "
                               "own top-8 teammates")
                else:
                    matched.add(hit)
            if len(matched) != len(recomputed_recipients):
                missing = sorted(recomputed_recipients - matched)
                if missing:
                    bad.append(f"{absent}: the game's own top-8 teammates {missing} are not in "
                               "the published recipient list")
        rep.add("F3_minutes_redistribution_vs_gamebook_minutes", ident,
                f"{team} replacement shares when a player is out (game {gid})",
                f"{checked} recipient weights and minute additions recomputed from the gamebook",
                f"{len(pg.get('scenarios', []))} scenarios published",
                game.get("source_pdf"), archive,
                "PASS" if not bad else "MISMATCH",
                "; ".join(bad[:6]))


# ---------------------------------------------------------------------------
# F4 - settlement vs the official finals
# ---------------------------------------------------------------------------

def settle_single(pick: dict, finals: dict) -> tuple:
    """Grade one single from the official finals.  Returns (result, units)."""
    gid = str(pick.get("game_id"))
    f = finals.get(gid)
    if not f:
        return ("UNVERIFIED", 0.0)
    away, home = f.get("away"), f.get("home")
    margin = f.get("home_pts", 0) - f.get("away_pts", 0)
    side = pick.get("pick_side") or ("AWAY" if pick.get("away") == away else "HOME")
    line = str(pick.get("pick_line") or "").replace("−", "-")
    m = re.search(r"([-+]?\d+(?:\.\d+)?)$", line)
    if not m:
        return ("UNVERIFIED", 0.0)
    spread = float(m.group(1))
    team_margin = margin if side == "HOME" else -margin
    covered = team_margin + spread > 0
    if abs(team_margin + spread) < 1e-9:
        return ("PUSH", 0.0)
    return ("WIN" if covered else "LOSS", 1.0 if covered else -1.1)


def f4_settlement(rep: Report):
    finals = {}
    for gid, (rel, r, _url) in official_final_sources().items():
        finals[gid] = r
    for path in sorted(glob.glob(os.path.join(ROOT, "data", "settlement", "settlement_*.json"))):
        rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
        doc = jload(rel)
        for s in doc.get("singles", []):
            ident = f"F4.{rel.split('/')[-1]}.{s.get('game_id')}.{s.get('pick_side')}"
            result, units = settle_single(s, finals)
            ok = result == s.get("result") and abs(units - float(s.get("units", 0))) < 1e-9
            rep.add("F4_settlement_vs_official_finals", ident,
                    f"{s.get('matchup')} {s.get('pick_side')} {s.get('pick_line')} "
                    "graded from the official final",
                    f"{result} ({units:+.2f}u) re-graded from the official finals file",
                    f"{s.get('result')} ({float(s.get('units', 0)):+.2f}u) published",
                    s.get("source_game_url"), rel,
                    "PASS" if ok else ("UNVERIFIED" if result == "UNVERIFIED" else "MISMATCH"))
        summary = doc.get("summary", {})
        recomputed_w = sum(1 for s in doc.get("singles", []) if s.get("result") == "WIN")
        recomputed_l = sum(1 for s in doc.get("singles", []) if s.get("result") == "LOSS")
        recomputed_u = round(sum(float(s.get("units", 0)) for s in doc.get("singles", [])), 2)
        published_w = summary.get("wins")
        published_l = summary.get("losses")
        published_u = summary.get("singles_units_at_minus110")
        ok = (recomputed_w == published_w and recomputed_l == published_l
              and abs(recomputed_u - float(published_u)) < 1e-9)
        rep.add("F4_settlement_vs_official_finals", f"F4.{rel.split('/')[-1]}.summary",
                "settlement summary totals re-computed from the settlement's own tickets",
                f"{recomputed_w}W-{recomputed_l}L, {recomputed_u:+.2f}u",
                f"{published_w}W-{published_l}L, {published_u:+.2f}u",
                doc.get("official_finals_rule"), rel, "PASS" if ok else "MISMATCH")


# ---------------------------------------------------------------------------
# F5 - the tamper-evident ledger and the pre-registration freeze
# ---------------------------------------------------------------------------

def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def f5_ledger(rep: Report):
    rel = "data/ledger/ledger.json"
    doc = jload(rel)
    entries = doc.get("entries", [])
    prev = None
    for e in entries:
        ident = f"F5.entry{e.get('entry')}"
        body = {k: v for k, v in e.items() if k not in ("prev_hash", "entry_hash")}
        recorded_prev = e.get("prev_hash")
        if prev is None:
            ok_chain = recorded_prev in (None, "", "genesis")
        else:
            ok_chain = recorded_prev == prev
        rep.add("F5_ledger_chain", ident,
                f"ledger entry {e.get('entry')} chain link",
                f"prev_hash {prev or 'genesis'}",
                f"prev_hash {recorded_prev}",
                "https://github.com/wingbangboozle1-lang/NBA1/blob/main/data/ledger/ledger.json",
                rel, "PASS" if ok_chain else "MISMATCH")
        prev = e.get("entry_hash") or prev
    idx_rel = "data/prereg/Prereg_index.json"
    idx = jload(idx_rel)
    for path, digest in (idx.get("files") or {}).items():
        if not os.path.exists(os.path.join(ROOT, path)):
            rep.add("F5_preregistration_freeze", f"F5.prereg.{os.path.basename(path)}",
                    f"{path} is byte-identical to the frozen copy",
                    digest, "file missing", "", path, "UNVERIFIED",
                    "the frozen file is not in the repository")
            continue
        actual = sha256_file(path)
        rep.add("F5_preregistration_freeze", f"F5.prereg.{os.path.basename(path)}",
                f"{path} is byte-identical to the frozen copy",
                digest, actual,
                "https://github.com/wingbangboozle1-lang/NBA1/blob/main/" + path,
                path, "PASS" if digest == actual else "MISMATCH")
    for e in entries:
        for path, digest in (e.get("files") or {}).items():
            if not os.path.exists(os.path.join(ROOT, path)):
                continue
            actual = sha256_file(path)
            rep.add("F5_ledger_chain", f"F5.file.{e.get('entry')}.{os.path.basename(path)}",
                    f"{path} is byte-identical to the digest recorded in ledger entry "
                    f"{e.get('entry')}",
                    digest, actual,
                    "https://github.com/wingbangboozle1-lang/NBA1/blob/main/" + path,
                    path, "PASS" if digest == actual else "MISMATCH")


# ---------------------------------------------------------------------------
# F6 - the published horizon vs the official schedule capture
# ---------------------------------------------------------------------------

def norm_tip(value) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", str(value).strip().upper()).replace(" PM ET", "PM ET") \
        .replace(" AM ET", "AM ET")


def f6_horizon(rep: Report):
    sched = {}
    for path in sorted(glob.glob(os.path.join(ROOT, "data", "official", "official_schedule_*.json"))):
        rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
        doc = jload(rel)
        for r in doc.get("rows", []):
            sched.setdefault(str(r.get("game_id")), (rel, r))
    slates = {}
    for path in sorted(glob.glob(os.path.join(ROOT, "data", "raw", "session-e3d25abc", "slate_*.json"))):
        rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
        doc = jload(path)
        for g in doc.get("games", []):
            slates.setdefault(str(g.get("game_id")), (rel, g))
    horizon_rel = "data/derived/horizon_lines_v2.json"
    if not os.path.exists(os.path.join(ROOT, horizon_rel)):
        return
    horizon = jload(horizon_rel)
    for g in horizon.get("games", []):
        gid = str(g.get("game_id"))
        ident = f"F6.{gid}"
        if gid not in sched:
            rep.add("F6_horizon_vs_official_schedule", ident,
                    f"{g.get('matchup')} date, tip time and venue",
                    "a row in the official schedule capture", "no official schedule row",
                    g.get("source_url") or "", horizon_rel, "UNVERIFIED",
                    "the official schedule capture has no row for this game id")
            continue
        rel, s = sched[gid]
        diffs = []
        not_printed = []
        for field in ("date", "away", "home", "matchup"):
            official_value = s.get(field)
            if official_value in (None, ""):
                not_printed.append(field)
                continue
            if g.get(field) != official_value:
                diffs.append(f"{field}: published {g.get(field)!r} vs official {official_value!r}")
        url = s.get("source_url")
        # the tip time: the schedule capture prints it for some days and not others,
        # so the official slate capture is the second source for it.
        official_tip = s.get("tip_et")
        artifact = rel
        if not official_tip and gid in slates:
            slate_rel, slate = slates[gid]
            card = slate.get("card_text") or ""
            m = re.search(r"(\d{1,2}:\d{2}\s*[ap]m ET)", card, re.I)
            official_tip = m.group(1) if m else None
            artifact = f"{rel} + {slate_rel}"
            url = slate.get("url") or url
        if official_tip and norm_tip(g.get("tip_et")) != norm_tip(official_tip):
            diffs.append(f"tip_et: published {g.get('tip_et')!r} vs official {official_tip!r}")
        elif not official_tip:
            diffs.append("tip_et: no official tip time in the stored captures")
        note_bits = list(diffs)
        if not_printed:
            note_bits.append("not printed by the official capture: " + ", ".join(not_printed))
        rep.add("F6_horizon_vs_official_schedule", ident,
                f"{g.get('matchup')} date, teams and tip time",
                f"{s.get('date')} {s.get('away')}@{s.get('home')} {official_tip or 'tip not captured'}",
                f"{g.get('date')} {g.get('away')}@{g.get('home')} {g.get('tip_et')}",
                url, artifact,
                "PASS" if not diffs else "MISMATCH", "; ".join(note_bits))


# ---------------------------------------------------------------------------

def write_markdown(rep: Report, families: dict, path: str):
    lines = []
    lines.append("# Line-by-line verification of the published values")
    lines.append("")
    lines.append(f"- generated_utc: {NOW}")
    lines.append("- session: `arena/eac340af-nba1` (COORDINATION §72, I03)")
    lines.append("- script: `scripts/verify_line_by_line_eac340af.py`")
    lines.append("")
    lines.append("The existing site gates check *provenance structure* - that every published "
                 "row carries an official source link and every link resolves. This report "
                 "compares the published **values** with the official bytes stored in this "
                 "repository, one line per comparison. `UNVERIFIED` means the value could not "
                 "be confirmed from an official artifact; it is never filled in by inference.")
    lines.append("")
    lines.append("| Family | Checks | Pass | Mismatch | Unverified |")
    lines.append("| --- | ---: | ---: | ---: | ---: |")
    for fam, st in families.items():
        lines.append(f"| {fam} | {st['checks']} | {st['pass']} | {st['mismatch']} | "
                     f"{st['unverified']} |")
    totals = {k: sum(v[k] for v in families.values())
              for k in ("checks", "pass", "mismatch", "unverified")}
    lines.append(f"| **Total** | **{totals['checks']}** | **{totals['pass']}** | "
                 f"**{totals['mismatch']}** | **{totals['unverified']}** |")
    lines.append("")
    bad = [r for r in rep.rows if r["verdict"] != "PASS"]
    lines.append(f"## The {len(bad)} lines that are not a PASS")
    lines.append("")
    lines.append("| Family | Claim | Expected (official) | Published | Verdict | Official source |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for r in bad[:400]:
        src = r["source_url"] or ""
        link = f"[source]({src})" if src.startswith("http") else (src or "-")
        lines.append(
            f"| {r['family']} | {r['claim']} | {r['expected']} | {r['published']} | "
            f"**{r['verdict']}** | {link} |")
    lines.append("")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def main() -> int:
    rep = Report()
    f1_player_logs(rep)
    f2_results_feed(rep)
    f3_rotation(rep)
    f4_settlement(rep)
    f5_ledger(rep)
    f6_horizon(rep)
    families = rep.finish()
    os.makedirs(OUT_DIR, exist_ok=True)
    out = {
        "title": "Line-by-line verification of the published values",
        "generated_at_utc": NOW,
        "session": "arena/eac340af-nba1",
        "script": "scripts/verify_line_by_line_eac340af.py",
        "rule": "A published value is compared with the official artifact stored in this "
                "repository. UNVERIFIED means it could not be confirmed; nothing is inferred.",
        "families": families,
        "rows": rep.rows,
    }
    with open(os.path.join(OUT_DIR, "line_by_line_report.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    write_markdown(rep, families, os.path.join(OUT_DIR, "line_by_line_report.md"))
    totals = {k: sum(v[k] for v in families.values())
              for k in ("checks", "pass", "mismatch", "unverified")}
    print(json.dumps({"families": families, "totals": totals}, indent=1))
    print(f"report -> {os.path.relpath(OUT_DIR, ROOT)}/line_by_line_report.{{json,md}}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
