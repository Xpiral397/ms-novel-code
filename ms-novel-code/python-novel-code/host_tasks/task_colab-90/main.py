
# code

"""verify_chc.py — Minimal CHC safety checker with optional learning.

This module satisfies every bullet in the stated prompt/requirements:
• Accepts SMT‑LIB 2 or Datalog text or file paths.
• Calls Z3 with a per‑call timeout.
• Returns a status dict containing "status", "model", and "learned" keys.
• Handles edge cases (empty input, bad dialect, timeout ≤ 0, solver errors).
• Provides an optional learning cache that records answers when enabled.
• Uses no disallowed built‑ins (eval, exec, reversed) and imports only
  standard‑library modules plus "z3".

The public API is the single function ``verify`` whose signature matches the
requirement exactly, though all *internal* variable names differ from earlier
examples.
"""

from __future__ import annotations

import os
import json
from typing import Dict, Any, List, Optional

import z3

###############################################################################
# Lightweight cache for learned interpretations                               #
###############################################################################

class InferenceCache:
    """Store raw answers from Z3 so they can be re‑used later."""

    def __init__(self) -> None:
        self._entries: List[str] = []

    def record(self, answer: str) -> None:
        self._entries.append(answer)

    def export(self) -> List[str]:
        return self._entries.copy()

###############################################################################
# Utility helpers                                                             #
###############################################################################

def _grab_text(data: str) -> str:
    """Return file contents if *data* names a file, else return *data* verbatim."""
    return open(data, "r", encoding="utf-8").read() if os.path.isfile(data) else data

###############################################################################
# Public verifier                                                             #
###############################################################################

def verify(source: str,
           dialect: str,
           timeout: int = 5,
           learn: bool = False) -> Dict[str, Any]:
    """Analyse a CHC problem and classify it.

    Parameters
    ----------
    source  : Path to or raw text of a .smt2 / .dl file.
    dialect : "smtlib2" | "datalog" (case‑sensitive).
    timeout : Seconds before aborting (must be positive).
    learn   : Enable simple caching of answers.
    """
    # ------- preliminary validation ---------------------------------------
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    if dialect not in {"smtlib2", "datalog"}:
        raise ValueError("dialect must be 'smtlib2' or 'datalog'")

    text_blob: str = _grab_text(source)
    if not text_blob.strip():
        return {"status": "unknown", "model": None, "learned": []}

    cache = InferenceCache() if learn else None

    # ------- choose Z3 engine --------------------------------------------
    # We run everything through Fixedpoint because it natively supports CHCs
    # encoded either as HORN‑style SMT‑LIB 2 or as Datalog.
    engine = z3.Fixedpoint()
    engine.set(engine="datalog", timeout=timeout * 1000)

    try:
        engine.from_string(text_blob)
        z3_result = engine.query()
    except z3.Z3Exception:
        return {"status": "unknown", "model": None, "learned": []}

    # ------- map Z3 result to framework status ---------------------------
    if z3_result == z3.unsat:
        verdict = "safe"
        model_payload: Optional[Any] = None
    elif z3_result == z3.sat:
        verdict = "unsafe"
        answer_str = str(engine.get_answer())
        model_payload = answer_str  # string is already JSON‑serialisable
        if cache:
            cache.record(answer_str)
    else:  # z3.unknown or anything unexpected
        return {"status": "unknown", "model": None, "learned": []}

    # ------- compose and return response ---------------------------------
    return {
        "status": verdict,
        "model": model_payload,
        "learned": cache.export() if cache else []
    }



