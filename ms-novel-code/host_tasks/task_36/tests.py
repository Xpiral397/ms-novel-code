# tests

"""
End-to-end tests for the AIRateLimiter implementation.

Each test spins up a fresh fake clock so that window-reset logic is
deterministic even under multi-process runners (which call setUp/tearDown
but *not* setUpClass/tearDownClass).  All behaviours required by the
specification are covered in one TestCase class.
"""

import unittest
from unittest.mock import patch
from main import AIRateLimiter


class _FakeClock:
    """Minimal monotonic clock that can be advanced manually."""
    def __init__(self, start: int = 0) -> None:
        self._now = start

    def time(self) -> int:
        return self._now

    def tick(self, seconds: int = 1) -> None:
        self._now += seconds


class TestAIRateLimiter(unittest.TestCase):
    # -----------------------------------------------------
    # common test scaffolding
    # -----------------------------------------------------
    def setUp(self):
        self.clock = _FakeClock()
        self._patcher = patch("time.time", self.clock.time)
        self._patcher.start()

    def tearDown(self):
        self._patcher.stop()

    @staticmethod
    def _request_limiter():
        cfg = {
            "free": {"limits": [2, 5, 10], "priority": 1},
            "enterprise": {"limits": [2, 5, 10], "priority": 3},
        }
        win = [1, 60, 86_400]
        return AIRateLimiter(cfg, win, {}, "request").create_limiter()

    @staticmethod
    def _token_limiter():
        cfg = {"pro": {"token_limits": [5, 50, 100], "priority": 2}}
        win = [1, 60, 86_400]
        costs = {"text_gen": 2}
        rl = AIRateLimiter(cfg, win, costs, "token")
        return rl.create_limiter(), rl

    # -----------------------------------------------------
    # request-mode success path
    # -----------------------------------------------------
    def test_request_success_counts(self):
        deco = self._request_limiter()

        @deco
        def api(u, t, o, c):
            return "ok"

        res = api("u1", "free", "op", "x")
        info = res["rate_limit_info"]
        self.assertEqual(info["requests_consumed"], 1)
        self.assertEqual(info["remaining_requests"][0], 1)

    # -----------------------------------------------------
    # request-mode queue when per-second window filled
    # -----------------------------------------------------
    def test_request_window_exhaustion_queue(self):
        deco = self._request_limiter()

        @deco
        def api(u, t, o, c):
            return "ok"

        api("u2", "free", "op", "a")
        api("u2", "free", "op", "b")
        queued = api("u2", "free", "op", "c")
        self.assertEqual(queued["status"], "queued")
        self.assertIn("queue_position", queued)

    # -----------------------------------------------------
    # window reset after clock tick
    # -----------------------------------------------------
    def test_request_reset_after_window(self):
        deco = self._request_limiter()

        @deco
        def api(u, t, o, c):
            return "ok"

        api("u3", "free", "op", "a")
        api("u3", "free", "op", "b")
        self.clock.tick(1)
        res = api("u3", "free", "op", "c")
        self.assertIn("rate_limit_info", res)
        self.assertEqual(res["rate_limit_info"]["remaining_requests"][0], 1)

    # -----------------------------------------------------
    # enterprise tier receives higher queue priority
    # -----------------------------------------------------
    def test_priority_enterprise_ahead_of_free(self):
        deco = self._request_limiter()

        @deco
        def api(u, t, o, c):
            return "ok"

        api("f1", "free", "op", "x")
        api("f2", "free", "op", "y")
        q_free = api("f3", "free", "op", "z")
        q_ent = api("e1", "enterprise", "op", "z")
        self.assertLess(q_ent["queue_position"], q_free["queue_position"])

    # -----------------------------------------------------
    # FIFO order for callers of identical priority
    # -----------------------------------------------------
    def test_fifo_within_same_priority(self):
        deco = self._request_limiter()

        @deco
        def api(u, t, o, c):
            return "ok"

        api("f4", "free", "op", "x")
        api("f5", "free", "op", "y")
        q1 = api("f6", "free", "op", "z")
        q2 = api("f7", "free", "op", "z")
        self.assertLess(q1["queue_position"], q2["queue_position"])

    # -----------------------------------------------------
    # token-mode success path
    # -----------------------------------------------------
    def test_token_success_counts(self):
        deco, _ = self._token_limiter()

        @deco
        def api(u, t, o, c):
            return "done"

        res = api("u4", "pro", "text_gen", "one two")
        info = res["rate_limit_info"]
        self.assertEqual(info["tokens_consumed"], 4)
        self.assertEqual(info["remaining_tokens"][0], 1)

    # -----------------------------------------------------
    # token-mode empty content still bills minimum token
    # -----------------------------------------------------
    def test_token_empty_content_minimum(self):
        deco, rl = self._token_limiter()

        @deco
        def api(u, t, o, c):
            return "done"

        self.assertEqual(rl.get_token_count(""), 1)
        res = api("u5", "pro", "text_gen", "")
        self.assertEqual(res["rate_limit_info"]["tokens_consumed"], 2)

    # -----------------------------------------------------
    # token-mode queue when per-second cap exceeded
    # -----------------------------------------------------
    def test_token_queue_on_exceed(self):
        deco, _ = self._token_limiter()

        @deco
        def api(u, t, o, c):
            return "done"

        api("u6", "pro", "text_gen", "one two")
        queued = api("u6", "pro", "text_gen", "one two three")
        self.assertEqual(queued["status"], "queued")

    # -----------------------------------------------------
    # helper token counter correctness
    # -----------------------------------------------------
    def test_helper_token_count_accuracy(self):
        _, rl = self._token_limiter()
        self.assertEqual(rl.get_token_count("one two three"), 3)

    def test_helper_token_count_empty(self):
        _, rl = self._token_limiter()
        self.assertEqual(rl.get_token_count(""), 1)

    # -----------------------------------------------------
    # fresh user starts with full quota
    # -----------------------------------------------------
    def test_new_user_full_allocation(self):
        deco = self._request_limiter()

        @deco
        def api(u, t, o, c):
            return "ok"

        res = api("newbie", "free", "op", "hi")
        self.assertEqual(res["rate_limit_info"]["remaining_requests"][0], 1)

    # -----------------------------------------------------
    # daily window resets after 24h tick
    # -----------------------------------------------------
    def test_daily_window_reset(self):
        deco = self._request_limiter()

        @deco
        def api(u, t, o, c):
            return "ok"

        api("u7", "free", "op", "a")
        self.clock.tick(86_400)
        res = api("u7", "free", "op", "b")
        self.assertEqual(res["rate_limit_info"]["remaining_requests"][2], 9)

    # -----------------------------------------------------
    # per-user isolation
    # -----------------------------------------------------
    def test_multi_user_isolated_state(self):
        deco = self._request_limiter()

        @deco
        def api(u, t, o, c):
            return "ok"

        r1 = api("userA", "free", "op", "x")
        r2 = api("userB", "free", "op", "x")
        self.assertEqual(r1["rate_limit_info"]["remaining_requests"][0], 1)
        self.assertEqual(r2["rate_limit_info"]["remaining_requests"][0], 1)


if __name__ == "__main__":
    unittest.main()
