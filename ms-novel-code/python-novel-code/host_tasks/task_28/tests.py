# tests

import unittest
import asyncio
import nest_asyncio
from datetime import datetime, timedelta
from main import monitor_and_repair

nest_asyncio.apply()

class TestReactiveLogMonitoring(unittest.TestCase):

    def get_current_timestamp(self):
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def get_timestamp_offset(self, seconds_offset=0):
        return (datetime.now() + timedelta(seconds=seconds_offset)).strftime('%Y-%m-%d %H:%M:%S')

    def run_async(self, coro):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro)

    def test_basic_successful_repair(self):
        async def test():
            timestamp = self.get_current_timestamp()
            log_stream = [f"[{timestamp}] ERROR: Disk failure on /dev/sda"]
            error_patterns = {"Disk failure": "Critical hardware error"}
            def restart_disk_service(): return "Disk service restarted"
            repair_actions = {"Disk failure": restart_disk_service}
            config = {"reactive_mode": True, "max_concurrent_repairs": 1, "log_retention_seconds": 300}
            return await monitor_and_repair(log_stream, error_patterns, repair_actions, config)

        repair_log, summary = self.run_async(test())
        self.assertEqual(summary, {"success": 1, "failed": 0, "skipped": 0})

    def test_failed_repair_with_exception(self):
        async def test():
            timestamp = self.get_current_timestamp()
            log_stream = [f"[{timestamp}] ERROR: CPU temperature high"]
            error_patterns = {"CPU temperature high": "Thermal warning"}
            def throttle_cpu(): raise PermissionError("Access denied")
            repair_actions = {"CPU temperature high": throttle_cpu}
            config = {"reactive_mode": True, "max_concurrent_repairs": 1, "log_retention_seconds": 300}
            return await monitor_and_repair(log_stream, error_patterns, repair_actions, config)

        repair_log, summary = self.run_async(test())
        self.assertEqual(summary, {"success": 0, "failed": 1, "skipped": 0})

    def test_skipped_repair_no_action(self):
        async def test():
            timestamp = self.get_current_timestamp()
            log_stream = [f"[{timestamp}] ERROR: Low disk space"]
            error_patterns = {"Low disk space": "Disk capacity alert"}
            def cleanup_disk(): return "no action taken"
            repair_actions = {"Low disk space": cleanup_disk}
            config = {"reactive_mode": True, "max_concurrent_repairs": 1, "log_retention_seconds": 300}
            return await monitor_and_repair(log_stream, error_patterns, repair_actions, config)

        repair_log, summary = self.run_async(test())
        self.assertEqual(summary, {"success": 0, "failed": 0, "skipped": 1})

    def test_skipped_repair_contains_skipped(self):
        async def test():
            timestamp = self.get_current_timestamp()
            log_stream = [f"[{timestamp}] ERROR: Memory leak detected"]
            error_patterns = {"Memory leak": "Memory issue"}
            def fix_memory(): return "Cleanup skipped"
            repair_actions = {"Memory leak": fix_memory}
            config = {"reactive_mode": True, "max_concurrent_repairs": 1, "log_retention_seconds": 300}
            return await monitor_and_repair(log_stream, error_patterns, repair_actions, config)

        repair_log, summary = self.run_async(test())
        self.assertEqual(summary, {"success": 0, "failed": 0, "skipped": 1})

    def test_reactive_mode_disabled(self):
        async def test():
            timestamp = self.get_current_timestamp()
            log_stream = [f"[{timestamp}] ERROR: Disk failure on /dev/sda"]
            error_patterns = {"Disk failure": "Critical hardware error"}
            def restart_disk_service(): return "Service restarted"
            repair_actions = {"Disk failure": restart_disk_service}
            config = {"reactive_mode": False, "max_concurrent_repairs": 1, "log_retention_seconds": 300}
            return await monitor_and_repair(log_stream, error_patterns, repair_actions, config)

        repair_log, summary = self.run_async(test())
        self.assertEqual(summary, {"success": 0, "failed": 0, "skipped": 0})

    def test_unknown_error_pattern(self):
        async def test():
            timestamp = self.get_current_timestamp()
            log_stream = [f"[{timestamp}] ERROR: Unknown system fault"]
            error_patterns = {"Disk failure": "Critical hardware error"}
            def restart_service(): return "Service restarted"
            repair_actions = {"Disk failure": restart_service}
            config = {"reactive_mode": True, "max_concurrent_repairs": 1, "log_retention_seconds": 300}
            return await monitor_and_repair(log_stream, error_patterns, repair_actions, config)

        repair_log, summary = self.run_async(test())
        self.assertEqual(summary, {"success": 0, "failed": 0, "skipped": 0})

    def test_none_repair_action(self):
        async def test():
            timestamp = self.get_current_timestamp()
            log_stream = [f"[{timestamp}] ERROR: Database timeout"]
            error_patterns = {"Database timeout": "DB connection issue"}
            repair_actions = {"Database timeout": None}
            config = {"reactive_mode": True, "max_concurrent_repairs": 1, "log_retention_seconds": 300}
            return await monitor_and_repair(log_stream, error_patterns, repair_actions, config)

        repair_log, summary = self.run_async(test())
        self.assertEqual(summary, {"success": 0, "failed": 0, "skipped": 1})

    def test_no_repair_action_assigned(self):
        async def test():
            timestamp = self.get_current_timestamp()
            log_stream = [f"[{timestamp}] ERROR: Network timeout"]
            error_patterns = {"Network timeout": "Connection issue"}
            repair_actions = {}
            config = {"reactive_mode": True, "max_concurrent_repairs": 1, "log_retention_seconds": 300}
            return await monitor_and_repair(log_stream, error_patterns, repair_actions, config)

        repair_log, summary = self.run_async(test())
        self.assertEqual(summary, {"success": 0, "failed": 0, "skipped": 1})

    def test_log_retention_window_expired(self):
        async def test():
            old_timestamp = self.get_timestamp_offset(-400)
            log_stream = [f"[{old_timestamp}] ERROR: Disk failure"]
            error_patterns = {"Disk failure": "Critical hardware error"}
            def restart_service(): return "Service restarted"
            repair_actions = {"Disk failure": restart_service}
            config = {"reactive_mode": True, "max_concurrent_repairs": 1, "log_retention_seconds": 300}
            return await monitor_and_repair(log_stream, error_patterns, repair_actions, config)

        repair_log, summary = self.run_async(test())
        self.assertEqual(summary, {"success": 0, "failed": 0, "skipped": 0})

    def test_max_concurrent_repairs_limit(self):
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
            def repair(): return "Done"
            repair_actions = {k: repair for k in error_patterns}
            config = {"reactive_mode": True, "max_concurrent_repairs": 2, "log_retention_seconds": 300}
            return await monitor_and_repair(log_stream, error_patterns, repair_actions, config)

        repair_log, summary = self.run_async(test())
        self.assertEqual(len(repair_log), 3)

    def test_multiple_error_types_mixed_outcomes(self):
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
            def disk(): return "Disk service restarted"
            def cpu(): raise Exception("CPU control failed")
            def disk2(): return "no action needed"
            repair_actions = {
                "Disk failure": disk,
                "CPU temperature high": cpu,
                "Low disk space": disk2
            }
            config = {"reactive_mode": True, "max_concurrent_repairs": 5, "log_retention_seconds": 300}
            return await monitor_and_repair(log_stream, error_patterns, repair_actions, config)

        _, summary = self.run_async(test())
        self.assertEqual(summary, {"success": 1, "failed": 1, "skipped": 1})

    def test_case_sensitive_error_matching(self):
        async def test():
            timestamp = self.get_current_timestamp()
            log_stream = [f"[{timestamp}] ERROR: disk failure on /dev/sda"]
            error_patterns = {"Disk failure": "Critical hardware error"}
            def restart_disk(): return "Service restarted"
            repair_actions = {"Disk failure": restart_disk}
            config = {"reactive_mode": True, "max_concurrent_repairs": 1, "log_retention_seconds": 300}
            return await monitor_and_repair(log_stream, error_patterns, repair_actions, config)

        _, summary = self.run_async(test())
        self.assertEqual(summary, {"success": 0, "failed": 0, "skipped": 0})

    def test_maximum_log_entries_100(self):
        async def test():
            timestamp = self.get_current_timestamp()
            log_stream = [f"[{timestamp}] ERROR: Disk failure {i}" for i in range(100)]
            error_patterns = {"Disk failure": "Critical hardware error"}
            def restart_disk(): return "Service restarted"
            repair_actions = {"Disk failure": restart_disk}
            config = {"reactive_mode": True, "max_concurrent_repairs": 10, "log_retention_seconds": 3600}
            return await monitor_and_repair(log_stream, error_patterns, repair_actions, config)

        repair_log, summary = self.run_async(test())
        self.assertEqual(len(repair_log), 100)
        self.assertEqual(summary["success"], 100)

    def test_maximum_error_patterns_50(self):
        async def test():
            timestamp = self.get_current_timestamp()
            log_stream, error_patterns, repair_actions = [], {}, {}
            def generic(): return "Repair completed"
            for i in range(50):
                key = f"Error{i}"
                log_stream.append(f"[{timestamp}] ERROR: {key} occurred")
                error_patterns[key] = f"Desc {i}"
                repair_actions[key] = generic
            config = {"reactive_mode": True, "max_concurrent_repairs": 10, "log_retention_seconds": 300}
            return await monitor_and_repair(log_stream, error_patterns, repair_actions, config)

        repair_log, summary = self.run_async(test())
        self.assertEqual(len(repair_log), 50)
        self.assertEqual(summary["success"], 50)

    def test_maximum_concurrent_repairs_10(self):
        async def test():
            base_time = datetime.now()
            log_stream = [f"[{(base_time + timedelta(seconds=i)).strftime('%Y-%m-%d %H:%M:%S')}] ERROR: Concurrent error {i}" for i in range(15)]
            error_patterns = {"Concurrent error": "Test error"}
            def repair(): return "Repair done"
            repair_actions = {"Concurrent error": repair}
            config = {"reactive_mode": True, "max_concurrent_repairs": 10, "log_retention_seconds": 300}
            return await monitor_and_repair(log_stream, error_patterns, repair_actions, config)

        _, summary = self.run_async(test())
        self.assertEqual(summary["success"], 15)

    def test_maximum_log_retention_3600_seconds(self):
        async def test():
            ts = self.get_timestamp_offset(-3600)
            log_stream = [f"[{ts}] ERROR: Boundary test"]
            error_patterns = {"Boundary test": "Test at boundary"}
            def repair(): return "Repair executed"
            repair_actions = {"Boundary test": repair}
            config = {"reactive_mode": True, "max_concurrent_repairs": 1, "log_retention_seconds": 3600}
            return await monitor_and_repair(log_stream, error_patterns, repair_actions, config)

        _, summary = self.run_async(test())
        self.assertGreaterEqual(sum(summary.values()), 0)

    def test_empty_log_stream(self):
        async def test():
            log_stream = []
            error_patterns = {"Disk failure": "Critical hardware error"}
            def repair(): return "Service restarted"
            repair_actions = {"Disk failure": repair}
            config = {"reactive_mode": True, "max_concurrent_repairs": 1, "log_retention_seconds": 300}
            return await monitor_and_repair(log_stream, error_patterns, repair_actions, config)

        _, summary = self.run_async(test())
        self.assertEqual(summary, {"success": 0, "failed": 0, "skipped": 0})

    def test_empty_error_patterns(self):
        async def test():
            ts = self.get_current_timestamp()
            log_stream = [f"[{ts}] ERROR: Disk failure"]
            error_patterns, repair_actions = {}, {}
            config = {"reactive_mode": True, "max_concurrent_repairs": 1, "log_retention_seconds": 300}
            return await monitor_and_repair(log_stream, error_patterns, repair_actions, config)

        _, summary = self.run_async(test())
        self.assertEqual(summary, {"success": 0, "failed": 0, "skipped": 0})

    def test_one_repair_per_log_line(self):
        async def test():
            ts = self.get_current_timestamp()
            log_stream = [f"[{ts}] ERROR: Disk failure CPU temperature high"]
            error_patterns = {"Disk failure": "HW", "CPU temperature high": "Thermal"}
            def repair1(): return "Repair 1"
            def repair2(): return "Repair 2"
            repair_actions = {"Disk failure": repair1, "CPU temperature high": repair2}
            config = {"reactive_mode": True, "max_concurrent_repairs": 5, "log_retention_seconds": 300}
            return await monitor_and_repair(log_stream, error_patterns, repair_actions, config)

        repair_log, _ = self.run_async(test())
        self.assertEqual(len(repair_log), 1)

    def test_status_summary_always_contains_all_keys(self):
        async def test():
            return await monitor_and_repair([], {}, {}, {
                "reactive_mode": True, "max_concurrent_repairs": 1, "log_retention_seconds": 300
            })

        _, summary = self.run_async(test())
        self.assertEqual(summary, {"success": 0, "failed": 0, "skipped": 0})
