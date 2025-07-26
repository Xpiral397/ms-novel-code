# tests

"""Test cases for JWTManager class covering all requirements."""

import unittest
import time
import jwt
import json
import base64
from main import JWTManager


class TestJWTManager(unittest.TestCase):
    """Test cases for JWTManager class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.secret = "test_secret_key_123"
        self.jwt_manager = JWTManager(self.secret)
        self.valid_payload = {"user_id": 123, "username": "testuser"}

    def tearDown(self):
        """Clean up after each test method."""
        if hasattr(self.jwt_manager, "blacklist"):
            self.jwt_manager.blacklist.clear()

    def test_generate_token_valid_payload(self):
        """Test successful token generation with valid payload."""
        token = self.jwt_manager.generate_token(
            self.valid_payload, expiry_seconds=3600
        )

        self.assertIsInstance(token, str)

        parts = token.split(".")
        self.assertEqual(len(parts), 3)

        for part in parts:
            try:
                padding = 4 - (len(part) % 4)
                if padding != 4:
                    part += "=" * padding
                base64.urlsafe_b64decode(part)
            except Exception:
                self.fail(f"Token part is not valid base64url: {part}")

    def test_validate_token_success(self):
        """Test successful token validation."""
        token = self.jwt_manager.generate_token(
            self.valid_payload, expiry_seconds=3600
        )
        decoded_payload = self.jwt_manager.validate_token(token)

        self.assertEqual(
            decoded_payload["user_id"], self.valid_payload["user_id"]
        )
        self.assertEqual(
            decoded_payload["username"], self.valid_payload["username"]
        )

        self.assertIn("exp", decoded_payload)
        self.assertIsInstance(decoded_payload["exp"], int)

    def test_invalidate_token_flow(self):
        """Test token invalidation and subsequent validation failure."""
        token = self.jwt_manager.generate_token(
            {"user_id": 456, "role": "admin"}, expiry_seconds=3600
        )

        result = self.jwt_manager.validate_token(token)
        self.assertEqual(result["user_id"], 456)
        self.assertEqual(result["role"], "admin")

        self.jwt_manager.invalidate_token(token)

        with self.assertRaises(Exception) as context:
            self.jwt_manager.validate_token(token)
        self.assertIn("invalidated", str(context.exception).lower())

    def test_generate_token_empty_payload(self):
        """Test error handling for empty payload."""
        with self.assertRaises(ValueError) as context:
            self.jwt_manager.generate_token({}, expiry_seconds=3600)
        self.assertIn("empty", str(context.exception).lower())

    def test_invalid_secret_key_init(self):
        """Test error handling for invalid secret keys."""
        with self.assertRaises(ValueError) as context:
            JWTManager("")
        self.assertIn("secret", str(context.exception).lower())

        with self.assertRaises(ValueError) as context:
            JWTManager(None)
        self.assertIn("secret", str(context.exception).lower())

    def test_validate_expired_token(self):
        """Test validation of expired tokens."""
        token = self.jwt_manager.generate_token(
            {"user_id": 789, "action": "test"}, expiry_seconds=1
        )

        time.sleep(6)

        with self.assertRaises(jwt.ExpiredSignatureError):
            self.jwt_manager.validate_token(token)

    def test_validate_invalid_token_format(self):
        """Test validation of malformed tokens."""
        invalid_tokens = [
            "not.a.token",
            "only.two",
            "",
            "a.b.c.d",
            "invalid base64 content",
            "eyJhbGci.eyJ1c2Vy.!!invalid!!",
        ]

        for invalid_token in invalid_tokens:
            with self.assertRaises(Exception):
                self.jwt_manager.validate_token(invalid_token)

    def test_validate_tampered_token(self):
        """Test validation of tampered tokens."""
        token = self.jwt_manager.generate_token(
            {"user_id": 999}, expiry_seconds=3600
        )

        parts = token.split(".")
        tampered_payload = parts[1][:-1] + (
            "A" if parts[1][-1] != "A" else "B"
        )
        tampered_token = f"{parts[0]}.{tampered_payload}.{parts[2]}"

        with self.assertRaises(jwt.InvalidSignatureError):
            self.jwt_manager.validate_token(tampered_token)

    def test_duplicate_invalidation(self):
        """Test multiple invalidations of the same token."""
        token = self.jwt_manager.generate_token(
            {"user_id": 111}, expiry_seconds=3600
        )

        self.jwt_manager.invalidate_token(token)
        self.jwt_manager.invalidate_token(token)
        self.jwt_manager.invalidate_token(token)

        with self.assertRaises(Exception):
            self.jwt_manager.validate_token(token)

    def test_very_short_expiry(self):
        """Test tokens with very short expiry times."""
        payload = {"session_id": "abc123", "temp": True}
        token = self.jwt_manager.generate_token(payload, expiry_seconds=1)

        result = self.jwt_manager.validate_token(token)
        self.assertEqual(result["session_id"], "abc123")

        time.sleep(6)

        with self.assertRaises(jwt.ExpiredSignatureError):
            self.jwt_manager.validate_token(token)

    def test_large_payload(self):
        """Test handling of large payload data."""
        large_data = "x" * 7000
        large_payload = {
            "user_id": 222,
            "large_field": large_data,
            "metadata": {"version": 1, "type": "test"},
        }

        try:
            token = self.jwt_manager.generate_token(
                large_payload, expiry_seconds=3600
            )
            decoded = self.jwt_manager.validate_token(token)
            self.assertEqual(decoded["user_id"], 222)
            self.assertEqual(len(decoded["large_field"]), 7000)
        except ValueError as e:
            self.assertIn("size", str(e).lower())

    def test_blacklist_checked_before_decode(self):
        """Test blacklist checking before token decoding."""
        token = self.jwt_manager.generate_token(
            {"user_id": 333}, expiry_seconds=3600
        )

        self.jwt_manager.invalidate_token(token)

        with self.assertRaises(Exception) as context:
            self.jwt_manager.validate_token(token)
        self.assertIn("invalidated", str(context.exception).lower())

    def test_different_secret_keys(self):
        """Test token validation with different secret keys."""
        jwt_manager1 = JWTManager("secret_key_1")
        token = jwt_manager1.generate_token(
            {"user_id": 777}, expiry_seconds=3600
        )

        jwt_manager2 = JWTManager("secret_key_2")
        with self.assertRaises(jwt.InvalidSignatureError):
            jwt_manager2.validate_token(token)

    def test_algorithm_hs256(self):
        """Test token uses HS256 algorithm."""
        token = self.jwt_manager.generate_token(
            {"test": "data"}, expiry_seconds=3600
        )

        header_part = token.split(".")[0]
        padding = 4 - (len(header_part) % 4)
        if padding != 4:
            header_part += "=" * padding

        header = json.loads(base64.urlsafe_b64decode(header_part))
        self.assertEqual(header["alg"], "HS256")

    def test_generate_token_preserves_original_payload(self):
        """Test original payload is not modified during token generation."""
        original_payload = {"user_id": 888, "data": "original"}
        payload_copy = original_payload.copy()

        self.jwt_manager.generate_token(original_payload, expiry_seconds=3600)

        self.assertEqual(original_payload, payload_copy)
        self.assertNotIn("exp", original_payload)

    def test_multiple_users_tokens(self):
        """Test managing tokens for multiple users."""
        tokens = []

        for i in range(5):
            payload = {"user_id": i, "username": f"user_{i}"}
            token = self.jwt_manager.generate_token(
                payload, expiry_seconds=3600
            )
            tokens.append(token)

        self.jwt_manager.invalidate_token(tokens[1])
        self.jwt_manager.invalidate_token(tokens[3])

        for i, token in enumerate(tokens):
            if i in [1, 3]:
                with self.assertRaises(Exception):
                    self.jwt_manager.validate_token(token)
            else:
                result = self.jwt_manager.validate_token(token)
                self.assertEqual(result["user_id"], i)

    def test_invalid_expiry_seconds(self):
        """Test error handling for invalid expiry values."""
        invalid_expiry_values = [0, -1, -100, None]

        for expiry in invalid_expiry_values:
            with self.assertRaises(ValueError):
                self.jwt_manager.generate_token(
                    self.valid_payload, expiry_seconds=expiry
                )

    def test_token_type_validation(self):
        """Test validation with invalid token types."""
        invalid_tokens = [123, None, [], {}, True]

        for invalid_token in invalid_tokens:
            with self.assertRaises(Exception):
                self.jwt_manager.validate_token(invalid_token)

    def test_complete_user_session(self):
        """Test complete user session workflow."""
        login_payload = {
            "user_id": 1001,
            "username": "john_doe",
            "email": "john@example.com",
            "roles": ["user", "premium"],
        }
        session_token = self.jwt_manager.generate_token(
            login_payload, expiry_seconds=7200
        )

        for i in range(3):
            user_data = self.jwt_manager.validate_token(session_token)
            self.assertEqual(user_data["user_id"], 1001)
            self.assertEqual(user_data["username"], "john_doe")
            self.assertIn("exp", user_data)

        self.jwt_manager.invalidate_token(session_token)

        with self.assertRaises(Exception) as context:
            self.jwt_manager.validate_token(session_token)
        self.assertIn("invalidated", str(context.exception).lower())

    def test_payload_data_types(self):
        """Test handling of various payload data types."""
        complex_payload = {
            "user_id": 500,
            "is_active": True,
            "score": 98.5,
            "tags": ["python", "jwt", "security"],
            "metadata": {"created": "2024-01-01", "version": 2},
        }

        token = self.jwt_manager.generate_token(
            complex_payload, expiry_seconds=3600
        )
        decoded = self.jwt_manager.validate_token(token)

        self.assertEqual(decoded["user_id"], 500)
        self.assertEqual(decoded["is_active"], True)
        self.assertEqual(decoded["score"], 98.5)
        self.assertEqual(decoded["tags"], ["python", "jwt", "security"])
        self.assertEqual(decoded["metadata"]["version"], 2)


if __name__ == "__main__":
    unittest.main()
