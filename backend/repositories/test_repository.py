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
        return JSONRepository(self.file_path).get_all()

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
