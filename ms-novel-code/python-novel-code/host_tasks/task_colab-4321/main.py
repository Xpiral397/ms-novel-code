# code
"""API Gateway Simulator using Python's http.server and socketserver.

This server simulates API gateway behavior:
- Validates URI path and request body
- Limits headers and body size
- Adds/removes custom headers
- Forwards to a mock internal endpoint
"""

import http.server
import socketserver
import json
import re
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timezone

PORT = 8080
MAX_BODY_SIZE = 10 * 1024  # 10KB
MAX_HEADERS = 20

GATEWAY_CUSTOM_HEADERS = {
    "X-Gateway-ID": "api-gateway-001",
    "X-Trace-ID": "trace-12345",
}


class APIGatewayHandler(http.server.BaseHTTPRequestHandler):
    """Handles HTTP requests as a simulated API Gateway."""

    def do_GET(self) -> None:
        """Handle GET requests."""
        self.handle_request("GET")

    def do_POST(self) -> None:
        """Handle POST requests."""
        self.handle_request("POST")

    def handle_request(self, method: str) -> None:
        """Parse and validate incoming request, then forward to mock."""
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        if not path.startswith("/api/"):
            self.send_error_response(404, "Not Found", "Invalid API path.")
            return

        resource_match = re.match(r"/api/([a-zA-Z0-9]+)$", path)
        if not resource_match:
            self.send_error_response(
                404, "Not Found", "Invalid resource name in API path."
            )
            return

        body = b""
        if method == "POST":
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length > MAX_BODY_SIZE:
                self.send_error_response(
                    413,
                    "Payload Too Large",
                    f"Request body exceeds {MAX_BODY_SIZE} bytes.",
                )
                return
            try:
                body = self.rfile.read(content_length)
                json.loads(body)  # Validate JSON
            except json.JSONDecodeError:
                self.send_error_response(400,
                                         "Bad Request", "Invalid JSON body.")
                return
            except Exception:
                self.send_error_response(
                    400, "Bad Request", "Error reading request body."
                )
                return

        forward_headers = {k: v for k, v in self.headers.items()}

        if len(forward_headers) + len(GATEWAY_CUSTOM_HEADERS) > MAX_HEADERS:
            self.send_error_response(
                400,
                "Bad Request",
                f"Too many headers. Maximum allowed is {MAX_HEADERS}.",
            )
            return

        try:
            (status_code, response_headers,
             response_body) = self.forward_request(
                method, path, forward_headers, body
            )
            self.send_response(status_code)
            for header, value in response_headers.items():
                self.send_header(header, value)
            self.end_headers()
            self.wfile.write(response_body)
        except Exception as e:
            print(f"Error during request forwarding: {e}")
            self.send_error_response(
                500, "Internal Server Error", "An unexpected error occurred."
            )

    def forward_request(
        self, method: str, path: str, headers: dict, body: bytes
    ) -> tuple[int, dict, bytes]:
        """Forward the request to a mock internal endpoint."""
        rewritten_path = self.rewrite_uri(path)
        modified_headers = self.add_custom_headers(headers)
        (status_code, mock_response_headers,
         mock_response_body) = self.mock_endpoint(
            rewritten_path, method, modified_headers, body
        )
        final_response_headers = (self.remove_custom_headers
                                  (mock_response_headers))
        return status_code, final_response_headers, mock_response_body

    def rewrite_uri(self, path: str) -> str:
        """Rewrite the incoming URI to an internal path."""
        parsed_path = urlparse(path)
        resource_name = parsed_path.path.split("/api/", 1)[1]
        new_path = f"/internal/{resource_name}"
        if parsed_path.query:
            new_path += f"?{parsed_path.query}"
        return new_path

    def add_custom_headers(self, headers: dict) -> dict:
        """Add gateway-specific custom headers."""
        new_headers = headers.copy()
        new_headers.update(GATEWAY_CUSTOM_HEADERS)
        return new_headers

    def remove_custom_headers(self, headers: dict) -> dict:
        """Remove gateway-injected headers from the response."""
        final_headers = headers.copy()
        for header_name in GATEWAY_CUSTOM_HEADERS:
            final_headers.pop(header_name, None)
        return final_headers

    def mock_endpoint(
        self, path: str, method: str, headers: dict, body: bytes
    ) -> tuple[int, dict, bytes]:
        """Simulate a mock internal endpoint and return dummy response."""
        parsed_path = urlparse(path)
        resource_name = parsed_path.path.split("/internal/", 1)[1]
        query_params = parse_qs(parsed_path.query)

        response_payload = {
            "resource": resource_name,
            "status": "received",
            "timestamp": datetime.now(timezone.utc)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z"),
        }

        if method == "GET":
            for key, values in query_params.items():
                response_payload[key] = values[0]
        elif method == "POST" and body:
            try:
                request_data = json.loads(body)
                response_payload.update(request_data)
            except json.JSONDecodeError:
                pass

        mock_headers = {
            "Content-Type": "application/json",
            "X-Internal-Processing-Time": "10ms",
            "X-Gateway-ID": "should-be-removed",
            "X-Trace-ID": "should-also-be-removed",
        }
        mock_headers.update(
            {
                k: v
                for k, v in headers.items()
                if k.startswith("X-") and k not in GATEWAY_CUSTOM_HEADERS
            }
        )

        return 200, mock_headers, json.dumps(response_payload).encode("utf-8")

    def send_error_response(
        self, status_code: int, status_message: str, error_detail: str
    ) -> None:
        """Send JSON-formatted error response."""
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        response = {
            "status": "error",
            "code": status_code,
            "message": status_message,
            "details": error_detail,
            "timestamp": datetime.now(timezone.utc)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z"),
        }
        self.wfile.write(json.dumps(response).encode("utf-8"))


def run_server():
    """Start the threaded HTTP server."""
    with (socketserver.ThreadingTCPServer(("", PORT),
                                          APIGatewayHandler) as httpd):
        print(f"Serving on port {PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down the server.")
            httpd.shutdown()
            httpd.server_close()


if __name__ == "__main__":
    run_server()

