
"""
LogProcessor Module.

This module defines a LogProcessor class that allows incremental reading
and classification of lines appended to a log file. It supports appending
new lines to a text file, reading only newly appended content, and
classifying lines based on predefined patterns.

Each line may belong to multiple categories: INFO, ERROR, WARNING, DATE.
Lines that do not match any of these are classified as OTHER.

Lines are stripped of whitespace before processing. Completely blank
lines are ignored. The last read position is tracked to ensure only
new lines are processed on each call.
"""

import re


class LogProcessor:
    """
    A processor that appends and categorizes new lines to a log file.

    Tracks the last read position and categorizes only newly added
    content on each operation.
    """

    def __init__(self, file_path: str):
        """
        Initialize the processor for the given file path.

        Creates the file if it does not already exist.

        Args:
            file_path (str): Path to the log file.
        """
        self.file_path = file_path
        self.last_offset = 0

        # Ensure the file exists
        with open(self.file_path, 'a', encoding='utf-8'):
            pass

    def append_and_categorize(self, new_lines: list[str]) -> dict:
        """
        Append new lines to the log file and categorize them.

        Appends new lines to the file, reads only the newly written
        lines since the last read, and classifies them into INFO,
        ERROR, WARNING, DATE, or OTHER.

        Returns:
            dict: A dictionary with the following keys:
                  "INFO", "ERROR", "WARNING", "DATE", "OTHER".
                  Each maps to a list of matching lines.
        """
        # Append new lines to the file
        with open(self.file_path, 'a', encoding='utf-8') as file:
            for line in new_lines:
                file.write(line + '\n')

        # Prepare the result dictionary
        result = {
            "INFO": [],
            "ERROR": [],
            "WARNING": [],
            "DATE": [],
            "OTHER": []
        }

        # Read newly appended lines
        with open(self.file_path, 'r', encoding='utf-8') as file:
            file.seek(self.last_offset)
            new_content = file.readlines()
            self.last_offset = file.tell()

        # Regex pattern for ISO 8601 date format YYYY-MM-DD
        date_pattern = re.compile(r'\b\d{4}-\d{2}-\d{2}\b')

        for raw_line in new_content:
            line = raw_line.strip()
            if not line:
                continue

            categorized = False

            if line.startswith("INFO"):
                result["INFO"].append(line)
                categorized = True

            if line.startswith("ERROR"):
                result["ERROR"].append(line)
                categorized = True

            if line.startswith("WARNING"):
                result["WARNING"].append(line)
                categorized = True

            if date_pattern.search(line):
                result["DATE"].append(line)
                categorized = True

            if not categorized:
                result["OTHER"].append(line)

        return result

