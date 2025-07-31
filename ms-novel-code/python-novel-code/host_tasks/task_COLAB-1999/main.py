"""
Simplified cron job scheduler that runs tasks.

It is based on interval and priority.
"""

import time
from typing import List, Dict, Any
import datetime


def start_scheduler(tasks: List[Dict[str, Any]]) -> None:
    """Start a simplified cron job scheduler.

    This function runs a continuous loop that checks and executes scheduled
    tasks based on their configured interval and priority.

    Args:
        tasks (List[Dict[str, Any]]): A list of task dictionaries. Each task
        must contain "name", "interval", "priority", and "function" keys.
    """
    if not tasks:
        print("Scheduler started with no tasks.")
        return

    if len(tasks) > 100:
        print("Error: Maximum of 100 tasks can be scheduled.")
        return

    scheduled_tasks = {}
    task_names = set()

    for task in tasks:
        name = task.get("name")
        interval = task.get("interval")
        priority = task.get("priority")
        function = task.get("function")

        if not isinstance(name, str) or not name:
            print(f"Error: Task name '{name}' is invalid. Skipping task.")
            continue
        if name in task_names:
            print(f"Error: Duplicate task name '{name}'. Skipping task.")
            continue
        task_names.add(name)

        if not isinstance(interval, int) or interval <= 0:
            print(
                f"Error: Task '{name}' has an invalid interval "
                f"({interval}). Skipping task."
            )
            continue

        if not isinstance(priority, int):
            print(
                f"Error: Task '{name}' has an invalid priority "
                f"({priority}). Skipping task."
            )
            continue

        if not callable(function):
            print(f"Error: Task '{name}'"
                  f" has an invalid function. Skipping task.")
            continue

        scheduled_tasks[name] = {
            "interval": interval,
            "priority": priority,
            "function": function,
            "next_run_time": time.time()
        }

    if not scheduled_tasks:
        print("No valid tasks to schedule. Exiting scheduler.")
        return

    print("Scheduler started. Press Ctrl+C to stop.")

    try:
        while True:
            current_time = time.time()
            due_tasks = []

            for name, task_info in scheduled_tasks.items():
                if current_time >= task_info["next_run_time"]:
                    due_tasks.append((
                        task_info["priority"],
                        name,
                        task_info["function"]
                    ))

            due_tasks.sort(key=lambda x: x[0], reverse=True)

            for priority, name, func in due_tasks:
                try:
                    timestamp = datetime.datetime.fromtimestamp(
                        current_time
                    ).strftime('%Y-%m-%d %H:%M:%S')
                    print(
                        f"[{timestamp}] Executing {name} "
                        f"(Priority: {priority})"
                    )
                    func()
                    scheduled_tasks[name]["next_run_time"] = (
                        current_time + scheduled_tasks[name]["interval"]
                    )
                except Exception as e:
                    print(
                        f"[{timestamp}] Error executing task '{name}': {e}"
                    )

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nScheduler stopped by user.")
    except Exception as e:
        print(f"\nAn unexpected error occurred in the scheduler: {e}")

