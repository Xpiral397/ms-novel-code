"""Simulate a thread-safe distributed cache using concurrent commands."""

import threading
import queue
import re


class DistributedCache:
    """Represent a thread-safe in-memory key-value cache."""

    def __init__(self):
        """Initialize the cache and the internal lock."""
        self._cache = {}
        self._lock = threading.Lock()

    def put(self, key, value):
        """Store the key-value pair in the cache."""
        with self._lock:
            self._cache[key] = value

    def get(self, key):
        """Retrieve the value for the given key from the cache."""
        with self._lock:
            return self._cache.get(key)

    def delete(self, key):
        """Remove the key from the cache if it exists."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False


def validate_command(parts):
    """Validate the format and constraints of a command."""
    command = parts[0]

    if command == "PUT":
        if len(parts) != 3:
            return "ERROR"
        key, value = parts[1], parts[2]
        if not (1 <= len(key) <= 64 and key.isalnum()):
            return "ERROR"
        if not (0 <= len(value) <= 256 and re.match(r'^[\x20-\x7E]*$', value)):
            return "ERROR"
    elif command == "GET":
        if len(parts) != 2:
            return "ERROR"
        key = parts[1]
        if not (1 <= len(key) <= 64 and key.isalnum()):
            return "ERROR"
    elif command == "DELETE":
        if len(parts) != 2:
            return "ERROR"
        key = parts[1]
        if not (1 <= len(key) <= 64 and key.isalnum()):
            return "ERROR"
    elif command == "EXIT":
        if len(parts) != 1:
            return "ERROR"
    else:
        return "ERROR"

    return None


def process_command(cache, command, result_queue, index):
    """Execute a cache command and store its result in the result queue."""
    parts = command.split(' ', 2)

    validation_error = validate_command(parts)
    if validation_error:
        result_queue.put((index, validation_error))
        return

    op = parts[0]

    if op == "PUT":
        key, value = parts[1], parts[2]
        cache.put(key, value)
        result_queue.put((index, "STORED"))
    elif op == "GET":
        key = parts[1]
        value = cache.get(key)
        if value is not None:
            result_queue.put((index, value))
        else:
            result_queue.put((index, "NOT_FOUND"))
    elif op == "DELETE":
        key = parts[1]
        if cache.delete(key):
            result_queue.put((index, "DELETED"))
        else:
            result_queue.put((index, "NOT_FOUND"))
    elif op == "EXIT":
        result_queue.put((index, "BYE"))


def simulate_distributed_cache(commands: list[str]) -> list[str]:
    """
    Simulate a distributed cache with concurrent access using threads.

    Args:
        commands: A list of command strings to execute.

    Returns:
        A list of output strings in the same order as the input commands.
    """
    cache = DistributedCache()
    results = [None] * len(commands)
    result_queue = queue.Queue()
    threads = []
    exit_command_found = False

    for i, command in enumerate(commands):
        if exit_command_found:
            break

        thread = threading.Thread(
            target=process_command,
            args=(cache, command, result_queue, i)
        )
        threads.append(thread)
        thread.start()

        if command.strip().upper() == "EXIT":
            exit_command_found = True

    for thread in threads:
        thread.join()

    while not result_queue.empty():
        index, result = result_queue.get()
        results[index] = result

    final_results = []
    for result in results:
        if result is not None:
            final_results.append(result)
        else:
            # Stop collecting results after the EXIT command's output.
            if final_results and final_results[-1] == "BYE":
                break

    return final_results

