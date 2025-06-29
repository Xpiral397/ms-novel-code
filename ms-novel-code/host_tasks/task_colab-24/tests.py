# tests

import unittest
from decimal import Decimal
from main import expected_dishes


class TestExpectedDishes(unittest.TestCase):
    """Unit tests for the expected_dishes function."""

    def assertRoundedEqual(self, val1: str, val2: str, places: int = 8):
        """
        Assert that two string-formatted floats are equal up to specified decimal places.
        """
        self.assertEqual(round(Decimal(val1), places), round(Decimal(val2), places))

    def test_case_1_single_chef(self):
        """Edge case: Only one chef."""
        self.assertRoundedEqual(expected_dishes(1), "1.00000000")

    def test_case_2_small_n(self):
        """Check basic validity for n = 2."""
        result = expected_dishes(2)
        self.assertIsInstance(result, str)
        self.assertGreater(Decimal(result), 1)
        self.assertEqual(len(result.split(".")[1]), 8)

    def test_case_3_given_example_n7(self):
        """Given example: E(7) = 42.28176050."""
        self.assertRoundedEqual(expected_dishes(7), "42.28176050")

    def test_case_4_progression_check(self):
        """Monotonic check: E(n+1) >= E(n) for 2 <= n <= 10."""
        prev = Decimal(expected_dishes(2))
        for n in range(3, 11):
            curr = Decimal(expected_dishes(n))
            self.assertGreaterEqual(curr, prev)
            prev = curr

    def test_case_5_precision_check(self):
        """Ensure all values have 8 decimal digits."""
        for n in range(1, 15):
            result = expected_dishes(n)
            self.assertRegex(result, r"^\d+\.\d{8}$")

    def test_case_6_output_type(self):
        """Check return type is string."""
        self.assertIsInstance(expected_dishes(5), str)

    def test_case_7_range_validity(self):
        """Check that values are within expected range for small n."""
        for n in range(1, 5):
            result = Decimal(expected_dishes(n))
            self.assertGreaterEqual(result, 1)
            self.assertLessEqual(result, 30)

    def test_case_8_upper_bound_n14(self):
        """Stress test the upper bound n = 14."""
        result = expected_dishes(14)
        self.assertIsInstance(result, str)
        self.assertEqual(len(result.split('.')[-1]), 8)
        self.assertGreater(Decimal(result), 50)

    def test_case_9_value_stability(self):
        """Ensure repeated calls return same result (no internal mutation)."""
        val1 = expected_dishes(6)
        val2 = expected_dishes(6)
        self.assertEqual(val1, val2)

    def test_case_10_realistic_boundaries(self):
        """Ensure value trends remain reasonable for middle values."""
        expected_ranges = {
            4: (6, 20),
            5: (10, 30),
            6: (20, 40),
        }
        for n, (lower, upper) in expected_ranges.items():
            value = Decimal(expected_dishes(n))
            self.assertGreater(value, lower)
            self.assertLess(value, upper)


if __name__ == "__main__":
    unittest.main()
