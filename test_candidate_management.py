"""Candidate Management tests use temporary JSON and no credentials/Azure calls."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from backend.repositories.candidate_repository import CandidateRepository
from backend.services.candidate_management_service import CandidateManagementService
from backend.services.candidate_assignment_service import CandidateAssignmentService


class CandidateManagementTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = CandidateRepository(self.root / "candidates.json")
        self.service = CandidateManagementService(self.repo)
        self.assignments = CandidateAssignmentService(self.service)
        self.assessments = self.service.assessments
        self.a = self.assessments.create_assessment({"name": "A", "tests": ["Formative 1"]})
        self.b = self.assessments.create_assessment({"name": "B", "tests": ["Formative 1"]})
        self.tid = self.a["test_ids"]["Formative 1"]

    def create(self, identity="C1", email="one@example.com"):
        return self.service.create_candidate({"candidate_id": identity, "name": " Candidate One ", "email": email})

    def assign(self):
        self.create()
        self.assignments.assign_candidate_to_assessment("C1", self.a["assessment_id"])
        return self.assignments.assign_candidate_to_test("C1", self.tid)

    def test_create_get_list_and_reload(self):
        value = self.create(" C1 ", " ONE@EXAMPLE.COM ")
        self.assertEqual(value["candidate_id"], "C1")
        self.assertEqual(value["name"], "Candidate One")
        self.assertEqual(value["email"], "one@example.com")
        self.assertEqual(value["created_at"], value["updated_at"])
        fresh = CandidateManagementService(CandidateRepository(self.repo.file_path))
        self.assertEqual(fresh.get_candidate("c1"), value)
        self.assertEqual(fresh.list_candidates(), [value])
        self.assertNotIn("password", value)

    def test_duplicate_id_and_email_do_not_overwrite(self):
        self.create(); before = self.repo.file_path.read_bytes()
        for identity, email in (("C1", "different@example.com"), ("c1", "different@example.com"), ("C2", "ONE@example.com")):
            with self.assertRaises(ValueError): self.create(identity, email)
        self.assertEqual(self.repo.file_path.read_bytes(), before)

    def test_invalid_required_fields_and_password_is_hashed(self):
        base = {"candidate_id": "C1", "name": "One", "email": "one@example.com"}
        for field, value in (("candidate_id", " "), ("candidate_id", 3), ("name", ""), ("name", None),
                             ("email", "bad"), ("email", ""), ("email", None)):
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                self.service.create_candidate({**base, field: value})

        with self.assertRaises(ValueError):
            self.service.create_candidate({**base, "password": "short"})

        value = self.service.create_candidate({**base, "password": "secret123"})
        self.assertNotIn("password", value)
        self.assertIn("password_hash", value)
        self.assertTrue(value["password_hash"].startswith("pbkdf2_sha256$"))
        self.assertTrue(
            self.service._verify_password("secret123", value["password_hash"])
        )
        self.assertFalse(
            self.service._verify_password("wrong-password", value["password_hash"])
        )

    def test_update_preserves_identity_and_timestamps(self):
        old = self.create()
        changed = self.service.update_candidate("C1", {"name": " Updated ", "email": "NEW@example.com"})
        self.assertEqual(changed["candidate_id"], "C1")
        self.assertEqual(changed["name"], "Updated")
        self.assertEqual(changed["email"], "new@example.com")
        self.assertEqual(changed["created_at"], old["created_at"])
        self.assertGreaterEqual(changed["updated_at"], old["updated_at"])
        with self.assertRaises(ValueError): self.service.update_candidate("C1", {"candidate_id": "C2"})

    def test_update_preserves_existing_password_and_can_change_it(self):
        self.service.create_candidate({
            "candidate_id": "C1",
            "name": "Candidate One",
            "email": "one@example.com",
            "password": "initial123",
        })

        self.service.update_candidate("C1", {"name": "Updated Candidate"})
        self.assertIsNotNone(self.service.authenticate_candidate("C1", "initial123"))

        with self.assertRaisesRegex(ValueError, "at least 6 characters"):
            self.service.update_candidate("C1", {"password": "short"})

        updated = self.service.update_candidate("C1", {"password": "changed123"})
        self.assertNotIn("password", updated)
        self.assertNotIn("changed123", self.repo.file_path.read_text())
        self.assertIsNone(self.service.authenticate_candidate("C1", "initial123"))
        self.assertIsNotNone(self.service.authenticate_candidate("C1", "changed123"))

    def test_update_duplicate_email_and_missing(self):
        self.create(); self.create("C2", "two@example.com")
        with self.assertRaises(ValueError): self.service.update_candidate("C2", {"email": "ONE@EXAMPLE.COM"})
        for identity in ("unknown", "", None):
            with self.assertRaises(ValueError): self.service.update_candidate(identity, {"name": "New"})
            with self.assertRaises(ValueError): self.service.get_candidate(identity)
            with self.assertRaises(ValueError): self.service.delete_candidate(identity)

    def test_delete_without_dependencies_persists(self):
        self.create(); self.service.delete_candidate("C1")
        self.assertEqual(CandidateManagementService(CandidateRepository(self.repo.file_path)).list_candidates(), [])

    def test_legacy_catalog_overlay_without_credential_migration(self):
        legacy = lambda: [{"emp_id": "L1", "name": "Legacy", "email": "legacy@example.com", "password": "not-copied"}]
        service = CandidateManagementService(self.repo, legacy_catalog=legacy)
        self.assertEqual(service.get_candidate("L1")["name"], "Legacy")
        self.assertEqual(self.repo.get_all(), [])
        service.update_candidate("L1", {"name": "New name"})
        self.assertNotIn("password", self.repo.file_path.read_text())
        service.delete_candidate("L1")
        fresh = CandidateManagementService(CandidateRepository(self.repo.file_path), legacy_catalog=legacy)
        self.assertEqual(fresh.list_candidates(), [])
        self.assertTrue(self.repo.get_all(include_deleted=True)[0]["deleted_at"])

    def test_delete_with_assessment_dependency(self):
        self.create()
        self.assignments.assign_candidate_to_assessment("C1", self.a["assessment_id"])
        with self.assertRaisesRegex(ValueError, "assessment assignments"): self.service.delete_candidate("C1")

    def test_delete_with_test_dependency(self):
        self.assign()
        with self.assertRaises(ValueError): self.service.delete_candidate("C1")
        self.assertEqual(len(self.assignments.list_test_assignments("C1")), 1)

    def test_delete_with_evaluation_and_feedback(self):
        self.create()
        for filename, row in (("manual_evaluations.json", {"candidate_id": "C1"}), ("ai_evaluation_runs.json", {"candidate_ids": ["C1", "C2"]})):
            path = self.root / filename; path.write_text(json.dumps([row]))
            with self.assertRaisesRegex(ValueError, "evaluation data"): self.service.delete_candidate("C1")
            path.unlink()
        folder = self.root / "app_data"; folder.mkdir()
        (folder / "candidate_feedbacks.json").write_text(json.dumps({"A:Formative 1:C1": {}}))
        with self.assertRaisesRegex(ValueError, "feedback data"): self.service.delete_candidate("C1")

    def test_assessment_assignment_validation_and_persistence(self):
        self.create()
        record = self.assignments.assign_candidate_to_assessment("C1", self.a["assessment_id"])
        self.assertEqual(record["assigned_candidates"], ["C1"])
        self.assertEqual(self.assessments.get_assessment(self.a["assessment_id"])["assigned_candidates"], ["C1"])
        with self.assertRaises(ValueError): self.assignments.assign_candidate_to_assessment("C1", self.a["assessment_id"])
        with self.assertRaises(ValueError): self.assignments.assign_candidate_to_assessment("unknown", self.a["assessment_id"])
        with self.assertRaises(ValueError): self.assignments.assign_candidate_to_assessment("C1", "unknown")
        self.assertFalse((self.root / "assessment_candidates.json").exists())

    def test_test_assignment_requires_eligibility_and_unique_pair(self):
        self.create()
        with self.assertRaisesRegex(ValueError, "not assigned to the assessment"):
            self.assignments.assign_candidate_to_test("C1", self.tid)
        with self.assertRaises(ValueError): self.assignments.assign_candidate_to_test("unknown", self.tid)
        with self.assertRaises(ValueError): self.assignments.assign_candidate_to_test("C1", "unknown")
        self.assignments.assign_candidate_to_assessment("C1", self.a["assessment_id"])
        result = self.assignments.assign_candidate_to_test("C1", self.tid)
        self.assertEqual(result["assessment_id"], self.a["assessment_id"])
        self.assertEqual(result["status"], "Assigned")
        self.assertIsNone(result["started_at"]); self.assertIsNone(result["submitted_at"])
        self.assertEqual(self.assignments.assign_candidate_to_test("C1", self.tid), result)
        with self.assertRaises(ValueError): self.assignments.assign_candidate_to_test("C1", self.b["test_ids"]["Formative 1"])

    def test_status_transitions_and_timestamp_preservation(self):
        assigned = self.assign()
        started = self.assignments.update_test_status("C1", self.tid, "In Progress")
        self.assertTrue(started["started_at"]); self.assertIsNone(started["submitted_at"])
        submitted = self.assignments.update_test_status("C1", self.tid, "Submitted")
        self.assertEqual(submitted["started_at"], started["started_at"])
        self.assertEqual(submitted["assigned_at"], assigned["assigned_at"])
        self.assertTrue(submitted["submitted_at"])
        self.assertEqual(self.assignments.update_test_status("C1", self.tid, "Submitted"), submitted)
        fresh = CandidateAssignmentService(CandidateManagementService(CandidateRepository(self.repo.file_path)))
        self.assertEqual(fresh.get_test_assignment("C1", self.tid), submitted)
        for status in ("Assigned", "In Progress", "Disqualified", "bad", None):
            with self.assertRaises(ValueError): self.assignments.update_test_status("C1", self.tid, status)

    def test_disqualified_is_terminal(self):
        self.assign()
        with self.assertRaises(ValueError): self.assignments.update_test_status("C1", self.tid, "Submitted")
        self.assignments.update_test_status("C1", self.tid, "In Progress")
        result = self.assignments.update_test_status("C1", self.tid, "Disqualified")
        self.assertIsNone(result["submitted_at"])
        with self.assertRaises(ValueError): self.assignments.update_test_status("C1", self.tid, "In Progress")

    def test_assignment_dependencies_protect_assessment_but_allow_unstarted_test_delete(self):
        self.assign()

        # A plain "Assigned" test has no candidate attempt yet, so the
        # facilitator may delete it.
        self.assessments.delete_test(
            self.a["assessment_id"],
            self.tid,
        )

        # The test itself must no longer exist.
        with self.assertRaises(ValueError):
            self.assessments.tests.get_test(self.tid)

        # Deleting the test must also remove its candidate assignment.
        self.assertIsNone(
            self.assignments.repository.get("C1", self.tid)
        )

        # Candidate remains assigned to the assessment itself.
        self.assertEqual(
            self.assessments.list_candidates(self.a["assessment_id"]),
            ["C1"],
        )

    def test_started_test_cannot_be_deleted(self):
        self.assign()

        # Once the candidate starts the test, deletion must be blocked.
        self.assignments.update_test_status(
            "C1",
            self.tid,
            "In Progress",
        )

        with self.assertRaises(ValueError):
            self.assessments.delete_test(
                self.a["assessment_id"],
                self.tid,
            )

        # Test must still exist after the rejected deletion.
        existing = self.assessments.tests.get_test(self.tid)
        self.assertEqual(existing["test_id"], self.tid)

        # Candidate assignment must also remain intact.
        assignment = self.assignments.repository.get(
            "C1",
            self.tid,
        )
        self.assertIsNotNone(assignment)
        self.assertEqual(assignment["status"], "In Progress")

    def test_failed_writes_leave_candidates_and_assignments_intact(self):
        self.create(); before = self.repo.file_path.read_bytes()
        with patch("backend.repositories.json_repository.os.replace", side_effect=OSError("disk")):
            with self.assertRaises(OSError): self.service.update_candidate("C1", {"name": "Changed"})
        self.assertEqual(self.repo.file_path.read_bytes(), before)
        self.assignments.assign_candidate_to_assessment("C1", self.a["assessment_id"])
        self.assignments.assign_candidate_to_test("C1", self.tid)
        path = self.service.test_assignments.file_path; before = path.read_bytes()
        with patch("backend.repositories.json_repository.os.replace", side_effect=OSError("disk")):
            with self.assertRaises(OSError): self.assignments.update_test_status("C1", self.tid, "In Progress")
        self.assertEqual(path.read_bytes(), before)

    def test_malformed_candidate_store_not_erased(self):
        for text in ("", "{bad", "{}", "[1]", '[{"candidate_id":"C1"},{"candidate_id":"C1"}]'):
            self.repo.file_path.write_text(text)
            with self.assertRaises(ValueError): self.service.list_candidates()
            with self.assertRaises(ValueError): self.create()
            self.assertEqual(self.repo.file_path.read_text(), text)

    def test_malformed_assignment_store_not_erased(self):
        self.assign()
        path = self.service.test_assignments.file_path
        record = self.service.test_assignments.get_all()[0]
        for text in ("", "{bad", json.dumps([record, record]), json.dumps([{**record, "status": "bad"}])):
            path.write_text(text)
            with self.assertRaises(ValueError): self.assignments.list_test_assignments("C1")
            with self.assertRaises(ValueError): self.assignments.update_test_status("C1", self.tid, "In Progress")
            self.assertEqual(path.read_text(), text)

    def test_response_service_and_old_candidate_wrapper_compatible(self):
        import os
        from backend.services.candidate_service import CandidateService
        from ai_hybrid_evaluator.services.candidate_response_service import save_candidate_response, find_candidate_response_file, get_latest_candidate_response
        self.create()
        self.assertEqual(CandidateService(self.repo).get_candidate("C1")["name"], "Candidate One")
        question = {"id": 1, "title": "Q1", "text": "Question", "marks": 2, "co": "CO1", "lo": "LO1", "knowledge_type": "Fact", "category": "Cognitive", "rbt_level": "Remember"}
        cwd = Path.cwd()
        try:
            os.chdir(self.root)
            save_candidate_response("C1", "Candidate One", "A", "Formative 1", [question], {"1": "Answer"})
            self.assertIsNotNone(find_candidate_response_file(candidate_id="C1", assessment_name="A", test_name="Formative 1", require_assessment_scope=True))
            result = get_latest_candidate_response(candidate_id="C1", assessment_name="A", test_name="Formative 1", require_assessment_scope=True)
            self.assertEqual(result["responses"][0]["response"], "Answer")
            self.assertEqual(get_latest_candidate_response(candidate_id="C1", assessment_name="B", test_name="Formative 1", require_assessment_scope=True), {})
        finally:
            os.chdir(cwd)
        with self.assertRaisesRegex(ValueError, "responses exist"): self.service.delete_candidate("C1")

    def test_candidate_attempt_prevents_deletion(self):
        import sys
        from types import SimpleNamespace
        self.create()
        module = SimpleNamespace(PERSISTED_CANDIDATE_TEST_DATA={"attempt": {"candidate_id": "C1"}})
        with patch.dict(sys.modules, {"ai_hybrid_evaluator.state.candidate_state": module}):
            with self.assertRaisesRegex(ValueError, "test attempt"): self.service.delete_candidate("C1")


if __name__ == "__main__": unittest.main()
