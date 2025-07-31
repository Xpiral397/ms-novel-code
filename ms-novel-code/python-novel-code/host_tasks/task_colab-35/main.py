
import sys
import numpy as np


class OrderLookup:
    """Locate first occurrence of target order ID by linear scan"""

    @staticmethod
    def find_order(orders: list[int], target: int) -> tuple[int, int]:
        if not isinstance(orders, list):
            raise TypeError("orders must be a list of integers")

        size = len(orders)
        if size > 10000:
            raise ValueError("orders length exceeds 10,000")

        allowed = (int, np.int32, np.int64)

        if type(target) not in allowed or isinstance(target, bool):
            raise TypeError("target must be an integer")
        if target < -sys.maxsize - 1 or target > sys.maxsize:
            raise ValueError("target must be within the valid integer range")

        if size == 0:
            return (-1, 0)

        for order in orders:
            if type(order) not in allowed or isinstance(order, bool):
                raise TypeError("orders must contain only integers")
            if order < -sys.maxsize - 1 or order > sys.maxsize:
                raise ValueError()

        comparisons = 0
        for idx in range(size):
            comparisons += 1
            if orders[idx] == target:
                return (idx, comparisons)

        return (-1, comparisons)
