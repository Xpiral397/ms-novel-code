# tests

"""Import libraries and functions."""
import unittest
from main import task_scheduler


class TestTaskScheduler(unittest.TestCase):
    """Unit tests for the task_scheduler function."""

    def test_add_and_execute_basic(self):
        """Test adding jobs and executing them in priority order."""
        ops = [["add", "A", 2, 3], ["add", "B", 1, 2], ["execute", 5]]
        expected = ["Job A added", "Job B added", [["B", 2], ["A", 3]]]
        self.assertEqual(task_scheduler(ops), expected)

    def test_execute_with_zero_time(self):
        """Test execute operation with zero time units returns empty list."""
        ops = [["add", "X", 1, 4], ["execute", 0], ["status"]]
        expected = ["Job X added", [], [["X", 1, 4]]]
        self.assertEqual(task_scheduler(ops), expected)

    def test_duplicate_job_id(self):
        """Test adding a duplicate job ID returns error message."""
        ops = [["add", "A", 1, 2], ["add", "A", 2, 3]]
        expected = ["Job A added", "Error: Job A already exists"]
        self.assertEqual(task_scheduler(ops), expected)

    def test_status_empty_queue(self):
        """Test status operation on empty queue returns empty list."""
        ops = [["status"]]
        expected = [[]]
        self.assertEqual(task_scheduler(ops), expected)

    def test_execute_on_empty_queue(self):
        """Test execute operation on empty queue returns empty list."""
        ops = [["execute", 3]]
        expected = [[]]
        self.assertEqual(task_scheduler(ops), expected)

    def test_priority_and_fifo(self):
        """Test FIFO within same priority; lower number = higher priority."""
        ops = [
            ["add", "A", 1, 2],
            ["add", "B", 1, 3],
            ["add", "C", 0, 1],
            ["execute", 3],
            ["status"]
        ]
        expected = [
            "Job A added",
            "Job B added",
            "Job C added",
            [["C", 1], ["A", 2]],
            [["B", 1, 3]]
        ]
        self.assertEqual(task_scheduler(ops), expected)

    def test_partial_execution_and_remaining(self):
        """Test partial execution and remaining time tracking."""
        ops = [
            ["add", "A", 2, 5],
            ["execute", 3],
            ["status"],
            ["execute", 2],
            ["status"]
        ]
        expected = [
            "Job A added",
            [],
            [["A", 2, 2]],
            [["A", 2]],
            []
        ]
        self.assertEqual(task_scheduler(ops), expected)

    def test_multiple_jobs_varied_priority(self):
        """Test all jobs complete in one execute based on priority."""
        ops = [
            ["add", "A", 3, 2],
            ["add", "B", 2, 2],
            ["add", "C", 1, 2],
            ["add", "D", 0, 2],
            ["execute", 8]
        ]
        expected = [
            "Job A added",
            "Job B added",
            "Job C added",
            "Job D added",
            [["D", 2], ["C", 2], ["B", 2], ["A", 2]]
        ]
        self.assertEqual(task_scheduler(ops), expected)

    def test_execute_time_less_than_job(self):
        """Test when execute time is less than job's full time."""
        ops = [
            ["add", "A", 1, 10],
            ["execute", 4],
            ["status"]
        ]
        expected = [
            "Job A added",
            [],
            [["A", 1, 6]]
        ]
        self.assertEqual(task_scheduler(ops), expected)

    def test_execute_time_exact_job(self):
        """Test when execute time equals job's full execution time."""
        ops = [
            ["add", "A", 1, 4],
            ["execute", 4],
            ["status"]
        ]
        expected = [
            "Job A added",
            [["A", 4]],
            []
        ]
        self.assertEqual(task_scheduler(ops), expected)

    def test_status_ordering(self):
        """Test that status returns correct order of queued jobs."""
        ops = [
            ["add", "A", 2, 2],
            ["add", "B", 1, 2],
            ["add", "C", 1, 1],
            ["status"]
        ]
        expected = [
            "Job A added",
            "Job B added",
            "Job C added",
            [["B", 1, 2], ["C", 1, 1], ["A", 2, 2]]
        ]
        self.assertEqual(task_scheduler(ops), expected)

    def test_large_number_of_operations(self):
        """Test scheduler with 1000 jobs and single execute."""
        ops = []
        for i in range(1, 1001):
            ops.append(["add", f"J{i}", i % 5, 1])
        ops.append(["execute", 1000])
        result = task_scheduler(ops)
        self.assertEqual(result.count("Job J1 added"), 1)
        self.assertEqual(len(result[-1]), 1000)

    def test_add_and_execute_interleaved(self):
        """Test interleaved add and execute operations."""
        ops = [
            ["add", "A", 1, 2],
            ["execute", 1],
            ["add", "B", 0, 1],
            ["execute", 2],
            ["status"]
        ]
        expected = [
            "Job A added",
            [],
            "Job B added",
            [["B", 1], ["A", 1]],
            []
        ]
        self.assertEqual(task_scheduler(ops), expected)

    def test_execute_multiple_jobs_partial(self):
        """Test partial execution with multiple jobs of same priority."""
        ops = [
            ["add", "A", 1, 3],
            ["add", "B", 1, 3],
            ["execute", 4],
            ["status"]
        ]
        expected = [
            "Job A added",
            "Job B added",
            [["A", 3]],
            [["B", 1, 2]]
        ]
        self.assertEqual(task_scheduler(ops), expected)


if __name__ == "__main__":
    unittest.main()
