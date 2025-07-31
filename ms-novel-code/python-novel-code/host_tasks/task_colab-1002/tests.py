# tests

import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from main import process_webhook_events


def _capture_output(func, *args, **kwargs):
    """Run *func* while capturing stdout; return list(stripped lines)."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        func(*args, **kwargs)
    return [line.strip() for line in buf.getvalue().splitlines()]


class TestProcessWebhookEvents(unittest.TestCase):
    """Unit-tests for `process_webhook_events` as specified in the prompt."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.store_path = os.path.join(self.tmpdir.name, "events.txt")

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_unique_events_first_run(self):
        events = [
            {"event_id": "evt_1", "event_type": "alpha",
                "timestamp": "2025-07-22T08:00:00Z", "payload": {}},
            {"event_id": "evt_2", "event_type": "beta",
                "timestamp": "2025-07-22T08:01:00Z", "payload": {}},
        ]
        out = _capture_output(process_webhook_events, events, self.store_path)
        self.assertEqual(
            out,
            ["Processed event: evt_1", "Processed event: evt_2"],
            "Both unique events should be processed in order.",
        )
        # verify IDs persisted
        with open(self.store_path, encoding="utf-8") as fh:
            self.assertEqual(fh.read().splitlines(), ["evt_1", "evt_2"])

    def test_duplicates_within_single_batch(self):
        events = [
            {"event_id": "dup", "event_type": "x",
                "timestamp": "2025-07-22T08:00:00Z", "payload": {}},
            {"event_id": "dup", "event_type": "x",
                "timestamp": "2025-07-22T08:02:00Z", "payload": {}},
        ]
        out = _capture_output(process_webhook_events, events, self.store_path)
        self.assertEqual(
            out,
            ["Processed event: dup", "Duplicate event skipped: dup"],
            "Second occurrence in same run should be skipped.",
        )

    def test_idempotency_across_runs(self):
        ev = {"event_id": "evt_z", "event_type": "z",
              "timestamp": "2025-07-22T08:00:00Z", "payload": {}}
        _capture_output(process_webhook_events, [ev], self.store_path)
        out = _capture_output(process_webhook_events, [ev], self.store_path)
        self.assertEqual(out, ["Duplicate event skipped: evt_z"])

    def test_storage_file_created_when_missing(self):
        self.assertFalse(Path(self.store_path).exists(),
                         "Pre-condition: storage file absent.")
        _capture_output(
            process_webhook_events,
            [{"event_id": "a", "event_type": "t",
                "timestamp": "2025-07-22T08:00:00Z", "payload": {}}],
            self.store_path,
        )
        self.assertTrue(Path(self.store_path).exists(),
                        "File should be created on first write.")

    def test_empty_input_no_processing(self):
        out = _capture_output(process_webhook_events, [], self.store_path)
        self.assertEqual(out, [], "No events means no output.")
        if Path(self.store_path).exists():
            self.assertEqual(
                Path(self.store_path).read_text(encoding="utf-8"), "")

    def test_malformed_event_skipped(self):
        """Only the well-formed event is processed; malformed one is NOT."""
        events = [
            {"event_id": "good", "event_type": "x",
             "timestamp": "2025-07-22T08:00:00Z", "payload": {}},
            {"event_type": "missing_id"},  # malformed
        ]
        out = _capture_output(process_webhook_events, events, self.store_path)

        processed = [ln for ln in out if ln.startswith("Processed event:")]
        self.assertEqual(
            processed,
            ["Processed event: good"],
            "Malformed event must not be processed (no extra "
            "'Processed event: …' lines are allowed).",
        )

    def test_non_ascii_event_id(self):
        eid = "%@#$42"
        events = [{"event_id": eid, "event_type": "x",
                   "timestamp": "2025-07-22T08:00:00Z", "payload": {}}]
        out = _capture_output(process_webhook_events, events, self.store_path)
        self.assertEqual(out, [f"Processed event: {eid}"])

    def test_max_length_event_id(self):
        eid = "x" * 100
        events = [{"event_id": eid, "event_type": "t",
                   "timestamp": "2025-07-22T08:00:00Z", "payload": {}}]
        out = _capture_output(process_webhook_events, events, self.store_path)
        self.assertEqual(out, [f"Processed event: {eid}"])

    def test_corrupted_storage_file_recovery(self):
        # pre-corrupt with random bytes & blank lines
        with open(self.store_path, "wb") as fh:
            fh.write(b"bad\xffline\n\n")
        events = [{"event_id": "fresh", "event_type": "a",
                   "timestamp": "2025-07-22T08:00:00Z", "payload": {}}]
        out = _capture_output(process_webhook_events, events, self.store_path)
        self.assertIn("Processed event: fresh", out[0])

    def test_large_batch_performance_integrity(self):
        events = [
            {"event_id": f"id_{i}", "event_type": "bulk",
                "timestamp": "2025-07-22T08:00:00Z", "payload": {}}
            for i in range(1_000)
        ]
        out = _capture_output(process_webhook_events, events, self.store_path)
        # first and last lines sanity-check
        self.assertEqual(out[0], "Processed event: id_0")
        self.assertEqual(out[-1], "Processed event: id_999")
        self.assertEqual(
            len(out), 1_000, "Every unique event should be processed once.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
