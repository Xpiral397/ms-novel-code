# tests

"""Unit tests for WebhookClient and WebhookServer."""

import unittest
import threading
import time
from http.client import HTTPConnection
from main import WebhookServer, WebhookClient


class TestWebhookSystem(unittest.TestCase):
    """Tests for WebhookClient and WebhookServer."""

    def setUp(self):
        """Start webhook server on dynamic port."""
        self.server = WebhookServer(
            host='localhost',
            port=0,
            drop_probability=0.0,
            max_delay=0.0
        )
        self.server_thread = threading.Thread(
            target=self.server.start,
            kwargs={'threaded': True},
            daemon=True
        )
        self.server_thread.start()
        max_wait = 50
        wait_count = 0
        while wait_count < max_wait:
            time.sleep(0.1)
            if hasattr(self.server, 'server') and self.server.server:
                break
            wait_count += 1
        if not hasattr(self.server, 'server') or not self.server.server:
            raise RuntimeError("Server failed to start")
        self.port = self.server.server.server_address[1]
        self.base_url = f'http://localhost:{self.port}'

    def tearDown(self):
        """Stop the server after test."""
        self.server.stop()
        time.sleep(0.1)

    def test_successful_delivery(self):
        """Verify successful webhook delivery."""
        client = WebhookClient(self.base_url, 1, 0.1, 2)
        payload = {"message": "test"}
        self.assertTrue(client.send_payload(payload))

    def test_timeout_due_to_delay(self):
        """Verify timeout when all requests are dropped."""
        self.server.stop()
        time.sleep(0.3)
        self.server = WebhookServer('localhost', 0, 1.0, 0.0)
        self.server_thread = threading.Thread(
            target=self.server.start,
            kwargs={'threaded': True},
            daemon=True
        )
        self.server_thread.start()
        max_wait = 50
        wait_count = 0
        while wait_count < max_wait:
            time.sleep(0.1)
            if hasattr(self.server, 'server') and self.server.server:
                break
            wait_count += 1
        port = self.server.server.server_address[1]
        client = WebhookClient(f'http://localhost:{port}', 2, 0.1, 1.0)
        payload = {"message": "timeout"}
        self.assertFalse(client.send_payload(payload))

    def test_all_requests_dropped(self):
        """Verify delivery fails if all requests are dropped."""
        self.server.stop()
        time.sleep(0.3)
        self.server = WebhookServer('localhost', 0, 1.0, 0.0)
        self.server_thread = threading.Thread(
            target=self.server.start,
            kwargs={'threaded': True},
            daemon=True
        )
        self.server_thread.start()
        max_wait = 50
        wait_count = 0
        while wait_count < max_wait:
            time.sleep(0.1)
            if hasattr(self.server, 'server') and self.server.server:
                break
            wait_count += 1
        port = self.server.server.server_address[1]
        client = WebhookClient(f'http://localhost:{port}', 2, 0.1, 1.0)
        payload = {"message": "drop test"}
        self.assertFalse(client.send_payload(payload))

    def test_malformed_payload(self):
        """Verify JSON serialization error on invalid payload."""
        client = WebhookClient(self.base_url, 1, 0.1, 1.0)
        payload = {"bad": set([1, 2, 3])}
        self.assertFalse(client.send_payload(payload))

    def test_invalid_url_format(self):
        """Verify ValueError on malformed URL."""
        with self.assertRaises(ValueError):
            WebhookClient('invalid-url', 1, 1.0, 1.0)

    def test_zero_retries(self):
        """Verify delivery with zero retries."""
        client = WebhookClient(self.base_url, 0, 0.1, 1.0)
        payload = {"key": "value"}
        self.assertTrue(client.send_payload(payload))

    def test_max_delay_boundary(self):
        """Verify delivery within maximum delay limit."""
        self.server.stop()
        time.sleep(0.3)
        self.server = WebhookServer('localhost', 0, 0.0, 10.0)
        self.server_thread = threading.Thread(
            target=self.server.start,
            kwargs={'threaded': True},
            daemon=True
        )
        self.server_thread.start()
        max_wait = 50
        wait_count = 0
        while wait_count < max_wait:
            time.sleep(0.1)
            if hasattr(self.server, 'server') and self.server.server:
                break
            wait_count += 1
        port = self.server.server.server_address[1]
        client = WebhookClient(f'http://localhost:{port}', 1, 0.1, 15.0)
        payload = {"slow": True}
        self.assertTrue(client.send_payload(payload))

    def test_server_shutdown_during_request(self):
        """Verify delivery fails after server shutdown."""
        client = WebhookClient(self.base_url, 1, 0.1, 1.0)
        self.server.stop()
        payload = {"interrupt": True}
        self.assertFalse(client.send_payload(payload))

    def test_invalid_payload_type(self):
        """Verify serialization failure for invalid payload type."""
        client = WebhookClient(self.base_url, 1, 0.1, 1.0)
        payload = {"bad": set([1, 2, 3])}
        self.assertFalse(client.send_payload(payload))

    def test_payload_with_non_serializable_object(self):
        """Verify serialization failure on custom object."""

        class NonSerializable:
            pass

        client = WebhookClient(self.base_url, 1, 0.1, 1.0)
        payload = {"obj": NonSerializable()}
        self.assertFalse(client.send_payload(payload))

    def test_large_payload(self):
        """Verify delivery of large payload."""
        client = WebhookClient(self.base_url, 1, 0.1, 10.0)
        payload = {"data": "x" * 100_000}
        self.assertTrue(client.send_payload(payload))

    def test_multiple_payloads_in_sequence(self):
        """Verify sending multiple sequential payloads."""
        client = WebhookClient(self.base_url, 1, 0.1, 2.0)
        for i in range(5):
            payload = {"sequence": i}
            self.assertTrue(client.send_payload(payload))

    def test_unreachable_port(self):
        """Verify failure for unreachable port."""
        client = WebhookClient('http://localhost:9999', 1, 0.1, 1.0)
        payload = {"fail": True}
        self.assertFalse(client.send_payload(payload))

    def test_server_responds_non_200(self):
        """Verify failure when server is down."""
        self.server.stop()
        time.sleep(0.3)
        client = WebhookClient(self.base_url, 1, 0.1, 1.0)
        payload = {"error": True}
        self.assertFalse(client.send_payload(payload))

    def test_partial_json_failure(self):
        """Verify server handles malformed JSON gracefully."""
        conn = HTTPConnection("localhost", self.port)
        conn.request(
            "POST",
            "/",
            body=b'{"incomplete": ',
            headers={"Content-Type": "application/json"}
        )
        resp = conn.getresponse()
        self.assertEqual(resp.status, 200)

    def test_invalid_method_handling(self):
        """Verify server response to unsupported method."""
        conn = HTTPConnection("localhost", self.port)
        conn.request("GET", "/")
        resp = conn.getresponse()
        self.assertEqual(resp.status, 501)


if __name__ == '__main__':
    unittest.main()
