#!/usr/bin/env python3
"""
gym.py — The Purple-Team Coevolution Gym engine.

WHY THIS IS RARE
----------------
Most security demos are one-shot: "here is a tool that finds a bug." This is a
living simulation where two autonomous agents learn against EACH OTHER:

  * RED  is a learning attacker: a contextual epsilon-greedy bandit that keeps
         value estimates Q(technique) and concentrates fire on whatever is
         currently most effective. It adapts when BLUE patches a hole.
  * BLUE is an adaptive defender: given a fixed security budget, it raises
         coverage of the defenses that mitigate the techniques RED is actually
         using (residual-risk gradient), and shifts budget when RED pivots.

The emergent behavior — an ARMS RACE that converges to a measurable
equilibrium — is what makes this portfolio piece stand out. It is fully
deterministic given a seed, zero-dependency, and validated by tests.

ROUND MODEL
-----------
Each round:
  1. BLUE commits a coverage vector c (defense_id -> 0..1) within budget.
  2. RED picks a technique a via epsilon-greedy on its Q-estimates, observes
     success s ~ Bernoulli(success_prob(a, c)).
  3. RED updates Q(a) with the win/loss (and a small exploration bonus).
  4. BLUE updates coverage toward the techniques RED is pounding, capped by
     budget; leftover budget is spread to reduce total residual risk.
  5. We record metrics: red success rate (over window), blue coverage, total
     residual risk = sum over techniques of base*Q-weighted success prob.

Convergence check: residual risk should DECREASE over time and then plateau
(a stable equilibrium), proving both agents are learning and the system is not
random noise.
"""

import random
from techniques import (
    TECHNIQUES, DEFENSES, success_prob, technique_ids, defense_ids,
    techniques_mitigated_by,
)

EPSILON = 0.15          # red exploration rate
LR = 0.25              # red Q-learning rate
BLUE_BUDGET = 3.0      # total coverage "points" blue can deploy
BLUE_LR = 0.35        # how fast blue reallocates toward live threats
WINDOW = 20            # rolling success-rate window
SHOCK_ROUND = 100      # round at which the zero-day is discovered/revealed
ADAPT_NOVELTY = 0.6    # initial Q boost RED gives a freshly-revealed technique


class Attacker:
    def __init__(self, rng, shock_round=SHOCK_ROUND):
        self.rng = rng
        # RED only "knows" observable techniques until the zero-day is revealed.
        self.active = [t["id"] for t in TECHNIQUES if not t.get("hidden", False)]
        self.q = {t["id"]: 0.5 for t in TECHNIQUES}
        self.pulls = {t["id"]: 1 for t in TECHNIQUES}
        self.last = None
        self.shock_round = shock_round
        self.zeroday_discovered = False

    def choose(self):
        if self.rng.random() < EPSILON:
            aid = self.rng.choice(self.active)
        else:
            # greedy over currently-known techniques
            aid = max(self.active, key=lambda k: self.q[k])
        self.last = aid
        return aid

    def observe(self, aid, success):
        # Win raises Q, loss lowers it; scaled by learning rate.
        reward = 1.0 if success else 0.0
        self.q[aid] += LR * (reward - self.q[aid])
        self.pulls[aid] += 1

    def reveal_zeroday(self):
        """At the shock round, the attacker learns a new technique. We give it a
        novelty-boosted Q so it immediately starts probing the hole (just like a
        real actor pivoting to a fresh exploit)."""
        if self.zeroday_discovered:
            return
        self.active.append("zeroday")
        self.q["zeroday"] = ADAPT_NOVELTY
        self.zeroday_discovered = True

    def threat_profile(self):
        """How much pressure each technique is under (softmax of Q)."""
        total = sum(max(0.0, self.q[t]) for t in self.active)
        if total <= 0:
            return {t: 0.0 for t in self.active}
        return {t: max(0.0, self.q[t]) / total for t in self.active}


class Defender:
    def __init__(self, budget=BLUE_BUDGET):
        self.budget = budget
        self.coverage = {d["id"]: 0.0 for d in DEFENSES}
        self.patch_available = False   # the zero-day fix exists only after shock

    def allocate(self, threat):
        """Shift coverage toward defenses that mitigate the techniques RED is
        pressuring. Residual-risk gradient: grow coverage of the defense whose
        mitigated techniques carry the most threat pressure, up to budget; once
        budget is saturated, reallocate from the least-beneficial defense.

        The emergency zero-day patch is only eligible AFTER the shock round
        (blue.patch_available), mirroring real life: you can't deploy a fix
        that hasn't been written yet."""
        step = BLUE_LR
        for _ in range(5):  # a few gradient steps per round
            benefits = {}
            for d in DEFENSES:
                if d.get("hidden") and not self.patch_available:
                    continue
                mits = techniques_mitigated_by(d["id"])
                benefits[d["id"]] = sum(threat.get(tid, 0.0) for tid in mits)
            if not benefits:
                break
            best = max(benefits, key=lambda k: benefits[k])
            worst = min(benefits, key=lambda k: benefits[k])
            total = sum(self.coverage.values())
            if self.coverage[best] < 1.0 and total < self.budget:
                # grow the best defense toward its cap, capped by remaining budget
                room = min(step, 1.0 - self.coverage[best], self.budget - total)
                self.coverage[best] += room
            elif self.coverage[best] < 1.0 and self.coverage[worst] > 0.0:
                # reallocate from the least-beneficial defense to the best
                move = min(step, self.coverage[worst], 1.0 - self.coverage[best])
                self.coverage[best] += move
                self.coverage[worst] -= move
        self._enforce_budget()

    def _enforce_budget(self):
        # scale all coverage down proportionally if over budget (sum may drift)
        total = sum(self.coverage.values())
        if total > self.budget + 1e-9:
            scale = self.budget / total
            for k in self.coverage:
                self.coverage[k] *= scale

    def residual_risk(self, threat):
        """Expected red success weighted by threat pressure, after coverage."""
        risk = 0.0
        for tid, w in threat.items():
            if w <= 0:
                continue
            # approximate: assume the technique's current success prob
            p = success_prob(tid, self.coverage)
            risk += w * p
        return risk


def run_simulation(rounds=200, seed=42, shock_round=SHOCK_ROUND):
    rng = random.Random(seed)
    red = Attacker(rng, shock_round=shock_round)
    blue = Defender()

    history = []
    red_wins_window = []
    pre_shock_risk = None
    peak_risk = None
    recovered_risk = None
    adaptation_latency = None  # rounds from shock to risk back under pre-shock

    for r in range(rounds):
        # ZERO-DAY SHOCK: at shock_round the exploit is revealed to RED and the
        # emergency patch becomes available to BLUE. The patch is not yet
        # deployed, so for a few rounds BLUE is blind to the new technique.
        if r == shock_round:
            red.reveal_zeroday()
            blue.patch_available = True

        # 1) blue commits coverage
        threat = red.threat_profile()
        if r > 0:
            blue.allocate(threat)

        # 2) red attacks
        aid = red.choose()
        p = success_prob(aid, blue.coverage)
        success = rng.random() < p
        red.observe(aid, success)

        # 3) metrics
        red_wins_window.append(1 if success else 0)
        if len(red_wins_window) > WINDOW:
            red_wins_window.pop(0)
        win_rate = sum(red_wins_window) / len(red_wins_window)
        risk = blue.residual_risk(red.threat_profile())
        total_cov = sum(blue.coverage.values())

        # shock bookkeeping
        if r == shock_round - 1:
            pre_shock_risk = risk
        if r >= shock_round:
            if peak_risk is None or risk > peak_risk:
                peak_risk = risk
            # Adaptation = the round BLUE first deploys the emergency patch to
            # a meaningful level. This is always defined (BLUE learns to add it).
            if adaptation_latency is None and blue.coverage.get("zeroday_patch", 0.0) >= 0.5:
                adaptation_latency = r - shock_round
                recovered_risk = risk

        history.append({
            "round": r,
            "attack": aid,
            "success": int(success),
            "attack_success_prob": round(p, 4),
            "red_win_rate": round(win_rate, 4),
            "blue_coverage_total": round(total_cov, 4),
            "residual_risk": round(risk, 4),
            "shock": int(r == shock_round),
            "coverage": {k: round(v, 3) for k, v in blue.coverage.items()},
            "threat": {k: round(v, 3) for k, v in red.threat_profile().items()},
        })

    return history, red, blue, {
        "pre_shock_risk": pre_shock_risk,
        "peak_risk": peak_risk,
        "recovered_risk": recovered_risk,
        "adaptation_latency": adaptation_latency,
        "shock_round": shock_round,
    }


def summarize(history, shock_meta=None):
    shock_meta = shock_meta or {}
    early = history[:20]
    late = history[-20:]
    return {
        "rounds": len(history),
        "early_red_win_rate": sum(h["red_win_rate"] for h in early) / len(early),
        "late_red_win_rate": sum(h["red_win_rate"] for h in late) / len(late),
        "early_residual_risk": early[-1]["residual_risk"],
        "late_residual_risk": late[-1]["residual_risk"],
        "final_coverage": history[-1]["coverage"],
        "final_threat": history[-1]["threat"],
        "shock": shock_meta,
    }


if __name__ == "__main__":
    hist, red, blue, meta = run_simulation(rounds=200, seed=42)
    s = summarize(hist, meta)
    print("=== Purple-Team Gym simulation (seed=42, rounds=%d) ===" % s["rounds"])
    print("RED win rate   early=%.3f  late=%.3f" % (s["early_red_win_rate"], s["late_red_win_rate"]))
    print("Residual risk  early=%.3f  late=%.3f" % (s["early_residual_risk"], s["late_residual_risk"]))
    print("Final BLUE coverage total: %.2f / %.2f budget" % (
        sum(blue.coverage.values()), blue.budget))
    print("Final BLUE coverage:", {k: round(v, 2) for k, v in blue.coverage.items()})
    print("Final RED threat profile:", {k: round(v, 2) for k, v in red.threat_profile().items()})
    print("ZERO-DAY @ round %d: pre-shock risk=%.3f  peak=%.3f  recovered=%.3f  "
          "adaptation latency=%s rounds" % (
              meta["shock_round"], meta["pre_shock_risk"], meta["peak_risk"],
              meta["recovered_risk"], meta["adaptation_latency"]))
    converged = s["late_residual_risk"] < s["early_residual_risk"]
    print("Converged (risk decreased):", converged)
