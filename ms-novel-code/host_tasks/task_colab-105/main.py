"""Module to define the TaskQueue class which manages task scheduling."""

import heapq


class TaskQueue:
    """Manages a priority-based task queue."""

    def __init__(self):
        """Initialize the task queue with a heap, task map, and counter."""
        self._heap = []
        self._task_map = {}
        self._counter = 0

    def add_task(self, task_name: str, priority: int) -> None:
        """
        Add a new task or update an existing task's priority.

        Args:
            task_name (str): Name of the task.
            priority (int): Priority of the task (lower means higher priority).
        """
        self._counter += 1
        insertion_order = self._counter
        self._task_map[task_name] = (priority, insertion_order)
        heapq.heappush(self._heap, (priority, insertion_order, task_name))

    def get_next_task(self) -> str:
        """
        Remove and return the task with the highest priority.

        Returns:
            str: The task name, or "NO TASKS" if the queue is empty.
        """
        while self._heap:
            priority, order, task_name = heapq.heappop(self._heap)
            if self._task_map.get(task_name) == (priority, order):
                del self._task_map[task_name]
                return task_name
        return "NO TASKS"

    def peek_next_task(self) -> str:
        """
        Return the task with the highest priority without removing it.

        Returns:
            str: The task name, or "NO TASKS" if the queue is empty.
        """
        while self._heap:
            priority, order, task_name = self._heap[0]
            if self._task_map.get(task_name) == (priority, order):
                return task_name
            heapq.heappop(self._heap)
        return "NO TASKS"

