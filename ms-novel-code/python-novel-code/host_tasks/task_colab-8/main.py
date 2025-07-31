
import asyncio
import re
from datetime import datetime
from typing import Iterable, Dict, Callable, Any, Tuple, List, Optional


async def monitor_and_repair(
    log_stream: Iterable[str],
    error_patterns: Dict[str, str],
    repair_actions: Dict[str, Optional[Callable[[], str]]],
    config: Dict[str, Any]
) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """
    Monitors a stream of system logs, detects errors using pattern matching,
    and triggers asynchronous repair actions based on configurable settings.

    Args:
        log_stream (Iterable[str]): A stream of log entries (e.g., generator or list).
        error_patterns (Dict[str, str]): Mapping of error pattern keywords to descriptions.
        repair_actions (Dict[str, Optional[Callable[[], str]]]):
            Mapping of error keywords to repair functions. A value of None skips repair.
        config (Dict[str, Any]): Configuration options including:
            - "reactive_mode" (bool): If False, disables automatic repair triggering.
            - "max_concurrent_repairs" (int): Maximum number of concurrent repair tasks.
            - "log_retention_seconds" (int): Max age of logs to be considered (in seconds).

    Returns:
        Tuple[List[Dict[str, Any]], Dict[str, int]]:
            - repair_log: List of dictionaries recording each repair attempt.
            - summary: Dictionary with counts of 'success', 'failed', and 'skipped' repairs.
    """
    semaphore = asyncio.Semaphore(config.get("max_concurrent_repairs", 5))
    repair_log: List[Dict[str, Any]] = []
    summary = {"success": 0, "failed": 0, "skipped": 0}

    async def handle_repair(timestamp: str, error_key: str) -> None:
        """
        Handles execution of a single repair task associated with an error key.

        Args:
            timestamp (str): Timestamp of the log triggering the repair.
            error_key (str): Keyword identifying the error.
        """
        description = error_patterns[error_key]
        action_func = repair_actions[error_key]

        # If no repair function is defined, mark as skipped.
        if not callable(action_func):
            repair_log.append({
                "timestamp": timestamp,
                "error": error_key,
                "description": description,
                "action": None,
                "status": "skipped",
                "details": "Invalid repair action"
            })
            summary["skipped"] += 1
            return

        action_name = action_func.__name__

        try:
            # Respect max concurrency using a semaphore.
            async with semaphore:
                result = await action_func() if asyncio.iscoroutinefunction(action_func) else action_func()

                if isinstance(result, str) and (
                    result.lower().startswith("no action") or "skipped" in result.lower()
                ):
                    status = "skipped"
                else:
                    status = "success"
                details = result

        except Exception as e:
            status = "failed"
            details = str(e)

        repair_log.append({
            "timestamp": timestamp,
            "error": error_key,
            "description": description,
            "action": action_name,
            "status": status,
            "details": details
        })
        summary[status] += 1

    async def process_logs() -> None:
        """
        Processes the entire log stream, spawns repair tasks for matched error patterns.
        """
        tasks = []

        for line in log_stream:
            # Parse log entry format: [timestamp] LEVEL: message
            match = re.match(r"\[(.*?)\]\s+(ERROR|WARNING):\s+(.*)", line)
            if not match:
                continue

            timestamp_str, _, message = match.groups()

            try:
                log_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue

            current_time = datetime.now()
            if (current_time - log_time).total_seconds() > config.get("log_retention_seconds", 86400):
                continue

            if not config.get("reactive_mode", True):
                continue

            for pattern in error_patterns:
                if pattern in message:
                    if pattern in repair_actions:
                        tasks.append(handle_repair(timestamp_str, pattern))
                    else:
                        # Error matches pattern but no repair action is defined
                        repair_log.append({
                            "timestamp": timestamp_str,
                            "error": pattern,
                            "description": error_patterns[pattern],
                            "action": None,
                            "status": "skipped",
                            "details": "No repair action assigned"
                        })
                        summary["skipped"] += 1
                    break

        if tasks:
            await asyncio.gather(*tasks)

    await process_logs()
    return repair_log, summary
