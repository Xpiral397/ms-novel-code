
import os
import json
import time
import secrets
import hashlib
import unicodedata
from contextlib import contextmanager
from typing import Optional, List, Dict, Any


class ResourceService:
    def __init__(self, root_dir: str) -> None:
        self.root = os.path.abspath(root_dir)
        os.makedirs(self.root, exist_ok=True)
        self.audit_path = os.path.join(self.root, "audit.log")
        self.audit_lock = os.path.join(self.root, "audit.lock")

    def create_resource(
        self, user_id: str, resource_name: str, content: str
    ) -> str:
        uid = self._check_user_id(user_id)
        name = self._check_resource_name(resource_name)
        slug = name.casefold()

        with self._user_lock(uid):
            data = self._read_user_json(uid)
            if slug in data:
                raise FileExistsError(
                    f"{resource_name!r} exists for user {uid!r}"
                )
            rev = secrets.token_hex(16)
            data[slug] = {"name": name, "revs": [{"id": rev, "text": content}]}
            self._write_user_json(uid, data)
            self._log_event({
                "action": "create", "user": uid,
                "resource": name, "rev": rev
            })
            return rev

    def read_resource(
        self,
        user_id: str,
        resource_name: str,
        revision_id: Optional[str] = None
    ) -> str:
        uid = self._check_user_id(user_id)
        name = self._check_resource_name(resource_name)
        slug = name.casefold()

        self._wait_unlock(uid)
        data = self._read_user_json(uid)
        if slug not in data:
            raise FileNotFoundError(
                f"{resource_name!r} not found for user {uid!r}"
            )
        revs = data[slug]["revs"]
        if revision_id is None:
            return revs[-1]["text"]
        for r in revs:
            if r["id"] == revision_id:
                return r["text"]
        raise FileNotFoundError(
            f"Revision {revision_id!r} not found for {resource_name!r}"
        )

    def update_resource(
        self, user_id: str, resource_name: str, new_content: str
    ) -> str:
        uid = self._check_user_id(user_id)
        name = self._check_resource_name(resource_name)
        slug = name.casefold()

        with self._user_lock(uid):
            data = self._read_user_json(uid)
            if slug not in data:
                raise FileNotFoundError(
                    f"{resource_name!r} not found for user {uid!r}"
                )
            rev = secrets.token_hex(16)
            data[slug]["revs"].append({"id": rev, "text": new_content})
            self._write_user_json(uid, data)
            self._log_event({
                "action": "update", "user": uid,
                "resource": name, "rev": rev
            })
            return rev

    def delete_resource(self, user_id: str, resource_name: str) -> None:
        uid = self._check_user_id(user_id)
        name = self._check_resource_name(resource_name)
        slug = name.casefold()

        with self._user_lock(uid):
            data = self._read_user_json(uid)
            if slug not in data:
                raise FileNotFoundError(
                    f"{resource_name!r} not found for user {uid!r}"
                )
            del data[slug]
            self._write_user_json(uid, data)
            self._log_event({
                "action": "delete", "user": uid, "resource": name
            })

    def list_resources(self, user_id: str) -> List[str]:
        uid = self._check_user_id(user_id)
        self._wait_unlock(uid)
        data = self._read_user_json(uid)
        return [info["name"] for info in data.values()]

    def list_revisions(
        self, user_id: str, resource_name: str
    ) -> List[str]:
        uid = self._check_user_id(user_id)
        name = self._check_resource_name(resource_name)
        slug = name.casefold()

        self._wait_unlock(uid)
        data = self._read_user_json(uid)
        if slug not in data:
            raise FileNotFoundError(
                f"{resource_name!r} not found for user {uid!r}"
            )
        return [r["id"] for r in data[slug]["revs"]]

    def verify_audit_log(self) -> bool:
        if not os.path.exists(self.audit_path):
            return True
        prev = ""
        try:
            with open(self.audit_path, "r", encoding="utf-8") as f:
                for raw in f:
                    entry = json.loads(raw)
                    expected = hashlib.sha256(
                        (prev + json.dumps(entry["event"],
                                          sort_keys=True)).encode()
                    ).hexdigest()
                    if entry.get("hash") != expected:
                        return False
                    prev = raw.rstrip("\n")
        except Exception:
            return False
        return True

    def _check_user_id(self, uid: str) -> str:
        if not uid or os.sep in uid:
            raise ValueError("Invalid user_id")
        path = os.path.realpath(os.path.join(self.root, f"{uid}.json"))
        if not path.startswith(self.root + os.sep):
            raise PermissionError("Path escape")
        return uid

    def _check_resource_name(self, name: str) -> str:
        if not name or os.sep in name or not name.endswith(".txt"):
            raise ValueError("Invalid resource_name")
        norm = unicodedata.normalize("NFC", name)
        if len(norm.encode("utf-8")) > 255:
            raise ValueError("Name too long")
        return norm

    def _read_user_json(self, uid: str) -> Dict[str, Any]:
        path = os.path.join(self.root, f"{uid}.json")
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write_user_json(self, uid: str, data: Dict[str, Any]) -> None:
        path = os.path.join(self.root, f"{uid}.json")
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(tmp, path)

    def _wait_unlock(self, uid: str, timeout: float = 0.2) -> None:
        lock = os.path.join(self.root, f"{uid}.lock")
        start = time.monotonic()
        while os.path.exists(lock):
            if time.monotonic() - start > timeout:
                raise TimeoutError("Lock wait timed out")
            time.sleep(0.001)

    @contextmanager
    def _user_lock(self, uid: str, timeout: float = 0.2):
        lock = os.path.join(self.root, f"{uid}.lock")
        start = time.monotonic()
        while True:
            try:
                fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.close(fd)
                break
            except FileExistsError:
                if time.monotonic() - start > timeout:
                    raise TimeoutError("Could not acquire user lock")
                time.sleep(0.001)
        try:
            yield
        finally:
            try:
                os.remove(lock)
            except OSError:
                pass

    def _log_event(self, event: dict) -> None:
        start = time.monotonic()
        while True:
            try:
                fd = os.open(
                    self.audit_lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY
                )
                os.close(fd)
                break
            except FileExistsError:
                if time.monotonic() - start > 0.2:
                    raise TimeoutError("Audit lock timeout")
                time.sleep(0.001)

        prev_line = ""
        if os.path.exists(self.audit_path):
            with open(self.audit_path, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
                if lines:
                    prev_line = lines[-1]

        payload = json.dumps(event, sort_keys=True)
        h = hashlib.sha256((prev_line + payload).encode()).hexdigest()
        record = {"hash": h, "event": event}
        line = json.dumps(record, ensure_ascii=False)

        with open(self.audit_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

        try:
            os.remove(self.audit_lock)
        except OSError:
            pass

