# tests

"""Unit tests for WorkStealingSimulator."""

import unittest
from main import WorkStealingSimulator


class TestWorkStealingSimulator(unittest.TestCase):
    """Test behaviors of WorkStealingSimulator."""

    def test_init_and_status_empty(self):
        """Initialize workers and check empty status."""
        sim = WorkStealingSimulator()
        output = sim.process_commands(["INIT 3", "STATUS"])
        self.assertEqual(output, [
            "Worker 0: []",
            "Worker 1: []",
            "Worker 2: []"
        ])

    def test_add_and_status(self):
        """Add tasks to workers and verify status."""
        sim = WorkStealingSimulator()
        cmds = ["INIT 2", "ADD 0 taskA", "ADD 1 taskB", "STATUS"]
        output = sim.process_commands(cmds)
        self.assertEqual(output, [
            "Worker 0: [taskA]",
            "Worker 1: [taskB]"
        ])

    def test_start_own_queue(self):
        """Start task on same worker's own queue."""
        sim = WorkStealingSimulator()
        cmds = ["INIT 2", "ADD 0 t1", "START 0", "STATUS"]
        output = sim.process_commands(cmds)
        self.assertEqual(output, [
            "Worker 0: []",
            "Worker 1: []"
        ])

    def test_start_steal(self):
        """Start task by stealing from another worker."""
        sim = WorkStealingSimulator()
        cmds = ["INIT 2", "ADD 1 t2", "START 0", "STATUS"]
        output = sim.process_commands(cmds)
        self.assertEqual(output, [
            "Worker 0: []",
            "Worker 1: []"
        ])

    def test_start_no_tasks(self):
        """Attempt to start when no tasks exist."""
        sim = WorkStealingSimulator()
        cmds = ["INIT 2", "START 0", "STATUS"]
        output = sim.process_commands(cmds)
        self.assertEqual(output, [
            "Worker 0: []",
            "Worker 1: []"
        ])

    def test_multiple_starts_and_steals(self):
        """Test repeated starts across multiple workers."""
        sim = WorkStealingSimulator()
        cmds = [
            "INIT 3", "ADD 0 t1", "ADD 1 t2", "ADD 2 t3",
            "START 0", "START 0", "START 0", "STATUS"
        ]
        output = sim.process_commands(cmds)
        self.assertEqual(output, [
            "Worker 0: []",
            "Worker 1: []",
            "Worker 2: []"
        ])

    def test_status_after_all_consumed(self):
        """Verify status after all tasks are started."""
        sim = WorkStealingSimulator()
        cmds = ["INIT 2", "ADD 0 t1", "START 0", "START 0", "STATUS"]
        output = sim.process_commands(cmds)
        self.assertEqual(output, ["Worker 0: []", "Worker 1: []"])

    def test_add_to_nonzero_worker(self):
        """Add task to a non-zero indexed worker."""
        sim = WorkStealingSimulator()
        cmds = ["INIT 3", "ADD 2 tX", "STATUS"]
        output = sim.process_commands(cmds)
        self.assertEqual(output, [
            "Worker 0: []",
            "Worker 1: []",
            "Worker 2: [tX]"
        ])

    def test_quit_immediately(self):
        """Test quit before other commands."""
        sim = WorkStealingSimulator()
        cmds = ["INIT 2", "QUIT", "STATUS"]
        output = sim.process_commands(cmds)
        self.assertEqual(output, [])

    def test_status_after_quit(self):
        """Check that no status appears after quit."""
        sim = WorkStealingSimulator()
        cmds = ["INIT 2", "ADD 0 t1", "QUIT", "STATUS"]
        output = sim.process_commands(cmds)
        self.assertEqual(output, [])

    def test_max_workers(self):
        """Add tasks to 100 workers and check status."""
        sim = WorkStealingSimulator()
        cmds = ["INIT 100"] + [f"ADD {i} t{i}" for i in range(100)] + ["STATUS"]
        output = sim.process_commands(cmds)
        for i in range(100):
            self.assertEqual(output[i], f"Worker {i}: [t{i}]")

    def test_multiple_status(self):
        """Check correct state across multiple status calls."""
        sim = WorkStealingSimulator()
        cmds = ["INIT 2", "ADD 0 t1", "STATUS", "START 0", "STATUS"]
        output = sim.process_commands(cmds)
        self.assertEqual(output, [
            "Worker 0: [t1]",
            "Worker 1: []",
            "Worker 0: []",
            "Worker 1: []"
        ])

    def test_task_name_constraints(self):
        """Ensure invalid task names are ignored."""
        sim = WorkStealingSimulator()
        cmds = ["INIT 2", "ADD 0 invalid task", "STATUS"]
        output = sim.process_commands(cmds)
        self.assertEqual(output, ["Worker 0: []", "Worker 1: []"])

    def test_start_on_all_empty(self):
        """Start on each worker when all queues are empty."""
        sim = WorkStealingSimulator()
        cmds = ["INIT 3", "START 0", "START 1", "START 2", "STATUS"]
        output = sim.process_commands(cmds)
        self.assertEqual(output, [
            "Worker 0: []",
            "Worker 1: []",
            "Worker 2: []"
        ])


if __name__ == "__main__":
    unittest.main()
