from copy import deepcopy
from pathlib import Path
from backend.repositories.json_repository import JSONRepository


class CandidateRepository:
    """Candidate directory; retain the existing public repository operations."""
    def __init__(self, file_path=None):
        self.file_path = Path(file_path) if file_path is not None else Path(__file__).resolve().parents[1] / "data" / "candidates.json"
        self.storage = JSONRepository(self.file_path)

    @staticmethod
    def _validate(records):
        ids = []
        for row in records:
            identity = row.get("candidate_id")
            if not isinstance(identity, str) or not identity.strip() or identity != identity.strip():
                raise ValueError("Invalid candidate ID in candidates.json.")
            if any(not isinstance(row.get(k), str) or not row[k].strip() for k in ("name", "email")):
                raise ValueError("Invalid candidate name/email in candidates.json.")
            ids.append(identity.casefold())
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate candidate ID in candidates.json.")

    def get_all(self, include_deleted=False):
        rows = self.storage.get_all()
        self._validate(rows)
        return rows if include_deleted else [r for r in rows if not r.get("deleted_at")]

    def get_by_id(self, candidate_id):
        return next((r for r in self.get_all() if r["candidate_id"] == candidate_id), None)

    def save_all(self, records):
        self.get_all(include_deleted=True)  # Never overwrite malformed existing data.
        self._validate(records)
        return self.storage.save_all(deepcopy(records))

    def save(self, candidate):
        rows = self.get_all(include_deleted=True)
        identity = candidate["candidate_id"]
        rows = [r for r in rows if r["candidate_id"] != identity] + [deepcopy(candidate)]
        self.save_all(rows)
        return deepcopy(candidate)

    def delete(self, candidate_id):
        self.save_all([r for r in self.get_all(include_deleted=True) if r["candidate_id"] != candidate_id])
