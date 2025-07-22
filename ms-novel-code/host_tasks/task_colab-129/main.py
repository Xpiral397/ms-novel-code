# hybrid_factorizer.py
#!/usr/bin/env python3
"""
Hybrid multi-algorithm integer factorization with blind‑spot thread recovery.

Stages:
  0) trial division
  1) Pollard’s p‑1 with fixed per‑bound timeout
  2) Pollard’s Rho (Brent variant) with heartbeat monitoring and respawn
  3) ECM fallback (stub)

Threads share:
  - stop_event for early cancel
  - result dict under result_lock
  - heartbeat dict under hb_lock
"""

import threading
import time
import math
import random
from typing import Dict, Tuple, Optional, List


def gcd(a: int, b: int) -> int:
    """Compute greatest common divisor of a and b."""
    return math.gcd(a, b)


def trial_division(N: int, limit: int) -> Optional[int]:
    """
    Trial‑divide N by integers 2..limit.
    Return a factor or None if none found ≤ limit.
    """
    r = int(math.isqrt(N))
    for p in range(2, min(limit, r) + 1):
        if N % p == 0:
            return p
    return None


def pollard_p1(
    N: int,
    B: int,
    stop_event: threading.Event,
    heartbeat: Dict[str, float],
    hb_lock: threading.Lock
) -> Optional[int]:
    """
    Pollard's p‑1: compute a = 2^{lcm(1..B)} mod N,
    check g = gcd(a−1, N). Return factor or None.
    """
    a = 2
    for j in range(2, B + 1):
        if stop_event.is_set():
            return None
        a = pow(a, j, N)
        with hb_lock:
            heartbeat[threading.current_thread().name] = time.time()
        g = gcd(a - 1, N)
        if 1 < g < N:
            return g
    return None


def pollard_rho_brent(
    N: int,
    c: int,
    stop_event: threading.Event,
    heartbeat: Dict[str, float],
    hb_lock: threading.Lock
) -> Optional[int]:
    """
    Pollard's Rho with Brent's cycle detection, deterministic start at x=2.
    f(x) = x^2 + c mod N.
    """
    x = 2
    y = x
    m = 100
    g = 1
    r = 1
    q = 1
    f = lambda v: (v * v + c) % N

    while g == 1 and not stop_event.is_set():
        x = y
        for _ in range(r):
            y = f(y)
        k = 0
        while k < r and g == 1 and not stop_event.is_set():
            for _ in range(min(m, r - k)):
                y = f(y)
                q = (q * abs(x - y)) % N
            g = gcd(q, N)
            k += m
            with hb_lock:
                heartbeat[threading.current_thread().name] = time.time()
        r <<= 1

    if g is None or g == 1 or g == N:
        return None
    return g


class PollardP1Worker(threading.Thread):
    """Thread running Pollard’s p‑1 up to bound B."""

    def __init__(
        self,
        N: int,
        B: int,
        stop_event: threading.Event,
        result: Dict[str, int],
        result_lock: threading.Lock,
        heartbeat: Dict[str, float],
        hb_lock: threading.Lock
    ) -> None:
        super().__init__(daemon=True)
        self.N = N
        self.B = B
        self.stop_event = stop_event
        self.result = result
        self.result_lock = result_lock
        self.heartbeat = heartbeat
        self.hb_lock = hb_lock

    def run(self) -> None:
        factor = pollard_p1(
            self.N, self.B,
            self.stop_event,
            self.heartbeat, self.hb_lock
        )
        if factor:
            with self.result_lock:
                if "p" not in self.result:
                    self.result["p"] = factor
                    self.result["q"] = self.N // factor
                    self.stop_event.set()


class PollardRhoWorker(threading.Thread):
    """Thread running Pollard’s Rho (Brent) with constant c."""

    def __init__(
        self,
        N: int,
        c: int,
        stop_event: threading.Event,
        result: Dict[str, int],
        result_lock: threading.Lock,
        heartbeat: Dict[str, float],
        hb_lock: threading.Lock
    ) -> None:
        super().__init__(daemon=True)
        self.N = N
        self.c = c
        self.stop_event = stop_event
        self.result = result
        self.result_lock = result_lock
        self.heartbeat = heartbeat
        self.hb_lock = hb_lock

    def run(self) -> None:
        factor = pollard_rho_brent(
            self.N, self.c,
            self.stop_event,
            self.heartbeat, self.hb_lock
        )
        if factor:
            with self.result_lock:
                if "p" not in self.result:
                    self.result["p"] = factor
                    self.result["q"] = self.N // factor
                    self.stop_event.set()


class HybridFactorizer:
    """
    Hybrid factorization pipeline:
      0) trial division
      1) Pollard p‑1 (fixed timeout per bound)
      2) Pollard Rho with blind‑spot monitoring
      3) (ECM stub)
    """

    def __init__(
        self,
        N: int,
        trial_limit: int = 1000,
        p1_bounds: Tuple[int, int] = (1000, 100_000),
        p1_timeout: float = 1.0,
        rho_workers: int = 4,
        rho_blind_timeout: float = 2.0,
        rho_timeout: float = 10.0,
        monitor_interval: float = 1.0
    ) -> None:
        self.N = N
        self.trial_limit = trial_limit
        self.p1_bounds = p1_bounds
        self.p1_timeout = p1_timeout
        self.rho_workers = rho_workers
        self.rho_blind_timeout = rho_blind_timeout
        self.rho_timeout = rho_timeout
        self.monitor_interval = monitor_interval

        self.stop_event = threading.Event()
        self.result_lock = threading.Lock()
        self.result: Dict[str, int] = {}

        self.heartbeat: Dict[str, float] = {}
        self.hb_lock = threading.Lock()

    def factor(self) -> Tuple[int, int]:
        """Return (p, q) with p*q == N, or (1, N) if no factor found."""

        # Stage 0: trial division
        if self.N <= 1:
            return (self.N, 1)
        if self.N % 2 == 0:
            return (2, self.N // 2)
        f = trial_division(self.N, self.trial_limit)
        if f:
            return (f, self.N // f)

        # Stage 1: Pollard p‑1
        for B in self.p1_bounds:
            if self.stop_event.is_set():
                break
            w = PollardP1Worker(
                self.N, B,
                self.stop_event, self.result, self.result_lock,
                self.heartbeat, self.hb_lock
            )
            with self.hb_lock:
                self.heartbeat[w.name] = time.time()
            w.start()
            w.join(self.p1_timeout)
            if self.stop_event.is_set():
                return (self.result["p"], self.result["q"])
            self.stop_event.set()
            w.join()
            self.stop_event.clear()

        # Stage 2: Pollard Rho with blind‑spot monitoring
        rho_threads: List[PollardRhoWorker] = []
        for _ in range(self.rho_workers):
            c = random.randrange(1, self.N - 1)
            w = PollardRhoWorker(
                self.N, c,
                self.stop_event, self.result, self.result_lock,
                self.heartbeat, self.hb_lock
            )
            with self.hb_lock:
                self.heartbeat[w.name] = time.time()
            rho_threads.append(w)
            w.start()

        start = time.time()
        while time.time() - start < self.rho_timeout and not self.stop_event.is_set():
            time.sleep(self.monitor_interval)
            now = time.time()
            with self.hb_lock:
                for w in list(rho_threads):
                    last = self.heartbeat.get(w.name, 0)
                    if now - last > self.rho_blind_timeout:
                        w.join(0)
                        rho_threads.remove(w)
                        if not self.stop_event.is_set():
                            c = random.randrange(1, self.N - 1)
                            nw = PollardRhoWorker(
                                self.N, c,
                                self.stop_event, self.result, self.result_lock,
                                self.heartbeat, self.hb_lock
                            )
                            self.heartbeat[nw.name] = time.time()
                            rho_threads.append(nw)
                            nw.start()

        self.stop_event.set()
        for w in rho_threads:
            w.join(0.1)

        if "p" in self.result:
            p, q = self.result["p"], self.result["q"]
            return (min(p, q), max(p, q))

        # Stage 3: ECM fallback (not implemented)
        return (1, self.N)


if __name__ == "__main__":
    N = 101 * 103
    f = HybridFactorizer(N)
    p, q = f.factor()
    print(f"Result: {p} × {q}")

