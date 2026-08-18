#!/usr/bin/env python3
"""
techniques.py — The technique catalog for the Purple-Team Gym.

This is the "rules of the game." Two agent roles act on this catalog:

  RED (attacker)  picks a TECHNIQUE  (an attack class to attempt)
  BLUE (defender) deploys DEFENSES    (controls that mitigate techniques)

Each technique is mitigated by exactly one primary defense. The success
probability of an attack = base_success * (1 - mitigation_effectiveness),
where mitigation_effectiveness scales with how strongly BLUE has deployed the
mitigating defense.

The first three techniques are the EXACT bug class you found at E-Tafakna
(legal-tech SaaS, authorized pentest): a JWT that could be minted with no
password because the server (a) verified tokens by string equality, (b) used a
guessable HMAC secret, and (c) accepted alg=none. Grounding the gym in a real
finding makes it more than a toy.
"""

# Each technique:
#   id, name, tactic (MITRE-ish), base (success prob with NO defense), mit_by (defense id)
TECHNIQUES = [
    {"id": "jwt_none",        "name": "JWT alg=none forgery",            "tactic": "T1608", "base": 0.95, "mit_by": "jwt_strict_verify"},
    {"id": "jwt_weak_secret", "name": "JWT weak HMAC secret brute",     "tactic": "T1608", "base": 0.85, "mit_by": "jwt_strict_verify"},
    {"id": "jwt_strcmp",      "name": "JWT verified by string equality", "tactic": "T1608", "base": 0.90, "mit_by": "jwt_strict_verify"},
    {"id": "sqli",            "name": "SQL injection",                  "tactic": "T1190", "base": 0.70, "mit_by": "input_validation"},
    {"id": "xss",             "name": "Reflected XSS",                  "tactic": "T1059", "base": 0.65, "mit_by": "input_validation"},
    {"id": "rce_eval",        "name": "RCE via eval()",                 "tactic": "T1059", "base": 0.75, "mit_by": "input_validation"},
    {"id": "path_traversal",  "name": "Path traversal",                 "tactic": "T1190", "base": 0.60, "mit_by": "path_confinement"},
    {"id": "brute_force",     "name": "Credential brute force",         "tactic": "T1110", "base": 0.55, "mit_by": "rate_limit"},
    {"id": "impossible_travel","name": "Impossible-travel abuse",       "tactic": "T1078", "base": 0.50, "mit_by": "geo_velocity"},
    {"id": "ssrf",            "name": "SSRF to metadata",               "tactic": "T1190", "base": 0.45, "mit_by": "ssrf_allowlist"},
    {"id": "priv_esc",        "name": "Privilege escalation",           "tactic": "T1068", "base": 0.40, "mit_by": "least_privilege"},
    # A ZERO-DAY: appears mid-simulation (hidden until the shock round). High
    # base success and mitigated only by a defense BLUE has not deployed yet,
    # so it forces a visible adaptation-latency + re-convergence arc.
    {"id": "zeroday",         "name": "Zero-day token confusion",       "tactic": "T1608", "base": 0.98, "mit_by": "zeroday_patch", "hidden": True},
]

# Each defense mitigates the techniques that list it as `mit_by`.
DEFENSES = [
    {"id": "jwt_strict_verify", "name": "Strict JWT signature verification", "cost": 1.0},
    {"id": "input_validation",  "name": "Input validation / parameterized queries", "cost": 1.0},
    {"id": "path_confinement",  "name": "Filesystem path confinement", "cost": 0.6},
    {"id": "rate_limit",        "name": "Auth rate limiting", "cost": 0.6},
    {"id": "geo_velocity",      "name": "Impossible-travel geo-velocity check", "cost": 0.8},
    {"id": "ssrf_allowlist",    "name": "Egress allowlist", "cost": 0.7},
    {"id": "least_privilege",   "name": "Least-privilege IAM", "cost": 0.9},
    # Defense that only becomes available once the zero-day is discovered (shock
    # round). Before that, BLUE literally cannot defend against it -> forcing the
    # adaptation-latency and re-convergence story.
    {"id": "zeroday_patch",     "name": "Emergency zero-day patch", "cost": 0.9, "hidden": True},
]

# How strongly a fully-deployed defense suppresses its technique (0..1).
MITIG_EFF = 0.9


def tech_by_id(tid):
    for t in TECHNIQUES:
        if t["id"] == tid:
            return t
    raise KeyError(tid)


def defense_ids(include_hidden=False):
    if include_hidden:
        return [d["id"] for d in DEFENSES]
    return [d["id"] for d in DEFENSES if not d.get("hidden", False)]


def technique_ids(include_hidden=False):
    if include_hidden:
        return [t["id"] for t in TECHNIQUES]
    return [t["id"] for t in TECHNIQUES if not t.get("hidden", False)]


def techniques_mitigated_by(did):
    return [t["id"] for t in TECHNIQUES if t["mit_by"] == did]


def success_prob(technique_id, coverage):
    """Probability an attack with `technique_id` succeeds given BLUE coverage
    vector {defense_id: 0..1}. Linearly reduced by the mitigating defense."""
    t = tech_by_id(technique_id)
    m = coverage.get(t["mit_by"], 0.0)
    s = t["base"] * (1.0 - MITIG_EFF * m)
    return max(0.01, min(0.99, s))
