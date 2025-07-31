
"""
Flask RESTful API to transform uploaded CSV files into flat or nested
JSON format. The transformation logic is encapsulated in helper functions
within this module to preserve modularity.
"""

from flask import Flask, request, jsonify
import csv
import io
from typing import List, Dict, Any, IO
from werkzeug.exceptions import RequestEntityTooLarge

app = Flask(__name__)

# Enforce 2MB upload limit
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024


@app.route("/transform", methods=["POST"])
def transform():
    """
    Flask route to accept a CSV file and return a JSON response.
    Validates input, delegates to transformation logic, and returns a
    structured JSON result.
    """
    if 'file' not in request.files or 'format' not in request.form:
        return _error_response(
            "Missing 'file' or 'format' parameter.", 400
        )

    uploaded_file = request.files['file']
    format_type = request.form['format']

    try:
        file_stream = io.TextIOWrapper(
            uploaded_file.stream, encoding='utf-8'
        )
        data = parse_csv(file_stream, format_type)
        return jsonify(success=True, data=data, error=None)

    except UnicodeDecodeError:
        return _error_response("CSV file must be UTF-8 encoded.", 400)

    except ValueError as ve:
        return _error_response(str(ve), 400)

    except RequestEntityTooLarge:
        return _error_response("File too large, must be under 2MB.", 413)

    except Exception:
        return _error_response(
            "An unexpected error occurred while processing the file.", 500
        )


def parse_csv(file_stream: IO[str], format_type: str) -> List[Dict[str, Any]]:
    """
    Parse the uploaded CSV file and return a list of JSON records.

    :param file_stream: A text stream of the CSV file.
    :param format_type: 'flat' or 'nested' to specify transformation style.
    :return: List of dictionaries representing JSON rows.
    :raises ValueError: If the format_type is invalid or CSV parsing fails.
    """
    if format_type not in ('flat', 'nested'):
        raise ValueError("Invalid format_type. Must be 'flat' or 'nested'.")

    try:
        reader = csv.DictReader(file_stream)

        if not reader.fieldnames:
            raise ValueError("CSV file is empty or missing headers.")

        if len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError("CSV headers contain duplicates.")

        _validate_headers(reader.fieldnames)

        data = []

        for row_num, row in enumerate(reader, start=1):
            if None in row:
                raise ValueError(
                    f"Row {row_num} has more columns than headers."
                )

            if len(row) != len(reader.fieldnames):
                raise ValueError(
                    f"Inconsistent column count in row {row_num}."
                )

            str_row = {k: str(v) for k, v in row.items()}

            if format_type == 'flat':
                data.append(str_row)
            else:
                nested = _to_nested_dict(str_row)
                data.append(nested)

        return data

    except csv.Error as e:
        raise ValueError(f"CSV parsing error: {str(e)}") from e


def _validate_headers(headers: List[str]) -> None:
    """
    Validate that headers are non-empty, legal, and non-conflicting.

    :param headers: List of header strings from the CSV file.
    :raises ValueError: If headers are invalid or conflicting.
    """
    seen = set()

    for header in headers:
        if not header or header.strip() == "":
            raise ValueError("Empty header found.")

        parts = header.split('.')
        path = []

        for part in parts:
            path.append(part)
            path_str = '.'.join(path)

            if path_str in seen:
                continue

            if any(h == path_str for h in headers if h != header):
                raise ValueError(
                    f"Conflicting nested key: '{path_str}' conflicts with "
                    f"another header."
                )

            seen.add(path_str)


def _to_nested_dict(flat_dict: Dict[str, str]) -> Dict[str, Any]:
    """
    Convert a flat dictionary with dotted keys into a nested dictionary.

    :param flat_dict: Dictionary with possibly dotted keys.
    :return: Nested dictionary.
    :raises ValueError: If there are key conflicts in nesting.
    """
    nested = {}

    for key, value in flat_dict.items():
        parts = key.split('.')
        sub_dict = nested

        for part in parts[:-1]:
            if part not in sub_dict:
                sub_dict[part] = {}
            elif not isinstance(sub_dict[part], dict):
                raise ValueError(
                    f"Key conflict while nesting: '{key}' cannot be created."
                )
            sub_dict = sub_dict[part]

        if parts[-1] in sub_dict:
            raise ValueError(
                f"Duplicate nested key detected: '{key}'"
            )

        sub_dict[parts[-1]] = value

    return nested


def _error_response(message: str, status_code: int):
    """
    Helper function to format error JSON responses.

    :param message: Error message to return.
    :param status_code: HTTP status code.
    :return: Flask response with JSON body.
    """
    return (
        jsonify(success=False, data=None, error=message),
        status_code
    )


if __name__ == "__main__":
    app.run(debug=True)

