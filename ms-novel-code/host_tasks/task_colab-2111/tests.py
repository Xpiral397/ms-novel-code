# tests

import os
import json
import time
import threading
import tempfile
import unittest
from pathlib import Path

# The implementation to be tested must live in main.py
from main import ResourceService


# ---------- helpers ---------- #

def new_service():
    """Return a fresh ResourceService rooted in a brand‑new temp dir
    and the pathlib.Path object for that directory."""
    tmpdir = tempfile.TemporaryDirectory()
    root = Path(tmpdir.name)
    return ResourceService(str(root)), root, tmpdir


def read_audit(root: Path) -> list[dict]:
    """Return audit.log lines already parsed as JSON."""
    log_file = root / "audit.log"
    if not log_file.exists():
        return []
    return [json.loads(l) for l in log_file.read_text().splitlines()]


# ---------- test‑cases ---------- #

class ResourceServiceBasics(unittest.TestCase):
    def setUp(self) -> None:
        self.svc, self.root, self._tmp = new_service()

    def tearDown(self) -> None:
        # Ensure tempdir is cleaned even if the test fails.
        self._tmp.cleanup()

    # ----- normal workflow ----- #
    def test_create_read_update_delete_cycle(self):
        rid1 = self.svc.create_resource("alice", "note.txt", "first")
        self.assertIsInstance(rid1, str)
        self.assertEqual(self.svc.read_resource("alice", "note.txt"), "first")

        rid2 = self.svc.update_resource("alice", "note.txt", "second")
        self.assertNotEqual(rid1, rid2)
        self.assertEqual(self.svc.read_resource("alice", "note.txt"), "second")
        self.assertEqual(self.svc.read_resource("alice", "note.txt", rid1), "first")

        revs = self.svc.list_revisions("alice", "note.txt")
        self.assertEqual(revs, [rid1, rid2])

        resources = self.svc.list_resources("alice")
        self.assertEqual(resources, ["note.txt"])

        # audit log must verify
        self.assertTrue(self.svc.verify_audit_log())

        # delete and ensure it is gone
        self.svc.delete_resource("alice", "note.txt")
        with self.assertRaises(FileNotFoundError):
            self.svc.read_resource("alice", "note.txt")

    # ----- duplicate and case‑insensitive slug clash ----- #
    def test_duplicate_resource_raises(self):
        self.svc.create_resource("alice", "Hello.txt", "a")
        with self.assertRaises(FileExistsError):
            self.svc.create_resource("alice", "hELLo.TXT", "b")

    # ----- edge‑case: bad inputs ----- #
    def test_invalid_user_and_resource_names(self):
        with self.assertRaises(ValueError):
            self.svc.create_resource("al/ice", "note.txt", "x")          # slash inside user
        with self.assertRaises(ValueError):
            self.svc.create_resource("bob", "note", "x")                 # missing .txt
        with self.assertRaises(ValueError):
            self.svc.create_resource("bob", "../note.txt", "x")          # traversal chars
        long_name = "a" * 260 + ".txt"
        with self.assertRaises(ValueError):
            self.svc.create_resource("bob", long_name, "x")

    # ----- missing resource operations ----- #
    def test_missing_resource_errors(self):
        with self.assertRaises(FileNotFoundError):
            self.svc.read_resource("nobody", "ghost.txt")
        with self.assertRaises(FileNotFoundError):
            self.svc.update_resource("nobody", "ghost.txt", "boo")
        with self.assertRaises(FileNotFoundError):
            self.svc.delete_resource("nobody", "ghost.txt")
        with self.assertRaises(FileNotFoundError):
            self.svc.list_revisions("nobody", "ghost.txt")

    # ----- path‑traversal / symlink attack ----- #
    def test_symlink_escape_prevention(self):
        # Forge a symlink inside <root> that points outside
        outside = Path(tempfile.gettempdir()) / "evil.json"
        outside.write_text("{}")
        (self.root / "bob.json").symlink_to(outside)
        with self.assertRaises(PermissionError):
            self.svc.create_resource("bob", "note.txt", "should fail")

    # ----- audit‑log tamper detection ----- #
    def test_audit_log_tampering_detected(self):
        self.svc.create_resource("alice", "note.txt", "hi")
        self.assertTrue(self.svc.verify_audit_log())      # baseline OK

        # Break the hash chain: flip one bit in the 2nd char of 2nd line
        log_file = self.root / "audit.log"
        lines = log_file.read_bytes().splitlines()
        if len(lines) < 2:   # paranoia guard
            self.skipTest("need at least two lines to tamper")
        tampered = bytearray(lines[1])
        tampered[2] ^= 0x01
        lines[1] = bytes(tampered)
        log_file.write_bytes(b"\n".join(lines))

        self.assertFalse(self.svc.verify_audit_log())

    # ----- concurrent access with per‑user locking ----- #
    def test_concurrent_updates_consistent(self):
        rid0 = self.svc.create_resource("alice", "note.txt", "v0")

        # 20 threads each append one revision
        def worker(i):
            self.svc.update_resource("alice", "note.txt", f"v{i}")

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        revs = self.svc.list_revisions("alice", "note.txt")
        # initial + 20 updates
        self.assertEqual(len(revs), 1 + 20)
        self.assertEqual(self.svc.read_resource("alice", "note.txt"), "v19")
        self.assertTrue(self.svc.verify_audit_log())


# Run the tests when executed directly
if __name__ == "__main__":
    unittest.main(verbosity=2)
