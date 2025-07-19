# test

import unittest as ut
from main import MajorityChecker

class TestMajorityChecker(ut.TestCase):
    def test_case_1(self):
        nums = [1, 1, 2, 2, 1, 1]
        checker = MajorityChecker(nums)
        self.assertEqual(checker.query(0, 5, 4), 1)

    def test_case_2(self):
        nums = [1, 1, 2, 2, 1, 1]
        checker = MajorityChecker(nums)
        self.assertEqual(checker.query(0, 3, 3), -1)

    def test_case_3(self):
        nums = [5, 5, 1, 5, 2, 5, 5, 3]
        checker = MajorityChecker(nums)
        self.assertEqual(checker.query(0, 7, 5), 5)

    def test_case_4(self):
        nums = [2, 2, 2, 2, 2]
        checker = MajorityChecker(nums)
        self.assertEqual(checker.query(1, 3, 2), 2)

    def test_case_5(self):
        nums = [3, 3, 4, 4, 4, 3, 3]
        checker = MajorityChecker(nums)
        self.assertEqual(checker.query(0, 6, 4), 3)

    def test_case_6(self):
        nums = [1, 2, 3, 4, 5]
        checker = MajorityChecker(nums)
        self.assertEqual(checker.query(0, 4, 2), -1)

    def test_case_7(self):
        nums = [7, 7, 7, 7, 7]
        checker = MajorityChecker(nums)
        self.assertEqual(checker.query(0, 4, 5), 7)

    def test_case_8(self):
        nums = [9]
        checker = MajorityChecker(nums)
        self.assertEqual(checker.query(0, 0, 1), 9)

    def test_case_9(self):
        nums = [1, 2, 1, 2, 1]
        checker = MajorityChecker(nums)
        self.assertEqual(checker.query(0, 4, 3), 1)

    def test_case_10(self):
        nums = [1, 2, 3, 2, 2, 2, 4]
        checker = MajorityChecker(nums)
        self.assertEqual(checker.query(1, 5, 3), 2)

if __name__ == "__main__":
    ut.main()
