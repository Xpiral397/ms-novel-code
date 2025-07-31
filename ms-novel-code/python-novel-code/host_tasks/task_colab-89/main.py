
"""Webhook audit logger module.

Validates and logs webhook events into a JSON file,
ensuring data integrity and preventing duplicates.
"""

import json
import uuid
import datetime
import ipaddress
import re
import os


def log_webhook_event(payload: str) -> str:
    """Validate and log a webhook event into the audit log file.

    Args:
        payload (str): A JSON string containing the webhook event.

    Returns:
        str: Status message indicating result of the operation.
    """
    if not (10 <= len(payload) <= 500):
        return "-1"

    if not os.path.exists("webhook_audit_log.json"):
        return "-1"

    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return "Bad payload"

    required_fields = [
        "event_id", "event_type", "timestamp", "source", "payload"
    ]
    for field in required_fields:
        if field not in data:
            return "Bad payload"

    try:
        uuid.UUID(data["event_id"])
    except (ValueError, TypeError):
        return "Bad payload"

    try:
        timestamp = datetime.datetime.fromisoformat(
            data["timestamp"].replace("Z", "+00:00")
        )
        if timestamp > datetime.datetime.now(datetime.timezone.utc):
            return "Invalid timestamp"
    except Exception:
        return "Invalid timestamp"

    source = data.get("source")
    if not isinstance(source, dict):
        return "Bad payload"
    if "ip" not in source or "user_agent" not in source:
        return "Bad payload"

    try:
        ip = ipaddress.ip_address(source["ip"])
        if not isinstance(ip, ipaddress.IPv4Address):
            return "Bad payload"
    except ValueError:
        return "Bad payload"

    if not isinstance(source["user_agent"], str):
        return "Bad payload"

    payload_data = data.get("payload")
    if not isinstance(payload_data, dict):
        return "Bad payload"

    user = payload_data.get("user")
    if not isinstance(user, dict):
        return "Bad payload"

    if "id" not in user or not isinstance(user["id"], int):
        return "Bad payload"

    if "email" not in user or not isinstance(user["email"], str):
        return "Bad payload"

    email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    if not re.match(email_regex, user["email"]):
        return "Bad payload"

    metadata = payload_data.get("metadata")
    if not isinstance(metadata, dict):
        return "Bad payload"

    if "priority" not in metadata:
        return "Bad payload"

    if metadata["priority"] not in ["low", "medium", "high"]:
        return "Bad payload"

    try:
        with open("webhook_audit_log.json", "r") as f:
            try:
                logs = json.load(f)
                if not isinstance(logs, list):
                    logs = []
            except json.JSONDecodeError:
                logs = []
    except Exception:
        logs = []

    is_duplicate = any(
        isinstance(entry, dict) and
        entry.get("event_id") == data["event_id"]
        for entry in logs
    )
    if is_duplicate:
        return "Duplicate event"

    logs.append(data)

    try:
        with open("webhook_audit_log.json", "w") as f:
            json.dump(logs, f, indent=2)
    except Exception:
        return "File write error"

    return "Logged"

