# tests

import unittest
from main import simulate_distributed_cache


class TestDistributedCacheSimulator(unittest.TestCase):
    """Unit tests for simulate_distributed_cache(commands: list[str]) -> list[str].
    Tests are written against the prompt and requirements, not any specific implementation.
    """

    def test_example_sequence(self):
        cmds = [
            "PUT user1 Alice",
            "PUT user2 Bob",
            "GET user1",
            "DELETE user2",
            "GET user2",
            "EXIT",
        ]
        exp = ["STORED", "STORED", "Alice", "DELETED", "NOT_FOUND", "BYE"]
        self.assertEqual(simulate_distributed_cache(cmds), exp)

    def test_get_on_missing_key(self):
        cmds = ["GET missing", "EXIT"]
        exp = ["NOT_FOUND", "BYE"]
        self.assertEqual(simulate_distributed_cache(cmds), exp)

    def test_delete_on_missing_key(self):
        cmds = ["DELETE nope", "EXIT"]
        exp = ["NOT_FOUND", "BYE"]
        self.assertEqual(simulate_distributed_cache(cmds), exp)

    def test_put_overwrite_and_get_new_value(self):
        cmds = [
            "PUT k1 v1",
            "PUT k1 v2",  # overwrite same key
            "GET k1",
            "EXIT",
        ]
        exp = ["STORED", "STORED", "v2", "BYE"]
        self.assertEqual(simulate_distributed_cache(cmds), exp)

    def test_invalid_missing_args_and_extra_args(self):
        cmds = [
            "PUT keyOnly",          # missing value
            "GET",                  # missing key
            "DELETE",               # missing key
            "PUT a b c",            # extra arg
            "GET a extra",          # extra arg
            "EXIT",
        ]
        exp = ["ERROR", "ERROR", "ERROR", "STORED", "ERROR", "BYE"]
        self.assertEqual(simulate_distributed_cache(cmds), exp)

    def test_invalid_key_constraints(self):
        # Keys must be non-empty, alphanumeric, len <= 64
        long_key = "k" * 65
        cmds = [
            # missing key entirely (two spaces after PUT)
            "PUT  v",
            "PUT  ''",                  # malformed; still missing args -> ERROR
            f"PUT {long_key} v",        # too long -> ERROR
            "PUT user-1 v",             # hyphen not alphanumeric -> ERROR
            "PUT user_1 v",             # underscore not alphanumeric -> ERROR
            "PUT user1 v",              # valid
            "GET user1",
            "EXIT",
        ]
        exp = ["ERROR", "ERROR", "ERROR", "ERROR",
               "ERROR", "STORED", "v", "BYE"]
        self.assertEqual(simulate_distributed_cache(cmds), exp)

    def test_invalid_value_constraints(self):
        # Values must be printable ASCII, len <= 256
        too_long_val = "x" * 257
        non_printable = "abc\x01def"
        printable = "~!@#$%^&*()_+=-[]{};:',.<>/?|\\`\""
        cmds = [
            f"PUT key1 {too_long_val}",     # too long -> ERROR
            f"PUT key2 {non_printable}",    # non-printable -> ERROR
            f"PUT key3 {printable}",        # printable OK
            "GET key3",
            "EXIT",
        ]
        exp = ["ERROR", "ERROR", "STORED", printable, "BYE"]
        self.assertEqual(simulate_distributed_cache(cmds), exp)

    def test_case_sensitivity(self):
        cmds = [
            "PUT Key1 Value",
            "GET key1",   # different case
            "GET Key1",
            "EXIT",
        ]
        exp = ["STORED", "NOT_FOUND", "Value", "BYE"]
        self.assertEqual(simulate_distributed_cache(cmds), exp)

    def test_repeated_delete_behavior(self):
        cmds = [
            "PUT a A",
            "DELETE a",
            "DELETE a",
            "EXIT",
        ]
        exp = ["STORED", "DELETED", "NOT_FOUND", "BYE"]
        self.assertEqual(simulate_distributed_cache(cmds), exp)

    def test_exit_mid_stream_stops_processing(self):
        cmds = [
            "PUT a A",
            "EXIT",
            "GET a",            # must be ignored after EXIT
            "DELETE a",         # ignored
        ]
        exp = ["STORED", "BYE"]  # outputs after EXIT should not appear
        self.assertEqual(simulate_distributed_cache(cmds), exp)

    def test_commands_with_embedded_whitespace_edges(self):
        # Ensure strict argument parsing: exactly expected count, space-separated.
        # These malformed forms must be ERROR.
        cmds = [
            "PUT   a   b",      # extra spaces but still two args: many parsers accept -> should be valid
            "GET   a",
            "PUT\tb\tc",        # tab separators should be invalid per "space-separated"
            "DELETE\tb",
            "PUT c   ",         # trailing spaces, missing value
            "GET    ",          # missing key
            "EXIT",
        ]
        exp = ["ERROR", "ERROR", "ERROR", "ERROR", "STORED", "ERROR", "BYE"]
        self.assertEqual(simulate_distributed_cache(cmds), exp)

    def test_concurrent_semantics_ordered_outputs(self):
        # Even with concurrent execution per command, outputs must be returned in input order.
        cmds = [
            "PUT x 1",
            "PUT x 2",
            "GET x",
            "DELETE x",
            "GET x",
            "EXIT",
        ]
        # Deterministic expectations:
        # - Two STORED acknowledgments in order
        # - GET returns last stored value "2"
        # - DELETE removes it
        # - GET after delete returns NOT_FOUND
        exp = ["STORED", "STORED", "2", "DELETED", "NOT_FOUND", "BYE"]
        self.assertEqual(simulate_distributed_cache(cmds), exp)

    def test_high_volume_reasonable_runtime(self):
        # Create 200 operations: 100 PUTs then 100 GETs for distinct keys.
        puts = [f"PUT k{i} v{i}" for i in range(100)]
        gets = [f"GET k{i}" for i in range(100)]
        cmds = puts + gets + ["EXIT"]
        out = simulate_distributed_cache(cmds)
        # First 100 responses are STORED
        self.assertEqual(out[:100], ["STORED"] * 100)
        # Next 100 responses are v0..v99 in order
        self.assertEqual(out[100:200], [f"v{i}" for i in range(100)])
        # Last response is BYE
        self.assertEqual(out[-1], "BYE")

    def test_commands_limit_not_enforced_but_handles_many(self):
        # Not required to validate the 10,000 max, but should handle a few hundred.
        n = 300
        cmds = [f"PUT u{i} val{i}" for i in range(
            n)] + [f"GET u{i}" for i in range(n)] + ["EXIT"]
        out = simulate_distributed_cache(cmds)
        self.assertEqual(len(out), 2 * n + 1)
        self.assertTrue(all(x == "STORED" for x in out[:n]))
        self.assertEqual(out[n:2 * n], [f"val{i}" for i in range(n)])
        self.assertEqual(out[-1], "BYE")


if __name__ == "__main__":
    unittest.main()
