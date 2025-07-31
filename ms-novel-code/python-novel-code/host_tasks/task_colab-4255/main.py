"""QueueProcessor system to manage tasks using queue module."""

import queue
import threading
import time
from typing import Callable, Any, Tuple, Dict


class QueueProcessor:
    """
    A simple queue processing system using Python's built-in queue module.

    The system can add tasks to the queue, process tasks from the queue,
    and gracefully shut down by draining the queue before termination,
    ensuring no tasks are lost.
    """

    def __init__(self) -> None:
        """Initialize the task queue, worker thread, and shutdown flag."""
        self._task_queue: queue.Queue = queue.Queue()
        self._shutdown_flag = threading.Event()
        self._worker_thread: threading.Thread | None = None
        self._lock = threading.Lock()

    def add_task(
        self,
        callable_func: Callable,
        args: Tuple[Any, ...],
        kwargs: Dict[str, Any]
    ) -> None:
        """
        Add a new task to the queue if the system is not shutting down.

        Args:
            callable_func: The function to execute.
            args: A tuple of positional arguments for the function.
            kwargs: A dictionary of keyword arguments for the function.

        Raises:
            ValueError: If the task is not a 3-tuple or has incorrect types.
            RuntimeError: If adding a task while the system is shutting down.
        """
        with self._lock:
            if self._shutdown_flag.is_set():
                raise RuntimeError("Cannot add tasks:"
                                   " system is shutting down.")

            if not isinstance(callable_func, Callable):
                raise ValueError("callable_func must be a callable object.")
            if not isinstance(args, tuple):
                raise ValueError("args must be a tuple.")
            if not isinstance(kwargs, dict):
                raise ValueError("kwargs must be a dictionary.")

            self._task_queue.put((callable_func, args, kwargs))
            print(f"Task added: {callable_func.__name__}")

    def _worker(self) -> None:
        """Continuously process tasks from the queue."""
        while True:
            try:
                task = self._task_queue.get(timeout=0.1)
                callable_func, args, kwargs = task
                try:
                    result = callable_func(*args, **kwargs)
                    print(
                        f"Successfully executed task:"
                        f" {callable_func.__name__}, "
                        f"Result: {result}"
                    )
                except Exception as e:
                    print(f"Error processing task"
                          f" {callable_func.__name__}: {e}")
                finally:
                    self._task_queue.task_done()
            except queue.Empty:
                if self._shutdown_flag.is_set():
                    break
            except Exception as e:
                print(f"Unexpected error in worker thread: {e}")
                if self._shutdown_flag.is_set():
                    break

        print("Worker thread finished processing remaining tasks.")

    def start(self) -> None:
        """Start the worker thread to begin processing tasks."""
        with self._lock:
            if (self._worker_thread is not None
                    and self._worker_thread.is_alive()):
                print("Queue processor is already running.")
                return
            self._shutdown_flag.clear()
            self._worker_thread = threading.Thread(
                target=self._worker,
                name="QueueProcessorWorker"
            )
            self._worker_thread.start()
            print("Queue processor started.")

    def shutdown(self) -> None:
        """
        Shut down the system gracefully after draining the queue.

        This method is thread-safe and idempotent.
        """
        with self._lock:
            if self._shutdown_flag.is_set():
                print("Shutdown already initiated or completed.")
                return

            print("Initiating graceful shutdown...")
            self._shutdown_flag.set()

        print("Waiting for all pending tasks to complete...")
        self._task_queue.join()

        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join()

        print("Queue processor shut down successfully. All tasks processed.")


def start_queue_processor() -> None:
    """
    Initialize and run the queue processor until shutdown is triggered.

    Demonstrate adding tasks and handling shutdown.
    """
    processor = QueueProcessor()
    processor.start()

    def sample_task(task_id: int, duration: float = 0.1):
        """Return success message after sleeping briefly."""
        time.sleep(duration)
        return f"Task {task_id} completed."

    def failing_task(task_id: int):
        """Raise simulated error for the task."""
        raise ValueError(f"Simulated error for Task {task_id}")

    print("\nAdding initial tasks...")
    for i in range(5):
        processor.add_task(sample_task, (i,), {})
    processor.add_task(failing_task, (99,), {})  # A task that will fail

    time.sleep(1)

    print("\nAdding more tasks during operation...")
    for i in range(5, 10):
        processor.add_task(sample_task, (i,), {'duration': 0.05})

    print("\nTriggering shutdown in 2 seconds...")
    time.sleep(2)
    processor.shutdown()

    try:
        processor.add_task(sample_task, (100,), {})
    except RuntimeError as e:
        print(f"\nCaught expected error: {e}")

    print("\nAttempting to call shutdown again (should be idempotent)...")
    processor.shutdown()

    print("\nQueue processor demonstration finished.")


if __name__ == "__main__":
    start_queue_processor()

