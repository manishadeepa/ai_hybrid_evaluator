from copy import deepcopy
from uuid import uuid4
from backend.repositories.test_repository import TestRepository


class TestService:
    """Keep stable test identities while adapting existing name-based UI fields."""

    def __init__(self, repository=None):
        self.repository = repository or TestRepository()

    def get_tests(self, assessment_id):
        return sorted((r for r in self.repository.get_all() if r["assessment_id"] == assessment_id),
                      key=lambda r: r.get("position", 0))

    def prepare_tests(self, assessment_id, assessment):
        old = self.get_tests(assessment_id)
        by_id = {r["test_id"]: r for r in old}
        by_name = {r["test_name"]: r for r in old}
        names = list(assessment.get("tests", []))
        final = assessment.get("final_test", "")
        if final:
            names.append(final)
        if any(not isinstance(n, str) or not n.strip() for n in names) or len(names) != len(set(names)):
            raise ValueError("Test names must be nonempty and unique within the assessment.")
        prepared = []
        used = set()
        for position, name in enumerate(names):
            requested_id = assessment.get("test_ids", {}).get(name)
            previous = by_id.get(requested_id) if requested_id else by_name.get(name)
            if requested_id and previous is None:
                raise ValueError("Unknown test identity for this assessment; reload before editing.")
            record = deepcopy(previous or {})
            test_id = record.get("test_id") or uuid4().hex
            if test_id in used:
                raise ValueError("Duplicate test identity.")
            used.add(test_id)
            record.update({"test_id": test_id, "assessment_id": assessment_id,
                           "test_name": name, "position": position, "is_final": name == final,
                           "date": assessment.get("test_dates", {}).get(name, ""),
                           "description": assessment.get("test_descriptions", {}).get(name, ""),
                           "question_paper": assessment.get("question_papers", {}).get(name, "")})
            prepared.append(record)
        return prepared

    def replace_tests(self, assessment_id, records):
        others = [r for r in self.repository.get_all() if r["assessment_id"] != assessment_id]
        self.repository.save_all(others + records)

    def delete_test(self, assessment_id, test_id, renumber=False):
        records = [r for r in self.get_tests(assessment_id) if r["test_id"] != test_id]
        number = 0
        for position, record in enumerate(records):
            record["position"] = position
            if renumber and not record["is_final"]:
                number += 1
                record["test_name"] = f"Formative {number}"
        self.replace_tests(assessment_id, records)

    def delete_assessment_tests(self, assessment_id):
        self.replace_tests(assessment_id, [])

    def populate_assessment(self, assessment):
        result = deepcopy(assessment)
        records = self.get_tests(result["assessment_id"])
        result.update({"tests": [r["test_name"] for r in records if not r["is_final"]],
                       "final_test": next((r["test_name"] for r in records if r["is_final"]), ""),
                       "test_ids": {r["test_name"]: r["test_id"] for r in records},
                       "test_dates": {r["test_name"]: r.get("date", "") for r in records},
                       "test_descriptions": {r["test_name"]: r.get("description", "") for r in records},
                       "question_papers": {r["test_name"]: r["question_paper"] for r in records if r.get("question_paper")}})
        return result
