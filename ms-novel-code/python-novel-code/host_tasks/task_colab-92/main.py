
"""verify_chc.py — minimal CHC safety checker with optional learning.

Public API
----------
verify(source: str, dialect: str, timeout: int = 5, learn: bool = False) -> dict
    Analyse a CHC problem (SMT-LIB 2 or Datalog) and return a dictionary with
    keys:
        • "status": "safe" | "unsafe" | "unknown"
        • "model":  counter-example as a string or None
        • "learned": list[str] of cached answers (empty if learning disabled)
The implementation uses only the standard library plus `z3` and avoids any
disallowed built-ins such as eval, exec, or reversed.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import z3


class _InferenceCache:
    """Simple in-memory store for answers returned by Z3."""

    def __init__(self) -> None:
        self._entries: List[str] = []

    def record(self, answer: str) -> None:
        self._entries.append(answer)

    def export(self) -> List[str]:
        return self._entries.copy()


def _read_source(data: str) -> str:
    """Return file contents if *data* is a path, else *data* itself."""
    if os.path.isfile(data):
        with open(data, encoding="utf-8") as handle:
            return handle.read()
    return data


def verify(
    source: str,
    dialect: str,
    timeout: int = 5,
    learn: bool = False,
) -> Dict[str, Any]:
    """Classify a CHC problem as safe, unsafe, or unknown.

    Parameters
    ----------
    source : raw text or pathname of an `.smt2` / `.dl` file
    dialect: "smtlib2" or "datalog"
    timeout: positive integer (seconds)
    learn  : enable caching of counter-examples
    """
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    if dialect not in {"smtlib2", "datalog"}:
        raise ValueError("dialect must be 'smtlib2' or 'datalog'")

    text = _read_source(source)
    if not text.strip():
        return {"status": "unknown", "model": None, "learned": []}

    cache = _InferenceCache() if learn else None

    solver = z3.Fixedpoint()
    solver.set(engine="datalog", timeout=timeout * 1000)

    try:
        solver.from_string(text)
        result = solver.query()
    except z3.Z3Exception:
        return {"status": "unknown", "model": None, "learned": []}

    if result == z3.unsat:
        status, model = "safe", None
    elif result == z3.sat:
        status = "unsafe"
        model = str(solver.get_answer())
        if cache:
            cache.record(model)
    else:
        return {"status": "unknown", "model": None, "learned": []}

    return {
        "status": status,
        "model": model,
        "learned": cache.export() if cache else [],
    }



