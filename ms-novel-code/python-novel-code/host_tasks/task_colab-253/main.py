# main

"""
Implements the Observer Pattern and three algorithm executors
(MergeSort, QuickSort, BFS) that emit events to observers.
"""

from abc import ABC, abstractmethod
from collections import deque
from typing import Any, Dict, List, Set


class Observer(ABC):
    """
    Abstract Observer requiring an update(event, data) method.
    """

    @abstractmethod
    def update(self, event: str, data: Any) -> None:
        pass


class Subject:
    """
    Maintains a list of observers and notifies them of events.
    """

    def __init__(self):
        self._observers: List[Observer] = []

    def attach(self, observer: Observer) -> None:
        if observer not in self._observers:
            self._observers.append(observer)

    def detach(self, observer: Observer) -> None:
        if observer in self._observers:
            self._observers.remove(observer)

    def notify(self, event: str, data: Any) -> None:
        for observer in list(self._observers):
            try:
                observer.update(event, data)
            except Exception as error:
                print(f"[error in observer] {error}")


class MergeSortExecutor(Subject):
    """
    MergeSort executor emitting start/compare/merge/end events.
    """

    def sort(self, arr: List[int]) -> List[int]:
        self.notify("start", arr.copy())
        if len(set(arr)) <= 1:
            self.notify("end", arr.copy())
            return arr.copy()
        result = self._merge_sort(arr)
        self.notify("end", result.copy())
        return result

    def _merge_sort(self, arr: List[int]) -> List[int]:
        if len(arr) <= 1:
            return arr
        mid = len(arr) // 2
        left = self._merge_sort(arr[:mid])
        right = self._merge_sort(arr[mid:])
        merged = self._merge(left, right)
        self.notify("merge", merged.copy())
        return merged

    def _merge(self, left: List[int], right: List[int]) -> List[int]:
        i = j = 0
        merged: List[int] = []
        while i < len(left) and j < len(right):
            self.notify("compare", {"left": left[i], "right": right[j]})
            if left[i] < right[j]:
                merged.append(left[i])
                i += 1
            else:
                merged.append(right[j])
                j += 1
        merged.extend(left[i:])
        merged.extend(right[j:])
        return merged


class QuickSortExecutor(Subject):
    """
    QuickSort executor emitting start/pivot/compare/swap/end events.
    """

    def sort(self, arr: List[int]) -> List[int]:
        self.notify("start", arr.copy())
        self._quick_sort(arr, 0, len(arr) - 1)
        self.notify("end", arr.copy())
        return arr

    def _quick_sort(self, arr: List[int], low: int, high: int) -> None:
        if low < high:
            p = self._partition(arr, low, high)
            self._quick_sort(arr, low, p - 1)
            self._quick_sort(arr, p + 1, high)

    def _partition(self, arr: List[int], low: int, high: int) -> int:
        pivot = arr[high]
        self.notify("pivot", pivot)
        i = low
        for j in range(low, high):
            self.notify("compare", {"i": j, "val": arr[j], "pivot": pivot})
            if arr[j] < pivot:
                arr[i], arr[j] = arr[j], arr[i]
                self.notify("swap", {"i": i, "j": j, "arr": arr.copy()})
                i += 1
        arr[i], arr[high] = arr[high], arr[i]
        self.notify("swap", {"i": i, "j": high, "arr": arr.copy()})
        return i


class BFSExecutor(Subject):
    """
    BFS executor emitting bfs_start/visit/enqueue/bfs_end or error.
    """

    def bfs(self, graph: Dict[Any, List[Any]], start: Any) -> Set[Any]:
        if start not in graph:
            self.notify("error", f"start node {start!r} not in graph")
            return set()

        visited: Set[Any] = set()
        queue = deque([start])
        self.notify("bfs_start", start)

        while queue:
            node = queue.popleft()
            if node not in visited:
                visited.add(node)
                self.notify("visit", node)
                for neighbor in graph.get(node, []):
                    self.notify("enqueue", neighbor)
                    if neighbor not in visited:
                        queue.append(neighbor)

        self.notify("bfs_end", visited.copy())
        return visited


class PrintObserver(Observer):
    """
    Observer that prints every event.
    """

    def update(self, event: str, data: Any) -> None:
        print(f"[{event}] {data}")


class FilterObserver(Observer):
    """
    Observer that only logs a subset of event types.
    """

    def __init__(self, allowed: List[str]) -> None:
        self.allowed = set(allowed)

    def update(self, event: str, data: Any) -> None:
        if event in self.allowed:
            print(f">>> filtered {event}: {data}")


class OneShotObserver(Observer):
    """
    Unsubscribes itself after the first occurrence of its trigger.
    """

    def __init__(self, subject: Subject, trigger: str) -> None:
        self.subject = subject
        self.trigger = trigger

    def update(self, event: str, data: Any) -> None:
        if event == self.trigger:
            self.subject.detach(self)


class ErrorObserver(Observer):
    """
    Raises an error when a specified event occurs.
    """

    def __init__(self, fail_on: str) -> None:
        self.fail_on = fail_on

    def update(self, event: str, data: Any) -> None:
        if event == self.fail_on:
            raise RuntimeError(f"intentional failure at {event}")
        print(f"ErrorObserver saw {event}")

