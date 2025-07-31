# test_hybrid_factorizer.py
import unittest
import threading
from main import (
    gcd,
    trial_division,
    PollardP1Worker,
    PollardRhoWorker,
    HybridFactorizer
)


class TestHybridFactorizer(unittest.TestCase):

    def test_gcd(self):
        self.assertEqual(gcd(10, 15), 5)
        self.assertEqual(gcd(17, 13), 1)
        self.assertEqual(gcd(0, 5), 5)
        self.assertEqual(gcd(5, 0), 5)

    def test_trial_division(self):
        self.assertEqual(trial_division(15, 5), 3)
        self.assertIsNone(trial_division(17, 5))
        self.assertEqual(trial_division(49, 10), 7)

    def test_factorizer_even_and_one(self):
        f1 = HybridFactorizer(1)
        self.assertEqual(f1.factor(), (1, 1))
        f2 = HybridFactorizer(14)
        self.assertEqual(f2.factor(), (2, 7))

    def test_factorizer_small_composite(self):
        f3 = HybridFactorizer(21, trial_limit=10)
        self.assertEqual(f3.factor(), (3, 7))

    def test_factorizer_medium_composite(self):
        N = 101 * 103
        f4 = HybridFactorizer(N, trial_limit=5, rho_workers=2, rho_timeout=5.0)
        self.assertEqual(f4.factor(), (101, 103))

    def test_factorizer_prime(self):
        f5 = HybridFactorizer(97, trial_limit=10, rho_workers=2, rho_timeout=2.0)
        self.assertEqual(f5.factor(), (1, 97))

    def test_pollard_p1_worker(self):
        N = 13 * 17
        stop = threading.Event()
        hb = {}
        hb_lock = threading.Lock()
        result = {}
        lock = threading.Lock()
        w = PollardP1Worker(N, 50, stop, result, lock, hb, hb_lock)
        w.start()
        w.join(2.0)
        if "p" in result:
            p, q = result["p"], result["q"]
            self.assertIn(p, (13, 17))
            self.assertEqual(p * q, N)

    def test_pollard_rho_worker(self):
        N = 15
        stop = threading.Event()
        hb = {}
        hb_lock = threading.Lock()
        result = {}
        lock = threading.Lock()
        w = PollardRhoWorker(N, 1, stop, result, lock, hb, hb_lock)
        w.start()
        w.join(2.0)
        # now guaranteed to find factor quickly with x=2 start
        self.assertIn("p", result)
        p, q = result["p"], result["q"]
        self.assertIn(p, (3, 5))
        self.assertEqual(p * q, N)


if __name__ == "__main__":
    unittest.main()
