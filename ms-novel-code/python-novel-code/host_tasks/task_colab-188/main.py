
"""This module simulates OCC in SQLite."""

import sqlite3
import threading
import time
from typing import List, Dict

DB_URI = "file:occdb?mode=memory&cache=shared"
_transaction_results: Dict[str, Dict] = {}


def setup_db() -> sqlite3.Connection:
    """Initialize a shared in-memory SQLite database with an `inventory` table.

    Inserts a default item with quantity=10 and version=1.

    Returns:
        sqlite3.Connection: The open connection to keep the in-memory DB alive.
    """
    conn = sqlite3.connect(DB_URI, uri=True, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY,
            item_name TEXT,
            quantity INTEGER,
            version INTEGER
        )
    ''')
    cursor.execute('''
        INSERT OR REPLACE INTO inventory (id, item_name, quantity, version)
        VALUES (1, 'Health Potion', 10, 1)
    ''')
    conn.commit()
    return conn


def run_transaction(name: str, delay: float) -> None:
    """Simulate a database transaction using optimistic concurrency control.

    Reads item data, waits for delay, checks version, and attempts update.
    If the version has changed, the transaction is rolled back.

    Args:
        name (str): Name of the transaction (used for tracking/logging).
        delay (float): Time to wait before attempting the update
        (simulates concurrency).
    """
    try:
        time.sleep(delay)
        conn = sqlite3.connect(DB_URI, uri=True, check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('BEGIN')

        try:
            cursor.execute(
                'SELECT quantity, version FROM inventory WHERE id = 1')
            row = cursor.fetchone()
        except sqlite3.OperationalError as e:
            if "no such table" in str(e):
                _transaction_results[name] = {
                    "transaction": name,
                    "status": -1,
                    "reason": "Database not initialized"
                }
                return
            raise

        if row is None:
            _transaction_results[name] = {
                "transaction": name,
                "status": "error",
                "reason": "Inventory row not found"
            }
            return

        current_quantity, current_version = row

        cursor.execute('SELECT version FROM inventory WHERE id = 1')
        latest_version = cursor.fetchone()[0]

        if latest_version != 1:
            conn.rollback()
            _transaction_results[name] = {
                "transaction": name,
                "status": "conflict",
                "reason": """Expected version={current_version},
                found version={latest_version}."""
            }
            return

        new_quantity = current_quantity - 1
        new_version = current_version + 1

        cursor.execute('''
            UPDATE inventory
            SET quantity = ?, version = ?
            WHERE id = 1
        ''', (new_quantity, new_version))

        conn.commit()
        _transaction_results[name] = {
            "transaction": name,
            "status": "committed",
            "final_quantity": new_quantity,
            "final_version": new_version
        }

    except Exception as e:
        conn.rollback()
        _transaction_results[name] = {
            "transaction": name,
            "status": "error",
            "reason": str(e)
        }
    finally:
        conn.close()


def simulate_concurrent_transactions(
        threads: List[threading.Thread]) -> List[Dict]:
    """Launch and manages concurrent execution of.

    provided transaction threads.
    Collects and returns the outcome of each transaction.

    Args:
        threads (List[threading.Thread]):
        A list of pre-configured transaction threads.

    Returns:
        List[Dict]: A list of transaction result dictionaries.
    """
    global _transaction_results
    _transaction_results = {}

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    return list(_transaction_results.values())


if __name__ == "__main__":
    keep_alive_conn = setup_db()

    threads = [
        threading.Thread(target=run_transaction, args=("Transaction A", 0.3)),
        threading.Thread(target=run_transaction, args=("Transaction B", 0.5))
    ]

    results = simulate_concurrent_transactions(threads)

    keep_alive_conn.close()

    for result in results:
        print(result)

