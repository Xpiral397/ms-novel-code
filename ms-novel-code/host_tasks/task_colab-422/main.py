"""JWT utility module for generation, validation, and blacklisting."""

import jwt
import time
from datetime import datetime, timezone


class JWTManager:
    """Manage JWT generation, validation, and invalidation using PyJWT."""

    MAX_TOKEN_BYTES = 8192

    def __init__(self, secret: str):
        """
        Initialize the JWTManager with a secret key.

        Args:
            secret: The secret key used for signing and verifying JWTs.

        Raises:
            ValueError: If the secret is empty.
        """
        if not secret:
            raise ValueError("Secret key cannot be empty.")
        self.__secret = secret
        self.__blacklist = set()
        self.__algorithm = "HS256"

    def generate_token(self, payload: dict, expiry_seconds: int = 3600) -> str:
        """
        Generate a JWT token with the given payload and expiry.

        Args:
            payload: A dictionary containing user data.
            expiry_seconds: The duration in seconds until the token expires.

        Returns:
            A string representing the generated JWT token.

        Raises:
            ValueError: If the payload is invalid or too large.
        """
        if not payload or not isinstance(payload, dict):
            raise ValueError("Payload must be a non-empty dictionary.")
        if not isinstance(expiry_seconds, int) or expiry_seconds <= 0:
            raise ValueError("Expiry seconds must be a positive integer.")

        token_payload = payload.copy()
        token_payload["exp"] = int(
            datetime.now(timezone.utc).timestamp() + expiry_seconds
        )

        try:
            token = jwt.encode(
                token_payload,
                self.__secret,
                algorithm=self.__algorithm
            )
            token_bytes = token.encode("utf-8")
            if len(token_bytes) > self.MAX_TOKEN_BYTES:
                raise ValueError(
                    f"Generated token byte size ({len(token_bytes)} bytes) "
                    f"exceeds recommended limit"
                    f" ({self.MAX_TOKEN_BYTES} bytes)."
                )
            return token
        except Exception as e:
            raise ValueError(f"Error generating token: {e}")

    def validate_token(self, token: str) -> dict:
        """
        Validate the JWT token and return the decoded payload if valid.

        Args:
            token: The JWT string to be validated.

        Returns:
            A dictionary containing the decoded payload.

        Raises:
            jwt.ExpiredSignatureError: If the token has expired.
            jwt.InvalidSignatureError: If the token's signature is invalid.
            jwt.DecodeError: If the token is malformed or invalid.
            ValueError: If the token is blacklisted.
        """
        if not isinstance(token, str) or token.count('.') != 2:
            raise jwt.DecodeError(
                "Invalid token format: Must have three segments."
            )

        if token in self.__blacklist:
            raise ValueError("Token has been invalidated (blacklisted).")

        try:
            return jwt.decode(
                token,
                self.__secret,
                algorithms=[self.__algorithm],
                leeway=5
            )
        except jwt.ExpiredSignatureError:
            raise jwt.ExpiredSignatureError("Token has expired.")
        except jwt.InvalidSignatureError:
            raise jwt.InvalidSignatureError("Invalid token signature.")
        except jwt.DecodeError as e:
            raise jwt.DecodeError(f"Invalid token: {e}")
        except Exception as e:
            raise ValueError(f"Unexpected error during validation: {e}")

    def invalidate_token(self, token: str) -> None:
        """
        Invalidate the given JWT token by adding it to a blacklist.

        Args:
            token: The JWT string to be invalidated.
        """
        if token:
            self.__blacklist.add(token)


if __name__ == "__main__":
    secret_key = "supersecretkey123"
    jwt_manager = JWTManager(secret_key)

    payload = {"user_id": 101, "role": "admin"}
    try:
        generated_token = jwt_manager.generate_token(payload,
                                                     expiry_seconds=30)
        print(f"Generated Token:\n{generated_token}")
    except ValueError as e:
        print(f"Error generating token: {e}")
        generated_token = None

    if generated_token:
        try:
            decoded_payload = jwt_manager.validate_token(generated_token)
            print(f"\nDecoded Payload:\n{decoded_payload}")
        except (
            jwt.ExpiredSignatureError,
            jwt.InvalidSignatureError,
            jwt.DecodeError,
            ValueError
        ) as e:
            print(f"Error validating token: {e}")

        print("\nInvalidating the token...")
        jwt_manager.invalidate_token(generated_token)
        print("Token invalidated.")

        try:
            jwt_manager.validate_token(generated_token)
        except (
            jwt.ExpiredSignatureError,
            jwt.InvalidSignatureError,
            jwt.DecodeError,
            ValueError
        ) as e:
            print(f"Expected validation failure after invalidation: {e}")

        print("\nTesting with an expired token...")
        expired_payload = {"user_id": 202}
        expired_token = jwt_manager.generate_token(expired_payload,
                                                   expiry_seconds=1)
        print(f"Generated expired token:\n{expired_token}")
        time.sleep(2)
        try:
            jwt_manager.validate_token(expired_token)
        except (
            jwt.ExpiredSignatureError,
            jwt.InvalidSignatureError,
            jwt.DecodeError,
            ValueError
        ) as e:
            print(f"Expected validation failure for expired token: {e}")

    print("\n--- Edge Cases ---")

    try:
        jwt_manager.generate_token({}, 3600)
    except ValueError as e:
        print(f"Expected error for empty payload: {e}")

    try:
        JWTManager("")
    except ValueError as e:
        print(f"Expected error for empty secret: {e}")

    try:
        jwt_manager.validate_token("invalid.token.format")
    except jwt.DecodeError as e:
        print(f"Expected error for invalid format (incorrect dots): {e}")

    try:
        jwt_manager.validate_token("abc.def.ghi")
    except jwt.DecodeError as e:
        print(f"Expected error for malformed token content: {e}")

    if generated_token:
        tampered_token = generated_token[:-5] + "AAAAA"
        try:
            jwt_manager.validate_token(tampered_token)
        except (
            jwt.ExpiredSignatureError,
            jwt.InvalidSignatureError,
            jwt.DecodeError,
            ValueError
        ) as e:
            print(f"Expected error for tampered token: {e}")

    if generated_token:
        print("\nAttempting duplicate invalidation...")
        jwt_manager.invalidate_token(generated_token)
        print("Duplicate invalidation call processed successfully.")

    long_payload = {"data": "A" * 6000}
    try:
        long_token = jwt_manager.generate_token(long_payload, 3600)
        print(f"Generated long token (length: {len(long_token)}).")
    except ValueError as e:
        print(f"Expected error for oversized token: {e}")

