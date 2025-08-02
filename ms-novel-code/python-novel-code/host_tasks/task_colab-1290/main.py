"""
Simulates a multi-worker task scheduler with work stealing logic.

Processes commands like INIT, ADD, START, STATUS, and QUIT to manage
and track worker queues for task distribution and execution.
"""


class WorkStealingSimulator:
    """Simulates task distribution and work stealing among multiple workers."""

    def __init__(self):
        """Initialize the simulator with no workers and default flags."""
        self.num_workers = 0
        self.workers = []
        self._initialized = False  # Flag to ensure INIT is called only once
        self._terminated = False   # Flag to stop processing after QUIT

    def _init_simulator(self, num_workers: int):
        """Initialize worker queues."""
        if self._initialized:
            return
        if not (1 <= num_workers <= 100):
            return
        self.num_workers = num_workers
        self.workers = [[] for _ in range(num_workers)]
        self._initialized = True

    def _add_task(self, worker_id: int, task: str):
        """Add a task to a specific worker's queue if valid."""
        if not self._initialized:
            return
        if not task or ' ' in task or len(task) > 100:
            return
        if 0 <= worker_id < self.num_workers:
            self.workers[worker_id].append(task)

    def _start_worker(self, worker_id: int):
        """Start task execution from the worker or steals a task if idle."""
        if not self._initialized:
            return
        if 0 <= worker_id < self.num_workers:
            if self.workers[worker_id]:
                self.workers[worker_id].pop(0)
            else:
                for i in range(self.num_workers):
                    if i == worker_id:
                        continue
                    if self.workers[i]:
                        self.workers[i].pop(0)
                        return

    def _get_status(self) -> list[str]:
        """Return the current task queue status for all workers."""
        if not self._initialized:
            return []
        status_output = []
        for i, queue in enumerate(self.workers):
            tasks_str = ", ".join(queue)
            status_output.append(f"Worker {i}: [{tasks_str}]")
        return status_output

    def process_commands(self, commands: list[str]) -> list[str]:
        """Process a list of simulation commands."""
        output = []

        for command in commands:
            if self._terminated:
                break

            parts = command.split()
            if not parts:
                continue

            cmd_type = parts[0]

            try:
                if cmd_type == "INIT":
                    if len(parts) == 2:
                        num_workers = int(parts[1])
                        self._init_simulator(num_workers)
                elif cmd_type == "ADD":
                    if len(parts) == 3:
                        worker_id = int(parts[1])
                        task = parts[2]
                        self._add_task(worker_id, task)
                elif cmd_type == "START":
                    if len(parts) == 2:
                        worker_id = int(parts[1])
                        self._start_worker(worker_id)
                elif cmd_type == "STATUS":
                    if len(parts) == 1:
                        output.extend(self._get_status())
                elif cmd_type == "QUIT":
                    if len(parts) == 1:
                        self._terminated = True
                        break
                else:
                    pass  # Unknown command
            except (ValueError, IndexError):
                pass  # Invalid or incomplete command

        return output

