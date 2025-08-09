"""Module for computing and verifying SHA 256 hashes with comparison."""
import hashlib
import hmac
import re


def compute_sha256_hash(message: str) -> str:
    """
    Compute the SHA-256 hash of a given message.

    Args:
        message (str): The input message to hash.

    Returns:
        str: The SHA-256 hexadecimal hash of the message.
    """
    if not isinstance(message, str):
        raise TypeError("message must be a string")

    sha256 = hashlib.sha256()
    sha256.update(message.encode('utf-8'))
    return sha256.hexdigest()


def verify_sha256_hash(message: str, expected_hash: str) -> bool:
    """
    Verify that a message matches the expected SHA-256 hash.

    Uses constant-time comparison to prevent timing attacks.

    Args:
        message (str): The original message to verify.
        expected_hash (str): The expected SHA-256 hexadecimal hash.

    Returns:
        bool: True if the hash matches the expected hash else False.
    """
    if not isinstance(message, str):
        raise TypeError("message must be a string")
    if not isinstance(expected_hash, str):
        raise TypeError("expected_hash must be a string")
    if not re.fullmatch(r'[0-9a-f]{64}', expected_hash):
        return False

    actual_hash = compute_sha256_hash(message)
    return hmac.compare_digest(actual_hash, expected_hash)


if __name__ == "__main__":
    msg = "Hello, world!"
    hash_val = compute_sha256_hash(msg)
    print("Hash:", hash_val)

    is_valid = verify_sha256_hash(msg, hash_val)
    print("Integrity check:", "Passed" if is_valid else "Failed")

    is_valid_tampered = verify_sha256_hash("Hacked message", hash_val)
    print("Tampered check:", "Passed" if is_valid_tampered else "Failed")

