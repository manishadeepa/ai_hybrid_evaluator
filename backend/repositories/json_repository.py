import json
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
import os
import tempfile
import time
from pathlib import Path
from typing import Any


_READ_SCOPE = ContextVar("json_repository_read_scope", default=None)


@contextmanager
def repository_read_scope():
    """Reuse unchanged JSON within one synchronous service operation only.

    Repository validation still runs on every access. Each caller owns its copy;
    file signatures detect replacements by other repository instances/processes.
    Never hold this scope across an await or use it as a process-wide cache.
    """
    if _READ_SCOPE.get() is not None:
        yield
        return
    token = _READ_SCOPE.set({})
    try:
        yield
    finally:
        _READ_SCOPE.reset(token)


class JSONRepository:
    """Reusable JSON file storage for backend repositories."""

    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)
        self._ensure_file_exists()

    def _ensure_file_exists(self) -> None:
        """Create the parent directory and an empty JSON list if needed."""
        if not self.file_path.exists():
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            self._write_data([])

    def _read_data(self) -> list[dict[str, Any]]:
        """Read and return records from the JSON file."""
        try:
            with self.file_path.open("r", encoding="utf-8-sig") as file:
                data = json.load(file)
        except (json.JSONDecodeError, UnicodeError) as exc:
            raise ValueError(f"Invalid or empty JSON repository: {self.file_path.name}") from exc

        if not isinstance(data, list) or any(not isinstance(row, dict) for row in data):
            raise ValueError(
                f"JSON repository must contain a list: {self.file_path}"
            )

        return data

    def _write_data(self, data: list[dict[str, Any]]) -> None:
        """Write records to the JSON file."""
        # Serialize before touching disk; replace only a fully written sibling file.
        payload = json.dumps(data, indent=4, ensure_ascii=False, allow_nan=False)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.file_path.parent,
                                             prefix=self.file_path.name + ".", suffix=".tmp", delete=False) as file:
                temporary = Path(file.name)
                file.write(payload)
                file.flush()
                os.fsync(file.fileno())
            # Windows scanners/sync clients can briefly hold the destination.
            # Keep replacement atomic; never truncate or delete the existing file.
            for attempt in range(4):
                try:
                    os.replace(temporary, self.file_path)
                    break
                except PermissionError as exc:
                    if getattr(exc, "winerror", None) not in (5, 32, 33) or attempt == 3:
                        raise
                    time.sleep((0.02, 0.05, 0.1)[attempt])
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()

    def get_all(self) -> list[dict[str, Any]]:
        """Return all stored records."""
        scope = _READ_SCOPE.get()
        if scope is None:
            return self._read_data()
        key = self.file_path.resolve()
        stat = key.stat()
        signature = (stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
        cached = scope.get(key)
        if cached is not None and cached[0] == signature:
            return deepcopy(cached[1])
        rows = self._read_data()
        # A concurrently replaced file must not be cached under its old signature.
        after = key.stat()
        if signature == (after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            scope[key] = (signature, deepcopy(rows))
        return rows

    def save_all(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Replace all stored records."""
        scope = _READ_SCOPE.get()
        if scope is not None:
            scope.pop(self.file_path.resolve(), None)
        self._write_data(data)
        return data
