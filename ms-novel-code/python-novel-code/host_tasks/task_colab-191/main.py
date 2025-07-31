
import threading
from typing import Any, Dict, Optional


class Config:
    """Thread-safe Singleton configuration with layered overrides."""

    _instance: Optional["Config"] = None
    _lock = threading.RLock()

    def __init__(self, input_json: Dict[str, Any]) -> None:
        """
        Build configuration by merging defaults, JSON, env vars, and CLI overrides.

        Args:
            input_json: Dict with keys "defaults", "config_json",
                        "env_vars", and "cli_overrides".
        """
        self._defaults = input_json.get("defaults", {})
        self._json_data = input_json.get("config_json", {})
        self._raw_env = input_json.get("env_vars", {})
        self._raw_cli = input_json.get("cli_overrides", {})

        # Parse nested structures from flat env and CLI
        self._env_layer = self._parse_nested(self._raw_env)
        self._cli_layer = self._parse_nested(self._raw_cli)

        # Initial merge under lock
        with self._lock:
            self._rebuild_config()

    @classmethod
    def get_instance(cls, input_json: Dict[str, Any]) -> "Config":
        """
        Return the singleton instance, creating it on first call.

        Args:
            input_json: Same dict passed on first invocation.
        """
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(input_json)
        return cls._instance

    def _deep_merge(self, dest: Dict[str, Any],
                    src: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively merge src into dest and return dest.

        Args:
            dest: Destination dict to be updated.
            src: Source dict whose values override dest.
        """
        for key, value in src.items():
            if (
                key in dest
                and isinstance(dest[key], dict)
                and isinstance(value, dict)
            ):
                dest[key] = self._deep_merge(dest[key], value)
            else:
                dest[key] = value
        return dest

    def _parse_nested(self, flat: Dict[str, Any]) -> Dict[str, Any]:
        """
        Expand keys containing '__' into nested dicts.

        Example: {'a__b': 1} -> {'a': {'b': 1}}
        """
        result: Dict[str, Any] = {}
        for flat_key, val in flat.items():
            parts = flat_key.split("__")
            node = result
            for part in parts[:-1]:
                node = node.setdefault(part, {})
            node[parts[-1]] = val
        return result

    def _rebuild_config(self) -> None:
        """
        Merge all layers into the internal _config dict.
        Called under _lock.
        """
        cfg = {}
        self._deep_merge(cfg, self._defaults)
        self._deep_merge(cfg, self._json_data)
        self._deep_merge(cfg, self._env_layer)
        self._deep_merge(cfg, self._cli_layer)
        self._config = cfg

    def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieve a value by dot-notation key.

        Args:
            key: e.g. "section.sub.key"
            default: returned if key is missing
        """
        node = self._config
        for part in key.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def get_int(self, key: str, default: Optional[int] = None
                ) -> Optional[int]:
        """
        Retrieve an integer, casting floats or numeric strings.

        Returns default on failure.
        """
        val = self.get(key, default)
        if isinstance(val, (int, float)):
            return int(val)
        try:
            return int(val)  # type: ignore
        except Exception:
            return default

    def get_bool(self, key: str, default: Optional[bool] = None
                 ) -> Optional[bool]:
        """
        Retrieve a boolean. Accepts True/False or "true"/"false" strings.

        Returns default on failure.
        """
        val = self.get(key, default)
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            low = val.lower()
            if low in ("true", "false"):
                return low == "true"
        return default

    def reload(self) -> None:
        """
        Re-apply config_json and env_vars under lock, preserving CLI overrides.
        """
        with self._lock:
            self._json_data = self._json_data.copy()
            self._env_layer = self._parse_nested(self._raw_env)
            self._rebuild_config()


