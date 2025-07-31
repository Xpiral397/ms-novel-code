
"""This module performs kernel-based weighted regression using NumPy only."""

import numpy as np


def kernel_weighted_regression(
    X, y, kernel, bandwidth, max_iter, tolerance
):
    """
    Perform kernel-based weighted regression.

    Args:
        X (np.ndarray): 2D input array of shape (n_samples, n_features)
        y (np.ndarray): 1D target array of shape (n_samples,)
        kernel (str): One of 'gaussian', 'laplacian', or 'linear'
        bandwidth (float): Positive kernel bandwidth
        max_iter (int): Maximum number of iterations
        tolerance (float): Non-negative L2 threshold for convergence

    Returns:
        tuple[np.ndarray, np.ndarray]:
            - Final coefficients (rounded to 4 decimals)
            - Final symmetric weight matrix
    """
    assert X.ndim == 2, "x must be a 2D array"
    assert y.ndim == 1, "y must be a 1D array"

    if X.size == 0 or X.shape[0] == 0 or X.shape[1] == 0:
        raise ValueError("X must not be empty")
    if np.any(np.isnan(X)):
        raise ValueError("X must not contain NaN")
    if np.any(np.isnan(y)):
        raise ValueError("y must not contain NaN")
    if kernel not in ("gaussian", "laplacian", "linear"):
        raise ValueError("Unsupported kernel type")
    if bandwidth <= 0:
        raise ValueError("Bandwidth must be positive")
    if max_iter <= 0:
        raise ValueError("max_iter must be a positive integer")
    if tolerance < 0:
        raise ValueError("tolerance must be non negative")
    if X.shape[0] != y.shape[0]:
        raise ValueError("X and y must have the same number of rows")

    n_features = X.shape[1]
    initial_coeffs = np.zeros(n_features)

    coeffs, weight_matrix = _iterative_update(
        X, y, initial_coeffs, kernel, bandwidth, max_iter, tolerance, 0
    )

    if not np.allclose(weight_matrix, weight_matrix.T):
        raise ValueError("Weight matrix must be symmetric")

    coeffs = np.round(coeffs, 4)
    return coeffs, weight_matrix


def _iterative_update(
    X, y, coeffs, kernel, bandwidth, max_iter, tolerance, step
):
    if step >= max_iter:
        w = _compute_weight_matrix(X, kernel, bandwidth)
        return coeffs, w

    w = _compute_weight_matrix(X, kernel, bandwidth)
    new_coeffs = _compute_weighted_coefficients(X, y, w)

    if np.linalg.norm(new_coeffs - coeffs) < tolerance:
        return new_coeffs, w

    return _iterative_update(
        X, y, new_coeffs, kernel, bandwidth, max_iter, tolerance, step + 1
    )


def _compute_weight_matrix(X, kernel, h):
    diffs = X[:, None, :] - X[None, :, :]
    dist = np.linalg.norm(diffs, axis=2)

    if kernel == "gaussian":
        w = np.exp(-dist**2 / (2 * h**2))
    elif kernel == "laplacian":
        w = np.exp(-dist / h)
    else:  # linear
        w = np.maximum(0, 1 - dist / h)

    return (w + w.T) / 2


def _compute_weighted_coefficients(X, y, w):
    xtw = X.T @ w
    xtwx = xtw @ X
    xtwy = xtw @ y

    reg = 1e-10 * np.eye(X.shape[1])
    inv = np.linalg.inv(xtwx + reg)

    coeffs = inv @ xtwy
    return coeffs
