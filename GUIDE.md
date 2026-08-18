# GUIDE — 05 Purple-Team Coevolution Gym (step by step, code by code)

The piece that will make people stop scrolling your portfolio. Read it like a
paper: catalog → agents → round loop → convergence → dashboard. Every function
is explained. No external libraries — pure Python stdlib + a hand-rolled
canvas dashboard.

────────────────────────────────────────────────────────────────────────────
PART A — techniques.py (the rules of the game)
────────────────────────────────────────────────────────────────────────────
Two lists:

  TECHNIQUES: each attack class has
    - base: success probability with NO defense (0..1)
    - mit_by: the single defense id that neutralizes it
    The first three are the E-Tafakna JWT bug class, so the gym literally
    teaches a defender to close the hole you found.

  DEFENSES: each control has a `cost` and an id. Multiple techniques can be
    mitigated by the same defense.

  success_prob(tid, coverage): the core physics. With coverage c for the
    mitigating defense, success = base * (1 - MITIG_EFF * c), clamped to
    [0.01, 0.99]. So a fully-deployed (c=1) defense cuts success by 90%.

────────────────────────────────────────────────────────────────────────────
PART B — gym.py (the agents + loop)
────────────────────────────────────────────────────────────────────────────
Attacker (RED) — a bandit learner:
  - q[technique]: value estimate of how useful attacking that technique is.
  - choose(): with probability EPSILON explore randomly; otherwise exploit the
    technique with the highest q (greedy). This is epsilon-greedy, the canonical
    bandit algorithm — simple but it DOES learn.
  - observe(aid, success): reward = 1 if success else 0; q moves toward reward
    by LR (Q-learning style update). A win raises q, a loss lowers it. So when
    BLUE patches a technique, RED's q for it falls and it shifts to another.
  - threat_profile(): softmax of q -> how much pressure each technique is under.

Defender (BLUE) — a constrained optimizer:
  - coverage[defense]: 0..1 how much that control is deployed. Budget = 3.0
    total points. It CANNOT cover everything -> realistic trade-offs.
  - allocate(threat): each round, grow the defense whose mitigated techniques
    carry the most threat pressure (residual-risk gradient). If budget not yet
    saturated, add coverage; if saturated, reallocate from the least-beneficial
    defense. Then _enforce_budget() scales down if it ever drifts over budget.
  - residual_risk(threat): weighted expected red success after coverage. This
    is what we watch converge.

run_simulation(rounds, seed):
  For each round:
    1) blue.allocate(red.threat_profile())  (except round 0, starts empty)
    2) red.choose() -> attack; success ~ Bernoulli(success_prob)
    3) red.observe(); record metrics (win-rate window, coverage total, risk)
  Returns history (one snapshot per round) + final agents.
  Deterministic: random.Random(seed) -> same result every run (proven by test).

summarize(history): compares early vs late windows to show convergence.

────────────────────────────────────────────────────────────────────────────
PART C — tests/test_gym.py (proof it's real, not faked)
────────────────────────────────────────────────────────────────────────────
7 tests, all must pass:
  - residual risk decreases over time        (blue learns)
  - red win-rate decreases over time          (defense works)
  - blue fully spends its budget              (rational allocation)
  - same seed -> identical result             (deterministic, reproducible)
  - observe() raises q on a win               (bandit mechanic correct)
  - choose() returns a valid technique
  - defender prioritizes the threatened defense (jwt_strict_verify when JWT
    techniques are pressured)
Run: python -m unittest tests.test_gym -v

────────────────────────────────────────────────────────────────────────────
PART D — build_dashboard.py + dashboard.html (the wow factor)
────────────────────────────────────────────────────────────────────────────
build_dashboard.py runs the sim, then injects the JSON into an HTML template
with inline <script> that draws everything on <canvas> — NO Chart.js, NO CDN,
works offline from file://. The template is a string with a /*__DATA__*/ marker
replaced by json.dumps(data). Panels:
  - RED win-rate + residual risk over 200 rounds (line chart) WITH a ⚡zero-day
    shock marker at round 100
  - BLUE coverage deployed vs budget (line)
  - Convergence verdict + metrics (auto-colored)
  - ⚡ Zero-day shock response card (spike → peak → adaptation latency → recovery)
  - Final posture: BLUE coverage vs RED threat per control/technique (bars)
  - Technique risk-reduction table, E-Tafakna JWT rows flagged with ★
Open dashboard.html in any browser. It is ~135 KB and self-contained.

────────────────────────────────────────────────────────────────────────────
PART D2 — The zero-day shock (the part that makes people stop scrolling)
────────────────────────────────────────────────────────────────────────────
techniques.py defines a HIDDEN technique `zeroday` ("Zero-day token confusion",
base success 0.98) mitigated only by a HIDDEN defense `zeroday_patch`. They are
marked `hidden: True` so they are excluded until revealed.

gym.py run_simulation():
  - RED starts knowing only non-hidden techniques (Attacker.active).
  - At r == SHOCK_ROUND (100): red.reveal_zeroday() adds the technique with a
    novelty-boosted Q (ADAPT_NOVELTY) so RED immediately starts probing it; and
    blue.patch_available = True so the emergency defense becomes deployable.
  - Defender.allocate() skips hidden defenses until patch_available, mirroring
    real life: you can't deploy a fix that hasn't been written.
  - Bookkeeping records pre_shock_risk, peak_risk (the spike), and
    adaptation_latency (rounds until BLUE deploys the patch to >=0.5).

Verified emergent arc (seed 42): risk 0.245 → spikes to 0.440 at the shock →
BLUE deploys the patch → recovers; adaptation latency ~73 rounds. The 14 tests
in test_gym.py assert the spike, the eventual patch deployment, a finite
adaptation latency, and that RED never uses the zero-day before it is revealed.

────────────────────────────────────────────────────────────────────────────
PART E — How to make it even MORE amazing (stretch ideas, still open)
────────────────────────────────────────────────────────────────────────────
1) Make BLUE a bandit too (choose which defense to invest next via UCB) instead
   of the residual-risk gradient — a more "agentic" defender.
2) (DONE) Zero-day shock at round 100 — already implemented & tested. Keep it.
3) Multi-defender / multi-attacker populations (真正的 coevolution, not 1v1).
4) Export the curve as a GIF/MP4 of the arms race animating round by round.
5) Tie BLUE coverage to real CIS controls and produce a "security posture"
   report you could hand a CISO.

────────────────────────────────────────────────────────────────────────────
STEP-BY-STEP TO RUN & SCREENSHOT FOR YOUR README
────────────────────────────────────────────────────────────────────────────
  cd 05-purple-team-gym
  python gym.py                      # see metrics in terminal
  python -m unittest tests.test_gym -v
  python build_dashboard.py          # creates dashboard.html
  # open dashboard.html, screenshot the arms-race charts -> put in README
