
import numpy as np
from sklearn.cluster import KMeans
from typing import Dict, List, Tuple, Optional


class TreeNode:
    """Represents a node in the decision tree."""

    def __init__(self, depth: int):
        self.depth = depth
        self.split_feature = -1  # -1 for leaf nodes
        self.split_value = None  # None for leaf nodes
        self.cluster_distribution = {}
        self.left_child = None
        self.right_child = None
        self.sample_indices = []


def explainable_kmeans(data: np.ndarray, k: int, max_depth: int) -> dict:
    """
    Performs k-means clustering with explainable decision tree refinement.
    """
    # Input validation
    _validate_inputs(data, k, max_depth)

    # Handle edge case: max_depth = 0
    if max_depth == 0:
        kmeans_result = _perform_kmeans(data, k)
        return {
            "refined_labels": kmeans_result['labels'].tolist(),
            "tree_structure": [],
            "initial_centroids": kmeans_result['centroids'].tolist()
        }

    # Perform initial k-means clustering
    kmeans_result = _perform_kmeans(data, k)
    initial_labels = kmeans_result['labels']
    initial_centroids = kmeans_result['centroids']

    # Build decision tree for explainability
    root_node = _build_decision_tree(data, initial_labels, max_depth)

    # Extract refined labels from tree
    refined_labels = _extract_refined_labels(data, root_node, len(data))

    # Convert tree to required format
    tree_structure = _convert_tree_to_structure(root_node)

    return {
        "refined_labels": refined_labels.tolist(),
        "tree_structure": tree_structure,
        "initial_centroids": initial_centroids.tolist()
    }


def _validate_inputs(data: np.ndarray, k: int, max_depth: int) -> None:
    """Validates all input parameters according to constraints."""

    # Check data type and format
    if not isinstance(data, np.ndarray):
        raise ValueError("Data must be a numpy array")

    if data.size == 0:
        raise ValueError("Input data is empty")

    if data.ndim != 2:
        raise ValueError("Data must be 2-dimensional")

    # Check for NaNs
    if np.isnan(data).any():
        raise ValueError("Input contains NaNs")

    # Validate k parameter
    if not isinstance(k, int) or k < 1 or k > 15:
        raise ValueError("k must be an integer between 1 and 15")

    # Check unique samples constraint
    unique_samples = len(np.unique(data, axis=0))
    if k > unique_samples:
        raise ValueError("k exceeds number of unique samples")

    # Check minimum samples constraint
    if len(data) < k:
        raise ValueError("Not enough samples for k clusters")

    # Validate max_depth
    if not isinstance(max_depth, int) or max_depth < 0:
        raise ValueError("max_depth must be a non-negative integer")


def _perform_kmeans(data: np.ndarray, k: int) -> Dict:
    """Performs k-means clustering with float64 precision."""

    # Ensure float64 precision
    data_float64 = data.astype(np.float64)

    # Handle single cluster case
    if k == 1:
        labels = np.zeros(len(data), dtype=int)
        centroids = np.mean(data_float64, axis=0, keepdims=True)
        return {'labels': labels, 'centroids': centroids}

    # Perform k-means clustering
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = kmeans.fit_predict(data_float64)
    centroids = kmeans.cluster_centers_

    return {'labels': labels, 'centroids': centroids}


def _build_decision_tree(data: np.ndarray, labels: np.ndarray, max_depth: int) -> TreeNode:
    """Builds a greedy decision tree for cluster refinement."""

    root_indices = np.arange(len(data))
    root_node = TreeNode(depth=0)
    root_node.sample_indices = root_indices
    root_node.cluster_distribution = _calculate_cluster_distribution(labels[root_indices])

    # Build tree recursively
    _build_tree_recursive(root_node, data, labels, max_depth)

    return root_node


def _build_tree_recursive(node: TreeNode, data: np.ndarray, labels: np.ndarray, max_depth: int) -> None:
    """Recursively builds the decision tree using greedy axis-aligned splits."""

    # Stop if max depth reached
    if node.depth >= max_depth:
        return

    # Stop if node is pure or has insufficient samples
    if len(set(labels[node.sample_indices])) <= 1 or len(node.sample_indices) <= 1:
        return

    # Find best split
    best_split = _find_best_split(data, labels, node.sample_indices)

    if best_split is None:
        return  # No valid split found

    feature_idx, split_value, left_indices, right_indices = best_split

    # Set node split information
    node.split_feature = feature_idx
    node.split_value = float(split_value)

    # Create child nodes
    node.left_child = TreeNode(depth=node.depth + 1)
    node.left_child.sample_indices = left_indices
    node.left_child.cluster_distribution = _calculate_cluster_distribution(labels[left_indices])

    node.right_child = TreeNode(depth=node.depth + 1)
    node.right_child.sample_indices = right_indices
    node.right_child.cluster_distribution = _calculate_cluster_distribution(labels[right_indices])

    # Recursively build subtrees
    _build_tree_recursive(node.left_child, data, labels, max_depth)
    _build_tree_recursive(node.right_child, data, labels, max_depth)


def _find_best_split(data: np.ndarray, labels: np.ndarray, sample_indices: np.ndarray) -> Optional[Tuple]:
    """Finds the best axis-aligned split for the given samples."""

    node_data = data[sample_indices]
    node_labels = labels[sample_indices]

    # For high dimensional data, consider only top 10 most variant features
    features_to_consider = _select_features_to_consider(node_data)

    best_split = None
    best_score = float('inf')

    for feature_idx in features_to_consider:
        feature_values = node_data[:, feature_idx]

        # Check if feature has at least 2 unique values
        unique_values = np.unique(feature_values)
        if len(unique_values) < 2:
            continue

        # Try splits at midpoints between consecutive unique values
        for i in range(len(unique_values) - 1):
            split_value = (unique_values[i] + unique_values[i + 1]) / 2.0

            # Create split
            left_mask = feature_values <= split_value
            right_mask = ~left_mask

            # Skip if either side is empty
            if not np.any(left_mask) or not np.any(right_mask):
                continue

            # Calculate split quality using weighted impurity
            score = _calculate_split_score(node_labels, left_mask, right_mask)

            if score < best_score:
                best_score = score
                left_indices = sample_indices[left_mask]
                right_indices = sample_indices[right_mask]
                best_split = (feature_idx, split_value, left_indices, right_indices)

    return best_split


def _select_features_to_consider(data: np.ndarray) -> List[int]:
    """Selects features to consider for splitting, limiting to top 10 for high-dimensional data."""

    n_features = data.shape[1]

    # For high dimensional data (>=100 features), select top 10 most variant
    if n_features >= 100:
        variances = np.var(data, axis=0)
        top_features = np.argsort(variances)[-10:]
        return top_features.tolist()

    return list(range(n_features))


def _calculate_split_score(labels: np.ndarray, left_mask: np.ndarray, right_mask: np.ndarray) -> float:
    """Calculates weighted impurity score for a split using float64 precision."""

    total_samples = len(labels)
    left_samples = np.sum(left_mask)
    right_samples = np.sum(right_mask)

    # Calculate weighted gini impurity
    left_weight = left_samples / total_samples
    right_weight = right_samples / total_samples

    left_gini = _calculate_gini_impurity(labels[left_mask])
    right_gini = _calculate_gini_impurity(labels[right_mask])

    # Return weighted impurity as float64
    weighted_impurity = np.float64(left_weight * left_gini + right_weight * right_gini)
    return weighted_impurity


def _calculate_gini_impurity(labels: np.ndarray) -> float:
    """Calculates Gini impurity for a set of labels with float64 precision."""

    if len(labels) == 0:
        return 0.0

    # Calculate cluster distribution
    cluster_dist = _calculate_cluster_distribution(labels)
    total_samples = len(labels)

    # Calculate Gini impurity
    gini = np.float64(1.0)
    for count in cluster_dist.values():
        probability = np.float64(count) / np.float64(total_samples)
        gini -= probability * probability

    return gini


def _calculate_cluster_distribution(labels: np.ndarray) -> Dict[int, int]:
    """Calculates cluster distribution without using collections.Counter."""

    distribution = {}
    for label in labels:
        label_int = int(label)
        if label_int in distribution:
            distribution[label_int] += 1
        else:
            distribution[label_int] = 1

    return distribution


def _extract_refined_labels(data: np.ndarray, root_node: TreeNode, n_samples: int) -> np.ndarray:
    """Extracts refined cluster labels from the decision tree."""

    refined_labels = np.zeros(n_samples, dtype=int)

    # Assign cluster labels based on tree structure
    _assign_labels_recursive(root_node, refined_labels, 0)

    return refined_labels


def _assign_labels_recursive(node: TreeNode, labels: np.ndarray, cluster_id: int) -> int:
    """Recursively assigns cluster labels to samples based on tree structure."""

    if node.split_feature == -1:  # Leaf node
        # Assign current cluster_id to all samples in this leaf
        for idx in node.sample_indices:
            labels[idx] = cluster_id
        return cluster_id + 1
    else:
        # Process left subtree first, then right subtree
        cluster_id = _assign_labels_recursive(node.left_child, labels, cluster_id)
        cluster_id = _assign_labels_recursive(node.right_child, labels, cluster_id)
        return cluster_id


def _convert_tree_to_structure(root_node: TreeNode) -> List[Dict]:
    """Converts tree to required output format in depth-first order."""

    if root_node is None:
        return []

    structure = []
    _traverse_tree_depth_first(root_node, structure)
    return structure


def _traverse_tree_depth_first(node: TreeNode, structure: List[Dict]) -> None:
    """Traverses tree in depth-first order and builds structure list."""

    # Add current node to structure
    node_dict = {
        "depth": node.depth,
        "split_feature": node.split_feature,
        "split_value": node.split_value,
        "cluster_distribution": node.cluster_distribution
    }
    structure.append(node_dict)

    # Traverse children in depth-first order
    if node.left_child is not None:
        _traverse_tree_depth_first(node.left_child, structure)

    if node.right_child is not None:
        _traverse_tree_depth_first(node.right_child, structure)


