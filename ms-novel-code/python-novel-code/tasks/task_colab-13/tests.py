# tests

import unittest
from main import optimal_rideshare_assignment


class TestOptimalRideShareAssignment(unittest.TestCase):

    def test_basic_one_to_one(self):
        num_drivers = 2
        num_passengers = 2
        cost_matrix = [[1, 100], [100, 2]]
        result = optimal_rideshare_assignment(
            num_drivers, num_passengers, cost_matrix,
            max_assignments_per_driver=1,
            max_assignments_per_passenger=1,
            allow_multiple_assignments=False
        )
        self.assertEqual(result, [(0, 0), (1, 1)])

    def test_multiple_passengers_per_driver(self):
        num_drivers = 1
        num_passengers = 3
        cost_matrix = [[1, 2, 3]]
        result = optimal_rideshare_assignment(
            num_drivers, num_passengers, cost_matrix,
            max_assignments_per_driver=3,
            max_assignments_per_passenger=1,
            allow_multiple_assignments=True
        )
        self.assertEqual(
            sorted(result),
            [(0, 0), (0, 1), (0, 2)]
        )

    def test_disallow_multiple_assignments(self):
        num_drivers = 2
        num_passengers = 3
        cost_matrix = [[5, 10, 15], [10, 5, 10]]
        result = optimal_rideshare_assignment(
            num_drivers, num_passengers, cost_matrix,
            max_assignments_per_driver=1,
            max_assignments_per_passenger=1,
            allow_multiple_assignments=False
        )
        self.assertEqual(result, [(0, 0), (1, 1)])

    def test_minimal_input(self):
        num_drivers = 1
        num_passengers = 1
        cost_matrix = [[7]]
        result = optimal_rideshare_assignment(
            num_drivers, num_passengers, cost_matrix,
            max_assignments_per_driver=1,
            max_assignments_per_passenger=1,
            allow_multiple_assignments=False
        )
        self.assertEqual(result, [(0, 0)])

    def test_no_feasible_solution_due_to_constraints(self):
        num_drivers = 1
        num_passengers = 2
        cost_matrix = [[10, 20]]
        result = optimal_rideshare_assignment(
            num_drivers, num_passengers, cost_matrix,
            max_assignments_per_driver=1,
            max_assignments_per_passenger=1,
            allow_multiple_assignments=False
        )
        self.assertEqual(len(result), 1)  # Only one assignment is possible

    def test_return_ordering_of_assignments(self):
        num_drivers = 2
        num_passengers = 2
        cost_matrix = [[2, 1], [1, 2]]
        result = optimal_rideshare_assignment(
            num_drivers, num_passengers, cost_matrix,
            max_assignments_per_driver=1,
            max_assignments_per_passenger=1,
            allow_multiple_assignments=False
        )
        self.assertEqual(result, sorted(result))

    def test_driver_limit_less_than_passengers(self):
        num_drivers = 2
        num_passengers = 4
        cost_matrix = [
            [1, 2, 3, 4],
            [2, 3, 4, 5]
        ]
        result = optimal_rideshare_assignment(
            num_drivers, num_passengers, cost_matrix,
            max_assignments_per_driver=2,
            max_assignments_per_passenger=1,
            allow_multiple_assignments=True
        )
        self.assertTrue(all(d <= 1 for d, _ in result))  # Only two per driver

    def test_passenger_limit_less_than_drivers(self):
        num_drivers = 3
        num_passengers = 2
        cost_matrix = [
            [4, 2],
            [3, 1],
            [2, 5]
        ]
        result = optimal_rideshare_assignment(
            num_drivers, num_passengers, cost_matrix,
            max_assignments_per_driver=1,
            max_assignments_per_passenger=1,
            allow_multiple_assignments=False
        )
        self.assertEqual(len(result), 2)

    def test_maximum_assignments_exact(self):
        num_drivers = 2
        num_passengers = 4
        cost_matrix = [
            [1, 2, 3, 4],
            [2, 3, 4, 5]
        ]
        result = optimal_rideshare_assignment(
            num_drivers, num_passengers, cost_matrix,
            max_assignments_per_driver=2,
            max_assignments_per_passenger=1,
            allow_multiple_assignments=True
        )
        self.assertEqual(len(result), 4)

    def test_infeasible_due_to_excess_demand(self):
        num_drivers = 1
        num_passengers = 3
        cost_matrix = [[3, 2, 1]]
        result = optimal_rideshare_assignment(
            num_drivers, num_passengers, cost_matrix,
            max_assignments_per_driver=1,
            max_assignments_per_passenger=1,
            allow_multiple_assignments=False
        )
        self.assertEqual(len(result), 1)

    def test_empty_assignment_due_to_zero_limits(self):
        num_drivers = 2
        num_passengers = 2
        cost_matrix = [[1, 2], [3, 4]]
        result = optimal_rideshare_assignment(
            num_drivers, num_passengers, cost_matrix,
            max_assignments_per_driver=0,
            max_assignments_per_passenger=0,
            allow_multiple_assignments=True
        )
        self.assertEqual(result, [])

    def test_identical_costs(self):
        num_drivers = 2
        num_passengers = 2
        cost_matrix = [[5, 5], [5, 5]]
        result = optimal_rideshare_assignment(
            num_drivers, num_passengers, cost_matrix,
            max_assignments_per_driver=1,
            max_assignments_per_passenger=1,
            allow_multiple_assignments=False
        )
        self.assertEqual(len(result), 2)


if __name__ == '__main__':
    unittest.main()
