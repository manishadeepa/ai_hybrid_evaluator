"""Persistent, salted-hash authentication for the single Master Admin."""

import hashlib
import hmac
import secrets
from pathlib import Path

from backend.repositories.json_repository import JSONRepository
from backend.data_paths import active_data_file


class MasterAdminService:
    """Store and authenticate one developer-managed Master Admin account."""

    ITERATIONS = 310_000

    def __init__(self, file_path=None):
        self.file_path = (
            Path(file_path)
            if file_path is not None
            else active_data_file("master_admin.json")
        )
        from backend.services.assessment_service import _PERSISTENCE_LOCK
        with _PERSISTENCE_LOCK:
            self.storage = JSONRepository(self.file_path)

    @staticmethod
    def _normalise_username(username):
        return str(username or "").strip()

    @classmethod
    def _hash_password(cls, password, salt):
        return hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, cls.ITERATIONS
        ).hex()

    def _get_record(self):
        records = self.storage.get_all()
        if len(records) > 1:
            raise ValueError("Master Admin storage contains multiple accounts.")
        if not records:
            return None

        record = records[0]
        if not all(
            isinstance(record.get(field), str) and record[field]
            for field in ("username", "salt", "password_hash")
        ):
            raise ValueError("Invalid Master Admin credential record.")
        try:
            bytes.fromhex(record["salt"])
            bytes.fromhex(record["password_hash"])
        except ValueError as exc:
            raise ValueError("Invalid Master Admin credential record.") from exc
        return record

    def get(self):
        """Return the public account identity, never credential material."""
        record = self._get_record()
        if record is None:
            return None
        return {"username": record["username"]}

    def is_configured(self):
        return self._get_record() is not None

    def authenticate(self, username, password):
        target = self._normalise_username(username).casefold()
        record = self._get_record()
        if record is None or record["username"].casefold() != target:
            return None
        salt = bytes.fromhex(record["salt"])
        supplied = self._hash_password(str(password or ""), salt)
        if hmac.compare_digest(supplied, record["password_hash"]):
            return {"username": record["username"]}
        return None

    def create(self, username, password):
        from backend.services.assessment_service import _PERSISTENCE_LOCK
        with _PERSISTENCE_LOCK:
            username = self._normalise_username(username)
            password = str(password or "").strip()
            if not username or not password:
                raise ValueError("Username and password are required.")
            if self._get_record() is not None:
                raise ValueError("A Master Admin account already exists.")

            salt = secrets.token_bytes(16)
            self.storage.save_all(
                [
                    {
                        "username": username,
                        "salt": salt.hex(),
                        "password_hash": self._hash_password(password, salt),
                    }
                ]
            )
            return {"username": username}

    def update(self, old_username, username, password=""):
        from backend.services.assessment_service import _PERSISTENCE_LOCK
        with _PERSISTENCE_LOCK:
            old_username = self._normalise_username(old_username).casefold()
            username = self._normalise_username(username)
            password = str(password or "").strip()
            if not username:
                raise ValueError("Username is required.")

            record = self._get_record()
            if record is None or record["username"].casefold() != old_username:
                raise ValueError("Master Admin account was not found.")

            updated_record = dict(record)
            updated_record["username"] = username
            if password:
                salt = secrets.token_bytes(16)
                updated_record["salt"] = salt.hex()
                updated_record["password_hash"] = self._hash_password(password, salt)
            self.storage.save_all([updated_record])
            return {"username": username}
