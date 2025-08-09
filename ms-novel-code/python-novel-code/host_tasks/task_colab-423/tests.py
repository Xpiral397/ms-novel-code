# tests

"""
Unit tests for job scheduling with timeout, logging, and error handling.
"""

import unittest
import os
import time
import tempfile
from typing import Callable
from pathlib import Path
from main import (
    schedule_jobs,
    default_follow_up_logger,
)


def fast_job() -> int:
    """Returns quickly with a valid result."""
    return 42


def slow_job() -> str:
    """Sleeps for 2 seconds and returns a string."""
    time.sleep(2)
    return "done"


def error_job() -> None:
    """Raises a RuntimeError immediately."""
    raise RuntimeError("job failed")


def non_picklable_job() -> Callable:
    """Returns a lambda (non-picklable)."""
    return lambda x: x


class TestJobScheduler(unittest.TestCase):
    """Test cases for the job scheduler module."""

    def setUp(self) -> None:
        """Create a temporary file for logging follow-ups."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.log_file = os.path.join(self.temp_dir.name, "followup.log")

    def tearDown(self) -> None:
        """Cleanup the temporary directory after tests."""
        self.temp_dir.cleanup()

    def test_fast_job_completes(self) -> None:
        """Fast job should complete successfully."""
        result = schedule_jobs(
            jobs=[("job1", fast_job)],
            timeout=1.0,
            follow_up=default_follow_up_logger,
            log_file=self.log_file,
        )
        self.assertEqual(result[0]["job_id"], "job1")
        self.assertEqual(result[0]["status"], "ok")
        self.assertEqual(result[0]["result"], 42)

    def test_slow_job_times_out(self) -> None:
        """Slow job should be terminated and logged on timeout."""
        result = schedule_jobs(
            jobs=[("job2", slow_job)],
            timeout=0.5,
            follow_up=default_follow_up_logger,
            log_file=self.log_file,
        )
        self.assertEqual(result[0]["status"], "timeout")
        self.assertTrue(Path(self.log_file).exists())

        with open(self.log_file, encoding="utf-8") as f:
            log = f.read()
            self.assertIn("job2", log)
            self.assertIn("timeout", log)

    def test_error_job_captures_exception(self) -> None:
        """Job that raises an exception should be recorded as error."""
        result = schedule_jobs(
            jobs=[("job3", error_job)],
            timeout=1.0,
            follow_up=default_follow_up_logger,
            log_file=self.log_file,
        )
        self.assertEqual(result[0]["status"], "error")
        self.assertIn("RuntimeError", result[0]["error"])

    def test_invalid_timeout_raises(self) -> None:
        """Invalid timeout should raise ValueError."""
        with self.assertRaises(ValueError):
            schedule_jobs(
                jobs=[("job5", fast_job)],
                timeout=0,
                follow_up=default_follow_up_logger,
                log_file=self.log_file,
            )

    def test_empty_job_list_returns_empty(self) -> None:
        """An empty job list should return an empty result list."""
        result = schedule_jobs(
            jobs=[],
            timeout=1.0,
            follow_up=default_follow_up_logger,
            log_file=self.log_file,
        )
        self.assertEqual(result, [])

    def test_invalid_job_format_raises(self) -> None:
        """Invalid job format should raise ValueError."""
        with self.assertRaises(ValueError):
            schedule_jobs(
                jobs=["bad job"],
                timeout=1.0,
                follow_up=default_follow_up_logger,
                log_file=self.log_file,
            )

    def test_follow_up_logger_writes_correct_line(self) -> None:
        """Follow-up logger should write a valid log entry."""
        default_follow_up_logger(
            job_id="job6",
            reason="timeout",
            duration_sec=2.3,
            log_file=self.log_file,
        )
        with open(self.log_file, encoding="utf-8") as f:
            line = f.read()
        self.assertIn("job6", line)
        self.assertIn("timeout", line)

    def test_multiple_jobs_mixed_status(self) -> None:
        """Multiple jobs should return mixed statuses correctly."""
        jobs = [
            ("job8", fast_job),
            ("job9", slow_job),
            ("job10", error_job),
        ]
        result = schedule_jobs(
            jobs=jobs,
            timeout=1.0,
            follow_up=default_follow_up_logger,
            log_file=self.log_file,
        )
        statuses = [r["status"] for r in result]
        self.assertEqual(statuses, ["ok", "timeout", "error"])

    def test_job_duration_accuracy(self) -> None:
        """Job duration should be a positive float."""
        result = schedule_jobs(
            jobs=[("job11", fast_job)],
            timeout=1.0,
            follow_up=default_follow_up_logger,
            log_file=self.log_file,
        )
        duration = result[0]["duration_sec"]
        self.assertIsInstance(duration, float)
        self.assertGreater(duration, 0.0)

    def test_duplicate_job_ids_allowed(self) -> None:
        """Duplicate job IDs are allowed and results preserved in order."""
        jobs = [("job12", fast_job), ("job12", slow_job)]
        result = schedule_jobs(
            jobs=jobs,
            timeout=0.5,
            follow_up=default_follow_up_logger,
            log_file=self.log_file,
        )
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["status"], "ok")
        self.assertEqual(result[1]["status"], "timeout")

    def test_log_file_created_only_on_timeout(self) -> None:
        """Log file should not exist if no timeouts occurred."""
        schedule_jobs(
            jobs=[("job13", fast_job)],
            timeout=1.0,
            follow_up=default_follow_up_logger,
            log_file=self.log_file,
        )
        self.assertFalse(Path(self.log_file).exists())

    def test_custom_follow_up_called_on_timeout(self) -> None:
        """Custom follow-up should be invoked only on timeout."""

        self.called = False

        def mock_follow_up(job_id: str, reason: str,
                           duration_sec: float, log_file: str) -> None:
            self.called = True
            self.assertEqual(job_id, "job14")
            self.assertEqual(reason, "timeout")
            self.assertTrue(duration_sec >= 0.5)

        schedule_jobs(
            jobs=[("job14", slow_job)],
            timeout=0.5,
            follow_up=mock_follow_up,
            log_file=self.log_file,
        )
        self.assertTrue(self.called)
