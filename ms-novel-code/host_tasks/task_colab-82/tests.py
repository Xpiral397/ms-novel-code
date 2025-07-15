# tests
"""Unit tests for the LogProcessor class."""

import unittest
import os
import tempfile
from main import LogProcessor


class TestLogProcessor(unittest.TestCase):
    """Test cases for the LogProcessor class."""

    def setUp(self):
        """Create a temporary file and LogProcessor before each test."""
        self.temp_file = tempfile.NamedTemporaryFile(
            delete=False, mode='w+', encoding='utf-8'
        )
        self.processor = LogProcessor(self.temp_file.name)

    def tearDown(self):
        """Remove the temporary file after each test."""
        self.temp_file.close()
        os.remove(self.temp_file.name)

    def test_single_info_line(self):
        """Test a single INFO line is categorized correctly."""
        result = self.processor.append_and_categorize(
            ["INFO This is an info message"]
        )
        self.assertEqual(result["INFO"], ["INFO This is an info message"])

    def test_single_error_line(self):
        """Test a single ERROR line is categorized correctly."""
        result = self.processor.append_and_categorize(
            ["ERROR Something went wrong"]
        )
        self.assertEqual(result["ERROR"], ["ERROR Something went wrong"])

    def test_single_warning_line(self):
        """Test a single WARNING line is categorized correctly."""
        result = self.processor.append_and_categorize(["WARNING Check this"])
        self.assertEqual(result["WARNING"], ["WARNING Check this"])

    def test_single_date_line(self):
        """Test a line with only a date gets categorized as DATE."""
        result = self.processor.append_and_categorize(
            ["Event on 2025-07-14"]
        )
        self.assertEqual(result["DATE"], ["Event on 2025-07-14"])

    def test_line_with_multiple_categories(self):
        """Test line matching WARNING and DATE categories."""
        line = "WARNING System failure at 2025-07-14"
        result = self.processor.append_and_categorize([line])
        self.assertIn(line, result["WARNING"])
        self.assertIn(line, result["DATE"])

    def test_line_with_no_category(self):
        """Test unclassified lines go to OTHER."""
        result = self.processor.append_and_categorize(["Random text here"])
        self.assertEqual(result["OTHER"], ["Random text here"])

    def test_blank_line_ignored(self):
        """Test completely blank lines are ignored."""
        result = self.processor.append_and_categorize(["   "])
        for category in result:
            self.assertEqual(result[category], [])

    def test_multiple_lines_various_categories(self):
        """Test multiple lines with different categories."""
        lines = [
            "INFO Starting service",
            "ERROR Failed to bind port",
            "WARNING Low memory",
            "Logged on 2025-01-01",
            "Unrecognized format"
        ]
        result = self.processor.append_and_categorize(lines)
        self.assertIn(lines[0], result["INFO"])
        self.assertIn(lines[1], result["ERROR"])
        self.assertIn(lines[2], result["WARNING"])
        self.assertIn(lines[3], result["DATE"])
        self.assertIn(lines[4], result["OTHER"])

    def test_multiple_date_matches(self):
        """Test multiple lines with date patterns."""
        lines = ["Date1: 2022-01-01", "Date2: 1999-12-31"]
        result = self.processor.append_and_categorize(lines)
        self.assertEqual(result["DATE"], lines)

    def test_line_matches_info_and_date(self):
        """Test line matching both INFO and DATE categories."""
        line = "INFO System started on 2023-03-15"
        result = self.processor.append_and_categorize([line])
        self.assertIn(line, result["INFO"])
        self.assertIn(line, result["DATE"])

    def test_multiple_calls_accumulate_correctly(self):
        """Test correct categorization after multiple calls."""
        self.processor.append_and_categorize(["INFO First"])
        result = self.processor.append_and_categorize(["ERROR Second"])
        self.assertEqual(result["ERROR"], ["ERROR Second"])
        self.assertEqual(result["INFO"], [])

    def test_only_new_lines_are_processed(self):
        """Test that only newly added lines are read and categorized."""
        self.processor.append_and_categorize(["INFO First"])
        self.processor.append_and_categorize(["WARNING Second"])
        result = self.processor.append_and_categorize(["2025-07-14"])
        self.assertEqual(result["DATE"], ["2025-07-14"])
        self.assertEqual(result["INFO"], [])
        self.assertEqual(result["WARNING"], [])

    def test_line_with_trailing_newline(self):
        """Test lines with newline characters are stripped."""
        result = self.processor.append_and_categorize(["INFO Hello\n"])
        self.assertIn("INFO Hello", result["INFO"])

    def test_line_with_mixed_case_prefix(self):
        """Test lowercase prefixes are not matched as categories."""
        result = self.processor.append_and_categorize(
            ["info lowercase should be OTHER"]
        )
        self.assertIn("info lowercase should be OTHER", result["OTHER"])
        self.assertEqual(result["INFO"], [])

    def test_line_with_embedded_info(self):
        """Test embedded keywords do not trigger categorization."""
        result = self.processor.append_and_categorize(["This is not INFO"])
        self.assertIn("This is not INFO", result["OTHER"])

    def test_no_lines_passed(self):
        """Test behavior when no lines are passed."""
        result = self.processor.append_and_categorize([])
        for category in result:
            self.assertEqual(result[category], [])

    def test_whitespace_line(self):
        """Test line with only whitespace is ignored."""
        result = self.processor.append_and_categorize(["   \t  \n"])
        for category in result:
            self.assertEqual(result[category], [])

    def test_multiple_categories_accumulate_properly(self):
        """Test multiple categories accumulate correctly."""
        self.processor.append_and_categorize(["INFO A", "INFO B"])
        result = self.processor.append_and_categorize(
            ["ERROR C", "WARNING D", "ERROR E"]
        )
        self.assertEqual(result["INFO"], [])
        self.assertEqual(result["ERROR"], ["ERROR C", "ERROR E"])
        self.assertEqual(result["WARNING"], ["WARNING D"])

    def test_reading_only_appended_content(self):
        """Test manually appended content is skipped."""
        self.processor.append_and_categorize(["INFO Start"])
        with open(self.temp_file.name, 'a', encoding='utf-8') as f:
            f.write("Manually added line\n")
        result = self.processor.append_and_categorize(["ERROR Forced"])
        self.assertEqual(result["ERROR"], ["ERROR Forced"])
