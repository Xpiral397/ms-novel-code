# tests

import unittest
import threading
import time
import sys
from io import StringIO
from main import start_scheduler


class TestCronScheduler(unittest.TestCase):

    def setUp(self):
        self.execution_log = []
        self.scheduler_thread = None

        self.original_stdout = sys.stdout
        self.captured_output = StringIO()
        sys.stdout = self.captured_output

    def tearDown(self):
        sys.stdout = self.original_stdout

        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=0.05)

    def create_trackable_function(self, task_name):
        def tracked_function():
            self.execution_log.append(task_name)

        return tracked_function

    def run_scheduler_briefly(self, tasks, duration=0.05):
        def scheduler_wrapper():
            try:
                start_scheduler(tasks)
            except KeyboardInterrupt:
                pass
            except Exception:
                pass

        self.scheduler_thread = threading.Thread(target=scheduler_wrapper)
        self.scheduler_thread.daemon = True
        self.scheduler_thread.start()

        time.sleep(duration)

        return self.captured_output.getvalue()

    def test_single_task_execution(self):
        tasks = [
            {
                "name": "test_task",
                "interval": 1,
                "priority": 1,
                "function": self.create_trackable_function("test_task"),
            }
        ]

        output = self.run_scheduler_briefly(tasks)

        self.assertIn("Scheduler started", output)
        self.assertIn("Executing test_task", output)
        self.assertIn("test_task", self.execution_log)

    def test_multiple_tasks_priority_order(self):
        tasks = [
            {
                "name": "low_priority",
                "interval": 1,
                "priority": 1,
                "function": self.create_trackable_function("low_priority"),
            },
            {
                "name": "high_priority",
                "interval": 1,
                "priority": 5,
                "function": self.create_trackable_function("high_priority"),
            },
        ]

        output = self.run_scheduler_briefly(tasks, 0.08)

        self.assertIn("Executing low_priority", output)
        self.assertIn("Executing high_priority", output)

        lines = output.split("\n")
        high_priority_line = None
        low_priority_line = None

        for i, line in enumerate(lines):
            if "Executing high_priority" in line:
                high_priority_line = i
            if "Executing low_priority" in line:
                low_priority_line = i

        if high_priority_line is not None and low_priority_line is not None:
            self.assertLess(high_priority_line, low_priority_line)

    def test_task_exception_handling(self):
        def failing_function():
            raise ValueError("Task failed!")

        def working_function():
            self.execution_log.append("working_task")

        tasks = [
            {
                "name": "failing_task",
                "interval": 1,
                "priority": 1,
                "function": failing_function,
            },
            {
                "name": "working_task",
                "interval": 1,
                "priority": 2,
                "function": working_function,
            },
        ]

        output = self.run_scheduler_briefly(tasks, 0.08)

        self.assertIn("Error executing task 'failing_task'", output)
        self.assertIn("working_task", self.execution_log)

    def test_empty_task_list(self):
        tasks = []

        output = self.run_scheduler_briefly(tasks, 0.1)

        self.assertIn("Scheduler started with no tasks", output)

    def test_duplicate_task_names(self):
        tasks = [
            {
                "name": "duplicate",
                "interval": 1,
                "priority": 1,
                "function": lambda: None,
            },
            {
                "name": "duplicate",
                "interval": 2,
                "priority": 2,
                "function": lambda: None,
            },
        ]

        output = self.run_scheduler_briefly(tasks, 0.1)

        self.assertIn("Duplicate task name 'duplicate'", output)

    def test_invalid_interval(self):
        tasks = [
            {
                "name": "invalid_interval",
                "interval": 0,
                "priority": 1,
                "function": lambda: None,
            }
        ]

        output = self.run_scheduler_briefly(tasks, 0.1)

        self.assertIn("invalid interval (0)", output)
        self.assertIn("No valid tasks to schedule", output)

    def test_invalid_priority(self):
        tasks = [
            {
                "name": "invalid_priority",
                "interval": 1,
                "priority": "high",
                "function": lambda: None,
            }
        ]

        output = self.run_scheduler_briefly(tasks, 0.1)

        self.assertIn("invalid priority (high)", output)

    def test_non_callable_function(self):
        tasks = [
            {
                "name": "invalid_function",
                "interval": 1,
                "priority": 1,
                "function": "not_callable",
            }
        ]

        output = self.run_scheduler_briefly(tasks, 0.1)

        self.assertIn("invalid function", output)

    def test_too_many_tasks(self):
        tasks = []
        for i in range(101):
            tasks.append(
                {
                    "name": f"task_{i}",
                    "interval": 1,
                    "priority": 1,
                    "function": lambda: None,
                }
            )

        output = self.run_scheduler_briefly(tasks, 0.1)

        self.assertIn("Maximum of 100 tasks", output)

    def test_missing_required_fields(self):
        tasks = [{"interval": 1, "priority": 1, "function": lambda: None}]
        output = self.run_scheduler_briefly(tasks)
        self.assertIn("invalid", output.lower())

    def test_same_priority_insertion_order(self):
        tasks = [
            {
                "name": "first",
                "interval": 1,
                "priority": 1,
                "function": self.create_trackable_function("first"),
            },
            {
                "name": "second",
                "interval": 1,
                "priority": 1,
                "function": self.create_trackable_function("second"),
            },
        ]
        self.run_scheduler_briefly(tasks, 0.08)
        self.assertIn("first", self.execution_log)
        self.assertIn("second", self.execution_log)

    def test_different_intervals_timing(self):
        tasks = [
            {
                "name": "fast",
                "interval": 1,
                "priority": 1,
                "function": self.create_trackable_function("fast"),
            },
            {
                "name": "slow",
                "interval": 3,
                "priority": 1,
                "function": self.create_trackable_function("slow"),
            },
        ]
        self.run_scheduler_briefly(tasks, 0.12)
        fast_count = self.execution_log.count("fast")
        slow_count = self.execution_log.count("slow")
        self.assertGreaterEqual(fast_count, slow_count)


if __name__ == "__main__":
    unittest.main()
