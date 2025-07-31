# test.py

import unittest
import time
import os
import psutil
import functools

# Define the classes to be tested
class StringAnalyzerFast:
    def has_repeated_pattern(self, s: str) -> bool:
        if len(s) < 2:
            return False
        doubled = (s + s)[1:-1]
        return s in doubled

class StringAnalyzerSlow(StringAnalyzerFast):
    def has_repeated_pattern(self, s: str) -> bool:
        # Introduce artificial delay to simulate a slow algorithm
        time.sleep(0.5)
        return super().has_repeated_pattern(s)

# Performance decorator
def performance_test(cores=4, min_freq_ghz=2.4, max_time=0.25):
    def decorator(test_func):
        @functools.wraps(test_func)
        def wrapper(self, *args, **kwargs):
            # Check machine specs
            physical = psutil.cpu_count(logical=False) or 0
            freq = (psutil.cpu_freq().max or 0) / 1000

            print(freq, physical, 'gggggggggggggggggggggggggggggggggggggggg')
            if physical < cores or freq < min_freq_ghz:
                self.skipTest(f"Requires ≥{cores} cores @ {min_freq_ghz}GHz")
            # Bind to cores
            try:
                proc = psutil.Process()
                proc.cpu_affinity(list(range(cores)))
            except Exception:
                pass
            start = time.time()
            test_func(self, *args, **kwargs)
            elapsed = time.time() - start
            if elapsed > max_time:
                self.fail(f"Performance exceeded {max_time}s (took {elapsed:.3f}s)")
        return wrapper
    return decorator

# Test cases
class TestStringAnalyzerFast(unittest.TestCase):
    def setUp(self):
        self.analyzer = StringAnalyzerFast()
        self.large_input = "xyz" * (10**6 // 3)

    def test_correctness(self):
        self.assertTrue(self.analyzer.has_repeated_pattern("abab"))
        self.assertTrue(self.analyzer.has_repeated_pattern("abcabcabc"))
        self.assertFalse(self.analyzer.has_repeated_pattern("abcd"))

    @performance_test(cores=4, min_freq_ghz=2.4, max_time=0.25)
    def test_performance(self):
        result = self.analyzer.has_repeated_pattern(self.large_input)
        self.assertTrue(result)

class TestStringAnalyzerSlow(unittest.TestCase):
    def setUp(self):
        self.analyzer = StringAnalyzerSlow()
        self.large_input = "xyz" * (10**6 // 3)

    def test_correctness(self):
        self.assertTrue(self.analyzer.has_repeated_pattern("abab"))
        self.assertTrue(self.analyzer.has_repeated_pattern("abcabcabc"))
        self.assertFalse(self.analyzer.has_repeated_pattern("abcd"))

    def test_performance_should_fail(self):
        with self.assertRaises(AssertionError):
            TestStringAnalyzerFast.test_performance(self)

# Run tests
loader = unittest.TestLoader()
suite = unittest.TestSuite()
suite.addTests(loader.loadTestsFromTestCase(TestStringAnalyzerFast))
suite.addTests(loader.loadTestsFromTestCase(TestStringAnalyzerSlow))

runner = unittest.TextTestRunner(verbosity=2)
runner.run(suite)
