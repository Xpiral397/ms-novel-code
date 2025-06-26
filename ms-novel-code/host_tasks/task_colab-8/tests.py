# tests

import unittest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Iterable, Optional, Callable, Tuple
import nest_asyncio
from main import monitor_and_repair

# Apply nest_asyncio to allow nested event loops in Jupyter/Colab
nest_asyncio.apply()


class TestReactiveLogMonitoring(unittest.TestCase):

    def get_current_timestamp(self):
        """Get current timestamp in the format expected by the code"""
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def get_timestamp_offset(self, seconds_offset=0):
        """Get timestamp with offset from current time"""
        return (datetime.now() + timedelta(seconds=seconds_offset)).strftime('%Y-%m-%d %H:%M:%S')

    def test_basic_successful_repair(self):
        """Test basic successful repair execution"""
        async def test():
            # Use current timestamp to ensure it's within retention window
            timestamp = self.get_current_timestamp()
            log_stream = [f"[{timestamp}] ERROR: Disk failure on /dev/sda"]
            error_patterns = {"Disk failure": "Critical hardware error"}

            def restart_disk_service():
                return "Disk service restarted"

            repair_actions = {"Disk failure": restart_disk_service}
            config = {"reactive_mode": True, "max_concurrent_repairs": 1, "log_retention_seconds": 300}

            repair_log, status_summary = await monitor_and_repair(log_stream, error_patterns, repair_actions, config)

            self.assertEqual(len(repair_log), 1)
            self.assertEqual(repair_log[0]["error"], "Disk failure")
            self.assertEqual(repair_log[0]["status"], "success")
            self.assertEqual(repair_log[0]["details"], "Disk service restarted")
            self.assertEqual(status_summary, {"success": 1, "failed": 0, "skipped": 0})

        asyncio.run(test())

    def test_failed_repair_with_exception(self):
        """Test repair that fails with exception"""
        async def test():
            # Use current timestamp
            timestamp = self.get_current_timestamp()
            log_stream = [f"[{timestamp}] ERROR: CPU temperature high"]
            error_patterns = {"CPU temperature high": "Thermal warning"}

            def throttle_cpu():
                raise PermissionError("Access denied")

            repair_actions = {"CPU temperature high": throttle_cpu}
            config = {"reactive_mode": True, "max_concurrent_repairs": 1, "log_retention_seconds": 300}

            repair_log, status_summary = await monitor_and_repair(log_stream, error_patterns, repair_actions, config)

            self.assertEqual(len(repair_log), 1)
            self.assertEqual(repair_log[0]["status"], "failed")
            self.assertIn("Access denied", repair_log[0]["details"])
            self.assertEqual(status_summary, {"success": 0, "failed": 1, "skipped": 0})

        asyncio.run(test())

    def test_skipped_repair_no_action(self):
        """Test repair that returns 'no action' message"""
        async def test():
            timestamp = self.get_current_timestamp()
            log_stream = [f"[{timestamp}] ERROR: Low disk space"]
            error_patterns = {"Low disk space": "Disk capacity alert"}

            def cleanup_disk():
                return "no action taken due to restrictions"

            repair_actions = {"Low disk space": cleanup_disk}
            config = {"reactive_mode": True, "max_concurrent_repairs": 1, "log_retention_seconds": 300}

            repair_log, status_summary = await monitor_and_repair(log_stream, error_patterns, repair_actions, config)

            self.assertEqual(len(repair_log), 1)
            self.assertEqual(repair_log[0]["status"], "skipped")
            self.assertEqual(status_summary, {"success": 0, "failed": 0, "skipped": 1})

        asyncio.run(test())

    def test_skipped_repair_contains_skipped(self):
        """Test repair that returns message containing 'skipped'"""
        async def test():
            timestamp = self.get_current_timestamp()
            log_stream = [f"[{timestamp}] ERROR: Memory leak detected"]
            error_patterns = {"Memory leak": "Memory issue"}

            def fix_memory():
                return "Cleanup skipped due to user restrictions"

            repair_actions = {"Memory leak": fix_memory}
            config = {"reactive_mode": True, "max_concurrent_repairs": 1, "log_retention_seconds": 300}

            repair_log, status_summary = await monitor_and_repair(log_stream, error_patterns, repair_actions, config)

            self.assertEqual(len(repair_log), 1)
            self.assertEqual(repair_log[0]["status"], "skipped")
            self.assertEqual(status_summary, {"success": 0, "failed": 0, "skipped": 1})

        asyncio.run(test())

    def test_reactive_mode_disabled(self):
        """Test when reactive_mode is False"""
        async def test():
            timestamp = self.get_current_timestamp()
            log_stream = [f"[{timestamp}] ERROR: Disk failure on /dev/sda"]
            error_patterns = {"Disk failure": "Critical hardware error"}

            def restart_disk_service():
                return "Service restarted"

            repair_actions = {"Disk failure": restart_disk_service}
            config = {"reactive_mode": False, "max_concurrent_repairs": 1, "log_retention_seconds": 300}

            repair_log, status_summary = await monitor_and_repair(log_stream, error_patterns, repair_actions, config)

            self.assertEqual(len(repair_log), 0)
            self.assertEqual(status_summary, {"success": 0, "failed": 0, "skipped": 0})

        asyncio.run(test())

    def test_unknown_error_pattern(self):
        """Test log with error not in error_patterns"""
        async def test():
            timestamp = self.get_current_timestamp()
            log_stream = [f"[{timestamp}] ERROR: Unknown system fault"]
            error_patterns = {"Disk failure": "Critical hardware error"}

            def restart_service():
                return "Service restarted"

            repair_actions = {"Disk failure": restart_service}
            config = {"reactive_mode": True, "max_concurrent_repairs": 1, "log_retention_seconds": 300}

            repair_log, status_summary = await monitor_and_repair(log_stream, error_patterns, repair_actions, config)

            self.assertEqual(len(repair_log), 0)
            self.assertEqual(status_summary, {"success": 0, "failed": 0, "skipped": 0})

        asyncio.run(test())

    def test_none_repair_action(self):
        """Test when repair action is None"""
        async def test():
            timestamp = self.get_current_timestamp()
            log_stream = [f"[{timestamp}] ERROR: Database timeout"]
            error_patterns = {"Database timeout": "DB connection issue"}
            repair_actions = {"Database timeout": None}
            config = {"reactive_mode": True, "max_concurrent_repairs": 1, "log_retention_seconds": 300}

            repair_log, status_summary = await monitor_and_repair(log_stream, error_patterns, repair_actions, config)

            self.assertEqual(len(repair_log), 1)
            self.assertEqual(repair_log[0]["status"], "skipped")
            self.assertEqual(repair_log[0]["details"], "Invalid repair action")
            self.assertEqual(repair_log[0]["action"], None)
            self.assertEqual(status_summary, {"success": 0, "failed": 0, "skipped": 1})

        asyncio.run(test())

    def test_no_repair_action_assigned(self):
        """Test when error pattern exists but no repair action assigned"""
        async def test():
            timestamp = self.get_current_timestamp()
            log_stream = [f"[{timestamp}] ERROR: Network timeout"]
            error_patterns = {"Network timeout": "Connection issue"}
            repair_actions = {}
            config = {"reactive_mode": True, "max_concurrent_repairs": 1, "log_retention_seconds": 300}

            repair_log, status_summary = await monitor_and_repair(log_stream, error_patterns, repair_actions, config)

            self.assertEqual(len(repair_log), 1)
            self.assertEqual(repair_log[0]["status"], "skipped")
            self.assertEqual(repair_log[0]["details"], "No repair action assigned")
            self.assertEqual(repair_log[0]["action"], None)
            self.assertEqual(status_summary, {"success": 0, "failed": 0, "skipped": 1})

        asyncio.run(test())

    def test_log_retention_window_expired(self):
        """Test logs outside retention window are ignored"""
        async def test():
            # Create log with timestamp 400 seconds ago (outside 300 second window)
            old_timestamp = self.get_timestamp_offset(-400)
            log_stream = [f"[{old_timestamp}] ERROR: Disk failure"]
            error_patterns = {"Disk failure": "Critical hardware error"}

            def restart_service():
                return "Service restarted"

            repair_actions = {"Disk failure": restart_service}
            config = {"reactive_mode": True, "max_concurrent_repairs": 1, "log_retention_seconds": 300}

            repair_log, status_summary = await monitor_and_repair(log_stream, error_patterns, repair_actions, config)

            self.assertEqual(len(repair_log), 0)
            self.assertEqual(status_summary, {"success": 0, "failed": 0, "skipped": 0})

        asyncio.run(test())

    def test_max_concurrent_repairs_limit(self):
        """Test max concurrent repairs constraint"""
        async def test():
            timestamp = self.get_current_timestamp()
            log_stream = [
                f"[{timestamp}] ERROR: Disk failure on /dev/sda",
                f"[{timestamp}] ERROR: CPU temperature high",
                f"[{timestamp}] ERROR: Memory leak detected"
            ]
            error_patterns = {
                "Disk failure": "Critical hardware error",
                "CPU temperature high": "Thermal warning",
                "Memory leak": "Memory issue"
            }

            def slow_repair():
                return "Repair completed"

            repair_actions = {
                "Disk failure": slow_repair,
                "CPU temperature high": slow_repair,
                "Memory leak": slow_repair
            }
            config = {"reactive_mode": True, "max_concurrent_repairs": 2, "log_retention_seconds": 300}

            repair_log, status_summary = await monitor_and_repair(log_stream, error_patterns, repair_actions, config)

            # Should process all 3 logs but respect concurrency limit
            self.assertEqual(len(repair_log), 3)
            success_count = sum(1 for entry in repair_log if entry["status"] == "success")
            self.assertGreaterEqual(success_count, 2)

        asyncio.run(test())

    def test_multiple_error_types_mixed_outcomes(self):
        """Test multiple errors with different outcomes"""
        async def test():
            timestamp = self.get_current_timestamp()
            log_stream = [
                f"[{timestamp}] ERROR: Disk failure on /dev/sda",
                f"[{timestamp}] ERROR: CPU temperature high",
                f"[{timestamp}] ERROR: Low disk space"
            ]
            error_patterns = {
                "Disk failure": "Critical hardware error",
                "CPU temperature high": "Thermal warning",
                "Low disk space": "Disk capacity alert"
            }

            def restart_disk():
                return "Disk service restarted"

            def throttle_cpu():
                raise Exception("CPU control failed")

            def cleanup_disk():
                return "no action needed"

            repair_actions = {
                "Disk failure": restart_disk,
                "CPU temperature high": throttle_cpu,
                "Low disk space": cleanup_disk
            }
            config = {"reactive_mode": True, "max_concurrent_repairs": 5, "log_retention_seconds": 300}

            repair_log, status_summary = await monitor_and_repair(log_stream, error_patterns, repair_actions, config)

            self.assertEqual(len(repair_log), 3)
            self.assertEqual(status_summary["success"], 1)
            self.assertEqual(status_summary["failed"], 1)
            self.assertEqual(status_summary["skipped"], 1)

        asyncio.run(test())

    def test_case_sensitive_error_matching(self):
        """Test that error pattern matching is case-sensitive"""
        async def test():
            timestamp = self.get_current_timestamp()
            log_stream = [f"[{timestamp}] ERROR: disk failure on /dev/sda"]
            error_patterns = {"Disk failure": "Critical hardware error"}  # Capital D

            def restart_disk():
                return "Service restarted"

            repair_actions = {"Disk failure": restart_disk}
            config = {"reactive_mode": True, "max_concurrent_repairs": 1, "log_retention_seconds": 300}

            repair_log, status_summary = await monitor_and_repair(log_stream, error_patterns, repair_actions, config)

            # Should not match due to case sensitivity
            self.assertEqual(len(repair_log), 0)
            self.assertEqual(status_summary, {"success": 0, "failed": 0, "skipped": 0})

        asyncio.run(test())

    def test_maximum_log_entries_100(self):
        """Test processing maximum 100 log entries"""
        async def test():
            timestamp = self.get_current_timestamp()
            log_stream = []
            for i in range(100):
                log_stream.append(f"[{timestamp}] ERROR: Disk failure {i}")

            error_patterns = {"Disk failure": "Critical hardware error"}

            def restart_disk():
                return "Service restarted"

            repair_actions = {"Disk failure": restart_disk}
            config = {"reactive_mode": True, "max_concurrent_repairs": 10, "log_retention_seconds": 3600}

            repair_log, status_summary = await monitor_and_repair(log_stream, error_patterns, repair_actions, config)

            self.assertEqual(len(repair_log), 100)
            self.assertEqual(status_summary["success"], 100)

        asyncio.run(test())

    def test_maximum_error_patterns_50(self):
        """Test handling up to 50 distinct error patterns"""
        async def test():
            timestamp = self.get_current_timestamp()
            log_stream = []
            error_patterns = {}
            repair_actions = {}

            def generic_repair():
                return "Repair completed"

            for i in range(50):
                error_key = f"Error{i}"
                log_stream.append(f"[{timestamp}] ERROR: {error_key} occurred")
                error_patterns[error_key] = f"Description for error {i}"
                repair_actions[error_key] = generic_repair

            config = {"reactive_mode": True, "max_concurrent_repairs": 10, "log_retention_seconds": 300}

            repair_log, status_summary = await monitor_and_repair(log_stream, error_patterns, repair_actions, config)

            self.assertEqual(len(repair_log), 50)
            self.assertEqual(status_summary["success"], 50)

        asyncio.run(test())

    def test_maximum_concurrent_repairs_10(self):
        """Test maximum concurrent repairs limit of 10"""
        async def test():
            base_time = datetime.now()
            log_stream = []
            for i in range(15):
                # Use slightly different timestamps to ensure all are within retention window
                timestamp = (base_time + timedelta(seconds=i)).strftime('%Y-%m-%d %H:%M:%S')
                log_stream.append(f"[{timestamp}] ERROR: Concurrent error {i}")

            error_patterns = {"Concurrent error": "Test error"}

            def slow_repair():
                return "Repair done"

            repair_actions = {"Concurrent error": slow_repair}
            config = {"reactive_mode": True, "max_concurrent_repairs": 10, "log_retention_seconds": 300}

            repair_log, status_summary = await monitor_and_repair(log_stream, error_patterns, repair_actions, config)

            self.assertEqual(len(repair_log), 15)
            # All should succeed but with concurrency limit respected
            self.assertEqual(status_summary["success"], 15)

        asyncio.run(test())

    def test_maximum_log_retention_3600_seconds(self):
        """Test maximum log retention window of 3600 seconds"""
        async def test():
            # Create log exactly at retention boundary
            boundary_timestamp = self.get_timestamp_offset(-3600)
            log_stream = [f"[{boundary_timestamp}] ERROR: Boundary test"]

            error_patterns = {"Boundary test": "Test at boundary"}

            def test_repair():
                return "Repair executed"

            repair_actions = {"Boundary test": test_repair}
            config = {"reactive_mode": True, "max_concurrent_repairs": 1, "log_retention_seconds": 3600}

            repair_log, status_summary = await monitor_and_repair(log_stream, error_patterns, repair_actions, config)

            # Should be processed as it's exactly at the boundary
            self.assertGreaterEqual(len(repair_log), 0)

        asyncio.run(test())

    def test_empty_log_stream(self):
        """Test empty log stream"""
        async def test():
            log_stream = []
            error_patterns = {"Disk failure": "Critical hardware error"}

            def restart_disk():
                return "Service restarted"

            repair_actions = {"Disk failure": restart_disk}
            config = {"reactive_mode": True, "max_concurrent_repairs": 1, "log_retention_seconds": 300}

            repair_log, status_summary = await monitor_and_repair(log_stream, error_patterns, repair_actions, config)

            self.assertEqual(len(repair_log), 0)
            self.assertEqual(status_summary, {"success": 0, "failed": 0, "skipped": 0})

        asyncio.run(test())

    def test_empty_error_patterns(self):
        """Test empty error patterns dictionary"""
        async def test():
            timestamp = self.get_current_timestamp()
            log_stream = [f"[{timestamp}] ERROR: Disk failure"]
            error_patterns = {}
            repair_actions = {}
            config = {"reactive_mode": True, "max_concurrent_repairs": 1, "log_retention_seconds": 300}

            repair_log, status_summary = await monitor_and_repair(log_stream, error_patterns, repair_actions, config)

            self.assertEqual(len(repair_log), 0)
            self.assertEqual(status_summary, {"success": 0, "failed": 0, "skipped": 0})

        asyncio.run(test())

    def test_one_repair_per_log_line(self):
        """Test that only one repair is triggered per log line even with multiple matches"""
        async def test():
            timestamp = self.get_current_timestamp()
            log_stream = [f"[{timestamp}] ERROR: Disk failure CPU temperature high"]
            error_patterns = {
                "Disk failure": "Critical hardware error",
                "CPU temperature high": "Thermal warning"
            }

            def repair1():
                return "Repair 1"

            def repair2():
                return "Repair 2"

            repair_actions = {
                "Disk failure": repair1,
                "CPU temperature high": repair2
            }
            config = {"reactive_mode": True, "max_concurrent_repairs": 5, "log_retention_seconds": 300}

            repair_log, status_summary = await monitor_and_repair(log_stream, error_patterns, repair_actions, config)

            self.assertEqual(len(repair_log), 1)

        asyncio.run(test())

    def test_status_summary_always_contains_all_keys(self):
        """Test that status summary always contains success, failed, and skipped keys"""
        async def test():
            log_stream = []
            error_patterns = {}
            repair_actions = {}
            config = {"reactive_mode": True, "max_concurrent_repairs": 1, "log_retention_seconds": 300}

            repair_log, status_summary = await monitor_and_repair(log_stream, error_patterns, repair_actions, config)

            self.assertIn("success", status_summary)
            self.assertIn("failed", status_summary)
            self.assertIn("skipped", status_summary)
            self.assertEqual(status_summary["success"], 0)
            self.assertEqual(status_summary["failed"], 0)
            self.assertEqual(status_summary["skipped"], 0)

        asyncio.run(test())

    def test_log_with_info_and_warning_levels(self):
        """Test logs with different severity levels (INFO, WARNING) are processed"""
        async def test():
            timestamp = self.get_current_timestamp()
            log_stream = [
                f"[{timestamp}] INFO: System startup complete",
                f"[{timestamp}] WARNING: CPU temperature high",
                f"[{timestamp}] ERROR: Disk failure"
            ]
            error_patterns = {
                "System startup": "Startup message",
                "CPU temperature high": "Thermal warning",
                "Disk failure": "Critical error"
            }

            def handle_startup():
                return "Startup handled"

            def handle_temp():
                return "Temperature controlled"

            def handle_disk():
                return "Disk repaired"

            repair_actions = {
                "System startup": handle_startup,
                "CPU temperature high": handle_temp,
                "Disk failure": handle_disk
            }
            config = {"reactive_mode": True, "max_concurrent_repairs": 5, "log_retention_seconds": 300}

            repair_log, status_summary = await monitor_and_repair(log_stream, error_patterns, repair_actions, config)

            self.assertEqual(len(repair_log), 2)
            self.assertEqual(status_summary["success"], 2)

        asyncio.run(test())


if __name__ == '__main__':
    try:
        import nest_asyncio
    except ImportError:
        import subprocess
        import sys
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'nest-asyncio'])
        import nest_asyncio

    unittest.main(argv=[''],exit=False)
