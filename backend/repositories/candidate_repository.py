from pathlib import Path
from typing import Any

from backend.repositories.json_repository import JSONRepository


class CandidateRepository:
    """JSON-backed candidate repository.

    This is temporary persistence and can later be replaced
    by a TVS database-backed repository without changing the
    candidate business logic.
    """

    def __init__(self):
        data_file = Path(__file__).resolve().parent.parent / "data" / "candidates.json"
        self.storage = JSONRepository(data_file)

    def get_all(self) -> list[dict[str, Any]]:
        """Return all candidates."""
        return self.storage.get_all()

    def get_by_id(self, candidate_id: str) -> dict[str, Any] | None:
        """Return a candidate by candidate ID."""
        candidates = self.storage.get_all()

        for candidate in candidates:
            if str(candidate.get("candidate_id")) == str(candidate_id):
                return candidate

        return None

    def save(self, candidate: dict[str, Any]) -> dict[str, Any]:
        """Create or update a candidate."""
        candidates = self.storage.get_all()
        candidate_id = str(candidate["candidate_id"])

        for index, existing_candidate in enumerate(candidates):
            if str(existing_candidate.get("candidate_id")) == candidate_id:
                candidates[index] = dict(candidate)
                self.storage.save_all(candidates)
                return candidates[index]

        candidates.append(dict(candidate))
        self.storage.save_all(candidates)
        return candidate
