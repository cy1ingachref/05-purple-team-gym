# 05 — Purple-Team Coevolution Gym

A reproducible purple-team simulation where an adaptive RED attacker and an adaptive BLUE defender coevolve over multiple rounds. The project emphasizes measurable learning, deterministic reproducibility, and an offline dashboard for visualization.

Why this project matters

- Demonstrates advanced modeling of attacker/defender dynamics and the ability to measure learning and recovery from novel threats.
- Provides a tested, deterministic simulation with a self-contained dashboard suitable for demos and technical interviews.

Highlights

- Learning RED attacker (epsilon-greedy bandit)
- Budget-constrained BLUE defender that reallocates coverage via residual-risk gradients
- A zero-day shock at round 100 to demonstrate recovery and adaptation
- Offline HTML dashboard (no external CDN) visualizing the arms race and metrics

Run

python gym.py                # prints convergence and summary metrics
python -m unittest tests.test_gym -v   # unit tests for learning + zero-day behavior
python build_dashboard.py    # generates dashboard.html (open in a browser)

Files

- `techniques.py` — technique and defense catalog (includes JWT-related techniques)
- `gym.py` — coevolution engine and round model
- `build_dashboard.py` — emits the offline HTML dashboard
- `dashboard.html` — generated visualization (open locally)
- `tests/test_gym.py` — unit tests proving learning, convergence, and determinism
- `GUIDE.md` — walkthrough and extension ideas

Notes

- The project is zero-dependency and deterministic by seed to make results reproducible for demos and interviews.
