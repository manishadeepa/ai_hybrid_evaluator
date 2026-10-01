"""Offline type/schema tests using isolated JSON stores and generated workbooks."""
from copy import deepcopy
from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from openpyxl import Workbook

from backend.repositories.assessment_repository import AssessmentRepository
from backend.repositories.test_repository import TestRepository
from backend.services.assessment_service import AssessmentService
from backend.services.test_service import TestService
from backend.services.question_paper_service import QuestionPaperService, COLUMNS


def workbook(question="Choose one\nA) Alpha\nB) Beta\nC) Gamma\nD) Delta", answer="B) Beta"):
    book = Workbook()
    book.active.append(COLUMNS)
    book.active.append(["Q1", question, 2, 1, 1.1, "Fact", "Cognitive", "Remember", answer])
    output = BytesIO()
    book.save(output)
    book.close()
    return output.getvalue()


class TestTypeTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.tests = TestService(TestRepository(self.root / "tests.json"))
        self.assessments = AssessmentService(AssessmentRepository(self.root / "assessments.json"), self.tests)
        self.a = self.assessments.create_assessment({"name": "Types"})["assessment_id"]
        self.papers = QuestionPaperService(self.tests)

    def create(self, **details):
        return self.tests.create_test(self.a, {"test_name": "Test", **details})

    def test_types_independent_of_final(self):
        for kind, final in (("objective", False), ("subjective", True)):
            test = self.create(test_name=kind, test_type=kind, is_final=final)
            self.assertEqual(TestService(self.tests.repository).get_test(test["test_id"])["test_type"], kind)
            self.assertEqual(test["is_final"], final)

    def test_legacy_read_and_unrelated_update_preserve_missing_type(self):
        test = self.create()
        before = self.tests.repository.file_path.read_bytes()
        self.assertNotIn("test_type", self.tests.get_test(test["test_id"]))
        self.assertEqual(before, self.tests.repository.file_path.read_bytes())
        self.tests.update_test(test["test_id"], {"description": "changed"})
        self.assertNotIn("test_type", self.tests.repository.get_by_id(test["test_id"]))

    def test_invalid_types_rejected_without_writes(self):
        test = self.create()
        before = self.tests.repository.file_path.read_bytes()
        for invalid in (None, "", "Objective", "Formative", True, [], {}):
            for action in (
                lambda: self.tests.update_test(test["test_id"], {"test_type": invalid}),
                lambda: self.tests.repository.save({**test, "test_type": invalid}),
                lambda: self.create(test_name="new", test_type=invalid),
                lambda: self.assessments.update_assessment(self.a, {"test_types": {"Test": invalid}}),
            ):
                with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                    action()
                self.assertEqual(before, self.tests.repository.file_path.read_bytes())

    def test_assessment_roundtrip_and_rename_keep_type(self):
        self.assessments.add_test(self.a, "Typed", test_type="objective")
        self.assessments.add_test(self.a, "Legacy")
        loaded = self.assessments.get_assessment(self.a)
        self.assertEqual(loaded["test_types"], {"Typed": "objective"})
        self.assessments.update_assessment(self.a, {"name": "Renamed assessment"})
        tid = loaded["test_ids"]["Typed"]
        self.assessments.update_test(self.a, tid, {"test_name": "Renamed test"})
        self.assertEqual(self.assessments.get_assessment(self.a)["test_types"], {"Renamed test": "objective"})
        self.assertNotIn("test_types", self.assessments.repository.get_by_id(self.a))

    def test_objective_import_and_reload(self):
        test = self.create(test_type="objective")
        paper = self.papers.import_upload(self.a, test["test_id"], "renamed.xlsx", workbook())
        row = paper["questions"][0]
        self.assertEqual(row["correct_option"], "B")
        self.assertEqual(row["options"], dict(zip("ABCD", ("Alpha", "Beta", "Gamma", "Delta"))))
        self.assertEqual(row["question_stem"], "Choose one")
        self.assertEqual(row["Answer Key"], "B) Beta")
        self.assertEqual(self.papers.get_paper(self.a, test["test_id"]), paper)

    def test_objective_rejects_malformed_options_and_keys(self):
        for question, answer in (
            ("Stem\nA) A\nB) B\nC) C", "A"),
            ("Stem\nA) A\nA) B\nC) C\nD) D", "A"),
            ("Stem\nA) Same\nB) same\nC) C\nD) D", "A"),
            ("Stem\nA) A\nB) B\nC) C\nD) D", "A) Wrong"),
            ("Stem\nA) A\nB) B\nC) C\nD) D", "A,B"),
            ("No options", "A"),
        ):
            with self.subTest(question=question, answer=answer), self.assertRaises(ValueError):
                self.papers.validate_workbook(workbook(question, answer), "paper.xlsx", "objective")
        self.assertEqual(self.papers.validate_workbook(workbook(answer="B"), "paper.xlsx", "objective")["questions"][0]["correct_option"], "B")

    def test_subjective_and_mismatched_upload_atomicity(self):
        test = self.create(test_type="subjective")
        paper = self.papers.import_upload(self.a, test["test_id"], "paper.xlsx", workbook("Explain why", "Reference answer"))
        before = self.tests.repository.file_path.read_bytes()
        replacement = self.papers.import_upload(self.a, test["test_id"], "objective.xlsx", workbook())
        self.assertEqual(self.tests.get_test(test["test_id"])["test_type"], "objective")
        self.assertEqual(self.papers.get_paper(self.a, test["test_id"]), replacement)
        before = self.tests.repository.file_path.read_bytes()
        with self.assertRaises(ValueError):
            self.papers.import_upload(self.a, test["test_id"], "bad.xlsx", workbook(answer="Z"))
        self.assertEqual(self.tests.repository.file_path.read_bytes(), before)
        self.assertEqual(len(list(self.papers.upload_dir.iterdir())), 2)

    def test_legacy_attached_paper_checked_when_selecting_type(self):
        test = self.create()
        self.papers.import_upload(self.a, test["test_id"], "arbitrary.xlsx", workbook())
        before = self.tests.repository.file_path.read_bytes()
        with self.assertRaises(ValueError):
            self.tests.update_test(test["test_id"], {"test_type": "subjective"})
        self.assertEqual(before, self.tests.repository.file_path.read_bytes())
        self.tests.update_test(test["test_id"], {"test_type": "objective"})
        self.assertEqual(self.papers.get_paper(self.a, test["test_id"])["questions"][0]["correct_option"], "B")

    def test_activity_blocks_type_change_in_both_entry_points(self):
        test = self.create(test_type="objective")
        (self.root / "ai_evaluation_runs.json").write_text(json.dumps([{"test_id": test["test_id"]}]))
        before = self.tests.repository.file_path.read_bytes()
        with self.assertRaisesRegex(ValueError, "dependent data"):
            self.tests.update_test(test["test_id"], {"test_type": "subjective"})
        with self.assertRaisesRegex(ValueError, "dependent data"):
            self.assessments.update_assessment(self.a, {"test_types": {"Test": "subjective"}})
        self.assertEqual(before, self.tests.repository.file_path.read_bytes())
        self.tests.update_test(test["test_id"], {"test_type": "objective", "description": "allowed"})

    def test_missing_attached_file_does_not_guess(self):
        test = self.create(question_paper="missing.xlsx")
        with self.assertRaisesRegex(ValueError, "missing"):
            self.tests.update_test(test["test_id"], {"test_type": "objective"})
        self.assertNotIn("test_type", self.tests.get_test(test["test_id"]))

    def test_actual_templates(self):
        root = Path(__file__).parent / "uploaded_files"
        for name, kind in (("Question sheet.xlsx", "subjective"), ("HoQ_Objective_Questions.xlsx", "objective")):
            with self.subTest(name=name):
                parsed = self.papers.validate_workbook((root / name).read_bytes(), "arbitrary.xlsx", kind)
                self.assertEqual(parsed["question_count"], 14)
                self.assertEqual(parsed["total_marks"], 40)
                self.assertEqual(parsed["test_type"], kind)


if __name__ == "__main__":
    unittest.main()
