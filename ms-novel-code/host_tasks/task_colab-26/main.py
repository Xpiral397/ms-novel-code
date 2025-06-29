
import math

def count_digit_factorial_chains(limit: int, required_length: int) -> int:
    # Precompute factorials of digits 0 to 9
    digit_factorials = [math.factorial(i) for i in range(10)]

    # Cache to memoize chain lengths
    chain_length_cache = {}

    def next_term(n: int) -> int:
        """Returns the sum of the factorial of the digits of n"""
        total = 0
        while n > 0:
            total += digit_factorials[n % 10]
            n //= 10
        return total

    def compute_chain_length(start: int) -> int:
        """Computes the non-repeating chain length for a given starting number"""
        visited = []
        seen = set()
        current = start

        while current not in seen:
            if current in chain_length_cache:
                # Use cached result
                total_length = len(visited) + chain_length_cache[current]
                break
            seen.add(current)
            visited.append(current)
            current = next_term(current)
        else:
            # A loop was encountered
            total_length = len(visited)

        # Cache the results for all unique numbers in this chain
        for index, value in enumerate(visited):
            if value not in chain_length_cache:
                chain_length_cache[value] = total_length - index

        return total_length

    # Main loop to count how many chains have exactly the required length
    count = 0
    for n in range(1, limit):
        if compute_chain_length(n) == required_length:
            count += 1

    return count

print(count_digit_factorial_chains(10000, 3)) # 147
print(count_digit_factorial_chains(10000, 5)) # 57
print(count_digit_factorial_chains(1000000, 60)) # 402
