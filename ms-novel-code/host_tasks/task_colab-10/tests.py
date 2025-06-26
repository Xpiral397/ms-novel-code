# tests
import unittest
import numpy as np
from main import explainable_kmeans

class TestExplainableKMeans(unittest.TestCase):

    def test_simple_two_clusters(self):
        data = np.array([[1.0, 2.0], [1.1, 1.9], [9.0, 8.8], [9.1, 9.0]])
        result = explainable_kmeans(data, k=2, max_depth=2)
        self.assertEqual(len(result["refined_labels"]), 4)
        self.assertEqual(len(result["initial_centroids"]), 2)
        self.assertTrue(all(isinstance(node, dict) for node in result["tree_structure"]))

    def test_single_cluster_no_split(self):
        data = np.array([[0, 0], [0, 1], [1, 0], [1, 1]])
        result = explainable_kmeans(data, k=1, max_depth=1)
        self.assertEqual(result["tree_structure"], [
            {
        "depth": 0,
        "split_feature": -1,
        "split_value": None,
        "cluster_distribution": {0: 4}
            }
        ])
        self.assertEqual(result["refined_labels"], [0, 0, 0, 0])

    def test_empty_data(self):
        with self.assertRaises(ValueError) as ctx:
            explainable_kmeans(np.array([]).reshape(0, 2), k=1, max_depth=1)
        self.assertIn("Input data is empty", str(ctx.exception))

    def test_all_identical_points(self):
        data = np.array([[1.0, 1.0]] * 5)
        k = 1
        max_depth = 2
        result = explainable_kmeans(data, k, max_depth)

        expected_structure = [
            {
                "depth": 0,
                "split_feature": -1,
                "split_value": None,
                "cluster_distribution": {0: 5}
            }
        ]

        self.assertEqual(result["tree_structure"], expected_structure)

    def test_k_greater_than_unique(self):
        data = np.array([[1, 2], [1, 2], [1, 2]])
        with self.assertRaises(ValueError) as ctx:
            explainable_kmeans(data, k=5, max_depth=2)
        self.assertIn("k exceeds number of unique samples", str(ctx.exception))

    def test_max_depth_zero(self):
        data = np.random.rand(10, 2)
        result = explainable_kmeans(data, k=3, max_depth=0)
        self.assertEqual(result["tree_structure"], [])
        self.assertEqual(len(result["initial_centroids"]), 3)

    def test_single_feature(self):
        data = np.array([[1], [2], [9], [10]])
        result = explainable_kmeans(data, k=2, max_depth=2)
        self.assertEqual(len(result["refined_labels"]), 4)
        self.assertTrue(isinstance(result["tree_structure"], list))

    def test_nan_input(self):
        data = np.array([[1.0, 2.0], [np.nan, 3.0]])
        with self.assertRaises(ValueError) as ctx:
            explainable_kmeans(data, k=2, max_depth=1)
        self.assertIn("Input contains NaNs", str(ctx.exception))

    def test_high_dimensional_input(self):
        data = np.random.rand(50, 150)
        result = explainable_kmeans(data, k=4, max_depth=3)
        self.assertEqual(len(result["initial_centroids"]), 4)

    def test_k_equals_1(self):
        data = np.random.rand(20, 5)
        result = explainable_kmeans(data, k=1, max_depth=2)
        self.assertEqual(len(set(result["refined_labels"])), 1)

    def test_depth_limit_enforced(self):
        data = np.random.rand(100, 2)
        result = explainable_kmeans(data, k=3, max_depth=1)
        for node in result["tree_structure"]:
            self.assertLessEqual(node["depth"], 1)

    def test_axis_aligned_only(self):
        data = np.random.rand(10, 3)
        result = explainable_kmeans(data, k=2, max_depth=2)
        for node in result["tree_structure"]:
            self.assertTrue(-1 <= node["split_feature"] < 3 or node["split_feature"] == -1)

    def test_feature_with_one_unique_value(self):
        data = np.array([[1, 2], [1, 3], [1, 4]])
        result = explainable_kmeans(data, k=1, max_depth=2)
        self.assertTrue(isinstance(result["refined_labels"], list))

    def test_correct_centroid_precision(self):
        data = np.random.rand(5, 2)
        result = explainable_kmeans(data, k=2, max_depth=1)
        for centroid in result["initial_centroids"]:
            self.assertTrue(all(isinstance(v, float) for v in centroid))

    def test_non_integer_k(self):
        with self.assertRaises(ValueError) as ctx:
            explainable_kmeans(np.random.rand(10, 2), k="3", max_depth=2)
        self.assertIn("k must be an integer", str(ctx.exception))

    def test_non_integer_max_depth(self):
        with self.assertRaises(ValueError) as ctx:
            explainable_kmeans(np.random.rand(10, 2), k=3, max_depth="2")
        self.assertIn("max_depth must be a non-negative integer", str(ctx.exception))

    def test_invalid_data_type(self):
        with self.assertRaises(ValueError) as ctx:
            explainable_kmeans("not an array", k=3, max_depth=2)
        self.assertIn("Data must be a numpy array", str(ctx.exception))

    def test_tree_structure_content(self):
        data = np.random.rand(10, 2)
        result = explainable_kmeans(data, k=2, max_depth=2)
        for node in result["tree_structure"]:
            self.assertIn("depth", node)
            self.assertIn("split_feature", node)
            self.assertIn("split_value", node)
            self.assertIn("cluster_distribution", node)

    def test_cluster_distribution_is_dict(self):
        data = np.random.rand(20, 3)
        result = explainable_kmeans(data, k=3, max_depth=2)
        for node in result["tree_structure"]:
            self.assertTrue(isinstance(node["cluster_distribution"], dict))

    def test_node_leaf_condition(self):
        data = np.random.rand(10, 2)
        result = explainable_kmeans(data, k=2, max_depth=1)
        for node in result["tree_structure"]:
            if node["split_feature"] == -1:
                self.assertIsNone(node["split_value"])

    def test_cluster_label_range(self):
        data = np.random.rand(12, 2)
        result = explainable_kmeans(data, k=3, max_depth=2)
        self.assertTrue(set(result["refined_labels"]).issubset(set(range(3))))

    def test_no_split_when_all_same_cluster(self):
        data = np.random.rand(10, 2)
        result = explainable_kmeans(data, k=1, max_depth=3)
        self.assertEqual(len(set(result["refined_labels"])), 1)

    def test_random_large_sample(self):
        data = np.random.rand(1000, 2)
        result = explainable_kmeans(data, k=5, max_depth=3)
        self.assertEqual(len(result["refined_labels"]), 1000)

    def test_only_top_10_features_considered(self):
        data = np.random.rand(200, 100)
        result = explainable_kmeans(data, k=4, max_depth=2)
        used_features = {node["split_feature"] for node in result["tree_structure"] if node["split_feature"] != -1}
        self.assertLessEqual(len(used_features), 10)

    def test_refined_label_length_matches_data(self):
        data = np.random.rand(75, 5)
        result = explainable_kmeans(data, k=4, max_depth=2)
        self.assertEqual(len(result["refined_labels"]), len(data))

    def test_refined_label_type(self):
        data = np.random.rand(20, 2)
        result = explainable_kmeans(data, k=3, max_depth=1)
        self.assertTrue(all(isinstance(lbl, int) for lbl in result["refined_labels"]))

    def test_node_ordering_depth_first(self):

        data = np.array([
            [1.0, 2.0],
            [1.1, 2.1],
            [9.0, 8.9],
            [9.1, 9.0],
            [5.0, 5.0],
        ])
        k = 2
        max_depth = 2

        result = explainable_kmeans(data, k, max_depth)
        tree = result["tree_structure"]

        # Validate preorder depth-first traversal (parent before children)
        stack = []
        last_depth = -1
        for node in tree:
            depth = node["depth"]
            # Depth can increase by 1 (child), or decrease (backtracking), or stay same (sibling)
            # Ensure no jumps > 1 in depth without a proper return
            if depth > last_depth + 1:
                self.fail(f"Invalid depth transition from {last_depth} to {depth}")
            last_depth = depth

        # Optional: ensure root node exists
        self.assertEqual(tree[0]["depth"], 0)

    def test_split_feature_valid_range(self):
        data = np.random.rand(20, 4)
        result = explainable_kmeans(data, k=3, max_depth=2)
        for node in result["tree_structure"]:
            if node["split_feature"] != -1:
                self.assertTrue(0 <= node["split_feature"] < 4)

    def test_all_clusters_present_in_distribution(self):
        data = np.random.rand(30, 2)
        result = explainable_kmeans(data, k=3, max_depth=2)
        for node in result["tree_structure"]:
            total = sum(node["cluster_distribution"].values())
            self.assertTrue(total > 0)

    def test_precision_stability(self):
        data = np.random.rand(100, 2).astype(np.float64)
        result = explainable_kmeans(data, k=5, max_depth=2)
        for node in result["tree_structure"]:
            self.assertTrue(isinstance(node["split_value"], (float, type(None))))

    def test_not_enough_samples_for_k(self):
        data = np.random.rand(2, 2)
        with self.assertRaises(ValueError) as ctx:
            explainable_kmeans(data, k=5, max_depth=1)
        self.assertIn("k exceeds number of unique samples", str(ctx.exception))

if __name__ == "__main__":
    unittest.main(argv=[''], exit=False, verbosity= 2)
