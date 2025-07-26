# tests

"""
Unit tests for the Diffie-Hellman key exchange formatted output.

This module uses Python's standard library unittest framework to verify
the formatted string output of a Diffie-Hellman key exchange function.
"""

import unittest
from main import diffie_hellman_key_exchange


class TestDiffieHellmanFormattedOutput(unittest.TestCase):
    """Test formatted string output of diffie_hellman_key_exchange."""

    def parse_output(self, output):
        """Parse structured output string into dictionary of values."""
        a_pub = int(output[0].split(" ")[-1])
        b_pub = int(output[1].split(" ")[-1])
        a_shared = int(output[2].split(" ")[-1])
        b_shared = int(output[3].split(" ")[-1])
        return a_pub, b_pub, a_shared, b_shared

    def test_example_case(self):
        """Test the example from the problem statement."""
        result = diffie_hellman_key_exchange(23, 5, 6, 15)
        a_pub, b_pub, a_shared, b_shared = self.parse_output(result)
        self.assertEqual((a_pub, b_pub, a_shared, b_shared), (8, 19, 2, 2))

    def test_shared_secret_equality(self):
        """Ensure shared secrets from A and B are equal."""
        result = diffie_hellman_key_exchange(29, 2, 5, 9)
        _, _, a_shared, b_shared = self.parse_output(result)
        self.assertEqual(a_shared, b_shared)

    def test_large_private_keys(self):
        """Test with large private keys."""
        result = diffie_hellman_key_exchange(1019, 2, 1000, 999)
        _, _, a_shared, b_shared = self.parse_output(result)
        self.assertEqual(a_shared, b_shared)

    def test_min_private_keys(self):
        """Test private keys equal to 1."""
        result = diffie_hellman_key_exchange(97, 3, 1, 1)
        _, _, a_shared, b_shared = self.parse_output(result)
        self.assertEqual(a_shared, b_shared)

    def test_max_private_keys(self):
        """Test private keys equal to p - 1."""
        result = diffie_hellman_key_exchange(97, 5, 96, 96)
        _, _, a_shared, b_shared = self.parse_output(result)
        self.assertEqual(a_shared, b_shared)

    def test_identical_private_keys(self):
        """Identical private keys should yield same shared secret."""
        result = diffie_hellman_key_exchange(61, 6, 12, 12)
        _, _, a_shared, b_shared = self.parse_output(result)
        self.assertEqual(a_shared, b_shared)

    def test_public_key_range(self):
        """Public keys must be in the valid range."""
        result = diffie_hellman_key_exchange(101, 7, 45, 76)
        a_pub, b_pub, _, _ = self.parse_output(result)
        self.assertTrue(1 <= a_pub < 101)
        self.assertTrue(1 <= b_pub < 101)

    def test_shared_secret_range(self):
        """Shared secret must be in the valid range."""
        result = diffie_hellman_key_exchange(103, 9, 25, 37)
        _, _, a_shared, b_shared = self.parse_output(result)
        self.assertTrue(1 <= a_shared < 103)
        self.assertTrue(1 <= b_shared < 103)

    def test_large_prime(self):
        """Test with a large prime modulus."""
        p = 104729
        result = diffie_hellman_key_exchange(p, 2, 12345, 67890)
        _, _, a_shared, b_shared = self.parse_output(result)
        self.assertEqual(a_shared, b_shared)

    def test_base_edge_low(self):
        """Test with minimum allowed base."""
        result = diffie_hellman_key_exchange(71, 2, 8, 27)
        _, _, a_shared, b_shared = self.parse_output(result)
        self.assertEqual(a_shared, b_shared)

    def test_base_edge_high(self):
        """Test with maximum allowed base."""
        result = diffie_hellman_key_exchange(89, 87, 23, 31)
        _, _, a_shared, b_shared = self.parse_output(result)
        self.assertEqual(a_shared, b_shared)

    def test_prime_11(self):
        """Test with small modulus p = 11."""
        result = diffie_hellman_key_exchange(11, 2, 7, 9)
        _, _, a_shared, b_shared = self.parse_output(result)
        self.assertEqual(a_shared, b_shared)

    def test_prime_17(self):
        """Test with small modulus p = 17."""
        result = diffie_hellman_key_exchange(17, 3, 4, 5)
        _, _, a_shared, b_shared = self.parse_output(result)
        self.assertEqual(a_shared, b_shared)

    def test_commutative_shared_secret(self):
        """Test that swapping a and b gives same shared secret."""
        output1 = diffie_hellman_key_exchange(41, 6, 7, 9)
        output2 = diffie_hellman_key_exchange(41, 6, 9, 7)
        _, _, shared1, _ = self.parse_output(output1)
        _, _, shared2, _ = self.parse_output(output2)
        self.assertEqual(shared1, shared2)
