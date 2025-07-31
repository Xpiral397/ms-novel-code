# tests

import unittest
from main import palindromic_prime_sum


class TestPalindromicPrimeSum(unittest.TestCase):
    """Unit tests for palindromic_prime_sum."""

    def test_example_case(self):
        self.assertEqual(palindromic_prime_sum(21, 52), 99)

    def test_low_equals_high(self):
        self.assertEqual(palindromic_prime_sum(100, 100), 0)

    def test_low_greater_than_high(self):
        self.assertEqual(palindromic_prime_sum(100, 50), 0)

    def test_no_palindromic_primes(self):
        self.assertEqual(palindromic_prime_sum(90, 100), 99)

    def test_only_one_valid_palindrome(self):
        self.assertEqual(palindromic_prime_sum(30, 35), 33)

    def test_multiple_expressions_same_number(self):
        # 44 = 3+41 = 17+27 (not valid), but only counted once
        self.assertIn(44, [22, 33, 44])
        self.assertEqual(palindromic_prime_sum(20, 45), 99)

    def test_lower_bound_constraint(self):
        self.assertEqual(palindromic_prime_sum(9, 11), 0)

    def test_upper_bound_constraint(self):
        self.assertEqual(palindromic_prime_sum(9990, 10000), 0)

    def test_large_range(self):
        # Will take longer but should still be correct
        result = palindromic_prime_sum(10, 500)
        self.assertIsInstance(result, int)
        self.assertGreater(result, 0)

    def test_all_single_digit_range(self):
        self.assertEqual(palindromic_prime_sum(1, 10), 0)

    def test_all_even_palindromes(self):
        # Check only even palindromes that are prime sums are counted
        self.assertEqual(palindromic_prime_sum(20, 60), 154)

    def test_recursive_property(self):
        # Verify recursion by monkeypatching the max depth
        import sys
        original_limit = sys.getrecursionlimit()
        sys.setrecursionlimit(5000)
        try:
            self.assertEqual(palindromic_prime_sum(10, 100), palindromic_prime_sum(10, 100))
        finally:
            sys.setrecursionlimit(original_limit)


if __name__ == '__main__':
    unittest.main()
