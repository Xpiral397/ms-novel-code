# tests

import unittest
from sympy import symbols, log
from main import solve_recurrence

class TestSolveRecurrence(unittest.TestCase):
    def test_basic_case_linear(self):
        recurrence = "T(n) = 2 * T(n / 2) + n"
        params = {"a": 2, "b": 2, "f(n)": "n", "base_case": "1"}
        self.assertEqual(solve_recurrence(recurrence, params), "T(n) = n*log(n)")

    def test_quadratic_case(self):
        recurrence = "T(n) = 3 * T(n / 4) + n ^ 2"
        params = {"a": 3, "b": 4, "f(n)": "n ^ 2", "base_case": "1"}
        self.assertEqual(solve_recurrence(recurrence, params), "T(n) = n**2")

    def test_log_case(self):
        recurrence = "T(n) = 1 * T(n / 2) + log(n)"
        params = {"a": 1, "b": 2, "f(n)": "log(n)", "base_case": "1"}
        self.assertEqual(solve_recurrence(recurrence, params), "T(n) = log(n)**2")

    def test_cubic_case(self):
        recurrence = "T(n) = 8 * T(n / 2) + n ^ 2"
        params = {"a": 8, "b": 2, "f(n)": "n ^ 2", "base_case": "1"}
        self.assertEqual(solve_recurrence(recurrence, params), "T(n) = n**3")

    def test_log_linear_case(self):
        recurrence = "T(n) = 2 * T(n / 2) + n * log(n)"
        params = {"a": 2, "b": 2, "f(n)": "n * log(n)", "base_case": "1"}
        self.assertEqual(solve_recurrence(recurrence, params), "T(n) = n*log(n)**2")

    def test_a_less_than_equal_zero(self):
        recurrence = "T(n) = 0 * T(n / 2) + n"
        params = {"a": 0, "b": 2, "f(n)": "n", "base_case": "1"}
        with self.assertRaises(ValueError):
            solve_recurrence(recurrence, params)

    def test_b_less_than_equal_one(self):
        recurrence = "T(n) = 2 * T(n / 1) + n"
        params = {"a": 2, "b": 1, "f(n)": "n", "base_case": "1"}
        with self.assertRaises(ValueError):
            solve_recurrence(recurrence, params)

    def test_invalid_base_case(self):
        recurrence = "T(n) = 2 * T(n / 2) + n"
        params = {"a": 2, "b": 2, "f(n)": "n", "base_case": "abc"}
        with self.assertRaises(SyntaxError):
            solve_recurrence(recurrence, params)

    def test_unsupported_function(self):
        recurrence = "T(n) = 2 * T(n / 2) + n!"
        params = {"a": 2, "b": 2, "f(n)": "n!", "base_case": "1"}
        self.assertEqual(solve_recurrence(recurrence, params), "Unsupported function")

    def test_empty_input(self):
        self.assertEqual(solve_recurrence("", {}), "Invalid input")

    def test_missing_params(self):
        recurrence = "T(n) = 2 * T(n / 2) + n"
        self.assertEqual(solve_recurrence(recurrence, {}), "Invalid input")

    def test_invalid_fn_expression(self):
        recurrence = "T(n) = 2 * T(n / 2) + n +"
        params = {"a": 2, "b": 2, "f(n)": "n +", "base_case": "1"}
        self.assertEqual(solve_recurrence(recurrence, params), "Invalid input")

    def test_unrecognized_expression(self):
        recurrence = "T(n) = 2 * T(n / 2) + [n]"
        params = {"a": 2, "b": 2, "f(n)": "[n]", "base_case": "1"}
        self.assertEqual(solve_recurrence(recurrence, params), "Invalid input")

    def test_constant_fn_case(self):
        recurrence = "T(n) = 4 * T(n / 2) + 1"
        params = {"a": 4, "b": 2, "f(n)": "1", "base_case": "1"}
        self.assertEqual(solve_recurrence(recurrence, params), "T(n) = n**2")

    def test_equal_fn_and_log_threshold(self):
        recurrence = "T(n) = 4 * T(n / 2) + n^2"
        params = {"a": 4, "b": 2, "f(n)": "n^2", "base_case": "1"}
        self.assertEqual(solve_recurrence(recurrence, params), "T(n) = n**2*log(n)")

    def test_polylog_case(self):
        recurrence = "T(n) = 2 * T(n / 2) + n * log(n)"
        params = {"a": 2, "b": 2, "f(n)": "n * log(n)", "base_case": "1"}
        self.assertEqual(solve_recurrence(recurrence, params), "T(n) = n*log(n)**2")

    def test_unresolvable_case(self):
        recurrence = "T(n) = T(n / 3) + sin(n)"
        params = {"a": 1, "b": 3, "f(n)": "sin(n)", "base_case": "1"}
        # CORRECTED: sin(n) is an unsupported function, not an unsolvable case
        self.assertEqual(solve_recurrence(recurrence, params), "Unsupported function")

if __name__ == '__main__':
    unittest.main(argv=[''], exit=False)
