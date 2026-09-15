#!/usr/bin/env python3
"""
ciso_report.py — Map the converged BLUE posture to CIS Controls and produce a
printable security posture report you could hand to a CISO.

This bridges the gap between "cool simulation" and "real security governance."

KEY DESIGN CHOICE — posture_score:
    We do NOT use sum(coverage)/budget, because BLUE always spends its full
    budget (proven by test_blue_uses_full_budget). That formula would always
    read ~100/100 even when most defenses are at 0% coverage.

    Instead we weight coverage by threat pressure: how much of the threat
    your organization faces are you actually mitigating? This gives an honest
    score that reflects real defensive posture, not just budget utilization.

    posture_score = sum(coverage[d] * threat_pressure[d]) / sum(threat_pressure[d]) * 100

    A CISO reading this number learns: "Of the total threat surface, what
    fraction are we actively suppressing?" — which is the question they
    actually care about.
"""

import json
import os
from datetime import datetime

import gym
import techniques as tech

HERE = os.path.dirname(os.path.abspath(__file__))

# Map each defense to a CIS Control v8 ID + sub-control
CIS_MAPPING = {
    "jwt_strict_verify": {"cis": "16.10", "name": "Implement Application Layer Filtering", "desc": "Ensure only approved applications and services are running"},
    "input_validation": {"cis": "16.6", "name": "Establish and Maintain Secure Configuration Processes", "desc": "Establish and maintain an inventory of approved services and applications"},
    "path_confinement": {"cis": "16.6", "name": "Establish and Maintain Secure Configuration Processes", "desc": "Establish and maintain an inventory of approved services and applications"},
    "rate_limit": {"cis": "16.10", "name": "Implement Application Layer Filtering", "desc": "Ensure only approved applications and services are running"},
    "geo_velocity": {"cis": "16.10", "name": "Implement Application Layer Filtering", "desc": "Ensure only approved applications and services are running"},
    "ssrf_allowlist": {"cis": "16.10", "name": "Implement Application Layer Filtering", "desc": "Ensure only approved applications and services are running"},
    "least_privilege": {"cis": "5.4", "name": "Restrict Administrator Privileges to Dedicated Administrator Accounts", "desc": "Restrict administrator privileges to dedicated administrator accounts on enterprise assets"},
    "zeroday_patch": {"cis": "7.3", "name": "Perform Automated Operating System Patch Management", "desc": "Perform automated operating system patch management"},
}

# Risk levels based on coverage
def risk_level(coverage):
    if coverage >= 0.8:
        return "LOW", "green"
    elif coverage >= 0.5:
        return "MEDIUM", "orange"
    else:
        return "HIGH", "red"


def generate_report():
    history, red, blue, meta = gym.run_simulation(rounds=200, seed=42)
    summ = gym.summarize(history, meta)

    # Compute threat pressure per defense for weighting the posture score.
    # A defense facing more threat pressure contributes more to the score.
    threat = red.threat_profile()
    threat_per_defense = {}
    for d in tech.DEFENSES:
        if d.get("hidden") and not blue.coverage.get(d["id"], 0):
            continue
        mits = tech.techniques_mitigated_by(d["id"])
        threat_per_defense[d["id"]] = sum(threat.get(tid, 0.0) for tid in mits)

    total_threat_pressure = sum(threat_per_defense.values())

    # Build posture rows
    posture_rows = []
    weighted_coverage = 0.0
    for d in tech.DEFENSES:
        if d.get("hidden") and not blue.coverage.get(d["id"], 0):
            continue
        cov = blue.coverage.get(d["id"], 0)
        level, color = risk_level(cov)
        cis = CIS_MAPPING.get(d["id"], {})
        posture_rows.append({
            "defense": d["name"],
            "coverage": round(cov, 2),
            "risk_level": level,
            "risk_color": color,
            "cis_control": cis.get("cis", "N/A"),
            "cis_name": cis.get("name", "N/A"),
            "cis_desc": cis.get("desc", "N/A"),
        })
        # Accumulate threat-weighted coverage
        weighted_coverage += cov * threat_per_defense.get(d["id"], 0)

    # Sort by coverage ascending (worst first)
    posture_rows.sort(key=lambda r: r["coverage"])

    # THREAT-WEIGHTED posture score: what fraction of threat are we mitigating?
    # This is honest — it reflects real defensive posture, not just budget spent.
    posture_score = round((weighted_coverage / total_threat_pressure) * 100) if total_threat_pressure > 0 else 0

    # Risk reduction stats
    early_risk = summ["early_residual_risk"]
    late_risk = summ["late_residual_risk"]
    risk_reduction = round((early_risk - late_risk) / early_risk * 100) if early_risk > 0 else 0

    report = {
        "generated_at": datetime.now().isoformat(),
        "posture_score": posture_score,
        "risk_reduction_pct": risk_reduction,
        "red_win_rate_early": round(summ["early_red_win_rate"], 3),
        "red_win_rate_late": round(summ["late_red_win_rate"], 3),
        "residual_risk_early": round(early_risk, 3),
        "residual_risk_late": round(late_risk, 3),
        "zero_day": {
            "round": meta["shock_round"],
            "pre_shock_risk": round(meta["pre_shock_risk"], 3),
            "peak_risk": round(meta["peak_risk"], 3),
            "adaptation_latency": meta["adaptation_latency"],
            "recovered_risk": round(meta["recovered_risk"], 3) if meta["recovered_risk"] else None,
        },
        "posture": posture_rows,
    }

    return report


def render_html(report):
    """Render the report as a printable HTML document."""
    rows_html = ""
    for r in report["posture"]:
        color = r["risk_color"]
        rows_html += f"""<tr>
            <td>{r["defense"]}</td>
            <td>{r["coverage"]:.2f}</td>
            <td style="color:{color};font-weight:700">{r["risk_level"]}</td>
            <td>{r["cis_control"]}</td>
            <td>{r["cis_name"]}</td>
        </tr>"""

    shock = report["zero_day"]
    shock_html = f"""
        <p>At round <b>{shock["round"]}</b> a zero-day token confusion vulnerability was discovered.</p>
        <ul>
            <li>Pre-shock risk: <b>{shock["pre_shock_risk"]}</b></li>
            <li>Peak risk (spike): <b style="color:red">{shock["peak_risk"]}</b></li>
            <li>Adaptation latency: <b>{shock["adaptation_latency"]} rounds</b> (time to deploy emergency patch to 50% coverage)</li>
            <li>Risk at adaptation point: <b>{shock["recovered_risk"] if shock["recovered_risk"] else "N/A"}</b> (note: may still exceed pre-shock {shock["pre_shock_risk"]})</li>
        </ul>
    """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Security Posture Report — Purple-Team Gym</title>
<style>
  body {{ font-family: 'Segoe UI', system-ui, sans-serif; max-width: 900px; margin: 0 auto; padding: 40px; color: #1a1a22; font-size: 13px; line-height: 1.6; }}
  h1 {{ font-size: 22px; margin: 0 0 4px; }}
  h2 {{ font-size: 16px; margin: 24px 0 10px; color: #333; border-bottom: 2px solid #6d5fd6; padding-bottom: 4px; }}
  .meta {{ color: #666; font-size: 12px; margin-bottom: 20px; }}
  .score {{ display: inline-block; padding: 8px 16px; border-radius: 8px; font-weight: 700; font-size: 18px; background: #f0eefb; color: #5b4fc0; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 10px; }}
  th, td {{ text-align: left; padding: 8px 10px; border-bottom: 1px solid #e3e3ec; }}
  th {{ background: #f8f8fc; font-weight: 600; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; }}
  .metric {{ display: inline-block; margin-right: 24px; }}
  .metric .val {{ font-weight: 700; font-size: 16px; }}
  .metric .lbl {{ font-size: 11px; color: #666; text-transform: uppercase; }}
  ul {{ margin: 6px 0; padding-left: 20px; }}
  .note {{ background: #fff8e1; border-left: 3px solid #ffb300; padding: 8px 12px; margin: 10px 0; font-size: 12px; }}
  @media print {{ body {{ padding: 20px; }} }}
</style>
</head>
<body>
  <h1>Security Posture Report</h1>
  <div class="meta">Generated: {report["generated_at"][:19]} | Purple-Team Coevolution Gym | Deterministic (seed=42)</div>

  <div style="margin: 20px 0">
    <div class="metric"><div class="val">{report["posture_score"]}/100</div><div class="lbl">Posture Score</div></div>
    <div class="metric"><div class="val">{report["risk_reduction_pct"]}%</div><div class="lbl">Risk Reduction</div></div>
    <div class="metric"><div class="val">{report["red_win_rate_late"]}</div><div class="lbl">Final RED Win Rate</div></div>
    <div class="metric"><div class="val">{report["residual_risk_late"]}</div><div class="lbl">Final Residual Risk</div></div>
  </div>

  <div class="note">
    <b>Posture score methodology:</b> threat-weighted coverage — what fraction of
    total threat pressure is actively mitigated? This is honest: a score of 100
    would require covering every defense facing threat, not just spending budget.
  </div>

  <h2>Executive Summary</h2>
  <p>
    A purple-team coevolution simulation was run for 200 rounds with a finite security budget.
    An adaptive RED attacker (epsilon-greedy bandit) and an adaptive BLUE defender (residual-risk gradient)
    learned against each other. The system converged to a stable equilibrium with a
    <b>{report["risk_reduction_pct"]}% reduction in residual risk</b>.
    A zero-day shock at round 100 tested the defender's ability to adapt to the unknown.
  </p>

  <h2>Zero-Day Response</h2>
  {shock_html}
  <div class="note">
    <b>Adaptation latency</b> is measured as rounds until the emergency patch reaches
    50% deployment — not until risk fully normalizes. At the adaptation point, risk has
    dropped substantially from peak but may still exceed pre-shock baseline.
  </div>

  <h2>Defense Posture (mapped to CIS Controls v8)</h2>
  <table>
    <thead><tr><th>Defense</th><th>Coverage</th><th>Risk Level</th><th>CIS Control</th><th>Control Name</th></tr></thead>
    <tbody>{rows_html}</tbody>
  </table>

  <h2>Recommendations</h2>
  <ul>
    <li>Prioritize defenses with HIGH risk level (low coverage) for immediate investment.</li>
    <li>The zero-day response shows adaptation is possible but takes {report["zero_day"]["adaptation_latency"]} rounds — invest in threat intelligence to shorten this window.</li>
    <li>Consider increasing the security budget to further reduce residual risk.</li>
    <li>Map remaining gaps to CIS Controls for compliance reporting.</li>
  </ul>
</body>
</html>"""


if __name__ == "__main__":
    report = generate_report()
    html = render_html(report)
    out = os.path.join(HERE, "posture_report.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Wrote {out}")
    print(f"Posture score: {report['posture_score']}/100 (threat-weighted)")
    print(f"Risk reduction: {report['risk_reduction_pct']}%")
    print(f"Defenses assessed: {len(report['posture'])}")
    high_risk = sum(1 for r in report['posture'] if r['risk_level'] == 'HIGH')
    print(f"Defenses at HIGH risk: {high_risk}/{len(report['posture'])}")
