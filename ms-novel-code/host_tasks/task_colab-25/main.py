
import sys
sys.setrecursionlimit(15000)

def palindromic_prime_sum(low: int, high: int) -> int:

    # Check all valid edge cases
    if low >= high or low < 10 or high > 10000:
        return 0

    # Generate all primes up to 'high' using Sieve of Eratosthenes
    def generate_primes(limit: int) -> list:
        sieve = [True] * (limit + 1)
        sieve[0] = sieve[1] = False
        for i in range(2, int(limit ** 0.5) + 1):
            if sieve[i]:
                for j in range(i * i, limit + 1, i):
                    sieve[j] = False
        return [i for i, is_prime in enumerate(sieve) if is_prime]

    primes = generate_primes(high)
    prime_set = set(primes)

    # Check if n is palindromic
    def is_palindrome(n: int) -> bool:
        return str(n) == str(n)[::-1]

    # Recursively check the conditions for each number in (low, high)
    def recurse(n: int, acc: int) -> int:
        if n >= high:
            return acc
        if is_palindrome(n):
            # Check if n can be expressed as a sum of two primes
            for p in primes:
                if p > n // 2:
                    break
                if (n - p) in prime_set:
                    return recurse(n + 1, acc + n)
        return recurse(n + 1, acc)

    return recurse(low + 1, 0)


print(palindromic_prime_sum(21, 52)) # 99
print(palindromic_prime_sum(10, 300)) # 3461
print(palindromic_prime_sum(11, 300)) # 3461
print(palindromic_prime_sum(699, 1697)) # 18377
print(palindromic_prime_sum(699, 1698)) # 18377
print(palindromic_prime_sum(8990, 10000)) #46464
print(palindromic_prime_sum(1, 30)) # 0
print(palindromic_prime_sum(8990, 100000)) # 0
print(palindromic_prime_sum(100001, 1000000)) # 0
