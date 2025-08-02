
"""Simulate an in-memory TTL cache using cachetools with virtual time."""

import cachetools
from typing import List


def ttl_cache_simulator(commands: List[str]) -> List[str]:
    """Simulate a TTL cache using cachetools.TTLCache with virtual clock."""
    virtual_time: int = 0
    outputs: List[str] = []

    def timer_func() -> int:
        return virtual_time

    # Cache with max TTL to avoid premature eviction by the cache itself
    cache = cachetools.TTLCache(maxsize=10 ** 4, ttl=86400, timer=timer_func)
    expiry_times = {}  # key -> expiry timestamp (virtual_time + ttl)

    for command_str in commands:
        parts = command_str.split()
        command = parts[0]

        if command == "EXIT":
            break

        elif command == "SET":
            key, value, ttl_str = parts[1], parts[2], parts[3]
            ttl = int(ttl_str)
            cache[key] = value
            expiry_times[key] = virtual_time + ttl  # track expiry

        elif command == "GET":
            key = parts[1]
            expiry = expiry_times.get(key)
            value = cache.get(key)

            if value is None or expiry is None or expiry <= virtual_time:
                # expired or missing
                cache.pop(key, None)
                expiry_times.pop(key, None)
                outputs.append("NULL")
            else:
                outputs.append(value)

        elif command == "SLEEP":
            seconds = int(parts[1])
            virtual_time += seconds

    return outputs

