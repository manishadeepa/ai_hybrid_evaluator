"""Encryption key management for credentials entered through the admin UIs."""

import os
from pathlib import Path

from cryptography.fernet import Fernet


PROJECT_ROOT = Path(__file__).resolve().parents[2]
KEY_FILE = PROJECT_ROOT / "backend" / ".credential_encryption.key"


def _read_or_create_key() -> bytes:
    KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        return KEY_FILE.read_bytes().strip()
    except FileNotFoundError:
        key = Fernet.generate_key()
        descriptor = None
        try:
            descriptor = os.open(
                KEY_FILE,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                0o600,
            )
        except FileExistsError:
            return KEY_FILE.read_bytes().strip()
        try:
            with os.fdopen(descriptor, "wb") as file:
                descriptor = None
                file.write(key)
                file.flush()
                os.fsync(file.fileno())
            try:
                KEY_FILE.chmod(0o600)
            except OSError:
                pass
            return key
        finally:
            if descriptor is not None:
                os.close(descriptor)


def get_credential_cipher() -> Fernet:
    """Use a host-injected secret or a persistent, app-generated key file.

    Environment variables are intentionally read without loading any .env file.
    """
    key = os.getenv("APP_CREDENTIAL_ENCRYPTION_KEY")
    if key:
        key_bytes = key.encode("utf-8")
    else:
        key_bytes = _read_or_create_key()
    try:
        return Fernet(key_bytes)
    except (TypeError, ValueError) as exc:
        raise ValueError("Credential encryption key is invalid.") from exc
