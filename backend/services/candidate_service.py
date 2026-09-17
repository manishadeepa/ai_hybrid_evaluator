from backend.repositories.candidate_repository import CandidateRepository


class CandidateService:
    """Business logic for candidate operations."""

    def __init__(self, repository: CandidateRepository | None = None):
        self.repository = repository or CandidateRepository()

    def get_all_candidates(self) -> list[dict]:
        """Return all candidates."""
        return self.repository.get_all()

    def get_candidate(self, candidate_id: str):
        """Return one candidate by candidate ID."""
        return self.repository.get_by_id(candidate_id)

    def save_candidate(self, candidate: dict):
        """Save or update a candidate."""
        return self.repository.save(candidate)
