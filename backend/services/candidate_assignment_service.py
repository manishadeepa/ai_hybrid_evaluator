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
                # Automatic propagation and explicit assignment share an idempotent API.
                return self.get_test_assignment(identity, test_id)
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

    @staticmethod
    def plan_assessment_assignments(assessment, tests, repository):
        """Reconcile canonical membership without granting access on a read/start event.

        Preserve existing attempts; recover status from canonical response snapshots
        when repairing a missing assignment. Never match by display name.
        """
        from backend.repositories.response_repository import ResponseRepository
        aid = assessment["assessment_id"]
        candidates = set(assessment.get("assigned_candidates", []))
        test_ids = {t["test_id"] for t in tests}
        if any(t["assessment_id"] != aid for t in tests):
            raise ValueError("Invalid assessment/test relationship.")
        rows = repository.get_all()
        planned = []
        for row in rows:
            if row["test_id"] in test_ids and row["assessment_id"] != aid:
                raise ValueError("Test assignment has conflicting assessment ownership.")
            if row["assessment_id"] == aid and (row["candidate_id"] not in candidates or row["test_id"] not in test_ids):
                if row["status"] != "Assigned":
                    raise ValueError("Cannot remove assessment assignment because candidate test attempts exist.")
                continue
            planned.append(row)
        responses = ResponseRepository(repository.file_path.parent / "responses.json").get_all()
        snapshots = {(r["candidate_id"], r["test_id"]): r for r in responses if r["assessment_id"] == aid}
        if any(r["candidate_id"] not in candidates or r["test_id"] not in test_ids for r in snapshots.values()):
            raise ValueError("Cannot remove assessment assignment because candidate responses exist.")
        pairs = {(r["candidate_id"], r["test_id"]) for r in planned}
        stamp = datetime.now(timezone.utc).isoformat()
        for test in tests:
            for cid in assessment.get("assigned_candidates", []):
                if (cid, test["test_id"]) in pairs:
                    continue
                response = snapshots.get((cid, test["test_id"]), {})
                planned.append({"candidate_id": cid, "assessment_id": aid, "test_id": test["test_id"],
                    "status": response.get("status", "Assigned"),
                    "assigned_at": response.get("created_at", stamp),
                    "created_at": response.get("created_at", stamp), "updated_at": stamp,
                    "started_at": response.get("started_at"), "submitted_at": response.get("submitted_at")})
        return planned
