# test.py

import unittest
import threading
import time
import json
import os
import logging
from unittest.mock import patch

import Pyro4

from main import (
    AuthenticationError,
    ServiceError,
    ArithmeticService,
    StatsService,
    ConfigHolder,
    ServiceProxy,
    ServiceRegistry,
)


class TestServicesLocal(unittest.TestCase):
    """Test ArithmeticService and StatsService logic and authentication."""

    def setUp(self):
        logger = logging.getLogger("test")
        logger.addHandler(logging.NullHandler())
        self.api_key = "secret"
        self.arith = ArithmeticService(self.api_key, logger)
        self.stats = StatsService(self.api_key, logger)

    def test_arithmetic_operations(self):
        self.assertEqual(self.arith.add(1, 2, self.api_key), 3)
        self.assertEqual(self.arith.subtract(5, 2, self.api_key), 3)
        self.assertEqual(self.arith.multiply(3, 4, self.api_key), 12)
        self.assertEqual(self.arith.divide(8, 2, self.api_key), 4.0)

    def test_divide_by_zero(self):
        with self.assertRaises(ZeroDivisionError):
            self.arith.divide(1, 0, self.api_key)

    def test_arithmetic_authentication(self):
        with self.assertRaises(AuthenticationError):
            self.arith.add(1, 2, "bad_key")

    def test_stats_record_and_auth(self):
        self.stats.record_call("svc", "v1", "m", 12.3, self.api_key)
        self.assertEqual(self.stats._calls, [("svc", "v1", "m", 12.3)])
        with self.assertRaises(AuthenticationError):
            self.stats.record_call("svc", "v1", "m", 5.5, "bad_key")


class TestServiceProxyIntegration(unittest.TestCase):
    """Integration tests for ServiceProxy under various scenarios."""

    @classmethod
    def setUpClass(cls):
        # Start a Pyro daemon and register services
        cls.daemon = Pyro4.Daemon()
        logger = logging.getLogger("test")
        logger.addHandler(logging.NullHandler())
        cls.api_key = "secret"

        svc = ArithmeticService(cls.api_key, logger)
        stats = StatsService(cls.api_key, logger)
        cls.uri_svc = cls.daemon.register(svc)
        cls.uri_stats = cls.daemon.register(stats)

        # Run daemon loop in background
        cls.thread = threading.Thread(target=cls.daemon.requestLoop, daemon=True)
        cls.thread.start()

        # Prepare config.json for reload & registry tests
        cls.config = {
            "name_servers": ["localhost:9999"],  # unreachable
            "services": {
                "arithmetic": {"direct_uris": {"v1_0": [str(cls.uri_svc)]}},
                "stats": {"direct_uris": {"1_0": [str(cls.uri_stats)]}}
            },
            "auth": {"api_key": cls.api_key},
            "client": {
                "retry_count": 1,
                "timeout_seconds": 0.5,
                "backoff_factor": 0.1
            },
            "logging": {"path": ".", "level": "DEBUG", "rotate_every_mb": 1}
        }
        with open("config.json", "w") as f:
            json.dump(cls.config, f)

        cls.proxy = ServiceProxy(cls.config)
        cls.stats_instance = stats

    @classmethod
    def tearDownClass(cls):
        cls.daemon.shutdown()
        cls.thread.join()
        os.remove("config.json")

    def setUp(self):
        # Ensure instance attributes
        self.config = self.__class__.config
        self.proxy = self.__class__.proxy
        self.stats = self.__class__.stats_instance

    def test_normal_call(self):
        resp = self.proxy.call("arithmetic", "v1_0", "add", [2, 3])
        self.assertEqual(resp["result"], 5)

    def test_divide_by_zero(self):
        with self.assertRaises(ServiceError) as cm:
            self.proxy.call("arithmetic", "v1_0", "divide", [5, 0])
        self.assertEqual(cm.exception.code, "ZeroDivisionError")

    def test_auth_failure_wrapped(self):
        bad_cfg = dict(self.config)
        bad_cfg["auth"] = {"api_key": "wrong"}
        proxy_bad = ServiceProxy(bad_cfg)
        with self.assertRaises(ServiceError) as cm:
            proxy_bad.call("arithmetic", "v1_0", "add", [1, 2])
        self.assertEqual(cm.exception.code, "AuthenticationError")

    def test_metrics_reporting(self):
        self.stats._calls.clear()
        self.proxy.call("arithmetic", "v1_0", "subtract", [9, 4])
        time.sleep(0.2)
        calls = self.stats._calls
        self.assertTrue(any(c[2] == "subtract" for c in calls))

    def test_retry_and_backoff(self):
        bad_cfg = dict(self.config)
        bad_cfg["services"] = {
            "arithmetic": {"direct_uris": {"v1_0": ["PYRO:nonexistent@none"]}}
        }
        proxy_bad = ServiceProxy(bad_cfg)
        with self.assertRaises(ServiceError) as cm:
            proxy_bad.call("arithmetic", "v1_0", "add", [1, 2])
        self.assertEqual(cm.exception.code, "PyroError")

    def test_name_server_fallback(self):
        calls = {"count": 0}

        def fake_locate(host=None, port=None):
            calls["count"] += 1
            if calls["count"] == 1:
                raise Pyro4.errors.PyroError()
            return None  # force direct URI next

        with patch.object(Pyro4, "locateNS", side_effect=fake_locate):
            resp = self.proxy.call("arithmetic", "v1_0", "add", [4, 3])
            self.assertEqual(resp["result"], 7)

    def test_config_reload(self):
        holder = ConfigHolder("config.json")
        old = holder.get()
        new = old.copy()
        new["auth"]["api_key"] = "newkey"
        with open("config.json", "w") as f:
            json.dump(new, f)
        holder.reload()
        updated = holder.get()
        self.assertEqual(updated["auth"]["api_key"], "newkey")

    def test_heartbeat_re_registration(self):
        # Patch Daemon.requestLoop so ServiceRegistry.__init__ returns immediately
        original_loop = Pyro4.Daemon.requestLoop
        Pyro4.Daemon.requestLoop = lambda self: None
        try:
            holder = ConfigHolder("config.json")
            reg = ServiceRegistry(holder)
        finally:
            Pyro4.Daemon.requestLoop = original_loop

        history = []

        class FakeNS:
            def register(self, name, uri):
                history.append(name)

        reg._locate_ns = lambda: FakeNS()
        reg._heartbeat()
        self.assertIn("arithmetic.service.v1_0", history)
        self.assertIn("stats.service.v1_0", history)


if __name__ == "__main__":
    unittest.main()
