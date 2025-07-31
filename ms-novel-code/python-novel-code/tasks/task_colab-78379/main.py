"""API Gateway simulation for HTTP server requests."""

import http.server
import socketserver
import json
import re
from urllib.parse import urlparse

PORT = 8000
MAX_REQUEST_BODY_SIZE = 10 * 1024


class APIGatewayHandler(http.server.BaseHTTPRequestHandler):
    """Handles HTTP requests with simulated API Gateway behavior."""

    SUPPORTED_METHODS = ['GET', 'POST', 'PUT', 'DELETE']
    GATEWAY_PREFIX = '/gateway/'
    MOCK_PREFIX = '/mock/'
    GATEWAY_INTERNAL_HEADERS = ['X-Gateway-Processed', 'X-Forwarded-For']
    ALLOWED_CLIENT_HEADERS = ['Host', 'X-Client-ID', 'Content-Type']

    def _send_error_response(self, status_code: int, message: str):
        """Send a JSON-formatted error response."""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        response_body = json.dumps({"error": message}).encode('utf-8')
        self.wfile.write(response_body)

    def _process_request(self, method: str):
        """Parse and validate the request and delegate to the mock handler."""
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        query_string = parsed_url.query

        if not path.startswith(self.GATEWAY_PREFIX):
            self._send_error_response(404, "Not Found")
            return

        incoming_headers = {k: v for k, v in self.headers.items()}
        filtered_headers = {
            h: incoming_headers[h] for h in self.ALLOWED_CLIENT_HEADERS
            if h in incoming_headers
        }

        if 'X-Client-ID' in filtered_headers:
            client_id = filtered_headers['X-Client-ID']
            if not isinstance(client_id, str) or not re.fullmatch(
                r'^[a-zA-Z0-9]{1,64}$', client_id
            ):
                self._send_error_response(
                    400, "Invalid X-Client-ID header format or length."
                )
                return

        request_body = b''
        if method in ['POST', 'PUT']:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > MAX_REQUEST_BODY_SIZE:
                self._send_error_response(413, "Payload Too Large")
                return
            if (
                'Content-Type' not in filtered_headers or
                filtered_headers['Content-Type'] != 'application/json'
            ):
                self._send_error_response(
                    400,
                    "Content-Type must be"
                    " application/json for POST/PUT requests."
                )
                return
            try:
                request_body = self.rfile.read(content_length)
                if request_body:
                    decoded_body = json.loads(request_body.decode('utf-8'))
                    if not isinstance(decoded_body, dict):
                        self._send_error_response(
                            400, "Request body must be a valid JSON object."
                        )
                        return
            except json.JSONDecodeError:
                self._send_error_response(400, "Invalid JSON payload.")
                return
            except UnicodeDecodeError:
                self._send_error_response(
                    400, "Request body must be UTF-8 encoded."
                )
                return
        elif int(self.headers.get('Content-Length', 0)) > 0:
            self._send_error_response(
                400, "Request body not allowed for this method."
            )
            return

        rewritten_path = self._rewrite_path(path)
        if query_string:
            rewritten_path += '?' + query_string

        forwarded_headers = self._add_gateway_headers(filtered_headers)
        status_code, mock_response_headers, mock_response_body = (
            self._handle_mock_endpoint(
                method, rewritten_path, forwarded_headers, request_body
            )
        )
        final_headers = self._remove_gateway_headers(mock_response_headers)
        self.send_response(status_code)
        for header, value in final_headers.items():
            self.send_header(header, value)
        self.end_headers()
        self.wfile.write(mock_response_body)

    def do_get(self):
        """Handle GET requests."""
        self._process_request('GET')

    def do_post(self):
        """Handle POST requests."""
        self._process_request('POST')

    def do_put(self):
        """Handle PUT requests."""
        self._process_request('PUT')

    def do_delete(self):
        """Handle DELETE requests."""
        self._process_request('DELETE')

    def do_head(self):
        """Reject unsupported HEAD requests."""
        self._send_error_response(405, "Method not allowed")

    def do_options(self):
        """Reject unsupported OPTIONS requests."""
        self._send_error_response(405, "Method not allowed")

    def _rewrite_path(self, path: str) -> str:
        """Rewrite path from gateway to mock prefix."""
        return path.replace(self.GATEWAY_PREFIX, self.MOCK_PREFIX, 1)

    def _add_gateway_headers(self, headers: dict) -> dict:
        """Add internal headers to simulate gateway forwarding."""
        modified_headers = headers.copy()
        modified_headers['X-Gateway-Processed'] = 'true'
        modified_headers['X-Forwarded-For'] = self.client_address[0]
        return modified_headers

    def _remove_gateway_headers(self, headers: dict) -> dict:
        """Remove internal headers before response."""
        return {
            k: v for k, v in headers.items()
            if k not in self.GATEWAY_INTERNAL_HEADERS
        }

    def _handle_mock_endpoint(
        self, method: str, path: str, headers: dict, body: bytes
    ) -> tuple[int, dict, bytes]:
        """Simulate the internal mock endpoint logic."""
        print(
            f"Mock Endpoint Received: Method={method}, Path={path}, "
            f"Headers={headers}, Body={body.decode('utf-8', errors='ignore')}"
        )
        status_code = 200
        response_headers = {'Content-Type': 'application/json'}
        response_body_data = {
            "status": "success",
            "message": "Processed by mock endpoint",
            "method": method,
            "path": path,
            "gateway_processed": headers.get('X-Gateway-Processed'),
            "client_id": headers.get('X-Client-ID', 'N/A')
        }

        parsed_url = urlparse(path)
        mock_path_segments = parsed_url.path.split('/')

        if (len(mock_path_segments) > 2
                and mock_path_segments[2] == 'nonexistent'):
            status_code = 404
            response_body_data = {
                "error": "Resource not found at mock endpoint"
            }
        elif method in ['POST', 'PUT'] and body:
            try:
                decoded_body = json.loads(body.decode('utf-8'))
                response_body_data["received_payload"] = decoded_body
            except json.JSONDecodeError:
                status_code = 400
                response_body_data = {
                    "error": "Invalid JSON received by mock endpoint"
                }

        response_headers['X-Mock-Service-Header'] = 'true'
        response_headers['X-Gateway-Processed'] = 'true-from-mock'

        return (
            status_code,
            response_headers,
            json.dumps(response_body_data).encode('utf-8')
        )


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    """Threaded HTTP server with daemon threads enabled."""

    daemon_threads = True


if __name__ == "__main__":
    print(f"Starting API Gateway on port {PORT}...")
    try:
        with ThreadedHTTPServer(("", PORT), APIGatewayHandler) as httpd:
            print(f"Server running on http://localhost:{PORT}")
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down API Gateway.")
    except Exception as e:
        print(f"An error occurred: {e}")

