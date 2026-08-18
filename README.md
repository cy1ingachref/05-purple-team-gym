# 05 — Purple-Team Coevolution Gym  ⭐ (the standout piece)

**Why this is the rarest, most impressive thing in the portfolio:**
Most security portfolios show *one* static tool. This shows a **living system**:
two autonomous agents — a learning RED attacker and an adaptive BLUE defender —
that play against each other for 200 rounds and **coevolve into a measurable
equilibrium**. It is:

- **A real zero-day shock scenario.** At round 100 a previously-unknown exploit
  (a "token confusion" zero-day) is revealed to the attacker. Risk spikes, then
  the defender *learns to deploy an emergency patch and re-converges* — you can
  watch the adaptation latency. Not just convergence, but **recovery from an
  unknown threat**.
- **A real simulation, not a scripted animation** — convergence AND recovery are
  emergent and proven by 14 unit tests (residual risk drops; red win-rate drops
  as blue adapts; blue fully spends its finite budget; the zero-day spikes risk
  then is patched within a finite number of rounds; deterministic by seed).
- **Grounded in your real E-Tafakna finding** — the first three techniques are
  the exact JWT bug class you found (alg=none, weak HMAC secret, string-equality
  verification), so the demo literally shows a defense *learning* to close the
  hole you discovered.
- **Zero dependencies, fully offline, deterministic**.
- **Self-contained HTML dashboard** (no CDN, opens from `file://`) visualizing
  the arms race including the zero-day shock marker and a recovery card.

**The "amazing" one-liner for your CV/LinkedIn:**
> "Built a purple-team coevolution gym: a learning attacker (epsilon-greedy
> bandit) and a budget-constrained adaptive defender that converge to a
> measurable security equilibrium over 200 rounds — emergent, tested, and
> visualized in a zero-dependency dashboard. Grounded in a real JWT bug class I
> found during an authorized pentest."

## What each agent is
- **RED (attacker):** contextual epsilon-greedy bandit. Maintains value estimates
  `Q(technique)`, concentrates fire on what currently works, explores 15% of the
  time, and updates `Q` with observed win/loss. When BLUE patches a hole, RED's
  `Q` for that technique drops and it pivots — genuine adaptation.
- **BLUE (defender):** residual-risk gradient allocator under a fixed budget
  (3.0 coverage points). Each round it raises coverage of the defense that
  neutralizes the techniques RED is pressuring most, reallocating from the
  least-useful defense once saturated. It can never block everything — so the
  arms race produces *realistic trade-offs*, not a perfect defense.

## Run it
```
python gym.py                # prints convergence metrics
python -m unittest tests.test_gym -v   # proves the agents learn + zero-day (14 tests)
python build_dashboard.py    # emits dashboard.html (open in a browser)
```

## Files
- `techniques.py` — technique/defense catalog (incl. E-Tafakna JWT bugs)
- `gym.py` — coevolution engine (agents + round model + convergence summary)
- `build_dashboard.py` — emits the offline HTML dashboard from a simulation
- `dashboard.html` — the generated visualization (open it!)
- `tests/test_gym.py` — proves learning/convergence/determinism (7 tests)
- `GUIDE.md` — step-by-step code walkthrough

See `GUIDE.md` for the full code-by-code explanation and how to extend it
(e.g. add techniques, change the budget, make BLUE a bandit too).
