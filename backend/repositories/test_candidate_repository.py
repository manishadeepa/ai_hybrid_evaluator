from copy import deepcopy
from pathlib import Path
from backend.repositories.json_repository import JSONRepository
from backend.data_paths import resolve_data_path


class TestCandidateRepository:
    def __init__(self, file_path=None):
        self.file_path = Path(file_path) if file_path else Path(__file__).resolve().parents[1] / "data" / "test_candidates.json"

    def get_all(self):
        path = resolve_data_path(self.file_path)
        if not path.exists():
            return []
        rows = JSONRepository(path).get_all()
        self._validate(rows)
        return rows

    @staticmethod
    def _validate(rows):
        pairs = []
        for r in rows:
            if any(not isinstance(r.get(k), str) or not r[k].strip() for k in ("candidate_id", "assessment_id", "test_id")):
                raise ValueError("Invalid candidate/test assignment identity.")
            if r.get("status") not in ("Assigned", "In Progress", "Submitted", "Disqualified"):
                raise ValueError("Invalid candidate/test status.")
            pairs.append((r["candidate_id"], r["test_id"]))
        if len(pairs) != len(set(pairs)):
            raise ValueError("Duplicate candidate/test assignment.")

    def save_all(self, records):
        from contextlib import ExitStack
        from backend.services.assessment_service import _PERSISTENCE_LOCK
        from backend.services.test_service import test_mutation_guard

        with _PERSISTENCE_LOCK:
            existing = self.get_all()
            test_ids = {row["test_id"] for row in existing + records}
            with ExitStack() as stack:
                for test_id in test_ids:
                    row = next(item for item in existing + records if item["test_id"] == test_id)
                    stack.enter_context(test_mutation_guard(
                        test_id=test_id,
                        assessment_id=row["assessment_id"],
                        data_dir=self.file_path.parent,
                    ))
                self._validate(records)
                JSONRepository(self.file_path).save_all(deepcopy(records))

    def get(self, candidate_id, test_id):
        return next((r for r in self.get_all() if r["candidate_id"] == candidate_id and r["test_id"] == test_id), None)

    def save(self, record):
        from backend.services.test_service import test_mutation_guard

        with test_mutation_guard(
            test_id=record.get("test_id"),
            assessment_id=record.get("assessment_id"),
            data_dir=self.file_path.parent,
        ):
            rows = self.get_all()
            rows = [r for r in rows if (r["candidate_id"], r["test_id"]) != (record["candidate_id"], record["test_id"])]
            JSONRepository(self.file_path).save_all(rows + [deepcopy(record)])
            return deepcopy(record)

    def delete_by_test(self, test_id):
        """Delete candidate assignments belonging to one test."""
        from backend.services.test_service import test_mutation_guard

        with test_mutation_guard(test_id=test_id, data_dir=self.file_path.parent):
            rows = self.get_all()
            remaining = [r for r in rows if r["test_id"] != test_id]
            JSONRepository(self.file_path).save_all(remaining)
