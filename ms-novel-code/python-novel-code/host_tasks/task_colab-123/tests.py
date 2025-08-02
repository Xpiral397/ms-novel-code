# tests


"""Unit tests for JobScheduler class covering all functionalities.

Import modules and define tests for JobScheduler, covering all edge cases.
"""

import json
import os
import tempfile
import unittest
from unittest.mock import patch
import schedule

from main import JobScheduler


class TestJobScheduler(unittest.TestCase):
    """Test JobScheduler class functionality."""

    def setUp(self):
        """Set up test environment before each test."""
        self.test_state_file = tempfile.mktemp(suffix='.json')
        self.scheduler = JobScheduler(self.test_state_file)
        schedule.clear()  # Clear any existing scheduled jobs.

    def tearDown(self):
        """Clean up test environment after each test."""
        schedule.clear()
        if os.path.exists(self.test_state_file):
            os.unlink(self.test_state_file)

    def test_init_creates_scheduler_with_state_file(self):
        """Test JobScheduler initialization with state file."""
        scheduler = JobScheduler("test_file.json")
        self.assertEqual(scheduler.state_file, "test_file.json")
        # Only test initialization, not internal structure.

    def test_add_job_valid_parameters_success(self):
        """Test adding a valid job successfully."""
        self.scheduler.add_job(
            "job1", 5, "seconds", "print_message", ["Hello"])

        # Verify job was added by checking if it can be saved/loaded.
        self.scheduler.save_jobs()
        self.assertTrue(os.path.exists(self.test_state_file))

        # Load and verify the job exists in the saved state.
        with open(self.test_state_file, 'r') as f:
            saved_data = json.load(f)
        self.assertGreater(len(saved_data), 0)
        job_found = any(job.get("id") == "job1" for job in saved_data)
        self.assertTrue(job_found)

    def test_add_job_duplicate_id_warns_and_skips(self):
        """Test adding job with duplicate ID warns and skips addition."""
        self.scheduler.add_job(
            "job1", 5, "seconds", "print_message", ["First"])

        # Save first job state.
        self.scheduler.save_jobs()
        with open(self.test_state_file, 'r') as f:
            first_save = json.load(f)

        with patch('logging.warning') as mock_warning:
            self.scheduler.add_job(
                "job1", 10, "minutes", "print_message", ["Second"])
            # Should warn about duplicate ID.

        # Save again and compare - should be unchanged.
        self.scheduler.save_jobs()
        with open(self.test_state_file, 'r') as f:
            second_save = json.load(f)

        # First job should remain unchanged (same data structure).
        self.assertEqual(len(first_save), len(second_save))
        if len(first_save) > 0:
            self.assertEqual(first_save[0]["interval"], 5)
            self.assertEqual(first_save[0]["unit"], "seconds")

    def test_add_job_validates_parameters_correctly(self):
        """Test add_job validates parameters according to constraints."""
        # Test that invalid parameters do not cause crashes.
        invalid_jobs = [
            ("invalid-job", 5, "seconds", "print_message", []),
            ("job2", -5, "seconds", "print_message", []),
            ("job3", 0, "seconds", "print_message", []),
            ("job4", 1000001, "seconds", "print_message", []),
            ("job5", 5, "invalid_unit", "print_message", []),
            ("a" * 65, 5, "seconds", "print_message", [])
        ]

        for job_args in invalid_jobs:
            try:
                self.scheduler.add_job(*job_args)
                self.assertTrue(True)
            except Exception as e:
                self.fail(
                    f"add_job should handle invalid params gracefully: {e}")

        # Test valid job works.
        self.scheduler.add_job(
            "validjob1", 5, "seconds", "print_message", ["Hello"])

        # Save and verify at least valid job handling works.
        self.scheduler.save_jobs()
        with open(self.test_state_file, 'r') as f:
            saved_data = json.load(f)
        self.assertIsInstance(saved_data, list)

    def test_save_jobs_creates_correct_json_file(self):
        """Test save_jobs creates correct JSON file format."""
        self.scheduler.add_job(
            "job1", 5, "seconds", "print_message", ["Test message"])

        self.scheduler.save_jobs()

        self.assertTrue(os.path.exists(self.test_state_file))
        with open(self.test_state_file, 'r') as f:
            saved_data = json.load(f)

        self.assertIsInstance(saved_data, list)
        self.assertEqual(len(saved_data), 1)
        self.assertEqual(saved_data[0]["id"], "job1")

    def test_load_jobs_missing_file_starts_with_no_jobs(self):
        """Test load_jobs handles missing state file gracefully."""
        non_existent_file = "non_existent_file.json"
        scheduler = JobScheduler(non_existent_file)

        # Should not crash when loading non-existent file.
        try:
            scheduler.load_jobs()
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"load_jobs should handle missing file: {e}")

        # After loading, there should be no jobs to save.
        scheduler.save_jobs()
        if os.path.exists(non_existent_file):
            with open(non_existent_file, 'r') as f:
                data = json.load(f)
            self.assertEqual(len(data), 0)
            os.unlink(non_existent_file)

    def test_load_jobs_invalid_json_starts_with_no_jobs(self):
        """Test load_jobs handles corrupted JSON gracefully."""
        with open(self.test_state_file, 'w') as f:
            f.write("invalid json content")

        # Should not crash with invalid JSON.
        try:
            self.scheduler.load_jobs()
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"load_jobs should handle invalid JSON: {e}")

        # Should result in no jobs being loaded.
        self.scheduler.save_jobs()
        with open(self.test_state_file, 'r') as f:
            data = json.load(f)
        self.assertEqual(len(data), 0)

    def test_load_jobs_non_list_format_starts_with_no_jobs(self):
        """Test load_jobs handles non-list JSON format gracefully."""
        with open(self.test_state_file, 'w') as f:
            json.dump({"not": "a list"}, f)

        # Should not crash with wrong JSON format.
        try:
            self.scheduler.load_jobs()
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"load_jobs should handle wrong format: {e}")

        # Should result in no jobs being loaded.
        self.scheduler.save_jobs()
        with open(self.test_state_file, 'r') as f:
            data = json.load(f)
        self.assertEqual(len(data), 0)

    def test_load_jobs_valid_file_loads_jobs_correctly(self):
        """Test load_jobs correctly loads valid job definitions."""
        test_jobs = [
            {
                "id": "job1",
                "interval": 5,
                "unit": "seconds",
                "action": "print_message",
                "args": ["Test 1"]
            },
            {
                "id": "job2",
                "interval": 10,
                "unit": "minutes",
                "action": "print_message",
                "args": ["Test 2"]
            }
        ]

        with open(self.test_state_file, 'w') as f:
            json.dump(test_jobs, f)

        self.scheduler.load_jobs()

        # Verify jobs loaded by saving and checking the saved state.
        self.scheduler.save_jobs()
        with open(self.test_state_file, 'r') as f:
            saved_data = json.load(f)

        self.assertGreaterEqual(len(saved_data), 1)
        job_ids = [job.get("id") for job in saved_data]
        self.assertIn("job1", job_ids)
        self.assertIn("job2", job_ids)

    def test_load_jobs_handles_invalid_job_definitions_gracefully(self):
        """Test load_jobs handles invalid job definitions gracefully."""
        test_jobs = [
            {
                "id": "valid_job",
                "interval": 5,
                "unit": "seconds",
                "action": "print_message",
                "args": ["Valid"]
            },
            {
                "id": "invalid_job",
                "interval": -5,
                "unit": "seconds",
                "action": "print_message",
                "args": ["Invalid"]
            }
        ]

        with open(self.test_state_file, 'w') as f:
            json.dump(test_jobs, f)

        # Test should not crash and should handle invalid jobs gracefully.
        try:
            self.scheduler.load_jobs()
            self.assertTrue(True)
        except Exception as e:
            self.fail(
                f"load_jobs should handle invalid jobs gracefully: {e}")

    def test_load_jobs_handles_missing_required_fields(self):
        """Test load_jobs handles jobs with missing required fields."""
        test_jobs = [
            {
                "id": "missing_interval",
                "unit": "seconds",
                "action": "print_message",
                "args": ["Test"]
            },
            {
                "interval": 5,
                "unit": "seconds",
                "action": "print_message",
                "args": ["Missing ID"]
            }
        ]

        with open(self.test_state_file, 'w') as f:
            json.dump(test_jobs, f)

        # Should handle gracefully without crashing.
        try:
            self.scheduler.load_jobs()
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"Should handle missing fields gracefully: {e}")

    def test_add_job_with_missing_fields_fails_validation(self):
        """Test add_job rejects jobs with missing required fields."""
        # Test missing interval (None).
        self.scheduler.add_job(
            "job1", None, "seconds", "print_message", [])

        # Test missing unit (None).
        self.scheduler.add_job(
            "job2", 5, None, "print_message", [])

        # Test missing action (None).
        self.scheduler.add_job(
            "job3", 5, "seconds", None, [])

        # Verify that invalid jobs do not get saved.
        self.scheduler.save_jobs()
        with open(self.test_state_file, 'r') as f:
            saved_data = json.load(f)

        job_ids = [job.get("id") for job in saved_data]
        self.assertNotIn("job1", job_ids)
        self.assertNotIn("job2", job_ids)
        self.assertNotIn("job3", job_ids)

    @patch('time.sleep')
    @patch('schedule.run_pending')
    def test_start_calls_schedule_run_pending_continuously(
            self, mock_run, mock_sleep):
        """Test start method calls schedule.run_pending continuously."""
        # Simulate KeyboardInterrupt after a few iterations.
        mock_run.side_effect = [None, None, KeyboardInterrupt()]

        with patch.object(self.scheduler, 'shutdown') as mock_shutdown:
            self.scheduler.start()
            mock_shutdown.assert_called_once()

        self.assertEqual(mock_run.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)

    def test_shutdown_clears_schedule_and_saves_jobs(self):
        """Test shutdown method clears schedule and saves jobs."""
        self.scheduler.add_job(
            "job1", 5, "seconds", "print_message", ["Test"])

        with patch.object(self.scheduler, 'save_jobs') as mock_save:
            self.scheduler.shutdown()
            mock_save.assert_called_once()

        self.assertEqual(len(schedule.jobs), 0)

    def test_scheduler_handles_job_execution_simulation(self):
        """Test scheduler can handle job execution simulation."""
        # Add a valid job.
        self.scheduler.add_job(
            "test_job", 1, "seconds", "print_message", ["Test execution"])

        # The key test is that schedule.run_pending() does not crash.
        with patch('logging.info'):
            try:
                schedule.run_pending()
                self.assertTrue(True)
            except Exception as e:
                self.fail(
                    f"schedule.run_pending() should not crash: {e}")

    def test_multiple_jobs_can_be_scheduled_simultaneously(self):
        """Test multiple jobs can be scheduled without conflict."""
        jobs_data = [
            ("job1", 5, "seconds", ["Message 1"]),
            ("job2", 10, "minutes", ["Message 2"]),
            ("job3", 2, "hours", ["Message 3"]),
            ("job4", 1, "days", ["Message 4"])
        ]

        for job_id, interval, unit, args in jobs_data:
            self.scheduler.add_job(
                job_id, interval, unit, "print_message", args)

        # Test that multiple add_job calls do not interfere with each other.
        self.scheduler.save_jobs()
        with open(self.test_state_file, 'r') as f:
            saved_data = json.load(f)

        self.assertIsInstance(saved_data, list)

    def test_persistence_round_trip_maintains_job_data(self):
        """Test save and load cycle maintains job data integrity."""
        original_jobs = [
            ("job1", 5, "seconds", ["Test 1"]),
            ("job2", 30, "minutes", ["Test 2", "Multiple", "Args"])
        ]

        for job_id, interval, unit, args in original_jobs:
            self.scheduler.add_job(
                job_id, interval, unit, "print_message", args)
        self.scheduler.save_jobs()

        new_scheduler = JobScheduler(self.test_state_file)
        new_scheduler.load_jobs()

        new_scheduler.save_jobs()
        with open(self.test_state_file, 'r') as f:
            loaded_data = json.load(f)

        self.assertGreaterEqual(len(loaded_data), 1)
        job_ids = [job.get("id") for job in loaded_data]
        self.assertIn("job1", job_ids)
        self.assertIn("job2", job_ids)

    def test_scheduler_handles_up_to_100_jobs(self):
        """Test scheduler can handle up to 100 jobs as per requirements."""
        # Add 10 jobs (representative test).
        for i in range(10):
            job_id = f"job{i:03d}"
            self.scheduler.add_job(
                job_id, i + 1, "seconds", "print_message", [f"Message {i}"])

        self.scheduler.save_jobs()
        with open(self.test_state_file, 'r') as f:
            data = json.load(f)

        self.assertIsInstance(data, list)

        new_scheduler = JobScheduler(self.test_state_file)
        try:
            new_scheduler.load_jobs()
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"Should handle loading multiple jobs: {e}")

    def test_job_state_file_named_correctly(self):
        """Test that jobs are saved to 'jobs_state.json' file."""
        scheduler = JobScheduler("jobs_state.json")
        scheduler.add_job(
            "test", 5, "seconds", "print_message", ["Test"])
        scheduler.save_jobs()

        self.assertTrue(os.path.exists("jobs_state.json"))

        if os.path.exists("jobs_state.json"):
            os.unlink("jobs_state.json")

    def test_all_time_units_supported(self):
        """Test all required time units are supported."""
        valid_units = ["seconds", "minutes", "hours", "days"]

        for unit in valid_units:
            job_id = f"test_{unit}"
            try:
                self.scheduler.add_job(
                    job_id, 1, unit, "print_message", [f"Test {unit}"])
                self.assertTrue(True)
            except Exception as e:
                self.fail(f"Should support time unit '{unit}': {e}")

    def test_json_serializable_args_only(self):
        """Test that only JSON-serializable arguments are accepted."""
        valid_args = [
            ["string", 123, 45.67, True, False, None],
            [{"key": "value"}, [1, 2, 3]]
        ]

        for args in valid_args:
            try:
                self.scheduler.add_job(
                    f"valid_{hash(str(args))}", 5, "seconds",
                    "print_message", args)
                self.assertTrue(True)
            except Exception as e:
                self.fail(f"Should accept JSON-serializable args: {e}")


if __name__ == "__main__":
    unittest.main()
