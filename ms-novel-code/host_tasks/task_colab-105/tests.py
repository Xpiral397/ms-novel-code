# tests

import unittest
from main import TaskQueue

class TestTaskQueue(unittest.TestCase):

    def setUp(self):
        self.queue = TaskQueue()

    def tearDown(self):
        self.queue = None

    def test_add_single_task_and_get(self):
        self.queue.add_task("task1", 5)
        result = self.queue.get_next_task()
        self.assertEqual(result, "task1")
        result = self.queue.get_next_task()
        self.assertEqual(result, "NO TASKS")

    def test_add_multiple_tasks_priority_order(self):
        self.queue.add_task("low_priority", 10)
        self.queue.add_task("high_priority", 2)
        self.queue.add_task("medium_priority", 5)
        self.assertEqual(self.queue.get_next_task(), "high_priority")
        self.assertEqual(self.queue.get_next_task(), "medium_priority")
        self.assertEqual(self.queue.get_next_task(), "low_priority")

    def test_same_priority_fifo_order(self):
        self.queue.add_task("first", 5)
        self.queue.add_task("second", 5)
        self.queue.add_task("third", 5)
        self.assertEqual(self.queue.get_next_task(), "first")
        self.assertEqual(self.queue.get_next_task(), "second")
        self.assertEqual(self.queue.get_next_task(), "third")

    def test_update_existing_task_priority(self):
        self.queue.add_task("task1", 10)
        self.queue.add_task("task2", 5)
        self.queue.add_task("task1", 1)
        self.assertEqual(self.queue.get_next_task(), "task1")
        self.assertEqual(self.queue.get_next_task(), "task2")

    def test_update_task_same_priority_new_order(self):
        self.queue.add_task("task1", 5)
        self.queue.add_task("task2", 5)
        self.queue.add_task("task3", 5)

        self.queue.add_task("task1", 5)

        self.assertEqual(self.queue.get_next_task(), "task2")
        self.assertEqual(self.queue.get_next_task(), "task3")
        self.assertEqual(self.queue.get_next_task(), "task1")

    def test_peek_without_removing(self):
        self.queue.add_task("task1", 10)
        self.queue.add_task("task2", 5)
        self.assertEqual(self.queue.peek_next_task(), "task2")
        self.assertEqual(self.queue.peek_next_task(), "task2")
        self.assertEqual(self.queue.get_next_task(), "task2")

    def test_peek_empty_queue(self):
        self.assertEqual(self.queue.peek_next_task(), "NO TASKS")

    def test_get_empty_queue(self):
        self.assertEqual(self.queue.get_next_task(), "NO TASKS")

    def test_mixed_operations_sequence(self):
        self.queue.add_task("email_processing", 5)
        self.queue.add_task("data_backup", 2)
        self.assertEqual(self.queue.get_next_task(), "data_backup")
        self.queue.add_task("system_update", 2)
        self.assertEqual(self.queue.peek_next_task(), "system_update")
        self.queue.add_task("email_processing", 1)
        self.assertEqual(self.queue.get_next_task(), "email_processing")
        self.assertEqual(self.queue.get_next_task(), "system_update")
        self.assertEqual(self.queue.peek_next_task(), "NO TASKS")

    def test_boundary_priority_values(self):
        self.queue.add_task("min_priority", 1000000)
        self.queue.add_task("max_priority", 1)
        self.assertEqual(self.queue.get_next_task(), "max_priority")
        self.assertEqual(self.queue.get_next_task(), "min_priority")

    def test_large_number_of_tasks(self):
        for i in range(1000):
            self.queue.add_task(f"task_{i}", i % 100 + 1)

        first_task = self.queue.get_next_task()
        self.assertIn("task_", first_task)


        second_task = self.queue.get_next_task()
        self.assertIn("task_", second_task)
        self.assertNotEqual(first_task, second_task)

    def test_task_name_edge_cases(self):
        long_name = "a" * 100
        self.queue.add_task(long_name, 5)
        special_name = "task_with_special-chars.123"
        self.queue.add_task(special_name, 3)
        self.assertEqual(self.queue.get_next_task(), special_name)
        self.assertEqual(self.queue.get_next_task(), long_name)

    def test_multiple_updates_same_task(self):
        self.queue.add_task("task1", 10)
        self.queue.add_task("task2", 5)
        self.queue.add_task("task1", 8)
        self.queue.add_task("task1", 3)
        self.queue.add_task("task1", 1)
        self.assertEqual(self.queue.get_next_task(), "task1")
        self.assertEqual(self.queue.get_next_task(), "task2")

    def test_complex_priority_and_fifo_interaction(self):
        self.queue.add_task("low1", 10)
        self.queue.add_task("high1", 2)
        self.queue.add_task("low2", 10)
        self.queue.add_task("high2", 2)
        self.queue.add_task("medium", 5)
        self.assertEqual(self.queue.get_next_task(), "high1")
        self.assertEqual(self.queue.get_next_task(), "high2")
        self.assertEqual(self.queue.get_next_task(), "medium")
        self.assertEqual(self.queue.get_next_task(), "low1")
        self.assertEqual(self.queue.get_next_task(), "low2")

    def test_peek_after_updates(self):
        self.queue.add_task("task1", 10)
        self.queue.add_task("task2", 5)
        self.assertEqual(self.queue.peek_next_task(), "task2")
        self.queue.add_task("task1", 1)
        self.assertEqual(self.queue.peek_next_task(), "task1")
        self.assertEqual(self.queue.get_next_task(), "task1")
        self.assertEqual(self.queue.peek_next_task(), "task2")
