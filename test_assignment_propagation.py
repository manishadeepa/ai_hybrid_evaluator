"""Canonical assignment lifecycle integration; temporary stores only, no Azure."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from backend.repositories.candidate_repository import CandidateRepository
from backend.services.candidate_management_service import CandidateManagementService
from backend.services.candidate_assignment_service import CandidateAssignmentService
from backend.services.response_lifecycle_service import ResponseLifecycleService
from backend.services.question_paper_service import QuestionPaperService
from test_automatic_objective import workbook


class AssignmentPropagationTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.candidates = CandidateManagementService(CandidateRepository(self.root / "candidates.json"))
        for cid in ("C999", "C2"):
            self.candidates.create_candidate({"candidate_id": cid, "name": cid, "email": cid + "@example.com"})
        self.assignments = CandidateAssignmentService(self.candidates)
        self.assessments = self.candidates.assessments
        self.a = self.assessments.create_assessment({"name": "HoQ Objective"})
        self.aid = self.a["assessment_id"]

    def add_test(self):
        a = self.assessments.add_test(self.aid, "Formative 1")
        return a["test_ids"]["Formative 1"]

    def assign(self):
        self.assignments.assign_candidate_to_assessment("C999", self.aid)

    def test_candidate_before_test_creation_and_reload(self):
        self.assign()
        tid = self.add_test()
        fresh = CandidateAssignmentService(CandidateManagementService(CandidateRepository(self.root / "candidates.json")))
        self.assertEqual(fresh.get_test_assignment("c999", tid)["status"], "Assigned")

    def test_candidate_after_test_creation(self):
        tid = self.add_test()
        self.assign()
        self.assertEqual(self.assignments.get_test_assignment("C999", tid)["assessment_id"], self.aid)

    def test_direct_test_service_also_propagates(self):
        self.assign()
        test = self.assessments.tests.create_test(self.aid, {"test_name": "Formative 1"})
        self.assertEqual(self.assignments.get_test_assignment("C999", test["test_id"])["status"], "Assigned")

    def test_objective_start_and_cross_assessment_authorization(self):
        tid = self.add_test(); self.assign()
        papers = QuestionPaperService(self.assessments.tests)
        papers.import_upload(self.aid, tid, "objective.xlsx", workbook())
        lifecycle = ResponseLifecycleService(self.assignments)
        session = lifecycle.start_test("C999", self.aid, tid)
        self.assertEqual(session["test_type"], "objective")
        self.assertEqual(session["questions"][0]["options"]["B"], "Beta")
        with self.assertRaisesRegex(ValueError, "not assigned"):
            lifecycle.start_test("C2", self.aid, tid)
        other = self.assessments.create_assessment({"name": "Other", "tests": ["Formative 1"]})
        other_tid = other["test_ids"]["Formative 1"]
        self.assertNotEqual(tid, other_tid)
        with self.assertRaisesRegex(ValueError, "not assigned"):
            lifecycle.start_test("C999", other["assessment_id"], other_tid)
        with self.assertRaisesRegex(ValueError, "does not belong"):
            lifecycle.start_test("C999", other["assessment_id"], tid)

    def test_removal_revokes_unstarted_assignments(self):
        tid = self.add_test(); self.assign()
        self.assessments.remove_candidate(self.aid, "C999")
        self.assertIsNone(self.assignments.repository.get("C999", tid))
        with self.assertRaisesRegex(ValueError, "not assigned"):
            ResponseLifecycleService(self.assignments).start_test("C999", self.aid, tid)

    def test_attempts_preserved_on_resave_and_removal_rejected(self):
        tid = self.add_test(); self.assign()
        started = self.assignments.update_test_status("C999", tid, "In Progress")
        self.assessments.save_assessment(self.assessments.get_assessment(self.aid))
        self.assertEqual(self.assignments.get_test_assignment("C999", tid), started)
        with self.assertRaisesRegex(ValueError, "attempts exist"):
            self.assessments.remove_candidate(self.aid, "C999")

    def test_legacy_missing_assignment_requires_explicit_save_not_read_or_start(self):
        tid = self.add_test(); self.assign()
        self.assignments.repository.save_all([])  # simulate the pre-fix persisted state
        self.assessments.load_assessments()
        with self.assertRaisesRegex(ValueError, "not assigned to the test"):
            ResponseLifecycleService(self.assignments).start_test("C999", self.aid, tid)
        self.assessments.update_assessment(self.aid, {})
        original = self.assignments.get_test_assignment("C999", tid)
        self.assessments.update_assessment(self.aid, {})
        self.assertEqual(self.assignments.get_test_assignment("C999", tid), original)
        self.assertEqual(len(self.assignments.repository.get_all()), 1)

    def test_legacy_response_status_not_reset_by_backfill(self):
        tid = self.add_test(); self.assign()
        QuestionPaperService(self.assessments.tests).import_upload(self.aid, tid, "objective.xlsx", workbook())
        lifecycle = ResponseLifecycleService(self.assignments)
        lifecycle.start_test("C999", self.aid, tid)
        lifecycle.update_violation_count("C999", self.aid, tid, 3)
        self.assignments.repository.save_all([])
        self.assessments.update_assessment(self.aid, {})
        self.assertEqual(self.assignments.get_test_assignment("C999", tid)["status"], "Disqualified")
        with self.assertRaisesRegex(ValueError, "cannot be restarted"):
            lifecycle.start_test("C999", self.aid, tid)

    def test_assignment_write_failure_rolls_back_membership_and_new_test(self):
        tid = self.add_test()
        with patch("backend.repositories.test_candidate_repository.TestCandidateRepository.save_all", side_effect=OSError("disk")):
            with self.assertRaises(OSError): self.assign()
        self.assertEqual(self.assessments.list_candidates(self.aid), [])
        self.assertIsNone(self.assignments.repository.get("C999", tid))
        self.assign()
        with patch("backend.repositories.test_candidate_repository.TestCandidateRepository.save_all", side_effect=OSError("disk")):
            with self.assertRaises(OSError): self.assessments.add_test(self.aid, "Formative 2")
            with self.assertRaises(OSError): self.assessments.tests.create_test(self.aid, {"test_name": "Formative 3"})
        self.assertEqual(len(self.assessments.list_tests(self.aid)), 1)

    def test_assessment_delete_cleans_only_unstarted_owned_assignments(self):
        tid = self.add_test(); self.assign()
        other = self.assessments.create_assessment({"name": "Other", "tests": ["Formative 1"], "assigned_candidates": ["C999"]})
        self.assessments.delete_assessment(self.aid)
        self.assertIsNone(self.assignments.repository.get("C999", tid))
        self.assertIsNotNone(self.assignments.repository.get("C999", other["test_ids"]["Formative 1"]))

    def test_membership_write_failure_rolls_back_assignment(self):
        tid = self.add_test()
        with patch.object(self.assessments.repository, "save", side_effect=OSError("disk")):
            with self.assertRaises(OSError): self.assign()
        self.assertEqual(self.assessments.list_candidates(self.aid), [])
        self.assertIsNone(self.assignments.repository.get("C999", tid))

    def test_cross_assessment_corrupt_assignment_rejected_without_overwrite(self):
        tid = self.add_test(); self.assign()
        row = self.assignments.get_test_assignment("C999", tid)
        self.assignments.repository.save_all([{**row, "assessment_id": "wrong"}])
        before = self.assignments.repository.file_path.read_bytes()
        with self.assertRaisesRegex(ValueError, "conflicting assessment"):
            self.assessments.update_assessment(self.aid, {})
        self.assertEqual(self.assignments.repository.file_path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
