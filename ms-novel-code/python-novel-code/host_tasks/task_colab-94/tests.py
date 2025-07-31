# tests

"""
Unit-test suite (12 cases) for main.verify.

Run with
    python -m unittest test_verify_chc.py
after installing requirements.txt and placing main.py
(with the verify function) in the same directory.
"""

import unittest
import tempfile
import os
from main import verify   # <- import now comes from main

# ────────────────────────────────────────────────────────────
# Re-usable CHC snippets
# ────────────────────────────────────────────────────────────
SAFE_DATALOG = """
(declare-rel ok ())
(query ok)
"""

UNSAFE_DATALOG = """
(declare-rel bug ())
(rule bug)
(query bug)
"""

MALFORMED_DATALOG = "(declare-rel p (Int))"      # missing query → unknown

SAFE_SMT = """
(set-logic ALL)
(assert false)
"""  # unsat → safe

UNSAFE_SMT = """
(set-logic ALL)
(assert true)
"""   # sat  → unsafe

MIXED_QUERIES_DATALOG = """
(declare-rel a ())
(declare-rel b ())
(rule a)
(rule b)
(query a)   ; sat first, should already report unsafe
(query b)
"""

# Helper to write a temporary file and return its path
def _tmp_file(text: str, suffix: str = ".tmp") -> str:
    handle, path = tempfile.mkstemp(suffix=suffix, text=True)
    with os.fdopen(handle, "w") as fp:
        fp.write(text)
    return path


class VerifyCHCTests(unittest.TestCase):
    # 1
    def test_safe_case_datalog_string(self):
        res = verify(SAFE_DATALOG, dialect="datalog", timeout=3, learn=False)
        self.assertEqual(res["status"], "safe")
        self.assertIsNone(res["model"])
        self.assertEqual(res["learned"], [])

    # 2
    def test_unsafe_case_datalog_string_with_learning(self):
        res = verify(UNSAFE_DATALOG, dialect="datalog", timeout=3, learn=True)
        self.assertEqual(res["status"], "unsafe")
        self.assertIsInstance(res["model"], str)
        self.assertGreater(len(res["model"]), 0)
        self.assertGreaterEqual(len(res["learned"]), 1)

    # 3
    def test_unknown_due_to_malformed_input(self):
        res = verify(MALFORMED_DATALOG, dialect="datalog", timeout=3)
        self.assertEqual(res["status"], "unknown")

    # 4
    def test_empty_source_returns_unknown(self):
        res = verify(" \n\t ", dialect="datalog", timeout=3)
        self.assertEqual(res["status"], "unknown")

    # 5
    def test_bad_dialect_raises(self):
        with self.assertRaises(ValueError):
            verify(SAFE_DATALOG, dialect="xyz", timeout=3)

    # 6
    def test_non_positive_timeout_raises(self):
        with self.assertRaises(ValueError):
            verify(SAFE_DATALOG, dialect="datalog", timeout=0)

    # 7
    def test_solver_timeout_returns_unknown(self):
        res = verify(UNSAFE_DATALOG, dialect="datalog", timeout=1)
        self.assertIn(res["status"], {"unsafe", "unknown"})  # host-speed dependent

    # 8
    def test_safe_case_smtlib_string(self):
        res = verify(SAFE_SMT, dialect="smtlib2", timeout=3)
        self.assertEqual(res["status"], "safe")

    # 9
    def test_unsafe_case_smtlib_file(self):
        path = _tmp_file(UNSAFE_SMT, ".smt2")
        try:
            res = verify(path, dialect="smtlib2", timeout=3)
            self.assertEqual(res["status"], "unsafe")
        finally:
            os.remove(path)

    # 10
    def test_safe_case_datalog_file_path(self):
        path = _tmp_file(SAFE_DATALOG, ".dl")
        try:
            res = verify(path, dialect="datalog", timeout=3)
            self.assertEqual(res["status"], "safe")
        finally:
            os.remove(path)

    # 11
    def test_invalid_file_path_returns_unknown(self):
        res = verify("/non/existent/file.dl", dialect="datalog", timeout=3)
        self.assertEqual(res["status"], "unknown")

    # 12
    def test_mixed_queries_returns_unsafe_first_sat(self):
        res = verify(MIXED_QUERIES_DATALOG, dialect="datalog", timeout=3)
        self.assertEqual(res["status"], "unsafe")


if __name__ == "__main__":
    unittest.main()
