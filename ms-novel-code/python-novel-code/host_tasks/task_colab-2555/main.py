from collections import defaultdict
from bisect import bisect_left, bisect_right
from typing import List

class MajorityChecker:
    def __init__(self, arr: List[int]):
        self.arr = arr
        self.n = len(arr)
        self.segment_tree = [None] * (4 * self.n)
        self.build(0, 0, self.n - 1)
        self.pos = defaultdict(list)
        for idx, val in enumerate(arr):
            self.pos[val].append(idx)

    def build(self, node, start, end):
        if start == end:
            self.segment_tree[node] = (self.arr[start], 1)
        else:
            mid = (start + end) // 2
            left_child = 2 * node + 1
            right_child = 2 * node + 2
            self.build(left_child, start, mid)
            self.build(right_child, mid + 1, end)
            self.segment_tree[node] = self.merge(
                self.segment_tree[left_child],
                self.segment_tree[right_child]
            )

    def merge(self, left_info, right_info):
        if left_info[0] == right_info[0]:
            return (left_info[0], left_info[1] + right_info[1])
        elif left_info[1] > right_info[1]:
            return (left_info[0], left_info[1] - right_info[1])
        else:
            return (right_info[0], right_info[1] - left_info[1])

    def count_in_range(self, val, left, right):
      indices = self.pos[val]
      return bisect_right(indices, right) - bisect_left(indices, left)

    def query(self, left: int, right: int, threshold: int) -> int:
        maj = self.query_majority(0, 0, self.n - 1, left, right)
        if maj == -1:
            return -1

        count = self.count_in_range(maj, left, right)
        return maj if count >= threshold else -1

    def query_majority(self, node, start, end, left, right):
        if right < start or end < left:
            return -1
        if left <= start and end <= right:
            return self.segment_tree[node][0]
        mid = (start + end) // 2
        left_maj = self.query_majority(2 * node + 1, start, mid, left, right)
        right_maj = self.query_majority(2 * node + 2, mid + 1, end, left, right)

        if left_maj == -1:
            return right_maj
        if right_maj == -1:
            return left_maj

        if left_maj == right_maj:
            return left_maj

        left_count = sum(1 for i in range(max(left, start), min(right + 1, end + 1)) if self.arr[i] == left_maj)
        right_count = sum(1 for i in range(max(left, start), min(right + 1, end + 1)) if self.arr[i] == right_maj)

        return left_maj if left_count > right_count else right_maj

# Example usage:
arr = [1, 1, 2, 2, 1, 1]
majorityChecker = MajorityChecker(arr)
print(majorityChecker.query(0, 5, 4))  # Output: 1
print(majorityChecker.query(0, 3, 3))  # Output: -1
arr = [5, 5, 1, 5, 2, 5, 5, 3]
majorityChecker = MajorityChecker(arr)
print(majorityChecker.query(0, 7, 5))  # Output: 5
