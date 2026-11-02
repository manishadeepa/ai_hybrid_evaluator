"""Resolve the app's active JSON data directory."""

import filecmp
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = PROJECT_ROOT / "backend" / "data"
DATA_LOCATION_FILE = PROJECT_ROOT / "backend" / "data_location.json"
STABLE_DATA_FILES = {"database_configurations.json"}
STABLE_DATA_DIRECTORIES = {"db_ca_certs"}
LEGACY_STATE_FILES = (
    "assessment_completions.json",
    "assessment_pass_percentages.json",
    "assessment_weightages.json",
    "candidate_feedbacks.json",
    "facilitator_feedbacks.json",
)


def copy_file_no_overwrite(source: Path, destination: Path) -> None:
    if destination.is_symlink():
        raise ValueError(f"Cannot migrate over linked data file: {destination.name}.")
    if destination.exists():
        if not destination.is_file() or not filecmp.cmp(
            source, destination, shallow=False
        ):
            raise ValueError(
                f"Conflicting data file: {destination.name}. "
                "Existing files were not overwritten."
            )
        return
    created = False
    completed = False
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(
            destination,
            os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            0o600,
        )
        created = True
        with os.fdopen(descriptor, "wb") as target:
            with source.open("rb") as source_file:
                shutil.copyfileobj(source_file, target)
            target.flush()
            os.fsync(target.fileno())
        completed = True
    except FileExistsError:
        if not destination.is_file() or not filecmp.cmp(
            source, destination, shallow=False
        ):
            raise ValueError(
                f"Conflicting data file: {destination.name}. "
                "Existing files were not overwritten."
            )
    except OSError as exc:
        raise ValueError(
            f"Could not safely migrate legacy data file {source.name} "
            f"({type(exc).__name__})."
        ) from exc
    finally:
        if created and not completed:
            destination.unlink(missing_ok=True)


def _read_migration_json(path: Path):
    with path.open("r", encoding="utf-8-sig") as file:
        return json.load(file)


def _merge_legacy_json(legacy, current, filename, keys=()):
    # Only dictionary keys can be merged without guessing list identity/order.
    if isinstance(legacy, dict) and isinstance(current, dict):
        merged = dict(current)
        for key, value in legacy.items():
            merged[key] = (_merge_legacy_json(value, current[key], filename, keys + (key,))
                           if key in current else value)
        return merged
    if type(legacy) is type(current) and legacy == current:
        return current
    if type(legacy) in (int, float) and type(current) in (int, float) and legacy == current:
        return current
    pointer = "/" + "/".join(str(k).replace("~", "~0").replace("/", "~1") for k in keys)
    raise ValueError(f"Conflicting data file: {filename} at {pointer}: "
                     f"legacy={json.dumps(legacy, ensure_ascii=False)}, "
                     f"backend={json.dumps(current, ensure_ascii=False)}. "
                     "Existing files were not overwritten.")


def _atomic_migration_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=path.name + ".", suffix=".tmp", delete=False) as file:
            temporary = Path(file.name)
            json.dump(value, file, indent=2, ensure_ascii=False)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _migrate_legacy_state_files() -> None:
    """One-time, serialized import; completed files are never compared again."""
    from contextlib import contextmanager
    from datetime import datetime, timezone
    import hashlib
    import time

    legacy_dir = PROJECT_ROOT / "ai_hybrid_evaluator" / "data"
    if not legacy_dir.is_dir():
        return
    marker = PROJECT_ROOT / "backend" / "legacy_state_migration.json"
    identity = hashlib.sha256(str(PROJECT_ROOT.resolve()).casefold().encode()).hexdigest()
    lock_path = Path(tempfile.gettempdir()) / f"hybrid-legacy-migration-{identity}.lock"

    @contextmanager
    def migration_lock():
        # Independent of the application lock: that lock resolves this directory.
        with lock_path.open("a+b") as lock:
            if os.name == "nt":
                import msvcrt
                lock.seek(0, os.SEEK_END)
                if lock.tell() == 0:
                    lock.write(b"\0")
                    lock.flush()
                lock.seek(0)
                while True:
                    try:
                        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
                        break
                    except OSError as exc:
                        import errno
                        if exc.errno not in (errno.EACCES, errno.EDEADLK, errno.EAGAIN):
                            raise
                        time.sleep(0.05)
            else:
                import fcntl
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                if os.name == "nt":
                    lock.seek(0)
                    msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    with migration_lock():
        completed = _read_migration_json(marker) if marker.exists() else {"version": 1, "files": {}}
        if not isinstance(completed, dict) or completed.get("version") != 1 or not isinstance(completed.get("files"), dict):
            raise ValueError("Invalid legacy migration record; existing data was not overwritten.")
        pending = [(name, legacy_dir / name, DEFAULT_DATA_DIR / name)
                   for name in LEGACY_STATE_FILES
                   if name not in completed["files"] and (legacy_dir / name).is_file()]
        if not pending:
            return
        backup = PROJECT_ROOT / "backend" / "migration_backups" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        # Back up every source and destination before planning or writing data.
        for name, source, destination in pending:
            if source.is_symlink() or destination.is_symlink() or (destination.exists() and not destination.is_file()):
                raise ValueError(f"Cannot migrate linked or non-file data: {name}.")
            for label, path in (("legacy", source), ("backend", destination)):
                if path.exists():
                    target = backup / label / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, target)
        plans = []
        conflicts = []
        for name, source, destination in pending:
            legacy = _read_migration_json(source)
            current = _read_migration_json(destination) if destination.exists() else None
            try:
                merged = _merge_legacy_json(legacy, current, name) if destination.exists() else legacy
                plans.append((name, destination, merged, destination.exists() and merged == current))
            except ValueError as exc:
                conflicts.append(str(exc))
        if conflicts:
            raise ValueError("\n".join(conflicts) + f" Backups: {backup}")
        for name, destination, merged, unchanged in plans:
            if not unchanged:
                _atomic_migration_json(destination, merged)
            completed["files"][name] = {"backup": str(backup), "completed_at": datetime.now(timezone.utc).isoformat()}
            # A marker per committed file makes restart after interruption safe.
            _atomic_migration_json(marker, completed)


def get_active_data_dir() -> Path:
    """Return the configured data directory, defaulting to backend/data."""
    if not DATA_LOCATION_FILE.exists():
        _migrate_legacy_state_files()
        return DEFAULT_DATA_DIR
    try:
        with DATA_LOCATION_FILE.open("r", encoding="utf-8") as file:
            settings: Any = json.load(file)
    except (OSError, json.JSONDecodeError, UnicodeError) as exc:
        raise ValueError("The active data-folder configuration cannot be read.") from exc
    if not isinstance(settings, dict):
        raise ValueError("The active data-folder configuration is invalid.")
    configured_path = settings.get("active_data_dir")
    if not isinstance(configured_path, str) or not configured_path.strip():
        raise ValueError("The active data-folder configuration is invalid.")
    path = Path(configured_path).expanduser()
    if not path.is_absolute():
        raise ValueError("The active data-folder path must be absolute.")
    return path


def resolve_data_path(path: str | Path) -> Path:
    """Redirect paths rooted in the default data directory to the active one."""
    candidate = Path(path)
    active = get_active_data_dir()
    roots = [
        DEFAULT_DATA_DIR,
        PROJECT_ROOT / "ai_hybrid_evaluator" / "data",
    ]
    if DATA_LOCATION_FILE.exists():
        try:
            with DATA_LOCATION_FILE.open("r", encoding="utf-8") as file:
                settings = json.load(file)
        except (OSError, json.JSONDecodeError, UnicodeError) as exc:
            raise ValueError(
                "The active data-folder configuration cannot be read."
            ) from exc
        managed = settings.get("managed_data_dirs", [])
        if not isinstance(managed, list) or any(
            not isinstance(item, str) or not item for item in managed
        ):
            raise ValueError("The active data-folder configuration is invalid.")
        roots.extend(Path(item) for item in managed)
        roots.append(active)
    roots = sorted(
        {root.resolve(strict=False) for root in roots},
        key=lambda root: len(root.parts),
        reverse=True,
    )
    relative = None
    for root in roots:
        try:
            relative = candidate.resolve(strict=False).relative_to(root)
            break
        except ValueError:
            continue
    if relative is None:
        return candidate
    if not relative.parts:
        return active
    if relative.parts[0] in STABLE_DATA_DIRECTORIES:
        return candidate
    if relative.parts[0] in STABLE_DATA_FILES:
        return candidate
    return active.joinpath(*relative.parts)


def active_data_file(filename: str) -> Path:
    """Return a path for one file in the currently active app data folder."""
    relative = Path(filename)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("Data filenames must be relative to the data folder.")
    path = get_active_data_dir() / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def save_active_data_dir(path: str | Path) -> Path:
    """Atomically persist the active data directory in the stable backend folder."""
    target = Path(path).expanduser().resolve()
    managed = {str(DEFAULT_DATA_DIR.resolve()), str(target)}
    if DATA_LOCATION_FILE.exists():
        try:
            with DATA_LOCATION_FILE.open("r", encoding="utf-8") as file:
                existing = json.load(file)
        except (OSError, json.JSONDecodeError, UnicodeError) as exc:
            raise ValueError(
                "The active data-folder configuration cannot be read."
            ) from exc
        old_active = existing.get("active_data_dir") if isinstance(existing, dict) else None
        if isinstance(old_active, str) and old_active:
            managed.add(str(Path(old_active).resolve(strict=False)))
        old_managed = existing.get("managed_data_dirs", []) if isinstance(existing, dict) else []
        if isinstance(old_managed, list):
            managed.update(
                str(Path(item).resolve(strict=False))
                for item in old_managed
                if isinstance(item, str) and item
            )
    DATA_LOCATION_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=DATA_LOCATION_FILE.parent,
            prefix=DATA_LOCATION_FILE.name + ".",
            suffix=".tmp",
            delete=False,
        ) as file:
            temporary = Path(file.name)
            json.dump(
                {
                    "active_data_dir": str(target),
                    "managed_data_dirs": sorted(managed),
                },
                file,
                indent=2,
            )
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, DATA_LOCATION_FILE)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    return target
