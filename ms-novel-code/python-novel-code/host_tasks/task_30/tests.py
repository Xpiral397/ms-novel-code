# tests
import unittest as ut
from main import last_ant_fall_time

class TestLastAntFallTime(ut.TestCase):

    def test_case_1_basic(self):
        n = 10
        left = [2, 6]
        right = [7]
        self.assertEqual(last_ant_fall_time(n, left, right), 6)

    def test_case_2_typical(self):
        n = 100
        left = [10, 50, 90]
        right = [1, 99]
        self.assertEqual(last_ant_fall_time(n, left, right), 99)

    def test_case_3_all_left(self):
        n = 30
        left = [5, 15, 29]
        right = []
        self.assertEqual(last_ant_fall_time(n, left, right), 29)

    def test_case_4_all_right(self):
        n = 40
        left = []
        right = [10, 20, 25]
        self.assertEqual(last_ant_fall_time(n, left, right), 30)

    def test_case_5_single_left(self):
        n = 100
        left = [65]
        right = []
        self.assertEqual(last_ant_fall_time(n, left, right), 65)

    def test_case_6_single_right(self):
        n = 200
        left = []
        right = [25]
        self.assertEqual(last_ant_fall_time(n, left, right), 175)

    def test_case_7_meeting_points(self):
        n = 50
        left = [5, 15, 45]
        right = [10, 30]
        self.assertEqual(last_ant_fall_time(n, left, right), 45)

    def test_case_8_max_range(self):
        n = 1_000_000
        left = [500_000]
        right = [1]
        self.assertEqual(last_ant_fall_time(n, left, right), 999_999)

    def test_case_9_large_left_heavy(self):
        n = 500_000
        left = [1, 2, 499_999]
        right = []
        self.assertEqual(last_ant_fall_time(n, left, right), 499_999)

    def test_case_10_large_right_heavy(self):
        n = 750_000
        left = []
        right = [500, 10_000, 100_000]
        self.assertEqual(last_ant_fall_time(n, left, right), 750_000 - 500)

if __name__ == '__main__':
    ut.main()
