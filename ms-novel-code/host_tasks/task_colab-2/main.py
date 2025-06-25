
"""
Computes the sum of k-Ruff numbers that are less than Nk and end in digit 7.

The result is computed modulo 1000000007.
"""

from typing import List


def compute_k_ruff_sum(k: int) -> int:
    """
    Compute the sum of all k-Ruff numbers less than Nk that end in digit 7.

    A k-Ruff number is not divisible by any element in Sk.
    Sk = {2, 5} ∪ {first k primes ending in 7}.
    Nk = product of elements in Sk.
    F(k) = sum of k-Ruff numbers < Nk ending in digit 7.
    Return the result modulo 1000000007.
    """
    mod = 1000000007

    # Step 1: Generate the first k primes ending in 7
    primes_ending_in_7: List[int] = []
    limit = 8000  # Safe upper bound; 97th such prime is 7927

    # Sieve of Eratosthenes to find all primes up to the limit
    is_prime = [True] * (limit + 1)
    is_prime[0] = is_prime[1] = False
    for p in range(2, int(limit ** 0.5) + 1):
        if is_prime[p]:
            for multiple in range(p * p, limit + 1, p):
                is_prime[multiple] = False

    # Collect the first k primes ending in digit 7
    for num in range(7, limit + 1):
        if len(primes_ending_in_7) == k:
            break
        if num % 10 == 7 and is_prime[num]:
            primes_ending_in_7.append(num)

    # Step 2: Compute pk = product of the primes in Sk modulo mod
    pk_product = 1
    for prime in primes_ending_in_7:
        pk_product = (pk_product * prime) % mod

    # Step 3: Compute c = product of (prime - 1) modulo mod
    c_product = 1
    for prime in primes_ending_in_7:
        c_product = (c_product * (prime - 1)) % mod

    # Step 4: Compute sum_k = ((-2)^k - 1) / 3 modulo mod
    inv_3 = pow(3, mod - 2, mod)  # Modular inverse of 3
    term_neg2_pow_k = pow(-2, k, mod)
    sum_k = (term_neg2_pow_k - 1 + mod) % mod
    sum_k = (sum_k * inv_3) % mod

    # Step 5: Compute F(k) = pk * (5 * c + 7 + sum_k) modulo mod
    term1 = (5 * c_product) % mod
    term2 = 7
    total_inner_sum = (term1 + term2 + sum_k) % mod
    f_k = (pk_product * total_inner_sum) % mod

    return f_k


print(compute_k_ruff_sum(97))

