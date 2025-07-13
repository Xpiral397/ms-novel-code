# tests
import unittest
import threading
import time
from unittest.mock import patch

import Pyro4
import main


# ───── helper to spin up a fresh daemon per test ────────────
def make_fixture():
    key = "secret"
    daemon = Pyro4.Daemon(host="127.0.0.1")
    arith = main.ArithmeticService(key)
    stats = main.StatsService(key)
    uri_a = daemon.register(arith)
    uri_s = daemon.register(stats)
    th = threading.Thread(target=daemon.requestLoop, daemon=True)
    th.start()

    cfg = {
        "name_servers": ["localhost:9999"],
        "services": {
            "arithmetic": {"direct_uris": {"v1_0": [str(uri_a)]}},
            "stats": {"direct_uris": {"1_0": [str(uri_s)]}},
        },
        "auth": {"api_key": key},
        "client": {"retry_count": 1, "timeout_seconds": 0.5, "backoff_factor": 0.1},
    }
    proxy = main.ServiceProxy(cfg)
    return daemon, th, cfg, proxy, stats


class TestSOA(unittest.TestCase):
    # ───────── local logic ──────────────────────────
    def test_local_ops(self):
        a = main.ArithmeticService("k")
        self.assertEqual(a.add(2, 3, "k"), 5)
        with self.assertRaises(main.AuthenticationError):
            a.add(1, 1, "bad")

    def test_local_zero(self):
        a = main.ArithmeticService("k")
        with self.assertRaises(ZeroDivisionError):
            a.divide(1, 0, "k")

    # ───────── remote happy path ─────────────────────
    def test_remote_add(self):
        d, t, _, px, _ = make_fixture()
        self.assertEqual(px.call("arithmetic", "v1_0", "add", [4, 6])["result"], 10)
        d.shutdown(); t.join(timeout=0.1)

    # ───────── remote error paths ────────────────────
    def test_remote_div_zero(self):
        d, t, _, px, _ = make_fixture()
        with self.assertRaises(main.ServiceError):
            px.call("arithmetic", "v1_0", "divide", [1, 0])
        d.shutdown(); t.join(timeout=0.1)

    def test_remote_bad_key(self):
        d, t, cfg, _, _ = make_fixture()
        wrong = {**cfg, "auth": {"api_key": "bad"}}
        with self.assertRaises(main.ServiceError):
            main.ServiceProxy(wrong).call("arithmetic", "v1_0", "add", [1, 1])
        d.shutdown(); t.join(timeout=0.1)

    # ───────── metrics posting ───────────────────────
    def test_metrics(self):
        d, t, _, px, stats = make_fixture()
        stats.calls.clear()
        px.call("arithmetic", "v1_0", "subtract", [7, 2])
        time.sleep(0.2)
        self.assertTrue(any(c[2] == "subtract" for c in stats.calls))
        d.shutdown(); t.join(timeout=0.1)

    # ───────── retry & NS fallback ───────────────────
    def test_retry(self):
        d, t, cfg, _, _ = make_fixture()
        broken = {**cfg}
        broken["services"]["arithmetic"]["direct_uris"]["v1_0"] = ["PYRO:bad@none"]
        with self.assertRaises(main.ServiceError):
            main.ServiceProxy(broken).call("arithmetic", "v1_0", "add", [1, 1])
        d.shutdown(); t.join(timeout=0.1)

    def test_ns_fallback(self):
        d, t, _, px, _ = make_fixture()
        first = {"n": 0}

        def fake_ns(*_, **__):
            first["n"] += 1
            if first["n"] == 1:
                raise Pyro4.errors.PyroError()
            return None  # second attempt → direct URI

        with patch.object(Pyro4, "locateNS", fake_ns):
            self.assertEqual(px.call("arithmetic", "v1_0", "add", [3, 4])["result"], 7)
        d.shutdown(); t.join(timeout=0.1)

    # ───────── heartbeat registration ────────────────
    def test_heartbeat(self):
        d, t, cfg, _, _ = make_fixture()
        holder = main.ConfigHolder(cfg)
        with patch.object(Pyro4.Daemon, "requestLoop", lambda *_: None):
            registry = main.ServiceRegistry(holder)
        captured = []

        class FakeNS:  # noqa: D401
            def register(self, name, uri): captured.append(name)
        registry._ServiceRegistry__ns = lambda: FakeNS()  # type: ignore
        registry._heartbeat()
        self.assertIn("arithmetic.service.v1_0", captured)
        self.assertIn("stats.service.v1_0", captured)

        # graceful shutdown
        registry.d.shutdown()
        d.shutdown(); t.join(timeout=0.1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
