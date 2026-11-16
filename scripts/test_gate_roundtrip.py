"""End-to-end dry run: promote_official.py -> refresh_gate.py on an isolated
tree whose captures are shaped exactly like the live fetcher's outputs.

This exercises the whole verified-promotion contract offline: the promoter
must promote the structured tables with digest-bound verification records,
reconcile the results captures, and the freshness gate must then PASS. Any
misalignment between the fetcher's capture shapes, the promoter's proofs and
the gate's checks fails here, before CI.

Run: python3 scripts/test_gate_roundtrip.py
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "engine"))

from common import ABBR, TEAM_ID  # noqa: E402
from parse_official import ADVANCED_COLS, STANDINGS_COLS  # noqa: E402

TRAD_COLS = ["team", "gp", "w", "l", "win_pct", "min", "pts", "fgm", "fga",
             "fg_pct", "3pm", "3pa", "3p_pct", "ftm", "fta", "ft_pct", "oreb",
             "dreb", "reb", "ast", "tov", "stl", "blk", "blka", "pf", "pfd",
             "+/-"]


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def team_rows(cols, w_off=8, l_off=2):
    rows = []
    for i, (name, abbr) in enumerate(sorted(ABBR.items())):
        w, l = w_off + i % 4, l_off + i % 3
        gp = w + l
        if cols is TRAD_COLS:
            rows.append([abbr, gp, w, l, round(w / gp, 3), 241.0, 113.5,
                         41.5, 88.5, 0.470, 13.5, 36.5, 0.370, 17.5, 22.5,
                         0.780, 9.5, 34.5, 44.0, 26.5, 14.5, 8.5, 4.5, 4.5,
                         19.5, 19.5, 2.5])
        elif cols is ADVANCED_COLS:
            rows.append([abbr, gp, w, l, 241.0, 114.5, 111.5, 3.0, 60.5,
                         1.85, 19.5, 25.5, 74.5, 55.5, 13.5, 53.5, 56.5,
                         98.5, 15.5, 992.0])
    return rows


def standings_rows():
    rows = []
    for conf in ("East", "West"):
        for i, (name, abbr) in enumerate(sorted(ABBR.items())[:15 if conf == "East" else 0] or []):
            pass
    # 15 East + 15 West, records consistent (W+L == GP mirrored into home+road).
    pairs = sorted(ABBR.items())
    for idx in range(30):
        name, abbr = pairs[idx]
        conf = "East" if idx < 15 else "West"
        rank = idx + 1 if idx < 15 else idx - 14
        w, l = 8 + idx % 4, 2 + idx % 3
        rows.append([abbr, name, conf, rank, w, l, round(w / (w + l), 3), 0.0,
                     f"{w - 1}-{l}", f"{w - 2}-{l - 1}", f"{w // 2}-{l // 2}",
                     f"{w - w // 2}-{l - l // 2}", "0-0", "0-0",
                     f"{w}-{l}", "W 1"])
    return rows


def write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(obj, fh)


def main():
    tmp = tempfile.mkdtemp(prefix="gate-roundtrip-")
    raw = os.path.join(tmp, "data", "raw")
    os.makedirs(raw)
    # engine + gate copied so the promoter's ROOT/RAW resolve inside the tree.
    shutil.copytree(os.path.join(ROOT, "engine"), os.path.join(tmp, "engine"))
    now = "2026-11-16T00:45:00Z"

    # --- captures, shaped exactly like engine/fetch_official.py writes them.
    checks = []

    def check(key, url, text):
        checks.append({"key": key, "url": url, "checked_at_utc": now,
                       "http_status": 200, "bytes": len(text),
                       "sha256": sha(text)})
        return sha(text)

    st_text = "standings-page-bytes"
    d = check("S8_standings", "https://www.nba.com/standings", st_text)
    write(os.path.join(raw, "_capture_S8_standings.json"), {
        "captured_at_utc": now, "source_url": "https://www.nba.com/standings",
        "bytes": len(st_text), "strategy": "html_table",
        "row_count": 30, "cols": STANDINGS_COLS, "rows": standings_rows(),
        "page_sha256": d})

    for key, url, out in (
            ("S9_team_traditional", "https://www.nba.com/stats/teams/traditional",
             "_capture_S9_team_traditional.json"),
            ("S10_team_opponent", "https://www.nba.com/stats/teams/opponent",
             "_capture_S10_team_opponent.json")):
        text = key + "-page-bytes"
        d = check(key, url, text)
        rows = team_rows(TRAD_COLS)
        write(os.path.join(raw, out), {
            "captured_at_utc": now, "source_url": url,
            "bytes": len(text), "strategy": "html_table", "variant":
                "traditional" if "traditional" in key else "opponent",
            "row_count": 30, "cols": TRAD_COLS, "rows": rows,
            "page_sha256": d})

    for key, url in (
            ("S1_season", "https://www.nba.com/stats/teams/advanced"),
            ("S2_train", "https://www.nba.com/stats/teams/advanced?DateFrom=10%2F20%2F2026&DateTo=11%2F05%2F2026&SeasonType=Regular+Season")):
        text = key + "-page-bytes"
        d = check(key, url, text)
        write(os.path.join(raw, f"_capture_{key}.json"), {
            "captured_at_utc": now, "source_url": url,
            "fetched_from": url + " (html_table)",
            "row_count": 30, "cols": list(ADVANCED_COLS),
            "rows": team_rows(ADVANCED_COLS), "page_sha256": d})

    s4_text = "schedule-page-bytes"
    d = check("S4_schedule", "https://www.nba.com/schedule", s4_text)
    games = [{"game_id": f"00226002{i:02d}", "date": "2026-11-16",
              "time_et": "7:00 PM", "away": "MEM", "home": "WAS",
              "away_rec": "9-4", "home_rec": "4-9",
              "venue": "Capital One Arena", "city": "Washington, DC",
              "source_url": "https://www.nba.com/game/mem-vs-was-0022600247"}
             for i in range(47, 58)]
    write(os.path.join(raw, "_capture_S4_schedule.json"), {
        "captured_at_utc": now, "source_url": "https://www.nba.com/schedule",
        "bytes": len(s4_text), "strategy": "game_link", "games": games,
        "row_count": len(games), "page_sha256": d})

    s5_text = "injury-index-bytes"
    d = check("S5_injury_index",
              "https://official.nba.com/nba-injury-report-2026-11-15/", s5_text)
    write(os.path.join(raw, "_capture_S5_injury_index.json"), {
        "captured_at_utc": now,
        "source_url": "https://official.nba.com/nba-injury-report-2026-11-15/",
        "bytes": len(s5_text), "links": ["Injury-Report_2026_11_15_05_15PM.pdf"],
        "page_sha256": d})

    s7_text = "players-page-bytes"
    check("S7_players", "https://www.nba.com/stats/players/traditional", s7_text)
    write(os.path.join(raw, "_capture_S7_players.json"), {
        "captured_at_utc": now,
        "source_url": "https://www.nba.com/stats/players/traditional",
        "bytes": len(s7_text), "rows": [], "missing": ["player rows"],
        "page_sha256": sha(s7_text)})

    # injury probe: the real archived PDF bytes.
    pdf_src = os.path.join(ROOT, "data", "raw", "injury_pdfs")
    pdfs = sorted(f for f in os.listdir(pdf_src) if f.endswith(".pdf"))
    assert pdfs, "no archived PDFs to test against"
    art_rel = None
    for f in pdfs:
        dst_dir = os.path.join(raw, "injury_pdfs")
        os.makedirs(dst_dir, exist_ok=True)
        shutil.copy(os.path.join(pdf_src, f), dst_dir)
        art_rel = "data/raw/injury_pdfs/" + f
    pdf_bytes = open(os.path.join(tmp, art_rel), "rb").read()
    results = [{"edition": os.path.basename(art_rel).split("__")[0] + ".pdf",
                "url": "https://ak-static.cms.nba.com/referee/injury/"
                       + os.path.basename(art_rel).split("__")[0] + ".pdf",
                "http_status": 200, "bytes": len(pdf_bytes),
                "sha256": hashlib.sha256(pdf_bytes).hexdigest(),
                "attempts": 1, "pdf_valid": True,
                "artifact_path": art_rel}]
    checks.append({"key": "injury_pdf_probe", "checked_at_utc": now,
                   "results": results})
    write(os.path.join(raw, "_capture_injury_probe.json"), {
        "captured_at_utc": now, "results": results, "note": "probe"})

    # results captures: the six verified finals.
    finals = [
        ("2026-11-14", "0022600231", "DEN", 116, "NOP", 108, 0),
        ("2026-11-14", "0022600232", "DAL", 117, "CLE", 127, 0),
        ("2026-11-14", "0022600233", "DET", 117, "MIA", 137, 0),
        ("2026-11-14", "0022600234", "BKN", 110, "MEM", 129, 0),
        ("2026-11-14", "0022600235", "CHI", 117, "MIN", 106, 0),
        ("2026-11-15", "0022600236", "IND", 124, "PHI", 131, 0),
    ]
    by_date = {}
    for date, gid, a, ap, h, hp, ot in finals:
        by_date.setdefault(date, []).append(
            {"game_id": gid, "away": a, "home": h, "away_pts": ap,
             "home_pts": hp, "ot": ot, "snapshot_match": True})
    by_date.setdefault("2026-11-16", [])  # run-date slate: no finals yet
    for date, rows in by_date.items():
        text = f"results-{date}-bytes"
        d = check(f"results_{date}", f"https://www.nba.com/games?date={date}",
                  text)
        write(os.path.join(raw, f"_capture_results_{date}.json"), {
            "captured_at_utc": now,
            "source_url": f"https://www.nba.com/games?date={date}",
            "page_bytes": len(text), "page_sha256": d,
            "parse": {"strategy": "embedded_json", "finals_rows": rows,
                      "not_final": [], "unparsed": [],
                      "link_occurrences": []},
            "snapshot_comparison": {
                "checked_against": "data/raw/games_completed.json + "
                                   "data/raw/schedule_upcoming.json",
                "mismatches": [],
                "promotion_candidates": [{"game_id": r["game_id"]}
                                         for r in rows],
                "committed_finals_missed": [r["game_id"] for r in rows]}})
        checks.append({"key": f"results_{date}",
                       "url": f"https://www.nba.com/games?date={date}",
                       "checked_at_utc": now, "http_status": 200,
                       "bytes": len(text), "sha256": sha(text)})

    # committed inputs the promoter starts from.
    for name in ("games_completed.json", "schedule_upcoming.json",
                 "injuries.json", "team_advanced.json"):
        shutil.copy(os.path.join(ROOT, "data", "raw", name),
                    os.path.join(raw, name))

    changed = ["S8_standings", "S9_team_traditional", "S10_team_opponent",
               "S1_season", "S2_train", "S4_schedule", "S5_injury_index",
               "S7_players", "injury probe"] + \
              [f"results {d}" for d in by_date]
    write(os.path.join(raw, "_last_refresh.json"), {
        "captured_at_utc": now, "changed": changed, "failed": [],
        "source_checks": checks})

    # ---- promote, then gate.
    env = dict(os.environ, NBA1_REPO_ROOT=tmp)
    pro = subprocess.run([sys.executable, "engine/promote_official.py"],
                         cwd=tmp, env=env, capture_output=True, text=True)
    print(pro.stdout[-3000:])
    gate = subprocess.run([sys.executable, "engine/refresh_gate.py",
                           "--record", "data/raw/_last_refresh.json",
                           "--now", "2026-11-16T00:50:00Z"],
                          cwd=tmp, env=env, capture_output=True, text=True)
    print(gate.stdout[-3000:])
    print("promote exit:", pro.returncode, "gate exit:", gate.returncode)
    ok = pro.returncode == 0 and gate.returncode == 0 and "PASS" in gate.stdout
    print("ROUNDTRIP:", "PASS" if ok else "FAIL")
    if not ok:
        print("promote stderr:", pro.stderr[-2000:])
        print("gate stderr:", gate.stderr[-2000:])
    shutil.rmtree(tmp, ignore_errors=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
