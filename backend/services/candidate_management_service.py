from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import re
from backend.repositories.candidate_repository import CandidateRepository
from backend.repositories.assessment_repository import AssessmentRepository
from backend.repositories.test_repository import TestRepository
from backend.repositories.test_candidate_repository import TestCandidateRepository
from backend.services.assessment_service import AssessmentService, _PERSISTENCE_LOCK
from backend.services.test_service import TestService
from backend.services.candidate_dependency_service import CandidateDependencyService


class CandidateManagementService:
    """Candidate identity CRUD, independent of credentials and test-taking state."""
    def __init__(self, repository=None, legacy_catalog=None, assessments=None, upload_dir=None, app_data_dir=None):
        production = repository is None
        self.repository = repository or CandidateRepository()
        self.data_dir = self.repository.file_path.parent
        self.legacy_catalog = legacy_catalog if legacy_catalog is not None else (self._shared_candidates if production else lambda: [])
        self.assessments = assessments or AssessmentService(AssessmentRepository(self.data_dir / "assessments.json"),
            TestService(TestRepository(self.data_dir / "tests.json")), candidate_catalog=self.list_candidates)
        self.assessments.candidate_catalog = self.list_candidates
        self.test_assignments = TestCandidateRepository(self.data_dir / "test_candidates.json")
        project = Path(__file__).resolve().parents[2]
        self.dependencies = CandidateDependencyService(self.data_dir,
            upload_dir or (project / "uploaded_files" if production else self.data_dir / "uploaded_files"),
            app_data_dir or (project / "ai_hybrid_evaluator" / "data" if production else self.data_dir / "app_data"))

    @staticmethod
    def _shared_candidates():
        from ai_hybrid_evaluator.models.models import SHARED_CANDIDATES
        return [{"candidate_id": c["emp_id"], "name": c["name"], "email": c["email"]} for c in SHARED_CANDIDATES]

    @staticmethod
    def _identity(value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Candidate ID is required.")
        return value.strip()

    @classmethod
    def _clean(cls, details):
        value = deepcopy(details)
        value["candidate_id"] = cls._identity(value.get("candidate_id"))
        if not isinstance(value.get("name"), str) or not value["name"].strip():
            raise ValueError("Candidate name is required.")
        value["name"] = value["name"].strip()
        email = value.get("email")
        if not isinstance(email, str) or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email.strip()):
            raise ValueError("Enter a valid candidate email address.")
        value["email"] = email.strip().lower()
        return value

    @staticmethod
    def _fields(details):
        if not isinstance(details, dict) or set(details) - {"candidate_id", "name", "email"}:
            raise ValueError("Candidate details support only candidate_id, name and email; credentials are not managed here.")

    def list_candidates(self):
        legacy = {self._identity(c.get("candidate_id", c.get("emp_id"))):
                  {"candidate_id": self._identity(c.get("candidate_id", c.get("emp_id"))), "name": c["name"], "email": c["email"]}
                  for c in self.legacy_catalog()}
        for row in self.repository.get_all(include_deleted=True):
            if row.get("deleted_at"):
                legacy.pop(row["candidate_id"], None)
            else:
                legacy[row["candidate_id"]] = {k: v for k, v in row.items() if k in {"candidate_id", "name", "email", "created_at", "updated_at"}}
        return [deepcopy(v) for v in legacy.values()]

    def get_candidate(self, candidate_id):
        identity = self._identity(candidate_id)
        result = next((r for r in self.list_candidates() if r["candidate_id"].casefold() == identity.casefold()), None)
        if result is None:
            raise ValueError("Candidate not found.")
        return result

    def _unique_email(self, value):
        if any(r["candidate_id"] != value["candidate_id"] and r["email"].strip().casefold() == value["email"].casefold() for r in self.list_candidates()):
            raise ValueError("Email already exists for another candidate.")

    def create_candidate(self, details):
        with _PERSISTENCE_LOCK:
            self._fields(details)
            value = self._clean(details)
            identities = {r["candidate_id"] for r in self.list_candidates()} | {r["candidate_id"] for r in self.repository.get_all(include_deleted=True)}
            if value["candidate_id"].casefold() in {i.casefold() for i in identities}:
                raise ValueError("Candidate ID already exists.")
            self._unique_email(value)
            stamp = datetime.now(timezone.utc).isoformat()
            return self.repository.save({**value, "created_at": stamp, "updated_at": stamp})

    def update_candidate(self, candidate_id, changes):
        with _PERSISTENCE_LOCK:
            self._fields(changes)
            old = self.get_candidate(candidate_id)
            if "candidate_id" in changes and self._identity(changes["candidate_id"]) != old["candidate_id"]:
                raise ValueError("Candidate ID cannot be changed.")
            value = self._clean({**old, **changes})
            self._unique_email(value)
            stamp = datetime.now(timezone.utc).isoformat()
            value.setdefault("created_at", stamp)
            value["updated_at"] = stamp
            return self.repository.save(value)

    def delete_candidate(self, candidate_id):
        with _PERSISTENCE_LOCK:
            candidate = self.get_candidate(candidate_id)
            self.dependencies.ensure_deletable(candidate, self.assessments.repository.get_all(), self.test_assignments.get_all())
            if any(self._identity(c.get("candidate_id", c.get("emp_id"))) == candidate["candidate_id"] for c in self.legacy_catalog()):
                # Persist a removal marker so the legacy in-memory seed cannot resurrect it.
                self.repository.save({**candidate, "deleted_at": datetime.now(timezone.utc).isoformat()})
            else:
                self.repository.delete(candidate["candidate_id"])
            return candidate
