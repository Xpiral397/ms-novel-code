# tests

"""Comprehensive tests for AIRateLimiter in a single TestCase class."""
import unittest
from unittest.mock import patch
from main import AIRateLimiter


class _FakeClock:
    def __init__(self, start: int = 0) -> None:
        self._now = start

    def time(self) -> int:
        return self._now

    def tick(self, seconds: int = 1) -> None:
        self._now += seconds


class TestAIRateLimiter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.clock = _FakeClock()
        cls._patcher = patch("time.time", cls.clock.time)
        cls._patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls._patcher.stop()

    # Helper fabricators
    def _request_limiter(self):
        cfg = {
            "free": {"limits": [2, 5, 10], "priority": 1},
            "enterprise": {"limits": [2, 5, 10], "priority": 3},
        }
        win = [1, 60, 86400]
        return main.AIRateLimiter(cfg, win, {}, "request").create_limiter()

    def _token_limiter(self):
        cfg = {"pro": {"token_limits": [5, 50, 100], "priority": 2}}
        win = [1, 60, 86400]
        costs = {"text_gen": 2}
        rl = main.AIRateLimiter(cfg, win, costs, "token")
        return rl.create_limiter(), rl

    # Request-based tests
    def test_request_success_counts(self):
        deco = self._request_limiter()

        @deco
        def api(u, t, o, c):
            return c

        r = api("u1", "free", "op", "x")
        self.assertEqual(r["rate_limit_info"]["requests_consumed"], 1)
        self.assertEqual(r["rate_limit_info"]["remaining_requests"][0], 1)

    def test_request_window_exhaustion_queue(self):
        deco = self._request_limiter()

        @deco
        def api(u, t, o, c):
            return c

        api("u2", "free", "op", "a")
        api("u2", "free", "op", "b")
        q = api("u2", "free", "op", "c")
        self.assertEqual(q["status"], "queued")

    def test_request_reset_after_window(self):
        deco = self._request_limiter()

        @deco
        def api(u, t, o, c):
            return c

        api("u3", "free", "op", "a")
        api("u3", "free", "op", "b")
        self.clock.tick(1)
        r = api("u3", "free", "op", "c")
        self.assertIn("rate_limit_info", r)

    # Token-based tests
    def test_token_success_counts(self):
        deco, _ = self._token_limiter()

        @deco
        def api(u, t, o, c):
            return c

        r = api("u4", "pro", "text_gen", "one two")
        self.assertEqual(r["tokens_consumed"], 4)
        self.assertEqual(r["remaining_tokens"][0], 1)

    def test_token_empty_content_minimum(self):
        deco, rl = self._token_limiter()

        @deco
        def api(u, t, o, c):
            return c

        self.assertEqual(rl.get_token_count(""), 1)
        r = api("u5", "pro", "text_gen", "")
        self.assertEqual(r["tokens_consumed"], 2)  # 1 token × cost 2

    def test_token_queue_on_exceed(self):
        deco, _ = self._token_limiter()

        @deco
        def api(u, t, o, c):
            return c

        api("u6", "pro", "text_gen", "one two")
        q = api("u6", "pro", "text_gen", "one two three")
        self.assertEqual(q["status"], "queued")

    # Priority and FIFO tests
    def test_priority_enterprise_ahead_of_free(self):
        deco = self._request_limiter()

        @deco
        def api(u, t, o, c):
            return c

        api("f1", "free", "op", "x")
        api("f2", "free", "op", "y")
        q_free = api("f3", "free", "op", "z")
        q_ent = api("e1", "enterprise", "op", "z")
        self.assertLess(q_ent["queue_position"], q_free["queue_position"])

    def test_fifo_within_same_priority(self):
        deco = self._request_limiter()

        @deco
        def api(u, t, o, c):
            return c

        api("f4", "free", "op", "x")
        api("f5", "free", "op", "y")
        q1 = api("f6", "free", "op", "z")
        q2 = api("f7", "free", "op", "z")
        self.assertLess(q1["queue_position"], q2["queue_position"])

    # Helper method accuracy
    def test_helper_token_count_accuracy(self):
        _, rl = self._token_limiter()
        self.assertEqual(rl.get_token_count("one two three"), 3)

    def test_helper_token_count_empty(self):
        _, rl = self._token_limiter()
        self.assertEqual(rl.get_token_count(""), 1)

    # New user state
    def test_new_user_full_allocation(self):
        deco = self._request_limiter()

        @deco
        def api(u, t, o, c):
            return c

        r = api("newbie", "free", "op", "hi")
        self.assertEqual(r["rate_limit_info"]["remaining_requests"][0], 1)

    # Long window reset
    def test_daily_window_reset(self):
        deco = self._request_limiter()

        @deco
        def api(u, t, o, c):
            return c

        api("u7", "free", "op", "a")
        self.clock.tick(86400)
        r = api("u7", "free", "op", "b")
        self.assertEqual(r["rate_limit_info"]["remaining_requests"][2], 9)

    # Multi-user isolation
    def test_multi_user_isolated_state(self):
        deco = self._request_limiter()

        @deco
        def api(u, t, o, c):
            return c

        r1 = api("userA", "free", "op", "x")
        r2 = api("userB", "free", "op", "x")
        self.assertEqual(r1["rate_limit_info"]["remaining_requests"][0], 1)
        self.assertEqual(r2["rate_limit_info"]["remaining_requests"][0], 1)


if __name__ == "__main__":
    unittest.main()
