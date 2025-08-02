# tests

"""Unit tests for the bfs_traversal function."""
import unittest
from main import bfs_traversal


class TestBFSTraversal(unittest.TestCase):
    """Define unit tests for bfs_traversal function."""

    def test_single_node_graph(self):
        """Test BFS on a graph with a single node."""
        self.assertEqual(bfs_traversal([[0]], 0), [0])

    def test_disconnected_graph(self):
        """Test BFS on a disconnected graph."""
        self.assertEqual(bfs_traversal([[0, 0], [0, 0]], 0), [0])

    def test_start_node_out_of_bounds(self):
        """Test BFS with start node index out of bounds."""
        with self.assertRaises(IndexError):
            bfs_traversal([[0, 1], [1, 0]], 2)

    def test_graph_with_cycle(self):
        """Test BFS on a graph containing a cycle."""
        self.assertEqual(bfs_traversal([[0, 1], [1, 0]], 0), [0, 1])

    def test_all_nodes_reachable(self):
        """Test BFS where all nodes are reachable from start node."""
        matrix = [[0, 1, 0], [0, 0, 1], [0, 0, 0]]
        self.assertEqual(bfs_traversal(matrix, 0), [0, 1, 2])

    def test_non_square_matrix(self):
        """Test BFS on a non-square adjacency matrix."""
        with self.assertRaises(ValueError):
            bfs_traversal([[0, 1, 0], [1, 0]], 0)

    def test_invalid_matrix_values(self):
        """Test BFS with invalid matrix values."""
        with self.assertRaises(ValueError):
            bfs_traversal([[0, 2], [0, 0]], 0)

    def test_empty_matrix(self):
        """Test BFS on an empty adjacency matrix."""
        with self.assertRaises(ValueError):
            bfs_traversal([], 0)

    def test_start_node_no_edges(self):
        """Test BFS on a node with no outgoing edges."""
        matrix = [[0, 0, 0], [0, 0, 1], [0, 0, 0]]
        self.assertEqual(bfs_traversal(matrix, 0), [0])

    def test_large_connected_graph(self):
        """Test BFS on a large connected graph."""
        n = 10
        matrix = [[0] * n for _ in range(n)]
        for i in range(n - 1):
            matrix[i][i + 1] = 1
        self.assertEqual(bfs_traversal(matrix, 0), list(range(n)))

    def test_disconnected_components(self):
        """Test BFS on a graph with disconnected components."""
        matrix = [
            [0, 1, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 1],
            [0, 0, 0, 0]
        ]
        self.assertEqual(bfs_traversal(matrix, 0), [0, 1])
        self.assertEqual(bfs_traversal(matrix, 2), [2, 3])

    def test_undirected_graph(self):
        """Test BFS on an undirected graph."""
        matrix = [
            [0, 1, 1],
            [1, 0, 1],
            [1, 1, 0]
        ]
        self.assertEqual(bfs_traversal(matrix, 0), [0, 1, 2])

    def test_matrix_with_self_loops(self):
        """Test BFS on a matrix containing self-loops."""
        matrix = [
            [1, 1],
            [0, 0]
        ]
        with self.assertRaises(ValueError):
            bfs_traversal(matrix, 0)

    def test_bfs_traversal_order(self):
        """Test BFS traversal order correctness."""
        matrix = [
            [0, 1, 1, 0],
            [0, 0, 1, 1],
            [0, 0, 0, 1],
            [0, 0, 0, 0]
        ]
        self.assertEqual(bfs_traversal(matrix, 0), [0, 1, 2, 3])


if __name__ == "__main__":
    unittest.main()
