"""Webhook listener server that receives JSON POSTs and stores events."""

import http.server
import socketserver
import json
import os
import threading
import time
import re

DB_FILE = "db.json"
DB_LOCK = threading.Lock()
ISO_8601_REGEX = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$"


class WebhookServer(http.server.BaseHTTPRequestHandler):
    """
    A simple HTTP server that listens for POST requests.

    Transforms the incoming JSON payload and stores it to a local JSON file.
    """

    def _send_response(self, status_code, message):
        """Send a JSON response with the given status and message."""
        self.send_response(status_code)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"message": message}).encode("utf-8"))

    def _load_db(self):
        """Safely load JSON array from db.json, handling corruption."""
        with DB_LOCK:
            if not os.path.exists(DB_FILE):
                with open(DB_FILE, "w", encoding="utf-8") as f:
                    json.dump([], f)
                return []

            try:
                with open(DB_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if not isinstance(data, list):
                        raise ValueError("DB file content"
                                         " is not a JSON array.")
                    return data
            except (json.JSONDecodeError, ValueError):
                timestamp = time.strftime("%Y%m%d%H%M%S")
                corrupted_file = f"{DB_FILE}_corrupted_{timestamp}.json"
                os.rename(DB_FILE, corrupted_file)
                print(
                    f"Warning: db.json corrupted."
                    f" Renamed to {corrupted_file}. "
                    "Creating a new empty db.json."
                )
                with open(DB_FILE, "w", encoding="utf-8") as f:
                    json.dump([], f)
                return []

    def _save_db(self, data):
        """Write the given JSON array to db.json safely."""
        with DB_LOCK:
            with open(DB_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

    def do_POST(self):
        """
        Handle POST /webhook requests.

        Validates JSON payload and appends flattened version to db.json.
        """
        if self.path != "/webhook":
            self._send_response(404, "Not Found")
            return

        try:
            content_length = int(self.headers["Content-Length"])
            if content_length == 0:
                self._send_response(400, "Empty JSON Body")
                return

            post_body = self.rfile.read(content_length).decode("utf-8")
            payload = json.loads(post_body)
        except (TypeError, ValueError, json.JSONDecodeError):
            self._send_response(400,
                                "Malformed JSON Payload")
            return
        except Exception as exc:
            self._send_response(500,
                                f"Error reading request body: {exc}")
            return

        required_fields = ["event_type", "timestamp", "user"]
        if not all(field in payload for field in required_fields):
            self._send_response(400,
                                "Missing required top-level fields")
            return

        timestamp = payload.get("timestamp")
        if (not isinstance(timestamp, str) or
                not re.fullmatch(ISO_8601_REGEX, timestamp)):
            self._send_response(400,
                                "Invalid 'timestamp' format"
                                " (must be ISO 8601)")
            return

        user_data = payload.get("user")
        if not isinstance(user_data, dict):
            self._send_response(400,
                                "Invalid 'user' field: must be an object.")
            return

        for field in ["id", "name", "email"]:
            value = user_data.get(field)
            if not isinstance(value, str) or not value:
                self._send_response(400,
                                    f"Invalid 'user.{field}':"
                                    f" must be a non-empty string.")
                return

        if "@" not in user_data["email"] or "." not in user_data["email"]:
            self._send_response(400,
                                "Invalid 'user.email':"
                                " must be a valid email format.")
            return

        transformed_data = {
            "event_type": payload["event_type"],
            "timestamp": payload["timestamp"]
        }

        for key, value in user_data.items():
            transformed_data[f"user_{key}"] = value

        metadata = payload.get("metadata")
        if isinstance(metadata, dict):
            for key, value in metadata.items():
                transformed_data[key] = value

        try:
            db_data = self._load_db()
            db_data.append(transformed_data)
            self._save_db(db_data)
            self._send_response(200,
                                "Webhook received and processed successfully")
        except Exception as exc:
            self._send_response(500, f"Error processing webhook: {exc}")

    def do_GET(self):
        """Reject GET requests."""
        self._send_response(405, "Method Not Allowed")

    def do_PUT(self):
        """Reject PUT requests."""
        self._send_response(405, "Method Not Allowed")

    def do_DELETE(self):
        """Reject DELETE requests."""
        self._send_response(405, "Method Not Allowed")


class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    """Handle requests in a separate thread."""

    pass


def run_server(port=8000):
    """Start the HTTP webhook server on the given port."""
    server_address = ("", port)
    httpd = ThreadingHTTPServer(server_address, WebhookServer)
    print(f"Starting webhook server on port {port}...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        httpd.shutdown()
        httpd.server_close()


if __name__ == "__main__":
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
    else:
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, list):
                    raise ValueError("DB file is not a JSON array.")
        except (json.JSONDecodeError, ValueError):
            timestamp = time.strftime("%Y%m%d%H%M%S")
            corrupted_file = f"{DB_FILE}_corrupted_{timestamp}.json"
            os.rename(DB_FILE, corrupted_file)
            print(
                f"Warning: db.json corrupted on startup. "
                f"Renamed to {corrupted_file}. Creating new empty db.json."
            )
            with open(DB_FILE, "w", encoding="utf-8") as f:
                json.dump([], f)

    run_server()

