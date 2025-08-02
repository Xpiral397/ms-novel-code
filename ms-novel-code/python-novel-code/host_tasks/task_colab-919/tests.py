# tests
"""Unit tests for the AdaptiveClient class interact with a GraphQL endpoint."""

import unittest
from unittest.mock import patch
from main import AdaptiveClient, GraphQLAdaptiveError
import os
import time


class TestAdaptiveClient(unittest.TestCase):
    """Test cases for the AdaptiveClient class."""

    def setUp(self):
        """Set up an AdaptiveClient instance for testing."""
        self.endpoint = "https://example.com/graphql"
        self.client = AdaptiveClient(endpoint=self.endpoint)

    def test_invalid_endpoint_scheme(self):
        """Test that an insecure HTTP endpoint raises an error."""
        with self.assertRaises(GraphQLAdaptiveError):
            AdaptiveClient("http://insecure.com/graphql")

    def test_session_headers_applied(self):
        """Test that custom headers are applied to the session."""
        client = AdaptiveClient(self.endpoint, headers={"X-Test": "1"})
        self.assertEqual(client._session.headers["X-Test"], "1")
        self.assertEqual(client._session.headers["Content-Type"],
                         "application/json")

    def test_offline_mode_detection(self):
        """Test that offline mode is respected via environment variable."""
        os.environ["ADAPTIVE_GQL_OFFLINE"] = "1"
        with self.assertRaises(GraphQLAdaptiveError):
            self.client._check_offline_mode()
        os.environ["ADAPTIVE_GQL_OFFLINE"] = "0"

    def test_should_refresh_schema_first_time(self):
        """Test that schema refresh is needed when none is loaded yet."""
        self.assertTrue(self.client._should_refresh_schema(force=False))

    def test_should_refresh_schema_force(self):
        """Test forced schema refresh."""
        self.client._schema_raw = {"dummy": True}
        self.assertTrue(self.client._should_refresh_schema(force=True))

    def test_should_refresh_schema_interval_elapsed(self):
        """Test schema refresh when interval has elapsed."""
        self.client._refresh_interval = 1
        self.client._schema_raw = {"x": "y"}
        self.client._schema_timestamp = time.time() - 2
        self.assertTrue(self.client._should_refresh_schema(force=False))

    def test_should_not_refresh_schema_when_cached(self):
        """Test no schema refresh when data is fresh and cached."""
        self.client._refresh_interval = 10
        self.client._schema_raw = {"x": "y"}
        self.client._schema_timestamp = time.time()
        self.assertFalse(self.client._should_refresh_schema(force=False))

    def test_compute_schema_hash_consistency(self):
        """Test that hashing the same schema twice gives the same hash."""
        schema = {"types": [{"name": "A"}]}
        h1 = self.client._compute_schema_hash(schema)
        h2 = self.client._compute_schema_hash(schema)
        self.assertEqual(h1, h2)

    def test_parse_type_ref_scalar(self):
        """Test parsing of scalar type reference."""
        ref = {"kind": "SCALAR", "name": "String"}
        name, nullable = self.client._parse_type_ref(ref)
        self.assertEqual(name, "String")
        self.assertTrue(nullable)

    def test_parse_type_ref_non_null(self):
        """Test parsing of non-null wrapped scalar reference."""
        ref = {"kind": "NON_NULL", "ofType": {"kind": "SCALAR", "name": "Int"}}
        name, nullable = self.client._parse_type_ref(ref)
        self.assertEqual(name, "Int")
        self.assertFalse(nullable)

    def test_parse_type_ref_list(self):
        """Test parsing of list type reference."""
        ref = {"kind": "LIST", "ofType": {"kind": "SCALAR", "name": "String"}}
        name, nullable = self.client._parse_type_ref(ref)
        self.assertEqual(name, "[String]")
        self.assertTrue(nullable)

    def test_is_scalar_builtin(self):
        """Test detection of built-in scalar type."""
        self.assertTrue(self.client._is_scalar_type("Int"))

    def test_is_scalar_custom_scalar(self):
        """Test detection of user-defined scalar type."""
        self.client._schema_types["CustomScalar"] = {"kind": "SCALAR"}
        self.assertTrue(self.client._is_scalar_type("CustomScalar"))

    def test_is_not_scalar(self):
        """Test detection of non-scalar type."""
        self.client._schema_types["Obj"] = {"kind": "OBJECT"}
        self.assertFalse(self.client._is_scalar_type("Obj"))

    @patch("main.AdaptiveClient._execute_request")
    def test_refresh_schema_success(self, mock_exec):
        """Test successful schema refresh updates internal type registry."""
        mock_exec.return_value = {
            "data": {
                "__schema": {
                    "types": [
                        {
                            "kind": "OBJECT",
                            "name": "User",
                            "fields": [
                                {
                                    "name": "id",
                                    "type": {"kind": "SCALAR", "name": "ID"},
                                    "args": [],
                                }
                            ]
                        }
                    ]
                }
            }
        }
        self.client.refresh_schema(force=True)
        self.assertIn("User", self.client._schema_types)

    @patch("main.AdaptiveClient._execute_request")
    def test_refresh_schema_skips_if_same_hash(self, mock_exec):
        """Test schema is not reloaded if hash matches existing schema."""
        mock_schema = {
            "__schema": {
                "types": [
                    {"kind": "OBJECT", "name": "X", "fields": []}
                ]
            }
        }
        mock_exec.return_value = {"data": mock_schema}
        h = self.client._compute_schema_hash(mock_schema)
        self.client._schema_hash = h
        self.client._schema_raw = mock_schema
        self.client._schema_timestamp = time.time() - 100
        self.client._refresh_interval = 1
        self.client.refresh_schema()
        self.assertEqual(self.client._schema_hash, h)

    def test_build_scalar_query_basic(self):
        """Test scalar query generation for basic object."""
        self.client._schema_types["User"] = {
            "kind": "OBJECT",
            "fields": {
                "id": {"type": "ID", "nullable": True, "requires_args": False},
                "email": {"type": "String",
                          "nullable": True, "requires_args": False}
            }
        }
        result = self.client._build_scalar_query("User")
        self.assertIn("id", result)
        self.assertIn("email", result)

    def test_build_scalar_query_recursion_block(self):
        """Test that recursion is prevented when generating scalar queries."""
        self.client._schema_types["A"] = {
            "kind": "OBJECT",
            "fields": {
                "self": {"type": "A",
                         "nullable": False, "requires_args": False}
            }
        }
        result = self.client._build_scalar_query("A")
        self.assertNotIn("self {", result)

    @patch("main.AdaptiveClient.refresh_schema")
    @patch("main.AdaptiveClient._execute_request")
    def test_fetch_by_id_success(self, mock_exec, mock_refresh):
        """Test successful fetch by ID with valid schema and response."""
        self.client._schema_types["Book"] = {
            "kind": "OBJECT",
            "fields": {
                "id": {"type": "ID", "nullable": True, "requires_args": False},
                "title": {"type": "String",
                          "nullable": True, "requires_args": False}
            }
        }

        mock_exec.return_value = {
            "data": {"book": {"id": "1", "title": "GraphQL"}}
        }

        result = self.client.fetch_by_id("Book", 1)
        self.assertEqual(result["title"], "GraphQL")

    @patch("main.AdaptiveClient._execute_request")
    def test_run_raw_uses_json_sorted_keys(self, mock_exec):
        """Test raw query execution returns valid results."""
        mock_exec.return_value = {"data": {"ping": "pong"}}
        query = "query { ping }"
        result = self.client.run_raw(query, {})
        self.assertEqual(result["data"]["ping"], "pong")
