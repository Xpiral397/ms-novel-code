# tests
"""Unit tests for the MarkdownParser and conversion utilities."""

import unittest
import tempfile
import os
from main import MarkdownParser, MarkdownParseError, convert_markdown_to_html


class TestMarkdownParser(unittest.TestCase):
    """Unit tests for the MarkdownParser class."""

    def setUp(self):
        """Initialize parser instance for test cases."""
        self.parser = MarkdownParser()

    def test_empty_string(self):
        """Test that an empty string returns a valid HTML structure."""
        html = self.parser.parse_string("")
        self.assertIn("<body>", html)
        self.assertIn("</body>", html)

    def test_single_header(self):
        """Test parsing a single level-1 header."""
        html = self.parser.parse_string("# Hello World")
        self.assertIn("<h1>Hello World</h1>", html)

    def test_multiple_headers(self):
        """Test parsing headers of various levels."""
        html = self.parser.parse_string("# H1\n## H2\n### H3")
        self.assertIn("<h1>H1</h1>", html)
        self.assertIn("<h2>H2</h2>", html)
        self.assertIn("<h3>H3</h3>", html)

    def test_bold_formatting(self):
        """Test parsing bold syntax."""
        html = self.parser.parse_string("This is **bold** text.")
        self.assertIn("<strong>bold</strong>", html)

    def test_italic_formatting(self):
        """Test parsing italic syntax."""
        html = self.parser.parse_string("This is *italic* text.")
        self.assertIn("<em>italic</em>", html)

    def test_link_formatting(self):
        """Test parsing a basic markdown link."""
        html = self.parser.parse_string("Visit [Google](https://google.com)")
        self.assertIn('<a href="https://google.com">Google</a>', html)

    def test_bold_and_italic_inside_link(self):
        """Test parsing bold content inside a link."""
        html = self.parser.parse_string("[**Bold Link**](https://bold.com)")
        self.assertIn(
            '<a href="https://bold.com"><strong>Bold Link</strong></a>', html)

    def test_unordered_list(self):
        """Test rendering of a basic unordered list."""
        md = "- Item 1\n- Item 2"
        html = self.parser.parse_string(md)
        self.assertIn("<ul>", html)
        self.assertIn("<li>Item 1</li>", html)

    def test_ordered_list(self):
        """Test rendering of an ordered list."""
        md = "1. First\n2. Second"
        html = self.parser.parse_string(md)
        self.assertIn("<ol>", html)
        self.assertIn("<li>First</li>", html)

    def test_nested_list(self):
        """Test rendering of a nested unordered list."""
        md = "- Item 1\n  - Subitem"
        html = self.parser.parse_string(md)
        self.assertIn("<ul>", html)
        self.assertIn("<li>Subitem</li>", html)

    def test_malformed_list_recovery(self):
        """Test how parser handles malformed list markers."""
        md = "- Item 1\n *Item with malformed marker"
        html = self.parser.parse_string(md)
        self.assertIn("<li>Item 1", html)
        self.assertIn("<p> *Item with malformed marker</p>", html)
        self.assertIn("</li>", html)

    def test_inline_formatting_in_paragraph(self):
        """Test combined inline formatting within a paragraph."""
        md = "Hello *world* and **Python** [link](https://test.com)"
        html = self.parser.parse_string(md)
        self.assertIn("<em>world</em>", html)
        self.assertIn("<strong>Python</strong>", html)
        self.assertIn('<a href="https://test.com">link</a>', html)

    def test_html_escaping(self):
        """Test that HTML-sensitive characters are escaped."""
        md = "5 < 10 & 3 > 2"
        html = self.parser.parse_string(md)
        self.assertIn("5 &lt; 10 &amp; 3 &gt; 2", html)

    def test_malformed_link(self):
        """Test that malformed links are not converted."""
        md = "[Bad Link](not closed"
        html = self.parser.parse_string(md)
        self.assertIn("[Bad Link](not closed", html)

    def test_unclosed_bold(self):
        """Test that unclosed bold formatting is ignored."""
        md = "**Bold"
        html = self.parser.parse_string(md)
        self.assertIn("**Bold", html)

    def test_unicode_content(self):
        """Test rendering of Unicode content."""
        md = "# Unicode 😊 🚀"
        html = self.parser.parse_string(md)
        self.assertIn("Unicode 😊 🚀", html)

    def test_line_ending_normalization(self):
        """Test that different line endings are normalized."""
        md = "# Heading\r\n\r\nParagraph\rLine"
        html = self.parser.parse_string(md)
        self.assertIn("<h1>Heading</h1>", html)

    def test_parse_batch_with_valid_and_invalid_file(self):
        """Test batch parsing with one valid file and one invalid path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            good_file = os.path.join(tmpdir, "good.md")
            bad_file = os.path.join(tmpdir, "bad.md")
            with open(good_file, "w", encoding="utf-8") as f:
                f.write("# Good")
            os.mkdir(bad_file)
            result = self.parser.parse_batch([good_file, bad_file])
            self.assertIn(good_file, result)
            self.assertIn(bad_file, result)
            self.assertIsInstance(result[bad_file], Exception)

    def test_parse_file_with_binary_detection(self):
        """Test that binary files raise a MarkdownParseError."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b'\x00\x01\x02')
            f.close()
            with self.assertRaises(MarkdownParseError):
                self.parser.parse_file(f.name)
            os.remove(f.name)

    def test_file_too_large(self):
        """Test that oversized files raise a MarkdownParseError."""
        parser = MarkdownParser(config={"max_file_size": 10})
        with tempfile.NamedTemporaryFile(delete=False, mode="w") as f:
            f.write("A" * 100)
            f.close()
            with self.assertRaises(MarkdownParseError):
                parser.parse_file(f.name)
            os.remove(f.name)

    def test_convert_markdown_to_html_output_file_created(self):
        """Test that the output is created and contains expected content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            md_path = os.path.join(tmpdir, "test.md")
            html_path = os.path.join(tmpdir, "test.html")
            with open(md_path, "w", encoding="utf-8") as f:
                f.write("# Title")
            result = convert_markdown_to_html(md_path, html_path)
            self.assertTrue(os.path.exists(result))
            with open(result, "r", encoding="utf-8") as f:
                self.assertIn("<h1>Title</h1>", f.read())

    def test_custom_indent_size(self):
        """Test that custom indentation settings are applied."""
        parser = MarkdownParser(config={"indent_size": 2})
        html = parser.parse_string("# Title")
        self.assertIn("<h1>Title</h1>", html)

    def test_header_with_inline_formatting(self):
        """Test that headers support inline bold and italic formatting."""
        html = self.parser.parse_string("## Header with *italic* and **bold**")
        self.assertIn("<em>italic</em>", html)
        self.assertIn("<strong>bold</strong>", html)

    def test_large_number_of_list_items(self):
        """Test parser performance with a large number of list items."""
        md = "\n".join(f"- Item {i}" for i in range(1000))
        html = self.parser.parse_string(md)
        self.assertEqual(html.count("<li>"), 1000)
