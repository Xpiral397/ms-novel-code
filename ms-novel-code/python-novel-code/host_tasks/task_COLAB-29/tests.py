# tests

"""Unit tests for the max_active_students function."""

import unittest
from main import max_active_students


class TestMaxActiveStudentsFull(unittest.TestCase):
    """Test suite for the max_active_students function."""

    def test_case_01_empty_inputs(self):
        """Test with all empty inputs."""
        self.assertEqual(max_active_students({}, {}, []), 0)

    def test_case_02_wrong_types(self):
        """Test with wrong input types."""
        self.assertEqual(max_active_students([], {}, [1]), 0)
        self.assertEqual(max_active_students({}, [], [1]), 0)
        self.assertEqual(max_active_students({}, {}, 'invalid'), 0)

    def test_case_03_invalid_interval_ranges(self):
        """Test with invalid interval ranges."""
        self.assertEqual(max_active_students({1: [[1, 0]]}, {}, [1]), 0)
        self.assertEqual(max_active_students({1: [[-1, 5]]}, {}, [1]), 0)

    def test_case_04_invalid_dependencies(self):
        """Test with invalid dependency definitions."""
        deps = {(1, 0): [('x', 1)]}
        self.assertEqual(max_active_students({1: [[1, 5]]}, deps, [1]), 0)

        deps = {(1, 0): [(1, 1)]}
        self.assertEqual(max_active_students({1: [[1, 5]]}, deps, [1]), 0)

    def test_case_05_invalid_query(self):
        """Test with invalid query values."""
        self.assertEqual(max_active_students({1: [[1, 5]]}, {}, [-1]), 0)

    def test_case_06_single_student_no_dependencies(self):
        """Test a single student with multiple intervals."""
        intervals = {1: [[1, 5], [10, 15]]}
        queries = [0, 1, 5, 10, 12, 15, 16]
        self.assertEqual(max_active_students(intervals, {}, queries), 1)

    def test_case_07_self_dependency(self):
        """Test where a student's interval depends on another of their own."""
        intervals = {1: [[1, 5], [6, 10]]}
        dependencies = {(1, 1): [(1, 0)]}
        queries = [1, 5, 6, 10]
        self.assertEqual(
            max_active_students(intervals, dependencies, queries), 1
        )

    def test_case_08_cross_student_dependencies(self):
        """Test intervals with inter-student dependencies."""
        intervals = {1: [[1, 4]], 2: [[2, 6], [7, 10]]}
        dependencies = {(2, 1): [(1, 0), (2, 0)]}
        queries = [1, 3, 6, 7, 9, 10]
        self.assertEqual(
            max_active_students(intervals, dependencies, queries), 2
        )

    def test_case_09_cycle_detection(self):
        """Test with cyclic dependencies between intervals."""
        intervals = {1: [[1, 5], [6, 10]]}
        dependencies = {(1, 0): [(1, 1)], (1, 1): [(1, 0)]}
        self.assertEqual(
            max_active_students(intervals, dependencies, [1, 2, 3]), 0
        )

    def test_case_10_merging_intervals(self):
        """Test overlapping intervals."""
        intervals = {1: [[1, 3], [2, 5], [7, 9]], 2: [[4, 6]]}
        queries = [1, 3, 4, 5, 6, 7, 8, 9]
        self.assertEqual(max_active_students(intervals, {}, queries), 2)

    def test_case_11_disjoint_students(self):
        """Test disjoint student intervals."""
        intervals = {1: [[1, 2]], 2: [[3, 4]], 3: [[5, 6]]}
        self.assertEqual(max_active_students(intervals, {}, [1, 3, 5]), 1)

    def test_case_12_chain_dependencies(self):
        """Test chain of dependencies across students."""
        intervals = {
            1: [[1, 2]],
            2: [[3, 4]],
            3: [[5, 6]],
            4: [[7, 8]],
        }
        dependencies = {
            (2, 0): [(1, 0)],
            (3, 0): [(2, 0)],
            (4, 0): [(3, 0)],
        }
        queries = [1, 3, 5, 7]
        self.assertEqual(
            max_active_students(intervals, dependencies, queries), 1
        )

    def test_case_13_parallel_dependencies(self):
        """Test parallel dependencies for one interval."""
        intervals = {1: [[1, 3]], 2: [[1, 3]], 3: [[4, 6]]}
        dependencies = {(3, 0): [(1, 0), (2, 0)]}
        self.assertEqual(
            max_active_students(intervals, dependencies, [1, 4]), 2
        )

    def test_case_14_multiple_deps_same_interval(self):
        """Test interval with multiple dependencies."""
        intervals = {1: [[1, 2]], 2: [[1, 2]], 3: [[3, 4]]}
        dependencies = {(3, 0): [(1, 0), (2, 0)]}
        self.assertEqual(max_active_students(intervals, dependencies, [3]), 1)

    def test_case_15_all_active_same_time(self):
        """Test all students active at the same time with no dependencies."""
        intervals = {
            1: [[1, 5]],
            2: [[1, 5]],
            3: [[1, 5]],
        }
        self.assertEqual(max_active_students(intervals, {}, [3]), 3)

    def test_case_16_dependency_causes_expiry(self):
        """Test where dependency still allows activity in a tight window."""
        intervals = {
            1: [[1, 2]],
            2: [[2, 2]],
        }
        dependencies = {(2, 0): [(1, 0)]}
        self.assertEqual(
            max_active_students(intervals, dependencies, [2]), 2
        )

    def test_case_17_large_range(self):
        """Test single large interval with wide query range."""
        intervals = {1: [[0, 1000000]]}
        self.assertEqual(max_active_students(intervals, {}, [500000]), 1)

    def test_case_18_dependency_skips_window(self):
        """Test where dependency causes window to be missed."""
        intervals = {
            1: [[1, 2]],
            2: [[1, 1]],
        }
        dependencies = {(2, 0): [(1, 0)]}
        self.assertEqual(
            max_active_students(intervals, dependencies, [1, 2]), 1
        )

    def test_case_19_query_before_any_interval(self):
        """Test query timestamp before any interval starts."""
        intervals = {1: [[10, 20]]}
        self.assertEqual(max_active_students(intervals, {}, [5]), 0)

    def test_case_20_query_after_all_intervals(self):
        """Test query timestamp after all intervals end."""
        intervals = {1: [[1, 5]]}
        self.assertEqual(max_active_students(intervals, {}, [10]), 0)

    def test_case_21_disconnected_dependency_components(self):
        """Test multiple dependency trees isolated from each other."""
        intervals = {
            1: [[1, 2]],
            2: [[2, 3]],
            3: [[10, 11]],
            4: [[12, 13]],
        }
        dependencies = {
            (2, 0): [(1, 0)],
            (4, 0): [(3, 0)],
        }
        queries = [2, 3, 10, 13]
        self.assertEqual(
            max_active_students(intervals, dependencies, queries), 2
        )
