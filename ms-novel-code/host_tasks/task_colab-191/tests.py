# tests


import unittest
import threading
from copy import deepcopy

# Assume Config is imported from config_module
from main import Config


class TestConfig(unittest.TestCase):
    """Unit tests for the Config singleton."""

    def setUp(self) -> None:
        """Prepare fresh input data for each test run."""
        self.base_input = {
            "defaults": {
                "server": {"host": "127.0.0.1", "port": 8000},
                "logging": {"level": "INFO"},
            },
            "config_json": {
                "server": {"port": 9000},
                "feature_flags": {"beta": True},
            },
            "env_vars": {
                "server__host": "0.0.0.0",
                "feature_flags__beta": "false",
            },
            "cli_overrides": {
                "server__port": 8081,
                "new_feature": True,
            },
        }
        # Reset singleton between tests
        Config._instance = None  # pylint: disable=protected-access

    def test_singleton_identity(self) -> None:
        """Two get_instance calls should return exactly the same object."""
        cfg1 = Config.get_instance(deepcopy(self.base_input))
        cfg2 = Config.get_instance(deepcopy(self.base_input))
        self.assertIs(cfg1, cfg2)

    def test_merge_order_and_values(self) -> None:
        """Verify the final merged output respects layer priorities."""
        cfg = Config.get_instance(deepcopy(self.base_input))

        # CLI override wins
        self.assertEqual(cfg.get_int("server.port"), 8081)
        # Env var overrides config_json
        self.assertEqual(cfg.get("server.host"), "0.0.0.0")
        # config_json overrides defaults
        self.assertFalse(cfg.get_bool("feature_flags.beta"))
        # Default remains when not overridden
        self.assertEqual(cfg.get("logging.level"), "INFO")
        # New key from CLI is present
        self.assertTrue(cfg.get_bool("new_feature"))

    def test_get_helpers_and_defaults(self) -> None:
        """Check get_int and get_bool conversions and default fallbacks."""
        cfg = Config.get_instance(deepcopy(self.base_input))

        # Numeric string converts to int
        cfg._config["threshold"] = "42"  # pylint: disable=protected-access
        self.assertEqual(cfg.get_int("threshold"), 42)

        # Non-numeric string falls back
        self.assertIsNone(cfg.get_int("logging.level"))

        # Boolean string handled
        cfg._config["flag"] = "true"  # pylint: disable=protected-access
        self.assertTrue(cfg.get_bool("flag"))

        # Missing key returns supplied default
        self.assertEqual(cfg.get("missing.key", "NA"), "NA")

    def test_reload_updates_json_and_env_only(self) -> None:
        """reload should pick up new JSON/env layers but keep CLI overrides."""
        cfg = Config.get_instance(deepcopy(self.base_input))

        # Simulate changes
        cfg._json_data["server"]["port"] = 9500  # pylint: disable=protected-access
        cfg._raw_env["server__host"] = "10.0.0.1"  # pylint: disable=protected-access

        cfg.reload()

        # CLI override still wins
        self.assertEqual(cfg.get_int("server.port"), 8081)
        # Updated env var visible
        self.assertEqual(cfg.get("server.host"), "10.0.0.1")
        # JSON change visible when not trumped by CLI
        self.assertEqual(cfg.get_int("server.port"), 8081)  # still overridden
        self.assertEqual(cfg.get("logging.level"), "INFO")  # unchanged

    def test_thread_safety_of_get(self) -> None:
        """Ensure concurrent reads do not raise and return consistent values."""

        cfg = Config.get_instance(deepcopy(self.base_input))
        results = []

        def reader() -> None:
            for _ in range(10_000):
                host = cfg.get("server.host")
                port = cfg.get_int("server.port")
                results.append((host, port))

        threads = [threading.Thread(target=reader) for _ in range(4)]
        for t_thr in threads:
            t_thr.start()
        for t_thr in threads:
            t_thr.join()

        # All reads should be consistent with current config state
        expected = ("0.0.0.0", 8081)
        self.assertTrue(all(pair == expected for pair in results))


if __name__ == "__main__":
    unittest.main()
