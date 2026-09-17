from pathlib import Path
from typing import Any

from backend.repositories.json_repository import JSONRepository


class ManualEvaluationRepository:
    """Temporary JSON-backed repository for manual evaluations."""

    def __init__(self):
        data_file = (
            Path(__file__).resolve().parent.parent
            / "data"
            / "manual_evaluations.json"
        )
        self.storage = JSONRepository(data_file)

    def get_all(self) -> list[dict[str, Any]]:
        """Return all manual evaluations."""
        return self.storage.get_all()

    def get_by_key(
        self,
        candidate_id: str,
        assessment_name: str,
        test_name: str,
    ) -> dict[str, Any] | None:
        """Find an evaluation for one candidate, assessment and test."""
        evaluations = self.storage.get_all()

        for evaluation in evaluations:
            if (
                str(evaluation.get("candidate_id")) == str(candidate_id)
                and str(evaluation.get("assessment_name")) == str(assessment_name)
                and str(evaluation.get("test_name")) == str(test_name)
            ):
                return evaluation

        return None

    def save(self, evaluation: dict[str, Any]) -> dict[str, Any]:
        """Create or update a manual evaluation."""
        evaluations = self.storage.get_all()

        candidate_id = str(evaluation["candidate_id"])
        assessment_name = str(evaluation["assessment_name"])
        test_name = str(evaluation["test_name"])

        for index, existing in enumerate(evaluations):
            if (
                str(existing.get("candidate_id")) == candidate_id
                and str(existing.get("assessment_name")) == assessment_name
                and str(existing.get("test_name")) == test_name
            ):
                evaluations[index] = dict(evaluation)
                self.storage.save_all(evaluations)
                return evaluations[index]

        evaluations.append(dict(evaluation))
        self.storage.save_all(evaluations)

        return evaluation
