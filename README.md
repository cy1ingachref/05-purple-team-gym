# Purple-Team Coevolution Gym

[![CI](https://github.com/cy1ingachref/05-purple-team-gym/actions/workflows/ci.yml/badge.svg)](https://github.com/cy1ingachref/05-purple-team-gym/actions/workflows/ci.yml)

A reproducible purple-team simulation where an adaptive RED attacker and an adaptive BLUE defender **coevolve** over 200 rounds — learning against each other until they reach a measurable equilibrium.

> **Why this exists.** Most security demos are one-shot: "here is a tool that finds a bug." This is a *living* system where two autonomous agents adapt to each other in real time.

1. **RED** is a learning attacker — an epsilon-greedy bandit that keeps value estimates Q(technique) and concentrates fire on whatever is currently most effective. When BLUE patches a hole, RED's Q for it falls and RED pivots.

2. **BLUE** is an adaptive defender — given a fixed security budget (3.0 points), it raises coverage of the defenses that mitigate the techniques RED is actually using (residual-risk gradient). It cannot cover everything — realistic trade-offs.

3. **They coevolve.** RED adapts to BLUE's coverage, BLUE adapts to RED's pressure. The result: residual risk **decreases** over time and plateaus at a stable equilibrium. Both agents are learning. This is proven by tests, not scripted.

4. **Zero-day shock.** At round 100, a hidden zero-day (base success 0.98) is revealed to RED, and the emergency patch becomes available to BLUE. Risk spikes. BLUE deploys the patch and recovers. The adaptation latency (~73 rounds) is measured and tested.

> **On "adaptation latency":** this is defined as rounds until BLUE deploys the emergency patch to 50% coverage, NOT until risk fully normalizes. At the adaptation point, risk has dropped substantially from peak but may still exceed the pre-shock baseline. This is internally consistent — we measure patch deployment speed, not full risk recovery, because risk is a continuous signal with no single "back to normal" threshold.

## What makes it different

| Feature | Why it matters |
|---------|---------------|
| **Epsilon-greedy bandit RED** | Real RL, not scripted. Proven to learn by tests. |
| **Budget-constrained BLUE** | Forces realistic trade-offs. Proven to fully spend budget by tests. |
| **Zero-day shock + recovery** | Tests adaptation to the unknown. Proven by tests. |
| **Deterministic (seed=42)** | Same result every run. Reproducible for demos. |
| **Zero dependencies** | Pure Python stdlib. Runs anywhere. |
| **Offline dashboard** | Self-contained HTML, no CDN, opens from `file://`. |
| **Animated replay** | Watch the arms race unfold round-by-round. |
| **CIS Controls mapping** | Maps converged posture to CIS v8 controls for governance. |
| **CISO posture report** | Printable HTML report with risk levels and recommendations. |

## connection

The first three techniques in the catalog are the **exact bug class found during an authorized pentest** (legal-tech SaaS):

- `jwt_none` — alg=none forgery (base 0.95)
- `jwt_weak_secret` — weak HMAC secret brute (base 0.85)
- `jwt_strcmp` — verified by string equality (base 0.90)

The gym literally teaches a defender to close the hole found in a real engagement. This grounds the simulation in reality, not theory.

## Run it

```bash
# Run the simulation (prints convergence metrics)
python gym.py

# Run the test suite (19 tests, all must pass)
python -m unittest tests.test_gym -v

# Build the dashboard (opens in any browser, no server needed)
python build_dashboard.py
# -> dashboard.html (self-contained, ~150 KB)

# Generate the CISO posture report
python ciso_report.py
# -> posture_report.html (printable, CIS-mapped)
```

## What the tests prove

```
test_residual_risk_decreases          — BLUE learns to reduce risk over time
test_red_win_rate_decreases           — defense lowers attacker success
test_blue_uses_full_budget            — rational allocation (no waste)
test_same_seed_same_result            — deterministic, reproducible
test_zeroday_causes_risk_spike        — zero-day creates measurable impact
test_blue_deploys_emergency_patch     — defender adapts to unknown
test_adaptation_latency_is_finite     — recovery happens within bounded rounds
test_zeroday_unknown_before_shock     — RED can't use what it doesn't know
test_defender_prioritizes_threatened_defense — gradient works
test_posture_score_not_trivially_100  — score reflects coverage gaps, not budget
test_posture_score_threat_weighted    — threat-weighted methodology
test_high_risk_defenses_present      — finite budget → real gaps visible
test_cis_mapping_complete             — every defense maps to a CIS control
test_html_report_renders             — report renders without errors
```

## Dashboard preview

The dashboard shows:
- RED win-rate + residual risk over 200 rounds (with zero-day shock marker)
- BLUE coverage deployed vs budget
- Convergence verdict (auto-colored)
- Zero-day shock response (spike → peak → adaptation → recovery)
- Final posture: BLUE coverage vs RED threat per technique
- Technique risk-reduction table (JWT bugs flagged with ★)
- **Animated replay** — watch the arms race unfold round-by-round

## CISO posture report

The report maps each defense to a CIS Control v8 ID and produces:
- Overall posture score (0-100) — **threat-weighted**: what fraction of total threat pressure is actively mitigated? This is honest — a score of 100 would require covering every defense facing threat, not just spending budget. With the default seed the score is ~54/100 (3 defenses cover ~50% of threat pressure).
- Risk reduction percentage
- Per-defense risk level (LOW/MEDIUM/HIGH)
- CIS control mapping
- Executive summary and recommendations

> **Why threat-weighted?** The alternative — `sum(coverage)/budget` — would always read ~100/100 because BLUE always spends its full budget (proven by `test_blue_uses_full_budget`). A CISO would immediately catch the contradiction: "100/100 posture but 5/8 defenses are HIGH risk?" This fix makes the score reflect real defensive posture, not just budget utilization.

## Files

| File | Purpose |
|------|---------|
| `gym.py` | Coevolution engine (Attacker + Defender agents + round loop) |
| `techniques.py` | Technique and defense catalog (includes JWT bugs) |
| `build_dashboard.py` | Generates the offline HTML dashboard |
| `ciso_report.py` | Generates the CIS-mapped posture report |
| `tests/test_gym.py` | 14 tests proving learning, convergence, and adaptation |
| `GUIDE.md` | Step-by-step walkthrough of every component |

## Notes

- Zero dependencies (pure Python stdlib)
- Deterministic by seed (reproducible for demos and interviews)
- The dashboard is self-contained (no CDN, no network)
- The posture report is printable (File → Print)
