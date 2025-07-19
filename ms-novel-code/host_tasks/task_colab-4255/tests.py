# tests

"""
Test cases for the QueueProcessor system.

This module contains comprehensive test cases for testing the QueueProcessor
class and its functionality including task addition, processing, exception
handling, and graceful shutdown.
"""

import unittest
import threading
import time
from unittest.mock import patch
from io import StringIO
from main import QueueProcessor, start_queue_processor


class TestQueueProcessor(unittest.TestCase):
    """Test cases for QueueProcessor class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.processor = QueueProcessor()
        self.test_results = []
        self.test_lock = threading.Lock()

    def tearDown(self):
        """Clean up after each test method."""
        if hasattr(self.processor, '_worker_thread'):
            if self.processor._worker_thread.is_alive():
                self.processor.shutdown()
        self.test_results.clear()

    def sample_task(self, value: int, multiplier: int = 1) -> int:
        """
        Sample task function for testing.

        Args:
            value: Integer value to process
            multiplier: Multiplier for the value

        Returns:
            Result of value * multiplier
        """
        result = value * multiplier
        with self.test_lock:
            self.test_results.append(result)
        return result

    def slow_task(self, duration: float = 0.1) -> str:
        """
        Slow task that takes time to complete.

        Args:
            duration: Time to sleep in seconds

        Returns:
            Completion message
        """
        time.sleep(duration)
        with self.test_lock:
            self.test_results.append(f"slow_task_completed_{duration}")
        return f"completed after {duration}s"

    def failing_task(self, error_msg: str = "Test error") -> None:
        """
        Task that always raises an exception.

        Args:
            error_msg: Error message to raise

        Raises:
            ValueError: Always raises with given message
        """
        raise ValueError(error_msg)

    def test_add_single_task_and_process(self):
        """Test adding a single task and processing it."""
        self.processor.start()

        self.processor.add_task(self.sample_task, (5,), {'multiplier': 2})

        # Wait for task to be processed
        time.sleep(0.1)

        with self.test_lock:
            self.assertEqual(len(self.test_results), 1)
            self.assertEqual(self.test_results[0], 10)

        self.processor.shutdown()

    def test_add_multiple_tasks_sequentially(self):
        """Test adding multiple tasks sequentially."""
        self.processor.start()

        for i in range(5):
            self.processor.add_task(self.sample_task, (i,), {'multiplier': 2})

        # Wait for all tasks to be processed
        time.sleep(0.2)

        with self.test_lock:
            self.assertEqual(len(self.test_results), 5)
            expected_results = [i * 2 for i in range(5)]
            self.assertEqual(sorted(self.test_results), sorted(expected_results))

        self.processor.shutdown()

    def test_add_tasks_with_empty_args_and_kwargs(self):
        """Test adding tasks with empty args and kwargs."""
        self.processor.start()

        def simple_task():
            with self.test_lock:
                self.test_results.append("simple_task_completed")
            return "done"

        self.processor.add_task(simple_task, (), {})

        time.sleep(0.1)

        with self.test_lock:
            self.assertEqual(len(self.test_results), 1)
            self.assertEqual(self.test_results[0], "simple_task_completed")

        self.processor.shutdown()

    def test_task_execution_with_exception_handling(self):
        """Test that exceptions in tasks are handled gracefully."""
        self.processor.start()

        # Add a failing task
        self.processor.add_task(self.failing_task, ("Custom error",), {})

        # Add a successful task after the failing one
        self.processor.add_task(self.sample_task, (3,), {'multiplier': 4})

        time.sleep(0.2)

        # The successful task should still complete
        with self.test_lock:
            self.assertEqual(len(self.test_results), 1)
            self.assertEqual(self.test_results[0], 12)

        self.processor.shutdown()

    @patch('sys.stdout', new_callable=StringIO)
    def test_exception_handling_output(self, mock_stdout):
        """Test that exceptions are printed without crashing."""
        self.processor.start()

        self.processor.add_task(self.failing_task, ("Test exception",), {})

        time.sleep(0.1)
        self.processor.shutdown()

        output = mock_stdout.getvalue()
        self.assertIn("Error processing task", output)
        self.assertIn("Test exception", output)

    def test_graceful_shutdown_with_pending_tasks(self):
        """Test graceful shutdown with tasks still in queue."""
        self.processor.start()

        # Add multiple tasks
        for i in range(3):
            self.processor.add_task(self.sample_task, (i,), {'multiplier': 1})

        # Shutdown immediately
        self.processor.shutdown()

        # All tasks should be processed
        with self.test_lock:
            self.assertEqual(len(self.test_results), 3)
            self.assertEqual(sorted(self.test_results), [0, 1, 2])

    def test_shutdown_with_long_running_task(self):
        """Test shutdown waits for long-running tasks to complete."""
        self.processor.start()

        # Add a slow task
        self.processor.add_task(self.slow_task, (0.2,), {})

        # Start shutdown
        start_time = time.time()
        self.processor.shutdown()
        end_time = time.time()

        # Should have waited for the task to complete
        self.assertGreater(end_time - start_time, 0.2)

        with self.test_lock:
            self.assertEqual(len(self.test_results), 1)
            self.assertEqual(self.test_results[0], "slow_task_completed_0.2")

    def test_reject_tasks_after_shutdown_initiated(self):
        """Test that tasks are rejected after shutdown is initiated."""
        self.processor.start()

        # Start shutdown in a separate thread
        shutdown_thread = threading.Thread(target=self.processor.shutdown)
        shutdown_thread.start()

        # Try to add a task after shutdown started
        time.sleep(0.05)  # Small delay to ensure shutdown started

        # This should not add the task
        with self.assertRaises(RuntimeError):
            self.processor.add_task(self.sample_task, (10,), {})

    def test_multiple_shutdown_calls_idempotent(self):
        """Test that multiple shutdown calls are handled safely."""
        self.processor.start()

        # First shutdown
        self.processor.shutdown()

        # Second shutdown should not cause issues
        self.processor.shutdown()

    def test_shutdown_with_empty_queue(self):
        """Test shutdown with no tasks in queue."""
        self.processor.start()

        # Shutdown immediately without adding tasks
        self.processor.shutdown()

        # Should complete without errors
        with self.test_lock:
            self.assertEqual(len(self.test_results), 0)

    def test_concurrent_task_additions(self):
        """Test adding tasks concurrently from multiple threads."""
        self.processor.start()

        def add_tasks(start_value: int, count: int):
            for i in range(count):
                self.processor.add_task(
                    self.sample_task,
                    (start_value + i,),
                    {'multiplier': 1}
                )

        # Create multiple threads to add tasks
        threads = []
        for i in range(3):
            thread = threading.Thread(target=add_tasks, args=(i * 10, 5))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Wait for processing
        time.sleep(0.3)

        with self.test_lock:
            self.assertEqual(len(self.test_results), 15)

        self.processor.shutdown()

    def test_invalid_task_parameters(self):
        """Test handling of invalid task parameters."""
        self.processor.start()

        # Test with invalid callable
        with self.assertRaises(ValueError):
            self.processor.add_task("not_a_function", (), {})

        # Test with invalid args (not a tuple)
        with self.assertRaises(ValueError):
            self.processor.add_task(self.sample_task, "not_a_tuple", {})

        # Test with invalid kwargs (not a dict)
        with self.assertRaises(ValueError):
            self.processor.add_task(self.sample_task, (), "not_a_dict")

        self.processor.shutdown()

    def test_task_with_non_standard_exception(self):
        """Test handling of non-standard exceptions in tasks."""
        self.processor.start()

        def custom_exception_task():
            class CustomError(Exception):
                """Base Class for custom error."""
            raise CustomError("Custom exception message")

        self.processor.add_task(custom_exception_task, (), {})

        # Add a normal task after the exception
        self.processor.add_task(self.sample_task, (1,), {'multiplier': 5})

        time.sleep(0.2)

        # The normal task should still complete
        with self.test_lock:
            self.assertEqual(len(self.test_results), 1)
            self.assertEqual(self.test_results[0], 5)

        self.processor.shutdown()

    def test_high_volume_task_processing(self):
        """Test processing a high volume of tasks."""
        self.processor.start()

        task_count = 100
        for i in range(task_count):
            self.processor.add_task(self.sample_task, (i,), {'multiplier': 1})

        # Wait for all tasks to be processed
        time.sleep(1.0)

        with self.test_lock:
            self.assertEqual(len(self.test_results), task_count)
            expected_results = list(range(task_count))
            self.assertEqual(sorted(self.test_results), expected_results)

        self.processor.shutdown()

    def test_worker_thread_state_after_shutdown(self):
        """Test that worker thread terminates properly after shutdown."""
        self.processor.start()

        # Verify worker thread is alive
        self.assertTrue(self.processor._worker_thread.is_alive())

        # Shutdown
        self.processor.shutdown()

        # Worker thread should be terminated
        self.assertFalse(self.processor._worker_thread.is_alive())


class TestStartQueueProcessor(unittest.TestCase):
    """Test cases for start_queue_processor function."""

    @patch('builtins.input', return_value='quit')
    def test_start_queue_processor_basic(self, mock_input):
        """Test basic functionality of start_queue_processor."""
        # This test assumes the function exists and can be called
        # The actual implementation would need to be tested based on
        # how the function is designed to work
        try:
            start_queue_processor()
        except NameError:
            # Function not implemented yet
            self.skipTest("start_queue_processor not implemented")
