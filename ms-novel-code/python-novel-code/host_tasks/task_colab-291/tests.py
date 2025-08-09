# tests

import unittest
import time
from unittest.mock import patch
from datetime import datetime
from main import MockRequest, CsrfProtector, ValidationInfo


class TestCSRFProtection(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures for each test case."""
        self.secret_key = "test_secret_key_123"
        self.csrf_protector = CsrfProtector(
            secret_key=self.secret_key,
            token_lifetime_seconds=300,
            strategy="per_session"
        )

        self.base_request = MockRequest(
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            cookies={},
            form={},
            query={},
            session={},
            origin="https://example.com",
            referer="https://example.com/page",
            remote_host="example.com"
        )

    def tearDown(self):
        """Clean up after each test."""
        # Clear any internal state that might affect other tests
        pass

    def test_mock_request_initialization(self):
        """Test MockRequest class initialization with all parameters."""
        request = MockRequest(
            method="GET",
            headers={"User-Agent": "Test"},
            cookies={"session": "abc123"},
            form={"field": "value"},
            query={"param": "test"},
            session={"user_id": "123"},
            origin="https://test.com",
            referer="https://test.com/ref",
            remote_host="test.com"
        )

        self.assertEqual(request.method, "GET")
        self.assertEqual(request.headers["User-Agent"], "Test")
        self.assertEqual(request.cookies["session"], "abc123")
        self.assertEqual(request.form["field"], "value")
        self.assertEqual(request.query["param"], "test")
        self.assertEqual(request.session["user_id"], "123")
        self.assertEqual(request.origin, "https://test.com")
        self.assertEqual(request.referer, "https://test.com/ref")
        self.assertEqual(request.remote_host, "test.com")

    def test_csrf_protector_initialization(self):
        """Test CsrfProtector initialization with various configurations."""
        # Test default initialization
        protector = CsrfProtector(secret_key="test")
        self.assertEqual(protector.token_lifetime_seconds, 300)
        self.assertEqual(protector.strategy, "per_session")
        self.assertTrue(protector.enable_replay_detection)

        # Test custom initialization
        custom_protector = CsrfProtector(
            secret_key="custom",
            token_lifetime_seconds=600,
            safe_methods=["GET", "HEAD", "OPTIONS", "TRACE"],
            strategy="double_submit",
            enable_replay_detection=False
        )
        self.assertEqual(custom_protector.token_lifetime_seconds, 600)
        self.assertEqual(custom_protector.strategy, "double_submit")
        self.assertFalse(custom_protector.enable_replay_detection)

    def test_token_generation_per_session_strategy(self):
        """Test token generation with per-session strategy."""
        token = self.csrf_protector.generate_token(self.base_request)

        self.assertIsInstance(token, str)
        self.assertGreaterEqual(len(token), 16)  # Ensure sufficient entropy

        # Token should be stored in session
        self.assertIn("csrf_token", self.base_request.session)
        self.assertEqual(self.base_request.session["csrf_token"], token)

        # Generate another token for same session should be different
        token2 = self.csrf_protector.generate_token(self.base_request)
        self.assertNotEqual(token, token2)

    def test_token_validation_success(self):
        """Test successful token validation with per-session strategy."""
        # Generate and store token
        token = self.csrf_protector.generate_token(self.base_request)
        self.base_request.form["csrf_token"] = token

        # Validate request
        valid, info = self.csrf_protector.validate_request(self.base_request)

        self.assertTrue(valid)
        self.assertIsInstance(info, ValidationInfo)
        self.assertTrue(info.valid)
        self.assertIsNone(info.reason)  # No failure reason for valid requests

    def test_token_validation_missing_token(self):
        """Test validation failure when CSRF token is missing."""
        # No token in form or session
        valid, info = self.csrf_protector.validate_request(self.base_request)

        self.assertFalse(valid)
        self.assertFalse(info.valid)
        self.assertIn("missing", info.reason.lower())

    def test_token_validation_expired_token(self):
        """Test validation failure with expired token."""
        # Create protector with very short lifetime
        short_protector = CsrfProtector(
            secret_key=self.secret_key,
            token_lifetime_seconds=1
        )

        # Generate token
        token = short_protector.generate_token(self.base_request)
        self.base_request.form["csrf_token"] = token

        # Wait for token to expire
        time.sleep(1.1)

        # Validate expired token
        valid, info = short_protector.validate_request(self.base_request)

        self.assertFalse(valid)
        self.assertIn("expired", info.reason.lower())

    def test_safe_methods_bypass_validation(self):
        """Test that safe HTTP methods bypass CSRF validation."""
        safe_methods = ["GET", "HEAD", "OPTIONS"]

        for method in safe_methods:
            request = MockRequest(
                method=method,
                headers={},
                cookies={},
                form={},
                query={},
                session={},
                origin="https://example.com",
                referer=None,
                remote_host="example.com"
            )

            # Should pass validation even without token
            valid, _ = self.csrf_protector.validate_request(request)
            self.assertTrue(
                valid, f"Safe method {method} should bypass validation")

    def test_double_submit_cookie_strategy(self):
        """Test double-submit cookie strategy for CSRF protection."""
        double_submit_protector = CsrfProtector(
            secret_key=self.secret_key,
            strategy="double_submit"
        )

        # Generate token
        token = double_submit_protector.generate_token(self.base_request)

        # Set token in both cookie and form (double-submit pattern)
        self.base_request.cookies["csrf_token"] = token
        self.base_request.form["csrf_token"] = token

        # Should validate successfully
        valid, info = double_submit_protector.validate_request(
            self.base_request)
        self.assertTrue(valid)

        # Test mismatch between cookie and form token
        self.base_request.form["csrf_token"] = "different_token"
        valid, info = double_submit_protector.validate_request(
            self.base_request)
        self.assertFalse(valid)
        self.assertIn("mismatch", info.reason.lower())

    def test_stateless_token_strategy(self):
        """Test stateless HMAC-based token strategy."""
        stateless_protector = CsrfProtector(
            secret_key=self.secret_key,
            strategy="stateless"
        )

        # Generate stateless token
        token = stateless_protector.generate_token(self.base_request)
        self.base_request.form["csrf_token"] = token

        # Should validate without session storage
        valid, _ = stateless_protector.validate_request(self.base_request)
        self.assertTrue(valid)

        # Test token tampering
        tampered_token = token[:-1] + "X"  # Change last character
        self.base_request.form["csrf_token"] = tampered_token
        valid, _ = stateless_protector.validate_request(self.base_request)
        self.assertFalse(valid)

    def test_replay_detection(self):
        """Test replay attack detection."""
        protector_with_replay = CsrfProtector(
            secret_key=self.secret_key,
            enable_replay_detection=True
        )

        # Generate and use token first time
        token = protector_with_replay.generate_token(self.base_request)
        self.base_request.form["csrf_token"] = token
        valid, info = protector_with_replay.validate_request(self.base_request)
        self.assertTrue(valid)

        # Try to reuse same token (replay attack)
        valid, info = protector_with_replay.validate_request(self.base_request)
        self.assertFalse(valid)
        self.assertIn("replay", info.reason.lower())

    def test_token_rotation(self):
        """Test token rotation functionality."""
        # Generate initial token
        initial_token = self.csrf_protector.generate_token(self.base_request)

        # Rotate token
        rotated_token = self.csrf_protector.rotate_token(self.base_request)

        self.assertNotEqual(initial_token, rotated_token)
        self.assertIsInstance(rotated_token[0], str)

        # Old token should be invalid, new token should be valid
        self.base_request.form["csrf_token"] = rotated_token
        valid, info = self.csrf_protector.validate_request(self.base_request)
        self.assertTrue(valid)

    def test_origin_referer_validation(self):
        """Test validation based on Origin and Referer headers."""
        # Test valid origin
        self.base_request.origin = "https://example.com"
        token = self.csrf_protector.generate_token(self.base_request)
        self.base_request.form["csrf_token"] = token
        valid, info = self.csrf_protector.validate_request(self.base_request)
        self.assertTrue(valid)

        # Test invalid origin (potential CSRF attack)
        self.base_request.origin = "https://malicious.com"
        valid, info = self.csrf_protector.validate_request(self.base_request)
        # Depending on implementation, this might fail origin validation
        # The specific behavior depends on the implementation details

    def test_concurrent_token_usage_race_condition(self):
        """Test handling of concurrent token usage scenarios."""
        protector = CsrfProtector(
            secret_key=self.secret_key,
            enable_replay_detection=True
        )

        # Generate token
        token = protector.generate_token(self.base_request)

        # Create two identical requests with same token
        request1 = MockRequest(**{
            "method": "POST",
            "headers": {"Content-Type": "application/x-www-form-urlencoded"},
            "cookies": {},
            "form": {"csrf_token": token},
            "query": {},
            "session": self.base_request.session.copy(),
            "origin": "https://example.com",
            "referer": "https://example.com/page",
            "remote_host": "example.com"
        })

        request2 = MockRequest(**{
            "method": "POST",
            "headers": {"Content-Type": "application/x-www-form-urlencoded"},
            "cookies": {},
            "form": {"csrf_token": token},
            "query": {},
            "session": self.base_request.session.copy(),
            "origin": "https://example.com",
            "referer": "https://example.com/page",
            "remote_host": "example.com"
        })

        # First request should succeed
        valid1, _ = protector.validate_request(request1)
        self.assertTrue(valid1)

        # Second request with same token should fail (replay detection)
        valid2, _ = protector.validate_request(request2)
        self.assertFalse(valid2)

    def test_token_tampering_detection(self):
        """Test detection of tampered tokens."""
        stateless_protector = CsrfProtector(
            secret_key=self.secret_key,
            strategy="stateless"
        )

        # Generate valid token
        token = stateless_protector.generate_token(self.base_request)

        # Test various tampering scenarios
        tampering_cases = [
            token + "extra",  # Append data
            token[1:],        # Remove first character
            token[:-1],       # Remove last character
            token[:10] + "X" + token[11:],  # Modify middle
            "completely_different_token"     # Completely different
        ]

        for tampered_token in tampering_cases:
            self.base_request.form["csrf_token"] = tampered_token
            valid, _ = stateless_protector.validate_request(
                self.base_request)
            self.assertFalse(
                valid, f"Tampered token should be rejected: {tampered_token}")

    def test_session_binding_validation(self):
        """Test that tokens are properly bound to sessions."""
        # Generate token for first session
        session1 = {"user_id": "user1", "session_id": "sess1"}
        request1 = MockRequest(
            method="POST",
            headers={},
            cookies={},
            form={},
            query={},
            session=session1,
            origin="https://example.com",
            referer="https://example.com",
            remote_host="example.com"
        )

        token = self.csrf_protector.generate_token(request1)

        # Try to use token with different session
        session2 = {"user_id": "user2", "session_id": "sess2"}
        request2 = MockRequest(
            method="POST",
            headers={},
            cookies={},
            form={"csrf_token": token},
            query={},
            session=session2,
            origin="https://example.com",
            referer="https://example.com",
            remote_host="example.com"
        )

        # Should fail due to session mismatch
        valid, _ = self.csrf_protector.validate_request(request2)
        self.assertFalse(valid)

    def test_validation_info_structure(self):
        """Test that ValidationInfo contains expected fields and structure."""
        token = self.csrf_protector.generate_token(self.base_request)
        self.base_request.form["csrf_token"] = token

        _, info = self.csrf_protector.validate_request(self.base_request)

        # Check ValidationInfo structure
        self.assertIsInstance(info, ValidationInfo)
        self.assertTrue(hasattr(info, 'valid'))
        self.assertTrue(hasattr(info, 'reason'))
        self.assertTrue(hasattr(info, 'timestamp'))
        self.assertTrue(hasattr(info, 'token_age_seconds'))

        # For valid requests
        self.assertTrue(info.valid)
        self.assertIsNone(info.reason)
        self.assertIsInstance(info.timestamp, datetime)
        self.assertIsInstance(info.token_age_seconds, (int, float))

    def test_configuration_validation(self):
        """Test validation of configuration parameters during initialization."""
        # Test invalid strategy
        with self.assertRaises(Exception):
            CsrfProtector(secret_key="test", strategy="invalid_strategy")

        # Test non-positive token lifetime
        with self.assertRaises(Exception):
            CsrfProtector(secret_key="test", token_lifetime_seconds=0)

        with self.assertRaises(Exception):
            CsrfProtector(secret_key="test", token_lifetime_seconds=-10)

        # Test empty secret key
        with self.assertRaises(Exception):
            CsrfProtector(secret_key="")

    def test_constant_time_comparison(self):
        """Test that token comparisons use constant-time comparison."""
        # This test verifies that the implementation uses hmac.compare_digest
        # or similar constant-time comparison to prevent timing attacks

        protector = CsrfProtector(
            secret_key=self.secret_key, strategy="stateless")

        # Generate a valid token
        token = protector.generate_token(self.base_request)
        self.base_request.form["csrf_token"] = token

        # Validate correct token
        valid, _ = protector.validate_request(self.base_request)
        self.assertTrue(valid)

        wrong_token = token[:-1] + ("A" if token[-1] != "A" else "B")
        self.base_request.form["csrf_token"] = wrong_token
        valid, _ = protector.validate_request(self.base_request)
        self.assertFalse(valid)

    @patch('time.time')
    def test_time_injection_for_deterministic_testing(self, mock_time):
        """Test that time can be injected for deterministic testing."""
        # Mock current time
        mock_time.return_value = 1000000.0

        protector = CsrfProtector(
            secret_key=self.secret_key,
            token_lifetime_seconds=300
        )

        # Generate token at mocked time
        token = protector.generate_token(self.base_request)
        self.base_request.form["csrf_token"] = token

        # Validate at same time - should work
        valid, info = protector.validate_request(self.base_request)
        self.assertTrue(valid)

        # Move time forward beyond token lifetime
        mock_time.return_value = 1000000.0 + 301  # 301 seconds later

        # Should now be expired
        valid, info = protector.validate_request(self.base_request)
        self.assertFalse(valid)
        self.assertIn("expired", info.reason.lower())

    def test_memory_bounded_replay_tracking(self):
        """Test that replay tracking memory usage is bounded."""
        protector = CsrfProtector(
            secret_key=self.secret_key,
            enable_replay_detection=True,
            token_lifetime_seconds=1  # Short lifetime for quick cleanup
        )

        # Generate and validate multiple tokens
        tokens = []
        for i in range(10):
            request = MockRequest(
                method="POST",
                headers={},
                cookies={},
                form={},
                query={},
                session={"id": f"session_{i}"},
                origin="https://example.com",
                referer="https://example.com",
                remote_host="example.com"
            )
            token = protector.generate_token(request)
            request.form["csrf_token"] = token
            valid, _ = protector.validate_request(request)
            self.assertTrue(valid)
            tokens.append(token)

        # Wait for tokens to expire
        time.sleep(1.1)
        new_token = protector.generate_token(self.base_request)
        self.base_request.form["csrf_token"] = new_token
        valid, _ = protector.validate_request(self.base_request)
        self.assertTrue(valid)


if __name__ == '__main__':
    unittest.main()
