# tests

import unittest
import sys
import numpy as np
import decimal
from main import OrderLookup


class TestOrderLookup(unittest.TestCase):

    def test_empty_list_returns_minus1_and_zero_comparisons(self):
        self.assertEqual(OrderLookup.find_order([], 5), (-1, 0))

    def test_first_element_match(self):
        self.assertEqual(OrderLookup.find_order([10, 20, 30], 10), (0, 1))

    def test_last_element_match(self):
        self.assertEqual(OrderLookup.find_order([1, 2, 3, 4, 5], 5), (4, 5))

    def test_all_elements_match_target(self):
        self.assertEqual(OrderLookup.find_order([7, 7, 7], 7), (0, 1))

    def test_duplicate_ids_returns_earliest_index(self):
        self.assertEqual(OrderLookup.find_order([9, 3, 9, 9], 9), (0, 1))

    def test_target_not_found(self):
        self.assertEqual(OrderLookup.find_order([10, 20, 30], 99), (-1, 3))

    def test_type_error_non_list_input(self):
        with self.assertRaisesRegex(TypeError, "orders must be a list of integers"):
            OrderLookup.find_order("not a list", 1)

    def test_type_error_non_int_elements(self):
        with self.assertRaisesRegex(TypeError, "orders must contain only integers"):
            OrderLookup.find_order([1, 2.0, 3], 3)

    def test_type_error_for_bool_in_list(self):
        with self.assertRaisesRegex(TypeError, "orders must contain only integers"):
            OrderLookup.find_order([1, True, 3], 3)

    def test_type_error_for_target(self):
        with self.assertRaisesRegex(TypeError, "target must be an integer"):
            OrderLookup.find_order([1, 2, 3], "3")

    def test_value_error_for_list_exceeding_limit(self):
        with self.assertRaisesRegex(ValueError, "orders length exceeds 10,000"):
            OrderLookup.find_order([1] * 10001, 1)

    def test_valid_numpys_and_range_bounds(self):
      big = sys.maxsize
      small = -sys.maxsize - 1
      self.assertEqual(OrderLookup.find_order([np.int64(big), np.int64(small)], small), (1, 2))


    def test_decimal_in_orders_raises_type_error(self):
        with self.assertRaisesRegex(TypeError, "orders must contain only integers"):
            OrderLookup.find_order([1, decimal.Decimal(2), 3], 2)

    def test_large_integer_in_orders_raises_value_error(self):
        too_big = sys.maxsize + 1
        too_small = -sys.maxsize - 2
        with self.assertRaises(ValueError):
            OrderLookup.find_order([1, too_big], 1)
        with self.assertRaises(ValueError):
            OrderLookup.find_order([1, too_small], 1)

    def test_target_out_of_bounds_raises_value_error(self):
        too_big = sys.maxsize + 1
        too_small = -sys.maxsize - 2
        with self.assertRaises(ValueError):
            OrderLookup.find_order([1, 2, 3], too_big)
        with self.assertRaises(ValueError):
            OrderLookup.find_order([1, 2, 3], too_small)


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
