# tests

import unittest
import sqlite3
import re
import datetime

from main import setup_and_track_changes


class TestSetupAndTrackChanges(unittest.TestCase):
    """Comprehensive unit tests for the setup_and_track_changes function."""

    _TS_REGEX = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")

    def _check_timestamps(self, logs):
        """Assert each timestamp is ISO‑8601 and logs are chronological."""
        parsed = []
        for row in logs:
            self.assertRegex(row[5], self._TS_REGEX, "Timestamp format invalid")
            parsed.append(datetime.datetime.fromisoformat(row[5]))
        # Non‑decreasing order preserves audit chronology
        self.assertEqual(parsed, sorted(parsed), "Timestamps out of order")

    def test_insert_update_delete_logging(self):
        """Happy‑path: INSERT ➔ UPDATE ➔ DELETE for a single row."""
        ops = [
            ("INSERT", (1, "Alice", "Engineer")),
            ("UPDATE", (1, "Alicia", "Senior Engineer")),
            ("DELETE", (1,)),
        ]
        logs = setup_and_track_changes(ops)

        self.assertEqual(len(logs), 3)
        self.assertEqual([r[1] for r in logs], ["INSERT", "UPDATE", "DELETE"])
        self.assertEqual([r[2] for r in logs], [1, 1, 1])

        self.assertEqual(logs[1][3:5], ("Alicia", "Senior Engineer"))
        self.assertEqual(logs[2][3:5], ("Alicia", "Senior Engineer"))

        self._check_timestamps(logs)

    def test_partial_update_role_only(self):
        """UPDATE that changes only the role keeps the existing name."""
        ops = [
            ("INSERT", (1, "Alice", "Engineer")),
            ("UPDATE", (1, None, "Lead Engineer")),
        ]
        logs = setup_and_track_changes(ops)

        self.assertEqual(len(logs), 2)
        self.assertEqual(logs[1][1], "UPDATE")
        self.assertEqual(logs[1][3], "Alice")
        self.assertEqual(logs[1][4], "Lead Engineer")
        self._check_timestamps(logs)

    def test_partial_update_name_only(self):
        """UPDATE that changes only the name keeps the existing role."""
        ops = [
            ("INSERT", (1, "Alice", "Engineer")),
            ("UPDATE", (1, "Alicia", None)),
        ]
        logs = setup_and_track_changes(ops)

        self.assertEqual(len(logs), 2)
        self.assertEqual(logs[1][3], "Alicia")
        self.assertEqual(logs[1][4], "Engineer")
        self._check_timestamps(logs)

    def test_update_nonexistent_employee(self):
        """Updating a missing row must leave the audit untouched."""
        ops = [
            ("INSERT", (1, "Alice", "Engineer")),
            ("UPDATE", (99, "Ghost", "Phantom")),
        ]
        logs = setup_and_track_changes(ops)
        self.assertEqual(len(logs), 1)

    def test_delete_nonexistent_employee(self):
        """Deleting a missing row must leave the audit untouched."""
        ops = [
            ("INSERT", (1, "Alice", "Engineer")),
            ("DELETE", (99,)),
        ]
        logs = setup_and_track_changes(ops)
        self.assertEqual(len(logs), 1)

    def test_duplicate_insert_error(self):
        """Inserting the same primary‑key twice should raise IntegrityError."""
        ops = [
            ("INSERT", (1, "Alice", "Engineer")),
            ("INSERT", (1, "Bob", "Manager")),
        ]
        with self.assertRaises(sqlite3.IntegrityError):
            setup_and_track_changes(ops)

    def test_prevent_duplicate_consecutive_logs(self):
        """
        Two identical UPDATEs in a row must yield
        only one audit entry for the UPDATE action.
        """
        ops = [
            ("INSERT", (1, "Alice", "Engineer")),
            ("UPDATE", (1, None, "Engineer II")),
            ("UPDATE", (1, None, "Engineer II")),
        ]
        logs = setup_and_track_changes(ops)
        self.assertEqual(len(logs), 2)
        self.assertEqual([r[1] for r in logs], ["INSERT", "UPDATE"])

    def test_timestamp_format_and_order(self):
        """All timestamps should be ISO‑8601 and in ascending order."""
        ops = [
            ("INSERT", (1, "Alice", "Engineer")),
            ("UPDATE", (1, "Alicia", "Lead Engineer")),
            ("DELETE", (1,)),
        ]
        logs = setup_and_track_changes(ops)
        self._check_timestamps(logs)

    def test_skip_update_no_changes(self):
        """UPDATE with both new_name and new_role as None is a no‑op."""
        ops = [
            ("INSERT", (1, "Alice", "Engineer")),
            ("UPDATE", (1, None, None)),
        ]
        logs = setup_and_track_changes(ops)
        self.assertEqual(len(logs), 1)

    def test_multiple_inserts_logging_order(self):
        """Multiple INSERTs must be logged in the order executed."""
        ops = [
            ("INSERT", (1, "Alice", "Engineer")),
            ("INSERT", (2, "Bob", "Manager")),
            ("INSERT", (3, "Charlie", "Analyst")),
        ]
        logs = setup_and_track_changes(ops)
        self.assertEqual(len(logs), 3)
        self.assertEqual([r[2] for r in logs], [1, 2, 3])
        self.assertEqual([r[1] for r in logs], ["INSERT"] * 3)
        self._check_timestamps(logs)

    def test_update_trailing_whitespace_is_logged(self):
        """UPDATE with whitespace/case change should still be logged."""
        ops = [
            ("INSERT", (1, "Alice", "Engineer")),
            ("UPDATE", (1, "Alice", "Engineer ")),
        ]
        logs = setup_and_track_changes(ops)
        self.assertEqual(len(logs), 2)
        self.assertEqual(logs[1][1], "UPDATE")

    def test_update_after_delete_is_ignored(self):
        """UPDATE after DELETE should not log anything."""
        ops = [
            ("INSERT", (1, "Alice", "Engineer")),
            ("DELETE", (1,)),
            ("UPDATE", (1, "Ghost", "Phantom")),
        ]
        logs = setup_and_track_changes(ops)
        self.assertEqual(len(logs), 2)
        self.assertEqual([r[1] for r in logs], ["INSERT", "DELETE"])

    def test_redundant_delete_is_ignored(self):
        """Second DELETE on same ID should not log again."""
        ops = [
            ("INSERT", (1, "Alice", "Engineer")),
            ("DELETE", (1,)),
            ("DELETE", (1,)),
        ]
        logs = setup_and_track_changes(ops)
        self.assertEqual(len(logs), 2)
        self.assertEqual([r[1] for r in logs], ["INSERT", "DELETE"])
