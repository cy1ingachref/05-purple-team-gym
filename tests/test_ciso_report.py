#!/usr/bin/env python3
"""
tests/test_ciso_report.py — Verify the CISO posture report generator.
"""

import importlib.util
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
spec = importlib.util.spec_from_file_location("ciso_report", os.path.join(ROOT, "ciso_report.py"))
ciso_report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ciso_report)


class TestCISORepost(unittest.TestCase):
    def test_report_generates(self):
        report = ciso_report.generate_report()
        self.assertIn("posture_score", report)
        self.assertIn("risk_reduction_pct", report)
        self.assertIn("posture", report)
        self.assertGreater(len(report["posture"]), 0)

    def test_posture_score_bounded(self):
        report = ciso_report.generate_report()
        self.assertGreaterEqual(report["posture_score"], 0)
        self.assertLessEqual(report["posture_score"], 100)

    def test_all_defenses_mapped(self):
        report = ciso_report.generate_report()
        for row in report["posture"]:
            self.assertIn("cis_control", row)
            self.assertIn("risk_level", row)
            self.assertIn(row["risk_level"], ["LOW", "MEDIUM", "HIGH"])

    def test_html_renders(self):
        report = ciso_report.generate_report()
        html = ciso_report.render_html(report)
        self.assertIn("<html", html.lower())
        self.assertIn("posture score", html.lower())
        self.assertIn("cis controls", html.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
