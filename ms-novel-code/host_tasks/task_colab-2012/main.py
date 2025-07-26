
import csv
from functools import reduce
from typing import List, Dict, Any, Callable, Tuple


def _safe_apply_filter(row: Dict[str, Any], column: str, func: Callable) -> bool:
    """
    Safely applies a filter function to a single row.
    Returns False if the column doesn't exist or if the function raises an exception.
    """
    if column not in row:
        return False
    try:
        return func(row[column])
    except Exception:
        # Skip the row if any error occurs during filter function execution
        return False


def _safe_apply_map(row: Dict[str, Any], new_col_name: str, func: Callable) -> Dict[str, Any] | None:
    """
    Safely applies a map function to a single row.
    Returns the updated row, or None if the function raises an exception.
    """
    try:
        new_value = func(row)
        return {**row, new_col_name: new_value}
    except Exception:
        # Skip the row by returning None if any error occurs
        return None


def process_csv_pipeline(file_path: str, operations: List[Tuple]) -> Any:
    """
    Processes data from a CSV file using a functional pipeline of operations.

    Args:
        file_path: The path to the input CSV file.
        operations: A list of tuples, each defining a processing step
                    ('filter', 'map', or 'reduce').

    Returns:
        The final processed data, which can be a list of dictionaries or a single
        aggregated value if a 'reduce' operation is the final step.

    Raises:
        FileNotFoundError: If the specified file_path does not exist.
        ValueError: If an operation tuple is malformed or an unknown operation
                    type is provided.
    """
    try:
        with open(file_path, mode='r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            data: List[Dict[str, Any]] = list(reader)
    except FileNotFoundError:
        raise FileNotFoundError(f"The file {file_path} does not exist.")

    # Process each operation in the pipeline sequentially
    for operation in operations:
        if not isinstance(operation, tuple) or not operation:
            raise ValueError(
                "Invalid operation format: Each operation must be a non-empty tuple.")

        op_type = operation[0]

        if op_type == 'filter':
            if len(operation) != 3:
                raise ValueError(
                    "Filter operation requires 3 elements: ('filter', column_name, filter_func).")
            _, column_name, filter_func = operation
            data = [row for row in data if _safe_apply_filter(
                row, column_name, filter_func)]

        elif op_type == 'map':
            if len(operation) != 3:
                raise ValueError(
                    "Map operation requires 3 elements: ('map', new_column_name, map_func).")
            _, new_column_name, map_func = operation

            # Process map row by row, skipping any that cause errors
            mapped_data = []
            for row in data:
                new_row = _safe_apply_map(row, new_column_name, map_func)
                if new_row is not None:
                    mapped_data.append(new_row)
            data = mapped_data

        elif op_type == 'reduce':
            if len(operation) != 3:
                raise ValueError(
                    "Reduce operation requires 3 elements: ('reduce', reduce_func, initial_value).")
            _, reduce_func, initial_value = operation
            # The reduce operation is terminal and returns the final aggregated value
            return reduce(reduce_func, data, initial_value)

        else:
            raise ValueError(
                f"Unknown operation type: '{op_type}'. Must be 'filter', 'map', or 'reduce'.")

    return data
