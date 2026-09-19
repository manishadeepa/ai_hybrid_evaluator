from pathlib import Path
from copy import deepcopy
from backend.repositories.json_repository import JSONRepository


class TestRepository:
    """JSON persistence for tests; files are created on first write/read only."""

    def __init__(self, file_path=None):
        self.file_path = Path(file_path) if file_path is not None else Path(__file__).resolve().parents[1] / "data" / "tests.json"

    def exists(self):
        return self.file_path.exists()

    def get_all(self):
        records = JSONRepository(self.file_path).get_all()
        ids = [r.get("test_id") for r in records]
        if any(not isinstance(i, str) or not i.strip() for i in ids) or len(ids) != len(set(ids)):
            raise ValueError("Invalid or duplicate test_id in {}".format(self.file_path.name))
        if any(not isinstance(r.get(field), str) or not r[field].strip()
               for r in records for field in ("assessment_id", "test_name")):
            raise ValueError("Invalid test relationship in {}".format(self.file_path.name))
        if any(not isinstance(r.get("position", 0), int) or not isinstance(r.get("is_final"), bool) for r in records):
            raise ValueError("Invalid test position/type in {}".format(self.file_path.name))
        return records

    def save_all(self, records):
        return JSONRepository(self.file_path).save_all(deepcopy(records))

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
        self.save_all([r for r in self.get_all() if r["test_id"] != record_id])
