"""
Minimal SOA sample used by the test-suite.

• ArithmeticService & StatsService – API-key auth
• ConfigHolder – in-memory, thread-safe
• ServiceRegistry – registers services + 30 s heartbeat
• ServiceProxy – retry, back-off, NS fallback, async metrics
"""

from __future__ import annotations

import logging
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

import Pyro4

# ────────── Exceptions ──────────────────────────────────────────
class AuthenticationError(Exception):
    """Raised when an invalid API key is supplied."""


class ServiceError(Exception):
    """Wraps remote/network exceptions with extra context."""

    def __init__(self, msg: str, svc: str, ver: str, mth: str, code: str, tb: str = ""):
        super().__init__(msg)
        self.service, self.version, self.method, self.code = svc, ver, mth, code
        self.traceback = tb


# ────────── Services ────────────────────────────────────────────
@Pyro4.expose
class ArithmeticService:
    """Simple arithmetic RPCs secured by API key."""

    def __init__(self, api_key: str, logger: Optional[logging.Logger] = None):
        self._key = api_key
        self._log = logger or logging.getLogger("arith")

    def _check(self, key: str):
        if key != self._key:
            raise AuthenticationError("invalid key")

    def add(self, a, b, api_key):       self._check(api_key); return a + b
    def subtract(self, a, b, api_key):  self._check(api_key); return a - b
    def multiply(self, a, b, api_key):  self._check(api_key); return a * b

    def divide(self, a, b, api_key):
        self._check(api_key)
        if b == 0:
            raise ZeroDivisionError("division by zero")
        return a / b


@Pyro4.expose
class StatsService:
    """Collects call metrics."""

    def __init__(self, api_key: str, logger: Optional[logging.Logger] = None):
        self._key = api_key
        self._log = logger or logging.getLogger("stats")
        self.calls: List[tuple] = []

    def _check(self, key: str):
        if key != self._key:
            raise AuthenticationError("invalid key")

    def record_call(self, svc, ver, mth, dur, api_key):
        self._check(api_key)
        self.calls.append((svc, ver, mth, dur))


# ────────── Config holder (pure in-memory) ───────────────────────
class ConfigHolder:
    """Thread-safe dict with minimal defaults (no file I/O)."""

    def __init__(self, data: Optional[Dict[str, Any]] = None):
        self._lock = threading.RLock()
        self._data = data or {
            "auth": {"api_key": "dummy"},
            "name_servers": [],
            "services": {},
            "client": {"retry_count": 0, "timeout_seconds": 1, "backoff_factor": 0},
        }

    def get(self) -> Dict[str, Any]:
        with self._lock:
            return self._data.copy()

    def set(self, new_data: Dict[str, Any]):
        with self._lock:
            self._data = new_data.copy()


# ────────── Service registry & heartbeat ─────────────────────────
class ServiceRegistry:
    """Registers services and re-registers every 30 s."""

    def __init__(self, cfg: ConfigHolder):
        self.cfg = cfg
        self.d = Pyro4.Daemon(host="127.0.0.1")
        self.reg: List[tuple[str, Any]] = []
        self._register_all()
        threading.Thread(target=self._heartbeat, daemon=True).start()

    # internal helpers ------------------------------------------------
    def _ns(self):
        for addr in self.cfg.get().get("name_servers", []):
            host, port = addr.split(":")
            try:
                return Pyro4.locateNS(host=host, port=int(port))
            except Pyro4.errors.PyroError:
                pass
        return None

    def _register(self, name: str, obj: Any):
        uri = self.d.register(obj)
        ns = self._ns()
        if ns:
            ns.register(name, uri)
        self.reg.append((name, obj))

    def _register_all(self):
        key = self.cfg.get()["auth"]["api_key"]
        self._register("arithmetic.service.v1_0", ArithmeticService(key))
        self._register("stats.service.v1_0", StatsService(key))

    def _heartbeat(self):
        while True:
            time.sleep(30)
            ns = self._ns()
            if not ns:
                continue
            for name, obj in self.reg:
                ns.register(name, self.d.register(obj))


# ────────── Client proxy ─────────────────────────────────────────
class ServiceProxy:
    """Retry, back-off, NS fallback, async metrics."""

    def __init__(self, cfg: Dict[str, Any]):
        self.cfg, self.key = cfg, cfg["auth"]["api_key"]
        cl = cfg["client"]
        self.retries, self.back, self.timeout = cl["retry_count"], cl["backoff_factor"], cl["timeout_seconds"]
        self.pool = ThreadPoolExecutor(2)

    # helpers --------------------------------------------------------
    def _ns(self):
        for addr in self.cfg["name_servers"]:
            h, p = addr.split(":")
            try:
                return Pyro4.locateNS(host=h, port=int(p))
            except Pyro4.errors.PyroError:
                pass
        return None

    def _px(self, svc: str, ver: str):
        name = f"{svc}.service.v{ver}"
        ns = self._ns()
        uri = ns.lookup(name) if ns else self.cfg["services"][svc]["direct_uris"][ver][0]
        p = Pyro4.Proxy(uri)
        p._pyroTimeout = self.timeout
        return p

    # public call ----------------------------------------------------
    def call(self, svc, ver, mth, args, kw=None):
        kw = dict(kw or {}, api_key=self.key)
        for i in range(self.retries + 1):
            try:
                p = self._px(svc, ver)
                t0 = time.time()
                res = getattr(p, mth)(*args, **kw)
                dur = (time.time() - t0) * 1000
                self.pool.submit(self._metric, svc, ver, mth, dur)
                return {"result": res, "duration_ms": dur}
            except (ZeroDivisionError, Pyro4.errors.PyroError) as exc:
                if i == self.retries:
                    raise ServiceError(str(exc), svc, ver, mth, exc.__class__.__name__, traceback.format_exc())
                time.sleep(self.back * (2 ** i))

    def _metric(self, svc, ver, mth, dur):
        try:
            self._px("stats", "1_0").record_call(svc, ver, mth, dur, self.key)
        except Exception:
            pass

