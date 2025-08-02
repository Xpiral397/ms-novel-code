"""
A persistent job scheduler using the 'schedule' package.

This module defines a `JobScheduler` class that can schedule and run jobs
at specified intervals, with the ability to save and load job state
to and from a local JSON file.
"""

import json
import logging
import os
import time
from typing import Any, Dict, List

import schedule

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S'
)


class JobScheduler:
    """Schedule and manage jobs with state persistence to a local JSON file."""

    def __init__(self, state_file: str) -> None:
        """
        Initialize the scheduler.

        :param state_file: The path to the file for persisting job state.
        """
        self.state_file = state_file
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self.known_actions = {
            'print_message': self._print_message,
        }

    def _print_message(self, *args: Any) -> None:
        """
        Print a message to the console.

        This is a predefined job action.
        """
        message = ' '.join(str(arg) for arg in args)
        logging.info(f"Executed job "
                     f"{schedule.get_jobs()[0].job_id}: {message}")

    def add_job(
        self,
        job_id: str,
        interval: int,
        unit: str,
        action: str,
        args: List[Any]
    ) -> None:
        """
        Add a new job to the scheduler.

        :param job_id: A unique identifier for the job.
        :param interval: The frequency interval.
        :param unit: The time unit (e.g., 'seconds', 'minutes').
        :param action: The name of the action function to call.
        :param args: A list of arguments to pass to the action.
        """
        if job_id in self.jobs:
            logging.warning(
                f"Job ID '{job_id}' already exists. Skipping addition."
            )
            return

        if not self._validate_job(job_id, interval, unit, action, args):
            return

        job_definition = {
            "id": job_id,
            "interval": interval,
            "unit": unit,
            "action": action,
            "args": args
        }
        self.jobs[job_id] = job_definition
        self._schedule_job(job_definition)

    def _validate_job(
        self,
        job_id: str,
        interval: int,
        unit: str,
        action: str,
        args: List[Any]
    ) -> bool:
        """
        Validate a job's definition.

        :return: True if valid, else False.
        """
        if not all([job_id, interval, unit, action]):
            logging.error(
                f"Invalid job definition for job_id '{job_id}': "
                "Missing required fields."
            )
            return False

        if (not isinstance(job_id, str)
                or not job_id.isalnum() or len(job_id) > 64):
            logging.error(
                f"Invalid job ID '{job_id}'. Must be a non-empty "
                "alphanumeric string (max 64 chars)."
            )
            return False

        if not isinstance(interval, int) or not 1 <= interval <= 1000000:
            logging.error(
                f"Invalid interval for job '{job_id}'. Must be a "
                "positive integer (1-1,000,000)."
            )
            return False

        if unit not in ["seconds", "minutes", "hours", "days"]:
            logging.error(
                f"Invalid time unit '{unit}' for job '{job_id}'. "
                "Must be one of 'seconds', 'minutes', 'hours', 'days'."
            )
            return False

        if action not in self.known_actions:
            logging.error(
                f"Unknown action '{action}' for job '{job_id}'. "
                "Action must be predefined."
            )
            return False

        try:
            json.dumps(args)
        except TypeError:
            logging.error(
                f"Arguments for job '{job_id}' are not JSON-serializable."
            )
            return False

        return True

    def _schedule_job(self, job_definition: Dict[str, Any]) -> None:
        """Schedule a single job using the 'schedule' package."""
        job_id = job_definition["id"]
        interval = job_definition["interval"]
        unit = job_definition["unit"]
        action = job_definition["action"]
        args = job_definition.get("args", [])

        action_func = self.known_actions.get(action)
        if not action_func:
            logging.error(
                f"Cannot schedule job '{job_id}'. Action '{action}' "
                "is not defined."
            )
            return

        try:
            job = getattr(schedule.every(interval), unit).do(
                action_func, *args
            )
            job.job_id = job_id
            logging.info(
                f"Scheduled job '{job_id}' to run every {interval} {unit}."
            )
        except Exception as e:
            logging.error(f"Failed to schedule job '{job_id}': {e}")

    def start(self) -> None:
        """
        Start the scheduler's main loop.

        This method loads any existing jobs from the state file before
        starting the execution loop.
        """
        self.load_jobs()
        logging.info("Scheduler started.")
        try:
            while True:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            self.shutdown()

    def shutdown(self) -> None:
        """Shut down the scheduler and save the current job state."""
        logging.info("Scheduler shutting down...")
        self.save_jobs()
        schedule.clear()
        logging.info("Scheduler has been shut down and state saved.")

    def load_jobs(self) -> None:
        """
        Load and schedule jobs from the state file.

        Clears existing jobs before loading to prevent duplication on restart.
        """
        self.jobs.clear()
        schedule.clear()

        if not os.path.exists(self.state_file):
            logging.warning(
                f"State file '{self.state_file}' not found. "
                "Starting with no jobs."
            )
            return

        try:
            with open(self.state_file, 'r') as f:
                job_definitions = json.load(f)

            if not isinstance(job_definitions, list):
                logging.error(
                    f"Corrupted state file"
                    f" '{self.state_file}': Expected a list."
                )
                return

            logging.info(f"Loading jobs from '{self.state_file}'...")
            for job_def in job_definitions:
                try:
                    self.add_job(
                        job_id=job_def.get("id"),
                        interval=job_def.get("interval"),
                        unit=job_def.get("unit"),
                        action=job_def.get("action"),
                        args=job_def.get("args", [])
                    )
                except Exception as e:
                    logging.error(
                        f"Failed to load job from definition {job_def}: {e}"
                    )

        except json.JSONDecodeError:
            logging.error(
                f"Invalid JSON in state file '{self.state_file}'. "
                "Starting with no jobs."
            )
        except IOError as e:
            logging.error(
                f"Failed to read state file '{self.state_file}': {e}"
            )

    def save_jobs(self) -> None:
        """Save the current list of job definitions to the state file."""
        job_definitions = list(self.jobs.values())
        try:
            with open(self.state_file, 'w') as f:
                json.dump(job_definitions, f, indent=2)
            logging.info(
                f"Saved {len(job_definitions)} jobs to '{self.state_file}'."
            )
        except IOError as e:
            logging.error(
                f"Failed to write to state file '{self.state_file}': {e}"
            )
        except TypeError as e:
            logging.error(f"Error serializing job definitions: {e}")


if __name__ == "__main__":
    STATE_FILE = "jobs_state.json"

    initial_jobs = [
        {
            "id": "job1",
            "interval": 5,
            "unit": "seconds",
            "action": "print_message",
            "args": ["Job 1 executed"]
        },
        {
            "id": "job2",
            "interval": 1,
            "unit": "minutes",
            "action": "print_message",
            "args": ["Job 2 running every minute"]
        },
        {
            "id": "job3_invalid",
            "interval": -10,
            "unit": "seconds",
            "action": "print_message",
            "args": ["This job should be ignored"]
        },
        {
            "id": "job4_unknown_action",
            "interval": 10,
            "unit": "seconds",
            "action": "unknown_function",
            "args": []
        }
    ]

    if not os.path.exists(STATE_FILE):
        logging.info(
            f"Creating initial job state file '{STATE_FILE}' for first run."
        )
        try:
            with open(STATE_FILE, 'w') as f:
                json.dump(initial_jobs, f, indent=2)
        except IOError as e:
            logging.error(f"Could not create initial state file: {e}")

    scheduler = JobScheduler(state_file=STATE_FILE)
    scheduler.start()

