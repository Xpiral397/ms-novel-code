# tests

"""Module for testing the DatabaseManager class."""

import unittest
import os
import tempfile
import json
from main import DatabaseManager


class TestDatabaseManager(unittest.TestCase):
    """Test suite for DatabaseManager SQLAlchemy CLI application."""

    def setUp(self):
        """Set up test environment."""
        self.test_db_fd, self.test_db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.test_db_fd)
        self.db_url = f"sqlite:///{self.test_db_path}"

        self.db_manager = DatabaseManager(self.db_url)
        self.temp_json_fd, self.temp_json_path = tempfile.mkstemp(
            suffix=".json"
        )
        self.temp_csv_fd, self.temp_csv_path = tempfile.mkstemp(suffix=".csv")
        os.close(self.temp_json_fd)
        os.close(self.temp_csv_fd)

    def tearDown(self):
        """Tear down test environment."""
        if hasattr(self.db_manager, "session"):
            self.db_manager.session.close()
        if hasattr(self.db_manager, "engine"):
            self.db_manager.engine.dispose()
        for file_path in [
            self.test_db_path, self.temp_json_path, self.temp_csv_path
        ]:
            if os.path.exists(file_path):
                os.unlink(file_path)

    def test_create_person_returns_valid_id(self):
        """Test create_person returns a valid integer ID."""
        person_id = self.db_manager.create_person("Alice Johnson", 30)
        self.assertIsInstance(person_id, int)
        self.assertGreater(person_id, 0)

    def test_create_person_invalid_name_raises_error(self):
        """Test create_person raises error for empty name validation."""
        with self.assertRaises(ValueError):
            self.db_manager.create_person("", 30)

    def test_create_person_invalid_age_raises_error(self):
        """Test create_person raises error for age <= 0 validation."""
        with self.assertRaises(ValueError):
            self.db_manager.create_person("John Doe", 0)

    def test_add_contact_info_success(self):
        """Test add_or_update_contact returns True for valid input."""
        person_id = self.db_manager.create_person("Bob Smith", 25)
        result = self.db_manager.add_or_update_contact(
            person_id, "bob@example.com", "1234567890"
        )
        self.assertTrue(result)

    def test_add_contact_invalid_email_raises_error(self):
        """Test add_or_update_contact raises error for invalid email."""
        person_id = self.db_manager.create_person("Test Person", 30)
        with self.assertRaises(ValueError):
            self.db_manager.add_or_update_contact(
                person_id, "invalid-email", "1234567890"
            )

    def test_create_group_returns_valid_id(self):
        """Test create_group returns a valid integer ID."""
        group_id = self.db_manager.create_group("Engineers")
        self.assertIsInstance(group_id, int)
        self.assertGreater(group_id, 0)

    def test_assign_person_to_group_success(self):
        """Test assign_group returns True for valid assignment."""
        person_id = self.db_manager.create_person("Charlie Brown", 35)
        group_id = self.db_manager.create_group("Developers")
        result = self.db_manager.assign_group(person_id, group_id)
        self.assertTrue(result)

    def test_read_people_with_age_filter(self):
        """Test read_people filters by min_age correctly."""
        self.db_manager.create_person("Alice", 30)
        self.db_manager.create_person("Bob", 25)
        people = self.db_manager.read_people({"min_age": 28})
        self.assertEqual(len(people), 1)

    def test_read_people_with_name_filter(self):
        """Test read_people filters by name_contains correctly."""
        self.db_manager.create_person("Alice Johnson", 30)
        self.db_manager.create_person("Bob Smith", 25)
        people = self.db_manager.read_people({"name_contains": "Alice"})
        self.assertEqual(len(people), 1)

    def test_update_person_success(self):
        """Test update_person returns True for valid update."""
        person_id = self.db_manager.create_person("David Wilson", 28)
        result = self.db_manager.update_person(
            person_id, name="David Wilson Jr."
        )
        self.assertTrue(result)

    def test_update_nonexistent_person_raises_error(self):
        """Test update_person raises error for non-existent ID."""
        with self.assertRaises(ValueError):
            self.db_manager.update_person(999, name="Nobody")

    def test_delete_person_success(self):
        """Test delete_person returns True for valid deletion."""
        person_id = self.db_manager.create_person("Eva Martinez", 32)
        result = self.db_manager.delete_person(person_id)
        self.assertTrue(result)

    def test_batch_update_valid_ids_success(self):
        """Test batch_update_age returns True for all valid IDs."""
        person1_id = self.db_manager.create_person("Frank", 45)
        person2_id = self.db_manager.create_person("Grace", 29)
        result = self.db_manager.batch_update_age([person1_id, person2_id], 40)
        self.assertTrue(result)

    def test_batch_update_invalid_id_rollback(self):
        """Test batch_update_age raises error and rolls back on invalid ID."""
        person1_id = self.db_manager.create_person("Henry", 33)
        with self.assertRaises(Exception):
            self.db_manager.batch_update_age([person1_id, 999], 40)

    def test_export_persons_to_json_success(self):
        """Test export_data returns True for valid JSON export."""
        self.db_manager.create_person("John Doe", 30)
        result = self.db_manager.export_data(
            "person", "json", self.temp_json_path
        )
        self.assertTrue(result)

    def test_import_persons_from_json_success(self):
        """Test import_data returns True for valid JSON import."""
        test_data = [{"name": "Imported Person", "age": 35}]
        with open(self.temp_json_path, "w") as f:
            json.dump(test_data, f)
        result = self.db_manager.import_data(
            "person", "json", self.temp_json_path
        )
        self.assertTrue(result)

    def test_import_invalid_json_raises_error(self):
        """Test import_data raises error for malformed JSON."""
        with open(self.temp_json_path, "w") as f:
            f.write("invalid json")
        with self.assertRaises(Exception):
            self.db_manager.import_data("person", "json", self.temp_json_path)

    def test_read_people_pagination_limit(self):
        """Test read_people respects limit parameter for pagination."""
        self.db_manager.create_person("Person1", 30)
        self.db_manager.create_person("Person2", 25)
        self.db_manager.create_person("Person3", 35)
        people = self.db_manager.read_people({"limit": 2})
        self.assertEqual(len(people), 2)


if __name__ == "__main__":
    unittest.main()
