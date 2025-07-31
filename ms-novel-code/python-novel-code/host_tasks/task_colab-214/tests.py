# tests

"""Minimal unit tests for process_message_pipeline."""

import unittest

from main import process_message_pipeline


class TestProcessMessagePipeline(unittest.TestCase):
    """Minimal tests for process_message_pipeline."""

    def test_success_and_chain_order(self):
        """Success and dependency chain order."""
        messages = [
            {
                "id": "A",
                "type": "DATA",
                "payload": {"content": "a", "checksum": "c"},
                "dependencies": [],
            },
            {
                "id": "B",
                "type": "DATA",
                "payload": {"content": "b", "checksum": "c"},
                "dependencies": ["A"],
            },
            {
                "id": "C",
                "type": "CONTROL",
                "payload": {"command": "go", "target": "B"},
                "dependencies": ["B"],
            },
        ]
        result = process_message_pipeline(messages)
        self.assertEqual([r["id"] for r in result], ["A", "B", "C"])
        self.assertTrue(all(r["status"] == "SUCCESS" for r in result))
        self.assertEqual(result[2]["result"], {"command_status": "completed"})

    def test_circular_dependency(self):
        """Circular dependencies are FAILED."""
        messages = [
            {"id": "A", "type": "DATA", "payload": {}, "dependencies": ["B"]},
            {"id": "B", "type": "DATA", "payload": {}, "dependencies": ["A"]},
            {"id": "C", "type": "DATA", "payload": {}, "dependencies": ["B"]},
        ]
        result = process_message_pipeline(messages)
        self.assertTrue(all(r["status"] == "FAILED" for r in result))

    def test_nonexistent_dependency(self):
        """Missing dependency is SKIPPED."""
        messages = [
            {
                "id": "A2",
                "type": "DATA",
                "payload": {"content": "abc", "checksum": "xyz"},
                "dependencies": ["NOPE"],
            }
        ]
        result = process_message_pipeline(messages)
        self.assertEqual(result[0]["status"], "SKIPPED")

    def test_dependency_on_failed_message(self):
        """Dependency on failed message is FAILED."""
        messages = [
            {"id": "A", "type": "DATA", "payload": {}, "dependencies": ["A"]},
            {
                "id": "B",
                "type": "CONTROL",
                "payload": {"command": "go", "target": "A"},
                "dependencies": ["A"],
            },
        ]
        result = process_message_pipeline(messages)
        msgA = next(r for r in result if r["id"] == "A")
        msgB = next(r for r in result if r["id"] == "B")
        self.assertEqual(msgA["status"], "FAILED")
        self.assertEqual(msgB["status"], "FAILED")

    def test_missing_payload_field(self):
        """DATA missing required fields is FAILED."""
        messages = [
            {
                "id": "M1",
                "type": "DATA",
                "payload": {"checksum": "xyz"},
                "dependencies": [],
            }
        ]
        result = process_message_pipeline(messages)
        self.assertEqual(result[0]["status"], "FAILED")

    def test_unknown_message_type(self):
        """Unknown type is SKIPPED."""
        messages = [
            {
                "id": "X1",
                "type": "UNKNOWN",
                "payload": {},
                "dependencies": []
            }
        ]
        result = process_message_pipeline(messages)
        self.assertEqual(result[0]["status"], "SKIPPED")

    def test_duplicate_message_ids(self):
        """Only first duplicate ID is processed."""
        messages = [
            {
                "id": "DUP",
                "type": "DATA",
                "payload": {"content": "a", "checksum": "b"},
                "dependencies": [],
            },
            {
                "id": "DUP",
                "type": "CONTROL",
                "payload": {"command": "c", "target": "DUP"},
                "dependencies": ["DUP"],
            },
        ]
        result = process_message_pipeline(messages)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "DUP")
        self.assertEqual(result[0]["status"], "SUCCESS")

    def test_empty_input(self):
        """Empty input returns empty list."""
        self.assertEqual(process_message_pipeline([]), [])

    def test_complex_valid_dag(self):
        """Valid DAG of dependencies is SUCCESS."""
        messages = [
            {
                "id": "D",
                "type": "DATA",
                "payload": {"content": "d", "checksum": "dchk"},
                "dependencies": ["B", "C"],
            },
            {
                "id": "C",
                "type": "DATA",
                "payload": {"content": "c", "checksum": "cchk"},
                "dependencies": ["A"],
            },
            {
                "id": "B",
                "type": "DATA",
                "payload": {"content": "b", "checksum": "bchk"},
                "dependencies": ["A"],
            },
            {
                "id": "A",
                "type": "DATA",
                "payload": {"content": "a", "checksum": "achk"},
                "dependencies": [],
            },
        ]
        result = process_message_pipeline(messages)
        self.assertEqual(len(result), 4)
        self.assertTrue(all(r["status"] == "SUCCESS" for r in result))

    def test_processor_chain_stops_on_failure(self):
        """Processor chain stops on failure."""
        messages = [
            {
                "id": "M1",
                "type": "DATA",
                "payload": {},
                "dependencies": []
            }
        ]
        result = process_message_pipeline(messages)
        self.assertEqual(result[0]["status"], "FAILED")
        self.assertEqual(len(result[0]["processors"]), 1)

    def test_basic_data_message(self):
        """Basic DATA message is SUCCESS."""
        messages = [
            {
                "id": "A1",
                "type": "DATA",
                "payload": {"content": "abc", "checksum": "xyz"},
                "dependencies": [],
            }
        ]
        result = process_message_pipeline(messages)
        self.assertEqual(result[0]["status"], "SUCCESS")
        self.assertEqual(result[0]["result"],
                         {"content": "ABC", "validated": True})

    def test_control_message_with_dependency(self):
        """CONTROL message with dependency is SUCCESS."""
        messages = [
            {
                "id": "A1",
                "type": "DATA",
                "payload": {"content": "abc", "checksum": "xyz"},
                "dependencies": [],
            },
            {
                "id": "B1",
                "type": "CONTROL",
                "payload": {"command": "run", "target": "A1"},
                "dependencies": ["A1"],
            },
        ]
        result = process_message_pipeline(messages)
        self.assertEqual(result[1]["status"], "SUCCESS")
        self.assertEqual(result[1]["result"], {"command_status": "completed"})

    def test_status_message(self):
        """STATUS message is SUCCESS."""
        messages = [
            {
                "id": "S1",
                "type": "STATUS",
                "payload": {"info": "ok"},
                "dependencies": []
            }
        ]
        result = process_message_pipeline(messages)
        self.assertEqual(result[0]["status"], "SUCCESS")
        self.assertEqual(result[0]["result"], {"info": "ok"})

    def test_processor_chain_stops_on_failure_2(self):
        """Processor chain stops on non-string content."""
        messages = [
            {
                "id": "F1",
                "type": "DATA",
                "payload": {"content": 123, "checksum": "xyz"},
                "dependencies": [],
            }
        ]
        result = process_message_pipeline(messages)
        self.assertEqual(result[0]["status"], "FAILED")
        self.assertEqual(len(result[0]["processors"]), 2)

    def test_max_boundary(self):
        """Max boundary of 100 messages is SUCCESS."""
        messages = [
            {
                "id": f"ID{i}",
                "type": "DATA",
                "payload": {"content": str(i), "checksum": "c"},
                "dependencies": [],
            }
            for i in range(100)
        ]
        result = process_message_pipeline(messages)
        self.assertEqual(len(result), 100)
        self.assertTrue(all(r["status"] == "SUCCESS" for r in result))

    def test_over_max_boundary(self):
        """Over max boundary returns empty list."""
        messages = [
            {
                "id": f"ID{i}",
                "type": "DATA",
                "payload": {"content": str(i), "checksum": "c"},
                "dependencies": [],
            }
            for i in range(101)
        ]
        result = process_message_pipeline(messages)
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
