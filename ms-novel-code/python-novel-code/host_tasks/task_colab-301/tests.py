# tests

"""Unit tests for GraphQLSchemaAdapter class in main module."""

import unittest

from main import (
    GraphQLSchemaAdapter,
    SchemaFormatError,
    NetworkError,
    ValidationError
)


class TestGraphQLSchemaAdapter(unittest.TestCase):
    """Test GraphQLSchemaAdapter behavior for all key functionalities."""

    def setUp(self):
        """Initialize common schema, endpoint, headers, and config."""
        self.valid_endpoint = "https://example.com/graphql"
        self.invalid_endpoint = "ftp://invalid-url"
        self.headers = {"Authorization": "Bearer token"}
        self.config = {
            "validate_changes": True,
            "print_diff": True,
            "update_internal_state": True
        }
        self.minimal_schema = {
            "__schema": {
                "types": [
                    {
                        "name": "Query",
                        "kind": "OBJECT",
                        "fields": [
                            {
                                "name": "hello",
                                "type": {"kind": "SCALAR", "name": "String"},
                                "args": []
                            }
                        ]
                    }
                ]
            }
        }
        self.modified_schema = {
            "__schema": {
                "types": [
                    {
                        "name": "Query",
                        "kind": "OBJECT",
                        "fields": [
                            {
                                "name": "hello",
                                "type": {"kind": "SCALAR", "name": "Int"},
                                "args": []
                            },
                            {
                                "name": "newField",
                                "type": {"kind": "SCALAR", "name": "String"},
                                "args": []
                            }
                        ]
                    },
                    {
                        "name": "ExtraType",
                        "kind": "OBJECT",
                        "fields": []
                    }
                ]
            }
        }

    def test_invalid_endpoint_raises_validation_error(self):
        """Raise ValidationError for invalid endpoint."""
        with self.assertRaises(ValidationError):
            GraphQLSchemaAdapter(self.invalid_endpoint)

    def test_unsupported_config_key_raises_validation_error(self):
        """Raise ValidationError for unknown config key."""
        with self.assertRaises(ValidationError):
            GraphQLSchemaAdapter(
                self.valid_endpoint,
                config={"bad_key": True}
            )

    def test_load_previous_schema_with_invalid_dict_raises_error(self):
        """Raise SchemaFormatError for invalid previous schema."""
        adapter = GraphQLSchemaAdapter(self.valid_endpoint)
        with self.assertRaises(SchemaFormatError):
            adapter.load_previous_schema({"not_schema": {}})

    def test_load_previous_schema_with_none_returns_none(self):
        """Return None when previous schema is None."""
        adapter = GraphQLSchemaAdapter(self.valid_endpoint)
        self.assertIsNone(adapter.load_previous_schema(None))

    def test_compare_schemas_detects_added_and_removed_types(self):
        """Detect added and removed types between schemas."""
        adapter = GraphQLSchemaAdapter(self.valid_endpoint)
        diff = adapter.compare_schemas(
            self.minimal_schema,
            self.modified_schema
        )
        added = [t["type"] for t in diff["added_types"]]
        removed = [t["type"] for t in diff["removed_types"]]
        self.assertIn("ExtraType", added)
        self.assertEqual(len(removed), 0)

    def test_compare_schemas_detects_added_and_removed_fields(self):
        """Detect field additions and removals in types."""
        adapter = GraphQLSchemaAdapter(self.valid_endpoint)
        mod_schema = {
            "__schema": {
                "types": [
                    {
                        "name": "Query",
                        "kind": "OBJECT",
                        "fields": [
                            {
                                "name": "hello",
                                "type": {"kind": "SCALAR", "name": "String"},
                                "args": []
                            }
                        ]
                    }
                ]
            }
        }
        diff = adapter.compare_schemas(self.modified_schema, mod_schema)
        removed = [t for t in diff["removed_types"] if "field" in t]
        self.assertTrue(any(f["field"] == "newField" for f in removed))

    def test_compare_schemas_detects_changed_fields(self):
        """Detect changes in field types."""
        adapter = GraphQLSchemaAdapter(self.valid_endpoint)
        diff = adapter.compare_schemas(
            self.minimal_schema,
            self.modified_schema
        )
        changed = [
            f for f in diff["changed_fields"] if f["field"] == "hello"
        ]
        self.assertTrue(changed)
        self.assertEqual(changed[0]["old_type"], "String")
        self.assertEqual(changed[0]["new_type"], "Int")

    def test_update_internal_state_applies_diff(self):
        """Update internal state using given diff."""
        adapter = GraphQLSchemaAdapter(self.valid_endpoint)
        diff = adapter.compare_schemas(
            self.minimal_schema,
            self.modified_schema
        )
        adapter.update_internal_state(diff)
        self.assertEqual(adapter.internal_state, diff)

    def test_run_returns_current_schema_only_if_no_old_schema(self):
        """Return only current schema when old schema is None."""
        adapter = GraphQLSchemaAdapter(self.valid_endpoint)
        adapter.fetch_current_schema = lambda: self.minimal_schema
        result = adapter.run()
        self.assertIn("current_schema", result)
        self.assertNotIn("added_types", result)

    def test_run_returns_diff_if_old_schema_provided(self):
        """Return schema diff when old schema is provided."""
        adapter = GraphQLSchemaAdapter(self.valid_endpoint)
        adapter.fetch_current_schema = lambda: self.modified_schema
        result = adapter.run(self.minimal_schema)
        self.assertIn("added_types", result)
        self.assertIn("removed_types", result)
        self.assertIn("changed_fields", result)

    def test_run_updates_internal_state_if_config_enabled(self):
        """Update internal state if config enables it."""
        adapter = GraphQLSchemaAdapter(
            self.valid_endpoint,
            config={"update_internal_state": True}
        )
        adapter.fetch_current_schema = lambda: self.modified_schema
        adapter.internal_state = None
        adapter.run(self.minimal_schema)
        self.assertIsNotNone(adapter.internal_state)

    def test_run_does_not_update_internal_state_if_config_disabled(self):
        """Do not update internal state if config disables it."""
        adapter = GraphQLSchemaAdapter(
            self.valid_endpoint,
            config={"update_internal_state": False}
        )
        adapter.fetch_current_schema = lambda: self.modified_schema
        adapter.internal_state = None
        adapter.run(self.minimal_schema)
        self.assertIsNone(adapter.internal_state)

    def test_schema_cache_returns_cached_schema(self):
        """Return cached schema for repeated same endpoint."""
        adapter = GraphQLSchemaAdapter(
            self.valid_endpoint,
            headers=self.headers
        )

        def fake_post(*args, **kwargs):
            class FakeResp:
                status_code = 200

                def json(self):
                    return {"data": {"__schema": {"types": []}}}

                def raise_for_status(self):
                    pass

            return FakeResp()

        import main
        main.requests.post = fake_post
        schema1 = adapter.fetch_current_schema()
        schema2 = adapter.fetch_current_schema()
        self.assertEqual(schema1, schema2)

    def test_fetch_current_schema_raises_network_error_on_401(self):
        """Raise NetworkError on unauthorized response."""
        adapter = GraphQLSchemaAdapter(self.valid_endpoint)

        def fake_post(*args, **kwargs):
            class FakeResp:
                status_code = 401

                def raise_for_status(self):
                    raise Exception("401 Unauthorized")

                def json(self):
                    return {"data": {"__schema": {"types": []}}}

            return FakeResp()

        import main
        main.requests.post = fake_post
        with self.assertRaises(NetworkError):
            adapter.fetch_current_schema()

    def test_schema_format_error_on_missing_schema(self):
        """Raise SchemaFormatError when '__schema' is missing."""
        adapter = GraphQLSchemaAdapter(self.valid_endpoint)

        def fake_post(*args, **kwargs):
            class FakeResp:
                status_code = 200

                def raise_for_status(self):
                    pass

                def json(self):
                    return {"data": {}}

            return FakeResp()

        import main
        main.requests.post = fake_post
        with self.assertRaises(SchemaFormatError):
            adapter.fetch_current_schema()


if __name__ == "__main__":
    unittest.main()
