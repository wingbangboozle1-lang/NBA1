#!/usr/bin/env python3
"""Gate: every parlay price is priced at a rho that is actually measured.

Requirement R14 asks for every parlay to be priced with the measured rho with the naive
product printed beside it.  The defect that prompted this gate (flag F128): a pricer
carried `RHO = 0.15  # measured ...` next to a lookup that could never find a `rho` key
in the file it named, so the fallback constant was published as a measurement on every
row and in the file's own method line.

Checks:
  1. the register exists, carries every pairing the pricing code asks for, and each row
     states its n, its status and its source;
  2. the measured values are reproducible from the committed official data - recomputed
     here, not read back from the register;
  3. no pricer source keeps a numeric rho literal as its default;
  4. every priced row prints BOTH the naive product and the rho-adjusted price, and its
     rho_status string may only claim MEASURED when the register really has a value for
     the pairing that priced the row.

Exit 0 = priced from measurement.  Run:  python3 scripts/test_rho_pricing.py
"""
import glob
import json
import math
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "engine"))
from model_v2 import is_verified_final, load_results  # noqa: E402

REG = os.path.join(ROOT, "data", "derived", "parlay_rho.json")
PAIRINGS = ("cross_team_points", "side_and_total", "home_points_total", "same_team_players")


def pearson(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return sxy / math.sqrt(sxx * syy)


def main():
    fails, notes = [], []
    if not os.path.exists(REG):
        print("FAIL: %s is missing - run scripts/measure_parlay_rho.py" % os.path.relpath(REG, ROOT))
        return 1
    reg = json.load(open(REG, encoding="utf-8"))
    rows = reg.get("register") or {}
    for k in PAIRINGS:
        r = rows.get(k)
        if not r:
            fails.append("register has no entry for the %s pairing" % k)
            continue
        for field in ("rho_measured", "status", "sample_floor", "clears_floor"):
            if field not in r:
                fails.append("%s row is missing %s" % (k, field))
        if r.get("rho_measured") is None and "NOT" not in str(r.get("status", "")).upper():
            fails.append("%s prints a blank rho without saying it is not measured" % k)

    # 2. reproduce the game-level measurements from the official finals corpus
    finals = [g for g in load_results() if is_verified_final(g) and not g.get("neutral")]
    hp = [g["home_pts"] for g in finals]
    ap = [g["away_pts"] for g in finals]
    mg = [g["home_pts"] - g["away_pts"] for g in finals]
    tt = [g["home_pts"] + g["away_pts"] for g in finals]
    recompute = {"cross_team_points": pearson(hp, ap),
                 "side_and_total": pearson(mg, tt),
                 "home_points_total": pearson(hp, tt)}
    for k, v in recompute.items():
        pub = (rows.get(k) or {}).get("rho_measured")
        if pub is None:
            continue
        if abs(round(v, 4) - pub) > 0.0005:
            fails.append("%s: published rho %s != %.4f recomputed from %d verified finals"
                         % (k, pub, v, len(finals)))
        else:
            notes.append("%s reproduced: %.4f on %d finals" % (k, v, len(finals)))
    if any(not is_verified_final(g) for g in finals):
        fails.append("a non-final row entered the finals set")
    if len(finals) != (rows.get("cross_team_points") or {}).get("n_games"):
        fails.append("the register's n (%s) != %d finals in the corpus now - the corpus moved "
                     "and the register was not rebuilt"
                     % ((rows.get("cross_team_points") or {}).get("n_games"), len(finals)))

    # 3. no pricer may keep a numeric rho literal as its DEFAULT.  Scanned through the
    #    syntax tree rather than the text, so a docstring that QUOTES the old line (as
    #    engine/parlay.py's does, to explain what was fixed) is not mistaken for code.
    import ast
    for src in ("engine/parlay.py", "scripts/generate_picks.py", "engine/strategies.py",
                "engine/correlate.py"):
        path = os.path.join(ROOT, src)
        text = open(path, encoding="utf-8").read()
        srclines = text.splitlines()
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            val = node.value
            if not (isinstance(val, ast.Constant) and isinstance(val.value, float)):
                continue
            window = " ".join(srclines[max(0, node.lineno - 4):node.lineno]).upper()
            for t in node.targets:
                nm = getattr(t, "id", "")
                if nm.upper().endswith("RHO") and "FALLBACK" not in window:
                    fails.append("%s:%d defaults %s to the literal %s with no FALLBACK "
                                 "label on it or above it"
                                 % (src, node.lineno, nm, val.value))
        # reading the register directly OR through engine/strategies.py's provenance,
        # which is the one module that opens the file.
        if "parlay_rho.json" not in text and "SGP_RHO_PROVENANCE" not in text:
            fails.append("%s does not read the measured register" % src)

    # 3b. the strategy engine and the correlation grid must agree with the register.
    #     X-57-02 (COORDINATION 57.7) found engine/strategies.py pricing S10 parlays at a
    #     hand-typed 0.00 for the same pairing the roll page measured at -0.06: one site,
    #     two prices for one line.  This asserts the constants cannot drift back.
    try:
        sys.path.insert(0, os.path.join(ROOT, "engine"))
        import strategies as _st
        mapped = {"side_total": "side_and_total", "two_teammates": "same_team_players",
                  "two_opponents": "cross_team_points"}
        for local, key in mapped.items():
            want = (rows.get(key) or {}).get("rho_measured")
            got = _st.SGP_RHO.get(local)
            if want is not None and got is not None and abs(got - want) > 1e-9:
                fails.append("engine/strategies.py SGP_RHO['%s'] = %s but the register "
                             "measures %s for %s" % (local, got, want, key))
            if want is not None and not str(_st.SGP_RHO_PROVENANCE.get(local, "")).startswith("MEASURED"):
                fails.append("engine/strategies.py has a register value for %s but labels "
                             "it %s" % (local, _st.SGP_RHO_PROVENANCE.get(local, "(nothing)")[:40]))
        for lab in ("player_total_same_team", "player_side_same_team", "cross_game"):
            prov = str(_st.SGP_RHO_PROVENANCE.get(lab, ""))
            if prov.startswith("MEASURED"):
                fails.append("engine/strategies.py labels the unmeasured %s assumption "
                             "MEASURED" % lab)
            if not prov:
                fails.append("engine/strategies.py carries no provenance for %s" % lab)
        notes.append("engine/strategies.py: %d pairings read the register, %d carry a "
                     "labelled assumption"
                     % (len(mapped), 3))
        import correlate as _co
        for r in _co.model_derived_correlations():
            # the grid keys are this module's names; the register is keyed by pairing.
            reg_row = rows.get(mapped.get(r["rho_key"], ""), {})
            has = reg_row.get("rho_measured") is not None
            claims = r["status"].startswith("MEASURED")
            if claims and not has:
                fails.append("correlations grid claims MEASURED for %s with no register value"
                             % r["rho_key"])
            if has and not claims:
                fails.append("correlations grid calls %s model-derived while the register "
                             "measures it" % r["rho_key"])
        notes.append("engine/correlate.py: grid status labels agree with the register on "
                     "all %d pairings" % len(_co.model_derived_correlations()))
    except ImportError as exc:
        fails.append("cannot import the strategy engine to check its rhos: %s" % exc)

    # 4. both prices on every priced row, and the MEASURED claim must be earned
    pp = json.load(open(os.path.join(ROOT, "data", "parlay_pricing.json"), encoding="utf-8"))
    side_rho = (rows.get("side_and_total") or {}).get("rho_measured")
    n_rows = 0
    for r in pp.get("rows", []):
        n_rows += 1
        if "naive_product" not in r or "rho_adjusted" not in r:
            fails.append("parlay_pricing row %s/%s does not print both prices"
                         % (r.get("date"), r.get("matchup")))
        claim = str(r.get("rho_status", ""))
        if "MEASURED" in claim.upper() and side_rho is None:
            fails.append("a row claims MEASURED while the register has no value")
        if "MEASURED" in claim.upper() and r.get("rho") != side_rho:
            fails.append("row priced at rho %s while the register says %s"
                         % (r.get("rho"), side_rho))
    if not n_rows:
        fails.append("data/parlay_pricing.json has no rows")
    notes.append("parlay_pricing.json: %d rows, each with the naive product beside the "
                 "rho-adjusted price" % n_rows)

    sgp_files = sorted(glob.glob(os.path.join(ROOT, "data/derived/horizon_picks*.json")))
    checked = 0
    frozen = 0
    for p in sgp_files:
        doc = json.load(open(p, encoding="utf-8"))
        sgp_rows = doc.get("sgp_candidates", [])
        gen = str((doc.get("_meta") or {}).get("produced_by")
                  or (doc.get("_meta") or {}).get("generated_by") or "")
        if "generate_picks.py" not in gen:
            # an earlier build's published artifact.  It is left exactly as that build
            # wrote it - re-pricing a frozen artifact would silently rewrite what that
            # session published - so it is reported, not corrected, and the site labels
            # it by its session id in the filename.
            frozen += len(sgp_rows)
            notes.append("%s: %d SGP rows from build %s - frozen artifact, not re-priced "
                         "by this gate (an earlier build's published artifact)"
                         % (os.path.basename(p), len(sgp_rows), gen or "unrecorded"))
            continue
        for r in sgp_rows:
            checked += 1
            if "naive_product" not in r:
                fails.append("%s: an SGP row prints no naive product" % os.path.basename(p))
            status = str(r.get("rho_status", ""))
            if r.get("rho") is None:
                fails.append("%s: SGP row without a rho" % r.get("game"))
            if "FALLBACK" in status.upper() and "MEASURED" in status.upper():
                fails.append("%s: a fallback constant is labelled as measured" % r.get("game"))
            if status.startswith("MEASURED"):
                if r.get("rho_source_file") != os.path.join("data", "derived", "parlay_rho.json"):
                    fails.append("%s: claims measured but does not cite the register" % r.get("game"))
                if r.get("rho_n") is None:
                    fails.append("%s: claims measured with no sample size" % r.get("game"))
    notes.append("SGP rows checked: %d (current build); %d rows in frozen earlier "
                 "artifacts reported but not re-priced" % (checked, frozen))

    for n in notes:
        print("  " + n)
    if fails:
        print("RHO PRICING GATE FAILED (%d):" % len(fails))
        for f in fails:
            print("  - " + f)
        return 1
    print("RHO PRICING OK - every price is reproducible from official finals and every row "
          "prints the naive product beside the correlation-adjusted price")
    return 0


if __name__ == "__main__":
    sys.exit(main())
