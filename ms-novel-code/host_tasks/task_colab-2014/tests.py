# tests
"""Unittests for CSVTransformer: validate modes, casting, schema and errors."""

import unittest
import tempfile
import os
from datetime import datetime
from main import CSVTransformer


class TestCSVTransformer(unittest.TestCase):
    """Unittests for the CSVTransformer class."""

    def setUp(self):
        """Set up temporary CSV files and schema for tests."""
        self.schema = {
            "id": {"target_field": "user.id", "type": int},
            "name": {"target_field": "user.name", "type": str},
            "active": {"target_field": "status.active", "type": bool},
            "created": {"target_field": "meta.created", "type": datetime},
        }

        self.csv_data = (
            "id,name,active,created\n"
            "1,Alice,true,2023-01-01T10:00:00Z\n"
            "2,Bob,false,2023-01-02T12:30:00Z\n"
        )

        self.temp_file = tempfile.NamedTemporaryFile(mode="w+", delete=False)
        self.temp_file.write(self.csv_data)
        self.temp_file.close()

    def tearDown(self):
        """Clean up the temporary file."""
        os.unlink(self.temp_file.name)

    def test_flat_mode(self):
        """Test transformation in flat mode."""
        transformer = CSVTransformer(self.schema, mode="flat")
        result = transformer.transform(self.temp_file.name)
        self.assertEqual(len(result), 2)
        self.assertIn("user.id", result[0])

    def test_nested_mode(self):
        """Test transformation in nested mode."""
        transformer = CSVTransformer(self.schema, mode="nested")
        result = transformer.transform(self.temp_file.name)
        self.assertEqual(result[0]["user"]["id"], 1)

    def test_grouped_mode(self):
        """Test transformation in grouped mode by name."""
        schema = {
            "name": {"target_field": "name", "type": str},
            "id": {"target_field": "id", "type": int},
        }
        csv_data = "id,name\n1,Alice\n2,Alice\n3,Bob\n"
        file = tempfile.NamedTemporaryFile(mode="w+", delete=False)
        file.write(csv_data)
        file.close()

        transformer = CSVTransformer(schema, mode="grouped", group_by="name")
        result = transformer.transform(file.name)
        os.unlink(file.name)
        self.assertEqual(len(result["Alice"]), 2)

    def test_invalid_mode(self):
        """Test initialization with an invalid mode."""
        with self.assertRaises(ValueError):
            CSVTransformer(self.schema, mode="invalid")

    def test_invalid_on_error(self):
        """Test initialization with invalid on_error strategy."""
        with self.assertRaises(ValueError):
            CSVTransformer(self.schema, on_error="fail")

    def test_grouped_without_group_by(self):
        """Test grouped mode without group_by."""
        with self.assertRaises(ValueError):
            CSVTransformer(self.schema, mode="grouped")

    def test_exceed_max_columns(self):
        """Test column limit enforcement."""
        csv_data = ",".join([f"col{i}" for i in range(101)]) + "\n"
        file = tempfile.NamedTemporaryFile(mode="w+", delete=False)
        file.write(csv_data)
        file.close()
        transformer = CSVTransformer({}, mode="flat")

        with self.assertRaises(ValueError):
            transformer.transform(file.name)
        os.unlink(file.name)

    def test_empty_file(self):
        """Test handling of empty file."""
        file = tempfile.NamedTemporaryFile(mode="w+", delete=False)
        file.close()
        transformer = CSVTransformer(self.schema, mode="flat")
        result = transformer.transform(file.name)
        os.unlink(file.name)
        self.assertEqual(result, [])

    def test_missing_required_column(self):
        """Test missing column error behavior."""
        csv_data = "id,created\n1,2022-01-01T00:00:00Z\n"
        file = tempfile.NamedTemporaryFile(mode="w+", delete=False)
        file.write(csv_data)
        file.close()
        transformer = CSVTransformer(
            self.schema, mode="flat", on_error="skip"
        )
        result = transformer.transform(file.name)
        os.unlink(file.name)
        self.assertEqual(len(result), 1)

    def test_casting_error_skip(self):
        """Test skipping rows with type casting errors."""
        csv_data = "id,name,active,created\nX,Alice,true,invalid\n"
        file = tempfile.NamedTemporaryFile(mode="w+", delete=False)
        file.write(csv_data)
        file.close()
        transformer = CSVTransformer(
            self.schema, mode="flat", on_error="skip"
        )
        result = transformer.transform(file.name)
        os.unlink(file.name)
        self.assertEqual(
            result,
            [{'user.name': 'Alice', 'status.active': True}]
        )

    def test_casting_error_raise(self):
        """Test raising exception on casting errors."""
        csv_data = "id,name,active,created\nX,Alice,true,invalid\n"
        file = tempfile.NamedTemporaryFile(mode="w+", delete=False)
        file.write(csv_data)
        file.close()
        transformer = CSVTransformer(
            self.schema, mode="flat", on_error="raise"
        )

        with self.assertRaises(Exception):
            transformer.transform(file.name)
        os.unlink(file.name)

    def test_boolean_true_casting(self):
        """Test valid boolean string conversion."""
        transformer = CSVTransformer(
            {"active": {"target_field": "a", "type": bool}}
        )
        row = {"active": "true"}
        result = transformer._process_row(row)
        self.assertTrue(result["a"])

    def test_boolean_invalid_casting(self):
        """Test invalid boolean string conversion raises."""
        transformer = CSVTransformer(
            {"active": {"target_field": "a", "type": bool}},
            on_error="raise"
        )
        row = {"active": "yes"}
        with self.assertRaises(ValueError):
            transformer._process_row(row)

    def test_datetime_casting(self):
        """Test valid datetime parsing."""
        transformer = CSVTransformer(
            {"created": {"target_field": "meta.created", "type": datetime}}
        )
        row = {"created": "2024-01-01T10:00:00Z"}
        result = transformer._process_row(row)
        self.assertIsInstance(result["meta"]["created"], datetime)

    def test_unsupported_type_cast(self):
        """Test unsupported type raises TypeError."""
        transformer = CSVTransformer(
            {"x": {"target_field": "x", "type": list}}
        )
        row = {"x": "[1,2]"}
        with self.assertRaises(TypeError):
            transformer._process_row(row)

    def test_flatten_nested_dict(self):
        """Test flattening a nested dictionary."""
        transformer = CSVTransformer(self.schema)
        nested = {"a": {"b": {"c": 1}}}
        flat = transformer._flatten_dict(nested)
        self.assertEqual(flat["a.b.c"], 1)

    def test_missing_field_skipped(self):
        """Test skipping missing field when on_error is skip."""
        transformer = CSVTransformer(self.schema, on_error="skip")
        row = {"id": "1", "name": ""}
        result = transformer._process_row(row)
        self.assertEqual(result.get("user", {}).get("id"), 1)

    def test_group_key_extraction(self):
        """Test group key extraction from nested path."""
        transformer = CSVTransformer(
            self.schema, mode="grouped", group_by="user.name"
        )
        row = {"user": {"name": "Alice"}}
        key = transformer._extract_group_key(row)
        self.assertEqual(key, "Alice")

    def test_construct_mapped_field(self):
        """Test building nested path."""
        transformer = CSVTransformer(self.schema)
        base = {}
        transformer._construct_mapped_field(base, "a.b.c", 123)
        self.assertEqual(base["a"]["b"]["c"], 123)
