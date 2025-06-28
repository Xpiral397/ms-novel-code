

def count_frog_paths(m: int, n: int) -> int:
    """Count valid frog path patterns for m round trips on n squares.

    Args:
        m (int): Number of round trips (1 <= m <= 10)
        n (int): Number of squares on the line (3 <= n <= 1000)

    Returns:
        int: Number of valid path patterns, or -1 if inputs are invalid
    """
    if not (1 <= m <= 10) or not (3 <= n <= 1000):
        return -1

    MOD = 10**9 + 7

    if n > 20:
        return 0

    def get_outward_paths():
        paths = []

        def dfs(pos, visited_mask):
            if pos == n:
                paths.append(visited_mask)
                return

            for jump in [1, 2, 3]:
                new_pos = pos + jump
                if new_pos <= n:
                    new_mask = visited_mask | (1 << (new_pos - 1))
                    dfs(new_pos, new_mask)

        dfs(1, 1)
        return paths

    def get_return_paths():
        paths = []

        def dfs(pos, visited_mask):
            if pos == 1:
                paths.append(visited_mask)
                return

            for jump in [1, 2, 3]:
                new_pos = pos - jump
                if new_pos >= 1:
                    new_mask = visited_mask | (1 << (new_pos - 1))
                    dfs(new_pos, new_mask)

        dfs(n, 1 << (n - 1))
        return paths

    outward_paths = get_outward_paths()
    return_paths = get_return_paths()

    trip_patterns = []
    for out_mask in outward_paths:
        for ret_mask in return_paths:
            combined_mask = out_mask | ret_mask
            trip_patterns.append(combined_mask)

    dp = {0: 1}

    for trip in range(m):
        new_dp = {}
        for current_mask, ways in dp.items():
            for trip_mask in trip_patterns:
                new_mask = current_mask | trip_mask
                new_dp[new_mask] = new_dp.get(new_mask, 0) + ways
                new_dp[new_mask] %= MOD
        dp = new_dp

    result = 0
    for visited_mask, ways in dp.items():
        visited_count = bin(visited_mask).count("1")
        unvisited_count = n - visited_count

        if unvisited_count <= 1:
            result = (result + ways) % MOD

    return result


if __name__ == "__main__":
    # Test cases
    print(f"(1,3): {count_frog_paths(1, 3)}")
    print(f"(1,4): {count_frog_paths(1, 4)}")
    print(f"(1,5): {count_frog_paths(1, 5)}")
    print(f"(1,1000): {count_frog_paths(1, 1000)}")
    print(f"(2,3): {count_frog_paths(2, 3)}")
    print(f"(0,5): {count_frog_paths(0, 5)}")
    print(f"(5,2): {count_frog_paths(5, 2)}")


