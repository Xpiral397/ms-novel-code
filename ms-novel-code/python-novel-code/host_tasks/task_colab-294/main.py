
"""Audit-tracked employee database using SQLite in-memory database."""

import sqlite3
from typing import List, Tuple


def setup_and_track_changes(
        operations: List[Tuple[str, Tuple]]) -> List[Tuple]:
    """
    Set up SQLite in-memory DB with triggers and execute operations.

    Args:
        operations: A list of tuples representing
                    database operations to perform.
                    Each tuple contains an operation type
                    and its corresponding data.

    Returns:
        A list of tuples representing rows in the audit_log table.
    """
    connection = sqlite3.connect(":memory:")
    cursor = connection.cursor()

    cursor.execute('''
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY,
            name TEXT,
            role TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT,
            employee_id INTEGER,
            name TEXT,
            role TEXT,
            timestamp TEXT
        )
    ''')

    cursor.execute('''
        CREATE TRIGGER insert_employee_trigger
        AFTER INSERT ON employees
        FOR EACH ROW
        BEGIN
            INSERT INTO audit_log(action, employee_id, name, role, timestamp)
            VALUES (
                'INSERT',
                NEW.id,
                NEW.name,
                NEW.role,
                datetime('now')
            );
        END;
    ''')

    cursor.execute('''
        CREATE TRIGGER update_employee_trigger
        AFTER UPDATE ON employees
        FOR EACH ROW
        WHEN NEW.name IS NOT OLD.name OR NEW.role IS NOT OLD.role
        BEGIN
            INSERT INTO audit_log(action, employee_id, name, role, timestamp)
            VALUES (
                'UPDATE',
                NEW.id,
                NEW.name,
                NEW.role,
                datetime('now')
            );
        END;
    ''')

    cursor.execute('''
        CREATE TRIGGER delete_employee_trigger
        AFTER DELETE ON employees
        FOR EACH ROW
        BEGIN
            INSERT INTO audit_log(action, employee_id, name, role, timestamp)
            VALUES (
                'DELETE',
                OLD.id,
                OLD.name,
                OLD.role,
                datetime('now')
            );
        END;
    ''')

    for operation in operations:
        op_type, data = operation
        if op_type == "INSERT":
            try:
                cursor.execute(
                    'INSERT INTO employees (id, name, role)'
                    ' VALUES (?, ?, ?)', data
                )
            except sqlite3.IntegrityError:
                raise
        elif op_type == "UPDATE":
            emp_id, new_name, new_role = data
            cursor.execute(
                'SELECT name, role FROM employees WHERE id = ?', (emp_id,)
            )
            result = cursor.fetchone()

            if result:
                current_name, current_role = result
                updated_name = new_name if (new_name
                                            is not None) else current_name
                updated_role = new_role if (new_role
                                            is not None) else current_role

                if new_name is None and new_role is None:
                    continue

                if (
                    updated_name != current_name
                    or updated_role != current_role
                ):
                    cursor.execute(
                        'UPDATE employees SET name = ?, role = ? WHERE id = ?',
                        (updated_name, updated_role, emp_id)
                    )
            else:
                continue
        elif op_type == "DELETE":
            emp_id_to_delete = data[0]
            cursor.execute(
                'SELECT id FROM employees WHERE id = ?', (emp_id_to_delete,)
            )
            if cursor.fetchone():
                cursor.execute(
                    'DELETE FROM employees WHERE id = ?', (emp_id_to_delete,)
                )
            else:
                continue

    connection.commit()
    cursor.execute(
        'SELECT id, action, employee_id, name, role, timestamp '
        'FROM audit_log ORDER BY id'
    )
    audit_log = cursor.fetchall()
    connection.close()

    return audit_log
