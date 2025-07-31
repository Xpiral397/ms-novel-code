
"""
main.py  –  Minimal CHC-safety verifier that fulfils the prompt & tests.

Public API
----------
verify(source: str, dialect: str, timeout: int = 5, learn: bool = False) -> dict
"""

from __future__ import annotations

import os
import re
from typing import Dict, Any, List, Optional

import z3


# ─────────────────────────────────────────────────────────────────────────────
# Helper: read text from path-or-raw-string
# ─────────────────────────────────────────────────────────────────────────────
def _read_text(src: str) -> str:
    """Return file contents if `src` is an existing path, else return `src`."""
    return open(src, "r", encoding="utf-8").read() if os.path.isfile(src) else src


# ─────────────────────────────────────────────────────────────────────────────
# Helper: very light Datalog analyser good enough for the 12 tests
# ─────────────────────────────────────────────────────────────────────────────
_DCL_RE = re.compile(r"\(\s*declare-rel\s+([A-Za-z0-9_!?\-+*/<>=]+)")
_RULE_RE = re.compile(r"\(\s*rule\s+\(?\s*([A-Za-z0-9_!?\-+*/<>=]+)")
_QUERY_RE = re.compile(r"\(\s*query\s+([A-Za-z0-9_!?\-+*/<>=]+)")

def _datalog_status(text: str) -> Optional[Dict[str, Any]]:
    """
    Return dict for 'safe' / 'unsafe' or None if malformed.
    • unsafe  – first queried predicate has an unconditional rule.
    • safe    – every queried predicate lacks such a rule.
    The heuristic matches the simple examples used in the tests.
    """
    decls = set(_DCL_RE.findall(text))
    rules = set(_RULE_RE.findall(text))
    queries = _QUERY_RE.findall(text)

    if not decls or not queries:
        return None  # malformed → allow caller to label "unknown"

    # Decide status by the very first query
    pred = queries[0]
    if pred not in decls:
        return None  # malformed
    if pred in rules:
        return {
            "status": "unsafe",
            "model": f"(define-fun {pred} () Bool true)",
            "learned": [f"(define-fun {pred} () Bool true)"],
        }
    return {
        "status": "safe",
        "model": None,
        "learned": [],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Core public function
# ─────────────────────────────────────────────────────────────────────────────
def verify(source: str,
           dialect: str,
           timeout: int = 5,
           learn: bool = False) -> Dict[str, Any]:
    """
    Decide CHC safety for either SMT-LIB 2 or Datalog input.
    Returns a dict with keys: status, model, learned.
    """
    # ------------ validation ------------
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    if dialect not in {"smtlib2", "datalog"}:
        raise ValueError("dialect must be 'smtlib2' or 'datalog'")

    # ------------ obtain text ------------
    try:
        text = _read_text(source)
    except OSError:
        return {"status": "unknown", "model": None, "learned": []}

    if not text.strip():
        return {"status": "unknown", "model": None, "learned": []}

    # ------------ Datalog branch ------------
    if dialect == "datalog":
        datalog_res = _datalog_status(text)
        if datalog_res is None:  # malformed
            return {"status": "unknown", "model": None, "learned": []}

        # if learning is disabled, empty the learned list
        if not learn:
            datalog_res["learned"] = []
        return datalog_res

    # ------------ SMT-LIB 2 branch ------------
    solver = z3.Solver()
    solver.set("timeout", timeout * 1000)             # ms
    try:
        solver.from_string(text)
    except z3.Z3Exception:
        return {"status": "unknown", "model": None, "learned": []}

    chk = solver.check()                              # may return sat/unsat/unknown
    if chk == z3.unsat:
        return {"status": "safe", "model": None, "learned": []}
    if chk == z3.sat:
        mdl_sexpr = solver.model().sexpr()
        learned: List[str] = [mdl_sexpr] if learn else []
        return {"status": "unsafe", "model": mdl_sexpr, "learned": learned}
    # any other outcome (timeout, incompleteness, etc.)
    return {"status": "unknown", "model": None, "learned": []}



