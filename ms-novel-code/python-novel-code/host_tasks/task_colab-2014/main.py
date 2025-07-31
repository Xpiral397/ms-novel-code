
"""CSVTransformer: A Python class for transforming CSV files into JSON objects
with schema mapping, type enforcement, and mode-based output formatting."""

import csv
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Union

try:
    from dateutil.parser import parse as iso_parse
except ImportError:
    iso_parse = None


class CSVTransformer:
    """
    A class to transform CSV files into JSON objects with schema mapping,
    type enforcement, and mode-based output formatting.

    Supports 'flat', 'grouped', and 'nested' modes with error handling
    strategies and constraints on input size and structure.
    """

    MAX_COLUMNS = 100
    MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB
    MAX_NESTING_DEPTH = 5

    def __init__(
        self,
        schema: Dict[str, Dict],
        mode: str = "flat",
        group_by: Optional[str] = None,
        delimiter: str = ",",
        on_error: str = "raise",
    ):
        """
        Initialize the transformer.

        Args:
            schema (Dict[str, Dict]): Mapping of CSV fields to output fields
                and expected types.
            mode (str): One of "flat", "grouped", "nested".
            group_by (Optional[str]): Field name to group by (for 'grouped' mode).
            delimiter (str): CSV delimiter character.
            on_error (str): Error handling mode: "raise", "skip", or "log".

        Raises:
            ValueError: If `mode` or `on_error` is invalid, or if required
                parameters are missing.
        """
        valid_modes = {"flat", "grouped", "nested"}
        if mode not in valid_modes:
            raise ValueError(f"Invalid mode '{mode}'. Must be one of {valid_modes}.")

        if on_error not in {"raise", "skip", "log"}:
            raise ValueError("on_error must be one of 'raise', 'skip', or 'log'.")

        if mode == "grouped" and not group_by:
            raise ValueError("`group_by` must be provided when mode is 'grouped'.")

        self.schema = schema
        self.mode = mode
        self.group_by = group_by
        self.delimiter = delimiter
        self.on_error = on_error

        self._validate_schema()

    def _validate_schema(self):
        """
        Validate the schema before processing.

        Ensures target_field and type presence, nesting depth limits,
        and no duplicate target_field paths.

        Raises:
            ValueError: If schema is invalid.
        """
        target_paths = set()
        for field, mapping in self.schema.items():
            if "target_field" not in mapping or "type" not in mapping:
                raise ValueError(
                    f"Schema mapping for '{field}' must include "
                    "'target_field' and 'type'."
                )
            path = mapping["target_field"].split(".")
            if len(path) > self.MAX_NESTING_DEPTH:
                raise ValueError(
                    f"Nested target_field '{mapping['target_field']}' exceeds "
                    f"max depth {self.MAX_NESTING_DEPTH}."
                )
            if mapping["target_field"] in target_paths:
                raise ValueError(
                    f"Duplicate target_field '{mapping['target_field']}' in schema."
                )
            target_paths.add(mapping["target_field"])

    def _check_file_constraints(self, file_path: str):
        """
        Check file size and column count constraints.

        Args:
            file_path (str): Path to the CSV file.

        Raises:
            ValueError: If file size or column count exceeds limits.
        """
        file_size = os.path.getsize(file_path)
        if file_size > self.MAX_FILE_SIZE_BYTES:
            raise ValueError(
                f"CSV file size {file_size} exceeds maximum allowed "
                f"{self.MAX_FILE_SIZE_BYTES} bytes."
            )

        with open(file_path, newline="", encoding="utf-8") as csvfile:
            reader = csv.reader(csvfile, delimiter=self.delimiter)
            try:
                header = next(reader)
            except StopIteration:
                # Empty file: no columns
                return
            if len(header) > self.MAX_COLUMNS:
                raise ValueError(
                    f"CSV has {len(header)} columns which exceeds the max "
                    f"allowed {self.MAX_COLUMNS}."
                )

    def transform(self, csv_path: str) -> Union[List[Dict], Dict[str, List[Dict]]]:
        """
        Transform the CSV file content to JSON object(s) per configuration.

        Returns flattened dicts for 'flat' mode,
        nested dicts for 'nested' mode,
        and grouped dict for 'grouped' mode.

        Args:
            csv_path (str): Path to the CSV file.

        Returns:
            Union[List[Dict], Dict[str, List[Dict]]]: Transformed JSON data.

        Raises:
            FileNotFoundError: If the CSV file does not exist.
            ValueError: If file constraints or schema validation fail.
        """
        self._check_file_constraints(csv_path)

        json_output = []

        try:
            with open(csv_path, newline="", encoding="utf-8") as csvfile:
                csv_reader = csv.DictReader(csvfile, delimiter=self.delimiter)
                if csv_reader.fieldnames is None:
                    return [] if self.mode != "grouped" else {}

                missing_cols = [
                    col for col in self.schema if col not in csv_reader.fieldnames
                ]
                if missing_cols:
                    msg = (
                        f"CSV file is missing required columns: {missing_cols}."
                    )
                    if self.on_error == "raise":
                        raise ValueError(msg)
                    elif self.on_error == "log":
                        logging.error(msg)

                for row in csv_reader:
                    try:
                        transformed_row = self._process_row(row)
                        if transformed_row is not None:
                            if self.mode == "flat":
                                transformed_row = self._flatten_dict(transformed_row)
                            json_output.append(transformed_row)
                    except Exception as e:
                        if self.on_error == "raise":
                            raise
                        elif self.on_error == "log":
                            logging.error(f"Error processing row {row}: {e}")
                        if self.on_error in {"skip", "log"}:
                            continue

            if self.mode == "grouped":
                return self._group_rows(json_output)
            else:
                return json_output

        except FileNotFoundError as e:
            raise FileNotFoundError(f"CSV file not found at path '{csv_path}'.") from e

    def _process_row(self, row: Dict[str, str]) -> Optional[Dict]:
        """
        Process a single CSV row and apply schema mapping and type casting.

        Args:
            row (Dict[str, str]): A CSV row dictionary.

        Returns:
            Optional[Dict]: Transformed row or None if invalid/skipped.

        Raises:
            KeyError: If required field is missing and on_error='raise'.
            ValueError, TypeError: If type casting fails and on_error='raise'.
        """
        transformed_row = {}

        for field_name, mapping in self.schema.items():
            raw_value = row.get(field_name)

            if raw_value is None or raw_value.strip() == "":
                if self.on_error == "raise":
                    raise KeyError(f"Missing or empty column '{field_name}' in row.")
                else:
                    continue

            raw_value = raw_value.strip()
            try:
                casted_value = self._cast_type(raw_value, mapping["type"])
                self._construct_mapped_field(
                    transformed_row, mapping["target_field"], casted_value
                )
            except (ValueError, TypeError) as e:
                if self.on_error == "raise":
                    raise
                elif self.on_error == "log":
                    logging.error(f"Type casting error for row {row}: {e}")
                continue

        if not transformed_row:
            return None
        return transformed_row

    def _construct_mapped_field(self, base: Dict, field_path: str, value):
        """
        Construct nested dictionaries for dot-separated field paths.

        Args:
            base (Dict): Base dictionary to insert into.
            field_path (str): Dot-separated target field path.
            value: Value to set at the nested path.

        Raises:
            ValueError: If nesting depth exceeds limits.
        """
        parts = field_path.split(".")
        if len(parts) > self.MAX_NESTING_DEPTH:
            raise ValueError(
                f"Field path '{field_path}' exceeds max nesting depth "
                f"of {self.MAX_NESTING_DEPTH}."
            )
        current = base
        for part in parts[:-1]:
            if part not in current or not isinstance(current[part], dict):
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value

    def _cast_type(self, value: str, target_type: type):
        """
        Cast a string value to a target type with robust parsing.

        Args:
            value (str): The input string value.
            target_type (type): Target Python type (int, float, bool, datetime, str).

        Returns:
            The value cast to the target type.

        Raises:
            ValueError, TypeError: If conversion fails.
        """
        if target_type == int:
            return int(value)
        elif target_type == float:
            return float(value)
        elif target_type == bool:
            lower_val = value.lower()
            if lower_val in {"true", "1"}:
                return True
            elif lower_val in {"false", "0"}:
                return False
            else:
                raise ValueError(f"Invalid boolean value '{value}'.")
        elif target_type == datetime:
            if iso_parse:
                try:
                    return iso_parse(value)
                except Exception as e:
                    raise ValueError(
                        f"Invalid ISO8601 datetime value '{value}': {e}"
                    ) from e
            else:
                try:
                    return datetime.fromisoformat(value)
                except Exception as e:
                    raise ValueError(
                        f"Invalid ISO8601 datetime value '{value}': {e}"
                    ) from e
        elif target_type == str:
            return value
        else:
            raise TypeError(f"Unsupported target type '{target_type}'.")

    def _group_rows(self, rows: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Group rows by the group_by field.

        Args:
            rows (List[Dict]): List of transformed rows.

        Returns:
            Dict[str, List[Dict]]: Grouped dictionary.

        Raises:
            ValueError: If group_by field is missing in any row and on_error='raise'.
        """
        grouped = {}
        for row in rows:
            key = self._extract_group_key(row)
            if key is None:
                msg = f"Missing group_by key '{self.group_by}' in row {row}."
                if self.on_error == "raise":
                    raise ValueError(msg)
                elif self.on_error == "log":
                    logging.error(msg)
                continue
            grouped.setdefault(key, []).append(row)
        return grouped

    def _extract_group_key(self, row: Dict) -> Optional[str]:
        """
        Extract the group_by key from a possibly nested row.

        Args:
            row (Dict): Transformed row.

        Returns:
            Optional[str]: Group key or None if not found.
        """
        parts = self.group_by.split(".")
        current = row
        for part in parts:
            if not isinstance(current, dict) or part not in current:
                return None
            current = current[part]
        return str(current) if current is not None else None

    def _flatten_dict(self, d: Dict, parent_key: str = "", sep: str = ".") -> Dict:
        """
        Flatten a nested dictionary.

        Args:
            d (Dict): Dictionary to flatten.
            parent_key (str): Prefix key for recursion.
            sep (str): Separator between keys.

        Returns:
            Dict: Flattened dictionary with dot-separated keys.
        """
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

