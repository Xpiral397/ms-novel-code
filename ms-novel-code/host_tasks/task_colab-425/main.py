
"""
Advanced Markdown to HTML Parser Module

This module provides a sophisticated Markdown to HTML conversion system that
handles complex nested structures, multiple file processing, and provides
extensible parsing capabilities.
"""

import os
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union


class MarkdownParseError(Exception):
    """Custom exception for Markdown parsing errors."""
    pass


class MarkdownParser:
    """
    Advanced Markdown to HTML parser with support for nested structures
    and inline formatting combinations.
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize the parser with optional configuration.

        Args:
            config (dict, optional): Configuration options for parsing behavior
                - max_file_size: Maximum file size in bytes (default: 100MB)
                - max_nesting_depth: Maximum list nesting depth (default: 10)
                - enable_logging: Enable debug logging (default: False)
                - indent_size: HTML indentation size (default: 4)
        """
        self.config = config if config else {}
        self.max_file_size = self.config.get('max_file_size', 100 * 1024 * 1024)
        self.max_nesting_depth = self.config.get('max_nesting_depth', 10)
        self.indent_size = self.config.get('indent_size', 4)

        if self.config.get('enable_logging', False):
            logging.basicConfig(level=logging.DEBUG)

        self.logger = logging.getLogger(__name__)

    def parse_file(self, input_path: str, output_path: Optional[str] = None) -> str:
        """
        Parse a single Markdown file and convert to HTML.

        Args:
            input_path (str): Path to the input Markdown file
            output_path (str, optional): Path for output HTML file

        Returns:
            str: Generated HTML content

        Raises:
            FileNotFoundError: If input file doesn't exist
            PermissionError: If unable to write output file
            MarkdownParseError: If parsing fails critically
        """
        # Validate input file exists
        if not os.path.isfile(input_path):
            raise FileNotFoundError(f"Input file '{input_path}' not found")

        # Check file size constraint
        file_size = os.path.getsize(input_path)
        if file_size > self.max_file_size:
            raise MarkdownParseError(
                f"File size {file_size} exceeds maximum allowed size "
                f"{self.max_file_size}"
            )

        # Check if file is binary
        if self._is_binary_file(input_path):
            raise MarkdownParseError(
                f"File '{input_path}' appears to be binary, not text"
            )

        try:
            # Read the content with UTF-8 encoding
            with open(input_path, 'r', encoding='utf-8', errors='replace') as file:
                markdown_content = file.read()
        except UnicodeDecodeError as e:
            raise MarkdownParseError(f"Unicode decode error: {e}")
        except IOError as e:
            raise PermissionError(f"Cannot read file '{input_path}': {e}")

        # Parse the content
        html_content = self.parse_string(markdown_content)

        # Write output if output path is specified
        if output_path:
            try:
                # Create output directory if it has a directory component
                output_dir = os.path.dirname(output_path)
                if output_dir:  # Only create directory if there's a directory part
                    os.makedirs(output_dir, exist_ok=True)

                with open(output_path, 'w', encoding='utf-8') as file:
                    file.write(html_content)
            except IOError as e:
                raise PermissionError(f"Cannot write to '{output_path}': {e}") from e

        self.logger.info(f"Successfully parsed '{input_path}'")
        return html_content

    def parse_batch(self, input_files: List[str],
                   output_directory: Optional[str] = None) -> Dict[str, Union[str, Exception]]:
        """
        Process multiple Markdown files in batch.

        Args:
            input_files (list): List of input file paths
            output_directory (str, optional): Directory for output files

        Returns:
            dict: Mapping of input files to output results or error messages
        """
        results = {}

        # Create output directory if specified
        if output_directory:
            os.makedirs(output_directory, exist_ok=True)

        for input_file in input_files:
            try:
                # Determine output path
                if output_directory:
                    output_filename = f"{Path(input_file).stem}.html"
                    output_path = os.path.join(output_directory, output_filename)
                else:
                    # Place output file alongside input file
                    input_path = Path(input_file)
                    output_path = str(input_path.parent / f"{input_path.stem}.html")

                html_content = self.parse_file(input_file, output_path)
                results[input_file] = html_content

            except (FileNotFoundError, PermissionError, MarkdownParseError) as e:
                results[input_file] = e
                self.logger.error(f"Error processing '{input_file}': {e}")
            except Exception as e:
                results[input_file] = MarkdownParseError(f"Unexpected error: {e}")
                self.logger.error(f"Unexpected error processing '{input_file}': {e}")

        return results

    def parse_string(self, markdown_content: str) -> str:
        """
        Parse Markdown content from string.

        Args:
            markdown_content (str): Markdown content to parse

        Returns:
            str: Generated HTML content
        """
        if not markdown_content.strip():
            return self._generate_empty_html()

        lines = self._normalize_line_endings(markdown_content).split('\n')
        html_lines = []

        # Add HTML document structure
        html_lines.extend([
            '<!DOCTYPE html>',
            '<html>',
            '<head>',
            '    <meta charset="UTF-8">',
            '    <title>Converted Markdown</title>',
            '</head>',
            '<body>'
        ])

        # Parse content
        body_content = self._parse_content(lines)
        html_lines.extend(body_content)

        # Close HTML structure
        html_lines.extend([
            '</body>',
            '</html>'
        ])

        return '\n'.join(html_lines)

    def _parse_content(self, lines: List[str]) -> List[str]:
        """
        Parse the main content of the markdown.

        Args:
            lines (list): List of markdown lines

        Returns:
            list: List of HTML lines with proper indentation
        """
        html_lines = []
        list_stack = []
        in_paragraph = False
        paragraph_lines = []

        i = 0
        while i < len(lines):
            line = lines[i]
            line = line.rstrip()

            # Handle empty lines
            if not line:
                if in_paragraph:
                    self._close_paragraph(paragraph_lines, html_lines)
                    in_paragraph = False
                    paragraph_lines = []
                i += 1
                continue

            # Check for headers
            header_match = re.match(r'^(#{1,6})\s+(.*)', line)
            if header_match:
                if in_paragraph:
                    self._close_paragraph(paragraph_lines, html_lines)
                    in_paragraph = False
                    paragraph_lines = []

                self._close_all_lists(list_stack, html_lines)
                level = len(header_match.group(1))
                content = self._parse_inline_formatting(header_match.group(2))
                html_lines.append(f'    <h{level}>{content}</h{level}>')
                i += 1
                continue

            # Check for lists (unordered and ordered)
            list_match = self._match_list_item(line)
            if list_match:
                if in_paragraph:
                    self._close_paragraph(paragraph_lines, html_lines)
                    in_paragraph = False
                    paragraph_lines = []

                indent_level, list_type, content = list_match

                # Handle nested lists
                i = self._handle_list_item(
                    lines, i, indent_level, list_type, content,
                    list_stack, html_lines
                )
                continue

            # Regular paragraph text
            if list_stack:
                self._close_all_lists(list_stack, html_lines)

            if not in_paragraph:
                in_paragraph = True
                paragraph_lines = []

            paragraph_lines.append(line)
            i += 1

        # Close any remaining open elements
        if in_paragraph:
            self._close_paragraph(paragraph_lines, html_lines)

        self._close_all_lists(list_stack, html_lines)

        return html_lines

    def _match_list_item(self, line: str) -> Optional[tuple]:
        """
        Match and extract list item information.

        Args:
            line (str): Line to check for list item pattern

        Returns:
            tuple: (indent_level, list_type, content) or None
        """
        # Calculate indentation
        indent_level = len(line) - len(line.lstrip())
        stripped_line = line.lstrip()

        # Check for unordered list
        ul_match = re.match(r'^[-*]\s+(.*)', stripped_line)
        if ul_match:
            return (indent_level, 'ul', ul_match.group(1))

        # Check for ordered list
        ol_match = re.match(r'^\d+\.\s+(.*)', stripped_line)
        if ol_match:
            return (indent_level, 'ol', ol_match.group(1))

        return None

    def _handle_list_item(self, lines: List[str], start_index: int,
                         indent_level: int, list_type: str, content: str,
                         list_stack: List[tuple], html_lines: List[str]) -> int:
        """
        Handle a list item and its potential nested content.

        Args:
            lines (list): All markdown lines
            start_index (int): Current line index
            indent_level (int): Indentation level of the list item
            list_type (str): Type of list ('ul' or 'ol')
            content (str): Content of the list item
            list_stack (list): Stack tracking open lists
            html_lines (list): HTML output lines

        Returns:
            int: Next line index to process
        """
        # Adjust list stack based on indentation
        self._adjust_list_stack(indent_level, list_type, list_stack, html_lines)

        # Parse the list item content
        parsed_content = self._parse_inline_formatting(content)

        # Check if this item has nested content
        next_index = start_index + 1
        nested_content = []

        while next_index < len(lines):
            next_line = lines[next_index]
            if not next_line.strip():
                next_index += 1
                continue

            next_indent = len(next_line) - len(next_line.lstrip())

            # If next line is more indented, it's nested content
            if next_indent > indent_level:
                nested_content.append(next_line)
                next_index += 1
            else:
                break

        # Generate list item HTML
        current_indent = '    ' * (len(list_stack) + 1)

        if nested_content:
            html_lines.append(f'{current_indent}<li>{parsed_content}')

            # Parse nested content
            nested_html = self._parse_content(nested_content)

            # Add nested HTML with proper indentation
            for nested_line in nested_html:
                if nested_line.strip():
                    html_lines.append(f'    {nested_line}')

            html_lines.append(f'{current_indent}</li>')
        else:
            html_lines.append(f'{current_indent}<li>{parsed_content}</li>')

        return next_index

    def _adjust_list_stack(self, indent_level: int, list_type: str,
                          list_stack: List[tuple], html_lines: List[str]):
        """
        Adjust the list stack based on current indentation level.

        Args:
            indent_level (int): Current indentation level
            list_type (str): Type of list ('ul' or 'ol')
            list_stack (list): Stack of open lists
            html_lines (list): HTML output lines
        """
        # Close lists that are at deeper or equal indentation
        while (list_stack and
               list_stack[-1][0] >= indent_level):
            _, old_type = list_stack.pop()
            current_indent = '    ' * (len(list_stack) + 1)
            html_lines.append(f'{current_indent}</{old_type}>')

        # Check if we need to start a new list
        if (not list_stack or
            list_stack[-1][0] < indent_level or
            list_stack[-1][1] != list_type):

            list_stack.append((indent_level, list_type))
            current_indent = '    ' * len(list_stack)
            html_lines.append(f'{current_indent}<{list_type}>')

    def _close_all_lists(self, list_stack: List[tuple], html_lines: List[str]):
        """
        Close all open lists in the stack.

        Args:
            list_stack (list): Stack of open lists
            html_lines (list): HTML output lines
        """
        while list_stack:
            _, list_type = list_stack.pop()
            current_indent = '    ' * (len(list_stack) + 1)
            html_lines.append(f'{current_indent}</{list_type}>')

    def _close_paragraph(self, paragraph_lines: List[str], html_lines: List[str]):
        """
        Close a paragraph and add it to HTML output.

        Args:
            paragraph_lines (list): Lines of the paragraph
            html_lines (list): HTML output lines
        """
        if paragraph_lines:
            content = ' '.join(paragraph_lines)
            parsed_content = self._parse_inline_formatting(content)
            html_lines.append(f'    <p>{parsed_content}</p>')

    def _parse_inline_formatting(self, text: str) -> str:
        """
        Parse and convert inline Markdown syntax to HTML.

        Args:
            text (str): Text to parse for inline formatting

        Returns:
            str: Text with inline formatting converted to HTML
        """
        # Escape HTML special characters first
        text = self._escape_html(text)

        # Handle links first (they can contain other formatting)
        text = self._parse_links(text)

        # Handle bold text (must come before italic to avoid conflicts)
        text = self._parse_bold(text)

        # Handle italic text
        text = self._parse_italic(text)

        return text

    def _parse_links(self, text: str) -> str:
        """
        Parse markdown links and convert to HTML.

        Args:
            text (str): Text containing potential links

        Returns:
            str: Text with links converted to HTML
        """
        # Handle malformed links gracefully
        def replace_link(match):
            link_text = match.group(1)
            url = match.group(2)

            # Basic URL validation and length check
            if len(url) > 2048:
                return match.group(0)  # Return original if URL too long

            # Parse inline formatting within link text
            formatted_text = self._parse_bold(self._parse_italic(link_text))

            return f'<a href="{url}">{formatted_text}</a>'

        # Match [text](url) pattern with error recovery
        try:
            text = re.sub(r'\[([^\]]*)\]\(([^)]*)\)', replace_link, text)
        except Exception:
            # If regex fails, return original text
            pass

        return text

    def _parse_bold(self, text: str) -> str:
        """
        Parse bold formatting and convert to HTML.

        Args:
            text (str): Text containing potential bold formatting

        Returns:
            str: Text with bold formatting converted to HTML
        """
        # Handle nested and malformed bold markers gracefully
        def replace_bold(match):
            content = match.group(1)
            if content.strip():  # Only convert non-empty content
                return f'<strong>{content}</strong>'
            return match.group(0)  # Return original if empty

        try:
            # Match **text** but handle unclosed markers gracefully
            text = re.sub(r'\*\*([^*\n]*?)\*\*', replace_bold, text)
        except Exception:
            pass

        return text

    def _parse_italic(self, text: str) -> str:
        """
        Parse italic formatting and convert to HTML.

        Args:
            text (str): Text containing potential italic formatting

        Returns:
            str: Text with italic formatting converted to HTML
        """
        def replace_italic(match):
            content = match.group(1)
            if content.strip():  # Only convert non-empty content
                return f'<em>{content}</em>'
            return match.group(0)  # Return original if empty

        try:
            # Match *text* but avoid matching ** patterns and handle unclosed
            text = re.sub(r'(?<!\*)\*([^*\n]*?)\*(?!\*)', replace_italic, text)
        except Exception:
            pass

        return text

    def _escape_html(self, text: str) -> str:
        """
        Escape HTML special characters in text.

        Args:
            text (str): Text to escape

        Returns:
            str: Text with HTML characters escaped
        """
        html_escape_table = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#x27;',
        }

        for char, escape in html_escape_table.items():
            text = text.replace(char, escape)

        return text

    def _normalize_line_endings(self, content: str) -> str:
        """
        Normalize different line ending conventions.

        Args:
            content (str): Content with potentially mixed line endings

        Returns:
            str: Content with normalized line endings
        """
        # Convert Windows and Mac line endings to Unix
        content = content.replace('\r\n', '\n')
        content = content.replace('\r', '\n')
        return content

    def _is_binary_file(self, file_path: str) -> bool:
        """
        Check if a file is binary by examining its content.

        Args:
            file_path (str): Path to the file to check

        Returns:
            bool: True if file appears to be binary
        """
        try:
            with open(file_path, 'rb') as file:
                chunk = file.read(1024)  # Read first 1KB

            # Check for null bytes (common in binary files)
            if b'\x00' in chunk:
                return True

            # Try to decode as UTF-8
            try:
                chunk.decode('utf-8')
                return False
            except UnicodeDecodeError:
                return True

        except (IOError, OSError):
            return True  # Assume binary if can't read

    def _generate_empty_html(self) -> str:
        """
        Generate HTML structure for empty input.

        Returns:
            str: Basic HTML structure
        """
        return '\n'.join([
            '<!DOCTYPE html>',
            '<html>',
            '<head>',
            '    <meta charset="UTF-8">',
            '    <title>Converted Markdown</title>',
            '</head>',
            '<body>',
            '</body>',
            '</html>'
        ])


def convert_markdown_to_html(input_path: str, output_path: Optional[str] = None,
                           config: Optional[Dict] = None) -> str:
    """
    Convenience function for simple Markdown to HTML conversion.

    Args:
        input_path (str): Path to input Markdown file
        output_path (str, optional): Path for output HTML file
        config (dict, optional): Parser configuration options

    Returns:
        str: Path to generated HTML file

    Raises:
        FileNotFoundError: If input file doesn't exist
        PermissionError: If unable to read/write files
        MarkdownParseError: If parsing fails
    """
    parser = MarkdownParser(config)

    # Generate output path if not provided
    if output_path is None:
        input_file = Path(input_path)
        output_path = str(input_file.parent / f"{input_file.stem}.html")

    # Parse the file
    parser.parse_file(input_path, output_path)

    return output_path

