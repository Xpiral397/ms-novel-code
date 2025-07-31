
"""CSRF protection system for Flask web applications."""

from flask import Flask
from typing import List, Tuple, Any, Dict, Callable
import hashlib
import re
from urllib.parse import urlparse

app = Flask(__name__)


class _EventSystem:
    """Event system for handling security events."""

    def __init__(self):
        """Initialize event system."""
        self.handlers: Dict[str, List[Callable]] = {}

    def subscribe(self, event_type: str, handler: Callable) -> None:
        """Subscribe handler to event type."""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)

    def emit(self, event_type: str, data: dict) -> None:
        """Emit event to all subscribed handlers."""
        if event_type in self.handlers:
            for handler in self.handlers[event_type]:
                handler(data)


class SessionManager:
    """Manages user sessions for CSRF protection."""

    def __init__(self):
        """Initialize session manager."""
        self.sessions: Dict[str, dict] = {}
        self._event_system: _EventSystem = None

    def _set_event_system(self, event_system: _EventSystem) -> None:
        """Set event system for notifications."""
        self._event_system = event_system

    def generate_session(
        self,
        session_id: str,
        user_agent: str,
        ip_address: str,
        origin_domain: str,
    ) -> None:
        """Generate new session with given parameters."""
        if session_id in self.sessions and self.sessions[session_id]["active"]:
            raise ValueError(f"Session {session_id} already exists")

        session_data = {
            "session_id": session_id,
            "user_agent": user_agent,
            "ip_address": ip_address,
            "origin_domain": origin_domain,
            "active": True,
        }
        self.sessions[session_id] = session_data

        if self._event_system:
            self._event_system.emit(
                "SESSION_CREATED", {"session_id": session_id}
            )

    def expire_session(self, session_id: str) -> None:
        """Expire session by session ID."""
        if session_id in self.sessions:
            self.sessions[session_id]["active"] = False
            if self._event_system:
                self._event_system.emit(
                    "SESSION_EXPIRED", {"session_id": session_id}
                )

    def _get_session(self, session_id: str) -> dict:
        """Get session data by session ID."""
        return self.sessions.get(session_id)


class RequestValidator:
    """Validates requests for CSRF protection."""

    def __init__(self):
        """Initialize request validator."""
        self._session_manager: SessionManager = None
        self._event_system: _EventSystem = None
        self._csrf_required_methods = {"POST", "PUT", "PATCH", "DELETE"}
        self._safe_methods = {"GET", "HEAD", "OPTIONS"}

    def _set_dependencies(
        self, session_manager: SessionManager, event_system: _EventSystem
    ) -> None:
        """Set dependencies for session manager and event system."""
        self._session_manager = session_manager
        self._event_system = event_system

    def validate_request(
        self,
        session_id: str,
        csrf_token: str,
        referer_url: str,
        request_method: str,
        user_agent: str,
        ip_address: str,
    ) -> bool:
        """Validate request for CSRF protection."""
        all_valid_methods = self._csrf_required_methods | self._safe_methods
        if request_method not in all_valid_methods:
            raise ValueError("Invalid request method")

        session = self._session_manager._get_session(session_id)
        if not session:
            raise ValueError("Session not found")

        if not session["active"]:
            raise ValueError("Session expired")

        if request_method in self._safe_methods:
            return True

        if not self._is_valid_csrf_format(csrf_token):
            raise ValueError("Invalid CSRF token format")

        expected_token = self._generate_csrf_token(
            session_id, session["user_agent"]
        )

        if csrf_token != expected_token:
            if self._event_system:
                self._event_system.emit(
                    "ATTACK_DETECTED",
                    {
                        "session_id": session_id,
                        "attack_type": "invalid_csrf_token",
                    },
                )
            return False

        if not self._is_same_origin(referer_url, session["origin_domain"]):
            if self._event_system:
                self._event_system.emit(
                    "ATTACK_DETECTED",
                    {"session_id": session_id, "attack_type": "cross_origin"},
                )
            return False

        if user_agent != session["user_agent"]:
            if self._event_system:
                self._event_system.emit(
                    "ATTACK_DETECTED",
                    {
                        "session_id": session_id,
                        "attack_type": "user_agent_mismatch",
                    },
                )
            return False

        if ip_address != session["ip_address"]:
            if self._event_system:
                self._event_system.emit(
                    "ATTACK_DETECTED",
                    {"session_id": session_id, "attack_type": "ip_mismatch"},
                )
            return False

        return True

    def _is_valid_csrf_format(self, token: str) -> bool:
        return bool(re.match(r"^[a-zA-Z0-9]{16}$", token))

    def _generate_csrf_token(self, session_id: str, user_agent: str) -> str:
        combined = session_id + user_agent
        hash_obj = hashlib.md5(combined.encode("utf-8"))
        hex_hash = hash_obj.hexdigest()

        alphanumeric = re.sub(r"[^a-zA-Z0-9]", "", hex_hash)
        return alphanumeric[:16]

    def _is_same_origin(self, referer_url: str, origin_domain: str) -> bool:
        try:
            referer_parsed = urlparse(referer_url)
            origin_parsed = urlparse(origin_domain)

            referer_origin = (
                f"{referer_parsed.scheme}://{referer_parsed.netloc}"
            )
            session_origin = f"{origin_parsed.scheme}://{origin_parsed.netloc}"

            return referer_origin == session_origin
        except Exception:
            return False


class SecurityAnalytics:
    """Analytics for tracking security metrics."""

    def __init__(self):
        """Initialize security analytics."""
        self._active_sessions: List[str] = []
        self._attack_count: int = 0
        self._event_system: _EventSystem = None

    def _set_event_system(self, event_system: _EventSystem) -> None:
        """Set event system and subscribe to relevant events."""
        self._event_system = event_system
        self._event_system.subscribe(
            "SESSION_CREATED", self._handle_session_created
        )
        self._event_system.subscribe(
            "SESSION_EXPIRED", self._handle_session_expired
        )
        self._event_system.subscribe(
            "ATTACK_DETECTED", self._handle_attack_detected
        )

    def get_active_sessions(self) -> List[str]:
        """Get list of active session IDs."""
        return self._active_sessions.copy()

    def get_attack_count(self) -> int:
        """Get total count of detected attacks."""
        return self._attack_count

    def _handle_session_created(self, data: dict) -> None:
        session_id = data["session_id"]
        if session_id not in self._active_sessions:
            self._active_sessions.append(session_id)

    def _handle_session_expired(self, data: dict) -> None:
        session_id = data["session_id"]
        if session_id in self._active_sessions:
            self._active_sessions.remove(session_id)

    def _handle_attack_detected(self, data: dict) -> None:
        self._attack_count += 1


def process_security_operations(operations: List[Tuple]) -> List[Any]:
    """Process security operations for CSRF protection system."""
    event_system = _EventSystem()

    session_manager = SessionManager()
    request_validator = RequestValidator()
    security_analytics = SecurityAnalytics()

    session_manager._set_event_system(event_system)
    request_validator._set_dependencies(session_manager, event_system)
    security_analytics._set_event_system(event_system)

    results = []

    for operation in operations:
        operation_type = operation[0]

        if operation_type == "GENERATE_SESSION":
            _, session_id, user_agent, ip_address, origin_domain = operation
            session_manager.generate_session(
                session_id, user_agent, ip_address, origin_domain
            )

        elif operation_type == "VALIDATE_REQUEST":
            (
                _,
                session_id,
                csrf_token,
                referer_url,
                request_method,
                user_agent,
                ip_address,
            ) = operation
            result = request_validator.validate_request(
                session_id,
                csrf_token,
                referer_url,
                request_method,
                user_agent,
                ip_address,
            )
            results.append(result)

        elif operation_type == "EXPIRE_SESSION":
            _, session_id = operation
            session_manager.expire_session(session_id)

        elif operation_type == "GET_ACTIVE_SESSIONS":
            active_sessions = security_analytics.get_active_sessions()
            results.append(active_sessions)

        elif operation_type == "GET_ATTACK_COUNT":
            attack_count = security_analytics.get_attack_count()
            results.append(attack_count)

    return results


