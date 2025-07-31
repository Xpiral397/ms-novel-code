# tests

import unittest
from main import compute_k_ruff_sum

# Basic sieve-based prime generator
def first_k_primes_ending_in_7(k: int) -> list[int]:
    limit = 10000
    sieve = [True] * (limit + 1)
    sieve[0:2] = [False, False]
    for i in range(2, int(limit**0.5) + 1):
        if sieve[i]:
            for j in range(i*i, limit + 1, i):
                sieve[j] = False
    return [i for i in range(7, limit + 1) if sieve[i] and i % 10 == 7][:k]

# Brute-force correct F(k) using naive logic
def brute_force_k_ruff_sum(k: int) -> int:
    primes = first_k_primes_ending_in_7(k)
    Sk = [2, 5] + primes
    Nk = 1
    for p in Sk:
        Nk *= p
    total = 0
    for i in range(7, Nk, 10):  # Only numbers ending in 7
        if all(i % s != 0 for s in Sk):
            total += i
    return total % 1000000007

# Unit Tests
class TestComputeKRuffSum(unittest.TestCase):

    def test_k_1_output(self):
        """Known output test for k = 1"""
        self.assertEqual(compute_k_ruff_sum(1), 252)

    def test_k_3_output(self):
        """Known output test for k = 3"""
        self.assertEqual(compute_k_ruff_sum(3), 76101452)

    def test_k_1_brute_force(self):
        """Cross-check with brute-force for k = 1"""
        expected = brute_force_k_ruff_sum(1)
        self.assertEqual(compute_k_ruff_sum(1), expected)

    def test_k_2_brute_force(self):
        """Cross-check with brute-force for k = 2"""
        expected = brute_force_k_ruff_sum(2)
        self.assertEqual(compute_k_ruff_sum(2), expected)

    def test_k_3_brute_force(self):
        """Cross-check with brute-force for k = 3"""
        expected = brute_force_k_ruff_sum(3)
        self.assertEqual(compute_k_ruff_sum(3), expected)

    def test_k_10_type_and_range(self):
        result = compute_k_ruff_sum(10)
        self.assertIsInstance(result, int)
        self.assertGreaterEqual(result, 0)
        self.assertLess(result, 1000000007)

    def test_k_25_precision_safe(self):
        result = compute_k_ruff_sum(25)
        self.assertIsInstance(result, int)
        self.assertGreaterEqual(result, 0)

    def test_k_50_consistency(self):
        result = compute_k_ruff_sum(50)
        self.assertIsInstance(result, int)
        self.assertLess(result, 1000000007)

    def test_k_97_upper_bound(self):
        result = compute_k_ruff_sum(97)
        self.assertIsInstance(result, int)
        self.assertLess(result, 1000000007)

    def test_k_ruff_modulo_constraint(self):
        result = compute_k_ruff_sum(15)
        self.assertEqual(result % 1000000007, result)

    def test_k_ruff_nonnegative(self):
        result = compute_k_ruff_sum(40)
        self.assertGreaterEqual(result, 0)

    def test_k_97_prime_generation_consistency(self):
        primes = first_k_primes_ending_in_7(97)
        self.assertEqual(len(primes), 97)
        self.assertTrue(all(p % 10 == 7 for p in primes))

    def test_sk_size_for_k_10(self):
        primes = first_k_primes_ending_in_7(10)
        sk = {2, 5, *primes}
        self.assertEqual(len(sk), 12)

    def test_nk_bit_length_k_30(self):
        primes = first_k_primes_ending_in_7(30)
        sk = [2, 5] + primes
        nk = 1
        for p in sk:
            nk *= p
        self.assertGreater(nk.bit_length(), 64)
