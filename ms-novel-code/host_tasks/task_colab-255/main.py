
import sqlite3
from typing import Callable


def apply_schema_migrations(
    database_path: str,
    migrations: dict[int, dict[str, Callable[[sqlite3.Connection], None]]],
    target_version: int
) -> int:
    """
    Applies schema migrations to reach the target version.

    Parameters:
        database_path (str): Path to the SQLite database file.
        migrations (dict): Dictionary mapping version numbers to a dictionary
            containing "upgrade" and "downgrade" functions.
        target_version (int): The desired schema version.

    Returns:
        int: The new schema version after successful migrations.

    Raises:
        RuntimeError: If a migration fails or the schema_version table is invalid.
        ValueError: If a required migration direction is missing.
    """

    conn = sqlite3.connect(database_path)
    try:
        # Ensure schema_version table exists
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY CHECK(version >= 0)
            )
        """)
        conn.commit()

        # Enforce single-row invariant
        cursor = conn.execute("SELECT version FROM schema_version")
        rows = cursor.fetchall()
        if len(rows) > 1:
            raise RuntimeError("schema_version table contains multiple rows.")

        if not rows:
            current_version = 0
            with conn:
                conn.execute("INSERT INTO schema_version (version) VALUES (0)")
        else:
            current_version = rows[0][0]

        if current_version == target_version:
            return current_version

        def update_version(new_version: int) -> None:
            conn.execute("DELETE FROM schema_version")
            conn.execute(
                "INSERT INTO schema_version (version) VALUES (?)",
                (new_version,)
            )

        if target_version > current_version:
            # Upgrade
            for version in range(current_version + 1, target_version + 1):
                step = migrations.get(version)
                if not step or "upgrade" not in step:
                    raise ValueError(
                        f"No upgrade function provided for version {version}"
                    )

                try:
                    with conn:
                        step["upgrade"](conn)
                        update_version(version)
                except Exception as e:
                    raise RuntimeError(
                        f"Failed to upgrade to version {version}: {e}"
                    ) from e

        else:
            # Downgrade
            for version in range(current_version, target_version, -1):
                step = migrations.get(version)
                if not step or "downgrade" not in step:
                    raise ValueError(
                        f"No downgrade function provided for version {version}"
                    )

                try:
                    with conn:
                        step["downgrade"](conn)
                        update_version(version - 1)
                except Exception as e:
                    raise RuntimeError(
                        f"Failed to downgrade from version {version}: {e}"
                    ) from e

        return target_version

    finally:
        conn.close()
