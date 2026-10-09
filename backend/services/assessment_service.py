import json
from copy import deepcopy
from datetime import datetime
from threading import RLock
from uuid import uuid4
from backend.repositories.assessment_repository import AssessmentRepository
from backend.services.test_service import TestService

# Serialize assessment/test read-modify-write operations within the Reflex process.
_PERSISTENCE_LOCK = RLock()
_TEST_FIELDS = {"tests", "final_test", "test_ids", "test_dates", "test_descriptions", "question_papers", "test_types", "test_timings"}


class AssessmentService:
    """Persistent source of truth, returning the existing assessment UI structure."""

    def __init__(self, repository=None, test_service=None, facilitator_catalog=None, candidate_catalog=None):
        self.repository = repository or AssessmentRepository()
        self.tests = test_service or TestService()
        self.tests.assessments = self.repository
        self.facilitator_catalog = facilitator_catalog
        self.candidate_catalog = candidate_catalog

    def load_assessments(self):
        with _PERSISTENCE_LOCK:
            assessments = self.repository.get_all()
            if not assessments:
                return []
            tests_by_assessment = {}
            for record in self.tests.repository.get_all():
                tests_by_assessment.setdefault(record["assessment_id"], []).append(record)
            return [self.tests.populate_assessment(
                record, tests_by_assessment.get(record["assessment_id"], [])
            ) for record in assessments]

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
            if not isinstance(assessment, dict):
                raise ValueError("Assessment details must be an object.")
            value = deepcopy(assessment)
            if "assessment_id" in value:
                previous = self.get_assessment(value["assessment_id"])
                value = {**previous, **value}
            name = value.get("name", "")
            if not isinstance(name, str) or not name.strip():
                raise ValueError("Assessment name is required.")
            existing = self.repository.get_all()
            identity = value.get("assessment_id")
            if identity and not any(r["assessment_id"] == identity for r in existing):
                raise ValueError("Assessment was deleted or changed; reload before saving.")
            if not identity:
                identity = uuid4().hex
            name = name.strip()
            value["name"] = name
            if any(r["name"].strip().casefold() == name.casefold() and r["assessment_id"] != identity for r in existing):
                raise ValueError("An assessment with this name already exists.")
            value["assessment_id"] = identity
            self._validate_lifecycle(value)
            for field in ("test_ids", "test_dates", "test_descriptions", "question_papers", "facilitator_approvals", "test_types", "test_timings"):
                if field in value and not isinstance(value[field], dict):
                    raise ValueError(f"{field} must be an object.")
            for field in ("tests", "facilitator_ids", "assigned_candidates"):
                if field in value:
                    self._unique_ids(value[field], field)
            if not isinstance(value.get("final_test", ""), str):
                raise ValueError("final_test must be a string.")
            tests = self.tests.prepare_tests(identity, value)
            record = {k: v for k, v in value.items() if k not in _TEST_FIELDS}
            # Validate serialization before either store changes.
            try:
                json.dumps([record, *tests], allow_nan=False)
            except (TypeError, ValueError) as exc:
                raise ValueError("Assessment details must contain valid JSON values.") from exc
            from backend.repositories.test_candidate_repository import TestCandidateRepository
            from backend.services.candidate_assignment_service import CandidateAssignmentService
            assignments = TestCandidateRepository(self.repository.file_path.parent / "test_candidates.json")
            previous_assignments = assignments.get_all()
            planned = CandidateAssignmentService.plan_assessment_assignments(record, tests, assignments)
            previous_tests = self.tests.repository.get_all()
            self.tests.replace_tests(identity, tests)
            try:
                if planned != previous_assignments:
                    assignments.save_all(planned)
                self.repository.save(record)
            except (ValueError, OSError):
                self.tests.repository.save_all(previous_tests)
                if assignments.get_all() != previous_assignments:
                    assignments.save_all(previous_assignments)
                raise
            return self.tests.populate_assessment(record)

    def delete_assessment(self, assessment_id):
        with _PERSISTENCE_LOCK:
            self._require_id(assessment_id)
            if self.repository.get_by_id(assessment_id) is None:
                return False
            from backend.repositories.test_candidate_repository import TestCandidateRepository
            from backend.services.candidate_assignment_service import CandidateAssignmentService
            assignments = TestCandidateRepository(self.repository.file_path.parent / "test_candidates.json")
            previous_assignments = assignments.get_all()
            planned = CandidateAssignmentService.plan_assessment_assignments(
                {"assessment_id": assessment_id, "assigned_candidates": []}, [], assignments)
            for test in self.tests.get_tests(assessment_id):
                self.tests.dependencies.ensure_mutable(test, self.repository.get_by_id(assessment_id))
            previous_tests = self.tests.repository.get_all()
            self.tests.delete_assessment_tests(assessment_id)
            try:
                if planned != previous_assignments:
                    assignments.save_all(planned)
                self.repository.delete(assessment_id)
            except (ValueError, OSError):
                self.tests.repository.save_all(previous_tests)
                if assignments.get_all() != previous_assignments:
                    assignments.save_all(previous_assignments)
                raise
            return True

    def delete_test(self, assessment_id, test_id, renumber=False):
        with _PERSISTENCE_LOCK:
            if self.repository.get_by_id(assessment_id) is None:
                raise ValueError("Assessment no longer exists.")
            self.get_test(assessment_id, test_id)
            self.tests.delete_test(assessment_id, test_id, renumber)
            return self.tests.populate_assessment(self.repository.get_by_id(assessment_id))

    @staticmethod
    def _require_id(assessment_id):
        if not isinstance(assessment_id, str) or not assessment_id.strip():
            raise ValueError("Assessment ID is required.")

    def get_assessment(self, assessment_id):
        self._require_id(assessment_id)
        with _PERSISTENCE_LOCK:
            record = self.repository.get_by_id(assessment_id)
            if record is None:
                raise ValueError("Assessment does not exist; reload before saving.")
            return self.tests.populate_assessment(record)

    def create_assessment(self, details):
        if not isinstance(details, dict) or "assessment_id" in details:
            raise ValueError("New assessment details must not specify an assessment ID.")
        return self.save_assessment(self.validate_assignments(details))

    def update_assessment(self, assessment_id, changes):
        self._require_id(assessment_id)
        if not isinstance(changes, dict):
            raise ValueError("Assessment changes must be an object.")
        if "assessment_id" in changes and changes["assessment_id"] != assessment_id:
            raise ValueError("Assessment ID cannot be changed.")
        with _PERSISTENCE_LOCK:
            previous = self.get_assessment(assessment_id)
            changes = deepcopy(changes)
            for field in ("test_dates", "test_descriptions", "question_papers", "test_types"):
                if field in changes:
                    if not isinstance(changes[field], dict):
                        raise ValueError(f"{field} must be an object.")
                    changes[field] = {**previous.get(field, {}), **changes[field]}
            # Preserve approvals for retained facilitators when only IDs are supplied.
            if "facilitator_ids" in changes and "facilitator_approvals" not in changes:
                changes = {**changes, "facilitator_approvals": previous.get("facilitator_approvals", {})}
            return self.save_assessment({**self.validate_assignments(changes), "assessment_id": assessment_id})

    def _facilitators(self):
        if self.facilitator_catalog is not None:
            return self.facilitator_catalog()
        # Existing facilitator directory is in memory; authentication is not involved.
        from ai_hybrid_evaluator.models.models import SHARED_FACILITATORS
        return SHARED_FACILITATORS

    @staticmethod
    def _unique_ids(values, label):
        if not isinstance(values, list) or any(not isinstance(i, str) or not i.strip() for i in values):
            raise ValueError(f"{label} IDs must be a list of nonempty strings.")
        if len(values) != len(set(values)):
            raise ValueError(f"Duplicate {label} assignment.")
        return list(values)

    def _facilitator_fields(self, record, ids):
        ids = self._unique_ids(ids, "facilitator")
        directory = {f["emp_id"]: f for f in self._facilitators()}
        if any(identity not in directory for identity in ids):
            raise ValueError("Selected facilitator does not exist.")
        names = [directory[identity]["name"] for identity in ids]
        return {"facilitator_ids": ids, "facilitator_names": names,
                "facilitator_id": ids[0] if ids else "", "facilitator_name": names[0] if names else "",
                "facilitator_approvals": {identity: record.get("facilitator_approvals", {}).get(identity, "pending") for identity in ids}}

    def assign_facilitator(self, assessment_id, facilitator_id):
        with _PERSISTENCE_LOCK:
            record = self.get_assessment(assessment_id)
            ids = list(record.get("facilitator_ids", [record["facilitator_id"]] if record.get("facilitator_id") else []))
            if facilitator_id in ids:
                raise ValueError("Facilitator is already assigned.")
            return self.update_assessment(assessment_id, self._facilitator_fields(record, ids + [facilitator_id]))

    def remove_facilitator(self, assessment_id, facilitator_id):
        with _PERSISTENCE_LOCK:
            record = self.get_assessment(assessment_id)
            ids = [f["emp_id"] for f in self.list_facilitators(assessment_id)]
            if facilitator_id not in ids:
                raise ValueError("Facilitator is not assigned to this assessment.")
            return self.update_assessment(assessment_id, self._facilitator_fields(record, [i for i in ids if i != facilitator_id]))

    def list_facilitators(self, assessment_id):
        record = self.get_assessment(assessment_id)
        ids = record.get("facilitator_ids", [record["facilitator_id"]] if record.get("facilitator_id") else [])
        names = record.get("facilitator_names", [record.get("facilitator_name", "")])
        return [{"emp_id": identity, "name": names[n] if n < len(names) else ""} for n, identity in enumerate(ids)]

    def _candidates(self):
        if self.candidate_catalog is not None:
            return self.candidate_catalog()
        from backend.services.candidate_management_service import CandidateManagementService
        return CandidateManagementService().list_candidates()

    def _candidate_ids(self, ids):
        ids = self._unique_ids(ids, "candidate")
        known = {str(c.get("emp_id") or c.get("candidate_id")) for c in self._candidates()}
        if any(identity not in known for identity in ids):
            raise ValueError("Selected candidate does not exist.")
        return ids

    def validate_assignments(self, details):
        """Validate explicitly supplied relationships; preserve omitted legacy data."""
        value = deepcopy(details)
        if "facilitator_id" in value and "facilitator_ids" not in value:
            value["facilitator_ids"] = [value["facilitator_id"]] if value["facilitator_id"] else []
        if "facilitator_ids" in value:
            value.update(self._facilitator_fields(value, value["facilitator_ids"]))
        if "assigned_candidates" in value:
            value["assigned_candidates"] = self._candidate_ids(value["assigned_candidates"])
        return value

    def assign_candidate(self, assessment_id, candidate_id):
        with _PERSISTENCE_LOCK:
            ids = self.list_candidates(assessment_id)
            if candidate_id in ids:
                raise ValueError("Candidate is already assigned.")
            return self.update_assessment(assessment_id, {"assigned_candidates": ids + [candidate_id]})

    def remove_candidate(self, assessment_id, candidate_id):
        with _PERSISTENCE_LOCK:
            ids = self.list_candidates(assessment_id)
            if candidate_id not in ids:
                raise ValueError("Candidate is not assigned to this assessment.")
            return self.update_assessment(assessment_id, {"assigned_candidates": [i for i in ids if i != candidate_id]})

    def list_candidates(self, assessment_id):
        return list(self.get_assessment(assessment_id).get("assigned_candidates", []))

    @staticmethod
    def _validate_lifecycle(value):
        statuses = {"Draft", "Scheduled", "In Progress", "Pending", "Active", "Completed"}
        if not isinstance(value.get("status", "Draft"), str) or value.get("status", "Draft") not in statuses:
            raise ValueError("Status must be Draft, Scheduled, In Progress, Pending, Active or Completed.")
        value.setdefault("status", "Draft")
        for field in ("start_date", "end_date"):
            raw = value.get(field, "")
            if not isinstance(raw, str):
                raise ValueError(f"{field} must be a date string or empty.")
            if not raw:
                continue
            for fmt in ("%Y-%m-%d", "%d %b %Y"):
                try:
                    value[field] = datetime.strptime(raw, fmt).date().isoformat()
                    break
                except ValueError:
                    pass
            else:
                raise ValueError(f"Invalid {field}; use YYYY-MM-DD.")
        if value.get("start_date") and value.get("end_date") and value["end_date"] < value["start_date"]:
            raise ValueError("End date cannot precede start date.")

    def update_lifecycle(self, assessment_id, **changes):
        if set(changes) - {"status", "start_date", "end_date"}:
            raise ValueError("Only status, start_date and end_date are lifecycle fields.")
        return self.update_assessment(assessment_id, changes)

    def list_tests(self, assessment_id):
        self.get_assessment(assessment_id)
        return self.tests.get_tests(assessment_id)

    def get_test(self, assessment_id, test_id):
        if not isinstance(test_id, str) or not test_id.strip():
            raise ValueError("Test ID is required.")
        for test in self.list_tests(assessment_id):
            if test["test_id"] == test_id:
                return test
        raise ValueError("Test does not belong to this assessment or does not exist.")

    def add_test(self, assessment_id, test_name, *, date="", description="", is_final=False, test_type=None,
                 start_time="", end_time=""):
        """Existing workflow creates owned tests; it never moves another assessment's test."""
        with _PERSISTENCE_LOCK:
            self.tests._validate_fields({"test_name": test_name, "date": date,
                                         "description": description, "is_final": is_final})
            record = self.get_assessment(assessment_id)
            if not isinstance(test_name, str) or not test_name.strip():
                raise ValueError("Test name is required.")
            test_name = test_name.strip()
            if any(t["test_name"].casefold() == test_name.casefold() for t in self.list_tests(assessment_id)):
                raise ValueError("Test is already associated with this assessment.")
            if not isinstance(is_final, bool) or not isinstance(date, str) or not isinstance(description, str):
                raise ValueError("Invalid test relationship details.")
            if is_final:
                if record.get("final_test"):
                    raise ValueError("Assessment already has a final test.")
                record["final_test"] = test_name
            else:
                record["tests"].append(test_name)
            record["test_dates"][test_name] = date
            record["test_descriptions"][test_name] = description
            if test_type is not None:
                record.setdefault("test_types", {})[test_name] = test_type
            # Persist start/end time so the candidate timer can be derived from the wall clock.
            if start_time or end_time:
                record.setdefault("test_timings", {})[test_name] = {
                    "start_time": start_time,
                    "end_time": end_time,
                }
            return self.save_assessment(record)

    def update_test(self, assessment_id, test_id, changes):
        with _PERSISTENCE_LOCK:
            self.get_test(assessment_id, test_id)
            self.tests.update_test(test_id, changes)
            return self.get_assessment(assessment_id)
