# tests

import unittest
from main import find_nested_radical_pair

class TestFindNestedRadicalPair(unittest.TestCase):

    def test_all_zero(self):
        # Edge: all zeros; cube_root(0 + 0 + 0) = cube_root(cube_root(0) + cube_root(0)) = 0
        self.assertTrue(find_nested_radical_pair(0, 0, 0))

    def test_one_nonzero(self):
        # Edge: minimal positive input
        self.assertTrue(find_nested_radical_pair(0, 0, 1))

    def test_all_same_nonzero(self):
        # Case where all inputs are same non-zero
        self.assertTrue(find_nested_radical_pair(1, 1, 1))

    def test_negatives_cancel_out(self):
        # Edge: negatives cancel out total
        self.assertTrue(find_nested_radical_pair(-1, 1, 0))

    def test_no_possible_match(self):
        # Case: sum is irrational, can't be represented by any pair
        self.assertTrue(find_nested_radical_pair(1, 1, 0))

    def test_large_balanced_opposites(self):
        # Edge: large opposites that sum to zero
        self.assertFalse(find_nested_radical_pair(-10, 5, 5))

    def test_non_integer_target(self):
        # Rare case: cube_root(1)+cube_root(2)+cube_root(3) is irrational
        self.assertFalse(find_nested_radical_pair(1, 2, 3))

    def test_negative_sum_root_exists(self):
        # cube_root(-1)+cube_root(-8)+cube_root(27) = -1 -2 + 3 = 0
        self.assertTrue(find_nested_radical_pair(-1, -8, 27))

    def test_far_apart_inputs(self):
        # Spread out values to force deep search
        self.assertFalse(find_nested_radical_pair(-100, 50, 50))

    def test_max_bounds(self):
        # Upper bound edge
        self.assertFalse(find_nested_radical_pair(100, 100, 100))

    def test_min_bounds(self):
        # Lower bound edge
        self.assertFalse(find_nested_radical_pair(-100, -100, -100))

    def test_one_very_large_one_small(self):
        # Mix extremes with zero
        self.assertFalse(find_nested_radical_pair(0, 1, 100))

    def test_asymmetrical_negative_sum(self):
        # Asymmetrical sum with negative result
        self.assertFalse(find_nested_radical_pair(-5, -6, 10))

    def test_integer_sum_but_no_nested_root_form(self):
        # cube_root(1)+cube_root(8)+cube_root(27)= 1 + 2 + 3 = 6; try nested root = cube_root(cube_root(x)+cube_root(y)) = 6
        self.assertFalse(find_nested_radical_pair(1, 8, 27))

    def test_small_rational_target(self):
        # Try for target close to zero but not exactly zero
        self.assertTrue(find_nested_radical_pair(-1, 1, 1))

if __name__ == '__main__':
    unittest.main()
