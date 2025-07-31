# tests

import unittest
from main import min_sprinklers_to_activate

class TestMinSprinklersToActivate(unittest.TestCase):

    def test_all_zero_sprinklers(self):
        m = 3
        n = 3
        ranges = [
            [0, 0, 0],
            [0, 0, 0],
            [0, 0, 0]
        ]
        self.assertEqual(min_sprinklers_to_activate(m, n, ranges), -1)

    def test_single_sprinkler_full_coverage(self):
        m = 3
        n = 3
        ranges = [
            [0, 0, 0],
            [0, 4, 0],
            [0, 0, 0]
        ]
        self.assertEqual(min_sprinklers_to_activate(m, n, ranges), 1)

    def test_exact_prompt_example1(self):
        m = 3
        n = 4
        ranges = [
            [0, 2, 0, 0],
            [0, 0, 0, 3],
            [0, 0, 0, 0]
        ]
        self.assertEqual(min_sprinklers_to_activate(m, n, ranges), -1)

    def test_exact_prompt_example2(self):
        m = 3
        n = 3
        ranges = [
            [2, 0, 2],
            [0, 0, 0],
            [2, 0, 2]
        ]
        self.assertEqual(min_sprinklers_to_activate(m, n, ranges), 2)

    def test_max_bounds_full_coverage(self):
        m = 100
        n = 100
        ranges = [[0]*100 for _ in range(100)]
        ranges[0][0] = 200
        self.assertEqual(min_sprinklers_to_activate(m, n, ranges), 1)

    def test_sparse_sprinklers_insufficient(self):
        m = 4
        n = 4
        ranges = [
            [1, 0, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 1]
        ]
        self.assertEqual(min_sprinklers_to_activate(m, n, ranges), -1)

    def test_full_grid_each_corner_has_large_range(self):
        m = 5
        n = 5
        ranges = [
            [4, 0, 0, 0, 4],
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0],
            [4, 0, 0, 0, 4]
        ]
        self.assertEqual(min_sprinklers_to_activate(m, n, ranges), 2)

    def test_rectangle_grid_one_line_sprinklers(self):
        m = 3
        n = 7
        ranges = [
            [0, 0, 0, 0, 0, 0, 0],
            [3, 3, 3, 3, 3, 3, 3],
            [0, 0, 0, 0, 0, 0, 0]
        ]
        self.assertEqual(min_sprinklers_to_activate(m, n, ranges), 3)

    def test_corner_case_smallest_grid(self):
        m = 1
        n = 1
        ranges = [[0]]
        self.assertEqual(min_sprinklers_to_activate(m, n, ranges), -1)

    def test_corner_case_single_sprinkler_needed(self):
        m = 1
        n = 1
        ranges = [[0]]
        self.assertEqual(min_sprinklers_to_activate(m, n, ranges), -1)
        ranges = [[1]]
        self.assertEqual(min_sprinklers_to_activate(m, n, ranges), 1)

    def test_dense_grid_minimal_sprinklers(self):
        m = 5
        n = 5
        ranges = [
            [2, 0, 2, 0, 2],
            [0, 0, 0, 0, 0],
            [2, 0, 2, 0, 2],
            [0, 0, 0, 0, 0],
            [2, 0, 2, 0, 2]
        ]
        self.assertEqual(min_sprinklers_to_activate(m, n, ranges), 5)

    def test_sprinkler_exactly_reaching_boundary(self):
        m = 5
        n = 6
        ranges = [[0]*n for _ in range(m)]
        ranges[0][0] = m + n - 2
        self.assertEqual(min_sprinklers_to_activate(m, n, ranges), 1)

    def test_sprinkler_just_fails_to_cover_grid(self):
        m = 4
        n = 5
        ranges = [[0]*n for _ in range(m)]
        ranges[0][0] = m + n - 3  # just 1 short
        self.assertEqual(min_sprinklers_to_activate(m, n, ranges), -1)

    def test_overlapping_sprinklers_min_selection(self):
        m = 3
        n = 3
        ranges = [
            [2, 0, 0],
            [0, 0, 0],
            [0, 0, 2]
        ]
        self.assertEqual(min_sprinklers_to_activate(m, n, ranges), 2)

    def test_all_cells_have_range_zero(self):
        m = 3
        n = 3
        ranges = [[0]*n for _ in range(m)]
        for i in range(m):
            for j in range(n):
                ranges[i][j] = 0
        self.assertEqual(min_sprinklers_to_activate(m, n, ranges), -1)

    def test_sprinklers_with_out_of_bound_range_clipping(self):
        m = 5
        n = 5
        ranges = [[0]*n for _ in range(m)]
        ranges[0][0] = 100
        ranges[0][4] = 100
        ranges[4][0] = 100
        ranges[4][4] = 100
        self.assertEqual(min_sprinklers_to_activate(m, n, ranges), 1)

    def test_maximum_range_performance(self):
        m = 100
        n = 100
        ranges = [[0]*n for _ in range(m)]
        for i in range(0, 100, 20):
            for j in range(0, 100, 20):
                ranges[i][j] = 100
        result = min_sprinklers_to_activate(m, n, ranges)
        self.assertTrue(isinstance(result, int))
        self.assertNotEqual(result, -1)

if __name__ == '__main__':
    unittest.main(argv=[''], exit=False)
