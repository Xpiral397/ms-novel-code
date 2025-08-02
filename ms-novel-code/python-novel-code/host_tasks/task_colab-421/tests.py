# tests

"""
Unit tests for ttl_cache_simulator using cachetools library,
ensuring correct per-key TTL logic and simulated time advancement.
"""

import unittest
from main import ttl_cache_simulator


class TestTTLCacheSimulator(unittest.TestCase):
    """Test suite for the ttl_cache_simulator function."""

    def test_basic_set_and_get(self):
        """Test simple SET and GET commands."""
        cmds = ["SET k1 v1 10", "GET k1", "EXIT"]
        self.assertEqual(ttl_cache_simulator(cmds), ["v1"])

    def test_get_nonexistent_key_returns_null(self):
        """GET for a key never SET returns NULL."""
        cmds = ["GET keyX", "EXIT"]
        self.assertEqual(ttl_cache_simulator(cmds), ["NULL"])

    def test_expiry_after_ttl(self):
        """Key expires after SLEEP equals or exceeds TTL."""
        cmds = [
            "SET sid A 2", "SLEEP 2",
            "GET sid", "EXIT"
        ]
        self.assertEqual(ttl_cache_simulator(cmds), ["NULL"])

    def test_access_just_before_and_after_expiry(self):
        """GET before expiry returns value, after returns NULL."""
        cmds = [
            "SET x val 5", "SLEEP 4", "GET x", "SLEEP 1", "GET x", "EXIT"
        ]
        self.assertEqual(ttl_cache_simulator(cmds), ["val", "NULL"])

    def test_multiple_keys_different_ttls(self):
        """Multiple keys with different TTLs handled independently."""
        cmds = [
            "SET a va 3", "SET b vb 7", "SLEEP 4", "GET a", "GET b", "EXIT"
        ]
        self.assertEqual(ttl_cache_simulator(cmds), ["NULL", "vb"])

    def test_overwrite_key_resets_ttl(self):
        """Reseting a key via SET updates its expiry."""
        cmds = [
            "SET k v1 2", "SLEEP 1", "SET k v2 4", "SLEEP 2", "GET k", "EXIT"
        ]
        self.assertEqual(ttl_cache_simulator(cmds), ["v2"])

    def test_key_min_ttl(self):
        """Key with TTL=1 expires after one tick."""
        cmds = [
            "SET k1 v 1", "GET k1", "SLEEP 1", "GET k1", "EXIT"
        ]
        self.assertEqual(ttl_cache_simulator(cmds), ["v", "NULL"])

    def test_key_max_ttl(self):
        """Key with max TTL remains valid up to the 24 hour mark."""
        cmds = [
            "SET k1 longval 86400", "SLEEP 86399", "GET k1", "SLEEP 1", "GET k1", "EXIT"
        ]
        self.assertEqual(ttl_cache_simulator(cmds), ["longval", "NULL"])

    def test_multiple_gets(self):
        """GET multiple times before expiry yields value."""
        cmds = [
            "SET a 1 10", "GET a", "GET a", "SLEEP 9", "GET a", "EXIT"
        ]
        self.assertEqual(ttl_cache_simulator(cmds), ["1", "1", "1"])

    def test_exit_terminates_processing(self):
        """No commands processed after EXIT."""
        cmds = [
            "SET k1 v1 5",
            "EXIT",
            "GET k1",
            "SLEEP 100",
            "GET k1"
        ]
        self.assertEqual(ttl_cache_simulator(cmds), [])

    def test_zero_length_input(self):
        """Empty input yields empty output."""
        self.assertEqual(ttl_cache_simulator([]), [])

    def test_sleep_no_set(self):
        """SLEEP before SET is allowed and has no effect."""
        cmds = [
            "SLEEP 10", "SET k foo 3", "SLEEP 2", "GET k", "SLEEP 1", "GET k", "EXIT"
        ]
        self.assertEqual(ttl_cache_simulator(cmds), ["foo", "NULL"])

    def test_overlapping_set_calls(self):
        """Overlapping SETs for same key reset TTL from now."""
        cmds = [
            "SET x v1 2", "SLEEP 1", "SET x v2 4", "SLEEP 2", "GET x", "EXIT"
        ]
        self.assertEqual(ttl_cache_simulator(cmds), ["v2"])

    def test_batch_many_keys(self):
        """Handles many keys and their expiry distinctly."""
        cmds = [
            *(f"SET k{i} v{i} {i+1}" for i in range(20)),
            "SLEEP 10",
            *(f"GET k{i}" for i in range(20)),
            "EXIT"
        ]
        expected = ["NULL" if i < 10 else f"v{i}" for i in range(20)]
        self.assertEqual(ttl_cache_simulator(list(cmds)), expected)

    def test_max_key_value_length(self):
        """Max-length keys and values stored and expire properly."""
        k = "K" * 64
        v = "V" * 256
        cmds = [f"SET {k} {v} 3", "GET " + k, "SLEEP 3", "GET " + k, "EXIT"]
        self.assertEqual(ttl_cache_simulator(cmds), [v, "NULL"])

    def test_many_gets_after_expiry(self):
        """Multiple consecutive GETs after expiry all return NULL."""
        cmds = [
            "SET temp v 2", "SLEEP 2",
            "GET temp", "GET temp", "EXIT"
        ]
        self.assertEqual(ttl_cache_simulator(cmds), ["NULL", "NULL"])

    def test_sleep_zero_is_effective(self):
        """SLEEP 0 does not advance virtual time."""
        cmds = [
            "SET a va 2", "SLEEP 0", "GET a", "SLEEP 2", "GET a", "EXIT"
        ]
        self.assertEqual(ttl_cache_simulator(cmds), ["va", "NULL"])

    def test_interleaved_set_sleep_get(self):
        """Test a mix of interleaved operations."""
        cmds = [
            "SET a 1 3", "SLEEP 1",
            "SET b 2 4", "SLEEP 2",
            "GET a", "GET b",   # a expired, b remains
            "SLEEP 2",
            "GET b", "EXIT"
        ]
        self.assertEqual(ttl_cache_simulator(cmds), ["NULL", "2", "NULL"])
