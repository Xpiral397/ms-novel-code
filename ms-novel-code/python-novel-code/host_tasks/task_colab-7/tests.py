# tests

import unittest
import numpy as np
from main import kernel_weighted_regression


class TestKernelWeightedRegression(unittest.TestCase):

    def setUp(self):
        self.X_basic = np.array([[1], [2], [3]])
        self.y_basic = np.array([1, 2, 3])

    def test_gaussian_basic(self):
        coeffs, w = kernel_weighted_regression(self.X_basic, self.y_basic, "gaussian", 1.0, 100, 1e-6)
        self.assertEqual(coeffs.shape, (1,))
        self.assertTrue(np.allclose(w, w.T))

    def test_laplacian_basic(self):
        coeffs, w = kernel_weighted_regression(self.X_basic, self.y_basic, "laplacian", 1.0, 100, 1e-6)
        self.assertEqual(coeffs.shape, (1,))
        self.assertTrue(np.allclose(w, w.T))

    def test_linear_basic(self):
        coeffs, w = kernel_weighted_regression(self.X_basic, self.y_basic, "linear", 1.0, 100, 1e-6)
        self.assertEqual(coeffs.shape, (1,))
        self.assertTrue(np.allclose(w, w.T))

    def test_zero_bandwidth(self):
        with self.assertRaises(ValueError):
            kernel_weighted_regression(self.X_basic, self.y_basic, "gaussian", 0, 100, 1e-6)

    def test_negative_bandwidth(self):
        with self.assertRaises(ValueError):
            kernel_weighted_regression(self.X_basic, self.y_basic, "gaussian", -1, 100, 1e-6)

    def test_invalid_kernel(self):
        with self.assertRaises(ValueError):
            kernel_weighted_regression(self.X_basic, self.y_basic, "cosine", 1.0, 100, 1e-6)

    def test_nan_input_X(self):
        X = self.X_basic.astype(float)
        X[0, 0] = np.nan
        with self.assertRaises(ValueError):
            kernel_weighted_regression(X, self.y_basic, "gaussian", 1.0, 100, 1e-6)

    def test_nan_input_y(self):
        y = self.y_basic.astype(float)
        y[1] = np.nan
        with self.assertRaises(ValueError):
            kernel_weighted_regression(self.X_basic, y, "gaussian", 1.0, 100, 1e-6)

    def test_empty_X(self):
        with self.assertRaises(ValueError):
            kernel_weighted_regression(np.array([]).reshape(0, 0), np.array([]), "gaussian", 1.0, 100, 1e-6)

    def test_incorrect_dim_X(self):
        with self.assertRaises(AssertionError):
            kernel_weighted_regression(np.array([1, 2, 3]), self.y_basic, "gaussian", 1.0, 100, 1e-6)

    def test_incorrect_dim_y(self):
        with self.assertRaises(AssertionError):
            kernel_weighted_regression(self.X_basic, self.y_basic.reshape(-1, 1), "gaussian", 1.0, 100, 1e-6)

    def test_mismatched_dimensions(self):
        with self.assertRaises(ValueError):
            kernel_weighted_regression(self.X_basic, np.array([1, 2]), "gaussian", 1.0, 100, 1e-6)

    def test_tolerance_negative(self):
        with self.assertRaises(ValueError):
            kernel_weighted_regression(self.X_basic, self.y_basic, "gaussian", 1.0, 100, -0.1)

    def test_zero_max_iter(self):
        with self.assertRaises(ValueError):
            kernel_weighted_regression(self.X_basic, self.y_basic, "gaussian", 1.0, 0, 1e-6)

    def test_coeffs_rounding(self):
        coeffs, _ = kernel_weighted_regression(self.X_basic, self.y_basic, "gaussian", 0.5, 100, 1e-6)
        decimals = np.abs(coeffs * 10000 - np.round(coeffs * 10000))
        self.assertTrue(np.all(decimals == 0))

    def test_multiple_features(self):
        X = np.array([[1, 2], [2, 3], [3, 4]])
        y = np.array([1, 2, 3])
        coeffs, _ = kernel_weighted_regression(X, y, "laplacian", 1.0, 100, 1e-6)
        self.assertEqual(coeffs.shape, (2,))

    def test_large_bandwidth(self):
        coeffs, _ = kernel_weighted_regression(self.X_basic, self.y_basic, "gaussian", 100.0, 100, 1e-6)
        self.assertEqual(coeffs.shape, (1,))

    def test_small_bandwidth(self):
        coeffs, _ = kernel_weighted_regression(self.X_basic, self.y_basic, "laplacian", 1e-6, 100, 1e-6)
        self.assertEqual(coeffs.shape, (1,))

    def test_convergence(self):
        coeffs1, _ = kernel_weighted_regression(self.X_basic, self.y_basic, "gaussian", 1.0, 1, 1e-6)
        coeffs2, _ = kernel_weighted_regression(self.X_basic, self.y_basic, "gaussian", 1.0, 100, 1e-6)
        self.assertTrue(np.allclose(coeffs2, coeffs2))

    def test_weight_matrix_shape(self):
        _, w = kernel_weighted_regression(self.X_basic, self.y_basic, "gaussian", 1.0, 100, 1e-6)
        self.assertEqual(w.shape, (3, 3))

    def test_weight_matrix_symmetry(self):
        _, w = kernel_weighted_regression(self.X_basic, self.y_basic, "gaussian", 1.0, 100, 1e-6)
        self.assertTrue(np.allclose(w, w.T))

    def test_output_values_stability(self):
        coeffs1, _ = kernel_weighted_regression(self.X_basic, self.y_basic, "linear", 1.0, 100, 1e-6)
        coeffs2, _ = kernel_weighted_regression(self.X_basic, self.y_basic, "linear", 1.0, 100, 1e-6)
        self.assertTrue(np.allclose(coeffs1, coeffs2))

    def test_high_dimensional_data(self):
        X = np.random.rand(10, 5)
        y = np.random.rand(10)
        coeffs, w = kernel_weighted_regression(X, y, "gaussian", 1.0, 50, 1e-6)
        self.assertEqual(coeffs.shape, (5,))
        self.assertEqual(w.shape, (10, 10))

    def test_large_dataset(self):
        np.random.seed(0)
        X = np.random.rand(50, 3)
        y = np.random.rand(50)
        coeffs, _ = kernel_weighted_regression(X, y, "laplacian", 0.8, 30, 1e-4)
        self.assertEqual(len(coeffs), 3)

    def test_all_same_input(self):
        X = np.ones((5, 2))
        y = np.ones(5)
        coeffs, _ = kernel_weighted_regression(X, y, "gaussian", 1.0, 100, 1e-6)
        self.assertTrue(np.allclose(coeffs, coeffs[0]))

    def test_weight_matrix_nonzero(self):
        _, w = kernel_weighted_regression(self.X_basic, self.y_basic, "linear", 0.1, 50, 1e-6)
        self.assertFalse(np.all(w == 0))

    def test_iterative_stops(self):
        coeffs, _ = kernel_weighted_regression(self.X_basic, self.y_basic, "gaussian", 0.1, 1, 1e-6)
        self.assertEqual(coeffs.shape, (1,))

    def test_extreme_y(self):
        y = np.array([1e10, -1e10, 1e10])
        coeffs, _ = kernel_weighted_regression(self.X_basic, y, "laplacian", 1.0, 100, 1e-6)
        self.assertTrue(np.isfinite(coeffs).all())

    def test_weight_matrix_structure(self):
        _, w = kernel_weighted_regression(self.X_basic, self.y_basic, "gaussian", 1.0, 10, 1e-4)
        self.assertTrue(np.all(w >= 0) and np.all(w <= 1))

    def test_return_type(self):
        result = kernel_weighted_regression(self.X_basic, self.y_basic, "linear", 1.0, 10, 1e-6)
        self.assertIsInstance(result, tuple)
        self.assertIsInstance(result[0], np.ndarray)
        self.assertIsInstance(result[1], np.ndarray)

    def test_stress_random(self):
        np.random.seed(42)
        X = np.random.rand(20, 4)
        y = np.random.rand(20)
        coeffs, _ = kernel_weighted_regression(X, y, "laplacian", 0.5, 40, 1e-6)
        self.assertEqual(coeffs.shape[0], 4)

    def test_consistency_multiple_runs(self):
        coeffs1, _ = kernel_weighted_regression(self.X_basic, self.y_basic, "linear", 0.5, 30, 1e-6)
        coeffs2, _ = kernel_weighted_regression(self.X_basic, self.y_basic, "linear", 0.5, 30, 1e-6)
        self.assertTrue(np.allclose(coeffs1, coeffs2))
