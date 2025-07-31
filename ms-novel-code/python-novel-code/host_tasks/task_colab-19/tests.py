# tests

"""
Unit tests for secure multi-tenant data layer.

Verifies bootstrap and query behavior against the P/R specification.
"""

import unittest
import main
from main import bootstrap, query


class TestMultiTenant(unittest.TestCase):
    """Tests for secure multi-tenant data layer."""

    def setUp(self):
        """Clear internal store before each test."""
        main._store = None

    def test_uninitialized_query(self):
        """Query before bootstrap must raise RuntimeError."""
        with self.assertRaises(RuntimeError):
            query({'tenant_id': 'any'})

    def test_duplicate_tenants(self):
        """Bootstrap with duplicate IDs must raise ValueError."""
        with self.assertRaises(ValueError):
            bootstrap(['a', 'a'])

    def test_basic_partitioning(self):
        """Each tenant sees exactly 50 of its own records."""
        bootstrap(['alpha', 'beta'], rng_seed=123)
        alpha_ctx = {'tenant_id': 'alpha'}
        beta_ctx = {'tenant_id': 'beta'}

        a_records = query(alpha_ctx)
        b_records = query(beta_ctx)

        self.assertEqual(len(a_records), 50)
        self.assertEqual(len(b_records), 50)
        for rec in a_records:
            self.assertEqual(rec['tenant_id'], 'alpha')
        for rec in b_records:
            self.assertEqual(rec['tenant_id'], 'beta')

    def test_invalid_range(self):
        """value_min > value_max must raise ValueError."""
        bootstrap(['tenant'], rng_seed=0)
        with self.assertRaises(ValueError):
            query({'tenant_id': 'tenant'},
                  value_min=500, value_max=100)

    def test_missing_tenant_key(self):
        """Missing tenant_id in context must raise KeyError."""
        bootstrap(['x'], rng_seed=1)
        with self.assertRaises(KeyError):
            query({'user': 'x'})

    def test_unknown_tenant(self):
        """Unknown tenant_id must raise KeyError."""
        bootstrap(['x'], rng_seed=1)
        with self.assertRaises(KeyError):
            query({'tenant_id': 'y'})

    def test_empty_results(self):
        """Non-overlapping range yields empty list."""
        bootstrap(['e'], rng_seed=5)
        results = query({'tenant_id': 'e'},
                        value_min=1000, value_max=2000)
        self.assertEqual(results, [])

    def test_min_only_filter(self):
        """Only lower bound filters records correctly."""
        bootstrap(['t'], rng_seed=7)
        results = query({'tenant_id': 't'}, value_min=500)
        for rec in results:
            self.assertGreaterEqual(rec['value'], 500)

    def test_max_only_filter(self):
        """Only upper bound filters records correctly."""
        bootstrap(['t'], rng_seed=7)
        results = query({'tenant_id': 't'}, value_max=500)
        for rec in results:
            self.assertLessEqual(rec['value'], 500)

    def test_reproducible_randomness(self):
        """Same seed must yield identical datasets."""
        bootstrap(['r'], rng_seed=9)
        first = query({'tenant_id': 'r'})
        bootstrap(['r'], rng_seed=9)
        second = query({'tenant_id': 'r'})
        self.assertEqual(first, second)

    def test_bootstrap_reset(self):
        """Bootstrap must replace old data completely."""
        bootstrap(['a'], rng_seed=42)
        _ = query({'tenant_id': 'a'})
        bootstrap(['b'], rng_seed=42)
        with self.assertRaises(KeyError):
            query({'tenant_id': 'a'})


if __name__ == '__main__':
    unittest.main()
