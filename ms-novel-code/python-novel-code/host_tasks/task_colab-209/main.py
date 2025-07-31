
from __future__ import annotations

import heapq
import itertools
import threading
import time
import weakref
import types
from contextlib import contextmanager
from dataclasses import dataclass
from types import TracebackType
from typing import Any, Callable, Dict, List, Optional, Tuple


class SubscriberError(RuntimeError):
    """Raised after broadcast if one or more subscribers raised."""
    def __init__(self, *exc_info: Tuple[BaseException, TracebackType]) -> None:
        super().__init__(f"{len(exc_info)} subscriber(s) raised")
        self.exc_info = exc_info


@dataclass(slots=True)
class _Entry:
    priority: int
    index: int
    token: int
    once: bool = False
    ttl: Optional[int] = None
    filter: Optional[Callable[[Any], bool]] = None
    fn_ref: Callable[[], Optional[Callable[[Any], Any]]] = lambda: None

    def __lt__(self, other: _Entry, /) -> bool:
        return (self.priority, self.index) < (other.priority, other.index)


class Publisher:
    _token_src = itertools.count(1)
    _index_src = itertools.count()

    def __init__(self, *, max_size: Optional[int] = None) -> None:
        self._lock = threading.RLock()
        self._subs: Dict[int, _Entry] = {}
        self._heap: List[_Entry] = []
        self._version = 0
        self._snapshot_cache: Optional[Tuple[int, List[_Entry]]] = None
        self._max_size = max_size
        self.audit_log: List[str] = []

    def _log(self, event: str) -> None:
        ts = time.perf_counter_ns()
        self.audit_log.append(f"{ts}:{event}")

    def _purge_heap(self) -> None:
        alive = [
            e for e in self._heap
            if e.token in self._subs and e.fn_ref() is not None
        ]
        if len(alive) != len(self._heap):
            self._heap[:] = alive
            heapq.heapify(self._heap)
            self._snapshot_cache = None
            self._version += 1

    def _snapshot(self) -> List[_Entry]:
        with self._lock:
            self._purge_heap()
            if self._snapshot_cache and self._snapshot_cache[0] == self._version:
                return list(self._snapshot_cache[1])
            ordered = heapq.nsmallest(len(self._heap), self._heap)
            self._snapshot_cache = (self._version, ordered)
            return ordered.copy()

    def _remove(self, token: int, *, log_event: bool = True) -> None:
        entry = self._subs.pop(token, None)
        if not entry:
            return
        entry.fn_ref = lambda: None
        self._version += 1
        if log_event:
            self._log(f"unsubscribe:{token}")

    def subscribe(
        self,
        fn: Callable[[Any], Any],
        *,
        priority: int = 100,
        once: bool = False,
        ttl: Optional[int] = None,
        filter: Optional[Callable[[Any], bool]] = None,
    ) -> int:
        if not callable(fn):
            raise TypeError("Subscriber must be callable")
        with self._lock:
            if self._max_size is not None and len(self._subs) >= self._max_size:
                raise OverflowError("subscriber capacity reached")
            token = next(self._token_src)
            idx = next(self._index_src)

            # methods held weakly, plain functions strongly, callable objects weakly
            if isinstance(fn, types.MethodType):
                fn_ref = weakref.WeakMethod(fn)
            elif isinstance(fn, types.FunctionType):
                fn_ref = (lambda fn=fn: fn)
            else:
                fn_ref = weakref.ref(fn)

            entry = _Entry(priority, idx, token, once, ttl, filter, fn_ref)
            self._subs[token] = entry
            heapq.heappush(self._heap, entry)
            self._version += 1
            self._log(f"subscribe:{token}")
            return token

    def unsubscribe(self, token: int) -> None:
        with self._lock:
            self._remove(token)

    def reset(self) -> None:
        with self._lock:
            if not self._subs:
                return
            self._subs.clear()
            self._heap.clear()
            self._snapshot_cache = None
            self._version += 1
            self._log("reset")

    def broadcast(self, msg: Any) -> List[Any]:
        entries = self._snapshot()
        results: List[Any] = []
        errors: List[Tuple[BaseException, TracebackType]] = []

        for entry in entries:
            fn = entry.fn_ref()
            if fn is None:
                continue
            if entry.filter and not entry.filter(msg):
                continue
            try:
                results.append(fn(msg))
            except BaseException as exc:
                errors.append((exc, exc.__traceback__))
            finally:
                with self._lock:
                    if entry.once:
                        self._remove(entry.token, log_event=True)
                    elif entry.ttl is not None:
                        entry.ttl -= 1
                        if entry.ttl <= 0:
                            self._remove(entry.token, log_event=True)

        if errors:
            raise SubscriberError(*errors)
        return results

    @contextmanager
    def temporary(self, fn: Callable[[Any], Any], **kwargs):
        token = self.subscribe(fn, **kwargs)
        try:
            yield token
        finally:
            self.unsubscribe(token)

