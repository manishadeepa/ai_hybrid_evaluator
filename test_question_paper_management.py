"""Question Paper business tests: isolated stores/workbooks, no Azure calls."""
import asyncio
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
with patch("dotenv.load_dotenv"):
    import reflex as rx
    import ai_hybrid_evaluator.state.facilitator_state as module
    from ai_hybrid_evaluator.state.admin_state import AdminState


def rows():
    return [{"Question No": "Q1", "Question": " First question ", "Marks": 5, "CO": 1, "LO": 1.1,
             "Knowledge Type": "Fact", "Domain": "Cognitive", "RBT level": "C-Remember", "Answer Key": " First answer "},
            {"Question No": "Q2", "Question": "Second question", "Marks": 2, "CO": "CO2", "LO": "LO2",
             "Knowledge Type": "Conceptual", "Domain": "Psychomotor", "RBT level": "Understand", "Answer Key": "B"}]


def workbook(records=None, columns=COLUMNS):
    book = Workbook(); sheet = book.active
    sheet.append(list(columns))
    for row in rows() if records is None else records:
        sheet.append([row.get(c) for c in columns])
    data = BytesIO(); book.save(data); book.close()
    return data.getvalue()


class QuestionPaperTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.tests = TestService(TestRepository(self.root / "tests.json"))
        self.assessments = AssessmentService(AssessmentRepository(self.root / "assessments.json"), self.tests)
        self.a = self.assessments.create_assessment({"name": "A"})["assessment_id"]
        self.b = self.assessments.create_assessment({"name": "B"})["assessment_id"]
        self.test = self.tests.create_test(self.a, {"test_name": "Formative 1"})
        self.papers = QuestionPaperService(self.tests)

    def upload(self, data=None, name="paper.xlsx"):
        return self.papers.import_upload(self.a, self.test["test_id"], name, workbook() if data is None else data)

    def test_import_totals_questions_and_reload(self):
        paper = self.upload()
        self.assertEqual(paper["question_count"], 2)
        self.assertEqual(paper["total_marks"], 7)
        self.assertEqual(paper["questions"][0]["Question"], " First question ")
        self.assertEqual(paper["questions"][0]["Answer Key"], " First answer ")
        fresh = QuestionPaperService(TestService(TestRepository(self.root / "tests.json")))
        self.assertEqual(fresh.get_paper(self.a, self.test["test_id"]), paper)
        self.assertEqual(fresh.get_questions(self.a, self.test["test_id"]), paper["questions"])
        self.assertEqual(fresh.list_papers(self.a), [paper])
        self.assertEqual(fresh.list_papers(self.b), [])
        self.assertEqual(self.assessments.get_assessment(self.a)["question_papers"], {"Formative 1": paper["filename"]})
        self.assertFalse((self.root / "question_papers.json").exists())

    def test_missing_columns(self):
        for column in COLUMNS:
            with self.subTest(column=column), self.assertRaisesRegex(ValueError, column):
                self.upload(workbook(columns=[c for c in COLUMNS if c != column]))
        self.assertEqual(self.papers.get_questions(self.a, self.test["test_id"]), [])

    def test_invalid_numbers_and_canonical_duplicates(self):
        for number in (None, "", "bad", "Q0", -1, 1.5, True):
            value = rows(); value[0]["Question No"] = number
            with self.subTest(number=number), self.assertRaisesRegex(ValueError, "question number"):
                self.upload(workbook(value))
        value = rows(); value[1]["Question No"] = 1
        with self.assertRaisesRegex(ValueError, "Duplicate question number"):
            self.upload(workbook(value))

    def test_numeric_and_nonconsecutive_numbers_preserved(self):
        value = rows(); value[0]["Question No"] = 1; value[1]["Question No"] = "Q3"
        paper = self.upload(workbook(value))
        self.assertEqual([r["Question No"] for r in paper["questions"]], [1, "Q3"])

    def test_blank_and_duplicate_text_rows(self):
        for text in (None, " ", 5):
            value = rows(); value[0]["Question"] = text
            with self.subTest(text=text), self.assertRaisesRegex(ValueError, "question text"):
                self.upload(workbook(value))
        value = rows(); value[1]["Question"] = value[0]["Question"].strip()
        with self.assertRaisesRegex(ValueError, "duplicates"):
            self.upload(workbook(value))
        with self.assertRaises(ValueError): self.upload(workbook([rows()[0], {}, rows()[1]]))

    def test_invalid_marks_and_zero(self):
        for marks in (None, "", "abc", -1, "NaN", "inf", True):
            value = rows(); value[0]["Marks"] = marks
            with self.subTest(marks=marks), self.assertRaisesRegex(ValueError, "marks"):
                self.upload(workbook(value))
        value = rows(); value[0]["Marks"] = 0; value[1]["Marks"] = 2.5
        self.assertEqual(self.upload(workbook(value))["total_marks"], 2.5)

    def test_metadata_validation_preserves_existing_conventions(self):
        for field, value in [("CO", "banana"), ("CO", 0), ("CO", None), ("LO", "bad"), ("LO", None),
                             ("Knowledge Type", ""), ("Domain", None), ("RBT level", 3)]:
            data = rows(); data[0][field] = value
            with self.subTest(field=field, value=value), self.assertRaisesRegex(ValueError, field):
                self.upload(workbook(data))
        data = rows(); data[0]["LO"] = "LO1.2"; data[0]["Knowledge Type"] = "Procedure"
        self.assertEqual(self.upload(workbook(data))["questions"][0]["LO"], "LO1.2")

    def test_answer_key_required_and_scalar_answers(self):
        for answer in (None, "", " ", True):
            data = rows(); data[0]["Answer Key"] = answer
            with self.subTest(answer=answer), self.assertRaisesRegex(ValueError, "answer key"):
                self.upload(workbook(data))
        data = rows(); data[0]["Answer Key"] = 0
        self.assertEqual(self.upload(workbook(data))["questions"][0]["Answer Key"], 0)

    def test_empty_corrupt_unsupported_and_formula(self):
        for data in (b"", b"not excel", workbook([])):
            with self.assertRaises(ValueError): self.upload(data)
        for name in ("paper.csv", "paper.pdf", "paper.xlsm"):
            with self.assertRaisesRegex(ValueError, "Unsupported"): self.upload(name=name)
        data = rows(); data[0]["Marks"] = "=2+3"
        with self.assertRaisesRegex(ValueError, "formula"): self.upload(workbook(data))
        with self.assertRaisesRegex(ValueError, "duplicate column"):
            self.upload(workbook(columns=[*COLUMNS, "CO"]))

    def test_path_traversal_and_reserved_names(self):
        for name in ("../paper.xlsx", "..\\paper.xlsx", "C:\\paper.xlsx", "/paper.xlsx", "CON.xlsx", "paper.xlsx:stream", "paper.xlsx "):
            with self.subTest(name=name), self.assertRaises(ValueError): self.upload(name=name)
        self.assertFalse(self.papers.upload_dir.exists())

    def test_import_file_preserves_source_and_identity(self):
        source = self.root / "source.xlsx"
        content = workbook(); source.write_bytes(content)
        paper = self.papers.import_file(self.a, self.test["test_id"], source)
        self.assertEqual(source.read_bytes(), content)
        self.assertEqual(paper["test_id"], self.test["test_id"])
        self.assertEqual(self.papers.list_papers(), [paper])

    def test_corrupt_metadata_is_not_overwritten(self):
        self.upload()
        record = self.tests.repository.get_by_id(self.test["test_id"])
        record["question_paper_details"]["test_id"] = "other"
        self.tests.repository.save(record)
        before = self.tests.repository.file_path.read_bytes()
        with self.assertRaisesRegex(ValueError, "relationship"):
            self.upload()
        self.assertEqual(self.tests.repository.file_path.read_bytes(), before)

    def test_missing_file_and_scope(self):
        with self.assertRaisesRegex(ValueError, "missing"): self.papers.import_file(self.a, self.test["test_id"], self.root / "missing.xlsx")
        for aid, tid in ((self.b, self.test["test_id"]), (self.a, "missing"), ("missing", self.test["test_id"])):
            with self.assertRaises(ValueError): self.papers.import_upload(aid, tid, "paper.xlsx", workbook())
        self.assertFalse(self.papers.upload_dir.exists())

    def test_invalid_replacement_preserves_file_and_metadata(self):
        paper = self.upload(); before = self.tests.repository.file_path.read_bytes()
        path = self.papers.upload_dir / paper["filename"]; contents = path.read_bytes()
        data = rows(); data[1]["Marks"] = -1
        with self.assertRaises(ValueError): self.upload(workbook(data))
        self.assertEqual(before, self.tests.repository.file_path.read_bytes())
        self.assertEqual(contents, path.read_bytes())
        self.assertEqual(len(list(self.papers.upload_dir.iterdir())), 1)

    def test_valid_replacement_and_same_name_other_test(self):
        old = self.upload(); data = rows(); data[0]["Marks"] = 8
        new = self.upload(workbook(data))
        self.assertNotEqual(old["filename"], new["filename"])
        self.assertTrue((self.papers.upload_dir / old["filename"]).exists())
        other = self.tests.create_test(self.b, {"test_name": "Formative 1"})
        third = self.papers.import_upload(self.b, other["test_id"], "paper.xlsx", workbook())
        self.assertNotEqual(third["filename"], old["filename"])
        self.assertEqual(self.papers.get_paper(self.a, self.test["test_id"])["total_marks"], 10)
        self.assertEqual(self.papers.get_paper(self.b, other["test_id"])["total_marks"], 7)

    def test_json_save_failure_keeps_old_paper(self):
        old = self.upload(); before = self.tests.repository.file_path.read_bytes()
        with patch("backend.repositories.json_repository.os.replace", side_effect=OSError("disk")):
            with self.assertRaises(OSError): self.upload()
        self.assertEqual(self.tests.repository.file_path.read_bytes(), before)
        self.assertEqual([p.name for p in self.papers.upload_dir.iterdir()], [old["filename"]])

    def test_file_write_failure_publishes_nothing(self):
        before = self.tests.repository.file_path.read_bytes()
        with patch("backend.services.question_paper_service.os.fsync", side_effect=OSError("disk")):
            with self.assertRaises(OSError): self.upload()
        self.assertEqual(self.tests.repository.file_path.read_bytes(), before)
        self.assertEqual(list(self.papers.upload_dir.iterdir()), [])

    def test_detach_keeps_file_and_other_test(self):
        paper = self.upload()
        self.papers.remove_paper(self.a, self.test["test_id"])
        self.assertIsNone(self.papers.get_paper(self.a, self.test["test_id"]))
        self.assertTrue((self.papers.upload_dir / paper["filename"]).exists())
        self.assertNotIn("question_paper_details", self.tests.get_test(self.test["test_id"]))

    def test_evaluation_dependencies_block_replacement_and_detach(self):
        paper = self.upload()
        (self.root / "ai_evaluation_runs.json").write_text(json.dumps([{"test_id": self.test["test_id"], "status": "paused"}]))
        with self.assertRaisesRegex(ValueError, "dependent data"): self.upload()
        with self.assertRaisesRegex(ValueError, "dependent data"): self.papers.remove_paper(self.a, self.test["test_id"])
        self.assertEqual(self.papers.get_paper(self.a, self.test["test_id"]), paper)

    def test_legacy_read_does_not_migrate(self):
        self.papers.upload_dir.mkdir(parents=True)
        (self.papers.upload_dir / "legacy.xlsx").write_bytes(workbook())
        self.tests.update_test(self.test["test_id"], {"question_paper": "legacy.xlsx"})
        before = self.tests.repository.file_path.read_bytes()
        self.assertEqual(self.papers.get_paper(self.a, self.test["test_id"])["total_marks"], 7)
        self.assertEqual(self.tests.repository.file_path.read_bytes(), before)

    def test_missing_or_changed_stored_file(self):
        paper = self.upload(); path = self.papers.upload_dir / paper["filename"]
        path.write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "changed outside"): self.papers.get_paper(self.a, self.test["test_id"])
        path.unlink()
        with self.assertRaisesRegex(ValueError, "missing"): self.papers.get_paper(self.a, self.test["test_id"])

    def test_corrupt_json_preserved(self):
        self.tests.repository.file_path.write_text("{bad")
        with self.assertRaises(ValueError): self.upload()
        self.assertEqual(self.tests.repository.file_path.read_text(), "{bad")
        self.assertFalse(self.papers.upload_dir.exists())

    def test_actual_workbook_and_unchanged_ai_normalization(self):
        actual = Path(__file__).parent / "uploaded_files" / "Question sheet.xlsx"
        if not actual.exists(): self.skipTest("Existing workbook unavailable")
        parsed = self.papers.validate_workbook(actual.read_bytes(), actual.name)
        self.assertEqual(parsed["question_count"], 14)
        self.assertEqual(parsed["total_marks"], 40)
        paper = self.upload()
        import pandas as pd
        response = self.root / "response.xlsx"
        records = rows()
        for row in records: row["Candidate Answer"] = "Actual answer"
        pd.DataFrame(records).to_excel(response, index=False)
        from ai_hybrid_evaluator.services.ai_evaluation_service import prepare_candidate_records
        normalized = prepare_candidate_records(self.papers.upload_dir / paper["filename"], response)
        self.assertEqual(len(normalized), 2)
        self.assertEqual(normalized[0]["answer_key"], " First answer ")
        self.assertEqual(sum(r["max_marks"] for r in normalized), 7)


class QuestionPaperReflexTests(unittest.IsolatedAsyncioTestCase):
    async def test_existing_upload_and_remove_events(self):
        with tempfile.TemporaryDirectory() as folder:
            rootpath = Path(folder)
            tests = TestService(TestRepository(rootpath / "tests.json"))
            service = AssessmentService(AssessmentRepository(rootpath / "assessments.json"), tests)
            assessment = service.create_assessment({"name": "Upload", "tests": ["Formative 1"]})
            root = rx.State(_reflex_internal_init=True)
            fac = root.get_substate(tuple(module.FacilitatorState.get_full_name().split(".")))
            admin = await fac.get_state(AdminState)
            admin._apply_assessment_records(service.load_assessments())
            fac.selected_assessment_name = "Upload"; fac.selected_test_name = "Formative 1"
            class Upload:
                filename = "paper.xlsx"
                def __init__(self, content): self.content = content
                async def read(self): return self.content
            with patch.object(module, "AssessmentService", return_value=service), patch.object(rx, "get_upload_dir", return_value=tests.dependencies.upload_dir):
                await fac.handle_upload_for_test([Upload(b"corrupt")])
                self.assertEqual(fac.qp_validation_status, "error")
                self.assertFalse(fac.question_papers.get("Upload", {}))
                await fac.handle_upload_for_test([Upload(workbook())])
                self.assertEqual(fac.qp_validation_status, "success")
                self.assertEqual(fac.question_papers["Upload"]["Formative 1"], "paper.xlsx")
                before = tests.repository.file_path.read_bytes()
                await fac.handle_upload_for_test([Upload(workbook()), Upload(workbook())])
                self.assertEqual(fac.qp_validation_status, "error")
                self.assertEqual(tests.repository.file_path.read_bytes(), before)
                await fac.remove_current_test_question_paper()
                self.assertFalse(fac.question_papers["Upload"])
                self.assertTrue((tests.dependencies.upload_dir / "paper.xlsx").exists())


if __name__ == "__main__": unittest.main()
