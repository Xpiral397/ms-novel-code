# tests

import unittest
import sqlite3
import os
import tempfile
from main import apply_schema_migrations


class TestSchemaMigrations(unittest.TestCase):
    """Unit test suite for schema migration system using
      apply_schema_migrations."""

    def setUp(self):
        """Create a temporary SQLite file before each test."""
        self.temp_file = tempfile.NamedTemporaryFile(
            delete=False, suffix=".sqlite")
        self.db_path = self.temp_file.name
        self.temp_file.close()

    def tearDown(self):
        """Clean up the temporary database file."""
        try:
            os.remove(self.db_path)
        except PermissionError:
            import gc
            gc.collect()
            try:
                os.remove(self.db_path)
            except Exception:
                pass

    def test_create_schema_version_on_fresh_db(self):
        """Should create schema_version on empty DB and upgrade to
        version 1."""
        migrations = {
            1: {
                "upgrade": lambda conn: conn.execute(
                    "CREATE TABLE test (id INTEGER)"),
                "downgrade": lambda conn: conn.execute("DROP TABLE test")
            }
        }
        new_version = apply_schema_migrations(self.db_path, migrations, 1)
        self.assertEqual(new_version, 1)

    def test_upgrade_multiple_versions(self):
        """Should apply all upgrades from version 0 to 3 in order."""
        migrations = {
            1: {"upgrade": lambda c: c.execute("CREATE TABLE t1 (id INTEGER)"),
                "downgrade": lambda c: c.execute("DROP TABLE t1")},
            2: {"upgrade": lambda c: c.execute("CREATE TABLE t2 (id INTEGER)"),
                "downgrade": lambda c: c.execute("DROP TABLE t2")},
            3: {"upgrade": lambda c: c.execute("CREATE TABLE t3 (id INTEGER)"),
                "downgrade": lambda c: c.execute("DROP TABLE t3")},
        }
        new_version = apply_schema_migrations(self.db_path, migrations, 3)
        self.assertEqual(new_version, 3)

    def test_downgrade_single_step(self):
        """Should downgrade from version 3 to version 1."""
        migrations = {
            1: {"upgrade": lambda c: c.execute("CREATE TABLE t1 (id INTEGER)"),
                "downgrade": lambda c: c.execute("DROP TABLE t1")},
            2: {"upgrade": lambda c: c.execute("CREATE TABLE t2 (id INTEGER)"),
                "downgrade": lambda c: c.execute("DROP TABLE t2")},
            3: {"upgrade": lambda c: c.execute("CREATE TABLE t3 (id INTEGER)"),
                "downgrade": lambda c: c.execute("DROP TABLE t3")},
        }
        apply_schema_migrations(self.db_path, migrations, 3)
        new_version = apply_schema_migrations(self.db_path, migrations, 1)
        self.assertEqual(new_version, 1)

    def test_noop_if_target_equals_current(self):
        """Should do nothing if target version equals current version."""
        migrations = {
            1: {"upgrade": lambda c: c.execute("CREATE TABLE t (id INTEGER)"),
                "downgrade": lambda c: c.execute("DROP TABLE t")},
        }
        apply_schema_migrations(self.db_path, migrations, 1)
        new_version = apply_schema_migrations(self.db_path, migrations, 1)
        self.assertEqual(new_version, 1)

    def test_empty_migrations_returns_current(self):
        """Should return current version if migrations dict is empty."""
        new_version = apply_schema_migrations(self.db_path, {}, 0)
        self.assertEqual(new_version, 0)

    def test_missing_upgrade_raises_error(self):
        """Should raise ValueError if upgrade function is missing."""
        migrations = {
            1: {"downgrade": lambda c: c.execute("SELECT 1")}
        }
        with self.assertRaises(ValueError):
            apply_schema_migrations(self.db_path, migrations, 1)

    def test_missing_downgrade_raises_error(self):
        """Should raise ValueError if downgrade function is missing."""
        migrations = {
            1: {"upgrade": lambda c: c.execute("SELECT 1")}
        }
        apply_schema_migrations(self.db_path, migrations, 1)
        with self.assertRaises(ValueError):
            apply_schema_migrations(self.db_path, migrations, 0)

    def test_downgrade_below_zero_raises_error(self):
        """Should raise ValueError when trying to downgrade below version 0."""
        with self.assertRaises(ValueError):
            apply_schema_migrations(self.db_path, {}, -1)

    def test_failed_upgrade_rolls_back(self):
        """Should not apply partial upgrade on failure."""
        def broken_migration(conn):
            raise RuntimeError("Upgrade failed before any change")

        migrations = {
            1: {
                "upgrade": broken_migration,
                "downgrade": lambda c: c.execute("DROP TABLE IF EXISTS safe")
            }
        }

        with self.assertRaises(RuntimeError):
            apply_schema_migrations(self.db_path, migrations, 1)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = [row[0] for row in cursor.fetchall()]
            self.assertNotIn("safe", tables)

    def test_idempotent_upgrade_execution(self):
        """Should allow safe re-run of same upgrade without duplication."""
        migrations = {
            1: {"upgrade": lambda c: c.execute(
                "CREATE TABLE IF NOT EXISTS t (id INTEGER)"),
                "downgrade": lambda c: c.execute("DROP TABLE t")}
        }
        apply_schema_migrations(self.db_path, migrations, 1)
        new_version = apply_schema_migrations(self.db_path, migrations, 1)
        self.assertEqual(new_version, 1)

    def test_non_consecutive_versions(self):
        """Should skip missing versions if not present in migrations."""
        migrations = {
            1: {"upgrade": lambda c: None, "downgrade": lambda c: None},
            2: {"upgrade": lambda c: None, "downgrade": lambda c: None},
            3: {"upgrade": lambda c: c.execute("CREATE TABLE x (id INTEGER)"),
                "downgrade": lambda c: c.execute("DROP TABLE x")},
        }

        version = apply_schema_migrations(self.db_path, migrations, 3)
        self.assertEqual(version, 3)

    def test_multiple_downgrades(self):
        """Should downgrade multiple steps from version 3 to 0."""
        migrations = {
            1: {"upgrade": lambda c: c.execute("CREATE TABLE t1 (id INTEGER)"),
                "downgrade": lambda c: c.execute("DROP TABLE t1")},
            2: {"upgrade": lambda c: c.execute("CREATE TABLE t2 (id INTEGER)"),
                "downgrade": lambda c: c.execute("DROP TABLE t2")},
            3: {"upgrade": lambda c: c.execute("CREATE TABLE t3 (id INTEGER)"),
                "downgrade": lambda c: c.execute("DROP TABLE t3")},
        }
        apply_schema_migrations(self.db_path, migrations, 3)
        new_version = apply_schema_migrations(self.db_path, migrations, 0)
        self.assertEqual(new_version, 0)

    def test_partial_migration_is_atomic(self):
        """Should rollback version if error occurs during downgrade."""
        def downgrade_with_error(conn):
            conn.execute("DROP TABLE t1")
            raise Exception("Oops")

        migrations = {
            1: {
                "upgrade": lambda c: c.execute("CREATE TABLE t1 (id INTEGER)"),
                "downgrade": downgrade_with_error
            }
        }

        apply_schema_migrations(self.db_path, migrations, 1)

        with self.assertRaises(Exception):
            apply_schema_migrations(self.db_path, migrations, 0)

        version = apply_schema_migrations(self.db_path, migrations, 1)
        self.assertEqual(version, 1)

    def test_target_version_equal_zero(self):
        """Should downgrade to version 0 from any higher version."""
        migrations = {
            1: {"upgrade": lambda c: c.execute("CREATE TABLE t1 (id INTEGER)"),
                "downgrade": lambda c: c.execute("DROP TABLE t1")},
            2: {"upgrade": lambda c: c.execute("CREATE TABLE t2 (id INTEGER)"),
                "downgrade": lambda c: c.execute("DROP TABLE t2")},
            3: {"upgrade": lambda c: c.execute("CREATE TABLE t3 (id INTEGER)"),
                "downgrade": lambda c: c.execute("DROP TABLE t3")},
        }
        apply_schema_migrations(self.db_path, migrations, 3)
        version = apply_schema_migrations(self.db_path, migrations, 0)
        self.assertEqual(version, 0)

    def test_max_version_boundary(self):
        """Ensure migrations are applied in correct ascending order to
        reach version 1000."""
        order = []

        migrations = {
            v: {
                "upgrade": (lambda v=v: lambda c: order.append(v))(),
                "downgrade": (lambda v=v: lambda c: order.append(-v))()
            }
            for v in range(1, 1001)
        }

        version = apply_schema_migrations(self.db_path, migrations, 1000)

        self.assertEqual(version, 1000)
        self.assertEqual(order, list(range(1, 1001)))

    def test_existing_schema_version_table(self):
        """Should respect existing schema_version table and continue
          migration."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE schema_version (version INTEGER)")
            conn.execute("INSERT INTO schema_version (version) VALUES (2)")
            conn.commit()

        migrations = {
            3: {
                "upgrade": lambda c: c.execute("CREATE TABLE t3 (id INTEGER)"),
                "downgrade": lambda c: c.execute("DROP TABLE t3")
            }
        }

        version = apply_schema_migrations(self.db_path, migrations, 3)
        self.assertEqual(version, 3)

    def test_schema_version_table_single_row(self):
        """Should raise error if schema_version table contains more than\
              one row."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE schema_version (version INTEGER)")
            conn.execute("INSERT INTO schema_version (version) VALUES (1)")
            conn.execute("INSERT INTO schema_version (version) VALUES (2)")
            conn.commit()

        migrations = {
            3: {
                "upgrade": lambda c: c.execute("CREATE TABLE x (id INTEGER)"),
                "downgrade": lambda c: c.execute("DROP TABLE x")
            }
        }

        with self.assertRaises(RuntimeError):
            apply_schema_migrations(self.db_path, migrations, 3)


if __name__ == '__main__':
    unittest.main()
