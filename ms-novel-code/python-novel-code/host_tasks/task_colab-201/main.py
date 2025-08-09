"""This module implements a HashTable with collision resolution.

using chaining or linear probing.
"""
from typing import Any


class HashTable:
    """HashTable DS with support for chaining and linear probing."""

    def __init__(
        self,
        collision_resolution: str = 'chaining',
        initial_capacity: int = 8,
        load_factor_threshold: float = 0.75
    ):
        """Initialize the HashTable with specified parameters."""
        if collision_resolution not in (
            'chaining', 'linear_probing'
                ):
            raise ValueError(
                "Collision resolution must be 'chaining' or 'linear_probing'"
                )

        if not isinstance(initial_capacity, int) or initial_capacity <= 0:
            raise ValueError("Initial capacity must be a positive integer")

        if not (0 < load_factor_threshold < 1):
            raise ValueError(
                "Load factor threshold must be a float "
                "between 0 and 1 (exclusive)"
                )

        self.collision_resolution = collision_resolution
        self.initial_capacity = initial_capacity
        self.capacity = initial_capacity
        self.load_factor_threshold = load_factor_threshold
        self.size = 0
        self._deleted_sentinel = object()
        self._deleted_count = 0

        if self.collision_resolution == 'chaining':
            self._table = [[] for _ in range(self.capacity)]
        else:
            self._table = [None] * self.capacity

    def put(self, key: str, value: Any) -> None:
        """Insert a key-value pair into the hash table."""
        if not isinstance(key, str) or not key:
            raise TypeError("Key must be a non-empty string")

        if self.collision_resolution == 'chaining':
            self._put_chaining(key, value)
        else:
            self._put_linear_probing(key, value)

        # Calculate current load factor
        cl = self.size / self.capacity
        current_load = (self.size + self._deleted_count) / self.capacity if \
            self.collision_resolution == 'linear_probing' else cl

        if current_load > self.load_factor_threshold:
            self._resize()

    def get(self, key: str) -> Any:
        """Retrieve a value by its key from the hash table."""
        if not isinstance(key, str) or not key:
            raise TypeError("Key must be a non-empty string")

        if self.collision_resolution == 'chaining':
            return self._get_chaining(key)
        return self._get_linear_probing(key)

    def remove(self, key: str) -> None:
        """Remove a key-value pair from the hash table."""
        if not isinstance(key, str) or not key:
            raise TypeError("Key must be a non-empty string")

        if self.collision_resolution == 'chaining':
            self._remove_chaining(key)
        else:
            self._remove_linear_probing(key)

    def _hash(self, key: str) -> int:
        """Compute the hash index for a given key."""
        return hash(key) % self.capacity

    def _put_chaining(self, key: str, value: Any) -> None:
        """Insert a key-value pair using chaining."""
        index = self._hash(key)
        bucket = self._table[index]

        for existing_key, _ in bucket:
            if existing_key == key:
                raise KeyError(f"Key '{key}' already exists")

        bucket.append((key, value))
        self.size += 1

    def _get_chaining(self, key: str) -> Any:
        """Retrieve a value using chaining."""
        index = self._hash(key)
        bucket = self._table[index]

        for existing_key, val in bucket:
            if existing_key == key:
                return val
        raise KeyError(f"Key '{key}' not found")

    def _remove_chaining(self, key: str) -> None:
        """Remove a key-value pair using chaining."""
        index = self._hash(key)
        bucket = self._table[index]

        for i, (existing_key, _) in enumerate(bucket):
            if existing_key == key:
                del bucket[i]
                self.size -= 1
                return
        raise KeyError(f"Key '{key}' not found")

    def _put_linear_probing(self, key: str, value: Any) -> None:
        """Insert a key-value pair using linear probing."""
        index = self._hash(key)
        first_deleted = None

        for _ in range(self.capacity):
            entry = self._table[index]

            if entry is None:
                if first_deleted is not None:
                    self._table[first_deleted] = (key, value)
                    self._deleted_count -= 1
                else:
                    self._table[index] = (key, value)
                self.size += 1
                return
            elif entry is self._deleted_sentinel:
                if first_deleted is None:
                    first_deleted = index
                index = (index + 1) % self.capacity
            else:
                existing_key, _ = entry
                if existing_key == key:
                    raise KeyError(f"Key '{key}' already exists")
                index = (index + 1) % self.capacity

        if first_deleted is not None:
            self._table[first_deleted] = (key, value)
            self._deleted_count -= 1
            self.size += 1
            return

        raise RuntimeError("Hash table is full")

    def _get_linear_probing(self, key: str) -> Any:
        """Retrieve a value using linear probing."""
        index = self._hash(key)

        for _ in range(self.capacity):
            entry = self._table[index]
            if entry is None:
                break
            elif entry is not self._deleted_sentinel:
                existing_key, val = entry
                if existing_key == key:
                    return val
            index = (index + 1) % self.capacity

        raise KeyError(f"Key '{key}' not found")

    def _remove_linear_probing(self, key: str) -> None:
        """Remove a key-value pair using linear probing."""
        index = self._hash(key)

        for _ in range(self.capacity):
            entry = self._table[index]
            if entry is None:
                break
            elif entry is not self._deleted_sentinel:
                existing_key, _ = entry
                if existing_key == key:
                    self._table[index] = self._deleted_sentinel
                    self.size -= 1
                    self._deleted_count += 1
                    return
            index = (index + 1) % self.capacity

        raise KeyError(f"Key '{key}' not found")

    def _resize(self) -> None:
        """Resize the hashtable when the load factor threshold is exceeded."""
        new_capacity = self.capacity * 2
        old_table = self._table

        if self.collision_resolution == 'chaining':
            self._table = [[] for _ in range(new_capacity)]
        else:
            self._table = [None] * new_capacity
            self._deleted_count = 0

        old_size = self.size
        self.size = 0
        self.capacity = new_capacity

        if self.collision_resolution == 'chaining':
            for bucket in old_table:
                for key, value in bucket:
                    self._put_chaining(key, value)
        else:
            for entry in old_table:
                if entry is not None and entry is not self._deleted_sentinel:
                    key, value = entry
                    self._put_linear_probing(key, value)

        self.size = old_size

