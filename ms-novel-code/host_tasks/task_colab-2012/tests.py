# tests
"""Unit tests for the CSV processing pipeline module."""

import unittest
import tempfile
import os
import csv
from main import process_csv_pipeline


class TestProcessCSVPipeline(unittest.TestCase):
    """Test suite for validating process_csv_pipeline behavior."""

    def setUp(self):
        """Create a temporary CSV file for testing."""
        self.temp_file = tempfile.NamedTemporaryFile(
            delete=False, mode='w', newline='', encoding='utf-8'
        )
        writer = csv.DictWriter(
            self.temp_file, fieldnames=['name', 'age', 'salary']
        )
        writer.writeheader()
        writer.writerows([
            {'name': 'Alice', 'age': '30', 'salary': '70000'},
            {'name': 'Bob', 'age': '25', 'salary': '50000'},
            {'name': 'Charlie', 'age': '35', 'salary': '80000'},
            {'name': 'Dana', 'age': 'invalid', 'salary': '40000'},
        ])
        self.temp_file.close()
        self.file_path = self.temp_file.name

    def tearDown(self):
        """Remove the temporary CSV file after testing."""
        os.remove(self.file_path)

    def test_filter_valid_numeric_column(self):
        """Test filtering rows with numeric age > 30."""
        ops = [('filter', 'age', lambda x: x.isdigit() and int(x) > 30)]
        result = process_csv_pipeline(self.file_path, ops)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['name'], 'Charlie')

    def test_filter_invalid_column(self):
        """Test filtering using a nonexistent column."""
        ops = [('filter', 'nonexistent', lambda x: True)]
        result = process_csv_pipeline(self.file_path, ops)
        self.assertEqual(result, [])

    def test_map_valid_operation(self):
        """Test mapping a column to create a new computed column."""
        ops = [('map', 'double_salary', lambda row: int(row['salary']) * 2)]
        result = process_csv_pipeline(self.file_path, ops)
        self.assertEqual(result[0]['double_salary'], 140000)
        self.assertEqual(result[1]['double_salary'], 100000)

    def test_map_raises_exception_skips_row(self):
        """Test that rows raising exceptions during map are skipped."""
        ops = [('map', 'parsed_age', lambda row: int(row['age']))]
        result = process_csv_pipeline(self.file_path, ops)
        for row in result:
            self.assertIn('parsed_age', row)
            self.assertNotEqual(row['name'], 'Dana')
        self.assertEqual(len(result), 3)

    def test_reduce_sum_salary(self):
        """Test reducing mapped numeric salary values to their sum."""
        ops = [
            ('map', 'numeric_salary', lambda row: int(row['salary'])),
            ('reduce', lambda acc, row: acc + row['numeric_salary'], 0),
        ]
        result = process_csv_pipeline(self.file_path, ops)
        self.assertEqual(result, 70000 + 50000 + 80000 + 40000)

    def test_reduce_returns_initial_on_empty_data(self):
        """Test reduce on filtered-out data returns initial value."""
        ops = [
            ('filter', 'age', lambda x: False),
            ('reduce', lambda acc, row: acc + 1, 0),
        ]
        result = process_csv_pipeline(self.file_path, ops)
        self.assertEqual(result, 0)

    def test_invalid_file_path(self):
        """Test error raised on missing input file."""
        with self.assertRaises(FileNotFoundError):
            process_csv_pipeline("nonexistent.csv", [])

    def test_invalid_operation_format(self):
        """Test malformed operation raises ValueError."""
        with self.assertRaises(ValueError):
            process_csv_pipeline(self.file_path, [None])

    def test_unknown_operation_type(self):
        """Test unknown operation raises ValueError."""
        with self.assertRaises(ValueError):
            process_csv_pipeline(
                self.file_path, [('transform', 'col', lambda x: x)]
            )

    def test_invalid_filter_length(self):
        """Test ValueError for improperly sized filter tuple."""
        with self.assertRaises(ValueError):
            process_csv_pipeline(self.file_path, [('filter', 'age')])

    def test_invalid_map_length(self):
        """Test ValueError for improperly sized map tuple."""
        with self.assertRaises(ValueError):
            process_csv_pipeline(self.file_path, [('map', 'new_col')])

    def test_invalid_reduce_length(self):
        """Test ValueError for improperly sized reduce tuple."""
        with self.assertRaises(ValueError):
            process_csv_pipeline(
                self.file_path, [('reduce', lambda x, y: x)]
            )

    def test_pipeline_no_operations(self):
        """Test pipeline returns unmodified data if no ops given."""
        result = process_csv_pipeline(self.file_path, [])
        self.assertEqual(len(result), 4)

    def test_chained_filter_and_map(self):
        """Test combined filtering and mapping operations."""
        ops = [
            ('filter', 'age', lambda x: x.isdigit() and int(x) < 33),
            ('map', 'greeting', lambda row: f"Hello {row['name']}"),
        ]
        result = process_csv_pipeline(self.file_path, ops)
        self.assertEqual(len(result), 2)
        self.assertIn('greeting', result[0])

    def test_filter_all_invalid_rows(self):
        """Test filtering out all rows results in empty output."""
        ops = [('filter', 'age', lambda x: False)]
        result = process_csv_pipeline(self.file_path, ops)
        self.assertEqual(result, [])

    def test_map_add_constant_column(self):
        """Test adding a constant value column using map."""
        ops = [('map', 'country', lambda row: 'India')]
        result = process_csv_pipeline(self.file_path, ops)
        for row in result:
            self.assertEqual(row['country'], 'India')

    def test_reduce_to_list_of_names(self):
        """Test reducing to a list of names."""
        ops = [('reduce', lambda acc, row: acc + [row['name']], [])]
        result = process_csv_pipeline(self.file_path, ops)
        self.assertListEqual(result, ['Alice', 'Bob', 'Charlie', 'Dana'])

    def test_reduce_on_filtered_rows(self):
        """Test reduction after filtering based on salary."""
        ops = [
            ('filter', 'salary', lambda x: int(x) > 60000),
            ('reduce', lambda acc, row: acc + [row['name']], []),
        ]
        result = process_csv_pipeline(self.file_path, ops)
        self.assertEqual(result, ['Alice', 'Charlie'])

    def test_map_add_length_of_name(self):
        """Test mapping to create name length column."""
        ops = [('map', 'name_len', lambda row: len(row['name']))]
        result = process_csv_pipeline(self.file_path, ops)
        for row in result:
            self.assertEqual(row['name_len'], len(row['name']))

    def test_map_skips_row_on_key_error(self):
        """Test map skips rows if referenced column is missing."""
        ops = [('map', 'missing_col', lambda row: row['unknown'])]
        result = process_csv_pipeline(self.file_path, ops)
        self.assertEqual(result, [])

    def test_filter_with_exception_returns_false(self):
        """Test filter returns False on exception (invalid int)."""
        ops = [('filter', 'age', lambda x: int(x) > 0)]
        result = process_csv_pipeline(self.file_path, ops)
        self.assertEqual(len(result), 3)
