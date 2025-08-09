# tests

"""Unittest cases for testing compute and verify function for SHA256 hashes"""

import unittest
from main import compute_sha256_hash, verify_sha256_hash

class TestSha256HashVerification(unittest.TestCase):
    """Unit tests for SHA-256 hash computation and verification functions."""

    def test_empty_string(self):
        """Test hashing and verifying an empty string."""
        msg = ""
        hash_val = compute_sha256_hash(msg)
        self.assertTrue(verify_sha256_hash(msg, hash_val))
        self.assertFalse(verify_sha256_hash(" ", hash_val))

    def test_basic_ascii_string(self):
        """Test basic ASCII string hashing and verification."""
        msg = "Hello, world!"
        hash_val = compute_sha256_hash(msg)
        self.assertTrue(verify_sha256_hash(msg, hash_val))
        self.assertFalse(verify_sha256_hash("hello, world!", hash_val))

    def test_long_string(self):
        """Test hashing and verification of a very long string."""
        msg = "a" * 100000
        hash_val = compute_sha256_hash(msg)
        self.assertTrue(verify_sha256_hash(msg, hash_val))
        self.assertFalse(verify_sha256_hash(msg + "b", hash_val))

    def test_case_sensitivity_hash(self):
        """Test hash verification with case difference in message."""
        msg = "TestCase"
        hash_val = compute_sha256_hash(msg)
        self.assertTrue(verify_sha256_hash(msg, hash_val))
        self.assertFalse(verify_sha256_hash(msg.lower(), hash_val))

    def test_expected_hash_case_sensitivity(self):
        """Verify that hash matching is case-sensitive on expected_hash."""
        msg = "CaseTest"
        hash_val = compute_sha256_hash(msg)
        self.assertFalse(verify_sha256_hash(msg, hash_val.upper()))
        self.assertTrue(verify_sha256_hash(msg, hash_val))

    def test_different_messages(self):
        """Verify different messages produce different hashes."""
        msg1 = "Message One"
        msg2 = "Message Two"
        hash1 = compute_sha256_hash(msg1)
        hash2 = compute_sha256_hash(msg2)
        self.assertNotEqual(hash1, hash2)
        self.assertTrue(verify_sha256_hash(msg1, hash1))
        self.assertFalse(verify_sha256_hash(msg1, hash2))
        self.assertTrue(verify_sha256_hash(msg2, hash2))
        self.assertFalse(verify_sha256_hash(msg2, hash1))

    def test_invalid_hash_length(self):
        """Verify that invalid expected hash length leads to False."""
        msg = "Test message"
        hash_val = compute_sha256_hash(msg)
        self.assertFalse(verify_sha256_hash(msg, "abc123"))  # too short
        self.assertFalse(verify_sha256_hash(msg, hash_val + "00"))  # too long

    def test_non_hex_characters_in_expected_hash(self):
        """Verify expected_hash with non-hex characters returns False."""
        msg = "Test message"
        invalid_hash = "g" * 64  # invalid hex characters
        self.assertFalse(verify_sha256_hash(msg, invalid_hash))

    def test_repeated_verification_consistency(self):
        """Verify repeated calls to verify return consistent results."""
        msg = "Consistent message"
        hash_val = compute_sha256_hash(msg)
        for _ in range(10):
            self.assertTrue(verify_sha256_hash(msg, hash_val))
            self.assertFalse(verify_sha256_hash(msg + "x", hash_val))

    def test_whitespace_variations(self):
        """Verify messages differing by whitespace fail verification."""
        msg1 = "Whitespace test"
        msg2 = "Whitespace  test"  # two spaces
        hash1 = compute_sha256_hash(msg1)
        self.assertTrue(verify_sha256_hash(msg1, hash1))
        self.assertFalse(verify_sha256_hash(msg2, hash1))

    def test_multiline_string(self):
        """Test hashing and verifying a multiline string."""
        msg = "Line one\nLine two\nLine three"
        hash_val = compute_sha256_hash(msg)
        self.assertTrue(verify_sha256_hash(msg, hash_val))
        self.assertFalse(verify_sha256_hash(msg.replace("\n", " "), hash_val))

    def test_message_with_numbers_and_symbols(self):
        """Test message containing numbers and symbols."""
        msg = "1234567890!@#$%^&*()_+-=[]{}|;:',.<>/?"
        hash_val = compute_sha256_hash(msg)
        self.assertTrue(verify_sha256_hash(msg, hash_val))
        self.assertFalse(verify_sha256_hash(msg + "!", hash_val))

    def test_message_with_only_spaces(self):
        """Test message consisting of only spaces."""
        msg = "     "
        hash_val = compute_sha256_hash(msg)
        self.assertTrue(verify_sha256_hash(msg, hash_val))
        self.assertFalse(verify_sha256_hash("", hash_val))

    def test_non_string_message_type(self):
        """Verify that passing non-string type raises an error."""
        with self.assertRaises(TypeError):
            compute_sha256_hash(12345)  # int instead of str
