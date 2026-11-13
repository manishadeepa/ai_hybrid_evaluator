import json
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
import os
import tempfile
import time
from pathlib import Path
from typing import Any

from backend.data_paths import resolve_data_path
from backend.data_paths import get_active_data_dir, STABLE_DATA_FILES


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


def _mysql_target(file_path: str | Path):
    path = resolve_data_path(Path(file_path))
    if Path(file_path).name in STABLE_DATA_FILES:
        return path, None, ""
    try:
        key = path.resolve().relative_to(get_active_data_dir().resolve()).as_posix()
    except ValueError:
        return path, None, ""
    from backend.database.mysql_json_store import active_mysql_store
    return path, active_mysql_store(), key


def read_json_document(file_path: str | Path, default=None):
    """Read an arbitrary JSON value from active MySQL storage or its JSON folder."""
    from backend.services.assessment_service import _PERSISTENCE_LOCK
    with _PERSISTENCE_LOCK:
        path, store, key = _mysql_target(file_path)
        if store is not None:
            return store.get_document(key, deepcopy(default))
        if not path.exists():
            return deepcopy(default)
        try:
            with path.open("r", encoding="utf-8-sig") as file:
                return json.load(file)
        except (json.JSONDecodeError, UnicodeError) as exc:
            raise ValueError(f"Invalid JSON document: {path.name}") from exc


def json_document_exists(file_path: str | Path) -> bool:
    """Check for a JSON document without creating a missing folder-backed file."""
    from backend.services.assessment_service import _PERSISTENCE_LOCK
    with _PERSISTENCE_LOCK:
        path, store, key = _mysql_target(file_path)
        return store.has_document(key) if store is not None else path.exists()


def write_json_document(file_path: str | Path, value) -> None:
    """Atomically persist an arbitrary JSON value to active MySQL or JSON storage."""
    from backend.services.assessment_service import _PERSISTENCE_LOCK
    with _PERSISTENCE_LOCK:
        path, store, key = _mysql_target(file_path)
        if store is not None:
            store.save_document(key, value)
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=path.parent,
                prefix=path.name + ".",
                suffix=".tmp",
                delete=False,
            ) as file:
                temporary = Path(file.name)
                file.write(payload)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary, path)
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()


class JSONRepository:
    """Reusable JSON file storage for backend repositories."""

    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)
        self._ensure_file_exists()

    def _resolved_path(self) -> Path:
        return resolve_data_path(self.file_path)

    def _active_mysql_store(self):
        return _mysql_target(self.file_path)[1]

    def _document_key(self, path: Path) -> str:
        return _mysql_target(path)[2]

    def _ensure_file_exists(self) -> None:
        """Initialize once, serialized with writes and storage migration."""
        from backend.services.assessment_service import _PERSISTENCE_LOCK
        with _PERSISTENCE_LOCK:
            if self._active_mysql_store() is not None:
                return
            path = self._resolved_path()
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                self._write_data([])

    def _read_data(self) -> list[dict[str, Any]]:
        """Read and return records from the JSON file."""
        store = self._active_mysql_store()
        if store is not None:
            data = store.get_document(self._document_key(self._resolved_path()))
            if not isinstance(data, list) or any(not isinstance(row, dict) for row in data):
                raise ValueError(f"Invalid MySQL application data: {self.file_path.name}")
            return data
        path = self._resolved_path()
        try:
            with path.open("r", encoding="utf-8-sig") as file:
                data = json.load(file)
        except (json.JSONDecodeError, UnicodeError) as exc:
            raise ValueError(f"Invalid or empty JSON repository: {path.name}") from exc

        if not isinstance(data, list) or any(not isinstance(row, dict) for row in data):
            raise ValueError(
                f"JSON repository must contain a list: {path}"
            )

        return data

    def _write_data(self, data: list[dict[str, Any]]) -> None:
        """Resolve and commit under the shared storage-switch lock."""
        from backend.services.assessment_service import _PERSISTENCE_LOCK
        with _PERSISTENCE_LOCK:
            self._write_data_locked(data)

    def _write_data_locked(self, data: list[dict[str, Any]]) -> None:
        path = self._resolved_path()
        store = self._active_mysql_store()
        if store is not None:
            store.save_document(self._document_key(path), data)
            return
        # Serialize before touching disk; replace only a fully written sibling file.
        payload = json.dumps(data, indent=4, ensure_ascii=False, allow_nan=False)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                             prefix=path.name + ".", suffix=".tmp", delete=False) as file:
                temporary = Path(file.name)
                file.write(payload)
                file.flush()
                os.fsync(file.fileno())
            # Windows scanners/sync clients can briefly hold the destination.
            # Keep replacement atomic; never truncate or delete the existing file.
            for attempt in range(4):
                try:
                    os.replace(temporary, path)
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
        path = self._resolved_path()
        scope = _READ_SCOPE.get()
        if scope is None:
            return self._read_data()
        key = path.resolve()
        stat = key.stat()
        signature = (stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
        cached = scope.get(key)
        if cached is not None and cached[0] == signature:
            return deepcopy(cached[1])
        rows = self._read_data()
        read_path = self._resolved_path()
        # A concurrently replaced file must not be cached under its old signature.
        if read_path.resolve() != key:
            return rows
        after = read_path.stat()
        if signature == (after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            scope[key] = (signature, deepcopy(rows))
        return rows

    def save_all(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Replace all stored records."""
        path = self._resolved_path()
        scope = _READ_SCOPE.get()
        if scope is not None:
            scope.pop(path.resolve(), None)
        self._write_data(data)
        if scope is not None:
            scope.pop(self._resolved_path().resolve(), None)
        return data
