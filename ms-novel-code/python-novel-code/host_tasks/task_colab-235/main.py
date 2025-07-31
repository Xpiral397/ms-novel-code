
import threading
import heapq
import itertools
import weakref
import time
import types

from typing import Callable, Dict, List, Optional, Tuple, Protocol, runtime_checkable


@runtime_checkable
class Observer(Protocol):
    def update(self, temp: float, humidity: float, pressure: float) -> None:
        ...


class _ObserverEntry:
    __slots__ = (
        "priority", "once", "ttl", "filter_fn",
        "fn_strong", "fn_ref", "token", "index",
    )

    def __init__(
        self,
        fn_strong: Optional[Callable],
        fn_ref: Optional[weakref.ReferenceType],
        priority: int,
        once: bool,
        ttl: Optional[int],
        filter_fn: Optional[Callable[[Tuple[float, float, float]], bool]],
        token: int,
        index: int,
    ) -> None:
        self.fn_strong = fn_strong
        self.fn_ref = fn_ref
        self.priority = priority
        self.once = once
        self.ttl = ttl
        self.filter_fn = filter_fn
        self.token = token
        self.index = index

    def __lt__(self, other) -> bool:
        return (self.priority, self.index) < (other.priority, other.index)


class WeatherData:
    _token_gen = itertools.count(1)

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._observers: List[_ObserverEntry] = []
        self._paused = False
        self._metrics: Dict[int, List[float]] = {}
        self._log: List[str] = []
        self._index_gen = itertools.count()
        self._data: Tuple[float, float, float] = (0.0, 0.0, 0.0)

    @staticmethod
    def _remove_dead(_ref: weakref.ReferenceType) -> None:
        # actual removal occurs in _cleanup_dead during notify
        pass

    def subscribe(
        self,
        callback: object,
        *,
        priority: int = 100,
        once: bool = False,
        ttl: Optional[int] = None,
        filter_fn: Optional[Callable[[Tuple[float, float, float]], bool]] = None,
    ) -> int:
        if not (callable(callback) or hasattr(callback, "update")):
            raise TypeError("Observer must be callable or have update method")

        fn_strong = None
        fn_ref = None
        if isinstance(callback, types.FunctionType):
            fn_strong = callback
        elif isinstance(callback, types.MethodType):
            fn_ref = weakref.WeakMethod(callback)
        elif hasattr(callback, "update"):
            fn_ref = weakref.ref(callback)
        else:
            fn_strong = callback

        token = next(WeatherData._token_gen)
        idx = next(self._index_gen)
        entry = _ObserverEntry(
            fn_strong, fn_ref, priority, once, ttl, filter_fn, token, idx
        )
        with self._lock:
            heapq.heappush(self._observers, entry)
            self._metrics[token] = []
            self._log.append(f"{time.perf_counter_ns()}:subscribe:{token}")
        return token

    def unsubscribe(self, token: int) -> None:
        with self._lock:
            before = len(self._observers)
            self._observers = [
                e for e in self._observers if e.token != token
            ]
            if len(self._observers) != before:
                heapq.heapify(self._observers)
                self._metrics.pop(token, None)
                self._log.append(f"{time.perf_counter_ns()}:unsubscribe:{token}")

    def pause(self) -> None:
        with self._lock:
            self._paused = True
            self._log.append(f"{time.perf_counter_ns()}:pause")

    def resume(self) -> None:
        with self._lock:
            self._paused = False
            self._log.append(f"{time.perf_counter_ns()}:resume")

    def set_measurements(self, temp: float, humidity: float, pressure: float) -> None:
        with self._lock:
            self._data = (temp, humidity, pressure)
            self._log.append(
                f"{time.perf_counter_ns()}:set:{temp},{humidity},{pressure}"
            )
        self._notify()

    def _cleanup_dead(self) -> None:
        alive: List[_ObserverEntry] = []
        for e in self._observers:
            fn = (
                e.fn_strong
                if e.fn_strong is not None
                else e.fn_ref() if e.fn_ref is not None
                else None
            )
            if fn is None:
                self._log.append(f"{time.perf_counter_ns()}:dead:{e.token}")
                self._metrics.pop(e.token, None)
            else:
                alive.append(e)
        if len(alive) != len(self._observers):
            self._observers = alive
            heapq.heapify(self._observers)

    def _notify(self) -> None:
        with self._lock:
            if self._paused:
                return
            self._cleanup_dead()
            snapshot = list(self._observers)

        snapshot.sort()
        temp, hum, pres = self._data

        for entry in snapshot:
            fn = (
                entry.fn_strong
                if entry.fn_strong is not None
                else entry.fn_ref() if entry.fn_ref is not None
                else None
            )
            if fn is None:
                continue

            call_fn = fn.update if hasattr(fn, "update") else fn
            if entry.filter_fn and not entry.filter_fn((temp, hum, pres)):
                continue

            start_ns = time.perf_counter_ns()
            try:
                call_fn(temp, hum, pres)
            except Exception as exc:
                self._log.append(
                    f"{time.perf_counter_ns()}:error:{entry.token}:{exc}"
                )
            end_ns = time.perf_counter_ns()
            duration = (end_ns - start_ns) / 1e9

            with self._lock:
                self._metrics.setdefault(entry.token, []).append(duration)
                self._log.append(
                    f"{time.perf_counter_ns()}:notify:"
                    f"{entry.token}:{duration}"
                )
                if entry.once:
                    self.unsubscribe(entry.token)
                elif entry.ttl is not None:
                    entry.ttl -= 1
                    if entry.ttl <= 0:
                        self.unsubscribe(entry.token)

    def get_metrics(self) -> Dict[int, float]:
        with self._lock:
            return {
                tok: sum(v) / len(v)
                for tok, v in self._metrics.items()
                if v
            }

    def get_log(self) -> List[str]:
        with self._lock:
            return list(self._log)

