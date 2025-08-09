# tests

import unittest
import asyncio
import time
from main import analyze_log_files


class TestAnalyzeLogFiles(unittest.TestCase):
    """Test cases for the analyze_log_files function."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.maxDiff = None

    def tearDown(self):
        """Clean up after each test method."""

        try:
            loop = asyncio.get_running_loop()
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
        except RuntimeError:

            pass

    def test_example_1_from_problem(self):
        """Test the first example from the problem statement."""
        log_files = [
            {
                "file_id": "srv1",
                "file_path": "/var/log/app.log",
                "timeout": 0.2,
                "expected_lines": 34,
                "error_type": None,
            },
            {
                "file_id": "srv2",
                "file_path": "/var/log/err.log",
                "timeout": 0.3,
                "expected_lines": 28,
                "error_type": "file_not_found",
            },
            {
                "file_id": "srv3",
                "file_path": "/var/log/sys.log",
                "timeout": 0.1,
                "expected_lines": 55,
                "error_type": None,
            },
        ]

        result = analyze_log_files(log_files)

        self.assertEqual(result["total_lines"], 89)
        self.assertEqual(result["successful_files"], 2)
        self.assertEqual(
            result["error_summary"],
            {"FileNotFoundError": 1, "PermissionError": 0, "TimeoutError": 0},
        )
        self.assertEqual(len(result["file_results"]), 3)
        self.assertEqual(
            result["file_results"][0],
            {"file_id": "srv1", "status": "success", "line_count": 34},
        )
        self.assertEqual(
            result["file_results"][1],
            {
                "file_id": "srv2",
                "status": "error",
                "error_type": "FileNotFoundError",
            },
        )
        self.assertEqual(
            result["file_results"][2],
            {"file_id": "srv3", "status": "success", "line_count": 55},
        )

    def test_example_2_from_problem(self):
        """Test the second example from the problem statement."""
        log_files = [
            {
                "file_id": "monitor",
                "file_path": "/logs/mon.log",
                "timeout": 0.05,
                "expected_lines": 42,
                "error_type": "timeout",
            },
            {
                "file_id": "backup",
                "file_path": "/logs/bak.log",
                "timeout": 0.4,
                "expected_lines": 18,
                "error_type": "permission_denied",
            },
        ]

        result = analyze_log_files(log_files)

        self.assertEqual(result["total_lines"], 0)
        self.assertEqual(result["successful_files"], 0)
        self.assertEqual(
            result["error_summary"],
            {"FileNotFoundError": 0, "PermissionError": 1, "TimeoutError": 1},
        )
        self.assertEqual(len(result["file_results"]), 2)
        self.assertEqual(
            result["file_results"][0],
            {
                "file_id": "monitor",
                "status": "error",
                "error_type": "TimeoutError",
            },
        )
        self.assertEqual(
            result["file_results"][1],
            {
                "file_id": "backup",
                "status": "error",
                "error_type": "PermissionError",
            },
        )

    def test_empty_input(self):
        """Test with empty log files list."""
        result = analyze_log_files([])

        self.assertEqual(result["total_lines"], 0)
        self.assertEqual(result["successful_files"], 0)
        self.assertEqual(
            result["error_summary"],
            {"FileNotFoundError": 0, "PermissionError": 0, "TimeoutError": 0},
        )
        self.assertEqual(result["file_results"], [])

    def test_all_files_successful(self):
        """Test when all files are processed successfully."""
        log_files = [
            {
                "file_id": "file1",
                "file_path": "/log1.log",
                "timeout": 0.1,
                "expected_lines": 10,
                "error_type": None,
            },
            {
                "file_id": "file2",
                "file_path": "/log2.log",
                "timeout": 0.1,
                "expected_lines": 20,
                "error_type": None,
            },
            {
                "file_id": "file3",
                "file_path": "/log3.log",
                "timeout": 0.1,
                "expected_lines": 30,
                "error_type": None,
            },
        ]

        result = analyze_log_files(log_files)

        self.assertEqual(result["total_lines"], 60)
        self.assertEqual(result["successful_files"], 3)
        self.assertEqual(result["error_summary"]["FileNotFoundError"], 0)
        self.assertEqual(result["error_summary"]["PermissionError"], 0)
        self.assertEqual(result["error_summary"]["TimeoutError"], 0)

    def test_all_error_types(self):
        """Test with all three error types."""
        log_files = [
            {
                "file_id": "f1",
                "file_path": "/f1.log",
                "timeout": 0.1,
                "expected_lines": 10,
                "error_type": "file_not_found",
            },
            {
                "file_id": "f2",
                "file_path": "/f2.log",
                "timeout": 0.1,
                "expected_lines": 20,
                "error_type": "permission_denied",
            },
            {
                "file_id": "f3",
                "file_path": "/f3.log",
                "timeout": 0.1,
                "expected_lines": 30,
                "error_type": "timeout",
            },
        ]

        result = analyze_log_files(log_files)

        self.assertEqual(result["total_lines"], 0)
        self.assertEqual(result["successful_files"], 0)
        self.assertEqual(result["error_summary"]["FileNotFoundError"], 1)
        self.assertEqual(result["error_summary"]["PermissionError"], 1)
        self.assertEqual(result["error_summary"]["TimeoutError"], 1)

    def test_zero_timeout_causes_timeout(self):
        """Test that zero timeout causes immediate timeout error."""
        log_files = [
            {
                "file_id": "zero_timeout",
                "file_path": "/zero.log",
                "timeout": 0.0,
                "expected_lines": 100,
                "error_type": None,
            }
        ]

        result = analyze_log_files(log_files)

        self.assertEqual(result["total_lines"], 0)
        self.assertEqual(result["successful_files"], 0)
        self.assertEqual(result["error_summary"]["TimeoutError"], 1)
        self.assertEqual(
            result["file_results"][0]["error_type"], "TimeoutError"
        )

    def test_negative_timeout_causes_timeout(self):
        """Test that negative timeout causes immediate timeout error."""
        log_files = [
            {
                "file_id": "neg_timeout",
                "file_path": "/neg.log",
                "timeout": -0.5,
                "expected_lines": 50,
                "error_type": None,
            }
        ]

        result = analyze_log_files(log_files)

        self.assertEqual(result["total_lines"], 0)
        self.assertEqual(result["successful_files"], 0)
        self.assertEqual(result["error_summary"]["TimeoutError"], 1)

    def test_invalid_error_type_treated_as_success(self):
        """Test that invalid error_type is treated as None (success)."""
        log_files = [
            {
                "file_id": "invalid",
                "file_path": "/invalid.log",
                "timeout": 0.1,
                "expected_lines": 75,
                "error_type": "unknown_error",
            }
        ]

        result = analyze_log_files(log_files)

        self.assertEqual(result["total_lines"], 75)
        self.assertEqual(result["successful_files"], 1)
        self.assertEqual(result["file_results"][0]["status"], "success")
        self.assertEqual(result["file_results"][0]["line_count"], 75)

    def test_duplicate_file_ids_processed_independently(self):
        """Test that duplicate file_ids are processed independently."""
        log_files = [
            {
                "file_id": "dup",
                "file_path": "/dup1.log",
                "timeout": 0.1,
                "expected_lines": 10,
                "error_type": None,
            },
            {
                "file_id": "dup",
                "file_path": "/dup2.log",
                "timeout": 0.1,
                "expected_lines": 20,
                "error_type": None,
            },
        ]

        result = analyze_log_files(log_files)

        self.assertEqual(result["total_lines"], 30)
        self.assertEqual(result["successful_files"], 2)
        self.assertEqual(len(result["file_results"]), 2)
        self.assertEqual(result["file_results"][0]["file_id"], "dup")
        self.assertEqual(result["file_results"][1]["file_id"], "dup")

    def test_maintains_original_order(self):
        """Test that results maintain the original input order."""
        log_files = [
            {
                "file_id": "z_last",
                "file_path": "/z.log",
                "timeout": 0.1,
                "expected_lines": 1,
                "error_type": None,
            },
            {
                "file_id": "a_first",
                "file_path": "/a.log",
                "timeout": 0.1,
                "expected_lines": 2,
                "error_type": "file_not_found",
            },
            {
                "file_id": "m_middle",
                "file_path": "/m.log",
                "timeout": 0.1,
                "expected_lines": 3,
                "error_type": None,
            },
        ]

        result = analyze_log_files(log_files)

        self.assertEqual(result["file_results"][0]["file_id"], "z_last")
        self.assertEqual(result["file_results"][1]["file_id"], "a_first")
        self.assertEqual(result["file_results"][2]["file_id"], "m_middle")

    def test_concurrent_processing(self):
        """Test that files are processed concurrently, not sequentially."""
        log_files = [
            {
                "file_id": "slow1",
                "file_path": "/s1.log",
                "timeout": 0.3,
                "expected_lines": 10,
                "error_type": None,
            },
            {
                "file_id": "slow2",
                "file_path": "/s2.log",
                "timeout": 0.3,
                "expected_lines": 20,
                "error_type": None,
            },
            {
                "file_id": "slow3",
                "file_path": "/s3.log",
                "timeout": 0.3,
                "expected_lines": 30,
                "error_type": None,
            },
        ]

        start_time = time.time()
        result = analyze_log_files(log_files)
        elapsed_time = time.time() - start_time

        self.assertLess(elapsed_time, 0.25)
        self.assertEqual(result["total_lines"], 60)
        self.assertEqual(result["successful_files"], 3)

    def test_mixed_success_and_errors(self):
        """Test with a mix of successful and failed file operations."""
        log_files = [
            {
                "file_id": "success1",
                "file_path": "/s1.log",
                "timeout": 0.1,
                "expected_lines": 100,
                "error_type": None,
            },
            {
                "file_id": "fail1",
                "file_path": "/f1.log",
                "timeout": 0.1,
                "expected_lines": 200,
                "error_type": "file_not_found",
            },
            {
                "file_id": "success2",
                "file_path": "/s2.log",
                "timeout": 0.1,
                "expected_lines": 150,
                "error_type": None,
            },
            {
                "file_id": "fail2",
                "file_path": "/f2.log",
                "timeout": 0.1,
                "expected_lines": 300,
                "error_type": "permission_denied",
            },
            {
                "file_id": "fail3",
                "file_path": "/f3.log",
                "timeout": 0.1,
                "expected_lines": 400,
                "error_type": "timeout",
            },
        ]

        result = analyze_log_files(log_files)

        self.assertEqual(result["total_lines"], 250)
        self.assertEqual(result["successful_files"], 2)
        self.assertEqual(result["error_summary"]["FileNotFoundError"], 1)
        self.assertEqual(result["error_summary"]["PermissionError"], 1)
        self.assertEqual(result["error_summary"]["TimeoutError"], 1)


if __name__ == "__main__":
    unittest.main()
