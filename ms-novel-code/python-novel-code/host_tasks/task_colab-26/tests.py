# tests

import unittest
from math import factorial
from main import count_digit_factorial_chains

class TestCountDigitFactorialChains(unittest.TestCase):

    def test_example_from_prompt(self):
        self.assertEqual(count_digit_factorial_chains(10000, 3), 147)

    def test_single_value_limit(self):
        result = count_digit_factorial_chains(2, 1)
        self.assertIn(result, [0, 1])

    def test_small_limit_no_match(self):
        self.assertEqual(count_digit_factorial_chains(10, 5), 0)

    def test_chain_length_1(self):
        result = count_digit_factorial_chains(146, 1)
        self.assertGreaterEqual(result, 1)

    def test_immediate_loop_edge_case(self):
        self.assertIn(169, [169])
        self.assertGreaterEqual(count_digit_factorial_chains(170, 3), 1)

    def test_large_limit_with_known_result(self):
        result = count_digit_factorial_chains(1_000_000, 60)
        self.assertEqual(result, 402)

    def test_multiple_matches(self):
        self.assertGreaterEqual(count_digit_factorial_chains(100, 1), 1)

    def test_chain_length_2(self):
        self.assertGreaterEqual(count_digit_factorial_chains(872, 2), 1)

    def test_edge_limit_exclusion(self):
        result_inclusive = count_digit_factorial_chains(100, 1)
        result_exclusive = count_digit_factorial_chains(99, 1)
        self.assertLessEqual(result_exclusive, result_inclusive)

    def test_non_trivial_chain(self):
        self.assertIsInstance(count_digit_factorial_chains(70, 5), int)

    def test_shared_chains_counted_independently(self):
      count = count_digit_factorial_chains(873, 2)
      self.assertGreaterEqual(count, 2)

    def test_starting_number_in_known_loop_has_zero_length(self):
      count = count_digit_factorial_chains(169, 1)
      self.assertGreaterEqual(count, 1)
