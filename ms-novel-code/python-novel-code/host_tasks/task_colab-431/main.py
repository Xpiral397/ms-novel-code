
"""BFS for a graph represented by an adjacency matrix."""

from collections import deque
from typing import List


def bfs_traversal(matrix: List[List[int]], start_node: int) -> List[int]:
    """
    Perform a BFS on a graph represented by an adjacency matrix.

    Args:
        matrix (List[List[int]]): A square adjacency matrix with 0/1 entries.
        start_node (int): The index of the starting node.

    Returns:
        List[int]: The BFS traversal order as a list of node indices.

    Raises:
        ValueError: If the matrix is empty, not square,
                    or contains non-binary values.
        IndexError: If the starting node index is out of bounds.
    """
    n = len(matrix)

    if n == 0:
        raise ValueError("Input matrix cannot be empty.")

    for i, row in enumerate(matrix):
        if len(row) != n:
            raise ValueError("Input matrix must be square.")
        for j, value in enumerate(row):
            if value not in (0, 1):
                raise ValueError("Matrix values must be 0 or 1.")
            if i == j and value != 0:
                raise ValueError(
                    "Matrix must not contain self-loops (matrix[i][i] == 0)."
                    )

    if not (0 <= start_node < n):
        raise IndexError("Starting node index is out of bounds.")

    visited = [False] * n
    queue = deque()
    traversal_order = []

    visited[start_node] = True
    queue.append(start_node)

    while queue:
        current_node = queue.popleft()
        traversal_order.append(current_node)

        for neighbor in range(n):
            if matrix[current_node][neighbor] == 1 and not visited[neighbor]:
                visited[neighbor] = True
                queue.append(neighbor)

    return traversal_order

