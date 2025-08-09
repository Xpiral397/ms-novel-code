
from collections.abc import Callable
from datetime import datetime
from multiprocessing import Process, Queue
from pathlib import Path
from queue import Empty
from typing import Any, Tuple
import time


def _child_worker(func: Callable[[], Any], q: Queue) -> None:
    """
    Execute func and put a tuple ('ok', result) or ('error', exception_instance) into q.
    Handles the case where the result itself is not picklable by sending a synthetic error.
    """
    try:
        result = func()
        try:
            q.put(("ok", result))
        except Exception as put_error:
            # Result not picklable or queue serialization failed.
            q.put(("error", RuntimeError(
                f"result not picklable: {put_error!r}")))
    except Exception as e:
        # Function raised; send the exception instance (usually picklable)
        try:
            q.put(("error", e))
        except Exception as put_error:
            # As a last resort, send a simple, picklable exception
            q.put(("error", RuntimeError(
                f"child failed to send exception: {put_error!r}")))


# Public API
def run_job_with_timeout(func: Callable[[], Any], timeout: float) -> Tuple[str, float, Any | BaseException]:
    """Run func in a child process with a hard timeout.

    Returns (status, duration_sec, payload) where:
      - status is "ok", "timeout", or "error"
      - payload is result (for "ok") or the exception instance (for "error")

    Notes:
      - Uses multiprocessing with a top-level worker for cross-platform 'spawn'.
      - Uses time.monotonic() for duration measurement.
    """
    if not isinstance(timeout, float) or timeout <= 0.0:
        raise ValueError("invalid timeout")

    q: Queue = Queue(maxsize=1)
    p = Process(target=_child_worker, args=(func, q))
    start = time.monotonic()
    p.start()
    p.join(timeout)
    duration = time.monotonic() - start

    if p.is_alive():
        # Timeout: hard stop, ensure cleanup
        p.terminate()
        p.join()
        # Parent should finalize the queue properly even on timeout.
        q.close()
        q.join_thread()
        return "timeout", duration, None

    # Child exited; retrieve outcome non-blockingly with a small timeout
    try:
        status, payload = q.get(timeout=1.0)
    except Empty:
        status, payload = "error", RuntimeError(
            "no result received from child")
    finally:
        q.close()
        q.join_thread()

    return status, duration, payload


def default_follow_up_logger(job_id: str, reason: str, duration_sec: float, log_file: str) -> None:
    """Append a single line describing the timed-out job to log_file.

    The line includes a timestamp, job_id, elapsed time, and reason.
    Ensures parent directories exist when the log_file includes a directory.
    Uses UTF-8 text and context managers.
    """
    if not isinstance(log_file, str) or not log_file:
        raise ValueError("invalid log_file")

    p = Path(log_file)
    # Create parent directory if present (no-op when file is in CWD)
    if p.parent and str(p.parent) not in ("", "."):
        p.parent.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} - Job ID: {job_id}, Reason: {reason}, Elapsed Time: {duration_sec:.6f} seconds\n"
    with p.open("a", encoding="utf-8") as f:
        f.write(line)


def schedule_jobs(
    jobs: list[tuple[str, Callable[[], Any]]],
    timeout: float,
    follow_up: Callable[[str, str, float, str], None],
    log_file: str,
) -> list[dict]:
    """Run jobs sequentially with a per-job hard timeout and follow-up on timeouts.

    Returns a list of dicts with keys: job_id, status, duration_sec, and one of:
      - result (if status == "ok")
      - error (repr of exception, if status == "error")

    Behavior:
      - Validates inputs as per spec.
      - Enforces hard timeout with process.terminate() and cleanup join.
      - Uses time.monotonic() for durations.
      - Calls follow_up only for timeouts; exceptions propagate from follow_up.
      - Maintains deterministic ordering of records.
    """
    # Validate inputs
    if not isinstance(jobs, list) or not all(
        isinstance(j, tuple) and len(j) == 2 and isinstance(
            j[0], str) and callable(j[1])
        for j in jobs
    ):
        raise ValueError("invalid jobs")

    if not isinstance(timeout, float) or timeout <= 0.0:
        raise ValueError("invalid timeout")

    if not callable(follow_up) or not isinstance(log_file, str) or not log_file:
        raise ValueError("invalid follow_up or log_file")

    records: list[dict] = []
    if not jobs:
        # Empty job list: return empty records and do not create logs
        return records

    for job_id, func in jobs:
        status, duration, payload = run_job_with_timeout(func, timeout)
        rec: dict = {"job_id": job_id,
                     "status": status, "duration_sec": duration}

        if status == "ok":
            rec["result"] = payload
        elif status == "error":
            rec["error"] = repr(payload)
        elif status == "timeout":
            # Invoke follow-up immediately; exceptions propagate by design
            follow_up(job_id, "timeout", duration, log_file)
        else:
            # Should never occur; defensive
            rec["error"] = repr(RuntimeError(f"unknown status: {status}"))

        records.append(rec)

    return records
