# tests
"""Unit tests for the event-driven user registration system."""

import unittest
from main import (
    Event,
    is_professional_email,
    is_personal_email,
    process_user_registered_events
)


class TestEventSystem(unittest.TestCase):
    """Test suite for Event system and user registration logic."""

    def test_subscribe_and_trigger_single_handler(self):
        """Test triggering a single subscribed handler."""
        event = Event()
        event.subscribe(lambda x: x * 2)
        result = event.trigger(5)
        self.assertEqual(result, [10])

    def test_trigger_multiple_handlers(self):
        """Test triggering multiple subscribed handlers."""
        event = Event()
        event.subscribe(lambda x: x + 1)
        event.subscribe(lambda x: x * 2)
        result = event.trigger(3)
        self.assertEqual(result, [4, 6])

    def test_is_professional_email_true(self):
        """Test detection of a professional email."""
        self.assertTrue(is_professional_email("alice@company.com"))

    def test_is_professional_email_false(self):
        """Test detection of a non-professional email."""
        self.assertFalse(is_professional_email("bob@gmail.com"))

    def test_is_personal_email_true_gmail(self):
        """Test detection of Gmail as a personal email."""
        self.assertTrue(is_personal_email("bob@gmail.com"))

    def test_is_personal_email_true_yahoo(self):
        """Test detection of Yahoo as a personal email."""
        self.assertTrue(is_personal_email("bob@yahoo.com"))

    def test_is_personal_email_false(self):
        """Test detection of non-personal email."""
        self.assertFalse(is_personal_email("bob@company.com"))

    def test_valid_admin_registration(self):
        """Test valid registration with admin privileges, work email."""
        events = [{
            "username": "Alice",
            "email": "alice@company.com",
            "timestamp": 1,
            "user_type": "admin",
            "age": 25
        }]
        result = process_user_registered_events(events)
        self.assertIn("admin privileges", result[0])
        self.assertIn("professional email", result[0])

    def test_valid_guest_registration(self):
        """Test valid guest registration with personal email."""
        events = [{
            "username": "Guest",
            "email": "guest@gmail.com",
            "timestamp": 2,
            "user_type": "guest",
            "age": 20
        }]
        result = process_user_registered_events(events)
        self.assertIn("guest access", result[0])
        self.assertIn("personal email", result[0])

    def test_underage_warning(self):
        """Test age restriction warning for users under 18."""
        events = [{
            "username": "Young",
            "email": "young@gmail.com",
            "timestamp": 3,
            "age": 17
        }]
        result = process_user_registered_events(events)
        self.assertIn("restricted for users under 18", result[0])

    def test_exact_age_no_warning(self):
        """Test that 18-year-old user receives no restriction message."""
        events = [{
            "username": "Adult",
            "email": "adult@gmail.com",
            "timestamp": 4,
            "age": 18
        }]
        result = process_user_registered_events(events)
        self.assertNotIn("restricted", result[0])

    def test_missing_username(self):
        """Test registration fails if username is missing."""
        events = [{
            "email": "no_user@gmail.com",
            "timestamp": 5
        }]
        result = process_user_registered_events(events)
        self.assertEqual(result[0], "Invalid registration")

    def test_missing_email(self):
        """Test registration fails if email is missing."""
        events = [{
            "username": "NoEmail",
            "timestamp": 6
        }]
        result = process_user_registered_events(events)
        self.assertEqual(result[0], "Invalid registration")

    def test_username_whitespace(self):
        """Test registration fails if username is only whitespace."""
        events = [{
            "username": "   ",
            "email": "user@company.com",
            "timestamp": 7
        }]
        result = process_user_registered_events(events)
        self.assertEqual(result[0], "Invalid registration")

    def test_email_whitespace(self):
        """Test registration fails if email is only whitespace."""
        events = [{
            "username": "User",
            "email": "   ",
            "timestamp": 8
        }]
        result = process_user_registered_events(events)
        self.assertEqual(result[0], "Invalid registration")

    def test_email_missing_at(self):
        """Test registration fails if email has no '@' symbol."""
        events = [{
            "username": "User",
            "email": "user.company.com",
            "timestamp": 9
        }]
        result = process_user_registered_events(events)
        self.assertEqual(result[0], "Invalid registration")

    def test_email_multiple_at(self):
        """Test registration fails if email has multiple '@' symbols."""
        events = [{
            "username": "User",
            "email": "user@@company.com",
            "timestamp": 10
        }]
        result = process_user_registered_events(events)
        self.assertEqual(result[0], "Invalid registration")

    def test_email_no_dot_after_at(self):
        """Test registration fails if email domain lacks a dot."""
        events = [{
            "username": "User",
            "email": "user@companycom",
            "timestamp": 11
        }]
        result = process_user_registered_events(events)
        self.assertEqual(result[0], "Invalid registration")

    def test_unknown_user_type(self):
        """Test registration with unknown user_type still succeeds."""
        events = [{
            "username": "Mystery",
            "email": "mystery@gmail.com",
            "timestamp": 12,
            "user_type": "superuser"
        }]
        result = process_user_registered_events(events)
        self.assertIn("registration is successful", result[0])

    def test_valid_email_with_extra_whitespace(self):
        """Test trimming of whitespace in email."""
        events = [{
            "username": "Trim",
            "email": "  trim@company.com  ",
            "timestamp": 13
        }]
        result = process_user_registered_events(events)
        self.assertIn("professional email", result[0])

    def test_process_empty_event_list(self):
        """Test processing an empty list of events returns an empty list."""
        self.assertEqual(process_user_registered_events([]), [])

    def test_multiple_valid_and_invalid_events(self):
        """Test processing a mix of valid and invalid registration events."""
        events = [
            {
                "username": "Valid",
                "email": "valid@company.com",
                "timestamp": 14
            },
            {
                "username": "",
                "email": "invalid@company.com",
                "timestamp": 15
            }
        ]
        result = process_user_registered_events(events)
        self.assertEqual(len(result), 2)
        self.assertIn("registration is successful", result[0])
        self.assertEqual(result[1], "Invalid registration")
