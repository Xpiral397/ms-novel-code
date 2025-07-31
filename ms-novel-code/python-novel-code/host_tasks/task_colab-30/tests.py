# tests
"""Unittest cases for social network graph analysis utilities."""

import unittest
from main import (
    validate_graph,
    compute_influencers,
    detect_communities,
    generate_recommendations,
    analyze_network,
)


class TestSocialNetworkAnalysis(unittest.TestCase):
    """Unit tests for social network analysis functions."""

    def test_valid_graph_passes(self):
        """Test that a valid graph passes validation."""
        graph = {"A": {"B": 10}, "B": {"C": 5}}
        validate_graph(graph)  # Should not raise

    def test_invalid_user_id(self):
        """Test that invalid user IDs raise ValueError."""
        with self.assertRaises(ValueError):
            validate_graph({"AA": {"B": 10}})

    def test_invalid_neighbor_id(self):
        """Test that invalid neighbor IDs raise ValueError."""
        with self.assertRaises(ValueError):
            validate_graph({"A": {"1": 5}})

    def test_invalid_interaction_count(self):
        """Test that out-of-range interaction count raises ValueError."""
        with self.assertRaises(ValueError):
            validate_graph({"A": {"B": 0}})

    def test_self_loop_detected(self):
        """Test that self-loop edges raise ValueError."""
        with self.assertRaises(ValueError):
            validate_graph({"A": {"A": 10}})

    def test_neighbor_overwrite_not_detected(self):
        """Test that overwriting neighbors does not cause validation error."""
        graph = {"A": {"B": 10}}  # Only one B, so no error expected
        validate_graph(graph)  # Should pass

    def test_compute_influencers_order(self):
        """Test that influencers are correctly sorted by score."""
        graph = {"A": {"B": 2}, "B": {"C": 3}, "C": {"A": 1}}
        result = compute_influencers(graph)
        self.assertEqual(result, ["B", "A", "C"])

    def test_compute_influencers_disconnected(self):
        """Test that disconnected users are included with zero score."""
        graph = {"A": {"B": 5}, "C": {}, "D": {}}
        result = compute_influencers(graph)
        self.assertIn("C", result)
        self.assertIn("D", result)

    def test_detect_single_community(self):
        """Test that a single connected component forms one community."""
        graph = {"A": {"B": 1}, "B": {"A": 1}}
        result = detect_communities(graph)
        self.assertEqual(result, [["A", "B"]])

    def test_detect_two_communities(self):
        """Test that two disjoint components form two communities."""
        graph = {
            "A": {"B": 1},
            "B": {"A": 1},
            "C": {"D": 1},
            "D": {"C": 1},
        }
        result = detect_communities(graph)
        self.assertEqual(result, [["A", "B"], ["C", "D"]])

    def test_generate_recommendations_simple(self):
        """Test basic recommendation generation."""
        graph = {"A": {"B": 1}, "B": {"C": 1}, "C": {"D": 1}, "D": {}}
        result = generate_recommendations(graph, "A")
        self.assertIn("C", result)

    def test_generate_recommendations_none(self):
        """Test that no recommendations are made when none exist."""
        graph = {"A": {"B": 1}, "B": {"A": 1}}
        result = generate_recommendations(graph, "A")
        self.assertEqual(result, [])

    def test_generate_recommendations_jaccard_tie_break(self):
        """Test recommendation sorting when Jaccard scores tie."""
        graph = {
            "A": {"B": 1, "C": 1},
            "D": {"B": 1, "C": 1},
            "E": {"C": 1, "F": 1},
        }
        result = generate_recommendations(graph, "A")
        self.assertEqual(result, ["D", "E", "F"])

    def test_analyze_network_empty(self):
        """Test network analysis with empty input."""
        graph = {}
        result = analyze_network(graph)
        self.assertEqual(
            result,
            {
                "influencers": [],
                "communities": [],
                "recommendations": {},
            },
        )

    def test_analyze_network_small_graph(self):
        """Test network analysis on a small graph."""
        graph = {"A": {"B": 1}, "B": {"C": 2}, "C": {"A": 3}}
        result = analyze_network(graph)
        self.assertIn("A", result["influencers"])
        self.assertTrue(any("A" in c for c in result["communities"]))
        self.assertIn("B", result["recommendations"])

    def test_influencers_sorted_alphabetically_on_tie(self):
        """Test that influencers are sorted alphabetically on score tie."""
        graph = {"A": {"B": 5}, "C": {"D": 5}}
        result = compute_influencers(graph)
        self.assertEqual(result, ["A", "C", "B", "D"])

    def test_detect_communities_stable_output(self):
        """Test that community detection produces consistent output."""
        graph = {
            "A": {"B": 1},
            "B": {"A": 1, "C": 1},
            "C": {"B": 1},
            "D": {"E": 1},
            "E": {"D": 1},
        }
        result = detect_communities(graph)
        expected = [["A", "B", "C"], ["D", "E"]]
        self.assertEqual(result, expected)

    def test_generate_recommendations_jaccard_zero_division(self):
        """Test Jaccard similarity when both sets are empty."""
        graph = {"A": {}, "B": {}}
        result = generate_recommendations(graph, "A")
        self.assertEqual(result, ["B"])

    def test_validate_graph_non_dict_neighbors(self):
        """Test that non-dict neighbors raise ValueError."""
        with self.assertRaises(ValueError):
            validate_graph({"A": [("B", 1)]})

    def test_analyze_network_large_complete(self):
        """Test network analysis on a complete graph of 5 users."""
        graph = {
            chr(i): {chr(j): 1 for j in range(65, 70) if i != j}
            for i in range(65, 70)
        }
        result = analyze_network(graph)
        self.assertEqual(len(result["influencers"]), 5)
        self.assertEqual(len(result["communities"]), 1)
        self.assertTrue(
            all(len(v) <= 4 for v in result["recommendations"].values())
        )

    def test_recommendations_excludes_existing_neighbors(self):
        """Test that recommendations exclude already connected users."""
        graph = {
            "A": {"B": 1, "C": 1},
            "B": {"C": 1},
            "C": {"D": 1},
            "D": {},
        }
        recs = generate_recommendations(graph, "A")
        self.assertNotIn("B", recs)
        self.assertNotIn("C", recs)
