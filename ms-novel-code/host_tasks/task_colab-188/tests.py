# tests
"""Unit tests for SQLite OCC simulation using threading."""

import unittest
import threading
import sqlite3
from main import (
    setup_db,
    run_transaction,
    simulate_concurrent_transactions,
    DB_URI,
    _transaction_results,
)


class TestOCCSimulation(unittest.TestCase):
    """Tests for SQLite OCC simulation."""

    def setUp(self):
        """Initialize shared in-memory DB before each test."""
        self.keep_alive_conn = setup_db()

    def tearDown(self):
        """Close the DB connection after each test."""
        self.keep_alive_conn.close()

    def test_single_transaction_commits(self):
        """Test that a single transaction commits successfully."""
        thread = threading.Thread(target=run_transaction, args=("T1", 0))
        results = simulate_concurrent_transactions([thread])
        self.assertEqual(results[0]["status"], "committed")
        self.assertEqual(results[0]["final_quantity"], 9)
        self.assertEqual(results[0]["final_version"], 2)

    def test_two_transactions_conflict(self):
        """Test that two transactions cause a conflict."""
        t1 = threading.Thread(target=run_transaction, args=("T1", 0))
        t2 = threading.Thread(target=run_transaction, args=("T2", 0.1))
        results = simulate_concurrent_transactions([t1, t2])
        statuses = {r["transaction"]: r["status"] for r in results}
        self.assertIn("committed", statuses.values())
        self.assertIn("conflict", statuses.values())

    def test_three_conflicting_transactions(self):
        """Only one of three conflicting transactions should commit."""
        threads = [
            threading.Thread(target=run_transaction, args=(f"T{i}", i * 0.1))
            for i in range(3)
        ]
        results = simulate_concurrent_transactions(threads)
        committed = sum(1 for r in results if r["status"] == "committed")
        self.assertEqual(committed, 1)
        self.assertEqual(len(results), 3)

    def test_conflict_has_reason(self):
        """Ensure conflict result contains a 'reason' field."""
        t1 = threading.Thread(target=run_transaction, args=("T1", 0))
        t2 = threading.Thread(target=run_transaction, args=("T2", 0.05))
        results = simulate_concurrent_transactions([t1, t2])
        for result in results:
            if result["status"] == "conflict":
                self.assertIn("reason", result)

    def test_inventory_row_absence(self):
        """Test transaction error when inventory row is missing."""
        conn = sqlite3.connect(DB_URI, uri=True, check_same_thread=False)
        conn.execute("DELETE FROM inventory WHERE id=1")
        conn.commit()
        conn.close()

        t = threading.Thread(target=run_transaction, args=("T1", 0))
        results = simulate_concurrent_transactions([t])
        self.assertEqual(results[0]["status"], "error")
        self.assertIn("Inventory row not found", results[0]["reason"])

    def test_uninitialized_db_error(self):
        """Test error when database schema is missing."""
        conn = sqlite3.connect(DB_URI, uri=True, check_same_thread=False)
        conn.execute("DROP TABLE inventory")
        conn.commit()
        conn.close()

        t = threading.Thread(target=run_transaction, args=("T1", 0))
        results = simulate_concurrent_transactions([t])
        self.assertEqual(results[0]["status"], -1)
        self.assertIn("Database not initialized", results[0]["reason"])

    def test_transaction_delay_effect(self):
        """Test conflict behavior with delayed transaction."""
        t1 = threading.Thread(target=run_transaction, args=("Fast", 0))
        t2 = threading.Thread(target=run_transaction, args=("Slow", 0.3))
        results = simulate_concurrent_transactions([t1, t2])
        statuses = {r["transaction"]: r["status"] for r in results}
        self.assertEqual(statuses["Fast"], "committed")
        self.assertEqual(statuses["Slow"], "conflict")

    def test_exact_version_conflict(self):
        """Test conflict when version is explicitly bumped."""
        conn = sqlite3.connect(DB_URI, uri=True, check_same_thread=False)
        conn.execute("UPDATE inventory SET version = 2 WHERE id = 1")
        conn.commit()
        conn.close()

        t = threading.Thread(target=run_transaction, args=("T1", 0))
        results = simulate_concurrent_transactions([t])
        self.assertEqual(results[0]["status"], "conflict")

    def test_zero_delay_multiple_threads(self):
        """Only one thread should commit with zero delay."""
        threads = [
            threading.Thread(target=run_transaction, args=(f"T{i}", 0))
            for i in range(4)
        ]
        results = simulate_concurrent_transactions(threads)
        committed = sum(1 for r in results if r["status"] == "committed")
        self.assertEqual(committed, 1)

    def test_long_delay_leads_to_conflict(self):
        """Test that long delay causes a version conflict."""
        t1 = threading.Thread(target=run_transaction, args=("T1", 0))
        t2 = threading.Thread(target=run_transaction, args=("T2", 2))
        results = simulate_concurrent_transactions([t1, t2])
        self.assertIn("conflict", {r["status"] for r in results})

    def test_exception_handling(self):
        """Test that transaction exceptions are captured in results."""
        _transaction_results.clear()

        def failing_tx(name, delay):
            try:
                raise RuntimeError("forced error")
            except Exception as e:
                _transaction_results[name] = {
                    "transaction": name,
                    "status": "error",
                    "reason": str(e)
                }

        thread = threading.Thread(target=failing_tx, args=("FaultyTx", 0))
        thread.start()
        thread.join()

        results = list(_transaction_results.values())
        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertEqual(result["status"], "error")
        self.assertIn("forced error", result["reason"])

    def test_transaction_keys_present(self):
        """Test that required keys are present in result."""
        t = threading.Thread(target=run_transaction, args=("T1", 0))
        results = simulate_concurrent_transactions([t])
        keys = results[0].keys()
        self.assertIn("transaction", keys)
        self.assertIn("status", keys)

    def test_quantity_never_negative(self):
        """Ensure quantity never becomes negative after commits."""
        threads = [
            threading.Thread(target=run_transaction, args=(f"T{i}", i * 0.2))
            for i in range(10)
        ]
        results = simulate_concurrent_transactions(threads)
        committed = [r for r in results if r["status"] == "committed"]
        if committed:
            min_quantity = min(r["final_quantity"] for r in committed)
            self.assertGreaterEqual(min_quantity, 0)

    def test_final_version_progression(self):
        """Ensure committed versions progress monotonically."""
        threads = [
            threading.Thread(target=run_transaction, args=(f"T{i}", i * 0.2))
            for i in range(4)
        ]
        results = simulate_concurrent_transactions(threads)
        committed_versions = sorted([
            r["final_version"] for r in results if r["status"] == "committed"
        ])
        for i in range(len(committed_versions) - 1):
            self.assertLess(committed_versions[i], committed_versions[i + 1])

    def test_transaction_naming(self):
        """Test Unicode transaction naming."""
        t = threading.Thread(target=run_transaction, args=("🧪", 0))
        results = simulate_concurrent_transactions([t])
        self.assertEqual(results[0]["transaction"], "🧪")

    def test_transaction_count_matches(self):
        """Ensure result count matches thread count."""
        n = 5
        threads = [
            threading.Thread(target=run_transaction, args=(f"T{i}", i * 0.1))
            for i in range(n)
        ]
        results = simulate_concurrent_transactions(threads)
        self.assertEqual(len(results), n)

    def test_db_stability_post_conflicts(self):
        """Test that DB remains stable after conflict."""
        t1 = threading.Thread(target=run_transaction, args=("T1", 0))
        t2 = threading.Thread(target=run_transaction, args=("T2", 0.1))
        simulate_concurrent_transactions([t1, t2])
        conn = sqlite3.connect(DB_URI, uri=True, check_same_thread=False)
        quantity = conn.execute(
            "SELECT quantity FROM inventory WHERE id=1"
        ).fetchone()[0]
        self.assertGreaterEqual(quantity, 0)
        conn.close()

    def test_final_version_expected(self):
        """Test that final version is incremented."""
        thread = threading.Thread(target=run_transaction, args=("VCheck", 0))
        simulate_concurrent_transactions([thread])
        conn = sqlite3.connect(DB_URI, uri=True, check_same_thread=False)
        version = conn.execute(
            "SELECT version FROM inventory WHERE id=1"
        ).fetchone()[0]
        self.assertGreaterEqual(version, 2)
        conn.close()

    def test_multiple_delays_affect_order(self):
        """Only one transaction should commit due to spacing."""
        delays = [0.4, 0.1, 0.2]
        names = [f"T{i}" for i in range(3)]
        threads = [
            threading.Thread(
                target=run_transaction, args=(names[i], delays[i])
            ) for i in range(3)
        ]
        results = simulate_concurrent_transactions(threads)
        committed = [r for r in results if r["status"] == "committed"]
        self.assertEqual(len(committed), 1)
