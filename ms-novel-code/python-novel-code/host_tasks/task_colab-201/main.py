
# main.py
import argparse
import json
import logging
import signal
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List

import Pyro4


# Exceptions
class AuthenticationError(Exception):
    """Raised when an invalid API key is presented."""


class ServiceError(Exception):
    """Wraps remote or network errors with metadata."""

    def __init__(self, message: str, service: str, version: str,
                 method: str, code: str, tb: str = ""):
        super().__init__(message)
        self.service = service
        self.version = version
        self.method = method
        self.code = code
        self.traceback = tb


# Services
@Pyro4.expose
class ArithmeticService:
    """Remote arithmetic operations with API key auth."""

    def __init__(self, api_key: str, logger: logging.Logger):
        self._api_key = api_key
        self._log = logger

    def _auth(self, key: str):
        if key != self._api_key:
            self._log.warning("Auth failed for ArithmeticService")
            raise AuthenticationError("Invalid API key.")
        self._log.info("Auth success for ArithmeticService")

    def add(self, a: float, b: float, api_key: str) -> float:
        self._auth(api_key)
        self._log.info(f"add({a}, {b})")
        return a + b

    def subtract(self, a: float, b: float, api_key: str) -> float:
        self._auth(api_key)
        self._log.info(f"subtract({a}, {b})")
        return a - b

    def multiply(self, a: float, b: float, api_key: str) -> float:
        self._auth(api_key)
        self._log.info(f"multiply({a}, {b})")
        return a * b

    def divide(self, a: float, b: float, api_key: str) -> float:
        self._auth(api_key)
        self._log.info(f"divide({a}, {b})")
        if b == 0:
            self._log.error("Division by zero")
            raise ZeroDivisionError("Division by zero.")
        return a / b


@Pyro4.expose
class StatsService:
    """Remote metrics aggregation with API key auth."""

    def __init__(self, api_key: str, logger: logging.Logger):
        self._api_key = api_key
        self._log = logger
        self._calls: List[tuple] = []

    def _auth(self, key: str):
        if key != self._api_key:
            self._log.warning("Auth failed for StatsService")
            raise AuthenticationError("Invalid API key.")
        self._log.info("Auth success for StatsService")

    def record_call(self, service: str, version: str, method: str,
                    duration_ms: float, api_key: str) -> None:
        self._auth(api_key)
        self._log.info(f"record_call {service} {version} {method} {duration_ms}")
        self._calls.append((service, version, method, duration_ms))


# Server and Proxy share config
class ConfigHolder:
    """Holds dynamic config and allows reload on SIGHUP."""

    def __init__(self, path: str):
        self._path = path
        self._lock = threading.RLock()
        self._data: Dict[str, Any] = {}
        self.reload()

    def get(self) -> Dict[str, Any]:
        with self._lock:
            return self._data.copy()

    def reload(self, *args):
        with self._lock:
            with open(self._path) as f:
                self._data = json.load(f)
            logging.getLogger().info("Config reloaded")


class ServiceRegistry:
    """Manages service registration and heartbeat."""

    def __init__(self, config: ConfigHolder):
        self.config = config
        self._daemon = Pyro4.Daemon()
        self._ns_lock = threading.Lock()
        self._registered: List[tuple] = []
        self._setup_logging()
        self._register_all()
        signal.signal(signal.SIGHUP, self._on_reload)
        threading.Thread(target=self._heartbeat, daemon=True).start()
        self._daemon.requestLoop()

    def _setup_logging(self):
        cfg = self.config.get()["logging"]
        log = logging.getLogger("SOA")
        handler = logging.handlers.RotatingFileHandler(
            cfg["path"] + "soa.log",
            maxBytes=cfg["rotate_every_mb"] * 1_048_576,
            backupCount=5
        )
        fmt = "%(asctime)s %(levelname)s %(message)s"
        handler.setFormatter(logging.Formatter(fmt))
        log.addHandler(handler)
        log.setLevel(getattr(logging, cfg["level"].upper(), logging.INFO))
        self._log = log

    def _locate_ns(self):
        cfg = self.config.get()
        for addr in cfg["name_servers"]:
            host, port = addr.split(":")
            try:
                return Pyro4.locateNS(host=host, port=int(port))
            except Pyro4.errors.PyroError:
                self._log.warning(f"Name server at {addr} down")
        return None

    def _register(self, name: str, obj: Any):
        uri = self._daemon.register(obj)
        ns = self._locate_ns()
        if ns:
            ns.register(name, uri)
            self._registered.append((name, obj))
            self._log.info(f"Registered {name}")
        else:
            self._log.error("No name server; cannot register")

    def _register_all(self):
        cfg = self.config.get()
        api = cfg["auth"]["api_key"]
        self._register("arithmetic.service.v1_0",
                       ArithmeticService(api, self._log))
        self._register("arithmetic.service.v2_0",
                       ArithmeticService(api, self._log))
        self._register("stats.service.v1_0",
                       StatsService(api, self._log))

    def _heartbeat(self):
        while True:
            time.sleep(30)
            self._log.info("Heartbeat re-registering services")
            ns = self._locate_ns()
            if ns:
                for name, obj in self._registered:
                    uri = self._daemon.register(obj)
                    ns.register(name, uri)

    def _on_reload(self, signum, frame):
        self._log.info("SIGHUP received: reloading config and re-registering")
        self.config.reload()
        self._register_all()


class ServiceProxy:
    """Client proxy with retry, fallback, timeout, metrics & error wrapping."""

    def __init__(self, config: Dict[str, Any]):
        self._cfg = config
        self._api = config["auth"]["api_key"]
        self._retries = config["client"]["retry_count"]
        self._timeout = config["client"]["timeout_seconds"]
        self._backoff = config["client"]["backoff_factor"]
        self._executor = ThreadPoolExecutor(max_workers=2)
        self._setup_logging()

    def _setup_logging(self):
        cfg = self._cfg["logging"]
        log = logging.getLogger("ServiceProxy")
        handler = logging.handlers.RotatingFileHandler(
            cfg["path"] + "proxy.log",
            maxBytes=cfg["rotate_every_mb"] * 1_048_576,
            backupCount=5
        )
        fmt = "%(asctime)s %(levelname)s %(message)s"
        handler.setFormatter(logging.Formatter(fmt))
        log.addHandler(handler)
        log.setLevel(getattr(logging, cfg["level"].upper(), logging.INFO))
        self._log = log

    def _locate_ns(self):
        for addr in self._cfg["name_servers"]:
            host, port = addr.split(":")
            try:
                return Pyro4.locateNS(host=host, port=int(port))
            except Pyro4.errors.PyroError:
                self._log.warning(f"Name server {addr} down")
        return None

    def _get_proxy(self, service: str, version: str):
        key = f"{service}.service.v{version.replace('.', '_')}"
        ns = self._locate_ns()
        if ns:
            uri = ns.lookup(key)
        else:
            uri = self._cfg["services"][service]["direct_uris"][version][0]
            self._log.info(f"Using direct URI for {key}")
        proxy = Pyro4.Proxy(uri)
        proxy._pyroTimeout = self._timeout
        return proxy

    def call(self, service: str, version: str, method: str,
             args: List[Any], kwargs: Dict[str, Any] = None) -> Dict[str, Any]:
        kwargs = kwargs.copy() if kwargs else {}
        kwargs["api_key"] = self._api
        attempt = 0
        while attempt <= self._retries:
            try:
                p = self._get_proxy(service, version)
                start = time.time()
                res = getattr(p, method)(*args, **kwargs)
                duration = (time.time() - start) * 1000
                self._executor.submit(self._send_metric,
                                      service, version, method, duration)
                return {"result": res, "service": service,
                        "version": version, "duration_ms": duration}
            except (ZeroDivisionError, Pyro4.errors.PyroError) as e:
                if attempt == self._retries:
                    tb = traceback.format_exc()
                    code = e.__class__.__name__
                    raise ServiceError(str(e), service, version,
                                       method, code, tb) from e
                back = self._backoff * (2 ** attempt)
                self._log.info(f"Retry {attempt} after {back}s")
                time.sleep(back)
                attempt += 1

    def _send_metric(self, service, version, method, duration):
        try:
            p = self._get_proxy("stats", "1_0")
            p.record_call(service, version, method, duration, self._api)
        except Exception as e:
            self._log.warning(f"Metrics failed: {e}")


# Entry points
def run_server(config_path: str):
    cfg = ConfigHolder(config_path)
    ServiceRegistry(cfg)


def run_client(config_path: str):
    with open(config_path) as f:
        cfg = json.load(f)
    proxy = ServiceProxy(cfg)
    # Example calls
    print(proxy.call("arithmetic", "1_0", "add", [5, 7]))
    try:
        proxy.call("arithmetic", "1_0", "divide", [5, 0])
    except ServiceError as e:
        print("Caught:", e)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--mode", choices=("server", "client"), required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    if args.mode == "server":
        run_server(args.config)
    else:
        run_client(args.config)


