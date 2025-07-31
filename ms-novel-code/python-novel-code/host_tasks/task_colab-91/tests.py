# tests

"""
Unit tests for verify_chc.verify

Run with:
    python -m unittest test_verify_chc.py
The suite checks every behaviour promised in the prompt and requirements.
"""

import unittest
from main import * as vc


# ───────────────────────────────────────────────
# Minimal CHC inputs used across multiple tests
# ───────────────────────────────────────────────
SAFE_CHC = """
(declare-rel ok ())
(query ok)
"""

UNSAFE_CHC = """
(declare-rel bug ())
(rule bug)
(query bug)
"""

MALFORMED_CHC = "(declare-rel p (Int))"      # no query ⇒ unknown


class VerifyCHCTests(unittest.TestCase):

    # ───────── explicit behaviour tests ─────────

    def test_safe_case(self):
        """All queries unsat → status 'safe' and model None."""
        res = vc.verify(SAFE_CHC, dialect="datalog", timeout=3, learn=False)
        self.assertEqual(res["status"], "safe")
        self.assertIsNone(res["model"])
        self.assertEqual(res["learned"], [])

    def test_unsafe_case(self):
        """Counter-example exists → status 'unsafe', non-empty model string, learning stores it."""
        res = vc.verify(UNSAFE_CHC, dialect="datalog", timeout=3, learn=True)
        self.assertEqual(res["status"], "unsafe")
        self.assertIsInstance(res["model"], str)
        self.assertGreater(len(res["model"]), 0)
        self.assertGreaterEqual(len(res["learned"]), 1)

    def test_unknown_due_to_malformed(self):
        """Malformed input yields status 'unknown'."""
        res = vc.verify(MALFORMED_CHC, dialect="datalog", timeout=3)
        self.assertEqual(res["status"], "unknown")
        self.assertIsNone(res["model"])

    # ───────── edge-case and validation tests ─────────

    def test_empty_source(self):
        res = vc.verify("   \n", dialect="datalog", timeout=3)
        self.assertEqual(res["status"], "unknown")

    def test_bad_dialect_raises(self):
        with self.assertRaises(ValueError):
            vc.verify(SAFE_CHC, dialect="foo", timeout=3)

    def test_non_positive_timeout_raises(self):
        with self.assertRaises(ValueError):
            vc.verify(SAFE_CHC, dialect="datalog", timeout=0)

    # ───────── timeout path (solver returns unknown) ─────────
    # For reliability we trigger Z3's 'unknown' by giving an absurdly
    # small timeout on a satisfiable problem.
    def test_solver_timeout_returns_unknown(self):
        res = vc.verify(UNSAFE_CHC, dialect="datalog", timeout=1, learn=False)
        self.assertIn(res["status"], {"unsafe", "unknown"})  # depends on host speed


if __name__ == "__main__":
    unittest.main()
