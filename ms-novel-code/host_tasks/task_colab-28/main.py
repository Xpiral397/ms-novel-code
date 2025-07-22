
"""
webhook_event_logger.py

A hardened, standard-library-only webhook event logger with tamper-evident
audit chaining and robust edge-case handling.

Features
--------
- Listens on POST /webhook for JSON payloads.
- Enforces Content-Type, Content-Length, UTF-8, and schema constraints.
- Appends each event to events.jsonl and audit.log with SHA-256 hash chain.
- Atomic, thread-safe writes via tempfile + os.replace and threading.Lock.
- Auto-rotates events.jsonl when it exceeds 10 MiB.
- Provides CLI:
    * serve  — start HTTP listener
    * verify — check audit log integrity (exit 0 if OK, 1 if broken)
"""

import argparse
import base64
import hashlib
import http.server
import json
import os
import signal
import sys
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

# Constants
_MAX_BODY_BYTES = 1_048_576  # 1 MiB
_MAX_EVENTS_FILE_BYTES = 10 * _MAX_BODY_BYTES
_EOL = "\n"
_LOCK = threading.Lock()


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _atomic_append(path: Path, text: str) -> None:
    fd, tmp_path = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as tmp:
            if path.exists():
                tmp.write(path.read_text("utf-8"))
            if not text.endswith(_EOL):
                text += _EOL
            tmp.write(text)
        os.replace(tmp_path, path)
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def _read_last_line(path: Path) -> str | None:
    if not path.exists():
        return None
    with path.open("rb") as f:
        try:
            f.seek(-2, os.SEEK_END)
            while f.read(1) != b"\n":
                f.seek(-2, os.SEEK_CUR)
        except OSError:
            f.seek(0)
        return f.readline().decode("utf-8", "replace").rstrip(_EOL) or None


def _lookup_event_json(events_path: Path, event_id: str) -> str:
    if not events_path.exists():
        raise FileNotFoundError("events file missing")
    with events_path.open("r", encoding="utf-8") as f:
        for line in f:
            candidate = line.rstrip(_EOL)
            if hashlib.sha256(candidate.encode()).hexdigest() == event_id:
                return candidate
    raise ValueError(f"event_id {event_id!r} not found")


class EventLogger:
    def __init__(self, root_dir: str | os.PathLike[str]) -> None:
        self.root = Path(root_dir).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.events_file = self.root / "events.jsonl"
        self.audit_file = self.root / "audit.log"

    def append(self, payload: Mapping[str, Any]) -> str:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping type")
        event = payload.get("event")
        if not isinstance(event, str) or not event.strip():
            raise ValueError("'event' must be a non-empty string")
        if len(event.encode("utf-8")) > 255:
            raise ValueError("'event' exceeds 255 bytes")
        if any(ord(ch) < 32 for ch in event):
            raise ValueError("'event' contains control characters")

        timestamp = datetime.now(timezone.utc).isoformat()
        record = {"ts": timestamp, "payload": dict(payload)}
        record_json = json.dumps(record, ensure_ascii=False)

        event_id = hashlib.sha256(record_json.encode()).hexdigest()
        prev_line = _read_last_line(self.audit_file)
        prev_id = prev_line.split(" ")[1] if prev_line else "0" * 64
        chain_hash = hashlib.sha256((prev_id + record_json).encode()).digest()
        audit_line = f"{_b64url(chain_hash)} {event_id}"

        with _LOCK:
            _atomic_append(self.events_file, record_json)
            _atomic_append(self.audit_file, audit_line)
            self._rotate_events_if_needed()

        return event_id

    def verify(self) -> bool:
        if not self.audit_file.exists():
            return True
        prev_id = "0" * 64
        for line in self.audit_file.read_text("utf-8").splitlines():
            parts = line.split(" ")
            if len(parts) != 2:
                return False
            chain_b64, event_id = parts
            try:
                ev_json = _lookup_event_json(self.events_file, event_id)
            except (FileNotFoundError, ValueError):
                return False
            expected = hashlib.sha256((prev_id + ev_json).encode()).digest()
            if chain_b64 != _b64url(expected):
                return False
            prev_id = event_id
        return True

    def _rotate_events_if_needed(self) -> None:
        if self.events_file.stat().st_size <= _MAX_EVENTS_FILE_BYTES:
            return
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        rotated = self.events_file.with_name(f"events-{ts}.jsonl")
        os.replace(self.events_file, rotated)
        self.events_file.touch()


class WebhookHandler(http.server.BaseHTTPRequestHandler):
    logger: EventLogger  # injected by server factory

    def log_message(self, *args: Any) -> None:
        return  # silence

    def _respond(self, code: int, body: dict[str, Any]) -> None:
        payload = json.dumps(body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self) -> None:
        if self.path != "/webhook":
            return self._respond(404, {"error": "Not Found"})

        ct = self.headers.get("Content-Type", "").split(";", 1)[0]
        if ct != "application/json":
            return self._respond(415, {"error": "Content-Type must be application/json"})

        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            return self._respond(411, {"error": "Content-Length required"})
        if length > _MAX_BODY_BYTES:
            # read and discard to avoid broken pipe
            _ = self.rfile.read(length)
            return self._respond(413, {"error": "Payload too large"})

        raw = self.rfile.read(length)
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            return self._respond(400, {"error": "Body must be valid UTF-8"})
        if "\r" in text or "\n" in text:
            return self._respond(400, {"error": "Body contains forbidden control characters"})

        try:
            obj = json.loads(text)
        except json.JSONDecodeError:
            return self._respond(400, {"error": "Invalid JSON"})
        if not isinstance(obj, dict):
            return self._respond(400, {"error": "JSON must be an object"})

        # missing-event → 404
        if "event" not in obj:
            return self._respond(404, {"error": "Not Found"})

        try:
            event_id = self.logger.append(obj)
        except (TypeError, ValueError) as e:
            return self._respond(422, {"error": str(e)})
        except Exception as e:
            return self._respond(500, {"error": f"Internal error: {e}"})

        self._respond(200, {"status": "ok", "id": event_id})


def _serve(root: str, host: str, port: int) -> None:
    logger = EventLogger(root)

    class ThreadedHTTPServer(http.server.ThreadingHTTPServer):
        def finish_request(self, request, client_address):
            handler = WebhookHandler(request, client_address, self)
            handler.logger = logger

    server = ThreadedHTTPServer((host, port), WebhookHandler)

    def _shutdown(signum, frame):
        server.shutdown()

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, _shutdown)

    print(f"Webhook logger listening on {host}:{port}", file=sys.stderr)
    server.serve_forever()


def _verify(root: str) -> None:
    ok = EventLogger(root).verify()
    sys.exit(0 if ok else 1)


def main() -> None:
    parser = argparse.ArgumentParser(prog="webhook_event_logger")
    sub = parser.add_subparsers(dest="cmd", required=True)

    serve_p = sub.add_parser("serve", help="Run HTTP webhook listener")
    serve_p.add_argument("--root", required=True, help="Root directory for logs")
    serve_p.add_argument("--host", default="0.0.0.0", help="Host to bind")
    serve_p.add_argument("--port", type=int, default=8000, help="Port to bind")

    verify_p = sub.add_parser("verify", help="Verify audit log integrity")
    verify_p.add_argument("--root", required=True, help="Root directory for logs")

    args = parser.parse_args()
    if args.cmd == "serve":
        _serve(args.root, args.host, args.port)
    else:
        _verify(args.root)


if __name__ == "__main__":
    main()

