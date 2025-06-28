# tests

import unittest
from main import count_frog_paths

class TestFrogRoundTrips(unittest.TestCase):

    def test_min_valid_input(self):
        self.assertEqual(count_frog_paths(1, 3), 4)

    def test_single_round_trip_medium_board(self):
        self.assertEqual(count_frog_paths(1, 4), 15)

    def test_two_round_trips_min_board(self):
        self.assertEqual(count_frog_paths(2, 3), 16)

    def test_max_jumps_no_overlap(self):
        self.assertEqual(count_frog_paths(1, 5), 46)

    def test_longer_board_single_trip(self):
        self.assertEqual(count_frog_paths(1, 6), 147)

    def test_all_jumps_contribute(self):
        result = count_frog_paths(1, 7)
        self.assertTrue(result > 189)

    def test_invalid_negative_rounds(self):
        self.assertEqual(count_frog_paths(-1, 10), -1)

    def test_invalid_zero_rounds(self):
        self.assertEqual(count_frog_paths(0, 10), -1)

    def test_invalid_large_rounds(self):
        self.assertEqual(count_frog_paths(11, 10), -1)

    def test_invalid_low_squares(self):
        self.assertEqual(count_frog_paths(2, 2), -1)

    def test_invalid_zero_squares(self):
        self.assertEqual(count_frog_paths(1, 0), -1)

    def test_single_trip_high_board(self):
        self.assertEqual(count_frog_paths(1, 1000), 0)

    def test_invalid_large_squares(self):
        self.assertEqual(count_frog_paths(1, 1001), -1)

    def test_invalid_round_trips_more_than_square(self):
        self.assertEqual(count_frog_paths(5, 2), -1)

    def test_maximum_input_limits(self):
        result = count_frog_paths(10, 1000)
        self.assertTrue(result >= 0)

    def test_double_trip_edge_board(self):
        result = count_frog_paths(2, 999)
        self.assertTrue(result >= 0)

    def test_revisit_valid_range_edge(self):
        result = count_frog_paths(10, 999)
        self.assertTrue(result >= 0)

    def test_full_visit_exhaustive_case(self):
        result = count_frog_paths(5, 5)
        self.assertTrue(result >= 0)


if __name__ == '__main__':
    unittest.main()
