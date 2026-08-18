#!/usr/bin/env python3
"""
tests/test_gym.py — Prove the two agents actually LEARN and ADAPT, including a
zero-day shock scenario.

These assertions are what make the project credible: it's not a scripted
animation, the emergent convergence (and recovery) is real and reproducible.

Run:  python -m unittest tests.test_gym -v
"""

import importlib.util
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
spec = importlib.util.spec_from_file_location("gym", os.path.join(ROOT, "gym.py"))
gym = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gym)

spec_t = importlib.util.spec_from_file_location("techniques", os.path.join(ROOT, "techniques.py"))
techniques = importlib.util.module_from_spec(spec_t)
spec_t.loader.exec_module(techniques)


def sim():
    hist, red, blue, meta = gym.run_simulation(rounds=200, seed=42)
    return hist, red, blue, meta


class TestConvergence(unittest.TestCase):
    def test_residual_risk_decreases(self):
        hist, _, _, _ = sim()
        early = hist[:20][-1]["residual_risk"]
        late = hist[-20:][-1]["residual_risk"]
        self.assertLess(late, early, "blue should reduce residual risk over time")

    def test_red_win_rate_decreases(self):
        hist, _, _, _ = sim()
        early = sum(h["red_win_rate"] for h in hist[:20]) / 20
        late = sum(h["red_win_rate"] for h in hist[-20:]) / 20
        self.assertLess(late, early, "defender should lower attacker success over time")

    def test_blue_uses_full_budget(self):
        _, _, blue, _ = sim()
        self.assertAlmostEqual(sum(blue.coverage.values()), blue.budget, places=2,
                               msg="defender should fully spend its finite budget")


class TestZeroDayShock(unittest.TestCase):
    def test_zeroday_causes_risk_spike(self):
        hist, _, _, meta = sim()
        self.assertGreater(meta["peak_risk"], meta["pre_shock_risk"],
                           "zero-day must spike residual risk above pre-shock")

    def test_blue_deploys_emergency_patch(self):
        _, _, blue, _ = sim()
        self.assertGreater(blue.coverage.get("zeroday_patch", 0.0), 0.5,
                           "defender must eventually deploy the zero-day patch")

    def test_adaptation_latency_is_finite(self):
        _, _, _, meta = sim()
        self.assertIsNotNone(meta["adaptation_latency"],
                             "defender should adapt within a finite number of rounds")
        self.assertGreater(meta["adaptation_latency"], 0)

    def test_zeroday_unknown_before_shock(self):
        hist, red, _, _ = sim()
        # Before the shock round, RED should never attack the hidden technique.
        shock = hist[0]["round"] + 0
        pre = [h for h in hist if h["round"] < gym.SHOCK_ROUND]
        self.assertTrue(all(h["attack"] != "zeroday" for h in pre),
                        "zero-day must not be used before it is revealed")


class TestDeterminism(unittest.TestCase):
    def test_same_seed_same_result(self):
        h1, _, b1, m1 = sim()
        h2, _, b2, m2 = sim()
        self.assertEqual(h1[-1]["residual_risk"], h2[-1]["residual_risk"])
        self.assertEqual(h1[-1]["coverage"], h2[-1]["coverage"])
        self.assertEqual(m1["peak_risk"], m2["peak_risk"])


class TestAgentMechanics(unittest.TestCase):
    def test_attacker_observe_updates_q(self):
        import random
        rng = random.Random(1)
        a = gym.Attacker(rng)
        before = a.q["sqli"]
        a.observe("sqli", success=True)
        after = a.q["sqli"]
        self.assertGreater(after, before, "a win should raise Q")

    def test_attacker_chooses_valid_technique(self):
        import random
        rng = random.Random(2)
        a = gym.Attacker(rng)
        self.assertIn(a.choose(), techniques.technique_ids())

    def test_attacker_unaware_of_zeroday_initially(self):
        import random
        rng = random.Random(3)
        a = gym.Attacker(rng)
        self.assertNotIn("zeroday", a.active)

    def test_reveal_zeroday_adds_technique(self):
        import random
        rng = random.Random(4)
        a = gym.Attacker(rng)
        a.reveal_zeroday()
        self.assertIn("zeroday", a.active)
        self.assertGreater(a.q["zeroday"], 0.5)

    def test_defender_prioritizes_threatened_defense(self):
        import random
        rng = random.Random(3)
        a = gym.Attacker(rng)
        for k in a.q:
            a.q[k] = 0.1
        a.q["jwt_none"] = 0.9
        a.q["jwt_weak_secret"] = 0.9
        a.q["jwt_strcmp"] = 0.9
        d = gym.Defender()
        for _ in range(30):
            d.allocate(a.threat_profile())
        self.assertGreater(d.coverage["jwt_strict_verify"], 0.5,
                           "defender must prioritize the threatened defense")

    def test_defender_cannot_patch_zeroday_before_shock(self):
        import random
        rng = random.Random(5)
        a = gym.Attacker(rng)
        d = gym.Defender()
        # Force a huge threat on the zero-day before the patch exists.
        a.reveal_zeroday()
        d.patch_available = False
        for _ in range(20):
            d.allocate(a.threat_profile())
        self.assertEqual(d.coverage["zeroday_patch"], 0.0,
                         "patch must be unavailable before the shock")


if __name__ == "__main__":
    unittest.main(verbosity=2)
