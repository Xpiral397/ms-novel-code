
"""
Asynchronous CSV processor.

Infers column types and normalizes values.
"""

import asyncio
import aiofiles
import os
import csv
from io import StringIO
from typing import Optional, List


async def infer_column_types(
    file_path: str,
    expected_columns: int
) -> List[str]:
    """Infer data types for each column by examining non-empty values."""
    column_types = ["string"] * expected_columns

    async with aiofiles.open(file_path, mode='r', encoding='utf-8') as infile:
        await infile.readline()
        sample_count = 0
        async for line in infile:
            line = line.strip()
            if not line or sample_count >= 10:
                continue
            items = line.split(',')
            if len(items) != expected_columns:
                continue
            for i, item in enumerate(items):
                item = item.strip()
                if item:
                    try:
                        float(item)
                        column_types[i] = "float"
                    except ValueError:
                        column_types[i] = "string"
            sample_count += 1

    return column_types


async def normalize_value_typed(
    value: str,
    expected_type: str
) -> str:
    """Normalize a single value according to the rules with type awareness."""
    value = value.strip()
    if not value:
        return "0" if expected_type == "float" else ""
    try:
        num = float(value)
        num = max(0, round(num, 3))
        if num == int(num):
            return str(int(num))
        return f"{num:.3f}".rstrip('0').rstrip('.')
    except ValueError:
        return value.upper()


async def process_line_typed(
    line: str,
    expected_columns: int,
    column_types: List[str]
) -> Optional[List[str]]:
    """Process a single line.

    according to normalization rules with type awareness.
    """
    items = line.split(',')
    if len(items) != expected_columns:
        return None

    processed_items = []
    for i, item in enumerate(items):
        expected_type = column_types[i] if i < len(column_types) else "string"
        normalized = await normalize_value_typed(item, expected_type)
        processed_items.append(normalized)

    return processed_items


async def process_file(
    input_path: str,
    output_path: str
) -> None:
    """Process a single CSV file asynchronously."""
    try:
        async with aiofiles.open(
            input_path,
            mode='r',
            encoding='utf-8'
        ) as infile:
            first_line = await infile.readline()
            if not first_line.strip():
                return

            header_items = first_line.strip().split(',')
            expected_columns = len(header_items)
            column_types = await infer_column_types(
                input_path,
                expected_columns
            )

            processed_header = [
                item.strip().upper() for item in header_items
            ]

            async with aiofiles.open(
                output_path,
                mode='w',
                encoding='utf-8',
                newline=''
            ) as outfile:
                output_buffer = StringIO()
                writer = csv.writer(output_buffer)
                writer.writerow(processed_header)
                await outfile.write(output_buffer.getvalue())

                async for line in infile:
                    line = line.strip()
                    if not line:
                        continue

                    processed_row = await process_line_typed(
                        line,
                        expected_columns,
                        column_types
                    )
                    if processed_row:
                        output_buffer = StringIO()
                        writer = csv.writer(output_buffer)
                        writer.writerow(processed_row)
                        await outfile.write(output_buffer.getvalue())

    except Exception as e:
        print(f"Error processing {input_path}: {e}")


async def process_csv_folder(folder_path: str) -> Optional[int]:
    """Process all CSV files in a folder concurrently."""
    try:
        files = [
            f for f in os.listdir(folder_path)
            if f.endswith('.csv')
        ]

        if len(files) != 2:
            return -1

        tasks = []
        for file in files:
            input_path = os.path.join(folder_path, file)
            output_path = os.path.join(
                folder_path,
                f"{os.path.splitext(file)[0]}_output.csv"
            )
            tasks.append(process_file(input_path, output_path))

        await asyncio.gather(*tasks)
        return None

    except OSError:
        return None

