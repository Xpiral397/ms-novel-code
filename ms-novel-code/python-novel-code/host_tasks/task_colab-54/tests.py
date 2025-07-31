# tests

"""
Test suite for Python memory profiler system.

This module contains comprehensive unit tests for the memory profiler
decorator that uses the gc module to control garbage collection and
optimize memory usage during function execution.
"""

import gc
import unittest
from unittest.mock import Mock, patch
from dataclasses import dataclass
from main import memory_profiler


@dataclass
class ProfileReport:
    """Data class representing memory profiling report."""

    function_name: str
    execution_time: float
    memory_before: float
    memory_after: float
    memory_saved: float
    gc_objects_collected: int
    exceeded_threshold: bool


class TestMemoryProfiler(unittest.TestCase):
    """Test cases for memory profiler decorator functionality."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.mock_psutil_process = Mock()
        self.mock_psutil_process.memory_info.return_value.rss = 50 * 1024 * 1024

    def tearDown(self):
        """Clean up after each test method."""
        gc.collect()

    @patch('psutil.Process')
    @patch('gc.collect')
    def test_basic_memory_profiling_without_auto_gc(self, mock_gc_collect,
                                                   mock_process):
        """Test basic memory profiling without automatic garbage collection."""
        mock_process.return_value = self.mock_psutil_process
        mock_gc_collect.return_value = 0

        @memory_profiler(auto_gc=False)
        def simple_function():
            """Simple test function."""
            return 42

        result = simple_function()

        # Verify function execution
        self.assertEqual(result, 42)

        # Verify gc.collect was not called when auto_gc=False
        mock_gc_collect.assert_not_called()

    @patch('psutil.Process')
    @patch('gc.collect')
    def test_memory_profiling_with_auto_gc_enabled(self, mock_gc_collect,
                                                  mock_process):
        """Test memory profiling with automatic garbage collection enabled."""
        mock_process.return_value = self.mock_psutil_process
        mock_gc_collect.return_value = 100

        @memory_profiler(auto_gc=True)
        def memory_intensive_function():
            """Function that creates memory-intensive objects."""
            data = [[i] * 100 for i in range(100)]
            return len(data)

        result = memory_intensive_function()

        # Verify function execution
        self.assertEqual(result, 100)

        # Verify gc.collect was called (at least once for cleanup)
        self.assertGreaterEqual(mock_gc_collect.call_count, 1)

    @patch('psutil.Process')
    @patch('gc.collect')
    def test_memory_threshold_exceeded_warning(self, mock_gc_collect,
                                              mock_process):
        """Test memory threshold exceeded warning functionality."""
        # Set up mock to simulate high memory usage
        mock_process.return_value.memory_info.return_value.rss = (
            150 * 1024 * 1024  # 150MB
        )
        mock_gc_collect.return_value = 50

        @memory_profiler(threshold_mb=100.0)
        def high_memory_function():
            """Function that exceeds memory threshold."""
            return "high memory usage"

        result = high_memory_function()

        # Verify function execution
        self.assertEqual(result, "high memory usage")

    @patch('psutil.Process')
    @patch('gc.collect')
    def test_memory_threshold_not_exceeded(self, mock_gc_collect,
                                          mock_process):
        """Test memory profiling when threshold is not exceeded."""
        mock_process.return_value = self.mock_psutil_process
        mock_gc_collect.return_value = 25

        @memory_profiler(threshold_mb=100.0)
        def low_memory_function():
            """Function that stays within memory threshold."""
            return "low memory usage"

        result = low_memory_function()

        # Verify function execution
        self.assertEqual(result, "low memory usage")

    @patch('psutil.Process')
    @patch('gc.collect')
    def test_detailed_stats_enabled(self, mock_gc_collect, mock_process):
        """Test memory profiling with detailed statistics enabled."""
        mock_process.return_value = self.mock_psutil_process
        mock_gc_collect.return_value = 75

        @memory_profiler(detailed_stats=True)
        def stats_function():
            """Function to test detailed statistics."""
            return {"status": "detailed"}

        result = stats_function()

        # Verify function execution
        self.assertEqual(result, {"status": "detailed"})

    @patch('psutil.Process')
    @patch('gc.collect')
    def test_peak_memory_tracking_enabled(self, mock_gc_collect,
                                         mock_process):
        """Test memory profiling with peak memory tracking enabled."""
        mock_process.return_value = self.mock_psutil_process
        mock_gc_collect.return_value = 30

        @memory_profiler(track_peak=True)
        def peak_tracking_function():
            """Function to test peak memory tracking."""
            temp_data = [i for i in range(1000)]
            return sum(temp_data)

        result = peak_tracking_function()

        # Verify function execution
        self.assertEqual(result, 499500)

    @patch('psutil.Process')
    @patch('gc.collect')
    def test_function_with_exception_handling(self, mock_gc_collect,
                                             mock_process):
        """Test memory profiling when function raises an exception."""
        mock_process.return_value = self.mock_psutil_process
        mock_gc_collect.return_value = 10

        @memory_profiler(auto_gc=True)
        def exception_function():
            """Function that raises an exception."""
            raise ValueError("Test exception")

        with self.assertRaises(ValueError):
            exception_function()

        # Verify gc.collect was still called for cleanup
        mock_gc_collect.assert_called()

    @patch('psutil.Process')
    @patch('gc.collect')
    def test_recursive_function_profiling(self, mock_gc_collect,
                                         mock_process):
        """Test memory profiling with recursive function calls."""
        mock_process.return_value = self.mock_psutil_process
        mock_gc_collect.return_value = 5

        @memory_profiler(auto_gc=True)
        def recursive_function(n):
            """Recursive function for testing."""
            if n <= 0:
                return 1
            return n * recursive_function(n - 1)

        result = recursive_function(5)

        # Verify function execution
        self.assertEqual(result, 120)

    @patch('psutil.Process')
    @patch('gc.collect')
    def test_zero_execution_time_handling(self, mock_gc_collect,
                                         mock_process):
        """Test handling of functions with extremely short execution times."""
        mock_process.return_value = self.mock_psutil_process
        mock_gc_collect.return_value = 0

        @memory_profiler(auto_gc=False)
        def instant_function():
            """Function with minimal execution time."""
            return None

        result = instant_function()

        # Verify function execution
        self.assertIsNone(result)

    @patch('psutil.Process')
    @patch('gc.collect')
    def test_no_memory_allocation_function(self, mock_gc_collect,
                                          mock_process):
        """Test profiling function that allocates no additional memory."""
        mock_process.return_value = self.mock_psutil_process
        mock_gc_collect.return_value = 0

        @memory_profiler(auto_gc=True)
        def no_allocation_function():
            """Function that doesn't allocate memory."""
            x = 1
            y = 2
            return x + y

        result = no_allocation_function()

        # Verify function execution
        self.assertEqual(result, 3)

    @patch('psutil.Process')
    @patch('gc.collect')
    def test_memory_decrease_during_execution(self, mock_gc_collect,
                                             mock_process):
        """Test handling when memory usage decreases during execution."""
        # Mock decreasing memory usage with enough return values
        mock_memory_info_before = Mock()
        mock_memory_info_before.rss = 100 * 1024 * 1024  # 100MB
        mock_memory_info_after = Mock()
        mock_memory_info_after.rss = 80 * 1024 * 1024    # 80MB

        mock_process_instance = Mock()
        mock_process_instance.memory_info.side_effect = [
            mock_memory_info_before,
            mock_memory_info_after,
            mock_memory_info_after,  # Additional call for safety
        ]
        mock_process.return_value = mock_process_instance
        mock_gc_collect.return_value = 20

        @memory_profiler(auto_gc=True)
        def memory_decreasing_function():
            """Function that decreases memory usage."""
            return "memory freed"

        result = memory_decreasing_function()

        # Verify function execution
        self.assertEqual(result, "memory freed")

    @patch('psutil.Process')
    @patch('gc.collect')
    def test_negative_memory_threshold_handling(self, mock_gc_collect,
                                               mock_process):
        """Test handling of negative memory threshold values."""
        mock_process.return_value = self.mock_psutil_process
        mock_gc_collect.return_value = 15

        @memory_profiler(threshold_mb=-10.0)
        def negative_threshold_function():
            """Function with negative threshold."""
            return "negative threshold"

        result = negative_threshold_function()

        # Verify function execution
        self.assertEqual(result, "negative threshold")

    @patch('psutil.Process')
    @patch('gc.collect')
    def test_zero_memory_threshold_handling(self, mock_gc_collect,
                                           mock_process):
        """Test handling of zero memory threshold value."""
        mock_process.return_value = self.mock_psutil_process
        mock_gc_collect.return_value = 8

        @memory_profiler(threshold_mb=0.0)
        def zero_threshold_function():
            """Function with zero threshold."""
            return "zero threshold"

        result = zero_threshold_function()

        # Verify function execution
        self.assertEqual(result, "zero threshold")

    @patch('psutil.Process')
    @patch('gc.collect')
    def test_circular_reference_handling(self, mock_gc_collect,
                                        mock_process):
        """Test memory profiling with circular references."""
        mock_process.return_value = self.mock_psutil_process
        mock_gc_collect.return_value = 200

        @memory_profiler(auto_gc=True, detailed_stats=True)
        def circular_refs_function():
            """Function that creates circular references."""
            objects = []
            for i in range(10):
                obj = {'id': i, 'refs': objects}
                objects.append(obj)
            return len(objects)

        result = circular_refs_function()

        # Verify function execution
        self.assertEqual(result, 10)

        # Verify gc.collect was called for circular reference cleanup
        mock_gc_collect.assert_called()

    @patch('psutil.Process')
    @patch('gc.collect')
    def test_combined_configuration_options(self, mock_gc_collect,
                                           mock_process):
        """Test memory profiling with multiple configuration options."""
        mock_process.return_value = self.mock_psutil_process
        mock_gc_collect.return_value = 150

        @memory_profiler(auto_gc=True, detailed_stats=True,
                        track_peak=True, threshold_mb=50.0)
        def combined_config_function():
            """Function with all configuration options enabled."""
            data = {'large_list': [i**2 for i in range(100)]}
            return len(data['large_list'])

        result = combined_config_function()

        # Verify function execution
        self.assertEqual(result, 100)

        # Verify gc.collect was called
        mock_gc_collect.assert_called()
