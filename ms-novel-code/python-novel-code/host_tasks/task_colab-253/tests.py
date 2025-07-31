# test

"""
test.py

Unit tests for Subject/Observer framework and executors per prompt.
"""

import unittest
from collections import deque
from typing import Any, List, Dict, Set

import main
from main import (
    Subject,
    MergeSortExecutor,
    QuickSortExecutor,
    BFSExecutor,
    FilterObserver,
    OneShotObserver,
    ErrorObserver,
)


class RecordingObserver:
    """Records received (event, data) tuples."""
    def __init__(self) -> None:
        self.events: List[tuple[str, Any]] = []

    def update(self, event: str, data: Any) -> None:
        self.events.append((event, data))


class TestObserverFramework(unittest.TestCase):
    """Comprehensive tests covering every requirement."""

    def test_subject_attach_detach_notify(self) -> None:
        subj = Subject()
        rec = RecordingObserver()

        subj.detach(rec)
        subj.notify("foo", 1)
        self.assertEqual(rec.events, [])

        subj.attach(rec)
        subj.notify("bar", "x")
        self.assertEqual(rec.events, [("bar", "x")])

        rec.events.clear()
        subj.detach(rec)
        subj.notify("baz", None)
        self.assertEqual(rec.events, [])

    def test_merge_sort_basic_and_events(self) -> None:
        ms = MergeSortExecutor()
        rec = RecordingObserver()
        ms.attach(rec)

        sorted_arr = ms.sort([3, 1, 2])
        self.assertEqual(sorted_arr, [1, 2, 3])

        names = [evt for evt, _ in rec.events]
        self.assertEqual(names[0], "start")
        self.assertEqual(names[-1], "end")
        self.assertIn("compare", names)
        self.assertIn("merge", names)

    def test_merge_sort_empty_and_duplicates(self) -> None:
        ms = MergeSortExecutor()
        rec = RecordingObserver()
        ms.attach(rec)

        self.assertEqual(ms.sort([]), [])
        names = [evt for evt, _ in rec.events]
        self.assertEqual(names, ["start", "end"])

        rec.events.clear()
        self.assertEqual(ms.sort([2, 2, 2]), [2, 2, 2])
        names = [evt for evt, _ in rec.events]
        self.assertEqual(names, ["start", "end"])

    def test_quick_sort_basic_and_events(self) -> None:
        qs = QuickSortExecutor()
        rec = RecordingObserver()
        qs.attach(rec)

        result = qs.sort([5, 4, 3, 2, 1])
        self.assertEqual(result, [1, 2, 3, 4, 5])

        names = [evt for evt, _ in rec.events]
        self.assertEqual(names[0], "start")
        self.assertEqual(names[-1], "end")
        self.assertTrue(any(e == "pivot" for e in names))
        self.assertTrue(any(e == "compare" for e in names))
        self.assertTrue(any(e == "swap" for e in names))

    def test_quick_sort_identical_elements(self) -> None:
        qs = QuickSortExecutor()
        rec = RecordingObserver()
        qs.attach(rec)

        self.assertEqual(qs.sort([1, 1, 1]), [1, 1, 1])
        names = [evt for evt, _ in rec.events]
        self.assertTrue(any(e == "pivot" for e in names))

    def test_bfs_missing_start_only_error(self) -> None:
        bfs = BFSExecutor()
        rec = RecordingObserver()
        bfs.attach(rec)

        result = bfs.bfs({"A": ["B"]}, "Z")
        self.assertEqual(result, set())
        self.assertEqual(
            rec.events,
            [("error", "start node 'Z' not in graph")]
        )

    def test_bfs_cycle_and_event_order(self) -> None:
        graph: Dict[str, List[str]] = {
            "A": ["B", "C"],
            "B": ["A", "D", "E"],
            "C": ["A", "F"],
            "D": [],
            "E": ["F"],
            "F": []
        }
        bfs = BFSExecutor()
        rec = RecordingObserver()
        bfs.attach(rec)

        visited = bfs.bfs(graph, "A")
        self.assertEqual(visited, {"A", "B", "C", "D", "E", "F"})

        names = [evt for evt, _ in rec.events]
        self.assertEqual(names[0], "bfs_start")
        self.assertEqual(names[-1], "bfs_end")
        self.assertIn("visit", names)
        self.assertIn("enqueue", names)

    def test_bfs_uses_deque_for_performance(self) -> None:
        fn_globals = BFSExecutor.bfs.__globals__
        from collections import deque as _dq  # noqa: F401
        self.assertIs(fn_globals.get("deque"), _dq)

    def test_filter_observer_no_exceptions(self) -> None:
        ms = MergeSortExecutor()
        rec = RecordingObserver()
        filt = FilterObserver(allowed=["merge"])

        ms.attach(rec)
        ms.attach(filt)
        ms.sort([3, 2, 1])  # no exceptions

        names = [evt for evt, _ in rec.events]
        self.assertIn("merge", names)

    def test_one_shot_observer_detaches(self) -> None:
        ms = MergeSortExecutor()
        one = OneShotObserver(subject=ms, trigger="merge")
        rec = RecordingObserver()
        ms.attach(rec)
        ms.attach(one)

        ms.sort([2, 1])
        before = len(ms._observers)
        ms.sort([3, 2])
        after = len(ms._observers)

        self.assertEqual(after, before)

    def test_error_observer_swallowed(self) -> None:
        ms = MergeSortExecutor()
        rec = RecordingObserver()
        err = ErrorObserver(fail_on="merge")

        ms.attach(rec)
        ms.attach(err)
        self.assertEqual(ms.sort([3, 1, 2]), [1, 2, 3])

        names = [evt for evt, _ in rec.events]
        self.assertIn("merge", names)


if __name__ == "__main__":
    unittest.main()
