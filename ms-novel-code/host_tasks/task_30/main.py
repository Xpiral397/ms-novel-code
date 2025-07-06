from typing import List
def last_ant_fall_time(n: int, l1: List[int], l2: List[int]) -> int:
    if not l1 and not l2:
      return 0

    l2 = [n-i for i in l2]

    if not l2:
        return max(l1)
    if not l1:
        return max(l2)
    answer = max(max([i for i in l1 if i not in [0, n]]), max([i for i in l1 if i not in [0, n]]))
    return answer

# Examples
print(last_ant_fall_time(10, [2, 6], [7]))  # Output: 6
print(last_ant_fall_time(100, [10, 50, 90], [0, 100]))  # Output: 90
