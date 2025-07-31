
"""
Webhook Network Simulation System

This module simulates real-world network delays and failures in webhook
communication. It consists of a WebhookServer that randomly delays or drops
responses, and a WebhookClient with retry logic and exponential backoff.

Usage:
    python simulate_network_conditions.py --mode server
    python simulate_network_conditions.py --mode client
"""

import argparse
import json
import random
import time
import threading
from datetime import datetime
from http.server import HTTPServer, ThreadingHTTPServer, BaseHTTPRequestHandler
from http.client import HTTPConnection, HTTPSConnection
from typing import Dict, Any, Optional
from urllib.parse import urlparse
import socket
import sys


class TimestampedLogger:
    """A simple logger that adds timestamps to all messages."""

    @staticmethod
    def log(message: str) -> None:
        """Log a message with timestamp to stdout.

        Args:
            message: The message to log
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        print(f"[{timestamp}] {message}")


class WebhookRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the webhook server."""

    def do_POST(self) -> None:
        """Handle POST requests with random delays and drops."""
        client_address = self.client_address[0]

        # Check if we should drop this request
        if random.random() < self.server.drop_probability:
            TimestampedLogger.log(
                f"[Server] Dropping request from {client_address} "
                f"(simulated failure)"
            )
            # Close connection without response to simulate dropped request
            self.connection.close()
            return

        # Read request body
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 0:
            body = self.rfile.read(content_length)
            try:
                json.loads(body.decode('utf-8'))
                TimestampedLogger.log(
                    f"[Server] Received request from {client_address}"
                )
            except (json.JSONDecodeError, UnicodeDecodeError):
                TimestampedLogger.log(
                    f"[Server] Received malformed request from "
                    f"{client_address}"
                )
        else:
            TimestampedLogger.log(
                f"[Server] Received empty request from {client_address}"
            )

        # Apply random delay
        delay = random.uniform(0, self.server.max_delay)
        if delay > 0:
            TimestampedLogger.log(
                f"[Server] Delaying response for {delay:.1f}s..."
            )
            time.sleep(delay)

        # Send successful response
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()

        response = {"status": "success", "timestamp": time.time()}
        self.wfile.write(json.dumps(response).encode('utf-8'))

        TimestampedLogger.log("[Server] Responded with 200 OK")


class WebhookServer:
    """HTTP server that simulates network instability with delays and drops."""

    def __init__(self, host: str, port: int, drop_probability: float,
                 max_delay: float) -> None:
        """Initialize the webhook server.

        Args:
            host: The host address to bind to
            port: The port number to listen on
            drop_probability: Probability (0.0-1.0) of dropping requests
            max_delay: Maximum delay in seconds for responses

        Raises:
            ValueError: If parameters are out of valid ranges
        """
        if not 0.0 <= drop_probability <= 1.0:
            raise ValueError("drop_probability must be between 0.0 and 1.0")
        if max_delay < 0 or max_delay > 10:
            raise ValueError("max_delay must be between 0 and 10 seconds")

        self.host = host
        self.port = port
        self.drop_probability = drop_probability
        self.max_delay = max_delay
        self.server: Optional[HTTPServer] = None
        self.server_thread: Optional[threading.Thread] = None

    def start(self, threaded: bool = False) -> None:
        """Start the HTTP server in blocking or threaded mode.

        Args:
            threaded: If True, start server in a separate thread
        """
        try:
            # Use ThreadingHTTPServer for concurrent request handling
            self.server = ThreadingHTTPServer((self.host, self.port),
                                            WebhookRequestHandler)
            # Pass configuration to request handler
            self.server.drop_probability = self.drop_probability
            self.server.max_delay = self.max_delay

            TimestampedLogger.log(
                f"[Server] Starting webhook server on {self.host}:"
                f"{self.port}"
            )
            TimestampedLogger.log(
                f"[Server] Drop probability: {self.drop_probability:.1%}, "
                f"Max delay: {self.max_delay}s"
            )

            if threaded:
                self.server_thread = threading.Thread(
                    target=self.server.serve_forever
                )
                self.server_thread.daemon = True
                self.server_thread.start()
                TimestampedLogger.log("[Server] Server started in background")
            else:
                TimestampedLogger.log(
                    f"[Server] Listening on port {self.port}"
                )
                self.server.serve_forever()

        except OSError as e:
            TimestampedLogger.log(f"[Server] Failed to start server: {e}")
            raise

    def stop(self) -> None:
        """Stop the server gracefully."""
        if self.server:
            TimestampedLogger.log("[Server] Shutting down server...")
            self.server.shutdown()
            self.server.server_close()

            if self.server_thread:
                self.server_thread.join(timeout=5)


class WebhookClient:
    """HTTP client with retry logic and exponential backoff."""

    def __init__(self, url: str, retries: int, backoff_factor: float,
                 timeout: float) -> None:
        """Initialize the webhook client.

        Args:
            url: The target webhook URL
            retries: Number of retry attempts
            backoff_factor: Exponential backoff multiplier
            timeout: Request timeout in seconds

        Raises:
            ValueError: If parameters are invalid
        """
        if retries < 0:
            raise ValueError("retries must be non-negative")
        if backoff_factor <= 0:
            raise ValueError("backoff_factor must be positive")
        if timeout <= 0:
            raise ValueError("timeout must be positive")

        self.url = url
        self.retries = retries
        self.backoff_factor = backoff_factor
        self.timeout = timeout

        # Parse URL for connection details
        parsed = urlparse(url)
        self.scheme = parsed.scheme
        self.host = parsed.hostname
        self.port = parsed.port
        self.path = parsed.path or '/'

        if not self.host:
            raise ValueError("Invalid URL: missing hostname")

        # Set default ports
        if not self.port:
            self.port = 443 if self.scheme == 'https' else 80

    def _create_connection(self) -> HTTPConnection:
        """Create an HTTP connection based on URL scheme.

        Returns:
            HTTPConnection or HTTPSConnection instance
        """
        if self.scheme == 'https':
            return HTTPSConnection(self.host, self.port, timeout=self.timeout)
        else:
            return HTTPConnection(self.host, self.port, timeout=self.timeout)

    def _send_request(self, payload: Dict[str, Any]) -> bool:
        """Send a single HTTP request.

        Args:
            payload: JSON payload to send

        Returns:
            True if request succeeded, False otherwise

        Raises:
            Various exceptions for different failure types
        """
        conn = None
        try:
            # Serialize payload
            json_data = json.dumps(payload)

            # Create connection
            conn = self._create_connection()
            conn.connect()

            # Send request
            headers = {
                'Content-Type': 'application/json',
                'Content-Length': str(len(json_data.encode('utf-8')))
            }

            conn.request('POST', self.path, json_data, headers)
            response = conn.getresponse()

            if response.status == 200:
                return True
            else:
                raise RuntimeError(f"HTTP {response.status}: "
                                 f"{response.reason}")

        finally:
            if conn:
                conn.close()

    def send_payload(self, payload: Dict[str, Any]) -> bool:
        """Send JSON payload with retry logic and exponential backoff.

        Args:
            payload: The JSON payload to send

        Returns:
            True if payload was successfully sent, False otherwise
        """
        attempt = 0
        max_attempts = self.retries + 1

        while attempt < max_attempts:
            attempt += 1

            try:
                # Attempt to send the request
                if self._send_request(payload):
                    TimestampedLogger.log(
                        f"[Client] Attempt {attempt}: Success - "
                        f"Status Code 200"
                    )
                    return True

            except socket.timeout:
                error_msg = "TimeoutError"
                TimestampedLogger.log(
                    f"[Client] Attempt {attempt}: {error_msg}"
                )

            except (socket.error, ConnectionRefusedError, OSError):
                error_msg = "ConnectionError"
                TimestampedLogger.log(
                    f"[Client] Attempt {attempt}: {error_msg}"
                )

            except (TypeError, ValueError) as e:
                TimestampedLogger.log(
                    f"[Client] Attempt {attempt}: JSON serialization error: {e}"
                )
                return False  # Don't retry serialization errors

            except Exception as e:
                TimestampedLogger.log(
                    f"[Client] Attempt {attempt}: {type(e).__name__}: {e}"
                )

            # Check if we should retry
            if attempt < max_attempts:
                # Calculate backoff delay with jitter
                base_delay = self.backoff_factor * (2 ** (attempt - 1))
                jitter = random.uniform(0.1, 0.3) * base_delay
                delay = base_delay + jitter

                TimestampedLogger.log(
                    f"[Client] Retrying in {delay:.1f}s"
                )
                time.sleep(delay)
            else:
                TimestampedLogger.log(
                    f"[Client] Attempt {attempt}: Failed - Max retries reached"
                )

        return False


def run_server_mode(args) -> None:
    """Run the application in server mode."""
    server = WebhookServer(
        host=args.host,
        port=args.port,
        drop_probability=args.drop_probability,
        max_delay=args.max_delay
    )

    try:
        server.start(threaded=False)
    except KeyboardInterrupt:
        TimestampedLogger.log("[Server] Received interrupt signal")
    finally:
        server.stop()


def run_client_mode(args) -> None:
    """Run the application in client mode."""
    client = WebhookClient(
        url=args.url,
        retries=args.retries,
        backoff_factor=args.backoff_factor,
        timeout=args.timeout
    )

    # Prepare payload
    payload = {
        "message": args.message,
        "timestamp": time.time(),
        "client_id": "webhook-client-001"
    }

    TimestampedLogger.log(f"[Client] Sending payload to {args.url}")
    TimestampedLogger.log(f"[Client] Retries: {args.retries}, "
                         f"Backoff: {args.backoff_factor}, "
                         f"Timeout: {args.timeout}s")

    success = client.send_payload(payload)

    if success:
        TimestampedLogger.log("[Client] Payload sent successfully")
        sys.exit(0)
    else:
        TimestampedLogger.log("[Client] Failed to send payload")
        sys.exit(1)


def main() -> None:
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(
        description="Webhook Network Simulation System"
    )
    parser.add_argument(
        '--mode',
        choices=['server', 'client'],
        required=True,
        help='Operation mode: server or client'
    )

    # Server arguments
    parser.add_argument(
        '--host',
        default='localhost',
        help='Server host address (default: localhost)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8080,
        help='Server port number (default: 8080)'
    )
    parser.add_argument(
        '--drop-probability',
        type=float,
        default=0.3,
        help='Request drop probability 0.0-1.0 (default: 0.3)'
    )
    parser.add_argument(
        '--max-delay',
        type=float,
        default=5.0,
        help='Maximum response delay in seconds (default: 5.0)'
    )

    # Client arguments
    parser.add_argument(
        '--url',
        default='http://localhost:8080',
        help='Webhook URL (default: http://localhost:8080)'
    )
    parser.add_argument(
        '--retries',
        type=int,
        default=3,
        help='Number of retry attempts (default: 3)'
    )
    parser.add_argument(
        '--backoff-factor',
        type=float,
        default=1.0,
        help='Exponential backoff factor (default: 1.0)'
    )
    parser.add_argument(
        '--timeout',
        type=float,
        default=10.0,
        help='Request timeout in seconds (default: 10.0)'
    )
    parser.add_argument(
        '--message',
        default='Hello from webhook client!',
        help='Message to send in payload'
    )

    args = parser.parse_args()

    try:
        if args.mode == 'server':
            run_server_mode(args)
        else:
            run_client_mode(args)

    except ValueError as e:
        TimestampedLogger.log(f"[Error] Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        TimestampedLogger.log(f"[Error] Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

