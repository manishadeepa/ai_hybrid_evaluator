"""Test business rules with temporary stores; no Azure or production data writes."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from backend.repositories.assessment_repository import AssessmentRepository
from backend.repositories.test_repository import TestRepository
from backend.services.assessment_service import AssessmentService
from backend.services.test_service import TestService


class TestManagementTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = TestRepository(self.root / "tests.json")
        self.service = TestService(self.repo)
        self.assessments = AssessmentService(AssessmentRepository(self.root / "assessments.json"), self.service)
        self.a = self.assessments.create_assessment({"name": "First"})["assessment_id"]
        self.b = self.assessments.create_assessment({"name": "Second"})["assessment_id"]

    def create(self, **details):
        return self.service.create_test(self.a, {"test_name": "Formative 1", **details})

    def test_crud_and_reload(self):
        first = self.create(description="keep", date="2099-09-20")
        other = self.service.create_test(self.b, {"test_name": "Formative 1"})
        fresh = TestService(TestRepository(self.repo.file_path))
        self.assertEqual(fresh.get_test(first["test_id"]), first)
        self.assertEqual(len(fresh.list_tests()), 2)
        self.assertEqual(fresh.list_tests(self.a), [first])
        changed = fresh.update_test(first["test_id"], {"status": "Active"})
        self.assertEqual(changed["description"], "keep")
        self.assertEqual(changed["created_at"], first["created_at"])
        self.assertGreaterEqual(changed["updated_at"], first["updated_at"])
        self.assertEqual(fresh.get_assessment(first["test_id"])["assessment_id"], self.a)
        fresh.delete_test(self.a, first["test_id"])
        self.assertEqual(fresh.list_tests(), [other])
        with self.assertRaisesRegex(ValueError, "not found"):
            fresh.get_test(first["test_id"])

    def test_past_dates_rejected_by_all_test_service_write_paths(self):
        with self.assertRaisesRegex(ValueError, "cannot be earlier than today"):
            self.create(date="2026-09-20")

        first = self.create()
        before = self.repo.file_path.read_bytes()
        with self.assertRaisesRegex(ValueError, "cannot be earlier than today"):
            self.service.update_test(first["test_id"], {"date": "20 Sep 2026"})
        self.assertEqual(self.repo.file_path.read_bytes(), before)

        assessment = self.assessments.get_assessment(self.a)
        assessment["tests"].append("Past Formative")
        assessment["test_dates"]["Past Formative"] = "2026-09-20"
        with self.assertRaisesRegex(ValueError, "cannot be earlier than today"):
            self.assessments.save_assessment(assessment)
        self.assertEqual(self.repo.file_path.read_bytes(), before)

    def test_required_fields_and_missing_records(self):
        for aid in (None, "", "missing"):
            with self.subTest(aid=aid), self.assertRaises(ValueError):
                self.service.create_test(aid, {"test_name": "Name"})
        for details in ({}, {"test_name": " "}, {"test_name": 3}, {"test_name": "X", "test_id": ""}):
            with self.subTest(details=details), self.assertRaises(ValueError):
                self.service.create_test(self.a, details)
        for identity in (None, "", "missing"):
            with self.assertRaises(ValueError): self.service.get_test(identity)
            with self.assertRaises(ValueError): self.service.update_test(identity, {})
            with self.assertRaises(ValueError): self.service.delete_test(self.a, identity)
        with self.assertRaises(ValueError): self.service.list_tests("missing")

    def test_duplicate_identity_name_and_final(self):
        first = self.create(test_id="stable")
        for details in ({"test_name": "Other", "test_id": "stable"}, {"test_name": " formative 1 "}):
            with self.assertRaises(ValueError): self.service.create_test(self.a, details)
        final = self.create(test_name="Final Assessment", is_final=True)
        with self.assertRaises(ValueError): self.create(test_name="Other final", is_final=True)
        with self.assertRaises(ValueError): self.service.update_test(final["test_id"], {"test_name": first["test_name"]})
        with self.assertRaises(ValueError): self.service.update_test(first["test_id"], {"is_final": True})

    def test_immutable_relationship_and_scoped_resolution(self):
        first = self.create()
        for changes in ({"assessment_id": self.b}, {"test_id": "new"}):
            with self.assertRaises(ValueError): self.service.update_test(first["test_id"], changes)
        with self.assertRaises(ValueError): self.service.get_test(first["test_id"], self.b)
        with self.assertRaises(ValueError): self.service.delete_test(self.b, first["test_id"])
        with self.assertRaises(ValueError): self.create(assessment_id=self.b)
        self.assertEqual(self.assessments.get_test(self.a, first["test_id"])["test_name"], "Formative 1")
        self.assertEqual(self.assessments.get_assessment(self.a)["test_ids"], {"Formative 1": first["test_id"]})

    def test_status_dates_and_unsupported_settings(self):
        first = self.create()
        for status in ("Draft", "Scheduled", "Active", "Completed"):
            self.assertEqual(self.service.update_test(first["test_id"], {"status": status})["status"], status)
        for changes in ({"status": "bad"}, {"status": None}, {"date": "tomorrow"}, {"date": "2026-02-30"}, {"date": "2026-09-20"},
                        {"date": 2}, {"is_final": "yes"}, {"description": []}, {"availability": "bad"},
                        {"duration": -1}, {"start_date": "2026-09-20", "end_date": "2026-09-19"}):
            before = self.repo.file_path.read_bytes()
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.service.update_test(first["test_id"], changes)
            self.assertEqual(self.repo.file_path.read_bytes(), before)
        for date in ("", "2099-09-20", "20 Sep 2099"):
            self.assertEqual(self.service.update_test(first["test_id"], {"date": date})["date"], date)

    def test_availability_follows_existing_paper_association(self):
        first = self.create()
        self.assertFalse(self.service.get_availability(first["test_id"]))
        self.service.update_test(first["test_id"], {"question_paper": "paper.xlsx"})
        self.assertTrue(self.service.get_availability(first["test_id"]))

    def test_legacy_optional_fields_and_date_preserved(self):
        row = {"test_id": "old", "assessment_id": self.a, "test_name": "Legacy", "date": "old free text", "extra": "keep"}
        self.repo.save_all([row])
        self.assertEqual(self.service.get_test("old")["status"], "Draft")
        self.assertEqual(self.assessments.get_assessment(self.a)["tests"], ["Legacy"])
        changed = self.service.update_test("old", {"description": "new"})
        self.assertEqual(changed["date"], "old free text")
        self.assertEqual(changed["extra"], "keep")

    def test_corrupt_store_is_not_erased(self):
        for text in ("", "{", "{}", "[1]", '[{"test_id":"x"},{"test_id":"x"}]'):
            self.repo.file_path.write_text(text)
            with self.assertRaises(ValueError): self.repo.get_all()
            with self.assertRaises(ValueError): self.repo.save_all([])
            self.assertEqual(self.repo.file_path.read_text(), text)

    def test_repository_duplicate_ids_and_relationship_rejected(self):
        first = self.create()
        before = self.repo.file_path.read_bytes()
        for rows in ([first, first], [{**first, "assessment_id": ""}], [{**first, "is_final": "false"}]):
            with self.assertRaises(ValueError): self.repo.save_all(rows)
            self.assertEqual(self.repo.file_path.read_bytes(), before)
        with self.assertRaises(ValueError): self.service.replace_tests(self.b, [first])

    def test_failed_atomic_update_preserves_data(self):
        first = self.create()
        before = self.repo.file_path.read_bytes()
        with patch("backend.repositories.json_repository.os.replace", side_effect=OSError("disk failure")):
            with self.assertRaises(OSError): self.service.update_test(first["test_id"], {"description": "change"})
        self.assertEqual(self.repo.file_path.read_bytes(), before)

    def test_question_paper_alone_does_not_block_delete_or_rename(self):
        first = self.create(question_paper="paper.xlsx")
        uploads = self.root / "uploaded_files"
        uploads.mkdir()
        (uploads / "paper.xlsx").write_bytes(b"paper")

        # A question paper alone must not prevent renaming.
        updated = self.service.update_test(
            first["test_id"],
            {"test_name": "Renamed"},
        )
        self.assertEqual(updated["test_name"], "Renamed")

        # A question paper alone must not prevent deletion.
        self.service.delete_test(self.a, first["test_id"])
        with self.assertRaisesRegex(ValueError, "Test not found"):
            self.service.get_test(first["test_id"])

    def test_saved_evaluations_block_removal_and_bulk_bypass(self):
        first = self.create()
        for filename, record in [("manual_evaluations.json", {"assessment_name": "First", "test_name": first["test_name"]}),
                                 ("ai_evaluation_runs.json", {"test_id": first["test_id"], "status": "paused"})]:
            path = self.root / filename; path.write_text(json.dumps([record]))
            with self.assertRaisesRegex(ValueError, "dependent data"): self.service.delete_test(self.a, first["test_id"])
            assessment = self.assessments.get_assessment(self.a)
            assessment["tests"] = []
            with self.assertRaisesRegex(ValueError, "dependent data"): self.assessments.save_assessment(assessment)
            path.unlink()

    def test_response_scope_and_legacy_safety(self):
        import pandas as pd
        first = self.create()
        folder = self.root / "uploaded_files" / "candidate_responses"; folder.mkdir(parents=True)
        path = folder / "C1_Formative_1_Response.xlsx"
        with pd.ExcelWriter(path) as writer:
            pd.DataFrame([{"Candidate Answer": "answer"}]).to_excel(writer, index=False, sheet_name="Responses")
            pd.DataFrame([{"assessment_name": "First", "test_name": "Formative 1", "candidate_id": "C1"}]).to_excel(writer, index=False, sheet_name="Submission")
        with self.assertRaisesRegex(ValueError, "candidate response"): self.service.delete_test(self.a, first["test_id"])
        other = self.service.create_test(self.b, {"test_name": "Formative 1"})
        self.service.delete_test(self.b, other["test_id"])
        pd.DataFrame([{"Candidate Answer": "legacy"}]).to_excel(path, index=False)
        with self.assertRaisesRegex(ValueError, "legacy response"): self.service.delete_test(self.a, first["test_id"])

    def test_renumber_cannot_break_survivor_dependencies(self):
        first = self.create()
        second = self.create(test_name="Formative 2")
        (self.root / "ai_evaluation_runs.json").write_text(json.dumps([{"test_id": second["test_id"]}]))
        with self.assertRaises(ValueError): self.service.delete_test(self.a, first["test_id"], renumber=True)
        self.assertEqual(len(self.service.list_tests(self.a)), 2)
        self.service.delete_test(self.a, first["test_id"], renumber=False)
        self.assertEqual(self.service.get_test(second["test_id"])["test_name"], "Formative 2")

    def test_admin_date_and_facilitator_delete_surface_validation(self):
        from test_assessment_persistence import PersistenceTests
        harness = PersistenceTests()
        harness.service = self.assessments
        admin, fac = harness.harnesses()
        admin._load_persisted_assessments()
        first = self.create()
        admin._apply_assessment_records(self.assessments.load_assessments())
        admin.selected_tests_assessment_index = 0
        error = admin.set_test_date("Formative 1", "bad date")
        self.assertIn("Invalid test date", error[0])
        past_error = admin.set_test_date("Formative 1", "2026-09-20")
        self.assertIn("cannot be earlier than today", past_error[0])
        self.assertEqual(self.service.get_test(first["test_id"])["date"], "")
        admin.set_test_date("Formative 1", "2099-09-20")
        self.assertEqual(self.service.get_test(first["test_id"])["date"], "2099-09-20")
        (self.root / "manual_evaluations.json").write_text(json.dumps([{"assessment_name": "First", "test_name": "Formative 1"}]))
        fac.selected_assessment_name = "First"
        import asyncio
        error = asyncio.run(fac.facilitator_remove_test("Formative 1"))
        self.assertIn("dependent data", error[0])
        self.assertIsNotNone(self.service.get_test(first["test_id"]))


    def test_missing_store_and_invalid_status_record(self):
        new = TestRepository(self.root / "new" / "tests.json")
        self.assertEqual(new.get_all(), [])
        first = self.create()
        with self.assertRaises(ValueError): self.repo.save_all([{**first, "status": "corrupt"}])

    def test_unreadable_dependencies_fail_closed(self):
        first = self.create()
        path = self.root / "manual_evaluations.json"
        path.write_text("{bad")
        with self.assertRaises(ValueError): self.service.delete_test(self.a, first["test_id"])
        self.assertIsNotNone(self.service.get_test(first["test_id"]))

    def test_current_candidate_attempt_prevents_delete(self):
        import sys
        from types import SimpleNamespace
        first = self.create()
        module = SimpleNamespace(PERSISTED_CANDIDATE_TEST_DATA={"attempt": {
            "assessment_name": "First", "test_name": "Formative 1", "status": "In Progress"}})
        with patch.dict(sys.modules, {"ai_hybrid_evaluator.state.candidate_state": module}):
            with self.assertRaisesRegex(ValueError, "candidate attempt"):
                self.service.delete_test(self.a, first["test_id"])

    def test_response_lookup_and_manual_evaluation_keep_scope(self):
        import os
        from ai_hybrid_evaluator.services.candidate_response_service import save_candidate_response, get_latest_candidate_response
        from backend.services.manual_evaluation_service import ManualEvaluationService
        from backend.repositories.json_repository import JSONRepository
        first = self.create()
        assessment = self.service.get_assessment(first["test_id"])
        question = {"id": 1, "title": "Q1", "text": "Question", "marks": 2,
                    "co": "CO1", "lo": "LO1", "knowledge_type": "Conceptual", "category": "Cognitive", "rbt_level": "Understand"}
        cwd = Path.cwd()
        try:
            os.chdir(self.root)
            save_candidate_response("C1", "Candidate", assessment["name"], first["test_name"], [question], {"1": "answer"})
            loaded = get_latest_candidate_response(candidate_id="C1", assessment_name="First", test_name="Formative 1", require_assessment_scope=True)
            wrong = get_latest_candidate_response(candidate_id="C1", assessment_name="Second", test_name="Formative 1", require_assessment_scope=True)
        finally:
            os.chdir(cwd)
        self.assertEqual(loaded["responses"][0]["response"], "answer")
        self.assertEqual(wrong, {})
        class ManualStore:
            def save(inner, record):
                JSONRepository(self.root / "manual-check.json").save_all([record])
                return record
        row = {**loaded["responses"][0], "awarded_marks": 1, "justification": "Partial"}
        evaluated = ManualEvaluationService(ManualStore()).evaluate_and_save("C1", "First", "Formative 1", [row])
        self.assertEqual(evaluated["assessment_name"], "First")
        self.assertEqual(evaluated["test_name"], "Formative 1")
        self.assertEqual(evaluated["total_marks"], 1)
        self.assertEqual(evaluated["max_marks"], 2)
        self.assertEqual(evaluated["percentage"], 50)


if __name__ == "__main__":
    unittest.main()

