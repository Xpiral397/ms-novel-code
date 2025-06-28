import unittest
import time
import os
import psutil
import functools
import platform
import statistics


from main import StringAnalyzer, StringAnalyzerSlow
# === Helper to detect real CPU cores inside Docker cgroups ===
def _detect_cgroup_cores() -> int:
    try:
        with open("/sys/fs/cgroup/cpu/cpu.cfs_quota_us") as f:
            quota = int(f.read().strip())
        with open("/sys/fs/cgroup/cpu/cpu.cfs_period_us") as f:
            period = int(f.read().strip())
        if quota > 0 and period > 0:
            return max(1, quota // period)
    except Exception:
        pass
    return psutil.cpu_count(logical=False) or 1

# === Performance‐testing decorator (never skips, only warns/fails) ===
def performance_test(
    max_time: float = 0.25,
    runs: int = 5,
    load_threshold: float = 10.0,
    warn_cores: int = 4,
    warn_freq_ghz: float = 2.4
):
    """
    Always runs the timing loop, prints warnings if:
      - detected cores < warn_cores
      - detected CPU freq < warn_freq_ghz
      - system load > load_threshold%
    Fails if median runtime > max_time.
    """
    def decorator(test_func):
        @functools.wraps(test_func)
        def wrapper(self, *args, **kwargs):
            # 1) Environment warnings
            cores = _detect_cgroup_cores()
            if cores < warn_cores:
                print(f"[PerfTest] WARNING: only {cores} cores detected; ideal ≥{warn_cores}")
            freq = psutil.cpu_freq()
            if freq and freq.current:
                ghz = freq.current / 1000.0
                if ghz < warn_freq_ghz:
                    print(f"[PerfTest] WARNING: CPU freq {ghz:.2f}GHz < {warn_freq_ghz}GHz")
            else:
                print("[PerfTest] WARNING: cannot detect CPU frequency")
            load = psutil.cpu_percent(interval=0.1)
            if load > load_threshold:
                print(f"[PerfTest] WARNING: system load {load:.1f}% > {load_threshold}%")
            print(f"[PerfTest] Env={platform.system()} | Cores={cores} | Load={load:.1f}%")

            # 2) (Optional) boost priority & set affinity on Linux
            try:
                proc = psutil.Process()
                proc.nice(-20)
            except Exception:
                pass
            if platform.system() == "Linux":
                try:
                    proc.cpu_affinity(list(range(cores)))
                except Exception:
                    pass

            # 3) Warm-up + timed runs
            timings = []
            total = runs + 1
            for i in range(total):
                t0 = time.time()
                test_func(self, *args, **kwargs)
                dt = time.time() - t0
                label = "warm-up" if i == 0 else f"run {i}"
                print(f"[PerfTest] {label}: {dt:.3f}s")
                if i > 0:
                    timings.append(dt)

            median_dt = statistics.median(timings)
            print(f"[PerfTest] median of {runs} runs = {median_dt:.3f}s (limit={max_time}s)")
            if median_dt > max_time:
                self.fail(f"Performance exceeded {max_time}s (median {median_dt:.3f}s)")
        return wrapper
    return decorator




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

    @performance_test()
    def test_performance_fast(self):
        # Include an assertion so the test body does work
        self.assertTrue(self.analyzer.has_repeated_pattern(self.large))

class TestStringAnalyzerSlow(unittest.TestCase):
    def setUp(self):
        self.analyzer = StringAnalyzerSlow()
        self.large = "xyz" * (10**6 // 3)

    def test_correctness(self):
        self.assertTrue(self.analyzer.has_repeated_pattern("abab"))
        self.assertTrue(self.analyzer.has_repeated_pattern("abcabcabc"))
        self.assertFalse(self.analyzer.has_repeated_pattern("abcd"))

    @performance_test()
    def test_performance_slow(self):
        self.assertTrue(self.analyzer.has_repeated_pattern(self.large))

if __name__ == "__main__":
    unittest.main(verbosity=2)
