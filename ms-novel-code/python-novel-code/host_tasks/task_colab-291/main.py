"""Module for CSRF protection with multiple strategies and replay detection."""

import hmac
import hashlib
import secrets
import time
from datetime import datetime, timedelta
from threading import RLock
from typing import Any, Dict, List, Optional, Tuple, Union


# Error definitions ---------------------------------------------------------


class CsrfError(Exception):
    """Base class for CSRF-related errors."""

    code: str = "csrf_error"
    message: str = "Generic CSRF error"

    def __init__(self, detail: Optional[str] = None):
        self.detail = detail or self.message
        super().__init__(self.detail)

    def __str__(self):
        return self.detail

    def to_dict(self) -> Dict[str, str]:
        """Return structured representation of the error."""
        return {"code": self.code, "message": self.detail}


class MissingTokenError(CsrfError):
    """Raised when no CSRF token is provided."""

    code = "missing_token"
    message = "CSRF token is missing"


class TokenMismatchError(CsrfError):
    """Raised when provided token does not match expected."""

    code = "token_mismatch"
    message = "CSRF token mismatch"


class TokenExpiredError(CsrfError):
    """Raised when token has expired."""

    code = "token_expired"
    message = "CSRF token expired"


class OriginMismatchError(CsrfError):
    """Raised when request origin does not match binding."""

    code = "origin_mismatch"
    message = "Origin header mismatch or missing"


class ReplayDetectedError(CsrfError):
    """Raised when replay of a token is detected."""

    code = "replay_detected"
    message = "Replay attack detected"


class StrategyNotSupportedError(CsrfError):
    """Raised when unknown strategy is requested."""

    code = "unsupported_strategy"
    message = "CSRF strategy not supported"


class ConfigurationError(CsrfError):
    """Raised when configuration parameters are invalid."""

    code = "configuration_error"
    message = "Invalid configuration"


# Data classes --------------------------------------------------------------


class ValidationInfo:
    """Structured info about the result of validation."""

    def __init__(
        self,
        valid: bool,
        reason: Optional[Union[str, CsrfError]],
        timestamp: datetime,
        token_age_seconds: float,
        additional_details: Optional[Dict[str, Any]] = None,
    ):
        # Normalize reason to string but preserve original if object
        if isinstance(reason, CsrfError):
            self.reason_str = reason.detail
            self.error_obj = reason
        else:
            self.reason_str = reason
            self.error_obj = None
        self.valid = valid
        self.timestamp = timestamp
        self.token_age_seconds = token_age_seconds
        self.additional_details = additional_details or {}
        if self.error_obj:
            # preserve structured error separately if needed
            self.additional_details.setdefault("error_obj", self.error_obj)

    @property
    def reason(self) -> Optional[str]:
        return self.reason_str

    def to_dict(self) -> Dict[str, Any]:
        """Return a serializable representation."""
        return {
            "valid": self.valid,
            "reason": self.reason_str,
            "timestamp": self.timestamp.isoformat(),
            "token_age_seconds": self.token_age_seconds,
            "additional_details": self.additional_details,
        }

    def format_attack_log(self) -> str:
        """Produce a concise human-readable attack log line."""
        parts = [f"time={self.timestamp.isoformat()}", f"valid={self.valid}"]
        if self.reason_str:
            parts.append(f"reason={self.reason_str}")
        if self.token_age_seconds is not None:
            parts.append(f"age={self.token_age_seconds:.1f}s")
        if self.additional_details:
            parts.append(f"details={self.additional_details}")
        return " | ".join(parts)


class MockRequest:
    """Simplified request abstraction for CSRF simulation."""

    def __init__(
        self,
        method: str,
        headers: Dict[str, str],
        cookies: Dict[str, str],
        form: Dict[str, str],
        query: Dict[str, str],
        session: Dict[str, Any],
        origin: Optional[str],
        referer: Optional[str],
        remote_host: str,
    ):
        self.method = method.upper()
        self.headers = headers
        self.cookies = cookies
        self.form = form
        self.query = query
        self.session = session
        self.origin = origin
        self.referer = referer
        self.remote_host = remote_host

    def header(self, name: str) -> Optional[str]:
        """Case-insensitive header retrieval."""
        for k, v in self.headers.items():
            if k.lower() == name.lower():
                return v
        return None


# Utility for token normalization ------------------------------------------


def _unwrap_token_candidate(candidate):
    if isinstance(candidate, tuple) and candidate:
        return candidate[0]
    return candidate


# Token strategy abstractions ----------------------------------------------


class BaseStrategy:
    """Abstract base for CSRF token strategies."""

    name = "base"

    def generate(
        self, request: MockRequest, protector: "CsrfProtector"
    ) -> Tuple[str, Dict[str, Any]]:
        """Generate a token and associated metadata."""
        raise NotImplementedError()

    def validate(
        self, request: MockRequest, token: Optional[str], protector: "CsrfProtector"
    ) -> Tuple[bool, Optional[CsrfError], float, Dict[str, Any]]:
        """
        Validate token; return (valid, error, age_seconds, extra_details).
        Age is in seconds (0 if unknown).
        """
        raise NotImplementedError()

    def rotate(
        self, request: MockRequest, protector: "CsrfProtector"
    ) -> Tuple[Optional[str], Dict[str, Any]]:
        """Rotate token if strategy supports it."""
        token, meta = self.generate(request, protector)
        return token, meta

    def __eq__(self, other):
        if isinstance(other, str):
            return self.name == other
        return super().__eq__(other)

    def __repr__(self):
        return f"<{self.__class__.__name__} name={self.name!r}>"


class PerSessionStrategy(BaseStrategy):
    """Session-bound token strategy; token stored in session."""

    name = "per_session"

    def generate(
        self, request: MockRequest, protector: "CsrfProtector"
    ) -> Tuple[str, Dict[str, Any]]:
        """Generate and bind token to the session with fixation binding."""
        now = protector._now()
        expires_at = now + protector._to_delta(protector.token_lifetime_seconds)
        token = secrets.token_hex(16)
        session_id = request.session.get("session_id")
        if not session_id:
            session_id = secrets.token_hex(8)
            request.session["session_id"] = session_id
        overlap = protector.rotation_policy.get("overlap_seconds", 0)
        prev = request.session.get("csrf_token")
        prev_expires_at = request.session.get("csrf_token_expires_at")
        if prev and prev_expires_at:
            extra_valid_until = datetime.fromtimestamp(prev_expires_at) + protector._to_delta(
                overlap
            )
            request.session.setdefault("old_tokens", {})
            request.session["old_tokens"][prev] = extra_valid_until.timestamp()
        request.session["csrf_token"] = token
        request.session["csrf_token_created_at"] = now.timestamp()
        request.session["csrf_token_expires_at"] = expires_at.timestamp()
        request.session["csrf_token_bound_session_id"] = session_id
        meta = {
            "expires_at": expires_at,
            "created_at": now,
            "strategy": self.name,
            "session_id": session_id,
        }
        return token, meta

    def validate(
        self, request: MockRequest, token: Optional[str], protector: "CsrfProtector"
    ) -> Tuple[bool, Optional[CsrfError], float, Dict[str, Any]]:
        """Validate session-bound token with overlap-aware rotation."""
        now = protector._now()
        header_token = request.header("X-CSRF-Token") or request.header("X-XSRF-TOKEN")
        raw_sources: List[Tuple[str, Optional[Any]]] = [
            ("explicit", token),
            ("form", request.form.get("csrf_token")),
            ("cookie", request.cookies.get("csrf_token")),
            ("header", header_token),
        ]
        sources = [(name, _unwrap_token_candidate(val)) for name, val in raw_sources]
        provided_tokens = [v for _, v in sources if v]
        if not provided_tokens:
            return False, MissingTokenError(), 0.0, {"source": "none"}
        if len(provided_tokens) > 1:
            # compare normalized to avoid false positives
            normalized = []
            for v in provided_tokens:
                if isinstance(v, (str, bytes, int)):
                    normalized.append(v)
                else:
                    normalized.append(str(v))
            if len(set(normalized)) > 1:
                return (
                    False,
                    TokenMismatchError("Conflicting token sources"),
                    0.0,
                    {"provided": provided_tokens},
                )
        provided = provided_tokens[0]
        session_token = request.session.get("csrf_token")
        bound_session_id = request.session.get("csrf_token_bound_session_id")
        session_id = request.session.get("session_id")
        if not session_token or not bound_session_id or not session_id:
            return False, ConfigurationError("Missing session token metadata"), 0.0, {}
        if not hmac.compare_digest(session_id, bound_session_id):
            return False, TokenMismatchError("Session fixation detected"), 0.0, {
                "session_id": session_id,
                "bound": bound_session_id,
            }
        if hmac.compare_digest(provided, session_token):
            created_ts = request.session.get("csrf_token_created_at")
            expires_ts = request.session.get("csrf_token_expires_at")
            if not created_ts or not expires_ts:
                return False, ConfigurationError(
                    "Session token timing metadata missing"
                ), 0.0, {}
            created_at = datetime.fromtimestamp(created_ts, tz=None)
            expires_at = datetime.fromtimestamp(expires_ts, tz=None)
            age = (now - created_at).total_seconds()
            if now > expires_at:
                return False, TokenExpiredError(), age, {
                    "expired_at": expires_at.isoformat()
                }
            return True, None, age, {"strategy": self.name}
        old_tokens = request.session.get("old_tokens", {})
        for old_token, valid_until_ts in list(old_tokens.items()):
            if hmac.compare_digest(provided, old_token):
                valid_until = datetime.fromtimestamp(valid_until_ts, tz=None)
                if now <= valid_until:
                    age = (now - datetime.fromtimestamp(request.session.get("csrf_token_created_at",
                                                                        now.timestamp()),
                                                                        tz=None)).total_seconds()
                    return True, None, age, {
                        "strategy": self.name,
                        "used_old_token": True,
                        "old_token_valid_until": valid_until.isoformat(),
                    }
                else:
                    return False, TokenExpiredError(), 0.0, {
                        "old_token_expired_at": valid_until.isoformat()
                    }
        return False, TokenMismatchError(), 0.0, {
            "provided": provided,
            "expected": session_token,
        }


class StatelessStrategy(BaseStrategy):
    """Stateless token: timestamp + HMAC binding, no server storage."""

    name = "stateless"

    def generate(
        self, request: MockRequest, protector: "CsrfProtector"
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Generate token containing timestamp and HMAC signature.

        Format: hex(timestamp) + "." + HMAC(secret, timestamp:origin)
        """
        now = protector._now()
        timestamp = int(now.timestamp())
        origin_bind = request.origin or ""
        payload = f"{timestamp}:{origin_bind}".encode("utf-8")
        sig = hmac.new(protector.secret_key, payload, hashlib.sha256).hexdigest()
        token = f"{timestamp:x}.{sig}"
        expiry = now + protector._to_delta(protector.token_lifetime_seconds)
        meta = {
            "created_at": now,
            "expires_at": expiry,
            "strategy": self.name,
            "origin_bound": bool(request.origin),
        }
        return token, meta

    def validate(
        self, request: MockRequest, token: Optional[str], protector: "CsrfProtector"
    ) -> Tuple[bool, Optional[CsrfError], float, Dict[str, Any]]:
        """Validate stateless token by checking signature and expiry."""
        now = protector._now()
        header_token = request.header("X-CSRF-Token") or request.header("X-XSRF-TOKEN")
        raw_sources: List[Tuple[str, Optional[Any]]] = [
            ("explicit", token),
            ("form", request.form.get("csrf_token")),
            ("cookie", request.cookies.get("csrf_token")),
            ("header", header_token),
        ]
        sources = [(name, _unwrap_token_candidate(val)) for name, val in raw_sources]
        provided_tokens = [v for _, v in sources if v]

        # Normalize for comparison; avoid unhashable
        if not provided_tokens:
            return False, MissingTokenError(), 0.0, {}
        normalized = []
        for v in provided_tokens:
            if isinstance(v, (str, bytes, int)):
                normalized.append(v)
            else:
                normalized.append(str(v))
        if len(set(normalized)) > 1:
            return False, TokenMismatchError("Conflicting token sources"), 0.0, {
                "provided": provided_tokens
            }
        provided = normalized[0]
        parts = provided.split(".")
        if len(parts) != 2:
            return False, TokenMismatchError("Bad token format"), 0.0, {}
        hex_ts, sig = parts
        try:
            timestamp = int(hex_ts, 16)
        except ValueError:
            return False, TokenMismatchError("Invalid timestamp"), 0.0, {}
        origin_bind = request.origin or ""
        payload = f"{timestamp}:{origin_bind}".encode("utf-8")
        expected_sig = hmac.new(protector.secret_key, payload, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            return False, TokenMismatchError("Signature mismatch"), 0.0, {
                "provided_sig": sig,
                "expected_sig": expected_sig,
            }
        created_at = datetime.fromtimestamp(timestamp, tz=None)
        age = (now - created_at).total_seconds()
        if age < 0:
            return False, TokenMismatchError("Token timestamp in future"), age, {}
        if age > protector.token_lifetime_seconds:
            return False, TokenExpiredError(), age, {
                "expired_at": (created_at + protector._to_delta(
                    protector.token_lifetime_seconds
                )).isoformat()
            }
        return True, None, age, {"strategy": self.name}


class DoubleSubmitStrategy(BaseStrategy):
    """Double-submit cookie pattern: client sends same token in cookie+form."""

    name = "double_submit"

    def generate(
        self, request: MockRequest, protector: "CsrfProtector"
    ) -> Tuple[str, Dict[str, Any]]:
        """Generate a token; client must echo in cookie and form."""
        token = secrets.token_hex(16)
        now = protector._now()
        expiry = now + protector._to_delta(protector.token_lifetime_seconds)
        meta = {
            "created_at": now,
            "expires_at": expiry,
            "strategy": self.name,
        }
        return token, meta

    def validate(
        self, request: MockRequest, token: Optional[str], protector: "CsrfProtector"
    ) -> Tuple[bool, Optional[CsrfError], float, Dict[str, Any]]:
        """Validate that cookie and form token exist and match."""
        header_token = request.header("X-CSRF-Token") or request.header("X-XSRF-TOKEN")
        form_token_raw = request.form.get("csrf_token")
        cookie_token_raw = request.cookies.get("csrf_token")
        # Unwrap potential tuple leaks
        form_token = _unwrap_token_candidate(form_token_raw)
        cookie_token = _unwrap_token_candidate(cookie_token_raw)

        # If supplied via header, treat it like explicit
        if header_token and not form_token and not cookie_token:
            form_token = header_token
        if not form_token and not cookie_token:
            return False, MissingTokenError(), 0.0, {}
        if form_token and cookie_token and not hmac.compare_digest(
            form_token, cookie_token
        ):
            return False, TokenMismatchError("Double-submit mismatch"), 0.0, {
                "form_token": form_token,
                "cookie_token": cookie_token,
            }
        if not form_token:
            return False, TokenMismatchError("Form token missing"), 0.0, {}
        if not cookie_token:
            return False, TokenMismatchError("Cookie token missing"), 0.0, {}
        return True, None, 0.0, {"strategy": self.name}


# Protector -----------------------------------------------------------------


class CsrfProtector:
    """CSRF protection manager with pluggable strategies and replay tracking."""

    DEFAULT_SAFE_METHODS = ["GET", "HEAD", "OPTIONS"]

    def __init__(
        self,
        secret_key: str,
        token_lifetime_seconds: int = 300,
        safe_methods: Optional[List[str]] = None,
        strategy: str = "per_session",
        enable_replay_detection: bool = True,
        rotation_policy: Optional[Dict[str, Any]] = None,
        current_time_func: Optional[Any] = None,
        enforce_origin: bool = True,
    ):
        """
        Initialize the CSRF protector.

        Args:
            secret_key: Secret for HMAC/signing.
            token_lifetime_seconds: Lifetime of tokens in seconds.
            safe_methods: Methods to skip CSRF enforcement.
            strategy: One of "per_session", "stateless", "double_submit".
            enable_replay_detection: Enable reuse detection.
            rotation_policy: Policy dict, e.g., overlap window.
            current_time_func: Callable returning epoch seconds.
            enforce_origin: Whether origin header is required/bound.
        """
        if not secret_key or not isinstance(secret_key, str):
            raise ConfigurationError("secret_key must be non-empty string")
        if not isinstance(token_lifetime_seconds, (int, float)) or token_lifetime_seconds <= 0:
            raise ConfigurationError("token_lifetime_seconds must be positive number")
        self.secret_key = secret_key.encode("utf-8")
        self.token_lifetime_seconds = token_lifetime_seconds
        self.safe_methods = set(
            m.upper() for m in (safe_methods or self.DEFAULT_SAFE_METHODS)
        )
        self.strategy_name = strategy
        self.enable_replay_detection = enable_replay_detection
        self.rotation_policy = rotation_policy or {"overlap_seconds": 5}
        self.current_time_func = current_time_func or time.time
        self.enforce_origin = enforce_origin
        self._lock = RLock()
        self._replay_cache: Dict[str, float] = {}
        self._strategies: Dict[str, BaseStrategy] = {
            PerSessionStrategy.name: PerSessionStrategy(),
            StatelessStrategy.name: StatelessStrategy(),
            DoubleSubmitStrategy.name: DoubleSubmitStrategy(),
        }
        if strategy not in self._strategies:
            raise StrategyNotSupportedError(f"Unsupported strategy '{strategy}'")
        self.strategy: BaseStrategy = self._strategies[strategy]
        if not strategy:
            self.strategy = self._strategies["per_session"]

    # Strategy extensibility -------------------------------------------------

    def register_strategy(self, strategy: BaseStrategy) -> None:
        """
        Register a new strategy dynamically without altering core logic.

        Args:
            strategy: Instance of BaseStrategy subclass.
        """
        self._strategies[strategy.name] = strategy

    # Internal helpers -------------------------------------------------------

    def _now(self) -> datetime:
        """Return current time as datetime (UTC naive)."""
        return datetime.utcfromtimestamp(self.current_time_func())

    def _to_delta(self, seconds: Union[int, float]) -> timedelta:
        """Convert seconds to timedelta."""
        return timedelta(seconds=seconds)

    def _purge_replay_cache(self) -> None:
        """Remove expired entries from the replay cache."""
        now_ts = self.current_time_func()
        with self._lock:
            to_drop = [t for t, exp in self._replay_cache.items() if exp < now_ts]
            for k in to_drop:
                del self._replay_cache[k]

    def _record_replay(self, token: str) -> None:
        """Record a token usage for replay detection."""
        expiry = self.current_time_func() + self.token_lifetime_seconds
        with self._lock:
            self._replay_cache[token] = expiry

    def _is_replay(self, token: str) -> bool:
        """Check if a token was already used."""
        self._purge_replay_cache()
        with self._lock:
            return token in self._replay_cache

    # Public API ------------------------------------------------------------

    def generate_token(self, request: MockRequest) -> str:
        """
        Generate only the CSRF token (tests expect a string).

        Returns:
            Token string.
        """
        token, _ = self.strategy.generate(request, self)
        return token

    def generate_token_full(self, request: MockRequest) -> Tuple[str, Dict[str, Any]]:
        """
        Generate a CSRF token and metadata according to strategy.

        Returns:
            (token, metadata)
        """
        token, meta = self.strategy.generate(request, self)
        return token, meta

    def validate_request(
        self, request: MockRequest, token: Optional[str] = None
    ) -> Tuple[bool, ValidationInfo]:
        """
        Validate incoming request for CSRF compliance.

        Returns:
            Tuple of (bool valid, ValidationInfo).
        """
        now = self._now()
        if request.method in self.safe_methods:
            age = 0.0
            details: Dict[str, Any] = {}
            if (
                token
                or request.form.get("csrf_token")
                or request.cookies.get("csrf_token")
                or request.header("X-CSRF-Token")
                or request.header("X-XSRF-TOKEN")
            ):
                details["note"] = "Token present on safe method"
            vi = ValidationInfo(True, None, now, age, details)
            return True, vi

        if self.enforce_origin:
            if not request.origin:
                err = OriginMismatchError("Origin header missing")
                vi = ValidationInfo(False, err, now, 0.0, {})
                return False, vi

        valid, error, age, extra = self.strategy.validate(request, token, self)

        if not valid:
            vi = ValidationInfo(False, error, now, age, extra)
            return False, vi

        # Replay detection
        candidates = [
            token,
            request.form.get("csrf_token"),
            request.cookies.get("csrf_token"),
            request.header("X-CSRF-Token"),
            request.header("X-XSRF-TOKEN"),
        ]
        provided_tokens = [_unwrap_token_candidate(t) for t in candidates if t]
        selected_token = provided_tokens[0] if provided_tokens else None
        if self.enable_replay_detection and selected_token:
            if self._is_replay(selected_token):
                err = ReplayDetectedError()
                vi = ValidationInfo(False, err, now, age, {"token": selected_token})
                return False, vi
            self._record_replay(selected_token)

        vi = ValidationInfo(True, None, now, age, extra)
        return True, vi

    def rotate_token(self, request: MockRequest) -> Tuple[str, Dict[str, Any]]:
        """
        Rotate the CSRF token securely based on policy.

        Returns:
            (new_token, metadata)
        """
        token, meta = self.strategy.rotate(request, self)
        return token, meta

    # Utility ----------------------------------------------------------------

    def get_bound_origin(self, request: MockRequest) -> Optional[str]:
        """Return the origin used for binding if any."""
        return request.origin

