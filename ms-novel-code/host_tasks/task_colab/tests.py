# tests

"""Unit tests for the `execute_batch` rollback-safe executor."""
import unittest
from copy import deepcopy
from main import execute_batch   # assumes function lives in main.py


class TestExecuteBatch(unittest.TestCase):
    # 1. all operations succeed
    def test_success_simple_flow(self):
        init = {1: "alice"}
        ops = ["INSERT 2 bob", "UPDATE 1 alicia", "DELETE 2"]
        expected = {1: "alicia"}
        self.assertEqual(execute_batch(init, ops), expected)

    # 2. duplicate insert triggers rollback
    def test_insert_duplicate_id_rollback(self):
        init = {1: "alice"}
        ops = ["INSERT 1 bob"]
        self.assertEqual(execute_batch(init, ops), init)

    # 3. explicit FAIL rolls back
    def test_explicit_fail(self):
        init = {1: "alice"}
        ops = ["INSERT 2 bob", "FAIL", "DELETE 2"]
        self.assertEqual(execute_batch(init, ops), init)

    # 4. update missing id rolls back
    def test_update_missing_id(self):
        init = {}
        ops = ["UPDATE 1 alice"]
        self.assertEqual(execute_batch(init, ops), init)

    # 5. delete missing id rolls back
    def test_delete_missing_id(self):
        init = {1: "alice"}
        ops = ["DELETE 2"]
        self.assertEqual(execute_batch(init, ops), init)

    # 6. empty operation list returns untouched copy
    def test_empty_operations_returns_copy(self):
        init = {1: "alice"}
        result = execute_batch(init, [])
        self.assertEqual(result, init)
        self.assertIsNot(result, init)  # ensure deep copy

    # 7. insert then delete same id succeeds
    def test_insert_then_delete_same_id(self):
        init = {}
        ops = ["INSERT 1 alice", "DELETE 1"]
        self.assertEqual(execute_batch(init, ops), {})

    # 8. first command FAIL
    def test_first_command_fail(self):
        init = {1: "alice"}
        ops = ["FAIL", "UPDATE 1 alicia"]
        self.assertEqual(execute_batch(init, ops), init)

    # 9. unknown command triggers rollback
    def test_unknown_command(self):
        init = {}
        ops = ["UPSERT 1 alice"]
        self.assertEqual(execute_batch(init, ops), init)

    # 10. malformed operation string triggers rollback
    def test_malformed_insert_lacks_name(self):
        init = {}
        ops = ["INSERT 1"]
        self.assertEqual(execute_batch(init, ops), init)

    # 11. deep copy on success (mutating result doesn't alter original)
    def test_deep_copy_on_success(self):
        init = {1: "alice"}
        ops = ["UPDATE 1 alicia"]
        result = execute_batch(init, ops)
        result[2] = "bob"
        self.assertNotIn(2, init)

    # 12. multiple sequential valid operations
    def test_many_valid_operations(self):
        init = {}
        ops = [f"INSERT {i} user{i}" for i in range(1, 6)]
        expected = {i: f"user{i}" for i in range(1, 6)}
        self.assertEqual(execute_batch(init, ops), expected)


if __name__ == "__main__":
    unittest.main()
