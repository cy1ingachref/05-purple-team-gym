#!/usr/bin/env python3
"""
build_dashboard.py — Run the coevolution gym and emit a single self-contained
HTML dashboard (no CDN, no network, opens from file://).

The dashboard shows the ARMS RACE:
  - RED rolling win-rate over rounds (declines as BLUE adapts)
  - Residual risk over rounds (converges)
  - BLUE total coverage over rounds (ramps to budget)
  - Final BLUE defense coverage vs final RED threat per technique
  - Per-technique base vs final success probability (the E-Tafakna JWT bugs
    highlighted)

Run:  python build_dashboard.py
Out:  dashboard.html  (open in any browser)
"""

import json
import os

import gym
import techniques as tech

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    history, red, blue, meta = gym.run_simulation(rounds=200, seed=42)
    summ = gym.summarize(history, meta)

    # Per-technique base vs final success probability (after BLUE converged).
    final_cov = blue.coverage
    tech_rows = []
    for t in tech.TECHNIQUES:
        base = t["base"]
        final = tech.success_prob(t["id"], final_cov)
        tech_rows.append({
            "id": t["id"],
            "name": t["name"],
            "tactic": t["tactic"],
            "base": round(base, 2),
            "final": round(final, 2),
            "reduction": round(base - final, 2),
            "mit_by": t["mit_by"],
        })
    # Sort: E-Tafakna JWT bugs first, then by reduction.
    jwt_ids = {"jwt_none", "jwt_weak_secret", "jwt_strcmp"}
    tech_rows.sort(key=lambda r: (r["id"] not in jwt_ids, -r["reduction"]))

    data = {
        "history": history,
        "summary": summ,
        "shock": {
            "round": meta["shock_round"],
            "pre_shock_risk": meta["pre_shock_risk"],
            "peak_risk": meta["peak_risk"],
            "adaptation_latency": meta["adaptation_latency"],
            "recovered_risk": meta["recovered_risk"],
        },
        "techniques": tech_rows,
        "defenses": {d["id"]: d["name"] for d in tech.DEFENSES},
        "coverage_final": {k: round(v, 2) for k, v in blue.coverage.items()},
        "threat_final": {k: round(v, 2) for k, v in red.threat_profile().items()},
    }

    html = HTML_TEMPLATE.replace("/*__DATA__*/", json.dumps(data))
    out = os.path.join(HERE, "dashboard.html")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(html)
    print("Wrote", out)
    print("RED win-rate  early=%.3f late=%.3f" % (
        summ["early_red_win_rate"], summ["late_red_win_rate"]))
    print("Residual risk early=%.3f late=%.3f" % (
        summ["early_residual_risk"], summ["late_residual_risk"]))


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Purple-Team Coevolution Gym</title>
<style>
  :root{--bg:#0b0e14;--panel:#131825;--ink:#e6edf3;--muted:#8b98a9;
        --red:#ff5d6c;--blue:#4ea8ff;--green:#3ddc97;--line:#222b3a;}
  *{box-sizing:border-box}
  body{margin:0;font:14px/1.5 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
       background:var(--bg);color:var(--ink)}
  header{padding:22px 26px;border-bottom:1px solid var(--line);
         background:linear-gradient(90deg,#161b29,#0b0e14)}
  h1{margin:0;font-size:20px;letter-spacing:.5px}
  .sub{color:var(--muted);margin-top:4px}
  .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:16px;padding:20px}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
  .card h2{margin:0 0 8px;font-size:14px;color:var(--muted);text-transform:uppercase;letter-spacing:1px}
  canvas{width:100%;height:220px;display:block}
  .verdict{display:inline-block;padding:4px 10px;border-radius:999px;font-weight:700;font-size:12px}
  .ok{background:rgba(61,220,151,.15);color:var(--green);border:1px solid var(--green)}
  table{width:100%;border-collapse:collapse;font-size:12.5px}
  th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line)}
  th{color:var(--muted);text-transform:uppercase;font-size:11px;letter-spacing:.5px}
  .tag{color:var(--blue)} .hi{color:var(--red);font-weight:700}
  .legend span{margin-right:14px;font-size:12px;color:var(--muted)}
  .dot{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:5px;vertical-align:middle}
  footer{padding:14px 26px;color:var(--muted);border-top:1px solid var(--line);font-size:12px}
</style>
</head>
<body>
<header>
  <h1>Purple-Team Coevolution Gym</h1>
  <div class="sub">An autonomous red agent and an autonomous blue agent learn against each other.
  Grounded in the E-Tafakna JWT bug class (legal-tech SaaS, authorized pentest).</div>
</header>

<div class="grid">
  <div class="card">
    <h2>RED rolling win-rate vs BLUE</h2>
    <div class="legend"><span><i class="dot" style="background:var(--red)"></i>RED success (20-rd window)</span>
      <span><i class="dot" style="background:var(--green)"></i>Residual risk</span></div>
    <canvas id="c1"></canvas>
  </div>
  <div class="card">
    <h2>BLUE coverage deployed (budget)</h2>
    <canvas id="c2"></canvas>
  </div>
  <div class="card">
    <h2>Convergence verdict</h2>
    <div id="verdict"></div>
    <p style="color:var(--muted)" id="metrics"></p>
  </div>
  <div class="card">
    <h2>⚡ Zero-day shock response</h2>
    <p style="color:var(--muted)" id="shock"></p>
  </div>
  <div class="card">
    <h2>Final posture: RED threat vs BLUE coverage</h2>
    <canvas id="c3"></canvas>
  </div>
  <div class="card" style="grid-column:1/-1">
    <h2>Technique risk reduction (E-Tafakna JWT bugs flagged)</h2>
    <table id="tt"><thead><tr>
      <th>Technique</th><th>MITRE</th><th>Base p</th><th>Final p</th><th>Reduction</th><th>Mitigated by</th>
    </tr></thead><tbody></tbody></table>
  </div>
</div>

<footer>
  Deterministic (seed=42). Zero dependencies. Open offline. Built to demonstrate emergent
  purple-team convergence: a finite security budget forces trade-offs, and both agents adapt.
</footer>

<script>
const DATA = /*__DATA__*/;
const C = {red:'#ff5d6c', blue:'#4ea8ff', green:'#3ddc97', muted:'#8b98a9', line:'#222b3a'};

function lineChart(canvas, series, opts){
  opts = opts||{};
  const dpr = window.devicePixelRatio||1;
  const w = canvas.clientWidth, h = canvas.clientHeight;
  canvas.width=w*dpr; canvas.height=h*dpr;
  const ctx = canvas.getContext('2d'); ctx.scale(dpr,dpr);
  const pad={l:34,r:10,t:10,b:20};
  const n = series[0].points.length;
  let maxY=opts.maxY||0; for(const s of series) for(const v of s.points) maxY=Math.max(maxY,v);
  maxY = opts.maxY|| (maxY*1.1)||1;
  const X = i => pad.l + (w-pad.l-pad.r)*(i/(n-1));
  const Y = v => h-pad.b - (h-pad.t-pad.b)*(v/maxY);
  ctx.strokeStyle=C.line; ctx.lineWidth=1;
  ctx.beginPath(); ctx.moveTo(pad.l,h-pad.b); ctx.lineTo(w-pad.r,h-pad.b); ctx.stroke();
  // y gridlines
  ctx.fillStyle=C.muted; ctx.font='10px monospace';
  for(let g=0;g<=4;g++){const v=maxY*g/4; const y=Y(v);
    ctx.strokeStyle=C.line; ctx.beginPath(); ctx.moveTo(pad.l,y); ctx.lineTo(w-pad.r,y); ctx.stroke();
    ctx.fillText(v.toFixed(2), 4, y+3);}
  // shock marker
  if(DATA.shock && DATA.shock.round>0){
    const xs=X(DATA.shock.round);
    ctx.strokeStyle='rgba(255,255,255,.35)'; ctx.setLineDash([4,4]);
    ctx.beginPath(); ctx.moveTo(xs,pad.t); ctx.lineTo(xs,h-pad.b); ctx.stroke(); ctx.setLineDash([]);
    ctx.fillStyle=C.muted; ctx.fillText('⚡zero-day', xs+3, pad.t+10);
  }
  for(const s of series){
    ctx.strokeStyle=s.color; ctx.lineWidth=2; ctx.beginPath();
    s.points.forEach((v,i)=>{const x=X(i),y=Y(v); i?ctx.lineTo(x,y):ctx.moveTo(x,y);});
    ctx.stroke();
  }
}

function barChart(canvas, items, color){
  const dpr=window.devicePixelRatio||1;
  const w=canvas.clientWidth,h=canvas.clientHeight; canvas.width=w*dpr;canvas.height=h*dpr;
  const ctx=canvas.getContext('2d'); ctx.scale(dpr,dpr);
  const pad={l:110,r:30,t:6,b:6};
  const n=items.length, bw=(h-pad.t-pad.b)/n;
  const max=Math.max(...items.map(d=>d.v),0.01);
  ctx.font='11px monospace';
  items.forEach((d,i)=>{
    const y=pad.t+i*bw+bw*0.15, bh=bw*0.7;
    ctx.fillStyle=C.muted; ctx.fillText(d.label, 4, y+bh*0.7);
    const bw2=(w-pad.l-pad.r)*(d.v/max);
    ctx.fillStyle=color; ctx.fillRect(pad.l,y,bw2,bh);
    ctx.fillStyle=C.ink; ctx.fillText(d.v.toFixed(2), pad.l+bw2+4, y+bh*0.7);
  });
}

// round indices
const H=DATA.history, N=H.length;
const idx=H.map((_,i)=>i);
const win = H.map(h=>h.red_win_rate);
const risk= H.map(h=>h.residual_risk);
const cov = H.map(h=>h.blue_coverage_total);

lineChart(document.getElementById('c1'),[
  {color:C.red, points:win},
  {color:C.green, points:risk},
]);
lineChart(document.getElementById('c2'),[{color:C.blue, points:cov}],{maxY:Math.max(...cov)*1.1});

// final posture
const defIds=Object.keys(DATA.coverage_final);
const covItems=defIds.map(d=>({label:DATA.defenses[d].slice(0,16), v:DATA.coverage_final[d]}));
const techIds=Object.keys(DATA.threat_final);
const thrItems=techIds.map(t=>({label:t.slice(0,16), v:DATA.threat_final[t]}));
// combine into one canvas: top half coverage, bottom half threat
(function(){
  const cv=document.getElementById('c3'); const dpr=window.devicePixelRatio||1;
  const w=cv.clientWidth,h=cv.clientHeight; cv.width=w*dpr;cv.height=h*dpr;
  const ctx=cv.getContext('2d'); ctx.scale(dpr,dpr);
  const half=h/2;
  // coverage (top)
  ctx.fillStyle=C.muted; ctx.font='10px monospace'; ctx.fillText('BLUE coverage',6,12);
  const cMax=Math.max(...covItems.map(d=>d.v),1);
  covItems.forEach((d,i)=>{const y=18+i*(half-18)/covItems.length; const bh=(half-18)/covItems.length*0.7;
    ctx.fillStyle=C.muted; ctx.fillText(d.label,4,y+bh);
    ctx.fillStyle=C.blue; ctx.fillRect(120,y,(w-150)*(d.v/cMax),bh);});
  // threat (bottom)
  const t0=half; ctx.fillStyle=C.muted; ctx.fillText('RED threat',6,t0+10);
  const tMax=Math.max(...thrItems.map(d=>d.v),0.01);
  thrItems.forEach((d,i)=>{const y=t0+16+i*(half-16)/thrItems.length; const bh=(half-16)/thrItems.length*0.7;
    ctx.fillStyle=C.muted; ctx.fillText(d.label,4,y+bh);
    ctx.fillStyle=C.red; ctx.fillRect(120,y,(w-150)*(d.v/tMax),bh);});
})();

// verdict
const s=DATA.summary;
const converged = s.late_residual_risk < s.early_residual_risk;
const v=document.getElementById('verdict');
v.innerHTML = '<span class="verdict '+((converged?'ok':'')||'')+'">'+
  (converged?'CONVERGED — agents learned':'NOT CONVERGED')+'</span>';
document.getElementById('metrics').innerHTML =
  'RED win-rate: '+s.early_red_win_rate.toFixed(3)+' → '+s.late_red_win_rate.toFixed(3)+'<br>'+
  'Residual risk: '+s.early_residual_risk.toFixed(3)+' → '+s.late_residual_risk.toFixed(3)+'<br>'+
  'BLUE budget used: '+Object.values(DATA.coverage_final).reduce((a,b)=>a+b,0).toFixed(2);

// shock card
const sh=DATA.shock||{};
const shEl=document.getElementById('shock');
if(sh.round){
  shEl.innerHTML =
    'At round <b>'+sh.round+'</b> a zero-day appears.<br>'+
    'Risk spikes '+sh.pre_shock_risk.toFixed(3)+' → <span class="hi">'+sh.peak_risk.toFixed(3)+'</span>.<br>'+
    'BLUE deploys the emergency patch and recovers in <b>'+(sh.adaptation_latency||'?')+
    ' rounds</b> (recovered risk '+ (sh.recovered_risk!=null?sh.recovered_risk.toFixed(3):'-') +').<br>'+
    '<span style="color:var(--green)">The defender adapts to the unknown — that is the point.</span>';
} else {
  shEl.textContent='No shock scenario configured.';
}

// table
const tb=document.querySelector('#tt tbody');
DATA.techniques.forEach(t=>{
  const tr=document.createElement('tr');
  const isJwt=['jwt_none','jwt_weak_secret','jwt_strcmp'].includes(t.id);
  tr.innerHTML='<td class="'+(isJwt?'hi':'')+'">'+t.name+(isJwt?' ★':'')+'</td>'+
    '<td class="tag">'+t.tactic+'</td><td>'+t.base+'</td><td>'+t.final+'</td>'+
    '<td>'+(t.reduction>0?'−':'')+Math.abs(t.reduction).toFixed(2)+'</td>'+
    '<td class="tag">'+DATA.defenses[t.mit_by]+'</td>';
  tb.appendChild(tr);
});
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
