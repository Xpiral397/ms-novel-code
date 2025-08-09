# tests
"""Test suite for the HashTable class."""
import unittest
from main import HashTable


class TestHashTable(unittest.TestCase):
    """Unit tests for HashTable."""

    def setUp(self):
        """Prepare hash tables for tests."""
        self.chaining_ht = HashTable(
            collision_resolution="chaining"
        )
        self.linear_ht = HashTable(
            collision_resolution="linear_probing"
        )

    def test_initialization_default(self):
        """Test default initialization."""
        ht = HashTable()
        self.assertEqual(ht.collision_resolution, "chaining")
        self.assertEqual(ht.capacity, 8)
        self.assertEqual(ht.load_factor_threshold, 0.75)

    def test_initialization_custom(self):
        """Test custom initialization."""
        ht = HashTable(
            collision_resolution="linear_probing",
            initial_capacity=16,
            load_factor_threshold=0.6
        )
        self.assertEqual(ht.collision_resolution, "linear_probing")
        self.assertEqual(ht.capacity, 16)
        self.assertEqual(ht.load_factor_threshold, 0.6)

    def test_invalid_collision_resolution(self):
        """Test invalid collision resolution."""
        with self.assertRaises(ValueError) as context:
            HashTable(collision_resolution="invalid_method")
        self.assertEqual(
            str(context.exception),
            "Collision resolution must be 'chaining' or 'linear_probing'"
        )

    def test_invalid_initial_capacity(self):
        """Test invalid initial capacity."""
        with self.assertRaises(ValueError) as context:
            HashTable(initial_capacity=0)
        self.assertEqual(
            str(context.exception),
            "Initial capacity must be a positive integer"
        )

    def test_invalid_load_factor_threshold(self):
        """Test invalid load factor threshold."""
        with self.assertRaises(ValueError) as context:
            HashTable(load_factor_threshold=1.5)
        self.assertEqual(
            str(context.exception),
            "Load factor threshold must be a float "
            "between 0 and 1 (exclusive)"
        )

    def test_put_and_get_chaining(self):
        """Test put and get with chaining."""
        self.chaining_ht.put("apple", 10)
        self.assertEqual(self.chaining_ht.get("apple"), 10)

    def test_put_and_get_linear_probing(self):
        """Test put and get with linear probing."""
        self.linear_ht.put("banana", 20)
        self.assertEqual(self.linear_ht.get("banana"), 20)

    def test_put_duplicate_key(self):
        """Test put with duplicate key."""
        self.chaining_ht.put("apple", 10)
        with self.assertRaises(KeyError) as context:
            self.chaining_ht.put("apple", 20)
        self.assertTrue(
            "Key 'apple' already exists" in str(context.exception)
        )

    def test_put_invalid_key(self):
        """Test put with invalid key."""
        with self.assertRaises(TypeError) as context:
            self.chaining_ht.put(123, "value")
        self.assertEqual(
            str(context.exception),
            "Key must be a non-empty string"
        )

    def test_get_nonexistent_key(self):
        """Test get with nonexistent key."""
        with self.assertRaises(KeyError) as context:
            self.chaining_ht.get("nonexistent")
        self.assertTrue(
            "Key 'nonexistent' not found" in str(context.exception)
        )

    def test_remove_key_chaining(self):
        """Test remove key with chaining."""
        self.chaining_ht.put("apple", 10)
        self.chaining_ht.remove("apple")
        with self.assertRaises(KeyError):
            self.chaining_ht.get("apple")

    def test_remove_key_linear_probing(self):
        """Test remove key with linear probing."""
        self.linear_ht.put("banana", 20)
        self.linear_ht.remove("banana")
        with self.assertRaises(KeyError):
            self.linear_ht.get("banana")

    def test_remove_nonexistent_key(self):
        """Test remove nonexistent key."""
        with self.assertRaises(KeyError) as context:
            self.chaining_ht.remove("nonexistent")
        self.assertTrue(
            "Key 'nonexistent' not found" in str(context.exception)
        )

    def test_resize_chaining(self):
        """Test resizing with chaining."""
        ht = HashTable(
            collision_resolution="chaining",
            initial_capacity=4,
            load_factor_threshold=0.6
        )
        ht.put("a", 1)
        ht.put("b", 2)
        ht.put("c", 3)
        self.assertGreater(ht.capacity, 4)

    def test_resize_linear_probing(self):
        """Test resizing with linear probing."""
        ht = HashTable(
            collision_resolution="linear_probing",
            initial_capacity=4,
            load_factor_threshold=0.6
        )
        ht.put("a", 1)
        ht.put("b", 2)
        ht.put("c", 3)
        self.assertGreater(ht.capacity, 4)

    def test_collision_chaining(self):
        """Test collision handling with chaining."""
        ht = HashTable(
            collision_resolution="chaining",
            initial_capacity=1
        )
        ht.put("a", 1)
        ht.put("b", 2)
        self.assertEqual(ht.get("a"), 1)
        self.assertEqual(ht.get("b"), 2)

    def test_collision_linear_probing(self):
        """Test collision handling with linear probing."""
        ht = HashTable(
            collision_resolution="linear_probing",
            initial_capacity=2
        )
        ht.put("a", 1)
        ht.put("b", 2)
        ht.put("c", 3)
        self.assertEqual(ht.get("a"), 1)
        self.assertEqual(ht.get("b"), 2)
        self.assertEqual(ht.get("c"), 3)

    def test_rehashing_chaining(self):
        """Test rehashing after resize with chaining."""
        ht = HashTable(
            collision_resolution="chaining",
            initial_capacity=2
        )
        ht.put("a", 1)
        ht.put("b", 2)
        ht.put("c", 3)
        self.assertEqual(ht.get("a"), 1)
        self.assertEqual(ht.get("b"), 2)
        self.assertEqual(ht.get("c"), 3)

    def test_rehashing_linear_probing(self):
        """Test rehashing after resize with linear probing."""
        ht = HashTable(
            collision_resolution="linear_probing",
            initial_capacity=2
        )
        ht.put("a", 1)
        ht.put("b", 2)
        ht.put("c", 3)
        self.assertEqual(ht.get("a"), 1)
        self.assertEqual(ht.get("b"), 2)
        self.assertEqual(ht.get("c"), 3)

    def test_empty_key(self):
        """Test put with empty key."""
        with self.assertRaises(TypeError) as context:
            self.chaining_ht.put("", "value")
        self.assertEqual(
            str(context.exception),
            "Key must be a non-empty string"
        )

    def test_reinsert_after_deletion_linear_probing(self):
        """Test reinsert after deletion with linear probing."""
        ht = HashTable(
            collision_resolution="linear_probing"
        )
        ht.put("apple", 10)
        ht.remove("apple")
        ht.put("apple", 20)
        self.assertEqual(ht.get("apple"), 20)

    def test_load_factor_calculation_with_deletions(self):
        """Test load factor calculation with deletions."""
        ht = HashTable(
            collision_resolution="linear_probing",
            initial_capacity=4,
            load_factor_threshold=0.6
        )
        ht.put("a", 1)
        ht.put("b", 2)
        ht.remove("a")
        ht.put("c", 3)
        self.assertGreater(ht.capacity, 4)
