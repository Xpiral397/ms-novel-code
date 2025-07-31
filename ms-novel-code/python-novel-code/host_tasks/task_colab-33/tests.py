# tests

import unittest
import copy
from main import migrate_payload, rollback_payload, _snapshot_store


class TestSchemaEvolution(unittest.TestCase):
    def setUp(self):
        _snapshot_store.clear()

    def test_upgrade_v1_to_v3(self):
        payload = {"version": "v1",
                   "data": {"user_id": 1, "items": [{"price_cents": 100}]}}
        rules = {
            "v1_to_v2": [
                {"op": "map", "path": "items", "rules": [
                    {"op": "rename", "from": "price_cents", "to": "price"},
                    {"op": "add", "field": "currency", "value": "USD"}]}],
            "v2_to_v3": [
                {"op": "rename", "from": "user_id", "to": "uid"}],
        }
        res = migrate_payload(payload, rules, "v3", payload_id="p1")
        self.assertEqual(res["version"], "v3")
        self.assertEqual(res["data"]["uid"], 1)
        self.assertEqual(res["data"]["items"][0],
                         {"price": 100, "currency": "USD"})

    def test_downgrade_v3_to_v1(self):
        payload = {"version": "v3", "data": {"uid": 1}}
        rules = {
            "v1_to_v2": [],
            "v2_to_v1": [],      # reverse step
            "v2_to_v3": [],
            "v3_to_v2": [],      # reverse step
        }
        res = migrate_payload(payload, rules, "v1", payload_id="p2")
        self.assertEqual(res["version"], "v1")

    def test_missing_rule_error(self):
        with self.assertRaises(ValueError):
            migrate_payload({"version": "v1", "data": {}},
                            {}, "v2", payload_id="p3")

    def test_snapshot_and_rollback(self):
        payload = {"version": "v1", "data": {"x": 1}}
        rules = {"v1_to_v2": [{"op": "set", "field": "x", "value": 2}]}
        migrate_payload(payload, rules, "v2", payload_id="p4")
        snap = rollback_payload("p4", "v1")
        self.assertEqual(snap, payload)

    def test_rollback_missing_version(self):
        with self.assertRaises(KeyError):
            rollback_payload("no_id", "v1")

    def test_migrate_to_same_version(self):
        payload = {"version": "v2", "data": {"a": 1}}
        migrate_payload(payload, {}, "v2", payload_id="p5")
        self.assertIn("v2", _snapshot_store["p5"])

    def test_rollback_to_current_version(self):
        payload = {"version": "v1", "data": {"a": 1}}
        migrate_payload(payload, {}, "v1", payload_id="p6")
        snap1 = rollback_payload("p6", "v1")
        snap2 = rollback_payload("p6", "v1")
        self.assertIsNot(snap1, snap2)

    def test_map_path_missing(self):
        payload = {"version": "v1", "data": {}}
        rules = {"v1_to_v2": [{"op": "map", "path": "items", "rules": [
            {"op": "add", "field": "foo", "value": "bar"}]}]}
        res = migrate_payload(payload, rules, "v2", payload_id="p7")
        self.assertEqual(res["data"], {})

    def test_map_empty_list(self):
        payload = {"version": "v1", "data": {"items": []}}
        rules = {"v1_to_v2": [{"op": "map", "path": "items", "rules": [
            {"op": "add", "field": "foo", "value": "bar"}]}]}
        res = migrate_payload(payload, rules, "v2", payload_id="p8")
        self.assertEqual(res["data"]["items"], [])

    def test_field_operations_chain(self):
        payload = {"version": "v1", "data": {}}
        rules = {"v1_to_v2": [
            {"op": "add", "field": "a", "value": 1},
            {"op": "set", "field": "a", "value": 2},
            {"op": "rename", "from": "a", "to": "b"},
            {"op": "remove", "field": "b"}]}
        res = migrate_payload(payload, rules, "v2", payload_id="p9")
        self.assertEqual(res["data"], {})

    def test_unknown_op(self):
        payload = {"version": "v1", "data": {}}
        rules = {"v1_to_v2": [{"op": "noop"}]}
        with self.assertRaises(ValueError):
            migrate_payload(payload, rules, "v2", payload_id="p10")

    def test_input_not_mutated(self):
        payload = {"version": "v1", "data": {"k": 1}}
        original = copy.deepcopy(payload)
        rules = {"v1_to_v2": [{"op": "set", "field": "k", "value": 2}]}
        migrate_payload(payload, rules, "v2", payload_id="p11")
        self.assertEqual(payload, original)


if __name__ == "__main__":
    unittest.main()
