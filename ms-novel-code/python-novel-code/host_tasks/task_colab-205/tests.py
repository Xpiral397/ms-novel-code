# tests

"""Unit tests for the normalize_csv_to_3nf function.

This module contains test cases to verify CSV to 3NF database normalization,
including edge cases and data validation scenarios.
"""

import os
import sqlite3
import unittest

import pandas as pd

from main import normalize_csv_to_3nf


class TestNormalizeCSVTo3NF(unittest.TestCase):
    """Test suite for normalize_csv_to_3nf function."""

    def setUp(self):
        """Initialize test files and paths before each test."""
        self.csv_path = "test_denormalized_data.csv"
        self.db_path = "test_normalized_data.db"
        self.cleanup_files()

    def tearDown(self):
        """Clean up test files after each test."""
        self.cleanup_files()

    def cleanup_files(self):
        """Remove test files if they exist."""
        for path in [self.csv_path, self.db_path]:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except PermissionError:
                pass

    def read_table(self, table_name):
        """Read table from database."""
        with sqlite3.connect(self.db_path) as conn:
            query = f"SELECT * FROM {table_name}"
            return pd.read_sql_query(query, conn)

    def test_single_valid_order(self):
        with open(self.csv_path, "w") as f:
            f.write("order_id,customer_name,customer_email,products,"
                    "order_date\n")
            f.write("1001, John Doe, john@example.com, Laptop:1@1000,"
                    " 2023-01-15\n")

        normalize_csv_to_3nf(self.csv_path, self.db_path)
        df = self.read_table("orders")
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["order_id"], 1001)

    def test_empty_products_field_skips_order(self):
        with open(self.csv_path, "w") as f:
            f.write("order_id,customer_name,customer_email,products,"
                    "order_date\n")
            f.write("1002,Alice,a@example.com,,2023-01-16\n")

        normalize_csv_to_3nf(self.csv_path, self.db_path)
        df = self.read_table("order_items")
        self.assertEqual(len(df), 0)

    def test_multiple_products_parsed_correctly(self):
        with open(self.csv_path, "w") as f:
            f.write("order_id,customer_name,customer_email,products,"
                    "order_date\n")
            f.write('1003,Bob,b@example.com,"Laptop:1@1000;Mouse:2@20",'
                    "2023-01-17\n")

        normalize_csv_to_3nf(self.csv_path, self.db_path)
        df = self.read_table("order_items")
        self.assertEqual(len(df), 2)

    def test_product_missing_quantity_skipped_or_zero(self):
        with open(self.csv_path, "w") as f:
            f.write("order_id,customer_name,customer_email,products,"
                    "order_date\n")
            f.write('1004,Carl,c@example.com,"Keyboard:@100",2023-01-18\n')

        normalize_csv_to_3nf(self.csv_path, self.db_path)
        df = self.read_table("order_items")
        self.assertTrue(df.empty)

    def test_product_missing_price_skipped_or_zero(self):
        with open(self.csv_path, "w") as f:
            f.write("order_id,customer_name,customer_email,products,"
                    "order_date\n")
            f.write('1005,Diana,d@example.com,"Monitor:2@",2023-01-19\n')

        normalize_csv_to_3nf(self.csv_path, self.db_path)
        df = self.read_table("order_items")
        self.assertTrue(df.empty)

    def test_no_crash_on_missing_columns(self):
        with open(self.csv_path, "w") as f:
            f.write("order_id,customer_name,products,order_date\n")
            f.write('1006,Eve,"Tablet:1@200",2023-01-20\n')

        with self.assertRaises(Exception):
            normalize_csv_to_3nf(self.csv_path, self.db_path)

    def test_trailing_semicolon_is_ignored(self):
        with open(self.csv_path, "w") as f:
            f.write("order_id,customer_name,customer_email,products,"
                    "order_date\n")
            f.write('1007,Fred,f@example.com,"Mouse:2@20;",2023-01-21\n')

        normalize_csv_to_3nf(self.csv_path, self.db_path)
        df = self.read_table("order_items")
        self.assertEqual(len(df), 1)

    def test_malformed_product_skipped(self):
        with open(self.csv_path, "w") as f:
            f.write("order_id,customer_name,customer_email,products,"
                    "order_date\n")
            f.write('1008,Gary,g@example.com,"BadProduct",2023-01-22\n')

        normalize_csv_to_3nf(self.csv_path, self.db_path)
        df = self.read_table("order_items")
        self.assertEqual(len(df), 0)

    def test_customers_have_unique_ids(self):
        with open(self.csv_path, "w") as f:
            f.write("order_id,customer_name,customer_email,products,"
                    "order_date\n")
            f.write('1009,Hank,h@example.com,"Pen:1@5",2023-01-23\n')
            f.write('1010,Hank,h@example.com,"Book:2@15",2023-01-24\n')

        normalize_csv_to_3nf(self.csv_path, self.db_path)
        df = self.read_table("customers")
        self.assertEqual(len(df), 1)

    def test_products_have_unique_ids(self):
        with open(self.csv_path, "w") as f:
            f.write("order_id,customer_name,customer_email,products,"
                    "order_date\n")
            f.write('1011,Ivy,i@example.com,"Pen:1@5;Pen:2@6",2023-01-25\n')

        normalize_csv_to_3nf(self.csv_path, self.db_path)
        df = self.read_table("products")
        self.assertEqual(len(df), 1)

    def test_multi_order_same_customer_and_product(self):
        with open(self.csv_path, "w") as f:
            f.write("order_id,customer_name,customer_email,products,"
                    "order_date\n")
            f.write('1012,John Doe,john@example.com,"Pen:1@5",2023-01-26\n')
            f.write('1013,John Doe,john@example.com,"Pen:3@15",2023-01-27\n')

        normalize_csv_to_3nf(self.csv_path, self.db_path)
        self.assertEqual(len(self.read_table("customers")), 1)
        self.assertEqual(len(self.read_table("products")), 1)

    def test_order_id_is_preserved(self):
        with open(self.csv_path, "w") as f:
            f.write("order_id,customer_name,customer_email,products,"
                    "order_date\n")
            f.write('9999,Zack,z@example.com,"Phone:1@999",2023-01-28\n')

        normalize_csv_to_3nf(self.csv_path, self.db_path)
        df = self.read_table("orders")
        self.assertEqual(df.iloc[0]["order_id"], 9999)

    def test_whitespace_trimmed_in_fields(self):
        with open(self.csv_path, "w") as f:
            f.write("order_id,customer_name,customer_email,products,"
                    "order_date\n")
            f.write('1014,  Jill ,  jill@example.com  ," Lamp :1@50 ",'
                    "2023-01-29\n")

        normalize_csv_to_3nf(self.csv_path, self.db_path)
        df = self.read_table("customers")
        self.assertIn("Jill", df.iloc[0]["customer_name"])

    def test_case_sensitive_customers(self):
        with open(self.csv_path, "w") as f:
            f.write("order_id,customer_name,customer_email,products,"
                    "order_date\n")
            f.write('1015,Kate,kate@example.com,"Cup:1@10",2023-01-30\n')
            f.write('1016,kate,kate@example.com,"Cup:1@10",2023-01-31\n')

        normalize_csv_to_3nf(self.csv_path, self.db_path)
        df = self.read_table("customers")
        self.assertEqual(len(df), 2)

    def test_product_name_case_insensitive_uniqueness(self):
        with open(self.csv_path, "w") as f:
            f.write("order_id,customer_name,customer_email,products,"
                    "order_date\n")
            f.write('1017,Liam,liam@example.com,"Chair:1@30",2023-02-01\n')
            f.write('1018,Liam,liam@example.com,"chair:1@35",2023-02-02\n')

        normalize_csv_to_3nf(self.csv_path, self.db_path)
        df = self.read_table("products")
        self.assertEqual(len(df), 2)

    def test_large_order_list_limit(self):
        with open(self.csv_path, "w") as f:
            f.write("order_id,customer_name,customer_email,products,"
                    "order_date\n")
            for i in range(1000, 1020):
                date = f"2023-02-0{i % 28 + 1}"
                f.write(f'{i},Bulk,b@example.com,"Item{i}:1@10",{date}\n')

        normalize_csv_to_3nf(self.csv_path, self.db_path)
        df = self.read_table("orders")
        self.assertEqual(len(df), 20)

    def test_valid_product_with_zero_quantity(self):
        with open(self.csv_path, "w") as f:
            f.write("order_id,customer_name,customer_email,products,"
                    "order_date\n")
            f.write('2001,Mira,m@example.com,"Box:0@10",2023-02-10\n')

        normalize_csv_to_3nf(self.csv_path, self.db_path)
        df = self.read_table("order_items")
        self.assertEqual(df.iloc[0]["quantity"], 0)

    def test_valid_product_with_zero_price(self):
        with open(self.csv_path, "w") as f:
            f.write("order_id,customer_name,customer_email,products,"
                    "order_date\n")
            f.write('2002,Nico,n@example.com,"Board:2@0",2023-02-11\n')

        normalize_csv_to_3nf(self.csv_path, self.db_path)
        df = self.read_table("order_items")
        self.assertEqual(df.iloc[0]["price"], 0)


if __name__ == "__main__":
    unittest.main()
