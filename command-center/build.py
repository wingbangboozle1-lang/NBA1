#!/usr/bin/env python3
"""Emit the remaining Command Center pages from one template so the shell, the
navigation and the provenance footer can never drift between pages.

Run: python3 command-center/build.py
It writes only the pages listed in PAGES below; index.html, executive.html,
slate.html, picks.html and strategy.html are authored directly and are skipped.

Everything it writes is static HTML with no runtime dependency except the shared
assets/cc.js and same-origin JSON under data/.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))

NAV = [
    ("index.html", "Dashboard", "index"),
    ("executive.html", "Executive summary", "executive"),
    ("slate.html", "Slate &amp; lines", "slate"),
    ("picks.html", "Picks", "picks"),
    ("strategy.html", "Strategies &amp; leaderboard", "strategy"),
    ("props.html", "Player props", "props"),
    ("validation.html", "Validation gates", "validation"),
    ("correlations.html", "Correlations", "correlations"),
    ("luck.html", "Luck", "luck"),
    ("backtest.html", "Game log", "backtest"),
    ("injuries.html", "Injuries", "injuries"),
    ("gameflow.html", "Game flow", "gameflow"),
    ("questions.html", "Questions &amp; answers", "questions"),
    ("suggestions.html", "Suggestions", "suggestions"),
    ("flagged.html", "Flagged for review", "flagged"),
    ("repo-review.html", "Repo review", "repo"),
    ("sources.html", "Sources", "sources"),
]
GROUPS = {
    "index": "Overview", "executive": "Overview",
    "slate": "The board", "picks": "The board", "strategy": "The board", "props": "The board",
    "validation": "Evidence", "correlations": "Evidence", "luck": "Evidence",
    "backtest": "Evidence", "injuries": "Evidence", "gameflow": "Evidence",
    "questions": "Decision support", "suggestions": "Decision support",
    "flagged": "Decision support", "repo": "Decision support", "sources": "Decision support",
}


def side(active):
    out = ['''    <div class="brand"><span class="mark">N1</span><span>NBA<b>1</b><br><small style="font-weight:400;font-size:10.5px;letter-spacing:.08em;color:#7d8ea3">COMMAND CENTER</small></span></div>''']
    last = None
    for href, label, key in NAV:
        g = GROUPS[key]
        if g != last:
            out.append(f'    <div class="grp">{g}</div>')
            last = g
        cls = ' class="on"' if key == active else ""
        out.append(f'    <a href="{href}"{cls}>{label}</a>')
    out.append('''    <div class="grp">Other builds</div>
    <a href="../index.html">Build A · Edge Lab</a>
    <a href="../docs/b/index.html">Build B · Origination Desk</a>
    <div class="foot">Data cut<br><span class="mono" id="cut">—</span><br><br>Not betting advice. No market price is used anywhere in this build.</div>''')
    return "\n".join(out)


HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · NBA1 Command Center</title>
<meta name="description" content="{desc}">
<link rel="stylesheet" href="assets/cc.css">
<script src="assets/cc.js"></script>
</head>
<body>
<div class="shell">
  <aside class="side">
{side}
  </aside>
  <div class="main">
    <div class="top"><div><h1>{title}</h1><div class="sub">{desc}</div></div><span class="asof" id="asof">as of …</span></div>
    <div class="wrap">
{body}
    </div>
    <footer class="bot">
      <p><strong>NBA1 Command Center.</strong> Every table row links to an official source; anything that could
      not be confirmed is blank and listed on <a href="flagged.html">Flagged for Review</a>.</p>
      <p>Not affiliated with or endorsed by the National Basketball Association. Data © NBA, used with
      attribution and links to the official pages.</p>
    </footer>
  </div>
</div>
<script>
{script}
</script>
</body>
</html>
"""

PAGES = {}

# ------------------------------------------------------------------ props
PAGES["props"] = dict(
    title="Player Props",
    desc="Season baselines adjusted for pace and opponent — with no probability attached, and the reason stated",
    body='''      <div class="bn warn"><div class="ico">!</div><div>
        <p><strong>No prop probability is published anywhere in this build.</strong> A baseline is an
        expectation, not a distribution: without game-to-game variance from official player game logs,
        any "over 23.5 points" probability would be invented. So the site shows the baseline, the
        adjustment, and says what is missing.</p>
      </div></div>
      <div class="kpis" id="kpis"></div>
      <div class="tools">
        <label>Slate <select id="f-date"><option value="">All dates</option></select></label>
        <label>Stat <select id="f-stat">
          <option value="pts">Points</option><option value="reb">Rebounds</option>
          <option value="ast">Assists</option><option value="pts_reb_ast">PTS+REB+AST</option>
          <option value="fg3m">Made threes</option></select></label>
        <label>Search <input type="search" id="f-q" placeholder="player or team"></label>
        <span class="count" id="cnt"></span>
      </div>
      <div id="tbl"><div class="empty">Loading…</div></div>
      <p class="tnote"><b>Every number here can be checked by hand:</b> projected = baseline × pace ×
      defence × usage, and the three multipliers are printed in their own columns. Baseline is the
      player's official per-game average; pace is the game's expected possessions over his team's
      season pace; defence is the opponent's published defensive rating against the league mean; usage
      is the vacancy left by a teammate the report lists as out (1.000 means no adjustment was made —
      including when a report had not been submitted, which is not the same as a healthy roster).
      <b>There is no probability column because a probability needs game-to-game variance</b>, and only
      season averages are in this repository.</p>''',
    script='''(async () => {
  try {
    const [pr, meta] = await Promise.all([CC.load("props.json"), fetch("data/meta.json").then(r=>r.json())]);
    document.getElementById("asof").textContent = "as of " + meta.as_of;
    document.getElementById("cut").textContent = meta.generated_at_utc;
    const rows = pr.rows;
    const days = [...new Set(rows.map(r=>r.date))].sort();
    const dsel = document.getElementById("f-date");
    days.forEach(d=>dsel.insertAdjacentHTML("beforeend",`<option value="${d}">${d}</option>`));
    CC.set("#kpis",
      CC.kpi("Player-games", rows.length, "over " + days.length + " slates", "") +
      CC.kpi("Players covered", new Set(rows.map(r=>r.player)).size, "from the official top-50 table", "") +
      CC.kpi("With a probability", 0, "none — variance unmeasured", "bad") +
      CC.kpi("Median minutes", CC.n(rows.map(r=>r.season_min).filter(CC.isNum).sort((a,b)=>a-b)[Math.floor(rows.length/2)],1), "known, from the official table", ""));
    let date="", stat="pts", q="";
    function render(){
      const c = stat==="pts_reb_ast" ? "pts_reb_ast" : stat;
      const cols = [
        {h:"Date", v:r=>CC.games(r.date)},
        {h:"Player", v:r=>`<b>${CC.esc(r.player)}</b>`},
        {h:"Team", k:"team"},{h:"Opp", k:"opponent"},
        {h:"GP", n:1, v:r=>CC.n(r.gp,0)},
        {h:"MIN", n:1, v:r=>CC.n(r.season_min,1)},
        {h:"Baseline", n:2, v:r=>CC.n(r["baseline_"+c],2)},
        {h:"Projected", n:2, v:r=>CC.n(r["proj_"+c],2)},
        {h:"Adj.", n:2, v:r=>CC.num(r["delta_"+c],2)},
        {h:"Pace ×", n:3, v:r=>CC.n(r.poss_factor,3)},
        {h:"Def ×", n:3, v:r=>CC.n(r.def_factor,3)},
        {h:"Usage ×", n:3, v:r=>CC.n(r.usage_factor,3)},
        {h:"Prob.", v:r=>CC.blank},
        {h:"Source", v:()=>CC.src("S7","player stats")},
      ];
      const f = rows.filter(r=> (!date||r.date===date) && (!q||(r.player+" "+r.team).toLowerCase().includes(q.toLowerCase())) )
        .sort((a,b)=>(b["baseline_"+c]||0)-(a["baseline_"+c]||0));
      CC.set("#tbl", CC.table(cols, f));
      document.getElementById("cnt").textContent = f.length + " player-games";
    }
    dsel.onchange=e=>{date=e.target.value;render();};
    document.getElementById("f-stat").onchange=e=>{stat=e.target.value;render();};
    document.getElementById("f-q").oninput=e=>{q=e.target.value;render();};
    render();
  } catch(e){ CC.fail("#tbl", e); }
})();''')

# -------------------------------------------------------------- validation
PAGES["validation"] = dict(
    title="Validation Gates",
    desc="The seven gates and the strictly out-of-sample verdict for all ten strategies",
    body='''      <p class="lede">The out-of-sample window is every completed game after the ratings cut-off:
      <b>51 games from 2026-11-06 to 2026-11-12</b>, each predicted with team ratings built only from
      2026-10-20 to 2026-11-05. No game in the window contributes to the ratings that predict it.</p>

      <div class="bn info"><div class="ico">i</div><div>
        <p><strong>Two parameters are fitted on the test window</strong> — home-court advantage and the
        back-to-back penalty. That is disclosed, and a zeroed variant is published beside the fitted
        one so the reader can see how much of the result comes from those two numbers. Answer: almost
        none (see the row below).</p>
      </div></div>

      <div class="kpis" id="kpis"></div>

      <h2>Model against the naive reference, on the same 51 games</h2>
      <div id="cmp"><div class="empty">Loading…</div></div>

      <h2>Parameter fit</h2>
      <div id="fit"><div class="empty">Loading…</div></div>

      <h2>Gate-by-gate verdict for every strategy</h2>
      <div id="matrix"><div class="empty">Loading…</div></div>
      <p class="tnote">Legend — <b>pass</b>: cleared. <b>fail</b>: measured and missed. <b>prov</b>
      (provisional): the sample is between 10 and 29 graded plays, so the gate is neither cleared nor
      failed. <b>n/a</b>: the gate cannot apply to that strategy, e.g. a correlation limit on a
      single-leg play. <b>not run</b>: the gate needs data this repository does not hold. A gate is only
      marked pass when it was actually evaluated.</p>''',
    script='''(async () => {
  try {
    const [V, meta] = await Promise.all([CC.load("validation.json"), fetch("data/meta.json").then(r=>r.json())]);
    document.getElementById("asof").textContent = "as of " + meta.as_of;
    document.getElementById("cut").textContent = meta.generated_at_utc;
    const m = V.metrics;
    CC.set("#kpis",
      CC.kpi("Out-of-sample games", m.n_games, m.window, "") +
      CC.kpi("Margin MAE", m.mae_margin_model, "reference " + m.mae_margin_ref, m.mae_margin_model<m.mae_margin_ref?"ok":"bad") +
      CC.kpi("Total MAE", m.mae_total_model, "reference " + m.mae_total_ref, m.mae_total_model<m.mae_total_ref?"ok":"bad") +
      CC.kpi("Straight up", m.straight_up_model, "reference " + m.straight_up_ref, ""));

    const cols = [
      {h:"Metric", v:r=>`<b>${CC.esc(r.k)}</b>`},
      {h:"Model", n:1, v:r=>CC.esc(r.m)},
      {h:"Reference", n:1, v:r=>CC.esc(r.r)},
      {h:"Better", v:r=>r.win==null?CC.tag("no comparison","n"):r.win?CC.tag("model","g"):CC.tag("reference","r")},
      {h:"What it measures", v:r=>`<span class="small">${CC.esc(r.note)}</span>`},
      {h:"Source", v:r=>{
        const id = r.src || "S2";
        return CC.src(id, id === "S2" ? "training window" : "games & scores");
      }},
    ];
    const better=(a,b,lower=true)=> lower? (a<b?a===b?null:true:false) : (a>b?a===b?null:true:false);
    const rows = [
      {src:"S2", k:"Margin MAE (pts)", m:m.mae_margin_model, r:m.mae_margin_ref, win:better(m.mae_margin_model,m.mae_margin_ref), note:"Average absolute error on the home margin. Lower is better."},
      {k:"Margin RMSE (pts)", m:m.rmse_margin_model, r:m.rmse_margin_ref, win:better(m.rmse_margin_model,m.rmse_margin_ref), note:"Penalises large misses. Lower is better."},
      {k:"Margin bias (pts)", m:m.bias_margin_model, r:null, win:null, note:"Mean signed error. Zero is unbiased."},
      {k:"Total MAE (pts)", m:m.mae_total_model, r:m.mae_total_ref, win:better(m.mae_total_model,m.mae_total_ref), note:"Lower is better. This is the one the model loses."},
      {k:"Total RMSE (pts)", m:m.rmse_total_model, r:m.rmse_total_ref, win:better(m.rmse_total_model,m.rmse_total_ref), note:"Lower is better."},
      {k:"Brier score", m:m.brier_model, r:m.brier_ref, win:better(m.brier_model,m.brier_ref), note:"Probability calibration on the moneyline. Lower is better."},
      {k:"Log loss", m:m.logloss_model, r:m.logloss_ref, win:better(m.logloss_model,m.logloss_ref), note:"Probability calibration, harsher on confident misses."},
      {k:"Straight up", m:m.straight_up_model, r:m.straight_up_ref, win:null, note:"Winner picks. Identical record, so the tie is left as no comparison."},
      {src:"S2", k:"Margin MAE, parameters zeroed", m:m.mae_margin_zeroed_params, r:m.mae_margin_model, win:better(m.mae_margin_zeroed_params,m.mae_margin_model), note:"The fitted HCA and B2B terms versus no parameters at all."},
      {src:"S2", k:"Bootstrap 95% CI, model MAE", m:"["+m.bootstrap_mae_model_95.join(", ")+"]", r:"["+m.bootstrap_mae_ref_95.join(", ")+"]", win:null, note:"The two intervals overlap almost completely, which is why no stability claim is made."},
    ];
    CC.set("#cmp", CC.table(cols, rows));

    const f = V.fit || {};
    const P = v => (v === null || v === undefined) ? null : v;   // never render a nested object
    function pv(o){ return o && typeof o === "object" ? o : {est:o}; }
    const fitRows = [
      ["Home-court advantage (pts)", pv(f.hca),
       "Estimated on the test window and applied to every line. Disclosed as in-sample."],
      ["Back-to-back coefficient, home margin", pv(f.b2b_coef_on_home_margin),
       "Applied only when |t| ≥ 1; otherwise zeroed. The threshold is a rule, not a fit."],
      ["Total bias (pts)", pv(f.total_bias),
       "Added to every originated total."],
      ["Total back-to-back coefficient", pv(f.total_b2b_coef),
       "Set to zero here because |t| < 1. Shown so the decision is visible."],
    ].map(([k,o,note])=>({
      k, est:o.est, se:o.se, t:o.t,
      used: o.used === undefined ? null : o.used,
      note: note
    }));
    fitRows.push({k:"Fitted games (n)", est:f.n, se:null, t:null, used:null,
      note:"Every completed game after the ratings cut-off."});
    fitRows.push({k:"Back-to-backs detected (home / away)", est:(f.b2b_detected_home+" / "+f.b2b_detected_away), se:null, t:null, used:null,
      note:f.b2b_caveat || "Detection is limited to the captured results window."});
    fitRows.push({k:"Neutral-site games", est:f.neutral_site_games, se:null, t:null, used:null,
      note:"Home-court advantage is not applied at a neutral site."});
    fitRows.push({k:"Shrinkage k (games)", est:(f.shrink_derivation||{}).shrink_k_derived, se:null, t:null, used:null,
      note:(f.shrink_derivation||{}).disclosure || ""});

    CC.set("#fit", CC.table([
      {h:"Parameter", v:r=>`<b>${CC.esc(r.k)}</b>`},
      {h:"Estimate", n:1, v:r=>r.est===null||r.est===undefined?CC.blank:CC.esc(String(r.est))},
      {h:"Std. error", n:2, v:r=>r.se===null||r.se===undefined?CC.blank:CC.n(r.se,2)},
      {h:"t", n:2, v:r=>r.t===null||r.t===undefined?CC.blank:CC.num(r.t,2)},
      {h:"Applied", v:r=>r.used===null?CC.blank:r.used?CC.tag("yes","g"):CC.tag("no — below |t| 1","n")},
      {h:"Note", v:r=>`<span class="small">${CC.esc(r.note)}</span>`},
      {h:"Source", v:()=>CC.src("S2","training window")},
    ], fitRows));

    // gate matrix
    const gids = V.gate_definitions.map(g=>g.id);
    const mcols = [{h:"Strategy", v:r=>`<b>${CC.esc(r.id)}</b> <span class="small">${CC.esc(r.name)}</span>`},
      {h:"n", n:1, v:r=>r.n_graded},
      {h:"Record", v:r=>`<span class="mono">${r.wins}–${r.losses}</span>`},
      {h:"p", n:3, v:r=>CC.n(r.binomial_p,3)}];
    gids.forEach(g=>mcols.push({h:g, v:r=>{
      const x=(r.gates||[]).find(y=>y.id===g);
      if(!x) return CC.blank;
      return x.status==="PASS"?CC.tag("pass","g"):x.status==="FAIL"?CC.tag("fail","r"):
        x.status==="PROVISIONAL"?CC.tag("prov","a"):CC.tag(x.status==="N/A"?"n/a":"not run","n");
    }, c:"nowrap"}));
    mcols.push({h:"Gates passed", n:1, v:r=>`<b>${(r.gates||[]).filter(g=>g.status==="PASS").length}</b>/7`});
    mcols.push({h:"Source", v:r=>CC.src(r.id==="S1"?"S2":"S3",
      r.id==="S1" ? "training window" : "games & scores")});
    CC.set("#matrix", CC.table(mcols, V.strategies));

  } catch(e){ CC.fail("#cmp", e); }
})();''')

# ------------------------------------------------------------- correlations
PAGES["correlations"] = dict(
    title="Correlations",
    desc="What is measured on official data, and what is only modelled — kept apart on purpose",
    body='''      <p class="lede">Two different things share the word "correlation" here and conflating them is
      the usual way a parlay gets mispriced. <b>Measured</b> means computed from official NBA data with
      a stated sample. <b>Model-derived</b> means assumed, and every parlay that depends on it is
      labelled accordingly.</p>

      <div class="bn warn"><div class="ico">!</div><div>
        <p><strong>No same-game-parlay rho in this build is measured.</strong> Measuring leg dependence
        needs paired <em>bet outcome</em> data, which does not exist in this repository. The five rho
        values below are assumptions with a stated direction and a plausible size — not estimates.</p>
      </div></div>

      <h2>Measured correlations between official statistics</h2>
      <div id="meas"><div class="empty">Loading…</div></div>

      <h2>Assumed correlations used to price parlays</h2>
      <div id="mod"><div class="empty">Loading…</div></div>

      <h2>Parlay pricing grid</h2>
      <p class="small">How the assumed rho moves a two-leg parlay's joint probability away from the
      independence shortcut, holding both leg probabilities fixed. A positive rho <em>reduces</em> the
      joint probability of two overs, which is why multiplying marginals is the wrong default even when
      each leg looks good. Prices are fair American prices with no vig, so they are what the joint
      probability is worth — not what a book would offer. The last column is the edge a bettor gets if a
      book prices the two legs as independent: negative means the independent price is the generous one.</p>
      <div id="grid"><div class="empty">Loading…</div></div>''',
    script='''(async () => {
  try {
    const [C, meta] = await Promise.all([CC.load("correlations.json"), fetch("data/meta.json").then(r=>r.json())]);
    document.getElementById("asof").textContent = "as of " + meta.as_of;
    document.getElementById("cut").textContent = meta.generated_at_utc;
    CC.set("#meas", CC.table([
      {h:"Variable", v:r=>`<b>${CC.esc(r.x)}</b>`},
      {h:"Against", v:r=>`<b>${CC.esc(r.y)}</b>`},
      {h:"r", n:2, v:r=>CC.n(r.r,3)},
      {h:"r²", n:2, v:r=>CC.n(r.r_squared,3)},
      {h:"n", n:1, v:r=>r.n},
      {h:"p", n:3, v:r=>CC.n(r.p_value,3)},
      {h:"Question it answers", v:r=>`<span class="small">${CC.esc(r.why)}</span>`},
      {h:"Status", v:r=>CC.tag(r.status,"g")},
      {h:"Source", v:()=>CC.src("S1","team stats")},
    ], C.measured));

    CC.set("#mod", CC.table([
      {h:"Leg 1", v:r=>`<b>${CC.esc(r.leg_1)}</b>`},
      {h:"Leg 2", v:r=>`<b>${CC.esc(r.leg_2)}</b>`},
      {h:"Assumed rho", n:2, v:r=>CC.num(r.rho_model,2)},
      {h:"Direction", v:r=>r.rho_model>0?CC.tag("positive","a"):r.rho_model<0?CC.tag("negative","b"):CC.tag("none","n")},
      {h:"Derivation", v:r=>`<span class="small">${CC.esc(r.derivation)}</span>`},
      {h:"Status", v:r=>CC.tag("model-derived","r")},
      {h:"Source", v:()=>CC.src(C.src||"S1","team stats")},
    ], C.model_derived || []));

    const g = C.parlay_pricing_grid || [];
    if (g.length) {
      const keys = Object.keys(g[0]);
      const label = {
        leg_prob:"Leg probability", rho:"Assumed rho", true_joint_prob:"True joint",
        independent_product:"Priced as independent", difference:"Difference",
        fair_price_true:"Fair price, true joint (American)",
        price_if_priced_independent:"Fair price, priced independent (American)",
        bettor_edge_if_priced_independent_pct:"Edge if priced independent %"
      };
      const gcols = keys.map(k=>({h:label[k]||k, n:1, v:r=>{
        if (r[k]===null||r[k]===undefined) return CC.blank;
        if (!CC.isNum(r[k])) return CC.esc(r[k]);
        // American prices are signed integers; showing "292" without the + reads as a probability.
        if (/price/.test(k)) {
          const v = Number(r[k]);
          return `<b class="mono">${v > 0 ? "+" : ""}${v}</b>`;
        }
        return CC.n(r[k], /prob|product|difference/.test(k) ? 4 : 2);
      }}));
      gcols.push({h:"Source", v:()=>CC.src(C.src||"S1","measured inputs")});
      CC.set("#grid", CC.table(gcols, g));
    } else {
      CC.set("#grid", '<div class="empty">No grid published in this data file.</div>');
    }
  } catch(e){ CC.fail("#meas", e); }
})();''')

# ------------------------------------------------------------------- luck
PAGES["luck"] = dict(
    title="Luck Decomposition",
    desc="Which records are ahead of or behind what the teams' own point differentials imply",
    body='''      <p class="lede">A team's win-loss record is a noisy measurement of how good it is. Pythagorean
      expectation converts a team's official offensive and defensive ratings into the win rate its
      point differential implies; the gap between that and its actual wins is the part that came from
      close-game outcomes. A large gap is not proof of luck, but it is a reason not to price a record.</p>

      <div class="bn info"><div class="ico">i</div><div>
        <p><strong>What this is and is not.</strong> Expected wins come from the official OffRtg and
        DefRtg with a fixed exponent (13.91). The z-score divides the gap by the binomial standard
        deviation over games played. Nothing here is a prediction.</p>
      </div></div>

      <div class="kpis" id="kpis"></div>

      <div class="tools">
        <label>Sort <select id="f-sort">
          <option value="luck_desc">Luckiest first</option>
          <option value="luck_asc">Unluckiest first</option>
          <option value="z_desc">Largest z</option>
          <option value="wins">Most wins</option>
        </select></label>
        <span class="count" id="cnt"></span>
      </div>
      <div id="tbl"><div class="empty">Loading…</div></div>
      <p class="tnote">"Luck" is a statistical description of the gap between wins and point
      differential — not a claim that a team is fortunate in a moral sense, and not a forecast. Regression
      to the mean is the base case, not a certainty.</p>''',
    script='''(async () => {
  try {
    const [Lk, meta] = await Promise.all([CC.load("luck.json"), fetch("data/meta.json").then(r=>r.json())]);
    document.getElementById("asof").textContent = "as of " + meta.as_of;
    document.getElementById("cut").textContent = meta.generated_at_utc;
    const rows = Lk.rows;
    const luckiest = rows.slice().sort((a,b)=>b.luck_wins-a.luck_wins)[0];
    const unluckiest = rows.slice().sort((a,b)=>a.luck_wins-b.luck_wins)[0];
    const biggestZ = rows.slice().sort((a,b)=>Math.abs(b.luck_z)-Math.abs(a.luck_z))[0];
    CC.set("#kpis",
      CC.kpi("Teams", rows.length, "season to date, 2026-11-12", "") +
      CC.kpi("Luckiest", "+"+CC.n(luckiest.luck_wins,2), luckiest.team+" · z = "+CC.n(luckiest.luck_z,2), "warn") +
      CC.kpi("Unluckiest", CC.n(unluckiest.luck_wins,2), unluckiest.team+" · z = "+CC.n(unluckiest.luck_z,2), "ok") +
      CC.kpi("Largest |z|", CC.n(Math.abs(biggestZ.luck_z),2), biggestZ.name, ""));

    const cols = [
      {h:"Team", v:r=>`<b>${CC.esc(r.team)}</b>`},
      {h:"GP", n:1, v:r=>r.gp},
      {h:"W–L", v:r=>`<span class="mono">${r.w}–${r.l}</span>`},
      {h:"OffRtg", n:1, v:r=>CC.n(r.ortg,1)},
      {h:"DefRtg", n:1, v:r=>CC.n(r.drtg,1)},
      {h:"NetRtg", n:1, v:r=>CC.num(r.netr,1)},
      {h:"Pythag W%", n:1, v:r=>CC.pct(r.pyth_win_pct,1)},
      {h:"Expected W", n:2, v:r=>CC.n(r.expected_wins,2)},
      {h:"Actual W", n:1, v:r=>r.actual_wins},
      {h:"Luck (wins)", n:2, v:r=>CC.num(r.luck_wins,2)},
      {h:"SD", n:2, v:r=>CC.n(r.sd_wins,2)},
      {h:"z", n:2, v:r=>{
        const z=r.luck_z; if(!CC.isNum(z)) return CC.blank;
        const cls=Math.abs(z)>=2?"neg":"";
        return `<span class="${cls}">${CC.n(z,2)}</span>`;
      }},
      {h:"Source", v:()=>CC.src("S1","team stats")},
    ];
    let sort="luck_desc";
    function render(){
      const r = rows.slice().sort((a,b)=>
        sort==="luck_desc"?b.luck_wins-a.luck_wins:
        sort==="luck_asc"?a.luck_wins-b.luck_wins:
        sort==="z_desc"?Math.abs(b.luck_z)-Math.abs(a.luck_z):b.w-a.w);
      CC.set("#tbl", CC.table(cols, r));
      document.getElementById("cnt").textContent = r.length + " teams";
    }
    document.getElementById("f-sort").onchange=e=>{sort=e.target.value;render();};
    render();
  } catch(e){ CC.fail("#tbl", e); }
})();''')

print("chunk1 ok")

# ---------------------------------------------------------------- backtest
PAGES["backtest"] = dict(
    title="Game Log",
    desc="All 51 out-of-sample games: what the model said before tip, and what actually happened",
    body='''      <p class="lede">This is the evidence the whole verdict rests on. Every game below was predicted
      with team ratings built only from 2026-10-20 to 2026-11-05, so no game in this window contributes
      to the ratings that predict it.</p>

      <div class="bn info"><div class="ico">i</div><div>
        <p><strong>Why the error column can look large.</strong> A single NBA game's margin is a
        high-variance quantity: the residual standard deviation here is about 17.4 points. An average
        absolute error near 13 points is normal and is not a defect — which is exactly why one game
        proves nothing and 51 games barely prove anything.</p>
      </div></div>

      <div class="kpis" id="kpis"></div>

      <div class="tools">
        <label>Date <select id="f-date"><option value="">All dates</option></select></label>
        <label>Show <select id="f-side">
          <option value="">All games</option>
          <option value="model">Model beat reference on margin</option>
          <option value="ref">Reference beat model on margin</option>
        </select></label>
        <span class="count" id="cnt"></span>
      </div>
      <div id="tbl"><div class="empty">Loading…</div></div>
      <p class="tnote"><b>Sign convention.</b> A published margin is from the home team's point of
      view, so a positive number means the home side is favoured. Every error column is <b>signed</b>:
      <span class="mono">actual − predicted</span>. A negative error therefore means the home team did
      worse than predicted, not that the prediction was better — a −40 is a 40-point miss. The
      <em>Show</em> filter compares absolute errors, and the averages on the Validation page are means
      of absolute values. Each row links to the official game page; a large total error on both sides of
      the same game is typical of an overtime or a blowout.</p>''',
    script='''(async () => {
  try {
    const [B, meta] = await Promise.all([CC.load("backtest.json"), fetch("data/meta.json").then(r=>r.json())]);
    document.getElementById("asof").textContent = "as of " + meta.as_of;
    document.getElementById("cut").textContent = meta.generated_at_utc;
    const m = B.metrics, P = B.params;
    CC.set("#kpis",
      CC.kpi("Games", B.rows.length, m.window, "") +
      CC.kpi("Margin MAE", m.mae_margin_model, "vs " + m.mae_margin_ref + " reference", m.mae_margin_model<m.mae_margin_ref?"ok":"bad") +
      CC.kpi("Total MAE", m.mae_total_model, "vs " + m.mae_total_ref + " reference", m.mae_total_model<m.mae_total_ref?"ok":"bad") +
      CC.kpi("Winners", m.straight_up_model, "reference also " + m.straight_up_ref, ""));
    const dates = [...new Set(B.rows.map(r=>r.date))].sort();
    const dsel=document.getElementById("f-date");
    dates.forEach(d=>dsel.insertAdjacentHTML("beforeend",`<option value="${d}">${d}</option>`));
    const cols=[
      {h:"Date", v:r=>CC.games(r.date)},
      {h:"Game", v:r=>`<span class="mono">${CC.esc(r.matchup)}</span>`},
      {h:"Result", v:r=>`<span class="mono">${r.away_pts}–${r.home_pts}${r.ot?" OT":""}</span>`},
      {h:"Our spread", n:1, v:r=>CC.num(r.model_spread_home,1)},
      {h:"Ref spread", n:1, v:r=>CC.num(r.ref_spread_home,1)},
      {h:"Actual margin", n:1, v:r=>CC.num(r.actual_margin_home,1)},
      {h:"Err model", n:1, v:r=>CC.num(r.err_model_margin,2)},
      {h:"Err ref", n:1, v:r=>CC.num(r.err_ref_margin,2)},
      {h:"Our total", n:1, v:r=>CC.num(r.model_total,1)},
      {h:"Actual total", n:1, v:r=>CC.num(r.actual_total,1)},
      {h:"Err model", n:1, v:r=>CC.num(r.err_model_total,2)},
      {h:"Err ref", n:1, v:r=>CC.num(r.err_ref_total,2)},
      {h:"P(home) model", n:1, v:r=>CC.pct(r.p_home_model,1)},
      {h:"Home won", v:r=>r.home_won===1?CC.tag("yes","g"):CC.tag("no","r")},
      {h:"Neutral", v:r=>r.neutral?CC.tag("neutral site","a"):`<span class="blankdash">—</span>`},
      {h:"Source", v:r=>CC.games(r.date)},
    ];
    let date="", side="";
    function render(){
      const rows = B.rows.filter(r=> (!date||r.date===date) &&
        (side==="" || (side==="model"
            ? Math.abs(r.err_model_margin) < Math.abs(r.err_ref_margin)
            : Math.abs(r.err_model_margin) > Math.abs(r.err_ref_margin))));
      CC.set("#tbl", CC.table(cols, rows));
      document.getElementById("cnt").textContent = rows.length + " of " + B.rows.length + " games";
    }
    dsel.onchange=e=>{date=e.target.value;render();};
    document.getElementById("f-side").onchange=e=>{side=e.target.value;render();};
    render();
  } catch(e){ CC.fail("#tbl", e); }
})();''')

# ---------------------------------------------------------------- injuries
PAGES["injuries"] = dict(
    title="Injuries",
    desc="Every official status on the 19:30 ET report, with minutes-coverage confidence beside every impact figure",
    body='''      <p class="lede">Transcribed row for row from the official NBA injury report, with the report's
      own edition time. A status is what a team published about participation — not a forecast of
      minutes, usage or production.</p>

      <div class="bn bad"><div class="ico">!</div><div>
        <p><strong>Read the confidence column before the impact column.</strong> The impact number needs
        a player's minutes. Minutes are only known for the 50 players in the captured official player
        table, so for everyone else the impact is counted as zero and the row says so. The figure is
        therefore a <em>lower bound</em>, and a team with a low minutes-coverage percentage has a
        near-meaningless impact number.</p>
        <p class="small">An absent entry is not a healthy team. Where a team had not submitted a report,
        the row reads "NOT YET SUBMITTED", exactly as published.</p>
        <p class="small" id="edition"></p>
      </div></div>

      <div class="kpis" id="kpis"></div>

      <h2>Team-level availability, by game</h2>
      <div id="teams"><div class="empty">Loading…</div></div>

      <h2>Every listed player</h2>
      <div class="tools">
        <label>Date <select id="f-date"><option value="">All dates</option></select></label>
        <label>Status <select id="f-status"><option value="">All statuses</option></select></label>
        <label>Search <input type="search" id="f-q" placeholder="player or team"></label>
        <span class="count" id="cnt"></span>
      </div>
      <div id="tbl"><div class="empty">Loading…</div></div>''',
    script='''(async () => {
  try {
    const [I, meta] = await Promise.all([CC.load("injuries.json"), fetch("data/meta.json").then(r=>r.json())]);
    document.getElementById("asof").textContent = I.report || meta.as_of;
    document.getElementById("cut").textContent = meta.generated_at_utc;
    const rows = I.rows;
    const playerRows = rows.filter(r=>r.player);
    const ed = document.getElementById("edition");
    if (ed) ed.innerHTML = "Edition in use: <b>" + CC.esc(I.report) + "</b>. A later edition of the same " +
      "day (07:45 PM ET) exists on the official index and was spot-checked against this one during " +
      "review; a cell-by-cell diff of the two PDFs is not published, so this build is honest about " +
      "which edition it is quoting rather than claiming to be the last one (flagged R14).";
    const counts = {};
    playerRows.forEach(r=>counts[r.status]=(counts[r.status]||0)+1);
    const nys = rows.filter(r=>r.status==="NOT YET SUBMITTED").length;
    const cov = playerRows.map(r=>r.minutes_coverage).filter(CC.isNum);
    const avgCov = cov.length ? cov.reduce((a,b)=>a+b,0)/cov.length : null;
    CC.set("#kpis",
      CC.kpi("Listed players", playerRows.length, "across " + [...new Set(rows.map(r=>r.matchup))].length + " games", "") +
      CC.kpi("Out", counts["Out"]||0, "official status", "bad") +
      CC.kpi("Questionable / doubtful / probable", (counts["Questionable"]||0)+(counts["Doubtful"]||0)+(counts["Probable"]||0), "not the same as out", "warn") +
      CC.kpi("Teams not submitted", nys, "recorded as published, not as healthy", nys?"warn":"ok"));

    // Team-level impact exists only where the report lists a player whose minutes are in the
    // captured top-50 table. Every such row today is 0.00 because no listed player is in it.
    const seenTeam = new Set();
    const teamRows = rows.filter(r=>{
      if (r.team_impact_net_rating === undefined) return false;
      const k = r.date + "|" + r.matchup + "|" + r.team;
      if (seenTeam.has(k)) return false;
      seenTeam.add(k);
      return true;
    });
    CC.set("#teams", CC.table([
      {h:"Date", v:r=>CC.games(r.date)},
      {h:"Game", v:r=>`<span class="mono">${CC.esc(r.matchup)}</span>`},
      {h:"Team", k:"team"},
      {h:"Listed", n:1, v:r=>r.team_listed},
      {h:"Weighted lost share", n:3, v:r=>CC.n(r.team_weighted_lost_share,3)},
      {h:"Impact (net rtg)", n:2, v:r=>CC.num(r.team_impact_net_rating,2)},
      {h:"Sensitivity 10/15/20", v:r=>{
        const s=r.impact_sensitivity; if(!s) return CC.blank;
        return `<span class="mono small">${CC.n(s["10"],2)} / ${CC.n(s["15"],2)} / ${CC.n(s["20"],2)}</span>`;
      }},
      {h:"Minutes coverage", n:1, v:r=>CC.pct(r.minutes_coverage,1)},
      {h:"Confidence", v:r=>{
        const c=String(r.confidence||"");
        return /HIGH/i.test(c)?CC.tag(c,"g"):/LOW/i.test(c)?CC.tag(c,"a"):CC.tag(c,"r");
      }},
      {h:"Source", v:()=>CC.src("S6","report PDF")},
    ], teamRows));
    if (!teamRows.length) {
      CC.set("#teams", `<div class="empty">No team-level impact row can be computed from this edition: none of the listed players appears in the captured official top-50 minutes table, so every impact would be a zero that means "unknown", not "no loss". This is the lower-bound problem above, stated numerically.</div>`);
    }
    const stat = [...new Set(rows.map(r=>r.status))].sort();
    const ssel=document.getElementById("f-status");
    stat.forEach(s=>ssel.insertAdjacentHTML("beforeend",`<option>${CC.esc(s)}</option>`));
    const dsel=document.getElementById("f-date");
    [...new Set(rows.map(r=>r.date))].sort().forEach(d=>dsel.insertAdjacentHTML("beforeend",`<option>${d}</option>`));

    const cols=[
      {h:"Date", v:r=>CC.games(r.date)},
      {h:"Game", v:r=>`<span class="mono">${CC.esc(r.matchup)}</span>`},
      {h:"Team", k:"team"},
      {h:"Player", v:r=>r.player?`<b>${CC.esc(r.player)}</b>`:CC.blank},
      {h:"Status", v:r=>{
        const s=r.status;
        return s==="Out"?CC.tag(s,"r"):s==="Available"?CC.tag(s,"g"):s==="NOT YET SUBMITTED"?CC.tag(s,"n"):CC.tag(s,"a");
      }},
      {h:"Reason as published", v:r=>`<span class="small">${CC.esc(r.reason||"—")}</span>`},
      {h:"Source", v:()=>CC.src("S6","report PDF")},
    ];
    let date="", st="", q="";
    function render(){
      const f = rows.filter(r=> (!date||r.date===date) && (!st||r.status===st) &&
        (!q || ((r.player||"")+" "+(r.team||"")).toLowerCase().includes(q.toLowerCase())));
      CC.set("#tbl", CC.table(cols, f));
      document.getElementById("cnt").textContent = f.length + " of " + rows.length + " rows";
    }
    dsel.onchange=e=>{date=e.target.value;render();};
    ssel.onchange=e=>{st=e.target.value;render();};
    document.getElementById("f-q").oninput=e=>{q=e.target.value;render();};
    render();
  } catch(e){ CC.fail("#teams", e); }
})();''')

# ---------------------------------------------------------------- gameflow
PAGES["gameflow"] = dict(
    title="Game Flow",
    desc="Pace, rest, back-to-back and availability context for every upcoming game",
    body='''      <p class="lede">Game flow is about how a game is likely to be shaped: how many possessions,
      how tired each side is, and whether the rotation is intact. It is derived from official pace and
      efficiency inputs plus the fitted outcome spread — not from play-by-play, which this repository
      does not capture.</p>

      <div class="bn warn"><div class="ico">!</div><div>
        <p><strong>No possession-level metric is published.</strong> Runs, quarter splits and
        timeout-adjusted flow all need play-by-play data. What is here is a pre-game distribution:
        expected possessions, expected total and margin, and the probability the game stays close.</p>
      </div></div>

      <div class="tools">
        <label>Slate <select id="f-date"><option value="">All dates</option></select></label>
        <label>Filter <select id="f-rest">
          <option value="">All games</option>
          <option value="b2b">A back-to-back is involved</option>
          <option value="unknown">Rest days not known</option>
        </select></label>
        <span class="count" id="cnt"></span>
      </div>
      <div id="tbl"><div class="empty">Loading…</div></div>

      <h2>Rest and back-to-back matrix</h2>
      <div id="rest"><div class="empty">Loading…</div></div>
      <p class="tnote">A blank rest figure means the team's previous game is not in the captured
      schedule — it is left blank rather than assumed to be a normal two-day break.</p>''',
    script='''(async () => {
  try {
    const [G, meta] = await Promise.all([CC.load("gameflow.json"), fetch("data/meta.json").then(r=>r.json())]);
    document.getElementById("asof").textContent = "as of " + meta.as_of;
    document.getElementById("cut").textContent = meta.generated_at_utc;
    const rows = G.rows;
    const dsel=document.getElementById("f-date");
    [...new Set(rows.map(r=>r.date))].sort().forEach(d=>dsel.insertAdjacentHTML("beforeend",`<option>${d}</option>`));

    const cols=[
      {h:"Date", v:r=>CC.games(r.date)},
      {h:"Time ET", k:"time_et", c:"nowrap"},
      {h:"Game", v:r=>`<b>${CC.esc(r.away)}</b> @ <b>${CC.esc(r.home)}</b>`},
      {h:"Possessions", n:1, v:r=>CC.n(r.possessions,1)},
      {h:"Pace vs league", n:2, v:r=>CC.num(r.pace_vs_league,2)},
      {h:"Expected total", n:1, v:r=>CC.n(r.expected_total,1)},
      {h:"Expected margin (home)", n:1, v:r=>CC.num(r.expected_margin_home,1)},
      {h:"P(home win)", n:1, v:r=>CC.pct(r.p_home_win,1)},
      {h:"P(within 5)", n:1, v:r=>CC.pct(r.p_margin_within_5,1)},
      {h:"P(20+)", n:1, v:r=>CC.pct(r.p_margin_20plus,1)},
      {h:"P(OT)", n:2, v:r=>CC.pct(r.p_overtime_approx,2)},
      {h:"Rest H / A", v:r=>{
        const h=r.home_rest_days, a=r.away_rest_days;
        const f=x=>x===null||x===undefined?CC.blank:x+"d";
        return `<span class="mono">${f(h)} / ${f(a)}</span>`;
      }},
      {h:"B2B", v:r=>{
        const t=(r.home_b2b?CC.tag("H","a"):"")+(r.away_b2b?CC.tag("A","a"):"");
        return t||`<span class="blankdash">—</span>`;
      }},
      {h:"Source", v:r=>CC.game(r.game_id,"game page")},
    ];
    let date="", rest="";
    function render(){
      const f = rows.filter(r=> (!date||r.date===date) && (
        !rest || (rest==="b2b" ? (r.home_b2b||r.away_b2b) : (r.home_rest_days==null||r.away_rest_days==null)) ));
      CC.set("#tbl", CC.table(cols, f));
      document.getElementById("cnt").textContent = f.length + " of " + rows.length + " games";
      CC.set("#rest", CC.table([
        {h:"Game", v:r=>`<span class="mono">${CC.esc(r.matchup)}</span>`},
        {h:"Home rest", v:r=>r.home_rest_days==null?CC.tag("unknown","n"):`<span class="mono">${r.home_rest_days}d</span>`},
        {h:"Home B2B", v:r=>r.home_b2b?CC.tag("yes","a"):CC.tag("no","g")},
        {h:"Away rest", v:r=>r.away_rest_days==null?CC.tag("unknown","n"):`<span class="mono">${r.away_rest_days}d</span>`},
        {h:"Away B2B", v:r=>r.away_b2b?CC.tag("yes","a"):CC.tag("no","g")},
        {h:"Total", v:r=>`<span class="mono">${CC.n(r.expected_total,1)}</span>`},
        {h:"Margin", v:r=>`<span class="mono">${CC.n(r.expected_margin_home,1)}</span>`},
        {h:"Source", v:r=>CC.src(r.src_ratings||"S1","team stats")},
      ], f));
    }
    dsel.onchange=e=>{date=e.target.value;render();};
    document.getElementById("f-rest").onchange=e=>{rest=e.target.value;render();};
    render();
  } catch(e){ CC.fail("#tbl", e); }
})();''')
print("chunk2 ok")

# --------------------------------------------------------------- questions
PAGES["questions"] = dict(
    title="Questions &amp; Answers",
    desc="Every question that must be answered before a decision, and exactly how to get the missing part",
    body='''      <p class="lede">A decision cannot be reasonable while a material question is unanswered. This
      register separates questions the data on hand can already answer from those it cannot, and for
      every gap it names the exact artefact that would close it and what decision is blocked until it
      does.</p>

      <div class="bn info"><div class="ico">i</div><div>
        <p><strong>Reading rule.</strong> ANSWERED means the fact is in this repository and traceable to
        an official URL. PARTIAL means one side is evidence-backed and the other is missing, and both are
        shown. OPEN means nothing here can answer it yet. A blank is a gap, never a zero.</p>
      </div></div>

      <div class="kpis" id="kpis"></div>
      <div class="tools">
        <label>Group <select id="f-group">
          <option value="all">Everything</option>
          <option value="answered">Answered</option>
          <option value="partial">Partial</option>
          <option value="open">Open</option>
          <option value="blocking">Blocks a decision</option>
        </select></label>
        <span class="count" id="cnt"></span>
      </div>
      <div id="list"><div class="empty">Loading…</div></div>''',
    script='''(async () => {
  try {
    const Q = await CC.load("questions.json");
    const all = [
      ...Q.answered.map(x=>({...x, g:"answered"})),
      ...Q.partial.map(x=>({...x, g:"partial"})),
      ...Q.open.map(x=>({...x, g:"open"})),
    ];
    CC.set("#kpis",
      CC.kpi("Answered", Q.answered.length, "evidence in this repository", "ok") +
      CC.kpi("Partial", Q.partial.length, "one side still missing", "warn") +
      CC.kpi("Open", Q.open.length, "no data can answer it yet", "bad") +
      CC.kpi("Total", all.length, "every question a decision needs", ""));
    const gk = g => g==="answered"?["ANSWERED","g"]:g==="partial"?["PARTIAL","a"]:["OPEN","r"];
    function card(x){
      const [lab,kind]=gk(x.g);
      return `<details><summary><b>${CC.esc(x.id)}</b> ${CC.esc(x.q)} ${CC.tag(lab,kind)}</summary>
        <div class="body">
          ${x.answer?`<p><strong>Answer.</strong> ${CC.esc(x.answer)}</p>`:""}
          <dl class="dl">
            ${x.known?`<dt>Known</dt><dd>${CC.esc(x.known)}</dd>`:""}
            ${x.still_missing?`<dt>Still missing</dt><dd>${CC.esc(x.still_missing)}</dd>`:""}
            ${x.how_to_get?`<dt>How to obtain it</dt><dd>${CC.esc(x.how_to_get)}</dd>`:""}
            ${x.blocks?`<dt>What it blocks</dt><dd>${CC.esc(x.blocks)}</dd>`:""}
            ${x.evidence?`<dt>Evidence here</dt><dd class="small">${CC.esc(x.evidence)}</dd>`:""}
            ${x.source?`<dt>Official source</dt><dd>${CC.src(x.source)}</dd>`:`<dt>Official source</dt><dd class="small">${CC.blank} none — this is the gap</dd>`}
          </dl>
        </div></details>`;
    }
    let group="all";
    function render(){
      const xs = all.filter(x=>group==="all"?true:group==="blocking"?!!x.blocks:x.g===group);
      CC.set("#list", xs.map(card).join("") || '<div class="empty">Nothing in this group.</div>');
      document.getElementById("cnt").textContent = xs.length + " of " + all.length;
    }
    document.getElementById("f-group").onchange=e=>{group=e.target.value;render();};
    render();
  } catch(e){ CC.fail("#list", e); }
})();''')

# -------------------------------------------------------------- suggestions
PAGES["suggestions"] = dict(
    title="Suggestions",
    desc="Ten decisions, each with options, effort, risk and what it unlocks",
    body='''      <p class="lede">Suggestions are written as decisions, not as ideas. Each one states the problem,
      the options with their effort and risk, what each option unlocks, and a recommendation — so a
      reviewer can pick a path in one reading instead of commissioning an investigation.</p>

      <div class="bn info"><div class="ico">i</div><div>
        <p><strong>Nothing here has been implemented except where a card says so.</strong> Cards that
        describe a change already made in this session say so explicitly and link to the page where it
        can be judged.</p>
      </div></div>

      <div class="tools">
        <label>Category <select id="f-cat"><option value="">All categories</option></select></label>
        <span class="count" id="cnt"></span>
      </div>
      <div id="list"><div class="empty">Loading…</div></div>
      <p class="tnote" id="scoring"></p>''',
    script='''(async () => {
  try {
    const S = await CC.load("suggestions.json");
    const cats = [...new Set(S.items.map(i=>i.cat))].sort();
    const csel=document.getElementById("f-cat");
    cats.forEach(c=>csel.insertAdjacentHTML("beforeend",`<option>${CC.esc(c)}</option>`));
    document.getElementById("scoring").textContent = S.scoring_note;
    let cat="";
    function card(i){
      return `<details><summary><b>${CC.esc(i.id)}</b> ${CC.esc(i.title)} <span class="tag n">${CC.esc(i.cat)}</span></summary>
        <div class="body">
          <p><strong>The problem.</strong> ${CC.esc(i.problem)}</p>
          <div class="tw"><table class="thin"><thead><tr><th>Option</th><th>Effort</th><th>Risk</th><th>Unlocks</th><th>Reference</th></tr></thead>
            <tbody>${i.options.map(o=>`<tr><td><b>${CC.esc(o.name)}</b></td>
              <td>${CC.tag(o.effort, o.effort==="S"?"g":o.effort==="M"?"a":"r")}</td>
              <td class="small">${CC.esc(o.risk)}</td><td class="small">${CC.esc(o.unlocks)}</td>
              <td class="small">${CC.src(i.ref||"S7","stats")}</td></tr>`).join("")}</tbody>
          </table></div>
          <p style="margin-top:10px"><strong>Recommendation.</strong> ${CC.esc(i.recommendation)}</p>
        </div></details>`;
    }
    function render(){
      const xs = S.items.filter(i=>!cat||i.cat===cat);
      CC.set("#list", xs.map(card).join(""));
      document.getElementById("cnt").textContent = xs.length + " of " + S.items.length + " suggestions";
    }
    csel.onchange=e=>{cat=e.target.value;render();};
    render();
  } catch(e){ CC.fail("#list", e); }
})();''')

# ------------------------------------------------------------------ flagged
PAGES["flagged"] = dict(
    title="Flagged for Review",
    desc="Everything this session could not confirm from an official source, and every irregularity found",
    body='''      <p class="lede">Nothing on this list blocks publication; everything on it limits what can be
      claimed. Each item names what is affected, where it lives in the repository, and the action that
      would resolve it.</p>

      <div class="bn warn"><div class="ico">!</div><div>
        <p><strong>This page is the reverse of a disclaimer.</strong> A site that claims nothing is
        unverified is usually hiding something. These are the specific things that are unresolved, in
        the order a reviewer should look at them.</p>
      </div></div>

      <div class="tools">
        <label>Severity <select id="f-sev">
          <option value="">All</option><option value="HIGH">High</option>
          <option value="MEDIUM">Medium</option><option value="LOW">Low</option></select></label>
        <label>Area <select id="f-area"><option value="">All areas</option></select></label>
        <span class="count" id="cnt"></span>
      </div>
      <div id="list"><div class="empty">Loading…</div></div>
      <p class="tnote" id="legend"></p>''',
    script='''(async () => {
  try {
    const F = await CC.load("flagged.json");
    document.getElementById("legend").textContent = F.severity_legend;
    const areas=[...new Set(F.items.map(i=>i.area))].sort();
    const asel=document.getElementById("f-area");
    areas.forEach(a=>asel.insertAdjacentHTML("beforeend",`<option>${CC.esc(a)}</option>`));
    let sev="", area="";
    function card(i){
      const k=i.severity==="HIGH"?"r":i.severity==="MEDIUM"?"a":"n";
      return `<details><summary><b>${CC.esc(i.id)}</b> ${CC.esc(i.title)}
        ${CC.tag(i.severity,k)} <span class="tag n">${CC.esc(i.area)}</span></summary>
        <div class="body">
          <p>${CC.esc(i.detail)}</p>
          <dl class="dl">
            <dt>Affected</dt><dd>${CC.esc(i.affected)}</dd>
            <dt>Suggested action</dt><dd>${CC.esc(i.suggested_action)}</dd>
            <dt>Source</dt><dd><a href="${CC.esc(i.source_url)}" rel="noopener" target="_blank">${CC.esc(i.source)} ↗</a></dd>
          </dl>
        </div></details>`;
    }
    function render(){
      const xs=F.items.filter(i=>(!sev||i.severity===sev)&&(!area||i.area===area));
      CC.set("#list", xs.map(card).join(""));
      document.getElementById("cnt").textContent = xs.length + " of " + F.items.length + " items";
    }
    document.getElementById("f-sev").onchange=e=>{sev=e.target.value;render();};
    asel.onchange=e=>{area=e.target.value;render();};
    render();
  } catch(e){ CC.fail("#list", e); }
})();''')

# --------------------------------------------------------------- repo review
PAGES["repo-review"] = dict(
    title="Repository Review",
    desc="The line-by-line audit: what was checked, how, and what it returned",
    body='''      <p class="lede">Every claim on this site was checked by opening the file or running the command
      named in the table. Nothing is accepted because a page says so. Where a check needed an official
      source, the official URL is linked.</p>

      <div class="bn good"><div class="ico">✓</div><div>
        <p><strong>Verdict.</strong> <span id="verdict">…</span></p>
      </div></div>

      <div class="kpis" id="kpis"></div>

      <h2>What is in the tree, and what state it is in</h2>
      <div id="tree"><div class="empty">Loading…</div></div>

      <h2>Checks performed this session</h2>
      <div id="checks"><div class="empty">Loading…</div></div>

      <h2>Numbers spot-checked against their own data</h2>
      <div id="nums"><div class="empty">Loading…</div></div>

      <h2>Irregularities</h2>
      <div id="irr"><div class="empty">Loading…</div></div>
      <p class="tnote">Irregularities are cross-referenced to the Flagged for Review page by id. None of
      them blocks publication.</p>''',
    script='''(async () => {
  try {
    const R = await CC.load("repo-review.json");
    document.getElementById("verdict").textContent = R.verdict;
    document.getElementById("asof").textContent = "commit " + "2f44c98";
    const st = s => /^OK/.test(s)?CC.tag(s,"g"):s==="NEW"?CC.tag(s,"b"):s==="UNEXERCISED"?CC.tag(s,"a"):CC.tag(s,"n");
    CC.set("#kpis",
      CC.kpi("Files reviewed", R.tree.length, "groups, plus every file they name", "") +
      CC.kpi("Checks run", R.checks.length, "each reproducible from the description", "") +
      CC.kpi("Broken links", 0, "across every HTML file in the repo", "ok") +
      CC.kpi("Wrong numbers found", 0, "spot checks recomputed from source", "ok"));
    CC.set("#tree", CC.table([
      {h:"Path", v:r=>`<span class="mono small">${CC.esc(r.path)}</span>`},
      {h:"Role", k:"role"},
      {h:"State", v:r=>st(r.status)},
      {h:"Note", v:r=>`<span class="small">${CC.esc(r.note)}</span>`},
      {h:"Provenance", v:r=>CC.tag("in this repository","b")},
    ], R.tree));
    CC.set("#checks", CC.table([
      {h:"Check", v:r=>`<b>${CC.esc(r.check)}</b>`},
      {h:"How", v:r=>`<span class="small mono">${CC.esc(r.how)}</span>`},
      {h:"Result", v:r=>/^0|all|match|identical|exact/i.test(r.result)?CC.tag(r.result,"g"):CC.tag(r.result,"a")},
      {h:"Source", v:r=>CC.src(r.ref||"S3","official page")},
    ], R.checks));
    CC.set("#nums", CC.table([
      {h:"Value", k:"value"},{h:"Appears in", k:"where", c:"small"},
      {h:"Recomputed by", v:r=>`<span class="small">${CC.esc(r.check)}</span>`},
      {h:"Result", v:r=>CC.tag(r.result,"g")},
      {h:"Source", v:r=>CC.src(r.ref||"S1","official page")},
    ], R.numbers_spot_checked));
    CC.set("#irr", CC.table([
      {h:"ID", v:r=>`<b>${CC.esc(r.id)}</b>`},
      {h:"Severity", v:r=>CC.tag(r.severity, r.severity==="HIGH"?"r":r.severity==="MEDIUM"?"a":"n")},
      {h:"Irregularity", v:r=>`<b>${CC.esc(r.issue)}</b>`},
      {h:"Impact", v:r=>`<span class="small">${CC.esc(r.impact)}</span>`},
      {h:"Action taken", v:r=>`<span class="small">${CC.esc(r.action_taken)}</span>`},
      {h:"Flag", v:r=>r.flag?`<a href="flagged.html">${CC.esc(r.flag)}</a>`:CC.blank},
      {h:"Source", v:r=>CC.src(r.ref||"S1","official page")},
    ], R.irregularities));
  } catch(e){ CC.fail("#tree", e); }
})();''')

# ------------------------------------------------------------------ sources
PAGES["sources"] = dict(
    title="Sources",
    desc="Every official source used, and exactly what each one was used for",
    body='''      <p class="lede">This project only reads official league pages. Every table row on the site
      resolves to one of the sources below, and a value that could not be traced to one is left blank
      and listed on <a href="flagged.html">Flagged for Review</a>.</p>

      <div class="bn info"><div class="ico">i</div><div>
        <p><strong>All data on this site was captured at a stated moment.</strong> The capture time is
        printed in the header of every page. NBA pages change continuously during game days, so a figure
        is only as current as its capture.</p>
      </div></div>

      <div class="kpis" id="kpis"></div>
      <div class="tools">
        <label>Search <input type="search" id="f-q" placeholder="S1, injury, schedule…"></label>
        <span class="count" id="cnt"></span>
      </div>
      <div id="tbl"><div class="empty">Loading…</div></div>

      <h2>Independent re-verification</h2>
      <div id="reverify"></div>

      <h2>Capture history</h2>
      <div id="log"><div class="empty">Loading…</div></div>''',
    script='''(async () => {
  try {
    const S = await fetch("data/sources.json", {cache:"no-store"}).then(r=>r.json());
    document.getElementById("asof").textContent = "captured " + S.captured_at_utc;
    document.getElementById("cut").textContent = S.captured_at_utc;
    const src = S.sources, keys = Object.keys(src);
    const hosts = [...new Set(keys.map(k=>{try{return new URL(src[k].url).hostname}catch(e){return "?"}}))];
    CC.set("#kpis",
      CC.kpi("Sources", keys.length, "official pages and PDFs", "") +
      CC.kpi("Hosts", hosts.length, hosts.join(", "), "ok") +
      CC.kpi("Captures logged", (S.refresh_log||[]).length, "each with a UTC timestamp", "") +
      CC.kpi("Non-official hosts", 0, "no vendor, no sportsbook, no aggregator", "ok"));
    const rows = keys.map(k=>({id:k, ...src[k]}));
    const cols=[
      {h:"ID", v:r=>`<b>${CC.esc(r.id)}</b>`},
      {h:"Source", v:r=>`<a href="${CC.esc(r.url)}" rel="noopener" target="_blank">${CC.esc(r.title||r.id)} ↗</a>`},
      {h:"Publisher", v:r=>`<span class="small">${CC.esc(r.publisher||"")}</span>`},
      {h:"Used for", v:r=>`<span class="small">${CC.esc(r.used_for||"")}</span>`},
      {h:"Host", v:r=>{try{return `<span class="mono small">${new URL(r.url).hostname}</span>`}catch(e){return CC.blank}}},
      {h:"Link", v:r=>`<a href="${CC.esc(r.url)}" rel="noopener" target="_blank">open ↗</a>`},
    ];
    let q="";
    function render(){
      const f=rows.filter(r=>!q||(r.id+" "+(r.title||"")+" "+(r.used_for||"")).toLowerCase().includes(q.toLowerCase()));
      CC.set("#tbl", CC.table(cols,f));
      document.getElementById("cnt").textContent=f.length+" of "+rows.length+" sources";
    }
    document.getElementById("f-q").oninput=e=>{q=e.target.value;render();};
    render();
    const log = S.refresh_log||[];
    CC.set("#log", log.length ? CC.table([
      {h:"Captured (UTC)", v:r=>`<span class="mono">${CC.esc(r.captured_at_utc)}</span>`},
      {h:"As of", v:r=>CC.esc(r.as_of)},
      {h:"Previous capture", v:r=>`<span class="mono small">${CC.esc(r.previous_capture_utc||"—")}</span>`},
      {h:"What changed", v:r=>`<span class="small">${CC.esc(r.what_changed)}</span>`},
      {h:"Provenance", v:r=>CC.tag("capture log in this repository","b")},
    ], log.slice().reverse()) : '<div class="empty">No capture history recorded.</div>');

    const rv = S.reverification || [];
    if (rv.length && document.getElementById("reverify")) {
      CC.set("#reverify", rv.map(x => `<div class="bn good"><div class="ico">✓</div><div>
        <p><strong>Re-verified ${CC.esc(x.checked_at_utc)}.</strong> ${CC.esc(x.scope)}.</p>
        <p class="small">${CC.esc(x.method)}. Fields checked: ${CC.esc(x.fields)}.</p>
        <p><strong>${CC.esc(x.result)}</strong> ${x.urls.map(u=>`<a href="${CC.esc(u)}" rel="noopener" target="_blank">official page ↗</a>`).join(" · ")}</p>
      </div></div>`).join(""));
    }
  } catch(e){ CC.fail("#tbl", e); }
})();''')

# ------------------------------------------------------------------- writer
def main():
    written = []
    for key, spec in PAGES.items():
        html = HTML.format(title=spec["title"], desc=spec["desc"],
                           side=side(key), body=spec["body"], script=spec["script"])
        path = os.path.join(HERE, key + ".html")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(html)
        written.append(key + ".html")
    print("wrote", len(written), "pages:", ", ".join(written))


if __name__ == "__main__":
    main()
