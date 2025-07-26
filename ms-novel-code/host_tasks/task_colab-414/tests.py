# tests

"""Test module for HTTP server webhook JSON database functionality."""

import unittest
import json
import os
import tempfile
import shutil
from http.server import ThreadingHTTPServer
from threading import Thread
import time
import requests

from main import WebhookServer


class TestWebhookServer(unittest.TestCase):
    """Test suite for WebhookServer HTTP server functionality."""

    def setUp(self):
        """Set up test environment and start server for each test."""
        self.test_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.test_dir)

        self.server = ThreadingHTTPServer(("localhost", 0), WebhookServer)
        self.server_thread = Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()
        time.sleep(0.5)

        port = self.server.server_address[1]
        self.base_url = f"http://localhost:{port}"

        if os.path.exists("db.json"):
            os.remove("db.json")

    def tearDown(self):
        """Stop server and clean up after each test."""
        self.server.shutdown()
        self.server_thread.join(timeout=2)

        os.chdir(self.original_dir)
        shutil.rmtree(self.test_dir)

    def test_successful_complete_payload(self):
        """Test webhook with all fields including optional metadata."""
        payload = {
            "event_type": "purchase",
            "timestamp": "2025-07-21T15:45:00Z",
            "user": {
                "id": "98765",
                "name": "Bob Smith",
                "email": "bob@example.com",
            },
            "metadata": {"source": "mobile_app", "campaign": "flash_sale"},
        }

        response = requests.post(f"{self.base_url}/webhook", json=payload)

        self.assertEqual(response.status_code, 200)

        with open("db.json", "r") as f:
            data = json.load(f)

        self.assertEqual(len(data), 1)
        entry = data[0]

        self.assertEqual(entry["event_type"], "purchase")
        self.assertEqual(entry["timestamp"], "2025-07-21T15:45:00Z")
        self.assertEqual(entry["user_id"], "98765")
        self.assertEqual(entry["user_name"], "Bob Smith")
        self.assertEqual(entry["user_email"], "bob@example.com")
        self.assertEqual(entry["source"], "mobile_app")
        self.assertEqual(entry["campaign"], "flash_sale")

    def test_only_required_fields(self):
        """Test webhook without optional metadata."""
        payload = {
            "event_type": "login",
            "timestamp": "2025-07-21T16:00:00Z",
            "user": {
                "id": "55555",
                "name": "Charlie",
                "email": "charlie@test.com",
            },
        }

        response = requests.post(f"{self.base_url}/webhook", json=payload)

        self.assertEqual(response.status_code, 200)

        with open("db.json", "r") as f:
            data = json.load(f)

        self.assertEqual(len(data), 1)
        entry = data[0]

        self.assertEqual(entry["event_type"], "login")
        self.assertEqual(entry["user_id"], "55555")

        self.assertNotIn("source", entry)
        self.assertNotIn("campaign", entry)

    def test_missing_timestamp(self):
        """Test validation when timestamp is missing."""
        payload = {
            "event_type": "logout",
            "user": {
                "id": "12345",
                "name": "David",
                "email": "david@example.com",
            },
        }

        response = requests.post(f"{self.base_url}/webhook", json=payload)

        self.assertEqual(response.status_code, 400)

        self.assertFalse(os.path.exists("db.json"))

    def test_empty_json_body(self):
        """Test empty request body."""
        response = requests.post(f"{self.base_url}/webhook", json={})

        self.assertEqual(response.status_code, 400)
        self.assertFalse(os.path.exists("db.json"))

    def test_malformed_json(self):
        """Test invalid JSON syntax."""
        response = requests.post(
            f"{self.base_url}/webhook",
            data='{"event_type": "test", invalid json}',
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(os.path.exists("db.json"))

    def test_wrong_endpoint(self):
        """Test POST to incorrect endpoint."""
        payload = {
            "event_type": "test",
            "timestamp": "2025-07-21T16:00:00Z",
            "user": {"id": "123", "name": "Test", "email": "test@test.com"},
        }

        response = requests.post(f"{self.base_url}/invalid", json=payload)

        self.assertEqual(response.status_code, 404)
        self.assertFalse(os.path.exists("db.json"))

    def test_unsupported_method(self):
        """Test GET request to webhook endpoint."""
        response = requests.get(f"{self.base_url}/webhook")

        self.assertEqual(response.status_code, 405)

    def test_concurrent_requests(self):
        """Test thread safety with simultaneous requests."""
        payload1 = {
            "event_type": "view",
            "timestamp": "2025-07-21T17:00:00Z",
            "user": {"id": "111", "name": "User1", "email": "user1@test.com"},
        }

        payload2 = {
            "event_type": "click",
            "timestamp": "2025-07-21T17:00:01Z",
            "user": {"id": "222", "name": "User2", "email": "user2@test.com"},
        }

        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future1 = executor.submit(
                requests.post, f"{self.base_url}/webhook", json=payload1
            )
            future2 = executor.submit(
                requests.post, f"{self.base_url}/webhook", json=payload2
            )

            response1 = future1.result()
            response2 = future2.result()

        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)

        with open("db.json", "r") as f:
            data = json.load(f)

        self.assertEqual(len(data), 2)

        user_ids = [entry["user_id"] for entry in data]
        self.assertIn("111", user_ids)
        self.assertIn("222", user_ids)

    def test_special_characters(self):
        """Test handling of special characters in values."""
        payload = {
            "event_type": "message",
            "timestamp": "2025-07-21T18:00:00Z",
            "user": {
                "id": "999",
                "name": 'O\'Brien "The Great"',
                "email": "test@example.com",
            },
            "metadata": {"source": "web\napp", "campaign": "summer\\2025"},
        }

        response = requests.post(f"{self.base_url}/webhook", json=payload)

        self.assertEqual(response.status_code, 200)

        with open("db.json", "r") as f:
            data = json.load(f)

        entry = data[0]
        self.assertEqual(entry["user_name"], 'O\'Brien "The Great"')
        self.assertEqual(entry["source"], "web\napp")
        self.assertEqual(entry["campaign"], "summer\\2025")

    def test_file_creation(self):
        """Test db.json creation when it doesn't exist."""
        self.assertFalse(os.path.exists("db.json"))

        payload = {
            "event_type": "first_event",
            "timestamp": "2025-07-21T19:00:00Z",
            "user": {
                "id": "001",
                "name": "First User",
                "email": "first@test.com",
            },
        }

        response = requests.post(f"{self.base_url}/webhook", json=payload)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(os.path.exists("db.json"))

        with open("db.json", "r") as f:
            data = json.load(f)

        self.assertEqual(len(data), 1)

    def test_missing_event_type(self):
        """Test validation when event_type is missing."""
        payload = {
            "timestamp": "2025-07-21T23:30:00Z",
            "user": {
                "id": "444",
                "name": "Test User",
                "email": "test@example.com",
            },
        }

        response = requests.post(f"{self.base_url}/webhook", json=payload)

        self.assertEqual(response.status_code, 400)
        self.assertFalse(os.path.exists("db.json"))

    def test_missing_user_field(self):
        """Test validation when user field is missing."""
        payload = {
            "event_type": "invalid",
            "timestamp": "2025-07-21T23:45:00Z",
        }

        response = requests.post(f"{self.base_url}/webhook", json=payload)

        self.assertEqual(response.status_code, 400)
        self.assertFalse(os.path.exists("db.json"))

    def test_empty_db_file(self):
        """Test handling of empty (but existing) db.json."""
        open("db.json", "w").close()

        payload = {
            "event_type": "recovery",
            "timestamp": "2025-07-22T00:00:00Z",
            "user": {
                "id": "333",
                "name": "Recovery User",
                "email": "recovery@test.com",
            },
        }

        response = requests.post(f"{self.base_url}/webhook", json=payload)

        self.assertEqual(response.status_code, 200)

        with open("db.json", "r") as f:
            data = json.load(f)

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["user_id"], "333")

    def test_deeply_nested_fields(self):
        """Test handling of unexpectedly deep nesting."""
        payload = {
            "event_type": "nested",
            "timestamp": "2025-07-22T00:15:00Z",
            "user": {
                "id": "nested123",
                "name": "Nested User",
                "email": "nested@test.com",
                "profile": {"settings": {"theme": "dark"}},
            },
        }

        response = requests.post(f"{self.base_url}/webhook", json=payload)

        self.assertEqual(response.status_code, 200)

        with open("db.json", "r") as f:
            data = json.load(f)

        entry = data[0]
        self.assertEqual(entry["user_id"], "nested123")
        self.assertEqual(entry["user_name"], "Nested User")
        self.assertEqual(entry["user_email"], "nested@test.com")

        if "user_profile" in entry:
            self.assertIsInstance(entry["user_profile"], dict)
            self.assertEqual(
                entry["user_profile"]["settings"]["theme"], "dark"
            )
        else:
            self.assertNotIn("theme", entry)
            self.assertNotIn("settings", entry)

    def test_put_request(self):
        """Test PUT request to webhook endpoint."""
        payload = {
            "event_type": "test",
            "timestamp": "2025-07-22T00:30:00Z",
            "user": {"id": "123", "name": "Test", "email": "test@test.com"},
        }

        response = requests.put(f"{self.base_url}/webhook", json=payload)

        self.assertEqual(response.status_code, 405)
        self.assertFalse(os.path.exists("db.json"))


if __name__ == "__main__":
    unittest.main()
