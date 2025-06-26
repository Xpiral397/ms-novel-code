# tests
import unittest

# Function assumed imported
from main import solve_pentagonal_sums

class TestFindPentagonalSums(unittest.TestCase):

    def test_exactly_one_valid_sum(self):
        result = solve_pentagonal_sums(n=20, min_ways=1)
        self.assertTrue(any(entry[1] == 1 for entry in result))
        self.assertTrue(all(len(entry[2]) == entry[1] for entry in result))

    def test_multiple_valid_sums(self):
        result = solve_pentagonal_sums(n=50, min_ways=1)
        self.assertTrue(len(result) > 1)
        self.assertTrue(all(entry[1] >= 1 for entry in result))
        self.assertTrue(all(len(entry[2]) == entry[1] for entry in result))

    def test_minimum_n_input(self):
        result = solve_pentagonal_sums(n=1, min_ways=1)
        self.assertEqual(result, [])

    def test_high_min_ways_no_result(self):
        result = solve_pentagonal_sums(n=20, min_ways=5)
        self.assertEqual(result, [])

    def test_multiple_ways_single_number(self):
        result = solve_pentagonal_sums(n=50, min_ways=2)
        # There should be at least one pentagonal number with >= 2 ways
        self.assertTrue(any(entry[1] >= 2 for entry in result))

    def test_multiple_numbers_with_multiple_ways(self):
        result = solve_pentagonal_sums(n=80, min_ways=1)
        self.assertTrue(len(result) > 1)
        for entry in result:
            self.assertGreaterEqual(entry[1], 1)

    def test_combinations_no_duplicates(self):
        result = solve_pentagonal_sums(n=50, min_ways=1)
        for entry in result:
            combinations = entry[2]
            for p1, p2 in combinations:
                self.assertLessEqual(p1, p2)

    def test_large_n_performance(self):
        # Just check that it runs and returns valid structure
        result = solve_pentagonal_sums(n=100, min_ways=1)
        for entry in result:
            self.assertIsInstance(entry[0], int)  # pentagonal_number
            self.assertIsInstance(entry[1], int)  # ways_count
            self.assertIsInstance(entry[2], list)  # combinations list

    def test_results_sorted(self):
        result = solve_pentagonal_sums(n=50, min_ways=1)
        pentagonal_numbers = [entry[0] for entry in result]
        self.assertEqual(pentagonal_numbers, sorted(pentagonal_numbers))

    def test_self_pair_sum_validity(self):
        # P(7) = 70, which can be expressed as 35 + 35 (P(5) + P(5))
        result = solve_pentagonal_sums(n=7, min_ways=1)
        # Find entry with pentagonal number 70
        found = False
        for entry in result:
            if entry[0] == 70:
                self.assertIn([35, 35], entry[2])
                found = True
        self.assertTrue(found, "Expected self-pair sum 35+35=70 not found in results")

if __name__ == '__main__':
    unittest.main()
