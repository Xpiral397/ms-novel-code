# tests
"""Unittests for CSRF protection system."""

import unittest
import re
from main import process_security_operations


class TestCSRFProtectionSystem(unittest.TestCase):
    """Test suite for CSRF protection system components."""

    def _generate_token(self, session_id, user_agent):
        """Generate a valid CSRF token based on session ID and user agent."""
        import hashlib
        combined = session_id + user_agent
        hex_hash = hashlib.md5(combined.encode("utf-8")).hexdigest()
        return re.sub(r"[^a-zA-Z0-9]", "", hex_hash)[:16]

    def test_generate_and_validate_valid_request(self):
        """Test successful session generation and request validation."""
        sid = "S1"
        ua = "UA"
        ip = "1.1.1.1"
        origin = "http://example.com"
        token = self._generate_token(sid, ua)

        ops = [
            ("GENERATE_SESSION", sid, ua, ip, origin),
            ("VALIDATE_REQUEST", sid, token, origin, "POST", ua, ip)
        ]
        result = process_security_operations(ops)
        self.assertEqual(result, [True])

    def test_validate_safe_method(self):
        """Test that safe HTTP methods like GET do not require CSRF token."""
        sid = "S2"
        ua = "UA2"
        ip = "2.2.2.2"
        origin = "http://safe.com"
        token = "invalid"

        ops = [
            ("GENERATE_SESSION", sid, ua, ip, origin),
            ("VALIDATE_REQUEST", sid, token, origin, "GET", ua, ip)
        ]
        result = process_security_operations(ops)
        self.assertEqual(result, [True])

    def test_validate_expired_session(self):
        """Test that validation fails for an expired session."""
        sid = "S3"
        ua = "UA3"
        ip = "3.3.3.3"
        origin = "http://x.com"
        token = self._generate_token(sid, ua)

        ops = [
            ("GENERATE_SESSION", sid, ua, ip, origin),
            ("EXPIRE_SESSION", sid),
            ("VALIDATE_REQUEST", sid, token, origin, "POST", ua, ip)
        ]
        with self.assertRaises(ValueError):
            process_security_operations(ops)

    def test_validate_missing_session(self):
        """Test validation fails for a session that was never created."""
        token = self._generate_token("MISSING", "UA4")
        ops = [
            ("VALIDATE_REQUEST", "MISSING", token,
             "http://x.com", "POST", "UA4", "4.4.4.4")
        ]
        with self.assertRaises(ValueError):
            process_security_operations(ops)

    def test_validate_invalid_method(self):
        """Test validation fails for unsupported HTTP method."""
        sid = "S4"
        ua = "UA4"
        ip = "4.4.4.4"
        origin = "http://x.com"

        ops = [
            ("GENERATE_SESSION", sid, ua, ip, origin),
            ("VALIDATE_REQUEST", sid, "1234567890123456",
             origin, "TRACE", ua, ip)
        ]
        with self.assertRaises(ValueError):
            process_security_operations(ops)

    def test_invalid_csrf_token(self):
        """Test request with an invalid CSRF token returns False."""
        sid = "S5"
        ua = "UA5"
        ip = "5.5.5.5"
        origin = "http://x.com"

        ops = [
            ("GENERATE_SESSION", sid, ua, ip, origin),
            ("VALIDATE_REQUEST", sid, "BADTOKEN12345678",
             origin, "POST", ua, ip)
        ]
        result = process_security_operations(ops)
        self.assertEqual(result, [False])

    def test_user_agent_mismatch(self):
        """Test validation when user-agent differs from stored session."""
        sid = "S6"
        ua = "UA6"
        ip = "6.6.6.6"
        origin = "http://x.com"
        token = self._generate_token(sid, ua)

        ops = [
            ("GENERATE_SESSION", sid, ua, ip, origin),
            ("VALIDATE_REQUEST", sid, token, origin, "POST", "WRONG_UA", ip)
        ]
        result = process_security_operations(ops)
        self.assertEqual(result, [False])

    def test_ip_mismatch(self):
        """Test validation fails when IP address differs from session data."""
        sid = "S7"
        ua = "UA7"
        ip = "7.7.7.7"
        origin = "http://x.com"
        token = self._generate_token(sid, ua)

        ops = [
            ("GENERATE_SESSION", sid, ua, ip, origin),
            ("VALIDATE_REQUEST", sid, token, origin, "POST", ua, "WRONG_IP")
        ]
        result = process_security_operations(ops)
        self.assertEqual(result, [False])

    def test_cross_origin_blocked(self):
        """Test that cross-origin requests are blocked."""
        sid = "S8"
        ua = "UA8"
        ip = "8.8.8.8"
        origin = "http://a.com"
        referer = "http://b.com"
        token = self._generate_token(sid, ua)

        ops = [
            ("GENERATE_SESSION", sid, ua, ip, origin),
            ("VALIDATE_REQUEST", sid, token, referer, "POST", ua, ip)
        ]
        result = process_security_operations(ops)
        self.assertEqual(result, [False])

    def test_get_active_sessions(self):
        """Test retrieval of currently active sessions."""
        sid = "S9"
        ua = "UA9"
        ip = "9.9.9.9"
        origin = "http://z.com"

        ops = [
            ("GENERATE_SESSION", sid, ua, ip, origin),
            ("GET_ACTIVE_SESSIONS",)
        ]
        result = process_security_operations(ops)
        self.assertEqual(result, [[sid]])

    def test_get_attack_count_after_failures(self):
        """Test that failed validations increment attack count."""
        sid = "S10"
        ua = "UA10"
        ip = "10.0.0.1"
        origin = "http://attack.com"
        token = "WRONGTOKEN123456"

        ops = [
            ("GENERATE_SESSION", sid, ua, ip, origin),
            ("VALIDATE_REQUEST", sid, token, origin, "POST", ua, ip),
            ("VALIDATE_REQUEST", sid, token, origin, "POST", ua, ip),
            ("GET_ATTACK_COUNT",)
        ]
        result = process_security_operations(ops)
        self.assertEqual(result, [False, False, 2])

    def test_multiple_sessions_tracking(self):
        """Test that multiple sessions can be created and tracked."""
        ops = [
            ("GENERATE_SESSION", "A1", "UA", "1.1.1.1", "http://a.com"),
            ("GENERATE_SESSION", "B2", "UB", "2.2.2.2", "http://b.com"),
            ("GET_ACTIVE_SESSIONS",),
        ]
        result = process_security_operations(ops)
        self.assertIn("A1", result[0])
        self.assertIn("B2", result[0])

    def test_expire_and_check_active_sessions(self):
        """Test session expiration updates active session list."""
        sid = "S11"
        ops = [
            ("GENERATE_SESSION", sid, "UA", "1.1.1.1", "http://d.com"),
            ("EXPIRE_SESSION", sid),
            ("GET_ACTIVE_SESSIONS",),
        ]
        result = process_security_operations(ops)
        self.assertNotIn(sid, result[0])

    def test_token_length_and_format(self):
        """Test that generated token has correct format and length."""
        token = self._generate_token("SESSION", "UA")
        self.assertEqual(len(token), 16)
        self.assertTrue(re.match(r"^[a-zA-Z0-9]{16}$", token))

    def test_repeated_session_creation_fails(self):
        """Test that creating an existing session raises error."""
        sid = "S12"
        ops = [
            ("GENERATE_SESSION", sid, "UA", "1.1.1.1", "http://x.com"),
            ("GENERATE_SESSION", sid, "UA", "1.1.1.1", "http://x.com"),
        ]
        with self.assertRaises(ValueError):
            process_security_operations(ops)

    def test_expiring_nonexistent_session_does_nothing(self):
        """Test that expiring a missing session safely ignored."""
        ops = [("EXPIRE_SESSION", "NON_EXISTENT")]
        result = process_security_operations(ops)
        self.assertEqual(result, [])

    def test_attack_event_emission_on_token_mismatch(self):
        """Test that a failed CSRF token triggers attack event increment."""
        sid = "S13"
        ua = "UA"
        ip = "1.1.1.1"
        origin = "http://csrf.com"
        bad_token = "1234567890123456"
        ops = [
            ("GENERATE_SESSION", sid, ua, ip, origin),
            ("VALIDATE_REQUEST", sid, bad_token, origin, "POST", ua, ip),
            ("GET_ATTACK_COUNT",)
        ]
        result = process_security_operations(ops)
        self.assertEqual(result[-1], 1)

    def test_invalid_csrf_token_format(self):
        """Test validation fails for malformed CSRF token."""
        sid = "S14"
        ua = "UA"
        ip = "1.1.1.1"
        origin = "http://badformat.com"
        bad_token = "short"

        ops = [
            ("GENERATE_SESSION", sid, ua, ip, origin),
            ("VALIDATE_REQUEST", sid, bad_token, origin, "POST", ua, ip),
        ]
        with self.assertRaises(ValueError):
            process_security_operations(ops)

    def test_valid_get_request_no_token_required(self):
        """Test that GET requests do not require valid CSRF token."""
        sid = "S15"
        ua = "UA"
        ip = "1.1.1.1"
        origin = "http://g.com"

        ops = [
            ("GENERATE_SESSION", sid, ua, ip, origin),
            ("VALIDATE_REQUEST", sid, "anytoken", origin, "GET", ua, ip)
        ]
        result = process_security_operations(ops)
        self.assertEqual(result, [True])

    def test_empty_operations_returns_empty(self):
        """Test that an empty list of operations returns empty result."""
        result = process_security_operations([])
        self.assertEqual(result, [])

    def test_referer_parsing_failure_returns_false(self):
        """Test that invalid referer format causes validation to fail."""
        sid = "S16"
        ua = "UA"
        ip = "1.1.1.1"
        origin = "http://host.com"
        token = self._generate_token(sid, ua)
        ops = [
            ("GENERATE_SESSION", sid, ua, ip, origin),
            ("VALIDATE_REQUEST", sid, token, "bad_url", "POST", ua, ip),
        ]
        result = process_security_operations(ops)
        self.assertEqual(result, [False])
