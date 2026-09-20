from datetime import datetime, timezone
from backend.services.assessment_service import _PERSISTENCE_LOCK
from backend.services.candidate_management_service import CandidateManagementService


class CandidateAssignmentService:
    """Reuse assessment assignments; persist explicit test assignment/status separately."""
    def __init__(self, candidates=None):
        self.candidates = candidates or CandidateManagementService()
        self.assessments = self.candidates.assessments
        self.repository = self.candidates.test_assignments

    def assign_candidate_to_assessment(self, candidate_id, assessment_id):
        with _PERSISTENCE_LOCK:
            candidate = self.candidates.get_candidate(candidate_id)
            return self.assessments.assign_candidate(assessment_id, candidate["candidate_id"])

    def _eligible(self, candidate_id, test_id):
        candidate = self.candidates.get_candidate(candidate_id)
        test = self.assessments.tests.get_test(test_id)
        if candidate["candidate_id"] not in self.assessments.list_candidates(test["assessment_id"]):
            raise ValueError("Candidate is not assigned to the assessment.")
        return candidate, test

    def assign_candidate_to_test(self, candidate_id, test_id):
        with _PERSISTENCE_LOCK:
            candidate, test = self._eligible(candidate_id, test_id)
            identity = candidate["candidate_id"]
            if self.repository.get(identity, test_id):
                raise ValueError("Candidate already assigned to this test.")
            stamp = datetime.now(timezone.utc).isoformat()
            return self.repository.save({"candidate_id": identity, "test_id": test_id, "assessment_id": test["assessment_id"],
                "status": "Assigned", "assigned_at": stamp, "created_at": stamp, "updated_at": stamp,
                "started_at": None, "submitted_at": None})

    def get_test_assignment(self, candidate_id, test_id):
        candidate, test = self._eligible(candidate_id, test_id)
        record = self.repository.get(candidate["candidate_id"], test_id)
        if record is None:
            raise ValueError("Candidate is not assigned to the test.")
        if record["assessment_id"] != test["assessment_id"]:
            raise ValueError("Test does not belong to the assigned assessment.")
        return record

    def list_test_assignments(self, candidate_id):
        candidate = self.candidates.get_candidate(candidate_id)
        return [r for r in self.repository.get_all() if r["candidate_id"] == candidate["candidate_id"]]

    def update_test_status(self, candidate_id, test_id, status):
        with _PERSISTENCE_LOCK:
            record = self.get_test_assignment(candidate_id, test_id)
            transitions = {"Assigned": {"In Progress"}, "In Progress": {"Submitted", "Disqualified"}, "Submitted": set(), "Disqualified": set()}
            if status == record["status"]:
                return record
            if not isinstance(status, str) or status not in transitions[record["status"]]:
                raise ValueError("Invalid candidate status transition.")
            stamp = datetime.now(timezone.utc).isoformat()
            record["status"] = status
            record["updated_at"] = stamp
            if status == "In Progress": record["started_at"] = stamp
            if status == "Submitted": record["submitted_at"] = stamp
            return self.repository.save(record)
