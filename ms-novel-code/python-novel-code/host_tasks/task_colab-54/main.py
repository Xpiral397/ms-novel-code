
"""A memory profiler using the gc module."""
import gc
import psutil
import os
import time
from functools import wraps
from dataclasses import dataclass
from typing import Callable, Optional, Dict, Any, List


@dataclass
class ProfileReport:
    """Data class to store memory profiling results."""

    function_name: str
    execution_time: float
    memory_before: float
    memory_after: float
    memory_saved: float
    gc_objects_collected: int
    exceeded_threshold: bool
    peak_memory: Optional[float] = None
    gc_stats: Optional[Dict[str, Any]] = None

    def __repr__(self):
        """Format output to match expected format."""
        parts = [
            f"function_name='{self.function_name}'",
            f"execution_time={self.execution_time:.3f}",
            f"memory_before={self.memory_before:.1f}",
            f"memory_after={self.memory_after:.1f}",
            f"memory_saved={self.memory_saved:.1f}",
            f"gc_objects_collected={self.gc_objects_collected}",
            f"exceeded_threshold={self.exceeded_threshold}",
        ]

        if self.peak_memory is not None:
            parts.append(f"peak_memory={self.peak_memory:.1f}")

        return f"ProfileReport({', '.join(parts)})"


def memory_profiler(
    auto_gc: bool = False,
    detailed_stats: bool = False,
    track_peak: bool = False,
    threshold_mb: float = float("inf"),
) -> Callable:
    """Profile memory usage of a function."""
    if threshold_mb <= 0:
        threshold_mb = float("inf")

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            process = psutil.Process(os.getpid())

            gc_stats_before = None
            if detailed_stats:
                gc_stats_before = {
                    "generations": gc.get_count(),
                    "stats": (
                        gc.get_stats() if hasattr(gc, "get_stats") else None
                    ),
                    "garbage": len(gc.garbage),
                    "thresholds": gc.get_threshold(),
                }

            initial_gc_collected = 0
            if auto_gc:
                initial_gc_collected = gc.collect()

            memory_info_before = process.memory_info()
            memory_before_mb = memory_info_before.rss / (1024 * 1024)

            peak_memory_mb = memory_before_mb if track_peak else None
            memory_samples = []

            start_time = time.time()

            exception_raised = None
            result = None

            try:
                if auto_gc:
                    gc_was_enabled = gc.isenabled()
                    if gc_was_enabled:
                        gc.disable()

                try:
                    result = func(*args, **kwargs)

                    if track_peak:
                        current_mem = process.memory_info().rss / (1024 * 1024)
                        memory_samples.append(current_mem)
                        peak_memory_mb = max(peak_memory_mb, current_mem)

                finally:
                    if auto_gc and gc_was_enabled:
                        gc.enable()

            except Exception as e:
                exception_raised = e

            execution_time = time.time() - start_time

            memory_info_after_exec = process.memory_info()
            memory_after_exec_mb = memory_info_after_exec.rss / (1024 * 1024)

            if track_peak:
                peak_memory_mb = max(peak_memory_mb, memory_after_exec_mb)

            gc_objects_collected = 0
            if auto_gc:
                gc_objects_collected = gc.collect(2)
                gc_objects_collected += gc.collect()

            memory_info_final = process.memory_info()
            memory_after_mb = memory_info_final.rss / (1024 * 1024)

            memory_saved_mb = max(0.0, memory_after_exec_mb - memory_after_mb)

            threshold_exceeded = memory_after_mb > threshold_mb

            gc_stats = None
            if detailed_stats:
                gc_stats_after = {
                    "generations": gc.get_count(),
                    "stats": (
                        gc.get_stats() if hasattr(gc, "get_stats") else None
                    ),
                    "garbage": len(gc.garbage),
                    "thresholds": gc.get_threshold(),
                }
                gc_stats = {
                    "before": gc_stats_before,
                    "after": gc_stats_after,
                    "objects_collected": gc_objects_collected,
                    "initial_collection": initial_gc_collected,
                }

            report = ProfileReport(
                function_name=func.__name__,
                execution_time=execution_time,
                memory_before=memory_before_mb,
                memory_after=memory_after_mb,
                memory_saved=memory_saved_mb,
                gc_objects_collected=gc_objects_collected,
                exceeded_threshold=threshold_exceeded,
                peak_memory=peak_memory_mb if track_peak else None,
                gc_stats=gc_stats if detailed_stats else None,
            )

            if not hasattr(wrapper, "profile_reports"):
                wrapper.profile_reports = []
            wrapper.profile_reports.append(report)
            wrapper.last_report = report

            if exception_raised:
                raise exception_raised

            return result

        wrapper.profiler_config = {
            "auto_gc": auto_gc,
            "detailed_stats": detailed_stats,
            "track_peak": track_peak,
            "threshold_mb": threshold_mb,
        }

        wrapper.profile_reports = []
        wrapper.last_report = None

        return wrapper

    return decorator


def profile_functions(
    functions: List[Callable], config: Dict[str, Any]
) -> List[ProfileReport]:
    """
    Profile a list of functions with a given configuration.

    Args:
        functions: List of callable functions to profile
        config: Dictionary with profiling configuration

    Returns:
        List of ProfileReport objects for each function
    """
    reports = []

    auto_gc = config.get("auto_gc", False)
    detailed_stats = config.get("detailed_stats", False)
    track_peak = config.get("track_peak", False)
    threshold_mb = config.get("threshold_mb", float("inf"))

    for func in functions:
        profiled_func = memory_profiler(
            auto_gc=auto_gc,
            detailed_stats=detailed_stats,
            track_peak=track_peak,
            threshold_mb=threshold_mb,
        )(func)

        try:
            profiled_func()
        except Exception:
            pass

        if hasattr(profiled_func, "last_report") and profiled_func.last_report:
            reports.append(profiled_func.last_report)

    return reports


def example_process_data():
    """Allocate memory as an example."""
    data = [[i] * 1000 for i in range(1000)]
    return len(data)


def example_circular_refs():
    """Create circular references as an example."""
    objects = []
    for i in range(100):
        obj = {"id": i, "refs": objects}
        objects.append(obj)
    return objects


if __name__ == "__main__":
    @memory_profiler(auto_gc=True, threshold_mb=100)
    def process_data():
        """Process some data."""
        data = [[i] * 1000 for i in range(1000)]
        return len(data)

    result = process_data()
    print(f"# Output: {process_data.last_report}")

    @memory_profiler(detailed_stats=True, track_peak=True)
    def create_circular_refs():
        """Create circular references."""
        objects = []
        for i in range(100):
            obj = {"id": i, "refs": objects}
            objects.append(obj)
        return objects

    result = create_circular_refs()
    print(f"# Output: {create_circular_refs.last_report}")


