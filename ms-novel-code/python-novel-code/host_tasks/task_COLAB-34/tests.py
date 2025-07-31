# tests
"""Unit tests for the event-driven banking system."""

import unittest
from main import process_bank_transactions


class TestBankAccountSystem(unittest.TestCase):
    """Test suite for bank account operations and event replay."""

    def test_single_deposit(self):
        """Test processing a single deposit."""
        tx = [("deposit", 100, 1)]
        result = process_bank_transactions(tx)
        self.assertEqual(result["final_balance"], 100)
        self.assertEqual(result["transaction_count"], 1)
        self.assertEqual(result["balance_history"], [100])

    def test_single_withdrawal(self):
        """Test a deposit followed by a withdrawal."""
        tx = [("deposit", 200, 1), ("withdraw", 50, 2)]
        result = process_bank_transactions(tx)
        self.assertEqual(result["final_balance"], 150)
        self.assertEqual(result["transaction_count"], 2)
        self.assertEqual(result["balance_history"], [200, 150])

    def test_multiple_deposits(self):
        """Test multiple deposit transactions."""
        tx = [("deposit", 100, 1), ("deposit", 200, 2)]
        result = process_bank_transactions(tx)
        self.assertEqual(result["final_balance"], 300)
        self.assertEqual(result["transaction_count"], 2)

    def test_multiple_withdrawals(self):
        """Test deposit followed by multiple withdrawals."""
        tx = [
            ("deposit", 500, 1),
            ("withdraw", 100, 2),
            ("withdraw", 50, 3)
        ]
        result = process_bank_transactions(tx)
        self.assertEqual(result["final_balance"], 350)
        self.assertEqual(result["balance_history"], [500, 400, 350])

    def test_zero_balance(self):
        """Test when no transactions are provided."""
        tx = []
        result = process_bank_transactions(tx)
        self.assertEqual(result["final_balance"], 0)
        self.assertEqual(result["transaction_count"], 0)
        self.assertEqual(result["balance_history"], [])

    def test_negative_balance(self):
        """Test starting with a withdrawal to get negative balance."""
        tx = [("withdraw", 100, 1)]
        result = process_bank_transactions(tx)
        self.assertEqual(result["final_balance"], -100)

    def test_alternating_transactions(self):
        """Test alternating deposits and withdrawals."""
        tx = [
            ("deposit", 300, 1),
            ("withdraw", 100, 2),
            ("deposit", 200, 3),
            ("withdraw", 50, 4)
        ]
        result = process_bank_transactions(tx)
        self.assertEqual(result["final_balance"], 350)
        self.assertEqual(result["balance_history"], [300, 200, 400, 350])

    def test_event_log_structure(self):
        """Test structure of event log entries."""
        tx = [("deposit", 150, 1)]
        result = process_bank_transactions(tx)
        self.assertIsInstance(result["event_log"], list)
        self.assertEqual(result["event_log"][0]["transaction_id"], 1)
        self.assertEqual(result["event_log"][0]["type"], "deposit")
        self.assertEqual(result["event_log"][0]["amount"], 150)
        self.assertEqual(result["event_log"][0]["resulting_balance"], 150)

    def test_transaction_ids_preserved(self):
        """Test that transaction IDs are preserved."""
        tx = [
            ("deposit", 100, 11),
            ("withdraw", 50, 22),
            ("deposit", 30, 33)
        ]
        result = process_bank_transactions(tx)
        self.assertEqual(
            [e["transaction_id"] for e in result["event_log"]],
            [11, 22, 33]
        )

    def test_negative_deposit(self):
        """Test depositing a negative amount."""
        tx = [("deposit", -100, 1)]
        result = process_bank_transactions(tx)
        self.assertEqual(result["final_balance"], -100)

    def test_negative_withdrawal(self):
        """Test withdrawing a negative amount (effectively deposits)."""
        tx = [("withdraw", -50, 1)]
        result = process_bank_transactions(tx)
        self.assertEqual(result["final_balance"], 50)

    def test_large_amounts(self):
        """Test large deposits and withdrawals."""
        tx = [("deposit", 1_000_000, 1), ("withdraw", 999_999, 2)]
        result = process_bank_transactions(tx)
        self.assertEqual(result["final_balance"], 1)

    def test_duplicate_transaction_ids(self):
        """Test system behavior with duplicate transaction IDs."""
        tx = [
            ("deposit", 100, 1),
            ("withdraw", 50, 1)
        ]
        result = process_bank_transactions(tx)
        self.assertEqual(result["transaction_count"], 2)

    def test_unknown_transaction_type(self):
        """Test exception is raised on unknown transaction type."""
        tx = [("invalid", 100, 1)]
        with self.assertRaises(ValueError):
            process_bank_transactions(tx)

    def test_no_mutation_of_event_log(self):
        """Modifying returned event log doesn't affect internal state."""
        tx = [("deposit", 100, 1)]
        result = process_bank_transactions(tx)
        log1 = result["event_log"]
        log1[0]["amount"] = 999
        result2 = process_bank_transactions(tx)
        self.assertEqual(result2["event_log"][0]["amount"], 100)

    def test_event_count_matches_transaction_count(self):
        """Test event log and transaction count match."""
        tx = [
            ("deposit", 10, 1),
            ("deposit", 20, 2),
            ("withdraw", 5, 3)
        ]
        result = process_bank_transactions(tx)
        self.assertEqual(len(result["event_log"]), 3)
        self.assertEqual(result["transaction_count"], 3)

    def test_balance_history_correctness(self):
        """Test correctness of intermediate balances."""
        tx = [
            ("deposit", 10, 1),
            ("deposit", 20, 2),
            ("withdraw", 5, 3)
        ]
        result = process_bank_transactions(tx)
        self.assertEqual(result["balance_history"], [10, 30, 25])

    def test_order_preservation(self):
        """Test order of transactions in event log."""
        tx = [
            ("deposit", 100, 1),
            ("withdraw", 10, 2),
            ("deposit", 40, 3)
        ]
        result = process_bank_transactions(tx)
        self.assertEqual(
            [e["type"] for e in result["event_log"]],
            ["deposit", "withdraw", "deposit"]
        )

    def test_empty_transaction_list(self):
        """Test result with no input transactions."""
        result = process_bank_transactions([])
        self.assertEqual(result["final_balance"], 0)
        self.assertEqual(result["transaction_count"], 0)
        self.assertEqual(result["event_log"], [])
        self.assertEqual(result["balance_history"], [])

    def test_mixed_zero_and_nonzero(self):
        """Test deposits and withdrawals of zero and nonzero amounts."""
        tx = [
            ("deposit", 0, 1),
            ("deposit", 100, 2),
            ("withdraw", 0, 3),
            ("withdraw", 100, 4)
        ]
        result = process_bank_transactions(tx)
        self.assertEqual(result["final_balance"], 0)
        self.assertEqual(result["transaction_count"], 4)
        self.assertEqual(result["balance_history"], [0, 100, 100, 0])

    def test_repeated_transactions(self):
        """Test processing of repeated deposit transactions."""
        tx = [("deposit", 50, i) for i in range(10)]
        result = process_bank_transactions(tx)
        self.assertEqual(result["final_balance"], 500)
        self.assertEqual(result["transaction_count"], 10)
