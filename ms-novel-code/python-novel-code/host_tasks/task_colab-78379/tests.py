# tests

"""Test suite for API Gateway Handler functionality."""

import unittest
import json
import threading
import time
import socket
from http.client import HTTPConnection
from main import APIGatewayHandler
import socketserver


class ReuseAddrTCPServer(socketserver.TCPServer):
    """TCPServer that enables socket reuse for Docker environments."""

    allow_reuse_address = True

    def server_bind(self):
        """Configure socket for address reuse."""
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        super().server_bind()


class TestAPIGateway(unittest.TestCase):
    """Test suite for API Gateway functionality."""

    @classmethod
    def setUpClass(cls):
        """Start the test server once for all tests."""
        cls.server_port = 8001

        for attempt in range(3):
            try:
                cls.server = ReuseAddrTCPServer(
                    ("", cls.server_port), APIGatewayHandler
                )
                break
            except OSError as e:
                if e.errno == 98 and attempt < 2:
                    time.sleep(1)
                    continue
                raise

        cls.server_thread = threading.Thread(target=cls.server.serve_forever)
        cls.server_thread.daemon = True
        cls.server_thread.start()
        time.sleep(0.5)

    @classmethod
    def tearDownClass(cls):
        """Stop the test server."""
        try:
            cls.server.shutdown()
            cls.server.server_close()
            time.sleep(0.1)
        except Exception:
            pass

    def setUp(self):
        """Set up HTTP connection for each test."""
        self.conn = HTTPConnection("localhost", self.server_port)

    def tearDown(self):
        """Close HTTP connection after each test."""
        self.conn.close()

    def _make_request(self, method, path, headers=None, body=None):
        """Make HTTP requests."""
        if headers is None:
            headers = {}

        if body is not None and isinstance(body, dict):
            body = json.dumps(body)
            if "Content-Type" not in headers:
                headers["Content-Type"] = "application/json"

        self.conn.request(method, path, body, headers)
        response = self.conn.getresponse()
        response_body = response.read().decode("utf-8")

        return {
            "status": response.status,
            "headers": dict(response.headers),
            "body": json.loads(response_body) if response_body else None,
        }

    def test_get_request_success(self):
        """Test successful GET request with path rewriting."""
        headers = {"X-Client-ID": "test-client-123"}
        response = self._make_request("GET", "/gateway/api/users", headers)

        self.assertEqual(response["status"], 200)
        self.assertEqual(response["body"]["path"], "/mock/api/users")
        self.assertEqual(response["body"]["method"], "GET")
        self.assertEqual(response["body"]["client_id"], "test-client-123")
        self.assertEqual(response["body"]["status"], "success")

    def test_post_request_with_json_body(self):
        """Test POST request with valid JSON body."""
        headers = {
            "X-Client-ID": "test-client",
            "Content-Type": "application/json",
        }
        body = {"message": "hello", "user": "john"}
        response = self._make_request(
            "POST", "/gateway/api/resource", headers, body
        )

        self.assertEqual(response["status"], 200)
        self.assertEqual(response["body"]["path"], "/mock/api/resource")
        self.assertEqual(response["body"]["method"], "POST")
        self.assertEqual(response["body"]["client_id"], "test-client")
        self.assertEqual(response["body"]["received_data"], body)

    def test_put_request_with_headers(self):
        """Test PUT request with JSON body and custom headers."""
        headers = {
            "Content-Type": "application/json",
            "X-Client-ID": "client-456",
        }
        body = {"name": "Updated User", "age": 30}
        response = self._make_request(
            "PUT", "/gateway/api/users/123", headers, body
        )

        self.assertEqual(response["status"], 200)
        self.assertEqual(response["body"]["path"], "/mock/api/users/123")
        self.assertEqual(response["body"]["method"], "PUT")
        self.assertEqual(response["body"]["client_id"], "client-456")
        self.assertEqual(response["body"]["received_data"], body)

    def test_delete_request(self):
        """Test DELETE request handling."""
        headers = {"X-Client-ID": "admin-client"}
        response = self._make_request(
            "DELETE", "/gateway/api/users/456", headers
        )

        self.assertEqual(response["status"], 200)
        self.assertEqual(response["body"]["path"], "/mock/api/users/456")
        self.assertEqual(response["body"]["method"], "DELETE")
        self.assertEqual(response["body"]["client_id"], "admin-client")

    def test_invalid_path_not_gateway(self):
        """Test request to path not starting with /gateway/."""
        response = self._make_request("GET", "/api/users")

        self.assertEqual(response["status"], 404)
        self.assertEqual(response["body"]["error"], "Not found")

    def test_invalid_method_patch(self):
        """Test unsupported HTTP method (PATCH)."""
        response = self._make_request("PATCH", "/gateway/api/resource")

        self.assertEqual(response["status"], 405)
        self.assertEqual(response["body"]["error"], "Method not allowed")

    def test_invalid_json_body(self):
        """Test POST with malformed JSON."""
        headers = {"Content-Type": "application/json"}
        self.conn.request(
            "POST", "/gateway/api/data", "{invalid json}", headers
        )
        response = self.conn.getresponse()
        response_body = json.loads(response.read().decode("utf-8"))

        self.assertEqual(response.status, 400)
        self.assertEqual(response_body["error"], "Invalid JSON payload")

    def test_oversized_payload(self):
        """Test request body exceeding 10KB limit."""
        headers = {"Content-Type": "application/json"}
        large_data = {"data": "x" * 11000}
        response = self._make_request(
            "POST", "/gateway/api/upload", headers, large_data
        )

        self.assertEqual(response["status"], 413)
        self.assertEqual(response["body"]["error"], "Payload too large")

    def test_get_with_query_parameters(self):
        """Test GET request with query string preservation."""
        response = self._make_request(
            "GET", "/gateway/api/search?q=test&limit=10&page=2"
        )

        self.assertEqual(response["status"], 200)
        self.assertEqual(
            response["body"]["path"], "/mock/api/search?q=test&limit=10&page=2"
        )
        self.assertEqual(response["body"]["method"], "GET")

    def test_gateway_headers_removed(self):
        """Verify gateway-specific headers are removed from response."""
        headers = {"X-Client-ID": "test-verify-headers"}
        response = self._make_request("GET", "/gateway/api/headers", headers)

        self.assertEqual(response["status"], 200)
        self.assertNotIn("X-Gateway-Processed", response["headers"])
        self.assertNotIn("X-Forwarded-For", response["headers"])

    def test_post_without_content_type(self):
        """Test POST request missing Content-Type header."""
        self.conn.request("POST", "/gateway/api/data", '{"test": "data"}')
        response = self.conn.getresponse()
        response_body = json.loads(response.read().decode("utf-8"))

        self.assertEqual(response.status, 400)
        self.assertEqual(
            response_body["error"],
            "Content-Type required for POST/PUT requests",
        )

    def test_empty_body_post(self):
        """Test POST with empty body."""
        headers = {"Content-Type": "application/json"}
        response = self._make_request(
            "POST", "/gateway/api/empty", headers, ""
        )

        self.assertEqual(response["status"], 400)
        self.assertEqual(
            response["body"]["error"], "Empty body not allowed for POST/PUT"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
