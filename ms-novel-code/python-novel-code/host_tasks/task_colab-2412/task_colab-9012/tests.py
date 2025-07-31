# tests
"""Unit tests for the CSVTransformer class."""

import unittest
import tempfile
import os
from datetime import datetime, timezone
from main import CSVTransformer


class TestCSVTransformer(unittest.TestCase):
    """Test suite for the CSVTransformer class."""

    def setUp(self):
        """Prepare common schema and sample CSV content for tests."""
        self.schema = {
            "id": {"target_field": "user.id", "type": int},
            "name": {"target_field": "user.name", "type": str},
            "active": {"target_field": "user.active", "type": bool},
            "created": {"target_field": "meta.created", "type": datetime},
        }

        self.valid_csv = (
            "id,name,active,created\n"
            "1,Alice,true,2023-01-01T10:00:00Z\n"
            "2,Bob,false,2023-02-01T11:30:00Z\n"
        )

    def _write_temp_file(self, content):
        """Write content to a temporary file and return the file path."""
        f = tempfile.NamedTemporaryFile(mode="w+", delete=False)
        f.write(content)
        f.close()
        return f.name

    def tearDown(self):
        """Clean up temporary files created during the tests."""
        for f in getattr(self, "_files_to_cleanup", []):
            os.unlink(f)

    def _cleanup_file(self, path):
        """Track a file for cleanup after the test."""
        if not hasattr(self, "_files_to_cleanup"):
            self._files_to_cleanup = []
        self._files_to_cleanup.append(path)

    def test_flat_mode_transform(self):
        """Test transformation in 'flat' mode."""
        path = self._write_temp_file(self.valid_csv)
        self._cleanup_file(path)
        transformer = CSVTransformer(self.schema, mode="flat")
        result = transformer.transform(path)
        self.assertEqual(len(result), 2)
        self.assertIn("user.id", result[0])
        self.assertIn("meta.created", result[0])

    def test_nested_mode_transform(self):
        """Test transformation in 'nested' mode."""
        path = self._write_temp_file(self.valid_csv)
        self._cleanup_file(path)
        transformer = CSVTransformer(self.schema, mode="nested")
        result = transformer.transform(path)
        self.assertEqual(result[0]["user"]["id"], 1)

    def test_grouped_mode(self):
        """Test grouping rows by a column in 'grouped' mode."""
        schema = {
            "name": {"target_field": "name", "type": str},
            "id": {"target_field": "id", "type": int},
        }
        csv = "id,name\n1,Alice\n2,Alice\n3,Bob\n"
        path = self._write_temp_file(csv)
        self._cleanup_file(path)
        transformer = CSVTransformer(schema, mode="grouped", group_by="name")
        result = transformer.transform(path)
        self.assertEqual(len(result["Alice"]), 2)
        self.assertEqual(len(result["Bob"]), 1)

    def test_invalid_mode(self):
        """Test error raised for invalid mode."""
        with self.assertRaises(ValueError):
            CSVTransformer(self.schema, mode="invalid")

    def test_invalid_on_error(self):
        """Test error raised for invalid on_error mode."""
        with self.assertRaises(ValueError):
            CSVTransformer(self.schema, on_error="warn")

    def test_grouped_missing_group_by(self):
        """Test error raised when 'group_by' is missing in grouped mode."""
        with self.assertRaises(ValueError):
            CSVTransformer(self.schema, mode="grouped")

    def test_missing_required_column_raises(self):
        """Test that missing columns raise an error with on_error='raise'."""
        csv = "id,created\n1,2022-01-01T00:00:00Z\n"
        path = self._write_temp_file(csv)
        self._cleanup_file(path)
        transformer = CSVTransformer(self.schema, on_error="raise")
        with self.assertRaises(ValueError):
            transformer.transform(path)

    def test_missing_required_column_skip(self):
        """Test that missing columns are skipped with on_error='skip'."""
        csv = "id,created\n1,2022-01-01T00:00:00Z\n"
        path = self._write_temp_file(csv)
        self._cleanup_file(path)
        transformer = CSVTransformer(self.schema, on_error="skip")
        result = transformer.transform(path)
        self.assertEqual(len(result), 1)

    def test_casting_error_raise(self):
        """Test that casting errors raise an exception."""
        csv = "id,name,active,created\nX,Alice,true,invalid\n"
        path = self._write_temp_file(csv)
        self._cleanup_file(path)
        transformer = CSVTransformer(self.schema, on_error="raise")
        with self.assertRaises(Exception):
            transformer.transform(path)

    def test_casting_error_skip(self):
        """Test that casting errors are skipped with on_error='skip'."""
        csv = "id,name,active,created\n1,Alice,,2023-01-01T00:00:00Z\n"
        path = self._write_temp_file(csv)
        self._cleanup_file(path)
        transformer = CSVTransformer(self.schema, mode="flat", on_error="skip")
        result = transformer.transform(path)
        expected = [{
            "user.id": 1,
            "user.name": "Alice",
            "meta.created": datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc),
        }]
        self.assertEqual(result, expected)

    def test_empty_csv_returns_empty_list(self):
        """Test that an empty CSV returns an empty list."""
        path = self._write_temp_file("")
        self._cleanup_file(path)
        transformer = CSVTransformer(self.schema, mode="flat")
        result = transformer.transform(path)
        self.assertEqual(result, [])

    def test_exceed_max_columns(self):
        """Test error raised when column count exceeds maximum allowed."""
        header = ",".join([f"col{i}" for i in range(101)])
        path = self._write_temp_file(header + "\n")
        self._cleanup_file(path)
        transformer = CSVTransformer({}, mode="flat")
        with self.assertRaises(ValueError):
            transformer.transform(path)

    def test_schema_duplicate_target_field(self):
        """Test schema validation for duplicate target_field entries."""
        schema = {
            "id": {"target_field": "user.id", "type": int},
            "uid": {"target_field": "user.id", "type": int},
        }
        with self.assertRaises(ValueError):
            CSVTransformer(schema)

    def test_schema_exceeds_nesting(self):
        """Test error for schema field path exceeding nesting limit."""
        schema = {
            "id": {"target_field": "a.b.c.d.e.f", "type": int},
        }
        with self.assertRaises(ValueError):
            CSVTransformer(schema)

    def test_cast_type_bool(self):
        """Test casting string values to bool."""
        t = CSVTransformer({})
        self.assertTrue(t._cast_type("True", bool))
        self.assertFalse(t._cast_type("0", bool))

    def test_cast_type_invalid_bool(self):
        """Test casting invalid bool string raises error."""
        t = CSVTransformer({}, on_error="raise")
        with self.assertRaises(ValueError):
            t._cast_type("maybe", bool)

    def test_cast_type_int(self):
        """Test casting string to integer."""
        t = CSVTransformer({})
        self.assertEqual(t._cast_type("123", int), 123)

    def test_cast_type_datetime(self):
        """Test parsing ISO 8601 datetime string."""
        t = CSVTransformer({})
        dt = t._cast_type("2023-01-01T10:00:00Z", datetime)
        self.assertIsInstance(dt, datetime)

    def test_cast_type_unsupported_type(self):
        """Test error raised for unsupported type casting."""
        t = CSVTransformer({}, on_error="raise")
        with self.assertRaises(TypeError):
            t._cast_type("{}", dict)

    def test_flatten_dict(self):
        """Test flattening of a nested dictionary."""
        t = CSVTransformer({})
        nested = {"a": {"b": {"c": 1}}}
        flat = t._flatten_dict(nested)
        self.assertEqual(flat["a.b.c"], 1)

    def test_construct_mapped_field(self):
        """Test nested field assignment using dot-separated path."""
        t = CSVTransformer({})
        d = {}
        t._construct_mapped_field(d, "a.b.c", 42)
        self.assertEqual(d["a"]["b"]["c"], 42)

    def test_extract_group_key(self):
        """Test extraction of group_by key from nested structure."""
        t = CSVTransformer({}, mode="grouped", group_by="a.b")
        row = {"a": {"b": "x"}}
        self.assertEqual(t._extract_group_key(row), "x")

    def test_extract_group_key_missing(self):
        """Test missing group_by key returns None."""
        t = CSVTransformer({}, mode="grouped", group_by="a.b")
        row = {"a": {"c": "x"}}
        self.assertIsNone(t._extract_group_key(row))
