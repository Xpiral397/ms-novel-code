
from collections import OrderedDict
from typing import List

def generate_pentagonal(index: int) -> int:
    """
    Generate the nth pentagonal number using P(n) = n(3n-1)/2.

    Args:
        index: The index n (1-based)

    Returns:
        The nth pentagonal number
    """
    return (index * (3 * index - 1)) // 2

def is_pentagonal(x: int) -> bool:
    """
    Check if a number is pentagonal using inverse formula.

    P(n) = n(3n-1)/2
    Solving for n: n = (1 + sqrt(1 + 24x)) / 6

    Args:
        x: Number to check

    Returns:
        True if x is a pentagonal number
    """
    if x < 1:
        return False

    # Check if discriminant is a perfect square
    discriminant = 1 + 24 * x
    sqrt_discriminant = int(discriminant ** 0.5)

    if sqrt_discriminant * sqrt_discriminant != discriminant:
        return False

    # Check if n is a positive integer
    n = (1 + sqrt_discriminant) / 6
    return n == int(n) and n >= 1

class LRUPentagonalCache:
    """
    LRU cache for pentagonal numbers with max 100 items.
    Constraint: "System can store maximum 100 pentagonal numbers simultaneously"
    """

    def __init__(self, capacity: int = 100):
        self.cache = OrderedDict()
        self.capacity = capacity

    def get(self, index: int) -> int:
        """Get pentagonal number, implementing LRU eviction."""
        if index in self.cache:
            # Move to end (most recently used)
            self.cache.move_to_end(index)
            return self.cache[index]

        # Compute and cache with LRU eviction
        value = generate_pentagonal(index)

        if len(self.cache) >= self.capacity:
            # Evict least recently used
            self.cache.popitem(last=False)

        self.cache[index] = value
        return value

    def size(self) -> int:
        """Current cache size for debugging."""
        return len(self.cache)

def insertion_sort(arr: List, key=lambda x: x) -> None:
    """
    Custom insertion sort implementation.
    Constraint: "Do not use inbuilt sort function"

    Args:
        arr: List to sort in-place
        key: Key function for sorting
    """
    for i in range(1, len(arr)):
        current_value = arr[i]
        j = i - 1
        while j >= 0 and key(arr[j]) > key(current_value):
            arr[j + 1] = arr[j]
            j -= 1
        arr[j + 1] = current_value

def solve_pentagonal_sums(n: int, min_ways: int) -> List[List]:
    """
    Find pentagonal numbers expressible as sums of two pentagonals in multiple ways.

    Implements ALL constraints:
    - Memory limit: 100 pentagonal numbers max via LRU cache
    - Streaming: Uses inverse formula instead of storing full sets
    - Custom sort: Uses insertion_sort implementation
    - Best effort: Results may be incomplete due to memory constraints

    Args:
        n: Maximum pentagonal index to generate and check (1 <= n <= 100)
        min_ways: Minimum number of ways to express as sum (1 <= min_ways <= 10)

    Returns:
        List of [pentagonal_number, ways_count, combinations] sorted by pentagonal_number
    """
    # Edge case: need at least 2 numbers for sum
    if n < 2:
        return []

    # Initialize LRU cache for constraint compliance
    pentagonal_cache = LRUPentagonalCache(capacity=100)

    # Track results: sum_value -> list of [p1, p2] pairs
    results = {}

    # Streaming approach: generate pairs on-demand without storing full sets
    # Constraint: "Each sum validation must use streaming approach without storing full number sets"

    for i in range(1, n + 1):
        for j in range(i, n + 1):  # j >= i to avoid duplicate pairs
            # Get pentagonal numbers via LRU cache
            p1 = pentagonal_cache.get(i)
            p2 = pentagonal_cache.get(j)

            sum_value = p1 + p2

            # Use inverse formula instead of set membership check
            # This is the key optimization: O(1) validation vs O(n) lookup
            if is_pentagonal(sum_value):
                if sum_value not in results:
                    results[sum_value] = []

                # Store pair with smaller number first
                pair = [min(p1, p2), max(p1, p2)]

                # Avoid duplicate pairs
                if pair not in results[sum_value]:
                    results[sum_value].append(pair)

    # Build final results list
    final_results = []

    for sum_value, combinations in results.items():
        if len(combinations) >= min_ways:
            # Custom sort combinations by first element, then second
            insertion_sort(combinations, key=lambda x: (x[0], x[1]))

            final_results.append([sum_value, len(combinations), combinations])

    # Custom sort final results by pentagonal number value
    insertion_sort(final_results, key=lambda x: x[0])

    return final_results

def solve():
    """
    Main solve function that reads input and processes the pentagonal sum problem.
    Handles input format: "n min_ways" on a single line.
    """
    import sys

    # Read input
    data = sys.stdin.read().strip().split()
    n, min_ways = map(int, data)

    # Validate input constraints
    if not (1 <= n <= 100):
        print([])  # Invalid input, return empty result
        return

    if not (1 <= min_ways <= 10):
        print([])  # Invalid input, return empty result
        return

    # Compute results
    result = solve_pentagonal_sums(n, min_ways)

    # Print result in required format
    print(result)

# Test the solution with provided examples
def test_examples():
    """Test the solution against provided examples."""

    print("=== Testing Example 1 ===")
    result1 = solve_pentagonal_sums(20, 1)
    print(f"Input: n=20, min_ways=1")
    print(f"Output: {result1}")
    print(f"Expected: [[92, 1, [[22, 70]]]]")
    print(f"Match: {result1 == [[92, 1, [[22, 70]]]]}")

    print("\n=== Testing Example 2 ===")
    result2 = solve_pentagonal_sums(50, 2)
    print(f"Input: n=50, min_ways=2")
    print(f"Output: {result2}")
    print(f"Expected: [[3577, 2, [[145, 3432], [287, 3290]]]]")
    print(f"Match: {result2 == [[3577, 2, [[145, 3432], [287, 3290]]]]}")

    print("\n=== Testing Inverse Formula ===")
    test_numbers = [1, 5, 12, 22, 35, 51, 70, 92, 117, 145]
    non_pentagonal = [2, 3, 4, 6, 7, 8, 9, 10, 11, 13]

    print("Pentagonal numbers:")
    for num in test_numbers:
        print(f"  {num}: {is_pentagonal(num)}")

    print("Non-pentagonal numbers:")
    for num in non_pentagonal:
        print(f"  {num}: {is_pentagonal(num)}")

if __name__ == "__main__":
    test_examples()

