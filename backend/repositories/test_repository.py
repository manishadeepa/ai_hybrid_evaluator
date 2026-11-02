from pathlib import Path
from copy import deepcopy
from datetime import datetime, timezone
from backend.repositories.json_repository import JSONRepository
from backend.services.question_type_schema import validate_test_type
from backend.data_paths import resolve_data_path


LOCKED_TEST_ERROR = "This test is locked and is view-only."


class TestRepository:
    """JSON persistence for tests; files are created on first write/read only."""

    def __init__(self, file_path=None):
        self.file_path = Path(file_path) if file_path is not None else Path(__file__).resolve().parents[1] / "data" / "tests.json"

    def exists(self):
        return resolve_data_path(self.file_path).exists()

    @staticmethod
    def _lock():
        from backend.services.assessment_service import _PERSISTENCE_LOCK
        return _PERSISTENCE_LOCK

    def get_all(self):
        with self._lock():
            storage = JSONRepository(self.file_path)
            records = storage.get_all()
            self._validate(records)
            migrated = []
            changed = False
            for record in records:
                value = dict(record)
                for field, default in (
                    ("created_by", ""),
                    ("is_locked", False),
                    ("locked_by", ""),
                    ("locked_at", None),
                ):
                    if field not in value:
                        value[field] = default
                        changed = True
                migrated.append(value)
            if changed:
                self._validate(migrated)
                storage.save_all(migrated)
            return migrated

    @staticmethod
    def _validate(records):
        if not isinstance(records, list) or any(not isinstance(r, dict) for r in records):
            raise ValueError("Tests must be a list of objects.")
        for record in records:
            if "test_type" in record:
                validate_test_type(record["test_type"])
        ids = [r.get("test_id") for r in records]
        if any(not isinstance(i, str) or not i.strip() for i in ids) or len(ids) != len(set(ids)):
            raise ValueError("Invalid or duplicate test_id in tests.json")
        if any(not isinstance(r.get(field), str) or not r[field].strip()
               for r in records for field in ("assessment_id", "test_name")):
            raise ValueError("Invalid test relationship in tests.json")
        if any(not isinstance(r.get("position", 0), int) or not isinstance(r.get("is_final", False), bool) for r in records):
            raise ValueError("Invalid test position/type in tests.json")
        if any(r.get("status", "Draft") not in ("Draft", "Scheduled", "Active", "Completed") for r in records):
            raise ValueError("Invalid test status in tests.json")
        for record in records:
            if "created_by" in record and not isinstance(record["created_by"], str):
                raise ValueError("Invalid test creator in tests.json")
            if "is_locked" in record and not isinstance(record["is_locked"], bool):
                raise ValueError("Invalid test lock state in tests.json")
            if "locked_by" in record and not isinstance(record["locked_by"], str):
                raise ValueError("Invalid test lock owner in tests.json")
            locked_at = record.get("locked_at")
            if locked_at is not None and not isinstance(locked_at, str):
                raise ValueError("Invalid test lock timestamp in tests.json")
            if record.get("is_locked") and (
                not record.get("locked_by") or not record.get("locked_at")
            ):
                raise ValueError("Locked tests must have lock metadata in tests.json")
        return records

    def save_all(self, records):
        with self._lock():
            self._validate(records)
            normalized = []
            for record in records:
                value = dict(record)
                value.setdefault("created_by", "")
                value.setdefault("is_locked", False)
                value.setdefault("locked_by", "")
                value.setdefault("locked_at", None)
                normalized.append(value)
            self._validate(normalized)
            existing = self.get_all() if self.exists() else []
            old_by_id = {row["test_id"]: row for row in existing}
            new_by_id = {row["test_id"]: row for row in normalized}
            for test_id, old in old_by_id.items():
                new = new_by_id.get(test_id)
                if old.get("is_locked") and new != old:
                    raise ValueError(LOCKED_TEST_ERROR)
                if new is not None and any(
                    new.get(field) != old.get(field)
                    for field in ("created_by", "is_locked", "locked_by", "locked_at")
                ):
                    raise ValueError("Test ownership and lock metadata cannot be changed.")
            if any(
                new_by_id[test_id].get("is_locked")
                for test_id in new_by_id.keys() - old_by_id.keys()
            ):
                raise ValueError("New tests cannot be created in a locked state.")
            return JSONRepository(self.file_path).save_all(deepcopy(normalized))

    def get_by_id(self, record_id):
        return next((r for r in self.get_all() if r["test_id"] == record_id), None)

    def save(self, record):
        records = self.get_all()
        for index, existing in enumerate(records):
            if existing["test_id"] == record["test_id"]:
                records[index] = deepcopy(record)
                break
        else:
            records.append(deepcopy(record))
        self.save_all(records)
        return deepcopy(record)

    def delete(self, record_id):
        with self._lock():
            record = self.get_by_id(record_id)
            if record and record.get("is_locked"):
                raise ValueError(LOCKED_TEST_ERROR)
            self.save_all([r for r in self.get_all() if r["test_id"] != record_id])

    def get_by_assessment(self, assessment_id):
        return [r for r in self.get_all() if r["assessment_id"] == assessment_id]

    def lock_test(self, test_id, facilitator_id, role):
        """Persist the permanent lock under the same lock used by every test mutation."""
        with self._lock():
            record = self.get_by_id(test_id)
            if record is None:
                raise ValueError("Test not found.")
            if role != "facilitator":
                raise ValueError("Only facilitators can lock tests.")
            if not isinstance(facilitator_id, str) or not facilitator_id.strip():
                raise ValueError("Authenticated facilitator identity is required.")
            if not record.get("created_by"):
                raise ValueError("Test creator is unknown; ownership must be resolved before locking.")
            if record["created_by"] != facilitator_id:
                raise ValueError("Only the test creator can lock this test.")
            if record.get("is_locked"):
                return {**record, "already_locked": True}

            record.update({
                "is_locked": True,
                "locked_by": facilitator_id,
                "locked_at": datetime.now(timezone.utc).isoformat(),
            })
            self._validate([record])
            rows = self.get_all()
            updated = [record if row["test_id"] == test_id else row for row in rows]
            JSONRepository(self.file_path).save_all(updated)
            return deepcopy(record)
