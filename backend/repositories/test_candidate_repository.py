from copy import deepcopy
from pathlib import Path
from backend.repositories.json_repository import JSONRepository


class TestCandidateRepository:
    def __init__(self, file_path=None):
        self.file_path = Path(file_path) if file_path else Path(__file__).resolve().parents[1] / "data" / "test_candidates.json"

    def get_all(self):
        if not self.file_path.exists():
            return []
        rows = JSONRepository(self.file_path).get_all()
        pairs = []
        for r in rows:
            if any(not isinstance(r.get(k), str) or not r[k].strip() for k in ("candidate_id", "assessment_id", "test_id")):
                raise ValueError("Invalid candidate/test assignment identity.")
            if r.get("status") not in ("Assigned", "In Progress", "Submitted", "Disqualified"):
                raise ValueError("Invalid candidate/test status.")
            pairs.append((r["candidate_id"], r["test_id"]))
        if len(pairs) != len(set(pairs)):
            raise ValueError("Duplicate candidate/test assignment.")
        return rows

    def get(self, candidate_id, test_id):
        return next((r for r in self.get_all() if r["candidate_id"] == candidate_id and r["test_id"] == test_id), None)

    def save(self, record):
        rows = self.get_all()
        rows = [r for r in rows if (r["candidate_id"], r["test_id"]) != (record["candidate_id"], record["test_id"])]
        JSONRepository(self.file_path).save_all(rows + [deepcopy(record)])
        return deepcopy(record)
