#!/usr/bin/env python
import argparse
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import time
import traceback
import unittest
from difflib import unified_diff
from pathlib import Path
from pprint import pformat

# === Start Standalone Helper Functions ===


# ANSI color codes
class Colors:
    RESET = "\033[0m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"


def load_module(file_path, module_name):
    """Dynamically load a module from file path."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if not spec or not spec.loader:
        raise ImportError(f"Could not load spec for {file_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module  # Add to sys.modules
    spec.loader.exec_module(module)
    return module


def safe_json_serialize(obj):
    """Attempt to JSON serialize an object, converting to string if it fails."""
    try:
        # Test serialization first without actually creating the string
        _ = json.dumps(obj, ensure_ascii=False)
        return obj
    except (TypeError, OverflowError):
        try:
            return str(obj)
        except Exception:
            return f"[Unserializable object of type {type(obj).__name__}]"


def write_json_to_file(data, output_file):
    """Helper function to write JSON data to a file with proper error handling."""
    try:
        # Ensure parent directory exists
        os.makedirs(os.path.dirname(str(output_file)), exist_ok=True)
        # Write JSON to file
        with open(output_file, "w") as f:
            json.dump(data, f, indent=2)
        print(f"JSON results saved to: {output_file}")
        return True
    except Exception as e:
        print(f"Error writing JSON to file: {e}", file=sys.stderr)
        # Fallback to stdout if file write fails
        print(json.dumps(data, indent=2))
        return False


def format_diff(expected, actual):
    """
    Format the difference between expected and actual outputs in a readable way.
    """
    try:
        expected_str = pformat(expected)
        actual_str = pformat(actual)

        # Generate unified diff
        diff_lines = list(
            unified_diff(
                expected_str.splitlines(),
                actual_str.splitlines(),
                lineterm="",
                fromfile="Expected",
                tofile="Actual",
            )
        )

        if diff_lines:
            colored_diff = []
            for line in diff_lines:
                if line.startswith("+"):
                    colored_diff.append(f"{Colors.GREEN}{line}{Colors.RESET}")
                elif line.startswith("-"):
                    colored_diff.append(f"{Colors.RED}{line}{Colors.RESET}")
                elif line.startswith("@@"):
                    colored_diff.append(f"{Colors.BLUE}{line}{Colors.RESET}")
                else:
                    colored_diff.append(line)
            return "\n".join(colored_diff)
        else:
            return f"{Colors.YELLOW}No textual difference in pformat output (may differ in type or structure){Colors.RESET}"
    except Exception as e:
        # Fallback for any errors during diff generation
        return f"{Colors.RED}Could not generate diff: {str(e)}{Colors.RESET}\nExpected: {pformat(expected)}\nActual: {pformat(actual)}"


# Custom test results handler for unittest to capture results in our format
class CustomTestResult(unittest.TestResult):
    def __init__(self):
        super().__init__()
        self.test_results = {
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "errors": 0,
                "all_passed": False,
            },
            "details": [],
            "setup_error": None,
        }
        self.current_test_output = None
        self.current_test_index = 0

    def startTest(self, test):
        super().startTest(test)
        self.test_results["summary"]["total"] += 1
        self.current_test_output = {
            "case_index": self.current_test_index,
            "test_name": test.id(),
            "passed": True,  # Default to True, set to False on failures
            "exception": None,
            "traceback": None,
            "stdout": "",
            "stderr": "",
        }
        self.current_test_index += 1

    def addSuccess(self, test):
        super().addSuccess(test)
        self.test_results["summary"]["passed"] += 1
        self.test_results["details"].append(self.current_test_output)

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.test_results["summary"]["failed"] += 1

        self.current_test_output["passed"] = False
        self.current_test_output["exception"] = f"{err[0].__name__}: {str(err[1])}"
        self.current_test_output["traceback"] = "".join(
            traceback.format_exception(*err)
        )

        self.test_results["details"].append(self.current_test_output)

    def addError(self, test, err):
        super().addError(test, err)
        self.test_results["summary"]["errors"] += 1

        self.current_test_output["passed"] = False
        self.current_test_output["exception"] = f"{err[0].__name__}: {str(err[1])}"
        self.current_test_output["traceback"] = "".join(
            traceback.format_exception(*err)
        )

        self.test_results["details"].append(self.current_test_output)

    def stopTest(self, test):
        super().stopTest(test)

    def finalize(self):
        """Finalize the results and return the summary"""
        total = self.test_results["summary"]["total"]
        passed = self.test_results["summary"]["passed"]

        self.test_results["summary"]["all_passed"] = total > 0 and passed == total

        return self.test_results


# Class to capture stdout/stderr during test execution
class OutputCapturer:
    def __init__(self, test_result, test):
        self.test_result = test_result
        self.test = test
        self.stdout_buffer = io.StringIO()
        self.stderr_buffer = io.StringIO()

    def __enter__(self):
        self.old_stdout = sys.stdout
        self.old_stderr = sys.stderr
        sys.stdout = self.stdout_buffer
        sys.stderr = self.stderr_buffer
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self.old_stdout
        sys.stderr = self.old_stderr

        # Store captured output
        for result in self.test_result.test_results["details"]:
            if result["test_name"] == self.test.id():
                result["stdout"] = self.stdout_buffer.getvalue()
                result["stderr"] = self.stderr_buffer.getvalue()
                break


# === Multi-run Result Aggregation ===


class MultiRunAggregator:
    """Aggregates results across multiple test runs to track pass rates."""

    def __init__(self):
        self.runs = []
        self.test_stats = {}  # test_name -> {passes, fails, errors, last_exception, last_traceback, last_stdout, last_stderr}

    def add_run(self, run_result):
        """Add a single run result to the aggregation."""
        self.runs.append(run_result)

        # Skip if there was a setup error
        if run_result.get("setup_error"):
            return

        # Track individual test results
        for detail in run_result.get("details", []):
            test_name = detail["test_name"]

            if test_name not in self.test_stats:
                self.test_stats[test_name] = {
                    "passes": 0,
                    "fails": 0,
                    "errors": 0,
                    "last_exception": None,
                    "last_traceback": None,
                    "last_stdout": "",
                    "last_stderr": "",
                    "case_index": detail["case_index"],
                }

            stats = self.test_stats[test_name]

            if detail["passed"]:
                stats["passes"] += 1
            elif detail.get("exception") and "Error" in detail["exception"]:
                stats["errors"] += 1
                stats["last_exception"] = detail["exception"]
                stats["last_traceback"] = detail["traceback"]
                stats["last_stdout"] = detail["stdout"]
                stats["last_stderr"] = detail["stderr"]
            else:
                stats["fails"] += 1
                stats["last_exception"] = detail["exception"]
                stats["last_traceback"] = detail["traceback"]
                stats["last_stdout"] = detail["stdout"]
                stats["last_stderr"] = detail["stderr"]

    def get_aggregated_results(self):
        """Generate aggregated results in the expected format."""
        total_runs = len([r for r in self.runs if not r.get("setup_error")])

        if total_runs == 0:
            # If all runs had setup errors, return the first error
            return (
                self.runs[0]
                if self.runs
                else {
                    "setup_error": "No successful runs",
                    "summary": {
                        "total": 0,
                        "passed": 0,
                        "failed": 0,
                        "errors": 0,
                        "all_passed": False,
                    },
                    "details": [],
                }
            )

        # Calculate summary statistics
        total_tests = len(self.test_stats)
        fully_passed_tests = sum(
            1 for stats in self.test_stats.values() if stats["passes"] == total_runs
        )

        # Create aggregated result structure
        result = {
            "summary": {
                "total": total_tests,
                "passed": fully_passed_tests,
                "failed": total_tests - fully_passed_tests,
                "errors": 0,  # We'll count this differently for multi-run
                "all_passed": fully_passed_tests == total_tests and total_tests > 0,
                "total_runs": total_runs,
                "consistent_pass_rate": fully_passed_tests / total_tests
                if total_tests > 0
                else 0.0,
            },
            "details": [],
            "setup_error": None,
        }

        # Create details for each test
        for test_name, stats in self.test_stats.items():
            pass_rate = stats["passes"] / total_runs if total_runs > 0 else 0.0
            is_flaky = 0 < stats["passes"] < total_runs

            detail = {
                "case_index": stats["case_index"],
                "test_name": test_name,
                "passed": stats["passes"] == total_runs,  # Only true if passed ALL runs
                "exception": stats["last_exception"],
                "traceback": stats["last_traceback"],
                "stdout": stats["last_stdout"],
                "stderr": stats["last_stderr"],
                # New fields for multi-run tracking
                "pass_rate": pass_rate,
                "runs_passed": stats["passes"],
                "runs_failed": stats["fails"],
                "runs_errored": stats["errors"],
                "total_runs": total_runs,
                "flaky": is_flaky,
            }

            result["details"].append(detail)

        # Sort details by case_index to maintain order
        result["details"].sort(key=lambda x: x["case_index"])

        return result


def has_dependencies(task_dir: Path) -> bool:
    """Check if the task has dependencies by looking for a non-empty requirements.txt file."""
    requirements_file = task_dir / "requirements.txt"

    if not requirements_file.exists():
        return False

    try:
        with open(requirements_file, "r") as f:
            content = f.read().strip()
            # Check if file has any non-comment, non-empty lines
            lines = [
                line.strip()
                for line in content.splitlines()
                if line.strip() and not line.strip().startswith("#")
            ]
            return len(lines) > 0
    except Exception:
        return False


def setup_virtual_environment(task_dir: Path) -> bool:
    """Create a virtual environment and install dependencies using uv."""

    try:
        # Create virtual environment
        print(
            f"{Colors.BLUE}Creating virtual environment for task...{Colors.RESET}",
            file=sys.stderr,
        )
        result = subprocess.run(
            ["uv", "venv", "--python", "python3"],
            cwd=task_dir,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            print(
                f"{Colors.RED}Failed to create virtual environment:{Colors.RESET}",
                file=sys.stderr,
            )
            print(result.stderr, file=sys.stderr)
            return False

        # Install dependencies
        print(
            f"{Colors.BLUE}Installing dependencies from requirements.txt...{Colors.RESET}",
            file=sys.stderr,
        )
        result = subprocess.run(
            ["uv", "pip", "install", "-r", "requirements.txt"],
            cwd=task_dir,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            print(
                f"{Colors.RED}Failed to install dependencies:{Colors.RESET}",
                file=sys.stderr,
            )
            print(result.stderr, file=sys.stderr)
            return False

        print(
            f"{Colors.GREEN}Dependencies installed successfully.{Colors.RESET}",
            file=sys.stderr,
        )
        return True

    except FileNotFoundError:
        print(
            f"{Colors.RED}Error: 'uv' command not found. Please ensure uv is installed and available in PATH.{Colors.RESET}",
            file=sys.stderr,
        )
        return False
    except Exception as e:
        print(
            f"{Colors.RED}Unexpected error setting up virtual environment: {e}{Colors.RESET}",
            file=sys.stderr,
        )
        return False


def run_with_dependencies(
    task_dir: Path, script_path: Path, original_args: list
) -> int:
    """Re-execute the script using uv run to use the virtual environment."""
    try:
        # Set environment variable to prevent infinite recursion
        env = os.environ.copy()
        env["_TEST_RUNNER_IN_VENV"] = "1"

        # Build the command to re-execute this script with uv run
        cmd = ["uv", "run", "python", str(script_path)] + original_args

        print(
            f"{Colors.BLUE}Running tests with virtual environment...{Colors.RESET}",
            file=sys.stderr,
        )
        result = subprocess.run(cmd, cwd=task_dir, env=env)

        return result.returncode

    except Exception as e:
        print(
            f"{Colors.RED}Error running tests with virtual environment: {e}{Colors.RESET}",
            file=sys.stderr,
        )
        return 1


def is_in_virtual_environment() -> bool:
    """Check if we're already running in a virtual environment (to avoid infinite recursion)."""
    return os.environ.get("_TEST_RUNNER_IN_VENV") == "1"


# === Main Test Runner Functions ===


def run_tests(task_dir: Path):
    """Run unittest-style tests found in task_dir."""
    test_file = task_dir / "tests.py"  # Assume tests are in tests.py
    main_file = task_dir / "main.py"  # Assume code is in main.py

    # Create result structure with similar format to original
    results = {
        "summary": {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "all_passed": False,
        },
        "details": [],
        "setup_error": None,
    }

    # Try to load and run the tests
    try:
        if not test_file.exists():
            raise FileNotFoundError(f"Test file not found: {test_file}")

        if not main_file.exists():
            raise FileNotFoundError(f"Main file not found: {main_file}")

        # NOTE: The working directory is already set to the task directory by the
        # logic in __main__, which automatically puts it in Python's import path.
        # No manual sys.path manipulation is needed and was the source of the bug.

        # Use consistent module names - they'll be cleaned up between runs
        main_module_name = "main_module"
        tests_module_name = "tests_module"

        # Flag to track if we've made module name changes
        modules_modified = False

        # Load main.py first
        try:
            # Load main.py with a unique module name
            main_module = load_module(str(main_file), main_module_name)

            # Explicitly add to sys.modules as both the unique name and as 'main'
            sys.modules[main_module_name] = main_module
            sys.modules["main"] = main_module
            modules_modified = True
        except Exception as _:
            raise  # Re-raise to trigger the exception handling below

        # Now try to load the tests module
        tests_module = load_module(str(test_file), tests_module_name)

        # Create a test suite and runner
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromModule(tests_module)

        # Create our custom test result handler
        test_result = CustomTestResult()

        # Create a runner and patch the run method to capture output
        original_run = unittest.TextTestRunner.run

        def patched_run(self, test):
            # Handle test suites recursively
            def run_test_with_capture(test_item):
                if isinstance(test_item, unittest.TestCase):
                    # If it's an individual test case, capture output
                    with OutputCapturer(test_result, test_item):
                        test_item.run(test_result)
                else:
                    # If it's a suite, recurse through its tests
                    for sub_test in test_item:
                        run_test_with_capture(sub_test)

            # Start with the top-level test suite
            run_test_with_capture(test)
            return test_result

        unittest.TextTestRunner.run = patched_run
        runner = unittest.TextTestRunner(verbosity=0)

        # Run the tests
        runner.run(suite)

        # Restore original run method
        unittest.TextTestRunner.run = original_run

        # Clean up any modules we added
        if modules_modified:
            if main_module_name in sys.modules:
                del sys.modules[main_module_name]
            if "main" in sys.modules:
                del sys.modules["main"]

        # Get the results
        return test_result.finalize()

    except (ImportError, FileNotFoundError, AttributeError, SyntaxError) as e:
        results["setup_error"] = f"Error loading tests: {type(e).__name__}: {e}"
        results["setup_traceback"] = traceback.format_exc()

        # Clean up any modules we added
        if "modules_modified" in locals() and modules_modified:
            if "main_module_name" in locals() and main_module_name in sys.modules:
                del sys.modules[main_module_name]
            if "main" in sys.modules:
                del sys.modules["main"]

        return results
    except Exception as e:
        results["setup_error"] = (
            f"Unexpected error during setup: {type(e).__name__}: {e}"
        )
        results["setup_traceback"] = traceback.format_exc()

        # Clean up any modules we added
        if "modules_modified" in locals() and modules_modified:
            if "main_module_name" in locals() and main_module_name in sys.modules:
                del sys.modules[main_module_name]
            if "main" in sys.modules:
                del sys.modules["main"]

        return results


def run_multiple_tests(task_dir: Path, num_runs: int, json_output: bool = False):
    """Run tests multiple times and aggregate results."""
    aggregator = MultiRunAggregator()

    # Store original sys.modules state to restore between runs
    original_modules = set(sys.modules.keys())

    for run_num in range(1, num_runs + 1):
        if not json_output:
            print(
                f"{Colors.BLUE}Running test iteration {run_num}/{num_runs}...{Colors.RESET}",
                file=sys.stderr,
            )

        # Clean up modules from previous runs (except the first run)
        if run_num > 1:
            # Clean up our specific test modules
            modules_to_clean = ["main_module", "tests_module"]
            if "main" not in original_modules:
                modules_to_clean.append("main")

            for module_name in modules_to_clean:
                if module_name in sys.modules:
                    del sys.modules[module_name]

        # Run a single test iteration
        result = run_tests(task_dir)
        aggregator.add_run(result)

        # If there's a setup error, no point in continuing
        if result.get("setup_error"):
            break

    return aggregator.get_aggregated_results()


# Function to print results in a human-friendly format
def print_human_readable_results(results, task_dir):
    print(f"{Colors.BOLD}Running tests for: {task_dir}{Colors.RESET}")
    print("=" * 60)

    if results.get("setup_error"):
        print(f"{Colors.RED}{Colors.BOLD}SETUP ERROR:{Colors.RESET}")
        print(f"{Colors.RED}{results['setup_error']}{Colors.RESET}")
        if results.get("setup_traceback"):
            print("-" * 60)
            print(results["setup_traceback"])
        print("=" * 60)
        return  # Stop here if setup failed

    total = results["summary"]["total"]
    passed_count = results["summary"]["passed"]
    failed_count = results["summary"]["failed"]
    error_count = results["summary"]["errors"]
    total_runs = results["summary"].get("total_runs", 1)

    print(
        f"\n{Colors.BOLD}Test Execution Summary (across {total_runs} runs):{Colors.RESET}"
    )
    print("-" * 60)

    for detail in results["details"]:
        idx = detail["case_index"] + 1
        test_name = detail["test_name"]

        if total_runs > 1:
            pass_rate = detail.get("pass_rate", 0.0) * 100
            runs_passed = detail.get("runs_passed", 0)
            is_flaky = detail.get("flaky", False)

            print(f"Test {idx}/{total}: {test_name}")
            print(
                f"  Pass Rate: {pass_rate:.1f}% ({runs_passed}/{total_runs} runs)",
                end="",
            )

            if is_flaky:
                print(f" {Colors.YELLOW}[FLAKY]{Colors.RESET}")
            elif pass_rate == 100.0:
                print(f" {Colors.GREEN}[STABLE PASS]{Colors.RESET}")
            elif pass_rate == 0.0:
                print(f" {Colors.RED}[CONSISTENT FAIL]{Colors.RESET}")
            else:
                print()
        else:
            # Single run display
            print(f"Test {idx}/{total} ({test_name}): ", end="")
            if detail["exception"]:
                print(
                    f"{Colors.RED}ERROR{Colors.RESET}"
                    if "Error" in detail["exception"]
                    else f"{Colors.RED}FAIL{Colors.RESET}"
                )
            elif detail["passed"]:
                print(f"{Colors.GREEN}PASS{Colors.RESET}")

    # Show failed/flaky tests details
    flaky_or_failed_tests = [
        d for d in results["details"] if not d["passed"] or d.get("flaky", False)
    ]

    if flaky_or_failed_tests:
        print(f"\n{Colors.BOLD}{Colors.RED}Failed and Flaky Tests:{Colors.RESET}")
        print("=" * 60)
        for detail in flaky_or_failed_tests:
            idx = detail["case_index"] + 1
            test_name = detail["test_name"]

            if total_runs > 1:
                pass_rate = detail.get("pass_rate", 0.0) * 100
                is_flaky = detail.get("flaky", False)

                if is_flaky:
                    status = f"{Colors.YELLOW}FLAKY ({pass_rate:.1f}% pass rate){Colors.RESET}"
                else:
                    status = f"{Colors.RED}FAILED{Colors.RESET}"
            else:
                status = (
                    f"{Colors.RED}ERROR{Colors.RESET}"
                    if detail.get("exception") and "Error" in detail["exception"]
                    else f"{Colors.RED}FAIL{Colors.RESET}"
                )

            print(
                f"\n{Colors.BOLD}Test Case {idx} ({test_name}): {status}{Colors.RESET}"
            )

            if detail["exception"]:
                print(f"{Colors.RED}Exception:{Colors.RESET} {detail['exception']}")
                if detail["traceback"]:
                    print(
                        f"{Colors.YELLOW}Traceback:{Colors.RESET}\n{detail['traceback']}"
                    )

            if detail["stdout"]:
                print(f"\n{Colors.BLUE}stdout:{Colors.RESET}\n{detail['stdout']}")
            if detail["stderr"]:
                if not detail["exception"] or (
                    detail["stderr"] not in (detail["traceback"] or "")
                ):
                    print(f"\n{Colors.YELLOW}stderr:{Colors.RESET}\n{detail['stderr']}")
            print("-" * 60)

    # Print Summary
    print(f"\n{Colors.BOLD}Test Summary{Colors.RESET}")
    print("=" * 60)

    if total_runs > 1:
        print(f"Total Test Runs: {total_runs}")
        print(f"Total Test Cases: {total}")
        consistent_pass_rate = results["summary"].get("consistent_pass_rate", 0.0) * 100

        print(
            f"Consistently Passing: {Colors.GREEN}{passed_count}/{total} ({consistent_pass_rate:.1f}%){Colors.RESET}"
        )

        flaky_count = sum(1 for d in results["details"] if d.get("flaky", False))
        if flaky_count > 0:
            print(f"Flaky Tests: {Colors.YELLOW}{flaky_count}/{total}{Colors.RESET}")

        failed_count = total - passed_count
        if failed_count > 0:
            print(
                f"Consistently Failing: {Colors.RED}{failed_count}/{total}{Colors.RESET}"
            )
    else:
        print(f"Total Test Cases: {total}")

        pass_color = Colors.GREEN if passed_count == total else Colors.YELLOW
        fail_color = Colors.RED if failed_count > 0 else Colors.GREEN
        error_color = Colors.RED if error_count > 0 else Colors.GREEN

        print(f"Passed: {pass_color}{passed_count}/{total}{Colors.RESET}")
        print(f"Failed: {fail_color}{failed_count}/{total}{Colors.RESET}")
        print(f"Errors: {error_color}{error_count}/{total}{Colors.RESET}")

    print("-" * 60)
    if results["summary"]["all_passed"]:
        if total_runs > 1:
            print(
                f"{Colors.GREEN}{Colors.BOLD}All tests passed consistently across all {total_runs} runs!{Colors.RESET}"
            )
        else:
            print(f"{Colors.GREEN}{Colors.BOLD}All tests passed!{Colors.RESET}")
    else:
        if total_runs > 1:
            flaky_count = sum(1 for d in results["details"] if d.get("flaky", False))
            if flaky_count > 0:
                print(
                    f"{Colors.YELLOW}{Colors.BOLD}Some tests are flaky or consistently failing.{Colors.RESET}"
                )
            else:
                print(
                    f"{Colors.RED}{Colors.BOLD}Some tests are consistently failing.{Colors.RESET}"
                )
        else:
            print(
                f"{Colors.RED}{Colors.BOLD}Some tests failed or encountered errors.{Colors.RESET}"
            )
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run unittest-style tests within a specified task directory."
    )
    parser.add_argument(
        "--task-dir",
        type=str,
        required=True,
        help="Path to the directory containing the test files",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format instead of human-readable text.",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=10,
        help="Number of times to run the tests to detect flaky behavior (default: 10)",
    )
    # Add a version flag to identify this as the new test runner
    parser.add_argument(
        "--version",
        action="version",
        version="test_runner_script_ng 1.0",
        help="Show script version",
    )
    # Add output file argument
    parser.add_argument(
        "--output-file",
        type=str,
        help="Path to save JSON output when using --json (default: test_results.json in task dir)",
    )

    args = parser.parse_args()

    # Validate runs argument
    if args.runs < 1:
        print(
            f"{Colors.RED}Error: --runs must be at least 1{Colors.RESET}",
            file=sys.stderr,
        )
        sys.exit(1)

    task_directory = Path(args.task_dir).resolve()  # Resolve to absolute path
    # Determine output file path once (if using JSON output)
    output_file = None
    if args.json:
        output_file = args.output_file or (task_directory / "test_results.json")

    # --- Dependency Management Check --- #
    # Check if we're already in a virtual environment (to avoid infinite recursion)
    if not is_in_virtual_environment():
        # Check if task has dependencies
        if has_dependencies(task_directory):
            print(
                f"Dependencies detected in {task_directory}/requirements.txt",
                file=sys.stderr,
            )

            # WORKAROUND: Due to an unresolved issue where `uv run` fails to properly
            # activate existing virtual environments on subsequent runs (causing
            # ModuleNotFoundError even though packages are installed), we always
            # recreate the virtual environment to ensure reliability.
            # This affects both our script and manual `uv run python -c "import ..."` tests.
            venv_dir = task_directory / ".venv"
            if venv_dir.exists():
                print(
                    "Removing existing virtual environment to ensure reliable activation...",
                    file=sys.stderr,
                )
                shutil.rmtree(venv_dir)

            if True:  # Always setup since we always remove above
                # Setup virtual environment and install dependencies
                if not setup_virtual_environment(task_directory):
                    # If setup failed, create error result and exit
                    error_result = {
                        "setup_error": "Failed to create virtual environment or install dependencies",
                        "summary": {
                            "total": 0,
                            "passed": 0,
                            "failed": 0,
                            "errors": 0,
                            "all_passed": False,
                        },
                        "details": [],
                    }
                    if args.json:
                        write_json_to_file(error_result, output_file)
                    else:
                        print(
                            f"{Colors.RED}Error: Failed to setup virtual environment{Colors.RESET}",
                            file=sys.stderr,
                        )
                    sys.exit(1)

            # Re-execute script with uv run to use the virtual environment
            script_path = Path(__file__).resolve()
            original_args = sys.argv[1:]  # Exclude script name
            exit_code = run_with_dependencies(
                task_directory, script_path, original_args
            )
            sys.exit(exit_code)
        else:
            print(
                "No dependencies required, running with system Python", file=sys.stderr
            )

    # --- Change CWD --- #
    original_cwd = os.getcwd()
    try:
        if not task_directory.is_dir():
            error_result = {
                "setup_error": f"Task directory not found or is not a directory: {task_directory}",
                "summary": {},
                "details": [],
            }
            if args.json:
                write_json_to_file(error_result, output_file)
            else:
                print(
                    f"{Colors.RED}Error: Task directory not found or is not a directory: {task_directory}{Colors.RESET}",
                    file=sys.stderr,
                )
            sys.exit(1)
        os.chdir(task_directory)

        # Clean up pycache to prevent stale bytecode issues between runs.
        # Stale .pyc files can retain incorrect path information from previous runs.
        pycache_dir = Path("__pycache__")
        if pycache_dir.is_dir():
            import shutil

            shutil.rmtree(pycache_dir)

    except Exception as e:
        error_result = {
            "setup_error": f"Error changing directory to {task_directory}: {e}",
            "summary": {},
            "details": [],
        }
        if args.json:
            write_json_to_file(error_result, output_file)
        else:
            print(
                f"{Colors.RED}Error changing directory to {task_directory}: {e}{Colors.RESET}",
                file=sys.stderr,
            )
        sys.exit(1)

        # --- Execute Tests --- #
    # Now that CWD is task_dir, use "." for relative path finding within run_tests
    if args.runs == 1:
        final_results = run_tests(Path("."))
    else:
        final_results = run_multiple_tests(Path("."), args.runs, args.json)

    # --- Change CWD Back --- #
    os.chdir(original_cwd)  # Change back to original CWD

    # --- Output Results --- #
    if args.json:
        # Serialize necessary fields just before dumping JSON
        for detail in final_results.get("details", []):
            detail["test_name"] = safe_json_serialize(detail.get("test_name"))

        # Write results to file using our helper function
        write_json_to_file(final_results, output_file)
    else:
        print_human_readable_results(final_results, task_directory)

    # --- Exit Code --- #
    if final_results.get("setup_error"):
        sys.exit(1)
    elif final_results.get("summary", {}).get("all_passed", False):
        sys.exit(0)
    else:
        sys.exit(1)