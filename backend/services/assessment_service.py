from copy import deepcopy
from threading import RLock
from uuid import uuid4
from backend.repositories.assessment_repository import AssessmentRepository
from backend.services.test_service import TestService

# Serialize assessment/test read-modify-write operations within the Reflex process.
_PERSISTENCE_LOCK = RLock()
_TEST_FIELDS = {"tests", "final_test", "test_ids", "test_dates", "test_descriptions", "question_papers"}


class AssessmentService:
    """Persistent source of truth, returning the existing assessment UI structure."""

    def __init__(self, repository=None, test_service=None):
        self.repository = repository or AssessmentRepository()
        self.tests = test_service or TestService()

    def load_assessments(self):
        with _PERSISTENCE_LOCK:
            return [self.tests.populate_assessment(r) for r in self.repository.get_all()]

    def load_or_bootstrap(self, initial_assessments):
        with _PERSISTENCE_LOCK:
            if not self.repository.exists():
                # Only first use seeds legacy state. Empty existing JSON means deleted.
                for assessment in initial_assessments:
                    self.save_assessment(assessment)
                if not self.repository.exists():
                    self.repository.save_all([])
            return self.load_assessments()

    def save_assessment(self, assessment):
        with _PERSISTENCE_LOCK:
            value = deepcopy(assessment)
            name = value.get("name", "")
            if not isinstance(name, str) or not name.strip():
                raise ValueError("Assessment name is required.")
            existing = self.repository.get_all()
            identity = value.get("assessment_id")
            if identity and not any(r["assessment_id"] == identity for r in existing):
                raise ValueError("Assessment was deleted or changed; reload before saving.")
            if not identity:
                match = next((r for r in existing if r["name"] == name), None)
                identity = match["assessment_id"] if match else uuid4().hex
            if any(r["name"] == name and r["assessment_id"] != identity for r in existing):
                raise ValueError("An assessment with this name already exists.")
            value["assessment_id"] = identity
            tests = self.tests.prepare_tests(identity, value)
            record = {k: v for k, v in value.items() if k not in _TEST_FIELDS}
            self.tests.replace_tests(identity, tests)
            self.repository.save(record)
            return self.tests.populate_assessment(record)

    def delete_assessment(self, assessment_id):
        with _PERSISTENCE_LOCK:
            self.tests.delete_assessment_tests(assessment_id)
            self.repository.delete(assessment_id)

    def delete_test(self, assessment_id, test_id, renumber=False):
        with _PERSISTENCE_LOCK:
            if self.repository.get_by_id(assessment_id) is None:
                raise ValueError("Assessment no longer exists.")
            self.tests.delete_test(assessment_id, test_id, renumber)
            return self.tests.populate_assessment(self.repository.get_by_id(assessment_id))
