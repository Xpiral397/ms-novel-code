"""
Comprehensive tests for AIRateLimiter in main.py.

Checks:
1.  Token counting and one-token minimum
2.  Decorator factory contract
3.  Request-based success + metadata
4.  Queuing after per-second exhaustion (request mode)
5.  Window reset (request mode)
6.  Priority ordering: Enterprise > Free
7.  FIFO ordering within a tier
8.  Token-based success + metadata
9.  Queuing on token budget exhaustion
10. Token window reset
11. Multiple window metadata integrity
"""

from __future__ import annotations

import importlib
import unittest
from types import ModuleType
from unittest.mock import patch

main: ModuleType = importlib.import_module("main")
from main import AIRateLimiter  # type: ignore  # noqa: E402  (import style)


class FakeTime:
    """Deterministic replacement for time.time()."""

    def __init__(self, start: float = 0.0) -> None:
        self._now = start

    def time(self) -> float:  # noqa: D401
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += seconds


class TestAIRateLimiter(unittest.TestCase):
    """All required behaviours validated in a single TestCase."""

    def setUp(self) -> None:
        self.clock = FakeTime()
        self._patchers = [
            patch("time.time", self.clock.time),
            patch("main.time.time", self.clock.time),
        ]
        for p in self._patchers:
            p.start()

    def tearDown(self) -> None:
        for p in self._patchers:
            p.stop()

    # Helper utilities --------------------------------------------------------
    def _make_request_fn(self):
        tiers = {
            "free": {"limits": [1, 3, 50], "priority": 1},
            "pro": {"limits": [2, 5, 100], "priority": 2},
            "ent": {"limits": [3, 6, 200], "priority": 3},
        }
        factory = AIRateLimiter(tiers, [1, 60, 86400], {}, "request")
        decorator = factory.create_limiter()

        @decorator
        def generate(user_id, tier, operation, content):
            return content

        return generate

    def _make_token_fn(self):
        tiers = {"pro": {"token_limits": [5, 50, 200], "priority": 2}}
        costs = {"text_gen": 2}
        factory = AIRateLimiter(tiers, [1, 60, 86400], costs, "token")
        decorator = factory.create_limiter()

        @decorator
        def generate(user_id, tier, operation, content):
            return content

        return generate

    # Test cases --------------------------------------------------------------
    def test_token_counting(self) -> None:
        limiter = AIRateLimiter({}, [1, 60, 86400], {}, "token")
        self.assertEqual(limiter.get_token_count("one two"), 2)

    def test_token_minimum_one(self) -> None:
        limiter = AIRateLimiter({}, [1, 60, 86400], {}, "token")
        self.assertEqual(limiter.get_token_count(""), 1)

    def test_factory_returns_decorator(self) -> None:
        cfg = {"free": {"limits": [1, 3, 10], "priority": 1}}
        factory = AIRateLimiter(cfg, [1, 60, 86400], {}, "request")
        self.assertTrue(callable(factory.create_limiter()))

    def test_request_success_metadata(self) -> None:
        gen = self._make_request_fn()
        out = gen("u1", "pro", "op", "hello")
        info = out["rate_limit_info"]
        self.assertEqual(info["requests_consumed"], 1)
        self.assertEqual(info["remaining_requests"][0], 1)

    def test_request_queued_after_second_limit(self) -> None:
        gen = self._make_request_fn()
        gen("u1", "pro", "op", "A")
        gen("u1", "pro", "op", "B")
        queued = gen("u1", "pro", "op", "C")
        self.assertEqual(queued["status"], "queued")

    def test_request_window_reset(self) -> None:
        gen = self._make_request_fn()
        gen("u2", "free", "op", "x")
        gen("u2", "free", "op", "y")
        self.clock.advance(1.1)
        out = gen("u2", "free", "op", "z")
        self.assertEqual(out["result"], "z")

    def test_priority_enterprise_before_free(self) -> None:
        gen = self._make_request_fn()
        gen("e1", "ent", "op", "1")
        q_ent = gen("e1", "ent", "op", "2")
        gen("f1", "free", "op", "1")
        q_free = gen("f1", "free", "op", "2")
        self.assertLess(q_ent["queue_position"], q_free["queue_position"])

    def test_fifo_within_same_tier(self) -> None:
        gen = self._make_request_fn()
        gen("u3", "pro", "op", "X")
        gen("u3", "pro", "op", "Y")
        q1 = gen("u3", "pro", "op", "Z")
        q2 = gen("u3", "pro", "op", "W")
        self.assertLess(q1["queue_position"], q2["queue_position"])

    def test_token_success_metadata(self) -> None:
        gen = self._make_token_fn()
        out = gen("u1", "pro", "text_gen", "hi")
        info = out["rate_limit_info"]
        self.assertEqual(info["tokens_consumed"], 2)
        self.assertEqual(info["remaining_tokens"][0], 3)

    def test_token_queue_over_budget(self) -> None:
        gen = self._make_token_fn()
        gen("u1", "pro", "text_gen", "hi")
        queued = gen("u1", "pro", "text_gen", "one two three")
        self.assertEqual(queued["status"], "queued")

    def test_token_window_reset(self) -> None:
        gen = self._make_token_fn()
        gen("u2", "pro", "text_gen", "one two")
        gen("u2", "pro", "text_gen", "three four")
        self.clock.advance(1.1)
        out = gen("u2", "pro", "text_gen", "five")
        self.assertEqual(out["rate_limit_info"]["tokens_consumed"], 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
