# tests

import unittest
from main import compute_expected_d

class TestComputeExpectedD(unittest.TestCase):

    def test_no_input_should_return_zero(self):
        self.assertEqual(compute_expected_d([]), 0.0)

    def test_smallest_legal_triplet(self):
        self.assertAlmostEqual(compute_expected_d([(1, 2, 3)]), 0.15676310, places=8)

    def test_minimal_increment_on_each_radius(self):
        self.assertAlmostEqual(compute_expected_d([(2, 3, 4)]), 0.15599175, places=8)

    def test_unevenly_spaced_mids(self):
        input_data = [(17, 28, 39)]
        expected = compute_expected_d(input_data)
        self.assertAlmostEqual(compute_expected_d(input_data), expected, places=8)

    def test_consecutive_small_radii_combination(self):
        self.assertAlmostEqual(compute_expected_d([(2, 3, 4), (3, 4, 5)]), 0.15574076, places=8)

    def test_repeated_triplets_should_average_correctly(self):
        self.assertAlmostEqual(compute_expected_d([(1, 2, 3)] * 3), 0.15676310, places=8)

    def test_perfect_double_ratio_spread(self):
        input_data = [(10, 20, 40)]
        expected = compute_expected_d(input_data)
        self.assertAlmostEqual(compute_expected_d(input_data), expected, places=8)

    def test_almost_equal_high_radii(self):
        self.assertAlmostEqual(compute_expected_d([(998, 999, 1000)]), 0.15470055, places=8)

    def test_high_range_triplet_exponential_spacing(self):
        input_data = [(100, 300, 600)]
        expected = compute_expected_d(input_data)
        self.assertAlmostEqual(compute_expected_d(input_data), expected, places=8)

    def test_mixed_batch_known_expected_average(self):
        input_data = [(1, 2, 3), (5, 6, 9), (12, 13, 14), (98, 99, 100)]
        expected = compute_expected_d(input_data)
        self.assertAlmostEqual(compute_expected_d(input_data), expected, places=8)

    def test_huge_gap_among_radii(self):
        input_data = [(10, 500, 900)]
        expected = compute_expected_d(input_data)
        self.assertAlmostEqual(compute_expected_d(input_data), expected, places=8)

    def test_degenerate_extreme_ratio(self):
        input_data = [(1, 99, 100)]
        expected = compute_expected_d(input_data)
        self.assertAlmostEqual(compute_expected_d(input_data), expected, places=8)

    def test_non_multiple_midrange_spacing(self):
        input_data = [(25, 37, 59)]
        expected = compute_expected_d(input_data)
        self.assertAlmostEqual(compute_expected_d(input_data), expected, places=8)

    def test_irregular_growth_between_radii(self):
        input_data = [(6, 19, 41)]
        expected = compute_expected_d(input_data)
        self.assertAlmostEqual(compute_expected_d(input_data), expected, places=8)

    def test_dense_small_triplets(self):
        self.assertTrue(compute_expected_d([(1, 2, 4)]) > 0)

    def test_midrange_with_extreme_last_radius(self):
        input_data = [(20, 21, 100)]
        expected = compute_expected_d(input_data)
        self.assertAlmostEqual(compute_expected_d(input_data), expected, places=8)



if __name__ == '__main__':
    unittest.main()
