import unittest
import time
import os
import glob
import statistics
import functools
import psutil
import platform

# Realistic prompt:
# This test suite validates both correctness and performance of the StringAnalyzer implementations.
# Performance tests assume a baseline machine profile:
# - At least 4 physical CPU cores
# - Minimum CPU frequency of 2.4 GHz
# - CPU governor set to 'performance' (Linux)
# - Tests pinned to a single core (0) and boosted priority
# - High-resolution timing via time.perf_counter()
# We run 20 timed iterations, remove the top/bottom 10% as outliers,
# and enforce a median execution time below the specified max_time.

def performance_test(
    max_time: float = 0.25,
    runs: int = 20,
    outlier_pct: float = 0.1,
    cpu_core: int = 0,
    min_cores: int = 4,
    min_freq_ghz: float = 2.4,
    enforce_affinity: bool = True,
    enforce_priority: bool = True,
    check_governor: bool = True,
    warn_arch: bool = True,
    warn_steal: bool = True,
    warn_wsl: bool = True,
    logger=print
):
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(self, *args, **kwargs):
            system = platform.system()

            # WSL2 detection
            if warn_wsl and system == 'Linux':
                if 'microsoft' in platform.uname().release.lower():
                    logger("[PerfTest] WARNING: Running under WSL2 dynamic memory VM")

            # ARM architecture warning
            if warn_arch:
                arch = platform.machine().lower()
                if 'arm' in arch:
                    logger(f"[PerfTest] WARNING: ARM architecture detected ({platform.machine()}), timing may vary")

            # CPU steal time
            if warn_steal and system == 'Linux':
                try:
                    steal = psutil.cpu_times_percent(interval=None)._asdict().get('steal', 0.0)
                    if steal > 0.0:
                        logger(f"[PerfTest] WARNING: Detected CPU steal time: {steal:.2f}%")
                except Exception:
                    pass

            # Pin to a single core
            if enforce_affinity:
                try:
                    psutil.Process().cpu_affinity([cpu_core])
                except Exception:
                    logger("[PerfTest] WARNING: Could not set CPU affinity")

            # Raise process priority
            if enforce_priority:
                try:
                    os.nice(-10)
                except Exception:
                    logger("[PerfTest] WARNING: Could not change process priority")

            # Check CPU governor on Linux
            if check_governor and system == 'Linux':
                governors = []
                for f in glob.glob('/sys/devices/system/cpu/cpu*/cpufreq/scaling_governor'):
                    try:
                        governors.append(open(f).read().strip())
                    except Exception:
                        pass
                if governors and any(g != 'performance' for g in governors):
                    logger("[PerfTest] WARNING: CPU governor is not 'performance' for all CPUs")

            # Baseline machine checks
            cores = psutil.cpu_count(logical=False) or 1
            if cores < min_cores:
                logger(f"[PerfTest] WARNING: detected {cores} cores (<{min_cores})")

            freq = psutil.cpu_freq()
            if freq and freq.current/1000.0 < min_freq_ghz:
                logger(f"[PerfTest] WARNING: CPU {freq.current/1000.0:.2f} GHz <{min_freq_ghz} GHz")

            # Warm-up and timed runs
            times = []
            for i in range(runs + 1):
                start = time.perf_counter()
                fn(self, *args, **kwargs)
                elapsed = time.perf_counter() - start
                label = 'warm-up' if i == 0 else f'run {i}'
                logger(f"[PerfTest] {label}: {elapsed:.3f}s")
                if i > 0:
                    times.append(elapsed)

            # Outlier removal and median check
            sorted_times = sorted(times)
            cut = int(len(sorted_times) * outlier_pct)
            filtered = sorted_times[cut:len(sorted_times)-cut]
            median = statistics.median(filtered)
            logger(f"[PerfTest] median(filtered {runs}) = {median:.3f}s (limit={max_time}s)")
            if median > max_time:
                self.fail(f"Performance exceeded {max_time}s (median {median:.3f}s)")

        return wrapper
    return decorator

from main import StringAnalyzer, StringAnalyzerSlow

class TestStringAnalyzerFast(unittest.TestCase):
    def setUp(self):
        self.analyzer = StringAnalyzer()
        self.large = "xyz" * (10**6 // 3)

    def test_correctness(self):
        self.assertTrue(self.analyzer.has_repeated_pattern("abab"))
        self.assertTrue(self.analyzer.has_repeated_pattern("abcabcabc"))
        self.assertFalse(self.analyzer.has_repeated_pattern("abcd"))
        self.assertFalse(self.analyzer.has_repeated_pattern("a"))
        self.assertTrue(self.analyzer.has_repeated_pattern("zzzzzz"))

    @performance_test(
        max_time=0.25,
        runs=20,
        outlier_pct=0.1,
        cpu_core=0,
        min_cores=4,
        min_freq_ghz=2.4
    )
    def test_performance_fast(self):
        self.assertTrue(self.analyzer.has_repeated_pattern(self.large))

class TestStringAnalyzerSlow(unittest.TestCase):
    def setUp(self):
        self.analyzer = StringAnalyzerSlow()
        self.large = "xyz" * (10**6 // 3)

    def test_correctness(self):
        self.assertTrue(self.analyzer.has_repeated_pattern("abab"))
        self.assertTrue(self.analyzer.has_repeated_pattern("abcabcabc"))
        self.assertFalse(self.analyzer.has_repeated_pattern("abcd"))

    @performance_test(
        max_time=0.5,
        runs=20,
        outlier_pct=0.1,
        cpu_core=0,
        min_cores=4,
        min_freq_ghz=2.4
    )
    def test_performance_slow(self):
        self.assertTrue(self.analyzer.has_repeated_pattern(self.large))

if __name__ == "__main__":
    unittest.main(verbosity=2)
