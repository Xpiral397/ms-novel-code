# tests

"""Test module for SQLAlchemy CRUD operations."""
import unittest
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError

from main import (
    create_user,
    get_user,
    get_users,
    update_user,
    delete_user,
    Base,
)


class TestSQLAlchemyCRUD(unittest.TestCase):
    """Test cases for SQLAlchemy CRUD operations."""

    def setUp(self):
        """Set up test database for each test case."""
        self.engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def tearDown(self):
        """Clean up after each test."""
        self.session.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_create_user_success(self):
        """Test successful user creation with valid inputs."""
        result = create_user(
            self.session, "Alice Johnson", "alice@example.com"
        )

        self.assertTrue(result)
        users = get_users(self.session)
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0]["name"], "Alice Johnson")
        self.assertEqual(users[0]["email"], "alice@example.com")
        self.assertIsInstance(users[0]["id"], int)

    def test_create_user_duplicate_email(self):
        """Test create user fails gracefully with duplicate email."""
        result1 = create_user(self.session, "Alice", "alice@example.com")
        self.assertTrue(result1)

        result2 = create_user(self.session, "Bob", "alice@example.com")
        self.assertFalse(result2)

        users = get_users(self.session)
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0]["name"], "Alice")

    def test_create_user_invalid_name_empty(self):
        """Test create user fails with empty name."""
        result = create_user(self.session, "", "alice@example.com")
        self.assertFalse(result)

        users = get_users(self.session)
        self.assertEqual(len(users), 0)

    def test_create_user_invalid_email_format(self):
        """Test create user fails with invalid email format."""
        invalid_emails = [
            "invalid-email",
            "@example.com",
            "alice@",
            "alice.example.com",
            "",
            "alice@.com",
        ]

        for invalid_email in invalid_emails:
            with self.subTest(email=invalid_email):
                result = create_user(self.session, "Alice", invalid_email)
                self.assertFalse(result)

        users = get_users(self.session)
        self.assertEqual(len(users), 0)

    def test_get_user_existing(self):
        """Test retrieving an existing user by ID."""
        create_user(self.session, "Bob Smith", "bob@example.com")

        user = get_user(self.session, 1)

        self.assertIsNotNone(user)
        self.assertIsInstance(user, dict)
        self.assertEqual(user["id"], 1)
        self.assertEqual(user["name"], "Bob Smith")
        self.assertEqual(user["email"], "bob@example.com")

        expected_keys = {"id", "name", "email"}
        self.assertEqual(set(user.keys()), expected_keys)

    def test_get_user_non_existent(self):
        """Test retrieving non-existent user returns None."""
        user = get_user(self.session, 999)
        self.assertIsNone(user)

        user = get_user(self.session, 1)
        self.assertIsNone(user)

    def test_get_users_empty_database(self):
        """Test get_users returns empty list when no users exist."""
        users = get_users(self.session)

        self.assertIsInstance(users, list)
        self.assertEqual(len(users), 0)

    def test_get_users_multiple_records(self):
        """Test get_users returns all users correctly."""
        create_user(self.session, "Alice", "alice@example.com")
        create_user(self.session, "Bob", "bob@example.com")
        create_user(self.session, "Charlie", "charlie@example.com")

        users = get_users(self.session)

        self.assertIsInstance(users, list)
        self.assertEqual(len(users), 3)

        for user in users:
            self.assertIsInstance(user, dict)
            self.assertIn("id", user)
            self.assertIn("name", user)
            self.assertIn("email", user)

        names = [user["name"] for user in users]
        self.assertIn("Alice", names)
        self.assertIn("Bob", names)
        self.assertIn("Charlie", names)

    def test_update_user_success(self):
        """Test successful user update."""
        create_user(self.session, "Original Name", "original@example.com")

        result = update_user(
            self.session, 1, "Updated Name", "updated@example.com"
        )
        self.assertTrue(result)

        user = get_user(self.session, 1)
        self.assertEqual(user["name"], "Updated Name")
        self.assertEqual(user["email"], "updated@example.com")
        self.assertEqual(user["id"], 1)

    def test_update_user_non_existent(self):
        """Test update returns False for non-existent user."""
        result = update_user(self.session, 999, "New Name", "new@example.com")
        self.assertFalse(result)

        users = get_users(self.session)
        self.assertEqual(len(users), 0)

    def test_update_user_duplicate_email_constraint(self):
        """Test update fails gracefully when violating email uniqueness."""
        create_user(self.session, "Alice", "alice@example.com")
        create_user(self.session, "Bob", "bob@example.com")

        result = update_user(
            self.session, 2, "Bob Updated", "alice@example.com"
        )
        self.assertFalse(result)

        bob = get_user(self.session, 2)
        self.assertEqual(bob["name"], "Bob")
        self.assertEqual(bob["email"], "bob@example.com")

    def test_update_user_invalid_inputs(self):
        """Test update fails with invalid name or email."""
        create_user(self.session, "Valid Name", "valid@example.com")

        result = update_user(self.session, 1, "", "valid@example.com")
        self.assertFalse(result)

        result = update_user(self.session, 1, "Valid Name", "invalid-email")
        self.assertFalse(result)

        user = get_user(self.session, 1)
        self.assertEqual(user["name"], "Valid Name")
        self.assertEqual(user["email"], "valid@example.com")

    def test_delete_user_success(self):
        """Test successful user deletion."""
        create_user(self.session, "To Delete", "delete@example.com")

        user = get_user(self.session, 1)
        self.assertIsNotNone(user)

        result = delete_user(self.session, 1)
        self.assertTrue(result)

        user = get_user(self.session, 1)
        self.assertIsNone(user)

        users = get_users(self.session)
        self.assertEqual(len(users), 0)

    def test_delete_user_non_existent(self):
        """Test delete returns False for non-existent user."""
        result = delete_user(self.session, 999)
        self.assertFalse(result)

        result = delete_user(self.session, 1)
        self.assertFalse(result)

    @patch("time.sleep")
    def test_create_user_retry_logic_on_operational_error(self, mock_sleep):
        """Test retry logic when OperationalError occurs."""
        with patch.object(self.session, "commit") as mock_commit:
            mock_commit.side_effect = [
                OperationalError("DB locked", None, None),
                OperationalError("DB locked", None, None),
                None,
            ]

            result = create_user(
                self.session, "Retry Test", "retry@example.com"
            )

            self.assertTrue(result)
            self.assertEqual(mock_commit.call_count, 3)
            self.assertEqual(mock_sleep.call_count, 2)
            mock_sleep.assert_called_with(0.1)


if __name__ == "__main__":
    unittest.main()
