"""Persistent authentication for administrator accounts created in Access Control."""

import hashlib
import hmac
import secrets
from copy import deepcopy
from pathlib import Path

from backend.repositories.json_repository import JSONRepository
from backend.data_paths import active_data_file


class GroupAdminService:
    """Store group-admin credentials as salted PBKDF2 hashes in JSON."""

    ITERATIONS = 310_000

    def __init__(self, file_path=None):
        self.file_path = (
            Path(file_path)
            if file_path is not None
            else active_data_file("group_admins.json")
        )
        self.storage = JSONRepository(self.file_path)

    @staticmethod
    def _normalise_username(username):
        return str(username or "").strip()

    @classmethod
    def _hash_password(cls, password, salt):
        return hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, cls.ITERATIONS
        ).hex()

    def get_all(self):
        records = self.storage.get_all()
        usernames = []
        for row in records:
            if not all(isinstance(row.get(field), str) for field in ("username", "salt", "password_hash")):
                raise ValueError("Invalid administrator record in group_admins.json.")
            if not row["username"].strip() or not row["salt"] or not row["password_hash"]:
                raise ValueError("Incomplete administrator record in group_admins.json.")
            usernames.append(row["username"].casefold())
        if len(usernames) != len(set(usernames)):
            raise ValueError("Duplicate administrator username in group_admins.json.")
        return deepcopy(records)

    def authenticate(self, username, password):
        target = self._normalise_username(username).casefold()
        for row in self.get_all():
            if row["username"].casefold() != target:
                continue
            try:
                salt = bytes.fromhex(row["salt"])
            except ValueError as exc:
                raise ValueError("Invalid administrator credential record.") from exc
            supplied = self._hash_password(str(password or ""), salt)
            if hmac.compare_digest(supplied, row["password_hash"]):
                return {"username": row["username"], "employee_id": row.get("employee_id", "")}
            return None
        return None

    def create(self, username, password):
        username = self._normalise_username(username)
        password = str(password or "").strip()
        if not username or not password:
            raise ValueError("Username and password are required.")
        rows = self.get_all()
        if any(row["username"].casefold() == username.casefold() for row in rows):
            raise ValueError("An administrator with this username already exists.")
        salt = secrets.token_bytes(16)
        rows.append({
            "username": username,
            "salt": salt.hex(),
            "password_hash": self._hash_password(password, salt),
        })
        self.storage.save_all(rows)
        return {"username": username}

    def update(self, old_username, username, password=""):
        old_username = self._normalise_username(old_username).casefold()
        username = self._normalise_username(username)
        password = str(password or "").strip()
        if not username:
            raise ValueError("Username is required.")
        rows = self.get_all()
        index = next((i for i, row in enumerate(rows) if row["username"].casefold() == old_username), None)
        if index is None:
            raise ValueError("Administrator account was not found.")
        if any(i != index and row["username"].casefold() == username.casefold() for i, row in enumerate(rows)):
            raise ValueError("An administrator with this username already exists.")
        rows[index]["username"] = username
        if password:
            salt = secrets.token_bytes(16)
            rows[index]["salt"] = salt.hex()
            rows[index]["password_hash"] = self._hash_password(password, salt)
        self.storage.save_all(rows)
        return {"username": username}

    def delete(self, username):
        target = self._normalise_username(username).casefold()
        rows = self.get_all()
        remaining = [row for row in rows if row["username"].casefold() != target]
        if len(remaining) == len(rows):
            raise ValueError("Administrator account was not found.")
        self.storage.save_all(remaining)
