"""Module for performing Diffie-Hellman key exchange using standard Python."""


def is_prime(n: int) -> bool:
    """Check if a number is prime."""
    if n <= 1:
        return False
    if n <= 3:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6
    return True


def diffie_hellman_key_exchange(
    p: int,
    g: int,
    a: int,
    b: int
) -> tuple[str, str, str, str]:
    """Perform Diffie-Hellman key exchange and return formatted output.

    Args:
        p (int): A large prime modulus.
        g (int): A primitive root modulo p.
        a (int): Private key of User A.
        b (int): Private key of User B.

    Returns:
        tuple[str, str, str, str]: A tuple containing:
            - Public Key of A
            - Public Key of B
            - Shared Secret (computed by A)
            - Shared Secret (computed by B)
    """
    if not all(isinstance(arg, int) for arg in [p, g, a, b]):
        raise TypeError("All inputs (p, g, a, b)"
                        " must be integers.")

    if p <= 2 or not is_prime(p):
        raise ValueError("p (modulus) must be a prime"
                         " number greater than 2.")

    if not (2 <= g <= p - 2):
        raise ValueError("g (base) must be an integer"
                         " in the range [2, p-2].")

    if not (1 <= a <= p - 1):
        raise ValueError("a (private key of User A)"
                         " must be in range [1, p-1].")

    if not (1 <= b <= p - 1):
        raise ValueError("b (private key of User B)"
                         " must be in range [1, p-1].")

    a_pub = pow(g, a, p)
    b_pub = pow(g, b, p)

    if not (1 <= a_pub <= p - 1):
        raise ValueError(
            f"Computed A's public key ({a_pub}) is not in range [1, p-1]."
        )
    if not (1 <= b_pub <= p - 1):
        raise ValueError(
            f"Computed B's public key ({b_pub}) is not in range [1, p-1]."
        )

    a_shared = pow(b_pub, a, p)
    b_shared = pow(a_pub, b, p)

    if not (1 <= a_shared <= p - 1):
        raise ValueError(
            f"Computed A's shared secret"
            f" ({a_shared}) is not in range [1, p-1]."
        )
    if not (1 <= b_shared <= p - 1):
        raise ValueError(
            f"Computed B's shared secret"
            f" ({b_shared}) is not in range [1, p-1]."
        )

    output_a_pub = f"Public Key of A: {a_pub}"
    output_b_pub = f"Public Key of B: {b_pub}"
    output_a_shared = f"Shared Secret (computed by A): {a_shared}"
    output_b_shared = f"Shared Secret (computed by B): {b_shared}"

    return output_a_pub, output_b_pub, output_a_shared, output_b_shared


if __name__ == "__main__":
    p_val = 23
    g_val = 5
    a_val = 6
    b_val = 15

    try:
        results = diffie_hellman_key_exchange(p_val, g_val, a_val, b_val)
        for line in results:
            print(line)
    except (TypeError, ValueError) as e:
        print(f"Error: {e}")

    print("\n--- Testing an invalid input (p not prime) ---")
    try:
        diffie_hellman_key_exchange(p=9, g=2, a=3, b=4)
    except (TypeError, ValueError) as e:
        print(f"Error: {e}")

    print("\n--- Testing an invalid input (g out of range) ---")
    try:
        diffie_hellman_key_exchange(p=23, g=1, a=3, b=4)
    except (TypeError, ValueError) as e:
        print(f"Error: {e}")

    print("\n--- Testing non-integer input ---")
    try:
        diffie_hellman_key_exchange(p=23.5, g=5, a=6, b=15)
    except (TypeError, ValueError) as e:
        print(f"Error: {e}")

