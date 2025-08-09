
"""Async log file processor with error simulation and validation."""

import asyncio
from typing import List, Dict, Any

ERROR_TYPE_MAP = {
    "file_not_found": "FileNotFoundError",
    "permission_denied": "PermissionError",
    "timeout": "TimeoutError"
}


def validate_file_id(file_id: str) -> bool:
    """Validates file ID format."""
    return bool(file_id) and all(
        c.isalnum() or c == '-' for c in file_id
    )


def validate_file_path(file_path: str) -> bool:
    """Validates file path format."""
    return (
        isinstance(file_path, str)
        and file_path.startswith('/')
        and '/' in file_path[1:]
    )


def validate_expected_lines(expected_lines: Any) -> bool:
    """Checks if expected lines are within valid range."""
    return isinstance(expected_lines, int) and 1 <= expected_lines <= 1000


def normalize_error_type(error_type: Any) -> str:
    """Returns normalized error type if valid."""
    if error_type in ERROR_TYPE_MAP:
        return error_type
    return None


async def process_log_file(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Processes a single log file config asynchronously."""
    file_id = cfg.get("file_id")
    file_path = cfg.get("file_path")
    timeout = cfg.get("timeout")
    expected_lines = cfg.get("expected_lines")
    error_type = normalize_error_type(cfg.get("error_type"))

    if (
        not validate_file_id(file_id)
        or not validate_file_path(file_path)
        or not validate_expected_lines(expected_lines)
    ):
        return {
            "file_id": file_id,
            "status": "error",
            "error_type": "FileNotFoundError"
        }

    if not isinstance(timeout, (int, float)) or timeout <= 0.0:
        error_type = "timeout"

    async def simulate_success():
        await asyncio.sleep(min(timeout, 0.05))
        return {
            "file_id": file_id,
            "status": "success",
            "line_count": expected_lines
        }

    async def simulate_error(error_type):
        await asyncio.sleep(min(timeout, 0.01))
        return {
            "file_id": file_id,
            "status": "error",
            "error_type": ERROR_TYPE_MAP[error_type]
        }

    if error_type == "file_not_found":
        return await simulate_error("file_not_found")
    elif error_type == "permission_denied":
        return await simulate_error("permission_denied")
    elif error_type == "timeout":
        return await simulate_error("timeout")
    else:
        try:
            return await asyncio.wait_for(
                simulate_success(), timeout=timeout
            )
        except asyncio.TimeoutError:
            return {
                "file_id": file_id,
                "status": "error",
                "error_type": "TimeoutError"
            }


def analyze_log_files(log_files: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyzes multiple log files asynchronously and summarizes results."""
    async def runner():
        log_files_limited = log_files[:50]
        tasks = [process_log_file(cfg) for cfg in log_files_limited]
        results = await asyncio.gather(*tasks)
        total_lines = sum(
            r.get("line_count", 0)
            for r in results if r.get("status") == "success"
        )
        successful_files = sum(
            1 for r in results if r.get("status") == "success"
        )
        error_summary = {
            "FileNotFoundError": sum(
                1 for r in results if r.get("error_type") == "FileNotFoundError"
            ),
            "PermissionError": sum(
                1 for r in results if r.get("error_type") == "PermissionError"
            ),
            "TimeoutError": sum(
                1 for r in results if r.get("error_type") == "TimeoutError"
            ),
        }
        return {
            "total_lines": total_lines,
            "successful_files": successful_files,
            "error_summary": error_summary,
            "file_results": results
        }

    return asyncio.run(runner())


def driver():
    """Driver for running all test scenarios."""
    print("Example 1:")
    log_files1 = [
        {
            "file_id": "srv1",
            "file_path": "/var/log/app.log",
            "timeout": 0.2,
            "expected_lines": 34,
            "error_type": None
        },
        {
            "file_id": "srv2",
            "file_path": "/var/log/err.log",
            "timeout": 0.3,
            "expected_lines": 28,
            "error_type": "file_not_found"
        },
        {
            "file_id": "srv3",
            "file_path": "/var/log/sys.log",
            "timeout": 0.1,
            "expected_lines": 55,
            "error_type": None
        }
    ]
    print(analyze_log_files(log_files1))

    print("\nExample 2:")
    log_files2 = [
        {
            "file_id": "monitor",
            "file_path": "/logs/mon.log",
            "timeout": 0.05,
            "expected_lines": 42,
            "error_type": "timeout"
        },
        {
            "file_id": "backup",
            "file_path": "/logs/bak.log",
            "timeout": 0.4,
            "expected_lines": 18,
            "error_type": "permission_denied"
        }
    ]
    print(analyze_log_files(log_files2))

    print("\nExample 3:")
    log_files3 = [
        {
            "file_id": "web-server-01",
            "file_path": "/logs/web.log",
            "timeout": 0.3,
            "expected_lines": 45,
            "error_type": None
        },
        {
            "file_id": "api-gateway",
            "file_path": "/logs/api.log",
            "timeout": 0.1,
            "expected_lines": 32,
            "error_type": "file_not_found"
        },
        {
            "file_id": "database-01",
            "file_path": "/logs/db.log",
            "timeout": 0.5,
            "expected_lines": 67,
            "error_type": None
        },
        {
            "file_id": "cache-redis",
            "file_path": "/logs/cache.log",
            "timeout": 0.2,
            "expected_lines": 28,
            "error_type": "permission_denied"
        },
        {
            "file_id": "auth-service",
            "file_path": "/logs/auth.log",
            "timeout": 0.4,
            "expected_lines": 44,
            "error_type": None
        }
    ]
    print(analyze_log_files(log_files3))

    print("\nEdge Case: Empty input")
    print(analyze_log_files([]))

    print("\nEdge Case: All succeed")
    log_files4 = [
        {
            "file_id": "a1",
            "file_path": "/a/a.log",
            "timeout": 0.1,
            "expected_lines": 10,
            "error_type": None
        },
        {
            "file_id": "b2",
            "file_path": "/b/b.log",
            "timeout": 0.2,
            "expected_lines": 20,
            "error_type": None
        }
    ]
    print(analyze_log_files(log_files4))

    print("\nEdge Case: All fail")
    log_files5 = [
        {
            "file_id": "x1",
            "file_path": "/x/x.log",
            "timeout": 0.1,
            "expected_lines": 10,
            "error_type": "file_not_found"
        },
        {
            "file_id": "y2",
            "file_path": "/y/y.log",
            "timeout": 0.2,
            "expected_lines": 20,
            "error_type": "permission_denied"
        },
        {
            "file_id": "z3",
            "file_path": "/z/z.log",
            "timeout": 0.0,
            "expected_lines": 30,
            "error_type": None
        }
    ]
    print(analyze_log_files(log_files5))

    print("\nEdge Case: Timeout 0.0 and negative timeout")
    log_files6 = [
        {
            "file_id": "t1",
            "file_path": "/t/t.log",
            "timeout": 0.0,
            "expected_lines": 5,
            "error_type": None
        },
        {
            "file_id": "t2",
            "file_path": "/t/t2.log",
            "timeout": -1.0,
            "expected_lines": 6,
            "error_type": None
        }
    ]
    print(analyze_log_files(log_files6))

    print("\nEdge Case: Duplicate file_id")
    log_files7 = [
        {
            "file_id": "dup",
            "file_path": "/dup/1.log",
            "timeout": 0.1,
            "expected_lines": 7,
            "error_type": None
        },
        {
            "file_id": "dup",
            "file_path": "/dup/2.log",
            "timeout": 0.1,
            "expected_lines": 8,
            "error_type": "file_not_found"
        }
    ]
    print(analyze_log_files(log_files7))

    print("\nEdge Case: Invalid error_type")
    log_files8 = [
        {
            "file_id": "inv",
            "file_path": "/inv/1.log",
            "timeout": 0.1,
            "expected_lines": 9,
            "error_type": "unknown_error"
        }
    ]
    print(analyze_log_files(log_files8))

    print("\nEdge Case: Invalid file_id, file_path, expected_lines")
    log_files9 = [
        {
            "file_id": "",
            "file_path": "/valid.log",
            "timeout": 0.1,
            "expected_lines": 10,
            "error_type": None
        },
        {
            "file_id": "ok",
            "file_path": "invalidpath",
            "timeout": 0.1,
            "expected_lines": 10,
            "error_type": None
        },
        {
            "file_id": "ok2",
            "file_path": "/ok2.log",
            "timeout": 0.1,
            "expected_lines": 0,
            "error_type": None
        }
    ]
    print(analyze_log_files(log_files9))

    print("\nEdge Case: More than 50 files")
    log_files10 = [
        {
            "file_id": f"id{i}",
            "file_path": f"/f{i}.log",
            "timeout": 0.1,
            "expected_lines": 1,
            "error_type": None
        }
        for i in range(60)
    ]
    print(analyze_log_files(log_files10))


if __name__ == "__main__":
    driver()

