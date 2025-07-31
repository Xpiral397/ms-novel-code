
import pandas as pd
import sqlite3
from typing import Tuple, List, Set
import os


def generate_customer_id_map(customers_df: pd.DataFrame) -> pd.DataFrame:
    """Assigns deterministic integer IDs to customers sorted by name and email."""
    customers_df = customers_df.drop_duplicates()
    customers_df = customers_df.sort_values(by=['customer_name', 'customer_email']).reset_index(drop=True)
    customers_df['customer_id'] = customers_df.index + 1
    return customers_df


def generate_product_id_map(products_set: Set[Tuple[str]]) -> pd.DataFrame:
    """Creates a DataFrame of unique products with deterministic product IDs."""
    products_list = sorted(list(products_set), key=lambda x: x[0].lower())
    products_df = pd.DataFrame(products_list, columns=['product_name'])
    products_df['product_id'] = products_df.index + 1
    return products_df


def parse_products_column(df: pd.DataFrame) -> Tuple[List[Tuple[int, str, int, float]], Set[Tuple[str]]]:
    """
    Parses the 'products' column to extract order_items and unique products.

    Returns:
        - A list of (order_id, product_name, quantity, price) tuples
        - A set of unique (product_name,) tuples
    """
    order_items = []
    products_set = set()

    for index, row in df.iterrows():
        order_id = row['order_id']
        products_str = row.get('products', '')
        if pd.isna(products_str) or not isinstance(products_str, str):
            continue

        for item in products_str.split(';'):
            item = item.strip()
            if not item:
                continue

            try:
                name_qty, price = item.split('@')
                product_name, quantity = name_qty.split(':')
                product_name = product_name.strip()
                quantity = int(quantity.strip())
                price = float(price.strip())

                if not product_name:
                    continue

                products_set.add((product_name,))
                order_items.append((order_id, product_name, quantity, price))

            except (ValueError, AttributeError):
                # Skip malformed entries but could log these if needed
                continue

    return order_items, products_set


def normalize_csv_to_3nf(csv_path: str, db_path: str) -> None:
    """
    Reads a denormalized CSV file, parses composite product entries,
    normalizes the data into 3NF, and exports it to a SQLite database.

    Parameters:
        csv_path (str): Path to the input CSV file.
        db_path (str): Path to the output SQLite database file.

    Returns:
        None
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    df = pd.read_csv(csv_path)

    required_columns = {'order_id', 'customer_name', 'customer_email', 'order_date', 'products'}
    missing = required_columns - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns in CSV: {', '.join(missing)}")

    if df.empty:
        # Create empty tables with schema only
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")
        cursor.executescript("""
        CREATE TABLE IF NOT EXISTS customers (
            customer_id INTEGER PRIMARY KEY,
            customer_name TEXT NOT NULL,
            customer_email TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS products (
            product_id INTEGER PRIMARY KEY,
            product_name TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL,
            order_date TEXT NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        );
        CREATE TABLE IF NOT EXISTS order_items (
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            PRIMARY KEY (order_id, product_id),
            FOREIGN KEY (order_id) REFERENCES orders(order_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        );
        """)
        conn.commit()
        conn.close()
        return

    # Normalize customers
    customers_df = df[['customer_name', 'customer_email']].copy()
    customers_df = generate_customer_id_map(customers_df)

    # Normalize orders
    orders_df = df[['order_id', 'customer_name', 'customer_email', 'order_date']].drop_duplicates()
    orders_df = orders_df.merge(customers_df, on=['customer_name', 'customer_email'], how='left')
    orders_df = orders_df[['order_id', 'customer_id', 'order_date']]

    # Parse products and order_items
    order_items_raw, products_set = parse_products_column(df)
    products_df = generate_product_id_map(products_set)

    # Create order_items DataFrame by joining product IDs
    order_items_df = pd.DataFrame(order_items_raw, columns=['order_id', 'product_name', 'quantity', 'price'])
    order_items_df = order_items_df.merge(products_df, on='product_name', how='left')
    order_items_df = order_items_df[['order_id', 'product_id', 'quantity', 'price']]

    # Fill missing numeric values safely
    order_items_df['quantity'] = order_items_df['quantity'].fillna(0).astype(int)
    order_items_df['price'] = order_items_df['price'].fillna(0.0).astype(float)

    # Connect to SQLite and create tables
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS customers (
        customer_id INTEGER PRIMARY KEY,
        customer_name TEXT NOT NULL,
        customer_email TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS products (
        product_id INTEGER PRIMARY KEY,
        product_name TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS orders (
        order_id INTEGER PRIMARY KEY,
        customer_id INTEGER NOT NULL,
        order_date TEXT NOT NULL,
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
    );

    CREATE TABLE IF NOT EXISTS order_items (
        order_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        price REAL NOT NULL,
        PRIMARY KEY (order_id, product_id),
        FOREIGN KEY (order_id) REFERENCES orders(order_id),
        FOREIGN KEY (product_id) REFERENCES products(product_id)
    );
    """)

    # Export data to database
    customers_df.to_sql('customers', conn, if_exists='replace', index=False)
    products_df.to_sql('products', conn, if_exists='replace', index=False)
    orders_df.to_sql('orders', conn, if_exists='replace', index=False)
    order_items_df.to_sql('order_items', conn, if_exists='replace', index=False)

    conn.commit()
    conn.close()
