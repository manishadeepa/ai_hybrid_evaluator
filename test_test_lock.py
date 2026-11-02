"""Permanent test-lock behavior across persistence and test-scoped mutations."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from io import BytesIO
import json
import multiprocessing
from pathlib import Path
import tempfile
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from openpyxl import Workbook
import reflex as rx

from backend.repositories.ai_evaluation_run_repository import AIEvaluationRunRepository
from backend.repositories.assessment_repository import AssessmentRepository
from backend.repositories.candidate_repository import CandidateRepository
from backend.repositories.manual_evaluation_repository import ManualEvaluationRepository
from backend.repositories.response_repository import ResponseRepository
from backend.repositories.test_repository import LOCKED_TEST_ERROR, TestRepository as LockTestRepository
from backend.services.assessment_service import AssessmentService
from backend.services.candidate_management_service import CandidateManagementService
from backend.services.candidate_assignment_service import CandidateAssignmentService
from backend.services.question_paper_service import COLUMNS, QuestionPaperService
from backend.services.response_lifecycle_service import ResponseLifecycleService
from backend.services.test_service import TestService as LockTestService
from backend.services.test_service import test_mutation_guard as _test_mutation_guard
from ai_hybrid_evaluator.state import facilitator_state as facilitator_state_module
from ai_hybrid_evaluator.state.facilitator_state import FacilitatorState


def _process_lock_or_update(root, test_id, action, barrier, output):
    service = LockTestService(LockTestRepository(Path(root) / "tests.json"))
    barrier.wait(timeout=15)
    if action == "lock":
        output.put(("locked", service.lock_test(test_id, "F001", "facilitator")["is_locked"]))
        return
    try:
        service.update_test(test_id, {"description": "concurrent process update"})
        output.put(("updated", True))
    except ValueError as exc:
        output.put(("update_rejected", str(exc)))


def _paper_bytes():
    book = Workbook()
    sheet = book.active
    sheet.append(list(COLUMNS))
    sheet.append(["Q1", "Question", 2, "CO1", "LO1", "Fact", "Cognitive", "Remember", "A"])
    data = BytesIO()
    book.save(data)
    book.close()
    return data.getvalue()


class TestLockTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.tests = LockTestService(
            LockTestRepository(self.root / "tests.json"),
            upload_dir=self.root / "uploaded_files",
        )
        self.assessments = AssessmentService(
            AssessmentRepository(self.root / "assessments.json"),
            self.tests,
        )
        self.assessment = self.assessments.save_assessment(
            {
                "name": "Lock assessment",
                "facilitator_ids": ["F001"],
                "facilitator_names": ["Facilitator"],
                "facilitator_id": "F001",
                "facilitator_name": "Facilitator",
                "assigned_candidates": [],
                "status": "Scheduled",
                "approval_status": "approved",
                "tests": ["Test 1"],
                "final_test": "",
            },
            test_created_by="F001",
        )
        self.test_id = self.assessment["test_ids"]["Test 1"]

    def lock(self):
        return self.tests.lock_test(self.test_id, "F001", "facilitator")

    def test_only_creator_can_lock_and_metadata_is_idempotent_and_utc(self):
        with self.assertRaisesRegex(ValueError, "Only the test creator"):
            self.tests.lock_test(self.test_id, "F002", "facilitator")
        with self.assertRaisesRegex(ValueError, "Only facilitators"):
            self.tests.lock_test(self.test_id, "F001", "admin")

        locked = self.lock()
        first_metadata = (locked["locked_by"], locked["locked_at"])
        self.assertEqual(first_metadata[0], "F001")
        stamp = datetime.fromisoformat(first_metadata[1])
        self.assertIsNotNone(stamp.tzinfo)
        self.assertEqual(stamp.utcoffset().total_seconds(), 0)

        fresh = LockTestRepository(self.root / "tests.json").get_by_id(self.test_id)
        repeated = self.lock()
        self.assertTrue(repeated["already_locked"])
        self.assertTrue(fresh["is_locked"])
        self.assertEqual(
            (repeated["locked_by"], repeated["locked_at"]),
            first_metadata,
        )

    def test_unknown_ownership_and_client_supplied_ownership_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unsupported test settings"):
            self.tests.create_test(
                self.assessment["assessment_id"],
                {"test_name": "Spoofed", "created_by": "F001"},
            )
        with self.assertRaisesRegex(ValueError, "Unsupported test settings"):
            self.tests.update_test(self.test_id, {"created_by": "F002"})

        before = self.tests.repository.get_by_id(self.test_id)
        changed = dict(before, created_by="F002")
        with self.assertRaisesRegex(ValueError, "ownership and lock metadata"):
            self.tests.repository.save_all([changed])
        self.assertEqual(
            self.tests.repository.get_by_id(self.test_id)["created_by"],
            "F001",
        )

        legacy = self.tests.create_test(
            self.assessment["assessment_id"],
            {"test_name": "Legacy test"},
        )
        self.assertEqual(legacy["created_by"], "")
        with self.assertRaisesRegex(ValueError, "creator is unknown"):
            self.tests.lock_test(legacy["test_id"], "F001", "facilitator")

    def test_creator_mutations_fail_closed_when_test_storage_is_missing(self):
        missing_root = self.root / "missing-test-store"
        with self.assertRaisesRegex(ValueError, "Canonical test identity"):
            with _test_mutation_guard(
                test_id="unknown-test",
                data_dir=missing_root,
                require_creator=True,
                facilitator_id="F001",
                role="facilitator",
            ):
                self.fail("Mutation guard must not allow writes without a test record.")

    def test_legacy_record_migration_preserves_existing_owner(self):
        path = self.root / "legacy-tests.json"
        path.write_text(
            json.dumps(
                [
                    {
                        "test_id": "legacy-id",
                        "assessment_id": "assessment-id",
                        "test_name": "Legacy",
                        "created_by": "F009",
                        "position": 0,
                        "is_final": False,
                    },
                    {
                        "test_id": "unknown-id",
                        "assessment_id": "assessment-id",
                        "test_name": "Unknown owner",
                        "position": 1,
                        "is_final": False,
                    }
                ]
            ),
            encoding="utf-8",
        )
        record = LockTestRepository(path).get_by_id("legacy-id")
        self.assertEqual(record["created_by"], "F009")
        self.assertFalse(record["is_locked"])
        self.assertEqual(record["locked_by"], "")
        self.assertIsNone(record["locked_at"])
        unknown = LockTestRepository(path).get_by_id("unknown-id")
        self.assertEqual(unknown["created_by"], "")
        with self.assertRaisesRegex(ValueError, "creator is unknown"):
            LockTestRepository(path).lock_test("unknown-id", "F001", "facilitator")

    def test_locked_metadata_is_returned_in_assessment_projection(self):
        locked = self.lock()
        projected = self.tests.populate_assessment(self.assessment)
        self.assertEqual(
            projected["test_lock_states"]["Test 1"],
            {
                "created_by": "F001",
                "is_locked": True,
                "locked_by": locked["locked_by"],
                "locked_at": locked["locked_at"],
            },
        )

    def test_locked_test_rejects_direct_parent_and_bulk_mutations(self):
        self.lock()
        with self.assertRaisesRegex(ValueError, LOCKED_TEST_ERROR):
            self.tests.update_test(self.test_id, {"description": "changed"})
        with self.assertRaisesRegex(ValueError, LOCKED_TEST_ERROR):
            self.tests.delete_test(self.assessment["assessment_id"], self.test_id)
        with self.assertRaisesRegex(ValueError, LOCKED_TEST_ERROR):
            self.tests.replace_tests(self.assessment["assessment_id"], [])
        with self.assertRaisesRegex(ValueError, LOCKED_TEST_ERROR):
            self.assessments.delete_test(self.assessment["assessment_id"], self.test_id)
        with self.assertRaisesRegex(ValueError, LOCKED_TEST_ERROR):
            self.assessments.delete_assessment(self.assessment["assessment_id"])

        changed_name = dict(self.assessment, name="Renamed")
        with self.assertRaisesRegex(ValueError, LOCKED_TEST_ERROR):
            self.assessments.save_assessment(changed_name)
        changed_candidates = dict(self.assessment, assigned_candidates=["C1"])
        with self.assertRaisesRegex(ValueError, LOCKED_TEST_ERROR):
            self.assessments.save_assessment(changed_candidates)

    def test_locked_test_rejects_question_paper_upload_without_orphan_file(self):
        service = QuestionPaperService(self.tests, self.root / "uploaded_files")
        self.lock()
        with self.assertRaisesRegex(ValueError, LOCKED_TEST_ERROR):
            service.import_upload(
                self.assessment["assessment_id"],
                self.test_id,
                "test.xlsx",
                _paper_bytes(),
            )
        self.assertFalse(
            (self.root / "uploaded_files").exists()
            and any((self.root / "uploaded_files").iterdir())
        )

    def test_locked_test_cannot_remove_an_existing_question_paper(self):
        service = QuestionPaperService(self.tests, self.root / "uploaded_files")
        paper = service.import_upload(
            self.assessment["assessment_id"], self.test_id, "test.xlsx", _paper_bytes()
        )
        self.lock()
        with self.assertRaisesRegex(ValueError, LOCKED_TEST_ERROR):
            service.remove_paper(self.assessment["assessment_id"], self.test_id)
        self.assertEqual(
            service.get_paper(self.assessment["assessment_id"], self.test_id),
            paper,
        )

    def test_locked_test_rejects_manual_and_background_evaluation_writes(self):
        self.lock()
        class FakeEvaluationStorage:
            file_path = self.root / "manual_evaluations.json"

            def get_all(self):
                return []

            def save_all(self, _):
                raise AssertionError("A locked manual evaluation must not reach persistence.")

        with patch(
            "backend.repositories.manual_evaluation_repository.JSONRepository",
            return_value=FakeEvaluationStorage(),
        ):
            manual = ManualEvaluationRepository()
            with self.assertRaisesRegex(ValueError, LOCKED_TEST_ERROR):
                manual.save(
                    {
                        "candidate_id": "C1",
                        "assessment_id": self.assessment["assessment_id"],
                        "test_id": self.test_id,
                        "assessment_name": "Lock assessment",
                        "test_name": "Test 1",
                        "questions": [],
                    },
                    facilitator_id="F001",
                    role="facilitator",
                )

        runs = AIEvaluationRunRepository(self.root / "ai_evaluation_runs.json")
        with self.assertRaisesRegex(ValueError, LOCKED_TEST_ERROR):
            runs.save(
                {
                    "run_id": "run-1",
                    "status": "running",
                    "questions": [{"status": "pending", "record": {}, "pair_id": "pair-1"}],
                    "candidate_ids": ["C1"],
                    "assessment_name": "Lock assessment",
                    "test_name": "Test 1",
                    "assessment_id": self.assessment["assessment_id"],
                    "test_id": self.test_id,
                },
                facilitator_id="F001",
                role="facilitator",
            )

    def test_locked_test_still_allows_existing_question_paper_reads(self):
        service = QuestionPaperService(self.tests, self.root / "uploaded_files")
        paper = service.import_upload(
            self.assessment["assessment_id"], self.test_id, "test.xlsx", _paper_bytes()
        )
        self.lock()
        self.assertEqual(
            service.get_paper(self.assessment["assessment_id"], self.test_id),
            paper,
        )
        self.assertEqual(
            service.get_questions(self.assessment["assessment_id"], self.test_id),
            paper["questions"],
        )

    def test_locked_test_rejects_candidate_response_changes(self):
        candidates = CandidateManagementService(
            CandidateRepository(self.root / "candidates.json"),
            assessments=self.assessments,
        )
        candidates.create_candidate(
            {"candidate_id": "C1", "name": "Candidate", "email": "c1@example.com"}
        )
        self.assessments.candidate_catalog = candidates.list_candidates
        self.assessment = self.assessments.update_assessment(
            self.assessment["assessment_id"], {"assigned_candidates": ["C1"]}
        )
        assignments = CandidateAssignmentService(candidates)
        responses = ResponseLifecycleService(
            assignments,
            question_loader=lambda *_: [
                {
                    "id": 1,
                    "title": "Question",
                    "text": "Question",
                    "marks": 2,
                    "co": "CO1",
                    "lo": "LO1",
                    "knowledge_type": "Fact",
                    "category": "Cognitive",
                    "rbt_level": "Remember",
                }
            ],
        )
        key = ("C1", self.assessment["assessment_id"], self.test_id)
        responses.start_test(*key)
        self.lock()
        with self.assertRaisesRegex(ValueError, LOCKED_TEST_ERROR):
            responses.save_answer(*key, 1, "A")

    def test_locked_test_blocks_direct_assignment_and_response_repository_writes(self):
        from backend.repositories.test_candidate_repository import TestCandidateRepository

        assignments = TestCandidateRepository(self.root / "test_candidates.json")
        assignment = {
            "candidate_id": "C1",
            "assessment_id": self.assessment["assessment_id"],
            "test_id": self.test_id,
            "status": "Assigned",
            "assigned_at": "2026-01-01T00:00:00+00:00",
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
            "started_at": None,
            "submitted_at": None,
        }
        assignments.save(assignment)
        self.lock()
        with self.assertRaisesRegex(ValueError, LOCKED_TEST_ERROR):
            assignments.save({**assignment, "status": "In Progress"})
        with self.assertRaisesRegex(ValueError, LOCKED_TEST_ERROR):
            assignments.save_all([])

        responses = ResponseRepository(self.root / "responses.json")
        with self.assertRaisesRegex(ValueError, LOCKED_TEST_ERROR):
            responses.save(
                {
                    "candidate_id": "C1",
                    "assessment_id": self.assessment["assessment_id"],
                    "test_id": self.test_id,
                    "assessment_name": "Lock assessment",
                    "test_name": "Test 1",
                }
            )

    def test_ui_lock_button_matches_creator_noncreator_and_locked_states(self):
        from ai_hybrid_evaluator.pages.facilitator.assessment_workspace import tests_tab_card

        def lock_button(item):
            root = tests_tab_card(item)
            pending = [root]
            while pending:
                node = pending.pop()
                if getattr(node, "tag", None) == "Button" and "LucideLock" in str(node.children):
                    return node
                pending.extend(getattr(node, "children", []))
            self.fail("Lock Test button was not rendered.")

        base = {
            "name": "Test 1",
            "date": "",
            "is_final": False,
            "has_qp": False,
            "test_id": self.test_id,
        }
        creator = lock_button({**base, "is_locked": False, "can_lock": True})
        self.assertIn("lock_test_request_in_progress", creator.disabled._js_expr)

        non_creator = lock_button({**base, "is_locked": False, "can_lock": False})
        self.assertIn("false ? reflex", non_creator.disabled._js_expr)
        self.assertTrue(non_creator.disabled._js_expr.endswith(": true))"))
        self.assertIn(
            "Only the facilitator who created this test can evaluate or lock it.",
            non_creator.title._js_expr,
        )

        locked = lock_button({**base, "is_locked": True, "can_lock": False})
        self.assertTrue(locked.disabled._js_expr.startswith("(true ? true"))
        self.assertIn("Locked", locked.title._js_expr)
        self.assertIn("Locked", str(locked.children))

    def test_admin_test_dialog_disables_locked_test_controls(self):
        from ai_hybrid_evaluator.pages.admin.assessments import test_card

        root = test_card({"name": "Test 1", "date": "", "is_locked": True})
        pending = [root]
        nodes = []
        while pending:
            node = pending.pop()
            nodes.append(node)
            pending.extend(getattr(node, "children", []))

        date_input = next(node for node in nodes if getattr(node, "tag", None) == "DebounceInput")
        delete_button = next(
            node for node in nodes
            if getattr(node, "tag", None) == "Button"
            and "LucideTrash2" in str(node.children)
        )
        self.assertTrue(date_input.custom_attrs["disabled"]._var_value)
        self.assertTrue(delete_button.disabled._var_value)
        self.assertTrue(any(
            getattr(node, "tag", None) == "Badge"
            and "Locked" in str(node.children)
            for node in nodes
        ))

    def test_concurrent_lock_and_update_leave_no_post_lock_update(self):
        barrier = threading.Barrier(2)

        def lock_test():
            barrier.wait()
            return self.lock()

        def update_test():
            barrier.wait()
            try:
                return self.tests.update_test(self.test_id, {"description": "concurrent"})
            except ValueError as exc:
                return exc

        with ThreadPoolExecutor(max_workers=2) as pool:
            lock_future = pool.submit(lock_test)
            update_future = pool.submit(update_test)
            locked = lock_future.result()
            update_result = update_future.result()

        self.assertTrue(locked["is_locked"])
        self.assertEqual(
            self.tests.repository.get_by_id(self.test_id)["is_locked"],
            True,
        )
        self.assertGreaterEqual(
            datetime.fromisoformat(locked["locked_at"]),
            datetime.fromisoformat(
                self.tests.repository.get_by_id(self.test_id)["updated_at"]
            ),
        )
        if isinstance(update_result, ValueError):
            self.assertEqual(str(update_result), LOCKED_TEST_ERROR)
        with self.assertRaisesRegex(ValueError, LOCKED_TEST_ERROR):
            self.tests.update_test(self.test_id, {"description": "stale page"})

    def test_concurrent_process_lock_serializes_test_updates(self):
        context = multiprocessing.get_context("spawn")
        barrier = context.Barrier(2)
        output = context.Queue()
        processes = [
            context.Process(
                target=_process_lock_or_update,
                args=(str(self.root), self.test_id, action, barrier, output),
            )
            for action in ("lock", "update")
        ]
        for process in processes:
            process.start()
        results = [output.get(timeout=30) for _ in processes]
        for process in processes:
            process.join(timeout=30)
            self.assertEqual(process.exitcode, 0)

        self.assertIn(("locked", True), results)
        final = self.tests.repository.get_by_id(self.test_id)
        self.assertTrue(final["is_locked"])
        self.assertGreaterEqual(
            datetime.fromisoformat(final["locked_at"]),
            datetime.fromisoformat(final["updated_at"]),
        )
        if ("update_rejected", LOCKED_TEST_ERROR) in results:
            self.assertEqual(final["description"], "")
        else:
            self.assertEqual(final["description"], "concurrent process update")

    def test_scoped_mutation_guard_uses_test_id_and_rejects_forged_ids(self):
        self.lock()
        with self.assertRaisesRegex(ValueError, LOCKED_TEST_ERROR):
            with _test_mutation_guard(
                test_id=self.test_id,
                assessment_id=self.assessment["assessment_id"],
                data_dir=self.root,
            ):
                pass
        with self.assertRaisesRegex(ValueError, LOCKED_TEST_ERROR):
            with _test_mutation_guard(
                test_id="wrong-id",
                assessment_id=self.assessment["assessment_id"],
                test_name="Test 1",
                data_dir=self.root,
            ):
                pass


class LockedWeightageStateTests(unittest.IsolatedAsyncioTestCase):
    async def test_stale_weightage_page_cannot_change_locked_test(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir)
            tests = LockTestService(LockTestRepository(root_dir / "tests.json"))
            assessments = AssessmentService(
                AssessmentRepository(root_dir / "assessments.json"),
                tests,
            )
            assessment = assessments.save_assessment(
                {
                    "name": "Lock assessment",
                    "facilitator_ids": ["F001"],
                    "facilitator_names": ["Facilitator"],
                    "facilitator_id": "F001",
                    "facilitator_name": "Facilitator",
                    "assigned_candidates": [],
                    "status": "Scheduled",
                    "approval_status": "approved",
                    "tests": ["Test 1"],
                    "final_test": "",
                },
                test_created_by="F001",
            )
            tests.lock_test(assessment["test_ids"]["Test 1"], "F001", "facilitator")

            weightages_file = root_dir / "weightages.json"
            pass_percentages_file = root_dir / "pass-percentages.json"
            weightages_file.write_text(
                json.dumps({"Lock assessment": {"Test 1": 75}}),
                encoding="utf-8",
            )
            pass_percentages_file.write_text(
                json.dumps({"Lock assessment": {"Test 1": 50}}),
                encoding="utf-8",
            )

            state_root = rx.State(_reflex_internal_init=True)
            facilitator = state_root.get_substate(
                tuple(FacilitatorState.get_full_name().split("."))
            )
            facilitator.selected_assessment_name = "Lock assessment"
            facilitator.weightage_inputs = {"Lock assessment": {"Test 1": "50"}}
            facilitator.pass_percentage_inputs = {"Lock assessment": {"Test 1": "50"}}
            facilitator.saved_assessment_weightages = {
                "Lock assessment": {"Test 1": 50}
            }
            facilitator.saved_assessment_pass_percentages = {
                "Lock assessment": {"Test 1": 50}
            }

            with (
                patch.object(
                    facilitator_state_module,
                    "AssessmentService",
                    return_value=assessments,
                ),
                patch.object(
                    FacilitatorState,
                    "get_state",
                    new=AsyncMock(return_value=SimpleNamespace(assessments=[])),
                ),
                patch.object(
                    FacilitatorState,
                    "_refresh_after_locked_mutation",
                    new=AsyncMock(return_value=None),
                ),
                patch.object(
                    FacilitatorState,
                    "_get_weightages_file_path",
                    return_value=weightages_file,
                ),
                patch.object(
                    FacilitatorState,
                    "_get_pass_percentages_file_path",
                    return_value=pass_percentages_file,
                ),
            ):
                await facilitator.save_weightage()

            self.assertEqual(
                json.loads(weightages_file.read_text(encoding="utf-8")),
                {"Lock assessment": {"Test 1": 75}},
            )
            self.assertEqual(
                json.loads(pass_percentages_file.read_text(encoding="utf-8")),
                {"Lock assessment": {"Test 1": 50}},
            )


if __name__ == "__main__":
    unittest.main()
