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
      <p class="tnote">Baseline = season per-game average from the official player table. Projection
      applies a pace factor, an opponent defensive factor and, where a teammate is officially out, a
      usage factor. A player with no official status entry is not assumed available or unavailable;
      the availability adjustment is simply not applied.</p>''',
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
        {h:"Prob.", v:()=>CC.blank},
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
      <p class="tnote">PROVISIONAL means the sample is between 10 and 29 graded plays; N/A means the
      gate cannot be evaluated for that strategy (for example a correlation limit on a single-leg
      strategy); NOT RUN means the gate needs data not present in this repository.</p>''',
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
    ];
    const better=(a,b,lower=true)=> lower? (a<b?a===b?null:true:false) : (a>b?a===b?null:true:false);
    const rows = [
      {k:"Margin MAE (pts)", m:m.mae_margin_model, r:m.mae_margin_ref, win:better(m.mae_margin_model,m.mae_margin_ref), note:"Average absolute error on the home margin. Lower is better."},
      {k:"Margin RMSE (pts)", m:m.rmse_margin_model, r:m.rmse_margin_ref, win:better(m.rmse_margin_model,m.rmse_margin_ref), note:"Penalises large misses. Lower is better."},
      {k:"Margin bias (pts)", m:m.bias_margin_model, r:null, win:null, note:"Mean signed error. Zero is unbiased."},
      {k:"Total MAE (pts)", m:m.mae_total_model, r:m.mae_total_ref, win:better(m.mae_total_model,m.mae_total_ref), note:"Lower is better. This is the one the model loses."},
      {k:"Total RMSE (pts)", m:m.rmse_total_model, r:m.rmse_total_ref, win:better(m.rmse_total_model,m.rmse_total_ref), note:"Lower is better."},
      {k:"Brier score", m:m.brier_model, r:m.brier_ref, win:better(m.brier_model,m.brier_ref), note:"Probability calibration on the moneyline. Lower is better."},
      {k:"Log loss", m:m.logloss_model, r:m.logloss_ref, win:better(m.logloss_model,m.logloss_ref), note:"Probability calibration, harsher on confident misses."},
      {k:"Straight up", m:m.straight_up_model, r:m.straight_up_ref, win:null, note:"Winner picks. Identical record, so the tie is left as no comparison."},
      {k:"Margin MAE, parameters zeroed", m:m.mae_margin_zeroed_params, r:m.mae_margin_model, win:better(m.mae_margin_zeroed_params,m.mae_margin_model), note:"The fitted HCA and B2B terms versus no parameters at all."},
      {k:"Bootstrap 95% CI, model MAE", m:"["+m.bootstrap_mae_model_95.join(", ")+"]", r:"["+m.bootstrap_mae_ref_95.join(", ")+"]", win:null, note:"The two intervals overlap almost completely, which is why no stability claim is made."},
    ];
    CC.set("#cmp", CC.table(cols, rows));

    const f = V.fit || {};
    CC.set("#fit", CC.table([
      {h:"Parameter", v:r=>`<b>${CC.esc(r.k)}</b>`},
      {h:"Value", n:1, v:r=>CC.esc(r.v)},
      {h:"Standard error", n:2, v:r=>CC.esc(r.se)},
      {h:"t", n:2, v:r=>CC.esc(r.t)},
      {h:"Read", v:r=>`<span class="small">${CC.esc(r.note)}</span>`},
    ], Object.entries(f).filter(([k,v])=>typeof v==="number"||typeof v==="string").map(([k,v])=>({k, v:v, se:"—", t:"—", note:""})).slice(0,0)
      .concat([
        {k:"Home-court advantage (pts)", v:f.hca, se:f.hca_se, t:f.hca_t, note:"Fitted on the test window; disclosed as in-sample."},
        {k:"Back-to-back penalty (pts)", v:f.b2b, se:f.b2b_se, t:f.b2b_t, note:"Fitted on the test window; disclosed as in-sample."},
        {k:"Total bias (pts)", v:f.total_bias, se:f.total_bias_se, t:f.total_bias_t, note:"Added to every originated total."},
        {k:"Total back-to-back coefficient", v:f.total_b2b_coef, se:f.total_b2b_se, t:f.total_b2b_t, note:"Applied per team on a back-to-back."},
        {k:"Shrinkage k (games)", v:f.shrink_k, se:"—", t:"—", note:"Empirical-Bayes prior weight. Sensitivity sweep published on the Model page of Build B."},
        {k:"Residual sd, margin", v:f.sigma_margin, se:"—", t:"—", note:"Drives every margin probability."},
        {k:"Residual sd, total", v:f.sigma_total, se:"—", t:"—", note:"Drives every total probability."},
      ].filter(r=>r.v!==undefined)));

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
      independence shortcut. A positive rho <em>reduces</em> the joint probability of two overs — which
      is why multiplying marginals is the wrong default even when each leg looks good.</p>
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
      {h:"Question it answers", v:r=>`<span class="small">${CC.esc(r.why)}</span>`},
      {h:"Status", v:r=>CC.tag(r.status,"g")},
      {h:"Source", v:()=>CC.src("S1","team stats")},
    ], C.measured));

    const mr = Object.entries(C.sgp_rho).map(([k,v])=>({k,v}));
    CC.set("#mod", CC.table([
      {h:"Relationship", v:r=>`<b>${CC.esc(r.k.replace(/_/g," "))}</b>`},
      {h:"Assumed rho", n:2, v:r=>CC.num(r.v,3)},
      {h:"Direction", v:r=>r.v>0?CC.tag("positive","a"):r.v<0?CC.tag("negative","b"):CC.tag("none","n")},
      {h:"Why this sign and size", v:r=>`<span class="small">${CC.esc({
        side_total:"A fast game produces more possessions, so the total and the margin are close to independent; set to zero rather than guessed.",
        player_total_same_team:"A player's points and his team's total move together through possessions and pace.",
        player_side_same_team:"A star scoring well usually means his team is performing, so side and player have a mild positive link.",
        two_teammates:"Two teammates compete for the same possessions and minutes, so their overs are mildly negatively dependent.",
        two_opponents:"Opposing players are near-independent on the same night; a small positive value is allowed for a shared pace environment."
      }[r.k] || "No rationale recorded.")}</span>`},
      {h:"Data status", v:()=>CC.tag("model-derived","r")},
    ], mr));

    const g = C.parlay_pricing_grid || [];
    if (g.length) {
      const keys = Object.keys(g[0]);
      CC.set("#grid", CC.table(keys.map(k=>({h:k, v:r=> r[k]===null?CC.blank:(CC.isNum(r[k])?CC.n(r[k],k.toLowerCase().includes("rho")?2:3):CC.esc(r[k]))})), g));
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
